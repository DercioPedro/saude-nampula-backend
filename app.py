import os
from flask import Flask, request, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager, create_access_token, jwt_required, get_jwt_identity
from datetime import datetime, timedelta
from models import db, bcrypt, Farmacia, Produto, Hospital, CentroSaude, Emergencia, Avaliacao, Visitante, EstatisticaVisita
from geopy.geocoders import Nominatim

app = Flask(__name__)

# ========== CONFIGURACOES ==========
database_url = os.environ.get('DATABASE_URL', 'sqlite:///database.db')

if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)

app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'sua-chave-secreta-local')
app.config['SQLALCHEMY_DATABASE_URI'] = database_url
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['JWT_SECRET_KEY'] = os.environ.get('JWT_SECRET_KEY', 'jwt-chave-secreta-local')
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = timedelta(hours=8)

# ========== CORS ==========
CORS(app, origins=[
    'https://saude-nampula-c9az.vercel.app',
    'https://saude-nampula-api.onrender.com',
    'http://localhost:5500',
    'http://localhost:5501',
    'http://127.0.0.1:5500',
    'http://127.0.0.1:5501'
], supports_credentials=True)

jwt = JWTManager(app)
db.init_app(app)
bcrypt.init_app(app)

geocode_cache = {}

with app.app_context():
    db.create_all()
    print("Banco de dados conectado: " + database_url[:50] + "...")

# ==================== API DE FARMACIAS ====================

@app.route('/api/farmacias', methods=['GET'])
def get_farmacias():
    farmacias = Farmacia.query.all()
    return jsonify([f.to_dict() for f in farmacias])

@app.route('/api/farmacias/<int:id>', methods=['GET'])
def get_farmacia(id):
    farmacia = Farmacia.query.get_or_404(id)
    return jsonify(farmacia.to_dict())

@app.route('/api/farmacias/login', methods=['POST'])
def login_farmacia():
    data = request.get_json()
    farmacia_id = data.get('farmaciaId')
    senha = data.get('senha')
    
    farmacia = Farmacia.query.get(farmacia_id)
    if not farmacia:
        return jsonify({'error': 'Farmacia nao encontrada'}), 404
    
    if not farmacia.senha_hash:
        return jsonify({'error': 'Farmacia sem senha cadastrada. Faca primeiro acesso.'}), 401
    
    if farmacia.check_senha(senha):
        access_token = create_access_token(identity=str(farmacia.id))
        return jsonify({
            'success': True,
            'token': access_token,
            'farmacia': farmacia.to_dict()
        })
    
    return jsonify({'error': 'Senha incorreta'}), 401

@app.route('/api/farmacias/<int:id>/senha', methods=['POST'])
def definir_senha_farmacia(id):
    data = request.get_json()
    senha = data.get('senha')
    
    if not senha or len(senha) < 4:
        return jsonify({'error': 'Senha deve ter no minimo 4 caracteres'}), 400
    
    farmacia = Farmacia.query.get_or_404(id)
    
    if farmacia.senha_hash:
        return jsonify({'error': 'Farmacia ja possui senha cadastrada'}), 400
    
    farmacia.set_senha(senha)
    db.session.commit()
    
    access_token = create_access_token(identity=str(farmacia.id))
    
    return jsonify({
        'success': True,
        'token': access_token,
        'farmacia': farmacia.to_dict()
    })

@app.route('/api/farmacias', methods=['POST'])
def create_farmacia():
    data = request.get_json()
    
    farmacia = Farmacia(
        nome=data['nome'],
        endereco=data.get('endereco', ''),
        telefone=data.get('telefone', ''),
        horario=data.get('horario', ''),
        plantao=data.get('plantao', False),
        latitude=data.get('latitude'),
        longitude=data.get('longitude')
    )
    
    db.session.add(farmacia)
    db.session.commit()
    
    return jsonify(farmacia.to_dict()), 201

