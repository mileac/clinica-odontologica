"""
Script para fazer BACKUP do banco de dados ONLINE (Render) para o seu computador.
Executar localmente: python backup_banco.py
"""
import os
import sys
import json
from datetime import datetime

# Adicionar o diretório atual ao path para importar o app
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, Paciente, Usuario, Agendamento, FichaClinica, FichaOrtodontica, FichaTratamento, Orcamento, Recibo, Despesa, ConfiguracaoClinica

# URL do banco de dados online
DATABASE_URL = os.environ.get(
    'DATABASE_URL', 
    "postgresql://admin:idmqu6Fq2YeGTfbiiQs5d0LE1kWEEnKc@dpg-d8jkpns8aovs73d4jfhg-a/clinica_3frt"
)

def gerar_backup():
    print("=" * 50)
    print("💾 INICIANDO BACKUP DO BANCO DE DADOS ONLINE")
    print("=" * 50)
    
    # Configurar a URL do banco de forma segura
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL_CORRIGIDA = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
    else:
        DATABASE_URL_CORRIGIDA = DATABASE_URL
        
    if 'postgresql://' in DATABASE_URL_CORRIGIDA and '?sslmode=' not in DATABASE_URL_CORRIGIDA:
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL_CORRIGIDA + '?sslmode=require'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL_CORRIGIDA

    # Criar pasta de backups locais se não existir
    if not os.path.exists('backups_locais'):
        os.makedirs('backups_locais')
        
    data_atual = datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
    nome_arquivo = f"backups_locais/backup_clinica_{data_atual}.json"

    with app.app_context():
        print("🔄 Coletando dados da nuvem... Aguarde...")
        try:
            dados_backup = {
                "metadados": {
                    "data_geracao": data_atual,
                    "descricao": "Backup completo do sistema odontologico"
                },
                "configuracoes": [c.to_dict() if hasattr(c, 'to_dict') else {col.name: getattr(c, col.name) for col in c.__table__.columns} for c in ConfiguracaoClinica.query.all()],
                "usuarios": [{col.name: getattr(u, col.name) for col in u.__table__.columns if col.name != 'senha_hash'} for u in Usuario.query.all()],
                "pacientes": [{col.name: (getattr(p, col.name).isoformat() if isinstance(getattr(p, col.name), (datetime, datetime.date)) else getattr(p, col.name)) for col in p.__table__.columns} for p in Paciente.query.all()],
                "agendamentos": [{col.name: (getattr(a, col.name).isoformat() if isinstance(getattr(a, col.name), (datetime, datetime.date)) else getattr(a, col.name)) for col in a.__table__.columns} for a in Agendamento.query.all()],
                "fichas_clinicas": [{col.name: getattr(f, col.name) for col in f.__table__.columns} for f in FichaClinica.query.all()],
                "fichas_ortodonticas": [{col.name: getattr(f, col.name) for col in f.__table__.columns} for f in FichaOrtodontica.query.all()],
                "fichas_tratamentos": [{col.name: (getattr(t, col.name).isoformat() if isinstance(getattr(t, col.name), (datetime, datetime.date)) else getattr(t, col.name)) for col in t.__table__.columns} for t in FichaTratamento.query.all()],
                "orcamentos": [{col.name: (getattr(o, col.name).isoformat() if isinstance(getattr(o, col.name), (datetime, datetime.date)) else getattr(o, col.name)) for col in o.__table__.columns} for o in Orcamento.query.all()],
                "recibos": [{col.name: (getattr(r, col.name).isoformat() if isinstance(getattr(r, col.name), (datetime, datetime.date)) else getattr(r, col.name)) for col in r.__table__.columns} for r in Recibo.query.all()],
                "despesas": [{col.name: (getattr(d, col.name).isoformat() if isinstance(getattr(d, col.name), (datetime, datetime.date)) else getattr(d, col.name)) for col in d.__table__.columns} for d in Despesa.query.all()]
            }
            
            # Salva o arquivo JSON localmente de forma organizada
            with open(nome_arquivo, 'w', encoding='utf-8') as f:
                json.dump(dados_backup, f, indent=4, ensure_ascii=False)
                
            print()
            print("=" * 50)
            print(f"✓ BACKUP CONCLUÍDO COM SUCESSO!")
            print(f"📁 Arquivo salvo em: {nome_arquivo}")
            print("=" * 50)
            
        except Exception as e:
            print(f"❌ Erro ao tentar extrair dados para o backup: {str(e)}")

if __name__ == '__main__':
    gerar_backup()