# coding=utf-8

# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from avaliacao_integrada.models import Avaliacao


class Command(BaseCommandPlus):
    def handle(self, **options):
        for avaliacao in Avaliacao.objects.all():
            avaliacao.enviar_emails()
