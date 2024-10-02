import json
from datetime import datetime

from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.serializers.json import DjangoJSONEncoder
from django.dispatch import Signal, receiver
from django.http import HttpResponseBadRequest, HttpResponse, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, redirect

from arquivo.forms import IdentificarArquivoForm, ValidarArquivoForm, FilterArquivosPorCampusForm, ArquivoServidorForm, \
    ArquivoUploadForm, ProtocolarArquivoForm
from arquivo.models import Arquivo, PRIVATE_ROOT_DIR, Funcao
from djtools.storages import is_remote_storage, LocalUploadBackend, AWSUploadBackend
from djtools.utils import render, rtr, httprr, permission_required, is_ajax
from djtools.utils.response import render_to_string
from rh.models import Servidor
from rh.views import rh_servidor_view_tab


@rtr()
def arquivos_servidor(request, servidor_matricula):
    is_rh = request.user.has_perm('rh.change_servidor')
    try:
        servidor = Servidor.objects.get(matricula=servidor_matricula)
    except Exception:
        return HttpResponseBadRequest('Servidor não existe!')
    verificacao_propria = request.user == servidor.user
    title = 'Arquivos Servidor: {}'.format(servidor)
    if verificacao_propria or is_rh:
        arquivos_servidor = Arquivo.get_arquivos_por_instancia(servidor).filter(status__in=[1, 2])
    return locals()


@rtr()
@permission_required('arquivo.pode_identificar_arquivo, arquivo.pode_validar_arquivo')
def arquivos_pendentes_servidor(request, servidor_matricula):
    servidor = get_object_or_404(Servidor, matricula=servidor_matricula)
    title = 'Arquivos Pendentes do Servidor: {}'.format(servidor)
    arquivos_pendentes_identificar_servidor = Arquivo.get_arquivos_por_instancia(servidor).filter(status=0)
    arquivos_pendentes_validacao_servidor = Arquivo.get_arquivos_por_instancia(servidor).filter(status=1)
    arquivos_rejeitados_servidor = Arquivo.get_arquivos_por_instancia(servidor).filter(status=3)
    arquivos_validados_servidor = Arquivo.get_arquivos_por_instancia(servidor).filter(status=2)
    return locals()


@rtr()
@permission_required('arquivo.pode_identificar_arquivo')
def arquivos_pendentes_servidor_identificar(request, servidor_matricula, arquivo_id):
    is_rh = request.user.has_perm('rh.change_servidor')
    try:
        servidor = Servidor.objects.get(matricula=servidor_matricula)
    except Exception:
        return HttpResponseBadRequest('Servidor não existe!')
    title = 'Identificar Arquivo: {}'.format(servidor)
    arquivo_pendente = Arquivo.objects.get(encrypted_pk=arquivo_id)
    form = IdentificarArquivoForm(request.POST or None, instance=arquivo_pendente)
    if form.is_valid():
        arquivo_pendente.status = int(form.cleaned_data['acao'])
        # o arquivo foi rejeitado, agora basta alterar o status do arquivo
        if form.cleaned_data['acao'] == '3':
            arquivo_pendente.justificativa_rejeicao = form.cleaned_data['justificativa_rejeicao']
            form.save()
            return httprr('/arquivo/arquivos_pendentes_servidor/{}'.format(servidor_matricula), 'Arquivo Rejeitado com sucesso!')

        arquivo_pendente.tipo_arquivo = form.cleaned_data['tipo_arquivo']
        arquivo_pendente.identificado_por = request.user
        arquivo_pendente.identificado_em = datetime.now()
        form.save()
        return httprr('/arquivo/arquivos_pendentes_servidor/{}'.format(servidor_matricula), 'Arquivo Identificado com sucesso!')
    return locals()


