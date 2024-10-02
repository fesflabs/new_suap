from django.db.models import Manager

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from djtools.db import models
from djtools.testutils import running_tests
from residencia.models import LogResidenciaModel, MatriculaDiario
from rh.models import Servidor
from suap.settings_base import PERIODO_LETIVO_CHOICES


class ObservacaoDiario(LogResidenciaModel):
    observacao = models.TextField('Observação do Diário')
    diario = models.ForeignKeyPlus('residencia.Diario', related_name='observacao_diarios_residencia_set', verbose_name='Diário')
    data = models.DateFieldPlus(verbose_name='Data')
    usuario = models.ForeignKeyPlus('comum.User', related_name='observacao_diarios_usuario_residencia_set', verbose_name='Usuário')

    class Meta:
        permissions = (('adm_delete_observacaodiario', 'Pode deletar observações de outros usuários'),)


class Diario(LogResidenciaModel):
    SEARCH_FIELDS = ['componente_curricular__componente__sigla', 'id', 'componente_curricular__componente__descricao']

    SITUACAO_ABERTO = 1
    SITUACAO_FECHADO = 2
    SITUACAO_CHOICES = [[SITUACAO_ABERTO, 'Aberto'], [SITUACAO_FECHADO, 'Fechado']]

    POSSE_REGISTRO_ESCOLAR = 0
    POSSE_PROFESSOR = 1
    POSSE_CHOICES = [[POSSE_PROFESSOR, 'Professor'], [POSSE_REGISTRO_ESCOLAR, 'Registro Escolar']]

    ETAPA_1 = 1
    ETAPA_2 = 2
    ETAPA_3 = 3
    ETAPA_4 = 4
    ETAPA_5 = 5
    ETAPA_CHOICES = [[ETAPA_1, 'Etapa 1'], [ETAPA_2, 'Etapa 2'], [ETAPA_3, 'Etapa 3'], [ETAPA_4, 'Etapa 4'], [ETAPA_5, 'Etapa Final']]

    # Manager
    objects = models.Manager()

    # Fields
    id = models.AutoField(verbose_name='Código', primary_key=True)
    turma = models.ForeignKeyPlus('residencia.Turma', verbose_name='Turma', related_name='diarios_turma_residencia_set', on_delete=models.CASCADE)
    componente_curricular = models.ForeignKeyPlus('residencia.ComponenteCurricular', verbose_name='Componente', related_name='diarios_componente_curriculares_residencia_set', null=True, on_delete=models.CASCADE)
    percentual_minimo_ch = models.PositiveIntegerField(verbose_name='Percentual Mínimo (Carga Horária)')
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano Letivo', related_name='diarios_residencia_por_ano_letivo_set', on_delete=models.CASCADE)
    periodo_letivo = models.PositiveIntegerField(verbose_name='Período Letivo', choices=PERIODO_LETIVO_CHOICES)
    quantidade_vagas = models.PositiveIntegerField(verbose_name='Quantidade de Vagas', default=0)
    situacao = models.PositiveIntegerField(verbose_name='Situação', choices=SITUACAO_CHOICES, default=SITUACAO_ABERTO)
    estrutura_curso = models.ForeignKeyPlus('residencia.EstruturaCurso', verbose_name='Estrutura de Curso', related_name='diarios_residencia_estrutura_curso_set', on_delete=models.CASCADE)
    calendario_academico = models.ForeignKeyPlus('residencia.CalendarioAcademico', verbose_name='Calendário Acadêmico', related_name='diarios_residencia_calendario_academico_set', on_delete=models.CASCADE)
    local_aula = models.ForeignKeyPlus('comum.Sala', verbose_name='Local de Aula', null=True ,related_name='diarios_residencia_local_aula_set',)
    locais_aula_secundarios = models.ManyToManyFieldPlus('comum.Sala', verbose_name='Locais de Aula Secundários', blank=True, related_name='diarios_residencia_ocais_aula_secundarios_set')
    descricao_dinamica = models.CharFieldPlus('Descrição Dinâmica', null=True, blank=True)
    segundo_ano = models.BooleanField('Segundo Semestre', default=False)
    posse_etapa_1 = models.PositiveIntegerField(choices=POSSE_CHOICES, default=POSSE_PROFESSOR)
    posse_etapa_2 = models.PositiveIntegerField(choices=POSSE_CHOICES, default=POSSE_PROFESSOR)
    posse_etapa_3 = models.PositiveIntegerField(choices=POSSE_CHOICES, default=POSSE_PROFESSOR)
    posse_etapa_4 = models.PositiveIntegerField(choices=POSSE_CHOICES, default=POSSE_PROFESSOR)
    posse_etapa_5 = models.PositiveIntegerField(choices=POSSE_CHOICES, default=POSSE_PROFESSOR)

    entregue_fisicamente = models.BooleanField(verbose_name='Entregue Fisicamente', null=True)

    class Meta:
        verbose_name = 'Diário'
        verbose_name_plural = 'Diários'

        permissions = (
            ('reabrir_diario', 'Pode reabrir Diário'),
            ('lancar_nota_diario', 'Pode lançar nota em Diário'),
            ('mudar_posse_diario', 'Pode mudar posse de Diário'),
            ('emitir_boletins', 'Pode emitir boletins de Diário'),
        )

    def __str__(self):
        componente = '{} - {} - [{} h/{} Aulas]'.format(
            self.componente_curricular.componente.sigla,
            self.componente_curricular.componente.descricao,
            self.componente_curricular.componente.ch_hora_relogio,
            self.componente_curricular.componente.ch_hora_aula,
        )
        if self.id:
            descricao = '{} - {}'.format(self.id, componente)
        else:
            descricao = str(self.componente_curricular)
        return descricao

    def get_preceptores(self):
        return self.preceptordiario_set.all()

    def get_alunos_ativos(self):
        return self.matriculas_diarios_diario_residencia_set.exclude(
            situacao__in=(MatriculaDiario.SITUACAO_CANCELADO, MatriculaDiario.SITUACAO_DISPENSADO, MatriculaDiario.SITUACAO_TRANCADO, MatriculaDiario.SITUACAO_TRANSFERIDO)
        )

    def get_quantidade_alunos_ativos(self):
        return self.get_alunos_ativos().count()

    def get_absolute_url(self):
        return '/residencia/diario/{:d}/'.format(self.pk)

    def em_posse_do_registro(self, etapa=None):
        retorno = True
        # if etapa:
        #     retorno = getattr(self, 'posse_etapa_{}'.format(etapa)) == Diario.POSSE_REGISTRO_ESCOLAR
        return retorno

    def is_aberto(self):
        return True

    def fechar(self):
        if not self.situacao == Diario.SITUACAO_FECHADO and not self.matriculas_diarios_diario_residencia_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO):
            self.situacao = Diario.SITUACAO_FECHADO
            self.posse_etapa_1 = Diario.POSSE_REGISTRO_ESCOLAR
            self.posse_etapa_2 = Diario.POSSE_REGISTRO_ESCOLAR
            self.posse_etapa_3 = Diario.POSSE_REGISTRO_ESCOLAR
            self.posse_etapa_4 = Diario.POSSE_REGISTRO_ESCOLAR
            self.posse_etapa_5 = Diario.POSSE_REGISTRO_ESCOLAR
            self.save()

    def abrir(self):
        if not self.situacao == Diario.SITUACAO_ABERTO:
            self.situacao = Diario.SITUACAO_ABERTO
            self.save()

    def get_numero_primeira_etapa(self):
        result = '1'
        # if self.is_semestral_segundo_semestre():
        #     result = '3'
        return result

    def get_numero_segunda_etapa(self):
        result = '2'
        # if self.is_semestral_segundo_semestre():
        #     result = '4'
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

    def get_lista_etapas(self):
        return list(range(1, 5))
        # if self.componente_curricular.qtd_avaliacoes == 0:
        #     return [1]
        # return list(range(1, self.componente_curricular.qtd_avaliacoes + 1))

    def etapas_anteriores_entregues(self, etapa):
        for num_etapa in self.get_lista_etapas() + [5]:
            if num_etapa < etapa:
                if getattr(self, 'posse_etapa_{}'.format(num_etapa)) != Diario.POSSE_REGISTRO_ESCOLAR:
                    return False
        return True

#     def get_resumo_ch_prevista(self):
#         resumo = []
#         for professor_diario in self.professordiario_set.all():
#             resumo.append(professor_diario.get_resumo_ch_prevista())
#         return ' | '.join(resumo)

    def get_itens_avaliacao(self):
        return ItemConfiguracaoAvaliacao.objects.filter(configuracao_avaliacao__diario=self)
