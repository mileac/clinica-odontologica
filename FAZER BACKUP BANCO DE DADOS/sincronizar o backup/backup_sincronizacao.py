import os
import shutil
import sqlite3
import zipfile
import paramiko
import stat
from datetime import datetime, timedelta
from pathlib import Path
import schedule
import time
import json

# ============================================
# CONFIGURAÇÕES - VOCÊ SÓ MUDA AQUI!
# ============================================

# Configurações do Banco Local
BANCO_LOCAL = r"C:\Users\Marco Antonio\OneDrive\Área de Trabalho\Dr. Eduardo\clinica_odontologica\instance\clinica.db"

# Configurações do Render.com
RENDER_HOST = "clinica-odontologic-a1ki.onrender.com"
RENDER_USER = "admin"  # Usuário SSH do Render
RENDER_PASSWORD = "admin123"  # Senha SSH
RENDER_BANCO_PATH = "/opt/render/project/src/instance/clinica.db"  # Caminho do banco no Render

# Pastas de Backup
PASTA_BACKUPS = r"C:\Users\Marco Antonio\OneDrive\Área de Trabalho\Dr. Eduardo\clinica_odontologica\instance\Backups\BancoDados"
HD_EXTERNO = r"F:\Backups_Clinica"

# Configurações
DIAS_MANTER_BACKUP = 90  # Dias para manter backups
CRIAR_LOG = True  # Criar arquivo de log

# ============================================
# O RESTO É AUTOMÁTICO - NÃO MEXA DAQUI PRA BAIXO
# ============================================

