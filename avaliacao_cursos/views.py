# -*- coding: utf-8 -*-
import math
from datetime import datetime, date
from django.db.models.expressions import Case, Value, When

import xlwt
from django.contrib.auth.decorators import login_required, permission_required
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404

from avaliacao_cursos.forms import (
    GrupoPerguntaForm,
    PerguntaForm,
    RespondentesForm,
    OpcaoRespostaPerguntaForm,
    OpcoesRespostaPerguntaForm,
    ResultadoForm,
    AdicionarQuestionarioForm,
    RelatorioForm,
)
from avaliacao_cursos.models import Questionario, GrupoPergunta, Pergunta, Respondente, Resposta, AvaliacaoComponenteCurricular, OpcaoRespostaPergunta, Segmento, Avaliacao, JustificativaAvaliacaoComponenteCurricular
from comum.models import Configuracao
from djtools import layout
from djtools import forms
from djtools.html.graficos import PieChart, StackedGroupedColumnChart, BarChart
from djtools.utils import rtr, httprr, group_required
from edu.models import ProfessorDiario
from edu.models.alunos import Aluno
from edu.models.cadastros_gerais import Nucleo, Modalidade
from edu.models.cursos import CursoCampus, ComponenteCurricular, Matriz, Componente
from edu.models.diretorias import Diretoria
from edu.utils import TabelaBidimensional, TabelaResumoAluno
from rh.models import UnidadeOrganizacional, Setor


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()
    qs = Respondente.objects.filter(
        vinculo=request.user.get_vinculo(),
        questionario__data_inicio__lte=datetime.today(),
        questionario__data_termino__gte=datetime.today(),
        finalizado=False).annotate(
            tem_resposta=Case(
                When(resposta__isnull=False, then=Value(True)), default=Value(False),),
            tem_avaliacao_componente_curricular=Case(
                When(avaliacaocomponentecurricular__isnull=False, then=Value(True)), default=Value(False),))
    for questionario in qs.order_by('id').distinct():
        titulo_prefix = 'Continue respondendo o' if questionario.tem_resposta or questionario.tem_avaliacao_componente_curricular else 'Você precisa responder o'
        titulo = f'{titulo_prefix} <strong>Questionário de Avaliação de Cursos - {questionario.segmento}</strong>.'.format(titulo_prefix, questionario.segmento)
        inscricoes.append(
            dict(
                url=f'/avaliacao_cursos/responder/{questionario.pk}/',
                titulo=titulo,
                prazo=questionario.questionario.data_termino,
            )
        )
    return inscricoes


@rtr()
@login_required
def resultado(request):
    title = 'Resultado'
    form = ResultadoForm(request.GET or None)
    if form.is_valid():
        respondentes = form.processar()
        qtd_respondentes = respondentes.count()
        qtd_finalizadas = respondentes.filter(finalizado=True).count()

    return locals()


@rtr()
@login_required
def avaliacao(request, pk):
    url = '/avaliacao_cursos/questionario/{}/'.format(pk)
    obj = get_object_or_404(Avaliacao, pk=pk)
    title = str(obj)
    if request.GET.get('tab') == 'monitoramento':
        uos = UnidadeOrganizacional.objects.suap().all()
        segmentos = Segmento.objects.all()
        modalidades = Modalidade.objects.filter(pk__in=obj.questionario_set.values_list('modalidades', flat=True).distinct())
        estatisticas = {}
        estatisticas_discente = {}
        for uo in uos:
            estatistica = []
            estatistica_discente = []
            for segmento in segmentos:
                estatistica.append(obj.get_qtd_respondentes(uo, segmento))
                estatistica.append(obj.get_qtd_iniciado(uo, segmento))
                estatistica.append(obj.get_qtd_finalizados(uo, segmento))
            for modalidade in modalidades:
                estatistica_discente.append(obj.get_qtd_respondentes_discente(uo, modalidade))
                estatistica_discente.append(obj.get_qtd_iniciado_discente(uo, modalidade))
                estatistica_discente.append(obj.get_qtd_finalizados_discente(uo, modalidade))
            estatisticas[uo.sigla] = estatistica
            estatisticas_discente[uo.sigla] = estatistica_discente
    return locals()


@rtr()
@group_required('Avaliador de Cursos')
def adicionar_questionario(request, pk, questionario_pk=None):
    title = 'Adicionar Questionário'
    url = '/avaliacao_cursos/questionario/{}/'.format(pk)
    obj = get_object_or_404(Avaliacao, pk=pk)
    questionario = questionario_pk and Questionario.objects.get(pk=questionario_pk) or Questionario()
    questionario.avaliacao = obj
    form = AdicionarQuestionarioForm(data=request.POST or None, instance=questionario)
    if form.is_valid():
        questionario = form.save(True)
        return httprr('..', 'Questionário salvo com sucesso.')

    return locals()


