import logging
import requests
from comum.models import Configuracao
from django.core.cache import cache
from datetime import datetime, timedelta
from django.conf import settings

from djtools.models import ConsultaCidadaoCache

logger = logging.getLogger(__name__)


def auth_token_conecta_govbr(name_token, client_id, client_secret):
    grant_type = 'client_credentials'

    try:
        response = requests.post("https://h-apigateway.conectagov.estaleiro.serpro.gov.br/oauth2/jwt-token" if settings.DEBUG else Configuracao.get_valor_por_chave('djtools', 'url_token_conecta_gov_br'),
                                 auth=(client_id, client_secret),
                                 data={'grant_type': grant_type, 'client_id': client_id,
                                       'client_secret': client_secret})
        cache.set(name_token, response.json()['access_token'], 6500)
    except Exception as e:
        pass
        print(' ERRO AO OBTER TOKEN DO CONECTA GOVBR: Detalhes: {}'.format(e))


def get_token(name_token, client_id, client_secret):
    if cache.get(name_token):
        return cache.get(name_token)
    else:
        auth_token_conecta_govbr(name_token, client_id, client_secret)
        return cache.get(name_token)


def consulta_cep(cpf_operador, cep):
    try:
        headers = {
            "x-cpf-usuario": cpf_operador.replace('.', '').replace('-', ''),
            'authorization': "Bearer {}".format(get_token("token_api_cep", Configuracao.get_valor_por_chave('djtools', 'client_id_api_cep_gov_br'), Configuracao.get_valor_por_chave('djtools', 'client_secret_api_cep_gov_br')))
        }
        url = "https://h-apigateway.conectagov.estaleiro.serpro.gov.br/" if settings.DEBUG else Configuracao.get_valor_por_chave('djtools', 'url_api_conecta_gov_br')
        url += "api-cep/v1/consulta/cep/{}".format(cep)
        req = requests.get(url, headers=headers, timeout=10)
        if req.ok:
            logger.info('Response API CEP: url_api:{}, CPF usuário/operador: {}, status_code: {}, content {}, '
                        'datetime: {}'.format(url, cpf_operador, req.status_code, req.content, datetime.now()))
            return req.json()
    except Exception as e:
        pass
        print(' ERRO AO CONSULTAR CEP: Detalhes: {}'.format(e))


def consulta_cidadao(cpfs, cpf_operador=None):
    '''
    Exemplo de uso:
        sucesso, resposta_lista = consulta_cidadao(["11111111111"], "02029393939")
        if sucesso:
            lista_registros_localizados = list()
            for registro_dict in resposta_lista:
                if not "mensagem" in registro_dict:
                    lista_registros_localizados.append(registro_dict)
    :param cpfs:
    :param cpf_operador:
    :return bool, list:
    True, '[{"CPF": "11111111111", "Nome": "GLEDE BERNACCI GOLLUSCIO", "SituacaoCadastral": 5, "ResidenteExterior": "N", "NomeMae": "INEZ DAINESE BERNACCI", "DataNascimento": "19380123", "Sexo": 2, "TipoLogradouro": "RUA", "Logradouro": "DOIS DE JULHO", "NumeroLogradouro": "196", "Bairro": "IPIRANGA", "Cep": 4215000, "UF": "SP", "CodigoMunicipio": 7107, "Municipio": "SAO PAULO", "UnidadeAdministrativa": 819600, "NomeUnidadeAdministrativa": "SAO PAULO", "Estrangeiro": "N", "DataAtualizacao": "20180914"}]'
    '''
    try:
        cpf_operador = cpf_operador if cpf_operador is not None else Configuracao.get_valor_por_chave('djtools', 'cpf_operador_api_cep_gov_br')
        json_cpf = {"listaCpf": cpfs}
        obj = ConsultaCidadaoCache.get(filtro_api=json_cpf)
        if obj:
            return True, obj.resultado
        headers = {
            "x-cpf-usuario": cpf_operador.replace('.', '').replace('-', ''),
            'authorization': "Bearer {}".format(get_token('token_api_cpf', Configuracao.get_valor_por_chave('djtools', 'client_id_api_cpf_gov_br'), Configuracao.get_valor_por_chave('djtools', 'client_secret_api_cpf_gov_br')))
        }
        url = "https://h-apigateway.conectagov.estaleiro.serpro.gov.br/" if settings.DEBUG else Configuracao.get_valor_por_chave('djtools', 'url_api_conecta_gov_br')
        url += "api-cpf-light/v2/consulta/cpf"
        req = requests.post(url, headers=headers, json=json_cpf, timeout=10)
        if req.ok:
            logger.info('Response API CPF: url:{}, CPF usuário/operador: {}, status_code: {}, content {}, '
                        'datetime: {}'.format(url, cpf_operador, req.status_code, req.content, datetime.now()))
            resultado = req.json()
            ConsultaCidadaoCache.objects.create(filtro_api=json_cpf, cpf_operador=cpf_operador, resultado=resultado, data_expiracao=datetime.now() + timedelta(days=60))
            return True, resultado
        else:
            return False, [req.content]
    except Exception as e:
        return False, {}
        print(' ERRO AO CONSULTAR CPF: Detalhes: {}'.format(e))
        return False, []


