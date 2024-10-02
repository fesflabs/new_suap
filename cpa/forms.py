# -*- coding: utf-8 -*-

from collections import OrderedDict

from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db import transaction
from django.db.models.aggregates import Count
from django.utils.safestring import mark_safe

from cpa.models import Questionario, Pergunta, Resposta
from djtools import forms
from djtools.html.graficos import GroupedColumnChart, ColumnChart, PieChart, StackedGroupedColumnChart
from djtools.utils import httprr
from edu.models import Aluno, CursoCampus
from rh.models import UnidadeOrganizacional


class PerguntaForm(forms.ModelFormPlus):
    objetiva = forms.BooleanField(label='Objetiva', initial=True, required=False)

    class Meta:
        model = Pergunta
        fields = ('identificador', 'texto', 'objetiva', 'ordem')

    def __init__(self, *args, **kwargs):
        questionario = None
        categoria = None
        if 'questionario' in kwargs:
            questionario = kwargs.pop('questionario')

        if 'categoria' in kwargs:
            categoria = kwargs.pop('categoria')

        super(PerguntaForm, self).__init__(*args, **kwargs)
        if questionario:
            self.instance.questionario = questionario

        if categoria:
            self.instance.categoria = categoria


class ResultadoForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Visualizar'
    questionario = forms.ModelChoiceField(Questionario.objects.order_by('-id'), label='Questionário')
    add_parcial = forms.BooleanField(label='Adicionar Questionários Parciais', required=False)
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.suap().filter(), label='Campus', required=False)
    # Esse curso está só para levar em consideração a descrição historico
    curso = forms.ChainedModelChoiceField(
        CursoCampus.objects.all(),
        label='Curso do Aluno',
        empty_label='Selecione o Campus',
        required=False,
        obj_label='descricao_historico',
        url='/cpa/get_cursos/',
        form_filters=[('uo', 'diretoria__setor__uo_id')],
    )
    ano_ingresso = forms.IntegerField(label='Ano de Ingresso do Aluno', required=False)

    def obter_respostas_subjetivas(self, pergunta):
        uo = self.cleaned_data['uo']
        curso = self.cleaned_data['curso']
        add_parcial = self.cleaned_data["add_parcial"]
        ano_ingresso = self.cleaned_data['ano_ingresso']
        questionario = self.cleaned_data['questionario']
        total_perguntas_objetivas = questionario.pergunta_set.filter(objetiva=True).count()
        respostas_subjetivas = Resposta.objects.filter(pergunta__id=pergunta.id, pergunta__objetiva=False)
        respostas = Resposta.objects.filter(pergunta__questionario=questionario)
        if uo:
            respostas_subjetivas = respostas_subjetivas.filter(uo=uo)
            respostas = respostas.filter(uo=uo)

        if not add_parcial:
            # Pega os identificadores das respostas que responderam todas as perguntas objetivas
            identificadores = (
                respostas.filter(pergunta__objetiva=True)
                .values('identificador')
                .annotate(count=Count('identificador'))
                .filter(count=total_perguntas_objetivas)
                .values_list('identificador', flat=True)
            )
            respostas_subjetivas = respostas_subjetivas.filter(identificador__in=identificadores)

        if questionario.publico == Questionario.ALUNO and (curso or ano_ingresso):
            identificadores = respostas_subjetivas.values_list('identificador', flat=True).distinct()
            alunos = Aluno.objects.filter(matricula__in=identificadores)
            if curso:
                alunos = alunos.filter(curso_campus__diretoria__setor__uo_id=uo.id, curso_campus__descricao_historico=curso.descricao_historico)

            if ano_ingresso:
                alunos = alunos.filter(data_matricula__year=ano_ingresso)

            identificadores = alunos.values_list('matricula', flat=True)
            respostas_subjetivas = respostas_subjetivas.filter(identificador__in=identificadores)

        return respostas_subjetivas

    def processar(self):
        uo = self.cleaned_data['uo']
        curso = self.cleaned_data['curso']
        add_parcial = self.cleaned_data["add_parcial"]
        ano_ingresso = self.cleaned_data['ano_ingresso']
        questionario = self.cleaned_data['questionario']
        respostas = Resposta.objects.filter(pergunta__questionario=questionario)
        total_perguntas_objetivas = questionario.pergunta_set.filter(objetiva=True).count()
        if uo:
            respostas = respostas.filter(uo=uo)

        if not add_parcial:
            # Pega os identificadores das respostas que responderam todas as perguntas objetivas
            identificadores = (
                respostas.filter(pergunta__objetiva=True)
                .values('identificador')
                .annotate(count=Count('identificador'))
                .filter(count=total_perguntas_objetivas)
                .values_list('identificador', flat=True)
            )
            respostas = respostas.filter(identificador__in=identificadores)

        if questionario.publico == Questionario.ALUNO and (curso or ano_ingresso):
            identificadores = respostas.filter(pergunta__objetiva=True).values_list('identificador', flat=True).distinct()
            alunos = Aluno.objects.filter(matricula__in=identificadores)
            if curso:
                alunos = alunos.filter(curso_campus__diretoria__setor__uo_id=uo.id, curso_campus__descricao_historico=curso.descricao_historico)

            if ano_ingresso:
                alunos = alunos.filter(data_matricula__year=ano_ingresso)

            identificadores = alunos.values_list('matricula', flat=True)
            respostas = respostas.filter(identificador__in=identificadores)

        categorias = questionario.get_categorias()
        opcoes = questionario.get_opcoes()
        groups = opcoes.values_list('nome', flat=True)
        grafico_empilhado_data = []
        for categoria in categorias:
            categoria.perguntas = []
            for pergunta in questionario.pergunta_set.filter(categoria=categoria):
                categoria.perguntas.append(pergunta)
                if pergunta.objetiva:
                    data = ['Opção']
                    pergunta.data = []
                    qtd_respostas_pergunta = respostas.filter(pergunta=pergunta).count()
                    pergunta.total = qtd_respostas_pergunta
                    for opcao in opcoes:
                        percent_respostas_opcao = 0
                        qtd_respostas_opcao = 0
                        if qtd_respostas_pergunta:
                            qtd_respostas_opcao = respostas.filter(pergunta=pergunta, opcao=opcao).count()
                            percent_respostas_opcao = round(float(qtd_respostas_opcao) / qtd_respostas_pergunta * 100, 2)
                        data.append(percent_respostas_opcao)
                        pergunta.data.append(qtd_respostas_opcao)
                    grafico = GroupedColumnChart(
                        'grafico{:d}'.format(pergunta.id),
                        title='{}'.format(pergunta),
                        subtitle='',
                        data=[data],
                        groups=groups,
                        minPointLength=0,
                        plotOptions_series_dataLabels_enable=True,
                        showDataLabels=True,
                        format='{point.y:.2f}%',
                        tooltip=dict(pointFormat='<span style="color:{series.color}">●</span> {series.name}: <b>{point.y:.2f}%</b><br/>'),
                    )
                    grafico.id = 'grafico{:d}'.format(pergunta.id)
                    pergunta.grafico = grafico

                    identificador_pergunta = pergunta.identificador or pergunta.ordem
                    grafico_empilhado_data.append([identificador_pergunta] + data[1:])

        grafico_empilhado = StackedGroupedColumnChart(
            'grafico_empilhado',
            title='{}'.format(questionario.descricao),
            subtitle='',
            data=grafico_empilhado_data,
            groups=groups,
            minPointLength=0,
            tooltip=dict(pointFormat='<span style="color:{series.color}">●</span> {series.name}: <b>{point.y:.2f}%</b><br/>'),
        )
        grafico_empilhado.id = 'grafico_empilhado'

        return [questionario, categorias, opcoes, grafico_empilhado]


class ResultadoAgrupadoForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Visualizar'
    EXTRA_BUTTONS = [dict(name='xls', value='Exportar para XLS')]
    ano = forms.IntegerField(label='Ano de Referência')
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.suap().filter(), label='Campus', required=False)
    add_parcial = forms.BooleanField(label='Adicionar Questionários Parciais', required=False)
    # Esse curso está só para levar em consideração a descrição historico
    curso = forms.ChainedModelChoiceField(
        CursoCampus.objects.all(),
        label='Curso do Aluno',
        empty_label='Selecione o Campus',
        required=False,
        obj_label='descricao_historico',
        url='/cpa/get_cursos/',
        form_filters=[('uo', 'diretoria__setor__uo_id')],
    )
    ano_ingresso = forms.IntegerField(label='Ano de Ingresso do Aluno', required=False)

    def processar(self):
        ano = self.cleaned_data['ano']
        add_parcial = self.cleaned_data["add_parcial"]
        uo = self.cleaned_data['uo']
        curso = self.cleaned_data['curso']
        ano_ingresso = self.cleaned_data['ano_ingresso']
        questionarios = Questionario.objects.filter(pergunta__questionario__ano=ano, campus=uo).distinct()
        questionario_agrupado = OrderedDict()
        nome_questionario_agrupado = None
        publicos = list()
        opcoes = list()
        for q in questionarios:
            publico = q.get_publico_display()
            if publico not in publicos:
                publicos.append(publico)

        publicos.sort()
        for questionario in questionarios:
            # coloca a descrição
            if nome_questionario_agrupado:
                if nome_questionario_agrupado != questionario.descricao:
                    return httprr('.', 'Questionário inconsistentes. Eles devem ter a mesma descrição.', 'error')
            else:
                nome_questionario_agrupado = questionario.descricao

            publico = questionario.get_publico_display()
            respostas = Resposta.objects.filter(pergunta__questionario=questionario)
            total_perguntas_objetivas = questionario.pergunta_set.filter(objetiva=True).count()
            if uo:
                respostas = respostas.filter(uo=uo)

            if not add_parcial:
                # Pega os identificadores das respostas que responderam todas as perguntas objetivas
                identificadores = (
                    respostas.filter(pergunta__objetiva=True)
                    .values('identificador')
                    .annotate(count=Count('identificador'))
                    .filter(count=total_perguntas_objetivas)
                    .values_list('identificador', flat=True)
                )
                respostas = respostas.filter(identificador__in=identificadores)

            if questionario.publico == Questionario.ALUNO and (curso or ano_ingresso):
                identificadores = respostas.filter(pergunta__objetiva=True).values_list('identificador', flat=True).distinct()
                alunos = Aluno.objects.filter(matricula__in=identificadores)
                if curso:
                    alunos = alunos.filter(curso_campus__diretoria__setor__uo_id=uo.id, curso_campus__descricao_historico=curso.descricao_historico)
                if ano_ingresso:
                    alunos = alunos.filter(data_matricula__year=ano_ingresso)

                identificadores = alunos.values_list('matricula', flat=True)
                respostas = respostas.filter(identificador__in=identificadores)

            categorias = questionario.get_categorias()
            opcoes = questionario.get_opcoes()
            questionario.categorias = []
            for categoria in categorias:
                nome_categoria = categoria.nome.strip()
                if nome_categoria not in questionario_agrupado:
                    questionario_agrupado[nome_categoria] = OrderedDict()

                categoria.perguntas = []
                questionario.categorias.append(categoria)
                for pergunta in questionario.pergunta_set.filter(categoria=categoria):
                    texto_pergunta = pergunta.texto.strip()
                    identificador_pergunta = pergunta.identificador or pergunta.ordem
                    categoria.perguntas.append(pergunta)
                    if pergunta.objetiva:
                        if identificador_pergunta not in questionario_agrupado[nome_categoria]:
                            questionario_agrupado[nome_categoria][identificador_pergunta] = OrderedDict()
                            questionario_agrupado[nome_categoria][identificador_pergunta]['texto_perguntas'] = set()
                            questionario_agrupado[nome_categoria][identificador_pergunta]['id'] = pergunta.id
                            questionario_agrupado[nome_categoria][identificador_pergunta]['qtd_respondentes'] = OrderedDict()

                        if publico not in questionario_agrupado[nome_categoria][identificador_pergunta]['qtd_respondentes']:
                            questionario_agrupado[nome_categoria][identificador_pergunta]['qtd_respondentes'][publico] = 0

                        questionario_agrupado[nome_categoria][identificador_pergunta]['texto_perguntas'].add(texto_pergunta)
                        qtd_respondentes = respostas.filter(pergunta=pergunta).count()
                        pergunta.qtd_respondentes = qtd_respondentes
                        questionario_agrupado[nome_categoria][identificador_pergunta]['qtd_respondentes'][publico] += qtd_respondentes
                        qtd_respondentes = questionario_agrupado[nome_categoria][identificador_pergunta]['qtd_respondentes'][publico]
                        pergunta.qtd_respostas_por_opcao = []
                        pergunta.porcentagem_respostas_por_opcao = []
                        for opcao in opcoes:
                            nome_opcao = opcao.nome.strip()
                            if nome_opcao not in questionario_agrupado[nome_categoria][identificador_pergunta]:
                                questionario_agrupado[nome_categoria][identificador_pergunta][nome_opcao] = OrderedDict()
                                for p in publicos:
                                    questionario_agrupado[nome_categoria][identificador_pergunta][nome_opcao][p] = OrderedDict()
                                    questionario_agrupado[nome_categoria][identificador_pergunta][nome_opcao][p]['qtd'] = 0
                                    questionario_agrupado[nome_categoria][identificador_pergunta][nome_opcao][p]['qtd_percent'] = 0

                            respostas_opcao = respostas.filter(pergunta=pergunta, opcao=opcao)
                            qtd_respostas = respostas_opcao.count()
                            pergunta.qtd_respostas_por_opcao.append(qtd_respostas)
                            percent_respostas = 0
                            if pergunta.qtd_respondentes:
                                percent_respostas = round(float(qtd_respostas) / pergunta.qtd_respondentes * 100, 2)
                            pergunta.porcentagem_respostas_por_opcao.append("{:.2f}%".format(percent_respostas))

                            questionario_agrupado[nome_categoria][identificador_pergunta][nome_opcao][publico]['qtd'] += qtd_respostas
                            qtd_respostas = questionario_agrupado[nome_categoria][identificador_pergunta][nome_opcao][publico]['qtd']
                            percent_respostas = 0
                            if qtd_respondentes:
                                percent_respostas = round(float(qtd_respostas) / qtd_respondentes * 100, 2)

                            questionario_agrupado[nome_categoria][identificador_pergunta][nome_opcao][publico]['qtd_percent'] = percent_respostas
                            questionario_agrupado[nome_categoria][identificador_pergunta][nome_opcao][publico]['percent'] = "{:.2f}%".format(percent_respostas)

                            if questionario.publico == Questionario.ALUNO:
                                identificadores = respostas_opcao.values_list('identificador', flat=True).distinct()
                                alunos = Aluno.objects.filter(matricula__in=identificadores)
                                id_grafico = 'grafico_faixa_etaria_{}_{:d}'.format(nome_opcao.lower().replace(" ", "_"), pergunta.id)
                                questionario_agrupado[nome_categoria][identificador_pergunta][nome_opcao]['id_grafico_faixa_etaria'] = id_grafico
                                questionario_agrupado[nome_categoria][identificador_pergunta][nome_opcao]['grafico_faixa_etaria'] = self.gerar_grafico_faixa_etaria(
                                    id_grafico, alunos, nome_opcao
                                )

        for nome_categoria in questionario_agrupado:
            for identificador_pergunta in questionario_agrupado[nome_categoria]:
                series = []
                questionario_opcoes = questionario.questionarioopcao_set.order_by('ordem')
                dados = OrderedDict()
                for questionario_opcao in questionario_opcoes:
                    agrupamento = questionario_opcao.agrupamento or questionario_opcao.opcao.nome
                    if agrupamento not in dados:
                        dados[agrupamento] = OrderedDict()

                    for publico in publicos:
                        if publico not in dados[agrupamento]:
                            dados[agrupamento][publico] = []

                        valores = questionario_agrupado[nome_categoria][identificador_pergunta][questionario_opcao.opcao.nome][publico]
                        dados[agrupamento][publico].append(valores and valores.get('qtd_percent', 0) or 0)

                for opcao, publicos_dados in list(dados.items()):
                    dado = [opcao]
                    for publico, valores in list(publicos_dados.items()):
                        dado.append(sum(dados[opcao][publico]))

                    series.append(dado)

                id = questionario_agrupado[nome_categoria][identificador_pergunta]['id']
                grafico = GroupedColumnChart(
                    'grafico{:d}'.format(id),
                    title='{}'.format(identificador_pergunta),
                    subtitle='',
                    data=series,
                    groups=publicos,
                    minPointLength=0,
                    plotOptions_series_dataLabels_enable=True,
                    showDataLabels=True,
                    format='{point.y:.2f}%',
                    tooltip=dict(pointFormat='<span style="color:{series.color}">●</span> {series.name}: <b>{point.y:.2f}%</b><br/>'),
                )
                grafico.id = 'grafico{:d}'.format(id)
                questionario_agrupado[nome_categoria][identificador_pergunta]['grafico'] = grafico

        return [questionarios, questionario_agrupado, opcoes, publicos, nome_questionario_agrupado]

    def gerar_grafico_faixa_etaria(self, id_grafico, alunos, nome_opcao):
        from djtools.utils import get_age

        nascimentos = alunos.values_list('pessoa_fisica__nascimento_data').annotate(count=Count('pessoa_fisica__nascimento_data')).order_by('-count')
        dados = list()
        dados_ate_18 = 0
        dados_19_29 = 0
        dados_30_40 = 0
        dados_acima_40 = 0
        for dado in nascimentos:
            nascimento = dado[0]
            qtd = dado[1]
            idade = get_age(nascimento)
            if idade <= 18:
                dados_ate_18 += qtd
            elif 19 <= idade <= 29:
                dados_19_29 += qtd
            elif 30 <= idade <= 40:
                dados_30_40 += qtd
            elif idade > 40:
                dados_acima_40 += qtd

        dados.append(['Até 18 anos', dados_ate_18])
        dados.append(['De 19 à 29 anos', dados_19_29])
        dados.append(['De 30 à 40 anos', dados_30_40])
        dados.append(['Acima de 40 anos', dados_acima_40])

        grafico = PieChart(id_grafico, title='Alunos respondentes por faixa etária da opção {}'.format(nome_opcao), subtitle='', data=dados, minPointLength=0)
        grafico.id = id_grafico
        return grafico

    def processar_xls(self):
        [questionarios, questionario_agrupado, opcoes, publicos, nome_questionario_agrupado] = self.processar()
        import xlwt
        from django.http.response import HttpResponse
        from djtools.utils import human_str

        name = 'report'
        encoding = 'iso8859-1'
        value_for_none = '-'
        response = HttpResponse(content_type="application/ms-excel")
        response['Content-Disposition'] = 'attachment; filename={}.xls'.format(name.encode(encoding))
        wb = xlwt.Workbook(encoding=encoding)
        for questionario in questionarios:
            row_idx = 0
            sheet = wb.add_sheet(questionario.get_publico_display())
            for categoria in questionario.categorias:
                col_idx = 0
                sheet.write(row_idx, col_idx, label=human_str(categoria, encoding=encoding, blank=value_for_none))
                col_idx += 1
                for idx, opcao in enumerate(opcoes):
                    sheet.write(row_idx, col_idx, label=human_str("{}".format(opcao), encoding=encoding, blank=value_for_none))
                    col_idx += 1

                for idx, opcao in enumerate(opcoes):
                    sheet.write(row_idx, col_idx, label=human_str("Porcentagem de {}".format(opcao), encoding=encoding, blank=value_for_none))
                    col_idx += 1

                sheet.write(row_idx, col_idx, label=human_str("N. Respondentes", encoding=encoding, blank=value_for_none))
                col_idx += 1
                row_idx += 1
                for idx, pergunta in enumerate(categoria.perguntas):
                    col_idx = 0
                    if pergunta.objetiva:
                        sheet.write(row_idx, col_idx, label=human_str("{:d}. {}".format(idx, pergunta), encoding=encoding, blank=value_for_none))
                        col_idx += 1

                        for qtd_respostas in pergunta.qtd_respostas_por_opcao:
                            sheet.write(row_idx, col_idx, label=human_str("{}".format(qtd_respostas), encoding=encoding, blank=value_for_none))
                            col_idx += 1

                        for porcentagem_respostas in pergunta.porcentagem_respostas_por_opcao:
                            sheet.write(row_idx, col_idx, label=human_str("{}".format(porcentagem_respostas), encoding=encoding, blank=value_for_none))
                            col_idx += 1

                        sheet.write(row_idx, col_idx, label=human_str("{}".format(pergunta.qtd_respondentes), encoding=encoding, blank=value_for_none))
                        col_idx += 1
                        row_idx += 1

        sheet = wb.add_sheet("Agrupado")
        row_idx = 0
        for categoria, perguntas in list(questionario_agrupado.items()):
            col_idx = 0
            sheet.write_merge(row_idx, row_idx + 1, col_idx, col_idx, human_str("{}".format(categoria), encoding=encoding, blank=value_for_none))
            col_idx += 1

            for opcao in opcoes:
                sheet.write_merge(row_idx, row_idx, col_idx, col_idx + len(publicos) - 1, human_str("{}".format(opcao.nome), encoding=encoding, blank=value_for_none))
                col_idx += len(publicos)

            col_idx = 0
            col_idx += 1
            row_idx += 1
            for opcao in opcoes:
                for publico in publicos:
                    sheet.write(row_idx, col_idx, label=human_str("{}".format(publico), encoding=encoding, blank=value_for_none))
                    col_idx += 1

            row_idx += 1
            for pergunta, opcoes_respostas in list(perguntas.items()):
                col_idx = 0
                sheet.write(row_idx, col_idx, label=human_str(' '.join(opcoes_respostas['texto_perguntas']), encoding=encoding, blank=value_for_none))
                col_idx += 1
                for opcao in opcoes:
                    for publico in publicos:
                        for opcao_resposta, publicos_respostas in list(opcoes_respostas.items()):
                            if hasattr(publicos_respostas, '__iter__') and hasattr(publicos_respostas, '__dict__'):
                                for publico_resposta, dados in list(publicos_respostas.items()):
                                    if opcao_resposta == opcao.nome and publico_resposta == publico:
                                        if dados:
                                            sheet.write(row_idx, col_idx, label=human_str("{}".format(dados.get('percent', '')), encoding=encoding, blank=value_for_none))
                                        else:
                                            sheet.write(row_idx, col_idx, label=human_str("", encoding=encoding, blank=value_for_none))
                                        col_idx += 1
                row_idx += 1

        wb.save(response)
        return response


class ResultadoPorCursoForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Visualizar'
    questionario = forms.ModelChoiceField(Questionario.objects.filter(publico=Questionario.ALUNO).order_by('-id'), label='Questionário')
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.suap().filter(), label='Campus', required=False)
    add_parcial = forms.BooleanField(label='Adicionar questionários parciais', required=False)

    def processar(self):
        add_parcial = self.cleaned_data["add_parcial"]
        questionario = self.cleaned_data["questionario"]
        respostas = Resposta.objects.filter(pergunta__questionario=questionario)
        total_perguntas_objetivas = questionario.pergunta_set.filter(objetiva=True).count()
        if self.cleaned_data['uo']:
            respostas = respostas.filter(uo=self.cleaned_data['uo'])

        if not add_parcial:
            # Pega os identificadores das respostas que responderam todas as perguntas objetivas
            identificadores = (
                respostas.filter(pergunta__objetiva=True)
                .values('identificador')
                .annotate(count=Count('identificador'))
                .filter(count=total_perguntas_objetivas)
                .values_list('identificador', flat=True)
            )
            respostas = respostas.filter(identificador__in=identificadores)

        identificadores = respostas.filter(pergunta__objetiva=True).values_list('identificador', flat=True)
        alunos = Aluno.objects.filter(matricula__in=identificadores)

        graficos = []
        # Alunos: 5 cursos com maior participação de respondentes
        # descricao_historico identifica o mesmo curso no campus e/ou no campi
        cursos = alunos.values_list('curso_campus__descricao_historico').annotate(count=Count('curso_campus__descricao_historico')).order_by('-count')[:5]
        cursos_serie = list()
        for curso in cursos:
            cursos_serie.append([curso[0], curso[1]])

        grafico = ColumnChart(
            'grafico_cursos',
            title='Cursos com maior número de respondentes',
            subtitle='',
            data=cursos_serie,
            minPointLength=0,
            plotOptions_series_dataLabels_enable=True,
            showDataLabels=True,
        )

        grafico.id = 'grafico_cursos'
        graficos.append(grafico)

        # Alunos: perfil dos respondentes por faixa etária
        from djtools.utils import get_age

        nascimentos = alunos.values_list('pessoa_fisica__nascimento_data').annotate(count=Count('pessoa_fisica__nascimento_data')).order_by('-count')
        dados = list()
        dados_ate_18 = 0
        dados_19_29 = 0
        dados_30_40 = 0
        dados_acima_40 = 0
        for dado in nascimentos:
            nascimento = dado[0]
            qtd = dado[1]
            idade = get_age(nascimento)
            if idade <= 18:
                dados_ate_18 += qtd
            elif 19 <= idade <= 29:
                dados_19_29 += qtd
            elif 30 <= idade <= 40:
                dados_30_40 += qtd
            elif idade > 40:
                dados_acima_40 += qtd

        dados.append(['Até 18 anos', dados_ate_18])
        dados.append(['De 19 à 29 anos', dados_19_29])
        dados.append(['De 30 à 40 anos', dados_30_40])
        dados.append(['Acima de 40 anos', dados_acima_40])

        grafico = PieChart('grafico_idade', title='Alunos respondentes por faixa etária', subtitle='', data=dados, minPointLength=0)
        grafico.id = 'grafico_idade'
        graficos.append(grafico)

        # Alunos: perfil dos respondentes por ano de ingresso no curso
        anos = alunos.values_list('ano_letivo__ano').annotate(count=Count('ano_letivo__ano')).order_by('-count')
        from datetime import date

        ano_corrente = date.today().year
        dados = list()
        dados_acima_2 = 0
        for dado in anos:
            ano = dado[0]
            qtd = dado[1]
            tempo_decorrido = ano_corrente - ano
            if tempo_decorrido == 1:
                dados.append(['Até {:d} ano'.format(tempo_decorrido), qtd])
            elif tempo_decorrido >= 3:
                dados_acima_2 += qtd
            else:
                dados.append(['Até {:d} anos'.format(tempo_decorrido), qtd])

        dados.append(['Acima de 2 anos', dados_acima_2])

        grafico = PieChart('grafico_ano', title='Alunos respondentes por tempo decorrido desde o ingresso', subtitle='', data=dados, minPointLength=0)
        grafico.id = 'grafico_ano'
        graficos.append(grafico)

        return graficos