@app.route('/api/farmacias/<int:id>', methods=['PUT'])
def update_farmacia(id):
    farmacia = Farmacia.query.get_or_404(id)
    data = request.get_json()
    
    farmacia.nome = data.get('nome', farmacia.nome)
    farmacia.endereco = data.get('endereco', farmacia.endereco)
    farmacia.telefone = data.get('telefone', farmacia.telefone)
    farmacia.horario = data.get('horario', farmacia.horario)
    farmacia.plantao = data.get('plantao', farmacia.plantao)
    
    if 'latitude' in data:
        farmacia.latitude = data['latitude']
    if 'longitude' in data:
        farmacia.longitude = data['longitude']
    
    db.session.commit()
    return jsonify(farmacia.to_dict())

@app.route('/api/farmacias/<int:id>', methods=['DELETE'])
def delete_farmacia(id):
    farmacia = Farmacia.query.get_or_404(id)
    db.session.delete(farmacia)
    db.session.commit()
    return jsonify({'message': 'Farmacia deletada com sucesso'})

# ==================== API DE PRODUTOS ====================

@app.route('/api/produtos', methods=['GET'])
def get_produtos():
    farmacia_id = request.args.get('farmaciaId')
    
    if farmacia_id:
        produtos = Produto.query.filter_by(farmacia_id=farmacia_id).all()
    else:
        produtos = Produto.query.all()
    
    return jsonify([p.to_dict() for p in produtos])

@app.route('/api/produtos', methods=['POST'])
def create_produto():
    data = request.get_json()
    
    produto = Produto(
        farmacia_id=data['farmaciaId'],
        nome=data['nome'],
        categoria=data.get('categoria', 'Medicamento'),
        preco=data.get('preco', 0),
        quantidade=data.get('quantidade', 0),
        fabricante=data.get('fabricante', ''),
        descricao=data.get('descricao', '')
    )
    
    if data.get('validade'):
        produto.validade = datetime.strptime(data['validade'], '%Y-%m-%d').date()
    
    db.session.add(produto)
    db.session.commit()
    
    return jsonify(produto.to_dict()), 201

@app.route('/api/produtos/<int:id>', methods=['PUT'])
def update_produto(id):
    produto = Produto.query.get_or_404(id)
    data = request.get_json()
    
    produto.nome = data.get('nome', produto.nome)
    produto.categoria = data.get('categoria', produto.categoria)
    produto.preco = data.get('preco', produto.preco)
    produto.quantidade = data.get('quantidade', produto.quantidade)
    produto.fabricante = data.get('fabricante', produto.fabricante)
    produto.descricao = data.get('descricao', produto.descricao)
    
    if data.get('validade'):
        produto.validade = datetime.strptime(data['validade'], '%Y-%m-%d').date()
    
    db.session.commit()
    return jsonify(produto.to_dict())

@app.route('/api/produtos/<int:id>', methods=['DELETE'])
def delete_produto(id):
    produto = Produto.query.get_or_404(id)
    db.session.delete(produto)
    db.session.commit()
    return jsonify({'message': 'Produto deletado com sucesso'})

# ==================== API DE HOSPITAIS ====================

@app.route('/api/hospitais', methods=['GET'])
def get_hospitais():
    hospitais = Hospital.query.all()
    return jsonify([h.to_dict() for h in hospitais])

@app.route('/api/hospitais/<int:id>', methods=['GET'])
def get_hospital(id):
    hospital = Hospital.query.get_or_404(id)
    return jsonify(hospital.to_dict())

@app.route('/api/hospitais', methods=['POST'])
def create_hospital():
    data = request.get_json()
    hospital = Hospital(
        nome=data['nome'],
        endereco=data.get('endereco', ''),
        telefone=data.get('telefone', ''),
        horario=data.get('horario', ''),
        servicos=data.get('servicos', ''),
        latitude=data.get('latitude'),
        longitude=data.get('longitude')
    )
    
    db.session.add(hospital)
    db.session.commit()
    return jsonify(hospital.to_dict()), 201

@app.route('/api/hospitais/<int:id>', methods=['PUT'])
def update_hospital(id):
    hospital = Hospital.query.get_or_404(id)
    data = request.get_json()
    
    hospital.nome = data.get('nome', hospital.nome)
    hospital.endereco = data.get('endereco', hospital.endereco)
    hospital.telefone = data.get('telefone', hospital.telefone)
    hospital.horario = data.get('horario', hospital.horario)
    hospital.servicos = data.get('servicos', hospital.servicos)
    
    if 'latitude' in data:
        hospital.latitude = data['latitude']
    if 'longitude' in data:
        hospital.longitude = data['longitude']
    
    db.session.commit()
    return jsonify(hospital.to_dict())

