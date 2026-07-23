@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Nejdrive spustte setup_windows.bat.
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m antenna_pattern_lab

