# -*- coding: utf-8 -
from django.apps import apps
from django.db import transaction

from djtools.management.commands import BaseCommandPlus
from djtools.utils import imprimir_percentual
from processo_eletronico.status import ProcessoStatus, SolicitacaoJuntadaStatus


# TODO esse comando sera exlcuido quando a rotina atualizar_status_processo estiver estavel


class Command(BaseCommandPlus):
    @transaction.atomic()
    def handle(self, *args, **options):
        SolicitacaoCiencia = apps.get_model("processo_eletronico", "SolicitacaoCiencia")
        print("Ajustando processos com Ciencias pendentes")
        for ciencia in imprimir_percentual(SolicitacaoCiencia.objects.solicitacoes_pendentes()):
            if ciencia.esta_esperando_nao_expirado() and ciencia.processo.esta_ativo():
                ciencia.processo.aguardar_ciencia()
                ciencia.processo.save()
        print("Ajustando processos com ciencias expiradas")
        for ciencia in imprimir_percentual(SolicitacaoCiencia.objects.solicitacoes_consideradas_cientes()):
            if ciencia.processo.esta_aguardando_ciencia():
                ciencia.processo.informar_ciencia()
                ciencia.processo.save()

        print("Ajustando processos antigos")
        Processo = apps.get_model("processo_eletronico", "Processo")
        SolicitacaoJuntada = apps.get_model("processo_eletronico", "SolicitacaoJuntada")
        status = [ProcessoStatus.STATUS_AGUARDANDO_JUNTADA]
        for processo in imprimir_percentual(Processo.objects.filter(status__in=status)):
            solicitacao_juntada = SolicitacaoJuntada.objects.filter(tramite__processo=processo, status=SolicitacaoJuntadaStatus.STATUS_EXPIRADO).first()
            if solicitacao_juntada:
                processo.colocar_em_tramite()
                processo.save()
