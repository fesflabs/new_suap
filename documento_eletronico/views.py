import itertools
import re
from urllib.parse import urljoin

import OpenSSL
from django.apps.registry import apps
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.core.exceptions import PermissionDenied, ValidationError
from django.db import transaction
from django.db.models import F, Max, Q
from django.dispatch import receiver
from django.http import Http404, HttpResponse, FileResponse
from django.shortcuts import get_object_or_404, render
from django.template import TemplateSyntaxError
from djtools.utils.http import get_client_ip
from djtools.utils.response import render_to_string
from django.urls import reverse_lazy
from django.utils.decorators import method_decorator
from django.views.generic.edit import FormView
from formtools.wizard.views import SessionWizardView
from reversion import revisions as reversion
from reversion.models import Version

from comum.models import PessoaFisica, Configuracao
from comum.utils import get_setor, get_todos_setores
from djtools import layout
from djtools.testutils import running_tests
from djtools.utils import JsonResponse, get_datetime_now, httprr, permission_required, rtr, \
    send_notification
from documento_eletronico.forms import AvaliarSolicitacaoCompartilhamentoDocumentoDigitalizadoForm, \
    SolicitarCompartilhamentoDocumentoDigitalizadoForm, ListarDocumentosTextoForm, DocumentoTextoForm, DocumentoTextoPessoalForm, AssinarDocumentoGovBRForm
from documento_eletronico.models import Documento, SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa, TipoDocumento, AssinaturaDocumentoTexto
from documento_eletronico.status import DocumentoStatus
from documento_eletronico.utils import (
    Notificar,
    app_processo_eletronico_estah_instalada,
    convert_to_pdfA,
    gerar_codigo_verificador_documento,
    get_previous,
    get_variaveis,
    imprimir_pdf, random_with_N_digits
)
from processo_eletronico.utils import iniciar_gerenciamento_compartilhamento
from rh.models import Papel, Setor
from rh.views import rh_servidor_view_tab
from .assinar_documento import CertificadoICPBrasil, SignerException, assinar_documento_com_token
from .forms import (
    AssinarDocumentoForm,
    AutenticacaoDocumentoDigitalizado,
    AutenticacaoDocumentoTexto,
    CancelarDocumentoForm,
    DocumentoAlterarNivelAcessoForm,
    DocumentoTextoFormEditarInteressados,
    DocumentoTextoEditarCorpoForm,
    EditarModeloDocumentoForm,
    GeradorIdentificadorDocumentoForm,
    GerenciarCompartilhamentoDocumentoForm,
    GerenciarCompartilhamentoSetorForm,
    ModeloDocumentoForm,
    PapelForm,
    RejeitarSolicitacaoAssinaturaForm,
    RevisarDocumentoForm,
    SolicitacaoAssinaturaForm,
    SolicitacaoComplementaresFormSet,
    SolicitacaoRevisaoForm,
    VinculoDocumentoTextoForm,
    SolicitacaoAssinaturaComAnexacaoForm,
    SolicitacaoComplementaresComAnexacaoFormSet,
)
from .models import (
    CompartilhamentoDocumentoPessoa,
    DocumentoDigitalizado,
    DocumentoTexto,
    HipoteseLegal,
    ModeloDocumento,
    NivelAcesso,
    NivelPermissao,
    RegistroAcaoDocumento,
    RegistroAcaoDocumentoTexto,
    SolicitacaoAssinatura,
    SolicitacaoRevisao,
    SolicitacaoStatus,
    TipoDocumentoTexto,
    TipoPermissao,
    VinculoDocumentoTexto,
    DocumentoTextoPessoal,
    DocumentoDigitalizadoPessoal,
    DocumentoTextoAnexoDocumentoTexto,
    DocumentoTextoAnexoDocumentoDigitalizado,
    DocumentoDigitalizadoAnexoSimples
)
from .utils import acesso_ao_documento_em_funcao_cargo, eh_auditor_chefe, get_documento_texto_tamanho_maximo_em_mb


@layout.quadro('Documentos Eletrônicos', icone='file')
def index_quadros(quadro, request):
    qtd_documentos_a_assinar = DocumentoTexto.objects.esperando_assinatura(request.user).count()
    if qtd_documentos_a_assinar:
        quadro.add_item(
            layout.ItemContador(
                titulo='Documento(s) Esperando Assinatura',
                qtd=qtd_documentos_a_assinar,
                url='/admin/documento_eletronico/documentotexto/?opcao=4'
            )
        )
    qtd_documentos_a_revisar = DocumentoTexto.objects.revisao_pendente(user=request.user).count()
    if qtd_documentos_a_revisar:
        quadro.add_item(
            layout.ItemContador(
                titulo='Documento(s) Esperando Revisão',
                qtd=qtd_documentos_a_revisar,
                url='/admin/documento_eletronico/documentotexto/?opcao=6'
            )
        )

    qtd_documentos_a_avaliar_revisao = DocumentoTexto.objects.compartilhados(request.user).filter(status=DocumentoStatus.STATUS_REVISADO).count()
    if qtd_documentos_a_avaliar_revisao:
        quadro.add_item(
            layout.ItemContador(
                titulo='Documento(s) Revisados',
                subtitulo='Aguardando avaliação',
                qtd=qtd_documentos_a_avaliar_revisao,
                url='/admin/documento_eletronico/documentotexto/?opcao=3&status__exact=4',
            )
        )

    return quadro


@rtr()
@permission_required('documento_eletronico.view_documentotexto')
def dashboard(request):
    title = 'Dashboard: Documentos Eletrônicos'

    meus_documentos = DocumentoTexto.objects.proprios(request.user).count()
    meus_favoritos = DocumentoTexto.objects.filter(usuarios_marcadores_favoritos=request.user).count()
    compartilhados_comigo = DocumentoTexto.objects.compartilhados(request.user).count()
    esperando_minha_assinatura = DocumentoTexto.objects.esperando_assinatura(request.user).count()
    minhas_requisicoes_assinaturas = DocumentoTexto.objects.assinatura_requisitada_por(request.user).count()
    assinados_por_mim = DocumentoTexto.objects.assinados(request.user).count()

    esperando_minha_revisao = DocumentoTexto.objects.revisao_pendente(request.user).count()
    minhas_requisicoes_revisoes = DocumentoTexto.objects.requisicao_pendente(request.user).count()
    revisados_por_mim = DocumentoTexto.objects.revisados_por(request.user).count()
    vinculados_a_mim = DocumentoTexto.objects.vinculados_a_mim(request.user).count()

    estados_terminais = [DocumentoStatus.STATUS_CONCLUIDO, DocumentoStatus.STATUS_FINALIZADO,
                         DocumentoStatus.STATUS_CANCELADO]
    meus_documentos_pendentes = DocumentoTexto.objects.proprios(request.user).exclude(status__in=estados_terminais)
    return locals()


def verificar_permissao_tramite(usuario_setor, processos_incluido):
    for processo in processos_incluido:
        ultimo_tramite = processo.get_ultimo_tramite()
        if ultimo_tramite:
            if ultimo_tramite.get_destino() == usuario_setor:
                return True
        elif processo.setor_criacao == usuario_setor:
            return True

    return False


def get_or_create_solicitacao(solicitante, solicitado, documento, conceder_acesso=False):
    comp_doc_pessoa_criado_via_solicitacao_assinatura = None
    if not documento.pode_ler(solicitado.user) and conceder_acesso:
        # Condece permissão para o balizador
        comp_doc_pessoa_criado_via_solicitacao_assinatura = CompartilhamentoDocumentoPessoa.objects.get_or_create(
            pessoa_permitida=solicitado.user.get_profile(), documento=documento, nivel_permissao=NivelPermissao.LER
        )[0]
    try:
        obj = SolicitacaoAssinatura.objects.get(documento_id=documento.id, solicitado=solicitado,
                                                status=SolicitacaoStatus.STATUS_ESPERANDO)
        created = False
    except SolicitacaoAssinatura.MultipleObjectsReturned:
        raise ValidationError(
            'Existem mais de uma solicitação de assinatura pendente para {} para ' 'este documento.'.format(
                solicitado))
    except SolicitacaoAssinatura.DoesNotExist:
        obj = SolicitacaoAssinatura(documento_id=documento.id, solicitado=solicitado, solicitante=solicitante)
        obj.save()

        if comp_doc_pessoa_criado_via_solicitacao_assinatura:
            comp_doc_pessoa_criado_via_solicitacao_assinatura.solicitacao_assinatura = obj
            comp_doc_pessoa_criado_via_solicitacao_assinatura.save(suspender_notificacao=True)
        created = True

    return obj, created


# TODO: Este método não ficaria melhor estando em Documento?
def get_or_create_balizadora(solicitante, solicitado, documento):
    if documento.possui_assinatura():
        return documento.get_solicitacao_balizadora()
    else:
        solicitacao, _ = get_or_create_solicitacao(solicitante, solicitado, documento, True)
        return solicitacao


def construir_ligacoes_entre_solicitacoes(solicitacoes_dict, root):
    for index, solicitacoes in list(solicitacoes_dict.items()):
        condicionantes = solicitacoes_dict.get(index - 1, [root])
        for solicitacao in solicitacoes:
            solicitacao.adicionar_condicionantes(condicionantes)
            solicitacao.save()


def registrar_acao_documento_texto(request, documento, tipo_acao, observacao=''):
    user = request.user
    ip = get_client_ip(request)
    RegistroAcaoDocumentoTexto.registrar_acao(documento=documento, tipo_acao=tipo_acao, user=user, ip=ip, observacao=observacao)


def registar_acesso_documento_texto(request, documento, acesso_via_cargo):
    user = request.user
    ip = get_client_ip(request)
    RegistroAcaoDocumentoTexto.registar_acesso(documento=documento, user=user, ip=ip, acesso_via_cargo=acesso_via_cargo)


def get_documento_or_forbidden(user, documento_id):
    documento = get_documento_texto(documento_id)

    pode_carregar_doc = False

    if documento:
        if user.is_authenticated:
            pode_carregar_doc = documento.pode_ler(user)
        else:
            pode_carregar_doc = True

    if pode_carregar_doc:
        if not documento.eh_documento_pessoal:
            documento_do_usuario = DocumentoTexto.objects.filter(id=documento_id).first()
        else:
            documento_do_usuario = DocumentoTextoPessoal.objects.filter(id=documento_id).first()
        if documento_do_usuario:
            return documento_do_usuario
    raise PermissionDenied


def iter_incrementing_name(name):
    prefix = 'Clone de'
    name = 'Clone de {} 1'.format(name if prefix not in name else name)
    r = re.compile(r'(.*?)\s+(\w+)$')
    match = r.match(name)
    if match:
        prefix = match.group(1)
        for i in itertools.count(start=1, step=1):
            yield prefix + ' {}'.format(i)
    else:
        yield prefix + name


def get_requisicoes_de_assinatura(usuario):
    solicitacoes = SolicitacaoAssinatura.objects.filter_requisicao_pendente(usuario)
    documentos_ids = solicitacoes.all().values_list('documento_id', flat=True)
    return DocumentoTexto.objects.filter(id__in=documentos_ids)


def get_documentos_a_revisar(pessoa):
    solicitacoes = SolicitacaoRevisao.objects.filter_revisao_pendente(pessoa)
    documentos_ids = solicitacoes.all().values_list('documento_id', flat=True)
    return DocumentoTexto.objects.filter(id__in=documentos_ids)


def get_documentos_revisados(usuario):
    revisados = SolicitacaoRevisao.objects.filter_revisados(usuario)
    documentos_ids = revisados.all().values_list('documento_id', flat=True)
    return DocumentoTexto.objects.filter(id__in=documentos_ids)


def get_requisicoes_de_revisao(usuario):
    solicitacoes = SolicitacaoRevisao.objects.filter_requisicao_pendente(usuario)
    documentos_ids = solicitacoes.all().values_list('documento_id', flat=True)
    return DocumentoTexto.objects.filter(id__in=documentos_ids)


def filtar_por_setor(request, setor):
    # Então buscamos o filtro por setor que fica na área html de "class=pills".
    setores_param = request.GET.get('setores')
    # Se não há um filtro por setores, então verificamos se na URL anterior há esse filtro. Se houver, vamos
    # manter esse filtro na próxima requisição. Isso é necessário para que os outros filtros do
    # form ListarDocumentosTextoForm
    # possam ser aplicados em conjunto com esse filtro de setores.
    if not setores_param:
        setores_param = 'todos'
        url_req_anterior = request.META.get('HTTP_REFERER', '').split('?')
        if len(url_req_anterior) == 2:
            params_req_anterior = url_req_anterior[1].split('&')
            for param in params_req_anterior:
                if 'setores' in param:
                    setores_param = param.split('=')[1]
                    break
    #
    try:
        setores_escolhidos = [Setor.objects.get(pk=(setores_param or setor.id))]
    except ValueError:
        setores_escolhidos = None
    return setores_param, setores_escolhidos


