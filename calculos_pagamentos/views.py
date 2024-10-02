# -*- coding: utf-8 -*-
import calendar
import os
from datetime import date

from dateutil.relativedelta import relativedelta
from django.apps.registry import apps
from django.contrib.auth.decorators import permission_required
from django.db.models.aggregates import Sum
from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt

from calculos_pagamentos.forms import (
    ArquivoPagamentoForm,
    vencimento_tae_proporcional_a_ch_do_cargo,
    calcula_vencimento_mensal,
    calcula_rt_mensal,
    UploadArquivoForm,
    InformarIRPFForm,
)
from calculos_pagamentos.models import (
    Calculo,
    NivelVencimentoTAEPorClasseEPadrao,
    NivelVencimento,
    CalculoInsalubridade,
    CalculoRT,
    CalculoIQ,
    CalculoMudancaRegime,
    CalculoPermanencia,
    CalculoNomeacaoCD,
    CalculoExoneracaoCD,
    CalculoDesignacaoFG,
    CalculoDispensaFG,
    CalculoSubstituicao,
    DetalhamentoSubstituicao,
    CalculoTerminoContratoInterpLibras,
    getClasseCalculo,
    CalculoProgressao,
    CalculoPericulosidade,
    CalculoRSC,
)
from calculos_pagamentos.models.pagamentos import Pagamento, ConfigPagamento, ArquivoPagamento, LinhaPagamento
from comum.models import FuncaoCodigo
from comum.utils import respond_as_attachment
from djtools.utils import rtr, httprr
from rh.models import Servidor


@rtr()
@permission_required('rh.eh_servidor')
def calculos(request):
    title = 'Lista de Cálculos de Pagamento'
    title_box = 'Escolha um tipo de Cálculo de Pagamento'
    link_prefix = '/admin/calculos_pagamentos/'

    # Todos os calculos
    # lista_calculos = [CalculoSubstituicao, CalculoProgressao, CalculoPericulosidade, CalculoInsalubridade,
    #                  CalculoRT, CalculoRSC, CalculoIQ, CalculoMudancaRegime, CalculoTransporte, CalculoPermanencia,
    #                  CalculoNomeacaoCD, CalculoExoneracaoCD, CalculoDesignacaoFG, CalculoDispensaFG,
    #                  CalculoTerminoContratoProfSubs, CalculoTerminoContratoInterpLibras]

    # Apenas calculos da primeira versao
    lista_calculos = [
        CalculoSubstituicao,
        CalculoProgressao,
        CalculoPericulosidade,
        CalculoInsalubridade,
        CalculoRT,
        CalculoRSC,
        CalculoIQ,
        CalculoMudancaRegime,
        CalculoPermanencia,
        CalculoNomeacaoCD,
        CalculoExoneracaoCD,
        CalculoDesignacaoFG,
        CalculoDispensaFG,
        CalculoTerminoContratoInterpLibras,
    ]

    for calculo in lista_calculos[:]:
        if not request.user.has_perm(calculo._meta.label_lower.replace(".", ".change_")):
            lista_calculos.remove(calculo)
    return locals()


# IFMA/Leonardo - Novembro/2017 - Transformar Calculo em Documento Eletrônico
"""
@rtr()
@login_required
def gerar_documentocalculosubstituicao(request, pk):
    pagamento = get_object_or_404(CalculoSubstituicao, pk=pk)
    documento_novo = pagamento.gerar_documento_eletronico()

    return httprr('/documento_eletronico/visualizar_documento/%s/' % documento_novo.id, 'Documento Gerado com sucesso.')
"""

# IFMA Leonardo FIM


# IFMA/Tássio: Método chamado pelo javascript do campo de servidor do formulário CalculoForm
@csrf_exempt
def get_valores(request):
    servidor_id = request.POST.get('id', None)
    data = {'vencimento': None, 'jornada': None, 'titulacao': None, 'nivel_string': None, 'padrao': None, 'funcao': None, 'campus': None}
    if Servidor.objects.filter(pk=servidor_id or 0).exists():
        servidor = Servidor.objects.get(id=servidor_id)

        if servidor.eh_tecnico_administrativo:
            try:
                nivel = NivelVencimentoTAEPorClasseEPadrao.objects.get(cargo_classe=servidor.cargo_classe, nivel_padrao=servidor.nivel_padrao).nivel
            except Exception:
                nivel = None
            nivel_string = "P"
        elif servidor.eh_docente:
            if servidor.cargo_emprego.codigo == '705001':  # Magistério Superior
                nivel = NivelVencimento.objects.get(categoria='docente', codigo__contains='-' + servidor.nivel_padrao)
                nivel_string = "-"
            else:  # Magistério Médio e Técnico
                nivel = NivelVencimento.objects.get(categoria='docente', codigo__contains='D' + servidor.nivel_padrao)
                nivel_string = "D"
        jornada = servidor.jornada_trabalho
        titulacao = servidor.titulacao

        if nivel:
            data['vencimento'] = nivel.id
        if jornada:
            data['jornada'] = jornada.id
        if titulacao:
            data['titulacao'] = titulacao.id
        if nivel_string:
            data['nivel_string'] = nivel_string
        if servidor.eh_tecnico_administrativo and servidor.nivel_padrao:
            data['padrao'] = servidor.nivel_padrao

        # Cálculo de Substituição
        if servidor.funcao and servidor.funcao_codigo:
            funcao = FuncaoCodigo.objects.filter(nome__unaccent__icontains=servidor.funcao.codigo).filter(nome__unaccent__icontains=servidor.funcao_codigo)
            if funcao:
                data['funcao'] = funcao[0].id
        if servidor.setor:
            data['campus'] = servidor.setor.uo.id

    return JsonResponse(data)


