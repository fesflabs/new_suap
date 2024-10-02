# -*- coding: utf-8 -*-
import datetime

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.shortcuts import get_object_or_404

from djtools import layout
from djtools.templatetags.filters import format_
from djtools.utils import XlsResponse, httprr, permission_required, rtr
from remanejamento.forms import (AvaliadorInscricaoFormFactory, CoordenadorInscricaoEditarFormFactory, DisciplinaForm,
                                 DisciplinaItemForm, EditalRecursoForm, EditalRecursoRespostaForm, InscreverFormFactory,
                                 InscricaoRecursoForm, InscricaoRespostaRecursoForm)
from remanejamento.models import Disciplina, Edital, EditalRecurso, Inscricao
from rh.models import UnidadeOrganizacional


@layout.info()
def index_infos(request):
    infos = list()

    if request.user.eh_servidor:
        servidor = request.user.get_relacionamento()
        for recurso in Edital.get_em_periodo_recurso_edital_servidor(servidor):
            infos.append(dict(url=recurso.get_url_recurso, titulo='Recurso ao Edital {}.'.format(recurso.titulo)))

        for inscricao in Inscricao.get_em_periodo_cancelamento_servidor(servidor):
            infos.append(dict(url='/admin/remanejamento/inscricao/',
                              titulo='Cancelamento de Inscrição {}.'.format(inscricao.edital.titulo)))

        for inscricao in Inscricao.get_em_periodo_recurso_servidor(servidor):
            infos.append(dict(url=inscricao.get_absolute_url(),
                              titulo=f'Recurso ao Resultado da Inscrição {inscricao} do Edital {inscricao.edital}.'))

    return infos


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()

    if request.user.eh_servidor:
        servidor = request.user.get_relacionamento()
        for edital in Edital.get_em_periodo_de_inscricao_servidor(servidor):
            inscricoes.append(dict(url=edital.get_url_inscrever,
                                   titulo='Inscrever-se para Remanejamento: <strong>{}</strong>.'.format(
                                       edital.titulo)))
    return inscricoes


@rtr()
@login_required()
def recurso_edital(request, edital_pk):
    edital = get_object_or_404(Edital, pk=edital_pk)
    title = f"Recurso ao {edital.titulo}"
    servidor = request.user.get_relacionamento()
    if not servidor.eh_servidor or not edital.is_em_periodo_de_recurso_edital_servidor(servidor):
        raise PermissionDenied("Acesso negado.")

    form = EditalRecursoForm(request.POST or None, id_edital=edital_pk)
    if form.is_valid():
        recurso = EditalRecurso()
        recurso.edital = form.cleaned_data['edital']
        recurso.recurso_texto = form.cleaned_data['recurso_texto']
        recurso.servidor = servidor
        recurso.save()
        return httprr("/admin/remanejamento/editalrecurso/", "Recurso cadastrado com sucesso.")

    return locals()


@rtr()
@login_required()
def visualizar_recurso_edital(request, recurso_pk):
    recurso = get_object_or_404(EditalRecurso, pk=recurso_pk)
    title = f"Recurso ao {recurso.edital}"
    exibir_resposta_recurso = recurso.pode_exibir_resposta_recurso_edital(request.user)
    servidor_logado = request.user.get_relacionamento()
    sou_coordenador = recurso.edital.coordenadores.filter(pk=request.user.pk).exists()
    if recurso.servidor == servidor_logado or sou_coordenador:
        if sou_coordenador and not recurso.edital.is_pode_exibir_resultado_recurso():
            form = EditalRecursoRespostaForm(request.POST or None, instance=recurso)
            if form.is_valid():
                recurso.recurso_resposta = form.cleaned_data['recurso_resposta']
                recurso.dh_resposta = datetime.datetime.now()
                recurso.recurso_respondido = True
                recurso.save()

                return httprr("/admin/remanejamento/editalrecurso/", "Resposta ao Recurso cadastrada com sucesso.")

        return locals()
    raise PermissionDenied("Acesso negado.")


@rtr()
@login_required()
def inscrever(request, edital_pk):
    # Se não tem inscrição, vamos verificar se ainda está no período
    edital = get_object_or_404(Edital, pk=edital_pk)
    if not request.user.eh_servidor or not edital.is_em_periodo_de_inscricao_servidor(
            request.user.get_relacionamento()):
        raise PermissionDenied('Edital não está em período de inscrição.')

    title = 'Inscrição para Edital de Remanejamento'
    FormClass = InscreverFormFactory(edital, request.user)
    form = FormClass(request.POST or None, request.FILES or None)
    if form.is_valid():
        inscricao = form.save()
        return httprr(f'/remanejamento/inscricao/{inscricao.pk}/', 'Inscrição realizada com sucesso.')
    return locals()


