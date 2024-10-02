import datetime

from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Sum

from djtools.templatetags.filters import format_
from djtools.testutils import running_tests
from djtools.utils import tl
from ppe.managers import TurmaPPEManager
from ppe.models import LogPPEModel
from djtools.db import models


class Turma(LogPPEModel):
    SEARCH_FIELDS = ['codigo', 'descricao']

    # Manager
    objects = TurmaPPEManager()
    # locals = TurmaLocalManager()
    # Fields
    grupo = models.CharFieldPlus(verbose_name='Grupo')
    codigo = models.CharFieldPlus(verbose_name='Código')
    sequencial = models.PositiveIntegerField(default=1)
    formacao = models.ForeignKeyPlus('ppe.FormacaoPPE', null=True)

    class Meta:
        verbose_name = 'Turma'
        verbose_name_plural = 'Turmas'

        permissions = (('gerar_turmas', 'Gerar Turmas'),)
        ordering = ('codigo',)

    def __str__(self):
        return '{}'.format(self.codigo)

    def get_absolute_url(self):
        return '/ppe/turma/{:d}/'.format(self.pk)

    @staticmethod
    @transaction.atomic
    def gerar_turmas( grupo, qtd_tumas, vagas, formacao,cursos, commit):
        from ppe.models import CursoTurma

        todas_turmas = []
        lista_cursos_geral = []

        sid = transaction.savepoint()

        turma_params = dict(grupo=grupo, formacao=formacao)
        qs_turma = Turma.objects.filter(**turma_params)
        ultimo_sequencial = qs_turma.exists() and qs_turma.order_by('-sequencial')[0].sequencial or 0

        turmas = []
        for turma in qs_turma:
            turma.criada = False
            turmas.append(turma)
            todas_turmas.append(turma)

        for i in range(len(turmas), int(qtd_tumas)):
            ultimo_sequencial += 1
            turma_params.update(sequencial=ultimo_sequencial)
            turma = Turma.objects.create(**turma_params)
            turma.criada = True
            turmas.append(turma)
            todas_turmas.append(turma)

        lista_cursos = []

        for turma in turmas:
            # turma.save()

            turma.cursos = []
            for curso_formacao in cursos.all():
                dict_curso_turma = dict(
                    turma=turma,
                    curso_formacao=curso_formacao,
                    estrutura_curso=curso_formacao.estrutura,
                )
                curso_turma_set = CursoTurma.objects.filter(**dict_curso_turma)
                if curso_turma_set.count() > 0:
                    curso_formacao = curso_turma_set[0]
                    curso_formacao.criado = False
                else:
                    dict_curso_turma.update(quantidade_vagas=vagas)
                    curso_formacao = CursoTurma(**dict_curso_turma)
                    curso_formacao.criado = True
                    lista_cursos.append(curso_formacao)
                turma.cursos.append(curso_formacao)

            lista_cursos_geral += lista_cursos

        if commit:
            for turma in todas_turmas:
                for curso in turma.cursos:
                    curso.save()
            transaction.savepoint_commit(sid)
        else:
            transaction.savepoint_rollback(sid)

        return todas_turmas


    def save(self, *args, **kwargs):
        self.codigo = f'{self.grupo}{self.sequencial}'
        super(self.__class__, self).save(*args, **kwargs)

    def pode_ser_excluido(self):
        return True

    def remover_trabalhadores_educandos(self, tes_turma, user):
        from ppe.models import MatriculaCursoTurma

        for te in tes_turma:
                for md in te.matriculacursoturma_set.filter(curso_turma__turma=self, situacao=MatriculaCursoTurma.SITUACAO_CURSANDO):
                    if md.pode_ser_excluido_do_curso_turma(user):
                        md.delete()
                te.turma = None
                te.save()
    @transaction.atomic
    def matricular_trabalhadores_educando(self, trabalhadores_educando):
        from ppe.models import MatriculaCursoTurma
        for trabalhador_educando in trabalhadores_educando:
            cursos_turma = self.cursoturma_set.all()
            for curso_turma in cursos_turma:
                if trabalhador_educando.pode_ser_matriculado_no_curso_turma(curso_turma)[0]:
                    MatriculaCursoTurma.objects.get_or_create(trabalhador_educando=trabalhador_educando, curso_turma=curso_turma)

            trabalhador_educando.turma = self
            trabalhador_educando.save()
    def get_trabalhadores_educando_apto_matricula(self, ignorar_matriculados=True, apenas_ingressantes=False):

        from ppe.models import TrabalhadorEducando

        qs = TrabalhadorEducando.objects.filter(formacao__isnull= False)
        if ignorar_matriculados:
            qs = qs.filter(turma__isnull=True)
        return qs
    
    def get_trabalhadores_educando_relacionados(self, diarios):
        from ppe.models import MatriculaCursoTurma
        qs = MatriculaCursoTurma.objects.filter(curso_turma__turma=self, curso_turma__in=diarios).distinct()
        return qs.distinct().order_by('trabalhador_educando__pessoa_fisica__nome', 'trabalhador_educando__pk').select_related('trabalhador_educando__pessoa_fisica')
    #     from ppe.models import CursoTurma
    #     qs = CursoTurma.objects.filter(turma=self)
    #     return qs.distinct().order_by('turma__trabalhadoreducando_set__pessoa_fisica__nome', 'turma__trabalhadoreducando_set__pk')#.select_related('turma__trabalhadoreducando__pessoa_fisica')


class TutorTurma(LogPPEModel):

    # Managers
    objects = models.Manager()

    turma = models.ForeignKeyPlus('ppe.Turma', verbose_name='Turma')
    tutor = models.ForeignKeyPlus('comum.Bolsista', verbose_name='Tutor')
    ativo = models.BooleanField(verbose_name='Ativo', default=True)

    class Meta:
        verbose_name = 'Vínculo de Tutor em uma Turma'
        verbose_name_plural = 'Vínculos de Tutor em uma Turma'

    def __str__(self):
        return 'Vínculo do Tutor {} na turma  {}'.format(self.tutor, self.turma.codigo)

    def save(self, *args, **kwargs):
        super().save()
        grupo = Group.objects.get(name='Tutor PPE')
        self.tutor.user.groups.add(grupo)
    def can_delete(self, user=None):
        return True

class ApoiadorTurma(LogPPEModel):

    # Managers
    objects = models.Manager()

    turma = models.ForeignKeyPlus('ppe.Turma', verbose_name='Turma')
    apoiador = models.ForeignKeyPlus('comum.Bolsista', verbose_name='Apoiador(a) Pedagógico')
    ativo = models.BooleanField(verbose_name='Ativo', default=True)

    class Meta:
        verbose_name = 'Vínculo de Apoiador Pedagógico em uma Turma'
        verbose_name_plural = 'Vínculos de Apoiadores Pedagógico em uma Turma'

    def __str__(self):
        return 'Vínculo do Apoiador Pedagógico {} na turma  {}'.format(self.tutor, self.turma.codigo)

    def save(self, *args, **kwargs):
        grupo = Group.objects.get(name='Apoiador(a) Pedagógico PPE')
        self.apoiador.user.groups.add(grupo)
        super().save()
    def can_delete(self, user=None):
        return True