@rtr()
@login_required
def questionario(request, pk):
    title = 'Visualizar Questionário'
    url = '/avaliacao_cursos/questionario/{}/'.format(pk)
    obj = get_object_or_404(Questionario, pk=pk)

    qtd_respondentes = obj.respondente_set.count()
    qtd_finalizados = obj.respondente_set.filter(finalizado=True).count()
    qtd_iniciado = Resposta.objects.filter(respondente__questionario=obj).values_list('respondente').order_by('respondente').distinct().count()

    if 'identificar_respondentes' in request.GET:
        obj.identificar_respondentes(excluir=False)
        return httprr(url, 'Respondentes identificados com sucesso.')

    if 'reprocessar_respondentes' in request.GET:
        obj.identificar_respondentes(excluir=True)
        return httprr(url, 'Respondentes reprocessados com sucesso.')

    if 'grupo_pergunta_id' in request.GET:
        pk_grupo_pergunta = request.GET.get('grupo_pergunta_id')
        grupo_pergunta = get_object_or_404(GrupoPergunta, pk=pk_grupo_pergunta)
        grupo_pergunta.delete()
        return httprr(url, 'Grupo excluído com sucesso.')

    if 'pergunta_id' in request.GET:
        pk_pergunta = request.GET.get('pergunta_id')
        pergunta = get_object_or_404(Pergunta, pk=pk_pergunta)
        pergunta.delete()
        return httprr(url, 'Pergunta excluída com sucesso.')

    if not obj.respondente_set.filter(segmento=Segmento.ALUNO).exists():
        tabela_resumo = TabelaBidimensional('Quadro Resumo - Segmentos', obj.respondente_set.all(), vertical_model=Segmento, vertical_key='segmento')
    else:
        qs_alunos = Aluno.objects.filter(vinculos__in=obj.respondente_set.values_list('vinculo', flat=True))
        tabela_resumo = TabelaResumoAluno(qs_alunos)
    return locals()


@rtr()
@group_required('Avaliador de Cursos')
def adicionar_grupo_pergunta(request, questionario_pk, grupo_pergunta_pk=None):
    title = 'Adicionar Grupo de Pergunta'
    questionario = get_object_or_404(Questionario, pk=questionario_pk)

    instance = grupo_pergunta_pk and GrupoPergunta.objects.get(pk=grupo_pergunta_pk) or None
    form = GrupoPerguntaForm(data=request.POST or None, instance=instance)

    if form.is_valid():
        form.instance.questionario = questionario
        form.save()
        return httprr('..', 'Grupo adicionado com sucesso')
    return locals()


@rtr()
@group_required('Avaliador de Cursos')
def adicionar_pergunta(request, grupo_pergunta_pk, pergunta_pk=None):
    title = 'Adicionar Pergunta'
    grupo_pergunta = get_object_or_404(GrupoPergunta, pk=grupo_pergunta_pk)

    instance = pergunta_pk and Pergunta.objects.get(pk=pergunta_pk) or None
    form = PerguntaForm(data=request.POST or None, instance=instance)

    if form.is_valid():
        form.instance.grupo_pergunta = grupo_pergunta
        form.save()
        return httprr('..', 'Pergunta adicionada com sucesso')
    return locals()


@rtr()
@group_required('Avaliador de Cursos')
def adicionar_opcao_resposta(request, pergunta_pk, opcao_resposta_pk=None):
    title = 'Adicionar Opção de Resposta'
    pergunta = get_object_or_404(Pergunta, pk=pergunta_pk)

    instance = opcao_resposta_pk and OpcaoRespostaPergunta.objects.get(pk=opcao_resposta_pk) or None
    if opcao_resposta_pk:
        form = OpcaoRespostaPerguntaForm(data=request.POST or None, instance=instance)
        if form.is_valid():
            form.instance.pergunta = pergunta
            form.save()
            return httprr('..', 'Opção de Resposta adicionada com sucesso')
    else:
        form = OpcoesRespostaPerguntaForm(data=request.POST or None)
        if form.is_valid():
            form.save(pergunta)
            return httprr('..', 'Opção de Resposta adicionada com sucesso')
    return locals()


@rtr()
@login_required
def visualizar_respondentes(request, pk):
    title = 'Visualizar Respondentes'
    obj = get_object_or_404(Questionario, pk=pk)
    form = RespondentesForm(data=request.POST or None, questionario=obj)
    respondentes = obj.respondente_set.all().order_by('vinculo__pessoa__nome')

    if form.is_valid():
        respondentes = form.processar()

    return locals()


@rtr()
@permission_required('avaliacao_cursos.delete_questionario')
def reabrir(request, pk):
    obj = get_object_or_404(Respondente, pk=pk)
    obj.reabrir()
    return httprr('..', 'Questionário reaberto com sucesso.')


