#!/usr/bin/env python3
"""Sistema Python: importa o gateway e decide. Nenhum servidor no meio.

Este é o caso mais comum de incorporação. Rode sem chave nenhuma:
    python3 exemplos/01-biblioteca.py
Com a chave configurada, troque `avaliador=simulado` por nada e vira consulta real.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from jev_gw import decidir

PEDIDO = {
    'model': 'jev-1.13.0',
    'state': 'Mensagem do cliente: "comprei ontem e quero devolver, ainda nem abri a caixa".',
    'questions': {
        'fila': {
            'type': 'choice',
            'instructions': 'Para qual fila encaminhar esta mensagem?',
            'criteria': {
                'reembolso': 'Pedido de devolução ou estorno',
                'suporte': 'Dúvida de uso ou defeito',
                'insuficiente': 'Não dá para decidir com o que está escrito',
            },
        },
    },
}

def simulado(pedido):
    """Resposta fixa, para o exemplo rodar sem crédito."""
    return {
        'model': 'jev-1.13.0',
        'answers': {'fila': {'type': 'choice', 'choice': 'reembolso', 'confidence': 0.97,
                             'probabilities': {'reembolso': 0.96, 'suporte': 0.02, 'insuficiente': 0.02}}},
        'usage': {'input_tokens': 132, 'output_tokens': 9, 'cost': 0.000071},
    }

saida = decidir(PEDIDO, avaliador=simulado)

# O padrão de uso: só age quando o gateway sugere; caso contrário, o fluxo humano.
if saida['acao'] == 'suggest':
    escolha = saida['resposta']['answers']['fila']['choice']
    print(f'→ encaminhar para a fila: {escolha}')
else:
    print(f'→ revisão humana: {saida["motivo"]}')

print(f'   custo US$ {saida["custo_usd"]:.6f} · {saida["latencia_ms"]:.0f} ms · origem {saida["origem"]}')
