import datetime
from typing import OrderedDict

from dateutil.relativedelta import relativedelta
from django.conf import settings
from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import connection
from django.db.models import Count, Max, Min, Sum, F, Avg
from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django_fsm import TransitionNotAllowed, has_transition_perm

from centralservicos.forms import (
    AtendimentosPorAnoForm,
    ChamadoFormFactory,
    ChamadoAnexoForm,
    AtendimentoAtribuicaoFormFactory,
    AdicionarOutrosInteressadosFormFactory,
    AlterarStatusChamadoFormFactory,
    BuscarChamadoUsuarioFormFactory,
    BuscarChamadoSuporteFormFactory,
    ComunicacaoFormFactory,
    BuscarArtigoFormFactory,
    ChamadoAnexoFormset,
    GraficosFormFactory,
    AtendentesFormFactory,
    BuscarServicoFormFactory,
    MarcarParaCorrecaoForm,
    AdicionarTagsAoChamadoFormFactory,
    ReclassificarChamadoFormFactory,
    AdicionarGrupoInteressadosFormFactory,
)
from centralservicos.models import (
    Servico,
    CategoriaServico,
    Chamado,
    Comunicacao,
    StatusChamado,
    GrupoAtendimento,
    AtendimentoAtribuicao,
    BaseConhecimento,
    HistoricoStatus,
    AvaliaBaseConhecimento,
    Tag,
    CentroAtendimento,
    PerguntaAvaliacaoBaseConhecimento,
    BaseConhecimentoAnexo,
    Monitoramento,
    RespostaPadrao,
    GrupoInteressado,
    GrupoServico,
)
from datetime import date
from centralservicos.utils import Notificar
from comum.models import User, AreaAtuacao
from comum.utils import Relatorio
from comum.utils import get_uo
from djtools import db
from djtools import layout
from djtools.choices import Meses
from djtools.html.graficos import LineChart, PieChart, ColumnChart
from djtools.templatetags.filters import in_group
from djtools.utils import rtr, httprr, login_required, permission_required, JsonResponse, generate_autocomplete_dict
from rh.models import UnidadeOrganizacional


@layout.quadro('Central de Serviços', icone='list', pode_esconder=True)
def index_quadros(quadro, request):
    if in_group(request.user, 'Atendente da Central de Serviços'):
        chamados_atribuidos_a_mim = Chamado.get_chamados_do_suporte(user=request.user, atribuicoes=Chamado.ATRIBUIDOS_A_MIM)
        if chamados_atribuidos_a_mim.exists():
            qtd = chamados_atribuidos_a_mim.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo='Chamado{}'.format(pluralize(qtd)),
                    subtitulo='Atribuído{} a mim'.format(pluralize(qtd)),
                    qtd=qtd,
                    url='/centralservicos/listar_chamados_suporte/?atribuicoes=1',
                )
            )
            prazo_dois_dias = datetime.date.today() + relativedelta(days=+2)
            vencendo_amanha = chamados_atribuidos_a_mim.filter(data_limite_atendimento__gt=datetime.datetime.now(), data_limite_atendimento__date__lt=prazo_dois_dias)
            if vencendo_amanha.exists():
                qtd = vencendo_amanha.count()
                quadro.add_item(
                    layout.ItemContador(
                        titulo='Chamado{}'.format(pluralize(qtd)),
                        subtitulo='Atribuído{} a mim com data limite para amanhã'.format(pluralize(qtd)),
                        qtd=qtd,
                        url='/centralservicos/listar_chamados_suporte/?atribuicoes=1',
                    )
                )
            vencidos = chamados_atribuidos_a_mim.filter(data_limite_atendimento__lt=datetime.datetime.now())
            if vencidos.exists():
                qtd = vencidos.count()
                quadro.add_item(
                    layout.ItemContador(
                        titulo='Chamado{}'.format(pluralize(qtd)),
                        subtitulo='Atrasado{0} atribuído{0} a mim'.format(pluralize(qtd)),
                        qtd=qtd,
                        url='/centralservicos/listar_chamados_suporte/?atribuicoes=1',
                    )
                )
        chamados_sem_atribuicao = Chamado.SEM_ATRIBUICAO
        qtd = Chamado.get_chamados_do_suporte(user=request.user, atribuicoes=Chamado.SEM_ATRIBUICAO).count()
        if qtd:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Novo{plural} Chamado{plural}'.format(plural=pluralize(qtd)),
                    subtitulo='Sem atribuição',
                    qtd=qtd,
                    url='/centralservicos/listar_chamados_suporte/?atribuicoes={}'.format(chamados_sem_atribuicao),
                )
            )

    quadro.add_item(layout.ItemAcessoRapido(titulo='Meus Chamados', url='/centralservicos/meus_chamados/?tab=ativos', icone='bars'))

    quadro.add_item(layout.ItemAcessoRapido(titulo='Abrir Chamado', url='/centralservicos/listar_area_servico/', icone='plus', classe='success'))

    quadro.add_item(layout.ItemAcessoRapido(titulo='Base de Conhecimentos', icone='question', url='/centralservicos/baseconhecimento/'))

    return quadro


@rtr('centralservicos/templates/listar_area_servico.html')
@permission_required(['centralservicos.view_chamado', 'centralservicos.change_chamado'])
def listar_area_servico(request):
    title = 'Listar Áreas do Serviço'
    title_box = 'Selecione a Área do Serviço para qual deseja abrir o chamado'
    link_prefix = '/centralservicos/selecionar_servico_abertura/'
    lista_areas = AreaAtuacao.objects.filter(ativo=True).distinct()
    return locals()


@rtr('centralservicos/templates/selecionar_servico_abertura_chamado.html')
@permission_required(['centralservicos.view_chamado', 'centralservicos.change_chamado'])
def selecionar_servico_abertura_chamado(request, slug):
    area = get_object_or_404(AreaAtuacao, slug=slug)
    if not area.ativo:
        raise PermissionDenied('Não é possível abrir um chamado para este serviço, pois a Área do Serviço não está ativa.')
    title = 'Abrir Chamado para {}'.format(area.nome)
    lista_categorias = CategoriaServico.objects.filter(area=area)

    if not request.user.has_perm('centralservicos.change_chamado'):
        servico_interno = False
        lista_categorias = CategoriaServico.objects.filter(area=area, gruposervico__servico__interno=servico_interno).distinct()
        FormClass = BuscarServicoFormFactory(request.user, area, servico_interno)
    else:
        lista_categorias = CategoriaServico.objects.filter(area=area).distinct()
        FormClass = BuscarServicoFormFactory(request.user, area)

    form = FormClass(request.POST or None)
    if form.is_valid():
        servico = form.cleaned_data.get('servico')
        if servico:
            return redirect(reverse('centralservicos_visualizar_solucoes', args=(servico.pk,)))
        else:
            return httprr('.', 'Selecione um serviço da lista.', tag='error')

    return locals()


@rtr('centralservicos/templates/listar_area_servico.html')
@permission_required(['centralservicos.view_baseconhecimento', 'centralservicos.add_chamado'])
def baseconhecimento_listar_area_servico(request):
    title = 'Listar Áreas do Serviço'
    title_box = 'Selecione a Área do Serviço para o qual deseja consultar Base de Conhecimento'
    link_prefix = '/centralservicos/baseconhecimento/dashboard/'
    if request.user.has_perm('centralservicos.view_baseconhecimento'):
        lista_areas = AreaAtuacao.objects.filter(ativo=True).distinct()
    else:
        # É usuario comum
        lista_areas = AreaAtuacao.objects.filter(
            ativo=True, servico__interno=False, servico__base_conhecimento_servicos_set__visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA
        ).distinct()

    return locals()


@rtr('centralservicos/templates/baseconhecimento.html')
@permission_required(['centralservicos.view_baseconhecimento', 'centralservicos.add_chamado'])
def baseconhecimento(request, slug):
    area = get_object_or_404(AreaAtuacao, slug=slug)
    if not area.ativo:
        raise PermissionDenied('Não é possível consultar Base de Conhecimento nesta área, pois a mesma não está ativa.')

    title = f'Base de Conhecimentos: {area.nome}'
    eh_atendente_desta_area = request.user.has_perm('centralservicos.view_baseconhecimento') and GrupoAtendimento.meus_grupos(request.user, area).exists()

    FormClass = BuscarArtigoFormFactory(request, eh_atendente_desta_area=eh_atendente_desta_area, area=area)
    form = FormClass(request.POST or None)
    if form.is_valid():
        baseconhecimento = form.cleaned_data.get('baseconhecimento')
        if baseconhecimento:
            return httprr('/centralservicos/baseconhecimento/{}/'.format(baseconhecimento.pk))
        else:
            return httprr('.', 'Selecione uma base da lista.', tag='error')

    if eh_atendente_desta_area:
        lista_categorias = CategoriaServico.objects.filter(
            pk__in=BaseConhecimento.objects.filter(ativo=True, servicos__grupo_servico__categorias__area=area).values('servicos__grupo_servico__categorias')
        ).distinct()
        qs = (
            HistoricoStatus.objects.filter(status=StatusChamado.get_status_resolvido(), bases_conhecimento__area=area, bases_conhecimento__ativo=True)
            .values('bases_conhecimento__id')
            .annotate(total=Count('bases_conhecimento__id'))
            .order_by('-total')[:5]
            .values('bases_conhecimento__id')
        )

        mais_populares = BaseConhecimento.objects.filter(id__in=qs)
        mais_populares = sorted(mais_populares, key=lambda t: t.get_quantidade_utilizacoes, reverse=True)
        ultimos_cadastrados = BaseConhecimento.objects.filter(area=area, ativo=True).order_by('-atualizado_em').distinct()[:5]
    else:
        lista_categorias = CategoriaServico.objects.filter(
            pk__in=BaseConhecimento.objects.filter(
                ativo=True, visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA, servicos__grupo_servico__categorias__area=area, servicos__interno=False
            ).values('servicos__grupo_servico__categorias')
        ).distinct()
        qs = (
            HistoricoStatus.objects.filter(
                status=StatusChamado.get_status_resolvido(),
                bases_conhecimento__ativo=True,
                bases_conhecimento__visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA,
                bases_conhecimento__area=area,
            )
            .values('bases_conhecimento__id')
            .annotate(total=Count('bases_conhecimento__id'))
            .order_by('-total')[:5]
            .values('bases_conhecimento__id')
        )

        mais_populares = BaseConhecimento.objects.filter(id__in=qs)
        mais_populares = sorted(mais_populares, key=lambda t: t.get_quantidade_utilizacoes, reverse=True)
        ultimos_cadastrados = BaseConhecimento.objects.filter(ativo=True, visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA, area=area).order_by('-atualizado_em').distinct()[:5]

    return locals()


