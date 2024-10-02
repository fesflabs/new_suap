import datetime

from djtools.db import models
from djtools.thumbs import ImageWithThumbsField
from djtools.storages import get_overwrite_storage
from djtools.utils import tooltip_text
from edu.managers import (
    ProfessorServidorDocenteManager,
    ProfessorServidorTecnicoManager,
    ProfessorNaoServidorManager,
    ProfessorAtivoManager,
    ProfessorServidorManager,
    ProfessorQuery,
)
from edu.models.projeto_final import ProjetoFinal
from edu.models.cadastros_gerais import HorarioCampus, HorarioAulaDiario, Turno, CursoFormacaoSuperior
from edu.models.estagio_docente import EstagioDocente
from edu.models.logs import LogModel
from rh.models import Servidor, PessoaFisica


class Professor(LogModel):
    SEARCH_FIELDS = ['vinculo__pessoa__nome', 'vinculo__user__username', 'vinculo__pessoa__pessoafisica__cpf']

    # Managers
    objects = ProfessorQuery().as_manager()
    ativos = ProfessorAtivoManager()
    servidores_docentes = ProfessorServidorDocenteManager()
    servidores_tecnicos = ProfessorServidorTecnicoManager()
    nao_servidores = ProfessorNaoServidorManager()
    servidores = ProfessorServidorManager()
    # Fields
    pessoa_fisica_remover = models.ForeignKeyPlus('rh.PessoaFisica', verbose_name='Pessoa Física')
    vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Vínculo', on_delete=models.CASCADE, null=False)

    disciplina = models.ForeignKeyPlus('edu.Disciplina', verbose_name='Disciplina de Ingresso', null=True, blank=True, on_delete=models.CASCADE)
    nce = models.ManyToManyFieldPlus('edu.NucleoCentralEstruturante', verbose_name='Núcleo Central Estruturante', blank=True)

    TITULACAO_CHOICES = [
        ['Graduado', 'Graduado'],
        ['Graduada', 'Graduada'],
        ['Especialista', 'Especialista'],
        ['Mestre', 'Mestre'],
        ['Mestra', 'Mestra'],
        ['Doutor', 'Doutor'],
        ['Doutora', 'Doutora'],
        ['Pós-Doutor', 'Pós-Doutor'],
        ['Pós-Doutora', 'Pós-Doutora'],
    ]
    AREA_ULTIMA_TITULACAO_CHOICES = [
        ['99', 'Programas básicos'],
        ['01', 'Educação'],
        ['02', 'Artes e humanidades'],
        ['03', 'Ciências sociais, comunicação e informação'],
        ['04', 'Negócios, administração e direito'],
        ['05', 'Ciências naturais, matemática e estatística'],
        ['06', 'Computação e Tecnologias da Informação e Comunicação (TIC)'],
        ['07', 'Engenharia, produção e construção'],
        ['08', 'Agricultura, silvicultura, pesca e veterinária'],
        ['09', 'Saúde e bem-estar'],
        ['10', 'Serviços'],
    ]
    titulacao = models.CharFieldPlus('Titulação', choices=TITULACAO_CHOICES, null=True, blank=True)
    ultima_instituicao_de_titulacao = models.CharFieldPlus('Instituição onde recebeu a última titulação', null=True, blank=True)
    area_ultima_titulacao = models.CharFieldPlus('Área da Última Titulação', null=True, blank=True, choices=AREA_ULTIMA_TITULACAO_CHOICES)
    ano_ultima_titulacao = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano da Última Titulação', null=True, blank=True, on_delete=models.CASCADE)
    vinculo_professor_ead = models.ForeignKeyPlus('edu.VinculoProfessorEAD', verbose_name='Vinculo do Professor com o EAD', null=True, blank=True, on_delete=models.CASCADE)

    ano_inicio_curso_superior = models.IntegerField('Ano de Início do Curso Superior', null=True, blank=True)
    ano_conclusao_curso_superior = models.IntegerField('Ano de Conclusão do Curso Superior', null=True, blank=True)
    possui_formacao_complementar = models.BooleanField('Possui formação/complementação pedagógica', default=False)
    codigo_curso_superior = models.CharFieldPlus('Código do Curso Superior', null=True, blank=True)
    curso_superior = models.ForeignKeyPlus(CursoFormacaoSuperior, verbose_name='Curso Superior', null=True, blank=True, on_delete=models.CASCADE)
    instituicao_ensino_superior = models.ForeignKeyPlus('edu.InstituicaoEnsinoSuperior', verbose_name='Instituição de Ensino Superior', null=True, blank=True)

    foto = ImageWithThumbsField(storage=get_overwrite_storage(), use_id_for_name=True, upload_to='professores', sizes=((75, 100), (150, 200)), null=True, blank=True)

    cursos_lecionados = models.ManyToManyFieldPlus('edu.CursoCampus', verbose_name='Cursos Lecionados')

    # Metadata
    class Meta:
        verbose_name = 'Professor'
        verbose_name_plural = 'Professores'
        ordering = ('vinculo__pessoa__nome',)
        permissions = (
            ('pode_ver_cpf_professor', 'Pode visualizar o CPF do professor'),
            ('eh_professor', 'É professor'),
        )

    def __str__(self):
        return '{} ({})'.format(self.get_nome(), self.get_matricula())

    # remover após migração de pessoa fisica para vinculo
    def save(self, *args, **kwargs):
        self.pessoa_fisica_remover_id = self.vinculo.pessoa.id
        return super().save(*args, **kwargs)

    def get_vinculo(self):
        return self.vinculo

    def get_materiais_aula_outros_vinculos(self):
        from edu.models.diarios import MaterialAula

        pessoa_fisica = PessoaFisica.objects.get(pk=self.vinculo.pessoa_id)
        descricoes = self.materialaula_set.values_list('descricao', flat=True)
        return MaterialAula.objects.exclude(professor_id=self.pk).filter(professor__vinculo__pessoa__pessoafisica__cpf=pessoa_fisica.cpf).exclude(descricao__in=descricoes)

    def get_titulacao(self):
        titulacao = None
        if self.titulacao:
            titulacao = self.titulacao
        elif self.vinculo.eh_servidor():
            titulacao = self.vinculo.relacionamento.get_titulacao()
        return titulacao

    def get_qtd_alunos(self):
        from edu.models import MatriculaDiario

        return MatriculaDiario.objects.filter(diario__professordiario__professor=self, situacao=MatriculaDiario.SITUACAO_CURSANDO).count()

    def is_servidor(self):
        return self.vinculo.eh_servidor()

    def get_matricula(self):
        if self.vinculo:
            return self.vinculo.user and self.vinculo.user.username or self.vinculo.relacionamento.pessoa_fisica.cpf
        return None

    def get_horarios_aula_por_horario_campus(self, ano, periodo):
        horarios_campi = HorarioCampus.objects.filter(diario__professordiario__professor=self, diario__ano_letivo__ano=ano).distinct()
        result = []
        for horario_campus in horarios_campi:
            horario_campus.turnos = self.get_horarios_aula_por_turno(ano, periodo, horario_campus)
            result.append(horario_campus)
        return result

    def get_horarios_aula_por_turno(self, ano, periodo, horario_campus=None):
        from edu.models.diarios import Diario
        from edu.models.cursos import CursoCampus

        dias_semana = HorarioAulaDiario.DIA_SEMANA_CHOICES
        if horario_campus:
            horarios_campus_ids = [horario_campus.pk]
        else:
            horarios_campus_ids = Diario.objects.filter(professordiario__professor=self, professordiario__ativo=True).values_list('horario_campus__id', flat=True)
        turnos_ids = HorarioCampus.objects.filter(id__in=horarios_campus_ids).values_list('horarioaula__turno__id', flat=True)
        turnos = Turno.objects.filter(id__in=turnos_ids).order_by('-id')
        for turno in turnos:
            turno.horarios_aula = []
            turno.dias_semana = dias_semana
            turno.vazio = True
            for horario_aula in turno.horarioaula_set.filter(horario_campus__id__in=horarios_campus_ids).order_by('-id').order_by('inicio'):
                horario_aula.dias_semana = []
                horario_aula.vazio = True
                for dia_semana in dias_semana:
                    numero = dia_semana[0]
                    nome = dia_semana[1]
                    marcado = False
                    sigla = ''

                    qs_horarios = HorarioAulaDiario.objects.filter(
                        diario__professordiario__professor=self,
                        diario__professordiario__ativo=True,
                        dia_semana=dia_semana[0],
                        horario_aula=horario_aula,
                        diario__ano_letivo__ano=ano,
                    )
                    qs_horarios_semestrais = qs_horarios.filter(diario__periodo_letivo=periodo).exclude(diario__turma__curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL)
                    qs_horarios_anuais = qs_horarios.filter(diario__turma__curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL)
                    # excluíndo os diários semestrais em cursos anuais
                    if periodo == 1:
                        qs_horarios_anuais = qs_horarios_anuais.exclude(diario__segundo_semestre=True)
                    else:
                        qs_horarios_anuais = qs_horarios_anuais.exclude(diario__segundo_semestre=False, diario__componente_curricular__qtd_avaliacoes=2)
                    qs = qs_horarios_semestrais | qs_horarios_anuais

                    if qs.exists():
                        marcado = True
                        turno.vazio = False
                        horario_aula.vazio = False
                        sigla = ''
                        for diario in Diario.objects.filter(id__in=qs.values_list('diario__id', flat=True)):
                            sigla += tooltip_text(
                                '({})-{} '.format(diario.id, diario.componente_curricular.componente.sigla), diario.componente_curricular.componente.descricao_historico
                            )
                        horario_aula.dias_semana.append(dict(numero=numero, nome=nome, marcado=marcado, sigla=sigla, horarios_aula_diario=qs))
                    else:
                        horario_aula.dias_semana.append(dict(numero=numero, nome=nome, marcado=marcado, sigla=sigla, horarios_aula_diario=[]))
                turno.horarios_aula.append(horario_aula)
        return turnos

    def get_uo(self):
        try:
            if self.vinculo.pessoa.excluido:
                return Servidor.objects.get(pessoa_fisica__id=self.vinculo.pessoa.id).setor_lotacao.uo.equivalente
            return self.vinculo.setor.uo
        except Exception:
            return None

    def get_disciplina(self):
        try:
            return self.disciplina
        except Exception:
            return None

    def get_nome(self):
        return self.vinculo and self.vinculo.pessoa.nome or None

    def get_nome_usual(self):
        return self.vinculo and self.vinculo.pessoa.nome_usual or None

    def get_foto_75x100_url(self):
        return (
            self.foto
            and self.foto.url_75x100
            or self.vinculo
            and self.vinculo.relacionamento.pessoa_fisica.foto
            and self.vinculo.relacionamento.pessoa_fisica.foto.url_75x100
            or '/static/comum/img/default.jpg'
        )

    def get_foto_150x200_url(self):
        return (
            self.foto
            and self.foto.url_150x200
            or self.vinculo
            and self.vinculo.relacionamento.pessoa_fisica.foto
            and self.vinculo.relacionamento.pessoa_fisica.foto.url_150x200
            or '/static/comum/img/default.jpg'
        )

    def get_absolute_url(self):
        return '/edu/professor/{:d}/'.format(self.pk)

    def get_telefones(self):
        if self.vinculo.setor and self.vinculo.setor.setortelefone_set.exists():
            return self.vinculo.setor.setortelefone_set.values_list('numero', flat=True)
        return []

    def get_qtd_orientacoes_estagio(self):
        from estagios.models import PraticaProfissional, Aprendizagem, AtividadeProfissionalEfetiva

        return (
            EstagioDocente.objects.filter(professor_orientador__vinculo__id=self.vinculo.pk)
            .exclude(situacao__in=[EstagioDocente.SITUACAO_ENCERRADO, EstagioDocente.SITUACAO_NAO_CONCLUIDO])
            .count()
            + PraticaProfissional.objects.filter(orientador__vinculo__id=self.vinculo.pk)
            .exclude(status__in=[PraticaProfissional.STATUS_CONCLUIDO, PraticaProfissional.STATUS_RESCINDIDO])
            .count()
            + Aprendizagem.objects.filter(orientador__vinculo__id=self.vinculo.pk).exclude(data_encerramento__isnull=False).count()
            + self.atividadeprofissionalefetiva_set.exclude(situacao__in=[AtividadeProfissionalEfetiva.CONCLUIDA, AtividadeProfissionalEfetiva.NAO_CONCLUIDA]).count()
        )

    def get_qtd_estagios_nao_visitados(self):
        from estagios.models import PraticaProfissional, Aprendizagem

        return (
            EstagioDocente.objects.filter(professor_orientador__vinculo__id=self.vinculo.pk)
            .exclude(visitaestagiodocente__isnull=False)
            .exclude(situacao__in=[EstagioDocente.SITUACAO_MUDANCA, EstagioDocente.SITUACAO_NAO_CONCLUIDO, EstagioDocente.SITUACAO_NAO_CONCLUIDO])
            .count()
            + PraticaProfissional.objects.filter(orientador__vinculo__id=self.vinculo.pk)
            .exclude(visitapraticaprofissional__isnull=False)
            .exclude(status__in=[PraticaProfissional.STATUS_CONCLUIDO, PraticaProfissional.STATUS_RESCINDIDO])
            .count()
            + Aprendizagem.objects.filter(orientador__vinculo__id=self.vinculo.pk).exclude(visitaaprendizagem__isnull=False).exclude(data_encerramento__isnull=False).count()
        )

    def get_anos_com_orientacao_tcc(self):
        return self.orientador_set.values_list('matricula_periodo__ano_letivo__ano', flat=True).distinct()

    def get_anos_com_orientacao_estagios(self):
        estagios = self.praticaprofissional_set.order_by('-data_inicio')
        anos = set()
        for estagio in estagios:
            periodo = estagio.get_periodo_duracao()
            anos = anos | set(range(periodo[0].year, periodo[1].year + 1))
        return sorted(self.excluir_anos_maiores_que_ano_atual(anos), reverse=True)

    def get_anos_com_orientacao_aprendizagens(self):
        aprendizagens = self.aprendizagem_set.order_by('-moduloaprendizagem__inicio')
        anos = set()
        for aprendizagem in aprendizagens:
            periodo = aprendizagem.get_periodo_duracao()
            anos = anos | set(range(periodo[0].year, periodo[1].year + 1))
        return sorted(self.excluir_anos_maiores_que_ano_atual(anos), reverse=True)

    def get_anos_com_orientacao_estagios_docentes(self):
        estagios = self.estagiodocente_orientador_set.order_by('-data_inicio')
        anos = set()
        for estagio in estagios:
            periodo = estagio.get_periodo_duracao()
            if periodo[0] and periodo[1]:
                anos = anos | set(range(periodo[0].year, periodo[1].year + 1))
        return sorted(self.excluir_anos_maiores_que_ano_atual(anos), reverse=True)

    def get_anos_com_orientacao_atividades_profissionais_efetivas(self):
        atividades_profissionais_efetivas = self.atividadeprofissionalefetiva_set.order_by('-inicio')
        anos = set()
        for atividade_profissional_efetiva in atividades_profissionais_efetivas:
            periodo = atividade_profissional_efetiva.get_periodo_duracao()
            if periodo[0] and periodo[1]:
                anos = anos | set(range(periodo[0].year, periodo[1].year + 1))
        return sorted(self.excluir_anos_maiores_que_ano_atual(anos), reverse=True)

    def excluir_anos_maiores_que_ano_atual(self, anos):
        return [x for x in anos if x <= datetime.date.today().year]

    def get_anos_com_diarios(self):
        return self.professordiario_set.values_list('diario__ano_letivo__ano', flat=True).distinct()

    def get_estagios_em_andamento(self):
        from estagios.models import PraticaProfissional

        return self.praticaprofissional_set.exclude(status__in=[PraticaProfissional.STATUS_CONCLUIDO, PraticaProfissional.STATUS_RESCINDIDO])

    def get_estagios_encerrados(self):
        from estagios.models import PraticaProfissional

        return self.praticaprofissional_set.filter(status__in=[PraticaProfissional.STATUS_CONCLUIDO, PraticaProfissional.STATUS_RESCINDIDO])

    def get_aprendizagens_em_andamento(self):
        return self.aprendizagem_set.exclude(data_encerramento__isnull=False)

    def get_aprendizagens_encerradas(self):
        return self.aprendizagem_set.filter(data_encerramento__isnull=False)

    def get_participacoes_em_bancas(self):
        projetos_presididos = []
        for projeto in ProjetoFinal.objects.filter(presidente=self).order_by('-data_defesa'):
            projetos_presididos.append(projeto)
        projetos_examinados = []
        for projeto in ProjetoFinal.objects.filter(examinador_interno__pk=self.vinculo.pessoa.pk):
            projeto.examinador = 'examinador_interno'
            projetos_examinados.append(projeto)
        for projeto in ProjetoFinal.objects.filter(examinador_externo__pk=self.vinculo.pessoa.pk):
            projeto.examinador = 'examinador_externo'
            projetos_examinados.append(projeto)
        for projeto in ProjetoFinal.objects.filter(terceiro_examinador__pk=self.vinculo.pessoa.pk):
            projeto.examinador = 'terceiro_examinador'
            projetos_examinados.append(projeto)
        return projetos_presididos, projetos_examinados

    def get_vinculo_diarios(self, ano_letivo, periodo_letivo, fic=None, ativo=None, financiamento_externo=None):
        from edu.models import CursoCampus, Modalidade

        professor_diarios = self.professordiario_set.filter(diario__ano_letivo__ano=ano_letivo, diario__periodo_letivo=periodo_letivo) | self.professordiario_set.filter(
            diario__ano_letivo__ano=ano_letivo, diario__turma__curso_campus__periodicidade=CursoCampus.PERIODICIDADE_ANUAL
        )

        if periodo_letivo == 2:
            professor_diarios = professor_diarios.exclude(
                diario__calendario_academico__qtd_etapas=4, diario__componente_curricular__qtd_avaliacoes=2, diario__segundo_semestre=False
            )
        else:
            professor_diarios = professor_diarios.exclude(
                diario__calendario_academico__qtd_etapas=4, diario__componente_curricular__qtd_avaliacoes=2, diario__segundo_semestre=True
            )

        if ativo is not None:
            professor_diarios = professor_diarios.filter(ativo=ativo)

        if financiamento_externo is not None:
            professor_diarios = professor_diarios.filter(financiamento_externo=financiamento_externo)

        if fic is not None:
            if fic:
                professor_diarios = professor_diarios.filter(diario__turma__curso_campus__modalidade=Modalidade.FIC)
            else:
                professor_diarios = professor_diarios.exclude(diario__turma__curso_campus__modalidade=Modalidade.FIC)

        return professor_diarios

    def get_vinculos_minicurso(self, ano_letivo, periodo_letivo):
        return self.professorminicurso_set.filter(turma_minicurso__ano_letivo__ano=ano_letivo, turma_minicurso__periodo_letivo=periodo_letivo)

    def get_vinculos_diarios_especiais(self, ano_letivo, periodo_letivo, is_cap=None):
        if is_cap is None:
            return self.diarioespecial_set.filter(ano_letivo__ano=ano_letivo, periodo_letivo=periodo_letivo)
        else:
            return self.diarioespecial_set.filter(ano_letivo__ano=ano_letivo, periodo_letivo=periodo_letivo, is_centro_aprendizagem=is_cap)