#
#     def get_ocorrencias(self):
#         return OcorrenciaDiario.objects.filter(professor_diario__diario=self)
#
#     def is_semestral_segundo_semestre(self):
#         return self.segundo_semestre and self.is_semestral()
#
#     def get_inicio_etapa_1(self):
#         inicio_etapa = self.calendario_academico.data_inicio_etapa_1
#         if self.is_semestral_segundo_semestre():
#             inicio_etapa = self.calendario_academico.data_inicio_etapa_3
#         return inicio_etapa
#
#     def get_fim_etapa_1(self):
#         fim_etapa = self.calendario_academico.data_fim_etapa_1
#         if self.is_semestral_segundo_semestre():
#             fim_etapa = self.calendario_academico.data_fim_etapa_3
#         if self.componente_curricular.qtd_avaliacoes == 1 and self.calendario_academico.qtd_etapas == 2:
#             fim_etapa = self.calendario_academico.data_fim_etapa_2
#         return fim_etapa
#
#     def get_inicio_etapa_2(self):
#         inicio_etapa = self.calendario_academico.data_inicio_etapa_2
#         if self.is_semestral_segundo_semestre():
#             inicio_etapa = self.calendario_academico.data_inicio_etapa_4
#         return inicio_etapa
#
#     def get_fim_etapa_2(self):
#         fim_etapa = self.calendario_academico.data_fim_etapa_2
#         if self.is_semestral_segundo_semestre():
#             fim_etapa = self.calendario_academico.data_fim_etapa_4
#         return fim_etapa
#
#     def get_inicio_etapa_3(self):
#         return self.calendario_academico.data_inicio_etapa_3
#
#     def get_fim_etapa_3(self):
#         return self.calendario_academico.data_fim_etapa_3
#
#     def get_inicio_etapa_4(self):
#         return self.calendario_academico.data_inicio_etapa_4
#
#     def get_fim_etapa_4(self):
#         return self.calendario_academico.data_fim_etapa_4
#
#     def get_inicio_etapa_final(self):
#         inicio_etapa = self.calendario_academico.data_inicio_prova_final or self.calendario_academico.get_data_fim_utlima_etapa()
#         if not self.segundo_semestre and self.is_semestral():
#             inicio_etapa = self.calendario_academico.data_fim_etapa_2 + timedelta(1)
#         return inicio_etapa
#
#     def get_fim_etapa_final(self):
#         fim_etapa = self.calendario_academico.data_fim_prova_final
#         if not self.segundo_semestre and self.is_semestral():
#             fim_etapa = self.calendario_academico.data_inicio_etapa_3 - timedelta(1)
#         elif not self.calendario_academico.data_fim_prova_final:
#             fim_etapa = self.calendario_academico.data_fechamento_periodo
#         return fim_etapa
#
#     def get_numero_primeira_etapa(self):
#         result = '1'
#         if self.is_semestral_segundo_semestre():
#             result = '3'
#         return result
#
#     def get_numero_segunda_etapa(self):
#         result = '2'
#         if self.is_semestral_segundo_semestre():
#             result = '4'
#         return result
#
#     def get_label_etapa(self, etapa):
#         if etapa == 1:
#             return self.get_numero_primeira_etapa()
#         elif etapa == 2:
#             return self.get_numero_segunda_etapa()
#         elif etapa == 5:
#             return 'Final'
#         else:
#             return etapa
#
#     def is_semestral(self):
#         return self.calendario_academico.qtd_etapas == 4 and self.componente_curricular.is_semestral()
#
#     def possui_residente_periodo_fechado(self):
#         situacoes = [MatriculaDiario.SITUACAO_APROVADO, MatriculaDiario.SITUACAO_REPROVADO, MatriculaDiario.SITUACAO_PENDENTE, MatriculaDiario.SITUACAO_APROVADO_REPROVADO_MODULO]
#         return self.matriculas_diarios_diario_residencia_set.filter(situacao__in=situacoes).exists()
#
#     def get_horarios_com_choque(self, verificar_apenas_existencia=False):
#         qs_matriculas_periodos = MatriculaPeriodo.objects.filter(matriculadiario__diario=self, matriculadiario__situacao=MatriculaDiario.SITUACAO_CURSANDO)
#         ids_matriculas_periodos = qs_matriculas_periodos.distinct().values_list("id", flat=True)
#         semestre_oposto = not self.segundo_semestre
#         horarios_choque = dict()
#         for horario_aula_diario in self.horarioauladiario_set.exclude(diario__segundo_semestre=semestre_oposto):
#             qs_horarios_com_choque = (
#                 HorarioAulaDiario.objects.filter(
#                     dia_semana=horario_aula_diario.dia_semana,
#                     horario_aula=horario_aula_diario.horario_aula,
#                     diario__matriculadiario__matricula_periodo__id__in=ids_matriculas_periodos,
#                 )
#                 .exclude(id=horario_aula_diario.id)
#                 .exclude(diario__segundo_semestre=semestre_oposto)
#                 .distinct()
#             )
#             if verificar_apenas_existencia:
#                 return qs_horarios_com_choque
#
#             horarios_com_choque = []
#             for horario_aula_diario_choque in qs_horarios_com_choque:
#                 horario_aula_diario_choque.matriculas_periodos = (
#                     qs_matriculas_periodos.filter(matriculadiario__diario__horarioauladiario=horario_aula_diario_choque).distinct().order_by("residente__pessoa_fisica__nome")
#                 )
#                 horarios_com_choque.append(horario_aula_diario_choque)
#             if horarios_com_choque:
#                 horarios_choque.update({horario_aula_diario: horarios_com_choque})
#         return horarios_choque
#
#     def pode_ser_dividido_ao_meio(self):
#         return not NotaAvaliacao.objects.filter(matricula_diario__diario=self, nota__isnull=False).exists()
#
#     @atomic()
#     def dividir(self, professor=None, matriculas_diario=None):
#         itens_configuracao_avaliacao_dict, novo_diario = self.iniciar_divisao_diario(professor)
#
#         # dividindo o diário ao meio caso os residentes não teham sido especificados
#         if not matriculas_diario:
#             matriculas_diario = self.matriculas_diarios_diario_residencia_set.all()[self.matriculas_diarios_diario_residencia_set.count() / 2:]
#
#         self.finalizar_divisao_diario(itens_configuracao_avaliacao_dict, matriculas_diario, novo_diario)
#         return novo_diario
#
#     @atomic()
#     def dividir_reprovados_dependentes(self, professor=None):
#         itens_configuracao_avaliacao_dict, novo_diario = self.iniciar_divisao_diario(professor)
#         ids = NotaAvaliacao.objects.filter(
#             matricula_diario__diario=self, nota__isnull=False
#         ).values_list('matricula_diario', flat=True).order_by('matricula_diario').distinct()
#         matriculas_diario_reprovados = []
#         for matricula_diario in self.matriculas_diarios_diario_residencia_set.exclude(id__in=ids):
#             if matricula_diario.esteve_reprovado():
#                 matriculas_diario_reprovados.append(matricula_diario)
#
#         self.finalizar_divisao_diario(itens_configuracao_avaliacao_dict, matriculas_diario_reprovados, novo_diario)
#         return novo_diario
#
#     @atomic
#     def replicar(self):
#         _, novo_diario = self.iniciar_divisao_diario(None)
#         novo_diario.local_aula = None
#         novo_diario.save()
#         return novo_diario
#
#     @atomic
#     def iniciar_divisao_diario(self, professor):
#         novo_diario = Diario.objects.get(pk=self.pk)
#         # criando um novo diário igual ao anterior
#         novo_diario.pk = None
#         novo_diario.dividindo = True
#         novo_diario.save()
#         # definindo o novo professor
#         if professor:
#             professor_diario = ProfessorDiario()
#             professor_diario.professor = professor
#             professor_diario.diario = novo_diario
#             professor_diario.tipo = TipoProfessorDiario.objects.get(pk=1)
#             professor_diario.percentual_ch = 100
#
#             if novo_diario.componente_curricular:
#                 qtd_avaliacoes = novo_diario.componente_curricular.qtd_avaliacoes
#                 professor_diario.data_inicio_etapa_1 = novo_diario.get_inicio_etapa_1()
#                 professor_diario.data_fim_etapa_1 = self.flexibilizar_data(novo_diario.get_fim_etapa_1())
#
#             if qtd_avaliacoes >= 2:
#                 professor_diario.data_inicio_etapa_2 = novo_diario.get_inicio_etapa_2()
#                 professor_diario.data_fim_etapa_2 = self.flexibilizar_data(novo_diario.get_fim_etapa_2())
#
#             if qtd_avaliacoes >= 4:
#                 professor_diario.data_inicio_etapa_3 = novo_diario.get_inicio_etapa_3()
#                 professor_diario.data_fim_etapa_3 = self.flexibilizar_data(novo_diario.get_fim_etapa_3())
#                 professor_diario.data_inicio_etapa_4 = novo_diario.get_inicio_etapa_4()
#                 professor_diario.data_fim_etapa_4 = self.flexibilizar_data(novo_diario.get_fim_etapa_4())
#
#             if qtd_avaliacoes > 0:
#                 professor_diario.data_inicio_etapa_final = novo_diario.get_inicio_etapa_final()
#                 professor_diario.data_fim_etapa_final = self.flexibilizar_data(novo_diario.get_fim_etapa_final())
#
#             professor_diario.save()
#
#         itens_configuracao_avaliacao_dict = dict()
#         # replicando as configurações de avaliação baseado no diário anterior
#         for configuracao_avaliacao in ConfiguracaoAvaliacao.objects.filter(diario=self):
#             nova_configuracao = ConfiguracaoAvaliacao.objects.get(pk=configuracao_avaliacao.pk)
#             nova_configuracao.id = None
#             nova_configuracao.diario = novo_diario
#             nova_configuracao.save()
#             # replicando também os itens de configuração
#             for item_configuracao_avaliacao in configuracao_avaliacao.itemconfiguracaoavaliacao_set.all():
#                 novo_item_configuracao_avaliacao = ItemConfiguracaoAvaliacao.objects.get(pk=item_configuracao_avaliacao.pk)
#                 novo_item_configuracao_avaliacao.id = None
#                 novo_item_configuracao_avaliacao.configuracao_avaliacao = nova_configuracao
#                 novo_item_configuracao_avaliacao.save()
#                 itens_configuracao_avaliacao_dict[item_configuracao_avaliacao.pk] = novo_item_configuracao_avaliacao
#
#         return itens_configuracao_avaliacao_dict, novo_diario
#
#     def flexibilizar_data(self, data):
#         if not data:
#             return None
#         return somar_data(data, 7)
#
#     def finalizar_divisao_diario(self, itens_configuracao_avaliacao_dict, matriculas_diario, novo_diario):
#         # transferindo os residentes par ao novo diário
#         for matricula_diario in matriculas_diario:
#
#             # excluindo as faltas do diário antigo
#             matricula_diario.falta_set.all().delete()
#
#             matricula_diario.diario = novo_diario
#             # alterando a referencia para os novos itens de configuração criados anteriormente
#             for nota_avaliacao in matricula_diario.notaavaliacao_set.all():
#                 nota_avaliacao.item_configuracao_avaliacao = itens_configuracao_avaliacao_dict[nota_avaliacao.item_configuracao_avaliacao.id]
#                 nota_avaliacao.save()
#
#             matricula_diario.save()
#
#     def configuracao_avaliacao_1(self):
#         try:
#             try:
#                 return self._configuracao_avaliacao_1
#             except AttributeError:
#                 self._configuracao_avaliacao_1 = self.configuracaoavaliacao_set.get(etapa=1)
#                 return self._configuracao_avaliacao_1
#         except ConfiguracaoAvaliacao.DoesNotExist:
#             return None
#
#     def configuracao_avaliacao_2(self):
#         try:
#             try:
#                 return self._configuracao_avaliacao_2
#             except Exception:
#                 self._configuracao_avaliacao_2 = self.configuracaoavaliacao_set.get(etapa=2)
#                 return self._configuracao_avaliacao_2
#         except ConfiguracaoAvaliacao.DoesNotExist:
#             return None
#
#     def configuracao_avaliacao_3(self):
#         try:
#             try:
#                 return self._configuracao_avaliacao_3
#             except Exception:
#                 self._configuracao_avaliacao_3 = self.configuracaoavaliacao_set.get(etapa=3)
#                 return self._configuracao_avaliacao_3
#         except ConfiguracaoAvaliacao.DoesNotExist:
#             return None
#
#     def configuracao_avaliacao_4(self):
#         try:
#             try:
#                 return self._configuracao_avaliacao_4
#             except Exception:
#                 self._configuracao_avaliacao_4 = self.configuracaoavaliacao_set.get(etapa=4)
#                 return self._configuracao_avaliacao_4
#         except ConfiguracaoAvaliacao.DoesNotExist:
#             return None
#
#     def configuracao_avaliacao_5(self):
#         try:
#             try:
#                 return self._configuracao_avaliacao_5
#             except Exception:
#                 self._configuracao_avaliacao_5 = self.configuracaoavaliacao_set.get(etapa=5)
#                 return self._configuracao_avaliacao_5
#         except ConfiguracaoAvaliacao.DoesNotExist:
#             return None
#
#     def get_polos(self):
#         ids = self.matriculas_diarios_diario_residencia_set.values_list('matricula_periodo__residente__polo__id', flat=True)
#         qs = Polo.objects.filter(id__in=ids)
#         return qs
#
    def get_matriculas_diario(self):
        matriculas_diario = self.matriculas_diarios_diario_residencia_set.all()
        if not running_tests():
            matriculas_diario = matriculas_diario.order_by('matricula_periodo__residente__pessoa_fisica__nome')
        return matriculas_diario

    def get_matriculas_diario_por_polo(self, pk=None):
        lista = []
        qs = self.matriculas_diarios_diario_residencia_set.all()
        if qs.exists():
            if not running_tests():
                qs = qs.order_by('matricula_periodo__residente__pessoa_fisica__nome')
            lista.append(qs)

        return lista