@rtr('centralservicos/templates/visualizar_solucoes.html')
@permission_required('centralservicos.add_chamado')
def visualizar_solucoes(request, servico_id):
    servico = get_object_or_404(Servico, pk=servico_id)
    title = servico
    if not servico.tem_bases_conhecimento_publicas():
        url = '/centralservicos/abrir_chamado/{}/'.format(servico.id)
        return httprr(url)
    else:
        bases = list(servico.get_bases_conhecimento_faq())
        bases.sort(key=lambda x: (x.get_quantidade_utilizacoes), reverse=True)
    return locals()


@rtr('centralservicos/templates/form_abrir_chamado.html')
@permission_required(['centralservicos.add_chamado'])
def abrir_chamado(request, servico_id):
    servico = get_object_or_404(Servico, pk=servico_id)
    if servico.interno and not (request.user.has_perm('centralservicos.change_chamado') and GrupoAtendimento.meus_grupos(request.user, servico.area).exists()):
        raise PermissionDenied('Você não tem permissão para abrir um chamado interno.')
    if not servico.ativo:
        raise PermissionDenied('Não é possível abrir um chamado para este serviço, pois o mesmo está inativo.')

    title = servico.nome
    interno = '(Interno)' if servico.interno else ''
    title = f'{servico.nome} {interno}'

    FormClass = ChamadoFormFactory(request, servico=servico)
    form = FormClass(request.POST or None)
    formset = ChamadoAnexoFormset(request.POST or None, request.FILES or None)
    form.instance.servico = servico
    if not hasattr(form.instance, 'interessado') or not form.cleaned_data.get('interessado'):
        form.instance.interessado = request.user
    if not hasattr(form.instance, 'requisitante') or not form.cleaned_data.get('requisitante'):
        form.instance.requisitante = form.instance.interessado

    if form.is_valid() and formset.is_valid():
        try:

            form.instance.aberto_em = datetime.datetime.today()
            form.instance.aberto_por = request.user

            if not servico.requer_numero_patrimonio:
                FormClass.base_fields['numero_patrimonio'].value = None

            if not hasattr(form.instance, 'meio_abertura') or not form.cleaned_data.get('meio_abertura'):
                form.instance.meio_abertura = Chamado.MEIO_ABERTURA_WEB

            """ É necessário fazer essa consulta pois esse atributo no form não é um objeto do tipo CentroAtendimento """
            form.instance.centro_atendimento = form.cleaned_data.get('centro_atendimento')
            form.instance.campus = UnidadeOrganizacional.objects.suap().get(pk=form.cleaned_data.get('uo'))
            form.save()

            if servico.permite_anexos:
                for frm in formset.forms:  # Para cada Anexo
                    if frm.cleaned_data.get('anexo'):
                        frm.instance.chamado = form.instance
                        frm.instance.anexado_em = datetime.datetime.today()
                        frm.instance.anexado_por = request.user
                        frm.instance.anexo = frm.cleaned_data.get('anexo')
                        frm.save()

            Notificar.chamado_aberto(form.instance, form.cleaned_data.get('enviar_copia_email'))

            if form.instance.permite_visualizar(request.user):
                return httprr(Chamado.get_absolute_url(form.instance), 'Chamado aberto com sucesso.')
            else:
                url = '/centralservicos/selecionar_servico_abertura/{}/'.format(servico.area.slug)
                return httprr(url, 'Chamado aberto com sucesso. Número do chamado:{}'.format(form.instance.pk))

        except ValidationError as e:
            messages.error(request, ''.join(e.messages))

    return locals()


@rtr('centralservicos/templates/chamado.html')
@permission_required(['centralservicos.view_chamado', 'centralservicos.change_chamado'])
def visualizar_chamado(request, chamado_id):
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    eh_atendente = chamado.eh_atendente(request.user)
    eh_pessoa_envolvida = chamado.pessoa_envolvida(request.user)
    if not (eh_atendente or eh_pessoa_envolvida or chamado.permite_visualizar(request.user)):
        raise PermissionDenied('Você não tem permissão para visualizar este chamado.')

    hoje = datetime.datetime.today()
    interno = 'Interno' if chamado.servico.interno else ''
    title = 'Chamado {} {}'.format(interno, chamado_id)
    pode_alterar_status = eh_atendente and not (chamado.estah_resolvido() or chamado.estah_cancelado() or chamado.estah_fechado())
    pode_fechar = chamado.pode_fechar(request.user)
    pode_reabrir = chamado.pode_reabrir(request.user)
    pode_assumir = chamado.pode_assumir(request.user)
    pode_suspender = chamado.pode_suspender(request.user)
    pode_reclassificar = chamado.pode_reclassificar(request.user)
    pode_cancelar = chamado.pode_cancelar(request.user)
    pode_adicionar_outros_interessados = (
        eh_pessoa_envolvida or eh_atendente or request.user.is_superuser or request.user in chamado.get_responsaveis_equipe_atendimento()
    ) and chamado.status not in (StatusChamado.get_status_fechado(), StatusChamado.get_status_resolvido(), StatusChamado.get_status_cancelado())

    if chamado.estah_em_atendimento() and eh_atendente:
        bases_de_conhecimento = list(chamado.servico.get_bases_de_conhecimento_disponiveis(chamado.get_atendimento_atribuicao_atual().grupo_atendimento))
        bases_de_conhecimento.sort(key=lambda x: (x.estah_disponivel_para_uso(), x.get_media_avaliacoes(), x.get_quantidade_utilizacoes), reverse=True)
        perguntas_avaliacao = PerguntaAvaliacaoBaseConhecimento.objects.filter(area=chamado.servico.area, ativo=True)
        respostas_padrao = RespostaPadrao.objects.filter(atendente=request.user)

    FormClass = ComunicacaoFormFactory(request, chamado)
    form = FormClass()

    pode_adicionar_comentario = False
    if (request.user.is_superuser or eh_atendente) and chamado.status in (StatusChamado.get_status_em_atendimento(), StatusChamado.get_status_suspenso()):
        pode_adicionar_comentario = True
    elif (request.user == chamado.interessado or chamado.eh_outro_interessado(request.user) or request.user == chamado.aberto_por) and chamado.status in (
        StatusChamado.get_status_aberto(),
        StatusChamado.get_status_reaberto(),
        StatusChamado.get_status_em_atendimento(),
        StatusChamado.get_status_suspenso(),
    ):
        pode_adicionar_comentario = True

    outras_opcoes = []
    if not chamado.estah_cancelado():
        if not chamado.estah_fechado() and not chamado.estah_resolvido():
            if request.user.is_superuser or request.user in chamado.get_responsaveis_equipe_atendimento():
                outras_opcoes.append('<li><a class="popup" href="/centralservicos/atribuir_chamado/{:d}/">Atribuir</a></li>'.format(chamado.pk))
        if request.user.is_superuser or eh_atendente or request.user in chamado.get_responsaveis_equipe_atendimento():
            if chamado.pode_escalar():
                outras_opcoes.append('<li><a href="/centralservicos/escalar_atendimento_chamado/{:d}/">Escalar</a></li>'.format(chamado.pk))
            if chamado.pode_retornar():
                outras_opcoes.append('<li><a href="/centralservicos/retornar_atendimento_chamado/{:d}/">Retornar</a></li>'.format(chamado.pk))
            areas = GrupoAtendimento.areas_vinculadas_ao_meu_centro_atendimento(request.user)
            if chamado.tem_tags_disponiveis(areas):
                outras_opcoes.append('<li><a class="popup" href="/centralservicos/adicionar_tags_ao_chamado/{:d}/">Adicionar Tags</a></li>'.format(chamado.pk))
        if pode_reclassificar:
            outras_opcoes.append('<li><a href="/centralservicos/reclassificar_chamado/{:d}/">Reclassificar</a></li>'.format(chamado.pk))
            if 'erros' in settings.INSTALLED_APPS:
                outras_opcoes.append('<li><a class="popup" href="/erros/reportar_erro_por_chamado/{:d}/">Reportar Erro</a></li>'.format(chamado.pk))
        if pode_adicionar_outros_interessados:
            outras_opcoes.append('<li><a class="popup" href="/centralservicos/adicionar_outros_interessados/{:d}/">Adicionar Outros Interessados</a></li>'.format(chamado.pk))
            if GrupoInteressado.objects.filter(grupo_atendimento=chamado.get_atendimento_atribuicao_atual().grupo_atendimento).exists():
                outras_opcoes.append(
                    '<li><a class="popup" href="/centralservicos/adicionar_grupo_de_interessados/{:d}/">Adicionar Grupo de Interessados</a></li>'.format(chamado.pk)
                )
        if pode_alterar_status and chamado.estah_em_atendimento():
            outras_opcoes.append('<li><a class="popup" href="/centralservicos/visualizar_chamados_semelhantes/{:d}/">Visualizar Chamados Semelhantes</a></li>'.format(chamado.pk))
        if request.user.is_superuser or request.user.has_perm('centralservicos.solve_chamado'):
            outras_opcoes.append(
                '<li><a class="popup" href="/centralservicos/visualizar_outros_chamados_do_interessado/{:d}/">Outros Chamados do Interessado</a></li>'.format(chamado.pk)
            )

    return locals()


@csrf_exempt
@permission_required('centralservicos.change_chamado')
def avaliar_baseconhecimento(request, baseconhecimento_id, pergunta_id, nota):
    base_conhecimento = get_object_or_404(BaseConhecimento, pk=baseconhecimento_id)
    pergunta = get_object_or_404(PerguntaAvaliacaoBaseConhecimento, pk=pergunta_id)
    try:
        avalia = AvaliaBaseConhecimento.objects.get(base_conhecimento=base_conhecimento, pergunta=pergunta, avaliado_por=request.user)
        avalia.nota = nota
    except AvaliaBaseConhecimento.DoesNotExist:
        avalia = AvaliaBaseConhecimento(base_conhecimento=base_conhecimento, pergunta=pergunta, avaliado_por=request.user, nota=nota)
    avalia.save()

    qtd_perguntas = PerguntaAvaliacaoBaseConhecimento.objects.filter(area=base_conhecimento.area, ativo=True).count()
    qtd_avaliacoes_usuario = AvaliaBaseConhecimento.objects.filter(
        base_conhecimento=base_conhecimento, avaliado_por=request.user, data__gte=base_conhecimento.atualizado_em
    ).count()
    avaliou_todas_perguntas = qtd_perguntas == qtd_avaliacoes_usuario
    media_avaliacoes = "{:,.1f}".format(base_conhecimento.get_media_avaliacoes()).replace('.', ',')
    qtd_avaliacoes = base_conhecimento.get_quantidade_avaliacoes

    return JsonResponse({'ok': True, 'avaliou_todas_perguntas': avaliou_todas_perguntas, 'media_avaliacoes': media_avaliacoes, 'qtd_avaliacoes': qtd_avaliacoes})


