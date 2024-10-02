from datetime import datetime

import plotly.figure_factory as ff
import plotly.offline as opy
from django.contrib import messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import F, Max
from django.shortcuts import get_object_or_404, redirect
from django.template.defaultfilters import pluralize
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt

from comum.models import Comentario
from djtools import layout
from djtools.utils import permission_required, rtr, httprr, JsonResponse
from gerenciador_projetos.forms import (
    TarefaFormFactory,
    HistoricoEvolucaoForm,
    AdicionarOuVincularListaProjetoForm,
    AtualizarPosicaoListaProjetoForm,
    RecorrenciaTarefaForm,
    TagForm, DashboardForm,
    MinhasTarefasForm,
    BuscaHistoricoEvolucaoForm
)
from gerenciador_projetos.models import Projeto, Tarefa, HistoricoEvolucao, Lista, ListaTarefa, ListaProjeto, \
    RecorrenciaTarefa, Tag
from gerenciador_projetos.utils import generate_color


@layout.quadro('Gerenciamento de Projetos', icone='diagnoses', pode_esconder=True)
def index_quadros(quadro, request):
    if request.user.has_perm('view_projeto'):
        tarefas_andamento = Tarefa.objects.filter(atribuido_a=request.user, data_conclusao__isnull=True)
        if tarefas_andamento.exists():
            qtd_tarefas_andamento = tarefas_andamento.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo='Tarefa{}'.format(pluralize(qtd_tarefas_andamento)),
                    subtitulo='Em andamento',
                    qtd=qtd_tarefas_andamento,
                    url='/gerenciador_projetos/minhastarefas/',
                )
            )
    return quadro


@rtr('gerenciador_projetos/templates/projeto.html')
@permission_required('gerenciador_projetos.view_projeto')
def projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)

    if not projeto.pode_ver_projeto(request.user):
        raise PermissionDenied('Você não está na equipe desse projeto.')

    title = "Projeto: {}".format(projeto.titulo)

    usuario_logado = request.user
    eh_superusuario = usuario_logado.is_superuser
    eh_gerente_projeto = projeto.eh_gerente_projeto(usuario_logado)
    eh_membro_projeto = projeto.eh_membro_projeto(usuario_logado)

    pode_adicionar_comentarios = projeto.pode_adicionar_comentarios(usuario_logado)
    pode_adicionar_tarefas = projeto.pode_adicionar_tarefas(usuario_logado)
    pode_adicionar_listas = projeto.pode_adicionar_listas(usuario_logado)
    pode_editar_tags = projeto.pode_editar_tags(usuario_logado)

    pode_editar_projeto = projeto.pode_editar_projeto(usuario_logado)
    pode_editar_tarefas = projeto.pode_editar_tarefas(usuario_logado)
    pode_registrar_evolucao = request.user.has_perm('gerenciador_projetos.change_historicoevolucao')

    qtd_comentarios = Comentario.objects.filter(
        content_type=ContentType.objects.get(app_label='gerenciador_projetos', model='projeto'), object_id=projeto.pk, resposta=None
    ).count()
    tarefas = projeto.tarefas_raiz()
    return locals()


@rtr()
@permission_required('gerenciador_projetos.change_lista')
def adicionar_ou_vincular_lista_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    title = projeto.titulo
    if not projeto.pode_editar_listas(request.user):
        return httprr('..', 'Você não tem permissão para adicionar e/ou editar listas nesse projeto.', 'error')

    form = AdicionarOuVincularListaProjetoForm(request.POST or None, request=request, projeto=projeto)
    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada com sucesso.')

    return locals()


@rtr()
@permission_required('gerenciador_projetos.add_tag')
def adicionar_tag(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if not projeto.pode_editar_tags(request.user):
        return httprr('..', 'Você não tem permissão para adicionar e/ou editar listas nesse projeto.', 'error')

    form = TagForm(request.POST or None, request=request)
    if form.is_valid():
        tag = form.instance
        tag.projeto = projeto
        form.save()
        return httprr('..', 'Tag adicionada com sucesso.')

    return locals()


@rtr()
@permission_required('gerenciador_projetos.change_tag')
def editar_tag(request, tag_id):
    tag = get_object_or_404(Tag, pk=tag_id)
    if not tag.projeto.pode_editar_tags(request.user):
        return httprr('..', 'Você não tem permissão para adicionar e/ou editar listas nesse projeto.', 'error')

    form = TagForm(request.POST or None, request=request, instance=tag)
    if form.is_valid():
        tag = form.instance
        form.save()
        return httprr('..', 'Tag atualizada com sucesso.')

    return locals()


@rtr()
@permission_required('gerenciador_projetos.change_tarefa')
def recorrencia_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, pk=tarefa_id)
    title = tarefa.titulo
    form = RecorrenciaTarefaForm(request.POST or None, request=request)
    form.instance.tarefa = tarefa
    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada com sucesso.')

    return locals()


