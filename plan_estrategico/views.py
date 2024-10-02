from datetime import date, datetime
from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models.aggregates import Sum
from django.db.models.query import Prefetch
from django.db.models.query_utils import Q
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize

from comum.models import Configuracao
from comum.utils import get_sigla_reitoria, get_uo
from djtools import layout
from djtools.html.graficos import GroupedColumnChart, LineChart
from djtools.templatetags.filters import in_group
from djtools.utils import rtr, httprr, group_required, permission_required, get_session_cache
from plan_estrategico import tasks
from plan_estrategico.forms import (
    AssociarPerspectivaPDIForm,
    UnidadeGestoraForm,
    ProjetoEstrategicoPDIForm,
    EtapaProjetoForm,
    AssociarObjetivoPDIForm,
    AssociarIndicadorPDIForm,
    MetaIndicadorFormFactory,
    farol_filtro_formfactory,
    ObjetivoIndicadorFormFactory,
    VariavelCampusForm,
    farol_indicadores_filtro_formfactory,
    OrigemRecursoForm,
    AssociarProjetosPlanoAtividadeForm,
    AssociarEtapasProjetoPlanoAtividadeForm,
    AssociarOrigemRecursoProjetoPlanoAtividadeForm,
    AssociarOrigemRecursoEtapaProjetoPlanoAtividadeForm,
    OrigemRecursoProjetoForm,
    AssociarUnidadeGestoraEtapaProjetoPlanoAtividadeForm,
    AtividadeEtapaForm,
    GerenciarCompartilhamentoGEstorUAForm,
    NaturezaDespesaForm,
    ValoresOrigemRecursoEtapaForm,
    ValoresEtapaUnidadesForm,
    VariavelCampusIdealForm,
    ValoresEtapaAtividadesForm,
    filtro_indicadores_formfactory,
    OrigemRecursoEspecialForm,
    RelatorioDemonstrativoForm,
    RelatorioProjetoForm, RelatorioPlanoatividadeForm, RelatorioRankingForm, filtro_linhadotempo_formfactory)
from plan_estrategico.models import (
    PDI,
    PDIPerspectiva,
    UnidadeGestora,
    ObjetivoEstrategico,
    ProjetoEstrategico,
    EtapaProjeto,
    Indicador,
    MetaIndicador,
    PDIObjetivoEstrategico,
    PDIIndicador,
    ObjetivoIndicador,
    VariavelCampus,
    PlanoAtividade,
    TotalizadorIndicador,
    OrigemRecurso,
    ProjetoPlanoAtividade,
    EtapaProjetoPlanoAtividade,
    OrigemRecursoProjeto,
    AtividadeEtapa,
    CompartilhamentoPoderdeGestorUA,
    OrigemRecursoProjetoEtapa,
    UnidadeGestoraEtapa,
    NaturezaDespesaPlanoAtividade,
    UnidadeOrigemEtapa,
    PeriodoPreenchimentoVariavel,
    IndicadorTrimestralCampus,
    VariavelTrimestralCampus, TematicaVariavel, Variavel)
from plan_estrategico.utils import get_setor_unidade_gestora, iniciar_gerenciamento_acesso
from rh.models import UnidadeOrganizacional


@layout.servicos_anonimos()
def servicos_anonimos(request):

    servicos_anonimos = list()

    servicos_anonimos.append(dict(categoria='Consultas', titulo='Farol de Desempenho', icone='chart-line', url='/plan_estrategico/pdi/1/farol_consolidado/'))

    return servicos_anonimos


@layout.quadro('PDI: Farol de Desempenho', icone='chart-bar')
def index_quadros(quadro, request):
    def do():
        uo = None
        if request.user.eh_aluno:
            aluno = request.user.get_relacionamento()
            uo = aluno.curso_campus.diretoria.setor.uo

        if request.user.eh_servidor or request.user.eh_prestador:
            servidor = request.user.get_relacionamento()
            if servidor.setor:
                uo = servidor.setor.uo

        if uo is None or uo.sigla == get_sigla_reitoria():
            uo = None
        ano = date.today().year

        if not PeriodoPreenchimentoVariavel.objects.filter(ano__ano=ano, trimestre=1).exists() or PeriodoPreenchimentoVariavel.objects.filter(data_inicio__date__gte=date.today(), ano__ano=ano, trimestre=1).exists():
            ano = date.today().year - 1

        pdi = PDI.objects.all().first()
        if pdi:
            alcancados = TotalizadorIndicador.objects.filter(ano=ano, uo=uo, status=TotalizadorIndicador.INDICADOR_ALCANCADO).first()
            parcialmente_alcancados = TotalizadorIndicador.objects.filter(ano=ano, uo=uo, status=TotalizadorIndicador.INDICADOR_PARCIALMENTE_ALCANCADO).first()
            nao_alcancados = TotalizadorIndicador.objects.filter(ano=ano, uo=uo, status=TotalizadorIndicador.INDICADOR_NAO_ALCANCADO).first()

            if alcancados or parcialmente_alcancados or nao_alcancados:
                quadro.add_item(layout.ItemTitulo(titulo=f'Indicadores do ano {ano}:'))

            if alcancados:
                indicadores_alcancados = '{} <strong>{}</strong> {}'.format(
                    '<i class="fas fa-circle icon-success" aria-hidden="true"></i>', alcancados.total_indicadores, 'Alcançados'
                )
                quadro.add_item(layout.ItemLista(titulo='', valor=indicadores_alcancados))
            if parcialmente_alcancados:
                indicadores_parcialmente = '{} <strong>{}</strong> {}'.format(
                    '<i class="fas fa-circle icon-warning" aria-hidden="true"></i>', parcialmente_alcancados.total_indicadores, 'Parcialmente Alcançados'
                )
                quadro.add_item(layout.ItemLista(titulo='', valor=indicadores_parcialmente))
            if nao_alcancados:
                indicadores_nao_alcancados = '{} <strong>{}</strong> {}'.format(
                    '<i class="fas fa-circle icon-error" aria-hidden="true"></i>', nao_alcancados.total_indicadores, 'Não Alcançados'
                )
                quadro.add_item(layout.ItemLista(titulo='', valor=indicadores_nao_alcancados))
            quadro.add_item(layout.ItemAcessoRapido(titulo='Farol de Desempenho', url=f'plan_estrategico/pdi/{pdi.id}/farol/', icone='search'))
            if pdi.mapa_estrategico:
                quadro.add_item(layout.ItemAcessoRapido(titulo='Mapa Estratégico', url=pdi.mapa_estrategico.url, icone='file-download'))
        return quadro

    return get_session_cache(request, 'index_quadros_transformacao_pdi', do, 24 * 3600)


@layout.quadro('PDI: Situação do Farol', icone='chart-bar')
def index_quadros_contador_variaveis(quadro, request):

    uo = get_uo(request.user)
    if request.user.groups.filter(name='Gestor Estratégico Local').exists():
        if PeriodoPreenchimentoVariavel.get_em_periodo_de_preenchimento():
            ano = PeriodoPreenchimentoVariavel.get_em_periodo_de_preenchimento()[0].ano
            variaveis = VariavelCampus.objects.filter(uo=uo, ano=ano.ano, variavel__fonte='Manual', data_atualizacao__lt=PeriodoPreenchimentoVariavel.get_em_periodo_de_preenchimento()[0].data_inicio, situacao=VariavelCampus.ATIVA).count()
            variaveis_sempreenchimento = VariavelCampus.objects.filter(uo=uo, ano=ano.ano, variavel__fonte='Manual', data_atualizacao=None, situacao=VariavelCampus.ATIVA).count()
            variaveis = variaveis | variaveis_sempreenchimento
            if variaveis:
                quadro.add_item(
                    layout.ItemContador(
                        titulo='Variá{} do Farol de Desempenho'.format(pluralize(variaveis, 'vel,veis')),
                        subtitulo='Aguardando preenchimento',
                        qtd=variaveis,
                        url=f'/admin/plan_estrategico/variavelcampus/?uo__id__exact={uo.id}&ano={ano.ano}',
                    )
                )
    return quadro


@rtr()
@login_required()
def pdi_ver(request, pdi_pk=None):
    if pdi_pk:
        pdi = get_object_or_404(PDI, pk=pdi_pk)
    else:
        pdi = PDI.objects.latest('id')

    title = f'PDI - {pdi.ano_inicial_pdi} a {pdi.ano_final_pdi}'

    ano_atual = date.today().year

    pode_adicionar_objetivo = in_group(request.user, 'Administrador de Planejamento Estratégico')
    pode_ver_planoatividade = request.user.has_perm('plan_estrategico.view_planoatividade')
    # Montagem das unidades gestoras
    ugs = UnidadeGestora.objects.select_related().filter(pdi=pdi).order_by('tipo', 'setor_equivalente__sigla')

    anos_pdi = [ano for ano in range(pdi.ano_inicial_pdi.ano, pdi.ano_final_pdi.ano + 1)]

    # Montagem das Perspectivas
    perspectivas_pdi = PDIPerspectiva.objects.select_related().filter(pdi=pdi)
    query_dados = PDIPerspectiva.objects.filter(pdi=pdi)
    projetos = ProjetoEstrategico.objects.filter(pdi=pdi).order_by('codigo')

    plano_atividades = PlanoAtividade.objects.filter(pdi=pdi).order_by('-ano_base')
    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico')
def pdi_perspectivas_associar(request, pdi_pk):
    pdi = get_object_or_404(PDI, pk=pdi_pk)

    title = 'Associar Perspectivas ao PDI'

    form = AssociarPerspectivaPDIForm(request.POST or None, pdi=pdi)
    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada.')

    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico')
def pdi_objetivo_associar(request, pdi_pk, perspectiva_pk):
    pdi = get_object_or_404(PDI, pk=pdi_pk)
    perspectiva = get_object_or_404(PDIPerspectiva, pk=perspectiva_pk)

    if pdi.pk != perspectiva.pdi_id:
        return

    title = 'Associar Objetivos Estratégicos ao PDI'

    form = AssociarObjetivoPDIForm(request.POST or None, pdi=pdi, perspectiva=perspectiva)
    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada.')

    return locals()


@transaction.atomic
@rtr()
@permission_required('plan_estrategico.delete_projetoestrategico')
def remover_projeto(request, projeto_id):
    url = request.META.get('HTTP_REFERER', '.')
    projeto = get_object_or_404(ProjetoEstrategico, pk=projeto_id)
    if not projeto.pode_excluir_projeto(usuario=request.user):
        raise PermissionDenied()
    if ProjetoPlanoAtividade.objects.filter(projeto=projeto).exists():
        return httprr(url, 'O Projeto Estratégico está vinculado à um ou mais plano de atividades e não pode ser removido.', tag='error')
    else:
        projeto.delete()
        return httprr(url, 'Projeto Estratégico removido com sucesso.')


@transaction.atomic
@rtr()
@permission_required('plan_estrategico.delete_etapaprojeto')
def remover_etapa(request, etapa_id):
    url = request.META.get('HTTP_REFERER', '.')
    etapa = get_object_or_404(EtapaProjeto, pk=etapa_id)
    if not etapa.pode_excluir_etapa(usuario=request.user):
        raise PermissionDenied()
    if EtapaProjetoPlanoAtividade.objects.filter(etapa=etapa).exists():
        return httprr(url, 'A Etapa está vinculada à um ou mais plano de atividades e não pode ser removida.', tag='error')
    else:
        etapa.delete()
        return httprr(url, 'Etapa removida com sucesso.')


@rtr()
@group_required('Administrador de Planejamento Estratégico')
def pdi_unidadegestora_add_change(request, pdi_pk, ug_pk=None):
    pdi = get_object_or_404(PDI, pk=pdi_pk)
    ug = None

    title = '{} Unidade Gestora'.format(ug_pk and 'Editar' or 'Adicionar')

    if ug_pk:
        ug = get_object_or_404(UnidadeGestora, pk=ug_pk)

    form = UnidadeGestoraForm(request.POST or None, instance=ug, pdi=pdi)

    if form.is_valid():
        form.save()
        return httprr('..', 'Unidade Gestora salva.')

    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico, Gestor de Projeto')
