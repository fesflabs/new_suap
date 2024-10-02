import datetime

from django.core.exceptions import ValidationError

from comum.models import Ano, UsuarioGrupo
from comum.models import UsuarioGrupoSetor
from comum.utils import somar_data
from djtools.db import models
from djtools.html.calendarios import Calendario
from edu.managers import FiltroUnidadeOrganizacionalManager, DiretoriaManager
from edu.models.cadastros_gerais import SituacaoMatriculaPeriodo, PERIODO_LETIVO_CHOICES,\
    HorarioAulaDiario
from edu.models.diarios import Diario, ProfessorDiario
from edu.models.logs import LogModel
from edu.models.historico import MatriculaDiario, MatriculaPeriodo
from edu.models.procedimentos import Requerimento
from edu.models.solicitacoes import SolicitacaoRelancamentoEtapa, SolicitacaoProrrogacaoEtapa
from edu.models.turmas import Turma
from rh.models import Funcionario, Servidor


class Diretoria(LogModel):

    SEARCH_FIELDS = ['setor__uo__sigla', 'setor__sigla']

    TIPO_DIRETORIA_ACADEMICA = 1
    TIPO_DIRETORIA_ENSINO = 2
    TIPO_SISTEMICA = 3
    TIPO_CHOICES = [[TIPO_DIRETORIA_ACADEMICA, 'Diretoria Acadêmica'], [TIPO_DIRETORIA_ENSINO, 'Diretoria de Ensino'], [TIPO_SISTEMICA, 'Sistêmica']]

    setor = models.ForeignKeyPlus('rh.Setor')
    codigo_academico = models.IntegerField(null=True)
    diretor_geral = models.ForeignKeyPlus(Funcionario, related_name='diretorgeral_set', null=True, blank=True)
    diretor_geral_exercicio = models.ForeignKeyPlus(Funcionario, related_name='diretorgeralexercicio_set', null=True, blank=True)

    diretor_academico = models.ForeignKeyPlus(Funcionario, related_name='diretoracademico_set', null=True, blank=True)
    diretor_academico_exercicio = models.ForeignKeyPlus(Funcionario, related_name='diretoracademicoexercicio_set', null=True, blank=True)
    ead = models.BooleanField('Ensino a Distância?', default=False)
    tipo = models.PositiveIntegerField(verbose_name='Tipo', choices=TIPO_CHOICES, default=1)

    titulo_autoridade_maxima_masculino = models.CharFieldPlus(verbose_name='Autoridade Máxima (M)', default='Reitor', help_text='Título masculino da autoridade máxima')
    titulo_autoridade_maxima_feminino = models.CharFieldPlus(verbose_name='Autoridade Máxima (F)', default='Reitora', help_text='Título feminino da autoridade máxima')

    titulo_autoridade_uo_masculino = models.CharFieldPlus(verbose_name='Responsável pela Unidade (M)', default='Diretor Geral', help_text='Título masculino do responsável pela unidade')
    titulo_autoridade_uo_feminino = models.CharFieldPlus(verbose_name='Responsável pela Unidade (F)', default='Diretora Geral', help_text='Título feminino da responsável pela unidade')

    titulo_autoridade_diretoria_masculino = models.CharFieldPlus(verbose_name='Responsável pela Diretoria (M)', default='Diretor Acadêmico', help_text='Título masculino do responsável pela diretoria')
    titulo_autoridade_diretoria_feminino = models.CharFieldPlus(verbose_name='Responsável pela Diretoria (F)', default='Diretora Acadêmica', help_text='Título feminino da responsável pela diretoria')

    objects = models.Manager()
    locals = DiretoriaManager()

    class Meta:
        verbose_name = 'Diretoria Acadêmica'
        verbose_name_plural = 'Diretorias Acadêmicas'
        ordering = ('setor__uo__sigla',)

    def __str__(self):
        return self.setor.sigla

    def get_absolute_url(self):
        return '/edu/diretoria/{:d}/'.format(self.pk)

    def get_diretores_academicos(self):
        ids = []
        qs = UsuarioGrupo.objects.filter(group__name='Diretor Acadêmico', setores=self.setor)
        if qs.exists():
            for usuario_grupo in qs:
                ids.append(usuario_grupo.user.get_profile().funcionario.id)
        return Funcionario.objects.filter(id__in=ids)

    def get_diretores_de_ensino(self):
        ids = []
        setores = Diretoria.objects.filter(setor__uo=self.setor.uo, tipo=Diretoria.TIPO_DIRETORIA_ENSINO).values_list('setor', flat=True)
        if setores.exists():
            qs = UsuarioGrupo.objects.filter(group__name='Diretor Acadêmico', setores__in=setores)
            if qs.exists():
                for usuario_grupo in qs:
                    ids.append(usuario_grupo.user.get_profile().funcionario.id)
        return Funcionario.objects.filter(id__in=ids)

    def get_diretores_gerais(self):
        ids = []
        qs = UsuarioGrupo.objects.filter(group__name='Diretor Geral', setores=self.setor)
        if qs.exists():
            for usuario_grupo in qs:
                ids.append(usuario_grupo.user.get_profile().funcionario.id)
        return Servidor.objects.filter(id__in=ids)

    def get_reitores(self):
        ids = []
        qs = UsuarioGrupo.objects.filter(group__name='Reitor', setores=self.setor)
        if qs.exists():
            for usuario_grupo in qs:
                ids.append(usuario_grupo.user.get_profile().funcionario.id)
        return Servidor.objects.filter(id__in=ids)

    def possui_pendencias(self, ano_letivo, periodo_letivo):
        if self.get_pendencias(ano_letivo, periodo_letivo):
            return True
        else:
            return False

    def get_pendencias(self, ano_letivo, periodo_letivo, user=None):
        from edu.models import RegistroEmissaoDiploma
        from edu.models.alunos import Aluno, ComponenteCurricular
        from edu.models.arquivos import AlunoArquivo

        pendencias = []
        ano = Ano.objects.get(ano=ano_letivo)
        qs_diarios = Diario.objects.filter(turma__curso_campus__diretoria_id=self.pk)
        if user and user.groups.filter(name='Coordenador de Curso').exists():
            qs_diarios = qs_diarios.filter(turma__curso_campus__coordenador__user_id=user.id) | qs_diarios.filter(turma__curso_campus__coordenador_2__user_id=user.id)
        qs_sem_professores = qs_diarios.exclude(professordiario__id__isnull=False).filter(ano_letivo_id=ano.id, periodo_letivo=periodo_letivo)

        qs = MatriculaDiario.objects.filter(situacao__in=[MatriculaDiario.SITUACAO_CURSANDO, MatriculaDiario.SITUACAO_PROVA_FINAL])
        qs = qs.filter(diario__calendario_academico__data_fechamento_periodo__lt=datetime.datetime.now())
        qs = (
            qs.filter(diario__componente_curricular__qtd_avaliacoes__gte=1, nota_1__isnull=True)
            | qs.filter(diario__componente_curricular__qtd_avaliacoes__gte=2, nota_2__isnull=True)
            | qs.filter(diario__componente_curricular__qtd_avaliacoes__gte=4, nota_3__isnull=True)
            | qs.filter(diario__componente_curricular__qtd_avaliacoes__gte=4, nota_4__isnull=True)
        )
        qs_pendentes = qs_diarios.filter(pk__in=qs.values_list('diario', flat=True).order_by('diario')).filter(ano_letivo_id=ano.id, periodo_letivo=periodo_letivo).distinct()

        if periodo_letivo == 1:
            qs_sem_professores = qs_sem_professores.exclude(segundo_semestre=True)
        qs_solicitacoes_pendentes = (
            SolicitacaoRelancamentoEtapa.objects.filter(uo=self.setor.uo).exclude(avaliador_id__isnull=False).filter(professor_diario__diario__turma__curso_campus__diretoria_id=self.pk)
        )

        solicitacoes_prorrogacao_etapa = SolicitacaoProrrogacaoEtapa.locals.pendentes().filter(professor_diario__diario__turma__curso_campus__diretoria_id=self.pk)
        ingressantes_sem_turma = Aluno.get_ingressantes_sem_turma(ano, periodo_letivo).filter(curso_campus__diretoria_id=self.pk)
        qs_professores_diario = ProfessorDiario.objects.filter(
            diario__turma__curso_campus__diretoria_id=self.pk,
            diario__calendario_academico__data_fechamento_periodo__lte=datetime.datetime.now(),
            diario__ano_letivo_id=ano.id,
            diario__periodo_letivo=periodo_letivo,
        )
        qs1 = (
            qs_professores_diario.exclude(diario__componente_curricular__qtd_avaliacoes__in=[0, 1], diario__posse_etapa_1=Diario.POSSE_REGISTRO_ESCOLAR)
            .exclude(diario__componente_curricular__qtd_avaliacoes=2, diario__posse_etapa_1=Diario.POSSE_REGISTRO_ESCOLAR, diario__posse_etapa_2=Diario.POSSE_REGISTRO_ESCOLAR)
            .exclude(
                diario__componente_curricular__qtd_avaliacoes=4,
                diario__posse_etapa_1=Diario.POSSE_REGISTRO_ESCOLAR,
                diario__posse_etapa_2=Diario.POSSE_REGISTRO_ESCOLAR,
                diario__posse_etapa_3=Diario.POSSE_REGISTRO_ESCOLAR,
                diario__posse_etapa_4=Diario.POSSE_REGISTRO_ESCOLAR,
            )
        )
        qs2 = qs_professores_diario.filter(diario__posse_etapa_5=Diario.POSSE_PROFESSOR)
        qs_professores_diario = (qs1 | qs2).distinct()
        qtd_diarios_sem_professores = qs_sem_professores.count()
        if qtd_diarios_sem_professores:
            pendencias.append(
                {
                    'nome': 'Diários - Sem professores',
                    'quantidade': qtd_diarios_sem_professores,
                    'url': '/admin/edu/diario/?ano_letivo__id__exact={}&periodo_letivo__exact={}&tab=tab_sem_professores&turma__curso_campus__diretoria__id__exact={}'.format(
                        ano.pk, periodo_letivo, self.pk
                    ),
                }
            )

        # Diretoria EAD não possui verificação de diário sem local ou horário de aula
        if not self.ead:
            qs_sem_local_aula = qs_diarios.filter(local_aula_id__isnull=True, ano_letivo_id=ano.id, periodo_letivo=periodo_letivo)
            # plano de retomada de aulas em virtude da pandemia (COVID19)
            qs_sem_local_aula = qs_sem_local_aula.exclude(turma__pertence_ao_plano_retomada=True)
            qs_sem_local_aula = qs_sem_local_aula.exclude(
                componente_curricular__tipo__in=[
                    ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL,
                    ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
                    ComponenteCurricular.TIPO_SEMINARIO,
                ]
            )
            if periodo_letivo == 1:
                qs_sem_local_aula = qs_sem_local_aula.exclude(segundo_semestre=True)
            qtd_diarios_sem_local_aula = qs_sem_local_aula.count()
            if qtd_diarios_sem_local_aula:
                pendencias.append(
                    {
                        'nome': 'Diários - Sem local de aula',
                        'quantidade': qtd_diarios_sem_local_aula,
                        'url': '/admin/edu/diario/?ano_letivo__id__exact={}&periodo_letivo__exact={}&tab=tab_sem_local_aula&turma__curso_campus__diretoria__id__exact={}'.format(
                            ano.pk, periodo_letivo, self.pk
                        ),
                    }
                )

            ids_diarios = list(qs_diarios.filter(ano_letivo_id=ano.id, periodo_letivo=periodo_letivo).values_list('id', flat=True).distinct())
            ids_diarios_com_horarios = list(HorarioAulaDiario.objects.filter(diario_id__in=ids_diarios).values_list('diario_id', flat=True).distinct())
            ids_diarios_sem_horarios = list(set(ids_diarios) - set(ids_diarios_com_horarios))
            if ids_diarios_sem_horarios:
                qs_sem_horario_aula = qs_diarios.filter(id__in=ids_diarios_sem_horarios).exclude(
                    componente_curricular__tipo__in=[
                        ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL,
                        ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
                        ComponenteCurricular.TIPO_SEMINARIO,
                    ]
                )
                if periodo_letivo == 1:
                    qs_sem_horario_aula = qs_sem_horario_aula.exclude(segundo_semestre=True)
                qtd_diarios_sem_horario_aula = qs_sem_horario_aula.count()
                if qtd_diarios_sem_horario_aula:
                    pendencias.append(
                        {
                            'nome': 'Diários - Sem horário de aula',
                            'quantidade': qtd_diarios_sem_horario_aula,
                            'url': '/admin/edu/diario/?ano_letivo__id__exact={}&periodo_letivo__exact={}&tab=tab_sem_horario_aula&turma__curso_campus__diretoria__id__exact={}'.format(
                                ano.pk, periodo_letivo, self.pk
                            ),
                        }
                    )

        qtd_diarios_com_alunos_pendentes = qs_pendentes.count()
        if qtd_diarios_com_alunos_pendentes:
            pendencias.append(
                {
                    'nome': 'Diários - Com alunos com situação pendente',
                    'quantidade': qtd_diarios_com_alunos_pendentes,
                    'subtexto': 'Após o prazo de fechamento',
                    'url': '/admin/edu/diario/?ano_letivo__id__exact={}&periodo_letivo__exact={}&tab=tab_pendentes&turma__curso_campus__diretoria__id__exact={}'.format(
                        ano.pk, periodo_letivo, self.pk
                    ),
                }
            )

        qtd_solicitacoes = qs_solicitacoes_pendentes.count()
        if qtd_solicitacoes and (not user or user.has_perm('edu.view_solicitacaorelancamentoetapa')):
            pendencias.append(
                {
                    'nome': 'Solicitações de Relançamento de Etapa  - Pendentes',
                    'quantidade': qtd_solicitacoes,
                    'url': '/admin/edu/solicitacaorelancamentoetapa/?tab=tab_pendentes&professor_diario__diario__turma__curso_campus__diretoria__id__exact={}'.format(self.pk),
                    'subtexto': 'Não atendidas',
                }
            )

        turmas_ids = list(CalendarioAcademico.objects.filter(
            data_fechamento_periodo__lt=datetime.datetime.now(),
            ano_letivo_id=ano.id,
            periodo_letivo=periodo_letivo).distinct().values_list('turma__id', flat=True))

        qs_alunos_periodo_aberto = MatriculaPeriodo.objects.filter(
            ano_letivo_id=ano.id,
            periodo_letivo=periodo_letivo,
            situacao=SituacaoMatriculaPeriodo.MATRICULADO,
            aluno__curso_campus__diretoria_id=self.pk,
            turma_id__in=turmas_ids
        )

        qtd_alunos_periodo_aberto = qs_alunos_periodo_aberto.count()
        if qtd_alunos_periodo_aberto:
            pendencias.append(
                {
                    'nome': 'Alunos com Período Letivo não Fechado',
                    'quantidade': qtd_alunos_periodo_aberto,
                    'url': '/edu/monitoramento_fechamento_periodo/?ano_letivo={}&periodo_letivo={}&agrupamento=Curso&diretorias={}&modalidades='.format(
                        ano.pk, periodo_letivo, self.pk
                    ),
                    'subtexto': 'Após o prazo de fechamento',
                }
            )
        qs_turmas_pendentes = Turma.locals.pendentes().filter(
            ano_letivo_id=ano.id,
            periodo_letivo=periodo_letivo,
            curso_campus__diretoria_id=self.pk
        )
        qtd_turmas_pendentes = qs_turmas_pendentes.count()
        if qtd_turmas_pendentes:
            pendencias.append(
                {
                    'nome': 'Turmas com Fechamento Pendente',
                    'quantidade': qtd_turmas_pendentes,
                    'url': '/admin/edu/turma/?ano_letivo__id__exact={}&periodo_letivo__exact={}&tab=tab_pendentes&curso_campus__diretoria__id__exact={}'.format(
                        ano.pk, periodo_letivo, self.pk
                    ),
                    'subtexto': 'Após o prazo de fechamento',
                }
            )
        alunos_concluidos_dados_incompletos = Aluno.get_alunos_concluidos_dados_incompletos().filter(curso_campus__diretoria_id=self.pk).values_list('id', flat=True).distinct()
        qtd_alunos_concluidos_dados_incompletos = alunos_concluidos_dados_incompletos.count()
        if qtd_alunos_concluidos_dados_incompletos:
            pendencias.append(
                {
                    'nome': 'Alunos concluídos com dados incompletos',
                    'quantidade': qtd_alunos_concluidos_dados_incompletos,
                    'url': '/edu/alunos_dados_incompletos/',
                    'subtexto': 'Aptos para emissão de certificado/diploma',
                }
            )
        qtd_solicitacoes_prorrogacao_etapa = solicitacoes_prorrogacao_etapa.count()
        if qtd_solicitacoes_prorrogacao_etapa:
            pendencias.append(
                {
                    'nome': 'Solicitações de prorrogação de etapa',
                    'quantidade': qtd_solicitacoes_prorrogacao_etapa,
                    'url': '/admin/edu/solicitacaoprorrogacaoetapa/?tab=tab_pendentes&professor_diario__diario__turma__curso_campus__diretoria__id__exact={}'.format(self.pk),
                    'subtexto': 'Não atendidas',
                }
            )
        qtd_ingressantes_sem_turma = ingressantes_sem_turma.count()
        if qtd_ingressantes_sem_turma:
            pendencias.append(
                {
                    'nome': 'Alunos Ingressantes',
                    'quantidade': qtd_ingressantes_sem_turma,
                    'url': '/edu/acompanhamento_matricula_turma/?tab=alunos&ano_letivo={}&periodo_letivo={}&diretoria={}'.format(ano.pk, periodo_letivo, self.pk),
                    'subtexto': 'Sem turma',
                }
            )
        qtd_diarios_nao_entregues = qs_professores_diario.count()
        if qtd_diarios_nao_entregues:
            pendencias.append(
                {
                    'nome': 'Diários não-entregues',
                    'quantidade': qtd_diarios_nao_entregues,
                    'url': '/edu/monitoramento_entrega_diarios/?ano_letivo={}&periodo_letivo={}&agrupamento=Professor&diretorias={}&modalidades='.format(
                        ano.pk, periodo_letivo, self.pk
                    ),
                    'subtexto': 'Após o prazo de fechamento do período',
                }
            )

        qs_registros_emissao = RegistroEmissaoDiploma.objects.filter(
            codigo_qacademico__isnull=True, cancelado=False, aluno__curso_campus__diretoria_id=self.pk,
        )

        if user and user.groups.filter(name='Coordenador de Registros Acadêmicos').exists():
            for situacao, descricao in RegistroEmissaoDiploma.SITUACAO_CHOICES:
                if descricao.startswith('Aguardando'):
                    qtd_registros_emissao_pendente = qs_registros_emissao.filter(
                        situacao=situacao
                    ).count()
                    if qtd_registros_emissao_pendente:
                        pendencias.append(
                            dict(
                                nome='Emissão de Diploma',
                                url='/admin/edu/registroemissaodiploma/?aluno__curso_campus__diretoria__id__exact={}&situacao__exact={}'.format(self.pk, situacao),
                                quantidade=qtd_registros_emissao_pendente,
                                subtexto=descricao
                            )
                        )

        qs_requerimentos = Requerimento.objects.filter(aluno__curso_campus__diretoria=self).exclude(situacao='Arquivado')
        qtd_requerimentos = qs_requerimentos.count()
        if qtd_requerimentos:
            pendencias.append(
                {'nome': 'Requerimentos de Aluno', 'quantidade': qtd_requerimentos, 'url': '/admin/edu/requerimento/?tab=tab_em_andamento', 'subtexto': 'Em Andamento'}
            )

        qs = AlunoArquivo.objects.filter(validado__isnull=True, aluno__curso_campus__diretoria=self)
        if qs.exists():
            pendencias.append(
                {
                    'nome': 'Arquivos',
                    'quantidade': qs.count(),
                    'url': '/edu/avaliacao_documentos/{}/'.format(self.pk),
                    'subtexto': 'Não-Avaliados',
                }
            )

        return pendencias

    def is_diretoria_sistemica(self):
        return self.tipo == Diretoria.TIPO_SISTEMICA

    def is_diretoria_ensino(self):
        return self.tipo == Diretoria.TIPO_DIRETORIA_ENSINO