def get_documento_texto(id_uuid):
    try:
        return DocumentoTexto.objects.get(id=id_uuid)
    except Exception:
        return get_object_or_404(DocumentoTexto, uuid=id_uuid)


def get_documento_digitalizado(id_uuid):
    try:
        return DocumentoDigitalizado.objects.get(id=id_uuid)
    except Exception:
        return get_object_or_404(DocumentoDigitalizado, uuid=id_uuid)


@rtr()
@permission_required('documento_eletronico.change_documentotexto, documento_eletronico.change_documentotextopessoal')
def editar_documento(request, documento_id, remontar_partes_documento=None):
    title = 'Editar Documento'

    documento = get_documento_or_forbidden(request.user, documento_id)

    if not documento.pode_editar(request.user):
        raise PermissionDenied()

    if remontar_partes_documento == 'remontar_corpo':
        documento.montar_corpo_padrao()

    # Verifcando se o documento em questão tem alguma pendência com relação a hipótese legal. Se tiver, o usuário será
    # conduzido a tela de edição para que forneça a informação.
    # Obs: (1) Isso é necessário por conta de documentos antigos, sigilosos/restritos, criados em data anterior a versão
    # do SUAP que introduziu o cadastro de Hipóteses Legais. (2) Isso evita o erro "DocumentoTextoEditarCorpoForm
    # has no field named hipotese_legal" quando o usuário tenta salvar a modificação do texto e há algo pendente com relação
    # a hipoótese legal.
    try:
        documento.clean_hipotese_legal()
    except Exception as e:
        error_message = (str(e) or ', '.join(e)) + ' Forneça a informação para poder editar o texto.'
        return httprr('/admin/documento_eletronico/documentotexto/{}/change/'.format(documento.id), error_message,
                      tag='error')

    form_corpo = DocumentoTextoEditarCorpoForm(request.POST or None, instance=documento, request=request)
    if form_corpo.is_valid():
        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                form_corpo.save()

                observacao = ''
                if documento.estah_para_receber_assinatura_balizadora(user_que_deseja_assinar=request.user):
                    observacao = 'antes de assinar ou rejeitar solicitação de assinatura balizadora.'
                #
                registrar_acao_documento_texto(
                    request=request, documento=documento,
                    tipo_acao=RegistroAcaoDocumento.TIPO_EDICAO, observacao=observacao
                )
                transaction.savepoint_commit(sid)
                msg_sucesso = 'Edição realizada com sucesso.'
                if '_salvar_e_concluir' in request.POST:
                    return concluir_documento(request, documento_id)
                elif '_salvar_e_visualizar' in request.POST:
                    return httprr('/documento_eletronico/visualizar_documento/{}/'.format(documento.id), msg_sucesso)
                else:
                    messages.success(request, msg_sucesso)
            except Exception as e:
                transaction.savepoint_rollback(sid)
                return httprr('/documento_eletronico/visualizar_documento/{}/'.format(documento.id), str(e),
                              tag='error')

    documento_texto_tamanho_maximo_em_mb = get_documento_texto_tamanho_maximo_em_mb()
    return locals()


@rtr()
@permission_required('documento_eletronico.change_modelodocumento')
def editar_modelo_documento(request, modelo_documento_id):
    modelo_documento = get_object_or_404(ModeloDocumento, pk=modelo_documento_id)
    title = 'Editar Modelo de Documento ({})'.format(modelo_documento)
    if request.method == 'POST':
        form = EditarModeloDocumentoForm(request.POST or None, instance=modelo_documento)
        if form.is_valid():
            form.save()
            messages.success(request, 'Atualização realizada com sucesso.')
        else:
            messages.error(request, 'Edição falhou.')
            return locals()

    form = ModeloDocumentoForm(request.GET or None, instance=modelo_documento)
    return locals()


@rtr()
@permission_required('documento_eletronico.view_documentotexto')
def visualizar_documento(request, documento_id):

    documento = get_documento_texto(documento_id)
    if not documento:
        raise Http404()

    title = documento.identificador
    user = request.user
    #
    tem_permissao_ler = documento.pode_ler(user=user, verificar_acesso_cargo=False)
    acesso_via_cargo = acesso_ao_documento_em_funcao_cargo(user, documento) if not tem_permissao_ler else False
    pode_ler = tem_permissao_ler or acesso_via_cargo

    if not pode_ler:
        raise PermissionDenied()

    app_processo_eletronico_disponivel = app_processo_eletronico_estah_instalada()

    processos_incluido = documento.get_processos(exibir_somente_processos_nos_quais_documento_nao_foi_removido=True)
    pode_criar_processo = user.has_perm("processo_eletronico.add_processo")
    title = documento.identificador
    registar_acesso_documento_texto(request, documento, acesso_via_cargo=acesso_via_cargo)
    # Lista os documentos que foram anexados a este
    pode_receber_anexos = documento.pode_receber_anexos()
    documentos_texto_anexados = DocumentoTextoAnexoDocumentoTexto.objects.filter(documento=documento)
    documentos_digitalizado_anexados = DocumentoTextoAnexoDocumentoDigitalizado.objects.filter(documento=documento)

    if documento.pode_alterar_nivel_acesso(user):
        existe_solicitacoes_aberto = documento.listar_solicitacoes_nivel_acesso_aberto()

    ocultar_acesso_cargo = False if eh_auditor_chefe(user) else True
    registros_acoes = documento.get_registros_acoes(ocultar_acesso_cargo=ocultar_acesso_cargo)
    return locals()


# TODO: Ideia abortada temporariamente. Precisamos de mais tempo para amadurecer os requisitos dessa
# TODO: tela e ver realmente
# a sua necessidade. Caso mais a frente não seja necessário continuar, apagar o código!
@rtr()
@permission_required('documento_eletronico.view_documentotexto')
def meus_documentos(request):
    title = 'Meus Documentos'

    setor = get_setor(request.user)
    setor_escolhido = request.GET.get('setor', setor.id)

    if setor_escolhido == 'todos':
        setor_escolhido = None
    else:
        setor_escolhido = Setor.objects.get(pk=setor_escolhido)

    setores_visiveis = get_todos_setores(request.user)

    documentos = DocumentoTexto.objects.proprios(request.user)
    documentos_compartilhados = DocumentoTexto.objects.compartilhados(request.user)

    if setor_escolhido:
        documentos = documentos.filter(setor_dono=setor_escolhido)
        documentos_compartilhados = documentos_compartilhados.filter(setor_dono=setor_escolhido)

    meus_registros_acao_documento_recentes = (
        RegistroAcaoDocumento.objects.filter(documento__registroacaodocumento__user=request.user,
                                             documento__id__in=documentos)
        .annotate(max=Max('documento__registroacaodocumento__data'))
        .filter(max=F('data'))
        .select_related('documento')
        .order_by('-data')
    )

    meus_setor_registros_acao_documento_recentes = (
        RegistroAcaoDocumento.objects.filter(documento__id__in=documentos)
        .annotate(max=Max('documento__registroacaodocumento__data'))
        .filter(max=F('data'))
        .select_related('documento')
        .order_by('-data')
    )

    return locals()


@rtr()
def conteudo_documento(request, documento_id):
    documento = get_documento_texto(documento_id)
    if not documento:
        raise Http404()

    app_processo_eletronico_disponivel = app_processo_eletronico_estah_instalada()

    eh_anonimo = request.user.is_anonymous

    if eh_anonimo:
        if not documento.pode_ler(user=request.user, eh_consulta_publica=True):
            return httprr('/processo_eletronico/consulta_publica/', message="Este documento não pode ser visualizado na consulta pública.", tag='error')
    else:
        if not request.user.has_perm('documento_eletronico.view_documentotexto') or not documento.pode_ler(user=request.user):
            raise PermissionDenied()

    try:
        codigo_verificador = gerar_codigo_verificador_documento(documento)
    except TemplateSyntaxError as e:
        return HttpResponse(f'Erro ao tentar processar documento. Por favor verifique as variáveis. Detalhes: {e}')

    mostrar_anexos = request.GET.get('mostrar_anexos')

    if mostrar_anexos and documento.possui_anexos:
        anexos = documento.get_todos_anexos()
        anexos_do_documento = list()
        for anexo in anexos:
            if eh_anonimo:
                if anexo.documento_anexado.pode_ler(user=request.user, eh_consulta_publica=True):
                    anexos_do_documento.append(anexo.documento_anexado)
            else:
                if documento.pode_ler(user=request.user):
                    anexos_do_documento.append(anexo.documento_anexado)

        return render(request, 'documento_eletronico/templates/conteudo_documento_com_anexos.html', locals())

    return render(request, 'documento_eletronico/templates/conteudo_documento.html', locals())


@permission_required('documento_eletronico.add_documentotexto, documento_eletronico.add_documentotextopessoal')
def modelos_tipo_documento(request, tipo_documento_id):
    tipo_documento = get_object_or_404(TipoDocumentoTexto, pk=tipo_documento_id)
    modelos = tipo_documento.get_modelos_ativos()
    modelos = [{'id': '', 'nome': '---------'}] + list(modelos.values('id', 'nome'))
    return JsonResponse({'modelos': modelos})


@permission_required('documento_eletronico.add_documentotexto')
def gerar_sugestao_identificador_documento_texto(request, tipo_documento_id, setor_dono_id):
    tipo_documento = get_object_or_404(TipoDocumentoTexto, pk=tipo_documento_id)
    setor_dono = get_object_or_404(Setor, pk=setor_dono_id)

    identificador_tipo_documento_sigla, identificador_numero, identificador_ano, identificador_setor_sigla = tipo_documento.get_sugestao_identificador_definitivo(
        klass=DocumentoTexto,
        tipo_documento_texto=tipo_documento,
        setor_dono=setor_dono
    )

    return JsonResponse(
        {
            'identificador_tipo_documento_sigla': identificador_tipo_documento_sigla,
            'identificador_numero': identificador_numero,
            'identificador_ano': identificador_ano,
            'identificador_setor_sigla': identificador_setor_sigla,
        }
    )


@permission_required('documento_eletronico.add_documentotexto, documento_eletronico.add_documentotextopessoal')
def nivel_acesso_padrao_classificacoes_modelo_documento(request, modelo_documento_id):
    modelo_documento = get_object_or_404(ModeloDocumento, pk=modelo_documento_id)
    classificacoes = modelo_documento.classificacao.all()

    niveis_acesso_permitidos_keys, niveis_acesso_permitidos_values = modelo_documento.niveis_acesso_permitidos
    niveis_acesso_permitidos = list()
    for i in range(len(niveis_acesso_permitidos_keys)):
        niveis_acesso_permitidos.append(
            {'id': niveis_acesso_permitidos_keys[i], 'descricao': niveis_acesso_permitidos_values[i]})

    return JsonResponse(
        {
            'niveis_acesso_permitidos': niveis_acesso_permitidos,
            'nivel_acesso_padrao': modelo_documento.nivel_acesso_padrao,
            'classificacoes': list(classificacoes.values('id', 'codigo', 'descricao')),
        }
    )


@rtr('processo_eletronico/templates/permissoes.html')
@login_required
def gerenciar_compartilhamento_setor(request):
    uc = 'doc'

    # ---------------------------------------
    # Validacoes e Setor escolhido
    # ---------------------------------------
    setor_escolhido, setores_chefe, setor_escolhido, msg_orientacao_acesso = iniciar_gerenciamento_compartilhamento(
        request)

    # ---------------------------------------
    # Compartilhamentos de Documentos
    # ---------------------------------------
    title = 'Permissões para Documentos e Processos Eletrônicos'

    form = GerenciarCompartilhamentoSetorForm(request.POST or None, request=request, setor=setor_escolhido)
    form.fieldsets = (
        ('Permissões para Setores:',
            {'fields': ('setores_permitidos_podem_ler', 'setores_permitidos_podem_escrever')}
         ),
        ('Permissões para Servidores/Prestadores de Serviço:',
            {'fields': ('pessoas_permitidas_podem_ler', 'pessoas_permitidas_podem_escrever')},
         ),
    )

    if form.is_valid():
        form.save()
        messages.success(request, 'Operação realizada com sucesso.')

    return locals()


