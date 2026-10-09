@echo off
chcp 65001 >nul
cd /d "%~dp0"
if exist "%~dp0kb.py" (set "APP=%~dp0kb.py") else (set "APP=%~dp0programa\kb.py")
py -3w -c "import tkinter" >nul 2>&1 && start "" py -3w "%APP%" && exit /b 0
pythonw -c "import tkinter" >nul 2>&1 && start "" pythonw "%APP%" && exit /b 0
echo Falta un programa que Teclado necesita.
echo 1. Se abre una pagina. Descarga Python.
echo 2. Instalalo y no quites ninguna casilla.
echo 3. Vuelve a hacer doble clic en Instalar.
start https://www.python.org/downloads/
pause
