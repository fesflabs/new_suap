from ldapdb.router import Router
from ldapdb.backends.ldap.base import DatabaseWrapper
from django.db import connections
from django.apps import apps
from django.db import migrations
from djtools.testutils import running_tests


class SuapLDAPDatabaseWrapper(DatabaseWrapper):

    def get_connection_params(self):
        from ldap_backend.models import LdapConf
        ldap_conf = LdapConf.get_active()
        conn_params = {
            'uri': ldap_conf.uri,
            'tls': False,
            'bind_dn': ldap_conf.who,
            'bind_pw': ldap_conf.cred,
            'retry_max': 1,
            'retry_delay': 60.0,
            'options': {
                k if isinstance(k, int) else k.lower(): v
                for k, v in self.settings_dict.get('CONNECTION_OPTIONS', {}).items()
            },
        }
        return conn_params


class SuapRouter(Router):
    def __init__(self):
        self.__engine = 'ldapdb.backends.ldap'
        self.__ldap_alias = None

    def is_migration_context(self):
        return getattr(migrations, 'MIGRATION_OPERATION_IN_PROGRESS', False)

    def enabled(self):
        return not self.is_migration_context() and not running_tests()

    @property
    def ldap_alias(self):
        if self.__ldap_alias is None and self.enabled():
            self.__ldap_alias = 'ldap'
            self.load_ldap_conf()
        return self.__ldap_alias

    def load_ldap_conf(self):
        LdapConf = apps.get_model(app_label='ldap_backend', model_name='LdapConf')
        ldap_conf = LdapConf.get_active_settings()
        connections[self.__ldap_alias] = self.create_connection(self.__ldap_alias, ldap_conf)

    def create_connection(self, alias, ldap_conf):
        connections.databases[alias] = {
            'NAME': ldap_conf.get('uri', ''),
            'USER': ldap_conf.get('who', ''),
            'PASSWORD': ldap_conf.get('cred', ''),
            'ENGINE': self.__engine
        }
        connections.ensure_defaults(alias)
        connections.prepare_test_settings(alias)
        db = connections.databases[alias]
        return SuapLDAPDatabaseWrapper(db, alias)
