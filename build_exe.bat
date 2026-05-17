@echo off
setlocal
cd /d %~dp0

set "PYTHON_EXE=python"
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -m pip --version >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
  )
)
%PYTHON_EXE% -m PyInstaller installer\StudyLock.spec --clean
