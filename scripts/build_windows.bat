@echo off
REM Build a self-contained single-file .exe for Windows.
REM Requires: Python 3.10+, pip, PyInstaller. Run from any shell.

setlocal enableextensions enabledelayedexpansion
set "ROOT=%~dp0.."
pushd "%ROOT%"

echo ==^> Installing build dependencies
python -m pip install --upgrade pip || goto :err
python -m pip install -r requirements.txt || goto :err
python -m pip install "pyinstaller>=6.0" || goto :err

echo ==^> Cleaning previous build output
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist

echo ==^> Running PyInstaller
python -m PyInstaller --noconfirm pyinstaller.spec || goto :err

if not exist "dist\RobloxAFKGuard.exe" (
  echo !! Expected dist\RobloxAFKGuard.exe to exist; PyInstaller output unexpected. 1>&2
  dir dist
  goto :err
)

echo ==^> Done: dist\RobloxAFKGuard.exe
popd
endlocal
exit /b 0

:err
echo Build failed. 1>&2
popd
endlocal
exit /b 1
