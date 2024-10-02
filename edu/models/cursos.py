import datetime

from comum.models import UsuarioGrupo
from django.db import transaction
from django.db.models.aggregates import Sum, Count
from djtools.db import models
from edu.managers import FiltroDiretoriaManager, MatrizManager, CursoCampusManager, MinicursoObjectsManager, MinicursoLocalsManager
from edu.models.cadastros_gerais import PERIODO_LETIVO_CHOICES, Modalidade, NivelEnsino, SituacaoMatricula
from edu.models.diretorias import Diretoria
from edu.models.logs import LogModel
from rh.models import UnidadeOrganizacional
from decimal import Decimal
from django.core.exceptions import ValidationError


class Componente(LogModel):
    SEARCH_FIELDS = ['descricao', 'descricao_historico', 'sigla', 'sigla_qacademico', 'abreviatura']

    descricao = models.CharFieldPlus(verbose_name='Descrição', width=500)
    descricao_historico = models.CharFieldPlus(verbose_name='Descrição no Diploma e Histórico', width=500)
    tipo = models.ForeignKeyPlus('edu.TipoComponente', verbose_name='Tipo do Componente', on_delete=models.CASCADE)
    sigla = models.CharFieldPlus(max_length=255, unique=True)
    diretoria = models.ForeignKeyPlus('edu.Diretoria', on_delete=models.CASCADE)
    nivel_ensino = models.ForeignKeyPlus('edu.NivelEnsino', verbose_name='Nível de ensino', on_delete=models.CASCADE)
    ativo = models.BooleanField('Está ativo', default=True)

    ch_hora_relogio = models.PositiveIntegerField('Hora/relógio')
    ch_hora_aula = models.PositiveIntegerField('Hora/aula')
    ch_qtd_creditos = models.PositiveIntegerField('Qtd. de créditos')

    observacao = models.TextField('Observação', blank=True, default='')
    sigla_qacademico = models.CharFieldPlus('Sigla do Q-Acadêmico', null=True)
    abreviatura = models.CharFieldPlus('Abreviatura', max_length=10, null=True)

    class Meta:
        verbose_name = 'Componente'
        verbose_name_plural = 'Componentes'
        ordering = ('descricao',)

    def __str__(self):
        return '{} - {} - {} [{} h/{} Aulas] {}'.format(
            self.sigla, self.descricao, str(self.nivel_ensino), self.ch_hora_relogio, self.ch_hora_aula, (self.observacao and '- {}'.format(self.observacao or ''))
        )

    def get_fator_conversao_hora_aula(self):
        return self.ch_hora_relogio and (Decimal(self.ch_hora_aula) / Decimal(self.ch_hora_relogio)) or Decimal(0)

    def get_absolute_url(self):
        return '/edu/componente/{:d}/'.format(self.pk)

    def clean(self):
        if hasattr(self, 'nivel_ensino'):
            qs = Componente.objects.filter(
                descricao=self.descricao, ch_hora_relogio=self.ch_hora_relogio, ch_hora_aula=self.ch_hora_aula, nivel_ensino=self.nivel_ensino, observacao=self.observacao
            ).exclude(id=self.id)
            if qs.exists():
                raise ValidationError('Já existe um componente ({}) cadastrado com a mesma descrição, carga horária, nível de ensino e observação.'.format(qs[0].pk))
        if Componente.objects.filter(sigla__iexact=self.sigla).exclude(id=self.id).exists():
            raise ValidationError('A sigla do componente deve ser única.')

    def save(self, *args, **kwargs):
        alterou_tipo_componente = False
        if self.id:
            old = Componente.objects.get(id=self.id)
            if old.tipo.id != self.tipo.id:
                alterou_tipo_componente = True

        if (not self.id and not self.sigla) or alterou_tipo_componente:
            tipos = Componente.objects.filter(tipo=self.tipo).exclude(id=self.id).order_by('-sigla')

            if tipos:
                prefix, sufixo = tipos[0].sigla.split('.')
                proxima_sigla = prefix + '.' + str(int(sufixo) + 1).zfill(4)
                self.sigla = proxima_sigla
            else:
                self.sigla = str(self.tipo) + '.0001'

        super(self.__class__, self).save(*args, **kwargs)