@app.route('/api/hospitais/<int:id>', methods=['DELETE'])
def delete_hospital(id):
    hospital = Hospital.query.get_or_404(id)
    db.session.delete(hospital)
    db.session.commit()
    return jsonify({'message': 'Hospital deletado com sucesso'})

# ==================== API DE CENTROS DE SAUDE ====================

@app.route('/api/centros', methods=['GET'])
def get_centros():
    centros = CentroSaude.query.all()
    return jsonify([c.to_dict() for c in centros])

@app.route('/api/centros/<int:id>', methods=['GET'])
def get_centro(id):
    centro = CentroSaude.query.get_or_404(id)
    return jsonify(centro.to_dict())

@app.route('/api/centros', methods=['POST'])
def create_centro():
    data = request.get_json()
    centro = CentroSaude(
        nome=data['nome'],
        endereco=data.get('endereco', ''),
        telefone=data.get('telefone', ''),
        horario=data.get('horario', ''),
        servicos=data.get('servicos', ''),
        latitude=data.get('latitude'),
        longitude=data.get('longitude')
    )
    
    db.session.add(centro)
    db.session.commit()
    return jsonify(centro.to_dict()), 201

@app.route('/api/centros/<int:id>', methods=['PUT'])
def update_centro(id):
    centro = CentroSaude.query.get_or_404(id)
    data = request.get_json()
    
    centro.nome = data.get('nome', centro.nome)
    centro.endereco = data.get('endereco', centro.endereco)
    centro.telefone = data.get('telefone', centro.telefone)
    centro.horario = data.get('horario', centro.horario)
    centro.servicos = data.get('servicos', centro.servicos)
    
    if 'latitude' in data:
        centro.latitude = data['latitude']
    if 'longitude' in data:
        centro.longitude = data['longitude']
    
    db.session.commit()
    return jsonify(centro.to_dict())

@app.route('/api/centros/<int:id>', methods=['DELETE'])
def delete_centro(id):
    centro = CentroSaude.query.get_or_404(id)
    db.session.delete(centro)
    db.session.commit()
    return jsonify({'message': 'Centro deletado com sucesso'})

# ==================== API DE EMERGENCIAS ====================

@app.route('/api/emergencias', methods=['GET'])
def get_emergencias():
    emergencias = Emergencia.query.all()
    return jsonify([e.to_dict() for e in emergencias])

@app.route('/api/emergencias/<int:id>', methods=['GET'])
def get_emergencia(id):
    emergencia = Emergencia.query.get_or_404(id)
    return jsonify(emergencia.to_dict())

@app.route('/api/emergencias', methods=['POST'])
def create_emergencia():
    data = request.get_json()
    emergencia = Emergencia(
        nome=data['nome'],
        tipo=data.get('tipo', ''),
        telefone=data.get('telefone', ''),
        disponibilidade=data.get('disponibilidade', '24/7')
    )
    db.session.add(emergencia)
    db.session.commit()
    return jsonify(emergencia.to_dict()), 201

@app.route('/api/emergencias/<int:id>', methods=['PUT'])
def update_emergencia(id):
    emergencia = Emergencia.query.get_or_404(id)
    data = request.get_json()
    
    emergencia.nome = data.get('nome', emergencia.nome)
    emergencia.tipo = data.get('tipo', emergencia.tipo)
    emergencia.telefone = data.get('telefone', emergencia.telefone)
    emergencia.disponibilidade = data.get('disponibilidade', emergencia.disponibilidade)
    
    db.session.commit()
    return jsonify(emergencia.to_dict())

@app.route('/api/emergencias/<int:id>', methods=['DELETE'])
def delete_emergencia(id):
    emergencia = Emergencia.query.get_or_404(id)
    db.session.delete(emergencia)
    db.session.commit()
    return jsonify({'message': 'Contato deletado com sucesso'})

# ==================== API DE ESTATISTICAS ====================

@app.route('/api/estatisticas', methods=['GET'])
def get_estatisticas():
    return jsonify({
        'hospitais': Hospital.query.count(),
        'centros': CentroSaude.query.count(),
        'farmacias': Farmacia.query.count(),
        'emergencias': Emergencia.query.count()
    })

