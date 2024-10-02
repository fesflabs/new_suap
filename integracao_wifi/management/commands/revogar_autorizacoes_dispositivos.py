# -*- coding: utf-8 -*-
import datetime
from integracao_wifi.models import AutorizacaoDispositivo
from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        qs = AutorizacaoDispositivo.objects.exclude(excluida=True)
        qs = qs.filter(data_validade_autorizacao__lt=datetime.datetime.today(), expirada=False)
        for obj in qs:
            obj.revogar_autorizacao()
        print(('{} autorização(ões) de dispositivo(s) revogada(s)'.format(qs.count())))
