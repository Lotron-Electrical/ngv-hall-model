@echo off
rem Starts the Art-Net / sACN -> browser bridge for the NGV hall page. Needs Node.js (https://nodejs.org).
rem Put this file next to dmx_bridge.js and double-click it. Leave the window open while you map.
cd /d "%~dp0"
where node >nul 2>nul || (echo Node.js is not installed. Get it from https://nodejs.org and run this again. & pause & exit /b 1)
node dmx_bridge.js %*
pause