#

#
#     def get_qtd_pedidos_nao_processados(self):
#         return self.pedidomatriculas_diarios_diario_residencia_set.filter(data_processamento__isnull=True).count()
#
#     def get_sigla(self):
#         if self.id:
#             return '({}) {}'.format(self.id, self.componente_curricular.componente.sigla)
#         else:
#             return self.componente_curricular.componente.sigla
#
#     def get_professor_principal(self):
#         qs = self.professordiario_set.all()
#         if qs.exists():
#             return self.professordiario_set.all()[0]
#         else:
#             return None
#
#     def get_professores(self):
#         return self.professordiario_set.all()
#
#     def get_professores_display(self):
#         return Professor.objects.filter(pk__in=self.professordiario_set.all().values_list('professor__pk', flat=True))
#
#     def get_nomes_professores(self, excluir_tutores=False):
#         lista_nomes = []
#         qs = self.professordiario_set.all()
#         if excluir_tutores:
#             qs = qs.exclude(tipo__descricao='Tutor')
#         for professordiario in qs:
#             lista_nomes.append(format(professordiario.professor.vinculo.pessoa.nome_usual))
#
#         return ', '.join(lista_nomes)
#
#     def get_residentes_ativos(self):
#         return self.matriculas_diarios_diario_residencia_set.exclude(
#             situacao__in=(MatriculaDiario.SITUACAO_CANCELADO, MatriculaDiario.SITUACAO_DISPENSADO, MatriculaDiario.SITUACAO_TRANCADO, MatriculaDiario.SITUACAO_TRANSFERIDO)
#         )
#
#     def get_quantidade_residentes_ativos(self):
#         return self.get_residentes_ativos().count()
#
#     def is_professor_diario(self, user):
#         return self.professordiario_set.filter(professor__vinculo__user=user).exists()
#
#     def entregar_etapa(self, etapa):
#         setattr(self, 'posse_etapa_{}'.format(etapa), Diario.POSSE_REGISTRO_ESCOLAR)
#         self.save()
#
#     def pode_ser_excluido(self):
#         return not self.matriculas_diarios_diario_residencia_set.exists()
#
#     def pode_ser_entregue_sem_nota(self):
#         return datetime.date.today() > self.get_fim_etapa_final() and (self.componente_curricular.pode_fechar_pendencia or self.componente_curricular.qtd_avaliacoes == 0)
#
#     def pode_ser_entregue_com_pedencia(self):
#         return datetime.date.today() > self.get_fim_etapa_final() and self.componente_curricular.pode_fechar_pendencia
#
#     def entregar_etapa_como_professor(self, etapa, entregar_nota_vazia=False):
#         etapa = int(etapa)
#
#         inativos = [MatriculaDiario.SITUACAO_CANCELADO, MatriculaDiario.SITUACAO_TRANSFERIDO, MatriculaDiario.SITUACAO_TRANCADO]
#         if (
#             etapa == 1
#             and self.componente_curricular.qtd_avaliacoes > 0
#             and self.matriculas_diarios_diario_residencia_set.exclude(situacao__in=inativos).filter(matricula_periodo__situacao=SituacaoMatriculaPeriodo.MATRICULADO, nota_1__isnull=True).exists()
#             and not (self.pode_ser_entregue_sem_nota() or entregar_nota_vazia)
#         ):
#             raise Exception('A etapa só pode ser entregue quando todas as notas forem lançadas.')
#         if (
#             etapa == 2
#             and self.matriculas_diarios_diario_residencia_set.exclude(situacao__in=inativos).filter(matricula_periodo__situacao=SituacaoMatriculaPeriodo.MATRICULADO, nota_2__isnull=True).exists()
#             and not (self.pode_ser_entregue_sem_nota() or entregar_nota_vazia)
#         ):
#             raise Exception('A etapa só pode ser entregue quando todas as notas forem lançadas.')
#         if (
#             etapa == 3
#             and self.matriculas_diarios_diario_residencia_set.exclude(situacao__in=inativos).filter(matricula_periodo__situacao=SituacaoMatriculaPeriodo.MATRICULADO, nota_3__isnull=True).exists()
#             and not (self.pode_ser_entregue_sem_nota() or entregar_nota_vazia)
#         ):
#             raise Exception('A etapa só pode ser entregue quando todas as notas forem lançadas.')
#         if (
#             etapa == 4
#             and self.matriculas_diarios_diario_residencia_set.exclude(situacao__in=inativos).filter(matricula_periodo__situacao=SituacaoMatriculaPeriodo.MATRICULADO, nota_4__isnull=True).exists()
#             and not (self.pode_ser_entregue_sem_nota() or entregar_nota_vazia)
#         ):
#             raise Exception('A etapa só pode ser entregue quando todas as notas forem lançadas.')
#         if etapa != 5 and not self.get_aulas(etapa) and not self.estrutura_curso.pode_entregar_etapa_sem_aula:
#             raise Exception('Etapas sem aulas cadastradas não podem ser entregues.')
#         if etapa == self.componente_curricular.qtd_avaliacoes and not self.cumpriu_carga_horaria_minina():
#             raise Exception('A carga horária mínima ({} aulas) ainda não foi registrada.'.format(self.get_carga_horaria_minima()))
#
#         for matricula_diario in self.matriculas_diarios_diario_residencia_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO):
#             if (etapa == 5 and not matricula_diario.is_em_prova_final()):  # não calcula média da nota_final de residente aprovado ou reprovado direto
#                 matricula_diario.registrar_nota_etapa(etapa, False)
#             elif (etapa == 5 and matricula_diario.is_em_prova_final()) or (entregar_nota_vazia and not matricula_diario.diario.componente_curricular.pode_fechar_pendencia):
#                 matricula_diario.registrar_nota_etapa(etapa, True)
#             else:
#                 matricula_diario.registrar_nota_etapa(etapa, False)
#         for matricula_diario in self.matriculas_diarios_diario_residencia_set.exclude(situacao=MatriculaDiario.SITUACAO_CURSANDO):
#             matricula_diario.registrar_nota_etapa(etapa, False)
#         self.entregar_etapa(etapa)
#
#         if etapa == self.componente_curricular.qtd_avaliacoes:
#             entregar_etapa_final = True
#             for matricula_diario in self.matriculas_diarios_diario_residencia_set.all():
#                 if matricula_diario.is_em_prova_final():
#                     entregar_etapa_final = False
#                     break
#             if entregar_etapa_final:
#                 self.entregar_etapa(5)
#
#     def get_lista_etapas(self):
#         if self.componente_curricular.qtd_avaliacoes == 0:
#             return [1]
#         return list(range(1, self.componente_curricular.qtd_avaliacoes + 1))
#
#     def etapas_anteriores_entegues(self, etapa):
#         for num_etapa in self.get_lista_etapas() + [5]:
#             if num_etapa < etapa:
#                 if getattr(self, 'posse_etapa_{}'.format(num_etapa)) != Diario.POSSE_REGISTRO_ESCOLAR:
#                     return False
#         return True
#
#     def get_num_etapa_posse_professor(self):
#         for num_etapa in self.get_lista_etapas() + [5]:
#             if getattr(self, 'posse_etapa_{}'.format(num_etapa)) != Diario.POSSE_REGISTRO_ESCOLAR:
#                 return num_etapa
#         return 1

    def etapa_1_em_posse_do_registro(self):
        return getattr(self, 'posse_etapa_1') == Diario.POSSE_REGISTRO_ESCOLAR

