from djstripe import webhooks
from djstripe.models import Customer, Event, Subscription

from core.models import Profile, ProfileStates
from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)


@webhooks.handler("customer.subscription.created")
def handle_created_subscription(**kwargs):
    event_id = kwargs["event"].id
    event = Event.objects.get(id=event_id)

    customer = Customer.objects.get(id=event.data["object"]["customer"])
    subscription = Subscription.objects.get(id=event.data["object"]["id"])

    profile = Profile.objects.get(customer=customer)
    profile.subscription = subscription
    profile.save(update_fields=["subscription"])

    profile.track_state_change(
        to_state=ProfileStates.SUBSCRIBED,
        metadata={"event": "subscription_created", "subscription_id": subscription.id, "stripe_event_id": event_id},
    )

    logger.info(
        "Subscription created and state updated for profile",
        profile_id=profile.id,
        webhook="handle_created_subscription",
        subscription_id=subscription.id,
        event_id=event_id,
    )


@webhooks.handler("customer.subscription.updated")
def handle_updated_subscription(**kwargs):
    event_id = kwargs["event"].id
    event = Event.objects.get(id=event_id)

    subscription_data = event.data["object"]

    customer_id = subscription_data["customer"]
    subscription_id = subscription_data["id"]

    logger.info(
        "Subscription updated",
        webhook="handle_updated_subscription",
        event_id=event_id,
        subscription_id=subscription_id,
        subscription_data=subscription_data,
    )

    try:
        customer = Customer.objects.get(id=customer_id)
        subscription = Subscription.objects.get(id=subscription_id)
        profile = Profile.objects.get(customer=customer)

        if (
            subscription_data.get("cancel_at_period_end")
            and subscription_data.get("cancellation_details", {}).get("reason") == "cancellation_requested"
        ):
            # The subscription has been cancelled and will end at the end of the current period
            profile.track_state_change(
                to_state=ProfileStates.CANCELLED,
                metadata={
                    "event": "subscription_cancelled",
                    "subscription_id": subscription_id,
                    "cancel_at": subscription_data.get("cancel_at"),
                    "current_period_end": subscription_data.get("current_period_end"),
                    "cancellation_feedback": subscription_data.get("cancellation_details", {}).get("feedback"),
                    "cancellation_comment": subscription_data.get("cancellation_details", {}).get("comment"),
                },
            )

            logger.info(
                "Subscription cancelled for profile.",
                profile_id=profile.id,
                subscription_id=subscription_id,
                end_date=subscription_data.get("current_period_end"),
            )

        profile.subscription = subscription
        profile.save(update_fields=["subscription"])

    except (Customer.DoesNotExist, Subscription.DoesNotExist, Profile.DoesNotExist) as e:
        logger.error(
            "Error processing subscription update",
            event_id=event_id,
            subscription_id=subscription_id,
            customer_id=customer_id,
            error=str(e),
        )


@webhooks.handler("customer.subscription.deleted")
def handle_deleted_subscription(**kwargs):
    event_id = kwargs["event"].id
    event = Event.objects.get(id=event_id)

    subscription_data = event.data["object"]
    customer_id = subscription_data["customer"]
    subscription_id = subscription_data["id"]

    logger.info(
        "Subscription deleted event received",
        webhook="handle_deleted_subscription",
        event_id=event_id,
        subscription_id=subscription_id,
        subscription_data=subscription_data,
    )

    try:
        customer = Customer.objects.get(id=customer_id)
        profile = Profile.objects.get(customer=customer)

        profile.track_state_change(
            to_state=ProfileStates.CHURNED,
            metadata={
                "event": "subscription_deleted",
                "subscription_id": subscription_id,
                "ended_at": subscription_data.get("ended_at"),
            },
        )

        profile.subscription = None
        profile.save(update_fields=["subscription"])

        logger.info(
            "Subscription deleted for profile.",
            profile_id=profile.id,
            subscription_id=subscription_id,
            ended_at=subscription_data.get("ended_at"),
        )

        # TODO: Implement any necessary clean-up or follow-up actions
        # For example: Revoke access to paid features, send a farewell email, etc.

    except (Customer.DoesNotExist, Profile.DoesNotExist) as e:
        logger.error(
            "Error processing subscription deletion",
            event_id=event_id,
            subscription_id=subscription_id,
            customer_id=customer_id,
            error=str(e),
        )
