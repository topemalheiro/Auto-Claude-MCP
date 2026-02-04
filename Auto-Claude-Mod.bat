@echo off
cd /d "C:\Users\topem\source\repos\Auto-Claude Mod\apps\frontend"
echo Starting Auto-Claude with crash recovery watchdog...
echo.
call npx tsx src/main/watchdog/launcher.ts ..\..\node_modules\.bin\electron out/main/index.js
echo.
echo Launcher exited with code: %errorlevel%
echo Press any key to close...
pause >nul