class CoordenadorRegistroAcademico(LogModel):
    diretoria = models.ForeignKeyPlus(Diretoria, verbose_name='Diretoria')
    servidor = models.ForeignKeyPlus('rh.Servidor', verbose_name='Servidor')
    numero_portaria = models.CharFieldPlus('Número da Portaria')
    eh_coordenador_registro = models.BooleanField('Coordenador de Registro Escolar?', default=False)
    ativo = models.BooleanField(verbose_name='Ativo', default=True)

    class Meta:
        verbose_name = 'Responsável pela Emissão do Diploma'
        verbose_name_plural = 'Responsáveis pela Emissão do Diploma'

    def __str__(self):
        return '{}'.format(self.servidor)

    def save(self, *args, **kwargs):
        from edu.forms import grupos

        super().save(*args, **kwargs)
        usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupos()['COORDENADOR_REGISTROS_ACADEMICOS'], user=self.servidor.pessoafisica.user)[0]
        UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=self.diretoria.setor)

    def delete(self, *args, **kwargs):
        from edu.forms import grupos

        usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupos()['COORDENADOR_REGISTROS_ACADEMICOS'], user=self.servidor.pessoafisica.user)[0]
        if CoordenadorRegistroAcademico.objects.filter(servidor=self.servidor).count() == 1:
            usuario_grupo.delete()
        UsuarioGrupoSetor.objects.filter(usuario_grupo=usuario_grupo, setor=self.diretoria.setor).delete()
        super().delete(*args, **kwargs)


