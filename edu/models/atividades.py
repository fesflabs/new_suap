# -*- coding: utf-8 -*-
from djtools.db import models
from edu.models.logs import LogModel
from edu.models.cadastros_gerais import Turno
from django.contrib.contenttypes.fields import GenericForeignKey, ContentType


class HorarioAtividadeExtra(LogModel):

    DIA_SEMANA_SEG = 1
    DIA_SEMANA_TER = 2
    DIA_SEMANA_QUA = 3
    DIA_SEMANA_QUI = 4
    DIA_SEMANA_SEX = 5
    DIA_SEMANA_SAB = 6
    DIA_SEMANA_DOM = 7
    DIA_SEMANA_CHOICES = [
        [DIA_SEMANA_SEG, 'Segunda'],
        [DIA_SEMANA_TER, 'Terça'],
        [DIA_SEMANA_QUA, 'Quarta'],
        [DIA_SEMANA_QUI, 'Quinta'],
        [DIA_SEMANA_SEX, 'Sexta'],
        [DIA_SEMANA_SAB, 'Sábado'],
        [DIA_SEMANA_DOM, 'Domingo'],
    ]

    ATIVIDADE_ESTUDO = 1
    ATIVIDADE_LAZER = 2

    TIPO_CHOICES = [[ATIVIDADE_ESTUDO, 'Atividade de Estudo'], [ATIVIDADE_LAZER, 'Atividade de Lazer']]

    tipo_atividade = models.PositiveIntegerField(choices=TIPO_CHOICES, default=ATIVIDADE_ESTUDO, verbose_name='Tipo de Atividade')
    descricao_atividade = models.CharFieldPlus('Descrição')
    matricula_periodo = models.ForeignKeyPlus('edu.MatriculaPeriodo')
    horario_aula = models.ForeignKeyPlus('edu.HorarioAula', on_delete=models.CASCADE)
    dia_semana = models.PositiveIntegerField(choices=DIA_SEMANA_CHOICES)

    class Meta:
        verbose_name = 'Horário da Atividade Extra'
        verbose_name_plural = 'Horários das Atividades Extras'

    def get_aluno(self):
        return self.matricula_periodo.aluno

    def get_horario_aulas(self):
        output = []
        turnos_ids = self.matricula_periodo.horarioatividadeextra_set.all().values_list('horario_aula__turno', flat=True).distinct()
        for turno in Turno.objects.filter(id__in=turnos_ids):
            dias_semana = (
                self.matricula_periodo.horarioatividadeextra_set.filter(horario_aula__turno=turno, tipo_atividade=self.tipo_atividade, descricao_atividade=self.descricao_atividade)
                .order_by('dia_semana')
                .values_list('dia_semana', flat=True)
                .distinct()
            )
            for dia_semana in dias_semana:
                if output:
                    output.append(' / ')
                numeros = []
                for numero in (
                    self.matricula_periodo.horarioatividadeextra_set.filter(
                        horario_aula__turno=turno, dia_semana=dia_semana, tipo_atividade=self.tipo_atividade, descricao_atividade=self.descricao_atividade
                    )
                    .values_list('horario_aula__numero', flat=True)
                    .distinct()
                ):
                    if numero not in numeros:
                        numeros.append(str(numero))
                numeros.sort()
                output.append('{}{}{}'.format(dia_semana + 1, turno.descricao[0], ''.join(numeros)))
        return ''.join(output)


class AtividadeCurricularExtensao(LogModel):
    matricula_periodo = models.ForeignKeyPlus('edu.MatriculaPeriodo')
    descricao = models.CharFieldPlus('Descrição')
    carga_horaria = models.IntegerField(verbose_name='Carga-Horária')

    referencia = GenericForeignKey('tipo_referencia', 'id_referencia')
    tipo_referencia = models.ForeignKeyPlus(ContentType, verbose_name='Tipo da Referência', on_delete=models.CASCADE, null=True)
    id_referencia = models.PositiveIntegerField(verbose_name='Referência', null=True)

    concluida = models.BooleanField(verbose_name='Concluída', default=False)
    aprovada = models.BooleanField(verbose_name='Aprovada', null=True)

    class Meta:
        verbose_name = 'Atividade Curricular de Extensão'
        verbose_name_plural = 'Atividades Curriculares de Extensão'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.matricula_periodo.aluno.atualizar_situacao()

    @staticmethod
    def registrar(aluno, modelo, pk, ch, descricao, concluida=False):
        tipo_referencia = ContentType.objects.get_for_model(modelo)
        qs = AtividadeCurricularExtensao.objects.filter(tipo_referencia=tipo_referencia, id_referencia=pk)
        if ch:
            atividade = qs.first() or AtividadeCurricularExtensao(tipo_referencia=tipo_referencia, id_referencia=pk)
            if atividade.carga_horaria != ch:
                atividade.aprovada = None
            atividade.concluida = concluida
            atividade.carga_horaria = ch
            atividade.descricao = descricao
            atividade.matricula_periodo = aluno.get_ultima_matricula_periodo()
            atividade.save()
        else:
            qs.delete()
