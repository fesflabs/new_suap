import datetime

from django.core.exceptions import PermissionDenied
from django.db.models.aggregates import Max
from django.http import HttpResponseForbidden
from django.template.defaultfilters import pluralize

from comum.models import Configuracao
from djtools import layout, documentos
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404

from comum.utils import get_uo, get_setor

from djtools.templatetags.filters import in_group
from djtools.utils import group_required, rtr, httprr, permission_required, documento, get_datetime_now
from documento_eletronico.models import ModeloDocumento, DocumentoTexto, Documento, TipoVinculoDocumento, VinculoDocumentoTexto, HipoteseLegal
from documento_eletronico.utils import processar_template_ckeditor, get_variaveis, EstagioProcessamentoVariavel
from edu.models import Aluno
from estagios.forms import (
    EncerrarPraticaProfissionalForm,
    VisitaPraticaProfissionalForm,
    EstagioAditivoContratualForm,
    RelatorioSemestralEstagioForm,
    AvaliarRelatorioSemestralForm,
    OrientacaoEstagioForm,
    EncontrarEstagioForm,
    AditivoContratualAprendizagemForm,
    VisitaAprendizagemForm,
    OrientacaoAprendizagemForm,
    RelatorioModuloAprendizagemForm,
    EncerrarAprendizagemForm,
    EncontrarAprendizagemForm,
    SolicitacaoCancelamentoEncerramentoEstagioForm,
    SolicitacaoCancelamentoEncerramentoAprendizagemForm,
    EncerrarAtividadeProfissionalEfetivaForm,
    OrientacaoAtividadeProfissionalEfetivaForm,
    RelatorioAtividadeProfissionalEfetivaForm,
    SolicitacaoCancelamentoEncerramentoAtividadeProfissionalEfetivaForm,
    CadastrarCancelamentoAtividadeProfissionalEfetivaForm,
    JustificativaVisitaEstagioForm,
    JustificativaVisitaModuloAprendizagemForm,
    EncerrarEstagioAbandonoMatriculaIrregularForm,
    EncerrarAprendizagemAbandonoMatriculaIrregularForm,
)
from estagios.models import (
    PraticaProfissional,
    OfertaPraticaProfissional,
    VisitaPraticaProfissional,
    EstagioAditivoContratual,
    RelatorioSemestralEstagio,
    OrientacaoEstagio,
    Aprendizagem,
    AditivoContratualAprendizagem,
    VisitaAprendizagem,
    OrientacaoAprendizagem,
    RelatorioModuloAprendizagem,
    ModuloAprendizagem,
    SolicitacaoCancelamentoEncerramentoEstagio,
    AtividadeProfissionalEfetiva,
    OrientacaoAtividadeProfissionalEfetiva,
    JustificativaVisitaEstagio,
    JustificativaVisitaModuloAprendizagem,
)
from estagios.utils import get_situacoes_irregulares, por_extenso


@documentos.emissao_documentos()
def emissao_documentos(request, data):
    pass


@layout.servicos_anonimos()
def servicos_anonimos(request):

    servicos_anonimos = list()
    # servicos_anonimos.append(dict(categoria='Avaliações', url="/estagios/avaliar_pratica_profissional_supervisor/", icone="chart-line", titulo='Avaliação de Estágio'))

    return servicos_anonimos


@layout.quadro('Estágios', icone='pencil-alt')
def index_quadros(quadro, request):

    if request.user.groups.filter(name='Coordenador de Estágio Sistêmico').exists():
        qtd_solicitacoes_cancelamento_encerramento_estagio = (
            SolicitacaoCancelamentoEncerramentoEstagio.objects.filter(situacao=SolicitacaoCancelamentoEncerramentoEstagio.AGUARDANDO_RESPOSTA).distinct().count()
        )
        if qtd_solicitacoes_cancelamento_encerramento_estagio:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Solicitaç{}'.format(pluralize(qtd_solicitacoes_cancelamento_encerramento_estagio, 'ão,ões')),
                    subtitulo='Cancelamento de encerramento de estágio',
                    qtd=qtd_solicitacoes_cancelamento_encerramento_estagio,
                    url='/admin/estagios/solicitacaocancelamentoencerramentoestagio/?tab=tab_aguardando_resposta',
                )
            )

    if request.user.groups.filter(name__in=['Coordenador de Estágio Sistêmico', 'Coordenador de Estágio']).exists():
        qs_estagiarios_situacao_matricula_irregular = (
            PraticaProfissional.objects.filter(data_fim__isnull=True, data_prevista_fim__gte=datetime.date.today())
            .filter(aluno__situacao__in=get_situacoes_irregulares())
            .distinct()
            .order_by('-prazo_final_regularizacao_matricula_irregular')
        )
        if not request.user.groups.filter(name='Coordenador de Estágio Sistêmico').exists():
            qs_estagiarios_situacao_matricula_irregular = qs_estagiarios_situacao_matricula_irregular.filter(aluno__curso_campus__diretoria__setor__uo=get_uo(request.user))
        if qs_estagiarios_situacao_matricula_irregular.exists():
            quadro.add_item(
                layout.ItemContador(
                    titulo='Estagiário{}'.format(pluralize(qs_estagiarios_situacao_matricula_irregular.count())),
                    subtitulo='Em situação de matrícula irregular',
                    qtd=qs_estagiarios_situacao_matricula_irregular.count(),
                    url='/admin/estagios/praticaprofissional/?tab=tab_matriculas_irregulares',
                )
            )
        qs_aprendizes_situacao_matricula_irregular = (
            Aprendizagem.objects.filter(data_encerramento__isnull=True)
            .annotate(fim=Max('moduloaprendizagem__fim'))
            .exclude(fim__lt=datetime.date.today())
            .filter(aprendiz__situacao__in=get_situacoes_irregulares())
        )
        if not request.user.groups.filter(name='Coordenador de Estágio Sistêmico').exists():
            qs_aprendizes_situacao_matricula_irregular = qs_aprendizes_situacao_matricula_irregular.filter(aprendiz__curso_campus__diretoria__setor__uo=get_uo(request.user))
        if qs_aprendizes_situacao_matricula_irregular.exists():
            quadro.add_item(
                layout.ItemContador(
                    titulo='Aprendiz{}'.format(pluralize(qs_aprendizes_situacao_matricula_irregular.count(), ',es')),
                    subtitulo='Em situação de matrícula irregular',
                    qtd=qs_aprendizes_situacao_matricula_irregular.count(),
                    url='/admin/estagios/aprendizagem/?tab=tab_matriculas_irregulares',
                )
            )
        qs_atividades_profissionais_efetivas_situacao_matricula_irregular = (
            AtividadeProfissionalEfetiva.objects.filter(situacao=AtividadeProfissionalEfetiva.EM_ANDAMENTO)
            .filter(data_prevista_encerramento__gte=datetime.date.today())
            .filter(aluno__situacao__in=get_situacoes_irregulares())
        )
        if not request.user.groups.filter(name='Coordenador de Estágio Sistêmico').exists():
            qs_atividades_profissionais_efetivas_situacao_matricula_irregular = qs_atividades_profissionais_efetivas_situacao_matricula_irregular.filter(
                aluno__curso_campus__diretoria__setor__uo=get_uo(request.user)
            )
        if qs_atividades_profissionais_efetivas_situacao_matricula_irregular.exists():
            quadro.add_item(
                layout.ItemContador(
                    titulo='Aluno{} de Atividades Profissionais Efetivas'.format(pluralize(qs_atividades_profissionais_efetivas_situacao_matricula_irregular.count())),
                    subtitulo='Com situação de matrícula irregular',
                    qtd=qs_atividades_profissionais_efetivas_situacao_matricula_irregular.count(),
                    url='/admin/estagios/atividadeprofissionalefetiva/?tab=tab_matriculas_irregulares',
                )
            )

    return quadro