@permission_required('documento_eletronico.add_documentotexto, documento_eletronico.add_documentotextopessoal')
def get_hipoteses_legais_by_documento_nivel_acesso(request, documento_nivel_acesso_id):
    documento_nivel_acesso_id = int(documento_nivel_acesso_id)
    nivel_acesso = None
    if documento_nivel_acesso_id == Documento.NIVEL_ACESSO_SIGILOSO:
        nivel_acesso = NivelAcesso.SIGILOSO
    elif documento_nivel_acesso_id == Documento.NIVEL_ACESSO_RESTRITO:
        nivel_acesso = NivelAcesso.RESTRITO

    hipoteses_legais = list()
    if nivel_acesso:
        # Este for está sendo feito para poder obter a descrição da Hipótese Legal de acordo com o que está sendo definido
        # no respectivo método __str__.
        for hl in HipoteseLegal.objects.filter(nivel_acesso=nivel_acesso.name):
            hipoteses_legais.append({'id': hl.id, 'descricao': str(hl)})

    return JsonResponse({'hipoteses_legais': [{'id': '', 'descricao': '---------'}] + hipoteses_legais})


@rtr()
@permission_required('documento_eletronico.change_documentotexto')
def gerenciar_favoritos(request, documento_id, operacao):
    documento_texto = get_object_or_404(DocumentoTexto, pk=documento_id)
    user = request.user

    url = request.META.get('HTTP_REFERER')
    if operacao == 'add':
        if not documento_texto.estah_marcado_como_favorito(user):
            documento_texto.usuarios_marcadores_favoritos.add(user)
            return httprr(url, 'Documento adicionado aos seus favoritos.')
        else:
            return httprr(url, 'Documento já pertence aos seus favoritos.')

    elif operacao == 'remove':
        if documento_texto.estah_marcado_como_favorito(user):
            documento_texto.usuarios_marcadores_favoritos.remove(user)
            return httprr(url, 'Documento removido dos seus favoritos.')
        else:
            return httprr(url, 'Documento não pertence aos seus favoritos.')

    return locals()


@rtr()
@permission_required('documento_eletronico.change_documentotexto, documento_eletronico.change_documentotextopessoal')
def gerenciar_compartilhamento_documento(request, documento_id):
    title = 'Gerenciamento de Compartilhamento de Documento'

    documento = get_documento_or_forbidden(request.user, documento_id)

    if not documento.pode_compartilhar():
        raise PermissionDenied()

    form = GerenciarCompartilhamentoDocumentoForm(request.POST or None, request=request, documento=documento)
    if form.is_valid():
        form.save()
        if running_tests():
            return httprr('/admin/documento_eletronico/documentotexto/', 'Gerenciamento salvo com sucesso.')

        return httprr('..', 'Gerenciamento salvo com sucesso.')

    # Setores e pessoas que podem ler/escrever no documento
    compartilhamentos_documento_pessoa_ler = documento.compartilhamento_pessoa_documento.filter(
        nivel_permissao=NivelPermissao.LER)
    compartilhamentos_documento_pessoa_editar = documento.compartilhamento_pessoa_documento.filter(
        nivel_permissao=NivelPermissao.EDITAR)
    return locals()


def visualizar_documento_digitalizado(request, documento_id):
    documento = get_documento_digitalizado(documento_id)

    eh_anonimo = request.user.is_anonymous
    if eh_anonimo:
        if not documento.pode_ler(user=request.user, eh_consulta_publica=True):
            return httprr('/processo_eletronico/consulta_publica/', message="Este documento não pode ser visualizado na consulta pública.", tag='error')
    else:
        if not documento.pode_ler(user=request.user):
            raise PermissionDenied()

    if documento.arquivo.name.split('.')[-1] == 'html':
        return imprimir_pdf(documento.arquivo.open('r'), documento)

    # TODO Registrar Ação
    try:

        if request.GET.get('original') and request.GET.get('original') == 'sim':
            response = FileResponse(documento.arquivo.open('rb'), content_type='application/pdf')
        else:
            pdf = documento.get_pdf(user=request.user, eh_consulta_publica=eh_anonimo)
            response = HttpResponse(pdf, content_type='application/pdf')
            response['Content-Disposition'] = 'inline; filename=documento.pdf'
    except OSError:
        return httprr('/', 'Falha ao tentar visualizar documento digitalizado, por favor tente novamente.', 'error')
    except Exception as e:
        return httprr('/', str(e), 'error')
    return response


@method_decorator(login_required, name='dispatch')
class AssinarDocumentoTokenWizard(SessionWizardView):
    form_list = [GeradorIdentificadorDocumentoForm, PapelForm]
    template_name = "documento_eletronico/assinatura_token.html"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.hash = None
        self.data_emissao = None

    def dispatch(self, request, *args, **kwargs):
        self.documento_id = kwargs.get('documento_id')
        self.documento = get_documento_or_forbidden(self.request.user, self.documento_id)
        try:
            self.exibir_tela_para_gerar_identificador = self.documento.estah_para_receber_assinatura_balizadora(
                request.user)
        except ValidationError as e:
            return httprr('/', str(e), 'error')
        if not self.exibir_tela_para_gerar_identificador:
            self.form_list = {"0": AssinarDocumentoForm}

        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        kwargs.update({'request': self.request})
        if step is None or step == '0' and self.exibir_tela_para_gerar_identificador:
            kwargs.update({'documento_id': self.documento_id})
        return kwargs

    def get_form_prefix(self, step=None, form=None):
        # nao retorne ids estilizados
        return ""

    def render(self, form=None, **kwargs):
        documento = get_documento_or_forbidden(self.request.user, self.documento_id)
        if not documento.pode_assinar(self.request.user):
            raise PermissionDenied()
        return super().render(form, **kwargs)

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)
        step = self.steps.index
        if step == 1:
            self.data_emissao = get_datetime_now()
            if self.exibir_tela_para_gerar_identificador and not self.documento.tem_identificador_definitivo:
                cleaned_data = self.get_all_cleaned_data()
                self.documento.atribuir_identificador_e_processar_conteudo_final(
                    identificador_tipo_documento_sigla=cleaned_data['identificador_tipo_documento_sigla'],
                    identificador_numero=cleaned_data['identificador_numero'],
                    identificador_ano=cleaned_data['identificador_ano'],
                    identificador_setor_sigla=cleaned_data['identificador_setor_sigla'],
                    identificador_dono_documento=None,
                    data_emissao=self.data_emissao,
                )
            self.request.session['hash'] = self.documento.hash_conteudo
            self.request.session['data_emissao'] = self.data_emissao
        #
        context.update({'documento_id': self.documento_id})
        context.update({'documento': self.documento})
        context.update({'hash': self.documento.hash_conteudo})
        return context

    def done(self, form_list, **kwargs):
        documento = get_documento_or_forbidden(self.request.user, self.documento_id)
        if not documento.pode_assinar(self.request.user) or not self.request.user.has_perm(
                'documento_eletronico.change_documentotexto'):
            raise PermissionDenied()

        for form in form_list:
            if not form.is_valid():
                raise Exception('Os dados submetidos estão incorretos.')

        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                cleaned_data = self.get_all_cleaned_data()
                papel = cleaned_data.get('papel', None)
                cert = self.request.POST.get('cert', None)
                sig = str(self.request.POST.get('sig', None))
                data = str(self.request.POST.get('data', None))
                data_emissao = self.request.session['data_emissao']
                #
                if (cert and sig and data and data_emissao) is None:
                    raise SignerException()

                target = reverse_lazy('visualizar_documento', kwargs={'documento_id': self.documento_id},
                                      current_app='documento_eletronico')

                # Caso o documento ainda não tenha identificador, ele será atribuído nesse momento e o conteúdo
                # (cabeçalho, corpo e rodapé) processados.
                icpbrasil = CertificadoICPBrasil(cert)
                pessoa_fisica = get_object_or_404(PessoaFisica, email=icpbrasil.email)

                if self.exibir_tela_para_gerar_identificador and not documento.tem_identificador_definitivo:
                    documento.atribuir_identificador_e_processar_conteudo_final(
                        identificador_tipo_documento_sigla=cleaned_data['identificador_tipo_documento_sigla'],
                        identificador_numero=cleaned_data['identificador_numero'],
                        identificador_ano=cleaned_data['identificador_ano'],
                        identificador_setor_sigla=cleaned_data['identificador_setor_sigla'],
                        identificador_dono_documento=None,
                        data_emissao=data_emissao,
                    )
                    if data != documento.hash_conteudo:
                        return httprr(target, message="A sessão foi invalidada ", tag='error')
                    documento.save()

                # Assinar o documento
                assinar_documento_com_token(documento, cert, icpbrasil, sig, pessoa_fisica, papel)
                # Registrar ação
                registrar_acao_documento_texto(
                    self.request, documento, RegistroAcaoDocumento.TIPO_ASSINATURA,
                    user=self.request.user, observacao=f'Documento assinado por {self.request.user}'
                )
                #
                transaction.savepoint_commit(sid)
                return httprr(target, 'Documento assinado com sucesso.')
            except Exception as e:
                transaction.savepoint_rollback(sid)
                return httprr(target, message=str(e), tag='error')


@method_decorator(login_required, name='dispatch')
class AssinarDocumentoSenhaWizard(SessionWizardView):
    form_list = [GeradorIdentificadorDocumentoForm, AssinarDocumentoForm]
    template_name = "documento_eletronico/assinatura_senha.html"

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form, **kwargs)

        solicitacao_assinatura_com_anexacao_processo = self.documento.get_solicitacao_assinatura_com_anexacao_processo()
        if solicitacao_assinatura_com_anexacao_processo and solicitacao_assinatura_com_anexacao_processo.solicitacao_assinatura.solicitado == self.request.user.get_profile():
            context['processo_para_anexar'] = solicitacao_assinatura_com_anexacao_processo.processo_para_anexar

        context['documento'] = self.documento
        return context

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        self.documento_id = kwargs.get('documento_id')
        self.documento = get_documento_or_forbidden(self.request.user, self.documento_id)
        try:
            self.exibir_tela_para_gerar_identificador = self.documento.estah_para_receber_assinatura_balizadora(request.user)
        except ValidationError as e:
            return httprr('/', str(e), 'error')

        if not self.exibir_tela_para_gerar_identificador:
            self.form_list = {"0": AssinarDocumentoForm}
            try:
                del request.session['wizard_assinar_documento_senha_wizard']
            except Exception:
                pass
        return super().dispatch(request, *args, **kwargs)

    def get_form_kwargs(self, step=None):
        kwargs = super().get_form_kwargs(step)
        kwargs.update({'request': self.request})
        if step is None or step == '0' and self.exibir_tela_para_gerar_identificador:
            kwargs.update({'documento_id': self.documento_id})
        return kwargs

    def render(self, form=None, **kwargs):
        documento = get_documento_or_forbidden(self.request.user, self.documento_id)
        if not documento.pode_assinar(self.request.user):
            raise PermissionDenied()
        return super().render(form, **kwargs)

    def done(self, form_list, **kwargs):
        documento = get_documento_or_forbidden(self.request.user, self.documento_id)
        if not documento.pode_assinar(self.request.user):
            raise PermissionDenied()

        for form in form_list:
            if not form.is_valid():
                raise Exception('Os dados submetidos estão incorretos.')

        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                cleaned_data = self.get_all_cleaned_data()
                papel = form.cleaned_data.get('papel')

                # Caso o documento ainda não tenha identificador, ele será atribuído nesse momento e o conteúdo
                # (cabeçalho, corpo e rodapé) processados.
                data_emissao = get_datetime_now()
                if self.exibir_tela_para_gerar_identificador and not documento.tem_identificador_definitivo:

                    identificador_tipo_documento_sigla, identificador_numero, identificador_ano, identificador_setor_sigla = documento.get_sugestao_identificador_definitivo(
                        tipo_documento_texto=documento.modelo.tipo_documento_texto, setor_dono=documento.setor_dono
                    )
                    if identificador_tipo_documento_sigla != cleaned_data['identificador_tipo_documento_sigla']:
                        raise ValidationError('Tipo de documento escolhido incompatível.')
                    if identificador_numero != cleaned_data['identificador_numero']:
                        raise ValidationError('Número do documento escolhido incompatível.')

                    if documento.usa_sequencial_anual and identificador_ano and (identificador_ano != cleaned_data['identificador_ano']):
                        raise ValidationError('Ano do documento escolhido incompatível.')
                    if identificador_setor_sigla != cleaned_data['identificador_setor_sigla']:
                        raise ValidationError('Setor do documento escolhido incompatível.')

                    documento.atribuir_identificador_e_processar_conteudo_final(
                        identificador_tipo_documento_sigla=identificador_tipo_documento_sigla,
                        identificador_numero=identificador_numero,
                        identificador_ano=identificador_ano,
                        identificador_setor_sigla=identificador_setor_sigla,
                        identificador_dono_documento=None,
                        data_emissao=data_emissao,
                    )
                    documento.save()

                # Assinar o documento
                documento.assinar_via_senha(self.request.user, papel, data_emissao)

                # Registrar ação
                msg = f'Documento assinado por {self.request.user}'
                registrar_acao_documento_texto(self.request, documento, RegistroAcaoDocumento.TIPO_ASSINATURA, msg)

                target = reverse_lazy('visualizar_documento', kwargs={'documento_id': self.documento_id},
                                      current_app='documento_eletronico')
                transaction.savepoint_commit(sid)

                # Notificação_email Demanda_495
                solicitacao = documento.get_solicitacao_balizadora()
                if solicitacao.solicitado == self.request.user.get_profile():
                    solicitacoes_dependentes = solicitacao.get_solicitacoes_dependentes()
                    if solicitacoes_dependentes:
                        Notificar.solicitacao_assinatura_condicionantes(solicitacoes_dependentes, documento)
                return httprr(target, 'Documento assinado com sucesso.')
            except Exception as e:
                transaction.savepoint_rollback(sid)
                error_message = e or ', '.join(e)
                return httprr('.', message=error_message, tag='error')


