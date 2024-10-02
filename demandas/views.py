from collections import OrderedDict
from datetime import date, datetime, timedelta
from django.apps import apps
import gitlab
import xlwt
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.db.models import Count
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize, slugify
from djtools.utils.response import render_to_string
from django.urls import reverse_lazy
from django.views.decorators.csrf import csrf_exempt
from gitlab import GitlabError
from requests.exceptions import ConnectionError

from demandas import tasks
from comum.models import Comentario, User, UsuarioGrupo, Configuracao
from comum.utils import get_uo
from demandas.forms import (
    AnexosForm,
    ConfirmarComSenhaForm,
    DashboardForm,
    DoDForm,
    EspecificacaoForm,
    NotaInternaForm,
    RelatorioForm,
    SituacaoAlterarFormFactory,
    DataPrevisaoAlterarForm,
    AcompanhamentoForm,
    EspecificacaoTecnicaForm,
    SugestaoMelhoriaAddForm, SugestaoMelhoriaEdicaoBasicaForm, SugestaoMelhoriaEdicaoAreaAtuacaoForm,
    SugestaoMelhoriaEdicaoCompletaForm,
    NovaPrioridadeDemandaForm,
    ExecutarComandoForm)
from demandas.models import Anexos, Atualizacao, Demanda, DemandaVoto, DoD, Especificacao, NotaInterna, Situacao, Tag, TipoDemanda, \
    AreaAtuacaoDemanda, AnalistaDesenvolvedor, ProjetoGitlab, AmbienteHomologacao, SugestaoMelhoria, SugestaoVoto
from demandas.utils import Notificar
from djtools import layout
from djtools.html.graficos import GroupedColumnChart, PieChart
from djtools.lps import lps
from djtools.templatetags.filters import in_group
from djtools.utils import httprr, permission_required, rtr, JsonResponse, documento


@layout.servicos_anonimos()
def servicos_anonimos(request):

    servicos_anonimos = list()

    servicos_anonimos.append(dict(categoria='Consultas', titulo='Atualizações do Sistema', icone='file-contract', url='/demandas/atualizacoes/'))

    return servicos_anonimos


@layout.atualizacao()
def index_atualizacoes(request):
    alertas = list()
    user_groups = request.user.groups.all()
    atualizacoes = Atualizacao.objects.filter(
        id__in=Atualizacao.objects.filter(grupos__in=user_groups, data__gte=datetime.now() - timedelta(days=5), data__lte=datetime.now()).values_list('id', flat=True)
    ).order_by('-data')

    for atualizacao in atualizacoes:
        alertas.append(
            dict(
                extra=atualizacao.data.strftime('%d/%m/%Y'),
                url=f'/demandas/atualizacao/{atualizacao.pk}/',
                titulo='<strong>{}</strong>: {}'.format(", ".join(atualizacao.get_tags()), atualizacao.descricao),
            )
        )
    return alertas


@layout.quadro('Demandas', icone='flag', pode_esconder=True)
def index_quadros(quadro, request):
    if in_group(request.user, 'Demandante'):
        demandas = Demanda.objects.filter(situacao__in=[Situacao.ESTADO_EM_ANALISE, Situacao.ESTADO_SUSPENSO, Situacao.ESTADO_EM_HOMOLOGACAO]).filter(demandantes=request.user)
        if demandas.exists():
            quadro.add_item(
                layout.ItemContador(
                    titulo='Demandas',
                    subtitulo='Aguardando seu feedback',
                    qtd=demandas.count(),
                    url=f'admin/demandas/demanda/?tab=tab_pendentes&demandantes__id__exact={request.user.pk}',
                )
            )

    if in_group(request.user, 'Analista'):
        demandas_como_analista = Demanda.objects.filter(situacao__in=[Situacao.ESTADO_ABERTO, Situacao.ESTADO_EM_NEGOCIACAO]).filter(
            analistas=request.user
        )
        if demandas_como_analista.exists():
            quadro.add_item(
                layout.ItemContador(
                    titulo='Demanda{s} atribuída{s}'.format(s=pluralize(demandas_como_analista.count())),
                    subtitulo='Como analista',
                    qtd=demandas_como_analista.count(),
                    url='admin/demandas/demanda/?tab=tab_como_analista',
                )
            )

    if in_group(request.user, 'Desenvolvedor'):
        demandas_como_desenvolvedor = Demanda.objects.filter(situacao__in=[Situacao.ESTADO_APROVADO, Situacao.ESTADO_EM_DESENVOLVIMENTO, Situacao.ESTADO_HOMOLOGADA]).filter(
            desenvolvedores=request.user
        )
        if demandas_como_desenvolvedor.exists():
            quadro.add_item(
                layout.ItemContador(
                    titulo='Demanda{s} atribuída{s}'.format(s=pluralize(demandas_como_desenvolvedor.count())),
                    subtitulo='Como desenvolvedor',
                    qtd=demandas_como_desenvolvedor.count(),
                    url='admin/demandas/demanda/?tab=tab_como_desenvolvedor',
                )
            )

    if in_group(request.user, 'Recebedor de Demandas'):
        demandas_sem_analista = Demanda.objects.filter(analistas__isnull=True, prioridade__lte=5).exclude(situacao=Situacao.ESTADO_SUSPENSO)
        if demandas_sem_analista.exists():
            quadro.add_item(
                layout.ItemContador(
                    titulo='Demanda{s} pendente{s}'.format(s=pluralize(demandas_sem_analista.count())),
                    subtitulo='Sem analista',
                    qtd=demandas_sem_analista.count(),
                    url='admin/demandas/demanda/?analistas__isnull=True&tab=tab_ativas',
                )
            )

        demandas_aprovadas_sem_desenvolvedor = Demanda.objects.filter(desenvolvedores__isnull=True, situacao=Situacao.ESTADO_APROVADO, prioridade__lte=5)
        if demandas_aprovadas_sem_desenvolvedor.exists():
            quadro.add_item(
                layout.ItemContador(
                    titulo='Demanda{s} aprovada{s}'.format(s=pluralize(demandas_aprovadas_sem_desenvolvedor.count())),
                    subtitulo='Sem desenvolvedor',
                    qtd=demandas_aprovadas_sem_desenvolvedor.count(),
                    url='admin/demandas/demanda/?situacao__exact=Aprovada&desenvolvedores__isnull=True&tab=tab_ativas',
                )
            )

    if in_group(request.user, 'Analista, Desenvolvedor'):
        quadro.add_item(layout.ItemAcessoRapido(titulo='Demandas', url='/demandas/demandas/', icone='columns'))
        quadro.add_item(layout.ItemAcessoRapido(titulo='Painel de Força-Trabalho', url='/demandas/painel_forca_trabalho/', icone='columns'))

    # Sugestões de melhoria
    minhas_sugestoes_ativas_como_demandante = SugestaoMelhoria.sugestoes_ativas(
        SugestaoMelhoria.sugestoes_por_papel_usuario(
            user_demandante=request.user
        )
    )

    if minhas_sugestoes_ativas_como_demandante.exists():
        quadro.add_item(
            layout.ItemContador(
                titulo='Sugestões de Melhorias Ativas',
                subtitulo='Como Demandante',
                qtd=minhas_sugestoes_ativas_como_demandante.count(),
                url='admin/demandas/sugestaomelhoria/?tab=tab_como_demandante',
            )
        )

    return quadro


