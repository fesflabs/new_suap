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
        Aluno = apps.get_model('edu', 'Aluno')
        LdapConf = apps.get_model('ldap_backend', 'LdapConf')
        conf = LdapConf.get_active()
        filter_kw = dict(situacao__ativo=True)
        if options['alterado_em']:
            filter_kw['alterado_em__gte'] = datetime.now() - timedelta(hours=int(options['alterado_em']))

        for a in Aluno.objects.filter(**filter_kw).select_related('pessoa_fisica', 'curso_campus__diretoria__setor__uo__setor', 'situacao'):
            try:
                if a.get_user():
                    conf.sync_user(a)
            except ldap.LDAPError as ldap_erro:
                print(('Analisar aluno {}'.format(a)))
                capture_exception(ldap_erro)
            except Exception as erro:
                print(('Analisar aluno {}'.format(a)))
                capture_exception(erro)
