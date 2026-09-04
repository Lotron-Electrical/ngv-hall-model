@echo off
rem NGV Gandel Hall lightshow studio - double-click me.
rem Serves the page locally (a minimised window stays open while you work) and opens the studio in Chrome.
rem Make the music, cue the lights, Export. Needs Node.js (https://nodejs.org).
cd /d "%~dp0"
where node >/dev/null 2>nul
if errorlevel 1 (
  echo Node.js is required. Install it from https://nodejs.org and run me again.
  pause
  exit /b 1
)
start "NGV studio server" /min node tools\serve.js --port 8877
timeout /t 1 >nul
start "" "http://127.0.0.1:8877/studio.html"
