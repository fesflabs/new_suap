# -*- coding: utf-8 -*-

from behave import when  # noqa
from comum.models import User


@when('altero a senha do aluno "{matricula}" para "{senha}"')
def step_alterar_senha(_, matricula, senha):
    aluno = User.objects.get(username=matricula)
    aluno.set_password(senha)
    aluno.save()
