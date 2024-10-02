# -*- coding: utf-8 -*-
from djtools.management.commands import BaseCommandPlus
from auxilioemergencial.models import InscricaoInternet, InscricaoDispositivo, InscricaoMaterialPedagogico, SEM_PARECER


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        InscricaoInternet.objects.filter(parecer=SEM_PARECER).update(data_parecer=None)
        InscricaoDispositivo.objects.filter(parecer=SEM_PARECER).update(data_parecer=None)
        InscricaoMaterialPedagogico.objects.filter(parecer=SEM_PARECER).update(data_parecer=None)
