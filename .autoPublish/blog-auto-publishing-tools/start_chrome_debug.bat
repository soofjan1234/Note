@echo off
chcp 65001 >nul
echo ======================================
echo 启动Chrome调试模式
echo ======================================
echo.
echo 请选择启动模式:
echo 1. 使用独立的调试配置文件（推荐，不影响现有Chrome）
echo 2. 关闭所有Chrome后重新启动调试模式
echo.
choice /C 12 /N /M "请选择 (1 或 2): "
if errorlevel 2 goto close_chrome
if errorlevel 1 goto new_profile

:new_profile
echo.
echo 正在以独立配置文件启动Chrome调试模式...
echo.
goto start_chrome

:close_chrome
echo.
echo 正在关闭现有的Chrome进程...
taskkill /F /IM chrome.exe 2>nul
timeout /t 2 >nul
echo.
echo 正在以调试模式启动Chrome (端口9222)...
echo.

:start_chrome

REM 尝试不同的Chrome路径
if exist "C:\Program Files\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome_debug_profile"
    echo Chrome已启动（64位路径）
) else if exist "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" (
    start "" "C:\Program Files (x86)\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome_debug_profile"
    echo Chrome已启动（32位路径）
) else if exist "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" (
    start "" "%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9222 --user-data-dir="%TEMP%\chrome_debug_profile"
    echo Chrome已启动（用户路径）
) else (
    echo 错误：找不到Chrome安装路径
    echo 请手动运行：chrome.exe --remote-debugging-port=9222
    pause
    exit /b 1
)

echo.
echo Chrome调试模式已启动！
echo 调试端口: 127.0.0.1:9222
echo.
echo 请在Chrome中访问 https://juejin.cn 并登录你的账号
echo 然后运行 publish_juejin.bat 发布文章
echo.
pause