@rtr()
@permission_required('arquivo.pode_validar_arquivo')
def arquivos_pendentes_servidor_validar(request, servidor_matricula, arquivo_id):
    is_rh = request.user.has_perm('rh.change_servidor')
    servidor = None
    try:
        servidor = Servidor.objects.get(matricula=servidor_matricula)
    except Exception:
        return HttpResponseBadRequest('Servidor não existe!')
    title = 'Validar Arquivo: {}'.format(servidor)
    arquivo_pendente_validacao = Arquivo.objects.get(encrypted_pk=arquivo_id)
    form = ValidarArquivoForm(request.POST or None, instance=arquivo_pendente_validacao)
    if form.is_valid():
        arquivo_pendente_validacao.status = int(form.cleaned_data['acao'])

        if arquivo_pendente_validacao.status == 3:
            arquivo_pendente_validacao.tipo_arquivo = None
            arquivo_pendente_validacao.validado_por = None
            arquivo_pendente_validacao.validado_em = None
            arquivo_pendente_validacao.identificado_por = None
            arquivo_pendente_validacao.identificado_em = None
            arquivo_pendente_validacao.justificativa_rejeicao = form.cleaned_data['justificativa_rejeicao']
            form.save()
            return httprr('/arquivo/arquivos_pendentes_servidor/{}'.format(servidor_matricula), 'Arquivo Rejeitado com sucesso!')
        arquivo_pendente_validacao.validado_por = request.user
        arquivo_pendente_validacao.validado_em = datetime.now()
        form.save()
        return httprr('/arquivo/arquivos_pendentes_servidor/{}'.format(servidor_matricula), 'Arquivo Identificado com sucesso!')
    return locals()


@rtr()
@permission_required(
    'arquivo.pode_fazer_upload_arquivo, \
                     arquivo.pode_identificar_arquivo, \
                     arquivo.pode_validar_arquivo'
)
def arquivos_pendentes_servidor_excluir(request, servidor_matricula, arquivo_id):
    redirect_to = request.META.get('HTTP_REFERER', '..')

    arquivo_pendente = Arquivo.objects.get(encrypted_pk=arquivo_id)
    if arquivo_pendente.status == 0:  # o arquivo esta pendente
        arquivo_pendente.delete()
        return httprr(redirect_to, 'Arquivo removido com sucesso!')
    else:
        return httprr(redirect_to, 'O arquivo esta bloqueado para remoção!', 'error')


@rtr()
@permission_required('arquivo.pode_identificar_arquivo, arquivo.pode_validar_arquivo')
def arquivos_rejeitados(request):
    is_rh = request.user.has_perm('rh.change_servidor')
    title = 'Arquivos Rejeitados'
    tipo_dono = ContentType.objects.get_for_model(Servidor)
    ids = {}
    servidores = []
    form = FilterArquivosPorCampusForm(request.POST)
    args = dict(content_type=tipo_dono, status=3)

    if form.is_valid():
        if form.cleaned_data['campus']:
            args['object_id__in'] = Servidor.objects.filter(setor__uo=form.cleaned_data['campus']).values_list('id', flat=True)
    for arquivo in Arquivo.objects.filter(**args):
        if not ids.get(arquivo.object_id):
            ids[arquivo.object_id] = True
            servidores.append(Servidor.objects.get(id=arquivo.object_id))
    return locals()


@rtr()
@permission_required('arquivo.pode_identificar_arquivo, arquivo.pode_validar_arquivo')
def arquivos_rejeitados_servidor(request, servidor_matricula):
    is_rh = request.user.has_perm('rh.change_servidor')
    try:
        servidor = Servidor.objects.get(matricula=servidor_matricula)
    except Exception:
        return HttpResponseBadRequest('Servidor não existe!')
    title = 'Arquivos Rejeitados do Servidor: {}'.format(servidor)
    arquivos_rejeitados_servidor = Arquivo.get_arquivos_por_instancia(servidor).filter(status=3)
    return locals()


