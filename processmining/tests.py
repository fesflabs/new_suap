# -*- coding: utf-8 -*-
import pandas as pd
from django.test import TestCase
from collections import defaultdict


def tempo_no_setor(dados, setores):
    setor_tempo = []
    for s in setores:
        t = 0
        for d in dados:
            if s == d[0]:
                t += d[1]
        setor_tempo.append([s, t])

    print(setor_tempo)


def calcular_tempo(data_recebimento, data_encaminhamento):
    x = data_recebimento - data_encaminhamento
    return round(x.seconds / 60 / 60, 2)


# from protocolo.models import Tramite
# tramites = Tramite.objects.filter(processo__id=17675)
# dados = []
# setores = set()
# print(type(tramites))
#
# for t in tramites:
#     print(t.data_recebimento)
#     if t.data_recebimento == None:
#         print(tramites.get(ordem=t.ordem),
#               {'x': int(t.data_recebimento.timestamp()) * 1000, 'name': t.orgao_interno_recebimento.nome,
#                'label': t.orgao_interno_recebimento.sigla, 'description': t.observacao_encaminhamento})


# from processo_eletronico.models import Tramite as TramiteEletronico
# tramites = TramiteEletronico.objects.filter(processo__id=867)
#
# for tramite in tramites:
#     print(tramite)

setores = ['CDSS (IFRR)', 'DGP (IFRR)', 'CDS (IFRR)', 'DTI (IFRR)', 'CDS (IFRR)', 'GAB (IFRR)', 'DTI (IFRR)',
           'GAB (IFRR)', 'CDS (IFRR)', 'GAB (IFRR)']
tempos_efetivos = [0.8, 0.14, 0.21, 1.48, 2.55, 5243.13, 240.71, 0.01, 0.02, 0.05]
tempos_handoff = [0.15, 95.12, 0.23, 1.5, 17.79, 42.61, 18.22, 1.51, 126.6, 0]


def get_tempo_em_cada_setor(setores, tempos):
    # Juntar o setor com o seu tempo
    setor_tempo = []
    for i, s in enumerate(setores):
        setor_tempo.append([s, tempos[i]])
    # Agrupa o setor e soma o tempo total dele
    setor_agrupado_tempo = defaultdict(float)
    for setor, tempo in setor_tempo:
        setor_agrupado_tempo[setor] += tempo
    setor_agrupado_tempo = setor_agrupado_tempo.items()
    # Formata os dados para o padrão aceito pelo gráfico
    tempo_em_cada_setor_grafico = []
    for s in setor_agrupado_tempo:
        tempo_em_cada_setor_grafico.append({'name': '{}'.format(s[0]), 'y': round(s[1], 2)})
    return tempo_em_cada_setor_grafico


def gerar_tabela(setores, tempos_efetivos, tempos_handoff):
    setores_obj = {
        'setor': setores,
        'repeticao': setores,
    }
    setores_tempos = {
        'setor': setores,
        'tempo_efetivo': tempos_efetivos,
        'tempo_handoff': tempos_handoff
    }
    repeticoes = pd.DataFrame(setores_obj, ).groupby('setor').count()
    df = pd.DataFrame(setores_tempos, ).groupby('setor').sum()
    tabela = pd.merge(df, repeticoes, how='inner', on='setor')
    tabela['tempo_total'] = (tabela['tempo_efetivo'] + tabela['tempo_handoff'])
    tempo_total = tabela.sum()
    tabela['percent_efetivo'] = (tabela['tempo_efetivo'] / tempo_total.tempo_efetivo) * 100
    tabela['percent_handoff'] = (tabela['tempo_handoff'] / tempo_total.tempo_handoff) * 100
    setor_index = tabela.to_dict(orient='split')['index']
    tabela_dict = tabela.to_dict(orient='records')
    for i, l in enumerate(tabela_dict):
        l['setor'] = setor_index[i]
    return tabela_dict


# setor | qtd repetições | tempo efetivo | tempo até o recebimento
# tempos_efetivos    5489.10
# tempos_handoff      303.7

class TestCaseBasico(TestCase):
    def test(self):
        tabela = gerar_tabela(setores, tempos_efetivos, tempos_handoff)
        print(tabela)

        for t in tabela:
            print(t)
            print('------------------')
