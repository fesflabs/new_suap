# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from ae.models import IntegranteFamiliarCaracterizacao


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        for registro in IntegranteFamiliarCaracterizacao.objects.filter(inscricao_caracterizacao__isnull=False):
            registro.id_inscricao = registro.inscricao_caracterizacao.id
            registro.save()
