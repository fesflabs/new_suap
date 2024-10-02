import base64
import datetime
import hashlib
import operator
import os
import subprocess
import sys
import tempfile
import traceback
from functools import reduce
from random import randint
from uuid import uuid4

from django.apps import apps
from django.conf import settings
from django.db.models import Q
from django.http import HttpResponse
from django.contrib.contenttypes.models import ContentType
from django.template import Context, Template
from django.template.loader import get_template
from django.utils.safestring import mark_safe
from reversion.models import Version
from wkhtmltopdf.views import PDFTemplateResponse

from comum.models import Configuracao
from comum.utils import get_setor, get_setor_procuradoria, get_sigla_reitoria, tl
from comum.utils import get_uo
from djtools.storages import cache_file
from djtools.templatetags.filters import format_
from djtools.utils import get_datetime_now
from djtools.utils import send_notification
from documento_eletronico.status import DocumentoStatus
from rh.models import Setor, UnidadeOrganizacional

try:
    from weasyprint import HTML
except ModuleNotFoundError:
    pass

# Recomendamos que o tamanho máximo de path (PRIVATE_ROOT_DIR) não exceda 94 caracteres
# Considerar: https://gitlab.ifrn.edu.br/cosinf/suap/-/issues/3705
PRIVATE_ROOT_DIR = 'private-media/processo_eletronico'


class EstagioProcessamentoVariavel:
    CRIACAO_DOCUMENTO = 'Criação do Documento'
    ASSINATURA_DOCUMENTO = 'Assinatura do Documento'


def get_documento_texto_tamanho_maximo_em_mb():
    return round(settings.PROCESSO_ELETRONICO_DOCUMENTO_EXTERNO_MAX_UPLOAD_SIZE / 1024.0 / 1024.0, 2)


def gerar_codigo_verificador_documento(documento, msg=None):

    msg = (
        msg
        or '<p>Este documento foi emitido pelo SUAP em {0}. Para comprovar sua autenticidade, '
        'faça a leitura do QRCode ao lado ou acesse {1} e forneça os dados abaixo:</p>'
        '<dl><dt>Código Verificador:</dt><dd>{2}</dd><dt>Código de Autenticação:</dt><dd>{3}</dd></dl>'
    )

    #
    codigo_verificador = mark_safe(msg.format(documento.data_criacao.strftime('%d/%m/%Y'), documento.get_url_autenticacao(), documento.id, documento.codigo_autenticacao))
    return codigo_verificador


def convert_pdf_to_string_b64(pdf):
    '''
    Método que converte o pdf (byte string) numa string base 64. Isso é bastante útil para a transmissão de conteúdo
    binário.

    :param pdf: byte string
    :return: String Base 64 do pdf
    '''
    return base64.b64encode(pdf)


def gerar_pdf_documento_texto(documento, orientacao, user, consulta_publica_hash, leitura_para_barramento, eh_consulta_publica=False):
    '''
    Retorna uma string contendo os bytes do pdf do documento, por completo, ou seja, contendo inclusive as assinaturas.
    Obs: Caso o usuário em questão não tenha permissão para ver o conteúdo do documento somente serão impressos os dados
    básicos do documento.

    :param documento: Documento do qual se quer obter os bytes do pdf.
    :param orientacao: Informar 'landscape' ou 'portrait'.
    :param user: Usuário que está tentando realizar a impressão.
    :param consulta_publica_hash hash da consulta externa
    :param leitura_para_barramento É um boleano que indica se o pdf gerado é para ser usado no barramento.
    :return string com os bytes do pdf do documento.
    '''
    imprimir_somente_dados_basicos = not documento.pode_ler(user=user,
                                                            consulta_publica_hash=consulta_publica_hash,
                                                            leitura_para_barramento=leitura_para_barramento,
                                                            eh_consulta_publica=eh_consulta_publica)

    if imprimir_somente_dados_basicos:

        from djtools.pdf import generate_pdf

        file_object = HttpResponse(content_type='application/pdf')
        context = {'documento': documento, 'instituicao': Configuracao.get_valor_por_chave('comum', 'instituicao'), 'uo': get_uo(user)}
        template = 'imprimir_documento_restrito.html'

        try:
            pdf_response = generate_pdf(template, file_object=file_object, context=context)
            # Se passar file_object = None, o objeto retornado vai ser um StringIO, daí o conteúdo do pdf estará disponível
            # em pdf_response.getvalue(). Caso file_object seja um HttpResponse, o objeto de retorno será um HttpResponse e
            # o conteúdo do pdf estará disponível em pdf_response.content.
            pdf = pdf_response.content
            return pdf
        except OSError as e:
            raise OSError(f'Erro ao gerar o arquivo PDF: {e}')
    else:
        template = 'imprimir_documento_pdf.html'

        # Gerando os dados para os campos verificador e autenticador
        # de documentos
        codigo_verificador = gerar_codigo_verificador_documento(documento)
        # Selo
        selo = os.path.join(settings.STATIC_ROOT, 'comum/img/selo-protocolo.png')
        selo_data = base64.b64encode(open(selo, 'rb').read()).decode('utf-8')
        selo_data = "data:image/png;base64," + selo_data
        # QR code
        qrcode_data = documento.qrcode_base64image

        agora = get_datetime_now()

        try:
            pdf = PDFTemplateResponse(
                None, template, context=locals(), cmd_options={'header-spacing': 3, 'footer-spacing': 3, 'orientation': orientacao, 'page-height': '297mm', 'page-width': '210mm'}
            ).rendered_content
            # return HttpResponse(pdf, content_type='application/pdf')
            return pdf
        except OSError as e:
            raise OSError(f'Erro ao gerar o arquivo PDF: {e}')


