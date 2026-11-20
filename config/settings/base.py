from pathlib import Path

import environ


BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env("DJANGO_SECRET_KEY")

DEBUG = env("DEBUG")

ALLOWED_HOSTS = env.list(
    "ALLOWED_HOSTS",
    default=[],
)

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",

    "apps.core",
    "apps.accounts",
    "apps.organization",
    "apps.tickets",
    "apps.digest",
    "apps.forms",
    "apps.contacts",
    "apps.access",
    "apps.notifications",
    "apps.audit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "apps.accounts.middleware.LoginRequiredMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.core.context_processors.portal_permissions",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "apps.accounts.backends.EmailBackend",
]

DATABASES = {
    "default": env.db("DATABASE_URL"),
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "UserAttributeSimilarityValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "MinimumLengthValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "CommonPasswordValidator"
        ),
    },
    {
        "NAME": (
            "django.contrib.auth.password_validation."
            "NumericPasswordValidator"
        ),
    },
]

LANGUAGE_CODE = "ru-ru"

TIME_ZONE = "Europe/Moscow"

USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"

STATICFILES_DIRS = [
    BASE_DIR / "static",
]

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

LOGIN_URL = "login"
LOGIN_REDIRECT_URL = "home"
LOGOUT_REDIRECT_URL = "login"

SESSION_COOKIE_AGE = 60 * 60 * 8
SESSION_SAVE_EVERY_REQUEST = False
SESSION_EXPIRE_AT_BROWSER_CLOSE = True

SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"

CSRF_COOKIE_SAMESITE = "Lax"

EMAIL_BACKEND = env(
    "EMAIL_BACKEND",
    default="django.core.mail.backends.console.EmailBackend",
)

EMAIL_HOST = env("EMAIL_HOST", default="")
EMAIL_PORT = env.int("EMAIL_PORT", default=587)

EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")

EMAIL_USE_TLS = env.bool("EMAIL_USE_TLS", default=True)
EMAIL_USE_SSL = env.bool("EMAIL_USE_SSL", default=False)

EMAIL_TIMEOUT = env.int("EMAIL_TIMEOUT", default=15)

DEFAULT_FROM_EMAIL = env(
    "DEFAULT_FROM_EMAIL",
    default="Leovit Portal <cpservice@leovit.ru>",
)

PRIVATE_UPLOAD_ROOT = (
    BASE_DIR / "private_uploads"
)

TICKET_ATTACHMENT_MAX_SIZE = 10 * 1024 * 1024
TICKET_ATTACHMENT_MAX_COUNT = 10

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "django_cache",
    },
}

# Exchange ActiveSync

ACTIVESYNC_URL = env(
    "ACTIVESYNC_URL",
    default=(
        "https://mail.leovit.ru"
        "/Microsoft-Server-ActiveSync"
    ),
)

ACTIVESYNC_USERNAME = env(
    "ACTIVESYNC_USERNAME",
    default="",
)

ACTIVESYNC_PASSWORD = env(
    "ACTIVESYNC_PASSWORD",
    default="",
)

ACTIVESYNC_SENDER_EMAIL = env(
    "ACTIVESYNC_SENDER_EMAIL",
    default="cpservice@leovit.ru",
)

ACTIVESYNC_PROTOCOL_VERSION = env(
    "ACTIVESYNC_PROTOCOL_VERSION",
    default="12.1",
)

ACTIVESYNC_DEVICE_ID = env(
    "ACTIVESYNC_DEVICE_ID",
    default="LeovitPortal001",
)

ACTIVESYNC_DEVICE_TYPE = env(
    "ACTIVESYNC_DEVICE_TYPE",
    default="LeovitPortal",
)

ACTIVESYNC_TIMEOUT = env.int(
    "ACTIVESYNC_TIMEOUT",
    default=30,
)

ACTIVESYNC_SAVE_IN_SENT = env.bool(
    "ACTIVESYNC_SAVE_IN_SENT",
    default=False,
)

# ============================================================
# Password reset security
# ============================================================

PASSWORD_RESET_SECRET_KEY = env(
    "PASSWORD_RESET_SECRET_KEY",
    default="",
)

PASSWORD_RESET_TRUSTED_PROXY_NETWORKS = env.list(
    "PASSWORD_RESET_TRUSTED_PROXY_NETWORKS",
    default=[],
)

PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_IP = env.int(
    "PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_IP",
    default=100,
)

PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_EMAIL = env.int(
    "PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_EMAIL",
    default=15,
)

# ============================================================
# Password reset cleanup
# ============================================================

PASSWORD_RESET_CODE_RETENTION_DAYS = env.int(
    "PASSWORD_RESET_CODE_RETENTION_DAYS",
    default=7,
)

PASSWORD_RESET_RATE_LIMIT_RETENTION_HOURS = env.int(
    "PASSWORD_RESET_RATE_LIMIT_RETENTION_HOURS",
    default=24,
)

PASSWORD_RESET_CLEANUP_BATCH_SIZE = env.int(
    "PASSWORD_RESET_CLEANUP_BATCH_SIZE",
    default=1000,
)
