const express = require('express');
const cors = require('cors');
const jwt = require('jsonwebtoken');
const bcrypt = require('bcryptjs');
const { createClient } = require('@supabase/supabase-js');
const fetch = require('node-fetch');
require('dotenv').config();

const app = express();
const port = process.env.PORT || 3000;

// ========== CONFIGURACAO CORS CORRIGIDA ==========
const allowedOrigins = [
    'https://saude-nampula-c9az.vercel.app',
    'https://saude-nampula-backend.onrender.com',
    'http://localhost:5500',
    'http://localhost:5501',
    'http://127.0.0.1:5500',
    'http://127.0.0.1:5501'
];

app.use(cors({
    origin: function(origin, callback) {
        // Permitir requisições sem origem (como mobile apps ou curl)
        if (!origin) return callback(null, true);
        if (allowedOrigins.indexOf(origin) !== -1) {
            callback(null, true);
        } else {
            console.log('Origin bloqueada:', origin);
            callback(null, true); // Temporariamente permitindo todas para teste
        }
    },
    credentials: true,
    methods: ['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'],
    allowedHeaders: ['Content-Type', 'Authorization', 'X-Requested-With']
}));

// Responder preflight requests imediatamente
app.options('*', cors());

app.use(express.json());

// Middleware para logging (ajuda a debuggar)
app.use((req, res, next) => {
    console.log(`${req.method} ${req.url} - Origin: ${req.headers.origin}`);
    next();
});

// ========== SUPABASE ==========
const supabase = createClient(
    process.env.SUPABASE_URL,
    process.env.SUPABASE_KEY
);

// ========== ADMIN LOGIN ==========
const ADMIN_USERNAME = "saudemz";
const ADMIN_PASSWORD_HASH = bcrypt.hashSync("197827", 10);

app.post('/api/admin/login', async (req, res) => {
    const { username, password } = req.body;
    
    if (username === ADMIN_USERNAME && bcrypt.compareSync(password, ADMIN_PASSWORD_HASH)) {
        const token = jwt.sign({ id: "admin", username: username }, process.env.JWT_SECRET, { expiresIn: '8h' });
        return res.json({ success: true, token, username });
    }
    
    res.status(401).json({ error: 'Credenciais invalidas' });
});

// ========== MIDDLEWARE ==========
const authenticateJWT = (req, res, next) => {
    const authHeader = req.headers.authorization;
    if (!authHeader) {
        return res.status(401).json({ error: 'Token nao fornecido' });
    }
    
    const token = authHeader.split(' ')[1];
    try {
        const decoded = jwt.verify(token, process.env.JWT_SECRET);
        req.user = decoded;
        next();
    } catch (error) {
        return res.status(403).json({ error: 'Token invalido' });
    }
};

// ==================== FARMACIAS ====================

app.get('/api/farmacias', async (req, res) => {
    const { data, error } = await supabase.from('farmacias').select('*');
    if (error) return res.status(500).json({ error: error.message });
    res.json(data);
});

app.get('/api/farmacias/:id', async (req, res) => {
    const { data, error } = await supabase.from('farmacias').select('*').eq('id', req.params.id).single();
    if (error) return res.status(404).json({ error: 'Farmacia nao encontrada' });
    res.json(data);
});

app.post('/api/farmacias/login', async (req, res) => {
    const { farmaciaId, senha } = req.body;
    
    const { data: farmacia, error } = await supabase.from('farmacias').select('*').eq('id', farmaciaId).single();
    if (error || !farmacia) {
        return res.status(404).json({ error: 'Farmacia nao encontrada' });
    }
    
    if (!farmacia.senha_hash) {
        return res.status(401).json({ error: 'Farmacia sem senha cadastrada. Faca primeiro acesso.' });
    }
    
    const senhaValida = bcrypt.compareSync(senha, farmacia.senha_hash);
    if (senhaValida) {
        const token = jwt.sign({ id: farmacia.id, nome: farmacia.nome }, process.env.JWT_SECRET, { expiresIn: '8h' });
        return res.json({ success: true, token, farmacia });
    }
    
    res.status(401).json({ error: 'Senha incorreta' });
});