def gerar_pdf_documento_digitalizado(documento, orientacao, user, consulta_publica_hash, leitura_para_barramento, eh_consulta_publica=False):
    def add_file_temp_dir(content):
        base_filename = f'{datetime.datetime.now()}.pdf'
        filename = os.path.join(settings.TEMP_DIR, base_filename.replace(" ", "_"))
        arquivo = open(filename, 'wb+')
        arquivo.write(content)
        arquivo.close()
        return arquivo.name

    def remove_file_temp_dir(path_file):
        try:
            os.remove(path_file)
        except FileNotFoundError:
            pass

    imprimir_somente_dados_basicos = not documento.pode_ler(user=user,
                                                            consulta_publica_hash=consulta_publica_hash,
                                                            leitura_para_barramento=leitura_para_barramento,
                                                            eh_consulta_publica=eh_consulta_publica)

    conteudo_pdf_assinaturas = gerar_assinatura_documento_digitalizado_pdf(documento, orientacao, user, eh_consulta_publica)
    if not imprimir_somente_dados_basicos:
        # Para os casos de termo de ciência em que o documento digitalizado
        # trata-se de um html será utilizada a função de geraçã do documento texto
        if documento.arquivo.name.split('.')[-1] == 'html':
            return imprimir_pdf(documento.arquivo.open('r'), documento).content
        arquivo_digitalizado = cache_file(documento.arquivo.name)
        path_arquivo_assinatura = add_file_temp_dir(conteudo_pdf_assinaturas)
        arquivo_final = merge_pdf_files([arquivo_digitalizado, path_arquivo_assinatura])
        remove_file_temp_dir(path_arquivo_assinatura)
        remove_file_temp_dir(arquivo_digitalizado)
        return arquivo_final

    return conteudo_pdf_assinaturas


def gerar_assinatura_documento_digitalizado_pdf(documento, orientacao, user, eh_consulta_publica):
    agora = get_datetime_now()
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao')
    if user and not user.is_anonymous:
        uo = get_uo(user)
    msg = (
        '<p>Este documento foi armazenado no SUAP em {}. Para comprovar sua integridade, '
        'faça a leitura do QRCode ao lado ou acesse {} e forneça os dados abaixo:</p>'
        '<dl><dt>Código Verificador:</dt><dd>{}</dd><dt>Código de Autenticação:</dt><dd>{}</dd></dl>'
    )
    codigo_verificador = gerar_codigo_verificador_documento(documento, msg)

    try:
        pdf = PDFTemplateResponse(
            None,
            'documento_eletronico/templates/imprimir_assinaturas_pdf.html',
            context=locals(),
            header_template='imprimir_documento_pdf_cabecalho.html',
            footer_template='imprimir_documento_pdf_rodape.html',
            cmd_options={'header-spacing': 3, 'footer-spacing': 3, 'orientation': orientacao, 'page-height': '297mm', 'page-width': '210mm', 'enable-local-file-access': True},
        ).rendered_content
        return pdf
    except OSError as e:
        raise OSError(f'Erro ao gerar o arquivo PDF: {e}')

# TODO: Remover este método após validar uso do PDFUNITE
# def merge_pdf_files_gs(paths_files):
#     gs = getattr(settings, 'GHOSTSCRIPT_CMD', None)
#     outfile = tempfile.NamedTemporaryFile(suffix=".pdf", dir=settings.TEMP_DIR, delete=False)
#     directory = tempfile.mkdtemp(dir=settings.TEMP_DIR)
#     cmd = [gs, "-dPDF=1", "-dQUIET", "-dBATCH", "-dNOPAUSE", "-q", "-sDEVICE=pdfwrite", "-dPDFSETTINGS=/prepress", "-sOutputFile=" + outfile.name]
#     cmd.extend(paths_files)
#     try:
#         dict_env = {'TMPDIR': settings.TEMP_DIR, 'TEMP': settings.TEMP_DIR}
#         subprocess.call(cmd, stderr=sys.stdout, cwd=directory, env=dict_env)
#         output_pdf = outfile.read()
#         outfile.close()  # deletes the file
#         os.remove(outfile.name)
#         return output_pdf
#     except OSError:
#         raise Exception("Error executing Ghostscript ({0}). Is it in your PATH?".format(gs))
#     except Exception:
#         raise Exception("Error while running Ghostscript subprocess. Traceback: \n {0}".format(traceback.format_exc()))


def merge_pdf_files(paths_files):
    pdfunite = getattr(settings, 'PDFUNITE_CMD', None)
    outfile = tempfile.NamedTemporaryFile(suffix=".pdf", dir=settings.TEMP_DIR, delete=False)
    directory = tempfile.mkdtemp(dir=settings.TEMP_DIR)
    cmd = [pdfunite]
    for path in paths_files:
        cmd.append(path)
    cmd.append(outfile.name)
    try:
        dict_env = {'TMPDIR': settings.TEMP_DIR, 'TEMP': settings.TEMP_DIR}
        subprocess.call(cmd, cwd=directory, env=dict_env)
        output_pdf = outfile.read()
        outfile.close()  # deletes the file
        os.remove(outfile.name)
        return output_pdf
    except OSError:
        raise Exception(f"Error executing pdfunite ({pdfunite}). Is it in your PATH?")
    except (SystemExit, Exception):
        raise Exception(f"Error while running pdfunite subprocess. Traceback: \n {traceback.format_exc()}")


