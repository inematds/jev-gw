"""Servidor HTTP: a mesma decisão, para quem não é Python.

Só biblioteca padrão (`http.server`). Escuta em 127.0.0.1 por padrão — este
gateway guarda a sua chave do Jev e não deve ficar exposto na rede sem que
alguém decida isso explicitamente (`JEV_GW_HOST=0.0.0.0`).

Rotas:
  POST /decidir   {model, state, questions, sensivel?, limiar?}  → decisão
  GET  /saude     estado, teto e gasto do dia
  GET  /custo     resumo do dia (?dia=AAAA-MM-DD para outro)
  GET  /painel    página única de acompanhamento
"""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlparse, parse_qs

from . import config as _config
from . import nucleo as _nucleo
from . import registro as _registro

LIMITE_CORPO = 200_000   # o Jev já recusa acima de 100 KB; aqui é o dobro, para dar erro claro


class _Manipulador(BaseHTTPRequestHandler):
    server_version = 'jev-gw'
    conf = None

    def _responder(self, codigo, corpo, tipo='application/json; charset=utf-8'):
        dados = corpo if isinstance(corpo, bytes) else json.dumps(corpo, ensure_ascii=False).encode()
        self.send_response(codigo)
        self.send_header('Content-Type', tipo)
        self.send_header('Content-Length', str(len(dados)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(dados)

    def log_message(self, formato, *args):
        pass   # o registro JSONL já é o log; o do http.server só polui o terminal

    def do_GET(self):
        rota = urlparse(self.path)
        consulta = parse_qs(rota.query)
        if rota.path in ('/saude', '/health'):
            return self._responder(200, _nucleo.saude(self.conf))
        if rota.path == '/custo':
            dia = (consulta.get('dia') or [None])[0]
            return self._responder(200, _registro.resumo(self.conf['dados'], dia))
        if rota.path in ('/painel', '/'):
            return self._responder(200, _painel(self.conf).encode(), 'text/html; charset=utf-8')
        return self._responder(404, {'erro': 'Rota desconhecida. Use /decidir, /saude, /custo ou /painel.'})

    def do_POST(self):
        rota = urlparse(self.path)
        if rota.path != '/decidir':
            return self._responder(404, {'erro': 'Rota desconhecida. O POST vai em /decidir.'})
        try:
            tamanho = int(self.headers.get('Content-Length') or 0)
        except ValueError:
            return self._responder(400, {'erro': 'Content-Length inválido.'})
        if tamanho <= 0:
            return self._responder(400, {'erro': 'Corpo vazio. Envie o pedido em JSON.'})
        if tamanho > LIMITE_CORPO:
            return self._responder(413, {'erro': f'Pedido acima de {LIMITE_CORPO} bytes.'})
        try:
            corpo = json.loads(self.rfile.read(tamanho))
        except (json.JSONDecodeError, UnicodeDecodeError):
            return self._responder(400, {'erro': 'JSON inválido.'})
        if not isinstance(corpo, dict):
            return self._responder(400, {'erro': 'O corpo precisa ser um objeto JSON.'})

        opcoes = {
            'sensivel': bool(corpo.pop('sensivel', False)),
            'limiar': float(corpo.pop('limiar', 0.9) or 0.9),
            'probabilidade': float(corpo.pop('probabilidade', 0.9) or 0.9),
            'usar_cache': bool(corpo.pop('cache', True)),
        }
        try:
            saida = _nucleo.decidir(corpo, conf=self.conf, **opcoes)
        except _nucleo.PedidoInvalido as erro:
            # 422: o pedido chegou íntegro mas não respeita o contrato do Jev.
            return self._responder(422, {'erro': str(erro), 'acao': 'review'})
        except ValueError as erro:
            return self._responder(400, {'erro': f'Opção inválida: {erro}', 'acao': 'review'})
        return self._responder(200, saida)


def _painel(conf):
    s = _nucleo.saude(conf)
    r = _registro.resumo(conf['dados'])
    eventos = _registro.ler(conf['dados'])[-25:][::-1]
    linhas = ''.join(
        f"<tr><td>{e.get('momento','')[11:19]}</td><td>{e.get('origem','')}</td>"
        f"<td class='{e.get('acao','')}'>{e.get('acao','')}</td>"
        f"<td>{e.get('latencia_ms',0):.0f} ms</td><td>US$ {e.get('custo_usd',0):.6f}</td>"
        f"<td>{(e.get('motivo') or '')[:80]}</td></tr>" for e in eventos) or \
        "<tr><td colspan='6'>Nenhuma chamada hoje.</td></tr>"
    pct = min(100, (r['gasto_usd']/s['teto_diario_usd']*100) if s['teto_diario_usd'] else 100)
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>jev-gw — painel</title><meta http-equiv="refresh" content="5">
<style>
 body{{margin:0;background:#0c0c10;color:#e9e9ee;font:15px/1.6 system-ui,sans-serif}}
 .w{{max-width:920px;margin:0 auto;padding:28px 20px}}
 h1{{font-size:1.4rem;margin:0 0 4px}} .m{{color:#9a9aa6}}
 .g{{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:22px 0}}
 .c{{background:#16161e;border:1px solid #272730;border-radius:12px;padding:14px}}
 .c b{{display:block;font-size:1.5rem;color:#E2A23B;font-weight:600}}
 .bar{{height:8px;background:#272730;border-radius:99px;overflow:hidden;margin-top:8px}}
 .bar i{{display:block;height:100%;background:#E2A23B;width:{pct:.1f}%}}
 table{{width:100%;border-collapse:collapse;font-size:.88rem}}
 td,th{{text-align:left;padding:7px 8px;border-bottom:1px solid #1e1e26}}
 .review{{color:#f0a06a}} .suggest{{color:#7fd18a}}
 code{{background:#16161e;padding:2px 6px;border-radius:6px}}
</style></head><body><div class="w">
<h1>jev-gw <span class="m">· painel</span></h1>
<p class="m">{s['motivo']} Provedor: {s['provedor']}. Atualiza sozinho a cada 5 s.</p>
<div class="g">
  <div class="c"><b>{r['chamadas']}</b>chamadas hoje</div>
  <div class="c"><b>{r['consultas_reais']}</b>consultas reais</div>
  <div class="c"><b>{r['cache']}</b>vindas do cache</div>
  <div class="c"><b>{r['revisao']}</b>foram para revisão</div>
  <div class="c"><b>{r['latencia_ms_p50']:.0f} ms</b>latência (mediana)</div>
  <div class="c"><b>US$ {r['gasto_usd']:.4f}</b>de US$ {s['teto_diario_usd']:.2f} no dia<div class="bar"><i></i></div></div>
</div>
<table><tr><th>hora</th><th>origem</th><th>ação</th><th>latência</th><th>custo</th><th>motivo</th></tr>{linhas}</table>
<p class="m" style="margin-top:22px">Consulta: <code>POST /decidir</code> · estado: <code>GET /saude</code> · números: <code>GET /custo</code></p>
</div></body></html>"""


def servir(conf=None, porta=None, host=None):
    conf = conf or _config.carregar()
    porta = porta or conf['porta']
    host = host or os.environ.get('JEV_GW_HOST', '127.0.0.1')
    _Manipulador.conf = conf
    servidor = ThreadingHTTPServer((host, porta), _Manipulador)
    servidor.daemon_threads = True
    return servidor
