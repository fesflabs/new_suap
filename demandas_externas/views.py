# -*- coding: utf-8 -*-
import datetime

from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize
from comum.utils import get_uo
from djtools import layout
from djtools.utils import send_mail, rtr, httprr, permission_required
from demandas_externas.forms import DemandaForm, RecusarDemandaForm, AtribuirDemandaForm, IndicarCampusForm, MembroEquipeForm, RegistrarAtendimentoForm
from demandas_externas.models import Periodo, Demanda, Equipe
from django.conf import settings
from comum.models import Configuracao


@layout.servicos_anonimos()
def servicos_anonimos(request):
    servicos_anonimos = list()
    servicos_anonimos.append(dict(categoria='Solicitações', url="/demandas_externas/periodos_demanda/", icone="file-alt", titulo='Demandas da Comunidade'))
    return servicos_anonimos


@layout.quadro('Demandas Externas', icone='suitcase', pode_esconder=True)
def index_quadros(quadro, request):
    if request.user.has_perm('demandas_externas.view_publicoalvo'):
        pendentes_aceite = Demanda.objects.filter(situacao=Demanda.SUBMETIDA)
        if not request.user.has_perm('demandas_externas.add_publicoalvo'):
            pendentes_aceite = pendentes_aceite.filter(campus_atendimento=get_uo(request.user))
        if pendentes_aceite.exists():
            qtd = pendentes_aceite.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo='Demanda%(plural)s Externa%(plural)s Pendente%(plural)s' % dict(plural=pluralize(qtd)),
                    subtitulo='De avaliação',
                    qtd=qtd,
                    url='/admin/demandas_externas/demanda?tab=tab_submetidas',
                )
            )

        pendentes_campus = Demanda.objects.filter(campus_atendimento__isnull=True).exclude(situacao__in=[Demanda.SUBMETIDA, Demanda.NAO_ATENDIDA, Demanda.NAO_ACEITA])
        if pendentes_campus.exists():
            qtd = pendentes_campus.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo='Demanda%(plural)s Externa%(plural)s Pendente%(plural)s' % dict(plural=pluralize(qtd)),
                    subtitulo='De indicação de campus de atendimento',
                    qtd=qtd,
                    url='/demandas_externas/demanda/{}/'.format(pendentes_campus[0].id),
                )
            )

        pendentes_responsavel = Demanda.objects.filter(situacao__in=[Demanda.EM_ATENDIMENTO, Demanda.EM_ESPERA], responsavel__isnull=True)
        if not request.user.has_perm('demandas_externas.add_publicoalvo'):
            pendentes_responsavel = pendentes_responsavel.filter(campus_atendimento=get_uo(request.user))
        if pendentes_responsavel.exists():
            qtd = pendentes_responsavel.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo='Demanda%(plural)s Externa%(plural)s Pendente%(plural)s' % dict(plural=pluralize(qtd)),
                    subtitulo='De indicação de responsável',
                    qtd=qtd,
                    url='/demandas_externas/demanda/{}/'.format(pendentes_responsavel[0].id),
                )
            )

    return quadro


@rtr()
def periodos_demanda(request):
    title = 'Adicionar Demanda da Comunidade'
    category = 'Solicitações'
    icon = 'file-alt'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    hoje = datetime.datetime.now().date()
    periodos = Periodo.objects.filter(data_inicio__lte=hoje, data_termino__gte=hoje)
    return locals()


@rtr()
def cadastrar_demanda(request, periodo_id):
    title = 'Adicionar Demanda'
    periodo = get_object_or_404(Periodo, pk=periodo_id)
    sigla_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    form = DemandaForm(request.POST or None, periodo=periodo, sigla_instituicao=sigla_instituicao)
    if form.is_valid():
        o = form.save(False)
        o.cadastrada_em = datetime.datetime.now()
        o.periodo = periodo
        o.campus_atendimento = form.cleaned_data.get('campus_indicado')
        o.save()
        form.save_m2m()
        return httprr('/demandas_externas/periodos_demanda/', 'Demanda cadastrada com sucesso. Mensagens sobre o andamento da demanda serão enviadas para o email informado.')

    return locals()


