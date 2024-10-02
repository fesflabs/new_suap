# -*- coding: utf-8 -*-

from behave import given
from ae.features.steps.given import dados_basicos_ae


@given('os dados básicos do auxílio emergencial')
def step_dados_basicos(context):
    dados_basicos_ae(context)
