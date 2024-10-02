# coding=utf-8

# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from rh.models import Setor


class Command(BaseCommandPlus):
    def handle(self, **options):
        setores = Setor.objects.exclude(superior__isnull=True).filter(areas_vinculacao__isnull=True)
        for setor in setores:
            setor_pai = setor.superior
            areas_vinculacao_pai = setor_pai.areas_vinculacao.all()
            setores_filhos = setor_pai.filhos.filter(areas_vinculacao__isnull=True)

            for setor_filho in setores_filhos:
                for area_vinculacao in areas_vinculacao_pai:
                    setor_filho.areas_vinculacao.add(area_vinculacao)
