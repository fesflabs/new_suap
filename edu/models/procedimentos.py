import datetime
from django.core.exceptions import ValidationError
from django.conf import settings
from django.db import transaction

from comum.utils import get_uo, somar_data, tl
from djtools.db import models
from djtools.templatetags.filters import in_group
from djtools.utils import send_mail
from edu.managers import AbonoFaltaManager, FiltroDiretoriaManager
from edu.models.cadastros_gerais import HorarioAula, HorarioAulaDiario, PERIODO_LETIVO_CHOICES, SituacaoMatricula, SituacaoMatriculaPeriodo, Turno
from edu.models.logs import LogModel


class ConfiguracaoPedidoMatricula(LogModel):
    id = models.AutoField(verbose_name='Código', primary_key=True)
    descricao = models.CharFieldPlus('Descrição')
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano Letivo', on_delete=models.CASCADE)
    periodo_letivo = models.PositiveIntegerField('Período Letivo', choices=PERIODO_LETIVO_CHOICES)
    data_inicio = models.DateFieldPlus('Data de Início')
    data_fim = models.DateFieldPlus('Data de Fim')
    cursos = models.ManyToManyFieldPlus('edu.CursoCampus')
    diretorias = models.ManyToManyField('edu.Diretoria')

    impedir_troca_turma = models.BooleanField(
        verbose_name='Impedir troca de turma',
        default=False,
        help_text='Marque essa opção caso deseje impedir que alunos do regime seriado possam trocar de turma dentro do seu respectivo turno.',
    )
    restringir_por_curso = models.BooleanField(
        verbose_name='Restringir por curso', default=False, help_text='Marque essa opção caso deseje impedir que os alunos se matriculem em disciplinas de outros cursos.'
    )
    requer_atualizacao_dados = models.BooleanField(
        verbose_name='Requer atualização do cadastro',
        default=False,
        help_text='Marque essa opção caso deseje que o aluno atualize seus dados cadastrais no ato do pedido de matrícula.',
    )
    requer_atualizacao_caracterizacao = models.BooleanField(
        verbose_name='Requer atualização da caracterização social',
        default=False,
        help_text='Marque essa opção caso deseje que o aluno atualize seus dados da caracterização social no ato do pedido de matrícula.',
    )
    requer_autorizacao_carteira_estudantil = models.BooleanField(
        verbose_name='Requer autorização para Emissão da Carteira de Estudante',
        default=False,
        help_text='Marque essa opção caso deseje que o aluno autorize a utilização dos seus dados pessoais para emissão da carteira de estudante digital',
    )
    permite_cancelamento_matricula_diario = models.BooleanField(
        verbose_name='Permite o cancelamento de matrículas em diário já deferidas',
        default=False,
        help_text='Marque essa opção caso o aluno possa solicitar o cancelamento de matrículas em diários nos quais ele já se encontra matriculado.',
    )

    # Managers
    objects = models.Manager()
    locals = FiltroDiretoriaManager('diretorias')

    class Meta:
        verbose_name = 'Renovação de Matrícula'
        verbose_name_plural = 'Renovações de Matrícula'

    def get_diarios_sem_horarios(self, curso=None, turma=None):
        from edu.models import Diario, ComponenteCurricular

        qs = Diario.objects.filter(turma__ano_letivo=self.ano_letivo, turma__periodo_letivo=self.periodo_letivo, turma__curso_campus__in=self.cursos.all())
        qs = qs.exclude(horarioauladiario__isnull=False)
        qs = qs.exclude(
            componente_curricular__tipo__in=[
                ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL,
                ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
                ComponenteCurricular.TIPO_SEMINARIO,
            ]
        )

        # excluindo diarios do turno EAD
        qs = qs.exclude(turno__descricao='EAD')

        if curso:
            qs = qs.filter(turma__curso_campus=curso)

        if turma:
            qs = qs.filter(turma=turma)

        return qs.order_by('turma__curso_campus__codigo', 'componente_curricular__optativo', 'componente_curricular__periodo_letivo')

    def get_absolute_url(self):
        return "/edu/configuracao_pedido_matricula/{:d}/".format(self.pk)

    def __str__(self):
        return "{} ({}.{})".format(self.descricao, self.ano_letivo, self.periodo_letivo)

    def cancelar(self):
        pedidomatricula = PedidoMatricula.objects.filter(configuracao_pedido_matricula=self)
        if not pedidomatricula.exists():
            raise ValidationError('Não há pedidos de matrícula.')
        pedidomatriculadiario = PedidoMatriculaDiario.objects.filter(pedido_matricula__in=pedidomatricula)
        if not pedidomatriculadiario.exists():
            raise ValidationError('Não há pedidos de matrícula com diários.')
        pedidomatriculadiario.update(deferido=False, data_processamento=datetime.date.today(), motivo=PedidoMatriculaDiario.MOTIVO_CANCELADO)

    def desfazer_cancelamento(self):
        PedidoMatriculaDiario.objects.filter(pedido_matricula__configuracao_pedido_matricula=self).update(deferido=False, data_processamento=None, motivo=None)

    def possui_pedido_diario(self):
        return PedidoMatriculaDiario.objects.filter(pedido_matricula__configuracao_pedido_matricula=self).exists()

    def is_cancelado(self):
        return PedidoMatriculaDiario.objects.filter(pedido_matricula__configuracao_pedido_matricula=self, motivo=PedidoMatriculaDiario.MOTIVO_CANCELADO).exists()

    def pode_ser_alterado(self):
        return self.data_fim >= datetime.date.today()

    def pode_processar(self):
        return self.data_fim < datetime.date.today() and not self.is_processado()

    def is_processado(self):
        return (
            self.pedidomatricula_set.filter(pedidomatriculadiario__data_processamento__isnull=False)
            .exclude(pedidomatriculadiario__motivo=PedidoMatriculaDiario.MOTIVO_CANCELADO)
            .exists()
        )

    def get_qtd_matriculas_vinculo(self):
        try:
            if self.pedidomatricula_set.filter(pedidomatriculadiario__isnull=True)[0].matricula_periodo.situacao.pk == SituacaoMatriculaPeriodo.MATRICULADO:
                return self.pedidomatricula_set.filter(pedidomatriculadiario__isnull=True).count()
        except Exception:
            pass
        return 0

    def get_matriculas_diario_deferidas(self):
        return PedidoMatriculaDiario.objects.filter(pedido_matricula__configuracao_pedido_matricula=self, deferido=True, data_processamento__isnull=False)

    def get_matriculas_diario_indeferidas(self):
        return PedidoMatriculaDiario.objects.filter(pedido_matricula__configuracao_pedido_matricula=self, deferido=False, data_processamento__isnull=False)

    def pode_ser_excluido(self):
        if self.get_qtd_matriculas_vinculo() or self.get_matriculas_diario_deferidas() or self.get_matriculas_diario_indeferidas():
            return False
        return True

    def get_cursos(self, curso_campus_id=None):
        lista = []
        for curso_campus in self.cursos.all():
            # quantidade de alunos
            curso_campus.qtd_alunos_aptos = self.get_alunos_aptos(curso_campus).count()
            curso_campus.qtd_alunos_participantes = self.get_alunos_participantes(curso_campus).count()
            curso_campus.qtd_alunos_nao_participantes = curso_campus.qtd_alunos_aptos - curso_campus.qtd_alunos_participantes
            percentual_alunos_participantes = round(curso_campus.qtd_alunos_participantes * 100.0 / float(curso_campus.qtd_alunos_aptos), 2) if curso_campus.qtd_alunos_aptos else 0
            curso_campus.percentual_alunos_participantes = percentual_alunos_participantes > 100 and 100 or percentual_alunos_participantes
            lista.append(curso_campus)
        return lista

    def get_alunos_aptos(self, curso=None):
        from edu.models.historico import MatriculaPeriodo

        qs_aptos = MatriculaPeriodo.objects.filter(
            aluno__matriz__isnull=False,
            ano_letivo=self.ano_letivo,
            periodo_letivo=self.periodo_letivo,
            situacao__id__in=[SituacaoMatriculaPeriodo.MATRICULADO, SituacaoMatriculaPeriodo.EM_ABERTO, SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL],
        )
        qs_aptos = qs_aptos.exclude(aluno__ano_letivo=self.ano_letivo, aluno__periodo_letivo=self.periodo_letivo)
        if curso:
            qs_aptos = qs_aptos.filter(aluno__curso_campus=curso)
        return qs_aptos.order_by("aluno__pessoa_fisica__nome")

    def get_alunos_participantes(self, curso=None):
        from edu.models import MatriculaPeriodo

        qs_participantes = MatriculaPeriodo.objects.filter(pedidomatricula__configuracao_pedido_matricula=self)
        if curso:
            qs_participantes = qs_participantes.filter(aluno__curso_campus=curso)
        return qs_participantes.order_by("aluno__pessoa_fisica__nome").distinct()

    def pode_ter_curso_removido(self, curso_campus):
        qs1 = self.pedidomatricula_set.filter(configuracao_pedido_matricula=self, turma__curso_campus=curso_campus)
        qs2 = PedidoMatriculaDiario.objects.filter(pedido_matricula__configuracao_pedido_matricula=self, diario__turma__curso_campus=curso_campus)
        return not qs1.exists() and not qs2.exists()

    def enviar_emails_alunos(self):
        titulo = '[SUAP] Pedidos de Matrícula Cancelados'
        texto = (
            '<h1>Ensino</h1>'
            '<h2>Pedidos de Matrícula Cancelados</h2>'
            '<p>Seus pedidos de matrícula para o período {}.{} foram cancelados devido a revogação do período de matrícula.</p>'
            '<p>Em breve comunicaremos um novo período. Pedimos desculpa pelos transtornos.</p>'.format(self.ano_letivo.ano, self.periodo_letivo)
        )
        emails_destino = []
        for pedido_matricula in self.pedidomatricula_set.all():
            email = pedido_matricula.matricula_periodo.aluno.pessoa_fisica.email
            email_secundario = pedido_matricula.matricula_periodo.aluno.pessoa_fisica.email_secundario

            if email:
                emails_destino.append(email)
            if email_secundario:
                emails_destino.append(email_secundario)

        send_mail(titulo, texto, settings.DEFAULT_FROM_EMAIL, emails_destino)

    def get_diarios_quantitativos(self, id_diario=None, curso=None, turma=None):
        from edu.models import Diario, ComponenteCurricular

        if id_diario:
            qs_diarios = Diario.objects.filter(id=id_diario)
        else:
            qs_diarios = Diario.objects.filter(turma__ano_letivo=self.ano_letivo, turma__periodo_letivo=self.periodo_letivo, turma__curso_campus__in=self.cursos.all())
            qs_diarios_com_pratica_profissional = qs_diarios.filter(
                componente_curricular__tipo__in=[
                    ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL,
                    ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
                    ComponenteCurricular.TIPO_SEMINARIO,
                ]
            )
            qs_diarios = qs_diarios.filter(horarioauladiario__isnull=False) | qs_diarios.filter(turno__descricao='EAD') | qs_diarios_com_pratica_profissional
            qs_diarios = qs_diarios.distinct().order_by('turma__curso_campus')

        if curso:
            qs_diarios = qs_diarios.filter(turma__curso_campus=curso)

        if turma:
            qs_diarios = qs_diarios.filter(turma=turma)

        lista_diarios_quantitativos = []
        for diario in qs_diarios:
            qs_pedidos_matricula_diario = PedidoMatriculaDiario.objects.filter(pedido_matricula__configuracao_pedido_matricula=self, diario=diario)
            qtd_matriculados = diario.matriculadiario_set.all().count()
            restantes = diario.quantidade_vagas - qtd_matriculados
            if restantes >= 0:
                restantes = '<span class="status status-success">{}</span>'.format(restantes)
            else:
                restantes = '<span class="status status-error">{}</span>'.format(restantes)
            diario_list = []
            diario_list.append(
                '<a class="btn default popup" href="/edu/visualizar_alunos_pedido_diario/{:d}/{}/">Ver Solicitantes</a><a class="btn" href="/edu/imprimir_pedido_diario_pdf/{}/{}/">Imprimir</a>'.format(
                    self.id, diario.id, self.id, diario.id
                )
            )
            diario_list.append('{}'.format(diario.turma.curso_campus.codigo))
            diario_list.append('<a href="/edu/diario/{}/" target="_blank">{}</a>'.format(diario.id, diario.id))
            diario_list.append(diario.componente_curricular)
            diario_list.append(diario.quantidade_vagas)
            diario_list.append(qtd_matriculados)
            diario_list.append(qs_pedidos_matricula_diario.count())
            diario_list.append(qs_pedidos_matricula_diario.filter(deferido=True).count())
            diario_list.append(qs_pedidos_matricula_diario.filter(deferido=False, data_processamento__isnull=False).count())
            diario_list.append(restantes)
            diario_list.append(diario.id)
            lista_diarios_quantitativos.append(diario_list)
        return lista_diarios_quantitativos

    def replicar(self, descricao, data_inicio, data_fim, impedir_troca_turma, restringir_por_curso, requer_atualizacao_dados, requer_atualizacao_caracterizacao, permite_cancelamento_matricula_diario):
        cursos = self.cursos.all()
        diretorias = self.diretorias.all()
        self.id = None
        self.descricao = descricao
        self.ano_letivo = self.ano_letivo
        self.periodo_letivo = self.periodo_letivo
        self.data_inicio = data_inicio
        self.data_fim = data_fim
        self.impedir_troca_turma = impedir_troca_turma
        self.restringir_por_curso = restringir_por_curso
        self.requer_atualizacao_dados = requer_atualizacao_dados
        self.requer_atualizacao_caracterizacao = requer_atualizacao_caracterizacao
        self.permite_cancelamento_matricula_diario = permite_cancelamento_matricula_diario
        self.clean()
        self.save()
        for curso_campus in cursos:
            self.cursos.add(curso_campus)
        for diretoria in diretorias:
            self.diretorias.add(diretoria)
        self.save()

        # validando se existe um curso em outra configuracao no periodo escolhido
        for curso in cursos:
            qs = curso.configuracaopedidomatricula_set.filter(ano_letivo=self.ano_letivo, periodo_letivo=self.periodo_letivo).exclude(pk=self.pk)
            if qs.filter(data_inicio__lte=self.data_inicio, data_fim__gte=self.data_inicio) or qs.filter(data_inicio__lte=self.data_fim, data_fim__gte=self.data_fim):
                self.delete()
                raise ValidationError('Existe uma configuração cadastrada para o curso ({}) no período inserido que impede o cadastro neste intervalo de datas.'.format(curso))

        return self

    def get_status(self):
        hoje = datetime.date.today()
        existe_pedido_processado = PedidoMatricula.objects.filter(pedidomatriculadiario__data_processamento__isnull=False, configuracao_pedido_matricula=self).exists()
        if self.is_cancelado():
            return ('Cancelado', 'status-error')
        else:
            if self.data_inicio > hoje:
                return ('Aguardando Início', 'status-info')
            elif self.data_inicio < somar_data(hoje, 1) and self.data_fim >= hoje:
                return ('Em Andamento', 'status-alert')
            elif self.data_fim < hoje and not existe_pedido_processado:
                return ('Aguardando Processamento', 'status-alert')
            elif self.data_fim < hoje and existe_pedido_processado:
                return ('Processado', 'status-success')


