from django.conf import settings
from drf_spectacular.extensions import OpenApiAuthenticationExtension


class CsrfProtectedSessionScheme(OpenApiAuthenticationExtension):
    target_class = "accounts.views.CsrfProtectedSessionAuthentication"
    name = ["csrfCookie", "csrfHeader"]

    def get_security_definition(self, auto_schema):
        return [
            {
                "type": "apiKey",
                "in": "cookie",
                "name": settings.CSRF_COOKIE_NAME,
                "description": "First fetch GET /api/auth/csrf to set this cookie.",
            },
            {
                "type": "apiKey",
                "in": "header",
                "name": "X-CSRFToken",
                "description": "Send the same token value returned in the CSRF cookie.",
            },
        ]
