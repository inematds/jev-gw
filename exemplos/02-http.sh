#!/usr/bin/env bash
# Sistema em qualquer linguagem: fala HTTP com o gateway.
#   terminal 1:  python3 -m jev_gw servir
#   terminal 2:  bash exemplos/02-http.sh
set -euo pipefail
GW="${JEV_GW_URL:-http://127.0.0.1:8770}"

echo "== estado do gateway (não gasta nada)"
curl -s "$GW/saude" | python3 -m json.tool

echo; echo "== uma decisão"
curl -s -X POST "$GW/decidir" -H 'content-type: application/json' -d '{
  "model": "jev-1.13.0",
  "state": "Mensagem do cliente: comprei ontem e quero devolver, nem abri a caixa.",
  "questions": {
    "fila": {
      "type": "choice",
      "instructions": "Para qual fila encaminhar esta mensagem?",
      "criteria": {
        "reembolso": "Pedido de devolução ou estorno",
        "suporte": "Dúvida de uso ou defeito",
        "insuficiente": "Não dá para decidir com o que está escrito"
      }
    }
  }
}' | python3 -m json.tool

echo; echo "== quanto gastei hoje"
curl -s "$GW/custo" | python3 -m json.tool
