# -*- coding: utf-8 -*-#

from django.conf import settings
import os
import xlrd
from rh.models import PadraoVencimento


def importar_dados_progressoes():
    arquivo_padrao_vencimento = os.path.join(settings.BASE_DIR, 'progressoes/static/progressoes/padrao_vencimento.xlsx')
    workbook_padrao_vencimento = xlrd.open_workbook(arquivo_padrao_vencimento)
    planilha_padrao_vencimento = workbook_padrao_vencimento.sheet_by_index(0)
    for i in range(0, planilha_padrao_vencimento.nrows):
        PadraoVencimento.objects.get_or_create(
            categoria=planilha_padrao_vencimento.cell_value(i, 0),
            classe=planilha_padrao_vencimento.cell_value(i, 1),
            posicao_vertical='%02d' % planilha_padrao_vencimento.cell_value(i, 2),
        )