class CoordenadorModalidade(LogModel):
    diretoria = models.ForeignKeyPlus(Diretoria, verbose_name='Diretoria')
    servidor = models.ForeignKeyPlus('rh.Servidor', verbose_name='Servidor')
    modalidades = models.ManyToManyFieldPlus('edu.Modalidade', verbose_name='Modalidades de Ensino', related_name='coordenadormodalidade_edu_set')

    class Meta:
        verbose_name = 'Coordenador de Modalidade'
        verbose_name_plural = 'Coordenadores de Modalidade'

    def __str__(self):
        return '{}'.format(self.servidor)

    def save(self, *args, **kwargs):
        from edu.forms import grupos

        super().save(*args, **kwargs)
        usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupos()['COORDENADOR_MODALIDADE'], user=self.servidor.pessoafisica.user)[0]
        UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=self.diretoria.setor)

    def delete(self, *args, **kwargs):
        from edu.forms import grupos

        usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupos()['COORDENADOR_MODALIDADE'], user=self.servidor.pessoafisica.user)[0]
        if CoordenadorModalidade.objects.filter(servidor=self.servidor).count() == 1:
            usuario_grupo.delete()
        UsuarioGrupoSetor.objects.filter(usuario_grupo=usuario_grupo, setor=self.diretoria.setor).delete()
        super().delete(*args, **kwargs)