@rtr('centralservicos/templates/visualizar_baseconhecimento.html')
@permission_required(['centralservicos.change_baseconhecimento', 'centralservicos.add_chamado'])
def visualizar_baseconhecimento(request, baseconhecimento_id):
    base_conhecimento = get_object_or_404(BaseConhecimento, pk=baseconhecimento_id)
    perguntas_avaliacao = PerguntaAvaliacaoBaseConhecimento.objects.filter(area=base_conhecimento.area, ativo=True)
    title = base_conhecimento.titulo
    tags = list()
    if base_conhecimento.tags:
        tags = base_conhecimento.tags.split(", ")
    eh_atendente_desta_area = request.user.has_perm('centralservicos.change_baseconhecimento') and GrupoAtendimento.meus_grupos(request.user, base_conhecimento.area).exists()
    return locals()


@rtr()
@permission_required('centralservicos.review_baseconhecimento')
def aprovar_baseconhecimento(request, baseconhecimento_id):
    if request.method == 'POST':
        BaseConhecimento.objects.filter(pk=baseconhecimento_id).update(necessita_correcao=False, supervisao_pendente=False)
        messages.success(request, 'Base de conhecimento revisada com sucesso.')
    return redirect(reverse('centralservicos_visualizar_baseconhecimento', args=(baseconhecimento_id,)))


@rtr('centralservicos/templates/visualizar_baseconhecimento_publica.html')
@permission_required('centralservicos.add_chamado')
def visualizar_baseconhecimento_publica(request, baseconhecimento_id):
    base_conhecimento = get_object_or_404(BaseConhecimento, pk=baseconhecimento_id)
    if not base_conhecimento.visibilidade == BaseConhecimento.VISIBILIDADE_PUBLICA and not request.user.has_perm('centralservicos.change_chamado'):
        raise PermissionDenied('Esta base de conhecimento não é publica e por isso não pode ser visualizada neste endereço.')
    title = base_conhecimento.titulo
    return locals()


@rtr()
@login_required
def adicionar_anexo(request, chamado_id):
    title = 'Adicionar Anexo'
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    if not chamado.permite_visualizar(request.user):
        raise PermissionDenied('Você não tem permissão para adicionar anexo neste chamado.')
    form = ChamadoAnexoForm(request.POST or None, request.FILES or None)
    form.instance.chamado = chamado
    form.instance.anexado_por = request.user
    if form.is_valid():
        form.save()
        Notificar.adicao_anexo(form.instance)
        return httprr(chamado.get_absolute_url(), 'Anexo adicionado com sucesso.')
    return locals()


def __adicionar_comentario_ou_nota_interna(request, tipo, chamado_id):
    """ Método privado, pois está sendo usado apenas internamente
        Responsável por adicionar um comentário ou nota interna no chamado
    """
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    if not chamado.permite_visualizar(request.user):
        raise PermissionDenied('Você não tem permissão para adicionar comentário ou nota interna neste chamado.')
    elif chamado.status not in (
        StatusChamado.get_status_aberto(),
        StatusChamado.get_status_reaberto(),
        StatusChamado.get_status_em_atendimento(),
        StatusChamado.get_status_suspenso(),
    ):
        raise PermissionDenied('Não é possível adicionar um comentário ou nota interna em um chamado com a situação atual ({}).'.format(chamado.get_status_display()))

    if tipo == Comunicacao.TIPO_NOTA_INTERNA and not (
        chamado.eh_atendente(request.user) or request.user in chamado.get_atendentes_equipe_atendimento() or request.user in chamado.get_responsaveis_equipe_atendimento()
    ):
        raise PermissionDenied('Você não tem permissão para adicionar uma Nota Interna neste chamado.')

    FormClass = ComunicacaoFormFactory(request, chamado)
    form = FormClass(request.POST or None)
    form.instance.chamado = chamado
    form.instance.remetente = request.user
    form.instance.tipo = tipo
    if form.is_valid():
        form.save()
        if tipo == Comunicacao.TIPO_COMENTARIO:
            mensagem = 'Comentário adicionado com sucesso.'
            url = '{}?tab=linha_tempo'.format(chamado.get_absolute_url())
        else:
            mensagem = 'Nota Interna adicionada com sucesso.'
            url = '{}?tab=notas_internas'.format(chamado.get_absolute_url())
        return httprr(url, mensagem)
    else:
        mensagem = 'Não foi possível enviar a sua mensagem.'
        if tipo == Comunicacao.TIPO_COMENTARIO:
            url = '{}?tab=linha_tempo'.format(chamado.get_absolute_url())
        else:
            url = '{}?tab=notas_internas'.format(chamado.get_absolute_url())
        return httprr(url, mensagem, 'error')


@rtr()
@permission_required(['centralservicos.add_comment', 'centralservicos.change_chamado'])
def desconsiderar_comentario(request, comentario_id):
    comentario = get_object_or_404(Comunicacao, pk=comentario_id)
    if not comentario.remetente == request.user:
        raise PermissionDenied('Você não tem permissão para desconsiderar este comentário. Apenas o próprio usuário pode desconsiderá-lo.')
    comentario.desconsiderada_em = datetime.datetime.now()
    comentario.save()
    return httprr(comentario.chamado.get_absolute_url(), 'Comentário desconsiderado com sucesso.')


@rtr()
@permission_required(['centralservicos.add_comment', 'centralservicos.change_chamado'])
def adicionar_comentario(request, chamado_id):
    return __adicionar_comentario_ou_nota_interna(request, Comunicacao.TIPO_COMENTARIO, chamado_id)


@rtr()
@permission_required('centralservicos.add_internal_note', 'centralservicos.change_chamado')
def adicionar_nota_interna(request, chamado_id):
    return __adicionar_comentario_ou_nota_interna(request, Comunicacao.TIPO_NOTA_INTERNA, chamado_id)


@rtr()
@permission_required('centralservicos.solve_chamado')
def resolver_chamado(request, chamado_id):
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    if chamado.eh_atendente(request.user) or chamado.pode_fechar(request.user):
        FormClass = AlterarStatusChamadoFormFactory(request, servico=chamado.servico, grupo_atendimento=chamado.get_atendimento_atribuicao_atual().grupo_atendimento)
        title = 'Alterar para Resolvido'
        form = FormClass(request.POST or None, instance=chamado)
        if form.is_valid():
            try:
                chamado.resolver_chamado(request.user, bases_conhecimento=form.cleaned_data.get('bases_conhecimento'), observacao=form.cleaned_data.get('observacao'))
                return httprr(chamado.get_absolute_url(), 'Alteração de situação realizada com sucesso.')
            except TransitionNotAllowed:
                raise PermissionDenied('Você não tem permissão para resolver este chamado.')

        return httprr(request.META.get('HTTP_REFERER', chamado.get_absolute_url()))
    else:
        raise PermissionDenied('Você não tem permissão para alterar a situação deste chamado.')
    return locals()


@rtr('centralservicos/templates/form_fechar_chamado.html')
@permission_required(['centralservicos.close_chamado'])
def fechar_chamado(request, chamado_id):
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    if chamado.pode_fechar(request.user):
        if chamado.interessado == request.user:
            title = 'Fechar Chamado'
            if request.method == 'POST':
                try:
                    chamado.fechar_chamado(request.user, nota_avaliacao=request.POST.get('nota_avaliacao', None), comentario_avaliacao=request.POST.get('comentario', ''))
                    return httprr(chamado.get_absolute_url(), 'Alteração de situação realizada com sucesso.')
                except TransitionNotAllowed:
                    raise PermissionDenied('Você não tem permissão para alterar a situação deste chamado.')
        elif request.method == 'POST':
            chamado.fechar_chamado(request.user)
            return httprr(chamado.get_absolute_url(), 'Chamado fechado com sucesso.')

    else:
        raise PermissionDenied('Você não tem permissão para fechar este chamado.')
    return locals()


@permission_required(['centralservicos.view_chamado', 'centralservicos.change_chamado'])
def colocar_em_atendimento(request, chamado_id):
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    if not has_transition_perm(chamado.colocar_em_atendimento_transition, request.user):
        raise PermissionDenied('Você não tem permissão para alterar a situação deste chamado.')
    try:
        chamado.colocar_em_atendimento(request.user)
    except TransitionNotAllowed:
        raise PermissionDenied('Você não tem permissão para alterar a situação deste chamado.')

    return httprr(chamado.get_absolute_url(), 'Alteração de situação realizada com sucesso.')


def __alterar_status_e_adicionar_comentario(request, chamado_id, status_id, status_nome):
    """ Método privado, pois está sendo usado apenas internamente
        Responsável por alterar um status e adicionar um comentário no chamado
    """
    title = 'Alterar Situação para {}'.format(status_nome)
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    pode_reabrir = status_id == StatusChamado.get_status_reaberto() and chamado.pode_reabrir(request.user)
    pode_suspender = status_id == StatusChamado.get_status_suspenso() and chamado.pode_suspender(request.user)
    if pode_reabrir or pode_suspender or chamado.pode_cancelar(request.user):
        FormClass = AlterarStatusChamadoFormFactory(request, servico=chamado.servico, grupo_atendimento=None)
        form = FormClass(request.POST or None, instance=chamado)
        if form.is_valid():
            chamado.alterar_status(request.user, status=status_id, observacao=form.cleaned_data.get('observacao'))
            return httprr(chamado.get_absolute_url(), 'Situação alterada com sucesso.')
    else:
        raise PermissionDenied('Você não tem permissão para alterar esta situação.')

    return locals()


@rtr()
@permission_required(['centralservicos.reopen_chamado'])
def reabrir_chamado(request, chamado_id):
    title = 'Alterar Situação para Reaberto'
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    if chamado.pode_reabrir(request.user):
        atendimento_atribuicao = chamado.get_atendimento_atribuicao_atual()
        FormClass = AlterarStatusChamadoFormFactory(request, servico=chamado.servico, grupo_atendimento=None)
        form = FormClass(request.POST or None, instance=chamado)
        if form.is_valid():
            try:
                chamado.reabrir_chamado(request.user, observacao=form.cleaned_data.get('observacao'))
                chamado.atribuir_atendente(atendimento_atribuicao.grupo_atendimento, request.user, atendimento_atribuicao.atribuido_para)
                return httprr(chamado.get_absolute_url(), 'Situação alterada com sucesso.')
            except TransitionNotAllowed:
                return httprr(chamado.get_absolute_url(), 'Você não tem permissão para alterar esta situação.', tag='error')
    else:
        raise PermissionDenied('Você não tem permissão para alterar esta situação.')
    return locals()


@rtr()
@permission_required(['centralservicos.suspend_chamado'])
def suspender_chamado(request, chamado_id):
    title = 'Alterar Situação para Suspenso'
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    if chamado.pode_suspender(request.user):
        atendimento_atribuicao = chamado.get_atendimento_atribuicao_atual()
        FormClass = AlterarStatusChamadoFormFactory(request, servico=chamado.servico, grupo_atendimento=None)
        form = FormClass(request.POST or None, instance=chamado)
        if form.is_valid():
            try:
                chamado.suspender_chamado(request.user, observacao=form.cleaned_data.get('observacao'))
                return httprr(chamado.get_absolute_url(), 'Situação alterada com sucesso.')
            except TransitionNotAllowed:
                return httprr(chamado.get_absolute_url(), 'Você não tem permissão para alterar esta situação.', tag='error')
    else:
        raise PermissionDenied('Você não tem permissão para alterar esta situação.')
    return locals()