class PedidoMatricula(LogModel):
    matricula_periodo = models.ForeignKeyPlus('edu.MatriculaPeriodo')
    configuracao_pedido_matricula = models.ForeignKeyPlus('edu.ConfiguracaoPedidoMatricula')
    turma = models.ForeignKeyPlus('edu.Turma', null=True)
    autorizacao_carteira_estudantil = models.BooleanField(
        default=False,
        verbose_name='Autorização para Emissão da Carteira de Estudante',
        help_text='Autorizo o envio dos meus dados pessoais para o Sistema Brasileiro de Educação (SEB) para fins de emissão da carteira de estudante digital',
    )
    matriculas_diario_canceladas = models.ManyToManyFieldPlus('edu.matriculadiario', verbose_name='Matrículas em Diário Canceladas')

    class Meta:
        verbose_name = 'Pedido de Matrícula'
        verbose_name_plural = 'Pedidos de Matrícula'
        permissions = (('pode_quebrar_quantidade_minima', 'Pode quebrar quantidade mínima de disciplinas exigidas para matrícula'),)

    def get_turnos_horarios(self):
        ids_diarios = self.pedidomatriculadiario_set.all().values_list('diario__id', flat=True)
        qs_turnos = Turno.objects.filter(horarioaula__horarioauladiario__diario__id__in=ids_diarios).distinct()
        turnos = []
        for turno in qs_turnos:
            turno.horarios_aula = HorarioAula.objects.filter(
                turno=turno, horario_campus__id__in=self.pedidomatriculadiario_set.all().values_list('diario__horario_campus__id', flat=True)
            )
            turnos.append(turno)
        return turnos

    def get_horarios(self):
        from edu.models.diarios import Diario

        turnos = Turno.objects.all()
        diarios_pks = self.pedidomatriculadiario_set.all().values_list('diario__pk', flat=True)
        diarios = Diario.objects.filter(pk__in=diarios_pks).order_by('componente_curricular__componente')
        turnos.vazio = True
        for turno in turnos:
            turno.vazio = True
            horarios = HorarioAula.objects.filter(horarioauladiario__diario__in=diarios, turno=turno).distinct()
            if horarios:
                turno.vazio = False
                turnos.vazio = False
            turno.horariosaulas = horarios
            dias_semana = [[1, 'Segunda'], [2, 'Terça'], [3, 'Quarta'], [4, 'Quinta'], [5, 'Sexta'], [6, 'Sábado'], [7, 'Domingo']]
            for dia_semana in dias_semana:
                dia_semana.append(HorarioAulaDiario.objects.filter(dia_semana=dia_semana[0], diario__in=diarios))
            turno.dias_semana = dias_semana
        return turnos

    def matricular_na_turma(self):
        # alterando situacao da matrícula período para MATRICULADO e setando a turma
        matricula_periodo = self.matricula_periodo
        matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
        matricula_periodo.turma = self.turma
        matricula_periodo.save()

        # alterando a situação do aluno para MATRICULADO
        aluno = matricula_periodo.aluno
        aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)

        aluno.save()

    def __str__(self):
        if self.turma:
            return 'Pedido de matrícula do aluno {} na turma {}'.format(self.matricula_periodo.aluno.matricula, self.turma.codigo)
        return 'Pedido de matrícula do aluno {}'.format(self.matricula_periodo.aluno.matricula)


