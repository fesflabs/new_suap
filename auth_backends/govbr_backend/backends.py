# coding: utf-8
import requests
from django.conf import settings
from social_core.backends.oauth import BaseOAuth2

from catalogo_provedor_servico.utils import get_cpf_formatado


class GovbrOAuth2(BaseOAuth2):
    name = 'govbr'
    AUTHORIZATION_URL = settings.AUTHORIZATION_URL
    ACCESS_TOKEN_METHOD = 'POST'
    ACCESS_TOKEN_URL = settings.ACCESS_TOKEN_URL
    ID_KEY = 'sub'  # id_token
    RESPONSE_TYPE = 'code'
    REDIRECT_STATE = False
    STATE_PARAMETER = False
    USER_DATA_URL = settings.USER_DATA_URL

    def user_data(self, access_token, *args, **kwargs):
        return self.request(url=self.USER_DATA_URL, data={'scope': kwargs['response']['scope']}, method='POST', headers={'Authorization': 'Bearer {0}'.format(access_token)}).json()

    def get_user_details(self, response):
        """
        Retorna um dicionário mapeando os fields do settings.AUTH_USER_MODEL.
        você pode fazer aqui outras coisas, como salvar os dados do usuário
        (`response`) em algum outro model.
        """
        splitted_name = response['name'].split()
        first_name, last_name = splitted_name[0], ''
        confiabilidade_govbr = self.get_nivel_confiabilidade(response['sub'], response['access_token'])
        vinculos_ativos_ids = self.get_vinculos_ativos(response['sub'])
        if len(splitted_name) > 1:
            last_name = splitted_name[-1]
        return {'username': response['sub'], 'first_name': first_name.strip(), 'last_name': last_name.strip(),
                'name': response['name'], 'email': response['email'], 'email_verified': response['email_verified'],
                'phone_number': response['phone_number'], 'confiabilidade_govbr': confiabilidade_govbr, 'vinculos_ativos_ids': vinculos_ativos_ids}

    def get_nivel_confiabilidade(self, cpf, access_token):
        '''
        Obtem confiabilidades do usuário
        Selos:
        1 - Nível Bronze
        2 - Nível Prata
        3 - Nível Ouro
        '''
        url = f"https://api.acesso.gov.br/confiabilidades/v3/contas/{cpf}/niveis?response-type=ids"

        headers = {
            'Authorization': f"Bearer {access_token}"
        }
        # # TODO: Ajustar para verificar se é confiabilidade: 1 - bronze - 2 - prata ou 3 - ouro e retornar a maior
        req = requests.request("GET", url, headers=headers)
        if req.ok and req.json():
            id_confiabilidade = req.json()[0].get("id")
        else:
            id_confiabilidade = "0"
        return id_confiabilidade

    def get_vinculos_ativos(self, cpf):
        '''
        Obtem vínculos ativos no SUAP do cidadão autenticado por CPF
        '''
        from django.apps import apps
        Vinculo = apps.get_model('comum', 'Vinculo')
        cpf_formatado = get_cpf_formatado(cpf)
        if Vinculo:
            vinculos_ativos_ids = Vinculo.objects.filter(pessoa__pessoafisica__cpf=cpf_formatado, user__is_active=True)
            return list(vinculos_ativos_ids.values_list('pk', flat=True))
        return list()
