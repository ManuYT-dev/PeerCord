@echo off
title PeerCord Compiler
color 0A

REM Gehe sicher, dass wir im Hauptverzeichnis des Skripts (P2P Ordner) sind
cd /d "%~dp0"

echo ==========================================
echo    PeerCord Auto-Compiler (Nuitka)
echo ==========================================
echo.

echo [1/5] Bereinige alte Dateien im 'bin' Ordner...
if exist "bin\Host" rmdir /s /q "bin\Host"
if exist "bin\Client" rmdir /s /q "bin\Client"
mkdir "bin\Host"
mkdir "bin\Client"

echo.
echo [2/5] Kompiliere Host (Das dauert ein paar Minuten)...
cd src
python -m nuitka --standalone --plugin-enable=pyqt6 --windows-console-mode=disable --output-dir="..\bin\Host" .\Host\main.py

echo.
echo [3/5] Kompiliere Client (Das dauert ebenfalls)...
python -m nuitka --standalone --plugin-enable=pyqt6 --windows-console-mode=disable --output-dir="..\bin\Client" .\Client\main.py

cd ..

echo.
echo [4/5] Raeume auf und benenne Dateien um...
if exist "bin\Host\main.build" rmdir /s /q "bin\Host\main.build"
if exist "bin\Client\main.build" rmdir /s /q "bin\Client\main.build"

if exist "bin\Host\main.dist\main.exe" ren "bin\Host\main.dist\main.exe" "PeerCord_Host.exe"
if exist "bin\Client\main.dist\main.exe" ren "bin\Client\main.dist\main.exe" "PeerCord_Client.exe"

if exist "bin\Host\main.dist" ren "bin\Host\main.dist" "PeerCord_Host"
if exist "bin\Client\main.dist" ren "bin\Client\main.dist" "PeerCord_Client"

echo.
echo [5/5] Erstelle Verknuepfungen (Shortcuts)...
REM Erstellt eine "Start PeerCord Host.lnk" direkt im bin\Host Ordner
powershell -Command "$wshell = New-Object -ComObject WScript.Shell; $shortcut = $wshell.CreateShortcut('%~dp0bin\Host\Start PeerCord Host.lnk'); $shortcut.TargetPath = '%~dp0bin\Host\PeerCord_Host\PeerCord_Host.exe'; $shortcut.WorkingDirectory = '%~dp0bin\Host\PeerCord_Host'; $shortcut.Save()"

REM Erstellt eine "Start PeerCord Client.lnk" direkt im bin\Client Ordner
powershell -Command "$wshell = New-Object -ComObject WScript.Shell; $shortcut = $wshell.CreateShortcut('%~dp0bin\Client\Start PeerCord Client.lnk'); $shortcut.TargetPath = '%~dp0bin\Client\PeerCord_Client\PeerCord_Client.exe'; $shortcut.WorkingDirectory = '%~dp0bin\Client\PeerCord_Client'; $shortcut.Save()"

echo.
echo ==========================================
echo FERTIG! 
echo Deine Programme und Verknuepfungen liegen hier:
echo - bin\Host\Start PeerCord Host.lnk
echo - bin\Client\Start PeerCord Client.lnk
echo ==========================================
pause