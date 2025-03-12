from django.urls import path

from core import views
from core.api.views import api

urlpatterns = [
    # pages
    path("", views.HomeView.as_view(), name="home"),
    path("settings", views.UserSettingsView.as_view(), name="settings"),
    # blog
    path("blog", views.BlogView.as_view(), name="blog_posts"),
    path("blog/<slug:slug>", views.BlogPostView.as_view(), name="blog_post"),
    # app
    path("api/", api.urls),
    path("project/<int:pk>/", views.ProjectDetailView.as_view(), name="project_detail"),
    path("blogging-agent/<int:pk>/", views.BloggingAgentDetailView.as_view(), name="blogging_agent_detail"),
    path("pricing-agent/<int:pk>/", views.PricingAgentView.as_view(), name="pricing_agent"),
    # utils
    path("resend-confirmation/", views.resend_confirmation_email, name="resend_confirmation"),
    # payments
    path("pricing", views.PricingView.as_view(), name="pricing"),
    path(
        "create-checkout-session/<int:pk>/<str:plan>/",
        views.create_checkout_session,
        name="user_upgrade_checkout_session",
    ),
    path("create-customer-portal/", views.create_customer_portal_session, name="create_customer_portal_session"),
    # Add these with your other URLs
    path("tools/", views.ToolsView.as_view(), name="tools"),
    path("sam-parr-roasts-your-page", views.PageRoastView.as_view(), name="sam_parr_page_roast"),
]
