# -*- coding: utf-8 -*-

from comum.utils import extrai_matricula
from datetime import datetime
from decimal import Decimal
from django.apps import apps
from djtools.management.commands import BaseCommandPlus
from djtools.utils import mask_cpf
from rh.models import Viagem, Servidor, PessoaFisica, BilheteViagem
from django.conf import settings
import logging as log
import os
import xlrd

Log = apps.get_model('comum', 'log')


class Command(BaseCommandPlus):
    help = 'Inicia a importação das Viagens SCDP'
    path = os.path.join(settings.BASE_DIR, 'rh/arquivos_scdp/')
    path_viagens = os.path.join(path, 'viagens/')
    path_bilhetes = os.path.join(path, 'bilhetes/')

    def handle(self, *args, **options):
        for arquivo in os.listdir(self.path_viagens):
            if arquivo.endswith('.xls') or arquivo.endswith('.xlsx'):
                log.info('>>> Processando Importar Viagens SCDP...')
                viagens = importar_viagens_scdp(os.path.join(self.path_viagens, arquivo))
                Log.objects.create(
                    titulo='Importação de viagens do SCDP',
                    texto='Foram importados %s Novas Viagens e %s foram Atualizados' % (viagens['NOVOS'], viagens['ATUALIZADOS']),
                    app='SCDP',
                )
                log.info('>>> Processado(s) %s Novas viagens do SCDP e %s foram Atualizados' % (viagens['NOVOS'], viagens['ATUALIZADOS']))

        arquivos = [i for i in os.listdir(self.path_viagens) if i.endswith('.xls') or i.endswith('.xlsx')]
        for f in arquivos:
            os.remove(self.path_viagens + f)

        for arquivo in os.listdir(self.path_bilhetes):
            if arquivo.endswith('.xls') or arquivo.endswith('.xlsx'):
                log.info('>>> Processando Importar Bilhetes das Viagens SCDP...')
                bilhetes = importar_bilhetes_viagens_scdp(os.path.join(self.path_bilhetes, arquivo))
                Log.objects.create(
                    titulo='Importação de Bilhetes das viagens do SCDP',
                    texto='Foram importados %s Novas Viagens e %s foram Atualizados' % (bilhetes['NOVOS'], bilhetes['ATUALIZADOS']),
                    app='SCDP',
                )
                log.info('>>> Processado(s) %s Novos Bilhetes das viagens do SCDP e %s foram Atualizados' % (bilhetes['NOVOS'], bilhetes['ATUALIZADOS']))

        arquivos = [i for i in os.listdir(self.path_bilhetes) if i.endswith('.xls') or i.endswith('.xlsx')]
        for f in arquivos:
            os.remove(self.path_bilhetes + f)


