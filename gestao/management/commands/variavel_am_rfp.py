# -*- coding: utf-8 -*-

import datetime

from djtools.management.commands import BaseCommandPlus
from gestao.models import Variavel, PeriodoReferencia


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        print('')
        print('- - - - -')
        print('Variáveis')
        print('- - - - -')
        print(
            (
                'Ano de Referência: {} ({} à {})'.format(
                    PeriodoReferencia.get_ano_referencia(), PeriodoReferencia.get_data_base().strftime('%d/%m/%Y'), PeriodoReferencia.get_data_limite().strftime('%d/%m/%Y')
                )
            )
        )
        print(('Data da consulta: {}'.format(datetime.datetime.now().strftime('%d/%m/%Y - %H:%M'))))
        print('')

        am = Variavel.objects.get(sigla='AM')
        print(('{} ({}) = {}'.format(am.sigla, am.nome, am.get_valor_formatado())))
        print(('SQL: {}'.format(am.get_querysets()[0].query)))

        print('')
        print('')

        rfp = Variavel.objects.get(sigla='RFP')
        print(('{} ({}) = {}'.format(rfp.sigla, rfp.nome, rfp.get_valor_formatado())))
        print('')

        faixas = [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 1000]
        for index, item in enumerate(faixas):
            if index > 0:
                qs = rfp.get_qs_renda_familiar(faixas[index - 1], faixas[index])
                print(('Faixa de {:.1f} a {:.1f}: {:d} '.format(faixas[index - 1], faixas[index], qs.count())))

            if index == 7:
                print(('SQL: {}' % qs.query))
