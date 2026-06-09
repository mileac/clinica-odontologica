import os
import shutil
import sqlite3
import zipfile
from datetime import datetime, timedelta
import subprocess
import sys

# ============================================
# CONFIGURAÇÕES - AJUSTE AQUI
# ============================================

# Caminho do seu banco SQLite LOCAL
BANCO_LOCAL = r"C:\Users\Marco Antonio\OneDrive\Área de Trabalho\Dr. Eduardo\clinica_odontologica\instance\clinica.db"

# Pasta onde ficarão os backups
PASTA_BACKUPS = r"C:\Users\Marco Antonio\OneDrive\Área de Trabalho\Dr. Eduardo\clinica_odontologica\instance\Backups\BancoDados"

# Caminho do HD externo (ajuste a letra)
HD_EXTERNO = r"F:\Backups_Clinica"

# Quantos dias manter os backups
DIAS_MANTER = 90

# ============================================
# FUNÇÕES
# ============================================

def criar_pastas():
    """Cria as pastas necessárias se não existirem"""
    os.makedirs(PASTA_BACKUPS, exist_ok=True)
    os.makedirs(HD_EXTERNO, exist_ok=True)
    print("✓ Pastas verificadas/criadas")

def fazer_backup_consistente(origem, destino):
    """
    Faz backup consistente do SQLite usando o comando .backup
    Isso garante que não haja corrupção mesmo se o banco estiver em uso
    """
    try:
        # Conecta ao banco e executa o backup
        conn = sqlite3.connect(origem)
        backup_conn = sqlite3.connect(destino)
        conn.backup(backup_conn)
        backup_conn.close()
        conn.close()
        return True
    except Exception as e:
        print(f"  Erro no backup consistente: {e}")
        # Fallback: cópia simples
        try:
            shutil.copy2(origem, destino)
            return True
        except Exception as e2:
            print(f"  Erro no fallback: {e2}")
            return False

def compactar_arquivo(arquivo_origem, arquivo_destino):
    """Compacta o arquivo de backup"""
    try:
        with zipfile.ZipFile(arquivo_destino, 'w', zipfile.ZIP_DEFLATED) as zipf:
            zipf.write(arquivo_origem, os.path.basename(arquivo_origem))
        return True
    except Exception as e:
        print(f"  Erro na compactação: {e}")
        return False

def limpar_backups_antigos(pasta, dias):
    """Remove backups mais antigos que 'dias'"""
    if not os.path.exists(pasta):
        return
    
    data_limite = datetime.now() - timedelta(days=dias)
    removidos = 0
    
    for arquivo in os.listdir(pasta):
        if arquivo.startswith("backup_clinica_") and (arquivo.endswith(".zip") or arquivo.endswith(".db")):
            caminho = os.path.join(pasta, arquivo)
            data_mod = datetime.fromtimestamp(os.path.getmtime(caminho))
            if data_mod < data_limite:
                os.remove(caminho)
                removidos += 1
                print(f"  Removido: {arquivo}")
    
    if removidos > 0:
        print(f"  ✓ {removidos} backup(s) antigo(s) removido(s)")

def registrar_log(mensagem):
    """Registra a operação em um arquivo de log"""
    log_path = os.path.join(PASTA_BACKUPS, "backup_log.txt")
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} - {mensagem}\n")

def obter_tamanho_arquivo(caminho):
    """Retorna o tamanho do arquivo em MB"""
    tamanho_bytes = os.path.getsize(caminho)
    return round(tamanho_bytes / (1024 * 1024), 2)

# ============================================
# MAIN
# ============================================

def main():
    print("=" * 50)
    print("BACKUP DO BANCO SQLITE - CLÍNICA")
    print(f"Data: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}")
    print("=" * 50)
    print()
    
    # Criar pastas
    print("[1/5] Verificando pastas...")
    criar_pastas()
    print()
    
    # Verificar se o banco existe
    print("[2/5] Verificando banco de dados...")
    if not os.path.exists(BANCO_LOCAL):
        print(f"  ERRO: Banco não encontrado em {BANCO_LOCAL}")
        print("  Verifique o caminho e tente novamente.")
        input("Pressione Enter para sair...")
        sys.exit(1)
    
    tamanho_mb = obter_tamanho_arquivo(BANCO_LOCAL)
    print(f"  ✓ Banco encontrado - Tamanho: {tamanho_mb} MB")
    print()
    
    # Criar backup
    print("[3/5] Criando backup consistente...")
    data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    nome_backup = f"backup_clinica_{data_hora}.db"
    caminho_backup = os.path.join(PASTA_BACKUPS, nome_backup)
    
    if fazer_backup_consistente(BANCO_LOCAL, caminho_backup):
        print(f"  ✓ Backup criado: {nome_backup}")
        tamanho_backup = obter_tamanho_arquivo(caminho_backup)
        print(f"    Tamanho: {tamanho_backup} MB")
    else:
        print("  ✗ ERRO: Falha ao criar backup!")
        registrar_log(f"ERRO: Falha ao criar backup - {nome_backup}")
        sys.exit(1)
    print()
    
    # Compactar
    print("[4/5] Compactando backup...")
    nome_zip = f"backup_clinica_{data_hora}.zip"
    caminho_zip = os.path.join(PASTA_BACKUPS, nome_zip)
    
    if compactar_arquivo(caminho_backup, caminho_zip):
        print(f"  ✓ Backup compactado: {nome_zip}")
        tamanho_zip = obter_tamanho_arquivo(caminho_zip)
        print(f"    Tamanho compactado: {tamanho_zip} MB")
        # Remover o arquivo .db original (não compactado)
        os.remove(caminho_backup)
        arquivo_final = caminho_zip
        nome_final = nome_zip
    else:
        print("  ⚠ Aviso: Falha na compactação, mantendo arquivo .db")
        arquivo_final = caminho_backup
        nome_final = nome_backup
    print()
    
    # Copiar para HD externo
    print("[5/5] Copiando para HD externo...")
    if os.path.exists(HD_EXTERNO):
        destino_hd = os.path.join(HD_EXTERNO, nome_final)
        try:
            shutil.copy2(arquivo_final, destino_hd)
            print(f"  ✓ Backup copiado para o HD externo!")
            print(f"    Local: {destino_hd}")
        except Exception as e:
            print(f"  ✗ ERRO: Falha ao copiar para HD externo: {e}")
    else:
        print(f"  ✗ ERRO: HD externo não encontrado em {HD_EXTERNO}")
        print("  Verifique se o HD está conectado e a letra da unidade está correta")
    print()
    
    # Limpar backups antigos
    print(f"Limpando backups antigos (mais de {DIAS_MANTER} dias)...")
    limpar_backups_antigos(PASTA_BACKUPS, DIAS_MANTER)
    limpar_backups_antigos(HD_EXTERNO, DIAS_MANTER)
    print()
    
    # Registrar no log
    registrar_log(f"Backup concluído: {nome_final}")
    
    # Finalizar
    print("=" * 50)
    print("BACKUP CONCLUÍDO COM SUCESSO!")
    print("=" * 50)
    print()
    print("RESUMO FINAL:")
    print("-" * 40)
    print(f"Banco original: {BANCO_LOCAL}")
    print(f"Backup criado:  {arquivo_final}")
    print(f"HD externo:     {os.path.join(HD_EXTERNO, nome_final)}")
    print(f"Log salvo em:   {os.path.join(PASTA_BACKUPS, 'backup_log.txt')}")
    print()
    print(f"Backups mantidos por {DIAS_MANTER} dias")
    print()
    
    input("Pressione Enter para sair...")

if __name__ == "__main__":
    main()