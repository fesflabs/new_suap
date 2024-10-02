import datetime
import os

from djtools.db import models
from djtools.utils import send_notification
from ppe.managers import AtendimentoPsicossocialManager, ContinuidadeAperfeicoamentoProfissionalManager, \
    AmpliacaoPrazoCursoManager, RealocacaoManager, VisitaTecnicaUnidadeManager
from ppe.models import LogPPEModel
from residencia.managers import SolicitacaoUsuarioManager, SolicitacaoDesligamentosManager, SolicitacaoFeriasManager, \
    SolicitacaoLicencasManager
from residencia.models import LogResidenciaModel
from suap import settings

class SolicitacaoUsuario(LogPPEModel):
    solicitante = models.CurrentUserField(verbose_name='Solicitante', related_name='solicitacao_solicitante_ppe_set')
    data_solicitacao = models.DateTimeFieldPlus(null=True, auto_now_add=True, verbose_name='Data da Solicitação')
    descricao = models.TextField(verbose_name='Descrição')

    avaliador = models.ForeignKeyPlus('comum.User', verbose_name='Avaliador', null=True, related_name='solicitacao_avaliador_ppe_set')
    data_avaliacao = models.DateTimeFieldPlus(null=True)

    atendida = models.BooleanField(verbose_name='Atendida', default=False)
    razao_indeferimento = models.TextField(null=True, verbose_name='Razão do Indeferimento')

    objects = models.Manager()
    locals = SolicitacaoUsuarioManager()

    class Meta:
        verbose_name = 'Solicitação de Usuário'
        verbose_name_plural = 'Solicitações de Usuários'
        ordering = ('data_solicitacao',)

    def atender(self, avaliador, trabalhador_educando=None):
        self.data_avaliacao = datetime.datetime.now()
        self.avaliador = avaliador
        self.atendida = True
        self.save()
        if not trabalhador_educando:
            self.enviar_email(avaliador)

    def rejeitar(self, avaliador, razao_indeferimento, trabalhador_educando=None):
        self.data_avaliacao = datetime.datetime.now()
        self.avaliador = avaliador
        self.atendida = False
        self.razao_indeferimento = razao_indeferimento
        self.save()
        if not trabalhador_educando:
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
        return "/ppe/solicitacaousuario/{:d}/".format(self.pk)

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


class SolicitacaoAtendimentoPsicossocial(SolicitacaoUsuario):
    motivo = models.TextField('Motivo', null=True)
    preferencia_contato = models.CharField(
        verbose_name="Preferencia de Contato",
        null=True,
        max_length=255
    )

    objects = models.Manager()
    locals = AtendimentoPsicossocialManager()

    class Meta:
        verbose_name = 'Solicitação de Atendimento pelo Núcleo de Atenção Psicossocial'
        verbose_name_plural = 'Solicitações de Atendimento pelo Núcleo de Atenção Psicossocial'

    def __str__(self):
        return 'Solicitação de Atendimento pelo Núcleo de Atenção Psicossocial por {}'.format(self.solicitante)

    def save(self, *args, **kwargs):
        self.descricao = str(self)
        super(SolicitacaoAtendimentoPsicossocial, self).save(*args, **kwargs)

    def atender(self, avaliador, trabalhador_educando=None,):
        super(SolicitacaoAtendimentoPsicossocial, self).atender(avaliador, trabalhador_educando)


class SolicitacaoContinuidadeAperfeicoamentoProfissional(SolicitacaoUsuario):
    observacao = models.TextField('Observação', null=True)
    anexo_termo = models.FileFieldPlus(upload_to='ppe/anexo_termo/', max_length=250,null=True, blank=True,)
    objects = models.Manager()
    locals = ContinuidadeAperfeicoamentoProfissionalManager()

    class Meta:
        verbose_name = 'Solicitação de continuidade no Aperfeiçoamento Profissional'
        verbose_name_plural = 'Solicitações de continuidade no Aperfeiçoamento Profissional'

    def __str__(self):
        return 'Solicitação de continuidade no Aperfeiçoamento Profissional por {}'.format(self.solicitante)

    def save(self, *args, **kwargs):
        self.descricao = str(self)
        super(SolicitacaoContinuidadeAperfeicoamentoProfissional, self).save(*args, **kwargs)

    def atender(self, avaliador, trabalhador_educando=None,):
        super(SolicitacaoContinuidadeAperfeicoamentoProfissional, self).atender(avaliador, trabalhador_educando)
    
    @property 
    def filename(self):
        return os.path.basename(self.anexo_termo.name)


