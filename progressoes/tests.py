# -*- coding: utf-8 -*-

from comum.tests import SuapTestCase
from django.apps.registry import apps
from datetime import date

Group = apps.get_model('auth', 'group')
ProcessoProgressao = apps.get_model('progressoes', 'processoprogressao')
PadraoVencimento = apps.get_model('rh', 'padraovencimento')


class ProgressoesTestCase(SuapTestCase):
    def setUp(self):
        super(ProgressoesTestCase, self).setUp()
        #
        self.padrao_vencimento_E1 = PadraoVencimento(categoria=PadraoVencimento.CATEGORIA_TECNICO_ADMINISTRATIVO, classe='E', posicao_vertical='01')
        self.padrao_vencimento_E1.save()
        self.padrao_vencimento_E2 = PadraoVencimento(categoria=PadraoVencimento.CATEGORIA_TECNICO_ADMINISTRATIVO, classe='E', posicao_vertical='02')
        self.padrao_vencimento_E2.save()
        #
        # permissões
        self.servidor_a.user.groups.add(Group.objects.get(name='Coordenador de Gestão de Pessoas Sistêmico'))
        self.servidor_a.save()
        self.servidor_b.user.groups.add(Group.objects.get(name='Servidor'))
        self.servidor_b.save()
        #
        # login com o servidor_a
        self.client.logout()
        self.client.login(**{'user': self.servidor_a.user})

    def test_add_progressao_merito(self):
        processos_merito_qtd = ProcessoProgressao.objects.filter(tipo=ProcessoProgressao.TIPO_PROGRESSAO_MERITO).count()
        #
        # via url admin
        response = self.client.post(
            '/admin/progressoes/processoprogressao/add/?tipo=1',
            dict(
                avaliado=self.servidor_b.pk,
                data_inicio_contagem_progressao=date(2017, 1, 9).strftime("%d/%m/%Y"),
                padrao_anterior=self.padrao_vencimento_E1.pk,
                padrao_novo=self.padrao_vencimento_E2.pk,
            ),
        )
        #
        self.assertNotEqual(response.status_code, 500)
        self.assertEqual(ProcessoProgressao.objects.filter(tipo=ProcessoProgressao.TIPO_PROGRESSAO_MERITO).count(), processos_merito_qtd + 1)
        #
        # via model
        processo = ProcessoProgressao(
            tipo=ProcessoProgressao.TIPO_PROGRESSAO_MERITO,
            avaliado=self.servidor_b,
            data_inicio_contagem_progressao=date(2017, 1, 9),
            padrao_anterior=self.padrao_vencimento_E1,
            padrao_novo=self.padrao_vencimento_E2,
        )
        processo.save()
        #
        self.assertEqual(ProcessoProgressao.objects.filter(tipo=ProcessoProgressao.TIPO_PROGRESSAO_MERITO).count(), processos_merito_qtd + 2)

    def test_add_estagio_probatorio(self):
        processos_estagio_probatorio_qtd = ProcessoProgressao.objects.filter(tipo=ProcessoProgressao.TIPO_ESTAGIO_PROBATORIO).count()
        #
        # via url admin
        response = self.client.post(
            '/admin/progressoes/processoprogressao/add/?tipo=2', dict(avaliado=self.servidor_b.pk, data_inicio_contagem_progressao=date(2017, 1, 9).strftime("%d/%m/%Y"))
        )
        #
        self.assertNotEqual(response.status_code, 500)
        self.assertEqual(ProcessoProgressao.objects.filter(tipo=ProcessoProgressao.TIPO_ESTAGIO_PROBATORIO).count(), processos_estagio_probatorio_qtd + 1)
        #
        # via model
        processo = ProcessoProgressao(tipo=ProcessoProgressao.TIPO_ESTAGIO_PROBATORIO, avaliado=self.servidor_b, data_inicio_contagem_progressao=date(2017, 1, 9))
        processo.save()
        #
        self.assertEqual(ProcessoProgressao.objects.filter(tipo=ProcessoProgressao.TIPO_ESTAGIO_PROBATORIO).count(), processos_estagio_probatorio_qtd + 2)
