# -*- coding: utf-8 -*-
import os
import tempfile
import zipfile
from datetime import datetime

from django.conf import settings
from djtools.assincrono import task
from documento_eletronico.utils import merge_pdf_files

from processo_eletronico.utils import gerar_partes_processo_pdf


@task('Gerar Processo PDF')
def gerar_processo_pdf(user, processo, leitura_para_barramento, eh_consulta_publica=False, task=None):
    '''
    Método que retorna o PDF completo do processo.

    :param user: usuário que está querendo ver os PDFs que compõem o processo.
    :param processo: o processo em si
    :param leitura_para_barramento: identifica se o PDFs exibido tem como objetivo a tramitação para barramento. Se for,
     então alguma regras vão ser aplicadas para saber se o PDF deverá conter o conteúdo do documento ou apenas alguns
     dados básicos.
    '''
    paths_files = []

    def add_file_temp_dir(content, nome_arquivo):
        base_filename = '{0}.pdf'.format(nome_arquivo)
        filename = os.path.join(settings.TEMP_DIR, base_filename.replace(" ", "_"))
        arquivo = open(filename, 'wb+')
        arquivo.write(content)
        arquivo.close()
        paths_files.append(arquivo.name)

    def remove_files_temp_dir(paths_files):
        for path_file in paths_files:
            os.remove(path_file)

    partes_processo_pdf = gerar_partes_processo_pdf(processo,
                                                    user,
                                                    leitura_para_barramento,
                                                    eh_consulta_publica=eh_consulta_publica, task=task)
    ordem = 0
    agora = datetime.now()
    for parte_processo in task.iterate(partes_processo_pdf):
        ordem += 1
        add_file_temp_dir(parte_processo['pdf'], "{}_{}_{}".format(ordem, processo.id, agora))

    tmp = tempfile.NamedTemporaryFile(suffix='.pdf', mode='w+b', delete=False)
    tmp.write(merge_pdf_files(paths_files))
    tmp.close()
    task.update_progress(90)
    remove_files_temp_dir(paths_files)
    task.finalize('Processo Gerado com sucesso.', '..', file_path=tmp.name)


@task('Gerar Zip do Processo')
def gerar_zip_processo(user, processo, leitura_para_barramento, eh_consulta_publica=False, task=None):
    '''
    Método que retorna o ZIP com os PDFs do processo.

    :param user: usuário que está querendo ver os PDFs que compõem o processo.
    :param processo: o processo em si
    :param leitura_para_barramento: identifica se o PDFs exibido tem como objetivo a tramitação para barramento. Se for,
     então alguma regras vão ser aplicadas para saber se o PDF deverá conter o conteúdo do documento ou apenas alguns
     dados básicos.
    '''
    paths_files = []

    def add_file_temp_dir(content, nome_arquivo):
        base_filename = '{0}.pdf'.format(nome_arquivo)
        filename = os.path.join(settings.TEMP_DIR, base_filename.replace(" ", "_"))
        arquivo = open(filename, 'wb+')
        arquivo.write(content)
        arquivo.close()
        paths_files.append(arquivo.name)

    def remove_files_temp_dir(paths_files):
        for path_file in paths_files:
            os.remove(path_file)
    partes_processo_pdf = gerar_partes_processo_pdf(processo,
                                                    user,
                                                    leitura_para_barramento,
                                                    eh_consulta_publica, task=task)
    ordem = 0
    agora = datetime.now()
    task.count(partes_processo_pdf)
    for parte_processo in partes_processo_pdf:
        ordem += 1
        add_file_temp_dir(parte_processo['pdf'], "{}_{}_{}".format(ordem, processo.id, agora))

    path_zip = os.path.join(settings.TEMP_DIR, str(processo.id) + '.zip')
    zip_file = zipfile.ZipFile(path_zip, 'w')

    for path in paths_files:
        zip_file.write(os.path.relpath(path), os.path.basename(path), compress_type=zipfile.ZIP_DEFLATED)

    zip_file.close()
    task.update_progress(99)
    remove_files_temp_dir(paths_files)
    task.finalize('Processo Gerado com sucesso.', '..', file_path=zip_file.filename)
