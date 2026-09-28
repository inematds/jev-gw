# 🚪 jev-gw — gateway de decisión para Jev

**🇧🇷 [Português](README.md) · 🇺🇸 [English](README.en.md) · 🇪🇸 [Español](README.es.md)**

[![jev-gw](guia/assets/banner.jpg)](https://inematds.github.io/jev-gw/guia/es/)

## 📖 Guía de uso

Guía completa (landing + paso a paso): **https://inematds.github.io/jev-gw/guia/es/**

Punto de acceso único para todas las consultas de un sistema a [Jev](https://docs.typesafe.ai/introduction):
valida la solicitud, respeta un **límite de gasto diario**, aprovecha la **caché**, aplica la **política
de abstención** y **registra el costo y la latencia** de cada llamada.

Y lo más importante: **cuando algo falla, devuelve una solicitud de revisión humana en lugar de dejar fuera de servicio al sistema que lo llamó.**
Jev fuera de servicio, clave incorrecta, timeout, límite excedido: tu sistema sigue funcionando.

Solo usa la biblioteca estándar de Python 3.10+. **No hay nada que instalar.**

> **Cómo funciona internamente: [ARQUITETURA.md](ARQUITETURA.md)** — el recorrido de una decisión,
> por qué este es el orden de las etapas, el contrato de fallos y lo que el gateway no hace.

## Incorpóralo a tu sistema

**Python: importa y usa.** Sin proceso adicional ni puerto.

```python
from jev_gw import decidir

saida = decidir({
    'model': 'jev-1.13.0',
    'state': 'Mensaje del cliente: compré ayer y quiero devolverlo, ni siquiera abrí la caja.',
    'questions': {
        'fila': {
            'type': 'choice',
            'instructions': '¿A qué cola debe enviarse este mensaje?',
            'criteria': {
                'reembolso': 'Solicitud de devolución o reembolso',
                'suporte': 'Duda sobre el uso o defecto',
                'insuficiente': 'No se puede decidir con lo que está escrito',
            },
        },
    },
})

if saida['acao'] == 'suggest':
    encaminhar(saida['resposta']['answers']['fila']['choice'])
else:
    fila_de_revisao(saida['motivo'])       # incluye "Jev dejó de funcionar", y no pasa nada
```

**Cualquier otro lenguaje: un POST.**

```bash
python3 -m jev_gw servir          # 127.0.0.1:8770
curl -X POST localhost:8770/decidir -H 'content-type: application/json' -d @pedido.json
```

**Terminal, cron, pipeline.** Salida `0` = sugerencia, `2` = requiere revisión.

```bash
python3 -m jev_gw decidir pedido.json
```

Ejemplos en funcionamiento, uno por modalidad: [`exemplos/`](exemplos/) (Python, `curl`, Node; todos sin
dependencias).

## Instalar

```bash
git clone https://github.com/inematds/jev-gw.git
cd jev-gw
python3 -m unittest discover -s testes     # 23 pruebas, ninguna consume créditos
```

Para usarlo desde otro proyecto, apunta `PYTHONPATH` a la carpeta o copia el directorio
`jev_gw/` dentro de tu proyecto: está autocontenido a propósito.

La clave solo es necesaria para la primera consulta real:

```bash
export TYPESAFE_API_KEY=...        # o OPENROUTER_API_KEY + JEV_PROVIDER=openrouter
```

## Qué obtienes

| | |
|---|---|
| **Límite de gasto** | `JEV_GW_TETO_DIARIO=1.00`. Si se excede, pasa a revisión; no consulta más |
| **Caché** | una solicitud idéntica dentro de 15 min no vuelve a generar gastos (medido: 610 ms → 0 ms, US$ 0) |
| **Fallos conservadores** | ningún fallo de infraestructura se convierte en una excepción para ti |
| **Registro** | JSONL con costo, latencia y decisión por llamada |
| **Panel** | `http://127.0.0.1:8770/painel` — gasto del día, latencia, últimas llamadas |
| **Privacidad** | `state` (tus datos) **no** se incluye en el registro. Solo escucha en `127.0.0.1` |

## Comandos

```bash
python3 -m jev_gw servir                  # inicia el servicio + panel
python3 -m jev_gw decidir pedido.json     # una decisión
python3 -m jev_gw saude                   # estado y límite, sin gastar nada
python3 -m jev_gw custo --dia 2026-09-22  # resumen del día
python3 -m jev_gw cache --limpar          # mantenimiento
```

## Probado de verdad (22/09/2026)

- **23 pruebas** aprobadas, todas con un evaluador controlado; la suite no gasta ni un centavo.
- **Llamada real a Jev** a través de OpenRouter: decisión `reembolso`, confianza 1,0, **610 ms**,
  **US$ 0,0000155**. La segunda llamada idéntica se obtuvo de la caché: **0 ms, US$ 0**.
  Evidencia: [`reports/smoke-2026-09-22.jsonl`](reports/smoke-2026-09-22.jsonl).
- Esto es una prueba de integración y de contrato; **no es un benchmark de calidad de decisión**.

## Qué no es este gateway

**No es un proxy de agentes de código.** No se interpone entre tu Codex/Claude Code y el modelo.
Para eso existe [jev-gateway](https://github.com/vinilana/jev-gateway) (proyecto
independiente, en TypeScript), que es complementario a este.

**No ejecuta acciones.** Devuelve sugerencias; quien las aplica es tu sistema, con sus permisos.

Lista completa en [ARQUITETURA.md, sección 6](ARQUITETURA.md#6-o-que-este-gateway-não-faz).

## Relacionados

- [Jev Decision Lab](https://github.com/inematds/jev) — el laboratorio: 20 casos, 17 paquetes,
  experimentos y métricas. De ahí proviene el cliente Jev que se usa aquí (vendorizado).
- [Curso Jev & Laya](https://inematds.github.io/jev-curso/) — decisiones estructuradas en la práctica.
- [Acervo Jev no Eventos INEMA](https://eventos.inema.pro/jev/).

## Licencia

MIT. El cliente vendorizado (`jev_gw/vendor/jev_core.py`) proviene de Jev Decision Lab, también de INEMA.
"jev" es el modelo de TypeSafe; este proyecto es un cliente de su API pública, sin afiliación.