class PedidoMatriculaDiario(LogModel):
    MOTIVO_PERIODIZADO = 1
    MOTIVO_IRA = 2
    MOTIVO_PERIODO_IRA = 3
    MOTIVO_CANCELADO = 4
    MOTIVO_MATRICULA_INATIVA = 5
    MOTIVO_CHOICES = [
        [MOTIVO_PERIODIZADO, 'Periodizado'],
        [MOTIVO_IRA, 'I.R.A.'],
        [MOTIVO_PERIODO_IRA, 'Período/I.R.A.'],
        [MOTIVO_CANCELADO, 'Cancelado pela Diretoria'],
        [MOTIVO_MATRICULA_INATIVA, 'Matrícula Inativa'],
    ]

    pedido_matricula = models.ForeignKeyPlus('edu.PedidoMatricula')
    diario = models.ForeignKeyPlus('edu.Diario')
    deferido = models.BooleanField(default=False)
    data_processamento = models.DateField(null=True, verbose_name='Data de Processamento')
    motivo = models.PositiveIntegerField(choices=MOTIVO_CHOICES, null=True)

    class Meta:
        verbose_name = 'Pedido de Matrícula'
        verbose_name_plural = 'Pedidos de Matrícula'

    def __str__(self):
        return 'Pedido de matrícula do aluno {} no diário {}'.format(self.pedido_matricula.matricula_periodo.aluno.matricula, self.diario.pk)

    def get_matricula_diario(self):
        from edu.models.historico import MatriculaDiario

        qs = MatriculaDiario.objects.filter(matricula_periodo=self.pedido_matricula.matricula_periodo, diario=self.diario)
        return qs.exists() and qs[0] or None

    def matricular_no_diario(self, motivo):
        from edu.models.diarios import MatriculaDiario

        # alterando situacao da matrícula período para MATRICULADO
        matricula_periodo = self.pedido_matricula.matricula_periodo
        matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
        matricula_periodo.save()

        # alterando a situação do aluno para MATRICULADO
        aluno = matricula_periodo.aluno
        aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
        aluno.save()

        # instanciando a matrícula diário para o diário solicitado
        if not MatriculaDiario.objects.filter(matricula_periodo=matricula_periodo, diario=self.diario).exists():
            matricula_diario = MatriculaDiario()
            matricula_diario.diario = self.diario
            matricula_diario.matricula_periodo = matricula_periodo
            matricula_diario.situacao = MatriculaDiario.SITUACAO_CURSANDO
            matricula_diario.save()

        # deferindo o pedido de matrícula em diário
        self.deferido = True
        self.data_processamento = datetime.date.today()
        self.motivo = motivo
        self.save()

    def indeferir(self, motivo):
        # indeferindo o pedido de matrícula em diário
        self.deferido = False
        self.data_processamento = datetime.date.today()
        self.motivo = motivo
        self.save()


