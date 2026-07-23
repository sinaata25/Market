"""
تنظیمات جنگو برای بک‌اند فروشگاه «ابزار سبز»
"""

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent

# متغیرهای محیطی از backend/.env خوانده می‌شوند
load_dotenv(BASE_DIR / ".env")

SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "django-insecure-dev-only-change-me",
)

DEBUG = os.getenv("DEBUG", "true").lower() == "true"

ALLOWED_HOSTS = os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")

# فرانت Next.js درخواست‌ها را پروکسی می‌کند؛ این originها برای CSRF مجازند
CSRF_TRUSTED_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
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
    # اپ‌های پروژه
    "accounts",
    "catalog",
    "carts",
    "orders",
    "adminapi",
    "seo",
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
# SQLite برای توسعه؛ در استقرار به PostgreSQL تغییر دهید

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": BASE_DIR / "db.sqlite3",
    }
}

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

# ─── DRF ─────────────────────────────────────────────────────

REST_FRAMEWORK = {
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
}

# ─── بین‌المللی‌سازی ─────────────────────────────────────────

LANGUAGE_CODE = "fa"
TIME_ZONE = "Asia/Tehran"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"

# فایل‌های آپلودی (تصاویر محصولات)
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ─── تنظیمات فروشگاه ─────────────────────────────────────────

SHOP = {
    "OTP_TTL_SECONDS": 120,
    "OTP_RESEND_COOLDOWN_SECONDS": 60,
    "OTP_MAX_ATTEMPTS": 5,
    "SHIPPING_PRICE": 60_000,  # تومان
    "FREE_SHIPPING_THRESHOLD": 2_000_000,
    # تا اتصال سرویس پیامک، کد OTP در پاسخ API برگردانده می‌شود
    "OTP_EXPOSE_DEV_CODE": DEBUG,
    # ⚠️ موقتی: ورود بدون کد پیامکی (فقط با شماره موبایل).
    # بعد از خرید پنل پیامکی، در .env مقدار OTP_BYPASS=false بگذارید.
    "OTP_BYPASS": os.getenv("OTP_BYPASS", "true").lower() == "true",
}
