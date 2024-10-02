# -*- coding: utf-8 -*-


from behave import then
from hamcrest import assert_that, greater_than


@then('vejo o status do estágio "{status}"')
def step_impl(context, status):
    xpath_padrao = '//span[contains(@class, "active") and contains(text(), "{}") and ancestor::*[contains(@class, "steps")]]'.format(status)

    elemento = context.browser.find_by_xpath(xpath_padrao)

    assert_that(len(elemento), greater_than(0), xpath_padrao)