def merge_pdfs_pdf(lista_pdf, prefixo_documento):
    paths_files = []

    def add_file_temp_dir(content, nome_arquivo):
        base_filename = f'{nome_arquivo}.pdf'
        filename = os.path.join(settings.TEMP_DIR, base_filename.replace(" ", "_"))
        arquivo = open(filename, 'wb+')
        arquivo.write(content)
        arquivo.close()
        paths_files.append(arquivo.name)

    def remove_files_temp_dir(paths_files):
        for path_file in paths_files:
            os.remove(path_file)

    ordem = 0
    for pdf in lista_pdf:
        ordem += 1
        add_file_temp_dir(pdf, f"{prefixo_documento}_{ordem}")

    arquivo_final = merge_pdf_files(paths_files)
    remove_files_temp_dir(paths_files)
    return arquivo_final


def imprimir_pdf(template_file, documento):
    if documento.eh_valido():
        msg = (
            '''
        <footer>
            <div align="center">Este documento foi emitido pelo SUAP e validado por <strong>: '''
            + format_(documento.imprimir_assinaturas())
            + '''</strong></div>
        </footer>'''
        )
    else:
        msg = '''
        <footer>
            <div align="center"><strong>Este documento sofreu alterações após a sua assinatura</strong></div>
        </footer>'''
    html = template_file.read()
    template_file.close()
    if isinstance(html, bytes):
        html = html.decode()
    html = html.replace('</body>', f'{msg}</body>')
    html = html.replace('/static/', 'static/')

    base_url = 'file://{}{}'.format(settings.BASE_DIR, '/deploy')

    filename = tempfile.mktemp()
    HTML(string=html, base_url=base_url).write_pdf(filename)
    with open(filename, 'rb') as f:
        out = f.read()
    return HttpResponse(out, content_type='application/pdf')


def app_processo_eletronico_estah_instalada():
    return 'processo_eletronico' in settings.INSTALLED_APPS


def solicitacoes_juntada_pendentes(documento):
    if app_processo_eletronico_estah_instalada():
        SolicitacaoJuntadaDocumento = apps.get_model("processo_eletronico", "SolicitacaoJuntadaDocumento")
        from processo_eletronico.status import SolicitacaoJuntadaDocumentoStatus
        #
        content_type = ContentType.objects.get_for_model(documento)
        return SolicitacaoJuntadaDocumento.objects.filter(
            status=SolicitacaoJuntadaDocumentoStatus.STATUS_ESPERANDO,
            anexo_content_id=documento.id,
            anexo_content_type=content_type
        )
    return None


def existem_solicitacoes_juntada_pendentes(documento):
    solicitacoes = solicitacoes_juntada_pendentes(documento)
    return solicitacoes.exists() if solicitacoes else False


def usuario_deve_ter_acesso_a_documento_restrito_atraves_de_solicitacao_juntada_pendente(user, documento):
    '''
    Este método verifica se, para o documento em questão, há uma solicitação de juntada pendente para a qual o solicitante
    (avaliador) é o usuário em questão. Se sim, a leitura do documento será permitida.

    :param user: usuário que deseja acessar o documento
    :param documento: documento restrito para o qual se deseja acesso
    :return: True caso o usuário deva ter acesso ao documento, False caso contrário.
    '''
    if documento.eh_restrito and app_processo_eletronico_estah_instalada():
        SolicitacaoJuntadaDocumento = apps.get_model("processo_eletronico", "SolicitacaoJuntadaDocumento")
        from processo_eletronico.status import SolicitacaoJuntadaDocumentoStatus
        from processo_eletronico.models import Tramite

        setores_visiveis = Tramite.get_todos_setores(user=user)

        solicitacoes_juntada_em_avaliacao_nos_meus_setores = SolicitacaoJuntadaDocumento.objects.filter(
            status=SolicitacaoJuntadaDocumentoStatus.STATUS_ESPERANDO, solicitacao_juntada__tramite__processo__setor_atual__in=setores_visiveis
        )

        if solicitacoes_juntada_em_avaliacao_nos_meus_setores.exists():
            for solicitacao_juntada_documento in solicitacoes_juntada_em_avaliacao_nos_meus_setores:
                if solicitacao_juntada_documento.documento == documento and solicitacao_juntada_documento.pode_deferir_documento(user):
                    return True

    return False