#     def etapa_2_em_posse_do_registro(self):
#         return getattr(self, 'posse_etapa_2') == Diario.POSSE_REGISTRO_ESCOLAR
#
#     def etapa_3_em_posse_do_registro(self):
#         return getattr(self, 'posse_etapa_3') == Diario.POSSE_REGISTRO_ESCOLAR
#
#     def etapa_4_em_posse_do_registro(self):
#         return getattr(self, 'posse_etapa_4') == Diario.POSSE_REGISTRO_ESCOLAR
#
#     def etapa_5_em_posse_do_registro(self):
#         return getattr(self, 'posse_etapa_5') == Diario.POSSE_REGISTRO_ESCOLAR
#
#     def etapa_1_em_atraso(self):
#         return not self.etapa_1_em_posse_do_registro() and datetime.date.today() > self.get_fim_etapa_1()
#
#     def etapa_2_em_atraso(self):
#         fim_etapa = self.get_fim_etapa_2()
#         return not self.etapa_2_em_posse_do_registro() and fim_etapa and datetime.date.today() > fim_etapa
#
#     def etapa_3_em_atraso(self):
#         fim_etapa = self.get_fim_etapa_3()
#         return not self.etapa_3_em_posse_do_registro() and fim_etapa and datetime.date.today() > fim_etapa
#
#     def etapa_4_em_atraso(self):
#         fim_etapa = self.get_fim_etapa_4()
#         return not self.etapa_4_em_posse_do_registro() and fim_etapa and datetime.date.today() > fim_etapa
#
#     def etapa_5_em_atraso(self):
#         return not self.etapa_5_em_posse_do_registro() and datetime.date.today() > self.get_fim_etapa_final()
#
#     def get_aulas(self, etapa=None):
#         qs = Aula.objects.filter(professor_diario__diario=self).order_by('-data').select_related('professor_diario')
#         if etapa:
#             return qs.filter(etapa=etapa)
#         return qs
#
#     def get_horas_aulas_etapa_1(self):
#         return self.get_horas_aulas(1)
#
#     def get_horas_aulas_etapa_2(self):
#         return self.get_horas_aulas(2)
#
#     def get_horas_aulas_etapa_3(self):
#         return self.get_horas_aulas(3)
#
#     def get_horas_aulas_etapa_4(self):
#         return self.get_horas_aulas(4)
#
#     def get_horas_aulas_etapa_5(self):
#         return self.get_horas_aulas(5)
#
#     def get_horas_aulas(self, etapa=None):
#         return self.get_aulas(etapa).aggregate(Sum('quantidade')).get('quantidade__sum') or 0
#
#     def get_carga_horaria_minima(self):
#         return int(round(self.get_carga_horaria_presencial() * self.percentual_minimo_ch * Decimal('0.01')))
#
#     def get_carga_horaria(self):
#         return self.componente_curricular.componente.ch_hora_aula  # ch_presencial
#
#     def get_carga_horaria_presencial(self, relogio=False):
#         if self.componente_curricular.matriz.estrutura.limitar_ch_por_tipo_aula:
#             ch = 0
#             ch += self.get_carga_horaria_maxima_teorica(relogio=relogio)
#             ch += self.get_carga_horaria_maxima_pratica(relogio=relogio)
#             ch += self.get_carga_horaria_maxima_extensao(relogio=relogio)
#             ch += self.get_carga_horaria_maxima_pcc(relogio=relogio)
#             ch += self.get_carga_horaria_maxima_visita_tecnica(relogio=relogio)
#             return ch
#         else:
#             fator_conversao = 1 if relogio else self.componente_curricular.componente.get_fator_conversao_hora_aula()
#             return Decimal(round(self.componente_curricular.ch_presencial * fator_conversao))
#
#     def get_carga_horaria_maxima_teorica(self, relogio=False):
#         fator_conversao = 1 if relogio else self.componente_curricular.componente.get_fator_conversao_hora_aula()
#         if self.componente_curricular.matriz.estrutura.limitar_ch_por_tipo_aula:
#             return int(round(self.componente_curricular.ch_presencial * fator_conversao))
#         return None
#
#     def get_carga_horaria_maxima_pratica(self, relogio=False):
#         fator_conversao = 1 if relogio else self.componente_curricular.componente.get_fator_conversao_hora_aula()
#         if self.componente_curricular.matriz.estrutura.limitar_ch_por_tipo_aula:
#             return int(round(self.componente_curricular.ch_pratica * fator_conversao))
#         return None
#
#     def get_carga_horaria_maxima_extensao(self, relogio=False):
#         fator_conversao = 1 if relogio else self.componente_curricular.componente.get_fator_conversao_hora_aula()
#         if self.componente_curricular.matriz.estrutura.limitar_ch_por_tipo_aula:
#             return int(round(self.componente_curricular.ch_extensao * fator_conversao))
#         return None
#
#     def get_carga_horaria_maxima_pcc(self, relogio=False):
#         fator_conversao = 1 if relogio else self.componente_curricular.componente.get_fator_conversao_hora_aula()
#         if self.componente_curricular.matriz.estrutura.limitar_ch_por_tipo_aula:
#             return int(round(self.componente_curricular.ch_pcc * fator_conversao))
#         return None
#
#     def get_carga_horaria_maxima_visita_tecnica(self, relogio=False):
#         fator_conversao = 1 if relogio else self.componente_curricular.componente.get_fator_conversao_hora_aula()
#         if self.componente_curricular.matriz.estrutura.limitar_ch_por_tipo_aula:
#             return int(round(self.componente_curricular.ch_visita_tecnica * fator_conversao))
#         return None
#
#     def get_carga_horaria_maxima_ead(self):
#         if self.componente_curricular.percentual_maximo_ead:
#             return Decimal(round(self.get_carga_horaria_presencial() / self.componente_curricular.percentual_maximo_ead))
#         return 0
#
#     def get_carga_horaria_relogio(self):
#         return self.componente_curricular.componente.ch_hora_relogio
#
#     def get_carga_horaria_cumprida_por_tipo(self, tipo, relogio=False):
#         fator_conversao = self.componente_curricular.componente.get_fator_conversao_hora_aula() if relogio else 1
#         qs = Aula.objects.filter(professor_diario__diario=self, data__lte=datetime.date.today(), tipo=tipo)
#         return int((qs.aggregate(Sum('quantidade')).get('quantidade__sum') or 0) / fator_conversao)
#
#     def get_carga_horaria_ead_disponivel(self):
#         if self.componente_curricular.percentual_maximo_ead:
#             qtd_registrada = Aula.objects.filter(
#                 professor_diario__diario=self, ead=True
#             ).aggregate(Sum('quantidade')).get('quantidade__sum') or 0
#             return max(self.get_carga_horaria_maxima_ead() - qtd_registrada, 0)
#         return 0
#
#     def get_carga_horaria_cumprida(self):
#         return (
#             self.get_carga_horaria_teorica_contabilizada()
#             + self.get_carga_horaria_pratica_contabilizada()
#             + self.get_carga_horaria_extensao_contabilizada()
#             + self.get_carga_horaria_pcc_contabilizada()
#             + self.get_carga_horaria_visita_tecnica_contabilizada()
#         )
#
#     def get_carga_horaria_teorica_ministrada(self, relogio=False):
#         return self.get_carga_horaria_cumprida_por_tipo(Aula.AULA, relogio=relogio)
#
#     def get_carga_horaria_teorica_contabilizada(self, relogio=False):
#         maxima = self.get_carga_horaria_maxima_teorica(relogio=relogio)
#         if maxima is None or maxima > 0:
#             ch = self.get_carga_horaria_teorica_ministrada(relogio=relogio)
#             return ch if maxima is None or ch < maxima else maxima
#         return 0
#
#     def get_carga_horaria_pratica_ministrada(self, relogio=False):
#         return self.get_carga_horaria_cumprida_por_tipo(Aula.PRATICA, relogio=relogio)
#
#     def get_carga_horaria_pratica_contabilizada(self, relogio=False):
#         maxima = self.get_carga_horaria_maxima_pratica(relogio=relogio)
#         if maxima is None or maxima > 0:
#             ch = self.get_carga_horaria_pratica_ministrada(relogio=relogio)
#             return ch if maxima is None or ch < maxima else maxima
#         return 0
#
#     def get_carga_horaria_extensao_ministrada(self, relogio=False):
#         return self.get_carga_horaria_cumprida_por_tipo(Aula.EXTENSAO, relogio=relogio)
#
#     def get_carga_horaria_extensao_contabilizada(self, relogio=False):
#         maxima = self.get_carga_horaria_maxima_extensao(relogio=relogio)
#         if maxima is None or maxima > 0:
#             ch = self.get_carga_horaria_extensao_ministrada(relogio=relogio)
#             return ch if maxima is None or ch < maxima else maxima
#         return 0
#
#     def get_carga_horaria_pcc_ministrada(self, relogio=False):
#         return self.get_carga_horaria_cumprida_por_tipo(Aula.PRATICA_COMO_COMPONENTE_CURRICULAR, relogio=relogio)
#
#     def get_carga_horaria_pcc_contabilizada(self, relogio=False):
#         maxima = self.get_carga_horaria_maxima_pcc(relogio=relogio)
#         if maxima is None or maxima > 0:
#             ch = self.get_carga_horaria_pcc_ministrada(relogio=relogio)
#             return ch if maxima is None or ch < maxima else maxima
#         return 0
#
#     def get_carga_horaria_relogio_pcc_contabilizada(self):
#         return self.get_carga_horaria_pcc_contabilizada(relogio=True)
#
#     def get_carga_horaria_visita_tecnica_ministrada(self, relogio=False):
#         return self.get_carga_horaria_cumprida_por_tipo(Aula.VISITA_TECNICA, relogio=relogio)
#
#     def get_carga_horaria_visita_tecnica_contabilizada(self, relogio=False):
#         maxima = self.get_carga_horaria_maxima_visita_tecnica(relogio=relogio)
#         if maxima is None or maxima > 0:
#             ch = self.get_carga_horaria_visita_tecnica_ministrada(relogio=relogio)
#             return ch if maxima is None or ch < maxima else maxima
#         return 0
#
#     def get_carga_horaria_relogio_visita_tecnica_contabilizada(self):
#         return self.get_carga_horaria_visita_tecnica_contabilizada(relogio=True)
#
#     def get_percentual_carga_horaria_cumprida(self, adicional=0):
#         if self.get_carga_horaria_presencial():
#             percentual = int((100 * (self.get_carga_horaria_cumprida() + adicional)) / self.get_carga_horaria_presencial())
#             return percentual > 100 and 100 or percentual
#         else:
#             return 100
#
#     def cumpriu_carga_horaria_minina(self):
#         return self.get_percentual_carga_horaria_cumprida() >= self.percentual_minimo_ch
#
#     def is_aberto(self):
#         return True
#
#     def fechar(self):
#         if not self.situacao == Diario.SITUACAO_FECHADO and not self.matriculas_diarios_diario_residencia_set.filter(situacao=MatriculaDiario.SITUACAO_CURSANDO):
#             self.situacao = Diario.SITUACAO_FECHADO
#             self.posse_etapa_1 = Diario.POSSE_REGISTRO_ESCOLAR
#             self.posse_etapa_2 = Diario.POSSE_REGISTRO_ESCOLAR
#             self.posse_etapa_3 = Diario.POSSE_REGISTRO_ESCOLAR
#             self.posse_etapa_4 = Diario.POSSE_REGISTRO_ESCOLAR
#             self.posse_etapa_5 = Diario.POSSE_REGISTRO_ESCOLAR
#             self.save()
#
#     def abrir(self):
#         if not self.situacao == Diario.SITUACAO_ABERTO:
#             self.situacao = Diario.SITUACAO_ABERTO
#             self.save()
#
#     def is_carga_horaria_minima_cumprida(self):
#         return self.get_percentual_carga_horaria_cumprida() >= 90
#
#     def get_aulas_etapa_1(self):
#         return self.get_aulas(1)
#
#     def get_aulas_etapa_2(self):
#         return self.get_aulas(2)
#
#     def get_aulas_etapa_3(self):
#         return self.get_aulas(3)
#
#     def get_aulas_etapa_4(self):
#         return self.get_aulas(4)
#
#     def get_aulas_etapa_5(self):
#         return self.get_aulas(5)
#
#     def get_horario_aulas(self):
#         output = []
#         turnos_ids = self.horarioauladiario_set.all().values_list('horario_aula__turno', flat=True).distinct()
#         for turno in Turno.objects.filter(id__in=turnos_ids):
#             dias_semana = self.horarioauladiario_set.filter(horario_aula__turno=turno).order_by('dia_semana').values_list('dia_semana', flat=True).distinct()
#             for dia_semana in dias_semana:
#                 if output:
#                     output.append(' / ')
#                 numeros = []
#                 for numero in self.horarioauladiario_set.filter(horario_aula__turno=turno, dia_semana=dia_semana).values_list('horario_aula__numero', flat=True).distinct():
#                     if numero not in numeros:
#                         numeros.append(str(numero))
#                 numeros.sort()
#                 output.append('{}{}{}'.format(dia_semana + 1, turno.descricao[0], ''.join(numeros)))
#         return ''.join(output)
#
#     @transaction.atomic
#     def processar_horarios(self, dados):
#         self.horarioauladiario_set.all().delete()
#         for horario in dados.POST.getlist('horario'):
#             horario_aula_pk, dia_semana = horario.split(';')
#             horario_aula = HorarioAula.objects.get(pk=horario_aula_pk)
#             HorarioAulaDiario.objects.create(diario=self, dia_semana=dia_semana, horario_aula=horario_aula)
#
#     def get_horarios_aula_por_turno(self):
#         turnos_ids = self.horario_campus.horarioaula_set.values_list('turno_id', flat=True).distinct()
#         dias_semana = HorarioAulaDiario.DIA_SEMANA_CHOICES
#         turnos = Turno.objects.filter(id__in=turnos_ids).order_by('-id')
#         for turno in turnos:
#             turno.horarios_aula = []
#             turno.dias_semana = dias_semana
#             for horario_aula in turno.horarioaula_set.filter(horario_campus=self.horario_campus):
#                 horario_aula.dias_semana = []
#                 for dia_semana in dias_semana:
#                     numero_semama = dia_semana[0]
#                     marcado = False
#                     horarios = []
#                     descricao = ''
#                     qs = self.horarioauladiario_set.filter(dia_semana=numero_semama, horario_aula=horario_aula)
#                     marcado = qs.count()
#                     if marcado:
#                         descricao = '{}{}'.format(qs[0].diario.componente_curricular.componente.descricao_historico, qs[0].diario.get_descricao_dinamica())
#                         horarios.append(['diario', qs[0].diario.pk, descricao, qs[0].diario.componente_curricular.componente.sigla])
#                     horario_aula.dias_semana.append(dict(numero=numero_semama, marcado=marcado, conflito=False, horarios=horarios))
#                 turno.horarios_aula.append(horario_aula)
#         return turnos


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
                NotaAvaliacao.objects.filter(matricula_diario__id=matricula_diario_pk, item_configuracao_avaliacao=item_configuracao_avaliacao).update(nota=nota)
