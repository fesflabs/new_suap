# -*- coding: utf-8 -*-

import ldap
from django.apps import apps

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        Professor = apps.get_model('edu', 'Professor')
        LdapConf = apps.get_model('ldap_backend', 'LdapConf')
        conf = LdapConf.get_active()
        for professor in Professor.nao_servidores.all():
            try:
                conf.sync_user(professor.vinculo.user.username)
            except ldap.LDAPError:
                print(('Analisar professor {}'.format(professor)))