# IFMA/Tássio - View geral para cálculos
def calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias, relatorio=False):

    Calculo = apps.get_model(str_calculo)
    Detalhamento = apps.get_model(str_detalhamento)
    Ferias = apps.get_model(str_ferias) if str_ferias else None
    Periodo = apps.get_model(str_periodo)

    calculo = get_object_or_404(Calculo, pk=pk)
    tipo_calculo = str_calculo[str_calculo.rfind('.') + 1:].lower()
    tipo_periodo = str_periodo[str_periodo.rfind('.') + 1:].lower()
    title = calculo.__unicode__()
    if relatorio:
        title = 'Relatório Detalhado - ' + title
    exoneracao_ou_dispensa = "Exoneração" in title or "Dispensa" in title

    periodos = Periodo.objects.filter(calculo__pk=pk)
    detalhamentos = Detalhamento.objects.filter(periodo__calculo__pk=pk)
    # Para cálculo de acerto de término de contrato
    if "Término" in title:
        detalhamentos_alim = calculo.get_detalhamento_alim_model().objects.filter(periodo__calculo__pk=pk)

    num_col_total = 1
    if hasattr(calculo, 'total_venc') and detalhamentos[0].valor_venc != 0:
        num_col_total += 1
    if hasattr(calculo, 'total_rt') and calculo.total_rt != 0:
        num_col_total += 1
    if hasattr(calculo, 'total_anuenio') and calculo.total_anuenio != 0:
        num_col_total += 1
    if hasattr(calculo, 'total_per') and calculo.total_per != 0:
        num_col_total += 1
    if hasattr(calculo, 'total_ins') and calculo.total_ins != 0:
        num_col_total += 1
    if hasattr(calculo, 'total_iq') and calculo.total_iq != 0:
        num_col_total += 1
    if hasattr(calculo, 'total_aux') and calculo.total_aux != 0:
        num_col_total += 1
    if hasattr(calculo, 'total_abono') and calculo.total_abono != 0:
        num_col_total += 1
    if hasattr(calculo, 'total_grat') and detalhamentos[0].valor_grat != 0:
        num_col_total += 1
    if hasattr(calculo, 'total_gadf') and detalhamentos[0].valor_gadf != 0:
        num_col_total += 1
    if hasattr(calculo, 'total_age') and detalhamentos[0].valor_age != 0:
        num_col_total += 1

    anos = [data.year for data in detalhamentos.dates('data_inicio', 'year')]
    anos_detalhamentos = []
    consolidacao = 0

    for ano in anos:
        ano_detalhamentos = {
            'detalhamentos': None,
            'total_venc': 0,
            'total_rt': 0,
            'total_anuenio': 0,
            'total_per': 0,
            'total_ins': 0,
            'total_iq': 0,
            'total_aux': 0,
            'total_abono': 0,
            'total_grat': 0,
            'total_gadf': 0,
            'total_age': 0,
            'total': 0,
            'ano': ano,
            'ferias': None,
        }
        qs = detalhamentos.filter(data_inicio__year=ano)
        ano_detalhamentos['detalhamentos'] = qs
        if relatorio:
            for detalhamento in ano_detalhamentos['detalhamentos']:
                vencimento_mensal_recebido = calcula_vencimento_mensal(
                    detalhamento.data_inicio, detalhamento.data_fim, detalhamento.periodo.nivel_passado, detalhamento.periodo.jornada_passada
                )
                vencimento_mensal_devido = calcula_vencimento_mensal(detalhamento.data_inicio, detalhamento.data_fim, detalhamento.periodo.nivel, detalhamento.periodo.jornada)
                if calculo.servidor.eh_tecnico_administrativo:
                    vencimento_mensal_recebido = vencimento_tae_proporcional_a_ch_do_cargo(vencimento_mensal_recebido, detalhamento.periodo.jornada_passada, calculo.servidor)
                    vencimento_mensal_devido = vencimento_tae_proporcional_a_ch_do_cargo(vencimento_mensal_devido, detalhamento.periodo.jornada, calculo.servidor)
                rt_mensal_recebida = (
                    calcula_rt_mensal(
                        detalhamento.data_inicio,
                        detalhamento.data_fim,
                        detalhamento.periodo.nivel_passado,
                        detalhamento.periodo.jornada_passada,
                        detalhamento.periodo.titulacao_passada,
                    )
                    if detalhamento.periodo.titulacao_passada
                    else 0
                )
                rt_mensal_devida = (
                    calcula_rt_mensal(
                        detalhamento.data_inicio, detalhamento.data_fim, detalhamento.periodo.nivel, detalhamento.periodo.jornada, detalhamento.periodo.titulacao_nova
                    )
                    if detalhamento.periodo.titulacao_nova
                    else 0
                )

                if detalhamento.gratificacao and ano < calculo.data_criacao.year:
                    vencimento_mensal_devido *= 2
                    vencimento_mensal_recebido *= 2
                    rt_mensal_devida *= 2
                    rt_mensal_recebida *= 2
                detalhamento.valor_venc_devido = vencimento_mensal_devido
                detalhamento.valor_venc_recebido = vencimento_mensal_recebido
                detalhamento.valor_rt_devido = rt_mensal_devida
                detalhamento.valor_rt_recebido = rt_mensal_recebida
        if hasattr(qs[0], 'valor_venc'):
            ano_detalhamentos['total_venc'] = qs.aggregate(Sum('valor_venc'))['valor_venc__sum'] or 0
        if hasattr(qs[0], 'valor_rt'):
            ano_detalhamentos['total_rt'] = qs.aggregate(Sum('valor_rt'))['valor_rt__sum'] or 0
        if hasattr(qs[0], 'valor_anuenio'):
            ano_detalhamentos['total_anuenio'] = qs.aggregate(Sum('valor_anuenio'))['valor_anuenio__sum'] or 0
        if hasattr(qs[0], 'valor_per'):
            ano_detalhamentos['total_per'] = qs.aggregate(Sum('valor_per'))['valor_per__sum'] or 0
        if hasattr(qs[0], 'valor_ins'):
            ano_detalhamentos['total_ins'] = qs.aggregate(Sum('valor_ins'))['valor_ins__sum'] or 0
        if hasattr(qs[0], 'valor_iq'):
            ano_detalhamentos['total_iq'] = qs.aggregate(Sum('valor_iq'))['valor_iq__sum'] or 0
        if hasattr(qs[0], 'valor_aux'):
            ano_detalhamentos['total_aux'] = qs.aggregate(Sum('valor_aux'))['valor_aux__sum'] or 0
        if hasattr(qs[0], 'valor_abono'):
            ano_detalhamentos['total_abono'] = qs.aggregate(Sum('valor_abono'))['valor_abono__sum'] or 0
        if hasattr(qs[0], 'valor_grat'):
            ano_detalhamentos['total_grat'] = qs.aggregate(Sum('valor_grat'))['valor_grat__sum'] or 0
        if hasattr(qs[0], 'valor_gadf'):
            ano_detalhamentos['total_gadf'] = qs.aggregate(Sum('valor_gadf'))['valor_gadf__sum'] or 0
        if hasattr(qs[0], 'valor_age'):
            ano_detalhamentos['total_age'] = qs.aggregate(Sum('valor_age'))['valor_age__sum'] or 0
        if Ferias:
            ferias = Ferias.objects.filter(periodo__calculo__pk=pk, data_inicio__year=ano)

            if ferias.exists():
                ano_detalhamentos['ferias'] = ferias
                if relatorio:
                    for f in ano_detalhamentos['ferias']:
                        if f.data_inicio < f.periodo.data_inicio:
                            data_inicio_mes = f.periodo.data_inicio
                        else:
                            data_inicio_mes = f.data_inicio
                        data_fim_mes = data_inicio_mes.replace(day=calendar.monthrange(data_inicio_mes.year, data_inicio_mes.month)[1])

                        if (
                            data_fim_mes.day > 30 and data_inicio_mes.day <= 30
                        ):  # Não é considerado o dia 31 no cálculo de progressão da DIGEPE do IFMA. Somente se o periodo começar em dia 31.
                            data_fim_mes = data_fim_mes.replace(day=30)
                        if f.periodo.data_fim < data_fim_mes:
                            data_fim_mes = f.periodo.data_fim

                        vencimento_mensal_recebido = calcula_vencimento_mensal(data_inicio_mes, data_fim_mes, f.periodo.nivel_passado, f.periodo.jornada_passada)
                        vencimento_mensal_devido = calcula_vencimento_mensal(data_inicio_mes, data_fim_mes, f.periodo.nivel, f.periodo.jornada)
                        if calculo.servidor.eh_tecnico_administrativo:
                            vencimento_mensal_recebido = vencimento_tae_proporcional_a_ch_do_cargo(vencimento_mensal_recebido, f.periodo.jornada_passada, calculo.servidor)
                            vencimento_mensal_devido = vencimento_tae_proporcional_a_ch_do_cargo(vencimento_mensal_devido, f.periodo.jornada, calculo.servidor)
                        rt_mensal_recebida = (
                            calcula_rt_mensal(data_inicio_mes, data_fim_mes, f.periodo.nivel_passado, f.periodo.jornada_passada, f.periodo.titulacao_passada)
                            if f.periodo.titulacao_passada
                            else 0
                        )
                        rt_mensal_devida = (
                            calcula_rt_mensal(data_inicio_mes, data_fim_mes, f.periodo.nivel, f.periodo.jornada, f.periodo.titulacao_nova) if f.periodo.titulacao_nova else 0
                        )

                        if calculo.servidor.eh_tecnico_administrativo:
                            x = 3
                        elif calculo.servidor.eh_docente:
                            x = 2
                        vencimento_ferias_devido = round(vencimento_mensal_devido / x, 2)
                        vencimento_ferias_recebido = round(vencimento_mensal_recebido / x, 2)
                        rt_ferias_devida = round(rt_mensal_devida / x, 2)
                        rt_ferias_recebida = round(rt_mensal_recebida / x, 2)

                        f.valor_venc_devido = vencimento_ferias_devido
                        f.valor_venc_recebido = vencimento_ferias_recebido
                        f.valor_rt_devido = rt_ferias_devida
                        f.valor_rt_recebido = rt_ferias_recebida
            for f in ferias:
                if ano < calculo.data_criacao.year:
                    if hasattr(f, 'valor_venc'):
                        ano_detalhamentos['total_venc'] += f.valor_venc or 0
                    if hasattr(f, 'valor_rt'):
                        ano_detalhamentos['total_rt'] += f.valor_rt or 0
                    if hasattr(f, 'valor_anuenio'):
                        ano_detalhamentos['total_anuenio'] += f.valor_anuenio or 0
                    if hasattr(f, 'valor_per'):
                        ano_detalhamentos['total_per'] += f.valor_per or 0
                    if hasattr(f, 'valor_ins'):
                        ano_detalhamentos['total_ins'] += f.valor_ins or 0
                    if hasattr(f, 'valor_iq'):
                        ano_detalhamentos['total_iq'] += f.valor_iq or 0
                    if hasattr(f, 'valor_grat'):
                        ano_detalhamentos['total_grat'] += f.valor_grat or 0
                    if hasattr(f, 'valor_gadf'):
                        ano_detalhamentos['total_gadf'] += f.valor_gadf or 0
                    if hasattr(f, 'valor_age'):
                        ano_detalhamentos['total_age'] += f.valor_age or 0
                    # Em anos anteriores, adicionar férias no detalhamento do mês de usufruto/Pedido DCLP
                    for det in ano_detalhamentos['detalhamentos']:
                        if det.data_inicio.month == f.data_inicio.month and det.periodo == f.periodo:  # Tenho q usar esse if pq ñ posso fazer + filter
                            if hasattr(f, 'valor_venc'):
                                det.valor_venc += f.valor_venc or 0
                            if hasattr(f, 'valor_rt'):
                                det.valor_rt += f.valor_rt or 0
                            if hasattr(f, 'valor_anuenio'):
                                det.valor_anuenio += f.valor_anuenio or 0
                            if hasattr(f, 'valor_per'):
                                det.valor_per += f.valor_per or 0
                            if hasattr(f, 'valor_ins'):
                                det.valor_ins += f.valor_ins or 0
                            if hasattr(f, 'valor_iq'):
                                det.valor_iq += f.valor_iq or 0
                            if hasattr(f, 'valor_grat'):
                                det.valor_grat += f.valor_grat or 0
                            if hasattr(f, 'valor_gadf'):
                                det.valor_gadf += f.valor_gadf or 0
                            if hasattr(f, 'valor_age'):
                                det.valor_age += f.valor_age or 0
                            det.total += f.total
                            det.tem_ferias = f.ano_referencia

        # Correção, pois valores de vencimento desses cálculos abaixo não entram na conta.
        if "CalculoPericulosidade" in str_calculo or 'CalculoInsalubridade' in str_calculo:
            ano_detalhamentos['total_venc'] = 0
        ano_detalhamentos['total'] = (
            ano_detalhamentos['total_venc']
            + ano_detalhamentos['total_rt']
            + ano_detalhamentos['total_anuenio']
            + ano_detalhamentos['total_per']
            + ano_detalhamentos['total_ins']
            + ano_detalhamentos['total_iq']
            + ano_detalhamentos['total_aux']
            + ano_detalhamentos['total_abono']
            + ano_detalhamentos['total_grat']
            + ano_detalhamentos['total_gadf']
            + ano_detalhamentos['total_age']
        )
        anos_detalhamentos.append(ano_detalhamentos)

        if ano < calculo.data_criacao.year:
            consolidacao += ano_detalhamentos['total']
    return locals()


