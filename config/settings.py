"""
Ustawienia aplikacji.

WAŻNE: żadnych haseł ani adresów nie wpisujemy tutaj na sztywno.
Wszystko, co zależy od miejsca uruchomienia (komputer w biurze / chmura),
czytamy ze zmiennych środowiskowych albo z pliku .env (wzór: .env.example).
"""

from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent

env = environ.Env()
# Plik .env jest opcjonalny – w Dockerze zmienne przychodzą z docker-compose.
environ.Env.read_env(BASE_DIR / ".env")

# --- Bezpieczeństwo ---------------------------------------------------------
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = env.bool("DJANGO_DEBUG", default=False)
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=["localhost", "127.0.0.1"])
# Adresy, z których można wysyłać formularze (np. adres Tailscale lub domena w chmurze).
CSRF_TRUSTED_ORIGINS = env.list("DJANGO_CSRF_TRUSTED_ORIGINS", default=[])

# Gdy aplikacja działa za HTTPS (Tailscale serve, chmura) – włącz w .env.
HTTPS = env.bool("DJANGO_HTTPS", default=False)
SESSION_COOKIE_SECURE = HTTPS
CSRF_COOKIE_SECURE = HTTPS
if HTTPS:
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_AGE = env.int("SESJA_SEKUNDY", default=60 * 60 * 12)  # 12 godzin
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# --- Aplikacje --------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "simple_history",
    "apps.core",
    "apps.konta",
    "apps.budowy",
    "apps.bhp",
    "apps.pulpit",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    # Zapamiętuje, KTO dokonał zmiany – potrzebne do dziennika zmian.
    "simple_history.middleware.HistoryRequestMiddleware",
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
                "apps.core.context_processors.uprawnienia",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# --- Baza danych (PostgreSQL) -------------------------------------------------
# Domyślnie składamy połączenie z POSTGRES_* (jak w docker-compose).
# W chmurze można zamiast tego podać jedną zmienną DATABASE_URL,
# np. postgres://uzytkownik:haslo@serwer:5432/posadzki
if env("DATABASE_URL", default=""):
    DATABASES = {"default": env.db("DATABASE_URL")}
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.postgresql",
            "NAME": env("POSTGRES_DB", default="posadzki"),
            "USER": env("POSTGRES_USER", default="posadzki"),
            "PASSWORD": env("POSTGRES_PASSWORD"),
            "HOST": env("POSTGRES_HOST", default="db"),
            "PORT": env.int("POSTGRES_PORT", default=5432),
        }
    }
DATABASES["default"]["CONN_MAX_AGE"] = 60

# --- Konta ------------------------------------------------------------------
AUTH_USER_MODEL = "konta.Uzytkownik"
LOGIN_URL = "konta:logowanie"
LOGIN_REDIRECT_URL = "pulpit:co_dzis"
LOGOUT_REDIRECT_URL = "konta:logowanie"

# Hasła są przechowywane jako bezpieczny skrót (PBKDF2) – nigdy otwartym tekstem.
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# --- Język i czas -------------------------------------------------------------
LANGUAGE_CODE = "pl"
TIME_ZONE = "Europe/Warsaw"
USE_I18N = True
USE_TZ = True

# --- Pliki statyczne (wygląd) i przesłane pliki (skany, zdjęcia) --------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
# Przesłane pliki NIE są publiczne – wydaje je widok sprawdzający uprawnienia.
MEDIA_ROOT = Path(env("MEDIA_ROOT", default=str(BASE_DIR / "media")))
MEDIA_URL = "/pliki/"
DATA_UPLOAD_MAX_MEMORY_SIZE = 20 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# --- Ustawienia biznesowe -----------------------------------------------------
NAZWA_APLIKACJI = env("NAZWA_APLIKACJI", default="Posadzki – Budowy")
# Ile dni przed wygaśnięciem dokumentu pokazywać ostrzeżenie (żółte) i alarm (czerwone).
ALERT_DNI_OSTRZEZENIE = env.int("ALERT_DNI_OSTRZEZENIE", default=30)
ALERT_DNI_PILNE = env.int("ALERT_DNI_PILNE", default=7)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"console": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["console"], "level": "INFO"},
}
