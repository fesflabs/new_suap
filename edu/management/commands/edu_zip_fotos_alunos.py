# -*- coding: utf-8 -*-
import os
import zipfile

import tqdm

from djtools.management.commands import BaseCommandPlus
from djtools.storages import cache_file, get_temp_storage
from edu.models import Aluno
from rh.models import UnidadeOrganizacional


class Command(BaseCommandPlus):
    help = 'Gera o arquivo fotos_alunos_campus.zip no storage para ser baixado pelos terminais de refeitorio'

    def handle(self, *args, **options):
        storage = get_temp_storage()
        storage.file_overwrite = True
        arquivo_dump = '/tmp/fotos_alunos.zip'
        for uo in tqdm.tqdm(UnidadeOrganizacional.locals.all()):
            zip_file = zipfile.ZipFile(arquivo_dump, 'w', zipfile.ZIP_DEFLATED)
            for aluno in Aluno.objects.filter(curso_campus__diretoria__setor__uo=uo).exclude(pessoa_fisica__foto=''):
                try:
                    if not aluno.pessoa_fisica.foto:
                        continue
                except Exception:
                    continue
                try:
                    remote_filename = aluno.pessoa_fisica.foto.name.replace('fotos/', 'fotos/150x200/')
                    local_filename = cache_file(remote_filename)
                    zip_file.write(local_filename, '{}.jpg'.format(aluno.matricula))
                    os.unlink(local_filename)
                except FileNotFoundError:
                    pass
            zip_file.close()
            storage.save(f'fotos/fotos_alunos_{uo.sigla}.zip', open(arquivo_dump, 'rb'))
