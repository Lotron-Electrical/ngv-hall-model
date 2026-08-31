@echo off
rem NGV Gandel Hall live preview - double-click me.
rem Installs ELM 2026 if missing, opens the show file, serves the hall page, connects the browser.
rem Needs Node.js (https://nodejs.org). Everything else is automatic.
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is required. Install it from https://nodejs.org and run me again.
  pause
  exit /b 1
)
node tools\live-preview.js
pause
