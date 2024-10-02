from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Manager

from djtools.db import models
from djtools.testutils import running_tests

from residencia.models import LogResidenciaModel, MatriculaPeriodo, SituacaoMatriculaPeriodo, SituacaoMatricula, \
    MatriculaUnidadeAprendizagemTurma, ComponenteCurricular, UnidadeAprendizagem
from suap import settings
from suap.settings_base import PERIODO_LETIVO_CHOICES


class ConfiguracaoAvaliacaoUnidadeAprendizagem(LogResidenciaModel):
    FORMA_CALCULO_SOMA_SIMPLES = 1
    FORMA_CALCULO_MEDIA_ARITMETICA = 2
    FORMA_CALCULO_MEDIA_PONDERADA = 3
    FORMA_CALCULO_MAIOR_NOTA = 4
    FORMA_CALCULO_SOMA_DIVISOR = 5
    FORMA_CALCULO_MEDIA_ATITUDINAL = 6
    FORMA_CALCULO_CHOICES = [
        [FORMA_CALCULO_MAIOR_NOTA, 'Maior Nota'],
        [FORMA_CALCULO_MEDIA_ARITMETICA, 'Média Aritmética'],
        [FORMA_CALCULO_MEDIA_PONDERADA, 'Média Ponderada'],
        [FORMA_CALCULO_SOMA_DIVISOR, 'Soma com Divisor Informado'],
        [FORMA_CALCULO_SOMA_SIMPLES, 'Soma Simples'],
        [FORMA_CALCULO_MEDIA_ATITUDINAL, 'Média Atitudinal'],
    ]

    unidadeaprendizagemturma = models.ForeignKeyPlus('residencia.UnidadeAprendizagemTurma', verbose_name='Unidade Aprendizagem Turma', null=True)
    etapa = models.IntegerField('Etapa', null=True)
    forma_calculo = models.IntegerField(choices=FORMA_CALCULO_CHOICES, default=FORMA_CALCULO_MEDIA_ARITMETICA, verbose_name='Forma de Cálculo')
    divisor = models.PositiveIntegerField('Divisor', null=True, blank=True)
    maior_nota = models.BooleanField('Ignorar Maior Nota', default=False)
    menor_nota = models.BooleanField('Ignorar Menor Nota', default=False)
    autopublicar = models.BooleanField('Autopublicar Notas', default=True, help_text='As notas das avaliacões serão exibidas aos residentes a medida que forem lançadas.')
    observacao = models.TextField('Observação', null=True, blank=True)

    class Meta:
        verbose_name = 'Configuração de Avaliação Unidade Aprendizagem'
        verbose_name_plural = 'Configurações de Avaliação Unidade Aprendizagem'

    def __str__(self):
        lista = []
        for item in self.itemconfiguracaoavaliacaounidadeaprendizagem_set.all():
            if item.peso:
                lista.append('{} - {} [{}]'.format(item.sigla, item.nota_maxima, item.peso))
            else:
                lista.append('{} - {}'.format(item.sigla, item.nota_maxima))
        return '{} ({})'.format(self.get_forma_calculo_display(), ' | '.join(lista))

    def get_absolute_url(self):
        return '/residencia/configuracao_avaliacao_unidadeaprendizagem/{:d}/'.format(self.pk)


