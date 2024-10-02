import collections
import hashlib
import operator
import os
from datetime import datetime
from functools import reduce

from braces.views import LoginRequiredMixin
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError, ObjectDoesNotExist
from django.core.files.base import ContentFile
from django.core.files.storage import FileSystemStorage
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template import loader
from django.template.defaultfilters import pluralize
from djtools.utils.response import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.decorators import method_decorator
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from formtools.wizard.views import SessionWizardView

from comum.models import Configuracao, User
from comum.utils import get_setor, get_uo, get_values_from_choices, get_sigla_reitoria
from conectagov_pen.api_pen_services import barramento_disponivel
from conectagov_pen.models import TramiteBarramento
from djtools import layout
from djtools.forms import ModelForm
from djtools.tables import PagedFilteredTableView
from djtools.templatetags.filters import in_group
from djtools.utils import JsonResponse, breadcrumbs_add, breadcrumbs_previous_url, documento, permission_required, \
    render
from djtools.utils import group_required
from djtools.utils.deprecation import deprecated
from djtools.views import httprr, rtr
from documento_eletronico.assinar_documento import hash_bytestr_iter
from documento_eletronico.forms import (
    ListarDocumentosTextoForm, AssinarDocumentoForm, PapelForm,
    DocumentoAlterarNivelAcessoForm, AssinarDocumentoGovBRForm
)
from documento_eletronico.models import (
    Documento,
    RegistroAcaoDocumento,
    DocumentoTexto,
    DocumentoDigitalizado,
    DocumentoStatus,
    RegistroAcaoDocumentoDigitalizado,
    TipoDocumento,
    TipoConferencia,
    SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa,
    HipoteseLegal,
    NivelAcesso as NivelAcessoEnum,
    NivelPermissao,
    CompartilhamentoSetorPessoa,
    DocumentoTextoPessoal,
    DocumentoDigitalizadoPessoal
)
from documento_eletronico.status import NivelAcesso
from documento_eletronico.utils import EstagioProcessamentoVariavel, gerar_hash, get_variaveis, \
    processar_template_ckeditor
from documento_eletronico.views import get_or_create_balizadora, get_documento_or_forbidden, get_documento_digitalizado, registrar_acao_documento_texto
from processo_eletronico import tasks
from processo_eletronico.exceptions import ProcessoEletronicoException
from processo_eletronico.forms import (
    AdicionarComentario,
    AnexarProcessosForm,
    ApensarProcessosForm,
    CancelarCienciaForm,
    CancelarSolicitacaoJuntadaForm,
    CienciaForm,
    ConcluirSolicitacaoForm,
    DeferirDespachoFormFactory,
    DeferirSolicitacaoJuntadaDocumentoForm,
    DesapensarProcessoForm,
    DesapensarTodosProcessosForm,
    DocumentoDigitalizadoProcessoRemoverForm,
    DocumentoDigitalizadoRequerimentoEditarForm,
    DocumentoDigitalizadoRequerimentoForm,
    DocumentoTextoProcessoRemoverForm,
    DocumentoUploadEditarForm,
    DocumentoUploadForm,
    FiltroCaixaEntradaSaidaForm,
    FinalizarRequerimentoForm,
    ListarDocumentoDigitalizadoProcessoForm,
    ListarDocumentoTextoProcessoForm,
    MotivoSolicitacaoDocumentoForm,
    PedidoJuntadaForm,
    PrioridadeTramiteForm,
    ProcessoFormArquivado,
    ProcessoFormDesfinalizar,
    ProcessoFormEditarInteressados,
    ProcessoFormFinalizar,
    ProcessoMinutaRemoverForm,
    RejeitarSolicitacaoDespachoForm,
    RelacionarProcessosForm,
    RequerimentoFormCadastrar,
    SenhaForm,
    SolicitacaoAssinaturaComAnexacaoProcessoForm,
    SolicitacaoCienciaForm,
    SolicitacaoDespachoFormFactory,
    TramiteFormEncaminharFactory,
    TramiteFormEncaminharViaBarramento,
    ProcessoFormAlterarNivelAcesso,
    BuscaProcessoEletronicoManutencaoForm,
    BuscaProcessoEletronicoManutencaoAlteraStatusForm,
    GerenciarCompartilhamentoProcessoForm,
    GerenciarCompartilhamentoPoderChefeProcessoForm,
    ConsultaPublicaProcessoForm,
    AdicionarRotuloForm,
    AtribuirProcessoForm,
    BuscaProcessoForm, ClonarMinutaForm, ConfiguracaoInstrucaoNivelAcessoForm,
    ConfirmarIndeferimentoForm, ConfirmarDeferimentoForm, ProcessoEditarAssuntoForm, CienciaGovBRForm
)
from processo_eletronico.models import (
    MSG_NAO_POSSUI_ACESSO_CAIXA_PROCESSO,
    Anexacao,
    Apensamento,
    AssinaturaTramite,
    ComentarioProcesso,
    DocumentoDigitalizadoProcesso,
    DocumentoDigitalizadoRequerimento,
    DocumentoProcesso,
    DocumentoTextoProcesso,
    DocumentoTextoRequerimento,
    Minuta,
    ModeloDespacho,
    ModeloParecer,
    ParecerDocumentoDigitalizado,
    ParecerDocumentoTexto,
    ParecerSimples,
    PrioridadeTramite,
    Processo,
    ProcessoMinuta,
    RegistroAcaoProcesso,
    Requerimento,
    SolicitacaoAssinaturaComAnexacaoProcesso,
    SolicitacaoCiencia,
    SolicitacaoDespacho,
    SolicitacaoJuntada,
    CompartilhamentoProcessoEletronicoSetorPessoa,
    CompartilhamentoProcessoEletronicoPoderDeChefe,
    SolicitacaoJuntadaDocumento,
    SolicitacaoStatus,
    TipoProcesso,
    Tramite,
    TramiteDistribuicao,
    DocumentoDigitalizadoRequerimentoOutros, ConfiguracaoInstrucaoNivelAcesso, SolicitacaoAlteracaoNivelAcesso
)
from processo_eletronico.models import NumerosProcessoEletronicoPorSetor, NumerosProcessoEletronicoGeral, \
    NumerosProcessoEletronicoPorTipo, NumerosProcessoEletronicoTempoPorTipo
from processo_eletronico.status import CienciaStatus, ProcessoStatus, SolicitacaoJuntadaStatus, \
    SolicitacaoJuntadaDocumentoStatus
from processo_eletronico.tables import ProcessoFilter, ProcessoFilterFormHelper, ProcessoTable
from processo_eletronico.utils import get_datetime_now, setores_que_sou_chefe_ou_tenho_poder_de_chefe, \
    iniciar_gerenciamento_compartilhamento, setores_que_sou_chefe, MSG_PERMISSAO_NEGADA_PROCESSO_CONSULTA_PUBLICA
from rh.models import Setor
from .utils import Notificar

from djtools.templatetags.filters import format_datetime


@layout.servicos_anonimos()
def servicos_anonimos(request):
    servicos_anonimos = list()

    # servicos_anonimos.append(dict(categoria='Consultas', url="/processo_eletronico/consulta_publica/", icone="file",
    #                               titulo='Processos Eletrônicos'))

    return servicos_anonimos


# @layout.quadro('Processos Eletrônicos', icone='file')
# def index_quadros(quadro, request):
#     today = get_datetime_now()
#     usuario = request.user
#     pessoa_fisica = usuario.get_profile()
#     setores_visiveis = Tramite.get_todos_setores(user=usuario)
#
#     solicitacoes_acesso = SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa.objects.filter(
#         status_solicitacao=SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa.STATUS_AGUARDANDO,
#         documento__dono_documento=pessoa_fisica
#     )
#     qtd = solicitacoes_acesso.count()
#     if qtd:
#         quadro.add_item(
#             layout.ItemContador(
#                 titulo=f'Solicitaç{pluralize(qtd,"ão,ões")} de Compartilhamento', subtitulo=f'Pendente{pluralize(qtd)}s', qtd=qtd,
#                 url='/admin/processo_eletronico/processo/?opcao=5'
#             )
#         )
#
#     if not usuario.eh_aluno:
#         ciencias_pendentes = SolicitacaoCiencia.objects.filter(solicitado=pessoa_fisica,
#                                                                status=CienciaStatus.STATUS_ESPERANDO)
#         qtd = ciencias_pendentes.count()
#         if qtd:
#             quadro.add_item(
#                 layout.ItemContador(titulo=f'Solicitaç{pluralize(qtd, "ão,ões")} de Ciência', subtitulo=f'Pendente{pluralize(qtd)}',
#                                     qtd=qtd, url='/admin/processo_eletronico/processo/?opcao=3')
#             )
#
#         despachos_pendentes = SolicitacaoDespacho.objects.solicitacao_pendente(pessoa=pessoa_fisica)
#         qtd = despachos_pendentes.count()
#         if qtd:
#             quadro.add_item(
#                 layout.ItemContador(
#                     titulo=f'Despacho{pluralize(qtd)}', subtitulo=f'Pendente{pluralize(qtd)}', qtd=qtd,
#                     url='admin/processo_eletronico/processo/?opcao=4'
#                 )
#             )
#
#         solicitacoes_pendentes = SolicitacaoJuntada.objects.filter(solicitado=pessoa_fisica,
#                                                                    status=SolicitacaoJuntadaStatus.STATUS_ESPERANDO,
#                                                                    data_limite__gte=today.date())
#         qtd = solicitacoes_pendentes.count()
#         if qtd:
#             quadro.add_item(
#                 layout.ItemContador(
#                     titulo=f'Solicitaç{pluralize(qtd, "ão,ões")} de Juntada de Documentos', subtitulo=f'Pendente{pluralize(qtd)}',
#                     qtd=qtd, url='/admin/processo_eletronico/processo/?opcao=6'
#                 )
#             )
#
#         solicitacoes_aguardando_avaliacao = SolicitacaoJuntadaDocumento.objects.filter(
#             status=SolicitacaoJuntadaDocumentoStatus.STATUS_ESPERANDO,
#             solicitacao_juntada__tramite__processo__status=ProcessoStatus.STATUS_EM_HOMOLOGACAO,
#             solicitacao_juntada__tramite__processo__setor_atual__in=setores_visiveis,
#         ).exclude(solicitacao_juntada__solicitado=pessoa_fisica)
#         qtd = solicitacoes_aguardando_avaliacao.count()
#         if qtd:
#             quadro.add_item(
#                 layout.ItemContador(
#                     titulo=f'Solicitaç{pluralize(qtd, "ão,ões")} de Juntada de Documento{pluralize(qtd)}',
#                     subtitulo='Aguardando avaliação',
#                     qtd=qtd,
#                     url='/processo_eletronico/caixa_processos/?tab=aguardando-validacao-juntada&setor=todos',
#                 )
#             )
#
#     if request.user.has_perm('processo_eletronico.pode_tramitar_processos_eletronicos'):
#         for setor in setores_visiveis:
#             processos_aguardando_recebimento = Tramite.get_caixa_entrada(setores=[setor]).filter(
#                 data_hora_recebimento__isnull=True)
#             qtd = processos_aguardando_recebimento.count()
#             if qtd:
#                 quadro.add_item(
#                     layout.ItemIndicador(
#                         grupo=f'{setor}',
#                         titulo='A receber',
#                         qtd=qtd,
#                         icone="reply",
#                         classname="success",
#                         url=f'/processo_eletronico/caixa_processos/?tab=a-receber&setor={setor.pk}',
#                     )
#                 )
#
#             processos_aguardando_encaminhamento = Tramite.get_caixa_entrada(setores=[setor]).filter(
#                 data_hora_recebimento__isnull=False)
#             qtd = processos_aguardando_encaminhamento.count()
#             if qtd:
#                 quadro.add_item(
#                     layout.ItemIndicador(
#                         grupo=f'{setor}',
#                         titulo='A encaminhar',
#                         qtd=qtd,
#                         icone="share",
#                         classname="info",
#                         url=f'/processo_eletronico/caixa_processos/?tab=a-encaminhar&setor={setor.pk}',
#                     )
#                 )
#
#     if request.user.has_perm('processo_eletronico.add_processo'):
#         quadro.add_item(
#             layout.ItemAcessoRapido(titulo='Processo', icone='plus', url='/admin/processo_eletronico/processo/add/',
#                                     classe='success'))
#
#     if request.user.has_perm('processo_eletronico.pode_abrir_requerimento'):
#         quadro.add_item(layout.ItemAcessoRapido(titulo='Requerimento', icone='plus',
#                                                 url=reverse('cadastrar_requerimento'), classe='success'))
#
#     if request.user.has_perm('processo_eletronico.pode_tramitar_processos_eletronicos'):
#         quadro.add_item(layout.ItemAcessoRapido(titulo='Caixa de Processos', icone='mail-bulk',
#                                                 url=reverse('selecao_caixa_processos')))
#
#     if request.user.has_perm('processo_eletronico.view_processo'):
#         quadro.add_item(layout.ItemAcessoRapido(titulo='Todos os Processos', icone='bars',
#                                                 url='/admin/processo_eletronico/processo/'))
#
#         quadro.add_item(layout.BuscaRapida(titulo='Processo Eletrônico', url=reverse('busca_processo')))
#
#     return quadro
#
#
# @layout.quadro('Documentos e Processos Eletrônicos', icone='file')
# def index_quadros_nivel_acesso(quadro, request):
#     qtd = SolicitacaoAlteracaoNivelAcesso.qtd_solicitacoes_em_aberto_que_posso_analisar(request.user)
#     if qtd > 0:
#         quadro.add_item(
#             layout.ItemContador(
#                 titulo='Solicitações de alteração de nível de acesso', subtitulo='Pendentes que posso analisar', qtd=qtd,
#                 url='/admin/processo_eletronico/solicitacaoalteracaonivelacesso/?agrupamento=que_posso_analisar'
#             )
#         )
#
#     return quadro


def registrar_acao_documento_digitalizado(request, documento, tipo_acao, observacao=''):
    if tipo_acao in [RegistroAcaoDocumento.TIPO_VISUALIZACAO,
                     RegistroAcaoDocumento.TIPO_IMPRESSAO] and documento.nivel_acesso == DocumentoTexto.NIVEL_ACESSO_PUBLICO:
        return

    RegistroAcaoDocumentoDigitalizado.objects.create(tipo=tipo_acao, documento=documento,
                                                     ip=request.META.get('REMOTE_ADDR', ''), observacao=observacao)


def registrar_acao(request, processo, tipo_acao, observacao=''):
    if tipo_acao in [RegistroAcaoProcesso.TIPO_VISUALIZACAO,
                     RegistroAcaoProcesso.TIPO_IMPRESSAO] and processo.nivel_acesso == Processo.NIVEL_ACESSO_PUBLICO:
        return

    RegistroAcaoProcesso.objects.create(tipo=tipo_acao, processo=processo, ip=request.META.get('REMOTE_ADDR', ''),
                                        observacao=observacao)


def pode_visualizar_minuta(user, minuta):
    pode_editar_algum_processo = False
    pessoa = user.get_profile()
    for processo in Processo.objects.filter(pk__in=minuta.processominuta_set.values_list('processo', flat=True)):
        # Se houver uma solicitação de despacho pendente para o usuário, então ele poderá ver a minuta.
        solicitacao_despacho_pendente = SolicitacaoDespacho.objects.solicitacao_pendente(pessoa, processo.id)
        if solicitacao_despacho_pendente.exists() or processo.pode_editar(user):
            pode_editar_algum_processo = True
            break
    #
    if not minuta.pode_ler(user) and not pode_editar_algum_processo:
        return False
    return True


def gerar_minuta(documento):
    return Minuta.objects.get_or_create(
        cabecalho=documento.cabecalho_para_visualizacao,
        corpo=documento.corpo_para_visualizacao,
        rodape=documento.rodape_para_visualizacao,
        assunto=documento.assunto,
        documento=documento,
    )


def verifica_pode_editar_processo(processo):
    if not processo.pode_editar():
        raise PermissionDenied()


def verifica_pode_alterar_nivel_acesso(processo, user=None):
    if not processo.pode_alterar_nivel_acesso(user):
        raise PermissionDenied()


def verifica_pode_remover_documento_do_processo(processo):
    if processo.tem_tramite_externo():
        raise PermissionDenied()


def get_processo(processo_id_uuid, acesso_publico):
    if acesso_publico:
        return get_object_or_404(Processo, uuid=processo_id_uuid)

    return get_object_or_404(Processo, pk=processo_id_uuid)


def get_tramite(tramite_id_uuid, acesso_publico):
    if acesso_publico:
        return get_object_or_404(Tramite, uuid=tramite_id_uuid)

    return get_object_or_404(Tramite, id=tramite_id_uuid)


def get_minuta(id_uuid, acesso_publico):
    if acesso_publico:
        return get_object_or_404(Minuta, uuid=id_uuid)

    return get_object_or_404(Minuta, id=id_uuid)


def get_parecer_simples(id_uuid, acesso_publico):
    if acesso_publico:
        return get_object_or_404(ParecerSimples, uuid=id_uuid)

    return get_object_or_404(ParecerSimples, id=id_uuid)


@login_required()
def busca_processo(request):
    consulta = request.GET.get('q')
    try:
        url = Processo.objects.get(numero_protocolo_fisico=consulta).get_absolute_url()
    except Processo.DoesNotExist:
        try:
            url = Processo.objects.get(numero_protocolo=consulta).get_absolute_url()
        except Processo.DoesNotExist:
            url = "/admin/processo_eletronico/processo/?q={}".format(consulta)
    return httprr(url)


@login_required()
def processo(request, processo_id):
    # Dados iniciais
    # -----------------------------
    instance = get_object_or_404(Processo, pk=processo_id)
    try:
        instance = Processo.atualizar_status_processo(instance)
    except ValidationError as e:
        messages.error(request, str(e))
    pessoa = request.user.get_profile()

    # Verifica se o usuario pode ler o processo, senao puder sera PermissionDenied()
    # -----------------------------
    pode_ler = instance.pode_ler(user=request.user, lancar_excecao=True)

    # Calcula os metadados do processo
    # ------------------------

    user = request.user
    is_superuser = user.is_superuser
    metadados_processo = None
    if is_superuser:
        metadados_processo = instance.get_metadados()

    # Se o processo tiver aguardando a ciencia do user sera redirecionado diretamente para o a tela de ciencia
    # -----------------------------
    if instance.get_ciencia_pendente(pessoa):
        return dar_ciencia(request, instance.id)

    # Anexacao
    # -----------------------------
    if instance.status == ProcessoStatus.STATUS_ANEXADO:
        processo_pk = Anexacao.objects.filter(processo_anexado_id=processo_id).values_list('processo_anexador__id',
                                                                                           flat=True)
        return processo(request, processo_pk.first())

    # Verifica as permissoes para montagem da tela
    # -----------------------------
    despacho_visualizar_botao_verificar_integridade = is_superuser or in_group(
        request.user, ['Gerente Sistêmico de Processo Eletrônico', 'processo_eletronico Administrador']
    )
    documento_visualizar_botao_verificar_integridade = is_superuser or in_group(
        request.user, ['Gerente Sistêmico de Documento Eletrônico', 'documento_eletronico Administrador']
    )

    processo_pode_ser_encaminhado = instance.pode_ser_encaminhado(remetente_user=user)
    processo_pode_ser_recebido = instance.pode_ser_recebido()
    processo_ultimo_tramite_pode_ser_removido = instance.ultimo_tramite_pode_ser_removido()
    instance.pode_anexar = instance.pode_anexar(user)
    instance.pode_apensar = instance.pode_apensar(user)
    instance.pode_desfinalizar = instance.pode_desfinalizar(user)

    # Documentos do processo
    # -----------------------------
    # Documentos Ativos no processo
    documentos_do_processo = instance.get_todos_documentos_processo()
    quantidade_documentos_processo = len(documentos_do_processo)
    # Documentos Removidos do processo
    documentos_removidos_processo = instance.get_documentos_removidos()
    quantidade_documentos_removidos = documentos_removidos_processo.count()

    # Processos Apensados, Anexados e Relacionados
    processos_apensados = instance.get_processos_apensados()
    quantidade_processos_apensados = processos_apensados.count()

    # Retorna registros da entidade Anexacao
    processos_anexados = instance.get_anexos()
    quantidade_processos_anexados = processos_anexados.count()
    processos_relacionados = instance.processos_relacionados.all()
    quantidade_processos_relacionados = processos_relacionados.count()

    quantidade_processos_apensados_anexados_relacionados = quantidade_processos_apensados + quantidade_processos_anexados + quantidade_processos_relacionados

    documentos_aguardando_para_serem_anexados = instance.get_documentos_aguardando_para_serem_anexados()
    quantidade_documentos_aguardando_para_serem_anexados = documentos_aguardando_para_serem_anexados.count()

    documentos_aguardando_assinatura_para_serem_anexados = instance.get_documentos_aguardando_assinatura_para_serem_anexados()
    quantidade_documentos_aguardando_assinatura_para_serem_anexados = documentos_aguardando_assinatura_para_serem_anexados.count()
    total_documentos_processo = (
        quantidade_documentos_processo + quantidade_documentos_removidos or quantidade_documentos_aguardando_assinatura_para_serem_anexados
    )
    solicitacoes_ciencia = instance.solicitacoes_ciencia()
    quantidade_solicitacoes_ciencia = solicitacoes_ciencia.count()
    solicitacao_despachos = instance.solicitacaodespacho_set.all()
    quantidade_solicitacao_despachos = solicitacao_despachos.count()
    solicitacoes_juntada_documento = instance.solicitacoes_juntada_documento()
    quantidade_solicitacoes_juntada_documento = solicitacoes_juntada_documento.count()
    solicitacoes_acesso = SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa.objects.filter(documento__documentodigitalizadoprocesso__processo=instance)
    quantidade_solicitacoes_acesso = solicitacoes_acesso.count()
    quantidade_solicitacoes = (
        quantidade_solicitacoes_ciencia + quantidade_solicitacao_despachos + quantidade_solicitacoes_juntada_documento + quantidade_solicitacoes_acesso
    )

    minutas = instance.get_minutas()
    quantidade_minutas = minutas.count()
    minutas_removidas = instance.get_minutas_removidas()
    quantidade_minutas_removidas = minutas_removidas.count()

    usuario_pode_tramitar_barramento = request.user.has_perm('conectagov_pen.pode_tramitar_pelo_barramento') and instance.setor_atual

    # Só exibe se o usuário logao puder analisar as solicitações de alteracao de nivel de acesso
    existe_solicitacao_em_aberto_processo = instance.existe_solicitacoes_nivel_acesso_aberto() and instance.pode_alterar_nivel_acesso(user)

    # Verifica se existem solicitações de alteracao de nivel de acesso para documentos digitalizados
    processos_docs_digit = DocumentoDigitalizadoProcesso.objects.filter(processo=instance)
    existe_solicitacao_em_aberto_documento_digitalizado = False
    for pd in processos_docs_digit:
        if pd.documento.existe_solicitacoes_nivel_acesso_aberto() and pd.documento.pode_alterar_nivel_acesso(user):
            messages.info(request, 'Existem solicitações de alteração de nível de acesso em aberto para um ou mais documentos digitalizados deste processo. Para analisar as solicitações você deve acessar a opção "Editar Nível de Acesso" do documento.')
            existe_solicitacao_em_aberto_documento_digitalizado = True
            break

    # Dados do template
    # -----------------------------
    title = 'Processo {}'.format(instance)
    template = loader.get_template('processo_eletronico/processo.html')
    context = {
        'title': title,
        'processo': instance,
        'processo_pode_ser_encaminhado': processo_pode_ser_encaminhado,
        'processo_pode_ser_recebido': processo_pode_ser_recebido,
        'processo_ultimo_tramite_pode_ser_removido': processo_ultimo_tramite_pode_ser_removido,
        'despacho_visualizar_botao_verificar_integridade': despacho_visualizar_botao_verificar_integridade,
        'documento_visualizar_botao_verificar_integridade': documento_visualizar_botao_verificar_integridade,
        'documentos_removidos_processo': documentos_removidos_processo,
        'documentos_aguardando_assinatura_para_serem_anexados': documentos_aguardando_assinatura_para_serem_anexados,
        'quantidade_documentos_aguardando_assinatura_para_serem_anexados': quantidade_documentos_aguardando_assinatura_para_serem_anexados,
        'documentos_do_processo': documentos_do_processo,
        'quantidade_documentos_processo': quantidade_documentos_processo,
        'total_documentos_processo': total_documentos_processo,
        'processos_apensados': processos_apensados,
        'quantidade_processos_apensados': processos_apensados,
        'processos_anexados': processos_anexados,
        'quantidade_processos_anexados': quantidade_processos_anexados,
        'processos_relacionados': processos_relacionados,
        'quantidade_processos_relacionados': quantidade_processos_relacionados,
        'quantidade_processos_apensados_anexados_relacionados': quantidade_processos_apensados_anexados_relacionados,
        'documentos_aguardando_para_serem_anexados': documentos_aguardando_para_serem_anexados,
        'quantidade_documentos_aguardando_para_serem_anexados': quantidade_documentos_aguardando_para_serem_anexados,
        # Minutas
        'minutas': minutas,
        'quantidade_minutas': quantidade_minutas,
        'minutas_removidas': minutas_removidas,
        'quantidade_minutas_removidas': quantidade_minutas_removidas,
        # Solicitações
        'solicitacoes_ciencia': solicitacoes_ciencia,
        'quantidade_solicitacoes_ciencia': quantidade_solicitacoes_ciencia,
        'solicitacao_despachos': solicitacao_despachos,
        'quantidade_solicitacao_despachos': quantidade_solicitacao_despachos,
        'solicitacoes_acesso': solicitacoes_acesso,
        'quantidade_solicitacoes_acesso': quantidade_solicitacoes_acesso,
        'quantidade_solicitacoes': quantidade_solicitacoes,
        'processo_eletronico_manutencao': processo_eletronico_manutencao,
        'usuario_pode_tramitar_barramento': usuario_pode_tramitar_barramento,
        'pode_ler': pode_ler,
        'is_superuser': is_superuser,
        'metadados_processo': metadados_processo,
        'existe_solicitacao_em_aberto_processo': existe_solicitacao_em_aberto_processo,
        'existe_solicitacao_em_aberto_documento_digitalizado': existe_solicitacao_em_aberto_documento_digitalizado,
        'eh_usuario_externo': pessoa.get_vinculo().eh_usuario_externo(),
        'ultimo_tramite': instance.ultimo_tramite,
        'quantidade_solicitacoes_juntada_documento': quantidade_solicitacoes_juntada_documento,
        'solicitacoes_juntada_documento': solicitacoes_juntada_documento,
        'quantidade_documentos_removidos': quantidade_documentos_removidos
    }
    breadcrumbs_add(request, context)
    registrar_acao(request, instance, RegistroAcaoProcesso.TIPO_VISUALIZACAO)
    return HttpResponse(template.render(context, request))