@rtr()
@login_required()
def pratica_profissional(request, pk):
    obj = get_object_or_404(PraticaProfissional, pk=pk)
    if not request.user.has_perm('estagios.view_praticaprofissional'):
        if (
            not obj.orientador.vinculo.user == request.user
            and not obj.aluno.pessoa_fisica.user == request.user
            and not obj.aluno.curso_campus.coordenador.user == request.user
            and not in_group(request.user, ['Auditor'])
        ):
            raise PermissionDenied
    title = str(obj)
    is_administrador = in_group(request.user, ['Coordenador de Estágio Sistêmico', 'estagios Administrador'])
    is_coordenador = in_group(request.user, ['Coordenador de Estágio'])
    hoje = datetime.date.today()
    pode_registrar_relatorio_estagiario = obj.pode_registrar_relatorio_estagiario(user=request.user)
    return locals()


@rtr()
@login_required()
def atividade_profissional_efetiva(request, pk):
    obj = get_object_or_404(AtividadeProfissionalEfetiva, pk=pk)
    if not request.user.has_perm('estagios.view_atividadeprofissionalefetiva'):
        if (
            not obj.orientador.vinculo.user == request.user
            and not obj.aluno.pessoa_fisica.user == request.user
            and not obj.aluno.curso_campus.coordenador.user == request.user
            and not in_group(request.user, ['Auditor'])
        ):
            raise PermissionDenied
    title = str(obj)
    is_administrador = in_group(request.user, ['Coordenador de Estágio Sistêmico', 'estagios Administrador'])
    is_coordenador = in_group(request.user, ['Coordenador de Curso', 'Coordenador de Estágio'])
    if request.GET.get('tab', default=None) == 'relatorio':
        pode_submeter_declaracao = is_administrador or is_coordenador or request.user == obj.aluno.pessoa_fisica.user
    return locals()


@rtr()
@group_required('Coordenador de Estágio Sistêmico, estagios Administrador')
def cancelar_encerramento_estagio(request, pk):
    if request.GET.get('scee_pk'):
        scee = get_object_or_404(SolicitacaoCancelamentoEncerramentoEstagio, pk=request.GET.get('scee_pk'))
        if scee.estagio:
            obj = get_object_or_404(PraticaProfissional, pk=pk)
            obj.movito_encerramento = None
            obj.motivacao_desligamento_encerramento = None
            obj.motivo_rescisao = None
            obj.data_fim = None
            obj.ch_final = 0
            obj.termo_encerramento = None
            obj.ficha_frequencia = None
            obj.estagio_anterior_20161 = False
            obj.desvinculado_matricula_irregular = False
            obj.atualizar_situacoes(salvar=True)
            obj.save()
        elif scee.aprendizagem:
            obj = get_object_or_404(Aprendizagem, pk=pk)
            obj.encerramento_por = None
            obj.motivo_encerramento = None
            obj.motivacao_rescisao = None
            obj.data_encerramento = None
            obj.ch_final = None
            obj.comprovante_encerramento = None
            obj.laudo_avaliacao = None
            obj.save()
            obj.notificar()
        elif scee.atividade_profissional_efetiva:
            obj = get_object_or_404(AtividadeProfissionalEfetiva, pk=pk)
            obj.anterior_20171 = None
            obj.encerramento = None
            obj.ch_final = None
            obj.relatorio_final_aluno = None
            obj.observacoes = None
            obj.situacao = obj.EM_ANDAMENTO

            # cancelamento
            obj.cancelamento = None
            obj.motivo_cancelamento = None
            obj.descricao_cancelamento = None
            obj.prazo_final_regularizacao_matricula_irregular = None
            obj.save()
            obj.notificar()
        scee.situacao = SolicitacaoCancelamentoEncerramentoEstagio.DEFERIDA
        scee.save()

    return httprr('/admin/estagios/solicitacaocancelamentoencerramentoestagio/', 'O cancelamento do encerramento do estágio ou afim foi realizado com sucesso.')


@rtr()
@group_required('Coordenador de Estágio Sistêmico, estagios Administrador')
def indeferir_cancelar_encerramento_estagio(request, pk):
    obj = get_object_or_404(SolicitacaoCancelamentoEncerramentoEstagio, pk=pk)
    obj.situacao = SolicitacaoCancelamentoEncerramentoEstagio.INDEFERIDA
    obj.save()
    return httprr('/admin/estagios/solicitacaocancelamentoencerramentoestagio/', 'O indeferimento foi realizado com sucesso.')