@rtr()
@login_required()
def inscricao(request, inscricao_pk):
    inscricao = get_object_or_404(Inscricao, pk=inscricao_pk)
    title = f'Comprovante de Inscrição #{inscricao_pk}'
    pode_ver = inscricao.pode_ver(request.user)
    if not pode_ver:
        raise PermissionDenied('Você não tem permissão para ver a página solicitada.')

    pode_mudar_status = inscricao.pode_mudar_status(request.user)
    pode_avaliar = inscricao.pode_avaliar(request.user)
    pode_cadastrar_recurso = inscricao.pode_cadastrar_recurso(request.user)
    avaliador_pode_habilitar = inscricao.avaliador_pode_habilitar(request.user)
    pode_ver_parecer = inscricao.pode_ver_parecer(request.user)
    pode_ver_resultado_recurso = inscricao.pode_ver_resultado_recurso(request.user)
    pode_excluir_recurso = inscricao.pode_excluir_recurso(request.user)
    pode_desistir = inscricao.is_pode_desistir(request.user)
    eh_coordenador = request.user.is_superuser or (request.user in inscricao.edital.coordenadores.all())
    eh_avaliador = inscricao.disciplina and request.user in inscricao.disciplina.avaliadores.all()

    # tratamento diferenciado para respostas a recursos de TAE's
    pode_responder_recurso_adm = eh_coordenador and inscricao.recurso_texto and not inscricao.avaliacao_recurso
    if pode_responder_recurso_adm:
        form_recurso_resposta = InscricaoRespostaRecursoForm(request.POST or None, instance=inscricao)
        if form_recurso_resposta.is_valid():
            form_recurso_resposta.save()
            return httprr(f'/remanejamento/inscricao/{inscricao.pk}/', 'Resposta ao recurso do resultado parcial cadastrado com sucesso.')

    if pode_mudar_status:
        CoordenadorInscricaoEditarForm = CoordenadorInscricaoEditarFormFactory(inscricao)
        form_coordenador = CoordenadorInscricaoEditarForm(request.POST or None, instance=inscricao)
        if form_coordenador.is_valid():
            form_coordenador.save()
            return httprr(f'/remanejamento/inscricao/{inscricao.pk}/', 'Inscrição alterada com sucesso!')

    if pode_avaliar:
        AvaliadorInscricaoForm = AvaliadorInscricaoFormFactory(inscricao)
        if request.method == 'POST' and 'observacao' in request.POST:
            form_avaliador = AvaliadorInscricaoForm(data=request.POST)
            if form_avaliador.is_valid():
                form_avaliador.save()
            return httprr(f'/remanejamento/inscricao/{inscricao.pk}/', 'Inscrição avaliada com sucesso!')
        else:
            form_avaliador = AvaliadorInscricaoForm()

    if pode_cadastrar_recurso:
        form_recurso = InscricaoRecursoForm(request.POST or None, instance=inscricao)
        if form_recurso.is_valid():
            form_recurso.save()
            return httprr(f'/remanejamento/inscricao/{inscricao.pk}/', 'Recurso ao resultado cadastrado com sucesso.')
    return locals()


@login_required()
def inscricao_desistir(request, inscricao_pk):
    inscricao = get_object_or_404(Inscricao, pk=inscricao_pk)
    if not inscricao.is_pode_desistir:
        raise PermissionDenied('Você não tem permissão para ver a página solicitada.')

    inscricao.efetivar_desistencia()

    return httprr(f'/remanejamento/inscricao/{inscricao.pk}/')


@login_required()
@rtr()
def inscricao_imprimir(request, inscricao_pk):
    inscricao = get_object_or_404(Inscricao, pk=inscricao_pk)
    pode_imprimir = request.user.is_superuser or request.user in inscricao.edital.coordenadores.all() or request.user in inscricao.disciplina.avaliadores.all()

    if not pode_imprimir:
        raise PermissionDenied('Você não tem permissão para ver a página solicitada.')

    return locals()


@login_required()
def inscricao_excluir_recurso(request, inscricao_pk):
    inscricao = get_object_or_404(Inscricao, pk=inscricao_pk)
    if not inscricao.pode_excluir_recurso(request.user):
        raise PermissionDenied('Você não tem permissão para ver a página solicitada.')

    inscricao.recurso_texto = ""
    inscricao.save()

    return httprr(f'/remanejamento/inscricao/{inscricao.pk}/')