app.post('/api/farmacias/:id/senha', async (req, res) => {
    const { id } = req.params;
    const { senha } = req.body;
    
    if (!senha || senha.length < 4) {
        return res.status(400).json({ error: 'Senha deve ter no minimo 4 caracteres' });
    }
    
    const { data: farmacia, error } = await supabase.from('farmacias').select('*').eq('id', id).single();
    if (error || !farmacia) {
        return res.status(404).json({ error: 'Farmacia nao encontrada' });
    }
    
    if (farmacia.senha_hash) {
        return res.status(400).json({ error: 'Farmacia ja possui senha cadastrada' });
    }
    
    const senhaHash = bcrypt.hashSync(senha, 10);
    const { data: updated, error: updateError } = await supabase.from('farmacias').update({ senha_hash: senhaHash }).eq('id', id).select().single();
    
    if (updateError) return res.status(500).json({ error: updateError.message });
    
    const token = jwt.sign({ id: updated.id, nome: updated.nome }, process.env.JWT_SECRET, { expiresIn: '8h' });
    res.json({ success: true, token, farmacia: updated });
});

app.post('/api/farmacias', authenticateJWT, async (req, res) => {
    const { data, error } = await supabase.from('farmacias').insert(req.body).select().single();
    if (error) return res.status(500).json({ error: error.message });
    res.status(201).json(data);
});

app.put('/api/farmacias/:id', authenticateJWT, async (req, res) => {
    const { data, error } = await supabase.from('farmacias').update(req.body).eq('id', req.params.id).select().single();
    if (error) return res.status(500).json({ error: error.message });
    res.json(data);
});

app.delete('/api/farmacias/:id', authenticateJWT, async (req, res) => {
    const { error } = await supabase.from('farmacias').delete().eq('id', req.params.id);
    if (error) return res.status(500).json({ error: error.message });
    res.json({ message: 'Farmacia deletada com sucesso' });
});

// ==================== HOSPITAIS ====================

app.get('/api/hospitais', async (req, res) => {
    const { data, error } = await supabase.from('hospitais').select('*');
    if (error) return res.status(500).json({ error: error.message });
    res.json(data);
});

app.get('/api/hospitais/:id', async (req, res) => {
    const { data, error } = await supabase.from('hospitais').select('*').eq('id', req.params.id).single();
    if (error) return res.status(404).json({ error: 'Hospital nao encontrado' });
    res.json(data);
});

app.post('/api/hospitais', authenticateJWT, async (req, res) => {
    const { data, error } = await supabase.from('hospitais').insert(req.body).select().single();
    if (error) return res.status(500).json({ error: error.message });
    res.status(201).json(data);
});

app.put('/api/hospitais/:id', authenticateJWT, async (req, res) => {
    const { data, error } = await supabase.from('hospitais').update(req.body).eq('id', req.params.id).select().single();
    if (error) return res.status(500).json({ error: error.message });
    res.json(data);
});

app.delete('/api/hospitais/:id', authenticateJWT, async (req, res) => {
    const { error } = await supabase.from('hospitais').delete().eq('id', req.params.id);
    if (error) return res.status(500).json({ error: error.message });
    res.json({ message: 'Hospital deletado com sucesso' });
});

// ==================== CENTROS ====================

app.get('/api/centros', async (req, res) => {
    const { data, error } = await supabase.from('centros').select('*');
    if (error) return res.status(500).json({ error: error.message });
    res.json(data);
});

app.get('/api/centros/:id', async (req, res) => {
    const { data, error } = await supabase.from('centros').select('*').eq('id', req.params.id).single();
    if (error) return res.status(404).json({ error: 'Centro nao encontrado' });
    res.json(data);
});

app.post('/api/centros', authenticateJWT, async (req, res) => {
    const { data, error } = await supabase.from('centros').insert(req.body).select().single();
    if (error) return res.status(500).json({ error: error.message });
    res.status(201).json(data);
});

app.put('/api/centros/:id', authenticateJWT, async (req, res) => {
    const { data, error } = await supabase.from('centros').update(req.body).eq('id', req.params.id).select().single();
    if (error) return res.status(500).json({ error: error.message });
    res.json(data);
});

app.delete('/api/centros/:id', authenticateJWT, async (req, res) => {
    const { error } = await supabase.from('centros').delete().eq('id', req.params.id);
    if (error) return res.status(500).json({ error: error.message });
    res.json({ message: 'Centro deletado com sucesso' });
});

