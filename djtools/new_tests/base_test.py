import json
from collections import OrderedDict

from django.utils.text import slugify


class Passo:
    def __init__(self, nome, imagem, descricao=''):
        self.nome = nome[0].upper() + nome[1:]
        self.descricao = descricao
        self.imagem = imagem.split('/')[-1]

    def default(self, o):
        return

    def show(self):
        print('---> {}'.format(self.nome))


class Cenario:
    def __init__(self, nome, descricao, funcionalidade, workflow=None):
        self.nome = nome
        self.descricao = descricao
        self.passos = list()
        self.workflows = OrderedDict()
        if workflow:
            self.add_workflow(workflow)

    def add_passo(self, passo):
        self.passos.append(passo)

    def add_workflow(self, workflow):
        self.workflows[workflow[0]] = workflow[1]

    def show(self):
        print('\n--> {}'.format(self.nome))

        print('Passos:')
        print('-' * 30)

        for p in self.passos:
            p.show()


class Funcionalidade:
    def __init__(self, nome, descricao, app_name, workflows=OrderedDict()):
        self.nome = nome
        self.descricao = descricao
        self.app_name = app_name
        self.cenarios = OrderedDict()
        self.workflows = workflows

    def add_cenario(self, cenario):
        self.cenarios[slugify(cenario.nome.strip())] = cenario

    def get_cenario(self, cenario):
        return self.cenarios[slugify(cenario.strip())]

    def has_cenario(self, cenario):
        return cenario.strip() in self.cenarios

    def add_workflow(self, workflow):
        self.workflows[workflow[0]] = workflow[1]

    def show(self):
        print('-> {}\n'.format(self.nome))

        print('Cenários:')
        print('-' * 30)

        for c in list(self.cenarios.values()):
            c.show()


class Aplicacao:
    def __init__(self, sigla, nome, area):
        self.sigla = sigla
        self.nome = nome
        self.area = area
        self.funcionalidades = OrderedDict()

    def add_funcionalidade(self, funcionalidade):
        self.funcionalidades[funcionalidade.nome] = funcionalidade

    def get_funcionalidade(self, funcionalidade):
        return self.funcionalidades[funcionalidade]

    def has_funcionalidade(self, funcionalidade):
        return funcionalidade.strip() in self.funcionalidades


class Documentacao:
    def __init__(self):
        self.aplicacoes = OrderedDict()

    def add_aplicacao(self, aplicacao):
        self.aplicacoes[aplicacao.sigla.strip()] = aplicacao

    def get_aplicacao(self, aplicacao):
        return self.aplicacoes[aplicacao.strip()]

    def has_aplicacao(self, aplicacao):
        return aplicacao.strip() in self.aplicacoes

    def toJSON(self):
        my_json = OrderedDict()

        my_json['aplicacoes'] = OrderedDict()
        for k_a, a in self.aplicacoes.items():
            aplicacao = OrderedDict()
            aplicacao['sigla'] = a.sigla
            aplicacao['nome'] = a.nome
            aplicacao['area'] = a.area
            aplicacao['funcionalidades'] = list()
            aplicacao['workflows'] = OrderedDict()

            for k_f, f in list(a.funcionalidades.items()):
                funcionalidade = OrderedDict()
                funcionalidade['chave'] = k_f
                funcionalidade['nome'] = f.nome
                funcionalidade['descricao'] = list(f.descricao)
                funcionalidade['app_name'] = f.app_name
                funcionalidade['cenarios'] = list()
                if f.workflows:
                    aplicacao['workflows'].update(f.workflows)

                for k_c, c in list(f.cenarios.items()):
                    cenario = OrderedDict()
                    cenario['chave'] = k_c
                    cenario['nome'] = c.nome
                    cenario['descricao'] = list(c.descricao)
                    cenario['passos'] = list()
                    if f.workflows:
                        aplicacao['workflows'].update(c.workflows)

                    for p in c.passos:
                        passo = OrderedDict()
                        passo['nome'] = p.nome
                        passo['imagem'] = p.imagem
                        passo['descricao'] = p.descricao
                        cenario['passos'].append(passo)

                    funcionalidade['cenarios'].append(cenario)
                aplicacao['funcionalidades'].append(funcionalidade)
            my_json['aplicacoes'][f.app_name] = aplicacao

        return json.dumps(my_json)

    def show(self):
        print('Documentaoção')
        print('=' * 30)

        print('Funcionalidades:')
        print('-' * 30)

        for f in list(self.funcionalidades.values()):
            f.show()


