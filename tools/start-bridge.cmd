@echo off
rem One-click bridge for the NGV hall page. Fetches dmx_bridge.js next to itself if missing,
rem then runs it. Needs Node.js (https://nodejs.org). Leave the window open while you map.
cd /d "%~dp0"
where node >nul 2>nul || (echo Node.js is not installed. Get it from https://nodejs.org and run this again. & start https://nodejs.org & pause & exit /b 1)
if not exist dmx_bridge.js (
  echo Fetching dmx_bridge.js ...
  curl -fsSL -o dmx_bridge.js https://raw.githubusercontent.com/lotron-electrical/ngv-hall-model/main/tools/dmx_bridge.js || (echo Could not download dmx_bridge.js. Check the internet connection. & pause & exit /b 1)
)
node dmx_bridge.js %*
pause
