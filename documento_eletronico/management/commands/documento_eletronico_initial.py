# -*- coding: utf-8 -*-
from django.core.management import call_command

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        call_command('loaddata', '../fixtures/initial_data_01_classificacao.json')
        # Os tipos de documento e modelos carregados a seguir foram criados com base em documentos presentes
        # na pasta do GABIN/RE.
        call_command('loaddata', '../fixtures/initial_data_02_tipo_documento.json')
        call_command('loaddata', '../fixtures/initial_data_03_modelo_documento.json')
        call_command('loaddata', '../fixtures/initial_data_04_tipo_conferencia.json')
        call_command('loaddata', '../fixtures/initial_data_05_tipo_vinculo_documento.json')
        call_command('importar_funcao_servidor')
