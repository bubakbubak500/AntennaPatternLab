@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Nejdrive spustte setup_windows.bat.
  pause
  exit /b 1
)
call ".venv\Scripts\python.exe" -m pytest
if errorlevel 1 exit /b 1
call ".venv\Scripts\pyinstaller.exe" --noconfirm AntennaPatternLab.spec
if errorlevel 1 exit /b 1
echo.
echo Build hotov: dist\AntennaPatternLab\AntennaPatternLab.exe
pause

