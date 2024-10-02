import io
import json
import os
from collections import OrderedDict
from datetime import date, datetime
from decimal import Decimal

from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required, permission_required
from django.core.exceptions import MultipleObjectsReturned, ObjectDoesNotExist, PermissionDenied
from django.core.files.storage import default_storage
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Case, Count, F, IntegerField, Q, Value, When
from django.db.models.aggregates import Sum
from django.dispatch import Signal
from django.forms.widgets import Select
from django.http import HttpResponse, HttpResponseNotAllowed, Http404
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django_tables2.columns.base import Column
from django_tables2.columns.datecolumn import DateColumn
from django_tables2.columns.linkcolumn import LinkColumn
from django_tables2.utils import Accessor

from comum.models import (
    Configuracao,
    ConfiguracaoImpressaoDocumento,
    DocumentoControle,
    DocumentoControleTipo,
    Log,
    PessoaEndereco,
    TipoCarteiraFuncional,
    PrestadorServico,
)
from comum.utils import get_qtd_dias_por_ano, get_table, get_uo, get_uo_siape, retira_acentos, get_sigla_reitoria
from djtools import layout, tasks
from djtools.choices import Meses, campos, campos_nao_agrupaveis
from djtools.html.graficos import ColumnChart, GroupedColumnChart, PieChart
from djtools.lps import lps
from djtools.storages import is_remote_storage, LocalUploadBackend, AWSUploadBackend
from djtools.templatetags.filters import in_group
from djtools.utils import JsonResponse, documento, group_required, httprr, mask_cpf, mask_numbers, render, rtr, send_notification, is_ajax
from rh.forms import (
    AdicionarHorarioAcaoSaudeForm,
    AdicionarHorarioAfastamentoForm,
    AfastamentosServidoresForm,
    AgendarAtendimentoForm,
    AniversarianteForm,
    AtualizarDadosAvaliadorForm,
    DefinirAreasVinculacaoWizard,
    DocumentacaoExigidaUploadForm,
    EditarHorarioAfastamentoForm,
    GetBuscarServidorForm,
    ImportarArquivoSCDPForm,
    ImportarServidorWSForm,
    IndeferirProcessoAfastamentoParcialRHForm,
    ImportacaoPJForm,
    PessoaFisicaInformacoesDigitaisFracasForm,
    RejeitarSolicitacaoAlteracaoFotoForm,
    RelatorioAfastamentosCriticosForm,
    SalvarProcessoAfastamentoForm,
    ServidorFuncaoFormFactory,
    ServidorInformacoesPessoaisForm,
    ServidoresParaCapacitacaoPorSetorForm,
    SetorJornadaHistoricoFormFactory,
    UploadArquivosExtratorForm,
    ViagensPorCampusForm,
    WebserviceSIAPEForm,
    PessoaFisicaAlterarSenhaPontoForm,
    DocentesPorDisciplinaFiltroForm,
    SetorRaizFormFactory,
    EditarServidorCargoEmpregoAreaForm,
    ServidoresPorAreaFiltroForm,
    BasesLegaisSetorForm,
    AdicionarDadosBancariosPFForm,
)
from rh.importador_ws import ImportadorWs
from rh.models import (
    AcaoSaude,
    AfastamentoSiape,
    AgendaAtendimentoHorario,
    ArquivoUnico,
    Avaliador,
    CargaHorariaReduzida,
    DocumentacaoExigida,
    Funcao,
    HorarioAgendado,
    HorarioSemanal,
    PCA,
    PRIVATE_ROOT_DIR,
    PessoaFisica,
    PessoaJuridica,
    Servidor,
    ServidorAfastamento,
    ServidorFuncaoHistorico,
    ServidorOcorrencia,
    ServidorSetorHistorico,
    ServidorSetorLotacaoHistorico,
    Setor,
    SetorJornadaHistorico,
    Situacao,
    SolicitacaoAlteracaoFoto,
    Titulacao,
    UnidadeOrganizacional,
    Viagem,
    DadosBancariosPF,
)
from rh.pdf import imprime_carteira_funcional, imprime_cracha
from rh import tasks as rh_tasks

# Sinais utilizados na composição de views complexas, com isso, podemos criar um vínculo fraco entre RH e outras apps
rh_servidor_view_tab = Signal()  # providing_args=["request", "servidor", "verificacao_propria", "eh_chefe"]


@layout.quadro("Gestão de Pessoas", icone="users", pode_esconder=True)
def index_quadros(quadro, request):
    eh_rh_sistemico = request.user.has_perm("rh.eh_rh_sistemico")
    eh_rh_campus = request.user.has_perm("rh.eh_rh_campus")
    if eh_rh_sistemico or eh_rh_campus:
        qtd_servidores_sem_setor_suap = Servidor.get_sem_setor_suap().count()
        if qtd_servidores_sem_setor_suap:
            quadro.add_item(
                layout.ItemContador(
                    titulo="Servidor{}".format(pluralize(qtd_servidores_sem_setor_suap, "es")),
                    subtitulo="Sem setor SUAP",
                    qtd=qtd_servidores_sem_setor_suap,
                    url="/rh/servidores_sem_setor_suap/",
                )
            )

        qtd_processos_afastamento_parcial_a_validar_rh = CargaHorariaReduzida.get_processos_rh_a_validar().count()
        if qtd_processos_afastamento_parcial_a_validar_rh:
            quadro.add_item(
                layout.ItemContador(
                    titulo="Processo{} de afastamento parcial".format(pluralize(qtd_processos_afastamento_parcial_a_validar_rh, "s")),
                    subtitulo="A validar",
                    qtd=qtd_processos_afastamento_parcial_a_validar_rh,
                    url="/admin/rh/cargahorariareduzida/",
                )
            )

        qtd_servidores_sem_cargo = Servidor.get_sem_cargo().count()
        if qtd_servidores_sem_cargo:
            quadro.add_item(
                layout.ItemContador(
                    titulo="Servidor{}".format(pluralize(qtd_servidores_sem_cargo, "es")),
                    subtitulo="Sem cargo",
                    qtd=qtd_servidores_sem_cargo,
                    url="/rh/servidores_sem_cargo/",
                )
            )

        hoje = datetime.now()
        uo = get_uo(request.user)
        if eh_rh_sistemico and uo and "edu" in settings.INSTALLED_APPS:
            qtd_docentes_sem_disciplina_ingresso = (
                Servidor.objects.docentes()
                .filter(situacao__codigo=Situacao.ATIVO_PERMANENTE, professor__disciplina__isnull=True, setor__uo=uo)
                .count()
            )
            if qtd_docentes_sem_disciplina_ingresso:
                quadro.add_item(
                    layout.ItemContador(
                        titulo="Docente{} sem disciplina de ingresso".format(pluralize(qtd_docentes_sem_disciplina_ingresso)),
                        subtitulo="Campus {}".format(uo),
                        qtd=qtd_docentes_sem_disciplina_ingresso,
                        url="/edu/disciplina_ingresso_docentes/?campus={}&disciplinas={}".format(uo.pk, 1),
                    )
                )

        if eh_rh_sistemico and uo:
            qtd_servidores_sem_area = (
                Servidor.objects.ativos()
                .filter(cargo_emprego__cargoempregoarea__isnull=False, cargo_emprego_area__isnull=True)
                .distinct()
                .count()
            )
            if qtd_servidores_sem_area:
                quadro.add_item(
                    layout.ItemContador(
                        titulo="Servidor{}".format(pluralize(qtd_servidores_sem_area, "es")),
                        subtitulo="Sem área",
                        qtd=qtd_servidores_sem_area,
                        url="/rh/servidores_por_area/?com_area_cadastrada=2",
                    )
                )

        if uo:
            servidor_funcao_historico = ServidorFuncaoHistorico.objects.filter(
                setor__uo__equivalente=uo, data_fim_funcao__gte=hoje, setor_suap__isnull=True
            ).exclude(funcao__codigo=Funcao.CODIGO_ESTAGIARIO) | ServidorFuncaoHistorico.objects.filter(
                setor__uo__equivalente=uo, data_fim_funcao__isnull=True, setor_suap__isnull=True
            ).exclude(
                funcao__codigo=Funcao.CODIGO_ESTAGIARIO
            )
            qtd_servidor_funcao_historico = servidor_funcao_historico.count()
            if qtd_servidor_funcao_historico:
                uo_siape = UnidadeOrganizacional.objects.siape().filter(equivalente=uo, setor__excluido=False).latest("pk")
                quadro.add_item(
                    layout.ItemContador(
                        titulo="Funções de Servidores sem Setor SUAP",
                        subtitulo="Campus {}".format(uo_siape),
                        qtd=qtd_servidor_funcao_historico,
                        url="/admin/rh/servidorfuncaohistorico/?setoruo={}&com_data_fim=False".format(uo_siape.pk),
                    )
                )

    if request.user.has_perm("rh.view_servidor"):
        quadro.add_item(layout.ItemAcessoRapido(titulo="Servidores", icone="users", url="/admin/rh/servidor/?excluido__exact=0"))
        quadro.add_item(layout.BuscaRapida(titulo="Servidor", url="/admin/rh/servidor/"))

    return quadro


@layout.alerta()
def index_alertas(request):
    alertas = list()
    hoje = datetime.date(datetime.now())

    if request.user.eh_servidor or request.user.eh_prestador:
        qs_horarioagendado = HorarioAgendado.objects.filter(
            solicitante=request.user.get_relacionamento(), data_consulta__gte=hoje, cancelado=False
        )
        if qs_horarioagendado.exists():
            for horario in qs_horarioagendado:
                delta = horario.data_consulta - hoje
                alertas.append(
                    dict(
                        url="/admin/rh/acaosaude/?acao_saude_ativa=1",
                        titulo="Você tem um consulta agendada para daqui a {} dia(s).".format(delta.days),
                    )
                )
    return alertas


@rtr()
@permission_required("rh.pode_ver_relatorios_rh")
def index(request):
    """
    gráficos:
        1-servidores com vínculo institucional por situação funcional
            1.1-servidores ativos permanentes (docentes e téc) e pensionistas
        2-titulação de ativos permanentes, cedidos e temporários
        3-campus de lotação de ativos permanentes e cedidos
        4-campus de exercício de ativos permanentes e cedidos
        5-servidores por campus de lotação
        6-servidores por campus de exercício

    +
    quadros de referências:
        docentes
        técnicos administrativos
    """
    title = "Indicadores"

    # verifica se foi repassado algum filtro
    categoria = request.GET.get("categoria", "")

    # ------------------------------------------------------------------------------------------------------------------------
    # gráfico 1 - servidores com vínculo institucional por situação funcional
    series1 = []
    for situacao in Situacao.objects.all():
        lista_servidores = Servidor.objects.filter(excluido=False, situacao__codigo=situacao.codigo)
        if categoria:
            lista_servidores = lista_servidores.filter(cargo_emprego__grupo_cargo_emprego__categoria__exact=categoria)
        if lista_servidores.count():
            series1.append([situacao.nome, lista_servidores.count()])

    grafico1 = ColumnChart(
        "grafico1",
        title="Servidores por Situação Funcional",
        subtitle="Contabilizando servidores com vínculo institucional",
        minPointLength=10,
        data=series1,
    )
    grafico1.series[0]["dataLabels"] = dict(enabled=True, rotation=-90, color="#FFF", align="right", x=4, y=10)
    grafico1.xAxis["labels"] = dict(rotation=-45, align="right")

    # ------------------------------------------------------------------------------------------------------------------------
    # gráfico 1.1 - servidores ativo permanente docentes, tecnicos adm e pensionistas
    if not categoria:
        ativos_permanentes_docentes = Servidor.objects.filter(excluido=False, situacao__codigo=Situacao.ATIVO_PERMANENTE, eh_docente=True)
        ativos_permanentes_tecnicos = Servidor.objects.filter(
            excluido=False, situacao__codigo=Situacao.ATIVO_PERMANENTE, eh_tecnico_administrativo=True
        )
        series1_1 = []
        series1_1.append(["Técnicos Adm. Ativos Permanentes", ativos_permanentes_tecnicos.count()])
        series1_1.append(["Docentes Ativos Permanentes", ativos_permanentes_docentes.count()])

        # PENSIONISTAS
        if "contracheques" in settings.INSTALLED_APPS:
            from contracheques.models import ContraCheque

            contra_cheques = ContraCheque.objects.ativos().fita_espelho().order_by("-ano__ano", "-mes")  # ordem decrescente
            if contra_cheques.exists():
                ultimo_contra_cheque = contra_cheques[0]  # pega o primeiro registro
                num_pensionistas = (
                    ContraCheque.objects.ativos()
                    .fita_espelho()
                    .filter(ano__ano=ultimo_contra_cheque.ano.ano, mes=ultimo_contra_cheque.mes, pensionista__isnull=False)
                    .count()
                )
            else:
                num_pensionistas = 0

            series1_1.append(["Pensionistas", num_pensionistas])

            grafico1_1 = ColumnChart(
                "grafico11",
                title="Ativos Permanentes e Pensionistas",
                subtitle="Contabilizando ativos permanentes e pensionistas",
                minPointLength=10,
                data=series1_1,
            )
            grafico1_1.series[0]["dataLabels"] = dict(enabled=True, rotation=-90, color="#FFF", align="right", x=4, y=10)
            grafico1_1.xAxis["labels"] = dict(rotation=-45, align="right")

    # ------------------------------------------------------------------------------------------------------------------------
    # gráfico 2 - titulação de ativos permanentes, cedidos e temporários
    series2 = []

    # com titulacao
    for titulacao in Titulacao.objects.all():
        lista_servidores = Servidor.objects.filter(
            excluido=False, situacao__codigo__in=Situacao.SITUACOES_EFETIVOS_E_TEMPORARIOS, titulacao__codigo=titulacao.codigo
        )
        if categoria:
            lista_servidores = lista_servidores.filter(cargo_emprego__grupo_cargo_emprego__categoria__exact=categoria)
        if lista_servidores.count():
            series2.append([titulacao.nome, lista_servidores.count()])

    # sem titulacao
    lista_servidores_sem_titulacao = Servidor.objects.filter(
        excluido=False, situacao__codigo__in=Situacao.SITUACOES_EFETIVOS_E_TEMPORARIOS, titulacao__isnull=True
    )
    if categoria:
        lista_servidores_sem_titulacao = lista_servidores_sem_titulacao.filter(
            cargo_emprego__grupo_cargo_emprego__categoria__exact=categoria
        )

    series2.append(["Nenhuma titulação", lista_servidores_sem_titulacao.count()])

    grafico2 = PieChart(
        "grafico2", title="Titulação de Servidores", subtitle="Contabilizando ativos permanentes, cedidos e temporários", data=series2
    )

    # ------------------------------------------------------------------------------------------------------------------------
    # gráfico 3 - campus de lotação de ativos permanentes e cedidos (efetivos)
    series3 = []
    campus = UnidadeOrganizacional.objects.siape().all().order_by("sigla")
    for c in campus:
        lista_servidores = Servidor.objects.filter(
            excluido=False, situacao__codigo__in=Situacao.SITUACOES_EFETIVOS, setor_lotacao__uo__id__exact=c.id
        )
        if categoria:
            lista_servidores = lista_servidores.filter(cargo_emprego__grupo_cargo_emprego__categoria__exact=categoria)
        if lista_servidores.count():
            series3.append((c.sigla, lista_servidores.count()))

    grafico3 = PieChart(
        "grafico3", title="Campus de Lotação de Servidores Efetivos", subtitle="Contabilizando ativos permanentes e cedidos", data=series3
    )

    # ------------------------------------------------------------------------------------------------------------------------
    # gráfico 4 - campus de exercício de ativos permanentes e cedidos (efetivos)
    series4 = []
    campus = UnidadeOrganizacional.objects.siape().all().order_by("sigla")
    for c in campus:
        lista_servidores = Servidor.objects.filter(
            excluido=False, situacao__codigo__in=Situacao.SITUACOES_EFETIVOS, setor_exercicio__uo__id__exact=c.id
        )
        if categoria:
            lista_servidores = lista_servidores.filter(cargo_emprego__grupo_cargo_emprego__categoria__exact=categoria)
        if lista_servidores.count():
            series4.append((c.sigla, lista_servidores.count()))

    grafico4 = PieChart(
        "grafico4", title="Campus de Exercício de Servidores Efetivos", subtitle="Contabilizando ativos permanentes e cedidos", data=series4
    )

    # ------------------------------------------------------------------------------------------------------------------------
    # gráfico 5 - servidores por campus de lotação
    if not categoria:
        series5 = []
        campus = UnidadeOrganizacional.objects.siape().all().order_by("sigla")
        for c in campus:
            series5.append(
                [
                    c.sigla,
                    # efetivos docentes
                    Servidor.objects.filter(
                        excluido=False, situacao__codigo__in=Situacao.SITUACOES_EFETIVOS, eh_docente=True, setor_lotacao__uo__id__exact=c.id
                    ).count(),
                    # efetivos téc admin
                    Servidor.objects.filter(
                        excluido=False,
                        situacao__codigo__in=Situacao.SITUACOES_EFETIVOS,
                        eh_tecnico_administrativo=True,
                        setor_lotacao__uo__id__exact=c.id,
                    ).count(),
                    # temporários
                    Servidor.objects.filter(
                        excluido=False, situacao__codigo__in=Situacao.SITUACOES_TEMPORARIOS, setor_lotacao__uo__id__exact=c.id
                    ).count(),
                    # estagiários
                    Servidor.objects.filter(
                        excluido=False, situacao__codigo__in=Situacao.situacoes_siape_estagiarios(), setor_lotacao__uo__id__exact=c.id
                    ).count(),
                ]
            )

        grafico5 = GroupedColumnChart(
            "grafico5",
            title="Servidores por Campus de Lotação",
            data=series5,
            groups=["Docentes", "Téc. Administrativos", "Temporários", "Estagiários"],
        )

    # ------------------------------------------------------------------------------------------------------------------------
    # gráfico 6 - servidores por campus de exercício
    if not categoria:
        series6 = []
        campus = UnidadeOrganizacional.objects.siape().all().order_by("sigla")
        for c in campus:
            series6.append(
                [
                    c.sigla,
                    # efetivos docentes
                    Servidor.objects.filter(
                        excluido=False,
                        situacao__codigo__in=Situacao.SITUACOES_EFETIVOS,
                        eh_docente=True,
                        setor_exercicio__uo__id__exact=c.id,
                    ).count(),
                    # efetivos téc admin
                    Servidor.objects.filter(
                        excluido=False,
                        situacao__codigo__in=Situacao.SITUACOES_EFETIVOS,
                        eh_tecnico_administrativo=True,
                        setor_exercicio__uo__id__exact=c.id,
                    ).count(),
                    # temporários
                    Servidor.objects.filter(
                        excluido=False, situacao__codigo__in=Situacao.SITUACOES_TEMPORARIOS, setor_exercicio__uo__id__exact=c.id
                    ).count(),
                    # estagiários
                    Servidor.objects.filter(
                        excluido=False, situacao__codigo__in=Situacao.situacoes_siape_estagiarios(), setor_exercicio__uo__id__exact=c.id
                    ).count(),
                ]
            )
        grafico6 = GroupedColumnChart(
            "grafico6",
            title="Servidores por Campus de Exercício",
            data=series6,
            groups=["Docentes", "Téc. Administrativos", "Temporários", "Estagiários"],
        )

    # ------------------------------------------------------------------------------------------------------------------------

    graficos = [grafico1, grafico2, grafico3, grafico4]
    if not categoria:
        if "contracheques" in settings.INSTALLED_APPS:
            graficos.append(grafico1_1)
        graficos.append(grafico5)
        graficos.append(grafico6)

    if categoria == "tecnico_administrativo":
        quadro_referencia_administrativos = Servidor.quadro_referencia_administrativos()

    elif categoria == "docente":
        texto_explicativo_situacoes_efetivos = "Efetivos (ativo permanente e cedido)"
        texto_explicativo_situacoes_temporarios = (
            "Temporários (contrato de professor substituto, contrato de professor temporário e contrato temporário)"
        )
        (quadro_referencia_docentes, quadro_referencia_docentes_total) = Servidor.quadro_referencia_docentes()

    inconsistencias = dict()
    campus_siape = UnidadeOrganizacional.objects.siape().all()
    efetivos_nao_importados = Servidor.objects.efetivos().filter(sistema_origem="")
    efetivos_sem_campus_lotacao = Servidor.objects.efetivos().filter(sistema_origem="SIAPE", setor_lotacao__uo=None)
    efetivos_sem_campus_exercicio = Servidor.objects.efetivos().filter(sistema_origem="SIAPE", setor_exercicio__uo=None)
    if not campus_siape:
        inconsistencias["campus_siape"] = 1
    if efetivos_nao_importados:
        inconsistencias["efetivos_nao_importados"] = efetivos_nao_importados
    if efetivos_sem_campus_lotacao:
        inconsistencias["efetivos_sem_campus_lotacao"] = efetivos_sem_campus_lotacao
    if efetivos_sem_campus_exercicio:
        inconsistencias["efetivos_sem_campus_exercicio"] = efetivos_sem_campus_exercicio

    try:
        data_ultima_importacao_siape = Log.objects.filter(app="rh").order_by("-horario")[0].horario
    except Exception:
        pass

    return locals()


