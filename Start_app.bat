@echo off
cd C:\Users\dkamande\oikonomos 
start python oikonomos.py

:: Wait for the Flask app to start
:waitForApp
timeout /t 1 >nul
curl -s http://localhost:5000 >nul
if errorlevel 1 (
    goto waitForApp
)

:: Open the web browser once the app is running
start "Chrome" "C:\Program Files\Google\Chrome\Application\chrome.exe" http://localhost:5000
pause