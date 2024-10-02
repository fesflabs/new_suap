import datetime

from random import choice
from django.conf import settings
from django.contrib.contenttypes.fields import GenericRelation
from django.core.validators import FileExtensionValidator
from django.utils.safestring import mark_safe
from rest_framework.authtoken.models import Token
from comum.models import Ano, User, Vinculo, Configuracao
from comum.utils import somar_data
from djtools.db import models
from djtools.thumbs import ImageWithThumbsField
from djtools.utils import normalizar_nome_proprio
from djtools.storages import get_overwrite_storage
from djtools.db.models import ModelPlus
from django.apps import apps

from residencia.models import LogResidenciaModel, Residente


class SolicitacaoEletivo(LogResidenciaModel):

    SITUACAO_EM_ANALISE = 1
    SITUACAO_ATENDIDO = 2
    SITUACAO_NAO_ATENDIDO = 3
    SITUACAO_CANCELADO = 4
    SITUACAO_CHOICES = (
        (SITUACAO_EM_ANALISE, 'Em Análise'),
        (SITUACAO_ATENDIDO, 'Atendido'),
        (SITUACAO_NAO_ATENDIDO, 'Não Atendido'),
        (SITUACAO_CANCELADO, 'Cancelado'),
    )

    numero_seguro = models.CharField(
        'Número do Seguro Saúde (caso seja uma exigência do serviço)', max_length=50, null=True, blank=True
    )
    nome_servico = models.CharFieldPlus('Nome do Serviço de interesse para o estágio')
    cidade_servico = models.CharFieldPlus('Cidade/Estado/País', blank=True, null=True)
    data_inicio = models.DateFieldPlus('Data de Início')
    data_fim = models.DateFieldPlus('Data de Término')
    local_estagio = models.TextField('Caracterização do local do estágio', blank=True)
    justificativa_estagio = models.TextField('Justificativa para o estágio', blank=True)

    residente = models.ForeignKeyPlus('residencia.Residente')
    estagio = models.ForeignKeyPlus('residencia.EstagioEletivo', verbose_name='Estágio Eletivo', null=True, blank=True)
    situacao = models.PositiveIntegerField(
        choices=SITUACAO_CHOICES, default=SITUACAO_EM_ANALISE, verbose_name='Situação'
    )
    solicitado_em = models.DateTimeFieldPlus('Data de Solicitação', auto_now=True, null=True, blank=True)
    alterado_em = models.DateTimeFieldPlus('Data de Alteração', auto_now=True, null=True, blank=True)
    parecer = models.CharField('Parecer da Solicitação', max_length=1000, null=True, blank=True)
    parecer_autor_vinculo = models.ForeignKeyPlus(
        'comum.Vinculo',
        verbose_name='Autor do Parecer',
        related_name='residencia_solic_eletivo_autor_parecer_vinculo',
        null=True, blank=True, on_delete=models.CASCADE
    )
    parecer_data = models.DateTimeFieldPlus('Data do Parecer', null=True, blank=True)

    class Meta:
        verbose_name = 'Solicitação de Estágio Eletivo'
        verbose_name_plural = 'Solicitações de Estágio Eletivo'

    def __str__(self):
        return f'Solicitação de Estágio Eletivo - {self.residente} - {self.nome_servico}'

    def get_absolute_url(self):
        return f'/residencia/solicitacao_eletivo/{self.pk}/'

    def get_situacao_display(self):
        for situacao in self.SITUACAO_CHOICES:
            if situacao[0] == self.situacao:
                return mark_safe(situacao[1])
        return mark_safe(self.SITUACAO_CHOICES[0][1])