@rtr()
@permission_required("rh.pode_ver_relatorios_rh")
def servidores_sem_setor_suap(request):
    title = "Servidores sem Setor SUAP"
    if request.method == "POST":
        mensagens = ""
        for servidor_post, setor_post in list(request.POST.items()):
            # Só interessa iterar os `names` que começam com "setor_".
            if not servidor_post.startswith("setor_") or not setor_post:
                continue

            try:
                setor = Setor.objects.get(id=int(setor_post))
            except Setor.DoesNotExist:
                continue
            else:
                matricula = servidor_post.strip("setor_")
                servidor = Servidor.objects.get(matricula=matricula)
                servidor.setor = setor
                servidor.save()
                if servidor.is_historico_setor_com_pendencias:
                    mensagens += "Verifique o histórico de setores do servidor {}. ".format(servidor)
        return httprr(".", "Modificação de servidores efetuada com sucesso. {}".format(mensagens))
    else:
        meu_campus_siape = get_uo_siape()
        apenas_do_meu_campus_siape = "meu_campus_siape" in request.GET
        servidores_sem_suap = dict()
        servidores = Servidor.get_sem_setor_suap(do_meu_campus=apenas_do_meu_campus_siape)
        situacoes = (Situacao.ATIVO_EM_OUTRO_ORGAO,) + Situacao.situacoes_siape_estagiarios()
        servidores_situacoes = servidores.exclude(situacao__codigo__in=situacoes)
        for servidor in servidores_situacoes:
            setor_exercicio = servidor.setor_exercicio
            if setor_exercicio is not None:
                uo = setor_exercicio.uo
                if uo is not None:
                    campus_equivalente = uo.equivalente
                    if campus_equivalente is not None:
                        setores_suap = Setor.objects.filter(uo=campus_equivalente)
                        servidores_sem_suap[servidor.id] = setores_suap

    return locals()


@rtr()
@permission_required("rh.pode_ver_relatorios_rh")
def servidores_sem_cargo(request):
    title = "Servidores sem Cargo"
    if request.method == "POST":
        for servidor_post, setor_post in list(request.POST.items()):
            # Só interessa iterar os `names` que começam com "setor_".
            if not servidor_post.startswith("setor_") or not setor_post:
                continue

            id_setor = int(setor_post)
            try:
                setor = Setor.objects.get(id=id_setor)
            except Setor.DoesNotExist:
                continue
            else:
                matricula = servidor_post.strip("setor_")
                servidor = get_object_or_404(Servidor, matricula=matricula)
                servidor.setor = setor
                servidor.save()
        return httprr(".", "Modificação de servidores efetuada com sucesso.")
    else:
        meu_campus = get_uo()
        apenas_do_meu_campus = "meu_campus" in request.GET
        servidores_sem_suap = dict()
        servidores = Servidor.get_sem_cargo(do_meu_campus=apenas_do_meu_campus)
        return locals()


@rtr()
@permission_required("rh.pode_ver_relatorios_rh")
def servidor_buscar(request):
    title = "Buscar Servidores"
    FormClass = GetBuscarServidorForm()
    form = FormClass(request.GET or None)
    if form.is_valid():
        return tela_relatorio(request, form.cleaned_data)
    else:
        campos_servidor = campos
        campos_servidor_nao_agrupaveis = campos_nao_agrupaveis
    return locals()


@rtr()
@permission_required("rh.pode_ver_relatorios_rh")
def tela_relatorio(request, cleaned_data=None):
    campos_selecionados = request.GET.getlist("campos")
    servidores_qs, filtrado = buscar_servidores(cleaned_data)
    if campos_selecionados and not filtrado:
        return httprr(".", "Selecione algum filtro.", "error")
    encoded_url = request.GET.urlencode()
    return rh_tasks.gerar_busca_servidor(request, cleaned_data, servidores_qs, campos_selecionados, encoded_url)


