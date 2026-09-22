# FALHAS — jev-gw

| data | o que quebrou | menor correção | prompt \| infra |
|---|---|---|---|
| 2026-09-22 | teste de TTL do cache falhava por corrida (escrevia e lia no mesmo instante, com ttl=0.0001s) | envelhecer o arquivo com `os.utime` em vez de depender do relógio | prompt |
| 2026-09-22 | `core.py` vendorizado quebrou no import (`from . import __version__` não existe fora do pacote jev_lab) | o script de sincronização troca essa linha por uma constante | prompt |
