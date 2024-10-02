# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from ponto.models import RecessoOpcaoEscolhida, RecessoOpcao

"""
    Compensações em Acompanhamento - Recesso de Natal/Ano Novo - Aguardando Validação
    Corrigir Validadores
"""


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        print('Compensações em Acompanhamento - Recesso de Natal/Ano Novo - Aguardando Validação')

        print('----------------------------------------------------------')
        print('Populando Validadores Possivelmente Incorretos')

        qtd = 0
        qtd_erro = 0
        qtd_chefes_modificados_por_outro = 0
        qtd_chefes_ja_atualizados = 0
        qtd_chefes_resetados_por_nao_haver_opcoes = 0
        qtd_chefes_resetados_por_nao_haver_opcoes_acompanhamentos = []
        qtd_chefes_resetados_por_haver_muitas_opcoes = 0
        qtd_chefes_resetados_por_haver_muitas_opcoes_acompanhamentos = []
        qtd_chefes_nao_modificados_por_ja_ser_uma_das_opcoes = 0
        for acompanhamento in RecessoOpcaoEscolhida.objects.filter(
            validador__isnull=False, recesso_opcao__tipo=RecessoOpcao.TIPO_NATAL_ANO_NOVO, validacao=RecessoOpcaoEscolhida.VALIDACAO_AGUARDANDO
        ).order_by('funcionario__nome'):
            try:
                chefes = acompanhamento.chefes

                if chefes.exists():
                    if acompanhamento.validador not in chefes:
                        if chefes.count() == 1:
                            if not acompanhamento.validador == chefes[0].servidor:
                                acompanhamento.validador = chefes[0].servidor
                                acompanhamento.save()
                                qtd_chefes_modificados_por_outro += 1
                            else:
                                qtd_chefes_ja_atualizados += 1
                        else:
                            # o chefe gravado é resetado pois há uma lista de chefes diferentes como opções!
                            acompanhamento.validador = None  # aqui um erro pode ser gerado!!
                            acompanhamento.save()
                            qtd_chefes_resetados_por_haver_muitas_opcoes += 1
                            qtd_chefes_resetados_por_haver_muitas_opcoes_acompanhamentos.append(acompanhamento)
                    else:
                        qtd_chefes_nao_modificados_por_ja_ser_uma_das_opcoes += 1  # aqui um erro pode permanecer!!
                else:
                    # o chefe gravado é limpo pois não há uma lista de chefes como opções!
                    acompanhamento.validador = None  # aqui um erro pode ser gerado!!
                    acompanhamento.save()
                    qtd_chefes_resetados_por_nao_haver_opcoes += 1
                    qtd_chefes_resetados_por_nao_haver_opcoes_acompanhamentos.append(acompanhamento)
            except Exception:
                qtd_erro += 1
            qtd += 1

        print(('Total de Acompanhamentos com Validadores Possivelmente Incorretos: {}'.format(qtd)))
        print(('Modificados por Outro: {}'.format(qtd_chefes_modificados_por_outro)))
        print(('Já Atualizados: {}'.format(qtd_chefes_ja_atualizados)))
        print(('Resetados por Não haver Opções: {}'.format(qtd_chefes_resetados_por_nao_haver_opcoes)))
        if qtd_chefes_resetados_por_nao_haver_opcoes:
            for acompanhamento in qtd_chefes_resetados_por_nao_haver_opcoes_acompanhamentos:
                print(('-----> {}'.format(acompanhamento.funcionario)))
        print(('Resetados por haver Muitas Opções: {}'.format(qtd_chefes_resetados_por_haver_muitas_opcoes)))
        if qtd_chefes_resetados_por_haver_muitas_opcoes:
            for acompanhamento in qtd_chefes_resetados_por_haver_muitas_opcoes_acompanhamentos:
                print(('-----> {}'.format(acompanhamento.funcionario)))
        print(('Não Modificados por Já ser Uma das Opções: {}'.format(qtd_chefes_nao_modificados_por_ja_ser_uma_das_opcoes)))
        print(('Erros: {}'.format(qtd_erro)))

        print('----------------------------------------------------------')
        print('Populando Validadores ainda Não Definidos')

        qtd = 0
        qtd_erro = 0
        qtd_salva_por_ter_um_chefe = 0
        qtd_nao_salva_por_ter_mais_de_um_chefe = 0
        qtd_nao_salva_por_ter_mais_de_um_chefe_acompanhamentos = []  # servidor e acompanhamento
        qtd_nao_salva_por_nao_ter_nenhum_chefe = 0
        qtd_nao_salva_por_nao_ter_nenhum_chefe_acompanhamentos = []  # servidor e acompanhamento
        for acompanhamento in RecessoOpcaoEscolhida.objects.filter(
            validador__isnull=True, recesso_opcao__tipo=RecessoOpcao.TIPO_NATAL_ANO_NOVO, validacao=RecessoOpcaoEscolhida.VALIDACAO_AGUARDANDO
        ).order_by('funcionario__nome'):
            try:
                chefes = acompanhamento.chefes

                if chefes.exists():
                    if chefes.count() == 1:
                        acompanhamento.validador = chefes[0].servidor
                        acompanhamento.save()
                        qtd_salva_por_ter_um_chefe += 1
                    else:
                        qtd_nao_salva_por_ter_mais_de_um_chefe += 1
                        qtd_nao_salva_por_ter_mais_de_um_chefe_acompanhamentos.append(acompanhamento)
                else:
                    qtd_nao_salva_por_nao_ter_nenhum_chefe += 1
                    qtd_nao_salva_por_nao_ter_nenhum_chefe_acompanhamentos.append(acompanhamento)
            except Exception:
                qtd_erro += 1
            qtd += 1

        print(('Total de Acompanhamentos com Validadores Não Definidos: {}'.format(qtd)))
        print(('Salvos (um chefe): {}'.format(qtd_salva_por_ter_um_chefe)))
        print(('Não Salvos (mais de um chefe): {}'.format(qtd_nao_salva_por_ter_mais_de_um_chefe)))
        if qtd_nao_salva_por_ter_mais_de_um_chefe:
            for acompanhamento in qtd_nao_salva_por_ter_mais_de_um_chefe_acompanhamentos:
                print(('-----> {}'.format(acompanhamento.funcionario)))
        print(('Não Salvos (nenhum chefe): {}'.format(qtd_nao_salva_por_nao_ter_nenhum_chefe)))
        if qtd_nao_salva_por_nao_ter_nenhum_chefe:
            for acompanhamento in qtd_nao_salva_por_nao_ter_nenhum_chefe_acompanhamentos:
                print(('-----> {}'.format(acompanhamento.funcionario)))
        print(('Erros: {}'.format(qtd_erro)))
