import json
import logging
from datetime import datetime

import requests
from requests.auth import HTTPBasicAuth
from sentry_sdk import capture_exception

from catalogo_provedor_servico.models import RegistroAcompanhamentoGovBR, RegistroAvaliacaoGovBR, \
    RegistroNotificacaoGovBR
from comum.models import Configuracao
from djtools.testutils import running_tests
from djtools.utils import send_mail
from djtools.utils import prevent_logging_errors
from suap import settings

# Serviços das APIs de Acompanhamento https://api-acompanha-avalia-servicos.dev.nuvem.gov.br/api/

logging.getLogger("urllib3.connection").setLevel(logging.CRITICAL)


def get_orgao_id(codigo_siorg):
    if running_tests():
        return int(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'orgao_id_portal_servicos_govbr') or 36761)
    try:
        req = requests.get(url="{}/{}".format(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'url_orgaos_gov_br') or 'https://servicos.gov.br/api/v1/orgao', codigo_siorg), timeout=int(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'request_timeout_gov_br') or 0))
        if req.ok:
            return req.json().get('id', None)
    except Exception as e:
        print(' ERRO AO OBTER ID DO ORGÃO - Detalhes: {}'.format(e))
        return int(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'orgao_id_portal_servicos_govbr') or 36761)


def registrar_acompanhamento_servico(
    cpf=None,
    data_etapa=None,
    data_situacao=None,
    descricao_etapa=None,
    codigo_siorg=None,
    protocolo=None,
    servico_id=None,
    descricao_situacao=None,
    registro=None,
    solicitacao=None,
):
    orgao_id = get_orgao_id(codigo_siorg)
    if registro:
        registro_acompanhamento = registro
        payload = registro_acompanhamento.payload
    else:
        payload = {
            "cpfCidadao": cpf.replace('.', '').replace('-', ''),  # "08254631654",
            "dataEtapa": datetime.strftime(data_etapa, '%d/%m/%Y'),  # "10/10/2017",
            "dataSituacaoEtapa": datetime.strftime(data_situacao, '%d/%m/%Y'),
            "etapa": descricao_etapa,  # "Em analise",
            "orgao": orgao_id,  # "36802",
            "protocolo": protocolo,  # "0001AC.20171212",
            "servico": settings.get_id_servico_portal_govbr(servico_id),  # "47",
            "situacaoEtapa": descricao_situacao,  # "Alguma descrição da situação."
        }
        registro_acompanhamento, registro_criado = RegistroAcompanhamentoGovBR.objects.update_or_create(
            solicitacao=solicitacao, payload=payload, tipo=RegistroAcompanhamentoGovBR.TIPO_ACOMPANHAMENTO, status=RegistroAcompanhamentoGovBR.PENDENTE
        )

    try:
        payload_externo = payload.copy()
        payload_externo["situacaoEtapa"] = descricao_situacao[:30]
        r = requests.post(
            Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'url_acompanhamentos_gov_br'),
            auth=HTTPBasicAuth(
                Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'user_acompanhamentos_gov_br'),
                Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'password_acompanhamentos_gov_br')
            ),
            json=payload_externo, timeout=int(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'request_timeout_gov_br') or 0))
        if r.ok:
            if registro_acompanhamento:
                registro_acompanhamento.status = RegistroAcompanhamentoGovBR.ENVIADO
                registro_acompanhamento.status_code = r.status_code
                registro_acompanhamento.save()
            return r
        else:
            if registro_acompanhamento:
                registro_acompanhamento.status = RegistroAcompanhamentoGovBR.ERRO
                registro_acompanhamento.tentativas_envio = registro_acompanhamento.tentativas_envio + 1
                registro_acompanhamento.status_code = r.status_code
                registro_acompanhamento.save()
    except Exception:
        if registro_acompanhamento:
            registro_acompanhamento.status = RegistroAcompanhamentoGovBR.ERRO
            registro_acompanhamento.tentativas_envio = registro_acompanhamento.tentativas_envio + 1
            registro_acompanhamento.save()