@rtr()
@permission_required('rh.eh_servidor')
def calculosubstituicao(request, pk):
    # ===================================
    # Visualiza os dados do pagamento e exibe as opcoes de operacao
    # ===================================

    calculo = get_object_or_404(CalculoSubstituicao, pk=pk)
    title = calculo.__unicode__()

    detalhamentos = DetalhamentoSubstituicao.objects.filter(periodo__calculo=calculo, gratificacao=False)
    gratificacoes = DetalhamentoSubstituicao.objects.filter(periodo__calculo=calculo, gratificacao=True)

    consolidacao = 0
    anos = [data.year for data in detalhamentos.dates('data_inicio', 'year')]
    anos_detalhamentos = []
    for ano in anos:
        ano_detalhamentos = {'total_grat': None, 'ano': ano}
        qs = detalhamentos.filter(data_inicio__year=ano) | gratificacoes.filter(data_inicio__year=ano)
        ano_detalhamentos['total_grat'] = qs.aggregate(Sum('valor_grat'))['valor_grat__sum']
        anos_detalhamentos.append(ano_detalhamentos)

        if ano < calculo.data_criacao.year:
            consolidacao += ano_detalhamentos['total_grat']

    simultaneidade = False
    simul_ids = []
    for periodo in calculo.periodosubstituicao_set.all():
        qs = CalculoSubstituicao.objects.filter(
            servidor=calculo.servidor, periodosubstituicao__data_inicio__lte=periodo.data_inicio, periodosubstituicao__data_fim__gte=periodo.data_inicio
        ).exclude(pk=calculo.pk)
        if qs.exists():
            simultaneidade = True
            for id in qs.values_list("id", flat=True):
                simul_ids.append(id)
        qs = CalculoSubstituicao.objects.filter(
            servidor=calculo.servidor, periodosubstituicao__data_inicio__lte=periodo.data_fim, periodosubstituicao__data_fim__gte=periodo.data_fim
        ).exclude(pk=calculo.pk)
        if qs.exists():
            simultaneidade = True
            for id in qs.values_list("id", flat=True):
                simul_ids.append(id)

    simul_ids = list(set(simul_ids))

    return locals()