# TODO: Substituir a rotina abaixo pelo método adicionar_documento de Processo.
@login_required()
@transaction.atomic()
def adicionar_documento_processo(request, processo_id, documento_id):
    processo = get_object_or_404(Processo, pk=processo_id)
    verifica_pode_editar_processo(processo)

    documento = None
    try:
        documento = get_documento_or_forbidden(request.user, documento_id)
    except Exception:
        try:
            documento = get_object_or_404(DocumentoDigitalizadoPessoal, pk=documento_id)
        except Exception:
            raise Http404()

    if processo.get_apensamento() and documento.nivel_acesso == Documento.NIVEL_ACESSO_SIGILOSO:
        raise PermissionDenied

    if DocumentoTextoProcesso.objects.filter(processo_id=processo.id, documento_id=documento.id).exclude(
            data_hora_remocao__isnull=False).exists():
        return httprr('/processo_eletronico/processo/{:d}/'.format(processo.id),
                      'O documento {} já pertence a este processo.'.format(documento.identificador), tag='warning')

    if documento.eh_documento_texto:
        if not documento.estah_finalizado:
            raise PermissionDenied
        if DocumentoTextoProcesso.objects.filter(processo_id=processo.id, documento_id=documento.id).exclude(data_hora_remocao__isnull=False).exists():
            return httprr('/processo_eletronico/processo/{:d}/'.format(processo.id), 'O documento {} já pertence a este processo.'.format(documento.identificador), tag='warning')

        documento_processo = DocumentoTextoProcesso(processo=processo, documento=documento)
        documento_processo.save()
        obs = f'Documento adicionado ao processo {processo}.'
        registrar_acao_documento_texto(request, documento, RegistroAcaoDocumento.TIPO_ADICAO_EM_PROCESSO, obs)

    else:
        if DocumentoDigitalizadoProcesso.objects.filter(processo_id=processo.id, documento_id=documento.id).exclude(data_hora_remocao__isnull=False).exists():
            return httprr('/processo_eletronico/processo/{:d}/'.format(processo.id), 'O documento {} já pertence a este processo.'.format(documento.assunto), tag='warning')

        documento_processo = DocumentoDigitalizadoProcesso(processo=processo, documento=documento)
        documento_processo.save()
        obs = f'Documento removido do processo {processo}.'
        registrar_acao_documento_digitalizado(request, documento, RegistroAcaoDocumento.TIPO_REMOCAO_EM_PROCESSO, obs)

    return httprr('/processo_eletronico/processo/{:d}/'.format(processo.id), 'Documento adicionado com sucesso.')


@rtr()
@login_required()
@transaction.atomic()
def adicionar_processo_minuta(request, processo_id, documento_id):
    processo = get_object_or_404(Processo, pk=processo_id)
    verifica_pode_editar_processo(processo)
    documento = DocumentoTexto.objects.get(pk=documento_id)
    title = 'Adicionar Minuta do {} ao Processo {}'.format(documento, processo)

    if processo.get_apensamento() and documento.nivel_acesso == Documento.NIVEL_ACESSO_SIGILOSO:
        raise PermissionDenied

    form = SenhaForm(request.POST or None, request=request)

    if form.is_valid():
        minuta, _ = gerar_minuta(documento)
        url = reverse_lazy('processo', current_app='processo_eletronico', kwargs={'processo_id': processo.id})
        found = ProcessoMinuta.objects.filter(minuta=minuta, processo=processo, data_hora_remocao__isnull=True).exists()
        if not found:
            processo_minuta = ProcessoMinuta(minuta=minuta, processo=processo)
            processo_minuta.save()

            return httprr(url, 'Minuta adicionada com sucesso.')
        #
        return httprr(url, 'Uma versão da minuta encontra-se presente no processo.', tag='warn')
    return locals()


@rtr()
@login_required()
def remover_documento_texto_processo(request, documento_processo_id):
    documento_processo = get_object_or_404(DocumentoTextoProcesso, pk=documento_processo_id)
    verifica_pode_editar_processo(documento_processo.processo)
    verifica_pode_remover_documento_do_processo(documento_processo.processo)
    title = 'Desentranhamento do Documento {} do Processo {}'.format(documento_processo.documento,
                                                                     documento_processo.processo)
    form = DocumentoTextoProcessoRemoverForm(data=request.POST or None, instance=documento_processo, user=request.user)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            observacao = f'Documento removido do processo {documento_processo.documento}.'
            registrar_acao_documento_texto(request, documento_processo.documento, RegistroAcaoDocumento.TIPO_REMOCAO_EM_PROCESSO, observacao=observacao)
            return httprr('..', 'Documento removido com sucesso.')

    return locals()


@rtr()
@login_required()
def remover_documento_digitalizado_processo(request, documento_processo_id):
    documento_processo = get_object_or_404(DocumentoDigitalizadoProcesso, pk=documento_processo_id)
    verifica_pode_editar_processo(documento_processo.processo)
    verifica_pode_remover_documento_do_processo(documento_processo.processo)
    title = 'Desentranhamento do Documento {} do Processo {}'.format(documento_processo.documento,
                                                                     documento_processo.processo)
    form = DocumentoDigitalizadoProcessoRemoverForm(data=request.POST or None, instance=documento_processo,
                                                    user=request.user)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            registrar_acao_documento_digitalizado(
                request, documento_processo.documento, RegistroAcaoDocumento.TIPO_REMOCAO_EM_PROCESSO,
                'Documento removido do processo {}.'.format(documento_processo.processo)
            )
            return httprr('..', 'Documento removido com sucesso.')

    return locals()


@rtr()
@login_required()
def remover_minuta_processo(request, minuta_processo_id):
    processo_minuta = get_object_or_404(ProcessoMinuta, pk=minuta_processo_id)
    verifica_pode_editar_processo(processo_minuta.processo)
    title = 'Desentranhamento da {} do Processo {}'.format(processo_minuta.minuta, processo_minuta.processo)
    form = ProcessoMinutaRemoverForm(data=request.POST or None, instance=processo_minuta, request=request)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return httprr('..', 'Minuta removida com sucesso.')

    return locals()


