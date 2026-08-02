from django.apps import AppConfig


class AccountsConfig(AppConfig):
    name = "accounts"

    def ready(self):
        # Register drf-spectacular's adapter for the custom CSRF auth class.
        from . import schema  # noqa: F401