class ItemConfiguracaoAvaliacaoUnidadeAprendizagem(LogResidenciaModel):
    TIPO_TRABALHO = 1
    TIPO_SEMINARIO = 2
    TIPO_TESTE = 3
    TIPO_PROVA = 4
    TIPO_ATIVIDADE = 5
    TIPO_EXERCICIO = 6
    TIPO_ATITUDINAL = 7
    TIPO_CHOICES = [
        [TIPO_PROVA, 'Prova'],
        [TIPO_SEMINARIO, 'Seminário'],
        [TIPO_TRABALHO, 'Trabalho'],
        [TIPO_TESTE, 'Teste'],
        [TIPO_ATIVIDADE, 'Atividade'],
        [TIPO_EXERCICIO, 'Exercício'],
        [TIPO_ATITUDINAL, 'Atitudinal'],
    ]

    configuracao_avaliacao = models.ForeignKeyPlus('residencia.ConfiguracaoAvaliacaoUnidadeAprendizagem', verbose_name='Configuração da Avaliação da Uminidade')
    tipo = models.IntegerField(choices=TIPO_CHOICES, verbose_name='Tipo da Avaliação', default=TIPO_PROVA)
    sigla = models.CharFieldPlus('Sigla', width=50)
    descricao = models.CharFieldPlus('Descrição', default='')
    data = models.DateFieldPlus('Data da Avaliação', null=True, blank=True)
    nota_maxima = models.PositiveIntegerField('Nota Máxima', default=settings.NOTA_DECIMAL and 10 or 100)
    peso = models.IntegerField('Peso', null=True, blank=True)

    class Meta:
        verbose_name = 'Item de Configuração de Avaliação'
        verbose_name_plural = 'Itens de Configuração de Avaliação'

    def __str__(self):
        return '{} {} na configuracao #{}'.format(self.get_tipo_display(), self.sigla, self.configuracao_avaliacao.pk)

    def clean(self):
        configuracao_avaliacao = self.configuracao_avaliacao
        if configuracao_avaliacao.forma_calculo == ConfiguracaoAvaliacaoUnidadeAprendizagem.FORMA_CALCULO_MEDIA_PONDERADA and self.peso and self.peso < 0:
            raise ValidationError('Deve ser informado o peso de cada item devido à forma de cálculo escolhida.')

    def get_qtd_avaliacoes_concorrentes(self):
        if self.data:
            qs_itens_avaliacao = ItemConfiguracaoAvaliacaoUnidadeAprendizagem.objects.exclude(pk=self.pk).filter(
                configuracao_avaliacao__diario__turma=self.configuracao_avaliacao.diario.turma_id, data=self.data
            )
            return qs_itens_avaliacao.count()
        return 0

    def get_tipo(self):
        if self.tipo == self.TIPO_PROVA:
            return 'Prova'
        elif self.tipo == self.TIPO_SEMINARIO:
            return 'Seminário'
        elif self.tipo == self.TIPO_TRABALHO:
            return 'Trabalho'
        elif self.tipo == self.TIPO_TESTE:
            return 'Teste'

    def get_descricao_etapa(self):
        if self.configuracao_avaliacao.etapa == 5:
            return 'Etapa Final'
        else:
            return 'Etapa {}'.format(self.configuracao_avaliacao.etapa)


class NotaAvaliacaoUnidadeAprendizagem(LogResidenciaModel):
    matricula_unidade_aprendizagem_turma = models.ForeignKeyPlus('residencia.MatriculaUnidadeAprendizagemTurma', verbose_name='Matrícula Unidade Aprendizagem Turma', on_delete=models.CASCADE)
    item_configuracao_avaliacao = models.ForeignKeyPlus('residencia.ItemConfiguracaoAvaliacaoUnidadeAprendizagem', verbose_name='Item de Configuração de Avaliação', on_delete=models.CASCADE)
    nota = models.NotaField('Nota', null=True)

    class Meta:
        verbose_name = 'Nota de Avaliação'
        verbose_name_plural = 'Notas de Avaliações'
        ordering = ('-id',)

    def __str__(self):
        return 'Nota {} do residente {} na avaliação {} do diário {}'.format(
            self.nota is None and 'não lançada' or self.nota,
            self.matricula_unidade_aprendizagem_turma.matricula_periodo.residente.matricula,
            self.item_configuracao_avaliacao.sigla,
            self.matricula_unidade_aprendizagem_turma.unidade_aprendizagem_turma.pk,
        )
