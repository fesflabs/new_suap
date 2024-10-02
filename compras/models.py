# -*- coding: utf-8 -*-

import datetime
from decimal import Decimal

from comum.utils import get_todos_campi, get_uo
from djtools.db import models, transaction
from djtools.templatetags.filters import format_money
from materiais.models import Material, MaterialTag
from rh.models import UnidadeOrganizacional, Servidor


class ProcessoCompra(models.ModelPlus):
    STATUS_AGUARDANDO_VALIDACAO = 1
    STATUS_VALIDADO = 2
    cadastrado_em = models.DateTimeField(auto_now_add=True)
    cadastrado_por = models.CurrentUserField()
    descricao = models.CharField('Descrição', max_length=255)
    observacao = models.TextField('Observação', blank=True)
    status = models.IntegerField(default=STATUS_AGUARDANDO_VALIDACAO, choices=[[STATUS_AGUARDANDO_VALIDACAO, 'Aguardando validação'], [STATUS_VALIDADO, 'Validado']])
    data_inicio = models.DateTimeField('Data de Início')
    data_fim = models.DateTimeField('Data de Fim')
    validado_por = models.ForeignKeyPlus('comum.User', null=True, blank=True, on_delete=models.CASCADE, related_name='abc', editable=False)
    validado_em = models.DateTimeField(null=True, blank=True, editable=False)
    tags = models.ManyToManyField('materiais.MaterialTag', blank=True)

    class Meta:
        permissions = (('pode_gerenciar_processocompra', 'Pode gerenciar processos de compra'),)
        verbose_name = 'Processo de Compra'
        verbose_name_plural = 'Processos de Compra'

    def save(self, *args, **kwargs):
        super(ProcessoCompra, self).save(*args, **kwargs)

    @transaction.atomic
    def aplicar_todos_campus(self):
        uos = self.processocompracampus_set.values_list('campus__pk', flat=True)
        for campus in UnidadeOrganizacional.objects.uo().exclude(pk__in=uos):
            ProcessoCompraCampus.objects.create(processo_compra=self, campus=campus, data_inicio=self.data_inicio, data_fim=self.data_fim)

    def __str__(self):
        return self.descricao

    def is_em_periodo_de_inclusao(self):
        return self in ProcessoCompra.get_no_periodo()

    @classmethod
    def get_no_periodo(cls):
        agora = datetime.datetime.now()
        return cls.objects.filter(data_inicio__lte=agora, data_fim__gte=agora)

    @classmethod
    def get_no_periodo_para_mim(cls):
        agora = datetime.datetime.now()
        return cls.objects.filter(data_inicio__lte=agora, data_fim__gte=agora, processocompracampus__campus=get_uo())

    def get_absolute_url(self):
        return '/compras/processo_compra/{:d}/'.format(self.pk)

    def get_itens(self, user=None):

        if user and user.has_perm('compras.pode_gerenciar_processocompra'):
            return self.processocompracampus_set.all()
        else:
            return self.processocompracampus_set.filter(campus__in=get_todos_campi())

    def get_materiais(self):
        materiais_ids = set(ProcessoCompraCampusMaterial.objects.filter(processo_compra_campus__processo_compra=self).values_list('material', flat=True).order_by('material'))
        return Material.objects.filter(id__in=materiais_ids)

    def get_materiais_sem_cotacao(self):
        materiais_ids = set(ProcessoCompraCampusMaterial.objects.filter(processo_compra_campus__processo_compra=self).values_list('material', flat=True).order_by('material'))
        return Material.get_sem_cotacao().filter(id__in=materiais_ids)

    def pode_validar(self, user):
        if self.processocompracampus_set.filter(status=self.STATUS_AGUARDANDO_VALIDACAO).exists():
            return False

        if self.status == self.STATUS_VALIDADO:
            return False

        if not user.has_perm('compras.pode_gerenciar_processocompra'):
            return False

        return True

    @transaction.atomic
    def validar(self, user):

        # Gravando em ProcessoCompraMaterial
        self.processocompramaterial_set.all().delete()
        for material in self.get_materiais():
            valor_referencia = []
            for c in material.materialcotacao_set.all():
                valor_referencia.append('{}: {}'.format(c.material.id, format_money(c.valor)))

            valor_referencia = ' | '.join(valor_referencia)
            material_tag = material.tags.exists() and material.tags.all()[0] or None
            ProcessoCompraMaterial.objects.create(
                processo_compra=self, material=material, material_tag=material_tag, valor_unitario=material.valor_medio, valor_referencia=valor_referencia
            )

            ProcessoCompraCampusMaterial.objects.filter(processo_compra_campus__processo_compra=self, material=material).update(material_tag=material_tag)

        # Atualizando os valores dos itens de compra
        for i in ProcessoCompraCampusMaterial.objects.filter(processo_compra_campus__processo_compra=self):
            i.atualizar_valores(atualizar_processo_compra_campus=False)

        for i in self.processocompracampus_set.all():
            i.atualizar_valores()

        # Atualizando as informações de self
        self.status = self.STATUS_VALIDADO
        self.validado_em = datetime.datetime.now()
        self.validado_por = user
        self.save()


