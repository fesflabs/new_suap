# -*- coding: utf-8 -*-

import ssl
import xmlrpc.client
from xmlrpc.server import SimpleXMLRPCDispatcher

from django.apps.registry import apps
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from suds.client import Client

from comum.models import User
from comum.utils import tl
from djtools.templatetags.filters import in_group
from djtools.utils import get_client_ip
from rh.models import PessoaFisica


def login(username, senha=None):
    """
    Realiza o login
    """
    try:
        user = User.objects.get(username=username)
    except User.DoesNotExist:
        return dict(ok=False, msg='Usuário inválido')
    if not user.is_active:
        return dict(ok=False, msg='Usuário inativo')
    if senha and not user.check_password(senha):
        return dict(ok=False, msg='Senha incorreta')

    return dict(ok=True, msg='Login realizado com sucesso', session_pk=username)


def logout(chave):
    """
    Realiza o logout
    """
    return dict(ok=True)


def cadastrar_template(session_pk, pessoa_id, template, client_encoding='latin-1', db_encoding='utf-8'):
    if not 'ponto' in settings.INSTALLED_APPS:
        msg = 'A aplicação de Ponto não está instalada no SUAP'
        return dict(ok=False, msg=msg)

    from ponto.models import Maquina

    try:
        ip = get_client_ip(tl.get_request())
        Maquina.objects.get(ip=ip, cliente_cadastro_impressao_digital=True)
    except Maquina.DoesNotExist:
        msg = 'Máquina sem permissão para cadastro de impressões digitais'
        return dict(ok=False, msg=msg)

    try:
        user = User.objects.get(username=session_pk)
    except Exception:
        return dict(ok=False, msg='Sua sessão expirou. Faça o login novamente.')

    if not (user.has_perm('rh.pode_cadastrar_digital') or user.has_perm('rh.pode_atualizar_digital')):
        return dict(ok=False, msg='Usuário sem permissões para cadastrar' ' digitais')

    try:
        pessoa_fisica = PessoaFisica.objects.get(id=pessoa_id)
    except PessoaFisica.DoesNotExist:
        return dict(ok=False, msg='Pessoa não encontrada')

    if bool(pessoa_fisica.get_template()):
        if not (user.has_perm('rh.pode_cadastrar_digital') and user.has_perm('rh.pode_atualizar_digital')):
            return dict(ok=False, msg='Usuário sem permissões para sobrescrever' ' digitais')

    # Salvando o ``template``

    if settings.USA_LEITOR_BIOMETRICO_GRIAULE:
        pessoa_fisica.template = template.data.decode(client_encoding).encode(db_encoding)
    else:
        pessoa_fisica.template = template.data
    pessoa_fisica.template_importado_terminal = True
    pessoa_fisica.save()
    return dict(ok=True, msg='Impressão digital cadastrada com sucesso')


def get_dados_pessoa(login, template_encoding='latin-1'):
    # TODO: usar ``values`` para evitar carregamento de colunas desnecessárias
    if not 'ponto' in settings.INSTALLED_APPS:
        msg = 'A aplicação de Ponto não está instalada no SUAP'
        return dict(ok=False, msg=msg)
    from ponto.models import Maquina

    try:
        ip = get_client_ip(tl.get_request())
        Maquina.objects.get(ip=ip, ativo=True)
    except Maquina.DoesNotExist:
        msg = 'Máquina sem permissão para acessar o Web Service'
        return dict(ok=False, msg=msg)

    try:
        pf = PessoaFisica.objects.get(username=login)
    except PessoaFisica.DoesNotExist:
        pf = None

    if pf:
        try:
            matricula = pf.funcionario.servidor.matricula
            setor = pf.funcionario.setor.sigla
        except Exception:
            matricula = ''
            setor = ''

        pode_cadastrar_digital_com_qualidade_media = pf.user and (pf.user.has_perm('rh.pode_cadastrar_digital') and pf.user.has_perm('rh.pode_atualizar_digital'))

        template_str = pf.get_template(encoding=template_encoding) or ''
        tem_impressao_digital = bool(template_str)
        is_superuser = pf.user and pf.user.is_superuser
        operador_chave = pf.user and in_group(pf.user, 'Operador de Chaves, Coordenador de Chaves Sistêmico')

    else:
        usuarios = User.objects.filter(username=login)
        if len(usuarios) > 0 and usuarios[0].is_superuser:
            # O usário tentando logar é um 'super usuário', então uma pessoa física será criada para ele
            pf = PessoaFisica()
            pf.pk = -1
            pf.nome = 'Administrador'
            pf.cpf = ''
            pf.tem_digital_fraca = False
            tem_impressao_digital = False
            pode_cadastrar_digital_com_qualidade_media = True
            template_str = ''
            matricula = ''
            setor = ''
            is_superuser = True
            operador_chave = False
        # Não há pessoa física associada ao usuário e ele não é o 'admin'
        else:
            return dict(ok=False, msg='Pessoa não encontrada')

    dados = dict(
        ok=True,
        msg='Pessoa encontrada',
        pessoa_id=pf.pk,
        nome=pf.nome,
        cpf=pf.cpf or '',
        matricula=matricula,
        login=pf.username or '',
        foto_url=pf.get_foto_url(),
        tem_impressao_digital=tem_impressao_digital,
        setor=setor,
        tem_digital_fraca=pf.tem_digital_fraca,
        pode_cadastrar_digital_com_qualidade_media=pode_cadastrar_digital_com_qualidade_media,
        template=xmlrpc.client.Binary(data=template_str),
        is_superuser=is_superuser,
        operador_chave=operador_chave,
    )
    return dados


