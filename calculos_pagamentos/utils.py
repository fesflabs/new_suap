# -*- coding: utf-8 -*-
# IFMA

import os

import xlrd
from django.conf import settings

from calculos_pagamentos.models import NivelVencimento, ValorPorNivelVencimento, ValorPorNivelVencimentoDocente, ValorRetribuicaoTitulacao
from djtools.storages import cache_file
from rh.models import JornadaTrabalho, Titulacao


# IFMA FIM


# IFMA/Tássio
def isfloat(value):
    try:
        float(value)
        return True
    except ValueError:
        return False


# Método criado no IFMA por Tássio Luz Campos para fazer a leitura de arquivos XLS com os valores de vencimentos de
# TAEs e preencher a tabela de vencimentos de TAEs com esses valores.
def atualizar_tabelas_de_vencimento_tae():
    '''
    REQUISITOS:
    - Haver um Grupo de Documentos chamado "Tabelas de Vencimentos de TAEs"
    - A descrição dos arquivos salvos no Grupo de Documentos "Tabelas de Vencimentos de TAEs" deve ser no
        formato TIPO-DATAINICIAL-DATAFINAL, sendo válidos os seguintes valores:
        - TIPO: TAE
        - DATAINICIAL e DATAFINAL: no formato DD.MM.AAAA (00.00.0000 significa que não há data)
    - Os arquivos devem ser do tipo .xls ou .xlsx
    - Na primera planilha, o primeiro número de cada linha que tenha números deve ser o valor de um nível, sendo que o
        primeiro desses valores corresponde ao nível mais baixo e o nível vai aumentando até a última linha com números.
    PS.: Lembrar de não deixar a data de fim de um período sobrepôr a data de início de outro.
    '''
    if 'conteudoportal' in settings.INSTALLED_APPS_SUAP:
        from conteudoportal.models import Documento

        niveis = NivelVencimento.objects.filter(categoria='tecnico_administrativo').order_by('id')
        try:
            arquivos = Documento.objects.get(titulo="Tabelas de Vencimentos de TAEs").arquivo_set.all()
            for arquivo in arquivos:
                nome = arquivo.descricao
                parametros = nome.split("-")
                d_ini = parametros[1]
                d_fim = parametros[2]

                if d_ini.split(".")[2] == "0000" and d_ini.split(".")[1] == "00" and d_ini.split(".")[0] == "00":
                    data1 = None
                else:
                    data1 = '%s-%s-%s' % (d_ini.split(".")[2], d_ini.split(".")[1], d_ini.split(".")[0])
                if d_fim.split(".")[2] == "0000" and d_fim.split(".")[1] == "00" and d_fim.split(".")[0] == "00":
                    data2 = None
                else:
                    data2 = '%s-%s-%s' % (d_fim.split(".")[2], d_fim.split(".")[1], d_fim.split(".")[0])
                filepath = cache_file(arquivo.arquivo.name)
                # IFMA/Tássio: Se sem arquivo = link externo = não entra
                if arquivo.arquivo and os.path.exists(filepath) and (filepath.endswith('.xls') or filepath.endswith('.xlsx')):
                    workbook = xlrd.open_workbook(filepath)
                    planilha = workbook.sheet_by_index(0)
                    nivel_idx = 0
                    for i in range(0, planilha.nrows):
                        for j in range(0, planilha.ncols):
                            str = planilha.cell_value(i, j)
                            if isfloat(str):
                                valor = float(str)
                                print(nome, valor)
                                nivel = niveis[nivel_idx]
                                ValorPorNivelVencimento.objects.update_or_create(nivel=nivel, data_inicio=data1, data_fim=data2, defaults={'valor': valor})
                                nivel_idx += 1
                                break
        except Exception:
            # Mostre na tela
            import traceback

            trace = traceback.format_exc()
            print('Aconteceu um erro:\n', trace)
            return False, 'Erro. Existe Grupo de Documentos chamado "Tabelas de Vencimentos de TAEs"?'
        return True, 'OK'


