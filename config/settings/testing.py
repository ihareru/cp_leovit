from .base import *  # noqa: F401,F403

DEBUG = False

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

EMAIL_BACKEND = (
    "django.core.mail.backends.locmem.EmailBackend"
)

CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "password-reset-tests",
    },
}

PASSWORD_RESET_SECRET_KEY = "a1" * 32

PASSWORD_RESET_TRUSTED_PROXY_NETWORKS = []

PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_IP = 100

PASSWORD_RESET_MAX_CONFIRM_REQUESTS_PER_EMAIL = 15

PASSWORD_RESET_CODE_RETENTION_DAYS = 7

PASSWORD_RESET_RATE_LIMIT_RETENTION_HOURS = 24

PASSWORD_RESET_CLEANUP_BATCH_SIZE = 1000

ACTIVESYNC_SAVE_IN_SENT = False
