# -*- coding: utf-8 -*-
from django.apps import apps
from django.core.cache import cache

from djtools.management.commands import BaseCommandPlus
from rh.importador import ImportadorSIAPE

Log = apps.get_model('comum', 'log')


class Command(BaseCommandPlus):
    help = 'Inicia a importação dos dados do SIAPE'

    def add_arguments(self, parser):
        parser.add_argument('--log', dest='log', default='DEBUG')

    def handle(self, *args, **options):
        importador = ImportadorSIAPE(log_level=options['log'])
        importador.descompactar_arquivos_manuais()
        if importador._verificar_arquivos():
            arquivos = importador.get_arquivos()
            importador.run()
            Log.objects.create(titulo='Importação de arquivos', texto='Os seguintes arquivos foram importados:' + ', '.join(arquivos), app='rh')
            cache.delete('data_ultima_importacao_siape')
