from urllib.parse import urlencode

import stripe
from allauth.account.models import EmailAddress
from allauth.account.utils import send_email_confirmation
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib.messages.views import SuccessMessageMixin
from django.shortcuts import redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, ListView, TemplateView, UpdateView
from djstripe import models as djstripe_models

from core.choices import BlogPostStatus, Language, ProfileStates, ProjectPageType
from core.forms import AutoSubmittionSettingForm, ProfileUpdateForm, ProjectScanForm
from core.models import (
    AutoSubmittionSetting,
    BlogPost,
    Competitor,
    PricingPageUpdatesSuggestion,
    Profile,
    Project,
    ProjectKeyword,
    ProjectPage,
)
from seo_blog_bot.utils import get_seo_blog_bot_logger

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
            projects = Project.objects.filter(profile=self.request.user.profile).order_by("-created_at")

            # Annotate projects with counts
            projects_with_stats = []
            for project in projects:
                project_stats = {
                    "project": project,
                }
                projects_with_stats.append(project_stats)

            context["projects"] = projects_with_stats

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
        context["has_subscription"] = user.profile.has_product_or_subscription

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
        number_of_subscribed_users = Profile.objects.filter(state=ProfileStates.SUBSCRIBED).count()

        if self.request.user.is_authenticated:
            try:
                profile = self.request.user.profile
                context["has_pro_subscription"] = profile.has_product_or_subscription
            except Profile.DoesNotExist:
                context["has_pro_subscription"] = False
        else:
            context["has_pro_subscription"] = False

        context["early_bird_spots_left"] = 20 - number_of_subscribed_users - 1

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
        mode="payment" if "one-time" in plan else "subscription",
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

    def get_queryset(self):
        return BlogPost.objects.filter(status=BlogPostStatus.PUBLISHED)


class ProjectDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "project/project_detail.html"
    context_object_name = "project"

    def get_queryset(self):
        # Ensure users can only see their own projects
        return Project.objects.filter(profile=self.request.user.profile)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["has_content_access"] = self.request.user.profile.has_active_subscription
        context["has_pricing_page"] = self.object.has_pricing_page
        return context


class ProjectSettingsView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "project/project_settings.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        project = self.object
        # Try to get existing settings for this project
        settings = AutoSubmittionSetting.objects.filter(project=project).first()
        if settings:
            form = AutoSubmittionSettingForm(instance=settings)
        else:
            form = AutoSubmittionSettingForm()
        context["auto_submittion_settings_form"] = form
        context["languages"] = Language.choices
        return context

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        project = self.object
        settings = AutoSubmittionSetting.objects.filter(project=project).first()
        if settings:
            form = AutoSubmittionSettingForm(request.POST, instance=settings)
        else:
            form = AutoSubmittionSettingForm(request.POST)
        if form.is_valid():
            auto_settings = form.save(commit=False)
            auto_settings.project = project
            auto_settings.save()
            messages.success(request, "Automatic submission settings saved.")
            return redirect("project_settings", pk=project.pk)
        else:
            context = self.get_context_data()
            context["auto_submittion_settings_form"] = form
            return self.render_to_response(context)


class BloggingAgentDetailView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "agents/blogging-agent.html"
    context_object_name = "project"


class KeywordsAgentView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "agents/keywords-agent.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)

        # Fetch all ProjectKeyword objects for this project, select_related to avoid N+1
        # Order by most recent first (assuming 'created' field, fallback to '-id')
        project_keywords = (
            ProjectKeyword.objects.filter(project=self.object)
            .select_related("keyword")
            .order_by("-id")  # Change to '-created' if a 'created' field exists
        )

        processed_keywords = []
        for pk in project_keywords:
            keyword_obj = pk.keyword
            # Extract the 'value', 'month', and 'year' from each trend object.
            keyword_obj.trend_data = [
                {"value": trend.value, "month": trend.month, "year": trend.year} for trend in keyword_obj.trends.all()
            ]
            # Attach the 'use' field from ProjectKeyword
            keyword_obj.use = pk.use
            processed_keywords.append(keyword_obj)

        context["keywords"] = processed_keywords

        return context


class PricingAgentView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "agents/pricing-agent.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        pricing_pages = ProjectPage.objects.filter(project=self.object, type=ProjectPageType.PRICING)
        pricing_suggestions = PricingPageUpdatesSuggestion.objects.filter(
            project=self.object,
        )

        context = super().get_context_data(**kwargs)
        context["has_pro_subscription"] = self.request.user.profile.has_product_or_subscription

        if pricing_pages.exists():
            context["pricing_page"] = pricing_pages.latest("id")
        else:
            context["pricing_page"] = None

        if pricing_suggestions.exists():
            context["pricing_suggestions"] = pricing_suggestions
        else:
            context["pricing_suggestions"] = None

        return context


class CompetitorAnalysisAgentView(LoginRequiredMixin, DetailView):
    model = Project
    template_name = "agents/competitor-analysis-agent.html"
    context_object_name = "project"

    def get_context_data(self, **kwargs):
        competitors = Competitor.objects.filter(
            project=self.object,
        ).exclude(markdown_content="")

        context = super().get_context_data(**kwargs)
        context["has_pro_subscription"] = self.request.user.profile.has_product_or_subscription

        if competitors.exists():
            context["competitors"] = competitors
        else:
            context["competitors"] = None

        return context