@rtr()
@login_required
def responder(request, pk):
    obj = get_object_or_404(Respondente, pk=pk)
    title = 'Responder Questionário de Avaliação de Cursos - {}'.format(obj.segmento)
    eh_previsualizacao = request.user.has_perm('avaliacao_cursos.change_avaliacao') and request.user.get_vinculo() != obj.vinculo
    if (date.today() > obj.questionario.data_termino) and not eh_previsualizacao:
        return httprr('/', 'O prazo para resposta da Avaliação foi expirado.', 'error')

    if not eh_previsualizacao:
        if not request.user.get_vinculo() == obj.vinculo:
            return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if request.user.get_vinculo() == obj.vinculo and obj.finalizado:
        return httprr('/', 'A avaliação já foi respondida.', 'error')

    qtd_perguntas = 0
    qtd_respondida = 0
    modalidades = []
    for i, modalidade in enumerate(obj.questionario.modalidades.all()):
        if i > 0:
            if i == obj.questionario.modalidades.count() - 1:
                modalidades.append(' e {}'.format(modalidade.descricao))
            else:
                modalidades.append(', {}'.format(modalidade.descricao))
        else:
            modalidades.append(modalidade.descricao)
    modalidades_str = ''.join(modalidades)

    form = forms.Form(data=request.POST or None)
    ids_perguntas_obrigatorias = Pergunta.objects.filter(grupo_pergunta__questionario=obj.questionario, obrigatoria=True).values_list('pk', flat=True)
    ids_componentes_ministrados = ProfessorDiario.objects.filter(professor__vinculo__id=obj.vinculo.id).values_list('diario__componente_curricular', flat=True)
    avaliacoes = AvaliacaoComponenteCurricular.objects.filter(respondente=obj).values_list(
        'carga_horaria', 'componente_curricular', 'sequencia_didatica', 'ementa_programa', 'regime_misto', 'justificativa'
    )
    respostas = dict()
    for carga_horaria, componente_curricular_pk, sequencia_didatica, ementa_programa, regime_misto, justificativa in avaliacoes:
        respostas[componente_curricular_pk] = dict(
            carga_horaria=carga_horaria, sequencia_didatica=sequencia_didatica, ementa_programa=ementa_programa, regime_misto=regime_misto, justificativa=justificativa
        )
    matrizes = []
    justificativas = {
        (x, y): z for x, y, z in obj.justificativaavaliacaocomponentecurricular_set.values_list(
            'componente_curricular', 'campo', 'justificativa'
        )
    }
    for matriz in obj.get_matrizes():
        anual = matriz.matrizcurso_set.filter(curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL).exists()
        periodos = [1, 2, 3, 4] or list(range(1, matriz.qtd_periodos_letivos + 1))
        qs = matriz.componentecurricular_set.filter(periodo_letivo__in=periodos)
        colspan = matriz.qtd_periodos_letivos + 6
        nucleos = list()
        attrs = ('carga_horaria', 'sequencia_didatica', 'ementa_programa')
        for nucleo in Nucleo.objects.filter(pk__in=qs.values_list('nucleo', flat=True).distinct()):
            componentes_curriculares = []
            for componente_curricular in (
                qs.filter(nucleo=nucleo)
                .exclude(tipo__in=(ComponenteCurricular.TIPO_SEMINARIO, ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL))
                .order_by('componente__descricao')
                .distinct()
            ):
                componente_curricular.justificativa_1 = justificativas.get((componente_curricular.pk, 1))
                componente_curricular.justificativa_2 = justificativas.get((componente_curricular.pk, 2))
                componente_curricular.justificativa_3 = justificativas.get((componente_curricular.pk, 3))
                for attr in attrs:
                    if not eh_previsualizacao:
                        initial = componente_curricular.pk in respostas and respostas[componente_curricular.pk][attr] or None
                    else:
                        initial = None
                    field_name = '{}:::{}'.format(componente_curricular.pk, attr)
                    if attr == 'justificativa':
                        form.fields[field_name] = forms.CharField(required=False, initial=initial)
                    else:
                        form.fields[field_name] = forms.ChoiceField(choices=Pergunta.RESPOSTA_ESCALA_PADRAO_CHOICES, required=False, initial=initial)

                    if obj.segmento_id == Segmento.PROFESSOR:
                        if componente_curricular.pk in ids_componentes_ministrados:
                            form.fields[field_name].widget.attrs['data-required'] = 1
                        else:
                            form.fields[field_name].widget.attrs['readonly'] = True
                            form.fields[field_name].widget.attrs['disabled'] = 'disabled'
                    else:
                        form.fields[field_name].widget.attrs['data-required'] = 1

                    setattr(componente_curricular, attr, field_name)
                componentes_curriculares.append(componente_curricular)
            nucleos.append(('Núcleo {}'.format(nucleo), componentes_curriculares))

        componentes_curriculares = []
        for componente_curricular in qs.filter(tipo=ComponenteCurricular.TIPO_SEMINARIO).order_by('componente__descricao').distinct():
            for attr in attrs:
                if not eh_previsualizacao:
                    initial = componente_curricular.pk in respostas and respostas[componente_curricular.pk][attr] or None
                else:
                    initial = None
                field_name = '{}:::{}'.format(componente_curricular.pk, attr)
                if attr == 'justificativa':
                    form.fields[field_name] = forms.CharField(required=False, initial=initial)
                else:
                    form.fields[field_name] = forms.ChoiceField(choices=Pergunta.RESPOSTA_ESCALA_PADRAO_CHOICES, required=False, initial=initial)
                if obj.segmento_id == Segmento.PROFESSOR:
                    if componente_curricular.pk in ids_componentes_ministrados:
                        form.fields[field_name].widget.attrs['data-required'] = 1
                    else:
                        form.fields[field_name].widget.attrs['readonly'] = True
                        form.fields[field_name].widget.attrs['disabled'] = 'disabled'
                else:
                    form.fields[field_name].widget.attrs['data-required'] = 1

                setattr(componente_curricular, attr, field_name)
            componentes_curriculares.append(componente_curricular)
        nucleos.append(('Seminários', componentes_curriculares))

        componentes_curriculares = []
        for componente_curricular in qs.filter(tipo=ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL).order_by('componente__descricao').distinct():
            for attr in attrs:
                initial = componente_curricular.pk in respostas and respostas[componente_curricular.pk][attr] or None
                field_name = '{}:::{}'.format(componente_curricular.pk, attr)
                form.fields[field_name] = forms.ChoiceField(choices=Pergunta.RESPOSTA_ESCALA_PADRAO_CHOICES, required=False, initial=initial)
                setattr(componente_curricular, attr, field_name)
                if obj.segmento_id == Segmento.PROFESSOR:
                    if componente_curricular.pk in ids_componentes_ministrados:
                        form.fields[field_name].widget.attrs['data-required'] = 1
                    else:
                        form.fields[field_name].widget.attrs['readonly'] = True
                        form.fields[field_name].widget.attrs['disabled'] = 'disabled'
                else:
                    form.fields[field_name].widget.attrs['data-required'] = 1

            componentes_curriculares.append(componente_curricular)
        nucleos.append(('Prática Profissional', componentes_curriculares))

        matrizes.append((matriz.descricao, nucleos, anual))

    grupos_pergunta = []
    respostas_grupo_pergunta = dict()
    for pergunta_pk, resposta, multipla_escolha in Resposta.objects.filter(respondente=obj).values_list('pergunta__id', 'resposta', 'pergunta__multipla_escolha').distinct():
        if pergunta_pk in respostas_grupo_pergunta:
            if not type(respostas_grupo_pergunta[pergunta_pk]) == list:
                respostas_grupo_pergunta[pergunta_pk] = [respostas_grupo_pergunta[pergunta_pk], resposta]
            else:
                respostas_grupo_pergunta[pergunta_pk].append(resposta)
        else:
            if multipla_escolha:
                respostas_grupo_pergunta[pergunta_pk] = [resposta]
            else:
                respostas_grupo_pergunta[pergunta_pk] = resposta
    for grupo_pergunta in obj.questionario.grupopergunta_set.all():
        grupo_pergunta.perguntas = []
        for pergunta in grupo_pergunta.pergunta_set.all():
            initial = respostas_grupo_pergunta.get(pergunta.pk)
            pergunta.form_field_name = str(pergunta.pk)
            field = pergunta.get_form_field(initial=initial)
            form.fields[pergunta.form_field_name] = field
            if pergunta.obrigatoria:
                field.widget.attrs['data-required'] = 1
            grupo_pergunta.perguntas.append(pergunta)
        grupos_pergunta.append(grupo_pergunta)

    for field_name in form.fields:
        field = form.fields[field_name]
        if 'readonly' not in field.widget.attrs or not field.widget.attrs['readonly']:
            if field.widget.attrs.get('data-required'):
                qtd_perguntas += 1
                if field.initial:
                    qtd_respondida += 1

    percentual = math.ceil(qtd_perguntas and (100.0 * qtd_respondida / qtd_perguntas) or 0)

    # Validando as perguntas obrigatórias ao salvar e finalizar
    if '_save_and_finalize' in request.POST:
        for id in ids_perguntas_obrigatorias:
            if str(id) not in form.data:
                form.add_error(str(id), 'O Campo é Obrigatório.')

    if form.is_valid():
        finalizar = '_save_and_finalize' in request.POST

        novas_respostas = dict()
        for field_name in form.cleaned_data:
            valor = form.cleaned_data.get(field_name)

            if ':::' in field_name:
                componente_curricular.pk, attr = field_name.split(':::')
                if componente_curricular.pk not in novas_respostas:
                    novas_respostas[componente_curricular.pk] = dict(carga_horaria=None, sequencia_didatica=None, ementa_programa=None)
                novas_respostas[componente_curricular.pk][attr] = valor
            else:
                if not type(valor) in (list, tuple):
                    qs = Resposta.objects.filter(respondente=obj, pergunta=field_name)
                    if qs.exists():
                        qs.update(resposta=valor)
                    elif valor:
                        Resposta.objects.create(respondente=obj, pergunta_id=field_name, resposta=valor)
                else:
                    Resposta.objects.filter(respondente=obj, pergunta=field_name).delete()
                    for valor_opcao in valor:
                        Resposta.objects.create(respondente=obj, pergunta_id=field_name, resposta=valor_opcao)

        for componente_curricular_pk in novas_respostas:
            qs = AvaliacaoComponenteCurricular.objects.filter(respondente=obj, componente_curricular=componente_curricular_pk)
            if qs.exists():
                qs.update(**novas_respostas[componente_curricular_pk])
            else:
                if (
                    novas_respostas[componente_curricular_pk]['sequencia_didatica']
                    or novas_respostas[componente_curricular_pk]['ementa_programa']
                ):
                    novas_respostas[componente_curricular_pk].update(respondente=obj, componente_curricular_id=componente_curricular_pk)
                    AvaliacaoComponenteCurricular.objects.create(**novas_respostas[componente_curricular_pk])

        if finalizar:
            # Finalizando a avaliação
            obj.finalizado = finalizar
            obj.save()
            return httprr('/', 'Avaliação finalizada com sucesso.')
        else:
            return httprr('.', 'Avaliação parcialmente salva com sucesso.')
    return locals()