#
#     def pode_exibir_nota(self):
#         diario_entregue = (
#             getattr(self.item_configuracao_avaliacao.configuracao_avaliacao.diario, 'posse_etapa_{}'.format(self.item_configuracao_avaliacao.configuracao_avaliacao.etapa))
#             == Diario.POSSE_REGISTRO_ESCOLAR
#         )
#         return diario_entregue or self.item_configuracao_avaliacao.configuracao_avaliacao.autopublicar
#
#
# class Trabalho(LogResidenciaModel):
#     diario = models.ForeignKeyPlus(Diario, verbose_name='Diário')
#     etapa = models.IntegerField(verbose_name='Etapa')
#
#     data_solicitacao = models.DateFieldPlus(verbose_name='Data da Solicitação', auto_now=True)
#     data_limite_entrega = models.DateFieldPlus(verbose_name='Data Limite', null=True, blank=True)
#     titulo = models.CharFieldPlus(verbose_name='Título')
#     descricao = models.TextField(verbose_name='Descrição')
#     arquivo = models.FileFieldPlus(verbose_name='Arquivo', upload_to='trabalhos', null=True, blank=True)
#
#     class Meta:
#         verbose_name = 'Trabalho'
#         verbose_name_plural = 'Trabalhos'
#         ordering = ('-id',)
#
#     def __str__(self):
#         return self.titulo
#
#     def pode_entregar_trabalho(self):
#         return self.data_limite_entrega is None or not (datetime.date.today() > self.data_limite_entrega)
#
#     def can_delete(self, user=None):
#         if user is None:
#             user = tl.get_user()
#         return user.pk in self.diario.professordiario_set.filter(ativo=True).values_list('professor__vinculo__user__id', flat=True)
#
#
# class EntregaTrabalho(LogResidenciaModel):
#     trabalho = models.ForeignKeyPlus(Trabalho, verbose_name='Diário', on_delete=models.CASCADE)
#     matricula_diario = models.ForeignKeyPlus(MatriculaDiario, verbose_name='Matrícula Diário', on_delete=models.CASCADE)
#     comentario = models.TextField(verbose_name='Comentário', blank=True)
#     data_entrega = models.DateTimeFieldPlus(verbose_name='Data da Entrega', auto_now=True)
#     arquivo = models.FileFieldPlus(verbose_name='Arquivo', upload_to='trabalhos_residentes')
#
#     class Meta:
#         verbose_name = 'Trabalho'
#         verbose_name_plural = 'Trabalhos'
#         ordering = ('-id',)
#
#     def __str__(self):
#         return 'Trabalho "{}" de {}'.format(self.trabalho.titulo, self.matricula_diario.matricula_periodo.residente)
#
#
# class TopicoDiscussao(LogResidenciaModel):
#     diario = models.ForeignKeyPlus(Diario, verbose_name='Diário', on_delete=models.CASCADE)
#     etapa = models.IntegerField(verbose_name='Etapa')
#     data = models.DateTimeFieldPlus(verbose_name='Data', auto_now=True)
#     user = models.ForeignKey('comum.User', verbose_name='Usuário', on_delete=models.CASCADE)
#     titulo = models.CharFieldPlus(verbose_name='Título')
#     descricao = models.TextField(verbose_name='Descrição')
#
#     class Meta:
#         verbose_name = 'Tópico'
#         verbose_name_plural = 'Tópicos'
#         ordering = ('-id',)
#
#     def __str__(self):
#         return self.titulo
#
#     def can_delete(self, user=None):
#         if user is None:
#             user = tl.get_user()
#         return user == self.user
#
#
# class RespostaDiscussao(LogResidenciaModel):
#     topico = models.ForeignKeyPlus(TopicoDiscussao, verbose_name='Tópico')
#     data = models.DateTimeFieldPlus(verbose_name='Data', auto_now=True)
#     user = models.ForeignKey('comum.User', verbose_name='Usuário', on_delete=models.CASCADE)
#     comentario = models.TextField(verbose_name='Comentário')
#
#     class Meta:
#         verbose_name = 'Resposta'
#         verbose_name_plural = 'Respostas'
#         ordering = ('-id',)
#
#     def __str__(self):
#         return 'Resposta de "{}" no tópico {}'.format(self.user, self.topico)
#
#     def can_delete(self, user=None):
#         if user is None:
#             user = tl.get_user()
#         return user == self.user

