# -*- coding: utf-8 -*-
"""
Comando que extrai os curriculos lattes
"""

from djtools.management.commands import BaseCommandPlus
from clipping import rss


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        verbosity = options.get('verbosity', 3)
        count = rss.importar_tudo(verbosity)
        if verbosity:
            print(('%d importadas' % count))
