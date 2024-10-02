from django.core.exceptions import ValidationError
from django.db.models import Sum

from djtools.db import models
from ppe.managers import CursoObjectsManager, FormacaoPPEManager
from ppe.models import LogPPEModel


class EstruturaCurso(LogPPEModel):

    CRITERIO_AVALIACAO_NOTA = 1
    CRITERIO_AVALIACAO_FREQUENCIA = 2
    CRITERIO_AVALIACAO_CHOICES = [[CRITERIO_AVALIACAO_NOTA, 'Nota'], [CRITERIO_AVALIACAO_FREQUENCIA, 'Frequência']]

    descricao = models.CharFieldPlus('Descrição', width=500)
    ativo = models.BooleanField('Está Ativa', default=True)

    # Critérios de Avaliação por Curso
    criterio_avaliacao = models.PositiveIntegerField('Critério de Avaliação', choices=CRITERIO_AVALIACAO_CHOICES)
    media_aprovacao_sem_prova_final = models.NotaField('Média para passar sem prova final', null=True, blank=True)
    media_aprovacao_avaliacao_final = models.NotaField('Média para aprovação após avaliação final', null=True, blank=True)

    # Critérios de Apuração de Frequência
    percentual_frequencia = models.PositiveIntegerField(
        'Percentual Mínimo de Frequência', help_text='Percentual (%) mínimo de frequência para que os alunos não reprovem no período ou na disciplina.', default=90
    )

    class Meta:
        verbose_name = 'Estrutura de Curso'
        verbose_name_plural = 'Estruturas de Curso'

    def get_absolute_url(self):
        return '/ppe/estruturacurso/{:d}/'.format(self.pk)

    def clean(self):
        if self.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_NOTA:
            if self.media_aprovacao_sem_prova_final is None:
                raise ValidationError('A média para passar sem prova final deve ser informada')
        if self.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_NOTA:
            if self.media_aprovacao_avaliacao_final is None:
                raise ValidationError('A média para aprovação após avaliação final deve ser informada')

    # def get_formacoes_ppe_ativas(self):
    #     return self.cursoformacaoppe_set.filter(data_fim__isnull=True)
    #
    # def get_formacoes_ppe_inativas(self):
    #     return self.cursoformacaoppe_set.filter(data_fim__isnull=False)


    #TODO Implementar
    # def get_matrizes_ativas(self):
    #     return self.matriz_set.filter(data_fim__isnull=True)

    #TODO Implementar
    # def get_matrizes_inativas(self):
    #     return self.matriz_set.filter(data_fim__isnull=False)


class Curso(LogPPEModel):

    SEARCH_FIELDS = ['codigo', 'codigo_academico', 'descricao', 'descricao_historico']

    codigo_academico = models.IntegerField(null=True)

    objects = CursoObjectsManager()

    # Identificação
    id = models.AutoField(verbose_name='Código', primary_key=True)
    descricao = models.CharFieldPlus(verbose_name='Descrição', width=500)
    descricao_historico = models.CharFieldPlus(verbose_name='Descrição no Diploma e Histórico', width=500)

    # Dados da Criação
    data_inicio = models.DateFieldPlus('Data início', null=True)
    data_fim = models.DateFieldPlus('Data fim', null=True, blank=True)
    ativo = models.BooleanField('Ativo', default=True)

    # Outros Dados
    codigo = models.CharFieldPlus(verbose_name='Código', help_text='Código para composição de turmas e matrículas',
                                  unique=True)

    ch_total = models.PositiveIntegerField('Carga Horária Total h/r', blank=True, null=True, default=None)
    ch_aula = models.PositiveIntegerField('Carga Horária Total h/a', blank=True, null=True, default=None)

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ('-ativo',)

    def __str__(self):
        codigo = self.codigo.replace('-', '')
        return '{} - {} [{} h/{} Aulas]'.format(codigo, self.descricao,self.ch_total, self.ch_aula)

    def get_absolute_url(self):
        return '/ppe/curso/{:d}'.format(self.pk)

    #TODO Implementar
    # def possui_trabalhador_educando_cursando(self):

    def clean(self):
        if Curso.objects.filter(codigo__iexact=self.codigo).exclude(id=self.id).exists():
            raise ValidationError('Já existe um curso com este mesmo código. O código do curso deve ser único.')
        if self.ativo and self.data_fim:
            raise ValidationError('Um curso ativo não pode ter data de fim')
        super().clean()

    def save(self, *args, **kwargs):
        curso = None
        if self.pk:
            curso = Curso.objects.get(pk=self.pk)
        super().save(*args, **kwargs)


