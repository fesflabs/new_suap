import datetime
from django.conf import settings
from django.apps import apps
from django.db.models import Q
from django.db import models, ProgrammingError
from django.db.utils import OperationalError
from comum.utils import tl, get_sigla_reitoria


GRUPOS = ['Administrador Acadêmico', 'Secretário Acadêmico', 'Diretor Acadêmico', 'Visualizador de Informações Acadêmicas', 'Auditor', 'Estagiário Acadêmico Sistêmico']


class FiltroDiretoriaManager(models.Manager):
    def __init__(self, key=None):
        super().__init__()
        self.key = key

    def get_queryset(self):
        qs = super().get_queryset()
        ids = self.get_ids()
        if ids:
            from edu.models.diretorias import Diretoria

            if Diretoria.objects.filter(tipo=Diretoria.TIPO_SISTEMICA, setor_id__in=ids).exists():
                return qs

            ids_diretoria_ensino = Diretoria.objects.filter(tipo=Diretoria.TIPO_DIRETORIA_ENSINO, setor_id__in=ids).values_list('id', flat=True)
            if ids_diretoria_ensino:
                ids_uos_diretoria_ensino = Diretoria.objects.filter(id__in=ids_diretoria_ensino).values_list('setor__uo_id', flat=True)
                ids.extend(Diretoria.objects.filter(setor__uo_id__in=ids_uos_diretoria_ensino).values_list('setor_id', flat=True))

            if self.key:
                filtro = {f'{self.key}__setor_id__in': ids}
            else:
                filtro = {'setor_id__in': ids}

            qs = qs.filter(**filtro)
        return qs

    def get_ids(self):
        ids = []
        try:
            from comum.models import UsuarioGrupoSetor

            user = tl.get_user()
            if user and user.groups.filter(name__in=['Administrador Acadêmico', 'Estagiário Acadêmico Sistêmico']).exists():
                return ids
            elif user and user.pk:
                groups = GRUPOS + ['Apoio Acadêmico', 'Auxiliar de Secretaria Acadêmica', 'Coordenador de Curso',
                                   'Coordenador de Desporto', 'Coordenador de Modalidade Acadêmica', 'Diretor Geral',
                                   'Estagiário', 'Membro ETEP', 'Organizador de Formatura',
                                   'Organizador de Minicurso', 'Pedagogo']
                ids = list(UsuarioGrupoSetor.objects.filter(usuario_grupo__user=user, usuario_grupo__group__name__in=groups).values_list('setor_id', flat=True))
                if not ids:
                    if user.get_vinculo() and user.get_vinculo().setor:
                        ids = [user.get_vinculo().setor.id]
                    else:
                        ids = [None]
            qs = apps.get_model('rh', 'UnidadeOrganizacional').objects.suap().filter(sigla=get_sigla_reitoria())
            try:
                reitoria = qs.first()
            # banco ainda não foi criado
            except OperationalError:
                reitoria = None
            if reitoria and reitoria.setor.pk in ids:
                return []
        except ProgrammingError:
            pass
        return ids


class AbonoFaltaManager(FiltroDiretoriaManager):
    def get_queryset(self):
        user = tl.get_user()
        qs = super().get_queryset()
        if user and user.groups.filter(name='Professor').exists():
            from edu.models import ProfessorDiario

            ids_alunos = (
                ProfessorDiario.objects.filter(professor__vinculo__user__username=user.username)
                .order_by('diario__matriculadiario__matricula_periodo__aluno')
                .values_list('diario__matriculadiario__matricula_periodo__aluno', flat=True)
                .distinct()
            )
            return (qs | qs.model.objects.filter(aluno__in=ids_alunos)).distinct()
        else:
            return qs


