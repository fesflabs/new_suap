# -*- coding: utf-8 -*-
from django.apps import apps
from django.db import transaction

from djtools.management.commands import BaseCommandPlus
from djtools.utils import imprimir_percentual


# TODO esse comando sera exlcuido quando a rotina atualizar_status_processo estiver estavel


class Command(BaseCommandPlus):
    @transaction.atomic()
    def handle(self, *args, **options):
        SolicitacaoCiencia = apps.get_model("processo_eletronico", "SolicitacaoCiencia")
        for ciencia in imprimir_percentual(SolicitacaoCiencia.objects.solicitacoes_pendentes()):
            ciencia.atualizar_status_ciencia()
            ciencia.save()
            if ciencia.esta_esperando_nao_expirado() and ciencia.processo.esta_ativo():
                ciencia.processo.aguardar_ciencia()
                ciencia.processo.save()
