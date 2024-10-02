# -*- coding: utf-8 -*-

from comum.models import Configuracao
from djtools.utils import to_ascii
import urllib.request
import urllib.parse
import urllib.error
import urllib.request
import urllib.error
import urllib.parse


def get_dreamspark_url(mail, nome):
    base_url = Configuracao.get_valor_por_chave('microsoft', 'dreamspark_url')
    account = Configuracao.get_valor_por_chave('microsoft', 'dreamspark_account')
    key = Configuracao.get_valor_por_chave('microsoft', 'dreamspark_key')
    url_params = dict(
        first_name=to_ascii(nome.split()[0]), last_name=to_ascii(nome.split()[-1]), academic_statuses='staff,students,faculty', account=account, key=key, username=mail, email=mail
    )
    return urllib.request.urlopen(base_url + '?' + urllib.parse.urlencode(url_params)).read()