class EstagioEletivo(LogResidenciaModel):

    SITUACAO_EM_ANDAMENTO = 1
    SITUACAO_CONCLUIDO = 2
    SITUACAO_NAO_CONCLUIDO = 3
    SITUACAO_CHOICES = (
        (SITUACAO_EM_ANDAMENTO, 'Em Andamento'),
        (SITUACAO_CONCLUIDO, 'Concluído'),
        (SITUACAO_NAO_CONCLUIDO, 'Não Concluído'),
    )

    numero_seguro = models.CharField(
        'Número do Seguro Saúde (caso seja uma exigência do serviço)', max_length=50, null=True, blank=True
    )
    nome_servico = models.CharFieldPlus('Nome do Serviço de interesse para o estágio')
    cidade_servico = models.CharFieldPlus('Cidade/Estado/País', blank=True, null=True)
    data_inicio = models.DateFieldPlus('Data de Início')
    data_fim = models.DateFieldPlus('Data de Término')
    local_estagio = models.TextField('Caracterização do local do estágio', blank=True)
    justificativa_estagio = models.TextField('Justificativa para o estágio', blank=True)

    residente = models.ForeignKeyPlus('residencia.Residente')
    situacao = models.PositiveIntegerField(
        choices=SITUACAO_CHOICES, default=SITUACAO_EM_ANDAMENTO, verbose_name='Situação'
    )
    alterado_em = models.DateTimeFieldPlus('Data de Alteração', auto_now=True, null=True, blank=True)
    alterado_por = models.ForeignKeyPlus(
        'comum.Vinculo',
        verbose_name='Alterado por',
        related_name='residencia_estagio_eletivo_alterado_por_vinculo',
        null=True, blank=True, on_delete=models.CASCADE
    )

    class Meta:
        verbose_name = 'Estágio Eletivo'
        verbose_name_plural = 'Estágios Eletivos'

    def __str__(self):
        return f'Estágio Eletivo - {self.residente} - {self.nome_servico}'

    def get_absolute_url(self):
        return f'/residencia/estagio_eletivo/{self.pk}/'

    def get_situacao_display(self):
        for situacao in self.SITUACAO_CHOICES:
            if situacao[0] == self.situacao:
                return mark_safe(situacao[1])
        return mark_safe(self.SITUACAO_CHOICES[0][1])

    def estah_concluido(self):
        return self.situacao == self.SITUACAO_CONCLUIDO

    def estah_em_andamento(self):
        return self.situacao == self.SITUACAO_EM_ANDAMENTO

    def get_anexos_relat(self):
        return self.estagioeletivoanexo_set.filter(
            tipo_arquivo=EstagioEletivoAnexo.RELATORIO
        )

    def get_anexos_aval(self):
        return self.estagioeletivoanexo_set.filter(
            tipo_arquivo=EstagioEletivoAnexo.AVALIACAO
        )

    def get_anexos_freq(self):
        return self.estagioeletivoanexo_set.filter(
            tipo_arquivo=EstagioEletivoAnexo.FREQUENCIA
        )


class EstagioEletivoAnexo(models.ModelPlus):
    RELATORIO = 1
    AVALIACAO = 2
    FREQUENCIA = 3

    TIPO_ARQUIVO_CHOICES = (
        (RELATORIO, 'Relatório'),
        (AVALIACAO, 'Avaliação'),
        (FREQUENCIA, 'Frequência'),
    )

    tipo_arquivo = models.PositiveIntegerField(
        verbose_name='Tipo do Arquivo', choices=TIPO_ARQUIVO_CHOICES, default=RELATORIO
    )
    descricao = models.CharFieldPlus(
        'Descrição', max_length=80, null=False, blank=False,
        help_text='Informe uma descrição resumida sobre o arquivo anexado'
    )
    estagio = models.ForeignKeyPlus('residencia.EstagioEletivo', verbose_name='Estágio Eletivo')
    anexo = models.FileFieldPlus(
        max_length=255,
        upload_to='upload/estagioeletivo/anexos/',
        validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'xls', 'docx', 'doc', 'pdf'])],
    )
    anexado_em = models.DateTimeField(verbose_name='Anexado Em', auto_now_add=True, null=False, blank=False)
    anexado_por = models.ForeignKeyPlus(User, verbose_name='Anexado Por', null=False, blank=False)

    def __str__(self):
        return f'Estágio Eletivo {self.estagio.id} - Anexo ({self.id}): {self.descricao}'

    class Meta:
        ordering = ['anexado_em']
        verbose_name = 'Anexo de Estágio Eletivo'
        verbose_name_plural = 'Anexos de Estágio Eletivo'
