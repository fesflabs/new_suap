# -*- coding: utf-8 -*-


from django.contrib.auth.decorators import permission_required, login_required
from django.shortcuts import get_object_or_404

from acumulocargo.models import DeclaracaoAcumulacaoCargo, PeriodoDeclaracaoAcumuloCargos
from djtools import layout
from djtools.utils import rtr, httprr, group_required, documento


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()

    if request.user.eh_servidor:
        servidor = request.user.get_relacionamento()
        if not servidor.eh_estagiario:
            qs = PeriodoDeclaracaoAcumuloCargos.periodo_aberto_para_cadastro(servidor)
            if qs.exists():
                qs_declaracao = DeclaracaoAcumulacaoCargo.objects.filter(periodo_declaracao_acumulo_cargo__in=qs, servidor=servidor)
                if qs_declaracao.exists():
                    declaracao = qs_declaracao[0]
                    inscricoes.append(
                        dict(
                            url='/admin/acumulocargo/declaracaoacumulacaocargo/{}/change/'.format(declaracao.id),
                            titulo='Você ainda pode editar o seu <strong>Termo de Acúmulo de Cargos</strong>.',
                            prazo=qs[0].data_fim,
                        )
                    )
                else:
                    inscricoes.append(
                        dict(
                            url='/admin/acumulocargo/declaracaoacumulacaocargo/add/',
                            titulo='Preencha o <strong>Termo de Acúmulo de Cargos {}</strong>.'.format(qs[0].ano),
                            prazo=qs[0].data_fim,
                        )
                    )

    return inscricoes


@rtr()
@permission_required('acumulocargo.pode_ver_declaracao')
def ver_declaracao(request, pk):
    declaracao = get_object_or_404(DeclaracaoAcumulacaoCargo, pk=pk)
    servidor = declaracao.servidor

    if not pode_ver_declaracao(request, declaracao):
        return httprr('/admin/acumulocargo/declaracaoacumulacaocargo/', "Você não tem permissão para acessar esta declaração.", tag="error")

    title = '{} - Declaração de {}'.format(servidor, declaracao.periodo_declaracao_acumulo_cargo.ano)
    cargo_funcao = '{} {}'.format(servidor.cargo_emprego, servidor.funcao or '')

    ''' Cargos acumuláveis '''
    cargos_acumulaveis = declaracao.cargopublicoacumulavel_set.all()

    ''' Tem Aposentadoria '''
    aposentadorias = declaracao.temaposentadoria_set.all()

    ''' Tem Pensão '''
    pensoes = declaracao.tempensao_set.all()

    ''' Tem Atuação Gerencial '''
    atuacoes_gerenciais = declaracao.tematuacaogerencial_set.all()
    mostrar_atuacoes_gerenciais = True
    if atuacoes_gerenciais:
        atuacao = atuacoes_gerenciais[0]
        if atuacao.nao_exerco_atuacao_gerencial or atuacao.nao_exerco_comercio:
            mostrar_atuacoes_gerenciais = False

    ''' Exerce Atividade Remunerada Privada '''
    atividades_remuneradas = declaracao.exerceatividaderemuneradaprivada_set.all()
    mostrar_atividades_remuneradas = True
    if atividades_remuneradas:
        atividade = atividades_remuneradas[0]
        if atividade.nao_exerco_atividade_remunerada:
            mostrar_atividades_remuneradas = False

    return locals()


@documento(enumerar_paginas=False)
@rtr()
@login_required()
@group_required('Coordenador de Gestão de Pessoas Sistêmico')
def imprimir_declaracoes(request, pk):
    questionario = get_object_or_404(PeriodoDeclaracaoAcumuloCargos, pk=pk)
    declaracoes = DeclaracaoAcumulacaoCargo.objects.filter(periodo_declaracao_acumulo_cargo=questionario)
    return locals()


def pode_ver_declaracao(request, declaracao):
    return request.user.is_superuser or eh_rh(request) or eh_dono(request, declaracao)


def eh_dono(request, declaracao):
    return declaracao.servidor_id == request.user.get_profile().id


def eh_rh(request):
    return request.user.has_perm('rh.change_servidor')
