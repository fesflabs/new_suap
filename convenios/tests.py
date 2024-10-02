# -*- coding: utf-8 -*-
from comum.tests import SuapTestCase
from comum.utils import somar_data
from convenios.models import Convenio, SituacaoConvenio, TipoConvenio
from django.contrib.auth.models import Group
from django.apps import apps
import datetime


Permission = apps.get_model('auth', 'permission')
User = apps.get_model('comum', 'user')

# ano usado nos testes
ano_atual = datetime.date.today().year
ano_futuro = ano_atual + 1


class ConveniosTestCase(SuapTestCase):
    def setUp(self):
        super(ConveniosTestCase, self).setUp()
        self.servidor_a.user.groups.add(Group.objects.get(name='Operador de Convênios Sistêmico'))
        self.servidor_a.user.save()
        self.client.login(username=self.servidor_a.user.username, password='123')

        self.tipoconvenio = TipoConvenio.objects.get_or_create(descricao='Convênio')[0]
        self.situacaoconvenio_vigente = SituacaoConvenio.objects.get_or_create(id=1, descricao='Vigente')[0]
        self.situacaoconvenio_vencido = SituacaoConvenio.objects.get_or_create(id=4, descricao='Vencido')[0]
        self.situacaoconvenio_vincendo = SituacaoConvenio.objects.get_or_create(id=3, descricao='Vincendo')[0]
        self.hoje = datetime.datetime.today()

    def test_cadastro_convenio(self):

        unidadeorganizacional = self.setor_a0_suap.uo
        pessoajuridica = self.pessoa_juridica
        self.pessoa_juridica.save()
        url = '/admin/convenios/convenio/add/'
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Convênio', status_code=200)
        count = Convenio.objects.all().count()
        data_inicio = somar_data(self.hoje, -120).date()
        data_fim = somar_data(self.hoje, 365).date()
        input = dict(
            numero='99999/9999',
            tipo=self.tipoconvenio.pk,
            situacao=self.situacaoconvenio_vigente.pk,
            uo=unidadeorganizacional.pk,
            interveniente=pessoajuridica.pk,
            data_inicio='%d/%d/%d' % (data_inicio.day, data_inicio.month, data_inicio.year),
            data_fim='%d/%d/%d' % (data_fim.day, data_fim.month, data_fim.year),
            objeto='Objetivo do contrato',
            vinculos_conveniadas=pessoajuridica.get_vinculo().pk,
        )
        response = self.client.post(url, input)

        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/convenios/convenio/%d/' % Convenio.objects.all()[0].pk, status_code=302)
        self.assertEqual(Convenio.objects.all().count(), count + 1)

    def test_busca_convenio(self):
        self.test_cadastro_convenio()

        unidadeorganizacional = self.setor_a0_suap.uo
        pessoajuridica = self.pessoa_juridica

        url = '/convenios/convenios/'
        response = self.client.get(url)
        self.assertContains(response, 'Buscar Convênios', status_code=200)
        data_inicio = somar_data(self.hoje, -120).date()
        data_fim = somar_data(self.hoje, +365).date()
        input = dict(
            numero='99999/9999',
            conveniada=pessoajuridica.pk,
            interveniente=pessoajuridica.pk,
            situacao=self.situacaoconvenio_vigente.pk,
            tipo=self.tipoconvenio.pk,
            uo=unidadeorganizacional.pk,
            data_inicio='%d/%d/%d' % (data_inicio.day, data_inicio.month, data_inicio.year),
            data_fim='%d/%d/%d' % (data_fim.day, data_fim.month, data_fim.year),
        )

        response = self.client.post(url, input)

        self.assertContains(response, 'Convênios Encontrados', status_code=200)

    def test_convenio_vincendo(self):
        self.test_cadastro_convenio()

        convenio = Convenio.objects.all()[0]
        convenio.data_fim = somar_data(self.hoje, +30).date()
        convenio.save()

        self.assertEqual(convenio.get_situacao().pk, self.situacaoconvenio_vincendo.pk)

    def test_convenio_vencido(self):
        self.test_cadastro_convenio()

        convenio = Convenio.objects.all()[0]
        convenio.data_fim = somar_data(convenio.data_inicio, 1)
        convenio.save()
        self.assertEqual(convenio.get_situacao().pk, self.situacaoconvenio_vencido.pk)

    def test_aditivar_convenio(self):
        self.test_convenio_vencido()
        convenio = Convenio.objects.all()[0]

        url = '/convenios/adicionar_aditivo/%d/' % convenio.pk
        response = self.client.get(url)
        self.assertContains(response, 'Adicionar Aditivo', status_code=200)
        data_inicio = somar_data(self.hoje, +180).date()
        data_fim = somar_data(self.hoje, +365).date()
        input = dict(
            numero='99999/9999',
            objeto='Objtivo do aditivo',
            data='%d/%d/%d' % (self.hoje.day, self.hoje.month, self.hoje.year),
            data_inicio='%d/%d/%d' % (data_inicio.day, data_inicio.month, data_inicio.year),
            data_fim='%d/%d/%d' % (data_fim.day, data_fim.month, data_fim.year),
        )
        response = self.client.post(url, input)
        self.assert_no_validation_errors(response)
        self.assertEqual(convenio.get_situacao().pk, self.situacaoconvenio_vigente.pk)
