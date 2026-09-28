@echo off
setlocal
cd /d "%~dp0"

REM OneDrive/cloud-synced folders can reject uv hardlinks.
REM Force copy mode so dependency setup works reliably there.
set "UV_LINK_MODE=copy"

echo ========================================
echo        DespairGen v0.6.1.1
echo ========================================
echo.

REM DespairGen is distributed as source code. The launcher uses uv to create
REM and maintain the Python environment automatically. If uv is not installed,
REM install it from the official Astral installer and then continue.
set "UV_EXE="

where uv >nul 2>&1
if %errorlevel%==0 set "UV_EXE=uv"

if not defined UV_EXE if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"

if not defined UV_EXE (
    echo uv was not found. Installing it automatically...
    echo.
    powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"
    if errorlevel 1 (
        echo.
        echo Failed to install uv automatically.
        echo Please install uv from https://docs.astral.sh/uv/getting-started/installation/
        echo and run this file again.
        pause
        exit /b 1
    )

    if exist "%USERPROFILE%\.local\bin\uv.exe" set "UV_EXE=%USERPROFILE%\.local\bin\uv.exe"
)

if not defined UV_EXE (
    where uv >nul 2>&1
    if %errorlevel%==0 set "UV_EXE=uv"
)

if not defined UV_EXE (
    echo.
    echo uv was installed, but Windows could not find it yet.
    echo Please close this window, open a new Command Prompt, and run run.bat again.
    pause
    exit /b 1
)

echo Preparing the DespairGen environment...
"%UV_EXE%" sync
if errorlevel 1 (
    echo.
    echo DespairGen could not install or update its Python dependencies.
    echo Check your internet connection and try running run.bat again.
    pause
    exit /b 1
)

echo Starting DespairGen...
"%UV_EXE%" run main.py
if errorlevel 1 (
    echo.
    echo DespairGen closed with an error. Check the log files for details.
    pause
    exit /b 1
)

endlocal
