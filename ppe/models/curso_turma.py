import datetime
from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Sum, Max
from django.db.models.functions import Coalesce

from djtools.db import models
from djtools.templatetags.filters import format_
from djtools.testutils import running_tests
from djtools.utils import tl, mask_nota
from ppe.models import LogPPEModel, TutorTurma
from suap import settings


class CursoTurma(LogPPEModel):
    SEARCH_FIELDS = ['curso_formacao__curso__descricao', 'id',]

    SITUACAO_ABERTO = 1
    SITUACAO_FECHADO = 2
    SITUACAO_CHOICES = [[SITUACAO_ABERTO, 'Aberto'], [SITUACAO_FECHADO, 'Fechado']]

    POSSE_REGISTRO_ESCOLAR = 0
    POSSE_TUTOR = 1
    POSSE_CHOICES = [[POSSE_TUTOR, 'Tutor'], [POSSE_REGISTRO_ESCOLAR, 'Coordenador']]

    ETAPA_1 = 1
    ETAPA_2 = 2
    ETAPA_3 = 3
    ETAPA_4 = 4
    ETAPA_5 = 5
    ETAPA_CHOICES = [[ETAPA_1, 'Etapa 1'], [ETAPA_2, 'Etapa 2'], [ETAPA_3, 'Etapa 3'], [ETAPA_4, 'Etapa 4'], [ETAPA_5, 'Etapa Final']]

    # Fields
    id = models.AutoField(verbose_name='Código', primary_key=True)
    turma = models.ForeignKeyPlus('ppe.Turma', verbose_name='Turma', on_delete=models.CASCADE)
    curso_formacao = models.ForeignKeyPlus('ppe.CursoFormacaoPPE', verbose_name='Curso', null=True, on_delete=models.CASCADE)
    quantidade_vagas = models.PositiveIntegerField(verbose_name='Quantidade de Vagas', default=0)
    situacao = models.PositiveIntegerField(verbose_name='Situação', choices=SITUACAO_CHOICES, default=SITUACAO_ABERTO)
    estrutura_curso = models.ForeignKeyPlus('ppe.EstruturaCurso', verbose_name='Estrutura de Curso', on_delete=models.CASCADE)
    # calendario_academico = models.ForeignKeyPlus('edu.CalendarioAcademico', verbose_name='Calendário Acadêmico', on_delete=models.CASCADE)
    descricao_dinamica = models.CharFieldPlus('Descrição Dinâmica', null=True, blank=True)

    # Moodle
    integracao_com_moodle = models.BooleanField('Integração com o Moodle', default=False)
    url_moodle = models.CharFieldPlus('URL do Moodle', null=True, blank=True)
    nome_breve_curso_moodle = models.CharFieldPlus('Nome breve do curso', null=True, blank=True)

    # url_ambiente_virtual = models.CharFieldPlus('URL do Ambiente Virtual', null=True, blank=True, help_text='Endereço da plataforma através da qual o professor poderá interagir com seus alunos durante a realização das aulas ou em atividades programadas')
    posse_etapa_1 = models.PositiveIntegerField(choices=POSSE_CHOICES, default=POSSE_TUTOR)

    data_inicio_etapa_1 = models.DateFieldPlus(verbose_name='Início', null=True, blank=True, help_text='Data de início da primeira etapa')
    data_fim_etapa_1 = models.DateFieldPlus(verbose_name='Fim', null=True, blank=True, help_text='Data de encerramento da primeira etapa')

    posse_etapa_5 = models.PositiveIntegerField(choices=POSSE_CHOICES, default=POSSE_TUTOR)

    data_inicio_prova_final = models.DateFieldPlus(verbose_name='Início da Prova Final', null=True, blank=True)
    data_fim_prova_final = models.DateFieldPlus(verbose_name='Encerramento da Prova Final', null=True, blank=True)

    class Meta:
        verbose_name = 'Diário de Curso'
        verbose_name_plural = 'Diários de Cursos'

        permissions = (
            ('lancar_nota_curso_turma', 'Pode lançar nota em Cursos'),
            ('reabrir_cursoturma', 'Pode reabri Cursos'),
            ('emitir_boletins', 'Pode emitir boletins dos Cursos'),
            ('mudar_posse_curso_turma', 'Pode mudar posse de Diário do cursos'),

        )

    def __str__(self):
        curso = '{} - [{} h ]'.format(
            self.curso_formacao.curso.descricao,
            self.curso_formacao.curso.ch_total,
        )
        if self.id:
            descricao = '{} - {}'.format(self.id, curso)
        else:
            descricao = str(self.curso_formacao.curso.descricao)
        return descricao

    def get_matriculas_diario_por_polo(self, pk=None):
        lista = []

        qs = self.matriculacursoturma_set.all()
        if qs.exists():
            if not running_tests():
                qs = qs.order_by('trabalhador_educando__pessoa_fisica__nome')
            lista.append(qs)

        return lista

    def is_aberto(self):
        return True

    def pode_ser_excluido(self):
        return not self.matriculacursoturma_set.exists()

    def get_trabalhadores_educando_ativos(self):
        return self.matriculacursoturma_set.exclude(
            situacao__in=(MatriculaCursoTurma.SITUACAO_CANCELADO,MatriculaCursoTurma.SITUACAO_TRANCADO)
        )


    def get_quantidade_trabalhadores_educando_ativos(self):
        return self.get_trabalhadores_educando_ativos().count()

    def get_lista_etapas(self):
        if self.curso_formacao.qtd_avaliacoes == 0:
            return [1]
        return list(range(1, self.curso_formacao.qtd_avaliacoes + 1))

    def etapas_anteriores_entegues(self, etapa):
        for num_etapa in self.get_lista_etapas() + [5]:
            if num_etapa < etapa:
                if getattr(self, 'posse_etapa_{}'.format(num_etapa)) != CursoTurma.POSSE_REGISTRO_ESCOLAR:
                    return False
        return True
    def get_num_etapa_posse_tutor(self):
        for num_etapa in self.get_lista_etapas() + [5]:
            if getattr(self, 'posse_etapa_{}'.format(num_etapa)) != CursoTurma.POSSE_REGISTRO_ESCOLAR:
                return num_etapa
        return 1

    def get_label_etapa(self, etapa):
        if etapa == 1:
            return self.get_numero_primeira_etapa()
        elif etapa == 5:
            return 'Final'
        else:
            return etapa
    def get_numero_primeira_etapa(self):
        result = '1'
        return result

    def em_posse_do_registro(self, etapa=None):
        retorno = True
        if etapa:
            retorno = getattr(self, 'posse_etapa_{}'.format(etapa)) == CursoTurma.POSSE_REGISTRO_ESCOLAR
        else:
            for etapa in list(range(1, self.curso_formacao.qtd_avaliacoes + 1)) + [5]:
                retorno = retorno and getattr(self, 'posse_etapa_{}'.format(etapa)) == CursoTurma.POSSE_REGISTRO_ESCOLAR
        return retorno

    def configuracao_avaliacao_1(self):
        try:
            try:
                return self._configuracao_avaliacao_1
            except AttributeError:
                self._configuracao_avaliacao_1 = self.configuracaoavaliacao_set.get(etapa=1)
                return self._configuracao_avaliacao_1
        except ConfiguracaoAvaliacao.DoesNotExist:
            return None

    def configuracao_avaliacao_2(self):
        try:
            try:
                return self._configuracao_avaliacao_2
            except AttributeError:
                self._configuracao_avaliacao_2 = self.configuracaoavaliacao_set.get(etapa=2)
                return self._configuracao_avaliacao_2
        except ConfiguracaoAvaliacao.DoesNotExist:
            return None

    def configuracao_avaliacao_3(self):
        try:
            try:
                return self._configuracao_avaliacao_3
            except AttributeError:
                self._configuracao_avaliacao_3 = self.configuracaoavaliacao_set.get(etapa=3)
                return self._configuracao_avaliacao_3
        except ConfiguracaoAvaliacao.DoesNotExist:
            return None

    def configuracao_avaliacao_4(self):
        try:
            try:
                return self._configuracao_avaliacao_4
            except AttributeError:
                self._configuracao_avaliacao_4 = self.configuracaoavaliacao_set.get(etapa=4)
                return self._configuracao_avaliacao_4
        except ConfiguracaoAvaliacao.DoesNotExist:
            return None

    def configuracao_avaliacao_5(self):
        try:
            try:
                return self._configuracao_avaliacao_5
            except Exception:
                self._configuracao_avaliacao_5 = self.configuracaoavaliacao_set.get(etapa=5)
                return self._configuracao_avaliacao_5
        except ConfiguracaoAvaliacao.DoesNotExist:
            return None

    def get_etapas(self):
        etapas = dict()
        etapas.update({1: {'posse': self.em_posse_do_registro(1), 'configuracao_avaliacao': self.configuracao_avaliacao_1, 'numero_etapa_exibicao': 1}})
        etapas.update({5: {'posse': self.em_posse_do_registro(5), 'configuracao_avaliacao': self.configuracao_avaliacao_5, 'numero_etapa_exibicao': 'Final'}})
        return etapas

    def get_inicio_etapa_1(self):
        inicio_etapa = self.data_inicio_etapa_1
        return inicio_etapa

    def get_fim_etapa_1(self):
        fim_etapa = self.data_inicio_etapa_1
        return fim_etapa

    def get_inicio_etapa_final(self):
        inicio_etapa = self.data_inicio_etapa_1
        return inicio_etapa

    def get_fim_etapa_final(self):
        fim_etapa = self.data_fim_etapa_1
        return fim_etapa

    def get_carga_horaria(self):
        return self.curso_formacao.curso.ch_total # ch_presencial

    def etapa_1_em_posse_do_registro(self):
        return getattr(self, 'posse_etapa_1') == CursoTurma.POSSE_REGISTRO_ESCOLAR

    def etapa_5_em_posse_do_registro(self):
        return getattr(self, 'posse_etapa_5') == CursoTurma.POSSE_REGISTRO_ESCOLAR

    def get_carga_horaria_maxima(self, relogio=False):
        if relogio:
            return int(self.curso_formacao.curso.ch_total)
        return int(self.curso_formacao.curso.ch_aula)

    def get_carga_horaria_cumprida_por_tipo(self, tipo, relogio=False):
        qs = Aula.objects.filter(curso_turma=self, data__lte=datetime.date.today(), tipo=tipo)
        return int((qs.aggregate(Sum('quantidade')).get('quantidade__sum') or 0))

    def get_carga_horaria_teorica_ministrada(self, relogio=False):
        return self.get_carga_horaria_cumprida_por_tipo(Aula.AULA, relogio=relogio)

    def get_carga_horaria_teorica_contabilizada(self, relogio=False):
        maxima = self.get_carga_horaria_maxima(relogio=relogio)
        if maxima is None or maxima > 0:
            ch = self.get_carga_horaria_teorica_ministrada(relogio=relogio)
            return ch if maxima is None or ch < maxima else maxima
        return 0

    def get_carga_horaria_cumprida(self):
        return (
            self.get_carga_horaria_teorica_contabilizada()

        )

    def get_aulas(self, etapa=None):
        qs = Aula.objects.filter(curso_turma=self).order_by('-data')#.select_related('professor_diario')
        if etapa:
            return qs.filter(etapa=etapa)
        return qs

    def get_aulas_etapa_1(self):
        return self.get_aulas(1)


    def save(self, *args, **kwargs):
        from ppe.models import CursoFormacaoPPE
        pk = self.pk
        qtd_etapas = self.curso_formacao.qtd_avaliacoes
        if not self.pk:
            if self.curso_formacao.tipo == CursoFormacaoPPE.TIPO_TRANSVERSAIS:
                self.nome_breve_curso_moodle = f'{self.curso_formacao.curso.codigo} - {self.turma}'
            else:
                self.nome_breve_curso_moodle = f'{self.curso_formacao.curso.codigo}'

        if not pk:
            if qtd_etapas <= 2:
                self.posse_etapa_4 = CursoTurma.POSSE_REGISTRO_ESCOLAR
                self.posse_etapa_3 = CursoTurma.POSSE_REGISTRO_ESCOLAR
            if qtd_etapas < 2:
                self.posse_etapa_2 = CursoTurma.POSSE_REGISTRO_ESCOLAR

        super().save(*args, **kwargs)

        etapas = list(range(1, self.curso_formacao.qtd_avaliacoes + 1))
        etapas = etapas and etapas + [5] or []

        for etapa in etapas:
            attr = 'configuracao_avaliacao_{}'.format(etapa)
            if not pk and not getattr(self, attr)() and not hasattr(self, 'dividindo'):
                configuracao_avaliacao = ConfiguracaoAvaliacao.objects.get(pk=1)
                item_configuracao_avaliacao = configuracao_avaliacao.itemconfiguracaoavaliacao_set.first()

                configuracao_avaliacao.pk = None
                configuracao_avaliacao.curso_turma = self
                configuracao_avaliacao.etapa = etapa
                configuracao_avaliacao.save()

                item_configuracao_avaliacao.pk = None
                item_configuracao_avaliacao.configuracao_avaliacao = configuracao_avaliacao
                item_configuracao_avaliacao.save()

    def registrar_notas_moodle(self, notas):

        for nota in notas:

            if nota['codigo_nota'] and nota['matricula_aluno']:

                qs_matricula_curso_turma = MatriculaCursoTurma.objects.filter(curso_turma=self,
                                                                              trabalhador_educando__pessoa_fisica__user__username=
                                                                              nota['matricula_aluno'])

                if qs_matricula_curso_turma.exists():
                    qs_nota_avaliacao = NotaAvaliacao.objects.filter(matricula_curso_turma=qs_matricula_curso_turma[0],
                                                                     item_configuracao_avaliacao__descricao=nota['descricao_nota'],
                                                                     item_configuracao_avaliacao__configuracao_avaliacao__etapa=1)
                    if qs_nota_avaliacao.exists():
                        nota_avaliacao = qs_nota_avaliacao[0]
                        nota_avaliacao.nota = float(nota['nota_aluno'])
                        nota_avaliacao.save()
                        nota_avaliacao.matricula_curso_turma.registrar_nota_etapa(
                            nota_avaliacao.item_configuracao_avaliacao.configuracao_avaliacao.etapa)


