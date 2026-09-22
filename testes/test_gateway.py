"""Testes do gateway. Nenhum gasta crédito: todos usam avaliador controlado.

Rodar:  python3 -m unittest discover -s testes -v
"""
import json
import os
import tempfile
import time
import unittest
import urllib.error
import urllib.request
from pathlib import Path
from threading import Thread

from jev_gw import PedidoInvalido, decidir, saude
from jev_gw import cache, config, orcamento, registro, servidor

PEDIDO = {
    'model': 'jev-1.13.0',
    'state': 'Cliente pede reembolso de uma compra feita ontem, dentro do prazo.',
    'questions': {
        'fila': {
            'type': 'choice',
            'instructions': 'Para qual fila encaminhar?',
            'criteria': {'reembolso': 'Time de reembolso', 'suporte': 'Suporte geral', 'insuficiente': 'Falta informação'},
        }
    },
}

def resposta(escolha='reembolso', confianca=0.97, custo=0.00007):
    probabilidades = {'reembolso': 0.02, 'suporte': 0.02, 'insuficiente': 0.02}
    probabilidades[escolha] = 1 - sum(v for k, v in probabilidades.items() if k != escolha)
    return {
        'model': 'jev-1.13.0',
        'answers': {'fila': {'type': 'choice', 'choice': escolha, 'confidence': confianca,
                             'probabilities': probabilidades}},
        'usage': {'input_tokens': 120, 'output_tokens': 8, 'cost': custo},
    }


