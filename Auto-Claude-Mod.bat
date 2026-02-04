@echo off
cd /d "C:\Users\topem\source\repos\Auto-Claude Mod\apps\frontend"
echo Starting Auto-Claude with crash recovery watchdog...
echo.
call npx tsx src/main/watchdog/launcher.ts ..\..\node_modules\.bin\electron out/main/index.js
set EXIT_CODE=%errorlevel%

REM Only pause on error/crash (non-zero exit code)
REM Normal exit (code 0) = user closed the app = close terminal immediately
if %EXIT_CODE% neq 0 (
    echo.
    echo Launcher exited with code: %EXIT_CODE%
    echo Press any key to close...
    pause >nul
)