class GeradorIdentificadorDocumentoView(FormView):
    '''
    View que tem apenas o objetivo de sugerir ao usuário um identificador para o documento de texto em questão e repassar
    para a view de assinatura o identificador escolhido.
    '''

    form_class = GeradorIdentificadorDocumentoForm
    template_name = "documento_eletronico/gerador_identificador_documento.html"

    def get(self, request, *args, **kwargs):
        documento_id = kwargs['documento_id']
        form = self.form_class(initial={}, documento_id=documento_id)
        return render(request, self.template_name, {'form': form})

    def get_success_url(self):
        success_url = reverse_lazy('assinar_documento_com_senha', kwargs={'documento_id': self.documento_id},
                                   current_app='documento_eletronico')
        return success_url


class AssinarDocumentoSenhaView(FormView):
    form_class = AssinarDocumentoForm
    template_name = "documento_eletronico/assinatura_senha.html"
    title = "Assinar Documento"

    def post(self, request, *args, **kwargs):
        self.documento_id = kwargs['documento_id']
        documento = get_documento_or_forbidden(request.user, self.documento_id)
        if not documento.pode_assinar(request.user) or not request.user.has_perm(
                'documento_eletronico.change_documentotexto'):
            raise PermissionDenied()

        form_class = self.get_form_class()
        form = self.get_form(form_class)
        form.request = request
        if form.is_valid():
            papel = form.cleaned_data.get('papel')
            documento.assinar_via_senha(request.user, papel)
            messages.success(request, 'Documento assinado com sucesso.')
            obs = f'Documento assinado por {request.user}'
            registrar_acao_documento_texto(request, documento, RegistroAcaoDocumento.TIPO_ASSINATURA, obs)
            return self.form_valid(form)
        else:
            return self.form_invalid(form)

    def get(self, request, *args, **kwargs):
        documento = get_object_or_404(DocumentoTexto, pk=kwargs['documento_id'])
        if not documento.pode_assinar(request.user) or not request.user.has_perm(
                'documento_eletronico.change_documentotexto'):
            raise PermissionDenied()

        # TODO: Implementar em documento um método para verificar se a assinatura que está se tentando realizar é a
        # balizadora. Se sim, então vai ser feito um bypass para a view GeradorIdentificadorDocumentoView.
        chamar_tela_para_gerar_identificador = True
        if chamar_tela_para_gerar_identificador:
            return GeradorIdentificadorDocumentoView.as_view()(self.request, *args, **kwargs)
        else:
            return super().get(request, *args, **kwargs)

    def get_success_url(self):
        return '/documento_eletronico/visualizar_documento/{}/'.format(self.documento_id)


def validar_assinatura_token(request, documento):
    cert = request.POST.get('cert', None)
    sig = str(request.POST.get('sig', None))
    data = str(request.POST.get('data', None))
    papel = str(request.POST.get('role', None))

    if (cert and sig and data) is None or (documento.hash_conteudo != data):
        return SignerException()

    icpbrasil = CertificadoICPBrasil(cert)
    pessoa_fisica = get_object_or_404(PessoaFisica, email=icpbrasil.email)
    papel = get_object_or_404(Papel, pk=papel)
    assinar_documento_com_token(documento, cert, icpbrasil, sig, pessoa_fisica, papel)


def validar_assinatura_token_view(request, documento_id, target=None):
    """
         Algoritmo de assinatura SHA-256 RSA
         Chave publica RSA 2048 bits
         Algoritmo de identificacao SHA1

    """
    documento = DocumentoTexto.objects.get_subclass(pk=documento_id)
    # O hash do documento enviado pelo servidor e o hash do documento
    # devolveido pelo cliente não batem.
    #
    if not target:
        target = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_id},
                              current_app='documento_eletronico')
    #
    try:
        validar_assinatura_token(request, documento)
        return HttpResponse(target)
    except SignerException:
        # Certificado invalida
        return httprr(target, message="O certificado fornecido não é válido", tag='error')
    except OpenSSL.crypto.Error:
        # Assinatura invalida
        return httprr(target, message="A assinatura fornecida não é válida", tag='error')
    except ValidationError as e:
        return httprr(target, message="{}".format(e), tag='error')


@rtr('documento_eletronico/assinatura_token.html')
@login_required()
def assinar_documento_token_view(request, documento_id):
    documento = get_object_or_404(DocumentoTexto, pk=documento_id)
    if not documento.pode_assinar(request.user) or not request.user.has_perm(
            'documento_eletronico.change_documentotexto'):
        raise PermissionDenied()
    title = 'Assinar Documento via Token'
    form = PapelForm(None)
    if form.is_valid():
        hash_conteudo = documento.hash_conteudo
    return locals()


@rtr()
@permission_required('documento_eletronico.change_documentotexto')
def revisar_documento(request, documento_id):
    documento = get_object_or_404(DocumentoTexto, pk=documento_id)
    if not documento.sou_revisor(request.user):
        raise PermissionDenied()
    title = 'Revisão de Documento'

    form = RevisarDocumentoForm(request.POST or None)
    if form.is_valid():
        notas_revisor = form.cleaned_data.get('notas_revisor')
        solicitacao = SolicitacaoRevisao.objects.filter(documento_id=documento_id, revisor=request.user.get_profile(),
                                                        data_resposta__isnull=True).first()
        if solicitacao:
            try:
                solicitacao.deferir_solicitacao()
                solicitacao.data_resposta = get_datetime_now()
                solicitacao.notas_revisor = notas_revisor
                solicitacao.save()

                compartilhamento = CompartilhamentoDocumentoPessoa.objects.filter(
                    pessoa_permitida=solicitacao.revisor, documento=documento, nivel_permissao=NivelPermissao.EDITAR,
                    tipo_permissao=TipoPermissao.REVISAO
                ).first()
                if compartilhamento:
                    compartilhamento.delete()
                #
                RegistroAcaoDocumentoTexto.objects.create(tipo=RegistroAcaoDocumento.TIPO_REVISADO, documento=documento,
                                                          ip=request.META.get('REMOTE_ADDR', ''),
                                                          observacao=notas_revisor)
            except Exception:
                raise PermissionDenied()

            return httprr(documento.get_absolute_url(), 'Revisão de documento realizada com sucesso.')
        else:
            raise PermissionDenied()
    else:
        return locals()


@permission_required('documento_eletronico.change_documentotexto')
@transaction.atomic()
def cancelar_revisao(request, documento_id):
    documento = get_object_or_404(DocumentoTexto, pk=documento_id)
    if documento.pode_cancelar_revisao():
        solicitacao = (
            SolicitacaoRevisao.objects.filter(documento_id=documento_id, data_resposta__isnull=True)
            .filter(Q(solicitante=request.user) | Q(revisor=request.user.get_profile()))
            .first()
        )
        if solicitacao:
            documento.cancelar_revisao()
            documento.save()
            solicitacao.delete()
            compartilhamento = CompartilhamentoDocumentoPessoa.objects.filter(
                pessoa_permitida=solicitacao.revisor, documento=documento, nivel_permissao=NivelPermissao.EDITAR,
                tipo_permissao=TipoPermissao.REVISAO
            ).first()
            if compartilhamento:
                compartilhamento.delete()

            RegistroAcaoDocumentoTexto.objects.create(
                tipo=RegistroAcaoDocumento.TIPO_CANCELAR_REVISAO, documento=documento,
                ip=request.META.get('REMOTE_ADDR', ''), observacao="Revisão cancelada por {}.".format(request.user)
            )

            if documento.pode_ler(request.user):
                url = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_id}, current_app='documento_eletronico')
            else:
                url = documento.get_documentos_url()

            Notificar.cancelamento_revisao(solicitacao.revisor, documento)
            return httprr(url, 'Revisão cancelada com sucesso.')
    raise PermissionDenied()


@rtr()
@permission_required('documento_eletronico.change_documentotexto')
def solicitar_revisao(request, documento_id):
    documento = get_object_or_404(DocumentoTexto, pk=documento_id)
    if not documento.pode_solicitar_revisao(request.user):
        raise PermissionDenied()
    title = 'Solicitação de Revisão'
    form = SolicitacaoRevisaoForm(request.POST or None)
    if form.is_valid():
        revisor = form.cleaned_data.get('revisor')
        obs = form.cleaned_data.get('observacao')

        with transaction.atomic():
            # Caso seja necessário adiciona permissão de edicao para
            # o revisor.
            if not documento.tem_permissao_editar(revisor.user):
                solicitacao, created = CompartilhamentoDocumentoPessoa.objects.get_or_create(
                    pessoa_permitida=revisor.user.get_profile(), documento=documento,
                    nivel_permissao=NivelPermissao.EDITAR, tipo_permissao=TipoPermissao.REVISAO
                )
            SolicitacaoRevisao.objects.get_or_create(documento_id=documento_id, revisor=revisor,
                                                     solicitante=request.user, data_resposta__isnull=True,
                                                     defaults={'observacao': obs})
            RegistroAcaoDocumentoTexto.objects.create(
                tipo=RegistroAcaoDocumento.TIPO_SOLICITAR_REVISAO, documento=documento,
                ip=request.META.get('REMOTE_ADDR', ''), observacao="{}:{}".format(revisor.user, obs)
            )
            documento.colocar_em_revisao()
            documento.save()

        Notificar.solicitacao_revisao(revisor, documento)
        return httprr('..', 'O documento foi enviado a {} para revisão.'.format(revisor.user))

    return locals()


@rtr('documento_eletronico/solicitar_assinatura.html')
@permission_required('documento_eletronico.change_documentotexto, documento_eletronico.change_documentotextopessoal')
def solicitar_assinatura(request, documento_id):
    documento = get_documento_or_forbidden(request.user, documento_id)
    if not documento.pode_solicitar_assinatura(request.user):
        raise PermissionDenied()

    title = 'Solicitações de Assinaturas'
    formset = SolicitacaoComplementaresFormSet(request.POST or None,
                                               form_kwargs={'request': request, 'documento': documento})
    main_form = SolicitacaoAssinaturaForm(request.POST or None, request=request, documento=documento)
    try:
        with transaction.atomic():
            if main_form.is_valid() and formset.is_valid():
                solicitado = main_form.cleaned_data.get('solicitacao')
                if solicitado and solicitado.eh_aluno:
                    aluno = solicitado.user.get_relacionamento()
                    aluno.criar_papel_discente()
                root = get_or_create_balizadora(request.user, solicitado, documento)
                solicitacoes = dict()
                for form in formset:
                    solicitado = form.cleaned_data.get('solicitacao', None)
                    solicitados = []
                    solicitados.append(solicitado)
                    ordem_solicitacao = int(form.cleaned_data.get('ordem', 1))
                    if form.is_valid() and solicitado:
                        if solicitado.eh_aluno:
                            aluno = solicitado.user.get_relacionamento()
                            aluno.criar_papel_discente()
                        solicitacao, created = get_or_create_solicitacao(request.user, solicitado, documento, True)
                        if not created:
                            continue
                        if ordem_solicitacao in solicitacoes:
                            solicitacoes[ordem_solicitacao].append(solicitacao)
                        else:
                            solicitacoes[ordem_solicitacao] = [solicitacao]
                # Se eu adicionei alguma solicitação complementar então anota ai
                if len(list(solicitacoes.keys())):
                    construir_ligacoes_entre_solicitacoes(solicitacoes, root)

                url = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_id},
                                   current_app='documento_eletronico')
                Notificar.solicitacao_assinatura(main_form.cleaned_data.get('solicitacao'), documento)
                return httprr(url, 'Sua solicitação foi enviada com sucesso.')
            return locals()
    except Exception as e:
        return httprr('.', message=str(e), tag='error')


