"""Cache por impressão digital do pedido, em arquivo, com validade curta.

Dois pedidos idênticos (mesmo modelo, mesmo contexto, mesmas perguntas) dentro
da validade devolvem a mesma resposta sem gastar crédito. É o caso comum de
sistema em produção: a mesma mensagem reprocessada, o retry do cliente, o lote
que repete um item.

Em arquivo, e não em memória, porque o gateway pode ser reiniciado (e porque
biblioteca embutida em processo curto perderia o cache toda vez).
"""
import hashlib
import json
import time
from pathlib import Path


def impressao(pedido: dict) -> str:
    """Identidade do pedido. Ordena chaves para não depender da ordem do JSON."""
    bruto = json.dumps(pedido, ensure_ascii=False, sort_keys=True, allow_nan=False)
    return hashlib.sha256(bruto.encode()).hexdigest()


def _arquivo(dados: Path, chave: str) -> Path:
    pasta = Path(dados)/'cache'
    pasta.mkdir(parents=True, exist_ok=True)
    return pasta/f'{chave}.json'


def buscar(dados: Path, chave: str, ttl: float):
    if ttl <= 0:
        return None
    arq = _arquivo(dados, chave)
    try:
        if time.time() - arq.stat().st_mtime > ttl:
            return None
        return json.loads(arq.read_text(encoding='utf-8'))
    except (OSError, json.JSONDecodeError):
        return None


def guardar(dados: Path, chave: str, resposta: dict):
    try:
        arq = _arquivo(dados, chave)
        tmp = arq.with_suffix('.tmp')
        tmp.write_text(json.dumps(resposta, ensure_ascii=False, allow_nan=False), encoding='utf-8')
        tmp.replace(arq)   # troca atômica: ninguém lê um arquivo pela metade
        return True
    except (OSError, ValueError, TypeError):
        return False


def limpar(dados: Path, ttl: float = 0):
    """Remove entradas vencidas (ttl>0) ou todas (ttl=0). Devolve quantas saíram."""
    pasta = Path(dados)/'cache'
    if not pasta.is_dir():
        return 0
    agora, saíram = time.time(), 0
    for arq in pasta.glob('*.json'):
        try:
            if ttl <= 0 or agora - arq.stat().st_mtime > ttl:
                arq.unlink()
                saíram += 1
        except OSError:
            continue
    return saíram
