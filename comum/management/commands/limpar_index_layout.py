# -*- coding: utf-8 -*-
from comum.models import IndexLayout
from djtools.management.commands import BaseCommandPlus
from djtools.layout import quadros_cadastrados


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        IndexLayout.objects.exclude(quadro_nome__in=quadros_cadastrados).delete()
