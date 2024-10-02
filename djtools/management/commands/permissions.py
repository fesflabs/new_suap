# -*- coding: utf-8 -*-

import json
from djtools.management.commands import BaseCommandPlus
from django.contrib.auth.models import Group


class Command(BaseCommandPlus):
    def add_arguments(self, parser):
        parser.add_argument(
            '--check',
            action='store_true',
            help='Realiza uma verificação nas permissões salvas no arquivo "permissions.json"',
        )

    def handle(self, *args, **options):
        if options['check']:
            d = json.load(open('permissions.json'))
            for name, perms in d.items():
                s1 = set(Group.objects.get(name=name).permissions.values_list('codename', flat=True))
                s2 = set(perms)
                if s1 != s2:
                    print('{}\n{}\n{}\n\n'.format(name, s1, s2))
                    return
        d = {}
        for g in Group.objects.all().order_by('id'):
            d[g.name] = [s for s in g.permissions.values_list('codename', flat=True)]
        json.dump(d, open('permissions.json', 'w'))
