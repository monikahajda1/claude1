@echo off
chcp 65001 >nul
cd /d "%~dp0.."
echo ================================================================
echo  UWAGA! Ten skrypt USUWA CAŁĄ BAZĘ DANYCH i wszystkie przesłane
echo  pliki. Używaj go tylko, aby usunąć dane TESTOWE przed wpisaniem
echo  prawdziwych danych. Kopie w folderze "kopie" zostają.
echo ================================================================
set /p OK=Wpisz USUN (wielkimi literami, bez polskich znaków), aby kontynuować: 
if not "%OK%"=="USUN" (
  echo Anulowano.
  pause
  exit /b 1
)
docker compose down -v
echo Baza usunięta. Uruchom start.bat, a potem skrypty\utworz-administratora.bat.
pause