def registrar_conclusao_servico(cpf=None, codigo_siorg=None, protocolo=None, servico_id=None, registro=None, solicitacao=None):
    orgao_id = get_orgao_id(codigo_siorg)
    if registro:
        registro_acompanhamento = registro
        payload = registro_acompanhamento.payload
        registro_criado = True
    else:
        payload = {
            "cpfCidadao": cpf.replace('.', '').replace('-', ''),
            "orgao": orgao_id,
            "protocolo": protocolo,
            "servico": settings.get_id_servico_portal_govbr(servico_id),
            "situacaoServico": 2,  # 1 = Aberto/Reaberto - 2 = Concluído
        }
        registro_acompanhamento, registro_criado = RegistroAcompanhamentoGovBR.objects.update_or_create(
            solicitacao=solicitacao, payload=payload, tipo=RegistroAcompanhamentoGovBR.TIPO_CONCLUSAO, status=RegistroAcompanhamentoGovBR.PENDENTE
        )

    try:
        r = requests.put(
            Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'url_acompanhamentos_gov_br') + "situacao",
            auth=HTTPBasicAuth(
                Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'user_acompanhamentos_gov_br'),
                Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'password_acompanhamentos_gov_br')
            ),
            json=payload, timeout=int(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'request_timeout_gov_br') or 0)
        )
        if r.ok:
            if registro_criado:
                registro_acompanhamento.status = RegistroAcompanhamentoGovBR.ENVIADO
                registro_acompanhamento.status_code = r.status_code
                registro_acompanhamento.save()
            return r
        else:
            if registro_criado:
                registro_acompanhamento.status = RegistroAcompanhamentoGovBR.ERRO
                registro_acompanhamento.status_code = r.status_code
                registro_acompanhamento.save()
    except Exception:
        if registro_criado:
            registro_acompanhamento.status = RegistroAcompanhamentoGovBR.ERRO
            registro_acompanhamento.save()


def registrar_reabertura_servico(cpf=None, codigo_siorg=None, protocolo=None, servico_id=None, registro=None, solicitacao=None):
    orgao_id = get_orgao_id(codigo_siorg)
    if registro:
        registro_acompanhamento = registro
        payload = registro_acompanhamento.payload
        registro_criado = True
    else:
        payload = {
            "cpfCidadao": cpf.replace('.', '').replace('-', ''),
            "orgao": orgao_id,
            "protocolo": protocolo,
            "servico": settings.get_id_servico_portal_govbr(servico_id),
            "situacaoServico": 1,  # 1 = Aberto/Reaberto - 2 = Concluído
        }
        registro_acompanhamento, registro_criado = RegistroAcompanhamentoGovBR.objects.update_or_create(
            solicitacao=solicitacao, payload=payload, tipo=RegistroAcompanhamentoGovBR.TIPO_REABERTURA, status=RegistroAcompanhamentoGovBR.PENDENTE
        )
    try:
        r = requests.put(
            Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'url_acompanhamentos_gov_br') + "situacao",
            auth=HTTPBasicAuth(
                Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'user_acompanhamentos_gov_br'),
                Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'password_acompanhamentos_gov_br')
            ),
            json=payload, timeout=int(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'request_timeout_gov_br') or 0)
        )
        if r.ok:
            if registro_criado:
                registro_acompanhamento.status = RegistroAcompanhamentoGovBR.ENVIADO
                registro_acompanhamento.status_code = r.status_code
                registro_acompanhamento.save()
            return
        else:
            if registro_criado:
                registro_acompanhamento.status = RegistroAcompanhamentoGovBR.ERRO
                registro_acompanhamento.status_code = r.status_code
                registro_acompanhamento.save()
    except Exception:
        if registro_criado:
            registro_acompanhamento.status = RegistroAcompanhamentoGovBR.ERRO
            registro_acompanhamento.save()


