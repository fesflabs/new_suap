import base64

import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize
from django.apps import apps
from comum.models import Configuracao
from comum.utils import tem_permissao_informar_erro
from djtools import layout
from djtools.templatetags.filters import in_group
from djtools.utils import httprr, rtr, get_client_ip
from erros.forms import (
    ReportarErroForm,
    ComentarioErroForm,
    SituacaoErroForm,
    InteressadoErroForm, ModulosForm, AlterarURLErroForm, AnexoErroForm, AtribuirErroForm, UnificarErroForm,
    ReportarErroPorChamadoForm, BuscarErrosForm, EditarAtualizacaoErroForm,
)
from erros.models import (
    AtendenteErro,
    Erro,
    InteressadoErro, HistoricoComentarioErro,
)
from erros.utils import (
    ferramentas_configuradas, get_apps_disponiveis, get_areas,
    popular_links_gitlab, get_custom_view_name_from_url, criar_issue_gitlab, get_hostname
)


@layout.quadro('Erros', icone='bug', pode_esconder=True)
def index_quadros(quadro, request):
    erros = Erro.objects.filter(interessadoerro__vinculo=request.user.get_vinculo()).exclude(situacao__in=Erro.SITUACOES_FINAIS)
    if erros.exists():
        quadro.add_item(
            layout.ItemContador(
                titulo=f'Erro{pluralize(erros.count())}',
                subtitulo='Aguardando resolução',
                qtd=erros.count(),
                url='erros/erros/?sou_interessado=sim',
            )
        )

    if in_group(request.user, 'Desenvolvedor'):
        erros = Erro.objects.filter(atendente_atual=request.user.get_vinculo()).exclude(situacao__in=Erro.SITUACOES_FINAIS)
        if erros.exists():
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Erro{pluralize(erros.count())}',
                    subtitulo=f'Atribuído{pluralize(erros.count())} a mim',
                    qtd=erros.count(),
                    url=f'erros/erros/?atendente_atual={request.user.get_vinculo().pk}',
                )
            )

    if in_group(request.user, 'Recebedor de Demandas', ignore_if_superuser=False):
        erros_sem_atribuicao = Erro.objects.filter(atendente_atual__isnull=True, url_sentry__isnull=True, gitlab_issue_url__isnull=True).exclude(situacao__in=Erro.SITUACOES_FINAIS)
        if erros_sem_atribuicao.exists():
            quadro.add_item(
                layout.ItemContador(
                    titulo='Erro{s} pendente{s}'.format(s=pluralize(erros_sem_atribuicao.count())),
                    subtitulo='Sem atribuição',
                    qtd=erros_sem_atribuicao.count(),
                    url='erros/erros/?sem_atribuicao=sim',
                )
            )

    return quadro


@rtr()
@login_required
def reportar_erro_500(request):
    try:  # esta tela não pode quebrar
        descricao = request.POST.get('descricao')
        event_id = request.POST.get('event_id')
        full_url = request.POST.get('full_url')
        view_name = get_custom_view_name_from_url(full_url)

        sentry_token = Configuracao.get_valor_por_chave('comum', 'sentry_token')
        sentry_url = Configuracao.get_valor_por_chave('comum', 'sentry_url')
        sentry_organization = Configuracao.get_valor_por_chave('comum', 'sentry_organization')
        sentry_project = Configuracao.get_valor_por_chave('comum', 'sentry_project')

        if all(
            [tem_permissao_informar_erro(request), descricao, full_url, view_name]
        ):
            from erros.models import Erro
            try:
                headers_api = {'Authorization': f'Bearer {sentry_token}'}
                data = {
                    "event_id": event_id,
                    "name": request.user.get_profile().nome,
                    "email": request.user.get_profile().email,
                    "comments": descricao
                }
                sentry_issue_url = f'{sentry_url}/api/0/projects/{sentry_organization}/{sentry_project}/user-feedback/'
                sentry_issue_id = requests.post(sentry_issue_url, headers=headers_api, data=data).json()['issue']['id']
                sentry_event_url = f'{sentry_url}/organizations/sentry/issues/{sentry_issue_id}/'
            except Exception:
                sentry_issue_id = None
                sentry_event_url = None

            obj = Erro.objects.filter(sentry_issue_id__isnull=False, sentry_issue_id=sentry_issue_id).exclude(situacao__in=Erro.SITUACOES_FINAIS).first()
            if obj:
                obj.gerenciar_interessado(request.user.get_vinculo())
                obj.comentar(request.user.get_vinculo(), descricao, tipo=HistoricoComentarioErro.TIPO_COMENTARIO)
                messages.success(request, 'Comentário adicionado ao erro com sucesso.')
            else:
                obj = Erro()
                obj.informante = request.user.get_vinculo()
                obj.descricao = descricao
                obj.url = full_url
                obj.url_sentry = sentry_event_url
                obj.view = view_name
                obj.sentry_issue_id = sentry_issue_id
                obj.agent = request.META.get('HTTP_USER_AGENT', '-')
                obj.ip_address = get_client_ip(request)
                obj.maquina = get_hostname()
                obj.criar()

                messages.success(request, 'Problema informado com sucesso.')

            return HttpResponseRedirect(obj.get_absolute_url())
    except Exception as e:
        if settings.DEBUG:
            import traceback
            traceback.print_exc()
            messages.error(request, str(e))
        messages.error(request, 'Você não tem permissão para fazer isso.')
    return HttpResponseRedirect('/')


