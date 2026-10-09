@echo off
chcp 65001 >nul
cd /d "%~dp0"
py -3w -c "import tkinter" >nul 2>&1 && start "" py -3w "%~dp0kb.py" && exit /b 0
pythonw -c "import tkinter" >nul 2>&1 && start "" pythonw "%~dp0kb.py" && exit /b 0
echo Falta Python con ventanas.
echo 1. Entra en https://www.python.org/downloads/
echo 2. Instala y marca Tcl/Tk
echo 3. Vuelve a abrir Instalar.bat
start https://www.python.org/downloads/
pause
