# -*- coding: utf-8 -*-

from django.conf import settings
from django.core.exceptions import ValidationError

from djtools.db import models
from djtools.utils import send_notification
from edu.managers import AtividadeComplementarManager, AtividadeAprofundamentoManager
from .cadastros_gerais import PERIODO_LETIVO_CHOICES
from .logs import LogModel


class ConfiguracaoAtividadeAprofundamento(LogModel):
    id = models.AutoField(verbose_name="Código", primary_key=True)
    descricao = models.CharFieldPlus('Descrição', width=500)

    class Meta:
        verbose_name = 'Configuração de ATPA'
        verbose_name_plural = 'Configurações de ATPA'

    def get_absolute_url(self):
        return "/edu/configuracaoatividadeaprofundamento/{:d}/".format(self.pk)

    def replicar(self, descricao):
        configuracao_replicada = ConfiguracaoAtividadeAprofundamento()
        configuracao_replicada.descricao = descricao
        configuracao_replicada.save()
        for atividade_academica in self.itemconfiguracaoatividadeaprofundamento_set.all():
            nova_atividade_academica = ItemConfiguracaoAtividadeAprofundamento()
            nova_atividade_academica.configuracao = configuracao_replicada
            nova_atividade_academica.tipo = atividade_academica.tipo
            nova_atividade_academica.carga_horaria = atividade_academica.carga_horaria
            nova_atividade_academica.obs_carga_horaria = atividade_academica.obs_carga_horaria
            nova_atividade_academica.save()
        return configuracao_replicada


class ItemConfiguracaoAtividadeAprofundamento(LogModel):
    configuracao = models.ForeignKeyPlus(ConfiguracaoAtividadeAprofundamento, verbose_name='Configuração de ATPA')
    tipo = models.ForeignKeyPlus('edu.TipoAtividadeAprofundamento')
    carga_horaria = models.IntegerField('Carga-Horária', blank=True, null=True)
    obs_carga_horaria = models.CharFieldPlus('Observação da Carga-Horária', help_text='Informação adicional sobre a carga-horária da atividade.', blank=True, null=True)

    class Meta:
        verbose_name = 'Item de Configuração de ATPA'
        verbose_name_plural = 'Itens de Configuração de ATPA'


class AtividadeAprofundamento(LogModel):
    aluno = models.ForeignKeyPlus('edu.Aluno', verbose_name='Aluno', null=False, blank=True)

    tipo = models.ForeignKeyPlus('edu.TipoAtividadeAprofundamento', verbose_name='Tipo', on_delete=models.CASCADE)
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano Letivo', null=False, blank=False, on_delete=models.CASCADE)
    periodo_letivo = models.PositiveIntegerField('Período Letivo', choices=PERIODO_LETIVO_CHOICES, null=False, blank=False)

    descricao = models.CharFieldPlus('Atividade', null=False, blank=False, help_text='Nome da atividade com até 100 caracteres.')
    data_atividade = models.DateFieldPlus('Data da Atividade', null=False, blank=False)
    carga_horaria = models.IntegerField('Carga Horária', null=False, blank=False)
    informacoes_complementares = models.TextField('Informações Complementares', null=True, blank=True)
    documento = models.FileFieldPlus(
        'Anexo',
        upload_to='edu/atividade_complementar/',
        null=True,
        blank=False,
        check_mimetype=False,
        help_text='Neste campo você pode anexar um certificado ou comprovante, por exemplo. Tipos de arquivos aceitados: pdf, png ou jpg. Tamanho Máximo: 5Mb',
        filetypes=['pdf', 'png', 'jpg'],
        max_file_size=5242880,
    )
    deferida = models.BooleanField(verbose_name='Deferida', null=True)
    razao_indeferimento = models.TextField(null=True, verbose_name='Razão do Indeferimento', blank=True)

    class Meta:
        verbose_name = 'Atividade Teórico-Prática de Aprofundamento'
        verbose_name_plural = 'Atividades Teórico-Práticas de Aprofundamento'

    objects = models.Manager()
    locals = AtividadeAprofundamentoManager()

    def get_absolute_url(self):
        return '/edu/atividadeaprofundamento/{}/'.format(self.pk)

    def enviar_email_coordenador(self):
        coordenador = self.aluno.curso_campus.coordenador
        if coordenador:
            vinculo = coordenador.get_vinculo()
        else:
            return False

        titulo = '[SUAP] Solicitação de Atividade de Aprofundamento'
        texto = (
            '<h1>Ensino</h1>'
            '<h2>Solicitação de Atividade de Aprofundamento</h2>'
            '<p>O aluno {} solicitou o deferimento de uma atividade de aprofundamento.</p>'
            '<p>Acesse {}/edu/aluno/{}/?tab=atividades_aprofundamento para deferir ou indeferir a solicitação.</p>'.format(self.aluno, settings.SITE_URL, self.aluno.matricula)
        )

        return send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [vinculo], fail_silently=True)