class FiltroPoloManager(FiltroDiretoriaManager):
    def __init__(self, key=None, polo_key=None):
        super().__init__()
        self.key = key
        self.polo_key = polo_key

    def get_queryset(self):
        user = tl.get_user()
        qs = super().get_queryset()
        if not user or user.groups.filter(name__in=GRUPOS + ['Administrador EAD']).exists():
            return qs
        else:
            from edu.models import TutorPolo, CoordenadorPolo, Polo

            pks = []
            for pk in Polo.objects.filter(turma__curso_campus__coordenador__user=user).values_list('id', flat=True):
                pks.append(pk)
            for pk in TutorPolo.objects.filter(funcionario__user=user).values_list('polo_id', flat=True):
                pks.append(pk)
            for pk in CoordenadorPolo.objects.filter(funcionario__user=user).values_list('polo_id', flat=True):
                pks.append(pk)
            if self.polo_key:
                return qs.filter(**{f'{self.polo_key}__id__in': pks})
            else:
                return qs.filter(**{'id__in': pks})


class FiltroUnidadeOrganizacionalManager(models.Manager):
    def __init__(self, key=None):
        super().__init__()
        self.key = key

    def get_queryset(self):
        qs = super().get_queryset()
        eh_setor_suap = settings.TIPO_ARVORE_SETORES == 'SUAP'
        if not self.key:
            if eh_setor_suap:
                qs = qs.filter(setor__codigo__isnull=True)
            else:
                qs = qs.filter()
        ids = self.get_ids()
        if ids:
            if self.key:
                filtro = {f'{self.key}__id__in': ids}
            else:
                filtro = {'id__in': ids}
            qs = qs.filter(**filtro)
        return qs

    def get_ids(self):
        from comum.models import UsuarioGrupoSetor

        user = tl.get_user()
        ids = []
        if not user or user.groups.filter(name__in=['Administrador Acadêmico', 'Estagiário Acadêmico Sistêmico']).exists():
            return ids
        elif user and user.pk:
            groups = GRUPOS + [
                'Agendador de Aula de Campo EDU',
                'Coordenador de Registros Acadêmicos',
                'Coordenador de Desporto',
                'Coordenador de Curso',
                'Coordenador de Modalidade Acadêmica',
                'Pedagogo',
                'Membro ETEP',
            ]
            ids = UsuarioGrupoSetor.objects.filter(usuario_grupo__user=user, usuario_grupo__group__name__in=groups).values_list('setor__uo', flat=True)

        UnidadeOrganizacional = apps.get_model('rh', 'UnidadeOrganizacional')
        qs = UnidadeOrganizacional.objects.suap().filter(sigla=get_sigla_reitoria())
        if qs.exists() and qs[0].pk in ids:
            return []
        return ids


class DiretoriaManager(FiltroDiretoriaManager):
    def __init__(self):
        super().__init__(None)

    def sem_diretores(self):
        return self.get_queryset().exclude(setor__usuariogrupo__group__name='Diretor Acadêmico')

    def sem_secretarios(self):
        return self.get_queryset().exclude(setor__usuariogrupo__group__name='Secretário Acadêmico')

    def sem_coordenadores(self):
        return self.get_queryset().exclude(setor__usuariogrupo__group__name='Coordenador de Curso')

    def sem_pedagogos(self):
        return self.get_queryset().exclude(setor__usuariogrupo__group__name='Pedagogo')


