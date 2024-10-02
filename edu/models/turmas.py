import datetime
from decimal import Decimal
from django.core.exceptions import ValidationError
from django.db import transaction
from django.apps import apps
from djtools.db import models
from edu import perms
from edu.managers import TurmaManager, TurmaLocalManager
from edu.models.cadastros_gerais import PERIODO_LETIVO_CHOICES, SituacaoMatricula, SituacaoMatriculaPeriodo, Turno, HorarioAula, HorarioAulaDiario
from edu.models.logs import LogModel
from edu.models.historico import MatriculaPeriodo
from django.conf import settings
from djtools.testutils import running_tests
from comum.models import User


class Turma(LogModel):
    SEARCH_FIELDS = ['codigo', 'descricao']

    # Manager
    objects = TurmaManager()
    locals = TurmaLocalManager()
    # Fields
    codigo = models.CharFieldPlus(verbose_name='Código')
    descricao = models.CharFieldPlus(verbose_name='Descrição')
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano Letivo', related_name='turma_por_ano_letivo_set', on_delete=models.CASCADE)
    periodo_letivo = models.PositiveIntegerField(verbose_name='Período Letivo', choices=PERIODO_LETIVO_CHOICES)
    periodo_matriz = models.PositiveIntegerField(verbose_name='Período Turma')
    turno = models.ForeignKeyPlus('edu.Turno', verbose_name='Turno', on_delete=models.CASCADE)
    curso_campus = models.ForeignKeyPlus('edu.CursoCampus', verbose_name='Curso')
    matriz = models.ForeignKeyPlus('edu.Matriz', null=True)
    sequencial = models.PositiveIntegerField(default=1)
    calendario_academico = models.ForeignKeyPlus('edu.CalendarioAcademico', null=True)
    quantidade_vagas = models.PositiveIntegerField('Quantidade de Vagas', default=0)
    polo = models.ForeignKeyPlus('edu.Polo', null=True, verbose_name='Polo EAD', blank=True, on_delete=models.CASCADE)
    sigla = models.CharFieldPlus(max_length=255, default='', null=True, blank=True)
    codigo_educacenso = models.CharFieldPlus('Código EDUCACENSO', null=True, blank=True)
    # plano de retomada de aulas em virtude da pandemia (COVID19)
    pertence_ao_plano_retomada = models.BooleanField(verbose_name='Plano de Retomada', default=False, help_text='Adicionada ao plano de retomada de aulas em virtude da pandemia (COVID19)')

    class Meta:
        verbose_name = 'Turma'
        verbose_name_plural = 'Turmas'

        permissions = (('gerar_turmas', 'Gerar Turmas'),)
        ordering = ('descricao',)

    def transferir(self, matriculas_periodo, turma_destino, commit=False):
        from edu.models import MatriculaDiario

        diarios = []

        for diario_origem in self.diario_set.all():
            qs_diario_destino = turma_destino.diario_set.filter(componente_curricular__componente=diario_origem.componente_curricular.componente)
            diario_destino = qs_diario_destino.exists() and qs_diario_destino[0] or None
            diarios.append((diario_origem, diario_destino))

        if commit:
            for matricula_periodo in MatriculaPeriodo.objects.filter(id__in=matriculas_periodo):
                for diario_origem, diario_destino in diarios:
                    if diario_destino:
                        for matricula_diario in MatriculaDiario.objects.filter(matricula_periodo=matricula_periodo, diario=diario_origem):
                            matricula_diario.transferir(diario_destino)
                matricula_periodo.turma = turma_destino
                matricula_periodo.save()

        return diarios

    def get_alunos_relacionados(self):
        qs = MatriculaPeriodo.objects.all()
        qs = qs.filter(matriculadiario__diario__turma=self) | qs.filter(turma=self)
        return qs.distinct().order_by('aluno__pessoa_fisica__nome', 'aluno__pk').select_related('aluno__pessoa_fisica')

    def get_alunos_matriculados(self):
        return MatriculaPeriodo.objects.filter(turma=self).order_by('aluno__pessoa_fisica__nome', 'aluno__pk').select_related('aluno__pessoa_fisica')

    def get_alunos_matriculados_diarios(self):
        from edu.models import MatriculaDiario

        return (
            MatriculaPeriodo.objects.filter(matriculadiario__diario__turma=self)
            .exclude(turma=self)
            .exclude(matriculadiario__situacao=MatriculaDiario.SITUACAO_TRANSFERIDO)
            .order_by('aluno__pessoa_fisica__nome', 'aluno__pk')
            .select_related('aluno__pessoa_fisica')
            .distinct()
        )

    def get_alunos_apto_matricula(self, turno=None, ignorar_matriculados=True, apenas_ingressantes=False):

        turno = turno or self.turno
        qs = MatriculaPeriodo.objects.filter(
            aluno__situacao__id__in=[
                SituacaoMatricula.MATRICULADO,
                SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL,
                SituacaoMatricula.TRANCADO,
                SituacaoMatricula.TRANCADO_VOLUNTARIAMENTE,
                SituacaoMatricula.INTERCAMBIO,
            ],
            situacao__id__in=[SituacaoMatriculaPeriodo.MATRICULADO, SituacaoMatriculaPeriodo.EM_ABERTO],
            ano_letivo=self.ano_letivo,
            periodo_letivo=self.periodo_letivo,
            aluno__periodo_atual=self.periodo_matriz,
            aluno__turno=turno,
            aluno__curso_campus=self.curso_campus,
            aluno__matriz__isnull=False,
        )
        if ignorar_matriculados:
            qs = qs.filter(turma__isnull=True)

        if apenas_ingressantes:
            qs = qs.filter(
                aluno__ano_letivo=self.ano_letivo,
                aluno__periodo_letivo=self.periodo_letivo,
                aluno__data_integralizacao__isnull=True,
                aluno__matriz__estrutura__proitec=False,
            )
        return qs

    @transaction.atomic
    def matricular_alunos(self, matriculas_periodo):
        from edu.models import MatriculaDiario

        matriculas_periodo.update(turma=self, situacao=SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO))
        for matricula_periodo in matriculas_periodo:
            diarios = self.diario_set.all().exclude(componente_curricular__componente_id__in=matricula_periodo.aluno.get_ids_componentes_cumpridos()).order_by('componente_curricular__componente_id').distinct('componente_curricular__componente_id')
            for diario in diarios:
                if matricula_periodo.aluno.pode_ser_matriculado_no_diario(diario)[0]:
                    MatriculaDiario.objects.get_or_create(matricula_periodo=matricula_periodo, diario=diario)
            if not matricula_periodo.aluno.situacao.pk == SituacaoMatricula.MATRICULADO:
                matricula_periodo.aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
                matricula_periodo.aluno.save()
            if not matricula_periodo.situacao == SituacaoMatriculaPeriodo.MATRICULADO:
                matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
                matricula_periodo.save()

    def remover_alunos(self, matriculas_periodo, user):
        from edu.models import EstruturaCurso, MatriculaDiario

        for matricula_periodo in matriculas_periodo:
            if matricula_periodo.pode_remover_da_turma(user):
                if matricula_periodo.aluno.matriz.estrutura.tipo_avaliacao != EstruturaCurso.TIPO_AVALIACAO_CREDITO:
                    for md in matricula_periodo.matriculadiario_set.filter(diario__turma=self, situacao=MatriculaDiario.SITUACAO_CURSANDO):
                        if md.pode_ser_excluido_do_diario(user):
                            md.delete()
                matricula_periodo.turma = None
                matricula_periodo.save()

                if not matricula_periodo.matriculadiario_set.count():
                    matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.EM_ABERTO)
                    matricula_periodo.save()
                    matricula_periodo.aluno.atualizar_situacao('Remoção de Turma')

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
        return '/edu/turma/{:d}/'.format(self.pk)

    def save(self, *args, **kwargs):
        self.codigo = '{}{}.{}.{}.{}{}'.format(self.ano_letivo.ano, self.periodo_letivo, self.periodo_matriz, self.curso_campus.codigo, self.sequencial, self.turno.descricao[0])
        self.descricao = '{}, {}, {}º Período, Turno {} ({})'.format(
            self.curso_campus.descricao_historico, self.curso_campus.modalidade.descricao, self.periodo_matriz, self.turno.descricao, self.ano_letivo.ano
        )
        for diario in self.diario_set.all():
            diario.calendario_academico = self.calendario_academico
            diario.save()
        super(self.__class__, self).save(*args, **kwargs)

    def get_calendario_academico(self):
        if self.diario_set.exists():
            return self.diario_set.all()[0].calendario_academico
        else:
            return None

    def pode_ser_excluido(self):
        from edu.models import MatriculaDiario

        return not (MatriculaPeriodo.objects.filter(turma=self).exists() or MatriculaDiario.objects.filter(diario__turma=self).exists())

    @staticmethod
    @transaction.atomic
    def gerar_turmas(
        ano_letivo, periodo_letivo, turnos_dict, numero_vagas_dict, numero_turmas_dict, curso_campus, matriz, horario_campus, calendario_academico, componentes, pertence_ao_plano_retomada, commit
    ):
        from edu.models import Diario

        todas_turmas = []
        lista_diarios_geral = []

        periodos = []
        for periodo_matriz in list(numero_turmas_dict.keys()):
            if numero_turmas_dict[periodo_matriz]:
                periodos.append(periodo_matriz)

        sid = transaction.savepoint()

        for periodo_matriz in periodos:

            turma_params = dict(
                ano_letivo=ano_letivo, periodo_letivo=periodo_letivo, periodo_matriz=periodo_matriz, turno=turnos_dict[periodo_matriz], curso_campus=curso_campus, matriz=matriz
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
                turma_params.update(calendario_academico=calendario_academico, sequencial=ultimo_sequencial, quantidade_vagas=numero_vagas_dict[periodo_matriz], pertence_ao_plano_retomada=pertence_ao_plano_retomada)
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
                        horario_campus=horario_campus,
                        turno=turma.turno,
                        estrutura_curso=turma.matriz.estrutura,
                        calendario_academico=calendario_academico,
                    )
                    diario_set = Diario.locals.filter(**dict_diario)
                    if diario_set.count() > 0:
                        diario = diario_set[0]
                        diario.criado = False
                    else:
                        dict_diario.update(quantidade_vagas=numero_vagas_dict[periodo_matriz])
                        dict_diario.update(segundo_semestre=componente_curricular.segundo_semestre)
                        diario = Diario(**dict_diario)
                        diario.criado = True
                        lista_diarios.append(diario)
                    turma.diarios.append(diario)

                lista_diarios_geral += lista_diarios

        if commit:
            for turma in todas_turmas:
                for diario in turma.diarios:
                    diario.save()
            transaction.savepoint_commit(sid)
        else:
            transaction.savepoint_rollback(sid)

        return todas_turmas

    def get_horarios(self, semestre='1'):
        turnos = Turno.objects.all()
        turnos.vazio = True
        for turno in turnos:
            turno.vazio = True
            horarios = HorarioAula.objects.filter(horarioauladiario__diario__in=self.diario_set.all(), turno=turno).distinct()
            if horarios:
                turno.vazio = False
                turnos.vazio = False
            turno.horariosaulas = horarios
            diarios = self.diario_set.order_by('componente_curricular__componente')
            # excluíndo os diários semestrais em cursos anuais
            if semestre == '1':
                diarios = diarios.exclude(segundo_semestre=True)
            else:
                diarios = diarios.exclude(segundo_semestre=False, componente_curricular__qtd_avaliacoes=2)
            dias_semana = [[1, 'Segunda'], [2, 'Terça'], [3, 'Quarta'], [4, 'Quinta'], [5, 'Sexta'], [6, 'Sábado'], [7, 'Domingo']]
            for dia_semana in dias_semana:
                dia_semana.append(HorarioAulaDiario.objects.filter(dia_semana=dia_semana[0], diario__in=diarios))
            turno.dias_semana = dias_semana
        return turnos

    def delete(self):
        self.matriculaperiodo_set.update(turma=None)
        super().delete()

    def diarios_pendentes(self):
        diarios_pendentes = []
        for diario in self.diario_set.all():
            if diario.pendente():
                diarios_pendentes.append(diario)
        return diarios_pendentes

    def get_matriculas_aptas_adicao_turma(self, diario):
        return MatriculaPeriodo.objects.filter(turma=self, situacao=SituacaoMatriculaPeriodo.MATRICULADO).exclude(matriculadiario__diario=diario)

    def can_change(self, user):
        return perms.realizar_procedimentos_academicos(user, self.curso_campus)