def pdi_projeto_add_change(request, pdi_pk, projeto_pk=None):
    pdi = get_object_or_404(PDI, pk=pdi_pk)
    projeto = None

    title = '{} Projeto Estratégico'.format(projeto_pk and 'Editar' or 'Adicionar')

    if projeto_pk:
        projeto = get_object_or_404(ProjetoEstrategico, pk=projeto_pk)

        if not projeto.pode_editar_projeto(usuario=request.user):
            raise PermissionDenied()

    form = ProjetoEstrategicoPDIForm(request.POST or None, request.FILES or None, instance=projeto, pdi=pdi, request=request)

    if form.is_valid():
        form.save()
        return httprr(f'/plan_estrategico/pdi/{pdi_pk}/ver/?tab=projeto_estrategico', 'Projeto Estratégico salvo.')

    return locals()


@rtr()
@login_required()
def pdi_projeto_etapas(request, pdi_pk, projeto_pk):
    projetoestrategico = get_object_or_404(ProjetoEstrategico, pk=projeto_pk)
    etapas = EtapaProjeto.objects.filter(projeto=projeto_pk).order_by('codigo')
    title = f'Projeto Estratégico #{projetoestrategico.id}'

    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico, Gestor de Projeto')
def pdi_projeto_etapa_add_change(request, projeto_pk=None, etapa_pk=None):
    projeto = get_object_or_404(ProjetoEstrategico, pk=projeto_pk)
    etapa = None

    title = '{} Etapa do Projeto'.format(etapa_pk and 'Editar' or 'Adicionar')

    if etapa_pk:
        etapa = get_object_or_404(EtapaProjeto, pk=etapa_pk)

    form = EtapaProjetoForm(request.POST or None, instance=etapa, projeto=projeto)

    if form.is_valid():
        form.save()
        return httprr('..', 'Etapa do Projeto salva.')

    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico')
def pdi_indicador_associar(request, pdi_pk, objetivo_pk):
    pdi = get_object_or_404(PDI, pk=pdi_pk)
    pdi_objetivo = get_object_or_404(PDIObjetivoEstrategico, pk=objetivo_pk)

    if pdi.pk != pdi_objetivo.pdi_perspectiva.pdi_id:
        return

    title = f'PDI - {pdi.ano_inicial_pdi} a {pdi.ano_final_pdi}'

    form = AssociarIndicadorPDIForm(request.POST or None, pdi=pdi, objetivo=pdi_objetivo)
    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada.')

    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico')
def indicador_add_change(request, objetivo_pk=None, indicador_pk=None):
    objetivo = get_object_or_404(ObjetivoEstrategico, pk=objetivo_pk)
    indicador = None

    title = '{} Indicador'.format(indicador_pk and 'Editar' or 'Adicionar')

    if indicador_pk:
        indicador = get_object_or_404(Indicador, pk=indicador_pk)

    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico')
def pdi_meta_atualizar(request, pdi_pk, indicador_pk):
    pdi = get_object_or_404(PDI, pk=pdi_pk)
    indicador = get_object_or_404(PDIIndicador, pk=indicador_pk)

    title = f'Atualização das Metas - {indicador}'

    Klass = MetaIndicadorFormFactory(indicador)
    form = Klass(request.POST or None)

    if form.is_valid():
        form.save()
        return httprr('..', 'Meta salva.')

    return locals()


@rtr()
@login_required()
def pdi_ver_meta_indicador(request, indicador_pk, ano_base):
    pdi_indicador = get_object_or_404(PDIIndicador, pk=indicador_pk)

    title = f'Metas do Indicador para {ano_base}'
    lista_meta = []

    for uo in UnidadeOrganizacional.objects.uo().all():
        metas = dict()
        try:
            valor_meta = pdi_indicador.indicador.get_formula_valor_meta(uo, ano_base)
        except Exception:
            valor_meta = None
        metas['uo'] = uo
        metas['valor_meta'] = valor_meta

        lista_meta.append(metas)
    geral = pdi_indicador.indicador.get_formula_valor_meta(ano_base=ano_base, uo=None)
    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico, Gestor Estratégico Sistêmico, Gestor Estratégico Local')
def visualizar_variavel(request, variavel_pk):
    variavel = get_object_or_404(Variavel, pk=variavel_pk)

    title = f'Variável - {variavel}'
    indicadores = variavel.get_indicadores_variavel()
    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico')
def indicador_relevancia_atualizar(request, objetivo_pk):
    objetivo = get_object_or_404(PDIObjetivoEstrategico, pk=objetivo_pk)

    title = f'Atualização de Relevância - {objetivo}'

    Klass = ObjetivoIndicadorFormFactory(objetivo)
    form = Klass(request.POST or None)

    if form.is_valid():
        form.save()
        return httprr('..', 'Relevância salva.')

    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico, Gestor Estratégico Sistêmico, Gestor Estratégico Local')
def informar_valor_variavel(request, variavelcampus_pk):

    variavelcampus = get_object_or_404(VariavelCampus, pk=variavelcampus_pk)

    title = f'Atualização Valor da Variável - {variavelcampus.variavel.nome} - {variavelcampus.uo}'

    form = VariavelCampusForm(request.POST or None, instance=variavelcampus, request=request)

    if form.is_valid():
        o = form.save(False)
        o.data_atualizacao = datetime.now()
        o.valor_real = form.cleaned_data['valor_trimestral']
        o.save()
        trimestre = PeriodoPreenchimentoVariavel.objects.filter(data_termino__gte=datetime.now(), data_inicio__lte=datetime.now()).first().trimestre
        variavel_trimestral = VariavelTrimestralCampus.objects.get_or_create(variavel=variavelcampus, ano=variavelcampus.ano, trimestre=trimestre)[0]
        variavel_trimestral.valor = form.cleaned_data['valor_trimestral']
        variavel_trimestral.save()

        indicadores = PDIIndicador.objects.filter(indicador__forma_calculo__contains=variavelcampus.variavel.sigla)
        for indicador in indicadores:
            variaveis = indicador.indicador.get_variaveis()
            if variavelcampus.variavel not in variaveis:
                continue
            else:
                if VariavelCampus.objects.filter(
                    uo=variavelcampus.uo, ano=variavelcampus.ano, variavel__in=variaveis, variavel__fonte='Manual', valor_trimestral__isnull=True
                ).exists():
                    continue
            trimestre = PeriodoPreenchimentoVariavel.objects.filter(data_termino__gte=datetime.now(), data_inicio__lte=datetime.now()).first().trimestre
            indicadorTrimestral = IndicadorTrimestralCampus.objects.get_or_create(indicador=indicador, ano=variavelcampus.ano, trimestre=trimestre, uo=variavelcampus.uo)[0]
            indicadorTrimestral.valor = indicador.indicador.get_formula_valor(uo=variavelcampus.uo, ano_base=variavelcampus.ano)
            indicadorTrimestral.save()

        return httprr('..', 'Valor da Variável salvo.')

    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico')
def informar_valor_variavel_ideal(request, variavelcampus_pk):

    variavelcampus = get_object_or_404(VariavelCampus, pk=variavelcampus_pk)

    title = f'Atualização Valor da Variável - {variavelcampus.variavel.nome} - {variavelcampus.uo}'

    form = VariavelCampusIdealForm(request.POST or None, instance=variavelcampus, request=request)

    if form.is_valid():
        form.save()
        return httprr('..', 'Valor da Variável Ideal salvo.')

    return locals()


@rtr()
@login_required()
def pdi_farol_nivel_1(request, pdi_pk):
    pdi = get_object_or_404(PDI, pk=pdi_pk)
    ano_base = date.today().year
    perspectiva_id = None
    instance = request.user.get_relacionamento()
    uo = instance.setor.uo
    if uo is None or uo.sigla == get_sigla_reitoria():
        uo = None

    if ano_base < pdi.ano_inicial_pdi.ano:
        ano_base = pdi.ano_inicial_pdi.ano
    elif ano_base > pdi.ano_final_pdi.ano:
        ano_base = pdi.ano_final_pdi.ano
    sigla_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    FormKlass = farol_filtro_formfactory(pdi, sigla_instituicao)
    filter_form = FormKlass(request.POST or None, pdi=pdi, ano_base=ano_base, uo=uo)

    if filter_form.is_valid():
        ano_base = filter_form.cleaned_data.get('ano', ano_base)
        perspectiva_id = filter_form.cleaned_data.get('perspectiva', None)
        uo = filter_form.cleaned_data.get('campus', uo)

    perspectivas = (
        PDIPerspectiva.objects.select_related('perspectiva')
        .order_by('perspectiva')
        .prefetch_related(
            Prefetch(
                'pdiobjetivoestrategico_set',
                queryset=PDIObjetivoEstrategico.objects.select_related('objetivo').prefetch_related(
                    Prefetch(
                        'pdiindicador_set',
                        queryset=PDIIndicador.objects.select_related('indicador').prefetch_related(
                            Prefetch('metaindicador_set', queryset=MetaIndicador.objects.filter(ano=ano_base))
                        ),
                    )
                ),
            )
        )
    )

    if perspectiva_id:
        perspectivas = perspectivas.filter(perspectiva_id=perspectiva_id)

    pdi = PDI.objects.prefetch_related(Prefetch('perspectivas', queryset=perspectivas)).filter(pk=pdi_pk)

    if pdi.exists():
        pdi = pdi[0]

    title = f'Farol de Desempenho - {pdi}'

    for perspectiva in pdi.perspectivas.all():
        for objetivo in perspectiva.pdiobjetivoestrategico_set.all():
            objetivo.sigla = objetivo.objetivo.sigla
            objetivo.valor_meta = objetivo.get_objetivo_valor_meta(uo, ano_base)
            objetivo.valor_real = objetivo.get_objetivo_valor_real(uo, ano_base)
            objetivo.status = objetivo.get_status_farol_objetivo(uo, ano_base)
    return locals()


def calcular_indicadores_farol(objetivo, uo, ano_base):
    farol = dict()
    farol['indicador'] = objetivo.indicador
    if uo:
        farol['uo'] = uo
    trimestre_atual = int((date.today().month - 1) / 3 + 1)
    if ano_base and int(ano_base) == date.today().year:
        if objetivo.indicador.verificar_variavel_real_vazia(uo, ano_base) or trimestre_atual == 1:
            farol['valor_formula'] = 'Aguardando Valor'
        else:
            objetivo.indicador.indicador.valor_real = objetivo.indicador.indicador.get_formula_valor(uo, ano_base)
            farol['valor_formula'] = objetivo.indicador.indicador.valor_real

        if objetivo.indicador.indicador.indicador_acompanhamento:
            farol['meta'] = None
            farol['meta_anual'] = None
        elif objetivo.indicador.verificar_variavel_ideal_vazia(uo, ano_base):
            farol['meta'] = 'Aguardando Valor'
            farol['meta_anual'] = 'Aguardando Valor'
        else:
            objetivo.indicador.indicador.valor_meta = objetivo.indicador.indicador.get_formula_valor_meta(uo, ano_base)
            farol['meta_anual'] = objetivo.indicador.indicador.valor_meta
            farol['meta'] = objetivo.indicador.indicador.valor_meta
            if objetivo.indicador.indicador.tendencia == Indicador.DIRECAO_ALTA and not objetivo.indicador.indicador.sem_escalonamento_trimestral:
                if trimestre_atual == 1:
                    farol['meta'] = objetivo.indicador.indicador.valor_meta / 4
                else:
                    farol['meta'] = (objetivo.indicador.indicador.valor_meta / 4.0) * (trimestre_atual - 1)
            objetivo.indicador.indicador.valor_meta = farol['meta']

        if trimestre_atual == 1:
            farol['status'] = 'Aguardando Medição'
            if objetivo.indicador.indicador.indicador_acompanhamento:
                farol['status'] = 'Indicador de Acompanhamento'
        else:
            farol['status'] = objetivo.indicador.get_status_farol(uo, ano_base)
    else:
        if objetivo.indicador.verificar_variavel_real_vazia(uo, ano_base):
            farol['valor_formula'] = 'Aguardando Valor'
        else:
            objetivo.indicador.indicador.valor_real = objetivo.indicador.indicador.get_formula_valor(uo, ano_base)
            farol['valor_formula'] = objetivo.indicador.indicador.valor_real

        if objetivo.indicador.indicador.indicador_acompanhamento:
            farol['meta'] = None
            farol['meta_anual'] = None
        elif objetivo.indicador.verificar_variavel_ideal_vazia(uo, ano_base):
            farol['meta'] = 'Aguardando Valor'
            farol['meta_anual'] = 'Aguardando Valor'
        else:
            objetivo.indicador.indicador.valor_meta = objetivo.indicador.indicador.get_formula_valor_meta(uo, ano_base)
            farol['meta_anual'] = objetivo.indicador.indicador.valor_meta
            farol['meta'] = objetivo.indicador.indicador.valor_meta
            objetivo.indicador.indicador.valor_meta = farol['meta']

        farol['status'] = objetivo.indicador.get_status_farol(uo, ano_base)
    return farol