@rtr()
@permission_required('gerenciador_projetos.change_tarefa')
def remover_recorrencia_tarefa(request, recorrenciatarefa_id):
    recorrenciatarefa = get_object_or_404(RecorrenciaTarefa, pk=recorrenciatarefa_id)
    tarefa = recorrenciatarefa.tarefa
    if request.method == 'POST':
        recorrenciatarefa.delete()
        return httprr(tarefa.get_absolute_url(), 'Operação realizada com sucesso.')
    return locals()


@permission_required('gerenciador_projetos.change_tarefa')
def reabrir_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, pk=tarefa_id)

    try:
        tarefa.reabrir(request.user)
        messages.success(request, "A tarefa foi reaberta.")
    except ValidationError as e:
        messages.error(request, str(e))
    except Exception:
        messages.error(request, "Ocorreu problemas ao reabrir tarefa.")

    return redirect(reverse('tarefa', args=[tarefa_id]))


@rtr()
@permission_required('gerenciador_projetos.change_projeto')
def atualizar_posicao_lista_projeto(request, lista_projeto_id):
    listaprojeto = get_object_or_404(ListaProjeto, pk=lista_projeto_id)
    title = listaprojeto.projeto.titulo
    form = AtualizarPosicaoListaProjetoForm(request.POST or None)
    if form.is_valid():
        posicao = form.cleaned_data.get('posicao')
        ListaProjeto.objects.filter(projeto=listaprojeto.projeto, posicao__gte=posicao).update(posicao=F('posicao') + 1)
        listaprojeto.posicao = posicao
        listaprojeto.save()
        count = 1
        for obj in ListaProjeto.objects.filter(projeto=listaprojeto.projeto).order_by('posicao'):
            ListaProjeto.objects.filter(pk=obj.pk).update(posicao=count)
            count += 1

        return httprr('..', 'Operação realizada com sucesso.')

    return locals()


