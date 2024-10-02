import datetime
import time
from freezegun import freeze_time

from behave import when  # NOQA
from hamcrest import assert_that, greater_than, not_none, equal_to_ignoring_case

from djtools.new_tests.base_test import XPathConstructor
from djtools.new_tests.environment_base import gerar_highlight_screenshot, gerar_screenshot, scroll_to
from djtools.new_tests.utils import wait_click, log, force_click, force_fill, force_click_checkbox, wait_element, \
    wait_url_change, force_fill_file, abrir_debugger, go_url, log_text  # NOQA

from djtools.new_tests.common_steps.tests import step_test_run  # NOQA


# Funções que mudan o contexto -----------------------------------------------------------------------------------------


@when('olho para a página')
def step_impl(context):
    scroll_to(context, None)
    context.contexto = ''


@when('olho para o quadro "{nome_quadro}"')
def step_olhar_quadro(context, nome_quadro):
    quadro_path = XPathConstructor(context.browser, context.contexto)
    quadro_path.find_box(nome_quadro)
    wait_element(quadro_path)
    quadro = quadro_path.get()

    log(quadro_path)
    assert_that(quadro, not_none(), quadro_path.get_xpath())
    assert_that(len(quadro), greater_than(0), quadro_path.get_xpath())

    gerar_highlight_screenshot(context, quadro_path.get_xpath())

    context.contexto = quadro_path.get_xpath()


@when('olho para os filtros')
def step_olhar_filtros(context):
    quadro_path = XPathConstructor(context.browser, context.contexto)
    quadro_path.find_filters()
    wait_element(quadro_path)
    quadro = quadro_path.get()

    log(quadro_path)
    assert_that(quadro, not_none(), quadro_path.get_xpath())
    assert_that(len(quadro), greater_than(0), quadro_path.get_xpath())

    gerar_highlight_screenshot(context, quadro_path.get_xpath())

    context.contexto = quadro_path.get_xpath()


@when('olho para a listagem')
def step_olhar_listagem(context):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_html_table(id_name='result_list')
    wait_element(my_xpath)
    tabela = my_xpath.get()

    log(my_xpath)
    assert_that(tabela, not_none(), my_xpath.get_xpath())
    assert_that(len(tabela), greater_than(0), my_xpath.get_xpath())

    gerar_highlight_screenshot(context, my_xpath.get_xpath())

    context.contexto = my_xpath.get_xpath()


@when('olho para a tabela')
def step_olhar_tabela(context):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_html_table()
    wait_element(my_xpath)
    tabela = my_xpath.get()

    log(my_xpath)
    assert_that(tabela, not_none(), my_xpath.get_xpath())
    assert_that(len(tabela), greater_than(0), my_xpath.get_xpath())

    gerar_highlight_screenshot(context, my_xpath.get_xpath())

    context.contexto = my_xpath.get_xpath()


@when('olho a linha "{texto}"')
def step_olhar_linha(context, texto):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_html_tr(text=texto)
    wait_element(my_xpath)
    linha = my_xpath.get()

    log(my_xpath)
    assert_that(linha, not_none(), my_xpath.get_xpath())
    assert_that(len(linha), greater_than(0), my_xpath.get_xpath())

    gerar_highlight_screenshot(context, my_xpath.get_xpath())

    context.contexto = my_xpath.get_xpath()


@when('olho para o popup')
def step_olhar_popup(context):
    iframe = context.browser.driver.find_element_by_xpath(xpath="//iframe[@class='fancybox-iframe']")
    context.browser.driver.switch_to.frame(frame_reference=iframe)
    context.popup.append(context.contexto)
    context.contexto = ''


@when('olho para a aba "{nome_tab}"')
def step_olhar_aba(context, nome_tab):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_tab_content(name=nome_tab)
    wait_element(my_xpath)
    div = my_xpath.get()

    log(my_xpath)
    assert_that(div, not_none(), my_xpath.get_xpath())
    assert_that(len(div), greater_than(0), my_xpath.get_xpath())

    gerar_highlight_screenshot(context, my_xpath.get_xpath())

    context.contexto = my_xpath.get_xpath()


@when('fecho o popup')
def step_fecho_popup(context):
    context.contexto = context.popup.pop()
    context.browser.driver.switch_to.parent_frame()

    context.browser.execute_script('jQuery.fancybox.close();')
    context.contexto = ''


@when('o popup é fechado')
def step_popup_fechado(context):
    context.contexto = context.popup.pop()
    context.browser.driver.switch_to.parent_frame()


# Funções que modificam a lib ------------------------------------------------------------------------------------------