class ComponenteCurricular(LogModel):
    SEARCH_FIELDS = ['componente__sigla', 'componente__descricao']

    TIPO_REGULAR = 1
    TIPO_SEMINARIO = 2
    TIPO_PRATICA_PROFISSIONAL = 3
    TIPO_TRABALHO_CONCLUSAO_CURSO = 4
    TIPO_ATIVIDADE_EXTENSAO = 5
    TIPO_PRATICA_COMO_COMPONENTE = 6
    TIPO_VISITA_TECNICA = 7
    TIPO_CHOICES = [
        [TIPO_REGULAR, 'Regular'],
        [TIPO_SEMINARIO, 'Seminário'],
        [TIPO_PRATICA_PROFISSIONAL, 'Prática Profissional'],
        [TIPO_TRABALHO_CONCLUSAO_CURSO, 'Trabalho de Conclusão de Curso'],
        [TIPO_ATIVIDADE_EXTENSAO, 'Atividade de Extensão'],
        [TIPO_PRATICA_COMO_COMPONENTE, 'Prática como Componente Curricular'],
    ]

    ESTAGIO_DOCENTE_1 = 1
    ESTAGIO_DOCENTE_2 = 2
    ESTAGIO_DOCENTE_3 = 3
    ESTAGIO_DOCENTE_4 = 4
    ESTAGIO_DOCENTE_MATRIZ_ANTERIOR = 5

    TIPO_ESTAGIO_DOCENTE_CHOICES = [
        [ESTAGIO_DOCENTE_1, 'Estágio Docente I'],
        [ESTAGIO_DOCENTE_2, 'Estágio Docente II'],
        [ESTAGIO_DOCENTE_3, 'Estágio Docente III'],
        [ESTAGIO_DOCENTE_4, 'Estágio Docente IV'],
        [ESTAGIO_DOCENTE_MATRIZ_ANTERIOR, 'Estágio Docente de Matriz Anterior'],
    ]

    MODULO_1 = 1
    MODULO_2 = 2
    MODULO_3 = 3
    MODULO_4 = 4
    MODULO_5 = 5
    MODULO_6 = 6
    MODULO_7 = 7

    TIPO_MODULO_CHOICES = [
        [MODULO_1, 'Módulo I'],
        [MODULO_2, 'Módulo II'],
        [MODULO_3, 'Módulo III'],
        [MODULO_4, 'Módulo IV'],
        [MODULO_5, 'Módulo V'],
        [MODULO_6, 'Módulo VI'],
        [MODULO_7, 'Módulo VII'],
    ]
    # Dados gerais
    matriz = models.ForeignKeyPlus('edu.Matriz')
    componente = models.ForeignKeyPlus('edu.Componente')
    classificacao_complementar = models.ForeignKeyPlus('edu.ClassificacaoComplementarComponenteCurricular', null=True, blank=True, verbose_name='Classificação Complementar')
    periodo_letivo = models.PositiveIntegerField('Período', null=True, blank=True)
    tipo = models.PositiveIntegerField(choices=TIPO_CHOICES)
    optativo = models.BooleanField(default=False)
    is_seminario_estagio_docente = models.BooleanField(
        'É um Seminário de Estágio Docente? (Ou Estágio Docente de Matriz Anterior)',
        default=False,
        help_text='Marcar caso este componente curricular seja um seminário de estágio docente.',
    )
    tipo_estagio_docente = models.PositiveIntegerField('Tipo de Estágio Docente', choices=TIPO_ESTAGIO_DOCENTE_CHOICES, null=True, blank=True)
    tipo_modulo = models.PositiveIntegerField('Tipo de Módulo', choices=TIPO_MODULO_CHOICES, null=True, blank=True)
    qtd_avaliacoes = models.PositiveIntegerField('Qtd. Avaliações', choices=[[0, 'Zero'], [1, 'Uma'], [2, 'Duas'], [4, 'Quatro']])
    nucleo = models.ForeignKeyPlus('edu.Nucleo', verbose_name='Núcleo', on_delete=models.CASCADE)
    # Carga horária
    ch_presencial = models.PositiveIntegerField('Teórica', help_text='Hora-Relógio')
    ch_pratica = models.PositiveIntegerField('Prática', help_text='Hora-Relógio')
    ch_extensao = models.PositiveIntegerField('Extensão', help_text='Hora-Relógio', default=0)
    ch_pcc = models.PositiveIntegerField('Prática como Componente Curricular', help_text='Hora-Relógio', default=0)
    ch_visita_tecnica = models.PositiveIntegerField('Visita Técnica/Aula de Campo', help_text='Hora-Relógio', default=0)
    percentual_maximo_ead = models.PositiveIntegerField('% Máximo EAD', help_text='Percentual máximo de aulas que o professor pode registrar à distância, ou seja, na modalidade EAD.', default=0)
    # Pré requisitos
    pre_requisitos = models.ManyToManyFieldPlus('edu.ComponenteCurricular', related_name='prerequisitos_set', blank=True)
    # Co-requisitos
    co_requisitos = models.ManyToManyFieldPlus('edu.ComponenteCurricular', related_name='corequisitos_set', blank=True)

    avaliacao_por_conceito = models.BooleanField(
        'Avaliação por Conceito', default=False, help_text='Marque essa opção caso a representação conceitual da nota deve ser apresentada ao invés do valor numérico.'
    )
    is_dinamico = models.BooleanField(
        'Descrição Dinâmica', default=False, help_text='Marque essa opção caso deseje que a descrição do componente possa ser complementada no diário.'
    )

    componente_curricular_associado = models.ForeignKeyPlus('edu.ComponenteCurricular', related_name='associados_set', null=True, blank=True)
    segundo_semestre = models.BooleanField('Segundo Semestre', default=False, help_text='Marque essa opção caso a disciplina seja ofertada no segundo semestre.')

    pode_fechar_pendencia = models.BooleanField('Pode Fechar com Pendência', default=False)
    ementa = models.TextField('Ementa', blank=True, null=True, default='')

    class Meta:
        ordering = ('matriz', 'periodo_letivo', 'componente__descricao', 'tipo', 'nucleo')
        unique_together = ('matriz', 'componente')
        verbose_name = 'Componente Curricular'
        verbose_name_plural = 'Componentes Curriculares'

    def get_ch_qtd_creditos_nucleo(self):
        return sum(
            ComponenteCurricular.objects.filter(matriz=self.matriz, nucleo=self.nucleo, periodo_letivo=self.periodo_letivo).values_list('componente__ch_qtd_creditos', flat=True)
        )

    def clean(self):
        from edu.models import MatrizCurso, EstruturaCurso

        if self.matriz.estrutura.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_MODULAR and not self.tipo_modulo:
            raise ValidationError('A estrutura de curso desta matriz exige que seja informado o tipo de módulo do componente curricular.')

        if self.tipo == ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO and self.qtd_avaliacoes != 1:
            raise ValidationError('Componentes de TCC devem possuir 1 avaliação.')

        if self.qtd_avaliacoes and self.qtd_avaliacoes > 0:

            if MatrizCurso.locals.filter(matriz=self.matriz, matriz__estrutura__criterio_avaliacao=EstruturaCurso.CRITERIO_AVALIACAO_FREQUENCIA).exists():
                raise ValidationError('Componentes com avaliação não podem ser adicionados a matrizes já vinculadas a cursos cuja estrutura de avaliação seja por frequência.')

        if hasattr(self, 'componente') and self.ch_presencial >= 0 and self.ch_pratica >= 0:
            if self.ch_presencial + self.ch_pratica + self.ch_extensao + self.ch_pcc + self.ch_visita_tecnica != self.componente.ch_hora_relogio:
                raise ValidationError('A soma das cargas horárias deve ser {}'.format(self.componente.ch_hora_relogio))
        if self.periodo_letivo and self.periodo_letivo > self.matriz.qtd_periodos_letivos:
            raise ValidationError('O período letivo excede a quantidade de períodos da matriz.')

        if self.is_seminario_estagio_docente and not self.tipo_estagio_docente:
            raise ValidationError(
                dict(
                    tipo_estagio_docente='Este componente curricular foi marcado como de Seminário de Estágio Docente, neste caso o preenchimento do Tipo de Estágio Docente é obrigatório.'
                )
            )

        if not self.is_seminario_estagio_docente and self.tipo_estagio_docente:
            raise ValidationError(
                dict(
                    tipo_estagio_docente='Este componente curricular não foi marcado como de Seminário de Estágio Docente, neste caso não deve ser preenchido Tipo de Estágio Docente.'
                )
            )

    def __str__(self):
        return '{} [Matriz {}]'.format(str(self.componente), self.matriz.pk)

    def get_carga_horaria_total(self):
        return self.ch_pratica + self.ch_presencial

    def is_projeto_final(self):
        return self.tipo == self.TIPO_TRABALHO_CONCLUSAO_CURSO or self.tipo == self.TIPO_PRATICA_PROFISSIONAL

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
        if self.tipo == ComponenteCurricular.TIPO_REGULAR:
            componentes = grupos_componentes['Componentes Curriculares']
        elif self.tipo == ComponenteCurricular.TIPO_SEMINARIO:
            componentes = grupos_componentes['Seminários']
        elif self.tipo == ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL:
            componentes = grupos_componentes['Prática Profissional']
        elif self.tipo == ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO:
            componentes = grupos_componentes['Componentes Curriculares']
        elif self.tipo == ComponenteCurricular.TIPO_ATIVIDADE_EXTENSAO:
            componentes = grupos_componentes['Atividade de Extensão']
        elif self.tipo == ComponenteCurricular.TIPO_PRATICA_COMO_COMPONENTE:
            componentes = grupos_componentes['Prática como Componente Curricular']
        elif self.tipo == ComponenteCurricular.TIPO_VISITA_TECNICA:
            componentes = grupos_componentes['Visita Técnica / Aula da Campo']
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