class BackupSincronizacao:
    def __init__(self):
        self.logs = []
        self.criar_pastas()
        
    def log(self, mensagem, tipo="INFO"):
        """Registra mensagem no console e no log"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        linha = f"[{timestamp}] [{tipo}] {mensagem}"
        print(linha)
        self.logs.append(linha)
        
        if CRIAR_LOG:
            with open(os.path.join(PASTA_BACKUPS, "sincronizacao_log.txt"), "a", encoding="utf-8") as f:
                f.write(linha + "\n")
    
    def criar_pastas(self):
        """Cria todas as pastas necessárias"""
        os.makedirs(PASTA_BACKUPS, exist_ok=True)
        os.makedirs(HD_EXTERNO, exist_ok=True)
        self.log("Pastas verificadas/criadas")
    
    def conectar_render(self):
        """Conecta ao Render via SSH"""
        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.log(f"Conectando ao Render.com em {RENDER_HOST}...")
            ssh.connect(
                hostname=RENDER_HOST,
                username=RENDER_USER,
                password=RENDER_PASSWORD,
                port=22,
                timeout=30
            )
            self.log("✓ Conectado ao Render com sucesso!")
            return ssh
        except Exception as e:
            self.log(f"✗ Erro ao conectar ao Render: {str(e)}", "ERRO")
            return None
    
    def baixar_banco_render(self, ssh, destino_temp):
        """Baixa o arquivo do banco do Render"""
        try:
            sftp = ssh.open_sftp()
            
            # Verificar se o arquivo existe
            try:
                sftp.stat(RENDER_BANCO_PATH)
            except FileNotFoundError:
                self.log(f"Arquivo não encontrado no Render: {RENDER_BANCO_PATH}", "ERRO")
                return False
            
            # Baixar arquivo
            self.log(f"Baixando banco do Render...")
            sftp.get(RENDER_BANCO_PATH, destino_temp)
            sftp.close()
            
            tamanho = os.path.getsize(destino_temp) / (1024 * 1024)
            self.log(f"✓ Banco baixado com sucesso! Tamanho: {tamanho:.2f} MB")
            return True
            
        except Exception as e:
            self.log(f"✗ Erro ao baixar banco: {str(e)}", "ERRO")
            return False
    
    def verificar_banco_local(self):
        """Verifica se o banco local existe e está íntegro"""
        if not os.path.exists(BANCO_LOCAL):
            self.log(f"Banco local não encontrado em: {BANCO_LOCAL}", "AVISO")
            return False
        
        # Testar integridade do SQLite
        try:
            conn = sqlite3.connect(BANCO_LOCAL)
            cursor = conn.cursor()
            cursor.execute("PRAGMA integrity_check")
            resultado = cursor.fetchone()[0]
            conn.close()
            
            if resultado == "ok":
                tamanho = os.path.getsize(BANCO_LOCAL) / (1024 * 1024)
                self.log(f"✓ Banco local íntegro! Tamanho: {tamanho:.2f} MB")
                return True
            else:
                self.log(f"✗ Banco local corrompido!", "ERRO")
                return False
        except Exception as e:
            self.log(f"✗ Erro ao verificar banco local: {str(e)}", "ERRO")
            return False
    
    def fazer_backup_local(self):
        """Faz backup do banco local com consistência"""
        data_hora = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        nome_backup = f"backup_clinica_{data_hora}.db"
        caminho_backup = os.path.join(PASTA_BACKUPS, nome_backup)
        
        try:
            # Usar .backup do SQLite para consistência
            conn = sqlite3.connect(BANCO_LOCAL)
            backup_conn = sqlite3.connect(caminho_backup)
            conn.backup(backup_conn)
            backup_conn.close()
            conn.close()
            
            self.log(f"✓ Backup local criado: {nome_backup}")
            
            # Compactar
            nome_zip = f"backup_clinica_{data_hora}.zip"
            caminho_zip = os.path.join(PASTA_BACKUPS, nome_zip)
            
            with zipfile.ZipFile(caminho_zip, 'w', zipfile.ZIP_DEFLATED) as zipf:
                zipf.write(caminho_backup, os.path.basename(caminho_backup))
            
            os.remove(caminho_backup)
            self.log(f"✓ Backup compactado: {nome_zip}")
            
            return caminho_zip, nome_zip
            
        except Exception as e:
            self.log(f"✗ Erro ao fazer backup: {str(e)}", "ERRO")
            return None, None
    
    def copiar_para_hd_externo(self, arquivo_origem, nome_arquivo):
        """Copia o backup para o HD externo"""
        if not os.path.exists(HD_EXTERNO):
            self.log(f"HD externo não encontrado em: {HD_EXTERNO}", "AVISO")
            return False
        
        try:
            destino = os.path.join(HD_EXTERNO, nome_arquivo)
            shutil.copy2(arquivo_origem, destino)
            self.log(f"✓ Backup copiado para HD externo: {destino}")
            return True
        except Exception as e:
            self.log(f"✗ Erro ao copiar para HD externo: {str(e)}", "ERRO")
            return False
    
    def limpar_backups_antigos(self):
        """Remove backups mais antigos que DIAS_MANTER_BACKUP"""
        data_limite = datetime.now() - timedelta(days=DIAS_MANTER_BACKUP)
        
        for pasta in [PASTA_BACKUPS, HD_EXTERNO]:
            if not os.path.exists(pasta):
                continue
                
            removidos = 0
            for arquivo in os.listdir(pasta):
                if arquivo.startswith("backup_clinica_") and arquivo.endswith(".zip"):
                    caminho = os.path.join(pasta, arquivo)
                    data_mod = datetime.fromtimestamp(os.path.getmtime(caminho))
                    if data_mod < data_limite:
                        os.remove(caminho)
                        removidos += 1
            
            if removidos > 0:
                self.log(f"✓ Removidos {removidos} backups antigos de {os.path.basename(pasta)}")
    
    def atualizar_banco_local(self, banco_temp):
        """Atualiza o banco local com o banco baixado do Render"""
        try:
            # Fazer backup do local antes de atualizar
            backup_local, _ = self.fazer_backup_local()
            
            # Substituir pelo banco do Render
            shutil.copy2(banco_temp, BANCO_LOCAL)
            self.log("✓ Banco local atualizado com dados do Render!")
            
            # Verificar se foi atualizado corretamente
            if self.verificar_banco_local():
                return True
            else:
                # Restaurar backup se falhou
                self.log("Restaurando backup local...", "AVISO")
                shutil.copy2(backup_local, BANCO_LOCAL)
                return False
                
        except Exception as e:
            self.log(f"✗ Erro ao atualizar banco local: {str(e)}", "ERRO")
            return False
    
    def executar(self):
        """Executa o fluxo completo"""
        self.log("="*60)
        self.log("INICIANDO BACKUP E SINCRONIZAÇÃO")
        self.log("="*60)
        
        # 1. Verificar banco local
        self.verificar_banco_local()
        
        # 2. Conectar ao Render e baixar banco
        ssh = self.conectar_render()
        if ssh:
            banco_temp = os.path.join(PASTA_BACKUPS, "temp_render.db")
            if self.baixar_banco_render(ssh, banco_temp):
                # 3. Atualizar banco local
                self.atualizar_banco_local(banco_temp)
                # Limpar arquivo temporário
                if os.path.exists(banco_temp):
                    os.remove(banco_temp)
            ssh.close()
        
        # 4. Fazer backup do banco local (já atualizado)
        arquivo_backup, nome_backup = self.fazer_backup_local()
        
        # 5. Copiar para HD externo
        if arquivo_backup:
            self.copiar_para_hd_externo(arquivo_backup, nome_backup)
        
        # 6. Limpar backups antigos
        self.limpar_backups_antigos()
        
        self.log("="*60)
        self.log("✓ PROCESSO CONCLUÍDO COM SUCESSO!")
        self.log("="*60)
        
        return True

# ============================================
# EXECUÇÃO PRINCIPAL
# ============================================

def executar_agora():
    """Executa o backup imediatamente"""
    backup = BackupSincronizacao()
    backup.executar()

def executar_agendado():
    """Versão para execução agendada (sem input())"""
    backup = BackupSincronizacao()
    backup.executar()
    return 0

if __name__ == "__main__":
    # Verificar se é execução única ou agendada
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--agendado":
        # Modo agendado - sem interação com usuário
        sys.exit(executar_agendado())
    else:
        # Modo manual - com pause no final
        executar_agora()
        print("\nPressione Enter para sair...")
        input()