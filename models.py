# models.py - Todos os modelos do banco de dados

from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class Usuario(db.Model):
    """Modelo de usuários do sistema (dentistas/secretárias)"""
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cro = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100), unique=True)
    senha = db.Column(db.String(100), nullable=False)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Usuario {self.nome}>'


class Paciente(db.Model):
    """Modelo de pacientes da clínica"""
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=False)
    email = db.Column(db.String(100))
    data_nascimento = db.Column(db.Date)
    criado_em = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Paciente {self.nome}>'


class Consulta(db.Model):
    """Modelo de consultas agendadas"""
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    data_hora = db.Column(db.DateTime, nullable=False)
    status = db.Column(db.String(20), default='pendente')  # pendente, confirmada, realizada, cancelada
    confirmada_whatsapp = db.Column(db.Boolean, default=False)
    token_confirmacao = db.Column(db.String(100), unique=True)
    paciente = db.relationship('Paciente', backref='consultas')

    def __repr__(self):
        return f'<Consulta {self.id} - {self.paciente.nome}>'


class Prontuario(db.Model):
    """Modelo de prontuário eletrônico"""
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    queixa_principal = db.Column(db.Text)
    historico_doenca = db.Column(db.Text)
    exame_fisico = db.Column(db.Text)
    diagnostico = db.Column(db.Text)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Prontuario Paciente:{self.paciente_id}>'


class Orcamento(db.Model):
    """Modelo de orçamentos"""
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    descricao = db.Column(db.Text)
    valor_total = db.Column(db.Float)
    status = db.Column(db.String(20), default='pendente')  # pendente, aprovado, recusado
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<Orcamento {self.id} - R$ {self.valor_total}>'


class PlanoTratamento(db.Model):
    """Modelo de planos de tratamento"""
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    titulo = db.Column(db.String(200))
    descricao = db.Column(db.Text)
    etapas = db.Column(db.Text)  # JSON com etapas do tratamento
    ativo = db.Column(db.Boolean, default=True)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f'<PlanoTratamento {self.titulo}>'


class Atendimento(db.Model):
    """Modelo de atendimentos clínicos (fichas)"""
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    data_atendimento = db.Column(db.DateTime, default=datetime.utcnow)
    dentes_marcados = db.Column(db.Text)  # Dentes marcados no odontograma
    procedimentos = db.Column(db.Text)    # Procedimentos realizados (separados por |)
    observacoes = db.Column(db.Text)
    proxima_consulta = db.Column(db.DateTime)
    paciente = db.relationship('Paciente', backref='atendimentos')

    def __repr__(self):
        return f'<Atendimento {self.id} - {self.data_atendimento}>'


class DesenhoFicha(db.Model):
    """Modelo para salvar desenhos da arcada dentária"""
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    data_criacao = db.Column(db.DateTime, default=datetime.utcnow)
    imagem_desenho = db.Column(db.Text)  # Base64 da imagem
    tratamentos = db.Column(db.Text)
    observacoes = db.Column(db.Text)
    paciente = db.relationship('Paciente', backref='desenhos')

    def __repr__(self):
        return f'<DesenhoFicha {self.id}>'


class Pagamento(db.Model):
    """Modelo de pagamentos e despesas"""
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=True)
    data_pagamento = db.Column(db.DateTime, default=datetime.utcnow)
    valor = db.Column(db.Float, nullable=False)
    descricao = db.Column(db.String(200))
    tipo = db.Column(db.String(20), default='entrada')  # entrada ou saida
    forma_pagamento = db.Column(db.String(50))  # dinheiro, cartao, pix, transferencia
    paciente = db.relationship('Paciente', backref='pagamentos')

    def __repr__(self):
        return f'<Pagamento R$ {self.valor} - {self.tipo}>'


class Atestado(db.Model):
    """Modelo de atestados médicos"""
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('paciente.id'), nullable=False)
    data_emissao = db.Column(db.DateTime, default=datetime.utcnow)
    cid = db.Column(db.String(10))  # Código da Classificação Internacional de Doenças
    diagnostico = db.Column(db.Text)
    periodo_inicio = db.Column(db.Date)
    periodo_fim = db.Column(db.Date)
    recomendacoes = db.Column(db.Text)
    paciente = db.relationship('Paciente', backref='atestados')

    def __repr__(self):
        return f'<Atestado {self.id} - {self.cid}>'