# -*- coding: utf-8 -*-
from behave import given  # NOQA

from comum.models import User


@given('os dados basicos cadastrados do rh')
def dados_basicos_rh(context):
    usuario = User.objects.get(username="9999100")
    usuario.is_superuser = True
    usuario.save()
