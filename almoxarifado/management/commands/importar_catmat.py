import os
import sys

import xlrd
from django.utils import termcolors

from almoxarifado.models import Catmat
from djtools.management.commands import BaseCommandPlus
from suap import settings


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        arquivo = os.path.join(settings.BASE_DIR, 'almoxarifado/fixtures/Lista-CATMAT-CATSER-publica-portal-Mai-2019.xlsx')
        print('Processando arquivo: {}'.format(arquivo))
        workbook = xlrd.open_workbook(arquivo)
        planilha_catmat = workbook.sheet_by_index(0)
        count = 0
        total = planilha_catmat.nrows
        for idx in range(7, planilha_catmat.nrows):
            count += 1
            porcentagem = int(float(count) / total * 100)
            sys.stdout.write(
                termcolors.make_style(fg='cyan', opts=('bold',))('\r[{0}] {1}% - Processando dados {2} de {3}'.format('#' * int(porcentagem / 10), porcentagem, count, total))
            )
            sys.stdout.flush()
            codigo = "{:0.0f}".format(planilha_catmat.cell_value(idx, 6))
            descricao = planilha_catmat.cell_value(idx, 7)
            catmat, created = Catmat.objects.get_or_create(codigo=codigo, descricao=descricao)
