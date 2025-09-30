@echo off
set "PORT=8000"
set "HOST=0.0.0.0"
set "VENV_DIR=.venv"

if not exist "%VENV_DIR%\Scripts\python.exe" (
	echo [INFO] Creating virtual environment...
	where py >nul 2>nul
	if %errorlevel%==0 (
		py -3 -m venv %VENV_DIR%
	) else (
		python -m venv %VENV_DIR%
	)
)

call "%VENV_DIR%\Scripts\activate.bat"

echo [INFO] Checking for waitress...
"%VENV_DIR%\Scripts\python.exe" -c "import waitress" 2>nul 1>nul
if not %errorlevel%==0 (
	echo [INFO] Installing dependencies from requirements.txt ...
	"%VENV_DIR%\Scripts\python.exe" -m pip install --upgrade pip >nul
	"%VENV_DIR%\Scripts\python.exe" -m pip install -r requirements.txt || goto :error
)

echo [INFO] Starting server with waitress on %HOST%:%PORT% ...
"%VENV_DIR%\Scripts\python.exe" -m waitress --listen=%HOST%:%PORT% app:app
goto :eof

:error
echo [ERROR] Failed to install dependencies.
exit /b 1
