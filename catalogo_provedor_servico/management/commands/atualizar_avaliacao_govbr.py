import datetime
import json

import requests
from django.core.management.base import BaseCommand
from requests.auth import HTTPBasicAuth

from catalogo_provedor_servico.models import RegistroAcompanhamentoGovBR, RegistroAvaliacaoGovBR
from comum.models import Configuracao

# Exemplo de chamada:
# python manage.py atualizar_avaliacao_govbr

URL_AVALIACAO_GOV_BR = Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'url_avaliacao_gov_br')
USER_AVALIACAO_GOV_BR = Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'user_avaliacao_gov_br')
PASSWORD_AVALIACAO_GOV_BR = Configuracao.get_valor_por_chave('catalogo_provedor_servico', 'password_avaliacao_gov_br')


class Command(BaseCommand):
    def handle(self, *args, **options):
        auth = HTTPBasicAuth(USER_AVALIACAO_GOV_BR, PASSWORD_AVALIACAO_GOV_BR)
        url = '{}'.format(URL_AVALIACAO_GOV_BR)
        solicitacoes_pendentes_de_avaliacao = RegistroAcompanhamentoGovBR.objects.filter(tipo=RegistroAcompanhamentoGovBR.TIPO_CONCLUSAO, avaliado=False)
        for registro in solicitacoes_pendentes_de_avaliacao:
            payload = {
                "cpfCidadao": registro.payload['cpfCidadao'].replace('.', '').replace('-', ''),
                "orgao": registro.payload['orgao'],
                "protocolo": registro.payload['protocolo'],
                "servico": registro.payload['servico'],
                "etapa": registro.solicitacao.status,
            }
            req = requests.get(url=url, params=payload, auth=auth)
            if req.ok and 'avaliacao' in req.json():
                if RegistroAvaliacaoGovBR.objects.filter(solicitacao=registro.solicitacao).exists():
                    registroavaliacao = RegistroAvaliacaoGovBR.objects.filter(solicitacao=registro.solicitacao)[0]
                    registroavaliacao.resposta_avaliacao = json.dumps(req.json())
                    registroavaliacao.data_cadastro_avaliacao = datetime.datetime.now()
                    registroavaliacao.avaliado = True
                    registroavaliacao.save()
                registro.avaliado = True
                registro.save()
                print("Avaliação registrada para solicitação {}".format(registro.solicitacao.id))
            else:
                print('Nenhum registro de avaliação para solicitação {}'.format(registro.solicitacao.id))
