# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from conectagov_pen.processa_pendencias import processar_pendencias


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        processar_pendencias()