#                 matriculadiario = MatriculaDiario.objects.get(id=matricula_diario_pk)
#                 if nota is not None and matriculadiario.matricula_periodo.residente.pessoa_fisica.email:
#                     emails.append(matriculadiario.matricula_periodo.residente.pessoa_fisica.email)

        for etapa in etapas:
            for matricula_diario in MatriculaDiario.objects.filter(id__in=matriculas_diario_pk):
                matricula_diario.registrar_nota_etapa(etapa)


#         if emails:
#             disciplina = self.componente_curricular.componente.descricao
#             mensagem = """
# Caro(a) residente(a),
#
# Informamos que foi realizado lançamento de nota na disciplina {}.
#
#             """.format(
#                 disciplina
#             )
#
#             subject = '[SUAP] Lançamento de Nota - {}'.format(disciplina)
#             body = mensagem
#             from_email = settings.DEFAULT_FROM_EMAIL
#             send_mail(subject, body, from_email, [], bcc=emails, fail_silently=True)

#     def get_media_notas_by_etapa(self, etapa):
#         avg = 'nota_{}'.format(etapa == 5 and 'final' or etapa)
#         avg = MatriculaDiario.objects.filter(diario=self).aggregate(Avg(avg))['{}__avg'.format(avg)]
#         if avg:
#             return round(avg, 0)
#         else:
#             return 0
#
#     def get_media_medias(self):
#         soma = 0
#         qs_matriculas_diario = MatriculaDiario.objects.filter(diario=self)
#         for matricula_diario in qs_matriculas_diario:
#             soma += matricula_diario.get_media_disciplina() or 0
#         return round(soma / qs_matriculas_diario.count(), 0)
#
#     def get_media_medias_finais(self):
#         soma = 0
#         qs_matriculas_diario = MatriculaDiario.objects.filter(diario=self)
#         for matricula_diario in qs_matriculas_diario:
#             soma += matricula_diario.get_media_final_disciplina() or 0
#         return round(soma / qs_matriculas_diario.count(), 0)
#
#     @staticmethod
#     def get_diarios_choque_horario(ids_diarios, diario_pivot=None):
#         if diario_pivot:
#             ids_diarios.append(diario_pivot.pk)
#
#         horarios_diario = HorarioAulaDiario.objects.filter(diario__id__in=ids_diarios).values_list('dia_semana', 'horario_aula')
#         horarios = []
#         for horario_diario in horarios_diario:
#             horarios.append('{}/{}'.format(horario_diario[0], horario_diario[1]))
#
#         diarios_com_choque = []
#         for horario in horarios:
#             if horarios.count(horario) > 1:
#                 horario = horario.split('/')
#                 qs = Diario.objects.filter(id__in=ids_diarios, horarioauladiario__dia_semana=horario[0], horarioauladiario__horario_aula=horario[1])
#                 for diario in qs:
#                     if (
#                         Diario.objects.filter(
#                             calendario_academico__data_inicio__range=(diario.calendario_academico.data_inicio, diario.calendario_academico.data_fechamento_periodo),
#                             id__in=diario_pivot and [diario_pivot.pk] or ids_diarios,
#                             horarioauladiario__dia_semana=horario[0],
#                             horarioauladiario__horario_aula=horario[1],
#                         )
#                         .exclude(ignorar_choque_horario_renovacao_matricula=True)
#                         .exclude(id=diario.pk)
#                         .exists()
#                     ):
#                         if not diario in diarios_com_choque:
#                             diarios_com_choque.append(diario)
#         return diarios_com_choque
#
#     def get_qtd_vagas_restante(self):
#         return self.quantidade_vagas - self.matriculas_diarios_diario_residencia_set.all().count()
#
#     def get_etapas(self):
#         etapas = dict()
#         etapas.update({1: {'posse': self.em_posse_do_registro(1), 'configuracao_avaliacao': self.configuracao_avaliacao_1, 'numero_etapa_exibicao': 1}})
#         etapas.update({2: {'posse': self.em_posse_do_registro(2), 'configuracao_avaliacao': self.configuracao_avaliacao_2, 'numero_etapa_exibicao': 2}})
#         etapas.update({3: {'posse': self.em_posse_do_registro(3), 'configuracao_avaliacao': self.configuracao_avaliacao_3, 'numero_etapa_exibicao': 3}})
#         etapas.update({4: {'posse': self.em_posse_do_registro(4), 'configuracao_avaliacao': self.configuracao_avaliacao_4, 'numero_etapa_exibicao': 4}})
#         etapas.update({5: {'posse': self.em_posse_do_registro(5), 'configuracao_avaliacao': self.configuracao_avaliacao_5, 'numero_etapa_exibicao': 'Final'}})
#         return etapas
#
#     def save(self, *args, **kwargs):
#         pk = self.pk
#         qtd_etapas = self.componente_curricular.qtd_avaliacoes
#         if not pk:
#             if qtd_etapas <= 2:
#                 self.posse_etapa_4 = Diario.POSSE_REGISTRO_ESCOLAR
#                 self.posse_etapa_3 = Diario.POSSE_REGISTRO_ESCOLAR
#             if qtd_etapas < 2:
#                 self.posse_etapa_2 = Diario.POSSE_REGISTRO_ESCOLAR
#         else:
#             if self.segundo_semestre != Diario.objects.get(pk=pk).segundo_semestre:
#                 for professor_diario in self.professordiario_set.all():
#                     professor_diario.atualizar_data_posse()
#         super().save(*args, **kwargs)
#         if self.turma.curso_campus.plano_ensino and not self.planoensino_set.exists():
#             PlanoEnsino.objects.create(
#                 diario=self, coordenador_curso=self.turma.curso_campus.coordenador,
#                 ementa=self.componente_curricular.ementa
#             )
#
#         etapas = list(range(1, self.componente_curricular.qtd_avaliacoes + 1))
#         etapas = etapas and etapas + [5] or []
#
#         for etapa in etapas:
#             attr = 'configuracao_avaliacao_{}'.format(etapa)
#             if not pk and not getattr(self, attr)() and not hasattr(self, 'dividindo'):
#                 configuracao_avaliacao = ConfiguracaoAvaliacao.objects.get(pk=1)
#                 item_configuracao_avaliacao = configuracao_avaliacao.itemconfiguracaoavaliacao_set.first()
#
#                 configuracao_avaliacao.pk = None
#                 configuracao_avaliacao.diario = self
#                 configuracao_avaliacao.etapa = etapa
#                 configuracao_avaliacao.save()
#
#                 item_configuracao_avaliacao.pk = None
#                 item_configuracao_avaliacao.configuracao_avaliacao = configuracao_avaliacao
#                 item_configuracao_avaliacao.save()
#
#                 if self.utiliza_nota_atitudinal():
#                     configuracao_avaliacao.forma_calculo = ConfiguracaoAvaliacao.FORMA_CALCULO_MEDIA_ATITUDINAL
#                     configuracao_avaliacao.save()
#
#                     item_configuracao_avaliacao2 = configuracao_avaliacao.itemconfiguracaoavaliacao_set.first()
#                     item_configuracao_avaliacao2.pk = None
#                     item_configuracao_avaliacao2.configuracao_avaliacao = configuracao_avaliacao
#                     item_configuracao_avaliacao2.tipo = ItemConfiguracaoAvaliacao.TIPO_ATITUDINAL
#                     item_configuracao_avaliacao2.sigla = 'AT'
#                     item_configuracao_avaliacao2.descrição = 'Atitudinal'
#                     item_configuracao_avaliacao2.save()
#
#     def utiliza_nota_atitudinal(self):
#         return self.turma.matriz.nivel_ensino_id == NivelEnsino.MEDIO and Configuracao.get_valor_por_chave('edu', 'nota_atitudinal')
#
#     def delete(self, *args, **kwargs):
#         if self.pode_ser_excluido():
#             super().delete(*args, **kwargs)
#         else:
#             raise Exception('Este diário não pode ser excluído.')
#
#     @atomic()
#     def transferir(self, matriculas_diario, diario_destino, flag):
#         matriculas_diario = self.matriculas_diarios_diario_residencia_set.filter(pk__in=matriculas_diario)
#         for matricula_diario in matriculas_diario:
#             matricula_diario.transferir(diario_destino)
#
#     def get_locais_aula(self):
#         locais = []
#         if self.local_aula:
#             locais.append(self.local_aula)
#         for sala in self.locais_aula_secundarios.all():
#             locais.append(sala)
#         return locais or None
#
#     def pendente(self):
#         if not self.cumpriu_carga_horaria_minina():
#             return True
#         qtd_avaliacoes = self.componente_curricular.qtd_avaliacoes
#         for md in (
#             MatriculaDiario.objects.filter(diario=self, diario__calendario_academico__data_fechamento_periodo__lt=datetime.datetime.now())
#             .exclude(situacao=MatriculaDiario.SITUACAO_CANCELADO)
#             .order_by('id')
#             .distinct()
#         ):
#             if qtd_avaliacoes > 0 and md.nota_1 is None:
#                 return True
#             if qtd_avaliacoes > 1 and md.nota_2 is None:
#                 return True
#             if qtd_avaliacoes > 2 and (md.nota_3 is None or md.nota_4 is None):
#                 return True
#         return False

    def get_periodo_letivo(self):
        from residencia.models import CursoResidencia
        if self.turma.curso_campus.periodicidade == CursoResidencia.PERIODICIDADE_ANUAL:
            return 1
        return self.periodo_letivo if not self.segundo_ano else 2