class EstruturaCurso(LogModel):
    TIPO_AVALIACAO_CREDITO = 1
    TIPO_AVALIACAO_SERIADO = 2
    TIPO_AVALIACAO_FIC = 3
    TIPO_AVALIACAO_MODULAR = 4
    TIPO_AVALIACAO_CHOICES = [[TIPO_AVALIACAO_CREDITO, 'Crédito'], [TIPO_AVALIACAO_SERIADO, 'Seriado'], [TIPO_AVALIACAO_FIC, 'FIC'], [TIPO_AVALIACAO_MODULAR, 'Modular']]

    CRITERIO_AVALIACAO_NOTA = 1
    CRITERIO_AVALIACAO_FREQUENCIA = 2
    CRITERIO_AVALIACAO_CHOICES = [[CRITERIO_AVALIACAO_NOTA, 'Nota'], [CRITERIO_AVALIACAO_FREQUENCIA, 'Frequência']]

    IRA_ARITMETICA_NOTAS_FINAIS = 1
    IRA_PONDERADA_POR_CH = 2
    IRA_CHOICES = [[IRA_ARITMETICA_NOTAS_FINAIS, 'Média aritmética das Notas Finais'], [IRA_PONDERADA_POR_CH, 'Média dos componentes pela carga horária dos componentes']]

    # Dados gerais
    id = models.AutoField("Código", primary_key=True)
    descricao = models.CharFieldPlus('Descrição', width=500)
    ativo = models.BooleanField('Está Ativa', default=True)

    # Aproveitamento de Disciplinas
    percentual_max_aproveitamento = models.PositiveIntegerField(
        'Percentual Máximo de Aproveitamento',
        help_text='Percentual (%) máximo de carga horária aproveitada/certificada em relação a carga horária das disciplinas na matriz. Informe 0 (zero) caso esse valor seja indeterminado.',
        null=True,
        blank=True,
        default=0,
    )
    formas_ingresso_ignoradas_aproveitamento = models.ManyToManyFieldPlus(
        'edu.FormaIngresso',
        verbose_name='Ignorar Formas de Ingresso',
        help_text='Formas de ingressos que não serão contabilizadas no cálculo de carga-horária aproveitada.',
        blank=True,
    )
    numero_max_certificacoes = models.PositiveIntegerField(
        'Número Máximo de Certificações por Período',
        help_text='Número máximo de certificação de conhecimento em disciplinas no mesmo período da matriz. Informe 0 (zero) caso esse valor seja indeterminado.',
        null=True,
        default=0,
    )
    media_certificacao_conhecimento = models.NotaField(
        'Média para Certificação', help_text='Média para certificação de conhecimento. Informe 0 (zero) caso esse valor seja indeterminado.', null=True, default=0
    )
    quantidade_max_creditos_aproveitamento = models.PositiveIntegerField(
        'Quantidade Máxima de Créditos para Aproveitamento',
        help_text='Quantidade máxima de créditos aproveitados/certificados. Informe 0 (zero) caso esse valor seja indeterminado.',
        null=True,
        blank=True,
        default=8,
    )

    # Critérios de Apuração de Resultados por Período
    # fic
    proitec = models.BooleanField('Proitec', help_text='Marque esta opção caso esta estrutura se destine a cursos Proitec.', default=False)
    tipo_avaliacao = models.PositiveIntegerField('Tipo de Avaliação', choices=TIPO_AVALIACAO_CHOICES)
    # seriado
    limite_reprovacao = models.PositiveIntegerField(
        'Número Máximo de Reprovações para Aprovação por Dependência',
        help_text='Quantidade máxima de reprovações em disciplinas no período que permite os alunos cursarem a próxima série.',
        null=True,
        blank=True,
    )
    # crédito
    qtd_minima_disciplinas = models.PositiveIntegerField(
        'Número Mínimo de Disciplinas por Período', help_text='Quantidade mínima de matrículas em disciplinas por período letivo.', null=True, blank=True
    )
    numero_disciplinas_superior_periodo = models.PositiveIntegerField(
        'Número Máximo de Disciplinas extras por Período',
        help_text='Número máximo de matrículas em disciplinas a mais no período em relação ao número de disciplinas daquele período definido na matriz.',
        null=True,
        blank=True,
    )
    qtd_max_periodos_subsequentes = models.PositiveIntegerField(
        'Número Máximo de Períodos Subsequentes para Matrícula em Disciplina',
        help_text='Quantidade máxima de períodos subsequentes ao período de referência na qual os alunos podem se matricular em disciplinas.',
        null=True,
        blank=True,
    )
    numero_max_cancelamento_disciplina = models.PositiveIntegerField(
        'Número Máximo de Cancelamentos de Disciplinas', help_text='Número máximo de cancelamento de disciplinas ao longo do curso.', null=True, blank=True
    )

    # Critérios de Avaliação por Disciplinas
    criterio_avaliacao = models.PositiveIntegerField('Critério de Avaliação', choices=CRITERIO_AVALIACAO_CHOICES)
    media_aprovacao_sem_prova_final = models.NotaField('Média para passar sem prova final', null=True, blank=True)
    media_evitar_reprovacao_direta = models.NotaField('Média para não reprovar direto', null=True, blank=True)
    media_aprovacao_avaliacao_final = models.NotaField('Média para aprovação após avaliação final', null=True, blank=True)

    # Critérios de Apuração de Frequência
    percentual_frequencia = models.PositiveIntegerField(
        'Percentual Mínimo de Frequência', help_text='Percentual (%) mínimo de frequência para que os alunos não reprovem no período ou na disciplina.', default=90
    )
    reprovacao_por_falta_disciplina = models.BooleanField(
        'Reprovação por Disciplina', help_text='Marque essa opção caso o controle da frequência seja feita por disciplina e não por módulo/série.', default=False
    )
    limitar_ch_por_tipo_aula = models.BooleanField(
        'Limitar Carga-Horária por Tipo de Aula',
        help_text='Marque essa opção caso a carga-horária de aulas definida na vinculação dos componentes às matrizes deva ser utilizada como limite na contabilização das cargas-horárias das aulas registradas no diário pelo professor.', default=False
    )

    # Coeficiente de rendimento(IRA)
    ira = models.PositiveIntegerField('Forma de Cálculo (I.R.A)', choices=IRA_CHOICES, default=1)

    # Fechamento de período
    permite_fechamento_com_pendencia = models.BooleanField(
        'Permitir fechamento com pendência', default=False, help_text='Habilita a possibilidade de fechar o período letivo do aluno mesmo havendo pendências em algum diário.'
    )

    # Critérios de Jubilamento
    qtd_periodos_conclusao = models.PositiveIntegerField(
        'Número Máximo de Matrículas em Períodos',
        help_text='Quantidade máxima de matrículas em períodos letivos que os alunos podem se matricular até concluir o curso. Informe 0 (zero) caso esse valor seja indeterminado.',
        default=0,
    )
    qtd_max_reprovacoes_periodo = models.PositiveIntegerField(
        'Número Máximo de Reprovações no Mesmo Período',
        help_text='Quantidade máxima de reprovações que os alunos podem ter no mesmo período da matriz. Informe 0 (zero) caso esse valor seja indeterminado.',
        null=True,
        default=0,
    )
    qtd_max_reprovacoes_disciplina = models.PositiveIntegerField(
        'Número Máximo de Reprovações na Mesma Disciplina',
        help_text='Qtd. máxima de reprovações que os alunos podem ter na mesma disciplina. Informe 0 (zero) caso esse valor seja indeterminado.',
        null=True,
        default=0,
    )

    # Critérios de Trancamento
    qtd_trancamento_voluntario = models.PositiveIntegerField(
        'Número Máximo de Trancamentos',
        help_text='Quantidade máxima de trancamentos de forma voluntária que os alunos podem realizar durante todo o curso.',
        blank=True,
        null=True,
        default=2,
    )

    pode_entregar_etapa_sem_aula = models.BooleanField(
        'Entregar Etapa Sem Aula', default=False, help_text='Marque essa opção caso seja permitido a entrega de etapa de diário sem registro de aula lançado para a etapa.'
    )

    pode_lancar_nota_fora_do_prazo = models.BooleanField(
        'Lançar Nota Fora do Prazo', default=False, help_text='Marque essa opção caso seja permitido que o professor de diário compartilhado lance nota em data diferente do período de posse da etapa pelo professor.'
    )

    plano_estudo = models.BooleanField('Permite Plano de Estudo', help_text='Marque essa opção caso os alunos necessitem solicitar dispensa/planejamento de plano de estudo durante a renovação da matrícula caso tenham ultrapassado o tempo de conclusão mínimo do curso.', default=False)

    # Critérios relacionados a matrícula
    numero_min_alunos_diario = models.IntegerField('Número Mínimo de Alunos em Diários', null=True, blank=True, help_text='Preencha essa opção caso haja um limite mínimo do número de alunos que devem estar matriculados nos diários.')
    numero_max_alunos_especiais = models.IntegerField('Número Máximo de Alunos Especiais', null=True, blank=True, help_text='Preencha essa opção apenas caso seja necessário limitar o número de alunos especiais em cursos de pós-graduação.')
    requer_declaracao_para_cancelamento_matricula = models.BooleanField('Requer Declaração para Cancelamento de Matrícula', default=False, help_text='Marque essa opção caso seja necessário a apresentação de uma declaração reconhecida em cartório para a realização do cancelamento voluntário no curso.')

    class Meta:
        verbose_name = 'Estrutura de Curso'
        verbose_name_plural = 'Estruturas de Curso'

    def get_absolute_url(self):
        return '/edu/estruturacurso/{:d}/'.format(self.pk)

    def clean(self):
        if self.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_SERIADO:
            if self.limite_reprovacao is None:
                raise ValidationError('O limite de reprovações deve ser informado')
        if self.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_NOTA:
            if self.media_aprovacao_sem_prova_final is None:
                raise ValidationError('A média para passar sem prova final deve ser informada')
        if self.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_NOTA:
            if self.media_evitar_reprovacao_direta is None:
                raise ValidationError('A média para não reprovar direto deve ser informada')
        if self.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_NOTA:
            if self.media_aprovacao_avaliacao_final is None:
                raise ValidationError('A média para aprovação após avaliação final deve ser informada')
        if self.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_FREQUENCIA:
            if MatrizCurso.locals.filter(matriz__estrutura=self, matriz__componentecurricular__qtd_avaliacoes__gt=0).exists():
                raise ValidationError(
                    'Estruturas associadas a cursos já vinculados a matrizes contendo componentes com avaliações não podem ter como critério de avaliacão a frequência.'
                )
        if not self.media_certificacao_conhecimento:
            self.media_certificacao_conhecimento = self.media_aprovacao_sem_prova_final

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


class Habilitacao(LogModel):
    descricao = models.CharFieldPlus('Descrição', width=500)

    class Meta:
        verbose_name = 'Habilitação'
        verbose_name_plural = 'Habilitações'

    def __str__(self):
        return self.descricao