// ==================== EMERGENCIAS ====================

app.get('/api/emergencias', async (req, res) => {
    const { data, error } = await supabase.from('emergencias').select('*');
    if (error) return res.status(500).json({ error: error.message });
    res.json(data);
});

app.post('/api/emergencias', authenticateJWT, async (req, res) => {
    const { data, error } = await supabase.from('emergencias').insert(req.body).select().single();
    if (error) return res.status(500).json({ error: error.message });
    res.status(201).json(data);
});

app.put('/api/emergencias/:id', authenticateJWT, async (req, res) => {
    const { data, error } = await supabase.from('emergencias').update(req.body).eq('id', req.params.id).select().single();
    if (error) return res.status(500).json({ error: error.message });
    res.json(data);
});

app.delete('/api/emergencias/:id', authenticateJWT, async (req, res) => {
    const { error } = await supabase.from('emergencias').delete().eq('id', req.params.id);
    if (error) return res.status(500).json({ error: error.message });
    res.json({ message: 'Contato deletado com sucesso' });
});

// ==================== PRODUTOS ====================

app.get('/api/produtos', async (req, res) => {
    const { farmaciaId } = req.query;
    let query = supabase.from('produtos').select('*');
    if (farmaciaId) query = query.eq('farmacia_id', farmaciaId);
    const { data, error } = await query;
    if (error) return res.status(500).json({ error: error.message });
    res.json(data);
});

app.post('/api/produtos', authenticateJWT, async (req, res) => {
    const { data, error } = await supabase.from('produtos').insert(req.body).select().single();
    if (error) return res.status(500).json({ error: error.message });
    res.status(201).json(data);
});

app.put('/api/produtos/:id', authenticateJWT, async (req, res) => {
    const { data, error } = await supabase.from('produtos').update(req.body).eq('id', req.params.id).select().single();
    if (error) return res.status(500).json({ error: error.message });
    res.json(data);
});

app.delete('/api/produtos/:id', authenticateJWT, async (req, res) => {
    const { error } = await supabase.from('produtos').delete().eq('id', req.params.id);
    if (error) return res.status(500).json({ error: error.message });
    res.json({ message: 'Produto deletado com sucesso' });
});

// ==================== AVALIACOES ====================

app.get('/api/avaliacoes', async (req, res) => {
    const { tipo, tipo_id } = req.query;
    let query = supabase.from('avaliacoes').select('*').eq('aprovado', true);
    if (tipo) query = query.eq('tipo', tipo);
    if (tipo_id) query = query.eq('tipo_id', tipo_id);
    const { data, error } = await query.order('data', { ascending: false }).limit(20);
    if (error) return res.status(500).json({ error: error.message });
    res.json(data);
});

app.get('/api/avaliacoes/todas', authenticateJWT, async (req, res) => {
    const { tipo } = req.query;
    let query = supabase.from('avaliacoes').select('*');
    if (tipo) query = query.eq('tipo', tipo);
    const { data, error } = await query.order('data', { ascending: false });
    if (error) return res.status(500).json({ error: error.message });
    res.json(data);
});

app.post('/api/avaliacoes', async (req, res) => {
    const { nome, email, nota, comentario, tipo, tipo_id } = req.body;
    
    if (!nome || !comentario) {
        return res.status(400).json({ error: 'Nome e comentario sao obrigatorios' });
    }
    if (!nota || nota < 1 || nota > 5) {
        return res.status(400).json({ error: 'Nota deve ser entre 1 e 5' });
    }
    
    const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
    
    const { data, error } = await supabase.from('avaliacoes').insert({
        nome, email, nota, comentario, tipo: tipo || 'site', tipo_id, aprovado: true, ip
    }).select().single();
    
    if (error) return res.status(500).json({ error: error.message });
    res.status(201).json({ success: true, message: 'Avaliacao enviada com sucesso!' });
});

