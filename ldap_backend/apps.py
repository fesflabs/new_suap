# coding=utf-8

from djtools.apps import SuapAppConfig as AppConfig
from django.db.models.signals import pre_migrate
from django.db import migrations


def ldap_backend_disable_router(sender, **kwargs):
    migrations.MIGRATION_OPERATION_IN_PROGRESS = True


class LdapBackendConfig(AppConfig):
    default = True
    name = 'ldap_backend'
    verbose_name = 'LDAP Backend'
    description = 'Comunica-se com o Active Directory para autenticação com outros serviços oferecidos pela TI: Microsoft, Google, Acesso pasta da rede, acesso a computadores etc.'
    icon = 'server'
    area = 'Tecnologia da Informação'

    def ready(self):
        pre_migrate.connect(ldap_backend_disable_router, sender=self)
