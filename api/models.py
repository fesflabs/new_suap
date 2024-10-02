# coding: utf-8
from django.conf import settings

from djtools.db import models
from django.utils.translation import gettext_lazy as _
from oauth2_provider.models import AbstractApplication


class AplicacaoOAuth2(AbstractApplication):

    """

    Trusted Apps:

        Apps com skip_authorization = True são consideradas trusted e apenas os
        administradores do SUAP podem tornar uma app trusted. Trusted apps podem ter scopes concedidos via atributo
        `granted_scopes`.

        Uma trusted app já tem acesso a uma série de serviços globais, tais como: consulta de servidores, setores,
        campi etc. Porém, permissões especiais via `granted_scopes` podem ser exigidas (ex: contracheques).

    Como Obter um AccessToken de uma app com client-credentials grant:

        curl -X POST -d "client_id=<client_id>&client_secret=<client_secret>&grant_type=client_credentials" <suap_url>/o/token/

    Fields:

        * `authorization_grant_type`:
            - foi redefinido para retirar GRANT_PASSWORD dos choices.
        * `granted_scopes`:
            - serve para definir os scopes, além dos DEFAULT_SCOPES, que a app tem acesso (só tem efeito caso a
              app tenha skip_authorization = True).
            - deixamos TextField para scopes para combinar com AbstractAccessToken.scope, o que evita migrations
              quando houver novos scopes mas exige que o programador trate os scopes disponíveis no form de edição.
    """

    GRANT_TYPES = (
        (AbstractApplication.GRANT_AUTHORIZATION_CODE, _("Authorization code")),
        (AbstractApplication.GRANT_IMPLICIT, _("Implicit")),
        (AbstractApplication.GRANT_CLIENT_CREDENTIALS, _("Client credentials")),
    )
    authorization_grant_type = models.CharField(max_length=32, choices=GRANT_TYPES)
    granted_scopes = models.TextField(blank=True)
    user = models.ForeignKeyPlus(
        settings.AUTH_USER_MODEL,
        related_name="%(app_label)s_%(class)s",
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )

    class Meta:
        ordering = ['id']

    def __str__(self):
        return self.name
