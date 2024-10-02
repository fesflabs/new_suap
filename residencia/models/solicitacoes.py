import datetime

from djtools.db import models
from djtools.utils import send_notification
from residencia.managers import SolicitacaoUsuarioManager, SolicitacaoDesligamentosManager, SolicitacaoFeriasManager, \
    SolicitacaoLicencasManager
from residencia.models import LogResidenciaModel, SituacaoMatricula, SituacaoMatriculaPeriodo
from suap import settings

class SolicitacaoUsuario(LogResidenciaModel):
    solicitante = models.CurrentUserField(verbose_name='Solicitante', related_name='solicitacao_solicitante_residencia_set')
    data_solicitacao = models.DateTimeFieldPlus(null=True, auto_now_add=True, verbose_name='Data da Solicitação')
    descricao = models.TextField(verbose_name='Descrição')

    avaliador = models.ForeignKeyPlus('comum.User', verbose_name='Avaliador', null=True, related_name='solicitacao_avaliador_residencia_set')
    data_avaliacao = models.DateTimeFieldPlus(null=True)

    atendida = models.BooleanField(verbose_name='Atendida', default=False)
    razao_indeferimento = models.TextField(null=True, verbose_name='Razão do Indeferimento')

    objects = models.Manager()
    locals = SolicitacaoUsuarioManager()

    class Meta:
        verbose_name = 'Solicitação de Usuário'
        verbose_name_plural = 'Solicitações de Usuários'
        ordering = ('data_solicitacao',)

    def atender(self, avaliador, residente=None):
        self.data_avaliacao = datetime.datetime.now()
        self.avaliador = avaliador
        self.atendida = True
        self.save()
        if not residente:
            self.enviar_email(avaliador)

    def rejeitar(self, avaliador, razao_indeferimento, residente=None):
        self.data_avaliacao = datetime.datetime.now()
        self.avaliador = avaliador
        self.atendida = False
        self.razao_indeferimento = razao_indeferimento
        self.save()
        if not residente:
            self.enviar_email(avaliador)

    def enviar_email(self, avaliador):
        if not self.solicitante:
            return
        titulo = '[SUAP] Situação da Solicitação Usuário de Número {}.'.format(self.pk)
        if self.atendida:
            texto = self.get_texto_deferimento(avaliador)
            texto += self.get_texto_dados_solicitacao()
        else:
            texto = (
                '<dl>'
                '<dt>A solicitação de número {} foi indeferida por {} devido ao seguinte motivo:</dt>'
                '<dd>{}.</dd>'
                '</dl>'.format(self.pk, avaliador, self.razao_indeferimento)
            )

        return send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [self.solicitante.get_vinculo()], categoria='Situação da Solicitação Usuário')

    def get_absolute_url(self):
        return "/residencia/solicitacaousuario/{:d}/".format(self.pk)

    def get_texto_deferimento(self, avaliador):
        return 'A solicitação de número {} foi deferida por {}.'.format(self.pk, avaliador)

    def get_texto_dados_solicitacao(self):
        texto = """

            Dados da Solicitação:

            Data: {}
            Solicitante: {}
            Descrição: {}
        """.format(
            self.data_solicitacao, self.solicitante, self.descricao
        )
        return texto

    def sub_instance(self):
        child = self
        objetos_relacionados = [f for f in self._meta.get_fields() if (f.one_to_many or f.one_to_one) and f.auto_created]
        for r in objetos_relacionados:
            try:
                if r.field.name == 'solicitacaousuario_ptr':
                    child = getattr(self, r.get_accessor_name())
            except Exception:
                pass
        return child

    def sub_instance_title(self):
        return self.sub_instance()._meta.verbose_name

    sub_instance_title.short_description = 'Tipo de Solicitação'


class SolicitacaoDesligamentos(SolicitacaoUsuario):
    motivo = models.TextField('Motivo', null=True)
    data = models.DateField(null=True, blank=True)

    objects = models.Manager()
    locals = SolicitacaoDesligamentosManager()

    class Meta:
        verbose_name = 'Solicitação de Desligamentos'
        verbose_name_plural = 'Solicitações de Desligamentos'

    def __str__(self):
        return 'Solicitação de Desligamentos por {}'.format(self.solicitante)

    def save(self, *args, **kwargs):
        self.descricao = str(self)
        super(SolicitacaoDesligamentos, self).save(*args, **kwargs)

    def atender(self, avaliador, residente=None,):
        super(SolicitacaoDesligamentos, self).atender(avaliador, residente)
        matricula_periodo = residente.get_matriculas_periodo()[0]
        matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.DESLIGADO)
        matricula_periodo.save()
        residente.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.DESLIGADO)
        residente.save()


