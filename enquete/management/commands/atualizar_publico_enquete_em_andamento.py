# -*- coding: utf-8 -*-
"""
Comando para atualizar os públicos das enquetes em andamento
"""
from djtools.management.commands import BaseCommandPlus
from enquete.models import Enquete
import datetime


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        hoje = datetime.date.today()
        for enquete in Enquete.objects.filter(data_inicio__lte=hoje, data_fim__gte=hoje, publicada=True):
            enquete.save()