class CursoCampus(LogModel):
    SEARCH_FIELDS = ['codigo', 'codigo_academico', 'descricao', 'descricao_historico']

    PERIODICIDADE_ANUAL = 1
    PERIODICIDADE_SEMESTRAL = 2
    PERIODICIDADE_LIVRE = 3
    PERIODICIDADE_CHOICES = [[PERIODICIDADE_ANUAL, 'Anual'], [PERIODICIDADE_SEMESTRAL, 'Semestral'], [PERIODICIDADE_LIVRE, 'Livre']]

    codigo_academico = models.IntegerField(null=True)

    objects = models.Manager()
    locals = CursoCampusManager()

    # Identificação
    id = models.AutoField(verbose_name='Código', primary_key=True)
    descricao = models.CharFieldPlus(verbose_name='Descrição', width=500)
    descricao_historico = models.CharFieldPlus(verbose_name='Descrição no Diploma e Histórico', width=500)
    codigo_censup = models.CharFieldPlus('Código CENSUP', default='', blank=True)
    codigo_emec = models.CharFieldPlus('Código EMEC', default='', blank=True)
    codigo_sistec = models.CharFieldPlus(
        'Código SISTEC', default='', blank=True, help_text='Separar por ";" sem espaço caso exista mais de um código cadastrado no SISTEC para esse curso. Ex: 00001;00002'
    )
    codigo_educacenso = models.CharFieldPlus('Código EDUCACENSO', null=True, blank=True)
    ciencia_sem_fronteira = models.BooleanField('Ciência sem Fronteiras', help_text='Prioritário para o programa Ciência sem Fronteiras?', default=False)
    formacao_de_professores = models.BooleanField('Formação de Professores', help_text='Marque essa opção caso se trate de um curso de formação de professores', default=False)
    # Dados da Criação
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano letivo', related_name='cursos_por_ano_letivo_set', null=True, on_delete=models.CASCADE)
    periodo_letivo = models.PositiveIntegerField('Período letivo', null=True, choices=PERIODO_LETIVO_CHOICES)
    data_inicio = models.DateFieldPlus('Data início', null=True)
    data_fim = models.DateFieldPlus('Data fim', null=True, blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    # Outros Dados
    codigo = models.CharFieldPlus(verbose_name='Código', help_text='Código para composição de turmas e matrículas', unique=True)
    natureza_participacao = models.ForeignKeyPlus('edu.NaturezaParticipacao', verbose_name='Natureza de participação', null=True, on_delete=models.CASCADE)
    modalidade = models.ForeignKeyPlus('edu.Modalidade', null=True, verbose_name='Modalidade de Ensino', on_delete=models.CASCADE)
    plano_ensino = models.BooleanField('Exige Plano de Ensino', help_text='Marque essa opção caso os professores necessitem informar o plano de ensino das disciplas nos diários', default=False)
    # cursos Licenciatura
    area = models.ForeignKeyPlus('edu.AreaCurso', null=True, verbose_name='Área', blank=True, on_delete=models.CASCADE)
    coordenadores_estagio_docente = models.ManyToManyFieldPlus(
        'edu.Professor', verbose_name='Coordenadores de Estágio Docente', related_name='cursos_coordenacao_estagio_docente_set'
    )
    # cursos tecnológicos ou FIC
    eixo = models.ForeignKeyPlus('edu.EixoTecnologico', null=True, verbose_name='Eixo Tecnológico', blank=True, on_delete=models.CASCADE)
    # cursos de pós-graduação
    area_capes = models.ForeignKeyPlus('edu.AreaCapes', null=True, verbose_name='Área Capes', blank=True, on_delete=models.CASCADE)

    periodicidade = models.PositiveIntegerField('Periodicidade', choices=PERIODICIDADE_CHOICES, null=True)
    exige_enade = models.BooleanField(default=False)
    exige_colacao_grau = models.BooleanField('Exige colação de grau', default=False)
    assinatura_digital = models.BooleanField('Certificado/Diploma Assinado via Certificado ICP-Brasil', default=False)
    emite_diploma = models.BooleanField('Certificado/Diploma Emitido pelo Campus', default=False)
    assinatura_eletronica = models.BooleanField('Certificado/Diploma Assinado via Certificado ICP-EDU', default=False)
    area_concentracao = models.ForeignKeyPlus('edu.AreaConcentracao', verbose_name='Área de Concentração', null=True, blank=True, on_delete=models.CASCADE)
    programa = models.CharFieldPlus('Programa', blank=True, default='')

    diretoria = models.ForeignKeyPlus('edu.Diretoria', null=True, verbose_name='Diretoria', on_delete=models.CASCADE)
    extensao = models.BooleanField('Curso de Extensão?', default=False)
    coordenador = models.ForeignKeyPlus('rh.Funcionario', null=True, blank=True)
    numero_portaria_coordenador = models.CharFieldPlus('Nº Portaria', null=True, blank=True, help_text='Número da portaria que nomeou o servidor como coordenador do curso.')
    coordenador_2 = models.ForeignKeyPlus('rh.Funcionario', verbose_name='Vice-Coordenador', null=True, blank=True, related_name='cursocampus_vicecoordenador_set')
    numero_portaria_coordenador_2 = models.CharFieldPlus(
        'Nº Portaria (vice-coordenador)', null=True, blank=True, help_text='Número da portaria que nomeou o servidor como vice-coordenador do curso.'
    )
    matrizes = models.ManyToManyFieldPlus('edu.Matriz', through='edu.MatrizCurso')

    # Ato normativo
    resolucao_criacao = models.TextField('Documento de Criação', blank=True, null=True)

    # Titulo do certificado de conclusão
    titulo_certificado_masculino = models.CharFieldPlus('Masculino', blank=True, null=True)
    titulo_certificado_feminino = models.CharFieldPlus('Feminino', blank=True, null=True)

    # Atributo de Minicurso
    ppc = models.FileFieldPlus(upload_to='edu/ppc/', null=True, blank=True, verbose_name='PPC', default=None)
    ch_total = models.PositiveIntegerField('Carga Horária Total h/r', blank=True, null=True, default=None)
    ch_aula = models.PositiveIntegerField('Carga Horária Total h/a', blank=True, null=True, default=None)
    tipo_hora_aula = models.PositiveIntegerField('Tipo Hora Aula', blank=True, null=True, choices=[[45, '45 min'], [60, '60 min']])

    fator_esforco_curso = models.DecimalField('Fator de Esforço de Curso (FEC)', blank=True, null=True, default=1, max_digits=4, decimal_places=2)

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ('-ativo',)
        app_label = 'edu'

    def __str__(self):
        codigo = self.codigo.replace('-', '')
        return '{} - {} ({})'.format(codigo, self.descricao, str(self.diretoria and self.diretoria.setor.uo.nome or '-'))

    def get_absolute_url(self):
        return '/edu/cursocampus/{:d}/?tab=matrizes'.format(self.pk)

    def get_funcao_coordenador(self):
        if self.coordenador:
            from rh.models import Servidor

            servidor = Servidor.objects.get(pk=self.coordenador)
            return servidor.funcao
        return None

    def possui_aluno_cursando(self):
        from edu.models import Aluno

        situacoes = (SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE, SituacaoMatricula.TRANCADO, SituacaoMatricula.MATRICULADO, SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL)
        return Aluno.objects.filter(curso_campus=self, situacao__in=situacoes).exists()

    def clean(self):
        if CursoCampus.objects.filter(codigo__iexact=self.codigo).exclude(id=self.id).exists():
            raise ValidationError('Já existe um curso com este mesmo código. O código do curso deve ser único.')
        if self.ativo and self.data_fim:
            raise ValidationError('Um curso ativo não pode ter data de fim')
        super().clean()

    def replicar(self, diretoria, codigo='[REPLICADO]', coordenador=None, coordenador_2=None):
        matrizes = self.matrizes.all()
        self.id = None
        self.codigo_censup = ''
        self.codigo_emec = ''
        self.codigo_sistec = ''
        self.codigo_educacenso = None
        self.descricao = '{} [REPLICADO]'.format(self.descricao)
        self.codigo = codigo
        self.diretoria = diretoria
        self.codigo_academico = None
        self.coordenador = coordenador
        self.coordenador_2 = coordenador_2
        self.clean()
        self.save()
        for matriz in matrizes:
            mc = MatrizCurso()
            mc.curso_campus = self
            mc.matriz = matriz
            mc.save()
        return self

    def is_fic(self):
        return self.modalidade and self.modalidade.pk == Modalidade.FIC

    def is_licenciatura(self):
        return self.modalidade and self.modalidade.pk == Modalidade.LICENCIATURA

    def eh_pos_graduacao(self):
        return self.modalidade and self.modalidade.pk in [Modalidade.MESTRADO, Modalidade.ESPECIALIZACAO, Modalidade.APERFEICOAMENTO, Modalidade.DOUTORADO]

    def save(self, *args, **kwargs):
        curso_campus = None
        if self.pk:
            curso_campus = CursoCampus.objects.get(pk=self.pk)
        super().save(*args, **kwargs)
        if curso_campus and curso_campus.coordenador_id and self.coordenador_id != curso_campus.coordenador_id:
            UsuarioGrupo.objects.filter(user=curso_campus.coordenador.user, group__name='Coordenador de Curso').delete()
        if curso_campus and curso_campus.coordenador_2_id and self.coordenador_2_id != curso_campus.coordenador_2_id:
            UsuarioGrupo.objects.filter(user=curso_campus.coordenador_2.user, group__name='Coordenador de Curso').delete()

    def is_coordenador(self, user):
        is_coordenador = self.coordenador and self.coordenador.username == user.username
        is_vice_coordenador = self.coordenador_2 and self.coordenador_2.username == user.username
        return is_coordenador or is_vice_coordenador


class RepresentacaoConceitual(LogModel):
    estrutura_curso = models.ForeignKeyPlus('edu.EstruturaCurso')
    descricao = models.CharFieldPlus('Descrição')
    valor_minimo = models.NotaField('Valor Mínimo')
    valor_maximo = models.NotaField('Valor Máximo')

    class Meta:
        verbose_name = 'Representação Conceitual'
        verbose_name_plural = 'Representações Conceituais'


class EquivalenciaComponenteQAcademico(LogModel):
    q_academico = models.PositiveIntegerField('Código Q-Acadêmico')
    sigla = models.CharFieldPlus('Sigla')
    descricao = models.CharFieldPlus('Descrição', width=500)
    carga_horaria = models.PositiveIntegerField('Carga horária')
    componente = models.ForeignKeyPlus('edu.Componente', null=True)

    class Meta:
        verbose_name = 'Equivalência Q-Academico'
        verbose_name_plural = 'Equivalências Q-Academico'

    def __str__(self):
        return '{} - {} ({}H)'.format(self.sigla, self.descricao, self.carga_horaria)


class Matriz(LogModel):
    SEARCH_FIELDS = ['id', 'descricao']

    objects = MatrizManager()
    locals = FiltroDiretoriaManager('matrizcurso__curso_campus__diretoria')
    # Dados gerais
    id = models.AutoField(verbose_name='Código', primary_key=True)
    descricao = models.CharFieldPlus(verbose_name='Descrição', width=500)
    ano_criacao = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano Criação', on_delete=models.CASCADE)
    periodo_criacao = models.PositiveIntegerField('Período Criação', default=1, choices=PERIODO_LETIVO_CHOICES)
    ativo = models.BooleanField('Ativa', default=True)
    data_inicio = models.DateFieldPlus('Data de início')
    data_fim = models.DateFieldPlus('Data de fim', null=True, blank=True)
    ppp = models.FileFieldPlus(upload_to='edu/ppp/', null=True, blank=True, verbose_name='PPP')
    qtd_periodos_letivos = models.PositiveIntegerField(verbose_name='Quantidade de Períodos Letivos', choices=[[x, x] for x in range(1, 13)])
    nivel_ensino = models.ForeignKeyPlus('edu.NivelEnsino', verbose_name='Nível de Ensino', null=True, on_delete=models.CASCADE)
    # Estrutura
    estrutura = models.ForeignKeyPlus('edu.EstruturaCurso', null=True, on_delete=models.CASCADE)
    # Carga horária
    ch_componentes_obrigatorios = models.PositiveIntegerField('Componentes obrigatórios', help_text='Hora-Relógio')
    ch_componentes_optativos = models.PositiveIntegerField('Componentes optativos', help_text='Hora-Relógio')
    ch_componentes_eletivos = models.PositiveIntegerField('Componentes eletivos', help_text='Hora-Relógio')
    ch_seminarios = models.PositiveIntegerField('Seminários', help_text='Hora-Relógio')
    ch_pratica_profissional = models.PositiveIntegerField('Prática Profissional', help_text='Hora-Relógio')
    ch_atividades_complementares = models.PositiveIntegerField('Atividades complementares', help_text='Hora-Relógio')
    ch_atividades_aprofundamento = models.PositiveIntegerField('Atividades Teórico-Práticas de Aprofundamento', help_text='Hora-Relógio')
    ch_atividades_extensao = models.PositiveIntegerField('Atividades de Extensão', help_text='Hora-Relógio')
    ch_componentes_tcc = models.PositiveIntegerField('Trabalho de Conclusão de Curso', help_text='Hora-Relógio')
    ch_pratica_como_componente = models.PositiveIntegerField('Prática como Componente Curricular', help_text='Hora-Relógio')
    ch_visita_tecnica = models.PositiveIntegerField('Visita Técnica/Aula de Campo', help_text='Hora-Relógio')

    # Componentes
    componentes = models.ManyToManyField('edu.Componente', through='edu.ComponenteCurricular')
    configuracao_atividade_academica = models.ForeignKeyPlus(
        'edu.ConfiguracaoAtividadeComplementar', null=True, blank=True, verbose_name='Configuração de AACC', on_delete=models.CASCADE
    )
    configuracao_atividade_aprofundamento = models.ForeignKeyPlus(
        'edu.ConfiguracaoAtividadeAprofundamento', null=True, blank=True, verbose_name='Configuração de ATPA', on_delete=models.CASCADE
    )
    configuracao_creditos_especiais = models.ForeignKeyPlus(
        'edu.ConfiguracaoCreditosEspeciais', null=True, blank=True, verbose_name='Configuração de Créditos Especiais', on_delete=models.CASCADE
    )
    # A matriz possui inconsistência?
    inconsistente = models.BooleanField(default=False)
    # Exige trabalho de conclusão de curso
    exige_tcc = models.BooleanField('Exige TCC', help_text='Marque essa opção caso a apresentação de um trabalho de conclusão de curso seja um pré-requisito para a finalização do curso', default=False)

    observacao = models.TextField('Observação', null=True, blank=True)

    # Estágio
    exige_estagio = models.BooleanField('Exige Estágio e Afins', help_text='Marque essa opção caso a realização de estágio seja um pré-requisito para a finalização do curso', default=False)
    ch_minima_estagio = models.PositiveIntegerField('Carga Horária Mínima de Estágio e Afins', help_text='Hora', null=True, blank=True)

    periodo_minimo_estagio_obrigatorio = models.IntegerField(
        'Período Mínimo para Estágio Obrigatório',
        choices=[['', '------']] + [[x, x] for x in range(1, 10)],
        help_text='Período mínimo para realização do Estágio Obrigatório',
        null=True,
        blank=True,
    )
    periodo_minimo_estagio_nao_obrigatorio = models.IntegerField(
        'Período Mínimo para Estágio Não Obrigatório',
        choices=[['', '------']] + [[x, x] for x in range(1, 10)],
        help_text='Período mínimo para realização do Estágio Não Obrigatório',
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = 'Matriz Curricular'
        verbose_name_plural = 'Matrizes Curriculares'
        ordering = ('descricao',)

    def pode_ser_editada(self, user=None):
        if user and user.is_superuser:
            return True
        return not self.aluno_set.filter(situacao__id=SituacaoMatricula.CONCLUIDO).exists()

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
                optativo=cc.optativo,
            )
            if p not in result:
                result[p] = []
            result[p].append(componente)
        return result

    def toJson(self):
        import json

        m = []
        for cc in self.componentecurricular_set.all():
            prerequisitos = []
            corequisitos = []
            for prerequisito in cc.pre_requisitos.all():
                prerequisitos.append(dict(id=str(prerequisito.pk)))
            for corequisito in cc.co_requisitos.all():
                corequisitos.append(dict(id=str(corequisito.pk)))

            m.append(
                dict(
                    componente=cc.componente.descricao_historico.replace("'", ""),
                    id=str(cc.pk),
                    periodo=str(cc.periodo_letivo or 0),
                    tipo=str(cc.tipo),
                    prerequisitos=prerequisitos,
                    corequisitos=corequisitos,
                    ch_hora_relogio=cc.componente.ch_hora_relogio,
                    sigla=cc.componente.sigla,
                    optativo=cc.optativo,
                )
            )
        return json.dumps(dict(matriz=m))

    def get_numero_colunas(self):
        qs = self.componentecurricular_set.filter(optativo=False).values_list('periodo_letivo', flat=True).order_by('-periodo_letivo')
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
        return '/edu/matriz/{:d}/'.format(self.pk)

    def get_ch_total(self):
        total = 0
        for componente_curricular in self.componentecurricular_set.all():
            total += componente_curricular.componente.ch_hora_relogio
        return total

    def get_carga_horaria_total_prevista(self):
        return (
            self.ch_componentes_obrigatorios
            + self.ch_componentes_optativos
            + self.ch_componentes_eletivos
            + self.ch_seminarios
            + self.ch_pratica_profissional
            + self.ch_atividades_complementares
            + self.ch_atividades_aprofundamento
            + self.ch_atividades_extensao
            + self.ch_componentes_tcc
            + self.ch_pratica_como_componente
            + self.ch_visita_tecnica
        )

    def possui_componentes_obrigatorios(self):
        return self.ch_atividades_complementares > 0

    def possui_componentes_optativos(self):
        return self.ch_componentes_optativos > 0

    def possui_componentes_eletivos(self):
        return self.ch_componentes_eletivos > 0

    def requer_paticipacao_seminarios(self):
        return self.ch_seminarios > 0

    def exige_pratica_profissional(self):
        return self.ch_pratica_profissional > 0

    def exige_atividades_complementares(self):
        return self.ch_atividades_complementares > 0

    # COMPONENTES

    def get_ids_componentes(self, periodos=[], apenas_obrigatorio=False, apenas_optativas=False):
        qs = self.get_componentes_curriculares(periodos, apenas_obrigatorio, apenas_optativas)
        return qs.values_list('componente__id', flat=True)

    def get_componentes(self, apenas_obrigatorio=False):
        return Componente.objects.filter(id__in=self.get_ids_componentes([], apenas_obrigatorio))

    def get_ids_componentes_regulares_obrigatorios(self):
        return self.get_componentes_curriculares_regulares_obrigatorios().values_list('componente__id', flat=True)

    def get_componentes_regulares_obrigatorios(self):
        return Componente.objects.filter(id__in=self.get_ids_componentes_regulares_obrigatorios())

    def get_ids_componentes_regulares_optativos(self):
        return self.get_componentes_curriculares_optativos().values_list('componente__id', flat=True)

    def get_componentes_regulares_optativos(self):
        return Componente.objects.filter(id__in=self.get_ids_componentes_regulares_optativos())

    def get_ids_componentes_seminario(self, apenas_obrigatorio=False):
        qs = self.get_componentes_curriculares_seminario()
        if apenas_obrigatorio:
            qs = qs.exclude(optativo=True)
        return qs.values_list('componente__id', flat=True)

    def get_componentes_seminario(self, apenas_obrigatorio=False):
        return Componente.objects.filter(id__in=self.get_ids_componentes_seminario(apenas_obrigatorio))

    def get_ids_componentes_pratica_como_componente(self, apenas_obrigatorio=False):
        qs = self.get_componentes_curriculares_pratica_como_componente()
        if apenas_obrigatorio:
            qs = qs.exclude(optativo=True)
        return qs.values_list('componente__id', flat=True)

    def get_componentes_pratica_como_componente(self, apenas_obrigatorio=False):
        return Componente.objects.filter(id__in=self.get_ids_componentes_pratica_como_componente(apenas_obrigatorio))

    def get_ids_componentes_visita_tecnica(self, apenas_obrigatorio=False):
        qs = self.get_componentes_curriculares_visita_tecnica()
        if apenas_obrigatorio:
            qs = qs.exclude(optativo=True)
        return qs.values_list('componente__id', flat=True)

    def get_componentes_visita_tecnica(self, apenas_obrigatorio=False):
        return Componente.objects.filter(id__in=self.get_ids_componentes_visita_tecnica(apenas_obrigatorio))

    def get_ids_componentes_pratica_profissional(self, apenas_obrigatorio=False):
        qs = self.get_componentes_curriculares_pratica_profissional()
        if apenas_obrigatorio:
            qs = qs.exclude(optativo=True)
        return qs.values_list('componente__id', flat=True)

    def get_componentes_pratica_profissional(self, apenas_obrigatorio=False):
        return Componente.objects.filter(id__in=self.get_ids_componentes_pratica_profissional(apenas_obrigatorio))

    def get_ids_componentes_tcc(self, apenas_obrigatorio=False):
        qs = self.get_componentes_curriculares_tcc()
        if apenas_obrigatorio:
            qs = qs.exclude(optativo=True)
        return qs.values_list('componente__id', flat=True)

    def get_componentes_tcc(self, apenas_obrigatorio=False):
        return Componente.objects.filter(id__in=self.get_ids_componentes_tcc(apenas_obrigatorio))

    # COMPONENTES CURRICULARES

    def get_componentes_curriculares(self, periodos=[], apenas_obrigatorio=False, apenas_optativas=False):
        qs = self.componentecurricular_set.all()
        if periodos:
            if type(periodos) == list:
                qs = qs.filter(periodo_letivo__in=periodos)
            else:
                qs = qs.filter(periodo_letivo=periodos)
        if apenas_obrigatorio:
            qs = qs.exclude(optativo=True)

        if apenas_optativas:
            qs = qs.exclude(optativo=False)

        return qs

    def get_componentes_curriculares_regulares_obrigatorios(self):
        return self.get_componentes_curriculares(apenas_obrigatorio=True).filter(tipo=ComponenteCurricular.TIPO_REGULAR)

    def get_componentes_curriculares_optativos(self):
        return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TIPO_REGULAR, optativo=True)

    def get_componentes_curriculares_seminario(self):
        return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TIPO_SEMINARIO)

    def get_componentes_curriculares_pratica_profissional(self):
        return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL)

    def get_componentes_curriculares_pratica_como_componente(self):
        return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TIPO_PRATICA_COMO_COMPONENTE)

    def get_componentes_curriculares_visita_tecnica(self):
        return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TIPO_VISITA_TECNICA)

    def get_componentes_curriculares_tcc(self):
        return self.get_componentes_curriculares().filter(tipo=ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO)

    # CARGA HORRÁRIA DOS COMPONENTES CURRICULARES

    def get_ch_componentes_obrigatorios(self, nucleo=None, relogio=True):
        componentes_regulares = self.get_componentes_curriculares_regulares_obrigatorios()
        if nucleo:
            componentes_regulares = componentes_regulares.filter(nucleo=nucleo).distinct()
        if relogio:
            return componentes_regulares.aggregate(qtd=Sum('componente__ch_hora_relogio')).get('qtd') or 0
        else:
            return componentes_regulares.aggregate(qtd=Sum('componente__ch_hora_aula')).get('qtd') or 0

    def get_ch_componentes_optativos(self, nucleo=None, relogio=True):
        componentes_optativos = self.get_componentes_curriculares_optativos()
        if nucleo:
            componentes_optativos = componentes_optativos.filter(nucleo=nucleo).distinct()
        if relogio:
            return componentes_optativos.aggregate(qtd=Sum('componente__ch_hora_relogio')).get('qtd') or 0
        else:
            return componentes_optativos.aggregate(qtd=Sum('componente__ch_hora_aula')).get('qtd') or 0

    def get_ch_componentes_seminario(self, nucleo=None, relogio=True):
        componentes_seminarios = self.get_componentes_curriculares_seminario()
        if nucleo:
            componentes_seminarios = componentes_seminarios.filter(nucleo=nucleo).distinct()
        if relogio:
            return componentes_seminarios.aggregate(qtd=Sum('componente__ch_hora_relogio')).get('qtd') or 0
        else:
            return componentes_seminarios.aggregate(qtd=Sum('componente__ch_hora_aula')).get('qtd') or 0

    def get_ch_componentes_pratica_profissional(self, nucleo=None, relogio=True):
        componentes_pratica_profissional = self.get_componentes_curriculares_pratica_profissional()
        if nucleo:
            componentes_pratica_profissional = componentes_pratica_profissional.filter(nucleo=nucleo).distinct()
        if relogio:
            return componentes_pratica_profissional.aggregate(qtd=Sum('componente__ch_hora_relogio')).get('qtd') or 0
        else:
            return componentes_pratica_profissional.aggregate(qtd=Sum('componente__ch_hora_aula')).get('qtd') or 0

    def get_ch_componentes_tcc(self):
        return self.get_componentes_tcc().aggregate(Sum('ch_hora_relogio')).get('ch_hora_relogio__sum') or 0

    def get_ch_componentes_obrigatorios_faltando(self):
        return self.ch_componentes_obrigatorios - self.get_ch_componentes_obrigatorios()

    def get_ch_componentes_optativos_faltando(self):
        return self.ch_componentes_optativos - self.get_ch_componentes_optativos()

    def get_ch_componentes_seminario_faltando(self):
        return self.ch_seminarios - self.get_ch_componentes_seminario()

    def get_ch_componentes_pratica_profissional_faltando(self):
        return self.ch_pratica_profissional - self.get_ch_componentes_pratica_profissional()

    def get_ch_componentes_tcc_faltando(self):
        return self.ch_componentes_tcc - self.get_ch_componentes_tcc()

    def get_qtd_credito_componentes_obrigatorios(self, nucleo=None, periodo_letivo=None):
        componentes_obrigatorios = self.get_componentes_curriculares_regulares_obrigatorios()
        if nucleo:
            componentes_obrigatorios = componentes_obrigatorios.filter(nucleo=nucleo)
        if periodo_letivo:
            componentes_obrigatorios = componentes_obrigatorios.filter(periodo_letivo=periodo_letivo)
        return componentes_obrigatorios.aggregate(qtd=Sum('componente__ch_qtd_creditos')).get('qtd') or 0

    def get_qtd_credito_componentes_optativos(self, nucleo=None):
        componentes_optativos = self.get_componentes_curriculares_optativos()
        if nucleo:
            componentes_optativos = componentes_optativos.filter(nucleo=nucleo)
        return componentes_optativos.aggregate(qtd=Sum('componente__ch_qtd_creditos')).get('qtd') or 0

    def get_qtd_credito_componentes_seminarios(self, nucleo=None, periodo_letivo=None):
        componentes_seminarios = self.get_componentes_curriculares_seminario()
        if nucleo:
            componentes_seminarios = componentes_seminarios.filter(nucleo=nucleo)
        if periodo_letivo:
            componentes_seminarios = componentes_seminarios.filter(periodo_letivo=periodo_letivo)
        return componentes_seminarios.aggregate(qtd=Sum('componente__ch_qtd_creditos')).get('qtd') or 0

    def get_qtd_credito_componentes_pratica_profissional(self, nucleo=None, periodo_letivo=None):
        componentes_pratica_profissional = self.get_componentes_curriculares_pratica_profissional()
        if nucleo:
            componentes_pratica_profissional = componentes_pratica_profissional.filter(nucleo=nucleo)
        if periodo_letivo:
            componentes_pratica_profissional = componentes_pratica_profissional.filter(periodo_letivo=periodo_letivo)
        return componentes_pratica_profissional.aggregate(qtd=Sum('componente__ch_qtd_creditos')).get('qtd') or 0

    def is_ch_componentes_obrigatorios_faltando(self):
        return self.get_ch_componentes_obrigatorios_faltando() > 0

    def is_ch_componentes_obrigatorios_consistente(self):
        return self.get_ch_componentes_obrigatorios() == self.ch_componentes_obrigatorios

    def is_ch_componentes_optativos_faltando(self):
        return self.get_ch_componentes_optativos_faltando() > 0

    def is_ch_componentes_seminario_faltando(self):
        return self.get_ch_componentes_seminario_faltando() > 0

    def is_ch_componentes_pratica_profissional_faltando(self):
        return self.get_ch_componentes_pratica_profissional_faltando() > 0

    def is_ch_componentes_tcc_faltando(self):
        return self.get_ch_componentes_tcc_faltando() > 0

    def is_configuracao_atividade_academica_faltando(self):
        return self.ch_atividades_complementares > 0 and not self.configuracao_atividade_academica

    def is_ch_faltando(self):
        return (
            self.is_ch_componentes_obrigatorios_faltando()
            or self.is_ch_componentes_optativos_faltando()
            or self.is_ch_componentes_seminario_faltando()
            or self.is_ch_componentes_pratica_profissional_faltando()
            or self.is_ch_componentes_tcc_faltando()
            or self.is_configuracao_atividade_academica_faltando()
        )

    # CAMPUS COM CURSOS CONTENDO A MATRIZ

    def get_uos(self):
        ids = set(self.cursocampus_set.all().filter(ativo=True).values_list('diretoria__setor__uo__id', flat=True))
        return UnidadeOrganizacional.objects.suap().filter(id__in=ids)

    def get_diretorias(self):
        ids = set(self.cursocampus_set.all().filter(ativo=True).values_list('diretoria__id', flat=True))
        return Diretoria.objects.filter(id__in=ids)

    def verificar_inconsistencias(self):
        retorno = False

        if self.is_ch_faltando() or not self.is_ch_componentes_obrigatorios_consistente():
            self.inconsistente = True
        else:
            self.inconsistente = False

        return retorno

    def save(self, *args, **kwargs):
        self.verificar_inconsistencias()
        super().save(*args, **kwargs)


