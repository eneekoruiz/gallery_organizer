@echo off
REM Smart Gallery Maintenance Task Wrapper
REM Executes the Python maintenance runner with logging and timestamp

setlocal enabledelayedexpansion
set REPO_ROOT=C:\Users\User\Desktop\PROYECTOS\smart_gallery_v2
set PYTHON=%REPO_ROOT%\.venv\Scripts\python.exe
if not exist "!PYTHON!" set PYTHON=C:\Users\User\AppData\Local\Programs\Python\Python310\python.exe
set RUNNER=%REPO_ROOT%\smart_gallery_v2\tools\maintenance_runner.py
set LOG_DIR=%REPO_ROOT%\maintenance_logs
if not exist "!LOG_DIR!" mkdir "!LOG_DIR!"

REM Generate timestamp for log file
for /f "tokens=2-4 delims=/ " %%a in ('date /t') do (set mydate=%%c%%a%%b)
for /f "tokens=1-2 delims=/:" %%a in ('time /t') do (set mytime=%%a%%b)
set LOGFILE=!LOG_DIR!\maintenance_!mydate!_!mytime!.log

REM Run the maintenance runner
echo Maintenance started at %date% %time% >> "!LOGFILE!"
"!PYTHON!" "!RUNNER!" --log-file "!LOGFILE!" >> "!LOGFILE!" 2>&1
set EXIT_CODE=%ERRORLEVEL%
echo Maintenance finished with exit code %EXIT_CODE% >> "!LOGFILE!"
exit /b %EXIT_CODE%