@rtr()
@login_required
def estatistica_avaliacao(request, pk):
    avaliacao = Avaliacao.objects.get(pk=pk)
    title = 'Relatório - {}'.format(avaliacao)
    form = RelatorioForm(avaliacao, data=request.POST or None)
    if form.is_valid():
        uos = form.cleaned_data.get('uos')
        segmento = form.cleaned_data.get('segmento')
        matriz = form.cleaned_data.get('matriz')
        modalidades = form.cleaned_data.get('modalidades')
        qs = Questionario.objects.filter(avaliacao=avaliacao, segmentos=segmento)
        if qs.exists():
            obj = qs[0]
            lista = ['?_=']
            lista.append('segmento={}'.format(segmento.pk))
            lista.append('uos={}'.format('-'.join([str(uo.pk) for uo in uos])))
            lista.append('modalidades={}'.format('-'.join([str(modalidade.pk) for modalidade in modalidades])))
            lista.append('matriz={}'.format(matriz and matriz.pk or ''))
            params = '&'.join(lista)

    return locals()


@rtr()
@login_required
def estatistica_avaliacao_componentes(request, pk):
    avaliacao = Avaliacao.objects.get(pk=pk)
    title = 'Relatório - {}'.format(avaliacao)
    form = RelatorioForm(avaliacao, data=request.POST or None)
    form.fields['segmento'].queryset = Segmento.objects.filter(pk__in=(Segmento.ALUNO, Segmento.PROFESSOR))
    if form.is_valid():
        uos = form.cleaned_data.get('uos')
        segmento = form.cleaned_data.get('segmento')
        matriz = form.cleaned_data.get('matriz')
        modalidades = form.cleaned_data.get('modalidades')
        qs = AvaliacaoComponenteCurricular.objects.filter(respondente__questionario__avaliacao=avaliacao)
        if modalidades:
            qs = qs.filter(componente_curricular__matriz__matrizcurso__curso_campus__modalidade__in=modalidades)
        if matriz:
            qs = qs.filter(componente_curricular__matriz=matriz)
        if uos:
            qs = qs.filter(componente_curricular__matriz__matrizcurso__curso_campus__diretoria__setor__uo__in=uos)
        if segmento:
            qs = qs.filter(respondente__segmento=segmento)
        componentes = Componente.objects.filter(pk__in=qs.order_by('componente_curricular__componente').values_list('componente_curricular__componente', flat=True).distinct())
    return locals()


