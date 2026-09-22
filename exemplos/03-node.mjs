// Sistema em Node: o gateway é só um POST. Nenhuma dependência.
//   python3 -m jev_gw servir     (em outro terminal)
//   node exemplos/03-node.mjs
const GW = process.env.JEV_GW_URL ?? 'http://127.0.0.1:8770'

export async function decidir (pedido, opcoes = {}) {
  const resposta = await fetch(`${GW}/decidir`, {
    method: 'POST',
    headers: { 'content-type': 'application/json' },
    body: JSON.stringify({ ...pedido, ...opcoes })
  })
  // 200 = decisão (que pode ser "revise"). 4xx = o SEU pedido está errado.
  if (resposta.status >= 400) throw new Error(`jev-gw ${resposta.status}: ${await resposta.text()}`)
  return resposta.json()
}

const saida = await decidir({
  model: 'jev-1.13.0',
  state: 'Mensagem do cliente: comprei ontem e quero devolver, nem abri a caixa.',
  questions: {
    fila: {
      type: 'choice',
      instructions: 'Para qual fila encaminhar esta mensagem?',
      criteria: {
        reembolso: 'Pedido de devolução ou estorno',
        suporte: 'Dúvida de uso ou defeito',
        insuficiente: 'Não dá para decidir com o que está escrito'
      }
    }
  }
})

if (saida.acao === 'suggest') console.log('→ fila:', saida.resposta.answers.fila.choice)
else console.log('→ revisão humana:', saida.motivo)
console.log(`   US$ ${saida.custo_usd} · ${saida.latencia_ms} ms · origem ${saida.origem}`)