class ProcessoCompraMaterial(models.ModelPlus):
    """
    Classe para guardar histórico de informações sobre cotações do material.
    É preenchido na validação do processo de compra.
    """

    processo_compra = models.ForeignKeyPlus('compras.ProcessoCompra', on_delete=models.CASCADE)
    material = models.ForeignKeyPlus('materiais.Material', on_delete=models.CASCADE)
    material_tag = models.ForeignKeyPlus('materiais.MaterialTag', null=True, on_delete=models.CASCADE)
    valor_unitario = models.DecimalFieldPlus(default=0, editable=False)
    valor_referencia = models.TextField()

    class Meta:
        ordering = ['material_tag', 'material__id']


class ProcessoCompraCampus(models.ModelPlus):
    STATUS_AGUARDANDO_VALIDACAO = 1
    STATUS_VALIDADO = 2
    processo_compra = models.ForeignKeyPlus('compras.ProcessoCompra', on_delete=models.CASCADE)
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, on_delete=models.CASCADE)
    data_inicio = models.DateTimeField()
    data_fim = models.DateTimeField()
    status = models.IntegerField(
        default=STATUS_AGUARDANDO_VALIDACAO, choices=[[STATUS_AGUARDANDO_VALIDACAO, 'Aguardando validação'], [STATUS_VALIDADO, 'Validado']], editable=False
    )
    validado_por = models.ForeignKeyPlus('comum.User', null=True, blank=True, editable=False, on_delete=models.CASCADE)
    validado_em = models.DateTimeField(null=True, blank=True, editable=False)
    valor_total = models.DecimalFieldPlus(default=0, editable=False)

    class Meta:
        ordering = ('processo_compra', 'campus__setor__sigla')
        unique_together = ('processo_compra', 'campus')
        permissions = (('pode_validar_do_seu_campus', 'Pode validar processos de compra do seu campus'),)
        verbose_name = 'Processo Compra Campus'
        verbose_name_plural = 'Processo Compra Campus'

    def __str__(self):
        return '{} - {}'.format(self.processo_compra, self.campus)

    def get_absolute_url(self):
        return '/compras/processo_compra_campus/{:d}/'.format(self.pk)

    def atualizar_valores(self):
        self.valor_total = sum(self.get_itens().values_list('valor_total', flat=True))
        ProcessoCompraCampus.objects.filter(pk=self.pk).update(valor_total=self.valor_total)

    def get_valor_total_por_tag(self):
        valores = dict()
        for tag in MaterialTag.objects.all():
            itens = self.get_itens().filter(material__tags=tag)
            if itens:
                valores[tag] = sum(i.valor_total for i in itens)
        return valores

    def get_itens(self):
        return self.processocompracampusmaterial_set.filter(material__ativo=True).order_by('material__id')

    def get_materiais_ausentes(self, user):
        """
        Retorna os itens que não foram escolhidos para este campus e que 
        foram escolhidos por algum outro do mesmo processo de compra.
        """
        todos = self.processo_compra.get_materiais().values_list('id', flat=True)
        incluidos = self.get_itens().values_list('material', flat=True)
        return Material.objects.filter(id__in=list(set(todos) - set(incluidos)))

    def preencher_materiais_ausentes(self, user):
        """
        Insere a quantidade 1 para todos os materiais presentes no processo de 
        compra que não foram inseridos no processo de compra do campus (self).
        """
        for material in self.get_materiais_ausentes(user):
            ProcessoCompraCampusMaterial.objects.create(
                processo_compra_campus=self, material=material, material_tag=material.tags.exists() and material.tags.all()[0] or None, qtd=1
            )

    def estah_no_periodo(self):
        return self.data_inicio <= datetime.datetime.now() <= self.data_fim and self.status == self.STATUS_AGUARDANDO_VALIDACAO

    def estah_validado(self):
        return self.status == self.STATUS_VALIDADO

    def pode_validar(self, user):

        if not self.estah_no_periodo() or self.estah_validado():
            return False

        if self.get_itens().filter(material__in=Material.get_sem_cotacao()).exists():
            return False

        if user.has_perm('compras.pode_gerenciar_processocompra'):
            return True

        if not user.has_perm('compras.pode_validar_do_seu_campus'):
            return False

        return True

    def validar(self, user):
        for processo in self.get_itens():
            for cotacao in processo.material.materialcotacao_set.all():
                ProcessoMaterialCotacao.objects.create(processo_compra=self.processo_compra, material=processo.material, cotacao=cotacao)

        self.status = self.STATUS_VALIDADO
        self.validado_em = datetime.datetime.now()
        self.validado_por = user
        self.save()


