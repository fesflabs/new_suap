# -*- coding: utf-8 -*-

import ldap
from django.apps import apps
from sentry_sdk import capture_exception

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        PrestadorServico = apps.get_model('comum', 'PrestadorServico')
        LdapConf = apps.get_model('ldap_backend', 'LdapConf')
        conf = LdapConf.get_active()
        for p in PrestadorServico.objects.all():
            try:
                conf.sync_user(p)
            except ldap.LDAPError as ldap_error:
                print(('Analisar prestador {}'.format(p)))
                capture_exception(ldap_error)
