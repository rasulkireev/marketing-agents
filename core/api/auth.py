from typing import Optional

from django.http import HttpRequest
from ninja.security import HttpBearer

from core.models import Profile


class MultipleAuthSchema(HttpBearer):
    def authenticate(self, request: HttpRequest, token: Optional[str] = None) -> Optional[Profile]:
        # For session-based authentication (when using the web interface)
        if hasattr(request, "user") and request.user.is_authenticated:
            try:
                return request.user.profile
            except Profile.DoesNotExist:
                return None

        # For API token authentication (when using the API directly)
        if token:
            try:
                return Profile.objects.get(key=token)
            except Profile.DoesNotExist:
                return None

        return None

    def __call__(self, request):
        # Override to make authentication optional for session-based requests
        if hasattr(request, "user") and request.user.is_authenticated:
            return self.authenticate(request)

        return super().__call__(request)
