# -*- coding: utf-8 -*-

from comum.tests import SuapTestCase, SuapClient
from datetime import datetime, timedelta
from django.contrib.auth.models import Group
from remanejamento.models import Edital, Inscricao


class RemanejamentoTestCase(SuapTestCase):
    def setUp(self):
        super(RemanejamentoTestCase, self).setUp()
        self.servidor_a.user.groups.add(Group.objects.get(name='Coordenador de Remanejamento'))
        self.client_a = SuapClient()
        self.client_a.login(username=self.servidor_a.user.username, password='123')
        self.client_b = SuapClient()
        self.client_b.login(username=self.servidor_b.user.username, password='123')

    def test_cadastrar_edital(self):
        """
        Testa o acesso às listagem de editais e o cadastro de editais.
        """
        qtd_editais_antes = Edital.objects.count()

        # Acesso à telas

        # O usuário com permissões
        res = self.client_a.get('/admin/remanejamento/edital/')
        self.assertEqual(res.status_code, 200)
        res = self.client_a.get('/admin/remanejamento/edital/add/')
        self.assertEqual(res.status_code, 200)

        # Cadastrando o edital
        inicio_inscricoes = datetime.now()
        fim_inscricoes = inicio_inscricoes + timedelta(7)
        inicio_resultados = fim_inscricoes + timedelta(1)
        resultado_recursos = inicio_resultados + timedelta(2)
        res = self.client_a.post(
            '/admin/remanejamento/edital/add/',
            {
                'titulo': 'Remanejamento para Cargo X',
                'descricao': 'Descricao de Remanejamento para cargo X',
                'inicio_inscricoes': inicio_inscricoes.strftime('%d/%m/%Y'),
                'inicio_inscricoes_time': '00:00',
                'fim_inscricoes': fim_inscricoes.strftime('%d/%m/%Y'),
                'fim_inscricoes_time': '00:00:00',
                'inicio_resultados': inicio_resultados.strftime('%d/%m/%Y'),
                'inicio_resultados_time': '00:00:00',
                'resultado_recursos': resultado_recursos.strftime('%d/%m/%Y'),
                'resultado_recursos_time': '00:00:00',
                'chave_hash': 'uma_chave_hash',
                'cargos': [self.servidor_b.cargo_emprego.pk],
                'campus': [self.campus_a_suap.pk],
            },
        )
        self.assertEqual(Edital.objects.count(), qtd_editais_antes + 1)

        self.edital = Edital.objects.latest('id')

    def test_cadastrar_inscricao(self):
        """
        Testa a visibilidade do link de inscrição em edital e faz a inscrição.
        """
        self.test_cadastrar_edital()

        # Acessando o index e o link da inscrição do edital

        # Servidor com cargo disponível no edital
        res = self.client_b.get('/')
        self.assertContains(res, self.edital.get_url_inscrever())
        res = self.client_b.get(self.edital.get_url_inscrever())
        self.assertEqual(res.status_code, 200)

        # Servidor com cargo indisponível no edital
        res = self.client_a.get('/')
        self.assertNotContains(res, self.edital.get_url_inscrever())
        # Realizando inscrição
        qtd_inscricoes_antes = Inscricao.objects.count()
        res = self.client_b.post(
            self.edital.get_url_inscrever(),
            {
                'inicio_exercicio': '01/01/2000',
                'jornada_trabalho': self.servidor_b.jornada_trabalho,
                'classificacao_concurso': '1',
                'dou_numero': '1',
                'dou_data': '01/02/2000',
                'dou_pagina': '1',
                'dou_sessao': '1',
                'campus_%d' % self.campus_a_suap.pk: self.campus_a_suap.pk,
            },
        )
        self.assertEqual(Inscricao.objects.count(), qtd_inscricoes_antes + 1)