@rtr()
@login_required()
def pdi_farol_nivel_2(request, pdi_pk, objetivo_pk, ano_base, uo=None):
    pdi = get_object_or_404(PDI, pk=pdi_pk)
    objetivo = get_object_or_404(PDIObjetivoEstrategico, pk=objetivo_pk)
    if ano_base:
        ano_base = ano_base
    indicador_selecionado = False
    perspectiva_id = None
    uos = UnidadeOrganizacional.objects.uo().all()
    indicador = None
    if uo:
        uo = get_object_or_404(UnidadeOrganizacional, pk=uo)

    sigla_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    FormKlass = farol_indicadores_filtro_formfactory(pdi, sigla_instituicao, objetivo)
    filter_form = FormKlass(request.POST or None, pdi=pdi, ano_base=ano_base, uo=uo)
    if filter_form.is_valid():
        ano_base = filter_form.cleaned_data.get('ano', ano_base)
        uo = filter_form.cleaned_data.get('campus', uo)
        indicador = filter_form.cleaned_data.get('indicador')
    title = f'Farol de Desempenho - Objetivo Estratégico {objetivo.objetivo.sigla}'
    objetivoindicador = ObjetivoIndicador.objects.filter(objetivo_estrategico=objetivo).order_by('indicador__indicador__sigla')
    lista_inds = []
    if indicador:
        objetivoindicador = ObjetivoIndicador.objects.filter(objetivo_estrategico=objetivo, indicador=indicador)
        indicador_selecionado = True
    if not uo and indicador:
        for uo in uos:
            for objetivo in objetivoindicador:
                farol = calcular_indicadores_farol(objetivo, uo, ano_base)
                lista_inds.append(farol)
    else:
        for objetivo in objetivoindicador:
            farol = calcular_indicadores_farol(objetivo, uo, ano_base)
            lista_inds.append(farol)
    return locals()


@rtr()
def pdi_farol_nivel_1_consolidado(request, pdi_pk):
    # Tela usada na tela inicial para o publico ter acesso ao farol consolidado
    pdi = get_object_or_404(PDI, pk=pdi_pk)
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    ano_base = date.today().year
    perspectiva_id = None
    uo = None
    if ano_base < pdi.ano_inicial_pdi.ano:
        ano_base = pdi.ano_inicial_pdi.ano
    elif ano_base > pdi.ano_final_pdi.ano:
        ano_base = pdi.ano_final_pdi.ano
    sigla_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    FormKlass = farol_filtro_formfactory(pdi, sigla_instituicao)
    filter_form = FormKlass(request.POST or None, pdi=pdi, ano_base=ano_base, uo=uo)

    if filter_form.is_valid():
        ano_base = filter_form.cleaned_data.get('ano', ano_base)
        perspectiva_id = filter_form.cleaned_data.get('perspectiva', None)
        uo = filter_form.cleaned_data.get('campus', uo)

    perspectivas = (
        PDIPerspectiva.objects.select_related('perspectiva')
        .order_by('perspectiva')
        .prefetch_related(
            Prefetch(
                'pdiobjetivoestrategico_set',
                queryset=PDIObjetivoEstrategico.objects.select_related('objetivo').prefetch_related(
                    Prefetch(
                        'pdiindicador_set',
                        queryset=PDIIndicador.objects.select_related('indicador').prefetch_related(
                            Prefetch('metaindicador_set', queryset=MetaIndicador.objects.filter(ano=ano_base))
                        ),
                    )
                ),
            )
        )
    )

    if perspectiva_id:
        perspectivas = perspectivas.filter(perspectiva_id=perspectiva_id)

    pdi = PDI.objects.prefetch_related(Prefetch('perspectivas', queryset=perspectivas)).filter(pk=pdi_pk)

    if pdi.exists():
        pdi = pdi[0]

    title = f'Farol de Desempenho - {pdi}'

    for perspectiva in pdi.perspectivas.all():
        for objetivo in perspectiva.pdiobjetivoestrategico_set.all():
            objetivo.sigla = objetivo.objetivo.sigla
            objetivo.valor_meta = objetivo.get_objetivo_valor_meta(uo, ano_base)
            objetivo.valor_real = objetivo.get_objetivo_valor_real(uo, ano_base)
            objetivo.status = objetivo.get_status_farol_objetivo(uo, ano_base)
    return locals()


def calcular_indicadores_farol_consolidado(objetivo, uo, ano_base):
    periodo = None
    trimestre_atual = int((date.today().month - 1) / 3 + 1)
    if PeriodoPreenchimentoVariavel.get_em_periodo_de_preenchimento():
        periodo = PeriodoPreenchimentoVariavel.objects.filter(data_termino__date__lt=date.today()).order_by('-id')[0]
        trimestre = periodo.trimestre

    farol = dict()
    farol['indicador'] = objetivo.indicador
    if uo:
        farol['uo'] = uo
    if ano_base and int(ano_base) == date.today().year:
        if objetivo.indicador.verificar_variavel_real_vazia(uo, ano_base):
            farol['valor_formula'] = 'Aguardando Valor'
        else:
            objetivo.indicador.indicador.valor_real = objetivo.indicador.indicador.get_formula_valor(uo, ano_base)
            try:
                farol['valor_formula'] = IndicadorTrimestralCampus.objects.filter(indicador=objetivo.indicador,
                                                                                  trimestre=trimestre_atual, uo=uo,
                                                                                  ano=ano_base).first().valor
            except Exception:
                farol['valor_formula'] = objetivo.indicador.indicador.valor_real
        if objetivo.indicador.indicador.indicador_acompanhamento:
            farol['meta'] = None
            farol['meta_anual'] = None
        elif objetivo.indicador.verificar_variavel_ideal_vazia(uo, ano_base):
            farol['meta'] = 'Aguardando Valor'
            farol['meta_anual'] = 'Aguardando Valor'
        else:
            objetivo.indicador.indicador.valor_meta = objetivo.indicador.indicador.get_formula_valor_meta(uo,
                                                                                                          ano_base)
            farol['meta_anual'] = objetivo.indicador.indicador.valor_meta
            farol['meta'] = objetivo.indicador.indicador.valor_meta
            if objetivo.indicador.indicador.tendencia == Indicador.DIRECAO_ALTA and not objetivo.indicador.indicador.sem_escalonamento_trimestral:
                if trimestre_atual == 1:
                    farol['meta'] = objetivo.indicador.indicador.valor_meta / 4
                else:
                    if periodo:
                        farol['meta'] = (objetivo.indicador.indicador.valor_meta / 4.0) * (trimestre)
                    else:
                        farol['meta'] = (objetivo.indicador.indicador.valor_meta / 4.0) * (trimestre_atual - 1)
            objetivo.indicador.indicador.valor_meta = farol['meta']

        if objetivo.indicador.indicador.indicador_acompanhamento:
            farol['status'] = 'Indicador de Acompanhamento'
        else:
            farol['status'] = objetivo.indicador.get_status_farol(uo, ano_base, valor_real=farol['valor_formula'])
    else:
        if objetivo.indicador.verificar_variavel_real_vazia(uo, ano_base):
            farol['valor_formula'] = 'Aguardando Valor'
        else:
            objetivo.indicador.indicador.valor_real = objetivo.indicador.indicador.get_formula_valor(uo, ano_base)
            farol['valor_formula'] = objetivo.indicador.indicador.valor_real

        if objetivo.indicador.indicador.indicador_acompanhamento:
            farol['meta'] = None
            farol['meta_anual'] = None
        elif objetivo.indicador.verificar_variavel_ideal_vazia(uo, ano_base):
            farol['meta'] = 'Aguardando Valor'
            farol['meta_anual'] = 'Aguardando Valor'
        else:
            objetivo.indicador.indicador.valor_meta = objetivo.indicador.indicador.get_formula_valor_meta(uo,
                                                                                                          ano_base)
            farol['meta_anual'] = objetivo.indicador.indicador.valor_meta
            farol['meta'] = objetivo.indicador.indicador.valor_meta
            objetivo.indicador.indicador.valor_meta = farol['meta']

        farol['status'] = objetivo.indicador.get_status_farol(uo, ano_base)
    return farol


@rtr()
def pdi_farol_nivel_2_consolidado(request, pdi_pk, objetivo_pk, ano_base, uo=None):
    # Tela usada na tela inicial para o publico ter acesso ao farol consolidado
    pdi = get_object_or_404(PDI, pk=pdi_pk)
    if ano_base:
        ano_base = ano_base
    perspectiva_id = None
    uo = None
    indicador = None
    objetivo = get_object_or_404(PDIObjetivoEstrategico, pk=objetivo_pk)
    sigla_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    FormKlass = farol_indicadores_filtro_formfactory(pdi, sigla_instituicao, objetivo)
    filter_form = FormKlass(request.POST or None, pdi=pdi, ano_base=ano_base, uo=uo)
    uos = UnidadeOrganizacional.objects.uo().all()
    if filter_form.is_valid():
        ano_base = filter_form.cleaned_data.get('ano', ano_base)
        uo = filter_form.cleaned_data.get('campus', uo)
        indicador = filter_form.cleaned_data.get('indicador')
    title = f'Farol de Desempenho - Objetivo Estratégico {objetivo.objetivo.sigla}'
    objetivoindicador = ObjetivoIndicador.objects.filter(objetivo_estrategico=objetivo).order_by(
        'indicador__indicador__sigla')
    lista_inds = []
    if indicador:
        objetivoindicador = ObjetivoIndicador.objects.filter(objetivo_estrategico=objetivo, indicador=indicador)
        indicador_selecionado = True
    if not uo and indicador:
        for uo in uos:
            for objetivo in objetivoindicador:
                farol = calcular_indicadores_farol_consolidado(objetivo, uo, ano_base)
                lista_inds.append(farol)
    else:
        for objetivo in objetivoindicador:
            farol = calcular_indicadores_farol_consolidado(objetivo, uo, ano_base)
            lista_inds.append(farol)
    return locals()


@rtr()
def ver_detalhamento(request, objetivo_pk, indicador_pk):
    title = 'Detalhamento do Indicador'
    pdiindicador = get_object_or_404(PDIIndicador, pk=indicador_pk)
    objetivo = get_object_or_404(ObjetivoIndicador, indicador=pdiindicador, objetivo_estrategico_id=objetivo_pk)
    return locals()