def visualizar_arquivo_pdf(request, arquivo_id):
    try:
        arquivo = Arquivo.objects.get(encrypted_pk=arquivo_id)
    except Exception:
        return httprr('..', 'Arquivo não encontrado', 'error')
    if arquivo.content_type == ContentType.objects.get_for_model(Servidor):
        try:
            servidor = Servidor.objects.get(pk=arquivo.object_id)
        except Exception:
            return HttpResponseBadRequest('Servidor não existe!')
        verificacao_propria = request.user == servidor.user
        is_rh = request.user.has_perm('rh.change_servidor')
        if verificacao_propria or is_rh:
            pdf_data = arquivo.file
            return render('viewer.html', locals())

    raise PermissionDenied('Você não tem acesso a visualização desse arquivo.')


@rtr()
@permission_required('arquivo.pode_identificar_arquivo, arquivo.pode_validar_arquivo')
def protocolar_arquivo(request, arquivo_id):
    title = 'Protocolar Arquivo'
    arquivo = Arquivo.objects.get(encrypted_pk=arquivo_id)
    form = ProtocolarArquivoForm(request.POST or None, instance=arquivo, user=request.user)
    if form.is_valid():
        form.save()
        return httprr('..')
    return locals()


@rtr()
@permission_required('arquivo.pode_identificar_arquivo, arquivo.pode_validar_arquivo')
def arquivos_pendentes(request):
    title = 'Arquivos Pendentes'
    tipo_dono = ContentType.objects.get_for_model(Servidor)
    form = FilterArquivosPorCampusForm(request.POST)
    servidores = Servidor.objects.filter(id__in=Arquivo.objects.filter(content_type=tipo_dono, status__in=[0, 1]).values_list('object_id', flat=True).distinct())
    if form.is_valid():
        campus = request.POST.get('campus')
        if campus:
            servidores = servidores.filter(setor__uo__pk=campus)

    return locals()


@rtr()
def tipos_arquivos(request):
    """
        TipoArquivo
             *
             |
             |
             *
          Processo * ---- 1 Funcao
           1  0..1
           |   |
           |___|


        criar a estrutura:

        funcao      processo            tipo
                        processo        tipo
                        processo        tipo
                            processo    tipo
                                        tipo
                                        tipo
                        processo        tipo
                    processo            tipo
                        processo        tipo
                                        tipo
    """
    title = 'Tipos de Arquivos'
    funcoes = Funcao.objects.all()
    dados_funcoes = dict()

    for funcao in funcoes:
        dados_processos = dict()
        for processo in funcao.processo_set.filter(superior__isnull=True).order_by('id'):
            dados_processos[processo] = dict()
            dados_processos[processo]['tipos_arquivos'] = processo.tipos_arquivos.all()
            if processo.processo_set.all().exists():
                dados_processos[processo]['filhos'] = dict()
                for processo_filho in processo.processo_set.all():
                    dados_processos[processo]['filhos'][processo_filho] = dict()
                    dados_processos[processo]['filhos'][processo_filho]['tipos_arquivos'] = processo_filho.tipos_arquivos.all()

        dados_funcoes[funcao] = dados_processos
    return locals()


###########################################################################################
###########################################################################################
###########################################################################################


@rtr()
def selecionar_servidor(request):
    title = 'Upload de Arquivos'
    form = ArquivoServidorForm(request.POST or None)
    if form.is_valid():
        servidor = form.cleaned_data['servidor']
        return redirect('arquivos_upload', servidor_matricula=servidor.matricula)
    return locals()


@rtr()
def arquivos_upload(request, servidor_matricula):
    title = 'Upload de Arquivos'
    servidor = Servidor.objects.get(matricula=servidor_matricula)
    arquivos_pendentes_identificar_servidor = Arquivo.get_arquivos_por_instancia(servidor).filter(status=0)
    form = ArquivoUploadForm(request=request, servidor=servidor)
    return locals()


