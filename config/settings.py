"""
Django settings for the CS Sânandrei Timiș website.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: setați DJANGO_SECRET_KEY în producție!
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "django-insecure-dev-only-change-me-sanandrei")
DEBUG = os.environ.get("DJANGO_DEBUG", "1") == "1"
ALLOWED_HOSTS = [h for h in os.environ.get("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1,testserver").split(",") if h]

# Site static pe GitHub Pages: dacă site-ul e servit dintr-un subfolder (https://orsadi.github.io/Sanandrei/),
# toate linkurile primesc prefixul acesta. Pentru un domeniu propriu (ex. cssanandrei.ro) lăsați "/".
SITE_URL_PREFIX = "/" + os.environ.get("SITE_URL_PREFIX", "/").strip("/") + "/"
SITE_URL_PREFIX = SITE_URL_PREFIX.replace("//", "/")
if SITE_URL_PREFIX != "/":
    FORCE_SCRIPT_NAME = SITE_URL_PREFIX.rstrip("/")
SITE_DOMAIN = os.environ.get("SITE_DOMAIN", "")  # ex. "https://orsadi.github.io", folosit în sitemap

# Conținutul editat de club (știri, Primul 11, jucători, sponsori, produse, setări)
CONTENT_DIR = Path(os.environ.get("CONTENT_DIR", BASE_DIR / "content"))
# Cheia Web3Forms (gratuită, web3forms.com) – formularele de contact și comenzi ajung pe email
WEB3FORMS_KEY = os.environ.get("WEB3FORMS_KEY", "")


INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "core",
    "shop",
    "teams",
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
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "core.context_processors.club",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"


DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        # Baza de date cu datele de pe FRF; e salvată în repo de GitHub Action după fiecare sincronizare.
        "NAME": os.environ.get("DJANGO_DB", BASE_DIR / "data" / "frf.sqlite3"),
    }
}


AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]


LANGUAGE_CODE = "ro"
TIME_ZONE = "Europe/Bucharest"
USE_I18N = True
USE_TZ = True


STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"


# --- Clubul și competiția -------------------------------------------------
CLUB_NAME = "CS Sânandrei Timiș"
CLUB_SHORT_NAME = "Sânandrei"
OUR_TEAM_FRF_ID = 205
FRF_TEAM_URL = "https://www.frf-ajf.ro/timis/echipe/cs-snandrei-timi-205.html"
FRF_COMPETITION_URL = "https://www.frf-ajf.ro/timis/competitii-fotbal/liga-a-iv-a-16445"
COMPETITION_NAME = "Liga a IV-a Timiș"
SEASON = "2026/2027"
# Valorile de mai jos sunt implicite; clubul le schimbă din content/setari.yml (Pages CMS → Setări site).
CLUB_VENUE = "Stadionul Comunal, Sânandrei"
CLUB_EMAIL = os.environ.get("CLUB_EMAIL", "contact@cssanandrei.ro")
CLUB_PHONE = os.environ.get("CLUB_PHONE", "")