@rtr('centralservicos/templates/cancelar_chamado.html')
@permission_required(['centralservicos.cancel_chamado'])
def cancelar_chamado(request, chamado_id):
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    title = 'Cancelar Chamado {}'.format(chamado)
    if chamado.pode_cancelar(request.user):
        FormClass = AlterarStatusChamadoFormFactory(request, servico=chamado.servico, grupo_atendimento=None)
        form = FormClass(request.POST or None, instance=chamado)
        if form.is_valid():
            try:
                chamado.cancelar_chamado(request.user, observacao=form.cleaned_data.get('observacao'))
                return httprr(chamado.get_absolute_url(), 'Situação alterada com sucesso.')
            except TransitionNotAllowed:
                return httprr(chamado.get_absolute_url(), 'Este atendimento não pode ser fechado.', tag='error')
    else:
        raise PermissionDenied('Você não tem permissão para alterar esta situação.')
    return locals()


@rtr('centralservicos/templates/meus_chamados.html')
@permission_required(['centralservicos.view_chamado', 'centralservicos.change_chamado'])
def meus_chamados(request):
    title = 'Meus Chamados'
    FormClass = BuscarChamadoUsuarioFormFactory(request)
    form = FormClass(request.GET or dict())
    if form.is_valid():
        todos_chamados = Chamado.get_chamados_do_usuario(
            request.user,
            chamado_id=form.cleaned_data.get('chamado_id'),
            area=form.cleaned_data.get('area'),
            data_inicial=form.cleaned_data.get('data_inicial'),
            data_final=form.cleaned_data.get('data_final'),
            tipo_usuario=form.cleaned_data.get('tipo_usuario'),
        )
        chamados_ativos = todos_chamados.exclude(status__in=(StatusChamado.get_status_fechado(), StatusChamado.get_status_resolvido(), StatusChamado.get_status_cancelado()))
        chamados_abertos = todos_chamados.filter(status=StatusChamado.get_status_aberto())
        chamados_em_atendimento = todos_chamados.filter(status=StatusChamado.get_status_em_atendimento())
        chamados_reabertos = todos_chamados.filter(status=StatusChamado.get_status_reaberto())
        chamados_suspensos = todos_chamados.filter(status=StatusChamado.get_status_suspenso())
        chamados_resolvidos = todos_chamados.filter(status=StatusChamado.get_status_resolvido())
        chamados_fechados = todos_chamados.filter(status=StatusChamado.get_status_fechado())
        chamados_cancelados = todos_chamados.filter(status=StatusChamado.get_status_cancelado())
    return locals()


@rtr('centralservicos/templates/listar_chamados_suporte.html')
@permission_required('centralservicos.list_chamados_suporte')
def listar_chamados_suporte(request):
    title = 'Chamados'
    FormClass = BuscarChamadoSuporteFormFactory(request, request.GET.get('area', None) and request.GET.getlist('area', []) or [])
    form = FormClass(request.GET or dict())
    if form.is_valid():
        lista_chamados = Chamado.get_chamados_do_suporte(
            request.user,
            chamado_id=form.cleaned_data.get('chamado_id'),
            data_inicial=form.cleaned_data.get('data_inicial'),
            data_final=form.cleaned_data.get('data_final'),
            tipo=form.cleaned_data.get('tipo'),
            status=form.cleaned_data.get('status'),
            nota_avaliacao=form.cleaned_data.get('nota_avaliacao'),
            area=form.cleaned_data.get('area'),
            grupo_atendimento=form.cleaned_data.get('grupo_atendimento'),
            tags=form.cleaned_data.get('tags'),
            uo=form.cleaned_data.get('uo'),
            atribuicoes=form.cleaned_data.get('atribuicoes'),
            todos_status=form.cleaned_data.get('todos_status'),
            texto_livre=form.cleaned_data.get('texto'),
            considerar_escalados=form.cleaned_data.get('considerar_escalados'),
            servico=form.cleaned_data.get('servico'),
            grupo_servico=form.cleaned_data.get('grupo_servico'),
            interessado=form.cleaned_data.get('interessado'),
            aberto_por=form.cleaned_data.get('aberto_por'),
            atendente=form.cleaned_data.get('atendente'),
            ordenar_por=form.cleaned_data.get('ordenar_por'),
            tipo_ordenacao=form.cleaned_data.get('tipo_ordenacao'),
            sla_estourado=form.cleaned_data.get('sla_estourado'),
        )
    else:
        lista_chamados = Chamado.get_chamados_do_suporte(request.user)

    return locals()


@rtr('centralservicos/templates/dashboard.html')
@permission_required('centralservicos.change_chamado')
def dashboard(request):
    title = 'Dashboard'
    """
        Chamados que estejam nos grupos de atendimento do usuário,
        que não estejam com o status igual a fechado ou resolvido
        e agrupado por incidente ou requisição
        #DashBoard se refere aos chamados que o Atendente possui permissão
    """

    area = None
    areas = GrupoAtendimento.areas_vinculadas_ao_meu_centro_atendimento(request.user)
    filtro_area = ''.join([f'&area={id_area}' for id_area in areas.values_list('id', flat=True)])
    filtros_qs_chamados = {}
    if request.GET.get('area'):
        area = get_object_or_404(AreaAtuacao, pk=request.GET.get('area'))
        filtro_area = f'&area={area.id}'
        title = f'Dashboard - {area.nome}'
        filtros_qs_chamados['area'] = area

    """ grupos_atendimento = Variavel utilizada no template para listar todos os grupos do usuário """
    grupos_atendimento = GrupoAtendimento.meus_grupos_com_servicos_ou_chamados_ativos(request.user, area)
    filtro_grupo_atendimento = ''.join([f'&grupo_atendimento={grupo_atendimento_uo_id}' for grupo_atendimento_uo_id in grupos_atendimento.values_list('id', flat=True)])
    uos = UnidadeOrganizacional.objects.suap().filter(pk__in=grupos_atendimento.values_list('campus', flat=True))
    filtro_uo = ''.join([f'&uo={id_uo}' for id_uo in uos.values_list('id', flat=True)])

    """ filtra_por_grupo = filtro com base no parametro informado na URL ou nos grupos do usuario """
    filtra_por_grupo = grupos_atendimento
    if request.GET.get('grupo_atendimento'):
        grupo_atendimento = get_object_or_404(GrupoAtendimento, pk=request.GET.get('grupo_atendimento'))
        filtro_grupo_atendimento = f'&grupo_atendimento={grupo_atendimento.id}'
        filtra_por_grupo = [grupo_atendimento.id]
        filtros_qs_chamados['grupo_atendimento'] = grupo_atendimento

    if request.GET.get('uo'):
        uo = get_object_or_404(UnidadeOrganizacional, pk=request.GET.get('uo'))
        filtro_uo = f'&uo={uo.id}'
        atendimentos = AtendimentoAtribuicao.objects.filter(grupo_atendimento__campus_id=uo.id, grupo_atendimento__in=filtra_por_grupo, cancelado_em__isnull=True)
        filtros_qs_chamados['uo'] = uo
    else:
        atendimentos = AtendimentoAtribuicao.objects.filter(grupo_atendimento__in=filtra_por_grupo, cancelado_em__isnull=True)

    qs_atribuidos_a_mim = Chamado.get_chamados_do_suporte(request.user, atribuicoes=Chamado.ATRIBUIDOS_A_MIM, **filtros_qs_chamados)
    qs = Chamado.objects.filter(pk__in=atendimentos.values('chamado')).exclude(
        status__in=(StatusChamado.get_status_fechado(), StatusChamado.get_status_resolvido(), StatusChamado.get_status_cancelado())
    )

    # qs_atribuidos_a_mim = Chamado.objects.filter(pk__in=atendimentos.filter(atribuido_para=request.user).values('chamado')).exclude(
    #     status__in=(StatusChamado.get_status_fechado(), StatusChamado.get_status_resolvido(), StatusChamado.get_status_cancelado())
    # )
    qs_atribuidos_a_outros = Chamado.objects.filter(pk__in=atendimentos.filter(atribuido_para__isnull=False).exclude(atribuido_para=request.user).values('chamado')).exclude(
        status__in=(StatusChamado.get_status_fechado(), StatusChamado.get_status_resolvido(), StatusChamado.get_status_cancelado())
    )
    qs_nao_atribuidos = Chamado.objects.filter(pk__in=atendimentos.filter(atribuido_para__isnull=True).values('chamado')).exclude(
        status__in=(StatusChamado.get_status_fechado(), StatusChamado.get_status_resolvido(), StatusChamado.get_status_cancelado())
    )

    qtd_incidentes_atribuidos_a_mim = qs_atribuidos_a_mim.filter(servico__tipo=Servico.TIPO_INCIDENTE).count()
    qtd_incidentes_atribuidos_a_outros = qs_atribuidos_a_outros.filter(servico__tipo=Servico.TIPO_INCIDENTE).count()
    qtd_incidentes_nao_atribuidos = qs_nao_atribuidos.filter(servico__tipo=Servico.TIPO_INCIDENTE).count()

    qtd_requisicoes_atribuidas_a_mim = qs_atribuidos_a_mim.filter(servico__tipo=Servico.TIPO_REQUISICAO).count()
    qtd_requisicoes_atribuidas_a_outros = qs_atribuidos_a_outros.filter(servico__tipo=Servico.TIPO_REQUISICAO).count()
    qtd_requisicoes_nao_atribuidas = qs_nao_atribuidos.filter(servico__tipo=Servico.TIPO_REQUISICAO).count()

    qtd_favicon = qtd_incidentes_nao_atribuidos + qtd_requisicoes_nao_atribuidas

    grafico_categorias = list()
    [grafico_categorias.append([categoria.nome, categoria.qtd_chamados]) for categoria in CategoriaServico.objects.filter(gruposervico__servico__chamado__in=qs).annotate(qtd_chamados=Count('gruposervico__servico__chamado')).filter(qtd_chamados__gt=0).only('nome')]

    dados_grafico = PieChart('div_grafico', title='Chamados por Categoria', subtitle='Nos seus Grupos de Atendimento', minPointLength=0, data=grafico_categorias)
    return locals()


@permission_required('centralservicos.add_auto_atribuicao')
def auto_atribuir_chamado(request, chamado_id):
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    url = request.META.get('HTTP_REFERER', chamado.get_absolute_url())

    if chamado.status in (StatusChamado.get_status_resolvido(), StatusChamado.get_status_fechado()):
        return httprr(url, 'Este chamado não pode ser atribuído, pois sua situação atual é Resolvido/Fechado.', tag='error')

    atendimento_atribuicao = chamado.get_atendimento_atribuicao_atual()

    try:
        chamado.atribuir_atendente(atendimento_atribuicao.grupo_atendimento, request.user, request.user)
        return httprr(url, 'Atribuição realizada com sucesso.')
    except TransitionNotAllowed:
        return httprr(url, 'Este atendimento não pode ser atribuído a {}.'.format(request.user), tag='error')


