# -*- coding: utf-8 -*-


from behave import when

from djtools.new_tests.base_test import XPathConstructor
from djtools.new_tests.utils import log


@when('preencho o inline "{titulo_inline}" com os dados')
def step_preencher_formulario(context, titulo_inline):
    linhas_xpath = XPathConstructor(context.browser, context.contexto)
    linhas_xpath.xpath = '//div[contains(@class, "tabular inline") and ./fieldset/h2[text()="{}"]]/fieldset/table/tbody/tr[contains(@class, "form-row")]'.format(titulo_inline)
    index_linha = 1
    for row in context.table:
        index_coluna = 2
        for head, cell in list(row.items()):
            tipo = head.lower()
            valor = cell
            xpath_coluna = XPathConstructor(context.browser, context.contexto)
            xpath_coluna.xpath += linhas_xpath.xpath + '[{}]//td[{}]'.format(index_linha, index_coluna)
            xpath_especifico = XPathConstructor(context.browser, context.contexto)
            if tipo == 'texto':
                xpath_especifico.xpath += xpath_coluna.xpath + '//input[@type="text"]'
                input_text = xpath_especifico.get()
                input_text.first.fill(valor)
            elif tipo == 'checkbox':
                xpath_especifico.xpath += xpath_coluna.xpath + '//input[@type="checkbox"]'
                checkbox = xpath_especifico.get()
                if checkbox and checkbox.first.selected and valor.lower() == 'desmarcar':
                    checkbox.first.click()
                elif checkbox and not checkbox.first.selected and valor.lower() == 'marcar':
                    checkbox.first.click()
            log(xpath_especifico)
            index_coluna += 1
        index_linha += 1