@rtr('documento_eletronico/solicitar_assinatura_com_anexacao.html')
@permission_required('documento_eletronico.change_documentotexto')
def solicitar_assinatura_com_anexacao(request, documento_id):
    documento = get_documento_or_forbidden(request.user, documento_id)
    # Se for documento pessoal não pode solicitar assinatura com anexação
    # - Para solicitar é necessário que o documento não tenha documento.tem_identificador_definitivo
    # - Todos os documentos pessoais devem ser assinadaos pelo seu criador (solicitação de lobão na demanda 1078/1068)
    # - Para que o documento não seja corra o rsico de ser adicionado ao processo sem assinatura do seu criador
    # - Não se pode solicitar assinatura para si mesmo
    # - Não existe um "pode_solicitar_assinatura_com_anexacao" e por isso Essa rotina está aqui
    # Conclusão: não pode solicitar assinatura com anexação
    if documento.eh_documento_pessoal:
        raise PermissionDenied()

    if not documento.pode_solicitar_assinatura(request.user):
        raise PermissionDenied()

    title = 'Solicitações de Assinaturas Com Posterior Anexação ao Processo'
    formset = SolicitacaoComplementaresComAnexacaoFormSet(request.POST or None,
                                                          form_kwargs={'request': request, 'documento': documento})
    main_form = SolicitacaoAssinaturaComAnexacaoForm(request.POST or None, request=request, documento=documento)
    try:
        with transaction.atomic():
            if main_form.is_valid() and formset.is_valid():
                from processo_eletronico.models import SolicitacaoAssinaturaComAnexacaoProcesso
                from processo_eletronico.views import verifica_pode_editar_processo

                solicitado = main_form.cleaned_data.get('solicitacao')
                if solicitado and solicitado.eh_aluno:
                    aluno = solicitado.user.get_relacionamento()
                    aluno.criar_papel_discente()
                root = get_or_create_balizadora(request.user, solicitado, documento)
                verifica_pode_editar_processo(main_form.cleaned_data['processo_para_anexar'])
                solicitar_assinatura = get_or_create_balizadora(request.user, solicitado, documento)
                solicitar_assinatura_com_anexacao_para_processo = SolicitacaoAssinaturaComAnexacaoProcesso.objects.create(
                    solicitacao_assinatura=solicitar_assinatura,
                    processo_para_anexar=main_form.cleaned_data['processo_para_anexar'],
                    destinatario_setor_tramite=main_form.get_destino(),
                    papel_solicitante=main_form.cleaned_data['papel'],
                    despacho_corpo=main_form.cleaned_data['despacho_corpo'],
                )
                url = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_id},
                                   current_app='documento_eletronico')

                solicitacoes = dict()
                for form in formset:
                    solicitado = form.cleaned_data.get('solicitacao', None)
                    solicitados = []
                    solicitados.append(solicitado)
                    ordem_solicitacao = int(form.cleaned_data.get('ordem', 1))
                    if form.is_valid() and solicitado:
                        if solicitado.eh_aluno:
                            aluno = solicitado.user.get_relacionamento()
                            aluno.criar_papel_discente()
                        solicitacao, created = get_or_create_solicitacao(request.user, solicitado, documento, True)
                        if not created:
                            continue
                        if ordem_solicitacao in solicitacoes:
                            solicitacoes[ordem_solicitacao].append(solicitacao)
                        else:
                            solicitacoes[ordem_solicitacao] = [solicitacao]
                # Se eu adicionei alguma solicitação complementar então anota ai
                if len(list(solicitacoes.keys())):
                    construir_ligacoes_entre_solicitacoes(solicitacoes, solicitar_assinatura)

                url = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_id},
                                   current_app='documento_eletronico')
                Notificar.solicitacao_assinatura(main_form.cleaned_data.get('solicitacao'), documento)
                return httprr(url, 'Sua solicitação foi enviada com sucesso.')
            return locals()
    except Exception as e:
        return httprr('.', message=str(e), tag='error')


@permission_required('documento_eletronico.change_documentotexto, documento_eletronico.change_documentotextopessoal')
def concluir_documento(request, documento_id):
    documento = get_documento_texto(documento_id)
    if not documento:
        raise Http404()
    if not documento.pode_concluir_documento(request.user):
        raise PermissionDenied()
    match = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_id},
                         current_app='documento_eletronico')
    try:
        with transaction.atomic(), reversion.create_revision():
            deve_adicionar_avaliacao_revisao = not documento.eh_documento_pessoal and \
                documento.pode_rejeitar_revisao(request.user) and \
                documento.estah_em_revisado

            documento.concluir()
            documento.save()
            if deve_adicionar_avaliacao_revisao:
                solicitacao_revisao = documento.get_ultima_solicitacao_revisao_sem_avaliacao()
                solicitacao_revisao.adicionar_avaliacao_deferida(request.user)
                registrar_acao_documento_texto(request, documento, RegistroAcaoDocumento.TIPO_AVALIACAO_REVISAO, solicitacao_revisao.get_status_avaliacao())

        return httprr(match, 'Operação realizada com sucesso.')
    except Exception as error:
        error_message = '; '.join(error)
        return httprr(match, message=error_message, tag='error')


@permission_required('documento_eletronico.change_documentotexto')
@rtr()
def cancelar_documento(request, documento_id):
    documento = get_documento_or_forbidden(request.user, documento_id)
    title = documento.identificador
    #
    match = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_id}, current_app='documento_eletronico')
    if not documento.pode_ser_cancelado(request.user):
        if documento.status in [DocumentoStatus.STATUS_FINALIZADO]:
            return httprr(match, 'O documento não pode ser cancelado, pois está sendo usado por algum processo.', tag='error')
        else:
            return httprr(match, 'O documento não pode ser cancelado.', tag='error')
    #
    form = CancelarDocumentoForm(request.POST or None, instance=documento)
    if form.is_valid():
        try:
            form.save()
            registrar_acao_documento_texto(request, documento, RegistroAcaoDocumento.TIPO_CANCELAR_DOCUMENTO, documento.justificativa_cancelamento)
            #
            return httprr(match, 'Operação realizada com sucesso.')
        except Exception:
            raise PermissionDenied
    return locals()


@permission_required('documento_eletronico.change_documentotexto, documento_eletronico.change_documentotextopessoal')
def retornar_para_rascunho(request, documento_id):
    documento = get_documento_or_forbidden(request.user, documento_id)
    if documento.pode_retornar_para_rascunho(request.user):
        url = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_id},
                           current_app='documento_eletronico')
        with transaction.atomic(), reversion.create_revision():
            documento.editar_documento()
            documento.save()
        return httprr(url, 'Operação realizada com sucesso.')
    raise PermissionDenied()


@rtr()
@permission_required('documento_eletronico.view_documentotexto')
def visualizar_variaveis(request):
    title = 'Visualização de Variáveis'
    variaveis = get_variaveis(documento_identificador='MEMO 1/2017 - COSINF/DIGTI/RE/IFRN', to_dict=False)
    return locals()


# Não há a notação @login_required porque a página pode ser acessada pelo público externo para conferência de documento
# público.
def imprimir_documento_pdf(request, documento_id, orientacao=None):
    documento = get_documento_or_forbidden(request.user, documento_id)

    # Código adicionado para tratar a exibição quando o documento for autenticado
    # Se for um usuário não autenticado só mostra o documento se vinher junto o hash
    leitura_para_barramento = False
    consulta_publica_hash = None
    if request.user.is_anonymous:
        consulta_publica_hash = request.GET.get('hash')
        leitura_para_barramento = True
        if documento.hash_conteudo != consulta_publica_hash:
            raise PermissionDenied()
    elif not request.user.has_perm('documento_eletronico.view_documentotexto'):
        raise PermissionDenied('Você não tem permissão de visualizar o documento.')

    if orientacao == 'paisagem':
        orientacao = 'landscape'
    else:
        orientacao = 'portrait'

    try:
        eh_consulta_publica = False
        if consulta_publica_hash:
            eh_consulta_publica = True

        pdf = documento.get_pdf(orientacao=orientacao, user=request.user, consulta_publica_hash=consulta_publica_hash,
                                leitura_para_barramento=leitura_para_barramento, eh_consulta_publica=eh_consulta_publica)

        registrar_acao_documento_texto(request, documento, RegistroAcaoDocumento.TIPO_IMPRESSAO)
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = 'inline; filename=documento.pdf'
        return response
    except OSError:
        raise Http404('Erro ao gerar o arquivo PDF.')
    except Exception as e:
        return httprr('..', str(e), 'error')


@permission_required('documento_eletronico.view_documentotexto')
def exportar_pdfa(request, documento_id, orientacao=None):
    response = imprimir_documento_pdf(request, documento_id, orientacao)
    response.content = convert_to_pdfA(response.content)
    return response


@rtr()
def autenticar_documento(request):
    title = 'Autenticar Documento'
    codigo_autenticacao = request.GET.get('codigo_autenticacao')
    codigo_verificador = request.GET.get('codigo_verificador')
    form = AutenticacaoDocumentoTexto(request.POST or None, codigo_autenticacao=codigo_autenticacao,
                                      codigo_verificador=codigo_verificador)
    if form.is_valid():
        documento = form.processar()
    return locals()


@rtr()
def verificar_documento_externo(request):
    title = 'Verificar Documento Externo'
    codigo_autenticacao = request.GET.get('codigo_autenticacao')
    codigo_verificador = request.GET.get('codigo_verificador')
    form = AutenticacaoDocumentoDigitalizado(request.POST or None, codigo_autenticacao=codigo_autenticacao,
                                             codigo_verificador=codigo_verificador)
    if form.is_valid():
        try:
            documento = form.processar()
            if documento:
                if documento.nivel_acesso in [Documento.NIVEL_ACESSO_SIGILOSO, Documento.NIVEL_ACESSO_RESTRITO]:
                    return httprr('.', 'Documento {} é válido.'.format(documento.get_nivel_acesso_display()))
                arquivo = documento.arquivo
                arquivo.seek(0)
                return HttpResponse(arquivo.read(), content_type='application/pdf')
            else:
                return httprr('.', 'Documento inexistente.', 'error')
        except Exception:
            return httprr('.', 'Erro ao procurar o documento.', 'error')
    return locals()


@rtr()
@transaction.atomic()
@login_required()
def rejeitar_assinatura(request, documento_id):
    title = 'Rejeitar Solicitação de Assinatura'
    documento = get_documento_or_forbidden(request.user, documento_id)
    solicitacao = get_object_or_404(SolicitacaoAssinatura, documento_id=documento_id, data_resposta__isnull=True,
                                    solicitado=request.user.get_profile())

    if solicitacao.documento.identificador and solicitacao.documento.estah_aguardando_assinatura and not solicitacao.eh_balizadora:
        solicitacao.documento.marcar_como_assinado()

    url = None
    if documento.eh_documento_pessoal:
        url = '/admin/documento_eletronico/documentotextopessoal/'
    else:
        url = '/admin/documento_eletronico/documentotexto/'

    form = RejeitarSolicitacaoAssinaturaForm(request.POST or None, instance=solicitacao)
    if form.is_valid():
        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                form.save()
                registrar_acao_documento_texto(request=request, documento=documento, tipo_acao=RegistroAcaoDocumento.TIPO_SOLICITACAO_ASSINATURA_REJEITADA)
                assunto = '[SUAP] Documento Eletrônico: Rejeição de Solicitação de Assinatura'
                mensagem = (
                    '<h1>Documento Eletrônico</h1> <h2>Rejeição de Solicitação de Assinatura</h2>'
                    '<p>A solicitação de assinatura do documento {} foi rejeitada por {} com a seguinte '
                    'justificativa: {}</p>'.format(solicitacao.documento, solicitacao.solicitado,
                                                   solicitacao.justificativa_rejeicao)
                )

                send_notification(assunto,
                                  ''.join(mensagem),
                                  settings.DEFAULT_FROM_EMAIL,
                                  [solicitacao.solicitante.get_vinculo()],
                                  fail_silently=True)
                return httprr(url, 'Solicitação rejeitada com sucesso. '
                                   'Um e-mail foi enviado ao solicitante.')

            except Exception as e:
                transaction.savepoint_rollback(sid)
                return httprr('/documento_eletronico/visualizar_documento/{}/'.format(documento.id), str(e),
                              tag='error')

    return locals()


