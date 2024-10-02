# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from rh.models import PessoaFisica
from edu.models import Aluno


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        PessoaFisica.objects.update(foto='')
        Aluno.objects.update(foto='')
