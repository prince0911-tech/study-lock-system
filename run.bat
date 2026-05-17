@echo off
setlocal
cd /d %~dp0

set "PYTHON_EXE=python"
if not exist runtime\tmp mkdir runtime\tmp
set "TMP=%CD%\runtime\tmp"
set "TEMP=%CD%\runtime\tmp"
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -m ensurepip --upgrade >nul 2>nul
  .venv\Scripts\python.exe -m pip --version >nul 2>nul
  if not errorlevel 1 (
    set "PYTHON_EXE=.venv\Scripts\python.exe"
  )
)
%PYTHON_EXE% -m desktop_app.main