@login_required()
@permission_required('documento_eletronico.view_documentotexto')
def verificar_integridade(request, documento_id):
    documento = get_documento_or_forbidden(request.user, documento_id)
    match = documento.get_documentos_url()
    if documento.estah_assinado:
        for assinatura_documento in documento.assinaturadocumentotexto_set.all():
            if not assinatura_documento.validar_documento():
                return httprr(match, message='O documento "{}" foi violado.'.format(documento), tag='error')
        #
        return httprr(match, 'O documento "{}" encontra-se íntegro.'.format(documento))
    raise PermissionDenied


@rtr()
@permission_required('documento_eletronico.change_modelodocumento')
def clonar_modelo_documento(request, modelo_documento_id):
    modelo_documento = get_object_or_404(ModeloDocumento, pk=modelo_documento_id)
    classificacoes = modelo_documento.classificacao.all()
    modelo_documento.id = None
    for nome in iter_incrementing_name(modelo_documento.nome):
        try:
            if not ModeloDocumento.objects.filter(nome=nome).exists():
                modelo_documento.nome = nome
                modelo_documento.save()
                modelo_documento.classificacao.set(classificacoes)
                return httprr('/admin/documento_eletronico/modelodocumento/{}/'.format(modelo_documento.id),
                              'Modelo de Documento clonado com sucesso.')
        except Exception:
            raise PermissionDenied
    return httprr('/admin/documento_eletronico/modelodocumento/', 'Modelo de Documento não pode ser clonado.',
                  tag='error')


@rtr()
@permission_required('documento_eletronico.change_tipodocumento')
def clonar_tipo_documento(request, tipo_documento_id):
    tipo_documento = get_object_or_404(TipoDocumentoTexto, pk=tipo_documento_id)
    for nome in iter_incrementing_name(tipo_documento.nome):
        try:
            if not TipoDocumentoTexto.objects.filter(nome=nome).exists():
                tipo_documento_clone = TipoDocumentoTexto()
                tipo_documento_clone.cabecalho_padrao = tipo_documento.cabecalho_padrao
                tipo_documento_clone.rodape_padrao = tipo_documento.rodape_padrao
                tipo_documento_clone.nome = nome
                tipo_documento_clone.sigla = "".join([word[0] for word in nome.split()])
                tipo_documento_clone.save()
                return httprr('/admin/documento_eletronico/tipodocumento/{}/'.format(tipo_documento_clone.id),
                              'Tipo de Documento clonado com sucesso.')
        except Exception:
            raise PermissionDenied
    return httprr('/admin/documento_eletronico/tipodocumento/', 'O Tipo de Documento não pode ser clonado.',
                  tag='error')


@rtr()
@permission_required('documento_eletronico.change_documentotexto')
def clonar_documento(request, documento_id):
    documento = get_documento_or_forbidden(request.user, documento_id)
    if not documento.pode_clonar_documento(request.user):
        raise ValidationError("O documento não pode ser clonado.")

    if not documento.modelo.tipo_documento_texto.ativo:
        messages.error(request, f"O tipo do documento {documento.modelo.tipo_documento_texto} não pode ser clonado pois está inativo.")
        return httprr(documento.get_absolute_url())

    mensagem_alteracao = ''
    if not documento.hipotese_legal and documento.nivel_acesso in [Documento.NIVEL_ACESSO_RESTRITO,
                                                                   Documento.NIVEL_ACESSO_SIGILOSO]:
        mensagem_alteracao = ', no entanto o nível de acesso do documento clonado foi alterado para {}'.format(
            documento.modelo.get_nivel_acesso_padrao_display())
    if request.method == 'POST':
        form = DocumentoTextoForm(request.POST, request=request)
        if documento.eh_documento_pessoal:
            form = DocumentoTextoPessoalForm(request.POST, request=request)

        if form.is_valid():
            setor = None
            if not documento.eh_documento_pessoal:
                setor = get_setor(request.user)

            instance = form.save()
            instance.corpo = documento.corpo
            instance.save()

            return httprr(
                f"/documento_eletronico/visualizar_documento/{form.instance.id}/",
                'Documento foi clonado com sucesso{}.'.format(
                    mensagem_alteracao),
            )
    else:
        initial = {
            'tipo': documento.tipo.id,
            'modelo': documento.modelo.id,
            'hipotese_legal': documento.hipotese_legal.id if documento.hipotese_legal else None,
            'classificacao': documento.modelo.classificacao.all() if documento.modelo.classificacao else None,
        }
        if documento.eh_documento_pessoal:
            form = DocumentoTextoPessoalForm(initial=initial, request=request)
        else:
            initial['setor_dono'] = documento.setor_dono.id if not documento.eh_documento_pessoal else None
            form = DocumentoTextoForm(initial=initial, request=request)
        messages.success(request, "Para prosseguir com a clonagem edite as informações necessárias e informe o assunto do documento.")

    return locals()


@rtr()
@login_required()
@permission_required('documento_eletronico.change_documentotexto')
def assinar_documento_cert_view(request, documento_id):
    documento = get_object_or_404(DocumentoTexto, pk=documento_id)
    if not documento.pode_assinar(request.user):
        raise PermissionDenied()
    title = 'Assinar Documento via Certificado Digital'
    return locals()


@transaction.atomic()
@permission_required('documento_eletronico.change_documentotexto')
def rejeitar_revisao(request, documento_id):
    documento = get_object_or_404(DocumentoTexto, pk=documento_id)
    if documento.pode_rejeitar_revisao(request.user):
        solicitacao = (
            SolicitacaoRevisao.objects.filter(documento_id=documento_id, data_resposta__isnull=False,
                                              status=SolicitacaoStatus.STATUS_DEFERIDA)
            .order_by("-data_solicitacao")
            .first()
        )
        # reverting
        with transaction.atomic():
            try:
                previous_instance = get_previous(documento, solicitacao.data_solicitacao)
                previous_instance.revert()
            except Version.DoesNotExist:
                return httprr("..", 'Você deve Concluir o documento, pois não existe alteração na revisão.')

        documento = get_object_or_404(DocumentoTexto, pk=documento_id)
        documento.cancelar_revisao()
        documento.save()
        solicitacao.adicionar_avaliacao_indeferida(request.user)
        registrar_acao_documento_texto(request, documento, RegistroAcaoDocumento.TIPO_AVALIACAO_REVISAO, solicitacao.get_status_avaliacao())
        url = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento.id},
                           current_app='documento_eletronico')
        return httprr(url, 'Revisão rejeitada com sucesso.')
    #
    raise PermissionDenied()


@transaction.atomic()
@permission_required('documento_eletronico.change_documentotexto, documento_eletronico.change_documentotextopessoal')
def finalizar_documento(request, documento_id):
    documento = get_documento_or_forbidden(request.user, documento_id)

    url = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_id},
                       current_app='documento_eletronico')

    # Se for um documento pessoal deve exigir ao menos a assinatura do dono do documento
    if documento.eh_documento_pessoal:
        assinou = AssinaturaDocumentoTexto.objects.filter(documento=documento, assinatura__pessoa=documento.usuario_criacao.get_profile()).exists()
        if not assinou:
            return httprr(url, 'O documento pessoal só pode ser finalizado se tiver ao menos a assinatura de quem o criou.', tag='error')

    if documento.pode_finalizar_documento(request.user):
        documento.finalizar_documento()
        try:
            documento.save()
        except ValidationError as e:
            return httprr(url, str(e), 'error')
        # Registrar ação
        registrar_acao_documento_texto(request, documento, RegistroAcaoDocumento.TIPO_FINALIZACAO)
        return httprr(url, 'Documento finalizado com sucesso.')

    raise PermissionDenied()


@rtr()
@permission_required('documento_eletronico.change_documentotexto')
def vincular_documentos(request, documento_texto_base_id):
    title = 'Vincular Documentos'
    documento_texto_base = get_object_or_404(DocumentoTexto, pk=documento_texto_base_id)
    form = VinculoDocumentoTextoForm(data=request.POST or None, request=request,
                                     documento_texto_base=documento_texto_base)
    if form.is_valid():
        form.save()
        url = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_texto_base_id},
                           current_app='documento_eletronico')
        return httprr(url, 'Vínculo criado com sucesso.')

    return locals()


@permission_required('documento_eletronico.change_documentotexto')
def remover_vinculo_documento_texto(request, vinculo_documento_texto_id, documento_id):
    vinculo_documento_texto = get_object_or_404(VinculoDocumentoTexto, pk=vinculo_documento_texto_id)
    url = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_id},
                       current_app='documento_eletronico')
    vinculo_documento_texto.delete()
    return httprr(url, 'Operação realizada com sucesso.')


@permission_required('documento_eletronico.change_documentotexto')
def remover_solicitacao_assinatura(request, solicitacao_assinatura_id):
    solicitacao = get_object_or_404(SolicitacaoAssinatura, id=solicitacao_assinatura_id)
    redirect_url = reverse_lazy('visualizar_documento', kwargs={'documento_id': solicitacao.documento_id},
                                current_app='documento_eletronico')
    if solicitacao.status == SolicitacaoStatus.STATUS_ESPERANDO:
        solicitacao.delete_removendo_solicitacoes_dependentes()
        Notificar.remocao_solicitacao_assinatura(solicitacao, solicitacao.documento)
        mensagem = 'Solicitação removida com sucesso.'
        tag = 'success'
    else:
        mensagem = 'Solicitação só pode ser removida se ela estiver na situação ESPERANDO.'
        tag = 'error'
    return httprr(redirect_url, mensagem, tag)


@permission_required('documento_eletronico.change_documentotexto, documento_eletronico.change_documentotextopessoal')
def excluir_documento_texto(request, documento_id):
    documento = get_documento_or_forbidden(request.user, documento_id)
    if not documento.pode_ser_excluido():
        raise PermissionDenied()

    if not documento.eh_documento_pessoal:
        if 'estagios' in settings.INSTALLED_APPS:
            if DocumentoTexto.objects.filter(pk=documento.pk, praticaprofissional__isnull=False).exists():
                return httprr(request.META.get('HTTP_REFERER', '/'), 'Erro ao tentar excluir. Esse documento é referenciado por uma prática profissional no módulo de estágios.', 'error')
        if 'contratos' in settings.INSTALLED_APPS:
            if not documento.estah_em_rascunho and (documento.medicoes_despacho_set.exists() or documento.medicoes_termo_definitivo_set.exists()):
                return httprr(request.META.get('HTTP_REFERER', '/'), 'Erro ao tentar excluir. Esse documento é referenciado por uma medição no módulo de contratos.', 'error')

    try:
        # Garante que os anexos serao excluidos
        anexos_simples = documento.get_apenas_anexos_digitalizados_simples()
        for anexo_simples in anexos_simples:
            anexo_simples.delete()

        documento.delete()
    except Exception as e:
        return httprr(request.META.get('HTTP_REFERER', '/'), f'Não é possível excluir este documento. Detalhes: {str(e)}', 'error')

    url = None
    if documento.eh_documento_pessoal:
        url = '/admin/documento_eletronico/documentotextopessoal/'
    else:
        url = '/admin/documento_eletronico/documentotexto/'

    return httprr(url, 'Documento removido com sucesso.')


@rtr()
@login_required()
def solicitar_compartilhamento_documento_digitalizado(request, processo_id, documento_id):
    documento = get_object_or_404(DocumentoDigitalizado, id=documento_id)
    processos_incluido = documento.get_processos(
        exibir_somente_processos_nos_quais_documento_nao_foi_removido=True).first()
    app_processo_eletronico_disponivel = app_processo_eletronico_estah_instalada()
    if app_processo_eletronico_disponivel:
        Processo = apps.get_model('processo_eletronico', 'Processo')
        processo_incluido = documento.get_processos(
            exibir_somente_processos_nos_quais_documento_nao_foi_removido=True).filter(id=processo_id).first()
        if (
                documento.eh_documento_digitalizado
                and documento.eh_privado
                and not documento.pode_ler(request.user)
                and processo_incluido
                and processos_incluido.pode_editar(request.user)
                and not documento.tem_solicitacao_pendente_compartilhamento(request.user)
        ):
            title = 'Solicitar visualização do Documento {}'.format(documento.assunto)
            form = SolicitarCompartilhamentoDocumentoDigitalizadoForm(
                request.POST or None, pessoa_solicitante=request.user.get_profile(), documento=documento,
                processo=processo_incluido
            )
            if form.is_valid():
                form.save()
                return httprr('..', 'Solicitação de visualização feita com sucesso.')
            return locals()
    raise PermissionDenied('Você não pode solicitar visualização a esse documento.')