def buscar_servidores(dados):
    """Retorna queryset de servidores com os filtros passados em ``dados``"""
    filtrado = False
    if dados["matricula"]:
        filtrado = True
        return Servidor.objects.filter(matricula=dados["matricula"]), filtrado
    if dados["cpf"]:
        filtrado = True
        return Servidor.objects.filter(cpf=mask_cpf(dados["cpf"])), filtrado

    # data_exclusao_instituidor eh o criterio usado para informar que um servidor inativo (instituidor)
    # nao saia nos relatorios, pois após essa data, ele perdeu todos os vínculo que o prendem ao instituto.
    # Os demais serviodres (ativos, aposentados, estagiarios, etc) vem com esse campo nulo
    filtrados = Servidor.objects.filter(data_exclusao_instituidor__isnull=True)

    if dados["nome"]:
        filtrado = True
        nomes = dados["nome"].split()
        for nome in nomes:
            filtrados = filtrados.filter(nome__icontains=nome)

    if dados["excluido"] == "1":
        filtrados = filtrados.filter(excluido=True)
    elif dados["excluido"] == "0":
        filtrados = filtrados.filter(excluido=False)

    if dados["setor"]:
        filtrado = True
        setor = dados["setor"]
        if "recursivo" in dados:
            setores = setor.ids_descendentes
        else:
            setores = [setor.id]
        filtrados = filtrados.filter(setor__id__in=setores)

    if dados["setor_contem"]:
        filtrado = True
        filtrados = filtrados.filter(setor__sigla__icontains=dados["setor_contem"]) | filtrados.filter(
            setor__nome__unaccent__icontains=dados["setor_contem"]
        )

    if dados["categoria"] != "todos":
        filtrado = True
        filtrados = filtrados.filter(
            cargo_emprego__grupo_cargo_emprego__categoria__isnull=False, cargo_emprego__grupo_cargo_emprego__categoria=dados["categoria"]
        )

    if dados["cargo_emprego"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(cargo_emprego__isnull=True)
    elif dados["cargo_emprego"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(cargo_emprego__isnull=False)
    elif dados["cargo_emprego"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(cargo_emprego=dados["cargo_emprego"])

    if dados["cargo_emprego_area"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(cargo_emprego_area__isnull=True)
    elif dados["cargo_emprego_area"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(cargo_emprego_area__isnull=False)
    elif dados["cargo_emprego_area"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(cargo_emprego_area=dados["cargo_emprego_area"])

    if dados["classe"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(cargo_classe__isnull=True)
    elif dados["classe"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(cargo_classe__isnull=False)
    elif dados["classe"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(cargo_classe=dados["classe"])

    if dados["funcao"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(funcao__isnull=True)
    elif dados["funcao"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(funcao__isnull=False)
    elif dados["funcao"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(
            servidorfuncaohistorico__funcao=dados["funcao"], servidorfuncaohistorico__data_fim_funcao__isnull=True
        ).distinct()

    if dados["funcao_atividade"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(funcao_atividade__isnull=True)
    elif dados["funcao_atividade"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(funcao_atividade__isnull=False)
    elif dados["funcao_atividade"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(funcao_atividade=dados["funcao_atividade"])

    if dados["jornada_trabalho"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(jornada_trabalho__isnull=True)
    elif dados["jornada_trabalho"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(jornada_trabalho__isnull=False)
    elif dados["jornada_trabalho"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(jornada_trabalho=dados["jornada_trabalho"])

    if dados["jornada_setor_trabalho"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(
            setor__setorjornadahistorico__jornada_trabalho__isnull=True, setor__setorjornadahistorico__data_fim_da_jornada__isnull=True
        )
    elif dados["jornada_setor_trabalho"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(
            setor__setorjornadahistorico__jornada_trabalho__isnull=False, setor__setorjornadahistorico__data_fim_da_jornada__isnull=True
        )
    elif dados["jornada_setor_trabalho"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(
            setor__setorjornadahistorico__jornada_trabalho=dados["jornada_setor_trabalho"],
            setor__setorjornadahistorico__data_fim_da_jornada__isnull=True,
        )

    if dados["regime_juridico"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(regime_juridico__isnull=True)
    elif dados["regime_juridico"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(regime_juridico__isnull=False)
    elif dados["regime_juridico"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(regime_juridico=dados["regime_juridico"])

    if dados["situacao"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(situacao__isnull=True)
    elif dados["situacao"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(situacao__isnull=False)
    elif dados["situacao"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(situacao=dados["situacao"])

    if dados["titulacao"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(titulacao__isnull=True)
    elif dados["titulacao"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(titulacao__isnull=False)
    elif dados["titulacao"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(titulacao=dados["titulacao"])

    if dados["setor_lotacao_siape"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(setor_lotacao__isnull=True)
    elif dados["setor_lotacao_siape"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(setor_lotacao__isnull=False)
    elif dados["setor_lotacao_siape"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(setor_lotacao=dados["setor_lotacao_siape"])

    if dados["campus_lotacao_siape"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(setor_lotacao__uo__isnull=True)
    elif dados["campus_lotacao_siape"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(setor_lotacao__uo__isnull=False)
    elif dados["campus_lotacao_siape"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(setor_lotacao__uo=dados["campus_lotacao_siape"])

    if dados["setor_exercicio_siape"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(setor_exercicio__isnull=True)
    elif dados["setor_exercicio_siape"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(setor_exercicio__isnull=False)
    elif dados["setor_exercicio_siape"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(setor_exercicio=dados["setor_exercicio_siape"])

    if dados["campus_exercicio_siape"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(setor_exercicio__uo__isnull=True)
    elif dados["campus_exercicio_siape"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(setor_exercicio__uo__isnull=False)
    elif dados["campus_exercicio_siape"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(setor_exercicio__uo=dados["campus_exercicio_siape"])

    if dados["tem_digital"] == "sim":
        filtrado = True
        filtrados = filtrados.filter(funcionario_ptr__pessoafisica_ptr__template__isnull=False)
    elif dados["tem_digital"] == "nao":
        filtrado = True
        filtrados = filtrados.filter(funcionario_ptr__pessoafisica_ptr__template__isnull=True)
    elif dados["tem_digital"] == "qualquer":
        pass

    if dados["aniversariantes"]:
        filtrado = True
        mes_escolhido = dados["aniversariantes"]
        filtrados = (
            filtrados.filter(nascimento_data__month=mes_escolhido, sistema_origem="SIAPE")
            .extra(select={"nascimento_data_day": "EXTRACT('day' FROM pessoa_fisica.nascimento_data)"})
            .order_by("nascimento_data_day", "nome")
        )

    if dados["disciplina_ingresso"] != "vazio" and "edu" in settings.INSTALLED_APPS:
        filtrado = True
        from edu.models import Professor

        if dados["disciplina_ingresso"] == "nulo":
            disciplina_escolhida_pks_servidores = Professor.objects.filter(disciplina__isnull=True).values_list(
                "vinculo__pessoa", flat=True
            )
        else:
            disciplina_escolhida_pk = dados["disciplina_ingresso"]
            disciplina_escolhida_pks_servidores = Professor.objects.filter(disciplina__pk=disciplina_escolhida_pk).values_list(
                "vinculo__pessoa", flat=True
            )
        filtrados = filtrados.filter(pk__in=disciplina_escolhida_pks_servidores)

    if dados["nivel"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(nivel_padrao__isnull=True)
    elif dados["nivel"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(nivel_padrao__isnull=False)
    elif dados["nivel"] == "qualquer":
        pass
    else:  # 101, 102, 103, ..., 416
        filtrado = True
        filtrados = filtrados.filter(nivel_padrao=dados["nivel"])

    if dados["deficiencia"] == "vazio":
        filtrado = True
        filtrados = filtrados.filter(deficiencia__isnull=True)
    elif dados["deficiencia"] == "nao_vazio":
        filtrado = True
        filtrados = filtrados.filter(deficiencia__isnull=False)
    elif dados["deficiencia"] == "qualquer":
        pass
    else:
        filtrado = True
        filtrados = filtrados.filter(deficiencia=dados["deficiencia"])

    return filtrados.order_by("nome"), filtrado


@rtr()
# @permission_required('rh.view_servidor, rh.eh_servidor')
@lps
def servidor(request, servidor_matricula):
    servidor = get_object_or_404(Servidor, matricula=servidor_matricula)
    title = str(servidor)
    verificacao_propria = request.user == servidor.user
    is_chefe = False

    if request.user.eh_servidor:
        is_chefe = request.user.get_relacionamento().eh_chefe_de(servidor)

    pode_ver_cpf_servidor = request.user.has_perm("rh.pode_ver_cpf_servidor") or verificacao_propria
    pode_ver_dados_pessoais_servidor = request.user.has_perm("rh.pode_ver_dados_pessoais_servidor") or verificacao_propria
    pode_ver_endereco_servidor = request.user.has_perm("rh.pode_ver_endereco_servidor") or verificacao_propria
    pode_ver_telefones_pessoais_servidor = request.user.has_perm("rh.pode_ver_telefones_pessoais_servidor") or verificacao_propria
    pode_ver_dados_bancarios_servidor = request.user.has_perm("rh.pode_ver_dados_bancarios_servidor") or verificacao_propria
    pode_ver_historico_funcional_servidor = request.user.has_perm("rh.pode_ver_historico_funcional_servidor") or verificacao_propria
    pode_ver_ocorrencias_afastamentos_servidor = (
        request.user.has_perm("rh.pode_ver_ocorrencias_afastamentos_servidor") or verificacao_propria or is_chefe
    )
    pode_ver_historico_setores_servidor = request.user.has_perm("rh.pode_ver_historico_setores_servidor") or verificacao_propria
    pode_ver_historico_funcao_servidor = request.user.has_perm("rh.pode_ver_historico_funcao_servidor") or verificacao_propria
    pode_ver_viagens_servidor = request.user.has_perm("rh.pode_ver_viagens_servidor") or verificacao_propria or is_chefe
    pode_ver_dados_funcionais_servidor = request.user.has_perm("rh.pode_ver_dados_funcionais_servidor") or verificacao_propria
    pode_ver__identificacao_unica_siape = request.user.has_perm("rh.pode_ver_identificacao_unica_siape") or verificacao_propria

    hoje = date.today()
    endereco_irregular = not (
        servidor.pessoaendereco
        and servidor.pessoaendereco.municipio
        and (servidor.pessoaendereco.municipio.uf == Configuracao.get_valor_por_chave("comum", "instituicao_estado"))
    )

    # if verificacao_propria or is_rh or pode_ver_dados_extras:
    if pode_ver_ocorrencias_afastamentos_servidor:
        servidor_ocorrencias = (
            ServidorOcorrencia.objects.filter(servidor=servidor).exclude(ocorrencia__grupo_ocorrencia__nome="AFASTAMENTO").order_by("-data")
        )
        servidor_afastamentos = ServidorAfastamento.objects.filter(servidor=servidor, cancelado=False).order_by("-data_inicio")
        servidor_afastamentos_suap = []
        if "ponto" in settings.INSTALLED_APPS:
            Afastamento = apps.get_model("ponto", "Afastamento")
            servidor_afastamentos_suap = Afastamento.objects.filter(vinculo=servidor.get_vinculo()).order_by("-data_ini")

        totais_qtd_dias_por_ano = OrderedDict()
        totais_qtd_dias_ocorrencias = 0
        totais_qtd_dias_afastamentos = 0
        for ocorrencia in servidor_ocorrencias:
            if ocorrencia.data_termino:
                for ano, qtd_dias in list(get_qtd_dias_por_ano(ocorrencia.data, ocorrencia.data_termino).items()):
                    if ano not in totais_qtd_dias_por_ano:
                        totais_qtd_dias_por_ano[ano] = [0, 0]
                    totais_qtd_dias_por_ano[ano][0] += qtd_dias  # 0 = ocorrências
                    totais_qtd_dias_ocorrencias += qtd_dias
        for afastamento in servidor_afastamentos:
            if afastamento.data_termino:
                for ano, qtd_dias in list(get_qtd_dias_por_ano(afastamento.data_inicio, afastamento.data_termino).items()):
                    if ano not in totais_qtd_dias_por_ano:
                        totais_qtd_dias_por_ano[ano] = [0, 0]
                    totais_qtd_dias_por_ano[ano][1] += qtd_dias  # 1 = afastamentos
                    totais_qtd_dias_afastamentos += qtd_dias
        for afastamento in servidor_afastamentos_suap:
            if afastamento.data_fim:
                for ano, qtd_dias in list(get_qtd_dias_por_ano(afastamento.data_ini, afastamento.data_fim).items()):
                    if ano not in totais_qtd_dias_por_ano:
                        totais_qtd_dias_por_ano[ano] = [0, 0]
                    totais_qtd_dias_por_ano[ano][1] += qtd_dias  # 1 = afastamentos
                    totais_qtd_dias_afastamentos += qtd_dias

        totais = {k: totais_qtd_dias_por_ano[k] for k in sorted(totais_qtd_dias_por_ano.keys(), reverse=True)}

    if pode_ver_historico_setores_servidor:
        historico_setor = ServidorSetorHistorico.objects.filter(servidor=servidor).order_by("-data_inicio_no_setor")
        historico_setor_siape = ServidorSetorLotacaoHistorico.objects.filter(servidor=servidor).order_by("-data_inicio_setor_lotacao")

    funcoes_ativas = ServidorFuncaoHistorico.objects.atuais().filter(servidor=servidor).order_by("data_inicio_funcao")
    if pode_ver_historico_funcao_servidor:
        servidor_historico_funcao = ServidorFuncaoHistorico.objects.filter(servidor=servidor).order_by("data_inicio_funcao")

    # Historico de Carga Horaria
    alteracao_carga_horaria = CargaHorariaReduzida.objects.filter(servidor=servidor)

    pode_gerar_cracha = servidor.pode_gerar_cracha()
    pode_gerar_carteira_funcional = servidor.pode_gerar_carteira_funcional()

    # provimentos
    if pode_ver_historico_funcional_servidor:
        pcas = PCA.montar_timeline(servidor.pca_set.all().order_by("data_entrada_pca"))
        outros_vinculos = (
            Servidor.objects.filter(cpf=servidor.cpf)
            .exclude(situacao__codigo__in=Situacao.situacoes_siape_estagiarios())
            .exclude(pk=servidor.pk)
        )

        servidor_tempo_servico_na_instituicao_via_pca = servidor.tempo_servico_na_instituicao_via_pca()
        servidor_tempo_servico_na_instituicao_via_pca_ficto = servidor.tempo_servico_na_instituicao_via_pca(ficto=True)

    viagens_servidor = Viagem.consolidadas.filter(servidor=servidor).order_by("-data_inicio_viagem")

    extra_tabs = list()
    for _, data in rh_servidor_view_tab.send(
        sender=index, request=request, servidor=servidor, verificacao_propria=verificacao_propria, eh_chefe=is_chefe
    ):
        if data:
            extra_tabs.append(data)

    return locals()


@rtr()
@permission_required("rh.view_servidor")
def editar_informacoes_pessoais_servidor(request):
    if request.user.eh_servidor:
        servidor = request.user.get_relacionamento()
        title = str(servidor)
        verificacao_propria = request.user == servidor.user
        if verificacao_propria:
            form = ServidorInformacoesPessoaisForm(request.POST or None, instance=servidor)
            if form.is_valid():
                form.save()
                return httprr("..", "Informações pessoais salvas com sucesso.")

        return locals()
    raise PermissionDenied("Tela apenas para servidores.")


@rtr()
@login_required()
def editar_informacoes_digitais_fracas(request, pessoa_fisica_id):
    pessoa_fisica = get_object_or_404(PessoaFisica, id=pessoa_fisica_id)
    pode_cadastrar_digital = request.user.has_perm("rh.pode_cadastrar_digital")
    verificacao_propria = request.user.get_profile() == pessoa_fisica and pessoa_fisica.tem_digital_fraca
    if not pode_cadastrar_digital and not verificacao_propria:
        raise PermissionDenied("Você não tem permissão para acessar essa tela.")
    if pode_cadastrar_digital:
        title = "Editar Informações de Digitais Fracas de {}".format(str(pessoa_fisica))
        form = PessoaFisicaInformacoesDigitaisFracasForm(request.POST or None, instance=pessoa_fisica, request=request)
    elif verificacao_propria:
        title = "Editar Minha Senha do Ponto"
        form = PessoaFisicaAlterarSenhaPontoForm(request.POST or None, instance=pessoa_fisica, request=request)

    if form.is_valid():
        form.save()
        return httprr("..", "Informações salvas com sucesso.")

    return locals()


@rtr()
@permission_required("rh.pode_ver_relatorios_rh")
def tela_recursos_humanos(request):
    class Tabela:
        def __init__(self, titulo):
            self.titulo = titulo
            self.tabela = []
            self.soma = OrderedDict()

        def adicionar(self, label, valores):
            self.tabela.append(valores)
            for vlabel, valor in list(valores.items()):
                if not isinstance(valor, str):
                    if vlabel in list(self.soma.keys()):
                        self.soma[vlabel] += valor
                    else:
                        self.soma[vlabel] = valor
                else:
                    self.soma[vlabel] = "Total"

        def cabecalho(self):
            return list(self.soma.keys())

        def total(self):
            return self.soma

        def linhas(self):
            return self.tabela

        def titulo(self):
            return self.titulo

    # Servidores vinculados retorna exluido=False
    servidores_all = Servidor.objects.vinculados()
    # Recupera só as situacoes usadas atualmente
    situacoes_usadas = Situacao.objects.filter(
        id__in=servidores_all.values("situacao")
        .annotate(Count("situacao"))
        .order_by()
        .filter(situacao__count__gt=0)
        .values_list("situacao", flat=True)
    )

    # ------------------------------------------------------------------------------------------
    relatorios = []

    tabela_geral_1 = Tabela("Docentes, técnicos admistrativos e estagiários - Composição por sexo")
    tabela_geral_2 = Tabela("Docentes, técnicos admistrativos e estagiários - Composição por regime de trabalho")

    tabela_docente_1 = Tabela("Docentes - Composição por sexo")
    tabela_docente_2 = Tabela("Docentes - Composição por regime de trabalho")

    tabela_tecnico_1 = Tabela("Técnicos administrativos - Composição por sexo")
    tabela_tecnico_2 = Tabela("Técnicos administrativos - Composição por regime de trabalho")

    tabela_estagiarios_1 = Tabela("Estagiários - Composição por sexo")
    tabela_estagiarios_2 = Tabela("Estagiários - Composição por regime de trabalho")

    for situacao in situacoes_usadas:
        servidores_situacao = servidores_all.filter(situacao=situacao)
        #       Tabela Por Sexo
        servidores_masculino = servidores_situacao.filter(sexo="M")
        servidores_feminino = servidores_situacao.filter(sexo="F")
        servidores_sexo_nao_definido = servidores_situacao.exclude(sexo__in=["F", "M"])

        #       Geral
        linha = OrderedDict()
        linha["Situação"] = situacao.nome
        linha["Masculino"] = servidores_masculino.count()
        linha["Feminino"] = servidores_feminino.count()
        linha["Não definido"] = servidores_sexo_nao_definido.count()
        linha["Total"] = servidores_masculino.count() + servidores_feminino.count() + servidores_sexo_nao_definido.count()

        tabela_geral_1.adicionar(str(situacao), linha)
        #       Tabela Por regime de Trabalho
        servidores_vinte_horas = servidores_situacao.filter(jornada_trabalho__nome__unaccent__icontains="20 HORAS")
        servidores_vinte_e_cinco_horas = servidores_situacao.filter(jornada_trabalho__nome__unaccent__icontains="25 HORAS")
        servidores_trinta_horas = servidores_situacao.filter(jornada_trabalho__nome__unaccent__icontains="30 HORAS")
        servidores_quarenta_horas = servidores_situacao.filter(jornada_trabalho__nome__unaccent__icontains="40 HORAS")
        servidores_dedicacao_exclusiva = servidores_situacao.filter(jornada_trabalho__nome__unaccent__icontains="DEDICACAO EXCLUSIVA")
        servidor_regime_trabalho_nao_definido = servidores_situacao.filter(jornada_trabalho__isnull=True)

        linha = OrderedDict()
        linha["Situação"] = situacao.nome
        linha["20h Semanais"] = servidores_vinte_horas.count()
        linha["25h Semanais"] = servidores_vinte_e_cinco_horas.count()
        linha["30h Semanais"] = servidores_trinta_horas.count()
        linha["40h Semanais"] = servidores_quarenta_horas.count()
        linha["Dedicação Exclusiva"] = servidores_dedicacao_exclusiva.count()
        linha["Não Definido"] = servidor_regime_trabalho_nao_definido.count()
        linha["Total"] = (
            servidores_vinte_horas.count()
            + servidores_vinte_e_cinco_horas.count()
            + servidores_trinta_horas.count()
            + servidores_quarenta_horas.count()
            + servidores_dedicacao_exclusiva.count()
            + servidor_regime_trabalho_nao_definido.count()
        )

        tabela_geral_2.adicionar(str(situacao), linha)

        #       Tecnicos Administrativos

        linha = OrderedDict()
        linha["Situação"] = situacao.nome
        linha["Masculino"] = servidores_masculino.filter(eh_tecnico_administrativo=True).count()
        linha["Feminino"] = servidores_feminino.filter(eh_tecnico_administrativo=True).count()
        linha["Não definido"] = servidores_sexo_nao_definido.filter(eh_tecnico_administrativo=True).count()
        linha["Total"] = (
            servidores_masculino.filter(eh_tecnico_administrativo=True).count()
            + servidores_feminino.filter(eh_tecnico_administrativo=True).count()
            + servidores_sexo_nao_definido.filter(eh_tecnico_administrativo=True).count()
        )

        tabela_tecnico_1.adicionar(str(situacao), linha)

        linha = OrderedDict()
        linha["Situação"] = situacao.nome
        linha["20h Semanais"] = servidores_vinte_horas.filter(eh_tecnico_administrativo=True).count()
        linha["25h Semanais"] = servidores_vinte_e_cinco_horas.filter(eh_tecnico_administrativo=True).count()
        linha["30h Semanais"] = servidores_trinta_horas.filter(eh_tecnico_administrativo=True).count()
        linha["40h Semanais"] = servidores_quarenta_horas.filter(eh_tecnico_administrativo=True).count()
        linha["Dedicação Exclusiva"] = servidores_dedicacao_exclusiva.filter(eh_tecnico_administrativo=True).count()
        linha["Não definido"] = servidor_regime_trabalho_nao_definido.filter(eh_tecnico_administrativo=True).count()
        linha["Total"] = (
            servidores_vinte_horas.filter(eh_tecnico_administrativo=True).count()
            + servidores_vinte_e_cinco_horas.filter(eh_tecnico_administrativo=True).count()
            + servidores_trinta_horas.filter(eh_tecnico_administrativo=True).count()
            + servidores_quarenta_horas.filter(eh_tecnico_administrativo=True).count()
            + servidores_dedicacao_exclusiva.filter(eh_tecnico_administrativo=True).count()
            + servidor_regime_trabalho_nao_definido.filter(eh_tecnico_administrativo=True).count()
        )

        tabela_tecnico_2.adicionar(str(situacao), linha)

        #       Docentes
        linha = OrderedDict()
        linha["Situação"] = situacao.nome
        linha["Masculino"] = servidores_masculino.filter(eh_docente=True).count()
        linha["Feminino"] = servidores_feminino.filter(eh_docente=True).count()
        linha["Não definido"] = servidores_sexo_nao_definido.filter(eh_docente=True).count()
        linha["Total"] = (
            servidores_masculino.filter(eh_docente=True).count()
            + servidores_feminino.filter(eh_docente=True).count()
            + servidores_sexo_nao_definido.filter(eh_docente=True).count()
        )

        tabela_docente_1.adicionar(str(situacao), linha)

        linha = OrderedDict()
        linha["Situação"] = situacao.nome
        linha["20h Semanais"] = servidores_vinte_horas.filter(eh_docente=True).count()
        linha["25h Semanais"] = servidores_vinte_e_cinco_horas.filter(eh_docente=True).count()
        linha["30h Semanais"] = servidores_trinta_horas.filter(eh_docente=True).count()
        linha["40h Semanais"] = servidores_quarenta_horas.filter(eh_docente=True).count()
        linha["Dedicação Exclusiva"] = servidores_dedicacao_exclusiva.filter(eh_docente=True).count()
        linha["Não definido"] = servidor_regime_trabalho_nao_definido.filter(eh_docente=True).count()
        linha["Total"] = (
            servidores_vinte_horas.filter(eh_docente=True).count()
            + servidores_vinte_e_cinco_horas.filter(eh_docente=True).count()
            + servidores_trinta_horas.filter(eh_docente=True).count()
            + servidores_quarenta_horas.filter(eh_docente=True).count()
            + servidores_dedicacao_exclusiva.filter(eh_docente=True).count()
        )

        tabela_docente_2.adicionar(str(situacao), linha)

        if situacao.codigo in Situacao.situacoes_siape_estagiarios():
            estagiarios_etg1 = servidores_situacao.filter(funcao_codigo=1)
            estagiarios_masculino_etg1 = estagiarios_etg1.filter(sexo="M")
            estagiarios_feminino_etg1 = estagiarios_etg1.filter(sexo="F")
            estagiarios_sexo_nao_definido_etg1 = estagiarios_etg1.exclude(sexo__in=["F", "M"])

            estagiarios_etg2 = servidores_situacao.filter(funcao_codigo=2)
            estagiarios_masculino_etg2 = estagiarios_etg2.filter(sexo="M")
            estagiarios_feminino_etg2 = estagiarios_etg2.filter(sexo="F")
            estagiarios_sexo_nao_definido_etg2 = estagiarios_etg2.exclude(sexo__in=["F", "M"])

            linha = OrderedDict()
            linha["Situação"] = "ETG1"
            linha["Masculino"] = estagiarios_masculino_etg1.count()
            linha["Feminino"] = estagiarios_feminino_etg1.count()
            linha["Não definido"] = estagiarios_sexo_nao_definido_etg1.count()
            linha["Total"] = estagiarios_etg1.count()
            tabela_estagiarios_1.adicionar(str(situacao), linha)

            linha = OrderedDict()
            linha["Situação"] = "ETG2"
            linha["Masculino"] = estagiarios_masculino_etg2.count()
            linha["Feminino"] = estagiarios_feminino_etg2.count()
            linha["Não definido"] = estagiarios_sexo_nao_definido_etg2.count()
            linha["Total"] = estagiarios_etg2.count()
            tabela_estagiarios_1.adicionar(str(situacao), linha)

            estagiarios_vinte_horas_etg1 = estagiarios_etg1.filter(jornada_trabalho__nome__unaccent__icontains="20 HORAS")
            estagiarios_vinte_e_cinco_horas_etg1 = estagiarios_etg1.filter(jornada_trabalho__nome__unaccent__icontains="25 HORAS")
            estagiarios_trinta_horas_etg1 = estagiarios_etg1.filter(jornada_trabalho__nome__unaccent__icontains="30 HORAS")
            estagiarios_quarenta_horas_etg1 = estagiarios_etg1.filter(jornada_trabalho__nome__unaccent__icontains="40 HORAS")
            estagiarios_dedicacao_exclusiva_etg1 = estagiarios_etg1.filter(
                jornada_trabalho__nome__unaccent__icontains="DEDICACAO EXCLUSIVA"
            )

            estagiarios_vinte_horas_etg2 = estagiarios_etg2.filter(jornada_trabalho__nome__unaccent__icontains="20 HORAS")
            estagiarios_vinte_e_cinco_horas_etg2 = estagiarios_etg2.filter(jornada_trabalho__nome__unaccent__icontains="25 HORAS")
            estagiarios_trinta_horas_etg2 = estagiarios_etg2.filter(jornada_trabalho__nome__unaccent__icontains="30 HORAS")
            estagiarios_quarenta_horas_etg2 = estagiarios_etg2.filter(jornada_trabalho__nome__unaccent__icontains="40 HORAS")
            estagiarios_dedicacao_exclusiva_etg2 = estagiarios_etg2.filter(
                jornada_trabalho__nome__unaccent__icontains="DEDICACAO EXCLUSIVA"
            )

            linha = OrderedDict()
            linha["Situação"] = "ETG1"
            linha["20h Semanais"] = estagiarios_vinte_horas_etg1.count()
            linha["25h Semanais"] = estagiarios_vinte_e_cinco_horas_etg1.count()
            linha["30h Semanais"] = estagiarios_trinta_horas_etg1.count()
            linha["40h Semanais"] = estagiarios_quarenta_horas_etg1.count()
            linha["Dedicação Exclusiva"] = estagiarios_dedicacao_exclusiva_etg1.count()
            linha["Total"] = estagiarios_etg1.count()

            tabela_estagiarios_2.adicionar(str(situacao), linha)

            linha = OrderedDict()
            linha["Situação"] = "ETG2"
            linha["20h Semanais"] = estagiarios_vinte_horas_etg2.count()
            linha["25h Semanais"] = estagiarios_vinte_e_cinco_horas_etg2.count()
            linha["30h Semanais"] = estagiarios_trinta_horas_etg2.count()
            linha["40h Semanais"] = estagiarios_quarenta_horas_etg2.count()
            linha["Dedicação Exclusiva"] = estagiarios_dedicacao_exclusiva_etg2.count()
            linha["Total"] = estagiarios_etg2.count()

            tabela_estagiarios_2.adicionar(str(situacao), linha)

    relatorios.append(tabela_geral_1)
    relatorios.append(tabela_geral_2)
    relatorios.append(tabela_docente_1)
    relatorios.append(tabela_docente_2)
    relatorios.append(tabela_tecnico_1)
    relatorios.append(tabela_tecnico_2)
    relatorios.append(tabela_estagiarios_1)
    relatorios.append(tabela_estagiarios_2)

    return locals()


def servidores_dados_exportacao(servidores_ids):
    """
    Monta tabela de dados retornados da busca de servidores com funcao para
    exportação via XLS.
    """
    rows = []
    header = [
        "#",
        "MATRICULA",
        "NOME",
        "FUNÇÃO",
        "ATIVIDADE",
        "DATA OCUPAÇÃO",
        "UORG",
        "QUANTIDADE DE SERVIDORES NO SETOR",
        "QUANTIDADE DE SERVIDORES SETORES DESCENDENTES",
    ]
    rows.append(header)
    count = 0
    servidores_qs = Servidor.objects.filter(id__in=servidores_ids)
    for s in servidores_qs:
        count += 1
        row = [
            count,
            s.matricula,
            s.nome,
            s.funcao.nome,
            s.atividade,
            s.funcao_data_ocupacao,
            s.setor,
            s.setor.qtd_servidores(recursivo=False),
            s.setor.qtd_servidores(recursivo=True),
        ]
        rows.append(row)

    return rows


@rtr()
@permission_required("rh.pode_ver_relatorios_rh")
def tela_servidores_com_funcao(request):
    title = "Lista de Servidores com Função"
    servidores = (
        Servidor.objects.ativos()
        .filter(funcao__isnull=False, funcao_data_saida__isnull=True)
        .select_related("funcao", "funcao_atividade", "setor")
        .order_by("setor__uo", "nome")
    )
    setores = Setor.suap.all()
    FormClass = ServidorFuncaoFormFactory()
    dict_setores = dict()
    if request.POST:
        form = FormClass(request.POST)
        if form.is_valid():
            campus = request.POST["campus"]
            funcao = request.POST["funcao"]

            setores = Setor.suap.all()
            if campus:
                campus = int(campus)
                servidores = servidores.filter(setor__uo=campus)
                setores = setores.filter(uo=campus)

            if funcao:
                funcao = int(funcao)
                servidores = servidores.filter(funcao=funcao)
    else:
        form = FormClass()

    for setor in setores:
        if not setor in list(dict_setores.keys()):
            dict_setores[setor] = dict()
            dict_setores[setor]["quantidade_servidores_setor"] = Servidor.objects.ativos_permanentes().filter(setor=setor).count()
            dict_setores[setor]["quantidade_servidores_setor_descendentes"] = (
                Servidor.objects.ativos_permanentes().filter(setor__in=setor.descendentes).select_related("superior").count()
            )

    return locals()


@permission_required("rh.pode_gerar_cracha")
def cracha_pessoa(request, pessoa_id):
    servidor = get_object_or_404(Servidor, pk=pessoa_id)
    if servidor.pode_gerar_cracha():
        documentos = DocumentoControle.objects.filter(
            solicitante_vinculo=servidor.get_vinculo(), documento_tipo__identificador=DocumentoControleTipo.CRACHA
        )
        if documentos.exists():
            solicitacao = documentos.latest("data_solicitacao")
            servidor.nome_sugerido_cracha = solicitacao.nome_sugerido or ""
            servidor.nome_social_cracha = solicitacao.nome_social or ""
        return imprime_cracha(servidor)
    return HttpResponse("A pessoa não tem dados suficientes para a impressão do crachá.")


@permission_required("rh.pode_gerar_cracha")
def cracha_setor(request, setor_id):
    lista = []
    setor = Setor.objects.get(pk=setor_id)
    for servidor in setor.get_servidores().filter(excluido=False):
        if servidor.pode_gerar_cracha():
            lista.append(servidor)
    return imprime_cracha(lista)


@login_required()
@permission_required("rh.pode_gerar_carteira")
def carteira_funcional(request, servidor_id=None):
    servidor_ids = []
    if servidor_id:
        request.session["_servidores_ids"] = [servidor_id]
        servidor_ids = [servidor_id]
    else:
        servidor_ids = request.session.get("_servidores_ids")

    versao = None
    qs_tipo_carteira_funcional = TipoCarteiraFuncional.objects.filter(ativo=True)
    if qs_tipo_carteira_funcional.exists():
        tipo_carteira_funcional = qs_tipo_carteira_funcional[0]
        versao = tipo_carteira_funcional.template

    if versao == TipoCarteiraFuncional.MODELO_2016:
        return httprr("/rh/imprimir_carteira_funcional_pdf")
    else:
        qs_servidores = Servidor.objects.filter(id__in=servidor_ids)
        servidores = []
        for servidor in qs_servidores:
            servidores.append(servidor)
        return imprime_carteira_funcional(servidores)


def carteira_funcional_setor(request, setor_id, abrangencia):
    """
    Gera carteira funcionais para um servidores de um setor.

    Apenas os servidores ativos permanentes podem ter a carteira gerada por
    esta função.

    """
    # Bloqueio de acesso com base na permissão
    if not request.user.has_perm("rh.pode_gerar_carteira"):
        raise PermissionDenied()

    # verificando a versão da carteira funcional que está ativo
    versao = None
    qs_tipo_carteira_funcional = TipoCarteiraFuncional.objects.filter(ativo=True)
    if qs_tipo_carteira_funcional.exists():
        tipo_carteira_funcional = qs_tipo_carteira_funcional[0]
        versao = tipo_carteira_funcional.template

    # selecionando servidores do setor selecionado
    servidores_setor = Servidor.objects.filter(setor=setor_id)

    lista = [servidor for servidor in servidores_setor if servidor.pode_gerar_carteira_funcional()]
    if abrangencia != "all":
        nova_lista = []
        servidor_ids = []
        for servidor in lista:
            dc = DocumentoControle.objects.filter(
                solicitante=servidor.pessoa_ptr, documento_tipo__identificador=DocumentoControleTipo.CARTEIRA_FUNCIONAL, ativo=True
            )
            if not dc:
                nova_lista.append(servidor)
                servidor_ids.append(servidor.id)
        if nova_lista:
            if versao == TipoCarteiraFuncional.MODELO_2016:
                request.session["_servidores_ids"] = servidor_ids
                return httprr("/rh/imprimir_carteira_funcional_pdf")
            else:
                return imprime_carteira_funcional(nova_lista)
        else:
            return httprr("/admin/rh/setor/", "Operação não pôde ser realizada")

    if versao == TipoCarteiraFuncional.MODELO_2016:
        request.session["_servidores_ids"] = [servidor.id for servidor in lista]
        return httprr("/rh/imprimir_carteira_funcional_pdf")
    else:
        return imprime_carteira_funcional(lista)


@documento(enumerar_paginas=False)
@rtr()
@login_required()
@permission_required("rh.pode_gerar_carteira")
def imprimir_carteira_funcional_pdf(request):
    usuario_logado = request.user.pessoafisica.sub_instance()
    local_data_expedicao = None
    qs_cid = ConfiguracaoImpressaoDocumento.objects.filter(
        uo=usuario_logado.campus, tipos_documento__identificador=DocumentoControleTipo.CARTEIRA_FUNCIONAL
    )
    if qs_cid:
        local_impressao = qs_cid[0].local_impressao
        data_expedicao = datetime.today().strftime("%d/%m/%Y")
        local_data_expedicao = "{}, {}".format(local_impressao, data_expedicao)

    servidor_ids = request.session.get("_servidores_ids", [])
    servidores = Servidor.objects.filter(id__in=servidor_ids)
    situacao_estagiario = Situacao.objects.filter(codigo__in=Situacao.situacoes_siape_estagiarios())

    carteiras = []
    for servidor in servidores:
        nome = servidor.nome.upper()
        matricula = servidor.matricula
        grupo_sanguineo = servidor.grupo_sanguineo
        fator_rh = servidor.fator_rh
        nome_mae = servidor.nome_mae.upper()
        rg = servidor.rg
        rg_orgao = servidor.rg_orgao
        rg_uf = servidor.rg_uf
        cpf = servidor.cpf
        nascimento_data = servidor.nascimento_data.strftime("%d/%m/%Y")

        aposentado = ""
        if not servidor.situacao in situacao_estagiario:
            cargo_emprego = servidor.cargo_emprego.nome
            if servidor.cargo_emprego.nome_amigavel:
                cargo_emprego = servidor.cargo_emprego.nome_amigavel
            if servidor.situacao.nome_siape == "APOSENTADO":
                aposentado = "(APOSENTADO)"
        else:
            cargo_emprego = "ESTAGIÁRIO(A)"
        imagemfoto = servidor.get_foto_150x200_url()

        identidade = "{}   {}/{}".format(rg, rg_orgao, rg_uf)
        sangue = "{}{}".format(grupo_sanguineo, fator_rh)
        naturalidade = str(servidor.nascimento_municipio)

        carteiras.append(
            {
                "nome": nome,
                "matricula": matricula,
                "nome_mae": nome_mae,
                "cpf": cpf,
                "foto": imagemfoto,
                "cargo": cargo_emprego,
                "data_nascimento": nascimento_data,
                "identidade": identidade,
                "sangue": sangue,
                "naturalidade": naturalidade,
                "local_data_expedicao": local_data_expedicao,
            }
        )

    return locals()


@rtr()
@permission_required("rh.pode_ver_relatorios_rh")
def aniversariantes(request):
    title = "Aniversariantes do Mês"
    mes_escolhido = int(request.GET.get("mes", datetime.today().month))
    meses = (
        {"numero": 1, "nome": "Janeiro"},
        {"numero": 2, "nome": "Fevereiro"},
        {"numero": 3, "nome": "Março"},
        {"numero": 4, "nome": "Abril"},
        {"numero": 5, "nome": "Maio"},
        {"numero": 6, "nome": "Junho"},
        {"numero": 7, "nome": "Julho"},
        {"numero": 8, "nome": "Agosto"},
        {"numero": 9, "nome": "Setembro"},
        {"numero": 10, "nome": "Outubro"},
        {"numero": 11, "nome": "Novembro"},
        {"numero": 12, "nome": "Dezembro"},
    )

    servidores = (
        Servidor.objects.vinculados()
        .filter(nascimento_data__month=mes_escolhido, sistema_origem="SIAPE")
        .order_by("nascimento_data__day", "nome")
    )

    form = AniversarianteForm(request.GET or None)
    if form.is_valid():
        campus = form.cleaned_data.get("uo")
        if campus:
            servidores = servidores.filter(setor__uo=campus)

    return locals()


@rtr()
@permission_required("rh.pode_ver_relatorios_rh")
def enderecos(request):
    def abreviar(endereco):
        return (
            endereco.upper()
            .replace("AVENIDA", "AV")
            .replace("BLOCO", "BL")
            .replace("NOVA", "N")
            .replace("RUA", "R")
            .replace("ESPERANCA", "ESPER")
            .replace("PARQUE", "PQ")
            .replace("SENADOR", "SEN")
            .replace("RESIDENCIAL", "RESID")
            .replace("APARTAMENTO", "AP")
            .replace("APTO", "AP")
            .replace("APT", "AP")
            .replace("LACERDA MONTENEGRO", "LACERDA")
        )

    def dividir_endereco(endereco):
        se = abreviar(s.endereco).split(",")
        if len(se) == 5:  # se nao tem complemento
            se.insert(2, "")
        return se

    lista = {"Servidores Ativos por Campus": dict(), "Servidores por Situação": dict()}
    lista["Servidores por Situação"]["Substitutos"] = []
    for s in Servidor.objects.substitutos().filter(sistema_origem="SIAPE"):
        lista["Servidores por Situação"]["Substitutos"].append([s.nome, s.telefones] + dividir_endereco(s.endereco))
    lista["Servidores por Situação"]["Inativos"] = []
    for s in Servidor.objects.aposentados().filter(sistema_origem="SIAPE"):
        lista["Servidores por Situação"]["Inativos"].append([s.nome, s.telefones] + dividir_endereco(s.endereco))
    lista["Servidores por Situação"]["Cedidos"] = []
    for s in Servidor.objects.cedidos().filter(sistema_origem="SIAPE"):
        lista["Servidores por Situação"]["Cedidos"].append([s.nome, s.telefones] + dividir_endereco(s.endereco))
    campus = list(UnidadeOrganizacional.objects.siape().all().order_by("setor__sigla").values_list("setor__sigla", flat=True))
    for c in campus:
        lista["Servidores Ativos por Campus"][c] = []
        for s in Servidor.objects.ativos_permanentes().filter(sistema_origem="SIAPE").filter(setor__uo__setor__sigla=c):
            lista["Servidores Ativos por Campus"][c].append([s.nome, s.telefones] + dividir_endereco(s.endereco))

    return locals()


@rtr("comum/templates/html_generico_para_listas.html")
@permission_required("rh.pode_ver_relatorios_rh")
def enderecos_fora_do_estado(request):
    lista = [["Matrícula", "Nome", "Situação", "Município / UF", "E-mail"]]
    uf = Configuracao.get_valor_por_chave("comum", "instituicao_estado")
    pes = PessoaEndereco.objects.exclude(municipio__uf=uf).values_list("pessoa", flat=True)
    servidores = Servidor.objects.ativos().filter(funcionario_ptr__in=pes)
    for s in servidores:
        lista.append(
            [
                '<a href="../servidor/{}/">{}</a>'.format(s.matricula, s.matricula),
                s.nome,
                s.situacao.nome,
                "{} / {}".format(s.pessoaendereco.municipio.nome, s.pessoaendereco.municipio.uf),
                s.email,
            ]
        )
    servidores = pes = None
    mensagem = ""
    titulo = "Servidores com endereço fora do {}".format(uf)
    return locals()


def handle_uploaded_file_extrator(arquivo):
    destination = os.path.join("rh/arquivos_siape/", arquivo.name)
    content = b"".join(arquivo.chunks())
    default_storage.save(destination, io.BytesIO(content))


def apagar_diretorio_extrator():
    destination = "rh/arquivos_siape/"
    arquivos = [i for i in default_storage.listdir(destination)[1] if i.endswith(".gz") or i.endswith(".zip")]
    for f in arquivos:
        default_storage.delete(destination + f)


@rtr()
@permission_required("rh.pode_gerenciar_extracao_siape")
def upload_arquivos_extrator(request):
    title = "Upload Arquivo Extrator"
    form = UploadArquivosExtratorForm(request.POST or None)
    historico = Log.objects.filter(app="rh", titulo="Importação de arquivos").order_by("-horario")[:10]
    if request.method == "POST":
        form = UploadArquivosExtratorForm(request.POST, request.FILES)
        if form.is_valid():
            arquivo = form.files["arquivo"]
            apagar_diretorio_extrator()
            handle_uploaded_file_extrator(arquivo)
            return httprr("..", "Upload de Arquivo {} feito com sucesso!".format(arquivo.name))
    return locals()


@rtr()
def pessoa_juridica(request, pk):
    pj = PessoaJuridica.objects.get(pk=pk)
    return locals()


@rtr()
@permission_required("rh.view_pessoajuridica")
def pessoajuridica(request, pessoajuridica_id):
    pj = get_object_or_404(PessoaJuridica, pk=pessoajuridica_id)
    return locals()


@rtr()
@permission_required("rh.view_pessoajuridica")
def importar_pj(request):
    title = "Importador de Pessoa Jurídica"
    form = ImportacaoPJForm(request.POST or None, files=request.FILES or None)
    if form.is_valid():
        errors = form.processar()
        if errors:
            return httprr(".", "Ocorreram alguns erros na importação: {}".format(errors), tag="error")
        else:
            return httprr(".", "Dados importados com sucesso sem erros.")

    return locals()


@rtr()
@permission_required("rh.pode_gerenciar_setor_jornada_historico")
def setor_jornada_historico(request, setor_pk):
    setor = get_object_or_404(Setor, pk=setor_pk)
    title = "Histórico de Jornadas de Trabalho do Setor {} - {}".format(setor.sigla, setor.nome)

    form_class = SetorJornadaHistoricoFormFactory(request)
    if request.POST:
        form = form_class(request.POST)
        if form.is_valid():
            form.save()

            return httprr(".", "Histórico de Jornada adicionado com sucesso.")
    else:
        nova_jornada = SetorJornadaHistorico()
        nova_jornada.setor = setor
        form = form_class(instance=nova_jornada)

    #
    # restringe a lista de setores no formulário de adição
    #
    form.fields["setor"].widget = Select()
    form.fields["setor"].queryset = Setor.objects.filter(id=setor.id)
    form.fields["setor"].initial = setor

    mensagens_periodos = setor.jornada_trabalho_pendencias()

    return locals()


@permission_required("rh.pode_gerenciar_setor_jornada_historico")
def setor_jornada_historico_remover(request, jornada_historico_pk):
    jornada_historico = SetorJornadaHistorico.objects.get(pk=jornada_historico_pk)
    setor_pk = jornada_historico.setor.pk
    jornada_historico.delete()
    return httprr("/rh/setor_jornada_historico/{:d}/".format(setor_pk), "Histórico removido com sucesso.")


@rtr()
@permission_required("rh.pode_gerenciar_setor_jornada_historico")
def setor_jornada_historico_pendencias(request):
    title = "Setores com pendências em Histórico de Jornadas de Trabalho"

    if request.user.has_perm("rh.eh_rh_sistemico"):
        setores = Setor.objects.all()
    else:
        #
        # exibe apenas os setores pertencentes ao mesmo campus do usuário logado
        #
        funcionario = request.user.get_profile().funcionario
        if funcionario:
            setores = Setor.objects.filter(uo__sigla=funcionario.setor.uo.sigla)
        else:
            setores = []  # usuário logado tem permissão para gerenciar jornadas de trabalho de setores mas não é funcionário!!!!!

    setores_com_pendencias = []
    for setor in setores:
        if setor.jornada_trabalho_pendencias():
            setores_com_pendencias.append(setor)

    return locals()


@rtr()
@login_required
def atualizar_dados_avaliador(request):
    title = "Atualizar Dados Pessoais"
    pessoa_fisica = request.user.get_profile()
    if not Avaliador.objects.filter(vinculo__pessoa=pessoa_fisica.pessoa_ptr).exists():
        raise PermissionDenied

    form = AtualizarDadosAvaliadorForm(request.POST or None, request=request)
    if form.is_valid():
        form.save()
        return httprr("..", "Dados atualizados com sucesso.")

    return locals()


@rtr()
@login_required
def visualizar_avaliador(request, avaliador_id):
    avaliador = get_object_or_404(Avaliador, pk=avaliador_id)
    title = "Avaliador {}".format(avaliador.vinculo.user.get_profile().nome)

    return locals()


@rtr()
@permission_required("rh.pode_ver_relatorios_rh")
def afastamentos_servidores(request):
    title = "Afastamentos dos Servidores"

    if not request.method == "POST":
        if "filtros-afastamentos-post" in request.session:
            request.POST = request.session["filtros-afastamentos-post"]
            request.method = "POST"
    form = AfastamentosServidoresForm(request.POST or None)
    if request.method == "POST":
        request.session["filtros-afastamentos-post"] = request.POST

        if form.is_valid():
            afastamentos_servidor = ServidorAfastamento.objects
            if form.cleaned_data.get("tipo_afastamento") != "Todos":
                afastamentos_servidor = afastamentos_servidor.filter(afastamento__tipo=form.cleaned_data.get("tipo_afastamento"))

            if form.cleaned_data.get("categoria") != "Todos":
                afastamentos_servidor = afastamentos_servidor.filter(
                    servidor__cargo_emprego__grupo_cargo_emprego__categoria__exact=form.cleaned_data.get("categoria")
                )

            if form.cleaned_data.get("situacao") != "Todos":
                afastamentos_servidor = afastamentos_servidor.filter(cancelado=form.cleaned_data.get("situacao"))

            if form.cleaned_data.get("afastamento"):
                afastamentos_servidor = afastamentos_servidor.filter(afastamento=form.cleaned_data.get("afastamento"))

            if form.cleaned_data.get("uo"):
                afastamentos_servidor = afastamentos_servidor.filter(servidor__setor__uo=form.cleaned_data.get("uo"))

            afastamentos_servidor = afastamentos_servidor.filter(
                data_termino__gte=form.cleaned_data.get("data_inicio"), data_inicio__lte=form.cleaned_data.get("data_termino")
            )

            fields = ("servidor",)
            custom_fields = dict(
                matricula=Column("Matricula", accessor="servidor.matricula", order_by="servidor__matricula"),
                servidor=Column("Servidor", accessor="servidor", order_by="servidor__pessoafisica_ptr__nome"),
                data_inicio=DateColumn(format="d/m/Y", verbose_name="Data de Início"),
                data_termino=DateColumn(format="d/m/Y", verbose_name="Data de Término"),
                afastamento=Column("Afastamento", accessor="afastamento", order_by="afastamento"),
                tipo=Column("Tipo de Afastamento", accessor="afastamento.tipo", order_by="afastamento__tipo"),
                cancelado=Column("Cancelado", accessor="cancelado", order_by="cancelado"),
            )
            sequence = ["servidor", "matricula", "data_inicio", "data_termino", "afastamento"]
            table = get_table(
                request=request,
                queryset=afastamentos_servidor,
                fields=fields,
                custom_fields=custom_fields,
                sequence=sequence,
                per_page_field=50,
            )
            if request.GET.get("relatorio", None):
                return tasks.table_export(request.GET.get("relatorio", None), *table.get_params())

    return locals()


@rtr()
@login_required
@permission_required("rh.pode_ver_relatorios_viagens")
def viagens_consolidadas(request):
    title = "Relatório de Viagens Consolidadas"

    form = ViagensPorCampusForm(request.POST or None, request=request)
    if form.is_valid():
        viagens = OrderedDict()
        ano = int(form.cleaned_data["ano"].ano)
        mes = int(form.cleaned_data["mes"])
        viagens_qs = Viagem.consolidadas.filter(data_inicio_viagem__year=ano).order_by("codigo_siorg")
        if mes:
            viagens_qs = viagens_qs.filter(data_inicio_viagem__month=mes)

        total_valor_desconto_auxilio_alimentacao = Decimal("0.0")
        total_valor_desconto_auxilio_transporte = Decimal("0.0")
        total_valor_passagem = Decimal("0.0")
        total_valor_diaria = Decimal("0.0")
        total_valor_viagem = Decimal("0.0")
        total_quantidade_viagens = 0

        for viagem in viagens_qs:

            if viagens.get(viagem.codigo_siorg):
                dicionario_por_siorg = viagens[viagem.codigo_siorg]
                dicionario_por_siorg["nome_siorg"] = viagem.nome_siorg
                dicionario_por_siorg["codigo_siorg"] = viagem.codigo_siorg
                dicionario_por_siorg["valor_desconto_auxilio_alimentacao"] = (
                    dicionario_por_siorg["valor_desconto_auxilio_alimentacao"] + viagem.valor_desconto_auxilio_alimentacao
                )
                dicionario_por_siorg["valor_desconto_auxilio_transporte"] = (
                    dicionario_por_siorg["valor_desconto_auxilio_transporte"] + viagem.valor_desconto_auxilio_transporte
                )
                dicionario_por_siorg["valor_passagem"] = dicionario_por_siorg["valor_passagem"] + viagem.valor_passagem
                dicionario_por_siorg["valor_diaria"] = dicionario_por_siorg["valor_diaria"] + viagem.valor_diaria
                dicionario_por_siorg["valor_viagem"] = dicionario_por_siorg["valor_viagem"] + viagem.valor_viagem
                dicionario_por_siorg["quantidade_viagens"] = dicionario_por_siorg["quantidade_viagens"] + 1
                viagens[viagem.codigo_siorg] = dicionario_por_siorg

            else:
                dicionario_por_siorg = dict()
                dicionario_por_siorg["nome_siorg"] = viagem.nome_siorg
                dicionario_por_siorg["codigo_siorg"] = viagem.codigo_siorg
                dicionario_por_siorg["valor_desconto_auxilio_alimentacao"] = viagem.valor_desconto_auxilio_alimentacao
                dicionario_por_siorg["valor_desconto_auxilio_transporte"] = viagem.valor_desconto_auxilio_transporte
                dicionario_por_siorg["valor_passagem"] = viagem.valor_passagem
                dicionario_por_siorg["valor_diaria"] = viagem.valor_diaria
                dicionario_por_siorg["valor_viagem"] = viagem.valor_viagem
                dicionario_por_siorg["quantidade_viagens"] = 1
                viagens[viagem.codigo_siorg] = dicionario_por_siorg

            total_valor_desconto_auxilio_alimentacao += viagem.valor_desconto_auxilio_alimentacao
            total_valor_desconto_auxilio_transporte += viagem.valor_desconto_auxilio_transporte
            total_valor_passagem += viagem.valor_passagem
            total_valor_diaria += viagem.valor_diaria
            total_valor_viagem += viagem.valor_viagem
            total_quantidade_viagens += 1

    return locals()


@rtr()
@login_required
@permission_required("rh.pode_ver_relatorios_viagens_detalhados")
def viagens_consolidadas_detalhamento(request, ano, mes, siorg):
    viagens = Viagem.consolidadas.filter(data_inicio_viagem__year=ano).order_by("codigo_siorg")
    mes_referencia = ""
    if int(mes):
        viagens = viagens.filter(data_inicio_viagem__month=int(mes))
        mes_referencia = Meses.get_mes(int(mes))

    campus = "Todos"
    if siorg != "todos":
        viagens = viagens.filter(codigo_siorg=siorg)
        campus = viagens[0].nome_siorg

    if viagens.exists():

        total_valor_desconto_auxilio_alimentacao = viagens.aggregate(Sum("valor_desconto_auxilio_alimentacao"))
        total_valor_desconto_auxilio_transporte = viagens.aggregate(Sum("valor_desconto_auxilio_transporte"))
        total_valor_passagem = viagens.aggregate(Sum("valor_passagem"))
        total_valor_diaria = viagens.aggregate(Sum("valor_diaria"))
        total_valor_viagem = viagens.aggregate(Sum("valor_viagem"))

        fields = (
            "numero_pcdp",
            "nome_siorg",
            "pessoa_fisica",
            "tipo_proposto",
            "objetivo_viagem",
            "valor_desconto_auxilio_alimentacao",
            "valor_desconto_auxilio_transporte",
            "valor_passagem",
            "valor_diaria",
            "valor_viagem",
            "situacao",
        )

        custom_fields = dict(
            numero_pcdp=LinkColumn(
                "tela_pcdp", kwargs={"pcdp_pk": Accessor("pk")}, verbose_name="Número PCDP", accessor=Accessor("numero_pcdp")
            ),
            data_inicio_viagem=DateColumn(format="d/m/Y"),
            data_fim_viagem=DateColumn(format="d/m/Y"),
            data_emissao_bilhete=DateColumn(
                format="d/m/Y",
                order_by="bilheteviagem.data_emissao",
                verbose_name="Data da Emissão dos Bilhetes",
                accessor="get_data_emissao_bilhetes",
            ),
        )

        sequence = ["numero_pcdp", "nome_siorg", "pessoa_fisica", "tipo_proposto", "objetivo_viagem"]
        if "relatorio" in request.GET:
            custom_fields["motivo_viagem"] = Column(verbose_name="Motivo da Viagem", accessor=Accessor("get_motivo_viagem_truncate"))
            sequence.append("motivo_viagem")

        sequence.append("data_inicio_viagem")
        sequence.append("data_fim_viagem")
        sequence.append("data_emissao_bilhete")

        table = get_table(
            request=request, queryset=viagens, fields=fields, custom_fields=custom_fields, sequence=sequence, per_page_field=50
        )
        table.add_sum_table_foot("valor_desconto_auxilio_alimentacao")
        table.add_sum_table_foot("valor_desconto_auxilio_transporte")
        table.add_sum_table_foot("valor_passagem")
        table.add_sum_table_foot("valor_diaria")
        table.add_sum_table_foot("valor_viagem")
        if request.GET.get("relatorio", None):
            return tasks.table_export(request.GET.get("relatorio", None), *table.get_params())

    title = "Detalhamento do Relatório de Viagens Consolidadas do ano {} - {}".format(ano, "Todos")
    return locals()


@rtr()
@login_required
def tela_pcdp(request, pcdp_pk):
    viagem = get_object_or_404(Viagem, pk=pcdp_pk)
    if viagem.servidor:
        verificacao_propria = request.user == viagem.servidor.user
    if not request.user.has_perm("rh.pode_ver_relatorios_rh") and not verificacao_propria:
        raise PermissionDenied("Você não tem permissão de acesso a essa página.")
    title = "Viagem de {} de {} à {}".format(
        viagem.pessoa_fisica.nome, viagem.data_inicio_viagem.strftime("%d/%m/%Y"), viagem.data_fim_viagem.strftime("%d/%m/%Y")
    )
    return locals()


def handle_uploaded_file_scdp(tipo, arquivo):
    if tipo == 0:
        destination = os.path.join(settings.BASE_DIR, "rh/arquivos_scdp/viagens/", arquivo.name)
    elif tipo == 1:
        destination = os.path.join(settings.BASE_DIR, "rh/arquivos_scdp/bilhetes/", arquivo.name)
    with open(os.path.join(destination), "w") as f:
        for chunk in arquivo.chunks():
            f.write(chunk)


@rtr()
@permission_required("rh.pode_gerenciar_extracao_scdp")
def scdp_importar_do_arquivo(request):
    title = "Importar Arquivo do SCDP"
    form = ImportarArquivoSCDPForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        if request.POST.get("tipo"):
            handle_uploaded_file_scdp(int(request.POST.get("tipo")), form.files["arquivo"])
            return httprr(request.path, "Upload de Arquivo SCDP feito com sucesso!")
        else:
            messages.error(request, "Você não escolheu um tipo de arquivo.")
    return locals()


@rtr()
def scdp_importar_bilhetes_do_arquivo(request):
    if not request.user.is_superuser:
        raise PermissionDenied()
    title = "Importar Arquivo dos Bilhetes do DW-SCDP"
    form = ImportarArquivoSCDPForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        handle_uploaded_file_scdp(form.files["arquivo"])
        return httprr(request.path, "Upload de Arquivo SCDP feito com sucesso!")
    return locals()


@rtr()
@permission_required("avaliacao_integrada.change_eixo")
def definir_areas_vinculacao(request):
    title = "Definir Áreas dos Setores"
    form = DefinirAreasVinculacaoWizard(request.POST or None)
    if form.is_valid():
        form.processar()
        return httprr(request.path, "Áreas vinculadas com sucesso.")
    return locals()


@rtr()
@permission_required("avaliacao_integrada.change_eixo")
def areas_vinculacao_setor(request):
    title = "Áreas de Vinculação dos Setores"
    setor = Setor.objects.get(sigla=get_sigla_reitoria())
    return locals()


@rtr()
@login_required()
def servidores_para_capacitacao_por_setor(request):
    title = "Dados dos Servidores para concessão de capacitação Strictu Sensu"
    form = ServidoresParaCapacitacaoPorSetorForm(request.POST or None, request=request)
    if form.is_valid():
        setor = form.cleaned_data["setor"]
        setores_filhos = form.cleaned_data["setores_filhos"]
        servidor = request.user.get_profile().funcionario.sub_instance()
        jornada_maxima = 40
        if servidor.eh_chefe_do_setor_hoje(setor) or request.user.has_perm("rh.pode_ver_relatorios_rh"):
            servidores_do_setor = setor.get_servidores(recursivo=setores_filhos).annotate(titulacao_isnull=Count("titulacao"))
            servidores = servidores_do_setor.all().order_by("titulacao_isnull", "titulacao__codigo")
            total_jornada_trabalho = 0
            total_jornada_trabalho_pca = 0
            total_jornada_maxima = 0
            for servidor in servidores:
                if not servidor.afastamentos_para_capacitacao_strictu_sensu_hoje.exists():
                    total_jornada_trabalho += servidor.jornada_trabalho.get_jornada_trabalho_semanal()
                if servidor.jornada_trabalho_servidor_pca and not servidor.afastamentos_para_capacitacao_strictu_sensu_hoje.exists():
                    total_jornada_trabalho_pca += int(servidor.jornada_trabalho_servidor_pca)
                total_jornada_maxima += 40
            porcentagens = []
            if total_jornada_maxima:
                porcentagem_total_jornada_trabalho = "{:.2f}".format((float(total_jornada_trabalho) / float(total_jornada_maxima)) * 100)
                porcentagem_total_jornada_trabalho_pca = "{:.2f}".format(
                    (float(total_jornada_trabalho_pca) / float(total_jornada_maxima)) * 100
                )
                porcentagem_total_jornada_trabalho_maxima = "{:.2f}".format(
                    (float(total_jornada_maxima) / float(total_jornada_maxima)) * 100
                )
            else:
                porcentagem_total_jornada_trabalho_maxima = (
                    porcentagem_total_jornada_trabalho_pca
                ) = porcentagem_total_jornada_trabalho = "{:.2f}".format(0)

        else:
            messages.error(request, "Você não pode acessar os dados desse setor.")
    return locals()


##########################
# Carga horária reduzida #
##########################


@csrf_exempt
@rtr()
@login_required()
@group_required("Coordenador de Gestão de Pessoas Sistêmico, Coordenador de Gestão de Pessoas")
def abrir_processo_afastamento_parcial(request, processo_id):
    processo = get_object_or_404(CargaHorariaReduzida, pk=processo_id)
    title = "Processo de Alteração de Carga Horária"

    if request.POST:
        form_afastamento = SalvarProcessoAfastamentoForm(request.POST or None, request=request, processo=processo)

        if request.POST["acao"] == "salvar_ch_excepcional":
            try:
                if processo.horariosemanal_set.all().exists():
                    periodos_validos, periodos_mensagem = processo.validar_periodos_horarios()
                    if periodos_validos:
                        processo.status = CargaHorariaReduzida.STATUS_DEFERIDO_PELO_RH
                        processo.save()
                        return httprr("/admin/rh/cargahorariareduzida/", "Carga horária excepcional cadastrada com sucesso.")
                    else:
                        return httprr(
                            "/rh/abrir_processo_afastamento_parcial/{}/".format(processo.id), message=periodos_mensagem, tag="warning"
                        )
                else:
                    raise Exception("Adicione o horário padrão")
            except Exception as erro:
                return httprr("/rh/abrir_processo_afastamento_parcial/{}/".format(processo.id), str(erro), tag="error")

    else:
        form_afastamento = SalvarProcessoAfastamentoForm(processo=processo)
        arquivos_pendentes_identificar_servidor = processo.documentos.all()

    usuario_logado_eh_rh_sistemico = in_group(request.user, "Coordenador de Gestão de Pessoas Sistêmico")
    grupo_coordenador_rh_campus = in_group(request.user, "Coordenador de Gestão de Pessoas")

    usuario_logado_eh_chefe = request.user.get_profile().id in [chefe.id for chefe in processo.chefe]
    form = DocumentacaoExigidaUploadForm(request=request, processo=processo)
    return locals()


@login_required()
def excluir_processo_afastamento_parcial(request, processo_id):
    processo = CargaHorariaReduzida.objects.get(pk=processo_id)

    # removendo arquivo físico
    arquivos = processo.documentos.all()
    for arquivo in arquivos:
        default_storage.delete(arquivo.diretorio)

    processo.delete()

    return httprr("/admin/rh/cargahorariareduzida/", "Processo excluído com sucesso.")


def get_upload_directory(instance):
    object_id = instance.id
    path = "{}/{}".format(PRIVATE_ROOT_DIR, object_id)
    return path


class FileUploader:
    def __init__(self, backend=None, **kwargs):
        if is_remote_storage():
            self.get_backend = lambda: AWSUploadBackend(**kwargs)
        else:
            self.get_backend = lambda: LocalUploadBackend(**kwargs)

    def __call__(self, request, *args, **kwargs):
        return self._upload(request, *args, **kwargs)

    def _upload(self, request, *args, **kwargs):
        if request.method == "POST":
            if "processo" in request.GET:
                processo_id = request.GET["processo"]
                processo = get_object_or_404(CargaHorariaReduzida, pk=processo_id)
            else:
                return HttpResponse(json.dumps({"success": False, "status": 400}), content_type="application/json")
            # Here, we have something on request.
            # The content_type and content_length variables
            # indicates that.
            if is_ajax(request):
                # the file is stored raw in the request
                upload = request
                is_raw = True
                # Ajax upload will pass the filename in querystring
                try:
                    if "qqfile" in request.GET:
                        filename = request.GET["qqfile"]
                    else:
                        filename = request.REQUEST["qqfilename"]
                #
                except KeyError:
                    return HttpResponse(json.dumps({"success": False}), content_type="application/json")

            else:
                # not an ajax upload, so it was pass via form
                is_raw = False
                if len(request.FILES) == 1:
                    upload = list(request.FILES.values())[0]
                else:
                    return HttpResponse(json.dumps({"success": False}), content_type="application/json")
                filename = upload.name
            content_type = str(request.META.get("CONTENT_TYPE", ""))
            content_length = int(request.META.get("CONTENT_LENGTH", 0))
            if content_type == "" or content_length == 0:
                return HttpResponse(json.dumps({"success": False, "status": 400}), content_type="application/json")

            # Here, we have the filename and file size
            backend = self.get_backend()

            # creating the destination upload directory
            upload_to = get_upload_directory(processo.servidor)
            # configuring the
            new_filename = backend.setup(upload_to, filename)
            # save the file
            success = backend.upload(upload, content_length, is_raw, *args, **kwargs)
            # callback
            uploaded_path = backend.upload_complete(*args, **kwargs)
            if success:
                arquivo_pk = create_on_upload(processo, uploaded_path, filename, content_length)
            else:
                arquivo_pk = None
            # let Ajax Upload know whether we saved it or not
            ret_json = {"success": success, "filename": new_filename, "chave": arquivo_pk, "tamanho": content_length}
            return HttpResponse(json.dumps(ret_json, cls=DjangoJSONEncoder), content_type="text/html; charset=utf-8")

        else:
            response = HttpResponseNotAllowed(["POST"])
            response.write("ERROR: Only POST allowed")
            return response


def create_on_upload(processo, diretorio, nome_do_arquivo, tamanho_arquivo):
    novo_arquivo = DocumentacaoExigida()
    novo_arquivo.processo = processo
    novo_arquivo.diretorio = diretorio
    novo_arquivo.nome = nome_do_arquivo
    novo_arquivo.tamanho = tamanho_arquivo
    novo_arquivo.save()
    return novo_arquivo.encrypted_pk


file_uploaded = Signal()  # providing_args=['backend', 'request']
afastamento_pacial_upload = FileUploader()


@login_required()
def visualizar_documentacao_pdf(request, arquivo_id):
    arquivo = DocumentacaoExigida.objects.get(encrypted_pk=arquivo_id)
    pdf_data = arquivo.diretorio
    return render("viewer.html", locals())


@csrf_exempt
@login_required()
def excluir_documentacao_pdf(request, arquivo_id):
    arquivo = DocumentacaoExigida.objects.get(encrypted_pk=arquivo_id)
    processo = arquivo.processo
    if processo.servidor_pode_editar and processo.servidor_id == request.user.get_relacionamento().id:
        default_storage.delete(arquivo.diretorio)
        arquivo.delete()
        retorno = JsonResponse({"ok": True, "msg": ""})
    else:
        retorno = JsonResponse({"ok": False, "msg": "Você não tem permissão para excluir o arquivo."})
    return retorno


@rtr()
@permission_required(["rh.change_cargahorariareduzida"])
def alterar_situacao_afastamento_parcial_rh(request, processo_id, situacao):
    processo = get_object_or_404(CargaHorariaReduzida, pk=processo_id)

    if not processo.rh_pode_validar():
        raise PermissionDenied("Você não pode validar um processo que ainda não foi enviado ao rh.")

    if situacao == "deferir":
        try:
            if processo.horariosemanal_set.all().exists():
                periodos_validos, periodos_mensagem = processo.validar_periodos_horarios()
                if periodos_validos:
                    processo.status = CargaHorariaReduzida.STATUS_DEFERIDO_PELO_RH
                    processo.servidor_rh_validador = request.user.get_profile().sub_instance()
                    processo.save()

                    """Enviando email para o servidor"""
                    assunto = "[SUAP] Processo de Alteração de Carga Horária"
                    mensagem = '''"Seu processo de alteração de carga horária foi deferido pelo RH "'''
                    if processo.status == CargaHorariaReduzida.STATUS_DEFERIDO_PELO_RH:
                        send_notification(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [processo.servidor.get_vinculo()])
                    return httprr(
                        "/admin/rh/cargahorariareduzida/?tab=tab_processos_validados_rh",
                        "Processo de alteração de carga horária deferido com sucesso.",
                    )
                else:
                    return httprr(
                        "/rh/abrir_processo_afastamento_parcial/{}/".format(processo.id), message=periodos_mensagem, tag="warning"
                    )
            else:
                raise Exception("Adicione seu horário padrão")
        except Exception as erro:
            return httprr("/rh/abrir_processo_afastamento_parcial/{}/".format(processo.id), str(erro), tag="error")

    elif situacao == "indeferir":
        title = "Indeferir Processo de Alteração de Carga Horária"
        form = IndeferirProcessoAfastamentoParcialRHForm(request.POST or None, request=request, instance=processo)
        if form.is_valid():
            form.save()

            """Enviando email para o servidor"""
            assunto = "[SUAP] Processo de Alteração de Carga Horária"
            mensagem = '''"Seu processo de alteração de carga horária foi indeferido pelo RH "'''
            if processo.status == CargaHorariaReduzida.STATUS_INDEFERIDO_PELO_RH:
                send_notification(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [processo.servidor.get_vinculo()])
            return httprr("..", "Processo de alteração de carga horária indeferido com sucesso.")

    return locals()


@rtr()
@permission_required("rh.change_cargahorariareduzida")
def adicionar_horario_afastamento_parcial(request, processo_id):
    title = "Adicionar Horário do Afastamento"
    processo = get_object_or_404(CargaHorariaReduzida, pk=processo_id)
    if not any([processo.servidor_pode_editar(), processo.rh_pode_validar(), processo.tipo_ch_excepcional()]):
        raise PermissionDenied("Você não tem permissão para acessar essa tela.")

    horario_novo = HorarioSemanal()
    horario_novo.processo_afastamento = processo
    form = AdicionarHorarioAfastamentoForm(request.POST or None, request=request, processo=processo)
    if form.is_valid():
        form.save()
        return httprr("..", message="Horário salvo com sucesso.")

    return locals()


@rtr()
@permission_required("rh.change_cargahorariareduzida")
def editar_horario_afastamento(request, horario_id):
    title = "Editar Horário"
    horario = get_object_or_404(HorarioSemanal, pk=horario_id)
    usuario_logado_eh_rh_sistemico = in_group(request.user, "Coordenador de Gestão de Pessoas Sistêmico")
    grupo_coordenador_rh_campus = in_group(request.user, "Coordenador de Gestão de Pessoas")
    if not (
        horario.processo_reducao_ch.tipo_ch_excepcional()
        or horario.processo_reducao_ch.servidor_pode_editar()
        or usuario_logado_eh_rh_sistemico
        or grupo_coordenador_rh_campus
        and horario.processo_reducao_ch.rh_pode_editar_horario
    ):
        raise PermissionDenied("Você não tem permissão de acesso a esta tela.")

    form = EditarHorarioAfastamentoForm(request.POST or None, horario=horario)
    if form.is_valid():
        form.save()
        return httprr("..", message="Horário atualizado com sucesso.")
    return locals()


@permission_required("rh.change_cargahorariareduzida")
def remover_horario_afastamento(request, horario_id):
    horario = get_object_or_404(HorarioSemanal, pk=horario_id)
    if (
        horario.processo_reducao_ch.servidor_pode_editar()
        or horario.processo_reducao_ch.rh_pode_validar()
        or horario.processo_reducao_ch.tipo_ch_excepcional()
    ):
        horario.processo_reducao_ch.status = CargaHorariaReduzida.STATUS_ALTERANDO_HORARIO
        horario.processo_reducao_ch.save()
        horario.delete()
        return httprr("/rh/abrir_processo_afastamento_parcial/{}/".format(horario.processo_reducao_ch.id), "Horário removido com sucesso.")
    else:
        raise PermissionDenied


# -------------------------------------------------------------------------------------------------------------------


@rtr()
@login_required
@permission_required("rh.add_agendaatendimentohorario")
def adicionar_horario(request, acaosaude_id):
    acao_saude = get_object_or_404(AcaoSaude, pk=acaosaude_id)
    title = "Adicionar Horário de Agendamento - {}".format(acao_saude.descricao)

    form = AdicionarHorarioAcaoSaudeForm(request.POST or None, acao_saude=acao_saude)
    if form.is_valid():
        form.save()
        return httprr(".", "Horário cadastrado com sucesso.")

    horarios = AgendaAtendimentoHorario.objects.filter(acao_saude=acao_saude)
    return locals()


@rtr()
@login_required
@permission_required("rh.delete_agendaatendimentohorario")
def remover_horario(request, horario_id):
    horario = get_object_or_404(AgendaAtendimentoHorario, pk=horario_id)
    acao_id = horario.acao_saude.id
    horario.delete()
    return httprr("/rh/adicionar_horario/{}/".format(acao_id), "Horário removido com sucesso.")


@rtr()
@login_required
@permission_required("rh.view_acaosaude")
def acao_saude(request, acao_id):
    acao_saude = get_object_or_404(AcaoSaude, pk=acao_id)
    title = "Visualizar Ação de Saúde - {}".format(acao_saude.descricao)
    hoje = datetime.now()
    servidor_logado = request.user.get_profile().sub_instance()
    pode_cancelar_agendamento = request.user.has_perm("rh.pode_cancelar_agendamento")

    qs_horarioagendado = HorarioAgendado.objects.filter(horario__acao_saude=acao_saude, cancelado=False).order_by("horario__hora_inicio")
    agendamentos_cancelados = HorarioAgendado.objects.filter(horario__acao_saude=acao_saude, cancelado=True)

    # verificando usuários
    pode_ver_agenda_completa = acao_saude.pode_ver_toda_agenda(request.user)
    if not pode_ver_agenda_completa and not acao_saude.eh_profissional_da_acao(servidor_logado):
        qs_horarioagendado = qs_horarioagendado.filter(solicitante=servidor_logado)
        agendamentos_cancelados = agendamentos_cancelados.filter(solicitante=servidor_logado)
        pode_cancelar_agendamento = True  # se só vai ver os próprios agendamentos, também pode cancelá-los

    agenda_dia = qs_horarioagendado.filter(data_consulta=hoje)
    agendados = qs_horarioagendado.filter(data_consulta__gt=hoje)
    agendamentos_passados = qs_horarioagendado.filter(data_consulta__lt=hoje)

    if request.user.has_perm("rh.view_agendaatendimentohorario") and pode_ver_agenda_completa:
        form = AgendarAtendimentoForm(request.POST or None, request=request, acao_saude=acao_saude)
        if form.is_valid():
            horario = form.cleaned_data.get("horario")
            form.save()
            return httprr("/rh/acao_saude/{}/?v={}".format(acao_saude.id, horario.id), "Agendamento cadastrado com sucesso.")

    return locals()


@rtr()
@login_required
@permission_required("rh.view_agendaatendimentohorario")
def agendar_horario(request, horario_id):
    title = "Agendar Atendimento"
    horario = get_object_or_404(AgendaAtendimentoHorario, pk=horario_id)
    form = AgendarAtendimentoForm(request.POST or None, request=request, horario=horario)
    if form.is_valid():
        form.save()
        return httprr("..", "Agendamento cadastrado com sucesso.")
    return locals()


@login_required
def cancelar_agendamento(request, horarioagendado_id):
    try:
        url_retorno = request.META.get("HTTP_REFERER")
        usuario_logado = request.user.get_profile().sub_instance()
        agendamento = HorarioAgendado.objects.filter(pk=horarioagendado_id)
        if request.user.has_perm("rh.pode_cancelar_agendamento") or agendamento.filter(solicitante=usuario_logado).exists():
            agendamento = agendamento[0]
            agendamento.cancelar_horario()
    except ObjectDoesNotExist:
        return httprr(url_retorno, "Você não tem agendamento nesta ação de saúde para cancelar.", "error")
    except MultipleObjectsReturned:
        return httprr(url_retorno, "Erro. Mais de um objeto foi encontrado.", "error")
    except Exception as e:
        return httprr(url_retorno, e, "error")

    return httprr(url_retorno, "Agendamento cancelado com sucesso.")


@rtr()
@permission_required("rh.delete_user")
def sincronizar_ws_siape(request):
    #
    # Sincroniza dados de um serviço específico
    #
    title = "Consulta WebService SIAPE"
    form = WebserviceSIAPEForm(request.POST or None)
    if form.is_valid():
        ws = ImportadorWs()
        result = ws._call_service_siape(form.cleaned_data)
    return locals()


@rtr()
@login_required()
def test_importador_ws(request, cpf):
    importador = ImportadorWs()
    # test = importador.importacao_servidor(mask_numbers(cpf))
    importador.importacao_completa()

    return locals()


@rtr()
@group_required("Servidor")
def atualizar_meus_dados_servidor(request):
    servidor = request.user.get_relacionamento()
    cpf = mask_numbers(request.user.get_profile().cpf)
    try:
        importador = ImportadorWs()
        dados_atualizar = importador.importacao_servidor(mask_numbers(cpf), False, False)
        importador.atualizar_ferias_afastamentos(mask_numbers(cpf), ano_inicio=1990)
        msg = []
        for dados, criado in dados_atualizar:
            msg.append(f'Servidor <a href="{dados.get_absolute_url()}">{dados}</a> {"cadastrado" if criado else "atualizado"} com sucesso.')
        return httprr(servidor.get_absolute_url(), mark_safe(", ".join(msg)))

    except Exception as e:
        return httprr(servidor.get_absolute_url(), e, "error")


@rtr()
@login_required()
@group_required("Coordenador de Gestão de Pessoas Sistêmico, Coordenador de Gestão de Pessoas")
def importar_servidor(request, cpf=None, apenas_servidores_em_exercicio=False):
    title = "Importar/Atualizar dados do servidor"
    try:
        form = ImportarServidorWSForm(request.POST or None)
        # verificando se o usuário pode acessar esta área (apenas RH e superuser)
        if form.is_valid():
            apenas_servidores_em_exercicio = form.cleaned_data.get("apenas_servidores_em_exercicio")
            cpf_form = form.cleaned_data.get("cpf")
            cpf_limpo = mask_numbers(cpf_form)
            importador = ImportadorWs()
            dados_atualizar = importador.importacao_servidor(cpf_limpo, True, apenas_servidores_em_exercicio)  # retornar apenas os dados
            dados_ferias_afastamentos = importador.get_afastamento_historico(cpf_limpo, ano_inicio=1990)  # retornar apenas os dados
            dados_ferias = dados_ferias_afastamentos["ferias"]
            dados_afastamentos = dados_ferias_afastamentos["afastamentos"]

            # dados, criado = importador.importacao_servidor(mask_numbers(cpf))

        # cadastrando ou atualizando o servidor
        if cpf is not None:
            importador = ImportadorWs()
            dados_atualizar = importador.importacao_servidor(mask_numbers(cpf), False, apenas_servidores_em_exercicio)
            importador.atualizar_ferias_afastamentos(mask_numbers(cpf), ano_inicio=1990)
            msg = []
            for dados, criado in dados_atualizar:
                msg.append(
                    f'Servidor <a href="{dados.get_absolute_url()}">{dados}</a> {"cadastrado" if criado else "atualizado"} com sucesso.'
                )
            return httprr("/rh/importar_servidor/", mark_safe(", ".join(msg)))

    except Exception as e:
        return httprr("/rh/importar_servidor/", e, "error")

    return locals()


@rtr()
@permission_required("rh.eh_rh_sistemico")
def relatorio_afastamentos_saude(request):
    title = "Relatório de afastamentos por motivo de saúde"
    form = RelatorioAfastamentosCriticosForm(request.GET or None, request=request)
    if form.is_valid():
        uo = form.cleaned_data.get("uo")
        categoria = form.cleaned_data.get("categoria")
        servidores = (
            Servidor.objects.filter(excluido=False)
            .annotate(
                quantidade_dias=Sum(
                    Case(
                        When(
                            servidorafastamento__afastamento__codigo__in=AfastamentoSiape.LICENCAS_TRATAMENTO_SAUDE,
                            then=F("servidorafastamento__quantidade_dias_afastamento"),
                        ),
                        default=Value(0),
                        output_field=IntegerField(),
                    )
                )
            )
            .filter(quantidade_dias__gte=400)
        )
        if uo:
            servidores = servidores.filter(setor__uo_id=uo)
        if categoria == "tecnico_adminitrativo":
            servidores = servidores.filter(eh_tecnico_adminitrativo=True)
        elif categoria == "docente":
            servidores = servidores.filter(eh_docente=True)

        fields = ("servidor", "setor", "setor.uo", "quantidade_dias")
        sequence = ["servidor", "setor", "setor.uo", "quantidade_dias"]
        table = get_table(request=request, queryset=servidores, fields=fields, sequence=sequence, per_page_field=50)
        if request.GET.get("relatorio", None):
            return tasks.table_export(request.GET.get("relatorio", None), *table.get_params())

    return locals()


@rtr()
@permission_required("rh.eh_rh_sistemico")
def disciplina_ingresso_docentes(request):
    form = DocentesPorDisciplinaFiltroForm(request.GET or None)
    title = "Docentes por Disciplina de Ingresso"
    if not "edu" in settings.INSTALLED_APPS_SUAP:
        return HttpResponse("O módulo de ensino não está instalado no SUAP.")
    docentes_por_disciplina = Servidor.objects.docentes().filter(situacao__codigo=Situacao.ATIVO_PERMANENTE)
    if form.is_valid():
        campus = form.cleaned_data.get("campus")
        disciplinas = form.cleaned_data.get("disciplinas")
        if disciplinas:
            if disciplinas == "1":
                docentes_por_disciplina = docentes_por_disciplina.filter(professor__disciplina__isnull=True)
            elif disciplinas == "2":
                docentes_por_disciplina = docentes_por_disciplina.filter(professor__disciplina__isnull=False)
        if campus:
            docentes_por_disciplina = docentes_por_disciplina.filter(setor__uo=campus)

    custom_fields = dict(
        link_column=LinkColumn(
            "editar_disciplina_docente",
            kwargs={"docente_pk": Accessor("pk")},
            verbose_name="#",
            accessor=Accessor("pk"),
            attrs={"a": {"class": "popup"}},
        ),
        disciplina_ingresso=Column("Disciplina de Ingresso", accessor="disciplina_ingresso", order_by="professor__disciplina"),
        campus=Column("Campus", accessor="campus", order_by="setor__uo"),
    )
    fields = ("matricula", "nome", "setor", "cargo_emprego")
    sequence = ["link_column", "matricula", "nome", "campus", "setor", "cargo_emprego", "disciplina_ingresso"]
    table_docentes_por_disciplina = get_table(
        request=request, queryset=docentes_por_disciplina, fields=fields, sequence=sequence, per_page_field=100, custom_fields=custom_fields
    )
    if request.GET.get("relatorio", None):
        return tasks.table_export(request.GET.get("relatorio", None), *table_docentes_por_disciplina.get_params())
    return locals()


@rtr()
@permission_required("rh.view_setor")
def editar_bases_legais_setor(request, pk):
    setor = get_object_or_404(Setor.todos, pk=pk)
    vinculo = request.user.get_relacionamento()
    eh_chefe_do_setor_hoje = hasattr(vinculo, "eh_chefe_do_setor_hoje") and vinculo.eh_chefe_do_setor_hoje(setor)
    if not eh_chefe_do_setor_hoje:
        raise PermissionDenied

    title = f"Editar Bases Legais do Setor {setor}"
    form = BasesLegaisSetorForm(request.POST or None, instance=setor)
    if form.is_valid():
        form.save()
        return httprr("..", message=f"Bases Legais do Setor {setor} foi atualizada com sucesso.", tag="success", close_popup=True)
    return locals()


@rtr()
@permission_required("rh.view_setor")
def setor(request, pk):
    setor = get_object_or_404(Setor.todos, pk=pk)
    vinculo = request.user.get_relacionamento()
    eh_chefe_do_setor_hoje = hasattr(vinculo, "eh_chefe_do_setor_hoje") and vinculo.eh_chefe_do_setor_hoje(setor)
    title = "{} - {}".format(setor.sigla, setor.nome)
    servidores = Servidor.objects.ativos().filter(setor=setor, cargo_emprego__isnull=False).exclude(
        situacao__codigo__in=Situacao.situacoes_siape_estagiarios()
    ) | Servidor.objects.em_exercicio().filter(setor=setor, cargo_emprego__isnull=False).exclude(
        situacao__codigo__in=Situacao.situacoes_siape_estagiarios()
    )
    estagiarios = Servidor.objects.estagiarios().filter(setor=setor)
    prestadores = PrestadorServico.objects.filter(setor=setor, ativo=True)
    if "ae" in settings.INSTALLED_APPS:
        from ae.models import ParticipacaoTrabalho

        bolsistas = ParticipacaoTrabalho.objects.filter(
            (Q(participacao__data_termino__gte=datetime.today()) | Q(participacao__data_termino__isnull=True))
            & Q(bolsa_concedida__setor=setor)
        )
    filhos = Setor.objects.filter(pk__in=setor.filhos.values_list("pk", flat=True))
    chefes_atuais = Servidor.objects.filter(
        pk__in=ServidorFuncaoHistorico.objects.atuais()
        .filter(setor_suap=setor, funcao__codigo__in=Funcao.get_codigos_funcao_chefia())
        .values_list("servidor", flat=True)
        .distinct()
    )
    funcoes_chefes_atuais = []
    for chefe in chefes_atuais:
        funcoes_chefes_atuais.append(
            dict(servidor=chefe, funcoes=ServidorFuncaoHistorico.objects.atuais().filter(setor_suap=setor, servidor=chefe))
        )
    servidores_com_acesso = Servidor.objects.ativos().filter(setores_adicionais=setor)
    estagiarios_com_acesso = Servidor.objects.estagiarios().filter(setores_adicionais=setor)
    prestadores_com_acesso = PrestadorServico.objects.filter(setores_adicionais=setor, ativo=True)

    servidores_inativos = ServidorSetorHistorico.objects.filter(setor=setor, data_fim_no_setor__isnull=False).order_by(
        "-data_inicio_no_setor"
    )

    return locals()


@rtr()
@permission_required("rh.view_setor")
def setor_detalhes(request, setor_pk):
    setor = get_object_or_404(Setor.todos, pk=setor_pk)
    vinculo = request.user.get_relacionamento()
    eh_chefe_do_setor_hoje = hasattr(vinculo, "eh_chefe_do_setor_hoje") and vinculo.eh_chefe_do_setor_hoje(setor)
    servidores = Servidor.objects.ativos().filter(setor=setor, cargo_emprego__isnull=False).exclude(
        situacao__codigo__in=Situacao.situacoes_siape_estagiarios()
    ) | Servidor.objects.em_exercicio().filter(setor=setor, cargo_emprego__isnull=False).exclude(
        situacao__codigo__in=Situacao.situacoes_siape_estagiarios()
    )
    estagiarios = Servidor.objects.estagiarios().filter(setor=setor)
    prestadores = PrestadorServico.objects.filter(setor=setor, ativo=True)
    if "ae" in settings.INSTALLED_APPS:
        from ae.models import ParticipacaoTrabalho

        bolsistas = ParticipacaoTrabalho.objects.filter(
            (Q(participacao__data_termino__gte=datetime.today()) | Q(participacao__data_termino__isnull=True))
            & Q(bolsa_concedida__setor=setor)
        )
    filhos = Setor.objects.filter(pk__in=setor.filhos.values_list("pk", flat=True))
    chefes_atuais = Servidor.objects.filter(
        pk__in=ServidorFuncaoHistorico.objects.atuais()
        .filter(setor_suap=setor, funcao__codigo__in=Funcao.get_codigos_funcao_chefia())
        .values_list("servidor", flat=True)
        .distinct()
    )
    funcoes_chefes_atuais = []
    for chefe in chefes_atuais:
        funcoes_chefes_atuais.append(
            dict(servidor=chefe, funcoes=ServidorFuncaoHistorico.objects.atuais().filter(setor_suap=setor, servidor=chefe))
        )
    servidores_com_acesso = Servidor.objects.ativos().filter(setores_adicionais=setor)
    estagiarios_com_acesso = Servidor.objects.estagiarios().filter(setores_adicionais=setor)
    prestadores_com_acesso = PrestadorServico.objects.filter(setores_adicionais=setor, ativo=True)
    return locals()


@rtr()
@permission_required("rh.view_setor")
def organograma(request):
    title = "Organograma"
    FormClass = SetorRaizFormFactory(request)
    form = FormClass(request.POST or None)
    if form.is_valid():
        setor_raiz = form.cleaned_data["raiz"].pk
    return locals()


@permission_required("rh.view_setor")
def organograma_data(request):
    servidor_logado = request.user.get_relacionamento()
    setor_raiz = servidor_logado.setor
    setor_raiz_form = request.GET.get("setor_raiz")
    if setor_raiz_form:
        setor_raiz = Setor.objects.get(pk=int(setor_raiz_form))

    dataset = []
    nodes = []
    width_calc = setor_raiz.filhos.count() * 100
    width = width_calc if width_calc >= 1000 else 1000
    # for setor in setor_raiz.filhos | Setor.objects.filter(pk=setor_raiz.pk):
    for setor in setor_raiz.filhos | Setor.objects.filter(pk=setor_raiz.pk):
        nodes.append(
            {
                "id": setor.sigla,
                "name": "<span onclick=\"preencher_setor('/rh/setor_detalhes/{}/')\">{}</span>".format(setor.pk, setor.sigla),
                "image": setor.chefes.all().first().get_foto_75x100_url() if setor.chefes.all().first() else "",
            }
        )
        if setor.superior and not setor.excluido:
            dataset.append([setor.superior.sigla, setor.sigla])

    levels = [
        {"level": 0, "color": "#3498db", "colorText": "white"},
        {"level": 1, "color": "#95a5a6"},
        {"level": 2, "color": "#7f8c8d"},
        {"level": 3, "color": "#bdc3c7"},
        {"level": 4, "layout": "hanging", "color": "silver"},
    ]
    chart = {
        "chart": {"type": "organization", "inverted": True, "width": width, "height": 400},
        "title": {"useHTML": True, "text": "Organograma {}".format(setor_raiz)},
        "tooltip": False,
        "series": [
            {
                "name": Configuracao.get_valor_por_chave("comum", "instituicao_sigla"),
                "keys": ["from", "to"],
                "data": dataset,
                "levels": levels,
                "nodes": nodes,
                "colorByPoint": False,
            }
        ],
        "xAxis": {"scrollbar": {"enabled": True}},
    }
    return JsonResponse(chart)


@rtr()
@permission_required("rh.eh_rh_sistemico")
def editar_servidor_cargo_emprego_area(request, servidor_pk):
    servidor = get_object_or_404(Servidor, pk=servidor_pk)
    title = f"Editar Área do Cargo Emprego do servidor: {servidor}"
    form = EditarServidorCargoEmpregoAreaForm(request.POST or None, instance=servidor)
    if form.is_valid():
        form.save()
        return httprr("..", message=f"Área do Cargo Emprego de {servidor} foi atualizada com sucesso.", tag="success", close_popup=True)
    return locals()


@rtr()
@permission_required("rh.eh_rh_sistemico")
def servidores_por_area(request):
    form = ServidoresPorAreaFiltroForm(request.GET or None)
    title = "Servidores por Área"
    servidores_por_area = Servidor.objects.ativos().filter(cargo_emprego__cargoempregoarea__isnull=False).distinct()
    if form.is_valid():
        campus = form.cleaned_data.get("campus")
        cargo_emprego = form.cleaned_data.get("cargo_emprego")
        cargo_emprego_area = form.cleaned_data.get("cargo_emprego_area")
        com_area_cadastrada = form.cleaned_data.get("com_area_cadastrada")
        if com_area_cadastrada:
            if com_area_cadastrada == "1":
                servidores_por_area = servidores_por_area.filter(cargo_emprego_area__isnull=False)
            elif com_area_cadastrada == "2":
                servidores_por_area = servidores_por_area.filter(cargo_emprego_area__isnull=True)
        if cargo_emprego:
            servidores_por_area = servidores_por_area.filter(cargo_emprego=cargo_emprego)
        if cargo_emprego_area:
            servidores_por_area = servidores_por_area.filter(cargo_emprego_area=cargo_emprego_area)
        if campus:
            servidores_por_area = servidores_por_area.filter(setor__uo=campus)

    custom_fields = dict(
        link_column=LinkColumn(
            "editar_servidor_cargo_emprego_area",
            kwargs={"servidor_pk": Accessor("pk")},
            verbose_name="#",
            accessor=Accessor("pk"),
            attrs={"a": {"class": "popup"}},
        ),
        campus=Column("Campus", accessor="campus", order_by="setor__uo"),
    )
    fields = ("matricula", "nome", "setor", "cargo_emprego", "cargo_emprego_area")
    sequence = ["link_column", "matricula", "nome", "campus", "setor", "cargo_emprego", "cargo_emprego_area"]
    table_servidores_por_area = get_table(
        request=request, queryset=servidores_por_area, fields=fields, sequence=sequence, per_page_field=100, custom_fields=custom_fields
    )
    if request.GET.get("relatorio", None):
        return tasks.table_export(request.GET.get("relatorio", None), *table_servidores_por_area.get_params())
    return locals()


@login_required()
def arquivo_unico(request, hash_sha512_link_id):
    try:
        try:
            arquivo_unico = ArquivoUnico.objects.get(hash_sha512_link_id=hash_sha512_link_id)
            response = HttpResponse(content=arquivo_unico.get_conteudo_as_bytes(), content_type=arquivo_unico.tipo_conteudo)

            filename = request.GET.get("filename")
            if filename:
                filename = retira_acentos(filename.replace(" ", ""))
                response["Content-Disposition"] = "inline; filename={};".format(filename)
            else:
                response["Content-Disposition"] = "inline;"

            return response
        except ArquivoUnico.DoesNotExist:
            raise Http404("O arquivo solicitado não existe.")
    except Exception as e:
        msg_error = "Erro ao tentar obter o arquivo."
        if settings.DEBUG:
            msg_error += " Detalhes: {}".format(e)
        raise Http404(msg_error)


@rtr()
@permission_required("rh.view_solicitacaoalteracaofoto")
def validaralteracaofoto(request, solicitacao_id):
    try:
        solicitacao = get_object_or_404(SolicitacaoAlteracaoFoto, pk=solicitacao_id)
        solicitacao.validar(request.user)
        return httprr('/admin/rh/solicitacaoalteracaofoto/', 'Solicitação validada com sucesso.')
    except Exception as ex:
        return httprr('/admin/rh/solicitacaoalteracaofoto/', ex)


@rtr()
@permission_required("rh.view_solicitacaoalteracaofoto")
def rejeitaralteracaofoto(request, solicitacao_id):
    try:
        solicitacao = get_object_or_404(SolicitacaoAlteracaoFoto, pk=solicitacao_id)
        form = RejeitarSolicitacaoAlteracaoFotoForm(request.POST or None, instance=solicitacao)
        if form.is_valid():
            form.processar(request)
            return httprr('/admin/rh/solicitacaoalteracaofoto/', 'Solicitação rejeitada.', close_popup=True)
        return locals()
    except Exception as ex:
        return httprr('/admin/rh/solicitacaoalteracaofoto/', ex, close_popup=True)


@rtr()
@login_required()
@permission_required("rh.view_solicitacaoalteracaofoto")
def detalhe_solicitacao_alteracao_foto(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoAlteracaoFoto, pk=solicitacao_id)
    title = f"Solicitação de Alteração de Foto #{solicitacao.id}"
    return locals()


@rtr()
@permission_required("rh.change_dados_bancarios")
def adicionardadobancariopessoa_fisica(request, pessoa_fisica_id, dado_bancario_pk=None):
    pessoa_fisica = get_object_or_404(PessoaFisica.objects, pk=pessoa_fisica_id)
    dados_bancarios = dado_bancario_pk and DadosBancariosPF.objects.get(pk=dado_bancario_pk) or None

    is_proprio_pf = pessoa_fisica.is_user(request)
    pode_ver_dados_bancarios = is_proprio_pf or request.user.has_perm('rh.pode_ver_dados_bancarios')
    if not pode_ver_dados_bancarios:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    title = "{} Dados Bancários".format(dado_bancario_pk and "Atualizar" or "Adicionar")
    form = AdicionarDadosBancariosPFForm(pessoa_fisica, data=request.POST or None, request=request, instance=dados_bancarios)
    if form.is_valid():
        o = form.save(False)
        o.banco = form.cleaned_data.get('instituicao').nome
        o.atualizado_por = request.user.get_vinculo()
        o.atualizado_em = datetime.datetime.now()
        o.save()
        return httprr('..', 'Dados bancários {} com sucesso.'.format(dado_bancario_pk and "atualizado" or "adicionado"))
    return locals()