@rtr('gerenciador_projetos/templates/dashboard.html')
@permission_required('gerenciador_projetos.view_projeto')
def dashboard(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    pode_adicionar_listas = projeto.pode_adicionar_listas(request.user)
    pode_adicionar_tarefas = projeto.pode_adicionar_tarefas(request.user)
    pode_editar_projeto = projeto.pode_editar_projeto(request.user)
    title = "Projeto: {}".format(projeto.titulo)

    listaprojeto_ativas = projeto.listaprojeto_set.filter(lista__ativa=True)
    listaprojeto_inativas = projeto.listaprojeto_set.filter(lista__pk__in=Tarefa.objects.filter(lista__ativa=False, projeto=projeto).values_list('lista__pk', flat=True))
    listaprojeto = (listaprojeto_ativas | listaprojeto_inativas).order_by('posicao')

    form_filtros = DashboardForm(request.POST or None, projeto=projeto)
    if form_filtros.is_valid():
        filtros = {}
        atribuido_a = form_filtros.cleaned_data.get('atribuido_a')
        situacao = form_filtros.cleaned_data.get('situacao')
        exibir_concluidas = form_filtros.cleaned_data.get('exibir_concluidas')
        if atribuido_a:
            filtros['atribuido_a__in'] = atribuido_a
        if situacao:
            filtros['situacao'] = situacao
        if exibir_concluidas:
            listaprojeto = listaprojeto_ativas
    return locals()


@rtr('gerenciador_projetos/templates/gantt.html')
@permission_required('gerenciador_projetos.view_projeto')
def gantt(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    title = projeto.titulo
    tarefas = Tarefa.objects.filter(projeto_id=projeto_id, data_inicio__isnull=False, data_conclusao_estimada__isnull=False).order_by('lista', '-data_inicio')
    pode_editar_tarefas = projeto.pode_editar_tarefas(request.user)
    if tarefas.exists():
        colors = []
        df = []
        for tarefa in tarefas:
            info = dict(Task=tarefa.titulo, Start=tarefa.data_inicio.strftime("%Y-%m-%d"), Finish=tarefa.data_conclusao_estimada.strftime("%Y-%m-%d"))
            df.append(info)
            colors.append(generate_color())
        fig = ff.create_gantt(df, colors=colors, index_col='Finish', show_colorbar=True, bar_width=0.2, showgrid_x=True, title='Gráfico de Gantt', height=900, width=1440)
        fig['layout'].pop('height', None)
        fig['layout'].pop('width', None)
        # height = 600, width = 900
        # fig['layout'].update(autosize=False, height=900, width=1440, margin=dict(l=110))

        gantt = opy.plot(fig, auto_open=False, output_type='div')
    return locals()


@rtr()
@permission_required(['gerenciador_projetos.change_tarefa'])
def gerenciar_tarefa(request, projeto_id, tarefa_id=None):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    if not projeto.pode_editar_tarefas(request.user):
        return httprr('..', 'Você não tem permissão para adicionar e/ou editar tarefas nesse projeto.', 'error')

    title = projeto.titulo
    lista_id = request.GET.get('lista')
    lista = Lista.objects.get(pk=lista_id) if lista_id and projeto.listas_do_projeto().filter(lista__id=lista_id).exists() else None

    tarefa_pai = request.GET.get('tarefa_pai')

    if tarefa_id:  # Alterando uma tarefa
        tarefa = get_object_or_404(Tarefa, pk=tarefa_id)
        FormClass = TarefaFormFactory(request, projeto=projeto, tarefa=tarefa, tarefa_pai=tarefa_pai)
        form = FormClass(request.POST or None, instance=tarefa)
    else:  # Adicionando uma tarefa
        FormClass = TarefaFormFactory(request, projeto=projeto, tarefa_pai=tarefa_pai)
        form = FormClass(request.POST or None)
        form.instance.projeto = projeto
        form.instance.criado_por = request.user
        if lista:
            form.instance.lista = lista

    if form.is_valid():
        form.save()
        if lista:
            tarefa = form.instance
            maior_posicao = ListaTarefa.objects.filter(lista=lista, tarefa=tarefa).aggregate(maior_posicao=Max('posicao'))['maior_posicao'] or 0
            ListaTarefa.objects.create(lista=lista, tarefa=tarefa, posicao=maior_posicao + 1, registrado_por=request.user)
        return httprr('..', 'Operação realizada com sucesso.')

    return locals()


@rtr()
@csrf_exempt
@permission_required(['gerenciador_projetos.change_tarefa'])
def editar_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, pk=tarefa_id)
    projeto = get_object_or_404(Projeto, pk=tarefa.projeto_id)
    if not projeto.pode_editar_tarefas(request.user):
        return httprr('..', 'Você não tem permissão para adicionar e/ou editar tarefas nesse projeto.', 'error')
    field = request.POST.get('field')
    value = request.POST.get('value')
    if field and value and getattr(tarefa, field) != value:
        setattr(tarefa, request.POST['field'], request.POST['value'])
        tarefa.save()
        return httprr(tarefa.get_absolute_url())


@csrf_exempt
@permission_required(['gerenciador_projetos.change_tarefa'])
def gerenciar_tarefa_api(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)

    if not projeto.pode_editar_tarefas(request.user):
        return JsonResponse({'ok': False})

    lista_id = request.POST.get('lista')
    lista = Lista.objects.get(pk=lista_id) if lista_id and projeto.listas_do_projeto().filter(lista__id=lista_id).exists() else None
    titulo = request.POST.get('titulo')

    tarefa = Tarefa(titulo=titulo, lista=lista, criado_por=request.user, projeto=projeto)

    tarefa.save()
    if tarefa.id is not None:
        return JsonResponse({'ok': True})
    else:
        return JsonResponse({'ok': False})


@rtr('gerenciador_projetos/templates/tarefa.html')
@permission_required('gerenciador_projetos.view_tarefa')
def tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, pk=tarefa_id)
    pode_editar_tarefas = tarefa.projeto.pode_editar_tarefas(request.user)
    eh_membro_projeto = tarefa.projeto.eh_membro_projeto(request.user)
    pode_registrar_evolucao = all([
        request.user.has_perm('gerenciador_projetos.change_historicoevolucao'),
        not tarefa.concluida
    ])
    title = "#{} {}".format(tarefa.id, tarefa.titulo)
    return locals()


@rtr()
@permission_required('gerenciador_projetos.change_projeto')
def clonar_projeto(request, projeto_id):
    projeto = get_object_or_404(Projeto, pk=projeto_id)
    projeto = projeto.clonar(request.user)
    return httprr(projeto.get_absolute_url(), 'Operação realizada com sucesso.')


@rtr()
@permission_required('gerenciador_projetos.change_tarefa')
def clonar_tarefa(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, pk=tarefa_id)
    tarefa = tarefa.clonar(request.user)
    return httprr(tarefa.get_absolute_url(), 'Operação realizada com sucesso.')