# Método criado no IFMA por Tássio Luz Campos para fazer a leitura de arquivos XLS com os valores de vencimentos de
# docentes e preencher a tabela de vencimentos de docentes com esses valores.
def atualizar_tabelas_de_vencimento_docente():
    '''
    REQUISITOS:
    - Haver um Grupo de Documentos chamado "Tabelas de Vencimentos de Docentes"
    - A descrição dos arquivos salvos no Grupo de Documentos "Tabelas de Vencimentos de Docentes" deve ser no
        formato TIPO-JORNADA-DATAINICIAL-DATAFINAL, sendo válidos os seguintes valores:
        - TIPO: Superior, EBTT
        - JORNADA: 20, 40, DE
        - DATAINICIAL e DATAFINAL: no formato DD.MM.AAAA (00.00.0000 significa que não há data)
    - Os arquivos devem ser do tipo .xls ou .xlsx
    - Na primeira planilha, as únicas linhas que tenham células com números racionais devem ter pelo menos 5 números
        racionais, sendo que eles estejam na ordem
        vencimento -> RT mais baixa -> ... -> RT mais alta
        e sendo que a primeira dessas linhas contendo os valores do nível mais alto e o nível ir diminuindo até a
        13ª das linhas.
    - Células de valores que estão vazias devem ser preenchidas com 0.
    PS.: Lembrar de não deixar a data de fim de um período sobrepôr a data de início de outro.
    '''

    if 'conteudoportal' in settings.INSTALLED_APPS_SUAP:
        from conteudoportal.models import Documento

        niveis_superior = ['8-801', '7-704', '7-703', '7-702', '7-701', '6-604', '6-603', '6-602', '6-601', '5-502', '5-501', '4-402', '4-401']
        niveis_ebtt = ['D501', 'D404', 'D403', 'D402', 'D401', 'D304', 'D303', 'D302', 'D301', 'D202', 'D201', 'D102', 'D101']
        aperf = Titulacao.objects.get(codigo="24")
        espec = Titulacao.objects.get(codigo="25")
        mestr = Titulacao.objects.get(codigo="26")
        douto = Titulacao.objects.get(codigo="27")
        rscI = Titulacao.objects.get(codigo="48")
        rscII = Titulacao.objects.get(codigo="49")
        rscIII = Titulacao.objects.get(codigo="50")
        titulacoes = [None, aperf, espec, mestr, douto]

        arquivos = Documento.objects.get(titulo="Tabelas de Vencimentos de Docentes").arquivo_set.all()
        for arquivo in arquivos:
            nome = arquivo.descricao
            parametros = nome.split("-")
            tipo = parametros[0]
            jornada_str = parametros[1]
            d_ini = parametros[2]
            d_fim = parametros[3]

            if tipo == "Superior":
                niveis = niveis_superior
            elif tipo == "EBTT":
                niveis = niveis_ebtt
            else:
                return False, 'Erro em Tipo de Docente. Opções: "Superior" e "EBTT".'

            if jornada_str == "20":
                jornada = JornadaTrabalho.objects.get(nome='20 HORAS SEMANAIS')
            elif jornada_str == "40":
                jornada = JornadaTrabalho.objects.get(nome='40 HORAS SEMANAIS')
            elif jornada_str == "DE":
                jornada = JornadaTrabalho.objects.get(nome='DEDICACAO EXCLUSIVA')
            else:
                return False, 'Erro em Jornada. Opções:"20", "40" e "DE".'

            if d_ini.split(".")[2] == "0000" and d_ini.split(".")[1] == "00" and d_ini.split(".")[0] == "00":
                data1 = None
            else:
                data1 = '%s-%s-%s' % (d_ini.split(".")[2], d_ini.split(".")[1], d_ini.split(".")[0])
            if d_fim.split(".")[2] == "0000" and d_fim.split(".")[1] == "00" and d_fim.split(".")[0] == "00":
                data2 = None
            else:
                data2 = '%s-%s-%s' % (d_fim.split(".")[2], d_fim.split(".")[1], d_fim.split(".")[0])

            filepath = cache_file(arquivo.arquivo.name)
            # IFMA/Tássio: Se sem arquivo = link externo = não entra
            if arquivo.arquivo and os.path.exists(filepath) and (filepath.endswith('.xls') or filepath.endswith('.xlsx')):
                workbook = xlrd.open_workbook(filepath)
                planilha = workbook.sheet_by_index(0)
                nivel_idx = 0
                for i in range(0, planilha.nrows):
                    linha_ok = False
                    nivel = NivelVencimento.objects.get(codigo=niveis[nivel_idx])
                    valor_idx = 0
                    for j in range(0, planilha.ncols):
                        str = planilha.cell_value(i, j)
                        if isfloat(str):
                            valor = float(str)
                            print(nome, valor)
                            if valor > 50 or valor == 0:
                                if valor_idx == 0:
                                    ValorPorNivelVencimentoDocente.objects.update_or_create(
                                        nivel=nivel, jornada_trabalho=jornada, data_inicio=data1, data_fim=data2, defaults={'valor': valor}
                                    )
                                elif 1 <= valor_idx <= 4:
                                    qs = ValorRetribuicaoTitulacao.objects.filter(
                                        nivel=nivel, jornada_trabalho=jornada, data_inicio=data1, data_fim=data2, titulacoes=titulacoes[valor_idx]
                                    )
                                    if not qs.exists():
                                        obj = ValorRetribuicaoTitulacao.objects.create(nivel=nivel, jornada_trabalho=jornada, data_inicio=data1, data_fim=data2, valor=valor)
                                    else:
                                        obj = qs[0]
                                        obj.valor = valor
                                        obj.save()
                                    if valor_idx == 1:
                                        obj.titulacoes.add(aperf)
                                    elif valor_idx == 2:
                                        obj.titulacoes.add(espec, rscI)
                                    elif valor_idx == 3:
                                        obj.titulacoes.add(mestr, rscII)
                                    elif valor_idx == 4:
                                        obj.titulacoes.add(douto, rscIII)
                                        linha_ok = True
                                        break
                                valor_idx += 1
                    if linha_ok:
                        nivel_idx += 1
                    if nivel_idx > 12:
                        break

        return True, 'OK'
