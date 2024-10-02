import datetime
from behave import then  # NOQA
from hamcrest import assert_that, equal_to, equal_to_ignoring_case, greater_than, none, not_none, less_than_or_equal_to

from djtools.new_tests.base_test import XPathConstructor
from djtools.new_tests.environment_base import gerar_highlight_screenshot, scroll_to
from djtools.new_tests.utils import force_view_msg, force_click, force_fill, wait_element, abrir_debugger, log

from djtools.new_tests.common_steps.tests import step_test_result  # NOQA


@then('vejo o indicador "{nome_indicador}" com o valor "{valor_indicador}"')
def step_ver_indicador_com_valor(context, nome_indicador, valor_indicador):
    step_ver_indicador(context, nome_indicador)

    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_indicator_value(name=nome_indicador, value=valor_indicador)
    wait_element(my_xpath)
    div = my_xpath.get()

    assert_that(div, not_none(), my_xpath.get_xpath())
    assert_that(len(div), greater_than(0), my_xpath.get_xpath())

    scroll_to(context, my_xpath.get_xpath())
    gerar_highlight_screenshot(context, my_xpath.get_xpath())


@then('vejo o indicador "{nome_indicador}"')
def step_ver_indicador(context, nome_indicador):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_indicator(name=nome_indicador)
    wait_element(my_xpath)
    div = my_xpath.get()

    assert_that(div, not_none(), my_xpath.get_xpath())
    assert_that(len(div), greater_than(0), my_xpath.get_xpath())

    scroll_to(context, my_xpath.get_xpath())
    gerar_highlight_screenshot(context, my_xpath.get_xpath())