class MatrizCurso(LogModel):
    SEARCH_FIELDS = ['curso_campus__descricao', 'curso_campus__codigo', 'matriz__pk']
    # Manager
    objects = models.Manager()
    locals = FiltroDiretoriaManager('curso_campus__diretoria')

    # Fields
    curso_campus = models.ForeignKeyPlus('edu.CursoCampus', on_delete=models.CASCADE, verbose_name='Curso')
    matriz = models.ForeignKeyPlus('edu.Matriz', on_delete=models.CASCADE, verbose_name='Matriz')

    # Ato normativo
    resolucao_criacao = models.TextField('Documento de Criação', blank=True, null=True)
    resolucao_data = models.DateFieldPlus('Data de Criação', null=True, blank=True)

    # Ato de reconhecimento
    reconhecimento_texto = models.TextField('Descrição', blank=True, null=True)
    reconhecimento_data = models.DateFieldPlus('Data', null=True, blank=True)

    search = models.SearchField(attrs=['curso_campus', 'matriz'])

    class Meta:
        verbose_name = 'Vínculo de Matriz em Curso'
        verbose_name_plural = 'Vínculos de Matriz em Curso'
        unique_together = ('matriz', 'curso_campus')

    def get_ext_combo_template(self):
        return '<p>Matriz: {} </p><p>Curso: {}</p><p> Campus: {}</p>'.format(
            self.matriz, self.curso_campus.descricao, str(self.curso_campus.diretoria and self.curso_campus.diretoria.setor.uo.nome or '-')
        )

    def get_absolute_url(self):
        return '/edu/cursocampus/{}/?tab=matrizes'.format(self.curso_campus.pk)

    def __str__(self):
        return 'Matriz: {} Curso: {} Campus: {}'.format(
            self.matriz, self.curso_campus.descricao, str(self.curso_campus.diretoria and self.curso_campus.diretoria.setor.uo.nome or '-')
        )

    def clean(self):
        if not hasattr(self, 'matriz'):
            raise ValidationError('Por favor selecione uma matriz.')
        if not self.matriz.estrutura:
            raise ValidationError('Não é possível adicionar matriz a este curso, pois o mesmo não possui Estrutura de Curso.')
        if self.matriz.estrutura.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_FREQUENCIA:
            for componente_curricular in self.matriz.componentecurricular_set.all():
                if componente_curricular.qtd_avaliacoes > 0:
                    raise ValidationError('Matrizes com componentes que requerem avaliações não podem ser vinculadas a cursos cuja estrutura de avaliação seja por frequência')

    def pode_ser_excluida(self):
        from edu.models.alunos import Aluno

        return not Aluno.objects.filter(matriz=self.matriz, curso_campus=self.curso_campus).exists()

    def delete(self, *args, **kwargs):
        if self.pode_ser_excluida():
            super().delete(*args, **kwargs)
        else:
            raise Exception('A Matriz não pode ser removida, pois existem alunos nela matriculados.')

    def get_autorizacao(self):
        result = self.autorizacao_set.order_by('-data').first()
        if result is None:
            result = self.resolucao_criacao != '' and self.resolucao_criacao or None
        return result

    def get_reconhecimento(self):
        result = None
        if self.curso_campus.modalidade.nivel_ensino_id == NivelEnsino.GRADUACAO:
            result = self.reconhecimento_set.filter(validade__gte=datetime.datetime.today()).order_by('-data').first()
        else:
            result = self.reconhecimento_set.order_by('-data').first()
        if result is None:
            result = self.reconhecimento_texto != '' and self.reconhecimento_texto or None
        return result


