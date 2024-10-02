# -*- coding: utf-8 -*-
"""
#easy_install xlrd
"""

from django.conf import settings
import xlrd

from djtools.management.commands import BaseCommandPlus
from edu.models import Estado, Cidade, Pais, Cartorio, OrgaoEmissorRg

# Agora os arquivos estão dentro da pasta /comum/cadastros_basicos/


class Command(BaseCommandPlus):
    def add_arguments(self, parser):
        # Named (optional) arguments
        parser.add_argument('--paises', action='store_true', dest='paises', default=False, help='Importe apenas países')

        parser.add_argument('--estados', action='store_true', dest='estados', default=False, help='Importe apenas estados')

        parser.add_argument('--cidades', action='store_true', dest='cidades', default=False, help='Importe apenas cidades')

        parser.add_argument('--cartorios', action='store_true', dest='cartorios', default=False, help='Importe apenas cartórios')

        parser.add_argument('--emissoresrg', action='store_true', dest='emissoresrg', default=False, help='Importe apenas órgãos emissores de RG')

    def handle(self, *args, **options):
        noargs = not options['paises'] and not options['estados'] and not options['cidades'] and not options['cartorios'] and not options['emissoresrg']

        if options['paises'] or noargs:
            workbook = xlrd.open_workbook('{}/comum/cadastros_basicos/paises.xls'.format(settings.BASE_DIR))
            sheet = workbook.sheet_by_index(0)
            if options['verbosity']:
                print('Importando Países')
            for i in range(1, sheet.nrows):
                # Sigla    Nome
                Pais.objects.get_or_create(sigla=sheet.cell_value(i, 0), nome=sheet.cell_value(i, 1).strip())

        if options['estados'] or noargs:
            workbook = xlrd.open_workbook('{}/comum/cadastros_basicos/estados.xls'.format(settings.BASE_DIR))
            sheet = workbook.sheet_by_index(0)
            if options['verbosity']:
                print('Importando Estados')
            for i in range(1, sheet.nrows):
                # Código    Nome
                Estado.objects.get_or_create(id=sheet.cell_value(i, 0), nome=sheet.cell_value(i, 1).strip())

        if options['cidades'] or noargs:
            workbook = xlrd.open_workbook('{}/comum/cadastros_basicos/cidades.xls'.format(settings.BASE_DIR))
            sheet = workbook.sheet_by_index(0)
            if options['verbosity']:
                print('Importando Cidades')
            for i in range(1, sheet.nrows):
                # Código Município    Código UF    Nome do Município    CEP Inicial    CEP Final
                try:
                    Cidade.objects.get_or_create(
                        id=sheet.cell_value(i, 0),
                        estado_id=sheet.cell_value(i, 1),
                        nome=sheet.cell_value(i, 2).strip(),
                        cep_inicial=sheet.cell_value(i, 3),
                        cep_final=sheet.cell_value(i, 4),
                    )
                except Exception:
                    print(('Impossível atualizar cidade {} já cadastrada'.format(sheet.cell_value(i, 2).strip())))
        if options['cartorios'] or noargs:
            workbook = xlrd.open_workbook('{}/comum/cadastros_basicos/cartorios.xls'.format(settings.BASE_DIR))
            sheet = workbook.sheet_by_index(0)
            if options['verbosity']:
                print('Importando Cartórios')
            for i in range(1, sheet.nrows):
                # Codigo    Nome    Município    UF    Serventia
                if sheet.cell_value(i, 2):
                    try:
                        Cartorio.objects.get_or_create(
                            id=sheet.cell_value(i, 0), nome=sheet.cell_value(i, 1).strip(), cidade_id=sheet.cell_value(i, 2), serventia=sheet.cell_value(i, 4)
                        )
                    except Exception:
                        print(('Impossível atualizar cartório {} já cadastrado'.format(sheet.cell_value(i, 1).strip())))
        if options['emissoresrg'] or noargs:
            workbook = xlrd.open_workbook('{}/comum/cadastros_basicos/emissores_rg.xls'.format(settings.BASE_DIR))
            sheet = workbook.sheet_by_index(0)
            if options['verbosity']:
                print('Importando Órgãos Emissores de RG')
            for i in range(1, sheet.nrows):
                # Codigo    Nome
                try:
                    OrgaoEmissorRg.objects.get_or_create(id=sheet.cell_value(i, 0), nome=sheet.cell_value(i, 1).strip())
                except Exception:
                    print(('Impossível atualizar órgão {} já cadastrado'.format(sheet.cell_value(i, 1).strip())))
