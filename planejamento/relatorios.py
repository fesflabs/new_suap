# -*- coding: utf-8 -*-

from comum.utils import get_topo_pdf
from djtools import pdf
from datetime import date


def get_unidadeadministrativa_viaturas_pdf(unidadeadministrativa, viaturas_cadastradas):
    """
    Retorna os elementos PDF para geração do relatório de viaturas cadastradas na unidade administrativa
    """
    tabela_info = [['Data de Emissão:', date.today().strftime("%d/%m/%Y")], ['Unidade Administrativa:', unidadeadministrativa]]

    tabela_registros = [['Marca/Modelo', 'Cor', 'Combustíveis utilizados', 'Odômetro', 'Número de Passageiros', 'Ano de Fabricação']]

    for viatura in viaturas_cadastradas:
        marca_modelo = viatura['marca_modelo']
        cor = viatura['cor']
        combustiveis_utilizados = []
        for combustivel in viatura['combustiveis']:
            combustiveis_utilizados.append('%s<br />' % combustivel)
        combustiveis_utilizados = ''.join(combustiveis_utilizados)
        odometro = viatura['odometro']
        numero_passageiros = viatura['numero_passageiros']
        ano_fabricacao = viatura['ano_fabricacao']

        linha = [marca_modelo, cor, combustiveis_utilizados, odometro, numero_passageiros, ano_fabricacao]

        tabela_registros.append(linha)

    tabela_info = pdf.table(tabela_info, grid=0, w=[60, 80], auto_align=0)

    tabela_registros = pdf.table(tabela_registros, head=1, zebra=1, w=[40, 30, 30, 20, 40, 30], a=['l', 'l', 'l', 'r', 'c', 'c'])

    return get_topo_pdf('Relatório de Viaturas Cadastradas') + [tabela_info, pdf.space(8), tabela_registros]