class ProcessoCompraCampusMaterial(models.ModelPlus):
    cadastrado_em = models.DateTimeField(auto_now_add=True)
    cadastrado_por = models.CurrentUserField()
    processo_compra_campus = models.ForeignKeyPlus('compras.ProcessoCompraCampus', on_delete=models.CASCADE)
    material = models.ForeignKeyPlus('materiais.Material', on_delete=models.CASCADE)
    material_tag = models.ForeignKeyPlus('materiais.MaterialTag', null=True, on_delete=models.CASCADE)
    qtd = models.FloatField()
    valor_unitario = models.DecimalFieldPlus(default=0, editable=False)
    valor_total = models.DecimalFieldPlus(default=0, editable=False, help_text='Esse valor vai ser atualizado após o processo de compra ser ' 'validado.')

    class Meta:
        unique_together = ('processo_compra_campus', 'material')
        verbose_name = 'Material em processo de compra'
        verbose_name_plural = 'Materiais em processo de compra'

    def save(self, *args, **kwargs):
        super(ProcessoCompraCampusMaterial, self).save(*args, **kwargs)
        self.atualizar_valores()

    def atualizar_valores(self, atualizar_processo_compra_campus=True):
        if self.processo_compra_campus.processo_compra.status == ProcessoCompra.STATUS_VALIDADO:
            return
        self.valor_unitario = self.material.valor_medio
        self.valor_total = Decimal('{:.2f}'.format(self.qtd)) * self.material.valor_medio
        ProcessoCompraCampusMaterial.objects.filter(pk=self.pk).update(valor_unitario=self.valor_unitario, valor_total=self.valor_total)
        if atualizar_processo_compra_campus:
            self.processo_compra_campus.atualizar_valores()


