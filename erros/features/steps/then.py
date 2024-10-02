from behave import then  # NOQA
from hamcrest import assert_that, greater_than

from djtools.new_tests.base_test import XPathConstructor
from djtools.new_tests.environment_base import gerar_highlight_screenshot
from djtools.new_tests.utils import log, wait_element


@then('vejo mensagem na timeline "{mensagem}"')
def step_ver_pagina(context, mensagem):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_html_element(element='p', text=mensagem)
    wait_element(my_xpath)
    titulo = my_xpath.get()
    log(my_xpath)
    assert_that(len(titulo), greater_than(0), my_xpath.get_xpath())

    gerar_highlight_screenshot(context, my_xpath.get_xpath())


@then('vejo o status "{mensagem}" acima do título')
def step_ver_status_titulo(context, mensagem):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_html_element(element='span', class_name='status', text=mensagem)
    wait_element(my_xpath)
    titulo = my_xpath.get()
    log(my_xpath)
    assert_that(len(titulo), greater_than(0), my_xpath.get_xpath())

    gerar_highlight_screenshot(context, my_xpath.get_xpath())