def get_upload_directory(instance):
    object_id = instance.id
    path = '{}/{}'.format(PRIVATE_ROOT_DIR, object_id)
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
        if request.method == 'POST':
            if 'servidor' in request.GET:
                servidor_matricula = request.GET['servidor']
                servidor = get_object_or_404(Servidor, matricula=servidor_matricula)
            else:
                return HttpResponse(json.dumps({'success': False, 'status': 400}), content_type='application/json')
            # Here, we have something on request.
            # The content_type and content_length variables
            # indicates that.
            if is_ajax(request):
                # the file is stored raw in the request
                upload = request
                is_raw = True
                # Ajax upload will pass the filename in querystring
                try:
                    if 'qqfile' in request.GET:
                        filename = request.GET['qqfile']
                    else:
                        filename = request.REQUEST['qqfilename']
                #
                except KeyError:
                    return HttpResponse(json.dumps({'success': False}), content_type='application/json')

            else:
                # not an ajax upload, so it was pass via form
                is_raw = False
                if len(request.FILES) == 1:
                    upload = list(request.FILES.values())[0]
                else:
                    return HttpResponse(json.dumps({'success': False}), content_type='application/json')
                filename = upload.name
            content_type = str(request.META.get('CONTENT_TYPE', ""))
            content_length = int(request.META.get('CONTENT_LENGTH', 0))
            if content_type == "" or content_length == 0:
                return HttpResponse(json.dumps({'success': False, 'status': 400}), content_type='application/json')

            # Here, we have the filename and file size
            backend = self.get_backend()

            # creating the destination upload directory
            upload_to = get_upload_directory(servidor)
            # configuring the
            new_filename = backend.setup(upload_to, filename)
            # save the file
            success = backend.upload(upload, content_length, is_raw, *args, **kwargs)
            # callback
            uploaded_path = backend.upload_complete(*args, **kwargs)
            if success:
                arquivo_pk = create_on_upload(servidor, request.user, uploaded_path, filename)
            else:
                arquivo_pk = None
            # let Ajax Upload know whether we saved it or not
            ret_json = {'success': success, 'filename': new_filename, 'chave': arquivo_pk, 'tamanho': content_length}
            return HttpResponse(json.dumps(ret_json, cls=DjangoJSONEncoder), content_type='text/html; charset=utf-8')

        else:
            response = HttpResponseNotAllowed(['POST'])
            response.write("ERROR: Only POST allowed")
            return response


def create_on_upload(servidor, usuario, diretorio, nome_do_arquivo):
    novo_arquivo = Arquivo()
    novo_arquivo.nome = nome_do_arquivo
    novo_arquivo.objeto = servidor
    novo_arquivo.object_id = servidor.id
    novo_arquivo.upload_por = usuario
    novo_arquivo.content_type = ContentType.objects.get_for_model(servidor.__class__)
    novo_arquivo.file = diretorio
    novo_arquivo.save()
    return novo_arquivo.encrypted_pk


file_uploaded = Signal()  # providing_args=['backend', 'request']
upload_handler = FileUploader()


# View que se conecta a view rh.views.servidor
@receiver(rh_servidor_view_tab)
def servidor_view_tab_signal(sender, request, servidor, verificacao_propria, eh_chefe, **kwargs):
    pode_ver_arquivos_servidor = request.user.has_perm('rh.pode_ver_arquivos_servidor') or verificacao_propria

    if pode_ver_arquivos_servidor:
        arquivo = True
        tipo_dono = ContentType.objects.get_for_model(servidor.__class__)
        arquivos_servidor = Arquivo.objects.filter(content_type=tipo_dono, object_id=servidor.id, status__in=[1, 2])

        return render_to_string(
            template_name='arquivo/templates/servidor_view_tab.html',
            context={"lps_context": {"nome_modulo": "arquivo"}, 'servidor': servidor, 'arquivo': arquivo, 'tipo_dono': tipo_dono, 'arquivos_servidor': arquivos_servidor},
            request=request,
        )
    return False
