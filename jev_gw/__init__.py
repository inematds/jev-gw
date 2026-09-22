"""jev-gw — gateway de decisão para o Jev.

Porta única para toda consulta ao Jev de um sistema: valida o pedido, respeita um
teto de gasto, aproveita cache, aplica a política de abstenção e registra custo e
latência. Quando algo falha, devolve revisão humana em vez de quebrar quem chamou.

Uso como biblioteca (o jeito de embutir num sistema Python):

    from jev_gw import decidir

    saida = decidir(pedido)
    if saida['acao'] == 'suggest':
        aplicar(saida['resposta']['answers'])
    else:
        fila_de_revisao(saida['motivo'])

Uso como serviço (para sistemas em outras linguagens):

    python3 -m jev_gw servir      # POST http://127.0.0.1:8770/decidir

Só biblioteca padrão do Python 3.10+. Nenhuma dependência para instalar.
"""
from .nucleo import PedidoInvalido, decidir, saude

__all__ = ['decidir', 'saude', 'PedidoInvalido', '__version__']
__version__ = '1.0.0'
