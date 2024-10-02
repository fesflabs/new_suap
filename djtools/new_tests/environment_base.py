import os
import shutil
from collections import OrderedDict

import graphviz
from behave import register_type
from django.apps import apps
from django.conf import settings
from django.utils.crypto import get_random_string
from django.utils.text import slugify
from selenium.webdriver.chrome.options import Options
from splinter import Browser

from djtools.new_tests.base_test import Documentacao, Funcionalidade, Cenario, Passo, Aplicacao
from djtools.utils import get_postgres_uri


def get_js_scroll_to(element):

    if element:
        result = f'$(document.evaluate(\'{element}\', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue.scrollIntoView({{block: "nearest"}}))'
    else:
        result = 'window.scrollTo(0,0);'
    return result


def get_js_snippet_on(element):
    if element:
        return f'highlight_behave($(document.evaluate(\'{element}\', document, null, XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue));'
    return 'console.log("elemento vazio")'


def get_js_snippet_off():
    return '$(".highlight_behave").remove();'


def eh_para_documentar(context):
    if settings.BEHAVE_AUTO_DOC:
        for tag in context.tags:
            if 'do_document' in tag:
                return True
    return False


def get_dependencias(context):
    if settings.BEHAVE_AUTO_DOC:
        for tag in context.tags:
            if 'after_scenario' in tag:
                return tag.split('.')[1]
    return []


def add_documentation_step(context, image_name):
    applicaction = context.documentacao.get_aplicacao(context.application_text)
    feature = applicaction.get_funcionalidade(context.feature_text)
    scenario = feature.get_cenario(context.scenario_text)
    step_text = context.step_text.replace('::', ' :: ')
    scenario.add_passo(Passo(nome=step_text, imagem=image_name, descricao=context.step_description or ''))


def scroll_to(context, elemento):
    if eh_para_documentar(context):
        browser = context.browser
        browser.execute_script(get_js_scroll_to(elemento))


def gerar_highlight_screenshot(context, elemento):
    if eh_para_documentar(context):
        scroll_to(context, elemento)
        browser = context.browser
        browser.execute_script(get_js_snippet_on(elemento))
        screenshot = browser.screenshot(name=f'{settings.BEHAVE_AUTO_DOC_PATH}/doc.png')
        browser.execute_script(get_js_snippet_off())

        add_documentation_step(context=context, image_name=screenshot)


def gerar_screenshot(context):
    if eh_para_documentar(context):
        browser = context.browser
        screenshot = browser.screenshot(name=f'{settings.BEHAVE_AUTO_DOC_PATH}/doc.png')
        add_documentation_step(context=context, image_name=screenshot)


# ----------------------------------------------------------------------------------------------------------------------
# Funções ligadas ao behave --------------------------------------------------------------------------------------------
# ----------------------------------------------------------------------------------------------------------------------
def before_all(context):
    if settings.BEHAVE_BROWSER == 'chrome':
        chrome_options = Options()
        if settings.BEHAVE_CHROME_HEADLESS:
            chrome_options.headless = True
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
        else:
            chrome_options.headless = False
        chrome_options.add_argument(f"--window-size={settings.BEHAVE_WINDOW_SIZE}")
        chrome_options.add_argument("--enable-features=NetworkService,NetworkServiceInProcess")
        chrome_options.add_argument("--incognito")
        if settings.BEHAVE_WINDOW_POSITION:
            chrome_options.add_argument(f"--window-position={settings.BEHAVE_WINDOW_POSITION}")
        if settings.BEHAVE_CHROME_WEBDRIVER:
            context.browser = Browser('chrome', options=chrome_options, executable_path=settings.BEHAVE_CHROME_WEBDRIVER)
        else:
            context.browser = Browser('chrome', options=chrome_options)
    elif settings.BEHAVE_BROWSER == 'firefox':
        context.browser = Browser('firefox')
    elif settings.BEHAVE_BROWSER == 'phantomjs':
        context.browser = Browser('phantomjs')
        context.browser.driver.maximize_window()
    else:
        context.browser = Browser(settings.BEHAVE_BROWSER)

    # Adiciona o contexto de vizualização da página
    context.contexto = ''
    context.popup = list()

    if settings.BEHAVE_AUTO_DOC:
        context.documentacao = Documentacao()


