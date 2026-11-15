@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Zatrzymuję aplikację (dane zostają zachowane)...
docker compose stop
echo Zatrzymano.
pause
