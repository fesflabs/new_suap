# -*- coding: utf-8 -*-
from edu.educacenso import Exportador
from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        e = Exportador(2017)
        print((str(e)))
        print('===================')
        for erro in e.erros:
            print(erro)