def obter_link_formulario_avaliacao(cpf, etapa, codigo_siorg, protocolo, servico_id, solicitacao, verbose=False):

    if verbose:
        print('Tentando obter link de avaliacao...')
        print('cpf: {}, etapa: {}, codigo_siorg: {}, protocolo: {}, servico_id: {}, solicitacao: {}'.format(cpf, etapa, codigo_siorg, protocolo, servico_id, solicitacao))

    orgao_id = get_orgao_id(codigo_siorg)
    payload = {
        "cpfCidadao": cpf.replace('.', '').replace('-', ''),
        "etapa": etapa,
        "orgao": str(orgao_id),
        "protocolo": str(protocolo),
        "servico": settings.get_id_servico_portal_govbr(servico_id)
    }
    registro_avaliacao, registro_criado = RegistroAvaliacaoGovBR.objects.update_or_create(solicitacao=solicitacao)
    try:
        url = Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'url_avaliacao_gov_br') + "formulario"
        if verbose:
            print('Disparando requisicao...')
            print('Url: {}, Auth: {}, json: {}, timeout: {}'.format(
                url,
                HTTPBasicAuth(
                    Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'user_avaliacao_gov_br'),
                    Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'password_avaliacao_gov_br')
                ),
                payload, int(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'request_timeout_gov_br') or 0))
            )

        req = requests.post(
            url,
            auth=HTTPBasicAuth(
                Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'user_avaliacao_gov_br'),
                Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'password_avaliacao_gov_br')
            ),
            json=payload, timeout=int(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'request_timeout_gov_br') or 0)
        )
        if req.ok:
            resposta = {'status_code': req.status_code, 'url': req.json()['location']}
            if verbose:
                print('Link de avaliacao obtido com sucesso.')
                print('resposta: {}'.format(resposta))

            if registro_avaliacao:
                registro_avaliacao.url_avaliacao = resposta['url']
                registro_avaliacao.data_cadastro_link_formulario = datetime.now()
                registro_avaliacao.save()
            return resposta
        else:
            status = None
            if 'status' in req.json():
                status = req.json()['status']
            resposta = {'status_code': req.status_code, 'response': req, 'status': status}

            if verbose:
                print('A obtencao do link de avaliacao foi negado.')
                print('resposta: {}'.format(resposta))
            return resposta
    except Exception as e:
        if verbose:
            print(' ERRO OBTER LINK AVALIACAO: Detalhes: {}'.format(e))
        if settings.DEBUG:
            return ' Detalhes: {}'.format(e)


def atualizar_registro_avaliacao(registro_acompanhamento):
    cpf = registro_acompanhamento.payload['cpfCidadao']
    registro_acompanhamento.payload['cpfCidadao'] = cpf.replace('.', '').replace('-', '')
    try:
        req = requests.get(
            url=Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'url_avaliacao_gov_br'),
            params=registro_acompanhamento.payload,
            auth=HTTPBasicAuth(
                Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'user_avaliacao_gov_br'),
                Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'password_avaliacao_gov_br')
            ),
            timeout=int(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'request_timeout_gov_br') or 0)
        )
        if req.ok and 'avaliacao' in req.json():
            if RegistroAvaliacaoGovBR.objects.filter(solicitacao=registro_acompanhamento.solicitacao).exists():
                registroavaliacao = RegistroAvaliacaoGovBR.objects.filter(solicitacao=registro_acompanhamento.solicitacao)[0]
                registroavaliacao.resposta_avaliacao = json.dumps(req.json())
                registroavaliacao.data_cadastro_avaliacao = datetime.now()
                registroavaliacao.avaliado = True
                registroavaliacao.save()
            registro_acompanhamento.avaliado = True
            registro_acompanhamento.save()
    except Exception as e:
        if settings.DEBUG:
            return ' Detalhes: {}'.format(e)