@rtr()
@login_required
def estatistica_resposta(request, pk):
    title = 'Estatísticas de Respostas'
    pergunta = Pergunta.objects.get(pk=pk)
    respostas = pergunta.resposta_set.all()
    mostrar_filtros = True

    series = []

    subtitle = []
    uo_ids = None
    modalidade_ids = None
    matriz_id = None
    setor_id = None

    if '_' in request.GET:
        segmento_id = int(request.GET.get('segmento'))
        uo_ids = request.GET.get('uos') and request.GET.get('uos').split('-') or None
        modalidade_ids = request.GET.get('modalidades') and [int(x) for x in request.GET.get('modalidades').split('-')] or []
        matriz_id = request.GET.get('matriz') and int(request.GET.get('matriz')) or None
        respostas = respostas.filter(respondente__segmento=segmento_id)

        if uo_ids:
            respostas = respostas.filter(respondente__setor__uo__in=uo_ids)
        if segmento_id == Segmento.ALUNO:
            if modalidade_ids:
                ids_alunos = Aluno.objects.filter(curso_campus__modalidade__in=modalidade_ids).values_list('id', flat=True)
                respostas = respostas.filter(respondente__vinculo__tipo_relacionamento__model='aluno', respondente__vinculo__id_relacionamento__in=ids_alunos)
            if matriz_id:
                ids_alunos = Aluno.objects.filter(curso_campus__matrizcurso__matriz=matriz_id).values_list('id', flat=True)
                respostas = respostas.filter(respondente__vinculo__tipo_relacionamento__model='aluno', respondente__vinculo__id_relacionamento__in=ids_alunos)
        else:
            if modalidade_ids:
                respondente_pks = (
                    respostas.filter(respondente__vinculo__pessoa__pessoafisica__professor__professordiario__diario__turma__curso_campus__modalidade__in=modalidade_ids)
                    .order_by('respondente')
                    .values_list('respondente')
                    .distinct()
                )
                respostas = respostas.filter(respondente__in=respondente_pks)
            if matriz_id:
                respondente_pks = (
                    respostas.filter(respondente__vinculo__pessoa__pessoafisica__professor__professordiario__diario__turma__curso_campus__matrizcurso__matriz=matriz_id)
                    .order_by('respondente')
                    .values_list('respondente')
                    .distinct()
                )
                respostas = respostas.filter(respondente__in=respondente_pks)

        if uo_ids or modalidade_ids or matriz_id:
            mostrar_filtros = False

    else:
        setor_id = request.GET.get('setor', '')
        if setor_id:
            respostas = respostas.filter(respondente__setor=setor_id)
        segmento_id = request.GET.get('segmento', '')
        if segmento_id:
            segmento = Segmento.objects.get(pk=segmento_id)
            respostas = respostas.filter(respondente__segmento=segmento_id)

    for resposta in respostas.values_list('resposta', flat=True).order_by('resposta').distinct():
        series.append((resposta, respostas.filter(resposta=resposta).order_by('respondente').values_list('respondente').distinct().count()))

    total_respondentes = respostas.order_by('respondente').values_list('respondente').distinct().count()

    if pergunta.tipo_resposta != Pergunta.RESPOSTA_SUBJETIVA:

        if modalidade_ids:
            subtitle.append(', '.join([modalidade.descricao for modalidade in Modalidade.objects.filter(pk__in=modalidade_ids)]))
        if segmento_id:
            segmento = Segmento.objects.get(pk=segmento_id)
            subtitle.append(segmento.descricao)
        if matriz_id:
            matriz = Matriz.objects.get(pk=matriz_id)
            subtitle.append(matriz.descricao)
        if setor_id:
            setor = Setor.objects.get(pk=setor_id)
            subtitle.append(setor.sigla)
        if uo_ids:
            subtitle.append(', '.join([uo.sigla for uo in UnidadeOrganizacional.objects.suap().filter(pk__in=uo_ids)]))

        subtitle = ' - '.join(subtitle)

        if pergunta.multipla_escolha:
            plotOptions = {'column': {'dataLabels': {'enabled': 'true', 'color': 'white'}}}
            grafico = BarChart(
                'grafico',
                title=str(pergunta),
                subtitle=subtitle,
                minPointLength=0,
                data=series,
                plotOptions=plotOptions,
                tooltip=dict(valueSuffix=' de {}'.format(total_respondentes)),
            )
            grafico.plotOptions['series']['dataLabels']['enabled'] = 'true'
            grafico.plotOptions['series']['dataLabels']['padding'] = '0'
            grafico.plotOptions['series']['dataLabels']['format'] = '{y}'
            grafico.plotOptions['column']['dataLabels']['padding'] = '0'
        else:
            dataLabels_format = '<b>{point.name}</b>: {point.percentage:.0f} %'
            grafico = PieChart('grafico', title=str(pergunta), subtitle=subtitle, minPointLength=0, data=series, dataLabels_format=dataLabels_format)
        if 'setor' in request.GET:
            return HttpResponse(str(grafico))
    else:
        respostas = respostas.order_by('respondente__setor')

    if mostrar_filtros:
        setores = Setor.objects.filter(pk__in=list(respostas.order_by('respondente__setor').values_list('respondente__setor', flat=True))).distinct()
        segmentos = pergunta.grupo_pergunta.questionario.segmentos.all()

    return locals()