class DiarioQuery(models.QuerySet):
    def sem_professores(self):
        from comum.models import Configuracao

        ano_letivo_atual = int(Configuracao.get_valor_por_chave('edu', 'ano_letivo_atual') or 1)
        periodo_letivo_atual = int(Configuracao.get_valor_por_chave('edu', 'periodo_letivo_atual') or 1)
        qs = self.exclude(professordiario__id__isnull=False)
        if periodo_letivo_atual == 1:
            qs = qs.exclude(segundo_semestre=True, ano_letivo__ano=ano_letivo_atual)
        return qs

    def sem_local_aula(self):
        from comum.models import Configuracao
        from edu.models import ComponenteCurricular

        ano_letivo_atual = int(Configuracao.get_valor_por_chave('edu', 'ano_letivo_atual') or 1)
        periodo_letivo_atual = int(Configuracao.get_valor_por_chave('edu', 'periodo_letivo_atual') or 1)
        qs = self.filter(turma__curso_campus__diretoria__ead=False).filter(local_aula__id__isnull=True)
        # plano de retomada de aulas em virtude da pandemia (COVID19)
        qs = qs.exclude(turma__pertence_ao_plano_retomada=True)
        if periodo_letivo_atual == 1:
            qs = qs.exclude(segundo_semestre=True, ano_letivo__ano=ano_letivo_atual)
        qs = qs.exclude(
            componente_curricular__tipo__in=[
                ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL,
                ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
                ComponenteCurricular.TIPO_SEMINARIO,
            ]
        )
        return qs

    def sem_horario_aula(self):
        from edu.models import ComponenteCurricular, HorarioAulaDiario

        qs = self.filter(turma__curso_campus__diretoria__ead=False)

        diarios_pks = HorarioAulaDiario.objects.all().values_list('diario_id', flat=True).distinct()
        qs = qs.exclude(pk__in=diarios_pks)

        qs = qs.exclude(
            componente_curricular__tipo__in=[
                ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL,
                ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
                ComponenteCurricular.TIPO_SEMINARIO,
            ]
        )
        return qs

    def pendentes(self):
        from edu.models import MatriculaDiario

        qs = MatriculaDiario.objects.filter(
            Q(
                situacao__in=[MatriculaDiario.SITUACAO_CURSANDO, MatriculaDiario.SITUACAO_PROVA_FINAL],
                diario__calendario_academico__data_fechamento_periodo__lt=datetime.datetime.now()),
            Q(diario__componente_curricular__qtd_avaliacoes__gte=1, nota_1__isnull=True) | Q(
                diario__componente_curricular__qtd_avaliacoes__gte=2, nota_2__isnull=True) | Q(
                diario__componente_curricular__qtd_avaliacoes__gte=4, nota_3__isnull=True) | Q(
                diario__componente_curricular__qtd_avaliacoes__gte=4, nota_4__isnull=True)
        )
        ids_diario = list(qs.values_list('diario_id', flat=True).order_by('diario_id').distinct())
        return self.filter(pk__in=ids_diario)

    def em_andamento(self):
        now = datetime.datetime.now()
        return self.filter(calendario_academico__data_inicio__lte=now, calendario_academico__data_fechamento_periodo__gte=now).order_by('id')

    def semestrais_em_cursos_anuais(self):
        return self.filter(calendario_academico__qtd_etapas=4, componente_curricular__qtd_avaliacoes=2)

    def em_curso(self):
        qs = self
        qs1 = qs.filter(componente_curricular__qtd_avaliacoes__lt=2, posse_etapa_1=1)
        qs2 = qs.filter(componente_curricular__qtd_avaliacoes=2, posse_etapa_2=1)
        qs3 = qs.filter(componente_curricular__qtd_avaliacoes=4)
        qs3 = qs3.filter(posse_etapa_3=1) | qs3.filter(posse_etapa_4=1)

        return qs1 | qs2 | qs3

    def entregues(self):
        from edu.models.diarios import Diario

        return self.filter(posse_etapa_5=Diario.POSSE_REGISTRO_ESCOLAR)

    def nao_entregues(self):
        from edu.models.diarios import Diario

        return self.filter(posse_etapa_5=Diario.POSSE_PROFESSOR, calendario_academico__data_fechamento_periodo__lt=datetime.datetime.now())


class DiarioManager(models.Manager):
    def sem_professores(self):
        return self.get_queryset().sem_professores()

    def sem_local_aula(self):
        return self.get_queryset().sem_local_aula()

    def sem_horario_aula(self):
        return self.get_queryset().sem_horario_aula()

    def pendentes(self):
        return self.get_queryset().pendentes()

    def em_andamento(self):
        return self.get_queryset().em_andamento()

    def semestrais_em_cursos_anuais(self):
        return self.get_queryset().semestrais_em_cursos_anuais()

    def em_curso(self):
        return self.get_queryset().em_curso()

    def entregues(self):
        return self.get_queryset().entregues()

    def get_queryset(self):
        return DiarioQuery(self.model, using=self._db)