@then('{nao:optional}vejo a página "{nome_pagina}"')
def step_ver_pagina(context, nome_pagina, nao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_html_element(element='h2', text=nome_pagina)
    if nao.strip() != 'nao':
        wait_element(my_xpath)
    titulo = my_xpath.get()
    if nao.strip() == 'nao':
        assert_that(len(titulo), equal_to(0), my_xpath.get_xpath())
    else:
        assert_that(len(titulo), greater_than(0), my_xpath.get_xpath())

    gerar_highlight_screenshot(context, my_xpath.get_xpath())


@then('{nao:optional}vejo o botão "{nome_botao}"')
def step_ver_botao(context, nome_botao, nao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_button(nome_botao)
    if nao.strip() != 'nao':
        wait_element(my_xpath)
    botao = my_xpath.get()

    if nao.strip() == 'nao':
        assert_that(len(botao), equal_to(0), my_xpath.get_xpath())
    else:
        assert_that(len(botao), greater_than(0), my_xpath.get_xpath())


@then('{nao:optional}vejo o botão de ação "{nome_botao}"')
def step_ver_botao_acao(context, nome_botao, nao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_button_action(nome_botao)

    if nao.strip() != 'nao':
        wait_element(my_xpath)
    botao = my_xpath.get()

    if nao.strip() == 'nao':
        assert_that(len(botao), equal_to(0), my_xpath.get_xpath())
    else:
        assert_that(len(botao), greater_than(0), my_xpath.get_xpath())


@then('vejo mensagem de {tipo} "{mensagem}"')
def step_ver_mensagem(context, tipo, mensagem):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    if tipo.lower() == 'erro':
        tipo_msg = XPathConstructor.MSG_ERROR
    elif tipo.lower() == 'sucesso':
        tipo_msg = XPathConstructor.MSG_SUCESS
    elif tipo.lower() == 'alerta':
        tipo_msg = XPathConstructor.MSG_ALERT

    force_view_msg(my_xpath, tipo_msg, mensagem)
    scroll_to(context, my_xpath.get_xpath())
    msg = my_xpath.get()
    assert_that(len(msg), greater_than(0), my_xpath.get_xpath())
    gerar_highlight_screenshot(context, my_xpath.get_xpath())


@then('nao vejo mensagem de {tipo} "{mensagem}"')
def step_nao_ver_mensagem(context, tipo, mensagem):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    # if tipo.lower() == 'erro':
    #    type = XPathConstructor.MSG_ERROR
    # elif tipo.lower() == 'sucesso':
    #    type = XPathConstructor.MSG_SUCESS
    # elif tipo.lower() == 'alerta':
    #    type = XPathConstructor.MSG_ALERT

    scroll_to(context, my_xpath.get_xpath())
    msg = my_xpath.get()
    assert_that(len(msg), equal_to(0), my_xpath.get_xpath())
    gerar_highlight_screenshot(context, my_xpath.get_xpath())


@then("vejo os seguintes campos no formulário")
def step_ver_campos_formularios(context):
    for row in context.table:
        campo = row['Campo']
        tipo = row['Tipo'].lower()

        my_xpath = XPathConstructor(context.browser, context.contexto)
        my_xpath.find_form_input(campo, tipo)
        wait_element(my_xpath)
        field = my_xpath.get()

        assert_that(len(field), greater_than(0), my_xpath.get_xpath())


@then("vejo os seguintes erros no formulário")
def step_ver_erros_formulario(context):
    for row in context.table:
        my_xpath = XPathConstructor(context.browser, context.contexto)
        my_xpath.find_input_error(label_name=row['Campo'], error_text=row['Mensagem'])

        error_msg = my_xpath.get()
        log(my_xpath)

        assert_that(len(error_msg), greater_than(0), my_xpath.get_xpath())


@then('{nao:optional}vejo o texto "{texto}"')
def step_ver_texto(context, texto, nao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_html_element(element='*', text=texto)

    if nao.strip() != 'nao':
        wait_element(my_xpath)
    elemento = my_xpath.get()

    if nao.strip() == 'nao':
        assert_that(len(elemento), equal_to(0), my_xpath.get_xpath())
    else:
        assert_that(len(elemento), greater_than(0), my_xpath.get_xpath())

    gerar_highlight_screenshot(context, my_xpath.get_xpath())


@then('{nao:optional}vejo a aba "{nome_tab}"')
def step_ver_aba(context, nome_tab, nao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_tab(name=nome_tab)

    if nao.strip() != 'nao':
        wait_element(my_xpath)
    tab = my_xpath.get()

    if nao.strip() == 'nao':
        assert_that(len(tab), equal_to(0), my_xpath.get_xpath())
    else:
        assert_that(len(tab), greater_than(0), my_xpath.get_xpath())


@then('{nao:optional}vejo o quadro "{nome_box}"')
def step_ver_quadro(context, nome_box, nao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_box(box_name=nome_box)
    if nao.strip() != 'nao':
        wait_element(my_xpath)
    tab = my_xpath.get()

    if nao.strip() == 'nao':
        assert_that(len(tab), equal_to(0), my_xpath.get_xpath())
    else:
        assert_that(len(tab), greater_than(0), my_xpath.get_xpath())


@then('{nao:optional}vejo a caixa de informações "{nome_box}" com "{informacao}"')
def step_ver_caixa_informacoes(context, nome_box, informacao, nao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_box_info(box_name=nome_box, informacao=informacao)

    if nao.strip() != 'nao':
        wait_element(my_xpath)
    tab = my_xpath.get()

    if nao.strip() == 'nao':
        assert_that(len(tab), equal_to(0), my_xpath.get_xpath())
    else:
        assert_that(len(tab), greater_than(0), my_xpath.get_xpath())


@then('{nao:optional}vejo o item "{item}" no autocomplete "{autocomplete}"')
def step_ver_item_autocomplete(context, item, autocomplete, nao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_item_autocomplete(autocomplete=autocomplete, item=item)
    if nao.strip() != 'nao':
        wait_element(my_xpath)
    element = my_xpath.get()

    if nao.strip() == 'nao':
        assert_that(len(element), equal_to(0), my_xpath.get_xpath())
    else:
        assert_that(len(element), greater_than(0), my_xpath.get_xpath())


@then('{nao:optional}vejo o item de menu "{item_menu}"')
def step_ver_item_menu(context, item_menu, nao):
    my_xpath = XPathConstructor(context.browser)
    items = item_menu.split('::')

    achou = True

    for i in range(len(items)):
        my_xpath.reset()
        my_xpath.find_item_menu(items[: (i + 1)])
        item = my_xpath.get()

        if len(item) == 0:
            achou = False
            break

        item = item.first

        if not item.visible:
            my_xpath.reset()
            my_xpath.find_item_menu(items[:i])
            force_click(my_xpath)
        force_click(my_xpath)

    if nao == 'nao':
        assert_that(achou, equal_to(False))
    else:
        assert_that(achou, equal_to(True))


@then('{nao:optional}vejo a linha "{texto}"')
def step_ver_linha(context, texto, nao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_html_tr(text=texto)
    if nao.strip() != 'nao':
        wait_element(my_xpath)
    linha = my_xpath.get()

    if nao == 'nao':
        assert_that(linha, none(), my_xpath.get_xpath())
        assert_that(len(linha), equal_to(0), my_xpath.get_xpath())
    else:
        assert_that(linha, not_none(), my_xpath.get_xpath())
        assert_that(len(linha), greater_than(0), my_xpath.get_xpath())


@then("vejo os seguintes campos no formulário com as obrigatoriedades atendidas")
def step_ver_campos_formularios_obrigatoriedades(context):
    def step_clicar_botao(context, nome_botao):
        my_xpath = XPathConstructor(context.browser, context.contexto)
        my_xpath.find_button(nome_botao)

        botao = my_xpath.get()
        assert_that(len(botao), greater_than(0), my_xpath.get_xpath())

        gerar_highlight_screenshot(context, my_xpath.get_xpath())

        context.browser.execute_script('confirm = function(msg){return true;};')
        force_click(my_xpath)

        context.contexto = ''

    def step_ver_erros_formulario(context):
        for row in context.table:
            if row['Obrigatório'] == "Sim":
                my_xpath = XPathConstructor(context.browser, context.contexto)
                my_xpath.find_input_error(label_name=row['Campo'], error_text="Este campo é obrigatório")

                error_msg = my_xpath.get()

                assert_that(len(error_msg), greater_than(0), my_xpath.get_xpath())

    step_ver_campos_formularios(context)
    step_ver_botao(context, "Salvar", "")
    step_clicar_botao(context, "Salvar")
    step_ver_mensagem(context, "erro", "Por favor, corrija os erros abaixo.", "")
    step_ver_erros_formulario(context)


@then('vejo os seguintes campos no formulário com as obrigatoriedades atendidas e preencho com')
def step_ver_campos_formularios_obrigatoriedades_preenchidos(context):
    def step_clicar_botao(context, nome_botao):
        my_xpath = XPathConstructor(context.browser, context.contexto)
        my_xpath.find_button(nome_botao)

        botao = my_xpath.get()
        assert_that(len(botao), greater_than(0), my_xpath.get_xpath())

        gerar_highlight_screenshot(context, my_xpath.get_xpath())

        context.browser.execute_script('confirm = function(msg){return true;};')
        force_click(my_xpath)

        context.contexto = ''

    def step_ver_erros_formulario(context):
        for row in context.table:
            if row['Obrigatório'] == "Sim":
                my_xpath = XPathConstructor(context.browser, context.contexto)
                my_xpath.find_input_error(label_name=row['Campo'], error_text="Este campo é obrigatório")
                error_msg = my_xpath.get()
                assert_that(len(error_msg), greater_than(0), my_xpath.get_xpath())

    def step_preencher_formulario(context):
        def fill_autocomplete(context, valor, log_data):
            force_fill(my_xpath, valor)

            item_xpath = XPathConstructor(context.browser, context.contexto)
            item_xpath.xpath = '//li[ancestor::div[@class="ac_results" and descendant::*[contains(text(), "{}")]]]'.format(row['Valor'])
            log_data += f' -> {item_xpath}'

            browser = context.browser
            browser.screenshot()

            contador = 5
            item = None
            while contador > 0:
                if browser.is_element_present_by_xpath(item_xpath.xpath):
                    item = browser.find_by_xpath(item_xpath.xpath)
                    browser.screenshot()
                    break
                contador -= 1

            assert_that(len(item), greater_than(0), log_data)

            force_click(item_xpath)

        def fill_autocomplete_multiplo(context, valor, log_data):
            force_click(my_xpath)

            xpath_input = XPathConstructor(context.browser, context.contexto)
            xpath_input.xpath = f'{my_xpath.get_xpath()}/span/ul/li/input'
            force_fill(xpath_input, valor)

            xpath_local = XPathConstructor(context.browser, context.contexto)
            xpath_local.xpath = '//li[contains(@class,"select2-results__option") and (contains(text(), "{0}") or descendant::*[contains(text(), "{0}")])]'.format(row['Valor'])
            log_data += f' -> {xpath_local}'

            browser = context.browser
            browser.screenshot()

            force_click(xpath_local)

        browser = context.browser
        for row in context.table:
            campo = row['Campo']
            tipo = row['Tipo'].lower()
            valor = row['Valor']
            if not valor:
                continue

            my_xpath = XPathConstructor(context.browser, context.contexto)
            if tipo != 'texto rico':
                my_xpath.find_form_input(campo, tipo)
                log_data = my_xpath.get_xpath()

            if tipo == 'texto':
                input_text = my_xpath.get()
                input_text.first.fill(valor)
            elif tipo == 'data':
                data_id = my_xpath.get().first._element.get_property('id')
                data_type = my_xpath.get().first._element.get_property('type')
                if data_type == 'date':
                    valor = datetime.datetime.strptime(valor, '%d/%m/%Y').strftime('%Y-%m-%d')
                    browser.execute_script(f'$("#{data_id}").val("{valor}");')
                elif data_type == 'datetime-local':
                    if len(valor) == 10:
                        valor = f'{valor} 00:00:00'
                    valor = datetime.datetime.strptime(valor, '%d/%m/%Y %H:%M:%S').strftime('%Y-%m-%dT%H:%M:%S')
                    browser.execute_script(f'$("#{data_id}").val("{valor}");')
            elif tipo == 'textarea':
                text_area = my_xpath.get()
                text_area.first.fill(valor)
            elif tipo == 'lista':
                wait_element(my_xpath)
                my_xpath.find_form_select_option(valor)
                force_click(my_xpath)
            elif tipo == 'arvore':
                wait_element(my_xpath)
                my_xpath.find_form_arvore(valor)
                force_click(my_xpath)
            elif tipo == 'checkbox':
                input_text = my_xpath.get()
                if input_text.first.selected and valor.lower() == 'desmarcar':
                    force_click(my_xpath)
                elif not input_text.first.selected and valor.lower() == 'marcar':
                    force_click(my_xpath)
            elif tipo == 'autocomplete':
                fill_autocomplete(context, valor, log_data)
            elif tipo == 'autocomplete multiplo':
                for valor_unico in valor.split(','):
                    my_xpath.reset()
                    my_xpath.find_form_input(campo, tipo)
                    fill_autocomplete_multiplo(context, valor_unico.strip(), log_data)
            elif tipo == 'filteredselectmultiple':
                for valor_unico in valor.split(','):
                    my_xpath.reset()
                    my_xpath.find_form_input(campo, tipo)
                    my_xpath.find_form_select_option(valor_unico.strip())
                    force_click(my_xpath)

                my_xpath.reset()
                my_xpath.find_form_filteredselectmultiple_add(campo)
                force_click(my_xpath)
            elif tipo == 'arquivo':
                input_file = my_xpath.get()
                filename = browser.screenshot(name=valor)
                input_file.first.fill(filename)
            elif tipo == 'texto rico':
                contador = 5
                while contador > 0:
                    if browser.is_element_present_by_tag('iframe'):
                        break
                    contador -= 1
                    # sleep(1)

                driver = browser.driver

                label = browser.find_by_xpath(f'//label[contains(normalize-space(text()), "{campo}")]')
                frame = driver.find_element_by_xpath('//iframe[contains(normalize-space(@title), "{}")]'.format(label.first['for']))

                driver.switch_to.frame(frame)
                body = browser.find_by_tag('body').first
                body.click()
                body.click()
                body._element.send_keys(valor)

                assert_that(body.html, equal_to_ignoring_case(f'<p>{valor}</p>'))

                driver.switch_to.default_content()
            elif tipo == 'busca':
                force_click(my_xpath)

    step_ver_campos_formularios(context)
    step_clicar_botao(context, "Salvar")
    step_ver_mensagem(context, "erro", "Por favor, corrija os erros abaixo.")
    step_ver_erros_formulario(context)
    step_preencher_formulario(context)


@then('abro o debugger')
def step_abro_debugger(context):
    abrir_debugger(context)


@then('vejo o status "{status}"')
def step_ver_status(context, status):
    xpath_padrao = f'//span[contains(@class, "active") and contains(text(), "{status}") and ancestor::*[contains(@class, "steps")]]'

    elemento = context.browser.find_by_xpath(xpath_padrao)

    assert_that(len(elemento), greater_than(0), xpath_padrao)


@then('{nao:optional}vejo mais de {resultados_esperados} resultados na tabela')
def step_vejo_mais_resultados_na_tabela(context, resultados_esperados, nao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_html_tr()
    linhas = len(my_xpath.get())

    esperado = int(resultados_esperados)
    if nao == 'nao':
        assert_that(linhas - 1, less_than_or_equal_to(esperado), len(my_xpath.get_xpath()))
    else:
        assert_that(linhas - 1, greater_than(esperado), len(my_xpath.get_xpath()))
