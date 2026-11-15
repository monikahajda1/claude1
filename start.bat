@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo   Uruchamianie aplikacji Posadzki - Budowy
echo ============================================

docker info >nul 2>&1
if errorlevel 1 (
  echo.
  echo [!] Docker nie działa. Uruchom program "Docker Desktop",
  echo     poczekaj, aż ikonka wieloryba przestanie się ruszać, i spróbuj ponownie.
  pause
  exit /b 1
)

if not exist ".env" (
  echo Pierwsze uruchomienie: tworzę plik ustawień .env z losowymi hasłami...
  powershell -NoProfile -ExecutionPolicy Bypass -File "skrypty\przygotuj-env.ps1"
)

echo Buduję i uruchamiam (za pierwszym razem może to potrwać kilka minut)...
docker compose up -d --build
if errorlevel 1 (
  echo [!] Coś poszło nie tak. Uruchom skrypty\logi.bat i prześlij treść błędu.
  pause
  exit /b 1
)

echo Czekam, aż aplikacja wystartuje...
powershell -NoProfile -Command "for($i=0;$i -lt 60;$i++){try{Invoke-WebRequest -UseBasicParsing http://localhost:8000/konto/logowanie/ -TimeoutSec 2 | Out-Null; exit 0}catch{Start-Sleep 2}}; exit 1"
if errorlevel 1 (
  echo [!] Aplikacja nie odpowiada. Uruchom skrypty\logi.bat, aby zobaczyć, co się dzieje.
  pause
  exit /b 1
)

echo.
echo Gotowe! Aplikacja działa pod adresem: http://localhost:8000
start "" http://localhost:8000
pause
