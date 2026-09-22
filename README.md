# 🚪 jev-gw — gateway de decisão para o Jev

[![jev-gw](guia/assets/banner.jpg)](https://inematds.github.io/jev-gw/guia/)

## 📖 Guia de uso

Guia completo (landing + passo a passo): **https://inematds.github.io/jev-gw/guia/**

Porta única para toda consulta ao [Jev](https://docs.typesafe.ai/introduction) de um sistema:
valida o pedido, respeita um **teto de gasto diário**, aproveita **cache**, aplica a **política
de abstenção** e **registra custo e latência** de cada chamada.

E o principal: **quando algo falha, devolve revisão humana em vez de quebrar quem chamou.**
Jev fora do ar, chave errada, timeout, teto estourado — o seu sistema continua de pé.

Só biblioteca padrão do Python 3.10+. **Nada para instalar.**

> **Como funciona por dentro: [ARQUITETURA.md](ARQUITETURA.md)** — o caminho de uma decisão,
> por que a ordem das etapas é essa, o contrato de falha e o que o gateway não faz.

## Incorporar no seu sistema

**Python — importa e usa.** Sem processo extra, sem porta.

```python
from jev_gw import decidir

saida = decidir({
    'model': 'jev-1.13.0',
    'state': 'Mensagem do cliente: comprei ontem e quero devolver, nem abri a caixa.',
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
})

if saida['acao'] == 'suggest':
    encaminhar(saida['resposta']['answers']['fila']['choice'])
else:
    fila_de_revisao(saida['motivo'])       # inclui "o Jev caiu" — e está tudo bem
```

**Qualquer outra linguagem — um POST.**

```bash
python3 -m jev_gw servir          # 127.0.0.1:8770
curl -X POST localhost:8770/decidir -H 'content-type: application/json' -d @pedido.json
```

**Terminal, cron, pipeline.** Saída `0` = sugestão, `2` = precisa de revisão.

```bash
python3 -m jev_gw decidir pedido.json
```

Exemplos rodando, um por forma: [`exemplos/`](exemplos/) (Python, `curl`, Node — todos sem
dependência).

## Instalar

```bash
git clone https://github.com/inematds/jev-gw.git
cd jev-gw
python3 -m unittest discover -s testes     # 23 testes, nenhum gasta crédito
```

Para usar de outro projeto, aponte o `PYTHONPATH` para a pasta, ou copie o diretório
`jev_gw/` para dentro do seu projeto — é autocontido de propósito.

A chave só é necessária na primeira consulta real:

```bash
export TYPESAFE_API_KEY=...        # ou OPENROUTER_API_KEY + JEV_PROVIDER=openrouter
```

## O que você ganha

| | |
|---|---|
| **Teto de gasto** | `JEV_GW_TETO_DIARIO=1.00`. Estourou, vira revisão — não consulta mais |
| **Cache** | pedido idêntico em 15 min não gasta de novo (medido: 610 ms → 0 ms, US$ 0) |
| **Falha conservadora** | nenhuma falha de infraestrutura sobe como exceção para você |
| **Registro** | JSONL com custo, latência e decisão por chamada |
| **Painel** | `http://127.0.0.1:8770/painel` — gasto do dia, latência, últimas chamadas |
| **Privacidade** | o `state` (seus dados) **não** vai para o registro. Escuta só em `127.0.0.1` |

## Comandos

```bash
python3 -m jev_gw servir                  # sobe o serviço + painel
python3 -m jev_gw decidir pedido.json     # uma decisão
python3 -m jev_gw saude                   # estado e teto, sem gastar nada
python3 -m jev_gw custo --dia 2026-09-22  # resumo do dia
python3 -m jev_gw cache --limpar          # manutenção
```

## Testado de verdade (22/09/2026)

- **23 testes** passando, todos com avaliador controlado — a suíte não gasta um centavo.
- **Chamada real ao Jev** pelo OpenRouter: decisão `reembolso`, confiança 1,0, **610 ms**,
  **US$ 0,0000155**. A segunda chamada idêntica veio do cache: **0 ms, US$ 0**.
  Evidência: [`reports/smoke-2026-09-22.jsonl`](reports/smoke-2026-09-22.jsonl).
- Isso é teste de integração e de contrato — **não é benchmark de qualidade de decisão**.

## O que este gateway não é

**Não é proxy de agente de código.** Ele não fica entre o seu Codex/Claude Code e o modelo.
Para isso existe o [jev-gateway](https://github.com/vinilana/jev-gateway) (projeto
independente, TypeScript), que é complementar a este.

**Não executa ações.** Devolve sugestão; quem aplica é o seu sistema, com as permissões dele.

Lista completa em [ARQUITETURA.md, seção 6](ARQUITETURA.md#6-o-que-este-gateway-não-faz).

## Relacionados

- [Jev Decision Lab](https://github.com/inematds/jev) — o laboratório: 20 casos, 17 pacotes,
  experimentos e métricas. É de lá que vem o cliente Jev usado aqui (vendorizado).
- [Curso Jev & Laya](https://inematds.github.io/jev-curso/) — decisões estruturadas na prática.
- [Acervo Jev no Eventos INEMA](https://eventos.inema.pro/jev/).

## Licença

MIT. O cliente vendorizado (`jev_gw/vendor/jev_core.py`) vem do Jev Decision Lab, também INEMA.
"jev" é o modelo da TypeSafe; este projeto é um cliente da API pública dela, sem vínculo.
