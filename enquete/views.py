from datetime import datetime

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from djtools import layout
from djtools.utils import rtr, httprr
from enquete import tasks
from enquete.forms import PerguntaForm, OpcaoForm, OpcaoPerguntaForm, ResponderEnqueteFormFactory, BuscarPublicoForm, \
    FiltrarRespostasForm
from enquete.models import Enquete, Categoria, Pergunta, Opcao


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()
    for enquete_aberta in Enquete.get_abertas(request.user.get_vinculo()):
        if enquete_aberta.manter_enquete_inicio or not enquete_aberta.respondeu_todas_as_perguntas(request.user.get_vinculo()):
            inscricoes.append(
                dict(
                    url='/enquete/responder_enquete/{:d}/'.format(enquete_aberta.id),
                    titulo='{}: <strong>{}</strong>.'.format(enquete_aberta.tag, enquete_aberta.titulo),
                    prazo=enquete_aberta.data_fim,
                )
            )

    return inscricoes


@rtr()
@login_required()
def enquete(request, id):
    enquete = get_object_or_404(Enquete, pk=id)
    title = 'Enquete: {}'.format(enquete.titulo)
    if not enquete.eh_responsavel(request.user):
        raise PermissionDenied

    hoje = datetime.now()
    categorias = enquete.get_perguntas_agrupadas_por_categoria()
    return locals()


@rtr()
@login_required()
def adicionar_opcao(request, enquete_id, pergunta_id=None):
    title = 'Adicionar Opção de Resposta'
    enquete = get_object_or_404(Enquete, pk=enquete_id)

    if not enquete.eh_responsavel(request.user):
        raise PermissionDenied

    if pergunta_id and enquete.eh_responsavel(request.user):
        pergunta = get_object_or_404(Pergunta, pk=pergunta_id)
        if not pergunta.objetiva:
            raise PermissionDenied
        form = OpcaoPerguntaForm(request.POST or None, request.FILES or None, enquete=enquete, pergunta=pergunta)
    elif enquete.eh_responsavel(request.user):
        form = OpcaoForm(request.POST or None, request.FILES or None, enquete=enquete)

    if request.method == 'POST':
        if form.is_valid():
            obj = form.save()
            return httprr(f'/enquete/enquete/{enquete.id}/', 'Opção adicionada com sucesso.')
    return locals()


@rtr()
@login_required()
def editar_opcao(request, id):
    title = 'Editar Opção'
    opcao = get_object_or_404(Opcao, pk=id)
    if not opcao.enquete.eh_responsavel(request.user):
        raise PermissionDenied

    form = OpcaoForm(request.POST or None, request.FILES or None, instance=opcao)
    if request.method == 'POST':
        if form.is_valid():
            obj = form.save()
            return httprr('/enquete/enquete/{:d}/'.format(opcao.enquete_id), 'Opção atualizada com sucesso.')
    return locals()


@rtr()
@login_required()
def remover_opcao(request, id):
    opcao = get_object_or_404(Opcao, pk=id)
    if not opcao.enquete.eh_responsavel(request.user):
        raise PermissionDenied

    opcao.delete()
    return httprr('/enquete/enquete/{:d}/'.format(opcao.enquete_id), 'Opção removida com sucesso.')


@rtr()
@login_required()
def adicionar_pergunta(request, enquete_id, categoria_id):
    title = 'Adicionar Pergunta'
    enquete = get_object_or_404(Enquete, pk=enquete_id)
    if not enquete.eh_responsavel(request.user):
        raise PermissionDenied

    categoria = get_object_or_404(Categoria, pk=categoria_id)
    form = PerguntaForm(request.POST or None, enquete=enquete, categoria=categoria)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return httprr('..', 'Pergunta adicionada com sucesso.')

    return locals()


@rtr()
@login_required()
def editar_pergunta(request, id):
    title = 'Editar Pergunta'
    pergunta = get_object_or_404(Pergunta, pk=id)
    if not pergunta.enquete.eh_responsavel(request.user):
        raise PermissionDenied

    form = PerguntaForm(request.POST or None, instance=pergunta)
    if request.method == 'POST':
        if form.is_valid():
            form.save()
            return httprr('..', 'Pergunta atualizada com sucesso.')

    return locals()


@rtr()
@login_required()
def remover_pergunta(request, id):
    pergunta = get_object_or_404(Pergunta, pk=id)
    if not pergunta.enquete.eh_responsavel(request.user):
        raise PermissionDenied

    pergunta.delete()
    return httprr('/enquete/enquete/{:d}/'.format(pergunta.enquete_id), 'Pergunta removida com sucesso.')


@rtr()
@login_required
def ver_respostas(request, id):
    return responder_enquete(request, id, read_only=True)


