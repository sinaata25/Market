"""
تنظیمات جنگو برای بک‌اند فروشگاه «ابزار سبز»
"""

import math
import os
import re
from pathlib import Path

import dj_database_url
from django.core.exceptions import ImproperlyConfigured
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# متغیرهای محیطی از backend/.env خوانده می‌شوند.
# utf-8-sig علامت BOM برخی ویرایشگرهای ویندوز را هم به‌درستی حذف می‌کند.
load_dotenv(BASE_DIR / ".env", encoding="utf-8-sig")


def env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name)
    if raw_value is None:
        return default
    value = raw_value.strip().lower()
    if value in {"1", "true", "yes", "on"}:
        return True
    if value in {"0", "false", "no", "off"}:
        return False
    raise ImproperlyConfigured(
        f"{name} must be one of true/false, yes/no, on/off, or 1/0"
    )


def env_int(
    name: str, default: int, *, minimum: int = 1, maximum: int | None = None
) -> int:
    try:
        value = int(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be an integer") from exc
    if value < minimum:
        raise ImproperlyConfigured(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ImproperlyConfigured(f"{name} must be at most {maximum}")
    return value


def env_float(
    name: str,
    default: float,
    *,
    minimum: float = 0.1,
    maximum: float | None = None,
) -> float:
    try:
        value = float(os.getenv(name, str(default)))
    except ValueError as exc:
        raise ImproperlyConfigured(f"{name} must be a number") from exc
    if not math.isfinite(value):
        raise ImproperlyConfigured(f"{name} must be a finite number")
    if value < minimum:
        raise ImproperlyConfigured(f"{name} must be at least {minimum}")
    if maximum is not None and value > maximum:
        raise ImproperlyConfigured(f"{name} must be at most {maximum}")
    return value

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-dev-only-change-me",
)

if os.getenv("DJANGO_DEBUG") is not None:
    DEBUG = env_bool("DJANGO_DEBUG")
else:
    # Backward-compatible fallback. Prefer the namespaced setting because
    # generic DEBUG is commonly injected by shells, IDEs, and process managers.
    DEBUG = env_bool("DEBUG", True)

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]

if not DEBUG and SECRET_KEY in {
    "django-insecure-dev-only-change-me",
    "a-long-random-secret",
    "replace-with-a-long-random-secret",
}:
    raise ImproperlyConfigured("SECRET_KEY must be set when DEBUG is false")
if not DEBUG and (len(SECRET_KEY) < 50 or len(set(SECRET_KEY)) < 5):
    raise ImproperlyConfigured(
        "SECRET_KEY must contain at least 50 characters with sufficient variety"
    )

# فرانت Next.js درخواست‌ها را پروکسی می‌کند؛ این originها برای CSRF مجازند
CSRF_TRUSTED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CSRF_TRUSTED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000,"
        "http://localhost:8000,http://127.0.0.1:8000",
    ).split(",")
    if origin.strip()
]

# ─── اپلیکیشن‌ها ─────────────────────────────────────────────

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    # شخص ثالث
    "rest_framework",
    "drf_spectacular",
    # اپ‌های پروژه
    "accounts",
    "catalog",
    "carts",
    "orders",
    "adminapi",
    "seo",
    "blog",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# ─── دیتابیس ─────────────────────────────────────────────────
# SQLite فقط برای توسعه است. ورود OTP در استقرار به قفل سطری PostgreSQL متکی است.
DATABASE_URL = os.getenv("DATABASE_URL", "").strip()
if DATABASE_URL:
    try:
        default_database = dj_database_url.parse(
            DATABASE_URL,
            conn_max_age=60,
            conn_health_checks=True,
        )
    except (ValueError, KeyError) as exc:
        raise ImproperlyConfigured("DATABASE_URL is invalid") from exc
    DATABASES = {"default": default_database}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

if not DEBUG and DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":
    raise ImproperlyConfigured(
        "Production OTP authentication requires a PostgreSQL DATABASE_URL"
    )

# ─── احراز هویت ──────────────────────────────────────────────

AUTH_USER_MODEL = "accounts.User"

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# سشن ۳۰ روزه (مطابق رفتار قبلی فروشگاه)
SESSION_COOKIE_AGE = 30 * 24 * 60 * 60
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
# در حالت توسعه روی http هستیم؛ در استقرار https اجباری می‌شود
SESSION_COOKIE_SECURE = not DEBUG
CSRF_COOKIE_SECURE = not DEBUG
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_SSL_REDIRECT = env_bool("SECURE_SSL_REDIRECT", not DEBUG)
SECURE_HSTS_SECONDS = env_int(
    "SECURE_HSTS_SECONDS", 31_536_000 if not DEBUG else 0, minimum=0
)
SECURE_HSTS_INCLUDE_SUBDOMAINS = env_bool(
    "SECURE_HSTS_INCLUDE_SUBDOMAINS", not DEBUG
)
SECURE_HSTS_PRELOAD = env_bool("SECURE_HSTS_PRELOAD", not DEBUG)

# OTP throttles must be shared by every production worker/replica. Redis also
# gives the fixed-window limiter atomic add/increment operations.
REDIS_URL = os.getenv("REDIS_URL", "").strip()
OTP_REQUIRE_SHARED_CACHE = env_bool("OTP_REQUIRE_SHARED_CACHE", False)
if (not DEBUG or OTP_REQUIRE_SHARED_CACHE) and not REDIS_URL:
    raise ImproperlyConfigured(
        "REDIS_URL is required for shared production OTP rate limits"
    )
