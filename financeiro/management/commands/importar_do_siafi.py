# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        from financeiro import importador

        importador.processar()
