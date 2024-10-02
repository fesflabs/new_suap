# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from progressoes.models import ProcessoProgressao


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        print('Calculando servidores a progredir ...')
        novos_processos = ProcessoProgressao.calcular_servidores_a_progredir()
        print('--------')
        print(('{} novo(s) processo(s) identificado(s).'.format(len(novos_processos))))