@rtr()
def ver_grafico_indicadores(request, indicador_pk, ano_base=None, uo=None):
    title = 'Gráfico'
    pdi_indicador = get_object_or_404(PDIIndicador, pk=indicador_pk)
    if uo:
        uo = get_object_or_404(UnidadeOrganizacional, pk=uo)
    valores_grafico = []

    ano_base = date.today().year if not ano_base else ano_base

    valores_grafico.append([pdi_indicador.indicador.get_formula_valor_meta(uo, ano_base), pdi_indicador.indicador.get_formula_valor(uo, ano_base)])
    nome_pk = f'grafico_indicador_{pdi_indicador.pk}'
    meta_ano_anterior = IndicadorTrimestralCampus.objects.filter(indicador=pdi_indicador, trimestre=4, uo=uo, ano=int(ano_base) - 1)
    trimestre_1 = IndicadorTrimestralCampus.objects.filter(indicador=pdi_indicador, trimestre=1, uo=uo, ano=ano_base).first()
    trimestre_2 = IndicadorTrimestralCampus.objects.filter(indicador=pdi_indicador, trimestre=2, uo=uo, ano=ano_base).first()
    trimestre_3 = IndicadorTrimestralCampus.objects.filter(indicador=pdi_indicador, trimestre=3, uo=uo, ano=ano_base).first()
    trimestre_4 = IndicadorTrimestralCampus.objects.filter(indicador=pdi_indicador, trimestre=4, uo=uo, ano=ano_base).first()

    series2 = []
    if meta_ano_anterior:
        meta_trimestral = round(pdi_indicador.indicador.get_formula_valor_meta(uo, int(ano_base) - 1), 1)
        serie = [meta_ano_anterior.first().ano]
        serie.append(round(meta_trimestral, 1))
        serie.append(meta_ano_anterior.first() and float(meta_ano_anterior.first().valor) or 0)
        series2.append(serie)

    if pdi_indicador.indicador.tendencia == Indicador.DIRECAO_ALTA:
        meta_trimestral = round(pdi_indicador.indicador.get_formula_valor_meta(uo, ano_base) / 4, 1)

        serie = ['1º Tri']
        serie.append(round(meta_trimestral, 1))
        serie.append(trimestre_1 and float(trimestre_1.valor) or 0)
        series2.append(serie)

        serie = ['2º Tri']
        serie.append(round(meta_trimestral * 2, 1))
        serie.append(trimestre_2 and float(trimestre_2.valor) or 0)
        series2.append(serie)

        serie = ['3º Tri']
        serie.append(round(meta_trimestral * 3, 1))
        serie.append(trimestre_3 and float(trimestre_3.valor) or 0)
        series2.append(serie)

        serie = ['4º Tri']
        serie.append(round(meta_trimestral * 4, 1))
        serie.append(trimestre_4 and float(trimestre_4.valor) or 0)
        series2.append(serie)

    else:
        meta_anual = round(pdi_indicador.indicador.get_formula_valor_meta(uo, ano_base), 1)
        serie = ['1º Tri']
        serie.append(meta_anual)
        serie.append(trimestre_1 and float(trimestre_1.valor) or 0)
        series2.append(serie)

        serie = ['2º Tri']
        serie.append(meta_anual)
        serie.append(trimestre_2 and float(trimestre_2.valor) or 0)
        series2.append(serie)

        serie = ['3º Tri']
        serie.append(meta_anual)
        serie.append(trimestre_3 and float(trimestre_3.valor) or 0)
        series2.append(serie)

        serie = ['4º Tri']
        serie.append(meta_anual)
        serie.append(trimestre_4 and float(trimestre_4.valor) or 0)
        series2.append(serie)

    groups = []
    for tipo in ['Meta', 'Valor Alcançado']:
        groups.append(tipo)

    descricao = 'Total'
    if pdi_indicador.indicador.tipo == Indicador.TIPO_PERCENTUAL:
        descricao = 'Total (%)'

    grafico_indicador = GroupedColumnChart(
        'div_grafico',
        title=f'{pdi_indicador}',
        subtitle=f'{pdi_indicador.indicador.finalidade}',
        data=series2,
        groups=groups,
        yAxis_title_text=descricao,
        plotOptions_line_dataLabels_enable=True,
        plotOptions_line_enableMouseTracking=True,
        plotOptions=dict(column=dict(dataLabels=dict(enabled='true')))
    )
    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico, Gestor Estratégico Local, Gestor Estratégico Sistêmico')
def ver_valores_trimestrais(request, variavel_pk):
    variavelcampus = get_object_or_404(VariavelCampus, pk=variavel_pk)
    tri1 = VariavelTrimestralCampus.objects.filter(variavel=variavelcampus, trimestre=1).first()
    tri2 = VariavelTrimestralCampus.objects.filter(variavel=variavelcampus, trimestre=2).first()
    tri3 = VariavelTrimestralCampus.objects.filter(variavel=variavelcampus, trimestre=3).first()
    tri4 = VariavelTrimestralCampus.objects.filter(variavel=variavelcampus, trimestre=4).first()

    title = f'Valores Trimestrais da Variável - {variavelcampus.variavel.sigla}'

    return locals()


@rtr()
def ver_faixas_valores_indicador(request, indicador_pk, ano_base=None, uo=None):
    title = 'Faixa de Valores do Indicador RFP'
    pdi_indicador = get_object_or_404(PDIIndicador, pk=indicador_pk)
    if uo:
        uo = get_object_or_404(UnidadeOrganizacional, pk=uo)
    valores_grafico = []

    ano_base = date.today().year if not ano_base else ano_base
    if uo:
        rfp_faixa_1 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_1', uo=uo, ano=ano_base).first().valor_real or 0
        rfp_faixa_2 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_2', uo=uo, ano=ano_base).first().valor_real or 0
        rfp_faixa_3 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_3', uo=uo, ano=ano_base).first().valor_real or 0
        rfp_faixa_4 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_4', uo=uo, ano=ano_base).first().valor_real or 0
        rfp_faixa_5 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_5', uo=uo, ano=ano_base).first().valor_real or 0
        rfp_faixa_6 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_6', uo=uo, ano=ano_base).first().valor_real or 0
        rfp_faixa_7 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_7', uo=uo, ano=ano_base).first().valor_real or 0
    else:
        rfp_faixa_1 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_1', ano=ano_base).aggregate(total=Sum('valor_real'))
        rfp_faixa_1 = rfp_faixa_1['total'] or 0
        rfp_faixa_2 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_2', ano=ano_base).aggregate(total=Sum('valor_real'))
        rfp_faixa_2 = rfp_faixa_2['total'] or 0
        rfp_faixa_3 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_3', ano=ano_base).aggregate(total=Sum('valor_real'))
        rfp_faixa_3 = rfp_faixa_3['total'] or 0
        rfp_faixa_4 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_4', ano=ano_base).aggregate(total=Sum('valor_real'))
        rfp_faixa_4 = rfp_faixa_4['total'] or 0
        rfp_faixa_5 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_5', ano=ano_base).aggregate(total=Sum('valor_real'))
        rfp_faixa_5 = rfp_faixa_5['total'] or 0
        rfp_faixa_6 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_6', ano=ano_base).aggregate(total=Sum('valor_real'))
        rfp_faixa_6 = rfp_faixa_6['total'] or 0
        rfp_faixa_7 = VariavelCampus.objects.filter(variavel__sigla='RFP_faixa_7', ano=ano_base).aggregate(total=Sum('valor_real'))
        rfp_faixa_7 = rfp_faixa_7['total'] or 0

    total = rfp_faixa_1 + rfp_faixa_2 + rfp_faixa_3 + rfp_faixa_4 + rfp_faixa_5 + rfp_faixa_6 + rfp_faixa_7
    if total == Decimal(0):
        total = Decimal(1)  # evitar divisao por zero
    total_faixa_1 = ('%.2f' % ((rfp_faixa_1 * 100) / total)) + ' %'
    total_faixa_2 = ('%.2f' % ((rfp_faixa_2 * 100) / total)) + ' %'
    total_faixa_3 = ('%.2f' % ((rfp_faixa_3 * 100) / total)) + ' %'
    total_faixa_4 = ('%.2f' % ((rfp_faixa_4 * 100) / total)) + ' %'
    total_faixa_5 = ('%.2f' % ((rfp_faixa_5 * 100) / total)) + ' %'
    total_faixa_6 = ('%.2f' % ((rfp_faixa_6 * 100) / total)) + ' %'
    total_faixa_7 = ('%.2f' % ((rfp_faixa_7 * 100) / total)) + ' %'

    return locals()


@rtr()
@permission_required('plan_estrategico.view_planoatividade')
def ver_plano_atividade(request, plano_atividade_pk):
    plano_atividade = get_object_or_404(PlanoAtividade, pk=plano_atividade_pk)
    title = f'Plano de atividades - {plano_atividade.ano_base}'
    origemrecurso = OrigemRecurso.objects.filter(plano_atividade=plano_atividade)
    natureza_despesa = NaturezaDespesaPlanoAtividade.objects.filter(plano_atividade=plano_atividade)
    projetos = plano_atividade.projetos.all().order_by('projetoplanoatividade__plano_atividade__projetos__codigo')

    # Permissões
    em_periodo_preloa = plano_atividade.em_periodo_orcamentario_preloa or plano_atividade.em_periodo_projeto_preloa or plano_atividade.em_periodo_atividade_preloa
    origem_recurso_pode_incluir = OrigemRecurso.pode_incluir(usuario=request.user, plano_atividade=plano_atividade)
    origem_recurso_pode_alterar = OrigemRecurso.pode_alterar(usuario=request.user, plano_atividade=plano_atividade)
    origem_recurso_pode_excluir = OrigemRecurso.pode_excluir(usuario=request.user, plano_atividade=plano_atividade)

    natureza_despesa_pode_gerenciar = NaturezaDespesaPlanoAtividade.pode_gerenciar(usuario=request.user, plano_atividade=plano_atividade)
    natureza_despesa_pode_excluir = NaturezaDespesaPlanoAtividade.pode_excluir(usuario=request.user, plano_atividade=plano_atividade)

    atividade_pode_editar = AtividadeEtapa.pode_editar_atividade(usuario=request.user, plano_atividade=plano_atividade)
    atividade_pode_incluir = AtividadeEtapa.pode_incluir_atividade(usuario=request.user, plano_atividade=plano_atividade)

    pode_incluir_dados_orcamentarios = OrigemRecurso.pode_incluir_dados_orcamentarios(usuario=request.user, plano_atividade=plano_atividade)

    origem_recurso_pode_incluir_valor = OrigemRecursoProjeto.pode_incluir_valor(usuario=request.user, plano_atividade=plano_atividade)

    origem_recurso_pode_ratear_valor = OrigemRecursoProjeto.pode_ratear_valor(plano_atividade=plano_atividade)

    projeto_plano_atividade_pode_incluir = ProjetoPlanoAtividade.pode_incluir(usuario=request.user, plano_atividade=plano_atividade)
    em_periodo_atividades_posloa = plano_atividade.em_periodo_atividades_posloa

    eh_auditor = request.user.has_perm('rh.auditor')
    eh_administrador = ProjetoPlanoAtividade.eh_administrador(usuario=request.user)
    eh_gestor = ProjetoPlanoAtividade.eh_gestor(usuario=request.user)
    eh_coordenador = ProjetoPlanoAtividade.eh_coordenador(usuario=request.user)

    pode_ver_atividades = AtividadeEtapa.pode_ver_atividade(usuario=request.user, plano_atividade=plano_atividade)

    pode_ver_todas_atividades = AtividadeEtapa.pode_ver_todas_atividades(usuario=request.user, plano_atividade=plano_atividade)

    tem_etapa_especial = plano_atividade.projetoplanoatividade_set.filter(etapaprojetoplanoatividade__tipo_especial=True).first()
    # se é gestor ver somente projetos de sua UG
    if eh_administrador or eh_auditor:
        projetos_plano_atividade = plano_atividade.projetoplanoatividade_set.all().order_by('projeto__codigo')
    elif eh_gestor:
        etapas = UnidadeGestoraEtapa.objects.filter(unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)).values_list('etapa_projeto_plano_atividade')

        projetos_plano_atividade = ProjetoPlanoAtividade.objects.filter(plano_atividade=plano_atividade)
        projetos_plano_atividade = projetos_plano_atividade.filter(Q(projeto__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)) | Q(etapaprojetoplanoatividade__in=etapas)).order_by('projeto__codigo').distinct()

    elif eh_coordenador:
        etapas = UnidadeGestoraEtapa.objects.filter(unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)).values_list('etapa_projeto_plano_atividade')
        projetos_plano_atividade = (
            ProjetoPlanoAtividade.objects.filter(plano_atividade=plano_atividade, etapaprojetoplanoatividade__in=etapas).order_by('projeto__codigo').distinct()
        )
    return locals()


@rtr()
@login_required()
def ver_atividades_etapa(request, etapa_pk):
    etapa_projeto_plano_atividade = get_object_or_404(EtapaProjetoPlanoAtividade, pk=etapa_pk)

    # Projetos no qual o usuário é dono
    projetos_donos = ProjetoPlanoAtividade.objects.filter(
        plano_atividade=etapa_projeto_plano_atividade.projeto_plano_atividade.plano_atividade,
        projeto__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user),
    ).values_list('projeto__pk')

    # verifica se a etapa é de um projeto no qual o usuário logado é dono
    lista_pks_projetos_que_usuario_ehdono = []
    for t in projetos_donos:
        for x in t:
            lista_pks_projetos_que_usuario_ehdono.append(x)
    projeto_pk_da_etapa = etapa_projeto_plano_atividade.projeto_plano_atividade.projeto.pk

    eh_dono = any(elem == projeto_pk_da_etapa for elem in lista_pks_projetos_que_usuario_ehdono)

    eh_coordenador = ProjetoPlanoAtividade.eh_coordenador(usuario=request.user)
    eh_administrador = ProjetoPlanoAtividade.eh_administrador(usuario=request.user)
    eh_gestor = ProjetoPlanoAtividade.eh_gestor(usuario=request.user)

    atividade_pode_editar = AtividadeEtapa.pode_editar_atividade(usuario=request.user, plano_atividade=etapa_projeto_plano_atividade.projeto_plano_atividade.plano_atividade)
    atividade_pode_incluir = AtividadeEtapa.pode_incluir_atividade(usuario=request.user, plano_atividade=etapa_projeto_plano_atividade.projeto_plano_atividade.plano_atividade)

    atividade_pode_excluir = AtividadeEtapa.pode_excluir_atividade(usuario=request.user, plano_atividade=etapa_projeto_plano_atividade.projeto_plano_atividade.plano_atividade)

    if (eh_gestor and eh_dono) or eh_administrador:  # ver tudo
        atividades_etapa = AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade=etapa_projeto_plano_atividade).order_by('unidade_gestora')
    elif (eh_coordenador) or (eh_gestor and not eh_dono):  # Ver somente dele
        atividades_etapa = AtividadeEtapa.objects.filter(
            etapa_projeto_plano_atividade=etapa_projeto_plano_atividade, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)
        ).order_by('unidade_gestora')

    origens_recurso_etapa = UnidadeOrigemEtapa.objects.filter(
        origem_recurso_etapa__etapa_projeto_plano_atividade=etapa_projeto_plano_atividade,
        unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user),
    )
    pode_ratear_valor_atividade = OrigemRecursoProjeto.pode_ratear_valor_atividade(
        usuario=request.user, plano_atividade=etapa_projeto_plano_atividade.projeto_plano_atividade.plano_atividade
    )
    origens = OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade=etapa_projeto_plano_atividade)

    return locals()


