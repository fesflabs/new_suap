# coding: utf-8

import django
from django.conf import settings
from django.utils.deprecation import MiddlewareMixin

from catalogo_provedor_servico.utils import get_cpf_formatado
from comum.models import Vinculo
from djtools.utils import httprr

proctitle_prefix = getattr(settings, 'PROCTITLE_PREFIX', '[django]')


class SelecionaVinculoMiddleware(MiddlewareMixin):
    def process_request(self, request):
        views_ignore = ['/comum/selecionar_vinculo/', '/comum/login/govbr']
        eh_gov_br_backend = "GovbrOAuth2" in request.session.get(django.contrib.auth.BACKEND_SESSION_KEY, "")

        request.session['autenticou_com_govbr'] = False
        if eh_gov_br_backend and request.user.social_auth.exists():
            request.session['autenticou_com_govbr'] = True
            request.session['confiabilidade_govbr'] = request.user.social_auth.first().extra_data.get("confiabilidade_govbr", "1")
            vinculos_ativos = Vinculo.objects.filter(pessoa__pessoafisica__cpf=get_cpf_formatado(request.user.social_auth.first().uid), user__is_active=True)
            if request.user.is_authenticated and request.path not in views_ignore and eh_gov_br_backend and vinculos_ativos.exists():
                return httprr('/comum/selecionar_vinculo/')