class AtividadeComplementar(LogModel):
    aluno = models.ForeignKeyPlus('edu.Aluno', verbose_name='Aluno', null=False, blank=True)

    tipo = models.ForeignKeyPlus('edu.TipoAtividadeComplementar', verbose_name='Tipo', on_delete=models.CASCADE)
    ano_letivo = models.ForeignKeyPlus('comum.Ano', verbose_name='Ano Letivo', null=False, blank=False, on_delete=models.CASCADE)
    periodo_letivo = models.PositiveIntegerField('Período Letivo', choices=PERIODO_LETIVO_CHOICES, null=False, blank=False)

    descricao = models.CharFieldPlus('Atividade', null=False, blank=False, help_text='Nome da atividade com até 100 caracteres.')
    data_atividade = models.DateFieldPlus('Data da Atividade', null=False, blank=False)
    carga_horaria = models.IntegerField('Carga Horária', null=False, blank=False)
    informacoes_complementares = models.TextField('Informações Complementares', null=True, blank=True)
    documento = models.FileFieldPlus(
        'Anexo',
        upload_to='edu/atividade_complementar/',
        null=True,
        blank=True,
        check_mimetype=False,
        help_text='Neste campo você pode anexar um certificado ou comprovante, por exemplo. Tipos de arquivos aceitados: pdf, png ou jpg. Tamanho Máximo: 5Mb',
        filetypes=['pdf', 'png', 'jpg'],
        max_file_size=5242880,
    )
    deferida = models.BooleanField(verbose_name='Deferida', null=True)
    razao_indeferimento = models.TextField(null=True, verbose_name='Razão do Indeferimento', blank=True)

    class Meta:
        verbose_name = 'Atividade Complementar'
        verbose_name_plural = 'Atividades Complementares'

    objects = models.Manager()
    locals = AtividadeComplementarManager()

    def is_curricular(self):
        return ItemConfiguracaoAtividadeComplementar.objects.filter(configuracao__matriz=self.aluno.matriz, tipo=self.tipo).exists()

    def ano_periodo_letivo(self):
        return "{}.{}".format(self.ano_letivo.ano, self.periodo_letivo)

    def save(self, *args, **kwargs):
        super(AtividadeComplementar, self).save(*args, **kwargs)
        if self.pk or self.is_curricular():
            self.aluno.atualizar_situacao('Lançamento de Atividade Complementar')

    def delete(self, *args, **kwargs):
        super(AtividadeComplementar, self).delete(*args, **kwargs)
        if self.pk or self.is_curricular():
            self.aluno.atualizar_situacao('Exclusão de Atividade Complementar')

    def enviar_email_coordenador(self):
        coordenador = self.aluno.curso_campus.coordenador
        if coordenador:
            vinculo = coordenador.get_vinculo()
        else:
            return False

        titulo = '[SUAP] Solicitação de Atividade Complementar'
        texto = (
            '<h1>Ensino</h1>'
            '<h2>Solicitação de Atividade Complementar</h2>'
            '<p>O aluno {} solicitou o deferimento de uma atividade acadêmica.</p>'
            '<p>Acesse {}/edu/aluno/{}/?tab=acc para deferir ou indeferir a solicitação.</p>'.format(self.aluno, settings.SITE_URL, self.aluno.matricula)
        )

        return send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [vinculo], fail_silently=True)

    def get_absolute_url(self):
        return '/edu/atividadecomplementar/{}/'.format(self.pk)

    def clean(self):
        if self.descricao and self.deferida and len(self.descricao) > 100:
            raise ValidationError('O nome da atividade deve ter até 100 caracteres.')
        if self.deferida is not None and not self.deferida and not self.razao_indeferimento:
            raise ValidationError('Por favor, informe a razão do indeferimento')


