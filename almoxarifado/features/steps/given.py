# -*- coding: utf-8 -*-


from behave import given

import datetime
from almoxarifado.models import Entrada, EntradaTipo, MaterialTipo, MaterialConsumo, MaterialEstoque, EmpenhoConsumo, \
    RequisicaoAlmoxUser, RequisicaoAlmoxUserMaterial, MovimentoAlmoxEntradaTipo
from protocolo.models import Processo
from rh.models import Servidor, Setor, UnidadeOrganizacional


@given('os usuarios do Almoxarifado')
def step_impl(context):
    context.execute_steps(
        """
        Dado os seguintes usuários
        | Nome                 | Matrícula            | Setor | Lotação | Email                               | CPF             | Senha   | Grupo                                              |
        | CoordDeAlmoxSiste    | CoordDeAlmoxSiste    | A0    | A0      | coorddealmoxsistê@ifrn.edu.br       | 078.255.187-34  | abcd    | Coordenador de Almoxarifado Sistêmico              |
        | AdminiDeOrCame       | AdminiDeOrcame       | A1    | A1      | adminideorçame@ifrn.edu.br          | 123.543.659-03  | abcd    | Administrador de Orçamento                         |
        | CoordDePatriSiste    | CoordDePatriSiste    | A2    | A2      | coorddepatrisistê@ifrn.edu.br       | 645.433.195-40  | abcd    | Coordenador de Patrimônio Sistêmico                |
        | CoordeDeAlmoxa       | CoordeDeAlmoxa       | B0    | B0      | coordedealmoxa@ifrn.edu.br          | 123.543.659-03  | abcd    | Coordenador de Almoxarifado                        |
        | GereDeMateDoAlmo     | GereDeMateDoAlmo     | B1    | B1      | geredematedoalmo@ifrn.edu.br        | 645.433.195-40  | abcd    | Gerenciador de Materiais do Almoxarifado           |
        | AdminiDePlanej       | AdminiDePlanej       | B2    | B2      | adminideplanej@ifrn.edu.br          | 078.255.187-34  | abcd    | Administrador de Planejamento                      |
        | ContaDePatriSiste    | ContaDePatriSiste    | A0    | A0      | contadepatrisistê@ifrn.edu.br       | 127.876.345-20  | abcd    | Contador de Patrimônio Sistêmico                   |
        | GereDoCataDeMate     | GereDoCataDeMate     | A1    | A1      | geredocatádemate@ifrn.edu.br        | 543.743.423-67  | abcd    | Gerenciador do Catálogo de Materiais               |
        | ContadorSistemico    | ContadorSistemico    | A2    | A2      | contadorsistêmico@ifrn.edu.br       | 543.743.423-67  | abcd    | Contador Sistêmico                                 |
        | OperadDeAlmoxa       | OperadDeAlmoxa       | B0    | B0      | operaddealmoxa@ifrn.edu.br          | 078.255.187-34  | abcd    | Operador de Almoxarifado                           |
        | Auditor              | Auditor              | B1    | B1      | auditor@ifrn.edu.br                 | 078.255.187-34  | abcd    | Auditor                                            |
        | ContadorAdministra   | ContadorAdministra   | B2    | B2      | contadoradministra@ifrn.edu.br      | 078.255.187-34  | abcd    | Contador Administrador                             |
        | Contador             | Contador             | A0    | A0      | contador@ifrn.edu.br                | 127.876.345-20  | abcd    | Contador                                           |
        | CoordeDePatrim       | CoordeDePatrim       | A1    | A1      | coordedepatrim@ifrn.edu.br          | 127.876.345-20  | abcd    | Coordenador de Patrimônio                          |
        | OperadordePatrimonio | OperadordePatrimonio | A2    | A2      | operadordepatrimônio@ifrn.edu.br    | 123.543.659-03  | abcd    | Operador de Patrimônio                             |
        | ContadordePatrimonio | ContadordePatrimonio | B0    | B0      | contadordepatrimônio@ifrn.edu.br    | 127.876.345-20  | abcd    | Contador de Patrimônio                             |
"""
    )


@given('o cadastro de processo')
def step_cadastro_processo(context):
    servidor = Servidor.objects.get(matricula='CoordDeAlmoxSiste')
    Processo.objects.get_or_create(vinculo_cadastro=servidor.get_vinculo(), assunto='Assunto Teste',
                                   tipo=1, setor_origem=servidor.setor)


@given('o cadastro de entrada de compra')
def step_cadastro_entrada_compra(context):
    setor = Setor.objects.get_or_create(sigla='A0', nome='A0')[0]
    unidadeorganizacional = UnidadeOrganizacional.objects.suap().get_or_create(setor=setor)[0]
    material = MaterialConsumo.objects.get(id='000001')
    MovimentoAlmoxEntradaTipo.objects.get_or_create(nome='entrada')
    MaterialEstoque.objects.get_or_create(
        material=material, uo=unidadeorganizacional,
        defaults={'valor_medio': 0, 'quantidade': 0}
    )
    entrada = Entrada.objects.get_or_create(data=datetime.datetime.now(), uo=unidadeorganizacional,
                                            tipo_entrada=EntradaTipo.COMPRA(), tipo_material=MaterialTipo.CONSUMO())[
        0]
    empenho_consumo = EmpenhoConsumo.objects.get(pk=1)
    empenho_consumo.efetuar_entrada(entrada, 1)


@given('o cadastro de entrada de doacao')
def step_cadastro_entrada_doacao(context):
    setor = Setor.objects.get_or_create(sigla='A0', nome='A0')[0]
    unidadeorganizacional = UnidadeOrganizacional.objects.suap().get_or_create(setor=setor)[0]
    material = MaterialConsumo.objects.get(id='000001')
    MovimentoAlmoxEntradaTipo.objects.get_or_create(nome='entrada')
    MaterialEstoque.objects.get_or_create(
        material=material, uo=unidadeorganizacional,
        defaults={'valor_medio': 0, 'quantidade': 0}
    )
    entrada = Entrada.objects.get_or_create(data=datetime.datetime.now(), uo=unidadeorganizacional,
                                            tipo_entrada=EntradaTipo.DOACAO(), tipo_material=MaterialTipo.CONSUMO())[
        0]
    empenho_consumo = EmpenhoConsumo.objects.get(pk=1)
    empenho_consumo.efetuar_entrada(entrada, 1)


@given('o cadastro de requisicao')
def step_cadastro_requisicao(context):
    setor = Setor.objects.get_or_create(sigla='A0', nome='A0')[0]
    unidadeorganizacional = UnidadeOrganizacional.objects.suap().get_or_create(setor=setor)[0]
    servidor = Servidor.objects.get(matricula='CoordDeAlmoxSiste').get_vinculo()
    material = MaterialConsumo.objects.get(id='000001')
    requisicao = RequisicaoAlmoxUser.objects.get_or_create(uo_fornecedora=unidadeorganizacional, vinculo_solicitante=servidor, setor_solicitante=setor,)[0]
    RequisicaoAlmoxUserMaterial.get_or_create(requisicao=requisicao, material=material, qtd=1)