@rtr()
@permission_required('gerenciador_projetos.change_tarefa')
def atribuir_a_mim(request, tarefa_id):
    tarefa = get_object_or_404(Tarefa, pk=tarefa_id)
    tarefa.atribuir_para(request.user)
    return httprr(tarefa.projeto.get_absolute_url(), 'Atribuição realizada com sucesso.')


@rtr()
@permission_required('gerenciador_projetos.change_historicoevolucao')
def gerenciar_historicoevolucao(request, tarefa_id, historicoevolucao_id=None):
    tarefa = get_object_or_404(Tarefa, pk=tarefa_id)
    title = tarefa.titulo

    if tarefa.concluida:
        messages.error(request, 'Não é possível registrar histórico a tarefas concluídas.')
        return httprr('..')

    if historicoevolucao_id:
        historicoevolucao = get_object_or_404(HistoricoEvolucao, pk=historicoevolucao_id)
        form = HistoricoEvolucaoForm(request.POST or None, request.FILES or None, instance=historicoevolucao)
    else:
        form = HistoricoEvolucaoForm(request.POST or None, request.FILES or None)
        form.instance.tarefa = tarefa

    form.instance.registrado_por = request.user
    if form.is_valid():
        form.save()
        return httprr('..', 'Evolução registrada com sucesso.')

    return locals()


@csrf_exempt
@permission_required('gerenciador_projetos.change_historicoevolucao')
def mudarlista(request, tarefa_id, lista_id, posicao):
    tarefa = get_object_or_404(Tarefa, pk=tarefa_id)
    if posicao < 2:
        return JsonResponse({'erro': True})
    posicao = posicao - 2
    ListaTarefa.objects.filter(tarefa=tarefa, data_hora_saida__isnull=True).update(data_hora_saida=datetime.now())
    if int(lista_id) != 0:
        lista = get_object_or_404(Lista, pk=lista_id)
        tarefa.lista = lista
        for index, item in enumerate(ListaTarefa.objects.filter(lista=lista, data_hora_saida__isnull=True).order_by('posicao')):
            if index >= posicao:
                index += 1
            item.posicao = index
            item.save()
        ListaTarefa.objects.create(lista=lista, tarefa=tarefa, posicao=posicao, registrado_por=request.user)
    else:
        tarefa.lista = None
    tarefa.save()
    return JsonResponse({'ok': True})


@rtr()
@permission_required('gerenciador_projetos.change_tarefa')
def minhas_tarefas(request):
    # 2295687
    title = 'Minhas Tarefas'

    tarefas_andamento = Tarefa.objects.filter(atribuido_a=request.user, data_conclusao__isnull=True)
    tarefas_concluidas = Tarefa.objects.filter(atribuido_a=request.user, data_conclusao__isnull=False)

    form_filtros = MinhasTarefasForm(request.POST or None, usuario=request.user)
    if form_filtros.is_valid():
        tarefas_andamento = tarefas_andamento.filter(projeto=form_filtros.cleaned_data['projeto'])
        tarefas_concluidas = tarefas_andamento.filter(projeto=form_filtros.cleaned_data['projeto'])

    return locals()


@rtr()
@permission_required('gerenciador_projetos.view_projeto')
def status_projeto(request, projeto_id):

    projeto = get_object_or_404(Projeto, pk=projeto_id)

    if not projeto.pode_ver_projeto(request.user):
        raise PermissionDenied('Você não está na equipe desse projeto.')

    pode_editar_tarefas = projeto.pode_editar_tarefas(request.user)

    title = 'Situação do projeto: {}'.format(projeto)

    lista_tarefas = list()
    tarefas = projeto.tarefas_raiz()
    for tarefa in tarefas:
        lista_tarefas.append(tarefa)
        for subtarefa in tarefa.get_subtarefas():
            lista_tarefas.append(subtarefa)

    return locals()


@rtr()
@permission_required('gerenciador_projetos.view_projeto')
def evolucao_tarefas_projeto(request, projeto_id):

    projeto = get_object_or_404(Projeto, pk=projeto_id)

    if not projeto.pode_ver_projeto(request.user):
        raise PermissionDenied('Você não está na equipe desse projeto.')

    title = 'Histórico de evolução das tarefas do projeto: {}'.format(projeto)

    historico = HistoricoEvolucao.objects.filter(tarefa__projeto=projeto).order_by('-data_hora')

    form = BuscaHistoricoEvolucaoForm(request.POST or None)
    if form.is_valid():
        di = form.cleaned_data.get('data_inicio')
        df = form.cleaned_data.get('data_final')

        if di or df:
            if di and df:
                historico = historico.filter(data_hora__gte=di, data_hora__lte=df)
            elif di and not df:
                historico = historico.filter(data_hora__gte=di)
            else:
                historico = historico.filter(data_hora__lte=df)

    return locals()
