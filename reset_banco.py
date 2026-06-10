"""
Script para limpar o banco de dados ONLINE (Render)
Executar: python reset_banco.py
"""
import os
import sys

# Adicionar o diretório atual ao path
sys.path.insert(0, os.path.dirname(__file__))

from app import app, db, inicializar_banco

# URL do banco online
DATABASE_URL = "postgresql://admin:idmqu6Fq2YeGTfbiiQs5d0LE1kWEEnKc@dpg-d8jkpns8aovs73d4jfhg-a/clinica_3frt"

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
    
    # Configurar a URL do banco online
    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL + '?sslmode=require'
    
    with app.app_context():
        print("🗑️  Apagando tabelas...")
        db.drop_all()
        
        print("📦 Criando novas tabelas...")
        db.create_all()
        
        print("👤 Criando usuário admin...")
        inicializar_banco()
        
        print()
        print("=" * 50)
        print("✅ BANCO LIMPO COM SUCESSO!")
        print("=" * 50)
        print()
        print("📋 Dados de acesso:")
        print("   • URL: https://clinica-odontologica-a1ki.onrender.com")
        print("   • Usuário: admin")
        print("   • Senha: admin123")
        print()