@rtr('documento_eletronico/avaliar_solicitacao_compartilhamento_documento_digitalizado.html')
@login_required()
def avaliar_solicitacao_compartilhamento_documento_digitalizado(request, processo_id, solicitacao_id):
    solicitacao = get_object_or_404(SolicitacaoCompartilhamentoDocumentoDigitalizadoPessoa, id=solicitacao_id)
    usuario_solicitacao = solicitacao.usuario_solicitacao
    documento = solicitacao.documento
    app_processo_eletronico_disponivel = app_processo_eletronico_estah_instalada()
    if app_processo_eletronico_disponivel:
        Processo = apps.get_model('processo_eletronico', 'Processo')
        processo_incluido = documento.get_processos(
            exibir_somente_processos_nos_quais_documento_nao_foi_removido=True).filter(id=processo_id).first()
        if documento.eh_documento_digitalizado and processo_incluido and documento.eh_privado and documento.tem_permissao_editar(
                request.user):
            title = 'Avaliar Solicitação de visualização do Documento {}'.format(documento.assunto)
            form = AvaliarSolicitacaoCompartilhamentoDocumentoDigitalizadoForm(request.POST or None,
                                                                               instance=solicitacao,
                                                                               processo=processo_incluido,
                                                                               documento_removido=False)
            if form.is_valid():
                form.save()
                return httprr('..', 'Avaliação da Solicitação de Visualização feita com sucesso.')
            return locals()
        elif (
                documento.get_processos(exibir_somente_processos_nos_quais_documento_nao_foi_removido=False).filter(
                    id=processo_id).first().get_documentos_removidos().filter(documento_id=documento.id)):
            processo_incluido = documento.get_processos(
                exibir_somente_processos_nos_quais_documento_nao_foi_removido=False).filter(id=processo_id).first()
            title = 'Avaliar Solicitação de visualização do Documento {}'.format(documento.assunto)
            form = AvaliarSolicitacaoCompartilhamentoDocumentoDigitalizadoForm(request.POST or None,
                                                                               instance=solicitacao,
                                                                               processo=processo_incluido,
                                                                               documento_removido=True)
            if form.is_valid():
                form.save()
                return httprr('..', 'Avaliação da Solicitação de Visualização feita com sucesso.')
            return locals()
        return httprr('.', 'Você não pode avaliar a solicitação de visualização desse documento.')
    raise PermissionDenied()


@rtr()
@login_required()
def documento_texto_editar_interessados(request, documento_id):
    documento = get_object_or_404(DocumentoTexto, id=documento_id)
    target = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento_id},
                          current_app='documento_eletronico')
    title = 'Editar Interessados do documento {}'.format(documento)
    if not documento.admite_interessados():
        return httprr(target, 'Esse tipo de documento não aceita interessados.', tag='error')
    #
    if not documento.pode_vincular_interessado(request.user):
        raise PermissionDenied(
            'Você não pode editar os interessados desse documento ou ' 'o presente documento não está finalizado.')
    #
    form = DocumentoTextoFormEditarInteressados(request.POST or None, documento=documento, request=request)
    if form.is_valid():
        interessados = form.cleaned_data.get('interessados')
        set_objeto = set(documento.interessados.all())
        set_form = set(interessados)
        if set_objeto != set_form:
            interessados_removidos = set_objeto.difference(set_form)
            interessados_adicionados = set_form.difference(set_objeto)

            motivo = 'Interessados adicionados: {}; Interessados Removidos: {}. Justificativa: {}'.format(
                ','.join([str(interessado) for interessado in interessados_adicionados] or ['Nenhum']),
                ', '.join([str(interessado) for interessado in interessados_removidos] or ['Nenhum']),
                form.cleaned_data.get('observacao_alteracao_interessados'),
            )
            documento.interessados.set(interessados)
            registrar_acao_documento_texto(request, documento, RegistroAcaoDocumento.TIPO_EDICAO_INTERESSADOS, motivo)
            # Notificar os interessados
            assunto = '[SUAP] Documento Eletrônico: Vinculação como interessado no documento'
            url_documento = urljoin(settings.SITE_URL, documento.get_absolute_url())
            if interessados_adicionados:
                mensagem_adicionados = f'''
                <h1>Documento Eletrônico</h1> <h2>Vinculação como interessado no documento</h2>
                <p>Você foi vinculado(a) ao documento <a href="{url_documento}">{documento}</a>. </p>
                '''
                vinculos = []
                for interessado in interessados_adicionados:
                    if interessado.eh_pessoa_fisica and interessado.pessoafisica.get_vinculo():
                        vinculos.append(interessado.pessoafisica.get_vinculo())
                    elif interessado.eh_pessoa_juridica and interessado.pessoajuridica.get_vinculo():
                        vinculos.append(interessado.pessoajuridica.get_vinculo())

                send_notification(assunto, mensagem_adicionados, settings.DEFAULT_FROM_EMAIL, vinculos,
                                  html=mensagem_adicionados, fail_silently=True)
            if interessados_removidos:
                mensagem_removidos = f'''
                <h1>Documento Eletrônico</h1>
                <h2>Desvinculação como interessado no documento</h2>
                <p>Você foi desvinculado(a) ao documento <a href="{url_documento}">{documento}</a>.</p>
                '''
                vinculos = []
                for interessado in interessados_removidos:
                    if interessado.eh_pessoa_fisica and interessado.pessoafisica.get_vinculo():
                        vinculos.append(interessado.pessoafisica.get_vinculo())
                    elif interessado.eh_pessoa_juridica and interessado.pessoajuridica.get_vinculo():
                        vinculos.append(interessado.pessoajuridica.get_vinculo())
                send_notification(assunto, mensagem_removidos, settings.DEFAULT_FROM_EMAIL, vinculos, html=mensagem_removidos,
                                  fail_silently=True)

            return httprr(target, 'Os interessados no documento foram alterados com sucesso.')
        return httprr(target, 'Não houve alteração nos interessados do documento.', tag='error')
    #
    return locals()


# View que se conecta a view rh.views.servidor
@receiver(rh_servidor_view_tab)
def servidor_view_tab_signal(sender, request, servidor, verificacao_propria, eh_chefe, **kwargs):
    tipo_portarias = TipoDocumento.objects.filter(nome__icontains='Portaria')
    portarias = DocumentoTexto.objects.filter(interessados=servidor, modelo__tipo_documento_texto__in=tipo_portarias,
                                              status=DocumentoStatus.STATUS_FINALIZADO)

    if portarias.exists():
        return render_to_string(template_name='documento_eletronico/templates/servidor_view_tab.html',
                                context={"lps_context": {"nome_modulo": "documento_eletronico"}, 'servidor': servidor, 'portarias': portarias}, request=request)
    return False


@rtr()
@login_required
def assinar_via_senha_documento_pessoal(request, documento_id):

    title = 'Assinatura de Documento com Senha'

    # Verifica se pode assinar
    # ------------------------
    documento = get_documento_or_forbidden(request.user, documento_id)
    if not documento.pode_assinar(request.user):
        raise PermissionDenied()

    if not request.user.get_profile().pessoafisica.get_cpf_ou_passaporte():
        raise PermissionDenied('Usuário não possui CPF.')

    if not request.user.get_profile().nome_usual:
        raise PermissionDenied('Usuário não possui nome usual.')

    # Verifica se foi com solicitacao de anexacao
    # ------------------------
    solicitacao_assinatura_com_anexacao_processo = documento.get_solicitacao_assinatura_com_anexacao_processo()
    if solicitacao_assinatura_com_anexacao_processo and solicitacao_assinatura_com_anexacao_processo.solicitacao_assinatura.solicitado == request.user.get_profile():
        processo_para_anexar = solicitacao_assinatura_com_anexacao_processo.processo_para_anexar

    # Gera a sugestao do identificador
    # ------------------------
    identificador_tipo_documento_sigla, identificador_numero, identificador_ano, identificador_dono_documento = documento.get_sugestao_identificador_definitivo(
        tipo_documento_texto=documento.modelo.tipo_documento_texto, usuario=documento.usuario_criacao, documento_id=documento_id
    )

    form = AssinarDocumentoForm(request.POST or None)
    if form.is_valid():
        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                papel = form.cleaned_data.get('papel')

                data_emissao = get_datetime_now()

                documento.atribuir_identificador_e_processar_conteudo_final(
                    identificador_tipo_documento_sigla=identificador_tipo_documento_sigla,
                    identificador_numero=identificador_numero,
                    identificador_ano=identificador_ano,
                    identificador_setor_sigla=None,
                    identificador_dono_documento=identificador_dono_documento,
                    data_emissao=data_emissao
                )
                documento.save()

                # Assinar o documento
                documento.assinar_via_senha(request.user, papel, data_emissao)

                # Registrar ação
                obs = f'Documento assinado por {request.user}'
                registrar_acao_documento_texto(request, documento, RegistroAcaoDocumento.TIPO_ASSINATURA, obs)
                target = reverse_lazy('visualizar_documento',
                                      kwargs={'documento_id': documento_id},
                                      current_app='documento_eletronico')
                transaction.savepoint_commit(sid)

                # Notificação_email Demanda_495
                solicitacao = documento.get_solicitacao_balizadora()
                if solicitacao.solicitado == request.user.get_profile():
                    solicitacoes_dependentes = solicitacao.get_solicitacoes_dependentes()
                    if solicitacoes_dependentes:
                        Notificar.solicitacao_assinatura_condicionantes(solicitacoes_dependentes,
                                                                        documento)

                return httprr(target, 'Documento assinado com sucesso.')
            except Exception as e:
                transaction.savepoint_rollback(sid)
                error_message = e or ', '.join(e)
                return httprr('.', message=error_message, tag='error')

    return locals()


@rtr()
@login_required
def assinar_documento_com_gov_br(request, documento_id):

    title = 'Assinatura de Documento'

    # Verifica se pode assinar
    # ------------------------
    documento = get_documento_or_forbidden(request.user, documento_id)
    if not documento.pode_assinar(request.user):
        raise PermissionDenied()

    if not request.user.get_profile().pessoafisica.get_cpf_ou_passaporte():
        raise PermissionDenied('Usuário não possui CPF.')

    if not request.user.get_profile().nome_usual:
        raise PermissionDenied('Usuário não possui nome usual.')

    # Verifica se foi com solicitacao de anexacao
    # ------------------------
    solicitacao_assinatura_com_anexacao_processo = documento.get_solicitacao_assinatura_com_anexacao_processo()
    if solicitacao_assinatura_com_anexacao_processo and solicitacao_assinatura_com_anexacao_processo.solicitacao_assinatura.solicitado == request.user.get_profile():
        processo_para_anexar = solicitacao_assinatura_com_anexacao_processo.processo_para_anexar

    # Gera a sugestao do identificador
    # ------------------------
    if isinstance(documento, DocumentoTextoPessoal):
        identificador_tipo_documento_sigla, identificador_numero, identificador_ano, identificador_dono_documento = documento.get_sugestao_identificador_definitivo(
            tipo_documento_texto=documento.modelo.tipo_documento_texto, usuario=documento.usuario_criacao, documento_id=documento_id)
    elif isinstance(documento, DocumentoTexto):
        identificador_tipo_documento_sigla, identificador_numero, identificador_ano, identificador_dono_documento = documento.get_sugestao_identificador_definitivo(
            tipo_documento_texto=documento.modelo.tipo_documento_texto, setor_dono=documento.setor_dono)

    form = AssinarDocumentoGovBRForm(request.POST or None, request=request)

    form.gerar_codigo_verificacao()
    messages.add_message(request, messages.SUCCESS, 'Código enviado com sucesso para App Gov.BR. A validade deste código é de 5 minutos!')

    if form.is_valid():
        with transaction.atomic():
            sid = transaction.savepoint()
            try:
                papel = form.cleaned_data.get('papel')

                data_emissao = get_datetime_now()

                setor_sigla = None
                if not documento.eh_documento_pessoal:
                    setor_sigla = documento.setor_dono.sigla

                documento.atribuir_identificador_e_processar_conteudo_final(
                    identificador_tipo_documento_sigla=identificador_tipo_documento_sigla,
                    identificador_numero=identificador_numero,
                    identificador_ano=identificador_ano,
                    identificador_setor_sigla=setor_sigla,
                    identificador_dono_documento=identificador_dono_documento,
                    data_emissao=data_emissao
                )
                documento.save()

                # Assinar o documento
                documento.assinar_via_senha(request.user, papel, data_emissao)

                # Registrar ação
                registrar_acao_documento_texto(request,
                                               documento,
                                               RegistroAcaoDocumento.TIPO_ASSINATURA,
                                               'Documento assinado por {}'.format(request.user))

                target = reverse_lazy('visualizar_documento',
                                      kwargs={'documento_id': documento_id},
                                      current_app='documento_eletronico')
                transaction.savepoint_commit(sid)

                # Notificação_email Demanda_495
                solicitacao = documento.get_solicitacao_balizadora()
                if solicitacao.solicitado == request.user.get_profile():
                    solicitacoes_dependentes = solicitacao.get_solicitacoes_dependentes()
                    if solicitacoes_dependentes:
                        Notificar.solicitacao_assinatura_condicionantes(solicitacoes_dependentes,
                                                                        documento)

                return httprr(target, 'Documento assinado com sucesso.')
            except Exception as e:
                transaction.savepoint_rollback(sid)
                if settings.DEBUG:
                    raise e
                error_message = e or ', '.join(e)
                return httprr('.', message=error_message, tag='error')

    return locals()