class CursoFormacaoPPE(LogPPEModel):
    SEARCH_FIELDS = ['formacao_ppe__codigo', 'formacao_ppe__descricao']

    TIPO_PERMANENTE = 1
    TIPO_TRANSVERSAIS = 2
    TIPO_ESPECIFICO = 3
    TIPO_CHOICES = [
        [TIPO_PERMANENTE, 'Formação Permanente'], [TIPO_TRANSVERSAIS, 'Transversais'], [TIPO_ESPECIFICO, 'Específicos'],
    ]
    # Dados gerais
    formacao_ppe = models.ForeignKeyPlus('ppe.FormacaoPPE')
    curso = models.ForeignKeyPlus('ppe.Curso')
    tipo = models.PositiveIntegerField(choices=TIPO_CHOICES)
    optativo = models.BooleanField(default=False)
    qtd_avaliacoes = models.PositiveIntegerField('Qtd. Avaliações', choices=[[0, 'Zero'], [1, 'Uma'], [2, 'Duas'], [4, 'Quatro']])
    # Estrutura
    estrutura = models.ForeignKeyPlus('ppe.EstruturaCurso', null=True, on_delete=models.CASCADE)

    # Carga horária
    ch_presencial = models.PositiveIntegerField('Teórica', help_text='Hora-Relógio')
    ch_pratica = models.PositiveIntegerField('Prática', help_text='Hora-Relógio')
    # Pré requisitos
    pre_requisitos = models.ManyToManyFieldPlus('ppe.CursoFormacaoPPE', related_name='prerequisitos_ppe_set', blank=True)
    # Co-requisitos
    co_requisitos = models.ManyToManyFieldPlus('ppe.CursoFormacaoPPE', related_name='corequisitos_ppe_set', blank=True)
    ementa = models.TextField('Ementa', blank=True, null=True, default='')

    class Meta:
        verbose_name = 'Curso PPE'
        verbose_name_plural = 'Cursos PPE'

    def get_absolute_url(self):
        return '/ppe/curso/{:d}/'.format(self.pk)

    def __str__(self):
        return '{} [Formacao PPE {}]'.format(str(self.curso), self.formacao_ppe.pk)

    def get_carga_horaria_total(self):
        return self.ch_pratica + self.ch_presencial

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        self.formacao_ppe.verificar_inconsistencias()
        self.formacao_ppe.save()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

        self.formacao_ppe.verificar_inconsistencias()
        self.formacao_ppe.save()

    def get_grupo_componente_historico(self, grupos_componentes):
        componentes = None
        if self.tipo == CursoFormacaoPPE.TIPO_PERMANENTE:
            componentes = grupos_componentes['Formação Permanente']
        elif self.tipo == CursoFormacaoPPE.TIPO_TRANSVERSAIS:
            componentes = grupos_componentes['Transversais']
        elif self.tipo == CursoFormacaoPPE.TIPO_ESPECIFICO:
            componentes = grupos_componentes['Específicos']

        return componentes

    def get_pre_requisitos(self, requisitos=None, recursivo=False):
        if requisitos is None:
            requisitos = []
        if len(requisitos) < 50:  # evitar loop infinito já que se trata de uma função recursiva
            for pre_requisito in self.pre_requisitos.all():
                if pre_requisito.componente.pk not in requisitos:
                    requisitos.append(pre_requisito.componente.pk)
                if recursivo:
                    pre_requisito.get_pre_requisitos(requisitos)
        return requisitos

    def get_corequisitos(self):
        requisitos = []
        for corequisito in self.co_requisitos.all():
            requisitos.append(corequisito.componente.pk)
        return requisitos

    def is_semestral(self):
        return self.qtd_avaliacoes == 2

    def get_periodo_letivo(self):
        return self.periodo_letivo and self.periodo_letivo or 0


