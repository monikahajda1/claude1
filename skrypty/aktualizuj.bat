@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Pobieram najnowszą wersję aplikacji...
git pull
if errorlevel 1 (
  echo [!] Nie udało się pobrać zmian.
  pause
  exit /b 1
)
echo Przebudowuję i uruchamiam ponownie...
docker compose up -d --build
echo Gotowe. Odśwież stronę w przeglądarce.
pause
