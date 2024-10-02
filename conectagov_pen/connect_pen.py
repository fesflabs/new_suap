import requests
from comum.models import Configuracao


class API_PEN_Exception(Exception):
    pass


def create_password_context(password):
    # Subclass OpenSSL.SSL.Context to use a password callback that gives your password
    class PasswordContext(requests.packages.urllib3.contrib.pyopenssl.OpenSSL.SSL.Context):
        def __init__(self, method):
            super(PasswordContext, self).__init__(method)

            def passwd_cb(maxlen, prompt_twice, userdata):
                return password.encode() if len(password) < maxlen else b''

            self.set_passwd_cb(passwd_cb)

    return PasswordContext


def get_config_api():
    url_ws = Configuracao.get_valor_por_chave(app='conectagov_pen', chave='urlProducaoWS_pen')
    password = Configuracao.get_valor_por_chave(app='conectagov_pen', chave='senhaWS_pen')
    cert = Configuracao.get_valor_por_chave(app='conectagov_pen', chave='pathCertificadoPublico_pen')
    cert_priv = Configuracao.get_valor_por_chave(app='conectagov_pen', chave='pathCertificadoPrivado_pen')
    certs = (cert, cert_priv)
    if url_ws and certs:
        if password:
            requests.packages.urllib3.contrib.pyopenssl.OpenSSL.SSL.Context = create_password_context(password)
        try:
            resposta = requests.get(url=url_ws.replace("/interoperabilidade/rest/v2", ""), verify=True, cert=certs)
            if resposta.status_code == 200:
                return {'password': str(password), 'certs': certs}
        except Exception as e:
            print(str(e))
    return {}
    # else:
    #     raise API_PEN_Exception('ERROAPI PEN: Parametros de configuracao nao localizados (comum/configuracao)')


def request_test_api(url):
    configuracao = get_config_api()
    if configuracao:
        requests.packages.urllib3.contrib.pyopenssl.OpenSSL.SSL.Context = create_password_context(configuracao.get('password'))
        resposta = requests.get(url=url, verify=True, cert=configuracao.get('certs'))
        if resposta.status_code:
            return {'status_code': resposta.status_code}
    return {}


def request_get(url, params={}):
    configuracao = get_config_api()
    if configuracao:
        requests.packages.urllib3.contrib.pyopenssl.OpenSSL.SSL.Context = create_password_context(configuracao.get('password'))
        resposta = requests.get(url=url, verify=True, cert=configuracao.get('certs'), params=params)
        if resposta.content:
            try:
                return {'status_code': resposta.status_code, 'content': resposta.content, 'data': resposta.json()}
            except Exception:
                return {}
        elif resposta.status_code:
            return {'status_code': resposta.status_code}
    return {}


def request_post(url, json_data):
    configuracao = get_config_api()
    if configuracao:
        requests.packages.urllib3.contrib.pyopenssl.OpenSSL.SSL.Context = create_password_context(configuracao.get('password'))
        req = requests.post(url=url, verify=True, cert=configuracao.get('certs'), json=json_data)
        if req.content:
            return {'status_code': req.status_code, 'content': req.content}
        elif req.status_code:
            return {'status_code': req.status_code}
    return {}


def request_put(url, json_data):
    configuracao = get_config_api()
    if configuracao:
        requests.packages.urllib3.contrib.pyopenssl.OpenSSL.SSL.Context = create_password_context(configuracao.get('password'))
        resposta = requests.put(url=url, verify=True, cert=configuracao.get('certs'), files=json_data)
        if resposta.content:
            return {'status_code': resposta.status_code, 'content': resposta.content}
        elif resposta.status_code:
            return {'status_code': resposta.status_code}
    return {}


def request_delete(url, params={}):
    configuracao = get_config_api()
    if configuracao:
        requests.packages.urllib3.contrib.pyopenssl.OpenSSL.SSL.Context = create_password_context(configuracao.get('password'))
        resposta = requests.delete(url=url, verify=True, cert=configuracao.get('certs'), params=params)
        if resposta.content:
            return {'status_code': resposta.status_code, 'content': resposta.content, 'data': resposta.json()}
        elif resposta.status_code:
            return {'status_code': resposta.status_code}
    return {}