def __escalar_ou_retornar_atendimento_chamado(request, operacao, chamado_id):
    if request.user.has_perm('centralservicos.change_chamado'):
        chamado = get_object_or_404(Chamado, pk=chamado_id)

        title = '{} Atendimento'.format(operacao.capitalize())
        if operacao == 'escalar':
            if not chamado.pode_escalar():
                return httprr(
                    '..', 'Este atendimento não pode ser escalado. Verifique se existe grupo de atendimento superior ou se o chamado não está resolvido/fechado.', tag='error'
                )
        else:
            if not chamado.pode_retornar():
                return httprr(
                    '..', 'Este atendimento não pode ser retornado. Verifique se existe grupo de atendimento inferior ou se o chamado não está resolvido/fechado.', tag='error'
                )

        FormClass = ComunicacaoFormFactory(request, chamado, operacao)
        form = FormClass(request.POST or None)
        form.fields['texto'].help_text = 'Para {} o atendimento, adicione um texto que será exibido como ' 'Nota Interna.'.format(operacao)
        form.instance.chamado = chamado
        form.instance.remetente = request.user
        form.instance.tipo = Comunicacao.TIPO_NOTA_INTERNA
        if form.is_valid():
            atribuido_para = form.cleaned_data.get('atribuido_para', None)
            chamado.escalar_ou_retornar_atendimento(operacao, request.user, atribuido_para)

            # if atribuido_para:
            #     chamado.atribuir_atendente(grupo, request.user, atribuido_para)
            form.save()
            """
                Quando o atendente escala/retorna um chamado, normalmente ele nao possui acesso ao chamado.
                Por isso, por padrão redireciona para o dashboard.
            """
            if chamado.permite_visualizar(request.user):
                return httprr(chamado.get_absolute_url(), 'Operação realizada com sucesso.')
            else:
                return httprr('/centralservicos/dashboard/')

    else:
        raise PermissionDenied('Você não tem permissão para realizar esta operação.')

    return locals()


@rtr()
@permission_required('centralservicos.change_atendimentoatribuicao')
def escalar_atendimento_chamado(request, chamado_id):
    return __escalar_ou_retornar_atendimento_chamado(request, 'escalar', chamado_id)


@rtr()
@permission_required('centralservicos.change_atendimentoatribuicao')
def retornar_atendimento_chamado(request, chamado_id):
    return __escalar_ou_retornar_atendimento_chamado(request, 'retornar', chamado_id)


@rtr('centralservicos/templates/form_atribuir_chamado.html')
@permission_required('centralservicos.change_chamado')
def atribuir_chamado(request, chamado_id):
    title = 'Atribuição de Chamado'
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    grupo = chamado.get_atendimento_atribuicao_atual().grupo_atendimento
    if not chamado.estah_fechado() and not chamado.estah_resolvido():
        if request.user.is_superuser or chamado.get_responsaveis_equipe_atendimento().filter(pk=request.user.pk).exists():
            FormClass = AtendimentoAtribuicaoFormFactory(request, grupo)
            form = FormClass(request.POST or None)
            if form.is_valid():
                try:
                    atribuido_para = form.cleaned_data.get('atribuido_para', None)
                    chamado.atribuir_atendente(grupo, request.user, atribuido_para)
                    return httprr('..', 'Atribuição realizada com sucesso para {}.'.format(atribuido_para))
                except TransitionNotAllowed:
                    return httprr(chamado.get_absolute_url(), 'Chamados com Situação Resolvido ou Fechado não podem ser atribuídos.', tag='error')
        else:
            raise PermissionDenied('..', 'Você não tem permissão para atribuir um chamado.')
    else:
        raise PermissionDenied('..', 'Chamados com Situação Resolvido ou Fechado não podem ser atribuídos.')

    return locals()


"""
Método responsavel por retornar uma lista de centros de atendimento, em formato json, com base no serviço e campus informado
Centros de atendimento do com eh_local = False, retornarão todos da área do serviço.
"""


@csrf_exempt
@login_required()
def get_centros_atendimento_por_servico_e_campus(request, servico_id, campus_id):
    servico = get_object_or_404(Servico, pk=servico_id)
    choice = []
    for centro in servico.get_centros_atendimento(campus_id):
        choice.append([centro.id, centro.nome, centro.eh_local])
    return JsonResponse({'centros': choice})


@csrf_exempt
@login_required()
def get_centros_atendimento_por_area(request, area_id):
    area = get_object_or_404(AreaAtuacao, pk=area_id)
    choice = []
    for centro in CentroAtendimento.objects.filter(area=area):
        choice.append([centro.id, centro.nome, centro.eh_local])
    return JsonResponse({'centros': choice})


"""
Método responsavel por retornar uma lista de campus, em formato json, com base no serviço informado
"""


@csrf_exempt
@login_required()
def get_campus_com_centros_atendimento(request, servico_id, chamado_id=None):
    try:
        campus_default = Chamado.objects.get(pk=chamado_id).campus
    except Chamado.DoesNotExist:
        campus_default = get_uo(request.user)
    servico = get_object_or_404(Servico, pk=servico_id)
    choice = []
    for campus in servico.get_campus_disponiveis_para_atendimento():
        selected = campus.id == campus_default.id
        choice.append([campus.id, campus.sigla, selected])
    return JsonResponse({'campus': choice})


@rtr()
@permission_required('centralservicos.reclassify_chamado')
def reclassificar_chamado(request, chamado_id):
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    interno = 'Interno' if chamado.servico.interno else ''
    title = 'Reclassificar Chamado {}: {} - {}'.format(interno, chamado_id, chamado.servico.nome)
    usuario = request.user
    if usuario.is_superuser or chamado.get_responsaveis_equipe_atendimento().filter(pk=usuario.pk).exists() or chamado.eh_atendente(usuario):
        troca_area = False
        if usuario.is_superuser or chamado.get_responsaveis_equipe_atendimento().filter(pk=usuario.pk).exists():
            troca_area = True
        FormClass = ReclassificarChamadoFormFactory(request, chamado, troca_area)
        form = FormClass(request.POST or None)
        if form.is_valid():
            try:
                """ Centro de Atendimento não é um modelo, então não vem completo """
                centro_atendimento_novo = CentroAtendimento.objects.get(pk=form.cleaned_data.get('centro_atendimento'))
                campus = UnidadeOrganizacional.objects.suap().get(pk=form.cleaned_data.get('uo'))
                chamado.reclassificar(form.cleaned_data.get('servico'), campus, centro_atendimento_novo, form.cleaned_data.get('justificativa'), request.user)
                if chamado.permite_visualizar(usuario):
                    return httprr(chamado.get_absolute_url(), 'Reclassificação de chamado realizada com sucesso.')
                else:
                    return httprr('/centralservicos/dashboard/', 'Reclassificação de chamado realizada com sucesso.')
            except ValidationError as e:
                messages.error(request, ''.join(e.messages))
    else:
        raise PermissionDenied('Você não tem permissão para reclassificar um chamado.')

    return locals()


