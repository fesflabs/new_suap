# -*- coding: utf-8 -*-

"""
Comando que reavalia todos os invenarios.
"""

from djtools.management.commands import BaseCommandPlus
from django.utils import termcolors
from patrimonio.models import Inventario, InventarioReavaliacao
import sys


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        total = Inventario.depreciaveis.count()
        count = 1
        inventarios = Inventario.depreciaveis.all()
        for inventario in inventarios:
            porcentagem = int(float(count) / total * 100)
            sys.stdout.write(termcolors.make_style(fg='cyan', opts=('bold',))('\r {0}% - Reavaliando {1} de {2}'.format(porcentagem, count, total)))
            sys.stdout.flush()
            count += 1

            InventarioReavaliacao.reavaliar(inventario)

        print('\n FIM \n')