def meu_ip():
    """
    Retorna informações sobre a máquina requisitante
    """
    return dict(
        ip=get_client_ip(tl.get_request()),
        is_terminal_ponto=is_terminal_ponto()['is_terminal_ponto'],
        is_terminal_cadastro=is_terminal_cadastro()['is_terminal_cadastro'],
        is_terminal_chaves=is_terminal_chaves()['is_terminal_chaves'],
        is_terminal_refeitorio=is_terminal_refeitorio()['is_terminal_refeitorio'],
    )


def is_terminal_ponto():
    if not 'ponto' in settings.INSTALLED_APPS:
        msg = 'A aplicação de Ponto não está instalada no SUAP'
        return dict(ok=False, msg=msg)
    from ponto.models import Maquina

    try:
        maquina = Maquina.objects.get(ip=get_client_ip(tl.get_request()), ativo=True)
        return dict(ok=True, is_terminal_ponto=maquina.cliente_ponto)
    except Maquina.DoesNotExist:
        return dict(ok=False, is_terminal_ponto=False)


def is_terminal_cadastro():
    if not 'ponto' in settings.INSTALLED_APPS:
        msg = 'A aplicação de Ponto não está instalada no SUAP'
        return dict(ok=False, msg=msg)
    from ponto.models import Maquina

    try:
        maquina = Maquina.objects.get(ip=get_client_ip(tl.get_request()), ativo=True)
        return dict(ok=True, is_terminal_cadastro=maquina.cliente_cadastro_impressao_digital)
    except Maquina.DoesNotExist:
        return dict(ok=False, is_terminal_cadastro=False)


def is_terminal_chaves():
    if not 'ponto' in settings.INSTALLED_APPS:
        msg = 'A aplicação de Ponto não está instalada no SUAP'
        return dict(ok=False, msg=msg)
    from ponto.models import Maquina

    try:
        maquina = Maquina.objects.get(ip=get_client_ip(tl.get_request()), ativo=True)
        return dict(ok=True, is_terminal_chaves=maquina.cliente_chaves)
    except Maquina.DoesNotExist:
        return dict(ok=False, is_terminal_chaves=False)


def is_terminal_refeitorio():
    if not 'ponto' in settings.INSTALLED_APPS:
        msg = 'A aplicação de Ponto não está instalada no SUAP'
        return dict(ok=False, msg=msg)
    from ponto.models import Maquina

    try:
        maquina = Maquina.objects.get(ip=get_client_ip(tl.get_request()), ativo=True)
        return dict(ok=True, is_terminal_refeitorio=maquina.cliente_refeitorio)
    except Maquina.DoesNotExist:
        return dict(ok=False, is_terminal_refeitorio=False)


comum_exposed = [
    [login, 'login'],
    [logout, 'logout'],
    [get_dados_pessoa, 'get_dados_pessoa'],
    [cadastrar_template, 'cadastrar_template'],
    [meu_ip, 'meu_ip'],
    [is_terminal_ponto, 'is_terminal_ponto'],
    [is_terminal_cadastro, 'is_terminal_cadastro'],
    [is_terminal_chaves, 'is_terminal_chaves'],
    [is_terminal_refeitorio, 'is_terminal_refeitorio'],
]

dispatcher = SimpleXMLRPCDispatcher(allow_none=False, encoding=None)


