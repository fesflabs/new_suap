# -*- coding: utf-8 -*-#
import os
from decimal import Decimal

import xlrd
from django.conf import settings

from rsc.models import TipoRsc, Diretriz, Unidade, Criterio, CategoriaMemorialDescritivo


def importar_diretrizes():
    arquivo = os.path.join(settings.BASE_DIR, 'rsc/static/rsc/diretrizes.xls')
    workbook = xlrd.open_workbook(arquivo)
    sheet = workbook.sheet_by_index(0)
    for i in range(0, sheet.nrows):
        tipo_rsc = TipoRsc.objects.get_or_create(nome=sheet.cell_value(i, 0), categoria=sheet.cell_value(i, 1))[0]
        Diretriz.objects.get_or_create(
            tipo_rsc=tipo_rsc, nome=sheet.cell_value(i, 2), descricao=sheet.cell_value(i, 3), peso=int(sheet.cell_value(i, 4)), teto=int(sheet.cell_value(i, 5))
        )


def importar_unidade_criterios():
    arquivo = os.path.join(settings.BASE_DIR, 'rsc/static/rsc/unidades_criterios.xls')
    workbook = xlrd.open_workbook(arquivo)
    sheet = workbook.sheet_by_index(0)
    for i in range(0, sheet.nrows):
        unidade = Unidade.objects.get_or_create(nome=sheet.cell_value(i, 6), sigla=sheet.cell_value(i, 6))[0]
        tipo_rsc = TipoRsc.objects.get_or_create(nome=sheet.cell_value(i, 0), categoria=sheet.cell_value(i, 1))[0]
        diretriz = Diretriz.objects.get_or_create(tipo_rsc=tipo_rsc, nome=sheet.cell_value(i, 2))[0]
        categoria_memorial = CategoriaMemorialDescritivo.objects.get_or_create(nome=sheet.cell_value(i, 8))[0]
        Criterio.objects.get_or_create(
            diretriz=diretriz,
            unidade=unidade,
            numero=int(sheet.cell_value(i, 3)),
            nome=sheet.cell_value(i, 4),
            fator=Decimal(sheet.cell_value(i, 5)),
            teto=int(sheet.cell_value(i, 7)),
            categoria_memorial_descritivo=categoria_memorial,
            status=0,
        )
