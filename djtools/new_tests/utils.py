import logging
import os
from time import sleep

from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

# Get an instance of a logger
logger = logging.getLogger('behave')


class LoadJS:
    """An expectation for checking the current url.
    url is the expected url, which must not be an exact match
    returns True if the url is different, false otherwise."""

    def __init__(self, browser):
        self.browser = browser

    def __call__(self, driver):
        return self.browser.evaluate_script("document.readyState") == "complete" and self.browser.evaluate_script("jQuery.active") == 0


def go_url(context, url):
    browser = context.browser
    my_url = context.config.server_url
    if url[0] != '/':
        my_url += '/' + url[1:]
    else:
        my_url += url

    browser.visit(my_url)


def wait_click(xpath_constructor, timeout=10):
    wait = WebDriverWait(xpath_constructor.browser.driver, timeout)
    wait.until(EC.element_to_be_clickable((By.XPATH, xpath_constructor.get_xpath())))


def force_click(xpath_constructor, timeout=10):
    current = 0
    increment = 0.2

    while current < timeout:
        current += increment
        sleep(increment)
        try:
            xpath_constructor.get().first.click()
            return
        except Exception:
            pass
    raise Exception('Timeout no click no botão {}'.format(xpath_constructor.get_xpath()))


def force_click_checkbox(xpath_constructor, action, timeout=10):
    current = 0
    increment = 0.2
    selected = None
    while current < timeout:
        current += increment
        sleep(increment)
        try:
            selected = xpath_constructor.get().first.selected
            break
        except Exception:
            pass
    if selected is None:
        raise Exception('Timeout no click do checkbox {}'.format(xpath_constructor.get_xpath()))

    if (selected and action.lower() == 'desmarcar') or (not selected and action.lower() == 'marcar'):
        force_click(xpath_constructor)


def force_fill(xpath_constructor, valor, timeout=10):
    current = 0
    increment = 0.2

    while current < timeout:
        current += increment
        sleep(increment)
        try:
            xpath_constructor.get().first.fill(valor)
            return
        except Exception:
            pass
    raise Exception('Timeout no preenchimento do campo {}'.format(xpath_constructor.get_xpath()))


def force_fill_file(xpath_constructor, campo, valor, real, timeout=10):
    wait = WebDriverWait(xpath_constructor.browser.driver, timeout)
    log(xpath_constructor)
    xpath_constructor.find_form_input(campo, 'arquivo', valor)
    if real:
        filename = os.path.join(os.getcwd(), f"djtools/new_tests/files/{valor.lower()}")
    else:
        filename = valor
    element = wait.until(EC.presence_of_element_located((By.XPATH, xpath_constructor.get_xpath())))
    element.send_keys(filename)


def force_view_msg(xpath_constructor, type_msg, msg, timeout=10):
    wait = WebDriverWait(xpath_constructor.browser.driver, timeout)
    xpath_constructor.find_message(type_msg, msg)
    wait.until(EC.presence_of_element_located((By.XPATH, xpath_constructor.get_xpath())))


def wait_element(xpath_constructor, timeout=10):
    wait = WebDriverWait(xpath_constructor.browser.driver, timeout)
    log(xpath_constructor)
    wait.until(EC.presence_of_element_located((By.XPATH, xpath_constructor.get_xpath())))


def click_until_render(elemento, tentativa=0, maximo_tentativas=10):
    try:
        if tentativa < maximo_tentativas:
            elemento.click()
            return
    except Exception:
        tentativa += 1
        click_until_render(elemento, tentativa)

    elemento.click()


def wait_document_ready(browser, timeout=10):
    wait = WebDriverWait(browser.driver, timeout)
    wait.until(LoadJS(browser))


def wait_url_change(browser, old_url, timeout=10):
    wait = WebDriverWait(browser.driver, timeout)
    wait.until(EC.url_changes(old_url))


def log(xpath_constructor):
    logger.debug('\n' + xpath_constructor.get_xpath())


def log_text(text):
    logger.debug('\n' + text)


def abrir_debugger(context):
    if context.debug:
        browser = context.browser
        contexto = context.contexto
        import ipdb
        ipdb.set_trace()
        print(browser, contexto)
    else:
        print('Debug desativado. Remova o parâmetro --noinput para reativá-lo\n')
