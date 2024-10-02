# -*- coding: utf-8 -*-

from avaliacao_integrada.models import Segmento
from behave import given
from comum.models import Ano


@given('os dados básicos para avaliacao integrada')
def step_dados_basicos_aval_int(context):
    Ano.objects.get_or_create(ano=2020)
    Segmento.objects.get_or_create(descricao='CPA_CENTRAL')[0]
    Segmento.objects.get_or_create(descricao='CPA_CAMPUS')[0]
    Segmento.objects.get_or_create(descricao='GESTOR')[0]
    Segmento.objects.get_or_create(descricao='TECNICO')[0]
    Segmento.objects.get_or_create(descricao='ETEP')[0]
    Segmento.objects.get_or_create(descricao='DOCENTE')[0]
    Segmento.objects.get_or_create(descricao='Estudante')[0]
