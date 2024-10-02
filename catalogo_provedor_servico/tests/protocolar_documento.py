from rest_framework.test import APIClient

from catalogo_provedor_servico.models import Servico, ServicoEquipe
from catalogo_provedor_servico.tests import dados
from comum.models import Configuracao
from comum.tests import SuapTestCase
from documento_eletronico.models import TipoDocumento, HipoteseLegal, NivelAcesso
from processo_eletronico.models import TipoProcesso, ModeloDespacho, Processo
from rh.models import Servidor


class ProtocolarDocumentoTestCase(SuapTestCase):
    @classmethod
    def criar_servicos(cls):
        servico_ead, _ = Servico.objects.get_or_create(
            id_servico_portal_govbr=6176,
            icone='fa fa-question-circle',
            titulo='Matrícula EAD',
            descricao='Este serviço permite que um candidato possa fazer uma matrícula de ensino a distancia',
            ativo=True)

        servico_diploma, _ = Servico.objects.get_or_create(
            id_servico_portal_govbr=6024,
            icone='fa fa-question-circle',
            titulo='Emissão de 2a Via de Diploma',
            descricao='Este serviço permite que um aluno formado possa solicitar a emissão de segunda via de diploma',
            ativo=True)

        servico_processo, _ = Servico.objects.get_or_create(
            id_servico_portal_govbr=10056,
            icone='fa fa-question-circle',
            titulo='Protocolar Documentos',
            descricao='Este serviço permite que um cidadão possa protocolar documentos junto a instituição',
            ativo=True)

        gerente = Servidor.objects.get(matricula='1111111').get_vinculo()
        ServicoEquipe.objects.get_or_create(servico=servico_ead, vinculo=gerente, campus=gerente.setor.uo)
        ServicoEquipe.objects.get_or_create(servico=servico_diploma, vinculo=gerente, campus=gerente.setor.uo)
        ServicoEquipe.objects.get_or_create(servico=servico_processo, vinculo=gerente, campus=gerente.setor.uo)

    @staticmethod
    def criar_tipo_processo():
        tipo_processo, _ = TipoProcesso.objects.get_or_create(
            nome='Segunda Via de Diploma',
            nivel_acesso_default=Processo.NIVEL_ACESSO_PUBLICO
        )
        Configuracao.objects.get_or_create(app='processo_eletronico', chave='tipo_processo_solicitar_emissao_diploma',
                                           valor=tipo_processo.pk)

        tipo_documento, _ = TipoDocumento.objects.get_or_create(
            nome='Requerimento Segunda Via de Diploma',
            sigla='REQ',
        )
        Configuracao.objects.get_or_create(app='documento_eletronico', chave='tipo_documento_requerimento',
                                           valor=tipo_documento.pk)

        modelo_despacho, _ = ModeloDespacho.objects.get_or_create(
            cabecalho='IFRN\n',
            rodape='\n------\n'
        )
        HipoteseLegal.objects.get_or_create(id=100, nivel_acesso=NivelAcesso.RESTRITO.name,
                                            descricao='Documento Severamente Restrito', base_legal='Lei 123789/2020')

        Configuracao.objects.get_or_create(app='processo_eletronico',
                                           chave='hipotese_legal_documento_abertura_requerimento', valor=100)

        tipo_processo, _ = TipoProcesso.objects.get_or_create(
            nome='Protocolo Eletrônico Demanda Externa',
            nivel_acesso_default=Processo.NIVEL_ACESSO_PUBLICO
        )
        Configuracao.objects.get_or_create(app='processo_eletronico', chave='tipo_processo_demanda_externa_do_cidadao',
                                           valor=tipo_processo.pk)
        Configuracao.objects.get_or_create(app='catalogo_provedor_servico', chave='url_orgaos_gov_br',
                                           valor='https://servicos.gov.br/api/v1/orgao')

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.criar_servicos()
        cls.criar_tipo_processo()
        cls.client = APIClient()

    def test_servicos_ativos(self):
        response = self.client.get('/catalogo_provedor_servico/servicos/', format='json').json()
        self.assertEqual(response, dados.servicos_ativos_01)

        response = self.client.get('/catalogo_provedor_servico/servicos/6024/', format='json').json()
        self.assertEqual(response, dados.servicos_ativos_02)

    def test_servicos_disponiveis(self):
        response = self.client.get('/catalogo_provedor_servico/servicos/cpf/86147407864/', format='json').json()
        self.assertEqual(response, dados.servicos_disponiveis_01)

    def test_servicos_avaliacao_disponibilidade(self):
        response = self.client.get('/catalogo_provedor_servico/servicos/cpf/86147407864/avaliacao_disponibilidade/', format='json').json()
        self.assertEqual(response, dados.servicos_avaliacao_disponibilidade_01)

    def test_receber_solicitacao_protocolar_documento(self):
        response = self.client.get('/catalogo_provedor_servico/servicos/10056/cpf/86147407864/receber_solicitacao/', content_type='application/json').json()
        self.assertEqual(response['mensagem'], None)
        self.assertEqual(response['resposta']['etapa_atual'], 1)
        self.assertEqual(response['resposta']['fieldsets'], dados.receber_solicitacao_protocolar_documento_01_response_fieldsets)

        response = self.client.post('/catalogo_provedor_servico/servicos/10056/cpf/86147407864/receber_solicitacao/',
                                    data=dados.receber_solicitacao_protocolar_documento_02_request,
                                    content_type='application/json').json()
        self.assertEqual(response['mensagem'], None)
        self.assertEqual(response['resposta']['etapa_atual'], 2)
        self.assertEqual(response['resposta']['fieldsets'], dados.receber_solicitacao_protocolar_documento_02_response_fieldsets)

        response = self.client.post('/catalogo_provedor_servico/servicos/10056/cpf/86147407864/receber_solicitacao/',
                                    data=dados.receber_solicitacao_protocolar_documento_03_request,
                                    content_type='application/json').json()
        self.assertEqual(response, dados.receber_solicitacao_protocolar_documento_03_response)
