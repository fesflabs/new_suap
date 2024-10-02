import base64
import datetime
import hashlib
import io
import json
import math
import os
import tempfile
import urllib.request
import zlib
from collections import OrderedDict
from datetime import timedelta
from xml.dom import minidom
import zipfile
import xlwt
import qrcode
import xmltodict
from PyPDF2 import PdfFileMerger
from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.files.base import ContentFile
from django.db import IntegrityError, transaction
from django.db.models import Subquery
from django.db.models.aggregates import Avg, Max, Min, Sum, Variance
from django.dispatch import receiver
from django.http import HttpResponse, HttpResponseRedirect
from django.http.response import HttpResponseForbidden
from django.shortcuts import get_object_or_404, render
from django.template.defaultfilters import pluralize

from djtools.history import log_view_object
from djtools.utils.response import render_to_string
from django.utils import dateformat
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt

from comum.models import Ano, Configuracao, RegistroEmissaoDocumento, Sala, UsuarioGrupo, Raca
from comum.utils import gerar_documento_impressao, get_sigla_reitoria, get_uo
from djtools import forms
from djtools import layout, documentos
from djtools.etiquetas.labels import factory
from djtools.html.calendarios import CalendarioPlus, Calendario
from djtools.html.graficos import GroupedColumnChart, LineChart, PieChart
from djtools.templatetags.filters import format_, getattrr, in_group, normalizar, format_datetime
from djtools.testutils import running_tests
from djtools.ui import TabelaHorario, TabelasHorario
from djtools.utils import (
    FitSheetWrapper,
    JsonResponse,
    XlsResponse,
    documento,
    get_client_ip,
    get_session_cache,
    group_required,
    httprr,
    normalizar_nome_proprio,
    permission_required,
    rtr,
    send_mail,
    int_to_roman,
)
from djtools.utils.response import PDFResponse
# from documento_eletronico.models import DocumentoTexto
from edu import moodle
from edu import perms, utils, tasks
from edu.forms import (
    AbrirPeriodoLetivoForm,
    AcessoResponsavelForm,
    AddCursoConfiguracaoPedidoMatriculaForm,
    AdicionarAlunosColacaoGrauForm,
    AdicionarAlunosDiarioEspecialForm,
    AdicionarAlunosDiarioForm,
    AdicionarCoordenadorForm,
    AdicionarEncontroDiarioEspecialForm,
    AdicionarMembroDiretoriaForm,
    AdicionarParticipanteEventoForm,
    AdicionarParticipanteTurmaMinicursoForm,
    AdicionarProfessorDiarioEspecialForm,
    AlterarMatrizAlunoForm,
    AlterarNotaForm,
    AlunoCRAForm,
    AlunosConflitosHorariosForm,
    AproveitamentoComponenteForm,
    AproveitamentoEstudoForm,
    AtenderComRessalvaSolicitacaoCertificadoENEMForm,
    AtenderSolicitacaoProrrogacaoEtapaForm,
    AtividadeAprofundamentoForm,
    AtividadeComplementarForm,
    AtualizarCodigoEducacensoForm,
    AtualizarDadosPessoaisForm,
    AtualizarEmailAlunoForm,
    AtualizarEncontroDiarioEspecialForm,
    AtualizarFotoForm,
    AtualizarFotoProfessorForm,
    AtualizarFotosAlunosForm,
    AtualizarListaConvocadosENADEForm,
    AuditoriaCensoForm,
    AulaForm,
    AutenticarCertificadoMinicursoForm,
    AvaliacaoRequerimentoForm,
    BuscaAlunoForm,
    BuscaCalendarioForm,
    BuscaDiarioForm,
    BuscaMatrizForm,
    BuscarAlunoForm,
    CadastrarEstagioDocenteConcomitanteForm,
    CancelarMatriculaForm,
    CancelarRegistroEmissaoCertificadoENEMForm,
    CancelarRegistroEmissaoDiplomaForm,
    CertificarConhecimentoForm,
    ComponenteCurricularForm,
    ConsultarAndamentoSolicitacaoCertificadoENEMForm,
    CoordenadorModalidadeForm,
    CoordenadorPoloForm,
    CoordenadorRegistroAcademicoForm,
    CreditoEspecialForm,
    DefinirCoordenadorCursoForm,
    DefinirCoordenadoresEstagioDocente,
    DefinirLocalAulaDiarioEspecialForm,
    DefinirLocalAulaForm,
    DefinirLocalAulaTurmaForm,
    DisciplinaIngressoProfessorForm,
    DispensaConvocacaoENADEForm,
    DividirDiarioForm,
    EditarAbreviaturaComponenteForm,
    EditarDadosPessoaisSolicitacaoCertificadoENEM,
    EditarDiretoriaCurso,
    EditarLegislacaoForm,
    EditarMatriculaDiarioResumidaForm,
    EditarParticipanteEventoForm,
    EditarParticipanteTurmaMinicursoForm,
    EditarRegistroAlunoINEPForm,
    EfetuarMatriculaForm,
    EfetuarMatriculaTurmaForm,
    EfetuarMatriculasTurmaForm,
    EmitirDiplomaAlunoForm,
    EmitirDiplomaLoteForm,
    EmitirSegundaViaDiploma,
    EncerrarEstagioDocenteForm,
    EncerrarEstagioDocenteNaoConcluidoForm,
    EntregaEtapaForm,
    EnviarAvaliacaoEstagioDocenteForm,
    EnviarPlanilhaMensalSeguroAulaCampoForm,
    EnviarPortfolioEstagioDocenteForm,
    EscolherReitorDiretorGeralForm,
    EstatisticaForm,
    EvasaoEmLoteForm,
    FecharPeriodoLetivoForm,
    GerarTurmasForm,
    HorarioAtendimentoPoloForm,
    IdentificacaoCandidatoForm,
    ImportacaoAlunosForm,
    ImportarAlunosAtivosForm,
    ImportarComponentesForm,
    ImportarComponentesMatrizForm,
    ImportarParticipantesEventoForm,
    ImportarParticipantesTurmaMinicursoForm,
    ImportarXMLTimeTables,
    ImprimirBoletimAlunoForm,
    ImprimirBoletinsEmLoteForm,
    ImprimirDiplomaForm,
    ImprimirHistoricoFinalEmLoteForm,
    ImprimirHistoricoFinalForm,
    ImprimirHistoricoParcialForm,
    ImprimirRegistroDiplomaAlunoForm,
    IndeferirAtividadeComplementarForm,
    IndicadoresForm,
    InserirDiretoriaForm,
    ItemConfiguracaoAtividadeAprofundamentoForm,
    ItemConfiguracaoAtividadeComplementarForm,
    ItemConfiguracaoCreditosEspeciaisForm,
    LancarResultadoProjetoFinalForm,
    QuestaoEducacensoForm,
    RespostaEducacensoFormFactory,
    RespostaQuestaoEducacensoFormFactory,
    UploadDocumentoProjetoFinalForm,
    LancarSituacaoAlunoENADEForm,
    LancarSituacaoAlunoEmLoteENADEForm,
    MapaTurmaForm,
    MatriculaIngressosTurmaForm,
    MatriculaVinculoForm,
    MatricularAlunoAvulsoDiarioForm,
    MatricularAlunoTurmaForm,
    ListarDiarioMatriculaAlunoForm,
    MatricularDiarioForm,
    MatrizCursoForm,
    MedidaDisciplinarForm,
    MensagemForm,
    ModeloCertificadoEventoForm,
    MonitoramentoEntregaDiariosForm,
    MonitoramentoFechamentoPeriodoForm,
    ObservacaoForm,
    ParticipacaoProjetoFinalForm,
    PesquisarAlunosForm,
    PesquisarRegistroAlunoINEPForm,
    PreencherRelatorioAlunosNaoExistentesNoSistecForm,
    PreencherRelatorioCensupForm,
    PreencherRelatorioSistecForm,
    PremiacaoForm,
    ProfessorDiarioForm,
    ProfessorExternoForm,
    ProfessorMinicursoForm,
    ProjetoFinalForm,
    RealizarAuditoriaForm,
    RegistrarMundancaEscolaEstagioDocenteForm,
    RegistroConvocacaoENADEForm,
    ReintegrarAlunoForm,
    RejeitarSolicitacaoCertificadoENEMForm,
    RejeitarSolicitacaoUsuarioForm,
    RelatorioCensupForm,
    RelatorioCoordenacaoCursoForm,
    RelatorioDependenteForm,
    RelatorioDiarioForm,
    RelatorioEducacensoEtapa2Form,
    RelatorioEducacensoForm,
    RelatorioFaltasForm,
    RelatorioForm,
    RelatorioHorarioForm,
    RelatorioIsFForm,
    RelatorioMigracaoForm,
    RelatorioPeriodosAbertosForm,
    RelatorioProfessorForm,
    RelatorioSTTUForm,
    ReplicacaoCalendarioForm,
    ReplicacaoConfiguracaoAvaliacaoForm,
    ReplicacaoConfiguracaoPedidoMatriculaForm,
    ReplicacaoCursoCampusForm,
    ReplicacaoHorarioCampusForm,
    ReplicacaoMatrizForm,
    ReplicarConfiguracaoAACCForm,
    ReplicarConfiguracaoATPAForm,
    RequisitosComponenteCurricularForm,
    SalvarRelatorioForm,
    SelecionarHorarioCampusExportarXMLTimeTables,
    SituacaoMatriculaForm,
    SituacaoMatriculaPeriodoForm,
    SolicitarCertificadoENEMForm,
    SolicitarProrrogacaoEtapaForm,
    SolicitarRelancamentoEtapaForm,
    TrancarMatriculaForm,
    TransferenciaCursoForm,
    TransferenciaExternaForm,
    TransferirDiarioForm,
    TransferirPoloAlunoForm,
    TransferirTurmaForm,
    TurmaMinicursoForm,
    TutorPoloForm,
    VincularConfiguracaoAtividadeAprofundamentoForm,
    VincularConfiguracaoAtividadeComplementarForm,
    VincularMaterialAulaForm,
    VisitaEstagioDocenteForm,
    DeferirColacaoGrauForm,
    MensagemComplementarForm,
    OcorrenciaDiarioForm,
    MateriaisAulaForm,
    ReplicarSolicitacaoCertificadoENEMForm,
    ExportarDadosPNP,
    ImportarEducacensoEtapa2Form,
    AdicionarAlunosDiarioEspecialWizard,
    RequerimentoCancelamentoDisciplinaForm,
    RequerimentoMatriculaDiarioForm,
    IndeferirRequerimentoForm,
    RegistroEmissaoDiplomaPublicForm,
    EntregaTrabalhoForm,
    AutorizacaoForm,
    ReconhecimentoForm,
    RelatorioHorarioDiarioEspecialForm,
    ObservacaoDiarioForm,
    TopicoDiscussaoForm,
    RespostaDiscussaoForm,
    TrabalhoForm,
    AlterarVinculoParticipanteEventoForm,
    AbonoFaltasLoteForm,
    EditarDadosResponsavelForm,
    FiltroAlunosForm,
    PublicaoDOURegistroEmissaoDiplomaForm,
    HorarioAtividadeExtraForm,
    EditarHorarioAtividadeExtraForm,
    EstatisticaTurmaForm,
    AtividadeCurricularExtensaoForm,
    ImportarMaterialAulaForm,
    MonitorMinicursoForm,
    ImprimirHorariosForm,
    ConfigurarAmbienteVirtualDiarioForm,
    IniciarSessaoAssinaturaSenhaForm,
    IniciarSessaoAssinaturaEletronicaForm,
    RevogarDiplomaForm,
    ImportarAutenticacaoSistecForm,
    UploadAlunoArquivoUnicoForm,
    AvaliarArquivoUnicoForm,
    DevolverPlanoEnsino, DefinirPlanoEstudoForm, AvaliarPlanoEstudoForm, InformarDadosTitulacaoForm
)
from edu.forms import AgendarAvaliacaoForm
from edu.models import (
    AbonoFaltas,
    Aluno,
    AlunoAulaCampo,
    AproveitamentoComponente,
    AproveitamentoEstudo,
    AtividadeComplementar,
    AtividadePolo,
    Aula,
    AulaCampo,
    CalendarioAcademico,
    CertificacaoConhecimento,
    Cidade,
    ColacaoGrau,
    Componente,
    ComponenteCurricular,
    ConfiguracaoAtividadeAprofundamento,
    ConfiguracaoAtividadeComplementar,
    ConfiguracaoAvaliacao,
    ConfiguracaoCertificadoENEM,
    ConfiguracaoCreditosEspeciais,
    ConfiguracaoLivro,
    ConfiguracaoPedidoMatricula,
    ConfiguracaoSeguro,
    ConvocacaoENADE,
    CoordenadorModalidade,
    CoordenadorPolo,
    CoordenadorRegistroAcademico,
    CreditoEspecial,
    CursoCampus,
    Diario,
    DiarioEspecial,
    Diretoria,
    Encontro,
    Estado,
    EstagioDocente,
    EstruturaCurso,
    Evento,
    Falta,
    HistoricoRelatorio,
    HorarioAula,
    HorarioAulaDiario,
    HorarioAulaDiarioEspecial,
    HorarioCampus,
    HorarioCoordenadorPolo,
    HorarioFuncionamentoPolo,
    HorarioPolo,
    HorarioTutorPolo,
    ItemConfiguracaoAtividadeAprofundamento,
    ItemConfiguracaoAtividadeComplementar,
    ItemConfiguracaoCreditosEspeciais,
    MaterialAula,
    MaterialDiario,
    MatriculaDiario,
    MatriculaDiarioResumida,
    MatriculaPeriodo,
    Matriz,
    MatrizCurso,
    MedidaDisciplinar,
    Mensagem,
    Minicurso,
    Modalidade,
    ModeloDocumento,
    NivelEnsino,
    NotaAvaliacao,
    Nucleo,
    OrgaoEmissorRg,
    ParticipacaoColacaoGrau,
    ParticipanteEvento,
    PedidoMatricula,
    PedidoMatriculaDiario,
    PeriodoLetivoAtual,
    PeriodoLetivoAtualPolo,
    PeriodoLetivoAtualSecretario,
    Polo,
    Premiacao,
    ProcedimentoMatricula,
    Professor,
    ProfessorDiario,
    ProjetoFinal,
    RegistroAlunoINEP,
    RegistroConvocacaoENADE,
    RegistroDiferenca,
    RegistroEmissaoCertificadoENEM,
    RegistroEmissaoDiploma,
    RegistroLeitura,
    Requerimento,
    SituacaoMatricula,
    SituacaoMatriculaPeriodo,
    SolicitacaoCertificadoENEM,
    SolicitacaoProrrogacaoEtapa,
    SolicitacaoRelancamentoEtapa,
    SolicitacaoUsuario,
    TipoAtividadeComplementar,
    TipoComponente,
    Turma,
    TurmaMinicurso,
    Turno,
    TutorPolo,
    VisitaEstagioDocente,
    OcorrenciaDiario,
    ItemConfiguracaoAvaliacao,
    Log,
    Observacao,
    AtividadeAprofundamento,
    ProfessorMinicurso,
    TopicoDiscussao,
    Trabalho,
    AtividadeCurricularExtensao,
    MonitorMinicurso,
    AssinaturaEletronica,
    SolicitacaoAssinaturaEletronica,
    AssinaturaAtaEletronica,
    AtaEletronica,
    AssinaturaDigital,
    AlunoArquivo,
    CertificadoDiploma,
    PlanoEnsino,
    PlanoEstudo,
    ClassificacaoComplementarComponenteCurricular, RespostaEducacenso)
from edu.models import Autorizacao, Reconhecimento
from edu.models.atividades import HorarioAtividadeExtra
from edu.models.censos import QuestaoEducacenso, RegistroEducacenso
from edu.models.diarios import ObservacaoDiario
from edu.perms import pode_ver_endereco_professores
from edu.q_academico import DAO
from edu.utils import TabelaAlunoPoloNivelEnsino, TabelaMPPoloNivelEnsino, TabelaPoloAnoNivelEnsino, TabelaResumoAluno, TabelaResumoMPCurso, TabelaAlunoCursoCampusPolo
from estagios.models import Aprendizagem, PraticaProfissional, AtividadeProfissionalEfetiva
from etep import perms as etep_perms
from etep.perms import tem_permissao_realizar_procedimentos_etep
from processo_eletronico.models import Processo
# from protocolo.models import Processo as ProcessoProtocolo
from processo_seletivo.models import CandidatoVaga
from rh.models import Funcao, PessoaFisica, Servidor, UnidadeOrganizacional
from rh.views import rh_servidor_view_tab


@documentos.emissao_documentos()
def emissao_documentos(request, data):
    participacoes = None
    professor = None
    alunos = None
    vinculo = request.user.get_vinculo()
    if vinculo:
        participacoes = ParticipanteEvento.objects.filter(participante__id=vinculo.pessoa.id)
        professor = Professor.objects.filter(vinculo__pessoa_id=vinculo.pessoa.id).first()
        alunos = Aluno.objects.filter(pessoa_fisica_id=vinculo.pessoa.id)
    for participacao in participacoes:
        data.append(
            ('Ensino', 'Palestras e Eventos', 'Comprovante de Participação', participacao.evento, f'/edu/imprimir_certificado_participacao_evento/{participacao.pk}/')
        )

    if professor:
        projetos_presididos, projetos_examinados = professor.get_participacoes_em_bancas()
        for projeto in projetos_presididos:
            data.append(
                (
                    'Ensino',
                    'Defesa de TCC / Projeto Final',
                    'Comprovante de Participação',
                    projeto,
                    f'/edu/declaracao_participacao_projeto_final_pdf/{projeto.pk}/presidente/',
                )
            )
        for projeto in projetos_examinados:
            data.append(
                (
                    'Ensino',
                    'Defesa de TCC / Projeto Final',
                    'Comprovante de Participação',
                    projeto,
                    f'/edu/declaracao_participacao_projeto_final_pdf/{projeto.pk}/{projeto.examinador}/',
                )
            )
    for aluno in alunos:
        for descricao, url in aluno.get_urls_documentos():
            data.append(('Ensino', 'Documentos Acadêmicos', aluno.curso_campus.descricao, descricao, url))


@layout.servicos_anonimos()
def servicos_anonimos(request):
    servicos_anonimos = list()
    # servicos_anonimos.append(dict(categoria='Acessos', url="/edu/acesso_responsavel/", icone="passport", titulo='Acesso do Responsável'))
    # servicos_anonimos.append(dict(categoria='Autenticação de Documentos', url="/comum/autenticar_documento/", icone="lock", titulo='Documentos Gerais'))
    # servicos_anonimos.append(dict(categoria='Autenticação de Documentos', url="/comum/validar_assinatura/", icone="lock", titulo='Assinaturas Digitais'))
    # servicos_anonimos.append(dict(categoria='Autenticação de Documentos', url="/edu/autenticar_certificado_minicurso/", icone="lock", titulo='Certificados de Minicursos'))
    # servicos_anonimos.append(dict(categoria='Solicitações', url="/edu/solicitar_certificado_enem/", icone="certificate", titulo='Certificação ENEM'))
    # servicos_anonimos.append(dict(categoria='Consultas', url="/edu/registroemissaodiploma_public/", icone="certificate", titulo='Registro de Diplomas'))

    return servicos_anonimos


@layout.quadro('Faça sua matrícula online', icone='users')
def index_quadros_banners_alunos(quadro, request):
    def do():

        if request.user.eh_aluno:
            aluno = request.user.get_relacionamento()

            # matrícula online
            if aluno.pode_matricula_online():
                quadro.add_item(layout.ItemImagem(titulo='Faça sua matrícula online.', path='/static/edu/img/index-banner-aluno.png', url=aluno.get_url_matricula_online()))
        return quadro

    return get_session_cache(request, 'index_quadros_banners_alunos', do, 24 * 3600)


@layout.info()
def index_infos(request):
    infos = list()

    if request.user.eh_aluno:
        aluno = request.user.get_relacionamento()
        if not aluno.pessoa_fisica.nome_usual:
            infos.append(
                dict(url=f"/edu/atualizar_meus_dados_pessoais/{aluno.matricula}", titulo='Você ainda não possui um nome usual no sistema. Edite o seus dados pessoais.')
            )

        # ofertas de estágio
        if aluno.get_ofertas_pratica_profissional().exists():
            infos.append(dict(url='/estagios/ofertas_pratica_profissional/', titulo='Há oportunidades de prática profissional (Estágio/ Aprendizagem) disponíveis para seu curso.'))

        if aluno.situacao_id in [SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO]:
            for pesquisa in aluno.pesquisas_egresso():
                infos.append(
                    dict(
                        url=f'/egressos/responder_pesquisa_egressos/atualizacao_cadastral/{pesquisa.pk}/',
                        titulo='<strong>Responda Pesquisa de Acompanhamento de Ex-Aluno</strong>',
                    )
                )

    return infos


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()

    if request.user.eh_aluno:
        aluno = request.user.get_relacionamento()

        # matrícula online
        if aluno.pode_matricula_online():
            inscricoes.append(dict(url=aluno.get_url_matricula_online(), titulo='Faça sua matrícula online.', prazo=aluno.get_configuracao_pedido_matricula_ativa().data_fim))

    return inscricoes


@layout.alerta()
def index_alertas(request):
    alertas = list()

    if request.user.eh_aluno:
        aluno = request.user.get_relacionamento()
        if not aluno.logradouro:
            alertas.append(dict(url=f'/edu/atualizar_meus_dados_pessoais/{aluno.matricula}/', titulo='Atualize seus dados pessoais.'))

    else:
        vinculo = request.user.get_vinculo()
        possui_assinaturas_eletronicias_pendentes = SolicitacaoAssinaturaEletronica.objects.filter(
            data_assinatura__isnull=True, vinculo=vinculo
        ).filter(assinatura_eletronica__data_revogacao__isnull=True).exists()
        if possui_assinaturas_eletronicias_pendentes:
            alertas.append(
                dict(
                    url='/admin/edu/assinaturaeletronica/?tab=tab_pendentes_usuario',
                    titulo='Realize a assinatura dos diplomas emitidos eletronicamente.'
                )
            )

        possui_assinaturas_eletronicas_ata_pendentes = AssinaturaAtaEletronica.objects.filter(
            data__isnull=True, pessoa_fisica_id=vinculo.pessoa.pessoafisica.id
        ).exists()
        if possui_assinaturas_eletronicas_ata_pendentes:
            alertas.append(
                dict(
                    url='/admin/edu/ataeletronica/?tab=tab_pendentes',
                    titulo='Realize a assinatura das atas de projeto final emitidas eletronicamente.'
                )
            )

    return alertas


@layout.quadro('Ensino', icone='pencil-alt')
def index_quadros(quadro, request):
    # PARA ALUNOS
    if request.user.eh_aluno:
        aluno = request.user.get_relacionamento()
        qtd_mensagens = (
            Mensagem.objects.filter(destinatarios=request.user.pk)
            .exclude(remetente=request.user)
            .exclude(registroexclusao__destinatario__pk=request.user.pk)
            .exclude(registroleitura__destinatario__pk=request.user.pk)
            .distinct()
        ).count()
        if qtd_mensagens:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Mensage{}'.format(pluralize(qtd_mensagens, 'm,ns')),
                    subtitulo=f'Não lida{pluralize(qtd_mensagens)}',
                    qtd=qtd_mensagens,
                    url='/admin/edu/mensagementrada/?tab=tab_nao_lidas',
                )
            )

        qtd_trabalhos = (
            Trabalho.objects.filter(diario__matriculadiario__matricula_periodo__aluno=aluno)
            .filter(diario__matriculadiario__situacao=MatriculaDiario.SITUACAO_CURSANDO)
            .exclude(entregatrabalho__isnull=False)
            .exclude(data_limite_entrega__lt=datetime.date.today())
            .distinct()
        ).count()
        if qtd_trabalhos:
            quadro.add_item(layout.ItemContador(titulo=f'Trabalho{pluralize(qtd_trabalhos)}', subtitulo=f'Não entregue{pluralize(qtd_trabalhos)}', qtd=qtd_trabalhos, url='/admin/edu/trabalho/'))

        qtd_requerimentos = Requerimento.objects.filter(aluno=aluno, situacao='Em Andamento').count()
        if qtd_requerimentos:
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Requerimento{pluralize(qtd_requerimentos)}', subtitulo='Em andamento', qtd=qtd_requerimentos, url=f'/edu/aluno/{aluno.matricula}/?tab=requerimentos'
                )
            )

        qtd_projetos_finais = ProjetoFinal.objects.filter(data_defesa__gte=datetime.datetime.today(), matricula_periodo__aluno__curso_campus=aluno.curso_campus).count()
        if qtd_projetos_finais:
            quadro.add_item(layout.ItemContador(titulo='Agenda de Defesas de TCC', qtd=qtd_projetos_finais, url='/edu/visualizar_agenda_defesas/'))

        qtd_pedidos_renovacao_pendente = PedidoMatriculaDiario.objects.filter(pedido_matricula__matricula_periodo__aluno=aluno, data_processamento__isnull=True).count()
        if qtd_pedidos_renovacao_pendente:
            quadro.add_item(
                layout.ItemContador(titulo='Renovação de Matrícula', subtitulo='Pendentes', qtd=qtd_pedidos_renovacao_pendente, url=f'{aluno.get_absolute_url()}?tab=pedidos')
            )

        if aluno.curso_campus.modalidade_id == aluno.curso_campus.modalidade.LICENCIATURA:
            qtd_portfolios_pendentes = (
                EstagioDocente.objects.filter(matricula_diario__matricula_periodo__aluno=aluno)
                .exclude(portfolio__isnull=True)
                .exclude(situacao__in=[EstagioDocente.SITUACAO_ENCERRADO, EstagioDocente.SITUACAO_MUDANCA])
            ).count()
            if qtd_portfolios_pendentes:
                quadro.add_item(
                    layout.ItemContador(
                        titulo='Portfólios de Estágio Docente', subtitulo='Pendentes', qtd=qtd_portfolios_pendentes, url=f'{aluno.get_absolute_url()}?tab=estagios'
                    )
                )
        qtd_estagios_com_avaliacao_pendente = aluno.get_estagios_com_avaliacao_pendente().count()
        if qtd_estagios_com_avaliacao_pendente:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Estágios',
                    subtitulo='Com Avaliação Pendente',
                    qtd=qtd_estagios_com_avaliacao_pendente,
                    url=f'{aluno.get_absolute_url()}?tab=estagios',
                )
            )

        if aluno.get_estagio_com_rel_atividades_pendente().exists():
            quadro.add_item(
                layout.ItemContador(
                    titulo='Estágios',
                    subtitulo='Rel. Atividades Pendentes',
                    qtd=aluno.get_estagio_com_rel_atividades_pendente()[0].get_qtd_pendente_relatorios_estagiario,
                    url=f'/estagios/pratica_profissional/{aluno.get_estagio_com_rel_atividades_pendente()[0].pk}/?tab=relatorios',
                )
            )

        if aluno.get_aprendizagem_com_rel_atividades_pendente() and aluno.get_aprendizagem_com_rel_atividades_pendente().qtd_relatorios_aprendiz_pendentes > 0:
            quadro.add_item(
                layout.ItemContador(
                    titulo='Aprendizagem',
                    subtitulo='Rel. Atividades Pendentes',
                    qtd=aluno.get_aprendizagem_com_rel_atividades_pendente().qtd_relatorios_aprendiz_pendentes,
                    url=f'{aluno.get_absolute_url()}?tab=estagios',
                )
            )
        atividade_relatorio_pendente = aluno.get_atividade_profissional_efetiva_pendente_relatorio().first()
        orientacoes = aluno.get_atividade_profissional_efetiva_reunioes_de_orientacao()
        if atividade_relatorio_pendente or orientacoes.exists():
            subtitulo = ''
            if atividade_relatorio_pendente:
                subtitulo = 'Relatório Final do Aluno Ainda Não Enviado'
                tab = 'relatorios'
                pk = atividade_relatorio_pendente.pk
            if orientacoes.exists():
                if subtitulo:
                    subtitulo = subtitulo + f' / {orientacoes.count()} Orientação(ões) marcada(s)'
                else:
                    subtitulo = f'{orientacoes.count()} orientação(ões) marcada(s)'
                tab = 'reunioes'
                pk = orientacoes[0].atividade_profissional_efetiva.pk

            quadro.add_item(
                layout.ItemContador(titulo='Atividade Profissional Efetiva', subtitulo=subtitulo, qtd=1, url=f'/estagios/atividade_profissional_efetiva/{pk}/?tab={tab}')
            )

        quadro.add_itens(
            [
                layout.ItemAcessoRapido(titulo='Meus Dados', icone='user', url=aluno.get_absolute_url()),
                layout.ItemAcessoRapido(titulo='Agenda de Avaliações', icone='calendar-alt', url='/edu/calendario_avaliacao/'),
                layout.ItemAcessoRapido(titulo='Locais e Horários de Aula', icone='search', url=f'{aluno.get_absolute_url()}?tab=locais_aula_aluno'),
                layout.ItemAcessoRapido(titulo='Meus Requerimentos', icone='search', url=f'{aluno.get_absolute_url()}?tab=requerimentos'),
                layout.ItemAcessoRapido(titulo='Minhas Disciplinas', icone='search', url='/edu/disciplinas/'),
            ]
        )

        if aluno.polo:
            quadro.add_item(layout.ItemAcessoRapido(titulo=f'Polo {aluno.polo.descricao}', url='/edu/meu_polo/'))

    else:

        # Certificado ENEM
        if request.user.groups.filter(name='Certificador ENEM').exists():
            configuracoes_certificado_enem = request.user.get_profile().funcionario.configuracaocertificadoenem_set.all()
            qtd_solicitacoes_pendentes = 0
            for configuracao_certificado_enem in configuracoes_certificado_enem:
                qtd_solicitacoes_pendentes += configuracao_certificado_enem.solicitacaocertificadoenem_set.filter(data_avaliacao__isnull=True).count()
            if qtd_solicitacoes_pendentes > 0:
                quadro.add_item(
                    layout.ItemContador(
                        titulo='Solicitaç{} de Certificados ENEM'.format(pluralize(qtd_solicitacoes_pendentes, 'ão,ões')),
                        subtitulo='Aguardando avaliação',
                        qtd=qtd_solicitacoes_pendentes,
                        url='/admin/edu/solicitacaocertificadoenem/?tab=tab_pendentes',
                    )
                )

    return quadro


@layout.quadro('Professores', icone='graduation-cap')
def index_quadros_professores(quadro, request):
    pessoa_fisica_logada = request.user.get_profile()
    if not pessoa_fisica_logada:
        return quadro
    professor = pessoa_fisica_logada.professor_set.first()
    if professor:
        professores_diario = professor.professordiario_set.filter(ativo=True).order_by('diario')
        if professores_diario.exists():
            hoje = datetime.datetime.now()
            inicio = hoje - timedelta(days=7)
            diarios = Diario.objects.filter(id__in=professores_diario.values_list('diario', flat=True), calendario_academico__data_inicio_etapa_1__lt=inicio)
            diarios = diarios.exclude(
                posse_etapa_1=Diario.POSSE_REGISTRO_ESCOLAR,
                posse_etapa_2=Diario.POSSE_REGISTRO_ESCOLAR,
                posse_etapa_3=Diario.POSSE_REGISTRO_ESCOLAR,
                posse_etapa_4=Diario.POSSE_REGISTRO_ESCOLAR,
            )
            pk_diarios = []
            pk_diarios_pendentes = []
            for diario in diarios:
                if diario.matriculadiario_set.exists():
                    aulas = diario.get_aulas().filter(data__range=(inicio, hoje))
                    if not aulas.exists():
                        pk_diarios.append(str(diario.pk))

                fimetapa = hoje - timedelta(days=7)
                if (
                    diario.matriculadiario_set.filter(diario__professordiario__data_fim_etapa_1__lt=fimetapa, diario__posse_etapa_1=Diario.POSSE_PROFESSOR).exists()
                    or diario.matriculadiario_set.filter(diario__professordiario__data_fim_etapa_2__lt=fimetapa, diario__posse_etapa_2=Diario.POSSE_PROFESSOR).exists()
                    or diario.matriculadiario_set.filter(diario__professordiario__data_fim_etapa_3__lt=fimetapa, diario__posse_etapa_3=Diario.POSSE_PROFESSOR).exists()
                    or diario.matriculadiario_set.filter(diario__professordiario__data_fim_etapa_4__lt=fimetapa, diario__posse_etapa_4=Diario.POSSE_PROFESSOR).exists()
                    or diario.matriculadiario_set.filter(diario__professordiario__data_fim_etapa_final__lt=fimetapa, diario__posse_etapa_5=Diario.POSSE_PROFESSOR).exists()
                ):
                    pk_diarios_pendentes.append(str(diario.pk))

            if pk_diarios:
                quadro.add_item(
                    layout.ItemContador(
                        titulo=len(pk_diarios) == 1 and 'Diário' or 'Diários',
                        subtitulo='Sem registro há 8 dias',
                        qtd=len(pk_diarios),
                        url=('/edu/meus_diarios/{}'.format('_'.join(pk_diarios))),
                    )
                )
            if pk_diarios_pendentes:
                quadro.add_item(
                    layout.ItemContador(
                        titulo=len(pk_diarios_pendentes) == 1 and 'Diário' or 'Diários',
                        subtitulo='Não Entregues',
                        qtd=len(pk_diarios_pendentes),
                        url=('/edu/meus_diarios/{}'.format('_'.join(pk_diarios_pendentes))),
                    )
                )

        qtd_orientacoes_estagio = professor.get_qtd_orientacoes_estagio()
        qtd_estagios_nao_visitados = professor.get_qtd_estagios_nao_visitados()

        quadro.add_itens(
            [
                layout.ItemAcessoRapido(titulo='Meus Diários', url='/edu/meus_diarios/'),
                layout.ItemAcessoRapido(titulo='Materiais de Aula', icone='book', url='/admin/edu/materialaula/'),
                layout.ItemAcessoRapido(titulo='Agenda de Avaliações', icone='calendar-alt', url='/edu/calendario_avaliacao/'),
                layout.ItemAcessoRapido(titulo='Participações em Bancas de Projeto Final', url=f'/edu/professor/{professor.pk:d}/?tab=banca'),
                layout.ItemAcessoRapido(titulo='Orientação de Projeto Final', url=f'/edu/professor/{professor.pk:d}/?tab=projetofinal'),
                layout.ItemAcessoRapido(titulo='Meus Dados', url=f'/edu/professor/{professor.pk:d}/'),
                layout.ItemAcessoRapido(titulo='Locais e Horários de Aula', url='/edu/locais_aula_professor/'),
            ]
        )
        if qtd_orientacoes_estagio:
            quadro.add_itens(
                [
                    layout.ItemContador(
                        titulo='Orientações de Estágios e Afins',
                        subtitulo=f'{qtd_estagios_nao_visitados} com visitas pendentes',
                        qtd=qtd_orientacoes_estagio,
                        url=f'/edu/professor/{professor.pk}/?tab=estagios',
                    )
                ]
            )

        if request.user.eh_docente:
            quadro.add_item(layout.ItemAcessoRapido(titulo='Plano Individual de Trabalho', url=f'/edu/professor/{professor.pk:d}/?tab=planoatividades'))

        if CursoCampus.objects.filter(plano_ensino=True).exists():
            qs = PlanoEnsino.objects.filter(
                diario__professordiario__professor__vinculo=request.user.get_vinculo(), data_submissao__isnull=True
            )
            if qs.exists():
                quadro.add_itens(
                    [
                        layout.ItemContador(
                            titulo='Planos de Ensino',
                            subtitulo='Aguardando Submissão',
                            qtd=qs.count(),
                            url='/admin/edu/planoensino/?tab=tab_aguardando_minha_subissao',
                        )
                    ]
                )
            quadro.add_item(layout.ItemAcessoRapido(titulo='Planos de Ensino', url='/admin/edu/planoensino/'))

    return quadro


@layout.quadro('Coordenação de Curso', icone='graduation-cap')
def index_quadros_coordenadores_curso(quadro, request):
    if in_group(request.user, 'Coordenador de Curso', False):
        ano = int(Configuracao.get_valor_por_chave('edu', 'ano_letivo_atual') or datetime.date.today().year)
        ano_letivo_corrente = Ano.objects.get(ano=ano)
        periodo_letivo_corrente = int(Configuracao.get_valor_por_chave('edu', 'periodo_letivo_atual') or 1)
        qs_cursos = CursoCampus.objects.filter(coordenador=request.user.get_vinculo().pessoa_id) | CursoCampus.objects.filter(coordenador_2=request.user.get_vinculo().pessoa_id)
        for curso in qs_cursos.distinct():
            # - Alunos com AACC pendentes de aprovação;
            qtd_aacc_pendente = AtividadeComplementar.locals.filter(deferida__isnull=True, aluno__curso_campus_id=curso.pk).count()
            if qtd_aacc_pendente:
                quadro.add_itens(
                    [layout.ItemContador(titulo='AACC', subtitulo=f'pendentes de aprovação do curso {curso.descricao_historico}', qtd=qtd_aacc_pendente, url=f'/admin/edu/atividadecomplementar/?deferida__isnull=True&aluno__curso_campus={curso.pk}')]
                )
            qtd_atp_pendente = AtividadeAprofundamento.locals.filter(deferida__isnull=True, aluno__curso_campus_id=curso.pk).count()
            if qtd_atp_pendente:
                quadro.add_itens(
                    [layout.ItemContador(titulo='ATP', subtitulo='pendentes de aprovação do curso {curso.descricao_historico}', qtd=qtd_atp_pendente, url=f'/admin/edu/atividadeaprofundamento/?deferida__isnull=True&aluno__curso_campus={curso.pk}')]
                )

            qtd_diarios = Diario.locals.get_queryset().filter(turma__curso_campus_id=curso.pk).exclude(professordiario__professor__vinculo__user_id=request.user.pk).nao_entregues().count()
            if qtd_diarios:
                quadro.add_itens(
                    [layout.ItemContador(titulo=f'Diário{pluralize(qtd_diarios)}', subtitulo=f'não entregues do curso {curso.descricao_historico}', qtd=qtd_diarios, url=f'/admin/edu/diario/?turma__curso_campus={curso.pk}&tab=tab_nao_entregues')]
                )
            qs_turma = Turma.locals.get_queryset().filter(curso_campus_id=curso.pk)
            # - Turmas com fechamento pendente;
            qtd_turmas_pendentes = qs_turma.pendentes().count()
            if qtd_turmas_pendentes:
                quadro.add_itens(
                    [
                        layout.ItemContador(
                            titulo=f'Turma{pluralize(qtd_turmas_pendentes)}', subtitulo=f'pendente{pluralize(qtd_turmas_pendentes)} do curso {curso.descricao_historico}', qtd=qtd_turmas_pendentes, url=f'/admin/edu/turma/?curso_campus={curso.id}&tab=tab_pendentes'
                        )
                    ]
                )

            # - Turmas existentes no semestre;
            qtd_anual = qs_turma.filter(ano_letivo=ano_letivo_corrente, curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL).count()
            qtd_outros = qs_turma.filter(ano_letivo=ano_letivo_corrente, periodo_letivo=periodo_letivo_corrente).exclude(curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL).count()
            qtd_turmas = qtd_anual + qtd_outros
            if qtd_turmas:
                if qtd_anual > 0:
                    url = f'/admin/edu/turma/?curso_campus={curso.id}&ano_letivo__id__exact={ano_letivo_corrente.pk}'
                else:
                    url = f'/admin/edu/turma/?curso_campus={curso.id}&ano_letivo__id__exact={ano_letivo_corrente.pk}&periodo_letivo__exact={periodo_letivo_corrente}'
                quadro.add_itens(
                    [
                        layout.ItemContador(
                            titulo=f'Turma{pluralize(qtd_turmas)}', subtitulo=f'em {ano_letivo_corrente}.{periodo_letivo_corrente} do curso {curso.descricao_historico}', qtd=qtd_turmas, url=url
                        )
                    ]
                )
            # - Alunos sem turma;
            qtd_alunos_sem_turma = Aluno.get_alunos_sem_turma(request.user, ano_letivo_corrente.ano, periodo_letivo_corrente, curso.id).count()
            if qtd_alunos_sem_turma:
                quadro.add_itens(
                    [
                        layout.ItemContador(
                            titulo=f'Aluno{pluralize(qtd_alunos_sem_turma)}',
                            subtitulo=f'sem turma em {ano_letivo_corrente.ano}.{periodo_letivo_corrente} do curso {curso.descricao_historico}',
                            qtd=qtd_alunos_sem_turma,
                            url=f'/edu/alunos_sem_turma_curso/{ano_letivo_corrente.ano}/{periodo_letivo_corrente}/{curso.id}/',
                        )
                    ]
                )
            # - Atividades curriculares de extensão não avaliadas
            qtd_atividades = AtividadeCurricularExtensao.objects.filter(matricula_periodo__aluno__curso_campus_id=curso.id, concluida=True, aprovada__isnull=True).count()
            if qtd_atividades:
                quadro.add_itens(
                    [
                        layout.ItemContador(
                            titulo='Atividade Curricular de Extensão',
                            subtitulo=f'não avaliada do curso {curso.descricao_historico}',
                            qtd=qtd_atividades,
                            url='/admin/edu/atividadecurricularextensao/?matricula_periodo__aluno__curso_campus={curso.id}&tab=tab_aguardando_avaliacao',
                        )
                    ]
                )
            qtd_requerimentos = Requerimento.objects.filter(aluno__curso_campus_id=curso.id, situacao='Em Andamento').count()
            if qtd_requerimentos:
                quadro.add_item(
                    layout.ItemContador(
                        titulo=f'Requerimento{pluralize(qtd_requerimentos)}', subtitulo='Em andamento do curso {curso.descricao_historico}',
                        qtd=qtd_requerimentos, url='/admin/edu/requerimento/?aluno__curso_campus={curso.id}&tab=tab_em_andamento'
                    )
                )

        if CursoCampus.objects.filter(plano_ensino=True, coordenador=request.user.get_profile()).exists():
            qs = PlanoEnsino.objects.filter(
                coordenador_curso=request.user.get_profile(), data_submissao__isnull=False, data_aprovacao__isnull=True
            )
            if qs.exists():
                quadro.add_itens(
                    [
                        layout.ItemContador(
                            titulo='Planos de Ensino',
                            subtitulo='Aguardando Aprovação',
                            qtd=qs.count(),
                            url='/admin/edu/planoensino/?tab=tab_aguardando_minha_aprovacao',
                        )
                    ]
                )
            quadro.add_item(layout.ItemAcessoRapido(titulo='Planos de Ensino', url='/admin/edu/planoensino/'))
        return quadro


@layout.quadro('Direção Acadêmica', icone='graduation-cap')
def index_quadros_diretores_academicos(quadro, request):
    if in_group(request.user, 'Diretor Acadêmico'):
        if CursoCampus.objects.filter(plano_ensino=True).exists():
            qs = PlanoEnsino.objects.filter(
                data_aprovacao__isnull=False, data_homologacao__isnull=True,
                diario__turma__curso_campus__diretoria__setor__uo=request.user.get_vinculo().setor.uo,
            )
            if qs.exists():
                quadro.add_itens(
                    [
                        layout.ItemContador(
                            titulo='Planos de Ensino',
                            subtitulo='Aguardando Homologação',
                            qtd=qs.count(),
                            url='/admin/edu/planoensino/?tab=tab_aguardando_homologacao',
                        )
                    ]
                )
            quadro.add_item(layout.ItemAcessoRapido(titulo='Planos de Ensino', url='/admin/edu/planoensino/'))
    return quadro


@layout.quadro('Serviços Microsoft', icone='windows fab', pode_esconder=True)
def index_quadros_microsoft(quadro, request):
    def do():

        if request.user.eh_aluno:
            aluno = request.user.get_relacionamento()
            if aluno.email_academico:
                quadro.add_itens(
                    [
                        layout.ItemAcessoRapido(titulo='E-mail Institucional', icone='envelope', url='/microsoft/redirecionar_aluno/office365/'),
                        layout.ItemAcessoRapido(
                            titulo='Microsoft Azure',
                            icone='windows fab',
                            url='https://portal.azure.com/?Microsoft_Azure_Education_correlationId=43de9837-5309-4b65-9503-02d577da29c4#blade/Microsoft_Azure_Education/EducationMenuBlade/software',
                        ),
                    ]
                )
            quadro.add_item(layout.ItemAcessoRapido(titulo='Portal Office 365', icone='windows fab', url='https://portal.office.com'))

        return quadro

    return get_session_cache(request, 'index_quadros_microsoft', do, 24 * 3600)


@layout.quadro('Calendário Acadêmico', icone='calendar-alt', pode_esconder=True)
def index_quadros_calendario_academico(quadro, request):
    def do():
        if request.user.eh_aluno:
            aluno = request.user.get_relacionamento()
            ultima_matricula_periodo = aluno.get_ultima_matricula_periodo()
            if ultima_matricula_periodo:
                calendario_academico = ultima_matricula_periodo.get_calendario_academico()
                if calendario_academico:
                    quadro.add_itens(
                        [
                            layout.ItemCalendario(calendario=calendario_academico.mensal()),
                            layout.ItemAcessoRapido(titulo='Calendário Completo', url=f'/edu/calendarioacademico/{calendario_academico.pk:d}/'),
                        ]
                    )

        return quadro

    return get_session_cache(request, 'index_quadros_calendario_academico_alunos', do, 24 * 3600)


@layout.quadro('Autorizações e Reconhecimentos', icone='graduation-cap', pode_esconder=True)
def index_quadros_autorizacao_reconhecimento(quadro, request):
    def do():
        if request.user.has_perm('edu.view_autorizacao'):
            qtd_sem_autorizacao = MatrizCurso.locals.filter(autorizacao__isnull=True).count()
            if qtd_sem_autorizacao > 0:
                quadro.add_itens(
                    [layout.ItemContador(
                        titulo='Curso{}'.format(pluralize(qtd_sem_autorizacao, 's')),
                        subtitulo='Sem autorização',
                        qtd=qtd_sem_autorizacao, url='/admin/edu/matrizcurso/?tab=tab_sem_autorizacao')]
                )

        if request.user.has_perm('edu.view_reconhecimento'):
            qs_reconhecimento = MatrizCurso.locals.filter(curso_campus__modalidade__nivel_ensino_id=NivelEnsino.GRADUACAO)
            qtd_sem_reconhecimento = qs_reconhecimento.filter(reconhecimento__isnull=True).count()
            if qtd_sem_reconhecimento > 0:
                quadro.add_itens(
                    [layout.ItemContador(
                        titulo='Curso{}'.format(pluralize(qtd_sem_reconhecimento, 's')),
                        subtitulo='Sem reconhecimento',
                        qtd=qtd_sem_reconhecimento, url='/admin/edu/matrizcurso/?curso_campus__modalidade__nivel_ensino__id__exact=3&tab=tab_sem_reconhecimento')]
                )
        return quadro

    return get_session_cache(request, 'index_quadros_autorizacao_reconhecimento', do, 24 * 3600)


@layout.quadro('Calendários Acadêmicos', icone='calendar-alt', pode_esconder=True)
def index_quadros_calendarios_academicos(quadro, request):
    def do():
        professor = Professor.objects.filter(vinculo__user=request.user).first()
        if professor:
            periodo_letivo_atual = PeriodoLetivoAtual.get_instance(request, professor)
            professores_diario = ProfessorDiario.objects.filter(professor__vinculo__user=request.user, ativo=True).order_by('diario')
            professores_diario_anual = professores_diario.filter(
                diario__turma__curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL, diario__ano_letivo__ano=periodo_letivo_atual.ano
            )

            # excluindo os diários semestrais em cursos anuais
            if periodo_letivo_atual.periodo == 1:
                professores_diario_anual = professores_diario_anual.exclude(diario__segundo_semestre=True)
            else:
                professores_diario_anual = professores_diario_anual.exclude(diario__segundo_semestre=False, diario__componente_curricular__qtd_avaliacoes=2)

            professores_diario_semestral = professores_diario.filter(
                diario__turma__curso_campus__periodicidade__in=[CursoCampus.PERIODICIDADE_SEMESTRAL, CursoCampus.PERIODICIDADE_LIVRE],
                diario__ano_letivo__ano=periodo_letivo_atual.ano,
                diario__periodo_letivo=periodo_letivo_atual.periodo,
            )
            professores_diario = (professores_diario_anual | professores_diario_semestral).order_by('diario__turma__curso_campus')
            pks_calendarios = professores_diario.order_by('diario__calendario_academico').values_list('diario__calendario_academico', flat=True).distinct()
            qs_calendarios_academicos = CalendarioAcademico.objects.filter(pk__in=pks_calendarios)

            diarios_especiais = professor.diarioespecial_set.filter(ano_letivo__ano=periodo_letivo_atual.ano, periodo_letivo=periodo_letivo_atual.periodo)
            qtd_diarios = professores_diario.count() + diarios_especiais.count()
            if qtd_diarios and qs_calendarios_academicos:
                legenda = '''
                <div class="legenda">
                    <p>Legenda:</p>
                    <ul>
                        <li class="hoje">Hoje</li>
                        <li class="success">1ª Etapa</li>
                        <li class="info">2ª Etapa</li>
                        <li class="alert">3ª Etapa</li>
                        <li class="error">4ª Etapa</li>
                        <li class="conflito">Fechamento do Período</li>
                    </ul>
                </div>
                '''
                for calendario_academico in qs_calendarios_academicos:
                    quadro.add_itens(
                        [
                            layout.ItemCalendario(calendario=calendario_academico.mensal(), legenda=legenda),
                            layout.ItemAcessoRapido(
                                titulo=f'Calendário #{calendario_academico.pk:d}', url=f'/edu/calendarioacademico/{calendario_academico.pk:d}/'
                            ),
                        ]
                    )

        return quadro

    return get_session_cache(request, 'index_calendarios_academicos_professores', do, 24 * 3600)


@login_required()
@rtr()
def calendarioacademico(request, pk):
    obj = get_object_or_404(CalendarioAcademico.locals, pk=pk)
    aluno = Aluno.objects.filter(matricula=request.user.username)
    aluno = aluno and aluno[0] or None
    calendario = obj.anual()
    title = str(obj)
    is_popup = request.GET.get('_popup')
    return locals()


@permission_required('edu.change_cursocampus')
@rtr()
def replicar_cursocampus(request, pk):
    title = 'Replicação de Curso'
    curso_campus = get_object_or_404(CursoCampus.locals, pk=pk)
    form = ReplicacaoCursoCampusForm(data=request.POST or None, curso_campus=curso_campus)
    if request.POST and form.is_valid():
        try:
            resultado = form.processar(curso_campus)
            return httprr('..', mark_safe(f'Curso replicado com sucesso. <a href="/admin/edu/cursocampus/{resultado.pk}/">Você deseja editá-lo?</a>'))
        except ValidationError as e:
            return httprr('..', f'Não foi possível replicar o curso: {e.messages[0]}', 'error')
    return locals()


@permission_required('edu.change_calendarioacademico')
@rtr()
def replicar_calendario(request, pk):
    title = 'Replicação de Calendário'
    calendario = get_object_or_404(CalendarioAcademico.locals, pk=pk)

    form = ReplicacaoCalendarioForm(data=request.POST or None)
    if form.is_valid():
        resultado = form.processar(calendario)
        return httprr('..', mark_safe('Calendário(s) replicado(s) com sucesso. <a href="/admin/edu/calendarioacademico/?id__in={}">Você deseja editá-lo(s)?</a>'.format(','.join(resultado))))

    return locals()


@group_required('Diretor de Avaliação e Regulação do Ensino')
@rtr()
def editar_legislacao_matriz(request, pk):
    obj = get_object_or_404(MatrizCurso, pk=pk)
    title = str(obj.matriz.descricao)
    form = EditarLegislacaoForm(data=request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Edição realizada com sucesso.')
    return locals()


@permission_required('edu.change_autorizacao')
@rtr()
def autorizacao_matriz_curso(request, pk, pk_autorizacao=None):
    obj = get_object_or_404(MatrizCurso, pk=pk)
    if pk_autorizacao:
        instance = Autorizacao.objects.get(pk=pk_autorizacao)
    else:
        instance = Autorizacao()
        instance.matriz_curso = obj
    title = str(obj.matriz.descricao)
    form = AutorizacaoForm(data=request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada com sucesso.')
    return locals()


@permission_required('edu.change_reconhecimento')
@rtr()
def reconhecimento_matriz_curso(request, pk, pk_reconhecimento=None):
    obj = get_object_or_404(MatrizCurso, pk=pk)
    if pk_reconhecimento:
        instance = Reconhecimento.objects.get(pk=pk_reconhecimento)
    else:
        instance = Reconhecimento()
        instance.matriz_curso = obj
    title = str(obj.matriz.descricao)
    form = ReconhecimentoForm(data=request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada com sucesso.')
    return locals()


@permission_required('edu.view_matriz')
@rtr()
def matriz(request, pk):
    obj = get_object_or_404(Matriz, pk=pk)
    is_avaliador_regulador = in_group(request.user, 'Diretor de Avaliação e Regulação do Ensino')
    pode_editar_matriz = request.user.has_perm('edu.change_matriz')
    componentes_curriculares = obj.componentecurricular_set.select_related('nucleo', 'componente')
    periodos = list(range(1, obj.qtd_periodos_letivos + 1))
    exibir_classificacao_complementar = ClassificacaoComplementarComponenteCurricular.objects.exists()
    title = str(obj)
    if 'xls' in request.GET:
        rows = [
            ['#', 'Período', 'Sigla', 'Componente', 'Tipo', 'Optativo', 'Qtd. Avaliações', 'Núcleo', 'CH Componente', 'CH Teórica', 'CH Prática', 'Pré-Requisitos', 'Co-Requisitos', 'Classificação Complementar']
        ]
        count = 0
        for componente_curricular in obj.componentecurricular_set.all():
            count += 1
            if componente_curricular.optativo:
                optativo = 'Sim'
            else:
                optativo = 'Não'
            ch_componente = f'CH Relógio: {componente_curricular.componente.ch_hora_relogio}, CH Aula: {componente_curricular.componente.ch_hora_aula}'
            row = [
                count,
                format_(componente_curricular.periodo_letivo),
                format_(componente_curricular.componente.sigla),
                format_(f'{componente_curricular.componente.id} - {componente_curricular.componente.descricao}'),
                format_(componente_curricular.get_tipo_display()),
                format_(optativo),
                format_(componente_curricular.qtd_avaliacoes),
                format_(componente_curricular.nucleo),
                format_(ch_componente),
                format_(componente_curricular.ch_presencial),
                format_(componente_curricular.ch_pratica),
                format_(', '.join(componente_curricular.pre_requisitos.all().values_list('componente__descricao', flat=True))),
                format_(', '.join(componente_curricular.co_requisitos.all().values_list('componente__descricao', flat=True))),
                format_(componente_curricular.classificacao_complementar),
            ]
            rows.append(row)
        return XlsResponse(rows)
    return locals()


@permission_required('edu.view_matriz')
@documento()
@rtr()
def matriz_pdf(request, pk):
    obj = get_object_or_404(Matriz, pk=pk)
    componentes_curriculares = obj.componentecurricular_set.all()
    periodos = list(range(1, obj.qtd_periodos_letivos + 1))
    title = str(obj)
    uo = request.user.get_profile().funcionario.setor.uo
    return locals()


@permission_required('edu.view_matriz')
@documento()
@rtr()
def matriz_nucleo_pdf(request, pk):
    obj = get_object_or_404(Matriz, pk=pk)
    qtd_semestre = 2 * obj.qtd_periodos_letivos
    periodos = list(range(1, obj.qtd_periodos_letivos + 1))
    title = str(obj)
    uo = request.user.get_profile().funcionario.setor.uo

    nucleos_componentes_obrigatorios = Nucleo.objects.filter(
        componentecurricular__matriz=obj, componentecurricular__in=obj.get_componentes_curriculares_regulares_obrigatorios()
    ).distinct()
    for nucleo in nucleos_componentes_obrigatorios:
        nucleo.componentes_regulares = obj.get_componentes_curriculares_regulares_obrigatorios().filter(nucleo=nucleo)
        nucleo.subtotal = []
        for periodo_letivo in periodos:
            nucleo.subtotal.append(obj.get_qtd_credito_componentes_obrigatorios(nucleo=nucleo, periodo_letivo=periodo_letivo))
        nucleo.subtotal.append(obj.get_ch_componentes_obrigatorios(nucleo=nucleo, relogio=False))
        nucleo.subtotal.append(obj.get_ch_componentes_obrigatorios(nucleo=nucleo))
        nucleo.total = []
        for periodo_letivo in periodos:
            nucleo.total.append(obj.get_qtd_credito_componentes_obrigatorios(periodo_letivo=periodo_letivo))
        nucleo.total.append(obj.get_ch_componentes_obrigatorios(relogio=False))
        nucleo.total.append(obj.get_ch_componentes_obrigatorios())

    nucleos_componentes_optativos = Nucleo.objects.filter(componentecurricular__matriz=obj, componentecurricular__in=obj.get_componentes_curriculares_optativos()).distinct()
    for nucleo in nucleos_componentes_optativos:
        nucleo.componentes_optativos = obj.get_componentes_curriculares_optativos().filter(nucleo=nucleo)
        nucleo.subtotal = []
        nucleo.subtotal.append(obj.get_qtd_credito_componentes_optativos(nucleo=nucleo))
        nucleo.subtotal.append(obj.get_ch_componentes_optativos(nucleo=nucleo, relogio=False))
        nucleo.subtotal.append(obj.get_ch_componentes_optativos(nucleo=nucleo))
        nucleo.total = []
        nucleo.total.append(obj.get_qtd_credito_componentes_optativos())
        nucleo.total.append(obj.get_ch_componentes_optativos(relogio=False))
        nucleo.total.append(obj.get_ch_componentes_optativos())

    nucleos_componentes_seminarios = Nucleo.objects.filter(componentecurricular__matriz=obj, componentecurricular__in=obj.get_componentes_curriculares_seminario()).distinct()
    for nucleo in nucleos_componentes_seminarios:
        nucleo.componentes_seminarios = obj.get_componentes_curriculares_seminario().filter(nucleo=nucleo)
        nucleo.subtotal = []
        for periodo_letivo in periodos:
            nucleo.subtotal.append(obj.get_qtd_credito_componentes_seminarios(nucleo=nucleo, periodo_letivo=periodo_letivo))
        nucleo.subtotal.append(obj.get_ch_componentes_seminario(nucleo=nucleo, relogio=False))
        nucleo.subtotal.append(obj.get_ch_componentes_seminario(nucleo=nucleo))
        nucleo.total = []
        for periodo_letivo in periodos:
            nucleo.total.append(obj.get_qtd_credito_componentes_seminarios(periodo_letivo=periodo_letivo))
        nucleo.total.append(obj.get_ch_componentes_seminario(relogio=False))
        nucleo.total.append(obj.get_ch_componentes_seminario())

    nucleos_componentes_pratica_profissional = Nucleo.objects.filter(
        componentecurricular__matriz=obj, componentecurricular__in=obj.get_componentes_curriculares_pratica_profissional()
    ).distinct()
    for nucleo in nucleos_componentes_pratica_profissional:
        nucleo.componentes_seminarios = obj.get_componentes_curriculares_pratica_profissional().filter(nucleo=nucleo)
        nucleo.subtotal = []
        for periodo_letivo in periodos:
            nucleo.subtotal.append(obj.get_qtd_credito_componentes_pratica_profissional(nucleo=nucleo, periodo_letivo=periodo_letivo))
        nucleo.subtotal.append(obj.get_ch_componentes_pratica_profissional(nucleo=nucleo, relogio=False))
        nucleo.subtotal.append(obj.get_ch_componentes_pratica_profissional(nucleo=nucleo))
        nucleo.total = []
        for periodo_letivo in periodos:
            nucleo.total.append(obj.get_qtd_credito_componentes_pratica_profissional(periodo_letivo=periodo_letivo))
        nucleo.total.append(obj.get_ch_componentes_pratica_profissional(relogio=False))
        nucleo.total.append(obj.get_ch_componentes_pratica_profissional())

    creditos_totais = []
    for periodo_letivo in periodos:
        creditos_totais.append(
            obj.get_qtd_credito_componentes_obrigatorios(periodo_letivo=periodo_letivo)
            + obj.get_qtd_credito_componentes_seminarios(periodo_letivo=periodo_letivo)
            + obj.get_qtd_credito_componentes_pratica_profissional(periodo_letivo=periodo_letivo)
        )
    creditos_totais.append(obj.ch_atividades_complementares)
    creditos_totais.append(
        obj.get_ch_componentes_obrigatorios(relogio=False) + obj.get_ch_componentes_seminario(relogio=False) + obj.get_ch_componentes_pratica_profissional(relogio=False)
    )
    creditos_totais.append(
        obj.ch_componentes_optativos + obj.get_ch_componentes_obrigatorios() + obj.get_ch_componentes_seminario() + obj.get_ch_componentes_pratica_profissional()
    )
    return locals()


@login_required()
@rtr()
def grade_curricular(request, matriz_pk):
    obj = get_object_or_404(Matriz, pk=matriz_pk)
    title = f'Grade Curricular: {str(obj)}'
    if (
        not request.user.has_perm('edu.view_matriz')
        and len(Aluno.objects.filter(pessoa_fisica=request.user.get_profile(), matriz=obj)) == 0
        and not in_group(request.user, 'Estagiário')
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    return locals()


@permission_required('edu.add_matriz')
@rtr()
def replicar_matriz(request, pk):
    title = 'Replicação de Matriz'
    matriz = get_object_or_404(Matriz, pk=pk)
    form = ReplicacaoMatrizForm(matriz, data=request.POST or None)
    if request.POST and form.is_valid():
        try:
            resultado = form.processar()
            return httprr(f'/edu/matriz/{resultado.id}/', 'Matriz replicada com sucesso.')
        except ValidationError as e:
            return httprr('..', f'Não foi possível replicar a matriz: {e.messages[0]}', 'error')
    return locals()


@permission_required('edu.add_componentecurricular')
@rtr()
def vincular_componente(request, matriz_pk, componente_pk=None):
    title = '{} Componente de matriz'.format(componente_pk and 'Editar' or 'Vincular')
    matriz = get_object_or_404(Matriz, pk=matriz_pk)

    if not matriz.pode_ser_editada(request.user):
        return httprr(f'/edu/matriz/{matriz.pk}/?tab=componentes', 'A matriz não pode ser editada.', 'error')

    if componente_pk:
        mc = get_object_or_404(ComponenteCurricular.objects, componente__pk=componente_pk, matriz=matriz)

    form = ComponenteCurricularForm(matriz, data=request.POST or None, instance=componente_pk and mc or None)

    if form.is_valid():
        form.save()
        redirect = '..'
        if 'continuar' in request.POST:
            redirect = '.'
        if not componente_pk:
            return httprr(redirect, 'Componente de matriz adicionado com sucesso.')
        else:
            return httprr(f'/edu/matriz/{matriz.pk}/?tab=componentes', 'Componente de matriz atualizado com sucesso.')
    return locals()


@permission_required('edu.add_componentecurricular')
@rtr()
def definir_requisitos(request, pk):
    title = 'Definir Pré e Co-requisitos'
    instance = get_object_or_404(ComponenteCurricular, pk=pk)
    form = RequisitosComponenteCurricularForm(request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        return httprr('..', 'Requisitos definidos com sucesso.')
    return locals()


@permission_required('edu.add_componentecurricular')
def desvincular_componente(request, mc_pk):
    mc = get_object_or_404(ComponenteCurricular, pk=mc_pk)

    if not mc.matriz.pode_ser_editada(request.user):
        return httprr(f'/edu/matriz/{mc.matriz.pk}/?tab=componentes', 'A matriz não pode ser editada.', 'error')

    mc.delete()
    return httprr(f'{mc.matriz.get_absolute_url()}?tab=componentes', 'Componente desvinculado com sucesso.')


@permission_required('edu.gerar_turmas')
@rtr()
def gerar_turmas(request):
    title = 'Gerar Turmas'
    form = GerarTurmasForm(request, data=request.GET or None, initial=dict(periodo_letivo=1))
    if form.is_valid():
        form.processar(commit=True)
        ids = []
        for turma in form.turmas:
            ids.append(str(turma.id))
        ano = get_object_or_404(Ano, ano=datetime.datetime.now().year)
        return httprr('/admin/edu/turma/?id__in={}'.format(','.join(ids)), 'Turmas geradas com sucesso.')
    return locals()


@permission_required('edu.view_turma')
@rtr()
def turma(request, pk):
    manager = in_group(request.user, 'Diretor Acadêmico') and Turma.objects or Turma.locals
    obj = get_object_or_404(manager, pk=pk)
    title = f'Turma {obj}'
    is_administrador = in_group(request.user, 'Administrador Acadêmico')
    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, obj.curso_campus)

    diarios = obj.diario_set.order_by('componente_curricular__componente')

    alunos = obj.get_alunos_matriculados()
    alunos_diarios = obj.get_alunos_matriculados_diarios()
    diarios_pendentes = obj.diarios_pendentes()
    situacoes_inativas = (
        SituacaoMatriculaPeriodo.CANCELADA,
        SituacaoMatriculaPeriodo.CANCELAMENTO_COMPULSORIO,
        SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DESLIGAMENTO,
        SituacaoMatriculaPeriodo.CANCELAMENTO_POR_DUPLICIDADE,
        SituacaoMatriculaPeriodo.TRANCADA,
        SituacaoMatriculaPeriodo.TRANCADA_VOLUNTARIAMENTE,
        SituacaoMatriculaPeriodo.TRANSF_CURSO,
    )
    qtd_alunos_ativos = alunos.exclude(situacao__in=situacoes_inativas).count()
    qtd_alunos_ativos += alunos_diarios.exclude(situacao__in=situacoes_inativas).count()

    ids = request.GET.get('matriculas_periodo')
    if ids:
        if not pode_realizar_procedimentos:
            return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
        matriculas_periodo = MatriculaPeriodo.objects.filter(id__in=ids.split('_'), turma=obj)
        obj.remover_alunos(matriculas_periodo, request.user)

        return httprr(f'/edu/turma/{obj.pk}/?tab=dados_alunos', 'Aluno(s) removido(s) com sucesso.')

    semestre = request.GET.get('semestre') or '1'
    turnos = obj.get_horarios(semestre)
    diarios_por_sigla = diarios.filter(horarioauladiario__isnull=False).distinct().order_by('componente_curricular__componente__sigla')
    return locals()


@group_required('Administrador Acadêmico, Diretor Acadêmico, Coordenador de Curso, Coordenador de Modalidade Acadêmica, Secretário Acadêmico')
@rtr("transferir_turma_ou_diario.html")
def transferir_turma(request, turma_origem, alunos):
    title = 'Transferência de Turma'
    turma_origem = get_object_or_404(Turma.locals, pk=turma_origem)

    if turma_origem.matriz.estrutura.tipo_avaliacao != turma_origem.matriz.estrutura.TIPO_AVALIACAO_SERIADO:
        httprr('..', 'Transferência de turma só é realizada para alunos do regime seriado.', 'error')
    matriculas_periodo = alunos.split('_')

    aluno_com_nota = False
    qs_diarios = turma_origem.diario_set.all()
    mp = MatriculaPeriodo.objects.filter(id__in=matriculas_periodo)
    matriculas = MatriculaDiario.objects.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO, diario__in=qs_diarios, matricula_periodo__in=mp)

    for matricula in matriculas:
        if matricula.tem_nota_lancada():
            aluno_com_nota = True
            break

    if aluno_com_nota:
        return httprr(f'/edu/turma/{turma_origem.pk}/?tab=dados_alunos', 'Só é possível realizar a transferência de alunos sem nota lançada.', 'error')

    form = TransferirTurmaForm(turma_origem, data=request.POST or None)

    turma_destino = form.get_entered_data('turma_destino')
    if turma_destino:
        diarios = turma_origem.transferir(matriculas_periodo, turma_destino, False)
        falta_diario = False
        for diario in diarios:
            if not diario[1]:
                falta_diario = True
                break

    if form.is_valid():
        diarios = turma_origem.transferir(matriculas_periodo, turma_destino, True)
        return httprr(f'/edu/turma/{turma_destino.pk}/', 'Transferência realizada com sucesso.')

    return locals()


@group_required('Administrador Acadêmico, Diretor Acadêmico, Coordenador de Curso, Coordenador de Modalidade Acadêmica, Secretário Acadêmico')
@rtr("transferir_turma_ou_diario.html")
def transferir_diario(request, diario_origem, matriculas_diario):
    diario_origem = get_object_or_404(Diario.locals, pk=diario_origem)
    matriculas_diario = matriculas_diario.split('_')

    aluno_com_nota = False
    matriculas = diario_origem.matriculadiario_set.filter(pk__in=matriculas_diario, situacao__in=[MatriculaDiario.SITUACAO_CURSANDO])

    if not matriculas:
        return httprr(f'/edu/diario/{diario_origem.pk}/?tab=notas_faltas', 'Só é possível realizar a transferência de alunos com situação cursando.', 'error')

    for matricula in matriculas:
        if matricula.tem_nota_lancada():
            aluno_com_nota = True
            break
    if aluno_com_nota:
        return httprr(f'/edu/diario/{diario_origem.pk}/?tab=notas_faltas', 'Só é possível realizar a transferência de alunos sem nota lançada.', 'error')

    title = 'Transferência de Diário'
    form = TransferirDiarioForm(diario_origem, data=request.POST or None)

    diario_destino = form.get_entered_data('diario_destino')

    diarios = []
    if diario_destino:
        diarios.append((diario_origem, diario_destino))

    turma_origem = diario_origem.turma
    turma_destino = diario_destino and diario_destino.turma or None

    if form.is_valid():
        diario_origem.transferir(matriculas_diario, diario_destino, True)
        return httprr(f'/edu/diario/{diario_origem.pk}/', 'Transferência realizada com sucesso.')
    return locals()


@permission_required('edu.view_turma')
@rtr()
def extrato_transferencia_turma(request, pk):
    matricula_periodo = get_object_or_404(MatriculaPeriodo, pk=pk)
    diarios = matricula_periodo.diario_set.filter(situacao=MatriculaDiario.SITUACAO_TRANSFERIDO)
    return locals()


@permission_required('edu.view_turma')
@documento()
@rtr()
def horarios_turma_pdf(request, pk):
    obj = get_object_or_404(Turma.locals, pk=pk)
    uo = obj.curso_campus.diretoria.setor.uo
    title = str(obj)
    diarios = obj.diario_set.order_by('componente_curricular__componente')
    semestre = request.GET.get('semestre') or '1'
    turnos = obj.get_horarios(semestre)
    diarios_por_sigla = diarios.filter(horarioauladiario__isnull=False).distinct().order_by('componente_curricular__componente__sigla')
    return locals()


@permission_required('edu.change_turma')
@rtr()
def adicionar_aluno_turma(request, pk):
    turma = get_object_or_404(Turma.locals, pk=pk)
    title = 'Adicionar Aluno à Turma'
    turnos = Turno.objects.all()
    polos = Polo.objects.all().order_by("descricao")
    polo = None
    if 'matriculas_periodo' in request.POST:
        matriculas_periodo = MatriculaPeriodo.objects.filter(id__in=request.POST.getlist('matriculas_periodo'))
        turma.matricular_alunos(matriculas_periodo)
        return httprr(f'/edu/turma/{turma.pk}/?tab=dados_alunos', 'Aluno(s) matriculado(s) com sucesso.')
    for turno in turnos:
        if 'turno' in request.POST:
            if turno.pk == int(request.POST['turno']):
                turno.selecionado = True
                break
        else:
            if turno.pk == turma.turno.pk:
                turno.selecionado = True
                break

    matriculas_periodo = turma.get_alunos_apto_matricula(turno)

    if request.POST.get('polo'):
        pk = int(request.POST.get('polo', '0'))
    elif hasattr(turma.polo, 'pk'):
        pk = turma.polo.pk
    else:
        pk = 0

    if pk > 0:
        for polo in polos:
            if polo.pk == pk:
                polo.selecionado = True
                break
        matriculas_periodo = matriculas_periodo.filter(aluno__polo=polo)

    return locals()


@permission_required('ppe.view_turma')
@rtr()
def mapa_turma(request, pk):
    turma = get_object_or_404(Turma.locals, pk=pk)

    title = f'Mapa da Turma - {turma}'
    form = MapaTurmaForm(turma.diario_set.all().order_by('componente_curricular__componente__sigla'), request.POST or None)
    diarios = None
    if form.is_valid():
        diarios = form.cleaned_data['diarios']

        quantidade = 1
        for diario in diarios:
            if len(diario.get_lista_etapas()) > quantidade:
                quantidade = len(diario.get_lista_etapas())
        etapas = OrderedDict()
        for etapa in range(1, quantidade + 1):
            etapas[f'etapa_{etapa}'] = f'Etapa {etapa}'
        etapas['etapa_final'] = 'Etapa Final'

        matriculas_periodo = turma.get_alunos_relacionados()
        matriculas_diario = (
            MatriculaDiario.locals.filter(diario__in=diarios)
            .order_by('matricula_periodo__aluno__pessoa_fisica__nome', 'matricula_periodo__aluno__pk', 'diario__componente_curricular__componente__sigla', 'diario')
            .annotate(total_faltas=Sum('falta__quantidade'))
            .select_related(
                'matricula_periodo__situacao',
                'matricula_periodo__turma__matriz__estrutura',
                'matricula_periodo__aluno__matriz__estrutura',
                'diario__componente_curricular__componente',
                'diario__estrutura_curso',
            )
        )

        tabela_mapa = []
        count = 0
        situacoes_diario = [md.get_situacao_diario_resumida() for md in matriculas_diario]
        for matricula_periodo in matriculas_periodo:
            aluno_diarios = []
            for diario in diarios:
                if count < matriculas_diario.count() and matriculas_diario[count].diario.pk == diario.pk and matriculas_diario[count].matricula_periodo.pk == matricula_periodo.pk:
                    aluno_diarios.append(
                        {
                            'md': matriculas_diario[count],
                            'rotulo': situacoes_diario[count]['rotulo'],
                            'faltasetapa1': matriculas_diario[count].total_faltas,
                            'percentualfrequencia': matriculas_diario[count].get_percentual_carga_horaria_frequentada(),
                        }
                    )
                    count += 1
                else:
                    aluno_diarios.append({'md': None})

            tabela_mapa.append([matricula_periodo, aluno_diarios])

    if request.POST.get('xls'):
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=mapa_turma.xls'

        wb = xlwt.Workbook(encoding='utf-8')
        sheet1 = wb.add_sheet('Etapa 1')
        sheet2 = wb.add_sheet('Etapa 2')
        sheet3 = wb.add_sheet('Etapa 3')
        sheet4 = wb.add_sheet('Etapa 4')
        sheetfinal = wb.add_sheet('Etapa Final')
        style = xlwt.easyxf('pattern: pattern solid, fore_colour gray25;' 'borders: left thin, right thin, top thin, bottom thin;' 'font: colour black, bold True;')

        sheet1.row(0).write(0, '', style)
        sheet2.row(0).write(0, '', style)
        sheet3.row(0).write(0, '', style)
        sheet4.row(0).write(0, '', style)
        sheetfinal.row(0).write(0, '', style)

        colspan = 3
        count = 1
        for diario in diarios:
            sheet1.write_merge(0, 0, count * colspan - (colspan - 1), count * colspan, diario.componente_curricular.componente.sigla, style)
            sheet2.write_merge(0, 0, count * colspan - (colspan - 1), count * colspan, diario.componente_curricular.componente.sigla, style)
            sheet3.write_merge(0, 0, count * colspan - (colspan - 1), count * colspan, diario.componente_curricular.componente.sigla, style)
            sheet4.write_merge(0, 0, count * colspan - (colspan - 1), count * colspan, diario.componente_curricular.componente.sigla, style)
            sheetfinal.write_merge(0, 0, count * colspan - (colspan - 1), count * colspan, diario.componente_curricular.componente.sigla, style)
            count += 1

        sheet1.row(1).write(0, 'Carga Horária', style)
        sheet2.row(1).write(0, 'Carga Horária', style)
        sheet3.row(1).write(0, 'Carga Horária', style)
        sheet4.row(1).write(0, 'Carga Horária', style)
        sheetfinal.row(1).write(0, 'Carga Horária', style)
        count = 1
        for diario in diarios:
            sheet1.write_merge(
                1,
                1,
                count * colspan - (colspan - 1),
                count * colspan,
                f'{diario.get_carga_horaria_cumprida()}H de {diario.componente_curricular.componente.ch_hora_aula}H',
                style,
            )
            sheet2.write_merge(
                1,
                1,
                count * colspan - (colspan - 1),
                count * colspan,
                f'{diario.get_carga_horaria_cumprida()}H de {diario.componente_curricular.componente.ch_hora_aula}H',
                style,
            )
            sheet3.write_merge(
                1,
                1,
                count * colspan - (colspan - 1),
                count * colspan,
                f'{diario.get_carga_horaria_cumprida()}H de {diario.componente_curricular.componente.ch_hora_aula}H',
                style,
            )
            sheet4.write_merge(
                1,
                1,
                count * colspan - (colspan - 1),
                count * colspan,
                f'{diario.get_carga_horaria_cumprida()}H de {diario.componente_curricular.componente.ch_hora_aula}H',
                style,
            )
            sheetfinal.write_merge(
                1,
                1,
                count * colspan - (colspan - 1),
                count * colspan,
                f'{diario.get_carga_horaria_cumprida()}H de {diario.componente_curricular.componente.ch_hora_aula}H',
                style,
            )
            sheet1.row(2).write(count * colspan - (colspan - 1), 'N', style)
            sheet2.row(2).write(count * colspan - (colspan - 1), 'N', style)
            sheet3.row(2).write(count * colspan - (colspan - 1), 'N', style)
            sheet4.row(2).write(count * colspan - (colspan - 1), 'N', style)
            sheetfinal.row(2).write(count * colspan - (colspan - 1), 'N', style)
            sheet1.row(2).write(count * colspan - (colspan - 1) + 1, 'F', style)
            sheet2.row(2).write(count * colspan - (colspan - 1) + 1, 'F', style)
            sheet3.row(2).write(count * colspan - (colspan - 1) + 1, 'F', style)
            sheet4.row(2).write(count * colspan - (colspan - 1) + 1, 'F', style)
            sheetfinal.row(2).write(count * colspan - (colspan - 1) + 1, 'F', style)
            sheet1.row(2).write(count * colspan - (colspan - 1) + 2, 'Sit.', style)
            sheet2.row(2).write(count * colspan - (colspan - 1) + 2, 'Sit.', style)
            sheet3.row(2).write(count * colspan - (colspan - 1) + 2, 'Sit.', style)
            sheet4.row(2).write(count * colspan - (colspan - 1) + 2, 'Sit.', style)
            sheetfinal.row(2).write(count * colspan - (colspan - 1) + 2, 'Sit.', style)
            count += 1

        sheet1.row(2).write(0, 'Aluno', style)
        sheet2.row(2).write(0, 'Aluno', style)
        sheet3.row(2).write(0, 'Aluno', style)
        sheet4.row(2).write(0, 'Aluno', style)
        sheetfinal.row(2).write(0, 'Aluno', style)
        posicao_media = (diarios.count() * colspan) + 1
        sheet1.write_merge(0, 2, posicao_media, posicao_media, 'Média', style)
        sheet2.write_merge(0, 2, posicao_media, posicao_media, 'Média', style)
        sheet3.write_merge(0, 2, posicao_media, posicao_media, 'Média', style)
        sheet4.write_merge(0, 2, posicao_media, posicao_media, 'Média', style)
        sheetfinal.write_merge(0, 2, posicao_media, posicao_media, 'Média', style)
        count = 3
        for item in tabela_mapa:
            sheet1.row(count).write(0, item[0].aluno.get_nome_social_composto())
            sheet2.row(count).write(0, item[0].aluno.get_nome_social_composto())
            sheet3.row(count).write(0, item[0].aluno.get_nome_social_composto())
            sheet4.row(count).write(0, item[0].aluno.get_nome_social_composto())
            sheetfinal.row(count).write(0, item[0].aluno.get_nome_social_composto())

            count_etapa1 = 1
            # Etapa 1
            for value in item[1]:
                if value.get('md'):
                    sheet1.row(count).write(count_etapa1 * colspan - (colspan - 1), value.get('md').nota_1 or '-')
                    sheet1.row(count).write(count_etapa1 * colspan - (colspan - 1) + 1, value.get('faltasetapa1') or '-')
                    sheet1.row(count).write(count_etapa1 * colspan - (colspan - 1) + 2, value.get('rotulo') or '-')
                else:
                    sheet1.row(count).write(count_etapa1 * colspan - (colspan - 1), '-')
                    sheet1.row(count).write(count_etapa1 * colspan - (colspan - 1) + 1, '-')
                    sheet1.row(count).write(count_etapa1 * colspan - (colspan - 1) + 2, '-')
                count_etapa1 += 1
            sheet1.row(count).write(posicao_media, format_(item[0].get_media_na_primeira_etapa()))

            count_etapa2 = 1
            # Etapa 2
            for value in item[1]:
                if value.get('md'):
                    sheet2.row(count).write(count_etapa2 * colspan - (colspan - 1), value.get('md').nota_2 or '-')
                    sheet2.row(count).write(count_etapa2 * colspan - (colspan - 1) + 1, value.get('faltasetapa2') or '-')
                    sheet2.row(count).write(count_etapa2 * colspan - (colspan - 1) + 2, value.get('rotulo') or '-')
                else:
                    sheet2.row(count).write(count_etapa2 * colspan - (colspan - 1), '-')
                    sheet2.row(count).write(count_etapa2 * colspan - (colspan - 1) + 1, '-')
                    sheet2.row(count).write(count_etapa2 * colspan - (colspan - 1) + 2, '-')
                count_etapa2 += 1
            sheet2.row(count).write(posicao_media, format_(item[0].get_media_na_segunda_etapa()))

            count_etapa3 = 1
            # Etapa 3
            for value in item[1]:
                if value.get('md'):
                    sheet3.row(count).write(count_etapa3 * colspan - (colspan - 1), value.get('md').nota_3 or '-')
                    sheet3.row(count).write(count_etapa3 * colspan - (colspan - 1) + 1, value.get('faltasetapa3') or '-')
                    sheet3.row(count).write(count_etapa3 * colspan - (colspan - 1) + 2, value.get('rotulo') or '-')
                else:
                    sheet3.row(count).write(count_etapa3 * colspan - (colspan - 1), '-')
                    sheet3.row(count).write(count_etapa3 * colspan - (colspan - 1) + 1, '-')
                    sheet3.row(count).write(count_etapa3 * colspan - (colspan - 1) + 2, '-')
                count_etapa3 += 1
            sheet3.row(count).write(posicao_media, format_(item[0].get_media_na_terceira_etapa()))

            count_etapa4 = 1
            # Etapa 4
            for value in item[1]:
                if value.get('md'):
                    sheet4.row(count).write(count_etapa4 * colspan - (colspan - 1), value.get('md').nota_4 or '-')
                    sheet4.row(count).write(count_etapa4 * colspan - (colspan - 1) + 1, value.get('faltasetapa4') or '-')
                    sheet4.row(count).write(count_etapa4 * colspan - (colspan - 1) + 2, value.get('rotulo') or '-')
                else:
                    sheet4.row(count).write(count_etapa4 * colspan - (colspan - 1), '-')
                    sheet4.row(count).write(count_etapa4 * colspan - (colspan - 1) + 1, '-')
                    sheet4.row(count).write(count_etapa4 * colspan - (colspan - 1) + 2, '-')
                count_etapa4 += 1
            sheet4.row(count).write(posicao_media, format_(item[0].get_media_na_quarta_etapa()))

            # Etapa Final
            count_etapa_final = 1
            for value in item[1]:
                if value.get('md'):
                    sheetfinal.row(count).write(count_etapa_final * colspan - (colspan - 1), value.get('md').nota_final or '-')
                    sheetfinal.row(count).write(count_etapa_final * colspan - (colspan - 1) + 1, '-')
                    sheetfinal.row(count).write(count_etapa_final * colspan - (colspan - 1) + 2, value.get('rotulo') or '-')
                else:
                    sheetfinal.row(count).write(count_etapa_final * colspan - (colspan - 1), '-')
                    sheetfinal.row(count).write(count_etapa_final * colspan - (colspan - 1) + 1, '-')
                    sheetfinal.row(count).write(count_etapa_final * colspan - (colspan - 1) + 2, '-')
                count_etapa_final += 1
            sheetfinal.row(count).write(posicao_media, format_(item[0].get_media_na_etapa_final()))

            count += 1

        wb.save(response)

        return response

    return locals()


@documento(enumerar_paginas=False)
@rtr('comprovante_matricula_pdf.html')
def comprovante_matricula_pdf(request, pk):
    hoje = datetime.date.today()
    aluno = get_object_or_404(Aluno.locals, pk=pk)

    if not request.user.has_perm('edu.efetuar_matricula') and not in_group(request.user, 'Estagiário') and not request.session.get('matricula-servico-impressao') == pk:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not aluno.possui_historico():
        return httprr('..', 'Aluno importado. Não possui diários no SUAP.', 'error')

    if aluno.is_concluido():
        return httprr('..', 'Aluno já concluiu, não é possível emitir o comprovante de matrícula.', 'error')

    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()

    uo = aluno.curso_campus.diretoria.setor.uo
    return locals()


@documento('Comprovante de Dados Acadêmicos', validade=30, modelo='edu.aluno')
@rtr()
def comprovante_dados_academicos_pdf(request, pk):
    hoje = datetime.date.today()
    aluno = get_object_or_404(Aluno.locals, pk=pk)

    if (
        not aluno.is_user(request)
        and not request.user.has_perm('edu.efetuar_matricula')
        and not in_group(request.user, 'Estagiário, Pedagogo')
        and not request.session.get('matricula-servico-impressao') == pk
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not aluno.possui_historico():
        return httprr('.', 'Aluno importado. Não possui diários no SUAP.', 'error')

    uo = aluno.curso_campus.diretoria.setor.uo
    procedimentos = aluno.get_procedimentos_matricula()
    return locals()


def emitir_boletim_pdf(request, pks):
    pks = pks.split('_')
    matriculas_periodo = MatriculaPeriodo.objects.filter(pk__in=pks)
    if request.user.is_anonymous:
        if not matriculas_periodo.filter(aluno__matricula=request.session.get('matricula_aluno_como_resposavel')).exists():
            return httprr('/', 'Você não tem permissão para acessar está página.', 'error')

    elif not request.user.has_perm('edu.emitir_boletim'):
        if len(pks) != 1 or not matriculas_periodo[0].aluno.is_user(request):
            return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if matriculas_periodo.count() > 1:
        return tasks.emitir_boletins_pdf(request, matriculas_periodo)
    else:
        return emitir_boletins_aluno_pdf(request, matriculas_periodo)


@documento()
@rtr('emitir_boletim_pdf.html')
def emitir_boletins_aluno_pdf(request, matriculas_periodo, task=None):
    title = 'Impressão de Boletim'
    hoje = datetime.date.today()
    site_url = settings.SITE_URL
    matriculas_periodo = matriculas_periodo.order_by('aluno__pessoa_fisica__nome')
    tem_nota_atitudinal = matriculas_periodo[0].utiliza_nota_atitudinal()
    uo = matriculas_periodo.exists() and matriculas_periodo.first().aluno.curso_campus.diretoria.setor.uo
    if task:
        task.start_progress(total=matriculas_periodo.count() + 50)
    i = 0
    for matricula_periodo in matriculas_periodo:
        if not matricula_periodo.aluno.get_matriculas_periodo_com_diario():
            return httprr('..', f'O Aluno com matrícula {matricula_periodo.aluno.matricula} não possui diário no SUAP.', 'error')
        matricula_periodo.matriculas_diario = matricula_periodo.matriculadiario_set.all().order_by('diario__componente_curricular__componente__descricao')
        if matricula_periodo.matriculas_diario:
            matricula_periodo.etapa = int(request.GET.get('etapa', 1))
            matricula_periodo.max_qtd_avaliacoes = 1
            for matricula_diario in matricula_periodo.matriculas_diario:
                if matricula_diario.diario.componente_curricular.qtd_avaliacoes > matricula_periodo.max_qtd_avaliacoes:
                    matricula_periodo.max_qtd_avaliacoes = matricula_diario.diario.componente_curricular.qtd_avaliacoes
        i += 1
        if task:
            task.update_progress(i)

    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()

    return locals()


@login_required()
@permission_required('edu.emitir_boletins')
@documento()
@rtr('emitir_boletim_diario_pdf.html')
def emitir_boletins_pdf(request, diario_pk):
    hoje = datetime.date.today()
    diario = get_object_or_404(Diario.locals, pk=diario_pk)
    qtd_avaliacoes = diario.componente_curricular.qtd_avaliacoes
    max_qtd_avaliacoes = qtd_avaliacoes
    uo = diario.turma.curso_campus.diretoria.setor.uo
    matriculas_diario = diario.matriculadiario_set.all().exclude(
        situacao__in=[MatriculaDiario.SITUACAO_TRANCADO, MatriculaDiario.SITUACAO_TRANSFERIDO, MatriculaDiario.SITUACAO_CANCELADO]
    )
    if not running_tests():
        matriculas_diario = matriculas_diario.order_by('matricula_periodo__aluno__pessoa_fisica__nome')
    title = str(diario)
    exibe_notas = max_qtd_avaliacoes > 0 and diario
    return locals()


@documento()
@login_required()
def emitir_historico_legado_pdf(request, pk):
    if not request.user.has_perm('edu.efetuar_matricula') and not request.user.has_perm('edu.view_registroemissaodiploma'):
        return httprr('/', 'Você não tem permissão para realizar isso.', 'error')
    return emitir_historico_legado(request, pk)


@rtr('emitir_historico_pdf.html')
def emitir_historico_legado(request, pk, eletronico=False):
    historicos = []
    aluno = get_object_or_404(Aluno, pk=pk)
    historicos.append(aluno.get_historico_legado(eletronico=eletronico))
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()
    cancelado_por_duplicidade = aluno.situacao_id == SituacaoMatricula.CANCELAMENTO_POR_DUPLICIDADE
    final = True
    return locals()


@rtr('emitir_historico_pdf.html')
def emitir_historico_pdf(request, pks, final=False, eletronico=False):
    is_proprio_aluno = True
    esconder_assinatura = 'digital' in request.GET
    if not final:
        is_proprio_aluno = get_object_or_404(Aluno.locals, pk=pks).is_user(request)

    is_servico_impressao = str(request.session.get('matricula-servico-impressao')) in pks

    if (
        not is_servico_impressao
        and not request.user.has_perm('edu.efetuar_matricula')
        and not in_group(request.user, 'Estagiário,Coordenador de Curso, Pedagogo, Professor')
        and not request.user.has_perm('edu.view_registroemissaodiploma')
        and not is_proprio_aluno
    ):
        return httprr('/', 'Você não tem permissão para realizar isso.', 'error')

    historicos = []

    if not "_" in pks:
        aluno = get_object_or_404(Aluno, pk=pks)
        title = str(aluno)
        if aluno.matriz:
            if aluno.matriz.estrutura and aluno.matriz.estrutura.proitec:
                return httprr('/', f'Aluno {title} de cursos PROITEC não possuem histórico.', 'error')
        else:
            return httprr('/', f'Aluno {title} não possui matriz associada.', 'error')

        if aluno.possui_historico():
            historicos.append(aluno.get_historico(final, Aluno.ORDENAR_HISTORICO_POR_PERIODO_MATRIZ, eletronico=eletronico))
        else:
            return httprr('/', f'Aluno {title} não foi matriculado através do SUAP ou não foi migrado do Q-Acadêmico.', 'error')
    else:
        alunos = Aluno.objects.filter(pk__in=pks.split('_'))
        count_historicos = alunos.count()
        for aluno in alunos:
            historicos.append(aluno.get_historico(final, Aluno.ORDENAR_HISTORICO_POR_PERIODO_MATRIZ, eletronico=eletronico))

    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()
    cancelado_por_duplicidade = aluno.situacao_id == SituacaoMatricula.CANCELAMENTO_POR_DUPLICIDADE
    return locals()


@documento('Histórico', validade=30, modelo='edu.aluno')
def emitir_historico_parcial_pdf(request, pk):
    aluno = get_object_or_404(Aluno.locals, pk=pk)
    if aluno.is_concluido():
        return httprr('/', 'O histórico parcial só pode ser emitido para alunos que não concluíram o curso.', 'error')

    return emitir_historico_pdf(request, pk)


@documento(enumerar_paginas=False)
@login_required()
def emitir_historico_final_pdf(request, pks):
    if not Aluno.objects.filter(pk__in=pks.split('_'), situacao__in=[SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO]).exists():
        return httprr('/', 'Os alunos selecionados ainda não estão formados ou concluídos.', 'error')
    if '_' in pks:
        merger = PdfFileMerger()
        for pk in pks.split('_'):
            response = emitir_historico_final_pdf(request, pk)
            merger.append(io.BytesIO(response.content))
        merged_file = tempfile.NamedTemporaryFile(suffix=".pdf", dir=settings.TEMP_DIR, delete=False)
        merger.write(merged_file.name)
        return HttpResponse(open(merged_file.name, 'r+b').read(), content_type='application/pdf')
    else:
        return emitir_historico_pdf(request, pks, final=True)


@rtr('emitir_historico_pdf.html')
def emitir_historico_legado_sica(request, pk, eletronico=False):
    historicos = []
    aluno = get_object_or_404(Aluno, pk=pk)
    historicos.append(aluno.get_historico_legado_sica(eletronico=eletronico))
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()
    cancelado_por_duplicidade = aluno.situacao_id == SituacaoMatricula.CANCELAMENTO_POR_DUPLICIDADE
    final = True
    return locals()


@documento(tipo_para_verificacao='Histórico Final', enumerar_paginas=False, pdf_response=False)
@login_required()
def emitir_historico_final_eletronico_pdf(request, pk, legado=False):
    qs = Aluno.objects.filter(pk=pk, situacao__in=[SituacaoMatricula.CONCLUIDO, SituacaoMatricula.FORMADO])
    qs = qs.filter(curso_campus__assinatura_eletronica=True) | qs.filter(curso_campus__assinatura_digital=True)
    aluno = qs.first()
    if aluno:
        if legado:
            if aluno.is_qacademico():
                return emitir_historico_legado(request, pk, eletronico=True)
            elif aluno.is_sica():
                return emitir_historico_legado_sica(request, pk, eletronico=True)
        else:
            return emitir_historico_pdf(request, pk, final=True, eletronico=True)


@rtr()
@permission_required('edu.gerar_relatorio')
def relatorio_faltas(request):
    title = 'Relatório de Faltas'
    campus = None
    if not in_group(request.user, 'Administrador Acadêmico, Coordenador de Atividades Estudantis Sistêmico, Assistente Social, Estagiário Acadêmico Sistêmico'):
        campus = request.user.get_vinculo().setor.uo
    form = RelatorioFaltasForm(campus, request.GET or None)
    if form.is_valid():
        turma = form.cleaned_data['turma']
        diario = form.cleaned_data['diario']
        aluno = form.cleaned_data['aluno']
        beneficio = form.cleaned_data['beneficio']
        programa = form.cleaned_data['programa']
        uo = form.cleaned_data['uo']
        diretoria = form.cleaned_data['diretoria']
        curso_campus = form.cleaned_data['curso_campus']
        ano_letivo = form.cleaned_data['ano_letivo']
        periodo_letivo = form.cleaned_data['periodo_letivo']
        situacao_periodo = form.cleaned_data['situacao_periodo']
        intervalo_inicio = form.cleaned_data['intervalo_inicio']
        intervalo_fim = form.cleaned_data['intervalo_fim']
        situacoes_inativas = form.cleaned_data['situacoes_inativas']

        meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]

        qs_aulas = Aula.objects.all()
        qs_matriculas_periodo = MatriculaPeriodo.objects.all()

        if aluno:
            qs_aulas = qs_aulas.filter(professor_diario__diario__matriculadiario__matricula_periodo__aluno_id=aluno.id)
            qs_matriculas_periodo = qs_matriculas_periodo.filter(aluno_id=aluno.id)

        if programa and 'ae' in settings.INSTALLED_APPS:
            Participacao = apps.get_model('ae', 'Participacao')
            participacoes = Participacao.abertas.filter(programa__in=programa)
            qs_matriculas_periodo = qs_matriculas_periodo.filter(aluno__in=participacoes.values_list('aluno', flat=True))

        if beneficio:
            qs_matriculas_periodo = qs_matriculas_periodo.filter(aluno__caracterizacao__beneficiario_programa_social=beneficio)

        if diario:
            qs_aulas = qs_aulas.filter(professor_diario__diario_id=diario.id)
            qs_matriculas_periodo = qs_matriculas_periodo.filter(matriculadiario__diario_id=diario.id)

        if turma:
            qs_aulas = qs_aulas.filter(professor_diario__diario__turma_id=turma.id)
            qs_matriculas_periodo = qs_matriculas_periodo.filter(turma_id=turma.id)

        if curso_campus:
            qs_aulas = qs_aulas.filter(professor_diario__diario__turma__curso_campus_id=curso_campus.id)
            qs_matriculas_periodo = qs_matriculas_periodo.filter(aluno__curso_campus_id=curso_campus.id)

        if uo:
            qs_aulas = qs_aulas.filter(professor_diario__diario__turma__curso_campus__diretoria__setor__uo_id=uo.id)
            qs_matriculas_periodo = qs_matriculas_periodo.filter(aluno__curso_campus__diretoria__setor__uo_id=uo.id)

        if diretoria:
            qs_aulas = qs_aulas.filter(professor_diario__diario__turma__curso_campus__diretoria_id=diretoria.id)
            qs_matriculas_periodo = qs_matriculas_periodo.filter(aluno__curso_campus__diretoria_id=diretoria.id)

        if ano_letivo:
            qs_aulas = qs_aulas.filter(professor_diario__diario__matriculadiario__matricula_periodo__ano_letivo_id=ano_letivo.id)
            qs_matriculas_periodo = qs_matriculas_periodo.filter(ano_letivo_id=ano_letivo.id)

        if periodo_letivo != '' and int(periodo_letivo):
            qs_aulas = qs_aulas.filter(professor_diario__diario__matriculadiario__matricula_periodo__periodo_letivo=periodo_letivo)
            qs_matriculas_periodo = qs_matriculas_periodo.filter(periodo_letivo=periodo_letivo)

        if situacao_periodo:
            qs_aulas = qs_aulas.filter(professor_diario__diario__matriculadiario__matricula_periodo__situacao__in=situacao_periodo)
            qs_matriculas_periodo = qs_matriculas_periodo.filter(situacao__in=situacao_periodo)

        if intervalo_inicio:
            qs_aulas = qs_aulas.filter(data__gte=intervalo_inicio)

        if intervalo_fim:
            qs_aulas = qs_aulas.filter(data__lte=intervalo_fim)

        if qs_aulas.exists():
            data_primeira_aula = qs_aulas.order_by('data')[0].data
            data_ultima_aula = qs_aulas.latest('data').data
            data_primeira_aula = data_primeira_aula.replace(day=1)
            data_ultima_aula = data_ultima_aula.replace(day=1)
            qtd_meses = relativedelta(data_ultima_aula, data_primeira_aula).months + 1

            lista1 = [
                [
                    (data_primeira_aula + relativedelta(months=n)).year,
                    (data_primeira_aula + relativedelta(months=n)).month,
                    meses[(data_primeira_aula + relativedelta(months=n)).month - 1],
                ]
                for n in range(qtd_meses)
            ]

            matriculas_periodos = []
            for matricula_periodo in qs_matriculas_periodo:
                faltas = []
                qs_aulas_mp = Aula.objects.filter(professor_diario__diario__matriculadiario__matricula_periodo__aluno_id=matricula_periodo.aluno.id)
                qs_faltas = Falta.objects.filter(matricula_diario__matricula_periodo_id=matricula_periodo.id)

                if intervalo_inicio:
                    qs_aulas_mp = qs_aulas_mp.filter(data__gte=intervalo_inicio)
                    qs_faltas = qs_faltas.filter(aula__data__gte=intervalo_inicio)

                if intervalo_fim:
                    qs_aulas_mp = qs_aulas_mp.filter(data__lte=intervalo_fim)
                    qs_faltas = qs_faltas.filter(aula__data__lte=intervalo_fim)

                if diario:
                    qs_aulas_mp = qs_aulas_mp.filter(professor_diario__diario_id=diario.id)
                    qs_faltas = qs_faltas.filter(matricula_diario__diario_id=diario.id)

                aulas_faltas_abonos = []
                aulas_total = 0
                faltas_total = 0
                abonos_total = 0
                for ano, mes, descricao in lista1:
                    aula, pks = matricula_periodo.get_qtd_aulas(qs_aulas_mp, mes, ano, situacoes_inativas) or 0
                    falta = aula and matricula_periodo.get_qtd_faltas(pks, qs_faltas) or 0
                    abono = falta and matricula_periodo.get_qtd_faltas(pks, qs_faltas, True) or 0
                    aulas_faltas_abonos.append({'aula': aula, 'falta': falta, 'abono': abono})
                    aulas_total += aula
                    faltas_total += falta
                    abonos_total += abono

                matricula_periodo.aulas_faltas_abonos = aulas_faltas_abonos
                matricula_periodo.aulas_total = aulas_total
                matricula_periodo.faltas_total = faltas_total
                matricula_periodo.abonos_total = abonos_total
                percentual_faltas = 0
                percentual_presenca = 0
                if matricula_periodo.aulas_total:
                    percentual_faltas = matricula_periodo.faltas_total * 100 / matricula_periodo.aulas_total
                    percentual_presenca = 100 - percentual_faltas

                matricula_periodo.percentual_faltas = '{number:.{digits}f}%'.format(number=percentual_faltas, digits=2)
                matricula_periodo.percentual_presenca = '{number:.{digits}f}%'.format(number=percentual_presenca, digits=2)
                matriculas_periodos.append(matricula_periodo)

            matriculas_periodos = sorted(matriculas_periodos, key=lambda x: x.percentual_presenca, reverse=True)

            if 'exportar' in request.GET:
                lista = []
                matriculas_periodos_ids = request.POST.getlist('select_aluno')
                if matriculas_periodos_ids:
                    ids = list(map(int, matriculas_periodos_ids))
                    for matricula_periodo in matriculas_periodos:
                        if matricula_periodo.id in ids:
                            lista.append(matricula_periodo)
                    matriculas_periodos = lista

                response = HttpResponse(content_type='application/ms-excel')
                response['Content-Disposition'] = 'attachment; filename=relatorio_de_faltas.xls'

                wb = xlwt.Workbook(encoding='utf-8')
                sheet1 = FitSheetWrapper(wb.add_sheet('Relatório de Faltas'))
                style = xlwt.easyxf(
                    'pattern: pattern solid, fore_colour gray25; borders: left thin, right thin, top thin, bottom thin; '
                    'font: colour black, bold True; align: wrap on, vert centre, horiz center;'
                )

                col = 0
                line = 0

                sheet1.write_merge(line, line + 1, col, col, 'Matrícula', style)
                col += 1
                sheet1.write_merge(line, line + 1, col, col, 'Aluno', style)
                col += 1

                if aluno:
                    sheet1.write_merge(line, line + 1, col, col, 'Período Letivo', style)
                    col += 1

                for ano, mes, descricao in lista1:
                    sheet1.write_merge(line, line, col, col + 2, f'{descricao}/{ano}', style)
                    sheet1.write_merge(line + 1, line + 1, col, col, 'Aulas', style)
                    col += 1
                    sheet1.write_merge(line + 1, line + 1, col, col, 'Faltas', style)
                    col += 1
                    sheet1.write_merge(line + 1, line + 1, col, col, 'Abonos', style)
                    col += 1

                sheet1.write_merge(line, line + 1, col, col, 'Total de Aulas', style)
                col += 1
                sheet1.write_merge(line, line + 1, col, col, 'Total de Faltas', style)
                col += 1
                sheet1.write_merge(line, line + 1, col, col, 'Percentual de Presença', style)
                col += 1
                sheet1.write_merge(line, line + 1, col, col, 'Percentual de Faltas', style)
                col += 1
                sheet1.write_merge(line, line + 1, col, col, 'Total de Justificativas', style)
                col += 1
                sheet1.write_merge(line, line + 1, col, col, 'Email do Aluno', style)
                col += 1
                sheet1.write_merge(line, line + 1, col, col, 'Telefone do Aluno', style)
                col += 1
                sheet1.write_merge(line, line + 1, col, col, 'Email do Responsável', style)
                col += 1
                sheet1.write_merge(line, line + 1, col, col, 'Telefone do Responsável', style)

                line = 1

                for matricula_periodo in matriculas_periodos:
                    line += 1
                    col = 0
                    sheet1.row(line).write(col, matricula_periodo.aluno.matricula)
                    col += 1
                    sheet1.row(line).write(col, matricula_periodo.aluno.pessoa_fisica.nome)
                    col += 1
                    if aluno:
                        sheet1.row(line).write(col, f'{matricula_periodo.ano_letivo.ano}/{matricula_periodo.periodo_letivo}')
                        col += 1
                    for n in matricula_periodo.aulas_faltas_abonos:
                        sheet1.row(line).write(col, n['aula'])
                        col += 1
                        sheet1.row(line).write(col, n['falta'])
                        col += 1
                        sheet1.row(line).write(col, n['abono'])
                        col += 1

                    sheet1.row(line).write(col, matricula_periodo.aulas_total)
                    col += 1
                    sheet1.row(line).write(col, matricula_periodo.faltas_total)
                    col += 1
                    sheet1.row(line).write(col, matricula_periodo.percentual_presenca)
                    col += 1
                    sheet1.row(line).write(col, matricula_periodo.percentual_faltas)
                    col += 1
                    sheet1.row(line).write(col, matricula_periodo.abonos_total)
                    col += 1
                    email_aluno = matricula_periodo.aluno.email_academico or matricula_periodo.aluno.pessoa_fisica.email or '-'
                    sheet1.row(line).write(col, email_aluno)
                    col += 1
                    sheet1.row(line).write(col, matricula_periodo.aluno.get_telefones() or '-')
                    col += 1
                    sheet1.row(line).write(col, matricula_periodo.aluno.email_responsavel or '-')
                    col += 1
                    sheet1.row(line).write(col, '-')

                wb.save(response)

                return response

            if 'notificar' in request.GET:
                for matricula_periodo in matriculas_periodos:
                    faltas_nao_justificadas = matricula_periodo.faltas_total - matricula_periodo.abonos_total
                    if matricula_periodo.aluno.email_responsavel and faltas_nao_justificadas > 0:
                        titulo = '[SUAP] Alerta de Frequência de Aluno'
                        texto = (
                            '<h1>Ensino</h1>'
                            '<h2>Alerta de Frequência de Aluno</h2>'
                            '<p>O aluno {} ({}) tem {:d} falta(s) não justificadas.</p>'.format(
                                matricula_periodo.aluno.pessoa_fisica.nome, matricula_periodo.aluno.matricula, faltas_nao_justificadas
                            )
                        )
                        email_destino = [matricula_periodo.aluno.email_responsavel]
                        send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, email_destino)
                return httprr(request.META.get('HTTP_REFERER') or '.', 'Notificação enviada com sucesso')
    return locals()


@permission_required('edu.view_cursocampus')
@rtr()
def cursocampus(request, pk):
    obj = get_object_or_404(CursoCampus, pk=pk)
    title = str(obj)
    is_avaliador_regulador = in_group(request.user, 'Diretor de Avaliação e Regulação do Ensino')
    pode_visualizar_estatistica = in_group(request.user, 'Secretário Acadêmico,Coordenador de Curso,Diretor Acadêmico,Administrador Acadêmico,Pedagogo')
    pode_definir_coordenador_estagio_docente = in_group(request.user, 'Secretário Acadêmico,Coordenador de Curso,Diretor Acadêmico,Administrador Acadêmico')
    tab = request.GET.get('tab', '')
    if tab == 'coordenacao':
        logs = (
            Log.objects.filter(modelo='CursoCampus', ref=pk, registrodiferenca__campo__in=['Coordenador', 'Vice-Coordenador'])
            .order_by('-pk')
            .values_list('dt', 'registrodiferenca__valor_anterior', 'registrodiferenca__valor_atual', 'registrodiferenca__campo')
        )
    return locals()


@permission_required('edu.add_matrizcurso')
@rtr()
def adicionar_matriz_curso(request, curso_campus_pk, matriz_curso_pk=None):
    title = 'Adicionar Matriz'
    curso_campus = get_object_or_404(CursoCampus.locals, pk=curso_campus_pk)
    if matriz_curso_pk:
        matriz_curso = curso_campus.matrizcurso_set.get(pk=matriz_curso_pk)
    form = MatrizCursoForm(data=request.POST or None, instance=matriz_curso_pk and matriz_curso or None)
    form.initial.update(dict(curso_campus=curso_campus.pk))
    if form.is_valid():
        form.save()
        return httprr('..', 'Matriz adicionada com sucesso.')
    return locals()


@permission_required('edu.view_horariocampus')
@rtr()
def horariocampus(request, pk):
    obj = get_object_or_404(HorarioCampus.locals, pk=pk)
    horarios_aula = HorarioAula.objects.filter(horario_campus=obj.pk)
    title = str(obj)
    return locals()


@permission_required('edu.add_horariocampus')
@rtr()
def replicar_horariocampus(request, pk):
    title = 'Replicação de Horário'
    horario_campus = get_object_or_404(HorarioCampus.locals, pk=pk)
    form = ReplicacaoHorarioCampusForm(data=request.POST or None)
    if request.POST and form.is_valid():
        try:
            resultado = form.processar(horario_campus)
            return httprr('..', mark_safe(f'Horário replicado com sucesso. <a href="/admin/edu/horariocampus/{resultado.pk}/">Você deseja editá-lo?</a>'))
        except ValidationError as e:
            return httprr('..', f'Não foi possível replicar o horário: {e.messages[0]}', 'error')
    return locals()


@permission_required('edu.view_componente')
@rtr()
def componente(request, pk):
    obj = get_object_or_404(Componente, pk=pk)
    title = obj.descricao_historico
    matrizes = Matriz.objects.filter(componentecurricular__componente=obj)
    return locals()


@permission_required('edu.add_tipocomponente')
@rtr()
def tipo_componente(request, pk):
    title = 'Tipo de Componente'
    obj = get_object_or_404(TipoComponente, pk=pk)
    componentes = obj.componente_set.all()
    return locals()


@permission_required('edu.view_diretoria')
@rtr()
def diretoria(request, pk):
    obj = get_object_or_404(Diretoria, pk=pk)

    title = f'{obj.get_tipo_display()} - {str(obj)}'
    dimensoes = []

    dimensao = dict(nome='Direção', grupos=[])
    if obj.is_diretoria_sistemica():
        for name, verbose_name in (('Reitor', 'Reitor'), ('Pró-Reitor', 'Pró-Reitores'), ('Diretor Acadêmico Sistêmico', 'Diretores Sistêmicos'), ('Diretor de Avaliação e Regulação do Ensino', 'Diretores de Avaliação e Regulação do Ensino')):
            grupo = Group.objects.get(name=name)
            dimensao['grupos'].append(dict(nome=verbose_name, membros=UsuarioGrupo.objects.filter(group=grupo, setores__id=obj.setor.pk), parametro=grupo.pk, group=grupo))
    else:
        for name, verbose_name in (('Diretor Geral', 'Diretor Geral'), ('Diretor Acadêmico', 'Diretor Acadêmico')):
            grupo = Group.objects.get(name=name)
            dimensao['grupos'].append(dict(nome=verbose_name, membros=UsuarioGrupo.objects.filter(group=grupo, setores__id=obj.setor.pk), parametro=grupo.pk, group=grupo))
    dimensoes.append(dimensao)

    dimensao = dict(nome='Coordenação Acadêmica', grupos=[])
    if obj.is_diretoria_sistemica():
        for name, verbose_name in (('Coordenador Acadêmico Sistêmico', 'Coordenadores Sistêmicos'),):
            grupo = Group.objects.get(name=name)
            dimensao['grupos'].append(dict(nome=verbose_name, membros=UsuarioGrupo.objects.filter(group=grupo, setores__id=obj.setor.pk), parametro=grupo.pk, group=grupo))
    else:
        for name, verbose_name in (('Coordenador de Curso', 'Coordenadores de Curso'),):
            grupo = Group.objects.get(name=name)
            dimensao['grupos'].append(dict(nome=verbose_name, membros=UsuarioGrupo.objects.filter(group=grupo, setores__id=obj.setor.pk), parametro=grupo.pk, group=grupo))
    dimensoes.append(dimensao)

    if not obj.is_diretoria_sistemica():
        dimensao = dict(nome='Secretaria Acadêmica', grupos=[])
        for name, verbose_name in (
            ('Secretário Acadêmico', 'Secretários Acadêmicos'),
            ('Auxiliar de Secretaria Acadêmica', 'Auxiliares de Secretaria Acadêmica'),
            ('Apoio Acadêmico', 'Apoio Acadêmico'),
            ('Estagiário', 'Estagiários'),
        ):
            grupo = Group.objects.get(name=name)
            dimensao['grupos'].append(dict(nome=verbose_name, membros=UsuarioGrupo.objects.filter(group=grupo, setores__id=obj.setor.pk), parametro=grupo.pk, group=grupo))
        dimensoes.append(dimensao)

        dimensao = dict(nome='Formatura/Diplomas', grupos=[])
        for name, verbose_name in (('Organizador de Formatura', 'Organizadores de Formatura'), ('Coordenador de Registros Acadêmicos', 'Responsáveis pela Emissão do Diploma')):
            grupo = Group.objects.get(name=name)
            dimensao['grupos'].append(dict(nome=verbose_name, membros=UsuarioGrupo.objects.filter(group=grupo, setores__id=obj.setor.pk), parametro=grupo.pk, group=grupo))
        dimensoes.append(dimensao)

        dimensao = dict(nome='Atividades Extensão', grupos=[])
        for name, verbose_name in (
            ('Coordenador de Estágio Docente', 'Coordenador de Estágio Docente'),
            ('Organizador de Minicurso', 'Organizador de Minicurso'),
        ):
            grupo = Group.objects.get(name=name)
            dimensao['grupos'].append(dict(nome=verbose_name, membros=UsuarioGrupo.objects.filter(group=grupo, setores__id=obj.setor.pk), parametro=grupo.pk, group=grupo))
        dimensoes.append(dimensao)

    dimensao = dict(nome='Outras Atividades', grupos=[])
    for name, verbose_name in (
        ('Pedagogo', 'Pedagogos'),
    ):
        grupo = Group.objects.get(name=name)
        dimensao['grupos'].append(dict(nome=verbose_name, membros=UsuarioGrupo.objects.filter(group=grupo, setores__id=obj.setor.pk), parametro=grupo.pk, group=grupo))
    if not obj.is_diretoria_sistemica():
        for name, verbose_name in (
            ('Bibliotecário', 'Bibliotecários'),
            ('Comissão de Horários', 'Comissão de Horários'),
            ('Coordenador de Desporto', 'Coordenadores de Atividades Desportivas'),
        ):
            grupo = Group.objects.get(name=name)
            dimensao['grupos'].append(dict(nome=verbose_name, membros=UsuarioGrupo.objects.filter(group=grupo, setores__id=obj.setor.pk), parametro=grupo.pk, group=grupo))
    if obj.is_diretoria_sistemica():
        for name, verbose_name in (
            ('Operador ENADE', 'Operadores ENADE'),
        ):
            grupo = Group.objects.get(name=name)
            dimensao['grupos'].append(dict(nome=verbose_name, membros=UsuarioGrupo.objects.filter(group=grupo, setores__id=obj.setor.pk), parametro=grupo.pk, group=grupo))
    dimensoes.append(dimensao)

    if request.user.has_perm('edu.delete_diretoria'):
        url = f'/edu/diretoria/{obj.pk}/'

        if 'diretor_geral_id' in request.GET:
            diretor = get_object_or_404(UsuarioGrupo, pk=request.GET['diretor_geral_id'])
            diretorias = Diretoria.objects.filter(setor__uo=obj.setor.uo)
            for diretoria in diretorias:
                diretoria.diretor_geral = diretor.user.get_profile().funcionario
                diretoria.diretor_geral_exercicio = diretor.user.get_profile().funcionario
                diretoria.save()
            return httprr(url, 'Diretor geral titular definido com sucesso.')
        if 'diretor_academico_id' in request.GET:
            o = get_object_or_404(UsuarioGrupo, pk=request.GET['diretor_academico_id'])
            obj.diretor_academico = o.user.get_profile().funcionario
            obj.diretor_academico_exercicio = obj.diretor_academico
            obj.save()
            return httprr(url, 'Diretor acadêmico titular definido com sucesso.')
    return locals()


@permission_required('edu.add_diretoria')
@rtr()
def adicionar_membro_diretoria(request, pk, grupo_pk):
    diretoria = get_object_or_404(Diretoria, pk=pk)
    grupo = Group.objects.get(pk=grupo_pk)
    if grupo.name == 'Diretor Acadêmico' and diretoria.is_diretoria_ensino():
        nome = 'Diretor de Ensino'
    else:
        nome = grupo.name
    title = f'Adicionar {nome}'
    form = AdicionarMembroDiretoriaForm(request.POST or None)
    if form.is_valid():
        form.processar(diretoria, grupo)
        return httprr('..', 'Usuário adicionado com sucesso.')
    return locals()


@permission_required('edu.add_diretoria')
@rtr()
def adicionar_coordenador(request, pk, usuario_grupo_id=None):
    title = 'Adicionar Coordenador'
    diretoria = get_object_or_404(Diretoria, pk=pk)
    initial = None
    usuario_grupo = None
    if usuario_grupo_id:
        usuario_grupo = get_object_or_404(UsuarioGrupo, pk=usuario_grupo_id)
        user = usuario_grupo.user
    form = AdicionarCoordenadorForm(request.POST or None, diretoria=diretoria, tipo_coordenador=request.GET.get('tipo'), user=user)
    if form.is_valid():
        form.processar(diretoria, usuario_grupo)
        return httprr('..', 'Coordenação alterada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.efetuar_matricula')
def definir_coordenador_curso(request, pk):
    title = 'Definir Coordenador'
    curso_campus = get_object_or_404(CursoCampus, pk=pk)
    form = DefinirCoordenadorCursoForm(request.POST or None, instance=curso_campus)
    if form.is_valid():
        form.processar(curso_campus)
        return httprr('..', 'Coordenador definido com sucesso.')
    return locals()


@permission_required('edu.view_diario')
@rtr()
def diario(request, pk, polo_pk=None):
    NOTA_DECIMAL = settings.NOTA_DECIMAL
    CASA_DECIMAL = settings.CASA_DECIMAL
    MULTIPLICADOR_DECIMAL = NOTA_DECIMAL and CASA_DECIMAL == 1 and 10 or 100
    MATRICULADO = SituacaoMatriculaPeriodo.MATRICULADO
    manager = in_group(request.user, 'Diretor Acadêmico') and Diario.objects or Diario.locals
    obj = get_object_or_404(manager, pk=pk)
    qtd_avaliacoes = obj.componente_curricular.qtd_avaliacoes

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, obj.turma.curso_campus)
    acesso_total = pode_realizar_procedimentos

    title = f'Diário ({obj.pk}) - {obj.componente_curricular.componente.sigla}'
    pode_manipular_etapa_1 = obj.em_posse_do_registro(1) and acesso_total
    pode_manipular_etapa_2 = obj.em_posse_do_registro(2) and acesso_total
    pode_manipular_etapa_3 = obj.em_posse_do_registro(3) and acesso_total
    pode_manipular_etapa_4 = obj.em_posse_do_registro(4) and acesso_total
    pode_manipular_etapa_5 = obj.em_posse_do_registro(5) and acesso_total
    etapa = 5
    materiais_diario = MaterialDiario.objects.filter(professor_diario__diario=obj).order_by('-data_vinculacao', 'material_aula__descricao')
    quantidade_vagas_estourada = obj.matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO).count() > obj.quantidade_vagas

    polos = obj.get_polos()
    if polo_pk is None:
        polo_pk = polos and polos.first().pk or None
    else:
        polo_pk = int(polo_pk)
    matriculas_diario_por_polo = obj.get_matriculas_diario_por_polo(polo_pk)

    if 'moodle' in request.GET and obj.integracao_com_moodle:
        try:
            url = moodle.sincronizar(obj)
            obj.url_moodle = url
            obj.save()
            return httprr('.', f'Dados enviados com sucesso! A URL de acesso para o ambiente virtual é: {url}')
        except BaseException as e:
            return httprr('.', f'Problemas ao enviar os dados para o Moodle: {e}', tag='error')

    if 'abrir' in request.GET:
        obj.situacao = Diario.SITUACAO_ABERTO
        obj.save()
        return httprr('.', 'Diário aberto com sucesso.')

    if 'fechar' in request.GET:
        obj.situacao = Diario.SITUACAO_FECHADO
        obj.save()
        return httprr('.', 'Diário fechado com sucesso.')

    if request.GET.get('xls'):
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = f'attachment; filename=diario_{pk}.xls'

        wb = xlwt.Workbook(encoding='utf-8')
        sheet1 = wb.add_sheet('Dados Gerais')
        sheet2 = wb.add_sheet('Registros de Aulas')

        rows_agrupada = []
        cabecalho = ['#', 'Matrícula', 'Nome', 'T. Faltas', '%Freq', 'Situação']
        for avaliacao in range(1, obj.componente_curricular.qtd_avaliacoes + 1):
            cabecalho.append(f'Nota Etapa {avaliacao}')
            cabecalho.append(f'Falta Etapa {avaliacao}')
        cabecalho += ['MD', 'Nota Etapa Final', 'MFD/Conceito']
        rows_agrupada.append(cabecalho)
        count = 0

        for matricula_diario in obj.matriculadiario_set.all():
            count += 1
            row = [
                format_(count),
                format_(matricula_diario.matricula_periodo.aluno.matricula),
                format_(normalizar_nome_proprio(matricula_diario.matricula_periodo.aluno.get_nome_social_composto())),
                format_(matricula_diario.get_numero_faltas()),
                format_(matricula_diario.get_percentual_carga_horaria_frequentada()),
                format_(matricula_diario.get_situacao_diario()['rotulo']),
            ]
            if matricula_diario.diario.componente_curricular.qtd_avaliacoes > 0:
                row.append(format_(matricula_diario.get_nota_1_boletim()))
                row.append(format_(matricula_diario.get_numero_faltas_primeira_etapa()))
            if matricula_diario.diario.componente_curricular.qtd_avaliacoes > 1:
                row.append(format_(matricula_diario.get_nota_2_boletim()))
                row.append(format_(matricula_diario.get_numero_faltas_segunda_etapa()))
            if matricula_diario.diario.componente_curricular.qtd_avaliacoes > 2:
                row.append(format_(matricula_diario.get_nota_3_boletim()))
                row.append(format_(matricula_diario.get_numero_faltas_terceira_etapa()))
                row.append(format_(matricula_diario.get_nota_4_boletim()))
                row.append(format_(matricula_diario.get_numero_faltas_quarta_etapa()))
            if matricula_diario.diario.componente_curricular.qtd_avaliacoes > 0:
                row.append(format_(matricula_diario.get_media_disciplina_boletim()))
                row.append(format_(matricula_diario.get_nota_final_boletim()))
                row.append(format_(matricula_diario.get_media_final_disciplina_boletim()))
            rows_agrupada.append(row)

        for row_idx, row in enumerate(rows_agrupada):
            row = [i for i in row]
            for col_idx, col in enumerate(row):
                sheet1.write(row_idx, col_idx, label=col)

        rows_agrupada = [['#', 'Etapa', 'Qtd.', 'Data', 'Professor', 'Conteúdo']]
        count = 0

        for aula in obj.get_aulas():
            count += 1
            row = [format_(count), format_(aula.etapa), format_(aula.quantidade), format_(aula.data), format_(str(aula.professor_diario.professor)), format_(aula.conteudo)]
            rows_agrupada.append(row)

        for row_idx, row in enumerate(rows_agrupada):
            row = [i for i in row]
            for col_idx, col in enumerate(row):
                sheet2.write(row_idx, col_idx, label=col)

        wb.save(response)
        return response

    if request.method == 'POST' and request.user.has_perm('edu.add_professordiario'):
        if 'lancamento_nota' in request.POST:
            if running_tests():
                try:
                    obj.processar_notas(request.POST)
                    return httprr('.', 'Notas registradas com sucesso.')
                except Exception as e:
                    return httprr('..', str(e), 'error', anchor='etapa')

    if not obj.turma.curso_campus.diretoria.ead:
        horarios_com_choque = obj.get_horarios_com_choque()

    tab = request.GET.get('tab', '')

    if tab == 'estatisticas':
        estatisticas = get_estatisticas_diario(obj)

    exibir_todos_alunos = not obj.matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO).exists()
    return locals()


@permission_required('edu.change_diario')
@rtr()
def replicar_diario(request, pk):
    diario = get_object_or_404(Diario.locals, pk=pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, diario.turma.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    novo_diario = diario.replicar()

    return httprr(novo_diario.get_absolute_url(), 'Diário replicado com sucesso.')


@permission_required('edu.change_diario')
@rtr()
def dividir_diario(request, pk):
    diario = get_object_or_404(Diario.locals, pk=pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, diario.turma.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    novo_diario = diario.dividir()

    return httprr('..', mark_safe(f'Diário dividido com sucesso. Código do novo diário: <a href="{novo_diario.get_absolute_url()}">{novo_diario.pk}</a>.'))


@permission_required('edu.change_diario')
@rtr()
def dividir_diario_individualizado(request, pk):
    diario = get_object_or_404(Diario.locals, pk=pk)
    title = f'Dividir diário - {diario}'

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, diario.turma.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    ids = NotaAvaliacao.objects.filter(
        matricula_diario__diario=diario, nota__isnull=False
    ).values_list('matricula_diario', flat=True).order_by('matricula_diario').distinct()
    qs = diario.matriculadiario_set.exclude(id__in=ids)
    form = DividirDiarioForm(qs, request.POST or None)
    if form.is_valid():
        novo_diario = diario.dividir(matriculas_diario=form.cleaned_data['matriculas_diario'])
        return httprr('..', mark_safe(f'Diário dividido com sucesso. Código do novo diário: <a href="{novo_diario.get_absolute_url()}">{novo_diario.pk}</a>.'))
    return locals()


@permission_required('edu.change_diario')
@rtr()
def dividir_diario_reprovados_dependentes(request, pk):
    diario = get_object_or_404(Diario.locals, pk=pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, diario.turma.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    novo_diario = diario.dividir_reprovados_dependentes()

    return httprr('..', mark_safe(f'Diário dividido com sucesso. Código do novo diário: <a href="{novo_diario.get_absolute_url()}">{novo_diario.pk}</a>.'))


@permission_required('edu.add_professordiario')
@rtr()
def definir_local_aula_diario(request, diario_pk):
    title = 'Definir Local de Aula'
    diario = get_object_or_404(Diario.locals, pk=diario_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, diario.turma.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = DefinirLocalAulaForm(diario, data=request.POST or None)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Local definido com sucesso.')
    return locals()


@permission_required('edu.change_turma')
@rtr()
def definir_local_aula_turma(request, turma_pk):
    title = 'Definir Local de Aula dos Diários'
    turma = get_object_or_404(Turma.locals, pk=turma_pk)
    form = DefinirLocalAulaTurmaForm(turma, data=request.POST or None)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Local de aula dos diários definido com sucesso.')
    return locals()


@permission_required('edu.change_diario')
@rtr()
def transferir_posse_diario(request, diario_pk, etapa, destino):
    diario = get_object_or_404(Diario.locals, pk=diario_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, diario.turma.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    destino = int(destino)
    etapa = int(etapa)
    if etapa == 1:
        diario.posse_etapa_1 = destino
    elif etapa == 2:
        diario.posse_etapa_2 = destino
    elif etapa == 3:
        diario.posse_etapa_3 = destino
    elif etapa == 4:
        diario.posse_etapa_4 = destino
    elif etapa == 5:
        diario.posse_etapa_5 = destino
    diario.save()
    for matricula_diario in diario.matriculadiario_set.all():
        matricula_diario.registrar_nota_etapa(etapa)
    return httprr(f'/edu/diario/{diario.pk:d}', 'Posse transferida com sucesso.')


@rtr()
def rejeitar_solicitacao(request, pks):
    title = 'Rejeitar Solicitação'
    solicitacoes = SolicitacaoUsuario.objects.filter(pk__in=pks.split('_'))
    for solicitacao in solicitacoes:
        filho_verbose_name = solicitacao.sub_instance_title()
        filho = solicitacao.sub_instance()
        solicitacao = get_object_or_404(filho.__class__.locals, pk=solicitacao.pk)

        eh_acompanhamento_etep = filho_verbose_name == 'Solicitação de Acompanhamento ETEP'
        tem_permissao_realizar_procedimentos_etep = False
        if eh_acompanhamento_etep:
            if not etep_perms.tem_permissao_realizar_procedimentos_etep(request, filho.aluno):
                return httprr('..', f'Você não tem permissão para realizar isso com a solicitação #{solicitacao.pk}.', 'error')
        else:
            if not request.user.has_perm('edu.view_solicitacaorelancamentoetapa'):
                return httprr('..', f'Você não tem permissão para realizar isso com a solicitação #{solicitacao.pk}.', 'error')

    form = RejeitarSolicitacaoUsuarioForm(data=request.POST or None)

    if form.is_valid():
        for solicitacao in solicitacoes:
            solicitacao.rejeitar(request.user, request.POST['razao_indeferimento'])
        return httprr('..', 'Solicitações indeferidas com sucesso.')

    return locals()


@rtr()
@permission_required('edu.change_solicitacaoprorrogacaoetapa')
def atender_prorrogacao_etapa(request, pks):
    title = 'Atender Solicitação'
    form = AtenderSolicitacaoProrrogacaoEtapaForm(data=request.POST or None)
    if form.is_valid():
        solicitacoes = SolicitacaoProrrogacaoEtapa.objects.filter(pk__in=pks.split('_'))
        for solicitacao in solicitacoes:
            solicitacao.atender(request.user, nova_data=form.cleaned_data['data_prorrogacao'])
        return httprr('..', 'Solicitações deferidas com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_solicitacaoprorrogacaoetapa')
def atender_relancamento_etapa_prorrogando_posse(request, pks):
    title = 'Atender Solicitação'
    form = AtenderSolicitacaoProrrogacaoEtapaForm(data=request.POST or None)
    if form.is_valid():
        solicitacoes = SolicitacaoRelancamentoEtapa.objects.filter(pk__in=pks.split('_'))
        for solicitacao in solicitacoes:
            solicitacao.atender(request.user, nova_data=form.cleaned_data['data_prorrogacao'])
        return httprr('..', 'Solicitações deferidas com sucesso.')
    return locals()


@permission_required('edu.emitir_boletins')
@documento()
@rtr('relacao_alunos_pdf.html')
def relacao_alunos_pdf(request, diario_pk):
    diario = get_object_or_404(Diario.locals, pk=diario_pk)
    situacoes_inativas = [MatriculaDiario.SITUACAO_TRANCADO, MatriculaDiario.SITUACAO_TRANSFERIDO, MatriculaDiario.SITUACAO_CANCELADO]
    matriculas_diario = diario.matriculadiario_set.exclude(situacao__in=situacoes_inativas)
    if not running_tests():
        matriculas_diario = matriculas_diario.order_by('matricula_periodo__aluno__pessoa_fisica__nome')
    uo = diario.turma.curso_campus.diretoria.setor.uo
    hoje = datetime.date.today()
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()
    return locals()


def cadastrar_pre_requisito_ajax(request, componente_curricular_pk, pre_requisito_pk):
    componente_curricular = get_object_or_404(ComponenteCurricular, pk=componente_curricular_pk)
    pre_requisito = get_object_or_404(ComponenteCurricular, pk=pre_requisito_pk)
    componente_curricular.pre_requisitos.add(pre_requisito)
    return HttpResponse('OK')


def remover_pre_requisito_ajax(request, componente_curricular_pk, pre_requisito_pk):
    componente_curricular = get_object_or_404(ComponenteCurricular, pk=componente_curricular_pk)
    pre_requisito = get_object_or_404(ComponenteCurricular, pk=pre_requisito_pk)
    componente_curricular.pre_requisitos.remove(pre_requisito)
    return HttpResponse('OK')


@transaction.atomic
@login_required()
def registrar_chamada_ajax(request, matricula_diario_pk, aula_pk, quantidade):
    aula = get_object_or_404(Aula, pk=aula_pk)
    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aula.professor_diario.diario.turma.curso_campus)
    if not pode_realizar_procedimentos and not aula.pode_registrar_chamada(request.user):
        return HttpResponse('Você não tem permissão para realizar isso.')
    if not quantidade:
        qs_falta = Falta.objects.filter(matricula_diario__id=matricula_diario_pk).filter(aula=aula).order_by('-id')
        qs_falta.delete()
    else:
        qs_matricula_diario = aula.professor_diario.diario.matriculadiario_set.filter(pk=matricula_diario_pk)
        if qs_matricula_diario.exists():
            matricula_diario = qs_matricula_diario[0]
        else:
            return HttpResponse('Este aluno não existe mais neste diário, por favor recarregue a página.')
        abono_faltas = matricula_diario.matricula_periodo.aluno.abonofaltas_set.filter(data_inicio__lte=aula.data, data_fim__gte=aula.data).first()
        falta = Falta.objects.filter(matricula_diario=matricula_diario, aula=aula).first()
        if falta is None:
            falta = Falta()
            falta.aula = aula
            falta.matricula_diario = matricula_diario
        falta.quantidade = quantidade
        falta.abono_faltas = abono_faltas
        falta.save()

    return HttpResponse('OK')


@transaction.atomic
@permission_required('edu.view_diario')
@rtr()
def registrar_chamada(request, diario_pk, etapa=0, matricula_diario_pk=0):
    diario = get_object_or_404(Diario.locals, pk=diario_pk)
    title = 'Registro de Frequência'

    is_proprio_professor = diario.professordiario_set.filter(professor__vinculo__user=request.user)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, diario.turma.curso_campus)
    if not pode_realizar_procedimentos and not is_proprio_professor and not in_group(request.user, 'Pedagogo, Apoio Acadêmico, Membro ETEP'):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not diario.professordiario_set.exists():
        return httprr(f'/edu/diario/{diario.pk}/', 'Não é possível registrar as aulas pois o professor do diário ainda não foi definido.', 'error')

    uo = get_uo()
    if is_proprio_professor or uo == diario.horario_campus.uo:
        acesso_total = True
    else:
        acesso_total = request.user.groups.filter(name='Administrador Acadêmico').exists()
    data_atual = datetime.date.today()
    aulas = diario.get_aulas().all()
    etapa = int(etapa)
    if not etapa or etapa == 1:
        aulas = diario.get_aulas_etapa_1().all()
    elif etapa == 2:
        aulas = diario.get_aulas_etapa_2().all()
    elif etapa == 3:
        aulas = diario.get_aulas_etapa_3().all()
    elif etapa == 4:
        aulas = diario.get_aulas_etapa_4().all()
    elif etapa == 5:
        aulas = diario.get_aulas_etapa_5().all()

    pode_manipular_etapa = diario.em_posse_do_registro(etapa) or is_proprio_professor

    form = AulaForm(diario, etapa, request=request)
    if request.POST:
        return httprr('..', 'Faltas registradas com sucesso.')

    polos = diario.get_polos()
    boxes_matriculas = []
    for matriculas in diario.get_matriculas_diario_por_polo():
        if matricula_diario_pk:
            matriculas = matriculas.filter(id=matricula_diario_pk)
        for matricula_diario in matriculas:
            matricula_diario.set_faltas(aulas)
        boxes_matriculas.append(matriculas)

    return locals()


@permission_required('edu.add_professordiario')
@rtr()
def definir_horario_aula_diario(request, diario_pk):
    obj = get_object_or_404(Diario.locals, pk=diario_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, obj.turma.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    campus_definiu_horario = HorarioAula.objects.filter(horario_campus__uo=obj.turma.curso_campus.diretoria.setor.uo).exists()

    horario_aula = obj.get_horario_aulas() or ''
    if horario_aula:
        horario_aula = f'({horario_aula})'

    title = f'Definir Horário de Aula {horario_aula}'

    if request.method == 'POST':
        qs_pedidos_matricula_nao_processados = PedidoMatriculaDiario.objects.filter(diario=obj, data_processamento__isnull=True)
        if not in_group(request.user, 'Administrador Acadêmico') and qs_pedidos_matricula_nao_processados.exists():
            return httprr('..', 'Não é possível alterar o horário do diário, pois existem pedidos de matrícula ainda não processados.', 'error')
        else:
            HorarioAulaDiario.objects.filter(diario=obj).delete()
            horarios = dict(request.POST).get("horario")
            if horarios:
                for horario in horarios:
                    horario_split = horario.split(";")
                    horario_aula = get_object_or_404(HorarioAula, pk=horario_split[0])
                    dia_semana = horario_split[1]
                    HorarioAulaDiario.objects.create(diario=obj, dia_semana=dia_semana, horario_aula=horario_aula)
            horarios_com_choque = obj.get_horarios_com_choque(verificar_apenas_existencia=True)
            if horarios_com_choque:
                return httprr('..', 'Horário definido com sucesso, porém existem alunos deste diário com conflitos de horário com outro(s) diário(s).', 'error')
            else:
                return httprr('..', 'Horário definido com sucesso.')

    turnos = obj.get_horarios_aula_por_turno()
    turnos.as_form = True

    return locals()


@permission_required('edu.add_professordiario')
@rtr()
def cadastrar_professor_nao_servidor(request):
    title = 'Adicionar Professor Prestador de Serviço'
    form = ProfessorExternoForm(data=request.POST or None)
    if form.is_valid():
        form.save()
        return httprr('..', 'Professor cadastrado com sucesso.')
    return locals()


@permission_required('edu.add_professordiario')
@rtr()
def adicionar_professor_diario(request, diario_pk, professordiario_pk=None):
    title = 'Adicionar Professor'
    diario = get_object_or_404(Diario.locals, pk=diario_pk)
    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, diario.turma.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    professor_diario = None
    if professordiario_pk:
        professor_diario = get_object_or_404(ProfessorDiario, pk=professordiario_pk)
    form = ProfessorDiarioForm(diario, data=request.POST or None, instance=professordiario_pk and professor_diario or None, request=request)
    if form.is_valid():
        form.save()
        if professor_diario:
            emails = [professor_diario.professor.vinculo.pessoa.email]
            mensagem = """
            Caro(a) Professor(a),

            Informamos que houve uma alteração do seu vínculo no diário {} que pode afetar o seu Plano/Relatório Individual de Trabalho de {}.{}.
            """.format(
                diario, diario.ano_letivo.ano, diario.periodo_letivo
            )

            send_mail(
                f'[SUAP] Alteração de Vínculo - Diário {diario}',
                mensagem,
                settings.DEFAULT_FROM_EMAIL,
                emails,
                fail_silently=True
            )
        return httprr('..', 'Professor adicionado/atualizado com sucesso.')
    return locals()


@login_required()
@rtr()
def visualizar(request, app, modelo, pk):
    if not request.user.has_perm(f'{app}.view_{modelo}'):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    classe = apps.get_model(app, modelo)
    objeto = get_object_or_404(classe, pk=pk)
    metadata = utils.metadata(objeto)
    title = objeto
    return locals()


@permission_required('edu.lancar_nota_diario')
@rtr()
def alterar_nota_diario(request, matriculadiario_pk, etapa=0):
    title = 'Alterar Nota'
    matricula_diario = get_object_or_404(MatriculaDiario.locals, id=matriculadiario_pk)
    etapa = int(etapa)
    if etapa == 1:
        nota = matricula_diario.nota_1
    elif etapa == 2:
        nota = matricula_diario.nota_2
    elif etapa == 3:
        nota = matricula_diario.nota_3
    elif etapa == 4:
        nota = matricula_diario.nota_4
    else:
        nota = matricula_diario.nota_final
    form = AlterarNotaForm(data=request.POST or None, initial=dict(nota=nota))
    if form.is_valid():
        nota = form.cleaned_data['nota']
        if etapa == 1:
            matricula_diario.nota_1 = nota
        elif etapa == 2:
            matricula_diario.nota_2 = nota
        elif etapa == 3:
            matricula_diario.nota_3 = nota
        elif etapa == 4:
            matricula_diario.nota_4 = nota
        else:
            matricula_diario.nota_final = nota
        matricula_diario.save()
        return httprr('..', 'Nota alterada com sucesso')
    return locals()


@permission_required('edu.add_aula')
@rtr()
def adicionar_aula_diario(request, etapa, diario_pk, aula_pk=None):
    title = 'Adicionar Aula'
    diario = get_object_or_404(Diario.locals, pk=diario_pk)
    if aula_pk:
        aula = get_object_or_404(Aula, pk=aula_pk)

    form = AulaForm(diario, etapa, data=request.POST or None, instance=aula_pk and aula or None, request=request)
    qtd_etapas = diario.componente_curricular.qtd_avaliacoes

    if form.is_valid():
        obj = form.save(False)
        obj.save()
        outros_professor_diario = form.cleaned_data.get('outros_professor_diario')
        if outros_professor_diario:
            obj.outros_professor_diario.set(outros_professor_diario)
        return httprr('..', 'Aula cadastrada/atualizada com sucesso.', anchor='etapa')
    return locals()


@rtr()
@permission_required('edu.efetuar_matricula')
def identificar_candidato(request, origem=None):
    title = 'Identificação do Candidato'
    form = IdentificacaoCandidatoForm(request.GET or None, request=request)
    if form.is_valid():
        candidato_vaga = form.processar()
        return httprr(f'/edu/efetuar_matricula/{candidato_vaga.pk}/', 'Candidato identificado com sucesso. Realize sua matrícula institucional.')

    return locals()


@rtr()
@login_required()
def efetuar_matricula(request, candidato_vaga_id=None):
    title = 'Matrícula Institucional'
    candidato_vaga = None
    initial = None
    alunos = Aluno.objects.none()

    cpf = request.POST.get('cpf')
    ignorar_sgc = request.GET.get('ignorar_sgc') or request.method == 'post'
    is_usuario_coordenador_do_polo = False

    if candidato_vaga_id:
        candidato_vaga = get_object_or_404(CandidatoVaga, pk=candidato_vaga_id)
        cpf = candidato_vaga.candidato.cpf
        if candidato_vaga:
            initial = dict(cpf=cpf, nome=candidato_vaga.candidato.nome, email_pessoal=candidato_vaga.candidato.email, telefone_principal=candidato_vaga.candidato.telefone)

        if request.user.groups.filter(name='Coordenador de Polo EAD').exists():
            polos = CoordenadorPolo.objects.filter(funcionario=request.user.get_profile()).values_list('polo__descricao', flat=True)
            is_usuario_coordenador_do_polo = candidato_vaga.candidato.campus_polo in polos

    if not request.user.has_perm('edu.efetuar_matricula') and not is_usuario_coordenador_do_polo:
        return HttpResponseForbidden()

    if cpf:
        alunos = Aluno.objects.filter(pessoa_fisica__cpf=cpf).exclude(matriz__estrutura__proitec=True)
        if alunos.exists():
            aluno = alunos.latest('id')
            initial = dict(
                # dados pessoais
                nome=aluno.pessoa_fisica.nome_registro,
                nome_social=aluno.pessoa_fisica.nome_social,
                sexo=aluno.pessoa_fisica.sexo,
                data_nascimento=aluno.pessoa_fisica.nascimento_data,
                estado_civil=aluno.pessoa_fisica.estado_civil,
                # dados familiares
                nome_pai=aluno.nome_pai,
                estado_civil_pai=aluno.estado_civil_pai,
                # pai_falecido = aluno.pai_falecido,
                nome_mae=aluno.nome_mae,
                estado_civil_mae=aluno.estado_civil_mae,
                # mae_falecida = aluno.mae_falecida,
                responsavel=aluno.responsavel,
                parentesco_responsavel=aluno.parentesco_responsavel,
                cpf_responsavel=aluno.cpf_responsavel,
                # endereço
                logradouro=aluno.logradouro,
                numero=aluno.numero,
                complemento=aluno.complemento,
                bairro=aluno.bairro,
                cep=aluno.cep,
                cidade=aluno.cidade,
                tipo_zona_residencial=aluno.tipo_zona_residencial,
                # informações para contado
                telefone_principal=aluno.telefone_principal,
                telefone_secundario=aluno.telefone_secundario,
                telefone_adicional_1=aluno.telefone_adicional_1,
                telefone_adicional_2=aluno.telefone_adicional_2,
                email_pessoal=aluno.pessoa_fisica.email_secundario,
                # outras informacoes
                tipo_sanguineo=aluno.tipo_sanguineo,
                nacionalidade=aluno.nacionalidade,
                pais_origem=aluno.pais_origem and aluno.pais_origem.id or None,
                naturalidade=aluno.naturalidade and aluno.naturalidade.id or None,
                raca=aluno.pessoa_fisica.raca,
                # dados escolares
                nivel_ensino_anterior=aluno.nivel_ensino_anterior and aluno.nivel_ensino_anterior.id or None,
                tipo_instituicao_origem=aluno.tipo_instituicao_origem,
                nome_instituicao_anterior=aluno.nome_instituicao_anterior,
                ano_conclusao_estudo_anterior=aluno.ano_conclusao_estudo_anterior and aluno.ano_conclusao_estudo_anterior.id or None,
                # rg
                numero_rg=aluno.numero_rg,
                uf_emissao_rg=aluno.uf_emissao_rg and aluno.uf_emissao_rg.id or None,
                orgao_emissao_rg=aluno.orgao_emissao_rg and aluno.orgao_emissao_rg.id or None,
                data_emissao_rg=aluno.data_emissao_rg,
                # titulo_eleitor
                numero_titulo_eleitor=aluno.numero_titulo_eleitor,
                zona_titulo_eleitor=aluno.zona_titulo_eleitor,
                secao=aluno.secao,
                data_emissao_titulo_eleitor=aluno.data_emissao_titulo_eleitor,
                uf_emissao_titulo_eleitor=aluno.uf_emissao_titulo_eleitor and aluno.uf_emissao_titulo_eleitor.id or None,
                # carteira de reservista
                numero_carteira_reservista=aluno.numero_carteira_reservista,
                regiao_carteira_reservista=aluno.regiao_carteira_reservista,
                serie_carteira_reservista=aluno.serie_carteira_reservista,
                estado_emissao_carteira_reservista=aluno.estado_emissao_carteira_reservista and aluno.estado_emissao_carteira_reservista.id or None,
                ano_carteira_reservista=aluno.ano_carteira_reservista,
                # certidao_civil
                tipo_certidao=aluno.tipo_certidao,
                cartorio=aluno.cartorio,
                numero_certidao=aluno.numero_certidao,
                folha_certidao=aluno.folha_certidao,
                livro_certidao=aluno.livro_certidao,
                data_emissao_certidao=aluno.data_emissao_certidao,
                matricula_certidao=aluno.matricula_certidao,
            )
        elif candidato_vaga and not ignorar_sgc:
            candidato = candidato_vaga.candidato
            webservice = candidato_vaga.oferta_vaga.oferta_vaga_curso.edital.webservice
            erro_acesso_sgc = False
            if webservice:
                try:
                    xml = webservice.candidato(candidato.edital.codigo, candidato.inscricao)
                except BaseException:
                    erro_acesso_sgc = True
                    if not request.POST.get('nome'):
                        alerta = 'Problemas ao tentar conectar com o Sistema de Gerenciamento de Concursos (SGC). Nenhum dado foi importado.'
                    else:
                        alerta = None
                if not erro_acesso_sgc:
                    # TODO Estudar a possibilidade de utilizar uma função de escape
                    doc = minidom.parseString(xml.replace('&', ' e '))

                    def getText(tag, normalizar=True):
                        dados_pessoais = doc.getElementsByTagName('dados_pessoais')
                        if dados_pessoais:
                            if dados_pessoais[0].getElementsByTagName(tag):
                                nodelist = dados_pessoais[0].getElementsByTagName(tag)[0].childNodes
                                rc = []
                                for node in nodelist:
                                    if node.nodeType == node.TEXT_NODE:
                                        rc.append(node.data)
                                return normalizar and normalizar_nome_proprio(''.join(rc)) or ''.join(rc)
                        return None

                    nascimento_municipio = getText('nascimento_municipio')
                    nascimento_uf = Estado.get_estado_por_sigla(getText('nascimento_uf'))

                    qs_naturalidade = Cidade.objects.filter(nome__unaccent__icontains=nascimento_municipio, estado=nascimento_uf)

                    naturalidade = None
                    if qs_naturalidade:
                        naturalidade = qs_naturalidade[0]

                    endereco_estado_obj = Estado.get_estado_por_sigla(getText('endereco_uf'))
                    qs = Cidade.objects.filter(nome__unaccent__icontains=getText('endereco_municipio'), estado=endereco_estado_obj)

                    if qs:
                        cidade = qs[0]
                    else:
                        cidade = ''

                    qs = OrgaoEmissorRg.objects.filter(nome__unaccent__icontains=getText('rg_orgao'))
                    if qs:
                        orgao = qs[0].id
                    else:
                        orgao = ''
                    qs = Estado.get_estado_por_sigla(getText('rg_uf'))
                    if qs:
                        uf_emissao_rg_id = qs.id
                    else:
                        uf_emissao_rg_id = ''
                    try:
                        daga_emissao_rg = datetime.datetime.strptime(getText('rg_data_emissao') or '', '%Y-%m-%d').strftime('%d/%m/%Y')
                    except ValueError:
                        daga_emissao_rg = ''
                    try:
                        nascimento_data = datetime.datetime.strptime(getText('nascimento_data') or '', '%Y-%m-%d').strftime('%d/%m/%Y')
                    except ValueError:
                        nascimento_data = ''

                    nome_mae = getText('mae_nome')
                    nome_pai = getText('pai_nome')
                    nome_responsavel = ''
                    parentesco_responsavel = ''

                    if nome_mae or nome_pai:
                        '''
                        Presume nome do responsável a partir do nome da mãe
                        ou do a pai informado
                        '''
                        nome_responsavel = nome_mae or nome_pai
                        parentesco_responsavel = 'Pai/Mãe'

                    initial = dict(
                        nome=getText('nome'),
                        sexo=getText('sexo') or 'M',
                        estado_civil=getText('estado_civil') or 'Solteiro',
                        tipo_sanguineo=getText('tipo_sanguineo'),
                        raca=Raca.objects.filter(descricao=getText('etnia')).values_list('pk', flat=True).first(),
                        data_nascimento=nascimento_data,
                        nome_mae=nome_mae,
                        nome_pai=nome_pai,
                        responsavel=nome_responsavel,
                        parentesco_responsavel=parentesco_responsavel,
                        logradouro=getText('endereco_logradouro'),
                        numero=getText('endereco_numero'),
                        complemento=getText('endereco_complemento'),
                        bairro=getText('endereco_bairro'),
                        cidade=cidade,
                        estado=endereco_estado_obj.pk,  # endereco_uf,
                        cep=getText('endereco_cep'),
                        telefone_principal=getText('telefone_residencial'),
                        telefone_secundario=getText('telefone_celular'),
                        email_pessoal=getText('email', False),
                        numero_rg=getText('rg_numero'),
                        uf_emissao_rg=uf_emissao_rg_id,
                        orgao_emissao_rg=orgao,
                        data_emissao_rg=daga_emissao_rg,
                        linha_pesquisa=candidato_vaga.oferta_vaga.oferta_vaga_curso.linha_pesquisa,
                        tipo_zona_residencial=getText('endereco_zona_residencial') == 'Urbana' and 1 or 0,
                        naturalidade=naturalidade,
                    )

                    url = '{}{}/{}/'.format(Configuracao.get_valor_por_chave('ae', 'caracterizacao_webservice'), candidato.edital.codigo, candidato.inscricao)

                    mapa_deficiencia = {
                        1: [Aluno.DEFICIENCIA_VISUAL, 'Baixa Visão', 'tipo_necessidade_especial'],
                        2: [Aluno.DEFICIENCIA_VISUAL_TOTAL, 'Cegueira', 'tipo_necessidade_especial'],
                        5: [Aluno.DEFICIENCIA_AUDITIVA, 'Deficiência Auditiva', 'tipo_necessidade_especial'],
                        3: [Aluno.DEFICIENCIA_FISICA, 'Deficiência Física', 'tipo_necessidade_especial'],
                        4: [Aluno.DEFICIENCIA_MENTAL, 'Deficiência Intelectual', 'tipo_necessidade_especial'],
                        6: [Aluno.DEFICIENCIA_AUDITIVA_TOTAL, 'Surdez', 'tipo_necessidade_especial'],
                        7: [Aluno.DEFICIENCIA_AUDITIVA_VISUAL_TOTAL, 'Surdocegueira', 'tipo_necessidade_especial'],
                        13: [Aluno.OUTRAS_CONDICOES, 'Outras Condições', 'tipo_necessidade_especial'],
                        8: [Aluno.AUTISMO_INFANTIL, 'Autismo', 'tipo_transtorno'],
                    }
                    try:
                        xml = zlib.decompress(urllib.request.urlopen(url).read())
                        dados = xmltodict.parse(xml)['edital']['caracterizacoes']['caracterizacao']
                        if 'necessidade_especial' in dados and dados['necessidade_especial']['deficiencia'] == 'Sim':
                            dados_deficiencia = mapa_deficiencia.get(int(dados['necessidade_especial']['codigo']))
                            if dados_deficiencia:
                                initial['aluno_pne'] = 'Sim'
                                initial[dados_deficiencia[2]] = dados_deficiencia[0]
                    except Exception:
                        pass

    alunos = alunos.filter(situacao__ativo=True)
    if initial and candidato_vaga:
        qs_matriz_curso = MatrizCurso.objects.filter(curso_campus=candidato_vaga.oferta_vaga.oferta_vaga_curso.curso_campus)
        initial.update(
            ano_letivo=candidato_vaga.candidato.edital.ano.pk,
            periodo_letivo=candidato_vaga.candidato.edital.semestre,
            turno=candidato_vaga.candidato.turno and candidato_vaga.candidato.turno.pk or None,
            matriz_curso=qs_matriz_curso.count() == 1 and qs_matriz_curso[0].pk or None,
        )
    form = EfetuarMatriculaForm(request, candidato_vaga, data=request.POST or None, initial=initial, files=request.FILES or None)
    if form.is_valid():
        aluno = form.processar()
        if form.is_curso_fic():
            return httprr(f'/edu/efetuar_matricula_turma/{aluno.pk}/', 'Matrícula institucional realizada com sucesso. Realize a matrícula na turma.')
        else:
            comprovante_matricula_response = comprovante_matricula_pdf(request, aluno.pk)

            email_pessoal = form.cleaned_data.get('email_pessoal')
            mensagem_envio_email = ''
            if email_pessoal:
                attachments = [('Comprovante.pdf', comprovante_matricula_response.content, 'application/pdf')]
                send_mail(
                    'Comprovante de Matrícula',
                    'Caro aluno(a), segue em anexo seu comprovante de matrícula.',
                    settings.DEFAULT_FROM_EMAIL,
                    [email_pessoal],
                    fail_silently=True,
                    attachments=attachments
                )
                mensagem_envio_email = f'Um e-mail com o comprovante foi enviado para {email_pessoal}.'

            if candidato_vaga_id:
                candidato_vaga = get_object_or_404(CandidatoVaga, pk=candidato_vaga_id)
                candidato_vaga.registrar_matricula()
                return httprr(
                    f'/processo_seletivo/classificados/{candidato_vaga.oferta_vaga.pk}/',
                    mark_safe('Matrícula realizada com sucesso. {} Clique neste link para <a target="_blank" href="/edu/comprovante_matricula_pdf/{}/">imprimir o comprovante</a>.'.format(
                        mensagem_envio_email, aluno.pk
                    )),
                )
            else:
                return httprr(
                    '/edu/efetuar_matricula/',
                    mark_safe('Matrícula realizada com sucesso. {} Clique neste link para (<a target="_blank" href="/edu/comprovante_matricula_pdf/{}/">imprimir o comprovante</a>).'.format(
                        mensagem_envio_email, aluno.pk
                    )),
                )
    return locals()


@rtr()
@permission_required('edu.efetuar_matricula')
def efetuar_matricula_turma(request, aluno_id):
    title = 'Matrícula em Turma'
    aluno = get_object_or_404(Aluno, pk=aluno_id)
    form = EfetuarMatriculaTurmaForm(aluno, data=request.POST or None)
    if form.is_valid():
        matricula_periodo = form.processar(aluno)
        return httprr(
            '/edu/efetuar_matricula/', mark_safe(f'Matrícula realizada com sucesso. (<a target="_blank" href="/edu/comprovante_matricula_pdf/{aluno.pk}/">Imprimir Comprovante</a>).')
        )
    return locals()


@rtr()
@permission_required('edu.efetuar_matricula')
def efetuar_matriculas_turma(request, turma_id):
    title = 'Matrículas em Turma'
    turma = get_object_or_404(Turma, pk=turma_id)
    form = EfetuarMatriculasTurmaForm(turma, data=request.POST or None)
    if form.is_valid():
        alunos = form.processar(turma)
        return httprr(f'/edu/turma/{turma_id}/', 'Matrículas realizadas com sucesso.')
    return locals()


@csrf_exempt
def fotografar(request):
    return HttpResponse(base64.b64encode(request.body))


def aluno_sincronizar_ldap(request, aluno_pk):
    if not request.user.is_superuser:
        raise PermissionDenied()
    aluno = get_object_or_404(Aluno, pk=aluno_pk)
    LdapConf = apps.get_model('ldap_backend', 'LdapConf')
    conf = LdapConf.get_active()
    conf.sync_user(aluno)
    return httprr('/admin/edu/aluno/', f'Aluno "{aluno}" sincronizado.')


@rtr()
@login_required()
def horario_professor(request, pk, pk_diario):
    obj = get_object_or_404(Professor, pk=pk)
    diario = Diario.objects.get(pk=pk_diario)
    turnos = obj.get_horarios_aula_por_turno(diario.ano_letivo.ano, diario.periodo_letivo)
    return locals()


@documento('Declaração de Orientação', validade=30, modelo='edu.professor')
@rtr('emitir_declaracao_de_orientacao_tcc_pdf.html')
@login_required()
def emitir_declaracao_de_orientacao_tcc_pdf(request, pk, ano=None):
    obj = get_object_or_404(Professor, pk=pk)
    pode_emitir_declaracao_orientacao_tcc = request.user == obj.vinculo.user or in_group(
        request.user, 'Administrador Acadêmico,Diretor Acadêmico,Coordenador de Curso,Secretário Acadêmico'
    )
    if not pode_emitir_declaracao_orientacao_tcc:
        return HttpResponseForbidden()
    nome_professor = obj.vinculo.pessoa.nome
    matricula_siape = obj.vinculo.relacionamento.matricula
    uo = request.user.get_vinculo().setor.uo
    hoje = datetime.date.today()
    projetos_finais = ProjetoFinal.objects.filter(orientador=obj).exclude(
        resultado_data__isnull=True, matricula_periodo__aluno__situacao__in=[SituacaoMatricula.JUBILADO, SituacaoMatricula.EVASAO, SituacaoMatricula.FALECIDO]
    )
    if ano:
        projetos_finais = projetos_finais.filter(matricula_periodo__ano_letivo__ano=int(ano))
    return locals()


@rtr()
@login_required()
@permission_required('edu.view_professor')
def professor(request, pk=None):
    if pk:
        obj = get_object_or_404(Professor, pk=pk)
    else:
        obj = get_object_or_404(Professor, vinculo__user=request.user)
    vinculo = obj.vinculo
    professor_eh_servidor = vinculo.eh_servidor()
    professor_eh_docente = professor_eh_servidor and vinculo.relacionamento.eh_docente
    eh_proprio_professor = request.user == vinculo.user
    pode_emitir_declaracao_orientacao_tcc = eh_proprio_professor or in_group(request.user, 'Administrador Acadêmico,Diretor Acadêmico,Coordenador de Curso,Secretário Acadêmico')
    if professor_eh_servidor:
        usuario_logado_uo = request.user.get_vinculo() and request.user.get_vinculo().setor and request.user.get_vinculo().setor.uo or None
        professor_uo = vinculo and vinculo.setor and vinculo.setor.uo or None
        pode_ver_dados_pessoais = in_group(request.user, 'Administrador Acadêmico') or (
            in_group(request.user, 'Diretor Acadêmico, Diretor Geral, Secretário Acadêmico') and usuario_logado_uo and usuario_logado_uo == professor_uo
        )
        pode_ver_dados_pessoais = pode_ver_dados_pessoais and (professor_eh_docente or obj.professordiario_set.exists())
    else:
        pode_ver_dados_pessoais = True

    periodo_letivo_atual = PeriodoLetivoAtual.get_instance(request, obj)
    title = f'Professor(a) {obj.get_matricula()}'

    projetos_finais = ProjetoFinal.objects.filter(orientador=obj)
    projetos_finais_coorientador = ProjetoFinal.objects.filter(coorientadores__id=obj.vinculo.pessoa.id)
    bancas_presidente, bancas_examinador = obj.get_participacoes_em_bancas()
    qtd_bancas_presidente = len(bancas_presidente)
    qtd_bancas_examinador = len(bancas_examinador)

    qtd_estagios = obj.praticaprofissional_set.count() + obj.estagiodocente_orientador_set.count() + obj.aprendizagem_set.count() + obj.atividadeprofissionalefetiva_set.count()

    app_pit_rit_instalada = 'pit_rit' in settings.INSTALLED_APPS or 'pit_rit_v2' in settings.INSTALLED_APPS
    exibir_diarios = not request.GET.get('tab') and not pode_ver_dados_pessoais

    if request.GET.get('tab') in ['planoatividades', 'disciplinas'] or exibir_diarios:
        vinculos_turmas_minicurso = obj.get_vinculos_minicurso(periodo_letivo_atual.ano, periodo_letivo_atual.periodo)
        diarios_especiais = obj.get_vinculos_diarios_especiais(periodo_letivo_atual.ano, periodo_letivo_atual.periodo)

    if request.GET.get('tab') == 'disciplinas' or exibir_diarios:
        vinculos_diarios_regulares = obj.get_vinculo_diarios(periodo_letivo_atual.ano, periodo_letivo_atual.periodo, False)
        vinculos_diarios_fics = obj.get_vinculo_diarios(periodo_letivo_atual.ano, periodo_letivo_atual.periodo, True)

    if request.GET.get('tab') == 'planoatividades':
        pit = None
        vinculos_diarios = obj.get_vinculo_diarios(periodo_letivo_atual.ano, periodo_letivo_atual.periodo, None, True, False)
        vinculos_diarios_regulares = obj.get_vinculo_diarios(periodo_letivo_atual.ano, periodo_letivo_atual.periodo, False, True, False)
        vinculos_diarios_fics = obj.get_vinculo_diarios(periodo_letivo_atual.ano, periodo_letivo_atual.periodo, True, True, False)
        ano_letivo = Ano.objects.get(ano=periodo_letivo_atual.ano)
        ano_corrente = int(Configuracao.get_valor_por_chave('edu', 'ano_letivo_atual') or datetime.date.today().year)
        periodo_corrente = int(Configuracao.get_valor_por_chave('edu', 'periodo_letivo_atual') or 1)

        if 'pit_rit' in settings.INSTALLED_APPS:
            from pit_rit.models import PlanoIndividualTrabalho, ConfiguracaoAtividadeDocente

            pit = PlanoIndividualTrabalho.objects.filter(ano_letivo=ano_letivo, periodo_letivo=periodo_letivo_atual.periodo, professor=obj).first()
            if not pit:
                configuracoes_ativas = ConfiguracaoAtividadeDocente.objects.filter(ano_letivo_inicio=ano_letivo, periodo_letivo_inicio=periodo_letivo_atual.periodo)
                if configuracoes_ativas.exists():
                    pit = PlanoIndividualTrabalho.objects.create(
                        ano_letivo=ano_letivo, periodo_letivo=periodo_letivo_atual.periodo, professor=obj, configuracao=configuracoes_ativas[0]
                    )
        if 'pit_rit_v2' in settings.INSTALLED_APPS:
            from pit_rit_v2.models import PlanoIndividualTrabalhoV2

            qs_relatorios = PlanoIndividualTrabalhoV2.objects.filter(ano_letivo=ano_letivo, periodo_letivo=periodo_letivo_atual.periodo, professor=obj)
            if qs_relatorios.exists():
                pit = qs_relatorios.first()

        if pit and (not 'pit_rit_v2' in settings.INSTALLED_APPS or periodo_letivo_atual.ano < 2019):
            pode_editar_plano_atividade = not pit.deferida

            atividades_ensino = pit.get_atividades_ensino()
            atividades_pesquisa = pit.get_atividades_pesquisa()
            atividades_extensao = pit.get_atividades_extensao()
            atividades_gestao = pit.get_atividades_gestao()
            atividades_cargo_funcao = pit.get_atividades_cargo_funcao()

            for professor_diario in vinculos_diarios:
                professor_diario.ch_qtd_creditos = professor_diario.get_qtd_creditos_efetiva()

            for diario_especial in diarios_especiais:
                diario_especial.ch_qtd_creditos = int(math.ceil(float(diario_especial.componente.ch_qtd_creditos) / diario_especial.professores.count()))

            ch_semanal_diarios = pit.get_ch_diarios()
            ch_semanal_diarios_fic = pit.get_ch_diarios(True)
            ch_semanal_minicursos = pit.get_ch_minicursos_ha()
            ch_semanal_manutencao_ensino = ch_semanal_diarios + ch_semanal_diarios_fic + ch_semanal_minicursos
            ch_semanal_atividades_ensino = pit.get_ch_semanal_atividades_ensino()
            ch_semanal_atividades_pesquisa = pit.get_ch_semanal_atividades_pesquisa()
            ch_semanal_atividades_extensao = pit.get_ch_semanal_atividades_extensao()
            ch_semanal_atividades_gestao = pit.get_ch_semanal_atividades_gestao()
            ch_semanal_atividades_cargo_funcao = pit.get_ch_semanal_atividades_cargo_funcao()
            ch_total_semanal = pit.get_ch_semanal_total()

            # Validando se o Professor está de acordo com as normas definidas na Configuração de Atividades Docentes.
            ha_semanal = pit.configuracao.ha_semanal
            ha_minima_semanal = pit.configuracao.ha_minima_semanal
            percentual_reducao = 0
            carga_horaria_servidor = None
            funcao_servidor = None

            if professor_eh_servidor:
                data_inicio = datetime.datetime.strptime(f'01/01/{periodo_letivo_atual.ano}', '%d/%m/%Y')
                data_fim = datetime.datetime.strptime(f'31/12/{periodo_letivo_atual.ano}', '%d/%m/%Y')
                servidor = obj.vinculo.relacionamento
                historico_funcoes = servidor.historico_funcao(data_inicio=data_inicio, data_fim=data_fim)

                if periodo_letivo_atual.ano < 2017 or (periodo_letivo_atual.ano == 2017 and periodo_letivo_atual.periodo == 1):
                    funcao_servidor = historico_funcoes.last().funcao_display if historico_funcoes.exists() else None
                else:
                    atividade_cargo_funcao_semestral = pit.get_atividade_cargo_funcao_semestral()
                    if atividade_cargo_funcao_semestral:
                        funcao_servidor = atividade_cargo_funcao_semestral.tipo_atividade.descricao
                carga_horaria_servidor = servidor.jornada_trabalho and servidor.jornada_trabalho.nome

            # Aplicando os redutores na Carga Horária do Docente 20Hrs
            if carga_horaria_servidor == "20 HORAS SEMANAIS":
                percentual_reducao = pit.configuracao.percentual_reducao_20h
                ha_semanal = ha_semanal - ((percentual_reducao * ha_semanal) / 100)

            # Aplicando os redutores na Carga Horária do Docente ocupante de Função
            if funcao_servidor:
                if funcao_servidor == 'CD1':
                    percentual_reducao = pit.configuracao.percentual_reducao_cd1
                elif funcao_servidor == 'CD2':
                    percentual_reducao = pit.configuracao.percentual_reducao_cd2
                elif funcao_servidor == 'CD3':
                    percentual_reducao = pit.configuracao.percentual_reducao_cd3
                elif funcao_servidor == 'CD4':
                    percentual_reducao = pit.configuracao.percentual_reducao_cd4
                elif funcao_servidor == 'FG1' or funcao_servidor == 'FCC' or funcao_servidor == 'FUC1':
                    percentual_reducao = pit.configuracao.percentual_reducao_fg1
                elif funcao_servidor == 'FG2':
                    percentual_reducao = pit.configuracao.percentual_reducao_fg2
                elif funcao_servidor == 'FG3':
                    percentual_reducao = pit.configuracao.percentual_reducao_fg3
                elif funcao_servidor == 'FG4':
                    percentual_reducao = pit.configuracao.percentual_reducao_fg4
                elif funcao_servidor == Funcao.get_sigla_funcao_apoio_a_gestao():
                    if obj.vinculo.setor.uo.eh_reitoria:
                        percentual_reducao = pit.configuracao.percentual_reducao_fa_reitoria
                    else:
                        percentual_reducao = pit.configuracao.percentual_reducao_fa_campus
            if percentual_reducao:
                ha_semanal = ha_semanal - ((percentual_reducao * ha_semanal) / 100)
                ha_minima_semanal = ha_minima_semanal - ((percentual_reducao * ha_minima_semanal) / 100)

        if 'pit_rit_v2' in settings.INSTALLED_APPS and periodo_letivo_atual.ano >= 2019:
            if not pit:
                qs = PlanoIndividualTrabalhoV2.objects.filter(professor=obj, ano_letivo=ano_letivo, periodo_letivo=periodo_letivo_atual.periodo)
                pit = instance = qs.first() or PlanoIndividualTrabalhoV2.objects.create(professor=obj, ano_letivo=ano_letivo, periodo_letivo=periodo_letivo_atual.periodo)
            if 'cancelar_submissao' in request.GET and eh_proprio_professor:
                pit.avaliador = None
                pit.data_envio = None
                pit.save()
                return httprr(
                    f'/edu/professor/{obj.pk}/?tab=planoatividades&ano-periodo={periodo_letivo_atual.ano}.{periodo_letivo_atual.periodo}',
                    'Submissão cancelada com sucesso',
                )
            pode_editar_plano_atividade = True
            ch_semanal_aulas, ch_aulas, ch_semanal_diarios, ch_semanal_diarios_fic, ch_semanal_minicursos, ch_semanal_diarios_especiais, ch_preparacao_manutencao_ensino, ch_apoio_ensino, ch_programas_projetos_ensino, ch_orientacao_alunos, ch_reunioes, ch_pesquisa, ch_extensao, ch_gestao, ch_total = (
                pit.get_cargas_horarias()
            )

            ch_resumo = [
                (ch_aulas, 'AULAS'),
                (ch_preparacao_manutencao_ensino, 'PREPARAÇÃO E MANUTENÇÃO DO ENSINO'),
                (ch_apoio_ensino, 'APOIO AO ENSINO'),
                (ch_programas_projetos_ensino, 'PROGRAMAS OU PROJETOS DE ENSINO'),
                (ch_orientacao_alunos, 'ATENDIMENTO, ACOMPANHAMENTO, AVALIAÇÃO E ORIENTAÇÃO DE ALUNOS'),
                (ch_reunioes, 'REUNIÕES PEDAGÓGICAS, DE GRUPO E AFINS'),
                (ch_pesquisa, 'PESQUISA E INOVAÇÃO'),
                (ch_extensao, 'EXTENSÃO'),
                (ch_gestao, 'GESTÃO E REPRESENTAÇÃO INSTITUCIONAL'),
            ]
            pode_enviar_plano = pit.pode_enviar_plano(request.user)
            pode_alterar_avaliador_plano = pit.pode_alterar_avaliador_plano(request.user)
            pode_avaliar_plano = pit.pode_avaliar_plano(request.user)
            pode_desfazer_aprovacao_plano = pit.pode_desfazer_aprovacao_plano(request.user)

            pode_preencher_relatorio = pit.pode_preencher_relatorio(request.user)
            pode_enviar_relatorio = pit.pode_enviar_relatorio(request.user)
            pode_alterar_avaliador_relatorio = pit.pode_alterar_avaliador_relatorio(request.user)
            pode_avaliar_relatorio = pit.pode_avaliar_relatorio(request.user)
            pode_desfazer_aprovacao_relatorio = pit.pode_desfazer_aprovacao_relatorio(request.user)

    if request.GET.get('tab') == 'estagios':
        usuario_emite_declaracao_orientacao = in_group(request.user, 'Administrador Acadêmico,Secretário Acadêmico,Coordenador de Curso,Diretor Acadêmico') or eh_proprio_professor

    if request.GET.get('tab') == 'horarios':
        horarios_campus = obj.get_horarios_aula_por_horario_campus(periodo_letivo_atual.ano, periodo_letivo_atual.periodo)

    ferias_instaladas = 'ferias' in settings.INSTALLED_APPS
    if professor_eh_servidor and ferias_instaladas:
        Ferias = apps.get_model('ferias', 'Ferias')
        servidor_ferias = Ferias.objects.filter(servidor=obj.vinculo.relacionamento).order_by('ano')

    from projetos.models import Participacao as PartExtensao

    participacoes_extensao = PartExtensao.objects.filter(vinculo_pessoa=vinculo, ativo=True, projeto__aprovado=True)

    from pesquisa.models import Participacao as PartPesquisa

    participacoes_pesquisa = PartPesquisa.objects.filter(vinculo_pessoa=vinculo, ativo=True, projeto__aprovado=True)

    participacoes_eventos = ParticipanteEvento.objects.filter(participante__id=vinculo.pessoa.id)

    return locals()


@rtr()
@login_required()
@group_required('Administrador Acadêmico,Diretor Acadêmico,Coordenador de Curso,Coordenador de Modalidade Acadêmica ,Secretário Acadêmico')
def editar_professor(request, pk):
    title = 'Editar Professor(a)'
    professor = get_object_or_404(Professor, pk=pk)
    initial = dict(
        nome=professor.vinculo.pessoa.nome,
        cpf=professor.vinculo.relacionamento.pessoa_fisica.cpf,
        sexo=professor.vinculo.relacionamento.pessoa_fisica.sexo,
        email=professor.vinculo.pessoa.email,
        uo=professor.vinculo.setor,
    )

    form = ProfessorExternoForm(data=request.POST or None, initial=initial)
    if form.is_valid():
        form.save(professor)
        return httprr('..', 'Edição realizada com sucesso.')
    return locals()


@rtr()
def adicionar_requerimento(request, tipo, pk=None):
    title = 'Requerimento'
    instance = pk and get_object_or_404(Requerimento, pk=pk) or None
    aluno = get_object_or_404(Aluno, matricula=request.user.username)
    if aluno.situacao.ativo:
        form_cls = None
        if int(tipo) == Requerimento.TRANCAMENTO_DISCIPLINA:
            form_cls = RequerimentoCancelamentoDisciplinaForm
            form = form_cls(data=request.POST or None, instance=instance, request=request, aluno=aluno)
            if form.is_valid():
                form.save()
                return httprr('..', 'Requerimento adicionado com sucesso')
        elif int(tipo) == Requerimento.MATRICULA_DISCIPLINA:
            form_cls = RequerimentoMatriculaDiarioForm
            form = form_cls(data=request.POST or None, instance=instance, request=request, aluno=aluno)
            if form.is_valid():
                form.save()
                return httprr('..', 'Requerimento adicionado com sucesso')
        else:
            return httprr('..', 'Tipo de Requerimento inválido.', 'error')
    else:
        return httprr('..', 'Requerimento disponível apenas para alunos ativos.', 'error')
    return locals()


@rtr()
def aluno(request, matricula):
    obj = get_object_or_404(Aluno, matricula=matricula)
    title = f'{normalizar_nome_proprio(obj.get_nome())} ({str(obj.matricula)})'
    is_responsavel = False

    if request.user.is_anonymous:
        if request.session.get('matricula_aluno_como_resposavel') == matricula:
            is_responsavel = True
        else:
            return httprr('/', 'Você não tem permissão para acessar está página.', 'error')

    is_proprio_aluno = obj.is_user(request)
    is_assistente_social = request.user.has_perm('ae.pode_abrir_inscricao_do_campus')
    is_admin = in_group(request.user, 'edu Administrador') or request.user.is_superuser
    is_nivel_superior = obj.curso_campus.modalidade and obj.curso_campus.modalidade.nivel_ensino.pk in [NivelEnsino.GRADUACAO, NivelEnsino.POS_GRADUACAO]
    is_orientador = not is_responsavel and obj.matriculaperiodo_set.filter(projetofinal__orientador__vinculo__user=request.user).exists()
    is_cra = in_group(request.user, 'Coordenador de Registros Acadêmicos') and obj.situacao.id in [
        SituacaoMatricula.CONCLUIDO,
        SituacaoMatricula.FORMADO,
        SituacaoMatricula.EVASAO,
        SituacaoMatricula.TRANCADO,
        SituacaoMatricula.FALECIDO,
        SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE,
        SituacaoMatricula.CANCELADO,
        SituacaoMatricula.CANCELAMENTO_COMPULSORIO,
        SituacaoMatricula.TRANSFERIDO_EXTERNO,
        SituacaoMatricula.JUBILADO,
    ]
    is_da_mesma_diretoria_academica = Diretoria.locals.filter(setor__id=obj.setor.id).exists()
    is_do_mesmo_campus = UnidadeOrganizacional.locals.filter(id=obj.setor.uo.id).exists()
    pode_ver_dados_sociais = is_proprio_aluno or in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico')

    pode_ver_dados_bancarios = pode_ver_dados_sociais or in_group(request.user, 'Coordenador de Pesquisa')
    pode_ver_dados_academicos = (
        is_admin
        or is_responsavel
        or is_proprio_aluno
        or (is_da_mesma_diretoria_academica or is_do_mesmo_campus)
        and request.user.has_perm('edu.view_dados_academicos')
    )
    pode_enviar_mensagem = (
        request.user.has_perm('edu.add_mensagem')
        and (
            in_group(
                request.user,
                'Administrador Acadêmico',
            )
            or is_da_mesma_diretoria_academica
            or (in_group(request.user, 'Coordenador de Registros Acadêmicos,Operador do Comunicador') and is_do_mesmo_campus)
        )
    )
    pode_editar_email_secundario_aluno = request.user.has_perm('rh.pode_editar_email_secundario_aluno')
    tem_permissao_realizar_procedimentos = not is_responsavel and perms.realizar_procedimentos_academicos(request.user, obj.curso_campus)
    pode_ver_etep = not is_responsavel and (
        tem_permissao_realizar_procedimentos_etep(request, obj.curso_campus.diretoria.setor) or obj.acompanhamento_set.filter(interessado__vinculo=request.user.get_vinculo())
    )
    tem_permissao_para_emitir_docs_matricula = (request.user.has_perm('edu.efetuar_matricula') or in_group(request.user, "Estagiário")) and is_da_mesma_diretoria_academica
    pode_editar_titulacao_diario_resumido = tem_permissao_realizar_procedimentos or is_admin
    pode_realizar_procedimentos = tem_permissao_realizar_procedimentos and not obj.is_concluido() or is_admin
    pode_realizar_operacoes_qacademico = is_do_mesmo_campus and (request.user.has_perm('edu.efetuar_matricula') or request.user.has_perm('edu.view_registroemissaodiploma'))
    pode_realizar_transferencia = pode_realizar_procedimentos and obj.get_ultima_matricula_periodo() and obj.get_ultima_matricula_periodo().pode_realizar_transferencia()
    pode_desfazer_migracao = not is_responsavel and in_group(request.user, 'Administrador Acadêmico')
    pode_ver_cpf = (
        pode_ver_dados_sociais
        or pode_ver_dados_academicos
        or in_group(request.user, 'Coordenador de TI de campus, Coordenador de TI sistêmico, Coordenador de Atividades Estudantis, Servidor')
    )
    pode_alterar_email = perms.pode_alterar_email(request, obj)
    pode_ver_requisitos_de_conclusao = pode_ver_dados_academicos or in_group(request.user, 'Organizador de Formatura, Coordenador de Registros Acadêmicos') and (is_da_mesma_diretoria_academica or is_do_mesmo_campus)
    diploma = RegistroEmissaoDiploma.objects.filter(aluno=obj, cancelado=False).order_by('-via')
    if not (pode_editar_email_secundario_aluno or pode_ver_dados_sociais or pode_ver_dados_academicos or pode_realizar_procedimentos or request.user.has_perm('edu.view_aluno')):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    ultima_matricula_periodo = obj.get_ultima_matricula_periodo()
    is_matriculado = obj.situacao.id == SituacaoMatricula.MATRICULADO
    is_matricula_vinculo = obj.situacao.id == SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL

    pode_evadir = False
    if ultima_matricula_periodo:
        pode_evadir = pode_realizar_procedimentos and (
            ultima_matricula_periodo.is_matriculado() or ultima_matricula_periodo.is_matricula_vinculo() or ultima_matricula_periodo.is_aberto()
        )
    if 'del_requerimento' in request.GET:
        requerimento = Requerimento.objects.filter(pk=request.GET.get('del_requerimento', 0)).first()
        if requerimento and requerimento.aluno == obj and requerimento.deferido is None:
            requerimento.delete()
            return httprr(f'/edu/aluno/{obj.matricula}/?tab=requerimentos', 'Requerimento excluído com sucesso.')
    if 'enviar_comprovante_matricula' in request.GET:
        if obj.pessoa_fisica.email_secundario:
            attachments = [('Comprovante.pdf', comprovante_matricula_pdf(request, obj.pk).content, 'application/pdf')]
            send_mail(
                'Comprovante de Matrícula',
                'Caro aluno(a), segue em anexo seu comprovante de matrícula.',
                settings.DEFAULT_FROM_EMAIL,
                [obj.pessoa_fisica.email_secundario],
                fail_silently=False, attachments=attachments
            )
            mensagem_envio_email = f'Comprovante de matrícula enviado para {obj.pessoa_fisica.email_secundario}.'
            return httprr(f'/edu/aluno/{obj.matricula}/', mensagem_envio_email)

    if 'desfazer_migracao' in request.GET and pode_desfazer_migracao:
        obj.desfazer_migracao()
        return httprr('..', 'A migração do aluno do Q-Acadêmico foi desfeita com sucesso!')

    if 'procedimento_id' in request.GET and pode_realizar_procedimentos:
        procedimento = get_object_or_404(ProcedimentoMatricula, pk=request.GET['procedimento_id'])
        try:
            procedimento.desfazer()
        except Exception as e:
            return httprr('.', e.message, 'error')
        return httprr('.', 'Procedimento desfeito com sucesso!')

    if 'reprocessar_historico' in request.GET and pode_realizar_procedimentos and (is_matriculado or is_matricula_vinculo):
        obj.atualizar_situacao('Reprocessamento do Histórico')
        return httprr('.', 'Histórico reprocessado com sucesso.')

    if (is_admin or pode_realizar_procedimentos or is_proprio_aluno) and 'aluno_arquivo' in request.GET:
        aluno_arquivo = AlunoArquivo.objects.filter(pk=request.GET['aluno_arquivo'], aluno=obj).first()
        if aluno_arquivo:
            if is_admin or (pode_realizar_procedimentos and (not aluno_arquivo.validado or aluno_arquivo.responsavel_validacao == request.user)) or (is_proprio_aluno and not aluno_arquivo.validado):
                aluno_arquivo.delete()
                return httprr(f'/edu/aluno/{obj.matricula}/?tab=pasta_documental', 'Arquivo excluído com sucesso.')

    # PROCEDIMENTOS DE MATRÍCULA
    procedimentos = obj.get_procedimentos_matricula()

    # ATIVIDADES ESTUDANTIS
    if request.GET.get('tab') == 'atividades_estudantis' and 'ae' in settings.INSTALLED_APPS:
        from ae.models import HistoricoFaltasAlimentacao, HistoricoSuspensoesAlimentacao, AgendamentoRefeicao, DemandaAluno, DocumentoInscricaoAluno, Participacao, ParticipacaoBolsa, PeriodoInscricao
        atendimentos = obj.demandaalunoatendida_set.filter(quantidade__gt=0).order_by('-data')[:10]
        participacoes = Participacao.objects.filter(inscricao__aluno=obj).order_by('data_inicio', 'data_termino')
        participacoes_bolsas = ParticipacaoBolsa.objects.filter(aluno=obj).order_by('data_inicio', 'data_termino')

        mes = datetime.date.today().month
        ano = datetime.date.today().year
        demandas_atendidas = obj.demandaalunoatendida_set.filter(quantidade__gt=0, data__month=mes, data__year=ano)
        atendimentos_grafico = []

        for demanda in DemandaAluno.ativas.all():
            atendimentos_do_mes = demandas_atendidas.filter(demanda__nome=demanda.nome)
            if atendimentos_do_mes.exists():
                atendimentos_grafico.append([demanda.nome, atendimentos_do_mes.aggregate(Sum('quantidade'))['quantidade__sum'] or 0])

        nome_pk = 'grafico_atendimentos'
        grafico = PieChart(nome_pk, title="Total de Atendimentos neste Mês", minPointLength=0, data=atendimentos_grafico)
        setattr(grafico, 'id', nome_pk)

        agendamentos = AgendamentoRefeicao.objects.filter(cancelado=False, aluno=obj, data__gte=datetime.date.today()).order_by('-data')

        historico_faltas = HistoricoFaltasAlimentacao.objects.filter(aluno=obj).order_by('-data')[:10]
        historico_suspensoes = HistoricoSuspensoesAlimentacao.objects.filter(participacao__aluno=obj).order_by('-data_inicio')[:10]
        documentos = DocumentoInscricaoAluno.objects.filter(aluno=obj).order_by('-data_cadastro', '-integrante_familiar')
        hoje = datetime.date.today()
        periodos_permitidos = PeriodoInscricao.objects.filter(
            campus=obj.curso_campus.diretoria.setor.uo, data_termino__gte=datetime.datetime.today(), programa__instituicao=get_uo(request.user), edital__ativo=True
        )

        aluno_pode_adicionar_documento = is_proprio_aluno and periodos_permitidos.exists()

    fazer_avaliacao_biomedica = False
    if 'saude' in settings.INSTALLED_APPS:
        from saude.models import Atendimento, TipoAtendimento

        fazer_avaliacao_biomedica = (
            obj.data_matricula
            and (datetime.datetime.now() - obj.data_matricula).days > 60
            and obj.curso_campus.modalidade
            and obj.curso_campus.modalidade.id == Modalidade.INTEGRADO
            and obj.ano_letivo
            and obj.ano_letivo.ano > 2015
            and not Atendimento.objects.filter(tipo=TipoAtendimento.AVALIACAO_BIOMEDICA, aluno=obj).exists()
        )

    # DIPLOMAS E CERTIFICADOS
    diplomas = obj.get_registros_emissao_diploma()

    # MODULOS
    if request.GET.get('tab') == 'modulos':
        qs_cc = ComponenteCurricular.objects.filter(matriz_id=obj.matriz.id).order_by('tipo_modulo')
        modulos = set()
        for componente_curricular in qs_cc:
            componente_curricular.matricula_diario = MatriculaDiario.objects.filter(
                matricula_periodo__aluno_id=obj.id, diario__componente_curricular_id=componente_curricular.id
            ).first()
            if componente_curricular.tipo_modulo is not None:
                modulos.add(componente_curricular.tipo_modulo)
        modulos_aptos_certificacao = []
        for modulo in modulos:
            ids_cc = ComponenteCurricular.objects.filter(matriz_id=obj.matriz_id, tipo_modulo=modulo).order_by('id').values_list('id', flat=True)
            ids_md = (
                MatriculaDiario.objects.filter(
                    matricula_periodo__aluno_id=obj.id,
                    diario__componente_curricular__tipo_modulo=modulo,
                    situacao__in=[MatriculaDiario.SITUACAO_APROVADO, MatriculaDiario.SITUACAO_APROVEITAMENTO_ESTUDO, MatriculaDiario.SITUACAO_CERTIFICACAO_CONHECIMENTO],
                )
                .order_by('diario__componente_curricular__id')
                .values_list('diario__componente_curricular_id', flat=True)
            )
            if list(ids_cc) == list(ids_md):
                modulos_aptos_certificacao.append((modulo, int_to_roman(modulo)))

    # BOLETIM
    if request.GET.get('tab') == 'boletim':
        qs = obj.get_matriculas_periodo()
        if qs.exists():
            anos_periodos = qs.values_list('ano_letivo__ano', 'periodo_letivo').distinct()
        matriculas_diario = None
        if not request.GET.get('ano_periodo'):
            matricula_periodo = ultima_matricula_periodo
            matriculas_diario = ultima_matricula_periodo and matricula_periodo.matriculadiario_set.all().order_by('diario__componente_curricular__componente__descricao')
        elif request.GET.get('ano_periodo'):
            try:
                ano_periodo = request.GET.get('ano_periodo').split('_')
                ano = int(ano_periodo[0])
                periodo = int(ano_periodo[1])
                qs_matricula_periodo = MatriculaPeriodo.objects.filter(aluno=obj, ano_letivo__ano=ano, periodo_letivo=periodo)
                if qs_matricula_periodo:
                    matricula_periodo = qs_matricula_periodo[0]
                    matriculas_diario = matricula_periodo.matriculadiario_set.all().order_by('diario__componente_curricular__componente__descricao')
            except ValueError:
                return httprr('.', 'Requisição inválida.', 'error')
            except Exception:
                return httprr('.', 'Erro.', 'error')
        if matriculas_diario:
            tem_nota_atitudinal = matriculas_diario[0].diario.utiliza_nota_atitudinal()
            try:
                etapa = int(request.GET.get('etapa'))
            except Exception:
                etapa = 1
            etapa = etapa > 7 and 1 or etapa
            id_grafico = 'graficoBoletim'
            grafico = GroupedColumnChart(id_grafico, data=matricula_periodo.get_estatiscas_boletim(etapa), groups=['Nota do Aluno', 'Média da Turma'])
            grafico.series[0]['dataLabels'] = dict(enabled=True, color='#FFF', align='center', y=30)
            grafico.series[1]['dataLabels'] = dict(enabled=True, color='#FFF', align='center', y=30)

            max_qtd_avaliacoes = 1
            for matricula_diario in matriculas_diario:
                if matricula_diario.diario.componente_curricular.qtd_avaliacoes > max_qtd_avaliacoes:
                    max_qtd_avaliacoes = matricula_diario.diario.componente_curricular.qtd_avaliacoes

    # ATIVIDADES ESPECIFICAS
    diarios_especiais = obj.get_diarios_especiais()
    if request.GET.get('tab') == 'atividades_especificas':
        if diarios_especiais.exists():
            anos_periodos = diarios_especiais.values_list('ano_letivo__ano', 'periodo_letivo').distinct()

        if request.GET.get('ano_periodo'):
            ano_periodo = request.GET.get('ano_periodo').split('_')
            ano = int(ano_periodo[0])
            periodo = int(ano_periodo[1])
            qs_matricula_periodo = MatriculaPeriodo.objects.filter(aluno=obj, ano_letivo__ano=ano, periodo_letivo=periodo)
            if qs_matricula_periodo:
                matricula_periodo = qs_matricula_periodo[0]
                if obj.curso_campus.periodicidade == CursoCampus.PERIODICIDADE_ANUAL:
                    diarios_especiais = diarios_especiais.filter(ano_letivo=matricula_periodo.ano_letivo, periodo_letivo=matricula_periodo.periodo_letivo).order_by(
                        'componente__descricao'
                    )
                else:
                    diarios_especiais = diarios_especiais.filter(ano_letivo=matricula_periodo.ano_letivo).order_by('componente__descricao')

    # HISTÓRICO
    if request.GET.get('tab') == 'historico':

        if 'order_by' in request.GET:
            ordenar_por = (
                request.GET['order_by'] == 'componente'
                and Aluno.ORDENAR_HISTORICO_POR_COMPONENTE
                or request.GET['order_by'] == 'periodo_matriz'
                and Aluno.ORDENAR_HISTORICO_POR_PERIODO_MATRIZ
                or Aluno.ORDENAR_HISTORICO_POR_PERIODO_LETIVO
            )
        else:
            ordenar_por = Aluno.ORDENAR_HISTORICO_POR_PERIODO_MATRIZ
        exibir_optativas = 'optativas' in request.GET
        historico = obj.get_historico(False, ordenar_por, exibir_optativas)

    # PROJETO FINAL
    projetos = obj.get_projetos_finais()

    # MEDIDAS DISCIPLINARES
    medidas_disciplinares = obj.medidadisciplinar_set.all()
    premiacoes = obj.premiacao_set.all()

    # ATIVIDADES COMPLEMENTARES
    if request.GET.get('tab') == 'acc':
        tipos = obj.get_ch_atividades_complementares_por_tipo()
    atividades_complementares = obj.get_atividades_complementares()

    # ATIVIDADES DE APROFUNDAMENTO
    if request.GET.get('tab') == 'atividades_aprofundamento':
        pass
    atividades_aprofundamento = obj.atividadeaprofundamento_set.all()

    # REQUISITOS DE CONCLUSÃO
    if request.GET.get('tab') == 'requisitos' and obj.matriz:
        # CH Esperada
        ch_componentes_regulares_obrigatorios_esperada = obj.get_ch_componentes_regulares_obrigatorios_esperada()
        ch_componentes_regulares_optativos_esperada = obj.get_ch_componentes_regulares_optativos_esperada()
        ch_pratica_como_componente_esperada = obj.get_ch_pratica_como_componente_esperada()
        ch_visita_tecnica_esperada = obj.get_ch_visita_tecnica_esperada()
        ch_componentes_eletivos_esperada = obj.get_ch_componentes_eletivos_esperada()
        ch_componentes_seminario_esperada = obj.get_ch_componentes_seminario_esperada()
        ch_componentes_pratica_profissional_esperada = obj.get_ch_componentes_pratica_profissional_esperada()
        ch_componentes_tcc_esperada = obj.get_ch_componentes_tcc_esperada()
        ch_atividades_complementares_esperada = obj.get_ch_atividades_complementares_esperada()
        ch_atividade_aprofundamento_esperada = obj.get_ch_atividade_aprofundamento_esperada()
        ch_atividade_extensao_esperada = obj.get_ch_atividade_extensao_esperada()
        total_ch_esperada = obj.matriz.get_carga_horaria_total_prevista()
        requer_pp_atp = ch_componentes_pratica_profissional_esperada and ch_atividade_aprofundamento_esperada

        # CH Cumprida
        ch_componentes_regulares_obrigatorios_cumprida, ch_componentes_regulares_optativos_cumprida, ch_componentes_seminario_cumprida, ch_componentes_pratica_profissional_cumprida, ch_componentes_tcc_cumprida, ch_atividades_complementares_cumprida, ch_atividades_aprofundamento_cumprida, ch_atividades_extensao_cumprida, ch_pratica_como_componente_cumprida, ch_visita_tecnica_cumprida, percentual_ch_cumprida = (
            obj.get_ch_componentes_com_percentual_ch_cumprida()
        )

        total_ch_cumprida = (
            ch_componentes_regulares_obrigatorios_cumprida
            + ch_componentes_regulares_optativos_cumprida
            + ch_componentes_seminario_cumprida
            + ch_componentes_pratica_profissional_cumprida
            + ch_atividades_aprofundamento_cumprida
            + ch_atividades_extensao_cumprida
            + ch_componentes_tcc_cumprida
            + ch_atividades_complementares_cumprida
            + ch_pratica_como_componente_cumprida
            + ch_visita_tecnica_cumprida
        )

        if ch_componentes_eletivos_esperada:
            ch_componentes_eletivos_cumprida = obj.get_ch_componentes_eletivos_cumprida()
            total_ch_cumprida += ch_componentes_eletivos_cumprida

        # Pendente
        ch_componentes_regulares_obrigatorios_pendente = obj.get_ch_componentes_regulares_obrigatorios_pendente()
        ch_componentes_regulares_optativos_pendente = obj.get_ch_componentes_regulares_optativos_pendente()
        ch_componentes_eletivos_pendente = obj.get_ch_componentes_eletivos_pendente()
        ch_componentes_seminario_pendente = obj.get_ch_componentes_seminario_pendente()
        ch_componentes_pratica_como_componente_pendente = obj.get_ch_componentes_pratica_como_componente_pendente()
        ch_componentes_visita_tecnica_pendente = obj.get_ch_componentes_visita_tecnica_pendente()
        ch_componentes_pratica_profissional_pendente = obj.get_ch_componentes_pratica_profissional_pendente()
        ch_atividades_aprofundamento_pendente = obj.get_ch_atividade_aprofundamento_pendente()
        ch_atividades_extensao_pendente = obj.get_ch_atividade_extensao_pendente()
        ch_componentes_tcc_pendente = obj.get_ch_componentes_tcc_pendente()
        ch_atividades_complementares_pendente = obj.get_ch_atividades_complementares_pendente()
        total_ch_pendente = (
            ch_componentes_regulares_obrigatorios_pendente
            + ch_componentes_regulares_optativos_pendente
            + ch_componentes_eletivos_pendente
            + ch_componentes_seminario_pendente
            + ch_componentes_pratica_profissional_pendente
            + ch_atividades_aprofundamento_pendente
            + ch_atividades_extensao_pendente
            + ch_atividades_complementares_pendente
            + ch_componentes_pratica_como_componente_pendente
            + ch_componentes_visita_tecnica_pendente
        )

    # PEDIDOS DE MATRÍCULA
    pedidos_matricula = obj.get_pedidos_matricula()

    # PROJETOS DE EXTENSAO E PESQUISA
    if 'pesquisa' in settings.INSTALLED_APPS:
        ProjetoPesquisa = apps.get_model('pesquisa', 'Projeto')
        ParticipacaoPesquisa = apps.get_model('pesquisa', 'Participacao')
        participacoes_pesquisa = ParticipacaoPesquisa.objects.filter(vinculo_pessoa__id=obj.get_vinculo().id,
                                                                     projeto__aprovado=True)
        participacoes_projetos_pesquisa = ProjetoPesquisa.objects.filter(id__in=participacoes_pesquisa.values_list('projeto', flat=True))
    else:
        participacoes_projetos_pesquisa = []

    if 'projetos' in settings.INSTALLED_APPS:
        ProjetoExtensao = apps.get_model('projetos', 'Projeto')
        ParticipacaoExtensao = apps.get_model('projetos', 'Participacao')
        participacoes_extensao = ParticipacaoExtensao.objects.filter(vinculo_pessoa__id=obj.get_vinculo().id,
                                                                     projeto__aprovado=True)
        participacoes_projetos_extensao = ProjetoExtensao.objects.filter(id__in=participacoes_extensao.values_list('projeto', flat=True))
    else:
        participacoes_projetos_extensao = []

    qtd_participacoes_projetos = len(participacoes_projetos_pesquisa) + len(participacoes_projetos_extensao)

    # PASTA DOCUMENTAL
    total_aluno_arquivos = obj.alunoarquivo_set.count()
    if request.GET.get('tab') == 'pasta_documental':
        aluno_arquivos = obj.alunoarquivo_set.all()
        if aluno_arquivos.exists():
            for arquivo in aluno_arquivos:
                arquivo.pode_ser_deletado = arquivo.can_delete(request.user)

    # ESTAGIOS
    if request.GET.get('tab') == 'estagios':
        estagios = obj.praticaprofissional_set.all()

    qtd_estagios = (
        obj.praticaprofissional_set.all().count()
        + EstagioDocente.objects.filter(matricula_diario__matricula_periodo__aluno=obj).distinct().count()
        + obj.aprendizagem_set.all().count()
        + obj.atividadeprofissionalefetiva_set.count()
    )

    # ENADE
    pode_realizar_procedimentos_enade = perms.pode_realizar_procedimentos_enade(request.user, obj.curso_campus) and not obj.is_concluido()
    pode_realizar_dispensa_enade = in_group(request.user, 'Diretor de Avaliação e Regulação do Ensino') or (pode_realizar_procedimentos_enade and obj.pode_ser_dispensado_enade())
    convocacoes_enade = obj.get_convocacoes_enade()
    qtd_convocacoes_enade = convocacoes_enade.count()

    # LOCAIS/HORÁRIOS DE AULA
    eh_minicurso = obj.eh_aluno_minicurso()
    if request.GET.get('tab') == 'locais_aula_aluno' and not eh_minicurso:
        periodo_letivo_atual = PeriodoLetivoAtual.get_instance(request, obj)
        tipo = 'aluno'
        matriculas_periodo = obj.matriculaperiodo_set.filter(ano_letivo__ano=periodo_letivo_atual.ano, periodo_letivo=periodo_letivo_atual.periodo)
        if matriculas_periodo:
            matriculas_diario = matriculas_periodo[0].matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO)
            turnos = matriculas_periodo[0].get_horarios_aula_atividade_por_turno()
            atividades = matriculas_periodo[0].horarioatividadeextra_set.all().distinct('descricao_atividade')
            for atividade in atividades:
                atividade.horarios = atividade.get_horario_aulas()

    # ANOTAÇÕES INTERDISCIPLINARES - MÓDULO SAÚDE
    pode_ver_anotacoes_interdisciplinares = False
    if 'saude' in settings.INSTALLED_APPS:
        from saude.models import AnotacaoInterdisciplinar, Especialidades

        grupos_permitidos = Especialidades.GRUPOS
        grupos_permitidos.append('Pedagogo')
        pode_ver_anotacoes_interdisciplinares = request.user.groups.filter(name__in=grupos_permitidos)
        anotacoes_disciplinares = AnotacaoInterdisciplinar.objects.filter(prontuario__vinculo=obj.get_vinculo())

    # ETEP
    if 'etep' in settings.INSTALLED_APPS:
        Acompanhamento = apps.get_model('etep', 'Acompanhamento')
        acompanhamentos = Acompanhamento.locals.filter(aluno=obj)
    else:
        acompanhamenots = []

    # REQUERIMENTO
    requerimentos = Requerimento.objects.filter(aluno=obj).order_by('-data')

    # Histórico/Diploma eletrônico
    urls_diploma_historico = obj.get_url_historico_diploma()

    # Documentos, Processos e Protocolos vinculados ao Aluno via atributo Aluno.pessoa_fisica
    if 'processo_eletronico' in settings.INSTALLED_APPS and request.GET.get('tab') == 'documentos_processos':
        documentos_eletronicos = DocumentoTexto.get_documentos_por_pessoa_fisica(obj.pessoa_fisica)
        processos_eletronicos = Processo.get_processos_por_pessoa_fisica(obj.pessoa_fisica, filtrar_pessoa_por_tipo_vinculo=True)
        processos_fisicos = ProcessoProtocolo.get_protocolos_por_pessoa_fisica(obj.pessoa_fisica)

    return locals()


@rtr()
@login_required()
def progresso_ch_por_matriculaperiodo(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    series = []
    percentual_ch_cumprida = 0
    if aluno.matriz:
        for mp in aluno.get_matriculas_periodo(orderbyDesc=False):
            percentual_ch_cumprida = mp.percentual_ch_cumprida and float(mp.percentual_ch_cumprida) or 0
            series.append([f"{mp.ano_letivo.ano}.{mp.periodo_letivo}", percentual_ch_cumprida])

    grafico_evolucao_anual = LineChart('grafico', title='', data=series, groups=['C.H Cumprida (%)'])
    return locals()


@group_required('Administrador Acadêmico, edu Administrador, Secretário Acadêmico')
@rtr()
@login_required()
def desfazer_migracao(request, pk):
    obj = get_object_or_404(Aluno, pk=pk)
    title = f'Desfazer Migração de {obj.get_nome_social_composto()} ({obj.matricula})'
    enade = RegistroConvocacaoENADE.objects.filter(aluno=obj).count()
    projeto_final = ProjetoFinal.objects.filter(matricula_periodo__aluno=obj).count()
    matriculas_diarios = MatriculaDiario.objects.filter(matricula_periodo__aluno=obj).count()
    pedidos_matricula = PedidoMatricula.objects.filter(matricula_periodo__aluno=obj).count()
    procedimentos_matricula = ProcedimentoMatricula.objects.filter(matricula_periodo__aluno=obj).count()
    pode_desfazer_migracao_total = in_group(request.user, 'Administrador Acadêmico')
    if 'confirmar' in request.GET:
        if 'parcial' in request.GET:
            obj.desfazer_migracao_qacademico()
        else:
            if not pode_desfazer_migracao_total:
                return httprr('..', 'Você não possui permissão para isso.', 'error')
            obj.desfazer_migracao()
        return httprr('..', 'Procedimento realizado com sucesso.')

    return locals()


@group_required('Coordenador de Registros Acadêmicos, edu Administrador')
@rtr()
@login_required()
def editar_aluno(request, pk):
    aluno = get_object_or_404(
        Aluno,
        pk=pk,
        situacao__in=[
            SituacaoMatricula.CONCLUIDO,
            SituacaoMatricula.FORMADO,
            SituacaoMatricula.EVASAO,
            SituacaoMatricula.TRANCADO,
            SituacaoMatricula.FALECIDO,
            SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE,
            SituacaoMatricula.CANCELADO,
            SituacaoMatricula.CANCELAMENTO_COMPULSORIO,
            SituacaoMatricula.TRANSFERIDO_EXTERNO,
            SituacaoMatricula.JUBILADO,
        ],
    )
    title = 'Aluno'
    form = AlunoCRAForm(data=request.POST or None, files=request.FILES or None, instance=aluno)

    if form.is_valid():
        form.save()
        return httprr('..', 'Aluno atualizado com sucesso!')

    return locals()


@login_required()
@rtr()
def editar_situacao_matricula_periodo(request, pk):
    if not in_group(request.user, 'Administrador Acadêmico'):
        return httprr('.', 'Você não tem permissão para realizar isso.', 'error')

    obj = get_object_or_404(MatriculaPeriodo, pk=pk)
    title = f'Editar {obj}'
    form = SituacaoMatriculaPeriodoForm(obj, data=request.POST or None, instance=obj)

    if form.is_valid():
        form.processar()
        return httprr('..', 'Situação de matrícula período alterada com sucesso.')
    return locals()


@group_required('edu Administrador')
@rtr()
def editar_situacao_matricula(request, pk):
    obj = get_object_or_404(Aluno, pk=pk)
    title = f'Editar {obj}'
    form = SituacaoMatriculaForm(data=request.POST or None, instance=obj)

    if form.is_valid():
        form.processar()
        return httprr('..', 'Situação de matrícula do aluno alterada com sucesso.')
    return locals()


@group_required('Administrador Acadêmico,Diretor Acadêmico,Secretário Acadêmico')
@rtr()
def fechar_periodo_letivo(request):
    title = 'Fechar Período Letivo'
    acao = 'fechar_periodo_letivo'
    situacao_contraria = 'fechado'
    qtd_avaliacoes = 4
    form = FecharPeriodoLetivoForm(data=request.GET or None)

    if form.is_valid():
        if not 'finalize' in request.GET:
            return form.processar(request)
        if form.matriculas_periodo.exists():
            messages.info(request, 'Período letivo fechado com sucesso. Os alunos listados abaixo não foram processados por apresentarem alguma pendência.')
        else:
            return httprr('/edu/fechar_periodo_letivo/')
    matriculas_periodo = form.matriculas_periodo

    is_administrador = in_group(request.user, 'Administrador Acadêmico')
    if not is_administrador and not form.exibir_forcar_fechamento:
        if 'forcar_fechamento' in form.fields:
            form.fields['forcar_fechamento'].widget.attrs.update(disabled='disabled')

    return locals()


@group_required('Administrador Acadêmico,Diretor Acadêmico,Secretário Acadêmico')
@rtr('fechar_periodo_letivo.html')
def abrir_periodo_letivo(request):
    title = 'Abrir Período Letivo'
    acao = 'abrir_periodo_letivo'
    situacao_contraria = 'aberto'
    qtd_avaliacoes = 4
    form = AbrirPeriodoLetivoForm(data=request.GET or None)
    if form.is_valid():
        if not 'finalize' in request.GET:
            return form.processar(request)
        if form.matriculas_periodo.exists():
            messages.info(request, 'Período letivo aberto com sucesso. Os alunos listados abaixo não foram processados por apresentarem alguma pendência.')
        else:
            return httprr('/edu/abrir_periodo_letivo/')
    matriculas_periodo = form.matriculas_periodo
    return locals()


@rtr()
@login_required()
def meus_diarios(request, diarios=None):
    professor = get_object_or_404(Professor, vinculo__user=request.user)
    if diarios:
        try:
            professores_diario = ProfessorDiario.objects.filter(professor__vinculo__user=request.user, ativo=True, diario__id__in=diarios.split('_'))
        except Exception:
            return httprr('..', 'Diários inválidos.', 'error')
        title = f'Meus Diários Pendentes ({len(professores_diario)})'
    else:
        periodo_letivo_atual = PeriodoLetivoAtual.get_instance(request, professor)
        professores_diario = ProfessorDiario.objects.filter(professor__vinculo__user=request.user, ativo=True)
        professores_diario_anual = professores_diario.filter(
            diario__turma__curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL, diario__ano_letivo__ano=periodo_letivo_atual.ano
        )

        # excluíndo os diários semestrais em cursos anuais
        if periodo_letivo_atual.periodo == 1:
            professores_diario_anual = professores_diario_anual.exclude(diario__segundo_semestre=True)
        else:
            professores_diario_anual = professores_diario_anual.exclude(diario__segundo_semestre=False, diario__componente_curricular__qtd_avaliacoes=2)

        professores_diario_semestral = professores_diario.filter(
            diario__turma__curso_campus__periodicidade__in=[CursoCampus.PERIODICIDADE_SEMESTRAL, CursoCampus.PERIODICIDADE_LIVRE],
            diario__ano_letivo__ano=periodo_letivo_atual.ano,
            diario__periodo_letivo=periodo_letivo_atual.periodo,
        )
        professores_diario = (professores_diario_anual | professores_diario_semestral).order_by('diario__turma__curso_campus', 'diario__turma', 'diario')
        diarios_especiais = professor.diarioespecial_set.filter(ano_letivo__ano=periodo_letivo_atual.ano, periodo_letivo=periodo_letivo_atual.periodo)
        qtd_diarios = professores_diario.count() + diarios_especiais.count()
        title = f'Meus Diários ({qtd_diarios})'
    return locals()


@group_required(
    'Administrador Acadêmico,Diretor Acadêmico,Coordenador de Curso, Coordenador de Modalidade Acadêmica,Secretário Acadêmico,Pedagogo,Coordenador de Polo EAD, Visualizador de Informações Acadêmicas, Auditor,Apoio Acadêmico,Membro ETEP'
)
@rtr()
@login_required()
def configuracao_avaliacao(request, pk):
    obj = get_object_or_404(ConfiguracaoAvaliacao, pk=pk)
    title = obj.__str__()
    return locals()


@rtr()
@login_required()
def replicar_configuracao_avaliacao(request, pk):
    obj = get_object_or_404(ConfiguracaoAvaliacao, pk=pk)
    title = 'Replicação de Configuração de Avaliação'
    form = ReplicacaoConfiguracaoAvaliacaoForm(obj, data=request.POST or None)
    if request.POST and form.is_valid():
        try:
            resultado = form.processar()
            return httprr(f'/edu/configuracao_avaliacao/{resultado.id}/', 'Configuração de Avaliação replicada com sucesso.')
        except ValidationError as e:
            return httprr('..', f'Não foi possível replicar a configuração de avaliação: {e.messages[0]}', 'error')
    return locals()


def get_estatisticas_diario(obj):
    estatisticas = {}
    estatisticas['alunos_aprovados'] = MatriculaDiario.objects.filter(diario=obj, situacao=MatriculaDiario.SITUACAO_APROVADO).count()
    estatisticas['alunos_reprovados'] = MatriculaDiario.objects.filter(diario=obj, situacao=MatriculaDiario.SITUACAO_REPROVADO).count()
    estatisticas['alunos_prova_final'] = MatriculaDiario.objects.filter(diario=obj, situacao=MatriculaDiario.SITUACAO_PROVA_FINAL).count()
    estatisticas['alunos_tcdt'] = MatriculaDiario.objects.filter(
        diario=obj, situacao__in=[MatriculaDiario.SITUACAO_TRANCADO, MatriculaDiario.SITUACAO_CANCELADO, MatriculaDiario.SITUACAO_DISPENSADO, MatriculaDiario.SITUACAO_TRANSFERIDO]
    ).count()
    estatisticas['alunos_pendentes'] = MatriculaDiario.objects.filter(diario=obj, situacao=MatriculaDiario.SITUACAO_PENDENTE).count()
    estatisticas['alunos_reprovados_por_falta'] = len(
        [matricula_diario for matricula_diario in obj.matriculadiario_set.all() if matricula_diario.get_situacao_diario()['rotulo'] == 'Reprov. por Falta']
    )
    estatisticas['alunos_aprovados_reprovados_modulo'] = MatriculaDiario.objects.filter(diario=obj, situacao=MatriculaDiario.SITUACAO_APROVADO_REPROVADO_MODULO).count()
    if obj.componente_curricular.qtd_avaliacoes > 0:
        nomes_etapa = list(x for x in range(1, obj.componente_curricular.qtd_avaliacoes + 1))
        etapas_estatistica = list()
        for nome_etapa in nomes_etapa:
            search_field = f'nota_{nome_etapa}'
            pks = (
                NotaAvaliacao.objects.filter(nota__isnull=False, matricula_diario__diario=obj, item_configuracao_avaliacao__configuracao_avaliacao__etapa=nome_etapa)
                .values_list('matricula_diario', flat=True)
                .order_by('matricula_diario')
                .distinct()
            )
            matriculas_consideradas = MatriculaDiario.objects.filter(pk__in=pks)
            variancia = matriculas_consideradas.aggregate(Variance(search_field))[f'{search_field}__variance']
            etapa_estatistica = {
                'nome': nome_etapa,
                'media': obj.get_media_notas_by_etapa(nome_etapa),
                'desvio': variancia and math.sqrt(variancia) or variancia,
                'maior_nota': matriculas_consideradas.aggregate(Max(search_field))[f'{search_field}__max'],
                'menor_nota': matriculas_consideradas.aggregate(Min(search_field))[f'{search_field}__min'],
            }
            etapas_estatistica.append(etapa_estatistica)

        estatisticas['etapas_estatistica'] = etapas_estatistica

        valores = []
        for matricula_diario in obj.matriculadiario_set.all():
            mfd = matricula_diario.get_media_final_disciplina()
            if mfd is not None:
                valores.append(mfd)

        if valores:
            media_mfd = sum(valores) / float(len(valores))
            desvio_mfd = math.sqrt(sum((media_mfd - value) ** 2 for value in valores) / len(valores))
            menor_mfd = min(valores)
            maior_mfd = max(valores)
        else:
            media_mfd, desvio_mfd, menor_mfd, maior_mfd = None, None, None, None

        estatisticas['media_mfd'] = media_mfd
        estatisticas['desvio_mfd'] = desvio_mfd
        estatisticas['menor_mfd'] = menor_mfd
        estatisticas['maior_mfd'] = maior_mfd
    return estatisticas


@rtr()
@login_required()
def configurar_ambiente_virtual_diario(request, pk):
    title = 'Configurar Ambiente Virtual'
    obj = get_object_or_404(Diario.locals, pk=pk)
    form = ConfigurarAmbienteVirtualDiarioForm(data=request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Configuração realizada com sucesso')
    return locals()


@rtr()
@login_required()
def meu_diario(request, diario_pk, etapa=0, polo_pk=None):
    NOTA_DECIMAL = settings.NOTA_DECIMAL
    CASA_DECIMAL = settings.CASA_DECIMAL
    MULTIPLICADOR_DECIMAL = NOTA_DECIMAL and CASA_DECIMAL == 1 and 10 or 100
    obj = get_object_or_404(Diario.locals, pk=diario_pk)

    solicitacoes_lab_fisico = None
    solicitacoes_lab_virtual = None

    labfisico_installed = 'labfisico' in settings.INSTALLED_APPS
    labvirtual_installed = 'labvirtual' in settings.INSTALLED_APPS

    if labfisico_installed:
        SolicitacaoLabFisico = apps.get_model('labfisico', 'SolicitacaoLabFisico')
        solicitacoes_lab_fisico = SolicitacaoLabFisico.objects.filter(diario=obj)
    #
    if labvirtual_installed:
        SolicitacaoLabVirtual = apps.get_model('labvirtual', 'SolicitacaoLabVirtual')
        solicitacoes_lab_virtual = SolicitacaoLabVirtual.objects.filter(diario=obj)

    if 'moodle' in request.GET and obj.integracao_com_moodle:
        try:
            url = moodle.sincronizar(obj)
            obj.url_moodle = url
            obj.save()
            return httprr('.', f'Dados enviados com sucesso! A URL de acesso para o ambiente virtual é: {url}')
        except BaseException as e:
            return httprr('.', f'Problemas ao enviar os dados para o Moodle: {e}', tag='error')

    etapa = int(etapa)
    if etapa == 0:
        return httprr(f'/edu/meu_diario/{obj.pk}/{obj.get_num_etapa_posse_professor()}/')
    if etapa > 5 or etapa < 1:
        return httprr('/edu/meus_diarios/', 'Escolha uma Etapa Válida', 'error')
    etapa_str = obj.get_label_etapa(etapa)
    descricao_etapa = f'Etapa {etapa_str}'
    title = f'{str(obj)} - {descricao_etapa}'
    is_fic = obj.estrutura_curso.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_FIC
    tab = request.GET.get('tab', '')

    MATRICULADO = SituacaoMatriculaPeriodo.MATRICULADO
    qtd_avaliacoes = obj.componente_curricular.qtd_avaliacoes
    professor_diario = get_object_or_404(obj.professordiario_set, professor__vinculo__user=request.user)
    if not professor_diario.ativo:
        return httprr('/edu/meus_diarios/', f'Vínculo com o diário {diario_pk} inativo', 'error')
    materiais_professor = professor_diario.materialdiario_set.all().order_by('-data_vinculacao')
    materias_outros = (
        MaterialDiario.objects.filter(professor_diario__diario=obj).exclude(id__in=materiais_professor.values_list("id", flat=True)).order_by('-material_aula__data_cadastro')
    )
    data_atual = datetime.date.today()

    q = request.GET.get('q')
    if q:
        materiais_professor = materiais_professor.filter(material_aula__descricao__unaccent__icontains=q)
        materias_outros = materias_outros.filter(material_aula__descricao__unaccent__icontains=q)

    if request.GET.get('xls'):
        response = HttpResponse(content_type='application/ms-excel')
        response['Content-Disposition'] = 'attachment; filename=meu_diario.xls'

        wb = xlwt.Workbook(encoding='utf-8')
        sheet1 = wb.add_sheet('Dados Gerais')
        sheet2 = wb.add_sheet('Registros de Aulas')

        rows_agrupada = []
        cabecalho = ['#', 'Matrícula', 'Nome', 'T. Faltas', '%Freq', 'Situação']
        for avaliacao in range(1, obj.componente_curricular.qtd_avaliacoes + 1):
            cabecalho.append(f'Nota Etapa {avaliacao}')
            cabecalho.append(f'Falta Etapa {avaliacao}')
        cabecalho += ['MD', 'Nota Etapa Final', 'MFD/Conceito']
        rows_agrupada.append(cabecalho)
        count = 0

        for matricula_diario in obj.matriculadiario_set.all():
            count += 1
            row = [
                format_(count),
                format_(matricula_diario.matricula_periodo.aluno.matricula),
                format_(normalizar_nome_proprio(matricula_diario.matricula_periodo.aluno.get_nome_social_composto())),
                format_(matricula_diario.get_numero_faltas()),
                format_(matricula_diario.get_percentual_carga_horaria_frequentada()),
                format_(matricula_diario.get_situacao_diario()['rotulo']),
            ]
            if matricula_diario.diario.componente_curricular.qtd_avaliacoes > 0:
                row.append(format_(matricula_diario.get_nota_1_boletim()))
                row.append(format_(matricula_diario.get_numero_faltas_primeira_etapa()))
            if matricula_diario.diario.componente_curricular.qtd_avaliacoes > 1:
                row.append(format_(matricula_diario.get_nota_2_boletim()))
                row.append(format_(matricula_diario.get_numero_faltas_segunda_etapa()))
            if matricula_diario.diario.componente_curricular.qtd_avaliacoes > 2:
                row.append(format_(matricula_diario.get_nota_3_boletim()))
                row.append(format_(matricula_diario.get_numero_faltas_terceira_etapa()))
                row.append(format_(matricula_diario.get_nota_4_boletim()))
                row.append(format_(matricula_diario.get_numero_faltas_quarta_etapa()))
            if matricula_diario.diario.componente_curricular.qtd_avaliacoes > 0:
                row.append(format_(matricula_diario.get_media_disciplina_boletim()))
                row.append(format_(matricula_diario.get_nota_final_boletim()))
                row.append(format_(matricula_diario.get_media_final_disciplina_boletim()))
            rows_agrupada.append(row)

        for row_idx, row in enumerate(rows_agrupada):
            row = [i for i in row]
            for col_idx, col in enumerate(row):
                sheet1.write(row_idx, col_idx, label=col)

        rows_agrupada = [['#', 'Etapa', 'Qtd.', 'Data', 'Professor', 'Conteúdo']]
        count = 0

        for aula in obj.get_aulas():
            count += 1
            row = [format_(count), format_(aula.etapa), format_(aula.quantidade), format_(aula.data), format_(str(aula.professor_diario.professor)), format_(aula.conteudo)]
            rows_agrupada.append(row)

        for row_idx, row in enumerate(rows_agrupada):
            row = [i for i in row]
            for col_idx, col in enumerate(row):
                sheet2.write(row_idx, col_idx, label=col)

        wb.save(response)
        return response

    em_posse_do_registro = obj.em_posse_do_registro(etapa)
    etapas_anteriores_entegues = obj.etapas_anteriores_entegues(etapa)

    qtd_professores = obj.professordiario_set.filter(ativo=True).count()
    pode_lancar_nota = obj.estrutura_curso.pode_lancar_nota_fora_do_prazo

    pode_manipular_etapa_1 = (
        etapa == 1
        and professor_diario.ativo
        and not em_posse_do_registro
        and (
            qtd_professores == 1
            or pode_lancar_nota
            or (
                professor_diario.data_inicio_etapa_1
                and professor_diario.data_fim_etapa_1
                and data_atual >= professor_diario.data_inicio_etapa_1
                and data_atual <= professor_diario.data_fim_etapa_1
            )
        )
    )
    pode_manipular_etapa_2 = (
        etapa == 2
        and professor_diario.ativo
        and not em_posse_do_registro
        and (
            qtd_professores == 1
            or pode_lancar_nota
            or (
                professor_diario.data_inicio_etapa_2
                and professor_diario.data_fim_etapa_2
                and data_atual >= professor_diario.data_inicio_etapa_2
                and data_atual <= professor_diario.data_fim_etapa_2
            )
        )
    )
    pode_manipular_etapa_3 = (
        etapa == 3
        and professor_diario.ativo
        and not em_posse_do_registro
        and (
            qtd_professores == 1
            or pode_lancar_nota
            or (
                professor_diario.data_inicio_etapa_3
                and professor_diario.data_fim_etapa_3
                and data_atual >= professor_diario.data_inicio_etapa_3
                and data_atual <= professor_diario.data_fim_etapa_3
            )
        )
    )
    pode_manipular_etapa_4 = (
        etapa == 4
        and professor_diario.ativo
        and not em_posse_do_registro
        and (
            qtd_professores == 1
            or pode_lancar_nota
            or (
                professor_diario.data_inicio_etapa_4
                and professor_diario.data_fim_etapa_4
                and data_atual >= professor_diario.data_inicio_etapa_4
                and data_atual <= professor_diario.data_fim_etapa_4
            )
        )
    )
    pode_manipular_etapa_5 = (
        etapa == 5
        and professor_diario.ativo
        and not em_posse_do_registro
        and (
            qtd_professores == 1
            or pode_lancar_nota
            or (
                professor_diario.data_inicio_etapa_final
                and professor_diario.data_fim_etapa_final
                and data_atual >= professor_diario.data_inicio_etapa_final
                and data_atual <= professor_diario.data_fim_etapa_final
            )
        )
    )

    configuracao_avaliacao_selecionada = getattr(obj, f'configuracao_avaliacao_{etapa}')()

    if etapa == 1:
        inicio_etapa = professor_diario.data_inicio_etapa_1
        fim_etapa = professor_diario.data_fim_etapa_1
        pode_manipular_etapa = pode_manipular_etapa_1
    if etapa == 2:
        inicio_etapa = professor_diario.data_inicio_etapa_2
        fim_etapa = professor_diario.data_fim_etapa_2
        pode_manipular_etapa = pode_manipular_etapa_2
    if etapa == 3:
        inicio_etapa = professor_diario.data_inicio_etapa_3
        fim_etapa = professor_diario.data_fim_etapa_3
        pode_manipular_etapa = pode_manipular_etapa_3
    if etapa == 4:
        inicio_etapa = professor_diario.data_inicio_etapa_4
        fim_etapa = professor_diario.data_fim_etapa_4
        pode_manipular_etapa = pode_manipular_etapa_4
    if etapa == 5:
        inicio_etapa = professor_diario.data_inicio_etapa_final
        fim_etapa = professor_diario.data_fim_etapa_final
        pode_manipular_etapa = pode_manipular_etapa_5

    solicitacao_prorrogacao_pendente = SolicitacaoProrrogacaoEtapa.locals.pendentes().filter(professor_diario=professor_diario, etapa=etapa).exists()

    # exibição das etapas
    etapas = dict()
    for numero_etapa in obj.get_lista_etapas():
        dados_etapa = obj.get_etapas().get(numero_etapa)

        if obj.is_semestral_segundo_semestre() and numero_etapa in [1, 2]:
            dados_etapa.update(numero_etapa_exibicao=numero_etapa + 2)

        dados_etapa.update(inicio_etapa=getattr(obj.calendario_academico, 'data_inicio_etapa_{}'.format(dados_etapa['numero_etapa_exibicao'])))
        dados_etapa.update(fim_etapa=getattr(obj.calendario_academico, 'data_fim_etapa_{}'.format(dados_etapa['numero_etapa_exibicao'])))
        dados_etapa.update(inicio_posse=getattr(professor_diario, f'data_inicio_etapa_{numero_etapa}'))
        dados_etapa.update(fim_posse=getattr(professor_diario, f'data_fim_etapa_{numero_etapa}'))
        dados_etapa.update(qtd_aulas=obj.get_aulas(numero_etapa).exclude(data__gt=datetime.datetime.now()).aggregate(Sum('quantidade'))['quantidade__sum'])
        etapas.update({numero_etapa: dados_etapa})

    dados_etapa_5 = obj.get_etapas().get(5)
    dados_etapa_5.update(inicio_etapa=obj.get_inicio_etapa_final())
    dados_etapa_5.update(fim_etapa=obj.get_fim_etapa_final())
    dados_etapa_5.update(inicio_posse=professor_diario.data_inicio_etapa_final)
    dados_etapa_5.update(fim_posse=professor_diario.data_fim_etapa_final)
    dados_etapa_5.update(qtd_aulas=obj.get_aulas(5).exclude(data__gt=datetime.datetime.now()).aggregate(Sum('quantidade'))['quantidade__sum'])
    etapas.update({'Final': dados_etapa_5})

    aulas = obj.get_aulas(etapa)
    qtd_aulas_passadas = 0
    for aula in aulas:
        if aula.data <= data_atual:
            qtd_aulas_passadas += 1

    acesso_total = True
    materiais_aula = professor_diario.professor.materialaula_set
    if not professor_diario and not in_group(
        request.user, 'Administrador Acadêmico,Diretor Acadêmico,Coordenador de Curso, Coordenador de Modalidade Acadêmica,Secretário Acadêmico,Pedagogo'
    ):
        raise PermissionDenied()

    polos = obj.get_polos()
    if polo_pk is None:
        polo_pk = polos and polos.first().pk or None
    else:
        polo_pk = int(polo_pk)
    matriculas_diario_por_polo = obj.get_matriculas_diario_por_polo(polo_pk)

    if request.method == 'POST':

        if 'lancamento_nota' in request.POST:
            url = f'/edu/meu_diario/{obj.pk}/{etapa}/?tab=notas'
            try:
                if running_tests():
                    obj.processar_notas(request.POST)
                return httprr(url, 'Notas registradas com sucesso.', anchor='etapa')
            except Exception as e:
                return httprr(url, str(e), 'error', anchor='etapa')

    if tab == 'faltas':
        polos = obj.get_polos()
        boxes_matriculas = []
        for matriculas in matriculas_diario_por_polo:
            for matricula_diario in matriculas:
                matricula_diario.set_faltas(aulas)
            boxes_matriculas.append(matriculas)

    possui_solicitacao_pendente = SolicitacaoRelancamentoEtapa.objects.filter(etapa=etapa, professor_diario=professor_diario, data_avaliacao__isnull=True).exists()
    possui_solicitacao_prorrogacao_pendente = SolicitacaoProrrogacaoEtapa.objects.filter(etapa=etapa, professor_diario=professor_diario, data_avaliacao__isnull=True).exists()

    topicos = obj.topicodiscussao_set.filter(etapa=etapa)
    trabalhos = obj.trabalho_set.filter(etapa=etapa)

    if tab == 'aulas' or tab == '':
        if inicio_etapa and fim_etapa:
            calendario = Calendario()
            for aula in aulas:
                calendario.adicionar_evento_calendario(aula.data, aula.data, f'{aula.conteudo} ({aula.quantidade} aulas)', 'success', aula.conteudo)
            calendario_diario = calendario.formato_periodo(inicio_etapa.month, inicio_etapa.year, fim_etapa.month, fim_etapa.year)

    if tab == 'estatisticas':
        estatisticas = get_estatisticas_diario(obj)
        if obj.turma.matriz.estrutura.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_NOTA:
            # plano de retomada de aulas em virtude da pandemia (COVID19)
            media_aprovacao_avaliacao_final = obj.turma.pertence_ao_plano_retomada and 50 or obj.turma.matriz.estrutura.media_aprovacao_avaliacao_final
            estatisticas['alunos_acima_da_media'] = MatriculaDiario.objects.filter(
                **{
                    'diario': obj,
                    f'nota_{etapa_str}__gt'.lower(): obj.turma.matriz.estrutura.media_aprovacao_sem_prova_final
                    if etapa != 5
                    else media_aprovacao_avaliacao_final,
                }
            ).count()
            estatisticas['alunos_na_media'] = MatriculaDiario.objects.filter(
                **{
                    'diario': obj,
                    f'nota_{etapa_str}'.lower(): obj.turma.matriz.estrutura.media_aprovacao_sem_prova_final
                    if etapa != 5
                    else media_aprovacao_avaliacao_final,
                }
            ).count()
            estatisticas['alunos_abaixo_da_media'] = MatriculaDiario.objects.filter(
                **{
                    'diario': obj,
                    f'nota_{etapa_str}__lt'.lower(): obj.turma.matriz.estrutura.media_aprovacao_sem_prova_final
                    if etapa != 5
                    else media_aprovacao_avaliacao_final,
                }
            ).count()
        else:
            estatisticas['alunos_acima_da_media'] = '-'
            estatisticas['alunos_na_media'] = '-'
            estatisticas['alunos_abaixo_da_media'] = '-'

    exibir_todos_alunos = not obj.matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO).exists()
    return locals()


@rtr()
@login_required()
def entregar_etapa(request, diario, etapa):
    obj = get_object_or_404(Diario.locals, pk=diario)
    qs = obj.matriculadiario_set.filter(nota_final__isnull=False).distinct()
    if qs.exists():
        for matricula_diario in qs:
            if (
                NotaAvaliacao.objects.filter(matricula_diario=matricula_diario, item_configuracao_avaliacao__configuracao_avaliacao__etapa=5, nota__isnull=False).exists()
                and not matricula_diario.is_em_prova_final()
            ):
                return httprr(
                    f'/edu/meu_diario/{diario}/{etapa}/?tab=notas',
                    f'Etapa não pode ser entregue porque a nota da prova final de {matricula_diario.matricula_periodo.aluno} esta inconsistente.',
                    tag='error', close_popup=True
                )

    qs = obj.matriculadiario_set.filter(
        situacao=MatriculaDiario.SITUACAO_CURSANDO, notaavaliacao__nota__isnull=True, notaavaliacao__item_configuracao_avaliacao__configuracao_avaliacao__etapa=etapa
    ).distinct()
    pode_entregar_sem_aula = False
    if etapa == 5:
        title = 'Entregar Etapa Final'
        ids = []
        for md in qs:
            if md.get_situacao_nota()['constant'] != MatriculaDiario.SITUACAO_PROVA_FINAL:
                ids.append(md.id)
        qs = qs.exclude(id__in=ids)
    else:
        title = f'Entregar Etapa {etapa}'
        pode_entregar_sem_aula = not obj.get_aulas(etapa) and obj.estrutura_curso.pode_entregar_etapa_sem_aula

    tem_nota_vazia = qs.exists()

    form = EntregaEtapaForm(data=request.POST or None, tem_nota_vazia=tem_nota_vazia, pode_entregar_sem_aula=pode_entregar_sem_aula)
    if form.is_valid():
        try:
            zerar_notas = form.cleaned_data['zerar_notas']
            obj.entregar_etapa_como_professor(etapa, zerar_notas)
        except Exception as e:
            return httprr(f'/edu/meu_diario/{diario}/{etapa}/', str(e), 'error', close_popup=True)
        return httprr(f'/edu/meu_diario/{diario}/{etapa}/', 'Etapa entregue com sucesso.', close_popup=True)
    return locals()


@rtr()
@login_required()
def solicitar_relancamento_etapa(request, professor_diario_pk, etapa):
    title = 'Solicitar Relaçamento de Etapa'
    professor_diario = get_object_or_404(ProfessorDiario, pk=professor_diario_pk)
    form = SolicitarRelancamentoEtapaForm(data=request.POST or None, professor_diario=professor_diario, etapa=etapa)

    if not professor_diario.ativo:
        return httprr('/edu/meus_diarios/', f'Vínculo com o diário {professor_diario.diario} inativo', 'error')

    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.', anchor='etapa')
    return locals()


@rtr()
@login_required()
def solicitar_prorrogacao_etapa(request, professor_diario_pk, etapa):
    title = 'Solicitar Prorrogação de Etapa'
    professor_diario = get_object_or_404(ProfessorDiario, pk=professor_diario_pk)
    form = SolicitarProrrogacaoEtapaForm(data=request.POST or None, professor_diario=professor_diario, etapa=etapa)

    if not professor_diario.ativo:
        return httprr('/edu/meus_diarios/', f'Vínculo com o diário {professor_diario.diario} inativo', 'error')

    if form.is_valid():
        form.save()
        return httprr('..', 'Solicitação enviada com sucesso. Assim que sua solicitação for avaliada, você será notificado por e-mail.', anchor='etapa')
    return locals()


@rtr()
@permission_required('edu.add_materialaula')
def importar_materiais_aula(request):
    title = 'Importar Materiais de Aula'
    professor = Professor.objects.filter(vinculo=request.user.get_vinculo()).first()
    form = ImportarMaterialAulaForm(professor, data=request.POST or None, request=request)
    if form.is_valid():
        form.processar()
        return httprr('/admin/edu/materialaula/', 'Materiais importados com sucesso.')
    return locals()


@rtr()
@permission_required('edu.add_materialaula')
def adicionar_materiais_aula(request):
    title = 'Adicionar Materiais de Aula'

    form = MateriaisAulaForm(request.POST or None, request=request, files=request.POST and request.FILES or None)

    if form.is_valid():
        notificar, diarios, materiais = form.processar()
        if notificar:
            materiais_str = []
            for material in materiais:
                materiais_str.append("\n\t- " + material.descricao)

            for diario in diarios:
                matriculas_diarios = MatriculaDiario.objects.filter(diario=diario)
                if matriculas_diarios.exists():
                    disciplina = diario.componente_curricular.componente.descricao
                    emails = []
                    for matricula in matriculas_diarios:
                        if matricula.matricula_periodo.aluno.pessoa_fisica.email:
                            emails.append(matricula.matricula_periodo.aluno.pessoa_fisica.email)

                    mensagem = """
        Caro(a) aluno(a),

        Informamos que foi vinculado um novo material à disciplina {}:
        {}

                    """.format(
                        disciplina, "".join(materiais_str)
                    )

                    send_mail(
                        f'[SUAP] Envio de Material - {disciplina}',
                        mensagem,
                        settings.DEFAULT_FROM_EMAIL,
                        [],
                        bcc=emails,
                        fail_silently=True
                    )
        return httprr('..', 'Materiais de aula adicionados com sucesso.')
    return locals()


@rtr()
@login_required()
def materiais_diario(request, pk, etapa):
    professor_diario = get_object_or_404(ProfessorDiario, pk=pk)
    is_proprio_professor = professor_diario.professor.vinculo.user.username == request.user.username

    if not is_proprio_professor and not in_group(
        request.user, 'Administrador Acadêmico,Diretor Acadêmico,Coordenador de Curso,Coordenador de Modalidade Acadêmica,Secretário Acadêmico,Pedagogo'
    ):
        raise PermissionDenied()

    disciplina = professor_diario.diario.componente_curricular.componente.descricao
    title = f'Materiais de Aula do Diário - {disciplina}'
    form = VincularMaterialAulaForm(request.POST or None, request=request, professor_diario=professor_diario)
    if form.is_valid():
        form.save(etapa)
        matriculas_diarios = MatriculaDiario.objects.filter(diario__professordiario=professor_diario)
        if matriculas_diarios.exists():
            emails = []
            for matricula in matriculas_diarios:
                if matricula.matricula_periodo.aluno.pessoa_fisica.email:
                    emails.append(matricula.matricula_periodo.aluno.pessoa_fisica.email)

            materiais = []
            for material in form.cleaned_data['materiais_aula']:
                materiais.append("\n\t- " + material.descricao)

            mensagem = """
Caro(a) aluno(a),

Informamos que foi vinculado um novo material à disciplina {}:
{}

            """.format(
                disciplina, "".join(materiais)
            )

            send_mail(
                f'[SUAP] Envio de Material - {disciplina}',
                mensagem,
                settings.DEFAULT_FROM_EMAIL,
                [],
                bcc=emails,
                fail_silently=True
            )
        return httprr('..', 'Material vinculado com sucesso.', anchor='etapa')
    return locals()


def alunos_ws(request):
    """WebService criado para o EAD"""
    if 'ponto' in settings.INSTALLED_APPS:
        Maquina = apps.get_model('ponto', 'Maquina')
        try:
            get_object_or_404(Maquina, ip=get_client_ip(request), cliente_ponto=True, ativo=True)
        except Maquina.DoesNotExist:
            raise PermissionDenied('Máquina sem permissões.')
    else:
        raise PermissionDenied('Máquina sem permissões.')

    if 'alunos_qs' in cache:
        return cache.get('alunos_qs')

    def aluno_to_dict(aluno):
        return dict(
            nome=aluno.get_nome_social_composto(),
            email=aluno.pessoa_fisica.email_secundario,
            matricula=aluno.matricula,
            curso=str(aluno.curso_campus),
            campus=str(aluno.curso_campus.diretoria.setor.uo.sigla),
        )

    campus_sigla = request.GET.get('campus', '')
    alunos_qs = Aluno.objects.filter(situacao__ativo=True, curso_campus__diretoria__setor__uo__sigla__iexact=campus_sigla)[0:20]
    alunos = [aluno_to_dict(a) for a in alunos_qs]
    response = JsonResponse(alunos)
    cache.set('alunos_qs', response, 60 * 60 * 12)
    return response


# utilizado pelo sistema da saúde


def exportar_alunos_academico(request, matricula):
    nome_aluno = ''
    try:
        aluno = get_object_or_404(Aluno, matricula__iexact=matricula)
        if aluno.situacao.ativo:
            nome_aluno = aluno.pessoa_fisica.nome
    except Exception:
        pass
    return HttpResponse(nome_aluno)


@rtr()
@login_required()
@permission_required('edu.gerar_relatorio')
def relatorio(request):
    title = 'Listagem de Alunos'
    tabela = None
    quantidade_itens = 25

    form = RelatorioForm(request, data=request.GET or None)
    if 'editar' in request.GET:
        formatacao = None
    else:
        if form.is_valid():
            exibicao_choices = form.EXIBICAO_CHOICES + RelatorioForm.PENDENCIAS_EXIBICAO_CHOICES + form.EXIBICAO_COMUNICACAO + form.EXIBICAO_DADOS_PESSOAIS
            ano_letivo = form.cleaned_data.get('ano_letivo')
            periodo_letivo = int(form.cleaned_data.get('periodo_letivo', 0) or 0)
            query_string = request.META.get('QUERY_STRING', '').encode("utf-8").hex()
            alunos = form.processar()
            alunos_list = request.POST.getlist('select_aluno')
            quantidade_itens = form.cleaned_data['quantidade_itens']
            if alunos_list:
                filtros = alunos.filtros
                alunos = Aluno.objects.filter(id__in=alunos_list)
                alunos.filtros = filtros
            formatacao = form.cleaned_data['formatacao']
            if formatacao == 'educacenso':
                for aluno in alunos:
                    qs = MatriculaPeriodo.objects.filter(aluno=aluno).order_by('-ano_letivo__ano', '-periodo_letivo')
                    if periodo_letivo not in [None, '', '0', 0]:
                        qs = qs.filter(periodo_letivo=periodo_letivo)
                    if ano_letivo:
                        qs = qs.filter(ano_letivo=ano_letivo)
                    if qs:
                        aluno.matricula_periodo = qs[0]
            elif formatacao == 'censup':
                for aluno in alunos:
                    qs = MatriculaPeriodo.objects.filter(aluno=aluno).order_by('-ano_letivo__ano', '-periodo_letivo')
                    if periodo_letivo not in [None, '', '0', 0]:
                        qs = qs.filter(periodo_letivo=periodo_letivo)
                    if ano_letivo:
                        qs = qs.filter(ano_letivo=ano_letivo)
                    if qs:
                        aluno.matricula_periodo = qs[0]
            elif formatacao == 'pordisciplinacursando' or formatacao == 'pordisciplinapendente':
                filtros = alunos.filtros
                alunos = alunos.filter(matriz__isnull=False)
                alunos.filtros = filtros
            elif formatacao == 'tcc':
                filtros = alunos.filtros
                alunos = alunos.filter(matriculaperiodo__projetofinal__isnull=False)
                alunos.filtros = filtros

            filtros = alunos.filtros
            agrupamento = form.cleaned_data['agrupamento']

            campos_exibicao = form.cleaned_data['exibicao']
            if (ano_letivo and not periodo_letivo) or (periodo_letivo and not ano_letivo):
                if 'get_situacao_periodo_referencia' in campos_exibicao:
                    campos_exibicao.remove('get_situacao_periodo_referencia')
                if 'get_frequencia_periodo_referencia' in campos_exibicao:
                    campos_exibicao.remove('get_frequencia_periodo_referencia')
            if 'pendencias' in campos_exibicao:
                campos_exibicao.remove('pendencias')
                for chave, valor in RelatorioForm.PENDENCIAS_EXIBICAO_CHOICES:
                    campos_exibicao.append(chave)

            if 'imprimir' in request.POST:
                return relatorio_pdf(request, alunos, formatacao, campos_exibicao)
            if 'etiquetas' in request.POST:
                etiquetas = request.POST['etiquetas']
                return etiquetas_alunos_pdf(request, alunos, etiquetas)
            if 'assinaturas' in request.POST:
                return assinaturas_alunos_pdf(request, alunos, agrupamento)
            if 'carometros' in request.POST:
                return carometros_alunos_pdf(request, alunos)
            if 'xls' in request.POST and tabela:
                rows = [tabela.colunas]
                for registro in tabela.registros:
                    row = []
                    for key in registro:
                        row.append(registro[key])
                    rows.append(row)
                return XlsResponse(rows)

            if 'xls' in request.POST:
                if formatacao == 'educacenso':
                    return tasks.relatorio_educacenso_xls(alunos, ano_letivo, periodo_letivo)
                elif formatacao == 'censup':
                    return tasks.relatorio_censup_xls(alunos, ano_letivo, periodo_letivo)
                elif formatacao == 'pordisciplinapendente':
                    return tasks.relatorio_pordisciplinapendente_xls(alunos)
                elif formatacao == 'pordisciplinacursando':
                    return tasks.relatorio_pordisciplinacursando_xls(alunos)
                elif formatacao == 'tcc':
                    return tasks.relatorio_tcc_xls(alunos)
                # Se for qualquer outra formatação
                else:
                    cabecalhos = exibicao_choices
                    return tasks.exportar_listagem_alunos_xls(alunos, ano_letivo, periodo_letivo, filtros, campos_exibicao, cabecalhos)

    return locals()


@rtr()
@login_required()
@permission_required('ponto.pode_ver_frequencia_propria')
def relatorio_professor(request):
    title = 'Listagem de Professores'
    pode_ver_endereco = pode_ver_endereco_professores(request.user)
    form = RelatorioProfessorForm(data=request.GET or None, pode_ver_endereco=pode_ver_endereco)
    exibir_botao_executar = HistoricoRelatorio.objects.filter(user=request.user, tipo=HistoricoRelatorio.TIPO_PROFESSOR).exists()
    if form.is_valid():
        query_string = request.META.get('QUERY_STRING', '').encode("utf-8").hex()
        professores = form.processar()
        filtros = professores.filtros
        campos_exibicao = form.cleaned_data['exibicao']

        if 'imprimir' in request.GET:
            return relatorio_professor_pdf(request, campos_exibicao)

        if 'xls' in request.GET:
            return tasks.exportar_listagem_professores_xls(professores, campos_exibicao, form.EXIBICAO_CHOICES)
    return locals()


@rtr()
@login_required()
@permission_required('edu.report_dependentes_reprovados')
def relatorio_dependentes(request):
    title = 'Listagem de Dependentes'
    form = RelatorioDependenteForm(data=request.GET or None)
    exibir_botao_executar = HistoricoRelatorio.objects.filter(user=request.user, tipo=HistoricoRelatorio.TIPO_PROFESSOR).exists()
    if form.is_valid():
        query_string = request.META.get('QUERY_STRING', '').encode("utf-8").hex()
        matriculas_diarios, filtros = form.processar()
        matricula_diario_list = request.POST.getlist('select_matricula_diario')
        matricula_diario_resumida_list = request.POST.getlist('select_matricula_diario_resumida')
        if matricula_diario_list or matricula_diario_resumida_list:
            matriculas_diarios = list(MatriculaDiario.objects.filter(id__in=matricula_diario_list)) + list(
                MatriculaDiarioResumida.objects.filter(id__in=matricula_diario_resumida_list)
            )

        if 'xls' in request.POST:
            return tasks.exportar_relatorio_dependencia_xls(matriculas_diarios)
    return locals()


@rtr()
@login_required()
@permission_required(['edu.gerar_relatorio', 'rh.eh_servidor'])
def relatorio_diario(request):
    exibir_botao_executar = HistoricoRelatorio.objects.filter(user=request.user, tipo=HistoricoRelatorio.TIPO_DIARIO).exists()
    title = 'Listagem de Diários'
    form = RelatorioDiarioForm(data=request.GET or None, initial=dict(etapa=1))
    if form.is_valid():
        query_string = request.META.get('QUERY_STRING', '').encode("utf-8").hex()
        diarios = form.processar()
        filtros = diarios.filtros
        agrupamento = form.cleaned_data['agrupamento']
        if agrupamento == 'Período':
            diarios = diarios.order_by('-ano_letivo')
        elif agrupamento == 'Campus':
            diarios = diarios.order_by('turma__curso_campus__diretoria__setor__uo__nome')
        else:
            diarios = diarios.order_by('turma__curso_campus')
        campos_exibicao = form.cleaned_data['exibicao']

        if 'imprimir' in request.GET and request.user.has_perm('edu.emitir_boletins'):
            return tasks.relatorio_diario_pdf(request, diarios)
        if 'xls' in request.GET:
            return tasks.exportar_relatorio_diario_xls(diarios, campos_exibicao, form.EXIBICAO_CHOICES)

    return locals()


@rtr()
@permission_required('edu.gerar_turmas')
def imprimir_horarios(request):
    title = 'Imprimir Horários'
    form = ImprimirHorariosForm(data=request.GET or None, request=request)
    if form.is_valid():
        tabelas = TabelasHorario(request=request)
        turmas = form.processar()
        for turma in turmas:
            horarios_campus = HorarioCampus.objects.filter(diario__in=turma.diario_set.all()).distinct()
            for horario_campus in horarios_campus:
                tabela = TabelaHorario(export_to_pdf=False, request=request)
                tabela.titulo = f'{turma} - {horario_campus.descricao}'
                horarios_disponiveis = horario_campus.horarioaula_set.all() or []
                for horario in horarios_disponiveis:
                    tabela.adicionar_horario(horario.turno.descricao, horario.inicio, horario.termino)
                horarios = HorarioAulaDiario.objects.filter(diario__turma=turma, diario__horario_campus=horario_campus)
                for horario in horarios:
                    hint = 'Componente: {}; Professor(es): {}; Sala: {};'.format(
                        horario.diario.componente_curricular.componente.descricao, horario.diario.get_nomes_professores(),
                        horario.diario.local_aula
                    )
                    tabela.adicionar_registro(horario.diario.componente_curricular.componente.sigla, horario.get_horario_formatado(), '', hint)
                tabelas.adicionar(tabela)
        return tabelas.as_pdf()
    return locals()


@rtr()
@permission_required('edu.view_horarioauladiario')
def relatorio_horario(request):
    title = 'Listagem de Horários'
    form = RelatorioHorarioForm(data=request.GET or None, user=request.user)
    if form.is_valid():
        tabelas = TabelasHorario(request=request)
        horarios = form.processar()
        tabela = TabelaHorario(export_to_pdf=True, request=request)
        tabela.filtros = horarios.filtros
        horarios_disponiveis = horarios.exists() and horarios.first().diario.horario_campus.horarioaula_set.all() or []
        for horario in horarios_disponiveis:
            tabela.adicionar_horario(horario.turno.descricao, horario.inicio, horario.termino)
        for horario in horarios:
            hint = 'Componente: {}; Professor(es): {}; Sala: {};'.format(
                horario.diario.componente_curricular.componente.descricao, horario.diario.get_nomes_professores(), horario.diario.local_aula
            )
            link = not request.GET.get('pdf') and f'/edu/diario/{horario.diario.pk}' or ''
            tabela.adicionar_registro(horario.diario.componente_curricular.componente.sigla, horario.get_horario_formatado(), link, hint)
        tabelas.adicionar(tabela)
        if request.GET.get('pdf'):
            return tabelas.as_pdf()

    return locals()


@rtr()
@permission_required('edu.view_horarioauladiarioespecial')
def relatorio_horario_especial(request):
    title = 'Listagem de Horários (Atividades Específicas)'
    form = RelatorioHorarioDiarioEspecialForm(data=request.GET or None, user=request.user)
    if form.is_valid():
        horarios = form.processar()
        tabelas = TabelasHorario(request=request)
        tabela = TabelaHorario(export_to_pdf=True, request=request)
        tabela.filtros = horarios.filtros
        horarios_disponiveis = horarios.exists() and horarios.first().diario_especial.horario_campus.horarioaula_set.all() or []
        for horario in horarios_disponiveis:
            tabela.adicionar_horario(horario.turno.descricao, horario.inicio, horario.termino)
        for horario in horarios:
            hint = 'Componente: {}; Professor(es): {}; Sala: {};'.format(
                horario.diario_especial.componente.descricao, horario.diario_especial.get_nomes_professores(), horario.diario_especial.sala
            )
            link = not request.GET.get('pdf') and f'/edu/diarioespecial/{horario.diario_especial.pk}' or ''
            tabela.adicionar_registro(horario.diario_especial.componente.sigla, horario.get_horario_formatado(), link, hint)
        tabelas.adicionar(tabela)
        if request.GET.get('pdf'):
            return tabelas.as_pdf()

    return locals()


@documento()
@rtr('relatorio_impressao_pdf.html')
@login_required()
def relatorio_pdf(request, alunos, formatacao, campos_exibicao):
    title = 'Listagem de Alunos'
    campos_exibicao = campos_exibicao[0:3]
    campos_exibicao_choices = RelatorioForm.EXIBICAO_CHOICES + RelatorioForm.PENDENCIAS_EXIBICAO_CHOICES
    if alunos:
        uo = alunos[0].curso_campus.diretoria.setor.uo
    filtros = alunos.filtros
    return locals()


@permission_required('edu.gerar_relatorio')
def etiquetas_alunos_pdf(request, alunos, etiquetas):
    rows = []
    for aluno in alunos:
        row = [f'{aluno.matricula} - {aluno.get_nome_social_composto()}', '', aluno.curso_campus.descricao_historico, 'Situação: __________________________________']
        rows.append(row)
    labels = factory('Pimaco', etiquetas)
    f = io.BytesIO()
    labels.generate(rows, f)
    f.seek(0)
    return PDFResponse(f.read(), nome='Etiquetas.pdf')


@permission_required('edu.gerar_relatorio')
@documento()
@rtr('assinaturas_alunos_pdf.html')
def assinaturas_alunos_pdf(request, alunos, agrupamento):
    title = 'Assinatura dos Alunos'
    if alunos:
        uo = alunos[0].curso_campus.diretoria.setor.uo
    filtros = alunos.filtros
    return locals()


@permission_required('edu.gerar_relatorio')
@documento()
@rtr('carometros_alunos_pdf.html')
def carometros_alunos_pdf(request, alunos):
    title = 'Carômetros dos Alunos'
    uo = request.user.get_profile().funcionario.setor.uo
    return locals()


@documento()
@rtr('relatorio_professor_impressao_pdf.html')
@login_required()
def relatorio_professor_pdf(request, campos_exibicao):
    title = 'Listagem de Professores'
    pode_ver_endereco = pode_ver_endereco_professores(request.user)
    form = RelatorioProfessorForm(data=request.GET or None, pode_ver_endereco=pode_ver_endereco)
    campos_exibicao = campos_exibicao[0:3]
    campos_exibicao_choices = form.EXIBICAO_CHOICES
    if form.is_valid():
        professores = form.processar()
        uo = professores[0].vinculo.setor.uo
        filtros = professores.filtros
    return locals()


@rtr()
@group_required('Administrador Acadêmico,Secretário Acadêmico,Diretor Acadêmico,Estagiário,Assistente Social,Coordenador de Atividades Estudantis Sistêmico,')
def atualizar_dados_pessoais(request, pk):
    title = 'Atualização de Dados Pessoais'
    aluno = get_object_or_404(Aluno, pk=pk)
    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not (pode_realizar_procedimentos or request.user.has_perm('ae.add_demandaalunoatendida')):
        raise PermissionDenied()
    initial = dict(
        nome_usual=aluno.pessoa_fisica.nome_usual,
        email_secundario=aluno.pessoa_fisica.email_secundario,
        logradouro=aluno.logradouro,
        numero=aluno.numero,
        complemento=aluno.complemento,
        bairro=aluno.bairro,
        cep=aluno.cep,
        cidade=aluno.cidade,
        lattes=aluno.pessoa_fisica.lattes,
        telefone_principal=aluno.telefone_principal,
        telefone_secundario=aluno.telefone_secundario,
        telefone_adicional_1=aluno.telefone_adicional_1,
        telefone_adicional_2=aluno.telefone_adicional_2,
    )

    form = AtualizarDadosPessoaisForm(data=request.POST or None, initial=initial, instance=aluno, pode_realizar_procedimentos=pode_realizar_procedimentos)
    if form.is_valid():
        form.save(aluno)
        return httprr('..', 'Dados Pessoais atualizados com sucesso.')
    return locals()


@login_required()
@rtr()
def atualizar_meus_dados_pessoais(request, matricula, renovacao_matricula=None):
    title = 'Atualização de Dados Pessoais'
    aluno = get_object_or_404(Aluno, matricula=matricula)

    if request.user != aluno.pessoa_fisica.user:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    initial = dict(
        nome_usual=aluno.pessoa_fisica.nome_usual,
        email_secundario=aluno.pessoa_fisica.email_secundario,
        logradouro=aluno.logradouro,
        numero=aluno.numero,
        complemento=aluno.complemento,
        bairro=aluno.bairro,
        cep=aluno.cep,
        cidade=aluno.cidade,
        lattes=aluno.pessoa_fisica.lattes,
        telefone_principal=aluno.telefone_principal,
        telefone_secundario=aluno.telefone_secundario,
        utiliza_transporte_escolar_publico=aluno.poder_publico_responsavel_transporte is not None and (aluno.poder_publico_responsavel_transporte and 'Sim' or 'Não') or None,
        poder_publico_responsavel_transporte=aluno.poder_publico_responsavel_transporte,
        tipo_veiculo=aluno.tipo_veiculo,
    )
    form = AtualizarDadosPessoaisForm(data=request.POST or None, initial=initial, instance=aluno, pode_realizar_procedimentos=False, request=request)
    if form.is_valid():
        form.save(aluno)
        if renovacao_matricula:
            request.session['dados_atualizados'] = True
            request.session.save()
            if aluno.is_credito():
                url = f'/edu/pedido_matricula_credito/{aluno.pk}/'
            else:
                url = f'/edu/pedido_matricula_seriado/{aluno.pk}/'
            return httprr(url, 'Dados Pessoais atualizados com sucesso.')
        return httprr('..', 'Dados Pessoais atualizados com sucesso.')
    return locals()


@permission_required('edu.efetuar_matricula')
@rtr()
def relatorio_dados_responsavel_incompletos(request):
    title = 'Relatório de Alunos Menores de Idade sem CPF do Responsável'
    hoje = datetime.datetime.now()
    nascimento_data = hoje - relativedelta(years=18)
    diretorias = Diretoria.locals.all()
    alunos = Aluno.locals.filter(curso_campus__diretoria__in=diretorias, situacao__ativo=True, cpf_responsavel__isnull=True, pessoa_fisica__nascimento_data__gte=nascimento_data)
    form = FiltroAlunosForm(data=request.GET or None)
    if form.is_valid():
        alunos = form.filtrar(alunos)
    if 'export' in request.GET:
        rows = [['MATRÍCULA', 'NOME', 'CURSO', 'TURMA', 'DIRETORIA']]
        for aluno in alunos:
            ultima_matricula_periodo = aluno.get_ultima_matricula_periodo()
            row = [
                aluno.matricula,
                aluno.get_nome(),
                str(aluno.curso_campus),
                ultima_matricula_periodo and str(ultima_matricula_periodo.turma) or '-',
                str(aluno.curso_campus.diretoria),
            ]
            rows.append(row)
        return XlsResponse(rows)
    return locals()


@permission_required('edu.efetuar_matricula')
@rtr()
def atualizar_dados_responsavel(request, pk):
    title = 'Atualizar Dados do Responsável'
    aluno = get_object_or_404(Aluno, pk=pk)
    form = EditarDadosResponsavelForm(data=request.POST or None, instance=aluno)
    if form.is_valid():
        form.save()
        return httprr('..', 'Dados alterados com sucesso.')
    return locals()


@permission_required('edu.change_foto_aluno')
@rtr()
def atualizar_foto(request, pk):
    title = 'Atualização de Foto'
    aluno = get_object_or_404(Aluno, pk=pk)
    if request.method == 'POST':
        form = AtualizarFotoForm(data=request.POST or None, files=request.FILES)
    else:
        form = AtualizarFotoForm()
    form.initial.update(aluno=pk)
    if form.is_valid():
        return httprr(aluno.get_absolute_url(), form.processar(request))
    return locals()


@group_required('Administrador Acadêmico,Secretário Acadêmico,Diretor Acadêmico,')
@permission_required('edu.add_professordiario')
@rtr()
def atualizar_foto_professor(request, pk):
    title = 'Atualização de Foto do Professor'
    if request.method == 'POST':
        form = AtualizarFotoProfessorForm(data=request.POST or None, files=request.FILES)
    else:
        form = AtualizarFotoProfessorForm()
    form.initial.update(professor=pk)
    if form.is_valid():
        return httprr('..', form.processar(request))
    return locals()


@rtr()
@group_required('Aluno')
@login_required()
def locais_aula_aluno(request):
    aluno = get_object_or_404(Aluno, matricula=request.user.username)
    return httprr(f'/edu/aluno/{aluno.matricula}/?tab=locais_aula_aluno')


@rtr()
@group_required('Aluno')
@login_required()
def boletim_aluno(request):
    aluno = get_object_or_404(Aluno, matricula=request.user.username)
    return httprr(f'/edu/aluno/{aluno.matricula}/?tab=boletim')


@rtr()
@group_required('Professor')
@login_required()
def locais_aula_professor(request):
    title = 'Locais e Horários de Aula'
    professor = get_object_or_404(Professor, vinculo__user__username=request.user.username)
    is_professor = True
    periodo_letivo_atual = PeriodoLetivoAtual.get_instance(request, professor)
    tipo = 'professor'
    professor_diarios = professor.professordiario_set.filter(ativo=True)
    professores_diario_anual = professor_diarios.filter(
        diario__turma__curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL, diario__ano_letivo__ano=periodo_letivo_atual.ano
    )

    # excluíndo os diários semestrais em cursos anuais
    if periodo_letivo_atual.periodo == 1:
        professores_diario_anual = professores_diario_anual.exclude(diario__segundo_semestre=True)
    else:
        professores_diario_anual = professores_diario_anual.exclude(diario__segundo_semestre=False, diario__componente_curricular__qtd_avaliacoes=2)

    professores_diario_semestral = professor_diarios.filter(
        diario__turma__curso_campus__periodicidade__in=[CursoCampus.PERIODICIDADE_SEMESTRAL, CursoCampus.PERIODICIDADE_LIVRE],
        diario__ano_letivo__ano=periodo_letivo_atual.ano,
        diario__periodo_letivo=periodo_letivo_atual.periodo,
    )
    professor_diarios = (professores_diario_anual | professores_diario_semestral).order_by('diario__turma__curso_campus')
    horarios_campus = professor.get_horarios_aula_por_horario_campus(periodo_letivo_atual.ano, periodo_letivo_atual.periodo)

    return locals()


@permission_required('edu.emitir_boletins')
@documento()
@rtr('diario_pdf.html')
def diario_pdf(request, pk, etapa):
    diarios = []
    etapa = int(etapa)
    diario = get_object_or_404(Diario, pk=pk)
    etapas = etapa and [etapa] or (list(range(1, diario.componente_curricular.qtd_avaliacoes + 1)) + [5])
    uo = diario.turma.curso_campus.diretoria.setor.uo
    orientation = 'portrait'
    for i, etapa in enumerate(etapas):
        diario = i == 0 and diario or get_object_or_404(Diario, pk=pk)
        diario.hoje = datetime.date.today()
        diario.uo = diario.turma.curso_campus.diretoria.setor.uo
        diario.etapa = etapa
        diario.aula = Aula()
        diario.aula.quantidade = ' '
        diario.aula.data = ' '
        diario.aula.conteudo = ' '
        diario.aulas = list(diario.get_aulas(diario.etapa).order_by('data'))
        diario.datas_aulas = {}
        diario.faltas = Falta.objects.filter(aula__professor_diario__diario__pk=diario.pk, aula__etapa=diario.etapa)
        diario.map = {}
        # criando cache de número de faltas por data e aluno
        for falta in diario.faltas:
            key = f'{falta.aula.data};{falta.matricula_diario_id}'
            if key in diario.map:
                diario.map[key] += falta.quantidade
            else:
                diario.map[key] = falta.quantidade
        diario.matriculas_diario = diario.matriculadiario_set.all().exclude(
            situacao__in=[MatriculaDiario.SITUACAO_TRANCADO, MatriculaDiario.SITUACAO_TRANSFERIDO, MatriculaDiario.SITUACAO_CANCELADO]
        )
        if not running_tests():
            diario.matriculas_diario = diario.matriculas_diario.order_by('matricula_periodo__aluno__pessoa_fisica__nome')
        diario.etapa_s = diario.etapa
        if int(diario.etapa) == 5:
            diario.etapa_s = 'final'
        for i, matricula_diario in enumerate(diario.matriculas_diario):
            matricula_diario.nota = getattr(matricula_diario, f'nota_{diario.etapa_s}')
            matricula_diario.faltas = []
            matricula_diario.total = 0
            datas_verificadas = []
            for contador, aula in enumerate(diario.aulas):
                # adicionando as datas das aulas sem repetição com a respectiva quantidade
                if i == 0:
                    if aula.data not in diario.datas_aulas:
                        diario.datas_aulas[aula.data] = aula.quantidade
                    else:
                        diario.datas_aulas[aula.data] += aula.quantidade
                # calculando o número de faltas em uma data
                if aula.data not in datas_verificadas:
                    key = f'{aula.data};{matricula_diario.id}'
                    quantidade = key in diario.map and diario.map[key]
                    matricula_diario.total += quantidade
                    if not quantidade and contador < len(diario.get_aulas(diario.etapa)):
                        quantidade = '-'
                    matricula_diario.faltas.append(quantidade or '')
                datas_verificadas.append(aula.data)
        diarios.append(diario)
        if orientation == 'portrait' and len(diario.aulas) > 17:
            orientation = 'landscape'
    return locals()


@rtr()
@permission_required('edu.emitir_diploma')
def emitir_segunda_via_diploma(request, pk):
    title = 'Emitir Via de Diploma'
    obj = get_object_or_404(RegistroEmissaoDiploma, pk=pk)
    initial = dict(autenticacao_sistec=obj.autenticacao_sistec)
    form = EmitirSegundaViaDiploma(data=request.POST or None, request=request, initial=initial)
    # ajustar quando a PROEN autorizar
    if 0 and obj.aluno.requer_autenticacao_sistec_para_emissao_diploma():
        form.fields['autenticacao_sistec'].widget.attrs.update(readonly='readonly')
    else:
        form.fields['autenticacao_sistec'].widget = forms.HiddenInput()
    if form.is_valid():
        try:
            registro_emissao_dimploma = form.processar(obj)
            return httprr(
                f'/admin/edu/registroemissaodiploma/?id__in={registro_emissao_dimploma.pk}',
                f'{registro_emissao_dimploma.via}ª Via de diploma emitida com sucesso.'
            )
        except Exception as e:
            return httprr('/edu/emitir_diploma/', str(e), 'error')

    return locals()


@rtr()
@permission_required('edu.view_registroemissaodiploma')
def informar_dados_publicao_dou(request, pk):
    title = 'Informar Dados da Publicação no DOU'
    instance = get_object_or_404(RegistroEmissaoDiploma, pk=pk)
    form = PublicaoDOURegistroEmissaoDiplomaForm(data=request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        return httprr('..', 'Dados registrados com sucesso.')
    return locals()


@rtr()
@permission_required('edu.emitir_diploma')
def emitir_diploma(request):
    initial = dict(aluno=request.GET.get('aluno'))
    form = EmitirDiplomaAlunoForm(data=request.POST or None, request=request, initial=initial)
    if form.is_valid():
        try:
            ids = form.processar()
            url = f'/admin/edu/registroemissaodiploma/?id__in={ids[0]}'
            return httprr(url, 'Registro de emissão de diploma cadastrado com sucesso.')
        except Exception as e:
            return httprr('/edu/emitir_diploma/', str(e), 'error')

    aluno = form.cleaned_data.get('aluno')
    title = 'Emitir Diploma {}'.format(aluno and f' - {aluno}' or '')
    if aluno:
        registros = aluno.get_registros_emissao_diploma().order_by('via')
        if not aluno.requer_autenticacao_sistec_para_emissao_diploma:
            form.fields['autenticacao_sistec'].widget = forms.HiddenInput()

    return locals()


@rtr()
@permission_required('edu.emitir_diploma')
def emitir_diplomas(request):
    title = 'Emitir Diploma em Lote'
    form = EmitirDiplomaLoteForm(data=request.POST or None, request=request)
    if form.is_valid():
        try:
            ids = form.processar()
        except Exception as e:
            return httprr('/edu/emitir_diplomas/', str(e), 'error')
        return httprr('/admin/edu/registroemissaodiploma/?id__in={}'.format(','.join(ids)), 'Registros de emissão de diploma cadastrados com sucesso.')
    return locals()


@documento(enumerar_paginas=False)
@rtr('registroemissaodiploma_pdf.html')
@permission_required('edu.view_registroemissaodiploma')
def registroemissaodiploma_pdf(request, pk):
    obj = get_object_or_404(RegistroEmissaoDiploma, pk=pk, data_expedicao__isnull=False)
    objs = [obj]
    esconder_assinatura = 'digital' in request.GET
    uo = obj.aluno.curso_campus.diretoria.setor.uo
    if not obj.aluno.matriz_id:
        if 'sica' in settings.INSTALLED_APPS and obj.aluno.historico_set.exists():
            uo = UnidadeOrganizacional.objects.suap().get(pk=1)
    cra = obj.get_coordenador_registro_academico()
    hoje = datetime.datetime.now()
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()
    credenciamento = (Configuracao.get_valor_por_chave('edu', 'credenciamento'),)
    recredenciamento = Configuracao.get_valor_por_chave('edu', 'recredenciamento')
    return locals()


@rtr()
def registroemissaodiploma_public(request):
    title = 'Registro de Diplomas'
    category = 'Consultas'
    icon = 'certificate'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    form = RegistroEmissaoDiplomaPublicForm(data=request.GET or None)
    registros = RegistroEmissaoDiploma.objects.none()
    if form.is_valid():
        registros = form.processar()
    return locals()


@rtr()
def diploma_digital(request, pk, codigo):
    title = f'Diploma Digital - {codigo}'
    category = 'Consultas'
    icon = 'certificate'
    obj = RegistroEmissaoDiploma.objects.get(pk=pk)
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    return locals()


@documento()
@rtr('registroemissaodiploma_pdf.html')
@permission_required('edu.view_registroemissaodiploma')
def registrosemissaodiploma_pdf(request, pks):
    objs = RegistroEmissaoDiploma.objects.filter(pk__in=pks.split('_'))
    if objs.exists():
        uo = objs[0].aluno.curso_campus.diretoria.setor.uo
    hoje = datetime.datetime.now()
    return locals()


@documento(enumerar_paginas=False)
@rtr('atestadofrequencia_pdf.html')
def atestadofrequencia_pdf(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    situacao = aluno.get_situacao()
    eh_masculino = aluno.pessoa_fisica.sexo == 'M'

    if not request.user.has_perm('edu.efetuar_matricula') and not in_group(request.user, 'Estagiário') and not request.session.get('matricula-servico-impressao') == pk:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not aluno.possui_historico():
        return httprr('.', 'Este aluno não está cursando no Suap.', 'error')

    if not aluno.is_matriculado() and not aluno.is_intercambio():
        return httprr('..', 'Não é possível emitir a declaração, pois o aluno não está matriculado e nem se encontra em intercâmbio.', 'error')

    matricula_periodo = MatriculaPeriodo.objects.filter(aluno=aluno).latest('id')
    if not matricula_periodo.situacao.pk == SituacaoMatriculaPeriodo.MATRICULADO:
        return httprr('..', 'Não é possível emitir a declaração, pois o aluno não está matriculado em diário no último período.', 'error')
    uo = aluno.curso_campus.diretoria.setor.uo
    hoje = datetime.datetime.now()

    # Verificando se o aluno possui faltou consecutivamente nos últimos 30 dias.
    data_mes_anterior = hoje + datetime.timedelta(days=-30)
    aulas = Aula.objects.filter(professor_diario__diario__matriculadiario__matricula_periodo__aluno=aluno, data__range=(data_mes_anterior, hoje))
    faltas = Falta.objects.filter(matricula_diario__matricula_periodo__aluno=aluno, aula__in=aulas.values_list('pk', flat=True), abono_faltas__isnull=True).distinct()

    if aulas.exists() and faltas.count() == aulas.count():
        return httprr('.', 'Não é possível emitir o atestado, pois o aluno possui 30 dias consecutivos de faltas.', 'error')

    return locals()


@documento('Declaração de Vínculo Discente', False, validade=30, enumerar_paginas=False, modelo='edu.aluno')
@rtr('declaracaovinculo_pdf.html')
def declaracaovinculo_pdf(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    situacao = aluno.situacao
    is_usuario_proprio_aluno = aluno.is_user(request)
    if (
        not is_usuario_proprio_aluno
        and not request.user.has_perm('edu.efetuar_matricula')
        and not in_group(request.user, 'Estagiário, Pedagogo, Coordenador de Curso')
        and not request.session.get('matricula-servico-impressao') == pk
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    matricula_periodo = aluno.get_ultima_matricula_periodo()
    uo = aluno.curso_campus.diretoria.setor.uo
    hoje = datetime.datetime.now()
    return locals()


@documento('Declaração de Conclusão de Módulo', False, validade=30, enumerar_paginas=False, modelo='edu.aluno')
@rtr('declaracao_certificacao_parcial_pdf.html')
def declaracao_certificacao_parcial_pdf(request, pk, modulo):
    obj = get_object_or_404(Aluno, pk=pk)
    uo = obj.curso_campus.diretoria.setor.uo
    hoje = datetime.datetime.now()
    componentes = ComponenteCurricular.objects.filter(matriz_id=obj.matriz_id, tipo_modulo=modulo).order_by('id')
    ids_cc = componentes.values_list('id', flat=True)
    ids_md = (
        MatriculaDiario.objects.filter(
            matricula_periodo__aluno_id=obj.id,
            diario__componente_curricular__tipo_modulo=modulo,
            situacao__in=[MatriculaDiario.SITUACAO_APROVADO, MatriculaDiario.SITUACAO_APROVEITAMENTO_ESTUDO, MatriculaDiario.SITUACAO_CERTIFICACAO_CONHECIMENTO],
        )
        .order_by('diario__componente_curricular__id')
        .values_list('diario__componente_curricular_id', flat=True)
    )
    if list(ids_cc) != list(ids_md):
        return httprr('..', f'O aluno {aluno} não concluiu todas as disciplinas do módulo {int_to_roman(modulo)}.', 'error')
    total_ch = componentes.aggregate(Sum('componente__ch_hora_relogio'))['componente__ch_hora_relogio__sum']
    modulo_numero_romano = int_to_roman(modulo)
    return locals()


@documento('Declaração de Vínculo Docente', False, validade=30, enumerar_paginas=False, modelo='edu.professor')
@rtr('declaracaodocencia_pdf.html')
def declaracaodocencia_pdf(request, pk, ano=None):
    ANO_NOVO_CALCULO_CH = 2023
    oculta_ch_ministrada = ano and ano < ANO_NOVO_CALCULO_CH
    obj = get_object_or_404(Professor, pk=pk)
    uo = obj.get_uo()
    hoje = datetime.datetime.now()
    if obj.vinculo.eh_prestador():
        texto_periodo_vinculo = 'ministrou as disciplinas'
    elif obj.vinculo.relacionamento.data_fim_servico_na_instituicao is None:
        texto_periodo_vinculo = f'desde {format_datetime(obj.vinculo.relacionamento.data_inicio_exercicio_no_cargo)}, vem ministrando as disciplinas'
    else:
        texto_periodo_vinculo = 'de {} a {}, ministrou as disciplinas'.format(
            format_datetime(obj.vinculo.relacionamento.data_inicio_exercicio_no_cargo), format_datetime(obj.vinculo.relacionamento.data_fim_servico_na_instituicao)
        )

    diarios = Diario.objects.filter(professordiario__professor=obj)
    diarios_minicurso = obj.professorminicurso_set.all()
    diarios_especiais = obj.diarioespecial_set.all()

    if ano:
        diarios = diarios.filter(ano_letivo__ano=ano)
        diarios_minicurso = diarios_minicurso.filter(turma_minicurso__ano_letivo__ano=ano)
        diarios_especiais = diarios_especiais.filter(ano_letivo__ano=ano)

    attrs_diario = (
        'turma__curso_campus__descricao_historico',
        'turma__curso_campus__modalidade__descricao',
        'turma__curso_campus__diretoria__setor__sigla',
        'ano_letivo__ano',
        'periodo_letivo',
        'componente_curricular__componente__descricao_historico',
    )
    diarios = diarios.order_by(*attrs_diario).distinct()

    lists_diarios = []
    for diario in diarios:
        lists_diarios.append(
            (
                diario.turma.curso_campus.descricao_historico,
                diario.turma.curso_campus.modalidade.descricao,
                diario.turma.curso_campus.diretoria.setor.sigla,
                diario.ano_letivo.ano,
                diario.get_periodo_letivo(),
                diario.componente_curricular.componente.ch_hora_relogio,
                diario.pk,
                diario.professordiario_set.get(professor_id=obj.id).get_percentual_ch_ministrada(),
                diario.componente_curricular.componente.descricao_historico,
                diario.componente_curricular.componente.ch_qtd_creditos,
                diario.segundo_semestre,
                diario.turma.curso_campus.periodicidade == CursoCampus.PERIODICIDADE_ANUAL and not diario.is_semestral() and 'Anual' or 'Semestral',
                diario.professordiario_set.get(professor_id=obj.id).get_percentual_ch()
            )
        )
    for diario in diarios_minicurso:
        lists_diarios.append(
            (
                'Minicursos',
                diario.turma_minicurso.minicurso.modalidade.descricao,
                diario.turma_minicurso.minicurso.diretoria.setor.sigla,
                diario.turma_minicurso.ano_letivo.ano,
                diario.turma_minicurso.periodo_letivo,
                diario.carga_horaria,
                '-',
                '100',
                diario.turma_minicurso.minicurso.descricao,
                '-',
                False,
                '',
                '100',
            )
        )
    for diario in diarios_especiais:
        lists_diarios.append(
            (
                'Diários Especiais',
                '',
                diario.diretoria.setor.sigla,
                diario.ano_letivo.ano,
                diario.periodo_letivo,
                diario.componente.ch_hora_relogio,
                diario.pk,
                '100',
                diario.componente.descricao_historico,
                diario.componente.ch_qtd_creditos,
                False,
                'Semestral',
                '100',
            )
        )
    return locals()


@rtr()
def registrar_ocorrencia_diario(request, pk, pk_ocorrencia):
    title = 'Registrar Observação'
    obj = OcorrenciaDiario.objects.filter(pk=pk_ocorrencia).first() or OcorrenciaDiario()
    obj.professor_diario_id = pk
    form = OcorrenciaDiarioForm(data=request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Ocorrência registrada com sucesso.')
    return locals()


@documento('Declaração de Matrícula', False, validade=30, enumerar_paginas=False, modelo='edu.aluno')
@rtr('declaracaomatricula_pdf.html')
def declaracaomatricula_pdf(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    situacao = aluno.situacao
    exibir_modalidade = 'Técnico' in aluno.curso_campus.modalidade.descricao
    eh_masculino = aluno.pessoa_fisica.sexo == 'M'

    is_usuario_proprio_aluno = aluno.is_user(request)
    if (
        not is_usuario_proprio_aluno
        and not request.user.has_perm('edu.efetuar_matricula')
        and not in_group(request.user, 'Estagiário, Pedagogo, Coordenador de Curso')
        and not request.session.get('matricula-servico-impressao') == pk
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not aluno.possui_historico():
        return httprr('.', 'Aluno importado. Não possui diários no SUAP.', 'error')

    if not aluno.is_matriculado() and not aluno.is_intercambio():
        return httprr('..', 'Não possível emitir a declaração, pois o aluno não está matriculado e também não está em intercâmbio.', 'error')

    matricula_periodo = MatriculaPeriodo.objects.filter(aluno=aluno).latest('id')
    uo = aluno.curso_campus.diretoria.setor.uo
    hoje = datetime.datetime.now()
    polo = aluno.polo
    return locals()


@documento('Declaração de Carga Horária Cumprida', False, validade=30, enumerar_paginas=False, modelo='edu.aluno')
@rtr('declaracao_ch_cumprida_pdf.html')
def declaracao_ch_cumprida_pdf(request, pk):
    aluno = get_object_or_404(Aluno, pk=pk)
    sexo_aluno = aluno.pessoa_fisica.sexo == 'M' and 'o' or 'a'

    is_usuario_proprio_aluno = aluno.is_user(request)
    if (
        not is_usuario_proprio_aluno
        and not request.user.has_perm('edu.efetuar_matricula')
        and not in_group(request.user, 'Estagiário, Pedagogo, Coordenador de Curso')
        and not request.session.get('matricula-servico-impressao') == pk
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not aluno.possui_historico():
        return httprr('.', 'Aluno importado. Não possui diários no SUAP.', 'error')

    if not aluno.is_matriculado() and not aluno.is_intercambio():
        return httprr('..', 'Não possível emitir a declaração, pois o aluno não está matriculado e também não está em intercâmbio.', 'error')

    uo = aluno.curso_campus.diretoria.setor.uo
    hoje = datetime.datetime.now()
    return locals()


@rtr()
@permission_required('edu.change_registroemissaodiploma')
def registroemissaodiploma(request, pk):
    obj = get_object_or_404(RegistroEmissaoDiploma, pk=pk)
    title = f'Emissão de Diploma - {obj.via}ª Via'
    if 'registrar' in request.GET:
        obj.registrar()
        return httprr(f'/edu/registroemissaodiploma/{obj.pk}/', 'Diploma registrado com sucesso. As assinaturas do registro podem ser realizadas.')
    if 'excluir' in request.GET and not obj.data_registro:
        obj.delete()
        return httprr('..', 'Registro excluído com sucesso.')
    if 'sincronizar_assinatura' in request.GET and request.user.is_superuser:
        from edu.diploma_digital.rap import AssinadorDigital
        assinador = AssinadorDigital()
        for assinatura_eletronica in obj.assinaturadigital_set.order_by('-id')[0:1]:
            assinador.sincronizar(assinatura_eletronica)
        return httprr(f'/edu/registroemissaodiploma/{obj.pk}/?tab=dados_assinatura_digital', 'Sincronização realizada com sucesso.')
    if 'enviar' in request.GET and obj.aluno.curso_campus.assinatura_eletronica:
        obj.enviar_por_email()
        return httprr('..', 'Diploma/Histórico enviados com sucesso.')

    uo = obj.aluno.curso_campus.diretoria.setor.uo
    hoje = datetime.datetime.now()
    return locals()


@rtr()
@permission_required('edu.change_registroemissaodiploma')
def cancelar_registroemissaodiploma(request, pk):
    title = 'Cancelar Registro de Emissão de Diploma'
    obj = get_object_or_404(RegistroEmissaoDiploma, pk=pk)
    form = CancelarRegistroEmissaoDiplomaForm(request.POST or None, instance=obj)
    if form.is_valid():
        form.instance.cancelar()
        form.instance.data_cancelamento = datetime.datetime.now()
        form.save()
        return httprr('..', 'Registro de emissão de diploma cancelado com sucesso.')
    return locals()


@documento('Diploma/Certificado', pdf_response=False, modelo='edu.registroemissaodiploma')
@rtr('registroemissaodiploma_pdf.html')
@permission_required(['edu.change_registroemissaodiploma', 'edu.view_assinaturaeletronica'])
def gerar_autenticacao_diploma_pdf(request, pk):
    obj = get_object_or_404(RegistroEmissaoDiploma, pk=pk)
    objs = [obj]
    uo = obj.aluno.curso_campus.diretoria.setor.uo
    hoje = datetime.datetime.now()
    esconder_assinatura = True
    return locals()


@rtr()
@permission_required('edu.emitir_diploma')
def imprimir_diploma(request, pks):
    redirect = None
    title = 'Gerar Diploma'
    objs = []
    if '_' in pks:
        objs = RegistroEmissaoDiploma.objects.filter(id__in=pks.split('_'))
        if objs.values_list('aluno__curso_campus__id', flat=True).distinct().count() > 1:
            redirect = 'Não é possível imprimir diploma/certificado para mais de um aluno de diferentes cursos.'

    else:
        objs = [get_object_or_404(RegistroEmissaoDiploma, pk=pks)]

    obj = objs[0]
    if not in_group(request.user, 'Administrador Acadêmico'):
        qs_coordenador_registro_academico = CoordenadorRegistroAcademico.objects.filter(
            diretoria__setor__uo=obj.aluno.curso_campus.diretoria.setor.uo, eh_coordenador_registro=True
        )
        if not qs_coordenador_registro_academico.exists():
            qs_coordenador_registro_academico = CoordenadorRegistroAcademico.objects.filter(servidor__pessoafisica_ptr__username=request.user.username)
    else:
        qs_coordenador_registro_academico = CoordenadorRegistroAcademico.objects.filter(diretoria__setor__uo=obj.aluno.curso_campus.diretoria.setor.uo)

    qs_modelo_documento = ModeloDocumento.objects.filter(modalidade=obj.aluno.curso_campus.modalidade, ativo=True)

    if 'sica' in settings.INSTALLED_APPS:
        if obj.aluno.historico_set.exists():
            qs_modelo_documento = qs_modelo_documento.filter(descricao__contains='SICA')
        else:
            qs_modelo_documento = qs_modelo_documento.exclude(descricao__contains='SICA')

    if not qs_modelo_documento.exists():
        redirect = 'Não é possível imprimir diploma/certificado para a modalidade {} já que não há um modelo de documento ativo cadastrado para ela'.format(
            obj.aluno.curso_campus.modalidade
        )

    if not obj.data_registro:
        redirect = 'É necessário realizar o registro do diploma.'

    if not obj.aluno.curso_campus.diretoria.diretor_geral:
        redirect = f'É necessário definir o Diretor Geral do campus no cadastro da diretoria {obj.aluno.curso_campus.diretoria}.'

    if not obj.aluno.curso_campus.diretoria.diretor_academico:
        redirect = f'É necessário definir o Diretor Acadêmico no cadastro da diretoria {obj.aluno.curso_campus.diretoria}.'

    if not obj.aluno.curso_campus.is_fic():
        if not obj.aluno.curso_campus.coordenador:
            redirect = f'É necessário definir o Coordenador do curso \"{obj.aluno.curso_campus.descricao}\" no cadastro da diretoria {obj.aluno.curso_campus.diretoria}.'

    initial = dict(
        diretor_geral=obj.aluno.curso_campus.diretoria.diretor_geral_exercicio.pk,
        diretor_academico=obj.aluno.curso_campus.diretoria.diretor_academico_exercicio.pk,
        coordenador_registro_escolar=qs_coordenador_registro_academico.exists() and qs_coordenador_registro_academico[0].pk,
    )
    form = ImprimirDiplomaForm(data=request.POST or None, initial=initial)
    form.fields['diretor_geral'].queryset = obj.aluno.curso_campus.diretoria.get_diretores_gerais()
    form.fields['diretor_academico'].queryset = obj.aluno.curso_campus.diretoria.get_diretores_academicos()
    form.fields['diretor_ensino'].queryset = obj.aluno.curso_campus.diretoria.get_diretores_de_ensino()
    form.fields['modelo_documento'].queryset = qs_modelo_documento
    form.fields['coordenador_registro_academico'].queryset = qs_coordenador_registro_academico

    sigla_reitoria = get_sigla_reitoria()
    reitoria = UnidadeOrganizacional.objects.suap().get(sigla=sigla_reitoria)
    reitor = reitoria.get_diretor_geral(True)[0]
    form.fields['reitor'].initial = reitor.pk

    if form.is_valid():
        reitor_protempore = form.cleaned_data['reitor_protempore']
        diretor_geral_protempore = form.cleaned_data['diretor_geral_protempore']
        modelo_documento = form.cleaned_data['modelo_documento'].template
        arquivo_zip = None

        for i, obj in enumerate(objs):
            if obj.aluno.curso_campus.assinatura_eletronica or obj.aluno.curso_campus.assinatura_digital:
                mensagem = 'Diploma(s) gerado(s) com sucesso. O envio será realizado por e-mail e disponibilizado no SUAP para o aluno após a(s) assinatura(s).'
                if obj.aluno.curso_campus.assinatura_eletronica:  # certificados ICP EDU
                    if AssinaturaEletronica.objects.filter(registro_emissao_diploma=obj).exists():
                        messages.error(request, f'Registro {obj.pk} já possui assinatura digital realizada.')
                        continue
                    vinculos = []
                    if obj.aluno.curso_campus.modalidade_id != Modalidade.FIC:
                        vinculos.append(form.cleaned_data['reitor'].get_vinculo())
                    vinculos.append(form.cleaned_data['diretor_geral'].get_vinculo())
                    assinatura_eletronica = AssinaturaEletronica.objects.create(
                        registro_emissao_diploma=obj,
                        reitor=form.cleaned_data['reitor'],
                        reitor_protempore=form.cleaned_data['reitor_protempore'],
                        diretor_geral=form.cleaned_data['diretor_geral'],
                        diretor_geral_protempore=form.cleaned_data['diretor_geral_protempore'],
                        diretor_academico=form.cleaned_data['diretor_academico'],
                        diretor_ensino=form.cleaned_data['diretor_ensino'],
                        coordenador_registro_academico=form.cleaned_data['coordenador_registro_academico'],
                        modelo_documento=form.cleaned_data['modelo_documento']
                    )
                    for vinculo in vinculos:
                        SolicitacaoAssinaturaEletronica.objects.create(
                            assinatura_eletronica=assinatura_eletronica, vinculo=vinculo
                        )
                    obj.situacao = RegistroEmissaoDiploma.AGUARDANDO_ASSINATURA_DIPLOMA
                    obj.save()
                else:  # certificados ICP Brasil
                    if AssinaturaDigital.objects.filter(registro_emissao_diploma=obj).exists():
                        messages.error(request, f'Registro {obj.pk} já possui assinatura digital realizada.')
                        continue
                    registro_emissao_documento_diploma = gerar_autenticacao_diploma_pdf(request, pk=obj.pk)
                    registro_emissao_documento_historico = emitir_historico_final_eletronico_pdf(
                        request, pk=str(obj.aluno.pk), legado=obj.aluno.is_qacademico()
                    )
                    if isinstance(registro_emissao_documento_historico, HttpResponseRedirect):
                        return registro_emissao_documento_historico
                    AssinaturaDigital.objects.create(
                        registro_emissao_diploma=obj,
                        reitor=form.cleaned_data['reitor'],
                        reitor_protempore=form.cleaned_data['reitor_protempore'],
                        diretor_geral=form.cleaned_data['diretor_geral'],
                        diretor_geral_protempore=form.cleaned_data['diretor_geral_protempore'],
                        diretor_academico=form.cleaned_data['diretor_academico'],
                        diretor_ensino=form.cleaned_data['diretor_ensino'],
                        coordenador_registro_academico=form.cleaned_data['coordenador_registro_academico'],
                        modelo_documento=form.cleaned_data['modelo_documento'],
                        registro_emissao_documento_diploma=registro_emissao_documento_diploma,
                        registro_emissao_documento_historico=registro_emissao_documento_historico,
                    )
                    obj.situacao = RegistroEmissaoDiploma.AGUARDANDO_SINCRONIZACAO
                    obj.save()
                if i == len(objs) - 1:
                    return httprr('..', mensagem)
                else:
                    continue
            else:
                obj.situacao = RegistroEmissaoDiploma.AGUARDANDO_ASSINATURA_FISICA
                obj.save()

            registro = gerar_autenticacao_diploma_pdf(request, pk=obj.pk)
            dicionario = obj.gerar_diploma(
                reitor,
                form.cleaned_data['reitor'],
                form.cleaned_data['diretor_geral'],
                form.cleaned_data['diretor_academico'] or form.cleaned_data['diretor_ensino'],
                form.cleaned_data['coordenador_registro_academico'],
                registro,
                reitor_protempore,
                diretor_geral_protempore,
            )
            caminho_arquivo = gerar_documento_impressao(dicionario, io.BytesIO(modelo_documento.read()))
            if not caminho_arquivo:
                return httprr('/', 'Documento não encontrado.', 'error')
            nome_arquivo = caminho_arquivo.split('/')[-1]
            extensao = nome_arquivo.split('.')[-1]

            if len(objs) == 1:
                arquivo = open(caminho_arquivo, "rb")
                content_type = caminho_arquivo.endswith('.pdf') and 'application/pdf' or 'application/vnd.ms-word'
                response = HttpResponse(arquivo.read(), content_type=content_type)
                response['Content-Disposition'] = f'attachment; filename={nome_arquivo}'
                arquivo.close()
                os.unlink(caminho_arquivo)
                return response
            else:
                if i == 0:
                    arquivo_zip = zipfile.ZipFile(f'{tempfile.mktemp()}{datetime.datetime.now()}', 'w')

                arquivo_zip.write(caminho_arquivo, f'{obj.aluno.matricula}.{extensao}')
                os.unlink(caminho_arquivo)

                if i == len(objs) - 1:
                    arquivo_zip.close()
                    response = HttpResponse(open(arquivo_zip.filename, 'r+b').read(), content_type='application/zip')
                    response['Content-Disposition'] = 'attachment; filename=Diplomas.zip'
                    return response
    return locals()


@rtr()
@permission_required('edu.view_log')
def log(request, pk):
    title = f'Visualização do Log #{pk}'
    obj = get_object_or_404(Log, pk=pk)
    tipo = str(Log.TIPO_CHOICES[obj.tipo - 1][1])
    diff = RegistroDiferenca.objects.filter(log=obj)
    cls = apps.get_model(obj.app, obj.modelo)
    instancia = None
    qs = cls.objects.filter(pk=obj.ref)
    if qs.exists():
        instancia = qs[0]
        metadata = utils.metadata(instancia)
    return locals()


@permission_required('edu.view_log')
@rtr('logs_ppe.html')
def realizar_auditoria(request):
    title = 'Auditoria'
    form = RealizarAuditoriaForm(data=request.GET or None)
    pode_exportar_log = True

    if form.is_valid():
        logs = form.processar()

        if 'exportar' in request.GET:
            response = HttpResponse(content_type='application/ms-excel')
            response['Content-Disposition'] = 'attachment; filename=relatorio_de_logs.xls'

            wb = xlwt.Workbook(encoding='utf-8')
            sheet1 = FitSheetWrapper(wb.add_sheet('Relatório de Logs'))
            style = xlwt.easyxf(
                'pattern: pattern solid, fore_colour gray25; borders: left thin, right thin, top thin, bottom thin; '
                'font: colour black, bold True; align: wrap on, vert centre, horiz center;'
            )

            col = 0
            line = 0

            sheet1.write_merge(line, line + 1, col, col, 'Id de Log', style)
            col += 1
            sheet1.write_merge(line, line + 1, col, col, 'Data', style)
            col += 1
            sheet1.write_merge(line, line + 1, col, col, 'Usuário', style)
            col += 1
            sheet1.write_merge(line, line + 1, col, col, 'Diário', style)
            col += 1
            sheet1.write_merge(line, line + 1, col, col, 'Aluno', style)
            col += 1
            sheet1.write_merge(line, line + 1, col, col, 'Tipo', style)
            col += 1
            sheet1.write_merge(line, line + 1, col, col, 'Modelo Alterado', style)
            col += 1
            sheet1.write_merge(line, line + 1, col, col, 'Id. Modelo', style)
            col += 1
            sheet1.write_merge(line, line + 1, col, col, 'Dados Alterados', style)
            col += 1
            line = 1

            for log in logs:

                line += 1
                col = 0
                sheet1.row(line).write(col, log.pk)
                col += 1
                sheet1.row(line).write(col, f'{log.dt.day}/{log.dt.month}/{log.dt.year}')
                col += 1
                user = log.user and f'{log.user.get_full_name()} ({log.user.username})' or '-'
                sheet1.row(line).write(col, user)
                col += 1
                sheet1.row(line).write(col, log.ref_diario or '-')
                col += 1
                sheet1.row(line).write(col, log.ref_aluno and Aluno.objects.filter(pk=log.ref_aluno).first().matricula or '-')
                col += 1
                sheet1.row(line).write(col, log.tipo == Log.CADASTRO and 'Cadastro' or log.tipo == Log.EDICAO and 'Edição' or log.tipo == Log.EXCLUSAO and 'Exclusão')
                col += 1
                sheet1.row(line).write(col, log.nome_modelo)
                col += 1
                sheet1.row(line).write(col, log.ref)
                col += 1

                if log.tipo in [Log.EDICAO, Log.EXCLUSAO]:
                    qs_diffs = RegistroDiferenca.objects.filter(log=log)
                    diffs = []
                    for diff in qs_diffs:
                        diffs.append('{}: {} para {}'.format(diff.campo, diff.valor_anterior, diff.valor_atual or '-'))
                    sheet1.row(line).write(col, ', '.join(diffs))
                    col += 1
                else:
                    sheet1.row(line).write(col, '-')
                    col += 1

            wb.save(response)
            return response

    return locals()


@permission_required('edu.view_log')
@rtr('logs_ppe.html')
def log_diario(request, pk):
    qs_log = Log.objects.filter(ref_diario=pk) | Log.objects.filter(ref=pk, modelo='Diario')
    logs = qs_log.distinct().order_by('-id')
    title = f'Log do diário {pk}'
    return locals()


@permission_required('edu.view_log')
@rtr('logs_ppe.html')
def log_diario_especial(request, pk):
    encontros = Encontro.objects.filter(diario_especial_id=pk).values_list('pk', flat=True)
    qs_log = Log.objects.filter(ref=pk, modelo='DiarioEspecial') | Log.objects.filter(ref__in=encontros, modelo='Encontro')
    logs = qs_log.distinct().order_by('-id')
    title = f'Log do diário {pk}'
    return locals()


@permission_required('edu.view_log')
@rtr('logs_ppe.html')
def log_aluno(request, pk):
    obj = get_object_or_404(Aluno, pk=pk)
    qs_log = Log.objects.filter(ref_aluno=pk) | Log.objects.filter(ref=pk, modelo='Aluno')
    qs_log = qs_log.distinct()
    logs = list()
    for log in qs_log:
        logs.append(dict(pk=log.pk, user=log.user, dt=log.dt, descricao=log.descricao))
    for matricula_periodo in obj.matriculaperiodo_set.all():
        for hsmp in matricula_periodo.historicosituacaomatriculaperiodo_set.all():
            descricao = 'A matrícula período {}.{} foi atualizada para a situação "{}"'.format(
                matricula_periodo.ano_letivo.ano, matricula_periodo.periodo_letivo, str(hsmp.situacao)
            )
            logs.append(dict(pk=None, user=hsmp.usuario, dt=hsmp.data, descricao=descricao))

    logs.sort(key=lambda x: (x['dt']), reverse=True)
    title = str(obj)
    return locals()


@rtr()
@login_required()
def redirecionar_aluno(request):
    title = 'Selecione o Aluno'
    form = BuscaAlunoForm(request.POST or None)
    if form.is_valid():
        return form.processar()
    return locals()


@rtr()
@login_required()
def redirecionar_diario(request):
    title = 'Selecione o Diário'
    form = BuscaDiarioForm(request.POST or None)
    if form.is_valid():
        return form.processar()
    return locals()


@rtr()
@login_required()
def redirecionar_matriz(request):
    title = 'Selecione a Matriz'
    form = BuscaMatrizForm(request.POST or None)
    if form.is_valid():
        return form.processar()
    return locals()


@rtr()
@login_required()
def redirecionar_calendario(request):
    title = 'Selecione o Calendário Acadêmico'
    form = BuscaCalendarioForm(request.POST or None)
    if form.is_valid():
        return form.processar()
    return locals()


@rtr()
@login_required()
@permission_required('edu.efetuar_matricula')
def imprimir_historico(request, tipo):
    if tipo.lower() == 'parcial':
        title = 'Impressão de Histórico Parcial'
        form = ImprimirHistoricoParcialForm(request.POST or None)
    elif tipo.lower() == 'final':
        title = 'Impressão de Histórico Final'
        form = ImprimirHistoricoFinalForm(request.POST or None)

    if form.is_valid():
        return form.processar()
    return locals()


@rtr()
@login_required()
@permission_required('edu.efetuar_matricula')
def imprimir_historico_em_lote(request):
    title = 'Impressão de Histórico Final em Lote'
    form = ImprimirHistoricoFinalEmLoteForm(request.POST or None)

    if form.is_valid():
        alunos = form.processar()
        if alunos.count() > 100 and not request.user.is_superuser:
            return httprr('.', 'A quantidade máxima de impressão de históricos em lote é de 100 alunos por vez.', 'error')

        pks_alunos = '_'.join(str(pk) for pk in alunos.values_list('pk', flat=True))
        return httprr(f'/edu/emitir_historico_final_pdf/{pks_alunos}/')

    return locals()


@rtr()
@login_required()
@permission_required('edu.add_abonofaltas')
def abonar_faltas_lote(request):
    title = 'Adicionar Justificativa de Falta em Lote'
    form = AbonoFaltasLoteForm(request.POST or None, files=request.FILES or None, request=request)

    if form.is_valid():
        form.processar()
        return httprr('/admin/edu/abonofaltas/')

    return locals()


@rtr()
@login_required()
@permission_required('edu.emitir_boletim')
def imprimir_boletins_alunos_em_lote(request):
    title = 'Impressão de Boletins em Lote'
    form = ImprimirBoletinsEmLoteForm(request.POST or None)

    if form.is_valid():
        alunos = form.processar()
        pks_alunos = '_'.join(str(pk) for pk in alunos.values_list('pk', flat=True))
        return httprr(f'/edu/emitir_boletim_pdf/{pks_alunos}/')

    return locals()


@rtr()
@login_required()
@permission_required('edu.efetuar_matricula')
def imprimir_boletim_aluno(request):
    title = 'Selecione o Aluno/Período'
    form = ImprimirBoletimAlunoForm(request.POST or None)
    if form.is_valid():
        return form.processar()
    return locals()


@rtr()
@login_required()
@permission_required('edu.efetuar_matricula')
def imprimir_registro_diploma_aluno(request):
    title = 'Selecione o Aluno'
    form = ImprimirRegistroDiplomaAlunoForm(request.POST or None)
    if form.is_valid():
        return form.processar()
    return locals()


def contexto_painel_controle(request):
    title = 'Painel de Controle'
    periodo_letivo_atual = PeriodoLetivoAtualSecretario.get_instance(request)
    diretorias = Diretoria.locals.all()
    diretoria_ids = '%3B'.join(str(x) for x in diretorias.values_list('id', flat=True))
    diretorias_com_pendencia = []
    ano_letivo = None
    if Ano.objects.filter(ano=periodo_letivo_atual.ano).exists():
        ano_letivo = Ano.objects.get(ano=periodo_letivo_atual.ano)
        cleaned_data = dict(ano_letivo=ano_letivo, periodo_letivo=periodo_letivo_atual.periodo, diretorias=diretorias)
        matriculas_periodos, graficos1 = MonitoramentoFechamentoPeriodoForm(request.GET or None, request=request).processar(cleaned_data)
        professores_diario, graficos2 = MonitoramentoEntregaDiariosForm(request.GET or None, request=request).processar(com_grafico=False, cleaned_data=cleaned_data)

        for diretoria in diretorias:
            diretoria.pendencias = diretoria.get_pendencias(periodo_letivo_atual.ano, periodo_letivo_atual.periodo, request.user)
            if diretoria.pendencias:
                diretorias_com_pendencia.append(diretoria)

    painel = []
    box_matriz = []
    if request.user.has_perm('edu.add_matriz'):
        contador = Matriz.objects.vazias().count()
        if contador:
            box_matriz.append(('Vazias', '/admin/edu/matriz/?tab=tab_vazias', f'{contador}'))
        contador = Matriz.objects.incompletas().count()
        if contador:
            box_matriz.append(('Incompletas', '/admin/edu/matriz/?tab=tab_incompletas', f'{contador}'))
        if box_matriz:
            painel.append(('Matrizes com Pendência', box_matriz, 'matriz'))

    box_acesso_rapido = []
    box_acesso_rapido.append(('Aluno', '/edu/redirecionar_aluno/', 0, 'popup'))
    box_acesso_rapido.append(('Diário', '/edu/redirecionar_diario/', 0, 'popup'))
    box_acesso_rapido.append(('Matriz', '/edu/redirecionar_matriz/', 0, 'popup'))
    box_acesso_rapido.append(('Calendário Acadêmico', '/edu/redirecionar_calendario/', 0, 'popup'))
    painel.append(('Acesso Rápido', box_acesso_rapido, 'busca'))

    box_relatorio = []
    box_relatorio.append(('Listagem de Alunos', '/edu/relatorio/', 0))
    box_relatorio.append(('Listagem de Professores', '/edu/relatorio_professor/', 0))
    box_relatorio.append(('Listagem de Diários', '/edu/relatorio_diario/', 0))
    box_relatorio.append(('Relatório de Faltas', '/edu/relatorio_faltas/', 0))
    if ano_letivo:
        box_relatorio.append(
            ('Estatísticas', f'/edu/estatistica/?situacao_matricula_periodo=4&agrupar=Curso&apartir_do_ano={ano_letivo.pk}&curso_campus=&ano_periodo=por_periodo_letivo', 0)
        )
    painel.append(('Relatórios e Estatísticas', box_relatorio, 'protocolo'))

    box_documento_aluno = []
    box_documento_aluno.append(('Imprimir Histórico Final', '/edu/imprimir_historico/final/', 0, 'popup'))
    box_documento_aluno.append(('Imprimir Histórico Final em Lote', '/edu/imprimir_historico_em_lote/', 0))
    box_documento_aluno.append(('Imprimir Boletim', '/edu/imprimir_boletim_aluno/', 0, 'popup'))

    painel.append(('Emissão de Documentos', box_documento_aluno, 'edu'))

    if request.user.has_perm('edu.add_diretoria'):
        box_diretoria = []
        contador = Diretoria.locals.sem_diretores().count()
        if contador:
            box_diretoria.append(('Sem diretores', '/admin/edu/diretoria/?tab=tab_sem_diretores', f'{contador}'))
        contador = Diretoria.locals.sem_secretarios().count()
        if contador:
            box_diretoria.append(('Sem secretários', '/admin/edu/diretoria/?tab=tab_sem_secretarios', f'{contador}'))
        contador = Diretoria.locals.sem_coordenadores().count()
        if contador:
            box_diretoria.append(('Sem coordenadores', '/admin/edu/diretoria/?tab=tab_sem_coordenadores', f'{contador}'))
        contador = Diretoria.locals.sem_pedagogos().count()
        if contador:
            box_diretoria.append(('Sem pedagogos', '/admin/edu/diretoria/?tab=tab_sem_pedagogos', f'{contador}'))
        if box_diretoria:
            painel.append(('Diretoria', box_diretoria, 'departamento'))

    box_processamento_periodo = []
    box_processamento_periodo.append(('Efetuar Matrícula Direta', '/edu/efetuar_matricula/', 0))
    box_processamento_periodo.append(('Fechar Período', '/edu/fechar_periodo_letivo/', 0))
    if in_group(request.user, 'Administrador Acadêmico'):
        box_processamento_periodo.append(('Abrir Período', '/edu/abrir_periodo_letivo/', 0))
    painel.append(('Procedimentos', box_processamento_periodo, 'protocolo'))

    if request.user.has_perm('edu.change_solicitacaocertificadoenem'):
        box_certificado_enem = []
        contador = SolicitacaoCertificadoENEM.objects.filter(data_avaliacao__isnull=True).count()
        if contador:
            box_certificado_enem.append(('Solicitações Pendentes', '/admin/edu/solicitacaocertificadoenem/?tab=tab_pendentes', contador))
            painel.append(('Certificado ENEM', box_certificado_enem, 'protocolo'))

    if request.user.has_perm('edu.add_cursocampus'):
        box_cursos = []
        contador = CursoCampus.locals.sem_coordenadores().count()
        if contador:
            box_cursos.append(('Sem Coordenadores', '/admin/edu/cursocampus/?tab=tab_sem_coordenadores', f'{contador}'))
        contador = CursoCampus.locals.nao_vinculados_diretoria().count()
        if contador:
            box_cursos.append(('Não-Vinculados à Diretoria', '/admin/edu/cursocampus/?tab=nao_vinculados_diretoria', f'{contador}'))
        if box_cursos:
            painel.append(('Cursos com Pendência', box_cursos, 'curso'))

    return locals()


@rtr()
@group_required('Coordenador de Curso,Coordenador de Modalidade Acadêmica,Secretário Acadêmico,Administrador Acadêmico,Diretor Acadêmico,Diretor Geral')
def painel_controle(request):
    return contexto_painel_controle(request)


@rtr()
@login_required()
def disciplina(request, pk):
    obj = get_object_or_404(Diario.objects, pk=pk)
    title = f'Disciplina: {obj}'
    aluno = get_object_or_404(Aluno, pessoa_fisica=request.user.get_profile())
    is_aluno_matriculado = obj.matriculadiario_set.filter(matricula_periodo__aluno=aluno).exists()

    if not is_aluno_matriculado:
        return httprr('/', 'Você não tem permissão para isso', 'erro')
    aulas = obj.get_aulas()
    matricula_diario_qs = obj.matriculadiario_set.filter(matricula_periodo__aluno=aluno)
    if matricula_diario_qs.exists():
        matricula_diario = matricula_diario_qs[0]
        matricula_diario.set_faltas(aulas)
        materiais = MaterialDiario.objects.filter(professor_diario__diario=obj).order_by('-data_vinculacao')
        turnos = obj.get_horarios_aula_por_turno()
    turnos.as_form = False

    topicos = obj.topicodiscussao_set.all()
    trabalhos = []
    for trabalho in obj.trabalho_set.all():
        qs = trabalho.entregatrabalho_set.filter(matricula_diario__matricula_periodo__aluno__matricula=request.user.username)
        trabalho.data_entrega = qs.exists() and qs[0].data_entrega or None
        trabalhos.append(trabalho)

    return locals()


@rtr()
@group_required('Administrador Acadêmico,Diretor Acadêmico,Coordenador de Curso,Coordenador de Modalidade Acadêmica,Secretário Acadêmico,Pedagogo, Professor')
def material_aula(request, pk):
    title = 'Visualização de Material de Aula'
    obj = get_object_or_404(MaterialAula, pk=pk, professor__vinculo__user__username=request.user.username)
    return locals()


@rtr()
@permission_required('edu.view_materialaula')
def registrar_acesso_aluno_material_aula(request, pk_diario, pk_materialaula):
    aluno = get_object_or_404(Aluno, vinculos__user=request.user)
    materialaula = get_object_or_404(MaterialAula, pk=pk_materialaula)
    diario = get_object_or_404(Diario, pk=pk_diario)
    descricao = f'O usuário visualizou o {materialaula._meta.verbose_name} #{materialaula.pk}'
    if settings.USE_HISTORY:
        log_view_object(materialaula)
    if settings.USE_EDU_LOG:
        log = Log()
        log.set_up(aluno.get_vinculo().user, Log.VISUALIZACAO, materialaula, descricao)
        log.ref_aluno = aluno.pk
        log.ref_diario = diario.pk
        log.save()
    return HttpResponseRedirect(materialaula.get_absolute_url())


@rtr()
@permission_required('edu.add_materialaula')
def log_acesso_material_aula(request, pk_diario, pk_materialaula):
    materialaula = get_object_or_404(MaterialAula, pk=pk_materialaula)
    title = f'{materialaula}'
    logs = Log.objects.filter(ref=pk_materialaula, modelo='MaterialAula', tipo=Log.VISUALIZACAO, ref_diario=pk_diario)
    return locals()


@rtr()
@login_required()
def disciplinas(request):
    title = 'Minhas Disciplinas'
    aluno = get_object_or_404(Aluno, matricula=request.user.username)
    periodo_letivo_atual = PeriodoLetivoAtual.get_instance(request, aluno)
    if aluno.matriculaperiodo_set.exists():
        if aluno.matriculaperiodo_set.filter(ano_letivo__ano=periodo_letivo_atual.ano, periodo_letivo=periodo_letivo_atual.periodo).exists():
            matricula_periodo = aluno.matriculaperiodo_set.get(ano_letivo__ano=periodo_letivo_atual.ano, periodo_letivo=periodo_letivo_atual.periodo)
        else:
            matricula_periodo = None
    else:
        return httprr('/', 'Você ainda não cursou nenhum período.', 'error')
    return locals()


@rtr()
@permission_required('edu.view_solicitacaousuario')
def solicitacaousuario(request, pk):
    obj = get_object_or_404(SolicitacaoUsuario.locals, pk=pk)

    filho_verbose_name = obj.sub_instance_title()
    filho = obj.sub_instance()
    title = f'{filho_verbose_name} {pk}'

    obj = get_object_or_404(filho.__class__.locals, pk=pk)

    eh_acompanhamento_etep = filho_verbose_name == 'Solicitação de Acompanhamento ETEP'
    eh_atividade_complementar = filho_verbose_name == 'Solicitação de Atividade Complementar'
    eh_prorrogacao_etapa = filho_verbose_name == 'Solicitação de Prorrogação de Etapa'
    eh_relacamento_e_precisa_prorrogar_posse = filho_verbose_name == 'Solicitação de Relançamento de Etapa' and filho.precisa_prorrogar_posse()

    pode_ver_etep = False
    pode_realizar_procedimento_etep = False
    if eh_acompanhamento_etep:
        pode_ver_etep = in_group(request.user, 'Professor, Pedagogo, Administrador Acadêmico')
        setor = obj.aluno.curso_campus.diretoria.setor
        tem_permissao_realizar_procedimentos_etep = etep_perms.tem_permissao_realizar_procedimentos_etep(request, setor)
        if 'etep' in settings.INSTALLED_APPS:
            Acompanhamento = apps.get_model('etep', 'Acompanhamento')
            acompanhamento = Acompanhamento.objects.filter(aluno=obj.aluno)
        else:
            acompanhamento = []
    if not request.user.has_perm('edu.view_solicitacaorelancamentoetapa') and not pode_ver_etep:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    aluno = Aluno.objects.filter(pessoa_fisica__user=obj.solicitante)
    if aluno:
        aluno = aluno[0]
    atender = request.GET.get('atender', False)
    if request.user.has_perm('edu.change_solicitacaousuario'):
        if 'avisar_coordenador' in request.GET and eh_atividade_complementar:
            if filho.enviar_email_coordenador():
                filho.atender(request.user)
                return httprr('..', 'Email enviado com sucesso.')
            else:
                return httprr('..', 'Falha ao tentar enviar email.')
        if atender:
            filho.atender(request.user)
            return httprr('..', 'Solicitação deferida com sucesso.')
    return locals()


@permission_required('edu.efetuar_matricula')
@rtr()
def integralizar_alunos(request, matriz_id):
    erros = request.session.get('pendencias_integralizacao')
    if 'xls' in request.GET and erros:
        rows = [['#', 'Aluno', 'Matrícula', 'Pendência']]
        count = 0
        for erro in erros:
            for mensagem in erro['mensagens']:
                count += 1
                row = [count, erro['aluno'], erro['matricula'], mensagem]
                rows.append(row)
        return XlsResponse(rows)

    title = 'Migração de Alunos Ativos do Q-Acadêmico'
    ano_corrente = get_object_or_404(Ano, ano=datetime.datetime.now().year)
    initial = dict(ano_letivo=ano_corrente.id)
    form = ImportarAlunosAtivosForm(matriz_id, data=request.POST or None, files=request.POST and request.FILES or None, initial=initial)
    if form.is_valid():
        return form.processar(request)
    else:
        try:
            request.session['pendencias_integralizacao'] = [
                dict(aluno=aluno.get_nome_social_composto(), matricula=aluno.matricula, mensagens=mensagens) for aluno, mensagens in form.erros
            ]
        except Exception:
            pass

    return locals()


@login_required()
@rtr()
@permission_required('edu.view_abonofaltas')
def abonofaltas(request, pk):
    obj = get_object_or_404(AbonoFaltas.locals, pk=pk)
    title = f'Justificativa de Falta - {obj.aluno}'
    is_professor_do_diario = False
    professor = Professor.objects.filter(vinculo__user=request.user)
    if professor:
        is_professor_do_diario = Falta.objects.filter(
            aula__professor_diario__diario__in=professor[0].professordiario_set.values_list('diario', flat=True), abono_faltas=obj
        ).exists()

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, obj.aluno.curso_campus)
    if not pode_realizar_procedimentos and not is_professor_do_diario and not request.user.has_perm('edu.view_abonofaltas'):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error', close_popup=True)
    return locals()


@login_required()
@rtr()
def realizar_cancelamento_matricula(request, matricula_periodo_pk):
    title = 'Cancelar Matrícula'
    matricula_periodo = get_object_or_404(MatriculaPeriodo, pk=matricula_periodo_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, matricula_periodo.aluno.curso_campus)
    if not pode_realizar_procedimentos or not matricula_periodo.pode_realizar_procedimento_matricula():
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = CancelarMatriculaForm(matricula_periodo_pk, request.POST or None, initial=dict(data=datetime.datetime.today()))
    if form.is_valid():
        form.save()
        return httprr('..', 'Cancelamento realizado com sucesso.')
    return locals()


@login_required()
@rtr()
def realizar_trancamento_matricula(request, matricula_periodo_pk):
    title = 'Trancar Matrícula'
    matricula_periodo = get_object_or_404(MatriculaPeriodo, pk=matricula_periodo_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, matricula_periodo.aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not matricula_periodo.pode_realizar_procedimento_matricula():
        return httprr('..', 'A matrícula deste aluno não pode ser trancada.', 'error')

    form = TrancarMatriculaForm(matricula_periodo_pk, request.POST or None, initial=dict(data=datetime.datetime.today()))
    if form.is_valid():
        try:
            form.save()
        except ValidationError as e:
            return httprr(matricula_periodo.aluno.get_absolute_url(), e.message, 'error', close_popup=True)
        return httprr(matricula_periodo.aluno.get_absolute_url(), 'Trancamento realizado com sucesso.', close_popup=True)
    return locals()


@login_required()
@rtr()
def calcular_ira_parcial(request, aluno_pk):
    aluno = get_object_or_404(Aluno, pk=aluno_pk)
    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    ira_parcial = aluno.calcular_indice_rendimento(parcial=True)
    return locals()


@transaction.atomic
@login_required()
@rtr()
def realizar_transferencia_curso(request, matricula_periodo_pk, tipo):
    title = f'Transferência - {tipo}'
    matricula_periodo = get_object_or_404(MatriculaPeriodo, pk=matricula_periodo_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, matricula_periodo.aluno.curso_campus)
    if not pode_realizar_procedimentos or not matricula_periodo.aluno.get_ultima_matricula_periodo().pode_realizar_transferencia():
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = TransferenciaCursoForm(matricula_periodo_pk, tipo, request.POST or None, initial=dict(data=datetime.datetime.now()))
    if form.is_valid():
        form.save()
        aluno = form.instance.matricula_periodo.aluno.clonar(form.cleaned_data['matriz_curso'], form.cleaned_data['forma_ingresso'], form.cleaned_data['turno'], data=form.instance.data)
        return httprr('..', mark_safe(f'Transferência realizada com sucesso. (<a target="_blank" href="/edu/comprovante_matricula_pdf/{aluno.pk}/">Imprimir Comprovante</a>) '))
    return locals()


@login_required()
@rtr()
def realizar_transferencia_externa(request, matricula_periodo_pk):
    title = 'Realizar Transferência'

    matricula_periodo = get_object_or_404(MatriculaPeriodo, pk=matricula_periodo_pk)
    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, matricula_periodo.aluno.curso_campus)
    if not pode_realizar_procedimentos or not matricula_periodo.aluno.get_ultima_matricula_periodo().pode_realizar_transferencia():
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = TransferenciaExternaForm(matricula_periodo_pk, request.POST or None, initial=dict(data=datetime.datetime.today()))
    if form.is_valid():
        form.save()
        return httprr('..', 'Transferência externa realizada com sucesso.')
    return locals()


@permission_required('edu.efetuar_matricula')
@rtr()
def realizar_matricula_vinculo(request, matricula_periodo_pk):
    title = 'Realizar Matrícula Vínculo'
    matricula_periodo = get_object_or_404(MatriculaPeriodo, pk=matricula_periodo_pk)
    if not matricula_periodo.is_aberto():
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    form = MatriculaVinculoForm(matricula_periodo_pk, request.POST or None, initial=dict(data=datetime.datetime.today()))
    if form.is_valid():
        form.save()
        return httprr('..', 'Matrícula Vínculo realizada com sucesso.')
    return locals()


@group_required('Administrador Acadêmico')
@rtr()
def importar_alunos(request):
    title = 'Importar Alunos do Q-Acadêmico'
    form = ImportacaoAlunosForm(request.POST or None)
    if form.is_valid():
        form.processar()
        return httprr('/admin/edu/historicoimportacao/', 'Alunos importados com sucesso.')

    return locals()


@login_required()
@rtr()
def reintegrar_aluno(request, matricula_periodo_pk):
    title = 'Reintegrar Aluno'
    matricula_periodo = get_object_or_404(MatriculaPeriodo, pk=matricula_periodo_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, matricula_periodo.aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not matricula_periodo.is_cancelado():
        return httprr('..', 'Impossível reintegrar aluno.', 'error')

    form = ReintegrarAlunoForm(matricula_periodo, data=request.POST or None, initial=dict(data=datetime.datetime.today()))
    if form.is_valid():
        ano_letivo = form.cleaned_data['ano_letivo']
        periodo_letivo = form.cleaned_data['periodo_letivo']

        procedimento = form.save(commit=False)
        procedimento.tipo = 'Reintegração'
        procedimento.situacao_matricula_anterior = matricula_periodo.aluno.situacao

        matricula_periodo.reintegrar_aluno(procedimento, ano_letivo, periodo_letivo)
        return httprr('..', 'Aluno reintegrado com sucesso.')
    return locals()


@login_required()
@rtr()
def certificar_conhecimento(request, aluno_pk, componente_curricular_pk):
    componente_curricular = get_object_or_404(ComponenteCurricular, pk=componente_curricular_pk)
    title = f'Certificar Conhecimento - {componente_curricular.componente.descricao_historico}'
    aluno = get_object_or_404(Aluno, pk=aluno_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    extrapola_percentual_max_aproveitamento = False
    if aluno.matriz.estrutura.percentual_max_aproveitamento:
        ch_componentes_aproveitaveis = (
            aluno.matriz.ch_componentes_obrigatorios + aluno.matriz.ch_componentes_optativos + aluno.matriz.ch_componentes_eletivos + aluno.matriz.ch_seminarios
        )
        extrapola_percentual_max_aproveitamento = (
            aluno.get_ch_certificada_ou_aproveitada() + (componente_curricular.ch_presencial + componente_curricular.ch_pratica)
            > aluno.matriz.estrutura.percentual_max_aproveitamento * ch_componentes_aproveitaveis / 100
        )
    extrapola_quantidade_max_creditos_aproveitamento = False
    if aluno.matriz.estrutura.quantidade_max_creditos_aproveitamento:
        extrapola_quantidade_max_creditos_aproveitamento = (
            aluno.get_creditos_certificados_ou_aproveitados() + componente_curricular.componente.ch_qtd_creditos > aluno.matriz.estrutura.quantidade_max_creditos_aproveitamento
        )
    matriculas_diario = MatriculaDiario.objects.filter(
        situacao=MatriculaDiario.SITUACAO_CURSANDO, matricula_periodo__aluno=aluno, diario__componente_curricular__componente=componente_curricular.componente.pk
    )
    qs = CertificacaoConhecimento.objects.filter(componente_curricular=componente_curricular, matricula_periodo__aluno=aluno)
    instance = qs.exists() and qs[0] or None
    form = CertificarConhecimentoForm(aluno, componente_curricular, request.POST or None, instance=instance, request=request)
    if form.is_valid():
        certificacao = form.save()
        if certificacao.is_aluno_aprovado():
            matriculas_diario.delete()
        return httprr('..', 'Certificação cadastrada com sucesso.')
    return locals()


@login_required()
@rtr()
def aproveitar_estudo(request, aluno_pk, componente_curricular_pk):
    componente_curricular = get_object_or_404(ComponenteCurricular, pk=componente_curricular_pk)
    title = f'Aproveitar Estudo - {componente_curricular.componente.descricao_historico}'
    aluno = get_object_or_404(Aluno, pk=aluno_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    extrapola_percentual_max_aproveitamento = False
    if aluno.matriz.estrutura.percentual_max_aproveitamento and not aluno.matriz.estrutura.formas_ingresso_ignoradas_aproveitamento.filter(pk=aluno.forma_ingresso.pk).exists():
        ch_componentes_aproveitaveis = (
            aluno.matriz.ch_componentes_obrigatorios + aluno.matriz.ch_componentes_optativos + aluno.matriz.ch_componentes_eletivos + aluno.matriz.ch_seminarios
        )
        extrapola_percentual_max_aproveitamento = (
            aluno.get_ch_certificada_ou_aproveitada() + (componente_curricular.ch_presencial + componente_curricular.ch_pratica)
            > aluno.matriz.estrutura.percentual_max_aproveitamento * ch_componentes_aproveitaveis / 100
        )
    extrapola_quantidade_max_creditos_aproveitamento = False
    if aluno.matriz.estrutura.quantidade_max_creditos_aproveitamento:
        extrapola_quantidade_max_creditos_aproveitamento = (
            aluno.get_creditos_certificados_ou_aproveitados() + componente_curricular.componente.ch_qtd_creditos > aluno.matriz.estrutura.quantidade_max_creditos_aproveitamento
        )

    matriculas_diario = MatriculaDiario.objects.filter(
        situacao=MatriculaDiario.SITUACAO_CURSANDO, matricula_periodo__aluno=aluno, diario__componente_curricular=componente_curricular
    )
    qs = AproveitamentoEstudo.objects.filter(componente_curricular__componente=componente_curricular.componente.pk, matricula_periodo__aluno=aluno)
    instance = qs.first()
    form = AproveitamentoEstudoForm(aluno, componente_curricular, request.POST or None, instance=instance, request=request)
    if form.is_valid():
        aproveitamento = form.save()
        matriculas_diario.delete()
        return httprr('..', 'Aproveitamento adicionado com sucesso.')
    return locals()


@login_required()
@rtr()
def aproveitar_componente(request, aluno_pk, componente_curricular_pk):
    componente_curricular = get_object_or_404(ComponenteCurricular, pk=componente_curricular_pk)
    title = f'{componente_curricular.componente.descricao} - {componente_curricular.componente.ch_hora_relogio} h'
    aluno = get_object_or_404(Aluno, pk=aluno_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    matriculas_diario = MatriculaDiario.objects.filter(
        situacao=MatriculaDiario.SITUACAO_CURSANDO, matricula_periodo__aluno=aluno, diario__componente_curricular=componente_curricular
    )
    qs = AproveitamentoComponente.objects.filter(componente_curricular=componente_curricular, matricula_periodo__aluno=aluno)
    instance = qs.exists() and qs[0] or None
    form = AproveitamentoComponenteForm(aluno, componente_curricular, request.POST or None, instance=instance)
    if form.is_valid():
        aproveitamento = form.save()
        matriculas_diario.delete()
        return httprr('..', 'Equivalência cadastrada com sucesso.')
    return locals()


@permission_required('edu.efetuar_matricula')
@rtr()
def evadir_alunos_selecionados(request):
    if 'alunos_selecionados' in request.POST:
        ids = request.POST.getlist('alunos_selecionados')
        if ids:
            alunos_selecionados = Aluno.locals.filter(id__in=ids)
            return tasks.evadir_alunos_lote(alunos_selecionados)
    else:
        return httprr('/')


@permission_required('edu.efetuar_matricula')
@rtr()
def evasao_em_lote(request):
    title = 'Evasão em Lote'
    form = EvasaoEmLoteForm(data=request.GET or None)
    if form.is_valid():
        alunos = form.processar()

        if 'xls' in request.GET:
            return tasks.exportar_evasao_em_lote_xls(alunos)

    return locals()


@permission_required('edu.efetuar_matricula')
@rtr()
def evadir_aluno(request, pk):
    aluno = get_object_or_404(Aluno.locals, pk=pk)
    try:
        aluno.get_ultima_matricula_periodo().evadir('Evasão Individual')
        return httprr(f'/edu/aluno/{aluno.matricula}', 'Aluno evadido com sucesso.')
    except ValidationError as e:
        return httprr(f'/edu/aluno/{aluno.matricula}', f'{e.messages[0]} de evasão.', 'error')


@login_required()
@rtr()
def visualizar_certificacao(request, aluno_pk, componente_curricular_pk):
    title = 'Visualizar Certificação do Conhecimento'
    obj = CertificacaoConhecimento.objects.filter(matricula_periodo__aluno__pk=aluno_pk, componente_curricular__pk=componente_curricular_pk)[0]
    return locals()


@login_required()
@rtr()
def visualizar_agenda_defesas(request):
    title = 'Projetos Finais'
    qs = Aluno.objects.filter(matricula=request.user.username)
    curso_campus = qs.exists() and qs[0].curso_campus or None
    projetos_finais = ProjetoFinal.objects.filter(data_defesa__gte=datetime.datetime.today(), matricula_periodo__aluno__curso_campus=curso_campus)
    return locals()


@login_required()
@rtr()
def visualizar_aproveitamento(request, aluno_pk, componente_curricular_pk):
    title = 'Visualizar Aproveitamento'
    obj = AproveitamentoEstudo.objects.filter(matricula_periodo__aluno__pk=aluno_pk, componente_curricular__pk=componente_curricular_pk).first()
    return locals()


@login_required()
@rtr()
def visualizar_equivalencia(request, aluno_pk, componente_curricular_pk):
    title = 'Visualizar Equivalência'
    obj = AproveitamentoComponente.objects.filter(matricula_periodo__aluno__pk=aluno_pk, componente_curricular__pk=componente_curricular_pk).first()
    return locals()


@login_required()
@rtr()
def adicionar_projeto_final(request, aluno_pk, projetofinal_pk=None):
    title = '{} Trabalho de Conclusão de Curso / Relatório'.format(projetofinal_pk and 'Editar' or 'Adicionar')

    projeto_final = None
    if projetofinal_pk:
        projeto_final = get_object_or_404(ProjetoFinal, pk=projetofinal_pk)

    aluno = get_object_or_404(Aluno, pk=aluno_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = ProjetoFinalForm(aluno, request.POST or None, instance=projeto_final, request=request)

    if form.is_valid():
        obj = form.save()

        if not projetofinal_pk:
            return httprr(f'/edu/aluno/{aluno.matricula}/?tab=projeto', 'TCC / Relatório adicionado com sucesso.')
        else:
            return httprr(f'/edu/aluno/{aluno.matricula}/?tab=projeto', 'TCC / Relatório atualizado com sucesso.')

    return locals()


@login_required()
@rtr()
def lancar_resultado_projeto_final(request, projetofinal_pk=None):
    title = 'Lançar Resultado de TCC / Relatório'
    projeto_final = get_object_or_404(ProjetoFinal.objects, pk=projetofinal_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, projeto_final.matricula_periodo.aluno.curso_campus)
    if not pode_realizar_procedimentos:
        if not projeto_final.presidente.vinculo == request.user.get_vinculo():
            return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    if not projeto_final.pode_ser_editado():
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    initial = dict(resultado_nota=projeto_final.nota, tipo_documento=(projeto_final.documento_url and 1 or 2))

    form = LancarResultadoProjetoFinalForm(request.POST or None, files=request.FILES or None, instance=projeto_final, initial=initial)
    if form.is_valid():
        complemento = ''
        form.save()

        if form.tipo_ata == 'eletronica':
            if projeto_final.presidente and projeto_final.presidente.vinculo == request.user.get_vinculo():
                return httprr(
                    '/admin/edu/ataeletronica/?tab=tab_pendentes',
                    'Resultado registrado com sucesso. Realize a assinatura da ata eletrônica'
                )
            complemento = 'A ata eletrônica foi gerada e as solicitações de assinatura foram enviadas para os membros da banca por e-mail.'

        return httprr('/edu/aluno/{}/?tab=projeto'.format(
            projeto_final.matricula_periodo.aluno.matricula), f'Resultado registrado com sucesso. {complemento}'
        )

    return locals()


@login_required()
@rtr()
def upload_documento_projeto_final(request, projetofinal_pk=None):
    title = 'Upload Documento Final de TCC/Relatório'
    projeto_final = get_object_or_404(ProjetoFinal.objects, pk=projetofinal_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, projeto_final.matricula_periodo.aluno.curso_campus)
    if not pode_realizar_procedimentos:
        if not projeto_final.presidente.vinculo == request.user.get_vinculo():
            return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = UploadDocumentoProjetoFinalForm(request.POST or None, files=request.FILES or None, instance=projeto_final)
    if form.is_valid():
        form.save()
        return httprr('/edu/aluno/{}/?tab=projeto'.format(
            projeto_final.matricula_periodo.aluno.matricula), 'Resultado registrado com sucesso.'
        )

    return locals()


@documento('Ata de Projeto Final')
@login_required()
@rtr('ata_projeto_final_pdf.html')
def ata_eletronica_projeto_final_pdf(request, pk):
    obj = get_object_or_404(AtaEletronica, pk=pk)
    dados_assinatura = []
    for assinatura in obj.get_assinaturas().filter(data__isnull=False):
        dados_assinatura.append(
            dict(
                nome=assinatura.pessoa_fisica.nome,
                matricula=assinatura.pessoa_fisica.cpf,
                data=assinatura.data.strftime('%d/%m/%Y %H:%M:%S'),
                chave=assinatura.chave
            )
        )
    request.GET._mutable = True
    request.GET['dados_assinatura'] = json.dumps(dados_assinatura)
    request.GET._mutable = False
    return imprimir_ata_projeto_final_pdf(request, obj.projeto_final.pk)


def visualizar_ata_eletronica(request, pk):
    obj = get_object_or_404(AtaEletronica, pk=pk)
    if not obj.get_assinaturas().filter(data__isnull=True).exists():
        return HttpResponseRedirect(f'/edu/ata_eletronica_projeto_final_pdf/{obj.pk}/')
    else:
        return HttpResponseRedirect(f'/edu/ata_projeto_final_pdf/{obj.projeto_final.pk}/')


@documento()
@login_required()
@rtr()
def ata_projeto_final_pdf(request, projetofinal_pk):
    return imprimir_ata_projeto_final_pdf(request, projetofinal_pk)


def imprimir_ata_projeto_final_pdf(request, projetofinal_pk):
    title = 'Lançar Resultado de Trabalho de Conclusão de Curso'
    obj = get_object_or_404(ProjetoFinal.objects, pk=projetofinal_pk)
    ata_eletronica = obj.get_ata_eletronica()
    artigo_aluno = obj.matricula_periodo.aluno.pessoa_fisica.sexo == 'F' and 'a' or 'o'
    artigo_presidente = obj.presidente and obj.presidente.vinculo and obj.presidente.vinculo.pessoa.pessoafisica.sexo == 'F' and 'a' or 'o'
    artigo_tipo = obj.tipo in ('Monografia', 'Dissertação', 'Tese') and 'da' or 'do'
    uo = obj.matricula_periodo.aluno.curso_campus.diretoria.setor.uo
    hoje = dateformat.format(datetime.date.today(), r'd \d\e F \d\e Y')
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()
    lista_professores = []
    lista_assinaturas = set()
    coorienadores = obj.coorientadores.all().values_list('nome', flat=True)
    if obj.presidente:
        professor = obj.get_titulo_participante('presidente')
        lista_professores.append(professor)
        lista_assinaturas.add(professor[2])
    if obj.examinador_interno:
        professor = obj.get_titulo_participante('examinador_interno')
        lista_professores.append(professor)
        lista_assinaturas.add(professor[2])
    if obj.examinador_externo:
        professor = obj.get_titulo_participante('examinador_externo')
        lista_professores.append(professor)
        lista_assinaturas.add(professor[2])
    if obj.terceiro_examinador:
        professor = obj.get_titulo_participante('terceiro_examinador')
        lista_professores.append(professor)
        lista_assinaturas.add(professor[2])
    if obj.suplente_interno:
        professor = obj.get_titulo_participante('suplente_interno')
        lista_professores.append(professor)
        lista_assinaturas.add(professor[2])
    if obj.suplente_externo:
        professor = obj.get_titulo_participante('suplente_externo')
        lista_professores.append(professor)
        lista_assinaturas.add(professor[2])
    if obj.terceiro_suplente:
        professor = obj.get_titulo_participante('terceiro_suplente')
        lista_professores.append(professor)
        lista_assinaturas.add(professor[2])
    return locals()


@login_required()
@documento('Declaração de Participação em Projeto Final', False, validade=30, enumerar_paginas=False, modelo='edu.projetofinal')
@rtr()
def declaracao_participacao_projeto_final_pdf(request, pk, participante):
    title = 'Imprimir Declaração de Participação em Projeto Final'
    obj = get_object_or_404(ProjetoFinal.objects, pk=pk)
    if participante == 'coorientador':
        professor = obj.coorientadores.get(pk=request.GET['coorientador'])
        sexo = professor.sexo
        participacao = 'Coorientador'
    else:
        sexo, participacao, _ = obj.get_titulo_participante(participante)
        professor = None
        if hasattr(obj, participante):
            professor = getattr(obj, participante)
        else:
            return httprr('..', 'Escolha um participante válido.', 'error')
    pessoa_fisica = hasattr(professor, 'vinculo') and professor.vinculo.relacionamento.pessoa_fisica or professor
    artigo_professor = sexo == 'F' and 'a' or 'o'
    artigo_aluno = obj.matricula_periodo.aluno.pessoa_fisica.sexo == 'F' and 'a' or 'o'
    lista_professores = []
    if obj.presidente and obj.orientador != obj.presidente:
        lista_professores.append(obj.get_titulo_participante('presidente'))
    if obj.orientador:
        lista_professores.append(obj.get_titulo_participante('orientador'))
    if obj.examinador_interno:
        lista_professores.append(obj.get_titulo_participante('examinador_interno'))
    if obj.examinador_externo:
        lista_professores.append(obj.get_titulo_participante('examinador_externo'))
    if obj.terceiro_examinador:
        lista_professores.append(obj.get_titulo_participante('terceiro_examinador'))
    if obj.suplente_interno:
        lista_professores.append(obj.get_titulo_participante('suplente_interno'))
    if obj.suplente_externo:
        lista_professores.append(obj.get_titulo_participante('suplente_externo'))
    if obj.terceiro_suplente:
        lista_professores.append(obj.get_titulo_participante('terceiro_suplente'))
    pks = [item[2].pk for item in lista_professores]
    for coorientador in obj.coorientadores.exclude(pk__in=pks):
        sexo = coorientador.sexo or 'M'
        if sexo == 'M':
            lista_professores.append(('M', 'Coorientador', coorientador))
        else:
            lista_professores.append(('F', 'Coorientadora', coorientador))
    if (
        not perms.tem_permissao_realizar_procedimentos(request.user, obj.matricula_periodo.aluno)
        and not perms.is_orientador(request, obj.matricula_periodo.aluno)
        and not perms.is_coorientador(request, obj.matricula_periodo.aluno)
        and not perms.is_examinador(request, obj.matricula_periodo.aluno)
        and not perms.is_presidente(request, obj.matricula_periodo.aluno)
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    uo = obj.matricula_periodo.aluno.curso_campus.diretoria.setor.uo
    hoje = dateformat.format(datetime.date.today(), r'd \d\e F \d\e Y')
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()
    return locals()


@login_required()
@rtr()
def declaracao_participacao_projeto_final(request, projetofinal_pk):
    title = 'Imprimir Declaração de Participação em Projeto Final'
    obj = get_object_or_404(ProjetoFinal.objects, pk=projetofinal_pk)

    if not perms.tem_permissao_realizar_procedimentos(request.user, obj.matricula_periodo.aluno) and not perms.is_orientador(request, obj.matricula_periodo.aluno):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = ParticipacaoProjetoFinalForm(projeto_final=obj)

    participante = request.GET.get('participante')
    if participante:
        return HttpResponseRedirect(f'/edu/declaracao_participacao_projeto_final_pdf/{projetofinal_pk}/{participante}/')
    return locals()


@rtr()
@login_required()
def listar_diarios_matricula_aluno(request, matricula_periodo_pk):
    title = 'Matricular em Diário'
    matricula_periodo = get_object_or_404(MatriculaPeriodo, pk=matricula_periodo_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, matricula_periodo.aluno.curso_campus)
    if not pode_realizar_procedimentos or not matricula_periodo.pode_matricular_diario():
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    diarios_matriculados = Diario.objects.none()
    if int(request.GET.get('page', 1)) == 1:
        diarios_matriculados = Diario.objects.filter(id__in=matricula_periodo.matriculadiario_set.values_list('diario__id', flat=True))

    remover_diario_id = request.GET.get('remover_diario_id')
    if remover_diario_id:
        md = matricula_periodo.matriculadiario_set.filter(diario__id=remover_diario_id).first()
        if md and md.can_delete():
            md.delete()
            return httprr(request.META.get('HTTP_REFERER', '.'), 'Aluno removido do diário com sucesso.')
        else:
            return httprr(
                request.META.get('HTTP_REFERER', '.'),
                'O aluno não pode ser removido do diário pois ele possui falta/nota lançada no sistema',
                'error',
            )

    form = ListarDiarioMatriculaAlunoForm(matricula_periodo, request.GET or None)

    if form.is_valid():
        diarios = form.processar()

    return locals()


@rtr()
@login_required()
def matricular_aluno_diario(request, matricula_periodo_pk, diario_pk):
    title = 'Matricular em Diário'
    matricula_periodo = get_object_or_404(MatriculaPeriodo, pk=matricula_periodo_pk)
    diario = get_object_or_404(Diario, pk=diario_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, matricula_periodo.aluno.curso_campus)
    if not pode_realizar_procedimentos or not matricula_periodo.pode_matricular_diario():
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    alertas = []

    pode_matricular, msg = matricula_periodo.aluno.pode_ser_matriculado_no_diario(diario)
    if not pode_matricular:
        return httprr('..', msg, 'error')
    if pode_matricular and msg:
        alertas.append(msg)

    if not diario.horarioauladiario_set.exists():
        alertas.append('Diário sem horário definido.')

    if matricula_periodo.atingiu_maximo_disciplinas():
        alertas.append('A matricula do aluno no diário, excede o número máximo de disciplinas permitidas para o período de referência.')

    form = MatricularDiarioForm(request.POST or None)
    if form.is_valid():
        form.processar(matricula_periodo, diario)
        return httprr('..', 'Aluno matriculado com sucesso.')

    return locals()


@rtr()
@login_required()
def matricular_aluno_turma(request, aluno_pk):
    title = 'Matricular em Turma'
    aluno = get_object_or_404(Aluno, pk=aluno_pk)
    matricula_periodo = aluno.get_ultima_matricula_periodo()

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if (
        not pode_realizar_procedimentos
        or not matricula_periodo.pode_matricular_diario()
        or not aluno.matriz.estrutura.tipo_avaliacao in [EstruturaCurso.TIPO_AVALIACAO_SERIADO, EstruturaCurso.TIPO_AVALIACAO_MODULAR]
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if matricula_periodo.turma:
        return httprr('..', 'O aluno selecionado já possui uma turma.', 'error')

    form = MatricularAlunoTurmaForm(matricula_periodo, data=request.POST or None)

    if form.is_valid():
        form.processar()
        return httprr('..', 'O aluno foi matriculado na turma com sucesso.')

    return locals()


@rtr()
@permission_required('edu.reabrir_diario')
def matricular_aluno_avulso_diario(request, diario_pk):
    title = 'Matricular Aluno Avulso em Diário'

    diario = get_object_or_404(Diario, pk=diario_pk)
    form = MatricularAlunoAvulsoDiarioForm(diario, request.POST or None, request=request)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Aluno matriculado com sucesso.')

    return locals()


@login_required()
@rtr()
def cancelar_matricula_diario(request, matricula_diario_pk):
    matricula_diario = get_object_or_404(MatriculaDiario, pk=matricula_diario_pk)
    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, matricula_diario.matricula_periodo.aluno.curso_campus)
    url = request.META.get('HTTP_REFERER', '.')
    if not pode_realizar_procedimentos:
        return httprr(url, 'Você não tem permissão para realizar isso.', 'error')
    try:
        matricula_diario.cancelar()
    except ValidationError as e:
        return httprr(url, e.message, 'error')

    return httprr(url, 'Matrícula em diário cancelada com sucesso.')


@login_required()
@rtr()
def defazer_cancelamento_matricula_diario(request, matricula_diario_pk):
    matricula_diario = MatriculaDiario.objects.get(pk=matricula_diario_pk)
    ultima_matricula_periodo = matricula_diario.matricula_periodo.aluno.get_ultima_matricula_periodo()

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, ultima_matricula_periodo.aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not (
        matricula_diario.matricula_periodo.ano_letivo.ano == ultima_matricula_periodo.ano_letivo.ano
        and matricula_diario.matricula_periodo.periodo_letivo == ultima_matricula_periodo.periodo_letivo
    ):
        return httprr(
            f'{matricula_diario.matricula_periodo.aluno.get_absolute_url()}?tab=historico',
            'Não é possível desfazer o cancelamento devido ao diário não ser do período corrente do aluno.',
            'error',
        )

    matricula_diario.situacao = MatriculaDiario.SITUACAO_CURSANDO
    matricula_diario.save()

    return httprr(f'{matricula_diario.matricula_periodo.aluno.get_absolute_url()}?tab=historico', 'Cancelamento de matrícula em diário desfeito com sucesso.')


@rtr()
@login_required()
def visualizar_projetofinal(request, projetofinal_pk=None):
    obj = get_object_or_404(ProjetoFinal, pk=projetofinal_pk)
    return locals()


@login_required()
@rtr()
def salvar_relatorio(request, tipo, query_string):
    title = 'Salvar Consulta'
    form = SalvarRelatorioForm(request.POST or None, tipo=tipo)
    if form.is_valid():
        form.processar(query_string)
        return httprr(f'/edu/meus_relatorios/{tipo}/', 'Consulta salva com sucesso.', close_popup=True)
    return locals()


@login_required()
@rtr()
def meus_relatorios(request, tipo):
    del_historicorelatorio = request.GET.get('del_historicorelatorio')
    if del_historicorelatorio:
        historicorelatorio = get_object_or_404(HistoricoRelatorio, id=del_historicorelatorio, user=request.user)
        url_sem_parametro = historicorelatorio.get_url_sem_parametro()
        historicorelatorio.delete()
        return httprr(url_sem_parametro, 'Consulta excluída com sucesso.')
    title = 'Consultas Salvas Anteriormente'
    relatorios = request.user.historicorelatorio_set.filter(tipo=tipo)
    return locals()


@login_required()
@rtr()
def cadastrar_atividade_complementar(request, aluno_pk, atividadecomplementar_pk=None):
    title = '{} Atividade Complementar'.format(atividadecomplementar_pk and 'Editar' or 'Adicionar')
    aluno = get_object_or_404(Aluno, pk=aluno_pk)

    atividade_complementar = None
    if atividadecomplementar_pk:
        atividade_complementar = get_object_or_404(AtividadeComplementar.objects, pk=atividadecomplementar_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = AtividadeComplementarForm(
        request.POST or None, initial={'aluno': aluno.pk}, files=request.FILES or None, instance=atividade_complementar, request=request, as_aluno=False
    )

    if form.is_valid():
        form.save()
        redirect = '..'
        if not atividadecomplementar_pk:
            return httprr(redirect, 'Atividade complementar adicionada com sucesso.')
        else:
            return httprr(redirect, 'Atividade complementar atualizada com sucesso.')
    return locals()


@login_required()
@rtr()
def cadastrar_atividade_aprofundamento(request, aluno_pk, atividadeaprofundamento_pk=None):
    title = '{} Atividade Complementar'.format(atividadeaprofundamento_pk and 'Editar' or 'Adicionar')
    aluno = get_object_or_404(Aluno, pk=aluno_pk)

    atividade_aprofundamento = None
    if atividadeaprofundamento_pk:
        atividade_aprofundamento = get_object_or_404(AtividadeAprofundamento.objects, pk=atividadeaprofundamento_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = AtividadeAprofundamentoForm(
        request.POST or None, initial={'aluno': aluno.pk}, files=request.FILES or None, instance=atividade_aprofundamento, request=request, as_aluno=False
    )

    if form.is_valid():
        form.save()
        redirect = '..'
        if not atividadeaprofundamento_pk:
            return httprr(redirect, 'Atividade complementar adicionada com sucesso.')
        else:
            return httprr(redirect, 'Atividade complementar atualizada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.view_configuracaoatividadecomplementar')
def configuracaoatividadecomplementar(request, pk):
    obj = ConfiguracaoAtividadeComplementar.objects.get(pk=pk)
    title = 'Configuração da AACC'

    if 'desvincular_matriz' in request.GET and request.user.has_perm('edu.change_configuracaoatividadecomplementar'):
        matriz = Matriz.objects.get(pk=request.GET.get('desvincular_matriz'))
        matriz.configuracao_atividade_academica = None
        matriz.save()
        return httprr(f'/edu/configuracaoatividadecomplementar/{pk}/?tab=matrizes', 'Matriz desvinculada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.view_configuracaoatividadeaprofundamento')
def configuracaoatividadeaprofundamento(request, pk):
    obj = ConfiguracaoAtividadeAprofundamento.objects.get(pk=pk)
    title = 'Configuração da ATPa'

    if 'desvincular_matriz' in request.GET and request.user.has_perm('edu.change_configuracaoatividadeaprofundamento'):
        matriz = Matriz.objects.get(pk=request.GET.get('desvincular_matriz'))
        matriz.configuracao_atividade_aprofundamento = None
        matriz.save()
        return httprr(f'/edu/configuracaoatividadeaprofundamento/{pk}/?tab=matrizes', 'Matriz desvinculada com sucesso.')
    return locals()


@rtr()
@login_required()
def visualizar_atividade_complementar(request, atividadecomplementar_pk):
    obj = get_object_or_404(AtividadeComplementar, pk=atividadecomplementar_pk)
    return locals()


@rtr()
@login_required()
def atividadeaprofundamento(request, pk):
    obj = get_object_or_404(AtividadeAprofundamento, pk=pk)
    title = str(obj)
    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, obj.aluno.curso_campus)
    if pode_realizar_procedimentos:
        if 'deferir' in request.GET:
            if request.GET['deferir'] == '1':
                obj.deferida = True
                obj.save()
                return httprr('..', 'Deferimento realizado com sucesso')
            else:
                obj.deferida = None
                obj.save()
                return httprr('..', 'Cancelamento do deferimento realizado com sucesso')
        elif 'indeferir' in request.GET:
            if request.GET['indeferir'] == '1':
                form = IndeferirAtividadeComplementarForm(data=request.POST or None, instance=obj)
                if form.is_valid():
                    form.save()
                    return httprr('..', 'Indeferimento realizado com sucesso.')
            else:
                obj.deferida = None
                obj.razao_indeferimento = None
                obj.save()
                return httprr('..', 'Cancelamento do indeferimento realizado com sucesso')
    return locals()


@rtr()
@login_required()
def dados_atividade_complementar_ajax(request, aluno_pk, tipo_pk):
    obj = get_object_or_404(Aluno, pk=aluno_pk)
    tipos = obj.get_ch_atividades_complementares_por_tipo(True)
    tipo = None
    for var in tipos:
        if var.pk == int(tipo_pk):
            tipo = var
            break
    return locals()


@login_required()
def listar_atividades_complementares_ajax(request, aluno_pk, vinculacao):
    aluno = get_object_or_404(Aluno, pk=aluno_pk)
    if int(vinculacao) == AtividadeComplementarForm.VINCULADO_CURSO:
        tipos = TipoAtividadeComplementar.objects.filter(itemconfiguracaoatividadecomplementar__configuracao__matriz__aluno=aluno).distinct().values_list('id', 'descricao')
    else:
        tipos = (
            TipoAtividadeComplementar.objects.filter(modalidades__in=[aluno.curso_campus.modalidade])
            .exclude(itemconfiguracaoatividadecomplementar__configuracao__matriz__aluno=aluno)
            .distinct()
            .values_list('id', 'descricao')
        )
    return JsonResponse(list(tipos))


@rtr()
@permission_required('edu.change_configuracaoatividadecomplementar')
def vincular_configuracao_atividade_complementar(request, pk):
    title = 'Vincular Matriz'
    form = VincularConfiguracaoAtividadeComplementarForm(request.POST or None)
    if form.is_valid():
        obj = ConfiguracaoAtividadeComplementar.objects.get(pk=pk)
        for matriz in form.cleaned_data['matrizes']:
            if matriz.configuracao_atividade_academica:
                return httprr('.', f'Matriz({matriz}) já vinculada a configuração({matriz.configuracao_atividade_academica.descricao}).', 'error')

        for matriz in form.cleaned_data['matrizes']:
            matriz.configuracao_atividade_academica = obj
            matriz.save()
        return httprr('..', 'Matrizes vinculadas com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_configuracaoatividadeaprofundamento')
def vincular_configuracao_atividade_aprofundamento(request, pk):
    title = 'Vincular Matriz'
    form = VincularConfiguracaoAtividadeAprofundamentoForm(request.POST or None)
    if form.is_valid():
        obj = ConfiguracaoAtividadeAprofundamento.objects.get(pk=pk)
        for matriz in form.cleaned_data['matrizes']:
            if matriz.configuracao_atividade_aprofundamento:
                return httprr('.', f'Matriz({matriz}) já vinculada a configuração({matriz.configuracao_atividade_academica.descricao}).', 'error')

        for matriz in form.cleaned_data['matrizes']:
            matriz.configuracao_atividade_aprofundamento = obj
            matriz.save()
        return httprr('..', 'Matrizes vinculadas com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_configuracaoatividadecomplementar')
def adicionar_item_configuracao_aacc(request, pk):
    title = 'Adicionar Atividade Acadêmica'

    instance = None
    if 'atividadeacademica' in request.GET:
        instance = ItemConfiguracaoAtividadeComplementar.objects.get(pk=request.GET.get('atividadeacademica'))
        title = f'Editar Atividade Acadêmica - {instance.tipo.descricao}'
        atividade_complementar = AtividadeComplementar.objects.filter(tipo__itemconfiguracaoatividadecomplementar=instance).exists()
    form = ItemConfiguracaoAtividadeComplementarForm(request.POST or None, instance=instance, configuracao_pk=pk)
    if form.is_valid():
        form.instance.configuracao = ConfiguracaoAtividadeComplementar.objects.get(pk=pk)
        try:
            form.instance.save()
        except IntegrityError:
            return httprr('.', 'Não foi possível adicionar a atividade complementar pois ela já pertence a esta Configuração de AACCs', 'error')

        if instance:
            return httprr('..', 'Atividade acadêmica alterada com sucesso.')
        else:
            return httprr('..', 'Atividade acadêmica cadastrada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_configuracaoatividadeaprofundamento')
def adicionar_item_configuracao_atpa(request, pk):
    title = 'Adicionar Atividade de Aprofundamento'

    instance = None
    if 'atividadeaprofundamento' in request.GET:
        instance = ItemConfiguracaoAtividadeAprofundamento.objects.get(pk=request.GET.get('atividadeaprofundamento'))
        title = f'Editar Atividade de Aprofundamento - {instance.tipo.descricao}'
        atividade_aprofundamento = AtividadeAprofundamento.objects.filter(tipo__itemconfiguracaoatividadeaprofundamento=instance).exists()
    form = ItemConfiguracaoAtividadeAprofundamentoForm(request.POST or None, instance=instance, configuracao_pk=pk)
    if form.is_valid():
        form.instance.configuracao = ConfiguracaoAtividadeAprofundamento.objects.get(pk=pk)
        try:
            form.instance.save()
        except IntegrityError:
            return httprr('.', 'Não foi possível adicionar a atividade de aprofundamento pois ela já pertence a esta Configuração de ATPA', 'error')

        if instance:
            return httprr('..', 'Atividade de aprofundamento alterada com sucesso.')
        else:
            return httprr('..', 'Atividade de aprofundamento cadastrada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_configuracaocreditosespeciais')
def adicionar_item_configuracao_ce(request, pk, pk_atividade=None):
    title = 'Adicionar Atividade'
    configuracao = ConfiguracaoCreditosEspeciais.objects.get(pk=pk)
    instance = None
    if pk_atividade:
        instance = ItemConfiguracaoCreditosEspeciais.objects.get(pk=pk_atividade)
        title = f'Editar Atividade - {instance}'
    form = ItemConfiguracaoCreditosEspeciaisForm(request.POST or None, instance=instance)
    if form.is_valid():
        obj = form.save(False)
        obj.configuracao = configuracao
        obj.save()
        if instance:
            return httprr('..', 'Atividade alterada com sucesso.')
        else:
            return httprr('..', 'Atividade cadastrada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.add_configuracaoatividadecomplementar')
def replicar_configuracao_aacc(request, pk):
    configuracao = ConfiguracaoAtividadeComplementar.objects.get(pk=pk)
    title = f'Replicar - {configuracao.descricao}'
    form = ReplicarConfiguracaoAACCForm(request.POST or None)
    if request.POST and form.is_valid():
        resultado = form.processar(configuracao)
        return httprr(
            '..',
            mark_safe('Configuração de AACC replicada com sucesso para {}. Deseja <a href="/edu/configuracaoatividadecomplementar/{}/">Visualizá-la?</a>'.format(
                resultado.descricao, resultado.pk
            )),
        )
    return locals()


@rtr()
@permission_required('edu.add_configuracaoatividadeaprofundamento')
def replicar_configuracao_atpa(request, pk):
    configuracao = ConfiguracaoAtividadeAprofundamento.objects.get(pk=pk)
    title = f'Replicar - {configuracao.descricao}'
    form = ReplicarConfiguracaoATPAForm(request.POST or None)
    if request.POST and form.is_valid():
        resultado = form.processar(configuracao)
        return httprr(
            '..',
            mark_safe('Configuração de ATPA replicada com sucesso para {}. Deseja <a href="/edu/configuracaoatividadeaprofundamento/{}/">Visualizá-la?</a>'.format(
                resultado.descricao, resultado.pk
            )),
        )
    return locals()


@rtr()
def visualizar_requisitos_conclusao(request, pk, tipo_requisito, tipo_ch):
    if not request.user.is_authenticated and not 'matricula_aluno_como_resposavel' in request.session:
        raise PermissionDenied()
    obj = get_object_or_404(Aluno, pk=pk)
    cumpridos = nao_cumpridos = pendentes = None
    # Verificando o tipo do Requisito
    if tipo_requisito == 'disciplinas_regulares_obrigatorias':
        title = 'Disciplinas Obrigatórias'
        if tipo_ch == 'pendente':
            pendentes = obj.get_componentes_regulares_obrigatorios_pendentes()
        else:
            cumpridos = obj.get_componentes_regulares_obrigatorios_cumpridos()
    elif tipo_requisito == 'disciplinas_regulares_optativas':
        title = 'Disciplinas Optativas'
        if tipo_ch == 'pendente':
            nao_cumpridos = obj.get_componentes_regulares_optativos_nao_cumpridos()
        else:
            cumpridos = obj.get_componentes_regulares_optativos_cumpridos()
            credito_especial = CreditoEspecial.objects.filter(matricula_periodo__in=obj.matriculaperiodo_set.all())
    elif tipo_requisito == 'disciplinas_eletivas':
        title = 'Disciplina Eletivas'
        componentes = obj.get_componentes_eletivos_cumpridos()
    elif tipo_requisito == 'seminario':
        title = 'Disciplinas de Seminário'
        if tipo_ch == 'pendente':
            pendentes = obj.get_componentes_seminario_pendentes()
            nao_cumpridos = obj.get_componentes_seminario_nao_cumpridos().exclude(pk__in=pendentes.values_list('id', flat=True))
        else:
            cumpridos = obj.get_componentes_seminario_cumpridos()
    elif tipo_requisito == 'pratica_como_componente':
        title = 'Prática como Componente Curricular'
        if tipo_ch == 'pendente':
            pendentes = obj.get_componentes_pratica_como_componente_pendentes()
            nao_cumpridos = obj.get_componentes_pratica_como_componente_nao_cumpridos().exclude(pk__in=pendentes.values_list('id', flat=True))
        else:
            cumpridos = obj.get_componentes_pratica_como_componente_cumpridos()
    elif tipo_requisito == 'visita_tecnica':
        title = 'Visita Técnica / Aula de Campo'
        if tipo_ch == 'pendente':
            pendentes = obj.get_componentes_visita_tecnica_pendentes()
            nao_cumpridos = obj.get_componentes_visita_tecnica_nao_cumpridos().exclude(pk__in=pendentes.values_list('id', flat=True))
        else:
            cumpridos = obj.get_componentes_visita_tecnica_cumpridos()
    elif tipo_requisito == 'pratica':
        title = 'Prática Profissional'
        if tipo_ch == 'pendente':
            pendentes = obj.get_componentes_pratica_profissional_pendentes()
            nao_cumpridos = obj.get_componentes_pratica_profissional_nao_cumpridos().exclude(pk__in=pendentes.values_list('id', flat=True))
        else:
            cumpridos = obj.get_componentes_pratica_profissional_cumpridos()
    elif tipo_requisito == 'projeto_final':
        title = 'Disciplinas de TCC'
        if tipo_ch == 'pendente':
            pendentes = obj.get_componentes_tcc_pendentes()
            nao_cumpridos = obj.get_componentes_tcc_nao_cumpridos().exclude(pk__in=pendentes.values_list('id', flat=True))
        else:
            cumpridos = obj.get_componentes_tcc_cumpridos()
    elif tipo_requisito == 'atividades_extensao':
        title = 'Atividades Curriculares de Extensão'

    lista = []
    if cumpridos is not None:
        lista.append(dict(descricao='Componentes Cursados', componentes=cumpridos))
    if pendentes is not None:
        lista.append(dict(descricao='Componentes Não-Cursados (Obrigatórios)', componentes=pendentes))
    if nao_cumpridos is not None:
        lista.append(dict(descricao='Componentes Não-Cursados (Optativos)', componentes=nao_cumpridos))
    return locals()


@rtr()
@login_required()
def visualizar_atividades_complementares_cumpridas(request, pk):
    obj = get_object_or_404(Aluno, pk=pk)
    title = 'Atividades Complementares Cumpridas'
    atividades_complementares = obj.get_atividades_complementares(True)
    tipos = obj.get_ch_atividades_complementares_por_tipo()
    return locals()


@rtr()
@login_required()
def visualizar_atividades_aprofundamento_cumpridas(request, pk):
    obj = get_object_or_404(Aluno, pk=pk)
    title = 'Atividades de Aprofudamento'
    atividades_aprofundamento = obj.atividadeaprofundamento_set.filter(deferida=True)
    return locals()


@rtr()
@login_required()
def visualizar_atividades_complementares_pendentes(request, pk):
    obj = get_object_or_404(Aluno, pk=pk)
    title = 'Atividades Complementares Pendentes'
    requer_atividade_obrigatoria = False
    tipos = obj.get_ch_atividades_complementares_por_tipo(apenas_obrigatorias=True)
    for tipo in tipos:
        if tipo.ch_considerada < tipo.ch_min_curso:
            requer_atividade_obrigatoria = True
            break
    return locals()


@rtr()
@login_required()
def visualizar_estrutura_curso(request, estrutura_curso_pk):
    title = 'Estrutura de Curso'
    obj = get_object_or_404(EstruturaCurso, pk=estrutura_curso_pk)
    if 'replicar' in request.GET:
        obj.pk = None
        obj.descricao = f'{obj.descricao} [REPLICADA]'
        obj.save()
        return httprr(f'/admin/edu/estruturacurso/{obj.pk}/', 'Estrutura replicada com sucesso. Edite a descrição e os demais dados necessários.')
    matrizes_ativas = obj.get_matrizes_ativas()
    matrizes_inativas = obj.get_matrizes_inativas()

    return locals()


@permission_required('edu.change_turma')
@rtr()
def adicionar_alunos_diario(request, diario_pk):
    diario = get_object_or_404(Diario.locals, pk=diario_pk)
    title = 'Matricular Alunos da Turma no Diário'
    qs_matriculas_periodo_turma = diario.turma.get_matriculas_aptas_adicao_turma(diario)
    form = AdicionarAlunosDiarioForm(qs_matriculas_periodo_turma, request.POST or None)
    if form.is_valid():
        count = form.processar(diario)
        if count:
            return httprr('..', f'{count} aluno(s) matriculado(s) no diário com sucesso.')
        else:
            return httprr('..', 'Nenhum aluno foi matriculado no diário.')
    return locals()


@rtr()
@login_required()
def pedido_matricula_seriado(request, aluno_pk):
    aluno = get_object_or_404(Aluno.locals, pk=aluno_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos and not aluno.is_user(request):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not aluno.pode_matricula_online() or aluno.is_credito():
        return httprr('/', 'Não existe um período de renovação de matrícula ativa para o seu curso.', 'error')

    configuracao_pedido_matricula_ativa = aluno.get_configuracao_pedido_matricula_ativa()
    if aluno.is_user(request) and configuracao_pedido_matricula_ativa.requer_atualizacao_dados and not 'dados_atualizados' in request.session:
        return httprr(f'/edu/atualizar_meus_dados_pessoais/{aluno.matricula}/1/')

    if aluno.is_user(request) and configuracao_pedido_matricula_ativa.requer_atualizacao_caracterizacao and not 'caracterizacao_atualizada' in request.session:
        return httprr(f'/ae/caracterizacao/{aluno.pk}/1/')

    ultima_matricula_periodo = aluno.get_ultima_matricula_periodo()
    segunda_chamada = ultima_matricula_periodo.situacao.pk in [SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL, SituacaoMatriculaPeriodo.MATRICULADO]
    title = 'Matrícula Online ({})'.format(segunda_chamada and '2ª Chamada' or '1ª Chamada')

    # obtendo as turmas com seus diários disponíveis para o aluno
    turmas = aluno.get_turmas_matricula_online()
    # obtendo os diários das disciplinas em dependência do aluno
    diarios_dependencia = aluno.get_diarios_pendentes_matricula_online(
        apenas_obrigatorias=True, ignorar_pendencia_horario=aluno.curso_campus.modalidade.pk in [Modalidade.INTEGRADO, Modalidade.SUBSEQUENTE]
    )

    # Verificando se existe algum diário disponível nas turmas disponíveis
    diarios_disponiveis_turma = False
    for turma in turmas:
        if turma.diarios:
            diarios_disponiveis_turma = True

    # Obtendo o pedido de matrícula salvo
    erros = ''
    pedido_matricula = None
    id_diarios_salvos = []
    id_diarios_persistidos = []
    id_turma_persistida = None
    diarios_optativos_selecionados = []
    diarios_optativos_persistidos = []
    qs_pedido_matricula = ultima_matricula_periodo.pedidomatricula_set.filter(configuracao_pedido_matricula=configuracao_pedido_matricula_ativa)
    if qs_pedido_matricula:
        pedido_matricula = qs_pedido_matricula[0]
        id_turma_persistida = pedido_matricula.turma and pedido_matricula.turma.pk or None

        for item in pedido_matricula.pedidomatriculadiario_set.all().values_list('diario__id', flat=True):
            id_diarios_salvos.append(item)
            id_diarios_persistidos.append(item)
        for item in pedido_matricula.pedidomatriculadiario_set.filter(diario__componente_curricular__optativo=True).values_list('diario__id', flat=True):
            diarios_optativos_persistidos.append(item)

        # Exibição dos horários já salvos
        dias_semana = HorarioAulaDiario.DIA_SEMANA_CHOICES
        turnos = pedido_matricula.get_turnos_horarios()
        pedidos_diario_turma = pedido_matricula.pedidomatriculadiario_set.filter(diario__turma=pedido_matricula.turma)
        pedidos_diario_dependencias = pedido_matricula.pedidomatriculadiario_set.exclude(diario__turma=pedido_matricula.turma)

    if request.POST:
        for x in request.POST.getlist('diario'):
            diarios_optativos_selecionados.append(int(x))
        continuar = True

        # Validando se foi selecionada alguma turma caso seja a primeira chamada
        id_turma_selecionada = None
        if diarios_disponiveis_turma:
            if not 'turma' in request.POST:  # and not segunda_chamada:
                continuar = False
                erros += 'Você deve selecionar uma turma.'
            else:
                id_turma_selecionada = int(request.POST['turma'])

        if continuar:

            # Verificando se foi selecionado algum diário de cada disciplina em dependência
            if diarios_dependencia:
                componentes_id = diarios_dependencia.values_list('componente_curricular__componente__id', flat=True).distinct()
                for componente_id in componentes_id:
                    chave = f'diarios_{componente_id}'
                    if not chave in request.POST:
                        continuar = False
                        componente = Componente.objects.get(pk=componente_id)
                        erros += f'Escolha uma turma para a disciplina em dependência {componente.descricao_historico}.'
                    else:
                        id_diarios_salvos.append(int(request.POST[chave]))
                        #             else:
                        #                 if segunda_chamada and not id_turma_selecionada:
                        #                     continuar = False
                        #                     erros += u'Escolha ao menos uma turma ou uma disciplina em dependência para salvar o pedido.'

            # Selecionando a turma selecionada pelo aluno entre as turmas disponíveis para ele
            turma = None
            if diarios_disponiveis_turma:
                for turma_tmp in turmas:
                    if turma_tmp.pk == id_turma_selecionada:
                        turma = turma_tmp
                        break

            # validando choque de horário
            ids_validar_choque = []
            for id_tmp in ultima_matricula_periodo.matriculadiario_set.values_list('diario__id', flat=True):
                ids_validar_choque.append(id_tmp)
            if turma:
                for diario in turma.diarios:
                    if not diario.componente_curricular.optativo or (diario.componente_curricular.optativo and diario.pk in diarios_optativos_selecionados):
                        ids_validar_choque.append(diario.pk)

            # plano de retomada de aulas em virtude da pandemia (COVID19)
            if Diario.objects.filter(id__in=ids_validar_choque, turma__pertence_ao_plano_retomada=True).exists():
                diarios_com_choque = []
            else:
                diarios_com_choque = Diario.get_diarios_choque_horario(ids_validar_choque)
            if diarios_com_choque:
                continuar = False
                erros += 'Seu pedido não pôde ser salvo, pois há conflitos de horários entre as seguintes disciplinas:'

                for diario in diarios_com_choque:
                    erros += f'<br> - {diario.componente_curricular.componente} Horário: {diario.get_horario_aulas()}'

            # caso exista algum erro e já exista um pedido de matrícula salvo, será exibido os pedidos salvos
            if pedido_matricula and not continuar:
                id_diarios_salvos = id_diarios_persistidos
                id_turma_selecionada = id_turma_persistida

            if continuar:
                # salvando o pedido de mnatricula
                if pedido_matricula:
                    pedido_matricula.pedidomatriculadiario_set.all().delete()
                else:
                    pedido_matricula = PedidoMatricula()
                pedido_matricula.matricula_periodo = ultima_matricula_periodo
                pedido_matricula.configuracao_pedido_matricula = configuracao_pedido_matricula_ativa
                if diarios_disponiveis_turma:
                    pedido_matricula.turma = turma
                pedido_matricula.save()

                # salvando os pedidos de matrícula nos diários disponíveis para aluno da turma selecionada por ele
                if turma:
                    for diario in turma.diarios:
                        if not diario.componente_curricular.optativo or diario.pk in diarios_optativos_selecionados:
                            pedido_matricula_diario = PedidoMatriculaDiario()
                            pedido_matricula_diario.diario = diario
                            pedido_matricula_diario.pedido_matricula = pedido_matricula
                            pedido_matricula_diario.save()

                # salvando os pedidos de matrícula nos diários das disciplinas pendentes
                if diarios_dependencia:
                    for componente_id in componentes_id:
                        diario = Diario.objects.get(pk=request.POST.get(f'diarios_{componente_id}'))
                        pedido_matricula_diario = PedidoMatriculaDiario()
                        pedido_matricula_diario.diario = diario
                        pedido_matricula_diario.pedido_matricula = pedido_matricula
                        pedido_matricula_diario.save()

                if diarios_dependencia or diarios_disponiveis_turma:
                    return httprr('.', 'Pedido de matrícula salvo com sucesso.')
                else:
                    return httprr('.', 'Pedido de manutenção do vínculo com a instituição salvo com sucesso.')

    return locals()


@login_required()
@group_required('Agendador de Aula de Campo EDU,Administrador Acadêmico,Secretário Acadêmico,Diretor Acadêmico')
@rtr()
def configuracaoseguro(request, pk):
    obj = get_object_or_404(ConfiguracaoSeguro, pk=pk)
    aulas_campo = AulaCampo.locals.filter(configuracao_seguro=obj).order_by('data_partida')
    title = 'Configuração de Seguro'

    usuario_is_administrador = in_group(request.user, 'Administrador Acadêmico')
    eh_secretario = in_group(request.user, 'Secretário Acadêmico')

    return locals()


@permission_required('edu.add_aulacampo')
@login_required()
@rtr()
def aulacampo(request, pk):
    obj = get_object_or_404(AulaCampo.locals, pk=pk)
    title = 'Visualização de Aula de Campo'
    usuario_is_administrador = in_group(request.user, 'Administrador Acadêmico')

    if 'cancelar' in request.GET:
        obj.situacao = AulaCampo.SITUACAO_CANCELADA
        obj.save()
        return httprr('.', 'Aula de Campo cancelada com sucesso.')

    if 'realizada' in request.GET:
        obj.situacao = AulaCampo.SITUACAO_REALIZADA
        obj.save()
        return httprr('.', 'Aula de Campo atualizada com sucesso.')

    if 'alunos_selecionados' in request.POST:
        alunos_aulas = AlunoAulaCampo.objects.filter(aula_campo=obj, aluno__id__in=request.POST.getlist('alunos_selecionados'))

        for aluno_aluno in alunos_aulas:
            aluno_aluno.delete()

        return httprr(f'/edu/aulacampo/{obj.pk:d}/', 'Aluno(s) removido(s) com sucesso.')
    return locals()


@permission_required('edu.add_aulacampo')
@login_required()
@rtr()
def adicionar_alunos_aula_campo(request, pk):
    obj = get_object_or_404(AulaCampo.locals, pk=pk)
    title = 'Adicionar Alunos à Aula de Campo'
    usuario_is_administrador = in_group(request.user, 'Administrador Acadêmico')
    if not obj.situacao == obj.SITUACAO_AGENDADA and not usuario_is_administrador:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    form = PesquisarAlunosForm(request.GET or None)

    if request.method == 'GET':
        if form.is_valid():
            alunos = form.processar()
            alunos = alunos.exclude(aulacampo=obj)

    if 'alunos_selecionados' in request.POST:
        alunos_selecionados = Aluno.objects.filter(id__in=request.POST.getlist('alunos_selecionados'))

        qtd_alunos_selecionados = alunos_selecionados.count()
        data_partida = obj.data_partida
        data_chegada = obj.data_chegada
        qtd_dias = (data_chegada - data_partida).days + 1
        gasto_previsto_aula = qtd_alunos_selecionados * qtd_dias * obj.configuracao_seguro.valor_repasse_pessoa

        # Verificando conflitos de datas para os alunos
        qs = obj.configuracao_seguro.aulacampo_set.filter(situacao=AulaCampo.SITUACAO_AGENDADA)
        qs = qs.exclude(data_chegada__lt=data_partida)
        qs = qs.exclude(data_partida__gt=data_chegada)

        if obj:
            qs = qs.exclude(pk=obj.pk)

        for aluno in alunos_selecionados:
            qs = qs.filter(alunos__matricula=aluno.matricula)

            if qs.exists():
                aulas_conflitos = qs.values_list('pk', flat=True).distinct()
                return httprr(
                    request.META.get('HTTP_REFERER', '.'),
                    f'Existe conflito de datas para o(a) aluno(a) {aluno} nas aulas de campo {aulas_conflitos}.',
                    'error',
                )

        if not obj.configuracao_seguro.possui_saldo_suficiente(gasto_previsto_aula):
            num_participantes_disponivel = obj.configuracao_seguro.get_participantes_disponiveis(qtd_dias)

            return httprr(
                request.META.get('HTTP_REFERER', '.'),
                f'Não existe saldo disponível para a quantidade de alunos selecionados. Você pode incluir até {num_participantes_disponivel:d} alunos.',
                'error',
            )
        else:
            for aluno in alunos_selecionados:
                aluno_aula = AlunoAulaCampo()
                aluno_aula.aluno = aluno
                aluno_aula.aula_campo = obj
                aluno_aula.save()

            return httprr(f'/edu/aulacampo/{obj.pk:d}/', 'Aluno(s) adicionado(s) com sucesso.')

    return locals()


@rtr()
@login_required()
def pedido_matricula_credito(request, aluno_pk):
    aluno = get_object_or_404(Aluno.locals, pk=aluno_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos and not aluno.is_user(request):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not aluno.pode_matricula_online() or aluno.is_seriado() or aluno.is_modular():
        return httprr('/', 'Não existe um período de renovação de matrícula ativa para o seu curso.', 'error')

    configuracao_pedido_matricula_ativa = aluno.get_configuracao_pedido_matricula_ativa()
    if aluno.is_user(request) and configuracao_pedido_matricula_ativa.requer_atualizacao_dados and not 'dados_atualizados' in request.session:
        return httprr(f'/edu/atualizar_meus_dados_pessoais/{aluno.matricula}/1/')

    if aluno.is_user(request) and configuracao_pedido_matricula_ativa.requer_atualizacao_caracterizacao and not 'caracterizacao_atualizada' in request.session:
        return httprr(f'/ae/caracterizacao/{aluno.pk}/1/')

    ultima_matricula_periodo = aluno.get_ultima_matricula_periodo()
    segunda_chamada = ultima_matricula_periodo.situacao.pk in [SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL, SituacaoMatriculaPeriodo.MATRICULADO]
    title = 'Matrícula Online ({})'.format(segunda_chamada and '2ª Chamada' or '1ª Chamada')

    # Recuperando diários das disciplinas obrigatórias disponíveis
    diarios_obrigatorias = aluno.get_diarios_pendentes_matricula_online(apenas_obrigatorias=True)
    ids_componentes_diarios_obrigatorias = diarios_obrigatorias.values_list('componente_curricular__componente__id', flat=True).distinct()

    # Recuperando diários das disciplinas optativas disponíveis
    diarios_optativas = aluno.get_diarios_pendentes_matricula_online(apenas_optativas=True, ids_componentes_diarios_obrigatorias=ids_componentes_diarios_obrigatorias)

    # Recuperando diários das disciplinas eletivas disponíveis
    if aluno.matriz.ch_componentes_eletivos > 0:
        diarios_eletivas = aluno.get_diarios_eletivas_matricula_online()

    # Recuperando diários que o aluno já se matrículou neste período
    ids_diarios_matriculados = ultima_matricula_periodo.get_matriculas_diario().exclude(situacao=MatriculaDiario.SITUACAO_CANCELADO).values_list('diario__id', flat=True)

    # Recuperando pedido de matrícula já salvo no atual período de pedido de matrícula
    pedido_matricula = None
    erros = ''

    id_diarios_salvos = []
    id_diarios_persistidos = []
    id_diarios_cancelados = []
    qs_pedido_matricula = ultima_matricula_periodo.pedidomatricula_set.filter(configuracao_pedido_matricula=configuracao_pedido_matricula_ativa)
    if qs_pedido_matricula:
        pedido_matricula = qs_pedido_matricula[0]
        for item in pedido_matricula.pedidomatriculadiario_set.all().values_list('diario__id', flat=True):
            id_diarios_salvos.append(item)
            id_diarios_persistidos.append(item)

        # Variáveis para exibição do quadro de horários
        dias_semana = HorarioAulaDiario.get_dias_semana_seg_a_sex()
        turnos = pedido_matricula.get_turnos_horarios()
        pedidos_diario_dependencias = pedido_matricula.pedidomatriculadiario_set.all()
        id_diarios_cancelados = pedido_matricula.matriculas_diario_canceladas.values_list('id', flat=True)

    # quantitativos para validação
    estrutura = aluno.matriz.estrutura
    ids_disciplinas_obrigatorias = diarios_obrigatorias.values_list('componente_curricular__componente_id', flat=True).order_by().distinct()
    ids_disciplinas_optativas = diarios_optativas.values_list('componente_curricular__componente_id', flat=True).order_by().distinct()
    qtd_disciplinas_obrigatorias = ids_disciplinas_obrigatorias.count()
    qtd_disciplinas_optativas = ids_disciplinas_optativas.count()
    qtd_disciplinas_matriculadas = ids_diarios_matriculados.count()
    qtd_disciplinas_matriz_disponiveis = qtd_disciplinas_obrigatorias + qtd_disciplinas_optativas + qtd_disciplinas_matriculadas
    qtd_componentes_obrigatorios_matriz_periodo_atual = len(aluno.matriz.get_ids_componentes(periodos=aluno.periodo_atual, apenas_obrigatorio=True))
    qtd_disciplinas_pendentes = diarios_obrigatorias.count()

    if estrutura.numero_disciplinas_superior_periodo:
        qtd_maxima_disciplinas = qtd_componentes_obrigatorios_matriz_periodo_atual + estrutura.numero_disciplinas_superior_periodo

    qtd_minima_disciplinas = estrutura.qtd_minima_disciplinas or 0
    if qtd_minima_disciplinas:
        diarios_abaixo_qtd_minima = 0 < qtd_disciplinas_matriz_disponiveis <= qtd_minima_disciplinas
        diarios_acima_qtd_minima = qtd_disciplinas_matriz_disponiveis > qtd_minima_disciplinas

    if request.POST:
        continuar = True
        diarios_solicitados = []
        ids_disciplinas_solicitadas = []
        componente_diario = {}
        for chave in list(request.POST.keys()):
            if 'diario' in chave:
                diario = Diario.objects.get(pk=request.POST.get(chave))
                diarios_solicitados.append(diario)
                id_diarios_salvos.append(int(request.POST[chave]))
                ids_disciplinas_solicitadas.append(diario.componente_curricular.componente.id)
                componente_diario[diario.componente_curricular.componente.id] = diario

        if ids_disciplinas_solicitadas:
            ids_cursando = aluno.get_ids_componentes_cursando()
            ids_cumprido = aluno.get_ids_componentes_cumpridos()
            for componente in ids_disciplinas_solicitadas:
                ids_correquisitos = componente_diario[componente].componente_curricular.get_corequisitos()
                for correquisito in ids_correquisitos:
                    if correquisito not in ids_cursando and correquisito not in ids_cumprido and correquisito not in ids_disciplinas_solicitadas:
                        continuar = False
                        componente_correquisito = Componente.objects.get(id=correquisito)
                        componente_pendente = Componente.objects.get(id=componente)
                        erros += f'A disciplina {componente_pendente} possui co requisito pendente ({componente_correquisito}).'

        qtd_disciplinas_solicitadas = len(ids_disciplinas_solicitadas)

        # se ele já realizou um pedido e foi deferido, ele deve escolher ao menos um diário na segunda chamada se tiver menos disciplinas que o exigido na estrutura
        if (
            segunda_chamada
            and (qtd_disciplinas_obrigatorias + qtd_disciplinas_optativas) > 0
            and not ids_disciplinas_solicitadas
            and qtd_disciplinas_matriculadas < qtd_minima_disciplinas
        ):
            continuar = False
            erros += 'É necessário escolher, ao menos, uma disciplina na segunda chamada.'

        # validando se a quantidade de diários disponíveis está abaixo da qtd mínima de disciplinas da estrutura do curso
        # ou seja, será necessário escolher todas as disciplinas obrigatórias e optativas disponíveis
        if qtd_disciplinas_pendentes > qtd_minima_disciplinas and qtd_minima_disciplinas and diarios_abaixo_qtd_minima:
            if not request.user.has_perm('edu.pode_quebrar_quantidade_minima'):
                for componente_oo in ids_disciplinas_obrigatorias:
                    if componente_oo not in ids_disciplinas_solicitadas:
                        continuar = False

                if not continuar:
                    erros += 'Você deve selecionar todas as disciplinas obrigatórias.'

        # validando a quantidade mínima de disciplinas
        elif qtd_minima_disciplinas and diarios_acima_qtd_minima and (qtd_disciplinas_solicitadas + qtd_disciplinas_matriculadas < qtd_minima_disciplinas):
            if not request.user.has_perm('edu.pode_quebrar_quantidade_minima'):
                # se o aluno necessita pagar mais do que a quantidade mínima de disciplina informada na estrutura do curso
                if qtd_disciplinas_pendentes > qtd_minima_disciplinas:
                    continuar = False
                    if qtd_disciplinas_matriculadas > 0:
                        erros += f'Escolha, no mínimo, {qtd_minima_disciplinas - qtd_disciplinas_matriculadas} disciplina(s) obrigatória(s) e/ou optativa(s).'
                    else:
                        erros += f'Escolha, no mínimo, {qtd_minima_disciplinas} disciplina(s) obrigatória(s) e/ou optativa(s) para cursar no próximo período letivo.'
                # o aluno está precisando cursar menos disciplinas do que a quantidade mínima de disciplina informada na estrutura do curso, logo ele deve escolher todas as disciplinas obrigatórias
                else:
                    for componente_oo in ids_disciplinas_obrigatorias:
                        if componente_oo not in ids_disciplinas_solicitadas:
                            continuar = False
                    if not continuar:
                        erros += 'Você deve selecionar todas as disciplinas obrigatórias.'

        # validando a quantidade de disciplinas que podem ser cursadas a mais da quantidade de disciplinas do seu período atual
        elif estrutura.numero_disciplinas_superior_periodo and qtd_disciplinas_solicitadas + qtd_disciplinas_matriculadas > qtd_maxima_disciplinas:
            continuar = False

            if qtd_disciplinas_matriculadas > 0:
                erros += 'Não é permitido se matricular em mais de {} disciplinas por período. Ainda é possível se matricular em {} disciplinas.'.format(
                    qtd_maxima_disciplinas, qtd_maxima_disciplinas - qtd_disciplinas_matriculadas
                )
            else:
                erros += f'Não é permitido se matricular em mais de {qtd_maxima_disciplinas} disciplinas por período.'
        else:
            # validando choque de horário
            ids_diarios_validar_choque = []
            # inserindo os diarios já matriculados
            ids_diarios_cancelar = MatriculaDiario.objects.filter(
                id__in=request.POST.getlist('cancelar_md')
            ).values_list('diario', flat=True) if request.POST and 'cancelar_md' in request.POST else []
            for id_diarios_matriculados in ids_diarios_matriculados:
                if id_diarios_matriculados not in ids_diarios_cancelar:
                    ids_diarios_validar_choque.append(id_diarios_matriculados)
            # inserindo os diarios solicitados
            for diario_solicitado in diarios_solicitados:
                ids_diarios_validar_choque.append(diario_solicitado.id)
            if Diario.objects.filter(id__in=ids_diarios_validar_choque, turma__pertence_ao_plano_retomada=True).exists():
                diarios_com_choque = []
            else:
                diarios_com_choque = Diario.get_diarios_choque_horario(ids_diarios_validar_choque)
            if diarios_com_choque:
                continuar = False
                erros += 'Seu pedido não pôde ser salvo, pois há conflitos de horários entre as seguintes disciplinas:'

                for diario in diarios_com_choque:
                    erros += f'<br> - {diario.componente_curricular.componente} Horário: {diario.get_horario_aulas()}'

        # caso exista algum erro e já exista um pedido de matrícula salvo, será exibido os pedidos salvos
        if pedido_matricula and not continuar:
            id_diarios_salvos = id_diarios_persistidos

        if pedido_matricula and continuar:
            if configuracao_pedido_matricula_ativa.permite_cancelamento_matricula_diario:
                pedido_matricula.matriculas_diario_canceladas.clear()
                ids_cancelar_md = request.POST.getlist('cancelar_md')
                for md in MatriculaDiario.objects.filter(id__in=ids_cancelar_md):
                    try:
                        md.cancelar(False)
                        pedido_matricula.matriculas_diario_canceladas.add(md)
                    except ValidationError as e:
                        continuar = False
                        erros += 'Seu pedido não pôde ser salvo, pois não é possível cancelar a matrícula no diário {}. Motivo: {}'.format(md.diario, e.message)

        if continuar:
            # salvando o pedido de matrícula
            if pedido_matricula:
                pedido_matricula.pedidomatriculadiario_set.all().delete()
            else:
                pedido_matricula = PedidoMatricula()
            pedido_matricula.matricula_periodo = ultima_matricula_periodo
            pedido_matricula.configuracao_pedido_matricula = configuracao_pedido_matricula_ativa
            pedido_matricula.save()

            # salvando os pedidos de matrícula em diário
            for diario in diarios_solicitados:
                pedido_matricula_diario = PedidoMatriculaDiario()
                pedido_matricula_diario.diario = diario
                pedido_matricula_diario.pedido_matricula = pedido_matricula
                pedido_matricula_diario.save()

            if qtd_disciplinas_solicitadas:
                return httprr('.', 'Pedidos de matrícula salvos com sucesso.')
            else:
                return httprr('.', 'Pedido de manutenção do vínculo com a instituição salvo com sucesso.')

    # caso o usuário seja o próprio aluno, sua estrutura possibilizar plano de estudo e ele já tenha atingido
    # o tempo mínimo para conclusão do curso, ele poderá informar se deseja a criação de um plano de estudo
    pode_solicitar_plano_estudo = aluno.is_user(request) and estrutura.plano_estudo and aluno.matriculaperiodo_set.count() > aluno.matriz.qtd_periodos_letivos
    if 'plano_estudo' in request.GET:
        pedido_matricula = PedidoMatricula()
        pedido_matricula.matricula_periodo = ultima_matricula_periodo
        pedido_matricula.configuracao_pedido_matricula = configuracao_pedido_matricula_ativa
        pedido_matricula.save()
        plano_estudo = PlanoEstudo()
        plano_estudo.tipo = 'Planejamento'
        plano_estudo.pedido_matricula = pedido_matricula
        plano_estudo.save()
        return httprr(f'/edu/pedido_matricula_credito/{aluno.pk}/', 'Solicitação de plano de estudo realizada com sucesso.')
    solicitou_dispensa_plano_estudo = False
    solicitou_criacao_plano_estudo = False
    if pode_solicitar_plano_estudo and pedido_matricula:
        solicitou_criacao_plano_estudo = pedido_matricula.planoestudo_set.filter(tipo='Planejamento').exists()
        solicitou_dispensa_plano_estudo = pedido_matricula.planoestudo_set.filter(tipo='Dispensa').exists()
        if not solicitou_criacao_plano_estudo and not solicitou_dispensa_plano_estudo:
            plano_estudo = PlanoEstudo()
            plano_estudo.tipo = 'Dispensa'
            plano_estudo.pedido_matricula = pedido_matricula
            plano_estudo.save()
            solicitou_dispensa_plano_estudo = True
    return locals()


@permission_required('edu.add_configuracaopedidomatricula')
@rtr()
def add_curso_configuracao_pedido_matricula(request, pk):
    title = 'Configuração de Renovação de Matrícula'
    obj = get_object_or_404(ConfiguracaoPedidoMatricula, pk=pk)
    if not obj.pode_ser_alterado():
        return httprr('..', 'O pedido não pode ser alterado.', 'error')
    form = AddCursoConfiguracaoPedidoMatriculaForm(request=request, data=request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Curso(s) adicionado(s) com sucesso.')
    return locals()


@permission_required('edu.view_configuracaopedidomatricula')
@rtr()
def configuracao_pedido_matricula(request, pk):
    title = 'Renovação de Matrícula'
    obj = get_object_or_404(ConfiguracaoPedidoMatricula, pk=pk)

    del_curso_id = request.GET.get('del_curso_id')
    cancelar = request.GET.get('cancelar')
    if cancelar and request.user.has_perm('edu.change_configuracaopedidomatricula'):
        if int(cancelar):
            if not obj.is_processado():
                try:
                    obj.cancelar()
                    return httprr('.', 'Cancelamento realizado com sucesso.')
                except ValidationError as e:
                    return httprr('.', f'Não foi possível cancelar a renovação de matrícula: {e.messages[0]}', 'error')
        else:
            if obj.is_cancelado():
                obj.desfazer_cancelamento()
                return httprr('.', 'Cancelamento desfeito com sucesso.')

    if del_curso_id and request.user.has_perm('edu.change_configuracaopedidomatricula'):
        curso_campus = get_object_or_404(CursoCampus, pk=del_curso_id)
        if obj.pode_ter_curso_removido(curso_campus) and obj.pode_ser_alterado():
            obj.cursos.remove(curso_campus)
            obj.save()
            return httprr('.', f'Curso {curso_campus} removido com sucesso.')
        else:
            return httprr('.', f'Curso {curso_campus} não pode ser removido.', 'error')

    turmas = None
    curso_escolhido = None
    turma_escolhida = None
    tab = request.GET.get('tab')
    if tab == 'monitoramento' or tab == 'pendencias':
        if request.GET.get('curso'):
            curso_escolhido = get_object_or_404(CursoCampus, pk=request.GET.get('curso'))
            qs_diarios = Diario.objects.filter(turma__ano_letivo=obj.ano_letivo, turma__periodo_letivo=obj.periodo_letivo, turma__curso_campus__in=obj.cursos.all())
            qs_diarios_com_pratica_profissional = qs_diarios.filter(
                componente_curricular__tipo__in=[
                    ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL,
                    ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
                    ComponenteCurricular.TIPO_SEMINARIO,
                ]
            )
            qs_diarios = qs_diarios.filter(horarioauladiario__isnull=False) | qs_diarios.filter(turno__descricao='EAD') | qs_diarios_com_pratica_profissional
            qs_diarios = qs_diarios.distinct().order_by('turma__curso_campus')
            qs_diarios = qs_diarios.filter(turma__curso_campus=curso_escolhido)
            turmas = Turma.objects.filter(diario__in=qs_diarios).distinct()
        else:
            turmas = None
            curso_escolhido = None
        if request.GET.get('turma'):
            turma_escolhida = get_object_or_404(Turma, pk=request.GET.get('turma'))
        else:
            turma_escolhida = None

    if tab == 'monitoramento':
        diarios_quantitativos = obj.get_diarios_quantitativos(curso=curso_escolhido, turma=turma_escolhida)
        qtd_diarios_quantitativos = len(diarios_quantitativos)

    diarios_sem_horarios = obj.get_diarios_sem_horarios(curso=curso_escolhido, turma=turma_escolhida).select_related(
        'componente_curricular', 'componente_curricular__componente', 'turma__curso_campus'
    )
    return locals()


@documento()
@login_required()
@rtr('comprovante_pedido_matricula_pdf.html')
def comprovante_pedido_matricula_pdf(request, pk):
    hoje = datetime.datetime.now()
    obj = get_object_or_404(PedidoMatricula, pk=pk)
    aluno = obj.matricula_periodo.aluno
    uo = aluno.curso_campus.diretoria.setor.uo

    # horarios
    dias_semana = HorarioAulaDiario.get_dias_semana_seg_a_sex()
    turnos = obj.get_turnos_horarios()

    pedidos_diario_turma = obj.pedidomatriculadiario_set.filter(diario__turma=obj.turma)
    pedidos_diario_dependencias = obj.pedidomatriculadiario_set.exclude(diario__turma=obj.turma)
    return locals()


@permission_required('edu.efetuar_matricula')
@login_required()
@rtr()
def processar_pedidos_matricula(request, pk):
    obj = get_object_or_404(ConfiguracaoPedidoMatricula, pk=pk)
    if not request.user.is_superuser and not obj.pode_processar():
        return httprr('..', 'O pedido não pode ser processado.', 'error')
    return tasks.processar_pedidos_matricula(obj)


@rtr()
def meu_pedido_matricula(request, pk):
    obj = get_object_or_404(PedidoMatricula, pk=pk)

    if not request.user.is_authenticated and not 'matricula_aluno_como_resposavel' in request.session:
        raise PermissionDenied()

    if not (
        obj.matricula_periodo.aluno.pessoa_fisica.user.username == request.session.get('matricula_aluno_como_resposavel')
        or obj.matricula_periodo.aluno.pessoa_fisica.user == request.user
        or request.user.has_perm('edu.efetuar_matricula')
        or in_group(request.user, 'Visualizador de Informações Acadêmicas, Auditor,Estagiário Acadêmico Sistêmico')
    ):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    pedidos_matricula_diario = obj.pedidomatriculadiario_set.all()
    diarios_removidos = []
    for pedido_matricula_diario in pedidos_matricula_diario.filter(deferido=True):
        if not MatriculaDiario.objects.filter(diario=pedido_matricula_diario.diario, matricula_periodo=obj.matricula_periodo).exists():
            diarios_removidos.append(pedido_matricula_diario.diario)
    turnos = obj.get_horarios()
    return locals()


@permission_required('edu.add_mensagem')
@rtr()
def enviar_mensagem_complementar(request, pk):
    title = 'Enviar Mensagem Complementar'
    obj = get_object_or_404(Mensagem, pk=pk)
    if obj.remetente.pk != request.user.pk:
        return HttpResponseForbidden()
    form = MensagemComplementarForm(obj, data=request.POST or None, request=request, files=request.FILES or None)
    if form.is_valid():
        nova_mensagem = form.processar()
        link = f'<a href="/edu/mensagem/{nova_mensagem.pk}/">CLIQUE AQUI</a>'
        return httprr('..', mark_safe(f'Mensagens ({nova_mensagem.destinatarios.count()}) enviadas com sucesso. Para visualizá-la, {link}.'))
    return locals()


@permission_required('edu.add_mensagem')
@rtr()
def enviar_mensagem(request):
    title = 'Nova Mensagem'
    initial = dict()
    post = request.POST.copy()

    if 'diario' in request.GET:
        diario = {'diario': request.GET.get('diario')}
        post.update(diario)

    if 'aluno' in request.GET:
        aluno = {'aluno': request.GET.get('aluno')}
        post.update(aluno)

    form = MensagemForm(post or None, request.FILES or None, request=request)

    if form.is_valid():
        return form.processar(request)
    return locals()


@login_required()
@rtr()
def mensagem(request, pk):
    obj = get_object_or_404(Mensagem, pk=pk)
    title = obj.assunto
    if not obj.remetente.pk == request.user.pk and not obj.destinatarios.filter(id=request.user.pk).exists() and not in_group(request.user, 'Administrador Acadêmico'):
        return httprr('/', 'Apenas o remetente e os destinatários podem visualizar a mensagem.', 'error')
    if not obj.existe_registro_leitura(request.user) and obj.destinatarios.filter(id=request.user.pk).exists():
        RegistroLeitura.objects.create(mensagem=obj, destinatario=request.user, data_leitura=datetime.datetime.today())
    if obj.remetente.pk == request.user.pk:
        registros_leitura = RegistroLeitura.objects.filter(mensagem=obj)
        outros_destinatarios = obj.destinatarios.exclude(pk__in=registros_leitura.values_list('destinatario', flat=True))
    else:
        registros_leitura = RegistroLeitura.objects.none()
        outros_destinatarios = obj.destinatarios.all()
    return locals()


@login_required()
@rtr()
def meu_polo(request):
    aluno = get_object_or_404(Aluno, matricula=request.user.username)
    if aluno.polo:
        definiu_horario = aluno.polo.definiu_horario()
        atividades = aluno.polo.get_proximas_atividades().filter(confirmada=True)
        turnos = aluno.polo.get_horarios_por_turno()
        meus_tutores = aluno.polo.get_tutores(aluno.curso_campus)
        coordenador_titular = aluno.polo.get_coordenador_titular()
        return locals()
    else:
        raise PermissionDenied


@permission_required('edu.view_polo')
@rtr()
def polo(request, pk):
    obj = get_object_or_404(Polo.locals, pk=pk)
    atividades = obj.get_proximas_atividades()
    periodo_letivo_atual = PeriodoLetivoAtualPolo.get_instance(request, obj)
    ano_letivo = Ano.objects.get(ano=periodo_letivo_atual.ano)
    periodo_letivo = periodo_letivo_atual.periodo
    turmas = obj.turma_set.filter(ano_letivo=ano_letivo, periodo_letivo=periodo_letivo)
    title = f'{obj}'
    cursos = obj.get_cursos_ofertados()
    usuario_coordenador = obj.coordenadorpolo_set.filter(funcionario__id=request.user.get_profile().pk).exists()
    tabela_polo_ano_nivel_ensino = TabelaPoloAnoNivelEnsino(obj.aluno_set.all())
    definiu_horario = obj.definiu_horario()
    turnos = obj.get_horarios_por_turno()
    coordenador_titular = obj.get_coordenador_titular()

    coordenadores = obj.coordenadorpolo_set.all()
    tutores = obj.tutorpolo_set.all()

    if request.user.has_perm('edu.change_polo'):
        url = f'/edu/polo/{obj.pk}/?tab=usuarios'
        if 'coordenador_titular_polo_id' in request.GET:
            o = get_object_or_404(CoordenadorPolo, pk=request.GET['coordenador_titular_polo_id'])
            CoordenadorPolo.objects.all().update(titular=False)
            o.titular = True
            o.save()
            return httprr(url, 'Coordenador de Polo Titular definido com sucesso.')

    return locals()


@permission_required('edu.change_polo')
@rtr()
def adicionar_coordenador_polo(request, pk):
    title = 'Adicionar Coordenador do Polo'
    polo = get_object_or_404(Polo, pk=pk)
    form = CoordenadorPoloForm(request.POST or None)
    if form.is_valid():
        form.processar(polo)
        return httprr('..', 'Coordenador de Polo adicionado com sucesso.')
    return locals()


@group_required('Administrador Acadêmico, Secretário Acadêmico')
@rtr()
def adicionar_tutor_polo(request, pk, pk_tutor=None):
    title = 'Adicionar Tutor do Polo'
    polo = get_object_or_404(Polo, pk=pk)
    tutor_polo = pk_tutor and TutorPolo.objects.get(pk=pk_tutor) or None
    form = TutorPoloForm(polo, tutor_polo, request.POST or None)
    if pk_tutor:
        form.fields['funcionario'].initial = tutor_polo.funcionario.pk
        form.fields['cursos'].initial = tutor_polo.cursos.all().values_list('pk', flat=True)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Tutor de Polo adicionado com sucesso.')
    return locals()


@group_required('Administrador Acadêmico, Secretário Acadêmico, Coordenador de Polo EAD, Aluno')
@rtr('definir_horario_polo.html')
def definir_horario_tutor_polo(request, pk):
    view_ajax = 'definir_horario_tutor_polo_ajax'
    obj = get_object_or_404(TutorPolo, pk=pk)
    definiu_horario = obj.polo.definiu_horario()
    usuario_coordenador = obj.polo.coordenadorpolo_set.filter(funcionario__id=request.user.get_profile().pk).exists()
    horario = obj.get_horario() or ''
    if horario:
        horario = f'({horario})'

    title = f'Horário do Tutor {horario}'

    if request.method == 'POST':
        return httprr('..', 'Horário definido com sucesso.')

    turnos = obj.get_horarios_por_turno()
    if usuario_coordenador or request.user.has_perm('edu.change_polo'):
        turnos.as_form = True
    else:
        turnos.as_form = False

    return locals()


@permission_required('edu.change_polo')
def definir_horario_tutor_polo_ajax(request, horario_funcionamento_pk, tutor_polo_pk, dia_semana_numero, checked):
    if checked == 'true':
        checked = True
    else:
        checked = False
    horario_funcionamento = get_object_or_404(HorarioFuncionamentoPolo, pk=horario_funcionamento_pk)
    tutor = get_object_or_404(TutorPolo, pk=tutor_polo_pk)
    if not checked:
        HorarioTutorPolo.objects.filter(tutor=tutor, dia_semana=dia_semana_numero, horario_funcionamento=horario_funcionamento).delete()
    else:
        HorarioTutorPolo.objects.create(tutor=tutor, dia_semana=dia_semana_numero, horario_funcionamento=horario_funcionamento)
    return HttpResponse('OK')


@group_required('Administrador Acadêmico, Secretário Acadêmico, Coordenador de Polo EAD')
@rtr('definir_horario_polo.html')
def definir_horario_coordenador_polo(request, pk):
    view_ajax = 'definir_horario_coordenador_polo_ajax'
    obj = get_object_or_404(CoordenadorPolo, pk=pk)
    definiu_horario = obj.polo.definiu_horario()
    horario = obj.get_horario() or ''
    if horario:
        horario = f'({horario})'

    title = f'Horário do Tutor {horario}'

    if request.method == 'POST':
        return httprr('..', 'Horário definido com sucesso.')

    turnos = obj.get_horarios_por_turno()
    if request.user.has_perm('edu.change_polo'):
        turnos.as_form = True
    else:
        turnos.as_form = False

    return locals()


@permission_required('edu.change_polo')
@rtr('definir_horario_polo.html')
def definir_horario_polo(request, pk):
    view_ajax = 'definir_horario_polo_ajax'
    obj = get_object_or_404(Polo, pk=pk)
    definiu_horario = obj.definiu_horario()

    title = f'Horário do Polo - {obj}'

    if request.method == 'POST':
        return httprr('..', 'Horário definido com sucesso.')

    turnos = obj.get_horarios_por_turno()
    if request.user.has_perm('edu.change_polo'):
        turnos.as_form = True
    else:
        turnos.as_form = False

    return locals()


@permission_required('edu.change_polo')
def definir_horario_coordenador_polo_ajax(request, horario_funcionamento_pk, coordenador_polo_pk, dia_semana_numero, checked):
    if checked == 'true':
        checked = True
    else:
        checked = False
    horario_funcionamento = get_object_or_404(HorarioFuncionamentoPolo, pk=horario_funcionamento_pk)
    coordenador = get_object_or_404(CoordenadorPolo, pk=coordenador_polo_pk)
    if not checked:
        HorarioCoordenadorPolo.objects.filter(coordenador=coordenador, dia_semana=dia_semana_numero, horario_funcionamento=horario_funcionamento).delete()
    else:
        HorarioCoordenadorPolo.objects.create(coordenador=coordenador, dia_semana=dia_semana_numero, horario_funcionamento=horario_funcionamento)
    return HttpResponse('OK')


@permission_required('edu.change_polo')
def definir_horario_polo_ajax(request, horario_funcionamento_pk, polo_pk, dia_semana_numero, checked):
    if checked == 'true':
        checked = True
    else:
        checked = False
    horario_funcionamento = get_object_or_404(HorarioFuncionamentoPolo, pk=horario_funcionamento_pk)
    polo = get_object_or_404(Polo, pk=polo_pk)
    if not checked:
        HorarioPolo.objects.filter(polo=polo, dia_semana=dia_semana_numero, horario_funcionamento=horario_funcionamento).delete()
    else:
        HorarioPolo.objects.create(polo=polo, dia_semana=dia_semana_numero, horario_funcionamento=horario_funcionamento)
    return HttpResponse('OK')


@login_required()
@rtr()
def horario_atendimento_polo(request):
    title = 'Horários de Atendimento dos Polos'
    form = HorarioAtendimentoPoloForm(request.GET or None)
    if form.is_valid():
        polos = form.processar()
        if 'imprimir' in request.GET:
            return horario_atendimento_polo_pdf(request)
        if 'xls' in request.GET:
            rows = []
            for polo in polos:
                if polo.get_horarios_por_turno():
                    rows.append([polo])
                    for turno in polo.get_horarios_por_turno():
                        header = [turno, 'Segunda', 'Terça', 'Quarta', 'Quinta', 'Sexta', 'Sábado', 'Domingo']
                        rows.append(header)
                        for horario in turno.horarios:
                            row = [format_(horario)]
                            for dia_semana in horario.dias_semana:
                                row.append(format_(dia_semana['tutores']))
                            rows.append(row)
                rows.append([])
            return XlsResponse(rows)
    return locals()


@documento()
@login_required()
@rtr()
def horario_atendimento_polo_pdf(request):
    title = 'Imprimir Horários de Atendimento dos Polos'
    form = HorarioAtendimentoPoloForm(data=request.GET or None)
    if form.is_valid():
        polos = form.processar()
    uo = request.user.get_profile().funcionario.setor.uo
    return locals()


@rtr()
@permission_required('edu.gerar_relatorio')
def relatorio_ead(request):
    title = 'Relatório EAD'
    tabela_aluno_polo_nivel_ensino = TabelaAlunoPoloNivelEnsino(Aluno.objects.all())
    return locals()


@login_required()
@rtr()
def atividades_polo_aluno(request):
    aluno = get_object_or_404(Aluno, matricula=request.user.username)
    atividades = AtividadePolo.objects.filter(polo=aluno.polo, data_inicio__gte=datetime.datetime.now()).order_by('data_inicio').order_by('data_fim')
    title = f'Próximas Atividades do Polo - {aluno.polo}'
    return locals()


@login_required()
@rtr()
def atividades_polo_tutor(request):
    polos = Polo.objects.filter(tutorpolo__funcionario__username=request.user.username)
    atividades = AtividadePolo.objects.filter(polo__in=polos, data_inicio__gte=datetime.datetime.now()).order_by('data_inicio').order_by('data_fim')
    title = 'Próximas Atividades dos Polos'
    return locals()


@login_required()
@rtr()
def meus_dados_academicos(request):
    obj = get_object_or_404(Aluno, matricula=request.user.username)
    return HttpResponseRedirect(obj.get_absolute_url())


@login_required()
@rtr()
def minha_caracterizacao_socioeconomica(request):
    obj = get_object_or_404(Aluno, matricula=request.user.username)
    return HttpResponseRedirect(f'/ae/caracterizacao/{obj.pk}/')


@login_required()
@group_required('Administrador Acadêmico')
@rtr()
def enviar_planilha_mensal_aula_campo(request, pk):
    title = 'Enviar Planilha Mensal das Aulas de Campo à Seguradora'
    obj = get_object_or_404(ConfiguracaoSeguro, pk=pk)
    form = EnviarPlanilhaMensalSeguroAulaCampoForm(obj, data=request.POST or None)

    if form.is_valid():
        sucesso = form.processar()

        if sucesso:
            return httprr('..', 'Planilha enviada com sucesso.')
        else:
            return httprr('..', 'Atenção: Não foi possível enviar a Planilha pois não existem aulas de campos para o período selecionado.', 'error')
    return locals()


@rtr()
@login_required()
def configuracao_certificacao_enem(request, pk):
    obj = get_object_or_404(ConfiguracaoCertificadoENEM, pk=pk)
    pedidos_certificado = obj.registroalunoinep_set.all().order_by('nome')
    form = PesquisarRegistroAlunoINEPForm(obj, data=request.GET or None)

    if form.is_valid():
        pedidos_certificado = form.processar(obj)

    title = 'Configuração para Certificação ENEM'
    return locals()


@rtr()
@login_required()
def editar_registro_inep(request, pk):
    obj = get_object_or_404(RegistroAlunoINEP, pk=pk)
    form = EditarRegistroAlunoINEPForm(instance=obj, data=request.POST or None)

    if form.is_valid():
        form.save()
        return httprr('..', 'Registro atualizado com sucesso.')

    title = 'Editar Registro de Aluno no INEP'
    return locals()


@rtr()
@login_required()
def solicitacao_certificado_enem(request, pk):
    obj = get_object_or_404(SolicitacaoCertificadoENEM, pk=pk)
    mime_types_imagem = ('image/jpeg', 'image/pjpeg', 'image/png')
    title = 'Solicitação de Certificado ENEM'

    is_avaliada = obj.avaliada
    is_anterior_2014 = obj.configuracao_certificado_enem.ano.ano <= 2013

    return locals()


@documento(enumerar_paginas=False)
@rtr('comprovante_solicitacao_certificado_enem_pdf.html')
def comprovante_solicitacao_certificado_enem_pdf(request, codigo_geracao_solicitacao):
    obj = get_object_or_404(SolicitacaoCertificadoENEM, codigo_geracao_solicitacao=codigo_geracao_solicitacao)
    uo = UnidadeOrganizacional.objects.suap().get(sigla=get_sigla_reitoria())
    title = 'Comprovante de Solicitação de Certificado ENEM'
    hoje = datetime.datetime.now()
    url_suap = settings.SITE_URL
    data_maxima_atendimento = obj.data_solicitacao + relativedelta(months=1)

    if obj.configuracao_certificado_enem.ano.ano <= 2013:
        return httprr('..', 'Não é possível imprimir o comprovante para solicitações de anos anteriores a 2014.', 'error')

    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()

    return locals()


@rtr()
def solicitar_certificado_enem(request):
    title = 'Solicitar Certificado ENEM'
    category = 'Solicitações'
    icon = 'certificate'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    if request.method == 'POST':
        form = SolicitarCertificadoENEMForm(request.POST or None, files=request.FILES)
    else:
        form = SolicitarCertificadoENEMForm()

    if form.is_valid():
        obj = form.processar()
        return httprr(
            f'/edu/comprovante_solicitacao_certificado_enem/{obj.codigo_geracao_solicitacao}',
            'A sua Solicitação foi realizada com sucesso e será analisada e o resultado será enviado para o seu email.',
        )

    return locals()


@rtr()
def consultar_andamento_certificado_enem(request):
    title = 'Consultar Andamento de Solicitação de Certificado ENEM'

    if request.method == 'POST':
        form = ConsultarAndamentoSolicitacaoCertificadoENEMForm(request.POST or None)
    else:
        form = ConsultarAndamentoSolicitacaoCertificadoENEMForm()

    if form.is_valid():
        obj = form.processar()
        if obj:
            is_avaliada = obj.avaliada
            is_anterior_2014 = obj.configuracao_certificado_enem.ano.ano > 2013
        else:
            is_avaliada = False
            is_anterior_2014 = False

    return locals()


@rtr()
def editar_dados_pessoais_solicitacao_enem(request, codigo_geracao_solicitacao):
    title = 'Editar meus Dados Pessoais - Solicitação de Certificado ENEM'
    solicitacao_enem = get_object_or_404(SolicitacaoCertificadoENEM, codigo_geracao_solicitacao=codigo_geracao_solicitacao)
    obj = solicitacao_enem.get_registro_aluno_inep()
    form = EditarDadosPessoaisSolicitacaoCertificadoENEM(request.POST or None, instance=obj)

    if form.is_valid():
        form.save()
        return httprr(f'/edu/comprovante_solicitacao_certificado_enem/{solicitacao_enem.codigo_geracao_solicitacao}', 'A sua Solicitação foi atualizada com sucesso.')

    return locals()


@rtr()
@permission_required('edu.change_solicitacaocertificadoenem')
@login_required()
def atender_solicitacao_certificado_enem(request, pk):
    solicitacao = get_object_or_404(SolicitacaoCertificadoENEM, pk=pk)

    try:
        ConfiguracaoLivro.objects.filter(uo__sigla=get_sigla_reitoria()).latest('numero_livro')
    except ConfiguracaoLivro.DoesNotExist:
        return httprr(
            f'/edu/solicitacao_certificado_enem/{solicitacao.pk}',
            'Não é possível atender a solicitação pois não há nenhuma Configuração de Livro cadastrada para a Reitoria. <a href="/admin/edu/configuracaolivro/add/">Deseja cadastrar agora?</a>',
            'error',
        )

    solicitacao.atender(request.user)
    registro_emissao = solicitacao.get_registro_emissao_certificado_enem()
    return httprr(f'/edu/registroemissaocertificadoenem/{registro_emissao.pk}/', 'Registro de emissão de Certificado ENEM cadastrado com sucesso.')


@rtr()
@permission_required('edu.change_solicitacaocertificadoenem')
@login_required()
def atender_com_ressalva_solicitacao_certificado_enem(request, pk):
    solicitacao = get_object_or_404(SolicitacaoCertificadoENEM, pk=pk)

    try:
        conf = ConfiguracaoLivro.objects.get(uo__sigla=get_sigla_reitoria())
    except ConfiguracaoLivro.DoesNotExist:
        return httprr(
            f'/edu/solicitacao_certificado_enem/{solicitacao.pk}',
            'Não é possível atender a solicitação pois não há nenhuma configuração de Livro cadastrada para a Reitoria. <a href="/admin/edu/configuracaolivro/add/">Deseja cadastrar agora?</a>',
            'error',
        )

    form = AtenderComRessalvaSolicitacaoCertificadoENEMForm(data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            solicitacao.atender(request.user, request.POST['razao_ressalva'])
            return httprr(f'/edu/solicitacao_certificado_enem/{solicitacao.pk}/', 'Solicitação atendida com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_solicitacaocertificadoenem')
def rejeitar_solicitacao_certificado_enem(request, pk):
    solicitacao = get_object_or_404(SolicitacaoCertificadoENEM, pk=pk)

    conf = ConfiguracaoLivro.objects.filter(uo__sigla=get_sigla_reitoria(), descricao__contains=' ENEM').first()
    if conf is None:
        return httprr(
            f'/edu/solicitacao_certificado_enem/{solicitacao.pk}',
            'Não é possível rejeitar a solicitação pois não há nenhuma configuração de Livro cadastrada para a Reitoria. <a href="/admin/edu/configuracaolivro/add/">Deseja cadastrar agora?</a>',
            'error',
        )

    form = RejeitarSolicitacaoCertificadoENEMForm(data=request.POST or None)
    if request.method == 'POST':
        if form.is_valid():
            solicitacao.rejeitar(request.user, request.POST['razao_indeferimento'])
            return httprr(f'/edu/solicitacao_certificado_enem/{solicitacao.pk}/', 'Solicitação rejeitada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_solicitacaocertificadoenem')
def replicar_solicitacao_certificado_enem(request, pk):
    solicitacao = get_object_or_404(SolicitacaoCertificadoENEM, pk=pk)
    form = ReplicarSolicitacaoCertificadoENEMForm(data=request.POST or None, instance=solicitacao, request=request)
    if form.is_valid():
        replicada = form.save()
        return httprr(f'/edu/solicitacao_certificado_enem/{replicada.pk}/', 'Solicitação replicada com sucesso.')
    return locals()


@rtr()
@login_required()
def registroemissaocertificadoenem(request, pk):
    title = 'Registro de Emissão de Certificado ENEM'
    obj = get_object_or_404(RegistroEmissaoCertificadoENEM, pk=pk)
    if 'email' in request.GET:
        obj.solicitacao.enviar_email(obj.solicitacao.avaliador)
        return httprr(f'/edu/registroemissaocertificadoenem/{pk}/', f'E-mail enviado para {obj.solicitacao.email}')
    hoje = datetime.datetime.now()
    return locals()


@rtr()
@permission_required('edu.change_registroemissaocertificadoenem')
@login_required()
def cancelar_registroemissaocertificadoenem(request, pk):
    obj = get_object_or_404(RegistroEmissaoCertificadoENEM, pk=pk)
    form = CancelarRegistroEmissaoCertificadoENEMForm(data=request.POST or None, instance=obj)
    if request.method == 'POST':
        if form.is_valid():
            obj.cancelar(request.user, request.POST['razao_cancelamento'])
            return httprr('..', 'Registro de emissão de Certificado ENEM cancelado com sucesso.')
    return locals()


@documento(enumerar_paginas=False)
@rtr('registroemissaocertificadoenem_pdf.html')
@login_required()
def registroemissaocertificadoenem_pdf(request, pk):
    obj = get_object_or_404(RegistroEmissaoCertificadoENEM, pk=pk)
    uo = UnidadeOrganizacional.objects.suap().get(sigla=get_sigla_reitoria())
    hoje = datetime.datetime.now()
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()
    return locals()


@documento('Certificado ENEM', modelo='edu.registroemissaocertificadoenem')
@rtr('imprimir_certificado_enem_pdf.html')
@login_required()
def imprimir_certificado_enem_pdf(request, pk):
    obj = get_object_or_404(RegistroEmissaoCertificadoENEM, pk=pk)
    uo = UnidadeOrganizacional.objects.suap().get(sigla=get_sigla_reitoria())
    hoje = datetime.datetime.now()

    # Verificando se o candidato é menor de idade.
    configuracao_enem = obj.solicitacao.configuracao_certificado_enem
    data_nascimento_candidato = obj.solicitacao.get_registro_aluno_inep().data_nascimento
    diferenca_em_anos = relativedelta(configuracao_enem.data_primeira_prova, data_nascimento_candidato).years
    is_menor_idade = diferenca_em_anos < 18

    if obj.solicitacao.configuracao_certificado_enem.ano.ano <= 2013:
        return httprr('..', 'Não é possível imprimir o certificado para solicitações de anos anteriores a 2014.', 'error')

    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()

    return locals()


@rtr()
@login_required()
def escolher_reitor_diretor_geral(request, pk):
    title = 'Escolher Reitor e Diretor Geral para o Certificado ENEM'
    obj = get_object_or_404(RegistroEmissaoCertificadoENEM, pk=pk)
    uo = obj.solicitacao.uo

    diretoria = Diretoria.objects.filter(setor__uo=uo)
    if diretoria:
        diretoria = diretoria[0]
    else:
        return httprr('..', 'Diretoria inexistente', 'error')

    reitoria = UnidadeOrganizacional.objects.suap().get(sigla=get_sigla_reitoria())
    initial = dict(reitor=reitoria.get_diretor_geral(True) and reitoria.get_diretor_geral(True)[0].pk or None, diretor_geral=diretoria.diretor_geral.pk)

    form = EscolherReitorDiretorGeralForm(diretoria.get_diretores_gerais(), data=request.POST or None, initial=initial)

    if form.is_valid():
        reitor = form.cleaned_data.get('reitor').pk
        diretor_geral = form.cleaned_data.get('diretor_geral').pk

        reitor_em_exercicio = form.initial['reitor'] != form.cleaned_data.get('reitor').pk
        diretor_geral_em_exercicio = form.initial['diretor_geral'] != form.cleaned_data.get('diretor_geral').pk

        return httprr(
            '/edu/imprimir_certificado_enem_antes_2014_pdf/{}/?reitor={}&reitor_em_exercicio={}&diretor_geral={}&diretor_geral_em_exercicio={}'.format(
                pk, reitor, reitor_em_exercicio, diretor_geral, diretor_geral_em_exercicio
            )
        )
    return locals()


@documento(enumerar_paginas=False)
@rtr('imprimir_certificado_enem_antes_2014_pdf.html')
@login_required()
def imprimir_certificado_enem_antes_2014_pdf(request, pk):
    hoje = datetime.datetime.now()

    if not request.GET.get('reitor') or not request.GET.get('diretor_geral'):
        return httprr('..', 'Você precisa definir o Reitor e o Diretor Geral.', 'error')

    reitor = Servidor.objects.get(pk=request.GET.get('reitor'))
    diretor_geral = Servidor.objects.get(pk=request.GET.get('diretor_geral'))

    reitor_em_exercicio = request.GET.get('reitor_em_exercicio')
    diretor_geral_em_exercicio = request.GET.get('diretor_geral_em_exercicio')

    obj = get_object_or_404(RegistroEmissaoCertificadoENEM, pk=pk)
    uo = obj.solicitacao.uo
    reitoria = UnidadeOrganizacional.objects.suap().get(sigla=get_sigla_reitoria())

    cargo_diretor = 'Diretor{}-Geral {} - {}'.format(diretor_geral.sexo == 'F' and 'a' or '', diretor_geral_em_exercicio == 'True' and 'em Exercício' or '', normalizar(uo.nome))
    cargo_reitor = 'Reitor{} {}'.format(reitor.sexo == 'F' and 'a' or '', reitor_em_exercicio == 'True' and 'em Exercício' or '')

    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')

    return locals()


@documento('Certificado ENEM', modelo='edu.registroemissaocertificadoenem')
@rtr('imprimir_certificado_enem_pdf.html')
def gerar_certificado_enem_pdf(request, pk):
    obj = get_object_or_404(RegistroEmissaoCertificadoENEM, pk=pk)
    if obj.cancelado:
        return httprr(
            '/edu/solicitar_certificado_enem/',
            f'O certificado não pode ser gerado porque foi cancelado pelo servidor {obj.responsavel_cancelamento} pelo seguinte motivo: "{obj.razao_cancelamento}"',
            'error',
        )

    uo = UnidadeOrganizacional.objects.suap().get(sigla=get_sigla_reitoria())
    hoje = datetime.datetime.now()
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()
    return locals()


def gerar_certificado_enem(request, codigo_geracao_certificado):
    obj = get_object_or_404(RegistroEmissaoCertificadoENEM, codigo_geracao_certificado=codigo_geracao_certificado)
    return gerar_certificado_enem_pdf(request, pk=obj.pk)


@permission_required('edu.lancar_nota_diario')
@rtr()
def registrar_nota_ajax(request, id_nota_avaliacao, nota=None):
    nota_avaliacao = get_object_or_404(NotaAvaliacao, pk=id_nota_avaliacao)
    etapa = nota_avaliacao.item_configuracao_avaliacao.configuracao_avaliacao.etapa
    diario = nota_avaliacao.matricula_diario.diario
    pode_registrar_nota = False
    # se a situação do aluno no diário for "Cursando"
    if nota_avaliacao.matricula_diario.is_cursando():
        qs_professor_diario = diario.professordiario_set.filter(professor__vinculo__user=request.user)

        if perms.realizar_procedimentos_academicos(request.user, diario.turma.curso_campus) and diario.em_posse_do_registro(etapa):
            pode_registrar_nota = True

        elif qs_professor_diario.exists() and not diario.em_posse_do_registro(etapa):
            unico_professor = diario.professordiario_set.filter(ativo=True).count() == 1
            if unico_professor or diario.estrutura_curso.pode_lancar_nota_fora_do_prazo:
                pode_registrar_nota = True
            else:
                data_atual = datetime.date.today()
                etapa_string = etapa == 5 and 'final' or str(etapa)
                professor_diario = qs_professor_diario[0]
                data_inicio_etapa = getattr(professor_diario, f'data_inicio_etapa_{etapa_string}', None)
                data_fim_etapa = getattr(professor_diario, f'data_fim_etapa_{etapa_string}', None)
                if data_inicio_etapa and data_fim_etapa and data_inicio_etapa <= data_atual <= data_fim_etapa:
                    pode_registrar_nota = True

    if pode_registrar_nota:
        nota_avaliacao.nota = None if nota is None else float(nota)
        nota_avaliacao.save()
        nota_avaliacao.matricula_diario.registrar_nota_etapa(nota_avaliacao.item_configuracao_avaliacao.configuracao_avaliacao.etapa)
        attr_nota = 'nota_{}'.format(int(etapa) == 5 and 'final' or etapa)
        attr_etapa = f'posse_etapa_{etapa}'
        nota_etapa = getattrr(nota_avaliacao.matricula_diario, attr_nota)
        posse_etapa = getattrr(nota_avaliacao.matricula_diario.diario, attr_etapa)
        dict_resposta = {
            'etapa': '-' if nota_etapa is None else nota_etapa,
            'media': nota_avaliacao.matricula_diario.get_media_disciplina() or '-',
            'media_final': nota_avaliacao.matricula_diario.get_media_final_disciplina() or '-',
            'situacao': nota_avaliacao.matricula_diario.get_situacao_nota(),
            'posse': posse_etapa,
            'em_prova_final': nota_avaliacao.matricula_diario.is_em_prova_final(),
            'prova_final_invalida': not nota_avaliacao.matricula_diario.is_em_prova_final() and nota_avaliacao.matricula_diario.nota_final,
        }
        return JsonResponse(dict_resposta)


@permission_required('edu.add_configuracaopedidomatricula')
@rtr()
def monitoramento_fechamento_periodo(request):
    title = 'Monitoramento de Fechamento de Período'

    periodo_letivo_atual = PeriodoLetivoAtual.get_instance(request)
    ano_letivo = Ano.objects.get(ano=periodo_letivo_atual.ano).pk
    periodo_letivo = periodo_letivo_atual.periodo
    diretorias = Diretoria.locals.all()
    initial = dict(ano_letivo=ano_letivo, periodo_letivo=periodo_letivo, diretorias=diretorias)
    form = MonitoramentoFechamentoPeriodoForm(request.GET or None, request=request, initial=initial)

    if form.is_valid():
        matriculas_periodos, graficos = form.processar()
        agrupamento = form.cleaned_data['agrupamento']

    return locals()


@login_required()
@rtr()
def monitoramento_entrega_diarios(request):
    title = 'Monitoramento de Entrega de Diários'

    periodo_letivo_atual = PeriodoLetivoAtual.get_instance(request)
    ano_letivo = Ano.objects.get(ano=periodo_letivo_atual.ano).pk
    periodo_letivo = periodo_letivo_atual.periodo
    diretorias = Diretoria.locals.all()
    initial = dict(ano_letivo=ano_letivo, periodo_letivo=periodo_letivo, diretorias=diretorias)
    form = MonitoramentoEntregaDiariosForm(request.GET or None, request=request, initial=initial)

    if form.is_valid():
        com_grafico = not in_group(request.user, 'Administrador Acadêmico')
        professores_diario, graficos = form.processar(com_grafico)
        qtd_diarios = professores_diario.values_list('diario__id', flat=True).distinct().count()
        qtd_professores = professores_diario.values_list('professor__id', flat=True).distinct().count()
        agrupamento = form.cleaned_data['agrupamento']

    return locals()


@permission_required('edu.add_matriz')
@rtr()
def inserir_diretoria_curso(request, pk):
    title = 'Inserir Diretoria em Curso'
    curso_campus = get_object_or_404(CursoCampus, pk=pk)
    form = InserirDiretoriaForm(request.POST or None, request=request)

    if curso_campus.diretoria:
        return httprr('..', 'Curso selecionado já possui diretoria.', 'error')

    if form.is_valid():
        curso_campus.diretoria = form.cleaned_data['diretoria']
        curso_campus.save()
        return httprr('..', 'Diretoria atualizada com sucesso.')

    return locals()


@permission_required('ponto.pode_ver_frequencia_propria')
@rtr()
def estatistica(request):
    title = 'Quantitativo de Alunos'
    form = EstatisticaForm(request.GET or None, request=request)

    if form.is_valid():
        uos, anos, periodos, uo_selecionada, ano_selecionado, periodo_selecionado, grafico_ano, alunos = form.processar()
        agrupar = form.cleaned_data.get('agrupar')
        tabela = TabelaResumoAluno(alunos)
        series = []
        for i, modalidade in enumerate(tabela.colunas):
            series.append([modalidade, tabela.registros[len(tabela.registros) - 1][i]])
        series = series[1:-1]

        id_grafico = 'id_grafico_x'
        grafico = PieChart(id_grafico, title='Total de Alunos por Modalidade', data=series)
        grafico.id = id_grafico

        if uo_selecionada:
            tabela_por_curso = TabelaResumoMPCurso(alunos)
            if uo_selecionada.pk == 14:
                tabela_aluno_polo_nivel_ensino = TabelaMPPoloNivelEnsino(alunos)
                tabela_aluno_curso_polo = TabelaAlunoCursoCampusPolo(alunos)

        if 'xls' in request.GET:
            if not request.GET.get('tab') == 'total_curso':
                return tasks.exportar_estaticas_xls(alunos)
            else:
                rows = [['Código', 'Descrição', 'Campus', 'Modalidade', 'Quantidade']]
                count = 0
                for registro in TabelaResumoMPCurso(alunos).registros:
                    count += 1
                    rows.append(list(registro.values()))
                return XlsResponse(rows)

        alunos = alunos[0:25]
    return locals()


@permission_required('edu.gerar_relatorio')
@rtr()
def variaveis(request, indicador, ano, uo, modalidades, curso):
    title = f'{IndicadoresForm.INDICADORES[indicador][0]} - {ano}'
    ano = int(ano)
    uos = uo.split('_')
    modalidades = modalidades.split('_')
    curso = int(curso)
    tipos_necessidade_especial = request.GET.get('tipos_necessidade_especial') and request.GET.get('tipos_necessidade_especial').split('_')
    tipos_transtorno = request.GET.get('tipos_transtorno') and request.GET.get('tipos_transtorno').split('_')
    superdotacao = request.GET.get('superdotacao') and request.GET.get('superdotacao').split('_')
    variaveis = IndicadoresForm.processar_variaveis(
        ano, ano, modalidades, uos, curso_id=curso, tipos_necessidade_especial=tipos_necessidade_especial, tipos_transtorno=tipos_transtorno, superdotacao=superdotacao
    )
    taxa_conclusao = float(variaveis['CONCLUIDOS'][ano].count()) / float(variaveis['ATENDIDOS'][ano].count() or 1) * 100
    taxa_ativos_regulares = float(variaveis['CONTINUADOS_REGULARES'][ano].count()) / float(variaveis['ATENDIDOS'][ano].count() or 1) * 100
    if 'variavel' in request.GET:
        alunos = Aluno.objects.filter(id__in=variaveis[request.GET.get('variavel')][ano])[0:100]
    return locals()


@login_required()
@rtr()
def indicadores(request):
    if (
        not request.user.has_perm('edu.efetuar_matricula')
        and not request.user.has_perm('edu.gerar_relatorio')
        and not request.user.has_perm('edu.view_aluno')
    ):
        return httprr('/', 'Você não tem permissão para acessar essa página', 'error')
    title = 'Indicadores de Ensino'
    is_administador = in_group(request.user, 'Administrador Acadêmico')
    form = IndicadoresForm(request.GET or None, request=request)
    indicadores_colunas = form.INDICADORES
    parametros = request.META.get('QUERY_STRING', '')
    if form.is_valid():
        uos, anos, uo_selecionada, indicadores, modalidade_selecionada, modalidades, curso_selecionado, cursos, tipos_necessidade_especial, tipos_transtorno, superdotacao = (
            form.processar_indicadores()
        )
        modalidades_pks = modalidades.values_list('pk', flat=True)
        uos_links = uos
        if uo_selecionada:
            uos_links = [UnidadeOrganizacional.objects.suap().get(pk=uo_selecionada)]
        uos_links = '_'.join([str(uo.pk) for uo in uos_links])
        if 'xls' in request.GET and ('uo_selecionada' in request.GET or is_administador):
            uos = []
            if request.GET.get('uo_selecionada') is None:
                uos.extend(uos_links.split('_'))
                cursos = CursoCampus.objects.filter(diretoria__setor__uo_id__in=uos, modalidade_id__in=modalidades_pks)
            else:
                uos.append(request.GET.get('uo_selecionada'))
            return tasks.exportar_indicadores_xls(cursos, anos, modalidades, uos, tipos_necessidade_especial, tipos_transtorno, superdotacao)

    return locals()


@permission_required('edu.gerar_relatorio')
@rtr()
def relatorio_periodos_abertos(request):
    title = 'Relatório de Alunos com Períodos Não-Fechados'

    form = RelatorioPeriodosAbertosForm(request.GET or None, request=request)

    is_administador = in_group(request.user, 'Administrador Acadêmico')

    situacoes = [2]
    series = []
    anos = (
        Ano.objects.filter(matriculaperiodo__ano_letivo__ano__lt=datetime.datetime.now().year, matriculaperiodo__situacao__id__in=situacoes)
        .order_by('-matriculaperiodo__ano_letivo__ano')
        .values_list('ano', flat=True)
        .distinct()[0:15]
    )

    if 'ano_selecionado' in request.GET:
        ano_selecionado = int(request.GET['ano_selecionado'])
    else:
        ano_selecionado = anos[0]

    ids = []
    qs = MatriculaPeriodo.objects.filter(situacao__id__in=situacoes)

    if form.is_valid():
        modalidades = form.cleaned_data['modalidades']
        cursos = form.cleaned_data['cursos']

        if modalidades:
            qs = qs.filter(aluno__curso_campus__modalidade__in=modalidades)

        if cursos:
            qs = qs.filter(aluno__curso_campus__in=cursos)

    if not is_administador:
        ids_uos = Diretoria.locals.all().values_list('setor__uo', flat=True).order_by('setor__uo').distinct()
    else:
        ids_uos = (
            qs.filter(aluno__curso_campus__diretoria__setor__uo__isnull=False)
            .order_by('aluno__curso_campus__diretoria__setor__uo')
            .values_list('aluno__curso_campus__diretoria__setor__uo', flat=True)
            .distinct()
        )

    if not ids_uos:
        return httprr('/', 'Você não tem permissão para realizar isso.', 'error')
    uos = UnidadeOrganizacional.objects.suap().filter(id__in=ids_uos)
    uo_selecionada = None
    if 'uo_selecionada' in request.GET:
        uo_selecionada_id = request.GET['uo_selecionada']
        if uo_selecionada_id:
            uo_selecionada = UnidadeOrganizacional.objects.suap().get(pk=uo_selecionada_id)

    if not is_administador and not uo_selecionada:
        uo_selecionada = uos and uos[0] or None

    ano_corrente = int(Configuracao.get_valor_por_chave('edu', 'ano_letivo_atual') or datetime.date.today().year)
    periodo_corrente = int(Configuracao.get_valor_por_chave('edu', 'periodo_letivo_atual') or 1)

    if periodo_corrente == 1:
        qs = qs.exclude(ano_letivo__ano=ano_corrente)
    else:
        qs = qs.exclude(ano_letivo__ano=ano_corrente, periodo_letivo=2).exclude(ano_letivo__ano=ano_corrente, aluno__curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL)

    for ano in anos:
        serie = []
        serie.append(ano)
        if is_administador:
            tmp = qs.filter(ano_letivo__ano=ano).values_list('aluno__id', flat=True)
            serie.append(len(set(tmp)))
        qs_tmp_ano = qs.filter(ano_letivo__ano=ano)
        if uo_selecionada:
            qs_tmp_ano = qs_tmp_ano.filter(aluno__curso_campus__diretoria__setor__uo=uo_selecionada)
        tmp_campus = qs_tmp_ano.values_list('aluno__id', flat=True)
        if ano == ano_selecionado:
            ids = tmp_campus
        serie.append(len(set(tmp_campus)))
        series.append(serie)
    alunos = Aluno.objects.filter(id__in=ids).order_by('curso_campus')

    groups = None
    disabled_groups = []
    if is_administador:

        if uo_selecionada:
            groups = ['Instituto', uo_selecionada.nome]
            disabled_groups = ['Instituto']
        else:
            groups = ['Instituto']

    else:
        groups = [uo_selecionada.nome]

    id_grafico = '1'
    grafico = GroupedColumnChart(id_grafico, title='Alunos com Período Letivo Aberto', data=series, groups=groups, disabled_groups=disabled_groups)

    grafico = grafico
    grafico.id = id_grafico

    if 'xls' in request.GET:
        rows = [['#', 'Ano', 'Matrícula', 'Aluno', 'Curso' 'Situação no Curso', 'Diretoria', 'Câmpus']]
        count = 0
        for aluno in alunos:
            count += 1
            row = [
                count,
                format_(ano_selecionado),
                format_(aluno.matricula),
                format_(aluno.get_nome_social_composto()),
                format_(aluno.curso_campus),
                format_(aluno.curso_campus.diretoria),
                format_(aluno.curso_campus.diretoria.setor.uo),
                format_(aluno.situacao),
            ]
            rows.append(row)
        return XlsResponse(rows)

    return locals()


@rtr()
@permission_required('edu.view_configuracaopedidomatricula')
def acompanhamento_matricula_turma(request):
    title = 'Matrícula de Ingressantes na Turma'
    form = MatriculaIngressosTurmaForm(request.GET or None)
    if form.is_valid():
        turmas, alunos_aptos_matricular = form.processar()
        qtd_turmas = len(turmas)
        alunos_sem_turma_geradas = (
            Aluno.get_ingressantes_sem_turma(form.cleaned_data['ano_letivo'], form.cleaned_data['periodo_letivo'], form.cleaned_data['diretoria'], form.cleaned_data['curso'])
            .exclude(id__in=alunos_aptos_matricular)
            .distinct()
            .order_by("pessoa_fisica__nome")
        )
        qtd_alunos_sem_turma_geradas = alunos_sem_turma_geradas.count()
        alunos_com_turma_geradas = Aluno.objects.filter(id__in=alunos_aptos_matricular).order_by("pessoa_fisica__nome")
        qtd_alunos_com_turma_geradas = alunos_com_turma_geradas.count()
        qtd_alunos = qtd_alunos_sem_turma_geradas + qtd_alunos_com_turma_geradas
    return locals()


@rtr()
@permission_required('edu.view_configuracaopedidomatricula')
def visualizar_alunos_pedido_diario(request, pk_configuracao, pk_diario):
    configuracao = get_object_or_404(ConfiguracaoPedidoMatricula, pk=pk_configuracao)
    diario = get_object_or_404(Diario, pk=pk_diario)
    title = str(diario)
    pedidos_alunos_diario = PedidoMatriculaDiario.objects.filter(diario__id=pk_diario, pedido_matricula__configuracao_pedido_matricula__pk=pk_configuracao).order_by(
        'pedido_matricula__matricula_periodo__aluno__pessoa_fisica__nome'
    )
    return locals()


@documento()
@rtr()
@permission_required('edu.view_configuracaopedidomatricula')
def imprimir_pedido_diario_pdf(request, pk_configuracao, pk_diario):
    configuracao = get_object_or_404(ConfiguracaoPedidoMatricula, pk=pk_configuracao)
    quantitativos_diario = configuracao.get_diarios_quantitativos(pk_diario)
    pedidos_alunos_diario = PedidoMatriculaDiario.objects.filter(diario__id=pk_diario, pedido_matricula__configuracao_pedido_matricula__pk=pk_configuracao).order_by(
        'pedido_matricula__matricula_periodo__aluno__pessoa_fisica__nome'
    )
    if pedidos_alunos_diario.exists():
        uo = pedidos_alunos_diario[0].diario.turma.curso_campus.diretoria.setor.uo
    return locals()


@documento()
@login_required()
@rtr()
@permission_required('edu.view_configuracaopedidomatricula')
def imprimir_pedidos_diarios_pdf(request, pk_configuracao):
    configuracao = get_object_or_404(ConfiguracaoPedidoMatricula, pk=pk_configuracao)
    uo = configuracao.cursos.all()[0].diretoria.setor.uo
    quantitativos_diario = configuracao.get_diarios_quantitativos()
    quantitativo_diarios_alunos = []
    for quantitativo_diario in quantitativos_diario:
        diario_pk = quantitativo_diario[10]
        pedidos_alunos_diario = PedidoMatriculaDiario.objects.filter(diario__pk=diario_pk, pedido_matricula__configuracao_pedido_matricula__pk=pk_configuracao).order_by(
            'pedido_matricula__matricula_periodo__aluno__pessoa_fisica__nome'
        )
        quantitativo_diario.append(pedidos_alunos_diario)
        quantitativo_diarios_alunos.append(quantitativo_diario)
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()
    return locals()


@documento()
@login_required()
@rtr()
@permission_required('edu.view_configuracaopedidomatricula')
def imprimir_pedidos_alunos_pdf(request, pk_configuracao):
    configuracao = get_object_or_404(ConfiguracaoPedidoMatricula, pk=pk_configuracao)
    uo = configuracao.cursos.all()[0].diretoria.setor.uo
    pedidos_matriculas_periodos = MatriculaPeriodo.objects.filter(pedidomatricula__configuracao_pedido_matricula=configuracao).distinct().order_by('aluno__pessoa_fisica__nome')
    pedidos_alunos_diarios = []
    for matricula_periodo in pedidos_matriculas_periodos:
        pedidos_alunos = []
        pedidos_alunos.append(matricula_periodo)
        pedidos_diarios_aluno = PedidoMatriculaDiario.objects.filter(
            pedido_matricula__matricula_periodo=matricula_periodo, pedido_matricula__configuracao_pedido_matricula__pk=pk_configuracao
        ).order_by('diario__componente_curricular__componente__descricao')
        pedidos_alunos.append(pedidos_diarios_aluno)
        pedidos_alunos_diarios.append(pedidos_alunos)

    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao').upper()

    return locals()


@rtr()
@permission_required('edu.change_diretoria')
def adicionar_coordenador_registro_academico(request, pk_diretoria, pk_membro=None):
    diretoria = Diretoria.objects.get(pk=pk_diretoria)
    coordenador = None

    if pk_membro:
        usuario_grupo = get_object_or_404(UsuarioGrupo, pk=pk_membro)
        servidor = usuario_grupo.user.get_profile().funcionario.servidor
        qs_coordenador = CoordenadorRegistroAcademico.objects.filter(diretoria=diretoria, servidor=servidor)

        if qs_coordenador.exists():
            coordenador = qs_coordenador.first()

    title = 'Adicionar/Remover Responsável pela Emissão do Diploma'
    form = CoordenadorRegistroAcademicoForm(data=request.POST or None, instance=coordenador, diretoria=diretoria)
    if form.is_valid():
        coordenador = form.save(False)
        coordenador.diretoria = diretoria
        coordenador.save()
        return httprr('..', 'Responsável pela Emissão do Diploma cadastrado/atualizado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_diretoria')
def remover_coordenador_registro_academico(request, pk_diretoria, pk_membro):
    diretoria = Diretoria.objects.get(pk=pk_diretoria)
    usuario_grupo = get_object_or_404(UsuarioGrupo, pk=pk_membro)
    usuario_grupo.delete()
    servidor = usuario_grupo.user.get_profile().funcionario.servidor
    CoordenadorRegistroAcademico.objects.filter(diretoria=diretoria, servidor=servidor).update(ativo=False)
    return httprr(f'/edu/diretoria/{diretoria.pk}/?tab=3', 'Responsável pela Emissão do Diploma removido com sucesso')


@rtr()
@permission_required('edu.change_diretoria')
def adicionar_coordenador_modalidade(request, pk_diretoria, pk_coordenador):
    diretoria = Diretoria.objects.get(pk=pk_diretoria)
    coordenador = int(pk_coordenador) and CoordenadorModalidade.objects.get(pk=pk_coordenador) or None
    title = 'Adicionar Coordenador de Modalidade de Ensino'
    form = CoordenadorModalidadeForm(data=request.POST or None, instance=coordenador, diretoria=diretoria)
    if form.is_valid():
        coordenador = form.save(False)
        coordenador.diretoria = diretoria
        coordenador.save()
        coordenador.modalidades.set(form.cleaned_data.get('modalidades'))
        coordenador.save()
        return httprr('..', 'Coordenador de registro acadêmico cadastrado/atualizado com sucesso.')
    return locals()


@rtr()
@group_required('Administrador Acadêmico,Diretor Acadêmico,Secretário Acadêmico')
def exibir_diarios_fechamento(request, pk):
    title = 'Diários'
    matricula_periodo = MatriculaPeriodo.objects.get(pk=pk)
    return locals()


@permission_required('edu.add_componente')
@rtr()
def importar_componentes(request):
    title = 'Importar Componentes'
    form = ImportarComponentesForm(data=request.POST or None, files=request.FILES or None)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Componentes importados com sucesso.')
    return locals()


@permission_required('edu.add_componentecurricular')
@rtr()
def importar_componentes_matriz(request, pk_matriz):
    matriz = get_object_or_404(Matriz, pk=pk_matriz)
    title = f'Importar Componentes em {matriz}'
    form = ImportarComponentesMatrizForm(matriz, data=request.POST or None, files=request.FILES or None)
    if form.is_valid():
        form.processar()
        return httprr(f'/edu/matriz/{matriz.pk}/?tab=componentes', 'Componentes importados com sucesso.')
    return locals()


@rtr()
@login_required()
def videos(request):
    title = 'Vídeo-Aula - Efetuar Matrícula por Processo Seletivo'
    return locals()


@rtr()
@group_required('Administrador Acadêmico,Diretor Acadêmico,Secretário Acadêmico,Coordenador de Curso')
def definir_coordenador_estagio_docente(request, pk):
    title = 'Definir Coordenadores de Estágio Docente'
    curso_campus = get_object_or_404(CursoCampus, pk=pk)
    form = DefinirCoordenadoresEstagioDocente(request.POST or None, instance=curso_campus)
    if form.is_valid():
        form.save()
        return httprr('..', 'Coordenadores de Estágio Docente definidos com sucesso.')
    return locals()


@rtr()
@permission_required('edu.efetuar_matricula')
def editar_diretoria_curso(request, pk):
    title = 'Editar Diretoria'
    curso_campus = get_object_or_404(CursoCampus, pk=pk)
    form = EditarDiretoriaCurso(request.POST or None, instance=curso_campus)
    if form.is_valid():
        form.save()
        return httprr('..', 'Diretoria editada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.efetuar_matricula')
@login_required()
def transferir_polo_aluno(request):
    title = 'Alterar Polo de Aluno'
    form = TransferirPoloAlunoForm(request.POST or None)
    if form.is_valid():
        form.processar()
        return httprr('/edu/transferir_polo_aluno/', 'Polo do(s) aluno(s) transferido(s) com sucesso.')
    return locals()


@permission_required('edu.change_configuracaopedidomatricula')
@rtr()
def replicar_configuracao_pedido_matricula(request, pk):
    configuracao_pedido_matricula = get_object_or_404(ConfiguracaoPedidoMatricula, pk=pk)
    title = f'Replicação da Configuração de Pedido de Matrícula - {configuracao_pedido_matricula.descricao}'
    initial = dict(
        descricao=f'{configuracao_pedido_matricula.descricao} [NOVA CHAMADA]',
        impedir_troca_turma=configuracao_pedido_matricula.impedir_troca_turma,
        restringir_por_curso=configuracao_pedido_matricula.restringir_por_curso,
        requer_atualizacao_dados=configuracao_pedido_matricula.requer_atualizacao_dados,
        requer_atualizacao_caracterizacao=configuracao_pedido_matricula.requer_atualizacao_caracterizacao,
    )
    form = ReplicacaoConfiguracaoPedidoMatriculaForm(data=request.POST or None, initial=initial)
    if request.POST and form.is_valid():
        try:
            resultado = form.processar(configuracao_pedido_matricula)
            return httprr(f'/edu/configuracao_pedido_matricula/{resultado.pk}/', 'Configuração de Renovação de Matrícula replicada com sucesso.')
        except ValidationError as e:
            return httprr('.', f'Não foi possível replicar a Configuração de Renovação de Matrícula: {e.messages[0]}', 'error')
    return locals()


@rtr()
def alterar_matriz_aluno(request, pk_aluno):
    aluno = get_object_or_404(Aluno.objects, pk=pk_aluno)
    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    title = f'Alterar Matriz - {aluno}'
    form = AlterarMatrizAlunoForm(data=request.POST or None, instance=aluno)
    if form.is_valid():
        form.save()
        return httprr('..', 'Matriz alterada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.view_convocacaoenade')
def convocacao_enade(request, pk):
    obj = get_object_or_404(ConvocacaoENADE, pk=pk)
    title = 'Convocação do ENADE'
    acesso_total = request.user.has_perm('edu.change_convocacaoenade')
    pk_cursos_nao_convocados = pk__in = (
        obj.registroconvocacaoenade_set.exclude(aluno__curso_campus__in=obj.cursos.values_list('pk', flat=True))
        .order_by('aluno__curso_campus')
        .values_list('aluno__curso_campus', flat=True)
        .distinct()
    )

    if acesso_total or in_group(request.user, 'Secretário Acadêmico, Estagiário Acadêmico Sistêmico'):
        cursos = obj.cursos.all()
        cursos_nao_convocados = CursoCampus.objects.filter(pk__in=pk_cursos_nao_convocados)
    else:
        cursos = CursoCampus.locals.sob_coordenacao_de(request.user.get_profile().funcionario)
        cursos_nao_convocados = cursos.filter(pk__in=pk_cursos_nao_convocados)
        cursos = cursos.exclude(pk__in=pk_cursos_nao_convocados)

    tabela = []
    for curso_campus in cursos.order_by('diretoria__setor__uo'):
        total_ingressantes = obj.registroconvocacaoenade_set.filter(aluno__curso_campus=curso_campus, tipo_convocacao=RegistroConvocacaoENADE.TIPO_CONVOCACAO_INGRESSANTE).count()
        total_concluintes = obj.registroconvocacaoenade_set.filter(aluno__curso_campus=curso_campus, tipo_convocacao=RegistroConvocacaoENADE.TIPO_CONVOCACAO_CONCLUINTE).count()
        total_alunos = total_ingressantes + total_concluintes
        tabela.append(dict(curso_campus=curso_campus, total_ingressantes=total_ingressantes, total_concluintes=total_concluintes, total_alunos=total_alunos))

    tabela_nao_convocados = []
    for curso_campus in cursos_nao_convocados.order_by('diretoria__setor__uo'):
        total_ingressantes = obj.registroconvocacaoenade_set.filter(aluno__curso_campus=curso_campus, tipo_convocacao=RegistroConvocacaoENADE.TIPO_CONVOCACAO_INGRESSANTE).count()
        total_concluintes = obj.registroconvocacaoenade_set.filter(aluno__curso_campus=curso_campus, tipo_convocacao=RegistroConvocacaoENADE.TIPO_CONVOCACAO_CONCLUINTE).count()
        total_alunos = total_ingressantes + total_concluintes
        tabela_nao_convocados.append(dict(curso_campus=curso_campus, total_ingressantes=total_ingressantes, total_concluintes=total_concluintes, total_alunos=total_alunos))

    if 'xls' in request.GET:
        lista_convocados = obj.registroconvocacaoenade_set.all()
        curso_id = request.GET.get('curso')
        if curso_id:
            lista_convocados = lista_convocados.filter(aluno__curso_campus__id=curso_id)
        rows = [
            [
                '#',
                'Tipo',
                'Matrícula',
                'Curso',
                'CPF',
                'Nome',
                'Data de Nascimento',
                'Sexo',
                'RG',
                'Telefone',
                'CEP',
                'UF',
                'Município',
                'Logradouro',
                'Número',
                'Complemento',
                'Bairro',
                'Ano de Conclusão do Ensino Médio',
                'Turno',
                '% CH Cumprido',
            ]
        ]
        count = 0
        for convocacao in lista_convocados.order_by('aluno__curso_campus', 'tipo_convocacao', 'aluno__pessoa_fisica__nome'):
            if convocacao.tipo_convocacao == 1:
                tipo_convocacao = 'Ingressante'
            else:
                tipo_convocacao = 'Concluinte'

            count += 1
            row = [
                count,
                format_(tipo_convocacao),
                format_(convocacao.aluno.matricula),
                format_(convocacao.aluno.curso_campus),
                format_(convocacao.aluno.pessoa_fisica.cpf),
                format_(convocacao.aluno.get_nome_social_composto()),
                format_(convocacao.aluno.pessoa_fisica.nascimento_data),
                format_(convocacao.aluno.pessoa_fisica.sexo),
                format_(convocacao.aluno.pessoa_fisica.rg),
                f'{format_(convocacao.aluno.telefone_principal)}, {format_(convocacao.aluno.telefone_secundario)}',
                format_(convocacao.aluno.cep),
                format_(convocacao.aluno.cidade and convocacao.aluno.cidade.estado or None),
                format_(convocacao.aluno.cidade),
                format_(convocacao.aluno.logradouro),
                format_(convocacao.aluno.numero),
                format_(convocacao.aluno.complemento),
                format_(convocacao.aluno.bairro),
                format_(convocacao.aluno.ano_conclusao_estudo_anterior),
                format_(convocacao.aluno.turno),
                format_(convocacao.percentual_ch_cumprida),
            ]
            rows.append(row)
        return XlsResponse(rows)
    return locals()


@rtr()
@permission_required('edu.change_convocacaoenade')
def atualizar_lista_convocados_enade(request, pk):
    obj = get_object_or_404(ConvocacaoENADE, pk=pk)
    title = 'Atualizar Lista de Convocados do ENADE'
    form = AtualizarListaConvocadosENADEForm(data=request.GET or None, convocao_enade=obj)

    if form.is_valid():
        return form.processar(request)

    return locals()


@rtr()
@permission_required('edu.change_registroconvocacaoenade')
def lancar_situacao_enade(request, pks):
    title = 'Convocação para o ENADE'

    if not "_" in pks:
        obj = get_object_or_404(RegistroConvocacaoENADE, pk=pks)
        form = LancarSituacaoAlunoENADEForm(data=request.POST or None, instance=obj)

        if form.is_valid():
            obj = form.save()

            if obj.situacao != RegistroConvocacaoENADE.SITUACAO_DISPENSADO and obj.justificativa_dispensa:
                obj.justificativa_dispensa = None
                obj.save()

            return httprr(f'/edu/aluno/{obj.aluno.matricula}/?tab=convocacoes_enade', 'Lançamento do ENADE realizado com sucesso.')
    else:
        registros_convocacoes_enade = RegistroConvocacaoENADE.objects.filter(pk__in=pks.split('_'))
        form = LancarSituacaoAlunoEmLoteENADEForm(data=request.POST or None, registros_convocacoes_enade=registros_convocacoes_enade)

        if form.is_valid():
            form.processar()
            return httprr('..', 'Lançamentos do ENADE realizados com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_registroconvocacaoenade')
def remover_situacao_enade(request, pk):
    obj = get_object_or_404(RegistroConvocacaoENADE, pk=pk)
    obj.remover_situacao()
    return httprr(f'/edu/aluno/{obj.aluno.matricula}/?tab=convocacoes_enade', 'Situação do ENADE removida com sucesso.')


@rtr('logs_ppe.html')
@permission_required('edu.view_convocacaoenade')
def log_situacao_enade(request, pk):
    title = 'Registro de Convocação ENADE'
    logs = Log.objects.filter(ref=pk, modelo='RegistroConvocacaoENADE')
    return locals()


@rtr('logs_ppe.html')
@permission_required('edu.view_alunoarquivo')
def log_pasta_documental(request, pk):
    title = 'Alterações na Pasta Documental'
    logs = Log.objects.filter(ref_aluno=pk, modelo='AlunoArquivo').order_by('-pk')
    return locals()


@rtr()
@permission_required('edu.view_convocacaoenade')
def convocados_enade(request, pk, curso_campus_pk):
    title = 'Lista de Convocados'
    obj = get_object_or_404(ConvocacaoENADE, pk=pk)
    curso_campus = get_object_or_404(CursoCampus, pk=curso_campus_pk)
    acesso_total = perms.pode_realizar_procedimentos_enade(request.user, curso_campus)
    lista_convocados = obj.registroconvocacaoenade_set.filter(aluno__curso_campus__id=curso_campus_pk)
    ingressantes = lista_convocados.filter(tipo_convocacao=RegistroConvocacaoENADE.TIPO_CONVOCACAO_INGRESSANTE)
    concluintes = lista_convocados.filter(tipo_convocacao=RegistroConvocacaoENADE.TIPO_CONVOCACAO_CONCLUINTE)

    if acesso_total:
        convocacoes_selecionadas = request.POST.getlist('convocacoes_selecionadas')
        pks_convocacoes_selecionadas = '_'.join(request.POST.getlist('convocacoes_selecionadas'))

        if 'excluir' in request.POST:
            lista_convocados.filter(pk__in=convocacoes_selecionadas).delete()
            return httprr('.', 'Registros de convocação removidos com sucesso.')

        if 'xls' in request.POST:
            if convocacoes_selecionadas:
                lista_convocados = obj.registroconvocacaoenade_set.filter(pk__in=convocacoes_selecionadas)
            rows = [
                [
                    '#',
                    'Tipo',
                    'Matrícula',
                    'Curso',
                    'CPF',
                    'Nome',
                    'Data de Nascimento',
                    'Sexo',
                    'RG',
                    'Telefone',
                    'CEP',
                    'UF',
                    'Município',
                    'Logradouro',
                    'Número',
                    'Complemento',
                    'Bairro',
                    'Ano de Conclusão do Ensino Médio',
                    'Turno',
                ]
            ]
            count = 0
            for convocacao in lista_convocados.order_by('aluno__curso_campus', 'tipo_convocacao', 'aluno__pessoa_fisica__nome'):
                if convocacao.tipo_convocacao == 1:
                    tipo_convocacao = 'Ingressante'
                else:
                    tipo_convocacao = 'Concluinte'

                count += 1
                row = [
                    count,
                    format_(tipo_convocacao),
                    format_(convocacao.aluno.matricula),
                    format_(convocacao.aluno.curso_campus),
                    format_(convocacao.aluno.pessoa_fisica.cpf),
                    format_(convocacao.aluno.get_nome_social_composto()),
                    format_(convocacao.aluno.pessoa_fisica.nascimento_data),
                    format_(convocacao.aluno.pessoa_fisica.sexo),
                    format_(convocacao.aluno.pessoa_fisica.rg),
                    f'{format_(convocacao.aluno.telefone_principal)}, {format_(convocacao.aluno.telefone_secundario)}',
                    format_(convocacao.aluno.cep),
                    format_(convocacao.aluno.cidade and convocacao.aluno.cidade.estado or None),
                    format_(convocacao.aluno.cidade),
                    format_(convocacao.aluno.logradouro),
                    format_(convocacao.aluno.numero),
                    format_(convocacao.aluno.complemento),
                    format_(convocacao.aluno.bairro),
                    format_(convocacao.aluno.ano_conclusao_estudo_anterior),
                    format_(convocacao.aluno.turno),
                ]
                rows.append(row)
            return XlsResponse(rows)

    return locals()


@rtr()
@permission_required('edu.add_registroconvocacaoenade')
def adicionar_aluno_avulso_enade(request, pk, curso_campus_pk):
    title = 'Adicionar Aluno Avulso'
    convocacao = get_object_or_404(ConvocacaoENADE.objects, pk=pk)
    curso_campus = get_object_or_404(CursoCampus.objects, pk=curso_campus_pk)

    form = RegistroConvocacaoENADEForm(convocacao, curso_campus, data=request.POST or None)
    if form.is_valid():
        form.save()
        return httprr('..', 'Aluno avulso cadastrado com sucesso.')

    return locals()


@rtr()
@permission_required('edu.add_registroconvocacaoenade')
def dispensar_participacao_enade(request, matricula):
    title = 'Registrar Dipensa de Aluno da Convocação do ENADE'
    aluno = get_object_or_404(Aluno.objects, matricula=matricula)
    url_retorno = f'/edu/aluno/{aluno.matricula}/?tab=convocacoes_enade'
    if not aluno.pode_ser_dispensado_enade() and not in_group(request.user, 'Diretor de Avaliação e Regulação do Ensino'):
        return httprr(url_retorno, 'Este aluno não pode ser dispensado do ENADE.', 'error', close_popup=True)
    form = DispensaConvocacaoENADEForm(data=request.POST or None, aluno=aluno)
    if form.is_valid():
        registro = RegistroConvocacaoENADE()
        registro.aluno = aluno
        registro.situacao = RegistroConvocacaoENADE.SITUACAO_DISPENSADO
        registro.convocacao_enade = form.cleaned_data.get('convocacao_enade')
        registro.justificativa_dispensa = form.cleaned_data.get('justificativa_dispensa')
        registro.tipo_convocacao = form.cleaned_data.get('tipo_convocacao')
        registro.save()
        return httprr(url_retorno, 'Registro de dispensa do ENADE cadastrada com sucesso.', close_popup=True)

    return locals()


@documento()
@rtr()
@permission_required('edu.view_convocacaoenade')
def imprimir_lista_convocados_enade_pdf(request, pk):
    obj = get_object_or_404(ConvocacaoENADE, pk=pk)
    sigla_reitoria = get_sigla_reitoria()
    uo = UnidadeOrganizacional.objects.suap().get(sigla=sigla_reitoria)
    lista_convocados = obj.registroconvocacaoenade_set.all()
    curso_id = request.GET.get('curso')
    if curso_id:
        lista_convocados = lista_convocados.filter(aluno__curso_campus__id=curso_id)
    ingressantes = lista_convocados.filter(tipo_convocacao=RegistroConvocacaoENADE.TIPO_CONVOCACAO_INGRESSANTE)
    concluintes = lista_convocados.filter(tipo_convocacao=RegistroConvocacaoENADE.TIPO_CONVOCACAO_CONCLUINTE)
    return locals()


@permission_required('edu.add_colacaograu')
@rtr()
def adicionar_alunos_colacao_grau(request, pk):
    title = 'Adicionar Aluno a Colação de Grau'
    colacao_grau = get_object_or_404(ColacaoGrau.objects, pk=pk)
    is_administrador = in_group(request.user, 'Administrador Acadêmico') or in_group(request.user, 'Organizador de Formatura')
    hoje = datetime.datetime.now().date()
    if not is_administrador:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    form = AdicionarAlunosColacaoGrauForm(request, colacao_grau=colacao_grau, data=request.GET or None)
    if form.is_valid():
        form.processar()
        return httprr(f'/edu/colacao_grau/{pk}/', 'Alunos adicionados à colação de grau.')
    return locals()


@permission_required('edu.view_colacaograu')
@rtr()
def colacao_grau(request, pk):
    obj = get_object_or_404(ColacaoGrau.objects, pk=pk)
    title = str(obj)
    participacoes = obj.participacaocolacaograu_set.all()
    hoje = datetime.datetime.now().date()
    is_administrador = in_group(request.user, 'Administrador Acadêmico')
    cursos = CursoCampus.objects.filter(id__in=obj.participacaocolacaograu_set.values_list('aluno__curso_campus__id'))
    if 'curso_campus' in request.POST and request.POST['curso_campus'] != '0':
        participacoes = participacoes.filter(aluno__curso_campus__id=request.POST['curso_campus'])

    for curso in cursos:
        if 'curso_campus' in request.POST:
            if curso.pk == int(request.POST['curso_campus']):
                curso.selecionado = True
                break

    if 'xls' in request.GET:
        count = 0
        rows = [['#', 'Matrícula', 'Nome', 'Curso', 'I.R.A.']]

        for participacao in participacoes:
            count += 1
            row = [
                count,
                format_(participacao.aluno.matricula),
                format_(participacao.aluno.get_nome_social_composto()),
                format_(participacao.aluno.curso_campus),
                format_(participacao.aluno.get_ira()),
            ]
            rows.append(row)
        return XlsResponse(rows)

    if 'cancelar_deferimento' in request.GET and (is_administrador or request.user.is_superuser):
        obj.deferida = False
        obj.save()
        return httprr('.', 'Deferimento cancelado com sucesso.')

    if 'participacao_colacao_grau' in request.POST:
        participacoes = ParticipacaoColacaoGrau.objects.filter(id__in=request.POST.getlist('participacao_colacao_grau'))
        for p in participacoes:
            p.aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
            p.aluno.save()
            p.delete()
        return httprr('.', 'Aluno removido com sucesso.')

    alunos_aptos = (
        Aluno.objects.filter(curso_campus__diretoria=obj.diretoria)
        .filter(matriz__isnull=False, situacao=SituacaoMatricula.MATRICULADO, pendencia_colacao_grau=True)
        .exclude(pendencia_tcc=True)
        .exclude(pendencia_enade=True)
        .exclude(pendencia_ch_atividade_complementar=True)
        .exclude(pendencia_ch_tcc=True, pendencia_ch_pratica_profissional=True)
        .exclude(pendencia_ch_seminario=True)
        .exclude(pendencia_ch_eletiva=True)
        .exclude(pendencia_ch_optativa=True)
        .exclude(pendencia_ch_obrigatoria=True)
        .exclude(pendencia_pratica_profissional=True)
        .exclude(curso_campus__modalidade=Modalidade.FIC)
    )
    return locals()


@permission_required('edu.add_colacaograu')
@rtr()
def deferir_colacao_grau(request, pk):
    title = 'Deferir Colação de Grau'
    obj = get_object_or_404(ColacaoGrau.objects, pk=pk)
    form = DeferirColacaoGrauForm(obj, data=request.POST or None)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Colação de grau deferida com sucesso.')
    return locals()


@permission_required('edu.view_colacaograu')
@documento()
@rtr()
def imprimir_lista_colacao_grau_pdf(request, pk):
    obj = get_object_or_404(ColacaoGrau.objects, pk=pk)
    is_administrador = in_group(request.user, 'Administrador Acadêmico')
    participacoes = obj.participacaocolacaograu_set.all()
    hoje = datetime.datetime.now().date()
    uo = obj.diretoria.setor.uo

    return locals()


@rtr()
@login_required()
def editar_matricula_diario_resumida(request, matricula_diario_resumida_pk):
    obj = get_object_or_404(MatriculaDiarioResumida, pk=matricula_diario_resumida_pk)
    aluno = obj.matricula_periodo.aluno
    title = 'Editar Matrícula Diário Resumida'
    form = EditarMatriculaDiarioResumidaForm(data=request.POST or None, instance=obj)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)

    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if form.is_valid():
        form.save(request)
        aluno.atualizar_situacao('Reprocessamento do Histórico')
        return httprr('..', 'Matrícula Diário Resumida atualizada com sucesso.')

    return locals()


@rtr()
@login_required()
def componentes_nao_disponiveis_matricula_online(request, aluno_pk):
    aluno = get_object_or_404(Aluno.locals, pk=aluno_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos and not aluno.is_user(request):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if not aluno.pode_matricula_online():
        return httprr('/', 'Não existe um período de renovação de matrícula ativa para o seu curso.', 'error')

    if aluno.is_credito():
        title = "Disciplinas {} pendentes não disponíveis".format(request.GET.get('optativas') == '1' and "optativas" or "obrigatórias")

    turma = None
    if aluno.is_seriado() or aluno.is_modular():
        if request.GET.get('turma'):
            turma = get_object_or_404(Turma, pk=request.GET.get('turma'))
            title = f"Disciplinas da turma({turma}) não disponíveis"
        else:
            title = "Disciplinas em dependência não disponíveis"

    componentes_nao_disponiveis = aluno.componentes_nao_disponiveis_matricula_online(request.GET.get('optativas'), turma)
    return locals()


@rtr()
@permission_required('edu.add_evento')
def evento(request, pk):
    obj = get_object_or_404(Evento, pk=pk)
    title = 'Palestra/Evento'
    if 'cpfs' in request.POST:
        for participante_evento_id in request.POST.getlist('cpfs'):
            ParticipanteEvento.objects.filter(id=participante_evento_id).delete()
    return locals()


@rtr()
@permission_required('edu.add_evento')
def adicionar_modelo_certificado_evento(request, pk, tipo):
    obj = get_object_or_404(Evento, pk=pk)
    title = f'Modelo do Certificado de {tipo}'
    form = ModeloCertificadoEventoForm(obj, tipo=tipo, files=request.FILES or None, data=request.POST or None)
    if request.POST and form.is_valid():
        form.processar()
        return httprr('..', 'Modelo de certificado adicionado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.add_evento')
def adicionar_participante_evento(request, pk, tipo):
    obj = get_object_or_404(Evento, pk=pk)
    title = f'Adicionar {tipo} à Palestra/Evento'
    form = AdicionarParticipanteEventoForm(obj, tipo=tipo, data=request.POST or None)
    if request.POST and form.is_valid():
        form.processar()
        return httprr('..', f'{tipo} adicionado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.add_evento')
def editar_participante_evento(request, pk):
    obj = get_object_or_404(ParticipanteEvento, pk=pk)
    title = 'Atualizar Participante de Palestra/Evento'
    form = EditarParticipanteEventoForm(data=request.POST or None, instance=obj.participante)
    if request.POST and form.is_valid():
        form.save()
        return httprr('..', 'Participante atualizado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.add_evento')
def alterar_vinculo_participante_evento(request, pk):
    obj = get_object_or_404(ParticipanteEvento, pk=pk)
    title = 'Alterar Vínculo do Participante de Palestra/Evento'
    form = AlterarVinculoParticipanteEventoForm(data=request.POST or None, instance=obj)
    if request.POST and form.is_valid():
        form.save()
        return httprr('..', 'Participante atualizado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.add_evento')
def importar_participantes_evento(request, pk, tipo):
    obj = get_object_or_404(Evento, pk=pk)
    title = f'Importar {tipo}s para Palestra/Evento'

    if request.method == 'POST':
        form = ImportarParticipantesEventoForm(obj, data=request.POST or None, files=request.FILES or None, tipo=tipo)
        if form.is_valid():
            form.processar()
            return httprr(f'/edu/evento/{pk}/', f'{tipo}s adicionados com sucesso.')
    else:
        form = ImportarParticipantesEventoForm(obj, tipo=tipo)
    return locals()


@login_required()
def imprimir_certificado_participacao_evento(request, pk):
    participanteEvento = get_object_or_404(ParticipanteEvento, pk=pk)
    if request.user.has_perm('edu.add_evento') or participanteEvento.participante.cpf == request.user.get_profile().cpf:
        return imprimir_certificado(request, pk)
    return httprr('..', 'Você não tem permissão para realizar isso.', 'error')


def imprimir_certificado_participacao_evento_email(request, token):
    obj = get_object_or_404(ParticipanteEvento, token=token)
    return imprimir_certificado(request, obj.pk, True)


def imprimir_certificado(request, pk, is_anonimo=False):
    obj = get_object_or_404(ParticipanteEvento, pk=pk)
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

    qs_registro = RegistroEmissaoDocumento.objects.filter(tipo='Certificado de Participação em Evento', modelo_pk=pk)
    if qs_registro.exists():
        codigo = qs_registro[0].codigo_verificador
        hoje = qs_registro[0].data_emissao
    else:
        codigo = obj.token
        hoje = datetime.date.today()

    codigo_verificador = (
        'Este documento foi emitido pelo SUAP. Para comprovar sua autenticidade, '
        'acesse {}/comum/autenticar_documento/ - '
        'Código de autenticação: {} - Tipo de Documento: Certificado de Participação em Evento - '
        'Data da emissão: {} '.format(settings.SITE_URL, codigo[0:7], hoje.strftime('%d/%m/%Y'))
    )

    if obj.tipo_participacao == ParticipanteEvento.PALESTRANTE:
        modelo_documento = obj.evento.modelo_certificado_palestrante
    elif obj.tipo_participacao == ParticipanteEvento.CONVIDADO:
        modelo_documento = obj.evento.modelo_certificado_convidado
    else:
        modelo_documento = obj.evento.modelo_certificado_participacao

    if modelo_documento.name == '':
        return httprr(f'/edu/evento/{obj.evento.pk}/', 'Modelo do certificado não cadastrado.', 'error')

    dicionario = {
        '#PARTICIPANTE#': normalizar(obj.participante.nome),
        '#CPF#': obj.participante.cpf,
        '#CAMPUS#': normalizar(obj.evento.uo.nome),
        '#CIDADE#': normalizar(obj.evento.uo.municipio.nome),
        '#UF#': obj.evento.uo.municipio.uf,
        '#DATA#': f'{hoje.day} de {meses[hoje.month - 1]} de {hoje.year}',
        '#CODIGOVERIFICADOR#': codigo_verificador,
    }
    if qs_registro.exists():
        registro = qs_registro[0]
    else:
        caminho_arquivo = gerar_documento_impressao(dicionario, io.BytesIO(modelo_documento.read()))
        if not caminho_arquivo:
            url = '..'
            if is_anonimo:
                url = '/'
            return httprr(url, 'Documento não encontrado.', 'error')
        nome_arquivo = caminho_arquivo.split('/')[-1]

        registro = RegistroEmissaoDocumento()
        registro.tipo = 'Certificado de Participação em Evento'
        registro.codigo_verificador = codigo
        registro.data_emissao = hoje
        registro.documento.save(nome_arquivo, ContentFile(open(caminho_arquivo, "rb").read()))
        registro.data_validade = None
        registro.modelo_pk = pk
        registro.save()
        os.unlink(caminho_arquivo)

    content_type = registro.documento.name.endswith('.pdf') and 'application/pdf' or 'application/vnd.ms-word'
    response = HttpResponse(registro.documento.read(), content_type=content_type)
    extensao = content_type == 'application/pdf' and 'pdf' or 'docx'
    response['Content-Disposition'] = f'attachment; filename=Certificado.{extensao}'
    return response


@permission_required('edu.add_evento')
def enviar_certificado_participacao_evento(request, evento_pk, pks):
    obj = get_object_or_404(Evento, pk=evento_pk)
    participantes_evento = ParticipanteEvento.objects.filter(pk__in=pks.split('_'))

    emails_nao_enviados = []
    for participante_evento in participantes_evento:
        if participante_evento.participante.email:
            subject = f'CERTIFICADO DE PARTICIPAÇÃO - {obj.titulo}'
            body = """
                Caro(a) {},

                Para gerar o seu certificado de participação no "{}" clique no link abaixo:

                {}edu/imprimir_certificado_participacao_evento/{}/
            """.format(
                participante_evento.participante.nome,
                participante_evento.evento.titulo,
                Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica'),
                participante_evento.token,
            )
            to = [participante_evento.participante.email.strip(), participante_evento.participante.email_secundario.strip()]
            try:
                send_mail(
                    subject, body, settings.DEFAULT_FROM_EMAIL, to, fail_silently=False
                )
            except Exception:
                emails_nao_enviados.append(to)
    if emails_nao_enviados:
        return httprr(f'/edu/evento/{evento_pk}/', f'Os seguintes e-mails para os seguintes destinatários não puderam ser enviados: {emails_nao_enviados}', 'error')
    return httprr(f'/edu/evento/{evento_pk}/', 'Emails enviados com sucesso.')


@rtr()
@login_required()
def alunos_dados_incompletos(request):
    if not request.user.has_perm('edu.efetuar_matricula'):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    title = "Alunos concluídos com dados incompletos aptos para emissão de certificado/diploma"
    alunos_dados_incompletos_para_diploma = Aluno.get_alunos_concluidos_dados_incompletos()
    return locals()


@rtr()
@group_required('Coordenador de Curso')
def alunos_sem_turma(request, ano, periodo):
    title = f"Alunos sem Turma em {ano}.{periodo}"
    alunos = Aluno.get_alunos_sem_turma(request.user, ano, periodo)
    return locals()


@rtr("alunos_sem_turma.html")
@group_required('Coordenador de Curso')
def alunos_sem_turma_curso(request, ano, periodo, curso_id):
    title = f"Alunos sem Turma em {ano}.{periodo}"
    alunos = Aluno.get_alunos_sem_turma(request.user, ano, periodo, curso_id)
    return locals()


@rtr()
@permission_required('edu.efetuar_matricula')
def enviar_fotos_lote(request):
    title = "Atualizar Fotos de Alunos em Lote"

    if request.POST:
        form = AtualizarFotosAlunosForm(request=request, data=request.POST, files=request.FILES)
    else:
        form = AtualizarFotosAlunosForm()

    if form.is_valid():
        arquivos_problema = form.processar()
        if not arquivos_problema:
            return httprr('.', 'Fotos atualizadas com sucesso.')
    return locals()


@rtr()
def detalhar_matricula_diario_boletim(request, aluno_pk, matricula_diario_pk):
    if not request.user.is_authenticated and not 'matricula_aluno_como_resposavel' in request.session:
        raise PermissionDenied()

    aluno = get_object_or_404(Aluno, pk=aluno_pk)
    matricula_diario = get_object_or_404(MatriculaDiario, pk=matricula_diario_pk)
    diario = matricula_diario.diario
    title = f"Notas: {diario.componente_curricular.componente.descricao_historico}"

    is_pai_aluno = request.session.get('matricula_aluno_como_resposavel')
    is_proprio_aluno = aluno.is_user(request)
    if is_pai_aluno:
        pode_ver_dados_academicos = True
        pode_realizar_procedimentos = False
    else:
        pode_ver_dados_academicos = is_proprio_aluno or in_group(
            request.user,
            'Coordenador de Curso,Coordenador de Modalidade Acadêmica,Coordenador de Modalidade Acadêmica,Administrador Acadêmico,Secretário Acadêmico,Diretor Acadêmico,Estagiário,Professor',
        )
        pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)

    if not (pode_ver_dados_academicos or pode_realizar_procedimentos or request.user.has_perm('edu.view_aluno')):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    notas_avaliacoes = NotaAvaliacao.objects.filter(matricula_diario__pk=matricula_diario.pk, matricula_diario__matricula_periodo__aluno__pk=aluno.pk).order_by(
        'item_configuracao_avaliacao__configuracao_avaliacao__etapa'
    )
    qtd_avaliacoes = diario.componente_curricular.qtd_avaliacoes
    etapas = list(range(1, qtd_avaliacoes + 1))
    return locals()


@group_required('Administrador Acadêmico, Diretor Acadêmico, Coordenador de Curso, Coordenador de Modalidade Acadêmica, Secretário Acadêmico')
@rtr()
@login_required()
def exportar_xml_time_tables(request):
    title = 'Exportar XML para o TimeTables'
    form = SelecionarHorarioCampusExportarXMLTimeTables(data=request.POST or None)

    if form.is_valid():
        ano_letivo, periodo_letivo, horario_campus, diretoria = form.processar()
        pks_cursos_ativos = CursoCampus.objects.filter(diretoria=diretoria, ativo=True).values_list('pk', flat=True)

        campus_siape = UnidadeOrganizacional.objects.siape().filter(sigla=diretoria.setor.uo.sigla)
        turmas = Turma.objects.filter(curso_campus__in=pks_cursos_ativos, ano_letivo=ano_letivo, periodo_letivo=periodo_letivo).order_by('codigo')
        diarios = Diario.objects.filter(turma__in=turmas.values_list('pk', flat=True)).order_by('componente_curricular__componente__descricao')

        servidores = Servidor.objects.filter(setor_lotacao__uo__in=campus_siape)
        professores = Professor.servidores_docentes.filter(vinculo__id_relacionamento__in=Subquery(servidores.values('id')), vinculo__tipo_relacionamento__model='servidor')

        salas = Sala.ativas.filter(predio__uo=diretoria.setor.uo)

        return render(request, "exportar_xml_time_tables.xml", locals(), content_type="application/xml")

    return locals()


@group_required('Administrador Acadêmico, Diretor Acadêmico, Coordenador de Curso, Coordenador de Modalidade Acadêmica, Secretário Acadêmico')
@rtr()
@login_required()
def importar_xml_time_tables(request):
    title = 'Importar o XML do TimeTables'
    form = ImportarXMLTimeTables(data=request.POST or None, files=request.FILES or None)

    if form.is_valid():
        exception_msg = 'Erro ao processar o XML do TimeTables. Verifique se o formato do arquivo está correto e tente novamente'
        try:
            form.processar()
            return httprr('..', 'Importação realizada com sucesso!')
        except KeyError as e:
            return httprr('/edu/importar_xml_time_tables/', f'{exception_msg}. Chave {e} não encontrada.', 'error')
        except Exception as e:
            return httprr('/edu/importar_xml_time_tables/', f'{exception_msg}. Detalhe: {e}', 'error')
    return locals()


@group_required('Administrador Acadêmico, Diretor Acadêmico, Coordenador de Curso, Coordenador de Modalidade Acadêmica, Secretário Acadêmico')
@rtr()
@login_required()
def editar_abreviatura_componente(request, pk):
    title = 'Editar Abreviatura de Componente'
    obj = get_object_or_404(Componente, pk=pk)
    form = EditarAbreviaturaComponenteForm(data=request.POST or None, instance=obj)

    if form.is_valid():
        form.save()
        return httprr('..', 'Abreviatura atualizada com sucesso.')

    return locals()


@rtr()
@login_required()
def diarioespecial(request, pk):
    obj = get_object_or_404(DiarioEspecial, pk=pk)
    title = obj.componente.descricao
    is_usuario_professor = obj.professores.filter(vinculo__user=request.user).exists()
    pode_realizar_procedimentos = (
        request.user.has_perm('edu.change_diario') or request.user.has_perm('edu.change_diarioespecial')
    ) and perms.realizar_procedimentos_diarios_especiais(request.user, obj)

    ids_alunos_encontros = obj.encontro_set.values_list('participantes', flat=True).distinct()

    if 'alunos_pk' in request.POST and (is_usuario_professor or pode_realizar_procedimentos):
        for aluno_pk in request.POST.getlist('alunos_pk'):
            if int(aluno_pk) not in ids_alunos_encontros:
                aluno = Aluno.objects.get(pk=aluno_pk)
                obj.participantes.remove(aluno)
        obj.save()

    if 'del_encontro' in request.GET and (is_usuario_professor or pode_realizar_procedimentos):
        obj.encontro_set.filter(pk=request.GET['del_encontro']).delete()
        return httprr(request.META.get('HTTP_REFERER', '.'), 'Encontro removido com sucesso.')

    if 'del_professor' in request.GET and (is_usuario_professor or pode_realizar_procedimentos):
        professor = Professor.objects.get(pk=request.GET['del_professor'])
        obj.professores.remove(professor)
        obj.save()
        return httprr(request.META.get('HTTP_REFERER', '.'), 'Professor removido com sucesso.')

    return locals()


@permission_required('edu.change_diarioespecial')
@rtr()
def definir_local_aula_diario_especial(request, diario_especial_pk):
    title = 'Definir Local de Aula'
    diario_especial = get_object_or_404(DiarioEspecial, pk=diario_especial_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_diarios_especiais(request.user, diario_especial)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    sala_id = None
    if diario_especial.sala:
        sala_id = diario_especial.sala.id
    form = DefinirLocalAulaDiarioEspecialForm(diario_especial, data=request.POST or None, initial=dict(sala=sala_id))
    if form.is_valid():
        form.processar()
        return httprr('..', 'Local definido com sucesso.')
    return locals()


@login_required()
def definir_horario_aula_diario_especial_ajax(request, diario_especial_pk, horario_aula_pk, dia_semana_numero, checked):
    if checked == 'true':
        checked = True
    else:
        checked = False
    diario_especial = get_object_or_404(DiarioEspecial, pk=diario_especial_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_diarios_especiais(request.user, diario_especial)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    horario_aula = get_object_or_404(HorarioAula, pk=horario_aula_pk)
    if not checked:
        HorarioAulaDiarioEspecial.objects.filter(diario_especial=diario_especial, dia_semana=dia_semana_numero, horario_aula=horario_aula).delete()
    else:
        HorarioAulaDiarioEspecial.objects.create(diario_especial=diario_especial, dia_semana=dia_semana_numero, horario_aula=horario_aula)
    return HttpResponse('OK')


@permission_required('edu.change_diarioespecial')
@rtr()
def definir_horario_aula_diario_especial(request, diario_especial_pk):
    obj = get_object_or_404(DiarioEspecial, pk=diario_especial_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_diarios_especiais(request.user, obj)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    campus_definiu_horario = HorarioAula.objects.filter(horario_campus__uo=obj.diretoria.setor.uo).exists()

    horario_aula = obj.get_horario_aulas() or ''
    if horario_aula:
        horario_aula = f'({horario_aula})'

    title = f'Definir Horário de Aula {horario_aula}'

    if request.method == 'POST':
        return httprr('..', 'Horário definido com sucesso.')

    turnos = obj.get_horarios_aula_por_turno()
    turnos.as_form = True

    return locals()


@rtr()
def adicionar_aluno_diario_especial(request, diario_especial_pk):
    diario_especial = get_object_or_404(DiarioEspecial, pk=diario_especial_pk)
    title = 'Adicionar Alunos na Atividade Pedagógica Específica'
    form = AdicionarAlunosDiarioEspecialForm(diario_especial, data=request.POST or None)

    is_usuario_professor = diario_especial.professores.filter(vinculo__user=request.user).exists()
    pode_realizar_procedimentos = (
        request.user.has_perm('edu.change_diario') or request.user.has_perm('edu.change_diarioespecial')
    ) and perms.realizar_procedimentos_diarios_especiais(request.user, diario_especial)

    if not is_usuario_professor and not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if form.is_valid():
        form.processar()
        return httprr('..', 'Alunos adicionados com sucesso.')

    return locals()


@rtr()
def adicionar_alunos_diario_especial(request, diario_especial_pk):
    diario_especial = get_object_or_404(DiarioEspecial, pk=diario_especial_pk)
    title = 'Adicionar Alunos na Atividade Pedagógica Específica'
    data = 'diario' in request.GET and request.GET or None
    form = AdicionarAlunosDiarioEspecialWizard(request, diario_especial, data=data)

    is_usuario_professor = request.user.is_authenticated and diario_especial.professores.filter(vinculo__user=request.user).exists()
    pode_realizar_procedimentos = (
        request.user.has_perm('edu.change_diario') or request.user.has_perm('edu.change_diarioespecial')
    ) and perms.realizar_procedimentos_diarios_especiais(request.user, diario_especial)

    if not is_usuario_professor and not pode_realizar_procedimentos:
        return httprr('/', 'Você não tem permissão para realizar isso.', 'error')

    if form.is_valid():
        form.processar()
        return httprr(f'/edu/diarioespecial/{diario_especial.pk}/?tab=participantes', 'Alunos adicionados com sucesso.')

    return locals()


@permission_required('edu.change_diarioespecial')
@rtr()
def adicionar_professor_diario_especial(request, diario_especial_pk):
    diario_especial = get_object_or_404(DiarioEspecial, pk=diario_especial_pk)
    title = 'Adicionar Professor na Atividade Pedagógica Específica'
    form = AdicionarProfessorDiarioEspecialForm(diario_especial, data=request.POST or None)

    pode_realizar_procedimentos = perms.realizar_procedimentos_diarios_especiais(request.user, diario_especial)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if form.is_valid():
        form.processar()
        return httprr('..', 'Professor adicionado com sucesso.')

    return locals()


@permission_required('edu.cadastrar_encontro_diarioespecial')
@rtr()
def adicionar_encontro_diario_especial(request, diario_especial_pk):
    diario_especial = get_object_or_404(DiarioEspecial, pk=diario_especial_pk)
    title = 'Adicionar Encontro na Atividade Pedagógica Específica'
    form = AdicionarEncontroDiarioEspecialForm(diario_especial, data=request.POST or None)

    if form.is_valid():
        form.processar()
        return httprr('..', 'Encontro adicionado com sucesso.')

    return locals()


@documento()
@rtr()
def frequencia_diarioespecial(request, pk):
    obj = get_object_or_404(Encontro, pk=pk)
    uo = obj.diario_especial.diretoria.setor.uo
    return locals()


@permission_required('edu.cadastrar_encontro_diarioespecial')
@rtr()
def atualizar_encontro_diario_especial(request, pk):
    obj = get_object_or_404(Encontro, pk=pk)
    title = 'Atualizar Encontro na Atividade Pedagógica Específica'
    form = AtualizarEncontroDiarioEspecialForm(instance=obj, data=request.POST or None)

    if form.is_valid():
        form.save()
        return httprr('..', 'Encontro atualizado com sucesso.')

    return locals()


@permission_required('edu.view_modelodocumento')
@rtr()
def modelo_documento(request, pk):
    obj = get_object_or_404(ModeloDocumento, pk=pk)
    title = obj.descricao
    url_suap = settings.SITE_URL
    if 'preview' in request.GET:
        qr_code_path = tempfile.mktemp('.png')
        img = qrcode.make(url_suap)
        img.save(qr_code_path)
        dicionario = {'#CHGERAL#': '50', '#CHESPECIAL#': '10', '#CHESTAGIO#': '10', '#EMPRESAESTAGIO#': '10', '#LEI#': 'Lei 01/1900', '#NOMECAMPUS#': 'Campus Central', '#ALUNO#': 'João Maria da Silva', '#CREDENCIAMENTO#': '0001/1900', '#RECREDENCIAMENTO#': '0002/1900', '#COLACAO#': '01/01/1900', '#NACIONALIDADE#': 'Brasileira', '#NATURALIDADE#': 'Natal/RN', '#DATANASCIMENTO#': '01/01/1900', '#CPF#': '111.111.111-11', '#PASSAPORTE#': '', '#RG#': '11.111', '#UFRG#': 'RN', '#EMISSORRG#': 'ITEP', '#DATARG#': '01/01/1900', '#CURSO#': 'Informática Básica', '#HABILITACAOPEDAGOGICA#': 'Sistemas', '#AREACONCENTRACAO#': 'Tecnologia', '#PROGRAMA#': 'Programa Básico', '#INICIO#': '01/01/1900', '#FIM#': '01/01/1900', '#TITULO#': 'Técnico em Informática', '#CHTOTAL#': '50', '#CIDADE#': 'Natal', '#UF#': 'RN', '#DATA#': '01/01/1900', '#COORDENADOR#': 'Pedro da Silva', '#AREA#': 'Tecnologia', '#TITULOCOORDENADOR#': 'coordenador', '#OREITOR#': 'Mauro Silva', '#REITOR#': 'Maria de Fática', '#TITULOREITOR#': 'reitora', '#EMEXERCICIO#': '', '#DIRETORGERAL#': 'Manoel Bandeira', '#TITULODIRETORGERAL#': 'diretor geral', '#DIRETORACADEMICO#': 'Roberto Carlos', '#TITULODIRETORACADEMICO#': 'diretor acadêmico', '#DISCIPLINAS#': 'Programação', '#PROFESSORES#': 'Maria Emília', '#TITULACOES#': 'Doutora', '#NOTAS#': '100', '#CH#': '50', '#REGISTRO#': '123', '#LIVRO#': '1', '#FOLHA#': '1', '#DATAEXPEDICAO#': '01/01/1900', '#PROCESSO#': '123.456.789', '#CODIGOVERIFICADOR#': 'abcdef', '#NASCIDO#': '01/01/1900', '#PORTADOR#': '', '#DIPLOMADO#': 'João Maria da Silva', '#AUTORIZACAO#': '123456/1900', '#RECONHECIMENTO#': '123456/1900', '#DIATCC#': '01/01/1900', '#MESTCC#': 'janeiro', '#ANOTCC#': '1900', '#TIPOTCC#': 'trabalho de concluão de curso', '#TEMATCC#': 'Algorítmos na prática', '#ORIENTADOR#': 'Joaqui Barbosa', '#TITULACAOORIENTADOR#': 'Doutor', '#CHTCC#': '10', '#NOTATCC#': '100', '#VIA#': '1', '#SERVIDORREGISTROESCOLAR#': 'Juliana Mendes', '#PORTARIAREGISTROESCOLAR#': '123/1900', '#NOMEPAI#': 'Joaqui da Silva', '#NOMEMAE#': 'Ruth Oliveira da Silva', '#ANOCONCLUSAOFIC#': '1900', '#AUTENTICACAOSISTEC#': '123-456-789', '#COORDENADORREGISTROESCOLAR#': 'Flávio de Sá', '#HABILITACAO#': 'Sistemas'}
        dicionario['#URLXML#'] = url_suap
        dicionario['#CODIGOVALIDACAO#'] = 'abcdef'
        dicionario['#URLVALIDACAO#'] = url_suap
        caminho_arquivo = gerar_documento_impressao(
            dicionario, io.BytesIO(obj.template.read()),
            pdfa=True, imagem_path=qr_code_path
        )
        return PDFResponse(open(caminho_arquivo, 'rb').read())
    return locals()


@rtr()
@permission_required('edu.view_configuracaopedidomatricula')
def alunos_conflitos_horarios(request):
    title = 'Relatório de Alunos com Conflitos de Horários'
    form = AlunosConflitosHorariosForm(request.GET or None)
    if form.is_valid():
        alunos_conflitos_horarios = form.processar()
    return locals()


@rtr()
@permission_required('edu.view_configuracaopedidomatricula')
def visualizar_alunos_configuracao_pedido_matricula(request, configuracao_pedido_matricula_pk, curso_pk):
    if "situacao" in request.GET:
        configuracao_pedido_matricula = get_object_or_404(ConfiguracaoPedidoMatricula, pk=configuracao_pedido_matricula_pk)
        curso = get_object_or_404(CursoCampus, pk=curso_pk)

        situacao_alunos_configuracao = request.GET.get("situacao")
        if situacao_alunos_configuracao == "aptos":
            title = 'Alunos Aptos'
            alunos = configuracao_pedido_matricula.get_alunos_aptos(curso)
        elif situacao_alunos_configuracao == "participantes":
            title = 'Alunos Participantes'
            alunos = configuracao_pedido_matricula.get_alunos_participantes(curso)
        elif situacao_alunos_configuracao == "nao_participantes":
            title = 'Alunos Não Participantes'
            alunos = configuracao_pedido_matricula.get_alunos_aptos(curso).exclude(
                id__in=configuracao_pedido_matricula.get_alunos_participantes(curso).values_list("id", flat=True)
            )
    return locals()


@rtr()
@login_required()
def solicitar_atividade_complementar(request, pk=None):
    title = '{} Solicitação de Atividade Complementar'.format(pk and 'Editar' or 'Adicionar')
    aluno = get_object_or_404(
        Aluno,
        pessoa_fisica=request.user.get_profile(),
        curso_campus__modalidade__nivel_ensino__pk__in=[NivelEnsino.GRADUACAO, NivelEnsino.POS_GRADUACAO],
        situacao__id__in=[SituacaoMatricula.MATRICULADO, SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL],
    )

    atividade = None
    if pk:
        atividade = get_object_or_404(AtividadeComplementar.objects, pk=pk, deferida__isnull=True, aluno=aluno)

    form = AtividadeComplementarForm(request.POST or None, initial={'aluno': aluno.pk}, files=request.FILES or None, instance=atividade, as_aluno=True, request=request)

    if form.is_valid():
        form.save()
        redirect = '..'
        if not pk:
            return httprr(redirect, 'Atividade complementar adicionada com sucesso. Compareça à secretaria acadêmica para entregar fisicamente o documento.')
        else:
            return httprr(redirect, 'Atividade complementar atualizada com sucesso. Compareça à secretaria acadêmica para entregar fisicamente o documento.')
    return locals()


@rtr()
@login_required()
def solicitar_atividade_aprofundamento(request, pk=None):
    title = '{} Solicitação de Atividade Aprofundamento'.format(pk and 'Editar' or 'Adicionar')
    aluno = get_object_or_404(
        Aluno,
        pessoa_fisica=request.user.get_profile(),
        curso_campus__modalidade__nivel_ensino__pk__in=[NivelEnsino.GRADUACAO, NivelEnsino.POS_GRADUACAO],
        situacao__id__in=[SituacaoMatricula.MATRICULADO, SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL],
    )

    atividade = None
    if pk:
        atividade = get_object_or_404(AtividadeAprofundamento.objects, pk=pk, deferida__isnull=True, aluno=aluno)

    form = AtividadeAprofundamentoForm(request.POST or None, initial={'aluno': aluno.pk}, files=request.FILES or None, instance=atividade, as_aluno=True, request=request)

    if form.is_valid():
        form.save()
        redirect = '..'
        if not pk:
            return httprr(redirect, 'Atividade de Aprofundamento adicionada com sucesso. Compareça à Secretaria Acadêmica para entregar fisicamente o documento.')
        else:
            return httprr(redirect, 'Atividade de Aprofundamento atualizada com sucesso. Compareça à Secretaria Acadêmica para entregar fisicamente o documento.')
    return locals()


@rtr()
@permission_required('edu.view_minicurso')
def minicurso(request, pk):
    obj = get_object_or_404(Minicurso.locals, pk=pk)
    title = f'{obj}'
    return locals()


@rtr()
@permission_required('edu.change_minicurso')
def criar_turma_minicurso(request, pk):
    obj = get_object_or_404(Minicurso, pk=pk)
    title = f'Criar uma nova Turma para o Minicurso {obj}'

    form = TurmaMinicursoForm(obj, data=request.POST or None)

    if request.method == 'POST':
        form = TurmaMinicursoForm(obj, data=request.POST or None, files=request.FILES or None)
        if form.is_valid():
            form.processar()
            return httprr(f'/edu/minicurso/{obj.pk}', 'Turma para o Minicurso criada com sucesso.')
    else:
        form = TurmaMinicursoForm(obj)

    return locals()


@rtr()
@permission_required('edu.view_turmaminicurso')
def turma_minicurso(request, pk):
    obj = get_object_or_404(TurmaMinicurso.objects, pk=pk)
    title = f'Turma {obj}'
    hoje = datetime.date.today()
    return locals()


@rtr()
@permission_required('edu.change_minicurso')
def editar_participante_turma_minicurso(request, pk):
    obj = get_object_or_404(PessoaFisica, pk=pk)
    title = 'Atualizar Participante'
    form = EditarParticipanteTurmaMinicursoForm(data=request.POST or None, instance=obj)
    if request.POST and form.is_valid():
        form.save()
        return httprr('..', 'Participante atualizado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_minicurso')
def editar_professor_minicurso(request, turma_minicurso_pk, professor_minicurso_pk=None):
    turma_minicurso = get_object_or_404(TurmaMinicurso, pk=turma_minicurso_pk)
    title = f'Adicionar Professor a turma: {turma_minicurso}'
    professor_minicurso = None
    if professor_minicurso_pk:
        professor_minicurso = get_object_or_404(ProfessorMinicurso, pk=professor_minicurso_pk)
        title = 'Editar Professor'
    form = ProfessorMinicursoForm(
        data=request.POST or None, instance=professor_minicurso_pk and professor_minicurso or ProfessorMinicurso(turma_minicurso=turma_minicurso), request=request
    )
    if request.POST and form.is_valid():
        form.save()
        return httprr('..', 'Professor atualizado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_minicurso')
def editar_monitor_minicurso(request, turma_minicurso_pk, monitor_minicurso_pk=None):
    turma_minicurso = get_object_or_404(TurmaMinicurso, pk=turma_minicurso_pk)
    title = f'Adicionar Monitor a turma: {turma_minicurso}'
    monitor_minicurso = None
    if monitor_minicurso_pk:
        monitor_minicurso = get_object_or_404(MonitorMinicurso, pk=monitor_minicurso_pk)
        title = 'Editar Monitor'
    form = MonitorMinicursoForm(
        data=request.POST or None, instance=monitor_minicurso_pk and monitor_minicurso or MonitorMinicurso(turma_minicurso=turma_minicurso), request=request
    )
    if request.POST and form.is_valid():
        form.save()
        return httprr('..', 'Monitor atualizado com sucesso.')
    return locals()


@rtr()
def autenticar_certificado_minicurso(request):
    title = 'Autenticação de Certificados de Minicurso'
    form = AutenticarCertificadoMinicursoForm(data=request.GET or None)
    if form.is_valid():
        obj, turma = form.processar()
        if not obj:
            return httprr('..', 'Aluno não encontrado.', 'error')
        turma_minicurso = obj.turmaminicurso_set.all()[0]
        meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

        if request.GET.get('com_timbre') == '1':
            modelo_documento = ModeloDocumento.objects.get(descricao='Certificado MINICURSO [Papel Timbrado]', ativo=True).template
        else:
            modelo_documento = ModeloDocumento.objects.get(descricao='Certificado MINICURSO', ativo=True).template
        inicio = turma_minicurso.data_inicio
        inicio = f'{str(inicio.day).zfill(2)}/{str(inicio.month).zfill(2)}/{inicio.year}'
        fim = turma_minicurso.data_fim
        fim = f'{str(fim.day).zfill(2)}/{str(fim.month).zfill(2)}/{fim.year}'
        url_suap = settings.SITE_URL

        dicionario = {
            '#PARTICIPANTE#': normalizar(obj.pessoa_fisica.nome),
            '#CURSO#': turma_minicurso.minicurso.descricao_historico,
            '#INICIO#': inicio,
            '#FIM#': fim,
            '#CHTOTAL#': turma_minicurso.minicurso.ch_total,
            '#CPF#': obj.pessoa_fisica.cpf,
            '#NOMECAMPUS#': normalizar(turma_minicurso.minicurso.diretoria.setor.uo.nome),
            '#CIDADE#': normalizar(turma_minicurso.minicurso.diretoria.setor.uo.municipio.nome),
            '#UF#': turma_minicurso.minicurso.diretoria.setor.uo.municipio.uf,
            '#CODIGOVERIFICADOR#': 'Este documento foi emitido pelo SUAP.\nPara comprovar sua autenticidade, entre com os dados:\nCPF: {} \nData da conclusão: {}\nCódigo da turma: {}\nNa página {}/edu/autenticar_certificado_minicurso/  '.format(
                obj.pessoa_fisica.cpf, fim, str(turma.pk).zfill(5), url_suap
            ),
        }
        caminho_arquivo = gerar_documento_impressao(dicionario, io.BytesIO(modelo_documento.read()))
        if not caminho_arquivo:
            return httprr('.', 'Documento não encontrado.', 'error')
        nome_arquivo = caminho_arquivo.split('/')[-1]
        arquivo = open(caminho_arquivo, "rb")

        content_type = caminho_arquivo.endswith('.pdf') and 'application/pdf' or 'application/vnd.ms-word'
        response = HttpResponse(arquivo.read(), content_type=content_type)
        response['Content-Disposition'] = f'attachment; filename={nome_arquivo}'
        arquivo.close()
        os.unlink(caminho_arquivo)

        return response
    return locals()


@permission_required('edu.change_turmaminicurso')
def enviar_certificado_participacao_minicurso(request, turma_minicurso_pk, pks):
    obj = get_object_or_404(TurmaMinicurso, pk=turma_minicurso_pk)
    if obj.data_fim >= datetime.date.today():
        return httprr('..', 'Essa turma de minicurso não se encontra concluída.', 'error')
    alunos = Aluno.objects.filter(pk__in=pks.split('_'))

    for aluno in alunos:
        subject = f'CERTIFICADO DE PARTICIPAÇÃO - {obj.minicurso.descricao}'
        body = """
            Caro(a) {},

            Para gerar o seu certificado de participação no curso "{}" clique no link abaixo:

            {}edu/autenticar_certificado_minicurso/?cpf={}&data_conclusao={}&codigo_turma={}
        """.format(
            aluno.get_nome(),
            obj.minicurso,
            Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica'),
            aluno.pessoa_fisica.cpf,
            format_(obj.data_fim),
            turma_minicurso_pk,
        )
        from_email = settings.DEFAULT_FROM_EMAIL
        to = [aluno.pessoa_fisica.email]
        send_mail(subject, body, from_email, to)
    return httprr(request.META.get('HTTP_REFERER'), 'Email(s) enviado(s) com sucesso.')


@rtr()
@permission_required('edu.change_turmaminicurso')
def adicionar_participante_turma_minicurso(request, pk):
    obj = get_object_or_404(TurmaMinicurso, pk=pk)
    title = 'Adicionar participante'
    form = AdicionarParticipanteTurmaMinicursoForm(obj, data=request.POST or None)
    if request.POST and form.is_valid():
        form.processar()
        return httprr('..', 'Participante adicionado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_turmaminicurso')
def aprovar_aluno_turma_minicurso(request, pks):
    pks = pks.split('_')
    alunos = Aluno.objects.filter(pk__in=pks)
    if alunos.exists():
        turma_minicurso = alunos[0].turmaminicurso_set.all()[0]
        if turma_minicurso.data_fim >= datetime.date.today():
            return httprr('..', f'Só será possível aprovar alunos desta turma a partir do dia {format_(turma_minicurso.data_fim)}, dia de fim desta turma.', 'error')
        turma_minicurso.aprovar(alunos)
        return httprr(f'/edu/turma_minicurso/{turma_minicurso.pk}', 'Alunos aprovados com sucesso.')
    return httprr('..', 'Nenhum aluno selecionado.', 'error')


@rtr()
@permission_required('edu.change_turmaminicurso')
def reprovar_aluno_turma_minicurso(request, pks):
    pks = pks.split('_')
    alunos = Aluno.objects.filter(pk__in=pks)
    if alunos.exists():
        turma_minicurso = alunos[0].turmaminicurso_set.all()[0]
        if turma_minicurso.data_fim >= datetime.date.today():
            return httprr('..', f'Só será possível reprovar alunos desta turma a partir do dia {format_(turma_minicurso.data_fim)}, dia de fim desta turma.', 'error')
        turma_minicurso.reprovar(alunos)
        return httprr(f'/edu/turma_minicurso/{turma_minicurso.pk}', 'Alunos reprovados com sucesso.')
    return httprr('..', 'Nenhum aluno selecionado.', 'error')


@rtr()
@permission_required('edu.change_turmaminicurso')
def importar_participantes_turma_minicurso(request, pk):
    obj = get_object_or_404(TurmaMinicurso, pk=pk)
    title = f'Importar participantes para Turma do Minicurso {obj.minicurso}'

    if request.method == 'POST':
        form = ImportarParticipantesTurmaMinicursoForm(obj, data=request.POST or None, files=request.FILES or None)
        if form.is_valid():
            form.processar()
            return httprr(f'/edu/turma_minicurso/{pk}/', 'Participantes adicionados com sucesso.')
    else:
        form = ImportarParticipantesTurmaMinicursoForm(obj)
    return locals()


@rtr()
@group_required('Professor')
def ver_alunos_turma_minicurso(request, pk):
    obj = get_object_or_404(TurmaMinicurso, pk=pk)
    title = f'Alunos Participantes da Turma {obj}'
    return locals()


@rtr()
@permission_required('edu.add_matriz')
def relatorio_migracao(request, acao=None, curso_campus_id=None):
    ano = int(Configuracao.get_valor_por_chave('edu', 'ano_letivo_atual') or datetime.date.today().year)
    periodo_letivo = int(Configuracao.get_valor_por_chave('edu', 'periodo_letivo_atual') or 1)
    ano_letivo = Ano.objects.get(ano=ano)

    qs = MatriculaPeriodo.objects.filter(
        aluno__situacao__in=[SituacaoMatricula.MATRICULADO, SituacaoMatricula.TRANCADO, SituacaoMatricula.INTERCAMBIO, SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL]
    )
    qs = qs.filter(aluno__codigo_academico__isnull=False)
    qs = qs.filter(aluno__matriz__estrutura__isnull=True) | qs.filter(aluno__matriz__estrutura__proitec=False)

    if acao in ['migrados', 'pendentes', 'pendencias', 'pendencias_excel']:
        qs = qs.filter(aluno__curso_campus=curso_campus_id)
        form = RelatorioMigracaoForm(data=request.GET)
        if form.is_valid():
            qs = form.filtrar(qs)
        form = None

    if acao == 'migrados':
        title = 'Alunos Migrados'
        qs_matriculas_periodo = qs.filter(aluno__curso_campus=curso_campus_id, aluno__matriz__isnull=False)
        return locals()
    elif acao == 'pendentes':
        title = 'Alunos Não-Migrados'
        qs_matriculas_periodo = qs.filter(aluno__curso_campus=curso_campus_id, aluno__matriz__isnull=True)
        return locals()
    elif acao == 'pendencias' or acao == 'pendencias_excel':
        title = 'Pendências do Q-Acadêmico'
        curso_campus = CursoCampus.objects.filter(pk=curso_campus_id)
        qs = qs.filter(aluno__curso_campus=curso_campus_id, aluno__matriz__isnull=True)
        dao = DAO()
        matriculas = []
        matriculas_aptos = []
        for matricula in qs.values_list('aluno__matricula', flat=True):
            matriculas_aptos.append(matricula)
            matriculas.append(matricula)

        ano_letivo = Ano.objects.get(pk=request.GET['ano_letivo'])
        periodo_letivo = int(request.GET['periodo_letivo'])
        ignorar_ultimo_periodo = 'ignorar_ultimo_periodo' in request.GET
        erros = dao.importar_historico_resumo(matriculas, 199, ano_letivo, periodo_letivo, validacao=True, ignorar_ultimo_periodo=ignorar_ultimo_periodo)

        for aluno, mensagens in erros:
            matriculas_aptos.remove(aluno.matricula)

        alunos_aptos = Aluno.objects.filter(matriz__isnull=True, matricula__in=matriculas_aptos)

        if acao == 'pendencias_excel':
            rows = [['#', 'Matrícula', 'Nome', 'Pendência']]
            count = 0
            for aluno, mensagens in erros:
                for mensagem in mensagens:
                    count += 1
                    row = [count, aluno.matricula, aluno.get_nome_social_composto(), mensagem.replace('<i>', '').replace('</i>', '')]
                    rows.append(row)
            rows.append(['', '', '', ''])
            for aluno in alunos_aptos:
                count += 1
                row = [count, aluno.matricula, aluno.get_nome_social_composto(), 'NENHUMA']
                rows.append(row)
            return XlsResponse(rows, name=f'{aluno.curso_campus.diretoria.setor.uo.sigla}-{aluno.curso_campus.codigo}')

        return locals()

    title = 'Relatório de Migração'
    form = RelatorioMigracaoForm(data=request.GET or None, initial=dict(ano_letivo=ano_letivo.pk, periodo_letivo=periodo_letivo))
    if form.is_valid():
        qs = form.filtrar(qs)
        resumo = []
        for curso_campus_id, codigo_curso_campus, descricao_curso_campus in (
            qs.order_by('aluno__curso_campus').values_list('aluno__curso_campus__id', 'aluno__curso_campus__codigo', 'aluno__curso_campus__descricao').distinct()
        ):
            qs_curso_campus = qs.filter(aluno__curso_campus=curso_campus_id)
            total = qs_curso_campus.count()
            migrados = qs_curso_campus.filter(aluno__matriz__isnull=False).count()
            pendentes = total - migrados
            percentual = total and int(migrados * 100 / total) or 0
            item = dict(
                id=curso_campus_id, codigo=codigo_curso_campus, descricao=descricao_curso_campus, total=total, migrados=migrados, pendentes=pendentes, percentual=percentual
            )
            resumo.append(item)
    return locals()


@rtr()
@login_required()
def lancar_credito_especial(request, aluno_pk, pk_ce=None):
    obj = get_object_or_404(Aluno.locals, pk=aluno_pk)
    title = 'Lançamento de Crédito Especial'
    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, obj.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    instance = None
    if pk_ce:
        instance = CreditoEspecial.objects.get(pk=pk_ce)
        title = f'Editar Lançamento de Crédito Especial - {instance}'
    form = CreditoEspecialForm(obj, data=request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        return httprr('..', 'Crédito Especial lançado com sucesso.')
    return locals()


@rtr()
@login_required()
@permission_required('ponto.pode_ver_frequencia_propria')
def relatorio_disciplinas_aluno(request, pk, tipo):
    obj = get_object_or_404(Aluno.locals, pk=pk)
    if tipo == 'pendente':
        componentes = obj.get_componentes_obrigatorios_pendentes(True)
        title = f'Relatório de Disciplinas Pendentes {obj}'
    else:
        if request.GET.get('ano_letivo'):
            obj.ano_letivo_referencia = request.GET.get('ano_letivo')
        if request.GET.get('periodo_letivo'):
            obj.periodo_letivo_referencia = request.GET.get('periodo_letivo', None)
        matriculas_diario = obj.get_matriculas_diario_cursando()
        title = f'Relatório de Disciplinas Cursando {obj}'
    return locals()


@rtr()
@login_required()
def grafico_etapa(request, diario_pk, etapa=0):
    etapa = int(etapa)
    if etapa > 5 or etapa < 1:
        return httprr('/edu/meus_diarios/', 'Escolha uma Etapa Válida', 'error')
    descricao_etapa = etapa <= 4 and 'Etapa {}'.format(etapa or 'Etapa Final')
    obj = get_object_or_404(Diario.locals, pk=diario_pk)
    title = f'Notas dos Alunos na {descricao_etapa}'
    media_etapa = obj.get_media_notas_by_etapa(etapa)
    alunos = []
    i = 1
    dicionario = {f'nota_{etapa}__isnull': False}
    for matricula_diario in obj.matriculadiario_set.filter(**dicionario).order_by('matricula_periodo__aluno__pessoa_fisica__nome'):
        alunos.append({'index': i, 'nome': matricula_diario.matricula_periodo.aluno, 'nota': getattr(matricula_diario, f'nota_{etapa}')})
        i += 1
    return locals()


@rtr()
@login_required()
def turma_estatistica(request, turma_pk):
    turma = get_object_or_404(Turma, pk=turma_pk)
    title = f'Estatística da Turma {turma.codigo}'
    media = turma.matriz.estrutura.media_aprovacao_sem_prova_final
    # plano de retomada de aulas em virtude da pandemia (COVID19)
    media_final = turma.pertence_ao_plano_retomada and 50 or turma.matriz.estrutura.media_aprovacao_avaliacao_final
    etapa_acima = {1: [], 2: [], 3: [], 4: [], 5: []}
    etapa_abaixo = {1: [], 2: [], 3: [], 4: [], 5: []}
    etapa_media_acima = {1: [], 2: [], 3: [], 4: [], 5: []}
    etapa_media_abaixo = {1: [], 2: [], 3: [], 4: [], 5: []}

    media_turma = {1: [], 2: [], 3: [], 4: [], 5: []}

    form = EstatisticaTurmaForm(data=request.POST or None)
    form.fields['diarios'].queryset = turma.diario_set.all()
    if form.is_valid():
        etapas = form.cleaned_data['etapas']
        diarios = form.cleaned_data['diarios']
        abreviar = form.cleaned_data['abreviar']
        for diario in diarios:
            matriculas_diarios = diario.matriculadiario_set.all()
            diario.total_alunos = matriculas_diarios.count()
            diario.media = OrderedDict()

            if not diario.is_semestral_segundo_semestre():
                diario.media['N1'] = []
                diario.media['N2'] = []
            if diario.is_semestral_segundo_semestre() or not diario.is_semestral():
                diario.media['N3'] = []
                diario.media['N4'] = []
            diario.media['NAF'] = []

            if diario.is_semestral_segundo_semestre():
                # acima da média
                diario.media['N3'].append(matriculas_diarios.filter(nota_1__gte=media).count())
                diario.media['N4'].append(matriculas_diarios.filter(nota_2__gte=media).count())

                # abaixo da média
                diario.media['N3'].append(matriculas_diarios.filter(nota_1__lt=media).count())
                diario.media['N4'].append(matriculas_diarios.filter(nota_2__lt=media).count())
            else:
                # acima da média
                diario.media['N1'].append(matriculas_diarios.filter(nota_1__gte=media).count())
                diario.media['N2'].append(matriculas_diarios.filter(nota_2__gte=media).count())
                if not diario.is_semestral():
                    diario.media['N3'].append(matriculas_diarios.filter(nota_3__gte=media).count())
                    diario.media['N4'].append(matriculas_diarios.filter(nota_4__gte=media).count())

                # abaixo da média
                diario.media['N1'].append(matriculas_diarios.filter(nota_1__lt=media).count())
                diario.media['N2'].append(matriculas_diarios.filter(nota_2__lt=media).count())
                if not diario.is_semestral():
                    diario.media['N3'].append(matriculas_diarios.filter(nota_3__lt=media).count())
                    diario.media['N4'].append(matriculas_diarios.filter(nota_4__lt=media).count())

            diario.media['NAF'].append(matriculas_diarios.filter(nota_final__gte=media_final).count())
            diario.media['NAF'].append(matriculas_diarios.filter(nota_final__lt=media_final).count())

            if diario.is_semestral_segundo_semestre():
                notas_1 = {'media': None, 'minima': None, 'maxima': None}
                notas_2 = {'media': None, 'minima': None, 'maxima': None}
                notas_3 = matriculas_diarios.filter(nota_1__isnull=False).aggregate(media=Avg('nota_1'), minima=Min('nota_1'), maxima=Max('nota_1'))
                notas_4 = matriculas_diarios.filter(nota_2__isnull=False).aggregate(media=Avg('nota_2'), minima=Min('nota_2'), maxima=Max('nota_2'))
            else:
                notas_1 = matriculas_diarios.filter(nota_1__isnull=False).aggregate(media=Avg('nota_1'), minima=Min('nota_1'), maxima=Max('nota_1'))
                notas_2 = matriculas_diarios.filter(nota_2__isnull=False).aggregate(media=Avg('nota_2'), minima=Min('nota_2'), maxima=Max('nota_2'))
                if not diario.is_semestral():
                    notas_3 = matriculas_diarios.filter(nota_3__isnull=False).aggregate(media=Avg('nota_3'), minima=Min('nota_3'), maxima=Max('nota_3'))
                    notas_4 = matriculas_diarios.filter(nota_4__isnull=False).aggregate(media=Avg('nota_4'), minima=Min('nota_4'), maxima=Max('nota_4'))
                else:
                    notas_3 = {'media': None, 'minima': None, 'maxima': None}
                    notas_4 = {'media': None, 'minima': None, 'maxima': None}
            notas_final = matriculas_diarios.filter(nota_final__isnull=False).aggregate(media=Avg('nota_final'), minima=Min('nota_final'), maxima=Max('nota_final'))

            # notas
            if not diario.is_semestral_segundo_semestre():
                diario.media['N1'].append(notas_1)
                diario.media['N2'].append(notas_2)
            if diario.is_semestral_segundo_semestre() or not diario.is_semestral():
                diario.media['N3'].append(notas_3)
                diario.media['N4'].append(notas_4)
            diario.media['NAF'].append(notas_final)

            # arredondando
            for notas in (notas_1, notas_2, notas_3, notas_4):
                if notas['media']:
                    notas['media'] = round(notas['media'])
            if notas_final['media']:
                notas_final['media'] = round(notas_final['media'])

            # dados do gráfico de alunos acima e abaixo
            for i in range(4):
                if 'N' + str(i + 1) in diario.media:
                    etapa_acima[i + 1].append(diario.media['N' + str(i + 1)][0])
                    etapa_abaixo[i + 1].append(diario.media['N' + str(i + 1)][1])
                else:
                    etapa_acima[i + 1].append(0)
                    etapa_abaixo[i + 1].append(0)
            etapa_acima[5].append(diario.media['NAF'][0])
            etapa_abaixo[5].append(diario.media['NAF'][1])

            # dados do gráfico de média
            etapa_media_acima[1].append(notas_1['media'] or 0)
            etapa_media_abaixo[1].append(notas_1['media'] and 100 - notas_1['media'] or 0)
            etapa_media_acima[2].append(notas_2['media'] or 0)
            etapa_media_abaixo[2].append(notas_2['media'] and 100 - notas_2['media'] or 0)
            etapa_media_acima[3].append(notas_3['media'] or 0)
            etapa_media_abaixo[3].append(notas_3['media'] and 100 - notas_3['media'] or 0)
            etapa_media_acima[4].append(notas_4['media'] or 0)
            etapa_media_abaixo[4].append(notas_4['media'] and 100 - notas_4['media'] or 0)
            etapa_media_acima[5].append(notas_final['media'] or 0)
            etapa_media_abaixo[5].append(notas_final['media'] and 100 - notas_final['media'] or 0)

            temp = []
            temp.append(notas_1['media'] or 0)
            if not diario.is_semestral_segundo_semestre():
                temp.append(matriculas_diarios.filter(nota_1__gte=notas_1['media'] or 0).count())
                temp.append(matriculas_diarios.filter(nota_1__lt=notas_1['media'] or 0).count())
            else:
                temp.append(0)
                temp.append(0)
            media_turma[1].append(temp)

            temp = []
            temp.append(notas_2['media'] or 0)
            if not diario.is_semestral_segundo_semestre():
                temp.append(matriculas_diarios.filter(nota_2__gte=notas_2['media'] or 0).count())
                temp.append(matriculas_diarios.filter(nota_2__lt=notas_2['media'] or 0).count())
            else:
                temp.append(0)
                temp.append(0)
            media_turma[2].append(temp)

            temp = []
            temp.append(notas_3['media'] or 0)
            if diario.is_semestral_segundo_semestre():
                temp.append(matriculas_diarios.filter(nota_1__gte=notas_3['media'] or 0).count())
                temp.append(matriculas_diarios.filter(nota_1__lt=notas_3['media'] or 0).count())
            else:
                temp.append(matriculas_diarios.filter(nota_3__gte=notas_3['media'] or 0).count())
                temp.append(matriculas_diarios.filter(nota_3__lt=notas_3['media'] or 0).count())
            media_turma[3].append(temp)

            temp = []
            temp.append(notas_4['media'] or 0)
            if diario.is_semestral_segundo_semestre():
                temp.append(matriculas_diarios.filter(nota_2__gte=notas_4['media'] or 0).count())
                temp.append(matriculas_diarios.filter(nota_2__lt=notas_4['media'] or 0).count())
            else:
                temp.append(matriculas_diarios.filter(nota_4__gte=notas_4['media'] or 0).count())
                temp.append(matriculas_diarios.filter(nota_4__lt=notas_4['media'] or 0).count())
            media_turma[4].append(temp)

            temp = []
            temp.append(notas_final['media'] or 0)
            temp.append(matriculas_diarios.filter(nota_final__gte=notas_final['media'] or 0).count())
            temp.append(matriculas_diarios.filter(nota_final__lt=notas_final['media'] or 0).count())
            media_turma[5].append(temp)

        for dicionario in (etapa_acima, etapa_abaixo, etapa_media_acima, etapa_media_abaixo, media_turma):
            chaves = list(dicionario.keys())
            for chave in chaves:
                if str(chave) not in etapas:
                    dicionario.pop(chave, None)
        if 'to_xls' in request.GET:
            rows = [['#', 'Código', 'Componente', 'Etapa', 'Qtd. Alunos', 'Acima da Média', 'Abaixo da Média', 'Nota Mínima', 'Nota Média', 'Nota Máxima']]
            count = 0
            for diario in diarios:
                if hasattr(diario, 'media'):
                    etapa = 1
                    for key in diario.media:
                        if etapa <= diario.componente_curricular.qtd_avaliacoes or key == 'NAF':
                            count += 1
                            row = [
                                count,
                                format_(diario.pk),
                                format_(f'{diario.componente_curricular.componente}{diario.get_descricao_dinamica()}'),
                                format_(key),
                                format_(diario.matriculadiario_set.count()),
                                format_(diario.media[key][0]),
                                format_(diario.media[key][1]),
                                format_(diario.media[key][2]['minima']),
                                format_(diario.media[key][2]['media']),
                                format_(diario.media[key][2]['maxima']),
                            ]
                            rows.append(row)
                            etapa += 1
            return XlsResponse(rows)

    return locals()


@rtr("grafico_etapa.html")
@login_required()
def grafico_mfd(request, diario_pk):
    obj = get_object_or_404(Diario.locals, pk=diario_pk)
    title = 'MFD dos Alunos'
    valores = []
    alunos = []
    i = 1
    for matricula_diario in obj.matriculadiario_set.all().order_by('matricula_periodo__aluno__pessoa_fisica__nome'):
        mfd = matricula_diario.get_media_final_disciplina()
        if mfd is not None:
            valores.append(mfd)
            alunos.append({'index': i, 'nome': matricula_diario.matricula_periodo.aluno, 'nota': mfd})
        i += 1
    media_etapa = len(valores) and sum(valores) / len(valores) or 0
    return locals()


@rtr()
@permission_required('edu.view_configuracaocreditosespeciais')
def configuracaocreditosespeciais(request, pk):
    obj = get_object_or_404(ConfiguracaoCreditosEspeciais, pk=pk)
    title = 'Configuração de Créditos Especiais'
    if 'desvincular_matriz' in request.GET and request.user.has_perm('edu.change_configuracaocreditosespeciais'):
        matriz = Matriz.objects.get(pk=request.GET.get('desvincular_matriz'))
        matriz.configuracao_creditos_especiais = None
        matriz.save()
        return httprr(f'/edu/configuracaoatividadecomplementar/{pk}/?tab=matrizes', 'Matriz desvinculada com sucesso.')
    return locals()


@rtr()
@group_required('Administrador Acadêmico')
def relatorio_educacenso_alunos_sem_codigo(request):
    return tasks.exportar_alunos_sem_codigo_educacenso(datetime.date.today().year)


@rtr()
@group_required('Administrador Acadêmico')
def preencher_relatorio_censup(request):
    title = 'Preencher Relatório CENSUP'
    form = PreencherRelatorioCensupForm(request.POST or None, files=request.POST and request.FILES or None)
    if form.is_valid():
        try:
            file_contents = form.cleaned_data['planilha'].file.read()
            tipo_relatorio = int(form.cleaned_data['tipo_relatorio'])
            coluna_busca = form.cleaned_data.get('coluna_busca') - 1
            coluna_salva = form.cleaned_data.get('coluna_salva') - 1
            return tasks.exportar_relatorio_censup_xls(file_contents, tipo_relatorio, coluna_busca, coluna_salva)
        except Exception as e:
            if settings.DEBUG:
                raise e
            return httprr('.', 'Erro ao tentar ler arquivo.', 'error')
    return locals()


@rtr()
@group_required('Administrador Acadêmico')
def atualizar_codigo_educacenso(request):
    title = 'Atualizar Código Educacenso'
    form = AtualizarCodigoEducacensoForm(request.POST or None, files=request.POST and request.FILES or None)
    if form.is_valid():
        return form.processar()
    return locals()


@rtr()
@group_required('Administrador Acadêmico')
def auditoria_censos(request):
    title = 'Auditoria Censos'
    form = AuditoriaCensoForm(data=request.POST or None, request=request)
    if form.is_valid():
        return form.processar()
    return locals()


@rtr()
@permission_required('edu.view_log')
def preencher_relatorio_sistec(request):
    title = 'Auditoria SISTEC -> SUAP'
    form = PreencherRelatorioSistecForm(request.POST or None, files=request.POST and request.FILES or None)
    if form.is_valid():
        try:
            planilha = form.cleaned_data['planilha']
            campus = form.cleaned_data['campus']
            path = os.path.join(settings.TEMP_DIR, planilha.name)
            planilha_path = open(path, 'w+b')
            planilha_path.write(planilha.file.read())
            planilha_path.close()
            return tasks.exportar_sistec_suap(planilha_path=planilha_path.name, campus=campus)
        except Exception as e:
            return httprr('.', str(e), 'error')
    return locals()


@rtr()
@permission_required('edu.view_log')
def preencher_relatorio_alunos_nao_existentes_sistec(request):
    title = 'Auditoria SUAP -> SISTEC'
    form = PreencherRelatorioAlunosNaoExistentesNoSistecForm(request.POST or None, files=request.POST and request.FILES or None)
    if form.is_valid():
        try:
            planilha = form.cleaned_data['planilha']
            campus_selecionado = form.cleaned_data.get('campus')
            anos_selecionados = form.cleaned_data.get('ano_letivo')
            convenios_selecionados = form.cleaned_data.get('excluir_convenio')
            path = os.path.join(settings.TEMP_DIR, planilha.name)
            planilha_path = open(path, 'w+b')
            planilha_path.write(planilha.file.read())
            planilha_path.close()
            return tasks.exportar_relatorio_alunos_nao_existentes_sistec_xls(planilha_path.name, campus_selecionado, anos_selecionados, convenios_selecionados)
        except Exception:
            return httprr('.', 'Erro ao tentar ler arquivo.', 'error')
    return locals()


@rtr()
@group_required('Administrador Acadêmico, Secretário Acadêmico')
def relatorio_isf(request):
    title = 'Relatório Idiomas sem Fronteiras'
    form = RelatorioIsFForm(data=request.POST or None)
    if form.is_valid():

        ano_letivo, periodo_letivo = form.processar()
        qs_aluno = Aluno.objects.filter(curso_campus__modalidade__nivel_ensino__in=[NivelEnsino.GRADUACAO, NivelEnsino.POS_GRADUACAO]).filter(
            matriculaperiodo__ano_letivo=ano_letivo, matriculaperiodo__periodo_letivo=periodo_letivo
        )
        return tasks.exportar_relatorio_isf_xls(qs_aluno)

    return locals()


@rtr()
@group_required('Administrador Acadêmico, Secretário Acadêmico')
def relatorio_sttu(request):
    title = 'Relatório STTU'
    form = RelatorioSTTUForm(data=request.POST or None, request=request)
    if form.is_valid():
        qs = form.processar()
        return tasks.exportar_para_sttu(qs)

    return locals()


@rtr()
@group_required('Administrador Acadêmico')
def relatorio_censup(request):
    title = 'Relatório CENSUP'
    form = RelatorioCensupForm(data=request.POST or None)
    if form.is_valid():
        return form.processar()
    return locals()


@rtr()
@group_required('Professor')
def cadastrar_visita_estagio_docente(request, pk, visita_pk=None):
    title = 'Registrar Visita do Professor'
    obj = get_object_or_404(EstagioDocente, pk=pk, professor_orientador__vinculo__user=request.user)
    instance = None
    if visita_pk:
        instance = get_object_or_404(VisitaEstagioDocente, pk=visita_pk)
    form = VisitaEstagioDocenteForm(estagio_docente=obj, data=request.POST or None, files=request.FILES or None, instance=instance)
    if form.is_valid():
        visita = form.save(False)
        visita.estagio_docente = obj
        visita.save()
        return httprr('..', 'Visita cadastrada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.view_estagiodocente')
def estagio_docente(request, pk):
    obj = get_object_or_404(EstagioDocente.locals, pk=pk)
    title = f'Estágio Docente - {obj.matricula_diario.diario.componente_curricular.componente.descricao}'
    return locals()


@rtr()
@group_required('Aluno')
def enviar_portfolio_estagio_docente(request, pk):
    obj = get_object_or_404(EstagioDocente, pk=pk, matricula_diario__matricula_periodo__aluno__pessoa_fisica__user=request.user)
    title = 'Enviar o portfólio'
    if obj.data_final_envio_portfolio >= datetime.date.today() and not obj.situacao == EstagioDocente.SITUACAO_ENCERRADO:
        title = 'Enviar o portfólio'
        form = EnviarPortfolioEstagioDocenteForm(request=request, data=request.POST or None, files=request.FILES or None, instance=obj)
        if form.is_valid():
            form.save()
            return httprr('..', 'Portfólio enviado com sucesso.')
    else:
        if obj.situacao == EstagioDocente.SITUACAO_ENCERRADO:
            title = 'O estágio docente já está encerrado.'
        else:
            title = f'Prazo para envio do portfólio encerrado. A data final foi: {format_(obj.data_final_envio_portfolio)}'
    return locals()


@rtr()
@group_required('Professor')
def enviar_avaliacao_estagio_docente(request, pk):
    obj = get_object_or_404(EstagioDocente, pk=pk, professor_orientador__vinculo__user=request.user)
    title = 'Enviar a avaliação'
    form = EnviarAvaliacaoEstagioDocenteForm(request=request, data=request.POST or None, files=request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Avaliação enviada com sucesso.')

    return locals()


@rtr()
@permission_required('edu.change_estagiodocente')
def encerrar_estagio_docente(request, pk):
    obj = get_object_or_404(EstagioDocente, pk=pk)
    title = f'Encerrar Estágio Docente de {obj.matricula_diario.matricula_periodo.aluno} por Conclusão'
    form = EncerrarEstagioDocenteForm(request=request, data=request.POST or None, files=request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Estágio docente concluído encerrado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_estagiodocente')
def encerrar_estagio_docente_nao_concluido(request, pk):
    obj = get_object_or_404(EstagioDocente, pk=pk)
    title = f'Encerrar Estágio Docente de {obj.matricula_diario.matricula_periodo.aluno} por Não Conclusão'
    form = EncerrarEstagioDocenteNaoConcluidoForm(request=request, data=request.POST or None, files=request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Estágio docente não concluído encerrado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_estagiodocente')
def cadastrar_estagio_docente_concomitante(request, pk):
    obj = get_object_or_404(EstagioDocente, pk=pk)
    title = f'Adicionar Estágio Docente Concomitante de {obj.matricula_diario.matricula_periodo.aluno}'
    form = CadastrarEstagioDocenteConcomitanteForm(estagio_docente=obj, request=request, data=request.POST or None, files=request.FILES or None)
    if form.is_valid():
        form.save()
        return httprr('..', 'Estágio docente concomitante adicionado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_estagiodocente')
def mudanca_escola_estagio_docente(request, pk):
    obj = get_object_or_404(EstagioDocente, pk=pk)
    title = f'Registrar Mudança de Escola do Estágio Docente de {obj.matricula_diario.matricula_periodo.aluno}'
    form = RegistrarMundancaEscolaEstagioDocenteForm(request=request, data=request.POST or None, files=request.FILES or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Estágio docente transferido de escola com sucesso.')
    return locals()


@rtr()
def acesso_responsavel(request):
    title = 'Acesso do Responsável'
    category = 'Acessos'
    icon = 'passport'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    form = AcessoResponsavelForm(request.POST or None)
    if form.is_valid():
        matricula = form.cleaned_data['matricula']
        request.session['matricula_aluno_como_resposavel'] = matricula
        return httprr(f'/edu/aluno/{matricula}/')
    return locals()


@rtr()
@permission_required('edu.change_requerimento')
def indeferir_requerimento(request, pk):
    title = 'Indeferir Requerimento'
    obj = get_object_or_404(Requerimento, pk=pk).sub_instance()
    form = IndeferirRequerimentoForm(data=request.POST or None, instance=obj)
    if form.is_valid():
        obj.indeferir(request.user)
        return httprr('..', 'Requerimento indeferido com sucesso.')
    return locals()


@rtr()
@permission_required('edu.view_requerimento')
def requerimento(request, pk):
    title = 'Requerimento'
    obj = get_object_or_404(Requerimento, pk=pk).sub_instance()
    if request.user.eh_aluno and obj.aluno.matricula != request.user.username:
        return httprr('..', 'Você não possui permissão para isso.', 'error')

    pode_realizar_procedimentos = request.user.has_perm('edu.change_requerimento')
    if pode_realizar_procedimentos and 'processar' in request.GET and obj.pode_ser_executado_automaticamente():
        try:
            obj.processar(request.user)
            return httprr('.', 'Requerimento atendido com sucesso.')
        except ValidationError as e:
            return httprr('.', e.message, 'error')

    elif pode_realizar_procedimentos:
        form = AvaliacaoRequerimentoForm(data=request.POST or None, instance=obj)
        if form.is_valid():
            form.save(user=request.user)
            return httprr('.', 'Ação realizada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_requerimento')
def desarquivar_requerimento(request, pk):
    obj = Requerimento.objects.get(pk=pk)
    if obj and obj.situacao == 'Arquivado':
        obj.situacao = 'Em Andamento'
        obj.deferido = None
        obj.save()
        return httprr(f'/edu/requerimento/{pk}/', 'Requerimento desarquivado com sucesso.')
    else:
        return httprr(f'/edu/requerimento/{pk}/', 'Não foi possível desarquivar o requerimento.', 'error')


@rtr()
# @group_required('')
def impressao_documentos_aluno(request):
    title = 'Impressão de Documento do Aluno'
    form = BuscarAlunoForm(data=request.POST or None)
    if form.is_valid():
        aluno = form.processar(request)
        if aluno:
            title = str(aluno)
    if 'logout' in request.GET:
        request.session['matricula-servico-impressao'] = None
        request.session.save()
    return locals()


@rtr()
@permission_required('edu.view_atividadecomplementar')
def atividadecomplementar(request, pk):
    title = 'Atividade Complementar'
    obj = get_object_or_404(AtividadeComplementar, pk=pk)
    if 'deferir' in request.GET and request.user.has_perm('edu.change_atividadecomplementar'):
        if request.GET['deferir'] == '1':
            obj.deferida = True
            obj.save()
            return httprr('..', 'Deferimento realizado com sucesso')
        else:
            obj.deferida = None
            obj.save()
            return httprr('..', 'Cancelamento do deferimento realizado com sucesso')
    elif 'indeferir' in request.GET and request.user.has_perm('edu.change_atividadecomplementar'):
        if request.GET['indeferir'] == '1':
            form = IndeferirAtividadeComplementarForm(data=request.POST or None, instance=obj)
            if form.is_valid():
                form.save()
                return httprr('..', 'Indeferimento realizado com sucesso.')
        else:
            obj.deferida = None
            obj.razao_indeferimento = None
            obj.save()
            return httprr('..', 'Cancelamento do indeferimento realizado com sucesso')
    return locals()


@rtr()
@group_required('Secretário Acadêmico,Coordenador de Curso,Diretor Acadêmico,Administrador Acadêmico,Pedagogo')
def analise_curso(request, pk, componente_curricular_pk=None, exibir=None):
    matriz_curso = get_object_or_404(MatrizCurso, pk=pk)
    registros = []
    pk_alunos = []
    alunos = []
    exibicao = []
    mapa_requisitos = dict()

    for pk, pre, co, componente_pk in matriz_curso.matriz.componentecurricular_set.values_list('pk', 'pre_requisitos', 'co_requisitos', 'pre_requisitos__componente'):
        if pk not in mapa_requisitos:
            mapa_requisitos[pk] = ([], [], [], [])
        if pre:
            mapa_requisitos[pk][0].append(pre)
        if co:
            mapa_requisitos[pk][1].append(co)
        if componente_pk:
            mapa_requisitos[pk][3].append(componente_pk)

    for pk in mapa_requisitos:
        for pre in mapa_requisitos[pk][0]:
            if pre in mapa_requisitos:
                if pk not in mapa_requisitos[pre][2]:
                    mapa_requisitos[pre][2].append(pk)

    situacoes = [SituacaoMatricula.MATRICULADO, SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL, SituacaoMatricula.TRANCADO]
    for aluno in Aluno.objects.filter(matriz=matriz_curso.matriz, curso_campus=matriz_curso.curso_campus, situacao__in=situacoes):
        pk_alunos.append(aluno.pk)
        aluno.ids_componentes_cumpridos = []
        if exibir != 'cursando':
            aluno.ids_componentes_cumpridos = aluno.get_ids_componentes_cumpridos()
        alunos.append(aluno)

    qs_periodos = matriz_curso.matriz.componentecurricular_set.exclude(periodo_letivo__isnull=True)
    if componente_curricular_pk:
        qs_periodos = qs_periodos.filter(pk=componente_curricular_pk)
    periodos = qs_periodos.order_by('periodo_letivo').values_list('periodo_letivo', flat=True).distinct()
    for periodo in list(periodos) + [None]:
        componentes_curriculares = []
        if periodo is None:
            qs_componente_curricular = matriz_curso.matriz.componentecurricular_set.filter(periodo_letivo__isnull=True)
        else:
            qs_componente_curricular = matriz_curso.matriz.componentecurricular_set.filter(periodo_letivo=periodo)
        if componente_curricular_pk:
            qs_componente_curricular = qs_componente_curricular.filter(pk=componente_curricular_pk)
        for componente_curricular in qs_componente_curricular:
            qs_cursando = MatriculaDiario.objects.filter(
                diario__componente_curricular__componente=componente_curricular.componente_id, situacao=MatriculaDiario.SITUACAO_CURSANDO, matricula_periodo__aluno__in=pk_alunos
            ).values_list('matricula_periodo__aluno', flat=True)
            componente_curricular.qtd_matriculados = len(qs_cursando)
            componente_curricular.qtd_concluidos = 0
            componente_curricular.qtd_pendentes = 0
            componente_curricular.qtd_aptos = 0
            componente_curricular.possui_requisitos = (
                mapa_requisitos[componente_curricular.pk][0] or mapa_requisitos[componente_curricular.pk][1] or mapa_requisitos[componente_curricular.pk][2]
            )
            for aluno in alunos:
                if componente_curricular.componente.pk in aluno.ids_componentes_cumpridos:
                    componente_curricular.qtd_concluidos = componente_curricular.qtd_concluidos + 1
                    if exibir == 'concluidos':
                        exibicao.append(aluno)
                else:
                    componente_curricular.qtd_pendentes = componente_curricular.qtd_pendentes + 1
                    if exibir == 'pendentes':
                        exibicao.append(aluno)
                    apto = True
                    for componente_pk in mapa_requisitos[componente_curricular.pk][3]:
                        if componente_pk not in aluno.ids_componentes_cumpridos:
                            apto = False
                            break
                    if apto and aluno.pk not in qs_cursando:
                        componente_curricular.qtd_aptos = componente_curricular.qtd_aptos + 1
                        if exibir == 'aptos':
                            exibicao.append(aluno)
            if exibir == 'cursando':
                exibicao = Aluno.objects.filter(pk__in=qs_cursando.values_list('matricula_periodo__aluno', flat=True))
            if exibir:
                title = f'Lista de Alunos ({len(exibicao)})'
                return locals()
            componentes_curriculares.append(componente_curricular)
        registros.append(dict(periodo=periodo or 'Optativo', componentes_curriculares=componentes_curriculares))

    width = 100 / len(registros)
    title = f'{matriz_curso.curso_campus.codigo} - {matriz_curso.curso_campus.descricao_historico} ({len(alunos)} alunos)'
    mapa_requisitos_js = json.dumps(mapa_requisitos)
    return locals()


@permission_required('edu.add_observacao')
@rtr()
def adicionar_observacao(request, aluno_pk):
    title = ' Adicionar Observação'
    aluno = Aluno.locals.filter(pk=aluno_pk).first()
    if aluno:
        form = ObservacaoForm(aluno, request.user, request.POST or None, instance=None)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Observação adicionada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar os dados deste aluno.', 'error')
    return locals()


@permission_required('edu.add_observacaodiario')
@rtr()
def adicionar_observacaodiario(request, diario_pk):
    title = ' Adicionar Observação'
    diario = Diario.locals.filter(pk=diario_pk).first()
    if diario:
        form = ObservacaoDiarioForm(diario, request.user, request.POST or None, instance=None)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Observação adicionada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar os dados deste diário.', 'error')
    return locals()


@permission_required('edu.change_observacao')
@rtr()
def editar_observacao(request, observacao_pk=None):
    title = ' Editar Observação'
    observacao = Observacao.objects.get(pk=observacao_pk)
    if request.user == observacao.usuario:
        form = ObservacaoForm(observacao.aluno, request.user, request.POST or None, instance=observacao)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Observação atualizada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar a observação de outro usuário.', 'error')
    return locals()


@permission_required('edu.change_observacaodiario')
@rtr()
def editar_observacaodiario(request, observacao_pk=None):
    title = ' Editar Observação'
    observacao = ObservacaoDiario.objects.get(pk=observacao_pk)
    if request.user == observacao.usuario:
        form = ObservacaoDiarioForm(observacao.diario, request.user, request.POST or None, instance=observacao)
        if form.is_valid():
            obj = form.save()
            return httprr('..', 'Observação atualizada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para modificar a obervação de outro usuário.', 'error')
    return locals()


@login_required()
@rtr()
def adicionar_premiacao(request, aluno_pk, premiacao_pk=None):
    title = ' {} Premiação'.format(premiacao_pk and 'Editar' or 'Adicionar')

    premiacao = None
    if premiacao_pk:
        premiacao = Premiacao.objects.get(pk=premiacao_pk)

    aluno = get_object_or_404(Aluno, pk=aluno_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = PremiacaoForm(aluno, request.POST or None, instance=premiacao)

    if form.is_valid():
        obj = form.save()

        if not premiacao_pk:
            return httprr('..', 'Premiação adicionada com sucesso.')
        else:
            return httprr('..', 'Premiação atualizada com sucesso.')

    return locals()


@login_required()
@rtr()
def adicionar_medida_disciplinar(request, aluno_pk, medida_pk=None):
    title = ' {} Medida Disciplinar'.format(medida_pk and 'Editar' or 'Adicionar')

    medida = None
    if medida_pk:
        medida = MedidaDisciplinar.objects.get(pk=medida_pk)

    aluno = get_object_or_404(Aluno, pk=aluno_pk)

    pode_realizar_procedimentos = perms.realizar_procedimentos_academicos(request.user, aluno.curso_campus)
    if not pode_realizar_procedimentos:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    form = MedidaDisciplinarForm(aluno, request.POST or None, instance=medida)

    if form.is_valid():
        obj = form.save()

        if not medida_pk:
            return httprr('..', 'Medida Disciplinar adicionada com sucesso.')
        else:
            return httprr('..', 'Medida Disciplinar atualizada com sucesso.')

    return locals()


@login_required()
@documento('Declaração de Orientação', validade=30, modelo='edu.professor')
@rtr('emitir_declaracao_de_orientacao_pdf.html')
def emitir_declaracao_de_orientacao_pdf(request, pk, tipo_estagio, ano):
    if in_group(request.user, 'Administrador Acadêmico,Secretário Acadêmico,Coordenador de Curso,Diretor Acadêmico'):
        obj = get_object_or_404(Professor, pk=pk)
    else:
        obj = get_object_or_404(Professor, pk=pk, vinculo__user=request.user)
    nome_professor = obj.vinculo.pessoa.nome
    matricula_siape = obj.vinculo.relacionamento.matricula
    uo = request.user.get_profile().funcionario.setor.uo
    hoje = datetime.date.today()
    estagios_docente = EstagioDocente.objects.none()
    estagios = PraticaProfissional.objects.none()
    aprendizagens = Aprendizagem.objects.none()
    atividades_profissionais_efetivas = AtividadeProfissionalEfetiva.objects.none()
    is_todos_os_anos = ano == '0'
    if tipo_estagio == 'estagios':
        tipo_estagio = 'Estágio'
        if is_todos_os_anos:
            estagios = obj.praticaprofissional_set.all()
        else:
            estagios_concluidos = obj.praticaprofissional_set.exclude(data_fim__isnull=True)
            estagios_nao_concluidos = obj.praticaprofissional_set.exclude(data_fim__isnull=False)
            estagios = estagios_nao_concluidos.filter(data_inicio__year__lte=ano, data_prevista_fim__year__gte=ano) | estagios_concluidos.filter(
                data_inicio__year__lte=ano, data_fim__year__gte=ano
            )
            estagios = estagios.distinct()
    elif tipo_estagio == 'aprendizagens':
        tipo_estagio = 'Aprendizagem'
        if is_todos_os_anos:
            aprendizagens = obj.aprendizagem_set.all()
        else:
            aprendizagens_concluidas = obj.aprendizagem_set.filter(data_encerramento__isnull=True)
            aprendizagens_nao_concluidas = obj.aprendizagem_set.filter(data_encerramento__isnull=False)
            aprendizagens = aprendizagens_nao_concluidas.filter(
                moduloaprendizagem__inicio__year__lte=ano, moduloaprendizagem__fim__year__gte=ano
            ) | aprendizagens_concluidas.filter(moduloaprendizagem__inicio__year__lte=ano, moduloaprendizagem__fim__year__gte=ano)
            aprendizagens = aprendizagens.distinct()
    elif tipo_estagio == 'estagiosdocentes':
        tipo_estagio = 'Estágio Docente'
        if is_todos_os_anos:
            estagios_docente = obj.estagiodocente_orientador_set.all()
        else:
            estagios_docente = obj.estagiodocente_orientador_set.filter(data_inicio__year__lte=ano, data_fim__year__gte=ano)
    elif tipo_estagio == 'atividadesprofissionaisefetivas':
        tipo_estagio = 'Atividade Profissional Efetiva'
        if is_todos_os_anos:
            atividades_profissionais_efetivas = obj.atividadeprofissionalefetiva_set.all()
        else:
            atividades_profissionais_efetivas_concluidas = obj.atividadeprofissionalefetiva_set.exclude(encerramento__isnull=True)
            atividades_profissionais_efetivas_nao_concluidas = obj.atividadeprofissionalefetiva_set.exclude(encerramento__isnull=False)
            atividades_profissionais_efetivas = atividades_profissionais_efetivas_nao_concluidas.filter(
                inicio__year__lte=ano, data_prevista_encerramento__year__gte=ano
            ) | atividades_profissionais_efetivas_concluidas.filter(inicio__year__lte=ano, encerramento__year__gte=ano)
            atividades_profissionais_efetivas = atividades_profissionais_efetivas.distinct()

    if estagios_docente.exists() or estagios.exists() or aprendizagens.exists() or atividades_profissionais_efetivas.exists():
        return locals()
    else:
        return httprr(f'/edu/professor/{obj.pk}/?tab=estagios', 'Nenhuma orientação registrada para este ano/professor.', 'error')


@rtr()
@group_required('Administrador Acadêmico')
def relatorio_educacenso(request):
    title = 'Relatório Educacenso'
    form = RelatorioEducacensoForm(data=request.POST or None, request=request)
    if form.is_valid():
        return form.processar()
    return locals()


@rtr()
@group_required('Administrador Acadêmico')
def relatorio_educacenso_etapa_2(request):
    title = 'Relatório Educacenso Etapa 2'
    form = RelatorioEducacensoEtapa2Form(data=request.POST or None, request=request)
    if form.is_valid():
        return form.processar()
    return locals()


@rtr()
@group_required('Administrador Acadêmico')
def importar_educacenso_etapa_2(request):
    title = 'Importação Educacenso Etapa 2'
    form = ImportarEducacensoEtapa2Form(data=request.POST or None, request=request, files=request.POST and request.FILES or None)
    if form.is_valid():
        return form.processar()
    return locals()


@rtr()
@group_required('Diretor de Avaliação e Regulação do Ensino')
def relatorio_coordenacao_curso(request):
    title = 'Relatório de Coordenação de Cursos'
    form = RelatorioCoordenacaoCursoForm(data=request.POST or None)
    if form.is_valid():
        cursos = form.processar()
    return locals()


@rtr()
@login_required()
def atualizar_email(request, pk):
    title = 'Atualização do E-mail'
    aluno = Aluno.locals.filter(pk=pk).first()
    if not perms.pode_alterar_email(request, aluno):
        raise PermissionDenied()
    form = AtualizarEmailAlunoForm(request.POST or None, request=request, aluno=aluno)
    if form.is_valid():
        form.save()
        return httprr('..', 'E-mail atualizado com sucesso.')
    return locals()


@receiver(rh_servidor_view_tab)
def servidor_view_tab_participacoes_signal(sender, request, servidor, verificacao_propria, eh_chefe, **kwargs):
    participacoes_eventos = ParticipanteEvento.objects.filter(participante__cpf=servidor.cpf)
    if participacoes_eventos.exists():
        return render_to_string(
            template_name='edu/templates/tabs/professor_participacoes_eventos.html',
            context={"lps_context": {"nome_modulo": "edu", "extra_dir": "tabs"}, 'servidor': servidor, 'participacoes_eventos': participacoes_eventos, 'verificacao_propria': verificacao_propria},
            request=request,
        )
    return False


@rtr()
@permission_required('rh.eh_rh_sistemico')
def editar_disciplina_docente(request, docente_pk):
    professor_docente = get_object_or_404(Professor, vinculo__pessoa__pk=docente_pk)
    form = DisciplinaIngressoProfessorForm(request.POST or None, instance=professor_docente)
    if form.is_valid():
        form.save()
        return httprr('..', 'Disciplina salva com sucesso.')
    return locals()


@permission_required('edu.gerar_turmas')
@rtr()
def exportar_dados_pnp(request):
    title = 'Exportar Dados - Plataforma Nilo Peçanha'
    form = ExportarDadosPNP(data=request.POST or None)
    if form.is_valid():
        return form.processar()
    return locals()


@permission_required('edu.add_itemconfiguracaoavaliacao')
@rtr()
def agendar_avaliacao(request, pk):
    title = 'Agendar Avaliação'
    obj = get_object_or_404(ItemConfiguracaoAvaliacao, pk=pk)
    form = AgendarAvaliacaoForm(data=request.POST or None, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Avaliação agendada com sucesso')
    return locals()


@rtr()
def calendario_avaliacao(request, pk=None):
    title = 'Agenda de Avaliações'

    calendario = CalendarioPlus()
    calendario.mostrar_mes_e_ano = True
    calendario.envolve_mes_em_um_box = True
    calendario.destacar_hoje = True
    hoje = datetime.date.today()
    username = request.user.username
    ano_letivo = Ano.objects.get_or_create(ano=hoje.year)[0]
    pks_diario_professor = []
    if pk:
        qs_diarios = Diario.objects.filter(turma_id=pk)
    else:
        qs_diarios = Diario.objects.filter(ano_letivo=ano_letivo)
        diarios_professor = qs_diarios.filter(professordiario__professor__vinculo__user__username=username)
        qs_diarios_aluno = qs_diarios.filter(matriculadiario__matricula_periodo__aluno__pessoa_fisica__username=username)
        qs_diarios = qs_diarios_aluno | diarios_professor
        pks_diario_professor = list(diarios_professor.values_list('pk', flat=True))
    diarios = []
    possui_avaliacao_agendada = False
    inicio = hoje
    fim = hoje
    for diario in qs_diarios.order_by('pk').distinct('pk'):
        diario.itens_avaliacao = []
        for item_avaliacao in diario.get_itens_avaliacao():
            item_avaliacao.editavel = item_avaliacao.configuracao_avaliacao.diario.pk in pks_diario_professor
            diario.itens_avaliacao.append(item_avaliacao)
            diario.possui_avaliacao_nao_agendada = False
            if item_avaliacao.data:
                possui_avaliacao_agendada = True
                if item_avaliacao.data < inicio:
                    inicio = item_avaliacao.data
                if item_avaliacao.data > fim:
                    fim = item_avaliacao.data
                calendario.adicionar_evento_calendario(
                    data_inicio=item_avaliacao.data,
                    data_fim=item_avaliacao.data,
                    descricao='{} {} - {} - {}'.format(
                        item_avaliacao.get_tipo_display(),
                        item_avaliacao.sigla,
                        item_avaliacao.get_descricao_etapa(),
                        item_avaliacao.configuracao_avaliacao.diario.componente_curricular.componente.descricao_historico,
                    ),
                    css_class=item_avaliacao.get_qtd_avaliacoes_concorrentes() > 1 and 'alert' or 'info',
                    title=f'{item_avaliacao.descricao or item_avaliacao.sigla} - {item_avaliacao.configuracao_avaliacao.diario}',
                    url=item_avaliacao.editavel and f'/edu/agendar_avaliacao/{item_avaliacao.pk}/' or None,
                )
            else:
                diario.possui_avaliacao_nao_agendada = True
        diarios.append(diario)
    calendario_html = calendario.formato_periodo(inicio.month, inicio.year, fim.month, fim.year)
    return locals()


@rtr()
@login_required()
def adicionar_topico_discussao(request, pk, etapa):
    title = 'Adicionar Tópico'
    is_aluno_diario = MatriculaDiario.objects.filter(diario__pk=pk, matricula_periodo__aluno__matricula=request.user.username).exists()
    is_professor_diario = ProfessorDiario.objects.filter(diario__pk=pk, professor__vinculo__user=request.user, ativo=True).exists()
    if is_aluno_diario or is_professor_diario:
        diario = get_object_or_404(Diario, pk=pk)
        initial = dict(etapa=int(etapa) or None)
        form = TopicoDiscussaoForm(data=request.POST or None, request=request, initial=initial)
        if diario.componente_curricular.qtd_avaliacoes == 1:
            form.fields['etapa'].choices = [[1, 'Etapa 1']]
        if diario.componente_curricular.qtd_avaliacoes == 2:
            form.fields['etapa'].choices = [[1, 'Etapa 1'], [2, 'Etapa 2']]
        if form.is_valid():
            form.save(diario, int(etapa))
            if is_aluno_diario:
                return httprr(f'/edu/disciplina/{pk}/?tab=forum', 'Tópico adicionado com sucesso.', close_popup=True)
            else:
                return httprr(f'/edu/meu_diario/{pk}/{etapa}/?tab=forum', 'Tópico adicionado com sucesso.', close_popup=True)
    else:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    return locals()


@rtr()
@login_required()
def responder_topico_discussao(request, pk):
    title = 'Adicionar Comentário'
    is_aluno_diario = MatriculaDiario.objects.filter(diario__topicodiscussao__pk=pk, matricula_periodo__aluno__matricula=request.user.username).exists()
    is_professor_diario = ProfessorDiario.objects.filter(diario__topicodiscussao__pk=pk, professor__vinculo__user=request.user, ativo=True).exists()
    if is_aluno_diario or is_professor_diario:
        topico = get_object_or_404(TopicoDiscussao, pk=pk)
        form = RespostaDiscussaoForm(data=request.POST or None, request=request)
        if form.is_valid():
            form.save(topico)
            return httprr('..', 'Resposta enviada com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    return locals()


@rtr()
@login_required()
def solicitar_trabalho(request, pk, etapa, pk_trabalho=None):
    title = 'Solicitar Trabalho'
    is_professor_diario = ProfessorDiario.objects.filter(diario__pk=pk, professor__vinculo__user=request.user, ativo=True).exists()
    instance = None
    if pk_trabalho:
        instance = Trabalho.objects.get(pk=pk_trabalho, diario=pk)
    if is_professor_diario:
        diario = get_object_or_404(Diario, pk=pk)
        form = TrabalhoForm(data=request.POST or None, request=request, files=request.POST and request.FILES or None, instance=instance)
        if form.is_valid():
            form.save(diario, int(etapa))
            return httprr('..', 'Trabalho solicitado com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    return locals()


@rtr()
@login_required()
def entregar_trabalho(request, pk):
    title = 'Entregar Trabalho'
    is_aluno_diario = MatriculaDiario.objects.filter(diario__trabalho__pk=pk, matricula_periodo__aluno__matricula=request.user.username).exists()
    if is_aluno_diario:
        aluno = request.user.get_vinculo().relacionamento
        trabalho = get_object_or_404(Trabalho.objects.distinct(), pk=pk, diario__matriculadiario__matricula_periodo__aluno=aluno)
        form = EntregaTrabalhoForm(data=request.POST or None, request=request, files=request.POST and request.FILES or None)
        if form.is_valid():
            form.save(trabalho, aluno)
            return httprr('..', 'Trabalho entregue com sucesso.')
    else:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')
    return locals()


@rtr()
@login_required()
def visualizar_entregas_trabalho(request, pk):
    title = 'Entregas de Trabalho'
    trabalho = get_object_or_404(Trabalho, pk=pk)
    if request.user.pk not in trabalho.diario.professordiario_set.values_list('professor__vinculo__user', flat=True):
        return HttpResponseForbidden()
    return locals()


@permission_required('edu.importar_aluno')
@rtr()
def importar_aluno_qacademico(request, pk):
    aluno = Aluno.objects.get(pk=pk)
    dao = DAO()
    dao.importar_alunos(prefixo_matricula=aluno.matricula, verbose=False)
    dao.importar_matriculas_periodo(prefixo_matricula=aluno.matricula, verbose=False)
    dao.importar_registros_diploma(matricula=aluno.matricula)
    return httprr(f'/edu/aluno/{aluno.matricula}/', 'Aluno importado com sucesso.')


@rtr()
@permission_required('edu.add_horarioatividadeextra')
def adicionar_horario_atividade_extra(request, aluno_pk, ano, periodo):
    aluno = get_object_or_404(Aluno.objects, pk=aluno_pk)
    mp = MatriculaPeriodo.objects.filter(aluno__pk=aluno_pk, ano_letivo__ano=ano, periodo_letivo=periodo)
    if not mp.exists():
        return httprr('..', f'Não existe uma matrícula no período {ano}.{periodo} para este o aluno {aluno}.', 'error')
    if request.user.eh_aluno and not aluno.is_user(request):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    title = "Adicionar Atividade Extra"
    turnos = mp[0].get_horarios_aula_atividade_por_turno()
    form = HorarioAtividadeExtraForm(data=request.POST or None, request=request, matricula_periodo=mp[0])
    if form.is_valid():
        horarios = dict(request.POST).get("horario")
        form.save(horarios)
        return httprr('..', 'Atividade adicionada com sucesso.')
    return locals()


@rtr('adicionar_horario_atividade_extra.html')
@permission_required('edu.add_horarioatividadeextra')
def editar_horario_atividade_extra(request, aluno_pk, ano, periodo, atividade_extra_pk):
    aluno = get_object_or_404(Aluno.objects, pk=aluno_pk)
    mp = get_object_or_404(MatriculaPeriodo.objects, aluno__pk=aluno_pk, ano_letivo__ano=ano, periodo_letivo=periodo)
    atividade_extra = get_object_or_404(HorarioAtividadeExtra.objects, pk=atividade_extra_pk)
    if request.user.eh_aluno and not aluno.is_user(request):
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    title = "Alterar Horário da Atividade Extra"
    turnos = mp.get_horarios_aula_atividade_por_turno()
    form = EditarHorarioAtividadeExtraForm(data=request.POST or None, request=request, instance=atividade_extra, matricula_periodo=mp)
    if form.is_valid():
        horarios = dict(request.POST).get("horario")
        form.save(horarios)
        return httprr('..', 'Atividade atualizada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.add_atividadecurricularextensao')
def adicionar_atividade_curricular_extensao(request, aluno_pk, pk=None):
    title = 'Registrar Atividade Curricular de Extensão'
    aluno = get_object_or_404(Aluno.objects, pk=aluno_pk)
    instance = pk and get_object_or_404(AtividadeCurricularExtensao.objects, pk=pk) or None
    form = AtividadeCurricularExtensaoForm(aluno, data=request.POST or None, instance=instance)
    if form.is_valid():
        form.save()
        return httprr('..', 'Atividade cadastrada com sucesso.')
    return locals()


@permission_required('edu.view_turma')
def exportar_xls_aluno(request):
    escopo = request.GET.get('escopo', None)

    turma_pk = request.GET.get('turma', None)
    turma_manager = in_group(request.user, 'Diretor Acadêmico') and Turma.objects or Turma.locals
    turma_obj = get_object_or_404(turma_manager, pk=turma_pk)

    xls = request.GET.get('xls', None)

    rows = []
    name_xls = 'report_xls'

    if escopo == 'turma':
        if xls in ['alunos_na_turma', 'alunos_apenas_em_diarios', 'alunos_todos']:
            rows.append(['#', 'Código da Turma', 'Aluno', 'Matrícula', 'Situação no Período'])
            name_xls = f'{turma_obj.codigo}_{xls}'

        matriculas_periodo = MatriculaPeriodo.objects.none()

        if xls == 'alunos_na_turma':
            matriculas_periodo = turma_obj.get_alunos_matriculados()

        elif xls == 'alunos_apenas_em_diarios':
            matriculas_periodo = turma_obj.get_alunos_matriculados_diarios()

        elif xls == 'alunos_todos':
            matriculas_periodo = turma_obj.get_alunos_matriculados() | MatriculaPeriodo.objects.filter(
                pk__in=[matricula.id for matricula in turma_obj.get_alunos_matriculados_diarios()]
            )

        count = 0
        for matricula_periodo in matriculas_periodo:
            count += 1
            rows.append([count, turma_obj.codigo, matricula_periodo.aluno.get_nome(), matricula_periodo.aluno.matricula, matricula_periodo.situacao])

    if not rows:
        rows.append(['?'])

    return XlsResponse(rows, name=name_xls)


@group_required('Diretor Geral, Diretor Acadêmico, Diretor de Ensino, Reitor')
@rtr()
def iniciar_sessao_assinatura_eletronica(request):
    title = 'Iniciar Sessão de Assinatura Eletrônica'
    form = IniciarSessaoAssinaturaEletronicaForm(data=request.POST or None, request=request)
    if form.is_valid():
        return httprr('..', 'Sessão de assinatura eletrônica iniciada com sucesso.')
    return locals()


@group_required('Diretor Geral, Diretor Acadêmico, Diretor de Ensino, Reitor')
def finalizar_sessao_assinatura_eletronica(request):
    if 'sessao_assinatura_eletronica' in request.session:
        del request.session['sessao_assinatura_eletronica']
        request.session.save()
    return httprr('/admin/edu/assinaturaeletronica/', 'Sessão de assinatura eletrônica finalizada com sucesso.')


@group_required('Diretor Geral, Diretor Acadêmico, Diretor de Ensino, Reitor')
@rtr()
def revogar_assinatura_eletronica(request, pk):
    title = 'Revogar Assinaturas Eletrônicas'
    form = RevogarDiplomaForm(data=request.POST or None, request=request)
    if form.is_valid():
        for assinatura_eletronica in AssinaturaEletronica.objects.filter(pk__in=pk.split('_')):
            assinatura_eletronica.revogar(form.cleaned_data['motivo'])
        return httprr('..', 'Assinaturas revogadas com sucesso.')
    return locals()


@group_required('Diretor Geral, Diretor Acadêmico, Diretor de Ensino, Reitor')
def assinar_diplomas_eletronicos(request, pk):
    qs = AssinaturaEletronica.objects.filter(pk__in=pk.split('_'), registro_emissao_diploma__cancelado=False)
    return tasks.assinar_diplomas_eletronicos(request, qs)


@rtr()
@permission_required('edu.view_codigoautenticadorsistec')
def importar_autenticacao_sistec(request):
    title = 'Importar Autenticação SISTEC'
    form = ImportarAutenticacaoSistecForm(data=request.POST or None, files=request.FILES or None)
    if form.is_valid():
        try:
            c = form.processar()
            return httprr('..', f'Importação de {c} código(s) realizada com sucesso')
        except Exception as e:
            if settings.DEBUG:
                raise e
        return httprr('..', 'Formato do formato inválido.', 'error')
    return locals()


@login_required()
@rtr()
def assinar_ata_eletronica(request, pk):
    title = 'Assinar Ata Eletrônica'
    assinatura = get_object_or_404(AssinaturaAtaEletronica, pk=pk)
    if assinatura.pessoa_fisica.user != request.user:
        return HttpResponseForbidden()
    form = IniciarSessaoAssinaturaSenhaForm(data=request.POST or None, request=request)
    if form.is_valid():
        assinatura.assinar()
        return httprr('..', 'Assinatura eletrônica realizada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.add_alunoarquivo')
def upload_arquivo_unico(request, pk):
    title = 'Upload de Arquivo'
    aluno = get_object_or_404(Aluno, pk=pk)
    form = UploadAlunoArquivoUnicoForm(data=request.POST or None, files=request.FILES or None)
    if form.is_valid():
        tipo = form.cleaned_data['tipo']

        # TODO: Rever este cadastro de Aluno Arquivo, pois da forma como está, caso o operador adicione dois arquivos iguais,
        # dois arquivoUnico serão criados no banco e no disco, ao invés de apenas um ArquivoUnico e dois AlunoArquivo referenciando
        # esse ArquivoUnico. O método AlunoArquivo.update_or_create_from_file_bytes cuida disso. Na época que Breno foi implementar
        # o cadastro manual de arquivos, eu cheguei a comentar com ele sobre esse método, mas talvez ele não tenha entendido bem a
        # a ideia.
        arquivo_unico = form.save()
        arquivo_unico.tipo_conteudo = arquivo_unico.conteudo.file.content_type
        arquivo_unico.tamanho_em_bytes = arquivo_unico.conteudo.file.size
        arquivo_unico.charset = None
        arquivo_unico.nome_original_primeiro_upload = arquivo_unico.conteudo.file.name
        arquivo_unico.data_hora_primeiro_upload = datetime.datetime.now()
        arquivo_unico.data_hora_criacao_registro = datetime.datetime.now()
        arquivo_unico.hash_sha512 = hashlib.sha512(arquivo_unico.conteudo.file.read())
        hash_sha512_link_id_str = '[{}],[{}]'.format(
            arquivo_unico.data_hora_criacao_registro.strftime('%d%m%Y__%H:%M:%S.%f'), arquivo_unico.hash_sha512)
        hash_sha512_link_id_bytes = (hash_sha512_link_id_str).encode('utf-8')
        arquivo_unico.hash_sha512_link_id = hashlib.sha512(hash_sha512_link_id_bytes).hexdigest()
        arquivo_unico.save()

        arquivo_aluno = AlunoArquivo()
        arquivo_aluno.tipo_origem_cadastro = AlunoArquivo.TIPO_ORIGEM_CADASTRO_MANUAL
        arquivo_aluno.tipo = tipo
        arquivo_aluno.aluno = aluno
        arquivo_aluno.arquivo_unico = arquivo_unico
        arquivo_aluno.nome_original = arquivo_unico.conteudo.file.name
        arquivo_aluno.nome_exibicao = arquivo_aluno.tipo.nome
        arquivo_aluno.descricao = arquivo_aluno.tipo.nome
        arquivo_aluno.validado = None
        arquivo_aluno.data_hora_upload = datetime.datetime.now()
        arquivo_aluno.data_hora_upload = datetime.datetime.now()
        arquivo_aluno.data_hora_criacao_registro = datetime.datetime.now()
        arquivo_aluno.save()
        return httprr('..', 'Arquivo cadastrado com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_alunoarquivo')
def avaliar_arquivo_unico(request, pk):
    title = 'Avaliar Documento'
    arquivo_aluno = get_object_or_404(AlunoArquivo, pk=pk)
    form = AvaliarArquivoUnicoForm(data=request.POST or None, instance=arquivo_aluno)
    if form.is_valid():
        form.save()
        arquivo_aluno.responsavel_validacao = request.user
        arquivo_aluno.data_validacao = datetime.datetime.now()
        arquivo_aluno.save()
        return httprr('..', 'Avaliação realizada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_alunoarquivo')
def avaliacao_documentos(request, pk):
    title = 'Avaliar Arquivo'
    qs = AlunoArquivo.objects.filter(validado__isnull=True, aluno__curso_campus__diretoria_id=pk)
    return locals()


@permission_required('edu.view_registroemissaodiploma')
def baixar_xml_documentacao_academica(request, pk):
    obj = get_object_or_404(AssinaturaDigital, pk=pk)
    arquivo = obj.baixar_xml_documentacao_academica()
    response = HttpResponse(arquivo, content_type='application/force-download')
    response['Content-Disposition'] = f'attachment; filename=documentacao_academica_{pk}.xml'
    return response


@permission_required('edu.view_registroemissaodiploma')
def baixar_xml_historico_escolar(request, pk):
    obj = get_object_or_404(AssinaturaDigital, pk=pk)
    arquivo = obj.baixar_xml_historico_escolar()
    response = HttpResponse(arquivo, content_type='application/force-download')
    response['Content-Disposition'] = f'attachment; filename=historico_escolar_{pk}.xml'
    return response


def baixar_xml_dados_diploma(request, pk):
    obj = get_object_or_404(AssinaturaDigital, pk=pk)
    return obj.baixar_xml_dados_diploma()


@rtr()
@login_required()
def consultar_status_assinaturas(request, pk):
    title = 'Situação das Assinaturas'
    obj = get_object_or_404(RegistroEmissaoDiploma, pk=pk)
    if obj.aluno.curso_campus.assinatura_eletronica:
        assinatura = obj.get_assinatura_eletronica()
        if assinatura:
            return consultar_status_assinaturas_eletronicas(request, assinatura.pk)
    elif obj.aluno.curso_campus.assinatura_digital:
        assinatura = obj.get_assinatura_digital()
        if assinatura:
            return consultar_status_assinaturas_digitais(request, assinatura.pk)
    return locals()


@rtr()
@login_required()
def consultar_status_assinaturas_digitais(request, pk):
    title = 'Situação das Assinaturas'
    obj = get_object_or_404(AssinaturaDigital, pk=pk)
    dados = obj.consultar_status_assinaturas()
    return locals()


@rtr()
@login_required()
def consultar_status_assinaturas_eletronicas(request, pk):
    title = 'Situação das Assinaturas'
    obj = get_object_or_404(AssinaturaEletronica, pk=pk)
    solicitacoes_assinatura = obj.solicitacaoassinaturaeletronica_set.all()
    return locals()


def baixar_pdf_representacao_visual(request, pk):
    obj = get_object_or_404(AssinaturaDigital, pk=pk)
    return obj.baixar_pdf_representacao_visual()


@login_required()
@documento('Certificado de Conclusão', False, validade=120, enumerar_paginas=False, modelo='edu.certificadodiploma')
@rtr()
def certificado_diploma_pdf(request, pk):
    hoje = datetime.date.today()
    obj = get_object_or_404(CertificadoDiploma, pk=pk)
    uo = obj.aluno.curso_campus.diretoria.setor.uo
    return locals()


@documento()
@rtr()
def plano_ensino_pdf(request, pk):
    obj = get_object_or_404(PlanoEnsino, pk=pk)
    return locals()


@login_required()
@rtr()
def devolver_plano_ensino(request, destino, pks):
    title = 'Devolver Plano de Ensino'
    form = DevolverPlanoEnsino(data=request.POST or None)
    if form.is_valid():
        for plano in PlanoEnsino.objects.filter(pk__in=pks.split('__')):
            if destino == 'professor' and in_group(request.user, 'Coordenador de Curso'):
                plano.devolver_para_professor(request.user, form.cleaned_data['justificativa'])
            elif destino == 'coordenador' and in_group(request.user, 'Diretor Acadêmico'):
                plano.devolver_para_coordenador(request.user, form.cleaned_data['justificativa'])
        return httprr('..', 'Ação realizada com sucesso.')
    return locals()


@login_required()
@rtr()
def planoestudo(request, pk):
    obj = get_object_or_404(PlanoEstudo, pk=pk)
    resumo_ch = obj.get_resumo_ch()
    return locals()


@login_required()
@rtr()
def definir_planoestudo(request, pk):
    title = 'Definir Plano de Estudo'
    obj = get_object_or_404(PlanoEstudo, pk=pk)
    is_coordenador = obj.pedido_matricula.matricula_periodo.aluno.curso_campus.coordenador_id == request.user.get_profile().id
    form = DefinirPlanoEstudoForm(data=request.POST or None, plano_estudo=obj)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Plano de estudo definido com sucesso.')
    return locals()


@documento()
@rtr()
def planoestudo_pdf(request, pk):
    obj = get_object_or_404(PlanoEstudo, pk=pk)
    return locals()


@login_required()
@rtr()
def avaliar_plano_estudo(request, pks):
    title = 'Devolver Plano de Ensino'
    qs = PlanoEstudo.objects.filter(pk__in=pks.split('__'))
    if not in_group(request.user, 'Diretor Acadêmico') and not request.user.is_superuser:
        return HttpResponseForbidden()
    form = AvaliarPlanoEstudoForm(data=request.POST or None)
    if form.is_valid():
        form.processar(qs)
        return httprr('..', 'Ação realizada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.view_registroeducacenso')
def registroeducacenso(request, pk):
    obj = get_object_or_404(RegistroEducacenso, pk=pk)
    title = str(obj)
    questoes = obj.questaoeducacenso_set.all()
    qtd_questoes = obj.questaoeducacenso_set.count()
    campi = UnidadeOrganizacional.objects.campi().values('sigla', 'nome')
    campus_selecionado = campi.filter(sigla=request.GET.get('campus')).first()
    if not campus_selecionado:
        campus_selecionado = campi.first()
    respostas = obj.get_respostas_por_campus(sigla_campus=campus_selecionado['sigla'])
    return locals()


@rtr()
@permission_required('edu.add_questaoeducacenso')
def adicionar_questaoeducacenso(request, pk_registroeducacenso, pk_clone=None):
    title = 'Adicionar Campo ao Questionário Educacenso'
    if pk_clone:
        clone = get_object_or_404(QuestaoEducacenso, pk=pk_clone)

    form = QuestaoEducacensoForm(data=request.POST or None, registro=pk_registroeducacenso, clone=pk_clone and clone or None)
    if form.is_valid():
        form.save()
        return httprr('..', 'Ação realizada com sucesso.')
    return locals()


@rtr()
@permission_required('edu.change_questaoeducacenso')
def responder_questionarioeducacenso(request, pk_registroeducacenso):
    obj = get_object_or_404(RegistroEducacenso, pk=pk_registroeducacenso)
    title = 'Responder Questionário Educacenso (Campus {})'.format(request.user.get_vinculo().setor.uo.sigla)
    Form = RespostaEducacensoFormFactory(request, pk_registroeducacenso, request.user.get_vinculo().setor.uo.id)
    if request.method == 'POST':
        form = Form(data=request.POST)
        if form.is_valid():
            form.save()
            return httprr(f'{obj.get_absolute_url()}', 'Ação realizada com sucesso.')
    else:
        form = Form()
    return locals()


@rtr()
@permission_required('edu.add_questaoeducacenso')
def responder_questionarioeducacenso_campus(request, pk_registroeducacenso, campus):
    obj = get_object_or_404(RegistroEducacenso, pk=pk_registroeducacenso)
    uo = UnidadeOrganizacional.objects.campi().get(sigla=campus)
    title = 'Responder Questionário Educacenso ({})'.format(campus)
    Form = RespostaEducacensoFormFactory(request, pk_registroeducacenso, uo.id)
    if request.method == 'POST':
        form = Form(data=request.POST)
        if form.is_valid():
            form.save()
            return httprr(f'{obj.get_absolute_url()}', 'Ação realizada com sucesso.')
    else:
        form = Form()
    return locals()


@rtr()
@permission_required('edu.change_respostaeducacenso')
def editar_resposta_questionarioeducacenso(request, pk_resposta):
    obj = get_object_or_404(RespostaEducacenso, pk=pk_resposta)
    title = 'Editar Resposta - {} (Campus {})'.format(obj.questao, obj.campus)
    Form = RespostaQuestaoEducacensoFormFactory(request, pk_questao=obj.questao.pk, pk_campus=obj.campus.pk)
    if request.method == 'POST':
        form = Form(data=request.POST)
        if form.is_valid():
            form.save()
            return httprr('..', 'Ação realizada com sucesso.')
    else:
        form = Form()
    return locals()


@rtr()
@permission_required('edu.add_questaoeducacenso')
def publicar_questaoeducacenso(request, pk_registroeducacenso, publicar):
    obj = get_object_or_404(RegistroEducacenso, pk=pk_registroeducacenso)
    if int(publicar):
        obj.publicar()
    else:
        obj.fechar()
    return httprr(f'{obj.get_absolute_url()}', 'Ação realizada com sucesso.')


@rtr()
@permission_required('edu.add_questaoeducacenso')
def responder_questaoeducacenso(request, pk):
    obj = get_object_or_404(QuestaoEducacenso, pk=pk)
    title = 'Responder para Todos os Campi - {}'.format(obj)
    Form = RespostaQuestaoEducacensoFormFactory(request, pk)
    if request.method == 'POST':
        form = Form(data=request.POST)
        if form.is_valid():
            form.save()
            return httprr(f'{obj.registro.get_absolute_url()}', 'Ação realizada com sucesso.')
    else:
        form = Form()
    return locals()


@rtr()
@login_required
def preencher_dados_titulacao(request):
    title = 'Dados da Titulação'
    obj = get_object_or_404(Professor.objects, vinculo=request.user.get_vinculo())
    form = InformarDadosTitulacaoForm(data=request.POST or None, request=request, instance=obj)
    if form.is_valid():
        form.save()
        request.session['informacao-titulacao-pendente'] = False
        request.session.save()
        return httprr('/', 'Dados salvos com sucesso.')
    return locals()