@rtr()
@login_required
def reportar_erro_por_chamado(request, chamado_pk):
    title = f'Reportar erro a partir do chamado #{chamado_pk}'
    if 'centralservicos' in settings.INSTALLED_APPS:
        from centralservicos.models import Chamado
        chamado = get_object_or_404(Chamado.objects, pk=chamado_pk)
        if chamado.pode_reclassificar(request.user):
            form = ReportarErroPorChamadoForm(request.POST or None, request=request)
            if form.is_valid():
                form.processar(chamado)
                return httprr('..', 'Erro reportado com sucesso.')
            return locals()
    return httprr(request, 'Você não tem permissão para fazer isso.', 'error')


@rtr()
@login_required
def reportar_erro(request):
    title = 'Reportar Erro no SUAP'
    path = request.GET.get('url')
    try:
        path = base64.b64decode(path.encode()).decode()
        url = request.build_absolute_uri(path)
        view = get_custom_view_name_from_url(url)
        if not view:
            raise Exception('url inválida.')
    except Exception:
        return httprr('..', 'URL informada é incorreta.', 'error')
    form = ReportarErroForm(request.POST or None, request=request, url=url)
    if form.is_valid():
        obj = form.processar()
        return httprr(obj.get_absolute_url(), 'Erro reportado com sucesso.')
    return locals()


@rtr()
@login_required
def areas(request):
    title = "Erros"
    lista_areas = get_areas()
    return locals()


@rtr()
@login_required
def modulos(request, area_id):
    areas = get_areas()
    area = areas.get(area_id, {})
    if not area:
        return httprr('/erros/areas', 'Área inexistente.', 'error')
    title = f"Área {area.get('area')}"
    lista_modulos = get_apps_disponiveis(area)
    modulos = []
    for modulo in lista_modulos:
        modulo.abertos = Erro.objects.filter(view__icontains=modulo.label).exclude(situacao__in=Erro.SITUACOES_FINAIS).count()
        modulo.resolvidos = Erro.objects.filter(situacao=Erro.SITUACAO_RESOLVIDO, view__icontains=modulo.label).count()
    modulo = request.GET.get('modulo')
    form = ModulosForm()
    return locals()


@rtr()
@login_required
def modulo(request, modulo_id):
    url = base64.b64encode(f"/erros/modulo/{modulo_id}/".encode()).decode()
    return HttpResponseRedirect(f'/erros/reportar_erro/?url={url}')


@rtr()
@login_required
def erros(request):
    title = 'Erros'
    form = BuscarErrosForm(request.GET or None, request=request)
    eh_desenvolvedor = in_group(request.user, 'Desenvolvedor', ignore_if_superuser=False)
    eh_recebedor = in_group(request.user, 'Recebedor de Demandas', ignore_if_superuser=False)
    if form.is_valid():
        erros = form.processar()
    else:
        erros = Erro.objects.all()
        if not in_group(request.user, 'Desenvolvedor'):
            erros = (erros.exclude(situacao=Erro.SITUACAO_CANCELADO) | erros.filter(situacao=Erro.SITUACAO_CANCELADO, interessadoerro__vinculo=request.user.get_vinculo())).distinct()
    erros = erros.order_by('-qtd_vinculos_afetados', 'data_criacao')

    abas = {}
    abas['Reportados'] = erros.filter(situacao__in=[Erro.SITUACAO_ABERTO, Erro.SITUACAO_REABERTO])
    abas['Em análise'] = erros.filter(situacao=Erro.SITUACAO_EM_ANDAMENTO)
    abas['Em correção'] = erros.filter(situacao=Erro.SITUACAO_EM_CORRECAO)
    abas['Aguardando feedback'] = erros.filter(situacao=Erro.SITUACAO_SUSPENSO)
    abas['Resolvidos'] = erros.filter(situacao=Erro.SITUACAO_RESOLVIDO)
    abas['Cancelados'] = erros.filter(situacao=Erro.SITUACAO_CANCELADO)
    return locals()