@rtr()
@permission_required('centralservicos.pode_ver_indicadores')
def indicadores(request):
    def obtem_media_tempo_chamados_agrupado_por_ano(campo, tipo_tempo, inicio, termino, area=None, tipo_retorno='list'):
        """
        :param campo: String: campo utilizado no group by. Exemplo: 'tipo' ou 'o_interessado_id'
        :param tipo_tempo: Strings: 'tempo_atendimento', 'tempo_resposta' ou 'tempo_suspensao
        :param ano: inteiro: Ano. Ex: 2015
        :param area: objeto tipo AreaAtuacao:
        :return: Lista
        """
        area_id = area.id if area else -1

        sql = """
                select {0}, round(  CAST(float8 (avg(tempo) / 3600) as numeric), 0) as total, CAST(ano as integer) as ano from (
                select chamado_id, {0}, to_char(data_hora, 'YYYY') as ano, sum({1}) as tempo
                from centralservicos_historicostatus hs
                inner join centralservicos_chamado c on c.id = hs.chamado_id
                inner join centralservicos_servico s on s.id = c.servico_id
                where {1} is not null
                and to_char(data_hora, 'YYYY-MM-DD') >= '{2}' and to_char(data_hora, 'YYYY-MM-DD') <= '{3}'
                and exists (select gs.id from centralservicos_gruposervico gs
                    inner join centralservicos_gruposervico_categorias gsc ON gs.id = gsc.gruposervico_id
                    inner join centralservicos_categoriaservico cs ON gsc.categoriaservico_id = cs.id
                    where s.grupo_servico_id = gs.id
                    and (cs.area_id = {4} or {4} = '-1')
                )
                group by chamado_id, {0}, to_char(data_hora, 'YYYY')
                ) as tab
                group by {0}, ano
                order by ano, {0} asc
                """.format(
            campo, tipo_tempo, inicio, termino, area_id
        )

        if tipo_retorno == 'list':
            return db.get_list(sql)

        return db.get_dict(sql)

    def obtem_media_tempo_chamados_agrupado_por_mes(campo, tipo_tempo, inicio, termino, uo=None, area=None, tipo_retorno='list'):
        """
        :param campo: String: campo utilizado no group by. Exemplo: 'tipo' ou 'o_interessado_id'
        :param tipo_tempo: String: 'tempo_atendimento', 'tempo_resposta' ou 'tempo_suspensao
        :param ano: inteiro: Ano. Ex: 2015
        :param uo_id: inteiro. id da UO
        :param area: objeto tipo AreaAtuacao:
        :param tipo_retorno: String: 'list' ou 'dict'
        :return: Lista
        """
        uo_id = uo.id if uo else -1
        area_id = area.id if area else -1

        sql = """
                select {0}, round(  CAST(float8 (avg(tempo) / 3600) as numeric), 0) as total, CAST(mes as integer) as mes from (
                select chamado_id, {0}, to_char(data_hora, 'MM') as mes, sum({1}) as tempo
                from centralservicos_historicostatus hs
                inner join centralservicos_chamado c on c.id = hs.chamado_id
                inner join centralservicos_servico s on s.id = c.servico_id
                where {1} is not null
                and (c.campus_id = {2} or {2} = '-1')
                and to_char(data_hora, 'YYYY-MM-DD') >= '{3}' and to_char(data_hora, 'YYYY-MM-DD') <= '{4}'
                and exists (select gs.id from centralservicos_gruposervico gs
                    inner join centralservicos_gruposervico_categorias gsc ON gs.id = gsc.gruposervico_id
                    inner join centralservicos_categoriaservico cs ON gsc.categoriaservico_id = cs.id
                    where s.grupo_servico_id = gs.id
                    and (cs.area_id = {5} or {5} = '-1')
                )
                group by chamado_id, {0}, to_char(data_hora, 'MM')
                ) as tab
                group by {0}, mes
                order by mes, {0} asc
                """.format(
            campo, tipo_tempo, uo_id, inicio, termino, area_id
        )
        if tipo_retorno == 'list':
            return db.get_list(sql)

        return db.get_dict(sql)

    def dados_grafico_tempo(lista, verifica_tipo):
        series = []
        mes_corrente = 0
        if lista:
            inc = 0
            rec = 0
            for tipo, total, mes in lista:
                if mes_corrente != 0 and mes_corrente != mes:
                    series.append([Meses.get_mes(mes_corrente), float(inc), float(rec)])
                    inc = 0
                    rec = 0
                mes_corrente = mes
                if tipo == verifica_tipo[0]:
                    inc = total
                elif tipo == verifica_tipo[1]:
                    rec = total
            series.append([Meses.get_mes(mes_corrente), float(inc), float(rec)])
        return series

    def dados_grafico_nota_avaliacao(queryset):
        def percentual(nota, total):
            percent = float(nota) * 100 / float(total)
            return dict(y=float("{:.2f}".format(percent)), total=nota)

        series = []
        mes_corrente = 0
        if queryset.exists():
            nota_1, nota_2, nota_3, nota_4, nota_5 = 0, 0, 0, 0, 0
            for nota, total, mes in queryset:
                if mes_corrente != 0 and mes_corrente != mes.month:
                    total_geral = nota_1 + nota_2 + nota_3 + nota_4 + nota_5
                    series.append(
                        [
                            Meses.get_mes(mes_corrente),
                            percentual(nota_1, total_geral),
                            percentual(nota_2, total_geral),
                            percentual(nota_3, total_geral),
                            percentual(nota_4, total_geral),
                            percentual(nota_5, total_geral),
                        ]
                    )
                    nota_1, nota_2, nota_3, nota_4, nota_5 = 0, 0, 0, 0, 0
                mes_corrente = mes.month
                if nota == 1:
                    nota_1 = total
                elif nota == 2:
                    nota_2 = total
                elif nota == 3:
                    nota_3 = total
                elif nota == 4:
                    nota_4 = total
                elif nota == 5:
                    nota_5 = total
            total_geral = nota_1 + nota_2 + nota_3 + nota_4 + nota_5
            series.append(
                [
                    Meses.get_mes(mes_corrente),
                    percentual(nota_1, total_geral),
                    percentual(nota_2, total_geral),
                    percentual(nota_3, total_geral),
                    percentual(nota_4, total_geral),
                    percentual(nota_5, total_geral),
                ]
            )
        return series

    # Tem que fazer isso, porque o retorno da consulta é datetime.datetime
    def configura_mes(data):
        for i in data:
            i[0] = Meses.get_mes(i[0].month)

    title = 'Indicadores'
    dic = Chamado.objects.all().aggregate(Max('aberto_em'), Min('aberto_em'))

    data_inicio = date(date.today().year, 1, 1)
    data_termino = date(date.today().year, 12, 31)

    FormClass = GraficosFormFactory(request, data_inicio, data_termino)
    form = FormClass(request.GET or None)
    if form.is_valid():
        inicio = form.cleaned_data.get('inicio')
        termino = form.cleaned_data.get('termino') + relativedelta(hours=23, minutes=59)
        uo = form.cleaned_data.get('uo')
        grupo_atendimento = form.cleaned_data.get('grupo_atendimento')
        area = form.cleaned_data.get('area')

        aberto_em_mes = connection.ops.date_trunc_sql('month', 'aberto_em')
        chamados_abertos = Chamado.objects.extra({'mes': aberto_em_mes}).filter(aberto_em__gte=inicio, aberto_em__lte=termino)
        fechado_em_mes = connection.ops.date_trunc_sql('month', 'data_hora')
        historico_status = HistoricoStatus.objects.extra({'mes': fechado_em_mes}).filter(data_hora__gte=inicio, data_hora__lte=termino)
        cancelado_em_mes = connection.ops.date_trunc_sql('month', 'cancelado_em')
        atendimento_atribuicao = AtendimentoAtribuicao.objects.extra({'mes': cancelado_em_mes}).filter(cancelado_em__gte=inicio, cancelado_em__lte=termino)
        reclassificado_mes = connection.ops.date_trunc_sql('month', 'data_hora')
        comunicacao = Comunicacao.objects.extra({'mes': reclassificado_mes}).filter(data_hora__gte=inicio, data_hora__lte=termino)

        if uo:
            chamados_abertos = chamados_abertos.filter(campus=uo)
            historico_status = historico_status.filter(chamado__campus=uo)
            atendimento_atribuicao = atendimento_atribuicao.filter(chamado__campus=uo)
            comunicacao = comunicacao.filter(chamado__campus=uo)

        if area:
            chamados_abertos = chamados_abertos.filter(servico__grupo_servico__categorias__area=area)
            historico_status = historico_status.filter(chamado__servico__grupo_servico__categorias__area=area)
            atendimento_atribuicao = atendimento_atribuicao.filter(chamado__servico__grupo_servico__categorias__area=area)
            comunicacao = comunicacao.filter(chamado__servico__grupo_servico__categorias__area=area)

        meus_grupos = GrupoAtendimento.meus_grupos(request.user)
        if grupo_atendimento:
            atendimentos = AtendimentoAtribuicao.objects.filter(grupo_atendimento=grupo_atendimento, cancelado_em__isnull=True)
        else:
            atendimentos = AtendimentoAtribuicao.objects.filter(grupo_atendimento__in=meus_grupos, cancelado_em__isnull=True)

        chamados_abertos = chamados_abertos.filter(pk__in=atendimentos.values('chamado'))
        historico_status = historico_status.filter(chamado__in=atendimentos.values('chamado'))
        atendimento_atribuicao = atendimento_atribuicao.filter(chamado__in=atendimentos.values('chamado'))
        comunicacao = comunicacao.filter(chamado__in=atendimentos.values('chamado'))

        chamados_abertos_por_tipo = chamados_abertos.values_list('mes', 'servico__tipo').annotate(total=Count('servico__tipo')).order_by('mes')

        chamados_fechados_por_tipo = (
            historico_status.filter(status=StatusChamado.get_status_fechado())
            .values('mes', 'chamado__servico__tipo')
            .annotate(total=Count('chamado__servico__tipo'))
            .order_by('mes')
        )

        chamados_reabertos_por_tipo = (
            historico_status.filter(status=StatusChamado.get_status_reaberto())
            .values('mes', 'chamado__servico__tipo')
            .annotate(total=Count('chamado__servico__tipo'))
            .order_by('mes')
        )
        chamados_nota_avaliacao = (
            historico_status.filter(status=StatusChamado.get_status_fechado(), chamado__nota_avaliacao__gte=0)
            .values('mes', 'chamado__nota_avaliacao')
            .annotate(total=Count('chamado__nota_avaliacao'))
            .order_by('mes', 'chamado__nota_avaliacao')
        )

        chamados_escalados_retornados = (
            atendimento_atribuicao.filter(tipo_justificativa__in=[AtendimentoAtribuicao.TIPO_CHAMADO_ESCALADO, AtendimentoAtribuicao.TIPO_CHAMADO_RETORNADO])
            .values('mes', 'tipo_justificativa')
            .annotate(total=Count('tipo_justificativa'))
            .order_by('mes', 'tipo_justificativa')
        )
        chamados_reclassificados = (
            comunicacao.filter(chamado__reclassificado__gte=1).values('mes', 'chamado__servico__tipo').annotate(total=Count('chamado__id', distinct=True)).order_by('mes')
        )

        groups = list()
        data1 = Relatorio.get_dados_em_coluna_linha(chamados_abertos_por_tipo.values('servico__tipo', 'total', 'mes'), groups, 'servico__tipo', 'mes', 'total', True)
        configura_mes(data1)
        grafico_chamados_abertos = LineChart(
            'grafico_chamados_abertos',
            title='Número de Chamados Abertos',
            data=data1,
            groups=groups,
            yAxis_title_text='Quantidade',
            plotOptions_line_dataLabels_enable=True,
            plotOptions_line_enableMouseTracking=True,
            yAxis_min=0,
        )

        groups = list()
        data1 = Relatorio.get_dados_em_coluna_linha(
            chamados_fechados_por_tipo.values('chamado__servico__tipo', 'total', 'mes'), groups, 'chamado__servico__tipo', 'mes', 'total', True
        )
        configura_mes(data1)
        grafico_chamados_fechados = LineChart(
            'grafico_chamados_fechados',
            title='Número de Chamados Fechados',
            data=data1,
            groups=groups,
            yAxis_title_text='Quantidade',
            plotOptions_line_dataLabels_enable=True,
            plotOptions_line_enableMouseTracking=True,
            yAxis_min=0,
        )

        groups = list()
        data1 = Relatorio.get_dados_em_coluna_linha(
            chamados_reabertos_por_tipo.values('chamado__servico__tipo', 'total', 'mes'), groups, 'chamado__servico__tipo', 'mes', 'total', True
        )
        configura_mes(data1)
        grafico_chamados_reabertos = LineChart(
            'grafico_chamados_reabertos',
            title='Número de Chamados Reabertos',
            data=data1,
            groups=groups,
            yAxis_title_text='Quantidade',
            plotOptions_line_dataLabels_enable=True,
            plotOptions_line_enableMouseTracking=True,
            yAxis_min=0,
        )

        groups = list()
        data1 = Relatorio.get_dados_em_coluna_linha(chamados_escalados_retornados.values('tipo_justificativa', 'total', 'mes'), groups, 'tipo_justificativa', 'mes', 'total', True)
        configura_mes(data1)
        groups = [w.replace('CHAMADO_', '').capitalize() for w in groups]
        grafico_escalados_retornados = LineChart(
            'grafico_escalados_retornados',
            title='Número de Chamados Escalados/Retornados',
            data=data1,
            groups=groups,
            yAxis_title_text='Quantidade',
            plotOptions_line_dataLabels_enable=True,
            plotOptions_line_enableMouseTracking=True,
            yAxis_min=0,
        )

        groups = list()
        data1 = Relatorio.get_dados_em_coluna_linha(
            chamados_reclassificados.values('chamado__servico__tipo', 'total', 'mes'), groups, 'chamado__servico__tipo', 'mes', 'total', True
        )
        configura_mes(data1)
        grafico_chamados_reclassificados = LineChart(
            'grafico_chamados_reclassificados',
            title='Número de Chamados Reclassificados',
            data=data1,
            groups=groups,
            yAxis_title_text='Quantidade',
            plotOptions_line_dataLabels_enable=True,
            plotOptions_line_enableMouseTracking=True,
            yAxis_min=0,
        )

        grafico_nota_avaliacao = LineChart(
            'grafico_nota_avaliacao',
            title='Avaliação dos Chamados Fechados',
            subtitle='Valores em percentuais',
            data=dados_grafico_nota_avaliacao(chamados_nota_avaliacao.values_list('chamado__nota_avaliacao', 'total', 'mes')),
            tooltip=dict(pointFormat='<strong>{point.y}%</strong> ({point.total})'),
            groups=['Ruim', 'Regular', 'Bom', 'Ótimo', 'Excelente'],
            yAxis_title_text='Quantidade',
            plotOptions_line_dataLabels_enable=True,
            plotOptions_line_enableMouseTracking=True,
            yAxis_min=0,
        )

        grafico_chamados_tempo_atendimento = LineChart(
            'grafico_chamados_tempo_atendimento',
            title='Média do Tempo de Atendimento dos Chamados',
            subtitle='(em horas)',
            data=dados_grafico_tempo(obtem_media_tempo_chamados_agrupado_por_mes('tipo', 'tempo_atendimento', inicio, termino, uo, area), ['INC', 'REQ']),
            tooltip=dict(pointFormat='<strong>{point.y} horas</strong>'),
            groups=['REQ', 'INC'],
            yAxis_title_text='Média do Tempo',
            plotOptions_line_dataLabels_enable=True,
            plotOptions_line_enableMouseTracking=True,
            yAxis_min=0,
        )

        grafico_chamados_tempo_resposta = LineChart(
            'grafico_chamados_tempo_resposta',
            title='Média do Tempo de Resposta dos Chamados',
            subtitle='(em horas)',
            data=dados_grafico_tempo(obtem_media_tempo_chamados_agrupado_por_mes('tipo', 'tempo_resposta', inicio, termino, uo, area), ['INC', 'REQ']),
            tooltip=dict(pointFormat='<strong>{point.y} horas</strong>'),
            groups=['REQ', 'INC'],
            yAxis_title_text='Média do Tempo',
            plotOptions_line_dataLabels_enable=True,
            plotOptions_line_enableMouseTracking=True,
            yAxis_min=0,
        )

        top_10_atendentes = (
            historico_status.filter(status=StatusChamado.get_status_resolvido())
            .values('usuario')
            .annotate(total_chamados=Count('chamado', distinct=True))
            .order_by('-total_chamados')[:10]
        )
        top_10_demandantes = chamados_abertos.values('aberto_por').annotate(total_chamados=Count('pk', distinct=True)).order_by('-total_chamados')[:10]
        top_10_chamados_maior_tempo_atendimento = (
            historico_status.filter(tempo_atendimento__isnull=False).values('chamado').annotate(tempo=Sum('tempo_atendimento')).order_by('-tempo')[:10]
        )

        lista_top_10_chamados_maior_tempo_atendimento = list()
        for i in top_10_chamados_maior_tempo_atendimento:
            chamado = Chamado.objects.get(pk=i['chamado'])
            lista_top_10_chamados_maior_tempo_atendimento.append(chamado)

        top_10_chamados_maior_tempo_resposta = (
            historico_status.filter(tempo_resposta__isnull=False)
            .filter(chamado__status=StatusChamado.get_status_em_atendimento())
            .values('chamado')
            .annotate(tempo=Sum('tempo_resposta'))
            .order_by('-tempo')[:10]
        )

        lista_top_10_chamados_maior_tempo_resposta = list()
        for i in top_10_chamados_maior_tempo_resposta:
            chamado = Chamado.objects.get(pk=i['chamado'])
            lista_top_10_chamados_maior_tempo_resposta.append(chamado)

        grafico_pizza = list()
        for i in top_10_atendentes:
            i['usuario'] = User.objects.get(pk=i['usuario'])
            if not i['usuario'].get_profile():
                grafico_pizza.append([i['usuario'].username, i['total_chamados']])
            else:
                grafico_pizza.append([i['usuario'].get_profile().nome_usual, i['total_chamados']])

        grafico_atendentes = PieChart('grafico_atendentes', title='Top 10 Atendentes', subtitle='que mais resolveram chamados', minPointLength=0, data=grafico_pizza)

        grafico_pizza = list()
        for i in top_10_demandantes:
            i['aberto_por'] = User.objects.get(pk=i['aberto_por'])
            if not i['aberto_por'].get_profile():
                grafico_pizza.append([i['aberto_por'].username, i['total_chamados']])
            else:
                grafico_pizza.append([i['aberto_por'].get_profile().nome_usual, i['total_chamados']])

        grafico_demandantes = PieChart('grafico_demandantes', title='Top 10 Demandantes', subtitle='que mais abriram chamados', minPointLength=0, data=grafico_pizza)

        # Gráfico: Top 10 Serviços mais demandados
        top_10_servicos = chamados_abertos.values('servico').annotate(total_chamados=Count('id')).order_by('-total_chamados')[:10]
        grafico_pizza_servicos = list()
        for i in top_10_servicos:
            i['servico'] = Servico.objects.get(pk=i['servico'])
            grafico_pizza_servicos.append([i['servico'].nome, i['total_chamados']])

        grafico_servicos = PieChart('grafico_servicos', title='Top 10 Serviços', subtitle='mais demandados', minPointLength=0, data=grafico_pizza_servicos)

        # Tabela com Serviços mais demandados
        servicos_mais_demandados = chamados_abertos.values('servico__nome').annotate(total_chamados=Count('id')).order_by('-total_chamados')

        # Gráfico: Grupos de Serviços mais demandados
        top_chamados_por_grupo_servicos = chamados_abertos.values('servico__grupo_servico').annotate(total_chamados=Count('id')).order_by('-total_chamados')
        grafico_chamados_por_grupo_servicos = list()
        for i in top_chamados_por_grupo_servicos:
            i['servico__grupo_servico'] = GrupoServico.objects.get(pk=i['servico__grupo_servico'])
            grafico_chamados_por_grupo_servicos.append([i['servico__grupo_servico'].nome, i['total_chamados']])

        grafico_grupos_servicos = PieChart(
            'grafico_grupos_servicos', title='Grupos de Serviços', subtitle='mais demandados', minPointLength=0, data=grafico_chamados_por_grupo_servicos
        )

        # Gráfico: Categorias de Serviços mais demandadas
        top_chamados_por_categoria_servicos = chamados_abertos.values('servico__grupo_servico__categorias').annotate(total_chamados=Count('id')).order_by('-total_chamados')
        grafico_chamados_por_categoria_servicos = list()
        for i in top_chamados_por_categoria_servicos:
            i['servico__grupo_servico__categorias'] = CategoriaServico.objects.get(pk=i['servico__grupo_servico__categorias'])
            grafico_chamados_por_categoria_servicos.append([i['servico__grupo_servico__categorias'].nome, i['total_chamados']])

        grafico_categorias_servicos = PieChart(
            'grafico_categorias_servicos', title='Categorias de Serviços', subtitle='mais demandadas', minPointLength=0, data=grafico_chamados_por_categoria_servicos
        )

        if request.user.is_superuser or request.user.groups.filter(name='centralservicos Administrador'):
            data1 = obtem_media_tempo_chamados_agrupado_por_ano('campus_id', 'tempo_atendimento', inicio, termino, area)
            for i in data1:
                if i[0]:
                    uo = UnidadeOrganizacional.objects.suap().get(pk=i[0])
                    i[0] = uo.sigla
                else:
                    i[0] = 'Não definido'
                i[1] = float(i[1])
            grafico_media_tempo_atendimento_agrupado_por_ano = ColumnChart(
                'grafico_media_tempo_atendimento_agrupado_por_ano',
                title='Média do Tempo de Atendimento por UO',
                subtitle='em horas / agrupado por ano',
                minPointLength=10,
                data=data1,
            )
            grafico_media_tempo_atendimento_agrupado_por_ano.series[0]['dataLabels'] = dict(enabled=True, rotation=-90, color='#FFF', align='right', x=4, y=10)
            grafico_media_tempo_atendimento_agrupado_por_ano.xAxis['labels'] = dict(rotation=-45, align='right')
            data1 = obtem_media_tempo_chamados_agrupado_por_ano('campus_id', 'tempo_resposta', inicio, termino, area)
            for i in data1:
                if i[0]:
                    uo = UnidadeOrganizacional.objects.suap().get(pk=i[0])
                    i[0] = uo.sigla
                else:
                    i[0] = 'Não definido'
                i[1] = float(i[1])
            grafico_media_tempo_resposta_agrupado_por_ano = ColumnChart(
                'grafico_media_tempo_resposta_agrupado_por_ano', title='Média do Tempo de Resposta por UO', subtitle='em horas / agrupado por ano', minPointLength=10, data=data1
            )
            grafico_media_tempo_resposta_agrupado_por_ano.series[0]['dataLabels'] = dict(enabled=True, rotation=-90, color='#FFF', align='right', x=4, y=10)
            grafico_media_tempo_resposta_agrupado_por_ano.xAxis['labels'] = dict(rotation=-45, align='right')

    return locals()


