from app import app, db

with app.app_context():
    db.drop_all()  # Remove tabelas antigas se existirem
    db.create_all()  # Cria todas as tabelas novamente
    print("✅ Banco de dados criado com sucesso!")
    print("📁 Tabelas criadas: Paciente, Consulta, Prontuario, Orcamento, PlanoTratamento")