def consulta_empresa(cnpj, cpf_operador=None):
    '''

    :param cnpj:
    :return:
    '''
    try:
        cpf_operador = cpf_operador if cpf_operador is not None else Configuracao.get_valor_por_chave('djtools', 'cpf_operador_api_cep_gov_br')
        headers = {
            "x-cpf-usuario": cpf_operador.replace('.', '').replace('-', ''),
            'authorization': "Bearer {}".format(get_token('token_api_cnpj', Configuracao.get_valor_por_chave('djtools', 'client_id_api_cnpj_gov_br'), Configuracao.get_valor_por_chave('djtools', 'client_secret_api_cnpj_gov_br')))
        }
        url = "https://h-apigateway.conectagov.estaleiro.serpro.gov.br/" if settings.DEBUG else Configuracao.get_valor_por_chave('djtools', 'url_api_conecta_gov_br')
        url += "api-cnpj-empresa/v2/empresa/{}".format(cnpj)
        req = requests.get(url, headers=headers, timeout=10)
        if req.ok:
            logger.info('Response API CNPJ: url_api:{}, CPF usuário/operador: {}, status_code: {}, content {}, '
                        'datetime: {}'.format(url, cpf_operador, req.status_code, req.content, datetime.now()))
            return True, req.json()
        else:
            return False, req.content
    except Exception as e:
        pass
        print(' ERRO AO CONSULTAR CNPJ: Detalhes: {}'.format(e))


def consulta_quitacao_eleitoral_cidadao(dados_eleitor, ip_usuario_logado, emitir_certidao=False, cpf_operador=None, return_full=False):
    '''
    Exemplo de uso:
    O parâmetro dados_eleitor é um dict conforme o modelo abaixo:
    O atributo dataNascimento do dict deve está no formato: YYYY-MM-DD
        params = {
        "inscricao": "123456789098",
        "cpf": "07117171198",
        "nome": "JOÃO DE DEUS DA SILVA",
        "nomeMae": "MARIA SILVA",
        "nomePai": "JOÃO DA SILVA",
        "dataNascimento": "1982-01-02"
        }
        sucesso, response = consulta_quitacao_eleitoral_cidadao(params, "192.168.0.5", "07371666496")
        if sucesso:
            dados_eleitor = response.json()
    :param dados_eleitor: Dict com informações do eleitor a ser consultado
    :param ip_usuario_logado: Endereço IP do usuario logado - Para obter utiliza-se o get_client_ip do djtools.utils
    :param cpf_operador: CPF do usuário logado no sistema
    :param emitir_certidao: Se True irá emitir uma nova certidão de quitação eleitoral
    :return: Tupla com boolean indicando se a requisição obteve sucesso e conteudo da resposta
    '''
    try:
        cpf_operador = cpf_operador if cpf_operador is not None else Configuracao.get_valor_por_chave('djtools', 'cpf_operador_api_cep_gov_br')
        headers = {
            "sistema": Configuracao.get_valor_por_chave('djtools', 'nome_sistema_quitacaoeleitoral_gov_br'),
            "ip": ip_usuario_logado,
            "cpf": cpf_operador.replace('.', '').replace('-', ''),
            "x-cpf-usuario": cpf_operador.replace('.', '').replace('-', ''),
            'authorization': "Bearer {}".format(get_token('token_api_quitacao_eleitoral', Configuracao.get_valor_por_chave('djtools', 'client_id_api_quitacaoeleitoral_gov_br'), Configuracao.get_valor_por_chave('djtools', 'client_secret_quitacaoeleitoral_gov_br'))),
            "Content-Type": "application/json;charset=UTF-8"
        }
        url = "https://h-apigateway.conectagov.estaleiro.serpro.gov.br/" if settings.DEBUG else Configuracao.get_valor_por_chave('djtools', 'url_api_conecta_gov_br')
        url += "api-quitacao-eleitoral/v3/eleitores/quitacao-eleitoral"
        if emitir_certidao:
            url = "https://h-apigateway.conectagov.estaleiro.serpro.gov.br/" if settings.DEBUG else Configuracao.get_valor_por_chave('djtools', 'url_api_conecta_gov_br')
            url += "api-quitacao-eleitoral/v2/eleitores/certidao-quitacao-eleitoral"

        dados_eleitor['inscricao'] = dados_eleitor['inscricao'].replace('.', '').replace('-', '')
        dados_eleitor['cpf'] = dados_eleitor['cpf'].replace('.', '').replace('-', '')
        req = requests.get(url, headers=headers, params=dados_eleitor, timeout=50)
        # Retorna a resposta da requisição sem nenhuma validação/tratamento
        if return_full:
            return False, req
        if req.ok:
            logger.info('Response API QUITAÇÃO ELEITORAL: url:{}, CPF usuário/operador: {}, status_code: {}, content {}, '
                        'datetime: {}'.format(url, cpf_operador, req.status_code, req.content, datetime.now()))
            return True, req.json()
        else:
            return False, req.content

    except Exception as e:
        pass
        print(' ERRO AO CONSULTAR API DE QUITAÇÃO ELEITORAL: Detalhes: {}'.format(e))