@rtr()
@permission_required('centralservicos.pode_ver_indicadores')
def atendimentos_por_ano(request):
    title = 'Relatório de Atendimentos por Ano'
    form = AtendimentosPorAnoForm(request.POST or None, request=request)
    if form.is_valid():
        inicio = form.cleaned_data.get('inicio')
        termino = form.cleaned_data.get('termino')
        area = form.cleaned_data.get('area')
        pks_chamados_resolvidos = HistoricoStatus.objects.filter(data_hora__year__gte=inicio, data_hora__year__lte=termino, status=StatusChamado.get_status_resolvido()).values_list('chamado__id', flat=True)
        chamados = Chamado.objects.filter(pk__in=pks_chamados_resolvidos).annotate(tempo_atendimento=Sum('historicostatus__tempo_atendimento'), tempo_resposta=Sum('historicostatus__tempo_resposta')).annotate(total_atendimento=F('tempo_atendimento') + F('tempo_resposta'))
        if area:
            chamados = chamados.filter(servico__grupo_servico__categorias__area=area)
        chamados_por_uo = OrderedDict()
        for uo in UnidadeOrganizacional.objects.suap():
            chamados_uo = chamados.filter(campus=uo)
            if chamados_uo.exists():
                chamados_uo = chamados_uo.aggregate(total_chamados=Count(F('id')), media_tempo_atendimento=Avg('total_atendimento'))
                chamados_por_uo[uo] = chamados_uo

    return locals()


@rtr()
@permission_required('centralservicos.pode_ver_indicadores')
def relatorio_atendentes(request):
    title = 'Relatório de Situação dos Atendentes'

    FormClass = AtendentesFormFactory(request)
    form = FormClass(request.GET or None)
    if form.is_valid():
        uo = form.cleaned_data.get('uo')
        setor = form.cleaned_data.get('setor')
        grupo_atendimento = form.cleaned_data.get('grupo_atendimento')
        area = form.cleaned_data.get('area')

        lista_atendentes = GrupoAtendimento.objects.all()

        if uo:
            lista_atendentes = lista_atendentes.filter(campus=uo)

        if setor:
            lista_atendentes = lista_atendentes.filter(atendentes__vinculo__setor=setor)

        if area:
            lista_atendentes = lista_atendentes.filter(centro_atendimento__area=area)

        meus_grupos = GrupoAtendimento.meus_grupos(request.user)
        if grupo_atendimento:
            lista_atendentes = lista_atendentes.filter(id=grupo_atendimento.id)
        else:
            lista_atendentes = lista_atendentes.filter(id__in=meus_grupos)

        atendentes = []
        for usuario in User.objects.filter(id__in=lista_atendentes.values('atendentes')):
            total_chamados = Chamado.get_chamados_do_suporte(user=usuario, area=area, grupo_atendimento=grupo_atendimento, uo=uo, atribuicoes=Chamado.ATRIBUIDOS_A_MIM).count()

            atendentes.append([usuario.pk, usuario.pessoafisica.nome, usuario.pessoafisica.foto, total_chamados])
        atendentes = sorted(atendentes, key=lambda atend: atend[3])

    return locals()