@rtr()
@login_required
def estatistica_grupo_resposta(request, pk):
    title = 'Estatísticas de Respostas'
    grupo_pergunta = GrupoPergunta.objects.get(pk=pk)
    series = []
    groups = []
    respostas = Resposta.objects.none()
    mostrar_filtros = True
    groups = [x for x, y in Pergunta.RESPOSTA_ESCALA_PADRAO_CHOICES[1:]]

    subtitle = []
    uo_ids = None
    modalidade_ids = None
    matriz_id = None
    setor_id = None
    segmento_id = None

    for pergunta in grupo_pergunta.pergunta_set.filter(tipo_resposta=Pergunta.RESPOSTA_ESCALA_PADRAO).all():
        series.append([pergunta.enunciado])
        respostas = pergunta.resposta_set.exclude(resposta='')

        if '_' in request.GET:
            segmento_id = int(request.GET.get('segmento'))
            uo_ids = request.GET.get('uos') and request.GET.get('uos').split('-') or None
            modalidade_ids = request.GET.get('modalidades').split('-')
            matriz_id = request.GET.get('matriz') and int(request.GET.get('matriz')) or None

            if uo_ids:
                respostas = respostas.filter(respondente__setor__uo__in=uo_ids)
            if segmento_id == Segmento.ALUNO:
                if modalidade_ids:
                    ids_alunos = Aluno.objects.filter(curso_campus__modalidade__in=modalidade_ids).values_list('id', flat=True)
                    respostas = respostas.filter(respondente__vinculo__tipo_relacionamento__model='aluno', respondente__vinculo__id_relacionamento__in=ids_alunos)
                if matriz_id:
                    ids_alunos = Aluno.objects.filter(curso_campus__matrizcurso__matriz=matriz_id).values_list('id', flat=True)
                    respostas = respostas.filter(respondente__vinculo__tipo_relacionamento__model='aluno', respondente__vinculo__id_relacionamento__in=ids_alunos)
            else:
                if modalidade_ids:
                    respondente_pks = (
                        respostas.filter(respondente__vinculo__pessoa__pessoafisica__professor__professordiario__diario__turma__curso_campus__modalidade__in=modalidade_ids)
                        .order_by('respondente')
                        .values_list('respondente')
                        .distinct()
                    )
                    respostas = respostas.filter(respondente__in=respondente_pks)
                if matriz_id:
                    respondente_pks = (
                        respostas.filter(respondente__vinculo__pessoa__pessoafisica__professor__professordiario__diario__turma__curso_campus__matrizcurso__matriz=matriz_id)
                        .order_by('respondente')
                        .values_list('respondente')
                        .distinct()
                    )
                    respostas = respostas.filter(respondente__in=respondente_pks)

            if uo_ids or modalidade_ids or matriz_id:
                mostrar_filtros = False
        else:
            setor_id = request.GET.get('setor', '')
            if setor_id:
                respostas = respostas.filter(respondente__setor=setor_id)
            segmento_id = request.GET.get('segmento', '')
            if segmento_id:
                respostas = respostas.filter(respondente__segmento=segmento_id)

        for resposta in groups:
            series[-1].append(respostas.filter(resposta=resposta).count())

    if modalidade_ids:
        subtitle.append(', '.join([modalidade.descricao for modalidade in Modalidade.objects.filter(pk__in=modalidade_ids)]))
    if segmento_id:
        segmento = Segmento.objects.get(pk=segmento_id)
        subtitle.append(segmento.descricao)
    if matriz_id:
        matriz = Matriz.objects.get(pk=matriz_id)
        subtitle.append(matriz.descricao)
    if setor_id:
        setor = Setor.objects.get(pk=setor_id)
        subtitle.append(setor.sigla)
    if uo_ids:
        subtitle.append(', '.join([uo.sigla for uo in UnidadeOrganizacional.objects.suap().filter(pk__in=uo_ids)]))

    subtitle = ' - '.join(subtitle)

    plotOptions = {'column': {'dataLabels': {'enabled': 'true', 'color': 'white'}}}
    grafico = StackedGroupedColumnChart('grafico', title=grupo_pergunta.descricao, subtitle=subtitle, data=series, groups=groups, plotOptions=plotOptions)
    grafico.plotOptions['series']['dataLabels']['enabled'] = 'true'
    grafico.plotOptions['series']['dataLabels']['padding'] = '0'
    grafico.plotOptions['series']['dataLabels']['format'] = '{percentage:.0f}%'
    grafico.plotOptions['column']['dataLabels']['padding'] = '0'

    if 'setor' in request.GET:
        return HttpResponse(str(grafico))
    if mostrar_filtros:
        setores = Setor.objects.filter(pk__in=list(respostas.order_by('respondente__setor').values_list('respondente__setor', flat=True))).distinct()
        segmentos = grupo_pergunta.questionario.segmentos.all()

    return locals()


