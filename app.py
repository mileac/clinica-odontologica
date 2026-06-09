from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session, Response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta
from dateutil.relativedelta import relativedelta
import os
import json
from functools import wraps
from werkzeug.utils import secure_filename

# Inicialização do app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_aqui_123456'
DATABASE_URL = os.environ.get('DATABASE_URL', 'sqlite:///clinica.db')
if DATABASE_URL and DATABASE_URL.startswith('postgres://'):
    DATABASE_URL = DATABASE_URL.replace('postgres://', 'postgresql://', 1)
app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URL

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Configuração para upload de arquivos
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'pdf', 'doc', 'docx'}

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Inicialização do banco de dados
db = SQLAlchemy(app)

# Inicialização do Login Manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# ==================== MODELOS ====================

class Usuario(UserMixin, db.Model):
    __tablename__ = 'usuarios'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)
    nome_completo = db.Column(db.String(200))
    email = db.Column(db.String(120))
    cargo = db.Column(db.String(50), default='Dentista')
    cro = db.Column(db.String(20))
    especialidade = db.Column(db.String(100))
    comissao_percentual = db.Column(db.Float, default=0.0)
    ativo = db.Column(db.Boolean, default=True)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    
    agendamentos = db.relationship('Agendamento', backref='profissional', lazy=True)
    tratamentos = db.relationship('FichaTratamento', backref='profissional', lazy=True)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
        
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def tem_permissao(self, modulo):
        permissoes = {
            'Admin': [
                'dashboard', 'pacientes', 'ficha_clinica', 'ficha_ortodontica',
                'ficha_tratamento', 'odontograma', 'orcamento', 'agenda',
                'atestados', 'historico', 'aniversariantes', 'financeiro',
                'configuracao', 'funcionarios', 'comissoes', 'arquivos',
                'editar_pacientes', 'deletar_pacientes', 'editar_tratamentos',
                'excluir_tratamentos', 'ver_financeiro', 'editar_configuracao'
            ],
            'Dentista': [
                'dashboard', 'pacientes', 'ficha_clinica', 'ficha_ortodontica',
                'ficha_tratamento', 'odontograma', 'orcamento', 'agenda',
                'atestados', 'historico', 'aniversariantes', 'arquivos',
                'editar_tratamentos'
            ],
            'Secretaria': [
                'dashboard', 'pacientes', 'ficha_clinica', 'agenda',
                'atestados', 'aniversariantes', 'arquivos',
                'editar_pacientes'
            ],
            'Auxiliar': [
                'dashboard', 'pacientes', 'agenda', 'arquivos'
            ]
        }
        return modulo in permissoes.get(self.cargo, [])

class ConfiguracaoClinica(db.Model):
    __tablename__ = 'configuracao_clinica'
    
    id = db.Column(db.Integer, primary_key=True)
    nome_clinica = db.Column(db.String(200), nullable=False)
    endereco = db.Column(db.String(300), nullable=False)
    cidade = db.Column(db.String(100))
    estado = db.Column(db.String(2))
    cep = db.Column(db.String(10))
    email = db.Column(db.String(120))
    telefone = db.Column(db.String(20))
    nome_doutor = db.Column(db.String(200))
    cro = db.Column(db.String(20))
    
    @staticmethod
    def get_configuracao():
        config = ConfiguracaoClinica.query.first()
        if not config:
            config = ConfiguracaoClinica(
                nome_clinica='Sua Clínica Odontológica',
                endereco='Endereço da Clínica',
                cidade='Cidade',
                estado='UF',
                cep='00000-000',
                email='clinica@email.com',
                telefone='(00) 0000-0000',
                nome_doutor='Dr. Nome do Dentista',
                cro='CRO-00000'
            )
            db.session.add(config)
            db.session.commit()
        return config

class Paciente(db.Model):
    __tablename__ = 'pacientes'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    cpf = db.Column(db.String(14), unique=True, nullable=False)
    data_nascimento = db.Column(db.Date, nullable=False)
    endereco = db.Column(db.String(300))
    celular = db.Column(db.String(20))
    email = db.Column(db.String(120))
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)
    observacoes = db.Column(db.Text)
    ativo = db.Column(db.Boolean, default=True)
    
    fichas_tratamento = db.relationship('FichaTratamento', backref='paciente', lazy=True)
    agendamentos = db.relationship('Agendamento', backref='paciente', lazy=True)
    historico = db.relationship('HistoricoPaciente', backref='paciente', lazy=True)
    
    def calcular_idade(self):
        hoje = date.today()
        idade = relativedelta(hoje, self.data_nascimento)
        return idade.years

class FichaOrtodontica(db.Model):
    __tablename__ = 'fichas_ortodonticas'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    data_abertura = db.Column(db.Date, default=date.today)
    tipo_denticao = db.Column(db.String(50))
    classe_angle = db.Column(db.String(50))
    tipo_mordida = db.Column(db.String(50))
    apinhamento = db.Column(db.String(50))
    diastemas = db.Column(db.Boolean, default=False)
    linha_media = db.Column(db.String(50))
    sna = db.Column(db.Float)
    snb = db.Column(db.Float)
    anb = db.Column(db.Float)
    diagnostico = db.Column(db.Text)
    plano_tratamento = db.Column(db.Text)
    aparelho_recomendado = db.Column(db.String(200))
    tempo_estimado = db.Column(db.Integer)
    valor_total = db.Column(db.Float)
    observacoes = db.Column(db.Text)
    status = db.Column(db.String(50), default='Em andamento')

class FichaClinica(db.Model):
    __tablename__ = 'fichas_clinicas'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    data_preenchimento = db.Column(db.Date, default=date.today)
    tem_alergia = db.Column(db.Boolean, default=False)
    qual_alergia = db.Column(db.Text)
    usa_antibioticos = db.Column(db.Boolean, default=False)
    qual_antibiotico = db.Column(db.Text)
    sensibilidade_medicamentos = db.Column(db.Boolean, default=False)
    quais_medicamentos_sensivel = db.Column(db.Text)
    toma_medicamento = db.Column(db.Boolean, default=False)
    qual_medicamento = db.Column(db.Text)
    usa_anestesico = db.Column(db.Boolean, default=False)
    qual_anestesico = db.Column(db.Text)
    tem_problema_saude = db.Column(db.Boolean, default=False)
    qual_problema_saude = db.Column(db.Text)
    pressao_arterial = db.Column(db.String(20))
    observacoes = db.Column(db.Text)
    paciente = db.relationship('Paciente', backref=db.backref('ficha_clinica', uselist=False))

class FichaTratamento(db.Model):
    __tablename__ = 'fichas_tratamento'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    profissional_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    data = db.Column(db.Date, default=date.today)
    dente = db.Column(db.String(10))
    procedimento = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    valor = db.Column(db.Float, nullable=False)
    valor_pago = db.Column(db.Float, default=0.0)
    status_pagamento = db.Column(db.String(50), default='Pendente')
    forma_pagamento = db.Column(db.String(50))
    observacoes = db.Column(db.Text)
    
    @property
    def saldo_restante(self):
        return self.valor - self.valor_pago

class Agendamento(db.Model):
    __tablename__ = 'agendamentos'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    profissional_id = db.Column(db.Integer, db.ForeignKey('usuarios.id'))
    data_hora = db.Column(db.DateTime, nullable=False)
    duracao = db.Column(db.Integer, default=60)
    procedimento = db.Column(db.String(200))
    status = db.Column(db.String(50), default='Agendado')
    observacoes = db.Column(db.Text)

class HistoricoPaciente(db.Model):
    __tablename__ = 'historico_pacientes'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    acao = db.Column(db.String(50))
    descricao = db.Column(db.Text)
    profissional = db.Column(db.String(200))

class Odontograma(db.Model):
    __tablename__ = 'odontogramas'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    data_atualizacao = db.Column(db.Date, default=date.today)
    dentes = db.Column(db.Text, default='{}')
    observacoes = db.Column(db.Text)
    paciente = db.relationship('Paciente', backref=db.backref('odontograma', uselist=False))

class Orcamento(db.Model):
    __tablename__ = 'orcamentos'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    data_criacao = db.Column(db.Date, default=date.today)
    status = db.Column(db.String(20), default='Aguardando')
    valor_total = db.Column(db.Float, default=0.0)
    parcelas = db.Column(db.Integer, default=1)
    valor_parcela = db.Column(db.Float, default=0.0)
    acrescimo_percentual = db.Column(db.Float, default=0.0)
    acrescimo_valor = db.Column(db.Float, default=0.0)
    valor_total_com_acrescimo = db.Column(db.Float, default=0.0)
    data_aprovacao = db.Column(db.Date)
    observacoes = db.Column(db.Text)
    paciente = db.relationship('Paciente', backref=db.backref('orcamentos', lazy=True))
    itens = db.relationship('ItemOrcamento', backref='orcamento', lazy=True, cascade='all, delete-orphan')

