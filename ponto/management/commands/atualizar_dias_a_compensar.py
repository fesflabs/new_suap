# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from ponto.models import RecessoOpcaoEscolhida, RecessoOpcao

"""
    Compensações em Acompanhamento - Recesso de Natal/Ano Novo - Validação: Autorizado
    Corrigir Dias Efetivos a Compensar
"""


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        print('Compensações em Acompanhamento - Recesso de Natal/Ano Novo - Validação: Autorizado')

        print('----------------------------------------------------------')
        print('Corrigindo Dias Efetivos a Compensar')

        qtd = 0
        qtd_erro = 0
        for acompanhamento in RecessoOpcaoEscolhida.objects.filter(recesso_opcao__tipo=RecessoOpcao.TIPO_NATAL_ANO_NOVO, validacao=RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO):
            try:
                acompanhamento.dias_efetivos_a_compensar_cache = ''  # força recriar o cache
                acompanhamento.dias_efetivos_a_compensar()
            except Exception:
                qtd_erro += 1
            qtd += 1

        print(('Total de Acompanhamentos: {}'.format(qtd)))
        print(('Erros: {}'.format(qtd_erro)))