@login_required()
def inscricoes_csv(request, edital_pk):
    edital = get_object_or_404(Edital, pk=edital_pk)

    cabecalho = [
        '#',
        'Horário',
        'Disciplina Inscrita',
        'Disciplina de Ingresso',
        'Anexo',
        'Matrícula',
        'Nome',
        'Nascimento',
        'E-mail',
        'Início Exercício',
        'Início de Exercício no Cargo(SUAP)',
        'DOU - Número',
        'DOU - Data',
        'DOU - Página',
        'DOU - Sessão',
        'DOU - Classificação Concurso',
        'DOU - Jornada de Trabalho',
        'Lotação SIAPE Atual',
        'Exercício SIAPE Atual',
        'Texto do recurso',
        'Parecer do recurso',
        'Dias em Serviço',
        'Dias em Serviço(via PCA)',
        'Cargo/Área',
        'Matricula_Substituto',
        'Situação da Inscrição',
    ]

    campi = UnidadeOrganizacional.objects.suap().order_by('setor__sigla')
    for campus in campi:
        cabecalho.append(str(campus))
    dados = [cabecalho]

    count = 0
    for inscricao in edital.inscricao_set.filter(confirmada=True).order_by('id'):
        servidor = inscricao.servidor
        matriculas_substituto = servidor.get_matriculas_por_cpf().filter(eh_docente=True).values_list('matricula',
                                                                                                      flat=True)

        cargo_area = None
        if servidor.cargo_emprego_area:
            cargo_area = servidor.cargo_emprego_area
        else:
            cargo_area = servidor.cargo_emprego.nome

        count += 1
        item = [
            count,
            inscricao.horario,
            inscricao.disciplina and inscricao.disciplina.descricao or '-',
            servidor.disciplina_ingresso,
            inscricao.anexo and inscricao.anexo.name or '-',
            servidor.matricula,
            inscricao.servidor.pessoa_fisica.nome,
            inscricao.servidor.pessoa_fisica.nascimento_data,
            inscricao.servidor.pessoa_fisica.email,
            inscricao.inicio_exercicio,
            servidor.data_inicio_exercicio_no_cargo,
            inscricao.dou_numero,
            inscricao.dou_data.year > 1950 and inscricao.dou_data or '-',  # evita erros de conversao de data
            inscricao.dou_pagina,
            inscricao.dou_sessao,
            inscricao.classificacao_concurso,
            inscricao.jornada_trabalho,
            servidor.setor_lotacao and servidor.setor_lotacao.uo or '-',
            servidor.setor_exercicio and servidor.setor_exercicio.uo or '-',
            inscricao.recurso_texto or '-',
            inscricao.avaliacao_recurso or '-',
            servidor.tempo_servico_no_cargo(inscricao.edital.inicio_inscricoes.date()).days,
            servidor.tempo_servico_no_cargo_via_pca(inscricao.edital.inicio_inscricoes.date()).days,
            cargo_area,
            format_(matriculas_substituto),
            inscricao.avaliacao_status,
        ]
        for campus in campi:
            inscricao_item = inscricao.inscricaoitem_set.filter(campus=campus)
            item.append(inscricao_item and inscricao_item[0].preferencia or '-')
        dados.append(item)
    return XlsResponse(dados)


@rtr()
@login_required()
@permission_required("remanejamento.add_disciplina")
def adicionar_disciplinas(request, edital_pk):
    edital = get_object_or_404(Edital, pk=edital_pk)
    if not request.user in edital.coordenadores.all() and not request.user.is_superuser:
        raise PermissionDenied()
    form = DisciplinaForm(request.POST or None, id_edital=edital_pk)
    if form.is_valid():
        disciplinas = form.cleaned_data['disciplinas']
        edital = form.cleaned_data['edital']
        for disciplina in disciplinas:
            Disciplina.objects.get_or_create(descricao=disciplina.descricao, edital=Edital.objects.get(id=edital_pk))
        return httprr('/admin/remanejamento/disciplina/', 'Disciplinas cadastradas com sucesso.')

    return locals()


@rtr()
@login_required()
def adicionar_disciplina_itens(request, edital_pk):
    if not request.user.is_superuser:
        raise PermissionDenied()

    edital = get_object_or_404(Edital, pk=edital_pk)
    if request.method == 'POST':
        form = DisciplinaItemForm(request.POST)
        if form.is_valid():
            form.save(edital)
            return httprr('/admin/remanejamento/disciplina/', 'Itens cadastrados com sucesso.')
    else:
        form = DisciplinaItemForm()
    return locals()


@rtr()
@login_required()
def inscricao_nao_habilitada(request, inscricao_pk):
    inscricao = get_object_or_404(Inscricao, pk=inscricao_pk)
    if inscricao.avaliador_pode_habilitar(request.user):
        inscricao.avaliacao_status = 'Não habilitado'
        inscricao.save()
    return httprr(f'/remanejamento/inscricao/{inscricao.pk}/', 'Inscrição alterada com sucesso!')
