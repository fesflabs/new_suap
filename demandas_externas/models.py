# -*- coding: utf-8 -*-
from ckeditor.fields import RichTextField

from djtools.db import models
from edu.models import Cidade
from rh.models import UnidadeOrganizacional
from comum.models import Vinculo
from projetos.models import AreaTematica


class Periodo(models.ModelPlus):
    titulo = models.CharField('Título', max_length=5000)
    data_inicio = models.DateFieldPlus('Início do Período')
    data_termino = models.DateFieldPlus('Término do Período')
    descricao = RichTextField(verbose_name='Descrição', max_length=5000, help_text=u'Este texto será exibido no formulário de cadastro das demandas.', null=True, blank=True)
    campi = models.ManyToManyFieldPlus(UnidadeOrganizacional, blank=True)

    class Meta:
        verbose_name = 'Período de Recebimento de Demandas'
        verbose_name_plural = 'Períodos de Recebimento de Demandas'
        ordering = ['data_inicio']

    def __str__(self):
        return self.titulo

    def get_campi(self):
        lista = list()
        for campus in self.campi.all():
            lista.append(campus.nome)
        return ', '.join(lista)


class PublicoAlvo(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name=u'Descrição', max_length=100)
    ativo = models.BooleanField(verbose_name=u'Ativo', default=True)

    class Meta:
        verbose_name = 'Descrição de Público-Alvo'
        verbose_name_plural = 'Descrições de Público-Alvo'

    def __str__(self):
        return self.descricao


class TipoAcao(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name=u'Descrição', max_length=100)
    ativo = models.BooleanField(verbose_name=u'Ativo', default=True)

    class Meta:
        verbose_name = 'Tipo de Ação de Extensão'
        verbose_name_plural = 'Tipos de Ação de Extensão'

    def __str__(self):
        return self.descricao


class Demanda(models.ModelPlus):
    SUBMETIDA = 'Submetida'
    EM_ESPERA = 'Em Espera'
    EM_ATENDIMENTO = 'Em Atendimento'
    ATENDIDA = 'Atendida'
    NAO_ATENDIDA = 'Não Atendida'
    NAO_ACEITA = 'Não Aceita'

    SITUACAO_DEMANDA_CHOICES = (
        (SUBMETIDA, SUBMETIDA),
        (EM_ESPERA, EM_ESPERA),
        (EM_ATENDIMENTO, EM_ATENDIMENTO),
        (ATENDIDA, ATENDIDA),
        (NAO_ATENDIDA, NAO_ATENDIDA),
        (NAO_ACEITA, NAO_ACEITA),
    )

    periodo = models.ForeignKeyPlus(Periodo, verbose_name=u'Período de Recebimento')
    nome = models.CharFieldPlus(verbose_name=u'Nome Completo / Razão Social', max_length=500)
    identificador = models.CharFieldPlus(verbose_name=u'CPF / CNPJ', max_length=20)
    email = models.EmailField(verbose_name=u'Email')
    telefones = models.CharFieldPlus(verbose_name=u'Telefone(s) de Contato', max_length=100)
    whatsapp = models.CharFieldPlus(verbose_name=u'Whatsapp', max_length=50, null=True, blank=True)
    municipio = models.ForeignKey(Cidade, verbose_name=u'Cidade', on_delete=models.CASCADE)
    nome_comunidade = models.CharFieldPlus(verbose_name=u'Nome da Comunidade a ser atendida ou grupo a ser beneficiado pela demanda', max_length=500)
    campus_indicado = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name=u'Campus que fica mais próximo da demanda')
    campus_atendimento = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name=u'Campus de Atendimento', null=True, related_name='demandaexterna_campus_atendimento')
    descricao = models.CharFieldPlus(verbose_name=u'Descreva o problema/demanda', max_length=5000)
    publico_alvo = models.ManyToManyFieldPlus(PublicoAlvo, verbose_name=u'Público-alvo a ser atendido')
    qtd_prevista_beneficiados = models.IntegerField(verbose_name=u'Estimativa do número de beneficiários')
    situacao = models.CharFieldPlus('Situação', max_length=40, choices=SITUACAO_DEMANDA_CHOICES, default=SUBMETIDA)
    responsavel = models.ForeignKeyPlus(Vinculo, verbose_name=u'Responsável', null=True, related_name='demandaexterna_responsavel')
    atribuida_em = models.DateTimeFieldPlus(verbose_name=u'Atribuída em', null=True)
    atribuida_por = models.ForeignKeyPlus(Vinculo, verbose_name=u'Atribuída Por', null=True, related_name=u'demandas_externas_atribuidapor')
    observacoes = models.CharFieldPlus(verbose_name=u'Observações', max_length=5000, null=True, blank=True)
    cadastrada_em = models.DateTimeFieldPlus(verbose_name=u'Cadastrada em', null=True)
    avaliada_em = models.DateTimeFieldPlus(verbose_name=u'Avaliada em', null=True)
    avaliada_por = models.ForeignKeyPlus(Vinculo, verbose_name=u'Avaliada Por', null=True)
    tipo_acao = models.ForeignKeyPlus(TipoAcao, verbose_name='Tipo de Ação', null=True)
    area_tematica = models.ForeignKeyPlus(AreaTematica, verbose_name='Área Temática', null=True)
    data_prevista = models.DateFieldPlus('Data Prevista de Atendimento', null=True)
    qtd_beneficiados_atendidos = models.IntegerField(verbose_name=u'Quantidade de Beneficiários Atendidos', null=True)
    descricao_atendimento = models.CharFieldPlus(verbose_name=u'Descrição sobre o Atendimento da Demanda', max_length=5000, null=True, blank=True)
    concluida_em = models.DateTimeFieldPlus(verbose_name=u'Concluída em', null=True)

    class Meta:
        verbose_name = 'Demanda Externa'
        verbose_name_plural = 'Demandas Externas'
        permissions = (("pode_ver_todas_demandas_externas", "Pode ver todas as demandas externas"), ("pode_ver_demandas_externas", "Pode ver demandas externas do campus"))

    def __str__(self):
        return self.nome

    def foi_aceita(self):
        return self.situacao in [Demanda.EM_ESPERA, Demanda.EM_ATENDIMENTO, Demanda.ATENDIDA]

    def eh_ativa(self):
        return self.situacao in [Demanda.EM_ATENDIMENTO, Demanda.ATENDIDA]

    def foi_concluida(self):
        return self.situacao == Demanda.ATENDIDA


class Equipe(models.ModelPlus):
    demanda = models.ForeignKeyPlus(Demanda, verbose_name=u'Demanda')
    participante = models.ForeignKeyPlus(Vinculo, verbose_name=u'Participante')

    class Meta:
        verbose_name = 'Participante da Demanda'
        verbose_name_plural = 'Participantes da Demanda'

    def __str__(self):
        return self.participante
