import logging as log
import os
from os.path import basename
from django.apps import apps
from django.core.files.storage import default_storage
from contracheques.migracao import importar_contracheque
from djtools.management.commands import BaseCommandPlus
from zipfile import ZipFile
import zipfile
from datetime import datetime

Log = apps.get_model('comum', 'log')


class Command(BaseCommandPlus):
    help = 'Inicia a importação Contracheques'
    path = 'contracheques/arquivos_contracheque/'
    fita_espelho_path = 'contracheques/arquivos_contracheque/fita_espelho/'

    def handle(self, *args, **options):
        diretorio, arquivos = default_storage.listdir(self.path)
        for arquivo in arquivos:
            eh_test = False
            if arquivo.split("_")[0] == "test":
                eh_test = True

            tipo = ''
            if arquivo.find("servidores") != -1:
                tipo = 'servidores'
            elif arquivo.find("pensionistas") != -1:
                tipo = 'pensionistas'
            else:
                continue
            log.info(f'>>> Iniciando Importação dos Contracheques dos {tipo}... {arquivo}')
            f = default_storage.open(os.path.join(self.path, arquivo), 'rb')
            contracheques = importar_contracheque(f, tipo)
            log.info(f'>>> Finalizando Importação dos Contracheques dos {tipo}... {arquivo}')

            if not eh_test:
                Log.objects.create(
                    titulo='Importação de Fita Espelho %s' % tipo,
                    texto='Foram importados {} Novos Contracheques e {} foram Atualizados'.format(contracheques['NOVOS'], contracheques['ATUALIZADOS']),
                    app='CC',
                )
            log.info('>>> Processado(s) {} Novos Contracheques e {} foram Atualizados'.format(contracheques['NOVOS'], contracheques['ATUALIZADOS']))

        arquivos = [i for i in arquivos if i.endswith(".txt")]

        # zipar os arquivos encontrados e salvar na pasta de contracheques
        if arquivos:
            file_zip_name = f"fita_espelho_{datetime.now()}.zip"
            zipObj = ZipFile(self.path + file_zip_name, "w", zipfile.ZIP_DEFLATED)
            check_arquivos = 0
            for f in arquivos:
                if arquivo.split("_")[0] == "test":
                    continue
                arquivo_path = os.path.join(self.path, f)
                with default_storage.open(arquivo_path, "rb") as arq:
                    zipObj.write(arq.name, basename(arq.name))
                check_arquivos += 1
            zipObj.close()

            # se não tiver nenhum arquivo que não seja testes, apaga o arquivo zip criado
            if check_arquivos == 0 and os.path.exists(self.path + file_zip_name):
                os.remove(self.path + file_zip_name)

            # excluir os arquivos da pasta de media
            for f in arquivos:
                arquivo_path = os.path.join(self.path, f)
                default_storage.delete(arquivo_path)
