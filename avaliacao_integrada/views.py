# -*- coding: utf-8 -*-
import datetime
from collections import OrderedDict, Counter

from django.shortcuts import get_object_or_404

from avaliacao_integrada import tasks
from avaliacao_integrada.forms import AvaliacaoExternaForm, RelatorioForm, FiltroIndicadorForm, RelatorioXLSXForm
from avaliacao_integrada.models import Avaliacao, Indicador, Segmento, Respondente, Resposta, Iterador
from djtools import forms
from djtools import layout
from djtools.forms.fields import DateFieldPlus
from djtools.html.graficos import PieChart, BarChart, StackedGroupedColumnChart
from djtools.utils import permission_required, rtr, httprr, group_required
from edu.models import Modalidade, CursoCampus, ProfessorDiario, Diario, Aluno
from edu.utils import TabelaBidimensional
from rh.models import UnidadeOrganizacional, Servidor


@layout.servicos_anonimos()
def servicos_anonimos(request):
    servicos_anonimos = list()

    # servicos_anonimos.append(dict(categoria='Avaliações', url="/avaliacao_integrada/avaliacao_externa/", icone="file", titulo='Avaliação Integrada'))

    return servicos_anonimos


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()

    qs = Respondente.objects.filter(user=request.user, avaliacao__data_inicio__lte=datetime.date.today(), avaliacao__data_termino__gte=datetime.date.today(
    ), finalizado=False)
    if qs.exists():
        for item in qs:
            titulo = 'Você precisa responder a {}.'.format(item.avaliacao) if not item.resposta_set.exists() else 'Você ainda pode editar as suas respostas da {}.'.format(item.avaliacao)
            inscricoes.append(
                dict(
                    url=f'/avaliacao_integrada/questionario/{item.pk}/'.format(item.pk), titulo=titulo, prazo=item.avaliacao.data_termino
                )
            )

    return inscricoes


@rtr()
@permission_required('avaliacao_integrada.change_avaliacao')
def avaliacao(request, pk):
    obj = get_object_or_404(Avaliacao, id=pk)
    title = str(obj)
    respondentes = obj.respondente_set.all()
    uos = UnidadeOrganizacional.objects.suap().filter(pk__in=Respondente.objects.filter(avaliacao=obj).values_list('uo__pk', flat=True).distinct())
    segmentos = Segmento.objects.filter(pk__in=Respondente.objects.filter(avaliacao=obj).values_list('segmento__pk', flat=True).distinct())

    q = request.GET.get('q')
    uo_selecionada = request.GET.get('uo_selecionada')
    segmento_selecionado = request.GET.get('segmento_selecionado')

    if 'identificar_respondentes' in request.GET:
        return tasks.reprocessar_publico_alvo(obj, False)

    if 'excluir_e_identificar_respondentes' in request.GET:
        return tasks.reprocessar_publico_alvo(obj, True)

    if q:
        respondentes = (
            respondentes.filter(user__pessoafisica__nome__icontains=q) | respondentes.filter(user__username=q) | respondentes.filter(user__pessoafisica__cpf__icontains=q)
        ).distinct()
    else:
        q = ''

    if uo_selecionada:
        respondentes = (respondentes.filter(uo__pk=uo_selecionada)).distinct()
    else:
        uo_selecionada = None

    if segmento_selecionado:
        respondentes = (respondentes.filter(segmento__pk=segmento_selecionado)).distinct()
    else:
        segmento_selecionado = None

    if request.GET.get('tab') == 'quadro_resumo':
        tabela_resumo_finalizados = TabelaBidimensional(
            'Finalizados',
            obj.respondente_set.filter(finalizado=True),
            vertical_model=UnidadeOrganizacional,
            vertical_key='uo',
            horizontal_model=Segmento,
            horizontal_key='segmento',
        )
        tabela_resumo_parciais = TabelaBidimensional(
            'Parciais',
            obj.respondente_set.filter(finalizado=False, resposta__isnull=False).distinct(),
            vertical_model=UnidadeOrganizacional,
            vertical_key='uo',
            horizontal_model=Segmento,
            horizontal_key='segmento',
        )
        tabela_resumo_nao_respondidos = TabelaBidimensional(
            'Não Respondidos',
            obj.respondente_set.filter(finalizado=False, resposta__isnull=True).distinct(),
            vertical_model=UnidadeOrganizacional,
            vertical_key='uo',
            horizontal_model=Segmento,
            horizontal_key='segmento',
        )

    return locals()


