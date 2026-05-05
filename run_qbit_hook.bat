@echo off
setlocal
cd /d %~dp0

if exist "dist\QbitMediaHook.exe" (
  dist\QbitMediaHook.exe %*
) else if exist ".venv\Scripts\python.exe" (
  .venv\Scripts\python.exe qbit_postprocess.py %*
) else (
  py -3 qbit_postprocess.py %*
)

endlocal