@when('a data do sistema for "{data}"')
def step_data_sistema(context, data):
    try:
        context.browser.time_freezer.stop()
    except Exception:
        pass
    dia, mes, ano = data.split('/')
    time_freezer = freeze_time(f"{ano}-{mes}-{dia}", tick=True)
    context.browser.time_freezer = time_freezer
    time_freezer.start()


@when('retorna a data do sistema')
def step_retorna_data_sistema(context):
    try:
        context.browser.time_freezer.stop()
    except Exception:
        pass


# Funções específicas --------------------------------------------------------------------------------------------------


@when('realizo o login com o usuário "{usuario}" e senha "{senha}"')
def step_do_login(context, usuario, senha):
    my_xpath = XPathConstructor(context.browser)

    inputs = [{'nome': 'Usuário:', 'valor': usuario, 'tipo': 'texto'}, {'nome': 'Senha:', 'valor': senha, 'tipo': 'senha'}]

    for i in inputs:
        my_xpath.reset()
        my_xpath.find_form_input(i['nome'], i['tipo'])
        log(my_xpath)
        force_fill(my_xpath, i['valor'])

    my_xpath.reset()
    my_xpath.find_submit_button('Acessar')
    log(my_xpath)
    force_click(my_xpath)
    my_xpath.find_user()
    assert my_xpath.get().first['title'] == f'Nome de usuário: {usuario}'


@when('acesso o menu "{item_menu}"')
def step_acessar_menu(context, item_menu, from_search=False):
    """
    Essa função serve tanto para acessar o menu interno do SUAP quanto para o menu anônimo.
    """
    old_url = context.browser.driver.current_url
    my_xpath = XPathConstructor(context.browser)
    items = item_menu.split('::')
    if from_search:
        my_xpath.find_item_menu(items, class_menu='')
    else:
        for i in range(len(items)):
            my_xpath.reset()
            my_xpath.find_item_menu(items[: (i + 1)])
            item = my_xpath.get().first
            if not item.visible:
                xpath_parent = XPathConstructor(context.browser)
                xpath_parent.find_item_menu(items[:i])
                force_click(xpath_parent)
    wait_element(my_xpath)
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
    force_click(my_xpath)
    try:
        wait_url_change(context.browser, old_url)
    except Exception:
        # forçando novo clique caso a nova página não tenha sido carregada.
        force_click(my_xpath)


@when('pesquiso por "{item_menu}" e acesso o menu "{path_menu}"')
def step_pesquisar_menu(context, item_menu, path_menu):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_menu_input()
    force_fill(my_xpath, item_menu)
    wait_element(my_xpath)
    step_acessar_menu(context, path_menu, True)


# Funções de manipulação -----------------------------------------------------------------------------------------------


