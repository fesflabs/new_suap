from behave import when  # NOQA

from djtools.new_tests.base_test import XPathConstructor
from djtools.new_tests.utils import force_click


@when('clico no label "{valor_label}" da etapa "{numero_etapa}"')
def step_clico_label(context, valor_label, numero_etapa):
    context.browser.execute_script(f"checkAllRadios({numero_etapa}, '{valor_label}')")


@when('seto o status da linha de avaliação para "{status}"')
def step_setar_status(context, status):
    status_value = ''
    if status == 'C.P':
        status_value = 'ERROR'
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.xpath += f'{my_xpath.context}//td//input[@value="{status_value}"]'
    force_click(my_xpath)
