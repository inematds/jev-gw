"""Registro de chamadas em JSONL + agregados do dia.

Uma linha por consulta, append-only. É o que permite responder três perguntas
sem instrumentar nada no sistema que chamou: quanto gastei hoje, o que foi
para revisão, e o que o Jev respondeu naquele pedido específico.
"""
import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path

_TRAVA = threading.Lock()


def _hoje():
    return datetime.now(timezone.utc).strftime('%Y-%m-%d')


def caminho(dados: Path, dia=None):
    return Path(dados)/f'registro-{dia or _hoje()}.jsonl'


def gravar(dados: Path, evento: dict):
    """Acrescenta um evento. Nunca levanta exceção para o chamador.

    Um gateway que quebra a aplicação porque não conseguiu escrever log é pior
    que um gateway sem log. Falha de escrita vira campo no retorno, não erro.
    """
    linha = dict(evento, momento=datetime.now(timezone.utc).isoformat(timespec='seconds'))
    try:
        with _TRAVA:
            with open(caminho(dados), 'a', encoding='utf-8') as arq:
                arq.write(json.dumps(linha, ensure_ascii=False, allow_nan=False)+'\n')
                arq.flush()
                os.fsync(arq.fileno())
        return True
    except (OSError, ValueError, TypeError):
        return False


def ler(dados: Path, dia=None):
    arq = caminho(dados, dia)
    if not arq.is_file():
        return []
    eventos = []
    for linha in arq.read_text(encoding='utf-8', errors='replace').splitlines():
        linha = linha.strip()
        if not linha:
            continue
        try:
            eventos.append(json.loads(linha))
        except json.JSONDecodeError:
            continue  # linha truncada por queda no meio da escrita: ignora, não derruba o relatório
    return eventos


def resumo(dados: Path, dia=None):
    eventos = ler(dados, dia)
    gasto = sum(float(e.get('custo_usd') or 0) for e in eventos)
    latencias = sorted(float(e['latencia_ms']) for e in eventos if isinstance(e.get('latencia_ms'), (int, float)))
    def _p(q):
        if not latencias:
            return 0.0
        return round(latencias[min(int(q*len(latencias)), len(latencias)-1)], 1)
    return {
        'dia': dia or _hoje(),
        'chamadas': len(eventos),
        'consultas_reais': sum(1 for e in eventos if e.get('origem') == 'api'),
        'cache': sum(1 for e in eventos if e.get('origem') == 'cache'),
        'erros': sum(1 for e in eventos if not e.get('ok')),
        'revisao': sum(1 for e in eventos if e.get('acao') == 'review'),
        'sugestao': sum(1 for e in eventos if e.get('acao') == 'suggest'),
        'gasto_usd': round(gasto, 6),
        'latencia_ms_p50': _p(.5),
        'latencia_ms_p95': _p(.95),
    }
