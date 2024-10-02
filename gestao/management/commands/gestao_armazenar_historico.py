# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from gestao.models import Variavel, HistoricoVariavel


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        for variavel in Variavel.objects.all():
            HistoricoVariavel.armazenar_dados(variavel)