class AbonoFaltas(LogModel):
    aluno = models.ForeignKeyPlus('edu.Aluno', null=False)
    data_inicio = models.DateFieldPlus('Data de Início')
    data_fim = models.DateFieldPlus('Data de Fim')
    justificativa = models.TextField('Justificativa', null=False)
    anexo = models.FileFieldPlus('Anexo', upload_to='edu/abono_faltas/', null=True, blank=True)
    responsavel_abono = models.ForeignKeyPlus('comum.User', verbose_name='Responsável Abono', null=True)

    # Managers
    objects = models.Manager()
    locals = AbonoFaltaManager('aluno__curso_campus__diretoria')

    fieldsets = (('Dados Gerais', {'fields': (('data_inicio', 'data_fim'), 'justificativa', 'anexo')}),)

    class Meta:
        verbose_name = 'Justificativa de Falta'
        verbose_name_plural = 'Justificativas de Faltas'

    def get_nome_arquivo(self):
        return self.anexo.name.split('/')[-1]

    def clean(self):
        # UC28-RN2 - A Data de Fim deve ser maior que a Data de Início.
        if self.data_inicio and self.data_fim and self.data_fim < self.data_inicio:
            raise ValidationError('A data inicial não pode ser maior que a data final.')

        if self.data_inicio and self.data_fim and self.aluno_id:
            if AbonoFaltas.objects.filter(aluno=self.aluno, data_inicio__gte=self.data_inicio, data_fim__lte=self.data_fim).exclude(pk=self.pk).exists():
                raise ValidationError('Já existe uma justificativa de falta envolvendo o período informado.')

    def __recuperar_faltas_periodo(self, periodo_inicial, periodo_final, diarios=None):
        from edu.models.diarios import Falta

        faltas = Falta.objects.filter(aula__data__gte=periodo_inicial, aula__data__lte=periodo_final, matricula_diario__matricula_periodo__aluno=self.aluno)
        if diarios:
            faltas = faltas.filter(matricula_diario__diario__in=diarios)
        return faltas

    def __desabona_faltas(self):
        abono_atual = AbonoFaltas.objects.get(pk=self.pk)
        faltas = self.__recuperar_faltas_periodo(abono_atual.data_inicio, abono_atual.data_fim)
        for falta in faltas:
            falta.abono_faltas = None
            falta.save()

    def save(self, *args, **kwargs):
        diarios = None
        if hasattr(self, 'diarios'):
            diarios = self.diarios
        # UC28-RN3 - Ao cadastrar um abono, todas as faltas cadastradas do aluno entre a Data de Início e a Data de Fim tem seu estado alterado para abonada.
        if self.pk:
            self.__desabona_faltas()

        super().save(*args, **kwargs)

        faltas = self.__recuperar_faltas_periodo(self.data_inicio, self.data_fim, diarios)
        for falta in faltas:
            falta.abono_faltas = self
            falta.save()

    def delete(self, *args, **kwargs):
        # UC28-RN4 - Ao excluir um abono, todas as faltas cadastradas do aluno entre a Data de Início e a Data de Fim tem seu estado alterado para não abonada.
        self.__desabona_faltas()
        super().delete(*args, **kwargs)

    def get_absolute_url(self):
        return '/edu/abonofaltas/{:d}/'.format(self.pk)

    def __str__(self):
        return 'Justificativa de Falta - {}'.format(self.aluno.get_nome_social_composto())