@rtr('ver_justificativa_remocao.html')
@login_required()
def ver_justificativa_remocao_documento(request, pk):
    try:
        instance = DocumentoTextoProcesso.objects.get(pk=pk)
    except ObjectDoesNotExist:
        instance = get_object_or_404(DocumentoDigitalizadoProcesso, pk=pk)
    title = 'Visualização da Justificativa de Remoção do Documento {}'.format(instance.documento)
    # verifica_pode_ver_processo(request.user, instance.processo_id)
    processo = get_object_or_404(Processo, id=instance.processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    return locals()


@rtr('ver_justificativa_remocao.html')
@login_required()
def ver_justificativa_remocao_minuta(request, pk):
    instance = get_object_or_404(ProcessoMinuta, pk=pk)
    title = 'Visualização da Justificativa de Remoção da Minuta {}'.format(instance.minuta)
    # verifica_pode_ver_processo(request.user, instance.processo_id)
    processo = get_object_or_404(Processo, id=instance.processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    return locals()


@rtr()
@login_required()
def listar_documentos_adicionar(request, processo_id, view_action='adicionar_documento_processo', solicitacao=None):
    processo = get_object_or_404(Processo, pk=processo_id)

    title = 'Documentos que podem ser adicionados ao processo {}'.format(processo)

    is_adicionar_documento_processo = True

    # Usado no link de adicionar ao processo/reuerimento
    url_add_documento = reverse_lazy('requerimentos', current_app='processo_eletronico')
    label_add_documento = 'Adicionar ao processo'

    servidor = User.objects.get(username=request.user.username)
    setor_processo = processo.setor_atual
    initial = None
    data = request.GET.copy()
    data.pop('tab', None)
    if setor_processo and setor_processo.uo and not data:
        data = dict(campus=setor_processo.uo.pk, setor=setor_processo.pk, ano=get_datetime_now().year)
    form = ListarDocumentosTextoForm(data or None, request=request)
    documentos, documentos_compartilhados, params, order_str = form.processar()

    documentos_do_processo_ids = DocumentoTextoProcesso.objects.filter(processo=processo, data_hora_remocao__isnull=True).values_list('documento__id', flat=True)
    documentos_finalizados_ids = DocumentoTexto.objects.filter(status=DocumentoStatus.STATUS_FINALIZADO).values_list('id', flat=True)

    documentos = documentos.exclude(id__in=documentos_do_processo_ids).filter(id__in=documentos_finalizados_ids)

    # Se o processo estiver apensado não pode adicionar documento sigiloso;
    if processo.get_apensamento():
        documentos = documentos.exclude(nivel_acesso=Documento.NIVEL_ACESSO_SIGILOSO)

    # Se ao usuário não foi solicitado nada, verifique permissões
    if not solicitacao:
        verifica_pode_editar_processo(processo)

    instance = solicitacao if solicitacao else processo

    # documentos = documentos.order_by('-identificador_ano', '-identificador_numero', '-identificador_tipo_documento_sigla', 'identificador_setor_sigla')

    # Lista os documentos pessoais
    documentos_pessoais = DocumentoTextoPessoal.objects.proprios(request.user).defer('cabecalho', 'rodape', 'corpo')
    documentos_pessoais = documentos_pessoais.filter(status=DocumentoStatus.STATUS_FINALIZADO)
    documentos_pessoais = documentos_pessoais.exclude(id__in=documentos_do_processo_ids)
    #
    documentos_pessoais_digitalizados = DocumentoDigitalizadoPessoal.objects.filter(usuario_criacao=request.user)
    documentos_do_processo_ids_pesoais = DocumentoDigitalizadoProcesso.objects.filter(processo=processo, data_hora_remocao__isnull=True).values_list('documento__id', flat=True)
    documentos_pessoais_digitalizados = documentos_pessoais_digitalizados.exclude(id__in=documentos_do_processo_ids_pesoais)

    documentos = documentos.order_by('-data_ultima_modificacao')

    return locals()


@rtr()
@login_required()
def vincular_parecer(request, processo_minuta_id):
    processo_minuta = get_object_or_404(ProcessoMinuta, pk=processo_minuta_id)
    verifica_pode_editar_processo(processo_minuta.processo)
    title = 'Documentos do Processo {}'.format(processo_minuta.processo)
    form = ListarDocumentoTextoProcessoForm(request.POST or None, processo_minuta=processo_minuta, request=request)
    if form.is_valid():
        parecer = form.cleaned_data.get('parecer')
        ParecerDocumentoTexto.objects.get_or_create(processo_minuta=processo_minuta, parecer=parecer)
        url = reverse_lazy('processo', current_app='processo_eletronico',
                           kwargs={'processo_id': processo_minuta.processo_id})
        return httprr(url, 'Parecer {} vinculado a minuta {} com sucesso.'.format(processo_minuta.minuta,
                                                                                  processo_minuta.processo))
    return locals()


@rtr()
@login_required()
def anexar_parecer(request, processo_minuta_id):
    processo_minuta = get_object_or_404(ProcessoMinuta, pk=processo_minuta_id)
    verifica_pode_editar_processo(processo_minuta.processo)
    title = 'Documentos do Processo {}'.format(processo_minuta.processo)
    form = ListarDocumentoDigitalizadoProcessoForm(request.POST or None, processo_minuta=processo_minuta,
                                                   request=request)
    if form.is_valid():
        parecer = form.cleaned_data.get('parecer')
        ParecerDocumentoDigitalizado.objects.get_or_create(processo_minuta=processo_minuta, parecer=parecer)
        url = reverse_lazy('processo', current_app='processo_eletronico',
                           kwargs={'processo_id': processo_minuta.processo_id})
        return httprr(url, 'Parecer {} vinculado a minuta {} com sucesso.'.format(processo_minuta.minuta,
                                                                                  processo_minuta.processo))
    return locals()


@rtr()
@login_required()
def listar_minutas_adicionar(request, processo_id):
    processo = get_object_or_404(Processo, pk=processo_id)
    verifica_pode_editar_processo(processo)
    title = 'Minutas que podem ser adicionadas ao processo {}'.format(processo)

    form = ListarDocumentosTextoForm(request.GET or None, request=request)
    documentos, documentos_compartilhados, params, order_str = form.processar()

    documentos_minutas_ids = DocumentoTexto.objects.filter(status=DocumentoStatus.STATUS_CONCLUIDO).values_list('id',
                                                                                                                flat=True)

    documentos = documentos.filter(id__in=documentos_minutas_ids)
    # Se o processo estiver apensado não pode adicionar documento sigiloso;
    if processo.get_apensamento():
        documentos = documentos.exclude(nivel_acesso=Documento.NIVEL_ACESSO_SIGILOSO)

    documentos = documentos.order_by('identificador_tipo_documento_sigla', 'identificador_numero', 'identificador_ano',
                                     'identificador_setor_sigla')

    return locals()


class ProcessoListView(LoginRequiredMixin, PagedFilteredTableView):
    title = 'Processos'
    model = Processo
    context_object_name = 'processos'
    template_name = 'processo_eletronico/processo_list.html'
    table_class = ProcessoTable
    filter_class = ProcessoFilter
    formhelper_class = ProcessoFilterFormHelper
    paginate_by = 20

    def get_table(self, **kwargs):
        return super().get_table(**self.kwargs)

    def get_queryset(self, **kwargs):
        qs = super().get_queryset().exclude(status=ProcessoStatus.STATUS_ANEXADO)
        processo = get_object_or_404(Processo, pk=self.kwargs['processo_pk'])
        return qs.exclude(id=processo.id)


@rtr('processo_eletronico/processo_padrao.html')
@transaction.atomic()
@login_required()
def processo_encaminhar(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    # Último trâmite realizado por completo.
    processo = get_object_or_404(Processo, pk=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    verifica_pode_editar_processo(processo)
    title = 'Encaminhar Processo {}'.format(processo)
    if not processo.pode_ser_encaminhado():
        return httprr(processo.get_absolute_url(),
                      'A operação não pode ser realizada porque o processo já foi encaminhado.')
    if ModeloDespacho.objects.all().first() is None:
        return httprr(processo.get_absolute_url(),
                      'A operação não pode ser realizada porque um modelo de despacho não foi cadastado.', tag='error')

    # Novo trâmite que se inicia, com base nos dados do último tramite
    # realizado por completo.
    tramite_novo = Tramite()
    tramite_novo.processo = processo
    if request.method == "POST":
        form = TramiteFormEncaminharFactory(tramite=tramite_novo, request_method=request.POST, request=request)
        if form.is_valid():
            form.save()
            Notificar.processo_encaminhado(tramite_novo)
            return httprr(processo.get_absolute_url(), 'Processo encaminhado com sucesso.')
    else:
        form = TramiteFormEncaminharFactory(tramite=tramite_novo, request_method=None, request=request)

    return locals()


@rtr('processo_eletronico/processo_padrao.html')
@transaction.atomic()
@login_required()
def encaminhar_sem_despacho(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    # Último trâmite realizado por completo.
    processo = get_object_or_404(Processo, pk=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    verifica_pode_editar_processo(processo)
    title = 'Encaminhar Processo {}'.format(processo)
    if not processo.pode_ser_encaminhado():
        return httprr(processo.get_absolute_url(),
                      'A operação não pode ser realizada porque o processo já foi encaminhado.')

    tramite_novo = Tramite()
    tramite_novo.processo = processo
    form = TramiteFormEncaminharFactory(tramite=tramite_novo, request_method=request.POST or None, request=request,
                                        despacho=False)
    if form.is_valid():
        form.save()
        Notificar.processo_encaminhado(tramite_novo)
        return httprr(processo.get_absolute_url(), 'Processo encaminhado com sucesso.')
    return locals()


@rtr()
@login_required()
def processo_receber(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    processo = get_object_or_404(Processo, id=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    tramite = processo.ultimo_tramite

    if not processo.pode_ser_recebido():
        return httprr(processo.get_absolute_url(),
                      'A operação não pode ser realizada porque o processo já foi recebido.', tag='error')
    try:
        tramite.receber_processo(pessoa_recebimento=request.user.get_profile(), data_hora_recebimento=datetime.today(),
                                 usuario_recebimento=request.user)
        # coloca processo recebido com prioridade default demanda_497
        PrioridadeTramite.objects.get_or_create(tramite=tramite, prioridade=2, justificativa='')
        return httprr(processo.get_absolute_url(), 'Processo recebido com sucesso.')
    except ValidationError as e:
        return httprr(processo.get_absolute_url(), e.message, tag='error')
    return PermissionDenied


@rtr('processo_eletronico/processo_padrao.html')
@login_required()
def processo_editar_interessados(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    processo = get_object_or_404(Processo, id=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    target = processo.get_absolute_url()
    verifica_pode_editar_processo(processo)
    title = 'Editar Interessados do Processo {}'.format(processo)
    if not processo.esta_ativo():
        return httprr(target, 'O processo não pode ter seus interessados editados porque não está mais em trâmite.',
                      close_popup=True)

    form = ProcessoFormEditarInteressados(request.POST or None, processo=processo, request=request)
    if form.is_valid():
        interessados = form.cleaned_data.get('interessados')
        set_objeto = set(processo.interessados.all())
        set_form = set(interessados)
        if set_objeto != set_form:
            interessados_removidos = set_objeto.difference(set_form)
            interessados_adicionados = set_form.difference(set_objeto)
            observacao = 'Interessados adicionados: {} ; Interessados Removidos: {}. Justificativa: {}'.format(
                ','.join([str(interessado) for interessado in interessados_adicionados]),
                ', '.join([str(interessado) for interessado in interessados_removidos]),
                form.cleaned_data.get('observacao_alteracao_interessados'),
            )

            processo.interessados.set(interessados)
            processo.save()
            registrar_acao(request, processo, RegistroAcaoProcesso.TIPO_EDICAO_INTERESSADOS, observacao)
            return httprr(processo.get_absolute_url(), 'Os interessados do processo foram alterados com sucesso.',
                          close_popup=True)
        return httprr(processo.get_absolute_url(), 'Não houve alteração nos interessados do processo.', tag='alert',
                      close_popup=True)

    return locals()


@rtr('processo_eletronico/registro_acoes_processo.html')
@login_required()
def registro_acoes_processo(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    processo = get_object_or_404(Processo, id=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    title = 'Registros de Ações do Processo {}'.format(processo)
    return locals()


@rtr()
@login_required()
def processo_finalizar(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    processo = get_object_or_404(Processo, id=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    verifica_pode_editar_processo(processo)
    if not processo.pode_finalizar():
        raise PermissionDenied
    title = 'Finalizar Processo {}'.format(processo)
    target = processo.get_absolute_url()
    #
    if bool(processo.get_apensamento()):
        return httprr(target, 'O processo não pode ser finalizado porque está apensado.')

    if not processo.esta_ativo():
        return httprr(target, 'O processo não pode ser finalizado porque não está ativo.')
    #
    form = ProcessoFormFinalizar(request.POST or None, processo=processo, request=request)
    if form.is_valid():
        observacao_finalizacao = form.cleaned_data.get('observacao_finalizacao')
        pdf = imprimir_termo_finalizacao_pdf(request, processo, observacao_finalizacao)
        papel = form.cleaned_data.get('papel', None)
        assunto = f"Termo de Finalização do Processo: {processo.numero_protocolo_fisico}"
        # Adicionei transaction atomic no metodo gerar_termo_finalizacao
        gerar_termo_finalizacao(processo, request.user, papel, assunto, pdf.content)
        form.save()
        registrar_acao(request, processo, RegistroAcaoProcesso.TIPO_FINALIZACAO, observacao_finalizacao)
        Notificar.processo_finalizado(processo)
        return httprr(target, 'Processo finalizado com sucesso.')

    return locals()


@rtr()
@login_required()
def processo_desfinalizar(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    processo = get_object_or_404(Processo, id=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    if not processo.pode_desfinalizar(request.user):
        raise PermissionDenied
    title = 'Remover finalização do Processo {}'.format(processo)
    target = processo.get_absolute_url()
    if not processo.esta_finalizado():
        return httprr(target, 'Não é possível remover a finalização do processo porque o processo não está Finalizado.')

    form = ProcessoFormDesfinalizar(request.POST or None, processo=processo, request=request)
    if form.is_valid():
        observacao_desfinalizacao = form.cleaned_data.get('observacao_desfinalizacao')
        pdf = imprimir_termo_reabertura_pdf(request, processo, observacao_desfinalizacao)
        papel = form.cleaned_data.get('papel', None)
        assunto = f"Termo de Reabertura do Processo: {processo.numero_protocolo_fisico}"
        # Adicionei transaction atomic no metodo gerar_termo_reabertura
        gerar_termo_reabertura(processo, request.user, papel, assunto, pdf.content)
        form.save()
        registrar_acao(request, processo, RegistroAcaoProcesso.TIPO_DESFINALIZACAO, observacao_desfinalizacao)
        Notificar.remocao_finalizacao(processo)
        return httprr(target, 'Processo reaberto com sucesso.')

    return locals()


@rtr()
@login_required()
def processo_arquivar(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    processo = get_object_or_404(Processo, id=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    verifica_pode_editar_processo(processo)
    target = processo.get_absolute_url()
    if not processo.pode_arquivar():
        raise PermissionDenied
    title = 'Arquivar Processo {}'.format(processo)
    if not processo.esta_finalizado():
        return httprr(target, 'O arquivamento só é permitado aos processos finalizados.')

    form = ProcessoFormArquivado(request.POST or None, processo=processo, request=request)
    if form.is_valid():
        form.save()
        Notificar.processo_arquivado(processo)
        return httprr(processo.get_absolute_url(), 'Processo arquivado com sucesso.')

    return locals()


@login_required()
def processo_remover_ultimo_tramite(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)

    processo = get_object_or_404(Processo, id=processo_id)
    try:
        processo.pode_ler(user=request.user, lancar_excecao=True)
        processo.ultimo_tramite_pode_ser_removido(user=request.user, lancar_excecao=True)
        # O próprio método "remover_ultimo_tramite" já verifica se o processo pode ter o último trâmite removido e lança
        # uma exceção caso contrário.
        processo.remover_ultimo_tramite()
        return httprr(processo.get_absolute_url(), 'Último trâmite removido com sucesso.')
    except Exception as e:
        return httprr(processo.get_absolute_url(),
                      'Não foi possível remover o último trâmite. Detalhe: ' + '{}'.format(e))


@rtr('processo_eletronico/tramite_conteudo.html')
def tramite_conteudo(request, tramite_id, acesso_publico=False):
    tramite = get_tramite(tramite_id, acesso_publico)
    assinatura = get_object_or_404(AssinaturaTramite, tramite=tramite).assinatura
    eh_anonimo = request.user.is_anonymous
    if eh_anonimo:
        if not tramite.processo.pode_ler_consulta_publica():
            return httprr('/processo_eletronico/consulta_publica/', message=MSG_PERMISSAO_NEGADA_PROCESSO_CONSULTA_PUBLICA, tag='error')
    else:
        if not tramite.pode_visualizar(request.user):
            raise PermissionDenied()

    agora = datetime.now()

    return locals()


@rtr('processo_eletronico/tramite_visualizar.html')
@login_required()
def tramite_visualizar(request, tramite_id):
    agora = datetime.now()
    tramite = get_object_or_404(Tramite, id=tramite_id)
    if not tramite.pode_visualizar(request.user):
        raise PermissionDenied()
    return locals()


@rtr('processo_eletronico/selecao_caixa_processos.html')
@login_required()
def selecao_caixa_processos(request):
    title = 'Seleção de Caixa de Processos'
    setores_visiveis = Tramite.get_todos_setores(user=request.user)

    if not setores_visiveis:
        raise PermissionDenied(MSG_NAO_POSSUI_ACESSO_CAIXA_PROCESSO)

    setores = []
    total = 0
    for setor in setores_visiveis:
        tramites_de_entrada = Tramite.get_caixa_entrada(setores=[setor]).distinct()
        a_receber = tramites_de_entrada.filter(data_hora_recebimento__isnull=True).count()
        despachos_solicitados = SolicitacaoDespacho.objects.filter(status=SolicitacaoStatus.STATUS_ESPERANDO).filter(
            Q(processo__in=tramites_de_entrada.values_list('processo', flat=True)) | Q(solicitado=request.user.get_profile())
        )
        a_encaminhar = tramites_de_entrada.filter(data_hora_recebimento__isnull=False).exclude(processo__in=despachos_solicitados.values_list('processo', flat=True)).count()
        dict = {'pk': setor.pk, 'sigla': setor.sigla, 'a_receber': a_receber, 'a_encaminhar': a_encaminhar}
        setores.append(dict)
        total += a_receber
        total += a_encaminhar

    return locals()


@rtr('processo_eletronico/caixas.html')
@login_required()
def caixa_processos(request):
    title = 'Caixa de Processos'
    setores_visiveis = Tramite.get_todos_setores(user=request.user)
    if not setores_visiveis:
        raise PermissionDenied(MSG_NAO_POSSUI_ACESSO_CAIXA_PROCESSO)

    setor_escolhido = int(request.GET.get('setor')) if request.GET.get('setor', '') and request.GET.get('setor', '') != 'todos' else None
    servidor_logado_eh_chefe_do_setor = False
    if setor_escolhido:
        servidor_logado_eh_chefe_do_setor = setores_que_sou_chefe_ou_tenho_poder_de_chefe(request.user).filter(
            id=setor_escolhido).exists()

    form = FiltroCaixaEntradaSaidaForm(request.GET, request=request, setores_usuario=setores_visiveis)
    filtros = None
    filtros_processo = None

    if form.is_valid():
        filtros = form.processar()
        filtros_processo = form.processar_processo()

    if not setor_escolhido:
        setores = setores_visiveis
    else:
        setores = setores_visiveis.filter(pk=setor_escolhido)
        setor_escolhido = setores.first()
        if setor_escolhido:
            title = f'{title} {setor_escolhido.sigla}'

    solicitado = request.user.get_profile()

    tramites_de_entrada = Tramite.get_caixa_entrada(setores=setores, filtros=filtros).distinct()
    cx_saida = Tramite.get_caixa_saida(setores=setores, filtros=filtros).exclude(
        tramite_barramento__isnull=False).order_by('data_hora_encaminhamento').distinct()
    cx_saida_externos = Tramite.get_caixa_saida_externos(setores=setores, filtros=filtros).filter(
        tramite_barramento__status=TramiteBarramento.STATUS_ENVIADO)
    cx_saida_aguardando_retorno = Tramite.get_caixa_aguardando_retorno(setores=setores, filtros=filtros)
    cx_entrada_nao_recebidos = tramites_de_entrada.filter(data_hora_recebimento__isnull=True).order_by(
        'data_hora_encaminhamento')
    cx_entrada_externos_nao_recebidos = cx_entrada_nao_recebidos.filter(tramite_barramento__isnull=False)
    despachos_solicitados = SolicitacaoDespacho.objects.filter(status=SolicitacaoStatus.STATUS_ESPERANDO).filter(
        Q(processo__in=tramites_de_entrada.values_list('processo', flat=True)) | Q(solicitado=solicitado)
    )

    cx_esperando_despachos = despachos_solicitados
    cx_entrada_recebidos = (
        tramites_de_entrada.filter(data_hora_recebimento__isnull=False)
        .order_by('prioridadetramite__prioridade', 'data_hora_encaminhamento')
        .exclude(processo__in=despachos_solicitados.values_list('processo', flat=True))
    )

    processos_pendencias = Processo.objects.filter(status__in=ProcessoStatus.status_pendentes())
    processos_pendencias = processos_pendencias.filter(ultimo_tramite__destinatario_setor__in=list(setores))
    processos_pendencias = processos_pendencias.filter(
        Q(ultimo_tramite__isnull=True) | Q(ultimo_tramite__pessoa_recebimento__isnull=False)).select_related(
        'ultimo_tramite')

    cx_entrada_sem_tramitacao = Processo.objects.filter(tramites__isnull=True, setor_criacao__in=setores,
                                                        status=ProcessoStatus.STATUS_ATIVO).order_by(
        'data_hora_criacao')
    cx_homologacao_juntada = processos_pendencias.filter(status=ProcessoStatus.STATUS_EM_HOMOLOGACAO)
    cx_esperando_juntada = processos_pendencias.filter(status=ProcessoStatus.STATUS_AGUARDANDO_JUNTADA)
    cx_esperando_ciencia = processos_pendencias.filter(status=ProcessoStatus.STATUS_AGUARDANDO_CIENCIA)

    if filtros_processo:
        cx_homologacao_juntada = cx_homologacao_juntada.filter(reduce(operator.and_, filtros_processo))
        cx_esperando_juntada = cx_esperando_juntada.filter(reduce(operator.and_, filtros_processo))
        cx_esperando_ciencia = cx_esperando_ciencia.filter(reduce(operator.and_, filtros_processo))
        cx_entrada_sem_tramitacao = cx_entrada_sem_tramitacao.filter(reduce(operator.and_, filtros_processo))

    cx_sigilosos = tramites_de_entrada.filter(processo__nivel_acesso=Processo.NIVEL_ACESSO_PRIVADO)
    template = loader.get_template('processo_eletronico/caixas.html')
    context = {
        'title': title,
        'cx_saida': cx_saida,
        'cx_entrada_nao_recebidos': cx_entrada_nao_recebidos,
        'cx_entrada_recebidos': cx_entrada_recebidos,
        'setores_visiveis': setores_visiveis,
        'setor_escolhido': setor_escolhido,
        'cx_esperando_despachos': cx_esperando_despachos,
        'cx_entrada_sem_tramitacao': cx_entrada_sem_tramitacao,
        'cx_esperando_ciencia': cx_esperando_ciencia,
        'cx_esperando_juntada': cx_esperando_juntada,
        'cx_homologacao_juntada': cx_homologacao_juntada,
        'cx_sigilosos': cx_sigilosos,
        'cx_entrada_externos_nao_recebidos': cx_entrada_externos_nao_recebidos,
        'cx_saida_externos': cx_saida_externos,
        'eh_chefe_do_setor': servidor_logado_eh_chefe_do_setor,
        'cx_saida_aguardando_retorno': cx_saida_aguardando_retorno,
        'form': form,
    }
    breadcrumbs_add(request, context)
    return HttpResponse(template.render(context, request))


@login_required()
def tipo_processo_classificacoes_nivel_acesso_padrao(request, tipo_processo_id):
    tipo_processo = get_object_or_404(TipoProcesso, pk=tipo_processo_id)
    classificacoes = tipo_processo.classificacoes.all()

    niveis_acesso_permitidos_keys, niveis_acesso_permitidos_values = tipo_processo.niveis_acesso_permitidos
    niveis_acesso_permitidos = list()
    for i in range(len(niveis_acesso_permitidos_keys)):
        niveis_acesso_permitidos.append(
            {'id': niveis_acesso_permitidos_keys[i], 'descricao': niveis_acesso_permitidos_values[i]})

    nivel_acesso_padrao = {'id': tipo_processo.nivel_acesso_default,
                           'descricao': get_values_from_choices(tipo_processo.nivel_acesso_default,
                                                                Processo.NIVEL_ACESSO_CHOICES)}

    return JsonResponse(
        {
            'niveis_acesso_permitidos': niveis_acesso_permitidos,
            'nivel_acesso_padrao': nivel_acesso_padrao,
            'classificacoes': list(classificacoes.values('id', 'codigo', 'descricao')),
        }
    )


@rtr()
@login_required()
@transaction.atomic()
def apensar_processos(request, processo_apensador_id):
    # verifica_pode_ver_processo(request.user, processo_apensador_id)
    title = 'Apensar Processos'
    processo_apensador = get_object_or_404(Processo, pk=processo_apensador_id)
    processo_apensador.pode_ler(user=request.user, lancar_excecao=True)
    verifica_pode_editar_processo(processo_apensador)
    if not processo_apensador.pode_apensar(request.user):
        raise PermissionDenied
    form = ApensarProcessosForm(request.POST or None, request=request, processo_apensador=processo_apensador)
    if form.is_valid():
        verifica_pode_editar_processo(processo_apensador)
        processos_a_apensar = form.cleaned_data['processos_a_apensar']
        for processo_a_apensar in processos_a_apensar:
            verifica_pode_editar_processo(processo_a_apensar)

        form.save()
        return httprr('..', 'Processo(s) apensado(s) com sucesso.')

    return locals()


@rtr()
@login_required()
@transaction.atomic()
def desapensar_processo(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    processo = get_object_or_404(Processo, pk=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    title = 'Desapensar Processo {}'.format(processo)
    verifica_pode_editar_processo(processo)
    form = DesapensarProcessoForm(request.POST or None, request=request, processo=processo)
    if form.is_valid():
        form.save()
        return httprr('..', 'Processo desapensado com sucesso.')

    return locals()


@rtr()
@login_required()
@transaction.atomic()
def desapensar_todos_processos(request, apensamento_id):
    apensamento = get_object_or_404(Apensamento, pk=apensamento_id)
    title = 'Desapensar todos os Processos {}'.format(apensamento.get_numero_protocolo_processos_apensados())
    for processo in apensamento.get_processos():
        verifica_pode_editar_processo(processo)

    form = DesapensarTodosProcessosForm(request.POST or None, request=request, apensamento=apensamento)
    if form.is_valid():
        form.save()
        return httprr('..', 'Processos desapensados com sucesso.')

    return locals()


@rtr()
@login_required()
@transaction.atomic()
def anexar_processos(request, processo_anexador_id):
    # verifica_pode_ver_processo(request.user, processo_anexador_id)
    title = 'Anexar Processos'
    processo_anexador = get_object_or_404(Processo, pk=processo_anexador_id)
    processo_anexador.pode_ler(user=request.user, lancar_excecao=True)
    target = processo_anexador.get_absolute_url()
    verifica_pode_editar_processo(processo_anexador)
    form = AnexarProcessosForm(request.POST or None, request=request, processo_anexador=processo_anexador)
    if not processo_anexador.pode_anexar(request.user):
        raise PermissionDenied
    if form.is_valid():
        processo_anexador = form.processo_anexador
        processos_anexados = form.cleaned_data['processos_anexados']
        for processo_anexado in processos_anexados:
            verifica_pode_editar_processo(processo_anexado)
            registrar_acao(request, processo_anexado, RegistroAcaoProcesso.TIPO_APENSACAO,
                           'Anexação ao processo {}'.format(processo_anexador))
            registrar_acao(request, processo_anexador, RegistroAcaoProcesso.TIPO_APENSACAO,
                           'Anexação do processo {}'.format(processo_anexado))

        form.save()

        return httprr('..', 'Processo(s) anexado(s) com sucesso.')

    return locals()


@rtr()
@login_required()
def listar_processos_relacionado(request, processo_id):
    processo_principal = get_object_or_404(Processo, pk=processo_id)
    title = 'Processos que podem ser relacionados ao processo {}'.format(processo_principal)
    verifica_pode_editar_processo(processo_principal)
    form = RelacionarProcessosForm(request.GET, request=request, processo_principal=processo_principal)
    processos, order_str = form.processar()
    #
    return locals()


@login_required()
@transaction.atomic()
def adicionar_processo_relacionado(request, processo_principal_id, processo_relacionado_id):
    processo_principal = get_object_or_404(Processo, pk=processo_principal_id)
    processo_relacionado = get_object_or_404(Processo, pk=processo_relacionado_id)
    verifica_pode_editar_processo(processo_principal)
    processo_principal.adicionar_relacionamento(processo_relacionado)
    match = reverse_lazy('processo', kwargs={'processo_id': processo_principal.id}, current_app='processo')
    return httprr(match, 'Relacionamento criado com sucesso.')


@login_required()
@transaction.atomic()
def remover_relacionamento_processos(request, processo_principal_id, processo_relacionado_id):
    processo_principal = get_object_or_404(Processo, pk=processo_principal_id)
    processo_relacionado = get_object_or_404(Processo, pk=processo_relacionado_id)
    verifica_pode_editar_processo(processo_principal)
    processo_principal.remover_relacionamento(processo_relacionado)
    #
    match = reverse_lazy('processo', kwargs={'processo_id': processo_principal.id}, current_app='processo')
    return httprr(match, 'Relacionamento removido com sucesso.')


@rtr()
@login_required()
def adicionar_comentario(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    title = 'Adicionar Comentário'
    processo = get_object_or_404(Processo, pk=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    verifica_pode_editar_processo(processo)
    comentario = ComentarioProcesso(processo=processo, pessoa=request.user.get_profile())
    form = AdicionarComentario(request.POST or None, request=request, instance=comentario)
    if form.is_valid():
        form.save()
        return httprr('..', 'Comentário adicionado com sucesso.')

    return locals()


@rtr()
@login_required()
def desconsiderar_comentario(request, comentario_id):
    comentario = get_object_or_404(ComentarioProcesso, pk=comentario_id)
    processo = comentario.processo
    if not processo.pode_editar(request.user):
        raise PermissionDenied(
            'Você não tem permissão para editar esse processo.')
    if comentario.pessoa.pessoafisica != request.user.get_profile():
        raise PermissionDenied(
            'Você não tem permissão para desconsiderar este comentário. Apenas o próprio usuário pode desconsiderá-lo.')
    comentario.desconsiderado_em = datetime.now()
    comentario.save()
    return httprr('..', 'Comentário desconsiderado com sucesso.')


@login_required()
def imprimir_minuta_pdf(request, minuta_id, orientacao=None):
    minuta = get_object_or_404(Minuta, pk=minuta_id)
    if not pode_visualizar_minuta(request.user, minuta):
        raise PermissionDenied()

    if orientacao == 'paisagem':
        orientacao = 'landscape'
    else:
        orientacao = 'portrait'

    try:
        pdf = minuta.get_pdf(orientacao=orientacao, user=request.user)
    except OSError:
        raise Http404('Erro ao gerar o arquivo PDF.')
    return HttpResponse(pdf, content_type='application/pdf')


@login_required()
def imprimir_parecer_pdf(request, parecer_id, orientacao=None):
    parecer = get_object_or_404(ParecerSimples, pk=parecer_id)
    if not parecer.pode_ler(request.user):
        raise PermissionDenied()

    if orientacao == 'paisagem':
        orientacao = 'landscape'
    else:
        orientacao = 'portrait'

    try:
        pdf = parecer.get_pdf(orientacao=orientacao, user=request.user)
        return HttpResponse(pdf, content_type='application/pdf')
    except OSError:
        raise Http404('Erro ao gerar o arquivo PDF.')


@deprecated('Esse método está depreciado. Usar o imprimir processo celery')
@login_required()
def imprimir_processo(request, processo_id):
    processo = get_object_or_404(Processo, pk=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    try:
        pdf = processo.get_pdf(user=request.user)
        registrar_acao(request, processo, RegistroAcaoProcesso.TIPO_IMPRESSAO)
        return HttpResponse(pdf, content_type='application/pdf')
    except Exception as e:
        raise e
        return httprr(processo.get_absolute_url(),
                      message="Ocorreu um erro ao gerar o arquivo PDF deste processo, tente utilizar a opção Baixar em ZIP.",
                      tag='error')


@login_required()
def fazer_download_zip_processo(request, processo_id):
    processo = get_object_or_404(Processo, pk=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    try:
        zip = processo.get_zip(user=request.user)
        registrar_acao(request, processo, RegistroAcaoProcesso.TIPO_IMPRESSAO)
        dump_zip_file = open(zip, 'rb')
        conteudo_dump = dump_zip_file.read()
        dump_zip_file.close()

        response = HttpResponse(conteudo_dump, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=processo_{}.zip'.format(processo.id)
        return response
    except Exception:
        return httprr(processo.get_absolute_url(), message="Ocorreu um erro ao gerar o arquivo ZIP deste processo.",
                      tag='error')

# TODO: Após unificar os métodos pode_ler e pode_ler_consulta_publica de Processo, tentar unificar fazer_download_zip_processo e fazer_download_zip_processo_consulta_publica,
# usando como parâmetro processo_uuid.


def fazer_download_zip_processo_consulta_publica(request, processo_uuid):
    processo = get_object_or_404(Processo, uuid=processo_uuid)
    pode_ler = processo.pode_ler_consulta_publica()
    if not pode_ler:
        return httprr('..',
                      message="Um processo só pode ser visualizado nas seguintes hipóteses: se ele for público e o seu tipo permitir ou estiver vinculado a contrato.",
                      tag='error')
    try:
        zip = processo.get_zip(eh_consulta_publica=True)
        registrar_acao(request, processo, RegistroAcaoProcesso.TIPO_IMPRESSAO)
        dump_zip_file = open(zip, 'rb')
        conteudo_dump = dump_zip_file.read()
        dump_zip_file.close()

        response = HttpResponse(conteudo_dump, content_type='application/zip')
        response['Content-Disposition'] = 'attachment; filename=processo_{}.zip'.format(processo.id)
        return response
    except Exception:
        return httprr('..', message="Ocorreu um erro ao gerar o arquivo ZIP deste processo.", tag='error')


def imprimir_processo_celery(request, processo_uuid):
    user = request.user
    processo = get_object_or_404(Processo, uuid=processo_uuid)

    # se processo tiver visibilidade pública não é necessária nenhuma verificação de permissão
    if not processo.pode_ler_consulta_publica():
        # se usuário for anônimo retorne erro
        if user.is_anonymous:
            return httprr('..',
                          message="Um processo só pode ser visualizado nas seguintes hipóteses: se ele for público e o seu tipo permitir ou estiver vinculado a contrato.",
                          tag='error')
        # senão verifique se o usuario pode ler
        processo.pode_ler(user=user, lancar_excecao=True)

    try:
        registrar_acao(request, processo, RegistroAcaoProcesso.TIPO_IMPRESSAO)
        return tasks.gerar_processo_pdf(processo=processo, user=user, leitura_para_barramento=False, eh_consulta_publica=user.is_anonymous)
    except Exception as e:
        raise e
        return httprr(processo.get_absolute_url(),
                      message="Ocorreu um erro ao gerar o arquivo PDF deste processo, tente utilizar a opção Baixar em ZIP.",
                      tag='error')


def fazer_download_zip_processo_celery(request, processo_uuid):
    user = request.user
    processo = get_object_or_404(Processo, uuid=processo_uuid)

    # se processo tiver visibilidade pública não é necessária nenhuma verificação de permissão
    if not processo.pode_ler_consulta_publica():
        # se usuário for anônimo retorne erro
        if user.is_anonymous:
            return httprr('..',
                          message="Um processo só pode ser visualizado nas seguintes hipóteses: se ele for público e o seu tipo permitir ou estiver vinculado a contrato.",
                          tag='error')
        # senão verifique se o usuario pode ler
        processo.pode_ler(user=user, lancar_excecao=True)

    try:
        registrar_acao(request, processo, RegistroAcaoProcesso.TIPO_IMPRESSAO)
        return tasks.gerar_zip_processo(processo=processo, user=user, leitura_para_barramento=False, eh_consulta_publica=user.is_anonymous)
    except Exception as e:
        raise e
        return httprr(processo.get_absolute_url(), message="Ocorreu um erro ao gerar o arquivo ZIP deste processo.",
                      tag='error')


@rtr()
def imprimir_requerimento_pdf(request, contexto):
    form = contexto['form']
    hoje = datetime.today()
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
    setor_destino = form.cleaned_data.get('destinatario_setor_autocompletar') or form.cleaned_data.get(
        'destinatario_setor_arvore')
    return locals()


# TODO - Eriton: Mantive esta função aqui mas em tese é pra ela ir pro saco. Não vi nenhuma ocorrência dela nos fontes!
@rtr()
def requerimento_pdf(requerimento):
    # Usado no novo requerimento
    hoje = datetime.today()
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
    return locals()


@rtr('processo_eletronico/requerimento_pdf.html')
def montar_requerimento_pdf_as_html(request, requerente_nome, requerente_telefone, requerente_email,
                                    requerimento_destinatario_setor,
                                    requerimento_tipo_processo, requerimento_assunto, requerimento_descricao,
                                    requerimento_data_hora_emissao,
                                    requerente_matricula_siap=None, requerente_cargo=None, requerente_lotacao=None):
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
    return locals()


def gerar_documento_digitalizado_from_file_content(file_content, file_name, tipo_documento, assunto, user, papel):
    data_hora_atual = datetime.now()

    documento = DocumentoDigitalizado()
    documento.identificador_tipo_documento_sigla = tipo_documento.sigla
    # documento.identificador_numero = self.id
    documento.identificador_ano = datetime.now().year
    documento.identificador_setor_sigla = get_setor(user).sigla
    documento.tipo = tipo_documento
    documento.interno = True
    documento.tipo_conferencia = TipoConferencia.objects.get(descricao='Cópia Simples')
    documento.setor_dono = get_setor(user)
    documento.assunto = assunto
    documento.data_emissao = data_hora_atual

    # O nivel de acesso do PDF do requerimento era definnido de acordo com o "tipo_processo.nivel_acesso_default" do
    # requerimento. Para proteger os dados do interessado o nível acesso do PDF será RESTRITO
    documento.nivel_acesso = Documento.NIVEL_ACESSO_RESTRITO

    # Informando a hipótese legal que será usada ao criado o documento digitalizado restrito, caso existam hipóteses
    # cadastradas para tal.
    # TODO: Todos os documentos deve ser restritos mesmo?
    if HipoteseLegal.objects.filter(nivel_acesso=NivelAcessoEnum.RESTRITO.name).exists():
        hipotese_legal_documento_abertura_requerimento_id = Configuracao.get_valor_por_chave('processo_eletronico',
                                                                                             'hipotese_legal_documento_abertura_requerimento')
        if not hipotese_legal_documento_abertura_requerimento_id:
            raise ValidationError(
                'Impossível gerar o documento digitalizado do requerimento pois não há hipótese legal configurada para isso no módulo de processo eletrônico. Entre em contato com os administradores do sistema.'
            )
        documento.hipotese_legal = HipoteseLegal.objects.get(pk=hipotese_legal_documento_abertura_requerimento_id)

    documento.usuario_criacao = user
    documento.data_criacao = data_hora_atual
    documento.usuario_ultima_modificacao = user
    documento.data_ultima_modificacao = data_hora_atual
    documento.arquivo.save(file_name, ContentFile(file_content))
    documento.assinar_via_senha(user, papel)
    # Chamando a validação do domínio.
    documento.clean()
    documento.save()
    return documento


def recibo_envio_conectagov(request, tramite_id):
    tramite = get_object_or_404(Tramite, id=tramite_id)
    if tramite.tramite_barramento.tramite_externo_recibo_envio_json:
        import json

        json_data = json.dumps(tramite.tramite_barramento.tramite_externo_recibo_envio_json)
        response = HttpResponse(json_data, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=recibo_envio.json'
    return response


def recibo_conclusao_conectagov(request, tramite_id):
    tramite = get_object_or_404(Tramite, id=tramite_id)
    if tramite.tramite_barramento.tramite_externo_recibo_conclusao_json:
        import json

        json_data = json.dumps(tramite.tramite_barramento.tramite_externo_recibo_conclusao_json)
        response = HttpResponse(json_data, content_type='application/json')
        response['Content-Disposition'] = 'attachment; filename=recibo_conclusao.json'
    return response


@login_required()
def verificar_integridade_documento_digitalizado(request, documentoprocesso_id):
    documento_processo = get_object_or_404(DocumentoDigitalizadoProcesso, id=documentoprocesso_id)
    documento = get_documento_digitalizado(documento_processo.documento_id)
    if not documento:
        raise Http404()

    match = reverse_lazy('processo', kwargs={'processo_id': documento_processo.processo_id}, current_app='processo')

    for assinatura_documento in documento.assinaturadocumentodigitalizado_set.all():
        if not assinatura_documento.validar_documento():
            return httprr(match, message='O documento "{}" foi violado.'.format(documento), tag='error')
    return httprr(match, 'O documento "{}" encontra-se íntegro.'.format(documento))


@login_required()
def verificar_integridade_documento_texto(request, documentoprocesso_id):
    documento_processo = get_object_or_404(DocumentoTextoProcesso, id=documentoprocesso_id)
    documento = get_documento_or_forbidden(request.user, documento_processo.documento_id)

    match = reverse_lazy('processo', kwargs={'processo_id': documento_processo.processo_id}, current_app='processo')
    for assinatura_documento in documento.assinaturadocumentotexto_set.all():
        if not assinatura_documento.validar_documento():
            return httprr(match, message='O documento "{}" foi violado.'.format(documento), tag='error')
    return httprr(match, 'O documento "{}" encontra-se íntegro.'.format(documento))


@login_required()
def verificar_integridade_tramite(request, tramite_id):
    tramite = get_object_or_404(Tramite, id=tramite_id)
    match = '/processo_eletronico/processo/{}/?tab=documentos'.format(tramite.processo_id)
    if not tramite.assinaturatramite.validar_tramite():
        return httprr(match, message='O despacho  de número "{}" foi violado.'.format(tramite.id), tag='error')
    else:
        return httprr(match, 'O despacho de número "{}" encontra-se íntegro.'.format(tramite.id))


@rtr()
@transaction.atomic()
@login_required()
def documento_upload(request, processo_id):
    processo = get_object_or_404(Processo, pk=processo_id)
    verifica_pode_editar_processo(processo)
    title = 'Anexar Documento ao Processo {}'.format(processo)
    processo.pode_realizar_upload(user=request.user)
    extensoes = settings.CONTENT_TYPES
    max_file_upload_size = settings.PROCESSO_ELETRONICO_DOCUMENTO_EXTERNO_MAX_UPLOAD_SIZE
    form = DocumentoUploadForm(request.POST or None, request.FILES or None, request=request, processo=processo)
    if form.is_valid():
        form.save()
        return httprr('..', 'Documento anexado com sucesso.')

    return locals()


@method_decorator(login_required, name='dispatch')
class DocumentoUploadWizard(SessionWizardView):
    title = 'Upload de Documento Externo'
    template_name = 'documento_upload.html'
    location = os.path.join(settings.TEMP_DIR, 'processo_eletronico', 'files')
    file_storage = FileSystemStorage(location)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.request = None
        self.processo = None
        self.solicitacao = None

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        self.processo = Processo.objects.filter(id=self.kwargs.get('processo_id', None)).first()
        self.solicitacao = SolicitacaoJuntada.objects.filter(id=self.kwargs.get('solicitacao_id', None)).first()
        if step is None or step == '0':
            self.request = self.request
            kwargs.update({'processo': self.processo, 'solicitacao': self.solicitacao, 'request': self.request})
        return kwargs

    def get_form_prefix(self, step=None, form=None):
        # nao retorne ids estilizados
        return ""

    def post(self, *args, **kwargs):
        if self.request.POST.get('tipo_assinatura') == 'senha' or 'senha' in self.request.POST:
            self.form_list['1'] = AssinarDocumentoForm
        if self.request.POST.get('tipo_assinatura') == 'govbr' or 'govbr' in self.request.POST:
            self.form_list['1'] = AssinarDocumentoGovBRForm
        return super().post(self, *args, **kwargs)

    def render(self, form=None, **kwargs):
        if not self.processo and not self.solicitacao:
            raise Http404
        if not self.solicitacao:
            if not self.processo.pode_editar() or not self.processo.pode_realizar_upload(self.request.user):
                raise PermissionDenied()
        return super().render(form, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        context[
            'title'] = self.title if not self.solicitacao else 'Adicionar Documento Externo à Solicitação de Juntada'
        context['extensoes'] = settings.CONTENT_TYPES
        if self.steps.current == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            if cleaned_data:
                uploaded_file = cleaned_data.get('arquivo')
                tipo_assinatura = cleaned_data.get('tipo_assinatura')
                if uploaded_file:
                    self.hash_conteudo = hash_bytestr_iter(uploaded_file.chunks(), hashlib.sha512())
                    context.update({'hash_conteudo': self.hash_conteudo, 'tipo_assinatura': tipo_assinatura})
        return context

    @transaction.atomic()
    def done(self, form_list, form_dict, **kwargs):
        cleaned_data = self.get_all_cleaned_data()
        uploaded_file = cleaned_data.get('arquivo')
        processo_id = self.solicitacao.processo.id if self.solicitacao else kwargs.get('processo_id', None)
        target = reverse_lazy('processo', kwargs={'processo_id': processo_id}, current_app='processo_eletronico')
        try:
            for form in form_list:
                if form.is_valid():
                    # injetando a request
                    form.request = self.request
                    if isinstance(form, ModelForm):
                        form.save()
                else:
                    raise Exception('Os dados submetidos estão incorretos.')
            # Redirecionanmento
            if self.solicitacao:
                msg = 'Documento enviado com sucesso. Caso não existam outros ' 'documentos para adicionar, você deve Concluir a solicitação.'
                target = target + '?tab=solicitacoes'
            else:
                msg = 'Documento anexado com sucesso.'
            return httprr(target, msg)
        except ValidationError as e:
            # Remove temp upload directory.
            self.file_storage.delete(uploaded_file.name)
            return httprr(target, e.message, 'error')
        except Exception as e:
            # Remove temp upload directory.
            self.file_storage.delete(uploaded_file.name)
            raise e


@method_decorator(login_required, name='dispatch')
class DespachoWizard(SessionWizardView):
    template_name = 'processo_eletronico/despacho.html'

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step is None or step == '0':
            self.processo = Processo.objects.filter(id=self.kwargs.get('processo_id')).first()
            kwargs.update({'processo': self.processo})
        return kwargs

    def get_form_prefix(self, step=None, form=None):
        # nao retorne ids estilizados
        return ""

    def get_form(self, step=None, data=None, files=None):
        if step == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            if cleaned_data.get('tipo_assinatura') == 'senha':
                return AssinarDocumentoForm(data=data, files=files, request=self.request)
        #
        return super().get_form(step, data, files)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        if self.steps.current == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            self.hash_conteudo = gerar_hash(cleaned_data.get('despacho'))
            tipo_assinatura = cleaned_data.get('tipo_assinatura')
            context.update({'hash_conteudo': self.hash_conteudo, 'tipo_assinatura': tipo_assinatura})
        return context

    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    @transaction.atomic()
    def done(self, form_list, form_dict, **kwargs):
        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                cleaned_data = self.get_all_cleaned_data()
                # interessados = cleaned_data.get('interessados')
                # assunto = cleaned_data.get('assunto')
                # setor_dono = get_setor(self.request.user)
                # despacho = cleaned_data.get('texto')
                papel = cleaned_data.get('papel')
                modelo_documento = ModeloDespacho.objects.all().first()
                if not (modelo_documento):
                    target = reverse_lazy('processo', kwargs={'processo_id': kwargs.get('processo_id')},
                                          current_app='processo_eletronico')
                    return httprr(target,
                                  'O Tipo de Documento Despacho e o modelo Despacho de andamento devem estar cadastrados no sistema.',
                                  tag='error')

                if cleaned_data.get('tipo_assinatura') == "senha":
                    documento.assinar_via_senha(self.request.user, papel)
                    documento.finalizar_documento()
                    documento.save()
                    adicionar_documento_processo(self.request, self.processo.id, documento.id)
                transaction.savepoint_commit(sid)
                return httprr('..', 'Despacho adicionado ao processo com sucesso.')
            except Exception as e:
                transaction.savepoint_rollback(sid)
                raise PermissionDenied(str(e))
        raise PermissionDenied


@rtr('processo_eletronico/processo_padrao.html')
@login_required()
def solicitar_ciencia(request, processo_id):
    processo = get_object_or_404(Processo, pk=processo_id)
    title = "Solicitar Ciência - Processo: {}".format(processo)

    target = processo.get_absolute_url()
    if processo.pode_solicitar_ciencia(request.user):
        form = SolicitacaoCienciaForm(request.POST or None, request=request, processo=processo)
        if form.is_valid():
            data_limite_juntada = form.cleaned_data.get('data_limite_juntada', None)
            try:
                for interessado in form.cleaned_data.get('interessados'):
                    created = False
                    with transaction.atomic():
                        solicitacao, created = SolicitacaoCiencia.objects.get_or_create(
                            processo=processo,
                            solicitado=interessado.pessoafisica,
                            solicitante=request.user,
                            data_limite_ciencia=form.cleaned_data.get('data_limite_ciencia'),
                            data_limite_juntada=data_limite_juntada,
                            data_ciencia=None,
                            status=CienciaStatus.STATUS_ESPERANDO,
                            defaults={'motivo': form.cleaned_data.get('motivo')},
                        )
                        #

                    # Se a solicitação foi criada.
                    if created:
                        # Enviando email
                        solicitacao.enviar_mail()
                return httprr(target, 'Solicitações de ciência adicionadas com sucesso.')
            except Exception:
                return httprr(target, 'Ocorreu um erro durante o envio da notificação.', tag='error')
        else:
            return locals()
    else:
        raise PermissionDenied


@rtr('processo_eletronico/imprimir_ciencia_pdf.html')
def imprimir_ciencia_pdf(request, solicitacao):
    instance = request.user.get_profile()

    setor = get_setor(request.user) if not instance.get_vinculo().eh_usuario_externo() else None
    hoje = datetime.today()
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
    return locals()


def gerar_termo_ciencia(processo, user, papel, assunto, content):
    qs = DocumentoDigitalizado.objects.all()
    pk = qs.latest('id').id if qs.exists() else 0

    today = get_datetime_now()
    documento = DocumentoDigitalizado()
    setor = get_setor(user)
    tipo_documento = TipoDocumento.objects.filter(nome="Termo").first()
    if tipo_documento is None:
        raise ValidationError('Tipo de Documento "Termo" não existe.')

    documento.identificador_tipo_documento_sigla = tipo_documento.sigla
    documento.identificador_numero = pk + 1
    documento.identificador_ano = today.year
    documento.identificador_setor_sigla = setor.sigla if setor else "-"
    documento.tipo = tipo_documento
    documento.interno = True
    documento.tipo_conferencia = TipoConferencia.objects.get(descricao='Cópia Simples')
    documento.usuario_criacao = user
    documento.data_ultima_modificacao = today
    documento.usuario_ultima_modificacao = user
    documento.data_emissao = today
    documento.setor_dono = setor or processo.setor_atual
    documento.dono_documento = user.get_profile()
    documento.data_criacao = today
    documento.assunto = assunto
    documento.nivel_acesso = NivelAcesso.NIVEL_ACESSO_RESTRITO
    documento.arquivo.save('ciencia.html', ContentFile(content))
    # Assina o documento de acordo com o papel selecionado na tela
    documento.assinar_via_senha(user, papel)
    documento.save()

    documento_processo = DocumentoDigitalizadoProcesso()
    documento_processo.processo = processo
    documento_processo.documento = documento
    documento_processo.data_hora_inclusao = today
    documento_processo.usuario_inclusao = user
    documento_processo.motivo_vinculo_documento_processo_inclusao = DocumentoProcesso.MOTIVO_ANEXACAO
    documento_processo.save()
    return processo


@rtr('processo_eletronico/imprimir_termo_finalizacao_pdf.html')
def imprimir_termo_finalizacao_pdf(request, processo, justificativa):
    instance = request.user.get_relacionamento()
    setor = get_setor(request.user)
    agora = datetime.now()
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
    return locals()


@transaction.atomic
def gerar_termo_finalizacao(processo, user, papel, assunto, content):
    today = get_datetime_now()
    documento = DocumentoDigitalizado()
    setor = get_setor(user)
    tipo_documento = TipoDocumento.objects.filter(nome="Termo").first()
    if tipo_documento is None:
        raise ValidationError('Tipo de Documento "Termo" não existe.')

    documento.identificador_tipo_documento_sigla = tipo_documento.sigla
    documento.identificador_ano = today.year
    documento.identificador_setor_sigla = setor.sigla
    documento.tipo = tipo_documento
    documento.interno = True
    documento.tipo_conferencia = TipoConferencia.objects.get(descricao='Cópia Simples')
    documento.usuario_criacao = user
    documento.data_ultima_modificacao = today
    documento.usuario_ultima_modificacao = user
    documento.data_emissao = today
    documento.setor_dono = get_setor(user)
    documento.dono_documento = user.get_profile()
    documento.data_criacao = today
    documento.assunto = assunto
    documento.nivel_acesso = NivelAcesso.NIVEL_ACESSO_RESTRITO
    documento.arquivo.save('finalizacao.html', ContentFile(content))
    # Assina o documento de acordo com o papel selecionado na tela
    documento.assinar_via_senha(user, papel)
    documento.save()
    DocumentoDigitalizado.objects.filter(pk=documento.pk).update(identificador_numero=documento.pk)

    documento_processo = DocumentoDigitalizadoProcesso()
    documento_processo.processo = processo
    documento_processo.documento = documento
    documento_processo.data_hora_inclusao = today
    documento_processo.usuario_inclusao = user
    documento_processo.motivo_vinculo_documento_processo_inclusao = DocumentoProcesso.MOTIVO_ANEXACAO
    documento_processo.save()
    return processo


@rtr('processo_eletronico/imprimir_termo_reabertura_pdf.html')
def imprimir_termo_reabertura_pdf(request, processo, justificativa):
    instance = request.user.get_relacionamento()
    setor = get_setor(request.user)
    agora = datetime.now()
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
    return locals()


@transaction.atomic
def gerar_termo_reabertura(processo, user, papel, assunto, content):
    today = get_datetime_now()
    documento: DocumentoDigitalizado = DocumentoDigitalizado()
    setor = get_setor(user)
    tipo_documento = TipoDocumento.objects.filter(nome="Termo").first()
    if tipo_documento is None:
        raise ValidationError('Tipo de Documento "Termo" não existe.')

    documento.identificador_tipo_documento_sigla = tipo_documento.sigla
    documento.identificador_ano = today.year
    documento.identificador_setor_sigla = setor.sigla
    documento.tipo = tipo_documento
    documento.interno = True
    documento.tipo_conferencia = TipoConferencia.objects.get(descricao='Cópia Simples')
    documento.usuario_criacao = user
    documento.data_ultima_modificacao = today
    documento.usuario_ultima_modificacao = user
    documento.data_emissao = today
    documento.setor_dono = get_setor(user)
    documento.dono_documento = user.get_profile()
    documento.data_criacao = today
    documento.assunto = assunto
    documento.nivel_acesso = NivelAcesso.NIVEL_ACESSO_RESTRITO
    documento.arquivo.save('reabertura.html', ContentFile(content))
    # Assina o documento de acordo com o papel selecionado na tela
    documento.assinar_via_senha(user, papel)
    documento.save()
    DocumentoDigitalizado.objects.filter(pk=documento.pk).update(identificador_numero=documento.pk)
    documento_processo = DocumentoDigitalizadoProcesso()
    documento_processo.processo = processo
    documento_processo.documento = documento
    documento_processo.data_hora_inclusao = today
    documento_processo.usuario_inclusao = user
    documento_processo.motivo_vinculo_documento_processo_inclusao = DocumentoProcesso.MOTIVO_ANEXACAO
    documento_processo.save()
    return processo


@rtr('processo_eletronico/dar_ciencia.html')
@login_required()
def dar_ciencia(request, processo_id):
    processo = get_object_or_404(Processo, pk=processo_id)
    target = reverse_lazy('processo', kwargs={'processo_id': processo_id}, current_app='processo_eletronico')
    title = 'Dar Ciência ao Processo {}'.format(processo)
    eh_usuario_externo = request.user.get_vinculo().eh_usuario_externo()
    eh_usuario_autenticado_govbr = request.session.get("autenticou_com_govbr")
    if processo.pode_dar_ciencia(request.user):
        instance = request.user.get_profile()
        solicitacao = processo.get_ciencia_pendente(instance)
        if solicitacao is None:
            return httprr(target, 'Não existe nenhuma ciência pendente no processo {}.'.format(processo), tag='error')
        #
        setor = get_setor(request.user)
        form = CienciaForm(request.POST or None, request=request)

        if eh_usuario_autenticado_govbr:
            form = CienciaGovBRForm(request.POST or None, request=request)

        if isinstance(form, CienciaGovBRForm):
            action = request.GET.get('action')
            force_new_code = False
            if action and action == 'new_code':
                force_new_code = True
            if request.method == "GET":
                form.gerar_codigo_verificacao(force=force_new_code)

        if form.is_valid():
            #
            papel = form.cleaned_data.get('papel', None)
            assunto = "Termo de Ciência: Conhecimento/Notificação"
            solicitacao.informar_ciencia(get_datetime_now())
            pdf = imprimir_ciencia_pdf(request, solicitacao)
            with transaction.atomic():
                sid = transaction.savepoint()
                try:
                    #
                    solicitacao.gerar_termo_ciencia(processo, request.user, papel, assunto, pdf.content)
                    solicitacao.save()
                    transaction.savepoint_commit(sid)
                    return httprr(target, 'Ciência do processo {} dada com sucesso.'.format(processo))
                except Exception as e:
                    transaction.savepoint_rollback(sid)
                    raise PermissionDenied(str(e))
        else:
            return locals()
    raise PermissionDenied


# TODO - Eriton: Rever função. Existe outra chamada "requerimento_pdf".
@rtr
@login_required()
def requirimento_pdf(request, processo_id):
    processo = get_object_or_404(Processo, pk=processo_id)
    return locals()


@method_decorator(login_required, name='dispatch')
class ParecerWizard(SessionWizardView):
    template_name = 'processo_eletronico/parecer.html'

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        if step is None or step == '0':
            self.processo_minuta = ProcessoMinuta.objects.filter(id=self.kwargs.get('processo_minuta_id')).first()
            kwargs.update({'processo_minuta': self.processo_minuta})
        return kwargs

    def get_form_prefix(self, step=None, form=None):
        # nao retorne ids estilizados
        return ""

    def get_form(self, step=None, data=None, files=None):
        if step == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            if cleaned_data.get('tipo_assinatura') == 'senha':
                return AssinarDocumentoForm(data=data, files=files, request=self.request)
        #
        return super().get_form(step, data, files)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)
        if self.steps.current == '1':
            cleaned_data = self.get_cleaned_data_for_step('0')
            self.hash_conteudo = gerar_hash(cleaned_data.get('texto_parecer'))
            tipo_assinatura = cleaned_data.get('tipo_assinatura')
            context.update({'hash_conteudo': self.hash_conteudo, 'tipo_assinatura': tipo_assinatura})
        return context

    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)

    @transaction.atomic()
    def done(self, form_list, form_dict, **kwargs):
        #
        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                cleaned_data = self.get_all_cleaned_data()
                texto_parecer = cleaned_data.get('texto')
                papel = cleaned_data.get('papel')
                modelo_documento = ModeloParecer.objects.all().first()
                target = reverse_lazy('processo', kwargs={'processo_id': self.processo_minuta.processo_id},
                                      current_app='processo_eletronico')
                if not modelo_documento:
                    return httprr(target, 'O Modelo de parecer não está cadastrado no sistema.', tag='error')

                variaveis = get_variaveis(documento_identificador='',
                                          estagio_processamento_variavel=EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO)
                cabecalho = processar_template_ckeditor(texto=modelo_documento.cabecalho, variaveis=variaveis)
                rodape = processar_template_ckeditor(texto=modelo_documento.rodape, variaveis=variaveis)
                parecer = ParecerSimples.objects.create(cabecalho=cabecalho, rodape=rodape, corpo=texto_parecer,
                                                        processo_minuta=self.processo_minuta)

                if cleaned_data.get('tipo_assinatura') == "senha":
                    parecer.assinar_via_senha(self.request.user, papel)

                transaction.savepoint_commit(sid)
                return httprr(target, 'Parecer adicionado ao processo com sucesso.')
            except Exception as e:
                transaction.savepoint_rollback(sid)
                raise PermissionDenied('{}'.format(e))
        raise PermissionDenied


@rtr()
@permission_required('documento_eletronico.change_documentotexto')
def clonar_minuta_em_documento(request, minuta_id):
    title = f'Clonar Minuta {minuta_id} em Documento'
    minuta = get_object_or_404(Minuta, id=minuta_id)
    documento = minuta.documento

    form = ClonarMinutaForm(
        request.POST or None, request=request, assunto=minuta.assunto, tipodocumento=documento.tipo,
        modelo=documento.modelo, nivel_acesso=documento.nivel_acesso, hipotese_legal=documento.hipotese_legal)
    if form.is_valid():
        hipotese_legal = form.cleaned_data.get('hipotese_legal')
        nivel_acesso = form.cleaned_data.get('nivel_acesso')
        modelo = form.cleaned_data.get('modelo')
        setor_dono = form.cleaned_data.get('setor_dono')
        if minuta.pode_clonar_documento(request.user):
            mensagem_alteracao = ''
            if not minuta.documento.hipotese_legal and minuta.documento.nivel_acesso in [
                    Documento.NIVEL_ACESSO_RESTRITO, Documento.NIVEL_ACESSO_SIGILOSO]:
                mensagem_alteracao = ', no entanto o nível de acesso do documento clonado foi alterado para {}'.format(
                    documento.modelo.get_nivel_acesso_padrao_display())

            try:
                documento_novo = minuta.clonar_documento(request.user, setor_dono, modelo=modelo,
                                                         hipotese_legal=hipotese_legal, nivel_acesso=nivel_acesso)
                return httprr(documento_novo.get_absolute_url(),
                              'Documento foi clonado com sucesso{}.'.format(
                                  mensagem_alteracao),
                              )
            except ValidationError as e:
                return httprr(documento.get_absolute_url(), message="{}".format(e.messages[0]), tag='error')
        else:
            return PermissionDenied('Você não tem permissão para clonar uma minuta.')

    return locals()


@rtr('processo_eletronico/visualizar_minuta.html')
@login_required()
def visualizar_minuta(request, minuta_id):
    minuta = get_object_or_404(Minuta, id=minuta_id)
    title = 'Visualização da Minuta #{}'.format(minuta)
    if not pode_visualizar_minuta(request.user, minuta):
        raise PermissionDenied()
    #
    processo_ids = minuta.processominuta_set.filter(data_hora_remocao__isnull=True).values_list('processo_id',
                                                                                                flat=True)
    processos_incluido = Processo.objects.by_user(request.user).filter(id__in=processo_ids)
    return locals()


@rtr('processo_eletronico/visualizar_parecer.html')
@login_required()
def visualizar_parecer(request, parecer_id):
    parecer = get_object_or_404(ParecerSimples, id=parecer_id)
    title = 'Visualização {} relacionado a {}'.format(parecer, parecer.processo_minuta.minuta)
    #
    if not pode_visualizar_minuta(request.user, parecer.processo_minuta.minuta):
        raise PermissionDenied()
    #
    processos_incluido = [parecer.processo_minuta.processo]
    return locals()


@rtr('documento_eletronico/templates/conteudo_documento.html')
def conteudo_minuta(request, minuta_id, acesso_publico=False):
    documento = get_minuta(minuta_id, acesso_publico)
    eh_anonimo = request.user.is_anonymous
    if eh_anonimo:
        # Observando do "pode_visualizar_minuta(user, minuta)" neste views.py
        # - Considerando o comentário "Se houver uma solicitação de despacho pendente para o usuário, então ele poderá ver a minuta."
        # - Defini que a minua não pode ser visualizada na área pública
        return httprr('/processo_eletronico/consulta_publica/', message="Este documento não pode ser visualizada na consulta pública.", tag='error')
    else:
        if not pode_visualizar_minuta(request.user, documento):
            raise PermissionDenied()

    eh_minuta = True
    return locals()


@rtr('documento_eletronico/templates/conteudo_documento.html')
def conteudo_parecer(request, parecer_id, acesso_publico=False):
    documento = get_parecer_simples(parecer_id, acesso_publico)
    eh_anonimo = request.user.is_anonymous
    if eh_anonimo:
        # Mesma regra da view "conteudo_minuta"
        return httprr('/processo_eletronico/consulta_publica/',
                      message="Este documento não pode ser visualizada na consulta pública.", tag='error')
    else:
        if not pode_visualizar_minuta(request.user, documento.processo_minuta.minuta):
            raise PermissionDenied()

    return locals()


@login_required()
def remover_parecer(request, id):
    processo_minuta = get_object_or_404(ProcessoMinuta, id=id)

    if request.user != processo_minuta.parecer.usuario_inclusao or not processo_minuta.minuta.pode_ler(request.user):
        raise PermissionDenied()
    #
    target = reverse_lazy('processo', kwargs={'processo_id': processo_minuta.processo_id},
                          current_app='processo_eletronico')
    if not processo_minuta.pode_remover_parecer():
        return httprr(target, 'O parecer não pode ser desvinculado.', tag='error')
    #
    processo_minuta.parecer.delete()
    processo_minuta.save()
    return httprr(target, 'O parecer foi removido com sucesso.')


@rtr()
@login_required()
def editar_informacoes_upload(request, documentoprocesso_id):
    documento_processo = get_object_or_404(DocumentoDigitalizadoProcesso,
                                           id=documentoprocesso_id)

    title = 'Informações sobre Documento {}'.format(documento_processo.documento)

    if documento_processo.processo.esta_anexado():
        processo_a = Anexacao.objects.get(processo_anexado=documento_processo.processo)
        verifica_pode_editar_processo(processo_a.processo_anexador)
    else:
        verifica_pode_editar_processo(documento_processo.processo)

    # documento_processo.documento
    documento = get_documento_digitalizado(documento_processo.documento.pk)
    if not documento:
        raise Http404()

    if not documento.pode_editar(user=request.user) and not request.user.is_superuser:
        raise PermissionDenied()

    target = reverse_lazy('processo',
                          kwargs={'processo_id': documento_processo.processo_id},
                          current_app='processo_eletronico'
                          )
    form = DocumentoUploadEditarForm(request.POST or None, instance=documento)
    if form.is_valid():
        form.save()
        return httprr(target, 'Os dados do documento foram atualizados com sucesso.')
    return locals()


# Demanda_497
@rtr()
@login_required()
def adicionar_prioridade(request, processo_id):
    processo = get_object_or_404(Processo, id=processo_id)
    tramite = processo.ultimo_tramite
    title = ('Nível de prioridade do processo {}').format(processo.numero_protocolo)
    verifica_pode_editar_processo(processo)

    if not tramite:
        return httprr(processo.get_absolute_url(),
                      'A operação não pode ser realizada porque o processo ainda não foi tramitado.')

    if processo.tem_solicitacoes_despacho_pendentes():
        return httprr(processo.get_absolute_url(),
                      'A operação não pode ser realizada porque o processo já foi encaminhado.')

    if not processo.pode_ser_encaminhado():
        return httprr(processo.get_absolute_url(),
                      'A operação não pode ser realizada porque o processo já foi encaminhado.')

    if ModeloDespacho.objects.all().first() is None:
        return httprr(processo.get_absolute_url(),
                      'A operação não pode ser realizada porque um modelo de despacho não foi cadastrado.', tag='error')

    try:
        PrioridadeTramite.objects.get(tramite_id=tramite.id)
        form = PrioridadeTramiteForm(request.POST or None, request=request, tramite=tramite,
                                     instance=tramite.prioridadetramite)
    except PrioridadeTramite.DoesNotExist:
        form = PrioridadeTramiteForm(request.POST or None, request=request, tramite=tramite)

    if form.is_valid():
        form.save()
        target = reverse_lazy('processo', kwargs={'processo_id': processo.id}, current_app='processo_eletronico')
        return httprr(target, 'O nível de prioridade foi atualizado com sucesso.')
    return locals()


@rtr('processo_eletronico/processo_padrao.html')
@login_required()
def solicitar_despacho(request, processo_id):
    processo = get_object_or_404(Processo, id=processo_id)
    title = ('Solicitação de despacho do {}').format(processo.numero_protocolo)
    verifica_pode_editar_processo(processo)

    if processo.tem_solicitacoes_despacho_pendentes():
        return httprr(processo.get_absolute_url(),
                      'A operação não pode ser realizada porque o processo já foi encaminhado.')

    if not processo.pode_ser_encaminhado():
        return httprr(processo.get_absolute_url(),
                      'A operação não pode ser realizada porque o processo já foi encaminhado.')

    if ModeloDespacho.objects.all().first() is None:
        return httprr(processo.get_absolute_url(),
                      'A operação não pode ser realizada porque um modelo de despacho não foi cadastrado.', tag='error')

    form = SolicitacaoDespachoFormFactory(request.POST or None, request=request, processo=processo)
    if form.is_valid():
        form.save()
        target = reverse_lazy('processo', kwargs={'processo_id': processo.id}, current_app='processo_eletronico')
        Notificar.solicitacao_despacho(processo, form.cleaned_data['solicitado'])
        return httprr(target, 'A solicitação de despacho foi efetuada com sucesso.')
    return locals()


@rtr('processo_eletronico/solicitacao_despacho_deferir.html')
@login_required()
def solicitacao_despacho_editar(request, id):
    solicitacao_despacho = get_object_or_404(SolicitacaoDespacho, id=id)
    processo = solicitacao_despacho.processo
    title = 'Editar Solicitação de Despacho do Processo {}'.format(processo.numero_protocolo)
    target_url = reverse_lazy('processo', kwargs={'processo_id': solicitacao_despacho.processo.id},
                              current_app='processo_eletronico') + '?tab=solicitacoes'
    if not solicitacao_despacho.eh_remetente(request.user):
        return httprr(target_url, 'A solicitação não pode ser editada pois você não é o remetente.', tag='error')
    if not solicitacao_despacho.em_espera():
        return httprr(target_url, 'A solicitação de despacho não está pendente.', tag='warning')
    #
    if ModeloDespacho.objects.all().first() is None:
        return httprr(target_url, 'A operação não pode ser realizada porque um modelo de despacho não foi cadastrado.',
                      tag='error')
    #
    form = SolicitacaoDespachoFormFactory(request.POST or None, request=request, processo=processo, instance=solicitacao_despacho)
    if form.is_valid():
        form.save(True)
        target = reverse_lazy('processo', kwargs={'processo_id': processo.id}, current_app='processo_eletronico')
        Notificar.solicitacao_despacho(processo, form.cleaned_data['solicitado'])
        return httprr(target, 'A solicitação de despacho foi efetuada com sucesso.')
    #
    return locals()


@rtr('processo_eletronico/solicitacao_despacho_visualizar.html')
@login_required()
def solicitacao_despacho_visualizar(request, id):
    agora = datetime.now()
    solicitacao_despacho = get_object_or_404(SolicitacaoDespacho, id=id)
    if not solicitacao_despacho.processo.pode_ler(request.user):
        raise PermissionDenied()
    return locals()


@rtr('processo_eletronico/solicitacao_despacho_deferir.html')
@login_required()
def solicitacao_despacho_deferir(request, id):
    solicitacao_despacho = get_object_or_404(SolicitacaoDespacho, id=id)
    processo = solicitacao_despacho.processo
    title = 'Solicitação de Despacho do Processo {}'.format(processo.numero_protocolo)
    target_url = reverse_lazy('processo', kwargs={'processo_id': solicitacao_despacho.processo.id},
                              current_app='processo_eletronico') + '?tab=solicitacoes'
    if not solicitacao_despacho.eh_solicitado(request.user):
        return httprr(target_url, 'A solicitação não pode ser analisada pois você não é o solicitado.', tag='error')
    if not solicitacao_despacho.em_espera():
        return httprr(target_url, 'A solicitação de despacho não está pendente.', tag='warning')
    #
    if ModeloDespacho.objects.all().first() is None:
        return httprr(target_url, 'A operação não pode ser realizada porque um modelo de despacho não foi cadastrado.',
                      tag='error')
    #
    form = DeferirDespachoFormFactory(request.POST or None, request=request, instance=solicitacao_despacho)
    if form.is_valid():
        form.save(True)
        return httprr(processo.get_absolute_url(), 'Processo encaminhado com sucesso.')
    #
    return locals()


@rtr()
@login_required()
def solicitacao_despacho_indeferir(request, id):
    solicitacao_despacho = get_object_or_404(SolicitacaoDespacho, id=id)
    processo = solicitacao_despacho.processo
    title = 'Indeferir Solicitação de Despacho do Processo {}'.format(processo.numero_protocolo)
    target_url = reverse_lazy('processo', kwargs={'processo_id': solicitacao_despacho.processo.id},
                              current_app='processo_eletronico') + '?tab=solicitacoes'
    #
    if not solicitacao_despacho.eh_solicitado(request.user):
        return httprr(target_url, 'A solicitação não pode ser indeferida pois você não é o solicitado.', tag='error')
    if not solicitacao_despacho.em_espera():
        return httprr(target_url, 'A solicitação de despacho não está pendente.', tag='warning')

    form = RejeitarSolicitacaoDespachoForm(request.POST or None, request=request, instance=solicitacao_despacho)
    if form.is_valid():
        form.save()
        return httprr(processo.get_absolute_url(), 'Despacho indeferido com sucesso.')
    return locals()


@rtr()
@login_required()
@transaction.atomic()
def solicitacao_despacho_cancelar(request, id):
    solicitacao_despacho = get_object_or_404(SolicitacaoDespacho, id=id)
    target = reverse_lazy('processo', kwargs={'processo_id': solicitacao_despacho.processo.id},
                          current_app='processo_eletronico') + '?tab=solicitacoes'
    if solicitacao_despacho.eh_remetente(request.user) and solicitacao_despacho.em_espera():
        solicitacao_despacho.indeferir_solicitacao()
        solicitacao_despacho.justificativa_rejeicao = 'Cancelada pelo solicitante'
        solicitacao_despacho.save()
        Notificar.cancelamento_solicitacao_despacho(solicitacao_despacho)
        return httprr(target, 'Solicitação de despacho cancelada com sucesso.')
    # O despacho não pode ser canclado
    return httprr(target, 'A solicitação selecionada não está pendente.', tag='error')


@rtr('processo_eletronico/solicitacao_conteudo.html')
@login_required()
def solicitacao_despacho_conteudo(request, id):
    agora = datetime.now()
    solicitacao_despacho = get_object_or_404(SolicitacaoDespacho, id=id)
    if not solicitacao_despacho.processo.pode_ler(request.user):
        raise PermissionDenied()
    #
    return locals()


# TODO: Funcao não está mais sendo utilizada no urls.py, ficando como backup em (08/10/2018) para remoção posterior.
@rtr()
@login_required()
def solicitar_assinatura_com_anexacao_para_processo(request, documento_id):
    documento = get_object_or_404(DocumentoTexto, pk=documento_id)
    if not documento.pode_solicitar_assinatura(request.user):
        raise PermissionDenied()

    if documento.tem_identificador_definitivo:
        return httprr('.', message="O documento já contém uma assinatura balizadora.", tag='error')

    title = 'Solicitações de Assinatura Com Anexação a Processo'
    form = SolicitacaoAssinaturaComAnexacaoProcessoForm(request.POST or None, request=request, documento=documento)
    if form.is_valid():
        processo_para_anexar = form.cleaned_data['processo_para_anexar']
        try:
            with transaction.atomic():
                verifica_pode_editar_processo(processo_para_anexar)
                solicitar_assinatura = get_or_create_balizadora(request.user, form.cleaned_data.get('solicitacao'),
                                                                documento)
                solicitar_assinatura_com_anexacao_para_processo = SolicitacaoAssinaturaComAnexacaoProcesso.objects.create(
                    solicitacao_assinatura=solicitar_assinatura, processo_para_anexar=processo_para_anexar,
                    destinatario_setor_tramite=form.get_destino()
                )
                url = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_id},
                                   current_app='documento_eletronico')

                # A noticação será desparada mas não é essencial, portanto mesmo que haja algum erro, o fluxo será
                # finalizado com sucesso.
                Notificar.solicitacao_assinatura_com_anexacao_a_processo(
                    solicitar_assinatura_com_anexacao_para_processo)
                return httprr(url, 'Sua solicitação foi enviada com sucesso.')
        except Exception as e:
            msg_error = 'Erro ao realizar operação.'
            if isinstance(e, PermissionDenied):
                msg_error = 'Você não possui permissão de edição no processo {}.'.format(processo_para_anexar)
            return httprr('.', message=msg_error, tag='error')

    return locals()


@rtr()
@login_required()
def criar_processo_documento(request, documento_id):
    url_admin = reverse('admin:{}_{}_add'.format('processo_eletronico', 'processo'))
    url = "{}?documento_id={}".format(url_admin, documento_id)
    return HttpResponseRedirect(url)


@rtr('processo_eletronico/processo_padrao.html')
@login_required()
def incluir_documento_processo(request, documento_id):
    documento = DocumentoTexto.objects.get(pk=documento_id)

    form = BuscaProcessoForm(request.POST or None, request=request)

    if form.is_valid():
        processo = form.cleaned_data.get('processo')
        if processo.pode_editar():
            return adicionar_documento_processo(request, processo.id, documento_id)
        else:
            messages.warning(request, 'Você não tem permissão para incluir documentos neste processo.')

    return locals()


@rtr()
@permission_required('processo_eletronico.pode_abrir_requerimento')
def cadastrar_requerimento(request):
    # Cadastra os dados basicos de um requerimento

    title = 'Adicionar Requerimento'

    form = RequerimentoFormCadastrar(request.POST or None, request=request)

    if form.is_valid():
        try:
            requerimento = form.save(commit=False)
            requerimento.save(request.user)

            return httprr(
                reverse_lazy('gerenciar_requerimento', current_app='processo_eletronico',
                             kwargs={'requerimento_id': requerimento.id}), 'Requerimento cadastrado com sucesso.'
            )
        except Exception as e:
            return httprr('.', message=str(e), tag='error')

    return locals()


@rtr()
@permission_required('processo_eletronico.pode_abrir_requerimento')
def gerenciar_requerimento(request, requerimento_id, modo=None):
    # Mostra um requerimento e disponibiliza opcoes para alterar seus dados,
    # Adiciona documento interno, externo e outras opcoes do requerimento

    requerimento = Requerimento.get_requerimento_by_user(request_user=request.user, requerimento_id=requerimento_id)
    if not requerimento:
        raise PermissionDenied

    title = 'Requerimento #{}'.format(requerimento.get_numero_requerimento())

    documento_visualizar_botao_verificar_integridade = request.user.is_superuser or in_group(
        request.user, ['Gerente Sistêmico de Documento Eletrônico', 'documento_eletronico Administrador']
    )

    # Lista dos documentos vinculados ao requerimento
    documentos_texto = DocumentoTextoRequerimento.objects.filter(requerimento_id=requerimento_id).extra(select={'digitalizado': False})
    documentos_digitalizados = DocumentoDigitalizadoRequerimento.objects.filter(requerimento_id=requerimento_id).extra(select={'digitalizado': True})
    documentos_digitalizados_outros = DocumentoDigitalizadoRequerimentoOutros.objects.filter(requerimento_id=requerimento_id).extra(select={'digitalizado': True})
    documentos_requerimento = list(documentos_texto) + list(documentos_digitalizados) + list(documentos_digitalizados_outros)
    documentos_requerimento.sort(key=lambda a: a.data_hora_cadastro, reverse=True)

    requerimento._listar_documentos()

    return locals()


@login_required()
def listar_documentos_juntar(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoJuntada, id=solicitacao_id)
    if solicitacao.estah_expirada():
        raise ValidationError('A solicitação de juntada está expirada.')

    processo_id = solicitacao.tramite.processo.id
    view_action = 'solicitar_juntada_documento_interno'
    return listar_documentos_adicionar(request, processo_id, view_action, solicitacao=solicitacao)


@rtr('processo_eletronico/processo_padrao.html')
@login_required()
def enviar_solicitacao_juntada(request, processo_id):
    title = 'Adicionar Solicitação de Juntada de Documentos'
    processo = get_object_or_404(Processo, id=processo_id)
    target = processo.get_absolute_url()
    if not processo.pode_solicitar_juntada_documento(request.user):
        return httprr(target,
                      'Este processo não permite a juntada de documento no momento, pois está na situação {}.'.format(
                          processo.status), tag='error')

    form = PedidoJuntadaForm(request.POST or None, processo=processo, request=request)
    if form.is_valid():
        try:
            for solicitado in form.cleaned_data.get('solicitados'):
                created = False
                with transaction.atomic():
                    solicitacao, created = SolicitacaoJuntada.objects.get_or_create(
                        tramite=processo.ultimo_tramite,
                        solicitado=solicitado.pessoafisica,
                        motivo=form.cleaned_data.get('motivo'),
                        data_limite=form.cleaned_data.get('data_limite'),
                    )

                # Se a solicitação foi criada.
                if created:
                    # Enviando email
                    solicitacao.enviar_mail()
            return httprr(target, 'Solicitações de Juntada de Documentos adicionadas com sucesso.')
        except Exception:
            return httprr(target, 'Ocorreu um erro durante o envio da notificação.', tag='error')
    else:
        return locals()


@rtr()
@permission_required('processo_eletronico.pode_abrir_requerimento')
def editar_requerimento(request, requerimento_id):
    requerimento = Requerimento.get_requerimento_by_user(request_user=request.user, requerimento_id=requerimento_id)
    if not requerimento:
        raise PermissionDenied

    title = 'Editar Requerimento {codigo}'.format(codigo=requerimento.get_numero_requerimento())

    if not requerimento.pode_editar():
        return httprr('/admin/processo_eletronico/requerimento/',
                      message='O requerimento {} não pode ser alterado.'.format(requerimento.get_numero_requerimento()),
                      tag='error')

    form = RequerimentoFormCadastrar(request.POST or None, instance=requerimento)
    if form.is_valid():
        requerimento = form.save(commit=False)
        requerimento.save(request.user)

        return httprr(reverse_lazy('gerenciar_requerimento', current_app='processo_eletronico',
                                   kwargs={'requerimento_id': requerimento.id}), 'Requerimento atualizado com sucesso.')

    return locals()


@rtr()
@permission_required('processo_eletronico.pode_abrir_requerimento')
def cancelar_requerimento(request, requerimento_id):
    requerimento = Requerimento.get_requerimento_by_user(request_user=request.user, requerimento_id=requerimento_id)
    if not requerimento:
        raise PermissionDenied

    if not requerimento.pode_editar():
        return httprr('/admin/processo_eletronico/requerimento/',
                      message='O requerimento {} não pode ser alterado.'.format(requerimento.get_numero_requerimento()),
                      tag='error')

    try:
        requerimento.situacao = Requerimento.SITUACAO_CANCELADO
        requerimento.save(request.user)
        return httprr('/admin/processo_eletronico/requerimento/', message='Requerimento cancelado com sucesso.')
    except Exception as e:
        return httprr(reverse_lazy('gerenciar_requerimento', current_app='processo_eletronico',
                                   kwargs={'requerimento_id': requerimento.id}), str(e), tag='error')


@rtr()
@permission_required('processo_eletronico.pode_abrir_requerimento')
def finalizar_requerimento(request, requerimento_id):
    requerimento = Requerimento.get_requerimento_by_user(request_user=request.user, requerimento_id=requerimento_id)
    if not requerimento:
        raise PermissionDenied

    title = 'Finalizar Requerimento {codigo}'.format(codigo=requerimento.get_numero_requerimento())

    # Sugestao de primeiro tramite
    sugestao_primeiro_tramite = Requerimento.get_sugestao_primeiro_tramite(requerimento.tipo_processo, get_uo(request.user))

    form = FinalizarRequerimentoForm(request.POST or None, request=request, sugestao_primeiro_tramite=sugestao_primeiro_tramite)

    aviso = 'Ao finalizar este requerimento será criado um Processo Eletrônico a partir destes dados.'

    if form.is_valid():
        try:
            #
            if form.cleaned_data.get('tipo_busca_setor') == 'sugestao_primeiro_tramite':
                requerimento.destinatario_setor = sugestao_primeiro_tramite
            else:
                requerimento.destinatario_setor = form.get_destino()
            #
            requerimento.save(request.user)
            requerimento_pdf_as_html = montar_requerimento_pdf_as_html(
                request=request,
                requerente_nome=requerimento.interessado.relacionamento.nome,
                requerente_telefone=requerimento.interessado.relacionamento.telefones_institucionais,
                requerente_email=requerimento.interessado.relacionamento.email,
                requerimento_destinatario_setor=requerimento.destinatario_setor,
                requerimento_tipo_processo=requerimento.tipo_processo,
                requerimento_assunto=requerimento.assunto,
                requerimento_descricao=requerimento.descricao,
                requerimento_data_hora_emissao=datetime.today(),
                requerente_matricula_siap=requerimento.interessado.relacionamento.matricula,
                requerente_cargo=hasattr(
                    requerimento.interessado.relacionamento,
                    'cargo_emprego') and requerimento.interessado.relacionamento.cargo_emprego and '{} - {}'.format(
                    requerimento.interessado.relacionamento.cargo_emprego.grupo_cargo_emprego.nome,
                    requerimento.interessado.relacionamento.cargo_emprego.nome) or '',
                requerente_lotacao='{} - {}'.format(
                    requerimento.interessado.relacionamento.setor_lotacao,
                    requerimento.interessado.relacionamento.setor)
            )
            with transaction.atomic():
                if requerimento.pode_editar():
                    processo = requerimento.cadastrar_processo(request.user, form.cleaned_data.get('papel'), requerimento_pdf_as_html)
                else:
                    msg = 'O requerimento {} não pode ser alterado.'.format(requerimento.get_numero_requerimento())
                    return httprr('/admin/processo_eletronico/requerimento/', message=msg, tag='error')
            #
            msg = 'Requerimento finalizado com sucesso. Este processo foi gerado com base nos dados do requerimento finalizado.'
            return httprr(reverse_lazy('processo', kwargs={'processo_id': processo.id}, current_app='processo_eletronico'), msg)
        #
        except Exception as e:
            url = reverse_lazy('gerenciar_requerimento', current_app='processo_eletronico', kwargs={'requerimento_id': requerimento.id})
            return httprr(url, str(e), tag='error')

    return locals()


@rtr('processo_eletronico/templates/listar_documentos_adicionar.html')
@permission_required('processo_eletronico.pode_abrir_requerimento')
def listar_documentos_adicionar_requerimento(request, requerimento_id):
    # View para listar os documentos que podem ser adicionados em um requerimento

    requerimento = Requerimento.get_requerimento_by_user(request_user=request.user, requerimento_id=requerimento_id)
    if not requerimento:
        raise PermissionDenied

    if not requerimento.pode_editar():
        return httprr('/admin/processo_eletronico/requerimento/',
                      message='O requerimento {} não pode ser alterado.'.format(requerimento.get_numero_requerimento()),
                      tag='error')

    # Usado no template para mostrar conteudo especifico do requerimento
    is_requerimento = True

    title = 'Documentos que podem ser adicionados ao requerimento {}'.format(requerimento.get_numero_requerimento())
    setor = get_setor(request.user)
    initial = dict()
    if setor and setor.uo:
        initial = dict(campus=setor.uo.pk, setor=setor.pk, ano=datetime.today().year)
    filters = request.GET.copy()
    page = filters.pop('page', 0)
    if not filters:
        data = initial
    else:
        data = request.GET
    form = ListarDocumentosTextoForm(data, request=request)
    documentos, documentos_compartilhados, params, order_str = form.processar()

    # Exclusao e ordenacao dos documentos que podem ser adcionados
    documentos_do_requerimento_ids = DocumentoTextoRequerimento.objects.filter(requerimento=requerimento).values_list(
        'documento__id', flat=True)
    documentos_finalizados_ids = DocumentoTexto.objects.filter(status=DocumentoStatus.STATUS_FINALIZADO).values_list(
        'id', flat=True)
    documentos = documentos.exclude(id__in=documentos_do_requerimento_ids).filter(id__in=documentos_finalizados_ids)
    documentos = documentos.order_by('-data_criacao', 'identificador_tipo_documento_sigla', 'identificador_numero',
                                     'identificador_ano', 'identificador_setor_sigla')

    # Lista os documentos pessoais
    documentos_pessoais = DocumentoTextoPessoal.objects.proprios(request.user).defer('cabecalho', 'rodape', 'corpo')
    documentos_pessoais = documentos_pessoais.filter(status=DocumentoStatus.STATUS_FINALIZADO)
    documentos_pessoais = documentos_pessoais.exclude(id__in=documentos_do_requerimento_ids)
    #
    documentos_pessoais_digitalizados = DocumentoDigitalizadoPessoal.objects.filter(usuario_criacao=request.user)
    documentos_pessoais_digitalizados_digitalizados_do_requerimento_ids = DocumentoDigitalizadoRequerimentoOutros.objects.filter(requerimento=requerimento).values_list('documento__id', flat=True)
    documentos_pessoais_digitalizados = documentos_pessoais_digitalizados.exclude(id__in=documentos_pessoais_digitalizados_digitalizados_do_requerimento_ids)

    return locals()


@rtr()
@permission_required('processo_eletronico.pode_abrir_requerimento')
def adicionar_documento_requerimento(request, requerimento_id, documento_id):
    # View para adicionar um documento a um requerimento

    requerimento = Requerimento.get_requerimento_by_user(request_user=request.user, requerimento_id=requerimento_id)
    if not requerimento:
        raise PermissionDenied

    if not requerimento.pode_editar():
        return httprr('/admin/processo_eletronico/requerimento/',
                      message='O requerimento {} não pode ser alterado.'.format(requerimento.get_numero_requerimento()),
                      tag='error')

    documento = None
    try:
        documento = get_documento_or_forbidden(request.user, documento_id)
    except Exception:
        try:
            documento = get_object_or_404(DocumentoDigitalizadoPessoal, pk=documento_id)
        except Exception:
            raise Http404()

    if documento.nivel_acesso == Documento.NIVEL_ACESSO_SIGILOSO:
        raise PermissionDenied

    if documento.eh_documento_texto and not documento.estah_finalizado:
        raise PermissionDenied

    documento_requerimento = None
    if documento.eh_documento_texto:
        documento_requerimento = DocumentoTextoRequerimento()
    elif documento.eh_documento_digitalizado:
        documento_requerimento = DocumentoDigitalizadoRequerimentoOutros()
    documento_requerimento.documento = documento
    documento_requerimento.requerimento = requerimento
    documento_requerimento.save()

    return httprr(
        reverse_lazy('gerenciar_requerimento', current_app='processo_eletronico',
                     kwargs={'requerimento_id': requerimento.id}), 'Documento adicionado com sucesso ao requerimento.'
    )


@permission_required('processo_eletronico.pode_abrir_requerimento')
def verificar_integridade_documento_texto_requerimento(request, documento_requerimento_id):
    documento_requerimento = get_object_or_404(DocumentoTextoRequerimento, id=documento_requerimento_id)

    requerimento = Requerimento.get_requerimento_by_user(request_user=request.user,
                                                         requerimento_id=documento_requerimento.requerimento.id)
    if not requerimento:
        raise PermissionDenied

    documento = get_documento_or_forbidden(request.user, documento_requerimento.documento.id)

    match = reverse_lazy('gerenciar_requerimento', current_app='processo_eletronico',
                         kwargs={'requerimento_id': requerimento.id})

    for assinatura_documento in documento.assinaturadocumentotexto_set.all():
        if not assinatura_documento.validar_documento():
            return httprr(match, message='O documento "{}" foi violado.'.format(documento), tag='error')

    return httprr(match, 'O documento "{}" encontra-se íntegro.'.format(documento))


@rtr()
@permission_required('processo_eletronico.pode_abrir_requerimento')
def remover_documento_requerimento(request, documento_requerimento_id):
    documento_requerimento = get_object_or_404(DocumentoTextoRequerimento, id=documento_requerimento_id)

    requerimento = Requerimento.get_requerimento_by_user(request_user=request.user,
                                                         requerimento_id=documento_requerimento.requerimento.id)
    if not requerimento:
        raise PermissionDenied

    if not requerimento.pode_editar():
        return httprr('/admin/processo_eletronico/requerimento/',
                      message='O requerimento {} não pode ser alterado.'.format(requerimento.get_numero_requerimento()),
                      tag='error')

    documento_requerimento.delete()

    return httprr(reverse_lazy('gerenciar_requerimento', current_app='processo_eletronico',
                               kwargs={'requerimento_id': requerimento.id}), 'Documento excluído com sucesso.')


@rtr('processo_eletronico/templates/documento_upload_requerimento.html')
@permission_required('processo_eletronico.pode_abrir_requerimento')
def adicionar_documento_upload_requerimento(request, requerimento_id):
    # View para adicionar um documento externo a um requerimento

    requerimento = Requerimento.get_requerimento_by_user(request_user=request.user, requerimento_id=requerimento_id)
    if not requerimento:
        raise PermissionDenied

    if not requerimento.pode_editar():
        return httprr('/admin/processo_eletronico/requerimento/',
                      message='O requerimento {} não pode ser alterado.'.format(requerimento.get_numero_requerimento()),
                      tag='error')

    title = 'Adicionar documento externo ao requerimento {}'.format(requerimento.get_numero_requerimento())

    form = DocumentoDigitalizadoRequerimentoForm(request.POST or None, request.FILES or None)

    if form.is_valid():
        try:
            documento_digitalizado_requerimento = form.save(commit=False)

            # Seta o tipo de conferencia como "Copia Simples" - de acordo com "initial_data_04_tipo_conferencia.json"
            documento_digitalizado_requerimento.tipo_conferencia = TipoConferencia.objects.get(id=3)

            documento_digitalizado_requerimento.requerimento = requerimento
            documento_digitalizado_requerimento.save()
            form.save_m2m()

            return httprr(
                reverse_lazy('gerenciar_requerimento', current_app='processo_eletronico',
                             kwargs={'requerimento_id': requerimento.id}), 'Requerimento cadastrado com sucesso.'
            )
        except Exception as e:
            return httprr('.', message=str(e), tag='error')

    return locals()


@rtr('processo_eletronico/templates/documento_upload_requerimento.html')
@permission_required('processo_eletronico.pode_abrir_requerimento')
def editar_documento_upload_requerimento(request, documento_digitalizado_requerimento_id):
    # View para editar um documento externo em um requerimento

    documento_digitalizado_requerimento = get_object_or_404(DocumentoDigitalizadoRequerimento,
                                                            id=documento_digitalizado_requerimento_id)

    requerimento = Requerimento.get_requerimento_by_user(request_user=request.user,
                                                         requerimento_id=documento_digitalizado_requerimento.requerimento.id)
    if not requerimento:
        raise PermissionDenied

    if not requerimento.pode_editar():
        return httprr('/admin/processo_eletronico/requerimento/',
                      message='O requerimento {} não pode ser alterado.'.format(requerimento.get_numero_requerimento()),
                      tag='error')

    title = 'Editar documento externo ao requerimento {}'.format(requerimento.get_numero_requerimento())

    form = DocumentoDigitalizadoRequerimentoEditarForm(request.POST or None,
                                                       instance=documento_digitalizado_requerimento)

    if form.is_valid():
        try:
            o = form.save(commit=False)
            o.save()
            form.save_m2m()

            return httprr(
                reverse_lazy('gerenciar_requerimento', current_app='processo_eletronico',
                             kwargs={'requerimento_id': requerimento.id}), 'Requerimento cadastrado com sucesso.'
            )
        except Exception as e:
            return httprr('.', message=str(e), tag='error')

    return locals()


@login_required()
@permission_required('processo_eletronico.pode_abrir_requerimento')
def visualizar_documento_requerimento_pdf(request, documento_digitalizado_requerimento_id):
    title = 'Visualização de Documento PDF'

    documento_digitalizado_requerimento = get_object_or_404(DocumentoDigitalizadoRequerimento,
                                                            id=documento_digitalizado_requerimento_id)

    requerimento = Requerimento.get_requerimento_by_user(request_user=request.user,
                                                         requerimento_id=documento_digitalizado_requerimento.requerimento.id)
    if not requerimento:
        raise PermissionDenied

    template = loader.get_template('documento_eletronico/viewer.html')
    arquivo = documento_digitalizado_requerimento.arquivo

    context = {'title': title, 'pdf_data': arquivo}

    return HttpResponse(template.render(context, request))


@rtr()
@permission_required('processo_eletronico.pode_abrir_requerimento')
def remover_documento_upload_requerimento(request, documento_digitalizado_requerimento_id):
    documento_digitalizado_requerimento = None
    documento_pessoal = request.GET.get('dps', None)

    if documento_pessoal:
        documento_digitalizado_requerimento = get_object_or_404(DocumentoDigitalizadoRequerimentoOutros, id=documento_digitalizado_requerimento_id)
    else:
        documento_digitalizado_requerimento = get_object_or_404(DocumentoDigitalizadoRequerimento, id=documento_digitalizado_requerimento_id)

    requerimento = Requerimento.get_requerimento_by_user(request_user=request.user,
                                                         requerimento_id=documento_digitalizado_requerimento.requerimento.id)
    if not requerimento:
        raise PermissionDenied

    if not requerimento.pode_editar():
        return httprr('/admin/processo_eletronico/requerimento/',
                      message='O requerimento {} não pode ser alterado.'.format(requerimento.get_numero_requerimento()),
                      tag='error')

    documento_digitalizado_requerimento.delete()

    return httprr(reverse_lazy('gerenciar_requerimento', current_app='processo_eletronico',
                               kwargs={'requerimento_id': requerimento.id}), 'Documento excluído com sucesso.')


@rtr()
@login_required()
def solicitar_juntada_documento_interno(request, solicitacao_id, documento_id):
    solicitacao = get_object_or_404(SolicitacaoJuntada, id=solicitacao_id)
    documento = get_documento_or_forbidden(request.user, documento_id)
    processo = solicitacao.tramite.processo
    title = 'Solicitar Juntada do(a) {} ao processo {}'.format(documento, processo)
    target_url = processo.get_absolute_url() + '?tab=solicitacoes'

    if not solicitacao.pode_anexar_documento(request.user):
        return httprr(target_url, 'Este processo não permite a juntada de documento no momento.', tag='error')

    form = MotivoSolicitacaoDocumentoForm(request.POST or None, processo=processo, documento=documento)
    if form.is_valid():
        related_object_type = ContentType.objects.get_for_model(documento)
        # Cria uma solicitacao de juntada
        SolicitacaoJuntadaDocumento.objects.create(
            solicitacao_juntada=solicitacao, anexo_content_type=related_object_type, anexo_content_id=documento.id,
            motivo=form.cleaned_data.get('motivo')
        )
        return httprr(target_url,
                      'Documento enviado com sucesso. Caso não existam outros documentos para adicionar, você deve Concluir a solicitação.')
    return locals()


@login_required()
def solicitar_juntada_documento_externo(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoJuntada, id=solicitacao_id)
    if not solicitacao.pode_anexar_documento(request.user):
        raise PermissionDenied

    if solicitacao.expirou:
        solicitacao.processo.pode_solicitar_juntada_documento()
        target_url = solicitacao.tramite.processo.get_absolute_url() + '?tab=solicitacoes'
        return httprr(target_url, 'A solicitação de juntada está expirada.', tag='error')

    forms = [DocumentoUploadForm, PapelForm]
    return DocumentoUploadWizard.as_view(forms)(request, solicitacao_id=solicitacao_id)


@rtr()
@login_required()
def concluir_juntada_documento(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoJuntada, id=solicitacao_id)

    # Uma solicitacao de juntada só pode ser concluida pelo solicitado da SolicitacaoJuntada
    if solicitacao.solicitado.id != request.user.get_profile().pessoa_ptr.id or not solicitacao.estah_esperando():
        raise PermissionDenied

    processo = solicitacao.tramite.processo
    title = 'Declaração de Conclusão de Juntada de Documento ao processo {}'.format(processo)
    target_url = processo.get_absolute_url()
    if solicitacao.estah_concluida():
        return httprr(target_url, 'A solicitação de juntada do documento já foi concluída.', tag='error')
    if solicitacao.estah_expirada() or solicitacao.estah_cancelada():
        return httprr(target_url, 'A solicitação de juntada do documento é invalida.', tag='error')
    form = ConcluirSolicitacaoForm(request.POST or None, request=request)
    if form.is_valid():
        with transaction.atomic():
            solicitacao.concluir_solicitacao()
            solicitacao.save()

            # TODO - CONCLUIR SOL JUNTADA - substitui pelo atualizar_status_processo
            # solicitacao.notificar_conclusao_solicitacao()

            return httprr(target_url, 'A solicitação de juntada do documento finalizada.')

    return locals()


@rtr()
@login_required()
def deferir_solicitacao_juntada(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoJuntadaDocumento, id=solicitacao_id)
    title = 'Deferir Juntada do documento {} ao processo {}'.format(solicitacao.documento, solicitacao.processo)
    target_url = solicitacao.processo.get_absolute_url()
    if not solicitacao.pode_deferir_documento(request.user):
        return httprr(target_url, 'Solicitação não pode ser deferida.', tag='error')
    #
    form = DeferirSolicitacaoJuntadaDocumentoForm(request.POST or None, user=request.user, solicitacao=solicitacao)
    if form.is_valid():
        justificativa = form.cleaned_data['justificativa']
        try:
            solicitacao.deferir_solicitacao_juntada_documento(request.user, justificativa)
            solicitacao.save()
            return httprr(target_url, 'Solicitação deferida com sucesso.')
        except ProcessoEletronicoException as e:
            return httprr(target_url, e, tag='error')

    return locals()


@rtr()
@login_required()
def indeferir_solicitacao_juntada(request, solicitacao_id):
    solicitacao_juntada_documento = get_object_or_404(SolicitacaoJuntadaDocumento, id=solicitacao_id)
    title = 'Indeferir Juntada do documento {} ao processo {}'.format(solicitacao_juntada_documento.documento,
                                                                      solicitacao_juntada_documento.processo)
    target_url = solicitacao_juntada_documento.processo.get_absolute_url()
    if not solicitacao_juntada_documento.pode_deferir_documento(request.user):
        return httprr(target_url, 'Solicitação não pode ser deferida.', tag='error')
    form = DeferirSolicitacaoJuntadaDocumentoForm(request.POST or None, user=request.user,
                                                  solicitacao=solicitacao_juntada_documento)
    if form.is_valid():
        justificativa = form.cleaned_data['justificativa']
        solicitacao_juntada_documento.indeferir_solicitacao_juntada_documento(request.user, justificativa)
        solicitacao_juntada_documento.save()
        return httprr(target_url, 'Solicitação indeferida com sucesso.')
    return locals()


@rtr()
@login_required()
def avaliar_solicitacao_juntada_documento(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoJuntadaDocumento, id=solicitacao_id)

    target_url = solicitacao.processo.get_absolute_url()
    title = 'Avaliar solicitação de juntada do documento {} ao processo {}'.format(solicitacao.documento,
                                                                                   solicitacao.processo)

    if not solicitacao.pode_deferir_documento(request.user):
        return httprr(target_url, 'Você não possui permissão para avaliar a atual solicitação de juntada de documento.',
                      tag='error')
    return locals()


@rtr()
@login_required()
def cancelar_solicitacao_ciencia(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoCiencia, id=solicitacao_id)
    title = 'Cancelar Solicitação de Ciência para {}'.format(solicitacao.solicitado)
    target_url = solicitacao.processo.get_absolute_url()
    if not solicitacao.pode_cancelar_ciencia(request.user):
        return httprr(target_url, 'Você não possui permissão para cancelar essa solicitação.', tag='error')
    form = CancelarCienciaForm(request.POST or None, request=request, instance=solicitacao)
    if form.is_valid():
        form.save()
        return httprr(target_url, 'Solicitação cancelada com sucesso.')
    return locals()


@rtr()
@login_required()
def cancelar_solicitacao_documento(request, solicitacao_id):
    title = 'Cancelar Solicitação de Documento'
    solicitacao = get_object_or_404(SolicitacaoJuntada, id=solicitacao_id)
    target_url = solicitacao.processo.get_absolute_url()
    if solicitacao.possui_solicitacoes_de_juntada_pendentes():
        return httprr(target_url,
                      'Você não pode cancelar essa solicitação porque já existem arquivos na fila ' 'para serem juntados.',
                      tag='error')
    if not solicitacao.pode_cancelar_solicitacao(request.user):
        return httprr(target_url, 'Você não possui permissão para cancelar essa solicitação ou ela já foi aceita.',
                      tag='error')
    form = CancelarSolicitacaoJuntadaForm(request.POST or None, request=request, instance=solicitacao)
    if form.is_valid():
        form.save()
        return httprr(target_url, 'Solicitação cancelada com sucesso.')
    return locals()


# demanda_495
@rtr()
@login_required()
def processo_acompanhar(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    processo = get_object_or_404(Processo, id=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    title = 'Adicionar interesse em processo {}'.format(processo)
    target = processo.get_absolute_url()

    #
    if not processo.esta_ativo():
        return httprr(target, 'O processo não pode ser acompanhado porque não está ativo.')
    #
    if processo.pode_cadastrar_interesse():
        processo.pessoas_acompanhando_processo.add(request.user.pessoafisica)
        return httprr(target, 'Processo adicionado na lista de interesses.')
    else:
        return httprr('..', 'Processo não pode ser adicionado a lista de interesses.')

    return locals()


@rtr()
@login_required()
def processo_desacompanhar(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    processo = get_object_or_404(Processo, id=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    target = processo.get_absolute_url()

    if not processo.pode_remover_interesse():
        return httprr(target, 'Não é possível remover pois o processo não consta na lista de interesses.')

    processo.pessoas_acompanhando_processo.remove(request.user.pessoafisica)
    return httprr(target, 'Processo removido da lista de interesses.')


@rtr('processo_eletronico/encaminhar_via_barramento.html')
@permission_required('conectagov_pen.pode_tramitar_pelo_barramento')
def encaminhar_via_barramento(request, processo_id):
    # verifica_pode_ver_processo(request.user, processo_id)
    # Último trâmite realizado por completo.
    processo = get_object_or_404(Processo, pk=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    verifica_pode_editar_processo(processo)
    title = 'Encaminhar Processo Externamente {}'.format(processo.numero_protocolo)
    if not barramento_disponivel():
        return httprr(processo.get_absolute_url(),
                      'O barramento do governo federal (ConectaGOV) está indisponível no momento, tente novamente mais tarde.',
                      'error')
    if not processo.pode_ser_encaminhado():
        return httprr(processo.get_absolute_url(),
                      'A operação não pode ser realizada porque o processo já foi encaminhado.')

    if request.method == 'POST':
        form = TramiteFormEncaminharViaBarramento(data=request.POST, request=request)
        if form.is_valid():
            form.save(processo=processo)
            return httprr(processo.get_absolute_url(), '')
    else:
        form = TramiteFormEncaminharViaBarramento()

    return locals()


@rtr()
@login_required()
def processo_eletronico_manutencao(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    title = 'Manutenção do Processo Eletrônico'

    form = BuscaProcessoEletronicoManutencaoForm(request.POST or None, request=request)

    processos = None
    if form.is_valid():
        if form.cleaned_data.get('tipo_busca') == 'numero_protocolo':
            processos = Processo.objects.filter(numero_protocolo=form.cleaned_data.get('parametro'))
        else:
            if form.cleaned_data.get('tipo_busca') == 'numero_protocolo_fisico':
                processos = Processo.objects.filter(numero_protocolo_fisico=form.cleaned_data.get('parametro'))
            else:
                if form.cleaned_data.get('tipo_busca') == 'id_processo':
                    processos = Processo.objects.filter(id=form.cleaned_data.get('parametro'))

    return locals()


@rtr()
@login_required()
def processo_eletronico_manutencao_altera_status(request):
    if not request.user.is_superuser:
        raise PermissionDenied

    title = 'Manutenção do Processo Eletrônico (Alterar Status)'

    form = BuscaProcessoEletronicoManutencaoAlteraStatusForm(request.POST or None, request=request)

    processos = None
    if form.is_valid():
        if form.cleaned_data.get('identificador') and form.cleaned_data.get('parametro'):
            try:
                Processo.objects.filter(id=form.cleaned_data.get('identificador')).update(
                    status=form.cleaned_data.get('parametro'))

                return httprr(
                    reverse_lazy('processo_eletronico_manutencao_altera_status', current_app='processo_eletronico'),
                    'Sucesso.')

            except Exception as e:
                return httprr('.', message=str(e), tag='error')

    return locals()


@rtr()
@login_required()
def processo_eletronico_numeros(request):
    if not request.user.is_superuser:
        raise PermissionDenied()

    # ---------------------------------------
    # Validacoes e Setor escolhido
    # ---------------------------------------
    setor_escolhido, setores_chefe, setor_escolhido, msg_orientacao_acesso = iniciar_gerenciamento_compartilhamento(
        request)

    title = 'Processo Eletrônico em Números'

    def arvore_setor(setor, lista=None):
        if lista is None:
            lista = []
        areas_vinculacao = []
        for area_vinculacao in setor.areas_vinculacao.all():
            areas_vinculacao.append('<div class="tree-tag">%s</div>' % area_vinculacao.descricao)
        destaque = areas_vinculacao and 'negrito' or 'cinza'
        areas_vinculacao = areas_vinculacao and ''.join(areas_vinculacao) or ''

        nums = NumerosProcessoEletronicoPorSetor.objects.filter(setor_id=setor.id)
        if nums.exists():
            num = nums[0]
            lista.append(
                '<li>'
                '<span class="{}">{}</span> {} '
                '<div class="tree-tag"><b>Abriu processos:</b> {}</div>'
                '<div class="tree-tag"><b>Tramitou processos:</b> {}</div>'.format(destaque, setor, areas_vinculacao,
                                                                                   num.criou, num.tramitou)
            )

        if setor.setor_set.exists():
            lista.append('<ul>')
            for subsetor in setor.setor_set.all():
                arvore_setor(subsetor, lista)
            lista.append('</ul>')
        lista.append('</li>')
        return mark_safe(''.join(lista))

    setores_numeros = list()
    sigla_reitoria = get_sigla_reitoria()
    if setores_chefe.filter(sigla=sigla_reitoria).exists():
        setores_numeros.append(arvore_setor(Setor.objects.get(sigla=sigla_reitoria), []))
    else:
        for setor in setores_chefe:
            setores_numeros.append(arvore_setor(setor, []))

    setores_numeros_todos = list()
    if request.user.is_superuser:
        setores_numeros_todos.append(arvore_setor(Setor.objects.get(sigla=sigla_reitoria), []))

    por_tipo = NumerosProcessoEletronicoPorTipo.objects.all().order_by('-qtd')

    geral = NumerosProcessoEletronicoGeral.objects.all()

    uo = request.user.get_relacionamento().setor.uo
    tempo_medio_por_tipo = NumerosProcessoEletronicoTempoPorTipo.objects.filter(uo_origem_interessado=uo).order_by(
        '-tempo_medio')

    return locals()


# Verificar se é melhor passar esse método para utils
def get_consulta_publica(numero_protocolo=None, interessado=None, assunto=None, todas_situacoes=None, status=None, data_inicio=None, data_fim=None, tipo_processo=None):
    manager = Processo.objects
    resultado = {}
    if numero_protocolo:
        manager = manager.filter(
            Q(numero_protocolo=numero_protocolo)
            | Q(numero_protocolo_fisico=numero_protocolo)
        )
    if interessado:
        manager = manager.filter(
            Q(interessados__nome__icontains=interessado)
            | Q(interessados__pessoafisica__cpf__icontains=interessado)
            | Q(interessados__pessoajuridica__cnpj__icontains=interessado)
        )
    if assunto:
        manager = manager.filter(assunto__icontains=assunto)
    if not todas_situacoes:
        manager = manager.filter(status=status)
    #
    if data_inicio:
        manager = manager.filter(data_hora_criacao__gte=data_inicio)
    #
    if data_fim:
        manager = manager.filter(data_hora_criacao__lte=data_fim)
    #
    if tipo_processo:
        manager = manager.filter(tipo_processo=tipo_processo)

    manager = manager.order_by('-data_hora_criacao')

    if manager.exists():
        resultado = {'processos_qs': manager}

    return resultado


@rtr()
def consulta_publica(request):
    form = ConsultaPublicaProcessoForm(request.GET or None)
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    title = 'Consulta de Processos Eletrônicos'
    category = 'Consultas'
    icon = 'file'

    if form.is_valid():
        try:
            resultado = get_consulta_publica(
                form.cleaned_data['numero_protocolo'],
                form.cleaned_data['interessado'],
                form.cleaned_data['assunto'],
                form.cleaned_data['todas_situacoes'],
                form.cleaned_data['status'],
                form.cleaned_data['data_inicio'],
                form.cleaned_data['data_final'],
                form.cleaned_data['tipo_processo']
            )
            if resultado.get('processos_qs') and resultado['processos_qs'].exists():
                processos_qs = resultado['processos_qs']
                return render('consulta_publica_processos.html', locals())
            else:
                return httprr('.', 'Nenhum processo encontrado.', 'error')

        except KeyError:
            return httprr('.', 'Nenhum processo encontrado.', 'error')

    return locals()


@login_required()
@rtr()
def permissoes(request):
    uc = 'proc'

    # ---------------------------------------
    # Validacoes e Setor escolhido
    # ---------------------------------------
    setor_escolhido, setores_chefe, setor_escolhido, msg_orientacao_acesso = iniciar_gerenciamento_compartilhamento(
        request)
    title = f'Permissões para Documentos e Processos Eletrônicos - {setor_escolhido}'
    # -----------------------------------------------------
    # Permite conceder permissões a pess
    # -----------------------------------------------------
    form = GerenciarCompartilhamentoProcessoForm(request.POST or None, setor_escolhido=setor_escolhido)

    # Carrega os dados que ja esta no banco
    form.fields[
        'pessoas_permitidas_para_operar_processo'].initial = CompartilhamentoProcessoEletronicoSetorPessoa.objects.filter(
        setor_dono=setor_escolhido, nivel_permissao=Processo.PERMISSAO_OPERAR_PROCESSO
    ).values_list('pessoa_permitida', flat=True)
    form.fields[
        'pessoas_permitidas_para_operar_e_criar_processos'].initial = CompartilhamentoProcessoEletronicoSetorPessoa.objects.filter(
        setor_dono=setor_escolhido, nivel_permissao=Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO
    ).values_list('pessoa_permitida', flat=True)
    form.fields[
        'pessoas_permitidas_para_cadastrar_retorno_programado'].initial = CompartilhamentoProcessoEletronicoSetorPessoa.objects.filter(
        setor_dono=setor_escolhido, nivel_permissao=Processo.PERMISSAO_RETORNO_PROGRAMADO
    ).values_list('pessoa_permitida', flat=True)

    if form.is_valid():
        setores_operar = form.cleaned_data.get('setores_permitidos_para_operar_processo', None)
        setores_operar_criar = form.cleaned_data.get('setores_permitidos_para_operar_e_criar_processos', None)

        pessoas_operar = form.cleaned_data.get('pessoas_permitidas_para_operar_processo', None)
        pessoas_operar_criar = form.cleaned_data.get('pessoas_permitidas_para_operar_e_criar_processos', None)
        pessoas_retorno_programado = form.cleaned_data.get('pessoas_permitidas_para_cadastrar_retorno_programado', None)

        Processo.atualizar_compartilhamentos(request.user, setor_escolhido, setores_operar, setores_operar_criar,
                                             pessoas_operar, pessoas_operar_criar, pessoas_retorno_programado)

        messages.success(request, 'Operação realizada com sucesso.')
    return locals()


@rtr()
@login_required()
def adicionar_rotulo(request, tramite_id):
    tramite = get_object_or_404(Tramite, pk=tramite_id)
    tramite.processo.pode_ler(user=request.user, lancar_excecao=True)
    title = 'Adicionar Rótulo'

    verifica_pode_editar_processo(tramite.processo)
    form = AdicionarRotuloForm(request.POST or None, request=request, tramite=tramite)
    if form.is_valid():
        if form.cleaned_data.get('rotulo') == 'nenhum':
            tramite.rotulo = None
        else:
            tramite.rotulo = form.cleaned_data.get('rotulo')
        tramite.save()
        return httprr('..', 'Rótulo adicionado com sucesso.')

    return locals()


@login_required()
@rtr('processo_eletronico/templates/permissoes.html')
def gerenciar_compartilhamento_processos_poder_de_chefe(request):
    title = 'Permissões para Documentos e Processos Eletrônicos'
    uc = 'procpc'

    # ---------------------------------------
    # Validacoes, Setor escolhido e dados iniciais
    # ---------------------------------------
    setor_escolhido, setores_chefe, setor_escolhido, msg_orientacao_acesso = iniciar_gerenciamento_compartilhamento(
        request)

    pessoas_com_poder_de_chefe_oficio = CompartilhamentoProcessoEletronicoPoderDeChefe.objects.filter(setor_dono=setor_escolhido, de_oficio=True)

    pessoas_com_poder_de_chefe = CompartilhamentoProcessoEletronicoPoderDeChefe.objects.filter(
        setor_dono=setor_escolhido, de_oficio=False).values_list(
        'pessoa_permitida', flat=True
    )

    # Permite conceder permissões a pessoas e setores
    # -----------------------------------------------------
    form = GerenciarCompartilhamentoPoderChefeProcessoForm(request.POST or None, setor_escolhido=setor_escolhido, pessoas_com_poder_de_chefe_oficio=pessoas_com_poder_de_chefe_oficio)

    # Carrega os dados que ja estao no banco
    form.fields['pessoas_com_poder_de_chefe'].initial = pessoas_com_poder_de_chefe

    if form.is_valid():
        pessoas_poder_de_chefe = form.cleaned_data.get('pessoas_com_poder_de_chefe', None)
        Processo.atualizar_compartilhamentos__setor_poder_chefe(request.user, setor_escolhido, pessoas_poder_de_chefe)
        messages.success(request, 'Operação realizada com sucesso.')
        return httprr('.')

    return locals()


@rtr()
@login_required()
def atribuir_processo(request, tramite_id):
    tramite = get_object_or_404(Tramite, pk=tramite_id)
    tramite.processo.pode_ler(user=request.user, lancar_excecao=True)
    title = 'Atribuir Processo'
    verifica_pode_editar_processo(tramite.processo)

    # Permissão negada caso não seja chefe do setor atual do processo em questao
    # if not tramite.processo.setor_atual in get_setores_que_sou_chefe_hoje(request.user):
    #    raise PermissionDenied()
    if not tramite.processo.pode_atribuir_processo(request.user):
        raise PermissionDenied('Você não tem permissão para atribuir esse processo.')

    form = AtribuirProcessoForm(request.POST or None, request=request, tramite=tramite)
    if form.is_valid():
        tramite.atribuido_para = form.cleaned_data.get('pessoa_fisica')
        tramite.atribuido_por = request.user.get_profile()
        tramite.atribuido_em = datetime.now()
        tramite.save()
        return httprr('..', 'Atribuição realizada com sucesso.')

    return locals()


@rtr()
def visualizar_capa_processo(request, processo_id, acesso_publico=False):
    processo = get_processo(processo_id, acesso_publico)
    eh_anonimo = request.user.is_anonymous
    if eh_anonimo:
        if not processo.pode_ler_consulta_publica():
            return httprr('/processo_eletronico/consulta_publica/', message=MSG_PERMISSAO_NEGADA_PROCESSO_CONSULTA_PUBLICA, tag='error')
    else:
        processo.pode_ler(user=request.user, lancar_excecao=True)

    return render('processo_eletronico/imprimir_capa_processo.html', locals())


@rtr()
@login_required()
def visualizar_requerimento_processo(request, processo_id):
    agora = get_datetime_now()
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
    uo = get_uo(request.user)
    processo = get_object_or_404(Processo, pk=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    return render('processo_eletronico/imprimir_capa_processo.html', locals())


@rtr()
def visualizar_processo(request, processo_id, acesso_publico=False):
    instance = get_processo(processo_id, acesso_publico)
    title = 'Visualização do Processo {}'.format(instance)
    eh_anonimo = request.user.is_anonymous
    pessoa = None
    if eh_anonimo:
        super_template_processo = 'admin/base_anonima.html'
        if not acesso_publico:
            raise Http404

        servicos_anonimos = layout.gerar_servicos_anonimos(request)
        category = 'Consultas'
        icon = 'file'
        if not instance.pode_ler_consulta_publica():
            return httprr('/processo_eletronico/consulta_publica/', message=MSG_PERMISSAO_NEGADA_PROCESSO_CONSULTA_PUBLICA, tag='error')
    else:
        super_template_processo = 'admin/base.html'
        try:
            instance = Processo.atualizar_status_processo(instance)
        except ValidationError as e:
            messages.error(request, str(e))
        pessoa = request.user.get_profile()
        instance.pode_ler(user=request.user, lancar_excecao=True)
        if instance.get_ciencia_pendente(pessoa):
            return dar_ciencia(request, instance.id)

    if instance.status == ProcessoStatus.STATUS_ANEXADO:
        processo_pk = Anexacao.objects.filter(processo_anexado_id=instance.id).values_list('processo_anexador__id', flat=True)
        return processo(request, processo_pk)

    documentos_do_processo = instance.get_todos_documentos_processo(reverse=False)
    doc = request.GET.get('doc', None)
    lista_documentos = ['capa_processo']
    if documentos_do_processo:
        lista_documentos += documentos_do_processo

    documento_selecionado = 'capa_processo'
    if doc and doc != 'capa_processo':
        documento_selecionado = doc
        try:
            doc = int(doc)
        except Exception:
            return httprr('..', 'Número do documento inválido.', 'error')
        documento_selecionado = documentos_do_processo[doc]

    if 'ajax' in request.GET:
        html = render_to_string('processo_eletronico/templates/visualizar_processo_conteudo_documento.html', locals())
        return JsonResponse({'doc': doc, 'html': html})

    return locals()


@rtr('processo_eletronico/dashboard_processos_setor.html')
@login_required()
def dashboard_processos_setor(request, setor_id):
    setor = get_object_or_404(Setor, pk=setor_id)
    pessoa = request.user.get_profile()
    title = 'Dashboard de processos - {}'.format(setor)

    # setores_usuario = get_todos_setores(request.user)
    # Novo esquema de permissoes do processo e documento eletronico
    setores_usuario = Tramite.get_todos_setores(user=request.user)

    if not setor in setores_usuario:
        raise PermissionDenied()

    funcionarios_do_setor_destino = setor.get_funcionarios()
    if funcionarios_do_setor_destino.exists():
        qtd_tramites_funcionario = list()
        for funcionario in funcionarios_do_setor_destino:
            tramites_de_entrada = Tramite.get_caixa_entrada(setores=Setor.objects.filter(id=setor.id))
            tramites_funcionario = tramites_de_entrada.filter(atribuido_para=funcionario)
            qtd_tramites_atribuidos_para_funcionario = tramites_funcionario.filter(em_atendimento=False,
                                                                                   atendido=False).count()
            qtd_tramites_em_atendimento_pelo_funcionario = tramites_funcionario.filter(em_atendimento=True,
                                                                                       atendido=False).count()
            qtd_tramites_atendidos_pelo_funcionario = tramites_funcionario.filter(atendido=True).count()
            if qtd_tramites_atribuidos_para_funcionario > 0 or qtd_tramites_em_atendimento_pelo_funcionario > 0 or qtd_tramites_atendidos_pelo_funcionario > 0:
                qtd_tramites_funcionario.append(
                    {
                        'funcionario': funcionario,
                        'qtd_pendentes': qtd_tramites_atribuidos_para_funcionario,
                        'qtd_em_atendimento': qtd_tramites_em_atendimento_pelo_funcionario,
                        'qtd_atendidos': qtd_tramites_atendidos_pelo_funcionario,
                    }
                )

        qtd_tramites_funcionario = sorted(qtd_tramites_funcionario, key=lambda i: (i['qtd_em_atendimento']))

    return locals()


@rtr('processo_eletronico/distribuicao_interna_processos_setor.html')
@login_required()
def distribuicao_interna_processos_setor(request, setor_id):
    setor = get_object_or_404(Setor, pk=setor_id)
    pessoa = request.user.get_profile()
    title = 'Distribuição Interna dos Processos - {}'.format(setor)

    # setores_usuario = get_todos_setores(request.user)
    # Novo esquema de permissoes do processo e documento eletronico
    setores_usuario = Tramite.get_todos_setores(user=request.user)

    # servidor_logado_eh_chefe_do_setor = True if setor in get_setores_que_sou_chefe_hoje(request.user) else False
    servidor_logado_eh_chefe_do_setor = True if setor in setores_que_sou_chefe_ou_tenho_poder_de_chefe(
        request.user) else False

    form = FiltroCaixaEntradaSaidaForm(request.GET, request=request, setores_usuario=setores_usuario)
    filtros = None
    filtros_processo = None

    if form.is_valid():
        filtros = form.processar()
        filtros_processo = form.processar_processo()

    if not setor in setores_usuario:
        raise PermissionDenied()

    def _tratar_tramites_processos_apensados(tramites):
        tramites_tratados = list()
        apensamento_ids = set()
        for tramite in tramites:
            apensamento = tramite.processo.get_apensamento()
            apensamento_id = None
            if apensamento:
                apensamento_id = apensamento.id

            if not apensamento_id or apensamento_id not in apensamento_ids:
                tramites_tratados.append(tramite)

            apensamento_ids.add(apensamento_id)

        return tramites_tratados

    tramites_de_entrada = Tramite.get_caixa_entrada(setores=Setor.objects.filter(id=setor_id),
                                                    filtros=filtros).order_by('data_hora_encaminhamento')
    solicitado = request.user.get_profile().pessoa_ptr
    despachos_solicitados = SolicitacaoDespacho.objects.filter(status=SolicitacaoStatus.STATUS_ESPERANDO).filter(
        Q(processo__in=tramites_de_entrada.values_list('processo', flat=True)) | Q(solicitado=solicitado)
    )
    pendentes = _tratar_tramites_processos_apensados(
        tramites_de_entrada.filter(data_hora_recebimento__isnull=False, em_atendimento=False).order_by('prioridadetramite__prioridade', 'data_hora_encaminhamento')
        .exclude(processo__in=despachos_solicitados.values_list('processo', flat=True))
    )

    andamento = _tratar_tramites_processos_apensados(
        tramites_de_entrada.filter(data_hora_recebimento__isnull=False, em_atendimento=True, atendido=False)
        .order_by('prioridadetramite__prioridade', 'data_hora_encaminhamento')
        .exclude(processo__in=despachos_solicitados.values_list('processo', flat=True))
    )

    concluidos = _tratar_tramites_processos_apensados(
        tramites_de_entrada.filter(data_hora_recebimento__isnull=False, processo__data_finalizacao__isnull=True,
                                   atendido=True).order_by('prioridadetramite__prioridade', 'data_hora_encaminhamento')
        .exclude(processo__in=despachos_solicitados.values_list('processo', flat=True))
    )

    dict_quadros = {}

    processos = collections.OrderedDict()
    processos['Pendentes'] = list()
    processos['Em Atendimento'] = list()
    processos['Atendidos'] = list()
    tem_processo = pendentes or andamento or concluidos

    for registro in pendentes:
        processos['Pendentes'].append(
            [registro.processo.id, registro.processo.numero_protocolo_fisico, registro.processo.assunto,
             registro.processo])

    for registro in andamento:
        processos['Em Atendimento'].append(
            [registro.processo.id, registro.processo.numero_protocolo_fisico, registro.processo.assunto,
             registro.processo])

    for registro in concluidos:
        processos['Atendidos'].append(
            [registro.processo.id, registro.processo.numero_protocolo_fisico, registro.processo.assunto,
             registro.processo])

    return locals()


@rtr()
@login_required()
def atender_processo(request, tramite_id):
    tramite = get_object_or_404(Tramite, pk=tramite_id)
    if tramite.atribuido_para and tramite.atribuido_para.pessoafisica == request.user.get_profile():
        if tramite.em_atendimento:
            tramite.atendido = True
        else:
            tramite.em_atendimento = True
        tramite.save()
        return httprr(tramite.processo.get_absolute_url(), 'Registro de atendimento atualizado.')
    else:
        raise PermissionDenied


@login_required()
@csrf_exempt
def movimentacao_interna_processo(request):
    if request.POST:
        processo = request.POST.get('processo', 0)
        coluna = int(request.POST.get('coluna', 0))
        if not processo or not coluna:
            raise PermissionDenied('Erro')

        if Tramite.objects.filter(processo=processo).exists():
            tramite = Tramite.objects.filter(processo=processo).order_by('-id')[0]
            if coluna == 3:
                tramite.atendido = True
                tramite.em_atendimento = True
            elif coluna == 2:
                tramite.em_atendimento = True
                tramite.atendido = False
            else:
                tramite.atendido = False
                tramite.em_atendimento = False

            tramite.save()

    return HttpResponse('Ok')


@permission_required('processo_eletronico.pode_abrir_requerimento')
def get_hipoteses_legais_by_processo_nivel_acesso(request, processo_nivel_acesso_id):
    processo_nivel_acesso_id = int(processo_nivel_acesso_id)
    nivel_acesso = None
    if processo_nivel_acesso_id == Processo.NIVEL_ACESSO_PRIVADO:
        nivel_acesso = NivelAcessoEnum.SIGILOSO
    elif processo_nivel_acesso_id == Processo.NIVEL_ACESSO_RESTRITO:
        nivel_acesso = NivelAcessoEnum.RESTRITO

    hipoteses_legais = list()
    if nivel_acesso:
        # Este for está sendo feito para poder obter a descrição da Hipótese Legal de acordo com o que está sendo definido
        # no respectivo método __str__.
        for hl in HipoteseLegal.objects.filter(nivel_acesso=nivel_acesso.name):
            hipoteses_legais.append({'id': hl.id, 'descricao': str(hl)})

    return JsonResponse({'hipoteses_legais': [{'id': '', 'descricao': '---------'}] + hipoteses_legais})


@permission_required('processo_eletronico.delete_tramitedistribuicao')
def remover_distribuicao_tramite(request, tramite_distribuicao_pk):
    tramite_distribuicao = get_object_or_404(TramiteDistribuicao, pk=tramite_distribuicao_pk)
    if not tramite_distribuicao.pode_excluir(request.user):
        raise PermissionDenied()

    tramite_distribuicao.delete()
    return httprr("/admin/processo_eletronico/tramitedistribuicao", 'Remoção realizada com sucesso.')


def imprimir_processo_visualizacao_publica(request, processo_uuid):
    try:
        processo = get_object_or_404(Processo, uuid=processo_uuid)
    except ValidationError:
        raise Http404

    pode_ler = processo.pode_ler_consulta_publica()
    if not pode_ler:
        return httprr('/processo_eletronico/consulta_publica/',
                      message="Um processo só pode ser visualizado nas seguintes hipóteses: se ele for público e o seu tipo permitir ou estiver vinculado a contrato.",
                      tag='error')
    try:
        pdf = processo.get_pdf(user=request.user, eh_consulta_publica=True)
        return HttpResponse(pdf, content_type='application/pdf')
    except Exception as e:
        raise e
        return httprr('/', message="Ocorreu um erro ao gerar o arquivo PDF deste processo.", tag='error')


@rtr()
@login_required()
def minhas_permissoes_processos_documentos(request):
    title = 'Minhas Permissões para Processos e Documentos Eletrônicos'
    url = reverse_lazy('remover_permissao_processo_documento', current_app='processo_eletronico')
    tipo_visualizacao = request.GET.get('v')
    # pp: por permissao / ps: por setor
    if not tipo_visualizacao:
        tipo_visualizacao = 'pp'

    user_permissoes = request.user

    # ================================================================================
    # ORGANIZA AS PERMISSOES POR TIPO DE PERMISSÃO
    # ================================================================================

    # - Lista as permissões individuais
    # -------------------------------------

    # Setores que tenho Poder de chefe: dizer o que pode fazer nesses setores
    lista_setores_que_tenho_poder_de_chefe_oficio = CompartilhamentoProcessoEletronicoPoderDeChefe.objects.filter(
        pessoa_permitida=user_permissoes.pessoafisica, de_oficio=True)
    lista_setores_que_tenho_poder_de_chefe = CompartilhamentoProcessoEletronicoPoderDeChefe.objects.filter(
        pessoa_permitida=user_permissoes.pessoafisica, de_oficio=False)

    # Setores que posso operar processos eletrônicos
    lista_processo_setores_pessoa_operar = CompartilhamentoProcessoEletronicoSetorPessoa.objects.filter(
        nivel_permissao=Processo.PERMISSAO_OPERAR_PROCESSO, pessoa_permitida=user_permissoes.pessoafisica
    )

    # Setores que posso operar e criar processos eletrônicos
    lista_processo_setores_pessoa_operar_criar = CompartilhamentoProcessoEletronicoSetorPessoa.objects.filter(
        nivel_permissao=Processo.PERMISSAO_OPERAR_CRIAR_PROCESSO, pessoa_permitida=user_permissoes.pessoafisica
    )

    # Setores que posso ler documentos
    lista_documentos_setores_pessoa_ler = CompartilhamentoSetorPessoa.objects.filter(
        pessoa_permitida=user_permissoes.pessoafisica, nivel_permissao=NivelPermissao.LER)

    # Setores que posso editar e ler documentos
    lista_documentos_setores_pessoa_editar_ler = CompartilhamentoSetorPessoa.objects.filter(
        pessoa_permitida=user_permissoes.pessoafisica, nivel_permissao=NivelPermissao.EDITAR)

    # - Lista as permissões coletivas
    # -------------------------------------

    # Setores do usuario que serao considerados nas permissoes
    ids_setores = list()
    setores_chefe = setores_que_sou_chefe(user_permissoes)
    setor_user = get_setor(user_permissoes)
    if setor_user:
        ids_setores.append(setor_user.id)
    if setores_chefe:
        ids_setores += setores_chefe.values_list('id', flat=True)
    setores = Setor.objects.filter(pk__in=set(ids_setores))

    # ================================================================================
    # ORGANIZA AS PERMISSOES POR TIPO DE PERMISSÃO
    # ================================================================================

    if tipo_visualizacao == 'ps':

        # Pegando os setores das permissoes individuais
        qs_setores_1 = Tramite.get_todos_setores(user_permissoes, deve_poder_criar_processo=True)
        qs_setores_2 = Tramite.get_todos_setores(user_permissoes, deve_poder_criar_processo=False)
        meus_setores_permissoes_individuais = qs_setores_1 | qs_setores_2

        # Com os setores agora pega as permissoes em cada lista adicionando na lista
        #   - setor
        #   - permissao
        #   - link para excluir permissao (quando puder)
        # setorA -> {'setor': setor, 'lista_permissoes':
        #                                 [{'descricao_permissao': 'Setores que posso ...',
        #                                   'descricao_atribuicao': 'Atribuída de individualmente ...',
        #                                   'quem_concedeu': xyz,
        #                                   'link_excluir': link},
        #                                  {'descricao_permissao': 'Setores que posso ...',
        #                                   'descricao_atribuicao': 'Atribuída de forma coletiva ao setor',
        #                                   'quem_concedeu': xyz,
        #                                   'link_excluir': link}]
        # lista_permissoes_por_setor = [setorA, ...]
        meus_setores_todos = meus_setores_permissoes_individuais
        lista_permissoes_por_setor = list()

        for setor in meus_setores_todos:
            setor_permissao_dict = dict()
            setor_permissao_dict['setor'] = setor

            setor_permissao_dict['permissoes'] = list()

            # COLETA AS PERMISSOES POR SETOR
            # -------------------------------------
            # Busca as permissoes nesse setor na lista: Individual - lista_setores_que_tenho_poder_de_chefe
            if lista_setores_que_tenho_poder_de_chefe:
                permissoes = lista_setores_que_tenho_poder_de_chefe.filter(setor_dono_id=setor.id)
                for p in permissoes:
                    permissoes_dict = dict()
                    permissoes_dict['descricao_permissao'] = 'Tenho poder de chefe'
                    permissoes_dict['descricao_atribuicao'] = 'Atribuída individualmente'
                    permissoes_dict['quem_concedeu'] = p.usuario_criacao
                    permissoes_dict['quem_concedeu_quando'] = p.data_criacao
                    permissoes_dict['link_excluir'] = mark_safe(f'<a href="{url}/?idp={p.id}&tp=pdc" class="btn danger">Remover</a>')
                    setor_permissao_dict['permissoes'].append(permissoes_dict)

            # Busca as permissoes nesse setor na lista: Individual - lista_processo_setores_pessoa_operar
            if lista_processo_setores_pessoa_operar:
                permissoes = lista_processo_setores_pessoa_operar.filter(setor_dono_id=setor.id)
                for p in permissoes:
                    permissoes_dict = dict()
                    permissoes_dict['descricao_permissao'] = 'Posso operar processo'
                    permissoes_dict['descricao_atribuicao'] = 'Atribuída individualmente'
                    permissoes_dict['quem_concedeu'] = p.usuario_criacao
                    permissoes_dict['quem_concedeu_quando'] = p.data_criacao
                    permissoes_dict['link_excluir'] = mark_safe(f'<a href="{url}/?idp={p.id}&tp=psp" class="btn danger">Remover</a>')
                    setor_permissao_dict['permissoes'].append(permissoes_dict)

            # Busca as permissoes nesse setor na lista: Individual - lista_processo_setores_pessoa_operar_criar
            if lista_processo_setores_pessoa_operar_criar:
                permissoes = lista_processo_setores_pessoa_operar_criar.filter(setor_dono_id=setor.id)
                for p in permissoes:
                    permissoes_dict = dict()
                    permissoes_dict['descricao_permissao'] = 'Posso operar e criar processo'
                    permissoes_dict['descricao_atribuicao'] = 'Atribuída individualmente'
                    permissoes_dict['quem_concedeu'] = p.usuario_criacao
                    permissoes_dict['quem_concedeu_quando'] = p.data_criacao
                    permissoes_dict['link_excluir'] = mark_safe(f'<a href="{url}/?idp={p.id}&tp=psp" class="btn danger">Remover</a>')
                    setor_permissao_dict['permissoes'].append(permissoes_dict)

            # Busca as permissoes nesse setor na lista: Individual - lista_documentos_setores_pessoa_ler
            if lista_documentos_setores_pessoa_ler:
                permissoes = lista_documentos_setores_pessoa_ler.filter(setor_dono_id=setor.id)
                for p in permissoes:
                    permissoes_dict = dict()
                    permissoes_dict['descricao_permissao'] = 'Posso ler documentos'
                    permissoes_dict['descricao_atribuicao'] = 'Atribuída individualmente'
                    permissoes_dict['quem_concedeu'] = p.usuario_criacao
                    permissoes_dict['quem_concedeu_quando'] = p.data_criacao
                    permissoes_dict['link_excluir'] = mark_safe(f'<a href="{url}/?idp={p.id}&tp=dsp" class="btn danger">Remover</a>')
                    setor_permissao_dict['permissoes'].append(permissoes_dict)

            # Busca as permissoes nesse setor na lista: Individual - lista_documentos_setores_pessoa_editar_ler
            if lista_documentos_setores_pessoa_editar_ler:
                permissoes = lista_documentos_setores_pessoa_editar_ler.filter(setor_dono_id=setor.id)
                for p in permissoes:
                    permissoes_dict = dict()
                    permissoes_dict['descricao_permissao'] = 'Posso ler e editar documentos'
                    permissoes_dict['descricao_atribuicao'] = 'Atribuída individualmente'
                    permissoes_dict['quem_concedeu'] = p.usuario_criacao
                    permissoes_dict['quem_concedeu_quando'] = p.data_criacao
                    permissoes_dict['link_excluir'] = mark_safe(f'<a href="{url}/?idp={p.id}&tp=dsp" class="btn danger">Remover</a>')
                    setor_permissao_dict['permissoes'].append(permissoes_dict)

            # Adiciona todas as permissoes coletadas
            # -------------------------------------
            lista_permissoes_por_setor.append(setor_permissao_dict)

    return locals()


@login_required()
@transaction.atomic()
def remover_permissao_processo_documento(request):
    url = reverse_lazy('minhas_permissoes_processos_documentos', current_app='processo_eletronico')
    try:
        permissoes = dict()
        permissoes['pdc'] = CompartilhamentoProcessoEletronicoPoderDeChefe
        permissoes['psp'] = CompartilhamentoProcessoEletronicoSetorPessoa
        permissoes['dsp'] = CompartilhamentoSetorPessoa

        id_permissao = request.GET.get('idp')
        tipo_permissao = request.GET.get('tp')
        if id_permissao and tipo_permissao and tipo_permissao in permissoes:
            permissao = permissoes.get(tipo_permissao)
            permissao = permissao.objects.get(id=int(id_permissao))
            if permissao.pessoa_permitida.id == request.user.pessoafisica.id:
                setor_permissao = permissao.setor_dono
                chefes_setor = setor_permissao.chefes
                descricao_permissao = permissao.__str__()
                permissao.delete()
                Notificar.remover_permissao_processo_documento(request.user, chefes_setor, descricao_permissao)
                return httprr(url, 'Remoção realizada com sucesso.')
            else:
                return httprr(url, 'Você não tem permissão para realizar isso.', 'error')
        else:
            return httprr(url, 'Permissão inválida.', 'error')
    #
    except Exception as e:
        return httprr(url, message=str(e), tag='error')


@rtr()
@group_required('Gestão Nível de Acesso dos Processos Documentos Eletrônicos')
def configurar_orientacao_nivel_acesso(request):
    title = 'Orientações de seleção de Nível de Acesso'

    conf = ConfiguracaoInstrucaoNivelAcesso.objects.all()
    if conf:
        conf = conf[0]
    else:
        conf = ConfiguracaoInstrucaoNivelAcesso()
        conf.save()

    form = ConfiguracaoInstrucaoNivelAcessoForm(data=request.POST or None, instance=conf)

    if request.method == 'POST':
        if form.is_valid():
            form.save()
            messages.success(request, 'Cadastro realizado com sucesso.')

    return locals()


@rtr('processo_eletronico/alterar_nivel_acesso_processo.html')
@login_required()
def alterar_nivel_acesso_processo(request, processo_id):
    processo = get_object_or_404(Processo, id=processo_id)
    #
    user = request.user
    verifica_pode_alterar_nivel_acesso(processo, user)
    #
    url = reverse_lazy('processo', kwargs={'processo_id': processo.id}, current_app='processo_eletronico')
    title = 'Alterar Nível de Acesso do Processo {}'.format(processo)

    existe_solicitacoes_aberto = processo.existe_solicitacoes_nivel_acesso_aberto()
    if existe_solicitacoes_aberto:
        return httprr(url, 'Não é possível alterar o nível de acesso sem antes analisar as solicitações de alteração de nível de acesso que estão em aberto.')

    form = ProcessoFormAlterarNivelAcesso(request.POST or None, request=request, processo=processo)
    if form.is_valid():
        try:
            processo.alterar_nivel_acesso(
                novo_nivel_acesso=int(form.cleaned_data.get('nivel_acesso')),
                nova_hipotese_legal=form.cleaned_data.get('hipotese_legal'),
                user=request.user,
                ip=request.META.get('REMOTE_ADDR', ''),
                destinatario_setor=form.cleaned_data.get('setor_usuario', None),
                justificativa=form.cleaned_data.get('justificativa', None)
            )
            return httprr(url, 'Nível de Acesso alterado com sucesso.')
        except Exception as e:
            error_message = '{}'.format(e) or ', '.join(e.messages)
            return httprr(url, error_message, tag='error')

    return locals()


@rtr('processo_eletronico/solicita_alteracao_nivel_acesso.html')
@login_required()
def solicita_alteracao_nivel_acesso_documento_digitalizado(request, documento_id):
    obj = get_object_or_404(DocumentoDigitalizado, id=documento_id)
    title = f'Solicitar Alteração de Nível de Acesso: {obj}'
    form = DocumentoAlterarNivelAcessoForm(request.POST or None, request=request, documento=obj, estah_solicitando=True)
    #
    if form.is_valid():
        SolicitacaoAlteracaoNivelAcesso.get_or_create(
            documento_digitalizado=obj,
            descricao=form.cleaned_data.get('justificativa'),
            # DE - NIVEL DE ACESSO
            de_nivel_acesso=obj.nivel_acesso,
            # PARA - NIVEL DE ACESSO
            para_nivel_acesso=int(form.cleaned_data.get('nivel_acesso')),
            hipotese_legal=form.cleaned_data.get('hipotese_legal')
        )
        message = 'Solicitação realizada com sucesso com sucesso.'
        return httprr('..', message)

    #
    return locals()


@rtr('processo_eletronico/solicita_alteracao_nivel_acesso.html')
@login_required()
def solicita_alteracao_nivel_acesso_documento_texto(request, documento_id):
    obj = get_object_or_404(DocumentoTexto, id=documento_id)
    title = f'Solicitar Alteração de Nível de Acesso do Documento: {obj}'
    form = DocumentoAlterarNivelAcessoForm(request.POST or None, request=request, documento=obj, estah_solicitando=True)
    #
    if form.is_valid():
        SolicitacaoAlteracaoNivelAcesso.get_or_create(
            documento_texto=obj,
            descricao=form.cleaned_data.get('justificativa'),
            # DE - NIVEL DE ACESSO
            de_nivel_acesso=obj.nivel_acesso,
            # PARA - NIVEL DE ACESSO
            para_nivel_acesso=int(form.cleaned_data.get('nivel_acesso')),
            hipotese_legal=form.cleaned_data.get('hipotese_legal')
        )

        # Importante para usabilidade
        url = None
        if request.GET.get('processo'):
            url = reverse_lazy('processo', kwargs={'processo_id': request.GET.get('processo')},
                               current_app='processo_eletronico')
        else:
            url = reverse_lazy('visualizar_documento', kwargs={'documento_id': obj.id},
                               current_app='documento_eletronico')

        return httprr(url, 'Solicitação realizada com sucesso com sucesso.')
    #
    return locals()


@rtr('processo_eletronico/solicita_alteracao_nivel_acesso.html')
@login_required()
def solicita_alteracao_nivel_acesso_processo(request, processo_id):
    obj = get_object_or_404(Processo, id=processo_id)
    title = f'Solicitar Alteração de Nível de Acesso do Processo: {obj}'
    form = ProcessoFormAlterarNivelAcesso(request.POST or None, request=request, processo=obj, estah_solicitando=True)
    #
    if form.is_valid():
        SolicitacaoAlteracaoNivelAcesso.get_or_create(
            processo=obj,
            descricao=form.cleaned_data.get('justificativa'),
            # DE - NIVEL DE ACESSO
            de_nivel_acesso=obj.nivel_acesso,
            # PARA - NIVEL DE ACESSO
            para_nivel_acesso=int(form.cleaned_data.get('nivel_acesso')),
            hipotese_legal=form.cleaned_data.get('hipotese_legal')
        )
        url = reverse_lazy('processo', kwargs={'processo_id': processo_id}, current_app='processo_eletronico')
        return httprr(url, 'Solicitação realizada com sucesso com sucesso.')
    #
    return locals()


@rtr('nivel_acesso/solicitacoes_alteracao_nivel_acesso.html')
@login_required()
def solicitacoes_alteracao_nivel_acesso_documento(request, documento_id):
    title = 'Solicitações de alteração de nível de acesso de documento'
    solicitacoes = SolicitacaoAlteracaoNivelAcesso.objects.filter(Q(documento_texto_id=documento_id) | Q(documento_digitalizado_id=documento_id))
    redirect = breadcrumbs_previous_url(request)
    return locals()


@rtr('nivel_acesso/solicitacoes_alteracao_nivel_acesso.html')
@login_required()
def solicitacoes_alteracao_nivel_acesso_processo(request, processo_id):
    instance = get_object_or_404(Processo, pk=processo_id)
    title = 'Solicitações de alteração de nível de acesso do processo {}'.format(instance)
    solicitacoes = SolicitacaoAlteracaoNivelAcesso.objects.filter(processo_id=processo_id)
    redirect = breadcrumbs_previous_url(request)
    return locals()


@rtr()
@login_required()
def analisar_solicitacao_alteracao_nivel_acesso(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoAlteracaoNivelAcesso, pk=solicitacao_id)
    object = solicitacao.get_documento_processo()
    form = None
    url = request.GET.get('next', '..')

    tipo = None
    if solicitacao.get_tipo_documento_processo_str() == 'processo':
        tipo = 'Processo'
    else:
        tipo = 'Documento'

    title = 'Analisar solicitação de alteração de nível de acesso do {} {}'.format(tipo, object)

    #
    form = ConfirmarDeferimentoForm(request.POST or None, request=request, solicitacao=solicitacao)
    #
    if form.is_valid():
        try:
            kwargs = dict(
                user=request.user,
                ip=request.META.get('REMOTE_ADDR', ''),
                destinatario_setor=form.cleaned_data.get('setor_usuario', None),
                pessoas_compartilhadas=form.cleaned_data.get('pessoas_compartilhadas', None)
            )
            #
            with transaction.atomic():
                solicitacao.deferir(**kwargs)
                return httprr(url, 'Nível de Acesso alterado com sucesso.')
        except Exception as e:
            error_message = '{}'.format(e) or ', '.join(e.messages)
            return httprr(url, error_message, tag='error')

    return locals()


@rtr()
@login_required()
def indeferir_solicitacao_alteracao_nivel_acesso(request, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoAlteracaoNivelAcesso, pk=solicitacao_id)
    obj = solicitacao.get_documento_processo()

    url = request.GET.get('next', '..')
    if solicitacao.usuario_analise:
        raise PermissionDenied('Solicitação já analisada.')

    title = f'Indeferir Solicitação de Alteração de Nível de Acesso - {obj}'

    form = ConfirmarIndeferimentoForm(request.POST or None, request=request, solicitacao=solicitacao)
    user = request.user
    if solicitacao.eh_processo():
        verifica_pode_alterar_nivel_acesso(obj, user)
    else:
        if not obj.pode_alterar_nivel_acesso(user):
            raise PermissionDenied()

    if form.is_valid():
        justificativa = form.cleaned_data.get('justificativa')
        #
        with transaction.atomic():
            try:
                sid = transaction.savepoint()
                # Indeferindo as solicitacoes
                solicitacao.usuario_analise = request.user
                solicitacao.data_analise = datetime.now()
                solicitacao.situacao = SolicitacaoAlteracaoNivelAcesso.SITUACAO_INDEFERIDO
                solicitacao.justificativa = justificativa
                solicitacao.save()
                #
                if form.cleaned_data.get('deferir_outras_solicitacoes'):
                    solicitacoes = solicitacao.get_solicitacoes_iguais_em_aberto()
                    for sol in solicitacoes:
                        sol.usuario_analise = request.user
                        sol.data_analise = datetime.now()
                        sol.situacao = SolicitacaoAlteracaoNivelAcesso.SITUACAO_INDEFERIDO
                        solicitacao.justificativa = justificativa
                        sol.save()
                #
                transaction.savepoint_commit(sid)
                return httprr(url, 'Indeferimento realizado com sucesso.')
            #
            except Exception as e:
                transaction.savepoint_rollback(sid)
                error_message = '{}'.format(e) or ', '.join(e.messages)
                raise PermissionDenied(error_message)
    #
    return locals()


@rtr('processo_eletronico/processo_padrao.html')
@login_required()
def processo_editar_assunto(request, processo_id):
    processo = get_object_or_404(Processo, id=processo_id)
    processo.pode_ler(user=request.user, lancar_excecao=True)
    target = processo.get_absolute_url()
    verifica_pode_editar_processo(processo)
    atual_assunto = processo.assunto

    title = 'Editar Assunto do Processo {}'.format(processo)

    if not processo.esta_ativo():
        return httprr(target, 'O processo não pode ter seu assunto editados porque não está mais em trâmite.',
                      close_popup=True)

    form = ProcessoEditarAssuntoForm(request.POST or None, instance=processo, request=request)
    if form.is_valid():
        novo_assunto = form.cleaned_data.get('assunto')
        justificativa = form.cleaned_data.get('justificativa')

        if atual_assunto != novo_assunto:
            form.save()

            observacao = 'Edição do assunto de "{}" para "{}" pelo motivo seguinte motivo: {}'.format(atual_assunto, novo_assunto, justificativa)

            registrar_acao(request, processo,
                           RegistroAcaoProcesso.TIPO_EDICAO_ASSUNTO,
                           observacao)

            return httprr(processo.get_absolute_url(), 'O assunto do processo foi alterado com sucesso.',
                          close_popup=True)

        return httprr(processo.get_absolute_url(), 'Não houve alteração no assunto do processo.', tag='alert',
                      close_popup=True)

    return locals()


@rtr()
@login_required()
def linha_tempo(request, processo_id):

    # Dados iniciais
    # -----------------------------
    instance = get_object_or_404(Processo, pk=processo_id)
    title = 'Linha do Tempo do Processo {}'.format(instance)
    instance = Processo.atualizar_status_processo(instance)
    pessoa = request.user.get_profile()

    # Verifica se o usuario pode ler o processo, senao puder sera PermissionDenied()
    # -----------------------------
    pode_ler = instance.pode_ler(user=request.user, lancar_excecao=True)

    # Se o processo tiver aguardando a ciencia do user sera redirecionado diretamente para o a tela de ciencia
    # -----------------------------
    if instance.get_ciencia_pendente(pessoa):
        return dar_ciencia(request, instance.id)

    # Anexacao
    # -----------------------------
    if instance.status == ProcessoStatus.STATUS_ANEXADO:
        processo_pk = Anexacao.objects.filter(processo_anexado_id=processo_id).values_list('processo_anexador__id',
                                                                                           flat=True)
        return linha_tempo(request, processo_pk.first())

    # ---------------------------
    # Lista geral de eventos
    # ---------------------------
    eventos = list()  # acao = {'data_hora': '', 'detalhes': ''}

    """
    > Grupo 1
    - 1.1 Inicio do processo
    - 1.2 Tramitou (com/sem despacho) e Recebeu
    - 1.3 Adicionou/removeu documento texto/upload
    - 1.4 Finalizar processo / Remover finalizacao do processo
    - 1.5 Remover ultimo tramite (não consigo mapear)
    """
    # 1.1 Inicio do processo
    # ----------------------------------
    acao = {'data_hora': instance.data_hora_criacao, 'usuario': instance.usuario_gerador, 'titulo': 'Processo foi criado', 'iniciado': True}
    eventos.append(acao)

    # 1.2 Tramitacoes
    # ----------------------------------
    tramites = Tramite.objects.filter(processo=instance)
    for tramite in tramites:
        de = None
        para = None
        if not tramite.tramite_barramento:
            # De "setor para setor", "setor para pessoa", "pessoa para pessoa" e "pessoa para setor"
            # Encaminhou DE -> PARA
            if tramite.remetente_setor:
                de = 'Do setor {}'.format(tramite.remetente_setor)
                if tramite.remetente_pessoa:
                    de = '{} ({})'.format(de, tramite.remetente_setor)
            else:
                de = 'Da pessoa {}'.format(tramite.remetente_pessoa)
            if tramite.destinatario_setor:
                para = 'para o setor {}'.format(tramite.destinatario_setor)
                if tramite.destinatario_pessoa:
                    de = '{} ({})'.format(para, tramite.destinatario_pessoa)
            else:
                para = 'para a pessoa {}'.format(tramite.destinatario_pessoa)
            if tramite.despacho_corpo:
                acao = {'data_hora': tramite.data_hora_encaminhamento, 'usuario': None, 'titulo': 'Processo foi encaminhado', 'detalhes': '{} {} | Despacho: #{}'.format(de, para, tramite.id)}
            else:
                acao = {'data_hora': tramite.data_hora_encaminhamento, 'usuario': None, 'titulo': 'Processo foi encaminhado', 'detalhes': '{} {}'.format(de, para)}
        else:
            # Tramite externo
            if tramite.remetente_setor:
                de = 'Do setor {}'.format(tramite.remetente_setor)
                para = 'para {}'.format(tramite.tramite_barramento.destinatario_externo_estrutura_descricao)
            else:
                de = 'De {}'.format(tramite.tramite_barramento.remetente_externo_estrutura_descricao)
                para = 'para o setor {}'.format(tramite.destinatario_setor)
        eventos.append(acao)
        # Recebeu
        if tramite.foi_recebido:
            if tramite.destinatario_setor:
                eventos.append({'data_hora': tramite.data_hora_recebimento, 'usuario': None, 'titulo': 'Processo foi recebido', 'detalhes': 'No setor {}'.format(tramite.destinatario_setor)})
            else:
                eventos.append({'data_hora': tramite.data_hora_recebimento, 'usuario': None, 'titulo': 'Processo foi recebido', 'detalhes': 'Pela pessoa {}'.format(tramite.destinatario_pessoa)})

    # 1.3 Adicionou/removeu documento texto/upload
    # ----------------------------------
    documentos_do_processo = instance.get_todos_documentos_processo()
    for documentop in documentos_do_processo:
        processo_anexado = ''
        if documentop.processo_anexado:
            processo_anexado = '(Documento Anexado pelo Processo: {} em {})'.format(documentop.processo_anexado, format_datetime(documentop.data_hora_anexado))
        if documentop.classe != "despacho":
            if hasattr(documentop, 'foi_adicionado_novamente') and documentop.foi_adicionado_novamente():
                acao = {'data_hora': documentop.documento_adicionado_novamente().get_documento().data_hora_inclusao, 'usuario': documentop.documento_adicionado_novamente().get_documento().usuario_inclusao, 'titulo': 'Documento foi adicionado novamente ao processo', 'detalhes': 'Documento: "{}" {}'.format(documentop.get_documento(), processo_anexado)}
            else:
                acao = {'data_hora': documentop.data_hora_inclusao, 'usuario': documentop.usuario_inclusao, 'titulo': 'Documento foi adicionado ao processo', 'detalhes': 'Documento: "{}" {}'.format(documentop.get_documento(), processo_anexado)}
            eventos.append(acao)
    documentos_removidos_processo = instance.get_documentos_removidos()
    for documentopr in documentos_removidos_processo:
        eventos.append({'data_hora': documentopr.data_hora_remocao, 'usuario': documentopr.usuario_remocao, 'titulo': 'Documento foi removido do processo', 'detalhes': 'Documento: "{}"'.format(documentopr.get_documento())})

    # 1.4 Finalizar processo / Desfinalizar processo
    # ----------------------------------
    for ra in RegistroAcaoProcesso.objects.filter(processo=instance, tipo=RegistroAcaoProcesso.TIPO_FINALIZACAO):
        eventos.append({'data_hora': ra.data, 'usuario': ra.user, 'titulo': 'Processo Finalizado ({})'.format(ra.observacao), 'finalizado': True})
    for ra in RegistroAcaoProcesso.objects.filter(processo=instance, tipo=RegistroAcaoProcesso.TIPO_DESFINALIZACAO):
        eventos.append({'data_hora': ra.data, 'usuario': ra.user, 'titulo': 'Finalização do proceso foi removida ({})'.format(ra.observacao), 'iniciado': True})

    """
    > Grupo 2
    2.1 Adicionou/removeu processo relacionado (não consigo mapear)
    2.2 Adicionou/removeu processo apensado
    2.3 Adicionou processo anexado
    2.4 Adicionou/removeu minuta
    2.5 Adicionou comentário
    """
    # 2.2 Adicionou/removeu processo apensado e 2.3 Adicionou processo anexado
    # ----------------------------------
    for ra in RegistroAcaoProcesso.objects.filter(Q(processo=instance) & (Q(tipo=RegistroAcaoProcesso.TIPO_APENSACAO) | Q(tipo=RegistroAcaoProcesso.TIPO_APENSACAO) | Q(tipo=RegistroAcaoProcesso.TIPO_ANEXACAO))):
        eventos.append({'data_hora': ra.data, 'usuario': ra.user, 'titulo': ra.observacao})

    # 2.4 Adicionou/removeu minuta
    # ----------------------------------
    processo_minutas = ProcessoMinuta.objects.filter(processo=instance)
    for minuta in processo_minutas:
        eventos.append({'data_hora': minuta.data_hora_inclusao, 'usuario': minuta.usuario_inclusao, 'titulo': 'Minuta adicionada: {}'.format(minuta)})
        if minuta.data_hora_remocao:
            eventos.append({'data_hora': minuta.data_hora_remocao, 'usuario': minuta.usuario_remocao, 'titulo': 'Minuta removida: {}'.format(minuta)})

    # 2.5 Adicionou comentário
    # ----------------------------------
    processo_comentarios = ComentarioProcesso.objects.filter(processo=instance)
    for comentario in processo_comentarios:
        eventos.append({'data_hora': comentario.data, 'usuario': comentario.pessoa, 'titulo': 'Comentário adicionado: {}'.format(comentario.comentario)})

    """
    > Grupo 3
    - 3.1 Solicitou despacho (e seus eventos)
    - 3.2 Solicitou documento (e seus eventos)
    - 3.3 Solicitou ciência (e seus eventos)
    """
    # 3.1 Solicitou despacho (e seus eventos)
    # ----------------------------------
    # Solicitou (data_solicitacao, remetente_pessoa, remetente_setor),
    # Deferir (será mapeado pelo despacho do processo, data_resposta, tramite_gerado),
    # Indeferir/Rejeitar (data_resposta, justificativa_rejeicao),
    # Cancelar (justificativa_rejeicao)
    processo_sols_despacho = SolicitacaoDespacho.objects.filter(processo=instance)
    for sol_despacho in processo_sols_despacho:
        # Solicitar Cancelar
        if not sol_despacho.data_resposta and sol_despacho.justificativa_rejeicao:
            eventos.append({'data_hora': sol_despacho.data_solicitacao, 'usuario': sol_despacho.remetente_pessoa, 'titulo': 'Despacho solicitado a: {}. Cancelado'.format(sol_despacho.solicitado)})
        else:
            eventos.append({'data_hora': sol_despacho.data_solicitacao, 'usuario': sol_despacho.remetente_pessoa, 'titulo': 'Despacho solicitado a: {}.'.format(sol_despacho.solicitado)})
            # Deferir
            if sol_despacho.tramite_gerado:
                eventos.append({'data_hora': sol_despacho.data_resposta, 'usuario': sol_despacho.solicitado, 'titulo': 'Despacho realizado'})
            # Indeferir/Rejeitar
            elif sol_despacho.data_resposta and sol_despacho.justificativa_rejeicao:
                # usuario: não consegui saber quem fez
                eventos.append({'data_hora': sol_despacho.data_resposta, 'usuario': None, 'titulo': 'Despacho rejeitado'})

    # 3.2 Solicitou documento (e seus eventos)
    # ----------------------------------
    # Solicitou (solicitante, data_solicitacao)
    # Cancelada (cancelada_por, data_cancelamento)
    # Concluida (solicitado, data_conclusao)
    processo_sols_junt = SolicitacaoJuntada.objects.filter(tramite__processo=instance)
    for sol_junt in processo_sols_junt:
        # Solicitou
        eventos.append({'data_hora': sol_junt.data_solicitacao, 'usuario': sol_junt.solicitante, 'titulo': 'Juntada de documento solicitada a: {}.'.format(sol_junt.solicitado)})
        # Cancelada
        if sol_junt.data_cancelamento:
            eventos.append({'data_hora': sol_junt.data_cancelamento, 'usuario': sol_junt.solicitado, 'titulo': 'Juntada cancelada'})
        # Concluida
        elif sol_junt.data_conclusao:
            eventos.append({'data_hora': sol_junt.data_conclusao, 'usuario': sol_junt.solicitado, 'titulo': 'Juntada concluída'})

    # 3.3 Solicitou ciência (e seus eventos)
    # ----------------------------------
    # Solicitou (solicitante, data_solicitacao)
    # Cancelada (cancelada_por, data_cancelamento)
    # Concluida (solicitado, data_ciencia)
    processo_sols_ci = SolicitacaoCiencia.objects.filter(processo=instance)
    for sol_ci in processo_sols_ci:
        # Solicitou
        eventos.append({'data_hora': sol_ci.data_ciencia, 'usuario': sol_ci.solicitante, 'titulo': 'Ciência solicitada a: {}.'.format(sol_ci.solicitado)})
        # Cancelada
        if sol_ci.data_cancelamento:
            eventos.append({'data_hora': sol_ci.data_cancelamento, 'usuario': sol_ci.cancelada_por, 'titulo': 'Ciência cancelada'})
        # Concluida
        elif sol_ci.data_ciencia:
            eventos.append({'data_hora': sol_ci.data_ciencia, 'usuario': sol_ci.solicitado, 'titulo': 'Ciência concluída'})

    """
    > Grupo 4
    - 4.1 Alterou nivel de acesso
    """
    for ra in RegistroAcaoProcesso.objects.filter(processo=instance, tipo=RegistroAcaoProcesso.TIPO_EDICAO_NIVEL_ACESSO):
        eventos.append({'data_hora': ra.data, 'usuario': ra.user, 'titulo': ra.observacao})

    # ----------------------------------
    # Organiza eventos
    # ----------------------------------
    eventos_ordenados = sorted(eventos, key=lambda i: (i['data_hora']))
    grupos_data = set()
    for eo in eventos_ordenados:
        grupos_data.add(eo.get('data_hora').date())
    grupos_data = sorted(grupos_data)

    eventos_organizados = dict()
    for gd in grupos_data:
        eventos_organizados[gd] = list()

    for eo in eventos_ordenados:
        eventos_organizados[eo.get('data_hora').date()].append(eo)

    return locals()
