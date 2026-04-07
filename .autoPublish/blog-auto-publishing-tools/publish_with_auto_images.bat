@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ======================================
echo Juejin auto publisher (with image upload)
echo ======================================
echo.
echo This script will start Chrome in debug mode and open https://juejin.cn/creator/home
echo.

:new_profile
echo.
echo Starting Chrome with a new debug profile...
echo.
goto start_chrome

:start_chrome

REM Try common Chrome install paths
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome_debug_profile" https://juejin.cn/creator/home
    echo Chrome started (Program Files 64-bit)
) 

echo.
echo Chrome debug mode is running on 127.0.0.1:9222
echo.
echo Starting auto publish without waiting for login...
echo.
"%~dp0venv\Scripts\python.exe" "%~dp0publish_juejin_with_images.py"
echo.
pause