class TurmaMinicurso(LogModel):
    descricao = models.CharFieldPlus('Descrição')
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano Letivo', on_delete=models.CASCADE)
    periodo_letivo = models.PositiveIntegerField('Período Letivo', choices=PERIODO_LETIVO_CHOICES)
    data_inicio = models.DateFieldPlus('Data de Início', null=False, blank=False)
    data_fim = models.DateFieldPlus('Data de Fim', null=False, blank=False)
    minicurso = models.ForeignKeyPlus('edu.Minicurso', null=False, blank=False, on_delete=models.CASCADE)
    participantes = models.ManyToManyField('edu.Aluno', blank=True)
    gerar_matricula = models.BooleanField('Gerar Matrícula', default=False)

    class Meta:
        verbose_name = 'Turma do Minicurso'
        verbose_name_plural = 'Turmas do Minicurso'

    def __str__(self):
        return '({}) {}'.format(self.pk, self.descricao)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        for aluno in self.participantes.all():
            if self.gerar_matricula:
                self.criar_user(aluno)
            else:
                self.revogar_acessos(aluno)

    def clean(self):
        if self.data_fim and self.data_inicio > self.data_fim:
            raise ValidationError({'data_inicio': 'A data de início deve ser maior ou igual a data de fim.'})
        ch_total = 0
        for professor_minicurso in self.professorminicurso_set.all():
            ch_total += professor_minicurso.carga_horaria or 0
        if ch_total > self.minicurso.ch_total:
            raise ValidationError('A soma das cargas-horárias dos professores não pode ultrapassar {}h.'.format(self.minicurso.ch_total))

    def adicionar_novo_aluno(self, pessoa_fisica):
        from edu.models import Aluno

        matricula = self.gerar_matricula_aluno()
        aluno = Aluno()
        pessoa_fisica.id = None
        pessoa_fisica.pk = None
        pessoa_fisica.save()
        aluno.pessoa_fisica = pessoa_fisica
        aluno.curso_campus = self.minicurso
        aluno.ano_letivo = self.ano_letivo
        aluno.periodo_letivo = self.periodo_letivo
        matricula_periodo = MatriculaPeriodo()
        if datetime.datetime.today().date() >= self.data_fim:
            aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.CONCLUIDO)
            matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.APROVADO)
        else:
            aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
            matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
        aluno.matricula = matricula
        aluno.dt_conclusao_curso = self.data_fim
        aluno.save()
        matricula_periodo.aluno = aluno
        matricula_periodo.ano_letivo = self.ano_letivo
        matricula_periodo.periodo_letivo = self.periodo_letivo
        matricula_periodo.save()
        self.participantes.add(aluno)
        if self.gerar_matricula and aluno.situacao.pk == SituacaoMatricula.MATRICULADO:
            self.criar_user(aluno)

    def gerar_matricula_aluno(self):
        from edu.models import Aluno

        ano_e_periodo = '{}{}'.format(self.ano_letivo.ano, self.periodo_letivo)
        sigla_campus = self.minicurso.diretoria.setor.uo.sigla
        codigo_minicurso = self.minicurso.codigo.split('.')[0]
        participantes_da_turma = Aluno.objects.filter(turmaminicurso__minicurso=self.minicurso, ano_letivo__ano=self.ano_letivo.ano, periodo_letivo=self.periodo_letivo).order_by(
            '-matricula'
        )
        maior_matricula = participantes_da_turma.exists() and participantes_da_turma[0].matricula or 0
        if not maior_matricula:
            codigo_aluno = '0001'
        else:
            maior_codigo = maior_matricula[len(maior_matricula) - 4: len(maior_matricula)]
            codigo_aluno = str(int(maior_codigo) + 1).zfill(4)
        return '{}{}{}{}'.format(ano_e_periodo, sigla_campus, codigo_minicurso, codigo_aluno)

    def aprovar(self, alunos):
        for aluno in alunos:
            if aluno in self.participantes.all():
                aluno.matriculaperiodo_set.all().update(situacao=SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.APROVADO))
                aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.CONCLUIDO)
                aluno.save()
                self.revogar_acessos(aluno)

    def reprovar(self, alunos):
        for aluno in alunos:
            if aluno in self.participantes.all():
                aluno.matriculaperiodo_set.all().update(situacao=SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.REPROVADO))
                aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.NAO_CONCLUIDO)
                aluno.save()
                self.revogar_acessos(aluno)

    def criar_user(self, aluno):
        if self.gerar_matricula and aluno.situacao.pk == SituacaoMatricula.MATRICULADO:
            aluno.pessoa_fisica.username = aluno.matricula
            aluno.pessoa_fisica.save()
            aluno.save()

    def revogar_acessos(self, aluno):
        from ldap_backend.models import LdapConf
        aluno.email_academico = ''  # liberando para ser utilizado novamente pelo AD
        aluno.email_google_classroom = ''  # liberando para ser utilizado novamente pelo google classroom
        aluno.save()
        if aluno.pessoa_fisica and aluno.pessoa_fisica.user:
            if not running_tests() and not settings.DEBUG:
                ldap_conf = LdapConf.get_active()
                if aluno.pessoa_fisica.username:
                    ldap_conf.sync_user(aluno.pessoa_fisica.username)

            aluno.pessoa_fisica.username = None
            aluno.pessoa_fisica.save()
            User.objects.filter(username=aluno.matricula).delete()