class Turma(LogResidenciaModel):
    SEARCH_FIELDS = ['codigo', 'descricao']

    # Manager
    objects = models.Manager()

    # Fields
    codigo = models.CharFieldPlus(verbose_name='Código')
    descricao = models.CharFieldPlus(verbose_name='Descrição')
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano Letivo', related_name='turma_residencia_por_ano_letivo_set', on_delete=models.CASCADE)
    periodo_letivo = models.PositiveIntegerField(verbose_name='Período Letivo', choices=PERIODO_LETIVO_CHOICES)
    periodo_matriz = models.PositiveIntegerField(verbose_name='Período Turma')
    curso_campus = models.ForeignKeyPlus('residencia.CursoResidencia', verbose_name='Curso')
    matriz = models.ForeignKeyPlus('residencia.Matriz', related_name='turma_residencia_matriz_set', null=True)
    sequencial = models.PositiveIntegerField(default=1)
    calendario_academico = models.ForeignKeyPlus('residencia.CalendarioAcademico', related_name='turma_residencia_calendario_academico_set', null=True)
    quantidade_vagas = models.PositiveIntegerField('Quantidade de Vagas', default=0)
    sigla = models.CharFieldPlus(max_length=255, default='', null=True, blank=True)

    class Meta:
        verbose_name = 'Turma'
        verbose_name_plural = 'Turmas'

        permissions = (('gerar_turmas', 'Gerar Turmas'),)
        ordering = ('descricao',)



    # def transferir(self, matriculas_periodo, turma_destino, commit=False):
    #     from residencia.models import MatriculaDiario
    #
    #     diarios = []
    #
    #     for diario_origem in self.diario_set.all():
    #         qs_diario_destino = turma_destino.diario_set.filter(componente_curricular__componente=diario_origem.componente_curricular.componente)
    #         diario_destino = qs_diario_destino.exists() and qs_diario_destino[0] or None
    #         diarios.append((diario_origem, diario_destino))
    #
    #     if commit:
    #         for matricula_periodo in MatriculaPeriodo.objects.filter(id__in=matriculas_periodo):
    #             for diario_origem, diario_destino in diarios:
    #                 if diario_destino:
    #                     for matricula_diario in MatriculaDiario.objects.filter(matricula_periodo=matricula_periodo, diario=diario_origem):
    #                         matricula_diario.transferir(diario_destino)
    #             matricula_periodo.turma = turma_destino
    #             matricula_periodo.save()
    #
    #     return diarios
    #
    # def get_alunos_relacionados(self):
    #     qs = MatriculaPeriodo.objects.all()
    #     qs = qs.filter(matriculadiario__diario__turma=self) | qs.filter(turma=self)
    #     return qs.distinct().order_by('aluno__pessoa_fisica__nome', 'aluno__pk').select_related('aluno__pessoa_fisica')
    #
    def get_residentes_matriculados(self):
        return MatriculaPeriodo.objects.filter(turma=self).order_by('residente__pessoa_fisica__nome', 'residente__pk').select_related('residente__pessoa_fisica')
    #
    # def get_alunos_matriculados_diarios(self):
    #     from residencia.models import MatriculaDiario
    #
    #     return (
    #         MatriculaPeriodo.objects.filter(matriculadiario__diario__turma=self)
    #         .exclude(turma=self)
    #         .exclude(matriculadiario__situacao=MatriculaDiario.SITUACAO_TRANSFERIDO)
    #         .order_by('aluno__pessoa_fisica__nome', 'aluno__pk')
    #         .select_related('aluno__pessoa_fisica')
    #         .distinct()
    #     )
    #
    def get_residentes_apto_matricula(self, ignorar_matriculados=True, apenas_ingressantes=False):


        qs = MatriculaPeriodo.objects.filter(
            residente__situacao__id__in=[
                SituacaoMatricula.MATRICULADO,
                SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL,
                SituacaoMatricula.TRANCADO,
                SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE,
                SituacaoMatricula.INTERCAMBIO,
            ],
            situacao__id__in=[SituacaoMatriculaPeriodo.MATRICULADO, SituacaoMatriculaPeriodo.EM_ABERTO],
            ano_letivo=self.ano_letivo,
            periodo_letivo=self.periodo_letivo,
            residente__periodo_atual=self.periodo_matriz,
            residente__curso_campus=self.curso_campus,
            residente__matriz__isnull=False,
        )
        if ignorar_matriculados:
            qs = qs.filter(turma__isnull=True)

        if apenas_ingressantes:
            qs = qs.filter(
                residente__ano_letivo=self.ano_letivo,
                residente__periodo_letivo=self.periodo_letivo,
            )
        return qs

    @transaction.atomic
    def matricular_residentes(self, matriculas_periodo):
        from residencia.models import MatriculaDiario

        matriculas_periodo.update(turma=self, situacao=SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO))
        for matricula_periodo in matriculas_periodo:
            # diarios = self.diarios_turma_residencia_set.all().exclude(componente_curricular__componente_id__in=matricula_periodo.residente.get_ids_componentes_cumpridos()).order_by('componente_curricular__componente_id').distinct('componente_curricular__componente_id')
            diarios = self.diarios_turma_residencia_set.all().order_by(
                'componente_curricular__componente_id').distinct('componente_curricular__componente_id')
            for diario in diarios:
                if matricula_periodo.residente.pode_ser_matriculado_no_diario(diario)[0]:
                    MatriculaDiario.objects.get_or_create(matricula_periodo=matricula_periodo, diario=diario)
            if not matricula_periodo.residente.situacao.pk == SituacaoMatricula.MATRICULADO:
                matricula_periodo.residente.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
                matricula_periodo.residente.save()
            if not matricula_periodo.situacao == SituacaoMatriculaPeriodo.MATRICULADO:
                matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
                matricula_periodo.save()

            unidadeaprendizagemturmas = self.unidadeaprendizagemturma_set.all()
            for unidade_aprendizagem_turma in unidadeaprendizagemturmas:
               MatriculaUnidadeAprendizagemTurma.objects.get_or_create(matricula_periodo=matricula_periodo, unidade_aprendizagem_turma=unidade_aprendizagem_turma)

    def remover_residentes(self, matriculas_periodo, user):
        from residencia.models import EstruturaCurso, MatriculaDiario

        for matricula_periodo in matriculas_periodo:
            if matricula_periodo.pode_remover_da_turma(user):
                for md in matricula_periodo.matriculas_diarios_matricula_periodo_residencia_set.filter(diario__turma=self, situacao=MatriculaDiario.SITUACAO_CURSANDO):
                    if md.pode_ser_excluido_do_diario(user):
                        md.delete()
                matricula_periodo.turma = None
                matricula_periodo.save()

                if not matricula_periodo.matriculas_diarios_matricula_periodo_residencia_set.count():
                    matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.EM_ABERTO)
                    matricula_periodo.save()
                    matricula_periodo.residente.atualizar_situacao('Remoção de Turma')

    def get_ext_combo_template(self):
        out = ['{}'.format(self)]
        out.append('<span class="disabled">{}</span>'.format(self.descricao))
        template = '''
        <div style="overflow: hidden">
            <div style="float: left">
                {}
            </div>
        </div>
        '''.format(
            '<br/>'.join(out)
        )
        return template

    def get_absolute_url(self):
        return '/residencia/turma/{:d}/'.format(self.pk)

    def save(self, *args, **kwargs):
        self.codigo = '{}.{}.{}'.format(self.ano_letivo.ano, self.periodo_matriz,
                                          self.sequencial)
        #self.descricao = '{}, {}º Ano, ({})'.format(            
            #self.curso_campus.descricao_historico, 
        self.descricao = ' {}º Ano {} ({})'.format(
            self.periodo_matriz, self.curso_campus.descricao ,self.ano_letivo.ano)
        for diario in self.diarios_turma_residencia_set.all():
            diario.calendario_academico = self.calendario_academico
            diario.save()
        super(self.__class__, self).save(*args, **kwargs)


    def get_calendario_academico(self):
        if self.diarios_turma_residencia_set.exists():
            return self.diarios_turma_residencia_set.all()[0].calendario_academico
        else:
            return None

    def pode_ser_excluido(self):
        from residencia.models import MatriculaDiario

        return not (MatriculaPeriodo.objects.filter(turma=self).exists() or MatriculaDiario.objects.filter(diario__turma=self).exists())

    @staticmethod
    @transaction.atomic
    def gerar_turmas(
        ano_letivo, periodo_letivo, numero_vagas_dict, numero_turmas_dict, curso_campus, matriz, calendario_academico, componentes, commit
    ):
        from residencia.models import Diario

        todas_turmas = []
        lista_diarios_geral = []

        periodos = []
        for periodo_matriz in list(numero_turmas_dict.keys()):
            if numero_turmas_dict[periodo_matriz]:
                periodos.append(periodo_matriz)

        sid = transaction.savepoint()

        for periodo_matriz in periodos:

            turma_params = dict(
                ano_letivo=ano_letivo, periodo_letivo=periodo_letivo, periodo_matriz=periodo_matriz, curso_campus=curso_campus, matriz=matriz
            )
            qs_turma = Turma.objects.filter(**turma_params)
            ultimo_sequencial = qs_turma.exists() and qs_turma.order_by('-sequencial')[0].sequencial or 0

            numero_turmas = numero_turmas_dict[periodo_matriz]

            turmas = []
            for turma in qs_turma.filter(calendario_academico=calendario_academico):
                turma.criada = False
                turmas.append(turma)
                todas_turmas.append(turma)

            for i in range(len(turmas), numero_turmas):
                ultimo_sequencial += 1
                turma_params.update(calendario_academico=calendario_academico, sequencial=ultimo_sequencial, quantidade_vagas=numero_vagas_dict[periodo_matriz])
                turma = Turma.objects.create(**turma_params)
                turma.criada = True
                turmas.append(turma)
                todas_turmas.append(turma)

            lista_diarios = []

            for turma in turmas:
                turma.diarios = []
                for componente_curricular in componentes.filter(periodo_letivo=periodo_matriz) | componentes.filter(periodo_letivo__isnull=True):
                    dict_diario = dict(
                        turma=turma,
                        componente_curricular=componente_curricular,
                        percentual_minimo_ch=100,
                        ano_letivo=turma.ano_letivo,
                        periodo_letivo=periodo_letivo,
                        estrutura_curso=turma.matriz.estrutura,
                        calendario_academico=calendario_academico,
                    )
                    diario_set = Diario.objects.filter(**dict_diario)
                    if diario_set.count() > 0:
                        diario = diario_set[0]
                        diario.criado = False
                    else:
                        dict_diario.update(quantidade_vagas=numero_vagas_dict[periodo_matriz])
                        diario = Diario(**dict_diario)
                        diario.criado = True
                        lista_diarios.append(diario)
                    turma.diarios.append(diario)

                lista_diarios_geral += lista_diarios

        if commit:
            for turma in todas_turmas:
                for diario in turma.diarios:
                    diario.save()

                # Criar a unidades de apredizagens
                unidade_aprendizagem__pks = set(ComponenteCurricular.objects.filter(matriz=matriz, periodo_letivo=turma.periodo_matriz).values_list(
                        'unidade_aprendizagem',flat=True))

                for unidade_aprendizagem_pk in unidade_aprendizagem__pks:

                    unidade_aprendizagem_turma = UnidadeAprendizagemTurma()
                    unidade_aprendizagem_turma.turma = turma
                    unidade_aprendizagem_turma.unidade_aprendizagem = UnidadeAprendizagem.objects.get(pk=unidade_aprendizagem_pk)
                    unidade_aprendizagem_turma.calendario_academico = calendario_academico
                    unidade_aprendizagem_turma.ano_letivo = turma.ano_letivo
                    unidade_aprendizagem_turma.periodo_letivo = turma.periodo_letivo
                    unidade_aprendizagem_turma.save()

            transaction.savepoint_commit(sid)
        else:
            transaction.savepoint_rollback(sid)

        return todas_turmas

    # def get_horarios(self, semestre='1'):
    #     turnos = Turno.objects.all()
    #     turnos.vazio = True
    #     for turno in turnos:
    #         turno.vazio = True
    #         horarios = HorarioAula.objects.filter(horarioauladiario__diario__in=self.diario_set.all(), turno=turno).distinct()
    #         if horarios:
    #             turno.vazio = False
    #             turnos.vazio = False
    #         turno.horariosaulas = horarios
    #         diarios = self.diario_set.order_by('componente_curricular__componente')
    #         # excluíndo os diários semestrais em cursos anuais
    #         if semestre == '1':
    #             diarios = diarios.exclude(segundo_semestre=True)
    #         else:
    #             diarios = diarios.exclude(segundo_semestre=False, componente_curricular__qtd_avaliacoes=2)
    #         dias_semana = [[1, 'Segunda'], [2, 'Terça'], [3, 'Quarta'], [4, 'Quinta'], [5, 'Sexta'], [6, 'Sábado'], [7, 'Domingo']]
    #         for dia_semana in dias_semana:
    #             dia_semana.append(HorarioAulaDiario.objects.filter(dia_semana=dia_semana[0], diario__in=diarios))
    #         turno.dias_semana = dias_semana
    #     return turnos

    def delete(self):
        self.matriculas_periodos_turma_residencia_set.update(turma=None)
        super().delete()
    #
    # def diarios_pendentes(self):
    #     diarios_pendentes = []
    #     for diario in self.diario_set.all():
    #         if diario.pendente():
    #             diarios_pendentes.append(diario)
    #     return diarios_pendentes

    def get_matriculas_aptas_adicao_turma(self, diario):
        return MatriculaPeriodo.objects.filter(turma=self, situacao=SituacaoMatriculaPeriodo.MATRICULADO).exclude(matriculadiario__diario=diario)

    # def can_change(self, user):
    #     return perms.realizar_procedimentos_academicos(user, self.curso_campus)


