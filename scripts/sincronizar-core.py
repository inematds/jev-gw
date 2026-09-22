#!/usr/bin/env python3
"""Revendoriza jev_lab/core.py (do repo inematds/jev) em jev_gw/vendor/jev_core.py.

Por que existe: jev-gw não importa o repo vizinho — ele carrega uma cópia, para
rodar sozinho em qualquer máquina. Este script faz a cópia de forma auditável:
grava o sha256 da origem no cabeçalho e mostra o que mudou antes de escrever.

Uso:
  python3 scripts/sincronizar-core.py --conferir        # só diz se está desatualizado
  python3 scripts/sincronizar-core.py                   # atualiza
  python3 scripts/sincronizar-core.py --origem /caminho/core.py
"""
import argparse
import difflib
import hashlib
import re
import sys
from datetime import date
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
DESTINO = RAIZ/'jev_gw/vendor/jev_core.py'
ORIGEM_PADRAO = Path.home()/'projetos/jev/jev_lab/core.py'

CABECALHO = '''"""Cópia vendorizada de jev_lab/core.py (Jev Decision Lab, github.com/inematds/jev).

NÃO EDITE À MÃO. Ressincronize com:  python3 scripts/sincronizar-core.py

origem:  {origem}
sha256:  {sha}
data:    {data}

Por que vendorizar em vez de importar: jev-gw é um serviço que roda sozinho, às
vezes em outra máquina, e não pode depender de um repo irmão estar no disco na
versão certa. O script de sincronização mostra o diff e atualiza o hash acima.

Única alteração aplicada na cópia: `from . import __version__` vira uma constante,
porque aqui não existe o pacote jev_lab em volta.
"""
'''


def adaptar(texto: str) -> str:
    """Corta o acoplamento com o pacote de origem, sem tocar na lógica."""
    novo, n = re.subn(r'^from \. import __version__$',
                      "__version__ = 'vendorizado-em-jev-gw'",
                      texto, count=1, flags=re.M)
    if not n:
        print('aviso: o import de __version__ não foi encontrado — confira se o core mudou.', file=sys.stderr)
    return novo


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--origem', type=Path, default=ORIGEM_PADRAO)
    p.add_argument('--conferir', action='store_true', help='não escreve; sai 1 se estiver desatualizado')
    a = p.parse_args()

    if not a.origem.is_file():
        sys.exit(f'não achei a origem: {a.origem}\nClone github.com/inematds/jev ao lado, ou passe --origem.')

    bruto = a.origem.read_text(encoding='utf-8')
    sha = hashlib.sha256(bruto.encode()).hexdigest()
    novo = CABECALHO.format(origem=a.origem, sha=sha, data=date.today().isoformat()) + adaptar(bruto)

    atual = DESTINO.read_text(encoding='utf-8') if DESTINO.is_file() else ''
    sha_atual = re.search(r'^sha256:\s+([0-9a-f]{64})$', atual, re.M)
    if sha_atual and sha_atual[1] == sha:
        print('já está sincronizado com a origem.')
        return 0

    corpo_atual = atual.split('"""', 2)[-1] if atual else ''
    corpo_novo = novo.split('"""', 2)[-1]
    diff = list(difflib.unified_diff(corpo_atual.splitlines(), corpo_novo.splitlines(),
                                     'vendorizado', 'origem', lineterm='', n=1))
    print(f'origem mudou ({len(diff)} linhas de diff).')
    print('\n'.join(diff[:60]) or '(sem diferença no corpo; só metadados)')

    if a.conferir:
        print('\n--conferir: nada foi escrito.')
        return 1

    DESTINO.write_text(novo, encoding='utf-8')
    print(f'\natualizado: {DESTINO}  sha256 {sha[:16]}…')
    print('rode os testes: python3 -m unittest discover -s testes')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
