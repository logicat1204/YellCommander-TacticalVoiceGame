@echo off
setlocal
powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File "%~dp0Iniciar.ps1" %*
if errorlevel 1 (
    echo.
    echo SujetoLugar no pudo completar la operacion. Revisa el mensaje anterior.
    pause
    exit /b 1
)
