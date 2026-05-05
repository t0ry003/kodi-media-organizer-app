@echo off
setlocal
cd /d %~dp0

if exist "dist\KodiMediaOrganizer.exe" (
  dist\KodiMediaOrganizer.exe
) else if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe media_manager_app.py
) else (
  py -3 media_manager_app.py
)

endlocal
