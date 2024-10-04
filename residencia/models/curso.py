import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum, Count

from comum.models import UsuarioGrupo
from comum.utils import somar_data
from djtools.db import models
from djtools.html.calendarios import Calendario
from residencia.managers import CursoResidenciaManager, MatrizManager
from residencia.models import LogResidenciaModel
from suap.settings_base import PERIODO_LETIVO_CHOICES


class Componente(LogResidenciaModel):
    SEARCH_FIELDS = ['descricao', 'descricao_historico', 'sigla', 'sigla_qacademico', 'abreviatura']

    descricao = models.CharFieldPlus(verbose_name='Descrição', width=500)
    descricao_historico = models.CharFieldPlus(verbose_name='Descrição no Diploma e Histórico', width=500)
    sigla = models.CharFieldPlus(max_length=255, unique=True)
    ativo = models.BooleanField('Está ativo', default=True)

    ch_hora_relogio = models.PositiveIntegerField('Hora/relógio')
    ch_hora_aula = models.PositiveIntegerField('Hora/aula', blank=True,null=True)

    observacao = models.TextField('Observação', blank=True, default='')
    abreviatura = models.CharFieldPlus('Abreviatura', max_length=10, null=True)

    class Meta:
        verbose_name = 'Atividade'
        verbose_name_plural = 'Atividades'
        ordering = ('descricao',)

    def __str__(self):
        return '{} - {} [{} h] {}'.format(
            self.abreviatura, self.descricao, self.ch_hora_relogio, (self.observacao and '- {}'.format(self.observacao or ''))
        )

    # def get_fator_conversao_hora_aula(self):
    #     return self.ch_hora_relogio and (Decimal(self.ch_hora_aula) / Decimal(self.ch_hora_relogio)) or Decimal(0)

    # def get_absolute_url(self):
    #     return '/residencia/componente/{:d}/'.format(self.pk)

    def save(self, *args, **kwargs):
        if (not self.id and not self.sigla):
            componentes = Componente.objects.all().exclude(id=self.id).order_by('-sigla')

            if componentes:
                prefix, sufixo = componentes[0].sigla.split('.')
                proxima_sigla = prefix + '.' + str(int(sufixo) + 1).zfill(4)
                self.sigla = proxima_sigla
            else:
                self.sigla = 'RES' + '.0001'

        super(self.__class__, self).save(*args, **kwargs)


