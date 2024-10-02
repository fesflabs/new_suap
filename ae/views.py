import calendar
import collections
import datetime
import hashlib
import operator
import os
import zipfile
from collections import OrderedDict
from datetime import date, timedelta
from decimal import Decimal
from functools import reduce
from os import stat
from os.path import exists
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import connection, transaction
from django.db.models import FloatField
from django.db.models import Q, F
from django.db.models import Sum, Count
from django.db.models.expressions import Value
from django.db.models.functions import Cast, Coalesce
from django.db.utils import IntegrityError
from django.forms.models import inlineformset_factory
from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from django_tables2 import Column
from django_tables2.columns.datecolumn import DateColumn
from django_tables2.columns.linkcolumn import LinkColumn
from django_tables2.utils import Accessor
from sentry_sdk import capture_exception

from ae import tasks as ae_tasks
from ae.forms import (
    InscricaoFormFactory,
    InscricaoDetalhamentoAlimentacaoForm,
    InscricaoDetalhamentoIdiomaForm,
    InscricaoDetalhamentoTrabalhoFormFactory,
    InscricaoDetalhamentoPasseEstudantilFormFactory,
    CaracterizacaoForm,
    DemandaAlunoAtendidaForm,
    RevogarParticipacaoForm,
    ParticipacaoBolsaModelForm,
    RelatorioSemanalRefeitorioForm,
    EstatisticasCaracterizacaoForm,
    RendimentoCaracterizacaoForm,
    BuscarAlunoForm,
    GerenciarParticipacaoBuscaForm,
    ParticipacaoFormFactory,
    AlunosProgramaForm,
    RelatorioFinanceiroForm,
    GraficoAtendimentoForm,
    RelatorioFinanceiroBolsasForm,
    RelatorioAtendimentoForm,
    RelatorioBolsasForm,
    ListaAtendidosAuxiliosForm,
    ParecerInscricaoForm,
    SolicitacaoRefeicaoAlunoForm,
    JustificaFaltaRefeicaoForm,
    LiberaParticipacaoAlimentacaoForm,
    FolhaPagamentoForm,
    RelatorioAlunosAptosForm,
    DataEntregaDocumentacaoForm,
    EditarParticipacaoForm,
    DashboardForm,
    TipoRefeicaoForm,
    RelatorioPlanejamentoForm,
    AgendamentoDesbloqueioParticipacaoForm,
    RelatorioDiarioRefeitorioForm,
    RelatorioAlunoRendimentoFrequenciaForm,
    RelatorioPNAESForm,
    CampusForm,
    PerguntaInscricaoProgramaForm,
    PerguntaParticipacaoForm,
    DocumentacaoInscricaoForm,
    DocumentacaoComprovRendaInscricaoForm,
    AtualizaDocumentoAlunoForm,
    AdicionarDocumentoAlunoForm,
    GerarFolhaPagamentoForm,
    RelatorioFinanceiroAuxiliosForm,
    ListaAtendimentoRefeicoesForm,
    IntegranteFamiliarCaracterizacaoForm,
    EditarPerguntaParticipacaoForm,
    AvaliarSolicitacaoAuxilioForm,
    EstatisticaInscricoesForm,
    ImportarCaracterizacaoForm,
    RelatorioDemandaReprimidaForm,
    AdicionarDadoBancarioForm,
    IntegranteFamiliarCaracterizacaoBaseFormSet,
)
from ae.models import (
    AtendimentoSetor,
    AgendamentoRefeicao,
    CategoriaAlimentacao,
    CategoriaBolsa,
    InscricaoCaracterizacao,
    IntegranteFamiliarCaracterizacao,
    PassesChoices,
    DemandaAluno,
    InscricaoAlimentacao,
    Programa,
    SolicitacaoAlimentacao,
    InscricaoIdioma,
    InscricaoTrabalho,
    InscricaoPasseEstudantil,
    Inscricao,
    Caracterizacao,
    OfertaTurma,
    OfertaBolsa,
    DemandaAlunoAtendida,
    Participacao,
    ParticipacaoBolsa,
    ValorTotalAuxilios,
    OfertaValorRefeicao,
    OfertaPasse,
    ParticipacaoPasseEstudantil,
    ValorTotalBolsas,
    ParticipacaoTrabalho,
    OfertaValorBolsa,
    OfertaAlimentacao,
    ParticipacaoAlimentacao,
    SolicitacaoRefeicaoAluno,
    HorarioSolicitacaoRefeicao,
    TipoRefeicao,
    HistoricoSuspensoesAlimentacao,
    HistoricoFaltasAlimentacao,
    DatasLiberadasFaltasAlimentacao,
    AtividadeDiversa,
    AcaoEducativa,
    ParticipacaoIdioma,
    TipoAtendimentoSetor,
    HorarioJustificativaFalta,
    DatasRecessoFerias,
    PeriodoInscricao,
    PerguntaInscricaoPrograma,
    RespostaInscricaoPrograma,
    OpcaoRespostaInscricaoPrograma,
    PerguntaParticipacao,
    OpcaoRespostaPerguntaParticipacao,
    RespostaParticipacao,
    DocumentoInscricaoAluno,
    RelatorioGrafico,
    Edital,
    SolicitacaoAuxilioAluno,
    HistoricoCaracterizacao,
    DadosBancarios
)
from ae.relatorio_gestao import (
    obter_relatorio_atendimentos,
    obter_relatorio_auxilios,
    obter_relatorio_bolsas,
    obter_relatorio_programas,
    obter_relatorio_saude,
    obter_dados_resumo,
    obter_relatorio_grafico,
)
from comum.models import Configuracao, Ano
from comum.utils import get_uo, get_topo_pdf, get_table, get_sigla_reitoria, somar_data
from djtools import layout, tasks
from djtools import pdf
from djtools.choices import DiaSemanaChoices
from djtools.db import models
from djtools.html.graficos import PieChart, LineChart, GroupedColumnChart, BarChart
from djtools.templatetags.filters import format_, in_group
from djtools.utils import rtr, httprr, permission_required, XlsResponse, get_client_ip, get_real_sql, send_notification, \
    get_session_cache
from djtools.utils.response import PDFResponse
from edu.models import Aluno, CursoCampus as Curso, Modalidade, SituacaoMatriculaPeriodo, Convenio, MatriculaPeriodo
from ponto.models import Maquina, VersaoTerminal
from rh.models import UnidadeOrganizacional, Funcionario


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()

    if request.user.eh_aluno:
        aluno = request.user.get_relacionamento()
        uo = aluno.curso_campus.diretoria.setor.uo
        programas = Programa.objects.filter(publico_alvo=uo)
        periodos = PeriodoInscricao.objects.filter(
            data_inicio__lte=datetime.datetime.today(), data_termino__gte=datetime.datetime.today(), campus__in=programas.values_list('instituicao', flat=True), edital__ativo=True
        )

        if periodos.exists() and aluno.situacao.ativo:
            for periodo in periodos:
                for programa in periodo.programa.filter(publico_alvo=uo):
                    if (periodo.apenas_participantes and aluno.eh_participante_do_programa(programa)) or not periodo.apenas_participantes:
                        inscricoes.append(
                            dict(
                                url=f'/ae/inscricao_caracterizacao/{aluno.pk}/{periodo.id}/{programa.id}/',
                                titulo=f'Inscrever-se em: <strong>{programa}</strong>',
                                prazo=periodo.data_termino.strftime('%d/%m/%Y %H:%M'),
                            )
                        )
    return inscricoes


@layout.alerta()
def index_alertas(request):
    alertas = list()

    sub_instance = request.user.get_relacionamento()
    if request.user.eh_aluno:
        aluno = request.user.get_relacionamento()
        if SolicitacaoRefeicaoAluno.objects.filter(deferida=True, aluno=sub_instance, ativa=True, data_auxilio__startswith=date.today()).exists():
            alertas.append(dict(url=f'/edu/aluno/{sub_instance.matricula}/?tab=atividades_estudantis', titulo='Você tem refeição agendada hoje.'))

        # caracterização econômica
        # removido alunos de minicurso (FIC-)
        if not Caracterizacao.objects.filter(aluno=aluno).exists() and not aluno.eh_aluno_minicurso():
            alertas.append(dict(url='/ae/caracterizacao/', titulo='Responda ao questionário de Caracterização Socioeconômica.'))

    elif request.user.eh_servidor or request.user.eh_prestador:
        if request.user.groups.filter(name__in=['Assistente Social', 'Coordenador de Atividades Estudantis Sistêmico', 'Gerente de Refeições']).exists():
            hoje = datetime.datetime.now()
            uo = sub_instance.setor.uo
            if hoje.weekday() not in (5, 6) and not OfertaAlimentacao.objects.filter(campus=uo, dia_inicio__lte=hoje.date(), dia_termino__gte=hoje.date()).exists():
                alertas.append(dict(url='/admin/ae/ofertaalimentacao/', titulo='Não há <strong>oferta de alimentação</strong> cadastrada para hoje.'))
        if request.user.has_perm('ae.pode_abrir_inscricao_do_campus'):
            if SolicitacaoAuxilioAluno.objects.filter(data_avaliacao__isnull=True, aluno__curso_campus__diretoria__setor__uo=get_uo(request.user)).exists():
                alertas.append(dict(url='/admin/ae/solicitacaoauxilioaluno/', titulo='<strong>Solicitações de auxílios eventuais</strong> pendentes de avaliação.'))

    return alertas


@layout.quadro('Serviço Social', icone='graduation-cap')
def index_quadros(quadro, request):
    def do():
        sub_instance = request.user.get_relacionamento()
        if request.user.eh_aluno:
            if sub_instance.situacao.ativo:
                programa = Programa.objects.filter(tipo=Programa.TIPO_ALIMENTACAO, instituicao=sub_instance.curso_campus.diretoria.setor.uo)
                if programa.exists():
                    programa_refeicao = programa[0].id
                    if not programa[0].impedir_solicitacao_beneficio:
                        quadro.add_item(
                            layout.ItemAcessoRapido(titulo='Solicitar Refeição', icone='plus', url=f'/ae/solicitar_refeicao/{programa_refeicao:d}/', classe='success')
                        )
                quadro.add_item(layout.ItemAcessoRapido(titulo='Solicitar Auxílio Eventual', icone='plus', url='/admin/ae/solicitacaoauxilioaluno/add/', classe='success'))

            quadro.add_item(layout.ItemAcessoRapido(titulo='Registro de Atividades', icone='bars', url=f'{sub_instance.get_absolute_url()}?tab=atividades_estudantis'))

            if Participacao.abertas.filter(aluno=sub_instance, participacaoalimentacao__isnull=False).exists():
                part_programa_alim = Participacao.abertas.filter(aluno=sub_instance, participacaoalimentacao__isnull=False)[0]
                if part_programa_alim:
                    quadro.add_item(
                        layout.ItemAcessoRapido(
                            titulo='Informar Falta em Participação de Alimentação',
                            icone='info',
                            url=f'/ae/justificar_falta/{sub_instance.id:d}/{part_programa_alim.programa.id:d}/',
                        )
                    )

        else:
            if request.user.groups.filter(name__in=['Assistente Social', 'Coordenador de Atividades Estudantis Sistêmico']).exists():
                programas = Programa.objects.filter(instituicao=get_uo(request.user))
                for programa in programas:
                    quadro.add_item(
                        layout.ItemAcessoRapido(titulo=f'<strong>Programa:</strong> {programa.tipo_programa.titulo}', url=f'ae/programa/{programa.pk:d}/')
                    )

            if request.user.groups.filter(name__in=['Assistente Social', 'Coordenador de Atividades Estudantis Sistêmico', 'Gerente de Refeições']).exists():
                hoje = datetime.datetime.now()
                uo = sub_instance.setor.uo
                programa = Programa.objects.filter(instituicao=uo)
                programa_alm = participacoes_suspensas_alm = None
                if programa.filter(tipo_programa__sigla=Programa.TIPO_ALIMENTACAO).exists():
                    programa_alm = programa.filter(tipo_programa__sigla=Programa.TIPO_ALIMENTACAO).first()
                if programa_alm:
                    participacoes_suspensas_alm = ParticipacaoAlimentacao.objects.filter(participacao__programa=programa_alm, suspensa=True).filter(
                        Q(participacao__data_termino__isnull=True) | Q(participacao__data_termino__gte=hoje)
                    )
                if participacoes_suspensas_alm:
                    qtd = participacoes_suspensas_alm.count()
                    quadro.add_item(
                        layout.ItemContador(
                            titulo='Participaç{} de Alimentação'.format(pluralize(qtd, 'ão,ões')),
                            subtitulo=f'Suspensa{pluralize(qtd)}',
                            qtd=qtd,
                            url=f'/ae/liberar_participacao_alimentacao/{programa_alm.id}/',
                        )
                    )

        return quadro

    return get_session_cache(request, 'index_servico_social', do, 24 * 3600)


# verifica se o usuário que tem a permissão de ver somente dados do câmpus está num programa do câmpus dele
def verificar_permissao_programa(request, programa):
    return programa.instituicao == get_uo(request.user) or request.user.is_superuser or request.user.has_perm('ae.pode_ver_relatorios_todos')


# -----------------------------------------------------------------------------
# Views relacionadas ao programa e seu gerenciamento --------------------------
# -----------------------------------------------------------------------------
@rtr()
@permission_required('ae.view_programa')
def programa(request, programa_id):
    box_title = 'Participantes'
    complemento_titulo = ''
    programa = get_object_or_404(Programa, pk=programa_id)

    title = f'Programa: {programa.titulo}'

    hoje = date.today()
    inicio_semana = hoje - timedelta(hoje.weekday())
    fim_semana = inicio_semana + timedelta(4)
    if programa.get_tipo() == Programa.TIPO_ALIMENTACAO:
        complemento_titulo = f'Semanal ({format_(inicio_semana)} a {format_(fim_semana)})'
    if not verificar_permissao_programa(request, programa):
        raise PermissionDenied()

    if request.user.groups.filter(name='Nutricionista').exists():
        is_nutricionista = True
        if programa.get_tipo() != Programa.TIPO_ALIMENTACAO:
            return httprr("/admin/ae/programa/", "Você não tem permissão para acessar esse programa.", tag="error")

    if not programa.estah_configurado():
        return httprr('/', 'A configuração de oferta para esse programa ainda não foi realizada. Favor, acesse o menu Serviço Social > Ofertas.', tag='error')

    # Trata as inscrições importadas que devem ser categorizadas na oferta de alimentação.
    # Esse trecho de código deve ser removido após a categoriazação
    if request.method == 'POST' and 'participaca_id' in request.POST:
        participacao = get_object_or_404(Participacao, pk=request.POST['participaca_id'])
        categoria = get_object_or_404(CategoriaAlimentacao, pk=request.POST['categoria_id'])

        participacao = participacao.sub_instance()
        participacao.categoria = categoria
        participacao.save()

        messages.info(request, 'Categoria definida com sucesso.')

    # Controle da paginação dos participantes
    query = request.GET.get('query', '')

    # Inscritos deve ser entendidos como os participantes ativos do programa
    inscritos = programa.get_participacoes_abertas()
    participacoes_futuras = programa.get_participacoes_futuras()
    if programa.get_tipo() == Programa.TIPO_ALIMENTACAO:
        form = GerenciarParticipacaoBuscaForm(request.GET, alimentacao=True)
    else:
        form = GerenciarParticipacaoBuscaForm(request.GET, alimentacao=False)

    if form.is_valid():
        if 'matricula_nome' in request.GET:
            query = form.cleaned_data.get('matricula_nome')
            if query:
                inscritos = inscritos.filter(Q(aluno__matricula__icontains=query) | Q(aluno__pessoa_fisica__nome__icontains=query))

        if 'situacao' in request.GET:
            query = form.cleaned_data.get('situacao')
            if query == 'Ativo':
                inscritos = inscritos.filter(aluno__situacao__ativo=True)
            elif query == 'Inativo':
                inscritos = inscritos.filter(aluno__situacao__ativo=False)

        if 'categoria' in request.GET:
            categoria = form.cleaned_data.get('categoria')
            if categoria:
                participacoes_por_categoria = ParticipacaoAlimentacao.objects.filter(categoria=categoria).values_list('participacao', flat=True)
                inscritos = inscritos.filter(id__in=participacoes_por_categoria)

        if 'documentacao_expirada' in request.GET:
            query = form.cleaned_data.get('documentacao_expirada')
            if query == True:
                prazo_expiracao = Configuracao.get_valor_por_chave('ae', 'prazo_expiracao_documentacao')
                total_dias = prazo_expiracao and int(prazo_expiracao) or 365
                inscritos = inscritos.filter(aluno__data_documentacao__lt=somar_data(datetime.datetime.now(), -total_dias)).distinct()

    disponibilidade = programa.get_disponibilidade(inicio_semana)

    return locals()


# Gerenciamento das participações em programas --------------------------------
@rtr()
@permission_required('ae.change_programa')
def gerenciar_participacao(request, programa_id):
    title = 'Gerenciar Participações'
    box_title = 'Resultado da Pesquisa'

    programa = get_object_or_404(Programa, pk=programa_id)

    url = f'/ae/gerenciar_participacao/{programa_id}/'

    if not verificar_permissao_programa(request, programa):
        raise PermissionDenied()

    if request.user.groups.filter(name='Nutricionista').exists():
        is_nutricionista = True

    inscritos = Inscricao.ativas.filter(programa=programa, aluno__caracterizacao__isnull=False, aluno__documentada=True).order_by('-data_cadastro')

    if programa.get_tipo() == Programa.TIPO_ALIMENTACAO:
        form = GerenciarParticipacaoBuscaForm(request.GET, alimentacao=True)
    else:
        form = GerenciarParticipacaoBuscaForm(request.GET, alimentacao=False)

    hoje = date.today()
    inicio_semana = hoje - timedelta(hoje.weekday())
    fim_semana = inicio_semana + timedelta(4)

    if form.is_valid():
        if 'matricula_nome' in request.GET:
            query = form.cleaned_data.get('matricula_nome')
            if query:
                inscritos = inscritos.filter(Q(aluno__matricula__icontains=query) | Q(aluno__pessoa_fisica__nome__icontains=query))
        if 'situacao' in request.GET:
            query = form.cleaned_data.get('situacao')
            if query == 'Ativo':
                inscritos = inscritos.filter(aluno__situacao__ativo=True)
            elif query == 'Inativo':
                inscritos = inscritos.filter(aluno__situacao__ativo=False)

        if 'categoria' in request.GET:
            categoria = form.cleaned_data.get('categoria')
            if categoria:
                participacoes_por_categoria = ParticipacaoAlimentacao.objects.filter(
                    Q(categoria=categoria), Q(participacao__data_termino__isnull=True) | Q(participacao__data_termino__gte=hoje)
                ).values_list('participacao__inscricao', flat=True)
                inscritos = inscritos.filter(id__in=participacoes_por_categoria)

        if 'documentacao_expirada' in request.GET:
            query = form.cleaned_data.get('documentacao_expirada')
            if query == True:
                prazo_expiracao = Configuracao.get_valor_por_chave('ae', 'prazo_expiracao_documentacao')
                total_dias = prazo_expiracao and int(prazo_expiracao) or 365
                inscritos = inscritos.filter(aluno__data_documentacao__lt=somar_data(datetime.datetime.now(), -total_dias)).distinct()

    disponibilidade = programa.get_disponibilidade(inicio_semana)

    if programa.get_tipo() == Programa.TIPO_TRANSPORTE:
        passes = PassesChoices.PASSES_CHOICES
    elif programa.get_tipo() == Programa.TIPO_IDIOMA:
        turmas = OfertaTurma.objects.filter(ativa=True, campus=programa.instituicao)
    elif programa.get_tipo() == Programa.TIPO_TRABALHO:
        bolsas = OfertaBolsa.objects.filter(disponivel=True, setor__uo=programa.instituicao, campus=programa.instituicao)

        # caso a oferta seja de reitoria verificar o campus que admnistra a vaga
        bolsas_RE = OfertaBolsa.objects.filter(disponivel=True, setor__uo__sigla=get_sigla_reitoria(), campus=programa.instituicao)
        bolsas = bolsas | bolsas_RE

    return locals()


@rtr()
@permission_required('ae.pode_editar_participacao')
def adicionar_participacao(request, programa_id, inscricao_id):
    title = 'Adicionar Participação'

    programa = get_object_or_404(Programa, pk=programa_id)
    inscricao = get_object_or_404(Inscricao, pk=inscricao_id)
    aluno = inscricao.aluno

    if not aluno.documentada:
        return httprr(request.META.get('HTTP_REFERER', '..'), 'A inclusão no programa só poderá ser realizada caso a documentação tenha sido entregue.', tag='error')

    if not inscricao.ativa:
        return httprr(request.META.get('HTTP_REFERER', '..'), 'A inclusão no programa só poderá ser realizada caso a inscrição esteja ativa.', tag='error')

    if not hasattr(aluno, 'caracterizacao') or (hasattr(aluno, 'caracterizacao') and not aluno.caracterizacao):
        return httprr(request.META.get('HTTP_REFERER', '..'), 'A inclusão no programa só poderá ser realizada caso o aluno possua caracterização.', tag='error')

    if programa.tipo_programa.sigla:
        form = ParticipacaoFormFactory(request.POST or None, programa=programa, inscricao=inscricao, request=request)

        if request.method == 'POST':
            if form.is_valid():
                form.save()
                return httprr('..', 'Participação adicionada com sucesso.')
    else:
        form = PerguntaParticipacaoForm(request.POST or None, programa=programa)

        if request.method == 'POST':
            if form.is_valid():
                participacao = Participacao()
                participacao.programa = programa
                participacao.aluno = inscricao.aluno
                participacao.inscricao = inscricao
                participacao.atualizado_por = request.user.get_vinculo()
                participacao.atualizado_em = datetime.datetime.now()
                participacao.data_inicio = form.cleaned_data.get('data_inicio')
                participacao.motivo_entrada = form.cleaned_data.get('motivo_entrada')
                participacao.save()
                chaves = list(request.POST.keys())
                for item in chaves:
                    valores = request.POST.getlist(item)
                    if 'pergunta_' in item:
                        id = item.split('_')[1]
                        pergunta_respondida = get_object_or_404(PerguntaParticipacao, pk=id)
                        for valor in valores:
                            resposta_informada = get_object_or_404(OpcaoRespostaPerguntaParticipacao, pk=int(valor))
                            if PerguntaParticipacao.objects.filter(id=id, ativo=True).exists():
                                o = RespostaParticipacao()
                                o.participacao = participacao
                                o.pergunta = pergunta_respondida
                                o.resposta = resposta_informada
                                o.save()

                    elif 'texto_' in item:
                        id = item.split('_')[1]
                        valor_informado = valores[0]
                        pergunta_respondida = get_object_or_404(PerguntaParticipacao, pk=id)
                        if pergunta_respondida.tipo_resposta == PerguntaParticipacao.NUMERO:
                            valor_informado = valor_informado.replace('.', '').replace(',', '.')
                        o = RespostaParticipacao()
                        o.participacao = participacao
                        o.pergunta = pergunta_respondida
                        o.valor_informado = valor_informado
                        o.save()

                return httprr('..', 'Participação adicionada com sucesso.')
    return locals()


@rtr()
@permission_required('ae.pode_editar_participacao')
def corrigir_participacao(request, participacao_id):
    title = 'Corrigir Participação'
    participacao_original = get_object_or_404(Participacao, pk=participacao_id)
    participacao = participacao_original.sub_instance()

    if participacao_original.programa.tipo_programa.sigla:
        form = ParticipacaoFormFactory(request.POST or None, instance=participacao)
    else:
        form = PerguntaParticipacaoForm(request.POST or None, programa=participacao.programa, instance=participacao)
    if request.method == 'POST':
        if form.is_valid():
            if participacao_original.programa.tipo_programa.sigla:
                form.save()
            else:
                respostas_previas = RespostaParticipacao.objects.filter(pergunta__tipo_programa=participacao.programa.tipo_programa, participacao=participacao)
                ids_respostas_atuais = list()
                participacao.data_inicio = form.cleaned_data.get('data_inicio')
                participacao.motivo_entrada = form.cleaned_data.get('motivo_entrada')
                participacao.save()
                chaves = list(request.POST.keys())
                for item in chaves:
                    valores = request.POST.getlist(item)

                    if 'pergunta_' in item:
                        id = item.split('_')[1]
                        pergunta_respondida = get_object_or_404(PerguntaParticipacao, pk=id)
                        for valor in valores:
                            resposta_informada = get_object_or_404(OpcaoRespostaPerguntaParticipacao, pk=int(valor))
                            if PerguntaParticipacao.objects.filter(id=id, ativo=True).exists():
                                if respostas_previas.filter(pergunta=pergunta_respondida, resposta=resposta_informada).exists():
                                    o = RespostaParticipacao.objects.filter(pergunta=pergunta_respondida, participacao=participacao, resposta__isnull=False)[0]
                                else:
                                    o = RespostaParticipacao()
                                    o.participacao = participacao
                                    o.pergunta = pergunta_respondida
                                o.resposta = resposta_informada
                                o.save()
                                ids_respostas_atuais.append(o.id)

                    elif 'texto_' in item:

                        id = item.split('_')[1]
                        valor_informado = valores[0]
                        pergunta_respondida = get_object_or_404(PerguntaParticipacao, pk=id)
                        if pergunta_respondida.tipo_resposta == PerguntaParticipacao.NUMERO:
                            valor_informado = valor_informado.replace('.', '').replace(',', '.')
                        if RespostaParticipacao.objects.filter(pergunta=pergunta_respondida, participacao=participacao).exists():
                            o = RespostaParticipacao.objects.filter(pergunta=pergunta_respondida, participacao=participacao)[0]
                        else:
                            o = RespostaParticipacao()
                            o.participacao = participacao
                            o.pergunta = pergunta_respondida
                        o.valor_informado = valor_informado
                        o.save()
                        ids_respostas_atuais.append(o.id)

                respostas_previas.exclude(id__in=ids_respostas_atuais).delete()

            return httprr('..', 'Participação corrigida com sucesso.')
    return locals()


@rtr()
@transaction.atomic
@permission_required('ae.pode_revogar_participacao')
def revogar_participacao(request, participacao_id):
    title = 'Finalizar Participação'

    participacao = get_object_or_404(Participacao, pk=participacao_id)
    form = RevogarParticipacaoForm(data=request.POST or None, instance=participacao)

    if request.method == 'POST':
        if form.is_valid():
            if participacao.programa.get_tipo() == Programa.TIPO_TRABALHO and participacao.participacaotrabalho.bolsa_concedida is None:
                return httprr(
                    '..', 'É necessário adicionar uma bolsa a esta participação antes de removê-la. Acesse o link de Corrigir, em Gerenciar Participações.', tag='warning'
                )
            elif participacao.programa.get_tipo() == Programa.TIPO_IDIOMA and participacao.participacaoidioma.turma_selecionada is None:
                return httprr(
                    '..', 'É necessário adicionar uma turma a esta participação antes de removê-la. Acesse o link de Corrigir, em Gerenciar Participações.', tag='warning'
                )
            elif participacao.programa.get_tipo() == Programa.TIPO_ALIMENTACAO:
                if (
                    participacao.participacaoalimentacao.solicitacao_atendida_cafe.valida() is False
                    and participacao.participacaoalimentacao.solicitacao_atendida_almoco.valida() is False
                    and participacao.participacaoalimentacao.solicitacao_atendida_janta.valida() is False
                ):
                    return httprr(
                        '..', 'É necessário adicionar uma refeição esta participação antes de removê-la. Acesse o link de Corrigir, em Gerenciar Participações.', tag='warning'
                    )

                if participacao.participacaoalimentacao.suspensa:
                    titulo = '[SUAP] Programa de Alimentação: Participação Finalizada'
                    texto = (
                        '<h1>Serviço Social</h1>'
                        '<h2>Sua participação foi finalizada.</h2>'
                        '<p>Devido à sua suspensão no programa de Alimentação por motivo de faltas não justificadas, sua participação no programa foi finalizada.</p>'
                        '<p>Procure o setor de Serviço Social do seu campus para mais informações.</p>'
                    )
                    send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [participacao.aluno.get_vinculo()])

            elif participacao.programa.get_tipo() == Programa.TIPO_TRANSPORTE and participacao.participacaopasseestudantil.tipo_passe_concedido is None:
                return httprr(
                    '..', 'É necessário adicionar um tipo de passe a esta participação antes de removê-la. Acesse o link de Corrigir, em Gerenciar Participações.', tag='warning'
                )
            o = form.save(False)
            o.finalizado_por = request.user.get_vinculo()
            o.finalizado_em = datetime.datetime.now()
            o.save()
            return httprr(
                '..',
                mark_safe('Participação finalizada com sucesso. <a href="/ae/adicionar_participacao/{}/{}/" class="popup">Adicionar Nova Participação</a> para este aluno.'.format(
                    participacao.programa.id, participacao.inscricao.id
                )),
            )
    return locals()


@rtr()
@permission_required('ae.pode_detalhar_programa_todos, ae.pode_detalhar_programa_do_campus')
def folha_pagamento(request, programa_id):
    programa = get_object_or_404(Programa, pk=programa_id)
    title = f'Folha de Pagamento - {programa.tipo_programa} ({programa.instituicao})'
    oferta_do_mes = None
    form = FolhaPagamentoForm(request.GET or None, programa=programa)
    if form.is_valid():
        ano = form.cleaned_data.get('ano')
        mes = form.cleaned_data.get('mes')
        ver_nome = form.cleaned_data['ver_nome']
        ver_matricula = form.cleaned_data['ver_matricula']
        ver_cpf = form.cleaned_data['ver_cpf']
        ver_banco = form.cleaned_data['ver_banco']
        ver_agencia = form.cleaned_data['ver_agencia']
        ver_operacao = form.cleaned_data['ver_operacao']
        ver_conta = form.cleaned_data['ver_conta']
        ver_tipo_passe = form.cleaned_data['ver_tipo_passe']
        ver_valor_padrao = form.cleaned_data['ver_valor_padrao']
        ver_valor_pagar = form.cleaned_data['ver_valor_pagar']
        total_escolhido = len(form.changed_data) - 2

        data_inicio = datetime.datetime(ano.ano, int(mes), 1).date()
        if int(mes) == 12:
            data_termino = datetime.datetime(ano.ano + 1, 1, 1).date()
        else:
            data_termino = datetime.datetime(ano.ano, int(mes) + 1, 1).date()

        if programa.get_tipo() == Programa.TIPO_TRANSPORTE:
            participantes = Participacao.objects.filter(participacaopasseestudantil__isnull=False, participacaopasseestudantil__valor_concedido__isnull=False)
        elif programa.get_tipo() == Programa.TIPO_TRABALHO:
            participantes = Participacao.objects.filter(participacaotrabalho__isnull=False)
        else:
            participantes = Participacao.objects.filter(programa=programa)
        participantes = participantes.filter(aluno__curso_campus__diretoria__setor__uo=programa.instituicao).order_by('aluno', 'data_inicio')
        participantes = participantes.filter(Q(data_termino__gt=data_inicio, data_inicio__lt=data_termino) | Q(data_termino__isnull=True, data_inicio__lt=data_termino))
        lista = list()

        total = 0
        decricao_dias_abonados = None
        if programa.get_tipo() == Programa.TIPO_TRANSPORTE:
            dias_do_mes = 22
            dias_abonados_geral = DatasRecessoFerias.objects.filter(data__gte=data_inicio, data__lt=data_termino, campus=programa.instituicao).exclude(data__week_day__in=[1, 7])
            decricao_dias_abonados = [dia.data.day for dia in dias_abonados_geral.order_by('data')]
            for item in participantes:
                dias_abonados = dias_abonados_geral.filter(data__gte=item.data_inicio)
                diferenca = None
                if item.data_termino:
                    dias_abonados = dias_abonados.filter(data__lt=item.data_termino)
                qtd_dias_abonados = dias_abonados.count()
                valor = item.sub_instance().valor_concedido
                if valor:
                    if item.data_inicio > data_inicio and item.data_inicio.month == int(mes):
                        fromdate = item.data_inicio
                        todate = data_termino
                        daygenerator = (fromdate + timedelta(x + 1) for x in range((todate - fromdate).days))
                        diferenca = sum(1 for day in daygenerator if day.weekday() < 5)

                        if diferenca > dias_do_mes:
                            diferenca_em_dias = dias_do_mes - qtd_dias_abonados
                        else:
                            diferenca_em_dias = diferenca - qtd_dias_abonados
                        if diferenca_em_dias < 0:
                            diferenca_em_dias = 0
                        valor = Decimal((valor / dias_do_mes) * diferenca_em_dias).quantize(Decimal(10) ** -2)
                    if item.data_termino and item.data_termino < data_termino and item.data_termino.month == int(mes):
                        fromdate = data_inicio
                        todate = item.data_termino
                        daygenerator = (fromdate + timedelta(x + 1) for x in range((todate - fromdate).days))
                        diferenca = sum(1 for day in daygenerator if day.weekday() < 5)
                        if diferenca > dias_do_mes:
                            diferenca_em_dias = dias_do_mes - qtd_dias_abonados
                        else:
                            diferenca_em_dias = diferenca - qtd_dias_abonados
                        if diferenca_em_dias < 0:
                            diferenca_em_dias = 0
                        valor = Decimal((valor / dias_do_mes) * diferenca_em_dias).quantize(Decimal(10) ** -2)
                    if not diferenca:
                        if qtd_dias_abonados > dias_do_mes:
                            qtd_dias_abonados = dias_do_mes
                        valor = ((dias_do_mes - qtd_dias_abonados) * valor) / dias_do_mes
                    total += valor
                    lista.append((item, valor))

        elif programa.get_tipo() == Programa.TIPO_TRABALHO:
            dias_do_mes = 30
            ofertas = OfertaValorBolsa.objects.filter(data_inicio__lte=data_termino, data_termino__gte=data_inicio, campus=programa.instituicao)
            if ofertas.exists():
                oferta_do_mes = ofertas[0].valor
                for item in participantes:
                    valor = ofertas[0].valor
                    if item.data_inicio > data_inicio and item.data_inicio.month == int(mes):
                        diferenca = data_termino - item.data_inicio
                        valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)
                    if item.data_termino and item.data_termino < data_termino and item.data_termino.month == int(mes):
                        diferenca = item.data_termino - data_inicio
                        valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)
                    total += valor
                    lista.append((item, valor))
            else:
                return httprr(f'/ae/folha_pagamento/{programa.id}/', 'Não existe Valor de Bolsa cadastrada para este mês.', tag='warning')
        else:
            dias_do_mes = 30
            for item in participantes:
                if RespostaParticipacao.objects.filter(
                    pergunta__eh_info_financeira=True, pergunta__ativo=True, pergunta__tipo_resposta=PerguntaParticipacao.NUMERO, participacao=item
                ).exists():
                    valor = (
                        RespostaParticipacao.objects.filter(
                            pergunta__eh_info_financeira=True, pergunta__ativo=True, pergunta__tipo_resposta=PerguntaParticipacao.NUMERO, participacao=item
                        )
                        .annotate(soma=Cast('valor_informado', FloatField()))
                        .aggregate(Sum('soma'))['soma__sum']
                    )
                    if item.data_inicio > data_inicio and item.data_inicio.month == int(mes):
                        diferenca = data_termino - item.data_inicio
                        valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)
                    if item.data_termino and item.data_termino < data_termino and item.data_termino.month == int(mes):
                        diferenca = item.data_termino - data_inicio
                        valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)
                    total += Decimal(valor)
                    lista.append((item, valor))

    if 'xls' in request.GET:
        return folha_pagamento_to_xls(
            request,
            programa.get_tipo(),
            oferta_do_mes,
            lista,
            ver_nome,
            ver_matricula,
            ver_cpf,
            ver_banco,
            ver_agencia,
            ver_operacao,
            ver_conta,
            ver_tipo_passe,
            ver_valor_padrao,
            ver_valor_pagar,
            total,
        )

    return locals()


@permission_required('ae.pode_detalhar_programa_todos, ae.pode_detalhar_programa_do_campus')
def folha_pagamento_to_xls(
    request,
    tipo_programa,
    oferta_do_mes,
    lista,
    ver_nome,
    ver_matricula,
    ver_cpf,
    ver_banco,
    ver_agencia,
    ver_operacao,
    ver_conta,
    ver_tipo_passe,
    ver_valor_padrao,
    ver_valor_pagar,
    total,
):
    return ae_tasks.exportar_folha_pagamento_xls(
        tipo_programa,
        oferta_do_mes,
        lista,
        ver_nome,
        ver_matricula,
        ver_cpf,
        ver_banco,
        ver_agencia,
        ver_operacao,
        ver_conta,
        ver_tipo_passe,
        ver_valor_padrao,
        ver_valor_pagar,
        total,
    )


# Ações relacionadas a inscrição ----------------------------------------------
@rtr()
@permission_required('ae.pode_ver_comprovante_inscricao')
def comprovante_inscricao(request, inscricao_id):
    title = "Comprovante de Inscrição"
    inscricao = get_object_or_404(Inscricao, pk=inscricao_id)
    respostas = None
    if not inscricao.programa.get_tipo():
        respostas = inscricao.get_respostas_inscricao()

    if InscricaoCaracterizacao.objects.filter(aluno__pk=inscricao.aluno_id).exists():
        inscricao_caracterizacao = inscricao.aluno.inscricaocaracterizacao_set.latest('id')
        if inscricao_caracterizacao.integrantefamiliarcaracterizacao_set.exists():
            integrantes_familiares = inscricao_caracterizacao.integrantefamiliarcaracterizacao_set.all()
        elif IntegranteFamiliarCaracterizacao.objects.filter(id_inscricao=inscricao_caracterizacao.id).exists():
            integrantes_familiares = IntegranteFamiliarCaracterizacao.objects.filter(id_inscricao=inscricao_caracterizacao.id)
        else:
            integrantes_familiares = IntegranteFamiliarCaracterizacao.objects.filter(aluno=inscricao.aluno).distinct('nome')

    return locals()


@rtr()
@permission_required('ae.save_caracterizacao_todos, ae.save_caracterizacao_do_campus, edu.pode_editar_caracterizacao')
def caracterizacao(request, aluno_id=None, renovacao_matricula=None):
    """
    Foi criada outra url - /ae/caracterizacao/ - sem o id do aluno para que apareça o menu
    "Atividades Estudantis". O id do aluno é recuperado durante o login.
    """

    # Caso exista caracterização mostrar editar com os dados
    # Caso contrário mostrar formulário

    title = "Caracterização Social"

    aluno = None
    aluno_logado = False

    if aluno_id:
        aluno = get_object_or_404(Aluno, pk=aluno_id)
    else:
        aluno = get_object_or_404(Aluno, matricula=request.user.username)
        aluno_logado = True

    if request.user.eh_aluno and aluno and request.user.get_relacionamento() != aluno:
        raise PermissionDenied()

    if not request.user.has_perm('ae.save_caracterizacao_todos'):
        if request.user.has_perm('ae.save_caracterizacao_do_campus') and aluno.curso_campus.diretoria.setor.uo != get_uo(request.user):
            raise PermissionDenied()
        else:  # se for o próprio aluno logado
            if hasattr(aluno, 'caracterizacao') or aluno_logado:
                if not request.user.has_perm('ae.change_caracterizacao') and not request.user == aluno.pessoa_fisica.user:
                    raise PermissionDenied()

    form = CaracterizacaoForm(aluno, data=request.POST or None)

    if Caracterizacao.objects.filter(aluno=aluno).exists():
        title = "Editar Caracterização Social"
        form = CaracterizacaoForm(aluno, instance=aluno.caracterizacao, data=request.POST or None)

    if request.method == 'POST':
        if form.is_valid():
            caracterizacao = form.save(False)
            caracterizacao.aluno = aluno
            caracterizacao.informado_por = request.user.get_vinculo()
            if Caracterizacao.objects.filter(id=caracterizacao.id).exists():
                registro_atual = Caracterizacao.objects.get(id=caracterizacao.id)
                if (
                    registro_atual.qtd_pessoas_domicilio != form.cleaned_data.get('qtd_pessoas_domicilio')
                    or registro_atual.companhia_domiciliar != form.cleaned_data.get('companhia_domiciliar')
                    or registro_atual.responsavel_financeir_trabalho_situacao != form.cleaned_data.get('responsavel_financeir_trabalho_situacao')
                    or registro_atual.renda_bruta_familiar != form.cleaned_data.get('renda_bruta_familiar')
                ):
                    IntegranteFamiliarCaracterizacao.objects.filter(aluno=aluno).update(inscricao_caracterizacao=None)
            caracterizacao.save()
            form.save_m2m()
            if renovacao_matricula:
                request.session['caracterizacao_atualizada'] = True
                request.session.save()
                if aluno.is_credito():
                    url = f'/edu/pedido_matricula_credito/{aluno.pk}/'
                else:
                    url = f'/edu/pedido_matricula_seriado/{aluno.pk}/'
            else:
                url = aluno.get_absolute_url()
            return httprr(url, 'Caracterização realizada com sucesso.')
    return locals()


@rtr()
@permission_required('ae.pode_ver_relatorios_todos, ae.pode_ver_relatorios_campus')
def estatisticas(request):
    title = 'Total de Inscrições'
    form = EstatisticaInscricoesForm(request.POST or None)
    if form.is_valid():
        campus = None
        if request.user.has_perm('ae.pode_ver_relatorios_todos'):
            campi = UnidadeOrganizacional.objects.uo().all()
            if 'campus' in request.POST and request.POST['campus']:
                campus = int(request.POST['campus'])
        elif request.user.has_perm('ae.pode_ver_relatorios_campus'):
            campus = get_uo(request.user).id

        inscricoes = Inscricao.objects.all()
        if form.cleaned_data.get('documentacao'):
            prazo_expiracao = Configuracao.get_valor_por_chave('ae', 'prazo_expiracao_documentacao')
            total_dias = prazo_expiracao and int(prazo_expiracao) or 365
            data = somar_data(datetime.datetime.now(), -total_dias)
            if form.cleaned_data.get('documentacao') == EstatisticaInscricoesForm.EM_DIA:
                inscricoes = inscricoes.filter(aluno__documentada=True, aluno__data_documentacao__gte=data)
            elif form.cleaned_data.get('documentacao') == EstatisticaInscricoesForm.NAO_ENTEGUE:
                inscricoes = inscricoes.filter(aluno__documentada=False)
            elif form.cleaned_data.get('documentacao') == EstatisticaInscricoesForm.EXPIRADA:
                inscricoes = inscricoes.filter(aluno__data_documentacao__lt=data)

        # grafico 1
        dados = list()
        groups = []
        series1 = Programa.objects.values_list('tipo_programa__titulo').annotate(qtd=models.Count('tipo_programa__titulo')).order_by('tipo_programa__titulo')
        if campus:
            series1 = series1.filter(instituicao=campus)
        for s in series1:
            dados.append([s[0], s[1]])
            groups.append(s[0])

        grafico1 = PieChart('grafico1', title='Programas', subtitle='Total de programas', minPointLength=0, data=dados)

        # grafico 2
        anos = (
            inscricoes.extra({'year': "EXTRACT(YEAR FROM data_cadastro)"})
            .values_list('year')
            .annotate(total_item=models.Count('data_cadastro'))
            .values_list('year', flat=True)
            .order_by('year')
        )

        if campus:
            anos = anos.filter(programa__instituicao=campus).values_list('year', flat=True).order_by('year')
        series2 = []
        for ano in anos:
            serie = [f'Ano {int(ano)}']
            dados = (
                inscricoes.filter(data_cadastro__year=ano)
                .values_list('programa__tipo_programa__titulo')
                .annotate(qtd=Count('programa__tipo_programa__titulo'))
                .order_by('programa__tipo_programa__titulo')
            )
            if campus:
                dados = dados.filter(programa__instituicao=campus)
            dict_dados = dict(dados)

            for grupo in groups:
                if grupo in dict_dados.keys():
                    for registro in dados:
                        if grupo == registro[0]:
                            serie.append(registro[1])
                else:
                    serie.append(0)
            series2.append(serie)

        grafico2 = LineChart(
            'grafico2', title='Inscrições por Ano', data=series2, groups=groups, plotOptions_line_dataLabels_enable=True, plotOptions_line_enableMouseTracking=True
        )

        # grafico 3
        if campus:
            campi_ids = [campus]
        else:
            campi_ids = (
                inscricoes.values_list('aluno__curso_campus__diretoria__setor__uo__nome')
                .annotate(qtd=models.Count('aluno__curso_campus__diretoria__setor__uo'))
                .values_list('aluno__curso_campus__diretoria__setor__uo', flat=True)
                .order_by('aluno__curso_campus__diretoria__setor__uo__nome')
            )
        series3 = []
        for campus_id in campi_ids:
            serie = [UnidadeOrganizacional.objects.uo().get(id=campus_id).sigla]
            dados = dict(
                inscricoes.filter(programa__instituicao=campus_id)
                .values_list('programa__tipo_programa__titulo')
                .annotate(qtd=models.Count('programa__tipo_programa__titulo'))
                .order_by('programa__tipo_programa__titulo')
            )

            for grupo in groups:
                serie.append(dados.get(grupo))
            series3.append(serie)

        grafico3 = GroupedColumnChart(
            'grafico3', title='Total de Inscrições', data=series3, groups=groups, plotOptions_line_dataLabels_enable=True, plotOptions_line_enableMouseTracking=True
        )

    return locals()


@rtr()
@permission_required('ae.pode_ver_motivo_solicitacao')
def inscricao_identificacao(request):
    title = 'Efetuar Inscrição em Programa'
    programas = Programa.objects.all()
    if not request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
        programas = programas.filter(instituicao=get_uo(request.user))

    Form = InscricaoFormFactory(request, programas)
    if request.method == 'POST':
        form = Form(data=request.POST)
        if form.is_valid():
            programa = form.cleaned_data['programa']
            programa_id = programa.id

            aluno = form.cleaned_data['aluno']
            data = form.cleaned_data['data_cadastro']
            edital = form.cleaned_data['edital']

            if PeriodoInscricao.objects.filter(programa=programa, edital=edital).exists():
                periodo = PeriodoInscricao.objects.filter(programa=programa, edital=edital).order_by('-data_termino')[0]
                return httprr("/ae/inscricao_caracterizacao/{}/{}/{}/{}".format(aluno.id, periodo.id, programa_id, data.strftime('%Y%m%d%H%M')))
            else:
                return httprr("/ae/inscricao_identificacao/", 'Não existe nenhum Período de Inscrição do Edital selecionado para este Programa.', tag='error')
    else:
        form = Form()

    return locals()


@rtr(two_factor_authentication=True)
@login_required
def inscricao_caracterizacao(request, aluno_id, periodo_id, programa_id, data_cadastro=date.today().strftime('%Y%m%d%H%M')):
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    programa = get_object_or_404(Programa, pk=programa_id)
    periodo_escolhido = get_object_or_404(PeriodoInscricao, pk=periodo_id)
    title = f'Inscrição para {programa}: Caracterização Socioeconômica'
    eh_aluno = request.user.get_profile().aluno_edu_set.exists()
    if eh_aluno:
        if aluno not in request.user.get_profile().aluno_edu_set.all():
            raise PermissionDenied()

    if not request.user.has_perm('ae.save_caracterizacao_todos'):
        if request.user.has_perm('ae.save_caracterizacao_do_campus') and aluno.curso_campus.diretoria.setor.uo != get_uo(request.user):
            raise PermissionDenied()
        else:  # se for o próprio aluno logado
            if hasattr(aluno, 'caracterizacao'):
                if not request.user.has_perm('ae.change_caracterizacao') and not request.user == aluno.pessoa_fisica.user:
                    raise PermissionDenied()

    form = CaracterizacaoForm(aluno, data=request.POST or None, inscricao_caracterizacao=True)
    if hasattr(aluno, 'caracterizacao'):
        form = CaracterizacaoForm(aluno, instance=aluno.caracterizacao, data=request.POST or None, inscricao_caracterizacao=True)

    if request.method == 'POST':
        if form.is_valid():
            caracterizacao = form.save(False)
            caracterizacao.aluno = aluno
            caracterizacao.informado_por = request.user.get_vinculo()
            if Caracterizacao.objects.filter(id=caracterizacao.id).exists():
                registro_atual = Caracterizacao.objects.get(id=caracterizacao.id)
                if (
                    registro_atual.qtd_pessoas_domicilio != form.cleaned_data.get('qtd_pessoas_domicilio')
                    or registro_atual.companhia_domiciliar != form.cleaned_data.get('companhia_domiciliar')
                    or registro_atual.responsavel_financeir_trabalho_situacao != form.cleaned_data.get('responsavel_financeir_trabalho_situacao')
                    or registro_atual.renda_bruta_familiar != form.cleaned_data.get('renda_bruta_familiar')
                    or form.cleaned_data.get('qtd_pessoas_domicilio') != IntegranteFamiliarCaracterizacao.objects.filter(aluno=aluno).count() - 1
                ):
                    # integrantes_extras = IntegranteFamiliarCaracterizacao.objects.filter(aluno=aluno).order_by('-data')[form.cleaned_data.get('qtd_pessoas_domicilio')-1:]
                    # IntegranteFamiliarCaracterizacao.objects.filter(id__in=integrantes_extras).delete()
                    integrantes_extras = IntegranteFamiliarCaracterizacao.objects.filter(aluno=aluno).order_by('-data')[form.cleaned_data.get('qtd_pessoas_domicilio') - 1:]
                    IntegranteFamiliarCaracterizacao.objects.filter(id__in=integrantes_extras.values_list('id', flat=True)).update(inscricao_caracterizacao=None)
                    # IntegranteFamiliarCaracterizacao.objects.filter(aluno=aluno).update(inscricao_caracterizacao=None)
            caracterizacao.save()
            form.save_m2m()

            return httprr(f'/ae/inscricao_grupo_familiar/{aluno_id}/{periodo_id}/{programa_id}/{data_cadastro}/', 'Preencha os dados socioeconômicos da sua inscrição.')
    return locals()


# @cache_control(no_cache=True, must_revalidate=True, no_store=True) # https://blog.ionelmc.ro/2011/03/17/stale-formsets-and-the-back-button/
@rtr()
@login_required
def inscricao_grupo_familiar(request, aluno_id, periodo_id, programa_id, data_cadastro):
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    programa = get_object_or_404(Programa, pk=programa_id)
    periodo_escolhido = get_object_or_404(PeriodoInscricao, pk=periodo_id)
    if periodo_escolhido.apenas_participantes and not aluno.eh_participante_do_programa(programa):
        return httprr('/', 'Apenas participantes do programa podem realizar inscrição.', tag='error')
    eh_aluno = request.user.get_profile().aluno_edu_set.exists()

    title = f'Inscrição para {programa}: Caracterização do Grupo Familiar'
    campus_do_aluno = aluno.curso_campus.diretoria.setor.uo
    periodos_permitidos = PeriodoInscricao.objects.filter(
        programa__publico_alvo=campus_do_aluno, data_termino__gte=datetime.datetime.today(), programa__pk=programa_id, edital__ativo=True
    )
    if eh_aluno:
        if request.user != aluno.pessoa_fisica.user or not periodos_permitidos.exists() or not (campus_do_aluno.id in programa.publico_alvo.values_list('id', flat=True)):
            raise PermissionDenied()
        if int(periodo_id) not in periodos_permitidos.values_list('id', flat=True):
            return httprr('/', 'Período de inscrição inválido.', tag='error')

    if not hasattr(aluno, 'caracterizacao') or (hasattr(aluno, 'caracterizacao') and not aluno.caracterizacao):
        if eh_aluno:
            return httprr(f'/ae/inscricao_caracterizacao/{aluno_id}/{periodo_id}/{programa_id}/{data_cadastro}/', 'Por favor, efetue sua caracterização social antes de se inscrever no programa.', tag='error')
        else:
            return httprr('/', 'O aluno precisa efetuar a caracterização social antes de ser inscrito no programa.', tag='error')

    qtd_pessoas_domicilio = aluno.caracterizacao.qtd_pessoas_domicilio
    registros_composicao = qtd_pessoas_domicilio - 1

    inscricao_caracterizacao = None
    if InscricaoCaracterizacao.objects.filter(aluno_id=aluno_id).exists():
        inscricao_caracterizacao = InscricaoCaracterizacao.objects.get(aluno_id=aluno_id)
        if not request.POST:
            for registro in IntegranteFamiliarCaracterizacao.objects.filter(inscricao_caracterizacao=inscricao_caracterizacao):
                if registro.remuneracao is not None:
                    registro.ultima_remuneracao = registro.remuneracao
                    registro.save()
            IntegranteFamiliarCaracterizacao.objects.filter(inscricao_caracterizacao=inscricao_caracterizacao).update(remuneracao=None)

    form = RendimentoCaracterizacaoForm(request.POST or None, instance=inscricao_caracterizacao)

    formset = None
    if registros_composicao:
        IntegranteFamiliarCaracterizacaoFormSet = inlineformset_factory(
            InscricaoCaracterizacao,
            IntegranteFamiliarCaracterizacao,
            form=IntegranteFamiliarCaracterizacaoForm,
            formset=IntegranteFamiliarCaracterizacaoBaseFormSet,
            exclude=('idade', 'ultima_remuneracao', 'aluno', 'id_inscricao'),
            max_num=registros_composicao,
            min_num=registros_composicao,
            can_delete=False,
        )
        formset = IntegranteFamiliarCaracterizacaoFormSet(request.POST or None, request.FILES or None, instance=inscricao_caracterizacao, aluno=aluno)

    renda_bruta_informada = Decimal(0.00)
    if form.is_valid():
        if formset:
            if formset.is_valid():
                for item in formset.cleaned_data:
                    if (
                        not 'nome' in item
                        or not 'parentesco' in item
                        or not 'estado_civil' in item
                        or not 'situacao_trabalho' in item
                        or not 'remuneracao' in item
                        or not 'data_nascimento' in item
                    ):
                        return httprr(
                            f"/ae/inscricao_grupo_familiar/{aluno_id}/{periodo_id}/{programa_id}/{data_cadastro}/", 'Informe os dados de todas as pessoas do domicílio.', tag='error'
                        )
                    else:
                        if not item.get('DELETE'):
                            renda_bruta_informada = renda_bruta_informada + Decimal(item['remuneracao'])

            else:
                if 'A quantidade de integrantes tem que ser igual a da caracterização.' in formset.non_form_errors():
                    recarregar_pagina = True

                return locals()

        renda_bruta_informada = renda_bruta_informada + Decimal(form.cleaned_data.get('remuneracao_trabalho'))
        aluno.caracterizacao.renda_bruta_familiar = renda_bruta_informada
        aluno.caracterizacao.informado_por = request.user.get_vinculo()
        aluno.caracterizacao.save()
        form.instance.aluno = aluno
        form.instance.save()
        if registros_composicao:
            formset.instance = form.instance
            formset.save()

        return httprr(f"/ae/inscricao_documentacao/{aluno_id}/{periodo_id}/{programa_id}/{data_cadastro}/")

    return locals()


@rtr()
@login_required
def inscricao_documentacao(request, aluno_id, periodo_id, programa_id, data_cadastro):
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    periodo_escolhido = get_object_or_404(PeriodoInscricao, pk=periodo_id)
    programa = get_object_or_404(Programa, pk=programa_id)
    if periodo_escolhido.apenas_participantes and not aluno.eh_participante_do_programa(programa):
        return httprr('/', 'Apenas participantes do programa podem realizar inscrição.', tag='error')
    eh_aluno = request.user.get_profile().aluno_edu_set.exists()

    title = f'Inscrição para {programa}: Documentação'
    eh_aluno = request.user.get_profile().aluno_edu_set.exists()
    periodos_permitidos = PeriodoInscricao.objects.filter(
        programa__publico_alvo=aluno.curso_campus.diretoria.setor.uo, data_termino__gte=datetime.datetime.today(), programa__pk=programa_id, edital__ativo=True
    )
    if eh_aluno:
        if request.user != aluno.pessoa_fisica.user or not periodos_permitidos.exists():
            raise PermissionDenied()

    edital = periodo_escolhido.edital

    documentacao_do_aluno = DocumentoInscricaoAluno.objects.filter(aluno=aluno)
    prazo_expira = date.today() + relativedelta(months=-12)
    comprov_resid_valido = documentacao_do_aluno.filter(tipo_arquivo=DocumentoInscricaoAluno.COMPROVANTE_RESIDENCIA,
                                                        data_cadastro__gte=prazo_expira, integrante_familiar__isnull=True)
    maior_dezoito_anos = date.today() + relativedelta(years=-18)
    falta_comprovante_renda = False
    precisa_comprovante_renda_aluno = aluno.pessoa_fisica.nascimento_data <= maior_dezoito_anos
    comprovante_renda_aluno = documentacao_do_aluno.filter(tipo_arquivo=DocumentoInscricaoAluno.COMPROVANTE_RENDA,
                                                           data_cadastro__gte=prazo_expira, integrante_familiar__isnull=True)
    form = DocumentacaoInscricaoForm(
        request.POST or None, request.FILES or None, comprov_resid_valido=comprov_resid_valido, comprovante_renda_aluno=comprovante_renda_aluno, precisa_comprovante_renda_aluno=precisa_comprovante_renda_aluno
    )

    integrantes = IntegranteFamiliarCaracterizacao.objects.filter(data_nascimento__lte=maior_dezoito_anos, inscricao_caracterizacao__aluno=aluno)

    ids_integrantes = list()
    for item in integrantes:
        if not DocumentoInscricaoAluno.objects.filter(aluno=aluno, integrante_familiar=item,
                                                      data_cadastro__gte=prazo_expira).exists():
            falta_comprovante_renda = True
            ids_integrantes.append(item.id)
        elif (
                not IntegranteFamiliarCaracterizacao.objects.filter(pk=item.pk,
                                                                    data_nascimento__lte=maior_dezoito_anos).exists()
                or not IntegranteFamiliarCaracterizacao.objects.filter(pk=item.pk, remuneracao__exact=F(
                    'ultima_remuneracao')).exists()
        ):
            falta_comprovante_renda = True
            ids_integrantes.append(item.id)

    if (
        (not (aluno.data_documentacao and not aluno.is_documentacao_expirada()))
        or falta_comprovante_renda
        or not DocumentoInscricaoAluno.objects.filter(aluno=aluno).exists()
        or DocumentoInscricaoAluno.objects.filter(aluno=aluno, data_cadastro__lt=prazo_expira).exists()
        or precisa_comprovante_renda_aluno
    ):

        integrantes = integrantes.filter(id__in=ids_integrantes)
        form_comprovantes = DocumentacaoComprovRendaInscricaoForm(request.POST or None, request.FILES or None, integrantes=integrantes)
        if form.is_valid() and form_comprovantes.is_valid():
            if form.cleaned_data.get('comprovante_residencia'):
                documentacao = documentacao_do_aluno.filter(tipo_arquivo=DocumentoInscricaoAluno.COMPROVANTE_RESIDENCIA,
                                                            data_cadastro__gte=prazo_expira,
                                                            integrante_familiar__isnull=True)
                if documentacao.exists():
                    nova_documentacao = documentacao.last()
                else:
                    nova_documentacao = DocumentoInscricaoAluno()
                    nova_documentacao.aluno = aluno
                    nova_documentacao.tipo_arquivo = DocumentoInscricaoAluno.COMPROVANTE_RESIDENCIA

                arquivo = form.cleaned_data.get('comprovante_residencia')
                if nova_documentacao.arquivo != arquivo:
                    filename = hashlib.md5(f'{request.user.pessoafisica.id}{datetime.datetime.now().date()}{datetime.datetime.now()}'.encode()).hexdigest()
                    filename += '{}'.format(arquivo.name[arquivo.name.rfind('.'):])
                    arquivo.name = filename
                    nova_documentacao.arquivo = arquivo

                nova_documentacao.cadastrado_por_vinculo = request.user.get_vinculo()
                nova_documentacao.data_cadastro = datetime.datetime.now()
                nova_documentacao.save()

            if form.cleaned_data.get('comprovante_renda_aluno'):
                documentacao = documentacao_do_aluno.filter(tipo_arquivo=DocumentoInscricaoAluno.COMPROVANTE_RENDA,
                                                            data_cadastro__gte=prazo_expira,
                                                            integrante_familiar__isnull=True)
                if documentacao.exists():
                    nova_documentacao = documentacao.last()
                else:
                    nova_documentacao = DocumentoInscricaoAluno()
                    nova_documentacao.aluno = aluno
                    nova_documentacao.tipo_arquivo = DocumentoInscricaoAluno.COMPROVANTE_RENDA

                arquivo = form.cleaned_data.get('comprovante_renda_aluno')
                if nova_documentacao.arquivo != arquivo:
                    filename = hashlib.md5(f'{request.user.pessoafisica.id}{datetime.datetime.now().date()}{datetime.datetime.now()}'.encode()).hexdigest()
                    filename += '{}'.format(arquivo.name[arquivo.name.rfind('.'):])
                    arquivo.name = filename
                    nova_documentacao.arquivo = arquivo

                nova_documentacao.cadastrado_por_vinculo = request.user.get_vinculo()
                nova_documentacao.data_cadastro = datetime.datetime.now()
                nova_documentacao.save()

            diversos = request.FILES.getlist('arquivos')
            for diverso in diversos:
                arquivo = diverso
                filename = hashlib.md5(f'{request.user.pessoafisica.id}{datetime.datetime.now().date()}{datetime.datetime.now()}'.encode()).hexdigest()
                filename += '{}'.format(arquivo.name[arquivo.name.rfind('.'):])
                arquivo.name = filename
                nova_documentacao = DocumentoInscricaoAluno()
                nova_documentacao.aluno = aluno
                nova_documentacao.tipo_arquivo = DocumentoInscricaoAluno.DOCUMENTO_COMPLEMENTAR
                nova_documentacao.arquivo = arquivo
                nova_documentacao.cadastrado_por_vinculo = request.user.get_vinculo()
                nova_documentacao.save()

            for integrante in integrantes:
                id = f'{integrante.id}'
                arquivo = form_comprovantes.cleaned_data.get(id)

                if arquivo:
                    documentacao = documentacao_do_aluno.filter(tipo_arquivo=DocumentoInscricaoAluno.COMPROVANTE_RENDA,
                                                                data_cadastro__gte=prazo_expira,
                                                                integrante_familiar=integrante)
                    if documentacao.exists():
                        nova_documentacao = documentacao.last()
                    else:
                        nova_documentacao = DocumentoInscricaoAluno()
                        nova_documentacao.aluno = aluno
                        nova_documentacao.tipo_arquivo = DocumentoInscricaoAluno.COMPROVANTE_RENDA
                        nova_documentacao.integrante_familiar = integrante

                    arquivo = form_comprovantes.cleaned_data.get(id)
                    if nova_documentacao.arquivo != arquivo:
                        filename = hashlib.md5(f'{request.user.pessoafisica.id}{datetime.datetime.now().date()}{datetime.datetime.now()}'.encode()).hexdigest()
                        filename += '{}'.format(arquivo.name[arquivo.name.rfind('.'):])
                        arquivo.name = filename
                        nova_documentacao.arquivo = arquivo
                    nova_documentacao.cadastrado_por_vinculo = request.user.get_vinculo()
                    nova_documentacao.data_cadastro = datetime.datetime.now()
                    nova_documentacao.save()

            mensagem = 'Complete o cadastro da inscrição.'
            if programa.tipo_programa.sigla == Programa.TIPO_ALIMENTACAO:
                mensagem = 'Informe as refeições que você deseja obter.'
            elif programa.tipo_programa.sigla == Programa.TIPO_IDIOMA:
                mensagem = 'Selecione o(s) idioma(s) que você deseja aprender.'
            elif programa.tipo_programa.sigla == Programa.TIPO_TRABALHO:
                mensagem = 'Infome o setor de sua prefência, o turno que deseja trabalhar e suas habilidades.'
            elif programa.tipo_programa.sigla == Programa.TIPO_TRANSPORTE:
                mensagem = 'Infome o tipo do passe estudantil desejado.'

            return httprr(f"/ae/inscricao_detalhamento/{aluno_id}/{periodo_id}/{programa_id}/{data_cadastro}/", mensagem)

    else:
        mensagem = 'Complete o cadastro da inscrição.'
        if programa.tipo_programa.sigla == Programa.TIPO_ALIMENTACAO:
            mensagem = 'Informe as refeições que você deseja obter.'
        elif programa.tipo_programa.sigla == Programa.TIPO_IDIOMA:
            mensagem = 'Selecione o(s) idioma(s) que você deseja aprender.'
        elif programa.tipo_programa.sigla == Programa.TIPO_TRABALHO:
            mensagem = 'Infome o setor de sua prefência, o turno que deseja trabalhar e suas habilidades.'
        elif programa.tipo_programa.sigla == Programa.TIPO_TRANSPORTE:
            mensagem = 'Infome o tipo do passe estudantil desejado.'

        return httprr(f"/ae/inscricao_detalhamento/{aluno_id}/{periodo_id}/{programa_id}/{data_cadastro}/", mensagem)

    return locals()


@rtr()
@login_required
def inscricao_detalhamento(request, aluno_id, periodo_id, programa_id, data_cadastro):
    initial = {}
    programa = get_object_or_404(Programa, pk=programa_id)
    periodo_escolhido = get_object_or_404(PeriodoInscricao, pk=periodo_id)
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    if periodo_escolhido.apenas_participantes and not aluno.eh_participante_do_programa(programa):
        return httprr('/', 'Apenas participantes do programa podem realizar inscrição.', tag='error')

    tipo_programa = programa.tipo_programa.sigla

    title = f'Inscrição para {programa}: Detalhamento'
    campus_do_aluno = aluno.curso_campus.diretoria.setor.uo
    # Data de cadastro passada pela Assistente Social
    data_cadastro_as = None
    if data_cadastro:
        data_cadastro_as = datetime.datetime.strptime(data_cadastro, '%Y%m%d%H%M')
    eh_aluno = request.user.get_profile().aluno_edu_set.exists()
    periodos_permitidos = PeriodoInscricao.objects.filter(
        programa__publico_alvo=campus_do_aluno, data_termino__gte=datetime.datetime.today(), programa__pk=programa_id, edital__ativo=True
    )
    if eh_aluno:
        if request.user != aluno.pessoa_fisica.user or not periodos_permitidos.exists() or not (campus_do_aluno.id in programa.publico_alvo.values_list('id', flat=True)):
            raise PermissionDenied()

        if int(periodo_id) not in periodos_permitidos.values_list('id', flat=True):
            return httprr('/', 'Período de inscrição inválido.', tag='error')

    is_aluno = Aluno.objects.filter(pessoa_fisica=request.user.get_profile()).exists()
    inscricao = None
    if Inscricao.objects.filter(aluno=aluno_id, programa=programa_id, ativa=True, periodo_inscricao__id=periodo_id).exists():
        if tipo_programa:
            inscricao = Inscricao.objects.filter(aluno=aluno_id, programa=programa_id, ativa=True,
                                                 periodo_inscricao__id=periodo_id).latest('id').sub_instance()
        else:
            inscricao = Inscricao.objects.filter(aluno=aluno_id, programa=programa_id, ativa=True,
                                                 periodo_inscricao__id=periodo_id).latest('id')

    edital = periodo_escolhido.edital

    if tipo_programa == Programa.TIPO_ALIMENTACAO:
        if request.method == 'POST':
            form = InscricaoDetalhamentoAlimentacaoForm(data=request.POST)
            if form.is_valid():
                aluno = Aluno.objects.get(pk=aluno_id)
                if not inscricao:
                    inscricao = InscricaoAlimentacao()
                    inscricao.periodo_inscricao = get_object_or_404(PeriodoInscricao, pk=periodo_id)
                    solicitacao_cafe = SolicitacaoAlimentacao()
                    solicitacao_almoco = SolicitacaoAlimentacao()
                    solicitacao_janta = SolicitacaoAlimentacao()
                else:
                    solicitacao_cafe = inscricao.solicitacao_cafe
                    solicitacao_almoco = inscricao.solicitacao_almoco
                    solicitacao_janta = inscricao.solicitacao_janta

                if is_aluno:
                    inscricao.data_cadastro = datetime.datetime.today()
                else:
                    inscricao.data_cadastro = data_cadastro_as

                inscricao.programa = Programa.objects.get(pk=programa_id)
                inscricao.aluno = aluno
                if 'justificativa' in form.cleaned_data:
                    inscricao.motivo = form.cleaned_data['justificativa']

                solicitacao_cafe.seg = form.cleaned_data['seg_cafe']
                solicitacao_cafe.ter = form.cleaned_data['ter_cafe']
                solicitacao_cafe.qua = form.cleaned_data['qua_cafe']
                solicitacao_cafe.qui = form.cleaned_data['qui_cafe']
                solicitacao_cafe.sex = form.cleaned_data['sex_cafe']
                solicitacao_cafe.save()
                inscricao.solicitacao_cafe = solicitacao_cafe

                solicitacao_almoco.seg = form.cleaned_data['seg_almoco']
                solicitacao_almoco.ter = form.cleaned_data['ter_almoco']
                solicitacao_almoco.qua = form.cleaned_data['qua_almoco']
                solicitacao_almoco.qui = form.cleaned_data['qui_almoco']
                solicitacao_almoco.sex = form.cleaned_data['sex_almoco']
                solicitacao_almoco.save()
                inscricao.solicitacao_almoco = solicitacao_almoco

                solicitacao_janta.seg = form.cleaned_data['seg_janta']
                solicitacao_janta.ter = form.cleaned_data['ter_janta']
                solicitacao_janta.qua = form.cleaned_data['qua_janta']
                solicitacao_janta.qui = form.cleaned_data['qui_janta']
                solicitacao_janta.sex = form.cleaned_data['sex_janta']
                solicitacao_janta.save()
                inscricao.solicitacao_janta = solicitacao_janta

                inscricao.ativa = True
                inscricao.atualizado_por = request.user.get_vinculo()
                inscricao.atualizado_em = datetime.datetime.now()

                inscricao.save()
                inscricao.aluno.documentada = False
                inscricao.aluno.save()

                return httprr(f"/ae/inscricao_confirmacao/ALM/{inscricao.pk:d}/", 'Inscrição realizada com sucesso.')
        else:
            if inscricao:
                initial['justificativa'] = inscricao.motivo
                initial['seg_cafe'] = inscricao.solicitacao_cafe.seg
                initial['ter_cafe'] = inscricao.solicitacao_cafe.ter
                initial['qua_cafe'] = inscricao.solicitacao_cafe.qua
                initial['qui_cafe'] = inscricao.solicitacao_cafe.qui
                initial['sex_cafe'] = inscricao.solicitacao_cafe.sex
                initial['seg_almoco'] = inscricao.solicitacao_almoco.seg
                initial['ter_almoco'] = inscricao.solicitacao_almoco.ter
                initial['qua_almoco'] = inscricao.solicitacao_almoco.qua
                initial['qui_almoco'] = inscricao.solicitacao_almoco.qui
                initial['sex_almoco'] = inscricao.solicitacao_almoco.sex
                initial['seg_janta'] = inscricao.solicitacao_janta.seg
                initial['ter_janta'] = inscricao.solicitacao_janta.ter
                initial['qua_janta'] = inscricao.solicitacao_janta.qua
                initial['qui_janta'] = inscricao.solicitacao_janta.qui
                initial['sex_janta'] = inscricao.solicitacao_janta.sex

            form = InscricaoDetalhamentoAlimentacaoForm(initial=initial)

    elif tipo_programa == Programa.TIPO_IDIOMA:
        if request.method == 'POST':
            form = InscricaoDetalhamentoIdiomaForm(data=request.POST, request=request)
            if form.is_valid():
                aluno = Aluno.objects.get(pk=aluno_id)
                if not inscricao:
                    inscricao = InscricaoIdioma()
                    inscricao.periodo_inscricao = get_object_or_404(PeriodoInscricao, pk=periodo_id)

                if is_aluno:
                    inscricao.data_cadastro = datetime.datetime.today()
                else:
                    inscricao.data_cadastro = data_cadastro_as

                inscricao.programa = Programa.objects.get(pk=programa_id)
                inscricao.aluno = aluno
                if 'justificativa' in form.cleaned_data:
                    inscricao.motivo = form.cleaned_data['justificativa']

                inscricao.primeira_opcao = form.cleaned_data['primeira_opcao']
                inscricao.segunda_opcao = form.cleaned_data['segunda_opcao']
                inscricao.ativa = True
                inscricao.atualizado_por = request.user.get_vinculo()
                inscricao.atualizado_em = datetime.datetime.now()
                inscricao.save()
                inscricao.aluno.documentada = False
                inscricao.aluno.save()
                return httprr(f"/ae/inscricao_confirmacao/IDM/{inscricao.pk:d}/", 'Inscrição realizada com sucesso.')
        else:
            if inscricao:
                initial['justificativa'] = inscricao.motivo
                initial['primeira_opcao'] = inscricao.primeira_opcao.pk
                initial['segunda_opcao'] = inscricao.segunda_opcao.pk

            form = InscricaoDetalhamentoIdiomaForm(initial=initial, request=request)

    elif tipo_programa == Programa.TIPO_TRABALHO:
        formClass = InscricaoDetalhamentoTrabalhoFormFactory(request.user)
        if request.method == 'POST':
            form = formClass(data=request.POST)
            if form.is_valid():
                aluno = Aluno.objects.get(pk=aluno_id)
                if not inscricao:
                    inscricao = InscricaoTrabalho()
                    inscricao.periodo_inscricao = get_object_or_404(PeriodoInscricao, pk=periodo_id)

                if is_aluno:
                    inscricao.data_cadastro = datetime.datetime.today()
                else:
                    inscricao.data_cadastro = data_cadastro_as

                inscricao.programa = Programa.objects.get(pk=programa_id)
                inscricao.aluno = aluno
                if 'justificativa' in form.cleaned_data:
                    inscricao.motivo = form.cleaned_data['justificativa']

                inscricao.setor_preferencia = form.cleaned_data['setor_preferencia']
                inscricao.turno = form.cleaned_data['turno']
                inscricao.habilidades = form.cleaned_data['habilidades']

                inscricao.ativa = True
                inscricao.atualizado_por = request.user.get_vinculo()
                inscricao.atualizado_em = datetime.datetime.now()
                inscricao.save()
                inscricao.aluno.documentada = False
                inscricao.aluno.save()
                return httprr(f"/ae/inscricao_confirmacao/TRB/{inscricao.pk:d}/", 'Inscrição realizada com sucesso.')
        else:
            if inscricao:
                initial['justificativa'] = inscricao.motivo
                if inscricao.setor_preferencia:
                    initial['setor_preferencia'] = inscricao.setor_preferencia_id

                initial['turno'] = inscricao.turno
                initial['habilidades'] = inscricao.habilidades

            form = formClass(initial=initial)

    elif tipo_programa == Programa.TIPO_TRANSPORTE:
        formClass = InscricaoDetalhamentoPasseEstudantilFormFactory(request.user)
        if request.method == 'POST':
            form = formClass(data=request.POST)
            if form.is_valid():
                aluno = Aluno.objects.get(pk=aluno_id)
                if not inscricao:
                    inscricao = InscricaoPasseEstudantil()
                    inscricao.periodo_inscricao = get_object_or_404(PeriodoInscricao, pk=periodo_id)

                if is_aluno:
                    inscricao.data_cadastro = datetime.datetime.today()
                else:
                    inscricao.data_cadastro = data_cadastro_as

                inscricao.programa = Programa.objects.get(pk=programa_id)
                inscricao.aluno = aluno
                if 'justificativa' in form.cleaned_data:
                    inscricao.motivo = form.cleaned_data['justificativa']

                inscricao.tipo_passe = form.cleaned_data['tipo_passe']
                inscricao.atualizado_por = request.user.get_vinculo()
                inscricao.atualizado_em = datetime.datetime.now()
                inscricao.ativa = True

                inscricao.save()
                inscricao.aluno.documentada = False
                inscricao.aluno.save()
                return httprr(f"/ae/inscricao_confirmacao/PAS/{inscricao.pk:d}/", 'Inscrição realizada com sucesso.')
        else:
            if inscricao:
                initial['justificativa'] = inscricao.motivo
                initial['tipo_passe'] = inscricao.tipo_passe

            form = formClass(initial=initial)

    else:
        respostas_previas = RespostaInscricaoPrograma.objects.filter(pergunta__tipo_programa=programa.tipo_programa, inscricao=inscricao)
        ids_respostas_atuais = list()
        if request.method == 'POST':
            form = PerguntaInscricaoProgramaForm(request.POST or None, request=request, inscricao=inscricao, tipo_programa=programa.tipo_programa)

            if form.is_valid():

                aluno = Aluno.objects.get(pk=aluno_id)
                if not inscricao:
                    inscricao = Inscricao()
                    inscricao.periodo_inscricao = get_object_or_404(PeriodoInscricao, pk=periodo_id)

                if is_aluno:
                    inscricao.data_cadastro = datetime.datetime.today()
                else:
                    inscricao.data_cadastro = data_cadastro_as

                inscricao.programa = Programa.objects.get(pk=programa_id)
                inscricao.aluno = aluno
                inscricao.ativa = True
                inscricao.atualizado_por = request.user.get_vinculo()
                inscricao.atualizado_em = datetime.datetime.now()
                if 'justificativa' in form.cleaned_data:
                    inscricao.motivo = form.cleaned_data['justificativa']
                inscricao.save()

                chaves = list(request.POST.keys())

                for item in chaves:
                    valores = request.POST.getlist(item)
                    if 'pergunta_' in item:
                        id = item.split('_')[1]
                        pergunta_respondida = get_object_or_404(PerguntaInscricaoPrograma, pk=id)
                        for valor in valores:
                            valor_foi_informado = None
                            try:
                                valor_foi_informado = int(valor)
                            except Exception:
                                pass
                            if valor_foi_informado:
                                resposta_informada = get_object_or_404(OpcaoRespostaInscricaoPrograma, pk=valor_foi_informado)
                                if PerguntaInscricaoPrograma.objects.filter(id=id, ativo=True).exists():
                                    if respostas_previas.filter(pergunta=pergunta_respondida, resposta=resposta_informada).exists():
                                        o = RespostaInscricaoPrograma.objects.filter(pergunta=pergunta_respondida, inscricao=inscricao, resposta__isnull=False)[0]
                                    else:
                                        o = RespostaInscricaoPrograma()
                                        o.inscricao = inscricao
                                        o.pergunta = pergunta_respondida
                                    o.resposta = resposta_informada
                                    o.save()
                                    ids_respostas_atuais.append(o.id)

                    elif 'texto_' in item:
                        id = item.split('_')[1]
                        pergunta_respondida = get_object_or_404(PerguntaInscricaoPrograma, pk=id)
                        valor_informado = valores[0]
                        if pergunta_respondida.tipo_resposta == PerguntaInscricaoPrograma.NUMERO:
                            valor_informado = valor_informado.replace('.', '').replace(',', '.')
                        if RespostaInscricaoPrograma.objects.filter(pergunta=pergunta_respondida, inscricao=inscricao).exists():
                            o = RespostaInscricaoPrograma.objects.filter(pergunta=pergunta_respondida, inscricao=inscricao)[0]
                        else:
                            o = RespostaInscricaoPrograma()
                            o.inscricao = inscricao
                            o.pergunta = pergunta_respondida
                        o.valor_informado = valor_informado
                        o.save()
                        ids_respostas_atuais.append(o.id)

                respostas_previas.exclude(id__in=ids_respostas_atuais).delete()
                return httprr(f"/ae/inscricao_confirmacao/GEN/{inscricao.pk:d}/", 'Inscrição realizada com sucesso.')
        else:
            if inscricao:
                initial['justificativa'] = inscricao.motivo
            form = PerguntaInscricaoProgramaForm(inscricao=inscricao, tipo_programa=programa.tipo_programa)
    return locals()


@rtr()
@login_required
def inscricao_confirmacao(request, tipo_programa, inscricao_id):
    title = 'Sua inscrição foi confirmada!'
    respostas = None
    if tipo_programa == 'GEN':
        inscricao = get_object_or_404(Inscricao, pk=inscricao_id)
        respostas = inscricao.get_respostas_inscricao()
    else:
        inscricao = get_object_or_404(Inscricao, pk=inscricao_id).sub_instance()
    # se não for aluno e não tiver a permissão para adicionar inscrição "acesso negado"
    aluno_logado = Aluno.objects.filter(pessoa_fisica=request.user.get_profile())
    eh_aluno = request.user.get_profile().aluno_edu_set.exists()
    if aluno_logado and aluno_logado[0] != inscricao.aluno:
        if not request.user.has_perm('ae.add_inscricao'):
            raise PermissionDenied()

    return locals()


@rtr()
@permission_required('ae.pode_abrir_inscricao_do_campus, ae.view_inscricao')
def atualizar_documentacao_aluno(request, documento_id):
    documento = get_object_or_404(DocumentoInscricaoAluno, pk=documento_id)
    if documento.eh_ativa() and (
        request.user.has_perm('ae.pode_abrir_inscricao_do_campus') or (request.user.has_perm('ae.view_inscricao') and documento.aluno.pessoa_fisica == request.user.pessoafisica)
    ):
        title = f'Atualizar Documentação - {documento.tipo_arquivo}'
        if documento.integrante_familiar:
            title = title + f' ({documento.integrante_familiar})'
        form = AtualizaDocumentoAlunoForm(request.POST or None, request.FILES or None, instance=documento, aluno=documento.aluno)
        if form.is_valid():
            o = form.save(False)
            o.cadastrado_por_vinculo = request.user.get_vinculo()
            o.data_cadastro = datetime.datetime.now()
            o.save()
            return httprr(f'/edu/aluno/{documento.aluno.matricula}/?tab=atividades_estudantis', 'Documento atualizado com sucesso.')

        return locals()

    else:
        raise PermissionDenied


@rtr()
@permission_required('ae.pode_abrir_inscricao_do_campus')
def remover_documentacao_aluno(request, documento_id):
    documento = get_object_or_404(DocumentoInscricaoAluno, pk=documento_id)
    aluno = documento.aluno
    documento.delete()
    return httprr(f'/edu/aluno/{aluno.matricula}/?tab=atividades_estudantis', 'Documento removido com sucesso.')


@rtr()
@permission_required('ae.pode_abrir_inscricao_do_campus, ae.view_inscricao')
def adicionar_documentacao_aluno(request, matricula):
    title = 'Adicionar Documento do Aluno'
    aluno = get_object_or_404(Aluno, matricula=matricula)
    hoje = date.today()
    if request.user.has_perm('ae.pode_abrir_inscricao_do_campus') or request.user.pessoafisica == aluno.pessoa_fisica:
        form = AdicionarDocumentoAlunoForm(request.POST or None, request.FILES or None, aluno=aluno)
        if form.is_valid():
            nova_documentacao = DocumentoInscricaoAluno()
            nova_documentacao.aluno = aluno
            arquivo = form.cleaned_data.get('arquivo')
            filename = hashlib.md5(f'{request.user.pessoafisica.id}{datetime.datetime.now().date()}{datetime.datetime.now()}'.encode()).hexdigest()
            filename += '{}'.format(arquivo.name[arquivo.name.rfind('.'):])
            arquivo.name = filename
            nova_documentacao.arquivo = arquivo
            nova_documentacao.tipo_arquivo = form.cleaned_data.get('tipo_arquivo')
            nova_documentacao.cadastrado_por_vinculo = request.user.get_vinculo()
            integrante_familiar = form.cleaned_data.get('integrante_familiar')
            if integrante_familiar:
                nova_documentacao.integrante_familiar = integrante_familiar
            nova_documentacao.save()

            return httprr(f'/edu/aluno/{aluno.matricula}/?tab=atividades_estudantis', 'Documento adicionado com sucesso.')

        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('ae.pode_ver_relatorios_todos, ae.pode_ver_relatorios_campus, saude.pode_ver_relatorio_gestao')
def relatorio_gestao(request):
    title = 'Relatório de Gestão'
    form = RelatorioAtendimentoForm(request.GET or None, request=request)
    try:
        if form.is_valid():
            campus = form.cleaned_data.get('campus')
            if campus:
                title = f'Relatório de Gestão - Campus {campus}'

            relatorio_sistemico = False
            if request.user.has_perm('ae.pode_ver_relatorio_atendimento_todos') and not campus:
                relatorio_sistemico = True

            relatorio = form.obter_relatorio()
            reprocessar_dados = form.cleaned_data.get('reprocessar_dados')
            if not relatorio or reprocessar_dados:
                response = form.processar(title, request)
                return response

            form = RelatorioAtendimentoForm(request.GET or None, request=request, relatorio=relatorio)

            ################
            # ATENDIMENTOS #
            ################
            atendimentos, atendimentos_valor = obter_relatorio_atendimentos(relatorio)

            atendimentos_grafico = obter_relatorio_grafico(relatorio, 'grafico_atendimentos', RelatorioGrafico.PIE, RelatorioGrafico.ATENDIMENTOS)
            grafico_atendimentos = PieChart(
                'grafico_atendimentos',
                title='Total de Atendimentos',
                subtitle='Somatório da quantidade de atendimentos',
                minPointLength=0,
                data=atendimentos_grafico,
                dataLabels_format='<b>{point.name}</b>: {point.y:,.0f}',
                tooltip_pointFormat="<strong>{point.y}</strong> de {point.total:,.0f} ({point.percentage:.2f}%)",
            )
            setattr(grafico_atendimentos, 'id', 'grafico_atendimentos')

            alunos_assistidos = obter_relatorio_grafico(relatorio, 'alunos_unicos', RelatorioGrafico.PIE, RelatorioGrafico.ATENDIMENTOS)
            alunos_unicos = PieChart(
                'alunos_unicos', title='Alunos Assistidos', subtitle='Somatório de alunos assistidos em atendimentos', minPointLength=0, data=alunos_assistidos
            )
            setattr(alunos_unicos, 'id', 'alunos_unicos')

            if relatorio_sistemico:
                series_refeicoes_por_campus, categorias = obter_relatorio_grafico(
                    relatorio, 'total_refeicoes_por_campus', RelatorioGrafico.GROUPEDCOLUMN, RelatorioGrafico.ATENDIMENTOS
                )
                total_refeicoes_por_campus = GroupedColumnChart(
                    'total_refeicoes_por_campus',
                    title='Refeições fornecidas por campus',
                    subtitle='Somatório de refeições fornecidas por campus',
                    data=series_refeicoes_por_campus,
                    groups=categorias,
                    plotOptions_line_dataLabels_enable=True,
                    plotOptions_line_enableMouseTracking=True,
                )
                setattr(total_refeicoes_por_campus, 'id', 'total_refeicoes_por_campus')

                series_refeicoes_por_campus_unicos, categorias = obter_relatorio_grafico(
                    relatorio, 'total_refeicoes_por_campus_unicos', RelatorioGrafico.GROUPEDCOLUMN, RelatorioGrafico.ATENDIMENTOS
                )
                total_refeicoes_por_campus_unicos = GroupedColumnChart(
                    'total_refeicoes_por_campus_unicos',
                    title='Alunos assistidos com refeições fornecidas por campus',
                    subtitle='Somatório de alunos assistidos com refeições fornecidas por campus',
                    data=series_refeicoes_por_campus_unicos,
                    groups=categorias,
                    plotOptions_line_dataLabels_enable=True,
                    plotOptions_line_enableMouseTracking=True,
                )
                setattr(total_refeicoes_por_campus_unicos, 'id', 'total_refeicoes_por_campus_unicos')

            ############
            # AUXÍLIOS #
            ############
            auxilios = obter_relatorio_auxilios(relatorio)

            auxilios_grafico = obter_relatorio_grafico(relatorio, 'grafico_auxilios', RelatorioGrafico.PIE, RelatorioGrafico.AUXILIOS)
            grafico_auxilios = PieChart('grafico_auxilios', title='Total de Auxílios', subtitle='Somatório da quantidade de auxílios', minPointLength=0, data=auxilios_grafico)
            setattr(grafico_auxilios, 'id', 'grafico_auxilios')

            ##########
            # BOLSAS #
            ##########
            bolsas = obter_relatorio_bolsas(relatorio)
            ver_bolsas_profissional_todos = False
            if relatorio_sistemico:
                ver_bolsas_profissional_todos = True
                series_bolsas_por_campus, categorias = obter_relatorio_grafico(relatorio, 'total_bolsas_campus', RelatorioGrafico.GROUPEDCOLUMN, RelatorioGrafico.BOLSAS)
                total_bolsas_campus = GroupedColumnChart(
                    'total_bolsas_campus',
                    title='Total geral de bolsas de apoio à formação estudantil por campus',
                    subtitle='Total geral de bolsas de apoio à formação estudantil por campus',
                    data=series_bolsas_por_campus,
                    groups=categorias,
                    plotOptions_line_dataLabels_enable=True,
                    plotOptions_line_enableMouseTracking=True,
                )
                setattr(total_bolsas_campus, 'id', 'total_bolsas_campus')

                series_bolsas_por_campus_unicos, categorias = obter_relatorio_grafico(
                    relatorio, 'total_bolsas_campus_unicos', RelatorioGrafico.GROUPEDCOLUMN, RelatorioGrafico.BOLSAS
                )
                total_bolsas_campus_unicos = GroupedColumnChart(
                    'total_bolsas_campus_unicos',
                    title='Total de assistidos com bolsas de apoio à formação estudantil por campus',
                    subtitle='Total de assistidos com bolsas de apoio à formação estudantil por campus',
                    data=series_bolsas_por_campus_unicos,
                    groups=categorias,
                    plotOptions_line_dataLabels_enable=True,
                    plotOptions_line_enableMouseTracking=True,
                )
                setattr(total_bolsas_campus_unicos, 'id', 'total_bolsas_campus_unicos')

            else:
                bolsas_todas = obter_relatorio_grafico(relatorio, 'bolsas_campus', RelatorioGrafico.PIE, RelatorioGrafico.BOLSAS)
                if bolsas_todas:
                    bolsas_campus = PieChart(
                        'bolsas_campus',
                        title='Total de Bolsas',
                        subtitle='Somatório da quantidade de bolsas',
                        minPointLength=0,
                        data=bolsas_todas,
                        dataLabels_format='<b>{point.name}</b>: {point.y:,.0f}',
                        tooltip_pointFormat="<strong>{point.y}</strong> de {point.total:,.0f} ({point.percentage:.2f}%)",
                    )
                    setattr(bolsas_campus, 'id', 'bolsas_campus')

                bolsas_unicas = obter_relatorio_grafico(relatorio, 'bolsas_campus_unicos', RelatorioGrafico.PIE, RelatorioGrafico.BOLSAS)
                if bolsas_unicas:
                    bolsas_campus_unicos = PieChart(
                        'bolsas_campus_unicos',
                        title='Alunos assistidos em bolsas',
                        subtitle='Somatório de alunos assistidos em bolsas',
                        minPointLength=0,
                        data=bolsas_unicas,
                        dataLabels_format='<b>{point.name}</b>: {point.y:,.0f}',
                        tooltip_pointFormat="<strong>{point.y}</strong> de {point.total:,.0f} ({point.percentage:.2f}%)",
                    )
                    setattr(bolsas_campus_unicos, 'id', 'bolsas_campus_unicos')

            #############
            # PROGRAMAS #
            #############
            programas = obter_relatorio_programas(relatorio)
            ver_transporte_todos = None
            if relatorio_sistemico:
                ver_transporte_todos = True
                series_transportes_por_campus, categorias = obter_relatorio_grafico(
                    relatorio, 'total_transportes_por_campus', RelatorioGrafico.GROUPEDCOLUMN, RelatorioGrafico.PROGRAMAS
                )
                total_transportes_por_campus = GroupedColumnChart(
                    'total_transportes_por_campus',
                    title='Participações em Auxílio-transporte por tipo',
                    subtitle='Somatório de participações em Auxílio-transporte por tipo',
                    data=series_transportes_por_campus,
                    groups=categorias,
                    plotOptions_line_dataLabels_enable=True,
                    plotOptions_line_enableMouseTracking=True,
                )
                setattr(total_transportes_por_campus, 'id', 'total_transportes_por_campus')

                series_transportes_por_campus_unicos, categorias = obter_relatorio_grafico(
                    relatorio, 'total_transportes_por_campus_unicos', RelatorioGrafico.GROUPEDCOLUMN, RelatorioGrafico.PROGRAMAS
                )
                total_transportes_por_campus_unicos = GroupedColumnChart(
                    'total_transportes_por_campus_unicos',
                    title='Alunos assistidos em participações em Auxílio-transporte por tipo',
                    subtitle='Somatório de alunos assistidos em participações em Auxílio-transporte por tipo',
                    data=series_transportes_por_campus_unicos,
                    groups=categorias,
                    plotOptions_line_dataLabels_enable=True,
                    plotOptions_line_enableMouseTracking=True,
                )
                setattr(total_transportes_por_campus_unicos, 'id', 'total_transportes_por_campus_unicos')

            else:
                dados = obter_relatorio_grafico(relatorio, 'transporte_campus', RelatorioGrafico.PIE, RelatorioGrafico.PROGRAMAS)
                if dados:
                    transporte_campus = PieChart(
                        'transporte_campus',
                        title='Auxílio-Transporte do Campus',
                        subtitle='Somatório da quantidade de auxílios-transporte',
                        minPointLength=0,
                        data=dados,
                        dataLabels_format='<b>{point.name}</b>: {point.y:,.0f}',
                        tooltip_pointFormat="<strong>{point.y}</strong> de {point.total:,.0f} ({point.percentage:.2f}%)",
                    )
                    setattr(transporte_campus, 'id', 'transporte_campus')

                dados_unicos = obter_relatorio_grafico(relatorio, 'transporte_campus_unicos', RelatorioGrafico.PIE, RelatorioGrafico.PROGRAMAS)
                if dados_unicos:
                    transporte_campus_unicos = PieChart(
                        'transporte_campus_unicos',
                        title='Total de alunos assistidos com auxílio-transporte do campus',
                        subtitle='Total de alunos assistidos com auxílio-transporte do campus',
                        minPointLength=0,
                        data=dados_unicos,
                        dataLabels_format='<b>{point.name}</b>: {point.y:,.0f}',
                        tooltip_pointFormat="<strong>{point.y}</strong> de {point.total:,.0f} ({point.percentage:.2f}%)",
                    )
                    setattr(transporte_campus_unicos, 'id', 'transporte_campus_unicos')

            #########
            # SAÚDE #
            #########
            saude = obter_relatorio_saude(relatorio)

            dados = obter_relatorio_grafico(relatorio, 'saude_atendimentos', RelatorioGrafico.PIE, RelatorioGrafico.SAUDE)
            saude_atendimentos = PieChart(
                'saude_atendimentos', title='Atendimentos por Especialidade', subtitle='Atendimentos contabilizados pela especialidade', minPointLength=0, data=dados
            )
            setattr(saude_atendimentos, 'id', 'saude_atendimentos')

            ###############
            # TOTALIZADOR #
            ###############
            dados_resumo_atendimentos, dados_resumo_auxilios, dados_resumo_bolsas, dados_resumo_programas, dados_resumo_saude, dados_resumo_total = obter_dados_resumo(relatorio)

            dados_grafico_resumo = obter_relatorio_grafico(relatorio, 'alunos_vulnerabilidade_assistidos', RelatorioGrafico.BAR, RelatorioGrafico.RESUMO)
            alunos_vulnerabilidade_assistidos = BarChart(
                'alunos_vulnerabilidade_assistidos',
                title='Alunos com Vunerabilidade Socioeconômica Assistidos',
                subtitle='Alunos com Vunerabilidade Socioeconômica Assistidos',
                minPointLength=0,
                data=dados_grafico_resumo,
            )
            setattr(alunos_vulnerabilidade_assistidos, 'id', 'alunos_vulnerabilidade_assistidos')
    except RelatorioGrafico.DoesNotExist:
        # Reprocessa os dados
        response = form.processar(title, request)
        return response

    return locals()


@rtr()
@permission_required('ae.pode_ver_relatorio_atendimento_todos, ae.pode_ver_relatorio_atendimento_do_campus')
def grafico_atendimentos(request):
    title = 'Gráficos de Atendimentos'
    form = GraficoAtendimentoForm(request.POST or None)
    if form.is_valid():
        demandas_atendidas = DemandaAlunoAtendida.objects.filter(quantidade__gt=0)
        if request.method == 'POST':
            if form.is_valid():
                if 'ano' in form.cleaned_data and form.cleaned_data.get('ano') != 'Todos':
                    demandas_atendidas = demandas_atendidas.filter(data__year=form.cleaned_data['ano'])

        demandas_atendidas.order_by('demanda__nome')

        campi = list(UnidadeOrganizacional.objects.uo().all())
        grafico_atendimentos = []

        for demanda in DemandaAluno.ativas.all():
            atendimentos_grafico = []
            for campus in campi:
                quantidade = demandas_atendidas.filter(campus=campus, demanda__nome=demanda.nome)
                if quantidade.exists():
                    atendimentos_grafico.append([campus.sigla, quantidade.aggregate(Sum('quantidade'))['quantidade__sum'] or 0])

            if atendimentos_grafico:
                nome_pk = f'grafico_atendimentos_{demanda.pk}'
                grafico = PieChart(nome_pk, title=demanda.nome, subtitle="Total de atendimentos por campus", minPointLength=0, data=atendimentos_grafico)
                setattr(grafico, 'id', nome_pk)
                grafico_atendimentos.append(grafico)

    return locals()


@rtr()
@permission_required(['ae.pode_ver_relatorio_financeiro', 'ae.pode_ver_relatorio_financeiro_todos'])
def relatorio_financeiro(request):
    title = 'Relatório Financeiro: Auxílios'

    if request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
        valor_total_auxilios = ValorTotalAuxilios.objects.all()
    else:
        valor_total_auxilios = ValorTotalAuxilios.objects.filter(campus=get_uo(request.user).id)

    form = RelatorioFinanceiroAuxiliosForm(request.POST or None, request=request)
    total_planejado = total_gasto = total_saldo = 0
    if form.is_valid():
        if request.POST.get('campus'):
            campus = int(request.POST['campus'])
            valor_total_auxilios = valor_total_auxilios.filter(campus=campus)

        if request.POST.get('ano'):
            if request.POST['ano'] != 'Selecione um ano':
                ano = int(request.POST['ano'])
                valor_total_auxilios = valor_total_auxilios.filter(data_inicio__lte=date(ano, 12, 31), data_termino__gte=date(ano, 1, 1))
        if request.POST.get('tipo_auxilio'):
            valor_total_auxilios = valor_total_auxilios.filter(tipoatendimentosetor=request.POST.get('tipo_auxilio'))
    auxilios = list()
    for valor_auxilios in valor_total_auxilios.order_by('campus', 'tipoatendimentosetor', 'data_inicio'):
        campus = valor_auxilios.campus
        inicio = valor_auxilios.data_inicio
        termino = valor_auxilios.data_termino
        tipoatendimentosetor = valor_auxilios.tipoatendimentosetor
        gasto = (
            AtendimentoSetor.objects.filter(campus=campus, tipoatendimentosetor=tipoatendimentosetor)
            .exclude(valor__isnull=True)
            .filter(data__gte=inicio, data__lte=termino)
            .aggregate(valor=Sum('valor'))
        )

        TWOPLACES = Decimal(10) ** -2
        if gasto['valor']:
            total_gasto = total_gasto + gasto['valor']
            saldo = Decimal(valor_auxilios.valor).quantize(TWOPLACES) - Decimal(gasto['valor']).quantize(TWOPLACES)
        else:
            saldo = Decimal(valor_auxilios.valor).quantize(TWOPLACES)
        total_planejado = total_planejado + Decimal(valor_auxilios.valor).quantize(TWOPLACES)
        total_saldo = total_saldo + saldo
        auxilios.append(
            dict(campus=campus, inicio=inicio, termino=termino, tipoatendimentosetor=tipoatendimentosetor, planejado=valor_auxilios.valor, gasto=gasto['valor'], saldo=saldo)
        )

    return locals()


@rtr()
@permission_required(['ae.pode_ver_relatorio_financeiro', 'ae.pode_ver_relatorio_financeiro_todos'])
def relatorio_financeiro_refeicoes(request):
    title = 'Relatório Financeiro: Refeições'

    form = RelatorioFinanceiroForm(request.POST or None, request=request)
    campus = False
    escolheu_ano_e_campus = False
    if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
        campus = get_uo(request.user).id
        nao_eh_usuario_sistemico = True

    if form.is_valid():
        if request.POST.get('ano') and request.POST.get('ano') != 'Selecione um ano':
            ano = int(request.POST['ano'])
            if campus:
                escolheu_ano_e_campus = True
            if request.POST.get('campus') and request.POST.get('campus') != 'Selecione um campus':
                campus = int(request.POST['campus'])
                escolheu_ano_e_campus = True
            if escolheu_ano_e_campus:
                achou_refeicoes = False
                TWOPLACES = Decimal(10) ** -2
                SEARCH_QUERY_OFERTA = Q(campus=campus) & (
                    Q(data_inicio__gte=date(ano, 1, 1), data_termino__lte=date(ano, 12, 31))
                    | Q(data_inicio__lte=date(ano, 1, 1), data_termino__gte=date(ano, 12, 31))
                    | Q(data_inicio__lte=date(ano, 1, 1), data_termino__gte=date(ano, 1, 1), data_termino__lte=date(ano, 12, 31))
                    | Q(data_inicio__gte=date(ano, 1, 1), data_inicio__lte=date(ano, 12, 31), data_termino__gte=date(ano, 12, 31))
                )
                campus_tem_valor_refeicao = OfertaValorRefeicao.objects.filter(SEARCH_QUERY_OFERTA)
                if campus_tem_valor_refeicao:
                    TWOPLACES = Decimal(10) ** -2
                    relatorio_por_periodo = list()
                    total_refeicoes = DemandaAlunoAtendida.objects.filter(
                        campus=campus, quantidade__gt=0, demanda__in=[1, 2, 19], data__lte=date(ano, 12, 31), data__gte=date(ano, 1, 1)
                    )
                    for oferta in campus_tem_valor_refeicao:
                        contador_cafe = 0
                        contador_almoco = 0
                        contador_jantar = 0
                        gasto_cafe = 0.00
                        gasto_almoco = 0.00
                        gasto_jantar = 0.00
                        valor_total_refeicoes = total_refeicoes.filter(data__gte=oferta.data_inicio, data__lte=oferta.data_termino)
                        if valor_total_refeicoes:
                            achou_refeicoes = True
                            sigla_campus = valor_total_refeicoes[0].campus
                            for valor_refeicoes in valor_total_refeicoes:
                                if valor_refeicoes.demanda.id == 1:
                                    contador_almoco += int(valor_refeicoes.quantidade)
                                    gasto_almoco = Decimal(gasto_almoco).quantize(TWOPLACES) + Decimal(valor_refeicoes.quantidade * float(oferta.valor)).quantize(TWOPLACES)
                                elif valor_refeicoes.demanda.id == 2:
                                    contador_jantar += int(valor_refeicoes.quantidade)
                                    gasto_jantar = Decimal(gasto_jantar).quantize(TWOPLACES) + Decimal(valor_refeicoes.quantidade * float(oferta.valor)).quantize(TWOPLACES)
                                elif valor_refeicoes.demanda.id == 19:
                                    contador_cafe += int(valor_refeicoes.quantidade)
                                    gasto_cafe = Decimal(gasto_cafe).quantize(TWOPLACES) + Decimal(valor_refeicoes.quantidade * float(oferta.valor)).quantize(TWOPLACES)
                            total = Decimal(gasto_almoco).quantize(TWOPLACES) + Decimal(gasto_jantar).quantize(TWOPLACES) + Decimal(gasto_cafe).quantize(TWOPLACES)
                            if not total:
                                total = 0.00
                            relatorio_por_periodo.append(
                                dict(
                                    campus=sigla_campus,
                                    data_inicio=oferta.data_inicio,
                                    data_termino=oferta.data_termino,
                                    valor=oferta.valor,
                                    gasto_cafe=gasto_cafe,
                                    gasto_almoco=gasto_almoco,
                                    gasto_jantar=gasto_jantar,
                                    quantidade_cafe=contador_cafe,
                                    quantidade_almoco=contador_almoco,
                                    quantidade_jantar=contador_jantar,
                                    total=total,
                                )
                            )

    return locals()


@rtr()
@permission_required(['ae.pode_ver_relatorio_financeiro', 'ae.pode_ver_relatorio_financeiro_todos'])
def relatorio_financeiro_auxilio_transporte(request):
    title = 'Relatório Financeiro: Auxílio Transporte'
    form = RelatorioFinanceiroForm(request.POST or None, request=request)
    campus = False
    escolheu_ano_e_campus = False
    if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
        campus = get_uo(request.user).id
        nao_eh_usuario_sistemico = True

    if form.is_valid():
        if request.POST.get('ano') and request.POST.get('ano') != 'Selecione um ano':
            ano = int(request.POST['ano'])
            if campus:
                escolheu_ano_e_campus = True
            if request.POST.get('campus') and request.POST.get('campus') != 'Selecione um campus':
                campus = int(request.POST['campus'])
                escolheu_ano_e_campus = True
            if escolheu_ano_e_campus:
                data_inicio = date(ano, 1, 1)
                mes_atual = datetime.datetime.now().month
                if mes_atual == 12:
                    data_termino = date(ano + 1, 1, 1)
                else:
                    data_termino = date(ano, mes_atual + 1, 1)
                dias_do_mes = calendar.monthrange(ano, mes_atual)[1]
                achou_passes = False
                TWOPLACES = Decimal(10) ** -2
                SEARCH_QUERY_OFERTA = Q(campus=campus) & (
                    Q(data_inicio__gte=date(ano, 1, 1), data_termino__lte=date(ano, 12, 31))
                    | Q(data_inicio__lte=date(ano, 1, 1), data_termino__gte=date(ano, 12, 31))
                    | Q(data_inicio__lte=date(ano, 1, 1), data_termino__gte=date(ano, 1, 1), data_termino__lte=date(ano, 12, 31))
                    | Q(data_inicio__gte=date(ano, 1, 1), data_inicio__lte=date(ano, 12, 31), data_termino__gte=date(ano, 12, 31))
                )
                relatorio_passe = list()
                valor_total_passe = OfertaPasse.objects.filter(SEARCH_QUERY_OFERTA)
                lista_de_participacoes = Participacao.objects.filter(programa__instituicao=campus)
                lista_de_participacoes = lista_de_participacoes.filter(id__in=ParticipacaoPasseEstudantil.objects.values_list('participacao_id'))
                sigla_campus = UnidadeOrganizacional.objects.uo().get(id=campus).sigla

                programa = Programa.objects.get(tipo=Programa.TIPO_TRANSPORTE, instituicao=campus)
                disponibilidade = programa.get_disponibilidade()
                for periodo_passe in valor_total_passe:
                    valor = 0.00
                    somatorio = 0.00
                    total_gasto = 0.00
                    quantidade = 0
                    demonstrativo_total_previsto = 0
                    demonstrativo_total_pago = 0
                    alunos = list()
                    total_valor_mensal = total_dias_previstos = total_dias_pagos = 0
                    SEARCH_QUERY_PASSES = (
                        Q(data_inicio__lt=periodo_passe.data_inicio, data_termino__isnull=True)
                        | Q(data_inicio__lt=periodo_passe.data_inicio, data_termino__gte=periodo_passe.data_inicio, data_termino__lte=periodo_passe.data_termino)
                        | Q(data_inicio__lt=periodo_passe.data_inicio, data_termino__gt=periodo_passe.data_termino)
                        | Q(data_inicio__gte=periodo_passe.data_inicio, data_inicio__lte=periodo_passe.data_termino)
                    )
                    participacoes_por_periodo = lista_de_participacoes.filter(SEARCH_QUERY_PASSES)
                    if participacoes_por_periodo:
                        for participacao in participacoes_por_periodo:
                            passe_estudantil = ParticipacaoPasseEstudantil.objects.get(participacao_id=participacao.id)
                            achou_passes = True
                            if participacao.data_termino:
                                if (
                                    participacao.data_inicio <= periodo_passe.data_inicio
                                    and participacao.data_termino >= periodo_passe.data_inicio
                                    and participacao.data_termino <= periodo_passe.data_termino
                                ):
                                    ajuste_ultimo_dia = participacao.data_termino + timedelta(1)
                                    calcula_meses = relativedelta(ajuste_ultimo_dia, periodo_passe.data_inicio)
                                elif participacao.data_inicio <= periodo_passe.data_inicio and participacao.data_termino >= periodo_passe.data_termino:
                                    ajuste_ultimo_dia = periodo_passe.data_termino + timedelta(1)
                                    calcula_meses = relativedelta(ajuste_ultimo_dia, periodo_passe.data_inicio)
                                else:
                                    ajuste_ultimo_dia = periodo_passe.data_termino + timedelta(1)
                                    calcula_meses = relativedelta(ajuste_ultimo_dia, participacao.data_inicio)
                            else:
                                if participacao.data_inicio <= periodo_passe.data_inicio:
                                    ajuste_ultimo_dia = periodo_passe.data_termino + timedelta(1)
                                    calcula_meses = relativedelta(ajuste_ultimo_dia, periodo_passe.data_inicio)
                                else:
                                    ajuste_ultimo_dia = periodo_passe.data_termino + timedelta(1)
                                    calcula_meses = relativedelta(ajuste_ultimo_dia, participacao.data_inicio)
                            quantidade += 1
                            if calcula_meses.years:
                                meses = calcula_meses.years * 12
                            else:
                                meses = calcula_meses.months
                            diferenca_dias = calcula_meses.days
                            diferenca_inicio = 0
                            diferenca_termino = 0
                            if passe_estudantil.valor_concedido:
                                if meses and not diferenca_dias:
                                    valor = (Decimal(meses).quantize(TWOPLACES) * passe_estudantil.valor_concedido).quantize(TWOPLACES)
                                elif not meses and diferenca_dias:
                                    valor = Decimal((Decimal(diferenca_dias).quantize(TWOPLACES) * passe_estudantil.valor_concedido) / 30).quantize(TWOPLACES)
                                else:
                                    valor = (Decimal(meses).quantize(TWOPLACES) * passe_estudantil.valor_concedido).quantize(TWOPLACES) + Decimal(
                                        (Decimal(diferenca_dias).quantize(TWOPLACES) * passe_estudantil.valor_concedido) / 30
                                    ).quantize(TWOPLACES)

                                valor_mensal = passe_estudantil.valor_concedido
                                if participacao.data_inicio < data_termino:
                                    if not participacao.data_termino or (participacao.data_termino and participacao.data_termino > data_inicio):
                                        if participacao.data_inicio > data_inicio:
                                            diferenca_inicio = (participacao.data_inicio - data_inicio).days
                                        if participacao.data_termino and participacao.data_termino < data_termino:
                                            diferenca_termino = (data_termino - participacao.data_termino).days

                                        dias_pagos = (data_termino - data_inicio).days - diferenca_inicio - diferenca_termino

                                        valor = Decimal((valor_mensal / 30) * dias_pagos).quantize(Decimal(10) ** -2)

                                        somatorio = Decimal(somatorio) + Decimal(valor)

                                        hoje = date.today()
                                        ultimo_dia_ano = date(ano, 12, 31)
                                        if participacao.data_termino and participacao.data_termino < ultimo_dia_ano and participacao.data_termino >= hoje:
                                            variacao = (participacao.data_termino - hoje).days
                                        elif participacao.data_termino and participacao.data_termino < hoje:
                                            variacao = 0
                                        else:
                                            variacao = (data_termino - hoje).days

                                        dias_pagos_efetivamente = dias_pagos - variacao
                                        valor_gasto_efetivamente = Decimal((valor_mensal / 30) * dias_pagos_efetivamente).quantize(Decimal(10) ** -2)
                                        alunos.append(
                                            [
                                                participacao.aluno.pessoa_fisica.nome,
                                                participacao.aluno.matricula,
                                                participacao.data_inicio,
                                                participacao.data_termino,
                                                valor_mensal,
                                                dias_pagos,
                                                valor,
                                                dias_pagos_efetivamente,
                                                valor_gasto_efetivamente,
                                            ]
                                        )

                                        total_valor_mensal = total_valor_mensal + valor_mensal
                                        total_dias_previstos = total_dias_previstos + dias_pagos
                                        total_dias_pagos = total_dias_pagos + dias_pagos_efetivamente
                                        demonstrativo_total_previsto += valor
                                        demonstrativo_total_pago += valor_gasto_efetivamente
                                        total_gasto = Decimal(total_gasto).quantize(Decimal(10) ** -2) + Decimal(valor_gasto_efetivamente).quantize(Decimal(10) ** -2)

                        if somatorio:
                            saldo = Decimal(periodo_passe.valor_passe).quantize(TWOPLACES) - Decimal(total_gasto).quantize(TWOPLACES)
                        else:
                            saldo = periodo_passe.valor_passe
                        lista_alunos = sorted(alunos, key=lambda student: student[0])
                        relatorio_passe.append(
                            dict(
                                campus=sigla_campus,
                                data_inicio=periodo_passe.data_inicio,
                                data_termino=periodo_passe.data_termino,
                                planejado=periodo_passe.valor_passe,
                                gasto=total_gasto,
                                quantidade=quantidade,
                                somatorio=somatorio,
                                saldo=saldo,
                            )
                        )

    return locals()


@rtr()
@permission_required(['ae.pode_ver_relatorio_financeiro', 'ae.pode_ver_relatorio_financeiro_todos'])
def relatorio_financeiro_bolsas(request):
    title = 'Relatório Financeiro: Bolsas'

    form = RelatorioFinanceiroBolsasForm(request.POST or None, request=request)

    campus_id = False
    escolheu_ano_e_campus = False
    nao_eh_usuario_sistemico = False

    if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
        campus_id = get_uo(request.user).id
        nao_eh_usuario_sistemico = True

    if form.is_valid():
        if request.POST.get('ano') and request.POST.get('ano') != 'Selecione um ano':
            ano = int(request.POST['ano'])
            campi = UnidadeOrganizacional.objects.uo().all()
            if request.POST.get('categoria') and request.POST.get('categoria') != 'Selecione uma categoria':
                categoria = int(request.POST['categoria'])
                escolheu_ano_e_campus = True

                if campus_id:
                    campi = campi.filter(id=campus_id)
                elif request.POST.get('campus') and request.POST.get('campus') != 'Selecione um campus':
                    campus_id = int(request.POST['campus'])
                    campi = campi.filter(id=campus_id)
                relatorio_bolsa = list()
                total_planejado = total_gasto = total_saldo = total_participacoes = 0
                for campus in campi:
                    achou_bolsas = True

                    TWOPLACES = Decimal(10) ** -2
                    SEARCH_QUERY_OFERTA = Q(campus=campus, categoriabolsa=categoria) & (
                        Q(data_inicio__gte=date(ano, 1, 1), data_termino__lte=date(ano, 12, 31))
                        | Q(data_inicio__lte=date(ano, 1, 1), data_termino__gte=date(ano, 12, 31))
                        | Q(data_inicio__lte=date(ano, 1, 1), data_termino__gte=date(ano, 1, 1), data_termino__lte=date(ano, 12, 31))
                        | Q(data_inicio__gte=date(ano, 1, 1), data_inicio__lte=date(ano, 12, 31), data_termino__gte=date(ano, 12, 31))
                    )

                    valor_total_bolsa = ValorTotalBolsas.objects.filter(SEARCH_QUERY_OFERTA)
                    valores_bolsa = OfertaValorBolsa.objects.filter(campus=campus)
                    sigla_campus = campus.sigla
                    participacoes_por_periodo = False

                    for item in valor_total_bolsa:
                        valor = 0.00
                        somatorio = 0.00
                        saldo = 0.00
                        tipo_vinculo_programa = CategoriaBolsa.objects.get(pk=item.categoriabolsa.id)
                        SEARCH_QUERY_BOLSAS = (
                            Q(data_inicio__lt=item.data_inicio, data_termino__isnull=True)
                            | Q(data_inicio__lt=item.data_inicio, data_termino__gte=item.data_inicio, data_termino__lte=item.data_termino)
                            | Q(data_inicio__lt=item.data_inicio, data_termino__gt=item.data_termino)
                            | Q(data_inicio__gte=item.data_inicio, data_inicio__lte=item.data_termino)
                        )

                        if tipo_vinculo_programa.vinculo_programa == True:
                            lista_de_participacoes = Participacao.objects.filter(programa__instituicao=campus)
                            lista_de_participacoes = lista_de_participacoes.filter(id__in=ParticipacaoTrabalho.objects.values_list('participacao_id'))
                            lista_de_bolsas = lista_de_participacoes.filter(SEARCH_QUERY_BOLSAS)
                        else:
                            lista_de_participacoes = ParticipacaoBolsa.objects.filter(
                                aluno__curso_campus__diretoria__setor__uo=campus, categoria=item.categoriabolsa.id, categoria__vinculo_programa=False
                            ).order_by('id')
                            lista_de_bolsas = lista_de_participacoes.filter(SEARCH_QUERY_BOLSAS)

                        if valores_bolsa:
                            for valor_da_bolsa in valores_bolsa:
                                if (
                                    (valor_da_bolsa.data_inicio >= item.data_inicio and valor_da_bolsa.data_termino <= item.data_termino)
                                    or (valor_da_bolsa.data_inicio < item.data_inicio and valor_da_bolsa.data_termino >= item.data_termino)
                                    or (
                                        valor_da_bolsa.data_inicio < item.data_inicio
                                        and valor_da_bolsa.data_termino > item.data_inicio
                                        and valor_da_bolsa.data_termino < item.data_termino
                                    )
                                    or (
                                        valor_da_bolsa.data_inicio >= item.data_inicio
                                        and valor_da_bolsa.data_inicio < item.data_termino
                                        and valor_da_bolsa.data_termino >= item.data_termino
                                    )
                                ):
                                    SEARCH_QUERY_VALORES = (
                                        Q(data_inicio__lt=valor_da_bolsa.data_inicio, data_termino__isnull=True)
                                        | Q(data_inicio__lt=valor_da_bolsa.data_inicio, data_termino__gte=valor_da_bolsa.data_inicio, data_termino__lte=valor_da_bolsa.data_termino)
                                        | Q(data_inicio__lt=valor_da_bolsa.data_inicio, data_termino__gt=valor_da_bolsa.data_termino)
                                        | Q(data_inicio__gte=valor_da_bolsa.data_inicio, data_inicio__lte=valor_da_bolsa.data_termino)
                                    )
                                    participacoes_por_periodo = lista_de_bolsas.filter(SEARCH_QUERY_VALORES)
                                    if participacoes_por_periodo:
                                        achou_bolsas = True
                                        for participacao in participacoes_por_periodo:
                                            if participacao.data_termino:
                                                if (
                                                    participacao.data_inicio <= valor_da_bolsa.data_inicio
                                                    and participacao.data_termino >= valor_da_bolsa.data_inicio
                                                    and participacao.data_termino <= valor_da_bolsa.data_termino
                                                ):
                                                    ajuste_ultimo_dia = participacao.data_termino + timedelta(1)
                                                    calcula_meses = relativedelta(ajuste_ultimo_dia, valor_da_bolsa.data_inicio)
                                                elif participacao.data_inicio <= valor_da_bolsa.data_inicio and participacao.data_termino >= valor_da_bolsa.data_termino:
                                                    ajuste_ultimo_dia = valor_da_bolsa.data_termino + timedelta(1)
                                                    calcula_meses = relativedelta(ajuste_ultimo_dia, valor_da_bolsa.data_inicio)
                                                else:
                                                    ajuste_ultimo_dia = valor_da_bolsa.data_termino + timedelta(1)
                                                    calcula_meses = relativedelta(ajuste_ultimo_dia, participacao.data_inicio)
                                            else:
                                                if participacao.data_inicio <= valor_da_bolsa.data_inicio:
                                                    ajuste_ultimo_dia = valor_da_bolsa.data_termino + timedelta(1)
                                                    calcula_meses = relativedelta(ajuste_ultimo_dia, valor_da_bolsa.data_inicio)
                                                else:
                                                    ajuste_ultimo_dia = valor_da_bolsa.data_termino + timedelta(1)
                                                    calcula_meses = relativedelta(ajuste_ultimo_dia, participacao.data_inicio)
                                            if calcula_meses.years:
                                                meses = calcula_meses.years * 12
                                            else:
                                                meses = calcula_meses.months
                                            diferenca_dias = calcula_meses.days
                                            if meses and not diferenca_dias:
                                                valor = (Decimal(meses).quantize(TWOPLACES) * valor_da_bolsa.valor).quantize(TWOPLACES)
                                            elif not meses and diferenca_dias:
                                                valor = Decimal((Decimal(diferenca_dias).quantize(TWOPLACES) * valor_da_bolsa.valor) / 30).quantize(TWOPLACES)
                                            else:
                                                valor = (Decimal(meses).quantize(TWOPLACES) * valor_da_bolsa.valor).quantize(TWOPLACES) + Decimal(
                                                    (Decimal(diferenca_dias).quantize(TWOPLACES) * valor_da_bolsa.valor) / 30
                                                ).quantize(TWOPLACES)
                                            somatorio = Decimal(somatorio) + Decimal(valor)
                                        if somatorio:
                                            saldo = Decimal(item.valor).quantize(TWOPLACES) - Decimal(somatorio).quantize(TWOPLACES)
                                        else:
                                            saldo = item.valor
                            if participacoes_por_periodo:
                                relatorio_bolsa.append(
                                    dict(
                                        campus=sigla_campus,
                                        data_inicio=item.data_inicio,
                                        data_termino=item.data_termino,
                                        planejado=item.valor,
                                        quantidade=len(lista_de_bolsas),
                                        categoria=item.categoriabolsa,
                                        somatorio=somatorio,
                                        saldo=saldo,
                                    )
                                )
                                total_planejado = total_planejado + item.valor
                                total_gasto = total_gasto + somatorio
                                total_saldo = total_saldo + saldo
                                total_participacoes = total_participacoes + len(lista_de_bolsas)

    return locals()


@rtr()
@permission_required('ae.pode_detalhar_programa_todos, ae.pode_detalhar_programa_do_campus, ae.change_demandaalunoatendida')
def registrar_atendimento(request, inscricao_id):
    title = 'Registrar Atendimento'

    inscricao = Inscricao.objects.get(pk=inscricao_id)

    if not verificar_permissao_programa(request, inscricao.programa):
        raise PermissionDenied()

    atendimento = DemandaAlunoAtendida()
    atendimento.responsavel_vinculo = request.user.get_vinculo()
    atendimento.programa = inscricao.programa
    atendimento.aluno = inscricao.aluno
    form = DemandaAlunoAtendidaForm(request.POST or None, instance=atendimento, demandas=inscricao.programa.demandas)
    if form.is_valid():
        try:
            form.save()
        except IntegrityError as e:
            if 'ae_demandaalunoatendida_aluno_id_key' in ''.join(e.args):
                return httprr('.', 'Já existe um atendimento do mesmo tipo e data/hora para esse aluno.', 'error')

        return httprr('..', 'Atendimento registrado com sucesso.')

    return locals()


@rtr()
@permission_required('ae.add_agendamentorefeicao')
def remover_agendamento_refeicao(request):
    if not Programa.objects.filter(instituicao=get_uo(request.user), tipo=Programa.TIPO_ALIMENTACAO).exists():
        return httprr('/', 'Seu campus não possui programa de alimentação.', tag='error')
    programa = get_object_or_404(Programa, instituicao=get_uo(request.user), tipo=Programa.TIPO_ALIMENTACAO)
    if not verificar_permissao_programa(request, programa):
        raise PermissionDenied()
    if request.user.has_perm('ae.add_solicitacaoalimentacao'):
        if request.method == 'GET' and 'id' in request.GET:
            agendamento = get_object_or_404(AgendamentoRefeicao, pk=request.GET['id'])
            if agendamento.cancelado:
                raise PermissionDenied
            hoje = datetime.datetime.today()
            if agendamento.data >= datetime.datetime(hoje.year, hoje.month, hoje.day, 0, 0, 0):
                agendamento.cancelado = True
                agendamento.cancelado_em = datetime.datetime.now()
                agendamento.cancelado_por = request.user.get_vinculo()
                agendamento.save()
                return httprr('/admin/ae/agendamentorefeicao/', 'Agendamento cancelado com sucesso.')
            return httprr('/admin/ae/agendamentorefeicao/', 'Só é possível cancelar um Agendamento de Refeição com data maior ou igual a hoje.', 'error')
    return httprr('/admin/ae/agendamentorefeicao/', 'Você não tem permissão de adicionar Agendamento de Refeição.', 'error')


@rtr()
@csrf_exempt
@permission_required('ae.pode_visualizar_auxilios', 'ae.pode_visualizar_auxilios_campus')
def lista_atendidos_auxilios(request):
    title = 'Lista de Atendidos em Auxílios'
    form = ListaAtendidosAuxiliosForm(request.GET or None, request=request)
    if form.is_valid():
        alunos = form.processar()

    return locals()


@rtr()
@csrf_exempt
@permission_required('ae.pode_ver_relatorio_participacao_todos, ae.pode_ver_relatorio_participacao_do_campus')
def lista_participantes_programas(request):
    title = 'Lista de Participantes em Programas'
    form = AlunosProgramaForm(request.GET or None, request=request)

    if form.is_valid():
        cleaned_data = form.cleaned_data
        alunos = None
        campus = cleaned_data.get('campus', None)
        programa = cleaned_data.get('programa', None)
        diretoria = cleaned_data.get('diretoria', None)
        curso = cleaned_data.get('curso', None)
        modalidade = cleaned_data.get('modalidade', None)
        ano = cleaned_data.get('ano', 0)
        mes = cleaned_data.get('mes', 0)
        setores_do_campus = cleaned_data.get('setores_do_campus', None)
        data_inicio = cleaned_data.get('data_inicio', None)
        data_fim = cleaned_data.get('data_fim', None)
        participantes = cleaned_data.get('participantes', None)
        tipo_programa = cleaned_data.get('tipo_programa', None)
        participacao = ultima_part = None

        try:
            page = int(request.GET.get('page', '1'))
        except Exception:
            page = 1

        pagina = 100 * (page - 1)

        alunos = Aluno.objects.filter(inscricao__participacao__isnull=False).distinct()
        if programa:
            alunos = alunos.filter(inscricao__participacao__programa=programa)
        if campus:
            alunos = alunos.filter(curso_campus__diretoria__setor__uo=campus)
        if diretoria:
            alunos = alunos.filter(curso_campus__diretoria=diretoria)
        if curso:
            alunos = alunos.filter(curso_campus=curso)
        if modalidade:
            alunos = alunos.filter(curso_campus__modalidade=modalidade)
        if tipo_programa:
            alunos = alunos.filter(inscricao__participacao__programa__tipo_programa=tipo_programa)

        if setores_do_campus:
            if campus and programa and programa.tipo_programa.sigla == Programa.TIPO_TRABALHO:
                alunos = alunos.filter(id__in=ParticipacaoTrabalho.objects.filter(bolsa_concedida__setor__uo=campus).values_list('participacao__aluno', flat=True))

        SEARCH_QUERY_PARTICIPACAO = None
        SEARCH_QUERY_2 = None
        SEARCH_QUERY_2_PARTICIPACAO = None

        if programa:
            SEARCH_QUERY_1 = Q(inscricao__programa=programa)

        if data_inicio and data_fim:
            SEARCH_QUERY_2 = (
                Q(inscricao__participacao__data_inicio__lte=data_fim, inscricao__participacao__data_inicio__gte=data_inicio)
                | Q(inscricao__participacao__data_termino__lte=data_fim, inscricao__participacao__data_termino__gte=data_inicio)
                | (
                    Q(inscricao__participacao__data_inicio__lt=data_inicio)
                    & (Q(inscricao__participacao__data_termino__gt=data_fim) | Q(inscricao__participacao__data_termino__isnull=True))
                )
            )
        elif data_fim:
            SEARCH_QUERY_2 = Q(inscricao__participacao__data_termino__gt=data_fim) | Q(inscricao__participacao__data_termino__isnull=True)

        elif data_inicio:
            SEARCH_QUERY_2 = Q(inscricao__participacao__data_inicio__lt=data_inicio) & (
                Q(inscricao__participacao__data_termino__gt=data_inicio) | Q(inscricao__participacao__data_termino__isnull=True)
            )

        if programa:
            if SEARCH_QUERY_2:
                alunos = alunos.filter(SEARCH_QUERY_1 & SEARCH_QUERY_2)
            else:
                alunos = alunos.filter(SEARCH_QUERY_1)
        elif SEARCH_QUERY_2:
            alunos = alunos.filter(SEARCH_QUERY_2)

        if programa:
            SEARCH_QUERY_1_PARTICIPACAO = Q(inscricao__programa=programa)

        if data_inicio and data_fim:
            SEARCH_QUERY_2_PARTICIPACAO = (
                Q(data_inicio__lte=data_fim, data_inicio__gte=data_inicio)
                | Q(data_termino__lte=data_fim, data_termino__gte=data_inicio)
                | Q(data_inicio__lt=data_inicio, data_termino__gt=data_fim)
                | (Q(data_inicio__lt=data_inicio) & (Q(data_termino__gt=data_fim) | Q(data_termino__isnull=True)))
            )

        elif data_fim:
            SEARCH_QUERY_2_PARTICIPACAO = Q(data_termino__gt=data_fim) | Q(data_termino__isnull=True)
        elif data_inicio:
            SEARCH_QUERY_2_PARTICIPACAO = Q(data_inicio__lt=data_inicio) & (Q(data_termino__gt=data_inicio) | Q(data_termino__isnull=True))

        if programa:
            if SEARCH_QUERY_2_PARTICIPACAO:
                SEARCH_QUERY_PARTICIPACAO = SEARCH_QUERY_1_PARTICIPACAO & SEARCH_QUERY_2_PARTICIPACAO
            else:
                SEARCH_QUERY_PARTICIPACAO = SEARCH_QUERY_1_PARTICIPACAO
        elif SEARCH_QUERY_2_PARTICIPACAO:
            SEARCH_QUERY_PARTICIPACAO = SEARCH_QUERY_2_PARTICIPACAO

        if participantes:
            alunos = alunos.filter(inscricao__participacao__isnull=False)
            if participantes == AlunosProgramaForm.ATIVOS:
                ids_alunos = list()
                for aluno in alunos:
                    if programa:
                        ultima_part = (
                            aluno.inscricao_set.filter(participacao__isnull=False, programa=programa).exists()
                            and aluno.inscricao_set.filter(participacao__isnull=False, programa=programa).latest('id').get_ultima_participacao()
                        )
                    else:
                        ultima_part = aluno.inscricao_set.filter(participacao__isnull=False).latest('id').get_ultima_participacao()
                    if ultima_part and (not ultima_part.data_termino or ultima_part.data_termino >= date.today()):
                        if programa:
                            if programa == ultima_part.programa:
                                ids_alunos.append(aluno.id)
                        else:
                            ids_alunos.append(aluno.id)
                alunos = alunos.filter(id__in=ids_alunos)

            elif participantes == AlunosProgramaForm.INATIVOS:
                ids_alunos = list()
                for aluno in alunos:
                    if programa:
                        if aluno.inscricao_set.filter(participacao__isnull=False, programa=programa).exists():
                            ultima_part = aluno.inscricao_set.filter(participacao__isnull=False, programa=programa).latest('id').get_ultima_participacao()
                    else:
                        if aluno.inscricao_set.filter(participacao__isnull=False).exists():
                            ultima_part = aluno.inscricao_set.filter(participacao__isnull=False).latest('id').get_ultima_participacao()
                    if ultima_part and ultima_part.data_termino and ultima_part.data_termino < date.today():
                        if programa:
                            if programa == ultima_part.programa:
                                ids_alunos.append(aluno.id)
                        else:
                            ids_alunos.append(aluno.id)

                alunos = alunos.filter(id__in=ids_alunos)

        alunos = alunos.order_by('pessoa_fisica__nome')
        p = Paginator(alunos, 100)
        qs = p.get_page(page).object_list

        if alunos:
            # precarrega a inscrição e a participação
            for aluno in qs:
                if programa:
                    aluno.inscricao = aluno.inscricao_set.filter(programa=programa).latest('data_cadastro').sub_instance()
                else:
                    aluno.inscricao = aluno.inscricao_set.filter(participacao__isnull=False).latest('data_cadastro').sub_instance()
                if SEARCH_QUERY_PARTICIPACAO:
                    participacao = aluno.participacao_set.filter(SEARCH_QUERY_PARTICIPACAO)

                if participacao:
                    aluno.participacao = participacao.latest('data_termino')
                else:
                    aluno.participacao = aluno.inscricao and aluno.inscricao.get_ultima_participacao() or None

        if request.method == 'GET' and 'export_to' in request.GET:
            export_to = request.GET.get('export_to')
            if export_to == 'pdf':
                return alunos_programa_participacao_pdf(request, alunos, programa, modalidade, curso, data_inicio, data_fim)
            elif export_to == 'xls':
                return alunos_programa_participacao_xls(request, alunos, programa)

    return locals()


@permission_required('ae.pode_ver_relatorio_participacao_todos, ae.pode_ver_relatorio_participacao_do_campus')
def alunos_programa_participacao_xls(request, alunos, programa):
    cabecalho = ['#', 'Aluno', 'Matrícula', 'Turma', 'Período']
    if programa:
        if programa.get_tipo() == Programa.TIPO_IDIOMA:
            cabecalho.append('Idioma')
        elif programa.get_tipo() == Programa.TIPO_TRABALHO:
            cabecalho.append('Bolsa')
        elif programa.get_tipo() == Programa.TIPO_TRANSPORTE:
            cabecalho.append('Tipo')
            cabecalho.append('Valor')
        elif programa.get_tipo() == Programa.TIPO_ALIMENTACAO:
            cabecalho.append('Categoria')

            cabecalho.append('Café da manhã')
            cabecalho.append('Almoço')
            cabecalho.append('Jantar')

    dados = [cabecalho]
    count = 0
    for aluno in alunos:
        count += 1
        turma = '-'
        if aluno.get_ultima_matricula_periodo():
            turma = aluno.get_ultima_matricula_periodo().get_codigo_turma()
        dado = [count, aluno.pessoa_fisica.nome, aluno.matricula, turma]
        inicio_periodo = format_(aluno.participacao.data_inicio)
        if aluno.participacao.data_termino:
            fim_periodo = f"a {format_(aluno.participacao.data_termino)}"
        else:
            fim_periodo = "até o momento"

        dado.append(f"{inicio_periodo} a {fim_periodo}")
        participacao_especializada = aluno.participacao.sub_instance()
        if programa:
            if programa.get_tipo() == Programa.TIPO_IDIOMA:
                if participacao_especializada.turma_selecionada:
                    turma = f"{participacao_especializada.turma_selecionada}"
                else:
                    turma = "Não há dados anteriores."

                dado.append(turma)
            elif programa.get_tipo() == Programa.TIPO_TRABALHO:

                if participacao_especializada.bolsa_concedida:
                    bolsa = f"{participacao_especializada.bolsa_concedida}"
                else:
                    bolsa = "Não há dados anteriores."

                dado.append(bolsa)
            elif programa.get_tipo() == Programa.TIPO_TRANSPORTE:

                if participacao_especializada.valor_concedido:
                    tipo = participacao_especializada.get_tipo_passe_concedido_display()
                    valor = participacao_especializada.valor_concedido
                else:
                    tipo = "Não há dados anteriores."
                    valor = "Não há dados anteriores."

                dado.append(tipo)
                dado.append(valor)
            elif programa.get_tipo() == Programa.TIPO_ALIMENTACAO:

                dado.append(participacao_especializada.categoria)
                dado.append('')
                dado.append(participacao_especializada.solicitacao_atendida_cafe)
                dado.append(participacao_especializada.solicitacao_atendida_almoco)
                dado.append(participacao_especializada.solicitacao_atendida_janta)

        dados.append(dado)

    return XlsResponse(rows=dados)


@permission_required('ae.pode_ver_relatorios_todos, ae.pode_ver_relatorios_campus')
def alunos_programa_participacao_pdf(request, alunos, programa, modalidade, curso, data_inicio, data_fim):
    if programa:
        topo = get_topo_pdf(f'Lista de Participantes no {programa}')
    else:
        topo = get_topo_pdf('Lista de Participantes')
    uo = get_uo(request.user)
    servidor = request.user.get_relacionamento()
    periodo = f'{data_inicio} - {data_fim}'
    info = [
        ["Servidor:", f'{servidor} | {uo}'],
        ["Data de Emissão:", format_(datetime.datetime.today())],
        ["Total de alunos participantes:", ' ' + str(alunos.count())],
        ["Modalidade:", modalidade],
        ["Curso:", curso],
        ["Período da Última Participação:", periodo],
    ]
    tabela_info = pdf.table(info, grid=0, w=[30, 160])
    dados = [['Matrícula', 'Aluno', 'Turma', 'Última Participação']]
    for aluno in alunos:
        turma = '-'
        if aluno.get_ultima_matricula_periodo():
            turma = aluno.get_ultima_matricula_periodo().get_codigo_turma()
        dado = [aluno.matricula, aluno.pessoa_fisica.nome, turma]
        inicio_periodo = format_(aluno.participacao.data_inicio)
        if aluno.participacao.data_termino:
            fim_periodo = f"a {format_(aluno.participacao.data_termino)}"
        else:
            fim_periodo = "até o momento"

        periodo = f"{inicio_periodo} a {fim_periodo}"
        participacao_especializada = aluno.participacao.sub_instance()
        if programa:
            if programa.get_tipo() == Programa.TIPO_IDIOMA:
                if participacao_especializada.turma_selecionada:
                    turma = f"{participacao_especializada.turma_selecionada}"
                else:
                    turma = "Não há dados anteriores."

                ultima_participacao = f"<b>Período:</b>{periodo}<br/><b>Idioma:</b>{turma}"
                dado.append(ultima_participacao)

            elif programa.get_tipo() == Programa.TIPO_TRABALHO:
                if participacao_especializada.bolsa_concedida:
                    bolsa = f"{participacao_especializada.bolsa_concedida}"
                else:
                    bolsa = "Não há dados anteriores."

                ultima_participacao = f"<b>Período:</b>{periodo}<br/><b>Bolsa:</b>{bolsa}"
                dado.append(ultima_participacao)

            elif programa.get_tipo() == Programa.TIPO_TRANSPORTE:
                if participacao_especializada.valor_concedido:
                    info = f"<b>Tipo:</b>{participacao_especializada.get_tipo_passe_concedido_display()}<br/><b>Valor:</b>R$ {participacao_especializada.valor_concedido}"
                else:
                    info = "<b>Informações:</b>Não há dados anteriores."

                ultima_participacao = f"<b>Período:</b>{periodo}<br/>{info}"
                dado.append(ultima_participacao)

            elif programa.get_tipo() == Programa.TIPO_ALIMENTACAO:
                categoria = participacao_especializada.categoria
                solicitacao_atendida_cafe = participacao_especializada.solicitacao_atendida_cafe
                solicitacao_atendida_almoco = participacao_especializada.solicitacao_atendida_almoco
                solicitacao_atendida_janta = participacao_especializada.solicitacao_atendida_janta
                if (
                    categoria
                    or (solicitacao_atendida_cafe and solicitacao_atendida_cafe.valida())
                    or (solicitacao_atendida_almoco and solicitacao_atendida_almoco.valida())
                    or (solicitacao_atendida_janta and solicitacao_atendida_janta.valida())
                ):
                    info = ""
                    if categoria:
                        info += f"<b>Categoria:</b>{categoria}"
                        if (
                            (solicitacao_atendida_cafe and solicitacao_atendida_cafe.valida())
                            or (solicitacao_atendida_almoco and solicitacao_atendida_almoco.valida())
                            or (solicitacao_atendida_janta and solicitacao_atendida_janta.valida())
                        ):
                            info += "<br/>"
                    if solicitacao_atendida_cafe and solicitacao_atendida_cafe.valida():
                        info += f"<b>Café da manhã:</b>{solicitacao_atendida_cafe}"
                        if (solicitacao_atendida_almoco and solicitacao_atendida_almoco.valida()) or (solicitacao_atendida_janta and solicitacao_atendida_janta.valida()):
                            info += "<br/>"
                    if solicitacao_atendida_almoco and solicitacao_atendida_almoco.valida():
                        info += f"<b>Almoço:</b>{solicitacao_atendida_almoco}"
                        if solicitacao_atendida_janta and solicitacao_atendida_janta.valida():
                            info += "<br/>"
                    if solicitacao_atendida_janta and solicitacao_atendida_janta.valida():
                        info += f"<b>Jantar:</b>{solicitacao_atendida_janta}"
                else:
                    info = "<b>Informações:</b>Não há dados anteriores."

                ultima_participacao = f"<b>Período:</b>{periodo}<br/>{info}"
                dado.append(ultima_participacao)
            else:
                ultima_participacao = f"<b>Período:</b>{periodo}<br/>"
                dado.append(ultima_participacao)
        else:
            ultima_participacao = f"<b>Período:</b>{periodo}<br/>"
            dado.append(ultima_participacao)
        dados.append(dado)

    tabela_dados = pdf.table(dados, head=1, zebra=1, w=[27, 68, 30, 65], count=1)
    body = topo + [tabela_info, pdf.space(8), tabela_dados]

    return PDFResponse(pdf.PdfReport(body=body).generate())


def get_query_estatistica(form):
    _QUERY = Q()
    if form.is_valid():

        if str(form.cleaned_data['situacao_matricula']) == 'Ativo':
            _QUERY = _QUERY & Q(situacao__ativo=True)
        elif str(form.cleaned_data['situacao_matricula']) == 'Inativo':
            _QUERY = _QUERY & Q(situacao__ativo=False)
        if form.cleaned_data['campus']:
            _QUERY = _QUERY & Q(curso_campus__diretoria__setor__uo=form.cleaned_data['campus'])
        if form.cleaned_data['modalidade']:
            _QUERY = _QUERY & Q(curso_campus__modalidade=form.cleaned_data['modalidade'])

        if form.cleaned_data['inscricao_situacao'] == '2':
            _QUERY = _QUERY & Q(inscricao__isnull=True)

        elif form.cleaned_data['inscricao_situacao'] == '1':
            _QUERY = _QUERY & Q(inscricao__isnull=False)

        if form.cleaned_data['programa'] and form.cleaned_data['inscricao_situacao'] == '1':
            _QUERY = _QUERY & Q(inscricao__programa=form.cleaned_data['programa'])

        if form.cleaned_data['participacao_situacao'] == '2':
            _QUERY = _QUERY & Q(participacao__isnull=True)

        elif form.cleaned_data['participacao_situacao'] == '1':
            _QUERY = _QUERY & Q(participacao__isnull=False)
        elif form.cleaned_data['participacao_situacao'] == '4':
            _QUERY = _QUERY & Q(participacao__isnull=False, participacao__id__in=Participacao.abertas.all().values_list('id'))

        if form.cleaned_data['participantes'] and (form.cleaned_data['participacao_situacao'] == '1' or form.cleaned_data['participacao_situacao'] == '4'):
            _QUERY = _QUERY & Q(participacao__programa=form.cleaned_data['participantes'])

        if form.cleaned_data['diretoria']:
            _QUERY = _QUERY & Q(curso_campus__diretoria=form.cleaned_data['diretoria'])

        if form.cleaned_data['curso']:
            _QUERY = _QUERY & Q(curso_campus=form.cleaned_data['curso'])

        if form.cleaned_data['turma']:
            _QUERY = _QUERY & Q(matriculaperiodo__matriculadiario__diario__turma=form.cleaned_data['turma'])

        if form.cleaned_data['ano'] and form.cleaned_data['ano'] != 'Todos':
            _QUERY = _QUERY & Q(data_matricula__year=int(form.cleaned_data['ano']))
        if form.cleaned_data['ano_letivo'] and form.cleaned_data['ano_letivo'] != 'Todos':
            _QUERY = _QUERY & Q(matriculaperiodo__ano_letivo__ano=form.cleaned_data['ano_letivo'])

    return _QUERY


@rtr()
@permission_required('ae.pode_ver_relatorio_caracterizacao_todos, ae.pode_ver_relatorio_caracterizacao_do_campus')
def estatisticas_caracterizacao_dados_pessoais(request):
    title = 'Relatório da Caracterização Socioeconômica - Dados Pessoais'
    form = EstatisticasCaracterizacaoForm(request.GET or None, request=request)
    if form.is_valid():
        dados = list()
        alunos_total = Aluno.objects.filter(get_query_estatistica(form)).distinct()
        if not form.cleaned_data['incluir_fic']:
            alunos_total = alunos_total.exclude(curso_campus__modalidade__pk__in=[Modalidade.FIC, Modalidade.PROEJA_FIC_FUNDAMENTAL])
        alunos_caracterizados = alunos_total.filter(caracterizacao__isnull=False)
        if alunos_caracterizados:
            caracterizacao_dos_alunos = Caracterizacao.objects.filter(aluno__in=alunos_caracterizados.values_list('id'))
            alunos_nao_caracterizados = alunos_total.count() - alunos_caracterizados.count()
            dados.append(["Alunos com Caracterização", alunos_caracterizados.count()])
            dados.append(["Alunos sem Caracterização", alunos_nao_caracterizados])
            grafico1 = PieChart('grafico1', title='Alunos Caracterizados', subtitle='Total de Alunos Caracterizados', minPointLength=0, data=dados)
            setattr(grafico1, 'id', 'grafico1')

            dados2 = list()
            alunos_masculino = alunos_caracterizados.filter(pessoa_fisica__sexo='M')
            alunos_feminino = alunos_caracterizados.filter(pessoa_fisica__sexo='F')
            dados2.append(["Masculino", alunos_masculino.count()])
            dados2.append(["Feminino", alunos_feminino.count()])
            diferenca = alunos_caracterizados.count() - alunos_masculino.count() - alunos_feminino.count()
            if diferenca > 0:
                dados2.append(["Não Informado", diferenca])
            grafico2 = PieChart('grafico2', title='Sexo', subtitle='Total de Alunos por Sexo', minPointLength=0, data=dados2)
            setattr(grafico2, 'id', 'grafico2')

            dados3 = list()
            alunos_por_raca = caracterizacao_dos_alunos.values('raca__descricao').annotate(qtd=Count('raca__descricao')).order_by('raca__descricao')
            total_raca = 0
            for registro in alunos_por_raca:
                dados3.append([registro['raca__descricao'], registro['qtd']])
                total_raca = total_raca + registro['qtd']
            if dados3[-1][1] == 0:
                dados3.pop()
            if alunos_caracterizados.count() - total_raca > 0:
                dados3.append(["Não Informado", alunos_caracterizados.count() - total_raca])
            grafico3 = PieChart('grafico3', title='Raça', subtitle='Total de Alunos por Raça', minPointLength=0, data=dados3)
            setattr(grafico3, 'id', 'grafico3')

            dados4 = list()
            alunos_por_necessidade_especial = (
                caracterizacao_dos_alunos.values('necessidade_especial__descricao')
                .annotate(qtd=Count('necessidade_especial__descricao'))
                .order_by('necessidade_especial__descricao')
            )
            total_necessidade = 0
            for registro in alunos_por_necessidade_especial:
                dados4.append([registro['necessidade_especial__descricao'], registro['qtd']])
                total_necessidade = total_necessidade + registro['qtd']
            if dados4[-1][1] == 0:
                dados4.pop()
            if alunos_caracterizados.count() - total_necessidade > 0:
                dados4.append(["Nenhuma", alunos_caracterizados.count() - total_necessidade])
            grafico4 = PieChart(
                'grafico4',
                title='Deficiências/Necessidades Educacionais Especiais',
                subtitle='Total de Alunos por Deficiências/Necessidades Educacionais Especiais',
                minPointLength=0,
                data=dados4,
            )
            setattr(grafico4, 'id', 'grafico4')

            dados5 = list()
            alunos_por_estado_civil = caracterizacao_dos_alunos.values('estado_civil__descricao').annotate(qtd=Count('estado_civil__descricao')).order_by('estado_civil__descricao')
            total_estado_civil = 0
            for registro in alunos_por_estado_civil:
                dados5.append([registro['estado_civil__descricao'], registro['qtd']])
                total_estado_civil = total_estado_civil + registro['qtd']
            if dados5[-1][1] == 0:
                dados5.pop()
            if alunos_caracterizados.count() - total_estado_civil > 0:
                dados5.append(["Não Informado", alunos_caracterizados.count() - total_estado_civil])
            grafico5 = PieChart('grafico5', title='Estado Civil', subtitle='Total de Alunos por Estado Civil', minPointLength=0, data=dados5)
            setattr(grafico5, 'id', 'grafico5')

            dados6 = list()
            alunos_por_municipio = caracterizacao_dos_alunos.values('aluno__cidade__nome').annotate(qtd=Count('aluno__cidade__nome')).order_by('aluno__cidade__nome')
            total_municipio = 0
            for registro in alunos_por_municipio:
                dados6.append([registro['aluno__cidade__nome'], registro['qtd']])
                total_municipio = total_municipio + registro['qtd']
            if dados6[-1][1] == 0:
                dados6.pop()
            if alunos_caracterizados.count() - total_municipio > 0:
                dados6.append(["Não Informado", alunos_caracterizados.count() - total_municipio])
            grafico6 = PieChart('grafico6', title='Município', subtitle='Total de Alunos por Município', minPointLength=0, data=dados6)
            setattr(grafico6, 'id', 'grafico6')

            dados7 = list()
            alunos_qtd_filhos = caracterizacao_dos_alunos.values('qtd_filhos').annotate(qtd=Count('qtd_filhos')).order_by('qtd_filhos')
            total_filhos = 0
            for registro in alunos_qtd_filhos:
                dados7.append([str(registro['qtd_filhos']), registro['qtd']])
                total_filhos = total_filhos + registro['qtd']
            if dados7[-1][1] == 0:
                dados7.pop()
            if alunos_caracterizados.count() - total_filhos > 0:
                dados7.append(["Não Informado", alunos_caracterizados.count() - total_filhos])
            grafico7 = PieChart('grafico7', title='Quantidade de Filhos', subtitle='Total de Alunos por Número de Filhos', minPointLength=0, data=dados7)
            setattr(grafico7, 'id', 'grafico7')

            dados8 = list()
            alunos_tipo_serv_saude = (
                caracterizacao_dos_alunos.values('tipo_servico_saude__descricao').annotate(qtd=Count('tipo_servico_saude__descricao')).order_by('tipo_servico_saude__descricao')
            )
            total_serv_saude = 0
            for registro in alunos_tipo_serv_saude:
                dados8.append([registro['tipo_servico_saude__descricao'], registro['qtd']])
                total_serv_saude = total_serv_saude + registro['qtd']
            if dados8[-1][1] == 0:
                dados8.pop()
            if alunos_caracterizados.count() - total_serv_saude > 0:
                dados8.append(["Não Informado", alunos_caracterizados.count() - total_serv_saude])

            grafico8 = PieChart('grafico8', title='Serviço de Saúde', subtitle='Total de Alunos por Serviço de Saúde', minPointLength=0, data=dados8)
            setattr(grafico8, 'id', 'grafico8')

            dados9 = list()
            hoje = datetime.datetime.now()
            ATE_14 = alunos_caracterizados.filter(pessoa_fisica__nascimento_data__gte=date(hoje.year - 14, hoje.month, hoje.day))
            ENTRE_15_17 = alunos_caracterizados.filter(
                pessoa_fisica__nascimento_data__lt=date(hoje.year - 14, hoje.month, hoje.day), pessoa_fisica__nascimento_data__gte=date(hoje.year - 17, hoje.month, hoje.day)
            )
            ENTRE_18_29 = alunos_caracterizados.filter(
                pessoa_fisica__nascimento_data__lt=date(hoje.year - 17, hoje.month, hoje.day), pessoa_fisica__nascimento_data__gte=date(hoje.year - 29, hoje.month, hoje.day)
            )
            ENTRE_30_49 = alunos_caracterizados.filter(
                pessoa_fisica__nascimento_data__lt=date(hoje.year - 29, hoje.month, hoje.day), pessoa_fisica__nascimento_data__gte=date(hoje.year - 49, hoje.month, hoje.day)
            )
            ACIMA_50 = alunos_caracterizados.filter(pessoa_fisica__nascimento_data__lt=date(hoje.year - 49, hoje.month, hoje.day))
            NAO_INFORMADO = alunos_caracterizados.filter(pessoa_fisica__nascimento_data__isnull=True)
            dados9.append(["Até 14 anos", ATE_14.count()])
            dados9.append(["Entre 15 e 17 anos", ENTRE_15_17.count()])
            dados9.append(["Entre 18 e 29 anos", ENTRE_18_29.count()])
            dados9.append(["Entre 30 e 49 anos", ENTRE_30_49.count()])
            dados9.append(["Acima de 50 anos", ACIMA_50.count()])
            dados9.append(["Não informado", NAO_INFORMADO.count()])
            grafico9 = PieChart('grafico9', title='Faixa Etária', subtitle='Total de Alunos por Faixa Etária', minPointLength=0, data=dados9)
            setattr(grafico9, 'id', 'grafico9')

            pie_chart_list_dados_pessoais = [grafico1, grafico2, grafico3, grafico4, grafico5, grafico6, grafico7, grafico8, grafico9]

    return locals()


@rtr()
@permission_required('ae.pode_ver_relatorio_caracterizacao_todos, ae.pode_ver_relatorio_caracterizacao_do_campus')
def estatisticas_caracterizacao_dados_educacionais(request):
    title = 'Relatório da Caracterização Socioeconômica - Dados Educacionais'
    form = EstatisticasCaracterizacaoForm(request.GET or None, request=request)
    if form.is_valid():
        alunos_total = Aluno.objects.filter(get_query_estatistica(form)).distinct()
        if not form.cleaned_data['incluir_fic']:
            alunos_total = alunos_total.exclude(curso_campus__modalidade__pk__in=[Modalidade.FIC, Modalidade.PROEJA_FIC_FUNDAMENTAL])
        alunos_caracterizados = alunos_total.filter(caracterizacao__isnull=False)
        if alunos_caracterizados:
            caracterizacao_dos_alunos = Caracterizacao.objects.filter(aluno__in=alunos_caracterizados.values_list('id'))
            dados = list()
            ensino_fundamental = (
                caracterizacao_dos_alunos.values('escola_ensino_fundamental__descricao')
                .annotate(qtd=Count('escola_ensino_fundamental__descricao'))
                .order_by('escola_ensino_fundamental__descricao')
            )
            total_ensino_fundamental = 0
            for registro in ensino_fundamental:
                dados.append([registro['escola_ensino_fundamental__descricao'], registro['qtd']])
                total_ensino_fundamental = total_ensino_fundamental + registro['qtd']
            if dados[-1][1] == 0:
                dados.pop()
            if alunos_caracterizados.count() - total_ensino_fundamental > 0:
                dados.append(["Não Informado", alunos_caracterizados.count() - total_ensino_fundamental])
            grafico1 = PieChart('grafico1', title='Ensino Fundamental', subtitle='Tipo de Escola que cursou o Ensino Fundamental', minPointLength=0, data=dados)
            setattr(grafico1, 'id', 'grafico1')

            dados2 = list()
            ensino_medio = (
                caracterizacao_dos_alunos.values('escola_ensino_medio__descricao').annotate(qtd=Count('escola_ensino_medio__descricao')).order_by('escola_ensino_medio__descricao')
            )
            total_ensino_medio = 0
            for registro in ensino_medio:
                dados2.append([registro['escola_ensino_medio__descricao'], registro['qtd']])
                total_ensino_medio = total_ensino_medio + registro['qtd']
            if dados2[-1][1] == 0:
                dados2.pop()
            if alunos_caracterizados.count() - total_ensino_medio > 0:
                dados2.append(["Não Informado", alunos_caracterizados.count() - total_ensino_medio])
            grafico2 = PieChart('grafico2', title='Ensino Médio', subtitle='Tipo de Escola que cursou o Ensino Médio', minPointLength=0, data=dados2)
            setattr(grafico2, 'id', 'grafico2')

            dados3 = list()
            motivo_ausencia = (
                caracterizacao_dos_alunos.values('razao_ausencia_educacional__descricao')
                .annotate(qtd=Count('razao_ausencia_educacional__descricao'))
                .order_by('razao_ausencia_educacional__descricao')
            )
            total_motivo_ausencia = 0
            for registro in motivo_ausencia:
                dados3.append([registro['razao_ausencia_educacional__descricao'], registro['qtd']])
                total_motivo_ausencia = total_motivo_ausencia + registro['qtd']
            if dados3[-1][1] == 0:
                dados3.pop()
            if alunos_caracterizados.count() - total_motivo_ausencia > 0:
                dados3.append(["Não teve ausência", alunos_caracterizados.count() - total_motivo_ausencia])
            grafico3 = PieChart('grafico3', title='Motivo da Ausência Escolar', subtitle='Total de Alunos por Motivo de Ausência Escolar', minPointLength=0, data=dados3)
            setattr(grafico3, 'id', 'grafico3')

            dados4 = list()
            conhecimento_idioma = (
                caracterizacao_dos_alunos.values('idiomas_conhecidos__descricao').annotate(qtd=Count('idiomas_conhecidos__descricao')).order_by('idiomas_conhecidos__descricao')
            )
            for registro in conhecimento_idioma:
                dados4.append([registro['idiomas_conhecidos__descricao'], registro['qtd']])
            if dados4[-1][1] == 0:
                dados4.pop()
            dados4.append(['Não conhece outro idioma', caracterizacao_dos_alunos.filter(possui_conhecimento_idiomas=False).count()])
            dados4.append(['Não informado se conhece outro idioma', caracterizacao_dos_alunos.filter(possui_conhecimento_idiomas__isnull=True).count()])
            dados4.append(['Não informado o idioma conhecido', caracterizacao_dos_alunos.filter(possui_conhecimento_idiomas=True, idiomas_conhecidos__isnull=True).count()])
            grafico4 = PieChart('grafico4', title='Conhecimento em Idiomas', subtitle='Total de Alunos por Idiomas Conhecidos', minPointLength=0, data=dados4)
            setattr(grafico4, 'id', 'grafico4')

            dados5 = list()
            dados5.append(['Não', caracterizacao_dos_alunos.filter(possui_conhecimento_informatica=False).count()])
            dados5.append(['Sim', caracterizacao_dos_alunos.filter(possui_conhecimento_informatica=True).count()])
            dados5.append(['Não informado', caracterizacao_dos_alunos.filter(possui_conhecimento_informatica__isnull=True).count()])
            grafico5 = PieChart('grafico5', title='Conhecimento em Informática', subtitle='Total de Alunos por Conhecimento em Informática', minPointLength=0, data=dados5)
            setattr(grafico5, 'id', 'grafico5')

            pie_chart_list_dados_educacionais = [grafico1, grafico2, grafico3, grafico4, grafico5]

    return locals()


@rtr()
@permission_required('ae.pode_ver_relatorio_caracterizacao_todos, ae.pode_ver_relatorio_caracterizacao_do_campus')
def estatisticas_caracterizacao_dados_familiares(request):
    title = 'Relatório da Caracterização Socioeconômica - Dados Familiares e Socioeconômicos'
    form = EstatisticasCaracterizacaoForm(request.GET or None, request=request)
    if form.is_valid():
        alunos_total = Aluno.objects.filter(get_query_estatistica(form)).distinct()
        if not form.cleaned_data['incluir_fic']:
            alunos_total = alunos_total.exclude(curso_campus__modalidade__pk__in=[Modalidade.FIC, Modalidade.PROEJA_FIC_FUNDAMENTAL])
        alunos_caracterizados = alunos_total.filter(caracterizacao__isnull=False)
        if alunos_caracterizados:
            caracterizacao_dos_alunos = Caracterizacao.objects.filter(aluno__in=alunos_caracterizados.values_list('id'))
            dados = list()
            situacao_trabalho = (
                caracterizacao_dos_alunos.values('trabalho_situacao__descricao').annotate(qtd=Count('trabalho_situacao__descricao')).order_by('trabalho_situacao__descricao')
            )
            total_situacao_trabalho = 0
            for registro in situacao_trabalho:
                dados.append([registro['trabalho_situacao__descricao'], registro['qtd']])
                total_situacao_trabalho = total_situacao_trabalho + registro['qtd']
            if dados[-1][1] == 0:
                dados.pop()
            if alunos_caracterizados.count() - total_situacao_trabalho > 0:
                dados.append(["Não Informado", alunos_caracterizados.count() - total_situacao_trabalho])
            grafico1 = PieChart('grafico1', title='Situação de Trabalho', subtitle='Total de Alunos por Situação de Trabalho', minPointLength=0, data=dados)
            setattr(grafico1, 'id', 'grafico1')

            dados2 = list()
            meio_transporte = (
                caracterizacao_dos_alunos.values('meio_transporte_utilizado__descricao')
                .annotate(qtd=Count('meio_transporte_utilizado__descricao'))
                .order_by('meio_transporte_utilizado__descricao')
            )
            total_meio_transporte = 0
            for registro in meio_transporte:
                dados2.append([registro['meio_transporte_utilizado__descricao'], registro['qtd']])
                total_meio_transporte = total_meio_transporte + registro['qtd']
            if dados2[-1][1] == 0:
                dados2.pop()
            if alunos_caracterizados.count() - total_meio_transporte > 0:
                dados2.append(["Não Informado", alunos_caracterizados.count() - total_meio_transporte])
            grafico2 = PieChart('grafico2', title='Meio de Transporte', subtitle='Total de Alunos por Meio de Transporte', minPointLength=0, data=dados2)
            setattr(grafico2, 'id', 'grafico2')

            dados3 = list()
            contribuintes_financeiros = (
                caracterizacao_dos_alunos.values('contribuintes_renda_familiar__descricao')
                .annotate(qtd=Count('contribuintes_renda_familiar__descricao'))
                .order_by('contribuintes_renda_familiar__descricao')
            )
            total_contribuintes_financeiros = 0
            for registro in contribuintes_financeiros:
                dados3.append([registro['contribuintes_renda_familiar__descricao'], registro['qtd']])
                total_contribuintes_financeiros = total_contribuintes_financeiros + registro['qtd']
            if dados3[-1][1] == 0:
                dados3.pop()
            if alunos_caracterizados.count() - total_contribuintes_financeiros > 0:
                dados3.append(["Não Informado", alunos_caracterizados.count() - total_contribuintes_financeiros])
            grafico3 = PieChart(
                'grafico3', title='Contribuintes para a Renda Familiar', subtitle='Total de Alunos por Contribuintes para a Renda Familiar', minPointLength=0, data=dados3
            )
            setattr(grafico3, 'id', 'grafico3')

            dados4 = list()
            responsavel_financeiro = (
                caracterizacao_dos_alunos.values('responsavel_financeiro__descricao')
                .annotate(qtd=Count('responsavel_financeiro__descricao'))
                .order_by('responsavel_financeiro__descricao')
            )
            total_responsavel_financeiro = 0
            for registro in responsavel_financeiro:
                dados4.append([registro['responsavel_financeiro__descricao'], registro['qtd']])
                total_responsavel_financeiro = total_responsavel_financeiro + registro['qtd']
            if dados4[-1][1] == 0:
                dados4.pop()
            if alunos_caracterizados.count() - total_responsavel_financeiro > 0:
                dados4.append(["Não Informado", alunos_caracterizados.count() - total_responsavel_financeiro])
            grafico4 = PieChart('grafico4', title='Responsável Financeiro', subtitle='Total de Alunos por Responsável Financeiro', minPointLength=0, data=dados4)
            setattr(grafico4, 'id', 'grafico4')

            dados5 = list()
            situacao_trabalho_responsavel_financeiro = (
                caracterizacao_dos_alunos.values('responsavel_financeir_trabalho_situacao__descricao')
                .annotate(qtd=Count('responsavel_financeir_trabalho_situacao__descricao'))
                .order_by('responsavel_financeir_trabalho_situacao__descricao')
            )
            total_situacao_trabalho_responsavel_financeiro = 0
            for registro in situacao_trabalho_responsavel_financeiro:
                dados5.append([registro['responsavel_financeir_trabalho_situacao__descricao'], registro['qtd']])
                total_situacao_trabalho_responsavel_financeiro = total_situacao_trabalho_responsavel_financeiro + registro['qtd']
            if dados5[-1][1] == 0:
                dados5.pop()
            if alunos_caracterizados.count() - total_situacao_trabalho_responsavel_financeiro > 0:
                dados5.append(["Não Informado", alunos_caracterizados.count() - total_situacao_trabalho_responsavel_financeiro])
            grafico5 = PieChart(
                'grafico5',
                title='Situação de Trabalho do Responsável Financeiro',
                subtitle='Total de Alunos por Situação de Trabalho do Responsável Financeiro',
                minPointLength=0,
                data=dados5,
            )
            setattr(grafico5, 'id', 'grafico5')

            dados6 = list()
            responsavel_financeiro_nivel_escolaridade = (
                caracterizacao_dos_alunos.values('responsavel_financeiro_nivel_escolaridade__descricao')
                .annotate(qtd=Count('responsavel_financeiro_nivel_escolaridade__descricao'))
                .order_by('responsavel_financeiro_nivel_escolaridade__descricao')
            )
            total_responsavel_financeiro_nivel_escolaridade = 0
            for registro in responsavel_financeiro_nivel_escolaridade:
                dados6.append([registro['responsavel_financeiro_nivel_escolaridade__descricao'], registro['qtd']])
                total_responsavel_financeiro_nivel_escolaridade = total_responsavel_financeiro_nivel_escolaridade + registro['qtd']
            if dados6[-1][1] == 0:
                dados6.pop()
            if alunos_caracterizados.count() - total_responsavel_financeiro_nivel_escolaridade > 0:
                dados6.append(["Não Informado", alunos_caracterizados.count() - total_responsavel_financeiro_nivel_escolaridade])
            grafico6 = PieChart(
                'grafico6',
                title='Nível de Escolaridade do Principal Responsável Financeiro',
                subtitle='Total de Alunos por Nível de Escolaridade do Principal Responsável Financeiro',
                minPointLength=0,
                data=dados6,
            )
            setattr(grafico6, 'id', 'grafico6')

            dados7 = list()
            nivel_escolaridade_pai = (
                caracterizacao_dos_alunos.values('pai_nivel_escolaridade__descricao')
                .annotate(qtd=Count('pai_nivel_escolaridade__descricao'))
                .order_by('pai_nivel_escolaridade__descricao')
            )
            total_nivel_escolaridade_pai = 0
            for registro in nivel_escolaridade_pai:
                dados7.append([registro['pai_nivel_escolaridade__descricao'], registro['qtd']])
                total_nivel_escolaridade_pai = total_nivel_escolaridade_pai + registro['qtd']
            if dados7[-1][1] == 0:
                dados7.pop()
            if alunos_caracterizados.count() - total_nivel_escolaridade_pai > 0:
                dados7.append(["Não Informado", alunos_caracterizados.count() - total_nivel_escolaridade_pai])
            grafico7 = PieChart('grafico7', title='Nível de Escolaridade (Pai)', subtitle='Total de Alunos por Nível de Escolaridade (Pai)', minPointLength=0, data=dados7)
            setattr(grafico7, 'id', 'grafico7')

            dados8 = list()
            nivel_escolaridade_mae = (
                caracterizacao_dos_alunos.values('mae_nivel_escolaridade__descricao')
                .annotate(qtd=Count('mae_nivel_escolaridade__descricao'))
                .order_by('mae_nivel_escolaridade__descricao')
            )
            total_nivel_escolaridade_mae = 0
            for registro in nivel_escolaridade_mae:
                dados8.append([registro['mae_nivel_escolaridade__descricao'], registro['qtd']])
                total_nivel_escolaridade_mae = total_nivel_escolaridade_mae + registro['qtd']
            if dados8[-1][1] == 0:
                dados8.pop()
            if alunos_caracterizados.count() - total_nivel_escolaridade_mae > 0:
                dados8.append(["Não Informado", alunos_caracterizados.count() - total_nivel_escolaridade_mae])
            grafico8 = PieChart('grafico8', title='Nível de Escolaridade (Mãe)', subtitle='Total de Alunos por Nível de Escolaridade (Mãe)', minPointLength=0, data=dados8)
            setattr(grafico8, 'id', 'grafico8')

            dados9 = list()
            dados9.append(['Até R$500', caracterizacao_dos_alunos.filter(renda_bruta_familiar__lte=500).count()])
            dados9.append(['Entre R$500 e R$1000', caracterizacao_dos_alunos.filter(renda_bruta_familiar__gt=500, renda_bruta_familiar__lte=1000).count()])
            dados9.append(['Entre R$1000 e R$2000', caracterizacao_dos_alunos.filter(renda_bruta_familiar__gt=1000, renda_bruta_familiar__lte=2000).count()])
            dados9.append(['Maior que R$2000', caracterizacao_dos_alunos.filter(renda_bruta_familiar__gt=2000).count()])
            grafico9 = PieChart('grafico9', title='Renda Bruta Familiar', subtitle='Total de Alunos por Renda Bruta Familiar', minPointLength=0, data=dados9)
            setattr(grafico9, 'id', 'grafico9')

            dados10 = list()
            sm = Decimal(Configuracao.get_valor_por_chave('comum', 'salario_minimo'))
            dados10.append(
                [
                    'Maior que 5 SM',
                    caracterizacao_dos_alunos.filter(~Q(qtd_pessoas_domicilio=0)).extra(where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > ({sm} * 5)']).count(),
                ]
            )
            dados10.append(['Não informado', caracterizacao_dos_alunos.filter(qtd_pessoas_domicilio=0).count()])
            dados10.append(
                [
                    'Até ½ SM',
                    caracterizacao_dos_alunos.filter(~Q(qtd_pessoas_domicilio=0)).extra(where=[f'renda_bruta_familiar/qtd_pessoas_domicilio <= {sm}/2']).count(),
                ]
            )
            for qtd_inicial in [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5]:
                if qtd_inicial % 1 == 0:
                    label = f'Entre {qtd_inicial} SM e {qtd_inicial} ½ SM'
                else:
                    label = 'Entre {} ½ SM e {} SM'.format(int(qtd_inicial - 0.5) if int(qtd_inicial - 0.5) else '', int(qtd_inicial + 0.5))
                # convertendo qtd_inicial para string por causa do erro que estava dando no gunicorn e nginx
                inicial = Decimal(str(qtd_inicial)) * sm
                final = (Decimal(str(qtd_inicial)) + Decimal("0.5")) * sm
                dados10.append(
                    [
                        label,
                        caracterizacao_dos_alunos.filter(~Q(qtd_pessoas_domicilio=0))
                        .extra(
                            where=[
                                'renda_bruta_familiar/qtd_pessoas_domicilio > ({inicial}) AND renda_bruta_familiar/qtd_pessoas_domicilio <= ({final})'.format(
                                    inicial=inicial, final=final
                                )
                            ]
                        )
                        .count(),
                    ]
                )
            grafico10 = PieChart('grafico10', title='Renda Per Capita', subtitle='Total de Alunos por Per Capita com base no salário mínimo (SM)', minPointLength=0, data=dados10)
            setattr(grafico10, 'id', 'grafico10')

            dados11 = list()
            companhia_domiciliar = (
                caracterizacao_dos_alunos.values('companhia_domiciliar__descricao')
                .annotate(qtd=Count('companhia_domiciliar__descricao'))
                .order_by('companhia_domiciliar__descricao')
            )
            total_companhia_domiciliar = 0
            for registro in companhia_domiciliar:
                dados11.append([registro['companhia_domiciliar__descricao'], registro['qtd']])
                total_companhia_domiciliar = total_companhia_domiciliar + registro['qtd']
            if dados11[-1][1] == 0:
                dados11.pop()
            if alunos_caracterizados.count() - total_companhia_domiciliar > 0:
                dados11.append(["Não Informado", alunos_caracterizados.count() - total_companhia_domiciliar])
            grafico11 = PieChart('grafico11', title='Companhia Domiciliar', subtitle='Total de Alunos por Companhia Domiciliar', minPointLength=0, data=dados11)
            setattr(grafico11, 'id', 'grafico11')

            dados12 = list()
            numero_pessoas_domicilio = caracterizacao_dos_alunos.values('qtd_pessoas_domicilio').annotate(qtd=Count('qtd_pessoas_domicilio')).order_by('qtd_pessoas_domicilio')
            total_numero_pessoas_domicilio = 0
            for registro in numero_pessoas_domicilio:
                dados12.append([str(registro['qtd_pessoas_domicilio']), registro['qtd']])
                total_numero_pessoas_domicilio = total_numero_pessoas_domicilio + registro['qtd']
            if dados12[-1][1] == 0:
                dados12.pop()
            if alunos_caracterizados.count() - total_numero_pessoas_domicilio > 0:
                dados6.append(["Não Informado", alunos_caracterizados.count() - total_numero_pessoas_domicilio])
            grafico12 = PieChart('grafico12', title='Número de Pessoas no Domicílio', subtitle='Total de Alunos por Número de Pessoas no Domicílio', minPointLength=0, data=dados12)
            setattr(grafico12, 'id', 'grafico12')

            dados13 = list()
            tipo_imovel = (
                caracterizacao_dos_alunos.values('tipo_imovel_residencial__descricao')
                .annotate(qtd=Count('tipo_imovel_residencial__descricao'))
                .order_by('tipo_imovel_residencial__descricao')
            )
            total_tipo_imovel = 0
            for registro in tipo_imovel:
                dados13.append([registro['tipo_imovel_residencial__descricao'], registro['qtd']])
                total_tipo_imovel = total_tipo_imovel + registro['qtd']
            if dados13[-1][1] == 0:
                dados13.pop()
            if alunos_caracterizados.count() - total_tipo_imovel > 0:
                dados13.append(["Não Informado", alunos_caracterizados.count() - total_tipo_imovel])
            grafico13 = PieChart('grafico13', title='Tipo de Imóvel', subtitle='Total de Alunos por Tipo de Imóvel', minPointLength=0, data=dados13)
            setattr(grafico13, 'id', 'grafico13')

            dados14 = list()
            tipo_zona_residencial = (
                caracterizacao_dos_alunos.values('tipo_area_residencial__descricao')
                .annotate(qtd=Count('tipo_area_residencial__descricao'))
                .order_by('tipo_area_residencial__descricao')
            )
            total_tipo_zona_residencial = 0
            for registro in tipo_zona_residencial:
                dados14.append([registro['tipo_area_residencial__descricao'], registro['qtd']])
                total_tipo_zona_residencial = total_tipo_zona_residencial + registro['qtd']
            if dados14[-1][1] == 0:
                dados14.pop()
            if alunos_caracterizados.count() - total_tipo_zona_residencial > 0:
                dados14.append(["Não Informado", alunos_caracterizados.count() - total_tipo_zona_residencial])
            grafico14 = PieChart('grafico14', title='Tipo de Zona Residencial', subtitle='Total de Alunos por Tipo de Zona Residencial', minPointLength=0, data=dados14)
            setattr(grafico14, 'id', 'grafico14')

            dados15 = list()
            programas_sociais_governo_federal = (
                caracterizacao_dos_alunos.values('beneficiario_programa_social__descricao')
                .annotate(qtd=Count('beneficiario_programa_social__descricao'))
                .order_by('beneficiario_programa_social__descricao')
            )
            for registro in programas_sociais_governo_federal:
                dados15.append([registro['beneficiario_programa_social__descricao'], registro['qtd']])
            if dados15[-1][1] == 0:
                dados15.pop()
            dados15.append(['Não é beneficiário', caracterizacao_dos_alunos.filter(beneficiario_programa_social__isnull=True).count()])
            grafico15 = PieChart(
                'grafico15', title='Programas Sociais do Governo Federal', subtitle='Total de Alunos por Programas Sociais do Governo Federal', minPointLength=0, data=dados15
            )
            setattr(grafico15, 'id', 'grafico15')

            pie_chart_list_dados_familiares_socioeconomicos = [
                grafico1,
                grafico2,
                grafico3,
                grafico4,
                grafico5,
                grafico6,
                grafico7,
                grafico8,
                grafico9,
                grafico10,
                grafico11,
                grafico12,
                grafico13,
                grafico14,
                grafico15,
            ]

    return locals()


@rtr()
@permission_required('ae.pode_ver_relatorio_caracterizacao_todos, ae.pode_ver_relatorio_caracterizacao_do_campus')
def estatisticas_caracterizacao_dados_tic(request):
    title = 'Relatório da Caracterização Socioeconômica - Acesso às Tecnologias da Informação e Comunicação'
    form = EstatisticasCaracterizacaoForm(request.GET or None, request=request)
    if form.is_valid():
        alunos_total = Aluno.objects.filter(get_query_estatistica(form)).distinct()
        if not form.cleaned_data['incluir_fic']:
            alunos_total = alunos_total.exclude(curso_campus__modalidade__pk__in=[Modalidade.FIC, Modalidade.PROEJA_FIC_FUNDAMENTAL])
        alunos_caracterizados = alunos_total.filter(caracterizacao__isnull=False)
        if alunos_caracterizados:
            caracterizacao_dos_alunos = Caracterizacao.objects.filter(aluno__in=alunos_caracterizados.values_list('id'))
            dados = list()
            frequencia_acesso_internet = (
                caracterizacao_dos_alunos.values('frequencia_acesso_internet__descricao')
                .annotate(qtd=Count('frequencia_acesso_internet__descricao'))
                .order_by('frequencia_acesso_internet__descricao')
            )
            total_frequencia_acesso_internet = 0
            for registro in frequencia_acesso_internet:
                dados.append([registro['frequencia_acesso_internet__descricao'], registro['qtd']])
                total_frequencia_acesso_internet = total_frequencia_acesso_internet + registro['qtd']
            if dados[-1][1] == 0:
                dados.pop()
            if alunos_caracterizados.count() - total_frequencia_acesso_internet > 0:
                dados.append(["Não Informado", alunos_caracterizados.count() - total_frequencia_acesso_internet])
            grafico1 = PieChart('grafico1', title='Frequencia de Acesso à Internet', subtitle='Total de Alunos por Frequencia de Acesso à Internet', minPointLength=0, data=dados)
            setattr(grafico1, 'id', 'grafico1')

            dados = list()
            frequencia_acesso_internet = (
                caracterizacao_dos_alunos.values('frequencia_acesso_internet__descricao')
                .annotate(qtd=Count('frequencia_acesso_internet__descricao'))
                .order_by('frequencia_acesso_internet__descricao')
            )
            total_frequencia_acesso_internet = 0
            for registro in frequencia_acesso_internet:
                dados.append([registro['frequencia_acesso_internet__descricao'], registro['qtd']])
                total_frequencia_acesso_internet = total_frequencia_acesso_internet + registro['qtd']
            if dados[-1][1] == 0:
                dados.pop()
            if alunos_caracterizados.count() - total_frequencia_acesso_internet > 0:
                dados.append(["Não Informado", alunos_caracterizados.count() - total_frequencia_acesso_internet])
            grafico1 = PieChart('grafico1', title='Frequencia de Acesso à Internet', subtitle='Total de Alunos por Frequencia de Acesso à Internet', minPointLength=0, data=dados)
            setattr(grafico1, 'id', 'grafico1')

            dados2 = list()
            quantidade_computadores = caracterizacao_dos_alunos.values('quantidade_computadores').annotate(qtd=Count('quantidade_computadores')).order_by('quantidade_computadores')
            total_quantidade_computadores = 0
            for registro in quantidade_computadores:
                dados2.append([str(registro['quantidade_computadores']), registro['qtd']])
                total_quantidade_computadores = total_quantidade_computadores + registro['qtd']
            if dados2[-1][1] == 0:
                dados2.pop()
            if alunos_caracterizados.count() - total_quantidade_computadores > 0:
                dados2.append(["Não Informado", alunos_caracterizados.count() - total_quantidade_computadores])
            grafico2 = PieChart(
                'grafico2', title='Quantidade de Computadores Desktop', subtitle='Total de Alunos por Quantidade de Computadores Desktop', minPointLength=0, data=dados2
            )
            setattr(grafico2, 'id', 'grafico2')

            dados3 = list()
            quantidade_notebooks = caracterizacao_dos_alunos.values('quantidade_notebooks').annotate(qtd=Count('quantidade_notebooks')).order_by('quantidade_notebooks')
            total_quantidade_notebooks = 0
            for registro in quantidade_notebooks:
                dados3.append([str(registro['quantidade_notebooks']), registro['qtd']])
                total_quantidade_notebooks = total_quantidade_notebooks + registro['qtd']
            if dados3[-1][1] == 0:
                dados3.pop()
            if alunos_caracterizados.count() - total_quantidade_notebooks > 0:
                dados3.append(["Não Informado", alunos_caracterizados.count() - total_quantidade_notebooks])
            grafico3 = PieChart('grafico3', title='Quantidade de Notebooks', subtitle='Total de Alunos por Quantidade de Notebooks', minPointLength=0, data=dados3)
            setattr(grafico3, 'id', 'grafico3')

            dados4 = list()
            quantidade_netbooks = caracterizacao_dos_alunos.values('quantidade_netbooks').annotate(qtd=Count('quantidade_netbooks')).order_by('quantidade_netbooks')
            total_quantidade_netbooks = 0
            for registro in quantidade_netbooks:
                dados4.append([str(registro['quantidade_netbooks']), registro['qtd']])
                total_quantidade_netbooks = total_quantidade_netbooks + registro['qtd']
            if dados4[-1][1] == 0:
                dados4.pop()
            if alunos_caracterizados.count() - total_quantidade_netbooks > 0:
                dados4.append(["Não Informado", alunos_caracterizados.count() - total_quantidade_netbooks])
            grafico4 = PieChart('grafico4', title='Quantidade de Neybooks', subtitle='Total de Alunos por Quantidade de Netbooks', minPointLength=0, data=dados4)
            setattr(grafico4, 'id', 'grafico4')

            dados5 = list()
            quantidade_smartphones = caracterizacao_dos_alunos.values('quantidade_smartphones').annotate(qtd=Count('quantidade_smartphones')).order_by('quantidade_smartphones')
            total_quantidade_smartphones = 0
            for registro in quantidade_smartphones:
                dados5.append([str(registro['quantidade_smartphones']), registro['qtd']])
                total_quantidade_smartphones = total_quantidade_smartphones + registro['qtd']
            if dados5[-1][1] == 0:
                dados5.pop()
            if alunos_caracterizados.count() - total_quantidade_smartphones > 0:
                dados5.append(["Não Informado", alunos_caracterizados.count() - total_quantidade_smartphones])
            grafico5 = PieChart('grafico5', title='Quantidade de Smartphones', subtitle='Total de Alunos por Quantidade de Smartphones', minPointLength=0, data=dados5)
            setattr(grafico5, 'id', 'grafico5')

            pie_chart_list_acesso_tecnologia_informacao = [grafico1, grafico2, grafico3, grafico4, grafico5]

    return locals()


@transaction.atomic
def get_pessoas(request, versao=None):
    def ajustar_colunas(sql, versao):
        extras = ''
        if versao and versao >= '1.2.5':
            extras = '"pf"."pf_pode_bater_ponto" as "pode_bate_ponto",\n'
            extras += '"pf"."pf_senha_ponto" as "senha_ponto",'
        query = '''
            SELECT
              "pf"."pf_id" as "id",
              "pf"."pf_username" as "username",
              "pf"."pf_nome" as "nome",
              "pf"."pf_setor" as "setor",
              "pf"."pf_campus" as "campus",
              "pf"."pf_template" as "template",
              "pf"."pf_tem_digital_fraca" as "tem_digital_fraca",
              "pf"."pf_operador_chave" as "operador_chave",
              "pf"."pf_operador_cadastro" as "operador_cadastro",
              {}
              "pf"."pf_exportada" as "exportada"
            FROM ({}) as "pf"'''.format(
            extras, sql
        )
        return query

    try:
        m = Maquina.objects.get(ip=get_client_ip(request), ativo=True, cliente_refeitorio=True)
        if versao:
            m.versao_terminal = VersaoTerminal.objects.get_or_create(numero=versao)[0]
            m.save()
    except Maquina.DoesNotExist:
        raise PermissionDenied('Máquina sem permissões')
    diretorio = f'tabela_alunos-{m.id:d}.zip'
    ARQUIVO_DUMP = os.path.join(settings.TEMP_DIR, diretorio)

    if exists(ARQUIVO_DUMP) and datetime.datetime.fromtimestamp(stat(ARQUIVO_DUMP)[-1]).date() == datetime.datetime.today():
        # Se existe um arquivo gerado no dia, este não precisa ser criado
        pass

    else:
        # Não existe arquivo gerado no dia, então precisa ser criado
        cursor = connection.cursor()

        annotate_alunos = {
            'pf_id': F('pessoa_fisica__pk'),
            'pf_username': F('matricula'),
            'pf_nome': F('pessoa_fisica__nome'),
            'pf_setor': F('curso_campus__diretoria__setor__sigla'),
            'pf_campus': F('curso_campus__diretoria__setor__uo__sigla'),
            'pf_template': F('pessoa_fisica__template'),
            'pf_tem_digital_fraca': F('pessoa_fisica__tem_digital_fraca'),
        }
        extra_alunos = {'pf_operador_chave': 'FALSE', 'pf_operador_cadastro': 'FALSE', 'pf_exportada': 'TRUE'}

        annotate_funcionarios = {
            'pf_id': F('pessoafisica_ptr__pk'),
            'pf_username': F('pessoafisica_ptr__username'),
            'pf_nome': F('pessoafisica_ptr__nome'),
            'pf_setor': Coalesce('setor__sigla', Value('N/A')),
            'pf_campus': Coalesce('setor__uo__setor__sigla', Value('N/A')),
            'pf_template': F('pessoafisica_ptr__template'),
            'pf_tem_digital_fraca': F('pessoafisica_ptr__tem_digital_fraca'),
        }
        extra_funcionarios = {'pf_operador_cadastro': 'TRUE', 'pf_operador_chave': 'TRUE', 'pf_exportada': 'TRUE'}

        if versao and versao >= '1.2.5':
            annotate_alunos['pf_senha_ponto'] = F('pessoa_fisica__senha_ponto')
            extra_alunos['pf_pode_bater_ponto'] = 'FALSE'
            annotate_funcionarios['pf_senha_ponto'] = F('pessoafisica_ptr__senha_ponto')
            extra_funcionarios['pf_pode_bater_ponto'] = 'TRUE'

        alunos = Aluno.ativos.filter(curso_campus__diretoria__setor__uo=m.uo, pessoa_fisica__user__isnull=False)
        alunos = alunos.annotate(**annotate_alunos).extra(select=extra_alunos).values(*(list(annotate_alunos.keys()) + list(extra_alunos.keys())))

        funcionarios = Funcionario.objects.filter(user__groups__name='Operador do Terminal do Refeitório', excluido=False, user__isnull=False)
        funcionarios = (
            funcionarios.extra(select=extra_funcionarios).annotate(**annotate_funcionarios).values(*(list(annotate_funcionarios.keys()) + list(extra_funcionarios.keys())))
        )

        query_alunos = get_real_sql(alunos, remove_order_by=True)
        query_funcionarios = get_real_sql(funcionarios, remove_order_by=True)

        query_alunos = ajustar_colunas(query_alunos, versao)
        query_funcionarios = ajustar_colunas(query_funcionarios, versao)

        query = f'CREATE TEMP TABLE tabela_terminal_refeitorio AS {query_alunos} UNION {query_funcionarios}'

        cursor.execute(query)

        # Gerando o dump
        diretorio = 'tabela_terminal_refeitorio.copy'
        arquivo_a_ser_gerado = os.path.join(settings.TEMP_DIR, diretorio)
        dump_file = open(arquivo_a_ser_gerado, 'w')
        cursor.copy_to(dump_file, 'tabela_terminal_refeitorio')
        dump_file.close()

        # Removendo tabela temporária
        cursor.execute('DROP TABLE tabela_terminal_refeitorio')

        # Compactando o dump
        zip_file = zipfile.ZipFile(ARQUIVO_DUMP, 'w', zipfile.ZIP_DEFLATED)
        zip_file.write(arquivo_a_ser_gerado, 'tabela_terminal_refeitorio.copy')
        zip_file.close()

    # Abrindo o arquivo zipado
    dump_zip_file = open(ARQUIVO_DUMP, 'rb')
    conteudo_dump = dump_zip_file.read()
    dump_zip_file.close()

    response = HttpResponse(conteudo_dump, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=dump_terminal.zip'
    return response


@transaction.atomic
def remover_cache_config_refeicao(uo):
    diretorio = f'tabela_config_refeicao-{uo.id:d}.zip'
    ARQUIVO_DUMP = os.path.join(settings.TEMP_DIR, diretorio)
    if os.path.exists(ARQUIVO_DUMP) and os.path.isfile(ARQUIVO_DUMP):
        os.remove(ARQUIVO_DUMP)


"""
View acessada pelo ponto do refeitório para recuperar os alunos que podem fazer refeição
"""


@transaction.atomic
def get_config_refeicao(request, versao=None):
    def ajustar_colunas(sql, versao):
        colunas_extras_1_2_3 = ''
        colunas_extras_1_2_4 = ''
        if versao and versao >= '1.2.3':
            colunas_extras_1_2_3 = '''
                , "pf"."suspensa"
            '''

        if versao and versao >= '1.2.4':
            colunas_extras_1_2_4 = '''
                "pf"."caf_seg",
                "pf"."caf_ter",
                "pf"."caf_qua",
                "pf"."caf_qui",
                "pf"."caf_sex",
                "pf"."caf_sab",
                "pf"."caf_dom",
            '''

        query = '''
            SELECT
                "pf"."matricula",
                {colunas_extras_1_2_4}
                "pf"."alm_seg",
                "pf"."alm_ter",
                "pf"."alm_qua",
                "pf"."alm_qui",
                "pf"."alm_sex",
                "pf"."alm_sab",
                "pf"."alm_dom",
                "pf"."jan_seg",
                "pf"."jan_ter",
                "pf"."jan_qua",
                "pf"."jan_qui",
                "pf"."jan_sex",
                "pf"."jan_sab",
                "pf"."jan_dom"
                {colunas_extras_1_2_3}
            FROM ({sql}) as "pf"'''.format(
            colunas_extras_1_2_4=colunas_extras_1_2_4, colunas_extras_1_2_3=colunas_extras_1_2_3, sql=sql
        )
        return query

    """
    :param versao: Verão do terminal
    """
    try:
        m = Maquina.objects.get(ip=get_client_ip(request), ativo=True, cliente_refeitorio=True)
    except Maquina.DoesNotExist:
        raise PermissionDenied('Máquina sem permissões')

    diretorio = f'tabela_config_refeicao-{m.uo.id:d}.zip'
    ARQUIVO_DUMP = os.path.join(settings.TEMP_DIR, diretorio)

    if not exists(ARQUIVO_DUMP):
        selects = {
            'matricula': F('participacao__aluno__matricula'),
            'alm_seg': F('solicitacao_atendida_almoco__seg'),
            'alm_ter': F('solicitacao_atendida_almoco__ter'),
            'alm_qua': F('solicitacao_atendida_almoco__qua'),
            'alm_qui': F('solicitacao_atendida_almoco__qui'),
            'alm_sex': F('solicitacao_atendida_almoco__sex'),
            'alm_sab': F('solicitacao_atendida_almoco__sab'),
            'alm_dom': F('solicitacao_atendida_almoco__dom'),
            'jan_seg': F('solicitacao_atendida_janta__seg'),
            'jan_ter': F('solicitacao_atendida_janta__ter'),
            'jan_qua': F('solicitacao_atendida_janta__qua'),
            'jan_qui': F('solicitacao_atendida_janta__qui'),
            'jan_sex': F('solicitacao_atendida_janta__sex'),
            'jan_sab': F('solicitacao_atendida_janta__sab'),
            'jan_dom': F('solicitacao_atendida_janta__dom'),
        }
        colunas_extras = []
        if versao and versao >= '1.2.3':
            colunas_extras.append('suspensa')

        if versao and versao >= '1.2.4':
            selects.update(
                {
                    'caf_seg': F('solicitacao_atendida_cafe__seg'),
                    'caf_ter': F('solicitacao_atendida_cafe__ter'),
                    'caf_qua': F('solicitacao_atendida_cafe__qua'),
                    'caf_qui': F('solicitacao_atendida_cafe__qui'),
                    'caf_sex': F('solicitacao_atendida_cafe__sex'),
                    'caf_sab': F('solicitacao_atendida_cafe__sab'),
                    'caf_dom': F('solicitacao_atendida_cafe__dom'),
                }
            )

        hoje = date.today()

        qs = (
            ParticipacaoAlimentacao.objects.annotate(**selects)
            .filter(participacao__programa__instituicao=m.uo)
            .filter(Q(participacao__data_termino__isnull=True) | Q(participacao__data_termino__gte=hoje))
            .values(*(list(selects.keys()) + colunas_extras))
        )

        query = ajustar_colunas(get_real_sql(qs), versao)

        query = f'CREATE TEMP TABLE tabela_config_refeicao AS {query}'
        cursor = connection.cursor()
        cursor.execute(query)

        segunda_dessa_semana = hoje + timedelta(days=-hoje.weekday())
        domingo_dessa_semana = segunda_dessa_semana + timedelta(days=6)

        coluna_extra_1_2_3 = ""
        if versao and versao >= '1.2.3':
            coluna_extra_1_2_3 = " , 'f'"

        coluna_extra = ""
        if versao and versao >= '1.2.4':
            coluna_extra = " , 'f', 'f', 'f', 'f', 'f', 'f', 'f' "

        # Pegando as refeições de segunda a domingo
        for agendamento in AgendamentoRefeicao.objects.filter(cancelado=False, data__range=[segunda_dessa_semana, domingo_dessa_semana]):
            if not qs.filter(participacao__aluno__matricula=agendamento.aluno.matricula).exists():
                query = "INSERT INTO tabela_config_refeicao VALUES ('{}', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f', 'f' {} {})".format(
                    agendamento.aluno.matricula, coluna_extra, coluna_extra_1_2_3
                )
                cursor.execute(query)
            dias = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
            colname = agendamento.tipo_refeicao.lower() + '_' + dias[agendamento.data.weekday()]
            if not (agendamento.tipo_refeicao.lower() == 'caf' and not coluna_extra):
                query = f"UPDATE tabela_config_refeicao SET {colname} = 't' WHERE matricula = '{agendamento.aluno.matricula}'"
                cursor.execute(query)

        # removendo da programacao semanal as faltas informadas pelos alunos em HistoricoFaltasAlimentacao
        dias = ['seg', 'ter', 'qua', 'qui', 'sex', 'sab', 'dom']
        for falta in HistoricoFaltasAlimentacao.objects.filter(data__range=[segunda_dessa_semana, domingo_dessa_semana], cancelada=False):
            if qs.filter(participacao__aluno__matricula=falta.aluno.matricula).exists():
                nome_refeicao = None
                if falta.tipo_refeicao == TipoRefeicao.TIPO_ALMOCO:
                    nome_refeicao = 'alm'
                elif falta.tipo_refeicao == TipoRefeicao.TIPO_CAFE and versao and versao >= '1.2.4':
                    nome_refeicao = 'caf'
                elif falta.tipo_refeicao == TipoRefeicao.TIPO_JANTAR:
                    nome_refeicao = 'jan'
                if nome_refeicao:
                    colname = nome_refeicao + '_' + dias[falta.data.weekday()]
                    query = f"UPDATE tabela_config_refeicao SET {colname} = 'f' WHERE matricula = '{falta.aluno.matricula}'"
                    cursor.execute(query)

        # Gerando o dump
        diretorio = 'tabela_config_refeicao.copy'
        arquivo_a_ser_gerado = os.path.join(settings.TEMP_DIR, diretorio)
        dump_file = open(arquivo_a_ser_gerado, 'w')
        cursor.copy_to(dump_file, 'tabela_config_refeicao')
        dump_file.close()

        # Removendo tabela temporária
        cursor.execute('DROP TABLE tabela_config_refeicao')

        # Compactando o dump
        zip_file = zipfile.ZipFile(ARQUIVO_DUMP, 'w', zipfile.ZIP_DEFLATED)
        zip_file.write(arquivo_a_ser_gerado, 'tabela_config_refeicao.copy')
        zip_file.close()

    # Abrindo o arquivo zipado
    dump_zip_file = open(ARQUIVO_DUMP, 'rb')
    conteudo_dump = dump_zip_file.read()
    dump_zip_file.close()

    response = HttpResponse(conteudo_dump, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=dump_terminal.zip'
    return response


@rtr()
@permission_required('ae.pode_detalhar_programa_todos, ae.pode_detalhar_programa_do_campus')
def relatorio_semanal_refeitorio(request, programa_id):
    programa = get_object_or_404(Programa, pk=programa_id)
    title = f'Relatório Semanal do Refeitório - {programa}'
    # Impede usuario acessar programa que nao seja de seu campus
    if not verificar_permissao_programa(request, programa):
        raise PermissionDenied()

    count = 1
    data = date.today()
    while data.weekday() != 0:
        data = somar_data(data, -1)

    data_segunda = data
    data_terca = somar_data(data_segunda, 1)
    data_quarta = somar_data(data_terca, 1)
    data_quinta = somar_data(data_quarta, 1)
    data_sexta = somar_data(data_quinta, 1)

    tipo_refeicao = DemandaAluno.ALMOCO

    buscou = False
    categoria = None
    categoria_busca = False
    agendados = False
    avulsos = False
    if request.method == 'GET':
        if 'pdf_data' in request.GET:
            data = datetime.datetime.strptime(request.GET['pdf_data'], '%d/%m/%Y')
            data = data.date()
            buscou = True
        if 'pdf_tipo_refeicao' in request.GET:
            buscou = True
            tipo_refeicao = int(request.GET['pdf_tipo_refeicao'])
        if 'categoria_busca' in request.GET and request.GET.get('categoria_busca'):
            categoria_busca = get_object_or_404(CategoriaAlimentacao, pk=request.GET['categoria_busca'])
            buscou = True
        if 'agendados' in request.GET:
            if request.GET['agendados'] == 'True':
                agendados = True
            buscou = True
        if 'avulsos' in request.GET:
            if request.GET['avulsos'] == 'True':
                avulsos = True
            buscou = True
        form = RelatorioSemanalRefeitorioForm(initial=dict(data=data))
    else:
        form = RelatorioSemanalRefeitorioForm(data=request.POST)
        if form.is_valid():
            buscou = True
            data = form.cleaned_data['data']
            tipo_refeicao = form.cleaned_data['tipo_refeicao']
            categoria_busca = form.cleaned_data['categoria']
            agendados = form.cleaned_data['agendados']
            avulsos = form.cleaned_data['avulsos']

    if buscou:

        atendimentos = []
        total_geral = 0
        data_limite = somar_data(data, 5)

        seg_count = 0
        seg_participante = 0
        seg_agendada = 0
        seg_avulsa = 0
        seg_faltas = 0
        ter_count = 0
        ter_participante = 0
        ter_agendada = 0
        ter_avulsa = 0
        ter_faltas = 0
        qua_count = 0
        qua_participante = 0
        qua_agendada = 0
        qua_avulsa = 0
        qua_faltas = 0
        qui_count = 0
        qui_participante = 0
        qui_agendada = 0
        qui_avulsa = 0
        qui_faltas = 0
        sex_count = 0
        sex_participante = 0
        sex_agendada = 0
        sex_avulsa = 0
        sex_faltas = 0
        seg_faltas_just = ter_faltas_just = qua_faltas_just = qui_faltas_just = sex_faltas_just = 0
        seg_faltas_agendados = ter_faltas_agendados = qua_faltas_agendados = qui_faltas_agendados = sex_faltas_agendados = 0
        total_participantes_seg = total_participantes_ter = total_participantes_qua = total_participantes_qui = total_participantes_sex = 0
        ids_participantes_unicos = set()
        disponibilidade = programa.get_disponibilidade(data)

        total_geral_disponibilidade = 0
        dados_disponibilidade = None

        if tipo_refeicao == DemandaAluno.CAFE:
            falta_tipo_refeicao = TipoRefeicao.TIPO_CAFE
            tipo_refeicao_agendada = AgendamentoRefeicao.TIPO_CAFE
            if disponibilidade:
                dados_disponibilidade = disponibilidade['cafe']['oferta']
        elif tipo_refeicao == DemandaAluno.ALMOCO:
            falta_tipo_refeicao = TipoRefeicao.TIPO_ALMOCO
            tipo_refeicao_agendada = AgendamentoRefeicao.TIPO_ALMOCO
            if disponibilidade:
                dados_disponibilidade = disponibilidade['almoco']['oferta']
        elif tipo_refeicao == DemandaAluno.JANTAR:
            falta_tipo_refeicao = TipoRefeicao.TIPO_JANTAR
            tipo_refeicao_agendada = AgendamentoRefeicao.TIPO_JANTAR
            if disponibilidade:
                dados_disponibilidade = disponibilidade['jantar']['oferta']
        if disponibilidade:
            for item in dados_disponibilidade:
                total_geral_disponibilidade = total_geral_disponibilidade + item

        if request.method == 'GET' and ('pdf_data' in request.GET or 'pdf_tipo_refeicao' in request.GET):
            avulsa = 'X'
            participante = 'P'
            atendida = 'PX'
            agendada = 'A'
            agendada_atendida = 'AX'
            falta = 'F'
            recesso = 'R'
            categoria_label = 'Avulso'
            falta_justificada = 'FJ'
            falta_agendado = 'FA'
        else:
            avulsa = '<span class="status status-success">X</span>'  # => atentidas avulsa
            participante = '<span class="status status-alert">P</span>'  # => agendada da participação
            atendida = '<span class="status status-success">P</span>'  # => atentidas da participação
            agendada = '<span class="status status-alert">A</span>'  # => agendadas
            agendada_atendida = '<span class="status status-success">A</span>'  # => agendadas atendidas
            falta = '<span class="status status-error">FP</span>'  # => faltas da participação
            falta_agendado = '<span class="status status-error">FA</span>'  # => faltas da participação
            recesso = '<span class="status status-default">R</span>'
            categoria_label = 'Atendimento avulso'
            falta_justificada = '<span class="status status-info">FJ</span>'

        registros_participacoes = Participacao.objects.filter(
            Q(programa=programa), Q(data_termino__isnull=True) | Q(data_termino__gte=data_limite), Q(data_inicio__lte=data_limite)
        )
        if categoria_busca:
            registros_participacoes = registros_participacoes.filter(participacaoalimentacao__categoria=categoria_busca)

        registros_participacoes = registros_participacoes.values_list('aluno_id', flat=True)
        registros_agendados = AgendamentoRefeicao.objects.filter(cancelado=False, tipo_refeicao=tipo_refeicao_agendada, programa=programa, data__gte=data, data__lte=data_limite).values_list(
            'aluno_id', flat=True
        )

        registros_atendidos = DemandaAlunoAtendida.objects.filter(campus=programa.instituicao, demanda=tipo_refeicao, data__gte=data, data__lte=data_limite).values_list(
            'aluno_id', flat=True
        )

        ids = set()

        ids.update(registros_agendados)
        if not agendados:
            ids.update(registros_participacoes)
            ids.update(registros_atendidos)
        alunos = Aluno.objects.filter(id__in=ids)
        if avulsos:
            alunos = alunos.exclude(id__in=registros_participacoes).exclude(id__in=registros_agendados)

        for aluno in alunos:

            categoria = ""
            mostrar = False
            solicitacao_atendida = None

            try:
                inscricao = aluno.inscricao_set.get(programa=programa).sub_instance()
            except Inscricao.DoesNotExist:
                inscricao = None
            except Exception:
                # Ainda existem alunos com inscrições duplicadas (ver https://projetos.ifrn.edu.br/issues/3889)
                # Existem alunos com participações que não tem os dados dos atendimentos
                inscricoes = aluno.inscricao_set.filter(programa=programa, participacao__isnull=False, participacao__data_termino__isnull=True).distinct()
                if inscricoes.exists():
                    inscricao = inscricoes[0].sub_instance()
                else:
                    inscricao = None

            participacao_aberta = None
            participacao = None
            if inscricao:
                try:
                    participacao = inscricao.get_ultima_participacao()
                    participacao_aberta = inscricao.get_participacao_aberta()
                except Exception:
                    pass
                if categoria_busca and participacao and participacao.sub_instance().categoria != categoria_busca:
                    continue
                if participacao:
                    if tipo_refeicao == DemandaAluno.ALMOCO:
                        solicitacao_atendida = participacao.sub_instance().solicitacao_atendida_almoco
                    elif tipo_refeicao == DemandaAluno.JANTAR:
                        solicitacao_atendida = participacao.sub_instance().solicitacao_atendida_janta
                    elif tipo_refeicao == DemandaAluno.CAFE:
                        solicitacao_atendida = participacao.sub_instance().solicitacao_atendida_cafe
                else:
                    solicitacao_atendida = None

            seg = ter = qua = qui = sex = '-'
            total = 0
            faltas = 0

            # SEGUNDA
            ref = somar_data(data, 0)
            data_segunda = ref
            if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):
                ids_participantes_unicos.add(participacao.id)
            datas_liberadas = DatasLiberadasFaltasAlimentacao.objects.filter(campus=programa.instituicao)

            # Se o aluno tiver atendimento
            if get_atendimento(aluno, programa, tipo_refeicao, ref):
                if AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                    seg = agendada_atendida
                    seg_agendada += 1

                else:
                    if solicitacao_atendida and solicitacao_atendida.valida() and solicitacao_atendida.seg:
                        # Se o aluno ainda é participante até a data ref
                        if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):
                            seg = atendida
                            seg_participante += 1
                            total_participantes_seg += 1
                        else:
                            seg = avulsa
                            categoria = categoria_label
                            seg_avulsa += 1
                    else:
                        seg = avulsa
                        categoria = categoria_label
                        seg_avulsa += 1
                total += 1
                seg_count += 1
                mostrar = True
            else:
                if datas_liberadas.filter(data=ref).exists() or datas_liberadas.filter(recorrente=True,
                                                                                       data__day=ref.day,
                                                                                       data__month=ref.month).exists():
                    seg = recesso
                # Se o aluno não tiver atendimento
                elif solicitacao_atendida and solicitacao_atendida.valida() and solicitacao_atendida.seg:
                    # Se o aluno ainda é participante até a data ref
                    if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):

                        if HistoricoFaltasAlimentacao.objects.filter(
                            justificativa__isnull=False, aluno=aluno, data=ref, tipo_refeicao=falta_tipo_refeicao, cancelada=False
                        ).exists():
                            seg = falta_justificada
                            seg_faltas_just += 1
                            total_participantes_seg += 1

                        else:
                            if ref >= date.today():
                                seg = participante
                                total_participantes_seg += 1
                            else:
                                if HistoricoFaltasAlimentacao.objects.filter(
                                    justificativa__isnull=True, aluno=aluno, data=ref, tipo_refeicao=falta_tipo_refeicao, cancelada=False
                                ).exists():
                                    seg = falta
                                    faltas += 1
                                    seg_faltas += 1
                                    total_participantes_seg += 1

                        mostrar = True
                    elif AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                        seg = agendada
                        mostrar = True

                else:
                    if AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                        seg_agendada += 1

                        if ref >= date.today():
                            seg = agendada

                        else:
                            seg = falta_agendado
                            faltas += 1
                            seg_faltas_agendados += 1

                        mostrar = True

            # TERCA
            ref = somar_data(data, 1)
            data_terca = ref
            if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):
                ids_participantes_unicos.add(participacao.id)
            datas_liberadas = DatasLiberadasFaltasAlimentacao.objects.filter(campus=programa.instituicao)

            if get_atendimento(aluno, programa, tipo_refeicao, ref):
                if AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                    ter = agendada_atendida
                    ter_agendada += 1
                else:
                    if solicitacao_atendida and solicitacao_atendida.valida() and solicitacao_atendida.ter:
                        if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):
                            ter = atendida
                            ter_participante += 1
                            total_participantes_ter += 1
                        else:
                            ter = avulsa
                            categoria = categoria_label
                            ter_avulsa += 1
                    else:
                        ter = avulsa
                        categoria = categoria_label
                        ter_avulsa += 1
                total += 1
                ter_count += 1
                mostrar = True
            else:
                if datas_liberadas.filter(data=ref).exists() or datas_liberadas.filter(recorrente=True,
                                                                                       data__day=ref.day,
                                                                                       data__month=ref.month).exists():
                    ter = recesso
                elif solicitacao_atendida and solicitacao_atendida.valida() and solicitacao_atendida.ter:
                    if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):

                        if HistoricoFaltasAlimentacao.objects.filter(
                            justificativa__isnull=False, aluno=aluno, data=ref, tipo_refeicao=falta_tipo_refeicao, cancelada=False
                        ).exists():
                            ter = falta_justificada
                            ter_faltas_just += 1
                            total_participantes_ter += 1

                        else:
                            if ref >= date.today():
                                ter = participante
                                total_participantes_ter += 1
                            else:
                                if HistoricoFaltasAlimentacao.objects.filter(
                                    justificativa__isnull=True, aluno=aluno, data=ref, tipo_refeicao=falta_tipo_refeicao, cancelada=False
                                ).exists():
                                    ter = falta
                                    faltas += 1
                                    ter_faltas += 1
                                    total_participantes_ter += 1
                        mostrar = True
                    elif AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                        ter = agendada
                        mostrar = True
                else:
                    if AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                        ter_agendada += 1

                        if ref >= date.today():
                            ter = agendada
                        else:
                            ter = falta_agendado
                            faltas += 1
                            ter_faltas_agendados += 1

                        mostrar = True

            #        QUARTA
            ref = somar_data(data, 2)
            data_quarta = ref
            if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):
                ids_participantes_unicos.add(participacao.id)
            datas_liberadas = DatasLiberadasFaltasAlimentacao.objects.filter(campus=programa.instituicao)

            if get_atendimento(aluno, programa, tipo_refeicao, ref):
                if AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                    qua = agendada_atendida
                    qua_agendada += 1
                else:
                    if solicitacao_atendida and solicitacao_atendida.valida() and solicitacao_atendida.qua:
                        if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):
                            qua = atendida
                            qua_participante += 1
                            total_participantes_qua += 1
                        else:
                            qua = avulsa
                            categoria = categoria_label
                            qua_avulsa += 1
                    else:
                        qua = avulsa
                        categoria = categoria_label
                        qua_avulsa += 1
                total += 1
                qua_count += 1
                mostrar = True
            else:
                if datas_liberadas.filter(data=ref).exists() or datas_liberadas.filter(recorrente=True,
                                                                                       data__day=ref.day,
                                                                                       data__month=ref.month).exists():
                    qua = recesso
                elif solicitacao_atendida and solicitacao_atendida.valida() and solicitacao_atendida.qua:
                    if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):

                        if HistoricoFaltasAlimentacao.objects.filter(
                            justificativa__isnull=False, aluno=aluno, data=ref, tipo_refeicao=falta_tipo_refeicao, cancelada=False
                        ).exists():
                            qua = falta_justificada
                            qua_faltas_just += 1
                            total_participantes_qua += 1

                        else:
                            if ref >= date.today():
                                qua = participante
                                total_participantes_qua += 1
                            else:
                                if HistoricoFaltasAlimentacao.objects.filter(
                                    justificativa__isnull=True, aluno=aluno, data=ref, tipo_refeicao=falta_tipo_refeicao, cancelada=False
                                ).exists():
                                    qua = falta
                                    faltas += 1
                                    qua_faltas += 1
                                    total_participantes_qua += 1
                        mostrar = True
                    elif AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                        qua = agendada
                        mostrar = True
                else:
                    if AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                        qua_agendada += 1

                        if ref >= date.today():
                            qua = agendada
                        else:
                            qua = falta_agendado
                            faltas += 1
                            qua_faltas_agendados += 1

                        mostrar = True

            #        QUINTA
            ref = somar_data(data, 3)
            data_quinta = ref
            if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):
                ids_participantes_unicos.add(participacao.id)
            datas_liberadas = DatasLiberadasFaltasAlimentacao.objects.filter(campus=programa.instituicao)

            if get_atendimento(aluno, programa, tipo_refeicao, ref):
                if AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                    qui = agendada_atendida
                    qui_agendada += 1
                else:
                    if solicitacao_atendida and solicitacao_atendida.valida() and solicitacao_atendida.qui:
                        if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):
                            qui = atendida
                            qui_participante += 1
                            total_participantes_qui += 1
                        else:
                            qui = avulsa
                            categoria = categoria_label
                            qui_avulsa += 1
                    else:
                        qui = avulsa
                        categoria = categoria_label
                        qui_avulsa += 1
                total += 1
                qui_count += 1
                mostrar = True
            else:
                if datas_liberadas.filter(data=ref).exists() or datas_liberadas.filter(recorrente=True,
                                                                                       data__day=ref.day,
                                                                                       data__month=ref.month).exists():
                    qui = recesso
                elif solicitacao_atendida and solicitacao_atendida.valida() and solicitacao_atendida.qui:
                    if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):

                        if HistoricoFaltasAlimentacao.objects.filter(
                            justificativa__isnull=False, aluno=aluno, data=ref, tipo_refeicao=falta_tipo_refeicao, cancelada=False
                        ).exists():
                            qui = falta_justificada
                            qui_faltas_just += 1
                            total_participantes_qui += 1

                        else:
                            if ref >= date.today():
                                qui = participante
                                total_participantes_qui += 1
                            else:
                                if HistoricoFaltasAlimentacao.objects.filter(
                                    justificativa__isnull=True, aluno=aluno, data=ref, tipo_refeicao=falta_tipo_refeicao, cancelada=False
                                ).exists():
                                    qui = falta
                                    faltas += 1
                                    qui_faltas += 1
                                    total_participantes_qui += 1
                        mostrar = True
                    elif AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                        qui = agendada
                        mostrar = True
                else:
                    if AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                        qui_agendada += 1

                        if ref >= date.today():
                            qui = agendada
                        else:
                            qui = falta_agendado
                            faltas += 1
                            qui_faltas_agendados += 1

                        mostrar = True

            #        SEXTA
            ref = somar_data(data, 4)
            data_sexta = ref
            if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):
                ids_participantes_unicos.add(participacao.id)
            datas_liberadas = DatasLiberadasFaltasAlimentacao.objects.filter(campus=programa.instituicao)

            if get_atendimento(aluno, programa, tipo_refeicao, ref):
                if AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                    sex = agendada_atendida
                    sex_agendada += 1
                else:
                    if solicitacao_atendida and solicitacao_atendida.valida() and solicitacao_atendida.sex:
                        if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):
                            sex = atendida
                            sex_participante += 1
                            total_participantes_sex += 1
                        else:
                            sex = avulsa
                            categoria = categoria_label
                            sex_avulsa += 1
                    else:
                        sex = avulsa
                        categoria = categoria_label
                        sex_avulsa += 1
                total += 1
                sex_count += 1
                mostrar = True
            else:
                if datas_liberadas.filter(data=ref).exists() or datas_liberadas.filter(recorrente=True,
                                                                                       data__day=ref.day,
                                                                                       data__month=ref.month).exists():
                    sex = recesso
                elif solicitacao_atendida and solicitacao_atendida.valida() and solicitacao_atendida.sex:
                    if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= ref)):

                        if HistoricoFaltasAlimentacao.objects.filter(
                            justificativa__isnull=False, aluno=aluno, data=ref, tipo_refeicao=falta_tipo_refeicao, cancelada=False
                        ).exists():
                            sex = falta_justificada
                            sex_faltas_just += 1
                            total_participantes_sex += 1

                        else:
                            if ref >= date.today():
                                sex = participante
                                total_participantes_sex += 1
                            else:
                                if HistoricoFaltasAlimentacao.objects.filter(
                                    justificativa__isnull=True, aluno=aluno, data=ref, tipo_refeicao=falta_tipo_refeicao, cancelada=False
                                ).exists():
                                    sex = falta
                                    faltas += 1
                                    sex_faltas += 1
                                    total_participantes_sex += 1
                        mostrar = True
                    elif AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                        sex = agendada
                        mostrar = True
                else:
                    if AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=ref, tipo_refeicao=tipo_refeicao_agendada).exists():
                        sex_agendada += 1

                        if ref >= date.today():
                            sex = agendada
                        else:
                            sex = falta_agendado
                            faltas += 1
                            sex_faltas_agendados += 1

                        mostrar = True

            if mostrar:
                inscricao_id = None
                if inscricao and participacao_aberta:
                    categoria = participacao.participacaoalimentacao.categoria
                    inscricao_id = inscricao.id
                uo = programa.instituicao.id

                if categoria == categoria_label and aluno.curso_campus and aluno.curso_campus.diretoria:
                    uo = aluno.curso_campus.diretoria.setor.uo.id
                dicionario = dict(
                    count=count,
                    matricula=aluno.matricula,
                    pessoa_fisica=aluno.pessoa_fisica.nome,
                    categoria=categoria,
                    seg=seg,
                    ter=ter,
                    qua=qua,
                    qui=qui,
                    sex=sex,
                    total=total,
                    faltas=faltas,
                    inscricao_id=inscricao_id,
                    participacao=participacao_aberta,
                    uo=uo,
                )

                atendimentos.append(dicionario)
                total_geral += total
                count += 1

        total_participante_cadastrados = len(ids_participantes_unicos)
        total_participante = total_participantes_seg + total_participantes_ter + total_participantes_qua + total_participantes_qui + total_participantes_sex
        total_agendada = seg_agendada + ter_agendada + qua_agendada + qui_agendada + sex_agendada
        total_avulsa = seg_avulsa + ter_avulsa + qua_avulsa + qui_avulsa + sex_avulsa
        total_faltas = seg_faltas + ter_faltas + qua_faltas + qui_faltas + sex_faltas
        total_faltas_just = seg_faltas_just + ter_faltas_just + qua_faltas_just + qui_faltas_just + sex_faltas_just
        total_faltas_agendados = seg_faltas_agendados + ter_faltas_agendados + qua_faltas_agendados + qui_faltas_agendados + sex_faltas_agendados

        total_executado = seg_count + ter_count + qua_count + qui_count + sex_count

        if tipo_refeicao == DemandaAluno.CAFE:
            tipo_refeicao_label = "CAFÉ DA MANHÃ"
        elif tipo_refeicao == DemandaAluno.ALMOCO:
            tipo_refeicao_label = "ALMOÇO"
        else:
            tipo_refeicao_label = "JANTAR"
        if request.method == 'GET' and 'pdf_data' in request.GET and 'pdf_tipo_refeicao' in request.GET:
            return relatorio_semanal_refeitorio_pdf(
                request, atendimentos, total_geral, data, data_limite, tipo_refeicao_label, [seg_count, ter_count, qua_count, qui_count, sex_count]
            )
        else:
            return locals()
    else:
        return locals()


def get_atendimento(aluno, programa, tipo_refeicao, ref):
    return aluno.demandaalunoatendida_set.filter(
        campus=programa.instituicao,
        demanda=tipo_refeicao,
        data__gte=datetime.datetime(ref.year, ref.month, ref.day, 0, 0, 0),
        data__lte=datetime.datetime(ref.year, ref.month, ref.day, 23, 59, 59),
    ).exists()


@permission_required('ae.pode_detalhar_programa_todos, ae.pode_detalhar_programa_do_campus')
def relatorio_semanal_refeitorio_pdf(request, atendimentos, total, data, data_limite, tipo_refeicao_label, counts):
    uo = get_uo(request.user)
    topo = get_topo_pdf(f'Relatório Semanal - Programa de Alimentação ({tipo_refeicao_label})')
    servidor = request.user.get_relacionamento()
    info = [
        ["UO", uo],
        ["Servidor", servidor],
        ["Data de Emissão", datetime.datetime.today().strftime("%d/%m/%Y")],
        ["Total de Atendimentos", ' ' + str(total)],
        ["Período", '{} - {}'.format(data.strftime("%d/%m/%Y"), data_limite.strftime("%d/%m/%Y"))],
    ]
    dados = [['Matrícula', 'Aluno', 'Categoria', 'Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Total', 'Faltas']]
    for registro in atendimentos:
        dados.append(
            [
                registro['matricula'],
                registro['pessoa_fisica'],
                registro['categoria'],
                registro['seg'],
                registro['ter'],
                registro['qua'],
                registro['qui'],
                registro['sex'],
                registro['total'],
                registro['faltas'],
            ]
        )
    dados.append(['', '', 'TOTAL:', counts[0], counts[1], counts[2], counts[3], counts[4], total, ''])
    tabela_info = pdf.table(info, grid=0, w=[30, 160])
    tabela_dados = pdf.table(dados, head=1, zebra=1, w=[27, 70, 40, 8, 8, 8, 8, 8, 10, 10], count=1)

    dados = list()
    dados.append(['Legenda', 'Descrição'])
    dados.append(['P', 'Aluno participante com refeição para esta data.'])
    dados.append(['PX', 'Aluno participante realizou refeição nesta data.'])
    dados.append(['A', 'Aluno possui refeição agendada para esta data.'])
    dados.append(['AX', 'Aluno realizou refeição nesta data, conforme agendamento.'])
    dados.append(['F', 'Aluno participante faltou refeição.'])
    dados.append(['-', 'Não há refeição nesta data para este aluno.'])
    tabela_legenda = pdf.table(dados, head=1, zebra=1, w=[25, 104], count=1)

    body = topo + [tabela_info, pdf.space(8), tabela_dados, pdf.space(8), tabela_legenda]

    return PDFResponse(pdf.PdfReport(body=body).generate())


@rtr()
@permission_required('ae.pode_ver_relatorio_caracterizacao_todos, ae.pode_ver_relatorio_caracterizacao_do_campus')
def alunos_ativos_sem_caracterizacao(request):
    alunos_ativos = Aluno.nao_fic.filter(situacao__ativo=True)
    alunos_ativos_sem_caracterizacao = alunos_ativos.filter(caracterizacao__isnull=True)

    dados = (
        alunos_ativos_sem_caracterizacao.values_list('curso_campus__diretoria__setor__uo__sigla')
        .annotate(count=models.Count('curso_campus__diretoria__setor__uo__sigla'))
        .order_by('count')
    )

    series = list()
    for dado in dados[1:]:
        series.append(dado)

    grafico1 = PieChart('grafico1', title="Quantidade de alunos ativos sem caracterização por campus", subtitle="", minPointLength=0, data=series)

    campus = get_uo(request.user)

    campi = UnidadeOrganizacional.objects.uo().filter(id=campus.id)
    grafico = None

    ordenacao = "?"

    # Filtro de Campus
    if request.user.has_perm('ae.pode_ver_relatorio_caracterizacao_todos'):
        campi = UnidadeOrganizacional.objects.uo().all()
        if request.GET.get('campus'):
            campus = UnidadeOrganizacional.objects.uo().get(id=int(request.GET['campus']))
            ordenacao += f"campus={campus.id}&"

    alunos_ativos_sem_caracterizacao = alunos_ativos_sem_caracterizacao.filter(curso_campus__diretoria__setor__uo=campus)
    alunos_ativos = alunos_ativos.filter(curso_campus__diretoria__setor__uo=campus)

    # Filtro de Curso
    cursos = Curso.objects.filter(diretoria__setor__uo=campus).exclude(modalidade__id__in=[Modalidade.FIC, Modalidade.PROEJA_FIC_FUNDAMENTAL])
    cursos_id = alunos_ativos.values('curso_campus').annotate(dcount=models.Count('curso_campus')).values_list('curso_campus')

    ids = list()
    for curso_id in cursos_id:
        ids.append(curso_id[0])

    if ids:
        cursos = cursos.filter(id__in=ids)

    curso = None
    if request.GET.get('curso'):
        curso = int(request.GET['curso'])
        if cursos.filter(id=curso):
            alunos_ativos_sem_caracterizacao = alunos_ativos_sem_caracterizacao.filter(curso_campus__id=curso)
            alunos_ativos = alunos_ativos.filter(curso_campus__id=curso)
            ordenacao += f"curso={curso}&"

    title = f'Alunos ativos sem caracterização ({campus})'

    nome_campus = str(campus)

    total_alunos_ativos = alunos_ativos.count()

    alunos_ativos_sem_caracterizacao = alunos_ativos_sem_caracterizacao.order_by('pessoa_fisica__nome')

    return locals()


@rtr()
@permission_required('ae.view_participacaobolsa', 'ae.change_participacaobolsa')
def participacoes_bolsas(request):
    title = 'Participações em Bolsas'
    usuario_sistemico = request.user.has_perm('ae.pode_ver_relatorio_participacao_todos')
    pode_editar = request.user.has_perm('ae.change_participacaobolsa')
    eh_diretor_geral = request.user.groups.filter(name='Diretor Geral').exists()

    categorias = CategoriaBolsa.objects.filter(vinculo_programa=False, ativa=True)
    lista_campus = UnidadeOrganizacional.objects.uo().all()
    participantes = ParticipacaoBolsa.abertas.filter(categoria__ativa=True)
    futuros_participantes = ParticipacaoBolsa.futuras.filter(categoria__ativa=True)
    ex_participantes = ParticipacaoBolsa.fechadas.filter(categoria__ativa=True)

    if not usuario_sistemico:
        uo = get_uo(request.user)
        participantes = participantes.filter(aluno__curso_campus__diretoria__setor__uo=uo)
        futuros_participantes = futuros_participantes.filter(aluno__curso_campus__diretoria__setor__uo=uo)
        ex_participantes = ex_participantes.filter(aluno__curso_campus__diretoria__setor__uo=uo)

    campus = int(request.GET.get('campus', None) or 0)
    if campus:
        participantes = participantes.filter(aluno__curso_campus__diretoria__setor__uo__pk=campus)
        futuros_participantes = futuros_participantes.filter(aluno__curso_campus__diretoria__setor__uo__pk=campus)
        ex_participantes = ex_participantes.filter(aluno__curso_campus__diretoria__setor__uo__pk=campus)

    if request.GET.get('categoria'):
        categoria = int(request.GET['categoria'])
        participantes = participantes.filter(categoria=categoria)
        futuros_participantes = futuros_participantes.filter(categoria=categoria)
        ex_participantes = ex_participantes.filter(categoria=categoria)

    if request.GET.get('query'):
        query = request.GET['query']
        participantes = participantes.filter(Q(aluno__matricula__icontains=query) | Q(aluno__pessoa_fisica__nome__icontains=query))
        futuros_participantes = futuros_participantes.filter(Q(aluno__matricula__icontains=query) | Q(aluno__pessoa_fisica__nome__icontains=query))
        ex_participantes = ex_participantes.filter(Q(aluno__matricula__icontains=query) | Q(aluno__pessoa_fisica__nome__icontains=query))

    return locals()


@rtr()
@permission_required('ae.change_participacaobolsa')
def participacoes_bolsas_salvar(request, participacao_pk=None):
    title = '{} Participação'.format(participacao_pk and 'Editar' or 'Adicionar')
    if participacao_pk:
        participacao = ParticipacaoBolsa.objects.get(id=participacao_pk)

    form = ParticipacaoBolsaModelForm(data=request.POST or None, instance=participacao_pk and participacao or None, request=request)
    if form.is_valid():
        form.save()
        return httprr('..', 'Participação {} com sucesso'.format(participacao_pk and 'editada' or 'adicionada'))
    return locals()


@rtr()
@permission_required(['ae.pode_ver_lista_bolsas_todos'])
def lista_participantes_bolsas(request):
    title = 'Lista de Participantes em Bolsas'

    form = RelatorioBolsasForm(request.GET or None, request=request)

    if form.is_valid():
        participacoes = ParticipacaoBolsa.objects.filter(categoria__ativa=True).order_by('data_inicio')
        cleaned_data = form.cleaned_data
        campus = cleaned_data.get('campus', None)
        categoria = cleaned_data.get('categoria', None)
        ano = cleaned_data.get('ano', 0)
        mes = cleaned_data.get('mes', 0)
        if categoria:
            categoria = int(request.GET['categoria'])
            participacoes = participacoes.filter(categoria=categoria).order_by('data_inicio')
        if campus:
            campus = int(request.GET['campus'])
            participacoes = participacoes.filter(aluno__curso_campus__diretoria__setor__uo__pk=campus)
        if ano:
            if mes:
                if mes == 12:
                    participacoes = participacoes.filter(
                        Q(data_inicio__lt=f'{ano + 1}-01-01') & (Q(data_termino__isnull=True) | Q(data_termino__gte=f'{ano}-{mes}-01'))
                    ).order_by('data_inicio')
                else:
                    participacoes = participacoes.filter(
                        Q(data_inicio__lt=f'{ano}-{mes + 1}-01') & (Q(data_termino__isnull=True) | Q(data_termino__gte=f'{ano}-{mes}-01'))
                    ).order_by('data_inicio')
            else:
                # Se o mês não for selecionado filtra pelo ano
                participacoes = participacoes.filter(
                    Q(data_inicio__lte=f'{ano}-12-31') & (Q(data_termino__isnull=True) | Q(data_termino__gte=f'{ano}-01-01'))
                ).order_by('data_inicio')
        ord_setor = None
        if request.GET.get('ord_setor'):
            ord_setor = request.GET['ord_setor']
            if ord_setor == 'asc':
                participacoes = participacoes.order_by('setor')
            elif ord_setor == 'desc':
                participacoes = participacoes.order_by('-setor')
        dados = participacoes.values('categoria__nome').annotate(qtd=models.Count('categoria__nome')).order_by('categoria__nome')
        dados_grafico = list()
        for dado in dados:
            dado_grafico = list()
            dado_grafico.append(dado['categoria__nome'])
            dado_grafico.append(dado['qtd'])
            dados_grafico.append(dado_grafico)

        grafico = PieChart('grafico', title='Relatório de Participantes', subtitle='Quantidade de participantes por categoria', minPointLength=0, data=dados_grafico)
        setattr(grafico, 'id', 'grafico')

        fields = ('aluno', 'categoria', 'setor', 'data_termino')
        custom_fields = dict(
            aluno=LinkColumn('aluno', kwargs={'matricula': Accessor('aluno.matricula')}, verbose_name='Aluno', accessor=Accessor('aluno')),
            data_inicio=DateColumn(format="d/m/Y"),
            data_termino=DateColumn(format="d/m/Y"),
        )
        sequence = ['aluno', 'categoria', 'setor', 'data_inicio', 'data_termino']
        table = get_table(queryset=participacoes, fields=fields, custom_fields=custom_fields, sequence=sequence, per_page_field=50)
        if request.GET.get("relatorio", None):
            return tasks.table_export(request.GET.get("relatorio", None), *table.get_params())

    return locals()


@rtr()
@permission_required('ae.pode_ver_lista_dos_alunos, ae.pode_ver_lista_dos_alunos_campus')
def aluno_buscar(request):
    title = 'Lista de Alunos'
    form = BuscarAlunoForm(request.GET or None, request=request)
    sm = Decimal(Configuracao.get_valor_por_chave('comum', 'salario_minimo'))

    if form.is_valid():
        kwargs = {}
        matricula = form.cleaned_data['matricula']
        nome = form.cleaned_data['nome']
        campus = form.cleaned_data['campus']
        curso = form.cleaned_data['curso']
        modalidade = form.cleaned_data['modalidade']
        atendimentos = form.cleaned_data['atendimentos']
        atendimentos_em = form.cleaned_data['atendimentos_em']
        com_caracterizacao = form.cleaned_data['caracterizacao']
        necessidades_especiais = form.cleaned_data['necessidades_especiais']
        raca = form.cleaned_data['raca']
        programa_inscricoes_sim_nao = form.cleaned_data['programa_inscricoes_sim_nao']
        programa_inscricoes_inicial = form.cleaned_data['programa_inscricoes_inicial']
        programa_inscricoes_final = form.cleaned_data['programa_inscricoes_final']
        programa_inscricoes = form.cleaned_data['programa_inscricoes']
        programa_participacoes_sim_nao = form.cleaned_data['programa_participacoes_sim_nao']
        programa_participacoes = form.cleaned_data['programa_participacoes']
        faixa_etaria = form.cleaned_data['faixa_etaria'] and int(form.cleaned_data['faixa_etaria'])
        situacao_matricula = form.cleaned_data['situacao']
        tipo_programa_inscricao = form.cleaned_data['tipo_programa_inscricao']
        tipo_programa_participacao = form.cleaned_data['tipo_programa_participacao']

        renda_bruta_familiar = None
        if form.cleaned_data['renda_bruta_familiar']:
            renda_bruta_familiar = int(form.cleaned_data['renda_bruta_familiar'])
        tipo_matricula = form.cleaned_data['tipo_matricula']

        procedencia_ensino_medio = form.cleaned_data['procedencia_ensino_medio']
        procedencia_ensino_fundamental = form.cleaned_data['procedencia_ensino_fundamental']
        ver_curso = form.cleaned_data['ver_curso']
        ver_polo_ead = form.cleaned_data['ver_polo_ead']
        ver_informacoes_contato = form.cleaned_data['ver_informacoes_contato']
        ver_rg_cpf = form.cleaned_data['ver_rg_cpf']
        ver_dados_pessoais = form.cleaned_data['ver_dados_pessoais']
        ver_dados_educacionais = form.cleaned_data['ver_dados_educacionais']
        ver_dados_familiares = form.cleaned_data['ver_dados_familiares']
        ver_acesso_tecnologias = form.cleaned_data['ver_acesso_tecnologias']
        ver_inscricoes_em_programas = form.cleaned_data['ver_inscricoes_em_programas']
        ver_documentacao = form.cleaned_data['ver_documentacao']

        if situacao_matricula:
            kwargs['situacao__ativo'] = situacao_matricula == 'Ativo'
        if tipo_matricula:
            kwargs['situacao'] = tipo_matricula
        if com_caracterizacao:
            kwargs['caracterizacao__isnull'] = False if com_caracterizacao == 'Sim' else True
        if matricula:
            kwargs['matricula__icontains'] = matricula
        if renda_bruta_familiar:
            if renda_bruta_familiar == 1:
                kwargs['caracterizacao__renda_bruta_familiar__lte'] = sm * 1
            if renda_bruta_familiar == 2:
                kwargs['caracterizacao__renda_bruta_familiar__gt'] = sm * 1
                kwargs['caracterizacao__renda_bruta_familiar__lte'] = sm * 2
            if renda_bruta_familiar == 3:
                kwargs['caracterizacao__renda_bruta_familiar__gt'] = sm * 2
                kwargs['caracterizacao__renda_bruta_familiar__lte'] = sm * 5
            if renda_bruta_familiar == 4:
                kwargs['caracterizacao__renda_bruta_familiar__gt'] = sm * 5
                kwargs['caracterizacao__renda_bruta_familiar__lte'] = sm * 10
            if renda_bruta_familiar == 5:
                kwargs['caracterizacao__renda_bruta_familiar__gt'] = sm * 10
        if raca:
            kwargs['caracterizacao__raca'] = raca
        if procedencia_ensino_medio:
            kwargs['caracterizacao__escola_ensino_medio'] = procedencia_ensino_medio
        if procedencia_ensino_fundamental:
            kwargs['caracterizacao__escola_ensino_fundamental'] = procedencia_ensino_fundamental
        if nome:
            kwargs['pessoa_fisica__nome__icontains'] = nome
        if campus:
            kwargs['curso_campus__diretoria__setor__uo'] = campus
        if curso:
            kwargs['curso_campus'] = curso
        if modalidade:
            kwargs['curso_campus__modalidade__id__in'] = modalidade

        if atendimentos and atendimentos != 'Todos':
            kwargs['demandaalunoatendida__demanda'] = atendimentos
        if atendimentos_em and atendimentos_em != 'Todos':
            kwargs['demandaalunoatendida__data__year'] = atendimentos_em

        if necessidades_especiais and kwargs.get('caracterizacao__isnull') == False:  # não pode ser null
            if necessidades_especiais == 'Nenhuma':
                kwargs['caracterizacao__possui_necessidade_especial'] = False
            elif necessidades_especiais == 'Qualquer':
                kwargs['caracterizacao__possui_necessidade_especial'] = True
            else:
                kwargs['caracterizacao__necessidade_especial'] = necessidades_especiais

        if faixa_etaria:
            hoje = datetime.datetime.now()
            if faixa_etaria == 1:
                kwargs['pessoa_fisica__nascimento_data__gte'] = hoje - relativedelta(years=14)
            if faixa_etaria == 2:
                kwargs['pessoa_fisica__nascimento_data__lte'] = hoje - relativedelta(years=15)
                kwargs['pessoa_fisica__nascimento_data__gte'] = hoje - relativedelta(years=17)
            if faixa_etaria == 3:
                kwargs['pessoa_fisica__nascimento_data__lte'] = hoje - relativedelta(years=18)
                kwargs['pessoa_fisica_' '_nascimento_data__gte'] = hoje - relativedelta(years=29)
            if faixa_etaria == 4:
                kwargs['pessoa_fisica__nascimento_data__lte'] = hoje - relativedelta(years=30)
                kwargs['pessoa_fisica__nascimento_data__gte'] = hoje - relativedelta(years=49)
            if faixa_etaria == 5:
                kwargs['pessoa_fisica__nascimento_data__lte'] = hoje - relativedelta(years=50)

        alunos = Aluno.objects.filter(**kwargs)

        if programa_inscricoes_sim_nao:
            alunos = alunos.filter(inscricao__isnull=False)
        data_inicio = data_fim = False
        if programa_inscricoes_inicial:
            data_inicio = True
            if programa_inscricoes_final:
                data_fim = True
                alunos = alunos.filter(inscricao__data_cadastro__gte=programa_inscricoes_inicial, inscricao__data_cadastro__lte=programa_inscricoes_final)
            else:
                alunos = alunos.filter(inscricao__data_cadastro__gte=programa_inscricoes_inicial)
        elif programa_inscricoes_final:
            alunos = alunos.filter(inscricao__data_cadastro__lte=programa_inscricoes_final)
        if programa_inscricoes:
            alunos = alunos.filter(inscricao__programa=programa_inscricoes)
        if tipo_programa_inscricao:
            if data_inicio and data_fim:
                alunos = alunos.filter(inscricao__programa__tipo_programa=tipo_programa_inscricao, inscricao__data_cadastro__gte=programa_inscricoes_inicial, inscricao__data_cadastro__lte=programa_inscricoes_final)
            elif data_inicio:
                alunos = alunos.filter(inscricao__programa__tipo_programa=tipo_programa_inscricao,
                                       inscricao__data_cadastro__gte=programa_inscricoes_inicial)
            else:
                alunos = alunos.filter(inscricao__programa__tipo_programa=tipo_programa_inscricao)

        if programa_participacoes_sim_nao:
            alunos = alunos.filter(Q(participacao__data_termino__isnull=True) | Q(participacao__data_termino__gte=datetime.datetime.today()))
            if programa_participacoes:
                alunos = alunos.filter(participacao__programa=programa_participacoes)
        elif programa_participacoes:
            alunos = alunos.filter(participacao__programa=programa_participacoes).filter(
                Q(participacao__data_termino__isnull=True) | Q(participacao__data_termino__gte=datetime.datetime.today())
            )
        if tipo_programa_participacao:
            alunos = alunos.filter(participacao__programa__tipo_programa=tipo_programa_participacao)

        custom_fields = dict(matricula=LinkColumn('aluno', kwargs={'matricula': Accessor('matricula')}, verbose_name='Matrícula', accessor=Accessor('matricula')))

        fields = ('pessoa_fisica.nome',)
        if ver_curso:
            fields = fields + ('curso_campus',)
        if ver_polo_ead:
            fields = fields + ('polo',)
        if ver_rg_cpf:
            fields = fields + ('pessoa_fisica.rg', 'pessoa_fisica.cpf')
        if ver_informacoes_contato:
            fields = fields + (
                'logradouro',
                'numero',
                'complemento',
                'bairro',
                'cep',
                'cidade',
                'tipo_zona_residencial',
                'telefone_principal',
                'pessoa_fisica.email',
                'pessoa_fisica.email_secundario',
            )
        if ver_dados_pessoais:
            fields = fields + (
                'caracterizacao.raca',
                'caracterizacao.possui_necessidade_especial',
                'caracterizacao.necessidade_especial',
                'caracterizacao.necessidade_especial',
                'caracterizacao.estado_civil',
                'caracterizacao.qtd_filhos',
            )
        if ver_dados_educacionais:
            fields = fields + (
                'caracterizacao.aluno_exclusivo_rede_publica',
                'caracterizacao.ensino_fundamental_conclusao',
                'caracterizacao.ensino_medio_conclusao',
                'caracterizacao.ficou_tempo_sem_estudar',
                'caracterizacao.tempo_sem_estudar',
                'caracterizacao.razao_ausencia_educacional',
                'caracterizacao.possui_conhecimento_idiomas',
                'caracterizacao.idiomas_conhecidos',
                'caracterizacao.possui_conhecimento_informatica',
                'caracterizacao.escola_ensino_fundamental',
                'caracterizacao.nome_escola_ensino_fundamental',
                'caracterizacao.escola_ensino_medio',
                'caracterizacao.nome_escola_ensino_medio',
            )
        if ver_dados_familiares:
            fields = fields + (
                'caracterizacao.trabalho_situacao',
                'caracterizacao.responsavel_financeiro',
                'caracterizacao.responsavel_financeir_trabalho_situacao',
                'caracterizacao.responsavel_financeiro_nivel_escolaridade',
                'caracterizacao.pai_nivel_escolaridade',
                'caracterizacao.mae_nivel_escolaridade',
                'caracterizacao.renda_bruta_familiar',
                'caracterizacao.companhia_domiciliar',
                'caracterizacao.qtd_pessoas_domicilio',
                'caracterizacao.tipo_imovel_residencial',
                'caracterizacao.tipo_area_residencial',
                'caracterizacao.meio_transporte_utilizado',
                'caracterizacao.contribuintes_renda_familiar',
                'caracterizacao.beneficiario_programa_social',
                'caracterizacao.tipo_servico_saude',
            )
        if ver_acesso_tecnologias:
            fields = fields + (
                'caracterizacao.frequencia_acesso_internet',
                'caracterizacao.local_acesso_internet',
                'caracterizacao.quantidade_computadores',
                'caracterizacao.quantidade_notebooks',
                'caracterizacao.quantidade_netbooks',
                'caracterizacao.quantidade_smartphones',
            )
        if ver_inscricoes_em_programas:
            custom_fields.update(get_inscricoes_em_programas=Column('Inscrições em Programas', accessor='get_inscricoes_programas_resumido'))
        if ver_inscricoes_em_programas:
            custom_fields.update(get_inscricoes_em_programas=Column('Inscrições em Programas', accessor='get_inscricoes_programas'))
        if ver_documentacao:
            custom_fields.update(get_situacao_documentacao=Column('Documentação', accessor='get_situacao_documentacao'))

        sequence = ['matricula']
        table = get_table(queryset=alunos.distinct(), fields=fields, custom_fields=custom_fields, sequence=sequence, per_page_field=100)
        if request.GET.get("relatorio", None):
            return tasks.table_export(request.GET.get("relatorio", None), *table.get_params())

    return locals()


@rtr()
@permission_required('ae.pode_detalhar_programa_todos, ae.pode_detalhar_programa_do_campus')
def relatorio_erro_participacoes(request):
    title = 'Relatório de Participações Conflitantes'
    participacoes_abertas = OrderedDict()
    campus = request.GET.get('campus')
    participacoes = Participacao.get_conflitos(request.user, tamanho=4, campus=campus)
    for participacao in participacoes:
        participacoes_abertas[participacao] = participacao.inscricao.get_participacao_aberta() or None
    return locals()


@rtr()
@permission_required('ae.pode_ver_relatorios_todos, ae.pode_ver_relatorios_campus')
def dashboard(request):
    title = 'Dashboard'

    resultado = []
    ano = False
    prazo_expiracao = Configuracao.get_valor_por_chave('ae', 'prazo_expiracao_documentacao')
    total_dias = prazo_expiracao and int(prazo_expiracao) or 365
    data_para_expiracao = somar_data(datetime.datetime.now(), -total_dias)
    campus = get_uo(request.user)
    ano = datetime.datetime.now().today().year
    registro_ano = Ano.objects.get(ano=ano)
    form = DashboardForm(request.POST or None, initial={'campus': get_uo(request.user).id, 'ano': registro_ano.id})

    if form.is_valid():
        if form.cleaned_data.get('campus'):
            campus = form.cleaned_data.get('campus')
        if form.cleaned_data.get('ano'):
            ano = form.cleaned_data.get('ano').ano

    # Participações Conflitantes
    participacoes_conflitantes = len(Participacao.get_conflitos(request.user, tamanho=5, campus=campus))

    # Participantes com Documentação Expirada
    documentacao_expirada = Participacao.objects.filter(programa__instituicao=campus)
    documentacao_expirada = documentacao_expirada.exclude(data_termino__lt=datetime.datetime.today())
    documentacao_expirada = documentacao_expirada.exclude(aluno__data_documentacao__gte=data_para_expiracao)
    documentacao_expirada = documentacao_expirada.values_list('aluno_id').distinct().count()

    # Financeiro
    tem_valor_refeicao = True
    tem_valor_bolsa = True
    tem_recursos_transporte = True
    tem_recursos_auxilios = True
    tem_recursos_bolsas = True
    valor_refeicao = valor_bolsa = recursos_transporte = recursos_bolsas = recursos_auxilios = 0

    oferta_refeicao_geral = OfertaValorRefeicao.objects.filter(campus=campus)
    oferta_bolsa_geral = OfertaValorBolsa.objects.filter(campus=campus)
    oferta_passe_geral = OfertaPasse.objects.filter(campus=campus)
    valor_total_auxilios_geral = ValorTotalAuxilios.objects.filter(campus=campus)
    valor_total_bolsas_geral = ValorTotalBolsas.objects.filter(campus=campus)

    # Financeiro: varre se há cadastro para todos os dias do ano
    inicio = date(ano, 1, 1)
    fim = date(ano, 12, 31)
    for idx in range(0, int((fim - inicio).days)):
        data = inicio + timedelta(idx)
        oferta_refeicao = oferta_refeicao_geral.filter(data_inicio__lte=data, data_termino__gte=data)
        oferta_bolsa = oferta_bolsa_geral.filter(data_inicio__lte=data, data_termino__gte=data)
        oferta_passe = oferta_passe_geral.filter(data_inicio__lte=data, data_termino__gte=data)
        valor_total_auxilios = valor_total_auxilios_geral.filter(data_inicio__lte=data, data_termino__gte=data)
        valor_total_bolsas = valor_total_bolsas_geral.filter(data_inicio__lte=data, data_termino__gte=data)

        if tem_valor_refeicao and not oferta_refeicao.exists():
            tem_valor_refeicao = False
        if tem_valor_bolsa and not oferta_bolsa.exists():
            tem_valor_bolsa = False
        if tem_recursos_transporte and not oferta_passe.exists():
            tem_recursos_transporte = False
        if tem_recursos_auxilios and not valor_total_auxilios.exists():
            tem_recursos_auxilios = False
        if tem_recursos_bolsas and not valor_total_bolsas.exists():
            tem_recursos_bolsas = False

    # Financeiro: Últimos valores Valor Refeição
    oferta_refeicao = oferta_refeicao_geral.filter(data_inicio__year=ano, data_termino__year=ano)
    if oferta_refeicao.exists():
        valor_refeicao = oferta_refeicao.order_by('-id')[0].valor

    # Financeiro: Últimos valores Valor Bolsa
    oferta_bolsa = oferta_bolsa_geral.filter(data_inicio__year=ano, data_termino__year=ano)
    if oferta_bolsa.exists():
        valor_bolsa = oferta_bolsa.order_by('-id')[0].valor

    # Financeiro: Últimos valores Recurso Planejado: Auxílio Transporte
    oferta_passe = oferta_passe_geral.filter(data_inicio__year=ano, data_termino__year=ano)
    if oferta_passe.exists():
        recursos_transporte = oferta_passe.order_by('-id')[0].valor_passe

    # Financeiro: Últimos valores Recurso Planejado: Auxílios
    valor_total_auxilios = valor_total_auxilios_geral.filter(data_inicio__year=ano, data_termino__year=ano)
    if valor_total_auxilios.exists():
        recursos_auxilios = valor_total_auxilios.order_by('-id')[0].valor

    # Financeiro: Últimos valores Recurso Planejado: Bolsas
    valor_total_bolsas = valor_total_bolsas_geral.filter(data_inicio__year=ano, data_termino__year=ano)
    if valor_total_bolsas.exists():
        recursos_bolsas = valor_total_bolsas.order_by('-id')[0].valor

    auxilios_atendidos = AtendimentoSetor.objects.filter(campus=campus, data__gte=date(ano, 1, 1))
    auxilios_atendidos = auxilios_atendidos.filter(data__lte=date(ano, 12, 31))

    if auxilios_atendidos.exists():
        valor_somado_dos_auxilios = auxilios_atendidos.aggregate(total=Sum('valor'))['total'] or 0
        saldo_auxilio = recursos_auxilios - valor_somado_dos_auxilios
    else:
        saldo_auxilio = recursos_auxilios

    solicitacoes_a_validar = SolicitacaoRefeicaoAluno.objects.filter(programa__instituicao=campus, avaliador_vinculo__isnull=True, data_auxilio__gte=datetime.datetime.now().today())

    alunos_nao_caracterizados = Aluno.objects.filter(
        situacao__ativo=True, matriculaperiodo__ano_letivo__ano=ano, curso_campus__diretoria__setor__uo=campus, caracterizacao__isnull=True
    )
    saldo_transporte = total_saldo_bolsa = 0

    data_inicio = date(ano, 1, 1)
    mes_atual = datetime.datetime.now().month
    if mes_atual == 12:
        data_termino = date(ano + 1, 1, 1)
    else:
        data_termino = date(ano, mes_atual + 1, 1)
    dias_do_mes = calendar.monthrange(ano, mes_atual)[1]
    achou_passes = False
    TWOPLACES = Decimal(10) ** -2
    SEARCH_QUERY_OFERTA = Q(campus=campus) & (
        Q(data_inicio__gte=date(ano, 1, 1), data_termino__lte=date(ano, 12, 31))
        | Q(data_inicio__lte=date(ano, 1, 1), data_termino__gte=date(ano, 12, 31))
        | Q(data_inicio__lte=date(ano, 1, 1), data_termino__gte=date(ano, 1, 1), data_termino__lte=date(ano, 12, 31))
        | Q(data_inicio__gte=date(ano, 1, 1), data_inicio__lte=date(ano, 12, 31), data_termino__gte=date(ano, 12, 31))
    )
    relatorio_passe = list()
    valor_total_passe = OfertaPasse.objects.filter(SEARCH_QUERY_OFERTA)
    lista_de_participacoes = Participacao.objects.filter(programa__instituicao=campus)
    lista_de_participacoes = lista_de_participacoes.filter(id__in=ParticipacaoPasseEstudantil.objects.values_list('participacao_id'))
    for periodo_passe in valor_total_passe:
        valor = 0.00
        somatorio = 0.00
        total_gasto = 0.00
        quantidade = 0
        demonstrativo_total_previsto = 0
        demonstrativo_total_pago = 0
        alunos = list()
        total_valor_mensal = total_dias_previstos = total_dias_pagos = 0
        SEARCH_QUERY_PASSES = (
            Q(data_inicio__lt=periodo_passe.data_inicio, data_termino__isnull=True)
            | Q(data_inicio__lt=periodo_passe.data_inicio, data_termino__gte=periodo_passe.data_inicio, data_termino__lte=periodo_passe.data_termino)
            | Q(data_inicio__lt=periodo_passe.data_inicio, data_termino__gt=periodo_passe.data_termino)
            | Q(data_inicio__gte=periodo_passe.data_inicio, data_inicio__lte=periodo_passe.data_termino)
        )
        participacoes_por_periodo = lista_de_participacoes.filter(SEARCH_QUERY_PASSES)
        if participacoes_por_periodo:
            for participacao in participacoes_por_periodo:
                passe_estudantil = ParticipacaoPasseEstudantil.objects.get(participacao_id=participacao.id)
                achou_passes = True
                if participacao.data_termino:
                    if (
                        participacao.data_inicio <= periodo_passe.data_inicio
                        and participacao.data_termino >= periodo_passe.data_inicio
                        and participacao.data_termino <= periodo_passe.data_termino
                    ):
                        ajuste_ultimo_dia = participacao.data_termino + timedelta(1)
                        calcula_meses = relativedelta(ajuste_ultimo_dia, periodo_passe.data_inicio)
                    elif participacao.data_inicio <= periodo_passe.data_inicio and participacao.data_termino >= periodo_passe.data_termino:
                        ajuste_ultimo_dia = periodo_passe.data_termino + timedelta(1)
                        calcula_meses = relativedelta(ajuste_ultimo_dia, periodo_passe.data_inicio)
                    else:
                        ajuste_ultimo_dia = periodo_passe.data_termino + timedelta(1)
                        calcula_meses = relativedelta(ajuste_ultimo_dia, participacao.data_inicio)
                else:
                    if participacao.data_inicio <= periodo_passe.data_inicio:
                        ajuste_ultimo_dia = periodo_passe.data_termino + timedelta(1)
                        calcula_meses = relativedelta(ajuste_ultimo_dia, periodo_passe.data_inicio)
                    else:
                        ajuste_ultimo_dia = periodo_passe.data_termino + timedelta(1)
                        calcula_meses = relativedelta(ajuste_ultimo_dia, participacao.data_inicio)
                quantidade += 1
                if calcula_meses.years:
                    meses = calcula_meses.years * 12
                else:
                    meses = calcula_meses.months
                diferenca_dias = calcula_meses.days
                diferenca_inicio = 0
                diferenca_termino = 0
                if passe_estudantil.valor_concedido:
                    if meses and not diferenca_dias:
                        valor = (Decimal(meses).quantize(TWOPLACES) * passe_estudantil.valor_concedido).quantize(TWOPLACES)
                    elif not meses and diferenca_dias:
                        valor = Decimal((Decimal(diferenca_dias).quantize(TWOPLACES) * passe_estudantil.valor_concedido) / 30).quantize(TWOPLACES)
                    else:
                        valor = (Decimal(meses).quantize(TWOPLACES) * passe_estudantil.valor_concedido).quantize(TWOPLACES) + Decimal(
                            (Decimal(diferenca_dias).quantize(TWOPLACES) * passe_estudantil.valor_concedido) / 30
                        ).quantize(TWOPLACES)

                    valor_mensal = passe_estudantil.valor_concedido
                    if participacao.data_inicio < data_termino:
                        if not participacao.data_termino or (participacao.data_termino and participacao.data_termino > data_inicio):
                            if participacao.data_inicio > data_inicio:
                                diferenca_inicio = (participacao.data_inicio - data_inicio).days
                            if participacao.data_termino and participacao.data_termino < data_termino:
                                diferenca_termino = (data_termino - participacao.data_termino).days

                            dias_pagos = (data_termino - data_inicio).days - diferenca_inicio - diferenca_termino

                            valor = Decimal((valor_mensal / 30) * dias_pagos).quantize(Decimal(10) ** -2)

                            somatorio = Decimal(somatorio) + Decimal(valor)

                            hoje = date.today()
                            ultimo_dia_ano = date(ano, 12, 31)
                            if participacao.data_termino and participacao.data_termino < ultimo_dia_ano and participacao.data_termino >= hoje:
                                variacao = (participacao.data_termino - hoje).days
                            elif participacao.data_termino and participacao.data_termino < hoje:
                                variacao = 0
                            else:
                                variacao = (data_termino - hoje).days

                            dias_pagos_efetivamente = dias_pagos - variacao
                            valor_gasto_efetivamente = Decimal((valor_mensal / 30) * dias_pagos_efetivamente).quantize(Decimal(10) ** -2)
                            alunos.append(
                                [
                                    participacao.aluno.pessoa_fisica.nome,
                                    participacao.aluno.matricula,
                                    participacao.data_inicio,
                                    participacao.data_termino,
                                    valor_mensal,
                                    dias_pagos,
                                    valor,
                                    dias_pagos_efetivamente,
                                    valor_gasto_efetivamente,
                                ]
                            )

                            total_valor_mensal = total_valor_mensal + valor_mensal
                            total_dias_previstos = total_dias_previstos + dias_pagos
                            total_dias_pagos = total_dias_pagos + dias_pagos_efetivamente
                            demonstrativo_total_previsto += valor
                            demonstrativo_total_pago += valor_gasto_efetivamente
                            total_gasto = Decimal(total_gasto).quantize(Decimal(10) ** -2) + Decimal(valor_gasto_efetivamente).quantize(Decimal(10) ** -2)

            if somatorio:
                saldo_transporte = Decimal(periodo_passe.valor_passe).quantize(TWOPLACES) - Decimal(total_gasto).quantize(TWOPLACES)
            else:
                saldo_transporte = periodo_passe.valor_passe

    TWOPLACES = Decimal(10) ** -2
    SEARCH_QUERY_OFERTA = Q(campus=campus) & (
        Q(data_inicio__gte=date(ano, 1, 1), data_termino__lte=date(ano, 12, 31))
        | Q(data_inicio__lte=date(ano, 1, 1), data_termino__gte=date(ano, 12, 31))
        | Q(data_inicio__lte=date(ano, 1, 1), data_termino__gte=date(ano, 1, 1), data_termino__lte=date(ano, 12, 31))
        | Q(data_inicio__gte=date(ano, 1, 1), data_inicio__lte=date(ano, 12, 31), data_termino__gte=date(ano, 12, 31))
    )

    valor_total_bolsa = ValorTotalBolsas.objects.filter(SEARCH_QUERY_OFERTA)
    valores_bolsa = OfertaValorBolsa.objects.filter(campus=campus)

    participacoes_por_periodo = False

    for item in valor_total_bolsa:
        valor = 0.00
        somatorio = 0.00
        saldo = 0.00
        tipo_vinculo_programa = CategoriaBolsa.objects.get(pk=item.categoriabolsa.id)
        SEARCH_QUERY_BOLSAS = (
            Q(data_inicio__lt=item.data_inicio, data_termino__isnull=True)
            | Q(data_inicio__lt=item.data_inicio, data_termino__gte=item.data_inicio, data_termino__lte=item.data_termino)
            | Q(data_inicio__lt=item.data_inicio, data_termino__gt=item.data_termino)
            | Q(data_inicio__gte=item.data_inicio, data_inicio__lte=item.data_termino)
        )

        if tipo_vinculo_programa.vinculo_programa == True:
            lista_de_participacoes = Participacao.objects.filter(programa__instituicao=campus)
            lista_de_participacoes = lista_de_participacoes.filter(id__in=ParticipacaoTrabalho.objects.values_list('participacao_id'))
            lista_de_bolsas = lista_de_participacoes.filter(SEARCH_QUERY_BOLSAS)
        else:
            lista_de_participacoes = ParticipacaoBolsa.objects.filter(
                aluno__curso_campus__diretoria__setor__uo=campus, categoria=item.categoriabolsa.id, categoria__vinculo_programa=False
            ).order_by('id')
            lista_de_bolsas = lista_de_participacoes.filter(SEARCH_QUERY_BOLSAS)

        if valores_bolsa:
            for valor_da_bolsa in valores_bolsa:
                if (
                    (valor_da_bolsa.data_inicio >= item.data_inicio and valor_da_bolsa.data_termino <= item.data_termino)
                    or (valor_da_bolsa.data_inicio < item.data_inicio and valor_da_bolsa.data_termino >= item.data_termino)
                    or (valor_da_bolsa.data_inicio < item.data_inicio and valor_da_bolsa.data_termino > item.data_inicio and valor_da_bolsa.data_termino < item.data_termino)
                    or (valor_da_bolsa.data_inicio >= item.data_inicio and valor_da_bolsa.data_inicio < item.data_termino and valor_da_bolsa.data_termino >= item.data_termino)
                ):
                    SEARCH_QUERY_VALORES = (
                        Q(data_inicio__lt=valor_da_bolsa.data_inicio, data_termino__isnull=True)
                        | Q(data_inicio__lt=valor_da_bolsa.data_inicio, data_termino__gte=valor_da_bolsa.data_inicio, data_termino__lte=valor_da_bolsa.data_termino)
                        | Q(data_inicio__lt=valor_da_bolsa.data_inicio, data_termino__gt=valor_da_bolsa.data_termino)
                        | Q(data_inicio__gte=valor_da_bolsa.data_inicio, data_inicio__lte=valor_da_bolsa.data_termino)
                    )
                    participacoes_por_periodo = lista_de_bolsas.filter(SEARCH_QUERY_VALORES)
                    if participacoes_por_periodo:
                        achou_bolsas = True
                        for participacao in participacoes_por_periodo:
                            if participacao.data_termino:
                                if (
                                    participacao.data_inicio <= valor_da_bolsa.data_inicio
                                    and participacao.data_termino >= valor_da_bolsa.data_inicio
                                    and participacao.data_termino <= valor_da_bolsa.data_termino
                                ):
                                    ajuste_ultimo_dia = participacao.data_termino + timedelta(1)
                                    calcula_meses = relativedelta(ajuste_ultimo_dia, valor_da_bolsa.data_inicio)
                                elif participacao.data_inicio <= valor_da_bolsa.data_inicio and participacao.data_termino >= valor_da_bolsa.data_termino:
                                    ajuste_ultimo_dia = valor_da_bolsa.data_termino + timedelta(1)
                                    calcula_meses = relativedelta(ajuste_ultimo_dia, valor_da_bolsa.data_inicio)
                                else:
                                    ajuste_ultimo_dia = valor_da_bolsa.data_termino + timedelta(1)
                                    calcula_meses = relativedelta(ajuste_ultimo_dia, participacao.data_inicio)
                            else:
                                if participacao.data_inicio <= valor_da_bolsa.data_inicio:
                                    ajuste_ultimo_dia = valor_da_bolsa.data_termino + timedelta(1)
                                    calcula_meses = relativedelta(ajuste_ultimo_dia, valor_da_bolsa.data_inicio)
                                else:
                                    ajuste_ultimo_dia = valor_da_bolsa.data_termino + timedelta(1)
                                    calcula_meses = relativedelta(ajuste_ultimo_dia, participacao.data_inicio)
                            if calcula_meses.years:
                                meses = calcula_meses.years * 12
                            else:
                                meses = calcula_meses.months
                            diferenca_dias = calcula_meses.days
                            if meses and not diferenca_dias:
                                valor = (Decimal(meses).quantize(TWOPLACES) * valor_da_bolsa.valor).quantize(TWOPLACES)
                            elif not meses and diferenca_dias:
                                valor = Decimal((Decimal(diferenca_dias).quantize(TWOPLACES) * valor_da_bolsa.valor) / 30).quantize(TWOPLACES)
                            else:
                                valor = (Decimal(meses).quantize(TWOPLACES) * valor_da_bolsa.valor).quantize(TWOPLACES) + Decimal(
                                    (Decimal(diferenca_dias).quantize(TWOPLACES) * valor_da_bolsa.valor) / 30
                                ).quantize(TWOPLACES)
                            somatorio = Decimal(somatorio) + Decimal(valor)
                        if somatorio:
                            saldo = Decimal(item.valor).quantize(TWOPLACES) - Decimal(somatorio).quantize(TWOPLACES)
                        else:
                            saldo = item.valor
            if participacoes_por_periodo:

                total_saldo_bolsa = total_saldo_bolsa + saldo

    resultado.append(
        dict(
            campus=campus.sigla,
            participacoes_conflitantes=participacoes_conflitantes,
            documentacao_expirada=documentacao_expirada,

            # Valor Refeição
            tem_valor_refeicao=tem_valor_refeicao,
            valor_refeicao=valor_refeicao,

            # Valor Bolsa
            tem_valor_bolsa=tem_valor_bolsa,
            valor_bolsa=valor_bolsa,

            # Auxílio-Transporte
            tem_recursos_transporte=tem_recursos_transporte,
            ha_saldo_recursos_transporte=saldo_transporte > 0,
            recursos_transporte=recursos_transporte,
            saldo_transporte=saldo_transporte,

            # Auxílios
            tem_recursos_auxilios=tem_recursos_auxilios,
            ha_saldo_recursos_auxilios=saldo_auxilio > 0,
            recursos_auxilios=recursos_auxilios,
            saldo_auxilios=saldo_auxilio,

            # Bolsas
            tem_recursos_bolsas=tem_recursos_bolsas,
            ha_saldo_recursos_bolsa=total_saldo_bolsa > 0,
            recursos_bolsas=recursos_bolsas,
            recursos_bolsa=total_saldo_bolsa,

            solicitacoes_refeicao=solicitacoes_a_validar.count(),
            alunos_sem_caracterizacao=alunos_nao_caracterizados.count(),
        )
    )
    return locals()


@rtr()
@permission_required('ae.pode_importar_caracterizacao')
def importar_caracterizacao_edital_ano(request):
    title = 'Importar Caracterização'
    form = ImportarCaracterizacaoForm(request.POST or None)
    if form.is_valid():
        try:
            numero_recebidas, numero_importadas = form.processar()
            return httprr('.', f'Número de caracterizações recebidas {numero_recebidas} e importadas {numero_importadas}')
        except Exception as e:
            capture_exception(e)
            if settings.DEBUG:
                raise e
            return httprr('.', 'Erro ao tentar importar a caracterização.', 'error')
    return locals()


@rtr()
@permission_required('ae.change_demandaalunoatendida')
def atendimento(request, pk):
    title = 'Visualizar Atendimento'
    atendimento = get_object_or_404(DemandaAlunoAtendida, pk=pk)
    if not request.user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
        if atendimento.campus != get_uo(request.user):
            raise PermissionDenied
        if request.user.groups.filter(name='Nutricionista').exists():
            if atendimento.demanda not in [DemandaAluno.CAFE, DemandaAluno.ALMOCO, DemandaAluno.JANTAR] and not atendimento.demanda.eh_kit_alimentacao:
                raise PermissionDenied
        if request.user.groups.filter(name='Coordenador de Atividades Estudantis').exists() and not request.user.groups.filter(name__in=['Coordenador de Atividades Estudantis Sistêmico', 'Bolsista do Serviço Social', 'Assistente Social']).exists():
            if not atendimento.demanda.eh_kit_alimentacao:
                raise PermissionDenied
    return locals()


@rtr()
@permission_required('ae.pode_ver_comprovante_inscricao')
def parecer_inscricao(request, inscricao_id):
    inscricao = get_object_or_404(Inscricao, pk=inscricao_id)
    title = f'Parecer da Inscrição {inscricao}'
    form = ParecerInscricaoForm(request.POST or None, instance=inscricao)
    if form.is_valid():
        o = form.save(False)
        o.parecer_autor_vinculo = request.user.get_vinculo()
        o.parecer_data = datetime.datetime.now()
        o.save()
        return httprr('/admin/ae/inscricao/', 'Parecer cadastrado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.view_mensagementrada')
def solicitar_refeicao(request, programa_id):
    title = "Solicitar Refeição"

    programa = get_object_or_404(Programa, pk=programa_id)
    aluno = get_object_or_404(Aluno, matricula=request.user.username)
    pessoa_fisica_aluno = aluno.pessoa_fisica

    if not (programa.instituicao == aluno.curso_campus.diretoria.setor.uo):
        return httprr('/', 'Este programa não pertence ao seu campus.', tag='error')

    if programa.impedir_solicitacao_beneficio:
        return httprr('/', 'Este programa não permite a solicitação de refeição.', tag='error')

    if not aluno.situacao.ativo:
        return httprr('/', 'Apenas alunos ativos podem solicitar refeição.', tag='error')

    if not hasattr(aluno, 'caracterizacao'):
        return httprr('/', 'Você precisa responder ao Questionário de Caracterização Socioeconômica para solicitar refeição.', tag='error')

    if not pessoa_fisica_aluno.template:
        return httprr('/', 'Você precisa ter uma digital cadastrada para solicitar refeição.', tag='error')

    if not (pessoa_fisica_aluno.email or pessoa_fisica_aluno.email_secundario or aluno.email_academico):
        return httprr('/', 'Você precisa ter um email cadastrado para solicitar refeição.', tag='error')
    else:
        tem_email = True

    if not HorarioSolicitacaoRefeicao.objects.filter(uo=aluno.curso_campus.diretoria.setor.uo).exists():
        return httprr('/', 'Seu campus não possui horário para solicitação de refeição cadastrado.', tag='error')

    tem_participacao = Participacao.abertas.filter(aluno=aluno, programa=programa)
    if ParticipacaoAlimentacao.objects.filter(participacao__in=tem_participacao.values_list('id', flat=True), suspensa=True).exists():
        return httprr('/', 'Sua participação está suspensa. Procure a assistência estudantil do seu campus.', tag='error')

    agora = datetime.datetime.now()
    uo = aluno.curso_campus.diretoria.setor.uo

    eh_dia_util = agora.weekday() not in [5, 6]

    tem_oferta = OfertaAlimentacao.objects.filter(campus=uo, dia_inicio__lte=agora.date(), dia_termino__gte=agora.date()).exists()

    if not tem_oferta:
        return httprr('/', 'Não existe oferta de alimentação cadastrada esta semana para o seu campus.', tag='error')

    horarios = HorarioSolicitacaoRefeicao.objects.filter(uo=uo)
    solicitacoes = SolicitacaoRefeicaoAluno.objects.filter(programa=programa_id, aluno=aluno).order_by('-data_solicitacao', '-data_auxilio', 'tipo_refeicao')

    horarios_permitidos = HorarioSolicitacaoRefeicao.objects.filter(
        uo=uo, hora_inicio__lte=agora, hora_fim__gte=agora, dia_fim=F('dia_inicio')
    ) | HorarioSolicitacaoRefeicao.objects.filter(Q(uo=uo), Q(hora_inicio__lte=agora) | Q(hora_fim__gte=agora), ~Q(dia_fim=F('dia_inicio')))
    form = SolicitacaoRefeicaoAlunoForm(data=request.POST or None, aluno=aluno, programa=programa, uo=uo)

    if form.is_valid():
        solicitacao = form.save(commit=False)
        solicitacao.motivo_solicitacao = form.cleaned_data.get('escolha_motivo_solicitacao').descricao
        horario = HorarioSolicitacaoRefeicao.objects.get(id=form.cleaned_data['tipo_refeicao_escolhido'])
        agora = datetime.datetime.now()
        horarios_permitidos = HorarioSolicitacaoRefeicao.objects.filter(
            uo=uo, hora_inicio__lte=agora, hora_fim__gte=agora, dia_fim=F('dia_inicio')
        ) | HorarioSolicitacaoRefeicao.objects.filter(Q(uo=uo), Q(hora_inicio__lte=agora) | Q(hora_fim__gte=agora), ~Q(dia_fim=F('dia_inicio')))
        if horario.id in horarios_permitidos.values_list('id', flat=True):
            hoje = date.today()
            amanha = hoje + timedelta(days=1)
            if amanha.weekday() == 5:
                amanha = hoje + timedelta(days=3)
            elif amanha.weekday() == 6:
                amanha = hoje + timedelta(days=2)

            if horario.dia_inicio == horario.dia_fim:
                if horario.dia_inicio == HorarioSolicitacaoRefeicao.DIA_ANTERIOR:
                    solicitacao.data_auxilio = amanha
                else:
                    solicitacao.data_auxilio = date.today()
            else:
                if (agora.time() < horario.hora_fim) and (agora.time() > horario.hora_inicio):
                    if form.cleaned_data['dia_solicitacao'] == TipoRefeicao.HOJE:
                        solicitacao.data_auxilio = date.today()
                    elif form.cleaned_data['dia_solicitacao'] == TipoRefeicao.AMANHA:
                        solicitacao.data_auxilio = amanha
                elif agora.time() < horario.hora_fim:
                    solicitacao.data_auxilio = date.today()
                else:
                    solicitacao.data_auxilio = amanha

            if DatasLiberadasFaltasAlimentacao.objects.filter(campus=uo, data=solicitacao.data_auxilio).exists():
                return httprr(
                    f'/ae/solicitar_refeicao/{programa.id:d}/',
                    f'O refeitório do seu campus não funcionará no dia {format_(solicitacao.data_auxilio)}.',
                    tag='error',
                )

            solicitacao.programa = programa
            solicitacao.tipo_refeicao = horario.tipo_refeicao

            if SolicitacaoRefeicaoAluno.objects.filter(
                ativa=True, programa=programa, aluno=solicitacao.aluno, tipo_refeicao=solicitacao.tipo_refeicao, data_auxilio=solicitacao.data_auxilio
            ).exists():
                return httprr(f'/ae/solicitar_refeicao/{programa.id:d}/', 'Esta solicitação já foi feita.', tag='error')

            if solicitacao.tipo_refeicao == TipoRefeicao.TIPO_CAFE:
                desc_tipo = AgendamentoRefeicao.TIPO_CAFE
            elif solicitacao.tipo_refeicao == TipoRefeicao.TIPO_ALMOCO:
                desc_tipo = AgendamentoRefeicao.TIPO_ALMOCO
            else:
                desc_tipo = AgendamentoRefeicao.TIPO_JANTAR

            if AgendamentoRefeicao.objects.filter(cancelado=False, programa=programa, aluno=solicitacao.aluno,
                                                  tipo_refeicao=desc_tipo,
                                                  data=solicitacao.data_auxilio).exists():
                return httprr(f'/ae/solicitar_refeicao/{programa.id:d}/',
                              'Você já possui um agendamento deste tipo de refeição para este dia.', tag='error')
            lista_de_participacoes = Participacao.objects.filter(programa=programa, aluno=aluno)
            lista_de_participacoes = lista_de_participacoes.filter(id__in=ParticipacaoAlimentacao.objects.values_list('participacao_id'))
            lista_de_participacoes = lista_de_participacoes.filter(Q(data_termino__isnull=True) | Q(data_termino__gte=solicitacao.data_auxilio))
            if lista_de_participacoes:
                participacao_ativa = lista_de_participacoes[0]
                participacao_alimentacao = ParticipacaoAlimentacao.objects.get(participacao=participacao_ativa)
                if solicitacao.tipo_refeicao == TipoRefeicao.TIPO_CAFE:
                    cafe = SolicitacaoAlimentacao.objects.get(pk=participacao_alimentacao.solicitacao_atendida_cafe.id)
                    if (
                        solicitacao.data_auxilio.weekday() == 0
                        and cafe.seg
                        or solicitacao.data_auxilio.weekday() == 1
                        and cafe.ter
                        or solicitacao.data_auxilio.weekday() == 2
                        and cafe.qua
                        or solicitacao.data_auxilio.weekday() == 3
                        and cafe.qui
                        or solicitacao.data_auxilio.weekday() == 4
                        and cafe.sex
                        or solicitacao.data_auxilio.weekday() == 5
                        and cafe.sab
                        or solicitacao.data_auxilio.weekday() == 6
                        and cafe.dom
                    ):
                        return httprr(f'/ae/solicitar_refeicao/{programa.id:d}/', 'O aluno já possui café da manhã agendado neste dia.', tag='error')

                elif solicitacao.tipo_refeicao == TipoRefeicao.TIPO_ALMOCO:
                    almoco = SolicitacaoAlimentacao.objects.get(pk=participacao_alimentacao.solicitacao_atendida_almoco.id)
                    if (
                        solicitacao.data_auxilio.weekday() == 0
                        and almoco.seg
                        or solicitacao.data_auxilio.weekday() == 1
                        and almoco.ter
                        or solicitacao.data_auxilio.weekday() == 2
                        and almoco.qua
                        or solicitacao.data_auxilio.weekday() == 3
                        and almoco.qui
                        or solicitacao.data_auxilio.weekday() == 4
                        and almoco.sex
                        or solicitacao.data_auxilio.weekday() == 5
                        and almoco.sab
                        or solicitacao.data_auxilio.weekday() == 6
                        and almoco.dom
                    ):
                        return httprr(f'/ae/solicitar_refeicao/{programa.id:d}/', 'O aluno já possui almoço agendado neste dia.', tag='error')

                elif solicitacao.tipo_refeicao == TipoRefeicao.TIPO_JANTAR:
                    jantar = SolicitacaoAlimentacao.objects.get(pk=participacao_alimentacao.solicitacao_atendida_janta.id)
                    if (
                        solicitacao.data_auxilio.weekday() == 0
                        and jantar.seg
                        or solicitacao.data_auxilio.weekday() == 1
                        and jantar.ter
                        or solicitacao.data_auxilio.weekday() == 2
                        and jantar.qua
                        or solicitacao.data_auxilio.weekday() == 3
                        and jantar.qui
                        or solicitacao.data_auxilio.weekday() == 4
                        and jantar.sex
                        or solicitacao.data_auxilio.weekday() == 5
                        and jantar.sab
                        or solicitacao.data_auxilio.weekday() == 6
                        and jantar.dom
                    ):
                        return httprr(f'/ae/solicitar_refeicao/{programa.id:d}/', 'O aluno já possui jantar agendado neste dia.', tag='error')
            solicitacao.ativa = True
            solicitacao.save()
            return httprr(f'/ae/solicitar_refeicao/{programa.id:d}/', 'Solicitação registrada com sucesso.')
        else:
            return httprr(f'/ae/solicitar_refeicao/{programa.id:d}/', 'Esta reserva não pode ser solicitada agora.', tag='error')

    return locals()


@rtr()
@permission_required('ae.add_agendamentorefeicao')
def avaliar_solicitacao_refeicao(request, programa_id):
    class Ordenacao:
        objetos_a_serem_ordenados = list()
        criterios = OrderedDict()

        def __init__(self, objetos_a_serem_ordenados):
            self.objetos_a_serem_ordenados = objetos_a_serem_ordenados

        def add_criterio(self, funcao, boleana=False, inversa=False):
            self.criterios[funcao] = {'boleana': boleana, 'inversa': inversa}

        def ordenar(self):
            listas_de_objetos_a_serem_ordenados = self.objetos_a_serem_ordenados
            if not listas_de_objetos_a_serem_ordenados:
                return list()

            listas_de_objetos_ordenados = list()

            for funcao in list(self.criterios.keys()):
                criterios = self.criterios[funcao]

                if criterios['boleana']:
                    temp_listas_de_objetos_a_serem_ordenados = list()

                    # ordenar os que não foram filtrados
                    def not_funcao(solicitacao):
                        return not funcao(solicitacao)

                    if not isinstance(listas_de_objetos_a_serem_ordenados[0], list):
                        lista_de_objetos_ordenados = list(filter(funcao, listas_de_objetos_a_serem_ordenados))
                        temp_listas_de_objetos_a_serem_ordenados.append(lista_de_objetos_ordenados)

                        lista_de_objetos_ordenados = list(filter(not_funcao, listas_de_objetos_a_serem_ordenados))
                        temp_listas_de_objetos_a_serem_ordenados.append(lista_de_objetos_ordenados)

                    else:
                        for lista_de_objetos_a_serem_ordenados in listas_de_objetos_a_serem_ordenados:
                            lista_de_objetos_ordenados = list(filter(funcao, lista_de_objetos_a_serem_ordenados))
                            temp_listas_de_objetos_a_serem_ordenados.append(lista_de_objetos_ordenados)

                            lista_de_objetos_ordenados = list(filter(not_funcao, lista_de_objetos_a_serem_ordenados))
                            temp_listas_de_objetos_a_serem_ordenados.append(lista_de_objetos_ordenados)

                    listas_de_objetos_ordenados = temp_listas_de_objetos_a_serem_ordenados

                listas_de_objetos_a_serem_ordenados = listas_de_objetos_ordenados

            for funcao in reversed(list(self.criterios.keys())):
                criterios = self.criterios[funcao]

                if not criterios['boleana']:
                    temp_listas_de_objetos_a_serem_ordenados = list()
                    if not isinstance(listas_de_objetos_a_serem_ordenados[0], list):
                        lista_de_objetos_ordenados = sorted(listas_de_objetos_a_serem_ordenados, key=funcao, reverse=criterios['inversa'])
                        temp_listas_de_objetos_a_serem_ordenados.append(lista_de_objetos_ordenados)
                    else:
                        for lista_de_objetos_a_serem_ordenados in listas_de_objetos_a_serem_ordenados:
                            lista_de_objetos_ordenados = sorted(lista_de_objetos_a_serem_ordenados, key=funcao, reverse=criterios['inversa'])
                            temp_listas_de_objetos_a_serem_ordenados.append(lista_de_objetos_ordenados)

                    listas_de_objetos_ordenados = temp_listas_de_objetos_a_serem_ordenados

                listas_de_objetos_a_serem_ordenados = listas_de_objetos_ordenados

            return listas_de_objetos_ordenados

    def ordenar_solicitacoes(solicitacoes, aluno_buscado):
        if aluno_buscado:
            solicitacoes = solicitacoes.filter(Q(aluno__pessoa_fisica__nome__icontains=aluno_buscado) | Q(aluno__matricula__icontains=aluno_buscado))

        solicitacoes_pendentes = solicitacoes.filter(ativa=True, deferida__isnull=True).order_by('data_auxilio', 'aluno__caracterizacao__renda_per_capita')
        solicitacoes_deferidas = solicitacoes.filter(deferida=True).order_by('-data_auxilio', 'tipo_refeicao', 'aluno')
        solicitacoes_indeferidas = solicitacoes.filter(deferida=False).order_by('-data_auxilio', 'tipo_refeicao', 'aluno')

        ordenacao = Ordenacao(list(solicitacoes_pendentes))

        # Critérios da Pré-seleção: os alunos solicitantes serão elencados, dentro da quantidade de vagas conforme a Tabela de Disponibilidade para o dia e tipo de refeição, na seguinte ordem:
        #
        #     Inscrição ativa em qualquer programa de Assistência Estudantil.
        def inscricao_ativa_program_AS(solicitacao):
            inscricao = solicitacao.aluno.inscricao_set.filter(ativa=True)
            return inscricao.exists()

        ordenacao.add_criterio(inscricao_ativa_program_AS, boleana=True, inversa=True)

        #     Documentação entregue e válida.
        def documentacao_valida(solicitacao):
            return solicitacao.aluno.documentada and not solicitacao.aluno.is_documentacao_expirada()

        ordenacao.add_criterio(documentacao_valida, boleana=True, inversa=True)

        #     Prioritário no programa de Alimentação.
        def prioritario_PA(solicitacao):
            inscricao = solicitacao.aluno.get_inscricao_programa_alimentacao()
            if inscricao:
                return inscricao.prioritaria

            return False

        ordenacao.add_criterio(prioritario_PA, boleana=True, inversa=True)

        #     Menor valor de renda per capita.
        def get_renda(solicitacao):
            return solicitacao.get_renda()

        ordenacao.add_criterio(get_renda)

        #     Não participação do programa de Alimentação.
        def nao_participantes_PA(solicitacao):
            if solicitacao.get_participacao_alimentacao():
                return False

            return True

        ordenacao.add_criterio(nao_participantes_PA, boleana=True)

        #     Ordem de solicitação.
        def get_data_solicitacao(solicitacao):
            return solicitacao.data_solicitacao

        ordenacao.add_criterio(get_data_solicitacao)

        solicitacoes_pendentes = ordenacao.ordenar()
        if solicitacoes_pendentes:
            solicitacoes_pendentes = reduce(operator.concat, solicitacoes_pendentes)

        return solicitacoes_pendentes, solicitacoes_deferidas, solicitacoes_indeferidas

    title = "Avaliar Solicitações de Refeição"
    programa = get_object_or_404(Programa, pk=programa_id)
    pode_avaliar_solicitacao = request.user.has_perm('ae.pode_gerenciar_ofertaalimentacao_do_campus')
    url = request.META.get('HTTP_REFERER', '.')
    form = TipoRefeicaoForm(request.GET or None)
    if request.method == 'GET':
        if request.GET.get('data'):
            try:
                data_buscada = datetime.datetime.strptime(request.GET.get('data'), "%Y-%m-%d").date()
            except Exception:
                return httprr(f'/ae/avaliar_solicitacao_refeicao/{programa_id}/', 'Formato de data inválido.', tag='error')

        else:
            data_buscada = date.today()

        tipo_refeicao = request.GET.get('tipo_refeicao', TipoRefeicao.TIPO_ALMOCO)
        aluno_buscado = request.GET.get('aluno', '')

        solicitacoes = SolicitacaoRefeicaoAluno.objects.filter(programa=programa, data_auxilio=data_buscada, tipo_refeicao=tipo_refeicao)

        solicitacoes_pendentes, solicitacoes_deferidas, solicitacoes_indeferidas = ordenar_solicitacoes(solicitacoes, aluno_buscado)

        qtd = 0
        dia_semana = data_buscada.weekday()
        if dia_semana in (5, 6):
            return httprr(f'/ae/avaliar_solicitacao_refeicao/{programa_id}/', 'Não existem refeições agendadas para o fim de semana.', tag='error')

        inicio_semana = data_buscada - timedelta(dia_semana)
        disponibilidade = programa.get_disponibilidade(inicio_semana)
        fim_semana = inicio_semana + timedelta(4)

        complemento_titulo = f'Semanal ({format_(inicio_semana)} a {format_(fim_semana)})'

        if disponibilidade:
            if tipo_refeicao == TipoRefeicao.TIPO_CAFE:
                qtd = disponibilidade['cafe']['oferta'][dia_semana] - disponibilidade['cafe']['demanda'][dia_semana]
            elif tipo_refeicao == TipoRefeicao.TIPO_ALMOCO:
                qtd = disponibilidade['almoco']['oferta'][dia_semana] - disponibilidade['almoco']['demanda'][dia_semana]
            elif tipo_refeicao == TipoRefeicao.TIPO_JANTAR:
                qtd = disponibilidade['jantar']['oferta'][dia_semana] - disponibilidade['jantar']['demanda'][dia_semana]

            solicitacoes_pendentes_pre_selecao = None
            if qtd > 0:
                solicitacoes_pendentes_pre_selecao = solicitacoes_pendentes[:qtd]

            if 'id' in request.GET and pode_avaliar_solicitacao:
                solicitacao = get_object_or_404(SolicitacaoRefeicaoAluno, pk=request.GET['id'])
                if 'deferir' in request.GET:
                    solicitacao.deferida = True
                    status = 'Deferida'
                    if solicitacao.tipo_refeicao == TipoRefeicao.TIPO_CAFE:
                        tipo_agendamento_solicitacao = AgendamentoRefeicao.TIPO_CAFE
                    elif solicitacao.tipo_refeicao == TipoRefeicao.TIPO_ALMOCO:
                        tipo_agendamento_solicitacao = AgendamentoRefeicao.TIPO_ALMOCO
                    else:
                        tipo_agendamento_solicitacao = AgendamentoRefeicao.TIPO_JANTAR

                    novo_agendamento = AgendamentoRefeicao.objects.update_or_create(cancelado=False, aluno=solicitacao.aluno, data=solicitacao.data_auxilio,
                                                                                    tipo_refeicao=tipo_agendamento_solicitacao,
                                                                                    programa=solicitacao.programa)[0]
                    solicitacao.agendamento = novo_agendamento
                    solicitacao.save()
                else:
                    solicitacao.deferida = False
                    status = 'Indeferida'

                solicitacao.avaliador_vinculo = request.user.get_vinculo()
                solicitacao.save()
                aluno = get_object_or_404(Aluno, pk=solicitacao.aluno.id)
                titulo = '[SUAP] Resposta à Solicitação de Refeição'
                texto = (
                    '<h1>Serviço Social</h1>'
                    '<h2>Resposta à Solicitação de Refeição</h2>'
                    '<p>Sua Solicitação de Refeição do tipo {} para o dia {} foi: <strong>{}</strong>.</p>'.format(
                        solicitacao.get_tipo_refeicao_display(), solicitacao.data_auxilio.strftime("%d/%m/%Y"), status
                    )
                )
                send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [aluno.get_vinculo()])
                return httprr(url, 'Solicitação avaliada com sucesso.')

    return locals()


@permission_required('edu.view_mensagementrada')
def busca_tipo_refeicao(request):
    from django.core import serializers

    data = []
    if request.method == 'GET':
        tipo_refeicao_escolhido = request.GET.get('tipo_refeicao_escolhido')
        if tipo_refeicao_escolhido:
            try:
                horario = HorarioSolicitacaoRefeicao.objects.filter(id=tipo_refeicao_escolhido)
                if horario.exists():
                    if (
                        (horario[0].dia_inicio != horario[0].dia_fim)
                        and (datetime.datetime.now().time() < horario[0].hora_fim)
                        and (datetime.datetime.now().time() > horario[0].hora_inicio)
                    ):
                        data = serializers.serialize('json', list(horario), fields=('id',))
            except Exception:
                return httprr('/', 'Tipo de refeição inválida.', tag='error')
    return HttpResponse(data, content_type='application/json')


@permission_required('edu.view_mensagementrada')
def cancelar_solicitacao_refeicao(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoRefeicaoAluno, pk=solicitacao_id)
    if solicitacao.pode_cancelar_solicitacao():
        solicitacao.ativa = False
        solicitacao.save()
        if solicitacao.agendamento:
            agendamento = solicitacao.agendamento
            agendamento.cancelado = True
            agendamento.cancelado_em = datetime.datetime.now()
            agendamento.cancelado_por = request.user.get_vinculo()
            agendamento.save()
        return httprr(f'/ae/solicitar_refeicao/{solicitacao.programa.id}/', 'Solicitação cancelada com sucesso.')
    else:
        return httprr(f'/ae/solicitar_refeicao/{solicitacao.programa.id}/', 'O período para cancelamento já terminou.', tag='error')


@rtr()
@permission_required('ae.pode_detalhar_programa_todos, ae.pode_detalhar_programa_do_campus')
def liberar_participacao_alimentacao(request, programa_id):
    programa = get_object_or_404(Programa, pk=programa_id)
    title = f'Participações Suspensas - {programa}'
    hoje = date.today()

    participacoes_suspensas = ParticipacaoAlimentacao.objects.filter(participacao__programa=programa, suspensa=True).order_by('suspensa_em', 'participacao__aluno')
    participacoes_suspensas = participacoes_suspensas.filter(Q(participacao__data_termino__isnull=True) | Q(participacao__data_termino__gte=hoje))
    form = LiberaParticipacaoAlimentacaoForm(request.POST or None)
    if request.POST and form.is_valid():
        if 'matricula_nome' in form.cleaned_data:
            participacoes_suspensas = participacoes_suspensas.filter(
                Q(participacao__aluno__matricula__icontains=form.cleaned_data.get('matricula_nome'))
                | Q(participacao__aluno__pessoa_fisica__nome__icontains=form.cleaned_data.get('matricula_nome'))
            )

    if 'libera' in request.GET and request.user.has_perm('ae.add_historicofaltasalimentacao'):
        participacao = get_object_or_404(ParticipacaoAlimentacao, pk=request.GET.get('libera'))
        if participacao.suspensa_em:
            novo_historico = HistoricoSuspensoesAlimentacao()
            novo_historico.participacao = participacao.participacao
            novo_historico.data_inicio = participacao.suspensa_em
            novo_historico.data_termino = datetime.datetime.now()
            novo_historico.liberado_por_vinculo = request.user.get_vinculo()
            novo_historico.save()
        participacao.suspensa = False
        participacao.suspensa_em = None
        participacao.save()
        if 'origem' in request.GET:
            return httprr(f'/ae/programa/{programa.id}/', 'Participação liberada com sucesso.')
        else:
            return httprr(f'/ae/liberar_participacao_alimentacao/{programa.id}/', 'Participação liberada com sucesso.')

    return locals()


@rtr()
@permission_required('edu.view_mensagementrada')
def justificar_falta(request, aluno_id, programa_id):
    title = "Informar Falta em Participação de Alimentação"
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    programa = get_object_or_404(Programa, pk=programa_id)
    hoje = date.today()
    amanha = hoje + timedelta(days=1)
    if request.user.get_relacionamento() != aluno:
        raise PermissionDenied
    participacao = Participacao.abertas.filter(aluno=aluno, programa=programa)
    if participacao.exists():
        participacao = participacao[0]
        horarios = HorarioJustificativaFalta.objects.filter(uo=programa.instituicao)
        cafe_hora = almoco_hora = jantar_hora = None
        cafe_dia = almoco_dia = jantar_dia = None
        if horarios.filter(tipo_refeicao=TipoRefeicao.TIPO_CAFE).exists():
            cafe_hora = horarios.filter(tipo_refeicao=TipoRefeicao.TIPO_CAFE)[0].hora_fim
            cafe_dia = horarios.filter(tipo_refeicao=TipoRefeicao.TIPO_CAFE)[0].get_dia_fim_display()
        if horarios.filter(tipo_refeicao=TipoRefeicao.TIPO_ALMOCO).exists():
            almoco_hora = horarios.filter(tipo_refeicao=TipoRefeicao.TIPO_ALMOCO)[0].hora_fim
            almoco_dia = horarios.filter(tipo_refeicao=TipoRefeicao.TIPO_ALMOCO)[0].get_dia_fim_display()
        if horarios.filter(tipo_refeicao=TipoRefeicao.TIPO_JANTAR).exists():
            jantar_hora = horarios.filter(tipo_refeicao=TipoRefeicao.TIPO_JANTAR)[0].hora_fim
            jantar_dia = horarios.filter(tipo_refeicao=TipoRefeicao.TIPO_JANTAR)[0].get_dia_fim_display()
        justificadas = HistoricoFaltasAlimentacao.objects.filter(aluno=aluno, justificativa__isnull=False)
        form = JustificaFaltaRefeicaoForm(request.POST or None)
        if form.is_valid():
            if DatasLiberadasFaltasAlimentacao.objects.filter(campus=programa.instituicao, data=form.cleaned_data.get('data')).exists():
                return httprr(
                    f'/ae/justificar_falta/{aluno.id}/{programa.id}/',
                    'Esta data já foi liberada pela assistência social, não sendo necessário justificar falta.',
                    tag='error',
                )
            if HistoricoFaltasAlimentacao.objects.filter(
                aluno=aluno, tipo_refeicao=form.cleaned_data.get('tipo_refeicao'), data=form.cleaned_data.get('data'), cancelada=False
            ).exists():
                return httprr(f'/ae/justificar_falta/{aluno.id}/{programa.id}/', 'Já foi cadastrada uma justificativa para este atendimento.', tag='error')

            if form.cleaned_data['data'] == hoje:
                if form.cleaned_data['tipo_refeicao'] == TipoRefeicao.TIPO_CAFE:
                    if cafe_dia == HorarioJustificativaFalta.DIA_CHOICES[1][1] and datetime.datetime.now().time() > cafe_hora:
                        return httprr(f'/ae/justificar_falta/{aluno.id}/{programa.id}/', f'O prazo para justificativa terminou às {cafe_hora}.', tag='error')
                    elif cafe_dia == HorarioJustificativaFalta.DIA_CHOICES[0][1]:
                        return httprr(
                            f'/ae/justificar_falta/{aluno.id}/{programa.id}/', f'O prazo para justificativa terminou ontem às {cafe_hora}.', tag='error'
                        )

                if form.cleaned_data['tipo_refeicao'] == TipoRefeicao.TIPO_ALMOCO:
                    if almoco_dia == HorarioJustificativaFalta.DIA_CHOICES[1][1] and datetime.datetime.now().time() > almoco_hora:
                        return httprr(f'/ae/justificar_falta/{aluno.id}/{programa.id}/', f'O prazo para justificativa terminou às {almoco_hora}.', tag='error')
                    elif almoco_dia == HorarioJustificativaFalta.DIA_CHOICES[0][1]:
                        return httprr(
                            f'/ae/justificar_falta/{aluno.id}/{programa.id}/', f'O prazo para justificativa terminou ontem às {almoco_hora}.', tag='error'
                        )

                if form.cleaned_data['tipo_refeicao'] == TipoRefeicao.TIPO_JANTAR:
                    if jantar_dia == HorarioJustificativaFalta.DIA_CHOICES[1][1] and datetime.datetime.now().time() > jantar_hora:
                        return httprr(f'/ae/justificar_falta/{aluno.id}/{programa.id}/', f'O prazo para justificativa terminou às {jantar_hora}.', tag='error')
                    elif jantar_dia == HorarioJustificativaFalta.DIA_CHOICES[0][1]:
                        return httprr(
                            f'/ae/justificar_falta/{aluno.id}/{programa.id}/', f'O prazo para justificativa terminou ontem às {jantar_hora}.', tag='error'
                        )

            elif form.cleaned_data['data'] == amanha:
                if form.cleaned_data['tipo_refeicao'] == TipoRefeicao.TIPO_CAFE:
                    if cafe_dia == HorarioJustificativaFalta.DIA_CHOICES[0][1] and datetime.datetime.now().time() > cafe_hora:
                        return httprr(f'/ae/justificar_falta/{aluno.id}/{programa.id}/', f'O prazo para justificativa terminou às {cafe_hora}.', tag='error')

                if form.cleaned_data['tipo_refeicao'] == TipoRefeicao.TIPO_ALMOCO:
                    if almoco_dia == HorarioJustificativaFalta.DIA_CHOICES[0][1] and datetime.datetime.now().time() > almoco_hora:
                        return httprr(f'/ae/justificar_falta/{aluno.id}/{programa.id}/', f'O prazo para justificativa terminou às {almoco_hora}.', tag='error')

                if form.cleaned_data['tipo_refeicao'] == TipoRefeicao.TIPO_JANTAR:
                    if jantar_dia == HorarioJustificativaFalta.DIA_CHOICES[0][1] and datetime.datetime.now().time() > jantar_hora:
                        return httprr(f'/ae/justificar_falta/{aluno.id}/{programa.id}/', f'O prazo para justificativa terminou às {jantar_hora}.', tag='error')

            nova_falta = HistoricoFaltasAlimentacao()
            nova_falta.aluno = aluno
            nova_falta.participacao = participacao
            nova_falta.programa = programa
            nova_falta.tipo_refeicao = form.cleaned_data.get('tipo_refeicao')
            nova_falta.data = form.cleaned_data.get('data')
            nova_falta.justificativa = form.cleaned_data.get('justificativa')
            nova_falta.justificada_em = datetime.datetime.now()
            nova_falta.justificada_por_vinculo = request.user.get_vinculo()
            nova_falta.save()
            return httprr(f'/ae/justificar_falta/{aluno.id}/{programa.id}/', 'Justificativa cadastrada com sucesso.')
    else:
        return httprr('/', 'Participação não encontrada.', tag='error')
    return locals()


@rtr()
@permission_required('ae.view_demandaalunoatendida')
def lista_alunodemandaatendida(request):
    hoje = datetime.datetime.today()
    return httprr(f'/admin/ae/demandaalunoatendida/?data__month={hoje.month}&data__year={hoje.year}')


@rtr()
@permission_required('edu.view_mensagementrada')
def redireciona_minhas_inscricoes(request):
    matricula = request.user.get_relacionamento().matricula
    return httprr(f'/edu/aluno/{matricula}/?tab=atividades_estudantis')


@rtr()
@permission_required('edu.view_mensagementrada')
def cancelar_justificativa_falta(request, solicitacao_id):
    solicitacao = get_object_or_404(HistoricoFaltasAlimentacao, pk=solicitacao_id)
    if solicitacao.data > date.today():
        solicitacao.cancelada = True
        solicitacao.save()
        return httprr(f'/ae/justificar_falta/{solicitacao.aluno.id}/{solicitacao.participacao.programa.id}/', 'Cancelamento cadastrado com sucesso.')
    else:
        return httprr(f'/ae/justificar_falta/{solicitacao.aluno.id}/{solicitacao.participacao.programa.id}/', 'O prazo para cancelamento já terminou.', tag='error')


@rtr()
@permission_required('ae.pode_ver_lista_dos_alunos')
def relatorio_alunos_aptos(request):
    title = "Relatório Estatístico de Alunos Aptos"
    form = RelatorioAlunosAptosForm(request.GET or None, request=request)
    if form.is_valid():
        key = 'curso_campus__diretoria__setor__uo__sigla'
        alunos_matriculados, alunos_caracterizados, alunos_filtrados, alunos_quartos_anos_integrado, alunos_eja, exportar_excel = form.processar()
        dados = {}
        for sigla, n in alunos_matriculados.values_list(key).annotate(Count('id')).order_by():
            dados[sigla] = [n, 0, 0, 0, 0]
        for sigla, n in alunos_caracterizados.values_list(key).annotate(Count('id')).order_by():
            dados[sigla][1] = n
        for sigla, n in alunos_filtrados.values_list(key).annotate(Count('id')).order_by():
            dados[sigla][2] = n
        for sigla, n in alunos_quartos_anos_integrado.values_list(key).annotate(Count('id')).order_by():
            dados[sigla][3] = n
        for sigla, n in alunos_eja.values_list(key).annotate(Count('id')).order_by():
            dados[sigla][4] = n

        if exportar_excel:
            lista = [['Campus', 'Matriculados', 'Caracterizados', 'Com os Critérios informados', '4º Ano do Integrado', 'Integrado EJA']]
            for sigla, totais in list(dados.items()):
                totais.insert(0, sigla)
                lista.append(totais)
            return XlsResponse(rows=lista)

    return locals()


@rtr()
@permission_required('ae.view_atividadediversa')
def atividadediversa(request, pk):
    title = 'Visualizar Atividade Diversa'
    atividade = get_object_or_404(AtividadeDiversa, pk=pk)
    return locals()


@rtr()
@permission_required('ae.view_acaoeducativa')
def acaoeducativa(request, pk):
    title = 'Visualizar Ação Educativa'
    acao = get_object_or_404(AcaoEducativa, pk=pk)

    return locals()


@rtr()
@permission_required('ae.add_inscricaoalimentacao')
def informar_data_entrega_documentacao(request):
    title = 'Informar Data de Entrega da Documentação'
    url_origem = request.META.get('HTTP_REFERER', '.')
    if request.POST:
        form = DataEntregaDocumentacaoForm(request.POST or None)
        if form.is_valid():
            data = form.cleaned_data.get('data')
            ids = request.GET.get('ids') and request.GET.get('ids').split(',')
            for item in ids:
                inscricao_aluno = get_object_or_404(Inscricao, pk=item)
                inscricao_aluno.entrega_doc_atualizada_por = request.user.get_vinculo()
                inscricao_aluno.entrega_doc_atualizada_em = datetime.datetime.now()
                inscricao_aluno.save()
                aluno = inscricao_aluno.aluno
                aluno.documentada = True
                aluno.data_documentacao = data
                aluno.save()
            return httprr(form.cleaned_data.get('url'), 'Entrega de documentação realizada com sucesso.')

    else:
        form = DataEntregaDocumentacaoForm(request.POST or None, url=url_origem)

    return locals()


@rtr()
@permission_required('ae.add_inscricaoalimentacao')
def informar_ausencia_documentacao(request):
    url_origem = request.META.get('HTTP_REFERER', '.')
    ids = request.GET.get('ids').split(',')
    for item in ids:
        inscricao_aluno = get_object_or_404(Inscricao, pk=item)
        inscricao_aluno.entrega_doc_atualizada_por = request.user.get_vinculo()
        inscricao_aluno.entrega_doc_atualizada_em = datetime.datetime.now()
        inscricao_aluno.save()
        aluno = inscricao_aluno.aluno
        aluno.documentada = False
        aluno.data_documentacao = None
        aluno.save()

    return httprr(url_origem, 'Registro de ausência de documentação realizada com sucesso.')


@rtr()
@transaction.atomic
@permission_required('ae.pode_revogar_participacao')
def editar_participacao(request, participacao_id):
    title = 'Editar Participação'

    participacao = get_object_or_404(Participacao, pk=participacao_id)
    if participacao.programa.tipo_programa.sigla:
        form = EditarParticipacaoForm(data=request.POST or None, instance=participacao)
    else:
        form = EditarPerguntaParticipacaoForm(request.POST or None, programa=participacao.programa)
    if form.is_valid():
        if participacao.programa.tipo_programa.sigla:
            o = form.save(False)
        else:
            o = participacao
            o.data_termino = form.cleaned_data.get('data_termino')
        o.finalizado_por = request.user.get_vinculo()
        o.finalizado_em = datetime.datetime.now()
        o.motivo_termino = 'Edição da participação.'
        o.save()
        nova_participacao = Participacao()
        nova_participacao.programa = participacao.programa
        nova_participacao.aluno = participacao.aluno
        nova_participacao.inscricao = participacao.inscricao
        nova_participacao.data_inicio = form.cleaned_data.get('data_termino') + timedelta(1)
        nova_participacao.motivo_entrada = 'Edição da participação.'
        nova_participacao.atualizado_por = request.user.get_vinculo()
        nova_participacao.atualizado_em = datetime.datetime.now()
        nova_participacao.save()
        if participacao.programa.get_tipo() == Programa.TIPO_TRABALHO:
            part_trab = ParticipacaoTrabalho()
            part_trab.participacao = nova_participacao
            part_trab.bolsa_concedida = form.cleaned_data.get('bolsa')
            part_trab.save()

        elif participacao.programa.get_tipo() == Programa.TIPO_IDIOMA:
            part_idioma = ParticipacaoIdioma()
            part_idioma.participacao = nova_participacao
            part_idioma.idioma = form.cleaned_data.get('idioma')
            part_idioma.save()

        elif participacao.programa.get_tipo() == Programa.TIPO_ALIMENTACAO:
            part_alimentacao = ParticipacaoAlimentacao()
            part_alimentacao.participacao = nova_participacao
            part_alimentacao.categoria = form.cleaned_data.get('categoria')
            part_alimentacao.save()

            solicitacao_cafe = SolicitacaoAlimentacao()
            for item in form.cleaned_data['cafe']:
                if int(item) == DiaSemanaChoices.SEGUNDA:
                    solicitacao_cafe.seg = True
                elif int(item) == DiaSemanaChoices.TERCA:
                    solicitacao_cafe.ter = True
                elif int(item) == DiaSemanaChoices.QUARTA:
                    solicitacao_cafe.qua = True
                elif int(item) == DiaSemanaChoices.QUINTA:
                    solicitacao_cafe.qui = True
                elif int(item) == DiaSemanaChoices.SEXTA:
                    solicitacao_cafe.sex = True
                elif int(item) == DiaSemanaChoices.SABADO:
                    solicitacao_cafe.sab = True
                elif int(item) == DiaSemanaChoices.DOMINGO:
                    solicitacao_cafe.dom = True
            solicitacao_cafe.save()

            solicitacao_almoco = SolicitacaoAlimentacao()
            for item in form.cleaned_data['almoco']:
                if int(item) == DiaSemanaChoices.SEGUNDA:
                    solicitacao_almoco.seg = True
                elif int(item) == DiaSemanaChoices.TERCA:
                    solicitacao_almoco.ter = True
                elif int(item) == DiaSemanaChoices.QUARTA:
                    solicitacao_almoco.qua = True
                elif int(item) == DiaSemanaChoices.QUINTA:
                    solicitacao_almoco.qui = True
                elif int(item) == DiaSemanaChoices.SEXTA:
                    solicitacao_almoco.sex = True
                elif int(item) == DiaSemanaChoices.SABADO:
                    solicitacao_almoco.sab = True
                elif int(item) == DiaSemanaChoices.DOMINGO:
                    solicitacao_almoco.dom = True
            solicitacao_almoco.save()

            solicitacao_jantar = SolicitacaoAlimentacao()
            for item in form.cleaned_data['jantar']:
                if int(item) == DiaSemanaChoices.SEGUNDA:
                    solicitacao_jantar.seg = True
                elif int(item) == DiaSemanaChoices.TERCA:
                    solicitacao_jantar.ter = True
                elif int(item) == DiaSemanaChoices.QUARTA:
                    solicitacao_jantar.qua = True
                elif int(item) == DiaSemanaChoices.QUINTA:
                    solicitacao_jantar.qui = True
                elif int(item) == DiaSemanaChoices.SEXTA:
                    solicitacao_jantar.sex = True
                elif int(item) == DiaSemanaChoices.SABADO:
                    solicitacao_jantar.sab = True
                elif int(item) == DiaSemanaChoices.DOMINGO:
                    solicitacao_jantar.dom = True
            solicitacao_jantar.save()

            part_alimentacao.solicitacao_atendida_cafe = solicitacao_cafe
            part_alimentacao.solicitacao_atendida_almoco = solicitacao_almoco
            part_alimentacao.solicitacao_atendida_janta = solicitacao_jantar
            part_alimentacao.save()

        elif participacao.programa.get_tipo() == Programa.TIPO_TRANSPORTE:
            part_transporte = ParticipacaoPasseEstudantil()
            part_transporte.participacao = nova_participacao
            part_transporte.valor_concedido = form.cleaned_data.get('valor_concedido')
            part_transporte.tipo_passe_concedido = form.cleaned_data.get('tipo_passe_concedido')
            part_transporte.save()
        else:
            chaves = list(request.POST.keys())
            for item in chaves:
                valores = request.POST.getlist(item)
                if 'pergunta_' in item:
                    id = item.split('_')[1]
                    pergunta_respondida = get_object_or_404(PerguntaParticipacao, pk=id)
                    for valor in valores:
                        resposta_informada = get_object_or_404(OpcaoRespostaPerguntaParticipacao, pk=int(valor))
                        if PerguntaParticipacao.objects.filter(id=id, ativo=True).exists():
                            nova = RespostaParticipacao()
                            nova.participacao = nova_participacao
                            nova.pergunta = pergunta_respondida
                            nova.resposta = resposta_informada
                            nova.save()

                elif 'texto_' in item:
                    id = item.split('_')[1]
                    valor_informado = valores[0]
                    pergunta_respondida = get_object_or_404(PerguntaParticipacao, pk=id)
                    if pergunta_respondida.tipo_resposta == PerguntaParticipacao.NUMERO:
                        valor_informado = valor_informado.replace('.', '').replace(',', '.')
                    nova = RespostaParticipacao()
                    nova.participacao = nova_participacao
                    nova.pergunta = pergunta_respondida
                    nova.valor_informado = valor_informado
                    nova.save()

        return httprr('..', 'Participação editada com sucesso.')

    return locals()


@rtr()
@permission_required('ae.pode_visualizar_auxilios')
def relatorio_planejamento(request):
    title = 'Relatório de Planejamento'
    form = RelatorioPlanejamentoForm(request.POST or None)
    if form.is_valid():
        ano_selecionado = get_object_or_404(Ano, ano=form.cleaned_data.get('ano'))
        tabela = {}
        caracterizacao = Caracterizacao.objects.all()
        campi = UnidadeOrganizacional.objects.uo().filter(municipio__isnull=False)
        if form.cleaned_data.get('campus'):
            campi = campi.filter(id=form.cleaned_data.get('campus').id)

        qs = MatriculaPeriodo.objects.filter(aluno__ano_letivo__ano__lte=date.today().year).exclude(aluno__turmaminicurso__gerar_matricula=False)
        for campus in campi:
            chave = f'{campus.sigla}'
            tabela[chave] = {}

            # ALUNOS MATRICULADOS
            matriculados = qs.filter(situacao__id__in=SituacaoMatriculaPeriodo.SITUACOES_MATRICULADO, aluno__curso_campus__diretoria__setor__uo=campus, ano_letivo=ano_selecionado)
            tabela[chave]['alunos_matriculados'] = Aluno.objects.filter(id__in=matriculados.values_list('aluno', flat=True)).distinct().count()

            # ALUNOS REGULARES
            regulares = matriculados.filter(aluno__curso_campus__matrizes__estrutura__isnull=True) | matriculados.filter(aluno__curso_campus__matrizes__estrutura__proitec=False)
            for convenio in Convenio.objects.all():  # TODO Verificar se é tratado de outra forma agora
                regulares = regulares.exclude(aluno__convenio=convenio.pk)
            regulares = regulares.exclude(aluno__curso_campus__modalidade__in=[Modalidade.ESPECIALIZACAO, Modalidade.MESTRADO, Modalidade.DOUTORADO])
            ids_regulares = list()
            for registro in regulares:
                if registro.matriculadiario_set.all().count() < 3:
                    ids_regulares.append(registro.id)
            regulares = regulares.exclude(id__in=ids_regulares)
            tabela[chave]['alunos_regulares'] = Aluno.objects.filter(id__in=regulares.values_list('aluno', flat=True)).count()

            # ALUNOS CARACTERIZADOS
            caracterizados = regulares.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
            tabela[chave]['alunos_caracterizados'] = Aluno.objects.filter(id__in=caracterizados.values_list('aluno', flat=True)).count()

            caract_ate_05 = Caracterizacao.objects.filter(renda_per_capita__lte=0.5, aluno__in=caracterizados.values_list('aluno', flat=True))
            tabela[chave]['aluno_renda_ate_05'] = Aluno.objects.filter(id__in=caract_ate_05.values_list('aluno', flat=True)).count()

            caract_entre_05_e_1 = Caracterizacao.objects.filter(renda_per_capita__gt=0.5, renda_per_capita__lte=1.0, aluno__in=caracterizados.values_list('aluno', flat=True))
            tabela[chave]['aluno_renda_entre_05_e_1'] = Aluno.objects.filter(id__in=caract_entre_05_e_1.values_list('aluno', flat=True)).count()

            caract_entre_1_e_15 = Caracterizacao.objects.filter(renda_per_capita__gt=1.0, renda_per_capita__lte=1.5, aluno__in=caracterizados.values_list('aluno', flat=True))
            tabela[chave]['aluno_renda_entre_1_e_15'] = Aluno.objects.filter(id__in=caract_entre_1_e_15.values_list('aluno', flat=True)).count()

            caract_maior_15 = Caracterizacao.objects.filter(renda_per_capita__gt=1.5, aluno__in=caracterizados.values_list('aluno', flat=True))
            tabela[chave]['aluno_renda_maior_15'] = Aluno.objects.filter(id__in=caract_maior_15.values_list('aluno', flat=True)).count()

            # ALUNOS COM PERFIL SOCIOECONOMICO
            intervalo_perfil_socioeconomico = caracterizacao.filter(renda_per_capita__lte=1.5)
            perfil_socioeconomico = caracterizados.filter(aluno__in=intervalo_perfil_socioeconomico.values_list('aluno', flat=True)).order_by('aluno__id').distinct()
            tabela[chave]['alunos_perfil_socioeconomico'] = Aluno.objects.filter(id__in=perfil_socioeconomico.values_list('aluno', flat=True)).count()

            # ALUNOS COM PERFIL SOCIOECONOMICO ATENDIDOS NOS PROGRAMAS
            data_inicio = date(ano_selecionado.ano, 1, 1)
            data_termino = date(ano_selecionado.ano, 12, 31)

            part_alim = Participacao.objects.filter(
                Q(programa__tipo_programa__sigla=Programa.TIPO_ALIMENTACAO),
                Q(data_termino__gte=data_inicio, data_inicio__lt=data_termino) | Q(data_termino__isnull=True, data_inicio__lte=data_termino),
            )
            perfil_socioeconomico_alim = perfil_socioeconomico.filter(aluno__in=part_alim.values_list('aluno', flat=True))
            tabela[chave]['alunos_perfil_socioeconomico_alm'] = Aluno.objects.filter(id__in=perfil_socioeconomico_alim.values_list('aluno', flat=True)).count()

            part_transp = Participacao.objects.filter(
                Q(participacaopasseestudantil__isnull=False),
                Q(data_termino__gte=data_inicio, data_inicio__lt=data_termino) | Q(data_termino__isnull=True, data_inicio__lte=data_termino),
            )
            perfil_socioeconomico_transp = perfil_socioeconomico.filter(aluno__in=part_transp.values_list('aluno', flat=True))
            tabela[chave]['alunos_perfil_socioeconomico_transp'] = Aluno.objects.filter(id__in=perfil_socioeconomico_transp.values_list('aluno', flat=True)).count()

            part_trab = Participacao.objects.filter(
                Q(programa__tipo_programa__sigla=Programa.TIPO_TRABALHO),
                Q(data_termino__gte=data_inicio, data_inicio__lt=data_termino) | Q(data_termino__isnull=True, data_inicio__lte=data_termino),
            )
            perfil_socioeconomico_trab = perfil_socioeconomico.filter(aluno__in=part_trab.values_list('aluno', flat=True))
            tabela[chave]['alunos_perfil_socioeconomico_trab'] = Aluno.objects.filter(id__in=perfil_socioeconomico_trab.values_list('aluno', flat=True)).count()

            # VALOR DA REFEICAO
            if OfertaValorRefeicao.objects.filter(campus=campus, data_inicio__lte=data_termino, data_termino__gte=data_termino).exists():
                registro = OfertaValorRefeicao.objects.filter(campus=campus, data_inicio__lte=data_termino, data_termino__gte=data_termino).order_by('-data_termino')[0]
                tabela[chave]['valor_refeicao'] = registro.valor
            else:
                tabela[chave]['valor_refeicao'] = None

            # VALOR MEDIO DE AUXILIO TRANSPORTE
            valor_gasto_transp_total = 0
            for item in Participacao.objects.filter(
                Q(aluno__in=perfil_socioeconomico_transp.values_list('aluno', flat=True)),
                Q(participacaopasseestudantil__isnull=False),
                Q(data_termino__gte=data_inicio, data_inicio__lt=data_termino) | Q(data_termino__isnull=True, data_inicio__lte=data_termino),
            ):
                valor_gasto_transp = 0
                for mes in range(1, 13):
                    inicio_mes = date(ano_selecionado.ano, mes, 1)
                    fim_mes = date(ano_selecionado.ano, mes, calendar.monthrange(ano_selecionado.ano, mes)[1])
                    dias_do_mes = calendar.monthrange(ano_selecionado.ano, mes)[1]
                    if (not item.data_termino and item.data_inicio <= fim_mes) or (item.data_termino and item.data_termino >= inicio_mes and item.data_inicio < fim_mes):
                        valor = item.sub_instance().valor_concedido
                        if item.data_inicio > data_inicio and item.data_inicio.month == int(mes):
                            diferenca = data_termino - item.data_inicio
                            valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)
                        if item.data_termino and item.data_termino < data_termino and item.data_termino.month == int(mes):
                            diferenca = item.data_termino - data_inicio
                            valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)
                        valor_gasto_transp += valor

                valor_gasto_transp_total += valor_gasto_transp

            tabela[chave]['valor_gasto_total_transp'] = valor_gasto_transp_total
            tabela[chave]['gasto_medio_total_transp'] = 0
            if tabela[chave]['alunos_perfil_socioeconomico_transp']:
                tabela[chave]['gasto_medio_total_transp'] = tabela[chave]['valor_gasto_total_transp'] / tabela[chave]['alunos_perfil_socioeconomico_transp']

            # VALOR DA BOLSA DE APOIO A FORMACAO ESTUDANTIL
            if OfertaValorBolsa.objects.filter(campus=campus, data_inicio__lte=data_termino, data_termino__gte=data_termino).exists():
                registro = OfertaValorBolsa.objects.filter(campus=campus, data_inicio__lte=data_termino, data_termino__gte=data_termino).order_by('-data_termino')[0]
                tabela[chave]['valor_bolsa_trab'] = registro.valor
            else:
                tabela[chave]['valor_bolsa_trab'] = None

            # VALOR GASTO COM APOIO A FORMACAO ESTUDANTIL
            valor_gasto_trab_total = 0
            for participacao_do_aluno in Participacao.objects.filter(
                Q(aluno__in=perfil_socioeconomico_trab.values_list('aluno', flat=True)),
                Q(participacaotrabalho__isnull=False),
                Q(data_termino__gte=data_inicio, data_inicio__lt=data_termino) | Q(data_termino__isnull=True, data_inicio__lte=data_termino),
            ):
                valor_gasto_trab = 0
                for mes in range(1, 13):
                    inicio_mes = date(ano_selecionado.ano, mes, 1)
                    fim_mes = date(ano_selecionado.ano, mes, calendar.monthrange(ano_selecionado.ano, mes)[1])
                    dias_do_mes = calendar.monthrange(ano_selecionado.ano, mes)[1]
                    if (not participacao_do_aluno.data_termino and participacao_do_aluno.data_inicio <= fim_mes) or (
                        participacao_do_aluno.data_termino and participacao_do_aluno.data_termino >= inicio_mes and participacao_do_aluno.data_inicio < fim_mes
                    ):
                        ofertas = OfertaValorBolsa.objects.filter(data_inicio__lte=fim_mes, data_termino__gte=inicio_mes, campus=campus)
                        if ofertas.exists():
                            valor = ofertas[0].valor
                            if valor:
                                if participacao_do_aluno.data_inicio > inicio_mes and participacao_do_aluno.data_inicio.month == mes:
                                    diferenca = fim_mes - participacao_do_aluno.data_inicio
                                    valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)
                                if participacao_do_aluno.data_termino and participacao_do_aluno.data_termino < fim_mes and participacao_do_aluno.data_termino.month == mes:
                                    diferenca = participacao_do_aluno.data_termino - inicio_mes
                                    valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)
                                if valor:
                                    valor_gasto_trab += valor
                valor_gasto_trab_total += valor_gasto_trab
            tabela[chave]['valor_gasto_bolsa_trab'] = valor_gasto_trab_total

            # ALUNOS ORIUNDOS DE ESCOLA PUBLICA
            escola_publica_cidade = Caracterizacao.objects.filter(aluno_exclusivo_rede_publica=True, aluno__cidade__nome=campus.municipio.nome)
            perfil_escola_publica_cidade = perfil_socioeconomico.filter(aluno__in=escola_publica_cidade.values_list('aluno', flat=True))
            tabela[chave]['rede_publica_municipio_sede'] = Aluno.objects.filter(id__in=perfil_escola_publica_cidade.values_list('aluno', flat=True)).count()
            escola_publica_outras_cidades = Caracterizacao.objects.filter(aluno_exclusivo_rede_publica=True).exclude(aluno__cidade__nome=campus.municipio.nome)
            perfil_escola_publica_outras_cidades = perfil_socioeconomico.filter(aluno__in=escola_publica_outras_cidades.values_list('aluno', flat=True))
            tabela[chave]['rede_publica_outros_municipios'] = Aluno.objects.filter(id__in=perfil_escola_publica_outras_cidades.values_list('aluno', flat=True)).count()

            # AUXILIOS
            tipos_atendimentos = TipoAtendimentoSetor.objects.all().order_by('id')
            ids_tipos_atendimentos = tipos_atendimentos.values_list('id', flat=True)
            tabela[chave]['auxilios'] = list()
            lista_valores_auxilios = list()
            for item in tipos_atendimentos:
                chave_atendimento = f'{item.id}'
                atendimentos = AtendimentoSetor.objects.filter(
                    Q(tipoatendimentosetor=item),
                    Q(campus=campus),
                    Q(data__year=ano_selecionado.ano) | Q(data_termino__year=ano_selecionado.ano),
                    Q(alunos__in=perfil_socioeconomico.values_list('aluno', flat=True)),
                )
                qtd = Aluno.objects.filter(id__in=atendimentos.values_list('alunos', flat=True)).count()
                lista_valores_auxilios.append(qtd)
            tabela[chave]['auxilios'] = lista_valores_auxilios

        resultado = collections.OrderedDict(sorted(tabela.items()))

    return locals()


@rtr()
@permission_required('ae.view_historicosuspensoesalimentacao')
def lista_historicosuspensoesalimentacao(request):
    hoje = datetime.datetime.today()
    return httprr(f'/admin/ae/historicosuspensoesalimentacao/?data__month={hoje.month}&data__year={hoje.year}')


@rtr()
@permission_required('ae.add_programa')
def relatorio_atendimentos_pnaes(request):
    title = 'Relatório de Atendimentos PNAES'
    form = RelatorioPNAESForm(request.GET or None)
    if form.is_valid():
        ano = form.cleaned_data.get('ano')
        campus = form.cleaned_data.get('campus')
        dias_do_ano = (date(ano, 12, 31) - date(ano, 1, 1)).days
        refeicoes = DemandaAlunoAtendida.objects.filter(demanda__in=[DemandaAluno.CAFE, DemandaAluno.ALMOCO, DemandaAluno.JANTAR], data__year=ano)

        if campus:
            refeicoes = refeicoes.filter(campus=campus)
        lista_alunos_alimentacao = Aluno.objects.filter(pessoa_fisica__cpf__isnull=False, id__in=refeicoes.values_list('aluno', flat=True))
        alunos_beneficiados_alimentacao = lista_alunos_alimentacao.count()
        qtd_media_almoco = refeicoes.filter(demanda=DemandaAluno.ALMOCO).count()
        if datetime.datetime.now().year == ano:
            qtd_dias = (datetime.datetime.now().date() - date(ano, 1, 1)).days
        else:
            qtd_dias = dias_do_ano
        qtd_media_almoco = qtd_media_almoco / qtd_dias
        total_orcamento_alimentacao = refeicoes.aggregate(total=Sum('valor'))['total']
        participantes_transporte = Participacao.objects.filter(
            Q(participacaopasseestudantil__isnull=False),
            Q(data_termino__gte=date(ano, 1, 1), data_inicio__lt=date(ano, 12, 31)) | Q(data_termino__isnull=True, data_inicio__lte=date(ano, 12, 31)),
        )
        if campus:
            participantes_transporte = participantes_transporte.filter(programa__instituicao=campus)
        lista_alunos_transporte = Aluno.objects.filter(pessoa_fisica__cpf__isnull=False, id__in=participantes_transporte.values_list('aluno', flat=True))
        alunos_beneficiados_transporte = lista_alunos_transporte.count()
        lista_alunos_transporte_valores = {}

        total_orcamento_transporte = 0
        for participacao_do_aluno in participantes_transporte.only('aluno', 'data_inicio', 'data_termino'):
            diferenca_inicio = diferenca_fim = 0
            valor = participacao_do_aluno.sub_instance().valor_concedido
            if valor:
                if participacao_do_aluno.data_inicio > date(ano, 1, 1):
                    diferenca_inicio = (participacao_do_aluno.data_inicio - date(ano, 1, 1)).days

                if participacao_do_aluno.data_termino and participacao_do_aluno.data_termino < date(ano, 12, 31):
                    diferenca_fim = (date(ano, 12, 31) - participacao_do_aluno.data_termino).days

                valor_diario = (valor * 12) / dias_do_ano

                valor = Decimal(valor_diario * (dias_do_ano - diferenca_inicio - diferenca_fim)).quantize(Decimal(10) ** -2)
                if valor:
                    total_orcamento_transporte += valor
                    nome_aluno = participacao_do_aluno.aluno.pessoa_fisica.nome
                    if nome_aluno in list(lista_alunos_transporte_valores.keys()):
                        lista_alunos_transporte_valores[nome_aluno] += valor
                    else:
                        lista_alunos_transporte_valores[nome_aluno] = valor

        if request.method == 'GET' and 'xls' not in request.GET:
            tabela = {}
            tipos = TipoAtendimentoSetor.objects.all()
            for tipo in tipos:
                atendimentos = AtendimentoSetor.objects.filter(tipoatendimentosetor=tipo, data__year=ano)
                if campus:
                    atendimentos = atendimentos.filter(campus=campus)
                if atendimentos.exists():
                    chave = f'{tipo}'
                    tabela[chave] = {}
                    qtd_atividades = atendimentos.count()
                    qtd_participantes = atendimentos.aggregate(total=Count('alunos'))
                    tabela[chave]['qtd_atividades'] = qtd_atividades
                    tabela[chave]['qtd_participantes'] = 0
                    if qtd_participantes['total']:
                        tabela[chave]['qtd_participantes'] = qtd_participantes['total'] / qtd_atividades
                    tabela[chave]['valor_total'] = atendimentos.aggregate(total=Sum('valor'))['total']

            resultado = collections.OrderedDict(sorted(tabela.items()))

        if request.method == 'GET' and 'xls' in request.GET:
            alunos_total = lista_alunos_alimentacao | lista_alunos_transporte
            ids_lista_alunos_alimentacao = lista_alunos_alimentacao.values_list('id', flat=True)
            ids_lista_alunos_transporte = lista_alunos_transporte.values_list('id', flat=True)
            alunos = alunos_total.distinct('pessoa_fisica__nome').order_by('pessoa_fisica__nome').only('curso_campus', 'pessoa_fisica', 'data_matricula')
            alunos_unicos = alunos_beneficiados_alimentacao + alunos_beneficiados_transporte
            return ae_tasks.exportar_relatorio_atendimento_pnaes_xls(
                alunos,
                ids_lista_alunos_alimentacao,
                ids_lista_alunos_transporte,
                lista_alunos_transporte_valores,

            )

    return locals()


@rtr()
@permission_required('ae.add_agendamentorefeicao')
def indeferir_solicitacoes(request, programa_id):
    programa = get_object_or_404(Programa, pk=programa_id)
    if not request.POST.getlist('action'):
        return httprr(f'/ae/avaliar_solicitacao_refeicao/{programa_id}/', 'Selecione uma ação.', tag='error')
    url = request.META.get('HTTP_REFERER', '.')
    if get_uo(request.user) == programa.instituicao and request.user.has_perm('ae.pode_gerenciar_ofertaalimentacao_do_campus') or request.user.has_perm('ae.save_caracterizacao_todos'):
        if request.POST.getlist('action')[0] == 'Deferir em massa':
            a_deferir = request.POST.getlist('registros')
            if a_deferir:
                status = 'Deferida'
                for item in a_deferir:
                    solicitacao = get_object_or_404(SolicitacaoRefeicaoAluno, pk=int(item))
                    solicitacao.deferida = True
                    if solicitacao.tipo_refeicao == TipoRefeicao.TIPO_CAFE:
                        tipo_agendamento_solicitacao = AgendamentoRefeicao.TIPO_CAFE
                    elif solicitacao.tipo_refeicao == TipoRefeicao.TIPO_ALMOCO:
                        tipo_agendamento_solicitacao = AgendamentoRefeicao.TIPO_ALMOCO
                    else:
                        tipo_agendamento_solicitacao = AgendamentoRefeicao.TIPO_JANTAR

                    novo_agendamento = \
                        AgendamentoRefeicao.objects.update_or_create(cancelado=False, aluno=solicitacao.aluno, data=solicitacao.data_auxilio,
                                                                     tipo_refeicao=tipo_agendamento_solicitacao,
                                                                     programa=solicitacao.programa)[0]
                    solicitacao.agendamento = novo_agendamento
                    solicitacao.avaliador_vinculo = request.user.get_vinculo()
                    solicitacao.save()
                    aluno = get_object_or_404(Aluno, pk=solicitacao.aluno.id)
                    titulo = '[SUAP] Resposta à Solicitação de Refeição'
                    texto = (
                        '<h1>Serviço Social</h1>'
                        '<h2>Resposta à Solicitação de Refeição</h2>'
                        '<p>Sua Solicitação de Refeição do tipo {} para o dia {} foi: {}.</p>'
                        '<p>Acesse o SUAP para mais detalhes.'.format(solicitacao.get_tipo_refeicao_display(), solicitacao.data_auxilio.strftime("%d/%m/%Y"), status)
                    )
                    send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [aluno.get_vinculo()])
                return httprr(url, 'Solicitações deferidas com sucesso.')
            else:
                return httprr(url, 'Nenhuma solicitação selecionada.', tag='error')

        elif request.POST.getlist('action')[0] == 'Indeferir em massa':
            indeferir = request.POST.getlist('registros')
            if indeferir:
                status = 'Indeferida'
                for item in indeferir:
                    solicitacao = get_object_or_404(SolicitacaoRefeicaoAluno, pk=int(item))
                    solicitacao.deferida = False
                    solicitacao.avaliador_vinculo = request.user.get_vinculo()
                    solicitacao.save()
                    aluno = get_object_or_404(Aluno, pk=solicitacao.aluno.id)
                    titulo = '[SUAP] Resposta à Solicitação de Refeição'
                    texto = (
                        '<h1>Serviço Social</h1>'
                        '<h2>Resposta à Solicitação de Refeição</h2>'
                        '<p>Sua Solicitação de Refeição do tipo {} para o dia {} foi: <strong>{}</strong>.</p>'.format(
                            solicitacao.get_tipo_refeicao_display(), solicitacao.data_auxilio.strftime("%d/%m/%Y"), status
                        )
                    )
                    send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [aluno.get_vinculo()])
                return httprr(url, 'Solicitações indeferidas com sucesso.')
            else:
                return httprr(url, 'Nenhuma solicitação selecionada.', tag='error')
        else:
            return httprr(url, 'Selecione uma ação.', tag='error')
    return httprr(f'/ae/avaliar_solicitacao_refeicao/{programa_id}/', 'Permissão negada.', tag='error')


@rtr()
@permission_required('ae.change_atividadediversa')
def cancelar_atividade_diversa(request, atividade_id):
    atividade = get_object_or_404(AtividadeDiversa, pk=atividade_id)
    if atividade.cancelada:
        atividade.cancelada = False
        atividade.cancelada_em = None
        atividade.cancelada_por_vinculo = None
    else:
        atividade.cancelada = True
        atividade.cancelada_em = datetime.datetime.now()
        atividade.cancelada_por_vinculo = request.user.get_vinculo()
    atividade.save()
    return httprr('/admin/ae/atividadediversa/', 'Atividade diversa cancelada com sucesso.')


@rtr()
@permission_required('ae.change_acaoeducativa')
def cancelar_acao_educativa(request, acao_id):
    acao = get_object_or_404(AcaoEducativa, pk=acao_id)
    if acao.cancelada:
        acao.cancelada = False
        acao.cancelada_em = None
        acao.cancelada_por_vinculo = None
    else:
        acao.cancelada = True
        acao.cancelada_em = datetime.datetime.now()
        acao.cancelada_por_vinculo = request.user.get_vinculo()
    acao.save()
    return httprr('/admin/ae/acaoeducativa/', 'Ação educativa cancelada com sucesso.')


@rtr()
@permission_required('ae.add_historicofaltasalimentacao')
def agendar_desbloqueio_alimentacao(request, participacaoalimentacao_id, programa_id):
    participacao = get_object_or_404(ParticipacaoAlimentacao, pk=participacaoalimentacao_id)
    title = f'Data de Desbloqueio Automático - {participacao.participacao.aluno}'
    form = AgendamentoDesbloqueioParticipacaoForm(request.POST or None, instance=participacao)
    if form.is_valid():
        o = form.save(False)
        o.liberado_por_vinculo = request.user.get_vinculo()
        o.save()
        titulo = '[SUAP] Desbloqueio Automático de Participação em Programa de Alimentação'
        texto = (
            '<h1>Serviço Social</h1>'
            '<h2>Desbloqueio Automático de Participação em Programa de Alimentação</h2>'
            '<p>O desbloqueio automático da sua participação no Programa de Alimentação Escolar foi cadastrada para o dia {}.</p>'
            '<p>Procure o setor de Serviço Social do seu campus para mais informações.</p>'.format(o.liberar_em.strftime("%d/%m/%Y"))
        )
        send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [participacao.participacao.aluno.get_vinculo()])
        return httprr(f'/ae/liberar_participacao_alimentacao/{programa_id}', 'Agendamento de desbloqueio realizado com sucesso.')
    return locals()


@rtr()
@permission_required('ae.add_agendamentorefeicao')
def redireciona_relatorio_semanal(request):
    programa = Programa.objects.filter(instituicao=get_uo(request.user), tipo_programa__sigla=Programa.TIPO_ALIMENTACAO)
    if programa.exists():
        return httprr(f'/ae/relatorio_semanal_refeitorio/{programa[0].id}/')
    elif request.user.has_perm('ae.pode_ver_relatorio_semanal'):
        title = 'Selecione o Campus'
        form = CampusForm(request.POST or None)
        if form.is_valid():
            if Programa.objects.filter(instituicao=form.cleaned_data.get('campus'), tipo_programa__sigla=Programa.TIPO_ALIMENTACAO).exists():
                programa = Programa.objects.filter(instituicao=form.cleaned_data.get('campus'), tipo_programa__sigla=Programa.TIPO_ALIMENTACAO)[0]
                return httprr(f'/ae/relatorio_semanal_refeitorio/{programa.id}/')
            else:
                return httprr('/ae/redireciona_relatorio_semanal/', 'Programa não encontrado.', tag='error')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('ae.add_agendamentorefeicao')
def redireciona_relatorio_diario(request):
    if (
        not request.user.has_perm('ae.pode_ver_relatorio_semanal')
        and Programa.objects.filter(instituicao=get_uo(request.user), tipo_programa__sigla=Programa.TIPO_ALIMENTACAO).exists()
    ):
        programa = Programa.objects.filter(instituicao=get_uo(request.user), tipo_programa__sigla=Programa.TIPO_ALIMENTACAO)[0]
        return httprr(f'/ae/relatorio_diario_refeitorio/{programa.id}/')
    elif request.user.has_perm('ae.pode_ver_relatorio_semanal'):
        title = 'Selecione o Campus'
        form = CampusForm(request.POST or None)
        if form.is_valid():
            if Programa.objects.filter(instituicao=form.cleaned_data.get('campus'), tipo_programa__sigla=Programa.TIPO_ALIMENTACAO).exists():
                programa = Programa.objects.filter(instituicao=form.cleaned_data.get('campus'), tipo_programa__sigla=Programa.TIPO_ALIMENTACAO)[0]
                return httprr(f'/ae/relatorio_diario_refeitorio/{programa.id}/')
            else:
                return httprr('/ae/redireciona_relatorio_diario/', 'Programa não encontrado.', tag='error')
        return locals()
    else:
        raise PermissionDenied


@permission_required('ae.add_agendamentorefeicao')
def imprimir_lista_diaria(request, programa_id, dia_semana):
    programa = get_object_or_404(Programa, pk=programa_id)
    categoria_busca = False
    agendados = None
    tipo_refeicao = None
    if request.method == 'GET':
        if 'pdf_data' in request.GET:
            data = datetime.datetime.strptime(request.GET['pdf_data'], '%d/%m/%Y')
            data = data.date()
            datas_liberadas = DatasLiberadasFaltasAlimentacao.objects.filter(campus=programa.instituicao)
            if data and datas_liberadas.filter(data=data).exists() or datas_liberadas.filter(recorrente=True, data__day=data.day, data__month=data.month).exists():
                return httprr(f'/ae/relatorio_diario_refeitorio/{programa_id}/', 'A data escolhida foi cadastrada como férias/recesso.', tag='error')
            elif data and data.weekday() in [5, 6]:
                return httprr(f'/ae/relatorio_diario_refeitorio/{programa_id}/', 'A data escolhida não é um dia útil.', tag='error')

        if 'pdf_tipo_refeicao' in request.GET:
            tipo_refeicao = int(request.GET['pdf_tipo_refeicao'])
        if 'categoria_busca' in request.GET and request.GET.get('categoria_busca'):
            categoria_busca = get_object_or_404(CategoriaAlimentacao, pk=request.GET['categoria_busca'])
        if 'agendados' in request.GET:
            if request.GET['agendados'] == 'True':
                agendados = True
        if tipo_refeicao:
            if tipo_refeicao == DemandaAluno.CAFE:
                tipo_refeicao_label = "CAFÉ DA MANHÃ"
                tipo_refeicao_agendada = AgendamentoRefeicao.TIPO_CAFE
                falta_tipo_refeicao = TipoRefeicao.TIPO_CAFE
            elif tipo_refeicao == DemandaAluno.ALMOCO:
                tipo_refeicao_label = "ALMOÇO"
                tipo_refeicao_agendada = AgendamentoRefeicao.TIPO_ALMOCO
                falta_tipo_refeicao = TipoRefeicao.TIPO_ALMOCO
            else:
                tipo_refeicao_label = "JANTAR"
                tipo_refeicao_agendada = AgendamentoRefeicao.TIPO_JANTAR
                falta_tipo_refeicao = TipoRefeicao.TIPO_JANTAR

            data_fim = somar_data(data, 1)
            registros_participacoes = Participacao.objects.filter(
                Q(programa=programa), Q(participacaoalimentacao__suspensa=False), Q(data_termino__isnull=True) | Q(data_termino__gte=data_fim), Q(data_inicio__lte=data)
            )
            if categoria_busca:
                registros_participacoes = registros_participacoes.filter(participacaoalimentacao__categoria=categoria_busca)

            registros_participacoes = registros_participacoes.values_list('aluno_id', flat=True)
            registros_agendados = AgendamentoRefeicao.objects.filter(cancelado=False, tipo_refeicao=tipo_refeicao_agendada, programa=programa, data__gte=data, data__lte=data_fim).values_list(
                'aluno_id', flat=True
            )

            registros_atendidos = DemandaAlunoAtendida.objects.filter(campus=programa.instituicao, demanda=tipo_refeicao, data__gte=data, data__lte=data_fim).values_list(
                'aluno_id', flat=True
            )

            ids = set()
            ids.update(registros_agendados)
            if not agendados:
                ids.update(registros_participacoes)
                ids.update(registros_atendidos)
            alunos = Aluno.objects.filter(id__in=ids).only('pessoa_fisica', 'matricula')

            count = 1
            atendimentos = []
            categoria_label = 'Atendimento Avulso'
            solicitacao_atendida = None
            for aluno in alunos:
                categoria = ""
                try:
                    inscricao = aluno.inscricao_set.get(programa=programa).sub_instance()
                except Inscricao.DoesNotExist:
                    inscricao = None

                except Exception:
                    # Ainda existem alunos com inscrições duplicadas (ver https://projetos.ifrn.edu.br/issues/3889)
                    # Existem alunos com participações que não tem os dados dos atendimentos
                    inscricoes = aluno.inscricao_set.filter(programa=programa, participacao__isnull=False, participacao__data_termino__isnull=True).distinct()
                    if inscricoes.exists():
                        inscricao = inscricoes[0].sub_instance()
                    else:
                        inscricao = None

                participacao_aberta = None
                participacao = None
                if inscricao:
                    try:
                        participacao = inscricao.get_ultima_participacao()
                        participacao_aberta = inscricao.get_participacao_aberta()
                    except Exception:
                        pass
                    if categoria_busca and participacao and participacao.sub_instance().categoria != categoria_busca:
                        continue
                    if participacao:
                        if tipo_refeicao == DemandaAluno.ALMOCO:
                            solicitacao_atendida = participacao.sub_instance().solicitacao_atendida_almoco
                        elif tipo_refeicao == DemandaAluno.JANTAR:
                            solicitacao_atendida = participacao.sub_instance().solicitacao_atendida_janta
                        elif tipo_refeicao == DemandaAluno.CAFE:
                            solicitacao_atendida = participacao.sub_instance().solicitacao_atendida_cafe
                    else:
                        solicitacao_atendida = None

                adiciona_aluno = False

                if get_atendimento(aluno, programa, tipo_refeicao, data):
                    if AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=data, tipo_refeicao=tipo_refeicao_agendada).exists():
                        adiciona_aluno = True

                    elif not agendados:
                        if (
                            solicitacao_atendida
                            and solicitacao_atendida.valida()
                            and (
                                (dia_semana == '0' and solicitacao_atendida.seg)
                                or (dia_semana == '1' and solicitacao_atendida.ter)
                                or (dia_semana == '2' and solicitacao_atendida.qua)
                                or (dia_semana == '3' and solicitacao_atendida.qui)
                                or (dia_semana == '4' and solicitacao_atendida.sex)
                            )
                        ):
                            if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= data)):
                                adiciona_aluno = True
                            else:
                                adiciona_aluno = True
                                categoria = categoria_label
                        else:
                            adiciona_aluno = True
                            categoria = categoria_label

                else:

                    if AgendamentoRefeicao.objects.filter(cancelado=False, aluno=aluno, data=data, tipo_refeicao=tipo_refeicao_agendada).exists():
                        adiciona_aluno = True

                    elif (
                        not agendados
                        and solicitacao_atendida
                        and solicitacao_atendida.valida()
                        and (
                            (dia_semana == '0' and solicitacao_atendida.seg)
                            or (dia_semana == '1' and solicitacao_atendida.ter)
                            or (dia_semana == '2' and solicitacao_atendida.qua)
                            or (dia_semana == '3' and solicitacao_atendida.qui)
                            or (dia_semana == '4' and solicitacao_atendida.sex)
                        )
                    ):
                        if participacao and ((not participacao.data_termino) or (participacao.data_termino and participacao.data_termino >= data)):
                            if not HistoricoFaltasAlimentacao.objects.filter(
                                justificativa__isnull=False, aluno=aluno, data=data, tipo_refeicao=falta_tipo_refeicao, cancelada=False
                            ).exists():
                                adiciona_aluno = True

                if inscricao and participacao_aberta:
                    categoria = participacao.participacaoalimentacao.categoria

                if not categoria:
                    categoria = 'Refeição Agendada'
                if adiciona_aluno:
                    dicionario = dict(count=count, matricula=aluno.matricula, pessoa_fisica=aluno.pessoa_fisica.nome, categoria=categoria)

                    atendimentos.append(dicionario)
                    count += 1

            uo = get_uo(request.user)
            topo = get_topo_pdf(f'Relatório Diário - Programa de Alimentação ({tipo_refeicao_label})')
            servidor = request.user.get_relacionamento()
            info = [["UO", uo], ["Servidor", servidor], ["Data", data.strftime("%d/%m/%Y")], ["Emitido em", datetime.datetime.now().strftime("%d/%m/%Y")]]
            dados = [['Matrícula', 'Aluno', 'Categoria', 'Restrição Alimentar', 'Assinatura']]
            for registro in atendimentos:
                ProcessoSaudeDoenca = apps.get_model('saude', 'ProcessoSaudeDoenca')
                AtendimentoNutricao = apps.get_model('saude', 'AtendimentoNutricao')
                lista_restricoes = list()
                if ProcessoSaudeDoenca:
                    processos_saude_doenca = ProcessoSaudeDoenca.objects.filter(atendimento__aluno__matricula=registro['matricula'])
                    if processos_saude_doenca.exists():
                        mais_recente = processos_saude_doenca.latest('id')
                        tem_alergia_alimentos = mais_recente.alergia_alimentos
                        if tem_alergia_alimentos:
                            lista_restricoes.append(mais_recente.que_alimentos)
                if AtendimentoNutricao:
                    atendimentos_nutricao = AtendimentoNutricao.objects.filter(atendimento__aluno__matricula=registro['matricula'])
                    if atendimentos_nutricao.exists():
                        atendimento = atendimentos_nutricao.latest('id')
                        for restricao in atendimento.restricao_alimentar.all():
                            lista_restricoes.append(restricao.descricao)

                dados.append([registro['matricula'], registro['pessoa_fisica'], registro['categoria'], ', '.join(lista_restricoes), ' '])
            tabela_info = pdf.table(info, grid=0, w=[30, 160])
            tabela_dados = pdf.table(dados, head=1, zebra=1, w=[30, 40, 30, 25, 70], count=1)
            body = topo + [tabela_info, pdf.space(8), tabela_dados, pdf.space(8)]

            return PDFResponse(pdf.PdfReport(body=body).generate())
        else:
            return httprr('..', 'Parâmetros incorretos.', tag='error')

    else:
        raise PermissionDenied


@rtr()
@permission_required('ae.add_agendamentorefeicao')
def relatorio_diario_refeitorio(request, programa_id):
    programa = get_object_or_404(Programa, id=programa_id)
    title = f'Relatório Diário - {programa}'
    form = RelatorioDiarioRefeitorioForm(request.POST or None)
    if form.is_valid():
        data = form.cleaned_data['data']
        tipo_refeicao = form.cleaned_data['tipo_refeicao']
        agendados = form.cleaned_data['agendados']
        url = '/ae/imprimir_lista_diaria/{}/{}?pdf_data={}&pdf_tipo_refeicao={}&agendados={}'.format(
            programa.id, data.weekday(), data.strftime("%d/%m/%Y"), tipo_refeicao, agendados
        )

        if form.cleaned_data.get('categoria'):
            categoria_busca = form.cleaned_data.get('categoria')
            url += f'&categoria_busca={categoria_busca.id}'

        return httprr(url)

    return locals()


@rtr()
@permission_required('ae.pode_ver_relatorios_todos, ae.pode_ver_relatorios_campus')
def relatorio_aluno_rendimento_frequencia(request):
    title = 'Relatório: Alunos Participantes x Índices Acadêmicos'
    form = RelatorioAlunoRendimentoFrequenciaForm(request.GET or None, request=request)
    if form.is_valid():
        campus = form.cleaned_data.get('campus')
        ano = form.cleaned_data.get('ano')
        periodo = form.cleaned_data.get('periodo')
        programa = form.cleaned_data.get('programa')
        data_inicio = datetime.datetime(int(ano), 1, 1).date()
        data_fim = datetime.datetime(int(ano), 12, 31).date()

        periodos_matricula = MatriculaPeriodo.objects.filter(ano_letivo__ano=int(ano))
        if periodo:
            periodos_matricula = periodos_matricula.filter(periodo_letivo=periodo)
            if periodo == '1':
                data_fim = datetime.datetime(int(ano), 6, 30).date()
            else:
                data_inicio = datetime.datetime(int(ano), 7, 1).date()

        hoje = date.today()
        participacoes_abertas = Participacao.objects.filter(Q(data_inicio__lte=hoje), Q(data_termino__isnull=True) | Q(data_termino__gte=hoje))
        if campus:
            periodos_matricula = periodos_matricula.filter(aluno__curso_campus__diretoria__setor__uo=campus)
            participacoes_abertas = participacoes_abertas.filter(programa__instituicao=campus)
        elif not request.user.has_perm('ae.pode_ver_relatorios_todos'):
            campus = get_uo(request.user).id
            periodos_matricula = periodos_matricula.filter(aluno__curso_campus__diretoria__setor__uo=campus)
            participacoes_abertas = participacoes_abertas.filter(programa__instituicao=campus)
        if programa:
            participacoes_abertas = participacoes_abertas.filter(programa=programa)

        matriculas = periodos_matricula.filter(aluno__in=participacoes_abertas.values_list('aluno', flat=True)).order_by('aluno')

        alunos = list()
        frequencia_acima_75 = 0
        frequencia_abaixo_75 = 0
        for matricula in matriculas:
            texto = ''
            for registro in Participacao.abertas.filter(aluno=matricula.aluno):
                texto = texto + '{} (<b>Entrada em: {}</b>), '.format(registro.programa.tipo_programa, registro.data_inicio.strftime('%d/%m/%Y'))
            texto = texto[:-2]

            frequencia = matricula.get_percentual_carga_horaria_frequentada()
            if frequencia > 75:
                frequencia_acima_75 = frequencia_acima_75 + 1
            else:
                frequencia_abaixo_75 = frequencia_abaixo_75 + 1

            alunos.append(
                [
                    matricula.aluno.matricula,
                    matricula.aluno,
                    matricula.aluno.curso_campus,
                    texto,
                    matricula.aluno.get_ira(),
                    frequencia,
                    matricula.aluno.get_ira_curso_aluno(),
                    matricula.aluno.get_total_medidas_disciplinares_premiacoes(data_inicio, data_fim),
                    matricula.aluno.get_total_atividades_complementares(data_inicio, data_fim),
                ]
            )

        series1 = (('Entre 60 e 100', matriculas.filter(aluno__ira__gte=60).count()), ('Abaixo de 60', matriculas.filter(aluno__ira__lt=60).count()))

        grafico1 = PieChart(
            'grafico1',
            title='Quantidade de alunos por Rendimento Acadêmico',
            subtitle='Percentual de alunos com rendimento acadêmico entre 60 e 100',
            minPointLength=0,
            data=series1,
        )
        setattr(grafico1, 'id', 'grafico1')

        series2 = (('Acima de 75%', frequencia_acima_75), ('Abaixo de 75%', frequencia_abaixo_75))

        grafico2 = PieChart('grafico2', title='Quantidade de alunos por Frequência', subtitle='Percentual de alunos com frequência acima de 75%', minPointLength=0, data=series2)
        setattr(grafico2, 'id', 'grafico2')

        graficos_relatorio = [grafico1, grafico2]

    if request.method == 'GET' and 'xls' in request.GET:
        return ae_tasks.relatorio_aluno_rendimento_frequencia_xls(matriculas, data_inicio, data_fim)

    return locals()


@permission_required('ae.pode_ver_relatorios_todos, ae.pode_ver_relatorios_campus')
def verifica_tipo_programa(request):
    from django.core import serializers

    data = []
    if request.method == 'GET':
        id_do_programa = request.GET.get('id_do_programa')
        if id_do_programa:
            try:
                programa = get_object_or_404(Programa, pk=id_do_programa)
                if programa.tipo_programa.sigla == Programa.TIPO_TRABALHO:
                    data = serializers.serialize('json', list(programa), fields=('id',))
            except Exception:
                return httprr('/', 'Programa inválido.', tag='error')
    return HttpResponse(data, content_type='application/json')


@rtr()
@permission_required('ae.pode_detalhar_programa_todos, ae.pode_detalhar_programa_do_campus')
def redireciona_folha_pagamento(request):
    title = 'Gerar Folha de Pagamento'
    form = GerarFolhaPagamentoForm(request.POST or None, request=request)
    if form.is_valid():
        if Programa.objects.filter(instituicao=form.cleaned_data.get('campus'), tipo_programa__sigla=form.cleaned_data.get('tipo_programa')).exists():
            programa = Programa.objects.filter(instituicao=form.cleaned_data.get('campus'), tipo_programa__sigla=form.cleaned_data.get('tipo_programa'))[0]
            return httprr(f'/ae/folha_pagamento/{programa.id}/')
        else:
            return httprr('/ae/redireciona_relatorio_diario/', 'Programa não encontrado.', tag='error')
    return locals()


@rtr()
@permission_required('ae.add_agendamentorefeicao')
def redireciona_avaliar_solicitacao_refeicao(request):
    if (
        not request.user.has_perm('ae.pode_ver_relatorio_semanal')
        and Programa.objects.filter(instituicao=get_uo(request.user), tipo_programa__sigla=Programa.TIPO_ALIMENTACAO).exists()
    ):
        programa = Programa.objects.filter(instituicao=get_uo(request.user), tipo_programa__sigla=Programa.TIPO_ALIMENTACAO)[0]
        return httprr(f'/ae/avaliar_solicitacao_refeicao/{programa.id}/')
    elif request.user.has_perm('ae.pode_ver_relatorio_semanal'):
        title = 'Selecione o Campus'
        form = CampusForm(request.POST or None)
        if form.is_valid():
            if Programa.objects.filter(instituicao=form.cleaned_data.get('campus'), tipo_programa__sigla=Programa.TIPO_ALIMENTACAO).exists():
                programa = Programa.objects.filter(instituicao=form.cleaned_data.get('campus'), tipo_programa__sigla=Programa.TIPO_ALIMENTACAO)[0]
                return httprr(f'/ae/avaliar_solicitacao_refeicao/{programa.id}/')
            else:
                return httprr('/ae/redireciona_avaliar_solicitacao_refeicao/', 'Programa não encontrado.', tag='error')
        return locals()
    else:
        raise PermissionDenied


@rtr()
@permission_required('ae.pode_ver_relatorios_controle_refeicoes')
def lista_atendimentos_refeicoes(request):
    title = 'Lista de Atendimentos de Refeições'
    form = ListaAtendimentoRefeicoesForm(request.GET or None, request=request)
    if form.is_valid():
        inicio = form.cleaned_data.get('data_inicio')
        termino = form.cleaned_data.get('data_termino')
        demandas = DemandaAlunoAtendida.objects.filter(
            demanda__in=[DemandaAluno.ALMOCO, DemandaAluno.CAFE, DemandaAluno.JANTAR],
            data__gte=datetime.datetime(inicio.year, inicio.month, inicio.day, 0, 0, 0),
            data__lte=datetime.datetime(termino.year, termino.month, termino.day, 23, 59, 59),
        )

        if form.cleaned_data.get('campus'):
            demandas = demandas.filter(campus=form.cleaned_data.get('campus'))
        if form.cleaned_data.get('tipo'):
            demandas = demandas.filter(demanda=form.cleaned_data.get('tipo'))

    return locals()


@rtr()
@permission_required('ae.add_edital')
def alterar_situacao_edital(request, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)
    if edital.ativo:
        edital.ativo = False
    else:
        for programa in edital.tipo_programa.all():
            if Edital.objects.filter(tipo_programa=programa, ativo=True).exclude(id=edital.id).exists():
                return httprr('/admin/ae/edital/', f'Já existe um Edital ativo para o Tipo de Programa {programa}.', tag='error')
        edital.ativo = True
    edital.save()
    return httprr('/admin/ae/edital/', 'Edital alterado com sucesso.')


@rtr()
@permission_required('ae.pode_abrir_inscricao_do_campus')
def avaliar_solicitacao_auxilio(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoAuxilioAluno, pk=solicitacao_id)
    title = 'Avaliar Solicitação de Auxílio Eventual'
    form = AvaliarSolicitacaoAuxilioForm(request.POST or None, instance=solicitacao)
    if form.is_valid():
        o = form.save(False)
        o.data_avaliacao = datetime.datetime.now()
        o.avaliador_vinculo = request.user.get_vinculo()
        if not form.cleaned_data.get('deferida'):
            o.deferida = False
        o.save()
        return httprr('/admin/ae/solicitacaoauxilioaluno/', 'Solicitação avaliada com sucesso.')
    return locals()


@rtr()
@permission_required('ae.add_inscricaoalimentacao')
def historico_caracterizacao(request, caracterizacao_id):
    caracterizacao = get_object_or_404(Caracterizacao, pk=caracterizacao_id)
    title = f'Histórico de Alterações na Caracterização - {caracterizacao.aluno}'
    fields = [
        f.get_attname()
        for f in HistoricoCaracterizacao._meta.get_fields()
        if f.name not in ['id', 'caracterizacao', 'caracterizacao_relacionada', 'data_cadastro', 'cadastrado_por']
    ]
    historico = HistoricoCaracterizacao.objects.filter(caracterizacao_relacionada=caracterizacao.pk).order_by('-id')
    custom_fields = dict(
        get_cadastro_display=Column('Cadastrado em', accessor="get_data_cadastro_display"),
        get_cadastrado_por_display=Column('Cadastrado por', accessor="get_cadastrado_por_display"),
    )
    sequence = fields + ['get_cadastro_display']
    table_historico = get_table(queryset=historico, sequence=sequence, custom_fields=custom_fields, fields=fields)
    if request.GET.get("relatorio", None):
        return tasks.table_export(request.GET.get("relatorio", None), *table_historico.get_params())

    return locals()


@rtr()
@csrf_exempt
@permission_required('ae.pode_ver_relatorios_todos, ae.pode_ver_relatorios_campus')
def relatorio_demanda_reprimida(request):
    title = 'Relatório de Demanda Reprimida'
    registros = list()
    form = RelatorioDemandaReprimidaForm(request.POST or None)
    if form.is_valid():
        ano = form.cleaned_data.get('ano').ano
        inscricoes = Inscricao.objects.filter(data_cadastro__year=ano)
        participacoes = Participacao.objects.filter(data_inicio__year=ano)
        if form.cleaned_data.get('campus'):
            inscricoes = inscricoes.filter(programa__instituicao=form.cleaned_data.get('campus'))
            participacoes = participacoes.filter(programa__instituicao=form.cleaned_data.get('campus'))
        if form.cleaned_data.get('programa'):
            inscricoes = inscricoes.filter(programa=form.cleaned_data.get('programa'))
            participacoes = participacoes.filter(programa=form.cleaned_data.get('programa'))

        limite_semestre = datetime.datetime(ano, 7, 1, 0, 0, 0)
        sm = Decimal(Configuracao.get_valor_por_chave('comum', 'salario_minimo'))

        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).filter(renda_bruta_familiar=0)
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Igual a 0 SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )

        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
            where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > 0 AND renda_bruta_familiar/qtd_pessoas_domicilio <= {sm}/4']
        )
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Até ¼ SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )

        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
            where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > {sm}/4 AND renda_bruta_familiar/qtd_pessoas_domicilio <= {sm}/2']
        )
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Entre ¼ SM e ½ SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )
        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
            where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > {sm}/2 AND renda_bruta_familiar/qtd_pessoas_domicilio <= {sm}']
        )
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Entre ½ SM e 1 SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )
        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
            where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > {sm} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 1.5*{sm}']
        )
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Entre 1 SM e 1 ½ SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )

        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
            where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > 1.5*{sm} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 2*{sm}']
        )
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Entre 1 ½ SM e 2 SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )
        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
            where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > 2*{sm} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 2.5*{sm}']
        )
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Entre 2 SM e 2 ½ SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )
        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
            where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > 2.5*{sm} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 3*{sm}']
        )
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Entre 2 ½ SM e 3 SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )
        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
            where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > 3*{sm} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 3.5*{sm}']
        )
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Entre 3 SM e 3 ½ SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )
        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
            where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > 3.5*{sm} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 4*{sm}']
        )
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Entre 3 ½ SM e 4 SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )
        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
            where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > 4*{sm} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 4.5*{sm}']
        )
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Entre 4 SM e 4 ½ SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )
        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
            where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > 4.5*{sm} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 5*{sm}']
        )
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Entre 4 ½ SM e 5 SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )
        caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(where=[f'renda_bruta_familiar/qtd_pessoas_domicilio > ({sm} * 5)'])
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Maior que 5 SM',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )
        caracterizacao = Caracterizacao.objects.filter(qtd_pessoas_domicilio=0)
        inscricoes_faixa = inscricoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        participacoes_faixa = participacoes.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
        inscricoes_1 = inscricoes_faixa.filter(data_cadastro__lt=limite_semestre).count()
        participacoes_1 = participacoes_faixa.filter(data_inicio__lt=limite_semestre).count()
        demanda_1 = inscricoes_1 - participacoes_1
        inscricoes_2 = inscricoes_faixa.filter(data_cadastro__gte=limite_semestre).count()
        participacoes_2 = participacoes_faixa.filter(data_inicio__gte=limite_semestre).count()
        demanda_2 = inscricoes_2 - participacoes_2
        inscricoes_anual = len(set(inscricoes_faixa.values_list('aluno', flat=True)))
        participacoes_anual = len(set(participacoes_faixa.values_list('aluno', flat=True)))
        demanda_anual = inscricoes_anual - participacoes_anual
        registros.append(
            dict(
                faixa='Não Informada',
                inscritos_1=inscricoes_1,
                participantes_1=participacoes_1,
                demanda_1=demanda_1,
                inscritos_2=inscricoes_2,
                participantes_2=participacoes_2,
                demanda_2=demanda_2,
                inscritos_anual=inscricoes_anual,
                participantes_anual=participacoes_anual,
                demanda_anual=demanda_anual,
            )
        )
    return locals()


@rtr(two_factor_authentication=True)
@login_required()
def adicionar_dado_bancario(request, aluno_pk, dado_bancario_pk=None):
    aluno = get_object_or_404(Aluno.objects, pk=aluno_pk)
    dados_bancarios = dado_bancario_pk and DadosBancarios.objects.get(pk=dado_bancario_pk) or None

    is_proprio_aluno = aluno.is_user(request)
    pode_ver_dados_sociais = is_proprio_aluno or in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico')
    if not pode_ver_dados_sociais:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    title = "{} Dados Bancários".format(dado_bancario_pk and "Atualizar" or "Adicionar")
    form = AdicionarDadoBancarioForm(aluno, data=request.POST or None, request=request, instance=dados_bancarios)
    if form.is_valid():
        o = form.save(False)
        o.banco = form.cleaned_data.get('instituicao').nome
        o.atualizado_por = request.user.get_vinculo()
        o.atualizado_em = datetime.datetime.now()
        o.save()
        return httprr('..', 'Dados bancários {} com sucesso.'.format(dado_bancario_pk and "atualizado" or "adicionado"))
    return locals()


@rtr()
@permission_required('ae.view_demandaalunoatendida')
def lista_alunodemandaatendida_alimentos(request):
    hoje = datetime.datetime.today()
    return httprr(f'/admin/ae/demandaalunoatendida/?demanda__eh_kit_alimentacao__exact=1&data__month={hoje.month}&data__year={hoje.year}')