def pode_visualizar_demanda(request, demanda, uo):
    if demanda.situacao in [Demanda.SUBMETIDA, Demanda.NAO_ACEITA] and not request.user.has_perm('demandas_externas.view_publicoalvo'):
        raise PermissionDenied
    elif (
        not request.user.has_perm('demandas_externas.add_publicoalvo')
        and not request.user.has_perm('demandas_externas.pode_ver_todas_demandas_externas')
        and demanda.campus_atendimento
        and demanda.campus_atendimento != uo
    ):
        raise PermissionDenied
    elif (
        not request.user.has_perm('demandas_externas.view_publicoalvo')
        and not request.user.has_perm('demandas_externas.pode_ver_todas_demandas_externas')
        and ((demanda.campus_atendimento and demanda.campus_atendimento != uo) or (not demanda.campus_atendimento))
    ):
        raise PermissionDenied


@rtr()
@permission_required('demandas_externas.view_demanda')
def demanda(request, demanda_id):
    title = 'Visualizar Demanda'
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    uo = get_uo(request.user)
    pode_visualizar_demanda(request, demanda, uo)
    pode_aceitar = request.user.has_perm('demandas_externas.add_publicoalvo') or (
        request.user.has_perm('demandas_externas.view_publicoalvo') and (not demanda.campus_atendimento or demanda.campus_atendimento == uo)
    )
    pode_assumir_demanda = not request.user.has_perm('demandas_externas.pode_ver_todas_demandas_externas') and not request.user.has_perm(
        'demandas_externas.pode_ver_demandas_externas'
    )
    return locals()


@rtr()
@permission_required('demandas_externas.view_publicoalvo')
def aceitar_demanda(request, demanda_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    uo = get_uo(request.user)
    pode_visualizar_demanda(request, demanda, uo)
    demanda.situacao = Demanda.EM_ESPERA
    demanda.avaliada_em = datetime.datetime.now()
    demanda.avaliada_por = request.user.get_vinculo()
    demanda.save()
    titulo = '[SUAP] Registro de Demanda Externa'
    texto = (
        '<h1>Extensão</h1>'
        '<h2>Registro de Demanda Externa</h2>'
        '<p>Descrição da Demanda: {}'
        '<p>A demanda foi aceita. Novas informações sobre o andamento e a execução serão enviadas em emails posteriores.</p>'.format(demanda.descricao)
    )
    send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, [demanda.email])
    return httprr('/demandas_externas/demanda/{}/'.format(demanda.id), 'Demanda aceita com sucesso.')


@rtr()
@permission_required('demandas_externas.view_publicoalvo')
def nao_aceitar_demanda(request, demanda_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    title = u'Não Aceitar Demanda'
    uo = get_uo(request.user)
    pode_visualizar_demanda(request, demanda, uo)
    form = RecusarDemandaForm(request.POST or None, instance=demanda)
    if form.is_valid():
        o = form.save(False)
        o.situacao = Demanda.NAO_ACEITA
        o.avaliada_em = datetime.datetime.now()
        o.avaliada_por = request.user.get_vinculo()
        o.save()
        titulo = '[SUAP] Registro de Demanda Externa'
        texto = (
            '<h1>Extensão</h1>'
            '<h2>Registro de Demanda Externa</h2>'
            '<p>Descrição da Demanda: {}'
            '<p>A demanda não foi aceita. Motivo: {} </p>'.format(demanda.descricao, demanda.observacoes)
        )
        send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, [demanda.email])
        return httprr('/demandas_externas/demanda/{}/'.format(demanda.id), 'Demanda não aceita com sucesso.')
    return locals()