#     def can_change(self, user):
#         return perms.realizar_procedimentos_academicos(user, self.turma.curso_campus)


class TipoPreceptorDiario(LogResidenciaModel):
    descricao = models.CharFieldPlus('Descrição', unique=True)

    class Meta:
        verbose_name = 'Tipo de Preceptor em Diário'
        verbose_name_plural = 'Tipos de Preceptor em Diário'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return '/residencia/visualizar/residencia/tipopreceptordiario/{}/'.format(self.pk)


class PreceptorDiario(LogResidenciaModel):

    SEARCH_FIELDS = ['preceptor__pessoa_fisica__search_fields_optimized']

    # Managers
    objects = models.Manager()

    diario = models.ForeignKeyPlus('residencia.Diario', verbose_name='Diário')
    preceptor = models.ForeignKeyPlus('rh.Servidor', verbose_name='Preceptor')
    tipo = models.ForeignKeyPlus('residencia.TipoPreceptorDiario', verbose_name='Tipo', on_delete=models.CASCADE)

    data_inicio_etapa_1 = models.DateFieldPlus(verbose_name='Data de Início', help_text='Início da posse do diário para a 1ª etapa', null=True, blank=True)
    data_fim_etapa_1 = models.DateFieldPlus(verbose_name='Data de Encerramento', help_text='Encerramento da posse incluindo 5 dias de tolerância', null=True, blank=True)

    data_inicio_etapa_2 = models.DateFieldPlus(verbose_name='Data de Início', help_text='Início da posse do diário para a 2ª etapa', null=True, blank=True)
    data_fim_etapa_2 = models.DateFieldPlus(verbose_name='Data de Encerramento', help_text='Encerramento da posse incluindo 5 dias de tolerância', null=True, blank=True)

    data_inicio_etapa_3 = models.DateFieldPlus(verbose_name='Data de Início', help_text='Início da posse do diário para a 3ª etapa', null=True, blank=True)
    data_fim_etapa_3 = models.DateFieldPlus(verbose_name='Data de Encerramento', help_text='Encerramento da posse incluindo 5 dias de tolerância', null=True, blank=True)

    data_inicio_etapa_4 = models.DateFieldPlus(verbose_name='Data de Início', help_text='Início da posse do diário para a 4ª etapa', null=True, blank=True)
    data_fim_etapa_4 = models.DateFieldPlus(verbose_name='Data de Encerramento', help_text='Encerramento da posse incluindo 5 dias de tolerância', null=True, blank=True)

    data_inicio_etapa_final = models.DateFieldPlus(verbose_name='Data de Início', help_text='Início da posse do diário para a etapa final', null=True, blank=True)
    data_fim_etapa_final = models.DateFieldPlus(verbose_name='Data de Encerramento', help_text='Encerramento da posse incluindo 5 dias de tolerância', null=True, blank=True)
    ativo = models.BooleanField(verbose_name='Ativo', default=True)
    financiamento_externo = models.BooleanField(
        verbose_name='Financiamento Externo', default=False, help_text='Vínculo com financiamento extraorçamentário (Bolsa, PRONATEC, Mulheres Mil, ETEC, UAB, etc.)'
    )
    percentual_ch = models.PositiveSmallIntegerField(
        verbose_name='Percentual da Carga Horária', null=True, help_text='Valor entre 0 e 100 correspondente ao percentual da carga horária ministrada pelo preceptor.'
    )
    periodo_letivo_ch = models.IntegerField(
        verbose_name='Período Letivo da Carga-Horária',
        null=True,
        blank=True,
        choices=settings.PERIODO_LETIVO_CHOICES,
        help_text='Informar caso o percentual da carga horária ministrada se refira a apenas um período letivo.',
    )

    class Meta:
        verbose_name = 'Vínculo de Preceptor em Diário'
        verbose_name_plural = 'Vínculos de Preceptor em Diário'

    def __str__(self):
        return 'Vínculo do(a) Preceptor(a) {} no diário {}'.format(self.preceptor, self.diario.pk)

    def get_percentual_ch(self, periodo_letivo=None):
        if periodo_letivo is None or self.periodo_letivo_ch is None or self.periodo_letivo_ch == periodo_letivo:
            return self.percentual_ch or 0
        return 0

    def can_delete(self, user=None):
        return True


