# -*- coding: utf-8 -*-

from behave import then
from hamcrest import assert_that, greater_than

from djtools.new_tests.base_test import XPathConstructor


@then("vejo os seguintes campos no formulário preenchidos com")
def step_ver_campos_formularios_preenchidos(context):
    for row in context.table:
        campo = row['Campo']
        tipo = row['Tipo'].lower()
        valor = row['Valor']

        my_xpath = XPathConstructor(context.browser, context.contexto)
        my_xpath.find_form_input(campo, tipo)
        field = my_xpath.get()

        assert_that(len(field), greater_than(0), my_xpath.get_xpath())
        assert_that(field.first.value, valor, my_xpath.get_xpath())