@rtr()
@permission_required('avaliacao_integrada.change_indicador')
def indicador(request, pk):
    obj = get_object_or_404(Indicador, id=pk)
    title = str(obj)
    form = forms.Form()
    fields = obj.get_form_field()
    if len(fields) > 1:
        form.fieldsets = ((obj.nome, {'fields': ([x.name for x in fields],)}),)
    for field in fields:
        form.fields[field.name] = field
    return locals()


@rtr()
@permission_required('avaliacao_integrada.change_indicador')
def replicar_indicador(request, pk):
    from copy import copy

    obj = get_object_or_404(Indicador, id=pk)

    # Clonando o objeto
    novo_obj = copy(obj)
    novo_obj.pk = None
    novo_obj.nome = '{} [Replicado]'.format(novo_obj.nome)
    novo_obj.save()

    # Associando os objetos relacionados ao novo objeto
    for subsidio_para in obj.subsidio_para.all():
        subsidio_para.indicador_set.add(novo_obj)
    for segmento in obj.segmentos.all():
        segmento.indicador_set.add(novo_obj)
    for area_vinculacao in obj.areas_vinculacao.all():
        area_vinculacao.indicador_set.add(novo_obj)
    for modalidade in obj.modalidades.all():
        modalidade.indicador_set.add(novo_obj)
    for opcaoresposta in obj.opcaoresposta_set.all():
        nova_opcaoresposta = copy(opcaoresposta)
        nova_opcaoresposta.pk = None
        nova_opcaoresposta.indicador = novo_obj
        nova_opcaoresposta.save()

    # Redirecionando para a página de edição
    return httprr('/admin/avaliacao_integrada/indicador/{}/change/'.format(novo_obj.pk), 'Indicador replicado com sucesso.')


@rtr()
def questionario(request, pk):
    respondente = get_object_or_404(Respondente, id=pk)
    title = respondente.avaliacao.nome
    eh_previsualizacao = request.user.has_perm('avaliacao_integrada.change_avaliacao') and request.user != respondente.user

    if (datetime.date.today() > respondente.avaliacao.data_termino) and not eh_previsualizacao:
        return httprr('/', 'O prazo para resposta da Avaliação foi expirado.', 'error')

    if not eh_previsualizacao:
        if not respondente.user == request.user:
            return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    if request.user == respondente.user and respondente.finalizado:
        return httprr('..', 'A avaliação já foi respondida.', 'error')

    form = forms.Form(data=request.POST or None)

    # obtendo as respostas previamente fornecidas para inicialização dos fields
    initial = {}
    if not eh_previsualizacao:
        for identificador, valor in Resposta.objects.filter(respondente=respondente).values_list('identificador', 'valor'):
            initial[identificador] = valor

    try:
        indicadores = respondente.get_indicadores()
    except ValueError:
        return httprr('..', 'Não foi possível exibir o questionário pois o aluno não possui a indicação do período de referência.', 'error')

    # além do agrupado por eixo, macroprocesso e dimensão, as perguntas serão
    # agrupadas por uma seção representando o objeto ao qual as perguntas/criterios
    # ser referem.
    # As perguntas relacionadas à instituição serão vinculadas ao objeto None
    objetos = [None]
    for modalidade in respondente.get_modalidades_relacionadas():
        objetos.append(modalidade)
    for curso_campus in respondente.get_cursos_relacionados():
        objetos.append(curso_campus)
    for turma in respondente.get_turmas_relacionadas():
        objetos.append(turma)
    for professor in respondente.get_professores_relacionados():
        objetos.append(professor)

    # identificando os idicadores para cada tipo de objeto iterável (None = instituição)
    iteracoes = OrderedDict()
    indicadores_por_iterador = OrderedDict()
    indicadores_por_iterador[type(None)] = indicadores.exclude(iterador__segmento=respondente.segmento)
    indicadores_por_iterador[Modalidade] = indicadores.filter(iterador__segmento=respondente.segmento, iterador__objeto=Iterador.MODALIDADE)
    indicadores_por_iterador[CursoCampus] = indicadores.filter(iterador__segmento=respondente.segmento, iterador__objeto=Iterador.CURSO)
    indicadores_por_iterador[ProfessorDiario] = indicadores.filter(iterador__segmento=respondente.segmento, iterador__objeto=Iterador.PROFESSOR)
    indicadores_por_iterador[Diario] = indicadores.filter(iterador__segmento=respondente.segmento, iterador__objeto=Iterador.TURMA)

    # montagem do formulário
    eixo = None
    dimensao = None
    macroprocesso = None

    total = 0
    respondido = 0

    tem_escala_padrao = False
    for objeto in objetos:
        indicadores = indicadores_por_iterador[type(objeto)]

        if objeto not in iteracoes:
            iteracoes[objeto] = OrderedDict()

        for indicador in indicadores:
            eixo = indicador.macroprocesso.dimensao.eixo
            dimensao = indicador.macroprocesso.dimensao
            macroprocesso = indicador.macroprocesso
            if eixo not in iteracoes[objeto]:
                iteracoes[objeto][eixo] = OrderedDict()
            if dimensao not in iteracoes[objeto][eixo]:
                iteracoes[objeto][eixo][dimensao] = OrderedDict()
            if macroprocesso not in iteracoes[objeto][eixo][dimensao]:
                iteracoes[objeto][eixo][dimensao][macroprocesso] = []
            if not tem_escala_padrao and indicador.tipo_resposta == Indicador.FAIXA_NUMERICA:
                tem_escala_padrao = True
            fields = indicador.get_form_field(respondente, objeto)
            iteracoes[objeto][eixo][dimensao][macroprocesso].append(fields)
            for field in fields:
                if len(fields) > 1:
                    field.aspecto = indicador.aspecto
                field.texto_ajuda = indicador.texto_ajuda
                form.fields[field.name] = field
                if not indicador.automatico:
                    total += 1
                if field.name in initial:
                    valor = initial[field.name]
                    if '::' in valor:
                        valor = valor.split('::')
                    if type(field) is DateFieldPlus:
                        valor = datetime.datetime.strptime(valor, "%Y-%m-%d").date()
                    field.initial = valor
                    if type(field.widget) == forms.Textarea or (valor not in ['', '', None] and not indicador.automatico):
                        respondido += 1

    if total:
        percentual = int(100 * respondido / total)
    else:
        percentual = 0

    if form.is_valid():
        finalizar = '_save_and_finalize' in request.POST
        Resposta.processar(respondente, form.cleaned_data, finalizar)

        if finalizar:
            return httprr('..', 'Avaliação respondida com sucesso.')
        else:
            return httprr(request.META.get('HTTP_REFERER', '.'), 'Avaliação salva com sucesso.')

    return locals()


