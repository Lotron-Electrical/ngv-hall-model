@echo off
rem NGV Gandel Hall live preview - double-click me.
rem Starts the DMX bridge and the local page server, opens the hall already connected.
rem Needs Node.js (https://nodejs.org). ELM steps are printed by the script.
cd /d "%~dp0"
where node >nul 2>nul
if errorlevel 1 (
  echo Node.js is required. Install it from https://nodejs.org and run me again.
  pause
  exit /b 1
)
node live-preview.js
pause