@rtr()
@permission_required('plan_estrategico.view_planoatividade')
def plano_atividade_detalhar_projeto(request, projeto_pk):
    projetoestrategico = get_object_or_404(ProjetoEstrategico, pk=projeto_pk)
    title = f'Projeto Estratégico - #{projeto_pk}'

    return locals()


@rtr()
@login_required()
def planoatividade_origemrecurso_add_change(request, plano_atividade_pk, origem_pk=None):
    plano_atividade = get_object_or_404(PlanoAtividade, pk=plano_atividade_pk)
    origem_recurso = None
    title = '{} Origem de Recurso'.format(origem_pk and 'Editar' or 'Adicionar')

    if not OrigemRecurso.pode_alterar(usuario=request.user, plano_atividade=plano_atividade):
        return httprr('..', 'Operação não permitida.', tag='error')
    else:
        if not OrigemRecurso.pode_incluir(usuario=request.user, plano_atividade=plano_atividade):
            return httprr('..', 'Operação não permitida.', tag='error')

    if origem_pk:
        origem_recurso = get_object_or_404(OrigemRecurso, pk=origem_pk)

    form = OrigemRecursoForm(request.POST or None, instance=origem_recurso, plano_atividade=plano_atividade, request=request)

    if form.is_valid():
        form.save()
        return httprr('..', 'Origem de Recurso Salva.')

    return locals()


@rtr()
@login_required()
def planoatividade_naturezadespesa_add_change(request, plano_atividade_pk, natureza_despesa_pk=None):
    plano_atividade = get_object_or_404(PlanoAtividade, pk=plano_atividade_pk)
    natureza_despesa = None
    title = '{} Natureza de Despesa'.format(natureza_despesa_pk and 'Editar' or 'Adicionar')

    if not OrigemRecurso.pode_alterar(usuario=request.user, plano_atividade=plano_atividade):
        return httprr('..', 'Operação não permitida.', tag='error')
    else:
        if not OrigemRecurso.pode_incluir(usuario=request.user, plano_atividade=plano_atividade):
            return httprr('..', 'Operação não permitida.', tag='error')

    if natureza_despesa_pk:
        natureza_despesa = get_object_or_404(NaturezaDespesaPlanoAtividade, pk=natureza_despesa_pk)

    form = NaturezaDespesaForm(request.POST or None, instance=natureza_despesa, plano_atividade=plano_atividade, request=request)

    if form.is_valid():
        form.save()
        return httprr('..', 'Natureza de Despesa Salva.')

    return locals()


@rtr()
@login_required()
@transaction.atomic
def planoatividade_origemrecurso_delete(request, plano_atividade_pk, origem_pk=None):
    plano_atividade = get_object_or_404(PlanoAtividade, pk=plano_atividade_pk)
    origem_recurso = get_object_or_404(OrigemRecurso, pk=origem_pk)
    url = f'/plan_estrategico/ver_plano_atividade/{plano_atividade.pk}/?tab=origem_recurso'
    if not OrigemRecurso.pode_excluir(usuario=request.user, plano_atividade=plano_atividade):
        return httprr(url, 'Operação não permitida.', tag='error')

    origem_recurso.delete()

    return httprr(url, 'Origem de recurso foi excluída.')


@rtr()
@login_required()
@transaction.atomic
def planoatividade_naturezadespesa_delete(request, plano_atividade_pk, natureza_despesa_pk=None):

    plano_atividade = get_object_or_404(PlanoAtividade, pk=plano_atividade_pk)
    url = f'/plan_estrategico/ver_plano_atividade/{plano_atividade.pk}/?tab=natureza_despesa'
    natureza_despesa = get_object_or_404(NaturezaDespesaPlanoAtividade, pk=natureza_despesa_pk)

    if AtividadeEtapa.objects.filter(naturezadespesa=natureza_despesa).exists():
        return httprr(url, 'A Natureza de Despesa está vinculada à uma ou mais atividades e não pode ser removida.', tag='error')
    if not NaturezaDespesaPlanoAtividade.pode_gerenciar(usuario=request.user, plano_atividade=plano_atividade):
        return httprr(url, 'Operação não permitida.', tag='error')

    natureza_despesa.delete()

    return httprr(url, 'A Natureza de Despesa foi desvinculada.')


@rtr()
@login_required()
def plano_atividade_projeto_associar(request, plano_atividade_pk):
    plano_atividade = get_object_or_404(PlanoAtividade, pk=plano_atividade_pk)

    title = f'Projetos estratégicos - {plano_atividade.ano_base}'

    servidor = request.user
    # recupera todos os projetos do plano de atividade
    m_initial = ProjetoPlanoAtividade.objects.filter(
        plano_atividade=plano_atividade, projeto__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)
    ).values_list('projeto__pk', flat=True)

    qs = ProjetoEstrategico.objects.filter(unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user))

    qs_projetos = qs.exclude(id__in=m_initial)
    form = AssociarProjetosPlanoAtividadeForm(request.POST or None, plano=plano_atividade, servidor=servidor)
    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada.')
    return locals()


@rtr()
@login_required()
def plano_atividade_projeto_etapa_associar(request, projeto_plano_atividade_pk):
    projeto_plano_atividade = get_object_or_404(ProjetoPlanoAtividade, pk=projeto_plano_atividade_pk)

    title = f'Etapas do projeto do plano de atividade - {projeto_plano_atividade}'

    m_initial = EtapaProjetoPlanoAtividade.objects.filter(projeto_plano_atividade=projeto_plano_atividade).values_list('etapa__pk', flat=True)
    qs = EtapaProjeto.objects.filter(projeto=projeto_plano_atividade.projeto).order_by('id')

    qs_etapas = qs.exclude(id__in=m_initial)
    form = AssociarEtapasProjetoPlanoAtividadeForm(request.POST or None, projeto_plano_atividade=projeto_plano_atividade)

    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada.')

    return locals()


@transaction.atomic
@rtr()
def remover_etapaplanoatividade(request, etapa_projeto_plano_atividade_pk):
    url = request.META.get('HTTP_REFERER', '.')
    etapa = get_object_or_404(EtapaProjetoPlanoAtividade, pk=etapa_projeto_plano_atividade_pk)
    OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade_id=etapa.pk).delete()
    UnidadeGestoraEtapa.objects.filter(etapa_projeto_plano_atividade_id=etapa.pk).delete()
    if AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade=etapa).exists():
        return httprr(url, 'Já existem atividades cadastradas nesta etapa.', tag='error')
    etapa.delete()
    return httprr(url, 'Etapa removida com sucesso.')


@rtr()
@login_required()
def plano_atividade_origem_recurso_projeto_associar(request, projeto_plano_atividade_pk):
    projeto_plano_atividade = get_object_or_404(ProjetoPlanoAtividade, pk=projeto_plano_atividade_pk)

    title = f'Origens de Recurso do projeto do plano de atividade - {projeto_plano_atividade}'

    qs = OrigemRecurso.objects.filter(plano_atividade=projeto_plano_atividade.plano_atividade)
    qs_origens_recurso = qs
    form = AssociarOrigemRecursoProjetoPlanoAtividadeForm(request.POST or None, projeto_plano_atividade=projeto_plano_atividade)
    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada.')

    return locals()


@rtr()
@login_required()
def plano_atividade_origem_recurso_etapa_projeto_associar(request, projeto_plano_atividade_pk, etapa_projeto_plano_atividade_pk):
    etapa_projeto_plano_atividade = get_object_or_404(EtapaProjetoPlanoAtividade, projeto_plano_atividade=projeto_plano_atividade_pk, etapa=etapa_projeto_plano_atividade_pk)

    title = f'Origens de Recurso da etapa do projeto do plano de atividade - {etapa_projeto_plano_atividade}'

    qs_origem_etapa = OrigemRecursoProjeto.objects.filter(projeto_plano_atividade_id=etapa_projeto_plano_atividade.projeto_plano_atividade)

    form = AssociarOrigemRecursoEtapaProjetoPlanoAtividadeForm(request.POST or None, etapa_projeto_plano_atividade=etapa_projeto_plano_atividade)

    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada.')

    return locals()


@rtr()
def informar_valor_origemrecurso_projeto(request, plano_atividade_pk, origemrecursoprojeto_id):
    title = "Informar Valor Origem Recurso"
    plano_atividade = get_object_or_404(PlanoAtividade, pk=plano_atividade_pk)
    origemrecurso = get_object_or_404(OrigemRecursoProjeto, pk=origemrecursoprojeto_id)

    valor_executado = OrigemRecursoProjeto.objects.filter(projeto_plano_atividade__plano_atividade=plano_atividade, origem_recurso=origemrecurso.origem_recurso)
    if origemrecurso.valor:
        valor_executado_atual = (valor_executado.aggregate(total=Sum('valor'))['total'] or 0) - origemrecurso.valor
    else:
        valor_executado_atual = valor_executado.aggregate(total=Sum('valor'))['total'] or 0

    saldo_disponivel = origemrecurso.origem_recurso.valor_total() - valor_executado_atual

    form = OrigemRecursoProjetoForm(request.POST or None, instance=origemrecurso, request=request)
    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada.')
    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico')
def definir_etapa_especial(request, projeto_plano_atividade_pk, etapa_projeto_plano_atividade_pk):
    etapa_projeto_plano_atividade = get_object_or_404(EtapaProjetoPlanoAtividade, projeto_plano_atividade=projeto_plano_atividade_pk, etapa=etapa_projeto_plano_atividade_pk)
    title = 'Definir Etapa como Especial'
    tem_etapa_especial = EtapaProjetoPlanoAtividade.objects.filter(tipo_especial=True, projeto_plano_atividade__plano_atividade=etapa_projeto_plano_atividade.projeto_plano_atividade.plano_atividade).exists()
    if not tem_etapa_especial:
        form = OrigemRecursoEspecialForm(request.POST or None, etapa_projeto_plano_atividade=etapa_projeto_plano_atividade)
        if form.is_valid():
            form.save()
            return httprr('..', 'Operação realizada.')
        return locals()
    else:
        return httprr('..', 'Operação não permitida. Já existe uma etapa definida como especial neste plano de atividades.', tag='error')
    return httprr('..', 'Operação realizada.')


@rtr()
@group_required('Administrador de Planejamento Estratégico')
def cancelar_etapa_especial(request, etapa_projeto_plano_atividade_pk):
    etapa_projeto_plano_atividade = get_object_or_404(EtapaProjetoPlanoAtividade, etapa=etapa_projeto_plano_atividade_pk)
    origem = OrigemRecursoProjetoEtapa.objects.filter(tipo_especial=True)[0]
    if origem.tem_valor_distribuido() or origem.tem_valor_especial_distribuido():
        return httprr('..', 'Operação não permitida. Já foi realizado o rateio entre as atividades', tag='error')
    etapa_projeto_plano_atividade.tipo_especial = False
    etapa_projeto_plano_atividade.save()
    origem.tipo_especial = False
    origem.save()
    return httprr('..', 'Operação realizada.')


@rtr()
@login_required()
def plano_atividade_unidade_gestora_etapa_associar(request, projeto_plano_atividade_pk, etapa_projeto_plano_atividade_pk):
    etapa_projeto_plano_atividade = get_object_or_404(EtapaProjetoPlanoAtividade, projeto_plano_atividade=projeto_plano_atividade_pk, etapa=etapa_projeto_plano_atividade_pk)

    title = f'Associar Unidades Administrativas a etapa: {etapa_projeto_plano_atividade.etapa}'

    form = AssociarUnidadeGestoraEtapaProjetoPlanoAtividadeForm(request.POST or None, etapa_projeto_plano_atividade=etapa_projeto_plano_atividade)
    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada.')

    return locals()


