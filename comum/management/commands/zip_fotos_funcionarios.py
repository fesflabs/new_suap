# -*- coding: utf-8 -*-
import os
import zipfile

import tqdm

from comum.models import PrestadorServico
from djtools.management.commands import BaseCommandPlus
from djtools.storages import cache_file, get_temp_storage
from rh.models import Servidor


class Command(BaseCommandPlus):
    help = 'Gera o arquivo fotos_funcionarios.zip no storage para ser baixado pelos terminais de ponto'

    def handle(self, *args, **options):
        storage = get_temp_storage()
        storage.file_overwrite = True
        arquivo_dump = '/tmp/fotos_funcionarios.zip'
        zip_file = zipfile.ZipFile(arquivo_dump, 'w', zipfile.ZIP_DEFLATED)
        for s in tqdm.tqdm(Servidor.objects.ativos().exclude(foto__isnull=True, foto='').exclude(foto__isnull=True)):
            if not s.foto:
                continue
            try:
                remote_filename = s.foto.name.replace('fotos/', 'fotos/150x200/')
                local_filename = cache_file(remote_filename)
                zip_file.write(local_filename, '{}.jpg'.format(s.matricula))
                os.unlink(local_filename)
            except FileNotFoundError:
                pass
        for s in tqdm.tqdm(PrestadorServico.objects.filter(excluido=False).exclude(foto__isnull=True, foto='').exclude(foto__isnull=True)):
            if not s.foto:
                continue
            try:
                remote_filename = s.foto.name.replace('fotos/', 'fotos/150x200/')
                local_filename = cache_file(remote_filename)
                zip_file.write(local_filename, '{}.jpg'.format(s.matricula))
                os.unlink(local_filename)
            except FileNotFoundError:
                pass
        zip_file.close()
        storage.save('fotos/fotos_funcionarios.zip', open(arquivo_dump, 'rb'))