class SolicitacaoAmpliacaoPrazoCurso(SolicitacaoUsuario):

    observacao = models.TextField('Observação', null=True, blank=True)
    email = models.CharField('E-mail para contato', max_length=50, blank=True)

    objects = models.Manager()
    locals = AmpliacaoPrazoCursoManager()

    class Meta:
        verbose_name = 'Solicitação de ampliação de prazo para execução de curso'
        verbose_name_plural = 'Solicitações de ampliação de prazo para execução de curso'

    def __str__(self):
        return 'Solicitação de ampliação de prazo para execução de curso por {}'.format(self.solicitante)

    def save(self, *args, **kwargs):
        self.descricao = str(self)
        super(SolicitacaoAmpliacaoPrazoCurso, self).save(*args, **kwargs)

    def atender(self, avaliador, trabalhador_educando=None,):
        super(SolicitacaoAmpliacaoPrazoCurso, self).atender(avaliador, trabalhador_educando)


class SolicitacaoRealocacao(SolicitacaoUsuario):
    unidade_lotacao = models.CharField(verbose_name='Unidade de lotação', max_length=80)
    novo_setor_trabalho = models.CharField(verbose_name='Novo setor de trabalho', max_length=80)
    motivo = models.TextField(verbose_name='Motivo')
    nome_nova_chefia = models.ForeignKeyPlus('ppe.ChefiaPPE', verbose_name='Nome da Nova Chefia', on_delete=models.CASCADE)
    cargo_nova_chefia = models.CharField(verbose_name='Cargo da nova chefia', max_length=100,null= True, blank=True)
    indicacao_nova_unidade = models.CharField(verbose_name='Indicação Nova Unidade', max_length=100,null= True, blank=True)
    a_partir_quando = models.DateFieldPlus(verbose_name='A partir de quando?', blank=True, null= True)
    objects = models.Manager()
    locals = RealocacaoManager()

    class Meta:
        verbose_name = 'Solicitação de realocação'
        verbose_name_plural = 'Solicitações de realocação'

    def __str__(self):
        return 'Solicitação de realocação por {}'.format(self.solicitante)

    def save(self, *args, **kwargs):
        self.descricao = str(self)
        super(SolicitacaoRealocacao, self).save(*args, **kwargs)

    def atender(self, avaliador, trabalhador_educando=None, ):
        super(SolicitacaoRealocacao, self).atender(avaliador, trabalhador_educando)


class SolicitacaoVisitaTecnicaUnidade(SolicitacaoUsuario):
    TIPO_OPCOES_CHOICES = [['Tipo1', 'Tipo1'], ['Tipo2', 'Tipo2'], ['Tipo3', 'Tipo3'],]
    unidade = models.CharField(verbose_name='Unidade', max_length=50)
    visitante = models.CharField(verbose_name='Visitante', max_length=250, null= True, blank=True)
    opcoes = models.CharFieldPlus(choices=TIPO_OPCOES_CHOICES, verbose_name='Tipo de Opções',
                                                 null=True, blank=False)
    data = models.DateFieldPlus('Data', null=True, blank=True)
    #hora_inicio = models.TimeFieldPlus('Horário Início', help_text='Utilize o formato hh:mm:ss', null=True, blank=True)
    #hora_fim = models.TimeFieldPlus('Horário Fim', help_text='Utilize o formato hh:mm:ss', null=True, blank=True)

    observacao = models.TextField('Observação', null=True, blank=True)

    objects = models.Manager()
    locals = VisitaTecnicaUnidadeManager()

    class Meta:
        verbose_name = 'Solicitação de visita técnica na unidade'
        verbose_name_plural = 'Solicitações de visita técnica na unidade'

    def __str__(self):
        return 'Solicitação de visita técnica na unidade por {}'.format(self.solicitante)

    def save(self, *args, **kwargs):
        self.descricao = str(self)
        super(SolicitacaoVisitaTecnicaUnidade, self).save(*args, **kwargs)

    def atender(self, avaliador, trabalhador_educando=None, ):
        super(SolicitacaoVisitaTecnicaUnidade, self).atender(avaliador, trabalhador_educando)

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

    # def atender(self, avaliador, trabalhador_educando=None,):
    #     super(SolicitacaoDesligamentos, self).atender(avaliador, trabalhador_educando)
    #     matricula_periodo = trabalhador_educando.get_matriculas_periodo()[0]
    #     matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.DESLIGADO)
    #     matricula_periodo.save()
    #     trabalhador_educando.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.DESLIGADO)
    #     trabalhador_educando.save()