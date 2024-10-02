# -*- coding: utf-8 -*-

import datetime

from django.utils import termcolors

from djtools.management.commands import BaseCommandPlus
from djtools.models import Task


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        qs = Task.objects.filter(user__isnull=True, start__lt=datetime.datetime.now() - datetime.timedelta(days=1))
        print((termcolors.make_style(fg='cyan', opts=('bold',))(f'>>> Limpando {qs.count()} tarefas sem usuários.')))
        qs.delete()