class ProcessoMaterialCotacao(models.ModelPlus):
    processo_compra = models.ForeignKeyPlus('compras.ProcessoCompra', on_delete=models.CASCADE)
    material = models.ForeignKeyPlus('materiais.Material', on_delete=models.CASCADE)
    cotacao = models.ForeignKeyPlus('materiais.MaterialCotacao', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Processo de Compra Cotação'
        verbose_name_plural = 'Processos de Compra Cotações'


class Calendario(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição', max_length=1000)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Calendário'
        verbose_name_plural = 'Calendários'

    def __str__(self):
        return self.descricao


class TipoEvento(models.ModelPlus):
    COR_CHOICE = (('alert', 'Amarelo'), ('info', 'Azul'), ('extra', 'Laranja'), ('extra2', 'Roxo'), ('success', 'Verde'), ('error', 'Vermelho'), ('nenhum', 'Nenhum'))
    descricao = models.CharFieldPlus('Descrição', max_length=1000)
    calendario = models.ForeignKeyPlus(Calendario, verbose_name='Calendário', on_delete=models.CASCADE)
    cor = models.CharFieldPlus('Cor', help_text='Informe uma cor para o tipo de evento', choices=COR_CHOICE)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Tipo de Evento'
        verbose_name_plural = 'Tipos de Evento'

    def __str__(self):
        return self.descricao


class Evento(models.ModelPlus):
    tipo_evento = models.ForeignKeyPlus(TipoEvento, verbose_name='Tipo de Evento', on_delete=models.CASCADE)
    data_inicio = models.DateFieldPlus('Data de Início')
    data_fim = models.DateFieldPlus('Data de Fim')
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Evento'
        verbose_name_plural = 'Eventos'

    def __str__(self):
        return f'{self.tipo_evento}'


class Nucleo(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição', max_length=1000)
    componentes = models.ManyToManyFieldPlus(Servidor, verbose_name='Servidores Relacionados')
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Núcleo'
        verbose_name_plural = 'Núcleos'

    def __str__(self):
        return f'{self.descricao}'


class TipoProcesso(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição', max_length=1000)
    tipo_calendario = models.ForeignKeyPlus(Calendario, verbose_name='Tipo do Calendário', on_delete=models.CASCADE)
    nucleo_responsavel = models.ForeignKeyPlus(Nucleo, verbose_name='Núcleo Responsável', on_delete=models.CASCADE)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Tipo de Processo'
        verbose_name_plural = 'Tipos de Processo'

    def __str__(self):
        return self.descricao


class Processo(models.ModelPlus):
    SITUACAO_PROCESSO = (
        ('Aberto', 'Aberto'),
        ('Suspenso', 'Suspenso'),
        ('Concluído', 'Concluído'),
    )
    tipo_processo = models.ForeignKeyPlus(TipoProcesso, verbose_name='Tipo do Processo', on_delete=models.CASCADE)
    situacao = models.CharFieldPlus('Situação', max_length=30, choices=SITUACAO_PROCESSO)

    class Meta:
        verbose_name = 'Processo de Compra e Contratação'
        verbose_name_plural = 'Processos de Compra e Contratação'

    def __str__(self):
        return '{} - {}'.format(self.tipo_processo.descricao, self.tipo_processo.tipo_calendario.descricao)

    def get_campi_solicitantes(self):
        return ', '.join(set([registro.campus_solicitante.sigla for registro in SolicitacaoParticipacao.objects.filter(fase__processo=self).order_by('campus_solicitante__sigla')]))


class Fase(models.ModelPlus):
    COR_CHOICE = (('alert', 'Amarelo'), ('info', 'Azul'), ('extra', 'Laranja'), ('extra2', 'Roxo'), ('success', 'Verde'), ('error', 'Vermelho'), ('nenhum', 'Nenhum'))
    cor = models.CharFieldPlus('Cor', help_text='Informe uma cor para a fase', choices=COR_CHOICE)
    processo = models.ForeignKeyPlus(Processo, verbose_name='Processo', on_delete=models.CASCADE)
    descricao = models.CharFieldPlus('Descrição', max_length=1000)
    data_inicio = models.DateFieldPlus('Data de Início')
    data_fim = models.DateFieldPlus('Data de Fim')
    fase_inicial = models.BooleanField('É uma fase inicial?', default=False)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Fase do Processo'
        verbose_name_plural = 'Fases do Processo'

    def __str__(self):
        return '{}: {} - {}'.format(self.processo.tipo_processo.descricao, self.data_inicio.strftime("%d/%m/%Y"), self.data_fim.strftime("%d/%m/%Y"))


class SolicitacaoParticipacao(models.ModelPlus):
    fase = models.ForeignKeyPlus(Fase, verbose_name='Fase', on_delete=models.CASCADE)
    solicitada_em = models.DateTimeFieldPlus('Solicitada Em')
    solicitada_por = models.ForeignKeyPlus(Servidor, verbose_name='Solicitada Por', on_delete=models.CASCADE)
    campus_solicitante = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus Solicitante', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Solicitação de Participação'
        verbose_name_plural = 'Solicitações de Participação'

    def __str__(self):
        return 'Solicitação do Campus {} para a Fase: {}'.format(self.campus_solicitante, self.fase)
