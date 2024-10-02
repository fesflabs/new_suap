# -*- coding: utf-8 -*-
from django.core.exceptions import PermissionDenied

# Create your views here.
from djtools.templatetags.filters import format_
from djtools.utils import group_required, rtr, httprr, XlsResponse
from edu.models import Aluno, SituacaoMatricula
from egressos.forms import CategoriaForm, PerguntaForm, OpcaoForm, CopiarOpcaoForm, AtualizacaoCadastralForm, ResponderBlocoForm, PublicarPesquisaForm, ClonarPesquisaForm
from egressos.models import Pesquisa, Categoria, Pergunta, Opcao, Resposta
from django.shortcuts import get_object_or_404


@rtr()
@group_required('Gerente Sistêmico de Extensão')
def pesquisa(request, pk):
    obj = get_object_or_404(Pesquisa, pk=pk)
    title = obj

    return locals()


@rtr()
@group_required('Gerente Sistêmico de Extensão')
def cadastrar_categoria(request, pk, categoria_pk=None):
    pesquisa = get_object_or_404(Pesquisa, pk=pk)
    title = 'Cadastro de Categoria'
    if categoria_pk:
        obj = get_object_or_404(Categoria, pk=categoria_pk)
    form = CategoriaForm(request=request, instance=categoria_pk and obj or Categoria(pesquisa=pesquisa), data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Categoria registrada com sucesso.')

    return locals()


@rtr()
@group_required('Gerente Sistêmico de Extensão')
def cadastrar_pergunta(request, pk, pergunta_pk=None):
    pesquisa = get_object_or_404(Pesquisa, pk=pk)
    title = 'Cadastro de Pergunta'
    if pergunta_pk:
        obj = get_object_or_404(Pergunta, pk=pergunta_pk)
    form = PerguntaForm(request=request, instance=pergunta_pk and obj or Pergunta(pesquisa=pesquisa), data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Pergunta registrada com sucesso.')

    return locals()


@rtr()
@group_required('Gerente Sistêmico de Extensão')
def cadastrar_opcao(request, pk, opcao_pk=None):
    pergunta = get_object_or_404(Pergunta, pk=pk)
    title = 'Cadastro de Opção de Pergunta'
    if opcao_pk:
        obj = get_object_or_404(Opcao, pk=opcao_pk)
    form = OpcaoForm(request=request, instance=opcao_pk and obj or Opcao(pergunta=pergunta), data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('..', 'Opção de pergunta registrada com sucesso.')

    return locals()


@rtr()
@group_required('Gerente Sistêmico de Extensão')
def copiar_opcoes(request, pk):
    obj = get_object_or_404(Pergunta, pk=pk)
    title = 'Copiar Opções de Resposta de uma pergunta anterior'
    form = CopiarOpcaoForm(request=request, pergunta_destino=obj, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        if form.processar():
            return httprr('..', 'Opções de resposta copiadas com sucesso.')
        else:
            return httprr('..', 'Falha ao copiar.')

    return locals()


@rtr()
@group_required('Aluno')
def atualizacao_cadastral(request, pk):
    obj = get_object_or_404(Pesquisa, pk=pk)
    if not obj.esta_em_periodo_de_resposta():
        raise PermissionDenied
    aluno = get_object_or_404(Aluno, matricula=request.user.username, situacao__id__in=[SituacaoMatricula.FORMADO, SituacaoMatricula.CONCLUIDO])
    title = 'Atualização Cadastral do Egresso'
    form = AtualizacaoCadastralForm(request=request, instance=aluno, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        bloco1 = Categoria.objects.get(pesquisa=obj, ordem=1)
        return httprr('/egressos/responder_pesquisa_egressos/bloco/{}/{}/'.format(obj.pk, bloco1.pk), 'Atualização cadastral realizada com sucesso.')
    return locals()


@rtr()
@group_required('Aluno')
def responder_bloco(request, pk, pk_categoria):
    obj = get_object_or_404(Pesquisa, pk=pk)
    if not obj.esta_em_periodo_de_resposta():
        raise PermissionDenied
    aluno = get_object_or_404(Aluno, matricula=request.user.username, situacao__id__in=[SituacaoMatricula.FORMADO, SituacaoMatricula.CONCLUIDO])
    categoria = get_object_or_404(Categoria, pk=pk_categoria)
    title = 'Responder bloco: {}'.format(categoria)
    form = ResponderBlocoForm(request=request, categoria=categoria, data=request.POST or None)
    ultimo_bloco = obj.get_ultimo_bloco()
    if request.method == 'POST' and form.is_valid():
        if form.save():
            if obj.get_ultimo_bloco().pk == categoria.pk:
                return httprr('/', 'Obrigado por responder esta pesquisa. Você pode ver suas respostas no menu Egressos -> Pesquisas de Egresso Respondidas.')
            else:
                proximo_bloco = obj.get_proximo_bloco(aluno=aluno, bloco_atual=categoria)
                return httprr(
                    '/egressos/responder_pesquisa_egressos/bloco/{}/{}/'.format(obj.pk, proximo_bloco.pk),
                    'Bloco <strong>{}</strong> respondido com sucesso.'.format(categoria.titulo),
                )
        else:
            return httprr('..', 'Falha.')

    return locals()


@rtr()
@group_required('Gerente Sistêmico de Extensão')
def publicar_pesquisa(request, pk):
    obj = get_object_or_404(Pesquisa, pk=pk)
    title = 'Publicar Pesquisa: {}'.format(obj.titulo)
    form = PublicarPesquisaForm(request=request, instance=obj, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        return httprr('/egressos/pesquisa/{}/'.format(obj.pk), 'A pesquisa foi publicada e foram enviados os convites ' 'para os alunos alvo.')
    return locals()


@rtr()
@group_required('Gerente Sistêmico de Extensão')
def gerar_planilha_alunos_alvo(request, pk):
    obj = get_object_or_404(Pesquisa, pk=pk)
    rows = [['#', 'Matrícula', 'Nome', 'Curso', 'Diretoria', 'Campus', 'Situação', 'E-mail']]
    count = 0
    for aluno in obj.get_alunos_alvo():
        count += 1
        row = [
            count,
            format_(aluno.matricula),
            format_(aluno.pessoa_fisica.nome),
            format_(aluno.curso_campus),
            format_(aluno.curso_campus.diretoria),
            format_(aluno.curso_campus.diretoria.setor.uo),
            format_(aluno.situacao),
            format_(aluno.pessoa_fisica.email_secundario),
        ]
        rows.append(row)
    return XlsResponse(rows)


@rtr()
@group_required('Aluno')
def pesquisas_respondidas(request):
    title = 'Pesquisas Respondidas'
    pesquisas = Pesquisa.objects.filter(pergunta__resposta__aluno__matricula=request.user.username).distinct()
    for pesquisa in pesquisas:
        pesquisa.bloco1 = Categoria.objects.get(pesquisa=pesquisa, ordem=1)
    return locals()


@rtr()
@group_required('Gerente Sistêmico de Extensão')
def reenviar_convites_alunos_nao_respondentes(request, pk):
    obj = get_object_or_404(Pesquisa, pk=pk)
    obj.reenviar_convites_alunos_nao_respondentes()
    return httprr('..', 'Convites reenviados.')


@rtr()
@group_required('Gerente Sistêmico de Extensão')
def clonar_pesquisa(request, pk):
    obj = get_object_or_404(Pesquisa, pk=pk)
    title = 'Clonar Pesquisa: {}'.format(obj)
    form = ClonarPesquisaForm(request=request, titulo='[Clonada]{}'.format(obj.titulo), descricao='[Clonada]{}'.format(obj.descricao), pesquisa=obj, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        pesquisa_clonada = form.processar()
        return httprr('/egressos/pesquisa/{}/'.format(pesquisa_clonada.pk), 'Pesquisa clonada com sucesso.')
    return locals()


@rtr()
@group_required('Aluno')
def ver_respostas_pesquisa(request, pk):
    obj = get_object_or_404(Pesquisa, pk=pk)
    title = 'Ver respostas da pesquisa: {}'.format(obj)
    respostas = Resposta.objects.filter(aluno__matricula=request.user.username, pergunta__pesquisa=obj).order_by('pergunta__categoria__ordem')
    return locals()


@rtr()
@group_required('Gerente Sistêmico de Extensão')
def exportar_respostas(request, pk):
    obj = get_object_or_404(Pesquisa, pk=pk)
    primeiras_colunas = ['#', 'Matrícula', 'Nome', 'Curso', 'Diretoria', 'Campus', 'Situação', 'E-mail']
    perguntas = []
    for pergunta in obj.pergunta_set.all():
        perguntas.append(format_(pergunta.conteudo))
    rows = [primeiras_colunas + perguntas]

    alunos_respondentes = Aluno.objects.filter(id__in=Resposta.objects.filter(pergunta__pesquisa=obj).values_list('aluno__id', flat=True).distinct())
    count = 0
    for aluno in alunos_respondentes:
        count += 1
        row = [
            count,
            format_(aluno.matricula),
            format_(aluno.pessoa_fisica.nome),
            format_(aluno.curso_campus),
            format_(aluno.curso_campus.diretoria),
            format_(aluno.curso_campus.diretoria.setor.uo),
            format_(aluno.situacao),
            format_(aluno.pessoa_fisica.email_secundario),
        ]
        for pergunta in obj.pergunta_set.all():
            resposta_da_pergunta = Resposta.objects.filter(aluno=aluno, pergunta=pergunta)
            if resposta_da_pergunta.exists():
                if pergunta.eh_objetiva():
                    if resposta_da_pergunta[0].resposta_subjetiva:
                        row.append(format_('{} {}'.format(format_(resposta_da_pergunta[0].opcoes.all()), resposta_da_pergunta[0].resposta_subjetiva)))
                    else:
                        row.append(format_(resposta_da_pergunta[0].opcoes))
                else:
                    row.append(format_(resposta_da_pergunta[0].resposta_subjetiva))
            else:
                row.append('')
        rows.append(row)
    return XlsResponse(rows, encoding='UTF-8')