class ProcedimentoMatricula(LogModel):
    INTERCAMBIO = 'Intercâmbio'
    TRANCAMENTO_COMPULSORIO = 'Trancamento Compulsório'
    TRANCAMENTO_VOLUNTARIO = 'Trancamento Voluntário'
    CANCELAMENTO_COMPULSORIO = 'Cancelamento Compulsório'
    CANCELAMENTO_VOLUNTARIO = 'Cancelamento Voluntário'
    CANCELAMENTO_POR_DUPLICIDADE = 'Cancelamento por Duplicidade'
    CANCELAMENTO_POR_DESLIGAMENTO = 'Cancelamento por Desligamento'
    EVASAO = 'Evasão'
    JUBILAMENTO = 'Jubilamento'
    REINTEGRACAO = 'Reintegração'
    TRANSFERENCIA_INTERCAMPUS = 'Transferência Intercampus'
    TRANSFERENCIA_CURSO = 'Transferência de Curso'
    TRANSFERENCIA_EXTERNA = 'Transferência Externa'
    MATRICULA_VINCULO = 'Matrícula Vínculo'

    tipo = models.CharFieldPlus()
    situacao_matricula_anterior = models.ForeignKeyPlus('edu.SituacaoMatricula', related_name='situacaomatriculaanterior', verbose_name='Situação de Matrícula Anterior')
    matricula_periodo = models.ForeignKeyPlus('edu.MatriculaPeriodo', verbose_name='Matrícula Período')
    motivo = models.TextField('Motivo')
    # processo = models.ForeignKeyPlus('protocolo.Processo', null=True, blank=True)
    data = models.DateFieldPlus('Data')
    user = models.CurrentUserField()
    nova_matricula = models.CharFieldPlus(blank=True)

    class Meta:
        verbose_name = 'Procedimento de Matrícula'
        verbose_name_plural = 'Procedimentos de Matrícula'

    def save(self, *args, **kwargs):
        from edu.models import EstruturaCurso

        if self.matricula_periodo.aluno.matriz.estrutura.tipo_avaliacao == EstruturaCurso.TIPO_AVALIACAO_MODULAR and self.tipo in [
            ProcedimentoMatricula.TRANCAMENTO_COMPULSORIO,
            ProcedimentoMatricula.TRANCAMENTO_VOLUNTARIO,
        ]:
            # plano de retomada de aulas em virtude da pandemia (COVID19)
            if not self.matricula_periodo.matriculadiario_set.filter(diario__turma__pertence_ao_plano_retomada=True).exists():
                raise ValidationError('Não é possível realizar o trancamento de um aluno do regime modular.')

        super().save(*args, **kwargs)
        if self.tipo in [
            ProcedimentoMatricula.TRANCAMENTO_COMPULSORIO,
            ProcedimentoMatricula.TRANCAMENTO_VOLUNTARIO,
            ProcedimentoMatricula.INTERCAMBIO,
            ProcedimentoMatricula.MATRICULA_VINCULO,
        ]:
            matricula_periodo = self.matricula_periodo.instanciar_proxima_matricula_periodo()
            matricula_periodo.save()

    def get_aluno(self):
        from edu.models.alunos import Aluno

        qs_aluno = Aluno.objects.filter(matricula=self.nova_matricula)
        return self.nova_matricula and qs_aluno.exists() and qs_aluno[0] or None

    def pode_ser_desfeito(self):
        from edu.models.alunos import Aluno

        if self.tipo in [ProcedimentoMatricula.TRANSFERENCIA_INTERCAMPUS, ProcedimentoMatricula.TRANSFERENCIA_CURSO]:
            # excluindo o novo aluno criado
            aluno_novo_qs = Aluno.objects.filter(matricula=self.nova_matricula)
            if aluno_novo_qs.exists():
                return aluno_novo_qs[0].pode_ser_excluido()

        mps = self.matricula_periodo.aluno.get_matriculas_periodo()
        eh_ultimo_procedimento = self.matricula_periodo.aluno.get_ultimo_procedimento_matricula() == self
        eh_ultima_matricula_periodo = self.matricula_periodo == mps[0] or (self.matricula_periodo == mps[1] and mps[0].situacao.pk == SituacaoMatriculaPeriodo.EM_ABERTO)
        return eh_ultima_matricula_periodo and eh_ultimo_procedimento

    @transaction.atomic
    def desfazer(self):
        from edu.models.alunos import Aluno, MatriculaDiario, MatriculaPeriodo

        if self.pode_ser_desfeito():
            if self.tipo == ProcedimentoMatricula.REINTEGRACAO:
                self.matricula_periodo.aluno.situacao = self.situacao_matricula_anterior
                self.matricula_periodo.aluno.save()
                self.matricula_periodo.delete()
            else:
                if self.tipo in [ProcedimentoMatricula.TRANCAMENTO_COMPULSORIO, ProcedimentoMatricula.TRANCAMENTO_VOLUNTARIO, ProcedimentoMatricula.MATRICULA_VINCULO]:
                    MatriculaPeriodo.objects.filter(
                        aluno=self.matricula_periodo.aluno, ano_letivo__gte=self.matricula_periodo.ano_letivo, situacao=SituacaoMatriculaPeriodo.EM_ABERTO
                    ).delete()

                if self.tipo in [
                    ProcedimentoMatricula.TRANSFERENCIA_INTERCAMPUS,
                    ProcedimentoMatricula.TRANSFERENCIA_CURSO,
                    ProcedimentoMatricula.TRANCAMENTO_VOLUNTARIO,
                    ProcedimentoMatricula.TRANSFERENCIA_EXTERNA,
                    ProcedimentoMatricula.TRANCAMENTO_COMPULSORIO,
                ]:
                    # excluindo o novo aluno criado
                    aluno_novo_qs = Aluno.objects.filter(matricula=self.nova_matricula)
                    if aluno_novo_qs.exists():
                        try:
                            aluno_novo = aluno_novo_qs[0]
                            aluno_novo.delete(desfazendo_transferencia=True)
                        except Exception:
                            return 'O procedimento não pode ser desfeito pois o aluno novo {} não pode ser excluido pois ele já tem notas ou procedimentos.'.format(
                                aluno_novo.matricula
                            )
                    if self.matricula_periodo.matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_CANCELADO).exists():
                        self.matricula_periodo.matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_CANCELADO).update(situacao=MatriculaDiario.SITUACAO_CURSANDO)

                self.matricula_periodo.aluno.situacao = self.situacao_matricula_anterior
                self.matricula_periodo.aluno.save()

                if self.tipo == ProcedimentoMatricula.EVASAO or self.tipo == ProcedimentoMatricula.MATRICULA_VINCULO:
                    self.matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.EM_ABERTO)
                else:
                    self.matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)

                is_tipo_cancelamento = self.tipo in [
                    ProcedimentoMatricula.CANCELAMENTO_COMPULSORIO,
                    ProcedimentoMatricula.CANCELAMENTO_VOLUNTARIO,
                    ProcedimentoMatricula.CANCELAMENTO_POR_DESLIGAMENTO,
                    ProcedimentoMatricula.EVASAO,
                    ProcedimentoMatricula.JUBILAMENTO,
                ]
                is_tipo_trancamento = self.tipo in [ProcedimentoMatricula.INTERCAMBIO, ProcedimentoMatricula.TRANCAMENTO_COMPULSORIO, ProcedimentoMatricula.TRANCAMENTO_VOLUNTARIO]

                if is_tipo_cancelamento and self.matricula_periodo.matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_CANCELADO).exists():
                    self.matricula_periodo.matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_CANCELADO).update(situacao=MatriculaDiario.SITUACAO_CURSANDO)
                    self.matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
                elif is_tipo_trancamento and self.matricula_periodo.matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_TRANCADO).exists():
                    self.matricula_periodo.matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_TRANCADO).update(situacao=MatriculaDiario.SITUACAO_CURSANDO)
                    self.matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)

                is_cursando_diario = self.matricula_periodo.matriculadiario_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO)
                if not is_cursando_diario:
                    self.matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.EM_ABERTO)

                self.matricula_periodo.save()
                self.matricula_periodo.excluir_proxima_matricula_periodo()

            if self.matricula_periodo.aluno.candidato_vaga_id and self.matricula_periodo.aluno.matriculaperiodo_set.count() == 1:
                from processo_seletivo.models import CandidatoVaga
                if self.tipo in (ProcedimentoMatricula.CANCELAMENTO_COMPULSORIO, ProcedimentoMatricula.CANCELAMENTO_VOLUNTARIO, ProcedimentoMatricula.EVASAO):
                    candidato_vaga = self.matricula_periodo.aluno.candidato_vaga
                    if candidato_vaga and CandidatoVaga.objects.filter(id=candidato_vaga.id, convocacao__isnull=False, eliminado=False, situacao__in=[CandidatoVaga.MATRICULA_CANCELADA, CandidatoVaga.EVADIDO, CandidatoVaga.TRANSFERIDO]):
                        if candidato_vaga.vaga is None:
                            vagas_disponiveis = candidato_vaga.oferta_vaga.get_vagas_disponiveis()
                            candidato_vaga.vaga = len(vagas_disponiveis) > 0 and vagas_disponiveis[0] or None
                        if candidato_vaga.vaga is None:
                            raise ValidationError('Não é possível desfazer este procedimento. Não há oferta de vaga disponível.')
                        candidato_vaga.situacao = CandidatoVaga.MATRICULADO
                        candidato_vaga.save()
            self.delete()
        else:
            raise ValidationError('Não é possível desfazer este procedimento.')


