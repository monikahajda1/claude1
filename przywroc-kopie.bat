@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Dostępne kopie bazy:
dir /b kopie\baza_*.dump 2>nul
echo.
set /p PLIK=Wpisz (lub wklej) nazwę pliku kopii, np. baza_2026-11-15_10-30.dump: 
if not exist "kopie\%PLIK%" (
  echo [!] Nie ma takiego pliku w folderze "kopie".
  pause
  exit /b 1
)
echo.
echo UWAGA: obecne dane w aplikacji zostaną ZASTĄPIONE danymi z kopii %PLIK%.
set /p OK=Wpisz TAK (wielkimi literami), aby kontynuować: 
if not "%OK%"=="TAK" (
  echo Anulowano.
  pause
  exit /b 1
)

docker compose up -d db
docker compose stop web
echo Przywracam bazę...
docker compose exec -T db sh -c "pg_restore -U $POSTGRES_USER -d $POSTGRES_DB --clean --if-exists --no-owner /kopie/%PLIK%"

set PLIKI=%PLIK:baza_=pliki_%
set PLIKI=%PLIKI:.dump=.tar.gz%
if exist "kopie\%PLIKI%" (
  echo Przywracam przesłane pliki...
  docker compose run --rm --no-deps --entrypoint tar web xzf /kopie/%PLIKI% -C /app/media
)

docker compose start web
echo.
echo Gotowe. Odśwież stronę w przeglądarce.
pause