def usuario_deve_ter_acesso_a_documento_restrito_atraves_de_processo(user, documento):
    '''
    Este método verifica se o usuário pode ter acesso a determinado documento restrito. De maneira resumida, caso o
    documento em questão tenha vínculo ativo com algum processo em que o usuário é interessado ou que o processo
    está atualmente em algum de seus setores, então o acesso ao documento será permitido.

    :param user: usuário que deseja acessar o documento
    :param documento: documento restrito para o qual se deseja ter acesso.
    :return: True caso o usuário deva ter acesso ao documento, False caso contrário.
    '''

    pessoa_fisica = user.get_profile()

    if documento.eh_restrito and app_processo_eletronico_estah_instalada() and pessoa_fisica:
        processos_com_vinculo_ativo_com_documento = get_processos_vinculados_ao_documento(documento=documento, exibir_somente_processos_nos_quais_documento_nao_foi_removido=True)

        if processos_com_vinculo_ativo_com_documento:
            Tramite = apps.get_model("processo_eletronico", "Tramite")

            # Setores pelos quais o usuário pode tramitar processos.
            setores_usuario = Tramite.get_todos_setores(user)

            q_processos_em_que_usuario_eh_interessado = Q(interessados=user.get_profile())
            q_processos_que_transitam_atualmente_por_setores_usuario = (
                (Q(setor_criacao__in=setores_usuario) & Q(ultimo_tramite__isnull=True))
                | (Q(ultimo_tramite__remetente_setor__in=setores_usuario) & Q(ultimo_tramite__data_hora_recebimento__isnull=True))
                | (Q(ultimo_tramite__destinatario_setor__in=setores_usuario) & Q(ultimo_tramite__data_hora_recebimento__isnull=False))
            )
            # TODO: Rever isso com Hugo (segundo o Git a alteração foi feita por ele em 21/09/2019) para entender o objetivo
            # desta variável, pois 3 signitica público e não privado. Além disso, esta condicional não está tendo efeito
            # prático uma vez que a condicional principal deste método é o documento ser restrito.
            predicate_privados = Q(nivel_acesso=3) & (Q(usuario_gerador=user) | Q(tramites__destinatario_pessoa=pessoa_fisica))

            processos_que_autorizam_usuario_a_acessar_documento = processos_com_vinculo_ativo_com_documento.filter(
                q_processos_em_que_usuario_eh_interessado | q_processos_que_transitam_atualmente_por_setores_usuario | predicate_privados
            )
            if processos_que_autorizam_usuario_a_acessar_documento.exists():
                return True
    return False


def eh_auditor(user):
    perfis = ['Auditor']
    return user.groups.filter(name__in=perfis).exists()


def eh_auditor_chefe(user):
    perfis = ['Auditor Sistêmico']
    return eh_auditor(user) and user.groups.filter(name__in=perfis).exists()


def eh_procurador(user):
    perfis = ['Procurador']
    return user.groups.filter(name__in=perfis).exists()


def auditoria_deve_ter_acesso_ao_documento(user, documento):
    if eh_auditor(user):
        eh_do_meu_setor = documento.setor_dono == get_setor(user)
        return not eh_do_meu_setor
    return False


def procuradoria_deve_ter_acesso_ao_documento(user, documento):
    if eh_procurador(user):
        eh_da_procuradoria = documento.setor_dono == get_setor_procuradoria()
        return not eh_da_procuradoria
    return False


def acesso_ao_documento_em_funcao_cargo(user, documento):
    status = [DocumentoStatus.STATUS_ASSINADO, DocumentoStatus.STATUS_FINALIZADO, DocumentoStatus.STATUS_CANCELADO]
    if documento.eh_documento_texto and documento.status not in status:
        return False
    #
    acesso_auditoria = auditoria_deve_ter_acesso_ao_documento(user, documento)
    acesso_procuradoria = procuradoria_deve_ter_acesso_ao_documento(user, documento)
    return acesso_auditoria or acesso_procuradoria

# TODO: Depois de esclarecida a dúvida com Hugo referente ao TODO no método usuario_deve_ter_acesso_a_documento_restrito_atraves_de_processo,
# acredito ser possível fazer um refactory para simplificar os dois métodos, uma vez que eles tem muitas coisas em comum.


def usuario_deve_ter_acesso_a_documento_publico_e_cancelado_atraves_de_processo(user, documento):
    '''
    Este método verifica se o usuário pode ter acesso a determinado documento público e cancelado. De maneira resumida,
    caso o documento em questão tenha vínculo ativo com algum processo em que o usuário é interessado ou que o processo
    está atualmente em algum de seus setores, então o acesso ao documento será permitido.

    :param user: usuário que deseja acessar o documento
    :param documento: documento restrito para o qual se deseja ter acesso.
    :return: True caso o usuário deva ter acesso ao documento, False caso contrário.
    '''

    pessoa_fisica = user.get_profile()

    if documento.eh_publico and documento.estah_cancelado and app_processo_eletronico_estah_instalada() and pessoa_fisica:
        processos_com_vinculo_ativo_com_documento = get_processos_vinculados_ao_documento(documento=documento)

        if processos_com_vinculo_ativo_com_documento:
            Tramite = apps.get_model("processo_eletronico", "Tramite")

            # Setores pelos quais o usuário pode tramitar processos.
            setores_usuario = Tramite.get_todos_setores(user)

            q_processos_em_que_usuario_eh_interessado = Q(interessados=user.get_profile())
            q_processos_que_transitam_atualmente_por_setores_usuario = (
                (Q(setor_criacao__in=setores_usuario) & Q(ultimo_tramite__isnull=True))
                | (Q(ultimo_tramite__remetente_setor__in=setores_usuario) & Q(ultimo_tramite__data_hora_recebimento__isnull=True))
                | (Q(ultimo_tramite__destinatario_setor__in=setores_usuario) & Q(ultimo_tramite__data_hora_recebimento__isnull=False))
            )

            processos_que_autorizam_usuario_a_acessar_documento = processos_com_vinculo_ativo_com_documento.filter(
                q_processos_em_que_usuario_eh_interessado | q_processos_que_transitam_atualmente_por_setores_usuario
            )
            if processos_que_autorizam_usuario_a_acessar_documento.exists():
                return True
    return False


