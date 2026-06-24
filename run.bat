@echo off
REM ===================================================================
REM  WHome Diagnostic Tool - one-click launcher (no build required)
REM  Double-click this file to install dependencies and start the app.
REM  For full repair powers, right-click -> "Run as administrator".
REM ===================================================================
setlocal
cd /d "%~dp0"

REM Prefer the Python launcher 'py', fall back to 'python'.
where py >nul 2>&1
if %errorlevel%==0 (set "PY=py") else (set "PY=python")

%PY% --version >nul 2>&1
if errorlevel 1 (
  echo.
  echo  [!] Python was not found.
  echo      1^) Install Python from https://www.python.org/downloads/
  echo      2^) On the first installer screen, TICK "Add python.exe to PATH"
  echo      3^) Then double-click run.bat again.
  echo.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
  echo  Creating virtual environment ^(first run only^)...
  %PY% -m venv .venv
)

call ".venv\Scripts\activate.bat"

echo  Installing dependencies ^(first run only; this can take a minute^)...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if errorlevel 1 (
  echo.
  echo  [!] Dependency install failed. Check your internet connection and retry.
  pause
  exit /b 1
)

echo.
echo  Launching WHome Diagnostic Tool...
python main.py

endlocal
