# -*- coding: utf-8 -*-
from collections import defaultdict
import pandas as pd
from datetime import datetime
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404
from django.shortcuts import get_object_or_404
from django.template import loader
from processo_eletronico.models import Processo as ProcessoEletronico
from protocolo.models import Processo


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
    df = pd.DataFrame(setores_tempos,).groupby('setor').sum()
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


def diferenca_datas_em_horas(data_recebimento, data_encaminhamento):
    x = data_recebimento - data_encaminhamento
    tempo_em_horas = round(x.total_seconds() / 60 / 60, 2)
    return tempo_em_horas


def get_dados(request, processo):
    tempo_efetivo_setor_list = []
    handoff_list = []
    setores = list()
    # setores_handoff = []
    timeline = []
    ultima_data = datetime.now()
    finalizado = False
    ultimo_tramite = None
    observacao_finalizacao = ''
    possui_tramites = True

    # Processo Eletrônico
    if processo.tem_vinculo_com_processo_eletronico:
        processo_eletronico = get_object_or_404(ProcessoEletronico,
                                                numero_protocolo=processo.numero_processo_eletronico)
        processo_eletronico.pode_ler(user=request.user, lancar_excecao=True)
        processo_eletronico = ProcessoEletronico.atualizar_status_processo(processo_eletronico)
        status = processo_eletronico.get_status_display()

        tramites = processo_eletronico.tramites.all().reverse()
        primeira_data = processo_eletronico.data_hora_criacao
        if processo_eletronico.data_finalizacao:
            ultima_data = processo_eletronico.data_finalizacao
            finalizado = True
            ultimo_tramite = processo_eletronico.ultimo_tramite
            observacao_finalizacao = processo_eletronico.observacao_finalizacao

    # Processo Físico
    else:
        status = processo.get_status_display()
        tramites = processo.tramite_set.order_by('ordem')
        primeira_data = processo.data_cadastro
        if processo.data_finalizacao:
            ultima_data = processo.data_finalizacao
            finalizado = True
            ultimo_tramite = processo.get_ultimo_tramite()
            observacao_finalizacao = processo.observacao_finalizacao

    if not tramites:
        possui_tramites = False

    data_recebimento = None
    for t in tramites:
        # Usada para salvar a data_recebimento do trâmite anterior
        data_recebimento_anterior = data_recebimento

        # Processo Eletrônico
        if processo.tem_vinculo_com_processo_eletronico:
            setor_que_encaminhou = t.remetente_setor
            setor_que_recebe = t.destinatario_setor
            data_recebimento = t.data_hora_recebimento
            data_encaminhamento = t.data_hora_encaminhamento
            despacho = t.despacho_corpo
        # Processo Físico
        else:
            setor_que_encaminhou = t.orgao_interno_encaminhamento
            setor_que_recebe = t.orgao_interno_recebimento
            data_recebimento = t.data_recebimento
            data_encaminhamento = t.data_encaminhamento
            despacho = t.observacao_encaminhamento

        setor_encaminhamento = '{} ({})'.format(setor_que_encaminhou.sigla, setor_que_encaminhou._get_uo())
        setor_recebimento = '{} ({})'.format(setor_que_recebe.sigla, setor_que_recebe._get_uo())
        setores.append(setor_encaminhamento)

        if t == tramites[0]:  # Se é o primeiro trâmite
            if data_encaminhamento is not None:  # Se foi encaminhado
                # TEMPO EFETIVO NO SETOR
                tempo_efetivo_setor = diferenca_datas_em_horas(data_encaminhamento, primeira_data)
                tempo_efetivo_setor_list.append(tempo_efetivo_setor)
                if data_recebimento is None:
                    tempo_efetivo_setor_list.append(0)
                if finalizado and t == ultimo_tramite:
                    tempo_efetivo_setor = diferenca_datas_em_horas(ultima_data, data_recebimento)
                    tempo_efetivo_setor_list.append(tempo_efetivo_setor)
            else:  # Se não foi encaminhado
                # TEMPO EFETIVO NO SETOR
                tempo_efetivo_setor = diferenca_datas_em_horas(datetime.now(), primeira_data)
                tempo_efetivo_setor_list.append(tempo_efetivo_setor)
        elif finalizado and t == ultimo_tramite:  # Se é o último trâmite
            # TEMPO EFETIVO NO SETOR
            # Adiciona tempo efetivo do penúltimo setor
            tempo_efetivo_setor = diferenca_datas_em_horas(data_encaminhamento, data_recebimento_anterior)
            tempo_efetivo_setor_list.append(tempo_efetivo_setor)
            # Adiciona tempo efetivo do último setor
            tempo_efetivo_setor = diferenca_datas_em_horas(ultima_data, data_recebimento)
            tempo_efetivo_setor_list.append(tempo_efetivo_setor)
        else:  # Se não é o primeiro e nem o último trâmite
            if data_encaminhamento is not None:  # Se foi encaminhado
                # TEMPO EFETIVO
                tempo_efetivo_setor = diferenca_datas_em_horas(data_encaminhamento, data_recebimento_anterior)
                tempo_efetivo_setor_list.append(tempo_efetivo_setor)
                if data_recebimento is None:
                    tempo_efetivo_setor_list.append(0)
            else:  # Se não foi encaminhado
                # TEMPO EFETIVO
                tempo_efetivo_setor = diferenca_datas_em_horas(datetime.now(), data_recebimento_anterior)
                tempo_efetivo_setor_list.append(tempo_efetivo_setor)

        # Foi recebido
        if data_recebimento is not None:
            handoff = diferenca_datas_em_horas(data_recebimento, data_encaminhamento)
            handoff_list.append(handoff)
            # setores_handoff.append([setor_que_encaminhou, handoff])
            timeline.append(
                {'x': int(data_encaminhamento.timestamp()) * 1000, 'name': setor_que_encaminhou.nome,
                 'label': setor_encaminhamento, 'description': despacho or ''})
        # Não foi recebido
        else:
            setores.append(setor_recebimento)
            handoff_list.append(diferenca_datas_em_horas(datetime.now(), data_encaminhamento))
            handoff_list.append(0)
            # setores_handoff.append([setor_que_encaminhou, handoff])
            # setores_handoff.append([setor_que_recebe, 0])
            timeline.append(
                {'x': int(data_encaminhamento.timestamp()) * 1000, 'name': setor_que_encaminhou.nome,
                 'label': setor_encaminhamento, 'description': despacho or ''})
            timeline.append(
                {'x': int(datetime.now().timestamp()) * 1000, 'name': setor_que_recebe.nome,
                 'label': setor_recebimento, 'description': ''})

        if finalizado and t == ultimo_tramite:
            setores.append(setor_recebimento)  #
            handoff_list.append(0)
            # setores_handoff.append([setor_que_recebe, 0])
            timeline.append(
                {'x': int(data_recebimento.timestamp()) * 1000, 'name': setor_que_recebe.nome,
                 'label': setor_recebimento, 'description': observacao_finalizacao or ''})

    tempo_total_dias = round((ultima_data - primeira_data).total_seconds() / 60 / 60 / 24, 2)
    tempo_total_horas = round((ultima_data - primeira_data).total_seconds() / 60 / 60, 2)
    tempo_efetivo_total_no_setor = get_tempo_em_cada_setor(setores, tempo_efetivo_setor_list)
    tabela = gerar_tabela(setores, tempo_efetivo_setor_list, handoff_list)

    dados = {
        'tempo_efetivo_setor_list': tempo_efetivo_setor_list,
        'handoff_list': handoff_list,
        'setores': setores,
        'tempo_efetivo_total_no_setor': tempo_efetivo_total_no_setor,
        'tabela': tabela,
        'timeline': timeline,
        'tempo_total_horas': tempo_total_horas,
        'tempo_total_dias': tempo_total_dias,
        'status': status,
        'possui_tramites': possui_tramites
    }
    return dados


@login_required
def processmining(request, tipo, pk):
    template = loader.get_template('processmining/index.html')
    if tipo == 'fisico':
        processo = get_object_or_404(Processo, pk=pk)
    elif tipo == 'eletronico':
        pe = get_object_or_404(ProcessoEletronico, pk=pk)
        processo = get_object_or_404(Processo, numero_processo=pe.numero_protocolo_fisico)
    else:
        raise Http404("Página não encontrada!")
    dados = get_dados(request, processo)
    context = {
        'processo': processo,
        'status': dados.get('status'),
        'tempo_efetivo_setor_list': dados.get('tempo_efetivo_setor_list'),
        'handoff_list': dados.get('handoff_list'),
        'setores': dados.get('setores'),
        'tempo_efetivo_total_no_setor': dados.get('tempo_efetivo_total_no_setor'),
        'tabela': dados.get('tabela'),
        'timeline': dados.get('timeline'),
        'tempo_total_dias': dados.get('tempo_total_dias'),
        'possui_tramites': dados.get('possui_tramites'),
        'mensagem': 'O Processo não possui trâmites!' if not dados.get('possui_tramites') else ''
    }
    return HttpResponse(template.render(context, request))