class FormacaoPPE(LogPPEModel):
    SEARCH_FIELDS = ['id', 'descricao']

    objects = FormacaoPPEManager()

    # Dados gerais
    id = models.AutoField(verbose_name='Código', primary_key=True)
    descricao = models.CharFieldPlus(verbose_name='Descrição', width=500)
    ativo = models.BooleanField('Ativa', default=True)
    data_inicio = models.DateFieldPlus('Data de início')
    data_fim = models.DateFieldPlus('Data de fim', null=True, blank=True)
    ppp = models.FileFieldPlus(upload_to='ppe/ppp/', null=True, blank=True, verbose_name='PPP')

    # Carga horária
    ch_componentes_obrigatorios = models.PositiveIntegerField('Cursos obrigatórios', help_text='Hora-Relógio')
    ch_especifica = models.PositiveIntegerField('Cursos específicos', help_text='Hora-Relógio', default=0)

    # Cursos
    cursos = models.ManyToManyField('ppe.Curso', through='ppe.CursoFormacaoPPE')

    # A matriz possui inconsistência?
    inconsistente = models.BooleanField(default=False)
    # Exige trabalho de conclusão de curso

    observacao = models.TextField('Observação', null=True, blank=True)


    class Meta:
        verbose_name = 'Formação PPE'
        verbose_name_plural = 'Formações PPE'
        ordering = ('descricao',)

    # TODO Implementar
    def pode_ser_editada(self, user=None):
        return True
    #     if user and user.is_superuser:
    #         return True
    #     return not self.aluno_set.filter(situacao__id=SituacaoMatricula.CONCLUIDO).exists()

    # TODO Implementar
    # def get_grade_curricular(self):
    #     result = dict()
    #     for cc in self.componentecurricular_set.all():
    #         p = str(cc.periodo_letivo or 0)
    #         prerequisitos = []
    #         for prerequisito in cc.pre_requisitos.all():
    #             prerequisitos.append(dict(id=str(prerequisito.pk)))
    #         corequisitos = []
    #         for corequisito in cc.co_requisitos.all():
    #             corequisitos.append(dict(id=str(corequisito.pk)))
    #         componente = dict(
    #             componente=cc.componente.descricao_historico.replace("'", ""),
    #             id=str(cc.pk),
    #             periodo=str(p),
    #             tipo=str(cc.tipo),
    #             prerequisitos=prerequisitos,
    #             corequisitos=corequisitos,
    #             ch_hora_relogio=cc.componente.ch_hora_relogio,
    #             sigla=cc.componente.sigla,
    #             optativo=cc.optativo,
    #         )
    #         if p not in result:
    #             result[p] = []
    #         result[p].append(componente)
    #     return result
    # TODO Implementar
    # def toJson(self):
    #     import json
    #
    #     m = []
    #     for cc in self.componentecurricular_set.all():
    #         prerequisitos = []
    #         corequisitos = []
    #         for prerequisito in cc.pre_requisitos.all():
    #             prerequisitos.append(dict(id=str(prerequisito.pk)))
    #         for corequisito in cc.co_requisitos.all():
    #             corequisitos.append(dict(id=str(corequisito.pk)))
    #
    #         m.append(
    #             dict(
    #                 componente=cc.componente.descricao_historico.replace("'", ""),
    #                 id=str(cc.pk),
    #                 periodo=str(cc.periodo_letivo or 0),
    #                 tipo=str(cc.tipo),
    #                 prerequisitos=prerequisitos,
    #                 corequisitos=corequisitos,
    #                 ch_hora_relogio=cc.componente.ch_hora_relogio,
    #                 sigla=cc.componente.sigla,
    #                 optativo=cc.optativo,
    #             )
    #         )
    #     return json.dumps(dict(matriz=m))
    # TODO Implementar
    # def get_numero_colunas(self):
    #     qs = self.componentecurricular_set.filter(optativo=False).values_list('periodo_letivo', flat=True).order_by('-periodo_letivo')
    #     return qs and qs[0] or 0
    # TODO Implementar
    # def get_numero_linhas(self):
    #     numero_linhas = 0
    #     for dicionarios in self.componentecurricular_set.values('periodo_letivo').annotate(Count('id')).order_by():
    #         count = dicionarios['id__count']
    #         if count >= numero_linhas:
    #             numero_linhas = count
    #     return numero_linhas

    def replicar(self, descricao):
        cursos = self.cursoformacaoppe_set.all()
        for _ in cursos:
            pass
        self.id = None
        self.descricao = descricao
        self.clean()
        self.save()

        for cursoformacaoppe in cursos:
            pre_requisitos = cursoformacaoppe.pre_requisitos.all()
            co_requisitos = cursoformacaoppe.co_requisitos.all()
            cursoformacaoppe.id = None
            cursoformacaoppe.formacao_ppe = self
            cursoformacaoppe.save()
            for pre_requisito in pre_requisitos:
                cursoformacaoppe.pre_requisitos.add(pre_requisito)
            for co_requisito in co_requisitos:
                cursoformacaoppe.co_requisitos.add(co_requisito)

        return self

    def clean(self):
        if self.ativo and self.data_fim:
            raise ValidationError('Uma Formação PPE ativa não pode ter data de fim')
        if not self.ativo and not self.data_fim:
            raise ValidationError('Uma Formação PPE inativa deve ter data de fim')

    def __str__(self):
        return '{} - {}'.format(self.pk, self.descricao)

    def get_absolute_url(self):
        return '/ppe/formacaoppe/{:d}/'.format(self.pk)

    def get_ch_total(self):
        total = 0
        for curso_formacao in self.cursoformacaoppe_set.all():
            total += curso_formacao.curso.ch_total
        return total

    def get_carga_horaria_total_prevista(self):
        return (
            self.ch_componentes_obrigatorios
        )

    def possui_componentes_obrigatorios(self):
        return self.ch_componentes_obrigatorios > 0

    # COMPONENTES

    # def get_ids_componentes(self, periodos=[], apenas_obrigatorio=False, apenas_optativas=False):
    #     qs = self.get_componentes_curriculares(periodos, apenas_obrigatorio, apenas_optativas)
    #     return qs.values_list('componente__id', flat=True)
    #
    # def get_componentes(self, apenas_obrigatorio=False):
    #     return Componente.objects.filter(id__in=self.get_ids_componentes([], apenas_obrigatorio))
    #
    # def get_ids_componentes_regulares_obrigatorios(self):
    #     return self.get_componentes_curriculares_regulares_obrigatorios().values_list('componente__id', flat=True)
    #
    # def get_componentes_regulares_obrigatorios(self):
    #     return Componente.objects.filter(id__in=self.get_ids_componentes_regulares_obrigatorios())
    #
    # def get_ids_componentes_regulares_optativos(self):
    #     return self.get_componentes_curriculares_optativos().values_list('componente__id', flat=True)
    #
    # def get_componentes_regulares_optativos(self):
    #     return Componente.objects.filter(id__in=self.get_ids_componentes_regulares_optativos())
    #
    # def get_ids_componentes_seminario(self, apenas_obrigatorio=False):
    #     qs = self.get_componentes_curriculares_seminario()
    #     if apenas_obrigatorio:
    #         qs = qs.exclude(optativo=True)
    #     return qs.values_list('componente__id', flat=True)
    #
    # def get_componentes_seminario(self, apenas_obrigatorio=False):
    #     return Componente.objects.filter(id__in=self.get_ids_componentes_seminario(apenas_obrigatorio))
    #
    # def get_ids_componentes_pratica_como_componente(self, apenas_obrigatorio=False):
    #     qs = self.get_componentes_curriculares_pratica_como_componente()
    #     if apenas_obrigatorio:
    #         qs = qs.exclude(optativo=True)
    #     return qs.values_list('componente__id', flat=True)
    #
    # def get_componentes_pratica_como_componente(self, apenas_obrigatorio=False):
    #     return Componente.objects.filter(id__in=self.get_ids_componentes_pratica_como_componente(apenas_obrigatorio))
    #
    # def get_ids_componentes_visita_tecnica(self, apenas_obrigatorio=False):
    #     qs = self.get_componentes_curriculares_visita_tecnica()
    #     if apenas_obrigatorio:
    #         qs = qs.exclude(optativo=True)
    #     return qs.values_list('componente__id', flat=True)
    #
    # def get_componentes_visita_tecnica(self, apenas_obrigatorio=False):
    #     return Componente.objects.filter(id__in=self.get_ids_componentes_visita_tecnica(apenas_obrigatorio))
    #
    # def get_ids_componentes_pratica_profissional(self, apenas_obrigatorio=False):
    #     qs = self.get_componentes_curriculares_pratica_profissional()
    #     if apenas_obrigatorio:
    #         qs = qs.exclude(optativo=True)
    #     return qs.values_list('componente__id', flat=True)
    #
    # def get_componentes_pratica_profissional(self, apenas_obrigatorio=False):
    #     return Componente.objects.filter(id__in=self.get_ids_componentes_pratica_profissional(apenas_obrigatorio))
    #
    # def get_ids_componentes_tcc(self, apenas_obrigatorio=False):
    #     qs = self.get_componentes_curriculares_tcc()
    #     if apenas_obrigatorio:
    #         qs = qs.exclude(optativo=True)
    #     return qs.values_list('componente__id', flat=True)
    #
    # def get_componentes_tcc(self, apenas_obrigatorio=False):
    #     return Componente.objects.filter(id__in=self.get_ids_componentes_tcc(apenas_obrigatorio))
    #
    # # COMPONENTES CURRICULARES
    #
    # def get_componentes_curriculares(self, periodos=[], apenas_obrigatorio=False, apenas_optativas=False):
    #     qs = self.cursoformacaoppe_set.all()
    #     if periodos:
    #         if type(periodos) == list:
    #             qs = qs.filter(periodo_letivo__in=periodos)
    #         else:
    #             qs = qs.filter(periodo_letivo=periodos)
    #     if apenas_obrigatorio:
    #         qs = qs.exclude(optativo=True)
    #
    #     if apenas_optativas:
    #         qs = qs.exclude(optativo=False)
    #
    #     return qs
    #
    # def get_componentes_curriculares_regulares_obrigatorios(self):
    #     return self.get_componentes_curriculares(apenas_obrigatorio=True).filter(tipo=ComponenteCurricular.TIPO_REGULAR)
    #
    # def get_componentes_curriculares_optativos(self):
    #     return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TIPO_REGULAR, optativo=True)
    #
    # def get_componentes_curriculares_seminario(self):
    #     return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TIPO_SEMINARIO)
    #
    # def get_componentes_curriculares_pratica_profissional(self):
    #     return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL)
    #
    # def get_componentes_curriculares_pratica_como_componente(self):
    #     return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TIPO_PRATICA_COMO_COMPONENTE)
    #
    # def get_componentes_curriculares_visita_tecnica(self):
    #     return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TIPO_VISITA_TECNICA)
    #
    # def get_componentes_curriculares_tcc(self):
    #     return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO)
    #
    # # CARGA HORRÁRIA DOS COMPONENTES CURRICULARES
    #
    # def get_ch_componentes_obrigatorios(self, nucleo=None, relogio=True):
    #     componentes_regulares = self.get_componentes_curriculares_regulares_obrigatorios()
    #     if nucleo:
    #         componentes_regulares = componentes_regulares.filter(nucleo=nucleo).distinct()
    #     if relogio:
    #         return componentes_regulares.aggregate(qtd=Sum('componente__ch_hora_relogio')).get('qtd') or 0
    #     else:
    #         return componentes_regulares.aggregate(qtd=Sum('componente__ch_hora_aula')).get('qtd') or 0
    #
    # def get_ch_componentes_optativos(self, nucleo=None, relogio=True):
    #     componentes_optativos = self.get_componentes_curriculares_optativos()
    #     if nucleo:
    #         componentes_optativos = componentes_optativos.filter(nucleo=nucleo).distinct()
    #     if relogio:
    #         return componentes_optativos.aggregate(qtd=Sum('componente__ch_hora_relogio')).get('qtd') or 0
    #     else:
    #         return componentes_optativos.aggregate(qtd=Sum('componente__ch_hora_aula')).get('qtd') or 0
    #
    # def get_ch_componentes_seminario(self, nucleo=None, relogio=True):
    #     componentes_seminarios = self.get_componentes_curriculares_seminario()
    #     if nucleo:
    #         componentes_seminarios = componentes_seminarios.filter(nucleo=nucleo).distinct()
    #     if relogio:
    #         return componentes_seminarios.aggregate(qtd=Sum('componente__ch_hora_relogio')).get('qtd') or 0
    #     else:
    #         return componentes_seminarios.aggregate(qtd=Sum('componente__ch_hora_aula')).get('qtd') or 0
    #
    # def get_ch_componentes_pratica_profissional(self, nucleo=None, relogio=True):
    #     componentes_pratica_profissional = self.get_componentes_curriculares_pratica_profissional()
    #     if nucleo:
    #         componentes_pratica_profissional = componentes_pratica_profissional.filter(nucleo=nucleo).distinct()
    #     if relogio:
    #         return componentes_pratica_profissional.aggregate(qtd=Sum('componente__ch_hora_relogio')).get('qtd') or 0
    #     else:
    #         return componentes_pratica_profissional.aggregate(qtd=Sum('componente__ch_hora_aula')).get('qtd') or 0
    #
    # def get_ch_componentes_tcc(self):
    #     return self.get_componentes_tcc().aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0
    #
    # def get_ch_componentes_obrigatorios_faltando(self):
    #     return self.ch_componentes_obrigatorios - self.get_ch_componentes_obrigatorios()
    #
    # def get_ch_componentes_optativos_faltando(self):
    #     return self.ch_componentes_optativos - self.get_ch_componentes_optativos()
    #
    # def get_ch_componentes_seminario_faltando(self):
    #     return self.ch_seminarios - self.get_ch_componentes_seminario()
    #
    # def get_ch_componentes_pratica_profissional_faltando(self):
    #     return self.ch_pratica_profissional - self.get_ch_componentes_pratica_profissional()
    #
    # def get_ch_componentes_tcc_faltando(self):
    #     return self.ch_componentes_tcc - self.get_ch_componentes_tcc()
    #
    # def get_qtd_credito_componentes_obrigatorios(self, nucleo=None, periodo_letivo=None):
    #     componentes_obrigatorios = self.get_componentes_curriculares_regulares_obrigatorios()
    #     if nucleo:
    #         componentes_obrigatorios = componentes_obrigatorios.filter(nucleo=nucleo)
    #     if periodo_letivo:
    #         componentes_obrigatorios = componentes_obrigatorios.filter(periodo_letivo=periodo_letivo)
    #     return componentes_obrigatorios.aggregate(qtd=Sum('componente__ch_qtd_creditos')).get('qtd') or 0
    #
    #
    #
    # def is_ch_componentes_obrigatorios_faltando(self):
    #     return self.get_ch_componentes_obrigatorios_faltando() > 0
    #
    # def is_ch_faltando(self):
    #     return (
    #         self.is_ch_componentes_obrigatorios_faltando()
    #     )
    # TODO Implementar
    def verificar_inconsistencias(self):
        retorno = False

        # if self.is_ch_faltando() or not self.is_ch_componentes_obrigatorios_consistente():
        #     self.inconsistente = True
        # else:
        #     self.inconsistente = False

        return retorno

    def save(self, *args, **kwargs):
        self.verificar_inconsistencias()
        super().save(*args, **kwargs)

#FES-37

class RepresentacaoConceitual(LogPPEModel):
    estrutura_curso = models.ForeignKeyPlus('ppe.EstruturaCurso')
    descricao = models.CharFieldPlus('Descrição')
    valor_minimo = models.NotaField('Valor Mínimo')
    valor_maximo = models.NotaField('Valor Máximo')

    class Meta:
        verbose_name = 'Representação Conceitual'
        verbose_name_plural = 'Representações Conceituais'