# 🚪 jev-gw — decision gateway for Jev

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![jev-gw](guia/assets/banner.jpg)](https://inematds.github.io/jev-gw/guia/en/)

## 📖 User guide

Complete guide (landing page + step-by-step instructions): **https://inematds.github.io/jev-gw/guia/en/**

A single entry point for every system request to [Jev](https://docs.typesafe.ai/introduction):
validates the request, enforces a **daily spending limit**, uses **cache**, applies the **abstention
policy**, and **records the cost and latency** of each call.

Most importantly: **when something fails, it returns a request for human review instead of breaking the caller.**
Jev is down, the key is wrong, a timeout occurs, the limit is exceeded — your system stays up.

Only the Python 3.10+ standard library. **Nothing to install.**

> **How it works under the hood: [ARQUITETURA.md](ARQUITETURA.md)** — the path of a decision,
> why the steps are ordered this way, the failure contract, and what the gateway does not do.

## Integrate into your system

**Python — import and use.** No extra process, no port.

```python
from jev_gw import decidir

saida = decidir({
    'model': 'jev-1.13.0',
    'state': 'Customer message: I bought it yesterday and want to return it, but I haven’t even opened the box.',
    'questions': {
        'fila': {
            'type': 'choice',
            'instructions': 'Which queue should this message be routed to?',
            'criteria': {
                'reembolso': 'Return or refund request',
                'suporte': 'Usage question or defect',
                'insuficiente': 'There is not enough information to decide',
            },
        },
    },
})

if saida['acao'] == 'suggest':
    encaminhar(saida['resposta']['answers']['fila']['choice'])
else:
    fila_de_revisao(saida['motivo'])       # includes "Jev went down" — and that's OK
```

**Any other language — a POST.**

```bash
python3 -m jev_gw servir          # 127.0.0.1:8770
curl -X POST localhost:8770/decidir -H 'content-type: application/json' -d @pedido.json
```

**Terminal, cron, pipeline.** Exit code `0` = suggestion, `2` = needs review.

```bash
python3 -m jev_gw decidir pedido.json
```

Runnable examples, one for each method: [`exemplos/`](exemplos/) (Python, `curl`, Node — all with
no dependencies).

## Install

```bash
git clone https://github.com/inematds/jev-gw.git
cd jev-gw
python3 -m unittest discover -s testes     # 23 tests, none use credits
```

To use it from another project, point `PYTHONPATH` to the folder, or copy the
`jev_gw/` directory into your project — it is self-contained by design.

The key is only needed for the first real request:

```bash
export TYPESAFE_API_KEY=...        # or OPENROUTER_API_KEY + JEV_PROVIDER=openrouter
```

## What you get

| | |
|---|---|
| **Spending limit** | `JEV_GW_TETO_DIARIO=1.00`. Once exceeded, requests go to review — no more queries |
| **Cache** | identical requests within 15 min do not incur another charge (measured: 610 ms → 0 ms, US$ 0) |
| **Conservative failure handling** | no infrastructure failure is raised to you as an exception |
| **Logging** | JSONL with cost, latency, and decision for each call |
| **Dashboard** | `http://127.0.0.1:8770/painel` — today's spending, latency, latest calls |
| **Privacy** | `state` (your data) is **not** sent to the log. Listens only on `127.0.0.1` |

## Commands

```bash
python3 -m jev_gw servir                  # starts the service + dashboard
python3 -m jev_gw decidir pedido.json     # one decision
python3 -m jev_gw saude                   # status and limit, no spending
python3 -m jev_gw custo --dia 2026-09-22  # daily summary
python3 -m jev_gw cache --limpar          # maintenance
```

## Tested in practice (09/22/2026)

- **23 tests** passing, all with a controlled evaluator — the suite does not spend a cent.
- **Real call to Jev** through OpenRouter: decision `reembolso`, confidence 1.0, **610 ms**,
  **US$ 0.0000155**. The second identical call came from cache: **0 ms, US$ 0**.
  Evidence: [`reports/smoke-2026-09-22.jsonl`](reports/smoke-2026-09-22.jsonl).
- This is an integration and contract test — **not a decision quality benchmark**.

## What this gateway is not

**It is not a code agent proxy.** It does not sit between your Codex/Claude Code and the model.
For that, there is [jev-gateway](https://github.com/vinilana/jev-gateway) (an
independent TypeScript project), which complements this one.

**It does not execute actions.** It returns a suggestion; your system applies it, with its own permissions.

Full list in [ARQUITETURA.md, section 6](ARQUITETURA.md#6-o-que-este-gateway-não-faz).

## Related

- [Jev Decision Lab](https://github.com/inematds/jev) — the lab: 20 cases, 17 packages,
  experiments, and metrics. The Jev client used here (vendored) comes from there.
- [Jev & Laya Course](https://inematds.github.io/jev-curso/) — structured decisions in practice.
- [Jev Collection at Eventos INEMA](https://eventos.inema.pro/jev/).

## License

MIT. The vendored client (`jev_gw/vendor/jev_core.py`) comes from Jev Decision Lab, also INEMA.
"jev" is TypeSafe's model; this project is a client for its public API, with no affiliation.
