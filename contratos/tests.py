# -*- coding: utf-8 -*-

from comum.tests import SuapTestCase
from contratos.models import Contrato, TipoContrato, TipoLicitacao, TipoPublicacao, TipoFiscal, SubtipoContrato
from decimal import Decimal
from django.contrib.auth.models import Group
from django.apps import apps

from rh.models import Pessoa

Permission = apps.get_model('auth', 'permission')
User = apps.get_model('comum', 'user')
PessoaJuridica = apps.get_model('rh', 'pessoajuridica')
Processo = apps.get_model('protocolo', 'processo')


class ContratosTestCase(SuapTestCase):
    def setUp(self):
        super(ContratosTestCase, self).setUp()
        self.servidor_a.user.groups.add(Group.objects.get(name='Operador de Contrato'))
        self.servidor_a.user.groups.add(Group.objects.get(name='Coordenador de Contrato Sistêmico'))
        self.servidor_a.user.save()
        self.client.login(username=self.servidor_a.user.username, password='123')
        # Cadastra um processo do Protocolo
        self.processo = Processo.objects.create(vinculo_cadastro=self.servidor_a.get_vinculo(), assunto='Assunto Qualquer', tipo=1, setor_origem=self.servidor_a.setor)

    def test_fluxo_principal(self):

        # CADASTRO DE SUBTIPO CONTRATO

        url = '/admin/contratos/subtipocontrato/add/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(SubtipoContrato.objects.all().count(), 0)

        data = dict(tipo=TipoContrato.objects.get(pk=1).pk, descricao='Subtipo 1')
        response = self.client.post(url, data)
        self.assertEqual(SubtipoContrato.objects.all().count(), 1)
        subtipo = SubtipoContrato.objects.get(pk=1)

        # CADASTRO DE CONTRATO

        url = '/admin/contratos/contrato/add/'
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(Contrato.objects.all().count(), 0)

        arquivo = open('contratos/static/contratos/Manual_Contrato_FISCAL.pdf', 'r+b')
        data = dict(
            tipo=TipoContrato.objects.get(pk=1).pk,
            subtipo=subtipo.pk,
            numero='99999/9999',
            valor='12.000,00',
            data_inicio='01/01/2012',
            data_fim='31/12/2012',
            objeto='Contrato para prestacao de servico de limpeza',
            continuado=False,
            processo=self.processo.pk,
            empenho='',
            campi=self.campus_a_suap.pk,
            pessoa_contratada=Pessoa.objects.all()[0].pk,
            qtd_parcelas=12,
            tipo_licitacao=TipoLicitacao.objects.get(pk=1).pk,
            pregao='',
            concluido=False,
            motivo_conclusao='',
            cancelado=False,
            motivo_cancelamento="",
            dh_cancelamento='01/01/2012',
            dh_cancelamento_time='00:00',
            arquivo_contrato=arquivo,
        )
        response = self.client.post(url, data)
        self.assertEqual(Contrato.objects.all().count(), 1)
        contrato = Contrato.objects.get(pk=1)

        # ADIÇÃO DE PUBLICAÇÃO
        arquivo = open('contratos/static/contratos/Manual_Contrato_FISCAL.pdf', 'r+b')
        url = '/contratos/adicionar_publicacao/1/'
        data = dict(tipo=TipoPublicacao.objects.get(pk=1).pk, numero='2012.1-0', data='01/01/2012', descricao='Publicação inicial', arquivo=arquivo)
        response = self.client.post(url, data)
        self.assertEqual(contrato.publicacoes_set.count(), 1)

        # ADIÇÃO DE FISCAL
        url = '/contratos/adicionar_fiscal/1/'
        data = dict(
            tipo=TipoFiscal.objects.get(pk=1).pk,
            data_nomeacao='01/01/2012',
            data_vigencia='31/12/2012',
            servidor=self.servidor_a.pk,
            numero_portaria='99999/99',
            campus=self.campus_a_suap.pk,
        )
        response = self.client.post(url, data)
        self.assertEqual(contrato.fiscais_set.count(), 1)

        # ADIÇÃO DE TERMO ADITIVO
        arquivo = open('contratos/static/contratos/Manual_Contrato_FISCAL.pdf', 'r+b')
        url = '/contratos/adicionar_aditivo/1/'
        data = dict(numero='99999/9999', valor='1.000,00', data_inicio='01/01/2013', data_fim='01/02/2013', de_prazo='on', de_valor='on', arquivo_aditivo=arquivo)
        response = self.client.post(url, data)
        self.assertEqual(contrato.aditivos_set.count(), 1)

        # REGISTRAR OCORRÊNCIA

        url = '/contratos/registrar_ocorrencia/1/'
        data = dict(descricao='Isso é um teste', prazo_resolucao='01/02/2013')
        response = self.client.post(url, data)
        self.assertEqual(contrato.ocorrencia_set.count(), 1)

        # TENTAR GERAR PARCELAS SEM CRONOGRAMA DEFINIDO

        url = '/contratos/gerar_parcelas/1/'
        response = self.client.get(url)

        # DEFINIR CRONOGRAMA
        url = '/contratos/definir_cronograma/1/'
        data = dict(numero='99999/9999', nl='9999')
        response = self.client.post(url, data)

        # GERAR PARCELAS COM CRONOGRAMA DEFINIDO
        url = '/contratos/gerar_parcelas/1/'
        data = {'form-TOTAL_FORMS': contrato.qtd_parcelas, 'form-INITIAL_FORMS': 1}
        meses = ['01', '02', '03', '04', '05', '06', '07', '08', '09', '10', '11', '12']
        valor_parcela = str(contrato.valor / Decimal(12)).replace('.', ',')
        for i in range(0, contrato.qtd_parcelas):
            key = 'form-{:d}-data_prevista_inicio'.format(i)
            data[key] = '01/{}/2012'.format(meses[i])
            key = 'form-{:d}-data_prevista_fim'.format(i)
            if i == 11:
                data[key] = '01/01/2013'
            data[key] = '01/{}/2012'.format(meses[i])
            key = 'form-{:d}-valor_previsto'.format(i)
            data[key] = valor_parcela
        response = self.client.post(url, data)
        self.assertEqual(contrato.get_cronograma().parcelas_set.count(), contrato.qtd_parcelas)

        # EFETUAR MEDIÇÃO DE PARCELA SEM PERFIL DE FISCAL
        arquivo_medicao = open('contratos/static/contratos/Manual_Contrato_FISCAL.pdf', 'r+b')
        url = '/contratos/efetuar_medicao/1/1/'
        data = dict(
            data_inicio='01/01/2012',
            data_fim='01/02/2012',
            numero_documento='9999',
            valor_executado=valor_parcela,
            ocorrencia='Descrição da ocorrência',
            arquivo_medicao=arquivo_medicao,
            processo=self.processo.pk
        )
        response = self.client.post(url, data)
        self.assertTrue('input name="valor_executado" ' not in response.content.decode("utf-8"))
