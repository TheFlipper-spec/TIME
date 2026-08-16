@echo off
chcp 65001 >nul
title TIME — детектив FL1PPER
cd /d "%~dp0"
python main.py
if errorlevel 1 (
  echo.
  echo Не удалось запустить игру. Установите зависимости:
  echo   pip install -r requirements.txt
  pause
)
