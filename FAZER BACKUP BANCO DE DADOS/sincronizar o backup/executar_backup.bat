@echo off
title Backup Automático Clínica
color 0A

echo ========================================
echo Backup Automático - Clínica Odontológica
echo ========================================
echo.

cd /d "%~dp0"

REM Executar o backup
python backup_sincronizacao.py

echo.
echo Backup concluído!
timeout /t 5