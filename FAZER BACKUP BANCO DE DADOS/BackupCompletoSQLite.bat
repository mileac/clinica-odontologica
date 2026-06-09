@echo off
setlocal enabledelayedexpansion

:: ============================================
:: CONFIGURAÇÕES - AJUSTE AQUI
:: ============================================

:: Caminho do seu banco SQLite LOCAL (principal)
set BANCO_LOCAL=C:\Users\Marco Antonio\OneDrive\Área de Trabalho\Dr. Eduardo\clinica_odontologica\instance\clinica.db

:: Pasta onde ficarão os backups
set PASTA_BACKUPS=C:\Users\Marco Antonio\OneDrive\Área de Trabalho\Dr. Eduardo\clinica_odontologica\instance\Backups\BancoDados

:: Caminho do HD externo (ajuste a letra)
set HD_EXTERNO=F:\Backups_Clinica

:: Quantos dias manter os backups (recomendo 90)
set DIAS_MANTER=90

:: ============================================
:: INÍCIO DO SCRIPT - NÃO MEXER
:: ============================================

:: Criar pastas se não existirem
if not exist "%PASTA_BACKUPS%" mkdir "%PASTA_BACKUPS%"
if not exist "%HD_EXTERNO%" mkdir "%HD_EXTERNO%"

:: Gerar nome do arquivo com data e hora
set ANO=%date:~6,4%
set MES=%date:~3,2%
set DIA=%date:~0,2%
set HORA=%time:~0,2%
set MINUTO=%time:~3,2%
set SEGUNDO=%time:~6,2%
set HORA=%HORA: =0%

set DATAHORA=%ANO%-%MES%-%DIA%_%HORA%-%MINUTO%-%SEGUNDO%
set NOME_BACKUP=backup_clinica_%DATAHORA%.db
set NOME_ZIP=backup_clinica_%DATAHORA%.zip

echo ========================================
echo BACKUP DO BANCO SQLITE - CLINICA
echo Data: %DATAHORA%
echo ========================================
echo.

:: ============================================
:: PASSO 1: VERIFICAR SE O BANCO EXISTE
:: ============================================
echo [1/4] Verificando banco de dados...

if not exist "%BANCO_LOCAL%" (
    echo ERRO: Banco nao encontrado em %BANCO_LOCAL%
    echo Verifique o caminho e tente novamente.
    pause
    exit /b 1
)

:: Mostrar tamanho do banco
for %%A in ("%BANCO_LOCAL%") do set TAMANHO=%%~zA
set /a TAMANHO_MB=%TAMANHO%/1048576
echo OK: Banco encontrado - Tamanho: %TAMANHO_MB% MB
echo.

:: ============================================
:: PASSO 2: FAZER BACKUP COM CONSISTÊNCIA
:: ============================================
echo [2/4] Criando backup consistente...

:: Usa o comando .backup do SQLite para garantir consistência
sqlite3 "%BANCO_LOCAL%" ".backup '%PASTA_BACKUPS%\%NOME_BACKUP%'"

if exist "%PASTA_BACKUPS%\%NOME_BACKUP%" (
    echo OK: Backup criado com sucesso!
    for %%A in ("%PASTA_BACKUPS%\%NOME_BACKUP%") do set TAM_BACKUP=%%~zA
    set /a TAM_BACKUP_MB=!TAM_BACKUP!/1048576
    echo     Arquivo: %NOME_BACKUP%
    echo     Tamanho: !TAM_BACKUP_MB! MB
) else (
    echo ERRO: Falha ao criar backup!
    echo Tentando metodo alternativo (copia simples)...
    copy "%BANCO_LOCAL%" "%PASTA_BACKUPS%\%NOME_BACKUP%" > nul
)
echo.

:: ============================================
:: PASSO 3: COMPACTAR PARA ECONOMIZAR ESPAÇO
:: ============================================
echo [3/4] Compactando backup...

powershell -command "Compress-Archive -Path '%PASTA_BACKUPS%\%NOME_BACKUP%' -DestinationPath '%PASTA_BACKUPS%\%NOME_ZIP%' -Force"

if exist "%PASTA_BACKUPS%\%NOME_ZIP%" (
    echo OK: Backup compactado!
    del "%PASTA_BACKUPS%\%NOME_BACKUP%" 2>nul
    
    :: Mostrar economia de espaço
    for %%A in ("%PASTA_BACKUPS%\%NOME_ZIP%") do set TAM_ZIP=%%~zA
    set /a TAM_ZIP_MB=!TAM_ZIP!/1048576
    echo     Compactado: %NOME_ZIP% (!TAM_ZIP_MB! MB)
) else (
    echo AVISO: Falha na compactacao, mantendo arquivo original
    set NOME_ZIP=%NOME_BACKUP%
)
echo.

:: ============================================
:: PASSO 4: COPIAR PARA HD EXTERNO
:: ============================================
echo [4/4] Copiando para HD externo...

if exist "%HD_EXTERNO%" (
    copy "%PASTA_BACKUPS%\%NOME_ZIP%" "%HD_EXTERNO%\" > nul
    if exist "%HD_EXTERNO%\%NOME_ZIP%" (
        echo OK: Backup copiado para o HD externo!
        echo     Local: %HD_EXTERNO%\%NOME_ZIP%
    ) else (
        echo ERRO: Falha ao copiar para o HD externo
    )
) else (
    echo ERRO: HD externo nao encontrado em %HD_EXTERNO%
    echo Verifique se o HD esta conectado e a letra da unidade esta correta
)
echo.

:: ============================================
:: LIMPAR BACKUPS ANTIGOS
:: ============================================
echo Limpando backups antigos (mais de %DIAS_MANTER% dias)...

:: Limpar backups antigos da pasta principal
forfiles /p "%PASTA_BACKUPS%" /m "backup_clinica_*.zip" /d -%DIAS_MANTER% /c "cmd /c echo Removendo @file..." 2>nul
forfiles /p "%PASTA_BACKUPS%" /m "backup_clinica_*.zip" /d -%DIAS_MANTER% /c "cmd /c del @file" 2>nul

:: Limpar backups antigos do HD externo
if exist "%HD_EXTERNO%" (
    forfiles /p "%HD_EXTERNO%" /m "backup_clinica_*.zip" /d -%DIAS_MANTER% /c "cmd /c echo Removendo @file do HD..." 2>nul
    forfiles /p "%HD_EXTERNO%" /m "backup_clinica_*.zip" /d -%DIAS_MANTER% /c "cmd /c del @file" 2>nul
)

:: ============================================
:: GERAR LOG
:: ============================================
echo %date% %time% - Backup concluido: %NOME_ZIP% >> "%PASTA_BACKUPS%\backup_log.txt"

echo ========================================
echo BACKUP CONCLUIDO COM SUCESSO!
echo ========================================
echo.
echo RESUMO FINAL:
echo ----------------------------------------
echo Banco original: %BANCO_LOCAL%
echo Backup criado:  %PASTA_BACKUPS%\%NOME_ZIP%
echo HD externo:     %HD_EXTERNO%\%NOME_ZIP%
echo Log salvo em:   %PASTA_BACKUPS%\backup_log.txt
echo.
echo Backups mantidos por %DIAS_MANTER% dias
echo.

pause