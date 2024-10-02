# -*- coding: utf-8 -*-

from behave import given
from datetime import datetime
from comum.models import Ano
from financeiro.models import CategoriaEconomicaDespesa, ElementoDespesa, GrupoNaturezaDespesa, ModalidadeAplicacao, NaturezaDespesa
from projetos.models import Tema, TipoBeneficiario, FocoTecnologico, AreaTematica
from django.apps.registry import apps

CategoriaBolsa = apps.get_model('ae', 'categoriabolsa')
PessoaFisica = apps.get_model('rh', 'PessoaFisica')
UnidadeOrganizacional = apps.get_model('rh', 'UnidadeOrganizacional')
Aluno = apps.get_model('edu', 'Aluno')
SituacaoMatricula = apps.get_model('edu', 'SituacaoMatricula')

Projeto = apps.get_model('projetos', 'Projeto')
AvaliadorIndicado = apps.get_model('projetos', 'AvaliadorIndicado')


@given('os dados básicos para a extensão')
def step_dados_basicos_extensao(context):
    categoriaeconomicadespesa = CategoriaEconomicaDespesa.objects.get_or_create(codigo='3', nome='Despesas Correntes')[0]
    gruponaturezadespesa = GrupoNaturezaDespesa.objects.get_or_create(codigo='3', nome='Outras Despesas Correntes')[0]
    modalidadeaplicacao = ModalidadeAplicacao.objects.get_or_create(codigo='90', nome='Aplicações Diretas')[0]
    elementodespesa1 = ElementoDespesa.objects.get_or_create(codigo='30', nome='Material de Consumo')[0]
    elementodespesa2 = ElementoDespesa.objects.get_or_create(codigo='18', nome='Auxílio Financeiro a Estudantes')[0]
    elementodespesa3 = ElementoDespesa.objects.get_or_create(codigo='20', nome='Auxílio Financeiro a Pesquisadores')[0]

    NaturezaDespesa.objects.get_or_create(
        categoria_economica_despesa=categoriaeconomicadespesa,
        grupo_natureza_despesa=gruponaturezadespesa,
        modalidade_aplicacao=modalidadeaplicacao,
        elemento_despesa=elementodespesa1,
        codigo='339030',
        nome=elementodespesa1.nome,
    )

    NaturezaDespesa.objects.get_or_create(
        categoria_economica_despesa=categoriaeconomicadespesa,
        grupo_natureza_despesa=gruponaturezadespesa,
        modalidade_aplicacao=modalidadeaplicacao,
        elemento_despesa=elementodespesa2,
        codigo='339018',
        nome=elementodespesa2.nome,
    )

    NaturezaDespesa.objects.get_or_create(
        categoria_economica_despesa=categoriaeconomicadespesa,
        grupo_natureza_despesa=gruponaturezadespesa,
        modalidade_aplicacao=modalidadeaplicacao,
        elemento_despesa=elementodespesa3,
        codigo='339020',
        nome=elementodespesa3.nome,
    )

    foco = FocoTecnologico.objects.get_or_create(descricao='Multidisciplinar', ativo=True)[0]

    foco.campi.add(UnidadeOrganizacional.objects.suap().filter(sigla='CZN')[0])
    areatematica = AreaTematica.objects.get_or_create(descricao='Multidisciplinar')[0]
    Tema.objects.get_or_create(descricao='Tecnologia da Informação  e Comunicação', areatematica=areatematica)

    if CategoriaBolsa:
        CategoriaBolsa.objects.get_or_create(nome='Bolsa de Extensão', descricao='Bolsa de Extensão', tipo_bolsa='extensão')
        CategoriaBolsa.objects.get_or_create(nome='Bolsa de iniciação científica', descricao='Bolsa de iniciação científica', tipo_bolsa='iniciação científica')

    TipoBeneficiario.objects.get_or_create(descricao='Movimentos Sociais')

    Ano.objects.get_or_create(ano=str(datetime.now().year))
    Ano.objects.get_or_create(ano='2018')
