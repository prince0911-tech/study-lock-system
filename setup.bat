@echo off
setlocal
cd /d %~dp0

set "PYTHON_EXE=python"
if not exist runtime\tmp mkdir runtime\tmp
set "TMP=%CD%\runtime\tmp"
set "TEMP=%CD%\runtime\tmp"

if not exist .venv (
  python -m venv .venv
)

if exist .venv\Scripts\python.exe (
  set "PYTHON_EXE=.venv\Scripts\python.exe"
)

%PYTHON_EXE% -m ensurepip --upgrade >nul 2>nul
%PYTHON_EXE% -m pip --version >nul 2>nul
if errorlevel 1 (
  echo Failed to initialize pip in the virtual environment.
  echo Please verify that your Python installation includes venv and ensurepip.
  exit /b 1
)

%PYTHON_EXE% -m pip install --upgrade pip
%PYTHON_EXE% -m pip install -r requirements.txt
%PYTHON_EXE% -c "from backend.services.database import DatabaseManager; DatabaseManager(); print('Database initialized')"

echo.
echo Setup complete.
echo Load the Chrome extension from the 'extension' folder after starting the app.