class ConfiguracaoAtividadeComplementar(LogModel):
    id = models.AutoField(verbose_name="Código", primary_key=True)
    descricao = models.CharFieldPlus('Descrição', width=500)

    class Meta:
        verbose_name = 'Configuração de AACCs'
        verbose_name_plural = 'Configurações de AACCs'

    def get_absolute_url(self):
        return "/edu/configuracaoatividadecomplementar/{:d}/".format(self.pk)

    def replicar(self, descricao):
        configuracao_replicada = ConfiguracaoAtividadeComplementar()
        configuracao_replicada.descricao = descricao
        configuracao_replicada.save()
        for atividade_academica in self.itemconfiguracaoatividadecomplementar_set.all():
            nova_atividade_academica = ItemConfiguracaoAtividadeComplementar()
            nova_atividade_academica.configuracao = configuracao_replicada
            nova_atividade_academica.tipo = atividade_academica.tipo
            nova_atividade_academica.pontuacao_max_periodo = atividade_academica.pontuacao_max_periodo
            nova_atividade_academica.pontuacao_max_curso = atividade_academica.pontuacao_max_curso
            nova_atividade_academica.fator_conversao = atividade_academica.fator_conversao
            nova_atividade_academica.save()
        return configuracao_replicada


class ItemConfiguracaoAtividadeComplementar(LogModel):
    configuracao = models.ForeignKeyPlus('edu.ConfiguracaoAtividadeComplementar', verbose_name='Configuração Atividades Acadêmicas')
    tipo = models.ForeignKeyPlus('edu.TipoAtividadeComplementar')
    pontuacao_min_curso = models.IntegerField('Pontuação Mínima no Curso', null=True, blank=True)
    pontuacao_max_periodo = models.IntegerField('Pontuação Máxima no Período', null=True, blank=True)
    pontuacao_max_curso = models.IntegerField('Pontuação Máxima no Curso', null=True, blank=True)
    pontuacao_por_evento = models.IntegerField(
        'Pontuação por Registro',
        help_text='Obrigatório apenas quando o registro dessa atividade complementar não requerer a entrada da carga horário pelo secretário acadêmico. Ex: Capítulo de Livro.',
        null=True,
        blank=True,
    )
    fator_conversao = models.DecimalFieldPlus('Fator de conversão (Peso)')

    ch_min_curso = models.IntegerField('C.H. Mínima no Curso', null=True)
    ch_max_periodo = models.IntegerField('C.H. Máxima no Período', null=True)
    ch_max_curso = models.IntegerField('C.H. Máxima no Curso', null=True)
    ch_por_evento = models.IntegerField('C.H. por Evento', null=True)

    class Meta:
        verbose_name = 'Item de Configuração de AACC'
        verbose_name_plural = 'Itens de Configuração de AACC'
        unique_together = ('configuracao', 'tipo')

    def save(self, *args, **kwargs):
        self.ch_min_curso = None
        self.ch_max_periodo = None
        self.ch_max_curso = None
        self.ch_por_evento = None
        if self.pontuacao_min_curso:
            self.ch_min_curso = int(self.pontuacao_min_curso * self.fator_conversao)
        if self.pontuacao_max_periodo:
            self.ch_max_periodo = int(self.pontuacao_max_periodo * self.fator_conversao)
        if self.pontuacao_max_curso:
            self.ch_max_curso = int(self.pontuacao_max_curso * self.fator_conversao)
        if self.pontuacao_por_evento:
            self.ch_por_evento = int(self.pontuacao_por_evento * self.fator_conversao)
        super(ItemConfiguracaoAtividadeComplementar, self).save(*args, **kwargs)

    def __str__(self):
        return '{}'.format(self.tipo)