class PaiAlunoForm(forms.FormPlus):
    identificacao = forms.BrCpfField(label='CPF do Pai')
    cpf = forms.BrCpfField(label='CPF do Aluno')
    matricula = forms.CharField(label='Matrícula do Aluno')

    def clean_matricula(self):
        try:
            self.aluno = Aluno.objects.get(matricula=self.cleaned_data['matricula'])
        except Exception:
            raise forms.ValidationError('Aluno não encontrado')

        if self.aluno.pessoa_fisica.cpf != self.data['cpf']:
            raise forms.ValidationError('A matrícula e o CPF do aluno não conferem')

        return self.cleaned_data['matricula']


def get_uos_as_choices():
    choices = []
    for uo in UnidadeOrganizacional.objects.suap().all():
        choices.append([uo.pk, uo.nome])
    return choices


class EmpresaForm(forms.FormPlus):
    identificacao = forms.BrCpfField(label='CPF do Representante')
    cnpj = forms.BrCnpjField(label='CNPJ da Empresa')
    uo = forms.ChoiceField(label='Campus')

    def __init__(self, *args, **kwargs):
        super(EmpresaForm, self).__init__(*args, **kwargs)
        self.fields['uo'].choices = get_uos_as_choices()


def ResponderQuestionarioFormFactory(request, opcoes, categorias):
    fields = dict()
    fieldsets = list()
    for categoria in categorias:
        fields_list = list()
        for pergunta in categoria.perguntas.all():
            field_name = '{}'.format(pergunta.id)
            resposta = pergunta.get_resposta(request)
            if pergunta.objetiva:
                initial = None
                if resposta.opcao:
                    initial = resposta.opcao.id
                field = forms.ModelChoiceField(
                    label=mark_safe("{:d} - {}".format(pergunta.ordem, pergunta.get_html())),
                    initial=initial,
                    queryset=opcoes,
                    widget=forms.RadioSelect(),
                    empty_label=None,
                    required=False,
                )
            else:
                field = forms.CharField(label=pergunta, initial=resposta.resposta, widget=forms.Textarea, required=False)
            fields[field_name] = field
            fields_list.append(field_name)

        # Usado para manter a ordenação dos campos
        fieldsets.append((categoria.nome, {'fields': fields_list}))

    def clean(self):
        error_fields_name = list()
        for categoria in categorias:
            mostrar_erro = False
            for pergunta in categoria.perguntas.filter(objetiva=True):
                field_name = '{}'.format(pergunta.id)
                if self.cleaned_data.get('{}'.format(pergunta.id)):
                    mostrar_erro = True
                else:
                    error_fields_name.append(field_name)

            if mostrar_erro and error_fields_name:
                self.errors['__all__'] = ['Só é permitido salvar uma dimensão se as perguntas objetivas estiverem completamente respondidas.']
                for field_name in error_fields_name:
                    self.errors[field_name] = ['É obrigatório responder todas as perguntas objetivas de cada categoria para salvar.']

            else:
                error_fields_name = list()

        return self.cleaned_data

    @transaction.atomic()
    def save(self, *args, **kwargs):
        for categoria in categorias:
            for pergunta in categoria.perguntas.all():
                field_name = '{}'.format(pergunta.id)
                resposta = pergunta.get_resposta(request)
                if pergunta.objetiva:
                    resposta.opcao = self.cleaned_data.get(field_name)
                    if not resposta.opcao:
                        continue
                else:
                    resposta.resposta = self.cleaned_data.get(field_name)
                    if not resposta.resposta:
                        continue
                resposta.save()

    return type(
        'ResponderQuestionarioForm', (forms.BaseForm,), {'base_fields': fields, 'METHOD': 'POST', 'fieldsets': fieldsets, 'clean': clean, 'save': save, 'categorias': categorias}
    )


class QuestionarioForm(forms.ModelFormPlus):
    campus = forms.ModelMultipleChoiceField(label='Campi', queryset=UnidadeOrganizacional.objects.suap().all(), widget=FilteredSelectMultiple('', True), required=False)

    class Meta:
        model = Questionario
        exclude = ()
