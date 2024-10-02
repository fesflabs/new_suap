# flake8: noqa
import collections
import logging
from datetime import datetime

from django.contrib.auth.models import Permission, Group
from django.core.management import call_command
from django.test.client import Client

from comum.models import PrestadorServico
from comum.tests import SuapTestCase
from documento_eletronico.models import TipoDocumentoTexto, DocumentoTexto, Documento, NivelPermissao, \
    Classificacao, HipoteseLegal
from documento_eletronico.utils import get_setores_compartilhados
from processo_eletronico.models import TipoProcesso, Processo, ModeloDespacho
from rh.models import Servidor, Atividade, Funcao, Papel, JornadaTrabalho, Situacao, CargoEmprego, \
    ServidorFuncaoHistorico

GRUPO_GERENTE_SISTEMICO = 'Gerente Sistêmico de Documento Eletrônico'
GRUPO_OPERADOR_DOCUMENTO = 'Operador de Documento Eletrônico'
GRUPO_SERVIDOR = 'Servidor'

VISUALIZAR_COMO_PUBLICO = DocumentoTexto.NIVEL_ACESSO_PUBLICO
VISUALIZAR_COMO_RESTRITO = DocumentoTexto.NIVEL_ACESSO_RESTRITO
VISUALIZAR_COMO_SIGILOSO = DocumentoTexto.NIVEL_ACESSO_SIGILOSO


# ./manage.py test documento_eletronico.tests.FluxoDocumentoTestCase.test_fluxo_documento_publico --keepdb --verbosity=2


def print_dict(d, indent=0):
    for key, value in list(d.items()):
        print('\t' * indent + str(key))
        if isinstance(value, dict):
            print_dict(value, indent + 1)
        else:
            print('\t' * (indent + 1) + str(value))


def merge_nested_dict(d, u):
    for k, v in list(u.items()):
        if isinstance(v, collections.Mapping):
            default = v.copy()
            default.clear()
            r = merge_nested_dict(d.get(k, default), v)
            d[k] = r
        else:
            d[k] = v
    return d