class Base(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.conf = dict(config.carregar(), dados=Path(self.tmp.name), teto_diario=1.0, ttl_cache=900)

    def tearDown(self):
        self.tmp.cleanup()


class TestDecisao(Base):
    def test_sugestao_quando_confiante(self):
        s = decidir(PEDIDO, avaliador=lambda p: resposta(), conf=self.conf)
        self.assertEqual(s['acao'], 'suggest')
        self.assertEqual(s['resposta']['answers']['fila']['choice'], 'reembolso')
        self.assertEqual(s['origem'], 'controlado')

    def test_revisao_quando_confianca_baixa(self):
        s = decidir(PEDIDO, avaliador=lambda p: resposta(confianca=0.51), conf=self.conf)
        self.assertEqual(s['acao'], 'review')
        self.assertIn('fila', s['motivo'])

    def test_revisao_quando_opcao_e_insuficiente(self):
        s = decidir(PEDIDO, avaliador=lambda p: resposta(escolha='insuficiente'), conf=self.conf)
        self.assertEqual(s['acao'], 'review')

    def test_dominio_sensivel_sempre_revisa(self):
        s = decidir(PEDIDO, avaliador=lambda p: resposta(), sensivel=True, conf=self.conf)
        self.assertEqual(s['acao'], 'review')

    def test_pedido_invalido_levanta(self):
        with self.assertRaises(PedidoInvalido):
            decidir({'model': 'jev-1.13.0', 'state': '', 'questions': {}}, conf=self.conf)


class TestFalhaConservadora(Base):
    """O ponto do gateway: infraestrutura quebrada vira revisão, não exceção."""

    def test_provedor_fora_do_ar_vira_revisao(self):
        def explode(pedido):
            raise ConnectionError('conexão recusada')
        s = decidir(PEDIDO, avaliador=explode, conf=self.conf)
        self.assertEqual(s['acao'], 'review')
        self.assertEqual(s['origem'], 'erro')

    def test_resposta_invalida_vira_revisao(self):
        s = decidir(PEDIDO, avaliador=lambda p: {'model': 'x', 'answers': {}, 'usage': {}}, conf=self.conf)
        self.assertEqual(s['acao'], 'review')
        self.assertEqual(s['origem'], 'erro')

    def test_teto_estourado_bloqueia_antes_de_gastar(self):
        conf = dict(self.conf, teto_diario=0.00001)
        registro.gravar(conf['dados'], {'custo_usd': 0.01, 'ok': True, 'acao': 'suggest', 'origem': 'api'})
        chamou = []
        s = decidir(PEDIDO, conf=conf)          # sem avaliador: caminho real, mas o teto barra antes
        self.assertEqual(s['acao'], 'review')
        self.assertEqual(s['origem'], 'bloqueado')
        self.assertIn('Teto diário', s['motivo'])
        self.assertEqual(chamou, [])

    def test_teto_zero_desliga(self):
        s = decidir(PEDIDO, conf=dict(self.conf, teto_diario=0))
        self.assertEqual(s['origem'], 'bloqueado')


class TestCache(Base):
    def test_impressao_ignora_ordem_das_chaves(self):
        a = {'model': 'm', 'state': 's', 'questions': {}}
        b = {'questions': {}, 'state': 's', 'model': 'm'}
        self.assertEqual(cache.impressao(a), cache.impressao(b))

    def test_guarda_e_recupera(self):
        chave = cache.impressao(PEDIDO)
        cache.guardar(self.conf['dados'], chave, resposta())
        self.assertIsNotNone(cache.buscar(self.conf['dados'], chave, 900))

    def test_ttl_vencido_nao_serve(self):
        chave = cache.impressao(PEDIDO)
        cache.guardar(self.conf['dados'], chave, resposta())
        # envelhece o arquivo em vez de dormir: teste deterministico, sem corrida
        arq = Path(self.tmp.name)/'cache'/f'{chave}.json'
        antigo = time.time() - 3600
        os.utime(arq, (antigo, antigo))
        self.assertIsNone(cache.buscar(self.conf['dados'], chave, 900))

    def test_limpar(self):
        cache.guardar(self.conf['dados'], cache.impressao(PEDIDO), resposta())
        self.assertEqual(cache.limpar(self.conf['dados']), 1)


class TestRegistro(Base):
    def test_resumo_soma_custo_e_classifica(self):
        d = self.conf['dados']
        registro.gravar(d, {'custo_usd': 0.001, 'ok': True, 'acao': 'suggest', 'origem': 'api', 'latencia_ms': 100})
        registro.gravar(d, {'custo_usd': 0.002, 'ok': True, 'acao': 'review', 'origem': 'api', 'latencia_ms': 300})
        registro.gravar(d, {'custo_usd': 0, 'ok': True, 'acao': 'suggest', 'origem': 'cache', 'latencia_ms': 1})
        r = registro.resumo(d)
        self.assertEqual(r['chamadas'], 3)
        self.assertEqual(r['consultas_reais'], 2)
        self.assertEqual(r['cache'], 1)
        self.assertEqual(r['revisao'], 1)
        self.assertAlmostEqual(r['gasto_usd'], 0.003)

    def test_linha_corrompida_nao_derruba(self):
        arq = registro.caminho(self.conf['dados'])
        arq.write_text('{"custo_usd": 0.5, "ok": true}\n{quebrado\n', encoding='utf-8')
        self.assertEqual(registro.resumo(self.conf['dados'])['chamadas'], 1)

    def test_decidir_grava_uma_linha(self):
        decidir(PEDIDO, avaliador=lambda p: resposta(), conf=self.conf)
        self.assertEqual(len(registro.ler(self.conf['dados'])), 1)


class TestServidorHTTP(Base):
    def setUp(self):
        super().setUp()
        self.srv = servidor.servir(self.conf, porta=0, host='127.0.0.1')
        self.url = f'http://127.0.0.1:{self.srv.server_address[1]}'
        Thread(target=self.srv.serve_forever, daemon=True).start()

    def tearDown(self):
        self.srv.shutdown(); self.srv.server_close()
        super().tearDown()

    def _post(self, corpo):
        req = urllib.request.Request(self.url+'/decidir', data=json.dumps(corpo).encode(),
                                     headers={'Content-Type': 'application/json'}, method='POST')
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                return r.status, json.loads(r.read())
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read())

    def test_saude_responde_sem_gastar(self):
        with urllib.request.urlopen(self.url+'/saude', timeout=10) as r:
            corpo = json.loads(r.read())
        self.assertTrue(corpo['ok'])
        self.assertEqual(corpo['teto_diario_usd'], 1.0)

    def test_painel_responde_html(self):
        with urllib.request.urlopen(self.url+'/painel', timeout=10) as r:
            self.assertIn('jev-gw', r.read().decode())

    def test_pedido_invalido_da_422(self):
        codigo, corpo = self._post({'model': 'jev-1.13.0', 'state': '', 'questions': {}})
        self.assertEqual(codigo, 422)
        self.assertEqual(corpo['acao'], 'review')

    def test_json_quebrado_da_400(self):
        req = urllib.request.Request(self.url+'/decidir', data=b'{nao e json',
                                     headers={'Content-Type': 'application/json'}, method='POST')
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(req, timeout=10)
        self.assertEqual(ctx.exception.code, 400)

    def test_rota_desconhecida_da_404(self):
        with self.assertRaises(urllib.error.HTTPError) as ctx:
            urllib.request.urlopen(self.url+'/qualquer', timeout=10)
        self.assertEqual(ctx.exception.code, 404)

    def test_teto_estourado_responde_200_com_revisao(self):
        """Erro de infraestrutura não vira erro HTTP: o cliente segue o fluxo dele."""
        registro.gravar(self.conf['dados'], {'custo_usd': 99, 'ok': True, 'acao': 'suggest', 'origem': 'api'})
        codigo, corpo = self._post(dict(PEDIDO))
        self.assertEqual(codigo, 200)
        self.assertEqual(corpo['acao'], 'review')
        self.assertEqual(corpo['origem'], 'bloqueado')


class TestSaude(Base):
    def test_reporta_teto_e_gasto(self):
        registro.gravar(self.conf['dados'], {'custo_usd': 0.25, 'ok': True, 'acao': 'suggest', 'origem': 'api'})
        s = saude(self.conf)
        self.assertAlmostEqual(s['gasto_hoje_usd'], 0.25)
        self.assertTrue(s['ok'])


if __name__ == '__main__':
    unittest.main()