@rtr()
@permission_required('demandas_externas.view_demanda')
def atribuir_demanda(request, demanda_id):
    title = 'Atribuir Demanda'
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    uo = get_uo(request.user)
    pode_visualizar_demanda(request, demanda, uo)
    if not request.user.has_perm('demandas_externas.pode_ver_todas_demandas_externas') and not request.user.has_perm('demandas_externas.pode_ver_demandas_externas'):
        form = AtribuirDemandaForm(request.POST or None, instance=demanda, request=request)
        if form.is_valid():
            o = form.save(False)
            o.atribuida_em = datetime.datetime.now()
            o.atribuida_por = request.user.get_vinculo()
            o.situacao = Demanda.EM_ATENDIMENTO
            o.save()
            titulo = '[SUAP] Registro de Demanda Externa'
            texto = (
                '<h1>Extensão</h1>'
                '<h2>Registro de Demanda Externa</h2>'
                '<p>Descrição da Demanda: {}'
                '<p>A demanda está em atendimento. Novas informações sobre o andamento e a execução serão enviadas em emails posteriores.</p>'.format(demanda.descricao)
            )
            send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, [demanda.email])
            return httprr('/demandas_externas/demanda/{}/'.format(demanda.id), 'Demanda atribuída com sucesso.')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('demandas_externas.view_publicoalvo')
def indicar_campus_atendimento(request, demanda_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    title = u'Indicar Campus de Atendimento'
    uo = get_uo(request.user)
    pode_visualizar_demanda(request, demanda, uo)
    form = IndicarCampusForm(request.POST or None, instance=demanda)
    if form.is_valid():
        form.save()
        return httprr('/demandas_externas/demanda/{}/'.format(demanda.id), 'Campus de atendimento indicado com sucesso.')
    return locals()


@rtr()
@permission_required('demandas_externas.view_publicoalvo')
def retornar_demanda(request, demanda_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    uo = get_uo(request.user)
    pode_visualizar_demanda(request, demanda, uo)
    if demanda.campus_atendimento:
        demanda.campus_atendimento = None
        demanda.save()
        return httprr('/demandas_externas/demanda/{}/'.format(demanda.id), 'Demanda retornada com sucesso.')
    else:
        raise PermissionDenied


@rtr()
@permission_required('demandas_externas.view_demanda')
def adicionar_membro(request, demanda_id):
    title = 'Adicionar Membro na Equipe'
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    if demanda.responsavel == request.user.get_vinculo() and not demanda.foi_concluida():
        form = MembroEquipeForm(request.POST or None, demanda=demanda)
        if form.is_valid():
            for participante in form.cleaned_data.get('participantes'):
                if not Equipe.objects.filter(demanda=demanda, participante=participante).exists():
                    membro = Equipe()
                    membro.demanda = demanda
                    membro.participante = participante
                    membro.save()
            for membro in demanda.equipe_set.all():
                if membro.participante not in form.cleaned_data.get('participantes'):
                    membro.delete()

            return httprr('/demandas_externas/demanda/{}/?tab=dados_equipe_demanda'.format(demanda.id), 'Membro da equipe cadastrado com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('demandas_externas.view_demanda')
def registrar_atendimento(request, demanda_id):
    title = 'Registrar Atendimento da Demanda'
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    if demanda.responsavel == request.user.get_vinculo() and not demanda.qtd_beneficiados_atendidos:
        form = RegistrarAtendimentoForm(request.POST or None, instance=demanda)
        if form.is_valid():
            o = form.save(False)
            o.concluida_em = datetime.datetime.now()
            o.situacao = Demanda.ATENDIDA
            o.save()
            titulo = '[SUAP] Registro de Demanda Externa'
            texto = (
                '<h1>Extensão</h1>'
                '<h2>Registro de Demanda Externa</h2>'
                '<p>Descrição da Demanda: {}'
                '<p>A demanda foi atendida. Data da conclusão: {}.</p>'.format(demanda.descricao, demanda.concluida_em)
            )
            send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, [demanda.email])
            return httprr('/demandas_externas/demanda/{}/?tab=dados_execucao_demanda'.format(demanda.id), 'Atendimento da demanda registrado com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('demandas_externas.view_periodo')
def ver_periodo(request, periodo_id):
    title = 'Período de Recebimento'
    periodo = get_object_or_404(Periodo, pk=periodo_id)
    return locals()
