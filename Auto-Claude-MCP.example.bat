@echo off
REM ============================================================
REM  Auto-Claude-MCP Launcher with External Watchdog
REM ============================================================
REM  This launches Auto-Claude via the watchdog process, which
REM  monitors for crashes and can auto-restart the app.
REM
REM  SETUP: Replace the path below with your actual install path.
REM  Example: C:\Users\YourName\source\repos\Auto-Claude-MCP
REM ============================================================

set AUTO_CLAUDE_DIR=C:\Users\USER\path\to\Auto-Claude-MCP

cd /d "%AUTO_CLAUDE_DIR%\apps\frontend"
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
