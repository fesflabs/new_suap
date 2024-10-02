# -*- coding: utf-8 -*-
import datetime

from django.conf import settings
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.db.models.aggregates import Max
from django.db.transaction import atomic

from comum.models import Ano, User
from djtools.db import models
from djtools.forms.widgets import CheckboxSelectMultiplePlus
from djtools.utils import send_mail
from edu.models import Modalidade, Aluno, CursoCampus, Turma, ProfessorDiario, Diario, FormaIngresso
from rh.models import AreaVinculacao, UnidadeOrganizacional, Servidor, Situacao


class Eixo(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')
    ordem = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = 'Eixo'
        verbose_name_plural = 'Eixos'
        ordering = ('ordem',)

    def __str__(self):
        return self.descricao

    def save(self):
        if not self.ordem:
            self.ordem = (Eixo.objects.all().aggregate(Max('ordem')).get('ordem__max', 0) or 0) + 1
        super(Eixo, self).save()


class Dimensao(models.ModelPlus):
    eixo = models.ForeignKeyPlus(Eixo, verbose_name='Eixo', on_delete=models.CASCADE)
    descricao = models.CharFieldPlus('Descrição')
    ordem = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = 'Dimensão'
        verbose_name_plural = 'Dimensões'
        ordering = ('eixo', 'ordem')

    def __str__(self):
        return self.descricao

    def save(self):
        if not self.ordem:
            self.ordem = (Dimensao.objects.filter(eixo=self.eixo).aggregate(Max('ordem')).get('ordem__max', 0) or 0) + 1
        super(Dimensao, self).save()


class Macroprocesso(models.ModelPlus):
    dimensao = models.ForeignKeyPlus(Dimensao, verbose_name='Dimensão', on_delete=models.CASCADE)
    descricao = models.CharFieldPlus('Descrição')
    ordem = models.IntegerField(blank=True, null=True)

    class Meta:
        verbose_name = 'Macroprocesso'
        verbose_name_plural = 'Macroprocessos'
        ordering = ('dimensao__eixo', 'dimensao', 'ordem')

    def __str__(self):
        return self.descricao

    def save(self):
        if not self.ordem:
            self.ordem = (Macroprocesso.objects.filter(dimensao=self.dimensao).aggregate(Max('ordem')).get('ordem__max', 0) or 0) + 1
        super(Macroprocesso, self).save()


class TipoAvaliacao(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Tipo de Avaliação'
        verbose_name_plural = 'Tipos de Avaliação'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao


class Segmento(models.ModelPlus):
    CPA_CENTRAL = 1
    CPA_CAMPUS = 2
    GESTOR = 3
    DOCENTE = 6
    TECNICO = 4
    ETEP = 5
    ESTUDANTE = 7
    DESLIGADO = 8
    EGRESSO = 9
    PAIS = 10
    EMPRESAS = 11
    SOCIEDADE_CIVIL = 12

    SERVIDORES = [GESTOR, DOCENTE, TECNICO, ETEP, CPA_CENTRAL, CPA_CAMPUS]
    ALUNOS = [ESTUDANTE, EGRESSO]
    EXTERNOS = [PAIS, DESLIGADO, EMPRESAS, SOCIEDADE_CIVIL]

    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Segmento Respondente'
        verbose_name_plural = 'Segmentos Respondentes'
        ordering = ('id',)

    def __str__(self):
        return self.descricao


class Indicador(models.ModelPlus):
    TEXTO_CURTO = 1
    TEXTO_LONGO = 2
    NUMERO_INTEIRO = 3
    NUMERO_DECIMAL = 4
    UNICA_ESCOLHA = 5
    MULTIPLA_ESCOLHA = 6
    CONJUNTO_VARIAVEIS = 7
    FAIXA_NUMERICA = 8
    GRAU_SATISFACAO = 9

    TIPO_CHOICES = [
        [TEXTO_CURTO, 'Texto Curto'],
        [TEXTO_LONGO, 'Texto Longo'],
        [NUMERO_INTEIRO, 'Número Inteiro'],
        [NUMERO_DECIMAL, 'Número Decimal'],
        [FAIXA_NUMERICA, 'Escala Padrão'],
        [GRAU_SATISFACAO, 'Grau de Satisfação'],
        [UNICA_ESCOLHA, 'Única Escolha'],
        [MULTIPLA_ESCOLHA, 'Múltipla Escolha'],
        [CONJUNTO_VARIAVEIS, 'Conjunto de Variáveis'],
    ]

    INDICADORES_AUTOCALCULADOS = {
        'Unidade de vinculação': 'get_unidade_vinculacao',
        'Modalidade de vinculação': 'get_modalidade_vinculacao',
        'Curso de vinculação': 'get_curso_vinculacao',
        'Ano de ingresso': 'get_ano_ingresso_curso',
        'Forma de ingresso': 'get_forma_ingresso_curso',
        'Série/Período no curso': 'get_serie_periodo_curso',
        'Área de atuação': 'get_area_atuacao_servidor',
        'Cargo': 'get_cargo_servidor',
        'Função': 'get_funcao_servidor',
        'Regime de trabalho - servidor': 'get_regime_trabalho_servidor',
        'Tipo de contrato': 'get_forma_contratacao_servidor',
        'Data de nascimento': 'get_data_nascimento',
        'Tipo de ação afirmativa': 'get_tipo_acao_afirmativa',
    }

    # Dados Gerais
    macroprocesso = models.ForeignKeyPlus(Macroprocesso, verbose_name='Macroprocessos')
    nome = models.CharFieldPlus('Denominação do Indicador', width=500)
    texto_ajuda = models.TextField('Texto de Ajuda', blank=True, null=True)
    aspecto = models.CharFieldPlus('Critério de Análise', width=500)
    subsidio_para = models.ManyToManyFieldPlus(TipoAvaliacao, verbose_name='Subsídio p/ Avaliações')
    anos_referencia = models.ManyToManyField(Ano, verbose_name='Anos de Referência')
    ordem = models.IntegerField(blank=True, null=True)
    em_uso = models.BooleanField('Em uso', default=True)
    tipo = models.IntegerField(choices=[[0, 'Qualitativo'], [1, 'Quantitativo']], default=0)
    automatico = models.BooleanField('Autocalculado', default=False)
    obrigatorio = models.BooleanField('Resposta Obrigatória', default=True)
    gestor_responde_como_docente = models.BooleanField('Gestor responde também como Docente', default=False)

    # Detalhamento
    segmentos = models.ManyToManyFieldPlus(Segmento, verbose_name='Segmentos Respondentes')
    areas_vinculacao = models.ManyToManyFieldPlus(AreaVinculacao, verbose_name='Áreas')
    modalidades = models.ManyToManyFieldPlus(Modalidade, verbose_name='Modalidades')
    periodo_curso = models.IntegerField(
        'Período Mínimo', help_text='Período mínimo do estudante no curso', choices=[[1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6], [7, 7], [8, 8]], default=1
    )

    uos = models.ManyToManyFieldPlus(UnidadeOrganizacional, verbose_name='Campi')

    # Unidades relacionadas
    envolve_reitoria = models.BooleanField('Reitoria', default=True)
    envolve_campus_ead = models.BooleanField('Campus EAD', default=True)
    envolve_campus_produtivos = models.BooleanField('Campus com Unidade Produtiva', default=True)
    envolve_campus_nao_produtivos = models.BooleanField('Campus sem Unidade Produtiva', default=True)

    # Tipo
    tipo_resposta = models.IntegerField(choices=TIPO_CHOICES, verbose_name='Tipo')
    valor_minimo = models.IntegerField('Valor Mínimo', null=True, blank=True)
    valor_maximo = models.IntegerField('Valor Máximo', null=True, blank=True)
    formula = models.CharFieldPlus('Fórmula', null=True, blank=True)

    class Meta:
        verbose_name = 'Indicador'
        verbose_name_plural = 'Indicadores'
        ordering = ('macroprocesso__dimensao__eixo__ordem', 'macroprocesso__dimensao__ordem', 'macroprocesso__ordem', 'ordem')

    def __str__(self):
        return self.nome

    def get_absolute_url(self):
        return '/avaliacao_integrada/indicador/{}/'.format(self.pk)

    def get_form_field(self, respondente=None, objeto=None):
        from djtools import forms as fields
        from django.forms import widgets

        lista = []
        if self.tipo_resposta == Indicador.CONJUNTO_VARIAVEIS:
            for variavel in self.variavel_set.all():
                lista.append(variavel.get_form_field(respondente, objeto))
        else:
            if self.tipo_resposta == Indicador.TEXTO_CURTO:
                field = fields.CharField(label=self.aspecto, required=False)
            elif self.tipo_resposta == Indicador.TEXTO_LONGO:
                field = fields.CharField(label=self.aspecto, required=False, widget=widgets.Textarea())
            elif self.tipo_resposta == Indicador.NUMERO_INTEIRO:
                field = fields.IntegerField(label=self.aspecto, required=self.obrigatorio, min_value=self.valor_minimo, max_value=self.valor_maximo)
            elif self.tipo_resposta == Indicador.NUMERO_DECIMAL:
                field = fields.DecimalField(label=self.aspecto, required=False)
            elif self.tipo_resposta == Indicador.UNICA_ESCOLHA:
                choices = [[x, x] for x in self.opcaoresposta_set.all()]
                field = fields.ChoiceField(label=self.aspecto, required=False, choices=choices, widget=widgets.RadioSelect())
            elif self.tipo_resposta == Indicador.MULTIPLA_ESCOLHA:
                choices = [[x, x] for x in self.opcaoresposta_set.all()]
                field = fields.MultipleChoiceField(label=self.aspecto, required=False, choices=choices, widget=CheckboxSelectMultiplePlus())

            elif self.tipo_resposta == Indicador.FAIXA_NUMERICA:
                choices = [[0, 'Desconheço'], [1, '1'], [2, '2'], [3, '3'], [4, '4'], [5, '5'], [9, 'Não se aplica']]
                field = fields.ChoiceField(label=self.aspecto, required=False, choices=choices, widget=widgets.RadioSelect())

            elif self.tipo_resposta == Indicador.GRAU_SATISFACAO:
                choices = [[0, 'Desconheço'], [1, 'Muito Insatisfeito'], [2, 'Insatisfeito'], [3, 'Neutro'], [4, 'Satisfeito'], [5, 'Muito Satisfeito'], [9, 'Não se aplica']]
                field = fields.ChoiceField(label=self.aspecto, required=False, choices=choices, widget=widgets.RadioSelect())

            if self.nome in Indicador.INDICADORES_AUTOCALCULADOS:
                if not self.nome in ['Unidade de vinculação', 'Modalidade de vinculação', 'Curso de vinculação', 'Data de nascimento', 'Ano de ingresso', 'Forma de ingresso']:
                    if respondente:
                        field.initial = getattr(respondente, Indicador.INDICADORES_AUTOCALCULADOS[self.nome])()
                    field.widget.attrs['readonly'] = True
                else:
                    # Unidade de Vinculação
                    if self.nome in ['Unidade de vinculação'] and respondente.segmento_id in [Segmento.PAIS, Segmento.DESLIGADO, Segmento.SOCIEDADE_CIVIL]:
                        choices = [[x, x] for x in UnidadeOrganizacional.objects.suap().all()]
                        field = fields.ChoiceField(label=self.aspecto, required=False, choices=choices)
                    elif self.nome in ['Unidade de vinculação'] and respondente.segmento_id in [Segmento.EMPRESAS]:
                        choices = [[x, x] for x in UnidadeOrganizacional.objects.suap().all()]
                        field = fields.MultipleChoiceField(label=self.aspecto, required=False, choices=choices, widget=CheckboxSelectMultiplePlus())
                    elif self.nome in ['Unidade de vinculação'] and respondente.segmento_id in [Segmento.ESTUDANTE]:
                        field.initial = respondente.get_unidade_vinculacao()
                        field.widget.attrs['readonly'] = True
                    elif self.nome in ['Unidade de vinculação'] and not respondente.segmento_id in [
                        Segmento.PAIS,
                        Segmento.DESLIGADO,
                        Segmento.SOCIEDADE_CIVIL,
                        Segmento.EMPRESAS,
                        Segmento.ESTUDANTE,
                    ]:
                        field.initial = respondente.get_unidade_atuacao_servidor()
                        field.widget.attrs['readonly'] = True

                    # Modalidade de Vinculação
                    if self.nome in ['Modalidade de vinculação'] and respondente.segmento_id in [Segmento.PAIS, Segmento.DESLIGADO]:
                        if respondente.segmento_id in [Segmento.PAIS]:
                            choices = [[x, x] for x in Modalidade.objects.filter(descricao='Técnico Integrado')]
                        else:
                            # choices = [[x, x] for x in Modalidade.objects.all()]
                            choices = [
                                [x, x]
                                for x in Modalidade.objects.exclude(
                                    descricao__in=['FIC', 'Proeja FIC Fundamental', 'Aperfeiçoamento', 'Doutorado', 'Especialização', 'Engenharia', 'Mestrado']
                                )
                            ]
                        field = fields.ChoiceField(label=self.aspecto, required=False, choices=choices)
                    elif self.nome in ['Modalidade de vinculação'] and respondente.segmento_id in [Segmento.EMPRESAS]:
                        choices = [
                            [x, x]
                            for x in Modalidade.objects.exclude(
                                descricao__in=['FIC', 'Proeja FIC Fundamental', 'Aperfeiçoamento', 'Doutorado', 'Especialização', 'Engenharia', 'Mestrado']
                            )
                        ]
                        field = fields.MultipleChoiceField(label=self.aspecto, required=False, choices=choices, widget=CheckboxSelectMultiplePlus())
                    elif self.nome in ['Modalidade de vinculação'] and respondente.segmento_id in [Segmento.ESTUDANTE]:
                        field.initial = respondente.get_modalidade_vinculacao()
                        field.widget.attrs['readonly'] = True
                    elif self.nome in ['Modalidade de vinculação'] and not respondente.segmento_id in [
                        Segmento.PAIS,
                        Segmento.DESLIGADO,
                        Segmento.SOCIEDADE_CIVIL,
                        Segmento.EMPRESAS,
                        Segmento.ESTUDANTE,
                    ]:
                        choices = [[x, x] for x in Modalidade.objects.filter(cursocampus__ativo=True, cursocampus__diretoria__setor__uo=respondente.uo).distinct()]
                        field = fields.MultipleChoiceField(label=self.aspecto, required=False, choices=choices, widget=CheckboxSelectMultiplePlus())
                        field.initial = (
                            Modalidade.objects.filter(cursocampus__ativo=True, cursocampus__diretoria__setor__uo=respondente.uo).distinct().values_list('descricao', flat=True)
                        )

                    # Curso de Vinculação
                    if self.nome in ['Curso de vinculação'] and respondente.segmento_id in [Segmento.PAIS, Segmento.DESLIGADO]:
                        if respondente.segmento_id in [Segmento.PAIS]:
                            choices = [
                                [x.descricao_historico, x.descricao_historico]
                                for x in CursoCampus.objects.filter(ativo=True, modalidade__descricao='Técnico Integrado').order_by('descricao_historico').distinct()
                            ]
                        else:
                            # choices = [[x.descricao_historico, x.descricao_historico] for x in CursoCampus.objects.filter(ativo=True)]
                            choices = [
                                [x.descricao_historico, x.descricao_historico]
                                for x in CursoCampus.objects.filter(ativo=True)
                                .exclude(modalidade__descricao__in=['FIC', 'Proeja FIC Fundamental', 'Aperfeiçoamento', 'Doutorado', 'Especialização', 'Engenharia', 'Mestrado'])
                                .order_by('descricao_historico')
                                .distinct()
                            ]
                        field = fields.ChoiceField(label=self.aspecto, required=False, choices=choices)
                    elif self.nome in ['Curso de vinculação'] and respondente.segmento_id in [Segmento.EMPRESAS]:
                        choices = [
                            [x.descricao_historico, x.descricao_historico]
                            for x in CursoCampus.objects.filter(ativo=True)
                            .exclude(modalidade__descricao__in=['FIC', 'Proeja FIC Fundamental', 'Aperfeiçoamento', 'Doutorado', 'Especialização', 'Engenharia', 'Mestrado'])
                            .order_by('descricao_historico')
                            .distinct()
                        ]
                        field = fields.MultipleChoiceField(label=self.aspecto, required=False, choices=choices, widget=CheckboxSelectMultiplePlus())
                    elif self.nome in ['Curso de vinculação'] and respondente.segmento_id in [Segmento.ESTUDANTE]:
                        field.initial = respondente.get_curso_vinculacao()
                        field.widget.attrs['readonly'] = True
                    elif self.nome in ['Curso de vinculação'] and not respondente.segmento_id in [
                        Segmento.PAIS,
                        Segmento.DESLIGADO,
                        Segmento.SOCIEDADE_CIVIL,
                        Segmento.EMPRESAS,
                        Segmento.ESTUDANTE,
                    ]:
                        choices = [
                            [x.descricao_historico, x.descricao_historico]
                            for x in CursoCampus.objects.filter(diretoria__setor__uo=respondente.uo, ativo=True).order_by('descricao_historico').distinct()
                        ]
                        field = fields.MultipleChoiceField(label=self.aspecto, required=False, choices=choices, widget=CheckboxSelectMultiplePlus())
                        field.initial = (
                            CursoCampus.objects.filter(diretoria__setor__uo=respondente.uo, ativo=True)
                            .order_by('descricao_historico')
                            .distinct()
                            .values_list('descricao_historico', flat=True)
                        )

                    # Data de Nascimento
                    if self.nome == 'Data de nascimento':
                        field = fields.DateFieldPlus(label=self.aspecto, required=False)
                        if not respondente.segmento_id in [Segmento.PAIS, Segmento.DESLIGADO, Segmento.SOCIEDADE_CIVIL, Segmento.EMPRESAS]:
                            field.initial = getattr(respondente, Indicador.INDICADORES_AUTOCALCULADOS[self.nome])()
                            field.widget.attrs['readonly'] = True

                    # Ano de Ingresso
                    if self.nome == 'Ano de ingresso' and respondente.segmento_id in [Segmento.ESTUDANTE]:
                        field.initial = respondente.get_ano_ingresso_curso()
                        field.widget.attrs['readonly'] = True
                    elif self.nome == 'Ano de ingresso' and not respondente.segmento_id in [Segmento.ESTUDANTE]:
                        choices = [[x.ano, x.ano] for x in Ano.objects.all()]
                        field = fields.ChoiceField(label=self.aspecto, required=False, choices=choices)

                    # Forma de Ingresso
                    if self.nome == 'Forma de ingresso' and respondente.segmento_id in [Segmento.ESTUDANTE]:
                        field.initial = respondente.get_forma_ingresso_curso()
                        field.widget.attrs['readonly'] = True
                    elif self.nome == 'Forma de ingresso' and not respondente.segmento_id in [Segmento.ESTUDANTE]:
                        choices = [[x.descricao, x.descricao] for x in FormaIngresso.objects.all()]
                        field = fields.ChoiceField(label=self.aspecto, required=False, choices=choices)

            field.name = Resposta.to_identificador(self.id, respondente and respondente.id or 'field', 0, objeto)
            lista.append(field)
        return lista

    def save(self):
        if not self.ordem:
            self.ordem = (Indicador.objects.filter(macroprocesso=self.macroprocesso).aggregate(Max('ordem')).get('ordem__max', 0) or 0) + 1
        super(Indicador, self).save()

    def filtrar_respondentes(self, respondentes):
        pass


class Iterador(models.ModelPlus):
    CURSO = 'edu.CursoCampus'
    MODALIDADE = 'edu.Modalidade'
    PROFESSOR = 'edu.Professor'
    TURMA = 'edu.Turma'

    OBJETOS_CHOICES = [[CURSO, 'Curso'], [MODALIDADE, 'Modalidade'], [PROFESSOR, 'Professor'], [TURMA, 'Turma']]

    indicador = models.ForeignKeyPlus(Indicador, verbose_name='Indicador', on_delete=models.CASCADE)
    segmento = models.ForeignKeyPlus(Segmento, verbose_name='Segmento', on_delete=models.CASCADE)
    objeto = models.CharFieldPlus(choices=OBJETOS_CHOICES)

    class Meta:
        verbose_name = 'Iterador'
        verbose_name_plural = 'Iteradores'
        ordering = ('id',)

    def __str__(self):
        return '{}'.format(self.pk)


class Variavel(models.ModelPlus):
    TIPO_CHOICES = [[Indicador.NUMERO_INTEIRO, 'Número Inteiro'], [Indicador.NUMERO_DECIMAL, 'Número Decimal']]

    indicador = models.ForeignKeyPlus(Indicador, verbose_name='Indicador', on_delete=models.CASCADE)
    sigla = models.CharFieldPlus('Sigla')
    nome = models.CharFieldPlus('Nome')
    tipo = models.IntegerField(choices=TIPO_CHOICES)
    valor_minimo = models.IntegerField('Valor Mínimo', null=True, blank=True)
    valor_maximo = models.IntegerField('Valor Máximo', null=True, blank=True)

    class Meta:
        verbose_name = 'Variável'
        verbose_name_plural = 'Variáveis'
        ordering = ('id',)

    def __str__(self):
        return self.sigla

    def get_form_field(self, respondente=None, objeto=None):
        from djtools.forms import fields

        if self.tipo == Indicador.NUMERO_INTEIRO:
            field = fields.IntegerField(label=self.aspecto, required=self.indicador.obrigatorio, min_value=self.indicador.valor_minimo, max_value=self.indicador.valor_maximo)
        elif self.tipo == Indicador.NUMERO_DECIMAL:
            field = fields.DecimalField(label=self.aspecto, required=self.indicador.obrigatorio)

        field.name = Resposta.to_identificador(self.indicador.id, respondente.id, self.id, objeto)
        return field


class OpcaoResposta(models.ModelPlus):
    indicador = models.ForeignKeyPlus(Indicador, verbose_name='Indicador', on_delete=models.CASCADE)
    descricao = models.CharFieldPlus('Descrição')

    def __str__(self):
        return self.descricao

    class Meta:
        verbose_name = 'Opção de Resposta'
        verbose_name_plural = 'Opções de Resposta'
        ordering = ('id',)


class Avaliacao(models.ModelPlus):
    # Dados Gerais
    tipos = models.ManyToManyField(TipoAvaliacao, verbose_name='Tipo')
    ano = models.ForeignKeyPlus(Ano, verbose_name='Ano de Referência', on_delete=models.CASCADE)
    periodo = models.IntegerField('Período Letivo', choices=[[1, 1], [2, 2]], null=True, blank=True)

    nome = models.CharFieldPlus('Nome')
    descricao = models.TextField('Descrição')

    data_inicio = models.DateField(verbose_name='Data de Início')
    data_termino = models.DateField(verbose_name='Data de Término')

    # Detalhametno
    areas_vinculacao = models.ManyToManyFieldPlus(AreaVinculacao, verbose_name='Áreas de Vinculação')
    segmentos = models.ManyToManyFieldPlus(Segmento, verbose_name='Segmentos Respondentes')

    modalidades = models.ManyToManyFieldPlus(Modalidade, verbose_name='Modalidades')
    uos = models.ManyToManyFieldPlus(UnidadeOrganizacional, verbose_name='Campi')

    # Unidades relacionadas
    envolve_reitoria = models.BooleanField('Reitoria', default=True)
    envolve_campus_ead = models.BooleanField('Campus EAD', default=True)
    envolve_campus_produtivos = models.BooleanField('Campus com Unidade Produtiva', default=True)
    envolve_campus_nao_produtivos = models.BooleanField('Campus em Unidade Produtiva', default=True)

    # Token utilizado na Avaliação Externa (Pais, Empresas, Sociedade Civil e Desligados)
    token = models.CharFieldPlus('Token de Acesso', null=True)

    class Meta:
        verbose_name = 'Avaliação'
        verbose_name_plural = 'Avaliações'
        ordering = ('id',)

    def identificar_respondentes(self, excluir=False, task=None):
        servidores = Servidor.objects.ativos()
        alunos = Aluno.objects.filter(ano_letivo__ano__lte=self.ano.ano)

        if self.areas_vinculacao.exists():
            servidores = servidores.filter(setor__areas_vinculacao__in=self.areas_vinculacao.values_list('id', flat=True), eh_tecnico_administrativo=True) | servidores.filter(
                eh_docente=True
            )
            servidores = servidores.exclude(situacao__codigo=Situacao.ATIVO_EM_OUTRO_ORGAO).distinct()

        if self.uos.exists():
            servidores = servidores.filter(setor__uo__in=self.uos.values_list('id', flat=True))
            alunos = alunos.filter(curso_campus__diretoria__setor__uo__in=self.uos.values_list('id', flat=True))

        if self.modalidades.exists():
            alunos = alunos.filter(curso_campus__modalidade__in=self.modalidades.values_list('id', flat=True))

        if not self.envolve_reitoria:
            servidores = servidores.exclude(setor__uo__tipo=UnidadeOrganizacional.TIPO_REITORIA)
        if not self.envolve_campus_ead:
            servidores = servidores.exclude(setor__uo__tipo=UnidadeOrganizacional.TIPO_CAMPUS_EAD)
            alunos = alunos.exlude(curso_campus__diretoria__setor__uo__tipo=UnidadeOrganizacional.TIPO_CAMPUS_EAD)
        if not self.envolve_campus_produtivos:
            servidores = servidores.exclude(setor__uo__tipo=UnidadeOrganizacional.TIPO_CAMPUS_PRODUTIVO)
            alunos = alunos.exlude(curso_campus__diretoria__setor__uo__tipo=UnidadeOrganizacional.TIPO_CAMPUS_PRODUTIVO)
        if not self.envolve_campus_nao_produtivos:
            servidores = servidores.exclude(setor__uo__tipo=UnidadeOrganizacional.TIPO_CAMPUS_NAO_PRODUTIVO)
            alunos = alunos.exlude(curso_campus__diretoria__setor__uo__tipo=UnidadeOrganizacional.TIPO_CAMPUS_NAO_PRODUTIVO)

        if excluir:
            Respondente.objects.filter(avaliacao=self, resposta__isnull=True).distinct().delete()

        qs = self.segmentos.all()
        if task:
            task.count(qs, qs)
            qs = task.iterate(qs)

        for segmento in qs:
            # Gestores, Docentes e Técnicos Administrativos e ETEP
            if segmento.pk in [Segmento.GESTOR, Segmento.DOCENTE, Segmento.TECNICO, Segmento.ETEP]:

                if segmento.pk == Segmento.GESTOR:
                    respondentes = servidores.exclude(situacao__codigo__in=Situacao.situacoes_siape_estagiarios()).filter(funcao__isnull=False)
                elif segmento.pk == Segmento.DOCENTE:
                    respondentes = servidores.filter(eh_docente=True)
                elif segmento.pk == Segmento.TECNICO:
                    respondentes = servidores.filter(eh_tecnico_administrativo=True).exclude(
                        # Excluindo os cargos que fazem parte do segmento ETEP
                        cargo_emprego__codigo__in=['701079', '701058', '701060'],
                        setor__areas_vinculacao__in=AreaVinculacao.objects.filter(descricao__unaccent__icontains='Ensino').values_list('pk', flat=True),
                    )
                elif segmento.pk == Segmento.ETEP:
                    respondentes = servidores.filter(
                        cargo_emprego__codigo__in=['701079', '701058', '701060'],
                        setor__areas_vinculacao__in=AreaVinculacao.objects.filter(descricao__unaccent__icontains='Ensino').values_list('pk', flat=True),
                    )

                for user, uo in respondentes.values_list('user', 'setor__uo'):
                    if user and uo:
                        if not Respondente.objects.filter(user_id=user, uo_id=uo, avaliacao=self, segmento=Segmento.GESTOR).exists():
                            Respondente.objects.get_or_create(user_id=user, uo_id=uo, segmento=segmento, avaliacao=self)

            # Alunos Ativos
            elif segmento.pk == Segmento.ESTUDANTE:
                respondentes = alunos.filter(situacao__ativo=True)

                for user, uo in respondentes.values_list('pessoa_fisica__user', 'curso_campus__diretoria__setor__uo'):
                    if user and uo:
                        if not Respondente.objects.filter(user_id=user, uo_id=uo, avaliacao=self, segmento=Segmento.GESTOR).exists():
                            Respondente.objects.get_or_create(user_id=user, uo_id=uo, segmento=segmento, avaliacao=self)

            # Membros da CPA
            elif segmento.pk == Segmento.CPA_CENTRAL:
                for user, uo in servidores.filter(user__groups__name='cpa_central').values_list('user', 'setor__uo'):
                    if user and uo:
                        if not Respondente.objects.filter(user_id=user, uo_id=uo, avaliacao=self, segmento=Segmento.GESTOR).exists():
                            Respondente.objects.get_or_create(user_id=user, uo_id=uo, segmento=segmento, avaliacao=self)
            elif segmento.pk == Segmento.CPA_CAMPUS:
                for user, uo in servidores.filter(user__groups__name='cpa_campus').values_list('user', 'setor__uo'):
                    if user and uo:
                        if not Respondente.objects.filter(user_id=user, uo_id=uo, avaliacao=self, segmento=Segmento.GESTOR).exists():
                            Respondente.objects.get_or_create(user_id=user, uo_id=uo, segmento=segmento, avaliacao=self)
        task.update_progress(51)
        self.enviar_emails(True)
        task.update_progress(80)

    def __str__(self):
        return self.nome

    def enviar_emails(self, obrigatorio=False):
        respondentes = (
            Respondente.objects.filter(avaliacao=self)
            .exclude(segmento__pk__in=[Segmento.PAIS, Segmento.DESLIGADO, Segmento.SOCIEDADE_CIVIL, Segmento.EMPRESAS])
            .exclude(user__email='')
            .exclude(resposta__isnull=True)
        )
        emails = respondentes.values_list("user__email", flat=True)
        assunto_criacao = '{}'.format(self.nome)
        conteudo_criacao = '{}'.format(self.descricao)
        assunto_inicio = '{}'.format(self.nome)
        conteudo_inicio = """
            Caro(a) respondente, até o dia {} está disponível o formulário do(a) da {}.

            Para participar, acesse o SUAP com sua matrícula e senha e clique no link disponível em “Fique Atento!”.
            É possível, a qualquer momento, clicar no botão "Salvar", disponível no final do formulário, e retomar o preenchimento posteriormente, até o prazo final.

            A sua participação é muito importante para a instituição!
        """.format(
            self.data_termino, self.nome
        )
        assunto_lembrete = '{}'.format(self.nome)
        conteudo_lembrete = """
            Caro(a) respondente, você ainda não concluiu o preenchimento da {}, que está disponível até {}.

            Para participar, acesse o SUAP com sua matrícula e senha e clique no link disponível em “Fique Atento!”.
            É possível, a qualquer momento, clicar no botão "Salvar", disponível no final do formulário, e retomar o preenchimento posteriormente, até o prazo final.

            Vamos lá! Participe! O prazo está acabando!
        """.format(
            self.nome, self.data_termino
        )
        assunto_ultimo = '{}'.format(self.nome)
        conteudo_ultimo = """
            Caro(a) respondente, hoje é o último dia para você concluir o preenchimento da {}.

            Para participar, acesse o SUAP com sua matrícula e senha e clique no link disponível em “Fique Atento!”.
            É possível, a qualquer momento, clicar no botão "Salvar", disponível no final do formulário, e retomar o preenchimento posteriormente, até o prazo final.

            Vamos lá! Dê a sua contribuição nesse processo!
        """.format(
            self.nome
        )
        tempo_total = (self.data_termino - self.data_inicio).days
        hoje = datetime.date.today()
        enviar_email = False
        if obrigatorio:
            enviar_email = True
            assunto = assunto_criacao
            conteudo = conteudo_criacao
        elif hoje == self.data_inicio:
            enviar_email = True
            assunto = assunto_inicio
            conteudo = conteudo_inicio
        elif hoje.replace(day=hoje.day + int(tempo_total * 0.75)) == self.data_termino:
            enviar_email = True
            assunto = assunto_lembrete
            conteudo = conteudo_lembrete
        elif hoje.replace(day=hoje.day + 1) == self.data_termino:
            enviar_email = True
            assunto = assunto_ultimo
            conteudo = conteudo_ultimo
        if enviar_email:
            send_mail(assunto, conteudo, settings.DEFAULT_FROM_EMAIL, emails, fail_silently=True)

    def get_absolute_url(self):
        return '/avaliacao_integrada/avaliacao/{}/'.format(self.pk)


class Respondente(models.ModelPlus):
    avaliacao = models.ForeignKeyPlus(Avaliacao, verbose_name='Avaliação', on_delete=models.CASCADE)
    user = models.ForeignKeyPlus(User, verbose_name='Usuário', null=True, on_delete=models.CASCADE)
    uo = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus', null=True, on_delete=models.CASCADE)
    segmento = models.ForeignKeyPlus(Segmento, verbose_name='Segmento', on_delete=models.CASCADE)
    finalizado = models.BooleanField('Questionário Finalizado', default=False)

    class Meta:
        verbose_name = 'Respondente'
        verbose_name_plural = 'Respondentes'
        ordering = ('id',)

    # CPA Central, CPA do Campus, Gestores, Docentes e Empresas
    def get_modalidades_relacionadas(self):
        if self.segmento_id in [Segmento.CPA_CENTRAL, Segmento.EMPRESAS]:
            return Modalidade.objects.all()
        elif self.segmento_id in [Segmento.CPA_CAMPUS, Segmento.GESTOR, Segmento.ETEP, Segmento.DOCENTE]:
            ids = CursoCampus.objects.filter(diretoria__setor__uo=self.uo, ativo=True).values_list('modalidade__pk', flat=True)
            return Modalidade.objects.filter(id__in=ids).filter(id__in=self.avaliacao.modalidades.values_list('id', flat=True))
        return Modalidade.objects.none()

    # Professores e Alunos (ativos e egressos)
    def get_cursos_relacionados(self):
        if self.segmento_id in [Segmento.CPA_CAMPUS, Segmento.DOCENTE]:
            return CursoCampus.objects.filter(diretoria__setor__uo=self.uo, ativo=True)
        elif self.segmento_id in [Segmento.ESTUDANTE, Segmento.ETEP, Segmento.EGRESSO]:
            return CursoCampus.objects.filter(aluno__pessoa_fisica__username=self.user.username)
        return CursoCampus.objects.none()

    # Professores e Alunos (ativos)
    def get_turmas_relacionadas(self):
        qs = Diario.objects.none()

        if self.segmento_id in [Segmento.DOCENTE]:
            qs = Diario.objects.filter(professordiario__professor__vinculo__user__username=self.user.username, ano_letivo=self.avaliacao.ano)
        elif self.segmento_id in [Segmento.ESTUDANTE]:
            qs = Diario.objects.filter(matriculadiario__matricula_periodo__aluno__pessoa_fisica__username=self.user.username, ano_letivo=self.avaliacao.ano)

        if self.avaliacao.periodo:
            qs.filter(periodo_letivo=self.avaliacao.periodo)

        return qs

    # Alunos (ativos)
    def get_professores_relacionados(self):
        qs = Turma.objects.none()

        if self.segmento_id in [Segmento.ESTUDANTE]:
            qs = ProfessorDiario.objects.filter(
                diario__ano_letivo=self.avaliacao.ano, diario__matriculadiario__matricula_periodo__aluno__pessoa_fisica__username=self.user.username
            )

        if self.avaliacao.periodo:
            qs.filter(diario__periodo_letivo=self.avaliacao.periodo)

        return qs

    # Métodos para recuperar o valor dos campos autocalculados.
    def get_unidade_vinculacao(self):
        try:
            return self.user.pessoafisica.aluno_edu_set.all()[0].curso_campus.diretoria.setor.uo.nome
        except Exception:
            return self.uo.nome

    def get_modalidade_vinculacao(self):
        return self.user.pessoafisica.aluno_edu_set.all()[0].curso_campus.modalidade.descricao

    def get_curso_vinculacao(self):
        try:
            return self.user.pessoafisica.aluno_edu_set.all()[0].curso_campus.descricao_historico
        except Exception:
            return ''

    def get_ano_ingresso_curso(self):
        return self.user.pessoafisica.aluno_edu_set.all()[0].ano_letivo.ano

    def get_forma_ingresso_curso(self):
        return self.user.pessoafisica.aluno_edu_set.all()[0].forma_ingresso.descricao

    def get_serie_periodo_curso(self):
        return self.user.pessoafisica.aluno_edu_set.all()[0].periodo_atual

    def get_cargo_servidor(self):
        return self.user.pessoafisica.funcionario.servidor.cargo_emprego.nome

    def get_unidade_atuacao_servidor(self):
        return self.uo.nome

    def get_area_atuacao_servidor(self):
        return self.user.pessoafisica.funcionario.servidor.setor.areas_vinculacao.all()[0].descricao

    def get_regime_trabalho_servidor(self):
        return self.user.pessoafisica.funcionario.servidor.jornada_trabalho.nome

    def get_forma_contratacao_servidor(self):
        return self.user.pessoafisica.funcionario.servidor.situacao.nome

    def get_data_nascimento(self):
        return self.user.pessoafisica.nascimento_data.strftime('%d/%m/%Y')

    def get_tipo_acao_afirmativa(self):
        return self.user.pessoafisica.aluno_edu_set.all()[0].get_cota_mec_display()

    def get_funcao_servidor(self):
        return self.user.pessoafisica.funcionario.servidor.funcao_display

    def get_ira_curso(self):
        return self.user.pessoafisica.aluno_edu_set.all()[0].get_ira()

    def get_indicadores(self, excluir_automatico=False, ignorar_opcionais=False):
        # filtrando indicadores ativos
        indicadores = Indicador.objects.filter(em_uso=True, anos_referencia__in=[self.avaliacao.ano])
        if excluir_automatico:
            indicadores = indicadores.filter(automatico=False)
        if ignorar_opcionais:
            indicadores = indicadores.filter(obrigatorio=True)

        # filtrando indicadores por unidades relacionadas

        if self.uo:
            if self.uo.tipo_id == UnidadeOrganizacional.TIPO_REITORIA:
                indicadores = indicadores.filter(envolve_reitoria=True)
            elif self.uo.tipo_id == UnidadeOrganizacional.TIPO_CAMPUS_EAD:
                indicadores = indicadores.filter(envolve_campus_ead=True)
            elif self.uo.tipo_id == UnidadeOrganizacional.TIPO_CAMPUS_NAO_PRODUTIVO:
                indicadores = indicadores.filter(envolve_campus_nao_produtivos=True)
            elif self.uo.tipo_id == UnidadeOrganizacional.TIPO_CAMPUS_PRODUTIVO:
                indicadores = indicadores.filter(envolve_campus_produtivos=True)

        # filtrando indicadores por segmento do respondente
        indicadores = indicadores.filter(segmentos=self.segmento)

        # Filtrando pelas UOs dos indicadores
        indicadores = (indicadores.filter(uos=self.uo) | indicadores.filter(uos__isnull=True)).distinct()

        # filtrando indicadores por area do respondente
        if self.segmento_id in [Segmento.GESTOR, Segmento.TECNICO, Segmento.ETEP]:
            servidor = Servidor.objects.get(matricula=self.user.username)
            indicadores = indicadores.filter(areas_vinculacao__isnull=True) | indicadores.filter(
                areas_vinculacao__in=servidor.setor and servidor.setor.areas_vinculacao.values_list('pk', flat=True) or []
            )

        # filtrando indicadores pela modalidade dos cursos
        if self.avaliacao.modalidades.exists():
            indicadores = indicadores.filter(modalidades__in=self.avaliacao.modalidades.values_list('id', flat=True)) | indicadores.filter(modalidades__isnull=True)
            # filtrando indicadores pelo período de referência do aluno
            if self.segmento_id in [Segmento.ESTUDANTE]:
                aluno = Aluno.objects.get(matricula=self.user.username)
                if aluno.periodo_atual:
                    indicadores = indicadores.exclude(periodo_curso__gt=aluno.periodo_atual)
        indicadores = indicadores.distinct()

        return indicadores

    def get_percentual_respondido(self, excluir_automatico=False, ignorar_opcionais=False):
        total = self.get_indicadores(excluir_automatico=excluir_automatico, ignorar_opcionais=ignorar_opcionais).count()
        if not total:
            return 0
        qs_respondido = Resposta.objects.filter(respondente=self).exclude(valor='').filter(valor__isnull=False)
        if excluir_automatico:
            qs_respondido = qs_respondido.filter(indicador__automatico=False)
        if ignorar_opcionais:
            qs_respondido = qs_respondido.filter(indicador__obrigatorio=True)
        resultado = int(qs_respondido.count() * 100 / total)
        return resultado if resultado < 100 else 100

    def get_percentual_realmente_respondido(self):
        return self.get_percentual_respondido(excluir_automatico=True, ignorar_opcionais=True)


class Resposta(models.ModelPlus):
    indicador = models.ForeignKeyPlus(Indicador, verbose_name='Indicador', on_delete=models.CASCADE)
    respondente = models.ForeignKeyPlus(Respondente, verbose_name='Respondente', on_delete=models.CASCADE)
    variavel = models.ForeignKeyPlus(Variavel, verbose_name='Variável', null=True, blank=True, on_delete=models.CASCADE)
    content_type = models.ForeignKeyPlus(ContentType, verbose_name='Content Type', null=True, blank=True, on_delete=models.CASCADE)
    object_id = models.PositiveIntegerField(verbose_name='', null=True, blank=True)
    objeto = GenericForeignKey('content_type', 'object_id')
    identificador = models.CharFieldPlus('Identificador')
    valor = models.TextField()

    class Meta:
        verbose_name = 'Resposta'
        verbose_name_plural = 'Resposta'
        ordering = ('id',)

    @staticmethod
    def to_identificador(indicador_id, respondente_id, variavel_id, object):
        content_type = object and ContentType.objects.get(model=object.__class__.__name__.lower()) or None
        return '{}::{}::{}::{}::{}'.format(indicador_id, respondente_id, variavel_id and variavel_id or 0, content_type and content_type.pk or 0, object and object.id or 0)

    @staticmethod
    @atomic
    def processar(respondente, dados, finalizar=False):
        Resposta.objects.filter(respondente=respondente).delete()
        for identificador in dados:
            if '::' in identificador:
                indicador_id, respondente_id, variavel_id, content_type_id, object_id = identificador.split('::')
                valor = dados[identificador]
                if valor is not None:
                    if isinstance(valor, (list, tuple)):
                        if len(valor) == 1:
                            valor.append('')
                        valor = '::'.join(valor)

                    Resposta.objects.create(
                        indicador_id=int(indicador_id),
                        respondente_id=int(respondente_id),
                        variavel_id=int(variavel_id) or None,
                        content_type_id=int(content_type_id) or None,
                        object_id=int(object_id) or None,
                        identificador=identificador,
                        valor=str(valor),
                    )
        if finalizar:
            respondente.finalizado = True
            respondente.save()
