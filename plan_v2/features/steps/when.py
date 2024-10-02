# -*- coding: utf-8 -*-

from behave import when
from hamcrest import assert_that, greater_than, not_none

from djtools.new_tests.base_test import XPathConstructor  # noqa


@when('olho para o objetivo estratégico do planejamento "{objetivo_nome}"')
def step_objetivo_estrategico(context, objetivo_nome):
    xpath_objetivo = '//div[contains(@class, "general-box") and descendant::div[contains(@class, "primary-info") and h4[contains(text(), "{}")]]]'.format(objetivo_nome)

    browser = context.browser
    obj = browser.find_by_xpath(xpath_objetivo)

    assert_that(obj, not_none(), xpath_objetivo)
    assert_that(len(obj), greater_than(0), xpath_objetivo)

    context.contexto = xpath_objetivo