@rtr()
@login_required
def resultado_avaliacao_matriz(request, pk, matriz_pk):
    title = 'Estatísticas de Respostas'
    avaliacao = Avaliacao.objects.get(pk=pk)

    id_questionario_professor = None

    qs = avaliacao.questionario_set.all()
    qs_questionario_aluno = qs.filter(segmentos=Segmento.ALUNO).values_list('pk', flat=True)
    id_questionario_aluno = qs_questionario_aluno.exists() and qs_questionario_aluno[0] or None
    qs_questionario_professor = qs.filter(segmentos=Segmento.PROFESSOR).values_list('pk', flat=True)
    id_questionario_professor = qs_questionario_professor.exists() and qs_questionario_professor[0] or None

    matriz = Matriz.objects.get(pk=matriz_pk)
    matrizes = []
    anual = matriz.matrizcurso_set.filter(curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL).exists()
    periodos = list(range(1, matriz.qtd_periodos_letivos + 1))
    colspan = matriz.qtd_periodos_letivos + 6
    nucleos = list()
    attrs = ('carga_horaria', 'sequencia_didatica', 'ementa_programa', 'regime_misto', 'justificativa')
    for nucleo in Nucleo.objects.filter(pk__in=matriz.componentecurricular_set.values_list('nucleo', flat=True).distinct()):
        componentes_curriculares = []
        for componente_curricular in (
            matriz.componentecurricular_set.filter(nucleo=nucleo)
            .exclude(tipo__in=(ComponenteCurricular.TIPO_SEMINARIO, ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL))
            .order_by('componente__descricao')
            .distinct()
        ):
            componentes_curriculares.append(componente_curricular)
        nucleos.append(('Núcleo {}'.format(nucleo), componentes_curriculares))

    componentes_curriculares = []
    for componente_curricular in matriz.componentecurricular_set.filter(tipo=ComponenteCurricular.TIPO_SEMINARIO).order_by('componente__descricao').distinct():
        componentes_curriculares.append(componente_curricular)
    nucleos.append(('Seminários', componentes_curriculares))

    componentes_curriculares = []
    for componente_curricular in matriz.componentecurricular_set.filter(tipo=ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL).order_by('componente__descricao').distinct():
        componentes_curriculares.append(componente_curricular)
    nucleos.append(('Prática Profissional', componentes_curriculares))

    matrizes.append((matriz, nucleos, anual))
    return locals()


@rtr()
@login_required
def estatistica_resposta_componente_curricular(request, pk, componente_curricular_pk, segmento_pk):
    componente_curricular = ComponenteCurricular.objects.get(pk=componente_curricular_pk)
    return estatistica_resposta_componente(request, pk, componente_curricular.matriz_id, componente_curricular.componente_id, segmento_pk)


@rtr()
@login_required
def estatistica_resposta_componente(request, pk, matriz_pk, componente_pk, segmento_pk):
    title = 'Estatísticas de Respostas'
    subtitle = []
    respostas = AvaliacaoComponenteCurricular.objects.filter(respondente__questionario__avaliacao=pk, respondente__segmento=segmento_pk)
    if matriz_pk and int(matriz_pk):
        componente_curricular = ComponenteCurricular.objects.get(matriz=matriz_pk, componente=componente_pk)
        respostas = respostas.filter(componente_curricular=componente_curricular)
    else:
        componente_curricular = Componente.objects.get(pk=componente_pk)
        respostas = respostas.filter(componente_curricular__componente=componente_pk)
    setor = request.GET.get('setor', '')
    if setor:
        setor = Setor.objects.get(pk=setor)
        respostas = respostas.filter(respondente__setor=setor)
        subtitle.append(setor.sigla)
    segmento_id = request.GET.get('segmento', segmento_pk)
    if segmento_id:
        segmento = Segmento.objects.get(pk=segmento_id)
        respostas = respostas.filter(respondente__segmento=segmento)
        subtitle.append(segmento.descricao)
    series = []
    groups = []
    subtitle = ' - '.join(subtitle)
    for choice in Pergunta.RESPOSTA_ESCALA_PADRAO_CHOICES[1:]:
        groups.append(choice[0])
    series.append(['Carga Horária'])
    for valor in groups:
        series[-1].append(respostas.exclude(carga_horaria='').filter(carga_horaria=valor).count())
    series.append(['Sequência-Didática'])
    for valor in groups:
        series[-1].append(respostas.exclude(sequencia_didatica='').filter(sequencia_didatica=valor).count())
    series.append(['Ementa'])
    for valor in groups:
        series[-1].append(respostas.exclude(ementa_programa='').filter(ementa_programa=valor).count())
    series.append(['Regime Misto'])
    for valor in groups:
        series[-1].append(respostas.exclude(regime_misto='').filter(regime_misto=valor).count())

    dataLabels_format = '<b>{point.name}</b>: {point.percentage:.1f} %'
    plotOptions = {'column': {'dataLabels': {'enabled': 'true', 'color': 'white'}}}
    grafico = StackedGroupedColumnChart('grafico', title=str(componente_curricular), subtitle=subtitle, data=series, groups=groups, plotOptions=plotOptions)

    grafico.plotOptions['series']['dataLabels']['enabled'] = 'true'
    grafico.plotOptions['series']['dataLabels']['padding'] = '0'
    grafico.plotOptions['series']['dataLabels']['format'] = '{percentage:.0f}%'
    grafico.plotOptions['column']['dataLabels']['padding'] = '0'
    if 'setor' in request.GET:
        return HttpResponse(str(grafico))

    setores = Setor.objects.filter(pk__in=respostas.order_by('respondente__setor').values_list('respondente__setor', flat=True).distinct())
    respostas = respostas.filter(justificativa__isnull=False).exclude(justificativa='').order_by('respondente__setor')
    return locals()