@rtr()
@login_required
def erro(request, pk):
    obj = get_object_or_404(Erro, pk=pk)

    title = f'Erro {pk}: {apps.get_app_config(obj.modulo_afetado).verbose_name}'

    vinculo = request.user.get_vinculo()

    if not obj.vinculo_eh_interessado(vinculo) and not obj.vinculo_pode_ser_atendente(vinculo) and obj.situacao == Erro.SITUACAO_CANCELADO:
        raise PermissionDenied()

    outros_interessados = obj.get_outros_interessados()
    outros_atendentes = obj.get_outros_atendentes()
    comentarios = obj.historicocomentarioerro_set.exclude(tipo=HistoricoComentarioErro.TIPO_NOTA_INTERNA)
    notas_internas = obj.historicocomentarioerro_set.filter(tipo=HistoricoComentarioErro.TIPO_NOTA_INTERNA)
    eh_atendente = obj.vinculo_pode_ser_atendente(vinculo)
    eh_interessado = obj.vinculo_eh_interessado(vinculo)
    pode_comentar = obj.pode_comentar(vinculo)
    pode_comentar_nota_interna = obj.pode_comentar_nota_interna(vinculo)
    pode_sincronizar_gitlab = obj.pode_sincronizar_gitlab(vinculo)
    pode_criar_issue_gitlab = obj.pode_criar_issue_gitlab(vinculo)
    pode_ver_comentarios = obj.pode_ver_comentarios(vinculo)
    pode_ver_nota_interna = obj.pode_ver_nota_interna(vinculo)
    pode_assumir = obj.pode_assumir(vinculo)
    pode_devolver = obj.pode_devolver(vinculo)
    pode_se_interessar = obj.pode_se_interessar(vinculo)
    pode_alterar_url = obj.pode_alterar_url(vinculo)
    pode_editar_atualizacao = obj.pode_editar_atualizacao(vinculo)
    pode_se_desinteressar = obj.pode_se_desinteressar(vinculo)
    pode_atribuir = obj.pode_atribuir(vinculo)
    pode_unificar = obj.pode_unificar(vinculo)
    situacoes_disponiveis = obj.get_situacoes_disponiveis(vinculo)
    conf = ferramentas_configuradas()

    if eh_atendente:
        erros_mesma_view = Erro.objects.filter(view=obj.view).exclude(situacao__in=Erro.SITUACOES_FINAIS).exclude(id=obj.id).count()
        if request.GET.get('sincronizar_gitlab'):
            if conf:
                if obj.pode_sincronizar_gitlab(vinculo):
                    url_gitlab = popular_links_gitlab(obj, conf)
                else:
                    return httprr('.', 'Usuário sem permissão para sincronizar o gitlab.')
            else:
                return httprr('.', 'Sentry ou Gitlab não configurados.')
            if url_gitlab:
                return httprr('.', 'Url de Issue do Gitlab sincronizada com sucesso.')
            else:
                return httprr('.', 'Url de Issue do Gitlab inexistente.', 'error')
        if request.GET.get('criar_issue_gitlab'):
            if conf:
                if obj.pode_criar_issue_gitlab(vinculo):
                    url_gitlab = criar_issue_gitlab(obj, conf, request)
                else:
                    return httprr('.', 'Usuário sem permissão para criar issue no gitlab.')
            else:
                return httprr('.', 'Sentry ou Gitlab não configurados.')
            if url_gitlab:
                return httprr('.', 'Issue criada no Gitlab com sucesso.')
            else:
                return httprr('.', 'Não foi possível criar Issue no Gitlab.', 'error')
        if request.GET.get('assumir'):
            obj.gerenciar_atendente(vinculo, forcar_assumir=True)
            return httprr('.', 'Você agora é o Atendente Principal deste erro.')
        elif request.GET.get('devolver'):
            obj.devolver(vinculo)
            return httprr('.', 'Erro devolvido com sucesso.')
    if request.GET.get('interessar') and pode_se_interessar:
        obj.gerenciar_interessado(vinculo)
        return httprr('.', 'Você agora é um Interessado deste erro.')
    if request.GET.get('desinteressar') and pode_se_desinteressar:
        obj.gerenciar_interessado(vinculo, habilitar=False)
        return httprr('.', 'Interesse removido com sucesso.')

    form = ComentarioErroForm(request.POST or None)
    if form.is_valid() and pode_comentar:
        tipo = request.POST.get('tipo', 'comentario')
        form.processar(obj, vinculo, tipo=tipo)
        url = obj.get_absolute_url()
        if tipo == 'nota_interna':
            url += '?tab=notas_internas'
        return httprr(url, 'Comentário cadastrado com sucesso.')

    return locals()