@rtr('demandas/templates/demanda.html')
@permission_required(['demandas.add_demanda', 'demandas.change_demanda', 'demandas.view_demanda'])
@lps
def visualizar(request, demanda_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    user = request.user

    if not demanda.permite_visualizar(user):
        raise PermissionDenied('Você não tem permissão para visualizar esta demanda.')

    title = demanda

    voto = DemandaVoto.objects.filter(demanda=demanda, usuario=user)
    if voto.exists():
        voto = voto[0]
    else:
        voto = None

    if demanda.situacao != Situacao.ESTADO_CANCELADO and demanda.situacao != Situacao.ESTADO_SUSPENSO:
        steps = '<ul class="steps">'
        for estado, help in list(Situacao.ESTADO_FLUXO.items()):
            if estado == demanda.situacao:
                steps += f'<li data-hint="{help}" class="hint"><span class="step-{slugify(estado)} active">{estado}</span></li>'
            else:
                steps += f'<li data-hint="{help}" class="hint"><span class="step-{slugify(estado)}">{estado}</span></li>'
        steps += '</ul>'

    hoje = date.today()

    eh_analista = in_group(request.user, 'Analista')
    eh_desenvolvedor = in_group(request.user, 'Desenvolvedor')
    eh_demandante = demanda.eh_demandante(request.user)
    eh_interessado = demanda.eh_interessado(request.user)
    eh_observador_pendente = demanda.eh_observador_pendente(request.user)
    eh_observador = demanda.eh_observador(request.user)

    dod = DoD.objects.filter(demanda=demanda)
    aprovada = (demanda.em_analise or demanda.ja_foi_aprovada()) and "collapsed" or ""
    qtd_comentarios = Comentario.objects.filter(
        content_type=ContentType.objects.get(app_label=demanda._meta.app_label, model=demanda._meta.model_name), object_id=demanda.pk, resposta=None
    ).count()
    data_previsao = demanda.get_ultimo_historico_situacao().data_previsao and datetime.combine(demanda.get_ultimo_historico_situacao().data_previsao, datetime.max.time()) or None

    if dod.exists():
        dod = dod[0]
    else:
        dod = DoD()
        dod.demanda = demanda
        dod.modulo = ''
        dod.descricao = ''
        dod.envolvidos = ''
        dod.save()

    pode_anexar = demanda.pode_anexar(request.user)

    sempre_visivel = ""
    if demanda.consolidacao_sempre_visivel and eh_analista and not demanda.eh_situacao_terminal():
        sempre_visivel = "(Sempre visível)"

    # Monta a lista com as quantidades de demandas que tenha a mesma área de atuação da Demanda Atual
    demandas = Demanda.objects.filter(area=demanda.area)
    lista = []
    em_andamento = demandas.filter(
        situacao__in=[
            Situacao.ESTADO_EM_NEGOCIACAO,
            Situacao.ESTADO_APROVADO,
            Situacao.ESTADO_EM_DESENVOLVIMENTO,
            Situacao.ESTADO_HOMOLOGADA,
            Situacao.ESTADO_EM_IMPLANTACAO,
        ],
    ).count()
    aguardando_feedback = demandas.filter(
        situacao__in=[
            Situacao.ESTADO_EM_ANALISE,
            Situacao.ESTADO_EM_HOMOLOGACAO,
            Situacao.ESTADO_SUSPENSO,
        ],
    ).count()
    nao_iniciadas = demandas.filter(situacao=Situacao.ESTADO_ABERTO).count()
    concluidas = demandas.filter(situacao=Situacao.ESTADO_CONCLUIDO).count()
    lista.append([em_andamento, aguardando_feedback, nao_iniciadas, concluidas])

    exibir_consolidacao = demanda.consolidacao_sempre_visivel or (eh_analista or eh_desenvolvedor or demanda.ja_foi_aprovada() or demanda.em_analise)

    pode_add_or_change_especificacao = eh_analista or eh_desenvolvedor or \
        request.user.has_perm('demandas.add_especificacao') or request.user.has_perm('demandas.change_especificacao')

    return locals()


@rtr()
@login_required()
def concordar_demanda(request, demanda_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)

    if demanda.pode_votar():
        demanda_voto = DemandaVoto.objects.filter(demanda=demanda, usuario=request.user)
        if demanda_voto.exists():
            voto = demanda_voto[0]
        else:
            voto = DemandaVoto()
            voto.demanda = demanda

        voto.concorda = True
        voto.save()

        return httprr(demanda.get_absolute_url(), 'Voto cadastrado com sucesso.', 'success')
    else:
        return httprr(demanda.get_absolute_url(), 'Não foi possível votar nesta demanda', 'error')


@rtr()
@login_required()
def discordar_demanda(request, demanda_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)

    if demanda.pode_votar():
        demanda_voto = DemandaVoto.objects.filter(demanda=demanda, usuario=request.user)
        if demanda_voto.exists():
            voto = demanda_voto[0]
        else:
            voto = DemandaVoto()
            voto.demanda = demanda

        voto.concorda = False
        voto.save()

        return httprr(demanda.get_absolute_url(), 'Voto cadastrado com sucesso.', 'success')
    else:
        return httprr(demanda.get_absolute_url(), 'Não foi possível votar nesta demanda', 'error')


@rtr('demandas/templates/formulario.html')
@permission_required(['demandas.atende_demanda', 'demandas.change_demanda'])
def adicionar_anexo(request, demanda_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)

    if not demanda.pode_anexar(request.user):
        raise PermissionDenied('Você não tem permissão para adicionar anexos.')

    title = f'Demanda #{demanda.pk}: {demanda.titulo}'
    sub_title = 'Adicionar Anexo à Demanda'

    form = AnexosForm(request.POST or None, request.FILES or None, demanda=demanda, usuario=request.user)

    if form.is_valid():
        form.save()
        return httprr('{}?tab=anexos'.format(reverse_lazy('demanda_visualizar', kwargs={'demanda_id': demanda.pk})), 'Anexo adicionado com sucesso.')

    return locals()


@rtr()
@permission_required(['demandas.atende_demanda', 'demandas.change_demanda'])
def remover_anexo(request, anexo_id):
    anexo = get_object_or_404(Anexos, pk=anexo_id)
    demanda = anexo.demanda

    if demanda.pode_remover_anexo and (demanda.eh_demandante(request.user) or anexo.demanda.analistas.filter(pk=request.user.pk).exists()):
        anexo.delete()
        return httprr('{}?tab=anexos'.format(reverse_lazy('demanda_visualizar', kwargs={'demanda_id': demanda.pk})), 'Anexo removido com sucesso.')

    raise PermissionDenied('Você não tem permissão para remover anexos neta demanda. Apenas os demandantes e os analistas podem remover anexos.')


@rtr('demandas/templates/formulario.html')
@permission_required('demandas.change_dod')
def dod_alterar(request, demanda_id, dod_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    dod = get_object_or_404(DoD, pk=dod_id)

    title = f'Demanda #{demanda.pk}: {demanda.titulo}'
    sub_title = 'Editar Consolidação da Demanda'
    url_ret = '{}?tab=dod'.format(reverse_lazy('demanda_visualizar', kwargs={'demanda_id': demanda.pk}))

    if demanda.em_analise:
        return httprr(url_ret, 'Não é possível atualizar uma demanda em análise.', tag='error')

    if demanda.aprovada:
        return httprr(url_ret, 'Não é possível atualizar uma demanda já aprovada.', tag='error')

    if demanda != dod.demanda:
        raise PermissionDenied('Esta consolidação não corresponde à demanda atual.')

    form = DoDForm(request.POST or None, instance=dod)

    if form.is_valid():
        form.save()
        return httprr(url_ret, 'A demanda foi {}.'.format(dod_id and 'atualizada' or 'adicionada'), close_popup=True)

    return locals()


@rtr()
@permission_required('demandas.fechar_dod')
def dod_fechar(request, demanda_id, dod_id):
    title = 'Enviar para Aprovação'

    demanda = get_object_or_404(Demanda, pk=demanda_id)
    dod = get_object_or_404(DoD, pk=dod_id)

    url_ret = '{}?tab=dod'.format(reverse_lazy('demanda_visualizar', kwargs={'demanda_id': demanda.pk}))

    if demanda.em_analise:
        return httprr(url_ret, 'Não é possível enviar uma demanda não consolidada para aprovação.', tag='error')

    if demanda.aprovada:
        return httprr(url_ret, 'Esta demanda já foi aprovada.', tag='error')

    if demanda != dod.demanda:
        raise PermissionDenied('Esta consolidação não corresponde à demanda atual.')

    form = ConfirmarComSenhaForm(request.POST or None, request=request)

    if form.is_valid():

        if not dod.especificacao_set.exists():
            return httprr(url_ret, 'A Consolidação da Demanda deve ter pelo menos uma especificação.', tag='error')

        for especificacao in dod.especificacao_set.all():
            if not especificacao.atividades:
                return httprr(url_ret, 'Existem especificações sem atividades cadastradas.', tag='error')

        if form.cleaned_data['confirmar'] == True:
            demanda.alterar_situacao(
                usuario=request.user, situacao=Situacao.ESTADO_EM_ANALISE, comentario='Consolidação liberada para análise dos interessados.', data_conclusao=date.today()
            )

        return httprr(url_ret, 'A demanda foi enviada para análise.')

    return locals()


@rtr()
@permission_required('demandas.aprovar_dod')
def dod_aprovar(request, demanda_id, dod_id):
    title = 'Aprovar Demanda'

    demanda = get_object_or_404(Demanda, pk=demanda_id)
    dod = get_object_or_404(DoD, pk=dod_id)

    url_ret = '{}?tab=dod'.format(reverse_lazy('demanda_visualizar', kwargs={'demanda_id': demanda.pk}))

    if not demanda.eh_demandante(request.user):
        return httprr(url_ret, 'Apenas demandantes podem aprovar a consolidação.', tag='error')

    if not demanda.em_analise:
        return httprr(url_ret, 'Não é possível aprovar uma demanda não consolidada.', tag='error')

    if demanda.aprovada:
        return httprr(url_ret, 'Esta demanda já foi aprovada.', tag='error')

    if demanda != dod.demanda:
        raise PermissionDenied('Esta consolidação não corresponde à demanda atual.')

    form = ConfirmarComSenhaForm(request.POST or None, request=request)

    if form.is_valid():

        if form.cleaned_data['confirmar'] == True:
            demanda.alterar_situacao(usuario=request.user, situacao=Situacao.ESTADO_APROVADO, data_conclusao=date.today())

        return httprr(url_ret, 'A consolidação da demanda foi aprovada.')

    return locals()


@rtr()
@permission_required('demandas.aprovar_dod')
def dod_reprovar(request, demanda_id, dod_id):
    title = 'Reprovar Demanda'

    demanda = get_object_or_404(Demanda, pk=demanda_id)
    dod = get_object_or_404(DoD, pk=dod_id)

    url_ret = '{}?tab=dod'.format(reverse_lazy('demanda_visualizar', kwargs={'demanda_id': demanda.pk}))

    if not demanda.eh_demandante(request.user):
        return httprr(url_ret, 'Apenas demandantes podem reprovar a consolidação.', tag='error')

    if not demanda.em_analise:
        return httprr(url_ret, 'Não é possível reprovar uma demanda não consolidada.', tag='error')

    if demanda.aprovada:
        return httprr(url_ret, 'Não é possível reprovar uma demanda já aprovada.', tag='error')

    if demanda != dod.demanda:
        raise PermissionDenied('Esta consolidação não corresponde à demanda atual.')

    form = ConfirmarComSenhaForm(request.POST or None, request=request)

    if form.is_valid():

        if form.cleaned_data['confirmar'] == True:
            demanda.alterar_situacao(
                usuario=request.user, situacao=Situacao.ESTADO_EM_NEGOCIACAO, comentario='A consolidação da demanda foi reprovada.', data_conclusao=date.today()
            )

        return httprr(url_ret, 'A consolidação da demanda foi reprovada.')

    return locals()


@rtr()
@permission_required('demandas.add_especificacao, demandas.change_especificacao')
def especificacao_add_change(request, demanda_id, dod_id, especificacao_id=None):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    dod = get_object_or_404(DoD, pk=dod_id)
    especificacao = None

    title = 'Adicionar Especificação'

    url_ret = '{}?tab=dod'.format(reverse_lazy('demanda_visualizar', kwargs={'demanda_id': demanda.pk}))

    if demanda.em_analise:
        return httprr(url_ret, 'Não é possível adicionar/alterar uma especificação para uma Consolidação em análise.', tag='error')

    if demanda.aprovada:
        return httprr(url_ret, 'Não é possível adicionar/alterar uma especificação para uma Consolidação aprovada.', tag='error')

    if demanda != dod.demanda:
        raise PermissionDenied('Esta consolidação não corresponde à demanda atual.')

    if especificacao_id:
        title = "Alterar Especificação"
        especificacao = get_object_or_404(Especificacao, pk=especificacao_id)

    form = EspecificacaoForm(request.POST or None, instance=especificacao, dod=dod)

    if form.is_valid():
        form.save()
        return httprr(f'/demandas/visualizar/{demanda.pk}/?tab=dod', f'A especificação foi {especificacao_id and "atualizada" or "adicionada"}.')

    return locals()


@rtr()
@permission_required('demandas.atende_demanda')
def especificacao_tecnica(request, demanda_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    title = 'Especificação Técnica'

    if not demanda.eh_situacao_terminal:
        raise PermissionDenied('Não é possível atualizar a Especificação Técnica para uma Demanda concluída ou cancelada.')

    form = EspecificacaoTecnicaForm(request.POST or None, instance=demanda)

    if form.is_valid():
        form.save()
        return httprr('..', 'A Especificação Técnica foi atualizada.')

    return locals()


@rtr()
@permission_required('demandas.delete_especificacao')
def especificacao_delete(request, demanda_id, dod_id, especificacao_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    dod = get_object_or_404(DoD, pk=dod_id)
    especificacao = get_object_or_404(Especificacao, pk=especificacao_id)

    url_ret = '{}?tab=dod'.format(reverse_lazy('demanda_visualizar', kwargs={'demanda_id': demanda.pk}))

    if demanda.em_analise:
        return httprr(url_ret, 'Não é possível excluir uma especificação para uma Consolidação em análise.', tag='error')

    if demanda.aprovada:
        return httprr(url_ret, 'Não é possível excluir uma especificação para uma Consolidação aprovada.', tag='error')

    if demanda != dod.demanda:
        raise PermissionDenied('Esta consolidação não corresponde à demanda atual.')

    if especificacao.dod != dod:
        raise PermissionDenied('Esta especificação não pertence à esta consolidação da demanda.')

    especificacao.delete()

    return httprr(url_ret, 'A especificação foi removida com sucesso.')


@rtr('demandas/templates/formulario.html')
@permission_required(['demandas.add_demanda'])
def alterar_situacao(request, demanda_id, situacao):
    demanda = get_object_or_404(Demanda, pk=demanda_id)

    estado = Situacao.get_situacao_em_amigavel(situacao)

    title = f'Demanda #{demanda.pk}: {demanda.titulo}'
    sub_title = f'Alterar Etapa para {estado}'

    if not request.user.has_perm('demandas.atende_demanda'):
        raise PermissionDenied('Você não tem permissão para alterar a etapa desta demanda.')

    if estado is None:
        raise PermissionDenied('Etapa escolhida não é válida.')

    if Situacao.eh_estado_terminal(demanda.situacao):
        raise PermissionDenied('Não é possível mudar a etapa atual da demanda.')

    if not Situacao.eh_estado_possivel(demanda.situacao, estado):
        raise PermissionDenied('Não é possível alterar para a etapa escolhida para esta demanda.')

    if estado in [Situacao.ESTADO_EM_ANALISE, Situacao.ESTADO_EM_DESENVOLVIMENTO] and not demanda.tem_dod:
        return httprr(
            reverse_lazy('demanda_visualizar', kwargs={'demanda_id': demanda.pk}),
            'Não é possível alterar uma demanda para Em Análise caso ela não tenha Consolidação.',
            tag='error',
        )

    FormKlass = SituacaoAlterarFormFactory(
        situacao=estado,
        url_validacao=demanda.url_validacao,
        senha_homologacao=demanda.senha_homologacao,
        desenvolvedores_demanda=demanda.desenvolvedores.all(),
        analistas_demanda=demanda.analistas.all(),
    )
    form = FormKlass(request.POST or None)

    if form.is_valid():
        demanda.alterar_situacao(
            usuario=request.user,
            situacao=estado,
            comentario=form.cleaned_data.get('comentario'),
            desenvolvedores=form.cleaned_data.get('desenvolvedores'),
            analistas=form.cleaned_data.get('analistas'),
            data_previsao=form.cleaned_data.get('data_previsao'),
            data_conclusao=form.cleaned_data.get('data_conclusao'),
            ambiente_homologacao=form.cleaned_data.get('ambiente_homologacao'),
            url_validacao=form.cleaned_data.get('url_validacao'),
            senha_homologacao=form.cleaned_data.get('senha_homologacao'),
            id_merge_request=form.cleaned_data.get('id_merge_request')
        )

        return httprr(f'/demandas/visualizar/{demanda.pk}/', 'A etapa da demanda foi alterada.')

    return locals()


@rtr('demandas/templates/formulario.html')
@permission_required(['demandas.add_demanda'])
def editar_data_previsao_etapa(request, demanda_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)

    title = f'Demanda #{demanda.pk}: {demanda.titulo}'
    sub_title = f'Alterar Previsão de Conclusão da Etapa {demanda.situacao}'

    if not request.user.has_perm('demandas.atende_demanda'):
        raise PermissionDenied('Você não tem permissão para alterar a etapa desta demanda.')

    if not Situacao.eh_estado_com_data_previsao(demanda.situacao):
        raise PermissionDenied('Não é possível mudar a data de previsão da etapa atual da demanda.')

    form = DataPrevisaoAlterarForm(request.POST or None)

    if form.is_valid():
        demanda.alterar_situacao(
            usuario=request.user, situacao=demanda.situacao, editou_data_previsao=True, comentario=form.cleaned_data.get('comentario'), data_previsao=form.cleaned_data.get('data_previsao')
        )

        return httprr(f'/demandas/visualizar/{demanda.pk}/', f'A data da previsão da etapa {demanda.situacao} foi alterada.', close_popup=True)

    return locals()


@rtr()
@login_required()
def acompanhar(request, demanda_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    if demanda.privada:
        return httprr(f'/demandas/visualizar/{demanda.pk}/', 'Você não pode acompanhar essa demanda por se tratar de uma demanda privada.')

    demanda.observadores_pendentes.add(request.user)
    demanda.save()

    Notificar.solicitacao_observador(demanda)

    return httprr(f'/demandas/visualizar/{demanda.pk}/', 'Você solicitou sua inclusão como Observador desta demanda. Aguarde validação pelos demandantes.')


@rtr()
@permission_required('demandas.aprovar_dod')
def adicionar_observador(request, demanda_id, user_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    user = get_object_or_404(User, pk=user_id)
    if demanda.privada:
        return httprr(f'/demandas/visualizar/{demanda.pk}/', 'Não é possível adicionar observador nesta demanda por se tratar de uma demanda privada.')
    demanda.observadores_pendentes.remove(user_id)
    demanda.observadores.add(user_id)
    demanda.save()

    Notificar.adicao_como_observador(demanda, user)

    return httprr(f'/demandas/visualizar/{demanda.pk}/', f'O usuário {user.get_profile().nome_usual} foi adicionado como Observador desta demanda.')


@rtr()
@permission_required('demandas.aprovar_dod')
def remover_observador(request, demanda_id, user_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    user = get_object_or_404(User, pk=user_id)

    demanda.observadores_pendentes.remove(user_id)
    demanda.save()

    Notificar.remocao_como_observador_pendente(demanda, user)

    return httprr(
        f'/demandas/visualizar/{demanda.pk}/',
        f'O usuário {user.get_profile().nome_usual} foi removido com sucesso da lista de Observadores Pendentes desta demanda.',
    )


@rtr('demandas/templates/formulario.html')
@permission_required('demandas.add_notainterna')
def nota_interna_add_change(request, demanda_id, notainterna_id=None):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    nota_interna = None

    title = f'Demanda #{demanda.pk}: {demanda.titulo}'
    sub_title = 'Adicionar Nota Interna'

    url_ret = '{}?tab=nota_interna'.format(reverse_lazy('demanda_visualizar', kwargs={'demanda_id': demanda.pk}))

    if not (in_group(request.user, 'Analista') or in_group(request.user, 'Desenvolvedor')):
        return httprr(url_ret, 'A nota interna é somente para analistas e desenvolvedores.', tag='error')

    if demanda.eh_situacao_terminal():
        return httprr(url_ret, 'Não é possível adicionar/alterar uma nota interna a uma demanda em etapa final.', tag='error')

    if notainterna_id is not None:
        sub_title = 'Alterar Nota Interna'
        nota_interna = get_object_or_404(NotaInterna, pk=notainterna_id)

        if nota_interna.demanda != demanda:
            raise PermissionDenied('Esta nota interna não é da demanda relacionada.')

    form = NotaInternaForm(request.POST or None, instance=nota_interna, demanda=demanda)

    if form.is_valid():
        form.save()
        return httprr('..', 'A nota interna foi {}'.format(nota_interna and 'atualizada.' or 'adicionada.'))

    return locals()


@rtr()
@permission_required('demandas.delete_notainterna')
def nota_interna_delete(request, demanda_id, notainterna_id):
    demanda = get_object_or_404(Demanda, pk=demanda_id)
    nota_interna = get_object_or_404(NotaInterna, pk=notainterna_id)

    url_ret = '{}?tab=nota_interna'.format(reverse_lazy('demanda_visualizar', kwargs={'demanda_id': demanda.pk}))

    if demanda.eh_situacao_terminal():
        return httprr(url_ret, 'Não é possível excluir uma atividade para uma DoD produzida', tag='error')

    if demanda != nota_interna.demanda:
        raise PermissionDenied('Esta nota interna não é da demanda atual.')

    nota_interna.delete()

    return httprr(url_ret, 'A nota interna foi removida com sucesso.')


@rtr()
@permission_required('demandas.aprovar_dod')
def homologacao_aprovar(request, demanda_id):
    title = 'Aprovar Homologação'

    demanda = get_object_or_404(Demanda, pk=demanda_id)

    url_ret = f'/demandas/visualizar/{demanda.pk}/'

    if not demanda.eh_demandante(request.user):
        return httprr(url_ret, 'Apenas demandantes podem aprovar a homologação.', tag='error')

    if not demanda.em_homologacao:
        return httprr(url_ret, 'Não é possível aprovar a homologação da demanda.', tag='error')

    if demanda.aprovada:
        return httprr(url_ret, 'A homologação desta demanda já foi aprovada.', tag='error')

    form = ConfirmarComSenhaForm(request.POST or None, request=request)

    if form.is_valid():

        if form.cleaned_data['confirmar'] == True:
            demanda.alterar_situacao(usuario=request.user, situacao=Situacao.ESTADO_HOMOLOGADA, data_conclusao=date.today())

        return httprr(url_ret, 'A homologação da demanda foi aprovada.')

    return locals()


@rtr()
@permission_required('demandas.aprovar_dod')
def homologacao_reprovar(request, demanda_id):
    title = 'Reprovar Homologação'

    demanda = get_object_or_404(Demanda, pk=demanda_id)

    url_ret = f'/demandas/visualizar/{demanda.pk}/'

    if not demanda.eh_demandante(request.user):
        return httprr(url_ret, 'Somente demandantes podem reprovar a homologação.', tag='error')

    if not demanda.em_homologacao:
        return httprr(url_ret, 'Não é possível reprovar a homologação da demanda.', tag='error')

    if demanda.aprovada:
        return httprr(url_ret, 'A homologação desta demanda já foi aprovada.', tag='error')

    form = ConfirmarComSenhaForm(request.POST or None, request=request)

    if form.is_valid():

        if form.cleaned_data['confirmar'] == True:
            demanda.alterar_situacao(
                usuario=request.user, situacao=Situacao.ESTADO_EM_NEGOCIACAO, comentario='A homologação da demanda foi reprovada.', data_conclusao=date.today()
            )

        return httprr(url_ret, 'A homologação da demanda foi reprovada.')

    return locals()


@rtr()
@permission_required('demandas.view_demanda')
def glossario(request):
    title = 'Glossário'
    return locals()


@rtr()
@permission_required('demandas.pode_relatorio')
def painel_forca_trabalho(request):
    title = 'Painel de Força-Trabalho'
    ano_atual = date.today().year
    analistas_desenvolvedores = AnalistaDesenvolvedor.objects.filter(ativo=True)

    # Desenvolvedores por Atualizações
    atualizacoes = Atualizacao.objects.all()
    atualizadores = []
    for atualizador in analistas_desenvolvedores:
        atualizacoes_desenvolvedores = atualizacoes.filter(responsaveis=atualizador.usuario)
        tags = Tag.objects.filter(atualizacao__in=atualizacoes_desenvolvedores).annotate(qtd=Count('atualizacao')).order_by('-qtd')
        if tags.exists():
            atualizadores_tags = []
            for tag in tags:
                atualizadores_tags.append([tag.pk, tag.nome, tag.qtd])
            atualizadores.append(
                [
                    atualizador.usuario_id,
                    atualizador.usuario.pessoafisica.nome_usual,
                    atualizadores_tags,
                    atualizador.usuario.pessoafisica.get_foto_75x100_url,
                    atualizacoes_desenvolvedores.count(),
                ]
            )

    return locals()


@permission_required('demandas.pode_relatorio')
def painel_forca_trabalho_desenvolvedor(request, desenvolvedor_id):
    desenvolvedor = get_object_or_404(AnalistaDesenvolvedor, pk=desenvolvedor_id)

    title = 'Painel de Força-Trabalho'
    ano_atual = date.today().year
    demandas_ativas = Demanda.objects.ativas()
    demandas_concluidas = Demanda.objects.filter(situacao=Situacao.ESTADO_CONCLUIDO)

    # Analista
    demandas_como_analista_a_iniciar = demandas_ativas.filter(situacao=Situacao.ESTADO_ABERTO)
    demandas_como_analista_em_andamento = demandas_ativas.filter(situacao=Situacao.ESTADO_EM_NEGOCIACAO)
    demandas_como_analista_aguardando_feedback = demandas_ativas.filter(situacao__in=[Situacao.ESTADO_EM_ANALISE, Situacao.ESTADO_SUSPENSO])

    # Desenvolvedor
    demandas_como_desenvolvedor_a_iniciar = demandas_ativas.filter(situacao__in=[Situacao.ESTADO_APROVADO, Situacao.ESTADO_HOMOLOGADA])
    demandas_como_desenvolvedor_em_andamento = demandas_ativas.filter(situacao__in=[Situacao.ESTADO_EM_DESENVOLVIMENTO, Situacao.ESTADO_EM_IMPLANTACAO])
    demandas_como_desenvolvedor_aguardando_feedback = demandas_ativas.filter(situacao=Situacao.ESTADO_EM_HOMOLOGACAO)

    # Afastamento ou Ferias
    vinculo = desenvolvedor.usuario.get_vinculo()
    if vinculo.eh_servidor():
        dia = datetime.today()
        afastamento_ou_ferias = vinculo.relacionamento.estah_afastado_ou_de_ferias_ateh(dia)

        # Recesso
        if 'ponto' in settings.INSTALLED_APPS:
            RecessoOpcaoEscolhida = apps.get_model('ponto', 'RecessoOpcaoEscolhida')
            recesso = RecessoOpcaoEscolhida.objects.filter(funcionario=vinculo.relacionamento, validacao=RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO, data_escolha=dia).exists()
        else:
            recesso = False
    # Atraso
    demandas_em_andamento_desenvolvedor = demandas_como_desenvolvedor_em_andamento.filter(desenvolvedores=desenvolvedor.usuario)
    em_atraso = False
    tags = set()
    for atrasada in demandas_em_andamento_desenvolvedor:
        for tag in atrasada.tags.all():
            tags.add(tag.nome)
        if atrasada.em_atraso():
            em_atraso = True
    em_atraso = em_atraso

    # Demandas
    qtd_como_analista_a_iniciar = demandas_como_analista_a_iniciar.filter(analistas=desenvolvedor.usuario).count()
    qtd_como_desenvolvedor_a_iniciar = demandas_como_desenvolvedor_a_iniciar.filter(desenvolvedores=desenvolvedor.usuario).count()
    qtd_como_analista_em_andamento = demandas_como_analista_em_andamento.filter(analistas=desenvolvedor.usuario).count()
    qtd_como_analista_em_andamento = qtd_como_analista_em_andamento
    qtd_como_desenvolvedor_em_andamento = demandas_em_andamento_desenvolvedor.count()
    qtd_como_desenvolvedor_em_andamento = qtd_como_desenvolvedor_em_andamento
    qtd_como_analista_aguardando_feedback = demandas_como_analista_aguardando_feedback.filter(analistas=desenvolvedor.usuario).count()
    qtd_como_desenvolvedor_aguardando_feedback = demandas_como_desenvolvedor_aguardando_feedback.filter(desenvolvedores=desenvolvedor.usuario).count()
    qtd_concluidas = demandas_concluidas.filter(desenvolvedores=desenvolvedor.usuario, data_atualizacao__year=ano_atual).count()
    qtd_demandas_como_analista = qtd_como_analista_a_iniciar + qtd_como_analista_em_andamento + qtd_como_analista_aguardando_feedback
    qtd_demandas_como_analista = qtd_demandas_como_analista
    qtd_demandas_como_desenvolvedor = (
        qtd_como_desenvolvedor_a_iniciar + qtd_como_desenvolvedor_em_andamento + qtd_como_desenvolvedor_aguardando_feedback
    )
    qtd_demandas_como_desenvolvedor = qtd_demandas_como_desenvolvedor

    hoje = date.today()
    # Gitlab
    projetos_issues = []
    qtd_tarefas = 0
    git = gitlab.Gitlab(Configuracao.get_valor_por_chave('demandas', 'gitlab_url'), private_token=Configuracao.get_valor_por_chave('demandas', 'gitlab_token'), timeout=60)
    qtd_issues_concluidas_ano = 0
    qtd_issues_atualizadas_7dias = 0
    qtd_issues_atualizadas_14dias = 0
    for projeto in ProjetoGitlab.objects.filter(ativo=True):
        qtd_issues = 0
        try:
            qtd_issues = len(git.projects.get(projeto.id_projeto_gitlab).issues.list(assignee_username=desenvolvedor.username_gitlab, state='opened', as_list=False))
            qtd_issues_concluidas_ano += len(git.projects.get(projeto.id_projeto_gitlab).issues.list(assignee_username=desenvolvedor.username_gitlab, state='closed', updated_after=date(hoje.year, 1, 1), as_list=False))
            qtd_issues_atualizadas_7dias += len(git.projects.get(projeto.id_projeto_gitlab).issues.list(assignee_username=desenvolvedor.username_gitlab, updated_after=hoje - timedelta(7), as_list=False))
            qtd_issues_atualizadas_14dias += len(git.projects.get(projeto.id_projeto_gitlab).issues.list(assignee_username=desenvolvedor.username_gitlab, updated_after=hoje - timedelta(14), as_list=False))
        except (GitlabError, ConnectionError):
            continue
        qtd_tarefas += qtd_issues
        projetos_issues.append((projeto.nome_projeto, qtd_issues, desenvolvedor.get_url_issues_em_andamento_projeto(projeto)))

    issues_desenvolvedor_em_andamento = projetos_issues
    qtd_tarefas = qtd_tarefas

    # Chamados
    qtd_chamados = 0
    if 'centralservicos' in settings.INSTALLED_APPS:
        from centralservicos.models import Chamado, AtendimentoAtribuicao, GrupoAtendimento, StatusChamado

        atendimentos = AtendimentoAtribuicao.objects.filter(
            grupo_atendimento__in=GrupoAtendimento.meus_grupos(desenvolvedor.usuario), atribuido_para=desenvolvedor.usuario, cancelado_em__isnull=True
        )
        qtd_chamados = (
            Chamado.objects.filter(pk__in=atendimentos.values('chamado'))
            .exclude(status__in=(StatusChamado.get_status_fechado(), StatusChamado.get_status_resolvido(), StatusChamado.get_status_cancelado()))
            .count()
        )
    qtd_chamados = qtd_chamados

    # Erros
    qtd_erros = 0
    if 'erros' in settings.INSTALLED_APPS:
        from erros.models import Erro
        qtd_erros = Erro.objects.filter(atendente_atual_id=vinculo.pk, situacao=Erro.SITUACAO_EM_ANDAMENTO).count()

    # Total
    total = qtd_demandas_como_analista + qtd_demandas_como_desenvolvedor + qtd_tarefas + qtd_chamados + qtd_erros

    # Estilo
    estilo = ''
    situacao = 'Ocupado'
    if total == 0:
        estilo = 'success'
        situacao = 'Disponível'
    elif qtd_como_analista_em_andamento == 0 and qtd_como_desenvolvedor_em_andamento == 0 and qtd_tarefas == 0 and qtd_chamados == 0:
        estilo = 'alert'
        situacao = 'Ocioso'
    elif em_atraso:
        estilo = 'error'
        situacao = 'Atrasado'

    ordem = f"{total:d}.{qtd_como_desenvolvedor_em_andamento:02d}{qtd_como_analista_em_andamento:02d}"

    html = render_to_string('demandas/templates/painel_forca_trabalho_desenvolvedor.html', locals())
    return JsonResponse({'html': html, 'estilo': estilo, 'ordem': ordem})


@rtr()
@permission_required('demandas.pode_relatorio')
def acompanhamento_demandas(request):
    title = 'Relatório de Acompanhamento de Demandas'
    form = AcompanhamentoForm(request.POST or None)
    if form.is_valid():
        area = form.cleaned_data.get('area') or ''
        demandas_concluidas = Demanda.objects.filter(situacao=Situacao.ESTADO_CONCLUIDO).order_by(
            'data_atualizacao')
        if area:
            demandas_prioritarias = Demanda.objects.ativas().filter(area=area).order_by('prioridade')[:5]
            demandas_concluidas = demandas_concluidas.filter(area=area)

        inicio = form.cleaned_data.get('inicio')
        final = form.cleaned_data.get('final')
        demandas_concluidas = demandas_concluidas.filter(data_atualizacao__range=(inicio, final))

    return locals()


@documento()
@rtr()
@permission_required('demandas.pode_relatorio')
def acompanhamento_demandas_pdf(request):
    title = 'Relatório de Acompanhamento de Demandas'
    uo = get_uo(request.user)
    area = request.GET.get('area')
    inicio = request.GET.get('inicio')
    final = request.GET.get('final')
    if not inicio or not final:
        return httprr('acompanhamento_demandas', 'Parametros inválidos para o relatório.', 'alert',)

    inicio = datetime.strptime(inicio, '%Y%m%d').date()
    final = datetime.strptime(final, '%Y%m%d').date()

    demandas_concluidas = Demanda.objects.filter(situacao=Situacao.ESTADO_CONCLUIDO, data_atualizacao__range=(inicio, final)).order_by('data_atualizacao')
    demandas_ativas = Demanda.objects.ativas()
    if area:
        area = AreaAtuacaoDemanda.objects.get(pk=area)
        demandas_prioritarias = Demanda.objects.ativas().filter(area=area).order_by('prioridade')[:5]
        demandas_concluidas = demandas_concluidas.filter(area=area)
        demandas_ativas = demandas_ativas.filter(area=area)
        demandas_prioritarias = demandas_ativas.order_by('prioridade')[:5]
        demandas_nao_prioritarias = demandas_ativas.count() - demandas_prioritarias.count()

    return locals()


@rtr()
@permission_required('demandas.view_demanda')
def demandas(request):
    title = 'Dashboard: Demandas'
    ano_atual = date.today().year
    ano_passado = ano_atual - 1
    demandas_ativas = Demanda.objects.ativas()
    demandas_nao_prioritarias = demandas_ativas.filter(prioridade__gt=5)

    # Estatísticas
    demandas_concluidas = Demanda.objects.filter(situacao=Situacao.ESTADO_CONCLUIDO)
    demandas_concluidas_ano = demandas_concluidas.filter(data_atualizacao__year=ano_atual)
    demandas_concluidas_ano_passado = demandas_concluidas.filter(data_atualizacao__year=ano_passado)
    melhorias = demandas_ativas.filter(tipo=TipoDemanda.MELHORIA).count()
    funcionalidades = demandas_ativas.filter(tipo=TipoDemanda.FUNCIONALIDADE).count()
    demandas_solicitadas = demandas_nao_prioritarias.filter(situacao=Situacao.ESTADO_ABERTO).count()
    demandas_em_negociacao = demandas_nao_prioritarias.filter(situacao=Situacao.ESTADO_EM_NEGOCIACAO).count()
    demandas_em_analise = demandas_nao_prioritarias.filter(situacao=Situacao.ESTADO_EM_ANALISE).count()
    demandas_aprovadas = demandas_nao_prioritarias.filter(situacao=Situacao.ESTADO_APROVADO).count()
    demandas_homologadas = demandas_nao_prioritarias.filter(situacao=Situacao.ESTADO_HOMOLOGADA).count()
    demandas_em_homologacao = demandas_nao_prioritarias.filter(situacao=Situacao.ESTADO_EM_HOMOLOGACAO).count()
    demandas_em_implantacao = demandas_nao_prioritarias.filter(situacao=Situacao.ESTADO_EM_IMPLANTACAO).count()
    demandas_suspensas = demandas_ativas.filter(situacao=Situacao.ESTADO_SUSPENSO).count()
    total_demandas = Demanda.objects.exclude(situacao=Situacao.ESTADO_CANCELADO).count()
    demandas_atrasadas_demandantes = 0
    demandas_atrasadas_desenvolvimento = 0
    for atrasada in demandas_ativas:
        historico_situacao = atrasada.get_ultimo_historico_situacao()
        if historico_situacao.data_previsao:
            hoje = date.today()
            historico_situacao = atrasada.get_ultimo_historico_situacao()
            if historico_situacao.data_previsao < hoje and not historico_situacao.data_conclusao:
                if atrasada.situacao in [Situacao.ESTADO_EM_ANALISE, Situacao.ESTADO_EM_HOMOLOGACAO]:
                    demandas_atrasadas_demandantes += 1
                elif atrasada.situacao in [Situacao.ESTADO_EM_DESENVOLVIMENTO, Situacao.ESTADO_EM_IMPLANTACAO]:
                    demandas_atrasadas_desenvolvimento += 1

    # Demandas Prioritárias
    total_demandas_prioritarias = demandas_ativas.filter(prioridade__lte=5).count()
    prioritarias = []
    areas = AreaAtuacaoDemanda.objects.all().order_by('area__nome')
    for area in areas:
        total_demandas_area = demandas_ativas.filter(area=area, prioridade__gte=0).order_by('prioridade')
        demandas_prioritarias = total_demandas_area[:5]
        if demandas_prioritarias.exists():
            qtd_demandas_concluidas_area = demandas_concluidas_ano.filter(area=area).count()
            prioritarias.append([area, demandas_prioritarias, 5 - demandas_prioritarias.count(), qtd_demandas_concluidas_area, total_demandas_area.count(), area.demandante_responsavel])

    return locals()


@rtr()
@permission_required('demandas.pode_relatorio')
def indicadores(request):
    title = 'Indicadores'
    form = DashboardForm(request.POST or None)
    demandas = Demanda.objects.all()
    demandas_ativas = Demanda.objects.ativas()
    demandas_em_andamento = Demanda.objects.em_andamento()
    demandas_aguardando_feedback = Demanda.objects.aguardando_feedback()
    atualizacoes = Atualizacao.objects.all()
    lista_desenvolvedores = UsuarioGrupo.objects.filter(group__name='Desenvolvedor')
    form_tag = None

    if form.is_valid():
        inicio = None
        if 'inicio' in form.cleaned_data and form.cleaned_data['inicio']:
            inicio = form.cleaned_data['inicio']

        final = None
        if 'final' in form.cleaned_data and form.cleaned_data['final']:
            final = form.cleaned_data['final']

        if inicio or final:
            if inicio and not final:
                demandas = demandas.filter(data_atualizacao__gte=inicio)
                demandas_ativas = demandas_ativas.filter(data_atualizacao__gte=inicio)
                demandas_em_andamento = demandas_em_andamento.filter(data_atualizacao__gte=inicio)
                demandas_aguardando_feedback = demandas_aguardando_feedback.filter(data_atualizacao__gte=inicio)
                atualizacoes = atualizacoes.filter(data__gte=inicio)
            elif final and not inicio:
                demandas = demandas.filter(data_atualizacao__lte=final)
                demandas_ativas = demandas_ativas.filter(data_atualizacao__lte=final)
                demandas_em_andamento = demandas_em_andamento.filter(data_atualizacao__lte=final)
                demandas_aguardando_feedback = demandas_aguardando_feedback.filter(data_atualizacao__lte=final)
                atualizacoes = atualizacoes.filter(data__lte=final)
            else:
                demandas = demandas.filter(data_atualizacao__range=(inicio, final))
                demandas_ativas = demandas_ativas.filter(data_atualizacao__range=(inicio, final))
                demandas_em_andamento = demandas_em_andamento.filter(data_atualizacao__range=(inicio, final))
                demandas_aguardando_feedback = demandas_aguardando_feedback.filter(data_atualizacao__range=(inicio, final))
                atualizacoes = atualizacoes.filter(data__range=(inicio, final))

        if 'tag' in form.cleaned_data and form.cleaned_data['tag']:
            form_tag = form.cleaned_data['tag']
            demandas = demandas.filter(tags=form_tag)
            demandas_ativas = demandas_ativas.filter(tags=form_tag)
            demandas_em_andamento = demandas_em_andamento.filter(tags=form_tag)
            demandas_aguardando_feedback = demandas_aguardando_feedback.filter(tags=form_tag)
            atualizacoes = atualizacoes.filter(tags=form_tag)

    # Gráfico com as situações das demandas
    dados_grafico_demandas_por_situacao = list()
    for demanda in demandas.order_by('situacao').values('situacao').annotate(Count('situacao')):
        dados_grafico_demandas_por_situacao.append([demanda['situacao'], demanda['situacao__count']])
    grafico_demandas_por_situacao = PieChart(
        'grafico_demandas_por_situacao', title='Demandas por Etapa', subtitle='Quantitativo de Demandas', minPointLength=0, data=dados_grafico_demandas_por_situacao
    )

    # Gráfico com demandas por tags
    dados_grafico_demandas_por_tags = list()
    tags = Tag.objects.filter(demanda_tags_set__in=demandas).annotate(qtd=Count('demanda_tags_set'))
    for tag in tags:
        dados_grafico_demandas_por_tags.append([tag.nome, tag.qtd])
    grafico_demandas_por_tags = PieChart(
        'grafico_demandas_por_tags', title='Demandas por Tags', subtitle='Quantitativo de Demandas', minPointLength=0, data=dados_grafico_demandas_por_tags
    )

    # Gráfico com as situações por área de atuação de demandas
    grupos_situacoes = [
        Situacao.ESTADO_ABERTO,
        Situacao.ESTADO_EM_NEGOCIACAO,
        Situacao.ESTADO_EM_ANALISE,
        Situacao.ESTADO_APROVADO,
        Situacao.ESTADO_EM_DESENVOLVIMENTO,
        Situacao.ESTADO_EM_HOMOLOGACAO,
        Situacao.ESTADO_HOMOLOGADA,
        Situacao.ESTADO_EM_IMPLANTACAO,
        Situacao.ESTADO_CONCLUIDO,
        Situacao.ESTADO_SUSPENSO,
        Situacao.ESTADO_CANCELADO,
    ]
    dict_situacao_por_area = dict()
    for demanda in demandas.order_by('area__area__nome'):
        if demanda.area:
            if demanda.area.area.nome not in dict_situacao_por_area:
                order = OrderedDict()
                order['nome'] = demanda.area.area.nome
                order[Situacao.ESTADO_ABERTO] = 0
                order[Situacao.ESTADO_EM_NEGOCIACAO] = 0
                order[Situacao.ESTADO_EM_ANALISE] = 0
                order[Situacao.ESTADO_APROVADO] = 0
                order[Situacao.ESTADO_EM_DESENVOLVIMENTO] = 0
                order[Situacao.ESTADO_EM_HOMOLOGACAO] = 0
                order[Situacao.ESTADO_HOMOLOGADA] = 0
                order[Situacao.ESTADO_EM_IMPLANTACAO] = 0
                order[Situacao.ESTADO_CONCLUIDO] = 0
                order[Situacao.ESTADO_SUSPENSO] = 0
                order[Situacao.ESTADO_CANCELADO] = 0
                dict_situacao_por_area[demanda.area.area.nome] = order

            dict_situacao_por_area[demanda.area.area.nome][demanda.situacao] += 1

    grafico_situacoes_por_tags = GroupedColumnChart(
        'grafico_situacoes_por_tags',
        title='Etapas por Áreas de Atuação',
        subtitle='Quantitativo de Demandas',
        data=[list(lista.values()) for lista in list(dict_situacao_por_area.values())],
        groups=grupos_situacoes,
        plotOptions_line_dataLabels_enable=True,
        plotOptions_line_enableMouseTracking=True,
    )

    # Gráfico com as força de trabalho dos analistas
    dados_grafico_analista = list()
    grupos_situacoes = [
        Situacao.ESTADO_ABERTO,
        Situacao.ESTADO_EM_NEGOCIACAO,
        Situacao.ESTADO_EM_ANALISE,
        Situacao.ESTADO_APROVADO,
        Situacao.ESTADO_EM_DESENVOLVIMENTO,
        Situacao.ESTADO_EM_HOMOLOGACAO,
        Situacao.ESTADO_HOMOLOGADA,
        Situacao.ESTADO_EM_IMPLANTACAO,
        Situacao.ESTADO_CONCLUIDO,
        Situacao.ESTADO_SUSPENSO,
        Situacao.ESTADO_CANCELADO,
    ]
    dict_analistas = dict()
    for demanda in demandas.order_by('analistas__username'):
        for analista in demanda.analistas.all():
            if analista.username not in dict_analistas:
                order = OrderedDict()
                order['nome'] = analista.pessoafisica.nome_usual
                order[Situacao.ESTADO_ABERTO] = 0
                order[Situacao.ESTADO_EM_NEGOCIACAO] = 0
                order[Situacao.ESTADO_EM_ANALISE] = 0
                order[Situacao.ESTADO_APROVADO] = 0
                order[Situacao.ESTADO_EM_DESENVOLVIMENTO] = 0
                order[Situacao.ESTADO_EM_HOMOLOGACAO] = 0
                order[Situacao.ESTADO_HOMOLOGADA] = 0
                order[Situacao.ESTADO_EM_IMPLANTACAO] = 0
                order[Situacao.ESTADO_CONCLUIDO] = 0
                order[Situacao.ESTADO_SUSPENSO] = 0
                order[Situacao.ESTADO_CANCELADO] = 0
                dict_analistas[analista.username] = order

            dict_analistas[analista.username][demanda.situacao] += 1

    dados_grafico_analistas = GroupedColumnChart(
        'div_grafico_analistas',
        title='Etapas por Analistas',
        subtitle='Quantitativo de Demandas',
        data=[list(lista.values()) for lista in list(dict_analistas.values())],
        groups=grupos_situacoes,
        plotOptions_line_dataLabels_enable=True,
        plotOptions_line_enableMouseTracking=True,
    )

    # Monta força tarefa - Desenvolvedores
    grafico_desenvolvedores = dict()
    dict_desenvolvedores = dict()

    for demanda in demandas.order_by('desenvolvedores__username'):
        for desenvolvedor in demanda.desenvolvedores.all():
            if desenvolvedor.username not in dict_desenvolvedores:
                order = OrderedDict()
                order['nome'] = desenvolvedor.pessoafisica.nome_usual
                order[Situacao.ESTADO_ABERTO] = 0
                order[Situacao.ESTADO_EM_NEGOCIACAO] = 0
                order[Situacao.ESTADO_EM_ANALISE] = 0
                order[Situacao.ESTADO_APROVADO] = 0
                order[Situacao.ESTADO_EM_DESENVOLVIMENTO] = 0
                order[Situacao.ESTADO_EM_HOMOLOGACAO] = 0
                order[Situacao.ESTADO_HOMOLOGADA] = 0
                order[Situacao.ESTADO_EM_IMPLANTACAO] = 0
                order[Situacao.ESTADO_CONCLUIDO] = 0
                order[Situacao.ESTADO_SUSPENSO] = 0
                order[Situacao.ESTADO_CANCELADO] = 0
                dict_desenvolvedores[desenvolvedor.username] = order

            dict_desenvolvedores[desenvolvedor.username][demanda.situacao] += 1

    dados_grafico_desenvolvedores = GroupedColumnChart(
        'div_grafico_desenvolvedores',
        title='Etapas por Desenvolvedores',
        subtitle='Quantitativo de Demandas',
        data=[list(lista.values()) for lista in list(dict_desenvolvedores.values())],
        groups=grupos_situacoes,
        plotOptions_line_dataLabels_enable=True,
        plotOptions_line_enableMouseTracking=True,
    )

    # Gráficos de Atualizações
    dados_grafico_tags = list()
    tags = Tag.objects.filter(atualizacao__in=atualizacoes).annotate(qtd=Count('atualizacao'))
    for tag in tags:
        dados_grafico_tags.append([tag.nome, tag.qtd])
    grafico_tags = PieChart('grafico_tags', title='Quantitativo de Atualizações por Tags', minPointLength=0, data=dados_grafico_tags)

    dados_grafico_tipos = []
    tags = Tag.objects.filter(id__in=atualizacoes.values_list('tags', flat=True))
    for tag in tags:
        serie = [
            tag.nome,
            atualizacoes.filter(tags=tag, tipo=Atualizacao.FUNCIONALIDADE).count(),
            atualizacoes.filter(tags=tag, tipo=Atualizacao.MANUTENCAO).count(),
            atualizacoes.filter(tags=tag, tipo=Atualizacao.BUG).count(),
        ]
        dados_grafico_tipos.append(serie)

    grafico_tipos = GroupedColumnChart(
        'grafico_tipos',
        title='Tipo por Tags',
        subtitle='Quantitativo de Atualizações',
        data=dados_grafico_tipos,
        groups=[Atualizacao.FUNCIONALIDADE, Atualizacao.MANUTENCAO, Atualizacao.BUG],
        plotOptions_line_dataLabels_enable=True,
        plotOptions_line_enableMouseTracking=True,
    )

    if not form_tag:
        dados_grafico_tipo_funcionalidade = list()
        qs = atualizacoes.filter(tipo=Atualizacao.FUNCIONALIDADE)
        tags = Tag.objects.filter(atualizacao__in=qs).annotate(qtd=Count('atualizacao'))
        for tag in tags:
            dados_grafico_tipo_funcionalidade.append([tag.nome, tag.qtd])
        grafico_tipo_funcionalidade = PieChart(
            'grafico_tipo_funcionalidade', title='Quantitativo de Atualizações de Funcionalidades', minPointLength=0, data=dados_grafico_tipo_funcionalidade
        )

        dados_grafico_tipo_manutencao = list()
        qs = atualizacoes.filter(tipo=Atualizacao.MANUTENCAO)
        tags = Tag.objects.filter(atualizacao__in=qs).annotate(qtd=Count('atualizacao'))
        for tag in tags:
            dados_grafico_tipo_manutencao.append([tag.nome, tag.qtd])
        grafico_tipo_manutencao = PieChart('grafico_tipo_manutencao', title='Quantitativo de Atualizações de Manutenção', minPointLength=0, data=dados_grafico_tipo_manutencao)

        dados_grafico_tipo_bug = list()
        qs = atualizacoes.filter(tipo=Atualizacao.BUG)
        tags = Tag.objects.filter(atualizacao__in=qs).annotate(qtd=Count('atualizacao'))
        for tag in tags:
            dados_grafico_tipo_bug.append([tag.nome, tag.qtd])
        grafico_tipo_bug = PieChart('grafico_tipo_bug', title='Quantitativo de Atualizações de Bugs', minPointLength=0, data=dados_grafico_tipo_bug)

    return locals()


@rtr()
@permission_required('demandas.pode_relatorio')
def relatorio_geral(request):
    title = 'Relatório de Demandas por Tags (XLS)'

    form = RelatorioForm(request.POST or None)

    if form.is_valid():
        dt_inicio = form.cleaned_data['inicio']
        dt_final = form.cleaned_data['final']

        demandas = Demanda.objects.filter(data_atualizacao__gte=dt_inicio).filter(data_atualizacao__lte=dt_final)

        tags_dict = dict()
        situacao_dict = dict()

        for demanda in demandas:
            for tag in demanda.tags.all():
                if tag.nome not in tags_dict:
                    sit_dict = OrderedDict()
                    sit_dict[Situacao.ESTADO_ABERTO] = 0
                    sit_dict[Situacao.ESTADO_EM_NEGOCIACAO] = 0
                    sit_dict[Situacao.ESTADO_EM_ANALISE] = 0
                    sit_dict[Situacao.ESTADO_APROVADO] = 0
                    sit_dict[Situacao.ESTADO_EM_DESENVOLVIMENTO] = 0
                    sit_dict[Situacao.ESTADO_EM_HOMOLOGACAO] = 0
                    sit_dict[Situacao.ESTADO_EM_IMPLANTACAO] = 0
                    sit_dict[Situacao.ESTADO_CONCLUIDO] = 0
                    sit_dict[Situacao.ESTADO_SUSPENSO] = 0
                    sit_dict[Situacao.ESTADO_CANCELADO] = 0
                    tags_dict[tag.nome] = {'qtd': 0, 'situacao': sit_dict}
                tags_dict[tag.nome]['qtd'] += 1

                if demanda.situacao not in tags_dict[tag.nome]['situacao']:
                    tags_dict[tag.nome]['situacao'][demanda.situacao] = 0

                tags_dict[tag.nome]['situacao'][demanda.situacao] += 1

        wb = xlwt.Workbook(encoding='iso8859-1')
        sheet = wb.add_sheet('Demandas por Tags')

        sheet.write(0, 0, 'Relatório de Demandas por Tags')
        sheet.write(1, 0, 'A demanda porde ter mais de uma tag')
        sheet.write(2, 0, f'Número de demandas no período de {dt_inicio} a {dt_final}:')
        sheet.write(2, 1, demandas.count())

        sheet.write(4, 0, 'Tag')
        sheet.write(4, 1, 'Total')
        sheet.write(4, 2, Situacao.ESTADO_ABERTO)
        sheet.write(4, 3, Situacao.ESTADO_EM_NEGOCIACAO)
        sheet.write(4, 4, Situacao.ESTADO_EM_ANALISE)
        sheet.write(4, 5, Situacao.ESTADO_APROVADO)
        sheet.write(4, 6, Situacao.ESTADO_EM_DESENVOLVIMENTO)
        sheet.write(4, 7, Situacao.ESTADO_EM_HOMOLOGACAO)
        sheet.write(4, 8, Situacao.ESTADO_EM_IMPLANTACAO)
        sheet.write(4, 9, Situacao.ESTADO_CONCLUIDO)
        sheet.write(4, 10, Situacao.ESTADO_SUSPENSO)
        sheet.write(4, 11, Situacao.ESTADO_CANCELADO)

        linha = 0

        for tag, dados in list(tags_dict.items()):
            sheet.write(5 + linha, 0, tag)
            sheet.write(5 + linha, 1, dados['qtd'])
            col = 0
            for key, situacao in list(dados['situacao'].items()):
                sheet.write(5 + linha, 2 + col, situacao)
                col += 1

            linha += 1

        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=DisponibilidadeGeral.xls'

        wb.save(response)

        return response

    return locals()


@rtr()
@login_required()
def atualizacao(request, atualizacao_id):
    atualizacao = get_object_or_404(Atualizacao, pk=atualizacao_id)
    title = f"Atualização #{atualizacao.pk}"

    eh_analista = in_group(request.user, 'Analista')
    eh_desenvolvedor = in_group(request.user, 'Desenvolvedor')

    # Monta a lista de Atualizacoes Relacionadas aos mesmos grupos da Atualizacao Atual
    grupos = atualizacao.grupos.all().values_list('id', flat=True)
    relacionadas = Atualizacao.objects.filter(grupos__in=grupos).exclude(pk=atualizacao.pk)[:5]

    # Monta a lista com as quantidades de bugs, manutencoes e funcionalidades de atualizacoes que tenham as mesmas tags da Atualizacao Atual
    tags = atualizacao.tags.all().values_list('id', flat=True)
    lista_tags = Tag.objects.filter(pk__in=tags)
    lista = []
    for tag in lista_tags:
        bugs = Atualizacao.objects.filter(tags=tag, tipo=Atualizacao.BUG).count()
        manutencoes = Atualizacao.objects.filter(tags=tag, tipo=Atualizacao.MANUTENCAO).count()
        funcionalidades = Atualizacao.objects.filter(tags=tag, tipo=Atualizacao.FUNCIONALIDADE).count()
        lista.append([tag, tag.pk, bugs, manutencoes, funcionalidades])

    return locals()


@rtr()
def atualizacoes(request):
    title = 'Atualizações do Sistema'
    category = 'Consultas'
    icon = 'file-contract'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)

    atualizacoes = Atualizacao.objects.all().order_by('-data')

    return locals()


@rtr()
@login_required()
def demandas_prioritarias_por_area(request, pk_area):
    area = get_object_or_404(AreaAtuacaoDemanda, pk=pk_area)
    title = f'Demandas Prioritárias pela Área: {area}'
    if not request.user.demandanteresponsavelarea.filter(area=area.area).exists() and not request.user.is_superuser:
        raise PermissionDenied('Você não tem permissão para visualizar esta página.')
    demandas = Demanda.objects.ativas().filter(area=area).order_by('prioridade')

    return locals()


@csrf_exempt
@login_required()
def atualizar_prioridade(request, area_id):
    area = get_object_or_404(AreaAtuacaoDemanda, pk=area_id)
    if not request.user.demandanteresponsavelarea.filter(area=area.area).exists() and not request.user.is_superuser:
        raise PermissionDenied('Você não tem permissão para visualizar esta página.')

    demandas = request.GET.get('demandas').split(',')
    for count, demanda in enumerate(demandas, start=1):
        demanda = get_object_or_404(Demanda, pk=demanda, area=area)
        if demanda.prioridade != count:
            demanda.prioridade = count
            Demanda.criar_historico_prioridade(demanda, request.user, count)
            demanda.save()

    return JsonResponse({'ok': True})


@rtr()
@login_required()
def atualizar_prioridade_manualmente(request, demanda_id):
    title = 'Alterar prioridade'

    demanda_nova_prioridade = get_object_or_404(Demanda, pk=demanda_id)

    if not request.user.demandanteresponsavelarea.filter(area=demanda_nova_prioridade.area.area).exists() and not request.user.is_superuser:
        raise PermissionDenied('Você não tem permissão para visualizar esta página.')

    form = NovaPrioridadeDemandaForm(request.POST or None)
    if form.is_valid():

        nova_prioridade = form.cleaned_data.get('nova_prioridade')
        demandas = Demanda.objects.ativas().filter(area=demanda_nova_prioridade.area).exclude(id=demanda_nova_prioridade.id).order_by('prioridade')

        # Criando nova lista ordenada
        nova_lista_ordenada = list()
        ordem = 1
        for dem in demandas:
            if ordem == nova_prioridade:
                nova_lista_ordenada.append(demanda_nova_prioridade)
                nova_lista_ordenada.append(dem)
                nova_prioridade = 0
            else:
                nova_lista_ordenada.append(dem)
            ordem += 1
        if nova_prioridade > 0:
            nova_lista_ordenada.append(demanda_nova_prioridade)

        # Atualizando a ordem das demandas
        ordem = 1
        for dem in nova_lista_ordenada:
            dem.prioridade = ordem
            dem.save()
            Demanda.criar_historico_prioridade(dem, request.user, ordem)
            ordem += 1

        return httprr('..', 'Gerenciamento salvo com sucesso.')

    return locals()


@rtr()
@permission_required('demandas.add_sugestaomelhoria')
def listar_areas_atuacao_sugestao_melhoria(request):
    title = 'Sugestões de Melhorias para o SUAP'
    areas_atuacao = AreaAtuacaoDemanda.areas_recebem_sugestoes()
    return locals()


@rtr()
@permission_required('demandas.add_sugestaomelhoria')
def sugestoes_modulo(request, area_atuacao_id, modulo_id):
    area_atuacao = get_object_or_404(AreaAtuacaoDemanda, pk=area_atuacao_id)
    modulo = get_object_or_404(Tag, pk=modulo_id)

    title = f'Sugestões de Melhorias para {modulo} ({area_atuacao})'

    sugestoes = SugestaoMelhoria.objects.filter(area_atuacao=area_atuacao, tags=modulo)
    sugestoes_ativas = sugestoes.exclude(situacao__in=[SugestaoMelhoria.SITUACAO_DEFERIDA, SugestaoMelhoria.SITUACAO_CANCELADA, SugestaoMelhoria.SITUACAO_INDEFERIDA]).order_by('situacao', '-votos')
    sugestoes_deferidas = sugestoes.filter(situacao=SugestaoMelhoria.SITUACAO_DEFERIDA).count()
    sugestoes_indeferidas = sugestoes.filter(situacao=SugestaoMelhoria.SITUACAO_INDEFERIDA).count()
    sugestoes_implementadas = sugestoes.filter(situacao=SugestaoMelhoria.SITUACAO_DEFERIDA, demanda_gerada__situacao=Situacao.ESTADO_CONCLUIDO).count()

    return locals()


@rtr()
@permission_required('demandas.add_sugestaomelhoria')
def adicionar_sugestao_melhoria(request, area_atuacao_id):
    area_atuacao = get_object_or_404(AreaAtuacaoDemanda, pk=area_atuacao_id)

    tags_ids = request.GET.get('tags_ids', '')
    tags = [get_object_or_404(Tag, pk=tag_id) for tag_id in tags_ids.split(',') if tag_id]

    if tags:
        area_atuacao_tags_relacionadas = area_atuacao.tags_relacionadas.all()
        for tag in tags:
            if tag not in area_atuacao_tags_relacionadas:
                raise Exception('A Tag "{}" não está relacionada à Área de Atuação "{}".'.format(
                    tag, area_atuacao
                ))
    else:
        raise Exception('Nenhuma Tag foi selecionada.')

    title = 'Adicionar Sugestão de Melhoria'

    form = SugestaoMelhoriaAddForm(
        request.POST or None,
        area_atuacao=area_atuacao,
        tags=tags,
        user_requisitante=request.user
    )

    if form.is_valid():
        sugestao_salva = form.save()
        if sugestao_salva:
            Notificar.nova_sugestao_melhoria(sugestao_salva)
            return httprr(sugestao_salva.get_absolute_url(), 'Sugestão de Melhoria salva com sucesso.')

    return locals()


@rtr()
@login_required()
def sugestao_melhoria(request, sugestao_melhoria_id):
    sugestao_melhoria = get_object_or_404(SugestaoMelhoria, pk=sugestao_melhoria_id)
    usuario = request.user
    title = f'Sugestão de Melhoria #{sugestao_melhoria.pk}: {sugestao_melhoria.titulo}'

    voto = SugestaoVoto.objects.filter(sugestao=sugestao_melhoria, usuario=usuario)
    if voto.exists():
        voto = voto[0]
    else:
        voto = None

    pode_editar_dados_basicos = sugestao_melhoria.pode_editar_dados_basicos(usuario)
    pode_editar_todos_dados = sugestao_melhoria.pode_editar_todos_dados(usuario)
    pode_gerar_demanda = sugestao_melhoria.pode_gerar_demanda(usuario)
    pode_visualizar_demanda_gerada = sugestao_melhoria.pode_visualizar_demanda_gerada(usuario)
    pode_excluir_demanda_gerada = sugestao_melhoria.pode_excluir_demanda_gerada(usuario)
    eh_usuario_ti = SugestaoMelhoria.eh_usuario_ti(usuario)
    eh_interessado = usuario in sugestao_melhoria.interessados.all()
    eh_requisitante = sugestao_melhoria.eh_requisitante(usuario)
    is_responsavel_ou_demandante = sugestao_melhoria.is_responsavel_ou_demandante(usuario)
    pode_visualizar_comentario = sugestao_melhoria.pode_visualizar_comentario(usuario)
    pode_registrar_comentario = sugestao_melhoria.pode_registrar_comentario(usuario)

    qtd_comentarios = Comentario.objects.filter(
        content_type=ContentType.objects.get(
            app_label=sugestao_melhoria._meta.app_label,
            model=sugestao_melhoria._meta.model_name),
        object_id=sugestao_melhoria.pk,
        resposta=None
    ).count()

    return locals()


@rtr()
@login_required()
def concordar_sugestao(request, sugestao_melhoria_id):
    sugestao = get_object_or_404(SugestaoMelhoria, pk=sugestao_melhoria_id)

    if sugestao.pode_votar():
        sugestao_voto = SugestaoVoto.objects.filter(sugestao=sugestao, usuario=request.user)
        if sugestao_voto.exists():
            voto = sugestao_voto[0]
        else:
            voto = SugestaoVoto()
            voto.sugestao = sugestao

        voto.concorda = True
        voto.save()

        return httprr(sugestao.get_absolute_url(), 'Voto cadastrado com sucesso.', 'success')
    else:
        return httprr(sugestao.get_absolute_url(), 'Não foi possível votar nesta sugestão', 'error')


@rtr()
@login_required()
def discordar_sugestao(request, sugestao_melhoria_id):
    sugestao = get_object_or_404(SugestaoMelhoria, pk=sugestao_melhoria_id)

    if sugestao.pode_votar():
        sugestao_voto = SugestaoVoto.objects.filter(sugestao=sugestao, usuario=request.user)
        if sugestao_voto.exists():
            voto = sugestao_voto[0]
        else:
            voto = SugestaoVoto()
            voto.sugestao = sugestao

        voto.concorda = False
        voto.save()

        return httprr(sugestao.get_absolute_url(), 'Voto cadastrado com sucesso.', 'success')
    else:
        return httprr(sugestao.get_absolute_url(), 'Não foi possível votar nesta sugestão', 'error')


@rtr()
@login_required()
def tornar_se_interessado(request, sugestao_melhoria_id):
    sugestao = get_object_or_404(SugestaoMelhoria, pk=sugestao_melhoria_id)
    usuario = request.user

    if usuario in sugestao.interessados.all():
        raise PermissionDenied('Você já é Interessado desta sugestão de melhoria.')

    if sugestao.eh_requisitante(usuario):
        raise PermissionDenied('Você já é o Requisitante desta sugestão de melhoria.')

    sugestao.interessados.add(usuario)
    sugestao.save()

    return httprr(sugestao.get_absolute_url(), 'Você foi incluído como Interessado desta sugestão.')


@rtr()
@login_required()
def alterar_situacao_sugestao(request, sugestao_melhoria_id, situacao):
    obj = SugestaoMelhoria.objects.get(pk=sugestao_melhoria_id)
    if obj.is_responsavel(request.user):
        obj.situacao = situacao
        obj.save()
        return httprr(obj.get_absolute_url(), 'Etapa alterada com sucesso.')
    return httprr(obj.get_absolute_url(), 'Somente o responsável pela sugestão pode alterar a etapa.', 'error')


def _editar_dados_sugestao_melhoria_processar_form(user, sugestao_melhoria, form):
    sugestao_melhoria_situacao_anterior = sugestao_melhoria.situacao
    if form.is_valid():
        sugestao_salva = form.save()
        if sugestao_salva:
            if form.cleaned_data.get('modulo'):
                sugestao_salva.tags.clear()
                sugestao_salva.tags.add(form.cleaned_data.get('modulo'))
            situacao_alterada = sugestao_salva.situacao != sugestao_melhoria_situacao_anterior
            if situacao_alterada:
                Notificar.nova_situacao_em_sugestao_melhoria(sugestao_salva, user)
            return httprr(sugestao_melhoria.get_absolute_url(), 'Sugestão de Melhoria salva com sucesso.')
    return None


@rtr()
@login_required()
def editar_dados_basicos_sugestao_melhoria(request, sugestao_melhoria_id):
    sugestao_melhoria = get_object_or_404(SugestaoMelhoria, pk=sugestao_melhoria_id)

    title = f'Editar Sugestão de Melhoria (Área de Atuação: {sugestao_melhoria.area_atuacao.area.nome})'

    if not sugestao_melhoria.pode_editar_dados_basicos(request.user):
        raise PermissionDenied('Você não tem permissão para editar a sugestão de melhoria.')

    form = SugestaoMelhoriaEdicaoBasicaForm(request.POST or None, instance=sugestao_melhoria)

    return _editar_dados_sugestao_melhoria_processar_form(request.user, sugestao_melhoria, form) or locals()


@rtr()
@login_required()
def editar_todos_dados_sugestao_melhoria(request, sugestao_melhoria_id):
    sugestao_melhoria = get_object_or_404(SugestaoMelhoria, pk=sugestao_melhoria_id)

    title = f'Editar Sugestão de Melhoria (Área de Atuação: {sugestao_melhoria.area_atuacao.area.nome})'

    if not sugestao_melhoria.pode_editar_todos_dados(request.user):
        raise PermissionDenied('Você não tem permissão para editar a sugestão de melhoria.')

    form = SugestaoMelhoriaEdicaoCompletaForm(request.POST or None, instance=sugestao_melhoria)

    return _editar_dados_sugestao_melhoria_processar_form(request.user, sugestao_melhoria, form) or locals()


@rtr()
@permission_required('comum.is_coordenador_de_sistemas')
def editar_area_atuacao(request, sugestao_melhoria_id):
    sugestao_melhoria = get_object_or_404(SugestaoMelhoria, pk=sugestao_melhoria_id)

    title = f'Editar Área de Atuação da Sugestão de Melhoria #{sugestao_melhoria_id}'

    form = SugestaoMelhoriaEdicaoAreaAtuacaoForm(request.POST or None, instance=sugestao_melhoria)

    if form.is_valid():
        form.save()
        return httprr(sugestao_melhoria.get_absolute_url(), 'Sugestão de Melhoria salva com sucesso.')

    return locals()


@rtr()
@login_required()
def atribuir_se_como_responsavel_sugestao_melhoria(request, sugestao_melhoria_id):
    sugestao_melhoria = get_object_or_404(SugestaoMelhoria, pk=sugestao_melhoria_id)

    if not sugestao_melhoria.pode_editar_todos_dados(request.user):
        raise PermissionDenied('Você não tem permissão para editar a sugestão de melhoria.')

    url_visualizar = sugestao_melhoria.get_absolute_url()

    try:
        situacao_alterada = False

        if not sugestao_melhoria.is_em_analise:
            sugestao_melhoria.situacao = SugestaoMelhoria.SITUACAO_EM_ANALISE
            situacao_alterada = True

        sugestao_melhoria.responsavel = request.user
        sugestao_melhoria.save()

        if sugestao_melhoria.responsavel:
            if situacao_alterada:
                Notificar.nova_situacao_em_sugestao_melhoria(sugestao_melhoria, request.user)

            return httprr(url_visualizar, 'Responsável definido com sucesso.')
        else:
            erro = Exception('Ocorreu um erro ao definir o responsável.')
    except Exception as e:
        erro = e

    return httprr(url_visualizar, f'{erro}', 'error')


@rtr()
@login_required()
def gerar_demanda_sugestao_melhoria(request, sugestao_melhoria_id):
    sugestao_melhoria = get_object_or_404(SugestaoMelhoria, pk=sugestao_melhoria_id)

    if not sugestao_melhoria.pode_gerar_demanda(request.user):
        raise PermissionDenied('Você não tem permissão para gerar a demanda para esta sugestão de melhoria.')

    url_visualizar = sugestao_melhoria.get_absolute_url()

    try:
        sugestao_melhoria.gerar_demanda(request.user)
        if sugestao_melhoria.demanda_gerada:
            return httprr(url_visualizar, 'Demanda gerada com sucesso.')
        else:
            erro = Exception('Ocorreu um erro ao gerar a demanda.')
    except Exception as e:
        erro = e

    return httprr(url_visualizar, f'{erro}', 'error')


@permission_required('demandas.add_ambientehomologacao')
def analistadesenvolvedor(request, pk):
    obj = get_object_or_404(AnalistaDesenvolvedor, pk=pk)
    title = str(obj)
    action = request.GET.get('action')
    if action:
        url = f'/demandas/analistadesenvolvedor/{pk}/'
        if action == 'deploy':
            return tasks.criar_atualizar_ide(obj, url)
        elif action == 'log':
            return HttpResponse(obj.get_log_ide_cricao_atualizacao_ide())
        elif action == 'undeploy':
            obj.excluir_ide()
            return httprr(url, 'Ambiente excluído provisoriamente com sucesso')
        elif action == 'destroy':
            obj.destruir_ide()
            return httprr(url, 'Ambiente e base de dados excluídos com sucesso')
    return locals()


@rtr()
@permission_required('demandas.add_ambientehomologacao')
def ambientehomologacao(request, pk):
    obj = get_object_or_404(AmbienteHomologacao, pk=pk)
    title = str(obj)
    action = request.GET.get('action')
    if action:
        url = f'/demandas/ambientehomologacao/{pk}/'
        if action == 'deploy':
            return tasks.criar_atualizar_container(obj, url)
        elif action == 'undeploy':
            obj.excluir_container()
            return httprr(url, 'Ambiente excluído provisoriamente com sucesso')
        elif action == 'destroy':
            obj.destruir()
            return httprr(url, 'Ambiente e base de dados excluídos com sucesso')
    return locals()


@permission_required('demandas.view_demanda')
def acessar_ambiente_via_demanda(request, pk, demanda_pk):
    obj = get_object_or_404(AmbienteHomologacao, pk=pk)
    if not obj.ativo:
        url = obj.get_url_homologacao()
        return tasks.criar_atualizar_container(obj, url)
    return HttpResponseRedirect(f'/demandas/visualizar/{demanda_pk}/?tab=homologacao')


@rtr()
@permission_required('demandas.add_ambientehomologacao')
def executar_comando_ambiente_homologacao(request, pk):
    title = 'Executar Comando'
    obj = get_object_or_404(AmbienteHomologacao, pk=pk)
    form = ExecutarComandoForm(data=request.POST or None)
    if form.is_valid():
        log = obj.executar_comando(form.cleaned_data['comando'])
        return HttpResponse(log)
    return locals()