class MonitorMinicurso(LogModel):
    aluno = models.ForeignKeyPlus('edu.Aluno', verbose_name='Aluno')
    turma_minicurso = models.ForeignKeyPlus('edu.TurmaMinicurso', verbose_name='Turma do Minicurso')
    carga_horaria = models.PositiveIntegerField('Carga Horária', null=True)

    class Meta:
        verbose_name = 'Monitor de Minicurso'
        verbose_name_plural = 'Monitores de Minicurso'

    def __str__(self):
        return '{} - {}'.format(self.aluno.matricula, self.aluno.pessoa_fisica.nome)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.is_aluno_extensao():
            AtividadeCurricularExtensao = apps.get_model('edu', 'AtividadeCurricularExtensao')
            AtividadeCurricularExtensao.registrar(self.aluno, type(self), self.pk, self.carga_horaria, self.turma_minicurso.minicurso.descricao_historico, True)

    def is_aluno_extensao(self):
        return self.aluno.situacao_id in (SituacaoMatricula.MATRICULADO, SituacaoMatricula.MATRICULA_VINCULO_INSTITUCIONAL) and self.aluno.matriz.ch_atividades_extensao

    def delete(self, *args, **kwargs):
        if self.is_aluno_extensao():
            AtividadeCurricularExtensao = apps.get_model('edu', 'AtividadeCurricularExtensao')
            AtividadeCurricularExtensao.registrar(self.aluno, type(self), self.pk, 0, False)
        super().delete(*args, **kwargs)