class Requerimento(models.ModelPlus):
    MUDANCA_TURNO = 1  # Mudança de Turno
    MUDANCA_CURSO = 2  # Mudança de Curso
    MUDANCA_TURMA = 3  # Mudança de Turma

    JUSTIFICATIVA_FALTA = 5  # Justificativa de Falta

    LANCAMENTO = 6  # Lançamento ou Revisão de Faltas/Notas/Situação
    RENOVACAO_MATRICULA = 7  # Renovação / Reabertura de Matrícula

    TRANCAMENTO_MATRICULA = 8  # Trancamento de Matrícula
    CANCELAMENTO_MATRICULA = 9  # Cancelamento de Matrícula

    AFASTAMENTO = 10  # Afastamento

    LICENCA = 11  # Licença
    ATENDIMENTO_DOMICILIAR = 12  # Atendimento Domiciliar
    DISPENSA_ATIVIDADE = 13  # Dispensa de Atividades
    INCLUSAO_REMOCAO_DISCIPLINA = 14  # Inclusão/Remoção de Disciplinas
    ADEQUACAO_HORARIO = 15  # Adequação de Horários
    ESTUDO_INDIVIDUALIZADO = 16  # Estudo Individualizado

    REALIZACAO_PROVA = 17  # Realização de Trabalhos/Provas

    APROVEITAMENTO_ESTUDO = 18  # Aproveitamento de Estudos
    CERTIFICACAO_CONHECIMENTO = 19  # Certificação de Conhecimentos

    TRANCAMENTO_DISCIPLINA = 20  # Trancamento de Disciplina
    MATRICULA_DISCIPLINA = 21

    OUTRO = 100  # Outro

    TIPO_CHOICES = [
        [MUDANCA_TURNO, 'Mudança de Turno'],
        [MUDANCA_CURSO, 'Mudança de Curso'],
        [MUDANCA_TURMA, 'Mudança de Turma'],
        [JUSTIFICATIVA_FALTA, 'Justificativa de Falta'],
        [LANCAMENTO, 'Lançamento ou Revisão de Faltas/Notas/Situação'],
        [RENOVACAO_MATRICULA, 'Renovação / Reabertura de Matrícula'],
        [TRANCAMENTO_MATRICULA, 'Trancamento de Matrícula'],
        [TRANCAMENTO_DISCIPLINA, 'Cancelamento de Disciplina'],
        [MATRICULA_DISCIPLINA, 'Matrícula em Disciplina'],
        [CANCELAMENTO_MATRICULA, 'Cancelamento de Matrícula'],
        [AFASTAMENTO, 'Afastamento'],
        [LICENCA, 'Licença'],
        [ATENDIMENTO_DOMICILIAR, 'Atendimento Domiciliar'],
        [DISPENSA_ATIVIDADE, 'Dispensa de Atividades'],
        [INCLUSAO_REMOCAO_DISCIPLINA, 'Inclusão/Remoção de Disciplinas'],
        [ADEQUACAO_HORARIO, 'Adequação de Horários'],
        [ESTUDO_INDIVIDUALIZADO, 'Estudo Individualizado'],
        [REALIZACAO_PROVA, 'Realização de Trabalhos/Provas'],
        [APROVEITAMENTO_ESTUDO, 'Aproveitamento de Estudos'],
        [CERTIFICACAO_CONHECIMENTO, 'Certificação de Conhecimentos'],
        [OUTRO, 'Outro'],
    ]

    TIPO_AUTOMATIZADO_CHOICES = [
        [TRANCAMENTO_DISCIPLINA, 'Cancelamento de Disciplina'],
        [MATRICULA_DISCIPLINA, 'Matrícula em Disciplina'],
    ]

    id = models.AutoField(verbose_name='Código', primary_key=True)

    aluno = models.ForeignKeyPlus('edu.Aluno', verbose_name='Aluno')
    tipo = models.IntegerField(verbose_name='Tipo', choices=TIPO_CHOICES)
    data = models.DateField(verbose_name='Data')
    localizacao = models.CharField(verbose_name='Localização', null=True, blank=True, max_length=255)

    turno = models.ForeignKeyPlus(Turno, verbose_name='Turno', null=True, blank=True, on_delete=models.CASCADE)
    curso_campus = models.ForeignKeyPlus('edu.CursoCampus', verbose_name='Curso', null=True, blank=True)
    turma = models.ForeignKeyPlus('edu.Turma', verbose_name='Turma', null=True, blank=True, on_delete=models.CASCADE)
    diario = models.ForeignKeyPlus('edu.Diario', verbose_name='Diário', null=True, blank=True, on_delete=models.CASCADE)

    inicio = models.DateField(verbose_name='Início', null=True, blank=True)
    termino = models.DateField(verbose_name='Término', null=True, blank=True)

    descricao = models.TextField(verbose_name='Descrição/Justificativa', null=True, blank=True)

    situacao = models.CharField(
        verbose_name='Situação', null=True, blank=True, max_length=255, default='Em Andamento', choices=[['Em Andamento', 'Em Andamento'], ['Arquivado', 'Arquivado']]
    )
    observacao = models.TextField(verbose_name='Observação', null=True, blank=True)

    deferido = models.BooleanField(verbose_name='Deferido', null=True)
    atendente = models.ForeignKeyPlus('comum.User', null=True, verbose_name='Atendente')

    objects = FiltroDiretoriaManager('aluno__curso_campus__diretoria')

    class Meta:
        verbose_name = 'Requerimento'
        verbose_name_plural = 'Requerimentos'

    def __str__(self):
        return 'Requerimento #{}'.format(self.pk)

    def get_absolute_url(self):
        return '/edu/requerimento/{}/'.format(self.pk)

    def pode_ser_executado_automaticamente(self):
        for choice in Requerimento.TIPO_AUTOMATIZADO_CHOICES:
            if self.tipo == choice[0]:
                return True
        return False

    def indeferir(self, atendente):
        self.situacao = 'Arquivado'
        self.deferido = False
        self.atendente = atendente
        self.termino = datetime.date.today()
        self.save()
        self.enviar_email()

    def processar(self, atendente):
        self.situacao = 'Arquivado'
        self.deferido = True
        self.atendente = atendente
        self.termino = datetime.date.today()
        self.observacao = 'Processamento realizado'
        self.save()
        self.enviar_email()

    def can_change(self, user):
        return not self.pode_ser_executado_automaticamente()

    def sub_instance(self):
        if self.tipo == Requerimento.TRANCAMENTO_DISCIPLINA:
            requerimento = RequerimentoCancelamentoDisciplina.objects.filter(pk=self.pk).first()
        elif self.tipo == Requerimento.MATRICULA_DISCIPLINA:
            requerimento = RequerimentoMatriculaDisciplina.objects.filter(pk=self.pk).first()
        else:
            requerimento = self
        return requerimento

    def enviar_email(self):
        from edu.models import Aluno
        from edu.models import Mensagem

        if self.deferido is None:
            deferido = ' - '
        else:
            deferido = self.deferido and 'Sim' or 'Não'
        conteudo = """
Caro(a) aluno(a),

Informamos que houve movimentação no seu requerimento para {}. Para mais informações procure a secretaria acadêmica.

Situação: {}.
Deferido: {}.
Observação: {}.

""".format(
            self.get_tipo_display(), self.situacao, deferido, self.observacao or ''
        )
        mensagem = Mensagem()
        mensagem.remetente = self.atendente
        mensagem.assunto = 'Requerimento - {}'.format(self.get_tipo_display())
        mensagem.conteudo = conteudo
        mensagem.via_suap = True
        mensagem.via_email = True
        mensagem.save()
        mensagem.destinatarios.add(self.aluno.pessoa_fisica.user)
        mensagem.save()
        mensagem.enviar_emails(Aluno.objects.filter(pk=self.aluno.pk), copia_para_remetente=False)

    def get_detalhamento(self):
        return []