class DiarioLocalManager(FiltroDiretoriaManager, DiarioManager):
    def __init__(self):
        super().__init__('turma__curso_campus__diretoria')

    def get_queryset(self):
        qs = super().get_queryset()
        user = tl.get_user()
        q = qs.none()

        # Coordenadores de polo podem visualizar diarios de turmas dos polos que ele coordena
        if user and user.groups.filter(name='Coordenador de Polo EAD').exists():
            from edu.models import CoordenadorPolo

            ids = CoordenadorPolo.objects.filter(funcionario=user.get_profile()).values_list('polo__id')
            q = q | qs.filter(turma__polo__id__in=ids)

        # Coordenadores de cursos podem visualizar diarios de turmas dos cursos que ele coordena
        if user and user.groups.filter(name='Coordenador de Curso').exists():
            q = q | qs.filter(turma__curso_campus__coordenador_id=user.get_profile().pk) | qs.filter(turma__curso_campus__coordenador_2_id=user.get_profile().pk)

        # Diretores Acadêmicos podem visualizar diarios de sua diretoria ou diarios de professores de sua diretoria
        if user and user.groups.filter(name__in=['Diretor Acadêmico', 'Auxiliar de Secretaria Acadêmica']).exists():
            from edu.models.diarios import Diario

            q = q | qs.filter(turma__curso_campus__diretoria__setor__uo=user.get_vinculo().setor.uo_id)
            q = q | Diario.objects.filter(professordiario__professor__vinculo__setor__uo=user.get_vinculo().setor.uo_id)

        # Diretor Geral e Comissão de horário podem visualizar todos os diarios do campus
        if user and user.groups.filter(name__in=['Diretor Geral', 'Comissão de Horários']).exists():
            q = q | qs.model.objects.filter(turma__curso_campus__diretoria__setor__uo=user.get_vinculo().setor.uo_id)

        # Coordenador de Modalidade Acadêmica
        if user and user.groups.filter(name='Coordenador de Modalidade Acadêmica').exists():
            q = q | qs.filter(turma__curso_campus__modalidade__id__in=list(user.get_profile().funcionario.servidor.coordenadormodalidade_set.values_list('modalidades', flat=True)))

        # Professores podem acessar todos os seus diários
        if user and user.groups.filter(name='Professor').exists():
            q = q | qs.model.objects.filter(professordiario__professor__vinculo__user=user)

        if user and user.groups.filter(name__in=GRUPOS + ['Pedagogo', 'Apoio Acadêmico', 'Membro ETEP']).exists():
            q = q | qs

        return q.select_related('componente_curricular__componente__nivel_ensino', 'turma', 'ano_letivo').distinct()


class DiarioEspecialManager(FiltroDiretoriaManager):
    def __init__(self):
        super().__init__('diretoria')

    def sem_professores(self):
        return self.get_queryset().exclude(professores__isnull=False)

    def sem_local_aula(self):
        return self.get_queryset().filter(sala__isnull=True)

    def sem_horario_aula(self):
        return self.get_queryset().exclude(horarioauladiarioespecial__id__isnull=False)


class TurmaQuery(models.QuerySet):
    def pendentes(self):
        from edu.models import Diario

        return self.filter(diario__in=Diario.locals.pendentes()).order_by('id').distinct()

    def em_andamento(self):
        from edu.models import Diario

        return self.filter(diario__in=Diario.locals.em_andamento()).order_by('id').distinct()


class TurmaManager(models.Manager):
    def get_queryset(self):
        return TurmaQuery(self.model, using=self._db)

    def pendentes(self):
        return self.get_queryset().pendentes()

    def em_andamento(self):
        return self.get_queryset().em_andamento()