class ComponenteCurricular(LogResidenciaModel):
    SEARCH_FIELDS = ['componente__sigla', 'componente__descricao']

    PRATICA = 1
    TEORICA = 2
    TEORICO_PRATICA = 3
    TIPO_CHOICES = [
        [PRATICA, 'Prática'],
        [TEORICA, 'Teórica'],
        [TEORICO_PRATICA, 'Teórico Prática']
    ]

    # CH_8H_MENSAIS = 1
    # CH_4H_MENSAIS = 2
    # CH_2H_SEMANAIS = 3
    # CH_CUMPRIMENTO_CHOICES = [
    #     [CH_8H_MENSAIS, '8 horas mensais'],
    #     [CH_4H_MENSAIS, '4 horas mensais'],
    #     [CH_2H_SEMANAIS, '2 horas semanais']
    # ]

    FREQ_RES_PRAT = 1
    FREQ_PRECEPTOR = 2
    FREQ_RES_EXT = 3
    FREQ_CHOICES = [
        [FREQ_RES_PRAT, 'Registro realizado pelo Residente - Atividades Práticas'],
        [FREQ_PRECEPTOR, 'Registro realizado pelo Preceptor/Apoiador'],
        [FREQ_RES_EXT, 'Registro realizado pelo Residente - Atividades Extras']
    ]

    # Dados gerais
    nome_do_componente = models.CharFieldPlus('Nome do Componente', blank=False, null=True, default='')
    matriz = models.ForeignKeyPlus('residencia.Matriz')
    componente = models.ForeignKeyPlus('residencia.Componente', verbose_name='Atividades')
    periodo_letivo = models.PositiveIntegerField('Período', null=True, blank=True)
    # Unidade de apredezagem
    unidade_aprendizagem = models.ForeignKeyPlus('residencia.UnidadeAprendizagem', null=True, on_delete=models.CASCADE)
    tipo = models.PositiveIntegerField(choices=TIPO_CHOICES, default=PRATICA)
    # Carga horária
    ch_total = models.PositiveIntegerField('Carga Horária Total', help_text='Hora-Relógio', null=True, blank=True)
    ch_cumprimento = models.PositiveIntegerField('Cumprimento da Carga Horária', null=True, blank=False)
    # Frequência
    registro_freq = models.PositiveIntegerField(
        'Tipo de Registro de Frequência', choices=FREQ_CHOICES, default=FREQ_RES_PRAT
    )
    # Pré requisitos
    pre_requisitos = models.ManyToManyFieldPlus('residencia.ComponenteCurricular', related_name='prerequisitosresidencia_set', blank=True)
    # Co-requisitos
    co_requisitos = models.ManyToManyFieldPlus('residencia.ComponenteCurricular', related_name='corequisitosresidencia_set', blank=True)

    avaliacao_por_conceito = models.BooleanField(
        'Avaliação por Conceito', default=False, help_text='Marque essa opção caso a representação conceitual da nota deve ser apresentada ao invés do valor numérico.'
    )
    is_dinamico = models.BooleanField(
        'Descrição Dinâmica', default=False, help_text='Marque essa opção caso deseje que a descrição do componente possa ser complementada no diário.'
    )
    ementa = models.TextField('Ementa', blank=True, null=True, default='')

    class Meta:
        ordering = ('nome_do_componente', 'matriz', 'periodo_letivo', 'componente__descricao')
        unique_together = ('matriz', 'componente')
        verbose_name = 'Componente Curricular'
        verbose_name_plural = 'Componentes Curriculares'



    def clean(self):

        # if hasattr(self, 'componente') and self.ch_presencial >= 0 and self.ch_pratica >= 0:
        #     if self.ch_presencial + self.ch_pratica != self.componente.ch_hora_relogio:
        #         raise ValidationError('A soma das cargas horárias deve ser {}'.format(self.componente.ch_hora_relogio))
        if self.periodo_letivo and self.periodo_letivo > self.matriz.qtd_periodos_letivos:
            raise ValidationError('O período letivo excede a quantidade de períodos da matriz.')

    def __str__(self):
        return '{}'.format(str(self.nome_do_componente))

    def get_carga_horaria_total(self):
        return self.ch_total

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        self.matriz.verificar_inconsistencias()
        self.matriz.save()

    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)

        self.matriz.verificar_inconsistencias()
        self.matriz.save()

    def get_grupo_componente_historico(self, grupos_componentes):
        componentes = None
        if self.tipo == ComponenteCurricular.PRATICA:
            componentes = grupos_componentes['Prática']
        elif self.tipo == ComponenteCurricular.TEORICO_PRATICA:
            componentes = grupos_componentes['Teórico Prática']
        elif self.tipo == ComponenteCurricular.TEORICA:
            componentes = grupos_componentes['Teórica']
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

    def get_periodo_letivo(self):
        return self.periodo_letivo and self.periodo_letivo or 0


class UnidadeAprendizagem(LogResidenciaModel):
    descricao = models.CharFieldPlus('Descrição', width=100)
    qtd_avaliacoes = models.PositiveIntegerField(verbose_name='Quantidade de Avaliações',
                                                       choices=[[x, x] for x in range(1, 3)], default=1)
    ciclo = models.PositiveIntegerField(verbose_name='Ciclo de avaliação',
                                                       choices=[[x, x] for x in range(1, 5)], default=1)

    class Meta:
        verbose_name = 'Unidade de Aprendizagem'
        verbose_name_plural = 'Unidades de Aprendizagem'

class EstruturaCurso(LogResidenciaModel):

    CRITERIO_AVALIACAO_NOTA = 1
    CRITERIO_AVALIACAO_FREQUENCIA = 2
    CRITERIO_AVALIACAO_CHOICES = [[CRITERIO_AVALIACAO_NOTA, 'Nota'], [CRITERIO_AVALIACAO_FREQUENCIA, 'Frequência']]
    # Dados gerais
    id = models.AutoField("Código", primary_key=True)
    descricao = models.CharFieldPlus('Descrição', width=500)
    ativo = models.BooleanField('Está Ativa', default=True)

    # Critérios de Avaliação
    criterio_avaliacao = models.PositiveIntegerField('Critério de Avaliação', choices=CRITERIO_AVALIACAO_CHOICES)
    media_aprovacao_sem_prova_final = models.NotaField('Média para passar sem prova final', null=True, blank=True)

    class Meta:
        verbose_name = 'Estrutura da Residência'
        verbose_name_plural = 'Estruturas da Residência'

    def get_absolute_url(self):
        return '/residencia/estruturacurso/{:d}/'.format(self.pk)

    def clean(self):
        if self.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_NOTA:
            if self.media_aprovacao_sem_prova_final is None:
                raise ValidationError('A média para passar sem prova final deve ser informada')

    def get_representacoesconceituais(self):
        return self.representacaoconceitual_set.all().order_by('descricao')

    def get_conceito(self, nota):
        qs_conceito = self.representacaoconceitual_set.filter(valor_minimo__lte=nota, valor_maximo__gte=nota)
        if qs_conceito.exists():
            return qs_conceito[0]
        else:
            return nota

    def get_matrizes_ativas(self):
        return self.matriz_set.filter(data_fim__isnull=True)

    def get_matrizes_inativas(self):
        return self.matriz_set.filter(data_fim__isnull=False)

