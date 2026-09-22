# FALHAS — jev-gw

| data | o que quebrou | menor correção | prompt \| infra |
|---|---|---|---|
| 2026-09-22 | push do portal, inemabuscas e inemapro-mono rejeitado (outra sessão publicou no meio) — rebase deu conflito em arquivos GERADOS | resolver os gerados pelo lado de cima e REGENERAR (`gen:data`, `build.mjs`, `gen-catalog`), nunca editar o conflito à mão | infra |
| 2026-09-22 | `git push origin` no inemabuscas foi pro repo errado: ali `origin` = inematds/INEMAPRO; o upstream real é o remote `inemabuscas` | conferir `git rev-parse --abbrev-ref main@{upstream}` antes de empurrar (lição já registrada no wifi/CLAUDE.md) | prompt |
| 2026-09-22 | teste de TTL do cache falhava por corrida (escrevia e lia no mesmo instante, com ttl=0.0001s) | envelhecer o arquivo com `os.utime` em vez de depender do relógio | prompt |
| 2026-09-22 | `core.py` vendorizado quebrou no import (`from . import __version__` não existe fora do pacote jev_lab) | o script de sincronização troca essa linha por uma constante | prompt |