# IFMA/Tássio: Visualização de um Cálculo de Pagamento por Progressão
@rtr()
@permission_required('rh.eh_servidor')
def calculoprogressao(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoProgressao'
    str_periodo = 'calculos_pagamentos.PeriodoCalculoProgressao'
    str_detalhamento = 'calculos_pagamentos.DetalhamentoProgressao'
    str_ferias = 'calculos_pagamentos.FeriasCalculoProgressao'
    return calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias)


# IFMA/Tássio: Visualização de um Cálculo de Pagamento por Periculosidade
@rtr()
@permission_required('rh.eh_servidor')
def calculopericulosidade(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoPericulosidade'
    str_periodo = 'calculos_pagamentos.PeriodoPericulosidade'
    str_detalhamento = 'calculos_pagamentos.DetalhamentoPericulosidade'
    str_ferias = 'calculos_pagamentos.FeriasPericulosidade'
    return calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias)


# IFMA/Tássio: Visualização de um Cálculo de Pagamento por Insalubridade
@rtr()
@permission_required('rh.eh_servidor')
def calculoinsalubridade(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoInsalubridade'
    str_periodo = 'calculos_pagamentos.PeriodoInsalubridade'
    str_detalhamento = 'calculos_pagamentos.DetalhamentoInsalubridade'
    str_ferias = 'calculos_pagamentos.FeriasInsalubridade'
    return calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias)


