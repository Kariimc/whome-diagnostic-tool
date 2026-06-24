@echo off
REM ===================================================================
REM  Build a standalone WHomeDiagnostics.exe with `flet pack`.
REM  Produces a single windowed (no-console) executable that requests
REM  Administrator elevation on launch (--uac-admin).
REM  Output: dist\WHomeDiagnostics.exe
REM ===================================================================
setlocal
cd /d "%~dp0"

where py >nul 2>&1
if %errorlevel%==0 (set "PY=py") else (set "PY=python")

%PY% --version >nul 2>&1
if errorlevel 1 (
  echo  [!] Python not found. Install it from https://www.python.org/downloads/
  pause
  exit /b 1
)

if not exist ".venv\Scripts\activate.bat" (
  echo  Creating virtual environment...
  %PY% -m venv .venv
)
call ".venv\Scripts\activate.bat"

echo  Installing dependencies...
python -m pip install --upgrade pip >nul 2>&1
python -m pip install -r requirements.txt
if errorlevel 1 ( echo  [!] Dependency install failed. & pause & exit /b 1 )

echo.
echo  Building standalone executable ^(this can take several minutes^)...
flet pack main.py ^
  --name WHomeDiagnostics ^
  --product-name "WHome Diagnostic Tool" ^
  --file-description "Windows diagnostic and repair utility" ^
  --product-version 1.0.0 ^
  --file-version 1.0.0.0 ^
  --uac-admin ^
  --yes

if errorlevel 1 ( echo  [!] Build failed. & pause & exit /b 1 )

echo.
echo  ============================================================
echo   Done!  Your app is here:
echo       dist\WHomeDiagnostics.exe
echo.
echo   Double-click it to run. Windows UAC will prompt for
echo   Administrator rights automatically.
echo  ============================================================
pause
endlocal