class Autorizacao(models.ModelPlus):
    # dados da criação
    matriz_curso = models.ForeignKeyPlus(MatrizCurso, verbose_name='Matriz Curso', on_delete=models.CASCADE)
    tipo = models.CharFieldPlus(verbose_name='Tipo', choices=[['Resolução', 'Resolução'], ['Portaria', 'Portaria'], ['Lei Federal', 'Lei Federal'], ['Deliberação', 'Deliberação']])
    data = models.DateFieldPlus(verbose_name='Data')
    numero = models.CharFieldPlus(verbose_name='Número')
    adequacao = models.BooleanField(verbose_name='Adequação', default=False)

    # dados do funcionamento
    funcionamento_tipo = models.CharFieldPlus(verbose_name='Tipo', null=True, blank=True, choices=[['Resolução', 'Resolução'], ['Portaria', 'Portaria'], ['Lei Federal', 'Lei Federal'], ['Deliberação', 'Deliberação']])
    funcionamento_data = models.DateFieldPlus(verbose_name='Data', null=True, blank=True)
    funcionamento_numero = models.CharFieldPlus(verbose_name='Número', null=True, blank=True)

    # dados da publicação
    numero_publicacao = models.CharFieldPlus(verbose_name='Seção da Publicação', null=True, blank=True)
    data_publicacao = models.DateFieldPlus(verbose_name='Data da Publicação', null=True, blank=True)
    veiculo_publicacao = models.CharFieldPlus(verbose_name='Veículo da Publicação', choices=[['DOU', 'DOU']], null=True, blank=True)
    secao_publicacao = models.CharFieldPlus(verbose_name='Seção da Publicação', null=True, blank=True)
    pagina_publicacao = models.CharFieldPlus(verbose_name='Página da Publicação', null=True, blank=True)

    class Meta:
        verbose_name = 'Autorização'
        verbose_name_plural = 'Autorizações'

    def __str__(self):
        adequacao = self.adequacao and ' (Adequação)' or ''
        publicacao = ' Publicado no DOU N° {}, seção {}, página {} em {}.'.format(
            self.numero_publicacao, self.secao_publicacao, self.pagina_publicacao, self.data_publicacao.strftime('%d/%m/%Y') if self.data_publicacao else '__/__/____'
        ) if self.veiculo_publicacao else ''
        funcionamento = ''
        if self.funcionamento_tipo:
            funcionamento = ' {} N° {} de {}.'.format(
                self.funcionamento_tipo, self.funcionamento_numero, self.funcionamento_data.strftime('%d/%m/%Y') if self.funcionamento_data else '__/__/____'
            )
        return '{} N° {} de {}.{}{}{}'.format(
            self.tipo, self.numero, self.data.strftime('%d/%m/%Y'), funcionamento, publicacao, adequacao
        )


