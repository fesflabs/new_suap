# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from django.apps import apps


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        LdapConf = apps.get_model('ldap_backend', 'LdapConf')
        conf = LdapConf.get_active()
        conf.sync_all_ous(test_mode=False)
