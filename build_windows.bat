@echo off
rem ============================================================
rem  TIME — официальная сборка .exe на Windows (PyInstaller)
rem
rem  Требования: установленный Python 3.11+ с pip (python.org)
rem
rem  Что делает:
rem    1. ставит pygame и PyInstaller
rem    2. собирает один файл TIME.exe (без консоли)
rem    3. кладёт результат в dist\TIME.exe
rem ============================================================
chcp 65001 >nul
title TIME — сборка exe
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo [ОШИБКА] Python не найден. Установите его с python.org
    echo          и не забудьте отметить галочку "Add to PATH".
    pause
    exit /b 1
)

echo [1/3] Устанавливаю зависимости...
python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller
if errorlevel 1 goto :err

echo [2/3] Собираю TIME.exe...
python -m PyInstaller --noconfirm --clean ^
    --onefile --windowed --name TIME ^
    --add-data "assets;assets" ^
    --icon assets\icon.ico ^
    main.py
if errorlevel 1 goto :err

echo [3/3] Готово!
echo.
echo Собран файл:  dist\TIME.exe
echo Запустите его двойным кликом. Сохранения появятся в папке
echo userdata рядом с exe.
pause
exit /b 0

:err
echo.
echo [ОШИБКА] Сборка не удалась. Проверьте вывод выше.
pause
exit /b 1