if REDIS_URL:
    CACHES = {
        "default": {
            "BACKEND": "django.core.cache.backends.redis.RedisCache",
            "LOCATION": REDIS_URL,
            "KEY_PREFIX": os.getenv("CACHE_KEY_PREFIX", "market"),
            "TIMEOUT": 3600,
            "OPTIONS": {
                "socket_connect_timeout": 2,
                "socket_timeout": 2,
            },
        }
    }

# ─── DRF ─────────────────────────────────────────────────────

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.SessionAuthentication",
    ],
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.AllowAny",
    ],
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # همه‌ی خطاها با قالب یکسان {ok: false, error: "..."} برگردند
    "EXCEPTION_HANDLER": "common.responses.api_exception_handler",
    # 0 ignores client-supplied X-Forwarded-For. Set this to the exact number
    # only behind an ingress that strips/rebuilds the header and blocks direct
    # access. The bundled Next.js rewrite is not itself such a trust boundary.
    "NUM_PROXIES": env_int("TRUSTED_PROXY_COUNT", 0, minimum=0, maximum=10),
    "DEFAULT_THROTTLE_RATES": {
        # محدودیت IP مانع پمپ پیامک به شماره‌های مختلف می‌شود.
        "otp_send_ip": os.getenv("OTP_SEND_IP_RATE", "30/hour"),
        "otp_send_phone": os.getenv("OTP_SEND_PHONE_RATE", "5/hour"),
        "otp_verify_ip": os.getenv("OTP_VERIFY_IP_RATE", "100/hour"),
        "otp_verify_phone": os.getenv("OTP_VERIFY_PHONE_RATE", "20/hour"),
    },
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Green Tools Store API",
    "DESCRIPTION": "OpenAPI documentation for the store backend.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# ─── بین‌المللی‌سازی ─────────────────────────────────────────

LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# فایل‌های آپلودی (تصاویر محصولات و آیکن‌های دسته‌بندی)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── تنظیمات فروشگاه ─────────────────────────────────────────

SHOP = {
    "OTP_LENGTH": env_int("OTP_LENGTH", 4, minimum=4, maximum=10),
    "OTP_TTL_SECONDS": env_int(
        "OTP_TTL_SECONDS", 300, minimum=60, maximum=600
    ),
    "OTP_RESEND_COOLDOWN_SECONDS": env_int(
        "OTP_RESEND_COOLDOWN_SECONDS", 60, minimum=40
    ),
    "OTP_MAX_ATTEMPTS": env_int(
        "OTP_MAX_ATTEMPTS", 5, minimum=3, maximum=10
    ),
    "OTP_RETENTION_DAYS": env_int(
        "OTP_RETENTION_DAYS", 7, minimum=1, maximum=30
    ),
    "SHIPPING_PRICE": 60_000,  # تومان
    "FREE_SHIPPING_THRESHOLD": 2_000_000,
}

if SHOP["OTP_TTL_SECONDS"] < SHOP["OTP_RESEND_COOLDOWN_SECONDS"]:
    raise ImproperlyConfigured(
        "OTP_TTL_SECONDS must be greater than or equal to "
        "OTP_RESEND_COOLDOWN_SECONDS"
    )
# ارسال OTP: در توسعه console و در استقرار ippanel.
# هیچ مسیر bypass یا بازگرداندن کد در API وجود ندارد.
_default_otp_backend = "console" if DEBUG else "ippanel"
OTP_SMS_BACKEND = os.getenv("OTP_SMS_BACKEND", _default_otp_backend).strip().lower()
if OTP_SMS_BACKEND not in {"console", "ippanel"}:
    raise ImproperlyConfigured("OTP_SMS_BACKEND must be 'console' or 'ippanel'")
if not DEBUG and OTP_SMS_BACKEND == "console":
    raise ImproperlyConfigured(
        "OTP_SMS_BACKEND=console is only allowed when DJANGO_DEBUG=true"
    )

IPPANEL = {
    "BASE_URL": os.getenv("IPPANEL_BASE_URL", "https://edge.ippanel.com/v1").rstrip(
        "/"
    ),
    "API_KEY": os.getenv("IPPANEL_API_KEY", "").strip(),
    "FROM_NUMBER": os.getenv("IPPANEL_FROM_NUMBER", "").strip(),
    "PATTERN_CODE": os.getenv("IPPANEL_PATTERN_CODE", "").strip(),
    "OTP_PARAMETER": os.getenv("IPPANEL_OTP_PARAMETER", "otp_code").strip(),
    "CONNECT_TIMEOUT": env_float(
        "IPPANEL_CONNECT_TIMEOUT", 3.0, maximum=10.0
    ),
    "READ_TIMEOUT": env_float("IPPANEL_READ_TIMEOUT", 10.0, maximum=20.0),
}

if OTP_SMS_BACKEND == "ippanel":
    missing = [
        key
        for key in ("API_KEY", "FROM_NUMBER", "PATTERN_CODE", "OTP_PARAMETER")
        if not IPPANEL[key]
    ]
    if missing:
        names = ", ".join(f"IPPANEL_{key}" for key in missing)
        raise ImproperlyConfigured(f"Missing IPPanel configuration: {names}")
    if not IPPANEL["BASE_URL"].startswith("https://"):
        raise ImproperlyConfigured("IPPANEL_BASE_URL must use HTTPS")
    if not re.fullmatch(r"\+[1-9][0-9]{7,14}", IPPANEL["FROM_NUMBER"]):
        raise ImproperlyConfigured("IPPANEL_FROM_NUMBER must use E.164 format")
    if (
        IPPANEL["CONNECT_TIMEOUT"] + IPPANEL["READ_TIMEOUT"]
        >= SHOP["OTP_RESEND_COOLDOWN_SECONDS"]
    ):
        raise ImproperlyConfigured(
            "IPPanel timeouts must total less than OTP_RESEND_COOLDOWN_SECONDS"
        )