@rtr()
def avaliacao_externa(request):
    title = 'Acessar Avaliação Integrada'
    category = 'Avaliações'
    icon = 'file'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    form = AvaliacaoExternaForm(data=request.POST or None)
    if form.is_valid():
        token = request.POST.get('token')
        tipo_respondente = request.POST.get('tipo_respondente')
        qs = Avaliacao.objects.filter(token=token)

        if qs.exists():
            return httprr('/avaliacao_integrada/avaliacao_externa/{0}/{1}/'.format(token, tipo_respondente))
        else:
            return httprr('.', 'Avaliação não encontrada. Por favor, verifique se a chave de acesso está correta.', 'error')
    return locals()


@rtr("avaliacao_integrada/templates/questionario.html")
def questionario_avaliacao_externa(request, token, segmento):
    avaliacao = get_object_or_404(Avaliacao, token=token)
    segmento = get_object_or_404(Segmento, pk=segmento)
    title = avaliacao.nome

    if not segmento.pk in [Segmento.PAIS, Segmento.EMPRESAS, Segmento.SOCIEDADE_CIVIL, Segmento.DESLIGADO]:
        return httprr('..', 'Você não tem permissão para realizar isso.', 'error')

    # Criando o respondente
    respondente = Respondente()
    respondente.avaliacao = avaliacao
    respondente.segmento = segmento
    respondente.save()

    form = forms.Form(data=request.POST or None)

    # obtendo as respostas previamente fornecidas para inicialização dos fields
    initial = {}
    for identificador, valor in Resposta.objects.filter(respondente=respondente).values_list('identificador', 'valor'):
        initial[identificador] = valor

    # filtrando indicadores ativos
    indicadores = Indicador.objects.filter(em_uso=True)
    # filtrando indicadores por segmento do respondente
    indicadores = indicadores.filter(segmentos=respondente.segmento)
    # filtrando indicadores por area do respondente
    if respondente.segmento_id in [Segmento.GESTOR, Segmento.TECNICO, Segmento.ETEP]:
        servidor = Servidor.objects.get(matricula=respondente.user.username)
        indicadores = indicadores.filter(areas_vinculacao__isnull=True) | indicadores.filter(areas_vinculacao__in=servidor.setor.areas_vinculacao.values_list('pk', flat=True))
    # filtrando indicadores pela modalidade dos cursos
    if respondente.avaliacao.modalidades.exists():
        indicadores = indicadores.filter(modalidades__in=respondente.avaliacao.modalidades.values_list('id', flat=True)) | indicadores.filter(modalidades__isnull=True)
        # filtrando indicadores pelo período de referência do aluno
        if respondente.segmento_id in [Segmento.ESTUDANTE]:
            aluno = Aluno.objects.get(matricula=respondente.user.username)
            if aluno.periodo_atual:
                indicadores = indicadores.exclude(periodo_curso__gt=aluno.periodo_atual)
    indicadores = indicadores.distinct()

    # além do agrupado por eixo, macroprocesso e dimensão, as perguntas serão
    # agrupadas por uma seção representando o objeto ao qual as perguntas/criterios
    # ser referem.
    # As perguntas relacionadas à instituição serão vinculadas ao objeto None
    objetos = [None]
    for modalidade in respondente.get_modalidades_relacionadas():
        objetos.append(modalidade)
    for curso_campus in respondente.get_cursos_relacionados():
        objetos.append(curso_campus)
    for turma in respondente.get_turmas_relacionadas():
        objetos.append(turma)
    for professor in respondente.get_professores_relacionados():
        objetos.append(professor)

    # identificando os idicadores para cada tipo de objeto iterável (None = instituição)
    iteracoes = OrderedDict()
    indicadores_por_iterador = OrderedDict()
    indicadores_por_iterador[type(None)] = indicadores.exclude(iterador__segmento=respondente.segmento)
    indicadores_por_iterador[Modalidade] = indicadores.filter(iterador__segmento=respondente.segmento, iterador__objeto=Iterador.MODALIDADE)
    indicadores_por_iterador[CursoCampus] = indicadores.filter(iterador__segmento=respondente.segmento, iterador__objeto=Iterador.CURSO)
    indicadores_por_iterador[ProfessorDiario] = indicadores.filter(iterador__segmento=respondente.segmento, iterador__objeto=Iterador.PROFESSOR)
    indicadores_por_iterador[Diario] = indicadores.filter(iterador__segmento=respondente.segmento, iterador__objeto=Iterador.TURMA)

    # montagem do formulário
    eixo = None
    dimensao = None
    macroprocesso = None

    for objeto in objetos:

        indicadores = indicadores_por_iterador[type(objeto)]

        if objeto not in iteracoes:
            iteracoes[objeto] = OrderedDict()

        for indicador in indicadores:

            eixo = indicador.macroprocesso.dimensao.eixo
            dimensao = indicador.macroprocesso.dimensao
            macroprocesso = indicador.macroprocesso
            if eixo not in iteracoes[objeto]:
                iteracoes[objeto][eixo] = OrderedDict()
            if dimensao not in iteracoes[objeto][eixo]:
                iteracoes[objeto][eixo][dimensao] = OrderedDict()
            if macroprocesso not in iteracoes[objeto][eixo][dimensao]:
                iteracoes[objeto][eixo][dimensao][macroprocesso] = []
            fields = indicador.get_form_field(respondente, objeto)
            iteracoes[objeto][eixo][dimensao][macroprocesso].append(fields)
            for field in fields:
                if len(fields) > 1:
                    field.aspecto = indicador.aspecto
                form.fields[field.name] = field
                if field.name in initial:
                    valor = initial[field.name]
                    if '::' in valor:
                        valor = valor.split('::')
                    field.initial = valor

    if form.is_valid():
        finalizar = '_save_and_finalize' in request.POST
        Resposta.processar(respondente, form.cleaned_data, finalizar)
        return httprr('..', 'Avaliação respondida com sucesso.')
    return locals()


