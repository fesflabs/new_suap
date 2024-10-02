# -*- coding: utf-8 -*-
import datetime

from behave import given  # NOQA
from django.contrib.auth.models import Group

from documento_eletronico.models import TipoDocumentoTexto
from rh.models import Setor, Servidor, ServidorFuncaoHistorico, Funcao, Atividade


def mudar_data(context, data):
    context.execute_steps('Quando a data do sistema for "{}"'.format(data))


def criar_usuarios(context):
    context.execute_steps(
        '''Dado os seguintes usuários
    | Nome                                 | Matrícula | Setor    | Lotação  | Email                               | CPF            | Senha | Grupo                                      |
    | Reitor                               | 000001    | RAIZ     | RAIZ     | reitor@ifrn.edu.br                  | 261.880.580-15 | abcd  | Gerente Sistêmico de Documento Eletrônico  |
    | Servidor Documento Gerente Sistêmico | 200001    | CEN      | CEN      | gerente_documento@ifrn.edu.br       | 994.034.470-87 | abcd  | Gerente Sistêmico de Documento Eletrônico  |
    | Servidor Documento Chefe Setor       | 200002    | DIDE/CEN | DIDE/CEN | chefe_setor@ifrn.edu.br             | 211.659.640-82 | abcd  | Chefe de Setor                             |
    | Servidor Documento Operador          | 200003    | DIDE/CEN | DIDE/CEN | operador_documento@ifrn.edu.br      | 704.518.120-50 | abcd  | Operador de Documento Eletrônico           |
    | Servidor Documento Leitor            | 200004    | DIDE/CEN | DIDE/CEN | servidor@ifrn.edu.br                | 058.903.560-62 | abcd  | Servidor                                   |
    '''
    )


@given('os cadastros básicos do documento eletrônico')
def step_cadastros_feature_001(context):
    criar_usuarios(context)
    data_inicio = datetime.datetime(2010, 3, 10)
    setor_campus = Setor.todos.get(sigla='CEN', codigo__isnull=True)
    setor_diretoria = Setor.todos.get(sigla='DIDE/CEN', codigo__isnull=True)
    setor_raiz_suap = Setor.todos.get(sigla='RAIZ', nome='RAIZ', codigo=None)
    atividade_reitor = Atividade.objects.get(codigo=Atividade.REITOR)
    funcao = Funcao.objects.get(nome="Chefe de Setor", codigo=Funcao.CODIGO_FG)
    funcao_reitor = Funcao.objects.get(nome="Reitor", codigo=Funcao.CODIGO_CD)

    servidor = Servidor.objects.get(matricula='200001')
    user = servidor.user
    user.groups.add(Group.objects.get(name='Servidor'))
    user.save()
    ServidorFuncaoHistorico.objects.get_or_create(servidor=servidor, data_inicio_funcao=data_inicio, funcao=funcao, setor=setor_campus, setor_suap=setor_campus)

    servidor = Servidor.objects.get(matricula='200002')
    user = servidor.user
    user.groups.add(Group.objects.get(name='Servidor'))
    user.save()
    ServidorFuncaoHistorico.objects.get_or_create(servidor=servidor, data_inicio_funcao=data_inicio, funcao=funcao, setor=setor_diretoria, setor_suap=setor_diretoria)

    servidor = Servidor.objects.get(matricula='200003')
    user = servidor.user
    user.groups.add(Group.objects.get(name='Servidor'))
    user.save()

    reitor = Servidor.objects.get(matricula='000001')
    user = reitor.user
    user.groups.add(Group.objects.get(name='Servidor'))
    user.save()
    ServidorFuncaoHistorico.objects.get_or_create(
        atividade=atividade_reitor, setor=setor_raiz_suap, setor_suap=setor_raiz_suap, data_inicio_funcao=data_inicio, servidor=reitor, funcao=funcao_reitor
    )

    for tipo_documento in TipoDocumentoTexto.objects.all():
        tipo_documento.save()
