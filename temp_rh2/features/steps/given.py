# -*- coding: utf-8 -*-

from behave import given
from django.apps.registry import apps

from rh.models import Servidor

Ano = apps.get_model('comum', 'Ano')


@given('os dados básicos para competição desportiva')
def step_dados_basicos_competicao(context):
    Ano.objects.get_or_create(ano='2020')[0]


@given('os dados de sexo do servidor está populado')
def step_dados_de_sexo_do_servidor_esta_populado(context):
    Servidor.objects.filter(matricula=337003).update(sexo='M')