class CalendarioAcademico(LogModel):
    SEARCH_FIELDS = ['id', 'descricao', 'uo__sigla']

    TIPO_ANUAL = 1
    TIPO_SEMESTRAL = 2
    TIPO_TEMPORARIO = 3
    TIPO_CHOICES = [[TIPO_ANUAL, 'Anual'], [TIPO_SEMESTRAL, 'Semestral'], [TIPO_TEMPORARIO, 'Livre']]

    QTD_ETAPA_1 = 1
    QTD_ETAPA_2 = 2
    QTD_ETAPA_4 = 4
    QTD_ETAPAS_CHOICES = [[QTD_ETAPA_1, 'Etapa Única'], [QTD_ETAPA_2, 'Duas Etapas'], [QTD_ETAPA_4, 'Quatro Etapas']]

    # Managers
    objects = models.Manager()
    locals = FiltroUnidadeOrganizacionalManager('uo')

    # Dados Gerais
    id = models.AutoField(verbose_name='Código', primary_key=True)
    descricao = models.CharFieldPlus(verbose_name='Descrição', width=500)
    tipo = models.PositiveIntegerField(verbose_name='Tipo', choices=TIPO_CHOICES)
    uo = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Campus', null=True, on_delete=models.CASCADE)
    diretoria = models.ForeignKeyPlus(Diretoria, verbose_name='Diretoria', null=True, blank=True, on_delete=models.CASCADE)
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano letivo', related_name='calendarios_por_ano_letivo_set', on_delete=models.CASCADE)
    periodo_letivo = models.PositiveIntegerField(verbose_name='Período letivo', choices=PERIODO_LETIVO_CHOICES)
    data_inicio = models.DateFieldPlus(verbose_name='Início das Aulas')
    data_fim = models.DateFieldPlus(verbose_name='Término das Aulas')
    data_fechamento_periodo = models.DateFieldPlus(verbose_name='Data de Fechamento do Período', help_text='Data limite para lançamento de notas/faltas pelos professores')
    eh_calendario_referencia = models.BooleanField('Calendário de Referência?', default=False)

    # Dados das Etapas
    qtd_etapas = models.PositiveIntegerField(verbose_name='Quantidade de Etapas', choices=QTD_ETAPAS_CHOICES)

    data_inicio_etapa_1 = models.DateFieldPlus(verbose_name='Início', help_text='Data de início da primeira etapa')
    data_fim_etapa_1 = models.DateFieldPlus(verbose_name='Fim', help_text='Data de encerramento da primeira etapa')

    data_inicio_etapa_2 = models.DateFieldPlus(verbose_name='Início', help_text='Data de início da segunda etapa', null=True, blank=True)
    data_fim_etapa_2 = models.DateFieldPlus(verbose_name='Fim', help_text='Data de encerramento da segunda etapa', null=True, blank=True)

    data_inicio_etapa_3 = models.DateFieldPlus(verbose_name='Início', help_text='Data de início da terceira etapa', null=True, blank=True)
    data_fim_etapa_3 = models.DateFieldPlus(verbose_name='Fim', help_text='Data de encerramento da terceira etapa', null=True, blank=True)

    data_inicio_etapa_4 = models.DateFieldPlus(verbose_name='Início', help_text='Data de início da quarta etapa', null=True, blank=True)
    data_fim_etapa_4 = models.DateFieldPlus(verbose_name='Fim', help_text='Data de encerramento da quarta etapa', null=True, blank=True)

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
        return '/edu/calendarioacademico/{:d}/'.format(self.pk)

    def __str__(self):
        return '[{}] {} - {}/{}.{}'.format(self.pk, self.descricao, self.uo.sigla, self.ano_letivo, self.periodo_letivo)

    def mensal(self):
        return self.anual(full=False)

    def anual(self, full=True, etapas=True):
        cal = Calendario()

        if etapas:
            data_inicio = self.data_inicio_etapa_1
            data_fim = self.data_fim_etapa_1
            descricao = '1ª Etapa'
            cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, 'success')

            if self.qtd_etapas > 1:
                data_inicio = self.data_inicio_etapa_2
                data_fim = self.data_fim_etapa_2
                descricao = '2ª Etapa'
                cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, 'info')

            if self.qtd_etapas > 2:
                data_inicio = self.data_inicio_etapa_3
                data_fim = self.data_fim_etapa_3
                descricao = '3ª Etapa'
                cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, 'alert')

                data_inicio = self.data_inicio_etapa_4
                data_fim = self.data_fim_etapa_4
                descricao = '4ª Etapa'
                cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, 'error')

            if self.data_inicio_espaco_pedagogico and self.data_fim_espaco_pedagogico:
                data_inicio = self.data_inicio_espaco_pedagogico
                data_fim = self.data_fim_espaco_pedagogico
                descricao = 'Espaço Pedagógico'
                cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, '')

            if self.data_inicio_certificacao and self.data_fim_certificacao:
                data_inicio = self.data_inicio_certificacao
                data_fim = self.data_fim_certificacao
                descricao = 'Período para Cert. e Aproveitamento'
                cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, '')

            if self.data_inicio_trancamento and self.data_fim_trancamento:
                data_inicio = self.data_inicio_trancamento
                data_fim = self.data_fim_trancamento
                descricao = 'Período para Trancamento'
                cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, '')

            if self.data_inicio_prova_final and self.data_fim_prova_final:
                data_inicio = self.data_inicio_prova_final
                data_fim = self.data_fim_prova_final
                descricao = 'Prova Final'
                cal.adicionar_evento_calendario(data_inicio, data_fim, descricao, 'conflito_leve')

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
                msg = ValidationError('A data de fechamento do período deve ser maior que a data de encerramento das aulas.')
            if not self.data_inicio == self.data_inicio_etapa_1:
                msg = ValidationError('A data de início da primeira etapa deve ser igual a data de início das aulas.')
            if self.data_inicio_etapa_1 > self.data_fim_etapa_1:
                msg = ValidationError('A data de encerramento da primeira etapa deve ser superior da data de início da primeira etapa.')
            if self.qtd_etapas == CalendarioAcademico.QTD_ETAPA_2:
                if not self.data_inicio_etapa_2 or not self.data_fim_etapa_2:
                    msg = ValidationError('Preencha as datas de início e de fim da segunda etapa.')
            if self.qtd_etapas == CalendarioAcademico.QTD_ETAPA_4:
                if not self.data_inicio_etapa_2 or not self.data_fim_etapa_2:
                    msg = ValidationError('Preencha as datas de início e de fim da segunda etapa.')
                if not self.data_inicio_etapa_3 or not self.data_fim_etapa_3:
                    msg = ValidationError('Preencha as datas de início e de fim da terceira etapa.')
                if not self.data_inicio_etapa_4 or not self.data_fim_etapa_4:
                    msg = ValidationError('Preencha as datas de início e de fim da quarta etapa.')
            if self.qtd_etapas == CalendarioAcademico.QTD_ETAPA_1:
                if not self.data_fim == self.data_fim_etapa_1:
                    msg = ValidationError('A data de encerramento da primeira etapa deve ser igual a data de encerramento das aulas.')
            if self.qtd_etapas > CalendarioAcademico.QTD_ETAPA_1:
                if self.data_fim_etapa_1 > self.data_inicio_etapa_2:
                    msg = ValidationError('A data de início da segunda etapa deve ser superior a data de encerramento da primeira etapa.')
            if self.qtd_etapas > CalendarioAcademico.QTD_ETAPA_1:
                if self.data_inicio_etapa_2 > self.data_fim_etapa_2:
                    msg = ValidationError('A data de encerramento da segunda etapa deve ser superior a data de início da segunda etapa.')
            if self.qtd_etapas == CalendarioAcademico.QTD_ETAPA_2:
                if not self.data_fim == self.data_fim_etapa_2:
                    msg = ValidationError('A data de encerramento da segunda etapa deve ser igual a data de encerramento das aulas.')
            if self.qtd_etapas > CalendarioAcademico.QTD_ETAPA_2:
                if self.data_fim_etapa_2 > self.data_inicio_etapa_3:
                    msg = ValidationError('A data de início da terceira etapa deve ser superior a data de encerramento da segunda etapa.')
            if self.qtd_etapas > CalendarioAcademico.QTD_ETAPA_2:
                if self.data_inicio_etapa_3 > self.data_fim_etapa_3:
                    msg = ValidationError('A data de encerramento da terceira etapa deve ser superior a data de início da terceira etapa.')
            if self.qtd_etapas > CalendarioAcademico.QTD_ETAPA_2:
                if self.data_fim_etapa_3 > self.data_inicio_etapa_4:
                    msg = ValidationError('A data de início da quarta etapa deve ser superior a data de encerramento da terceira etapa.')
            if self.qtd_etapas > CalendarioAcademico.QTD_ETAPA_2:
                if self.data_inicio_etapa_4 > self.data_fim_etapa_4:
                    msg = ValidationError('A data de encerramento da quarta etapa deve ser superior a data de início da quarta etapa.')
            if self.qtd_etapas == CalendarioAcademico.QTD_ETAPA_4:
                if not self.data_fim == self.data_fim_etapa_4:
                    msg = ValidationError('A data de encerramento da quarta etapa deve ser igual a data de encerramento das aulas.')
        except Exception:
            raise ValidationError('Preencha os campos obrigatórios.')
        if msg:
            raise msg

    def replicar(self, uos):
        ids = []
        modelo = self
        for uo in uos:
            if not '[REPLICADO]' in modelo.descricao:
                modelo.descricao = '{} [REPLICADO]'.format(modelo.descricao)
            modelo.id = None
            modelo.uo = uo
            modelo.save()
            ids.append(str(modelo.id))
        return ids

    def save(self, *args, **kwargs):
        # selecionando professordiario que tenham o calendário acadêmico e alternando as datas das etapas
        super(self.__class__, self).save(*args, **kwargs)

        professores_diarios = ProfessorDiario.objects.filter(diario__calendario_academico=self)
        for professor_diario in professores_diarios:
            professor_diario.atualizar_data_posse()