class UnidadeAprendizagemTurma(LogResidenciaModel):
    POSSE_REGISTRO = 0
    POSSE_PRECEPTOR = 1
    POSSE_CHOICES = [[POSSE_PRECEPTOR, 'Preceptor'], [POSSE_REGISTRO, 'Registro']]

    turma = models.ForeignKeyPlus('residencia.Turma', null=True, on_delete=models.SET_NULL)
    unidade_aprendizagem = models.ForeignKeyPlus('residencia.UnidadeAprendizagem', null=True, on_delete=models.SET_NULL)
    calendario_academico = models.ForeignKeyPlus('residencia.CalendarioAcademico', verbose_name='Calendário Acadêmico',
                                                 on_delete=models.CASCADE)

    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano Letivo',
                                       related_name='unidadesapredizagens_residencia_por_ano_letivo_set', on_delete=models.CASCADE, null=True, blank=True)
    periodo_letivo = models.PositiveIntegerField(verbose_name='Período Letivo', choices=PERIODO_LETIVO_CHOICES, null=True, blank=True)

    posse_etapa_1 = models.PositiveIntegerField(choices=POSSE_CHOICES, default=POSSE_PRECEPTOR)
    posse_etapa_2 = models.PositiveIntegerField(choices=POSSE_CHOICES, default=POSSE_PRECEPTOR)



    class Meta:
        ordering = ('turma', 'unidade_aprendizagem')
        verbose_name = 'Unidade Aprendizagem Turma'
        verbose_name_plural = 'Matrículas em Período'
        unique_together = ('turma', 'unidade_aprendizagem')
        permissions = (
            ('reabrir_unidadeaprendizagemturma', 'Pode reabrir Unidade aprendizagem'),
            ('lancar_nota_unidadeaprendizagemturma', 'Pode lançar nota em Unidade aprendizagem'),
            ('mudar_posse_unidadeaprendizagemturma', 'Pode mudar posse de Unidade aprendizagem'),
        )

    def get_inicio_etapa_1(self):
        if self.unidade_aprendizagem.ciclo == 1:
            inicio_etapa = self.calendario_academico.data_inicio_etapa_1
        elif self.unidade_aprendizagem.ciclo == 2:
            inicio_etapa = self.calendario_academico.data_inicio_etapa_2
        elif self.unidade_aprendizagem.ciclo == 3:
            inicio_etapa = self.calendario_academico.data_inicio_etapa_3
        else:
            inicio_etapa = self.calendario_academico.data_inicio_etapa_4
        return inicio_etapa

    def get_fim_etapa_1(self):
        if self.unidade_aprendizagem.ciclo == 1:
            fim_etapa = self.calendario_academico.data_fim_etapa_1
        elif self.unidade_aprendizagem.ciclo == 2:
            fim_etapa = self.calendario_academico.data_fim_etapa_2
        elif self.unidade_aprendizagem.ciclo == 3:
            fim_etapa = self.calendario_academico.data_fim_etapa_3
        else:
            fim_etapa = self.calendario_academico.data_fim_etapa_4
        return fim_etapa

    def get_inicio_etapa_2(self):
        if self.unidade_aprendizagem.ciclo == 1:
            inicio_etapa = self.calendario_academico.data_inicio_etapa_1
        elif self.unidade_aprendizagem.ciclo == 2:
            inicio_etapa = self.calendario_academico.data_inicio_etapa_2
        elif self.unidade_aprendizagem.ciclo == 3:
            inicio_etapa = self.calendario_academico.data_inicio_etapa_3
        else:
            inicio_etapa = self.calendario_academico.data_inicio_etapa_4
        return inicio_etapa

    def get_fim_etapa_2(self):
        if self.unidade_aprendizagem.ciclo == 1:
            fim_etapa = self.calendario_academico.data_fim_etapa_1
        elif self.unidade_aprendizagem.ciclo == 2:
            fim_etapa = self.calendario_academico.data_fim_etapa_2
        elif self.unidade_aprendizagem.ciclo == 3:
            fim_etapa = self.calendario_academico.data_fim_etapa_3
        else:
            fim_etapa = self.calendario_academico.data_fim_etapa_4
        return fim_etapa

    def em_posse_do_registro(self, etapa=None):
        retorno = True
        if etapa:
            retorno = getattr(self, 'posse_etapa_{}'.format(etapa)) == UnidadeAprendizagemTurma.POSSE_REGISTRO
        return retorno
    def get_matriculas_unidadeaprendizagemturma_por_polo(self, pk=None):
        lista = []
        qs = self.matriculas_unidadeaprendizagemturma_unidade_aprendizagem_turma_set.all()
        if qs.exists():
            if not running_tests():
                qs = qs.order_by('matricula_periodo__residente__pessoa_fisica__nome')
            lista.append(qs)

        return lista

    def configuracao_avaliacao_1(self):
        try:
            try:
                return self._configuracao_avaliacao_1
            except AttributeError:
                self._configuracao_avaliacao_1 = self.configuracaoavaliacaounidadeaprendizagem_set.get(etapa=1)
                return self._configuracao_avaliacao_1
        except ConfiguracaoAvaliacaoUnidadeAprendizagem.DoesNotExist:
            return None

    def configuracao_avaliacao_2(self):
        try:
            try:
                return self._configuracao_avaliacao_2
            except AttributeError:
                self._configuracao_avaliacao_2 = self.configuracaoavaliacaounidadeaprendizagem_set.get(etapa=2)
                return self._configuracao_avaliacao_2
        except ConfiguracaoAvaliacaoUnidadeAprendizagem.DoesNotExist:
            return None

    @transaction.atomic
    def processar_notas(self, dados):
        etapas = []
        matriculas_diario_pk = []
        # emails = []
        for key in list(dados.keys()):
            if ';' in key:
                etapa, matricula_diario_pk, item_configuracao_avaliacao = key.split(';')
                if etapa not in etapas:
                    etapas.append(etapa)
                if matricula_diario_pk not in matriculas_diario_pk:
                    matriculas_diario_pk.append(matricula_diario_pk)
                nota = dados[key].strip()
                if nota == '0':
                    nota = 0
                elif nota == '':
                    nota = None
                else:
                    nota = int(nota)
                NotaAvaliacaoUnidadeAprendizagem.objects.filter(matricula_unidade_aprendizagem_turma__id=matricula_diario_pk,
                                             item_configuracao_avaliacao=item_configuracao_avaliacao).update(nota=nota)

        for etapa in etapas:
            for matricula_diario in MatriculaUnidadeAprendizagemTurma.objects.filter(id__in=matriculas_diario_pk):
                matricula_diario.registrar_nota_etapa(etapa)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        etapas = list(range(1, self.unidade_aprendizagem.qtd_avaliacoes + 1))
        etapas = etapas and etapas or []

        for etapa in etapas:
            attr = 'configuracao_avaliacao_{}'.format(etapa)
            if not getattr(self, attr)() and not hasattr(self, 'dividindo'):
                configuracao_avaliacao = ConfiguracaoAvaliacaoUnidadeAprendizagem.objects.get(pk=1)
                item_configuracao_avaliacao = configuracao_avaliacao.itemconfiguracaoavaliacaounidadeaprendizagem_set.first()

                configuracao_avaliacao.pk = None
                configuracao_avaliacao.unidadeaprendizagemturma = self
                configuracao_avaliacao.etapa = etapa
                configuracao_avaliacao.save()

                item_configuracao_avaliacao.pk = None
                item_configuracao_avaliacao.configuracao_avaliacao = configuracao_avaliacao
                item_configuracao_avaliacao.save()

                # if self.utiliza_nota_atitudinal():
                #     configuracao_avaliacao.forma_calculo = ConfiguracaoAvaliacao.FORMA_CALCULO_MEDIA_ATITUDINAL
                #     configuracao_avaliacao.save()
                #
                #     item_configuracao_avaliacao2 = configuracao_avaliacao.itemconfiguracaoavaliacao_set.first()
                #     item_configuracao_avaliacao2.pk = None
                #     item_configuracao_avaliacao2.configuracao_avaliacao = configuracao_avaliacao
                #     item_configuracao_avaliacao2.tipo = ItemConfiguracaoAvaliacao.TIPO_ATITUDINAL
                #     item_configuracao_avaliacao2.sigla = 'AT'
                #     item_configuracao_avaliacao2.descrição = 'Atitudinal'
                #     item_configuracao_avaliacao2.save()

    def etapa_1_em_posse_do_registro(self):
        return getattr(self, 'posse_etapa_1') == UnidadeAprendizagemTurma.POSSE_REGISTRO

    def etapa_2_em_posse_do_registro(self):
        return getattr(self, 'posse_etapa_2') == UnidadeAprendizagemTurma.POSSE_REGISTRO

    def get_numero_primeira_etapa(self):
        result = '1'
        return result

    def get_numero_segunda_etapa(self):
        result = '2'
        return result

    def get_label_etapa(self, etapa):
        if etapa == 1:
            return self.get_numero_primeira_etapa()
        elif etapa == 2:
            return self.get_numero_segunda_etapa()
        elif etapa == 5:
            return 'Final'
        else:
            return etapa

    def pode_ser_excluido(self):
        return not self.matriculas_unidadeaprendizagemturma_unidade_aprendizagem_turma_set.exists()

    def get_periodo_letivo(self):
        self.periodo_letivo