def rpc_handler(request):
    """
    the actual handler:
    if you setup your urls.py properly, all calls to the xml-rpc service
    should be routed through here.
    If post data is defined, it assumes it's XML-RPC and tries to process as such
    Empty post assumes you're viewing from a browser and tells you about the service.
    """
    response = HttpResponse()
    data = None
    if 'body' in request.POST:  # hack para testes unitários
        data = request.POST['body']
    elif request.body:  # fluxo normal (chamada do webservice)
        data = request.body

    if data:
        response.write(dispatcher._marshaled_dispatch(data))

    # tela de apresentação do webservice, listando os métodos disponíveis
    else:
        response.write("<h2>This is an XML-RPC Service</h2>")
        response.write("<p>You need to invoke it using an XML-RPC Client!</p>")
        response.write("<p>The following methods are available:</p>")
        methods = dispatcher.system_listMethods()
        for method in methods:
            sig = dispatcher.system_methodSignature(method)
            help_ = dispatcher.system_methodHelp(method)
            response.write("<li><strong>{}</strong>: [{}] {}".format(method, sig, help_))
        response.write("</ul>")
        response.write('<p><a href="http://www.djangoproject.com/"><img src="/static/comum/img/django.gif" alt="Feito com Django" /></a></p>')

    response['Content-length'] = str(len(response.content))
    return response


rpc_handler = csrf_exempt(rpc_handler)


EXPOSED_FUNCTIONS = [comum_exposed]
if 'ponto' in settings.INSTALLED_APPS:
    from ponto.webservice import exposed as ponto_exposed

    EXPOSED_FUNCTIONS.append(ponto_exposed)

if 'ae' in settings.INSTALLED_APPS:
    from ae.webservice import exposed as ae_exposed

    EXPOSED_FUNCTIONS.append(ae_exposed)

if 'chaves' in settings.INSTALLED_APPS:
    from chaves.webservice import exposed as chaves_exposed

    EXPOSED_FUNCTIONS.append(chaves_exposed)

if 'protocolo' in settings.INSTALLED_APPS:
    from protocolo.webservice import exposed as protocolo_exposed

    EXPOSED_FUNCTIONS.append(protocolo_exposed)

if 'patrimonio' in settings.INSTALLED_APPS:
    from patrimonio.webservice import exposed as patrimonio_exposed

    EXPOSED_FUNCTIONS.append(patrimonio_exposed)


for app_exposed_functions in EXPOSED_FUNCTIONS:
    for item in app_exposed_functions:
        function, exposed_name = item
        dispatcher.register_function(function, exposed_name)

####################
# Webservice SIAPE #
####################
"""
Iniciando as configurações para acesso ao webservice SIAPE
"""


def _get_client_siape():
    ssl._create_default_https_context = ssl._create_unverified_context
    Configuracao = apps.get_model('comum', 'configuracao')
    config = Configuracao.get_valor_por_chave(app='rh', chave='urlProducaoWS')
    cliente = None
    if config:
        cliente = Client(config[0].valor)
        cliente.options.location = config.split('?')[0]
    return cliente


"""
definição auxiliar que monta, separados por vírgula, os parâmetros de um serviço
"""


def __get_params_service(method):
    params = ', '.join('{}'.format(part.name for part in method.soap.input.body.parts))
    return params


"""
monta uma lista dos serviços e seus parametros para ser utilizado em um combobox
"""


def _get_services_siape():
    list_options = []
    for k, v in list(_get_service_and_params().items()):
        list_options.append(['{}'.format(k), '{}({})'.format(k, v)])
    return list_options


"""
monta um dicionário onde a chave é o nome do serviço e o valor todos os seus parâmetros
"""


def _get_service_and_params(client=None):
    c = client
    if not c:
        c = _get_client_siape()
    dict = {}
    if c:
        for method in list(c.wsdl.services[0].ports[0].methods.values()):
            params = __get_params_service(method)
            dict[method.name] = params
    return dict


"""
definição que chama um serviço do webservice
"""


def _call_service_siape(params):
    Configuracao = apps.get_model('comum', 'configuracao')
    cliente = _get_client_siape()

    #
    # consultado parametros cadastrados nas configurações
    qs = Configuracao.objects.filter(app='rh')
    di = dict()
    for i in qs:
        di[i.chave] = i.valor

    #
    # verificando parametros passados
    # espera-se um dicionário com os nomes dos parametros da consulta
    if params:
        for p in params:
            if p not in di and p + 'WS' not in di:
                di[p + 'WS'] = params.get(p)

    # verificando qual a consulta foi solicitada
    metodo = di.get('consultaWS')
    params = _get_service_and_params(cliente).get(metodo)

    params_values = ', '.join('di.get("{}WS")'.format(p.strip().replace(')', '')) for p in params.split(','))
    result = eval('cliente.service.{}({})'.format(metodo, params_values))

    return result