class Aula(LogPPEModel):
    ETAPA_1 = 1
    ETAPA_5 = 5
    ETAPA_CHOICES = [[ETAPA_1, 'Primeira'], [ETAPA_5, 'Final']]

    AULA = 1
    PRATICA = 2

    TIPO_CHOICES = [
        [AULA, 'Teórica'],
        [PRATICA, 'Prática'],
    ]

    curso_turma = models.ForeignKeyPlus(CursoTurma, verbose_name='Curso Turma')
    etapa = models.PositiveIntegerField(verbose_name='Etapa', default=1, choices=ETAPA_CHOICES)
    quantidade = models.PositiveIntegerField(default=1, help_text='Quantidade de aulas ministradas')
    # plano de retomada de aulas em virtude da pandemia (COVID19)
    url = models.CharFieldPlus(verbose_name='URL da Aula', null=True, blank=True)
    data = models.DateFieldPlus(verbose_name='Data')
    conteudo = models.TextField('Conteúdo')
    tipo = models.PositiveIntegerFieldPlus(verbose_name='Tipo', choices=TIPO_CHOICES, null=True, default=AULA)

    class Meta:
        verbose_name = 'Aula'
        verbose_name_plural = 'Aulas'
        ordering = ('etapa', 'data')

    def is_ministrada(self):
        return self.data <= datetime.date.today()

    def __str__(self):
        return 'Aula do diário de curso  {}'.format(self.curso_turma)

    def get_curso_turma(self):
        return self.curso_turma

    def can_change(self, user):
        user = user or tl.get_user()
        em_posse_do_registro = self.curso_turma.em_posse_do_registro(self.etapa)
        if em_posse_do_registro:
            return False
        etapa = self.etapa == 5 and 'final' or self.etapa
        inicio = getattr(self.professor_diario, "data_inicio_etapa_{}".format(etapa))
        fim = getattr(self.professor_diario, "data_fim_etapa_{}".format(etapa))
        if inicio and fim and self.data and self.data >= inicio and self.data <= fim:
            return True
        return False

    def clean(self):
        adicional = self.quantidade
        if self.pk:
            adicional -= Aula.objects.get(pk=self.pk).quantidade
        if self.quantidade < 0:
            raise ValidationError('A quantidade de horas deve ser um número inteiro positivo')
        if (
                self.data
                and hasattr(self, 'professor_diario')
                and (
                self.professor_diario.diario.calendario_academico.get_data_inicio_letivo() > self.data or self.data > self.professor_diario.diario.get_fim_etapa_final())
        ):
            raise ValidationError(
                'As aulas devem estar no intervalo de {} a {}'.format(
                    format_(self.professor_diario.diario.calendario_academico.get_data_inicio_letivo()),
                    format_(self.professor_diario.diario.get_fim_etapa_final())
                )
            )
        if not self.professor_diario_id:
            raise ValidationError('A aula precisa estar atribuída a um professor.')
        user = tl.get_user()
        if self.professor_diario.diario.is_professor_diario(user):
            if self.professor_diario.diario.em_posse_do_registro(self.etapa):
                raise ValidationError('A etapa precisa estar em posse do professor.')
            if not self.can_change(user):
                raise ValidationError('Verifique se a data da aula está no período de posse da etapa selecionada.')

    def pode_registrar_chamada(self, user):
        tutor_turma = TutorTurma.objects.filter(tutor__vinculo__user=user,
                                                         turma_id=self.curso_turma.turma.pk).first()
        if tutor_turma:
            etapa = self.etapa == 5 and 'final' or self.etapa
            inicio = getattr(tutor_turma, "data_inicio_etapa_{}".format(etapa))
            fim = getattr(tutor_turma, "data_fim_etapa_{}".format(etapa))
            if inicio and fim and self.data and self.data >= inicio and self.data <= fim:
                return True
        return False