# class ProfessorDiario(LogResidenciaModel):
#
#     SEARCH_FIELDS = ['professor__vinculo__pessoa__pessoa_fisica__search_fields_optimized']
#
#     # Managers
#     objects = models.Manager()
#     locals = FiltroDiretoriaManager('diario__turma__curso_campus__diretoria')
#
#     diario = models.ForeignKeyPlus('residencia.Diario', verbose_name='Diário')
#     professor = models.ForeignKeyPlus('residencia.Professor', verbose_name='Professor')
#     tipo = models.ForeignKeyPlus('residencia.TipoProfessorDiario', verbose_name='Tipo', on_delete=models.CASCADE)
#
#     data_inicio_etapa_1 = models.DateFieldPlus(verbose_name='Data de Início', help_text='Início da posse do diário para a 1ª etapa', null=True, blank=True)
#     data_fim_etapa_1 = models.DateFieldPlus(verbose_name='Data de Encerramento', help_text='Encerramento da posse incluindo 5 dias de tolerância', null=True, blank=True)
#
#     data_inicio_etapa_2 = models.DateFieldPlus(verbose_name='Data de Início', help_text='Início da posse do diário para a 2ª etapa', null=True, blank=True)
#     data_fim_etapa_2 = models.DateFieldPlus(verbose_name='Data de Encerramento', help_text='Encerramento da posse incluindo 5 dias de tolerância', null=True, blank=True)
#
#     data_inicio_etapa_3 = models.DateFieldPlus(verbose_name='Data de Início', help_text='Início da posse do diário para a 3ª etapa', null=True, blank=True)
#     data_fim_etapa_3 = models.DateFieldPlus(verbose_name='Data de Encerramento', help_text='Encerramento da posse incluindo 5 dias de tolerância', null=True, blank=True)
#
#     data_inicio_etapa_4 = models.DateFieldPlus(verbose_name='Data de Início', help_text='Início da posse do diário para a 4ª etapa', null=True, blank=True)
#     data_fim_etapa_4 = models.DateFieldPlus(verbose_name='Data de Encerramento', help_text='Encerramento da posse incluindo 5 dias de tolerância', null=True, blank=True)
#
#     data_inicio_etapa_final = models.DateFieldPlus(verbose_name='Data de Início', help_text='Início da posse do diário para a etapa final', null=True, blank=True)
#     data_fim_etapa_final = models.DateFieldPlus(verbose_name='Data de Encerramento', help_text='Encerramento da posse incluindo 5 dias de tolerância', null=True, blank=True)
#     ativo = models.BooleanField(verbose_name='Ativo', default=True)
#     financiamento_externo = models.BooleanField(
#         verbose_name='Financiamento Externo', default=False, help_text='Vínculo com financiamento extraorçamentário (Bolsa, PRONATEC, Mulheres Mil, ETEC, UAB, etc.)'
#     )
#     percentual_ch = models.PositiveSmallIntegerField(
#         verbose_name='Percentual da Carga Horária', null=True, help_text='Valor entre 0 e 100 correspondente ao percentual da carga horária ministrada pelo professor.'
#     )
#     periodo_letivo_ch = models.IntegerField(
#         verbose_name='Período Letivo da Carga-Horária',
#         null=True,
#         blank=True,
#         choices=settings.PERIODO_LETIVO_CHOICES,
#         help_text='Informar caso o percentual da carga horária ministrada se refira a apenas um período letivo.',
#     )
#
#     class Meta:
#         verbose_name = 'Vínculo de Professor em Diário'
#         verbose_name_plural = 'Vínculos de Professor em Diário'
#
#     def __str__(self):
#         return 'Vínculo do professor {} no diário {}'.format(self.professor, self.diario.pk)
#
#     def is_mesmo_campus_do_curso(self):
#         return self.professor.get_uo() == self.diario.horario_campus.uo
#
#     def can_delete(self, user=None):
#         return not self.aula_set.exists() and not self.is_rit_publicado()
#
#     def atualizar_data_posse(self):
#         qtd_etapas = self.diario.componente_curricular.qtd_avaliacoes
#         if qtd_etapas >= 1:
#             self.data_inicio_etapa_1 = self.diario.get_inicio_etapa_1()
#             if self.diario.get_fim_etapa_1():
#                 self.data_fim_etapa_1 = somar_data(self.diario.get_fim_etapa_1(), 7)
#             else:
#                 self.data_fim_etapa_1 = self.diario.get_fim_etapa_1()
#
#         if qtd_etapas >= 2:
#             self.data_inicio_etapa_2 = self.diario.get_inicio_etapa_2()
#             if self.diario.get_fim_etapa_2():
#                 self.data_fim_etapa_2 = somar_data(self.diario.get_fim_etapa_2(), 7)
#             else:
#                 self.data_fim_etapa_2 = self.diario.get_fim_etapa_2()
#
#         if qtd_etapas >= 3:
#             self.data_inicio_etapa_3 = self.diario.get_inicio_etapa_3()
#             if self.diario.get_fim_etapa_3():
#                 self.data_fim_etapa_3 = somar_data(self.diario.get_fim_etapa_3(), 7)
#             else:
#                 self.data_fim_etapa_3 = self.diario.get_fim_etapa_3()
#
#             self.data_inicio_etapa_4 = self.diario.get_inicio_etapa_4()
#             if self.diario.get_fim_etapa_4():
#                 self.data_fim_etapa_4 = somar_data(self.diario.get_fim_etapa_4(), 7)
#             else:
#                 self.data_fim_etapa_4 = self.diario.get_fim_etapa_4()
#
#         self.data_inicio_etapa_final = self.diario.get_inicio_etapa_final()
#         self.data_fim_etapa_final = somar_data(self.diario.get_fim_etapa_final(), 7)
#         self.save()
#
#     def save(self, *args, **kwargs):
#         if not self.is_rit_publicado():
#             super().save()
#             grupo = Group.objects.get(name='Professor')
#             self.professor.vinculo.user.groups.add(grupo)
#             self.professor.cursos_lecionados.add(self.diario.turma.curso_campus)
#
#     def delete(self, *args, **kwargs):
#         if self.professor.professordiario_set.filter(diario__turma__curso_campus=self.diario.turma.curso_campus).count() == 1:
#             self.professor.cursos_lecionados.remove(self.diario.turma.curso_campus)
#
#         super().delete(*args, **kwargs)
#
#     def get_percentual_ch(self, periodo_letivo=None):
#         if periodo_letivo is None or self.periodo_letivo_ch is None or self.periodo_letivo_ch == periodo_letivo:
#             return self.percentual_ch or 0
#         return 0
#
#     def get_carga_horaria_ministrada(self):
#         qs = Aula.objects.filter(professor_diario=self, data__lte=datetime.date.today())
#         qs = qs | Aula.objects.filter(outros_professor_diario=self, data__lte=datetime.date.today())
#         return qs.aggregate(Sum('quantidade')).get('quantidade__sum') or 0
#
#     def get_percentual_ch_ministrada(self, ano_novo_calculo=2023):
#         if self.diario.ano_letivo.ano < ano_novo_calculo:
#             return self.get_percentual_ch()
#         else:
#             total = self.diario.componente_curricular.componente.ch_hora_aula
#             ministrada = self.get_carga_horaria_ministrada()
#             return total and int(ministrada * 100 / total) or 0
#
#     def get_qtd_creditos_efetiva(self, periodo_letivo=None):
#         return int(math.ceil(self.diario.componente_curricular.componente.ch_qtd_creditos * (self.get_percentual_ch(periodo_letivo=periodo_letivo) / 100.0)))
#
#     def get_qtd_creditos_efetiva_1(self):
#         return self.get_qtd_creditos_efetiva(1)
#
#     def get_qtd_creditos_efetiva_2(self):
#         return self.get_qtd_creditos_efetiva(2)
#
#     def get_periodo_posse(self):
#         periodo = []
#         vetor = []
#         inicio = None
#         fim = None
#
#         if self.diario.componente_curricular.qtd_avaliacoes == 0:
#             periodo.append((self.data_inicio_etapa_1, self.data_fim_etapa_1))
#
#         vetor.append([self.data_inicio_etapa_1, self.data_fim_etapa_1])
#         if self.diario.componente_curricular.qtd_avaliacoes == 2:
#             vetor.append([self.data_inicio_etapa_2, self.data_fim_etapa_2])
#         if self.diario.componente_curricular.qtd_avaliacoes == 4:
#             vetor.append([self.data_inicio_etapa_2, self.data_fim_etapa_2])
#             vetor.append([self.data_inicio_etapa_3, self.data_fim_etapa_3])
#             vetor.append([self.data_inicio_etapa_4, self.data_fim_etapa_4])
#         vetor.append([self.data_inicio_etapa_final, self.data_fim_etapa_final])
#
#         for elem in vetor:
#             if not inicio and elem[0]:
#                 inicio = elem[0]
#                 fim = elem[1]
#             elif inicio and elem[0]:
#                 fim = elem[1]
#             elif inicio and not elem[0]:
#                 periodo.append((inicio, fim))
#                 inicio = None
#                 fim = None
#         if inicio:
#             periodo.append((inicio, fim))
#
#         return periodo
#
#     def is_rit_publicado(self, vinculo=None, diario=None, periodo_letivo_ch=None, financiamento_externo=None):
#         if financiamento_externo is None:
#             financiamento_externo = self.financiamento_externo
#
#         if 'pit_rit_v2' in settings.INSTALLED_APPS and not financiamento_externo:
#
#             from pit_rit_v2.models import PlanoIndividualTrabalhoV2
#
#             qs = PlanoIndividualTrabalhoV2.objects.filter(publicado=True)
#             if vinculo and diario:
#                 qs = qs.filter(professor__vinculo_id=vinculo.id, ano_letivo_id=diario.ano_letivo.id)
#                 if diario.is_semestral_segundo_semestre():
#                     return qs.filter(periodo_letivo=2).exists()
#                 elif periodo_letivo_ch:
#                     return qs.filter(periodo_letivo=periodo_letivo_ch).exists()
#                 else:
#                     return qs.filter(periodo_letivo=diario.periodo_letivo).exists()
#             else:
#                 qs = qs.filter(professor_id=self.professor.id, ano_letivo_id=self.diario.ano_letivo.id)
#                 if self.diario.is_semestral_segundo_semestre():
#                     return qs.filter(periodo_letivo=2).exists()
#                 elif self.periodo_letivo_ch:
#                     return qs.filter(periodo_letivo=self.periodo_letivo_ch).exists()
#                 else:
#                     return qs.filter(periodo_letivo=self.diario.periodo_letivo).exists()
#
#         return False
#
#     def get_resumo_ch_prevista(self):
#         if self.periodo_letivo_ch:
#             periodo_letivo_ch = '{}.{}'.format(self.diario.ano_letivo, self.periodo_letivo_ch)
#         else:
#             periodo_letivo_ch = '{}'.format(self.diario.ano_letivo)
#         return '{}/{}: {}%'.format(self.professor.get_matricula(), periodo_letivo_ch, self.percentual_ch or 0)
#
#     def get_diarios_choque_horario(self):
#         diarios = []
#         qs = ProfessorDiario.objects.filter(
#             professor=self.professor,
#             diario__ano_letivo=self.diario.ano_letivo,
#             diario__periodo_letivo=self.diario.periodo_letivo
#         ).exclude(pk=self.pk).exclude(diario__ignorar_choque_horario_renovacao_matricula=True)
#         horarios = set(self.diario.horarioauladiario_set.values_list(
#             'dia_semana', 'horario_aula'
#         ))
#         for professor_diario in qs:
#             outros_horarios = set(professor_diario.diario.horarioauladiario_set.values_list(
#                 'dia_semana', 'horario_aula'
#             ))
#             if horarios & outros_horarios:
#                 diarios.append(professor_diario.diario.id)
#         return diarios