def get_processos_vinculados_ao_documento(documento, exibir_somente_processos_nos_quais_documento_nao_foi_removido=False):
    '''
    Este método retorna todos os processos aos quais determinado Documento (DocumentoTexto ou DocumentoDigitalizado)
    possua vínculo.

    :param documento: Documento
    :param exibir_somente_processos_nos_quais_documento_nao_foi_removido: Caso queira exibir somente os processos nos
    quais o documento possui vínculo ativo.

    :return: Caso a aplicação "Processo Eletrônico" esteja instalada e haja processos nos quais o documento possuí vínculo,
    será retornado um QuerySet de Processos. Caso contrário, None.
    '''

    if app_processo_eletronico_estah_instalada():
        documentoprocesso = None
        if hasattr(documento, 'documentotextoprocesso_set'):
            documentoprocesso = documento.documentotextoprocesso_set
        elif hasattr(documento, 'documentodigitalizadoprocesso_set'):
            documentoprocesso = documento.documentodigitalizadoprocesso_set

        if documentoprocesso:
            if exibir_somente_processos_nos_quais_documento_nao_foi_removido:
                documentoprocesso = documentoprocesso.filter(data_hora_remocao__isnull=True)
            else:
                documentoprocesso = documentoprocesso.all()

            processo_ids = documentoprocesso.values_list('processo_id', flat=True)
            Processo = apps.get_model("processo_eletronico", "Processo")
            processos = Processo.objects.filter(id__in=processo_ids)
            return processos

    return None


def gerar_hash(conteudo, use_sha256=False):
    if use_sha256:
        return hashlib.sha256(str(conteudo).encode('utf-8')).hexdigest()
    return hashlib.sha512(str(conteudo).encode('utf-8')).hexdigest()


def file_upload_to(instance, filename):
    tipo = f'{instance.tipo}'.lower()
    setor = f'{instance.setor_dono}'.lower()
    path = f'{PRIVATE_ROOT_DIR}/{setor}/{tipo}'
    ext = filename.split('.')[-1]
    # get filename
    if instance.pk:
        filename = f'{instance.pk}.{ext}'
    else:
        # set filename as random string
        filename = f'{uuid4().hex}.{ext}'
        # return the whole path to the file
    return os.path.join(path, filename)


def processar_template_ckeditor(texto, variaveis):
    # O "mark_safe" foi necessário por conta dos documentos legados que foram otimizados. No caso desses documentos,
    # as variáveis ao invés de conter um conteúdo de texto, conterão html. Sem isso, a engine de template do Django irá
    # remover todas as marcações html (< >).
    if variaveis:
        for key in variaveis:
            variaveis[key] = mark_safe(variaveis[key])

    template = Template(texto)
    return template.render(Context(variaveis))


def get_variaveis(documento_identificador, estagio_processamento_variavel=None, to_dict=True, usuario=None, setor_dono=None):
    usuario = usuario or tl.get_user()
    setor = setor_dono or get_setor(usuario)
    uo = setor.uo

    sigla_reitoria = get_sigla_reitoria()

    reitoria = UnidadeOrganizacional.objects.suap().get(sigla=sigla_reitoria)

    hoje = datetime.date.today()
    meses = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho', 'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']

    variaveis = (
        # TODO: Essa variável usuário logado tem que ser revista já que o processamento do documento
        # só será feito antes da assinatura balizadora.
        ('usuario_nome', usuario.get_profile().nome, 'Nome do usuário logado', EstagioProcessamentoVariavel.CRIACAO_DOCUMENTO),
        ('documento_data_emissao', format_(hoje), 'Data de emissão do documento', EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO),
        (
            'documento_data_emissao_por_extenso',
            f'{hoje.day} de {meses[hoje.month - 1]} de {hoje.year}',
            'Data de emissão do documento por extenso',
            EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO,
        ),
        (
            'documento_data_emissao_por_extenso_maiuscula',
            f'{hoje.day} de {meses[hoje.month - 1]} de {hoje.year}'.upper(),
            'Data de emissão do documento por extenso',
            EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO,
        ),
        (
            'reitor_nome',
            reitoria.get_diretor_geral()[0].nome if reitoria.get_diretor_geral() else 'Sem Reitor',
            'Nome do reitor',
            EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO,
        ),
        ('setor_nome', setor.nome, 'Nome do setor do documento', EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO),
        ('setor_sigla', setor.sigla, 'Sigla do setor do documento', EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO),
        ('setor_chefe', str(setor.chefes[0]) if setor.chefes else 'Sem Chefe', 'Chefe do setor do documento', EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO),
        ('setor_telefones', setor.telefones() if setor.telefones() else 'Sem Telefones cadastrados', 'Telefones do setor', EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO),
        ('documento_identificador', documento_identificador, 'Identificador do documento', EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO),
        ('instituicao_nome', Configuracao.get_valor_por_chave('comum', 'instituicao'), 'Nome da instituição', EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO),
        ('instituicao_sigla', Configuracao.get_valor_por_chave('comum', 'instituicao_sigla'), 'Sigla da instituição', EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO),
        ('instituicao_sitio_internet', settings.SITE_URL, 'Site da instituição', EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO),
        ('unidade_sigla', setor.uo.sigla, 'Sigla do campus do usuário logado', EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO),
        ('unidade_nome', setor.uo.nome, 'Nome do campus do usuário logado', EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO),
        ('unidade_telefone', uo.setor.telefones(sem_ramal=True), 'Telefone do campus do usuário logado', EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO),
        (
            'unidade_endereco',
            f'{uo.endereco}, {uo.numero}, {uo.bairro}, {uo.municipio}, CEP {uo.cep}',
            'Endereço do campus do usuário logado',
            EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO,
        ),
        (
            'unidade_diretor_nome',
            uo.get_diretor_geral()[0].nome if uo.get_diretor_geral() else 'Sem Diretor Geral',
            'Nome do diretor do campus do usuário logado',
            EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO,
        ),
    )

    if not to_dict:
        return variaveis

    variaveis_as_dict = dict()
    for chave, valor, descricao, estagio_proc_var in variaveis:
        if estagio_processamento_variavel is None or estagio_proc_var == estagio_processamento_variavel:
            variaveis_as_dict[chave] = valor
        else:
            # Esse artifício foi usado para poder manter no template as variáveis que não façam parte do estágio de
            # processamento, caso tenha sido especificado algum.
            variaveis_as_dict[chave] = f'{{{{ {chave} }}}}'
    return variaveis_as_dict


