"""
Script para limpar o banco de dados ONLINE (Render)
Executar: python reset_banco.py
"""
import os
import sys

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, inicializar_banco

# Tenta ler a URL do ambiente (Config Vars do Render). Se não encontrar, usa a string padrão.
DATABASE_URL = os.environ.get(
    'DATABASE_URL', 
    "postgresql://admin:idmqu6Fq2YeGTfbiiQs5d0LE1kWEEnKc@dpg-d8jkpns8aovs73d4jfhg-a/clinica_3frt"
)

if __name__ == '__main__':
    print("=" * 50)
    print("🗄️  LIMPEZA DO BANCO DE DADOS ONLINE")
    print("=" * 50)
    print()
    print(f"⚠️  ATENÇÃO!")
    print(f"⚠️  Isso vai APAGAR TODOS os dados do banco online!")
    print(f"⚠️  Banco: Render PostgreSQL")
    print()
    
    resposta = input("Digite SIM para confirmar: ")
    
    if resposta.upper() != "SIM":
        print("Operação cancelada.")
        sys.exit()
    
    print()
    print("🔄 Conectando ao banco online...")
    
    # Garante que a URL usa o formato correto exigido pelas novas versões do SQLAlchemy
    if DATABASE_URL.startswith('postgres://'):
        DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
        
    if 'postgresql://' in DATABASE_URL and '?sslmode=' not in DATABASE_URL:
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL + '?sslmode=require'
    else:
        app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL
    
    with app.app_context():
        print("🗑️  Apagando tabelas...")
        db.drop_all()
        
        print("📦 Criando novas tabelas...")
        db.create_all()
        
        print("🌱 Inserindo dados iniciais (Admin/Configurações)...")
        inicializar_banco()
        
        print()
        print("=" * 50)
        print("✓ SUCESSO: Banco de dados limpo e reinicializado!")
        print("=" * 50)