@rtr()
@permission_required('plan_estrategico.add_atividadeetapa')
def atividade_etapa_add_change(request, etapa_projeto_plano_atividade_pk, atividade_pk=None):
    etapa_projeto_plano_atividade = get_object_or_404(EtapaProjetoPlanoAtividade, pk=etapa_projeto_plano_atividade_pk)

    atividade = None

    title = '{} Atividade da etapa'.format(atividade_pk and 'Editar' or 'Adicionar')

    if atividade_pk:
        atividade = get_object_or_404(AtividadeEtapa, pk=atividade_pk)
        if not atividade.eh_dono():
            return httprr('..', 'Não tem permissão para editar a atividade', tag='error')

    form = AtividadeEtapaForm(request.POST or None, instance=atividade, etapa=etapa_projeto_plano_atividade, request=request)

    if form.is_valid():
        form.save()
        return httprr('..', 'Atividade salva.')

    return locals()


@transaction.atomic
@rtr()
@permission_required('plan_estrategico.delete_atividadeetapa')
def remover_atividade(request, atividade_pk):
    url = request.META.get('HTTP_REFERER', '.')
    atividade = get_object_or_404(AtividadeEtapa, pk=atividade_pk)
    if not atividade.pode_excluir_atividade(usuario=request.user, plano_atividade=atividade.etapa_projeto_plano_atividade.projeto_plano_atividade.plano_atividade):
        raise PermissionDenied()
    atividade.delete()
    return httprr(url, 'Atividade removida com sucesso.')


@rtr()
@login_required()
def gerenciar_compartilhamento_poder_de_gestor_ua(request):
    title = 'Gerenciamento de Permissões de Plano de Atividades'

    su, setor_escolhido, setor_escolhido, msg_orientacao_acesso = iniciar_gerenciamento_acesso(request)

    form = GerenciarCompartilhamentoGEstorUAForm(request.POST or None, setor_escolhido=setor_escolhido)

    form.fields['pessoas_com_poder_de_chefe'].initial = CompartilhamentoPoderdeGestorUA.objects.filter(setor_dono=setor_escolhido).values_list('pessoa_permitida', flat=True)

    if form.is_valid():

        pessoas_poder_de_gestor = form.cleaned_data.get('pessoas_com_poder_de_chefe', None)

        CompartilhamentoPoderdeGestorUA.atualizar_poder_gestor(request.user, setor_escolhido, pessoas_poder_de_gestor)

        messages.success(request, 'Operação realizada com sucesso.')

    return locals()


@rtr()
@login_required()
def adicionar_valores_origem_etapas(request, origemrecurso_id):
    tem_rateio_unidades = None
    origemrecurso = get_object_or_404(OrigemRecursoProjeto, pk=origemrecurso_id)
    etapas = OrigemRecursoProjetoEtapa.objects.filter(origem_recurso_projeto=origemrecurso)
    for etapa in etapas:
        if etapa.etapa_projeto_plano_atividade.tem_valor_rateado_unidades():
            tem_rateio_unidades = True
    title = 'Ratear Valor por Etapa'

    form = ValoresOrigemRecursoEtapaForm(request.POST or None, origemrecurso=origemrecurso)
    if form.is_valid():
        for item, valor in form.cleaned_data.items():
            try:
                origem_etapa = get_object_or_404(OrigemRecursoProjetoEtapa, pk=item)
                origem_etapa.valor = valor
                origem_etapa.save()
            except ValueError:
                pass

        return httprr('..', 'Rateio da Origem de Recurso realizado com sucesso.')
    return locals()


@rtr()
@login_required()
def ver_rateio_atividades(request, plano_atividade_pk, etapa_id):
    eh_administrador = ProjetoPlanoAtividade.eh_administrador(usuario=request.user)
    plano_atividade = get_object_or_404(PlanoAtividade, pk=plano_atividade_pk)
    origem_recurso_pode_ratear_valor = OrigemRecursoProjeto.pode_ratear_valor(plano_atividade=plano_atividade)
    etapa = get_object_or_404(EtapaProjetoPlanoAtividade, pk=etapa_id)
    origens = OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade=etapa.id)
    unidades = UnidadeGestoraEtapa.objects.filter(etapa_projeto_plano_atividade=etapa.id).order_by('unidade_gestora__setor_equivalente')
    tem_valor_compatibilizado = False
    for origem in origens:
        if origem.tem_valor_distribuido() or origem.tem_valor_especial_distribuido():
            tem_valor_compatibilizado = True

    return locals()


@rtr()
@login_required()
def detalhar_atividades_unidade(request, etapa_pk, origemrecurso_pk, unidade_pk):
    etapa_projeto_plano_atividade = get_object_or_404(EtapaProjetoPlanoAtividade, pk=etapa_pk)
    unidade = get_object_or_404(UnidadeGestora, pk=unidade_pk)
    origemrecurso = get_object_or_404(OrigemRecursoProjetoEtapa, pk=origemrecurso_pk)
    atividades_etapa = AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade=etapa_projeto_plano_atividade, origem_recurso_etapa=origemrecurso, unidade_gestora=unidade).order_by('nome')
    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico, Gestor de Projeto, Gestor de UA, Coordenador de UA')
def ratear_valores_atividades(request, etapa_id, origemrecurso_id):
    etapa = get_object_or_404(EtapaProjetoPlanoAtividade, pk=etapa_id)
    origemrecurso = get_object_or_404(OrigemRecursoProjetoEtapa, pk=origemrecurso_id)
    title = 'Ratear Valor por Atividades'
    percentual_reserva_tecnica = etapa.projeto_plano_atividade.plano_atividade.percentual_reserva_tecnica
    tem_atividades = AtividadeEtapa.objects.filter(
        etapa_projeto_plano_atividade=etapa, origem_recurso_etapa=origemrecurso, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)
    )
    saldo_disponivel = 0
    if UnidadeOrigemEtapa.objects.filter(
        origem_recurso_etapa=origemrecurso, unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)
    ).exists():
        saldo_disponivel = (
            UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa=origemrecurso, unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user))[
                0
            ].valor
            or 0
        )
    saldo_especial = None
    or_especial = None
    valor_especial_unidade = 0
    if OrigemRecursoProjetoEtapa.objects.filter(
        etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=etapa.projeto_plano_atividade.plano_atividade, tipo_especial=True
    ).exists():
        or_especial = OrigemRecursoProjetoEtapa.objects.filter(
            etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=etapa.projeto_plano_atividade.plano_atividade, tipo_especial=True
        )[0]
        if UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa=or_especial, unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)):
            valor_especial_unidade = (
                UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa__etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=etapa.projeto_plano_atividade.plano_atividade,
                                                  origem_recurso_etapa=or_especial, unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)
                                                  )[0].valor
                or 0
            )
    atividades = AtividadeEtapa.objects.filter(origem_recurso_etapa=or_especial, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user))
    valor_rateado_ativ = atividades.aggregate(total=Sum('valor_rateio'))['total'] or 0
    atividades_reserva = AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=etapa.projeto_plano_atividade.plano_atividade, valor_reserva_tecnica__isnull=False, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user))
    total_atividades_reserva = atividades_reserva.aggregate(total=Sum('valor_reserva_tecnica'))['total'] or 0
    if OrigemRecursoProjetoEtapa.objects.filter(
        etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=etapa.projeto_plano_atividade.plano_atividade, tipo_especial=True
    ).exists():
        if (
            etapa.eh_especial()
            and origemrecurso.tipo_especial is False
            and or_especial.origem_recurso_projeto.origem_recurso.gnd == origemrecurso.origem_recurso_projeto.origem_recurso.gnd
        ) or (etapa.eh_especial() is False and or_especial.origem_recurso_projeto.origem_recurso.gnd == origemrecurso.origem_recurso_projeto.origem_recurso.gnd):
            percentual_reserva_tecnica = etapa.projeto_plano_atividade.plano_atividade.percentual_reserva_tecnica
            saldo_especial = valor_especial_unidade - (valor_rateado_ativ + total_atividades_reserva)

    if origemrecurso.valor:
        valor_executado = AtividadeEtapa.objects.filter(
            etapa_projeto_plano_atividade=etapa, origem_recurso_etapa=origemrecurso, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)
        )

        if origemrecurso.tipo_especial:
            unidade = UnidadeGestora.objects.filter(setor_equivalente=get_setor_unidade_gestora(user=request.user))[0]
            if unidade.recurso_total:
                valor_percentual_unidade = saldo_disponivel
            else:
                valor_percentual_unidade = (saldo_disponivel * percentual_reserva_tecnica) / 100
            saldo_origem_especial = valor_especial_unidade - total_atividades_reserva
            if saldo_origem_especial > valor_percentual_unidade:
                saldo_origem_especial = valor_percentual_unidade
            else:
                saldo_origem_especial = saldo_origem_especial
        saldo_disponivel = saldo_disponivel - (valor_executado.aggregate(total=Sum('valor_rateio'))['total'] or 0)
    form = ValoresEtapaAtividadesForm(request.POST or None, origemrecurso=origemrecurso, etapa=etapa)
    if form.is_valid():
        for atividade in AtividadeEtapa.objects.filter(
            etapa_projeto_plano_atividade=etapa, origem_recurso_etapa=origemrecurso, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)
        ):
            atividade.valor_rateio = form.cleaned_data[f"{atividade.id}"]
            atividade.valor_reserva_tecnica = form.cleaned_data[f"reserva_tecnica_{atividade.id}"]
            atividade.origem_recurso_reserva_tecnica = or_especial
            atividade.save()
        return httprr('..', 'Rateio das atividades realizado com sucesso.')
    return locals()


@rtr()
@login_required()
def ratear_valores_unidades(request, etapa_id, origemrecurso_id):
    etapa = get_object_or_404(EtapaProjetoPlanoAtividade, pk=etapa_id)
    origemrecurso = get_object_or_404(OrigemRecursoProjetoEtapa, pk=origemrecurso_id)
    title = 'Ratear Valor por Unidades'

    saldo_disponivel = origemrecurso.valor or 0
    if origemrecurso.valor:
        valor_executado = UnidadeOrigemEtapa.objects.filter(
            origem_recurso_etapa__etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=etapa.projeto_plano_atividade.plano_atividade,
            origem_recurso_etapa=origemrecurso,
        )
        saldo_disponivel = origemrecurso.valor - (valor_executado.aggregate(total=Sum('valor'))['total'] or 0)

    form = ValoresEtapaUnidadesForm(request.POST or None, origemrecurso=origemrecurso, etapa=etapa)
    if form.is_valid():
        for item, valor in form.cleaned_data.items():
            try:
                unidade_gestora = get_object_or_404(UnidadeGestoraEtapa, pk=item)
                unidade_origem, criado = UnidadeOrigemEtapa.objects.get_or_create(unidade_gestora=unidade_gestora, origem_recurso_etapa=origemrecurso)
                unidade_origem.valor = valor
                unidade_origem.save()
            except ValueError:
                pass
        return httprr('..', 'Rateio das Unidades Administrativas realizado com sucesso.')
    return locals()


