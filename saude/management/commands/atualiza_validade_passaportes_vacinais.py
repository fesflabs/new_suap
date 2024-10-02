# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from saude.models import PassaporteVacinalCovid
import datetime


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        PassaporteVacinalCovid.objects.filter(data_expiracao__isnull=False).filter(data_expiracao__lt=datetime.datetime.now()).update(situacao_passaporte=PassaporteVacinalCovid.INVALIDO, data_expiracao=None)