@rtr()
@login_required
def alterar_situacao_erro(request, pk):
    erro = get_object_or_404(Erro, pk=pk)
    vinculo = request.user.get_vinculo()

    try:
        situacao_id = int(request.GET.get('situacao'))
    except Exception:
        return httprr('..', 'Situação de destino inválida.', 'error')

    if situacao_id in erro.get_situacoes_disponiveis(vinculo):
        situacao_nova_display = Erro(situacao=situacao_id).get_situacao_display()
        title = 'Criar Atualização'
        if situacao_id == Erro.SITUACAO_REABERTO and not erro.vinculo_pode_ser_atendente(vinculo):
            form = SituacaoErroForm(request.POST or None)
            if form.is_valid():
                form.processar(erro, vinculo, situacao_id)
                return httprr('..', 'Situação alterada com sucesso.')
        elif situacao_id == Erro.SITUACAO_RESOLVIDO:
            form = EditarAtualizacaoErroForm(request.POST or None, request=request, instance=erro, required=False)
            if form.is_valid():
                form.save()
                erro.gerenciar_situacao(vinculo=request.user.get_vinculo(), situacao=situacao_id)
                return httprr('..', 'Situação alterada com sucesso.')
        else:
            erro.gerenciar_situacao(vinculo=request.user.get_vinculo(), situacao=situacao_id)
            return httprr(erro.get_absolute_url(), 'Situação alterada com sucesso.')
    else:
        return httprr('..', 'Você não possui permissão para fazer isto.', 'error')
    return locals()


@rtr()
@login_required
def gerenciar_interessados_erro(request, pk):
    title = f'Gerenciar Interessados do Erro {pk}'
    erro = get_object_or_404(Erro, pk=pk)
    vinculo = request.user.get_vinculo()
    if not erro.pode_gerenciar_interessados(vinculo):
        return httprr('..', 'Você não tem permissão para fazer isto.', 'erro')

    try:
        desabilitar_interessado_id = int(request.GET.get('desabilitar', 0))
        if desabilitar_interessado_id:
            interessado = InteressadoErro.objects.filter(pk=desabilitar_interessado_id, erro=erro).first()
            if interessado:
                erro.gerenciar_interessado(interessado.vinculo, habilitar=False)
                return httprr(erro.get_absolute_url(), 'Interessado desabilitado com sucesso.')
            else:
                return httprr(erro.get_absolute_url(), 'Interessado inexistente.')

        reabilitar_interessado_id = int(request.GET.get('reabilitar', 0))
        if reabilitar_interessado_id:
            interessado = InteressadoErro.objects.filter(pk=reabilitar_interessado_id, erro=erro).first()
            if interessado:
                erro.gerenciar_interessado(interessado.vinculo, habilitar=True)
                return httprr(erro.get_absolute_url(), 'Interessado reabilitado com sucesso.')
            else:
                return httprr(erro.get_absolute_url(), 'Interessado inexistente.')
    except Exception as e:
        return httprr('..', f'Erro ao tentar desabilitar interessado. Detalhes: {e}', 'error')

    form = InteressadoErroForm(request.POST or None, erro=erro, request=request)
    if form.is_valid():
        form.save()
        return httprr('..', 'Interessados alterados com sucesso.')
    return locals()


