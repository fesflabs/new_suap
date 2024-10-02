# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from ae.models import Caracterizacao
import tqdm


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        for caracterizacao in tqdm.tqdm(Caracterizacao.objects.all()):
            if caracterizacao.historico_caracterizacao:
                caracterizacao.historico_caracterizacao.caracterizacao_relacionada = caracterizacao
                caracterizacao.historico_caracterizacao.save()
