# -*- coding: utf-8 -*-


from behave import when  # NOQA
from hamcrest import assert_that, equal_to_ignoring_case

from demandas.models import Demanda


@when('digito "{texto}" no editor de texo')
def step_digitar_texto(context, texto):
    browser = context.browser
    driver = browser.driver

    contador = 5

    while contador > 0:
        if browser.is_element_present_by_tag('iframe'):
            break
        contador -= 1
        # sleep(1)

    frame = driver.find_element_by_tag_name('iframe')

    driver.switch_to.frame(frame)

    body = browser.find_by_tag('body').first

    body.click()
    body.click()

    body._element.send_keys(texto)

    assert_that(body.html, equal_to_ignoring_case('<p>{}</p>'.format(texto)))

    driver.switch_to.default_content()


@when('forço o status da demanda "{titulo_demanda}" para "{situacao}"')
def step_forcar_status(context, titulo_demanda, situacao):
    demanda = Demanda.objects.filter(titulo=titulo_demanda)

    if demanda.exists():
        demanda = demanda[0]
        demanda.situacao = situacao
        demanda.save()
    else:
        raise Exception("Erro ao atualizar demanda.")