@rtr()
@group_required('avaliacao_integrada Administrador,Administrador de Avaliação Institucional,Aplicador de Avaliação Institucional,Visualizador de Avaliação Institucional')
def relatorio(request):
    title = 'Relatórios'
    form = RelatorioForm(request.GET or None)
    if form.is_valid():
        indicadores = form.processar()
    return locals()


@rtr()
@group_required('avaliacao_integrada Administrador,Administrador de Avaliação Institucional,Aplicador de Avaliação Institucional,Visualizador de Avaliação Institucional')
def relatorio_xlsx(request):
    title = 'Relatório em XLSX'
    form = RelatorioXLSXForm(request.GET or None)
    if form.is_valid():
        respostas = form.processar()
        return tasks.relatorio_xlsx(respostas)

    return locals()


@rtr()
@group_required('avaliacao_integrada Administrador,Administrador de Avaliação Institucional,Aplicador de Avaliação Institucional,Visualizador de Avaliação Institucional')
def exibir_relatorio_indicador(request, pk, pk_avaliacao):
    obj = get_object_or_404(Indicador, pk=pk)
    avaliacao = get_object_or_404(Avaliacao, pk=pk_avaliacao)
    title = 'Detalhamento do Indicador - {}'.format(obj.aspecto)
    respostas = obj.resposta_set.filter(respondente__avaliacao=avaliacao)
    respondentes = avaliacao.respondente_set
    form = FiltroIndicadorForm(data=request.POST or None)
    respondentes = FiltroIndicadorForm.filtrar_respondentes2(respondentes, obj.segmentos.all(), obj.areas_vinculacao.all(), None, obj.modalidades.all())

    form.fields['segmentos'].queryset = obj.segmentos
    if form.is_valid():
        respostas = form.filtrar_respostas(respostas)
        respondentes = form.filtrar_respondentes(respondentes)
        respondentes = form.filtrar_respondentes(respondentes)
    qtd_respondentes = respondentes.count()
    qtd_respostas = respostas.order_by('respondente').values_list('respondente', flat=True).distinct().count()

    if qtd_respondentes > 0:
        percentual_respostas = (float(qtd_respostas) / float(qtd_respondentes)) * 100
    else:
        percentual_respostas = 0.0

    def calcular_distribuicao(respostas, valores):
        distribuicao_frequencia = []
        for valor in valores:
            item = dict(qtd=respostas.filter(valor=valor).count(), valor=str(valor))
            distribuicao_frequencia.append(item)
        return distribuicao_frequencia

    if qtd_respondentes and qtd_respostas:
        if obj.tipo_resposta in [Indicador.FAIXA_NUMERICA, Indicador.NUMERO_INTEIRO, Indicador.GRAU_SATISFACAO]:

            if obj.iterador_set.exists() and not request.POST:
                exibir_mensagem = True
            else:
                import math
                import numpy

                dados_brutos = respostas.exclude(valor__in=["", "0", "9"]).values_list('valor', flat=True)
                lista_valores_str = respostas.order_by('valor').values_list('valor', flat=True).distinct()
                lista_valores = [int(x or 0) for x in lista_valores_str]
                lista_valores_1_a_5_str = respostas.exclude(valor__in=["", "0", "9"]).order_by('valor').values_list('valor', flat=True).distinct()
                lista_valores_1_a_5 = [int(x or 0) for x in lista_valores_1_a_5_str]

                distribuicao_frequencia = calcular_distribuicao(respostas, lista_valores_str)
                distribuicao_1_a_5 = calcular_distribuicao(respostas, lista_valores_1_a_5_str)

                for df in distribuicao_frequencia:
                    df['percentual'] = (float(df['qtd']) / float(respostas.count())) * 100
                    if obj.tipo_resposta in [Indicador.FAIXA_NUMERICA, Indicador.GRAU_SATISFACAO]:
                        if df['valor'] == '0':
                            df['valor'] = 'Desconheço'
                        elif df['valor'] == '9':
                            df['valor'] = 'Não se aplica'
                        elif df['valor'] == '':
                            df['valor'] = 'Não responderam'

                media = 0
                dados = [int(x['valor'] or 0) for x in distribuicao_1_a_5]
                pesos = [x['qtd'] for x in distribuicao_1_a_5]

                if pesos:
                    media = numpy.average(lista_valores_1_a_5, weights=pesos)

                    x_barra = numpy.multiply(lista_valores_1_a_5, pesos)
                    x_media_2 = [x * x for x in [n - media for n in lista_valores_1_a_5]]
                    numerador = []
                    for i in range(len(pesos)):
                        numerador.append(x_media_2[i] * pesos[i])
                    sum_valores = sum(lista_valores_1_a_5)
                    sum_pesos = sum(pesos)
                    sum_x_barra = sum(x_barra)
                    sum_numerador = sum(numerador)

                    # Calculando as medidas resumo
                    mediana = round(numpy.median(lista_valores_1_a_5), 2)
                    variancia = round(sum_numerador / (sum_pesos - 1), 2)
                    desvio_padrao = round(math.sqrt(variancia), 2)
                    counts = numpy.bincount(dados_brutos)
                    moda = numpy.argmax(counts)
                    # moda = stats.mode(dados_brutos).mode[0]
                    coeficiente_variacao = round(desvio_padrao / media, 2)

                id_grafico = 'id_grafico_x'
                grafico = StackedGroupedColumnChart(
                    id_grafico,
                    title='Distribuição de Frequência das Respostas',
                    groups=[x['valor'] or 'Não responderam' for x in distribuicao_frequencia],
                    data=[['Total'] + [x['qtd'] for x in distribuicao_frequencia]],
                )
                grafico.id = id_grafico

                id_grafico = 'id_grafico_y'
                grafico2 = PieChart(
                    id_grafico,
                    title='Distribuição de Frequência das Respostas',
                    data=[[x['valor'], x['qtd']] for x in distribuicao_frequencia],
                    dataLabels_format='{point.name} ({point.percentage:.2f}%)',
                )
                grafico2.id = id_grafico

        elif obj.tipo_resposta in [Indicador.UNICA_ESCOLHA, Indicador.MULTIPLA_ESCOLHA]:
            qs = respostas.values_list('valor', flat=True)
            lista = []
            for x in qs:
                ly = []
                for y in x.rstrip('::').split('::'):
                    ly.append(y)
                lista.append(ly)

            ranking_frequencia = Counter(sum(lista, [])).most_common()
            ranking_frequencia_sem_percentual = list()
            ranking_frequencia_com_percentual = list()

            qtd_itens = 0
            for rf in ranking_frequencia:
                qtd_itens += 1
                if not rf[0]:
                    rf = ('Não responderam', rf[1])
                ranking_frequencia_sem_percentual.append(rf)
                rf = rf + ((float(rf[1]) / float(respostas.count())) * 100,)
                ranking_frequencia_com_percentual.append(rf)

            if obj.tipo_resposta == Indicador.UNICA_ESCOLHA:
                id_grafico = 'id_grafico_x'
                grafico = PieChart(
                    id_grafico, title='Ranking de Frequência das Respostas', data=ranking_frequencia_sem_percentual, dataLabels_format='{point.name} ({point.percentage:.2f}%)'
                )
                grafico.id = id_grafico
            else:
                id_grafico = 'id_grafico_x'
                grafico = BarChart(id_grafico, title='Ranking de Frequência das Respostas', data=ranking_frequencia_sem_percentual)
                grafico.id = id_grafico
                if qtd_itens > 6:
                    grafico.div_height = qtd_itens * 70
                else:
                    grafico.div_height = 400
        elif obj.tipo_resposta in [Indicador.TEXTO_CURTO, Indicador.TEXTO_LONGO]:
            conjunto_respostas = respostas.order_by('valor').values_list('valor', flat=True).distinct()

            if obj.tipo_resposta == Indicador.TEXTO_CURTO and obj.automatico:
                if not obj.nome == 'Data de nascimento':
                    conjunto_respostas = calcular_distribuicao(respostas, conjunto_respostas)
                    serie = []

                    for cr in conjunto_respostas:
                        cr['percentual'] = (float(cr['qtd']) / float(respostas.count())) * 100
                        serie.append([cr['valor'], float(cr['qtd'])])

                    id_grafico = 'id_grafico_x'
                    grafico = PieChart(id_grafico, title='Ranking de Frequência das Respostas', data=serie, dataLabels_format='{point.name} ({point.percentage:.2f}%)')
                    grafico.id = id_grafico
                else:
                    import numpy

                    lista_anos = [int(x[:4]) for x in conjunto_respostas if 1930 < int(x[:4]) < 2010]
                    distribuicao, faixas = numpy.histogram(lista_anos)

                    distribuicao_por_faixa = []
                    for n in range(distribuicao.size):
                        distribuicao_por_faixa.append({'inicio': int(faixas[n]), 'final': int(faixas[n + 1]), 'total': int(distribuicao[n])})
    return locals()
