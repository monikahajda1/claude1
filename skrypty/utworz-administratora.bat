@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Tworzenie konta administratora.
echo Podaj login, e-mail (można pominąć klawiszem Enter) i dwa razy hasło.
echo Uwaga: podczas wpisywania hasła NIC się nie wyświetla – to normalne.
echo.
docker compose exec web python manage.py createsuperuser
pause