def after_all(context):
    context.browser.quit()
    context.browser = None
    context.contexto = ''
    context.popup = None

    if settings.BEHAVE_AUTO_DOC:
        documentacao_json = context.documentacao.toJSON()
        try:
            aplicacao = next(iter(context.documentacao.aplicacoes.keys()))
            json_file = f'{settings.BEHAVE_AUTO_DOC_PATH}/documentacao_test_{aplicacao}.json'
            with open(json_file, mode='w') as f:
                f.write(documentacao_json)
        except Exception as exception:
            print(exception)
            pass
    if getattr(settings, 'BEHAVE_AUTO_MOCK', False):
        os.system('pg_dump {} > {}/suap_mock.sql'.format(get_postgres_uri(), settings.BEHAVE_AUTO_MOCK_PATH or '.'))


def before_feature(context, feature):
    app_label = feature.filename.split('/')[0]
    if settings.BEHAVE_AUTO_DOC:
        workflow = graphviz.Digraph(format='png')
        workflow.attr(rankdir='LR')
        context.workflow = workflow
        feature.has_flow = False
        if not context.documentacao.has_aplicacao(app_label):
            app_config = apps.get_app_config(app_label)
            context.documentacao.add_aplicacao(Aplicacao(sigla=app_label, nome=app_config.verbose_name, area=app_config.area))
        aplicacao = context.documentacao.get_aplicacao(app_label)
        bpmns = OrderedDict()
        if os.path.isfile(f'{app_label}/workflows/{slugify(feature.name)}.bpmn'):
            bpmns[f'{app_label}::{feature.name}'] = f'{slugify(feature.name)}.bpmn'
        aplicacao.add_funcionalidade(Funcionalidade(feature.name, descricao=feature.description, app_name=feature.filename.split('/')[0], workflows=bpmns))
    context.application_text = app_label
    context.feature_text = feature.name


def after_feature(context, feature):
    context.execute_steps('Dado acesso a página "/accounts/logout/"')
    context.execute_steps('Quando retorna a data do sistema')
    if settings.BEHAVE_AUTO_DOC and feature.has_flow:
        app_label = feature.filename.split('/')[0]
        feature_name = slugify(feature.name)
        workflow = context.workflow
        workflow.render(f'{settings.BEHAVE_AUTO_DOC_PATH}/workflow/{app_label}/{feature_name}')


def before_scenario(context, scenario):
    if eh_para_documentar(context):
        app_label = scenario.feature.filename.split('/')[0]
        workflow = None
        if os.path.isfile(f'{app_label}/workflows/{slugify(scenario.name)}.bpmn'):
            nome = f'{app_label}::{scenario.feature.name}::{scenario.name}'
            workflow = (nome, f'{slugify(scenario.name)}.bpmn')
        context.workflow.node(str(scenario.feature.scenarios.index(scenario)), scenario.name, shape='box')
        for dependencia in get_dependencias(context):
            scenario.feature.has_flow = True
            context.workflow.edge(dependencia, str(scenario.feature.scenarios.index(scenario)))
        feature = context.documentacao.get_aplicacao(context.application_text).get_funcionalidade(context.feature_text)
        feature.add_cenario(Cenario(nome=scenario.name, descricao=scenario.description, funcionalidade=feature.nome, workflow=workflow))
    context.scenario_text = scenario.name


def after_scenario(context, scenario):
    context.contexto = ''
    context.popup = list()
    context.browser.driver.switch_to.parent_frame()

    if scenario.status == "failed":
        project_path = os.environ.get('CI_PROJECT_DIR', '/tmp')
        project_path = os.path.join(project_path, 'artifacts')
        os.makedirs(project_path, exist_ok=True)
        tmp = get_random_string()
        origin_print = context.browser.screenshot()
        destiny_print = os.path.join(project_path, f'screen{tmp}.png')
        shutil.copy(origin_print, destiny_print)
        origin_log_file = os.path.join(settings.BASE_DIR, 'deploy/logs/debug.log')
        destiny_log_file = os.path.join(project_path, f'debug{tmp}.log')
        shutil.copy(origin_log_file, destiny_log_file)
        os.chmod(destiny_print, 0o644)
        os.chmod(destiny_log_file, 0o644)
        print(f'\n\nFalha ao executar o cenário: {scenario.name} >>> {destiny_print} >>> {destiny_log_file}\n')


def before_step(context, step):
    context.step_text = step.name
    context.step_description = step.text


def parse_optional(text):
    return text.strip()


parse_optional.pattern = r'\s?\w*\s?'
register_type(optional=parse_optional)
