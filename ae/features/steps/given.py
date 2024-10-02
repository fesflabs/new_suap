# -*- coding: utf-8 -*-
from behave import given

from ae.models import (
    ContribuinteRendaFamiliar,
    MeioTransporte,
    CompanhiaDomiciliar,
    EstadoCivil,
    TipoServicoSaude,
    TipoEscola,
    NivelEscolaridade,
    SituacaoTrabalho,
    TipoImovelResidencial,
    TipoAcessoInternet,
    TipoAreaResidencial,
    TipoPrograma,
    CategoriaAlimentacao,
)
from comum.models import Raca, Configuracao


@given('os dados basicos cadastrados do ae')
def dados_basicos_ae(context):
    Configuracao.objects.get_or_create(app='comum', chave='salario_minimo', valor='954', descricao='valor do salário mínimo')

    ContribuinteRendaFamiliar.objects.get_or_create(descricao='Pai')
    ContribuinteRendaFamiliar.objects.get_or_create(descricao='Mãe')
    ContribuinteRendaFamiliar.objects.get_or_create(descricao='Parentes')
    ContribuinteRendaFamiliar.objects.get_or_create(descricao='Outros')
    ContribuinteRendaFamiliar.objects.get_or_create(descricao='O próprio aluno')
    ContribuinteRendaFamiliar.objects.get_or_create(descricao='Não informado')
    MeioTransporte.objects.get_or_create(descricao='Bicicleta')
    MeioTransporte.objects.get_or_create(descricao='Moto')
    MeioTransporte.objects.get_or_create(descricao='Transporte coletivo')
    MeioTransporte.objects.get_or_create(descricao='Automóvel')
    MeioTransporte.objects.get_or_create(descricao='Outro')
    CompanhiaDomiciliar.objects.get_or_create(descricao='Pai')
    CompanhiaDomiciliar.objects.get_or_create(descricao='Mãe')
    CompanhiaDomiciliar.objects.get_or_create(descricao='Outros')
    EstadoCivil.objects.get_or_create(descricao='Solteiro(a)')
    EstadoCivil.objects.get_or_create(descricao='Casado(a)')
    EstadoCivil.objects.get_or_create(descricao='Viúvo(a)')
    TipoServicoSaude.objects.get_or_create(descricao='Sistema Único de Saúde - SUS')
    TipoServicoSaude.objects.get_or_create(descricao='Plano de saúde particular')
    TipoServicoSaude.objects.get_or_create(descricao='Plano de saúde da empresa')
    TipoEscola.objects.get_or_create(descricao='Somente em escola pública')
    TipoEscola.objects.get_or_create(descricao='Somente em escola particular')
    TipoEscola.objects.get_or_create(descricao='Outro tipo de escola')
    NivelEscolaridade.objects.get_or_create(descricao='Ensino fundamental completo')
    NivelEscolaridade.objects.get_or_create(descricao='Ensino médio completo')
    NivelEscolaridade.objects.get_or_create(descricao='Ensino superior completo')
    SituacaoTrabalho.objects.get_or_create(descricao='Não está trabalhando')
    SituacaoTrabalho.objects.get_or_create(descricao='Autônomo')
    SituacaoTrabalho.objects.get_or_create(descricao='Nunca trabalhou')
    SituacaoTrabalho.objects.get_or_create(descricao='Trabalha com vínculo empregatício')
    TipoImovelResidencial.objects.get_or_create(descricao='Financiado')
    TipoImovelResidencial.objects.get_or_create(descricao='Alugado')
    TipoImovelResidencial.objects.get_or_create(descricao='Próprio')
    TipoImovelResidencial.objects.get_or_create(descricao='Outro')
    TipoAreaResidencial.objects.get_or_create(descricao='Urbana')
    TipoAreaResidencial.objects.get_or_create(descricao='Rural')
    TipoAcessoInternet.objects.get_or_create(descricao='Diariamente')
    TipoAcessoInternet.objects.get_or_create(descricao='Semanalmente')

    Raca.objects.get_or_create(descricao='Parda', codigo_siape=4)
    Raca.objects.get_or_create(descricao='Preta', codigo_siape=6)
    Raca.objects.get_or_create(descricao='Branca', codigo_siape=1)
    Raca.objects.get_or_create(descricao='Indígena', codigo_siape=5)
    Raca.objects.get_or_create(descricao='Amarela', codigo_siape=3)
    Raca.objects.get_or_create(descricao='Não declarado', codigo_siape=9)

    TipoPrograma.objects.update(sigla='ALM')
    CategoriaAlimentacao.get_or_create(nome='AS', descricao='Assistência Social')
    CategoriaAlimentacao.get_or_create(nome='Bolsa de extensão', descricao='Bolsa de extensão')
    CategoriaAlimentacao.get_or_create(nome='Bolsa de pesquisa', descricao='Bolsa de pesquisa')