class RepresentacaoConceitual(LogResidenciaModel):
    estrutura_curso = models.ForeignKeyPlus('residencia.EstruturaCurso')
    descricao = models.CharFieldPlus('Descrição')
    valor_minimo = models.NotaField('Valor Mínimo')
    valor_maximo = models.NotaField('Valor Máximo')

    class Meta:
        verbose_name = 'Representação Conceitual'
        verbose_name_plural = 'Representações Conceituais'


class CursoResidencia(LogResidenciaModel):
    SEARCH_FIELDS = ['codigo', 'codigo_academico', 'descricao', 'descricao_historico']

    PERIODICIDADE_ANUAL = 1
    PERIODICIDADE_CHOICES = [[PERIODICIDADE_ANUAL, 'Anual'],]

    codigo_academico = models.IntegerField(null=True)

    objects = models.Manager()
    locals = CursoResidenciaManager()

    # Identificação
    id = models.AutoField(verbose_name='Código', primary_key=True)
    descricao = models.CharFieldPlus(verbose_name='Descrição', width=500)
    descricao_historico = models.CharFieldPlus(verbose_name='Descrição no Diploma e Histórico', width=500)

    # Dados da Criação
    data_inicio = models.DateFieldPlus('Data início', null=True)
    data_fim = models.DateFieldPlus('Data fim', null=True, blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    # Outros Dados
    codigo = models.CharFieldPlus(verbose_name='Código', help_text='Código para composição de turmas e matrículas', unique=True)

    periodicidade = models.PositiveIntegerField('Periodicidade', choices=PERIODICIDADE_CHOICES, null=True)

    matrizes = models.ManyToManyFieldPlus('residencia.Matriz', through='residencia.MatrizCurso')
    ppc = models.FileFieldPlus(upload_to='residencia/ppc/', null=True, blank=True, verbose_name='PPC', default=None)

    coordenador = models.ForeignKeyPlus('rh.Funcionario', null=True, blank=True)

    class Meta:
        verbose_name = 'Curso Residênca'
        verbose_name_plural = 'Cursos Residêncas'
        ordering = ('-ativo',)

    def __str__(self):
        codigo = self.codigo.replace('-', '')
        return '{} - {}'.format(codigo, self.descricao)

    def get_absolute_url(self):
        return '/residencia/cursoresidencia/{:d}/?tab=matrizes'.format(self.pk)

    # TODO Implementar
    # def possui_residentes_cursando(self):

    def clean(self):
        if CursoResidencia.objects.filter(codigo__iexact=self.codigo).exclude(id=self.id).exists():
            raise ValidationError('Já existe um curso com este mesmo código. O código do curso deve ser único.')
        if self.ativo and self.data_fim:
            raise ValidationError('Um curso ativo não pode ter data de fim')
        super().clean()


    def save(self, *args, **kwargs):
        curso_residencia = None
        if self.pk:
            curso_residencia = CursoResidencia.objects.get(pk=self.pk)
        super().save(*args, **kwargs)
        if curso_residencia and curso_residencia.coordenador_id and self.coordenador_id != curso_residencia.coordenador_id:
            UsuarioGrupo.objects.filter(user=curso_residencia.coordenador.user, group__name='Coordenadores(as) Residência').delete()

    def is_coordenador(self, user):
        is_coordenador = self.coordenador and self.coordenador.username == user.username
        return is_coordenador


class Matriz(LogResidenciaModel):
    SEARCH_FIELDS = ['id', 'descricao']

    objects = MatrizManager()
    # Dados gerais
    id = models.AutoField(verbose_name='Código', primary_key=True)
    descricao = models.CharFieldPlus(verbose_name='Descrição', width=500)
    ativo = models.BooleanField('Ativa', default=True)
    data_inicio = models.DateFieldPlus('Data de início')
    data_fim = models.DateFieldPlus('Data de fim', null=True, blank=True)
    ppp = models.FileFieldPlus(upload_to='residencia/ppp/', null=True, blank=True, verbose_name='PPP')
    qtd_periodos_letivos = models.PositiveIntegerField(verbose_name='Quantidade de Anos Letivos', choices=[[x, x] for x in range(1, 3)])
    # Estrutura
    estrutura = models.ForeignKeyPlus('residencia.EstruturaCurso', null=True, on_delete=models.CASCADE)
    # Carga horária
    ch_pratica = models.PositiveIntegerField('Carga Horária Prática', help_text='Hora-Relógio', null=True, blank=True)
    ch_teorica = models.PositiveIntegerField('Carga Horária Teórica', help_text='Hora-Relógio', null=True, blank=True)
    ch_teorico_pratica = models.PositiveIntegerField('Carga Horária Teórico Prática', help_text='Hora-Relógio', null=True, blank=True)

    # Critérios
    porcetagem_cumprimento_ch_teorica = models.PositiveIntegerField('Porcetagem de cumprimento mínimo da carga horária teórica', help_text='0-100%', default=100)

    # Componentes
    componentes = models.ManyToManyField('residencia.Componente', through='residencia.ComponenteCurricular')

    # A matriz possui inconsistência?
    inconsistente = models.BooleanField(default=False)
    # Exige trabalho de conclusão de curso
    exige_tcr = models.BooleanField('Exige TCR', help_text='Marque essa opção caso a apresentação de um Trabalho de Conclusão de Residência seja um pré-requisito para a finalização do curso', default=False)

    observacao = models.TextField('Observação', null=True, blank=True)



    class Meta:
        verbose_name = 'Matriz Curricular'
        verbose_name_plural = 'Matrizes Curriculares'
        ordering = ('descricao',)

    # TODO Implementar
    def pode_ser_editada(self, user=None):
        return True
        # if user and user.is_superuser:
        #     return True
        # return not self.aluno_set.filter(situacao__id=SituacaoMatricula.CONCLUIDO).exists()

    def get_grade_curricular(self):
        result = dict()
        for cc in self.componentecurricular_set.all():
            p = str(cc.periodo_letivo or 0)
            prerequisitos = []
            for prerequisito in cc.pre_requisitos.all():
                prerequisitos.append(dict(id=str(prerequisito.pk)))
            corequisitos = []
            for corequisito in cc.co_requisitos.all():
                corequisitos.append(dict(id=str(corequisito.pk)))
            componente = dict(
                componente=cc.componente.descricao_historico.replace("'", ""),
                id=str(cc.pk),
                periodo=str(p),
                tipo=str(cc.tipo),
                prerequisitos=prerequisitos,
                corequisitos=corequisitos,
                ch_hora_relogio=cc.componente.ch_hora_relogio,
                sigla=cc.componente.sigla,
            )
            if p not in result:
                result[p] = []
            result[p].append(componente)
        return result

    def toJson(self):
        import json

        m = []
        for cc in self.componentecurricular_set.filter(unidade_aprendizagem__isnull=False).order_by('unidade_aprendizagem__id'):
            prerequisitos = []
            corequisitos = []
            for prerequisito in cc.pre_requisitos.all():
                prerequisitos.append(dict(id=str(prerequisito.pk)))
            for corequisito in cc.co_requisitos.all():
                corequisitos.append(dict(id=str(corequisito.pk)))


            m.append(
                dict(
                    componente='{} - {}'.format(cc.componente.abreviatura, cc.componente.descricao_historico.replace("'", "")),
                    id=str(cc.pk),
                    periodo=str(cc.periodo_letivo or 0),
                    tipo=str(cc.tipo),
                    prerequisitos=prerequisitos,
                    corequisitos=corequisitos,
                    ch_hora_relogio=cc.componente.ch_hora_relogio,
                    sigla=cc.unidade_aprendizagem.descricao,
                )
            )
        return json.dumps(dict(matriz=m))

    def get_numero_colunas(self):
        qs = self.componentecurricular_set.all().values_list('periodo_letivo', flat=True).order_by('-periodo_letivo')
        return qs and qs[0] or 0

    def get_numero_linhas(self):
        numero_linhas = 0
        for dicionarios in self.componentecurricular_set.values('periodo_letivo').annotate(Count('id')).order_by():
            count = dicionarios['id__count']
            if count >= numero_linhas:
                numero_linhas = count
        return numero_linhas

    def replicar(self, descricao):
        componentes_curriculares = self.componentecurricular_set.all()
        for _ in componentes_curriculares:
            pass
        self.id = None
        self.descricao = descricao
        self.clean()
        self.save()

        for componente_curricular in componentes_curriculares:
            pre_requisitos = componente_curricular.pre_requisitos.all()
            co_requisitos = componente_curricular.co_requisitos.all()
            componente_curricular.id = None
            componente_curricular.matriz = self
            componente_curricular.save()
            for pre_requisito in pre_requisitos:
                componente_curricular.pre_requisitos.add(pre_requisito)
            for co_requisito in co_requisitos:
                componente_curricular.co_requisitos.add(co_requisito)

        return self

    def clean(self):
        if self.ativo and self.data_fim:
            raise ValidationError('Uma matriz ativa não pode ter data de fim')
        if not self.ativo and not self.data_fim:
            raise ValidationError('Uma matriz inativa deve ter data de fim')

    def __str__(self):
        return '{} - {}'.format(self.pk, self.descricao)

    def get_absolute_url(self):
        return '/residencia/matriz/{:d}/'.format(self.pk)

    def get_ch_total(self):
        total = 0
        for componente_curricular in self.componentecurricular_set.all():
            total += componente_curricular.componente.ch_hora_relogio
        return total

    def get_carga_horaria_total_prevista(self):
        return (
            (self.ch_pratica or 0)
            + (self.ch_teorica or 0)
            + (self.ch_teorico_pratica or 0)
        )

    def possui_componentes_pratica(self):
        return self.ch_pratica > 0

    def possui_componentes_teorica(self):
        return self.ch_teorica > 0

    def possui_componentes_teorico_pratica(self):
        return self.ch_teorico_pratica > 0

    # COMPONENTES

    def get_ids_componentes(self, periodos=[], apenas_obrigatorio=False, apenas_optativas=False):
        qs = self.get_componentes_curriculares(periodos, apenas_obrigatorio, apenas_optativas)
        return qs.values_list('componente__id', flat=True)

    def get_componentes(self, apenas_obrigatorio=False):
        return Componente.objects.filter(id__in=self.get_ids_componentes([], apenas_obrigatorio))

    def get_ids_componentes_pratica(self):
        return self.get_componentes_curriculares_pratica().values_list('componente__id', flat=True)

    def get_componentes_regulares_pratica(self):
        return Componente.objects.filter(id__in=self.get_ids_componentes_pratica())

    def get_ids_componentes_teorica(self):
        return self.get_componentes_curriculares_teorica().values_list('componente__id', flat=True)

    def get_componentes_regulares_teorica(self):
        return Componente.objects.filter(id__in=self.get_ids_componentes_teorica())

    def get_ids_componentes_teorico_pratica(self):
        return self.get_componentes_curriculares_teorico_pratica().values_list('componente__id', flat=True)

    def get_componentes_regulares_teorico_pratica(self):
        return Componente.objects.filter(id__in=self.get_ids_componentes_teorico_pratica())

   # COMPONENTES CURRICULARES
    def get_componentes_curriculares(self, periodos=[], apenas_obrigatorio=False, apenas_optativas=False):
        qs = self.componentecurricular_set.all()
        if periodos:
            if type(periodos) == list:
                qs = qs.filter(periodo_letivo__in=periodos)
            else:
                qs = qs.filter(periodo_letivo=periodos)

        return qs

    def get_componentes_curriculares_pratica(self):
        return self.get_componentes_curriculares(apenas_obrigatorio=True).filter(tipo=ComponenteCurricular.PRATICA)

    def get_componentes_curriculares_teorico_pratica(self):
        return self.get_componentes_curriculares(apenas_obrigatorio=True).filter(tipo=ComponenteCurricular.TEORICO_PRATICA)

    def get_componentes_curriculares_teorica(self):
        return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TEORICA)

    # CARGA HORRÁRIA DOS COMPONENTES CURRICULARES
    def get_ch_pratica(self, nucleo=None, relogio=True):
        componentes_pratica = self.get_componentes_curriculares_pratica()
        if relogio:
            return componentes_pratica.aggregate(qtd=Sum('componente__ch_hora_relogio')).get('qtd') or 0
        else:
            return componentes_pratica.aggregate(qtd=Sum('componente__ch_hora_aula')).get('qtd') or 0

    def get_ch_teorico_pratica(self, nucleo=None, relogio=True):
        componentes_teorico_pratica = self.get_componentes_curriculares_teorico_pratica()
        if relogio:
            return componentes_teorico_pratica.aggregate(qtd=Sum('componente__ch_hora_relogio')).get('qtd') or 0
        else:
            return componentes_teorico_pratica.aggregate(qtd=Sum('componente__ch_hora_aula')).get('qtd') or 0

    def get_ch_teorica(self, nucleo=None, relogio=True):
        componentes_teoricas = self.get_componentes_curriculares_teorica()
        if relogio:
            return componentes_teoricas.aggregate(qtd=Sum('componente__ch_hora_relogio')).get('qtd') or 0
        else:
            return componentes_teoricas.aggregate(qtd=Sum('componente__ch_hora_aula')).get('qtd') or 0

    def get_ch_pratica_faltando(self):
        return self.ch_pratica - self.get_ch_pratica()

    def get_ch_teorico_pratica_faltando(self):
        return self.ch_teorico_pratica - self.get_ch_teorico_pratica()

    def get_ch_teorica_faltando(self):
        return self.ch_teorica - self.get_ch_teorica()

    def is_ch_pratica_faltando(self):
        return self.get_ch_pratica_faltando() > 0

    def is_ch_teorico_pratica_faltando(self):
        return self.get_ch_teorico_pratica_faltando() > 0

    def is_ch_teorica_faltando(self):
        return self.get_ch_teorica_faltando() > 0

    def is_ch_faltando(self):
        return (
            self.is_ch_pratica_faltando()
            or self.is_ch_teorica_faltando()
            or self.is_ch_teorico_pratica_faltando()
        )

    def is_ch_pratica_consistente(self):
        return self.get_ch_pratica() == self.ch_pratica

    def is_ch_teorico_pratica_consistente(self):
        return self.get_ch_teorico_pratica() == self.ch_teorico_pratica

    def verificar_inconsistencias(self):
        retorno = False
        #
        # if self.is_ch_faltando() or not self.is_ch_pratica_consistente():
        #     self.inconsistente = True
        # else:
        #     self.inconsistente = False

        return retorno

    def save(self, *args, **kwargs):
        self.verificar_inconsistencias()
        super().save(*args, **kwargs)


