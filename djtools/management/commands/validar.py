# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from pprint import pprint
from django.apps import apps


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        expected_perms = []
        for model in apps.get_models():
            for perm_codename in [p[0] for p in model._meta.permissions]:
                expected_perms.append('%s.%s' % (model._meta.app_label, perm_codename))
            for p in ('add', 'change', 'delete'):
                expected_perms.append('%s.%s_%s' % (model._meta.app_label, p, model.__name__.lower()))
        database_perms = []
        for app_label, perm_codename in apps.get_model('auth', 'Permission').objects.values_list('content_type__app_label', 'codename'):
            database_perms.append('%s.%s' % (app_label, perm_codename))
        set1 = set(database_perms) - set(expected_perms)
        print((len(set1), 'permissions found at database, but not defined in any model permissions attribute'))
        pprint(sorted(set1))
