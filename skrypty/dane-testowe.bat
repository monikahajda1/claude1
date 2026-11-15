@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Wczytuję FIKCYJNE dane testowe (budowy, klienci, pracownicy, sprzęt) i konta demo...
docker compose exec web python manage.py dane_testowe --konta
pause