@rtr()
@login_required()
def visualizar_documento_digitalizado_pessoal(request, documento_id):
    documento = get_object_or_404(DocumentoDigitalizadoPessoal, pk=documento_id)

    title = documento

    if not documento.pode_ler(user=request.user):
        raise PermissionDenied()
    return locals()


@rtr('documento_eletronico/templates/visualizar_documento_digitalizado_pessoal.html')
@login_required()
def visualizar_documento_digitalizado_anexo_simples(request, documento_id):

    documento = get_object_or_404(DocumentoDigitalizadoAnexoSimples, pk=documento_id)

    title = documento

    if not documento.pode_ler(user=request.user):
        raise PermissionDenied()
    return locals()


@rtr('processo_eletronico/templates/listar_documentos_adicionar.html')
@permission_required('documento_eletronico.change_documentotexto')
def listar_documentos_anexar(request, documento_id):
    instance = get_documento_or_forbidden(request.user, documento_id)

    if not instance.pode_receber_anexos():
        raise PermissionDenied()

    title = 'Documentos que podem ser anexados {}'.format(instance)

    is_anexar_documento = True
    view_action = 'anexar_documento_a_documentotexto'

    # Filtrar os dados
    setor = get_setor(request.user)
    initial = dict(campus=setor.uo.pk, setor=setor.pk, ano=get_datetime_now().year)
    tem_apenas_tab = len(request.GET) == 1 and request.GET.get('tab')
    parametros_para_processar = initial
    if request.GET and not tem_apenas_tab:
        parametros_para_processar = request.GET
    form = ListarDocumentosTextoForm(parametros_para_processar, request=request, exceto_documento=instance)
    documentos, documentos_compartilhados, params, order_str = form.processar()

    # Exclusao dos documentos que nao podem ser anexados
    # - Documentos internos (texto) que ja tenham sido anexados a instance
    # - Documentos digitalizados que ja tenham sido anexados a instance
    documentos_internos_ja_anexados_ids = DocumentoTextoAnexoDocumentoTexto.objects.filter(documento=instance).values_list('documento_anexado__id', flat=True)
    documentos_digitalizados_ja_anexados_ids = DocumentoTextoAnexoDocumentoDigitalizado.objects.filter(documento=instance).values_list('documento_anexado__id', flat=True)
    #
    documentos = documentos.filter(status=DocumentoStatus.STATUS_FINALIZADO)
    documentos = documentos.exclude(id__in=documentos_internos_ja_anexados_ids)
    documentos = documentos.order_by('-data_criacao', 'identificador_tipo_documento_sigla', 'identificador_numero',
                                     'identificador_ano', 'identificador_setor_sigla')
    #
    documentos_pessoais = DocumentoTextoPessoal.objects.proprios(request.user).defer('cabecalho', 'rodape', 'corpo')
    documentos_pessoais = documentos_pessoais.filter(status=DocumentoStatus.STATUS_FINALIZADO)
    documentos_pessoais = documentos_pessoais.exclude(id__in=documentos_internos_ja_anexados_ids)
    #
    documentos_pessoais_digitalizados = DocumentoDigitalizadoPessoal.objects.filter(usuario_criacao=request.user)
    documentos_pessoais_digitalizados = documentos_pessoais_digitalizados.exclude(id__in=documentos_digitalizados_ja_anexados_ids)

    return locals()


@transaction.atomic()
@permission_required('documento_eletronico.change_documentotexto')
def anexar_documento_a_documentotexto(request, documentotexto_id, documento_id):
    # Documento que vai receber o anexo
    instance = get_documento_or_forbidden(request.user, documentotexto_id)

    if not instance.pode_receber_anexos():
        raise PermissionDenied()

    # Documento que serah anexado
    documento = None
    try:
        documento = get_documento_or_forbidden(request.user, documento_id)
    except Exception:
        try:
            documento = get_documento_digitalizado(documento_id)
        except Exception:
            raise Http404()

    # Anexando
    d = None
    if documento.eh_documento_texto:
        d = DocumentoTextoAnexoDocumentoTexto()
    elif documento.eh_documento_digitalizado:
        d = DocumentoTextoAnexoDocumentoDigitalizado()
    d.documento = instance
    d.documento_anexado = documento
    d.save()

    redirect_url = reverse_lazy('visualizar_documento', kwargs={'documento_id': instance.id}, current_app='documento_eletronico')

    return httprr(redirect_url, 'Solicitação removida com sucesso.')


@transaction.atomic()
@permission_required('documento_eletronico.change_documentotexto')
def desanexar_documento(request, documentotexto_id, documento_id):
    # Documento que tem o anexo
    instance = get_documento_or_forbidden(request.user, documentotexto_id)

    if not instance.pode_receber_anexos():
        raise PermissionDenied()

    # Documento que serah dexanexado
    documento = None
    try:
        documento = get_documento_or_forbidden(request.user, documento_id)
    except Exception:
        try:
            documento = get_documento_digitalizado(documento_id)
        except Exception:
            raise Http404()

    # Desanexando
    d = None
    if documento.eh_documento_texto:
        d = get_object_or_404(DocumentoTextoAnexoDocumentoTexto, documento=instance, documento_anexado=documento)
    elif documento.eh_documento_digitalizado:
        d = get_object_or_404(DocumentoTextoAnexoDocumentoDigitalizado, documento=instance, documento_anexado=documento)
    d.delete()

    redirect_url = reverse_lazy('visualizar_documento', kwargs={'documento_id': instance.id},
                                current_app='documento_eletronico')

    return httprr(redirect_url, 'Documento desanexado com sucesso.')


@rtr()
@permission_required('documento_eletronico.pode_alterar_nivel_acesso_documento_texto')
def alterar_nivel_acesso_documento_texto(request, documento_texto_id):
    documento = get_documento_or_forbidden(request.user, documento_texto_id)
    user = request.user
    if not documento.pode_alterar_nivel_acesso(user):
        raise PermissionDenied()

    title = 'Alterar Nível de Acesso do Documento {}'.format(documento)

    existe_solicitacoes_aberto = documento.existe_solicitacoes_nivel_acesso_aberto()
    if existe_solicitacoes_aberto:
        error_message = 'Não é possível alterar o nível de acesso sem antes analisar as solicitações de alteração de nível de acesso que estão em aberto.'
        return httprr('..', error_message, tag='error')

    #
    form = DocumentoAlterarNivelAcessoForm(request.POST or None, request=request, documento=documento)
    if form.is_valid():
        try:
            DocumentoTexto.alterar_nivel_acesso(
                documento,
                int(form.cleaned_data.get('nivel_acesso')),
                form.cleaned_data.get('hipotese_legal'),
                request.user,
                request.META.get('REMOTE_ADDR', ''),
                form.cleaned_data.get('justificativa'),
            )

            # Importante para usabilidade
            url = None
            if request.GET.get('processo'):
                url = reverse_lazy('processo', kwargs={'processo_id': request.GET.get('processo')},
                                   current_app='processo_eletronico')
            elif documento.pode_ler(request.user):
                url = reverse_lazy('visualizar_documento', kwargs={'documento_id': documento.id},
                                   current_app='documento_eletronico')
            else:
                # Se o usuario editar o nivel de acesso e por isso nao tiver mais acesso ao documento
                # - Sera redirecionado a lista de documentos
                url = '/admin/processo_eletronico/processo/?opcao=1'

            return httprr(url, 'Nível de Acesso alterado com sucesso.')
        except Exception as e:
            error_message = '{}'.format(e) or ', '.join(e.messages)
            return httprr('..', error_message, tag='error')

    #
    return locals()


@rtr()
@permission_required('documento_eletronico.pode_alterar_nivel_acesso_documento_digitalizado')
def alterar_nivel_acesso_documento_digitalizado(request, documento_digitalizado_id):
    documento = get_object_or_404(DocumentoDigitalizado, id=documento_digitalizado_id)
    user = request.user
    if not documento.pode_alterar_nivel_acesso(user):
        raise PermissionDenied()

    existe_solicitacoes_aberto = documento.existe_solicitacoes_nivel_acesso_aberto()
    if existe_solicitacoes_aberto:
        error_message = 'Não é possível alterar o nível de acesso sem antes analisar as solicitações de alteração de nível de acesso que estão em aberto.'
        return httprr('..', error_message, tag='error')

    #
    title = 'Alterar Nível de Acesso do Documento Digitalizado {}'.format(documento)

    form = DocumentoAlterarNivelAcessoForm(request.POST or None, request=request, documento=documento)
    if form.is_valid():
        try:
            documento.alterar_nivel_acesso(
                int(form.cleaned_data.get('nivel_acesso')),
                form.cleaned_data.get('hipotese_legal'),
                request.user,
                request.META.get('REMOTE_ADDR', ''),
                form.cleaned_data.get('justificativa'),
                form.cleaned_data.get('pessoas_compartilhadas'),
            )
            return httprr('..', 'Nível de Acesso alterado com sucesso.')
        except Exception as e:
            error_message = '{}'.format(e) or ', '.join(e.messages)
            return httprr('..', error_message, tag='error')

    return locals()


@login_required()
def enviar_codigo_verificacao_govbr(request):
    # API NOTIFICA GOV BR
    API_KEY_NOTIFICA_GOVBR = Configuracao.get_valor_por_chave('catalogo_provedor_servico',
                                                              'api_key_notifica_govbr') or "balcao_digital-c4764905-0bb2-4259-ae69-cc8efa2f7402-12ed59cf-b52b-4655-b0c1-242858612cc5"
    TEMPLATE_PADRAO_SUAP_APP_GOVBR = Configuracao.get_valor_por_chave('catalogo_provedor_servico',
                                                                      'id_template_notifica_padrao_suap_app_govbr') or "4c4e7279-755e-40e9-8040-f0cd0b64c48e"
    HABILITAR_NOTIFICA_GOVBR = Configuracao.get_valor_por_chave('catalogo_provedor_servico',
                                                                'habilitar_notifica_govbr') or False

    # TODO: o que fazer se notifica não tá habilitado enviar_por_email ou redirecionar e exibir mensagem que o tente mais tarde
    if not settings.DEBUG and not HABILITAR_NOTIFICA_GOVBR:
        messages.add_message(request, messages.ERROR,
                             'Não é possível enviar o código de verificação pois a integração do SUAP com a Plataforma Notifica está desativada!')

    force_new_code = request.GET.get('action', False)

    if not cache.get(f'govbr_check_{request.user.get_vinculo().id}', None) or force_new_code:
        codigo_verificacao = random_with_N_digits(5)
        cache.set(f'govbr_check_{request.user.get_vinculo().id}', codigo_verificacao, 300)
        mensagem_app_govbr = f"Código de verificação - SUAP/IFRN: {codigo_verificacao}"
        try:
            from notifications_python_client.notifications import NotificationsAPIClient
            cliente_notifica_govbr = NotificationsAPIClient(API_KEY_NOTIFICA_GOVBR)
            cpf = request.user.get_profile().cpf.replace('.', '').replace('-', '')
            cliente_notifica_govbr.send_app_govbr_cpf_notification(
                cpf=cpf,
                template_id=TEMPLATE_PADRAO_SUAP_APP_GOVBR,
                personalisation={'mensagem': mensagem_app_govbr, })
            messages.add_message(request, messages.SUCCESS, 'Código enviado com sucesso para App Gov.BR. A validade deste código é de 5 minutos!')
        except Exception:
            messages.add_message(request, messages.ERROR, 'Houve um erro ao enviar código de verificação, certifique-se que possui o aplicativo Gov.BR instalado!')
            return HttpResponse('ERROR')
        print(f"Código: {codigo_verificacao}")
    return HttpResponse('OK')