@when('clico no botão "{nome_botao}"')
def step_clicar_botao(context, nome_botao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_button(nome_botao)
    log(my_xpath)
    wait_click(my_xpath)
    wait_click(my_xpath)
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
    context.browser.execute_script('confirm = function(msg){return true;};')
    force_click(my_xpath)
    context.contexto = ''


@when('olho e clico no botão "{nome_botao}"')
def step_mover_e_clicar_botao(context, nome_botao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_button(nome_botao)
    log(my_xpath)
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
    context.browser.execute_script('confirm = function(msg){return true;};')
    force_click(my_xpath)
    context.contexto = ''


@when('clico no botão de ação "{nome_botao}"')
def step_clicar_botao_acao(context, nome_botao):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_button_action(nome_botao)
    log(my_xpath)
    wait_element(my_xpath)
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
    context.browser.execute_script('confirm = function(msg){return true;};')
    force_click(my_xpath)
    context.contexto = ''


@when('clico no link "{nome_link}"')
def step_clicar_link(context, nome_link):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_link(nome_link)
    log(my_xpath)
    wait_element(my_xpath)
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
    context.browser.execute_script('confirm = function(msg){return true;};')
    force_click(my_xpath)
    context.contexto = ''


@when('clico no link h4 "{nome_link}"')
def step_clicar_h4_link(context, nome_link):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_link_h4(nome_link)
    log(my_xpath)
    wait_element(my_xpath)
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
    context.browser.execute_script('confirm = function(msg){return true;};')
    force_click(my_xpath)
    context.contexto = ''


@when('clico no quadro "{nome_quadro}"')
def step_clicar_box(context, nome_quadro):
    quadro_path = XPathConstructor(context.browser, context.contexto)
    quadro_path.find_box(nome_quadro)
    wait_element(quadro_path)
    gerar_highlight_screenshot(context, quadro_path.get_xpath())
    force_click(quadro_path)
    context.contexto = ''


@when('clico no indicador "{nome_indicador}"')
def step_clicar_indicador(context, nome_indicador):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_indicator(nome_indicador)
    log(my_xpath)
    wait_element(my_xpath)
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
    context.browser.execute_script('confirm = function(msg){return true;};')
    force_click(my_xpath)
    context.contexto = ''


@when('clico no ícone de {nome_link}')
def step_clicar_icone(context, nome_link):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    icon = None
    if nome_link == 'edição':
        icon = 'icon-edit'
    elif nome_link == 'exibição':
        icon = 'icon-view'
    elif nome_link == 'remoção':
        icon = 'icon-delete'
    elif nome_link == 'configuração':
        icon = 'icon-cog'
    my_xpath.find_html_element(element='a', class_name=icon)
    log(my_xpath)
    wait_element(my_xpath)
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
    context.browser.execute_script('confirm = function(msg){return true;};')
    force_click(my_xpath)
    context.contexto = ''


@when('clico na aba "{nome_tab}"')
def step_clicar_aba(context, nome_tab):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_tab(name=nome_tab)
    log(my_xpath)
    wait_element(my_xpath)
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
    force_click(my_xpath)


@when('removo o item "{item}" no autocomplete "{autocomplete}"')
def step_clicar_item_autocomplete(context, item, autocomplete):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_item_autocomplete(autocomplete=autocomplete, item=item)
    log(my_xpath)
    force_click(my_xpath)


@when('preencho as linhas do quadro "{obj}" com os dados')
def step_preencher_linha(context, obj):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_box(obj)
    context.contexto = my_xpath.get_xpath()

    for linha in range(len(context.table.rows)):
        row = context.table.rows[linha]
        for i in range(len(row)):
            valor = row[i]
            coluna, tipo = context.table.headings[i].lower().split(":")
            from unicodedata import normalize, combining

            nfkd = normalize('NFKD', coluna)
            coluna = "".join([c for c in nfkd if not combining(c)])
            row_xpath = XPathConstructor(context.browser, context.contexto)
            if tipo == 'lista':
                row_xpath.find_form_inline_select_option(valor, linha, coluna)
                force_click(row_xpath)
            elif tipo == 'texto':
                row_xpath.find_form_inline_input(linha, coluna)
                force_fill(row_xpath, valor)
            elif tipo == 'checkbox':
                pass
                # TODO:implementar para checkbox
            # TODO: se não achar linha clicar no link adicionar outro
    step_impl(context)


@when('preencho o formulário com os dados')
def step_preencher_formulario(context):
    def fill_autocomplete(context, valor, log_data):
        force_click(my_xpath)

        xpath_input = XPathConstructor(context.browser, context.contexto)
        xpath_input.xpath = '//span[contains(@class, "select2-search--dropdown")]/input'
        force_fill(xpath_input, valor)

        xpath_local = XPathConstructor(context.browser, context.contexto)
        xpath_local.xpath = '//li[contains(@class,"select2-results__option") and (contains(text(), "{0}") or descendant::*[contains(text(), "{0}")])]'.format(row['Valor'])
        log_data += f' -> {xpath_local.get_xpath()}'

        context.browser.screenshot()

        force_click(xpath_local)

    def fill_autocomplete_multiplo(context, valor, log_data):
        force_click(my_xpath)

        xpath_input = XPathConstructor(context.browser, context.contexto)
        xpath_input.xpath = f'{my_xpath.get_xpath()}/span/ul/li/input'
        force_fill(xpath_input, valor)

        xpath_local = XPathConstructor(context.browser, context.contexto)
        xpath_local.xpath = '//li[contains(@class,"select2-results__option") and (contains(text(), "{0}") or descendant::*[contains(text(), "{0}")])]'.format(row['Valor'])

        context.browser.screenshot()

        log_data += f' -> {xpath_local.get_xpath()}'

        force_click(xpath_local)

    browser = context.browser
    my_xpath = XPathConstructor(context.browser, context.contexto)
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
    for row in context.table:
        # Tem que zerar o xpath para garantir que o campo do formulário vai ser encontrado
        my_xpath = XPathConstructor(context.browser, context.contexto)
        campo = row['Campo']
        tipo = row['Tipo'].lower()
        valor = row['Valor']
        if tipo not in ('texto rico', 'checkbox multiplo', 'radio', 'checkbox popup'):
            log_data = my_xpath.get_xpath()
            my_xpath.find_form_input(campo, tipo)

        if tipo in ('texto', 'textarea', 'senha'):
            force_fill(my_xpath, valor)

        elif tipo in ('checkbox multiplo', 'radio'):
            for valor_unico in valor.split(','):
                my_xpath.reset()
                my_xpath.find_form_input(campo, tipo, valor_unico.strip())
                log(my_xpath)
                force_click(my_xpath)

        elif tipo == 'checkbox popup':
            my_xpath.xpath = '//input[contains(@class, "popup_multiple_choice_field") and ancestor::div[preceding-sibling::label[contains(normalize-space(text()), "{}")]]]'.format(
                campo
            )
            item = browser.find_by_xpath(my_xpath.get_xpath())
            wait_click(my_xpath)
            item.first.click()
            for valor_unico in valor.split(','):
                my_xpath.reset()
                my_xpath.xpath = f'//input[contains(@title, "{valor_unico}")]'
                force_click(my_xpath)
            my_xpath.reset()
            my_xpath.xpath = '//input[contains(@value, "Confirmar")]'
            force_click(my_xpath)

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

        elif tipo == 'hora':
            data_id = my_xpath.get().first._element.get_property('id')
            if len(valor) == 5:
                valor = f'{valor}:00'
            browser.execute_script(f'$("#{data_id}").val("{valor}");')

        elif tipo == 'lista':
            wait_element(my_xpath)
            my_xpath.find_form_select_option(valor)
            force_click(my_xpath)

        elif tipo == 'checkbox':
            force_click_checkbox(my_xpath, valor)

        elif tipo == 'autocomplete':
            fill_autocomplete(context, valor, log_data)

        elif tipo == 'filteredselectmultiple':
            for valor_unico in valor.split(','):
                my_xpath.reset()
                my_xpath.find_form_input(campo, tipo)
                my_xpath.find_form_select_option(valor_unico.strip())
                force_click(my_xpath)
            my_xpath.reset()
            my_xpath.find_form_filteredselectmultiple_add(campo)
            force_click(my_xpath)

        elif tipo == 'autocomplete multiplo':
            for valor_unico in valor.split(','):
                my_xpath.reset()
                my_xpath.find_form_input(campo, tipo)
                fill_autocomplete_multiplo(context, valor_unico.strip(), log_data)

        elif tipo == 'arquivo':
            filename = browser.screenshot(name=valor)
            time.sleep(2)
            force_fill_file(my_xpath, campo, filename, False)

        elif tipo == 'arquivo real':
            force_fill_file(my_xpath, campo, valor, True)

        elif tipo == 'texto rico':
            contador = 5
            while contador > 0:
                if browser.is_element_present_by_tag('iframe'):
                    break
                contador -= 1

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
        log(my_xpath)


@when('acesso a página "{url}"')
def step_acessar_pagina(context, url):
    go_url(context, url)
    gerar_screenshot(context)


@when('atualizo a página')
def step_atualizar_pagina(context):
    context.browser.reload()


@when('gero um screenshot - "{marcador}"')
def step_gerar_screenshot(context, marcador):
    print(f'{marcador}: {context.browser.screenshot()}')


@when('gero um erro')
def step_gerar_erro(_):
    assert True == False


@when('seleciono o item "{obj}" da lista')
def step_selecionar_checkbox(context, obj):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_checkbox(obj)
    wait_element(my_xpath)
    log(my_xpath)
    force_click(my_xpath)


@when('clico no checkbox')
def step_clico_checkbox(context):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_html_element(element='input')
    log(my_xpath)
    force_click(my_xpath)


@when('clico no link "{nome_link}" na listagem das áreas')
def step_clicar_link_lista_area_servicos(context, nome_link):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_link_h4(nome_link)
    link = my_xpath.get()
    assert_that(len(link), greater_than(0), my_xpath.get_xpath())
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
    context.browser.execute_script('confirm = function(msg){return true;};')
    link.first.click()
    context.contexto = ''


@when('abro o debugger')
def step_abro_debugger(context):
    abrir_debugger(context)


@when('seleciono o custom checkbox "{nome_do_checkbox}"')
def step_selecionar_custom_checkbox(context, nome_do_checkbox):
    my_xpath = XPathConstructor(context.browser, context.contexto)
    my_xpath.find_custom_checkbox(nome_do_checkbox)
    link = my_xpath.get()
    assert_that(len(link), greater_than(0), my_xpath.get_xpath())
    gerar_highlight_screenshot(context, my_xpath.get_xpath())
    context.browser.execute_script('confirm = function(msg){return true;};')
    link.first.click()
    context.contexto = ''