# Integração com serviço de SMS do Gov.BR
def enviar_sms(numero_telefone, mensagem):
    """
    :param numero_telefone: numero do telefone para notificar via SMS no padrão  (ddi)(ddd)numero. exemplo: 5561999718735
    :param mensagem: não devem exceder 160 caracteres e não podem conter caracteres especiais e acentos
    :return: status code
    """
    url = Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'url_api_sms')
    mensagem = mensagem[:160]
    payload = {"destination": numero_telefone, "messageText": mensagem}
    headers = {
        'username': Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'username_api_sms'),
        'authenticationtoken': Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'token_api_sms'),
        'content-type': "application/json"
    }
    try:
        response = requests.request("POST", url, json=payload, headers=headers, timeout=int(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'request_timeout_gov_br') or 0))
        if response.ok:
            resposta = {'status_code': response.status_code, 'text': response.text}
            print('SMS enviado com sucesso!')
            print('resposta: {}'.format(resposta))
        else:
            resposta = {'status_code': response.status_code, 'text': response.text}
            print('Houve erro ao enviar o SMS. Detalhes: {}'.format(response.text))
        return resposta
    except Exception as e:
        print('Detalhes: {}'.format(e))
        if settings.DEBUG:
            print(' Detalhes: {}'.format(e))


def ligar_para_telefone(numero_telefone, solicitacao, mensagem):
    """
    :param numero_telefone: numero do telefone para notificar no padrão  (ddi)(ddd)numero. exemplo: 5561999718735
    :param mensagem: Mensagem da chamada que será reproduzida
    :return:
    """
    from twilio.rest import Client

    account_sid = Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'sid_api_twilio')

    auth_token = Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'token_api_twilio')
    try:
        client = Client(account_sid, auth_token)
        text_call = '<Response> <Say voice="alice" language="pt-BR">{}</Say> </Response>'.format(mensagem)

        call = client.calls.create(
            twiml=text_call,
            from_='+{}'.format(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'numero_telefone_api_twilio')),
            to='+{}'.format(numero_telefone)
        )
        response_ligacao = dict(mensagem=mensagem, telefone=numero_telefone, id_chamada_twilio=call.sid)
        ligacao_efetuada = True
    except Exception as e:
        ligacao_efetuada = False
        response_ligacao = dict(mensagem=f'Erro ao enviar mensagem {mensagem}', telefone=numero_telefone, exception=str(e))
    RegistroNotificacaoGovBR.objects.create(response_content=response_ligacao, solicitacao=solicitacao, tipo=RegistroNotificacaoGovBR.LIGACAO, enviada=ligacao_efetuada)