@rtr()
@login_required
def responder_enquete(request, id, read_only=False):
    enquete = get_object_or_404(Enquete, pk=id)
    title = enquete.titulo
    vinculo = request.user.get_vinculo()
    if not enquete.pode_responder(vinculo) and not read_only:
        raise PermissionDenied

    Form = ResponderEnqueteFormFactory(request, enquete)
    form = Form(request.POST or None)
    if form.is_valid():
        form.save()
        messages.info(request, 'Enquete respondida com sucesso.')

    """
        enquete_dados = [
            categoria_dados = {
                nome: "Nome da categoria",
                grupos_perguntas: [ #Perguntas agrupadas em discursivas e objetivas de mesma opção
                    grupo_perguntas = {
                        objetiva: True ou False # se o grupo é de perguntas objetivas ou discursivas
                        perguntas: [] #lista de perguntas do grupo
                    }
                ]
            }
        ]
    """
    enquete_dados = list()
    for categoria in enquete.get_perguntas_agrupadas_por_categoria():
        categoria_dados = dict()
        categoria_dados["nome"] = categoria.texto
        categoria_dados["orientacao"] = categoria.orientacao
        grupos_perguntas = list()
        opcoes_anteriores = None
        grupo_perguntas = dict()
        grupo_perguntas["perguntas"] = list()
        grupo_perguntas["objetiva"] = None
        for pergunta in categoria.perguntas.all():
            opcoes = pergunta.get_opcoes()
            if not opcoes_anteriores:
                opcoes_anteriores = opcoes

            if grupo_perguntas["objetiva"] != pergunta.objetiva or opcoes.exclude(id__in=opcoes_anteriores):
                if grupo_perguntas["perguntas"]:
                    grupos_perguntas.append(grupo_perguntas)

                grupo_perguntas = dict()
                grupo_perguntas["perguntas"] = list()
                grupo_perguntas["objetiva"] = pergunta.objetiva

            pergunta.resposta = pergunta.get_resposta(request.user.get_vinculo())
            if not pergunta.resposta:
                pergunta.resposta = request.POST.get('{}'.format(pergunta.id)) or ''
                if pergunta.objetiva and pergunta.resposta:
                    if pergunta.multipla_escolha:
                        pergunta.resposta = [int(resp) for resp in request.POST.getlist('{}'.format(pergunta.id))]
                    else:
                        pergunta.resposta = int(pergunta.resposta)

            grupo_perguntas["perguntas"].append(pergunta)
            opcoes_anteriores = opcoes

        grupos_perguntas.append(grupo_perguntas)
        categoria_dados["grupos_perguntas"] = grupos_perguntas
        enquete_dados.append(categoria_dados)

    return locals()


@rtr()
@login_required()
def publicar_enquete(request, id):
    enquete = get_object_or_404(Enquete, pk=id)
    if not enquete.eh_responsavel(request.user) or not enquete.pode_publicar():
        raise PermissionDenied

    enquete.publicada = True
    enquete.save()
    return httprr('/enquete/enquete/{:d}/'.format(enquete.id), 'Enquete publicada com sucesso.')


@rtr()
@login_required()
def despublicar_enquete(request, id):
    enquete = get_object_or_404(Enquete, pk=id)
    if not enquete.eh_responsavel(request.user):
        raise PermissionDenied

    enquete.publicada = False
    enquete.save()
    return httprr('/enquete/enquete/{:d}/'.format(enquete.id), 'Enquete despublicada com sucesso.')


@rtr()
@login_required()
def ver_resultados(request, id):
    enquete = get_object_or_404(Enquete, pk=id)
    title = f'Resultados da Enquete: {enquete.titulo}'
    if not enquete.eh_responsavel(request.user):
        raise PermissionDenied

    form = FiltrarRespostasForm(request.GET or None, enquete=enquete)
    if form.is_valid():
        participantes = form.get_participantes()
        if form.cleaned_data.get('exportar_xls'):
            return tasks.exportar_resultado_to_xls(enquete, participantes)
        else:
            return tasks.processar_respostas_enquete(request, enquete, title)

    return locals()


@rtr()
@login_required()
def ver_publico(request, enquete_id):
    enquete = get_object_or_404(Enquete, pk=enquete_id)
    title = 'Público da Enquete: {}'.format(enquete.titulo)
    eh_responsavel_enquete = enquete.eh_responsavel(request.user)
    vinculos = enquete.vinculos_publico.all().order_by('pessoa__nome')
    form = BuscarPublicoForm(request.GET or None, enquete=enquete)
    if form.is_valid():
        vinculos = form.processar()

    return locals()


@rtr()
@login_required()
def atualizar_publico(request, enquete_id):
    enquete = get_object_or_404(Enquete, pk=enquete_id)
    if not enquete.eh_responsavel(request.user):
        raise PermissionDenied

    enquete.save()
    return httprr('/enquete/ver_publico/{:d}/'.format(enquete.id), 'Público da enquete {} foi atualizado com sucesso.'.format(enquete))
