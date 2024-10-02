# -*- coding: utf-8 -*-

from djtools.db import models
from djtools.templatetags.filters import format_
from edu.models.logs import LogModel


class ConvocacaoENADE(LogModel):
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano letivo', null=True, on_delete=models.CASCADE)
    data_prova = models.DateFieldPlus(
        'Data de Realização da Prova', null=True, blank=True, help_text="Após inserir esta data, a lista de alunos convocados não poderá ser mais atualizada."
    )
    cursos = models.ManyToManyFieldPlus('edu.CursoCampus')
    encerrado = models.BooleanField('Encerrado?', default=False)
    descricao = models.CharFieldPlus(verbose_name='Descrição', null=True, blank=True, max_length=255)
    edital = models.FileFieldPlus(
        'Edital',
        upload_to='edu/convocacao_enade_edital/',
        null=True,
        blank=True,
        check_mimetype=False,
        help_text='Arquivo em PDF referente ao edital de convocação do ENADE.',
        filetypes=['pdf'],
    )

    portaria = models.FileFieldPlus(
        'Portaria',
        upload_to='edu/convocacao_enade_edital/',
        null=True,
        blank=True,
        check_mimetype=False,
        help_text='Arquivo em PDF referente à portaria de convocação do ENADE.',
        filetypes=['pdf'],
    )

    # Ingressantes
    percentual_minimo_ingressantes = models.PositiveIntegerField('Percentual Mínimo (%) para Ingressantes')
    percentual_maximo_ingressantes = models.PositiveIntegerField('Percentual Máximo (%) para Ingressantes')

    # Concluintes
    percentual_minimo_concluintes = models.PositiveIntegerField('Percentual Mínimo (%) para Concluintes')
    percentual_maximo_concluintes = models.PositiveIntegerField('Percentual Máximo (%) para Concluintes')

    def __str__(self):
        return 'Convocação {}: {}'.format(self.ano_letivo, format_(self.descricao))

    def get_absolute_url(self):
        return '/edu/convocacao_enade/{}/'.format(self.pk)

    class Meta:
        verbose_name = 'Convocação do ENADE'
        verbose_name_plural = 'Convocações do ENADE'


class RegistroConvocacaoENADE(LogModel):
    SITUACAO_PRESENTE = 1
    SITUACAO_DISPENSADO = 2
    SITUACAO_AUSENTE = 3
    SITUACAO_CHOICES = ((SITUACAO_PRESENTE, 'Regular'), (SITUACAO_DISPENSADO, 'Dispensado'), (SITUACAO_AUSENTE, 'Ausente'))

    TIPO_CONVOCACAO_INGRESSANTE = 1
    TIPO_CONVOCACAO_CONCLUINTE = 2
    TIPO_CONVOCACAO_CHOICES = ((TIPO_CONVOCACAO_INGRESSANTE, 'Ingressante'), (TIPO_CONVOCACAO_CONCLUINTE, 'Concluinte'))

    aluno = models.ForeignKeyPlus('edu.Aluno')
    convocacao_enade = models.ForeignKeyPlus('edu.ConvocacaoENADE', null=True)
    situacao = models.PositiveIntegerField('Situação', null=True, choices=SITUACAO_CHOICES)
    percentual_ch_cumprida = models.DecimalFieldPlus('Situação', null=True)
    justificativa_dispensa = models.ForeignKeyPlus('edu.JustificativaDispensaENADE', null=True, blank=True, verbose_name='Justificativa de Dispensa')
    tipo_convocacao = models.PositiveIntegerField('Tipo da Convocação', null=True, choices=TIPO_CONVOCACAO_CHOICES)

    objects = models.Manager()

    class Meta:
        ordering = ('aluno__curso_campus', 'aluno__pessoa_fisica__nome')

    def remover_situacao(self):
        self.situacao = None
        self.justificativa_dispensa = None
        self.save()

    def save(self, *args, **kwargs):
        super(RegistroConvocacaoENADE, self).save(*args, **kwargs)
        self.aluno.atualizar_situacao('Lançamento do ENADE')

    def delete(self, *args, **kwargs):
        super(RegistroConvocacaoENADE, self).delete(*args, **kwargs)
        self.aluno.atualizar_situacao('Exclusão de Lançamento do ENADE')

    def get_situacao_para_diploma_digital(self):
        OPCOES = {
            5: 'Ingressante / Participante',
            1: 'Dispensado, em razão do calendário trienal',
            2: 'Dispensado, em razão da natureza do curso',
            3: 'Dispensado, por razão de ordem pessoal',
            4: 'Dispensado, por ato da instituição de ensino',
            7: 'Estudante não habilitado ao ENADE em razão do calendário do ciclo avaliativo'
        }
        if self.tipo_convocacao == RegistroConvocacaoENADE.TIPO_CONVOCACAO_INGRESSANTE:
            condicao = 'Ingressante'
        else:
            condicao = 'Concluinte'
        if self.situacao == RegistroConvocacaoENADE.SITUACAO_PRESENTE or self.justificativa_dispensa.id == 5:
            return {
                "SituacaoENADE": {
                    "Habilitado": {
                        "Condicao": condicao,
                        "Edicao": str(self.convocacao_enade.data_prova.year),
                    }
                }
            }
        if self.justificativa_dispensa.id in (1, 7):
            motivo = 'Estudante não habilitado ao Enade em razão do calendário do ciclo avaliativo'
        elif self.justificativa_dispensa.id in (2,):
            motivo = 'Estudante não habilitado ao Enade em razão da natureza do projeto pedagógico do curso'
        else:
            motivo = OPCOES.get(self.justificativa_dispensa.id, 'Motivo não informado')
        return {
            "SituacaoENADE": {
                "NaoHabilitado": {
                    "Condicao": condicao,
                    "Edicao": str(self.convocacao_enade.data_prova.year),
                    "Motivo": motivo
                }
            }
        }