class RequerimentoCancelamentoDisciplina(Requerimento):
    matriculas_diario = models.ManyToManyField('edu.MatriculaDiario', verbose_name='Matrículas em Diário')

    objects = FiltroDiretoriaManager('aluno__curso_campus__diretoria')

    def processar(self, atendente):
        for matricula_diario in self.matriculas_diario.all():
            matricula_diario.cancelar()
        super().processar(atendente)

    def save(self, *args, **kwargs):
        self.tipo = Requerimento.TRANCAMENTO_DISCIPLINA
        super().save()

    def get_detalhamento(self):
        lista = [str(md.diario.componente_curricular.componente.descricao_historico) for md in self.matriculas_diario.all()]
        return [('Disciplinas', ', '.join(lista))]


class RequerimentoMatriculaDisciplina(Requerimento):

    # objects = FiltroDiretoriaManager('diario__turma__curso_campus__diretoria')

    def processar(self, atendente):
        from edu.models import Diario, MatriculaDiario

        pode_ser_matriculado, msg_validacao = self.aluno.pode_ser_matriculado_no_diario(self.diario)
        if not pode_ser_matriculado:
            raise ValidationError(msg_validacao)

        matricula_periodo = self.aluno.matriculaperiodo_set.get(
            ano_letivo=self.diario.ano_letivo,
            periodo_letivo=self.diario.periodo_letivo
        )
        ids_diarios = list(matricula_periodo.matriculadiario_set.values_list('diario__pk', flat=True))
        diarios_com_choque_horario = Diario.get_diarios_choque_horario(ids_diarios, diario_pivot=self.diario)
        if diarios_com_choque_horario:
            raise ValidationError(f"Esta matrícula causa choque de horário com os seguintes diários em que o aluno "
                                  f"está matriculado: {', '.join([str(diario) for diario in diarios_com_choque_horario])}")
        if not MatriculaDiario.objects.filter(matricula_periodo=matricula_periodo, diario=self.diario).exists():
            matricula_diario = MatriculaDiario()
            matricula_diario.diario = self.diario
            matricula_diario.matricula_periodo = matricula_periodo
            matricula_diario.situacao = MatriculaDiario.SITUACAO_CURSANDO
            matricula_diario.save()
            if not matricula_periodo.aluno.situacao.pk == SituacaoMatricula.MATRICULADO:
                matricula_periodo.aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
                matricula_periodo.aluno.save()
            if not matricula_periodo.situacao == SituacaoMatriculaPeriodo.MATRICULADO:
                matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(
                    pk=SituacaoMatriculaPeriodo.MATRICULADO)
                matricula_periodo.save()
        super().processar(atendente)

    def save(self, *args, **kwargs):
        self.tipo = Requerimento.MATRICULA_DISCIPLINA
        super().save()

    def get_detalhamento(self):
        return [('Diário', self.diario)]


