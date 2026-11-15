#!/bin/sh
# Uruchamiane przy każdym starcie kontenera z aplikacją.
set -e

echo ">> Aktualizacja struktury bazy danych (migracje)..."
python manage.py migrate --noinput

echo ">> Przygotowanie plików wyglądu..."
python manage.py collectstatic --noinput >/dev/null

echo ">> Start aplikacji."
exec "$@"