class ItemOrcamento(db.Model):
    __tablename__ = 'itens_orcamento'
    
    id = db.Column(db.Integer, primary_key=True)
    orcamento_id = db.Column(db.Integer, db.ForeignKey('orcamentos.id'), nullable=False)
    dente = db.Column(db.String(10))
    procedimento = db.Column(db.String(200), nullable=False)
    descricao = db.Column(db.Text)
    valor = db.Column(db.Float, nullable=False)
    quantidade = db.Column(db.Integer, default=1)

class ArquivoPaciente(db.Model):
    __tablename__ = 'arquivos_pacientes'
    
    id = db.Column(db.Integer, primary_key=True)
    paciente_id = db.Column(db.Integer, db.ForeignKey('pacientes.id'), nullable=False)
    nome_original = db.Column(db.String(200))
    nome_arquivo = db.Column(db.String(200))
    tipo = db.Column(db.String(50))
    categoria = db.Column(db.String(50))
    descricao = db.Column(db.Text)
    data_upload = db.Column(db.DateTime, default=datetime.utcnow)
    paciente = db.relationship('Paciente', backref=db.backref('arquivos', lazy=True))

class CategoriaDespesa(db.Model):
    __tablename__ = 'categorias_despesas'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    icone = db.Column(db.String(50), default='bi bi-cash')
    cor = db.Column(db.String(20), default='#607D8B')
    fixa = db.Column(db.Boolean, default=False)
    
    despesas = db.relationship('Despesa', backref='categoria', lazy=True)

