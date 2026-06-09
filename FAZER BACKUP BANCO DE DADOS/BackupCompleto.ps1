# ============================================
# SCRIPT DE BACKUP COMPLETO - NUVEM -> PC LOCAL -> HD EXTERNO
# ============================================

# CONFIGURAÇÕES (VOCÊ DEVE AJUSTAR AQUI)
# ============================================

# Dados do Banco na Nuvem
$servidor_nuvem = "seu_servidor.com"
$usuario = "seu_usuario"
$senha = "sua_senha"
$banco_dados = "nome_do_banco"

# Pastas Locais
$pasta_pc_local = "C:\Backups\BancoDados"
$pasta_hd_externo = "D:\Backups\BancoDados"  # Mude a letra do seu HD externo

# Configurações de Retenção (quantos backups manter)
$manter_dias_pc = 30      # Mantém 30 dias no PC local
$manter_dias_hd = 90      # Mantém 90 dias no HD externo

# ============================================
# INÍCIO DO SCRIPT - NÃO MEXER DAQUI PRA BAIXO
# ============================================

# Cria as pastas se não existirem
New-Item -ItemType Directory -Force -Path $pasta_pc_local | Out-Null
New-Item -ItemType Directory -Force -Path $pasta_hd_externo | Out-Null

# Gera nome do arquivo com data e hora
$data_atual = Get-Date -Format "yyyy-MM-dd_HH-mm"
$nome_backup = "backup_${banco_dados}_${data_atual}.sql"
$caminho_pc = Join-Path $pasta_pc_local $nome_backup
$caminho_hd = Join-Path $pasta_hd_externo $nome_backup

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "INICIANDO BACKUP DO BANCO DE DADOS" -ForegroundColor Cyan
Write-Host "Data/Hora: $(Get-Date -Format 'dd/MM/yyyy HH:mm')" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# ============================================
# PASSO 1: FAZER BACKUP DO BANCO NA NUVEM
# ============================================

Write-Host "[1/3] Conectando ao banco na nuvem..." -ForegroundColor Yellow

# Verifica qual banco está sendo usado (MySQL/MariaDB)
$comando_mysql = "mysqldump.exe -h $servidor_nuvem -u $usuario -p$senha --databases $banco_dados --result-file=`"$caminho_pc`""

# Se for PostgreSQL, use este comando:
# $comando_pg = "pg_dump.exe -h $servidor_nuvem -U $usuario -d $banco_dados -f `"$caminho_pc`""

try {
    # Executa o backup (MySQL por padrão)
    & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqldump.exe" -h $servidor_nuvem -u $usuario -p$senha --databases $banco_dados --result-file="$caminho_pc" 2>&1
    
    # Verifica se o arquivo foi criado
    if (Test-Path $caminho_pc) {
        $tamanho = [math]::Round((Get-Item $caminho_pc).Length / 1MB, 2)
        Write-Host "✓ Backup criado com sucesso no PC local!" -ForegroundColor Green
        Write-Host "  Local: $caminho_pc" -ForegroundColor Gray
        Write-Host "  Tamanho: ${tamanho} MB" -ForegroundColor Gray
    } else {
        throw "Arquivo de backup não foi criado"
    }
}
catch {
    Write-Host "✗ ERRO no backup do banco!" -ForegroundColor Red
    Write-Host "  Detalhes: $_" -ForegroundColor Red
    exit 1
}

# ============================================
# PASSO 2: COPIAR PARA O HD EXTERNO
# ============================================

Write-Host "[2/3] Copiando backup para o HD externo..." -ForegroundColor Yellow

# Verifica se o HD externo está conectado
if (Test-Path $pasta_hd_externo) {
    try {
        Copy-Item -Path $caminho_pc -Destination $caminho_hd -Force
        Write-Host "✓ Backup copiado para o HD externo!" -ForegroundColor Green
        Write-Host "  Local: $caminho_hd" -ForegroundColor Gray
    }
    catch {
        Write-Host "✗ ERRO ao copiar para o HD externo!" -ForegroundColor Red
        Write-Host "  Verifique se o HD está conectado e tem espaço" -ForegroundColor Red
    }
} else {
    Write-Host "✗ HD externo não encontrado em: $pasta_hd_externo" -ForegroundColor Red
    Write-Host "  Backup mantido apenas no PC local" -ForegroundColor Red
}

# ============================================
# PASSO 3: LIMPAR BACKUPS ANTIGOS
# ============================================

Write-Host "[3/3] Removendo backups antigos..." -ForegroundColor Yellow

# Limpa backups antigos do PC local
$data_limite_pc = (Get-Date).AddDays(-$manter_dias_pc)
$backups_antigos_pc = Get-ChildItem -Path $pasta_pc_local -Filter "*.sql" | Where-Object { $_.LastWriteTime -lt $data_limite_pc }

foreach ($backup in $backups_antigos_pc) {
    Remove-Item -Path $backup.FullName -Force
    Write-Host "  Removido backup antigo do PC: $($backup.Name)" -ForegroundColor Gray
}

# Limpa backups antigos do HD externo (se existir)
if (Test-Path $pasta_hd_externo) {
    $data_limite_hd = (Get-Date).AddDays(-$manter_dias_hd)
    $backups_antigos_hd = Get-ChildItem -Path $pasta_hd_externo -Filter "*.sql" | Where-Object { $_.LastWriteTime -lt $data_limite_hd }
    
    foreach ($backup in $backups_antigos_hd) {
        Remove-Item -Path $backup.FullName -Force
        Write-Host "  Removido backup antigo do HD: $($backup.Name)" -ForegroundColor Gray
    }
}

# ============================================
# FINALIZAR E GERAR LOG
# ============================================

# Cria arquivo de log
$log_path = Join-Path $pasta_pc_local "backup_log.txt"
$log_entry = "$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss') - Backup concluído: $nome_backup"
Add-Content -Path $log_path -Value $log_entry

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "BACKUP CONCLUÍDO COM SUCESSO!" -ForegroundColor Green
Write-Host "Log salvo em: $log_path" -ForegroundColor Gray
Write-Host "========================================" -ForegroundColor Cyan

# Exibe resumo
Write-Host "`nRESUMO:" -ForegroundColor Cyan
Write-Host "- Backup no PC local: $caminho_pc" -ForegroundColor White
Write-Host "- Backup no HD externo: $caminho_hd" -ForegroundColor White
Write-Host "- Mantendo $manter_dias_pc dias no PC" -ForegroundColor White
Write-Host "- Mantendo $manter_dias_hd dias no HD" -ForegroundColor White