from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

class Farmacia(db.Model):
    __tablename__ = 'farmacias'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    endereco = db.Column(db.String(300))
    telefone = db.Column(db.String(50))
    horario = db.Column(db.String(100))
    plantao = db.Column(db.Boolean, default=False)
    senha_hash = db.Column(db.String(200), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    produtos = db.relationship('Produto', backref='farmacia', lazy=True, cascade='all, delete-orphan')
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'endereco': self.endereco,
            'telefone': self.telefone,
            'horario': self.horario,
            'plantao': self.plantao,
            'latitude': self.latitude,
            'longitude': self.longitude,
            'senha_hash': self.senha_hash is not None,
            'medicamentos': [p.nome + ' - ' + str(p.preco) + ' MZN' for p in self.produtos[:5]]
        }
    
    def set_senha(self, senha):
        self.senha_hash = bcrypt.generate_password_hash(senha).decode('utf-8')
    
    def check_senha(self, senha):
        return bcrypt.check_password_hash(self.senha_hash, senha)

class Produto(db.Model):
    __tablename__ = 'produtos'
    
    id = db.Column(db.Integer, primary_key=True)
    farmacia_id = db.Column(db.Integer, db.ForeignKey('farmacias.id'), nullable=False)
    nome = db.Column(db.String(200), nullable=False)
    categoria = db.Column(db.String(50), default='Medicamento')
    preco = db.Column(db.Float, default=0)
    quantidade = db.Column(db.Integer, default=0)
    fabricante = db.Column(db.String(200))
    validade = db.Column(db.Date)
    descricao = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'farmaciaId': str(self.farmacia_id),
            'nome': self.nome,
            'categoria': self.categoria,
            'preco': self.preco,
            'quantidade': self.quantidade,
            'fabricante': self.fabricante,
            'validade': self.validade.strftime('%Y-%m-%d') if self.validade else None,
            'descricao': self.descricao
        }

class Hospital(db.Model):
    __tablename__ = 'hospitais'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    endereco = db.Column(db.String(300))
    telefone = db.Column(db.String(50))
    horario = db.Column(db.String(100))
    servicos = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'endereco': self.endereco,
            'telefone': self.telefone,
            'horario': self.horario,
            'servicos': self.servicos,
            'latitude': self.latitude,
            'longitude': self.longitude
        }

class CentroSaude(db.Model):
    __tablename__ = 'centros'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    endereco = db.Column(db.String(300))
    telefone = db.Column(db.String(50))
    horario = db.Column(db.String(100))
    servicos = db.Column(db.Text)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'endereco': self.endereco,
            'telefone': self.telefone,
            'horario': self.horario,
            'servicos': self.servicos,
            'latitude': self.latitude,
            'longitude': self.longitude
        }

class Emergencia(db.Model):
    __tablename__ = 'emergencias'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(200), nullable=False)
    tipo = db.Column(db.String(50))
    telefone = db.Column(db.String(50))
    disponibilidade = db.Column(db.String(50))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'tipo': self.tipo,
            'telefone': self.telefone,
            'disponibilidade': self.disponibilidade
        }


        
class Avaliacao(db.Model):
    __tablename__ = 'avaliacoes'
    
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100))
    nota = db.Column(db.Integer, nullable=False)
    comentario = db.Column(db.Text, nullable=False)
    tipo = db.Column(db.String(50), default='site')
    tipo_id = db.Column(db.Integer, nullable=True)
    aprovado = db.Column(db.Boolean, default=True)  # Agora aprovado automaticamente
    resposta = db.Column(db.Text, nullable=True)  # Resposta do admin
    respondido_por = db.Column(db.String(100), nullable=True)  # Quem respondeu
    data_resposta = db.Column(db.DateTime, nullable=True)
    data = db.Column(db.DateTime, default=datetime.utcnow)
    ip = db.Column(db.String(50))
    
    def to_dict(self):
        return {
            'id': self.id,
            'nome': self.nome,
            'email': self.email,
            'nota': self.nota,
            'comentario': self.comentario,
            'tipo': self.tipo,
            'tipo_id': self.tipo_id,
            'aprovado': self.aprovado,
            'resposta': self.resposta,
            'respondido_por': self.respondido_por,
            'data_resposta': self.data_resposta.strftime('%d/%m/%Y %H:%M') if self.data_resposta else None,
            'data': self.data.strftime('%d/%m/%Y %H:%M'),
            'ip': self.ip
        }

class Visitante(db.Model):
    __tablename__ = 'visitantes'
    
    id = db.Column(db.Integer, primary_key=True)
    ip = db.Column(db.String(50), nullable=False)
    pagina = db.Column(db.String(200))
    user_agent = db.Column(db.String(500))
    data_hora = db.Column(db.DateTime, default=datetime.utcnow)
    sessao_id = db.Column(db.String(100))
    
    def to_dict(self):
        return {
            'id': self.id,
            'ip': self.ip,
            'pagina': self.pagina,
            'user_agent': self.user_agent,
            'data_hora': self.data_hora.strftime('%d/%m/%Y %H:%M:%S'),
            'sessao_id': self.sessao_id
        }

class EstatisticaVisita(db.Model):
    __tablename__ = 'estatisticas_visitas'
    
    id = db.Column(db.Integer, primary_key=True)
    data = db.Column(db.Date, default=datetime.utcnow().date)
    visitantes_unicos = db.Column(db.Integer, default=0)
    visualizacoes = db.Column(db.Integer, default=0)
    page_views = db.Column(db.Integer, default=0)  # dicionário em JSON