# IFMA/Tássio: Visualização de um Cálculo de Pagamento de RT
@rtr()
@permission_required('rh.eh_servidor')
def calculort(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoRT'
    str_periodo = 'calculos_pagamentos.PeriodoRT'
    str_detalhamento = 'calculos_pagamentos.DetalhamentoRT'
    str_ferias = 'calculos_pagamentos.FeriasRT'
    return calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias)


# IFMA/Tássio: Visualização de um Cálculo de Pagamento de RSC
@rtr("calculort.html")
@permission_required('rh.eh_servidor')
def calculorsc(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoRSC'
    str_periodo = 'calculos_pagamentos.PeriodoRSC'
    str_detalhamento = 'calculos_pagamentos.DetalhamentoRSC'
    str_ferias = 'calculos_pagamentos.FeriasRSC'
    return calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias)


# IFMA/Tássio: Visualização de um Cálculo de Pagamento de IQ
@rtr()
@permission_required('rh.eh_servidor')
def calculoiq(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoIQ'
    str_periodo = 'calculos_pagamentos.PeriodoIQ'
    str_detalhamento = 'calculos_pagamentos.DetalhamentoIQ'
    str_ferias = 'calculos_pagamentos.FeriasIQ'
    return calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias)


# IFMA/Tássio: Visualização de um Cálculo de Pagamento por Mudança de Regime
@rtr()
@permission_required('rh.eh_servidor')
def calculomudancaregime(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoMudancaRegime'
    str_periodo = 'calculos_pagamentos.PeriodoMudancaRegime'
    str_detalhamento = 'calculos_pagamentos.DetalhamentoMudancaRegime'
    str_ferias = 'calculos_pagamentos.FeriasMudancaRegime'
    return calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias)


# IFMA/Tássio: Visualização de um Cálculo de Pagamento de Auxílio Transporte
@rtr()
@permission_required('rh.eh_servidor')
def calculotransporte(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoTransporte'
    str_periodo = 'calculos_pagamentos.PeriodoTransporte'
    str_detalhamento = 'calculos_pagamentos.DetalhamentoTransporte'
    str_ferias = None
    return calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias)


# IFMA/Tássio: Visualização de um Cálculo de Pagamento de Abono de Permanência
@rtr()
@permission_required('rh.eh_servidor')
def calculopermanencia(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoPermanencia'
    str_periodo = 'calculos_pagamentos.PeriodoPermanencia'
    str_detalhamento = 'calculos_pagamentos.DetalhamentoPermanencia'
    str_ferias = None
    return calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias)


def calculo_fgs_cds_(pk, str_calculo):
    str_periodo = 'calculos_pagamentos.PeriodoFGsCDs'
    str_detalhamento = 'calculos_pagamentos.DetalhamentoFGsCDs'
    str_ferias = 'calculos_pagamentos.FeriasFGsCDs'
    return calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias)


