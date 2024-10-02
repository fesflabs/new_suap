from datetime import datetime

import tqdm
from django.utils.html import strip_tags

from djtools.management.commands import BaseCommandPlus

from catalogo_provedor_servico.models import RegistroNotificacaoGovBR
from catalogo_provedor_servico.services import notificar_cidadao_via_notifica_govbr

# Exemplo de chamada:
# python manage.py enviar_notificacoes_notifica_govbr


class Command(BaseCommandPlus):
    '''
    Este command será executado duas vezes ao dia (12:00 e 19:00) para reenviar as notificações com registro de erro daquele dia
    '''

    def handle(self, *args, **options):
        verbose = str(options.get('verbosity', '0')) != '0'

        # Envia registros de notificação que houve erro no envio ao Notifica Gov.BR
        registros_notificacoes_govbr_erro_envio_hoje = RegistroNotificacaoGovBR.objects.filter(enviada=False, data_criacao__date=datetime.today())
        registros_notificacoes_govbr_erro_envio_sms = registros_notificacoes_govbr_erro_envio_hoje.filter(enviada=False, tipo=RegistroNotificacaoGovBR.SMS)
        registros_notificacoes_govbr_erro_envio_email = registros_notificacoes_govbr_erro_envio_hoje.filter(enviada=False, tipo=RegistroNotificacaoGovBR.EMAIL)
        registros_notificacoes_govbr_erro_envio_appgovbr = registros_notificacoes_govbr_erro_envio_hoje.filter(enviada=False, tipo=RegistroNotificacaoGovBR.APP)

        print('Tentando obter os registros de  notificações SMS.')
        if verbose:
            registros_notificacoes_govbr_erro_envio_sms = tqdm.tqdm(registros_notificacoes_govbr_erro_envio_sms)

        for registro_notificacao in registros_notificacoes_govbr_erro_envio_sms:
            notificar_cidadao_via_notifica_govbr(registro_notificacao.solicitacao,
                                                 mensagem_sms=registro_notificacao.mensagem,
                                                 registro_notificacao=registro_notificacao)

        print('Tentando obter os registros de  notificações EMAIL.')
        if verbose:
            registros_notificacoes_govbr_erro_envio_email = tqdm.tqdm(registros_notificacoes_govbr_erro_envio_email)

        for registro_notificacao in registros_notificacoes_govbr_erro_envio_email:
            notificar_cidadao_via_notifica_govbr(registro_notificacao.solicitacao,
                                                 mensagem_email=strip_tags(registro_notificacao.mensagem),
                                                 registro_notificacao=registro_notificacao)

        print('Tentando obter os registros de  notificações APP Gov.BR.')
        if verbose:
            registros_notificacoes_govbr_erro_envio_appgovbr = tqdm.tqdm(registros_notificacoes_govbr_erro_envio_appgovbr)

        for registro_notificacao in registros_notificacoes_govbr_erro_envio_appgovbr:
            notificar_cidadao_via_notifica_govbr(registro_notificacao.solicitacao,
                                                 mensagem_email=registro_notificacao.mensagem,
                                                 registro_notificacao=registro_notificacao)