class ProfessorMinicurso(LogModel):
    professor = models.ForeignKeyPlus('edu.Professor', verbose_name='Professor')
    turma_minicurso = models.ForeignKeyPlus('edu.TurmaMinicurso', verbose_name='Turma do Minicurso')
    carga_horaria = models.PositiveIntegerField('Carga horária', null=True)
    carga_horaria_semanal = models.DecimalFieldPlus('Carga horária Semanal', null=True)

    def __str__(self):
        return '{} - {}'.format(self.professor.get_matricula(), self.professor.vinculo.pessoa.nome)

    def save(self, *args, **kwargs):
        self.carga_horaria_semanal = (1.0 * self.carga_horaria or 0) / 20
        super().save(*args, **kwargs)

    def clean(self):
        ch_total = 0
        for professor_minicurso in self.turma_minicurso.professorminicurso_set.exclude(pk=self.pk):
            ch_total += professor_minicurso.carga_horaria or 0
        ch_total += self.carga_horaria or 0
        if ch_total > self.turma_minicurso.minicurso.ch_total:
            raise ValidationError('A soma das cargas-horárias dos professores não pode ultrapassar {}h.'.format(self.turma_minicurso.minicurso.ch_total))

    def get_carga_horaria_semanal_ha(self):
        return int(
            Decimal(
                round(
                    self.turma_minicurso.minicurso.tipo_hora_aula and self.carga_horaria_semanal * 60 / self.turma_minicurso.minicurso.tipo_hora_aula or self.carga_horaria_semanal,
                    0,
                )
            )
        )

    def get_carga_horaria_ha(self):
        return (
            self.turma_minicurso.minicurso.tipo_hora_aula
            and self.carga_horaria
            and self.carga_horaria * 60 / self.turma_minicurso.minicurso.tipo_hora_aula
            or self.carga_horaria
            or 0
        )
