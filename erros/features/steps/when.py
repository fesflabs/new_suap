from behave import when  # NOQA
from djtools.new_tests.base_test import XPathConstructor
from djtools.new_tests.environment_base import gerar_highlight_screenshot
from djtools.new_tests.utils import log, force_fill, wait_element


@when('olho para a textarea "{nome}" e preencho com "{texto}"')
def step_ver_textarea(context, nome, texto):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_textarea(nome)
    log(my_xpath)
    wait_element(my_xpath)
    force_fill(my_xpath, texto)
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
