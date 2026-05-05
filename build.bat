@echo off
setlocal
cd /d %~dp0

echo ================================================
echo Kodi Media Organizer - Build
echo ================================================

if not exist ".venv\Scripts\python.exe" (
  echo [1/5] Creating virtual environment...
  py -3 -m venv .venv
  if errorlevel 1 goto :fail
) else (
  echo [1/5] Virtual environment already exists.
)

echo [2/5] Upgrading pip...
call .venv\Scripts\python.exe -m pip install --upgrade pip
if errorlevel 1 goto :fail

echo [3/5] Installing requirements...
call .venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto :fail

echo [4/6] Building TUI executable with PyInstaller...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist "KodiMediaOrganizer.spec" del /q "KodiMediaOrganizer.spec"

call .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --icon "app.ico" --name "KodiMediaOrganizer" media_manager_app.py
if errorlevel 1 goto :fail

echo [5/6] Building qBittorrent hook executable...
call .venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --onefile --icon "app.ico" --name "QbitMediaHook" qbit_postprocess.py
if errorlevel 1 goto :fail

echo [6/6] Build complete.
echo Output: %cd%\dist\KodiMediaOrganizer.exe
echo Output: %cd%\dist\QbitMediaHook.exe
goto :end

:fail
echo.
echo Build failed.
exit /b 1

:end
echo.
echo Done.
endlocal
