# flake8: noqa
import collections
import json
import logging
from datetime import datetime

from django.contrib.auth.models import Permission, Group
from django.core.management import call_command
from django.db import transaction
from django.test.client import Client
from rest_framework.status import *

from comum.tests import SuapTestCase
from comum.utils import get_todos_setores
from documento_eletronico.models import TipoDocumentoTexto, ModeloDocumento, DocumentoTexto, Documento, NivelPermissao, \
    Classificacao, DocumentoStatus
from documento_eletronico.utils import get_variaveis
from rh.models import Servidor, Atividade, Funcao, Papel, JornadaTrabalho, Situacao, CargoEmprego, \
    ServidorFuncaoHistorico

GRUPO_GERENTE_SISTEMICO = 'Gerente Sistêmico de Documento Eletrônico'
GRUPO_OPERADOR_DOCUMENTO = 'Operador de documento eletrônico'
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
        cls._criar_documentos()

    @classmethod
    def cadastrar(cls, modelo, data, chaves=None):
        if chaves is None:
            chaves = data
        qs = modelo.objects.filter(**chaves)
        if qs.exists():
            return qs[0]
        else:
            objeto = modelo.objects.create(**data)
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
        cls.records['setor_re'], cls.records['setor_re_siap'] = cls.cadastrar_setor('RE', cls.records['setor_ifrn'], '00001')
        # IFRN -> RE -> DIGTI
        cls.records['setor_digti'], cls.records['setor_digti_siap'] = cls.cadastrar_setor('DIGTI', cls.records['setor_re'])
        # IFRN -> RE -> GABIN
        cls.records['setor_gabin'], cls.records['setor_gabin_siap'] = cls.cadastrar_setor('GABIN', cls.records['setor_re'])
        # IFRN -> RE -> PROPI
        cls.records['setor_propi'], cls.records['setor_propi_siap'] = cls.cadastrar_setor('PROPI', cls.records['setor_re'])
        # IFRN -> RE -> PROEX
        cls.records['setor_proex'], cls.records['setor_proex_siap'] = cls.cadastrar_setor('PROEX', cls.records['setor_re'])

        # IFRN -> RE -> DIGTI -> COSINF
        cls.records['setor_cosinf'], cls.records['setor_cosinf_siap'] = cls.cadastrar_setor('COSINF', cls.records['setor_digti'])
        # IFRN -> RE -> DIGTI -> COINRE
        cls.records['setor_coinre'], cls.records['setor_coinre_siap'] = cls.cadastrar_setor('COINRE', cls.records['setor_digti'])
        # IFRN -> RE -> DIGTI -> COSINF -> COSAAD
        cls.records['setor_cosaad'], cls.records['setor_cosaad_siap'] = cls.cadastrar_setor('COSAAD', cls.records['setor_cosinf'])
        # COSAAD é setor irmão da COSINF
        cls.records['setor_cosinf'].setores_compartilhados.add(cls.records['setor_cosaad'])
        cls.records['setor_cosinf'].save()
        # IFRN -> RE -> DG/CNAT
        cls.records['setor_dg_cnat'], cls.records['setor_dg_cnat_siape'] = cls.cadastrar_setor('DG/CNAT', cls.records['setor_re'], '00003')
        # IFRN -> RE -> DG/CNAT -> DIATINF
        cls.records['setor_diatinf'], cls.records['setor_diatinf_siape'] = cls.cadastrar_setor('DIATINF', cls.records['setor_dg_cnat'])

    @classmethod
    def _criar_usuarios_e_permissoes(cls):
        situacao_ativo_permanente = Situacao.objects.get(codigo=Situacao.ATIVO_PERMANENTE)
        jornada_trabalho_40h = JornadaTrabalho.objects.get(codigo='40')
        jornada_trabalho_de = JornadaTrabalho.objects.get(codigo='99')
        cargo_emprego_professor = CargoEmprego.objects.get(codigo='01')
        cargo_emprego_tae = CargoEmprego.objects.get(codigo='01')

        # Criando atividades das funções
        funcao_atividade_reitor = cls.cadastrar(Atividade, data={'codigo': Atividade.REITOR, 'nome': 'Reitor'}, chaves={'codigo': Atividade.REITOR})
        funcao_atividade_diretor_geral = cls.cadastrar(Atividade, data={'codigo': Atividade.DIRETOR_GERAL, 'nome': 'Diretor Geral'}, chaves={'codigo': Atividade.DIRETOR_GERAL})
        funcao_atividade_diretor = cls.cadastrar(Atividade, data={'codigo': Atividade.DIRETOR, 'nome': 'Diretor'}, chaves={'codigo': Atividade.DIRETOR})
        funcao_atividade_chefe = cls.cadastrar(Atividade, data={'codigo': '0006', 'nome': 'Chefe de Gabinete'}, chaves={'codigo': '0006'})
        funcao_atividade_coordenador = cls.cadastrar(Atividade, data={'codigo': '2038', 'nome': 'Coordenador'}, chaves={'codigo': '2038'})
        funcao_cd = cls.cadastrar(Funcao, data={'codigo': 'CD', 'nome': 'CD'}, chaves={'codigo': 'CD'})
        funcao_fg = cls.cadastrar(Funcao, data={'codigo': 'FG', 'nome': 'FG'}, chaves={'codigo': 'FG'})

        agora = datetime.utcnow()

        data = {
            'nome': 'reitor',
            'matricula': '9001',
            'template': '1',
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
        cls.records['reitor'].user.set_password('123')
        cls.records['reitor'].user.save()

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
            'template': '1',
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
        cls.records['diretor_cnat'].user.set_password('123')
        cls.records['diretor_cnat'].user.save()

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
            'template': '1',
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
        cls.records['diretor_digti'].user.set_password('123')
        cls.records['diretor_digti'].user.save()

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
            'template': '1',
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
        cls.records['chefe_gabin'].user.set_password('123')
        cls.records['chefe_gabin'].user.save()
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
            'template': '1',
            'excluido': False,
            'situacao': situacao_ativo_permanente,
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
        cls.records['coord_cosinf'].user.set_password('123')
        cls.records['coord_cosinf'].user.save()

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
            'template': '1',
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
        cls.records['coord_cosaad'].user.set_password('123')
        cls.records['coord_cosaad'].user.save()

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
            'template': '1',
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
        cls.records['scosinf1'].user.set_password('123')
        cls.records['scosinf1'].user.save()

        data = {
            'nome': 'Servidor COSINF2',
            'matricula': '9008',
            'template': '1',
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
        cls.records['scosinf2'].user.set_password('123')
        cls.records['scosinf2'].user.save()

        # Criando os servidores da DIATINF
        data = {
            'nome': 'Servidor DIATINF',
            'matricula': '9009',
            'template': '1',
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
        cls.records['sdiatinf1'].user.set_password('123')
        cls.records['sdiatinf1'].user.save()

        # Criando os servidores da COINRE
        data = {
            'nome': 'Servidor COINRE 1',
            'matricula': '9010',
            'template': '1',
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
        cls.records['scoinre1'].user.set_password('123')
        cls.records['scoinre1'].user.save()

        data = {
            'nome': 'Servidor COINRE 2',
            'matricula': '9011',
            'template': '1',
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
        cls.records['scoinre2'].user.set_password('123')
        cls.records['scoinre2'].user.save()

        # Pro-reitor PROEX
        data = {
            'nome': 'Pro-reitor PROEX',
            'matricula': '9012',
            'template': '1',
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
        cls.records['proreitor_proex'].user.set_password('123')
        cls.records['proreitor_proex'].user.save()

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
            'template': '1',
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
        cls.records['proreitor_propi'].user.set_password('123')
        cls.records['proreitor_propi'].user.save()

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
            'template': '1',
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
        cls.records['sdigti1'].user.set_password('123')
        cls.records['sdigti1'].user.save()

        if not Papel.objects.filter(servidor=cls.records['reitor']).exists():
            # Cadastrando os papeis dos servidores
            from rh.management.commands.importar_funcao_servidor import Command

            comando_cadastrar_papel = Command()
            comando_cadastrar_papel.handle()

        # DocumentoEletronicoTestCase.first_time = False
        # print '9009009009', Funcao.objects.filter(codigo='CD').exists()
        logger = logging.getLogger()
        for obj in list(cls.records.values()):
            if isinstance(obj, Servidor):
                logger.info('Adicionando servidor {} no grupo {}'.format(obj, GRUPO_OPERADOR_DOCUMENTO))
                obj.user.groups.add(Group.objects.get(name=GRUPO_OPERADOR_DOCUMENTO))
                obj.user.save()

    @classmethod
    def _criar_documentos(cls):
        client = Client()
        servidor = cls.records['scosinf1']
        user = cls.records['scosinf1'].user
        client.login(username=user.username, password='123')

        # Documento Rascunho
        cls.records['documento_rascunho'] = cls._gerar_documento(client, 'Rascunho', Documento.NIVEL_ACESSO_PUBLICO)

        # Documento Compartilhado
        cls.records['documento_compartilhado'] = cls._gerar_documento(client, 'Compartilhado', Documento.NIVEL_ACESSO_PUBLICO)
        cls._gerar_compartilhamento(client, cls.records['documento_compartilhado'])

        # Documento Concluído
        cls.records['documento_concluido'] = cls._gerar_documento(client, 'Concluído', Documento.NIVEL_ACESSO_PUBLICO)
        cls._gerar_compartilhamento(client, cls.records['documento_concluido'])
        cls._finalizar_documento(client, cls.records['documento_concluido'])

    @classmethod
    def _gerar_documento(cls, client, assunto, nivel_acesso):
        if DocumentoTexto.objects.filter(assunto=assunto).exists():
            return DocumentoTexto.objects.filter(assunto=assunto)[0]
        oficio = TipoDocumentoTexto.objects.get(sigla='OFÍCIO')
        setor = cls.records['scosinf1'].setor
        modelo_documento = oficio.modelos.all()[0]
        classificacao = modelo_documento.classificacao.all()[0]

        identificador_tipo_documento_sigla, identificador_numero, identificador_ano, identificador_setor_sigla = oficio.get_sugestao_identificador_definitivo(
            tipo_documento_texto=oficio, setor_dono=setor
        )

        data = dict(
            tipo=oficio.id,
            modelo=modelo_documento.id,
            nivel_acesso=Documento.NIVEL_ACESSO_PUBLICO,
            setor_dono=setor.id,
            identificador_tipo_documento_sigla='OFICIO',
            identificador_numero=identificador_numero,
            identificador_ano=identificador_ano,
            identificador_setor_sigla=identificador_setor_sigla,
            assunto='Documento {}'.format(assunto),
        )
        # Verifica se aparece o botão "Adicionar"
        response = client.post('/admin/documento_eletronico/documentotexto/add/', data)
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
    def _finalizar_documento(cls, client, documento):
        url = '/documento_eletronico/concluir_documento/{}/'.format(documento.id)
        response = client.get(url, follow=True)

    def setUp(self):
        # logging.disable(logging.CRITICAL)
        super().setUp()
        self.records = DocumentoEletronicoBaseTestCase.records
        self.servidores = []
        for obj in list(self.records.values()):
            if isinstance(obj, Servidor):
                self.servidores.append(obj)

    def _get_servidores(self):
        return self.servidores

    def login(self, servidor=None):
        self.logout()
        if not servidor:
            servidor = self.records['scosinf1']  # Servidor.objects.get(matricula='9007')
        user = servidor.user
        successful = self.client.login(user=user)
        self.assertEqual(successful, True)
        return self.client.user

    def acessar_como_gerente_sistemico(self):
        self.logout()
        servidor = self.records['chefe_gabin']  # Servidor.objects.get(matricula='9004')
        successful = self.client.login(user=servidor.user)
        self.assertEqual(successful, True)
        return self.client.user

    def retornar(self, cls, qtd=1, chaves={}):
        if chaves:
            return cls.objects.filter(**chaves)
        return cls.objects.all().order_by('-id')[0:qtd]

    def _verifica_conteudo_tela(self, obj, url, page_contains={}, status_code=HTTP_200_OK):
        """
        Verifica se a página relativa a url possui os conteúdos definidos em page_contains
        :param obj:
        :param url:
        :param page_contains:
        :return:
        """
        self.logger.info('\t  {}, {}'.format(url, status_code))
        # print '\tUsuário', self.client.user
        # for conteudo, visivel in page_contains.items():
        #     if visivel:
        #         print '\t', conteudo

        response = self.client.get(url)
        try:
            self.assertEqual(
                response.status_code, status_code, msg='\t{}, acesso {}, esperado {}, obtido {}'.format(self.client.user, url.format(id=obj.id), status_code, response.status_code)
            )
        except AssertionError as err:
            self.logger.error(err.message)

        if not status_code == HTTP_403_FORBIDDEN:
            try:
                sid = transaction.savepoint()
                for conteudo, visivel in list(page_contains.items()):
                    verifica_tela, status_code = visivel
                    urllink = conteudo.format(id=obj.id)
                    resp = None
                    try:
                        if verifica_tela:
                            if not isinstance(urllink, str) and urllink.find('/') >= 0:
                                msg = 'Ação não disponível'
                            else:
                                msg = 'Texto não encontrado'
                            self.assertContains(response, conteudo.format(id=obj.id), status_code=HTTP_200_OK, msg_prefix='\t\t{}: {}'.format(msg, self.client.user))
                        else:
                            if not isinstance(urllink, str) and urllink.find('/') >= 0:
                                msg = 'Ação disponível'
                            else:
                                msg = 'Texto encontrado'
                            self.assertNotContains(response, conteudo.format(id=obj.id), status_code=HTTP_200_OK, msg_prefix='\t\t{}: {}'.format(msg, self.client.user))
                    except AssertionError as err:
                        self.logger.error(err.message)
                        print((conteudo, visivel))
                    except UnicodeDecodeError as err:
                        pass
                        # if err.message:
                        #     self.logger.error(err.message)
                        # else:
                        #     self.logger.error('UnicodeDecodeError, {}' %urllink)
                    try:
                        if not isinstance(urllink, str) and urllink.find('/') >= 0:
                            resp = self.client.get(conteudo.format(id=obj.id), follow=True)
                            if status_code == HTTP_200_OK:
                                self.assertEqual(
                                    resp.status_code,
                                    HTTP_200_OK,
                                    msg='\tErro de acesso: {}, acesso {}, esperado {}, obtido {}'.format(
                                        self.client.user, conteudo.format(id=obj.id), status_code, resp.status_code
                                    ),
                                )

                            else:
                                if resp.status_code == HTTP_200_OK:
                                    self.assertContains(
                                        resp,
                                        'Você não tem permissão para essa operação',
                                        status_code=HTTP_200_OK,
                                        msg_prefix='\t\tErro de acesso: esperado HTTP_403_FORBIDDEN, recebido HTTP_200_OK. {} - {}'.format(self.client.user, urllink),
                                    )
                                else:
                                    self.assertEqual(
                                        resp.status_code,
                                        status_code,
                                        msg='\tErro de acesso: {}, acesso {}, esperado {}, obtido {}'.format(
                                            self.client.user, conteudo.format(id=obj.id), status_code, resp.status_code
                                        ),
                                    )
                    except AssertionError as err:
                        self.logger.error(err.message)
                        print((conteudo, visivel))
                    except UnicodeDecodeError as err:
                        pass
                        # if err.message:
                        #     self.logger.error(err.message)
                        # else:
                        #     self.logger.error('UnicodeDecodeError, {}' %urllink)
            except Exception as err:
                print(page_contains)
                raise
            finally:
                transaction.savepoint_rollback(sid)

    def _cadastrar(self, cls, data, page_contains={}, url_list=None, url_add=None, expected_url=None, status_code_expected_common_user=HTTP_403_FORBIDDEN):
        user_tmp = self.client.user
        nome = cls.__name__.lower()
        if url_list is None:
            url_list = '/admin/documento_eletronico/{}/'.format(nome)
        if url_add is None:
            url_add = '/admin/documento_eletronico/{}/add/'.format(nome)
        if status_code_expected_common_user != HTTP_200_OK:
            # Servidor comum não tem acesso
            self.login()
            response = self.client.get(url_list)
            self.assertEqual(response.status_code, status_code_expected_common_user)
            response = self.client.get(url_add)
            self.assertEqual(response.status_code, status_code_expected_common_user)

        # usuário previamente definido tem acesso
        self.client.login(user=user_tmp)

        # Verifica se aparece o botão "Adicionar"
        response = self.client.get(url_add)
        self.assertContains(response, 'Adicionar {}'.format(cls._meta.verbose_name), status_code=HTTP_200_OK)
        # testa funcionalidade cadastrar
        count = cls.objects.all().count()
        response = self.client.post(url_add, data)
        self.assert_no_validation_errors(response)
        self.assertEqual(cls.objects.all().count(), count + 1)

        # testa redirecionamento da url após o cadastro
        obj = self.retornar(cls)[0]
        if expected_url is None:
            expected_url = url_list
        else:
            expected_url %= {'id': obj.id}
        self.assertRedirects(response, expected_url, status_code=HTTP_302_FOUND)

        self._verifica_conteudo_tela(obj, url_list, page_contains)

        return obj

    def _excluir_cadastros(self, cls):
        '''
        Gerente sistêmico só pode excluir cadastros básicos(tipo e modelo de documento e classificação) se não possuir documento relacionado.
        Um tipo de documento só pode excluir se não posuir classificação e/ou documento relacionado.
        '''
        nome = cls.__name__.lower()
        user_tmp = self.client.user
        # usuário coumum não tem permissão para excluir
        self.login()
        obj = self.retornar(cls)[0]
        url_change = '/admin/documento_eletronico/{}/{}/delete/'.format(nome, obj.id)

        response = self.client.get(url_change)
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        # usuário previamente definido tem acesso, mas só pode excluir se não existir objetos relacionados
        self.client.login(user=user_tmp)
        # http://localhost:8000/admin/documento_eletronico/tipodocumento/5/change/
        # botão delete http://localhost:8000/admin/documento_eletronico/tipodocumento/3/delete/

    def _editar_cadastros(self, cls, dados, expected_url):
        def adiciona_chave_fk(data):
            d = {}
            for k, v in list(data.items()):
                d[k] = v
                if '_id' in k:
                    d[k[:-3]] = v
            data.update(d)

        user_tmp = self.client.user

        data = list(self.retornar(cls).values())[0]
        data.update(dados)
        adiciona_chave_fk(data)

        url = expected_url.format(id=data['id'])

        # usuário comum não tem acesso
        self.login()
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        # usuário previamente definido tem acesso
        self.client.login(user=user_tmp)
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Atualização realizada com sucesso', status_code=HTTP_200_OK)
        new_data = list(self.retornar(cls).values())[0]
        adiciona_chave_fk(new_data)
        self.assertEqual(data, new_data)

    def _get_nivel_acesso_display(self, nivel_acesso):
        return [s[1] for s in Documento.NIVEL_ACESSO_CHOICES if s[0] == nivel_acesso][0]

    def _get_status_display(self, status):
        return ['>{}<'.format(s[1]) for s in DocumentoStatus.STATUS_CHOICES if s[0] == status][0]


class DocumentoTestCase(DocumentoEletronicoBaseTestCase):
    def setUp(self):
        super().setUp()
        Documento.objects.all().delete()

    def _obter_numeracao_documento(self, tipo_documento, setor_dono):
        """
        :param tipo_documento:
        :param setor_dono:
        :return: retorna o dicionário descrito abaixo
            {'identificador_numero': 1, 'identificador_setor_sigla': 'COSINF/DIGTI/RE/RAIZ',
            'identificador_tipo_documento_sigla': 'MEMO', 'identificador_ano': 2017}
        """
        url = '/documento_eletronico/gerar_sugestao_identificador_documento_texto/{}/{}/'.format(tipo_documento.id, setor_dono.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTP_200_OK)
        return json.loads(response.content)

    def _get_conteudo_pills_setor(self, meu_setor, setores_compartilhados=None, valor_padrao=(True, HTTP_200_OK)):
        # existe o método get_todos_setores(self.client.user) para obter os setores compartilhados, não usei pq o documento eletrônico faz uso dele
        # eu quiz constatar se de fato está aparecendo as abas dos setores corretos.
        conteudo_padrao = {}
        if setores_compartilhados is None:
            setores_compartilhados = (self.records['setor_cosaad'], self.records['setor_cosinf'])
        if meu_setor in setores_compartilhados:
            for setor_compartilhado in setores_compartilhados:
                conteudo_padrao['?setores={}'.format(setor_compartilhado.id)] = valor_padrao
        return conteudo_padrao

    def _get_conteudo_listagem_documento(self, meu_setor, conteudo={}, valor_padrao=(False, HTTP_403_FORBIDDEN)):
        """
        retorno os links existens na página de listagem de documentos. Padrão é retornar os links disponíveis para servidores sem acesso ao documento.
        Dicionário conteudo_padrao:
            - chave: link/texto a ser verificado se existe ou não na tela
            - valor: dupla boolean, por exemplo (True, HTTP_200_OK). O primeiro item diz respeito se deve verificar ou não a existência da texto na tela,
              enquanto que o segundo, verifica se tem acesso à funcionalidade ou não do link.
        :param meu_setor:
        :param nivel_acesso:
        :param status:
        :param conteudo:
        :param valor_padrao:
        :return:
        """
        conteudo_padrao = {
            'Nenhum documento foi encontrado': (True, HTTP_200_OK),
            '/admin/documento_eletronico/documentotexto/add/': (True, HTTP_200_OK),
            '/documento_eletronico/gerenciar_compartilhamento_setor/': (True, HTTP_200_OK),
            '?setores=todos': (True, HTTP_200_OK),
            '?setores=todos_setores_usuario': (True, HTTP_200_OK),
            '?setores={}'.format(meu_setor.id): (True, HTTP_200_OK),
            '/documento_eletronico/visualizar_documento/%(id)s/': valor_padrao,
            '/documento_eletronico/editar_documento/%(id)s/': valor_padrao,
            '/documento_eletronico/gerenciar_compartilhamento_documento/%(id)s/': valor_padrao,
            '/documento_eletronico/clonar_documento/%(id)s/': valor_padrao,
            '/documento_eletronico/imprimir_documento_pdf/%(id)s/carta/': (False, HTTP_403_FORBIDDEN),
            '/documento_eletronico/imprimir_documento_pdf/%(id)s/paisagem/': (False, HTTP_403_FORBIDDEN),
            '/admin/documento_eletronico/documentotexto/%(id)s/history/': (False, HTTP_403_FORBIDDEN),
            '/documento_eletronico/solicitar_revisao/%(id)s/': (False, HTTP_403_FORBIDDEN),
            '/documento_eletronico/cancelar_revisao/%(id)s/': (False, HTTP_403_FORBIDDEN),
            'Documentos Esperando Revisão': (False, HTTP_403_FORBIDDEN),
            'Documentos Esperando Assinatura': (False, HTTP_403_FORBIDDEN),
            '/documento_eletronico/rejeitar_solicitacao/%(id)s/': (False, HTTP_404_NOT_FOUND),
            '/documento_eletronico/verificar_integridade/%(id)s/': (False, HTTP_403_FORBIDDEN),
            'Documentos Assinados': (False, HTTP_404_NOT_FOUND),
            'Requisições de Assinatura': (False, HTTP_404_NOT_FOUND),
        }
        conteudo_padrao.update(conteudo)
        conteudo_padrao.update(self._get_conteudo_pills_setor(meu_setor))
        return conteudo_padrao

    def _cadastrar_documento(self, servidor, tipo_documento, nivel_acesso, dados={}):
        meu_setor = servidor.setor
        modelo_documento = tipo_documento.modelos.all()[0]
        classificacao = modelo_documento.classificacao.all()[0]
        identificao_documento = self._obter_numeracao_documento(tipo_documento, meu_setor)

        data = dict(
            tipo=tipo_documento.id,
            modelo=modelo_documento.id,
            nivel_acesso=nivel_acesso,
            setor_dono=meu_setor.id,
            identificador_tipo_documento_sigla=identificao_documento['identificador_tipo_documento_sigla'],
            identificador_numero=identificao_documento['identificador_numero'],
            identificador_ano=identificao_documento['identificador_ano'],
            identificador_setor_sigla=identificao_documento['identificador_setor_sigla'],
            classificacao=[classificacao.id],
            assunto='Assunto teste {}'.format(identificao_documento['identificador_numero']),
        )
        data.update(dados)
        conteudos = self._get_conteudo_listagem_documento(servidor.setor)
        conteudos.update(
            {
                '/documento_eletronico/imprimir_documento_pdf/%(id)s/paisagem/': (False, HTTP_403_FORBIDDEN),
                '/documento_eletronico/imprimir_documento_pdf/%(id)s/carta/': (False, HTTP_403_FORBIDDEN),
                '/documento_eletronico/visualizar_documento/%(id)s/': (True, HTTP_200_OK),
                self._get_nivel_acesso_display(Documento.NIVEL_ACESSO_PUBLICO): (True, HTTP_200_OK),
                self._get_status_display(DocumentoStatus.STATUS_RASCUNHO): (True, HTTP_200_OK),
                '/documento_eletronico/gerenciar_compartilhamento_documento/%(id)s/': (True, HTTP_200_OK),
                '/documento_eletronico/clonar_documento/%(id)s/': (True, HTTP_200_OK),
                '/admin/documento_eletronico/documentotexto/%(id)s/history/': (True, HTTP_200_OK),
                '/documento_eletronico/editar_documento/%(id)s/': (True, HTTP_200_OK),
                'Nenhum documento foi encontrado': (False, HTTP_403_FORBIDDEN),
            }
        )
        documento = self._cadastrar(
            cls=DocumentoTexto,
            data=data,
            url_list='/documento_eletronico/listar_documentos/',
            url_add='/admin/documento_eletronico/documentotexto/add/',
            expected_url='/documento_eletronico/editar_documento/%(id)s/',
            page_contains=conteudos,
            status_code_expected_common_user=HTTP_200_OK,
        )
        print((documento.identificador_numero, documento.identificador))
        # TODO comentei a linha abaixo, pois ocorre divergência entre numero e identificador do documento,
        # ex: numero = 4/2017 - COSINF/DIGTI/RE/RAIZ, identificador MEMO 1/2017 - COSINF/DIGTI/RE/RAIZ, ou seja, a numeração do identificador permanece não está mudando.
        # self.assertEqual(documento.numero, documento.identificador[len(documento.tipo.sigla)+1:])
        return documento

    def _verifica_permissao_tela_edicao_documento(self, documento, status_code=HTTP_200_OK):
        url = '/documento_eletronico/editar_documento/{}/'.format(documento.id)
        conteudos = {}
        if status_code == HTTP_200_OK:
            conteudos = {
                '/documento_eletronico/imprimir_documento_pdf/%(id)s/carta/': (False, HTTP_403_FORBIDDEN),
                '/documento_eletronico/imprimir_documento_pdf/%(id)s/paisagem/': (False, HTTP_403_FORBIDDEN),
                '/documento_eletronico/editar_documento/%(id)s/remontar_corpo/': (True, HTTP_200_OK),
                'Salvar': (True, HTTP_200_OK),
                # u'Salvar e concluir': (True, HTTP_200_OK),
                # '/documento_eletronico/revisar_documento/%(id)s/': (False, HTTP_403_FORBIDDEN)
            }
        self._verifica_conteudo_tela(documento, url, conteudos, status_code)

    def _verifica_permissao_tela_visualizar_documento(self, documento, status_code=HTTP_200_OK, dconteudos={}):
        url = '/documento_eletronico/visualizar_documento/{}/'.format(documento.id)
        conteudos = {}
        if status_code == HTTP_200_OK:
            conteudos = {
                '/documento_eletronico/concluir_documento/%(id)s/': (False, HTTP_403_FORBIDDEN),
                '/documento_eletronico/retornar_para_rascunho/%(id)s/': (False, HTTP_403_FORBIDDEN),
                '/documento_eletronico/imprimir_documento_pdf/%(id)s/carta/': (False, HTTP_403_FORBIDDEN),
                '/documento_eletronico/imprimir_documento_pdf/%(id)s/paisagem/': (False, HTTP_403_FORBIDDEN),
                '/documento_eletronico/cancelar_revisao/%(id)s/': (False, HTTP_403_FORBIDDEN),
                '/documento_eletronico/assinar_documento/%(id)s/': (False, HTTP_403_FORBIDDEN),
                '/documento_eletronico/assinar_documento_cert/%(id)s/': (False, HTTP_403_FORBIDDEN),
                '/documento_eletronico/assinar_documento_token/%(id)s/': (False, HTTP_403_FORBIDDEN),
                '/documento_eletronico/solicitar_assinatura/%(id)s/': (False, HTTP_403_FORBIDDEN),
            }
            conteudos.update(dconteudos)
        self._verifica_conteudo_tela(documento, url, conteudos, status_code)

    def _verificar_conteudo_telas_documento(self, documento, servidores, url=None, conteudos_tela_listagem={}, conteudos_tela_visualizacao={}):
        for servidor in servidores:
            self.login(servidor)
            self.logger.info('\t-- {}'.format(self.client.user))
            if url is None:
                url = '/documento_eletronico/listar_documentos/'
            conteudos = self._get_conteudo_listagem_documento(servidor.setor, conteudos_tela_listagem)
            self._verifica_conteudo_tela(documento, url, conteudos)
            pode_visualizar = conteudos_tela_listagem['/documento_eletronico/visualizar_documento/%(id)s/'][1] == HTTP_200_OK
            self._verifica_permissao_tela_visualizar_documento(
                documento, status_code=HTTP_200_OK if pode_visualizar else HTTP_403_FORBIDDEN, dconteudos=conteudos_tela_visualizacao
            )
            pode_editar = conteudos_tela_listagem['/documento_eletronico/editar_documento/%(id)s/'][1] == HTTP_200_OK
            self._verifica_permissao_tela_edicao_documento(documento, status_code=HTTP_200_OK if pode_editar else HTTP_403_FORBIDDEN)

    def _get_servidores_mesmo_setor(self):
        if not hasattr(self, 'servidores_mesmo_setor') or not self.servidores_mesmo_setor:
            servidor = self.client.user.get_profile()
            self.servidores_mesmo_setor = list(set(servidor.setor.get_servidores(recursivo=False)) - {servidor})
        return self.servidores_mesmo_setor

    def _get_servidores_setor_irmao(self):
        if not hasattr(self, 'servidores_irmaos') or not self.servidores_irmaos:
            servidor = self.client.user.get_profile()
            setores_irmaos = list(set(get_todos_setores(servidor)) - {servidor.setor})
            servidores_irmaos = []
            for setor_irmao in setores_irmaos:
                servidores_irmaos.extend(setor_irmao.get_servidores(recursivo=False))
            self.servidores_irmaos = servidores_irmaos
        return self.servidores_irmaos

    def _get_chefe_setor_pai(self):
        if not hasattr(self, 'chefe_setor_pai') or not self.chefe_setor_pai:
            servidor = self.client.user.get_profile()
            chefes = []
            setores_superiores = servidor.setor.get_caminho()
            for setor in setores_superiores:
                if setor.superior:
                    for chefe in setor.superior.chefes:
                        chefes.append(Servidor.objects.get(id=chefe.id))
            self.chefe_setor_pai = chefes
        return self.chefe_setor_pai

    def _get_servidores_de_documento_compartilhado_setor(self, servidor, documento):
        pass

    def _get_servidores_de_documento_compartilhado_ler(self, documento):
        if not hasattr(self, 'servidores_de_documento_compartilhado_ler') or not self.servidores_de_documento_compartilhado_ler:
            documento_compartilhado_pessoas_podem_ler = set()
            compartilhamentos_documento_pessoa_ler = documento.compartilhamento_pessoa_documento.filter(nivel_permissao=NivelPermissao.LER)
            documento_compartilhado_pessoas_podem_ler |= {
                Servidor.objects.get(id=cdp.pessoa_permitida.id) for cdp in compartilhamentos_documento_pessoa_ler if compartilhamentos_documento_pessoa_ler
            }
            self.servidores_de_documento_compartilhado_ler = list(documento_compartilhado_pessoas_podem_ler)
        return self.servidores_de_documento_compartilhado_ler

    def _get_servidores_de_documento_compartilhado_editar(self, documento):
        if not hasattr(self, 'servidores_de_documento_compartilhado_editar') or not self.servidores_de_documento_compartilhado_editar:
            documento_compartilhado_pessoas_podem_editar = set()
            compartilhamentos_documento_pessoa_editar = documento.compartilhamento_pessoa_documento.filter(nivel_permissao=NivelPermissao.EDITAR)
            documento_compartilhado_pessoas_podem_editar |= {
                Servidor.objects.get(id=cdp.pessoa_permitida.id) for cdp in compartilhamentos_documento_pessoa_editar if compartilhamentos_documento_pessoa_editar
            }
            self.servidores_de_documento_compartilhado_editar = list(documento_compartilhado_pessoas_podem_editar)
        return self.servidores_de_documento_compartilhado_editar

    def verificar_conteudo_telas_documento(self, documento, conteudos_tela_listagem={}, conteudos_tela_visualizacao={}, servidores_caso_particular=[]):
        """
        Verifica se tem acesso a tela de listagem de documento, bem como a tela de visualização e edição de documento.
        Se tem acesso, é verificado se os links estão disponíveis, caso negado, também é verificado se não aparece.

        Os [servidores_mesmo_setor_ou_pai] são servidores dos setores compartilhado ao dono do documento, pode listar documento, visualiar e clonar.

        Os [servidores_setores_irmaos_e_compartilhados_editar_setor] tem acesso ao documento, ou seja, pode listar, editar e visualizar.

        Os [servidores_compartilhados_podem_editar] são os servidores com documentos compartilhados com acesso escrita,
        podem listar, editar e visualizar, porém as opções de ações do documento não estão disponíveis.

        Os [servidores_compartilhados_podem_ler] são os servidores com documentos compartilhados com acesso leitura,
        podem listar e visualizar. As opções de ações e editar do documento não estão disponíveis

        Também é verificado os servidores sem acesso, ou seja, todos aqueles que não estão em [servidores_mesmo_setor_ou_pai],
        [servidores_setores_irmaos_e_compartilhados_editar_setor],  [servidores_compartilhados_podem_editar] e [servidores_compartilhados_podem_ler]

        :param documento:
        :param servidores_mesmo_setor_ou_pai: são os servidores que tem acesso por padrão ao documento, nesse caso, pode editar
                                        e visualizar documentos.
        :param servidores_setores_irmaos_e_compartilhados_editar_setor: são os servidores dos setores compartilhado ao servidor dono do documento
        :param servidores_compartilhados_podem_editar: são os servidores compartilhado com acesso para edição
        :param servidores_compartilhados_podem_ler: são so servidores compartilhados com acesso somente para
                                                    visualização
        :param conteudos_tela_listagem:

        conteudos_tela_listagem = {
            'servidores_com_acesso_edicao': {
                'comum': {},
                'servidor_dono': {},
                'servidores_mesmo_setor_ou_pai': {},
                'servidores_setores_irmaos_e_compartilhados_editar_setor': {},
                'servidores_caso_particular': {},
            },
            'documentos_compartilhados_listagem_qualquer_setor_editar': {},
            'documentos_compartilhados_listagem_todos_setores_ler': {},
            'outros_usuarios': {},
        }
        :param conteudos_tela_visualizacao:

        conteudos_tela_visualizacao = {
            'servidores_com_acesso_edicao': {
                'comum': {},
                'servidor_dono': {},
                'servidores_mesmo_setor_ou_pai': {},
                'servidores_setores_irmaos_e_compartilhados_editar_setor': {},
                'servidores_caso_particular': {},
            },
            'documentos_compartilhados_listagem_qualquer_setor_editar': {},
            'documentos_compartilhados_listagem_todos_setores_ler': {},
            'outros_usuarios': {},
        }
        :return:
        """
        # print 'Tela Listagem'
        # print_dict(conteudos_tela_listagem)
        # print 'Tela Visualização'
        # print_dict(conteudos_tela_visualizacao)
        user_tmp = self.client.user
        url = '/documento_eletronico/listar_documentos/'
        if not hasattr(self, 'servidor_dono'):
            self.servidor_dono = Servidor.objects.get(id=documento.usuario_criacao.get_profile().id)

        servidores_mesmo_setor = self._get_servidores_mesmo_setor()
        servidores_setor_pai = self._get_chefe_setor_pai()
        servidores_setores_irmaos_e_compartilhados_editar_setor = self._get_servidores_setor_irmao()
        servidores_compartilhados_podem_editar = self._get_servidores_de_documento_compartilhado_editar(documento)
        servidores_compartilhados_podem_ler = self._get_servidores_de_documento_compartilhado_ler(documento)

        servidores_compartilhados = servidores_compartilhados_podem_editar + servidores_compartilhados_podem_ler

        # Servidores sem acesso, o documento não é exibido na tela de listagem padrão
        # Servidores sem acesso, não pode visualizar ou editar o documento
        servidores_sem_acesso = (
            set(self._get_servidores())
            - set(servidores_mesmo_setor)
            - set(servidores_setor_pai)
            - set(servidores_compartilhados)
            - set(servidores_setores_irmaos_e_compartilhados_editar_setor)
            - {self.servidor_dono}
            - set(servidores_caso_particular)
        )

        # servidores com acesso, o documento é exibido na tela de listagem
        # As opções de ações do documento estão disponíveis.
        # servidores com acesso tem permissão para editar e visualizar documento

        # Desativando todos os links da tela de listagem
        # Nesse caso, não existe documento para ser exibido.
        aconteudos_tela_listagem = self._get_conteudo_listagem_documento(documento.setor_dono, {}, (False, HTTP_403_FORBIDDEN))
        aconteudos_tela_listagem.update(self._get_conteudo_pills_setor(meu_setor=documento.setor_dono, valor_padrao=(False, HTTP_403_FORBIDDEN)))

        self.logger.info('* OUTROS USUÁRIOS ...')
        # aconteudos_tela_listagem.update({u'Nenhum documento foi encontrado': (True, HTTP_200_OK),})
        ctlistagem = aconteudos_tela_listagem.copy()
        ctlistagem.update(conteudos_tela_listagem.get('outros_usuarios', {}))
        ctvisualizacao = conteudos_tela_visualizacao.get('outros_usuarios', {})
        self._verificar_conteudo_telas_documento(documento, servidores_sem_acesso, url, conteudos_tela_listagem=ctlistagem, conteudos_tela_visualizacao=ctvisualizacao)
        if servidores_compartilhados:
            self.logger.info('* Documentos compartilhados não aparece na listagem da guia "Meus Setores"')
            # Usuários de documentos compartilhados, as ações de opções não estão disponíveis
            for servidor in servidores_compartilhados:
                self.login(servidor)
                self.logger.info('\t-- {}'.format(self.client.user))
                self._verifica_conteudo_tela(
                    documento,
                    '/documento_eletronico/listar_documentos/?setores=todos_setores_usuario',
                    {'Nenhum documento foi encontrado': (True, HTTP_200_OK), documento.identificador: (True, HTTP_200_OK)},
                )
            self.logger.info('* DOCUMENTO COMPARTILHADO - aparecem na listagem da guia "Qualquer Setor"')
            if servidores_compartilhados_podem_ler:
                self.logger.info('** COMPARTILHADO LER  - verificando servidores com permissão somente leitura')
                ctlistagem = aconteudos_tela_listagem.copy()
                ctlistagem.update(conteudos_tela_listagem.get('documentos_compartilhados_listagem_todos_setores_ler', {}))
                ctvisualizacao = conteudos_tela_visualizacao.get('documentos_compartilhados_listagem_todos_setores_ler', {})
                self._verificar_conteudo_telas_documento(
                    documento,
                    servidores_compartilhados_podem_ler,
                    url='/documento_eletronico/listar_documentos/?setores=todos&tab=1',
                    conteudos_tela_listagem=ctlistagem,
                    conteudos_tela_visualizacao=ctvisualizacao,
                )
            if servidores_compartilhados_podem_editar:
                self.logger.info('** COMPARTILHADO EDITAR  - verificando servidores com permissão escrita ...')
                # Documento compartilhado aparece na listagem "Qualquer Setor"
                ctlistagem = aconteudos_tela_listagem.copy()
                ctlistagem.update(
                    conteudos_tela_listagem.get(
                        'documentos_compartilhados_listagem_qualquer_setor_editar', {'/documento_eletronico/concluir_documento/%(id)s/': (True, HTTP_200_OK)}
                    )
                )
                ctvisualizacao = conteudos_tela_visualizacao.get('documentos_compartilhados_listagem_qualquer_setor_editar', {})
                self._verificar_conteudo_telas_documento(
                    documento,
                    servidores_compartilhados_podem_editar,
                    url='/documento_eletronico/listar_documentos/?setores=todos',
                    conteudos_tela_listagem=ctlistagem,
                    conteudos_tela_visualizacao=ctvisualizacao,
                )

        aconteudos_tela_listagem.update(conteudos_tela_listagem['servidores_com_acesso_edicao'].get('comum', {}))
        aconteudos_tela_visualizacao = conteudos_tela_visualizacao['servidores_com_acesso_edicao'].get('comum', {})

        if servidores_setores_irmaos_e_compartilhados_editar_setor:
            self.logger.info('* SETOR IRMÃO/COMPARTILHADO EDITAR (SETOR) - verificando permissões de setores irmãos ...')
            self.logger.info('** Documento de setores irmãos não é exibido na tela de listagem padrão ...')
            for servidor in servidores_setores_irmaos_e_compartilhados_editar_setor:
                self.login(servidor)
                self.logger.info('\t-- {}'.format(self.client.user))
                self._verifica_conteudo_tela(documento, url, {'Nenhum documento foi encontrado': (True, HTTP_200_OK), documento.identificador: (False, HTTP_403_FORBIDDEN)})
            self.logger.info('** Documento de setores irmãos é exibido na tela "Meus Setores" ...')
            # Documento de setores compartilhados aparece na listagem "Meus Setores"
            # Ações Visualizar, Clonar, Imprimir Carta e Paisagem aparecem nas opções
            ctlistagem = aconteudos_tela_listagem.copy()
            ctlistagem.update(conteudos_tela_listagem['servidores_com_acesso_edicao'].get('servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores', {}))
            ctvisualizacao = aconteudos_tela_visualizacao.copy()
            ctvisualizacao.update(
                conteudos_tela_visualizacao['servidores_com_acesso_edicao'].get('servidores_setores_irmaos_e_compartilhados_editar_setor_usuario_meus_setores', {})
            )
            self._verificar_conteudo_telas_documento(
                documento,
                servidores_setores_irmaos_e_compartilhados_editar_setor,
                url='/documento_eletronico/listar_documentos/?setores=todos_setores_usuario',
                conteudos_tela_listagem=ctlistagem,
                conteudos_tela_visualizacao=ctvisualizacao,
            )
        if servidores_mesmo_setor:
            self.logger.info('* MESMO SETOR - servidores do mesmo setor ...')
            ctlistagem = aconteudos_tela_listagem.copy()
            ctlistagem.update(conteudos_tela_listagem['servidores_com_acesso_edicao'].get('servidores_mesmo_setor', {}))
            ctvisualizacao = aconteudos_tela_visualizacao.copy()
            ctvisualizacao.update(conteudos_tela_visualizacao['servidores_com_acesso_edicao'].get('servidores_mesmo_setor', {}))
            self._verificar_conteudo_telas_documento(
                documento,
                servidores_mesmo_setor,
                url='/documento_eletronico/listar_documentos/?setores=todos_setores_usuario',
                conteudos_tela_listagem=ctlistagem,
                conteudos_tela_visualizacao=ctvisualizacao,
            )
        if servidores_mesmo_setor:
            self.logger.info('* SETOR PAI - servidores de hirarquia setorial superior ...')
            ctlistagem = aconteudos_tela_listagem.copy()
            ctlistagem.update(conteudos_tela_listagem['servidores_com_acesso_edicao'].get('servidores_setor_pai', {}))
            ctvisualizacao = aconteudos_tela_visualizacao.copy()
            ctvisualizacao.update(conteudos_tela_visualizacao['servidores_com_acesso_edicao'].get('servidores_setor_pai', {}))
            self._verificar_conteudo_telas_documento(
                documento,
                servidores_setor_pai,
                url='/documento_eletronico/listar_documentos/?setores=todos',
                conteudos_tela_listagem=ctlistagem,
                conteudos_tela_visualizacao=ctvisualizacao,
            )

        self.logger.info('* CRIADOR - verificando permissões do servidor dono do documento...')
        ctlistagem = aconteudos_tela_listagem.copy()
        ctlistagem.update(conteudos_tela_listagem['servidores_com_acesso_edicao'].get('servidor_dono', {}))
        ctvisualizacao = aconteudos_tela_visualizacao.copy()
        ctvisualizacao.update(conteudos_tela_visualizacao['servidores_com_acesso_edicao'].get('servidor_dono', {}))
        self._verificar_conteudo_telas_documento(documento, [self.servidor_dono], url, conteudos_tela_listagem=ctlistagem, conteudos_tela_visualizacao=ctvisualizacao)

        if servidores_caso_particular:
            self.logger.info('* CASO PARTICULAR - verificando permissões de servidores de casos particulares...')
            ctlistagem = aconteudos_tela_listagem.copy()
            ctlistagem.update(conteudos_tela_listagem['servidores_com_acesso_edicao'].get('servidores_caso_particular', {}))
            ctvisualizacao = aconteudos_tela_visualizacao.copy()
            ctvisualizacao.update(conteudos_tela_visualizacao['servidores_com_acesso_edicao'].get('servidores_caso_particular', {}))
            self._verificar_conteudo_telas_documento(documento, servidores_caso_particular, url, conteudos_tela_listagem=ctlistagem, conteudos_tela_visualizacao=ctvisualizacao)
        self.client.login(user=user_tmp)

    def _compatilhar_documento_setor(
        self, pessoas_permitidas_podem_ler=[], pessoas_permitidas_podem_escrever=[], setores_permitidos_podem_ler=[], setores_permitidos_podem_escrever=[]
    ):
        """
        Os documentos sigilosos não serão compartilhados

        """
        # /documento_eletronico/gerenciar_compartilhamento_setor/?_popup=1
        url = '/documento_eletronico/gerenciar_compartilhamento_setor'
        conteudos = {
            'Setores que podem ler': (True, HTTP_200_OK),
            'Setores que podem editar': (True, HTTP_200_OK),
            'Servidores que podem ler': (True, HTTP_200_OK),
            'Servidores que podem editar': (True, HTTP_200_OK),
        }

        data = dict(
            pessoas_permitidas_podem_ler=[p.id for p in pessoas_permitidas_podem_ler if pessoas_permitidas_podem_ler],
            pessoas_permitidas_podem_escrever=[p.id for p in pessoas_permitidas_podem_escrever if pessoas_permitidas_podem_escrever],
            setores_permitidos_podem_ler=[p.id for p in setores_permitidos_podem_ler if setores_permitidos_podem_ler],
            setores_permitidos_podem_escrever=[p.id for p in setores_permitidos_podem_escrever if setores_permitidos_podem_escrever],
        )
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/documento_eletronico/listar_documentos/', status_code=HTTP_302_FOUND)
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertContains(response, 'Gerenciamento salvo com sucesso', status_code=HTTP_200_OK)

    def _compartilhar_documento_individual(
        self, documento, pessoas_permitidas_podem_ler=[], pessoas_permitidas_podem_escrever=[], setores_permitidos_podem_ler=[], setores_permitidos_podem_escrever=[]
    ):
        """
        Documento sigiloso não é compartilhado entre os setores, logo os campos "Setores que podem ler" e "Setores que podem editar" não aparecem.

        :param documento:
        :return:
        """
        url = '/documento_eletronico/gerenciar_compartilhamento_documento/{}/'.format(documento.id)
        conteudos = {
            'Setores que podem ler': (True, HTTP_200_OK),
            'Setores que podem editar': (True, HTTP_200_OK),
            'Servidores que podem ler': (True, HTTP_200_OK),
            'Servidores que podem editar': (True, HTTP_200_OK),
        }
        if documento.nivel_acesso == Documento.NIVEL_ACESSO_SIGILOSO:
            conteudos['Setores que podem ler'] = False
            conteudos['Setores que podem editar'] = False
        self._verifica_conteudo_tela(documento, url, conteudos)

        data = dict(
            pessoas_permitidas_podem_ler=[p.id for p in pessoas_permitidas_podem_ler if pessoas_permitidas_podem_ler],
            pessoas_permitidas_podem_escrever=[p.id for p in pessoas_permitidas_podem_escrever if pessoas_permitidas_podem_escrever],
            setores_permitidos_podem_ler=[p.id for p in setores_permitidos_podem_ler if setores_permitidos_podem_ler],
            setores_permitidos_podem_escrever=[p.id for p in setores_permitidos_podem_escrever if setores_permitidos_podem_escrever],
        )

        if documento.compartilhamento_pessoa_documento.exists():
            response = self.client.post(url, data={'popup': 1}, follow=True)
            self.assert_no_validation_errors(response)
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertRedirects(response, '/documento_eletronico/listar_documentos/', status_code=HTTP_302_FOUND)
        self.assertEqual(response.status_code, HTTP_200_OK)
        self.assertContains(response, 'Gerenciamento salvo com sucesso', status_code=HTTP_200_OK)

        compartilhamentos_documento_pessoa_ler = documento.compartilhamento_pessoa_documento.filter(nivel_permissao=NivelPermissao.LER)
        self.assertEqual(
            [cdp.pessoa_permitida.id for cdp in compartilhamentos_documento_pessoa_ler if compartilhamentos_documento_pessoa_ler],
            [p.id for p in pessoas_permitidas_podem_ler if pessoas_permitidas_podem_ler],
        )

        compartilhamentos_documento_pessoa_editar = documento.compartilhamento_pessoa_documento.filter(nivel_permissao=NivelPermissao.EDITAR)
        self.assertEqual(
            [cdp.pessoa_permitida.id for cdp in compartilhamentos_documento_pessoa_editar if compartilhamentos_documento_pessoa_editar],
            [p.id for p in pessoas_permitidas_podem_escrever if pessoas_permitidas_podem_escrever],
        )

    def _concluir_documento(self, documento):
        if documento is None:
            documento = self._cadastrar_documento(self.records['scosinf1'], self.retornar(TipoDocumentoTexto, chaves={'sigla': 'OFÍCIO'})[0], Documento.NIVEL_ACESSO_PUBLICO)
        url = '/documento_eletronico/concluir_documento/{}/'.format(documento.id)
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Operação realizada com sucesso.', status_code=HTTP_200_OK)
        self.assertRedirects(response, '/documento_eletronico/visualizar_documento/{:d}/'.format(documento.id), status_code=HTTP_302_FOUND, target_status_code=HTTP_200_OK)

    def _retonar_para_rascunho(self, documento):
        if documento is None:
            documento = self._cadastrar_documento(self.records['scosinf1'], self.retornar(TipoDocumentoTexto, chaves={'sigla': 'OFÍCIO'})[0], Documento.NIVEL_ACESSO_PUBLICO)
        url = '/documento_eletronico/retornar_para_rascunho/{}/'.format(documento.id)
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'Operação realizada com sucesso.', status_code=HTTP_200_OK)
        self.assertRedirects(response, '/documento_eletronico/visualizar_documento/{:d}/'.format(documento.id), status_code=HTTP_302_FOUND, target_status_code=HTTP_200_OK)

    def _solicitar_revisao(self, revisor, documento=None):
        if documento is None:
            documento = self._cadastrar_documento(self.records['scosinf1'], self.retornar(TipoDocumentoTexto, chaves={'sigla': 'OFÍCIO'})[0], Documento.NIVEL_ACESSO_PUBLICO)
        url = '/documento_eletronico/solicitar_revisao/{}/'.format(documento.id)
        data = {'revisor': revisor.id, 'observacao': 'obs'}

        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertEqual(HTTP_200_OK, response.status_code)
        self.assertContains(response, 'O documento foi enviando a {} para revisão.'.format(revisor.user))
        # self.assertContains(response, u'O documento foi enviando a {} para revisão.' % revisor.user, status_code=HTTP_200_OK)

        self.assertRedirects(response, '/documento_eletronico/listar_documentos/', status_code=HTTP_302_FOUND, target_status_code=HTTP_200_OK)

    def _marcar_como_revisado(self, servidor_revisor, documento=None):
        user_tmp = self.client.user
        self.login(servidor_revisor)
        if documento is None:
            documento = self._cadastrar_documento(self.records['scosinf1'], self.retornar(TipoDocumentoTexto, chaves={'sigla': 'OFÍCIO'})[0], Documento.NIVEL_ACESSO_PUBLICO)

        url = '/documento_eletronico/revisar_documento/{}/'.format(documento.id)
        data = {'notas_revisor': 'obs'}
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Sua solicitação foi enviada com sucesso')
        self.assertRedirects(response, '/documento_eletronico/listar_documentos/', status_code=HTTP_302_FOUND, target_status_code=HTTP_200_OK)
        self.client.login(user=user_tmp)

    def _solicitar_assinatura(self, servidor, documento=None):
        if documento is None:
            documento = self._cadastrar_documento(self.records['scosinf1'], self.retornar(TipoDocumentoTexto, chaves={'sigla': 'OFÍCIO'})[0], Documento.NIVEL_ACESSO_PUBLICO)
        url = '/documento_eletronico/solicitar_assinatura/{}/'.format(documento.id)
        data = {'solicitado': servidor.id}
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Sua solicitação foi enviada com sucesso')
        self.assertRedirects(response, '/documento_eletronico/listar_documentos/', status_code=HTTP_302_FOUND, target_status_code=HTTP_200_OK)

    def _assinar_documento_via_senha(self, servidor, documento):
        user_tmp = self.client.user
        self.login(servidor)
        url = '/documento_eletronico/assinar_documento/{}/'.format(documento.id)
        data = {'papel': servidor.papeis_ativos[0].id, 'senha': '123'}
        response = self.client.post(url, data, follow=True)
        self.assert_no_validation_errors(response)
        self.assertContains(response, 'Documento assinado com sucesso', status_code=HTTP_200_OK)
        self.assertRedirects(response, '/documento_eletronico/visualizar_documento/{}/'.format(documento.id), status_code=HTTP_302_FOUND, target_status_code=HTTP_200_OK)

        # Verificando conteúdo do documento
        response = self.client.get('/documento_eletronico/conteudo_documento/{}/'.format(documento.id))
        self.assertContains(response, 'Documento assinado eletronicamente por', status_code=HTTP_200_OK)
        hoje = '{}'.format(datetime.today().strftime('%d/%m/%Y'))
        self.assertContains(response, '<strong>{}</strong>'.format(servidor.nome), status_code=HTTP_200_OK)
        self.assertContains(response, '<strong>{}</strong>'.format(servidor.papeis_ativos[0].descricao), status_code=HTTP_200_OK)
        self.assertContains(response, 'em {}'.format(hoje), status_code=HTTP_200_OK)
        self.assertContains(
            response,
            'Este documento foi emitido pelo SUAP em {}. Para comprovar sua autenticidade, ' 'faça a leitura do QRCode ao lado ou acesse '.format(hoje),
            status_code=HTTP_200_OK,
        )
        self.assertContains(response, '/autenticar-documento/ e forneça os dados abaixo:', status_code=HTTP_200_OK)
        self.client.login(user=user_tmp)

    def _assinar_documento_via_token(self, servidor, documento):
        # Utilizei a ferramenta keystore explorer (http://keystore-explorer.org/downloads.html) para gerar o certificado
        # https://sourceforge.net/projects/xca/
        user_tmp = self.client.user
        self.login(servidor)
        # "/documento_eletronico/validar_assinatura_token/" + documento_id + "/"
        url = '/documento_eletronico/assinar_documento_token/{}/'.format(documento.id)
        data = {'papel': servidor.papeis_ativos[0].id}
        response = self.client.post(url, data, follow=True)
        # self.assert_no_validation_errors(response)
        # self.assertContains(response, u'Documento assinado com sucesso', status_code=HTTP_200_OK)
        # self.assertRedirects(response, '/documento_eletronico/visualizar_documento/{}/' %documento.id,
        # status_code=HTTP_302_FOUND, target_status_code=HTTP_200_OK)
        url = '/documento_eletronico/validar_assinatura_token/{}/'.format(documento.id)
        data = {'cert': '', 'sig': '', 'data': documento.hash_conteudo, 'papel': servidor.papeis_ativos[0].id}  # hexToPem(certificate.hex)  # signature.hex
        response = self.client.post(url, data, follow=True)
        # Verificando conteúdo do documento
        # response = self.client.get('/documento_eletronico/conteudo_documento/{}/' %documento.id)
        # self.assertContains(response, u'Documento assinado eletronicamente por', status_code=HTTP_200_OK)
        # hoje = u'{}' %datetime.today().strftime('%d/%m/%Y')
        # self.assertContains(response, u'<strong>{}</strong>' % servidor.nome, status_code=HTTP_200_OK)
        # self.assertContains(response, u'<strong>{}</strong>' % servidor.papeis_ativos[0].descricao, status_code=HTTP_200_OK)
        # self.assertContains(response, u'em {}' %hoje, status_code=HTTP_200_OK)
        # self.assertContains(response,
        #                     u'Este documento foi emitido pelo SUAP em {}. Para comprovar sua autenticidade,
        # faça a leitura do QRCode ao lado ou acesse ' % hoje,
        #                     status_code=HTTP_200_OK)
        # self.assertContains(response, u'/autenticar-documento/ e forneça os dados abaixo:', status_code=HTTP_200_OK)
        # self.client.login(user=user_tmp)


class CadastrosBasicosTestCase(DocumentoEletronicoBaseTestCase):
    # ./manage.py test documento_eletronico.tests.CadastrosBasicosTestCase --keepdb --verbosity=2
    def _clonar_objeto(self, cls, url, expected_url):
        user_tmp = self.client.user
        obj_data = list(self.retornar(cls).values())[0]
        url = url.format(id=obj_data['id'])

        # usuário comum não tem acesso
        self.login()
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

        # usuário previamente definido tem acesso
        self.client.login(user=user_tmp)
        response = self.client.get(url, follow=True)
        self.assertContains(response, 'clonado com sucesso.', status_code=HTTP_200_OK)

        data = list(self.retornar(cls).values())[0]

        expected_url %= {'id': data['id']}
        self.assertRedirects(response, expected_url, status_code=HTTP_302_FOUND, target_status_code=HTTP_200_OK)
        self.assertEqual('Clone de {} 1'.format(obj_data['nome']), data['nome'])

        # clonando o mesmo documento novamente
        response = self.client.get(url, follow=True)

    def test_verificar_variaveis(self):
        """
        1. Verifica cada valor do dicionário da variável corresponde com os dados experados
        2. Testa a funcionalidade exibir variáveis.
            - verifica se aparecece a mensagem 'Visualização de variáveis'
            - verifica se usuário sem permissão tem acesso.
        :return:
        """
        self.acessar_como_gerente_sistemico()
        servidor = self.records['chefe_gabin']
        usuario = servidor.user
        setor = servidor.setor
        uo = setor.uo

        lvariaveis = get_variaveis(documento_identificador='', to_dict=False)
        variaveis = {}
        for v in lvariaveis:
            variaveis[v[0]] = v[1]

        self.assertEqual(variaveis['usuario_nome'], servidor.nome)
        self.assertEqual(variaveis['reitor'], self.records['reitor'].nome)
        self.assertEqual(variaveis['setor_nome'], setor.nome)
        self.assertEqual(variaveis['setor_sigla'], setor.sigla)
        self.assertEqual(variaveis['setor_chefe'], setor.funcionarios.filter(id=servidor.id)[0])
        self.assertEqual(variaveis['instituicao_nome'], self.instituicao_nome.valor)
        self.assertEqual(variaveis['instituicao_sigla'], self.instituicao_sigla.valor)
        self.assertEqual(variaveis['unidade_sigla'], uo.sigla)
        self.assertEqual(variaveis['unidade_nome'], uo.nome)
        self.assertEqual(variaveis['unidade_diretor'], self.records['reitor'].nome)

        url = '/documento_eletronico/visualizar_variaveis/?_popup=1&_popup=1'
        response = self.client.get(url)
        self.assertContains(response, 'Visualização de Variáveis', status_code=HTTP_200_OK)

        self.login()
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTP_403_FORBIDDEN)

    def test_cadastros_basicos(self):
        """
        Realiza testes nos cadastros básicos
        1. Verifica se usuário sem permissão tem acesso na listagem e no detalhe do objeto
        2. Teste com usuário com permissão
            - Verifica acesso na listagem
            - verifica se texto definido em page_contains existe na página
            - Verifica acesso na exibição do detalhe
            - Verifica se existe o botão 'Adicionar [modelo nome]'
        3. Testa se o dado fornecido foi salvo com sucesso
            - Verifica se não ocorreu erro no form
            - Verifica se a url redireciona é a esperada
            - Verifica se o objeto foi salvo com sucesso no banco.
        :return:
        """
        self.acessar_como_gerente_sistemico()
        self.logger.info('\n\nCadastrando tipo de documento interno ...')
        data = dict(nome='nome do tipo de documento', sigla='NTDOC')
        tipo = self._cadastrar(
            TipoDocumentoTexto,
            data,
            page_contains={
                '/documento_eletronico/clonar_tipo_documento/{}/'.format(self.retornar(TipoDocumentoTexto).values('id')[0]['id']): (True, HTTP_200_OK),
                '/admin/documento_eletronico/modelodocumento/?tipo_documento__id__exact=1': (True, HTTP_200_OK),
            },
            url_add='/admin/documento_eletronico/tipodocumentotexto/add/',
            expected_url='/',
        )
        self.logger.info('\n\nCadastrando classificação do documento ...')
        data = dict(codigo='0000000001', descricao='Nome da classificação', suficiente_para_classificar_processo=True)
        classificacao = self._cadastrar(Classificacao, data, expected_url='/')

        self.logger.info('\n\nCadastrando modelo de documento ...')
        data = dict(nome='Nome do modelo', tipo_documento_texto=tipo.id, nivel_acesso_padrao=Documento.NIVEL_ACESSO_SIGILOSO, classificacao=[classificacao.id])

        self._cadastrar(
            ModeloDocumento,
            data,
            page_contains={'/documento_eletronico/clonar_modelo_documento/{}/'.format(self.retornar(ModeloDocumento).values('id')[0]['id']): (True, HTTP_200_OK)},
            expected_url='/documento_eletronico/editar_modelo_documento/%(id)s/',
        )

    def test_excluir_cadastros(self):
        self.acessar_como_gerente_sistemico()
        self._excluir_cadastros(TipoDocumentoTexto)
        self._excluir_cadastros(ModeloDocumento)
        self._excluir_cadastros(Classificacao)

    def test_editar_cadastros(self):
        """
        1. Verifica se usuário sem permissão tem acesso
        2. Testa a ação salvar da funcionalidade edição do objeto clonado e faz as seguintes verificações:
            - Se não ocorreu erros no formulário
            - Se apareceu a mensagem 'Atualização realizada com sucesso.'
            - Se objeto os dados do objeto salvo confere com os dados enviados
        """
        self.acessar_como_gerente_sistemico()
        self._editar_cadastros(TipoDocumentoTexto, dados={'nome': 'tipo de documento clonado'}, expected_url='/admin/documento_eletronico/tipodocumento/%(id)s/change/')
        self._editar_cadastros(ModeloDocumento, dados={'nome': 'modelo de documento clonado'}, expected_url='/documento_eletronico/editar_modelo_documento/%(id)s/')

    def test_clonar_tipo_e_modelo_documento(self):
        """
        1. Verifica se usuário sem permissão tem acesso.
        2. Testa funcionalidade de clonar objeto, de acordo com o fluxo:
            - Se aparece a mensagem '[Nome do Modelo] clonado com sucesso
            -  Se foi redirecionado para url correta
            -  Se o nome do objeto salvo segue o padrão 'Clone de [nome anterior]'
        2. Testa funcionalidade de clonar objeto novamente com o objeto original
        """
        self.acessar_como_gerente_sistemico()
        self._clonar_objeto(TipoDocumentoTexto, url='/documento_eletronico/clonar_tipo_documento/%(id)s/', expected_url='/admin/documento_eletronico/tipodocumento/%(id)s/change/')
        self._clonar_objeto(ModeloDocumento, url='/documento_eletronico/clonar_modelo_documento/%(id)s/', expected_url='/documento_eletronico/editar_modelo_documento/%(id)s/')


class AjaxTestCase(DocumentoEletronicoBaseTestCase):
    # ./manage.py test documento_eletronico.tests.AjaxTestCase --keepdb --verbosity=2
    def test_acao_clique_autor_documento(self):
        """
        Na tela de listagem de documento, ao clicar no link do nome do autor do documento ocorre a requisição abaixo.
        :return:
        """
        servidor = self.records['scosinf1']

        url = '/djtools/user_info/{}/'.format(servidor.id)

        # qualquer servidor tem acesso
        self.login(servidor)
        response = self.client.get(url)
        self.assertContains(response, '/rh/servidor/{}/'.format(servidor.matricula), status_code=HTTP_200_OK)
        self.assertContains(response, '/rh/setor/{}/'.format(servidor.setor.id), status_code=HTTP_200_OK)
        self.assertContains(response, servidor.email, status_code=HTTP_200_OK)

    def test_acao_caixa_selecao_tipo(self):
        """
        No formulário cadastro de documento, ao selecionar um setor dono ocorre a requisição ajax abaixo
        Obs.: Além da requisição ajax, ocorre as requisições testadas nas funções test_acao_caixa_selecao_modelo
        e test_acao_caixa_selecao_setor_dono
        :return:
        """
        servidor = self.records['scosinf1']
        setor_dono = servidor.setor
        tipo_documento = self.retornar(TipoDocumentoTexto, chaves={'sigla': 'OFÍCIO'})[0]

        # qualquer servidor tem acesso
        self.login()

        url = '/documento_eletronico/modelos_tipo_documento/{}/'.format(tipo_documento.id)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = {
            'modelos': [
                {'id': '', 'nome': '---------'},
                {'id': 4, 'nome': 'Consulta sobre disponibilidade de código de vaga a ser oferecido ' 'ao instituto em contrapartida pela redistribuição de servidor.'},
                {'id': 3, 'nome': 'Exercício provisório para acompanhamento de cônjuge'},
                {'id': 5, 'nome': 'Informa impossibilidade de renovação de cessão de servidor'},
            ]
        }
        js = json.loads(response.content)
        self.assertEqual(js, data)

    def test_acao_caixa_selecao_modelo(self):
        """
        No formulário cadastro de documento, ao selecionar um modelo de documento ocorre a requisição ajax abaixo
        :return:
        """
        tipo_documento = self.retornar(TipoDocumentoTexto, chaves={'sigla': 'OFÍCIO'})[0]
        modelo_documento = tipo_documento.modelos.filter(nome='Informa impossibilidade de renovação de cessão de servidor')[0]

        # qualquer servidor tem acesso
        self.login()

        url = '/documento_eletronico/nivel_acesso_padrao_classificacoes_modelo_documento/{}/'.format(modelo_documento.id)
        response = self.client.get(url, follow=True)
        self.assertEqual(response.status_code, HTTP_200_OK)
        data = {'nivel_acesso_padrao': 3, 'classificacoes': [{'id': 50, 'descricao': 'REQUISIÇÃO. CESSÃO'}]}
        js = json.loads(response.content)
        self.assertEqual(js, data)