class Despesa(db.Model):
    __tablename__ = 'despesas'
    
    id = db.Column(db.Integer, primary_key=True)
    categoria_id = db.Column(db.Integer, db.ForeignKey('categorias_despesas.id'))
    data = db.Column(db.Date, default=date.today)
    descricao = db.Column(db.String(200), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    comprovante = db.Column(db.String(200))  # nome do arquivo
    recorrente = db.Column(db.Boolean, default=False)  # despesa fixa mensal
    pago = db.Column(db.Boolean, default=True)
    observacoes = db.Column(db.Text)
    data_cadastro = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== FUNÇÕES AUXILIARES ====================

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(Usuario, int(user_id))

def requer_permissao(modulo):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
            if not current_user.tem_permissao(modulo):
                flash('Você não tem permissão para acessar esta área!', 'error')
                return redirect(url_for('dashboard'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# ==================== ROTAS PRINCIPAIS ====================

@app.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        try:
            username = request.form['username']
            password = request.form['password']
            
            usuario = Usuario.query.filter_by(username=username, ativo=True).first()
            
            if usuario and usuario.check_password(password):
                login_user(usuario)
                flash(f'Bem-vindo(a), {usuario.nome_completo}!', 'success')
                return redirect(url_for('dashboard'))
            else:
                flash('Usuário ou senha incorretos!', 'error')
        except Exception as e:
            flash('Erro ao fazer login.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/dashboard')
@login_required
def dashboard():
    config = ConfiguracaoClinica.get_configuracao()
    total_pacientes = Paciente.query.filter_by(ativo=True).count()
    hoje = date.today()
    
    agendamentos_hoje = Agendamento.query.filter(
        db.func.date(Agendamento.data_hora) == hoje
    ).order_by(Agendamento.data_hora).all()
    
    total_agendamentos_hoje = len(agendamentos_hoje)
    amanha = hoje + timedelta(days=1)
    agendamentos_amanha = Agendamento.query.filter(
        db.func.date(Agendamento.data_hora) == amanha
    ).order_by(Agendamento.data_hora).all()
    
    seis_meses_atras = hoje - relativedelta(months=6)
    pacientes_sem_retorno = db.session.query(Paciente).join(
        FichaTratamento
    ).filter(
        FichaTratamento.data < seis_meses_atras,
        Paciente.ativo == True
    ).distinct().limit(5).all()
    
    total_financeiro_pendente = db.session.query(
        db.func.sum(FichaTratamento.valor - FichaTratamento.valor_pago)
    ).filter(FichaTratamento.status_pagamento != 'Pago').scalar() or 0
    
    aniversariantes = Paciente.query.filter(
        db.extract('month', Paciente.data_nascimento) == hoje.month,
        Paciente.ativo == True
    ).all()
    
    return render_template('dashboard.html', 
                         config=config,
                         total_pacientes=total_pacientes,
                         total_agendamentos_hoje=total_agendamentos_hoje,
                         agendamentos_hoje_lista=agendamentos_hoje,
                         agendamentos_amanha=agendamentos_amanha,
                         pacientes_sem_retorno=pacientes_sem_retorno,
                         total_financeiro_pendente=total_financeiro_pendente,
                         aniversariantes=aniversariantes,
                         hoje=hoje)

# ==================== ROTAS DE PROFISSIONAIS ====================

@app.route('/api/profissionais')
@login_required
def api_profissionais():
    profissionais = Usuario.query.filter_by(ativo=True).all()
    resultado = [{'id': p.id, 'nome': p.nome_completo, 'cargo': p.cargo} for p in profissionais]
    return jsonify(resultado)

# ==================== ROTAS DE CONFIGURAÇÃO ====================

@app.route('/configuracao', methods=['GET', 'POST'])
@requer_permissao('editar_configuracao')
def configuracao():
    config = ConfiguracaoClinica.get_configuracao()
    if request.method == 'POST':
        config.nome_clinica = request.form['nome_clinica']
        config.endereco = request.form['endereco']
        config.cidade = request.form['cidade']
        config.estado = request.form['estado']
        config.cep = request.form['cep']
        config.email = request.form['email']
        config.telefone = request.form['telefone']
        config.nome_doutor = request.form['nome_doutor']
        config.cro = request.form['cro']
        db.session.commit()
        flash('Configurações atualizadas!', 'success')
        return redirect(url_for('configuracao'))
    return render_template('configuracao.html', config=config)

# ==================== ROTAS DE PACIENTES ====================

@app.route('/pacientes')
@requer_permissao('pacientes')
def listar_pacientes():
    config = ConfiguracaoClinica.get_configuracao()
    pacientes = Paciente.query.filter_by(ativo=True).all()
    return render_template('pacientes/listar.html', config=config, pacientes=pacientes)

@app.route('/pacientes/buscar')
@login_required
def buscar_pacientes():
    termo = request.args.get('termo', '')
    pacientes = Paciente.query.filter(
        db.or_(
            Paciente.nome.ilike(f'%{termo}%'),
            Paciente.cpf.ilike(f'%{termo}%')
        ),
        Paciente.ativo == True
    ).all()
    resultado = []
    for p in pacientes:
        resultado.append({
            'id': p.id, 'nome': p.nome, 'cpf': p.cpf,
            'idade': p.calcular_idade(), 'celular': p.celular
        })
    return jsonify(resultado)

@app.route('/pacientes/cadastrar', methods=['GET', 'POST'])
@requer_permissao('editar_pacientes')
def cadastrar_paciente():
    config = ConfiguracaoClinica.get_configuracao()
    if request.method == 'POST':
        cpf = request.form['cpf']
        paciente_existente = Paciente.query.filter_by(cpf=cpf, ativo=True).first()
        if paciente_existente:
            flash(f'CPF {cpf} já cadastrado!', 'error')
            return redirect(url_for('cadastrar_paciente'))
        try:
            paciente = Paciente(
                nome=request.form['nome'], cpf=cpf,
                data_nascimento=datetime.strptime(request.form['data_nascimento'], '%Y-%m-%d').date(),
                endereco=request.form['endereco'], celular=request.form['celular'],
                email=request.form['email'], observacoes=request.form.get('observacoes', '')
            )
            db.session.add(paciente)
            db.session.flush()
            historico = HistoricoPaciente(
                paciente_id=paciente.id, acao='Cadastro',
                descricao='Paciente cadastrado', profissional=current_user.nome_completo
            )
            db.session.add(historico)
            db.session.commit()
            flash('Paciente cadastrado!', 'success')
            return redirect(url_for('listar_pacientes'))
        except Exception as e:
            db.session.rollback()
            flash('Erro ao cadastrar.', 'error')
    return render_template('pacientes/cadastrar.html', config=config)

@app.route('/pacientes/editar/<int:id>', methods=['GET', 'POST'])
@requer_permissao('editar_pacientes')
def editar_paciente(id):
    config = ConfiguracaoClinica.get_configuracao()
    paciente = db.session.get(Paciente, id)
    if not paciente:
        flash('Paciente não encontrado!', 'error')
        return redirect(url_for('listar_pacientes'))
    if request.method == 'POST':
        paciente.nome = request.form['nome']
        paciente.cpf = request.form['cpf']
        paciente.data_nascimento = datetime.strptime(request.form['data_nascimento'], '%Y-%m-%d').date()
        paciente.endereco = request.form['endereco']
        paciente.celular = request.form['celular']
        paciente.email = request.form['email']
        paciente.observacoes = request.form.get('observacoes', '')
        historico = HistoricoPaciente(
            paciente_id=paciente.id, acao='Edição',
            descricao='Dados atualizados', profissional=current_user.nome_completo
        )
        db.session.add(historico)
        db.session.commit()
        flash('Paciente atualizado!', 'success')
        return redirect(url_for('listar_pacientes'))
    return render_template('pacientes/editar.html', config=config, paciente=paciente)

@app.route('/pacientes/deletar/<int:id>')
@requer_permissao('deletar_pacientes')
def deletar_paciente(id):
    paciente = db.session.get(Paciente, id)
    if paciente:
        paciente.ativo = False
        historico = HistoricoPaciente(
            paciente_id=paciente.id, acao='Exclusão',
            descricao='Paciente removido', profissional=current_user.nome_completo
        )
        db.session.add(historico)
        db.session.commit()
        flash('Paciente removido!', 'success')
    return redirect(url_for('listar_pacientes'))

@app.route('/pacientes/<int:id>')
@requer_permissao('pacientes')
def visualizar_paciente(id):
    config = ConfiguracaoClinica.get_configuracao()
    paciente = db.session.get(Paciente, id)
    if not paciente:
        flash('Paciente não encontrado!', 'error')
        return redirect(url_for('listar_pacientes'))
    return render_template('pacientes/visualizar.html', config=config, paciente=paciente)

# ==================== ROTAS DE FICHAS ====================

@app.route('/ficha-ortodontica/<int:paciente_id>', methods=['GET', 'POST'])
@requer_permissao('ficha_ortodontica')
def ficha_ortodontica(paciente_id):
    config = ConfiguracaoClinica.get_configuracao()
    paciente = db.session.get(Paciente, paciente_id)
    if not paciente:
        flash('Paciente não encontrado!', 'error')
        return redirect(url_for('listar_pacientes'))
    ficha = FichaOrtodontica.query.filter_by(paciente_id=paciente_id).first()
    if request.method == 'POST':
        if not ficha:
            ficha = FichaOrtodontica(paciente_id=paciente_id)
            db.session.add(ficha)
        ficha.tipo_denticao = request.form['tipo_denticao']
        ficha.classe_angle = request.form['classe_angle']
        ficha.tipo_mordida = request.form['tipo_mordida']
        ficha.apinhamento = request.form['apinhamento']
        ficha.diastemas = 'diastemas' in request.form
        ficha.linha_media = request.form['linha_media']
        ficha.sna = float(request.form.get('sna', 0) or 0)
        ficha.snb = float(request.form.get('snb', 0) or 0)
        ficha.anb = float(request.form.get('anb', 0) or 0)
        ficha.diagnostico = request.form['diagnostico']
        ficha.plano_tratamento = request.form['plano_tratamento']
        ficha.aparelho_recomendado = request.form['aparelho_recomendado']
        ficha.tempo_estimado = int(request.form['tempo_estimado'] or 0)
        ficha.valor_total = float(request.form['valor_total'] or 0)
        ficha.observacoes = request.form.get('observacoes', '')
        db.session.commit()
        flash('Ficha ortodôntica salva!', 'success')
        return redirect(url_for('visualizar_paciente', id=paciente_id))
    return render_template('fichas/ortodontica.html', config=config, paciente=paciente, ficha=ficha)

@app.route('/ficha-clinica/<int:paciente_id>', methods=['GET', 'POST'])
@requer_permissao('ficha_clinica')
def ficha_clinica(paciente_id):
    config = ConfiguracaoClinica.get_configuracao()
    paciente = db.session.get(Paciente, paciente_id)
    if not paciente:
        flash('Paciente não encontrado!', 'error')
        return redirect(url_for('listar_pacientes'))
    ficha = FichaClinica.query.filter_by(paciente_id=paciente_id).first()
    if request.method == 'POST':
        if not ficha:
            ficha = FichaClinica(paciente_id=paciente_id)
            db.session.add(ficha)
        ficha.tem_alergia = 'tem_alergia' in request.form
        ficha.qual_alergia = request.form.get('qual_alergia', '')
        ficha.usa_antibioticos = 'usa_antibioticos' in request.form
        ficha.qual_antibiotico = request.form.get('qual_antibiotico', '')
        ficha.sensibilidade_medicamentos = 'sensibilidade_medicamentos' in request.form
        ficha.quais_medicamentos_sensivel = request.form.get('quais_medicamentos_sensivel', '')
        ficha.toma_medicamento = 'toma_medicamento' in request.form
        ficha.qual_medicamento = request.form.get('qual_medicamento', '')
        ficha.usa_anestesico = 'usa_anestesico' in request.form
        ficha.qual_anestesico = request.form.get('qual_anestesico', '')
        ficha.tem_problema_saude = 'tem_problema_saude' in request.form
        ficha.qual_problema_saude = request.form.get('qual_problema_saude', '')
        ficha.pressao_arterial = request.form.get('pressao_arterial', '')
        ficha.observacoes = request.form.get('observacoes', '')
        db.session.commit()
        historico = HistoricoPaciente(
            paciente_id=paciente.id, acao='Ficha Clínica',
            descricao='Ficha clínica atualizada', profissional=current_user.nome_completo
        )
        db.session.add(historico)
        db.session.commit()
        flash('Ficha clínica salva!', 'success')
        return redirect(url_for('visualizar_paciente', id=paciente_id))
    return render_template('fichas/clinica.html', config=config, paciente=paciente, ficha=ficha)

@app.route('/ficha-tratamento/<int:paciente_id>', methods=['GET', 'POST'])
@requer_permissao('ficha_tratamento')
def ficha_tratamento(paciente_id):
    config = ConfiguracaoClinica.get_configuracao()
    paciente = db.session.get(Paciente, paciente_id)
    if not paciente:
        flash('Paciente não encontrado!', 'error')
        return redirect(url_for('listar_pacientes'))
    tratamentos = FichaTratamento.query.filter_by(paciente_id=paciente_id).order_by(FichaTratamento.data.desc()).all()
    if request.method == 'POST':
        try:
            tratamento = FichaTratamento(
                paciente_id=paciente_id,
                profissional_id=current_user.id,
                data=datetime.strptime(request.form['data'], '%Y-%m-%d').date(),
                dente=request.form['dente'],
                procedimento=request.form['procedimento'],
                descricao=request.form['descricao'],
                valor=float(request.form['valor']),
                valor_pago=float(request.form.get('valor_pago', 0) or 0),
                forma_pagamento=request.form.get('forma_pagamento', ''),
                observacoes=request.form.get('observacoes', '')
            )
            if tratamento.valor_pago >= tratamento.valor:
                tratamento.status_pagamento = 'Pago'
            elif tratamento.valor_pago > 0:
                tratamento.status_pagamento = 'Parcial'
            else:
                tratamento.status_pagamento = 'Pendente'
            db.session.add(tratamento)
            historico = HistoricoPaciente(
                paciente_id=paciente.id, acao='Tratamento',
                descricao=f'{tratamento.procedimento}', profissional=current_user.nome_completo
            )
            db.session.add(historico)
            db.session.commit()
            flash('Tratamento registrado!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {str(e)}', 'error')
        return redirect(url_for('ficha_tratamento', paciente_id=paciente_id))
    return render_template('fichas/tratamento.html', config=config, paciente=paciente, tratamentos=tratamentos)

@app.route('/tratamento/editar/<int:id>', methods=['GET', 'POST'])
@requer_permissao('editar_tratamentos')
def editar_tratamento(id):
    tratamento = db.session.get(FichaTratamento, id)
    if not tratamento:
        flash('Tratamento não encontrado!', 'error')
        return redirect(url_for('listar_pacientes'))
    if request.method == 'POST':
        try:
            tratamento.data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()
            tratamento.dente = request.form['dente']
            tratamento.procedimento = request.form['procedimento']
            tratamento.descricao = request.form['descricao']
            tratamento.valor = float(request.form['valor'])
            tratamento.valor_pago = float(request.form.get('valor_pago', 0) or 0)
            tratamento.forma_pagamento = request.form.get('forma_pagamento', '')
            tratamento.observacoes = request.form.get('observacoes', '')
            if tratamento.valor_pago >= tratamento.valor:
                tratamento.status_pagamento = 'Pago'
            elif tratamento.valor_pago > 0:
                tratamento.status_pagamento = 'Parcial'
            else:
                tratamento.status_pagamento = 'Pendente'
            db.session.commit()
            flash('Tratamento atualizado!', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {str(e)}', 'error')
        return redirect(url_for('ficha_tratamento', paciente_id=tratamento.paciente_id))
    return render_template('fichas/editar_tratamento.html', tratamento=tratamento)

@app.route('/tratamento/excluir/<int:id>')
@requer_permissao('excluir_tratamentos')
def excluir_tratamento(id):
    tratamento = db.session.get(FichaTratamento, id)
    if tratamento:
        paciente_id = tratamento.paciente_id
        try:
            db.session.delete(tratamento)
            db.session.commit()
            flash('Tratamento excluído!', 'success')
        except:
            db.session.rollback()
            flash('Erro ao excluir.', 'error')
        return redirect(url_for('ficha_tratamento', paciente_id=paciente_id))
    return redirect(url_for('listar_pacientes'))

# ==================== ROTA ODONTOGRAMA E ORÇAMENTO ====================

@app.route('/odontograma/<int:paciente_id>', methods=['GET', 'POST'])
@requer_permissao('odontograma')
def odontograma(paciente_id):
    config = ConfiguracaoClinica.get_configuracao()
    paciente = db.session.get(Paciente, paciente_id)
    if not paciente:
        flash('Paciente não encontrado!', 'error')
        return redirect(url_for('listar_pacientes'))
    odonto = Odontograma.query.filter_by(paciente_id=paciente_id).first()
    if request.method == 'POST':
        if not odonto:
            odonto = Odontograma(paciente_id=paciente_id)
            db.session.add(odonto)
        dentes_status = {}
        for key, value in request.form.items():
            if key.startswith('dente_'):
                dentes_status[key.replace('dente_', '')] = value
        odonto.dentes = json.dumps(dentes_status)
        odonto.observacoes = request.form.get('observacoes', '')
        odonto.data_atualizacao = date.today()
        db.session.commit()
        flash('Odontograma salvo!', 'success')
        return redirect(url_for('visualizar_paciente', id=paciente_id))
    return render_template('odontograma.html', config=config, paciente=paciente, odonto=odonto)

@app.route('/orcamento/<int:paciente_id>')
@requer_permissao('orcamento')
def orcamento(paciente_id):
    config = ConfiguracaoClinica.get_configuracao()
    paciente = db.session.get(Paciente, paciente_id)
    if not paciente:
        flash('Paciente não encontrado!', 'error')
        return redirect(url_for('listar_pacientes'))
    orcamentos = Orcamento.query.filter_by(paciente_id=paciente_id).order_by(Orcamento.data_criacao.desc()).all()
    return render_template('orcamento.html', config=config, paciente=paciente, orcamentos=orcamentos)

@app.route('/orcamento/novo/<int:paciente_id>', methods=['GET', 'POST'])
@login_required
def novo_orcamento(paciente_id):
    config = ConfiguracaoClinica.get_configuracao()
    paciente = db.session.get(Paciente, paciente_id)
    if not paciente:
        flash('Paciente não encontrado!', 'error')
        return redirect(url_for('listar_pacientes'))
    if request.method == 'POST':
        try:
            parcelas = int(request.form.get('parcelas', 1))
            orcamento = Orcamento(paciente_id=paciente_id, parcelas=parcelas, observacoes=request.form.get('observacoes', ''))
            db.session.add(orcamento)
            db.session.flush()
            valor_total = 0
            procedimentos = request.form.getlist('procedimento[]')
            dentes = request.form.getlist('dente[]')
            valores = request.form.getlist('valor[]')
            for i in range(len(procedimentos)):
                if procedimentos[i]:
                    valor = float(valores[i] or 0)
                    item = ItemOrcamento(orcamento_id=orcamento.id, dente=dentes[i] if i < len(dentes) else '', procedimento=procedimentos[i], valor=valor)
                    db.session.add(item)
                    valor_total += valor
            acrescimo_percentual = float(request.form.get('acrescimo_percentual', 0) or 0)
            acrescimo_valor = valor_total * (acrescimo_percentual / 100)
            valor_com_acrescimo = valor_total + acrescimo_valor
            orcamento.valor_total = valor_total
            orcamento.acrescimo_percentual = acrescimo_percentual
            orcamento.acrescimo_valor = acrescimo_valor
            orcamento.valor_total_com_acrescimo = valor_com_acrescimo
            orcamento.valor_parcela = valor_com_acrescimo / parcelas if parcelas > 0 else valor_com_acrescimo
            db.session.commit()
            flash('Orçamento criado!', 'success')
            return redirect(url_for('orcamento', paciente_id=paciente_id))
        except Exception as e:
            db.session.rollback()
            flash(f'Erro: {str(e)}', 'error')
    return render_template('novo_orcamento.html', config=config, paciente=paciente)

@app.route('/orcamento/ver/<int:id>')
@login_required
def ver_orcamento(id):
    config = ConfiguracaoClinica.get_configuracao()
    orcamento = db.session.get(Orcamento, id)
    if not orcamento:
        flash('Orçamento não encontrado!', 'error')
        return redirect(url_for('listar_pacientes'))
    return render_template('ver_orcamento.html', config=config, orcamento=orcamento)

@app.route('/orcamento/status/<int:id>', methods=['POST'])
@login_required
def atualizar_status_orcamento(id):
    orcamento = db.session.get(Orcamento, id)
    if orcamento:
        orcamento.status = request.form['status']
        if request.form['status'] == 'Aprovado':
            orcamento.data_aprovacao = date.today()
        db.session.commit()
        flash('Status atualizado!', 'success')
    return redirect(url_for('orcamento', paciente_id=orcamento.paciente_id))

# ==================== ROTAS DE AGENDA ====================

@app.route('/agenda')
@requer_permissao('agenda')
def agenda():
    config = ConfiguracaoClinica.get_configuracao()
    return render_template('agenda.html', config=config)

@app.route('/api/agendamentos')
@login_required
def api_agendamentos():
    query = Agendamento.query
    
    # Filtros
    if request.args.get('profissional_id'):
        query = query.filter_by(profissional_id=request.args.get('profissional_id'))
    if request.args.get('status'):
        query = query.filter_by(status=request.args.get('status'))
    
    agendamentos = query.all()
    eventos = []
    
    cores = {
        'Consulta': '#4CAF50', 'Limpeza': '#2196F3', 'Restauracao': '#FF9800',
        'Canal': '#9C27B0', 'Extracao': '#F44336', 'Ortodontia': '#00BCD4',
        'Protese': '#795548', 'Clareamento': '#FFD700', 'Emergencia': '#F44336',
        'Bloqueado': '#9E9E9E', 'Outro': '#607D8B'
    }
    
    for agend in agendamentos:
        cor = cores.get(agend.procedimento.replace(' ', ''), '#607D8B')
        if agend.status == 'Bloqueado':
            cor = '#9E9E9E'
        
        eventos.append({
            'id': agend.id,
            'title': agend.procedimento if agend.paciente else '⛔ ' + agend.procedimento,
            'start': agend.data_hora.isoformat(),
            'end': (agend.data_hora + timedelta(minutes=agend.duracao)).isoformat(),
            'backgroundColor': cor,
            'borderColor': cor,
            'textColor': '#fff',
            'paciente': agend.paciente.nome if agend.paciente else 'Bloqueado',
            'status': agend.status,
            'profissional': agend.profissional.nome_completo if agend.profissional else ''
        })
    
    return jsonify(eventos)

# ==================== ROTAS DE CANCELAMENTO AGENDA ====================

@app.route('/agendamento/cancelar/<int:id>', methods=['POST'])
@login_required
def cancelar_agendamento(id):
    agendamento = db.session.get(Agendamento, id)
    if agendamento:
        agendamento.status = 'Cancelado'
        db.session.commit()
        return jsonify({'success': True})
    return jsonify({'success': False})

@app.route('/agendamento/novo', methods=['POST'])
@login_required
def novo_agendamento():
    data = request.json
    try:
        paciente_id = data.get('paciente_id')
        paciente = db.session.get(Paciente, paciente_id) if paciente_id else None
        
        agendamento = Agendamento(
            paciente_id=paciente_id,
            profissional_id=data.get('profissional_id'),
            data_hora=datetime.fromisoformat(data['data_hora']),
            duracao=data.get('duracao', 60),
            procedimento=data['procedimento'],
            status=data.get('status', 'Agendado'),
            observacoes=data.get('observacoes', '')
        )
        db.session.add(agendamento)
        db.session.commit()
        
        whatsapp_link = ''
        paciente_nome = ''
        
        if paciente:
            data_formatada = agendamento.data_hora.strftime('%d/%m/%Y às %H:%M')
            mensagem = f"Olá {paciente.nome}! Sua consulta foi agendada para {data_formatada}. Procedimento: {agendamento.procedimento}. Aguardamos você!".replace(' ', '%20')
            celular_limpo = paciente.celular.replace('(', '').replace(')', '').replace(' ', '').replace('-', '') if paciente.celular else ''
            whatsapp_link = f"https://wa.me/55{celular_limpo}?text={mensagem}" if celular_limpo else ''
            paciente_nome = paciente.nome
        
        return jsonify({
            'success': True, 
            'id': agendamento.id, 
            'whatsapp_link': whatsapp_link, 
            'paciente_nome': paciente_nome
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# ==================== ROTAS DE ATESTADOS ====================

@app.route('/atestados')
@requer_permissao('atestados')
def atestados():
    config = ConfiguracaoClinica.get_configuracao()
    pacientes = Paciente.query.filter_by(ativo=True).all()
    return render_template('atestados.html', config=config, pacientes=pacientes)

@app.route('/gerar-atestado', methods=['POST'])
@login_required
def gerar_atestado():
    config = ConfiguracaoClinica.get_configuracao()
    paciente = db.session.get(Paciente, request.form['paciente_id'])
    dados_atestado = {
        'clinica': config.nome_clinica, 'doutor': config.nome_doutor, 'cro': config.cro,
        'endereco': config.endereco, 'paciente': paciente.nome, 'cpf': paciente.cpf,
        'data': datetime.now().strftime('%d/%m/%Y'), 'tipo': request.form['tipo'],
        'conteudo': request.form['conteudo'], 'dias_afastamento': request.form.get('dias_afastamento', ''),
        'cidade': config.cidade, 'estado': config.estado
    }
    return render_template('atestado_gerado.html', dados=dados_atestado)

# ==================== ROTAS DE HISTÓRICO ====================

@app.route('/historico/<int:paciente_id>')
@requer_permissao('historico')
def historico_paciente(paciente_id):
    config = ConfiguracaoClinica.get_configuracao()
    paciente = db.session.get(Paciente, paciente_id)
    if not paciente:
        flash('Paciente não encontrado!', 'error')
        return redirect(url_for('listar_pacientes'))
    historicos = HistoricoPaciente.query.filter_by(paciente_id=paciente_id).order_by(HistoricoPaciente.data.desc()).all()
    return render_template('historico.html', config=config, paciente=paciente, historicos=historicos)

# ==================== ROTAS DE ANIVERSARIANTES ====================

@app.route('/aniversariantes')
@requer_permissao('aniversariantes')
def aniversariantes():
    config = ConfiguracaoClinica.get_configuracao()
    hoje = date.today()
    aniversariantes_mes = Paciente.query.filter(
        db.extract('month', Paciente.data_nascimento) == hoje.month,
        Paciente.ativo == True
    ).all()
    return render_template('aniversariantes.html', config=config, aniversariantes=aniversariantes_mes, mes_atual=hoje.month)

# ==================== ROTAS FINANCEIRAS ====================

@app.route('/financeiro')
@requer_permissao('ver_financeiro')
def financeiro():
    config = ConfiguracaoClinica.get_configuracao()
    total_faturado = db.session.query(db.func.sum(FichaTratamento.valor)).scalar() or 0
    total_recebido = db.session.query(db.func.sum(FichaTratamento.valor_pago)).scalar() or 0
    total_pendente = total_faturado - total_recebido
    ultimos_tratamentos = FichaTratamento.query.order_by(FichaTratamento.data.desc()).limit(20).all()
    hoje = date.today()
    meses_labels, meses_faturado, meses_recebido = [], [], []
    for i in range(5, -1, -1):
        mes_date = hoje - relativedelta(months=i)
        mes_inicio = mes_date.replace(day=1)
        mes_fim = hoje if i == 0 else (mes_date.replace(month=mes_date.month+1, day=1) - timedelta(days=1) if mes_date.month < 12 else mes_date.replace(year=mes_date.year, month=12, day=31))
        meses_labels.append(['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][mes_date.month-1])
        faturado = db.session.query(db.func.sum(FichaTratamento.valor)).filter(FichaTratamento.data >= mes_inicio, FichaTratamento.data <= mes_fim).scalar() or 0
        recebido = db.session.query(db.func.sum(FichaTratamento.valor_pago)).filter(FichaTratamento.data >= mes_inicio, FichaTratamento.data <= mes_fim).scalar() or 0
        meses_faturado.append(float(faturado))
        meses_recebido.append(float(recebido))
    procedimentos = db.session.query(FichaTratamento.procedimento, db.func.count(FichaTratamento.id).label('total')).group_by(FichaTratamento.procedimento).order_by(db.desc('total')).limit(5).all()
    return render_template('financeiro/geral.html', config=config, total_faturado=total_faturado, total_recebido=total_recebido, total_pendente=total_pendente, ultimos_tratamentos=ultimos_tratamentos, meses_labels=meses_labels, meses_faturado=meses_faturado, meses_recebido=meses_recebido, proc_labels=[p[0] for p in procedimentos], proc_valores=[p[1] for p in procedimentos])

@app.route('/financeiro/filtros', methods=['GET', 'POST'])
@requer_permissao('ver_financeiro')
def financeiro_filtros():
    config = ConfiguracaoClinica.get_configuracao()
    resultados, filtro_aplicado = [], False
    pacientes = Paciente.query.filter_by(ativo=True).all()
    if request.method == 'POST':
        filtro_aplicado = True
        query = FichaTratamento.query
        if request.form.get('paciente_id'): query = query.filter_by(paciente_id=request.form['paciente_id'])
        if request.form.get('data_inicio'): query = query.filter(FichaTratamento.data >= datetime.strptime(request.form['data_inicio'], '%Y-%m-%d').date())
        if request.form.get('data_fim'): query = query.filter(FichaTratamento.data <= datetime.strptime(request.form['data_fim'], '%Y-%m-%d').date())
        if request.form.get('mes'):
            mes_num, ano = request.form['mes'].split('-')
            query = query.filter(db.extract('month', FichaTratamento.data) == int(mes_num), db.extract('year', FichaTratamento.data) == int(ano))
        if request.form.get('status'): query = query.filter_by(status_pagamento=request.form['status'])
        resultados = query.order_by(FichaTratamento.data.desc()).all()
        total_filtrado = sum(r.valor for r in resultados)
        recebido_filtrado = sum(r.valor_pago for r in resultados)
        return render_template('financeiro/filtros.html', config=config, resultados=resultados, filtro_aplicado=filtro_aplicado, total_filtrado=total_filtrado, recebido_filtrado=recebido_filtrado, pendente_filtrado=total_filtrado-recebido_filtrado, pacientes=pacientes)
    return render_template('financeiro/filtros.html', config=config, resultados=resultados, filtro_aplicado=filtro_aplicado, pacientes=pacientes)

# ==================== ROTAS DE FUNCIONÁRIOS ====================

@app.route('/funcionarios')
@requer_permissao('funcionarios')
def listar_funcionarios():
    config = ConfiguracaoClinica.get_configuracao()
    funcionarios = Usuario.query.filter_by(ativo=True).all()
    return render_template('funcionarios/listar.html', config=config, funcionarios=funcionarios)

@app.route('/funcionarios/cadastrar', methods=['GET', 'POST'])
@requer_permissao('funcionarios')
def cadastrar_funcionario():
    config = ConfiguracaoClinica.get_configuracao()
    if request.method == 'POST':
        username = request.form['username']
        if Usuario.query.filter_by(username=username).first():
            flash('Usuário já existe!', 'error')
            return redirect(url_for('cadastrar_funcionario'))
        funcionario = Usuario(
            username=username, nome_completo=request.form['nome_completo'],
            email=request.form.get('email', ''), cargo=request.form.get('cargo', 'Dentista'),
            cro=request.form.get('cro', ''), especialidade=request.form.get('especialidade', ''),
            comissao_percentual=float(request.form.get('comissao_percentual', 0) or 0)
        )
        funcionario.set_password(request.form['password'])
        db.session.add(funcionario)
        db.session.commit()
        flash('Funcionário cadastrado!', 'success')
        return redirect(url_for('listar_funcionarios'))
    return render_template('funcionarios/cadastrar.html', config=config)

@app.route('/funcionarios/editar/<int:id>', methods=['GET', 'POST'])
@requer_permissao('funcionarios')
def editar_funcionario(id):
    config = ConfiguracaoClinica.get_configuracao()
    funcionario = db.session.get(Usuario, id)
    if not funcionario:
        flash('Funcionário não encontrado!', 'error')
        return redirect(url_for('listar_funcionarios'))
    if request.method == 'POST':
        funcionario.nome_completo = request.form['nome_completo']
        funcionario.email = request.form.get('email', '')
        funcionario.cargo = request.form.get('cargo', 'Dentista')
        funcionario.cro = request.form.get('cro', '')
        funcionario.especialidade = request.form.get('especialidade', '')
        funcionario.comissao_percentual = float(request.form.get('comissao_percentual', 0) or 0)
        if request.form.get('password'):
            funcionario.set_password(request.form['password'])
        db.session.commit()
        flash('Funcionário atualizado!', 'success')
        return redirect(url_for('listar_funcionarios'))
    return render_template('funcionarios/editar.html', config=config, funcionario=funcionario)

@app.route('/funcionarios/deletar/<int:id>')
@requer_permissao('funcionarios')
def deletar_funcionario(id):
    funcionario = db.session.get(Usuario, id)
    if funcionario and funcionario.username != 'admin':
        funcionario.ativo = False
        db.session.commit()
        flash('Funcionário removido!', 'success')
    return redirect(url_for('listar_funcionarios'))

@app.route('/relatorio/comissoes')
@requer_permissao('comissoes')
def relatorio_comissoes():
    config = ConfiguracaoClinica.get_configuracao()
    profissionais = Usuario.query.filter_by(ativo=True).all()
    dados = []
    for prof in profissionais:
        tratamentos = FichaTratamento.query.filter_by(profissional_id=prof.id).all()
        total_produzido = sum(t.valor for t in tratamentos)
        total_recebido = sum(t.valor_pago for t in tratamentos)
        comissao = total_recebido * (prof.comissao_percentual / 100) if prof.comissao_percentual > 0 else 0
        dados.append({
            'nome': prof.nome_completo, 'cargo': prof.cargo,
            'total_produzido': total_produzido, 'total_recebido': total_recebido,
            'comissao_percentual': prof.comissao_percentual, 'comissao_valor': comissao,
            'total_tratamentos': len(tratamentos)
        })
    return render_template('funcionarios/comissoes.html', config=config, dados=dados)

# ==================== ROTAS DE ARQUIVOS ====================

@app.route('/arquivos/<int:paciente_id>')
@requer_permissao('arquivos')
def arquivos_paciente(paciente_id):
    config = ConfiguracaoClinica.get_configuracao()
    paciente = db.session.get(Paciente, paciente_id)
    if not paciente:
        flash('Paciente não encontrado!', 'error')
        return redirect(url_for('listar_pacientes'))
    arquivos = ArquivoPaciente.query.filter_by(paciente_id=paciente_id).order_by(ArquivoPaciente.data_upload.desc()).all()
    return render_template('arquivos.html', config=config, paciente=paciente, arquivos=arquivos)

@app.route('/arquivos/upload/<int:paciente_id>', methods=['POST'])
@login_required
def upload_arquivo(paciente_id):
    paciente = db.session.get(Paciente, paciente_id)
    if not paciente:
        return redirect(url_for('listar_pacientes'))
    if 'arquivo' not in request.files:
        flash('Nenhum arquivo!', 'error')
        return redirect(url_for('arquivos_paciente', paciente_id=paciente_id))
    arquivo = request.files['arquivo']
    if arquivo.filename == '':
        return redirect(url_for('arquivos_paciente', paciente_id=paciente_id))
    if arquivo and allowed_file(arquivo.filename):
        filename = secure_filename(arquivo.filename)
        nome_unico = f"{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
        paciente_folder = os.path.join(app.config['UPLOAD_FOLDER'], str(paciente_id))
        if not os.path.exists(paciente_folder):
            os.makedirs(paciente_folder)
        arquivo.save(os.path.join(paciente_folder, nome_unico))
        novo_arquivo = ArquivoPaciente(
            paciente_id=paciente_id, nome_original=filename, nome_arquivo=nome_unico,
            tipo=request.form.get('tipo', 'imagem'), categoria=request.form.get('categoria', ''),
            descricao=request.form.get('descricao', '')
        )
        db.session.add(novo_arquivo)
        db.session.commit()
        flash('Arquivo enviado!', 'success')
    else:
        flash('Tipo não permitido!', 'error')
    return redirect(url_for('arquivos_paciente', paciente_id=paciente_id))

@app.route('/arquivos/deletar/<int:id>')
@login_required
def deletar_arquivo(id):
    arquivo = db.session.get(ArquivoPaciente, id)
    if arquivo:
        paciente_id = arquivo.paciente_id
        caminho = os.path.join(app.config['UPLOAD_FOLDER'], str(paciente_id), arquivo.nome_arquivo)
        if os.path.exists(caminho):
            os.remove(caminho)
        db.session.delete(arquivo)
        db.session.commit()
        flash('Arquivo removido!', 'success')
        return redirect(url_for('arquivos_paciente', paciente_id=paciente_id))
    return redirect(url_for('listar_pacientes'))

# ==================== ROTAS DE RELATÓRIOS ====================

@app.route('/relatorios')
@requer_permissao('ver_financeiro')
def relatorios():
    config = ConfiguracaoClinica.get_configuracao()
    return render_template('relatorios/index.html', config=config)

@app.route('/api/relatorio/financeiro')
@requer_permissao('ver_financeiro')
def api_relatorio_financeiro():
    periodo = request.args.get('periodo', 'mes')
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    hoje = date.today()
    
    if data_inicio and data_fim:
        inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    elif periodo == 'hoje':
        inicio = hoje
        fim = hoje
    elif periodo == 'semana':
        inicio = hoje - timedelta(days=7)
        fim = hoje
    elif periodo == 'mes':
        inicio = hoje.replace(day=1)
        fim = hoje
    elif periodo == 'ano':
        inicio = hoje.replace(month=1, day=1)
        fim = hoje
    else:
        inicio = hoje.replace(day=1)
        fim = hoje
    
    # Dados gerais
    total_faturado = db.session.query(db.func.sum(FichaTratamento.valor)).filter(
        FichaTratamento.data >= inicio, FichaTratamento.data <= fim
    ).scalar() or 0
    
    total_recebido = db.session.query(db.func.sum(FichaTratamento.valor_pago)).filter(
        FichaTratamento.data >= inicio, FichaTratamento.data <= fim
    ).scalar() or 0
    
    total_pendente = total_faturado - total_recebido
    total_tratamentos = FichaTratamento.query.filter(
        FichaTratamento.data >= inicio, FichaTratamento.data <= fim
    ).count()
    
    total_pacientes_atendidos = db.session.query(FichaTratamento.paciente_id).filter(
        FichaTratamento.data >= inicio, FichaTratamento.data <= fim
    ).distinct().count()
    
    ticket_medio = total_faturado / total_pacientes_atendidos if total_pacientes_atendidos > 0 else 0
    
    # Dados por mês para gráfico
    meses_labels = []
    meses_faturado = []
    meses_recebido = []
    meses_pendente = []
    
    for i in range(5, -1, -1):
        mes_date = hoje - relativedelta(months=i)
        mes_inicio = mes_date.replace(day=1)
        if mes_date.month == 12:
            mes_fim = mes_date.replace(day=31)
        else:
            mes_fim = mes_date.replace(month=mes_date.month+1, day=1) - timedelta(days=1)
        
        meses_labels.append(['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][mes_date.month-1])
        
        fat = db.session.query(db.func.sum(FichaTratamento.valor)).filter(
            FichaTratamento.data >= mes_inicio, FichaTratamento.data <= mes_fim
        ).scalar() or 0
        rec = db.session.query(db.func.sum(FichaTratamento.valor_pago)).filter(
            FichaTratamento.data >= mes_inicio, FichaTratamento.data <= mes_fim
        ).scalar() or 0
        
        meses_faturado.append(float(fat))
        meses_recebido.append(float(rec))
        meses_pendente.append(float(fat - rec))
    
    # Procedimentos mais realizados
    procs = db.session.query(
        FichaTratamento.procedimento,
        db.func.count(FichaTratamento.id).label('qtd'),
        db.func.sum(FichaTratamento.valor).label('total')
    ).filter(
        FichaTratamento.data >= inicio, FichaTratamento.data <= fim
    ).group_by(FichaTratamento.procedimento).order_by(db.desc('qtd')).limit(8).all()
    
    # Profissionais
    profs = db.session.query(
        Usuario.nome_completo,
        db.func.count(FichaTratamento.id).label('qtd'),
        db.func.sum(FichaTratamento.valor).label('total'),
        db.func.sum(FichaTratamento.valor_pago).label('recebido')
    ).join(FichaTratamento, FichaTratamento.profissional_id == Usuario.id).filter(
        FichaTratamento.data >= inicio, FichaTratamento.data <= fim
    ).group_by(Usuario.nome_completo).all()
    
    return jsonify({
        'periodo': {'inicio': inicio.strftime('%d/%m/%Y'), 'fim': fim.strftime('%d/%m/%Y')},
        'total_faturado': total_faturado,
        'total_recebido': total_recebido,
        'total_pendente': total_pendente,
        'total_tratamentos': total_tratamentos,
        'total_pacientes_atendidos': total_pacientes_atendidos,
        'ticket_medio': ticket_medio,
        'taxa_inadimplencia': (total_pendente / total_faturado * 100) if total_faturado > 0 else 0,
        'grafico_meses': {
            'labels': meses_labels,
            'faturado': meses_faturado,
            'recebido': meses_recebido,
            'pendente': meses_pendente
        },
        'procedimentos': [{'nome': p[0], 'qtd': p[1], 'total': float(p[2] or 0)} for p in procs],
        'profissionais': [{'nome': p[0], 'qtd': p[1], 'total': float(p[2] or 0), 'recebido': float(p[3] or 0)} for p in profs]
    })

@app.route('/api/relatorio/pacientes')
@requer_permissao('pacientes')
def api_relatorio_pacientes():
    total_ativos = Paciente.query.filter_by(ativo=True).count()
    total_inativos = Paciente.query.filter_by(ativo=False).count()
    total_geral = total_ativos + total_inativos
    
    # Por faixa etária
    hoje = date.today()
    faixas = {'0-12': 0, '13-18': 0, '19-30': 0, '31-45': 0, '46-60': 0, '60+': 0}
    for p in Paciente.query.filter_by(ativo=True).all():
        idade = p.calcular_idade()
        if idade <= 12: faixas['0-12'] += 1
        elif idade <= 18: faixas['13-18'] += 1
        elif idade <= 30: faixas['19-30'] += 1
        elif idade <= 45: faixas['31-45'] += 1
        elif idade <= 60: faixas['46-60'] += 1
        else: faixas['60+'] += 1
    
    # Por mês de cadastro
    cadastros_mes = []
    for i in range(5, -1, -1):
        mes_date = hoje - relativedelta(months=i)
        mes_inicio = mes_date.replace(day=1)
        if mes_date.month == 12:
            mes_fim = mes_date.replace(day=31)
        else:
            mes_fim = mes_date.replace(month=mes_date.month+1, day=1) - timedelta(days=1)
        
        count = Paciente.query.filter(
            Paciente.data_cadastro >= mes_inicio,
            Paciente.data_cadastro <= mes_fim
        ).count()
        cadastros_mes.append(count)
    
    meses_labels = ['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez']
    labels = [meses_labels[(hoje - relativedelta(months=i)).month - 1] for i in range(5, -1, -1)]
    
    return jsonify({
        'total_ativos': total_ativos,
        'total_inativos': total_inativos,
        'total_geral': total_geral,
        'faixas_etarias': faixas,
        'cadastros': {'labels': labels, 'valores': cadastros_mes}
    })

@app.route('/api/relatorio/exportar')
@requer_permissao('ver_financeiro')
def exportar_relatorio():
    import csv
    from io import StringIO
    
    tipo = request.args.get('tipo', 'financeiro')
    data_inicio = request.args.get('data_inicio', (date.today().replace(day=1)).strftime('%Y-%m-%d'))
    data_fim = request.args.get('data_fim', date.today().strftime('%Y-%m-%d'))
    
    inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
    fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    
    si = StringIO()
    writer = csv.writer(si)
    
    if tipo == 'financeiro':
        writer.writerow(['Data', 'Paciente', 'Procedimento', 'Dente', 'Valor', 'Pago', 'Saldo', 'Status', 'Profissional'])
        tratamentos = FichaTratamento.query.filter(
            FichaTratamento.data >= inicio, FichaTratamento.data <= fim
        ).order_by(FichaTratamento.data.desc()).all()
        
        for t in tratamentos:
            writer.writerow([
                t.data.strftime('%d/%m/%Y'),
                t.paciente.nome,
                t.procedimento,
                t.dente or '',
                f'R$ {t.valor:.2f}',
                f'R$ {t.valor_pago:.2f}',
                f'R$ {t.saldo_restante:.2f}',
                t.status_pagamento,
                t.profissional.nome_completo if t.profissional else ''
            ])
    
    output = si.getvalue()
    return Response(
        output,
        mimetype='text/csv',
        headers={'Content-Disposition': f'attachment;filename=relatorio_{tipo}_{data_inicio}_{data_fim}.csv'}
    )

# ==================== ROTAS DE RELATÓRIOS POR DENTISTA ====================

@app.route('/api/relatorio/dentista/<int:profissional_id>')
@requer_permissao('comissoes')
def api_relatorio_dentista(profissional_id):
    data_inicio = request.args.get('data_inicio')
    data_fim = request.args.get('data_fim')
    
    hoje = date.today()
    
    if data_inicio and data_fim:
        inicio = datetime.strptime(data_inicio, '%Y-%m-%d').date()
        fim = datetime.strptime(data_fim, '%Y-%m-%d').date()
    else:
        inicio = hoje.replace(day=1)
        fim = hoje
    
    profissional = db.session.get(Usuario, profissional_id)
    
    if not profissional:
        return jsonify({'error': 'Profissional não encontrado'})
    
    # Tratamentos do dentista no período
    tratamentos = FichaTratamento.query.filter(
        FichaTratamento.profissional_id == profissional_id,
        FichaTratamento.data >= inicio,
        FichaTratamento.data <= fim
    ).order_by(FichaTratamento.data.desc()).all()
    
    total_produzido = sum(t.valor for t in tratamentos)
    total_recebido = sum(t.valor_pago for t in tratamentos)
    total_pendente = total_produzido - total_recebido
    
    # Comissão sobre o recebido
    comissao_valor = total_recebido * (profissional.comissao_percentual / 100)
    
    # Detalhamento por procedimento
    procedimentos = {}
    for t in tratamentos:
        proc = t.procedimento
        if proc not in procedimentos:
            procedimentos[proc] = {'qtd': 0, 'total': 0, 'recebido': 0}
        procedimentos[proc]['qtd'] += 1
        procedimentos[proc]['total'] += t.valor
        procedimentos[proc]['recebido'] += t.valor_pago
    
    # Por dia
    dias = {}
    for t in tratamentos:
        dia = t.data.strftime('%d/%m/%Y')
        if dia not in dias:
            dias[dia] = {'qtd': 0, 'total': 0}
        dias[dia]['qtd'] += 1
        dias[dia]['total'] += t.valor
    
    return jsonify({
        'profissional': {
            'nome': profissional.nome_completo,
            'cargo': profissional.cargo,
            'comissao_percentual': profissional.comissao_percentual
        },
        'periodo': {'inicio': inicio.strftime('%d/%m/%Y'), 'fim': fim.strftime('%d/%m/%Y')},
        'total_produzido': total_produzido,
        'total_recebido': total_recebido,
        'total_pendente': total_pendente,
        'comissao_valor': comissao_valor,
        'total_tratamentos': len(tratamentos),
        'tratamentos': [{
            'data': t.data.strftime('%d/%m/%Y'),
            'paciente': t.paciente.nome,
            'procedimento': t.procedimento,
            'dente': t.dente or '',
            'valor': t.valor,
            'valor_pago': t.valor_pago,
            'status': t.status_pagamento
        } for t in tratamentos],
        'procedimentos': [{'nome': k, **v} for k, v in procedimentos.items()],
        'dias': [{'data': k, **v} for k, v in sorted(dias.items())]
    })

# ==================== ROTAS DE DESPESAS ====================

@app.route('/despesas')
@requer_permissao('ver_financeiro')
def despesas():
    config = ConfiguracaoClinica.get_configuracao()
    categorias = CategoriaDespesa.query.all()
    return render_template('despesas/index.html', config=config, categorias=categorias)

@app.route('/api/despesas')
@requer_permissao('ver_financeiro')
def api_despesas():
    mes = request.args.get('mes')
    categoria_id = request.args.get('categoria_id')
    
    query = Despesa.query
    
    if mes:
        ano, mes_num = mes.split('-')
        query = query.filter(
            db.extract('month', Despesa.data) == int(mes_num),
            db.extract('year', Despesa.data) == int(ano)
        )
    else:
        hoje = date.today()
        query = query.filter(
            db.extract('month', Despesa.data) == hoje.month,
            db.extract('year', Despesa.data) == hoje.year
        )
    
    if categoria_id:
        query = query.filter_by(categoria_id=categoria_id)
    
    despesas = query.order_by(Despesa.data.desc()).all()
    
    return jsonify([{
        'id': d.id,
        'data': d.data.strftime('%d/%m/%Y'),
        'descricao': d.descricao,
        'valor': d.valor,
        'categoria': d.categoria.nome if d.categoria else 'Sem categoria',
        'categoria_cor': d.categoria.cor if d.categoria else '#607D8B',
        'pago': d.pago,
        'recorrente': d.recorrente,
        'observacoes': d.observacoes or ''
    } for d in despesas])

@app.route('/api/despesas/resumo')
@requer_permissao('ver_financeiro')
def api_despesas_resumo():
    hoje = date.today()
    mes_inicio = hoje.replace(day=1)
    
    # Total de despesas do mês
    total_despesas = db.session.query(db.func.sum(Despesa.valor)).filter(
        Despesa.data >= mes_inicio, Despesa.data <= hoje
    ).scalar() or 0
    
    # Total de entradas do mês (recebido)
    total_entradas = db.session.query(db.func.sum(FichaTratamento.valor_pago)).filter(
        FichaTratamento.data >= mes_inicio, FichaTratamento.data <= hoje
    ).scalar() or 0
    
    lucro = total_entradas - total_despesas
    
    # Despesas por categoria
    despesas_categoria = db.session.query(
        CategoriaDespesa.nome, CategoriaDespesa.cor,
        db.func.sum(Despesa.valor).label('total')
    ).join(Despesa, Despesa.categoria_id == CategoriaDespesa.id).filter(
        Despesa.data >= mes_inicio, Despesa.data <= hoje
    ).group_by(CategoriaDespesa.nome, CategoriaDespesa.cor).all()
    
    # Últimos 6 meses (entradas vs saídas)
    meses_labels = []
    entradas_mes = []
    saidas_mes = []
    
    for i in range(5, -1, -1):
        mes_date = hoje - relativedelta(months=i)
        m_inicio = mes_date.replace(day=1)
        if mes_date.month == 12:
            m_fim = mes_date.replace(day=31)
        else:
            m_fim = mes_date.replace(month=mes_date.month+1, day=1) - timedelta(days=1)
        
        meses_labels.append(['Jan','Fev','Mar','Abr','Mai','Jun','Jul','Ago','Set','Out','Nov','Dez'][mes_date.month-1])
        
        ent = db.session.query(db.func.sum(FichaTratamento.valor_pago)).filter(
            FichaTratamento.data >= m_inicio, FichaTratamento.data <= m_fim
        ).scalar() or 0
        
        saida = db.session.query(db.func.sum(Despesa.valor)).filter(
            Despesa.data >= m_inicio, Despesa.data <= m_fim
        ).scalar() or 0
        
        entradas_mes.append(float(ent))
        saidas_mes.append(float(saida))
    
    return jsonify({
        'total_despesas': total_despesas,
        'total_entradas': total_entradas,
        'lucro': lucro,
        'despesas_categoria': [{'nome': d[0], 'cor': d[1], 'total': float(d[2] or 0)} for d in despesas_categoria],
        'grafico_meses': {
            'labels': meses_labels,
            'entradas': entradas_mes,
            'saidas': saidas_mes
        }
    })

@app.route('/despesas/editar/<int:id>', methods=['POST'])
@requer_permissao('ver_financeiro')
def editar_despesa(id):
    despesa = db.session.get(Despesa, id)
    
    if not despesa:
        flash('Despesa não encontrada!', 'error')
        return redirect(url_for('despesas'))
    
    try:
        despesa.categoria_id = request.form.get('categoria_id') or None
        despesa.data = datetime.strptime(request.form['data'], '%Y-%m-%d').date()
        despesa.descricao = request.form['descricao']
        despesa.valor = float(request.form['valor'])
        despesa.recorrente = 'recorrente' in request.form
        despesa.pago = 'pago' in request.form
        despesa.observacoes = request.form.get('observacoes', '')
        
        # Upload de novo comprovante
        if 'comprovante' in request.files:
            arquivo = request.files['comprovante']
            if arquivo.filename and allowed_file(arquivo.filename):
                # Excluir comprovante antigo
                if despesa.comprovante:
                    caminho_antigo = os.path.join(app.config['UPLOAD_FOLDER'], 'despesas', despesa.comprovante)
                    if os.path.exists(caminho_antigo):
                        os.remove(caminho_antigo)
                
                filename = secure_filename(arquivo.filename)
                nome_unico = f"despesa_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                despesas_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'despesas')
                if not os.path.exists(despesas_folder):
                    os.makedirs(despesas_folder)
                arquivo.save(os.path.join(despesas_folder, nome_unico))
                despesa.comprovante = nome_unico
        
        db.session.commit()
        flash('Despesa atualizada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao atualizar despesa: {str(e)}', 'error')
    
    return redirect(url_for('despesas'))

@app.route('/despesas/nova', methods=['POST'])
@requer_permissao('ver_financeiro')
def nova_despesa():
    try:
        despesa = Despesa(
            categoria_id=request.form.get('categoria_id') or None,
            data=datetime.strptime(request.form['data'], '%Y-%m-%d').date(),
            descricao=request.form['descricao'],
            valor=float(request.form['valor']),
            recorrente='recorrente' in request.form,
            pago='pago' in request.form,
            observacoes=request.form.get('observacoes', '')
        )
        
        # Upload do comprovante
        if 'comprovante' in request.files:
            arquivo = request.files['comprovante']
            if arquivo.filename and allowed_file(arquivo.filename):
                filename = secure_filename(arquivo.filename)
                nome_unico = f"despesa_{datetime.now().strftime('%Y%m%d%H%M%S')}_{filename}"
                despesas_folder = os.path.join(app.config['UPLOAD_FOLDER'], 'despesas')
                if not os.path.exists(despesas_folder):
                    os.makedirs(despesas_folder)
                arquivo.save(os.path.join(despesas_folder, nome_unico))
                despesa.comprovante = nome_unico
        
        db.session.add(despesa)
        db.session.commit()
        flash('Despesa registrada com sucesso!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Erro ao registrar despesa: {str(e)}', 'error')
    
    return redirect(url_for('despesas'))

@app.route('/despesas/excluir/<int:id>')
@requer_permissao('ver_financeiro')
def excluir_despesa(id):
    despesa = db.session.get(Despesa, id)
    if despesa:
        # Excluir comprovante se existir
        if despesa.comprovante:
            caminho = os.path.join(app.config['UPLOAD_FOLDER'], 'despesas', despesa.comprovante)
            if os.path.exists(caminho):
                os.remove(caminho)
        db.session.delete(despesa)
        db.session.commit()
        flash('Despesa excluída!', 'success')
    return redirect(url_for('despesas'))

@app.route('/api/despesas/gerar_recorrentes')
@requer_permissao('ver_financeiro')
def gerar_despesas_recorrentes():
    """Gera despesas recorrentes para o mês atual se ainda não existirem"""
    hoje = date.today()
    mes_inicio = hoje.replace(day=1)
    
    despesas_fixas = Despesa.query.filter_by(recorrente=True).all()
    geradas = 0
    
    for despesa in despesas_fixas:
        # Verificar se já existe neste mês
        existente = Despesa.query.filter(
            Despesa.descricao == despesa.descricao,
            Despesa.data >= mes_inicio,
            Despesa.data <= hoje
        ).first()
        
        if not existente:
            nova = Despesa(
                categoria_id=despesa.categoria_id,
                data=mes_inicio,
                descricao=despesa.descricao,
                valor=despesa.valor,
                recorrente=True,
                pago=False,
                observacoes='Gerado automaticamente'
            )
            db.session.add(nova)
            geradas += 1
    
    if geradas > 0:
        db.session.commit()
    
    return jsonify({'geradas': geradas, 'mensagem': f'{geradas} despesas recorrentes geradas'})

# ==================== INICIALIZAÇÃO ====================

def inicializar_banco():
    # Criar usuário admin
    if not Usuario.query.filter_by(username='admin').first():
        admin = Usuario(username='admin', nome_completo='Administrador', cargo='Admin')
        admin.set_password('admin123')
        db.session.add(admin)
        print("✓ Usuário admin criado!")
        
        config = ConfiguracaoClinica(
            nome_clinica='Clínica Odontológica Exemplo', endereco='Rua Exemplo, 123',
            cidade='São Paulo', estado='SP', cep='00000-000',
            email='clinica@exemplo.com', telefone='(11) 9999-9999',
            nome_doutor='Dr. João Silva', cro='CRO-SP 12345'
        )
        db.session.add(config)
        print("✓ Configuração inicial criada!")
    
    # Criar categorias de despesas padrão
    if not CategoriaDespesa.query.first():
        categorias_padrao = [
            ('Aluguel', 'bi bi-building', '#E91E63', True),
            ('Condomínio', 'bi bi-building', '#9C27B0', True),
            ('IPTU', 'bi bi-receipt', '#673AB7', True),
            ('Água', 'bi bi-droplet', '#2196F3', True),
            ('Luz', 'bi bi-lightning', '#FF9800', True),
            ('Internet/Telefone', 'bi bi-wifi', '#00BCD4', True),
            ('Salários', 'bi bi-people', '#F44336', True),
            ('Comissões', 'bi bi-calculator', '#FF5722', False),
            ('Encargos', 'bi bi-file-text', '#795548', True),
            ('Materiais Odontológicos', 'bi bi-box-seam', '#4CAF50', False),
            ('Manutenção', 'bi bi-tools', '#607D8B', False),
            ('Limpeza', 'bi bi-droplet', '#8BC34A', False),
            ('Contador', 'bi bi-calculator', '#009688', True),
            ('Software/Sistema', 'bi bi-laptop', '#3F51B5', True),
            ('Marketing', 'bi bi-megaphone', '#FF4081', False),
            ('Transporte', 'bi bi-car-front', '#795548', False),
            ('Impostos/Taxas', 'bi bi-receipt', '#F44336', False),
            ('Seguros', 'bi bi-shield', '#2196F3', True),
            ('Outros', 'bi bi-three-dots', '#9E9E9E', False),
        ]
        for nome, icone, cor, fixa in categorias_padrao:
            db.session.add(CategoriaDespesa(nome=nome, icone=icone, cor=cor, fixa=fixa))
        print("✓ Categorias de despesas criadas!")
    
    db.session.commit()

# Criar tabelas e inicializar (funciona local e no Render)
with app.app_context():
    db.create_all()
    inicializar_banco()
    print("✓ Banco de dados pronto!")

if __name__ == '__main__':
    print("\n" + "="*60)
    print("🏥 SISTEMA DE GESTÃO ODONTOLÓGICA")
    print("="*60)
    print("   • URL: http://localhost:5000")
    print("   • Admin: admin / admin123")
    print("="*60 + "\n")
    app.run(debug=True, port=5000, host='0.0.0.0')