class AproveitamentoComponente(LogModel):
    class Meta:
        verbose_name = 'Aproveitamento de Componente'
        verbose_name_plural = 'Aproveitamentos de Componente'

    matricula_periodo = models.ForeignKeyPlus('edu.MatriculaPeriodo')
    componente_curricular = models.ForeignKeyPlus('edu.ComponenteCurricular')

    matriculas_diario_resumidas = models.ManyToManyFieldPlus('edu.MatriculaDiarioResumida', related_name='equivalencias_set')
    matriculas_diario = models.ManyToManyFieldPlus('edu.MatriculaDiario', related_name='equivalencias_set')
    registros_historico = models.ManyToManyFieldPlus('edu.RegistroHistorico', related_name='equivalencias_set')

    def __str__(self):
        return 'Aproveitamento de Componente #{}'.format(self.id)

    def get_observacao_historico(self):
        disciplinas_equivalentes = []
        for matricula_diario_resumida in self.matriculas_diario_resumidas.all():
            disciplinas_equivalentes.append('{}'.format(matricula_diario_resumida.equivalencia_componente))
        for matricula_diario in self.matriculas_diario.all():
            disciplinas_equivalentes.append('{}'.format(matricula_diario.diario.componente_curricular.componente))
        for registro_historico in self.registros_historico.all():
            disciplinas_equivalentes.append('{}'.format(registro_historico.componente))
        sufixo = len(disciplinas_equivalentes) > 1 and 's' or ''
        return 'A disciplina {} - {} ({}H) do projeto do curso foi cursada pela{} disciplina{} equivalente{}: {}'.format(
            self.componente_curricular.componente.sigla,
            self.componente_curricular.componente.descricao_historico,
            self.componente_curricular.componente.ch_hora_relogio,
            sufixo,
            sufixo,
            sufixo,
            ', '.join(disciplinas_equivalentes),
        )


class MedidaDisciplinar(LogModel):
    aluno = models.ForeignKeyPlus('edu.Aluno', null=False, blank=False)
    tipo = models.ForeignKeyPlus('edu.TipoMedidaDisciplinar', null=False, blank=False)
    data_inicio = models.DateFieldPlus(verbose_name='Data de Início', null=False, blank=False)
    data_fim = models.DateFieldPlus(verbose_name='Data de Fim', null=True, blank=True)
    observacao = models.TextField(verbose_name='Observação', null=True, blank=True)

    class Meta:
        verbose_name = 'Medida Disciplinar'
        verbose_name_plural = 'Medidas Disciplinares'

    def __str__(self):
        return 'Medida Disciplinar #{} - {}'.format(self.id, self.aluno)

    def can_delete(self, user=None):
        if user is None:
            user = tl.get_user()
        if not self.aluno.is_cancelado():
            if in_group(user, 'Administrador Acadêmico'):
                return True
            elif get_uo():
                return in_group(user, 'Secretário Acadêmico') and self.aluno.curso_campus.diretoria.setor.uo == get_uo()
        return False


class Premiacao(LogModel):
    aluno = models.ForeignKeyPlus('edu.Aluno', null=False, blank=False)
    tipo = models.ForeignKeyPlus('edu.TipoPremiacao', null=False, blank=False)
    data = models.DateFieldPlus(verbose_name='Data', null=False, blank=False)
    observacao = models.TextField(verbose_name='Observação', null=True, blank=True)

    class Meta:
        verbose_name = 'Premiação'
        verbose_name_plural = 'Premiações'

    def __str__(self):
        return 'Premiação #{} - {}'.format(self.id, self.aluno)
