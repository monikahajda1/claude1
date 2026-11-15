@echo off
chcp 65001 >nul
cd /d "%~dp0"
for /f %%i in ('powershell -NoProfile -Command "Get-Date -Format yyyy-MM-dd_HH-mm"') do set DATA=%%i
if not exist kopie mkdir kopie

echo Robię kopię bazy danych...
docker compose exec -T db sh -c "pg_dump -U $POSTGRES_USER -d $POSTGRES_DB -Fc -f /kopie/baza_%DATA%.dump"
if errorlevel 1 goto blad

echo Robię kopię przesłanych plików (skany, zdjęcia)...
docker compose exec -T web tar czf /kopie/pliki_%DATA%.tar.gz -C /app/media .
if errorlevel 1 goto blad

echo.
echo Gotowe. Kopia jest w folderze "kopie":
echo   baza_%DATA%.dump
echo   pliki_%DATA%.tar.gz
echo Skopiuj te pliki także poza ten komputer (dysk zewnętrzny / chmura firmowa).
pause
exit /b 0

:blad
echo [!] Kopia NIE powiodła się. Czy aplikacja jest uruchomiona (start.bat)?
pause
exit /b 1