class TurmaLocalManager(FiltroDiretoriaManager, TurmaManager):
    def __init__(self):
        super().__init__('curso_campus__diretoria')

    def get_queryset(self):
        qs = super().get_queryset()
        user = tl.get_user()
        q = qs.none()

        # Coordenadores de polo podem visualizar turmas dos polos que ele coordena
        if user and user.groups.filter(name='Coordenador de Polo EAD').exists():
            from edu.models import CoordenadorPolo

            ids = CoordenadorPolo.objects.filter(funcionario=user.get_profile()).values_list('polo__id')
            q = q | qs.model.objects.filter(polo__id__in=ids)

        # Coordenadores de cursos podem visualizar turmas dos cursos que ele coordena
        if user and user.groups.filter(name='Coordenador de Curso').exists():
            q = q | qs.model.objects.filter(curso_campus__coordenador_id=user.get_profile().pk) | qs.model.objects.filter(curso_campus__coordenador_2_id=user.get_profile().pk)

        if user and user.groups.filter(name__in=['Diretor Geral', 'Auxiliar de Secretaria Acadêmica', 'Apoio Acadêmico']).exists():
            q = q | qs.model.objects.filter(curso_campus__diretoria__setor__uo=user.get_vinculo().setor.uo_id)

        # Coordenador de Modalidade Acadêmica
        if user and user.groups.filter(name='Coordenador de Modalidade Acadêmica').exists():
            q = q | qs.filter(curso_campus__modalidade__id__in=user.get_profile().funcionario.servidor.coordenadormodalidade_set.values_list('modalidades', flat=True))

        if user and user.groups.filter(name__in=GRUPOS + ['Pedagogo', 'Avaliador do Catálogo Digital']).exists():
            q = q | qs

        return q.distinct()


class MatrizQuery(models.QuerySet):
    def vazias(self):
        return self.exclude(componentecurricular__id__isnull=False)

    def incompletas(self):
        return self.filter(inconsistente=True)


class MatrizManager(models.Manager):
    def get_queryset(self):
        return MatrizQuery(self.model, using=self._db)

    def vazias(self):
        return self.get_queryset().vazias()

    def incompletas(self):
        return self.get_queryset().incompletas()


class SolicitacaoUsuarioManager(FiltroUnidadeOrganizacionalManager):
    def __init__(self):
        super().__init__('uo')

    def pendentes(self):
        return self.get_queryset().exclude(avaliador__id__isnull=False)


class SolicitacaoRelancamentoEtapaManager(FiltroUnidadeOrganizacionalManager):
    def __init__(self):
        super().__init__('uo')

    def pendentes(self):
        return self.get_queryset().exclude(avaliador__id__isnull=False)


class SolicitacaoProrrogacaoEtapaManager(FiltroDiretoriaManager):
    def __init__(self):
        super().__init__('professor_diario__diario__turma__curso_campus__diretoria')

    def pendentes(self):
        return self.get_queryset().exclude(avaliador__id__isnull=False)


class AtividadeComplementarManager(FiltroDiretoriaManager):
    def __init__(self):
        super().__init__('aluno__curso_campus__diretoria')

    def get_queryset(self):
        qs = super().get_queryset()
        user = tl.get_user()
        if user and not user.groups.filter(name__in=['Administrador Acadêmico', 'Secretário Acadêmico', 'Estagiário Acadêmico Sistêmico']).exists():
            qs = qs.filter(aluno__curso_campus__coordenador__username=user.username) | qs.filter(aluno__curso_campus__coordenador_2__username=user.username)
            return qs.distinct()
        return qs

    def pendentes(self):
        return self.get_queryset().filter(deferida__isnull=True)


class AtividadeAprofundamentoManager(FiltroDiretoriaManager):
    def __init__(self):
        super().__init__('aluno__curso_campus__diretoria')

    def get_queryset(self):
        qs = super().get_queryset()
        user = tl.get_user()
        if user and not user.groups.filter(name__in=['Administrador Acadêmico', 'Secretário Acadêmico', 'Estagiário Acadêmico Sistêmico']).exists():
            return qs.filter(aluno__curso_campus__coordenador__username=user.username)
        return qs

    def pendentes(self):
        return self.get_queryset().filter(deferida__isnull=True)