def get_previous(obj, date=None):
    """
        objects have a revision attribute, which has two methods, 'get_next_by_date_created', and
        'get_previous_by_date_created', which you could use to traverse version history either way.
        version.revision.get_previous_by_date_created()

        Returns the latest version of an object prior to the given date.
        [...] each version has a revision attribute for the corresponding revision and can be used to do the following:
            1. get the user that made the change through the revision.user attribute
            2. get the date of the change through the revision.date_created attribute
            3. get the values of the object fields as they were in this revision using the field_dict attribute
            4. get a model instance as it was on that revision using the object_version.object attribute
                revert to that previous version of that object using the revert() method
            5. So try changing your return version.get_object() line to  return version.object_version.object!

    """
    versions = Version.objects.get_for_object(obj)
    versions = versions.filter(revision__date_created__lt=date)

    try:
        version = versions[0]
    except IndexError:
        raise Version.DoesNotExist
    else:
        return version


def revert_to_previous_instance(obj, date=None):
    previous_instance = get_previous(obj, date)
    previous_instance.revert()


def get_setores_compartilhados(user, nivel_permissao):
    from processo_eletronico.utils import setores_que_tenho_poder_de_chefe
    lista_setores_que_tenho_poder_de_chefe = Setor.objects.filter(id__in=setores_que_tenho_poder_de_chefe(user))
    compartilhamento_setor_usuario = [Q(compartilhamentosetorpessoa__pessoa_permitida=user.get_profile()), Q(compartilhamentosetorpessoa__nivel_permissao=nivel_permissao)]
    setores_compartilhados_com_usuario = Setor.objects.filter(reduce(operator.and_, compartilhamento_setor_usuario))
    return (setores_compartilhados_com_usuario | lista_setores_que_tenho_poder_de_chefe).distinct()


def convert_to_pdfA(input_pdf):
    gs = getattr(settings, 'GHOSTSCRIPT_CMD', None)
    with tempfile.NamedTemporaryFile(suffix=".pdf") as fp:
        fp.write(input_pdf)
        fp.seek(0)
        outfile = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
        directory = tempfile.mkdtemp()

        cmd = [
            gs,
            "-dPDFA=1",
            "-dBATCH",
            "-dNOPAUSE",
            "-dNOOUTERSAVE",
            "-dPDFSETTINGS=/printer",
            "-dCompatibilityLevel=1.4",
            "-dPDFACompatibilityPolicy=1",
            "-sDEVICE=pdfwrite",
            "-dQUIET",
            "-sOutputFile=" + outfile.name,
            fp.name,
        ]

        try:
            dict_env = {'TMPDIR': settings.TEMP_DIR, 'TEMP': settings.TEMP_DIR}
            subprocess.call(cmd, stderr=sys.stdout, cwd=directory, env=dict_env)
            output_pdf = outfile.read()
            outfile.close()  # deletes the file
            return output_pdf
        except OSError:
            sys.exit(f"Error executing Ghostscript ({gs}). Is it in your PATH?")
        except Exception:
            print("Error while running Ghostscript subprocess. Traceback:")
            print(f"Traceback:\n {traceback.format_exc()}")


def get_documento_url(documento):
    return f'{settings.SITE_URL}{documento.get_absolute_url()}'