class MatrizCurso(LogResidenciaModel):
    SEARCH_FIELDS = ['curso_campus__descricao', 'curso_campus__codigo', 'matriz__pk']
    # Manager
    objects = models.Manager()

    # Fields
    curso_campus = models.ForeignKeyPlus('residencia.CursoResidencia', on_delete=models.CASCADE, verbose_name='Curso')
    matriz = models.ForeignKeyPlus('residencia.Matriz', on_delete=models.CASCADE, verbose_name='Matriz')

    search = models.SearchField(attrs=['curso_campus', 'matriz'])

    class Meta:
        verbose_name = 'Vínculo de Matriz em Curso'
        verbose_name_plural = 'Vínculos de Matriz em Curso'
        unique_together = ('matriz', 'curso_campus')

    def get_ext_combo_template(self):
        return '<p>Matriz: {} </p><p>Curso: {}</p>'.format(
            self.matriz, self.curso_campus.descricao
        )

    def get_absolute_url(self):
        return '/residencia/cursocampus/{}/?tab=matrizes'.format(self.curso_campus.pk)

    def __str__(self):
        return 'Matriz: {} Curso: {}'.format(self.matriz, self.curso_campus.descricao)

    def clean(self):
        if not hasattr(self, 'matriz'):
            raise ValidationError('Por favor selecione uma matriz.')
        if not self.matriz.estrutura:
            raise ValidationError('Não é possível adicionar matriz a este curso, pois o mesmo não possui Estrutura de Curso.')
        # if self.matriz.estrutura.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_FREQUENCIA:
        #     for componente_curricular in self.matriz.componentecurricular_set.all():
        #         if componente_curricular.qtd_avaliacoes > 0:
        #             raise ValidationError('Matrizes com componentes que requerem avaliações não podem ser vinculadas a cursos cuja estrutura de avaliação seja por frequência')

    # TODO Implementar
    def pode_ser_excluida(self):
        # from edu.models.alunos import Aluno
        #
        # return not Aluno.objects.filter(matriz=self.matriz, curso_campus=self.curso_campus).exists()
        return True

    def delete(self, *args, **kwargs):
        if self.pode_ser_excluida():
            super().delete(*args, **kwargs)
        else:
            raise Exception('A Matriz não pode ser removida, pois existem alunos nela matriculados.')



