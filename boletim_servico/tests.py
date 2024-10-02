# -*- coding: utf-8 -*-


import datetime

from django.test import RequestFactory, override_settings
from django.urls import reverse
from mock import mock
from model_mommy import mommy, random_gen
from comum.tests import SuapTestCase
from djtools.middleware import threadlocals
from documento_eletronico import models as docs
from rh.models import Servidor, UnidadeOrganizacional, ServidorFuncaoHistorico
from boletim_servico import models


def mock_now():
    return datetime.datetime(2018, 8, 13)


mommy.generators.add('djtools.db.models.CharFieldPlus', random_gen.gen_string)
mommy.generators.add('djtools.db.models.CharFieldPlus', random_gen.gen_string)
mommy.generators.add('djtools.db.models.SearchField', random_gen.gen_text)
mommy.generators.add('djtools.db.models.ForeignKey', random_gen.gen_related)
mommy.generators.add('djtools.db.models.ForeignKeyPlus', random_gen.gen_related)
mommy.generators.add('djtools.db.models.DateFieldPlus', random_gen.gen_date)
mommy.generators.add('djtools.db.models.DateTimeFieldPlus', random_gen.gen_datetime)
mommy.generators.add('djtools.db.models.TimeFieldPlus', random_gen.gen_time)
mommy.generators.add('djtools.db.models.OneToOneFieldPlus', random_gen.gen_related)
mommy.generators.add('djtools.db.models.OneToOneField', random_gen.gen_related)
mommy.generators.add('djtools.db.models.ManyToManyFieldPlus', random_gen.gen_m2m)
mommy.generators.add('djtools.db.models.CurrentUserField', random_gen.gen_related)
mommy.generators.add('djtools.db.models.DecimalFieldPlus', random_gen.gen_decimal)
mommy.generators.add('djtools.db.models.FileFieldPlus', random_gen.gen_file_field)


@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class BoletimTestCase(SuapTestCase):
    def setUp(self):
        super(BoletimTestCase, self).setUp()
        self.campus_raiz = mommy.make(UnidadeOrganizacional, setor=self.setor_raiz_suap, sigla=self.instituicao_sigla)
        self.setor_raiz_suap.uo = self.campus_raiz
        self.setor_raiz_suap.save()
        self.reitor = mommy.make(
            Servidor,
            template=b'1',
            setor=self.setor_raiz_suap,
            funcao_atividade__codigo='0062',
            nome='reitor',
            setor_funcao=self.setor_raiz_suap,
            setor_lotacao=self.setor_raiz_siape,
            setor_exercicio=self.setor_raiz_siape,
            _fill_optional=True,
            excluido=False,
        )
        self.historico_funcao = mommy.make(
            ServidorFuncaoHistorico,
            servidor=self.reitor,
            setor=self.setor_raiz_siape,
            setor_suap=self.setor_raiz_suap,
            atividade=self.reitor.funcao_atividade,
            data_inicio_funcao=mock_now() - datetime.timedelta(days=1),
            data_fim_funcao=None,
        )
        self.portaria = mommy.make(docs.TipoDocumentoTexto, nome='portaria', sigla='port')
        self.factory = RequestFactory()
        self.request = self.factory.get('/')
        threadlocals.tl.request = self.request
        threadlocals.tl.user = self.servidor_a.user

    def criar_documento(self):
        documento = mommy.make(
            docs.DocumentoTexto,
            setor_dono=self.setor_a0_suap,
            modelo__tipo_documento_texto=self.portaria,
            nivel_acesso=docs.Documento.NIVEL_ACESSO_PUBLICO,
            usuario_criacao=self.servidor_a.user,
            status=docs.DocumentoStatus.STATUS_CONCLUIDO,
            variaveis='',
        )
        mommy.make(docs.AssinaturaDocumentoTexto, documento=documento, assinatura__pessoa=self.servidor_a)
        documento.marcar_como_assinado()
        documento.finalizar_documento()
        documento.save()
        return documento

    def criar_boletim_programado(self):
        boletim_programado = models.BoletimProgramado.objects.create(
            titulo='Boletim de serviço', nivel_acesso=[docs.Documento.NIVEL_ACESSO_PUBLICO], programado=True, criado_por=self.servidor_a.user
        )
        boletim_programado.tipo_documento.add(self.portaria)
        models.ConfiguracaoSetorBoletim.objects.create(boletim_programado=boletim_programado, descricao='Seotr A0', setor_documento=self.setor_a0_suap)
        boletim_programado.gerar_boletim_diario(data=datetime.datetime(2018, 8, 13))
        return boletim_programado

    @mock.patch('django.utils.timezone.now', mock_now)
    def _test_criar_boletim_diario(self):
        self.assertEqual(models.BoletimDiario.objects.count(), 0)
        self.criar_documento()
        self.criar_documento()
        self.criar_boletim_programado()
        self.assertEqual(models.BoletimDiario.objects.count(), 1)
        boletim_diario = models.BoletimDiario.objects.first()
        self.assertEqual(boletim_diario.documentos.count(), 2)

    @mock.patch('django.utils.timezone.now', mock_now)
    def _test_edicao_extra(self):
        self.assertEqual(models.BoletimDiario.objects.count(), 0)
        documento_1 = self.criar_documento()
        boletim_programado = self.criar_boletim_programado()
        self.assertEqual(models.BoletimDiario.objects.count(), 1)
        boletim_diario = models.BoletimDiario.objects.first()
        self.assertEqual(boletim_diario.edicao_extra, 0)
        self.assertEqual(boletim_diario.documentos.count(), 1)

        documento_2 = self.criar_documento()
        boletim_programado.gerar_boletim_diario(data=datetime.datetime(2018, 8, 13))
        self.assertEqual(models.BoletimDiario.objects.count(), 2)
        boletim_diario2 = models.BoletimDiario.objects.last()
        self.assertEqual(boletim_diario2.edicao_extra, 1)
        self.assertEqual(boletim_diario.data, boletim_diario2.data)

        documento_3 = self.criar_documento()
        boletim_programado.gerar_boletim_diario(data=datetime.datetime(2018, 8, 13))
        self.assertEqual(models.BoletimDiario.objects.count(), 3)
        boletim_diario3 = models.BoletimDiario.objects.last()
        self.assertEqual(boletim_diario3.edicao_extra, 2)

        self.assertEqual(boletim_diario.documentos.first(), documento_1)
        self.assertEqual(boletim_diario2.documentos.first(), documento_2)
        self.assertEqual(boletim_diario3.documentos.first(), documento_3)

    @mock.patch('django.utils.timezone.now', mock_now)
    def _test_visualizar_boletim(self):
        self.criar_documento()
        boletim_programado = self.criar_boletim_programado()
        response = self.client.get(reverse('boletim_servico:boletins_publicos'))
        self.assertContains(response, '<h2>Boletins de Serviço do Período</h2>')
        self.assertContains(response, boletim_programado.boletimdiario_set.first())
        self.assertContains(response, 'Mostrando 1')