INPUT_TYPES = {
    'texto': 'input',
    'senha': 'password',
    'data': 'input',
    'datahora': 'input',
    'hora': 'input',
    'valor': 'input',
    'numero': 'input',
    'arquivo': 'file',
    'arquivo real': 'file',
    'checkbox': 'input',
    'checkbox multiplo': 'multiplecheckbox',
    'checkbox popup': 'multiplecheckbox',
    'textarea': 'textarea',
    'lista': 'select',
    'arvore': 'arvore',
    'radio': 'radio',
    'busca': 'busca',
    'autocomplete': 'autocomplete',
    'autocomplete multiplo': 'autocomplete multiplo',
    'filteredselectmultiple': 'filteredselectmultiple',
    'captcha': 'captcha',
}


class XPathConstructor:
    MSG_ERROR = 0
    MSG_INFO = 1
    MSG_SUCESS = 2
    MSG_ALERT = 3

    def __init__(self, browser, context=''):
        self.context = context
        self.xpath = ''
        self.browser = browser

    def get_context(self):
        return self.context

    def get_xpath(self):
        return '{}'.format(self.xpath)

    def get(self):
        return self.browser.find_by_xpath(self.get_xpath())

    def reset(self):
        self.xpath = ''

    def reset_context(self):
        self.context = ''

    def find_item_menu(self, items, class_menu="_main_menu"):
        if class_menu:
            self.xpath += '//nav/descendant::a[ancestor::ul[contains(@class, "{}")] and @title="{}"]'.format(class_menu, items[0])
        else:
            self.xpath += '//nav/descendant::a[ancestor::ul[@id="_menu_list_expanded"] and @title="{}"]'.format(items[0])
        for item in items[1:]:
            self.xpath += '/following-sibling::ul/child::*/a[@title="{}"]'.format(item)

    def find_filters(self):
        self.xpath = '//div[contains(@class, "search-and-filters")]'

    def find_box(self, box_name):
        box_modulo = '//div[contains(@class, "modulo") and h3//span[contains(normalize-space(.), "{}")]]'.format(box_name)
        box_box = '//div[contains(@class, "box") and h3[contains(normalize-space(.), "{}")]]'.format(box_name)
        box_alertas = '//div[contains(@class, "modulo") and h3[contains(normalize-space(.), "{}")]]'.format(box_name)
        box_fieldset = '//fieldset[contains(@class, "module") and h2[contains(normalize-space(.), "{}")]]'.format(box_name)
        self.xpath = '({}|{}|{}|{})'.format(box_modulo, box_box, box_alertas, box_fieldset)

    def find_box_info(self, box_name, informacao):
        self.xpath = '//div[contains(@class, "extra-info") and contains(normalize-space(.), "{}")]/ancestor::div[contains(@class, "general-box") and div//h4[contains(normalize-space(.), "{}")]]'.format(informacao, box_name)

    # Form elements methods --------------------------------------------------------------------------------------------

    def find_menu_input(self):
        self.xpath += '{}//input[@id="__filterinput__"]'.format(self.context)

    def find_user(self):
        self.xpath = '//div[@id="user-tools"]/a/span'

    def find_form_input(self, label_name, type_input, value_input=None):
        find_label = label_name
        value = ''
        if value_input is not None:
            value = ' and ancestor::*/label[contains(normalize-space(.), "{}")]'.format(value_input)
        if label_name[-1] != ':':
            find_label = '{}:'.format(label_name)
        if INPUT_TYPES[type_input] == 'select':
            self.xpath += '{}//{}[ancestor::*/label[normalize-space(text())="{}"]]'.format(self.context, INPUT_TYPES[type_input], find_label)
        elif type_input == 'checkbox':
            self.xpath += '{0}//{1}[following-sibling::label[contains(normalize-space(.),"{2}")] or preceding-sibling::label[contains(normalize-space(.), "{2}")]]'.format(
                self.context, INPUT_TYPES[type_input], find_label[:-1]
            )
        elif INPUT_TYPES[type_input] == 'textarea':
            self.xpath += '{}//{}[ancestor::*/label[normalize-space(text())="{}"]]'.format(self.context, INPUT_TYPES[type_input], find_label)
        elif INPUT_TYPES[type_input] == 'autocomplete multiplo':
            self.xpath += '{0}//input[ancestor::*/label[normalize-space(text())="{1}"] and @type="text"]|//span[ancestor::*/label[normalize-space(text())="{1}"]]'.format(self.context, find_label)
        elif INPUT_TYPES[type_input] == 'filteredselectmultiple':
            self.xpath += '{}//select[ancestor::*/label[normalize-space(text())="{}"]]'.format(self.context, find_label)
        elif INPUT_TYPES[type_input] == 'autocomplete':
            self.xpath += '{}//span[ancestor::*/label[normalize-space(text())="{}"]]'.format(self.context, find_label)
        elif INPUT_TYPES[type_input] == 'busca':
            self.xpath += '{}//a[contains(@class, "btn") and preceding-sibling::label[contains(normalize-space(.), "{}")]]'.format(self.context, find_label)
        elif type_input == 'radio':
            self.xpath += '{}//input[ancestor::*/label[contains(normalize-space(.), "{}")]{} and @type="radio"]'.format(self.context, find_label, value)
        elif INPUT_TYPES[type_input] == 'multiplecheckbox':
            self.xpath += '{}//input[ancestor::*/label[normalize-space(text())="{}"]{}]'.format(self.context, find_label, value)
        elif INPUT_TYPES[type_input] == 'file':
            self.xpath = '{}//label[contains(normalize-space(.), "{}")]/following-sibling::div/p/input[@type="file"]'.format(self.context, label_name)
        elif INPUT_TYPES[type_input] == 'password':
            self.xpath = '{}//label[contains(normalize-space(.), "{}")]/following-sibling::div/input[@type="password"]'.format(self.context, label_name)
        elif INPUT_TYPES[type_input] == 'captcha':
            self.xpath = '//label[normalize-space(text())="{}"]'.format(find_label)
        else:
            self.xpath += '{}//{}[preceding-sibling::label[normalize-space(text())="{}"]]'.format(self.context, INPUT_TYPES[type_input], find_label)
            # xpath do filtro do admin
            self.xpath += '|//div[contains(@class, "search-and-filters")]//input[ancestor::div[contains(@class, "filter")]//label[normalize-space(text())="{}"]]'.format(find_label)

    def find_form_select_option(self, value):
        self.xpath += '//option[contains(normalize-space(.), "{}")]'.format(value)

    def find_form_arvore(self, value):
        self.xpath += '//a[contains(@class, "jstree-anchor") and text()="{}"]'.format(value)

    def find_form_inline_select_option(self, value, line, column):
        self.xpath += '//option[ancestor::select[contains(@name, "-{}-{}")] and contains(normalize-space(.), "{}")]'.format(line, column, value)

    def find_form_inline_input(self, line, column):
        self.xpath += '//input[contains(@name, "-{}-{}")]'.format(line, column)

    def find_submit_button(self, button_name):
        self.xpath += '{}//input[@type="submit" and @value="{}"]'.format(self.context, button_name)

    def find_submit_button_nonstandard(self, button_name):
        self.xpath += '{}//input[@type="button" and @value="{}"]'.format(self.context, button_name)

    def find_submit_button_action(self, button_name):
        self.xpath += '{}//button[@type="submit" and @value="{}"]'.format(self.context, button_name)

    def find_filter_button(self, button_name):
        self.xpath += '{}//button[@type="submit" and contains(., "{}")]'.format(self.context, button_name)

    def find_just_button(self, button_name):
        self.xpath += '{}//button[contains(., "{}")]'.format(self.context, button_name)

    def find_just_button_by_class(self, class_name):
        self.xpath += '{}//button[contains(@class, "{}")]'.format(self.context, class_name)

    def find_input_error(self, label_name, error_text):
        base_xpath = '{}//label[contains(normalize-space(.), "{}") and ancestor::*//li[contains(normalize-space(.), "{}")]]'.format(self.context, label_name, error_text)
        self.xpath += base_xpath
        return self

    # HTML specific elements -------------------------------------------------------------------------------------------

    def find_html_table(self, class_name=None, id_name=None):
        self.xpath += '{}//table'.format(self.context)

        filters = []

        if class_name is not None:
            filters.append('contains(@class, "{}")'.format(class_name))

        if id_name is not None:
            filters.append('@id="{}"'.format(id_name))

        if len(filters) > 0:
            self.xpath += '[{}]'.format(' and '.join(filters))

    def find_html_tr(self, text=None, class_name=None):
        self.xpath += '{}//tr'.format(self.context)

        filters = []

        if text is not None:
            filters.append('descendant-or-self::*[contains(normalize-space(.), "{}")]'.format(text))

        if class_name is not None:
            filters.append('contains(@class, "{}")'.format(class_name))

        if len(filters) > 0:
            self.xpath += '[{}]'.format(' and '.join(filters))

    # Other methods ----------------------------------------------------------------------------------------------------
    def find_button(self, button_name):
        self.find_submit_button(button_name)
        self.xpath += '|'
        self.find_link_button(button_name)
        self.xpath += '|'
        self.find_submit_button_nonstandard(button_name)
        self.xpath += '|'
        self.find_filter_button(button_name)
        self.xpath += '|'
        self.find_just_button(button_name)

    def find_link_button(self, button_name):
        # Find links on action bar
        self.xpath += '{}//a[contains(normalize-space(.), "{}") and ancestor::ul[contains(@class, "action-bar")]]'.format(self.context, button_name)
        self.xpath += '|{}//a[contains(normalize-space(.), "{}") and contains(@class, "btn")]'.format(self.context, button_name)
        self.xpath += '|{}//a[contains(@title, "{}") and contains(@class, "btn")]'.format(self.context, button_name)
        self.xpath += '|{}//a[contains(normalize-space(.), "{}") and ancestor::ul[contains(@class, "pills")]]'.format(self.context, button_name)

    def find_button_action(self, button_name):
        self.find_submit_button_action(button_name)
        self.xpath += '|'
        self.find_link_button_action(button_name)

    def find_link_button_action(self, button_name):
        # Find links on div actions
        self.xpath += '{}//button[contains(normalize-space(.), "{}") and ancestor::div[contains(@class, "actions")]]'.format(self.context, button_name)

    def find_link(self, value):
        # https://stackoverflow.com/questions/34593753/testing-text-nodes-vs-string-values-in-xpath?answertab=votes#tab-top
        self.xpath += '{}//a[contains(., "{}")]'.format(self.context, value)

    def find_link_h4(self, value):
        self.xpath += '{}//a[descendant::h4[text()="{}"]]'.format(self.context, value)

    def find_custom_checkbox(self, value):
        self.xpath += '{}//h4[descendant::*[normalize-space(text())="{}"]]/parent::*/preceding-sibling::*//label'.format(self.context, value)
        self.xpath += '|'
        self.xpath += '{}//h4[normalize-space(text())="{}"]/parent::*/preceding-sibling::*//label'.format(self.context, value)

    def find_html_element(self, element, class_name=None, id_name=None, text=None):
        xfilter = list()

        if class_name is not None:
            xfilter.append('contains(@class, "{}")'.format(class_name))

        if id_name is not None:
            xfilter.append('@id="{}"'.format(id_name))

        if text is not None:
            xfilter.append('contains(normalize-space(.), "{}")'.format(text))

        self.xpath += '{}//{}'.format(self.context, element)

        if len(xfilter) > 0:
            self.xpath += '[{}]'.format(' and '.join(xfilter))

    def find_item_autocomplete(self, autocomplete, item):
        filter_img = f'//li[contains(@title, "{item}")]//parent::button[ancestor::*/label[contains(., "{autocomplete}")]]'

        self.xpath += f'{self.context}{filter_img}'

    def find_message(self, type, text):
        class_name = 'info'
        if type == self.MSG_SUCESS:
            class_name = "success"
        elif type == self.MSG_INFO:
            class_name = "info"
        elif type == self.MSG_ERROR:
            class_name = "errornote"
        elif type == self.MSG_ALERT:
            class_name = "alert"
        self.xpath += '{}//p[contains(@class, {}) and contains(normalize-space(.), "{}")]'.format(self.context, class_name, text)

    def find_tab(self, name):
        self.xpath += '{}//a[contains(normalize-space(.), "{}") and ancestor::*[contains(@class, "tabs")]]'.format(self.context, name)

    def find_tab_content(self, name):
        self.xpath += '{}//div[contains(@data-title, "{}") and contains(@class, "tab-container") and not(contains(@class, "d-none"))]'.format(self.context, name)

    def find_indicator(self, name):
        self.xpath += '{}//p[@class="description" and contains(normalize-space(string()), "{}") and ancestor::*[contains(@class, "flex-container boxes indicators")]]'.format(self.context, name)
        self.xpath += '|'
        self.xpath += '{}//p[@class="description" and contains(normalize-space(string()), "{}") and ancestor::*[contains(@class, "total-container")]]'.format(self.context, name)

    def find_textarea(self, name):
        self.xpath += f'//h4[contains(normalize-space(.),"{name}")]/parent::*//textarea'

    def find_indicator_value(self, name, value):
        self.xpath += '{}//p[@class="description" and contains(normalize-space(string()), "{}") and ancestor::*[contains(@class, "flex-container boxes indicators")]]/preceding-sibling::p[contains(@class, "indicator") and contains(normalize-space(string()), "{}")]'.format(self.context, name, value)
        self.xpath += '|'
        self.xpath += '{}//p[@class="description" and contains(normalize-space(string()), "{}") and ancestor::*[contains(@class, "total-container")]]/preceding-sibling::p[contains(@class, "total") and contains(normalize-space(string()), "{}")]'.format(self.context, name, value)

    def find_form_filteredselectmultiple_add(self, label_name):
        find_label = label_name
        if label_name[-1] != ':':
            find_label = '{}:'.format(label_name)
        self.xpath += '{}//a[ancestor::*/label[normalize-space(text())="{}"] and contains(@class, "selector-add")]'.format(self.context, find_label)

    def find_form_filteredselectmultiple_remove(self, label_name):
        find_label = label_name
        if label_name[-1] != ':':
            find_label = '{}:'.format(label_name)
        self.xpath += '{}//a[ancestor::*/label[normalize-space(text())="{}"] and contains(@class, "selector-remove")]'.format(self.context, find_label)

    def find_checkbox(self, label_name):
        self.xpath += '{}//input[ancestor::tr[contains(normalize-space(.), "{}")]]'.format(self.context, label_name)

    def find_inline_input(self, input_name):
        self.xpath += '{}//input[@type="text" and @name="{}"]'.format(self.context, input_name)