class CalendarioAcademico(LogResidenciaModel):
    SEARCH_FIELDS = ['id', 'descricao', 'uo__sigla']

    TIPO_ANUAL = 1
    TIPO_SEMESTRAL = 2
    TIPO_TEMPORARIO = 3
    TIPO_CHOICES = [[TIPO_ANUAL, 'Anual'],]

    QTD_ETAPA_1 = 1
    QTD_ETAPA_2 = 2
    QTD_ETAPA_4 = 4
    QTD_ETAPAS_CHOICES = [[QTD_ETAPA_1, 'Ciclo Único'], [QTD_ETAPA_2, 'Dois Ciclos'], [QTD_ETAPA_4, 'Quatro Ciclos']]

    # Managers
    objects = models.Manager()


    # Dados Gerais
    id = models.AutoField(verbose_name='Código', primary_key=True)
    descricao = models.CharFieldPlus(verbose_name='Descrição', width=500)
    tipo = models.PositiveIntegerField(verbose_name='Tipo', choices=TIPO_CHOICES)
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano letivo', related_name='calendarios_residencia_por_ano_letivo_set', on_delete=models.CASCADE)
    periodo_letivo = models.PositiveIntegerField(verbose_name='Período letivo', choices=PERIODO_LETIVO_CHOICES)
    data_inicio = models.DateFieldPlus(verbose_name='Início')
    data_fim = models.DateFieldPlus(verbose_name='Término')
    data_fechamento_periodo = models.DateFieldPlus(verbose_name='Data de Fechamento do Período', help_text='Data limite para lançamento de notas/faltas pelos professores')
    eh_calendario_referencia = models.BooleanField('Calendário de Referência?', default=False)

    # Dados das Etapas
    qtd_etapas = models.PositiveIntegerField(verbose_name='Quantidade de Etapas', choices=QTD_ETAPAS_CHOICES)

    data_inicio_etapa_1 = models.DateFieldPlus(verbose_name='Início', help_text='Data de início da primeiro ciclo', null=True, blank=True)
    data_fim_etapa_1 = models.DateFieldPlus(verbose_name='Fim', help_text='Data de encerramento da primeiro ciclo', null=True, blank=True)

    data_inicio_etapa_2 = models.DateFieldPlus(verbose_name='Início', help_text='Data de início da segundo ciclo', null=True, blank=True)
    data_fim_etapa_2 = models.DateFieldPlus(verbose_name='Fim', help_text='Data de encerramento da segundo ciclo', null=True, blank=True)

    data_inicio_etapa_3 = models.DateFieldPlus(verbose_name='Início', help_text='Data de início da terceiro ciclo', null=True, blank=True)
    data_fim_etapa_3 = models.DateFieldPlus(verbose_name='Fim', help_text='Data de encerramento da terceiro ciclo', null=True, blank=True)

    data_inicio_etapa_4 = models.DateFieldPlus(verbose_name='Início', help_text='Data de início da quarto ciclo', null=True, blank=True)
    data_fim_etapa_4 = models.DateFieldPlus(verbose_name='Fim', help_text='Data de encerramento da quarto ciclo', null=True, blank=True)

    data_inicio_trancamento = models.DateFieldPlus(verbose_name='Início do Trancamento', null=True, blank=True)
    data_fim_trancamento = models.DateFieldPlus(verbose_name='Encerramento do Trancamento', null=True, blank=True)

    data_inicio_certificacao = models.DateFieldPlus(verbose_name='Início da Cert. e Aproveitamento', null=True, blank=True)
    data_fim_certificacao = models.DateFieldPlus(verbose_name='Encerramento da Cert. e Aproveitamento', null=True, blank=True)

    data_inicio_prova_final = models.DateFieldPlus(verbose_name='Início da Prova Final', null=True, blank=True)
    data_fim_prova_final = models.DateFieldPlus(verbose_name='Encerramento da Prova Final', null=True, blank=True)

    data_inicio_espaco_pedagogico = models.DateFieldPlus(verbose_name='Início', null=True, blank=True)
    data_fim_espaco_pedagogico = models.DateFieldPlus(verbose_name='Fim', null=True, blank=True)

    class Meta:
        verbose_name = 'Calendário Acadêmico'
        verbose_name_plural = 'Calendários Acadêmicos'
        ordering = ('descricao',)

    def get_data_inicio_letivo(self):
        return self.data_inicio_espaco_pedagogico or self.data_inicio_etapa_1

    def get_data_fim_utlima_etapa(self):
        if self.data_fim_prova_final:
            return self.data_fim_prova_final
        data = self.qtd_etapas == 1 and self.data_fim_etapa_1 or self.qtd_etapas == 2 and self.data_fim_etapa_2 or self.qtd_etapas == 4 and self.data_fim_etapa_4
        return somar_data(data, 1)

    def get_absolute_url(self):
        return '/residencia/calendarioacademico/{:d}/'.format(self.pk)

    def __str__(self):
        return '[{}] - {}/{}.{}'.format(self.pk, self.descricao, self.ano_letivo, self.periodo_letivo)

    def mensal(self):
        return self.anual(full=False)

    def anual(self, full=True, etapas=True):
        cal = Calendario()

        if etapas:
            data_inicio = self.data_inicio_etapa_1
            data_fim = self.data_fim_etapa_1
            descricao = '1ª Ciclo'
            cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, 'success')

            if self.qtd_etapas > 1:
                data_inicio = self.data_inicio_etapa_2
                data_fim = self.data_fim_etapa_2
                descricao = '2ª Ciclo'
                cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, 'info')

            if self.qtd_etapas > 2:
                data_inicio = self.data_inicio_etapa_3
                data_fim = self.data_fim_etapa_3
                descricao = '3ª Ciclo'
                cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, 'alert')

                data_inicio = self.data_inicio_etapa_4
                data_fim = self.data_fim_etapa_4
                descricao = '4ª Ciclo'
                cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, 'error')

            data_inicio = self.data_fechamento_periodo
            data_fim = self.data_fechamento_periodo
            descricao = 'Fechamento do Período'
            cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, 'conflito')
        if full:
            return cal.formato_periodo(self.data_inicio.month, self.data_inicio.year, self.data_fechamento_periodo.month, self.data_fechamento_periodo.year)
        else:
            hoje = datetime.datetime.today()

            return cal.formato_mes(hoje.year, hoje.month)

    def clean(self):
        msg = None
        try:
            if self.data_inicio > self.data_fim:
                msg = ValidationError('A data de encerramento deve ser maior que a data de início.')
            if self.data_fim > self.data_fechamento_periodo:
                msg = ValidationError(
                    'A data de fechamento do período deve ser maior que a data de encerramento das aulas.')
            if not self.data_inicio == self.data_inicio_etapa_1:
                msg = ValidationError('A data de início da primeiro ciclo deve ser igual a data de início das aulas.')
            if self.data_inicio_etapa_1 > self.data_fim_etapa_1:
                msg = ValidationError(
                    'A data de encerramento da primeiro ciclo deve ser superior da data de início da primeiro ciclo.')
            if self.qtd_etapas == CalendarioAcademico.QTD_ETAPA_2:
                if not self.data_inicio_etapa_2 or not self.data_fim_etapa_2:
                    msg = ValidationError('Preencha as datas de início e de fim da segundo ciclo.')
            if self.qtd_etapas == CalendarioAcademico.QTD_ETAPA_4:
                if not self.data_inicio_etapa_2 or not self.data_fim_etapa_2:
                    msg = ValidationError('Preencha as datas de início e de fim da segundo ciclo.')
                if not self.data_inicio_etapa_3 or not self.data_fim_etapa_3:
                    msg = ValidationError('Preencha as datas de início e de fim da terceiro ciclo.')
                if not self.data_inicio_etapa_4 or not self.data_fim_etapa_4:
                    msg = ValidationError('Preencha as datas de início e de fim da quarto ciclo.')
            if self.qtd_etapas == CalendarioAcademico.QTD_ETAPA_1:
                if not self.data_fim == self.data_fim_etapa_1:
                    msg = ValidationError(
                        'A data de encerramento da primeiro ciclo deve ser igual a data de encerramento das aulas.')
            if self.qtd_etapas > CalendarioAcademico.QTD_ETAPA_1:
                if self.data_fim_etapa_1 > self.data_inicio_etapa_2:
                    msg = ValidationError(
                        'A data de início da segundo ciclo deve ser superior a data de encerramento da primeiro ciclo.')
            if self.qtd_etapas > CalendarioAcademico.QTD_ETAPA_1:
                if self.data_inicio_etapa_2 > self.data_fim_etapa_2:
                    msg = ValidationError(
                        'A data de encerramento da segundo ciclo deve ser superior a data de início da segundo ciclo.')
            if self.qtd_etapas == CalendarioAcademico.QTD_ETAPA_2:
                if not self.data_fim == self.data_fim_etapa_2:
                    msg = ValidationError(
                        'A data de encerramento da segundo ciclo deve ser igual a data de encerramento das aulas.')
            if self.qtd_etapas > CalendarioAcademico.QTD_ETAPA_2:
                if self.data_fim_etapa_2 > self.data_inicio_etapa_3:
                    msg = ValidationError(
                        'A data de início da terceiro ciclo deve ser superior a data de encerramento da segundo ciclo.')
            if self.qtd_etapas > CalendarioAcademico.QTD_ETAPA_2:
                if self.data_inicio_etapa_3 > self.data_fim_etapa_3:
                    msg = ValidationError(
                        'A data de encerramento da terceiro ciclo deve ser superior a data de início da terceiro ciclo.')
            if self.qtd_etapas > CalendarioAcademico.QTD_ETAPA_2:
                if self.data_fim_etapa_3 > self.data_inicio_etapa_4:
                    msg = ValidationError(
                        'A data de início da quarto ciclo deve ser superior a data de encerramento da terceiro ciclo.')
            if self.qtd_etapas > CalendarioAcademico.QTD_ETAPA_2:
                if self.data_inicio_etapa_4 > self.data_fim_etapa_4:
                    msg = ValidationError(
                        'A data de encerramento da quarto ciclo deve ser superior a data de início da quarto ciclo.')
            if self.qtd_etapas == CalendarioAcademico.QTD_ETAPA_4:
                if not self.data_fim == self.data_fim_etapa_4:
                    msg = ValidationError(
                        'A data de encerramento da quarto ciclo deve ser igual a data de encerramento das aulas.')
        except Exception:
            raise ValidationError('Preencha os campos obrigatórios.')
        if msg:
            raise msg

    # def replicar(self, uos):
    #     ids = []
    #     modelo = self
    #     for uo in uos:
    #         if not '[REPLICADO]' in modelo.descricao:
    #             modelo.descricao = '{} [REPLICADO]'.format(modelo.descricao)
    #         modelo.id = None
    #         modelo.uo = uo
    #         modelo.save()
    #         ids.append(str(modelo.id))
    #     return ids

    def save(self, *args, **kwargs):
        # selecionando professordiario que tenham o calendário acadêmico e alternando as datas das etapas
        super(self.__class__, self).save(*args, **kwargs)
        #
        # professores_diarios = ProfessorDiario.objects.filter(diario__calendario_academico=self)
        # for professor_diario in professores_diarios:
        #     professor_diario.atualizar_data_posse()