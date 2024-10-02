# -*- coding: utf-8 -*-
import datetime
from edu.models import ConfiguracaoPedidoMatricula, PedidoMatriculaDiario
from djtools.management.commands import BaseCommandPlus
from edu import tasks


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        pks = (
            PedidoMatriculaDiario.objects.filter(
                pedido_matricula__configuracao_pedido_matricula__ano_letivo__ano__gte=2018,
                pedido_matricula__configuracao_pedido_matricula__data_fim__lt=datetime.date.today(),
                motivo__isnull=True,
            )
            .order_by('pedido_matricula__configuracao_pedido_matricula')
            .values_list('pedido_matricula__configuracao_pedido_matricula', flat=True)
            .distinct()
        )
        for configuracao in ConfiguracaoPedidoMatricula.objects.filter(pk__in=pks):
            tasks.processar_pedidos_matricula(configuracao)
