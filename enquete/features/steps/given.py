# -*- coding: utf-8 -*-

from behave import given  # NOQA


@given('os usuarios de Enquete')
def step_impl(context):
    context.execute_steps(
        """
        Dado os seguintes usuários
        | Nome                 | Matrícula            | Setor | Lotação | Email                               | CPF             | Senha   | Grupo                                              |
        | Criador de Enquete   | CriadorEnquete       | A0    | A0      | criadorenquete@ifrn.edu.br          | 077.255.187-34  | abcd    | Criador de Enquete                                 |
    """
    )