app.post('/api/avaliacoes/:id/responder', authenticateJWT, async (req, res) => {
    const { resposta } = req.body;
    if (!resposta) return res.status(400).json({ error: 'Resposta nao pode ser vazia' });
    
    const { data, error } = await supabase.from('avaliacoes').update({
        resposta,
        respondido_por: req.user.id,
        data_resposta: new Date()
    }).eq('id', req.params.id).select().single();
    
    if (error) return res.status(500).json({ error: error.message });
    res.json({ success: true, message: 'Resposta enviada com sucesso!' });
});

app.delete('/api/avaliacoes/:id', authenticateJWT, async (req, res) => {
    const { error } = await supabase.from('avaliacoes').delete().eq('id', req.params.id);
    if (error) return res.status(500).json({ error: error.message });
    res.json({ message: 'Avaliacao deletada com sucesso' });
});

app.get('/api/avaliacoes/estatisticas', async (req, res) => {
    const { tipo, tipo_id } = req.query;
    let query = supabase.from('avaliacoes').select('*').eq('aprovado', true);
    if (tipo) query = query.eq('tipo', tipo);
    if (tipo_id) query = query.eq('tipo_id', tipo_id);
    const { data, error } = await query;
    
    if (error || !data || data.length === 0) {
        return res.json({ total: 0, media: 0, distribuicao: { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 } });
    }
    
    const soma = data.reduce((acc, a) => acc + a.nota, 0);
    const media = soma / data.length;
    const distribuicao = { 1: 0, 2: 0, 3: 0, 4: 0, 5: 0 };
    data.forEach(a => { distribuicao[a.nota]++ });
    
    res.json({ total: data.length, media: Math.round(media * 10) / 10, distribuicao });
});

// ==================== ESTATISTICAS ====================

app.get('/api/estatisticas', async (req, res) => {
    const [hospitais, centros, farmacias, emergencias] = await Promise.all([
        supabase.from('hospitais').select('*', { count: 'exact', head: true }),
        supabase.from('centros').select('*', { count: 'exact', head: true }),
        supabase.from('farmacias').select('*', { count: 'exact', head: true }),
        supabase.from('emergencias').select('*', { count: 'exact', head: true })
    ]);
    
    res.json({
        hospitais: hospitais.count || 0,
        centros: centros.count || 0,
        farmacias: farmacias.count || 0,
        emergencias: emergencias.count || 0
    });
});

// ==================== VISITANTES ====================

app.post('/api/visitantes/registrar', async (req, res) => {
    const { sessao_id, pagina } = req.body;
    const ip = req.headers['x-forwarded-for'] || req.socket.remoteAddress;
    const userAgent = req.headers['user-agent'];
    
    await supabase.from('visitantes').insert({ ip, pagina, user_agent: userAgent, sessao_id });
    
    const hoje = new Date().toISOString().split('T')[0];
    const { data: estatistica } = await supabase.from('estatisticas_visitas').select('*').eq('data', hoje).single();
    
    if (estatistica) {
        await supabase.from('estatisticas_visitas').update({ visualizacoes: (estatistica.visualizacoes || 0) + 1 }).eq('data', hoje);
    } else {
        await supabase.from('estatisticas_visitas').insert({ data: hoje, visualizacoes: 1 });
    }
    
    res.json({ success: true });
});

// ==================== GEOCODIFICACAO ====================

const geocodeCache = {};

app.post('/api/geocode', async (req, res) => {
    const { endereco } = req.body;
    if (!endereco) return res.status(400).json({ error: 'Endereco nao informado' });
    
    if (geocodeCache[endereco]) return res.json(geocodeCache[endereco]);
    
    try {
        const enderecoCompleto = encodeURIComponent(`${endereco}, Nampula, Mocambique`);
        const response = await fetch(`https://nominatim.openstreetmap.org/search?q=${enderecoCompleto}&format=json&limit=1`);
        const data = await response.json();
        
        if (data && data.length > 0) {
            const resultado = { success: true, latitude: parseFloat(data[0].lat), longitude: parseFloat(data[0].lon) };
            geocodeCache[endereco] = resultado;
            return res.json(resultado);
        }
        return res.status(404).json({ success: false, error: 'Endereco nao encontrado' });
    } catch (error) {
        return res.status(500).json({ success: false, error: error.message });
    }
});

// ==================== INICIAR SERVIDOR ====================

app.listen(port, () => {
    console.log(`🚀 Servidor rodando na porta ${port}`);
});