class CursoCampusQuery(models.QuerySet):
    def sem_coordenadores(self):
        return self.filter(coordenador__isnull=True, ativo=True)

    def com_coordenadores(self):
        return self.filter(coordenador__isnull=False)

    def nao_vinculados_diretoria(self):
        return self.filter(diretoria__isnull=True)

    def sob_coordenacao_de(self, funcionario):
        return self.filter(coordenador=funcionario)

    def integralizados(self):
        return self.filter(aluno__matriz__id__isnull=False, aluno__codigo_academico__isnull=False).distinct()


class CursoCampusManager(models.Manager):
    def get_queryset(self):
        return CursoCampusQuery(self.model, using=self._db).select_related('diretoria__setor__uo')

    def sem_coordenadores(self):
        return self.get_queryset().sem_coordenadores()

    def com_coordenadores(self):
        return self.get_queryset().com_coordenadores()

    def nao_vinculados_diretoria(self):
        return self.get_queryset().nao_vinculados_diretoria()

    def sob_coordenacao_de(self, funcionario):
        return self.get_queryset().sob_coordenacao_de(funcionario)

    def integralizados(self):
        return self.get_queryset().integralizados()


class MinicursoObjectsManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(ch_total__gt=0).distinct()


class MinicursoLocalsManager(FiltroDiretoriaManager):
    def __init__(self):
        super().__init__('diretoria')

    def get_queryset(self):
        return super().get_queryset().filter(ch_total__gt=0).distinct()


class ProfessorQuery(models.QuerySet):
    def ativo(self):
        return self.all().distinct()

    def servidores_docentes(self):
        from rh.models import Servidor

        return self.servidores().filter(vinculo__id_relacionamento__in=Servidor.objects.filter(eh_docente=True).values_list('id', flat=True))

    def servidores_tecnicos(self):
        from rh.models import Servidor

        return self.servidores().filter(vinculo__id_relacionamento__in=Servidor.objects.filter(eh_tecnico_administrativo=True).values_list('id', flat=True))

    def nao_servidores(self):
        return self.exclude(vinculo__tipo_relacionamento__app_label='rh', vinculo__tipo_relacionamento__model='servidor')

    def servidores(self):
        return self.filter(vinculo__tipo_relacionamento__app_label='rh', vinculo__tipo_relacionamento__model='servidor')


class ProfessorAtivoManager(FiltroDiretoriaManager):
    def __init__(self):
        super().__init__('professordiario__diario__turma__curso_campus__diretoria')

    def get_queryset(self):
        return super().get_queryset().distinct()


class ProfessorServidorDocenteManager(ProfessorAtivoManager):
    def get_queryset(self):
        from rh.models import Servidor

        return super(self.__class__, self).get_queryset().filter(vinculo__pessoa__id__in=Servidor.objects.filter(eh_docente=True).values_list('pessoa_fisica__id', flat=True))


class ProfessorServidorTecnicoManager(ProfessorAtivoManager):
    def get_queryset(self):
        from rh.models import Servidor

        return (
            super(self.__class__, self)
            .get_queryset()
            .filter(vinculo__pessoa__id__in=Servidor.objects.filter(eh_tecnico_administrativo=True).values_list('pessoa_fisica__id', flat=True))
        )


class ProfessorNaoServidorManager(ProfessorAtivoManager):
    def get_queryset(self):
        return super(self.__class__, self).get_queryset().exclude(vinculo__tipo_relacionamento__app_label='rh', vinculo__tipo_relacionamento__model='servidor')


class ProfessorServidorManager(ProfessorAtivoManager):
    def get_queryset(self):
        return super(self.__class__, self).get_queryset().filter(vinculo__tipo_relacionamento__app_label='rh', vinculo__tipo_relacionamento__model='servidor')


