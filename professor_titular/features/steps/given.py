# -*- coding: utf-8 -*-

from professor_titular.models import Indicador, Grupo, CategoriaMemorialDescritivo, Unidade
from behave import given  # noqa


@given('os dados básicos para professor titular')
def step_cadastros(context):
    Unidade.objects.get_or_create(nome='mês', sigla='lv')
    CategoriaMemorialDescritivo.get_or_create(nome="pesquisa e atividades", indice='1')
    Grupo.objects.get_or_create(nome='A', percentual=10)

    grupo2 = Grupo.objects.get(nome='A')
    Indicador.objects.get_or_create(grupo=grupo2, nome='atividade', descricao='teste')