@rtr()
@login_required
def respostas_subjetivas_xls(request, pk):
    questionario = Questionario.objects.get(pk=pk)
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=RespostasSubjetivas.xls'
    wb = xlwt.Workbook(encoding='utf-8')
    style = xlwt.easyxf('pattern: pattern solid, fore_colour gray25;' 'borders: left thin, right thin, top thin, bottom thin;' 'font: colour black, bold True;')
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    for sigla in [instituicao] + list(UnidadeOrganizacional.objects.suap().all().values_list('sigla', flat=True)):
        qs_diretorias = Diretoria.objects.filter(setor__uo__sigla=sigla)
        if qs_diretorias.count() > 1:
            for diretoria in qs_diretorias:
                sheet1 = wb.add_sheet(diretoria.setor.sigla.replace('/', '-'))
                count = 0
                for i, grupo_pergunta in enumerate(questionario.grupopergunta_set.all()):
                    qs_perguntas = grupo_pergunta.pergunta_set.filter(tipo_resposta=Pergunta.RESPOSTA_SUBJETIVA)
                    for j, pergunta in enumerate(qs_perguntas):
                        sheet1.row(0).write(count, 'Grupo {}'.format(i + 1), style)
                        sheet1.row(1).write(count, grupo_pergunta.descricao, style)
                        sheet1.row(2).write(count, pergunta.enunciado, style)
                        for k, resposta in enumerate(pergunta.resposta_set.filter(respondente__setor=diretoria.setor)):  # aprovada=True,
                            sheet1.row(3 + k).write(count, resposta.resposta)
                        count += 1
                    if not qs_perguntas:
                        sheet1.row(0).write(count, 'Grupo {}'.format(i + 1), style)
                        count += 1
        else:
            sheet1 = wb.add_sheet(sigla)
            count = 0
            for i, grupo_pergunta in enumerate(questionario.grupopergunta_set.all()):
                qs_perguntas = grupo_pergunta.pergunta_set.filter(tipo_resposta=Pergunta.RESPOSTA_SUBJETIVA)
                for j, pergunta in enumerate(qs_perguntas):
                    sheet1.row(0).write(count, 'Grupo {}'.format(i + 1), style)
                    sheet1.row(1).write(count, grupo_pergunta.descricao, style)
                    sheet1.row(2).write(count, pergunta.enunciado, style)
                    qs = pergunta.resposta_set.all()  # filter(aprovada=True)
                    if sigla != 'IFRN':
                        qs = qs.filter(respondente__setor__uo__sigla=sigla)
                    for k, resposta in enumerate(qs):
                        sheet1.row(3 + k).write(count, resposta.resposta)
                    count += 1
                if not qs_perguntas:
                    sheet1.row(0).write(count, 'Grupo {}'.format(i + 1), style)
                    count += 1

    wb.save(response)
    return response


@rtr()
@login_required
def respostas_subjetivas_componentes_xls(request, pk, matriz_id=None):
    questionario = Questionario.objects.get(pk=pk)
    response = HttpResponse(content_type='application/ms-excel')
    response['Content-Disposition'] = 'attachment; filename=RespostasSubjetivas.xls'
    wb = xlwt.Workbook(encoding='utf-8')
    style = xlwt.easyxf('pattern: pattern solid, fore_colour gray25;' 'borders: left thin, right thin, top thin, bottom thin;' 'font: colour black, bold True;')
    qs = AvaliacaoComponenteCurricular.objects.filter(respondente__questionario=questionario).exclude(justificativa='').exclude(justificativa__isnull=True)  # aprovada=True,
    if matriz_id:
        qs = qs.filter(componente_curricular__matriz=matriz_id)
    componentes = Componente.objects.filter(id__in=qs.order_by('componente_curricular__componente').values_list('componente_curricular__componente', flat=True).distinct())
    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    for sigla in [instituicao] + list(UnidadeOrganizacional.objects.suap().all().values_list('sigla', flat=True)):
        count = 0
        qs_diretorias = Diretoria.objects.filter(setor__uo__sigla=sigla)
        if qs_diretorias.count() > 1:
            for diretoria in qs_diretorias:
                pks_componentes = (
                    componentes.filter(componentecurricular__matriz__matrizcurso__curso_campus__diretoria__setor=diretoria.setor)
                    .order_by('pk')
                    .values_list('pk', flat=True)
                    .distinct()
                )
                tmp_componentes = componentes.filter(pk__in=pks_componentes)
                sheet1 = wb.add_sheet(diretoria.setor.sigla.replace('/', '-'))
                for componente in tmp_componentes.order_by('descricao'):
                    qs_avaliacao_componente = qs.filter(componente_curricular__componente=componente)
                    if qs_avaliacao_componente.exists():
                        sheet1.row(count).write(0, str(componente), style)
                        count += 1
                        for justificativa in qs_avaliacao_componente.order_by('justificativa').values_list('justificativa', flat=True).distinct():
                            sheet1.row(count).write(0, justificativa)
                            count += 1
        else:
            sheet1 = wb.add_sheet(sigla)

            if sigla != instituicao:
                pks_componentes = (
                    componentes.filter(componentecurricular__matriz__matrizcurso__curso_campus__diretoria__setor__uo__sigla=sigla)
                    .order_by('pk')
                    .values_list('pk', flat=True)
                    .distinct()
                )
                tmp_componentes = componentes.filter(pk__in=pks_componentes)
            else:
                tmp_componentes = componentes

            for componente in tmp_componentes.order_by('descricao'):
                qs_avaliacao_componente = qs.filter(componente_curricular__componente=componente)
                if qs_avaliacao_componente.exists():
                    sheet1.row(count).write(0, str(componente), style)
                    count += 1
                    for justificativa in qs_avaliacao_componente.order_by('justificativa').values_list('justificativa', flat=True).distinct():
                        sheet1.row(count).write(0, justificativa)
                        count += 1

    wb.save(response)
    return response


@login_required
def justificar_avaliacao_componente_ajax(request, respondente, campo, componente_curricular):
    qs = JustificativaAvaliacaoComponenteCurricular.objects.filter(
        respondente_id=respondente, campo=int(campo), componente_curricular_id=componente_curricular
    )
    if qs.exists():
        obj = qs.first()
    else:
        obj = JustificativaAvaliacaoComponenteCurricular(
            respondente_id=respondente, campo=int(campo), componente_curricular_id=componente_curricular
        )
    obj.justificativa = request.GET['justificativa']
    if obj.justificativa:
        obj.save()
    else:
        if obj.pk:
            obj.delete()
    return HttpResponse('Justificativa salva com sucesso.')
