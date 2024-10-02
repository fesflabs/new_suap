import csv
import datetime
import operator
import os
import re
import tempfile
from django.conf import settings
from django.core.exceptions import ValidationError
from time import sleep

import xlrd
import xlwt
from django.db import transaction
from xlutils.copy import copy

from django.db.models import Count
from djtools.assincrono import task
from djtools.models import Task
from djtools.templatetags.filters import format_, getattrr
from djtools.testutils import running_tests
from djtools.utils import XlsResponse, CsvResponse, mask_cpf, similaridade
from djtools.utils.python import to_ascii

@task('Exportar Trabalhadores Educando - XLS')
def exportar_listagem_trabalhadores_educando_xls(trabalhadores_educando, filtros, campos_exibicao, cabecalhos, task=None):
    count = 0
    rows = [['#', 'Matrícula', 'Nome']]
    for campo in campos_exibicao:
        for label in cabecalhos:
            if label[0] == campo:
                rows[0].append(format_(label[1], html=False))
    task.count(trabalhadores_educando, trabalhadores_educando)
    for trabalhador_educando in task.iterate(trabalhadores_educando):
        # if ano_letivo and periodo_letivo:
        #     aluno.ano_letivo_referencia = ano_letivo
        #     aluno.periodo_letivo_referencia = periodo_letivo
        count += 1
        row = [count, format_(trabalhador_educando.matricula, html=False), format_(trabalhador_educando.get_nome_social_composto(), html=False)]
        for campo in campos_exibicao:
            row.append(format_(getattrr(trabalhador_educando, campo), html=False))
        rows.append(row)
    rows_filtros = [['FILTROS']]
    for filtro in filtros:
        rows_filtros.append([filtro.get('chave'), filtro.get('valor')])
    if len(rows) >= 65536:
        CsvResponse(rows, processo=task)
    else:
        XlsResponse({'Registros': rows, 'Filtros': rows_filtros}, processo=task)