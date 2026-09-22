"""Teto de gasto diário, conferido ANTES de cada consulta real.

O custo do Jev por chamada é pequeno; o risco é volume em laço. Por isso o teto
é diário e é verificado antes de sair a chamada, não depois. Quando o teto estoura,
o gateway não falha: devolve `review` (revisão humana), que é a saída conservadora.

O estado vem do próprio registro do dia — não existe contador separado para
dessincronizar. Custa uma leitura de arquivo por consulta; num gateway que faz
dezenas de chamadas por minuto isso é irrelevante perto da latência de rede.
"""
from . import registro


class Estouro(Exception):
    """Teto diário atingido. O chamador recebe revisão, não erro."""


def gasto_do_dia(dados):
    return registro.resumo(dados)['gasto_usd']


def avaliar(dados, teto_diario):
    """Devolve (permitido, motivo, gasto_atual)."""
    if teto_diario <= 0:
        return False, 'Teto diário zerado: o gateway está em modo desligado.', 0.0
    gasto = gasto_do_dia(dados)
    if gasto >= teto_diario:
        return False, f'Teto diário de US$ {teto_diario:.2f} atingido (gasto US$ {gasto:.6f}).', gasto
    return True, '', gasto
