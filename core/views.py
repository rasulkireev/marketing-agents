from urllib.parse import urlencode

import stripe

from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.conf import settings
from django.contrib import messages
from django.urls import reverse, reverse_lazy
from django.views.generic import TemplateView, UpdateView, ListView, DetailView, FormView
from django.views import View
from django_q.tasks import async_task
from djstripe import models as djstripe_models
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.http import JsonResponse
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from core.models import BlogPostTitleSuggestion, GeneratedBlogPost
from django.utils.text import slugify
from django_q.tasks import async_task

from core.utils import check_if_profile_has_pro_subscription
from core.forms import ProfileUpdateForm, ProjectScanForm
from core.models import Profile, BlogPost, Project

from seo_blog_bot.utils import get_seo_blog_bot_logger
from django.db import IntegrityError


stripe.api_key = settings.STRIPE_SECRET_KEY


logger = get_seo_blog_bot_logger(__name__)

class HomeView(TemplateView):
    template_name = "pages/home.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        payment_status = self.request.GET.get("payment")
        if payment_status == "success":
            messages.success(self.request, "Thanks for subscribing, I hope you enjoy the app!")
            context["show_confetti"] = True
        elif payment_status == "failed":
            messages.error(self.request, "Something went wrong with the payment.")

        context["form"] = ProjectScanForm()

        # Add projects to context for authenticated users
        if self.request.user.is_authenticated:
            context["projects"] = Project.objects.filter(
                profile=self.request.user.profile
            ).order_by('-created_at')

        return context


class UserSettingsView(LoginRequiredMixin, SuccessMessageMixin, UpdateView):
    login_url = "account_login"
    model = Profile
    form_class = ProfileUpdateForm
    success_message = "User Profile Updated"
    success_url = reverse_lazy("settings")
    template_name = "pages/user-settings.html"

    def get_object(self):
        return self.request.user.profile

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        user = self.request.user

        email_address = EmailAddress.objects.get_for_user(user, user.email)
        context["email_verified"] = email_address.verified
        context["resend_confirmation_url"] = reverse("resend_confirmation")
        context["has_subscription"] = user.profile.subscription is not None

        return context


@login_required
def resend_confirmation_email(request):
    user = request.user
    send_email_confirmation(request, user, EmailAddress.objects.get_for_user(user, user.email))

    return redirect("settings")


class PricingView(TemplateView):
    template_name = "pages/pricing.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context["has_pro_subscription"] = check_if_profile_has_pro_subscription(profile.id)
            except Profile.DoesNotExist:
                context["has_pro_subscription"] = False
        else:
            context["has_pro_subscription"] = False

        return context


def create_checkout_session(request, pk, plan):
    user = request.user

    product = djstripe_models.Product.objects.get(name=plan)
    price = product.prices.filter(active=True).first()
    customer, _ = djstripe_models.Customer.get_or_create(subscriber=user)

    profile = user.profile
    profile.customer = customer
    profile.save(update_fields=["customer"])

    base_success_url = request.build_absolute_uri(reverse("home"))
    base_cancel_url = request.build_absolute_uri(reverse("home"))

    success_params = {"payment": "success"}
    success_url = f"{base_success_url}?{urlencode(success_params)}"

    cancel_params = {"payment": "failed"}
    cancel_url = f"{base_cancel_url}?{urlencode(cancel_params)}"

    checkout_session = stripe.checkout.Session.create(
        customer=customer.id,
        payment_method_types=["card"],
        allow_promotion_codes=True,
        automatic_tax={"enabled": True},
        line_items=[
            {
                "price": price.id,
                "quantity": 1,
            }
        ],
        mode="subscription" if plan != "one-time" else "payment",
        success_url=success_url,
        cancel_url=cancel_url,
        customer_update={
            "address": "auto",
        },
        metadata={"user_id": user.id, "pk": pk, "price_id": price.id},
    )

    return redirect(checkout_session.url, code=303)


@login_required
def create_customer_portal_session(request):
    user = request.user
    customer = djstripe_models.Customer.objects.get(subscriber=user)

    session = stripe.billing_portal.Session.create(
        customer=customer.id,
        return_url=request.build_absolute_uri(reverse("home")),
    )

    return redirect(session.url, code=303)


class BlogView(ListView):
    model = BlogPost
    template_name = "blog/blog_posts.html"
    context_object_name = "blog_posts"


class BlogPostView(DetailView):
    model = BlogPost
    template_name = "blog/blog_post.html"
    context_object_name = "blog_post"


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "project/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        # Ensure users can only see their own projects
        return Project.objects.filter(profile=self.request.user.profile)


@login_required
@require_POST
def generate_blog_content(request, suggestion_id):
    suggestion = BlogPostTitleSuggestion.objects.get(id=suggestion_id)

    # Create a placeholder GeneratedBlogPost
    generated_post = GeneratedBlogPost.objects.create(
        project=suggestion.project,
        title=suggestion,
        slug=slugify(suggestion.title),
        description=suggestion.description,
        tags="",  # Will be populated by the task
        content=""  # Will be populated by the task
    )

    # Queue the content generation task
    async_task(
        'core.tasks.generate_blog_content_task',
        generated_post.id,
        suggestion.title,
        suggestion.project,
        task_name=f"Generate blog content for {suggestion.title}"
    )

    return JsonResponse({
        'status': 'success',
        'redirect_url': reverse('project_detail', kwargs={'pk': suggestion.project.id})
    })

@login_required
def check_content_status(request, suggestion_id):
    suggestion = get_object_or_404(
        BlogPostTitleSuggestion,
        id=suggestion_id,
        project__profile=request.user.profile
    )
    generated_post = suggestion.generated_blog_posts.first()

    if not generated_post:
        return JsonResponse({
            "is_generated": False,
            "content": None,
            "slug": None,
            "tags": None,
            "description": None
        })

    return JsonResponse({
        "is_generated": bool(generated_post.content),
        "content": generated_post.content if generated_post.content else None,
        "slug": generated_post.slug if generated_post.slug else None,
        "tags": generated_post.tags if generated_post.tags else None,
        "description": generated_post.description if generated_post.description else None
    }, json_dumps_params={"ensure_ascii": False})