@rtr('calculofgscds.html')
@permission_required('rh.eh_servidor')
def calculonomeacaocd(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoNomeacaoCD'
    return calculo_fgs_cds_(pk, str_calculo)


@rtr('calculofgscds.html')
@permission_required('rh.eh_servidor')
def calculoexoneracaocd(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoExoneracaoCD'
    return calculo_fgs_cds_(pk, str_calculo)


@rtr('calculofgscds.html')
@permission_required('rh.eh_servidor')
def calculodesignacaofg(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoDesignacaoFG'
    return calculo_fgs_cds_(pk, str_calculo)


@rtr('calculofgscds.html')
@permission_required('rh.eh_servidor')
def calculodispensafg(request, pk):
    str_calculo = 'calculos_pagamentos.CalculoDispensaFG'
    return calculo_fgs_cds_(pk, str_calculo)


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def criar_pagamento_substituicao(request, pk):
    calculo = get_object_or_404(CalculoSubstituicao, pk=pk)
    configuracao = None
    try:
        configuracao = ConfigPagamento.objects.get(tipo_calculo=calculo.tipo)
    except Exception:
        return httprr(calculo.get_absolute_url(), message='Não existe configuração de pagamento para este cálculo. ', tag='error')

    hoje = date.today()
    data_inicio = calculo.get_data_inicio()
    data_fim = calculo.get_data_fim()
    # Se o cálculo terminar em anos passados, e for antes do ano passado, ou ano passado antes de dezembro.
    if data_fim.year < hoje.year:
        if hoje.month > 1 or data_fim.month < 12 or hoje.year - data_fim.year > 1 or (data_fim.year == data_inicio.year and data_inicio.month < data_fim.month):
            return httprr(calculo.get_absolute_url(), 'Este cálculo é todo referente a anos passados e não pode ser ' 'enviado ao módulo Pagamento.', tag='warning')
    elif data_inicio.year < hoje.year and (hoje.month > 1 or data_inicio.month < 12 or hoje.year - data_inicio.year > 1):
        return httprr(calculo.get_absolute_url(), 'Este cálculo é parcialmente referente a anos passados e não pode ' 'ser enviado ao módulo Pagamento.', tag='warning')
    if data_inicio.replace(day=1) < hoje.replace(day=1):
        if data_fim.replace(day=1) < hoje.replace(day=1):
            mes_fim = data_fim
        else:
            mes_fim = hoje.replace(day=1) + relativedelta(days=-1)
        pagamento = Pagamento(calculo=calculo, configuracao=configuracao, situacao=1, mes_inicio=data_inicio, mes_fim=mes_fim)
        pagamento.save()
    mes_atual_ou_futuro = hoje
    while mes_atual_ou_futuro.replace(day=1) <= data_fim.replace(day=1):
        pagamento = Pagamento(calculo=calculo, configuracao=configuracao, situacao=1, mes_inicio=mes_atual_ou_futuro, mes_fim=mes_atual_ou_futuro)
        pagamento.save()
        mes_atual_ou_futuro = mes_atual_ou_futuro.replace(day=1) + relativedelta(months=+1)

    return httprr(calculo.get_absolute_url(), 'Cálculo enviado ao módulo Pagamento como Não Processado.')


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def pagamento(request, pk):
    pag = get_object_or_404(Pagamento, pk=pk)
    title = pag.__unicode__()
    return locals()


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def gerar_arquivo_nao_processados(request):
    if request.GET.get('ids') is not None:
        ids = request.GET.get('ids')
        if not ids:  # Este caso ocorre antes do formulário ser carregado.
            return httprr(request.META.get('HTTP_REFERER', '.'), 'Não foram encontrados pagamentos não processados, por isso ' 'não foi gerado um arquivo de pagamento.', tag='error')
        title = "Informar Dados do Novo Arquivo de Pagamento"
        pos_url = '/admin/calculos_pagamentos/pagamento' if len(ids.split(',')) > 1 else Pagamento.objects.get(id=ids).get_absolute_url()
        form = ArquivoPagamentoForm(request.GET.get('mes') is not None and request.GET or None, request=request, initial={'ids': ids, 'pos_url': pos_url})
        if form.is_valid():
            ids = form.cleaned_data['ids'].split(',')
            arquivo = ArquivoPagamento()
            pagamentos_incluidos = arquivo.gerar_arquivo(mes=form.cleaned_data['mes'], ano=form.cleaned_data['ano'], pagamentos=Pagamento.objects.filter(id__in=ids, situacao=1))
            if pagamentos_incluidos:
                arquivo.save()
                for pag in pagamentos_incluidos:
                    pag.arquivo = arquivo
                    pag.situacao = 2  # Processado
                    pag.save()
                return respond_as_attachment(arquivo.file_path, os.path.split(arquivo.file_path)[1])
            # Normalmente só chega até aqui se todos os pagamentos não-processados não são dos meses anteriores.
            return httprr(
                pos_url,
                tag='error',
                message='Não foram encontrados pagamentos não processados anteriores a {}/{} para gerar o ' 'arquivo.'.format(form.cleaned_data['mes'], form.cleaned_data['ano']),
            )
        return locals()
    return httprr('..', 'Não há IDs.', tag='error')  # Teoricamente, não deve chegar aqui


# IFMA/Tássio: Relatório Detalhado com valores devidos, recebidos e diferença.
@permission_required('rh.eh_servidor')
def relatorio_detalhado(request, pk):
    c = Calculo.objects.get(pk=pk).get_calculo_espeficico()
    if 'CalculoProgressao' in str(type(c)):
        return relatorio_detalhado_progressao(pk)
    else:
        return 'Tipo de cálculo sem relatório detalhado.'


# IFMA/Tássio: Relatório Detalhado com valores devidos, recebidos e diferença.
@rtr()
def relatorio_detalhado_progressao(pk):
    str_calculo = 'calculos_pagamentos.CalculoProgressao'
    str_periodo = 'calculos_pagamentos.PeriodoCalculoProgressao'
    str_detalhamento = 'calculos_pagamentos.DetalhamentoProgressao'
    str_ferias = 'calculos_pagamentos.FeriasCalculoProgressao'
    return calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias, True)


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def arquivo_aceitos(request):
    return view_arquivo_de_retorno(request, "aceitos")


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def arquivo_rejeitados(request):
    return view_arquivo_de_retorno(request, "rejeitados")


def view_arquivo_de_retorno(request, tipo):
    title = "Upload de Arquivo de Pagamentos {}".format(tipo.title())
    form = UploadArquivoForm(request.POST or None, request.POST and request.FILES or None)
    if form.is_valid():
        arquivo = form.files['arquivo']
        msg = processar_arquivo(arquivo, tipo)
        return httprr('/admin/calculos_pagamentos/pagamento', msg)
    return locals()


def processar_arquivo(arquivo, tipo):
    quant_aceitos = 0
    quant_aceitos_parcial = 0
    quant_nao_aceitos = 0
    arquivos_pag = None
    linhas_processadas = []
    for line in arquivo.read().splitlines():
        if line.startswith('0'):
            mes_arq = line[38:40]
            ano_arq = line[40:44]
            arquivos_pag = ArquivoPagamento.objects.filter(mes=mes_arq, ano=ano_arq)
        if line.startswith('1'):
            servidor_matricula = line[6:13].lstrip("0")  # Retira "0" do início da string
            mes_pag = line[193:195]
            ano_pag = line[196:200]
            rubrica = line[87:92]
            rend_desc = line[92:93]
            seq = line[93:94]
            valor = line[94:106].replace('.', '').replace(',', '').replace(' ', '').zfill(11)
            servidor = Servidor.objects.get(matricula=servidor_matricula)
            linha = LinhaPagamento.objects.filter(
                ano=ano_pag, mes=mes_pag, rend_desc=rend_desc, rubrica=rubrica, sequencia=seq, valor=valor, pagamentos__calculo__servidor=servidor
            ).distinct()
            if linha.count() > 1:
                return 'Erro: Mais de uma linha com os valores: servidor={}, mes={}, ano={}, rend_desc={}, rubrica={},' 'sequencia={}, valor={}'.format(
                    servidor, mes_pag, ano_pag, rend_desc, rubrica, seq, valor
                )
            if linha.exists():
                linhas_processadas.append(linha[0])

    for arquivo_pag in arquivos_pag:
        for pagamento in arquivo_pag.pagamentos.all():
            quant_linhas_processadas = 0
            for linha in pagamento.linhas.all():
                if linha in linhas_processadas:
                    quant_linhas_processadas += 1
                    if tipo == 'aceitos':
                        linha.situacao = 1
                        linha.save()
                    elif tipo == 'rejeitados':
                        linha.situacao = 2
                        linha.save()
            if tipo == 'aceitos':
                if 0 < quant_linhas_processadas < pagamento.linhas.all().count():
                    quant_aceitos_parcial += 1
                    pagamento.situacao = 6  # Aceito Parcialmente
                elif quant_linhas_processadas == pagamento.linhas.all().count():
                    quant_aceitos += 1
                    pagamento.situacao = 3  # Aceito
            elif tipo == 'rejeitados':
                if 0 < quant_linhas_processadas < pagamento.linhas.all().count():
                    quant_aceitos_parcial += 1
                    pagamento.situacao = 6  # Aceito Parcialmente
                elif quant_linhas_processadas == pagamento.linhas.all().count():
                    quant_nao_aceitos += 1
                    pagamento.situacao = 4  # Rejeitado
            if quant_linhas_processadas:
                pagamento.save()

    if tipo == 'rejeitados':
        return '{} pagamentos foram REJEITADOS na folha de {}/{}.<br/>' '{} pagamentos foram rejeitados parcialmente.<br/>'.format(
            quant_nao_aceitos, mes_arq, ano_arq, quant_aceitos_parcial
        )

    return '{} pagamentos tiveram sua INCLUSÃO EFETUADA na folha de {}/{}.<br/>' '{} pagamentos foram aceitos parcialmente.<br/>'.format(
        quant_aceitos, mes_arq, ano_arq, quant_aceitos_parcial
    )


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def lancado_manualmente_substituicao(request):
    calculo, calculo_id, pagamento_id = None, None, None
    if request.GET.get('calculo_id') is not None:
        calculo_id = request.GET.get('calculo_id')
    if request.GET.get('pagamento_id') is not None:
        pagamento_id = request.GET.get('pagamento_id')

    pagamento = Pagamento()
    if pagamento_id:
        pagamento = get_object_or_404(Pagamento, pk=pagamento_id)
        if pagamento.situacao not in [3, 5]:  # Aceito e Lançado Manualmente
            pagamento.situacao = 5
    elif calculo_id:
        calculo = get_object_or_404(CalculoSubstituicao, pk=calculo_id)
        configuracao = ConfigPagamento.objects.get(tipo_calculo=calculo.tipo)
        data_inicio = calculo.get_data_inicio()
        data_fim = calculo.get_data_fim()
        pagamento = Pagamento(calculo=calculo, configuracao=configuracao, situacao=5, mes_inicio=data_inicio, mes_fim=data_fim)  # Lançado Manualmente
    pagamento.save()

    return httprr(
        calculo.get_absolute_url() if calculo else pagamento.get_absolute_url(),
        'Cálculo enviado ao módulo Pagamento como Lançado Manualmente.' if calculo else 'Pagamento alterado para Lançado Manualmente.',
    )


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def regerar_arquivo(request, pk):
    arquivo = get_object_or_404(ArquivoPagamento, pk=pk)
    return respond_as_attachment(arquivo.file_path, os.path.split(arquivo.file_path)[1])


@rtr()
@permission_required('rh.eh_servidor')
def calculoterminocontrato(request, pk):
    calc = Calculo.objects.get(pk=pk).get_calculo_espeficico()

    str_calculo = calc._meta.label
    str_periodo = calc.get_periodo_model()._meta.label
    str_detalhamento = calc.get_detalhamento_model()._meta.label
    str_ferias = None
    return calculo(pk, str_calculo, str_periodo, str_detalhamento, str_ferias)


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def informar_irpf(request, pk):
    # @permission_required('calculos_pagamentos.change_calculoterminocontrato')

    title = 'Informar valor de IRPF da Gratificação Natalina'
    calc = Calculo.objects.get(pk=pk).get_calculo_espeficico()
    form = InformarIRPFForm(request.POST or None, instance=calc)
    if form.is_valid():
        form.save()
        return httprr(calc.get_absolute_url(), 'Valor de IRPF da Gratificação Natalina incluído.')
    return locals()


# ======================================================================================================================
# ======================================================================================================================


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def excluir_calculo(request):
    calculo_id = request.GET.get('calculo_id')

    calculo = get_object_or_404(Calculo, pk=calculo_id)
    if calculo.pode_excluir:
        calculo.excluido = True
        calculo.save()
    else:
        return httprr(calculo.get_absolute_url(), message='Impossível excluir este cálculo pois existem pagamentos não excluídos vinculados a ele.', tag='error')
    return httprr(calculo.get_absolute_url(), 'Cálculo excluído com sucesso.')


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def excluir_pagamento(request):
    pagamento_id = request.GET.get('pagamento_id')

    pagamento = get_object_or_404(Pagamento, pk=pagamento_id)
    if pagamento.pode_excluir:
        pagamento.situacao = 7
        pagamento.save()
    else:
        return httprr(pagamento.get_absolute_url(), message='Impossível excluir este pagamento pois existem pagamentos não excluídos vinculados a ele.', tag='error')
    return httprr(pagamento.get_absolute_url(), 'Pagamento excluído com sucesso.')


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def desfazer_pagamento(request):
    pagamento_id = request.GET.get('pagamento_id')

    pagamento = get_object_or_404(Pagamento, pk=pagamento_id)
    if pagamento.pode_desfazer_pagamento:
        pagamento.situacao = 1
        pagamento.save()
    else:
        return httprr(pagamento.get_absolute_url(), message='Impossível desfazer este pagamento.', tag='error')
    return httprr(pagamento.get_absolute_url(), 'Pagamento desfeito com sucesso.')


# ======================================================================================================================
# ======================================================================================================================


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def lancar_pagamento_manualmente(request, calculo_id, calculo):

    calculo = get_object_or_404(getClasseCalculo(int(calculo)), pk=calculo_id)

    try:
        configuracao = ConfigPagamento.objects.get(tipo_calculo=calculo.tipo)
    except Exception:
        return httprr(calculo.get_absolute_url(), message='Não existe configuração de pagamento para este cálculo. ', tag='error')

    data_inicio = calculo.get_data_inicio()
    data_fim = calculo.get_data_fim()
    pagamento = Pagamento(calculo=calculo, configuracao=configuracao, situacao=5, mes_inicio=data_inicio, mes_fim=data_fim)

    pagamento.save()

    return httprr(calculo.get_absolute_url(), 'Cálculo enviado ao módulo Pagamento como Lançado Manualmente no SIAPE.')


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def criar_pagamento(request, calculo_id, calculo):
    calculo = get_object_or_404(getClasseCalculo(int(calculo)), pk=calculo_id)

    configuracao = None
    try:
        configuracao = ConfigPagamento.objects.get(tipo_calculo=calculo.tipo)
    except Exception:
        return httprr(calculo.get_absolute_url(), message='Não existe configuração de pagamento para este cálculo. ', tag='error')

    data_inicio = calculo.get_data_inicio()
    data_fim = calculo.get_data_fim()
    pagamento = Pagamento(calculo=calculo, configuracao=configuracao, situacao=1, mes_inicio=data_inicio, mes_fim=data_fim)

    pagamento.save()

    return httprr(calculo.get_absolute_url(), 'Cálculo enviado ao módulo Pagamento como Não Processado.')


@rtr()
@permission_required('calculos_pagamentos.add_pagamento')
def alterar_para_lancado_manualmente(request):
    pagamento_id = request.GET.get('pagamento_id')

    pagamento = get_object_or_404(Pagamento, pk=pagamento_id)
    if pagamento.pode_pagar:
        pagamento.situacao = 5
        pagamento.save()
    else:
        return httprr(pagamento.get_absolute_url(), message='Pagamento não pode ser alterado para Lançado Manualmente.', tag='error')
    return httprr(pagamento.get_absolute_url(), 'Pagamento alterado para Lançado Manualmente com sucesso.')