class DocumentoEletronicoBaseTestCase(SuapTestCase):
    '''
    Servidores self.servidor_a e self.servidor_a2 são do mesmo setor

    Exemplo de definições dos métodos:
        Método que edita um documento:
            _editar_documento
                Só faz a ação de editar, sem testar perfis nem usuários
            _test_editar_documento
                No fluxo normal de teste deve fazer todas as verificações, mas no início dele deve
                ter um que faça, se necessário a verificação da submissão pode diversos usuário.
                Exemplo: _test_editar_documento_pessoas que executaria
                a submissão em '/documento_eletronico/editar_documento/{:d}/', necessário isso porque
                se tiver mais que uma verificação e um usuário que não deveria pode executar a ação
                pode ser bloqueada na na primeira e poder ser executada a segunda
            _test_editar_documento_pessoas
                Testar a edição de documento para vários usuários passados como parâmetro


    '''

    records = {}

    @classmethod
    def setUpTestData(cls):
        cls._criar_tipos_e_modelos()
        cls._criar_setores()
        cls._criar_usuarios_e_permissoes()
        cls._adicionar_permissoes()

    @classmethod
    def cadastrar(cls, modelo, data, chaves=None):
        if chaves is None:
            chaves = data
        qs = modelo.objects.filter(**chaves)
        if qs.exists():
            return qs[0]
        else:
            objeto = modelo.objects.create(**data)
            if modelo == Servidor:
                objeto.user.set_password('123')
                objeto.user.save()
                objeto = modelo.objects.get(pk=objeto.pk)
        return objeto

    @classmethod
    def _criar_tipos_e_modelos(cls):
        if not Classificacao.objects.exists():
            print('Loading initial data for types and models')
            call_command('loaddata', '../fixtures/initial_data_01_classificacao.json')
            call_command('loaddata', '../fixtures/initial_data_02_tipo_documento.json')
            call_command('loaddata', '../fixtures/initial_data_03_modelo_documento.json')

        print('Classificao carregada com sucesso')

    @classmethod
    def _criar_setores(cls):
        # atualizar_setor('RAIZ', 'IFRN')
        cls.records['setor_ifrn'] = cls.dict_initial_data['setor_raiz_suap']
        cls.records['setor_ifrn_siap'] = cls.dict_initial_data['setor_raiz_suap']
        # IFRN -> RE
        cls.records['setor_re'], cls.records['setor_re_siap'] = cls.cadastrar_setor('RE', cls.records['setor_ifrn'],
                                                                                    '00001')
        # IFRN -> RE -> DIGTI
        cls.records['setor_digti'], cls.records['setor_digti_siap'] = cls.cadastrar_setor('DIGTI',
                                                                                          cls.records['setor_re'])
        # IFRN -> RE -> GABIN
        cls.records['setor_gabin'], cls.records['setor_gabin_siap'] = cls.cadastrar_setor('GABIN',
                                                                                          cls.records['setor_re'])
        # IFRN -> RE -> PROPI
        cls.records['setor_propi'], cls.records['setor_propi_siap'] = cls.cadastrar_setor('PROPI',
                                                                                          cls.records['setor_re'])
        # IFRN -> RE -> PROEX
        cls.records['setor_proex'], cls.records['setor_proex_siap'] = cls.cadastrar_setor('PROEX',
                                                                                          cls.records['setor_re'])

        # IFRN -> RE -> DIGTI -> COSINF
        cls.records['setor_cosinf'], cls.records['setor_cosinf_siap'] = cls.cadastrar_setor('COSINF',
                                                                                            cls.records['setor_digti'])
        # IFRN -> RE -> DIGTI -> COINRE
        cls.records['setor_coinre'], cls.records['setor_coinre_siap'] = cls.cadastrar_setor('COINRE',
                                                                                            cls.records['setor_digti'])
        # IFRN -> RE -> DIGTI -> COSINF -> COSAAD
        cls.records['setor_cosaad'], cls.records['setor_cosaad_siap'] = cls.cadastrar_setor('COSAAD',
                                                                                            cls.records['setor_cosinf'])
        # COSAAD é setor irmão da COSINF
        cls.records['setor_cosinf'].setores_compartilhados.add(cls.records['setor_cosaad'])
        cls.records['setor_cosinf'].save()
        # IFRN -> RE -> DG/CNAT
        cls.records['setor_dg_cnat'], cls.records['setor_dg_cnat_siape'] = cls.cadastrar_setor('DG/CNAT',
                                                                                               cls.records['setor_re'],
                                                                                               '00003')
        # IFRN -> RE -> DG/CNAT -> DIATINF
        cls.records['setor_diatinf'], cls.records['setor_diatinf_siape'] = cls.cadastrar_setor('DIATINF', cls.records[
            'setor_dg_cnat'])

    @classmethod
    def _criar_usuarios_e_permissoes(cls):
        situacao_ativo_permanente = Situacao.objects.get(codigo=Situacao.ATIVO_PERMANENTE)
        jornada_trabalho_40h = JornadaTrabalho.objects.get(codigo='40')
        jornada_trabalho_de = JornadaTrabalho.objects.get(codigo='99')
        cargo_emprego_professor = CargoEmprego.objects.get(codigo='01')
        cargo_emprego_tae = CargoEmprego.objects.get(codigo='01')

        # Criando atividades das funções
        funcao_atividade_reitor = cls.cadastrar(Atividade, data={'codigo': Atividade.REITOR, 'nome': 'Reitor'},
                                                chaves={'codigo': Atividade.REITOR})
        funcao_atividade_diretor_geral = cls.cadastrar(Atividade, data={'codigo': Atividade.DIRETOR_GERAL,
                                                                        'nome': 'Diretor Geral'},
                                                       chaves={'codigo': Atividade.DIRETOR_GERAL})
        funcao_atividade_diretor = cls.cadastrar(Atividade, data={'codigo': Atividade.DIRETOR, 'nome': 'Diretor'},
                                                 chaves={'codigo': Atividade.DIRETOR})
        funcao_atividade_chefe = cls.cadastrar(Atividade, data={'codigo': '0006', 'nome': 'Chefe de Gabinete'},
                                               chaves={'codigo': '0006'})
        funcao_atividade_coordenador = cls.cadastrar(Atividade, data={'codigo': '2038', 'nome': 'Coordenador'},
                                                     chaves={'codigo': '2038'})
        funcao_cd = cls.cadastrar(Funcao, data={'codigo': 'CD', 'nome': 'CD'}, chaves={'codigo': 'CD'})
        funcao_fg = cls.cadastrar(Funcao, data={'codigo': 'FG', 'nome': 'FG'}, chaves={'codigo': 'FG'})

        agora = datetime.utcnow()

        data = {
            'nome': 'reitor',
            'matricula': '9001',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_professor,
            'setor': cls.records['setor_re'],
            'setor_lotacao': cls.records['setor_dg_cnat_siape'],  # setor siap DG
            'setor_exercicio': cls.records['setor_re_siap'],  # setor siap RE
            'setor_funcao': cls.records['setor_re_siap'],
            'email': 'reitor@mail.gov',
            'jornada_trabalho': jornada_trabalho_de,
            'cargo_emprego_data_ocupacao': agora,
            'funcao_atividade': funcao_atividade_reitor,
            'funcao': funcao_cd,
            'funcao_codigo': 1,
        }
        cls.records['reitor'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9001'})

        data = {
            'servidor': cls.records['reitor'],
            'data_inicio_funcao': datetime.today(),
            'data_fim_funcao': None,
            'atividade': funcao_atividade_reitor,
            'funcao': funcao_cd,
            'nivel': '10',
            'setor': cls.records['setor_re_siap'],
            'setor_suap': cls.records['setor_re'],
        }
        cls.cadastrar(ServidorFuncaoHistorico, data)

        data = {
            'nome': 'Diretor Geral CNAT',
            'matricula': '9002',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_professor,
            'setor': cls.records['setor_dg_cnat'],
            'setor_lotacao': cls.records['setor_dg_cnat_siape'],
            'setor_exercicio': cls.records['setor_dg_cnat_siape'],
            'setor_funcao': cls.records['setor_dg_cnat_siape'],
            'email': 'diretor_cnat@mail.gov',
            'jornada_trabalho': jornada_trabalho_de,
            'cargo_emprego_data_ocupacao': agora,
            'funcao_atividade': funcao_atividade_diretor_geral,
            'funcao': funcao_cd,
            'funcao_codigo': 2,
        }
        cls.records['diretor_cnat'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9002'})

        data = {
            'servidor': cls.records['diretor_cnat'],
            'data_inicio_funcao': datetime.today(),
            'data_fim_funcao': None,
            'atividade': funcao_atividade_diretor_geral,
            'funcao': funcao_cd,
            'nivel': '10',
            'setor': cls.records['setor_dg_cnat_siape'],
            'setor_suap': cls.records['setor_dg_cnat'],
        }
        cls.cadastrar(ServidorFuncaoHistorico, data)

        data = {
            'nome': 'Diretor DIGTI',
            'matricula': '9003',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_professor,
            'setor': cls.records['setor_digti'],
            'setor_lotacao': cls.records['setor_diatinf_siape'],
            'setor_exercicio': cls.records['setor_digti_siap'],
            'setor_funcao': cls.records['setor_digti_siap'],
            'email': 'diretor_digti@mail.gov',
            'jornada_trabalho': jornada_trabalho_de,
            'cargo_emprego_data_ocupacao': agora,
            'funcao_atividade': funcao_atividade_diretor,
            'funcao': funcao_cd,
            'funcao_codigo': 3,
        }
        cls.records['diretor_digti'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9003'})

        data = {
            'servidor': cls.records['diretor_digti'],
            'data_inicio_funcao': datetime.today(),
            'data_fim_funcao': None,
            'atividade': funcao_atividade_diretor,
            'funcao': funcao_cd,
            'nivel': '10',
            'setor': cls.records['setor_digti_siap'],
            'setor_suap': cls.records['setor_digti'],
        }
        cls.cadastrar(ServidorFuncaoHistorico, data)

        data = {
            'nome': 'Chefe de gabinete',
            'matricula': '9004',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_tae,
            'setor': cls.records['setor_gabin'],
            'setor_lotacao': cls.records['setor_re_siap'],
            'setor_exercicio': cls.records['setor_gabin_siap'],
            'setor_funcao': cls.records['setor_gabin_siap'],
            'email': 'chefe_gabin@mail.gov',
            'jornada_trabalho': jornada_trabalho_40h,
            'cargo_emprego_data_ocupacao': agora,
            'funcao_atividade': funcao_atividade_chefe,
            'funcao': funcao_cd,
            'funcao_codigo': 3,
        }
        cls.records['chefe_gabin'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9004'})
        permissoes = Permission.objects.filter(
            codename__in=[
                'add_tipodocumento',
                'change_tipodocumento',
                'change_tipodocumento',
                'delete_tipodocumento',
                'add_tipodocumentotexto',
                'change_tipodocumentotexto',
                'change_tipodocumentotexto',
                'delete_tipodocumentotexto',
                'add_classificacao',
                'change_classificacao',
                'add_modelodocumento',
                'change_modelodocumento',
                'change_modelodocumento',
                'delete_modelodocumento',
            ]
        )
        for permissao in permissoes:
            cls.records['chefe_gabin'].user.user_permissions.add(permissao)

        data = {
            'servidor': cls.records['chefe_gabin'],
            'data_inicio_funcao': datetime.today(),
            'data_fim_funcao': None,
            'atividade': funcao_atividade_chefe,
            'funcao': funcao_cd,
            'nivel': '10',
            'setor': cls.records['setor_gabin_siap'],
            'setor_suap': cls.records['setor_gabin'],
        }
        cls.cadastrar(ServidorFuncaoHistorico, data)

        # obj.user.groups.add(Group.objects.get(name=GRUPO_GERENTE_SISTEMICO))
        # obj.user.save()

        # Criando os coordenadores dos setores

        data = {
            'nome': 'Coordenador COSINF',
            'matricula': '9005',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cpf': '370.254.950-18',
            'cargo_emprego': cargo_emprego_tae,
            'setor': cls.records['setor_cosinf'],
            'setor_lotacao': cls.records['setor_re_siap'],
            'setor_exercicio': cls.records['setor_digti_siap'],
            'setor_funcao': cls.records['setor_digti_siap'],
            'email': 'coord_cosinf@mail.gov',
            'jornada_trabalho': jornada_trabalho_40h,
            'cargo_emprego_data_ocupacao': agora,
            'funcao_atividade': funcao_atividade_coordenador,
            'funcao': funcao_cd,
            'funcao_codigo': 4,
        }
        cls.records['coord_cosinf'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9005'})

        data = {
            'servidor': cls.records['coord_cosinf'],
            'data_inicio_funcao': datetime.today(),
            'data_fim_funcao': None,
            'atividade': funcao_atividade_coordenador,
            'funcao': funcao_cd,
            'nivel': '10',
            'setor': cls.records['setor_digti_siap'],
            'setor_suap': cls.records['setor_cosinf'],
        }
        cls.cadastrar(ServidorFuncaoHistorico, data)

        data = {
            'nome': 'Coordenador COSAAD',
            'matricula': '9006',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_tae,
            'setor': cls.records['setor_cosaad'],
            'setor_lotacao': cls.records['setor_re_siap'],
            'setor_exercicio': cls.records['setor_digti_siap'],
            'setor_funcao': cls.records['setor_digti_siap'],
            'email': 'coord_cosaad@mail.gov',
            'jornada_trabalho': jornada_trabalho_40h,
            'cargo_emprego_data_ocupacao': agora,
            'funcao_atividade': funcao_atividade_coordenador,
            'funcao': funcao_fg,
            'funcao_codigo': 1,
        }
        cls.records['coord_cosaad'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9006'})

        data = {
            'servidor': cls.records['coord_cosaad'],
            'data_inicio_funcao': datetime.today(),
            'data_fim_funcao': None,
            'atividade': funcao_atividade_coordenador,
            'funcao': funcao_fg,
            'nivel': '10',
            'setor': cls.records['setor_digti_siap'],
            'setor_suap': cls.records['setor_cosaad'],
        }
        cls.cadastrar(ServidorFuncaoHistorico, data)

        # Criando os servidores da COSINF
        data = {
            'nome': 'Servidor COSINF1',
            'matricula': '9007',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_tae,
            'setor': cls.records['setor_cosinf'],
            'setor_lotacao': cls.records['setor_re_siap'],
            'setor_exercicio': cls.records['setor_digti_siap'],
            'email': 'scosinf1@mail.gov',
            'jornada_trabalho': jornada_trabalho_40h,
            'cargo_emprego_data_ocupacao': agora,
        }
        cls.records['scosinf1'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9007'})

        data = {
            'nome': 'Servidor COSINF2',
            'matricula': '9008',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_tae,
            'setor': cls.records['setor_cosinf'],
            'setor_lotacao': cls.records['setor_re_siap'],
            'setor_exercicio': cls.records['setor_digti_siap'],
            'email': 'sconsif2@mail.gov',
            'jornada_trabalho': jornada_trabalho_40h,
            'cargo_emprego_data_ocupacao': agora,
        }
        cls.records['scosinf2'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9008'})

        data = {
            'nome': 'Prestador COSINF3',
            'cpf': '9098',
            'template': b'1',
            'excluido': False,
            'ativo': True,
            'setor': cls.records['setor_cosinf'],
            'setor_lotacao': cls.records['setor_re_siap'],
            'email': 'sconsif3@mail.gov',
        }
        cls.records['pcosinf3'] = cls.cadastrar(PrestadorServico, data, chaves={'username': '9098'})

        # Criando os servidores da DIATINF
        data = {
            'nome': 'Servidor DIATINF',
            'matricula': '9009',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_professor,
            'setor': cls.records['setor_diatinf'],
            'setor_lotacao': cls.records['setor_dg_cnat_siape'],
            'setor_exercicio': cls.records['setor_diatinf_siape'],
            'email': 'sdiatinf1@mail.gov',
            'jornada_trabalho': jornada_trabalho_de,
            'cargo_emprego_data_ocupacao': agora,
        }
        cls.records['sdiatinf1'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9009'})

        # Criando os servidores da COINRE
        data = {
            'nome': 'Servidor COINRE 1',
            'matricula': '9010',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_tae,
            'setor': cls.records['setor_coinre'],
            'setor_lotacao': cls.records['setor_re_siap'],
            'setor_exercicio': cls.records['setor_digti_siap'],
            'email': 'scoinre1@mail.gov',
            'jornada_trabalho': jornada_trabalho_40h,
            'cargo_emprego_data_ocupacao': agora,
        }
        cls.records['scoinre1'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9010'})

        data = {
            'nome': 'Servidor COINRE 2',
            'matricula': '9011',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_tae,
            'setor': cls.records['setor_coinre'],
            'setor_lotacao': cls.records['setor_re_siap'],
            'setor_exercicio': cls.records['setor_digti_siap'],
            'email': 'scoinre2@mail.gov',
            'jornada_trabalho': jornada_trabalho_40h,
            'cargo_emprego_data_ocupacao': agora,
        }
        cls.records['scoinre2'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9011'})

        # Pro-reitor PROEX
        data = {
            'nome': 'Pro-reitor PROEX',
            'matricula': '9012',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_professor,
            'setor': cls.records['setor_proex'],
            'setor_lotacao': cls.records['setor_dg_cnat_siape'],
            'setor_exercicio': cls.records['setor_proex_siap'],
            'setor_funcao': cls.records['setor_proex_siap'],
            'email': 'proreitor_proex@mail.gov',
            'jornada_trabalho': jornada_trabalho_de,
            'cargo_emprego_data_ocupacao': agora,
            'funcao_atividade': funcao_atividade_diretor,
            'funcao': funcao_cd,
            'funcao_codigo': 2,
        }
        cls.records['proreitor_proex'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9012'})

        data = {
            'servidor': cls.records['proreitor_proex'],
            'data_inicio_funcao': datetime.today(),
            'data_fim_funcao': None,
            'atividade': funcao_atividade_diretor,
            'funcao': funcao_cd,
            'nivel': '10',
            'setor': cls.records['setor_proex_siap'],
            'setor_suap': cls.records['setor_proex'],
        }
        cls.cadastrar(ServidorFuncaoHistorico, data)

        # Pro-reitor PROPI
        data = {
            'nome': 'Pro-reitor PROPI',
            'matricula': '9013',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_professor,
            'setor': cls.records['setor_propi'],
            'setor_lotacao': cls.records['setor_dg_cnat_siape'],
            'setor_exercicio': cls.records['setor_propi_siap'],
            'setor_funcao': cls.records['setor_propi_siap'],
            'email': 'proreitor_proex@mail.gov',
            'jornada_trabalho': jornada_trabalho_de,
            'cargo_emprego_data_ocupacao': agora,
            'funcao_atividade': funcao_atividade_diretor,
            'funcao': funcao_cd,
            'funcao_codigo': 2,
        }
        cls.records['proreitor_propi'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9013'})

        data = {
            'servidor': cls.records['proreitor_propi'],
            'data_inicio_funcao': datetime.today(),
            'data_fim_funcao': None,
            'atividade': funcao_atividade_diretor,
            'funcao': funcao_cd,
            'nivel': '10',
            'setor': cls.records['setor_propi_siap'],
            'setor_suap': cls.records['setor_propi'],
        }
        cls.cadastrar(ServidorFuncaoHistorico, data)

        # Criando os servidores da DIATINF
        data = {
            'nome': 'Servidor DIGTI',
            'matricula': '9014',
            'template': b'1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
            'cargo_emprego': cargo_emprego_professor,
            'setor': cls.records['setor_digti'],
            'setor_lotacao': cls.records['setor_dg_cnat_siape'],
            'setor_exercicio': cls.records['setor_digti_siap'],
            'email': 'sdigti1@mail.gov',
            'jornada_trabalho': jornada_trabalho_de,
            'cargo_emprego_data_ocupacao': agora,
        }
        cls.records['sdigti1'] = cls.cadastrar(Servidor, data, chaves={'matricula': '9014'})

        data = {
            'nome': 'Interrupção de Férias',
            'permite_nivel_acesso_privado': True,
            'permite_nivel_acesso_restrito': True,
            'permite_nivel_acesso_publico': True,
            'nivel_acesso_default': 3,
        }
        cls.records['tipo_processo'] = cls.cadastrar(TipoProcesso, data, chaves={'nome': 'Interrupção de Férias'})

        data = {'nivel_acesso': 'Público', 'descricao': 'Hipótese Legal Pública', 'base_legal': 'Art. 26'}
        cls.records['hipotese_legal_publico'] = cls.cadastrar(HipoteseLegal, data,
                                                              chaves={'descricao': 'Hipótese Legal Pública'})

        data = {'nivel_acesso': 'Restrito', 'descricao': 'Hipótese Legal Restrita', 'base_legal': 'Art. 27'}
        cls.records['hipotese_legal_restrito'] = cls.cadastrar(HipoteseLegal, data,
                                                               chaves={'descricao': 'Hipótese Legal Restrita'})

        data = {'nivel_acesso': 'Sigiloso', 'descricao': 'Hipótese Legal Sigilosa', 'base_legal': 'Art. 28'}
        cls.records['hipotese_legal_sigiloso'] = cls.cadastrar(HipoteseLegal, data,
                                                               chaves={'descricao': 'Hipótese Legal Sigilosa'})

        ModeloDespacho.objects.create(cabecalho='----', rodape='----')

        if not Papel.objects.filter(pessoa=cls.records['reitor']).exists():
            # Cadastrando os papeis dos servidores
            from rh.management.commands.importar_funcao_servidor import Command

            comando_cadastrar_papel = Command()
            comando_cadastrar_papel.handle()

        for tipo in TipoDocumentoTexto.objects.all():
            tipo.save()

        # DocumentoEletronicoTestCase.first_time = False
        # print '9009009009', Funcao.objects.filter(codigo='CD').exists()
        logger = logging.getLogger()
        for obj in list(cls.records.values()):
            if isinstance(obj, Servidor):
                logger.info('Adicionando servidor {} no grupo {}'.format(obj, GRUPO_OPERADOR_DOCUMENTO))
                obj.user.groups.add(Group.objects.get(name=GRUPO_OPERADOR_DOCUMENTO))
                obj.user.save()

    def test_fluxo(self):
        # Verificando permissões de adição
        self._verificar_setores_compartilhados()

        client = Client()
        client.login(username=self.records['coord_cosinf'].user.username, password='123')
        self._criar_documentos(client)

        self._tem_permissao_ler()
        self._tem_permissao_estrita_leitura()
        self._tem_permissao_editar()
        self._pode_editar()
        self._pode_concluir_documento()

    @classmethod
    def _adicionar_permissoes(cls):
        client = Client()
        user = cls.records['coord_cosinf'].user
        client.login(username=user.username, password='123')

        data = dict(
            setores_permitidos_podem_escrever=[cls.records['setor_digti'].id],
            pessoas_permitidas_podem_escrever=[cls.records['scosinf1'].id],
            setores_permitidos_podem_ler=[cls.records['setor_cosaad'].id],
            pessoas_permitidas_podem_ler=[cls.records['scosinf2'].id],
        )
        client.post('/documento_eletronico/gerenciar_compartilhamento_setor/', data)

    @classmethod
    def _verificar_setores_compartilhados(cls):
        def setor_editar_compartilhado_usuario(user):
            return get_setores_compartilhados(user, NivelPermissao.EDITAR).order_by('id').values_list('id', flat=True)

        def setor_ler_compartilhado_usuario(user):
            return get_setores_compartilhados(user, NivelPermissao.LER).order_by('id').values_list('id', flat=True)

        assert cls.records['setor_cosinf'].id in setor_editar_compartilhado_usuario(cls.records['coord_cosinf'].user)
        # servidor cosaad ta compartilhado leitura pela cosinf
        assert cls.records['setor_cosaad'].id in setor_editar_compartilhado_usuario(cls.records['coord_cosaad'].user)
        assert all(setor in setor_editar_compartilhado_usuario(cls.records['diretor_digti'].user) for setor in [cls.records['setor_digti'].id, cls.records['setor_cosinf'].id])
        assert cls.records['setor_cosinf'].id in setor_editar_compartilhado_usuario(cls.records['scosinf1'].user)
        assert not setor_editar_compartilhado_usuario(cls.records['scosinf2'].user).exists()
        assert not setor_editar_compartilhado_usuario(cls.records['pcosinf3'].user).exists()
        assert cls.records['setor_proex'].id in setor_editar_compartilhado_usuario(cls.records['proreitor_proex'].user)
        assert cls.records['setor_propi'].id in setor_editar_compartilhado_usuario(cls.records['proreitor_propi'].user)

        assert cls.records['setor_cosinf'].id in setor_ler_compartilhado_usuario(cls.records['coord_cosinf'].user)
        assert all(setor in setor_ler_compartilhado_usuario(cls.records['coord_cosaad'].user) for setor in [cls.records['setor_cosinf'].id,
                                                                                                            cls.records['setor_cosaad'].id])
        assert cls.records['setor_digti'].id in setor_ler_compartilhado_usuario(cls.records['diretor_digti'].user)
        assert not setor_ler_compartilhado_usuario(cls.records['scosinf1'].user).exists()
        assert cls.records['setor_cosinf'].id in setor_ler_compartilhado_usuario(cls.records['scosinf2'].user)
        assert not setor_ler_compartilhado_usuario(cls.records['pcosinf3'].user).exists()
        assert cls.records['setor_proex'].id in setor_ler_compartilhado_usuario(cls.records['proreitor_proex'].user)
        assert cls.records['setor_propi'].id in setor_ler_compartilhado_usuario(cls.records['proreitor_propi'].user)

    @classmethod
    def _criar_documentos(cls, client):
        # Documento Rascunho Público
        cls.records['documento_rascunho_publico'] = cls._gerar_documento(client, 'Rascunho Público',
                                                                         Documento.NIVEL_ACESSO_PUBLICO)

        # Documento Compartilhado Público
        cls.records['documento_compartilhado_publico'] = cls._gerar_documento(client, 'Compartilhado Público',
                                                                              Documento.NIVEL_ACESSO_PUBLICO)

        cls._gerar_compartilhamento(client, cls.records['documento_compartilhado_publico'])

        # Documento Concluído Público
        cls.records['documento_concluido_publico'] = cls._gerar_documento(client, 'Concluído Público',
                                                                          Documento.NIVEL_ACESSO_PUBLICO)
        cls._gerar_compartilhamento(client, cls.records['documento_concluido_publico'])
        cls._concluir_documento(client, cls.records['documento_concluido_publico'])
        # Documento Concluído Público
        cls.records['documento_finalizado_publico'] = cls._gerar_documento(client, 'Finalizado Público',
                                                                           Documento.NIVEL_ACESSO_PUBLICO)
        cls._gerar_compartilhamento(client, cls.records['documento_finalizado_publico'])
        cls._finalizar_documento(client, cls.records['documento_finalizado_publico'])

        # Documento Rascunho Restrito
        cls.records['documento_rascunho_restrito'] = cls._gerar_documento(client, 'Rascunho Restrito',
                                                                          Documento.NIVEL_ACESSO_RESTRITO)

        # Documento Compartilhado Restrito
        cls.records['documento_compartilhado_restrito'] = cls._gerar_documento(client, 'Compartilhado Restrito',
                                                                               Documento.NIVEL_ACESSO_RESTRITO)
        cls._gerar_compartilhamento(client, cls.records['documento_compartilhado_restrito'])

        # Documento Concluído Restrito
        cls.records['documento_concluido_restrito'] = cls._gerar_documento(client, 'Concluído Restrito',
                                                                           Documento.NIVEL_ACESSO_RESTRITO)
        cls._gerar_compartilhamento(client, cls.records['documento_concluido_restrito'])
        cls._concluir_documento(client, cls.records['documento_concluido_restrito'])

        # Documento Concluído Restrito
        cls.records['documento_finalizado_restrito'] = cls._gerar_documento(client, 'Finalizado Restrito',
                                                                            Documento.NIVEL_ACESSO_RESTRITO)
        cls._gerar_compartilhamento(client, cls.records['documento_finalizado_restrito'])
        cls._finalizar_documento(client, cls.records['documento_finalizado_restrito'])

        # Documento Rascunho Sigiloso
        cls.records['documento_rascunho_sigiloso'] = cls._gerar_documento(client, 'Rascunho Sigiloso',
                                                                          Documento.NIVEL_ACESSO_SIGILOSO)

        # Documento Compartilhado Sigiloso
        cls.records['documento_compartilhado_sigiloso'] = cls._gerar_documento(client, 'Compartilhado Sigiloso',
                                                                               Documento.NIVEL_ACESSO_SIGILOSO)
        cls._gerar_compartilhamento(client, cls.records['documento_compartilhado_sigiloso'])

        # Documento Concluído Sigiloso
        cls.records['documento_concluido_sigiloso'] = cls._gerar_documento(client, 'Concluído Sigiloso',
                                                                           Documento.NIVEL_ACESSO_SIGILOSO)
        cls._gerar_compartilhamento(client, cls.records['documento_concluido_sigiloso'])
        cls._concluir_documento(client, cls.records['documento_concluido_sigiloso'])

        # Documento Concluído Sigiloso
        cls.records['documento_finalizado_sigiloso'] = cls._gerar_documento(client, 'Finalizado Sigiloso',
                                                                            Documento.NIVEL_ACESSO_SIGILOSO)
        cls._gerar_compartilhamento(client, cls.records['documento_finalizado_sigiloso'])
        cls._finalizar_documento(client, cls.records['documento_finalizado_sigiloso'])

        # Documento Processo Público
        cls.records['documento_processo_publico'] = cls._gerar_documento(client, 'Processo Público',
                                                                         Documento.NIVEL_ACESSO_PUBLICO)
        cls._gerar_compartilhamento(client, cls.records['documento_processo_publico'])
        cls._finalizar_documento(client, cls.records['documento_processo_publico'])
        cls._criar_processo(client, cls.records['documento_processo_publico'], Processo.NIVEL_ACESSO_PUBLICO)

        # Documento Processo Restrito
        cls.records['documento_processo_restrito'] = cls._gerar_documento(client, 'Processo Restrito',
                                                                          Documento.NIVEL_ACESSO_RESTRITO)
        cls._gerar_compartilhamento(client, cls.records['documento_processo_restrito'])
        cls._finalizar_documento(client, cls.records['documento_processo_restrito'])
        cls._criar_processo(client, cls.records['documento_processo_restrito'], Processo.NIVEL_ACESSO_RESTRITO)

        # Documento Processo Sigiloso
        cls.records['documento_processo_sigiloso'] = cls._gerar_documento(client, 'Processo Sigiloso',
                                                                          Documento.NIVEL_ACESSO_SIGILOSO)
        cls._gerar_compartilhamento(client, cls.records['documento_processo_sigiloso'])
        cls._finalizar_documento(client, cls.records['documento_processo_sigiloso'])
        cls._criar_processo(client, cls.records['documento_processo_sigiloso'], Processo.NIVEL_ACESSO_PRIVADO)

    @classmethod
    def _gerar_documento(cls, client, assunto, nivel_acesso):
        if DocumentoTexto.objects.filter(assunto=assunto).exists():
            return DocumentoTexto.objects.filter(assunto=assunto)[0]
        oficio = TipoDocumentoTexto.objects.get(sigla='OFÍCIO')
        setor = cls.records['scosinf1'].setor
        modelo_documento = oficio.modelos.all()[0]

       #oficio.get_sugestao_identificador_definitivo(tipo_documento_texto=oficio, setor_dono=setor)

        data = dict(tipo=oficio.id, modelo=modelo_documento.id, nivel_acesso=nivel_acesso, setor_dono=setor.id,
                    assunto='Documento {}'.format(assunto))
        # Verifica se aparece o botão "Adicionar"
        client.post('/admin/documento_eletronico/documentotexto/add/', data)
        documento = DocumentoTexto.objects.latest('id')
        return documento

    @classmethod
    def _gerar_compartilhamento(cls, client, documento):
        data = dict(
            pessoas_permitidas_podem_ler=[cls.records['proreitor_propi'].id],
            pessoas_permitidas_podem_escrever=[cls.records['diretor_cnat'].id],
            setores_permitidos_podem_ler=[cls.records['setor_proex'].id],
            setores_permitidos_podem_escrever=[cls.records['setor_gabin'].id],
        )
        url = '/documento_eletronico/gerenciar_compartilhamento_documento/{}/'.format(documento.id)
        client.post(url, data, follow=True)

    @classmethod
    def _concluir_documento(cls, client, documento):
        url = '/documento_eletronico/concluir_documento/{}/'.format(documento.id)
        response = client.get(url, follow=True)

    @classmethod
    def _assinar_documento(cls, client, documento):
        url = '/documento_eletronico/assinar_documento/{}/'.format(documento.id)
        identificador_tipo_documento_sigla, identificador_numero, identificador_ano, identificador_setor_sigla = documento.get_sugestao_identificador_definitivo(
            tipo_documento_texto=documento.modelo.tipo_documento_texto, setor_dono=documento.setor_dono
        )
        data = {
            'assinar_documento_senha_wizard-current_step': '0',
            '0-identificador_tipo_documento_sigla': identificador_tipo_documento_sigla,
            '0-identificador_numero': identificador_numero,
            '0-identificador_ano': identificador_ano,
            '0-identificador_setor_sigla': identificador_setor_sigla,
            '1-senha': '123',
            '1-papel': '6',
        }
        response = client.post(url, data, follow=True)
        assert 'Assinar Documento' in response.content.decode()
        data['assinar_documento_senha_wizard-current_step'] = '1'
        response = client.post(url, data, follow=True)
        assert 'Documento assinado com sucesso.' in response.content.decode()

    @classmethod
    def _finalizar_documento(cls, client, documento):
        cls._concluir_documento(client, documento)
        cls._assinar_documento(client, documento)

        url = f'/documento_eletronico/finalizar_documento/{documento.id}/'
        response = client.get(url, follow=True)

    @classmethod
    def _criar_processo(cls, client, documento, nivel_acesso):
        url = f'/admin/processo_eletronico/processo/add/?documento_id={documento.id}'

        if nivel_acesso == Processo.NIVEL_ACESSO_PRIVADO:
            nivel_acesso_str = 'sigiloso'
        elif nivel_acesso == Processo.NIVEL_ACESSO_RESTRITO:
            nivel_acesso_str = 'restrito'
        else:
            nivel_acesso_str = 'publico'

        data = {
            'interessados': [cls.records['sdiatinf1'].id],
            'tipo_processo': cls.records['tipo_processo'].id,
            'assunto': 'Interrupção de Férias',
            'nivel_acesso': nivel_acesso,
            'hipotese_legal': cls.records[f'hipotese_legal_{nivel_acesso_str}'].id,
            'setor_criacao': cls.records['setor_cosinf'].id,
        }
        response = client.post(url, data, follow=True)
        processo_id = response.request['PATH_INFO'].split('/')[3]
        url = f'/processo_eletronico/processo/encaminhar_sem_despacho/{processo_id}/'

        data = {'tipo_busca_setor': 'autocompletar',
                'destinatario_setor_autocompletar': cls.records['setor_diatinf'].id}
        response = client.post(url, data, follow=True)

        client2 = Client()
        client2.login(username=cls.records['sdiatinf1'].user.username, password='123')
        url = f'/processo_eletronico/processo/receber/{processo_id}/'
        response = client2.get(url, follow=True)

    def setUp(self):
        # logging.disable(logging.CRITICAL)
        super().setUp()
        self.records = DocumentoEletronicoBaseTestCase.records
        self.servidores = []
        for obj in list(self.records.values()):
            if isinstance(obj, Servidor):
                self.servidores.append(obj)

    @classmethod
    def _tem_permissao_ler(cls):
        data = {
            'documento_rascunho_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', True],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', True],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', True],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', True],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
            ],
            'documento_concluido_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', True],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', True],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
            ],
            'documento_finalizado_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', True],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', True],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
            ],
            'documento_rascunho_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', True],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', True],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', True],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', True],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
            ],
            'documento_concluido_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', True],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', True],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
            ],
            'documento_finalizado_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', True],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', True],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
            ],
            'documento_rascunho_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_concluido_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_finalizado_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_processo_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', True],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', True],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
                ['sdiatinf1', False],
            ],
            # Rever esse teste porque o documento
            # tem um compartilhamento e esse teste é
            # inócuo.
            'documento_processo_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', True],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', True],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
                ['sdiatinf1', True],
            ],
            'documento_processo_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
                ['sdiatinf1', False],
            ],
        }
        for chave, lista in data.items():
            for usuario, resultado in lista:
                if cls.records[chave].pode_ler(cls.records[usuario].user) != resultado:
                    print('tem_permissao_ler', chave, usuario, resultado)
                    assert False

    @classmethod
    def _tem_permissao_estrita_leitura(cls):
        data = {
            'documento_rascunho_publico': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_publico': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
            ],
            'documento_concluido_publico': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
            ],
            'documento_finalizado_publico': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
            ],
            'documento_rascunho_restrito': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_restrito': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
            ],
            'documento_concluido_restrito': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
            ],
            'documento_finalizado_restrito': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
            ],
            'documento_rascunho_sigiloso': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_sigiloso': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_concluido_sigiloso': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_finalizado_sigiloso': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_processo_publico': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
                ['sdiatinf1', False],
            ],
            'documento_processo_restrito': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', True],
                ['chefe_gabin', True],
                ['sdiatinf1', False],
            ],
            'documento_processo_sigiloso': [
                ['coord_cosinf', False],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', True],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
                ['sdiatinf1', False],
            ],
        }

        for chave, lista in data.items():
            for usuario, resultado in lista:
                if cls.records[chave].tem_permissao_estrita_leitura(cls.records[usuario]) != resultado:
                    print('tem_permissao_estrita_leitura', chave, usuario, resultado)
                    assert False

    @classmethod
    def _tem_permissao_editar(cls):
        data = {
            'documento_rascunho_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_concluido_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_finalizado_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_rascunho_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_concluido_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_finalizado_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_rascunho_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_concluido_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_finalizado_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_processo_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
                ['sdiatinf1', False],
            ],
            'documento_processo_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
                ['sdiatinf1', False],
            ],
            'documento_processo_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
                ['sdiatinf1', False],
            ],
        }

        for chave, lista in data.items():
            for usuario, resultado in lista:
                if cls.records[chave].tem_permissao_editar(cls.records[usuario].user) != resultado:
                    print('tem_permissao_editar', chave, usuario, resultado)
                    assert False

    @classmethod
    def _pode_editar(cls):
        data = {
            'documento_rascunho_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_concluido_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_finalizado_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_rascunho_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_concluido_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_finalizado_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_rascunho_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_concluido_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_finalizado_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_processo_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
                ['sdiatinf1', False],
            ],
            'documento_processo_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
                ['sdiatinf1', False],
            ],
            'documento_processo_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
                ['sdiatinf1', False],
            ],
        }

        for chave, lista in data.items():
            for usuario, resultado in lista:
                if cls.records[chave].pode_editar(cls.records[usuario].user) != resultado:
                    print('pode_editar', chave, usuario, resultado)
                    assert False

    @classmethod
    def _pode_concluir_documento(cls):
        data = {
            'documento_rascunho_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_concluido_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_finalizado_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_rascunho_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_concluido_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_finalizado_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_rascunho_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', False],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_compartilhado_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_concluido_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_finalizado_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
            'documento_processo_publico': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_processo_restrito': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', True],
                ['scosinf1', True],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', True],
            ],
            'documento_processo_sigiloso': [
                ['coord_cosinf', True],
                ['coord_cosaad', False],
                ['diretor_digti', False],
                ['scosinf1', False],
                ['scosinf2', False],
                ['pcosinf3', False],
                ['proreitor_propi', False],
                ['diretor_cnat', True],
                ['proreitor_proex', False],
                ['chefe_gabin', False],
            ],
        }

        for chave, lista in data.items():
            for usuario, resultado in lista:
                if cls.records[chave].pode_concluir_documento(cls.records[usuario].user) != resultado:
                    print('pode_concluir_documento', chave, usuario, resultado)
                    assert False
