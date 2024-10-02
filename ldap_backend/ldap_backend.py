import datetime
from django.conf import settings
from django.contrib.auth.backends import ModelBackend
from django.contrib import messages
from comum.models import User
from ldap_backend.models import LdapConf
from ldap_backend.utils import ad_to_datetime


def escape_query(query):
    """Escapes certain filter characters from an LDAP query."""
    return query.replace("\\", r"\5C").replace("*", r"\2A").replace("(", r"\28").replace(")", r"\29")


class LdapBackend(ModelBackend):

    supports_object_permissions = False
    supports_anonymous_user = False
    supports_inactive_user = False

    def authenticate(self, request, username=None, password=None, **kwargs):
        from comum.models import Configuracao
        if Configuracao.get_valor_por_chave('ldap_backend', 'utilizar_autenticacao_via_ldap'):
            ldap_conf = LdapConf.get_active()
            authorized = ldap_conf.check_password(username, password)
            if not password or not ldap_conf or not authorized:
                return None
            if settings.DEBUG and authorized:
                return User.objects.filter(username=username).first()
            try:
                dn = ldap_conf.get_user(username, attrs=['pwdLastSet', 'whenCreated'])
                pwd_last_set = dn['pwdLastSet'][0].decode()
                when_created = dn['whenCreated'][0].decode()
                if pwd_last_set == '0':
                    return None
                datetime_pwd_last_set = ad_to_datetime(int(pwd_last_set))
                datetime_when_created = datetime.datetime.strptime(when_created[:14], '%Y%m%d%H%M%S')
                if (datetime_pwd_last_set - datetime_when_created).seconds < 120:
                    messages.error(request, f'Sua conta "{username}" está vencida. Por favor, clique em "Esqueceu ou deseja alterar sua senha?" ou entre em contato com o suporte de TI do seu campus.')
                    return None
            except Exception:
                return None
            try:
                user = User.objects.get(username=username)
                if not hasattr(user, 'pessoafisica'):
                    # raise ValidationError('Seu usuário não tem perfil no sistema, contacte o administrador.')
                    return None
                return user
            except User.DoesNotExist:
                return None
        return None

    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
