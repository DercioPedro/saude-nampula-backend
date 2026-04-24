// geolocalizacao.js - Versão corrigida (sem emojis)

let localizacaoAtual = null;
let distanciaAtiva = false;
let cacheCoordenadas = {};

// URL do backend (Render)
const API_URL = 'https://saude-nampula-api.onrender.com/api';

function obterLocalizacao() {
    return new Promise((resolve, reject) => {
        if (!navigator.geolocation) {
            reject(new Error('Geolocalizacao nao suportada'));
            return;
        }
        
        navigator.geolocation.getCurrentPosition(
            (position) => {
                localizacaoAtual = {
                    lat: position.coords.latitude,
                    lng: position.coords.longitude
                };
                console.log('Localizacao obtida:', localizacaoAtual);
                resolve(localizacaoAtual);
            },
            (error) => reject(new Error('Permissao negada ou erro na localizacao')),
            { enableHighAccuracy: true, timeout: 10000 }
        );
    });
}

async function geocodeEndereco(endereco) {
    if (!endereco) return null;
    if (cacheCoordenadas[endereco]) return cacheCoordenadas[endereco];
    
    try {
        const response = await fetch(`${API_URL}/geocode`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ endereco: endereco })
        });
        
        if (response.ok) {
            const data = await response.json();
            if (data.success) {
                cacheCoordenadas[endereco] = { lat: data.latitude, lng: data.longitude };
                return cacheCoordenadas[endereco];
            }
        }
        return null;
    } catch (error) {
        console.error('Erro geocode:', error);
        return null;
    }
}

function calcularDistancia(lat1, lng1, lat2, lng2) {
    const R = 6371;
    const dLat = (lat2 - lat1) * Math.PI / 180;
    const dLng = (lng2 - lng1) * Math.PI / 180;
    const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
              Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
              Math.sin(dLng/2) * Math.sin(dLng/2);
    const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a));
    return R * c;
}

function formatarDistancia(distancia) {
    if (distancia < 1) return Math.round(distancia * 1000) + ' m';
    return distancia.toFixed(1) + ' km';
}

async function adicionarDistanciasAosCards() {
    try {
        if (!localizacaoAtual) {
            await obterLocalizacao();
        }
        
        const path = window.location.pathname;
        let itens = [];
        let tipoCard = '';
        
        if (path.includes('farm.html')) {
            const farmacias = await apiRequest('/farmacias');
            itens = farmacias.map(f => ({ ...f, tipo: 'farmacia' }));
            tipoCard = 'farmacia-card';
            console.log(itens.length + ' farmacias para processar');
        } else if (path.includes('hospital.html')) {
            const hospitais = await apiRequest('/hospitais');
            itens = hospitais.map(h => ({ ...h, tipo: 'hospital' }));
            tipoCard = 'hospital-card';
            console.log(itens.length + ' hospitais para processar');
        } else if (path.includes('centros.html')) {
            const centros = await apiRequest('/centros');
            itens = centros.map(c => ({ ...c, tipo: 'centro' }));
            tipoCard = 'centro-card';
            console.log(itens.length + ' centros para processar');
        } else {
            console.log('Pagina nao suporta geolocalizacao');
            return;
        }
        
        let cardsComDistancia = 0;
        
        for (const item of itens) {
            let coords = null;
            
            if (item.latitude && item.longitude) {
                coords = { lat: item.latitude, lng: item.longitude };
            } else if (item.endereco && item.endereco !== 'Endereco nao informado') {
                coords = await geocodeEndereco(item.endereco);
            }
            
            if (coords) {
                const distancia = calcularDistancia(localizacaoAtual.lat, localizacaoAtual.lng, coords.lat, coords.lng);
                
                const cards = document.querySelectorAll('.' + tipoCard);
                let cardEncontrado = null;
                
                for (const card of cards) {
                    const cardId = card.getAttribute('data-id');
                    if (cardId && parseInt(cardId) === item.id) {
                        cardEncontrado = card;
                        break;
                    }
                }
                
                if (cardEncontrado) {
                    const badgeAntigo = cardEncontrado.querySelector('.distancia-badge');
                    if (badgeAntigo) badgeAntigo.remove();
                    
                    const badge = document.createElement('div');
                    badge.className = 'distancia-badge';
                    badge.textContent = ' a ' + formatarDistancia(distancia);
                    badge.style.cssText = 'background: #7c3aed; color: white; padding: 4px 12px; border-radius: 20px; font-size: 12px; display: inline-block; margin-bottom: 8px; width: fit-content;';
                    
                    const primeiroFilho = cardEncontrado.firstChild;
                    cardEncontrado.insertBefore(badge, primeiroFilho);
                    cardsComDistancia++;
                } else {
                    console.log('Card nao encontrado para ID:', item.id, item.nome);
                }
            }
        }
        
        const msg = document.createElement('div');
        msg.style.cssText = 'position: fixed; bottom: 20px; right: 20px; background: #059669; color: white; padding: 10px 20px; border-radius: 8px; z-index: 1000;';
        msg.textContent = cardsComDistancia + ' estabelecimentos com distancia calculada.';
        document.body.appendChild(msg);
        setTimeout(function() { msg.remove(); }, 3000);
        
        const btnOrdenar = document.getElementById('btn-ordenar-distancia');
        if (btnOrdenar && cardsComDistancia > 0) {
            btnOrdenar.style.display = 'flex';
        }
        
    } catch (error) {
        console.error('Erro:', error);
        alert(error.message);
    }
}

