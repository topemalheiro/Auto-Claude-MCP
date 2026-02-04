@echo off
cd /d "C:\Users\topem\source\repos\Auto-Claude Mod\apps\frontend"
call npx electron .
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start. Press any key to close...
    pause >nul
)
