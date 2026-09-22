"""Configuração do gateway: só variáveis de ambiente, sem arquivo de config.

Tudo tem padrão utilizável. O gateway precisa subir com `python3 -m jev_gw servir`
sem ninguém ter configurado nada — a chave só é exigida quando a primeira consulta
real acontece.
"""
import os
from pathlib import Path

PORTA_PADRAO = 8770          # fora da faixa 8788-8791 do jev-gateway (vinilana)
TETO_DIARIO_PADRAO = 1.00    # dólares por dia; 0 desliga o gateway (nega tudo)
TTL_CACHE_PADRAO = 900       # segundos que uma resposta idêntica vale
TIMEOUT_PADRAO = 5.0         # segundos por consulta ao Jev


def _numero(nome, padrao, minimo=0.0):
    bruto = os.environ.get(nome, '').strip()
    if not bruto:
        return padrao
    try:
        valor = float(bruto)
    except ValueError:
        raise ValueError(f'{nome} precisa ser um número. Recebi: {bruto!r}') from None
    if valor < minimo:
        raise ValueError(f'{nome} não pode ser menor que {minimo}.')
    return valor


def raiz_dados():
    """Onde ficam o registro JSONL e o estado do orçamento."""
    bruto = os.environ.get('JEV_GW_DADOS', '').strip()
    caminho = Path(bruto).expanduser() if bruto else Path.home()/'.jev-gw'
    caminho.mkdir(parents=True, exist_ok=True)
    return caminho


def carregar():
    return {
        'porta': int(_numero('JEV_GW_PORTA', PORTA_PADRAO, 1)),
        'teto_diario': _numero('JEV_GW_TETO_DIARIO', TETO_DIARIO_PADRAO),
        'ttl_cache': _numero('JEV_GW_TTL_CACHE', TTL_CACHE_PADRAO),
        'timeout': _numero('JEV_GW_TIMEOUT', TIMEOUT_PADRAO, 0.01),
        'provedor': os.environ.get('JEV_PROVIDER', '').strip() or None,
        'dados': raiz_dados(),
    }