class SituacaoMatricula(LogPPEModel):
    MATRICULADO = 1
    TRANCADO = 2
    CONCLUIDO = 6
    FALECIDO = 7
    AFASTADO = 8
    EVASAO = 9
    CANCELADO = 10
    CANCELAMENTO_COMPULSORIO = 20
    TRANCADO_VOLUNTARIAMENTE = 99

    SITUACOES_INATIVAS_PARA_EXCLUSAO_TURMA = [
        TRANCADO,
        EVASAO,
        CANCELADO,
        CANCELAMENTO_COMPULSORIO,
        TRANCADO_VOLUNTARIAMENTE,
    ]

    codigo_academico = models.IntegerField(null=True)
    descricao = models.CharFieldPlus('Descrição', unique=True)
    ativo = models.BooleanField(verbose_name='Ativo', default=False)

    class Meta:
        verbose_name = 'Situação de Matrícula'
        verbose_name_plural = 'Situações de Matrículas'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/ppe/visualizar/edu/situacaomatricula/{}/'.format(self.pk)


class MatriculaCursoTurma(LogPPEModel):
    SITUACAO_CURSANDO = 1
    SITUACAO_APROVADO = 2
    SITUACAO_REPROVADO = 3
    SITUACAO_PROVA_FINAL = 4
    SITUACAO_REPROVADO_POR_FALTA = 5
    SITUACAO_TRANCADO = 6
    SITUACAO_CANCELADO = 7
    SITUACAO_DISPENSADO = 8
    SITUACAO_PENDENTE = 9

    SITUACAO_CHOICES = [
        [SITUACAO_CURSANDO, 'Cursando'],
        [SITUACAO_APROVADO, 'Aprovado'],
        [SITUACAO_REPROVADO, 'Reprovado'],
        [SITUACAO_PROVA_FINAL, 'Prova Final'],
        [SITUACAO_REPROVADO_POR_FALTA, 'Reprovado por falta'],
        [SITUACAO_TRANCADO, 'Trancado'],
        [SITUACAO_CANCELADO, 'Cancelado'],
        [SITUACAO_DISPENSADO, 'Dispensado'],
        [SITUACAO_PENDENTE, 'Pendente'],
    ]

    # Managers
    objects = models.Manager()
    # Fields
    trabalhador_educando = models.ForeignKeyPlus('ppe.TrabalhadorEducando')
    curso_turma = models.ForeignKeyPlus('ppe.CursoTurma')

    nota_1 = models.NotaField(verbose_name='N1', null=True)
    nota_final = models.NotaField(verbose_name='NAF', null=True)
    situacao = models.PositiveIntegerField(choices=SITUACAO_CHOICES, default=SITUACAO_CURSANDO, verbose_name='Situação')

    SEARCH_FIELDS = [
        'trabalhador_educando__matricula',
        'trabalhador_educando__pessoa_fisica__nome',
        'curso_turma__curso_formacao__curso__codigo',
        'curso_turma__id',
        'curso_turma__curso_formacao__curso__descricao',
    ]
    class Meta:
        verbose_name = 'Matrícula em Turma'
        verbose_name_plural = 'Matrículas em Turma'
        ordering = ('trabalhador_educando__pessoa_fisica__nome',)

    def habilitada(self):
        return self.situacao not in [MatriculaCursoTurma.SITUACAO_TRANCADO, MatriculaCursoTurma.SITUACAO_TRANSFERIDO,
                                     MatriculaCursoTurma.SITUACAO_CANCELADO, MatriculaCursoTurma.SITUACAO_PENDENTE]

    def save(self, *args, **kwargs):

        pk = self.pk
        super().save(*args, **kwargs)
        if not pk:
            self.criar_registros_notas()

    def delete(self, *args, **kwargs):
      super().delete(*args, **kwargs)

    def criar_registros_notas(self):
        from ppe.models import ItemConfiguracaoAvaliacao, ConfiguracaoAvaliacao

        etapas = list(range(1, self.curso_turma.curso_formacao.qtd_avaliacoes + 1))
        etapas = etapas and etapas + [5] or []
        for etapa in etapas:
            if not self.notaavaliacao_set.filter(
                    item_configuracao_avaliacao__configuracao_avaliacao__etapa=etapa).exists():
                configuracao_avaliacao, _ = ConfiguracaoAvaliacao.objects.get_or_create(curso_turma=self.curso_turma, etapa=etapa)
                if not configuracao_avaliacao.itemconfiguracaoavaliacao_set.exists():
                    item_configuracao_avaliacao = ItemConfiguracaoAvaliacao.objects.create(
                        configuracao_avaliacao=configuracao_avaliacao, sigla='A{}'.format(etapa))
                    for matricula_curso_turma in self.curso_turma.matriculacursoturma_set.all():
                        matricula_curso_turma.criar_registros_notas_etapa(etapa, [item_configuracao_avaliacao])
                self.criar_registros_notas_etapa(etapa, configuracao_avaliacao.itemconfiguracaoavaliacao_set.all())

    def criar_registros_notas_etapa(self, etapa, itens_configuracao_avaliacao):
        from ppe.models import NotaAvaliacao

        for item_configuracao_avaliacao in itens_configuracao_avaliacao:
            qs = NotaAvaliacao.objects.filter(matricula_curso_turma=self,
                                              item_configuracao_avaliacao=item_configuracao_avaliacao)
            if not qs.exists():
                NotaAvaliacao.objects.create(matricula_curso_turma=self,
                                             item_configuracao_avaliacao=item_configuracao_avaliacao, nota=None)
        self.registrar_nota_etapa(etapa)

    def is_carga_horaria_diario_fechada(self):
        return True

    def registrar_nota_etapa(self, etapa, considerar_nota_vazia=False):
        from ppe.models import NotaAvaliacao, ConfiguracaoAvaliacao

        if not self.curso_turma.curso_formacao.qtd_avaliacoes:
            return
        qs = NotaAvaliacao.objects.filter(matricula_curso_turma=self,
                                          item_configuracao_avaliacao__configuracao_avaliacao__etapa=etapa)
        id_configuracao_avaliacao = qs.values_list('item_configuracao_avaliacao__configuracao_avaliacao',
                                                   flat=True).first()
        configuracao_avaliacao = ConfiguracaoAvaliacao.objects.filter(pk=id_configuracao_avaliacao).first()
        # se a forma de cálculo for a maior nota ou soma simples
        if configuracao_avaliacao and configuracao_avaliacao.forma_calculo in (
        ConfiguracaoAvaliacao.FORMA_CALCULO_MAIOR_NOTA, ConfiguracaoAvaliacao.FORMA_CALCULO_SOMA_SIMPLES):
            # pelo menos uma nota deve ter sido lançada
            notas_foram_lancadas = qs.filter(nota__isnull=False).exists()
        else:
            # senão todas as notas devem ter sido lançadas
            notas_foram_lancadas = not qs.filter(nota__isnull=True).exists()
        if not notas_foram_lancadas and not considerar_nota_vazia:
            resultado = None
        else:
            resultado = self.calcular_media_etapa(qs, etapa)
        attr = 'nota_{}'.format(int(etapa) == 5 and 'final' or etapa)
        setattr(self, attr, resultado)
        super().save()


    def get_notas_etapa(self, etapa):
        from ppe.models import NotaAvaliacao

        return (
            NotaAvaliacao.objects.filter(matricula_curso_turma=self,
                                         item_configuracao_avaliacao__configuracao_avaliacao__etapa=etapa)
            .order_by('item_configuracao_avaliacao__id')
            .select_related('item_configuracao_avaliacao', 'matricula_curso_turma',
                            'item_configuracao_avaliacao__configuracao_avaliacao')
        )

    def get_notas_etapa_1(self):
        return self.get_notas_etapa(1)

    def get_notas_etapa_5(self):
        return self.get_notas_etapa(5)


    def calcular_media_etapa(self, notas_avaliacao, etapa):
        from ppe.models import ConfiguracaoAvaliacao

        nota_avaliacao1 = notas_avaliacao.first()
        forma_calculo = False
        if nota_avaliacao1:
            configuracao_avaliacao = nota_avaliacao1.item_configuracao_avaliacao.configuracao_avaliacao
            forma_calculo = configuracao_avaliacao.forma_calculo

            if configuracao_avaliacao.maior_nota:
                notas_avaliacao = notas_avaliacao.exclude(id=notas_avaliacao.order_by(Coalesce('nota', 0).desc())[0].id)

            if configuracao_avaliacao.menor_nota:
                notas_avaliacao = notas_avaliacao.exclude(id=notas_avaliacao.order_by(Coalesce('nota', 0).asc())[0].id)

        # Cálculos
        media_etapa = None
        if forma_calculo == ConfiguracaoAvaliacao.FORMA_CALCULO_MEDIA_PONDERADA:
            soma = 0
            soma_pesos = 0
            for nota_avaliacao in notas_avaliacao:
                if nota_avaliacao.nota is None:
                    nota_avaliacao.nota = 0
                soma += nota_avaliacao.nota * nota_avaliacao.item_configuracao_avaliacao.peso
                soma_pesos += nota_avaliacao.item_configuracao_avaliacao.peso
            if soma is not None and soma_pesos > 0:
                media_etapa = float(soma) / soma_pesos

        if forma_calculo == ConfiguracaoAvaliacao.FORMA_CALCULO_MAIOR_NOTA:
            media_etapa = notas_avaliacao.aggregate(Max('nota')).get('nota__max')

        if forma_calculo == ConfiguracaoAvaliacao.FORMA_CALCULO_SOMA_SIMPLES:
            media_etapa = notas_avaliacao.aggregate(Sum('nota')).get('nota__sum')

        if forma_calculo == ConfiguracaoAvaliacao.FORMA_CALCULO_MEDIA_ARITMETICA:
            soma_notas = notas_avaliacao.aggregate(Sum('nota')).get('nota__sum')
            if soma_notas is not None:
                media_etapa = float(soma_notas) / notas_avaliacao.count()

        if forma_calculo == ConfiguracaoAvaliacao.FORMA_CALCULO_SOMA_DIVISOR:
            soma_notas = notas_avaliacao.aggregate(Sum('nota')).get('nota__sum')
            if soma_notas is not None:
                media_etapa = float(soma_notas) / configuracao_avaliacao.divisor

        if media_etapa is not None:
            return int(round(media_etapa))
        else:
            return 0

    def is_aprovado_sem_prova_final(self):
        """
        Este método retorna verdadeiro caso o aluno tenha alcançado a média através das avaliações regulares, ou seja, sem prova final.
        Caso o componente não possua avaliações, o método deverá retornar verdadeiro.
        """
        if self.realizou_todas_avaliacoes_regulares():
            if self.curso_turma.curso_formacao.qtd_avaliacoes == 0:
                return True
            else:
                return self.get_media_disciplina() >= self.curso_turma.curso_formacao.estrutura.media_aprovacao_sem_prova_final
        return False

    def realizou_avaliacao_final(self):
        """
        Este método retorna verdadeiro caso o valor da nota final seja diferente de nulo.
        """
        return self.nota_final is not None

    def is_em_prova_final(self):
        """
        Este método retorna verdadeiro se o aluno realizou todas as avaliações regulares e:
            a) Não esteja reprovado direto
            b) Não tenha sido aprovado direto
        """
        if self.realizou_todas_avaliacoes_regulares():
            return not self.is_aprovado_sem_prova_final()
        return False

    def get_nota_final(self):
        """
        Este método retorna a nota da avaliação final caso ela esteja registrada ou zero, caso contrário.
        """
        return self.nota_final or 0


    def get_nota_final_boletim(self):
        if self.curso_turma.configuracao_avaliacao_5() and self.curso_turma.configuracao_avaliacao_5().autopublicar or not self.curso_turma.posse_etapa_5:
            return mask_nota(self.nota_final)
        return None

    def get_media_disciplina_boletim(self):
        from ppe.models import ConfiguracaoAvaliacao

        qs = ConfiguracaoAvaliacao.objects.filter(curso_turma=self.curso_turma, autopublicar=False)
        if self.curso_turma.em_posse_do_registro() or not qs.exists():
            return mask_nota(self.get_media_disciplina())
        return None

    def get_media_final_disciplina_boletim(self):
        from ppe.models import ConfiguracaoAvaliacao

        qs = ConfiguracaoAvaliacao.objects.filter(curso_turma=self.curso_turma, autopublicar=False).exclude(etapa=5)
        if self.curso_turma.em_posse_do_registro() or not qs.exists():
            return self.get_media_final_disciplina_exibicao()
        return None

    def get_media_final_disciplina_exibicao(self):
        nota = self.get_media_final_disciplina()
        # if nota and self.curso_turma.curso_formacaor.avaliacao_por_conceito:
        #     return self.curso_turma.curso_formacao.estrutura.get_conceito(nota)
        # else:
        return mask_nota(nota)

    def get_media_final_disciplina(self):
        """
        Este método retorna a média da disciplina, incluindo a avaliação final, de acordo com o tipo e avaliação do curso.
        Até o momento, apenas cursos FIC foram implementados.

        O cálculo da média final da disciplina deve ser a maior nota dentre as notas listadas a seguir, conforme a Organização Didática (Página 61):

        a) Para componentes de uma avaliação
            1. Nota da primeira avaliação
            2. Nota da avaliação final
        b) Para componentes de duas avaliações
            1. Média aritimética entre a média da disciplina e a nota final
            2. Média ponderada entre a nota da primeira avaliação e a nota final com pesos 2 e 3 respectivamente.
            3. Média ponderada entre a nota final e a nota da segunda avaliação com pesos 2 e 3 respectivamente.
        c) Para componentes de quatro avaliações
            1. Média aritimética entre a média da disciplina e a nota final
            2. Média ponderada entre a nota final e as notas da segunda, terceira e quarta etapas com pesos 2, 2, 3 e 3 respectivamente.
            3. Média ponderada entre a nota da primeira etapa, a nota final e as notas da terceira e quarta etapas com pesos 2, 2, 3 e 3 respectivamente.
            4. Média ponderada entre as notas da primeira e segunda etapas, nota final e quarta etapa com pesos 2, 2, 3 e 3 respectivamente.
            5. Média ponderada entre as notas da primeira, segunda e terceira etapas e da nota final com pesos 2, 2, 3 e 3 respectivamente.
        """
        qtd_avaliacoes = self.curso_turma.curso_formacao.qtd_avaliacoes

        # a média final da disciplina deve retonar None caso alguma das notas esperadas não tenha sido registrada
        if not qtd_avaliacoes:
            return None

        if qtd_avaliacoes > 0:
            if self.nota_1 is None:
                return None
        elif qtd_avaliacoes > 1:
            if self.nota_1 is None or self.nota_2 is None:
                return None
        elif qtd_avaliacoes > 2:
            if self.nota_3 is None or self.nota_4 is None:
                return None

        if self.is_em_prova_final():

            if self.nota_final is None:
                return None

            notas = []
            if qtd_avaliacoes == 1:
                notas.append(self.get_nota_1())
                notas.append(self.get_nota_final())

            nota = Decimal('0')
            for n in notas:
                if n > nota:
                    nota = n
            return nota
        return self.get_media_disciplina()

    def get_situacao_diario_boletim(self):
        situacao = self.get_situacao_diario()
        if self.situacao == MatriculaCursoTurma.SITUACAO_CURSANDO:
            if situacao['rotulo'] == 'Pendente':
                situacao['rotulo'] = 'Cursando'
        return situacao

    def get_situacao_registrada_diario(self):
        """
        Este método retorna um dicionário contendo:
            a) uma descrição amigável para a situação computada
            b) o status, que corresonde a uma classe css utilizada no template
            c) a constante do choice definido para o field 'situacao' da classe

        A situação do diário não é calculada a partir das notas das avaliações e frequência, mas sim do valor atual do atributo 'situacao'.
        Caso deseje saber a situação do diário baseada nas notas e na frequência, o método 'self.get_situacao_diario()' deve ser utilizado.
        """
        if self.situacao == MatriculaCursoTurma.SITUACAO_CURSANDO:
            return dict(rotulo='Cursando', status='info', constant=MatriculaCursoTurma.SITUACAO_CURSANDO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_PROVA_FINAL:
            return dict(rotulo='Prova Final', status='alert', constant=MatriculaCursoTurma.SITUACAO_PROVA_FINAL)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_APROVADO:
            return dict(rotulo='Aprovado', status='success', constant=MatriculaCursoTurma.SITUACAO_APROVADO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_REPROVADO:
            return dict(rotulo='Reprovado', status='error', constant=MatriculaCursoTurma.SITUACAO_REPROVADO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_REPROVADO_POR_FALTA:
            return dict(rotulo='Reprov. por Falta', status='error', constant=MatriculaCursoTurma.SITUACAO_REPROVADO_POR_FALTA)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_TRANCADO:
            return dict(rotulo='Trancado', status='alert', constant=MatriculaCursoTurma.SITUACAO_TRANCADO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_TRANSFERIDO:
            return dict(rotulo='Transferido', status='alert', constant=MatriculaCursoTurma.SITUACAO_TRANSFERIDO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_CANCELADO:
            return dict(rotulo='Cancelado', status='alert', constant=MatriculaCursoTurma.SITUACAO_CANCELADO)


    def is_aprovado_em_prova_final(self):
        """
        Este método retorna verdadeiro se o aluno tiver atingido a média após realizar a avaliação final.
        É importante que ele seja chamado caso a condição definida em 'self.is_em_prova_final()' seja satisfeita
        """
        media_final_disciplina = self.get_media_final_disciplina()
        media_aprovacao_avaliacao_final = self.curso_turma.curso_formacao.estrutura.media_aprovacao_avaliacao_final
        if media_final_disciplina is not None and media_aprovacao_avaliacao_final is not None:
            return self.is_em_prova_final() and media_final_disciplina >= media_aprovacao_avaliacao_final
        return False

    def is_aprovado_por_nota(self):
        """
        Este método retorna verdadeiro caso o aluno tenha sido aprovado direto ou na prova final.
        """
        return self.is_aprovado_sem_prova_final() or self.is_aprovado_em_prova_final()

    def is_cursando(self):
        """
        Este método retorna verdadeiro caso o período não tenha sido fechado para o aluno.
        Quando o período está fechado, a situação do diário não pode ser 'cursando' e nem 'em prova final', ou seja,
        só pode ser 'aprovado', 'reprovado' ou 'reprovado por falta'.
        """
        return self.situacao == MatriculaCursoTurma.SITUACAO_CURSANDO or self.situacao == MatriculaCursoTurma.SITUACAO_PROVA_FINAL

    def is_cancelado(self):
        return self.situacao == MatriculaCursoTurma.SITUACAO_CANCELADO

    def exibe_no_boletim(self):
        return self.situacao != MatriculaCursoTurma.SITUACAO_TRANSFERIDO

    def is_aprovado(self):
        """
        Este método retorna verdadeiro caso o aluno tenha sido aprovado por nota e por frequência
        """
        return self.is_aprovado_por_nota() and self.is_aprovado_por_frequencia()

    def get_situacao_is_aprovado(self):
        return self.situacao == MatriculaCursoTurma.SITUACAO_APROVADO

    def registrar_situacao_se_aprovado(self):
        if self.is_aprovado() and self.situacao != MatriculaCursoTurma.SITUACAO_APROVADO:
            self.situacao = MatriculaCursoTurma.SITUACAO_APROVADO
            super().save()

    def get_nota_1(self):
        """
        Este método retorna a nota da avaliação 1 caso ela esteja registrada ou zero, caso contrário.
        """
        return self.nota_1 or 0

    def get_nota_1_boletim(self):
        if self.curso_turma.configuracao_avaliacao_1() and self.curso_turma.configuracao_avaliacao_1().autopublicar or not self.curso_turma.posse_etapa_1:
            return mask_nota(self.nota_1)
        return None

    def get_media_disciplina(self):
        """
        Este método retorna a média da disciplina, sem a avaliação final, de acordo com o tipo e avaliação do curso.
        Até o momento, apenas cursos FIC foram implementados.
        """

        media_disciplina = 0
        qtd_avaliacoes = self.curso_turma.curso_formacao.qtd_avaliacoes

        # a média da disciplina deve retonar None caso alguma das notas esperadas não tenha sido registrada
        if qtd_avaliacoes > 0:
            if self.nota_1 is None:
                return None

        if qtd_avaliacoes == 1:
            return self.get_nota_1()

        return media_disciplina

    def realizou_todas_avaliacoes_regulares(self):
        """
        Este método retorna verdadeiro se todas as avaliações (não importando a avaliação final), possuir um valor diferente de nulo.
        """
        qtd_avaliacoes = self.curso_turma.curso_formacao.qtd_avaliacoes
        if qtd_avaliacoes == 0:
            return True
        elif qtd_avaliacoes == 1:
            return self.nota_1 is not None
        return False

    def realizou_todas_avaliacoes(self):
        """
        Este método retorna verdadeiro se todas as avaliações, que necessitam ser feitas, possuir um valor diferente de nulo.
        O valor da avaliação só precisa ser observado se, e somente se, o aluno estiver em prova final.
        """
        if self.realizou_todas_avaliacoes_regulares():
            if self.is_em_prova_final():
                return self.realizou_avaliacao_final()
            return True
        return False

    def get_situacao_nota(self):
        """
        Este método retorna um dicionário contendo:
            a) uma descrição amigável para a situação computada
            b) o status, que corresonde a uma classe css utilizada no template
            c) a constante do choice definido para o field 'situacao' da classe

        A situação deve ser computada conforme a seguir:
            Se o critério de avaliacão do curso for por frequência, a situação será 'Aprovado'
            Senão,
                Se o aluno realizou todas as avaliações regulares
                    Se o aluno estiver aprovado direto, a situação será 'Aprovado'
                    Senão, se estiver reprovado direto, a situação será 'Reprovado'
                    Senão, se realizou a avaliação final
                        Se estiver aprovado em prova final, a situação será 'Aprovado'
                        Senão a situação será 'Reprovado'
                    Senão, a situação será 'Prova Final'
                Senão, a situação será 'Pendente'
        """
        from ppe.models import EstruturaCurso

        if self.curso_turma.curso_formacao.estrutura.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_FREQUENCIA:
            return dict(rotulo='Aprovado', status='success', constant=MatriculaCursoTurma.SITUACAO_APROVADO)
        else:
            if self.realizou_todas_avaliacoes_regulares():
                if self.is_aprovado_sem_prova_final():
                    return dict(rotulo='Aprovado', status='success', constant=MatriculaCursoTurma.SITUACAO_APROVADO)
                else:
                    if self.realizou_avaliacao_final():
                        if self.is_aprovado_em_prova_final():
                            return dict(rotulo='Aprovado', status='success', constant=MatriculaCursoTurma.SITUACAO_APROVADO)
                        else:
                            return dict(rotulo='Reprovado', status='error', constant=MatriculaCursoTurma.SITUACAO_REPROVADO)
                    else:
                        return dict(rotulo='Prova Final', status='alert', constant=MatriculaCursoTurma.SITUACAO_PROVA_FINAL)
            else:

                return dict(rotulo='Cursando', status='info', constant=MatriculaCursoTurma.SITUACAO_CURSANDO)

    def registrar_nota_etapa(self, etapa, considerar_nota_vazia=False):
        from ppe.models import NotaAvaliacao, ConfiguracaoAvaliacao

        if not self.curso_turma.curso_formacao.qtd_avaliacoes:
            return
        qs = NotaAvaliacao.objects.filter(matricula_curso_turma=self, item_configuracao_avaliacao__configuracao_avaliacao__etapa=etapa)
        id_configuracao_avaliacao = qs.values_list('item_configuracao_avaliacao__configuracao_avaliacao', flat=True).first()
        configuracao_avaliacao = ConfiguracaoAvaliacao.objects.filter(pk=id_configuracao_avaliacao).first()
        # se a forma de cálculo for a maior nota ou soma simples
        if configuracao_avaliacao and configuracao_avaliacao.forma_calculo in (ConfiguracaoAvaliacao.FORMA_CALCULO_MAIOR_NOTA, ConfiguracaoAvaliacao.FORMA_CALCULO_SOMA_SIMPLES):
            # pelo menos uma nota deve ter sido lançada
            notas_foram_lancadas = qs.filter(nota__isnull=False).exists()
        else:
            # senão todas as notas devem ter sido lançadas
            notas_foram_lancadas = not qs.filter(nota__isnull=True).exists()
        if not notas_foram_lancadas and not considerar_nota_vazia:
            resultado = None
        else:
            resultado = self.calcular_media_etapa(qs, etapa)
        attr = 'nota_{}'.format(int(etapa) == 5 and 'final' or etapa)
        setattr(self, attr, resultado)
        super().save()

    def get_situacao_diario(self, ignorar_fechamento_carga_horaria=False, zerar_avaliacoes_nao_realizadas=False):
        """
        Este método retorna um dicionário contendo:
            a) uma descrição amigável para a situação computada
            b) o status, que corresonde a uma classe css utilizada no template
            c) a constante do choice definido para o field 'situacao' da classe
        """
        from ppe.models import EstruturaCurso


        if self.situacao == MatriculaCursoTurma.SITUACAO_APROVADO:
            return dict(rotulo='Aprovado', status='success', constant=MatriculaCursoTurma.SITUACAO_APROVADO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_REPROVADO:
            return dict(rotulo='Reprovado', status='error', constant=MatriculaCursoTurma.SITUACAO_REPROVADO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_REPROVADO_POR_FALTA:
            return dict(rotulo='Reprov. por Falta', status='error', constant=MatriculaCursoTurma.SITUACAO_REPROVADO_POR_FALTA)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_PENDENTE:
            return dict(rotulo='Pendente', status='info', constant=MatriculaCursoTurma.SITUACAO_PENDENTE)

        # Caso contrário, a situação é computada em tempo de execução a partir das notas da avaliações e da frequência

        nota_1 = self.nota_1
        nota_final = self.nota_final

        # Se o parâmetro 'zerar_avaliacoes_nao_realizadas' for verdadeiro, é necessário identificar as notas que estão nulas para que depois sejam substituídas novamente
        if zerar_avaliacoes_nao_realizadas:
            if not self.nota_1:
                self.nota_1 = 0
            if self.is_em_prova_final():
                if not self.nota_final:
                    self.nota_final = 0

        # o período do aluno está aberto
        if self.situacao == MatriculaCursoTurma.SITUACAO_CURSANDO:
            # se todas as aulas já foram registradas
            if ignorar_fechamento_carga_horaria:
                # caso a avaliação seja por nota
                if self.curso_turma.estrutura.criterio_avaliacao == EstruturaCurso.CRITERIO_AVALIACAO_NOTA:
                    # se o componente requer nota
                    if self.curso_turma.curso_formacao.qtd_avaliacoes > 0:
                        # se todas as notas tiverem sido lançadas
                        if self.realizou_todas_avaliacoes():
                            if self.curso_turma.estrutura.reprovacao_por_falta_disciplina and not self.is_aprovado_por_frequencia():
                                d = dict(rotulo='Reprov. por Falta', status='error', constant=MatriculaCursoTurma.SITUACAO_REPROVADO_POR_FALTA)
                            else:
                                if self.is_aprovado_por_nota():
                                    d = dict(rotulo='Aprovado', status='success', constant=MatriculaCursoTurma.SITUACAO_APROVADO)
                                else:
                                    d = dict(rotulo='Reprovado', status='error', constant=MatriculaCursoTurma.SITUACAO_REPROVADO)
                        # alguma nota está faltando
                        else:
                            # se alguma nota está faltando e não for uma das notas das etapas regulares, é da etapa final
                            if self.realizou_todas_avaliacoes_regulares():
                                d = dict(rotulo='Prova Final', status='alert', constant=MatriculaCursoTurma.SITUACAO_PROVA_FINAL)
                            # alguma nota das estas regulares não foram entregues
                            else:
                                # se o diário puder ser entregue sem nota
                                if self.curso_turma.curso_formacao.pode_fechar_pendencia:
                                    # se o diário puder se entregue sem nota e as aulas tiverem sido lançadas
                                    d = dict(rotulo='Pendente', status='info', constant=MatriculaCursoTurma.SITUACAO_PENDENTE)
                                # o diário não pode ser entregue sem que todas as notas das etapas regulares tenham sido registradas
                                else:
                                    d = dict(rotulo='Cursando', status='info', constant=MatriculaCursoTurma.SITUACAO_CURSANDO)
                    # o componente não requer nota e a avaliação é por nota
                    else:
                        # se o componente não requer nota, mas ainda não completou CH mínima
                        if not self.is_carga_horaria_diario_fechada():
                            d = dict(rotulo='Cursando', status='info', constant=MatriculaCursoTurma.SITUACAO_CURSANDO)
                        # se atingiu o percentual mínimo de frequência na disciplina
                        elif self.is_aprovado_por_frequencia():
                            d = dict(rotulo='Aprovado', status='success', constant=MatriculaCursoTurma.SITUACAO_APROVADO)
                        else:
                            d = dict(rotulo='Reprov. por Falta', status='error', constant=MatriculaCursoTurma.SITUACAO_REPROVADO)
                # avaliação por frequência
                else:
                    # se atingiu o percentual mínimo de frequência na disciplina
                    if self.is_aprovado_por_frequencia():
                        d = dict(rotulo='Aprovado', status='success', constant=MatriculaCursoTurma.SITUACAO_APROVADO)
                    # não atingiu o percentual mínimo de frequência na disciplina
                    else:
                        d = dict(rotulo='Reprov. por Falta', status='error', constant=MatriculaCursoTurma.SITUACAO_REPROVADO_POR_FALTA)
            # todas as aulas ainda não foram registradas
            else:
                status = 'info'
                d = dict(rotulo='Cursando', status=status, constant=MatriculaCursoTurma.SITUACAO_CURSANDO)
        # o período do aluno está fechado
        else:
            if self.situacao == MatriculaCursoTurma.SITUACAO_APROVADO:
                status = 'success'
            elif self.situacao == MatriculaCursoTurma.SITUACAO_REPROVADO:
                status = 'error'
            elif self.situacao == MatriculaCursoTurma.SITUACAO_REPROVADO_POR_FALTA:
                status = 'error'
            elif self.situacao == MatriculaCursoTurma.SITUACAO_CANCELADO:
                status = 'error'
            elif self.situacao == MatriculaCursoTurma.SITUACAO_TRANCADO:
                status = 'alert'
            elif self.situacao == MatriculaCursoTurma.SITUACAO_TRANSFERIDO:
                status = 'alert'
            elif self.situacao == MatriculaCursoTurma.SITUACAO_PENDENTE:
                status = 'info'
            else:
                status = 'alert'
            d = dict(rotulo=self.get_situacao_display(), status=status, constant=self.situacao)

        # Substituindo as notas nulas caso as notas tenham sido zeradas anteriormente
        if zerar_avaliacoes_nao_realizadas:
            self.nota_1 = nota_1
            self.nota_final = nota_final

        return d

    def get_situacao_diario_resumida(self, ignorar_fechamento_carga_horaria=False, zerar_avaliacoes_nao_realizadas=False):
        d = self.get_situacao_diario(ignorar_fechamento_carga_horaria, zerar_avaliacoes_nao_realizadas)
        if d['rotulo'] == 'Aprovado':
            d['rotulo'] = 'APR'
        elif d['rotulo'] == 'Reprovado':
            d['rotulo'] = 'REP'
        elif d['rotulo'] == 'Reprov. por Falta':
            d['rotulo'] = 'RF'
        elif d['rotulo'] == 'Prova Final':
            d['rotulo'] = 'PF'
        elif d['rotulo'] == 'Cursando':
            d['rotulo'] = 'CUR'
        elif d['rotulo'] == 'Trancado':
            d['rotulo'] = 'TRA'
        elif d['rotulo'] == 'Cancelado':
            d['rotulo'] = 'CAN'
        elif d['rotulo'] == 'Transferido':
            d['rotulo'] = 'TRF'
        else:
            d['rotulo'] = 'OUT'
        return d

    def get_situacao_forcada_diario(self):
        """
        Este método retorna um dicionário contendo:
            a) uma descrição amigável para a situação computada
            b) o status, que corresonde a uma classe css utilizada no template
            c) a constante do choice definido para o field 'situacao' da classe

        A situação do diário é calculada não importando se a carga horária tenha sido cumprida ou não.
        Caso as notas das etapas estejam nulas, elas serão definidas como 'zero'.
        Este método é utilizado no processo de fechamento de período.
        """
        return self.get_situacao_diario(ignorar_fechamento_carga_horaria=True, zerar_avaliacoes_nao_realizadas=True)

    def get_situacao_registrada_diario(self):
        """
        Este método retorna um dicionário contendo:
            a) uma descrição amigável para a situação computada
            b) o status, que corresonde a uma classe css utilizada no template
            c) a constante do choice definido para o field 'situacao' da classe

        A situação do diário não é calculada a partir das notas das avaliações e frequência, mas sim do valor atual do atributo 'situacao'.
        Caso deseje saber a situação do diário baseada nas notas e na frequência, o método 'self.get_situacao_diario()' deve ser utilizado.
        """
        if self.situacao == MatriculaCursoTurma.SITUACAO_CURSANDO:
            return dict(rotulo='Cursando', status='info', constant=MatriculaCursoTurma.SITUACAO_CURSANDO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_PROVA_FINAL:
            return dict(rotulo='Prova Final', status='alert', constant=MatriculaCursoTurma.SITUACAO_PROVA_FINAL)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_APROVADO:
            return dict(rotulo='Aprovado', status='success', constant=MatriculaCursoTurma.SITUACAO_APROVADO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_REPROVADO:
            return dict(rotulo='Reprovado', status='error', constant=MatriculaCursoTurma.SITUACAO_REPROVADO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_REPROVADO_POR_FALTA:
            return dict(rotulo='Reprov. por Falta', status='error', constant=MatriculaCursoTurma.SITUACAO_REPROVADO_POR_FALTA)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_TRANCADO:
            return dict(rotulo='Trancado', status='alert', constant=MatriculaCursoTurma.SITUACAO_TRANCADO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_TRANSFERIDO:
            return dict(rotulo='Transferido', status='alert', constant=MatriculaCursoTurma.SITUACAO_TRANSFERIDO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_CANCELADO:
            return dict(rotulo='Cancelado', status='alert', constant=MatriculaCursoTurma.SITUACAO_CANCELADO)
        elif self.situacao == MatriculaCursoTurma.SITUACAO_PENDENTE:
            return dict(rotulo='Pendente', status='info', constant=MatriculaCursoTurma.SITUACAO_PENDENTE)


    def set_faltas(self, aulas):

        self.faltas = []
        for aula in aulas:
            falta = Falta.objects.filter(matricula_curso_turma=self, aula=aula).order_by('-id').first()
            if falta is None:
                falta = Falta()
                falta.matricula_curso_turma = self
                falta.aula = aula
                falta.quantidade = 0

            # abono_faltas = self.matricula_periodo.aluno.abonofaltas_set.filter(data_inicio__lte=aula.data, data_fim__gte=aula.data)
            # if abono_faltas:
            #     falta.abono_faltas = abono_faltas[0]
            self.faltas.append(falta)

    def get_qtd_aulas(self, qs_aulas, mes, ano, excluir_situacoes_inativas=True):
        qs = qs_aulas.filter(data__year=ano, data__month=mes, data__lte=datetime.date.today())
        # if excluir_situacoes_inativas:
        #     situacoes_inativas = [MatriculaCursoTurma.SITUACAO_CANCELADO, MatriculaCursoTurma.SITUACAO_DISPENSADO, MatriculaCursoTurma.SITUACAO_TRANCADO, MatriculaCursoTurma.SITUACAO_TRANSFERIDO]
        #     qs = qs.filter(matriculadiario__in=self.matricula_cursoturma_set.exclude(situacao__in=situacoes_inativas).values_list('pk', flat=True))
        soma = 0
        pks = []
        for pk, quantidade in qs.values_list('pk', 'quantidade'):
            soma += quantidade
            pks.append(pk)
        return soma, pks

    def get_qtd_faltas(self, pks, qs_faltas, abonada=None):
        qs_faltas = qs_faltas.filter(aula_id__in=pks)
        if abonada:
            qs_faltas = qs_faltas.filter(abono_faltas__isnull=False)
        return qs_faltas.aggregate(Sum('quantidade'))['quantidade__sum'] or 0

    def get_numero_faltas(self, etapa=None, ignorar_abonos=False):
        """
        Este método retorna o número de faltas para a etapa informada.
        O total de faltas em todas as etapas é rotornado caso nenhuma etapa seja informada.
        """

        qs = Falta.objects.filter(matricula_curso_turma=self)#.exclude(abono_faltas__isnull=ignorar_abonos)
        if etapa:
            qs = qs.filter(aula__etapa=etapa)
        return qs.aggregate(Sum('quantidade')).get('quantidade__sum') or 0

    def get_numero_faltas_primeira_etapa(self):
        """
        Este método retorna o número de faltas na primeira etapa.
        """
        return self.get_numero_faltas(1)

    def pode_ser_excluido_do_curso_turma(self, user):
        return True


class ConfiguracaoAvaliacao(LogPPEModel):
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

    curso_turma = models.ForeignKeyPlus(CursoTurma, verbose_name='Professor', null=True)
    etapa = models.IntegerField('Etapa', null=True)
    forma_calculo = models.IntegerField(choices=FORMA_CALCULO_CHOICES, default=FORMA_CALCULO_MEDIA_ARITMETICA, verbose_name='Forma de Cálculo')
    divisor = models.PositiveIntegerField('Divisor', null=True, blank=True)
    maior_nota = models.BooleanField('Ignorar Maior Nota', default=False)
    menor_nota = models.BooleanField('Ignorar Menor Nota', default=False)
    autopublicar = models.BooleanField('Autopublicar Notas', default=True, help_text='As notas das avaliacões serão exibidas aos alunos a medida que forem lançadas.')
    observacao = models.TextField('Observação', null=True, blank=True)

    class Meta:
        verbose_name = 'Configuração de Avaliação'
        verbose_name_plural = 'Configurações de Avaliação'

    def __str__(self):
        lista = []
        for item in self.itemconfiguracaoavaliacao_set.all():
            if item.peso:
                lista.append('{} - {} [{}]'.format(item.sigla, item.nota_maxima, item.peso))
            else:
                lista.append('{} - {}'.format(item.sigla, item.nota_maxima))
        return '{} ({})'.format(self.get_forma_calculo_display(), ' | '.join(lista))

    def get_absolute_url(self):
        return '/edu/configuracao_avaliacao/{:d}/'.format(self.pk)


class ItemConfiguracaoAvaliacao(LogPPEModel):
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

    configuracao_avaliacao = models.ForeignKeyPlus(ConfiguracaoAvaliacao, verbose_name='Configuração da Avaliação')
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
        if configuracao_avaliacao.forma_calculo == ConfiguracaoAvaliacao.FORMA_CALCULO_MEDIA_PONDERADA and self.peso and self.peso < 0:
            raise ValidationError('Deve ser informado o peso de cada item devido à forma de cálculo escolhida.')

    def get_qtd_avaliacoes_concorrentes(self):
        if self.data:
            qs_itens_avaliacao = ItemConfiguracaoAvaliacao.objects.exclude(pk=self.pk).filter(
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


class NotaAvaliacao(LogPPEModel):
    matricula_curso_turma = models.ForeignKeyPlus(MatriculaCursoTurma, verbose_name='Matrícula Diário', on_delete=models.CASCADE)
    item_configuracao_avaliacao = models.ForeignKeyPlus(ItemConfiguracaoAvaliacao, verbose_name='Item de Configuração de Avaliação', on_delete=models.CASCADE)
    nota = models.NotaField('Nota', null=True)

    class Meta:
        verbose_name = 'Nota de Avaliação'
        verbose_name_plural = 'Notas de Avaliações'
        ordering = ('-id',)

    def __str__(self):
        return 'Nota {} do aluno {} na avaliação {} do diário {}'.format(
            self.nota is None and 'não lançada' or self.nota,
            self.matricula_curso_turma.trabalhador_educando.matricula,
            self.item_configuracao_avaliacao.sigla,
            self.matricula_curso_turma.curso_turma.pk,
        )

    def pode_exibir_nota(self):
        diario_entregue = (
            getattr(self.item_configuracao_avaliacao.configuracao_avaliacao.curso_turma, 'posse_etapa_{}'.format(self.item_configuracao_avaliacao.configuracao_avaliacao.etapa))
            == CursoTurma.POSSE_REGISTRO_ESCOLAR
        )
        return diario_entregue or self.item_configuracao_avaliacao.configuracao_avaliacao.autopublicar


class Falta(LogPPEModel):
    matricula_curso_turma = models.ForeignKeyPlus(MatriculaCursoTurma, verbose_name='Aluno')
    aula = models.ForeignKeyPlus(Aula, verbose_name='Aula')
    quantidade = models.IntegerField(default=0)
    # abono_faltas = models.ForeignKeyPlus('ppe.AbonoFaltas', verbose_name='Abono Faltas', null=True, blank=True)

    class Meta:
        verbose_name = 'Falta'
        verbose_name_plural = 'Faltas'
        unique_together = (('matricula_curso_turma', 'aula'),)

    def __str__(self):
        return 'Falta referente à {} hora(s)/aula(s) do aluno {} na aula {}'.format(self.quantidade, self.matricula_curso_turma.trabalhador_educando.matricula, self.aula.pk)

    def get_trabalhador_educando(self):
        return self.matricula_cursoturma.trabalhador_educando

    def get_curso_turma(self):
        return self.matricula_curso_turma.curso_turma

    def pode_ser_registrada(self):
        return self.aula.data <= datetime.date.today()