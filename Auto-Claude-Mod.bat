@echo off
cd /d "c:\Users\topem\source\repos\Auto-Claude Mod"
call npm run start
if %errorlevel% neq 0 (
    echo.
    echo ERROR: Failed to start. Press any key to close...
    pause >nul
)
