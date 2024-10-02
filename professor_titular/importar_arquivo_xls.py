# -*- coding: utf-8 -*-#
from decimal import Decimal
from django.conf import settings
from professor_titular.models import Grupo, CategoriaMemorialDescritivo, PontuacaoMinima, Unidade, Indicador, Criterio
import os
import xlrd


def importar_dados_titular():
    arquivo_grupo = os.path.join(settings.BASE_DIR, 'professor_titular/static/titular/grupo_titular.xlsx')
    workbook_grupo = xlrd.open_workbook(arquivo_grupo)
    planilha_grupo = workbook_grupo.sheet_by_index(0)
    for i in range(0, planilha_grupo.nrows):
        Grupo.objects.get_or_create(nome=planilha_grupo.cell_value(i, 0), percentual=Decimal(planilha_grupo.cell_value(i, 1)))

    arquivo_memorial = os.path.join(settings.BASE_DIR, 'professor_titular/static/titular/memorial_descritivo_titular.xlsx')
    workbook_memorial = xlrd.open_workbook(arquivo_memorial)
    planilha_memorial = workbook_memorial.sheet_by_index(0)
    for i in range(0, planilha_memorial.nrows):
        CategoriaMemorialDescritivo.objects.get_or_create(nome=planilha_memorial.cell_value(i, 1), indice=planilha_memorial.cell_value(i, 0))

    arquivo_pontuacao_minima = os.path.join(settings.BASE_DIR, 'professor_titular/static/titular/pontuacao_minima_titular_por_ano.xlsx')
    workbook_pontuacao_minima = xlrd.open_workbook(arquivo_pontuacao_minima)
    planilha_pontuacao_minima = workbook_pontuacao_minima.sheet_by_index(0)
    for i in range(0, planilha_pontuacao_minima.nrows):
        for grupo_banco in Grupo.objects.all():
            PontuacaoMinima.objects.get_or_create(
                grupo=grupo_banco,
                ano=planilha_pontuacao_minima.cell_value(i, 0),
                pontuacao_exigida=Decimal(planilha_pontuacao_minima.cell_value(i, 1)),
                qtd_minima_grupos=planilha_pontuacao_minima.cell_value(i, 2),
            )

    arquivo_indicador_criterios_titular = os.path.join(settings.BASE_DIR, 'professor_titular/static/titular/indicador_criterios_titular.xlsx')
    workbook_indicador_criterios_titular = xlrd.open_workbook(arquivo_indicador_criterios_titular)
    planilha_indicador_criterios_titular = workbook_indicador_criterios_titular.sheet_by_index(0)
    for i in range(0, planilha_indicador_criterios_titular.nrows):
        unidade = Unidade.objects.get_or_create(nome=planilha_indicador_criterios_titular.cell_value(i, 6), sigla=planilha_indicador_criterios_titular.cell_value(i, 6))[0]
        grupo = Grupo.objects.get_or_create(nome=planilha_indicador_criterios_titular.cell_value(i, 0))[0]
        item_memorial = CategoriaMemorialDescritivo.objects.get_or_create(indice=planilha_indicador_criterios_titular.cell_value(i, 1))[0]
        indicador = Indicador.objects.get_or_create(
            grupo=grupo, nome=planilha_indicador_criterios_titular.cell_value(i, 2), descricao=planilha_indicador_criterios_titular.cell_value(i, 3)
        )[0]
        Criterio.objects.get_or_create(
            indicador=indicador,
            artigo=planilha_indicador_criterios_titular.cell_value(i, 4),
            nome=planilha_indicador_criterios_titular.cell_value(i, 5),
            status=0,
            pontos=Decimal(planilha_indicador_criterios_titular.cell_value(i, 7)),
            unidade=unidade,
            categoria_memorial_descritivo=item_memorial,
        )
