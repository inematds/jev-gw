"""CLI: python3 -m jev_gw <comando>

  servir      sobe o gateway HTTP (padrão 127.0.0.1:8770)
  decidir     manda um pedido JSON (arquivo ou stdin) e imprime a decisão
  saude       estado, teto e gasto do dia
  custo       resumo do dia (--dia AAAA-MM-DD)
  cache       --limpar [--vencidos]
"""
import argparse
import json
import sys

from . import cache as _cache
from . import config as _config
from . import nucleo as _nucleo
from . import registro as _registro
from . import servidor as _servidor


def _pedido(origem):
    bruto = sys.stdin.read() if origem in (None, '-') else open(origem, encoding='utf-8').read()
    try:
        return json.loads(bruto)
    except json.JSONDecodeError as erro:
        sys.exit(f'JSON inválido: {erro}')


def main(argv=None):
    p = argparse.ArgumentParser(prog='jev-gw', description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest='cmd', required=True)

    s = sub.add_parser('servir', help='sobe o gateway HTTP')
    s.add_argument('--porta', type=int)
    s.add_argument('--host')

    d = sub.add_parser('decidir', help='consulta o Jev pelo gateway')
    d.add_argument('arquivo', nargs='?', help='pedido JSON (padrão: stdin)')
    d.add_argument('--sensivel', action='store_true', help='domínio supervisionado: sempre revisão')
    d.add_argument('--limiar', type=float, default=0.9)
    d.add_argument('--sem-cache', action='store_true')

    sub.add_parser('saude', help='estado do gateway, sem gastar nada')

    c = sub.add_parser('custo', help='resumo do dia')
    c.add_argument('--dia', help='AAAA-MM-DD (padrão: hoje, UTC)')

    k = sub.add_parser('cache', help='manutenção do cache')
    k.add_argument('--limpar', action='store_true')
    k.add_argument('--vencidos', action='store_true', help='só os que passaram do TTL')

    a = p.parse_args(argv)
    conf = _config.carregar()

    if a.cmd == 'servir':
        srv = _servidor.servir(conf, a.porta, a.host)
        host, porta = srv.server_address[0], srv.server_address[1]
        print(f'jev-gw ouvindo em http://{host}:{porta}  (painel em /painel, Ctrl+C para parar)')
        print(f'teto diário US$ {conf["teto_diario"]:.2f} · cache {conf["ttl_cache"]:.0f}s · dados em {conf["dados"]}')
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            print('\nencerrando.')
        finally:
            srv.server_close()
        return 0

    if a.cmd == 'decidir':
        try:
            saida = _nucleo.decidir(_pedido(a.arquivo), sensivel=a.sensivel, limiar=a.limiar,
                                    usar_cache=not a.sem_cache, conf=conf)
        except _nucleo.PedidoInvalido as erro:
            sys.exit(f'Pedido inválido: {erro}')
        print(json.dumps(saida, ensure_ascii=False, indent=2))
        return 0 if saida['acao'] == 'suggest' else 2   # 2 = precisa de revisão humana

    if a.cmd == 'saude':
        print(json.dumps(_nucleo.saude(conf), ensure_ascii=False, indent=2))
        return 0

    if a.cmd == 'custo':
        print(json.dumps(_registro.resumo(conf['dados'], a.dia), ensure_ascii=False, indent=2))
        return 0

    if a.cmd == 'cache':
        if not a.limpar:
            sys.exit('Use --limpar (opcionalmente com --vencidos).')
        saíram = _cache.limpar(conf['dados'], conf['ttl_cache'] if a.vencidos else 0)
        print(f'{saíram} entrada(s) removida(s).')
        return 0

    return 1


if __name__ == '__main__':
    raise SystemExit(main())
