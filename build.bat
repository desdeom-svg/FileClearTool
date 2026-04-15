@echo off
chcp 65001 >nul
echo ================================================
echo    磁盘清理助手 — 一键打包脚本
echo ================================================
echo.

set PYTHON=D:\soft\Anaconda\python.exe
set PROJECT_DIR=%~dp0

echo [步骤 1/3] 安装/检查依赖库...
%PYTHON% -m pip install customtkinter pystray pillow psutil pyinstaller --quiet
if errorlevel 1 (
    echo [错误] 依赖安装失败，请检查网络和 Python 环境。
    pause
    exit /b 1
)
echo   依赖检查完成。
echo.

echo [步骤 2/3] 生成应用程序图标...
%PYTHON% make_icon.py
if errorlevel 1 (
    echo [警告] 图标生成失败，将使用默认图标继续打包。
)
echo   图标处理完成。
echo.

echo [步骤 3/3] 开始 PyInstaller 打包...
%PYTHON% -m PyInstaller ^
    --onefile ^
    --noconsole ^
    --icon=app_icon.ico ^
    --name=DiskCleanerAssistant ^
    --add-data="app_icon.ico;." ^
    --exclude-module=numpy ^
    --exclude-module=pandas ^
    --exclude-module=scipy ^
    --exclude-module=matplotlib ^
    --exclude-module=PyQt5 ^
    --exclude-module=PyQt6 ^
    --exclude-module=PySide2 ^
    --exclude-module=PySide6 ^
    --exclude-module=tkinter.test ^
    --exclude-module=unittest ^
    --exclude-module=pydoc ^
    --exclude-module=doctest ^
    main.py

if errorlevel 1 (
    echo.
    echo [错误] 打包失败！请查看上方错误信息。
    pause
    exit /b 1
)

echo.
echo ================================================
echo    打包成功！
echo    可执行文件位于: dist\DiskCleanerAssistant.exe
echo ================================================
echo.
pause
