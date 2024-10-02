# -*- coding: utf-8 -*-

from datetime import datetime, timedelta

import ldap
from django.apps import apps
from sentry_sdk import capture_exception

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def add_arguments(self, parser):
        parser.add_argument('args', nargs='*', type=str)
        parser.add_argument(
            '--alterado_em', action='store', dest='alterado_em', default=0, type=int, help='Informe a quantidade de horas da última alteração para restringir a sincronia.'
        )

    def handle(self, *args, **options):
        Servidor = apps.get_model('rh', 'Servidor')
        LdapConf = apps.get_model('ldap_backend', 'LdapConf')
        conf = LdapConf.get_active()

        filter_kw = dict()
        if options['alterado_em']:
            filter_kw['alterado_em__gte'] = datetime.now() - timedelta(hours=int(options['alterado_em']))

        for s in Servidor.objects.filter(**filter_kw).select_related('setor__uo__setor', 'cargo_emprego__grupo_cargo_emprego'):
            try:
                conf.sync_user(s)
            except ldap.LDAPError as ldap_error:
                print(('Analisar servidor {}'.format(s)))
                capture_exception(ldap_error)