@rtr()
@group_required('Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def solicitar_cancelar_encerramento_estagio(request, pk):
    obj = get_object_or_404(PraticaProfissional, pk=pk)
    title = 'Solicitar Desfazimento do Encerramento do {}'.format(obj)
    form = SolicitacaoCancelamentoEncerramentoEstagioForm(
        request=request,
        data=request.POST or None,
        instance=SolicitacaoCancelamentoEncerramentoEstagio(user=request.user, estagio=obj, situacao=SolicitacaoCancelamentoEncerramentoEstagio.AGUARDANDO_RESPOSTA),
    )
    if form.is_valid():
        form.save()
        return httprr(
            '/estagios/pratica_profissional/{}/?tab=informacoes'.format(obj.pk),
            'A solicitação de cancelamento do encerramento do estágio foi realizada com sucesso e está aguardando a resposta da pro-reitoria.',
        )
    return locals()


@rtr()
@group_required('Coordenador de Curso, Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def solicitar_cancelar_encerramento_atividade_profissional_efetiva(request, pk):
    obj = get_object_or_404(AtividadeProfissionalEfetiva, pk=pk)
    title = 'Solicitar Desfazimento do Encerramento da Atividade Profissional Efetiva {}'.format(obj)
    form = SolicitacaoCancelamentoEncerramentoAtividadeProfissionalEfetivaForm(
        request=request,
        data=request.POST or None,
        instance=SolicitacaoCancelamentoEncerramentoEstagio(
            user=request.user, atividade_profissional_efetiva=obj, situacao=SolicitacaoCancelamentoEncerramentoEstagio.AGUARDANDO_RESPOSTA
        ),
    )
    if form.is_valid():
        form.save()
        return httprr(
            '/estagios/atividade_profissional_efetiva/{}/?tab=informacoes'.format(obj.pk),
            'A solicitação de cancelamento do encerramento da atividade profissional efetiva foi realizada com sucesso e está aguardando a resposta da pro-reitoria.',
        )
    return locals()


@rtr()
@group_required('Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def solicitar_cancelar_encerramento_aprendizagem(request, pk):
    obj = get_object_or_404(Aprendizagem, pk=pk)
    title = 'Solicitar Desfazimento do Encerramento da {}'.format(obj)
    form = SolicitacaoCancelamentoEncerramentoAprendizagemForm(
        request=request,
        data=request.POST or None,
        instance=SolicitacaoCancelamentoEncerramentoEstagio(user=request.user, aprendizagem=obj, situacao=SolicitacaoCancelamentoEncerramentoEstagio.AGUARDANDO_RESPOSTA),
    )
    if form.is_valid():
        form.save()
        return httprr(
            '/estagios/aprendizagem/{}/?tab=informacoes'.format(obj.pk),
            'A solicitação de cancelamento do encerramento da aprendizagem foi realizada com sucesso e está aguardando a resposta da pro-reitoria.',
        )
    return locals()


@rtr()
@login_required()
def aprendizagem(request, pk):
    obj = get_object_or_404(Aprendizagem, pk=pk)
    if not request.user.has_perm('estagios.view_aprendizagem'):
        if (
            not obj.orientador.vinculo.user == request.user
            and not obj.aprendiz.pessoa_fisica.user == request.user
            and not obj.aprendiz.curso_campus.coordenador.user == request.user
        ):
            raise PermissionDenied
    title = str(obj)
    hoje = datetime.date.today()
    return locals()


@rtr()
def oferta_pratica_profissional(request, pk):
    obj = get_object_or_404(OfertaPraticaProfissional, pk=pk)
    title = str(obj)
    return locals()


@rtr()
@login_required()
def ofertas_pratica_profissional(request):
    pessoa_fisica = request.user.get_profile()
    if not request.user.eh_aluno:
        return HttpResponseForbidden('Seu vínculo atual não é de aluno e por isso você não pode acessar esta tela')
    aluno = Aluno.objects.filter(pessoa_fisica=pessoa_fisica).first()
    title = 'Ofertas de Prática Profissional para o Curso {}'.format(aluno.curso_campus)
    ofertas = aluno.get_ofertas_pratica_profissional()
    return locals()


@rtr()
@permission_required('estagios.add_praticaprofissional')
def encerrar_pratica_profissional(request, pk):
    obj = get_object_or_404(PraticaProfissional, pk=pk)
    title = 'Encerrar Estágio - {}'.format(obj)
    form = EncerrarPraticaProfissionalForm(request=request, data=request.POST or None, files=request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        form.instance.aluno.atualizar_situacao()
        return httprr('..', 'Estágio encerrado com sucesso.')
    return locals()


@rtr()
@permission_required('estagios.add_praticaprofissional')
def encerrar_estagio_abandono_matricula_irregular(request, pk):
    obj = get_object_or_404(PraticaProfissional, pk=pk)
    title = 'Encerrar Estágio - {}'.format(obj)
    form = EncerrarEstagioAbandonoMatriculaIrregularForm(request=request, data=request.POST or None, files=request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Estágio encerrado com sucesso.')
    return locals()


@rtr()
@permission_required('estagios.add_praticaprofissional')
def notificar_pendencias_estagio(request, pk):
    obj = get_object_or_404(PraticaProfissional, pk=pk)
    obj.notificar()
    return httprr('/estagios/pratica_profissional/{}/?tab=notificacoes'.format(obj.pk), 'Foram enviadas as notificações.')


@rtr()
@permission_required('estagios.add_aprendizagem')
def notificar_pendencias_aprendizagem(request, pk):
    obj = get_object_or_404(Aprendizagem, pk=pk)
    obj.notificar()
    return httprr('..', 'Foram enviadas as notificações.')


@rtr()
@permission_required('estagios.add_aprendizagem')
def encerrar_aprendizagem(request, pk):
    obj = get_object_or_404(Aprendizagem, pk=pk)
    title = 'Encerrar aprendizagem - {}'.format(obj)
    form = EncerrarAprendizagemForm(request=request, data=request.POST or None, files=request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        form.instance.aprendiz.atualizar_situacao()
        return httprr('..', 'Aprendizagem encerrada com sucesso.')
    return locals()


@rtr()
@permission_required('estagios.add_aprendizagem')
def encerrar_aprendizagem_abandono_matricula_irregular(request, pk):
    obj = get_object_or_404(Aprendizagem, pk=pk)
    title = 'Encerrar Aprendizagem - {}'.format(obj)
    form = EncerrarAprendizagemAbandonoMatriculaIrregularForm(request=request, data=request.POST or None, files=request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Aprendizagem encerrada com sucesso.')
    else:
        print(form._errors)
    return locals()


@rtr()
@permission_required('estagios.add_atividadeprofissionalefetiva')
def encerrar_atividade_profissional_efetiva(request, pk):
    obj = get_object_or_404(AtividadeProfissionalEfetiva, pk=pk)
    title = 'Encerrar Atividade Profissional Efetiva - {}'.format(obj)
    form = EncerrarAtividadeProfissionalEfetivaForm(request=request, data=request.POST or None, files=request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        form.instance.aluno.atualizar_situacao()
        return httprr('..', 'Atividade Profissional Efetiva encerrada com sucesso.')
    return locals()


@rtr()
@permission_required('estagios.add_atividadeprofissionalefetiva')
def cadastrar_cancelamento_atividade_profissional_efetiva(request, pk):
    obj = get_object_or_404(AtividadeProfissionalEfetiva, pk=pk)
    title = 'Adicionar Cancelamento - {}'.format(obj)
    form = CadastrarCancelamentoAtividadeProfissionalEfetivaForm(request=request, data=request.POST or None, files=request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Cancelamento da Atividade Profissional Efetiva registrado com sucesso.')
    return locals()


@rtr('submeter_relatorio_monitor.html')
def avaliar_aprendizagem_monitor(request):
    email_monitor = request.GET.get('email_monitor', default=None)
    codigo_verificador = request.GET.get('codigo_verificador', default=None)
    matricula = request.GET.get('matricula', default=None)
    inicio = request.GET.get('inicio', default=None)
    fim = request.GET.get('fim', default=None)
    try:
        inicio = datetime.datetime.strptime(inicio, "%d/%m/%Y")
        fim = datetime.datetime.strptime(fim, "%d/%m/%Y")
    except Exception:
        return httprr('/', 'Data inválida.', tag='error')

    if email_monitor and codigo_verificador and matricula and inicio and fim:
        modulo_aprendizagem = get_object_or_404(
            ModuloAprendizagem,
            aprendizagem__email_monitor=email_monitor,
            aprendizagem__codigo_verificador__startswith=codigo_verificador,
            aprendizagem__aprendiz__matricula=matricula,
            inicio=inicio,
            fim=fim,
        )
        title = 'Submeter Relatório de Módulo de Aprendizagem de {}'.format(modulo_aprendizagem.aprendizagem.aprendiz)
        form = RelatorioModuloAprendizagemForm(
            request=request,
            instance=modulo_aprendizagem.tem_relatorio_monitor()
            and modulo_aprendizagem.relatorio_monitor
            or RelatorioModuloAprendizagem(modulo_aprendizagem=modulo_aprendizagem, eh_relatorio_do_empregado_monitor=True),
            data=request.POST or None,
            files=request.FILES or None,
        )

        if request.method == 'POST' and form.is_valid():
            form.save()
            return httprr('/', 'Avaliação do supervisor registrada com sucesso.')
        return locals()
    else:
        form = EncontrarAprendizagemForm()
        if request.method == 'POST' and form.is_valid():
            return httprr(
                '/estagios/avaliar_aprendizagem_monitor/?matricula={}&codigo_verificador={}&email_supervisor={}'.format(
                    form.cleaned_data.get('matricula'), form.cleaned_data.get('codigo_verificador'), form.cleaned_data.get('email_supervisor')
                ),
                'Avaliação do supervisor registrada com sucesso.',
            )
        else:
            title = 'Avaliar Estágio'
            return locals()


@rtr()
def avaliar_pratica_profissional_supervisor(request):
    email_supervisor = request.GET.get('email_supervisor', default=None)
    codigo_verificador = request.GET.get('codigo_verificador', default=None)
    matricula = request.GET.get('matricula', default=None)

    if email_supervisor and codigo_verificador and matricula:
        pratica_profissional = get_object_or_404(
            PraticaProfissional, email_supervisor=email_supervisor, codigo_verificador__startswith=codigo_verificador, aluno__matricula=matricula
        )
        title = 'Submeter Relatório Semestral do estágio de {}'.format(pratica_profissional.aluno)
        form = RelatorioSemestralEstagioForm(
            request=request,
            instance=RelatorioSemestralEstagio(pratica_profissional=pratica_profissional, eh_relatorio_do_supervisor=True),
            data=request.POST or None,
            files=request.FILES or None,
        )

        if not pratica_profissional.ha_pendencia_relatorio_supervisor():
            return httprr(
                '/',
                'Todas as avaliações demandadas do supervisor já foram enviadas ou o estágio já se encontra encerrado. Em caso de dúvidas procurar a coordenação responsável por estágios no campus do aluno.',
            )

        if request.method == 'POST' and form.is_valid():
            form.save()
            return httprr('/', 'Avaliação do supervisor registrada com sucesso.')
        return locals()
    else:
        servicos_anonimos = layout.gerar_servicos_anonimos(request)
        form = EncontrarEstagioForm()
        if request.method == 'POST' and form.is_valid():
            return httprr(
                '/estagios/avaliar_pratica_profissional_supervisor/?matricula={}&codigo_verificador={}&email_supervisor={}'.format(
                    form.cleaned_data.get('matricula'), form.cleaned_data.get('codigo_verificador'), form.cleaned_data.get('email_supervisor')
                ),
                'Avaliação do supervisor registrada com sucesso.',
            )
        else:
            title = 'Avaliar Estágio'
            category = 'Avaliações'
            icon = 'chart-line'
            return locals()


@rtr()
@group_required('Professor, Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def cadastrar_visitapraticaprofissional(request, pk, visita_pk=None):
    obj = get_object_or_404(PraticaProfissional, pk=pk, data_fim__isnull=True)
    title = 'Adicionar Visita Trimestral ao Estágio de {}'.format(obj.aluno)
    if visita_pk:
        instance = get_object_or_404(VisitaPraticaProfissional, pk=visita_pk)

    if (
        not in_group(request.user, ['Coordenador de Estágio', 'Coordenador de Estágio Sistêmico'])
        and not request.user == obj.orientador.vinculo.user
        and not request.user.is_superuser
    ):
        raise PermissionDenied

    form = VisitaPraticaProfissionalForm(
        request.POST or None,
        instance=visita_pk and instance or VisitaPraticaProfissional(ultimo_editor=request.user, pratica_profissional=obj, orientador=obj.orientador),
        initial=dict(pratica_profissional=obj.pk),
        files=request.FILES or None,
    )
    if form.is_valid():
        form.save()
        return httprr('/estagios/pratica_profissional/{}/?tab=visitas'.format(obj.pk), 'Visita adicionada com sucesso.', close_popup=True)
    close_popup = True
    return locals()


@rtr()
@group_required('Professor, Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def cadastrar_visita_aprendizagem(request, pk, visita_pk=None):
    obj = get_object_or_404(Aprendizagem, pk=pk)
    title = 'Adicionar Visita da Aprendizagem de {}'.format(obj.aprendiz)
    instance = VisitaAprendizagem(ultimo_editor=request.user, aprendizagem=obj, orientador=obj.orientador)
    if visita_pk:
        instance = get_object_or_404(VisitaAprendizagem, pk=visita_pk)

    if (
        not in_group(request.user, ['Coordenador de Estágio', 'Coordenador de Estágio Sistêmico'])
        and not request.user == obj.orientador.vinculo.user
        and not request.user.is_superuser
    ):
        raise PermissionDenied

    form = VisitaAprendizagemForm(request.POST or None, instance=instance, files=request.FILES or None, request=request)

    if form.is_valid():
        form.save()
        return httprr('..', 'Visita adicionada com sucesso.')
    return locals()


@rtr()
@group_required('Professor')
def agendar_orientacao_atividade_profissional_efetiva(request, pk, orientacao_pk=None):
    obj = get_object_or_404(AtividadeProfissionalEfetiva, pk=pk, orientador__vinculo__user=request.user)
    title = 'Registro/Agendamento de Orientação de Atividade Profissional Efetiva'
    instance = None
    if orientacao_pk:
        instance = get_object_or_404(OrientacaoAtividadeProfissionalEfetiva, pk=orientacao_pk, atividade_profissional_efetiva__orientador__vinculo__user=request.user)
    form = OrientacaoAtividadeProfissionalEfetivaForm(request=request, instance=instance, data=request.POST or None, atividade_profissional_efetiva=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Registro/Agendamento de orientação adicionado com sucesso.')
    return locals()


@rtr()
@group_required('Professor')
def agendar_orientacao_estagio(request, pk, orientacao_pk=None):
    obj = get_object_or_404(PraticaProfissional, pk=pk, orientador__vinculo__user=request.user)
    title = 'Agendamento de Orientação de Estágio'
    instance = None
    if orientacao_pk:
        instance = get_object_or_404(OrientacaoEstagio, pk=orientacao_pk, pratica_profissional__orientador__vinculo__user=request.user)
    form = OrientacaoEstagioForm(request=request, instance=instance, data=request.POST or None, pratica_profissional=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Agendamento de orientação adicionado com sucesso.')
    return locals()


@rtr()
@group_required('Professor')
def agendar_orientacao_aprendizagem(request, pk, orientacao_pk=None):
    obj = get_object_or_404(Aprendizagem, pk=pk, orientador__vinculo__user=request.user)
    title = 'Agendamento de Orientação de Aprendizagem'
    instance = None
    if orientacao_pk:
        instance = get_object_or_404(OrientacaoAprendizagem, pk=orientacao_pk, aprendizagem__orientador__vinculo__user=request.user)
    form = OrientacaoAprendizagemForm(request=request, instance=instance, data=request.POST or None, aprendizagem=obj)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Agendamento de orientação adicionado com sucesso.')
    return locals()


@rtr()
@group_required('Professor, Aluno, Coordenador de Estágio, Coordenador de Estágio Sistêmico, Coordenador de Estágio Docente, estagios Administrador')
def visualizar_dados_visita(request, pk):
    obj = get_object_or_404(VisitaPraticaProfissional, pk=pk)
    title = 'Registro de Visita do Orientador ao Estagiário'
    return locals()


@rtr()
@group_required('Professor, Aluno, Coordenador de Estágio, Coordenador de Estágio Sistêmico, Coordenador de Estágio Docente, estagios Administrador')
def visualizar_dados_visita_aprendizagem(request, pk):
    obj = get_object_or_404(VisitaAprendizagem, pk=pk)
    title = 'Registro da Visita do Orientador ao Aprendiz na Concedente.'
    return locals()


@rtr()
@group_required('Professor, Aluno, Coordenador de Estágio, Coordenador de Estágio Sistêmico, Coordenador de Estágio Docente, estagios Administrador')
def visualizar_relatorio_aprendizagem(request, pk):
    obj = get_object_or_404(RelatorioModuloAprendizagem, pk=pk)
    if obj.eh_relatorio_do_empregado_monitor:
        title = 'Registro do Relatório do Empregado Monitor'
    else:
        title = 'Registro do Relatório do Aprendiz'
    return locals()


@rtr()
@permission_required('estagios.add_praticaprofissional')
def adicionar_estagio_aditivo_contratual(request, pk, aditivo_pk=None):
    pratica_profissional = get_object_or_404(PraticaProfissional, pk=pk)
    title = 'Adicionar Aditivo - {}'.format(pratica_profissional)
    instance = None
    if aditivo_pk:
        instance = get_object_or_404(EstagioAditivoContratual, pk=aditivo_pk)
    form = EstagioAditivoContratualForm(request=request, instance=instance, data=request.POST or None, pratica_profissional=pratica_profissional, files=request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('/estagios/pratica_profissional/{}/?tab=documentacao'.format(pratica_profissional.pk), 'Aditivo adicionado com sucesso.')
    return locals()


@rtr()
@group_required('Aluno, Coordenador de Curso, Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def submeter_relatorio_atividade_profissional_efetiva(request, pk):
    atividade_profissional_efetiva = get_object_or_404(AtividadeProfissionalEfetiva, pk=pk)

    if (
        not in_group(request.user, ['Coordenador de Curso', 'Coordenador de Estágio', 'Coordenador de Estágio Sistêmico'])
        and not request.user == atividade_profissional_efetiva.aluno.pessoa_fisica.user
        and not request.user.is_superuser
    ):
        raise PermissionDenied

    title = 'Submeter Declaração de Realização de Atividade Profissional Efetiva'

    form = RelatorioAtividadeProfissionalEfetivaForm(request=request, instance=atividade_profissional_efetiva, data=request.POST or None, files=request.FILES or None)

    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Declaração de realização de atividade profissional efetiva registrada com sucesso.')
    return locals()


@rtr()
@group_required('Aluno, Coordenador de Curso, Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def submeter_relatorio_semestral(request, pk, relatorio_pk=None):
    pratica_profissional = get_object_or_404(PraticaProfissional, pk=pk)
    title = 'Submeter Relatório Semestral do Aluno'
    if relatorio_pk:
        relatorio_semestral_estagio = get_object_or_404(RelatorioSemestralEstagio, pk=relatorio_pk)

    if not pratica_profissional.pode_registrar_relatorio_estagiario(exclude_relatorio_pk=relatorio_pk, user=request.user):
        raise PermissionDenied()

    form = RelatorioSemestralEstagioForm(
        request=request,
        instance=relatorio_pk
        and relatorio_semestral_estagio
        or RelatorioSemestralEstagio(pratica_profissional=pratica_profissional, eh_relatorio_do_supervisor=False, ultimo_editor=request.user),
        data=request.POST or None,
        files=request.FILES or None,
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Avaliação registrada com sucesso.')
    return locals()


@rtr()
@group_required('Coordenador de Estágio, Coordenador de Estágio Sistêmico, Aluno')
def submeter_relatorio_modulo_aprendizagem(request, pk, modulo_pk=None):
    aprendizagem = get_object_or_404(Aprendizagem, pk=pk)
    title = 'Submeter Relatório do Módulo - Aluno'
    if modulo_pk:
        modulo_aprendizagem = get_object_or_404(ModuloAprendizagem, pk=modulo_pk)
        title = 'Submeter Relatório do {} - Aprendiz'.format(modulo_aprendizagem)

    if (
        not in_group(request.user, ['Coordenador de Estágio', 'Coordenador de Estágio Sistêmico'])
        and not request.user == aprendizagem.aprendiz.pessoa_fisica.user
        and not request.user.is_superuser
    ):
        raise PermissionDenied

    form = RelatorioModuloAprendizagemForm(
        request=request,
        instance=modulo_aprendizagem.tem_relatorio_aprendiz()
        and modulo_aprendizagem.relatorio_aprendiz
        or RelatorioModuloAprendizagem(modulo_aprendizagem=modulo_aprendizagem, eh_relatorio_do_empregado_monitor=False, ultimo_editor=request.user),
        data=request.POST or None,
        files=request.FILES or None,
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Avaliação registrada com sucesso.')
    return locals()


@rtr()
@group_required('Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def submeter_relatorio_monitor(request, pk, modulo_pk=None):
    aprendizagem = get_object_or_404(Aprendizagem, pk=pk)

    if modulo_pk:
        modulo_aprendizagem = get_object_or_404(ModuloAprendizagem, pk=modulo_pk)
        title = 'Submeter Relatório do {} - Empregado Monitor'.format(modulo_aprendizagem)

    form = RelatorioModuloAprendizagemForm(
        request=request,
        instance=modulo_aprendizagem.tem_relatorio_monitor()
        and modulo_aprendizagem.relatorio_monitor
        or RelatorioModuloAprendizagem(modulo_aprendizagem=modulo_aprendizagem, eh_relatorio_do_empregado_monitor=True, ultimo_editor=request.user),
        data=request.POST or None,
        files=request.FILES or None,
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Avaliação registrada com sucesso.')
    return locals()


@rtr()
def avaliar_relatorio_semestral(request, pk):
    instance = get_object_or_404(RelatorioSemestralEstagio, pk=pk, orientador__vinculo__user=request.user)
    title = 'Avaliar Relatório Semestral'

    form = AvaliarRelatorioSemestralForm(request=request, instance=instance, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Observações do relatório semestral atualizadas com sucesso.')
    return locals()


@rtr()
@permission_required('estagios.add_praticaprofissional')
def registrar_avaliacao_supervisor_pratica_profissional(request, pk, relatorio_pk=None):
    pratica_profissional = get_object_or_404(PraticaProfissional, pk=pk)
    title = 'Registro da Avaliação do Supervisor - {}'.format(pratica_profissional)
    if relatorio_pk:
        relatorio_semestral_estagio = get_object_or_404(RelatorioSemestralEstagio, pk=relatorio_pk)

    # form = RegistrarAvaliacaoSupervisorPraticaProfissionalForm(request=request, instance=pratica_profissional,
    #                                                            data=request.POST or None, files=request.FILES or None)
    form = RelatorioSemestralEstagioForm(
        request=request,
        instance=relatorio_pk
        and relatorio_semestral_estagio
        or RelatorioSemestralEstagio(pratica_profissional=pratica_profissional, eh_relatorio_do_supervisor=True, ultimo_editor=request.user),
        data=request.POST or None,
        files=request.FILES or None,
    )

    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Avaliação do supervisor registrada com sucesso.')
    return locals()


@rtr()
@permission_required('estagios.add_aprendizagem')
def adicionar_aditivo_contratual_aprendizagem(request, pk, aditivo_pk=None):
    aprendizagem = get_object_or_404(Aprendizagem, pk=pk)
    title = 'Adicionar Aditivo - {}'.format(aprendizagem)
    instance = None
    if aditivo_pk:
        instance = get_object_or_404(AditivoContratualAprendizagem, pk=aditivo_pk)
    form = AditivoContratualAprendizagemForm(request=request, instance=instance, data=request.POST or None, aprendizagem=aprendizagem, files=request.FILES or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Aditivo adicionado com sucesso.')
    return locals()


@rtr()
@group_required('Coordenador de Curso, Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def enviar_notificacoes_atividade_profissional_efetiva(request, pk):
    obj = get_object_or_404(AtividadeProfissionalEfetiva, pk=pk)
    obj.notificar()
    return httprr('/estagios/atividade_profissional_efetiva/{}/?tab=notificacoes'.format(obj.pk), 'Notificações da {} enviadas com sucesso.'.format(obj))


@rtr()
@group_required('Professor, Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def justificar_visita_estagio(request, pk):
    inicio = request.GET.get('inicio', default=None)
    fim = request.GET.get('fim', default=None)
    instance = None
    pratica_profissional = None
    if not inicio and not fim:
        instance = get_object_or_404(JustificativaVisitaEstagio, pk=pk)
    else:
        pratica_profissional = get_object_or_404(PraticaProfissional, pk=pk)
        inicio = datetime.datetime.strptime(inicio, "%d/%m/%Y").date()
        fim = datetime.datetime.strptime(fim, "%d/%m/%Y").date()

        erro = True
        for trimestre in pratica_profissional.get_periodos_trimestrais():
            if trimestre['inicio'] == inicio and trimestre['fim'] == fim:
                erro = False
                break
        if erro:
            raise PermissionDenied

        instance = JustificativaVisitaEstagio(inicio=inicio, fim=fim, pratica_profissional=pratica_profissional)

    form = JustificativaVisitaEstagioForm(request=request, instance=instance, data=request.POST or None, files=request.FILES or None)
    title = 'Justificar Decurso de Prazo'
    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Justificativa adicionada com sucesso.')
    return locals()


@rtr()
@group_required('Professor, Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def ver_justificativa_visita_estagio(request, pk):
    obj = get_object_or_404(JustificativaVisitaEstagio, pk=pk)
    title = 'Justificativa de Decurso de Prazo de Visita'
    return locals()


@rtr()
@group_required('Professor, Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def justificar_visita_aprendizagem(request, pk):
    modulo = get_object_or_404(ModuloAprendizagem, pk=pk)
    if modulo.justificativavisitamoduloaprendizagem_set.exists():
        justificativa = modulo.justificativavisitamoduloaprendizagem_set.all()[0]
    else:
        justificativa = JustificativaVisitaModuloAprendizagem(modulo=modulo)

    form = JustificativaVisitaModuloAprendizagemForm(request=request, instance=justificativa, data=request.POST or None, files=request.FILES or None)
    title = 'Justificar Decurso de Prazo'
    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Justificativa adicionada com sucesso.')
    return locals()


@rtr()
@group_required('Professor, Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def ver_justificativa_visita_aprendizagem(request, pk):
    obj = get_object_or_404(JustificativaVisitaModuloAprendizagem, pk=pk)
    title = 'Justificativa de Decurso de Prazo de Visita'
    return locals()


@documento()
@rtr()
@group_required('Professor, Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def gerar_relatorio_visita_estagio(request, pk):
    obj = get_object_or_404(VisitaPraticaProfissional, pk=pk)
    title = 'Relatório de Visita a Organização Concedente'
    uo = obj.pratica_profissional.aluno.curso_campus.diretoria.setor.uo
    hoje = datetime.date.today()
    return locals()


@documento()
@rtr()
@group_required('Professor, Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def gerar_relatorio_visita_aprendizagem(request, pk):
    obj = get_object_or_404(VisitaAprendizagem, pk=pk)
    title = 'Relatório de Visita à Organização Concedente'
    uo = obj.aprendizagem.aprendiz.curso_campus.diretoria.setor.uo
    hoje = datetime.date.today()
    return locals()


@documento(enumerar_paginas=True)
@rtr()
@group_required('Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def gerar_termo_compromisso(request, pk):
    obj = get_object_or_404(PraticaProfissional, pk=pk)
    title = 'Termo de Compromisso e Plano de Atividades'
    uo = obj.aluno.curso_campus.diretoria.setor.uo
    hoje = datetime.date.today()
    instituicao = Configuracao.get_valor_por_chave("comum", 'instituicao')
    return locals()


@rtr()
@group_required('Coordenador de Estágio, Coordenador de Estágio Sistêmico')
def gerar_termo_compromisso_documentotexto(request, pk):
    obj = get_object_or_404(PraticaProfissional, pk=pk)
    title = 'Termo de Compromisso e Plano de Atividades'

    uo = obj.aluno.curso_campus.diretoria.setor.uo  # uo do aluno

    instituicao = Configuracao.get_valor_por_chave("comum", 'instituicao')

    # Se não possui supervisor, representante da concedente e testumunhas na PraticaProfissional então retorna mensagem
    if not obj.representante_concedente or not obj.supervisor or not obj.testemunha1 or not obj.testemunha2:
        return httprr(
            obj.get_absolute_url(),
            "Para gerar o termo de compromisso no SUAP é necessário incluir os campos: Representante da Concedente, Supervisor, Testemunha 1  e Testemunha 2.",
            'warning',
        )

    # Instanciar modelo de documento texto
    modelo = None
    try:
        modelo = ModeloDocumento.objects.get(nome='Termo de Compromisso de Estágio')
    except Exception:
        raise Exception('Não existe o modelo de documento texto com nome de "Termo de Compromisso".')

    # Criar documento texto - passa objetos para replace de tags no modelo
    user = request.user

    assunto = title

    setor_dono = get_setor(user)

    # Representante
    if obj.servidor_representante:
        representante_cargo = obj.servidor_representante.funcao_atividade.nome if obj.servidor_representante.funcao_atividade else obj.servidor_representante.cargo_emprego.nome
    else:
        representante_cargo = "Cargo não informado"

    # Supervisor
    if obj.supervisor:
        supervisor_nome = obj.supervisor.nome
    else:
        supervisor_nome = obj.nome_supervisor

    # Telefone Orientador
    if obj.orientador.vinculo.pessoa.telefones:
        telefone_orientador = obj.orientador.vinculo.pessoa.telefones
    else:
        telefone_orientador = obj.orientador.vinculo.setor.telefones

    def xstr(s):
        if s is not None:
            return str(s)
        return ''

    # Tags do modelo
    # instituição
    variaveis = dict()
    variaveis['instituicao_nome'] = xstr(instituicao)
    variaveis['instituicao_endereco'] = xstr(uo.endereco)
    variaveis['unidade_municipio'] = xstr(uo.municipio.nome)
    variaveis['unidade_uf'] = xstr(uo.municipio.uf)
    variaveis['unidade_cep'] = xstr(uo.cep)
    variaveis['unidade_cnpj'] = xstr(uo.cnpj)
    variaveis['unidade_telefone'] = xstr(uo.telefone)
    variaveis['representante_nome'] = xstr(obj.servidor_representante.nome) if obj.servidor_representante else "Não Informado"
    variaveis['representante_cargo'] = representante_cargo

    # Orientador
    variaveis['orientador_nome'] = xstr(obj.orientador.vinculo.pessoa.nome)
    variaveis['orientador_cpf'] = obj.orientador.vinculo.pessoa.pessoafisica.cpf
    variaveis['orientador_telefone'] = telefone_orientador
    variaveis['orientador_email'] = xstr(obj.orientador.vinculo.pessoa.email)

    if obj.empresa.eh_pessoa_juridica:
        # Empresa - Concedente Pessoa Juridica
        variaveis['label_pessoa'] = 'ÓRGÃO OU EMPRESA'
        variaveis['label_pessoa_documento'] = 'CNPJ'
        variaveis['label_razao_social'] = 'RAZÃO SOCIAL'
        variaveis['label_nome_fantasia'] = 'NOME FANTASIA:'
        variaveis['empresa_razao_social'] = xstr(obj.empresa.nome)
        variaveis['empresa_nome_fantasia'] = xstr(obj.empresa.pessoajuridica.nome_fantasia) if obj.empresa.eh_pessoa_juridica else obj.empresa.pessoafisica.nome
        variaveis['empresa_cnpj'] = xstr(obj.empresa.pessoajuridica.cnpj) if obj.empresa.eh_pessoa_juridica else " "
        variaveis['empresa_endereco'] = xstr(obj.logradouro)
        variaveis['empresa_endereco_numero'] = xstr(obj.numero)
        variaveis['empresa_endereco_complemento'] = xstr(obj.complemento)
        variaveis['empresa_bairro'] = xstr(obj.bairro)
        variaveis['empresa_telefone'] = xstr(obj.telefone_supervisor)
        variaveis['empresa_cidade'] = xstr(obj.cidade)
        variaveis['empresa_cep'] = xstr(obj.cep)
        variaveis['empresa_representante'] = obj.representante_concedente.nome if obj.representante_concedente else xstr(obj.nome_representante_concedente)
        variaveis['empresa_representante_cargo'] = xstr(obj.cargo_representante_concedente)
        variaveis['empresa_supervisor'] = supervisor_nome
        variaveis['empresa_supervisor_cargo'] = xstr(obj.cargo_supervisor)
        variaveis['empresa_supervisor_email'] = xstr(obj.email_supervisor)
        variaveis['empresa_supervisor_telefone'] = xstr(obj.telefone_supervisor)
        variaveis['empresa_ramo_atividade'] = xstr(obj.ramo_atividade)
    else:
        variaveis['label_pessoa'] = 'PESSOA FÍSICA'
        variaveis['label_razao_social'] = 'NOME'
        variaveis['label_pessoa_documento'] = 'CPF'
        variaveis['label_nome_fantasia'] = ''
        variaveis['empresa_razao_social'] = xstr(obj.empresa.pessoafisica.nome)
        variaveis['empresa_nome_fantasia'] = ''
        variaveis['empresa_cnpj'] = obj.empresa.pessoafisica.cpf
        variaveis['empresa_endereco'] = xstr(obj.logradouro)
        variaveis['empresa_endereco_numero'] = xstr(obj.numero)
        variaveis['empresa_endereco_complemento'] = xstr(obj.complemento)

    # Estagiario - variáveis
    variaveis['estagiario_nome'] = xstr(obj.aluno.pessoa_fisica.nome)
    variaveis['estagiario_cpf'] = xstr(obj.aluno.pessoa_fisica.cpf)
    variaveis['estagiario_rg'] = xstr(obj.aluno.numero_rg)
    variaveis['estagiario_orgaoexpedidor'] = xstr(obj.aluno.orgao_emissao_rg)
    variaveis['estagiario_endereco'] = xstr(obj.aluno.logradouro)
    variaveis['estagiario_numero'] = xstr(obj.aluno.numero)
    variaveis['estagiario_complemento'] = xstr(obj.aluno.complemento)
    variaveis['estagiario_bairro'] = xstr(obj.aluno.bairro)
    variaveis['estagiario_cidade'] = xstr(obj.aluno.cidade)
    variaveis['estagiario_cep'] = xstr(obj.aluno.cep)
    variaveis['estagiario_data_nascimento'] = xstr(obj.aluno.pessoa_fisica.nascimento_data.strftime("%d/%m/%Y"))
    variaveis['estagiario_telefone'] = xstr(obj.aluno.telefone_principal)
    variaveis['estagiario_email'] = xstr(obj.get_email_aluno())
    variaveis['estagiario_curso'] = xstr(obj.aluno.curso_campus.descricao)
    variaveis['estagiario_periodo'] = xstr(obj.aluno.periodo_atual)
    variaveis['estagiario_nivel'] = xstr(obj.aluno.matriz.nivel_ensino)
    variaveis['estagiario_tem_necessidade_especial'] = "Sim" if obj.aluno.tipo_necessidade_especial else "Não"

    # outras variaveis
    variaveis['duracao_meses'] = obj.get_qtd_meses_e_dias().months
    variaveis['duracao_dias'] = obj.get_qtd_meses_e_dias().days
    variaveis['estagio_data_inicio'] = obj.data_inicio.strftime("%d/%m/%Y")
    variaveis['estagio_data_fim'] = obj.data_prevista_fim.strftime("%d/%m/%Y")
    variaveis['estagio_jornada_dia'] = xstr(obj.ch_diaria)
    variaveis['estagio_jornada_semana'] = xstr(obj.ch_semanal)
    variaveis['estagio_horario'] = xstr(obj.horario)
    variaveis['estagio_valor'] = xstr(obj.valor)
    variaveis['estagio_valor_por_extenso'] = por_extenso(obj.valor)
    variaveis['estagio_auxilio_transporte'] = xstr(obj.auxilio_transporte)
    variaveis['estagio_auxilio_transporte_por_extenso'] = por_extenso(obj.auxilio_transporte)
    variaveis['estagio_outros_beneficios'] = xstr(obj.descricao_outros_beneficios)
    variaveis['estagio_numero_seguro'] = xstr(obj.numero_seguro)
    variaveis['estagio_nome_da_seguradora'] = xstr(obj.nome_da_seguradora)
    variaveis['estagio_cnpj_da_seguradora'] = xstr(obj.cnpj_da_seguradora)
    variaveis['estagio_plano_atividades'] = obj.get_atividades
    variaveis['estagio_testemunha1'] = obj.testemunha1.nome if obj.testemunha1 else xstr(obj.testemunha_1)
    variaveis['estagio_testemunha1_cpf'] = obj.testemunha1.cpf if obj.testemunha1 else ""
    variaveis['estagio_testemunha2'] = obj.testemunha2.nome if obj.testemunha2 else xstr(obj.testemunha_2)
    variaveis['estagio_testemunha2_cpf'] = obj.testemunha2.cpf if obj.testemunha2 else ""
    variaveis['estagio_obrigatorio'] = "Sim" if obj.obrigatorio else "Não"

    # Se documento ja existe e é rascunho ou concluido cria novamente
    # Se o documento está assinado ou finalizado já mostra documento e exibe uma mensagem que para gerar um novo deve cancelar o antigo
    # Se o documento está cancelado no momento de criar o novo deve adicionar o vinculo do antigo como retifica e depois adicionar a referencia para o novo

    variaveis_correntes = get_variaveis(
        documento_identificador=None, estagio_processamento_variavel=EstagioProcessamentoVariavel.CRIACAO_DOCUMENTO, usuario=user, setor_dono=setor_dono
    )

    def gerar_termo_compromisso():
        try:
            documento_novo = DocumentoTexto()
            documento_novo.setor_dono = setor_dono
            documento_novo.usuario_criacao = user
            documento_novo.assunto = assunto
            documento_novo.data_ultima_modificacao = get_datetime_now()
            documento_novo.usuario_ultima_modificacao = user
            documento_novo.modelo = modelo
            documento_novo.nivel_acesso = Documento.NIVEL_ACESSO_RESTRITO
            documento_novo.hipotese_legal = HipoteseLegal.objects.get(descricao="Informação Pessoal")
            documento_novo.save()

            variaveis_correntes.update(variaveis)
            documento_novo.corpo = processar_template_ckeditor(texto=modelo.corpo_padrao, variaveis=variaveis_correntes)

            documento_novo.save()

            obj.termo_compromisso_documentotexto = documento_novo
            obj.save()

            return documento_novo
        except Exception as e:
            raise e

    if not obj.termo_compromisso_documentotexto:
        documento_novo = gerar_termo_compromisso()
        url = documento_novo.get_absolute_url()
        msg = 'Termo de compromisso gerado com sucesso!'
    elif obj.termo_compromisso_documentotexto.estah_em_rascunho or obj.termo_compromisso_documentotexto.estah_concluido:
        documento_novo = obj.termo_compromisso_documentotexto
        url = documento_novo.get_absolute_url()
        variaveis_correntes.update(variaveis)
        documento_novo.corpo = processar_template_ckeditor(texto=modelo.corpo_padrao, variaveis=variaveis_correntes)
        if obj.termo_compromisso_documentotexto.estah_concluido:
            documento_novo.editar_documento()
        documento_novo.save()
        msg = 'Termo de compromisso atualizado com sucesso!'
    elif obj.termo_compromisso_documentotexto.estah_assinado or obj.termo_compromisso_documentotexto.estah_finalizado:
        documento_novo = obj.termo_compromisso_documentotexto
        url = documento_novo.get_absolute_url()
        msg = 'Este documento está na situação {} que não permite edição. Para gerar um novo termo favor cancelar este documento: {}'.format(
            documento_novo.get_status(), documento_novo.identificador
        )
    elif obj.termo_compromisso_documentotexto.estah_cancelado:
        documento_antigo = obj.termo_compromisso_documentotexto
        documento_novo = gerar_termo_compromisso()
        url = documento_novo.get_absolute_url()
        # tipo vinculo - retificação
        tipo_vinculo = TipoVinculoDocumento.objects.get(descricao='Retificação')
        # Vincula documentos
        vinculo_documentos = VinculoDocumentoTexto()
        vinculo_documentos.tipo_vinculo_documento = tipo_vinculo
        vinculo_documentos.documento_texto_base = documento_novo
        vinculo_documentos.documento_texto_alvo = documento_antigo
        vinculo_documentos.usuario_criacao = user
        vinculo_documentos.save()
        # Atualiza referencia do obj PraticaProfissional
        obj.termo_compromisso_documentotexto = documento_novo
        obj.save()
        msg = 'Termo de compromisso substituído com sucesso!'
    else:
        url = '/estagios/gerar_termo_compromisso_documentotexto/{}/'.format(obj.pk)
        msg = 'A situação atual do estágio não permite a geração do termo de compromisso'

    return httprr(url, msg)