@rtr()
@login_required()
def relatorio_indicadores_pdi(request, pdi_pk=None, indicador_pk=None, uo=None):
    if pdi_pk:
        pdi = get_object_or_404(PDI, pk=pdi_pk)
    else:
        pdi = PDI.objects.latest('id')
    pdi_indicadores = PDIIndicador.objects.filter(pdi__id=pdi.pk)
    meta_geral = None
    valor_geral = None
    trimestre_atual = int((date.today().month - 1) / 3 + 1)
    title = f'Indicadores do PDI - {pdi.ano_inicial_pdi} a {pdi.ano_final_pdi}'
    escolheu_ano = False
    lista_indicadores = []
    ano_base = datetime.today().year
    uos = UnidadeOrganizacional.objects.uo().all()
    sigla_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')

    FormKlass = filtro_indicadores_formfactory(pdi, sigla_instituicao)
    filter_form = FormKlass(request.GET or None, pdi=pdi)

    if filter_form.is_valid():
        if filter_form.cleaned_data.get('ano') and filter_form.cleaned_data.get('ano') != 'Selecione um ano':
            ano_base = int(filter_form.cleaned_data['ano'])
            escolheu_ano = True
        uo = filter_form.cleaned_data.get('campus', uo)
        indicador = filter_form.cleaned_data.get('indicador', pdi_indicadores)
        if uo:
            uos = UnidadeOrganizacional.objects.filter(pk=uo.id)
        if indicador:
            pdi_indicadores = PDIIndicador.objects.filter(pk=indicador.id)
        if escolheu_ano:
            for pdi_indicador in pdi_indicadores.order_by('indicador__sigla'):
                for unidade in uos:
                    info_indicadores = dict()
                    try:
                        valor_meta = pdi_indicador.indicador.get_formula_valor_meta(unidade, ano_base)
                    except Exception:
                        valor_meta = 0
                    try:
                        valor_real = pdi_indicador.indicador.get_formula_valor(unidade, ano_base)
                    except Exception:
                        valor_real = None
                    valor_trimestral = 0
                    if ano_base == date.today().year and valor_meta:
                        if trimestre_atual == 1:
                            valor_trimestral = valor_meta / 4
                        else:
                            valor_trimestral = (valor_meta / 4.0) * (trimestre_atual - 1)
                    else:
                        valor_trimestral = valor_meta
                    info_indicadores['sigla'] = pdi_indicador.indicador.sigla
                    info_indicadores['indicador'] = pdi_indicador
                    info_indicadores['uo'] = unidade
                    info_indicadores['valor_meta'] = valor_meta
                    info_indicadores['valor_trimestral'] = valor_trimestral
                    info_indicadores['valor_real'] = valor_real
                    lista_indicadores.append(info_indicadores)
                if uo is None:
                    meta_geral = 0
                    if not pdi_indicador.verificar_variavel_ideal_vazia(uo, ano_base):
                        meta_geral = pdi_indicador.indicador.get_formula_valor_meta(uo, ano_base)
                    valor_real_geral = None
                    if not pdi_indicador.verificar_variavel_real_vazia(uo, ano_base):
                        valor_real_geral = pdi_indicador.indicador.get_formula_valor(uo, ano_base)
                    if ano_base == date.today().year:
                        if trimestre_atual == 1:
                            valor_trimestral = meta_geral / 4
                        else:
                            valor_trimestral = (meta_geral / 4.0) * (trimestre_atual - 1)
                    else:
                        valor_trimestral = meta_geral
                    lista_indicadores.append({'indicador': pdi_indicador, 'uo': 'IFRN', 'valor_meta': meta_geral, 'valor_trimestral': valor_trimestral, 'valor_real': valor_real_geral})

    if 'xls' in request.POST and escolheu_ano:
        return tasks.indicadores_pdi_export_to_xls(lista_indicadores)
    return locals()


@rtr()
@login_required()
def relatorio_linhadotempo(request, pdi_pk=None, indicador_pk=None, uo=None):
    if pdi_pk:
        pdi = get_object_or_404(PDI, pk=pdi_pk)
    else:
        pdi = PDI.objects.latest('id')
    pdi_indicadores = PDIIndicador.objects.filter(pdi__id=pdi.pk)
    title = 'Relatório Linha do Tempo do PDI - {} a {}'.format(pdi.ano_inicial_pdi, pdi.ano_final_pdi)
    ano_base = datetime.today().year
    lista_inds = []
    uos = UnidadeOrganizacional.objects.uo().all()
    sigla_instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')

    FormKlass = filtro_linhadotempo_formfactory(pdi, sigla_instituicao)
    filter_form = FormKlass(request.GET or None, pdi=pdi)

    if filter_form.is_valid():
        uo = filter_form.cleaned_data.get('campus', uo)
        indicador = filter_form.cleaned_data.get('indicador', pdi_indicadores)
        if uo:
            uos = UnidadeOrganizacional.objects.filter(pk=uo.id)
        if indicador:
            pdi_indicador = PDIIndicador.objects.filter(pk=indicador.id).first()
            series = []
            for ano in IndicadorTrimestralCampus.objects.filter(indicador=pdi_indicador, trimestre=4, uo=uo).values_list('ano', flat=True).order_by('ano'):
                ind = IndicadorTrimestralCampus.objects.filter(indicador=pdi_indicador, trimestre=4, uo=uo, ano=ano)[0]
                meta_anual = round(pdi_indicador.indicador.get_formula_valor_meta(uo, ano), 1)
                series.append([ano, float(meta_anual or 0), float(ind.valor or 0)])
                info_indicadores = dict()
                info_indicadores['indicador'] = indicador
                info_indicadores['uo'] = uo
                if uo is None:
                    info_indicadores['uo'] = sigla_instituicao
                info_indicadores['ano'] = ano
                info_indicadores['meta_anual'] = meta_anual
                info_indicadores['valor_alcancado'] = ind.valor
                lista_inds.append(info_indicadores)
            grafico_linha_tempo = LineChart(
                'grafico_linha_tempo',
                title='Linha do Tempo Indicador',
                subtitle='{}'.format(pdi_indicador),
                data=series,
                groups=['Meta Anual', 'Valor Alcançado'],
                plotOptions_line_dataLabels_enable=True,
                plotOptions_line_enableMouseTracking=True,
            )
    if 'xls' in request.POST:
        return tasks.linhadotempo_export_to_xls(lista_inds)
    return locals()


@transaction.atomic
@rtr()
@permission_required('plan_estrategico.delete_projetoestrategico')
def remover_rateio_atividades(request, etapa_pk, origemrecurso_pk):
    url = request.META.get('HTTP_REFERER', '.')
    etapa_projeto_plano_atividade = get_object_or_404(EtapaProjetoPlanoAtividade, pk=etapa_pk)
    origemrecurso = get_object_or_404(OrigemRecursoProjetoEtapa, pk=origemrecurso_pk)

    atividades_etapa = AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade=etapa_projeto_plano_atividade, origem_recurso_etapa=origemrecurso)
    for ativ in atividades_etapa:
        ativ.valor_rateio = None
        ativ.valor_reserva_tecnica = None
        ativ.save()
    return httprr(url, 'Rateio das Atividades cancelado.')


@transaction.atomic
@rtr()
@permission_required('plan_estrategico.delete_projetoestrategico')
def remover_rateio_unidades(request, etapa_pk):
    url = request.META.get('HTTP_REFERER', '.')
    etapa_projeto_plano_atividade = get_object_or_404(EtapaProjetoPlanoAtividade, pk=etapa_pk)
    origens_recurso = OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade=etapa_projeto_plano_atividade).exists()
    if origens_recurso:
        for origem in OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade=etapa_projeto_plano_atividade):
            unidades = UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa=origem).exists()
            if unidades:
                for unidade in UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa=origem):
                    unidade.valor = None
                    unidade.save()
    return httprr(url, 'Rateio das Unidades das Origens de recurso cancelado.')


@rtr()
@login_required()
def ver_rateio_reserva_tecnica(request, etapa_id):
    etapa = get_object_or_404(EtapaProjetoPlanoAtividade, pk=etapa_id)
    title = 'Demonstrativo da Origem de Recurso'
    unidade = get_setor_unidade_gestora(user=request.user)
    valor_reserva_tecnica_unidade = 0
    total_atividades_projeto_especial = 0
    if OrigemRecursoProjetoEtapa.objects.filter(
        etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=etapa.projeto_plano_atividade.plano_atividade, tipo_especial=True
    ).exists():
        or_especial = OrigemRecursoProjetoEtapa.objects.filter(
            etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=etapa.projeto_plano_atividade.plano_atividade, tipo_especial=True
        )[0]
        if UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa=or_especial, unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)):
            valor_reserva_tecnica_unidade = (
                UnidadeOrigemEtapa.objects.filter(
                    origem_recurso_etapa=or_especial, unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)
                )[0].valor
                or 0
            )

        atividades_projeto_especial = AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=etapa.projeto_plano_atividade.plano_atividade,
                                                                    valor_rateio__gt=0, origem_recurso_etapa=or_especial, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)
                                                                    )
        total_atividades_projeto_especial = atividades_projeto_especial.aggregate(total=Sum('valor_rateio'))['total'] or 0
    atividades_reserva = AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=etapa.projeto_plano_atividade.plano_atividade, valor_reserva_tecnica__gt=0, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user))
    total_atividades_reserva = atividades_reserva.aggregate(total=Sum('valor_reserva_tecnica'))['total'] or 0
    total_atividades_reserva = total_atividades_reserva + total_atividades_projeto_especial
    saldo_reserva_tecnica = valor_reserva_tecnica_unidade - total_atividades_reserva

    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico, Gestor de Projeto, Gestor de UA, Coordenador de UA, Auditor')
def ver_extrato_reserva_tecnica(request, plano_atividade_pk):
    plano_atividade = get_object_or_404(PlanoAtividade, pk=plano_atividade_pk)
    title = 'Demonstrativo da Origem de Recurso por Projetos'
    eh_administrador = ProjetoPlanoAtividade.eh_administrador(usuario=request.user)
    eh_auditor = request.user.has_perm('rh.auditor')
    valor_reserva_tecnica_unidade = 0
    total_atividades_projeto_especial = 0
    lista_projetos = []
    unidade = None

    if eh_administrador or eh_auditor:
        unidade_form = RelatorioDemonstrativoForm(request.POST)
        try:
            unidade = UnidadeGestora.objects.get(pk=int(request.POST['unidade_gestora']))
        except Exception:
            mensagem = 'Selecione um Campus para gerar o relatório.'
    else:
        unidade_gestora = get_setor_unidade_gestora(user=request.user)
        if unidade_gestora:
            unidade = UnidadeGestora.objects.get(setor_equivalente=unidade_gestora)
    if unidade:
        if OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=plano_atividade, tipo_especial=True).exists():
            or_especial = OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=plano_atividade, tipo_especial=True)[0]
            if UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa=or_especial, unidade_gestora__unidade_gestora=unidade).exists():
                valor_reserva_tecnica_unidade = UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa=or_especial, unidade_gestora__unidade_gestora=unidade)[0].valor or 0

            atividades_projeto_especial = AtividadeEtapa.objects.filter(valor_rateio__gt=0, origem_recurso_etapa=or_especial, unidade_gestora=unidade, etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=plano_atividade)
            total_atividades_projeto_especial = atividades_projeto_especial.aggregate(total=Sum('valor_rateio'))['total'] or 0

            if total_atividades_projeto_especial > 0:
                projeto_estrategico = dict()
                projeto_estrategico['codigo'] = or_especial.origem_recurso_projeto.projeto_plano_atividade.projeto.codigo
                projeto_estrategico['valor'] = total_atividades_projeto_especial
                lista_projetos.append(projeto_estrategico)
        atividades_reserva = AtividadeEtapa.objects.filter(valor_reserva_tecnica__gt=0, unidade_gestora=unidade, etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=plano_atividade)

        for projeto in plano_atividade.projetos.all().order_by('codigo'):
            atividades = AtividadeEtapa.objects.filter(
                valor_reserva_tecnica__gt=0, etapa_projeto_plano_atividade__projeto_plano_atividade__projeto__codigo=projeto.codigo, unidade_gestora=unidade,
                etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=plano_atividade
            )

            valor_projeto = atividades.aggregate(total=Sum('valor_reserva_tecnica'))['total'] or 0
            if valor_projeto > 0:
                projeto_estrategico = dict()
                projeto_estrategico['codigo'] = projeto.codigo
                projeto_estrategico['valor'] = valor_projeto
                lista_projetos.append(projeto_estrategico)

        total_atividades_reserva = atividades_reserva.aggregate(total=Sum('valor_reserva_tecnica'))['total'] or 0
        total_atividades_reserva = total_atividades_reserva + total_atividades_projeto_especial
        saldo_reserva_tecnica = valor_reserva_tecnica_unidade - total_atividades_reserva

    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico, Gestor de Projeto, Gestor de UA, Coordenador de UA, Auditor')
