# -*- coding: utf-8 -*-
from behave import given  # NOQA

from rh.models import Instituicao


@given('os dados basicos cadastrados')
def step_atual_pagina(context):
    Instituicao.objects.get_or_create(nome="TRE/RN")
