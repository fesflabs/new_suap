# -*- coding: utf-8 -*-

import datetime

from django.apps.registry import apps
from django.urls import reverse

from comum.tests.tests_base import SuapTestCase

Group = apps.get_model('auth', 'group')
AreaAtuacao = apps.get_model('comum', 'AreaAtuacao')
CategoriaServico = apps.get_model('centralservicos', 'CategoriaServico')
GrupoServico = apps.get_model('centralservicos', 'GrupoServico')
Servico = apps.get_model('centralservicos', 'Servico')
CentroAtendimento = apps.get_model('centralservicos', 'CentroAtendimento')
GrupoAtendimento = apps.get_model('centralservicos', 'GrupoAtendimento')
Chamado = apps.get_model('centralservicos', 'Chamado')
BaseConhecimento = apps.get_model('centralservicos', 'BaseConhecimento')
HistoricoStatus = apps.get_model('centralservicos', 'HistoricoStatus')


class CentralServicosTestCase(SuapTestCase):
    def setUp(self):
        super(CentralServicosTestCase, self).setUp()
        self.servidor_a.user.groups.add(Group.objects.get(name='Atendente da Central de Serviços'))
        self.servidor_a.user.groups.add(Group.objects.get(name='Publicador da Base de Conhecimento'))
        self.servidor_b.user.groups.add(Group.objects.get(name='Aluno'))

        self.area_servico_1 = AreaAtuacao.objects.create(nome='Área Teste')
        self.categoria_servico_1 = CategoriaServico.objects.create(nome='Categoria Serviço 01', area=self.area_servico_1)
        self.grupo_servico_1 = GrupoServico.objects.create(
            nome='Grupo Serviço 01', detalhamento='Bibendum ducimus reiciendis quod similique, ipsa recusandae condimentum elementum?'
        )
        self.grupo_servico_1.categorias.add(self.categoria_servico_1)

        self.centro_atendimento_1 = CentroAtendimento.objects.create(nome='Centro de Atendimento 01', eh_local=True, area=self.area_servico_1)
        self.servico_1 = Servico.objects.create(nome='Serviço 01', tipo=Servico.TIPO_REQUISICAO, area=self.area_servico_1, grupo_servico=self.grupo_servico_1)
        self.servico_1.centros_atendimento.add(self.centro_atendimento_1)

        self.campus_referencia = self.campus_a_suap

        self.grupo_atendimento_1 = GrupoAtendimento.objects.create(nome='Grupo Atendimento 01', campus=self.campus_referencia, centro_atendimento=self.centro_atendimento_1)
        self.grupo_atendimento_1.responsaveis.add(self.servidor_a.user)
        self.grupo_atendimento_1.atendentes.add(self.servidor_a.user)
        chamado = Chamado(
            descricao='Abertura de chamado padrão. Testes Iniciais.',
            servico=self.servico_1,
            aberto_em=datetime.datetime.today(),
            aberto_por=self.servidor_b.user,
            interessado=self.servidor_b.user,
            requisitante=self.servidor_b.user,
            campus=self.campus_referencia,
            meio_abertura=Chamado.MEIO_ABERTURA_TELEFONE,
        )
        chamado.centro_atendimento = self.centro_atendimento_1
        chamado.save()
        self.chamado = chamado
        self.base_conhecimento = BaseConhecimento.objects.create(
            titulo='Esse, voluptatibus omnis illum autem aut illum.',
            resumo='Class unde in architecto eum nostrud neque nisi sem',
            area=self.area_servico_1,
            atualizado_por=self.servidor_a.user,
        )
        self.base_conhecimento.grupos_atendimento.add(self.grupo_atendimento_1)
        self.base_conhecimento.servicos.add(self.servico_1)

    def test_abrir_chamado(self):
        """ Aluno Abrindo Chamado """
        self.client.logout()
        self.client.login(username=self.servidor_b.user.username, password='123')

        url = reverse('centralservicos_selecionar_servico_abertura', args=[self.area_servico_1.slug])
        response = self.client.get(url)
        titulo = 'Abrir Chamado para {0}'.format(self.area_servico_1.nome)
        self.assertContains(response, titulo, status_code=200)

        url = reverse('centralservicos_abrir_chamado', args=[self.servico_1.id])
        response = self.client.get(url)
        self.assertContains(response, self.servico_1.nome, status_code=200)

        # http://whoisnicoleharris.com/2015/01/06/implementing-django-formsets.html#unit-testing
        data = {
            'descricao': 'Nihil illo? Sunt purus, iusto, erat litora, adipisci eu amet!',
            'interessado': self.servidor_b.user,
            'requisitante': self.servidor_b.user,
            'uo': self.campus_referencia.pk,
            'centro_atendimento': self.centro_atendimento_1.pk,
            'meio_abertura': Chamado.MEIO_ABERTURA_TELEFONE,
            'chamadoanexo_set-TOTAL_FORMS': '0',
            'chamadoanexo_set-INITIAL_FORMS': '0',
            'chamadoanexo_set-TOTAL_FORM_COUNT': '',
        }

        response = self.client.post(url, data)
        self.assertEqual(Chamado.objects.all().count(), 2)

    def test_assumir_chamado_e_alterar_status(self):
        chamado = Chamado.objects.all()[0]
        atendimento_atribuicao = chamado.get_atendimento_atribuicao_atual()
        self.assertIsNone(atendimento_atribuicao.atribuido_para)

        """ Atendente da Central realizando Login """
        self.client.logout()
        self.client.login(username=self.servidor_a.user.username, password='123')

        """ Atendente da Central Assumindo o Chamado """
        url = reverse('centralservicos_auto_atribuir_chamado', args=[chamado.id])
        self.client.post(url)
        atendimento_atribuicao = chamado.get_atendimento_atribuicao_atual()
        self.assertEqual(atendimento_atribuicao.atribuido_para, self.servidor_a.user)

        """ Atendente da Central Colocando Em Atendimento """
        url = reverse('centralservicos_colocar_em_atendimento', args=[chamado.id])
        response = self.client.post(url)
        self.assert_no_validation_errors(response)
        historico_status = HistoricoStatus.objects.all().order_by('-data_hora')[0]
        self.assertEqual(historico_status.status, 2)  # EM_ATENDIMENTO = 2

        """ Atendente da Central Resolver Chamado """
        url = reverse('centralservicos_resolver_chamado', args=[chamado.id])
        data = {'bases_conhecimento': [self.base_conhecimento.id], 'observacao': 'Facere aliquam, et adipisci fugit corporis, ridiculus accusantium eros.'}
        response = self.client.post(url, data)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, chamado.get_absolute_url(), status_code=302)
        historico_status = HistoricoStatus.objects.all().order_by('-data_hora')[0]
        self.assertEqual(historico_status.status, 3)  # RESOLVIDO = 3
