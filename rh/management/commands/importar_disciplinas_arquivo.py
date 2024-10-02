# -*- coding: utf-8 -*-

from django.conf import settings
from djtools.management.commands import BaseCommandPlus
from edu.models import Disciplina
import os


class Command(BaseCommandPlus):
    help = 'Inicia a importação disciplinas'

    def handle(self, *args, **options):
        arquivo = os.path.join(settings.BASE_DIR, 'rh/static/rh/disciplinas.txt')
        txt_file = open(arquivo, 'r')
        txt_linhas = txt_file.readlines()
        for linha in txt_linhas:
            Disciplina.objects.get_or_create(descricao=linha.strip())
        txt_file.close()
