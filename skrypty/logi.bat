@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo Ostatnie komunikaty aplikacji (zamknij okno, aby wyjść):
docker compose logs --tail 100 -f