# class OcorrenciaDiario(LogResidenciaModel):
#     professor_diario = models.ForeignKeyPlus(ProfessorDiario, verbose_name='Professor')
#     data = models.DateFieldPlus(verbose_name='Data')
#     descricao = models.TextField('Descrição')
#
#     class Meta:
#         verbose_name = 'Ocorrência'
#         verbose_name_plural = 'Ocorrências'
#
#     def __str__(self):
#         return '{} {}'.format(self.data, self.descricao)
#
#
# class Aula(LogResidenciaModel):
#     ETAPA_1 = 1
#     ETAPA_2 = 2
#     ETAPA_3 = 3
#     ETAPA_4 = 4
#     ETAPA_5 = 5
#     ETAPA_CHOICES = [[ETAPA_1, 'Primeira'], [ETAPA_2, 'Segunda'], [ETAPA_3, 'Terceira'], [ETAPA_4, 'Quarta'], [ETAPA_5, 'Final']]
#     ETAPA_CHOICES_SEGUNGO_SEMESTRE = [[ETAPA_1, 'Terceira'], [ETAPA_2, 'Quarta']]
#
#     AULA = 1
#     PRATICA = 2
#     EXTENSAO = 3
#     PRATICA_COMO_COMPONENTE_CURRICULAR = 4
#     VISITA_TECNICA = 5
#
#     TIPO_CHOICES = [
#         [AULA, 'Teórica'],
#         [PRATICA, 'Prática'],
#         [EXTENSAO, 'Extensão'],
#         [PRATICA_COMO_COMPONENTE_CURRICULAR, 'Prática como Componente Curricular'],
#         [VISITA_TECNICA, 'Visita Técnica/Aula de Campo'],
#     ]
#
#     professor_diario = models.ForeignKeyPlus(ProfessorDiario, verbose_name='Professor')
#     etapa = models.PositiveIntegerField(verbose_name='Etapa', default=1, choices=ETAPA_CHOICES)
#     quantidade = models.PositiveIntegerField(default=1, help_text='Quantidade de aulas ministradas')
#     # plano de retomada de aulas em virtude da pandemia (COVID19)
#     url = models.CharFieldPlus(verbose_name='URL da Aula', null=True, blank=True)
#     data = models.DateFieldPlus(verbose_name='Data')
#     conteudo = models.TextField('Conteúdo')
#     tipo = models.PositiveIntegerFieldPlus(verbose_name='Tipo', choices=TIPO_CHOICES, null=True, default=AULA)
#     ead = models.BooleanField(verbose_name='EAD', default=False, blank=True)
#     outros_professor_diario = models.ManyToManyFieldPlus(ProfessorDiario, related_name='outros_professor_diario_set', verbose_name='Outros Professores', help_text='A CH desta aula será compartilhada com os professores selecionados', blank=True)
#
#     class Meta:
#         verbose_name = 'Aula'
#         verbose_name_plural = 'Aulas'
#         ordering = ('etapa', 'data')
#
#     def is_ministrada(self):
#         return self.data <= datetime.date.today()
#
#     def __str__(self):
#         return 'Aula do professor {} no diário {}'.format(self.professor_diario.professor, self.professor_diario.diario.pk)
#
#     def get_diario(self):
#         return self.professor_diario.diario
#
#     def can_change(self, user):
#         user = user or tl.get_user()
#         em_posse_do_registro = self.professor_diario.diario.em_posse_do_registro(self.etapa)
#         if em_posse_do_registro:
#             return False
#         etapa = self.etapa == 5 and 'final' or self.etapa
#         inicio = getattr(self.professor_diario, "data_inicio_etapa_{}".format(etapa))
#         fim = getattr(self.professor_diario, "data_fim_etapa_{}".format(etapa))
#         if inicio and fim and self.data and self.data >= inicio and self.data <= fim and self.professor_diario.diario.is_professor_diario(user) and self.professor_diario.professor.vinculo.user == user:
#             return True
#         return False
#
#     def clean(self):
#         adicional = self.quantidade
#         if self.pk:
#             adicional -= Aula.objects.get(pk=self.pk).quantidade
#         if self.quantidade < 0:
#             raise ValidationError('A quantidade de horas deve ser um número inteiro positivo')
#         if (
#             self.data
#             and hasattr(self, 'professor_diario')
#             and (self.professor_diario.diario.calendario_academico.get_data_inicio_letivo() > self.data or self.data > self.professor_diario.diario.get_fim_etapa_final())
#         ):
#             raise ValidationError(
#                 'As aulas devem estar no intervalo de {} a {}'.format(
#                     format_(self.professor_diario.diario.calendario_academico.get_data_inicio_letivo()), format_(self.professor_diario.diario.get_fim_etapa_final())
#                 )
#             )
#         if not self.professor_diario_id:
#             raise ValidationError('A aula precisa estar atribuída a um professor.')
#         user = tl.get_user()
#         if self.professor_diario.diario.is_professor_diario(user):
#             if self.professor_diario.diario.em_posse_do_registro(self.etapa):
#                 raise ValidationError('A etapa precisa estar em posse do professor.')
#             if not self.can_change(user):
#                 raise ValidationError('Verifique se a data da aula está no período de posse da etapa selecionada.')
#
#     def pode_registrar_chamada(self, user):
#         professordiario = ProfessorDiario.objects.filter(professor__vinculo__user=user, diario_id=self.professor_diario.diario.pk).first()
#         if professordiario:
#             etapa = self.etapa == 5 and 'final' or self.etapa
#             inicio = getattr(professordiario, "data_inicio_etapa_{}".format(etapa))
#             fim = getattr(professordiario, "data_fim_etapa_{}".format(etapa))
#             if inicio and fim and self.data and self.data >= inicio and self.data <= fim:
#                 return True
#         return False
#
#     def get_professores(self):
#         professores = [self.professor_diario.professor.vinculo.pessoa.nome_usual, ]
#         for professor_diario in self.outros_professor_diario.all():
#             professores.append(professor_diario.professor.vinculo.pessoa.nome_usual)
#         return professores
#
#
# class Falta(LogResidenciaModel):
#     matricula_diario = models.ForeignKeyPlus(MatriculaDiario, verbose_name='Aluno')
#     aula = models.ForeignKeyPlus(Aula, verbose_name='Aula')
#     quantidade = models.IntegerField(default=0)
#     abono_faltas = models.ForeignKeyPlus('residencia.AbonoFaltas', verbose_name='Abono Faltas', null=True, blank=True)
#
#     class Meta:
#         verbose_name = 'Falta'
#         verbose_name_plural = 'Faltas'
#         unique_together = (('matricula_diario', 'aula'),)
#
#     def __str__(self):
#         return 'Falta referente à {} hora(s)/aula(s) do residente {} na aula {}'.format(self.quantidade, self.matricula_diario.matricula_periodo.residente.matricula, self.aula.pk)
#
#     def get_residente(self):
#         return self.matricula_diario.matricula_periodo.residente
#
#     def get_diario(self):
#         return self.matricula_diario.diario
#
#     def pode_ser_registrada(self):
#         return self.aula.data <= datetime.date.today()
#
#
# class MaterialAula(LogResidenciaModel):
#     professor = models.ForeignKeyPlus('residencia.Professor', null=False, verbose_name='Professor', on_delete=models.CASCADE)
#     descricao = models.CharFieldPlus(width=500, null=False, verbose_name='Descrição')
#     data_cadastro = models.DateTimeField(auto_now_add=True, null=False, verbose_name='Data de Cadastro')
#     arquivo = models.FileFieldPlus(upload_to='edu/material_aula/', null=True, blank=True, verbose_name='Upload do arquivo')
#     url = models.CharFieldPlus(width=500, null=True, blank=True, verbose_name='Url do arquivo')
#     publico = models.BooleanField(verbose_name='Público', default=False, help_text='Permitir que outros professores visualizem o material')
#
#     class Meta:
#         verbose_name = 'Material de Aula'
#         verbose_name_plural = 'Materiais de Aula'
#         ordering = ('-data_cadastro',)
#
#     def __str__(self):
#         return self.descricao
#
#     def get_absolute_url(self):
#         if self.arquivo:
#             return self.arquivo.url
#         if self.url.startswith('http://') or self.url.startswith('https://') or self.url.startswith('ftp://'):
#             return self.url
#         else:
#             return 'http://{}'.format(self.url)
#
#     def can_change(self, user):
#         return self.professor.vinculo.user == user
#
#     def clone(self, user):
#         self.pk = None
#         self.professor = Professor.objects.filter(vinculo__user=user)
#         if self.professor:
#             self.publico = False
#             self.save()
#
#
# class MaterialDiario(LogResidenciaModel):
#     material_aula = models.ForeignKeyPlus('residencia.MaterialAula', null=False, verbose_name='Material de Aula', on_delete=models.CASCADE)
#     professor_diario = models.ForeignKeyPlus('residencia.ProfessorDiario', null=False, verbose_name='Professor Diário', on_delete=models.CASCADE)
#     data_vinculacao = models.DateField('Data de Vinculação', null=True, default=datetime.date.today)
#
#     class Meta:
#         verbose_name = 'Vínculo de Material em Diário'
#         verbose_name_plural = 'Vínculos de Material em Diário'


class ConfiguracaoAvaliacao(LogResidenciaModel):
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

    diario = models.ForeignKeyPlus('residencia.Diario', verbose_name='Diário', null=True)
    etapa = models.IntegerField('Etapa', null=True)
    forma_calculo = models.IntegerField(choices=FORMA_CALCULO_CHOICES, default=FORMA_CALCULO_MEDIA_ARITMETICA, verbose_name='Forma de Cálculo')
    divisor = models.PositiveIntegerField('Divisor', null=True, blank=True)
    maior_nota = models.BooleanField('Ignorar Maior Nota', default=False)
    menor_nota = models.BooleanField('Ignorar Menor Nota', default=False)
    autopublicar = models.BooleanField('Autopublicar Notas', default=True, help_text='As notas das avaliacões serão exibidas aos residentes a medida que forem lançadas.')
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


class ItemConfiguracaoAvaliacao(LogResidenciaModel):
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

    configuracao_avaliacao = models.ForeignKeyPlus('residencia.ConfiguracaoAvaliacao', verbose_name='Configuração da Avaliação')
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


class NotaAvaliacao(LogResidenciaModel):
    matricula_diario = models.ForeignKeyPlus('residencia.MatriculaDiario', verbose_name='Matrícula Diário', on_delete=models.CASCADE)
    item_configuracao_avaliacao = models.ForeignKeyPlus('residencia.ItemConfiguracaoAvaliacao', verbose_name='Item de Configuração de Avaliação', on_delete=models.CASCADE)
    nota = models.NotaField('Nota', null=True)

    class Meta:
        verbose_name = 'Nota de Avaliação'
        verbose_name_plural = 'Notas de Avaliações'
        ordering = ('-id',)

    def __str__(self):
        return 'Nota {} do residente {} na avaliação {} do diário {}'.format(
            self.nota is None and 'não lançada' or self.nota,
            self.matricula_diario.matricula_periodo.residente.matricula,
            self.item_configuracao_avaliacao.sigla,
            self.matricula_diario.diario.pk,
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