class Reconhecimento(models.ModelPlus):
    # dados gerais
    matriz_curso = models.ForeignKeyPlus(MatrizCurso, verbose_name='Matriz Curso', on_delete=models.CASCADE)
    tipo = models.CharFieldPlus(verbose_name='Tipo', choices=[['Resolução', 'Resolução'], ['Portaria', 'Portaria'], ['Lei Federal', 'Lei Federal'], ['Deliberação', 'Deliberação']])
    data = models.DateFieldPlus(verbose_name='Data')
    numero = models.CharFieldPlus(verbose_name='Número')
    renovacao = models.BooleanField(verbose_name='Renovação', default=False)
    validade = models.DateFieldPlus(verbose_name='Validade', null=True, blank=False)

    # dados da publicação
    numero_publicao = models.CharFieldPlus(verbose_name='Número da Publicação', blank=True, null=True)
    data_publicacao = models.DateFieldPlus(verbose_name='Data da Publicação', blank=True, null=True)
    veiculo_publicacao = models.CharFieldPlus(verbose_name='Veículo da Publicação', choices=[['DOU', 'DOU']], null=True, blank=True)
    secao_publicao = models.CharFieldPlus(verbose_name='Seção da Publicação', blank=True, null=True)
    pagina_publicao = models.CharFieldPlus(verbose_name='Página da Publicação', blank=True, null=True)

    class Meta:
        verbose_name = 'Reconhecimento'
        verbose_name_plural = 'Reconhecimentos'

    def __str__(self):
        renovacao = self.renovacao and ' (Renovação)' or ''
        publicacao = ' Publicado no DOU N° {}, seção {}, página {} em {}.'.format(
            self.numero_publicao, self.secao_publicao, self.pagina_publicao, self.data_publicacao.strftime('%d/%m/%Y') if self.data_publicacao else '__/__/____'
        ) if self.veiculo_publicacao else ''
        return '{} N° {} de {}.{}{}'.format(
            self.tipo, self.numero, self.data.strftime('%d/%m/%Y'), publicacao, renovacao
        )


