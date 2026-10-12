@echo off
setlocal
cd /d "%~dp0"
echo.
echo =======================================
echo    SAARTHI JEWAR 63 ELECTORAL LENS
echo =======================================
echo.
where py >nul 2>nul
if %errorlevel% == 0 (
  set "PYTHON=py"
) else (
  set "PYTHON=python"
)
%PYTHON% -m pip install -r requirements.txt
if errorlevel 1 (
 echo Could not install packages. Check your internet connection and Python installation.
 pause
 exit /b 1
)
%PYTHON% -m streamlit run app.py --server.port 8502
pause