@prevent_logging_errors('notifications_python_client.base')
def notificar_cidadao_via_notifica_govbr(solicitacao, mensagem_email=None, mensagem_sms=None, mensagem_app_govbr=None, assunto=None, dados_email=None, registro_notificacao=None):
    """
    Função utilizada para notificar cidadães através da Plataforma Notifica Gov.BR
    :param solicitacao: Solicitação que pertente a um cidadão com CPF (somente números) que será notificado
    :param mensagem_email: Se esse parametro for preenchido será enviado e-mail (cadastro Login único) para o cidadão
    :param mensagem_sms: Se esse parametro for preenchido será enviado sms (cadastro Login único) para o cidadão
    :param mensagem_govbr: Se é parametro for preenchido o cidadão será notificado no app Gov.BR
    :return:
    """
    cpf = solicitacao.cpf.replace('.', '').replace('-', '')
    if not assunto:
        assunto = "IFRN - Notificação"
    if Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'habilitar_notifica_govbr') or False:
        cliente_notifica_govbr = None
        data_envio = None
        try:
            from notifications_python_client.notifications import NotificationsAPIClient
            cliente_notifica_govbr = NotificationsAPIClient(Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'api_key_notifica_govbr') or "balcaodigital-e33c3dcf-cab8-41da-9a7a-8614ab82d123-64f78150-84e7-4456-a7d5-64de9d01551d")
        except Exception as e:
            capture_exception(e)
        if mensagem_email:
            try:
                response_email = cliente_notifica_govbr.send_email_cpf_notification(
                    cpf=cpf,
                    template_id=Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'id_template_notifica_padrao_suap_email') or "3f92e567-6322-4571-b199-3dfb787cfdf3",
                    personalisation={'assunto': assunto, 'mensagem': mensagem_email, })
                email_enviado = True
                data_envio = datetime.now()
            except Exception as e:
                response_email = dict(mensagem=f'Erro ao enviar mensagem {mensagem_sms}.', cpf=cpf, exception=str(e))
                email_enviado = False

            if registro_notificacao:
                registro_notificacao.enviada = email_enviado
                registro_notificacao.data_envio = data_envio if email_enviado else None
                registro_notificacao.save()
            else:
                RegistroNotificacaoGovBR.objects.create(mensagem=mensagem_email, response_content=response_email,
                                                        solicitacao=solicitacao, tipo=RegistroNotificacaoGovBR.EMAIL,
                                                        data_envio=data_envio, enviada=email_enviado)

        if mensagem_sms:
            try:
                response_sms = cliente_notifica_govbr.send_sms_cpf_notification(
                    cpf=cpf,
                    template_id=Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'id_template_notifica_padrao_suap_sms') or "48da34bf-fd34-41a3-9b2f-592112ee07da",
                    personalisation={'mensagem': mensagem_sms, })
                sms_enviado = True
                data_envio = datetime.now()
            except Exception as e:
                response_sms = dict(mensagem=f'Erro ao enviar mensagem {mensagem_sms}.', cpf=cpf, exception=str(e))
                sms_enviado = False

            if registro_notificacao:
                registro_notificacao.enviada = sms_enviado
                registro_notificacao.data_envio = data_envio if sms_enviado else None
                registro_notificacao.save()
            else:
                RegistroNotificacaoGovBR.objects.create(mensagem=mensagem_sms, response_content=response_sms,
                                                        solicitacao=solicitacao, tipo=RegistroNotificacaoGovBR.SMS,
                                                        data_envio=data_envio, enviada=sms_enviado)

        if mensagem_app_govbr:
            try:
                response_app_govbr = cliente_notifica_govbr.send_app_govbr_cpf_notification(
                    cpf=cpf,
                    template_id=Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'id_template_notifica_padrao_suap_app_govbr') or "bedbad5d-d9e4-48cd-bd34-d442bb55c991",
                    personalisation={'mensagem': mensagem_app_govbr, })
                app_enviado = True
                data_envio = datetime.now()
            except Exception as e:
                response_app_govbr = dict(mensagem=f'Erro ao enviar mensagem {mensagem_app_govbr}.', cpf=cpf, exception=str(e))
                app_enviado = False

            if registro_notificacao:
                registro_notificacao.enviada = app_enviado
                registro_notificacao.data_envio = data_envio if app_enviado else None
                registro_notificacao.save()
            else:
                RegistroNotificacaoGovBR.objects.create(mensagem=mensagem_app_govbr, response_content=response_app_govbr,
                                                        solicitacao=solicitacao, tipo=RegistroNotificacaoGovBR.APP,
                                                        data_envio=data_envio, enviada=app_enviado)
    else:
        if mensagem_email:
            email = ''
            for dado in dados_email:
                if dado['name'] == 'email':
                    email = dado['value']
                    break
            if email:
                try:
                    send_mail(assunto=assunto, mensagem=mensagem_email, de=settings.DEFAULT_FROM_EMAIL, para=[email])
                    response_email = dict(email=email, cpf=cpf, assunto=assunto, mensagem=mensagem_email)
                    email_enviado = True
                    data_envio = datetime.now()
                except Exception as e:
                    email_enviado = False
                    response_email = dict(email='Erro ao tentar enviar email: {email}', cpf=cpf, assunto=assunto, mensagem=mensagem_email, exception=str(e))
                RegistroNotificacaoGovBR.objects.create(response_content=response_email, solicitacao=solicitacao,
                                                        tipo=RegistroNotificacaoGovBR.EMAIL_SUAP, data_envio=data_envio, enviada=email_enviado)