@rtr()
@permission_required(['centralservicos.add_interested'])
def adicionar_outros_interessados(request, chamado_id):
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    title = 'Adicionar Outros Interessados'
    if chamado.permite_visualizar(request.user):
        FormClass = AdicionarOutrosInteressadosFormFactory(request, chamado)
        form = FormClass(request.POST or None)
        if form.is_valid():
            try:
                chamado.adicionar_outros_interessados(form.cleaned_data.get('outros_interessados'))
                return httprr('..', 'Adição de outros interessados realizada com sucesso.')
            except ValidationError as e:
                messages.error(request, ''.join(e.messages))
    else:
        raise PermissionDenied('Você não tem permissão para adicionar outros interessados neste chamado.')

    return locals()


@rtr()
@permission_required(['centralservicos.add_interested'])
def adicionar_grupo_de_interessados(request, chamado_id):
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    title = 'Adicionar Grupo de Interessados'
    if chamado.permite_visualizar(request.user):
        FormClass = AdicionarGrupoInteressadosFormFactory(request, chamado)
        form = FormClass(request.POST or None)
        if form.is_valid():
            try:
                chamado.adicionar_grupos_interessados(form.cleaned_data.get('grupos_interessados'))
                return httprr('..', 'Adição de grupo de interessados realizada com sucesso.')
            except ValidationError as e:
                messages.error(request, ''.join(e.messages))
    else:
        raise PermissionDenied('Você não tem permissão para adicionar um grupo de interessados neste chamado.')

    return locals()


@rtr()
@permission_required(['centralservicos.remove_interested'])
def remover_outros_interessados(request, chamado_id, usuario_id):
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    usuario = get_object_or_404(User, pk=usuario_id)
    title = 'Remover Interessado'
    if chamado.permite_visualizar(request.user):
        if request.method == 'POST':
            chamado.outros_interessados.remove(usuario)
            if request.user != usuario:
                return httprr(chamado.get_absolute_url(), 'Interessado removido com sucesso.')
            else:
                return httprr('/', 'Interessado removido com sucesso.')

    else:
        raise PermissionDenied('Você não tem permissão para remover interessados neste chamado.')

    return locals()


@rtr()
@permission_required(['centralservicos.pode_unificar_baseconhecimento'])
def unificar_basesconhecimento(request):
    title = 'Unificar Bases de Conhecimento'
    if not request.GET.get('bases'):
        raise PermissionDenied('Nenhuma base de conhecimento selecionada.')

    ids = request.GET.getlist('bases')[0].split(',')
    bases = BaseConhecimento.objects.filter(id__in=ids)
    if request.method == 'POST':
        base_principal = BaseConhecimento.objects.get(pk=request.POST.get('base_id'))
        removeu = False
        for base in bases:
            if base != base_principal:
                for historico in HistoricoStatus.objects.filter(bases_conhecimento=base):
                    historico.bases_conhecimento.add(base_principal)
                    historico.bases_conhecimento.remove(base)
                base.delete()
                removeu = True
        bases = BaseConhecimento.objects.filter(id__in=ids)
        if removeu:
            messages.success(request, 'Bases de conhecimento unificadas com sucesso.')
    return locals()


@rtr()
@permission_required(['centralservicos.review_baseconhecimento'])
def revisar_basesconhecimento(request):
    title = 'Revisar Bases de Conhecimento'

    if request.GET.get('bases'):
        ids = request.GET.getlist('bases')[0].split(',')
        bases = BaseConhecimento.objects.filter(id__in=ids)
    if request.method == 'POST':
        ids = request.POST.getlist('base_id')
        if len(ids) == 0:
            messages.error(request, 'Nenhuma base de conhecimento foi selecionada.')
        else:
            BaseConhecimento.objects.filter(id__in=ids).update(necessita_correcao=False, supervisao_pendente=False)
            messages.success(request, 'Bases de conhecimento revisadas com sucesso.')

    return locals()


@rtr()
def marcar_baseconhecimento_para_correcao(request, baseconhecimento_id):
    title = 'Solicitar Correção da Base de Conhecimento'
    base_conhecimento = get_object_or_404(BaseConhecimento, pk=baseconhecimento_id)
    if request.method == 'POST':
        form = MarcarParaCorrecaoForm(request.POST)
        if form.is_valid():
            comentario = form.cleaned_data.get('comentario')
            base_conhecimento.marcar_para_correcao(comentario, request.user)
            return httprr(base_conhecimento.get_absolute_url(), 'Base de conhecimento marcada para correção.')
    else:
        form = MarcarParaCorrecaoForm()

    return locals()


@rtr('centralservicos/templates/visualizar_chamados_semelhantes.html')
@permission_required('centralservicos.solve_chamado')
def visualizar_chamados_semelhantes(request, chamado_id):
    title = 'Visualizar Chamados Semelhantes'
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    if chamado.eh_atendente(request.user):
        chamados = Chamado.objects.filter(status=StatusChamado.RESOLVIDO, servico_id=chamado.servico_id)[:20]
    else:
        raise PermissionDenied('Você não tem permissão para visualizar chamados semelhantes.')
    return locals()


@rtr('centralservicos/templates/visualizar_outros_chamados_do_interessado.html')
@permission_required('centralservicos.solve_chamado')
def visualizar_outros_chamados_do_interessado(request, chamado_id):
    title = 'Outros Chamados do Interessado'
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    chamados = Chamado.objects.exclude(pk=chamado.pk).filter(
        interessado_id=chamado.interessado_id, servico__centros_atendimento__area__in=chamado.servico.centros_atendimento.all().values_list('area', flat=True)
    ).distinct()[:20]
    return locals()


@rtr()
@permission_required('centralservicos.change_chamado')
def adicionar_tags_ao_chamado(request, chamado_id):
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    title = 'Adicionar tags a este chamado'
    FormClass = AdicionarTagsAoChamadoFormFactory(request, chamado)
    form = FormClass(request.POST or None)
    if form.is_valid():
        try:
            chamado.adicionar_tags(form.cleaned_data.get('tags'))
            return httprr('..', 'Adição de tags realizada com sucesso.')
        except ValidationError as e:
            messages.error(request, ''.join(e.messages))

    return locals()


@rtr()
@permission_required('centralservicos.change_chamado')
def remover_tag_do_chamado(request, chamado_id, tag_id):
    chamado = get_object_or_404(Chamado, pk=chamado_id)
    tag = get_object_or_404(Tag, pk=tag_id)
    if request.method == 'POST':
        chamado.tags.remove(tag)
        return httprr(chamado.get_absolute_url(), 'Tag removida com sucesso.')
    return locals()


@rtr()
@permission_required('centralservicos.delete_baseconhecimentoanexo')
def remover_anexo_baseconhecimento(request, baseconhecimento_id, baseconhecimento_anexo_id):
    baseconhecimento = get_object_or_404(BaseConhecimento, pk=baseconhecimento_id)
    baseconhecimento_anexo = get_object_or_404(BaseConhecimentoAnexo, pk=baseconhecimento_anexo_id)
    if request.method == 'POST':
        baseconhecimento_anexo.delete()
        return httprr(baseconhecimento.get_absolute_url(), 'Anexo removido com sucesso.')
    return locals()


@rtr('centralservicos/templates/visualizar_chamados_resolvidos.html.html')
def baseconhecimento_chamados_resolvidos(request, baseconhecimento_id):
    title = 'Chamados Resolvidos com Este Artigo'
    base_conhecimento = get_object_or_404(BaseConhecimento, pk=baseconhecimento_id)
    chamados = Chamado.objects.filter(
        pk__in=HistoricoStatus.objects.filter(status=StatusChamado.get_status_resolvido(), bases_conhecimento__id__in=[baseconhecimento_id]).values_list('chamado_id', flat=True)
    )
    return locals()


@rtr()
def monitoramento(request, token):
    obj = get_object_or_404(Monitoramento, token=token)
    title = 'Monitoramento de Chamados: {} '.format(obj.titulo)

    ha_pendencias = False
    resultado = []
    organizar_por_tipo = obj.organizar_por_tipo

    for grupo in obj.grupos.all():
        atendimentos = AtendimentoAtribuicao.objects.filter(grupo_atendimento=grupo, cancelado_em__isnull=True)

        qs_atribuidos = Chamado.ativos.filter(pk__in=atendimentos.filter(atribuido_para__isnull=False).values('chamado'))
        qs_nao_atribuidos = Chamado.ativos.filter(pk__in=atendimentos.filter(atribuido_para__isnull=True).values('chamado'))

        qtd_com_sla_estourado = Chamado.com_sla_estourado.filter(pk__in=atendimentos.filter(atribuido_para__isnull=False).values('chamado')).count()

        qtd_incidentes_atribuidos = qs_atribuidos.filter(servico__tipo=Servico.TIPO_INCIDENTE).count()
        qtd_incidentes_nao_atribuidos = qs_nao_atribuidos.filter(servico__tipo=Servico.TIPO_INCIDENTE).count()

        qtd_requisicoes_atribuidas = qs_atribuidos.filter(servico__tipo=Servico.TIPO_REQUISICAO).count()
        qtd_requisicoes_nao_atribuidas = qs_nao_atribuidos.filter(servico__tipo=Servico.TIPO_REQUISICAO).count()
        item = {
            'grupo': grupo,
            'qtd_incidentes_atribuidos': qtd_incidentes_atribuidos,
            'qtd_requisicoes_atribuidas': qtd_requisicoes_atribuidas,
            'qtd_atribuidos': qs_atribuidos.count(),
            'qtd_incidentes_nao_atribuidos': qtd_incidentes_nao_atribuidos,
            'qtd_requisicoes_nao_atribuidas': qtd_requisicoes_nao_atribuidas,
            'qtd_nao_atribuidos': qs_nao_atribuidos.count(),
            'qtd_com_sla_estourado': qtd_com_sla_estourado,
        }
        if qtd_incidentes_nao_atribuidos > 0 or qtd_requisicoes_nao_atribuidas > 0:
            ha_pendencias = True
        resultado.append(item)

    return locals()


@csrf_exempt
@login_required
def ac_interessado(request):
    qs = User.objects.filter(is_active=True, pessoafisica__isnull=False)
    q = request.POST.get('q', '')
    if q:
        qs = qs.filter(pessoafisica__search_fields_optimized__icontains=q)
    qs = qs.order_by('-eh_servidor', '-eh_prestador', 'pessoafisica__nome')
    data = generate_autocomplete_dict(qs, int(request.POST.get('page', 1)))
    return JsonResponse(data)