# ==================== ADMIN LOGIN ====================

ADMIN_USERNAME = "saudemz"
ADMIN_PASSWORD_HASH = bcrypt.generate_password_hash("197827").decode('utf-8')

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')
    
    if username == ADMIN_USERNAME and bcrypt.check_password_hash(ADMIN_PASSWORD_HASH, password):
        access_token = create_access_token(identity="admin")
        return jsonify({
            'success': True,
            'token': access_token,
            'username': username
        })
    
    return jsonify({'error': 'Credenciais invalidas'}), 401

# ==================== API DE AVALIACOES ====================

@app.route('/api/avaliacoes', methods=['GET'])
def get_avaliacoes():
    tipo = request.args.get('tipo', 'site')
    tipo_id = request.args.get('tipo_id')
    
    query = Avaliacao.query.filter_by(aprovado=True, tipo=tipo)
    
    if tipo_id:
        query = query.filter_by(tipo_id=tipo_id)
    
    avaliacoes = query.order_by(Avaliacao.data.desc()).limit(20).all()
    return jsonify([a.to_dict() for a in avaliacoes])

@app.route('/api/avaliacoes/todas', methods=['GET'])
@jwt_required()
def get_todas_avaliacoes():
    tipo = request.args.get('tipo')
    query = Avaliacao.query
    
    if tipo:
        query = query.filter_by(tipo=tipo)
    
    avaliacoes = query.order_by(Avaliacao.data.desc()).all()
    return jsonify([a.to_dict() for a in avaliacoes])

@app.route('/api/avaliacoes', methods=['POST'])
def criar_avaliacao():
    data = request.get_json()
    
    if not data.get('nome') or not data.get('comentario'):
        return jsonify({'error': 'Nome e comentario sao obrigatorios'}), 400
    
    if not data.get('nota') or data['nota'] < 1 or data['nota'] > 5:
        return jsonify({'error': 'Nota deve ser entre 1 e 5'}), 400
    
    ip = request.remote_addr
    
    avaliacao = Avaliacao(
        nome=data['nome'],
        email=data.get('email', ''),
        nota=data['nota'],
        comentario=data['comentario'],
        tipo=data.get('tipo', 'site'),
        tipo_id=data.get('tipo_id'),
        aprovado=True,
        ip=ip
    )
    
    db.session.add(avaliacao)
    db.session.commit()
    
    return jsonify({'success': True, 'message': 'Avaliacao enviada com sucesso!'}), 201

@app.route('/api/avaliacoes/<int:id>/responder', methods=['POST'])
@jwt_required()
def responder_avaliacao(id):
    data = request.get_json()
    resposta = data.get('resposta')
    
    if not resposta:
        return jsonify({'error': 'Resposta nao pode ser vazia'}), 400
    
    avaliacao = Avaliacao.query.get_or_404(id)
    avaliacao.resposta = resposta
    avaliacao.respondido_por = get_jwt_identity()
    avaliacao.data_resposta = datetime.utcnow()
    
    db.session.commit()
    return jsonify({'success': True, 'message': 'Resposta enviada com sucesso!'})

@app.route('/api/avaliacoes/<int:id>/aprovar', methods=['PUT'])
@jwt_required()
def aprovar_avaliacao(id):
    avaliacao = Avaliacao.query.get_or_404(id)
    avaliacao.aprovado = True
    db.session.commit()
    return jsonify({'success': True, 'message': 'Avaliacao aprovada!'})

@app.route('/api/avaliacoes/<int:id>', methods=['DELETE'])
@jwt_required()
def deletar_avaliacao(id):
    avaliacao = Avaliacao.query.get_or_404(id)
    db.session.delete(avaliacao)
    db.session.commit()
    return jsonify({'message': 'Avaliacao deletada com sucesso'})

