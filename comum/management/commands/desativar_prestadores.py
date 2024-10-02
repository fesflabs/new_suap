# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from comum.models import PrestadorServico
import datetime


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        for prestador in PrestadorServico.objects.all():
            ativo = False
            for ocupacao_prestador in prestador.ocupacaoprestador_set.all():
                if ocupacao_prestador.data_fim > datetime.date.today() or ocupacao_prestador.data_fim is None:
                    ativo = True
            prestador.ativo = ativo
            prestador.save()