function ordenarCardsPorDistancia() {
    const container = document.querySelector('.farmacias-grid, .centros-grid, main');
    if (!container) return;
    
    const cards = Array.from(container.querySelectorAll('.farmacia-card, .hospital-card, .centro-card'));
    
    const cardsComDistancia = cards.map(function(card) {
        const badge = card.querySelector('.distancia-badge');
        let distancia = Infinity;
        if (badge) {
            const texto = badge.textContent;
            const match = texto.match(/(\d+(?:\.\d+)?)\s*(?:m|km)/);
            if (match) {
                let valor = parseFloat(match[1]);
                if (texto.indexOf('km') !== -1) {
                    distancia = valor;
                } else if (texto.indexOf('m') !== -1) {
                    distancia = valor / 1000;
                }
            }
        }
        return { card: card, distancia: distancia };
    });
    
    cardsComDistancia.sort(function(a, b) {
        return a.distancia - b.distancia;
    });
    
    for (var i = 0; i < cardsComDistancia.length; i++) {
        container.appendChild(cardsComDistancia[i].card);
    }
    
    const btn = document.getElementById('btn-ordenar-distancia');
    if (btn) {
        btn.textContent = 'Ordenado!';
        setTimeout(function() {
            btn.textContent = 'Ordenar por distancia';
        }, 2000);
    }
}

function criarBotaoLocalizacao() {
    if (document.querySelector('.btn-localizacao-container')) return;
    
    const filterSection = document.querySelector('.filter-section');
    if (!filterSection) return;
    
    const container = document.createElement('div');
    container.className = 'btn-localizacao-container';
    container.style.cssText = 'margin-bottom: 20px; display: flex; gap: 10px; justify-content: flex-end;';
    
    const btnLocalizar = document.createElement('button');
    btnLocalizar.id = 'btn-localizar';
    btnLocalizar.textContent = 'Encontrar mais proximos';
    btnLocalizar.style.cssText = 'background: #7c3aed; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600;';
    
    const btnOrdenar = document.createElement('button');
    btnOrdenar.id = 'btn-ordenar-distancia';
    btnOrdenar.textContent = 'Ordenar por distancia';
    btnOrdenar.style.cssText = 'background: #059669; color: white; border: none; padding: 10px 20px; border-radius: 8px; cursor: pointer; font-weight: 600; display: none;';
    
    btnLocalizar.onclick = async function() {
        btnLocalizar.disabled = true;
        btnLocalizar.textContent = 'Calculando...';
        await adicionarDistanciasAosCards();
        btnLocalizar.disabled = false;
        btnLocalizar.textContent = 'Localizacao ativa';
        btnLocalizar.style.background = '#059669';
    };
    
    btnOrdenar.onclick = ordenarCardsPorDistancia;
    
    container.appendChild(btnLocalizar);
    container.appendChild(btnOrdenar);
    filterSection.parentNode.insertBefore(container, filterSection.nextSibling);
}

document.addEventListener('DOMContentLoaded', function() {
    if (window.location.pathname.indexOf('farm.html') !== -1 ||
        window.location.pathname.indexOf('hospital.html') !== -1 ||
        window.location.pathname.indexOf('centros.html') !== -1) {
        setTimeout(criarBotaoLocalizacao, 1000);
    }
});
