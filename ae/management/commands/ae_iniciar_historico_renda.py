# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus


from ae.models import Caracterizacao, HistoricoRendaFamiliar


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        for c in Caracterizacao.objects.all().order_by('id'):
            c.save()
        print((Caracterizacao.objects.count(), HistoricoRendaFamiliar.objects.count()))