@rtr()
@login_required
def alterar_url(request, pk):
    title = f'Alterar URL do Erro {pk}'
    erro = get_object_or_404(Erro, pk=pk)
    tipo = request.GET.get('tipo')
    vinculo = request.user.get_vinculo()
    if not erro.vinculo_pode_ser_atendente(vinculo) or not tipo in ['erro', 'sentry', 'gitlab']:
        return httprr('..', 'Você não tem permissão para fazer isto.', 'erro')

    url = ''
    if tipo == 'erro':
        url = erro.url
    elif tipo == 'sentry':
        url = erro.url_sentry
    elif tipo == 'gitlab':
        url = erro.gitlab_issue_url

    form = AlterarURLErroForm(request.POST or None, request=request, initial={'url': url}, tipo=tipo, erro=erro, vinculo=vinculo)
    if form.is_valid():
        form.processar()
        return httprr('..', f'URL do {tipo} alterada com sucesso.')

    return locals()


@rtr()
@login_required
def adicionar_anexo(request, pk):
    title = f'Adicionar Anexo ao Erro {pk}'
    erro = get_object_or_404(Erro, pk=pk)
    vinculo = request.user.get_vinculo()
    if not erro.pode_comentar(vinculo):
        return httprr('..', 'Você não tem permissão para fazer isto.', 'erro')

    form = AnexoErroForm(request.POST or None, files=request.FILES or None, request=request, erro=erro, vinculo=vinculo)
    if form.is_valid():
        instancia = form.processar()
        return httprr('..', 'Anexo adicionado com sucesso.')

    return locals()


@rtr()
@login_required
def atribuir_atendente(request, pk):
    title = f'Atribuir Atendente ao erro #{pk}'
    erro = get_object_or_404(Erro, pk=pk)
    atribuinte = request.user.get_vinculo()
    if not erro.pode_atribuir(atribuinte):
        return httprr('..', 'Você não tem permissão para fazer isto.', 'erro')

    form = AtribuirErroForm(request.POST or None, files=request.FILES or None, request=request, erro=erro, atribuinte=atribuinte)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Usuário atribuído com sucesso.')
    return locals()


@rtr()
@login_required
def unificar_erros(request, pk):
    title = f'Unificar erros ao erro #{pk}'
    erro = get_object_or_404(Erro, pk=pk)
    vinculo = request.user.get_vinculo()
    if not erro.pode_unificar(vinculo):
        return httprr('..', 'Você não tem permissão para fazer isto.', 'erro')

    form = UnificarErroForm(request.POST or None, files=request.FILES or None, request=request, erro=erro, vinculo=vinculo)
    if form.is_valid():
        form.processar()
        return httprr('..', 'Erros unificados com sucesso.')
    return locals()


@rtr()
@login_required
def desconsiderar_comentario(request, pk):
    comentario = get_object_or_404(HistoricoComentarioErro, pk=pk)
    vinculo = request.user.get_vinculo()
    if not comentario.pode_desconsiderar_comentario(vinculo):
        return httprr(comentario.erro.get_absolute_url(), 'Você não tem permissão para fazer isto.', 'erro')

    comentario.desconsiderar_comentario()

    return httprr(comentario.erro.get_absolute_url(), 'Comentário desconsiderado com sucesso.')


@rtr()
@login_required
def remover_atendente(request, pk_erro, pk_vinculo):
    obj = get_object_or_404(Erro, pk=pk_erro)
    if request.user.get_vinculo().id == pk_vinculo:
        qs = AtendenteErro.objects.filter(erro_id=pk_erro, vinculo_id=pk_vinculo).exclude(vinculo=obj.atendente_atual)
        if qs.exists():
            qs.delete()
            return httprr(obj.get_absolute_url(), 'Remoção realizada com sucesso.')
    return httprr(obj.get_absolute_url(), 'Você não tem permissão para fazer isto.', 'erro')


@rtr()
@login_required
def editar_atualizacao(request, pk):
    obj = get_object_or_404(Erro, pk=pk)
    vinculo = request.user.get_vinculo()
    if not obj.pode_editar_atualizacao(vinculo):
        return httprr('..', 'Você não tem permissão para fazer isto.', 'erro')

    if obj.atualizacao:
        title = f'Editar Atualização para o Erro #{pk}'
    else:
        title = f'Criar Atualização para o Erro #{pk}'

    form = EditarAtualizacaoErroForm(request.POST or None, request=request, instance=obj)
    if form.is_valid():
        form.save()
        return httprr('..', 'Atualização editada com sucesso.')
    return locals()


def exception(request, pk=None):
    from sentry_sdk import capture_exception
    from comum.views import handler500

    e = Exception('Erro simulado para testar o sentry .')

    if not settings.DEBUG:
        raise e

    capture_exception(e)
    return handler500(request)