class AtoRegulatorio(models.ModelPlus):
    # dados gerais
    tipo_ato = models.CharFieldPlus(verbose_name='Tipo', choices=[['Credenciamento', 'Credenciamento'], ['Recredenciamento', 'Recredenciamento']])
    natureza_participacao = models.ForeignKey('edu.NaturezaParticipacao', verbose_name='Natureza de Participação', on_delete=models.CASCADE)

    # dados do documento
    tipo = models.CharFieldPlus(verbose_name='Tipo', choices=[['Resolução', 'Resolução'], ['Portaria', 'Portaria'], ['Lei', 'Lei']])
    data = models.DateFieldPlus(verbose_name='Data')
    numero = models.CharFieldPlus(verbose_name='Número')

    # dados da publicação
    numero_publicao = models.CharFieldPlus(verbose_name='Número da Publicação')
    data_publicacao = models.DateFieldPlus(verbose_name='Data da Publicação')
    pagina_publicao = models.CharFieldPlus(verbose_name='Página da Publicação')
    secao_publicao = models.CharFieldPlus(verbose_name='Seção da Publicação')

    class Meta:
        verbose_name = 'Ato Regulatório'
        verbose_name_plural = 'Atos Regulatórios'

    def __str__(self):
        return '{} - {} N° {} de {}, publicado no DOU N° {}, seção {}, página {} em {}'.format(
            self.tipo_ato,
            self.tipo,
            self.numero,
            self.data.strftime('%d/%m/%Y'),
            self.numero_publicao,
            self.secao_publicao,
            self.pagina_publicao,
            self.data_publicacao.strftime('d/%m/%Y'),
        )


class Minicurso(CursoCampus):
    objects = MinicursoObjectsManager()
    locals = MinicursoLocalsManager()

    class Meta:
        verbose_name = 'Curso FIC < 160h'
        verbose_name_plural = 'Cursos FIC < 160h'
        proxy = True

    def get_absolute_url(self):
        return '/edu/minicurso/{:d}/'.format(self.pk)

    def clean(self):
        if not self.ch_total:
            raise ValidationError({'ch_total': 'Não é possível cadastrar um minicurso sem carga horária total.'})
        if self.ch_total > 160:
            raise ValidationError({'ch_total': 'Não é possível cadastrar uma carga horária total maior que 160 horas.'})
        if self.ch_total < 1:
            raise ValidationError({'ch_total': 'Não é possível cadastrar uma carga horária total menor que 1 hora.'})

    @transaction.atomic
    def save(self, *args, **kwargs):
        if self.codigo == '' or self.codigo is None:
            minicursos_do_campus = Minicurso.objects.filter(diretoria__setor__uo=self.diretoria.setor.uo).order_by('-codigo')
            maior_codigo = minicursos_do_campus.exists() and minicursos_do_campus[0].codigo or 0
            if not maior_codigo:
                self.codigo = '0001'
            else:
                maior_codigo = str(int(maior_codigo.split('.')[0]) + 1).zfill(4)
                self.codigo = maior_codigo
            self.codigo = '{}.{}'.format(self.codigo, self.diretoria.setor.uo)

        self.ch_aula = int(self.ch_total * 60 / self.tipo_hora_aula)
        super().save(*args, **kwargs)

    def get_codigo(self):
        return self.codigo.split('.')[0]

    get_codigo.admin_order_field = 'codigo'
    get_codigo.short_description = "Código"


class ConteudoMinicurso(LogModel):
    descricao = models.CharFieldPlus('Descrição')
    ch = models.PositiveIntegerField('Carga Horária')
    minicurso = models.ForeignKeyPlus('edu.Minicurso', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Conteúdo'
        verbose_name_plural = 'Conteúdos'

    def __str__(self):
        return '({}) Conteúdo'.format(self.pk)
