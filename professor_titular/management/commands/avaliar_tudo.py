# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from professor_titular.models import Avaliacao


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        processo_id = args[0]
        avaliador_id = args[1]

        # selecionado a avaliação
        avaliacao = Avaliacao.objects.filter(processo__id=processo_id, avaliador__id=avaliador_id)
        if avaliacao.exists():
            avaliacao = avaliacao[0]
            print(('Avaliação selecionada: %s' % avaliacao))
            for item in avaliacao.avaliacaoitem_set.all():
                item.data_referencia = item.arquivo.data_referencia
                item.qtd_itens_validado = item.arquivo.qtd_itens
                item.save()