def importar_viagens_scdp(filepath):
    retorno = dict(NOVOS=0, ATUALIZADOS=0)
    workbook = xlrd.open_workbook(filepath)
    linha = workbook.sheet_by_index(0)
    for idx, i in enumerate(range(0, linha.nrows)):
        if idx == 0:
            continue
        numero_pcdp = linha.cell_value(i, 2)
        kwargs = dict(
            nome_siorg=linha.cell_value(i, 1),
            tipo_proposto=linha.cell_value(i, 6),
            motivo_viagem=linha.cell_value(i, 7),
            objetivo_viagem=linha.cell_value(i, 8),
            data_inicio_viagem=datetime(*xlrd.xldate_as_tuple(linha.cell_value(i, 9), workbook.datemode)).date(),
            data_fim_viagem=datetime(*xlrd.xldate_as_tuple(linha.cell_value(i, 10), workbook.datemode)).date(),
            situacao=int(linha.cell_value(i, 11)),
            quantidade_viagens=int(linha.cell_value(i, 12)),
            quantidade_de_dias_afastamento=int(linha.cell_value(i, 13)),
            quantidade_de_diarias=Decimal('%.2f' % (linha.cell_value(i, 14),)),
            valor_desconto_auxilio_alimentacao=Decimal('%.2f' % (linha.cell_value(i, 15),)),
            valor_desconto_auxilio_transporte=Decimal('%.2f' % (linha.cell_value(i, 16),)),
            valor_passagem=Decimal('%.2f' % (linha.cell_value(i, 17),)),
            valor_diaria=Decimal('%.2f' % (linha.cell_value(i, 18),)),
            valor_viagem=Decimal('%.2f' % (linha.cell_value(i, 19),)),
            codigo_siorg=('%.2f' % (linha.cell_value(i, 0),)).rstrip('0').rstrip('.'),
            nome_proposto=linha.cell_value(i, 3),
        )
        try:
            if type(linha.cell_value(i, 5)) == float:
                matricula = extrai_matricula(('%.2f' % (linha.cell_value(i, 5),)).rstrip('0').rstrip('.'))
            else:
                matricula = extrai_matricula(linha.cell_value(i, 5))
        except Exception:
            matricula = None
        try:
            cpf = mask_cpf(linha.cell_value(i, 4))
        except Exception:
            cpf = None
        nome_pessoa_fisica = linha.cell_value(i, 3)
        servidor = None
        pessoa_fisica = None

        if cpf:
            if matricula and Servidor.objects.filter(matricula=matricula).exists():
                servidor = Servidor.objects.filter(matricula=matricula)[0]
                pessoa_fisica = servidor.pessoafisica_ptr
            elif PessoaFisica.objects.filter(cpf=cpf).exists():
                pessoa_fisica = PessoaFisica.objects.filter(cpf=cpf)[0]
            else:
                pessoa_fisica = PessoaFisica.objects.create(cpf=cpf, nome=nome_pessoa_fisica)

        kwargs['servidor'] = servidor
        kwargs['pessoa_fisica'] = pessoa_fisica

        if Viagem.objects.filter(numero_pcdp=numero_pcdp).exists():
            Viagem.objects.filter(numero_pcdp=numero_pcdp).update(**kwargs)
            retorno['ATUALIZADOS'] = retorno['ATUALIZADOS'] + 1
        else:
            kwargs['numero_pcdp'] = numero_pcdp
            Viagem.objects.create(**kwargs)
            retorno['NOVOS'] = retorno['NOVOS'] + 1

    return retorno


def importar_bilhetes_viagens_scdp(filepath):
    retorno = dict(NOVOS=0, ATUALIZADOS=0, ERROS=0)
    workbook = xlrd.open_workbook(filepath)
    linha = workbook.sheet_by_index(0)
    for idx, i in enumerate(range(0, linha.nrows)):
        if idx == 0:
            continue
        numero_pcdp = linha.cell_value(i, 0)
        numero = linha.cell_value(i, 1)
        if type(numero) == float and numero.is_integer():
            numero = str(numero.as_integer_ratio()[0])
        kwargs = dict(tipo=linha.cell_value(i, 2), status=linha.cell_value(i, 3))
        if linha.cell_value(i, 4):
            try:
                kwargs['data_emissao'] = datetime(*xlrd.xldate_as_tuple(linha.cell_value(i, 4), workbook.datemode)).date()
            except Exception:
                print('Não tem data emissão')

        if Viagem.objects.filter(numero_pcdp=numero_pcdp).exists():
            viagem = Viagem.objects.filter(numero_pcdp=numero_pcdp)[0]
            if BilheteViagem.objects.filter(viagem=viagem, numero=numero).exists():
                BilheteViagem.objects.filter(viagem=viagem, numero=numero).update(**kwargs)
                retorno['ATUALIZADOS'] = retorno['ATUALIZADOS'] + 1
            else:
                kwargs['viagem'] = viagem
                kwargs['numero'] = numero
                BilheteViagem.objects.create(**kwargs)
                retorno['NOVOS'] = retorno['NOVOS'] + 1
        else:
            retorno['ERROS'] = retorno['ERROS'] + 1

    return retorno