class AlunoManager(models.Manager):
    def autocomplete(self):
        qs = super().get_queryset()
        qs = qs.select_related('pessoa_fisica',
                               'pessoa_fisica__pessoa_ptr',
                               'curso_campus',
                               'curso_campus__diretoria__setor__uo')
        qs = qs.only('foto', 'matricula', 'pessoa_fisica__pessoa_ptr__search_fields_optimized', 'pessoa_fisica__nome', 'pessoa_fisica__nome_registro', 'pessoa_fisica__nome_social',
                     'curso_campus__codigo', 'curso_campus__descricao', 'curso_campus__diretoria__setor__uo__nome')
        return qs


class AlunosFICManager(models.Manager):
    def get_queryset(self):
        from edu.models import Modalidade

        return super().get_queryset().filter(curso_campus__modalidade__pk__in=[Modalidade.FIC, Modalidade.PROEJA_FIC_FUNDAMENTAL])


class AlunosNaoFICManager(models.Manager):
    def get_queryset(self):
        from edu.models import Modalidade

        return super().get_queryset().exclude(curso_campus__modalidade__pk__in=[Modalidade.FIC, Modalidade.PROEJA_FIC_FUNDAMENTAL])


class AlunosAtivosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(situacao__ativo=True)


class AlunosCaracterizadosManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(caracterizacao__isnull=False)


class AlunosComMatrizManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(matriz__isnull=False)


class AlunoLocalManager(models.Manager):
    def get_queryset(self):
        qs = super().get_queryset()
        user = tl.get_user()
        # Coordenadores de polo que não possuem outro perfil que permite visualização de aluno, só podem visualizar alunos do seu polo
        if user and user.groups.filter(name='Coordenador de Polo EAD').exists():
            if user.groups.filter(permissions__codename='view_aluno').count() == 1:
                from edu.models import CoordenadorPolo

                ids = CoordenadorPolo.objects.filter(funcionario=user.get_profile()).values_list('polo__id')
                return qs.filter(polo__id__in=ids)
        return qs


class EstagioDocenteManager(models.Manager):
    def get_queryset(self):
        user = tl.get_user()
        qs = (
            super()
            .get_queryset()
            .order_by('-matricula_diario__diario__ano_letivo__ano')
            .order_by('-matricula_diario__diario__periodo_letivo')
            .order_by('matricula_diario__matricula_periodo__aluno__matricula')
        )
        if not user.is_superuser and not user.groups.filter(name__in=['Coordenador de Estágio Sistêmico', 'estagios Administrador', 'Administrador Acadêmico', 'Auditor', 'Estagiário Acadêmico Sistêmico']).exists():
            from edu.models.estagio_docente import EstagioDocente

            qs_ret = EstagioDocente.objects.none()
            if user.groups.filter(name__in=['Coordenador de Estágio Docente']).exists():
                qs_coordenador_estagio_docente = qs.filter(
                    matricula_diario__matricula_periodo__aluno__curso_campus__coordenadores_estagio_docente__vinculo__pessoa__pk=user.get_profile().pk
                )
                qs_ret = qs_coordenador_estagio_docente
            if user.groups.filter(name__in=['Coordenador de Curso']).exists():
                qs_coordenador_de_curso = qs.filter(matricula_diario__matricula_periodo__aluno__curso_campus__coordenador__pk=user.get_profile().pk)
                qs_ret = qs_ret | qs_coordenador_de_curso
            if user.groups.filter(name__in=['Professor']).exists():
                qs_professor = qs.filter(professor_orientador__vinculo__pessoa__pk=user.get_profile().pk)
                qs_ret = qs_ret | qs_professor
            if user.groups.filter(name__in=['Aluno']).exists():
                return qs.filter(matricula_diario__matricula_periodo__aluno__pessoa_fisica__pk=user.get_profile().pk)
            return qs_ret.distinct()
        return qs