@app.route('/api/avaliacoes/estatisticas', methods=['GET'])
def get_estatisticas_avaliacoes():
    tipo = request.args.get('tipo', 'site')
    tipo_id = request.args.get('tipo_id')
    
    query = Avaliacao.query.filter_by(aprovado=True, tipo=tipo)
    if tipo_id:
        query = query.filter_by(tipo_id=tipo_id)
    
    avaliacoes = query.all()
    
    if not avaliacoes:
        return jsonify({
            'total': 0,
            'media': 0,
            'distribuicao': {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
        })
    
    soma = sum(a.nota for a in avaliacoes)
    media = soma / len(avaliacoes)
    
    distribuicao = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    for a in avaliacoes:
        distribuicao[a.nota] += 1
    
    return jsonify({
        'total': len(avaliacoes),
        'media': round(media, 1),
        'distribuicao': distribuicao
    })

# ==================== API DE VISITANTES ====================

@app.route('/api/visitantes/registrar', methods=['POST'])
def registrar_visita():
    data = request.get_json()
    
    ip = request.remote_addr
    sessao_id = data.get('sessao_id')
    pagina = data.get('pagina', 'desconhecida')
    user_agent = request.headers.get('User-Agent', '')
    
    visita = Visitante(
        ip=ip,
        pagina=pagina,
        user_agent=user_agent[:500],
        sessao_id=sessao_id
    )
    db.session.add(visita)
    
    hoje = datetime.utcnow().date()
    estatistica = EstatisticaVisita.query.filter_by(data=hoje).first()
    
    if not estatistica:
        estatistica = EstatisticaVisita(data=hoje, visitantes_unicos=0, visualizacoes=0)
        db.session.add(estatistica)
    
    visitas_hoje = Visitante.query.filter(
        Visitante.data_hora >= datetime(hoje.year, hoje.month, hoje.day)
    ).all()
    
    sessoes_unicas = set(v.sessao_id for v in visitas_hoje if v.sessao_id)
    estatistica.visitantes_unicos = len(sessoes_unicas)
    estatistica.visualizacoes = len(visitas_hoje)
    
    db.session.commit()
    
    return jsonify({'success': True})

@app.route('/api/visitantes/estatisticas', methods=['GET'])
@jwt_required()
def get_estatisticas_visitantes():
    dias = request.args.get('dias', 7, type=int)
    
    data_inicio = datetime.utcnow().date() - timedelta(days=dias)
    
    estatisticas = EstatisticaVisita.query.filter(
        EstatisticaVisita.data >= data_inicio
    ).order_by(EstatisticaVisita.data).all()
    
    resultado = []
    for e in estatisticas:
        resultado.append({
            'data': e.data.strftime('%d/%m/%Y'),
            'visitantes_unicos': e.visitantes_unicos,
            'visualizacoes': e.visualizacoes
        })
    
    total_visitas = Visitante.query.count()
    total_sessoes = len(set(v.sessao_id for v in Visitante.query.all() if v.sessao_id))
    
    return jsonify({
        'por_dia': resultado,
        'total_visitas': total_visitas,
        'total_sessoes': total_sessoes
    })

@app.route('/api/visitantes/paginas', methods=['GET'])
@jwt_required()
def get_paginas_mais_acessadas():
    from sqlalchemy import func
    
    paginas = db.session.query(
        Visitante.pagina, 
        func.count(Visitante.id).label('total')
    ).group_by(Visitante.pagina).order_by(func.count(Visitante.id).desc()).limit(10).all()
    
    return jsonify([{'pagina': p[0], 'total': p[1]} for p in paginas])

# ==================== API DE GEOCODIFICACAO ====================

@app.route('/api/geocode', methods=['POST'])
def geocode_endereco():
    data = request.get_json()
    endereco = data.get('endereco')
    
    if not endereco:
        return jsonify({'error': 'Endereco nao informado'}), 400
    
    if endereco in geocode_cache:
        return jsonify(geocode_cache[endereco])
    
    try:
        geolocator = Nominatim(user_agent="saude_nampula")
        endereco_completo = endereco + ", Nampula, Mocambique"
        location = geolocator.geocode(endereco_completo)
        
        if location:
            resultado = {
                'success': True,
                'latitude': location.latitude,
                'longitude': location.longitude
            }
            geocode_cache[endereco] = resultado
            return jsonify(resultado)
        else:
            return jsonify({'success': False, 'error': 'Endereco nao encontrado'}), 404
            
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

# ==================== INICIAR SERVIDOR ====================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=False, host='0.0.0.0', port=port)
