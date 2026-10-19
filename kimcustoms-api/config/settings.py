import os

from dotenv import load_dotenv

load_dotenv()

from pathlib import Path
from django.core.exceptions import ImproperlyConfigured

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent


# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/6.1/howto/deployment/checklist/

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv(
    "SECRET_KEY",
    "unsafe-development-key",
)

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = os.getenv(
    "DEBUG",
    "False",
).lower() == "true"

if not DEBUG and SECRET_KEY == "unsafe-development-key":
    raise ImproperlyConfigured(
        "SECRET_KEY must be set when DEBUG is False."
    )

ALLOWED_HOSTS = [
    host.strip()
    for host in os.getenv("ALLOWED_HOSTS", "localhost,127.0.0.1").split(",")
    if host.strip()
]


# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    "corsheaders",
    "rest_framework",

    "products",
    "customers",
    "orders",
    "payments",

    
]

MIDDLEWARE = [
    "corsheaders.middleware.CorsMiddleware",

    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'config.wsgi.application'


# Database
# https://docs.djangoproject.com/en/6.1/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": os.getenv("DB_NAME"),
        "USER": os.getenv("DB_USER"),
        "PASSWORD": os.getenv("DB_PASSWORD"),
        "HOST": os.getenv("DB_HOST", "127.0.0.1"),
        "PORT": os.getenv("DB_PORT", "5432"),
    }
}
# Password validation
# https://docs.djangoproject.com/en/6.1/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/6.1/topics/i18n/

LANGUAGE_CODE = 'en-us'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_TZ = True


# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/6.1/howto/static-files/

STATIC_URL = 'static/'
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"



# Email
# https://docs.djangoproject.com/en/6.1/topics/email/#topic-email-configuration

MAILERS = {
    'default': {
        'BACKEND': os.getenv(
            "EMAIL_BACKEND",
            "django.core.mail.backends.smtp.EmailBackend",
        ),
    },
}

CORS_ALLOWED_ORIGINS = [
    origin.strip()
    for origin in os.getenv(
        "CORS_ALLOWED_ORIGINS",
        "http://localhost:3000,http://127.0.0.1:3000",
    ).split(",")
    if origin.strip()
]

# Keep the browser API boundary explicit.  A permissive CORS policy would let
# any website drive checkout and spend a payment-initiation token it obtains.
CORS_ALLOW_ALL_ORIGINS = False

if not DEBUG:
    # These defaults presume production traffic is HTTPS. Set HSTS only after
    # the public domain is known to be HTTPS-only; it is deliberately
    # configurable for staged rollouts.
    SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "true").lower() == "true"
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_REFERRER_POLICY = "same-origin"
    X_FRAME_OPTIONS = "DENY"
    SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    if os.getenv("SECURE_PROXY_SSL_HEADER", "false").lower() == "true":
        SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

MPESA_CALLBACK_MAX_BYTES = int(os.getenv("MPESA_CALLBACK_MAX_BYTES", "65536"))
MPESA_INITIATION_TOKEN_TTL_SECONDS = int(
    os.getenv("MPESA_INITIATION_TOKEN_TTL_SECONDS", "1800")
)

REST_FRAMEWORK = {
    "DEFAULT_THROTTLE_RATES": {
        "mpesa_stk_push": os.getenv("MPESA_STK_PUSH_RATE", "5/min"),
    },
}


# M-Pesa Daraja. Keep credentials in the environment; this project deliberately
# provides no defaults so a missing configuration cannot send a real request.
MPESA_DARAJA = {
    "consumer_key": os.getenv("MPESA_CONSUMER_KEY", ""),
    "consumer_secret": os.getenv("MPESA_CONSUMER_SECRET", ""),
    "shortcode": os.getenv("MPESA_SHORTCODE", ""),
    "passkey": os.getenv("MPESA_PASSKEY", ""),
    "callback_url": os.getenv("MPESA_CALLBACK_URL", ""),
    "oauth_url": os.getenv(
        "MPESA_OAUTH_URL",
        "https://sandbox.safaricom.co.ke/oauth/v1/generate?grant_type=client_credentials",
    ),
    "stk_push_url": os.getenv(
        "MPESA_STK_PUSH_URL",
        "https://sandbox.safaricom.co.ke/mpesa/stkpush/v1/processrequest",
    ),
    "transaction_type": os.getenv(
        "MPESA_TRANSACTION_TYPE",
        "CustomerPayBillOnline",
    ),
    "timeout_seconds": int(os.getenv("MPESA_TIMEOUT_SECONDS", "15")),
}