class SolicitacaoDiplomas(SolicitacaoUsuario):
    observacao = models.TextField('Observação', null=True)

    objects = models.Manager()
    locals = SolicitacaoDesligamentosManager()

    class Meta:
        verbose_name = 'Solicitação de Diplomas'
        verbose_name_plural = 'Solicitações de Diplomas'

    def __str__(self):
        return 'Solicitação de Diplomas por {}'.format(self.solicitante)

    def save(self, *args, **kwargs):
        self.descricao = str(self)
        super(SolicitacaoDiplomas, self).save(*args, **kwargs)

    def atender(self, avaliador, residente=None,):
        super(SolicitacaoDiplomas, self).atender(avaliador, residente)


class SolicitacaoFerias(SolicitacaoUsuario):


    data_inicio = models.DateFieldPlus('Início', null=False)
    data_fim = models.DateFieldPlus('Fim', null=False)
    observacao = models.TextField('Observação', null=True, blank=True)
    email = models.CharField('E-mail para contato', max_length=50, blank=True)


    objects = models.Manager()
    locals = SolicitacaoFeriasManager()

    class Meta:
        verbose_name = 'Solicitação de Férias'
        verbose_name_plural = 'Solicitações de Férias'

    def __str__(self):
        return 'Solicitação de Férias por {}'.format(self.solicitante)

    def get_quantidade_dias(self):
        return self.data_fim - self.data_inicio

    def save(self, *args, **kwargs):
        self.descricao = str(self)
        super(SolicitacaoFerias, self).save(*args, **kwargs)

    def atender(self, avaliador, residente=None,):
        super(SolicitacaoFerias, self).atender(avaliador, residente)


class SolicitacaoLicencas(SolicitacaoUsuario):

    TIPO_LICENCA_CHOICES = [['Tipo1', 'Tipo1'], ['Tipo2', 'Tipo2'], ['Tipo3', 'Tipo3'],]

    TIPO_LICENCA_MATERNIDADE = 1
    TIPO_LICENCA_MEDICA = 2
    TIPO_LICENCA_OUTRAS= 10
    TIPO_LICENCA_CHOICES = ((TIPO_LICENCA_MATERNIDADE, 'Licença Maternidade'), (TIPO_LICENCA_MEDICA, 'Licença Médica'), (TIPO_LICENCA_OUTRAS, 'Outras'))


    data_inicio = models.DateFieldPlus('Início', null=False)
    data_fim = models.DateFieldPlus('Fim', null=False)
    observacao = models.TextField('Observação', null=True, blank=True)
    email = models.CharField('E-mail para contato', max_length=50, blank=True)
    tipo = models.PositiveIntegerField('Tipo de licença', null=True, choices=TIPO_LICENCA_CHOICES)

    objects = models.Manager()
    locals = SolicitacaoLicencasManager()

    class Meta:
        verbose_name = 'Solicitação de Licenças'
        verbose_name_plural = 'Solicitações de Licenças'

    def __str__(self):
        return 'Solicitação de Licenças por {}'.format(self.solicitante)

    def get_quantidade_dias(self):
        return self.data_fim - self.data_inicio

    def save(self, *args, **kwargs):
        self.descricao = str(self)
        super(SolicitacaoLicencas, self).save(*args, **kwargs)

    def atender(self, avaliador, residente=None, ):
        super(SolicitacaoLicencas, self).atender(avaliador, residente)


class SolicitacaoCongressos(SolicitacaoUsuario):
    PRESENCIAL = 'Presencial'
    ONLINE = 'Online'

    R1 = 'R1'
    R2 = 'R2'

    MODALIDADE_CHOICES = ((PRESENCIAL, 'Presencial'), (ONLINE, 'Online'))
    TURMA_CHOICES = ((R1, 'R1'), (R2, 'R2'))

    descricao_evento = models.TextField(verbose_name='Descrição do evento')
    condicao_participacao = models.TextField(verbose_name='Condição da participação')
    modalidade = models.CharFieldPlus(choices=MODALIDADE_CHOICES, null=True, default=PRESENCIAL, verbose_name='Modalidade do evento')
    turma = models.CharFieldPlus(choices=TURMA_CHOICES, null=True, default=R1,
                                      verbose_name='Turma')
    hora_inicio = models.TimeFieldPlus('Horário do evento', help_text='Utilize o formato hh:mm:ss')
    estagio = models.TextField(verbose_name='Estágio', help_text='Se for R2 informe o estágio que está no momento', null=True, blank=True)

    data_inicio = models.DateFieldPlus('Início', null=False)
    data_fim = models.DateFieldPlus('Fim', null=False)

    email = models.CharField('E-mail para contato', max_length=50, blank=True)

    objects = models.Manager()
    locals = SolicitacaoLicencasManager()

    class Meta:
        verbose_name = 'Solicitação de Congressos'
        verbose_name_plural = 'Solicitações de Congressos'

    def __str__(self):
        return 'Solicitação de Congressos por {}'.format(self.solicitante)

    def get_quantidade_dias(self):
        return self.data_fim - self.data_inicio

    def save(self, *args, **kwargs):
        self.descricao = str(self)
        super(SolicitacaoCongressos, self).save(*args, **kwargs)

    def atender(self, avaliador, residente=None, ):
        super(SolicitacaoCongressos, self).atender(avaliador, residente)