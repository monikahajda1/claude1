@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Uruchamiam automatyczne testy aplikacji...
docker compose exec web python manage.py test
pause
