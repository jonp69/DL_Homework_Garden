@echo off
setlocal ENABLEDELAYEDEXPANSION

REM ================================================
REM Detect repo root (directory of this script)
REM ================================================
set SCRIPT_DIR=%~dp0
pushd "%SCRIPT_DIR%"

set REQ_FILE=requirements.txt
if not exist "%REQ_FILE%" (
  echo ERROR: requirements.txt not found in %CD%
  pause
  exit /b 1
)

REM ================================================
REM Determine Python interpreter
REM ================================================
set USE_PY311=0
set LLM_PKGS=transformers torch tensorflow langchain openai llama-cpp-python sentence-transformers diffusers accelerate bitsandbytes
for /f "usebackq delims=" %%L in ("%REQ_FILE%") do (
  set LINE=%%L
  for %%P in (%LLM_PKGS%) do (
    echo !LINE! | findstr /I /R "^%%P\(==\|>=\|<=\|~=\|>\|<\|$\)" >nul 2>nul
    if !errorlevel! EQU 0 (
      set USE_PY311=1
    )
  )
)

if %USE_PY311% EQU 1 (
  set PY_EXE=C:\Python311\python.exe
  if not exist "%PY_EXE%" (
    echo [INFO] C:\Python311\python.exe not found. Falling back to system python.
    set PY_EXE=python
  )
) else (
  set PY_EXE=python
)

REM Resolve python path to echo
for /f "delims=" %%p in ('"%PY_EXE%" -c "import sys; print(sys.executable)" 2^>nul') do set PY_REAL=%%p
if not defined PY_REAL set PY_REAL=%PY_EXE%

set VENV_DIR=.venv
set ACTIVATE_CMD=%VENV_DIR%\Scripts\activate.bat

REM ================================================
REM [1/4] Create or Activate virtual environment
REM ================================================
if not exist "%VENV_DIR%" (
  echo ================================================
  echo [1/4] Creating virtual environment...
  echo ================================================
  "%PY_EXE%" -m venv "%VENV_DIR%"
  if errorlevel 1 (
    echo ERROR: Failed to create virtual environment with %PY_REAL%
    pause
    exit /b 1
  )
) else (
  echo ================================================
  echo [1/4] Activating virtual environment...
  echo ================================================
)

if not exist "%ACTIVATE_CMD%" (
  echo ERROR: Activation script not found: %ACTIVATE_CMD%
  pause
  exit /b 1
)
call "%ACTIVATE_CMD%"
if errorlevel 1 (
  echo ERROR: Failed to activate virtual environment
  pause
  exit /b 1
)

REM ================================================
REM [2/4] Verify/install requirements
REM ================================================
set NEED_INSTALL=0

REM Try to verify modules by attempting import of top-level names
REM This is a best-effort approach; not all packages map 1:1 to import names.
for /f "usebackq tokens=1 delims==>=<~ " %%r in ("%REQ_FILE%") do (
  set PKG=%%r
  if not "!PKG!"=="" (
    echo !PKG! | findstr /R "^[#;]" >nul 2>nul
    if !errorlevel! NEQ 0 (
      "%VENV_DIR%\Scripts\python.exe" -c "import importlib,sys; sys.exit(0) if importlib.util.find_spec(r'!PKG!') else sys.exit(1)" >nul 2>nul
      if !errorlevel! NEQ 0 (
        set NEED_INSTALL=1
      )
    )
  )
)

if %NEED_INSTALL% EQU 1 (
  echo ================================================
  echo [2/4] Installing packages from requirements.txt...
  echo ================================================
  "%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip
  if errorlevel 1 (
    echo ERROR: Failed to upgrade pip
    pause
    exit /b 1
  )
  "%VENV_DIR%\Scripts\pip.exe" install -r "%REQ_FILE%"
  if errorlevel 1 (
    echo ERROR: Failed to install requirements
    pause
    exit /b 1
  )
) else (
  echo ================================================
  echo [2/4] Verifying installed packages...
  echo ================================================
  echo [INFO] All required packages appear to be installed.
)

REM ================================================
REM [3/4] Run DL Homework Garden GUI
REM ================================================
echo.
pause

echo ================================================
echo [3/4] Running DL Homework Garden...
echo ================================================
"%VENV_DIR%\Scripts\python.exe" main.py

REM ================================================
REM [4/4] Application closed!
REM ================================================
echo ================================================
echo [4/4] Application closed!
echo ================================================
pause

popd
endlocal
