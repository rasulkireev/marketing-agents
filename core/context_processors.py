def pro_subscription_status(request):
    """
    Adds a 'has_pro_subscription' variable to the context.
    This variable is True if the user has an active pro subscription, False otherwise.
    """
    if request.user.is_authenticated and hasattr(request.user, "profile"):
        return {"has_pro_subscription": request.user.profile.has_product_or_subscription}
    return {"has_pro_subscription": False}
