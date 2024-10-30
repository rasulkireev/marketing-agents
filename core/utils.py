from django.forms.utils import ErrorList

from core.models import Profile

from seo_blog_bot.utils import get_seo_blog_bot_logger

logger = get_seo_blog_bot_logger(__name__)


class DivErrorList(ErrorList):
    def __str__(self):
        return self.as_divs()

    def as_divs(self):
        if not self:
            return ""
        return f"""
            <div class="p-4 my-4 bg-red-50 rounded-md border border-red-600 border-solid">
              <div class="flex">
                <div class="flex-shrink-0">
                  <!-- Heroicon name: solid/x-circle -->
                  <svg class="w-5 h-5 text-red-400" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 20 20" fill="currentColor" aria-hidden="true"> # noqa: E501
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" /> # noqa: E501
                  </svg>
                </div>
                <div class="ml-3 text-sm text-red-700">
                      {''.join([f'<p>{e}</p>' for e in self])}
                </div>
              </div>
            </div>
         """

def check_if_profile_has_pro_subscription(profile_id):
    has_pro_subscription = False
    if profile_id:
        try:
            profile = Profile.objects.get(id=profile_id)
            has_pro_subscription = profile.subscription is not None
        except Profile.DoesNotExist:
            logger.error("Profile does not exist", profile_id=profile_id)

    return has_pro_subscription