class Notificar:
    @staticmethod
    def solicitacao_assinatura(solicitacao, documento, gerar_excecao_erro=False):
        titulo = '[SUAP] Documento Eletrônico: Solicitação de Assinatura'
        texto = []
        texto.append('<h1>Documentos Eletrônicos</h1>')
        texto.append('<h2>Solicitação de Assinatura de Documento</h2>')
        texto.append(f'<p>Prezado(a) {solicitacao.nome}, uma solicitação de assinatura foi adicionada para o documento: {documento.assunto}</p>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        texto.append(f'<dt>Documento criado por:</dt><dd>{documento.usuario_criacao}</dd>')
        texto.append('<dt>Criado em:</dt><dd>{}</dd>'.format(documento.data_criacao.strftime("%d/%m/%Y")))
        texto.append(f'<dt>Setor:</dt><dd>{documento.setor_dono}</dd>')
        texto.append('</dl>')
        texto.append('<h3>Tutoriais</h3>')
        texto.append('<ul>')
        texto.append('<li><a href="https://portal.suap.ifrn.edu.br/tutoriais/primeiro-acesso/">Primeiro Acesso</a</li>')
        texto.append('<li><a href="https://portal.suap.ifrn.edu.br/tutoriais/assinando-um-documento-eletronico/">Assinando um Documento Eletrônico</a></li>')
        texto.append('</ul>')
        texto.append('<p></p>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(get_documento_url(documento)))
        vinculo = []
        vinculo.append(solicitacao.get_vinculo())
        try:
            if vinculo:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, vinculo, objeto=documento)
        except Exception as e:
            if gerar_excecao_erro:
                raise e

    @staticmethod
    def remocao_solicitacao_assinatura(solicitacao, documento, gerar_excecao_erro=False):
        titulo = '[SUAP] Documento Eletrônico: Remoção de Solicitação de Assinatura'
        texto = []
        texto.append('<h1>Documentos Eletrônicos</h1>')
        texto.append('<h2>Remoção da Solicitação de Assinatura de Documento</h2>')
        texto.append(f'<p>Prezado(a) {solicitacao.solicitado.nome}, uma solicitação de assinatura foi removida do documento: {documento.assunto}</p>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        texto.append(f'<dt>Documento criado por:</dt><dd>{documento.usuario_criacao}</dd>')
        texto.append('<dt>Criado em:</dt><dd>{}</dd>'.format(documento.data_criacao.strftime("%d/%m/%Y")))
        texto.append(f'<dt>Setor:</dt><dd>{documento.setor_dono}</dd>')
        texto.append('</dl>')
        solicitado = solicitacao.solicitado.get_vinculo()
        try:
            if solicitado:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [solicitado], objeto=documento)
        except Exception as e:
            if gerar_excecao_erro:
                raise e

    @staticmethod
    def solicitacao_assinatura_condicionantes(solicitacoes_condicionantes, documento, gerar_excecao_erro=False):
        for solicitacao in solicitacoes_condicionantes:
            titulo = '[SUAP] Documento Eletrônico: Solicitação de Assinatura'
            texto = []
            texto.append('<h1>Documentos Eletrônicos</h1>')
            texto.append('<h2>Solicitação de Assinatura de Documento</h2>')
            texto.append(f'<p>Prezado(a) {solicitacao.solicitado.nome}, uma solicitação de assinatura foi adicionada para o documento: {documento.assunto}</p>')
            texto.append('<h3>Dados Gerais</h3>')
            texto.append('<dl>')
            texto.append(f'<dt>Documento criado por:</dt><dd>{documento.usuario_criacao}</dd>')
            texto.append('<dt>Criado em:</dt><dd>{}</dd>'.format(documento.data_criacao.strftime("%d/%m/%Y")))
            texto.append(f'<dt>Setor:</dt><dd>{documento.setor_dono}</dd>')
            texto.append('</dl>')
            texto.append('<h3>Tutoriais</h3>')
            texto.append('<ul>')
            texto.append('<li><a href="https://portal.suap.ifrn.edu.br/tutoriais/primeiro-acesso/">Primeiro Acesso</a</li>')
            texto.append('<li><a href="https://portal.suap.ifrn.edu.br/tutoriais/assinando-um-documento-eletronico/">Assinando um Documento Eletrônico</a></li>')
            texto.append('</ul>')
            texto.append('<p></p>')
            texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(get_documento_url(documento)))
            solicitado = solicitacao.solicitado.get_vinculo()
            try:
                if solicitado:
                    send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [solicitado], objeto=documento)
            except Exception as e:
                if gerar_excecao_erro:
                    raise e

    @staticmethod
    def solicitacao_revisao(revisor, documento, gerar_excecao_erro=False):
        titulo = '[SUAP] Documento Eletrônico: Solicitação de Revisão de Documento'
        texto = []
        texto.append('<h1>Documentos Eletrônicos</h1>')
        texto.append('<h2>Solicitação de Revisão de Documento</h2>')
        texto.append(f'<p>Prezado(a) {revisor.nome}, uma solicitação de revisão foi adicionada para o documento: {documento.assunto}</p>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        texto.append(f'<dt>Documento criado por:</dt><dd>{documento.usuario_criacao}</dd>')
        texto.append('<dt>Criado em:</dt><dd>{}</dd>'.format(documento.data_criacao.strftime("%d/%m/%Y")))
        texto.append(f'<dt>Setor:</dt><dd>{documento.setor_dono}</dd>')
        texto.append('</dl>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(get_documento_url(documento)))
        revisor = revisor.get_vinculo()
        try:
            if revisor:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [revisor], objeto=documento)
        except Exception as e:
            if gerar_excecao_erro:
                raise e

    @staticmethod
    def cancelamento_revisao(revisor, documento, gerar_excecao_erro=False):
        titulo = '[SUAP] Documento Eletrônico: Cancelamento da Solicitação de Revisão de Documento'
        texto = []
        texto.append('<h1>Documentos Eletrônicos</h1>')
        texto.append('<h2>Cancelamento da Solicitação de Revisão de Documento</h2>')
        texto.append(f'<p>Prezado(a) {revisor.nome}, uma solicitação de revisão foi cancelada para o documento: {documento.assunto}</p>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        texto.append(f'<dt>Documento criado por:</dt><dd>{documento.usuario_criacao}</dd>')
        texto.append('<dt>Criado em:</dt><dd>{}</dd>'.format(documento.data_criacao.strftime("%d/%m/%Y")))
        texto.append(f'<dt>Setor:</dt><dd>{documento.setor_dono}</dd>')
        texto.append('</dl>')
        revisor = revisor.pessoafisica.get_vinculo()
        try:
            if revisor:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [revisor], objeto=documento)
        except Exception as e:
            if gerar_excecao_erro:
                raise e

    @staticmethod
    def add_compartilhamento_de_documento(obj, gerar_excecao_erro=False):
        """
        :param obj: instance of CompartilhamentoDocumentoPessoa
        :param gerar_excecao_erro:
        :return:
        """
        from .models import NivelPermissao

        titulo = '[SUAP] Documento Eletrônico: Novo Documento Compartilhado'
        texto = []
        texto.append('<h1>Documentos Eletrônicos</h1>')
        texto.append('<h2>Compartilhamento de Documento</h2>')
        texto.append(f'<p>Prezado(a) {obj.pessoa_permitida.nome}, o documento {obj.documento.assunto} foi compartilhado com você.</p>')
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        texto.append(f'<dt>Documento criado por:</dt><dd>{obj.documento.usuario_criacao}</dd>')
        texto.append('<dt>Criado em:</dt><dd>{}</dd>'.format(obj.documento.data_criacao.strftime("%d/%m/%Y")))
        texto.append(f'<dt>Setor:</dt><dd>{obj.documento.setor_dono}</dd>')
        texto.append(f'<dt>Você tem permissão de:</dt><dd>{dict(NivelPermissao.CHOICES)[obj.nivel_permissao]}</dd>')
        texto.append('</dl>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(get_documento_url(obj.documento)))
        pessoa_permitida = obj.pessoa_permitida.get_vinculo()
        try:
            if pessoa_permitida:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [pessoa_permitida], objeto=obj.documento)
        except Exception as e:
            if gerar_excecao_erro:
                raise e

    @staticmethod
    def remove_compartilhamento_de_documento(obj, gerar_excecao_erro=False):
        """

        :param obj: instance of CompartilhamentoDocumentoPessoa
        :param gerar_excecao_erro:
        :return:
        """
        from .models import NivelPermissao

        titulo = '[SUAP] Documento Eletrônico: Remoção de Compartilhamento de Documento'
        texto = []
        texto.append('<h1>Documentos Eletrônicos</h1>')
        texto.append('<h2>Remoção de Compartilhamento de Documento</h2>')
        texto.append(
            '<p>Prezado(a) {}, o compartilhamento de {} no documento {} foi removido para você.</p>'.format(
                obj.pessoa_permitida.nome, dict(NivelPermissao.CHOICES)[obj.nivel_permissao], obj.documento.assunto
            )
        )
        texto.append('<h3>Dados Gerais</h3>')
        texto.append('<dl>')
        texto.append(f'<dt>Documento criado por:</dt><dd>{obj.documento.usuario_criacao}</dd>')
        texto.append('<dt>Criado em:</dt><dd>{}</dd>'.format(obj.documento.data_criacao.strftime("%d/%m/%Y")))
        texto.append(f'<dt>Setor:</dt><dd>{obj.documento.setor_dono}</dd>')
        texto.append('</dl>')
        texto.append('<p>Para mais informações, acesse: <a href="{0}">{0}</a></p>'.format(get_documento_url(obj.documento)))
        pessoa_permitida = obj.pessoa_permitida.pessoafisica.get_vinculo()
        try:
            if pessoa_permitida:
                send_notification(titulo, ''.join(texto), settings.DEFAULT_FROM_EMAIL, [pessoa_permitida], objeto=obj.documento)
        except Exception as e:
            if gerar_excecao_erro:
                raise e


def processar_template_documentos_anexados(anexos):
    template = get_template('documento_eletronico/templates/documento_eletronico/lista_anexos_do_documento.html')
    return mark_safe(template.render(anexos))


def anonimizar_identificador_unico_matricula_aluno(matricula):
    from math import ceil, floor

    qtd_anonim = round(len(matricula) / 2) - 1
    anonim_f = (qtd_anonim / 2) - 1
    anonim_i = qtd_anonim - anonim_f
    anonim_f = ceil(anonim_f)
    anonim_i = floor(anonim_i)

    return ('*' * int(anonim_i)) + matricula[int(anonim_i):-int(anonim_f)] + ('*' * int(anonim_f))


def anonimizar_identificador_unico_matricula_servidor(matricula):
    matricula = matricula.zfill(7)
    matricula = matricula[0:3] + '*' * 4
    return matricula


def random_with_N_digits(n):
    range_start = 10 ** (n - 1)
    range_end = (10 ** n) - 1
    return randint(range_start, range_end)


'''
#=====# DO THE ACTUAL CONVERSION #=====#
echo "  Compressing PDF & embedding fonts..."
run gs $MSGOPTS \
    -dBATCH -dNOPAUSE -dNOOUTERSAVE \
    -dCompatibilityLevel=1.4 \
    -dEmbedAllFonts=true -dSubsetFonts=true \
    -dCompressFonts=true -dCompressPages=true \
    -dUseCIEColor -sColorConversionStrategy=RGB \
    -dDownsampleMonoImages=false -dDownsampleGrayImages=false -dDownsampleColorImages=false \
    -dAutoFilterColorImages=false -dAutoFilterGrayImages=false \
    -sDEVICE=pdfwrite \
    -sOutputFile=$TMPFILE $INPUT
echo "  Converting to PDF/A-1B..."
run gs $MSGOPTS \
    -dPDFA=1 -dBATCH -dNOPAUSE -dNOOUTERSAVE \
    $QUALITYOPTS \
    -dCompatibilityLevel=1.4 -dPDFACompatibilityPolicy=1 \
    -dUseCIEColor -sProcessColorModel=DeviceRGB -sColorConversionStrategy=RGB \
    -sOutputICCProfile=$ICCTMPFILE \
    -sDEVICE=pdfwrite \
    -sOutputFile=$OUTPUT $TMPFILE $PSTMPFILE
'''