def ver_extrato_unidade(request, plano_atividade_pk):
    plano_atividade = get_object_or_404(PlanoAtividade, pk=plano_atividade_pk)
    title = 'Demonstrativo por Unidades'
    eh_administrador = ProjetoPlanoAtividade.eh_administrador(usuario=request.user)
    valor_reserva_tecnica_unidade = 0
    total_atividades_projeto_especial = 0
    campi = []

    for unidade in UnidadeGestora.objects.all().order_by('tipo', 'setor_equivalente__sigla'):
        unidade.lista_projetos = []
        unidade.somatorios = []
        total_unidade = 0
        for projeto in plano_atividade.projetos.all().order_by('codigo'):
            atividades = AtividadeEtapa.objects.filter(
                valor_rateio__gt=0, etapa_projeto_plano_atividade__projeto_plano_atividade__projeto__codigo=projeto.codigo, unidade_gestora=unidade,
                etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=plano_atividade
            )
            atividades_com_reserva_tecnica = AtividadeEtapa.objects.filter(
                valor_reserva_tecnica__gt=0,
                etapa_projeto_plano_atividade__projeto_plano_atividade__projeto__codigo=projeto.codigo,
                unidade_gestora=unidade, etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=plano_atividade
            )
            valor_projeto = atividades.aggregate(total=Sum('valor_rateio'))['total'] or 0
            valor_reserva_projeto = atividades_com_reserva_tecnica.aggregate(total=Sum('valor_reserva_tecnica'))['total'] or 0
            if valor_projeto > 0 or valor_reserva_projeto > 0:
                projeto_estrategico = dict()
                projeto_estrategico['codigo'] = projeto.codigo
                projeto_estrategico['valor'] = valor_projeto
                projeto_estrategico['valor_reserva_tecnica'] = valor_reserva_projeto
                projeto_estrategico['total'] = valor_projeto + valor_reserva_projeto
                unidade.lista_projetos.append(projeto_estrategico)
                total_unidade += projeto_estrategico['total']
        unidade.somatorios.append(total_unidade)
        campi.append(unidade)

    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico, Gestor de Projeto, Gestor de UA, Coordenador de UA, Auditor')
def ver_extrato_projeto(request, projeto_pk):
    projeto = get_object_or_404(ProjetoPlanoAtividade, pk=projeto_pk)
    title = 'Demonstrativo por Projeto'
    eh_administrador = ProjetoPlanoAtividade.eh_administrador(usuario=request.user)
    total_valor_proposto = 0
    total_valor_rateio = 0
    total_valor_reserva = 0
    total_atividades = 0
    lista_etapas = []
    unidade = None
    origem_recurso = None
    projeto_form = RelatorioProjetoForm(request.POST or None, projeto=projeto)
    for etapaprojeto in EtapaProjetoPlanoAtividade.objects.filter(projeto_plano_atividade=projeto).order_by('etapa__codigo'):
        atividades = AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade=etapaprojeto).order_by('unidade_gestora__setor_equivalente', 'origem_recurso_etapa__origem_recurso_projeto__origem_recurso', 'origem_recurso_etapa__origem_recurso_projeto__origem_recurso__gnd__codigo')
        if projeto_form.is_valid():
            unidade = projeto_form.cleaned_data['unidade_gestora']
            origem_recurso = projeto_form.cleaned_data['origem_recurso_etapa']
            if unidade:
                atividades = atividades.filter(unidade_gestora=unidade)
            if origem_recurso:
                atividades = atividades.filter(origem_recurso_etapa__origem_recurso_projeto=origem_recurso.origem_recurso_projeto)
        total_valor_proposto = atividades.aggregate(total=Sum('valor'))['total'] or 0
        total_valor_rateio = atividades.aggregate(total=Sum('valor_rateio'))['total'] or 0
        total_valor_reserva = atividades.aggregate(total=Sum('valor_reserva_tecnica'))['total'] or 0
        descricao = dict()
        descricao['etapa'] = etapaprojeto.etapa.descricao
        descricao['total_valor_proposto'] = total_valor_proposto
        descricao['total_valor_rateio'] = total_valor_rateio
        descricao['total_valor_reserva'] = total_valor_reserva
        descricao['total_atividades'] = total_valor_rateio + total_valor_reserva
        descricao['codigo'] = etapaprojeto.etapa.codigo
        descricao['atividades'] = atividades
        lista_etapas.append(descricao)

    return locals()


@rtr()
@login_required()
def ver_resumo_plano(request, plano_atividade_pk):
    plano_atividade = get_object_or_404(PlanoAtividade, pk=plano_atividade_pk)
    title = 'Resumo do Plano de Atividades'
    eh_administrador = ProjetoPlanoAtividade.eh_administrador(usuario=request.user)
    total_valor_proposto = 0
    total_valor_rateio = 0
    total_valor_reserva = 0
    total_atividades = 0
    lista_projetos = []
    unidade = None
    projeto_plano = None
    origem_recurso = None
    projeto = request.GET.get('projeto')
    resumoplano_form = RelatorioPlanoatividadeForm(request.POST or None, plano_atividade=plano_atividade, request=request)
    projetos = ProjetoPlanoAtividade.objects.filter(plano_atividade=plano_atividade).order_by('projeto__codigo')
    if resumoplano_form.is_valid():
        projeto_plano = resumoplano_form.cleaned_data['projeto']
        etapa = resumoplano_form.cleaned_data['etapa']
        if projeto_plano:
            projetos = ProjetoPlanoAtividade.objects.filter(plano_atividade=plano_atividade, projeto=projeto_plano.projeto).order_by('projeto__codigo')
        if etapa and not projeto_plano:
            projetos = ProjetoPlanoAtividade.objects.filter(plano_atividade=plano_atividade, projeto=etapa.projeto_plano_atividade.projeto).order_by('projeto__codigo')
        for projeto_plano in projetos:
            atividades = AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade__projeto_plano_atividade=projeto_plano)
            unidade = resumoplano_form.cleaned_data['unidade_gestora']
            origem_recurso = resumoplano_form.cleaned_data['origem_recurso']

            if unidade:
                atividades = atividades.filter(unidade_gestora=unidade)
            if origem_recurso:
                atividades = atividades.filter(origem_recurso_etapa__origem_recurso_projeto__origem_recurso=origem_recurso)
            if etapa:
                atividades = atividades.filter(etapa_projeto_plano_atividade=etapa)
            total_valor_proposto = atividades.aggregate(total=Sum('valor'))['total'] or 0
            total_valor_rateio = atividades.aggregate(total=Sum('valor_rateio'))['total'] or 0
            total_valor_reserva = atividades.aggregate(total=Sum('valor_reserva_tecnica'))['total'] or 0
            descricao = dict()
            descricao['projeto_plano'] = projeto_plano
            descricao['total_valor_proposto'] = total_valor_proposto
            descricao['total_valor_rateio'] = total_valor_rateio
            descricao['total_valor_reserva'] = total_valor_reserva
            descricao['total_atividades'] = total_valor_rateio + total_valor_reserva

            descricao['atividades'] = atividades.order_by('unidade_gestora__setor_equivalente', 'etapa_projeto_plano_atividade__etapa__codigo', 'origem_recurso_etapa__origem_recurso_projeto__origem_recurso', 'origem_recurso_etapa__origem_recurso_projeto__origem_recurso__gnd__codigo')
            lista_projetos.append(descricao)
    else:
        for projeto_plano in projetos:
            atividades = AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade__projeto_plano_atividade=projeto_plano, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=request.user)).order_by('unidade_gestora__setor_equivalente')
            total_valor_proposto = atividades.aggregate(total=Sum('valor'))['total'] or 0
            total_valor_rateio = atividades.aggregate(total=Sum('valor_rateio'))['total'] or 0
            total_valor_reserva = atividades.aggregate(total=Sum('valor_reserva_tecnica'))['total'] or 0
            descricao = dict()
            descricao['projeto_plano'] = projeto_plano
            descricao['total_valor_proposto'] = total_valor_proposto
            descricao['total_valor_rateio'] = total_valor_rateio
            descricao['total_valor_reserva'] = total_valor_reserva
            descricao['total_atividades'] = total_valor_rateio + total_valor_reserva

            descricao['atividades'] = atividades.order_by('unidade_gestora__setor_equivalente', 'etapa_projeto_plano_atividade__etapa__codigo', 'origem_recurso_etapa__origem_recurso_projeto__origem_recurso', 'origem_recurso_etapa__origem_recurso_projeto__origem_recurso__gnd__codigo')
            lista_projetos.append(descricao)
    return locals()


@rtr()
@group_required('Administrador de Planejamento Estratégico, Gestor Estratégico Local, Gestor Estratégico Sistêmico, Auditor')
def relatorio_ranking(request):
    title = 'Relatório Ranking de Preenchimento de Variáveis'
    lista_campi = []
    if PeriodoPreenchimentoVariavel.objects.exists():
        form = RelatorioRankingForm(request.POST or None, request=request)
        uos = UnidadeOrganizacional.objects.uo().all()
        periodo = PeriodoPreenchimentoVariavel.objects.filter(data_inicio__date__lte=date.today()).order_by('-id')[0]
        ano = periodo.ano
        tematicas = TematicaVariavel.objects.all()
        lista_tematica = []
        for uo in uos:
            total_variaveis_preenchidas = VariavelCampus.objects.filter(uo=uo, ano=ano.ano, variavel__fonte='Manual',
                                                                        data_atualizacao__date__gte=periodo.data_inicio, situacao=VariavelCampus.ATIVA).count()
            total_variaveis = VariavelCampus.objects.filter(uo=uo, ano=ano.ano, variavel__fonte='Manual', situacao=VariavelCampus.ATIVA).count() or 0
            percentual_preenchido = None
            if total_variaveis > 0:
                percentual_preenchido = round(total_variaveis_preenchidas * 100.0 / total_variaveis)
            infos = dict()
            infos['uo'] = uo
            infos['percentual_preenchido'] = percentual_preenchido
            infos['total_variaveis_preenchidas'] = total_variaveis_preenchidas
            infos['total_variaveis'] = total_variaveis
            lista_campi.append(infos)
        if form.is_valid():
            uo = form.cleaned_data['campus']
            tematica = form.cleaned_data['tematica']
            if tematica:
                total_variaveis_preenchidas = VariavelCampus.objects.filter(variavel__tematica=tematica, ano=ano.ano,
                                                                            variavel__fonte='Manual',
                                                                            data_atualizacao__date__gte=periodo.data_inicio, situacao=VariavelCampus.ATIVA)
                total_variaveis = VariavelCampus.objects.filter(variavel__tematica=tematica, ano=ano.ano,
                                                                variavel__fonte='Manual', situacao=VariavelCampus.ATIVA)

                if uo:
                    lista_campi = []
                    total_variaveis_preenchidas = total_variaveis_preenchidas.filter(uo=uo).count()
                    total_variaveis = total_variaveis.filter(uo=uo).count() or 0
                    percentual_preenchido = None
                    if total_variaveis > 0:
                        percentual_preenchido = round(total_variaveis_preenchidas * 100.0 / total_variaveis)
                    infos = dict()
                    infos['uo'] = uo
                    infos['percentual_preenchido'] = percentual_preenchido
                    infos['total_variaveis_preenchidas'] = total_variaveis_preenchidas
                    infos['total_variaveis'] = total_variaveis
                    lista_campi.append(infos)
                else:
                    lista_campi = []
                    for uo in uos:
                        total_variaveis_preenchidas_uo = total_variaveis_preenchidas.filter(uo=uo).count()
                        total_variaveis_uo = total_variaveis.filter(uo=uo).count() or 0
                        percentual_preenchido = None
                        if total_variaveis_uo > 0:
                            percentual_preenchido = round(total_variaveis_preenchidas_uo * 100.0 / total_variaveis_uo)
                        infos = dict()
                        infos['uo'] = uo
                        infos['percentual_preenchido'] = percentual_preenchido
                        infos['total_variaveis_preenchidas'] = total_variaveis_preenchidas_uo
                        infos['total_variaveis'] = total_variaveis_uo
                        lista_campi.append(infos)
            elif uo:
                lista_campi = []
                for tematica in tematicas:
                    total_variaveis_preenchidas = VariavelCampus.objects.filter(variavel__tematica=tematica, uo=uo, ano=ano.ano, variavel__fonte='Manual', data_atualizacao__date__gte=periodo.data_inicio, situacao=VariavelCampus.ATIVA).count()
                    total_variaveis = VariavelCampus.objects.filter(variavel__tematica=tematica, uo=uo, ano=ano.ano, variavel__fonte='Manual', situacao=VariavelCampus.ATIVA).count() or 0
                    percentual_preenchido = None
                    if total_variaveis > 0:
                        percentual_preenchido = round(total_variaveis_preenchidas * 100.0 / total_variaveis)
                    infos = dict()
                    infos['tematica'] = tematica
                    infos['percentual_preenchido'] = percentual_preenchido
                    infos['total_variaveis_preenchidas'] = total_variaveis_preenchidas
                    infos['total_variaveis'] = total_variaveis
                    lista_tematica.append(infos)
            else:
                lista_campi.append(infos)
    return locals()
