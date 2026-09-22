"""O caminho de uma decisão: validação → orçamento → cache → Jev → política → registro.

Esta é a única porta. Servidor HTTP e CLI são cascas em cima de `decidir()`.

Contrato de falha, que é o ponto do gateway: **`decidir()` não levanta exceção por
falha de infraestrutura**. Jev fora do ar, chave ausente, teto estourado, resposta
inválida — tudo devolve `acao='review'` com o motivo. O sistema que chamou segue o
seu caminho normal (revisão humana, regra antiga, fila) em vez de quebrar.

A única exceção que sai daqui é `PedidoInvalido`: erro de programação no pedido,
que precisa aparecer no desenvolvimento e não pode ser mascarado como "revise".
"""
import time

from . import cache as _cache
from . import config as _config
from . import orcamento as _orcamento
from . import registro as _registro
from .vendor.jev_core import LabError, evaluate, policy, validate_request, validate_response


class PedidoInvalido(ValueError):
    """O pedido não respeita o contrato do Jev (perguntas, tipos, tamanho)."""


def _resultado(acao, motivo, *, origem, resposta=None, decisoes=None, custo=0.0, latencia=0.0, impressao=None):
    return {
        'acao': acao,                 # 'suggest' | 'review'
        'motivo': motivo,
        'origem': origem,             # 'api' | 'cache' | 'controlado' | 'bloqueado' | 'erro'
        'resposta': resposta,         # resposta crua do Jev (ou None)
        'decisoes': decisoes or {},   # política por pergunta
        'custo_usd': round(float(custo or 0), 8),
        'latencia_ms': round(float(latencia or 0), 1),
        'impressao': impressao,
    }


def _custo_de(resposta):
    uso = (resposta or {}).get('usage') or {}
    return float(uso.get('cost') or 0)


def decidir(pedido, *, sensivel=False, limiar=0.9, probabilidade=0.9,
            avaliador=None, conf=None, usar_cache=True, gravar=True):
    """Consulta o Jev por trás do gateway e devolve a decisão já com política aplicada.

    pedido      dict no formato da API do Jev (model, state, questions)
    sensivel    True força revisão humana em todas as perguntas (domínio supervisionado)
    limiar      confiança mínima para virar sugestão (padrão 0.9)
    avaliador   substitui a chamada real — é assim que se testa sem gastar crédito
    conf        dict de configuração; o padrão vem do ambiente (jev_gw.config)
    """
    conf = conf or _config.carregar()
    dados = conf['dados']

    try:
        validate_request(pedido)
    except LabError as erro:
        raise PedidoInvalido(str(erro)) from None

    chave = _cache.impressao(pedido)
    controlado = avaliador is not None

    # 1. cache — antes do orçamento: resposta repetida não custa e não deve ser barrada
    if usar_cache and not controlado:
        guardado = _cache.buscar(dados, chave, conf['ttl_cache'])
        if guardado is not None:
            saida = _aplicar_politica(pedido, guardado, sensivel, limiar, probabilidade,
                                      origem='cache', custo=0.0, latencia=0.0, impressao=chave)
            if gravar:
                _registrar(dados, pedido, saida, ok=True)
            return saida

    # 2. orçamento — só para consulta real
    if not controlado:
        permitido, motivo, _ = _orcamento.avaliar(dados, conf['teto_diario'])
        if not permitido:
            saida = _resultado('review', motivo, origem='bloqueado', impressao=chave)
            if gravar:
                _registrar(dados, pedido, saida, ok=False)
            return saida

    # 3. consulta
    inicio = time.monotonic()
    try:
        if controlado:
            bruta = avaliador(pedido)
            validate_response(pedido, bruta)
        else:
            bruta = evaluate(pedido, timeout=conf['timeout'], provider=conf['provedor'])
    except LabError as erro:
        latencia = (time.monotonic()-inicio)*1000
        saida = _resultado('review', str(erro), origem='erro', latencia=latencia, impressao=chave)
        if gravar:
            _registrar(dados, pedido, saida, ok=False)
        return saida
    except Exception as erro:  # provedor exótico, avaliador do usuário com bug: ainda assim não derruba
        latencia = (time.monotonic()-inicio)*1000
        saida = _resultado('review', f'Falha inesperada na consulta: {erro}', origem='erro',
                           latencia=latencia, impressao=chave)
        if gravar:
            _registrar(dados, pedido, saida, ok=False)
        return saida
    latencia = (time.monotonic()-inicio)*1000

    if usar_cache and not controlado:
        _cache.guardar(dados, chave, bruta)

    saida = _aplicar_politica(pedido, bruta, sensivel, limiar, probabilidade,
                              origem='controlado' if controlado else 'api',
                              custo=_custo_de(bruta), latencia=latencia, impressao=chave)
    if gravar:
        _registrar(dados, pedido, saida, ok=True)
    return saida


def _aplicar_politica(pedido, bruta, sensivel, limiar, probabilidade, *, origem, custo, latencia, impressao):
    decisoes = {
        nome: policy(resposta, threshold=limiar, probability=probabilidade, sensitive=sensivel)
        for nome, resposta in bruta['answers'].items()
    }
    revisar = [n for n, d in decisoes.items() if d['action'] == 'review']
    acao = 'review' if revisar else 'suggest'
    motivo = (f'Revisão em: {", ".join(sorted(revisar))}.' if revisar
              else 'Sugestão em observação. Nenhuma ação externa executada.')
    return _resultado(acao, motivo, origem=origem, resposta=bruta, decisoes=decisoes,
                      custo=custo, latencia=latencia, impressao=impressao)


def _registrar(dados, pedido, saida, *, ok):
    _registro.gravar(dados, {
        'impressao': saida['impressao'],
        'modelo': (saida.get('resposta') or {}).get('model') or pedido.get('model'),
        'perguntas': sorted(pedido.get('questions', {})),
        'acao': saida['acao'],
        'origem': saida['origem'],
        'custo_usd': saida['custo_usd'],
        'latencia_ms': saida['latencia_ms'],
        'ok': ok,
        'motivo': saida['motivo'] if not ok or saida['acao'] == 'review' else '',
    })


def saude(conf=None):
    """Estado do gateway sem gastar nada: dá para responder antes de qualquer consulta."""
    conf = conf or _config.carregar()
    permitido, motivo, gasto = _orcamento.avaliar(conf['dados'], conf['teto_diario'])
    return {
        'ok': permitido,
        'motivo': motivo or 'Dentro do teto.',
        'teto_diario_usd': conf['teto_diario'],
        'gasto_hoje_usd': gasto,
        'ttl_cache_s': conf['ttl_cache'],
        'timeout_s': conf['timeout'],
        'provedor': conf['provedor'] or 'typesafe (padrão)',
        'dados': str(conf['dados']),
    }
