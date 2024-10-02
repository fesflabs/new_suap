import urllib
from collections import OrderedDict
from datetime import date, datetime

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.template.defaultfilters import truncatewords
from django.urls import reverse, reverse_lazy
from reversion import revisions as reversion
from reversion.models import Version

from comum.models import Comentario, Configuracao, User
from demandas.utils import Notificar, adicionar_comentario
from comum.utils import tl
from djtools.db import models
from djtools.db.models import ModelPlus
from djtools.middleware.threadlocals import get_user
from djtools.utils import gitlab
from djtools.utils import send_notification
from rh.pdf import dateToStr


class TipoDemanda:
    MELHORIA = 'Melhoria'
    FUNCIONALIDADE = 'Funcionalidade'

    TIPODEMANDA_CHOICES = ((MELHORIA, 'Melhoria'), (FUNCIONALIDADE, 'Funcionalidade'))


class AreaAtuacaoDemanda(models.ModelPlus):
    SEARCH_FIELDS = ['area__nome']
    area = models.OneToOneFieldPlus("comum.AreaAtuacao", verbose_name='Área')
    demandantes = models.ManyToManyField(User, related_name='demanda_demandantesarea_set', verbose_name='Demandantes')
    demandante_responsavel = models.ForeignKeyPlus(User, related_name='demandanteresponsavelarea', verbose_name='Demandante Responsável pela Área', null=True)
    tags_relacionadas = models.ManyToManyField("demandas.Tag", verbose_name='Tags relacionadas')
    recebe_sugestoes = models.BooleanField('Recebe sugestões de melhorias?', default=False)

    class Meta:
        verbose_name = 'Área de Atuação'
        verbose_name_plural = 'Áreas de Atuação'

    def __str__(self):
        return f'{self.area}'

    @staticmethod
    def areas_recebem_sugestoes():
        return AreaAtuacaoDemanda.objects.filter(recebe_sugestoes=True).order_by('area__nome')

    def qtd_sugestoes_ativas(self):
        sugestoes = SugestaoMelhoria.objects.filter(area_atuacao=self)
        return sugestoes.exclude(situacao__in=[SugestaoMelhoria.SITUACAO_DEFERIDA, SugestaoMelhoria.SITUACAO_CANCELADA, SugestaoMelhoria.SITUACAO_INDEFERIDA]).count()

    def qtd_sugestoes_deferidas(self):
        sugestoes = SugestaoMelhoria.objects.filter(area_atuacao=self)
        return sugestoes.filter(situacao=SugestaoMelhoria.SITUACAO_DEFERIDA).count()


class AnalistaDesenvolvedor(models.ModelPlus):
    usuario = models.OneToOneFieldPlus(User, related_name='analistadesenvolvedor', verbose_name='Analista/Desenvolvedor', null=False)
    username_gitlab = models.CharFieldPlus(verbose_name='Username Gitlab')
    eh_analista = models.BooleanField('É Analista?', default=True)
    eh_desenvolvedor = models.BooleanField('É Desenvolvedor?', default=True)
    ativo = models.BooleanField('Ativo?', default=True)

    pipeline = models.IntegerField('Pipeline da IDE', null=True, blank=True)
    senha_ide = models.CharFieldPlus('Senha da IDE', null=True, blank=True)

    class Meta:
        verbose_name = 'Analista/Desenvolvedor'
        verbose_name_plural = 'Analistas/Desenvolvedores'

    def __str__(self):
        return f'{self.usuario}'

    def get_absolute_url(self):
        return '/demandas/analistadesenvolvedor/{}/'.format(self.pk)

    def save(self, *args, **kwargs):
        if self.pipeline is None and gitlab.access_token():
            self.pipeline = self.criar_pipeline().get('id')
        super().save(*args, **kwargs)
        grupo_analista = Group.objects.get(name='Analista')
        if self.eh_analista:
            self.usuario.groups.add(grupo_analista)
        else:
            self.usuario.groups.remove(grupo_analista)
        grupo_desenvolvedor = Group.objects.get(name='Desenvolvedor')
        if self.eh_desenvolvedor:
            self.usuario.groups.add(grupo_desenvolvedor)
        else:
            self.usuario.groups.remove(grupo_desenvolvedor)

    def get_url_issues_em_andamento_projeto(self, projeto):
        return urllib.parse.urljoin(
            f"{Configuracao.get_valor_por_chave('demandas', 'gitlab_url')}",
            f"{projeto.grupo}/{projeto.nome_projeto}/issues/?scope=all&utf8=✓&state=opened&assignee_username={self.username_gitlab}",
        )

    def criar_pipeline(self):
        variables = [
            {'key': 'USERNAME', 'variable_type': 'env_var', 'value': self.usuario.username},
            {'key': 'PASSWORD', 'variable_type': 'env_var', 'value': self.senha_ide},
        ]
        return gitlab.create_pipeline(variables)

    def criar_atualizar_ide(self):
        gitlab.execute_job(self.pipeline, 'ide-deploy')

    def get_log_ide_cricao_atualizacao_ide(self):
        return gitlab.job_log(self.pipeline, 'ide-deploy')

    def excluir_ide(self):
        gitlab.execute_job(self.pipeline, 'ide-undeploy')

    def destruir_ide(self):
        gitlab.execute_job(self.pipeline, 'ide-destroy')
        self.pipeline = None
        self.save()

    def get_senha_ide(self):
        log = gitlab.job_log(self.pipeline, 'ide-deploy')
        tokens = log.split('SENHA: ')
        if len(tokens) > 1:
            return tokens[1][0:6]
        return None


class ProjetoGitlab(models.ModelPlus):
    id_projeto_gitlab = models.PositiveIntegerFieldPlus(verbose_name='ID projeto no gitlab', null=False)
    nome_projeto = models.CharFieldPlus(verbose_name='Nome do projeto')
    grupo = models.CharFieldPlus(verbose_name='Grupo')
    ativo = models.BooleanField('Ativo?', default=True)

    class Meta:
        verbose_name = 'Projeto no Gitlab'
        verbose_name_plural = 'Projetos no Gitlab'

    def __str__(self):
        return f'{self.nome_projeto}'


class Situacao:
    ESTADO_ABERTO = 'Solicitada'
    ESTADO_EM_NEGOCIACAO = 'Em negociação'
    ESTADO_EM_ANALISE = 'Em análise'
    ESTADO_APROVADO = 'Aprovada'
    ESTADO_EM_DESENVOLVIMENTO = 'Em desenvolvimento'
    ESTADO_EM_HOMOLOGACAO = 'Em homologação'
    ESTADO_HOMOLOGADA = 'Homologada'
    ESTADO_EM_IMPLANTACAO = 'Em implantação'
    ESTADO_CONCLUIDO = 'Concluída'
    ESTADO_CANCELADO = 'Cancelada'
    ESTADO_SUSPENSO = 'Suspensa'

    INICIAL = [ESTADO_ABERTO]
    TERMINAL = [ESTADO_CONCLUIDO, ESTADO_CANCELADO]

    ENCAMINHAMENTOS = {
        ESTADO_ABERTO: [ESTADO_EM_NEGOCIACAO, ESTADO_SUSPENSO, ESTADO_CANCELADO],
        ESTADO_EM_NEGOCIACAO: [ESTADO_EM_ANALISE, ESTADO_EM_DESENVOLVIMENTO, ESTADO_SUSPENSO, ESTADO_CANCELADO],
        ESTADO_EM_ANALISE: [ESTADO_APROVADO, ESTADO_EM_NEGOCIACAO, ESTADO_SUSPENSO, ESTADO_CANCELADO],
        ESTADO_APROVADO: [ESTADO_EM_NEGOCIACAO, ESTADO_EM_DESENVOLVIMENTO, ESTADO_SUSPENSO, ESTADO_CANCELADO],
        ESTADO_EM_DESENVOLVIMENTO: [ESTADO_EM_NEGOCIACAO, ESTADO_EM_HOMOLOGACAO, ESTADO_EM_IMPLANTACAO, ESTADO_SUSPENSO, ESTADO_CANCELADO],
        ESTADO_EM_HOMOLOGACAO: [ESTADO_EM_NEGOCIACAO, ESTADO_EM_DESENVOLVIMENTO, ESTADO_HOMOLOGADA, ESTADO_SUSPENSO, ESTADO_CANCELADO],
        ESTADO_HOMOLOGADA: [ESTADO_EM_NEGOCIACAO, ESTADO_EM_IMPLANTACAO, ESTADO_SUSPENSO, ESTADO_CANCELADO],
        ESTADO_EM_IMPLANTACAO: [ESTADO_EM_NEGOCIACAO, ESTADO_SUSPENSO, ESTADO_CONCLUIDO],
        ESTADO_SUSPENSO: [ESTADO_EM_NEGOCIACAO, ESTADO_EM_DESENVOLVIMENTO, ESTADO_EM_HOMOLOGACAO, ESTADO_CANCELADO],
        ESTADO_CONCLUIDO: [],
        ESTADO_CANCELADO: [],
    }

    ESTADO_CHOICES = [
        [ESTADO_ABERTO, ESTADO_ABERTO],
        [ESTADO_EM_NEGOCIACAO, ESTADO_EM_NEGOCIACAO],
        [ESTADO_EM_ANALISE, ESTADO_EM_ANALISE],
        [ESTADO_APROVADO, ESTADO_APROVADO],
        [ESTADO_EM_DESENVOLVIMENTO, ESTADO_EM_DESENVOLVIMENTO],
        [ESTADO_EM_HOMOLOGACAO, ESTADO_EM_HOMOLOGACAO],
        [ESTADO_HOMOLOGADA, ESTADO_HOMOLOGADA],
        [ESTADO_EM_IMPLANTACAO, ESTADO_EM_IMPLANTACAO],
        [ESTADO_CONCLUIDO, ESTADO_CONCLUIDO],
        [ESTADO_CANCELADO, ESTADO_CANCELADO],
        [ESTADO_SUSPENSO, ESTADO_SUSPENSO],
    ]

    ESTADO_AMIGAVEL = {
        ESTADO_ABERTO: 'Solicitar',
        ESTADO_EM_NEGOCIACAO: 'Negociar',
        ESTADO_EM_ANALISE: 'Analisar',
        ESTADO_APROVADO: 'Aprovar',
        ESTADO_EM_DESENVOLVIMENTO: 'Desenvolver',
        ESTADO_EM_HOMOLOGACAO: 'Homologar',
        ESTADO_HOMOLOGADA: 'Homologada',
        ESTADO_EM_IMPLANTACAO: 'Implantar',
        ESTADO_CONCLUIDO: 'Concluir',
        ESTADO_CANCELADO: 'Cancelar',
        ESTADO_SUSPENSO: 'Suspender',
    }

    ESTADO_FLUXO = OrderedDict()
    ESTADO_FLUXO[ESTADO_ABERTO] = 'Etapa de abertura da demanda (Responsável: Demandante)'
    ESTADO_FLUXO[ESTADO_EM_NEGOCIACAO] = 'Etapa de levantamento de requisitos (Responsável: Analistas)'
    ESTADO_FLUXO[ESTADO_EM_ANALISE] = 'Etapa de análise da consolidação da demanda (Responsável: Demandantes e Interessados)'
    ESTADO_FLUXO[ESTADO_APROVADO] = 'Etapa de aprovação da consolidação da demanda'
    ESTADO_FLUXO[ESTADO_EM_DESENVOLVIMENTO] = 'Etapa de desenvolvimento da demanda (Responsável: Desenvolvedor)'
    ESTADO_FLUXO[ESTADO_EM_HOMOLOGACAO] = 'Etapa de testes da execução da demanda (Responsável: Demandantes e Interessados)'
    ESTADO_FLUXO[ESTADO_HOMOLOGADA] = 'Etapa de aprovação da homologação da demanda'
    ESTADO_FLUXO[ESTADO_EM_IMPLANTACAO] = 'Etapa de encaminhamento da demanda para implantação (Responsável: Desenvolvedor)'
    ESTADO_FLUXO[ESTADO_CONCLUIDO] = 'Etapa de conclusão da demanda (Responsável: Sistema)'

    @classmethod
    def get_choices(cls, estado=None):
        if estado:
            choices = list()

            for estado in cls.ENCAMINHAMENTOS[estado]:
                choices.append([estado, estado])

            return choices

        return cls.ESTADO_CHOICES

    @classmethod
    def get_estados_amigavel(cls, estado):
        estados = list()

        for estado in cls.ENCAMINHAMENTOS[estado]:
            estados.append(cls.ESTADO_AMIGAVEL.get(estado, estado))

        return estados

    @classmethod
    def get_etapas_amigavel(cls, estado):
        estados = list()

        for estado in cls.ENCAMINHAMENTOS[estado]:
            if not estado in [Situacao.ESTADO_CANCELADO, Situacao.ESTADO_SUSPENSO]:
                estados.append(cls.ESTADO_AMIGAVEL.get(estado, estado))
        return estados

    @classmethod
    def get_situacao_em_amigavel(cls, amigavel):
        for estado, valor in list(cls.ESTADO_AMIGAVEL.items()):
            if valor == amigavel:
                return estado
        return None

    @classmethod
    def eh_estado_inicial(cls, estado):
        return estado in cls.INICIAL

    @classmethod
    def eh_estado_terminal(cls, estado):
        return estado in cls.TERMINAL

    @classmethod
    def eh_estado_com_data_previsao(cls, estado):
        return estado in [cls.ESTADO_EM_ANALISE, cls.ESTADO_EM_DESENVOLVIMENTO, cls.ESTADO_EM_HOMOLOGACAO, cls.ESTADO_EM_IMPLANTACAO]

    @classmethod
    def get_status_dod_interessados(cls):
        return [
            cls.ESTADO_EM_ANALISE,
            cls.ESTADO_APROVADO,
            cls.ESTADO_EM_DESENVOLVIMENTO,
            cls.ESTADO_EM_HOMOLOGACAO,
            cls.ESTADO_HOMOLOGADA,
            cls.ESTADO_EM_IMPLANTACAO,
            cls.ESTADO_CONCLUIDO,
            cls.ESTADO_SUSPENSO,
        ]

    @classmethod
    def eh_estado_possivel(cls, estado_atual, estado_futuro):
        return estado_futuro in cls.ENCAMINHAMENTOS[estado_atual]


class Tag(ModelPlus):
    SEARCH_FIELDS = ['nome', 'sigla']

    nome = models.CharFieldPlus('Nome', max_length=200, unique=True)
    sigla = models.CharFieldPlus('Sigla', null=True, blank=True)
    icone = models.CharFieldPlus('Ícone', max_length=80, blank=True, null=True,
                                 help_text='Informe um ícone para representar esta Tag. Fonte: https://fontawesome.com/')

    def __str__(self):
        return self.nome

    class Meta:
        ordering = ['nome']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'


class DemandasQueryset(models.QuerySet):
    def ativas(self):
        return self.filter().exclude(situacao__in=[Situacao.ESTADO_CANCELADO, Situacao.ESTADO_CONCLUIDO])

    def inativas(self):
        return self.filter(situacao__in=[Situacao.ESTADO_CANCELADO, Situacao.ESTADO_CONCLUIDO])

    def em_andamento(self):
        return self.filter(situacao__in=[Situacao.ESTADO_EM_NEGOCIACAO, Situacao.ESTADO_EM_DESENVOLVIMENTO, Situacao.ESTADO_EM_IMPLANTACAO])

    def aguardando_feedback(self):
        return self.filter(situacao__in=[Situacao.ESTADO_EM_ANALISE, Situacao.ESTADO_EM_HOMOLOGACAO, Situacao.ESTADO_SUSPENSO])

    def nao_iniciadas(self):
        return self.filter(situacao__in=[Situacao.ESTADO_ABERTO, Situacao.ESTADO_APROVADO, Situacao.ESTADO_HOMOLOGADA])


class DemandasManager(models.Manager):
    def get_queryset(self):
        return DemandasQueryset(self.model, using=self._db)

    def ativas(self):
        return self.get_queryset().ativas()

    def inativas(self):
        return self.get_queryset().inativas()

    def em_andamento(self):
        return self.get_queryset().em_andamento()

    def aguardando_feedback(self):
        return self.get_queryset().aguardando_feedback()

    def nao_iniciadas(self):
        return self.get_queryset().nao_iniciadas()


@reversion.register()
class Demanda(ModelPlus):
    SEARCH_FIELDS = ['id', 'titulo', 'descricao']
    area = models.ForeignKeyPlus('demandas.AreaAtuacaoDemanda', verbose_name="Área de Atuação", null=True)
    tipo = models.CharFieldPlus('Tipo', choices=TipoDemanda.TIPODEMANDA_CHOICES, default=TipoDemanda.FUNCIONALIDADE)
    titulo = models.CharField('Título da Demanda', max_length=250)
    descricao = models.TextField('Descrição da Demanda', help_text='Evite colocar informações sensiveis nesse campo pois essa descrição é pública.')
    privada = models.BooleanField('Privada?', default=False, help_text='Indique se a demanda deve ser privada nos seus detalhes até a sua finalização.')
    aberto_em = models.DateTimeField('Aberto Em', auto_now_add=True)
    prazo_legal = models.DateField(
        'Prazo Legal',
        help_text="Só preencher esse campo se existir um prazo legal da demanda. ex: Data limite(por lei, ou determinação) para estar em produção.",
        blank=True,
        null=True,
    )
    data_atualizacao = models.DateField('Data da Última Atualização', blank=True, null=True)
    demandantes = models.ManyToManyField(User, related_name='demanda_demandantes_set', verbose_name='Demandantes')
    interessados = models.ManyToManyField(
        User, related_name='demanda_interessados_set', verbose_name='Interessados', help_text='Vincule outros usuários que desejem acompanhar as discussões desta demanda.'
    )
    observadores_pendentes = models.ManyToManyField(User, related_name='demanda_observadores_pendentes_set', verbose_name='Observadores Pendentes')
    observadores = models.ManyToManyField(User, related_name='demanda_observadores_set', verbose_name='Observadores')
    desenvolvedores = models.ManyToManyField(
        User, related_name='demanda_desenvolvedores_set', verbose_name='Desenvolvedores', help_text='Vincule usuários desenvolvedores desta demanda.'
    )
    analistas = models.ManyToManyField(User, related_name='demanda_analistas_set', verbose_name='Analista', help_text='Vincule usuários analistas dessa demanda')
    tags = models.ManyToManyField(Tag, related_name='demanda_tags_set', verbose_name='Tags')

    prioridade = models.PositiveIntegerField('Prioridade', null=True, blank=True)
    situacao = models.CharFieldPlus('Etapa', choices=Situacao.ESTADO_CHOICES, default=Situacao.ESTADO_ABERTO)

    especificacao_tecnica = models.TextField(verbose_name='Especificação Técnica', blank=True)

    ambiente_homologacao = models.ForeignKeyPlus('demandas.AmbienteHomologacao', verbose_name='Ambiente de Homologação', blank=True, null=True)
    url_validacao = models.CharFieldPlus('URL para Ambiente de Homologação', null=True, blank=True)
    senha_homologacao = models.CharFieldPlus('Senha para Ambiente de Homologação', null=True, blank=True)

    id_merge_request = models.PositiveIntegerField('ID do Merge-Request', help_text='Identificador do Merge-request. Exemplo: na url https://gitlab.ifrn.edu.br/cosinf/suap/-/merge_requests/25 o número 25 é o identificador.', null=True, blank=True)
    # Integração com gitlab
    milestone = models.PositiveIntegerField('ID da Milestone', null=True)
    id_repositorio = models.PositiveIntegerField('ID do Repositório GIT', null=True)

    consolidacao_sempre_visivel = models.BooleanField('Consolidação visível durante todas as etapas?', default=False)

    votos = models.IntegerFieldPlus(verbose_name='Votos', default=0)

    objects = DemandasManager()

    class Meta:
        verbose_name = 'Demanda'
        verbose_name_plural = 'Demandas'
        ordering = ['prioridade', 'area']
        permissions = (('atende_demanda', 'Pode atender Demanda'), ('pode_relatorio', 'Pode visualizar relatórios'))

    def __str__(self):
        if self.tem_dod:
            titulo = self.get_dod().descricao
        else:
            titulo = self.titulo
        return f'Demanda {self.pk}: {titulo}'

    @classmethod
    @transaction.atomic
    def atualizar_prioridades(self, area, usuario):
        demandas = Demanda.objects.ativas().filter(area=area).order_by('prioridade', 'pk')
        for count, demanda in enumerate(demandas, start=1):
            if demanda.prioridade != count:
                demanda.prioridade = count
                Demanda.criar_historico_prioridade(demanda, usuario, count)
                demanda.save()

        # Demandas Concluídas ou Canceladas devem ter prioridade setada para None
        demandas_inativas = Demanda.objects.inativas().filter(area=area, prioridade__isnull=False)
        for inativa in demandas_inativas:
            Demanda.criar_historico_prioridade(inativa, usuario, None)
        demandas_inativas.update(prioridade=None)

    @classmethod
    def colocar_demanda_em_ultima_prioridade(cls, demanda, usuario):
        area = demanda.area
        area_as_outras_demandas = Demanda.objects.ativas().filter(area=area).exclude(prioridade=None).exclude(pk=demanda.pk)

        if area_as_outras_demandas.exists():
            ultima_prioridade = area_as_outras_demandas.order_by('-prioridade').first().prioridade + 1
        else:
            ultima_prioridade = 1

        demanda.prioridade = ultima_prioridade
        demanda.save()

        # atualiza a prioridade das demandas da área
        Demanda.atualizar_prioridades(area, usuario)

    @classmethod
    def criar_historico_prioridade(self, demanda, usuario, prioridade):
        HistoricoPrioridade.objects.create(demanda=demanda, prioridade=prioridade, usuario=usuario)

    def permite_visualizar(self, user):
        return user.has_perm('demandas.atende_demanda') or user.has_perm('demandas.change_demanda') or user.has_perm('demandas.view_demanda')

    def eh_demandante(self, user):
        return self.demandantes.filter(pk=user.pk).exists()

    def eh_interessado(self, user):
        return self.interessados.filter(pk=user.pk).exists()

    def eh_observador_pendente(self, user):
        return self.observadores_pendentes.filter(pk=user.pk).exists()

    def eh_observador(self, user):
        return self.observadores.filter(pk=user.pk).exists()

    def pode_anexar(self, user):
        return (self.eh_demandante(user) or user.has_perm("demandas.atende_demanda")) and self.situacao in [
            Situacao.ESTADO_ABERTO,
            Situacao.ESTADO_EM_NEGOCIACAO,
            Situacao.ESTADO_EM_ANALISE,
            Situacao.ESTADO_APROVADO,
            Situacao.ESTADO_EM_DESENVOLVIMENTO,
            Situacao.ESTADO_SUSPENSO,
            Situacao.ESTADO_EM_HOMOLOGACAO,
            Situacao.ESTADO_HOMOLOGADA,
            Situacao.ESTADO_EM_IMPLANTACAO,
        ]

    def pode_votar(self):
        return (self.situacao not in [Situacao.ESTADO_CANCELADO, Situacao.ESTADO_CONCLUIDO] and not self.privada)

    def get_prioridade_display(self):
        return str(self.prioridade) if self.prioridade else 'Sem prioridade'

    @property
    def em_negociacao(self):
        return self.situacao == Situacao.ESTADO_EM_NEGOCIACAO

    @property
    def em_analise(self):
        return self.situacao == Situacao.ESTADO_EM_ANALISE

    @property
    def aprovada(self):
        return self.situacao == Situacao.ESTADO_APROVADO

    @property
    def em_desenvolvimento(self):
        return self.situacao == Situacao.ESTADO_EM_DESENVOLVIMENTO

    @property
    def em_homologacao(self):
        return self.situacao == Situacao.ESTADO_EM_HOMOLOGACAO

    @property
    def homologada(self):
        return self.situacao == Situacao.ESTADO_HOMOLOGADA

    def em_atraso(self):
        if self.get_ultimo_historico_situacao().em_atraso:
            return True
        return False

    @property
    def pode_remover_anexo(self):
        return self.situacao in [Situacao.ESTADO_ABERTO, Situacao.ESTADO_EM_NEGOCIACAO]

    @property
    def tem_dod(self):
        if not self.dod_set.exists():
            return False
        dod = self.dod_set.all()[0]
        return dod.feito

    def get_dod(self):
        if self.dod_set.exists():
            return self.dod_set.all()[0]
        return False

    def ja_foi_aprovada(self):
        return self.situacao in [
            Situacao.ESTADO_APROVADO,
            Situacao.ESTADO_EM_DESENVOLVIMENTO,
            Situacao.ESTADO_EM_HOMOLOGACAO,
            Situacao.ESTADO_HOMOLOGADA,
            Situacao.ESTADO_EM_IMPLANTACAO,
            Situacao.ESTADO_CONCLUIDO,
        ]

    def nao_foi_homologada(self):
        return self.situacao in [
            Situacao.ESTADO_EM_NEGOCIACAO,
            Situacao.ESTADO_EM_ANALISE,
            Situacao.ESTADO_APROVADO,
            Situacao.ESTADO_EM_DESENVOLVIMENTO,
            Situacao.ESTADO_EM_HOMOLOGACAO,
        ]

    def eh_situacao_inicial(self):
        return Situacao.eh_estado_inicial(self.situacao)

    def eh_situacao_terminal(self):
        return Situacao.eh_estado_terminal(self.situacao)

    def eh_situacao_com_data_previsao(self):
        return Situacao.eh_estado_com_data_previsao(self.situacao)

    def get_id_repositorio(self):
        if self.id_repositorio:
            return self.id_repositorio
        return Configuracao.get_valor_por_chave('demandas', 'gitlab_suap_id')

    def get_situacoes(self):
        return Situacao.get_estados_amigavel(self.situacao)

    def get_etapas(self):
        return Situacao.get_etapas_amigavel(self.situacao)

    def get_ultimo_historico_situacao(self):
        return self.historicosituacao_set.order_by('-data_hora')[0]

    def permite_alterar(self):
        return self.situacao not in Situacao.TERMINAL

    def permite_cancelar(self):
        return self.situacao not in Situacao.TERMINAL

    def get_absolute_url(self):
        return reverse_lazy('demanda_visualizar', kwargs={'demanda_id': self.pk})

    def get_visualizar_demanda_url(self):
        return '{}{}'.format(settings.SITE_URL, self.get_absolute_url())

    def tem_historico_revisoes(self):
        return Version.objects.get_for_object(self).exists()

    @transaction.atomic
    def alterar_situacao(self, usuario, situacao, **kwargs):
        texto_comentario = kwargs.get('comentario')
        data_previsao = kwargs.get('data_previsao')
        data_conclusao = kwargs.get('data_conclusao')
        ambiente_homologacao = kwargs.get('ambiente_homologacao')
        url_validacao = kwargs.get('url_validacao')
        senha_homologacao = kwargs.get('senha_homologacao')
        desenvolvedores = kwargs.get('desenvolvedores')
        analistas = kwargs.get('analistas')
        editou_data_previsao = kwargs.get('editou_data_previsao')
        id_merge_request = kwargs.get('id_merge_request')

        if analistas:
            novos_analistas = set(analistas) - set(self.analistas.all())
            self.analistas.set(analistas)
            Notificar.analistas_vinculados_a_demanda(self, novos_analistas, usuario)
        if desenvolvedores:
            novos_desenvolvedores = set(desenvolvedores) - set(self.desenvolvedores.all())
            self.desenvolvedores.set(desenvolvedores)
            Notificar.desenvolvedores_vinculados_a_demanda(self, novos_desenvolvedores, usuario)

        # Se demanda é concluída ou cancelada, a prioridade é definida como None e a Área tem a sua lista de prioridades atualizadas
        atualizar_prioridade = False
        if Situacao.eh_estado_terminal(situacao):
            self.prioridade = None
            atualizar_prioridade = True

        self.situacao = situacao
        estado_em_homologacao = self.situacao == Situacao.ESTADO_EM_HOMOLOGACAO
        if estado_em_homologacao:
            if ambiente_homologacao:
                self.ambiente_homologacao = ambiente_homologacao
            else:
                self.ambiente_homologacao = None
            if url_validacao:
                self.url_validacao = url_validacao
            else:
                self.url_validacao = None
            if senha_homologacao:
                self.senha_homologacao = senha_homologacao
            else:
                self.senha_homologacao = None

        if id_merge_request:
            self.id_merge_request = id_merge_request
        self.save()

        if atualizar_prioridade:
            Demanda.atualizar_prioridades(self.area, usuario)

        historicosituacao = self.get_ultimo_historico_situacao()

        if historicosituacao and data_conclusao:
            historicosituacao.data_conclusao = data_conclusao
            historicosituacao.save()

        novo_historico = HistoricoSituacao()
        novo_historico.demanda = self
        novo_historico.usuario = usuario
        novo_historico.situacao = self.situacao
        novo_historico.data_previsao = data_previsao
        novo_historico.save()

        if data_conclusao:
            data_atualizacao = data_conclusao
        else:
            data_atualizacao = novo_historico.data_hora

        Demanda.objects.filter(pk=self.pk).update(data_atualizacao=data_atualizacao)
        if editou_data_previsao:
            comentario_nova_previsao = 'Etapa da demanda alterada para {}'.format(situacao)
            if data_previsao:
                comentario_nova_previsao += ' com Data de Previsão para  {}'.format(
                    data_previsao.strftime('%d/%m/%Y'))
            comentario_nova_previsao += '.'

            if texto_comentario:
                adicionar_comentario(
                    usuario=usuario,
                    mensagem='{}\n--\n{}'.format(comentario_nova_previsao, texto_comentario), demanda=self)
            else:
                adicionar_comentario(usuario=usuario, mensagem='{}'.format(comentario_nova_previsao), demanda=self)

        else:
            comentario_nova_previsao = ''
            if not novo_historico.eh_primeiro_historico_da_etapa and data_previsao:
                comentario_nova_previsao = 'Alteração de Data de Previsão para {}.'.format(data_previsao.strftime('%d/%m/%Y'))

            if texto_comentario:
                adicionar_comentario(
                    usuario=usuario, mensagem='Etapa da demanda alterada para {}. {}\n--\n{}'.format(situacao, comentario_nova_previsao, texto_comentario), demanda=self
                )
            else:
                adicionar_comentario(usuario=usuario, mensagem='Etapa da demanda alterada para {}. {}'.format(situacao, comentario_nova_previsao), demanda=self)

        estado_em_analise = self.situacao == Situacao.ESTADO_EM_ANALISE
        eh_observador = self.eh_observador(usuario)

        Notificar.situacao_alterada(self, texto_comentario, estado_em_analise, estado_em_homologacao, eh_observador)
        if self.situacao == Situacao.ESTADO_CONCLUIDO:
            self.gerar_atualizacao_demanda()

    def gerar_atualizacao_demanda(self):
        if self.situacao == Situacao.ESTADO_CONCLUIDO:
            hoje = date.today()
            dod = self.dod_set.first()
            grupos = Group.objects.filter(name__in=dod.envolvidos.split(','))
            if not grupos.exists():
                grupos = Group.objects.filter(name__in=dod.envolvidos.replace('\r', '').split('\n'))

            kwargs = {
                'descricao': dod.descricao,
                'detalhamento': dod.detalhamento,
                'tipo': Atualizacao.FUNCIONALIDADE,
                'data': hoje,
            }

            atualizacao, created = Atualizacao.objects.get_or_create(demanda=self, defaults=kwargs)
            if created:
                atualizacao.grupos.set(grupos)
                responsaveis = User.objects.filter(pk__in=self.desenvolvedores.all().values_list('pk', flat=True) | self.analistas.all().values_list('pk', flat=True))
                atualizacao.responsaveis.set(responsaveis)
                atualizacao.tags.set(self.tags.all())

    def get_anexos(self):
        return self.comentario_set.exclude(anexo__isnull=True).exclude(anexo__exact='').order_by('data_hora')

    def get_vinculos_recebedores_novas_demandas(self):
        vinculos = list()
        group = Group.objects.get(name='Recebedor de Demandas')
        usuarios = User.objects.filter(groups=group)
        for usuario in usuarios:
            vinculos.append(usuario.get_vinculo())
        return vinculos

    def get_vinculos_interessados(self):
        vinculos = list()
        for demandante in self.demandantes.all():
            vinculos.append(demandante.get_vinculo())

        for interessado in self.interessados.all():
            vinculos.append(interessado.get_vinculo())
        return vinculos

    def get_vinculos_demandantes(self):
        vinculos = list()
        for demandante in self.demandantes.all():
            vinculos.append(demandante.get_vinculo())
        return vinculos

    def get_vinculos_observadores(self):
        vinculos = list()
        for observador in self.observadores.all():
            vinculos.append(observador.get_vinculo())
        return vinculos

    def get_vinculos_analistas(self):
        vinculos = list()
        for analista in self.analistas.all():
            vinculos.append(analista.get_vinculo())
        return vinculos

    def get_vinculos_desenvolvedores(self):
        vinculos = list()
        for desenvolvedor in self.desenvolvedores.all():
            vinculos.append(desenvolvedor.get_vinculo())
        return vinculos

    def get_situacao_acompanhamento(self):
        # Utilizada no Relatorio de Acompanhamento de Demandas
        if self.situacao == Situacao.ESTADO_SUSPENSO:
            return '<span class="status status-error">Suspensa por falta de feedback desde {}</span>'.format(dateToStr(self.get_ultimo_historico_situacao().data_hora))
        elif self.situacao in [
            Situacao.ESTADO_EM_IMPLANTACAO,
            Situacao.ESTADO_EM_DESENVOLVIMENTO,
            Situacao.ESTADO_EM_NEGOCIACAO,
            Situacao.ESTADO_APROVADO,
            Situacao.ESTADO_HOMOLOGADA,
        ]:
            return '<span class="status status-alert">{} desde {}</span>'.format(self.situacao, dateToStr(self.get_ultimo_historico_situacao().data_hora))
        elif self.situacao in [Situacao.ESTADO_EM_ANALISE, Situacao.ESTADO_EM_HOMOLOGACAO]:
            return '<span class="status status-error">{} desde {}</span>'.format(self.situacao, dateToStr(self.get_ultimo_historico_situacao().data_hora))
        return '<span class="status status-info">Não iniciada</span>'

    def pode_comentar(self):
        return not self.situacao in Situacao.TERMINAL

    @property
    def qtd_votos(self):
        voto = DemandaVoto.objects.filter(demanda=self)
        return voto.filter(concorda=True).count() - voto.filter(concorda=False).count()

    @property
    def ja_concordou(self):
        usuario = tl.get_user()
        return DemandaVoto.objects.filter(demanda=self, usuario=usuario, concorda=True).exists()

    @property
    def ja_discordou(self):
        usuario = tl.get_user()
        return DemandaVoto.objects.filter(demanda=self, usuario=usuario, concorda=False).exists()

    def quem_concordou(self):
        return DemandaVoto.objects.filter(demanda=self, concorda=True)

    def quem_discordou(self):
        return DemandaVoto.objects.filter(demanda=self, concorda=False)


class DemandaVoto(models.ModelPlus):
    demanda = models.ForeignKeyPlus(Demanda, verbose_name='Demanda', on_delete=models.CASCADE)
    usuario = models.CurrentUserField()
    concorda = models.BooleanField(null=True)
    cadastrado_em = models.DateTimeField('Cadastrado em', auto_now_add=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        demanda = self.demanda
        demanda.votos = demanda.qtd_votos
        demanda.save()


class HistoricoPrioridade(ModelPlus):
    demanda = models.ForeignKeyPlus(Demanda, verbose_name='Demanda', on_delete=models.CASCADE)
    data_hora = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKeyPlus(User, verbose_name='Usuário', related_name='historicoprioridade_usuarios_set', on_delete=models.CASCADE)
    prioridade = models.PositiveIntegerFieldPlus(verbose_name='Prioridade', null=True)

    def __str__(self):
        return '{}: {} ({})'.format(self.pk, self.demanda.titulo, self.prioridade)

    class Meta:
        ordering = ['-data_hora']
        verbose_name = 'Histórico de Prioridades'
        verbose_name_plural = 'Históricos de Prioridades'


class NotaInterna(ModelPlus):
    demanda = models.ForeignKeyPlus(Demanda, on_delete=models.CASCADE)
    nota = models.TextField('Nota')
    usuario = models.CurrentUserField()
    cadastrado_em = models.DateTimeField('Cadastrado em', auto_now_add=True)

    class Meta:
        verbose_name = 'Nota Interna'
        verbose_name_plural = 'Notas Interna'
        ordering = ['-cadastrado_em']

    def __str__(self):
        return truncatewords(self.nota, 25)

    def save(self, *args, **kwargs):
        insert = not self.pk
        super().save(*args, **kwargs)

        if insert:
            Notificar.nota_interna_criada(self)


class DoD(ModelPlus):
    demanda = models.ForeignKeyPlus(Demanda)
    descricao = models.TextField('Descrição', null=True)
    detalhamento = models.TextField('Detalhamento', null=True)
    envolvidos = models.TextField('Grupos de Usuários Envolvidos', null=True)

    class Meta:
        verbose_name = 'Consolidação da Demanda'
        verbose_name_plural = 'Consolidações das Demandas'

        permissions = (('aprovar_dod', 'Pode aprovar demanda'), ('fechar_dod', 'Pode enviar demanda para aprovação'))

    def __str__(self):
        return truncatewords(self.descricao, 25)

    @property
    def feito(self):
        if self.descricao is None or self.descricao == '':
            return False

        if not self.especificacao_set.exists():
            return False

        for especificacao in self.especificacao_set.all():
            if not especificacao.atividades:
                return False

        return True


class Especificacao(ModelPlus):
    dod = models.ForeignKeyPlus(DoD)
    nome = models.CharFieldPlus('Nome')
    atividades = models.TextField('Atividade(s)', blank=True)
    ordem = models.PositiveIntegerFieldPlus('Ordem da Especificação', default=1, min_value=1)

    class Meta:
        verbose_name = 'Especificação'
        verbose_name_plural = 'Especificações'
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome

    @staticmethod
    @transaction.atomic
    def atualizar_ordens(dod):
        for seq, especificacao in enumerate(Especificacao.objects.filter(dod=dod).order_by('ordem', 'pk'), start=1):
            if especificacao.ordem != seq:
                especificacao.ordem = seq
                especificacao.save()


class Anexos(ModelPlus):
    demanda = models.ForeignKeyPlus(Demanda, verbose_name='Demanda', on_delete=models.CASCADE)
    arquivo = models.FileFieldPlus(upload_to='upload/demandas/anexos/', null=True, blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKeyPlus(User, verbose_name='Usuário', related_name='anexos_usuario_set', on_delete=models.CASCADE)

    class Meta:
        ordering = ['data_hora']
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'

    def save(self, *args, **kwargs):
        pk = self.pk

        super().save(*args, **kwargs)

        if not pk:
            adicionar_comentario(usuario=get_user(), mensagem='Adicionou um anexo.', demanda=self.demanda)


class HistoricoSituacao(ModelPlus):
    demanda = models.ForeignKeyPlus(Demanda, verbose_name='Demanda', on_delete=models.CASCADE)
    data_hora = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKeyPlus(User, verbose_name='Usuário', related_name='historicosituacao_usuarios_set', on_delete=models.CASCADE)
    situacao = models.CharFieldPlus('Situacao', choices=Situacao.ESTADO_CHOICES, null=True)
    data_previsao = models.DateFieldPlus('Data de Previsão', null=True)
    data_conclusao = models.DateFieldPlus('Data de Conclusão', null=True)

    def __str__(self):
        return '{}: {} ({})'.format(self.pk, self.demanda.titulo, self.situacao)

    class Meta:
        ordering = ['-data_hora']
        verbose_name = 'Histórico das Etapas'
        verbose_name_plural = 'Históricos das Etapas'

    @property
    def em_atraso(self):
        data_conclusao = self.data_conclusao
        data_previsao = self.data_previsao
        if data_conclusao and data_previsao:
            if data_conclusao > data_previsao:
                return True
        elif data_previsao:
            if self.eh_ultimo_historico:
                data_posterior = date.today()
                if data_previsao < data_posterior:
                    return True
            else:
                data_posterior = self.data_historico_posterior.date()
                if data_previsao < data_posterior:
                    return True
        return False

    @property
    def eh_ultimo_historico(self):
        ultimo_historico = HistoricoSituacao.objects.filter(demanda=self.demanda).order_by('-data_hora')[0]
        if self == ultimo_historico:
            return True
        return False

    @property
    def eh_primeiro_historico_da_etapa(self):
        primeiro_historico_da_etapa = HistoricoSituacao.objects.filter(demanda=self.demanda, situacao=self.situacao).order_by('data_hora').first()
        if self == primeiro_historico_da_etapa:
            return True
        return False

    @property
    def data_historico_posterior(self):
        historico_posterior = HistoricoSituacao.objects.filter(demanda=self.demanda, id__gt=self.id).order_by('id')
        if historico_posterior:
            return historico_posterior[0].data_hora
        return None

    @property
    def get_class_situacao(self):
        if self.situacao in ["Aberta", Situacao.ESTADO_ABERTO]:
            return 'info'
        elif self.situacao in [
            Situacao.ESTADO_EM_NEGOCIACAO,
            Situacao.ESTADO_EM_ANALISE,
            Situacao.ESTADO_EM_DESENVOLVIMENTO,
            Situacao.ESTADO_EM_HOMOLOGACAO,
            Situacao.ESTADO_EM_IMPLANTACAO,
        ]:
            return 'alert'
        elif self.situacao in [Situacao.ESTADO_APROVADO, Situacao.ESTADO_HOMOLOGADA, Situacao.ESTADO_CONCLUIDO]:
            return 'success'
        return 'error'

    @property
    def conclusao(self):
        data_conclusao = self.data_conclusao
        data_previsao = self.data_previsao
        responsaveis = 'desenvolvedores'
        if self.situacao == Situacao.ESTADO_EM_ANALISE or self.situacao == Situacao.ESTADO_EM_HOMOLOGACAO:
            responsaveis = 'demandantes'
        if data_conclusao and data_previsao:
            if data_conclusao > data_previsao:
                dias = (data_conclusao - data_previsao).days
                return '<span class="status status-alert">Em {}, com atraso de {} dias, por parte dos {}.</span>'.format(
                    date.strftime(data_conclusao, "%d/%m/%Y"), dias, responsaveis
                )
            elif data_conclusao == data_previsao:
                return '<span class="status status-success">Em {}, por parte dos {}.</span>'.format(date.strftime(data_conclusao, "%d/%m/%Y"), responsaveis)
            return '<span class="status status-success">Em {}, antes da previsão, por parte dos {}.</span>'.format(date.strftime(data_conclusao, "%d/%m/%Y"), responsaveis)
        elif data_conclusao and not data_previsao:
            return date.strftime(data_conclusao, "%d/%m/%Y")
        elif data_previsao:
            if self.eh_ultimo_historico:
                data_posterior = date.today()
                if data_previsao < data_posterior:
                    dias = (data_posterior - data_previsao).days
                    return '<span class="status status-error">Em atraso de {} dias, por parte dos {}.</span>'.format(dias, responsaveis)
            else:
                data_posterior = self.data_historico_posterior.date()
                if data_previsao < data_posterior:
                    dias = (data_posterior - data_previsao).days
                    return '<span class="status status-alert">Reprovada com atraso de {} dias, por parte dos {}.</span>'.format(dias, responsaveis)
        return '-'


class Atualizacao(ModelPlus):
    FUNCIONALIDADE = 'Funcionalidade'
    MANUTENCAO = 'Manutenção'
    BUG = 'Bug'
    TIPO_CHOICES = ((FUNCIONALIDADE, 'Funcionalidade'), (MANUTENCAO, 'Manutenção'), (BUG, 'Bug'))

    descricao = models.CharFieldPlus('Título')
    detalhamento = models.TextField('Detalhamento', blank=True, null=True)
    tipo = models.CharFieldPlus(choices=TIPO_CHOICES)
    tags = models.ManyToManyField(Tag, verbose_name='Tags')
    grupos = models.ManyToManyField(Group, verbose_name='Grupos Envolvidos')
    data = models.DateFieldPlus('Data de Implantação')
    demanda = models.ForeignKeyPlus(Demanda, verbose_name='Demanda Vinculada', null=True, blank=True)
    responsaveis = models.ManyToManyField(
        User, related_name='atualizacao_responsaveis_set', verbose_name='Responsáveis', help_text='Vincule usuários desenvolvedores desta atualização.'
    )

    class Meta:
        verbose_name = 'Atualização'
        verbose_name_plural = 'Atualizações'
        ordering = ['-data']

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return reverse('demanda_atualizacao', kwargs={'atualizacao_id': self.id})

    def save(self, *args, **kwargs):
        pk = self.pk
        super().save(*args, **kwargs)
        if pk is None:
            self.notificar_interessados()

    def get_tags(self):
        lista = []
        for tag in self.tags.all():
            lista.append(tag.nome)
        return lista

    def notificar_interessados(self):
        for grupo in self.grupos.all():
            [self.notificar(user) for user in grupo.user_set.all()]

    def notificar(self, user):
        send_notification(
            'Atualização do Sistema',
            'Atualização: <b>{}</b>\n\n<p>{}</p>'.format(self.descricao, self.detalhamento or ''),
            settings.DEFAULT_FROM_EMAIL,
            [user.get_vinculo()],
            categoria='Atualização do Sistema'
        )


def altera_permissao_apos_salvar_outros_interessados(sender, **kwargs):
    group = Group.objects.get(name='Visualizador de Demandas')

    visualizador_demandas_sem_permissao = User.objects.filter(demanda_interessados_set__isnull=False).exclude(groups=group)

    for user in visualizador_demandas_sem_permissao:
        user.groups.add(group)


@receiver(post_save, sender=Comentario, dispatch_uid="enviar_email_ao_comentar")
def enviar_email_ao_comentar(sender, instance, **kwargs):
    if instance.content_type in ContentType.objects.filter(app_label='demandas', model='sugestaomelhoria'):
        sugestao_melhoria = instance.content_object
        comentario = instance
        Notificar.novo_comentario_em_sugestao_melhoria(sugestao_melhoria, comentario)

    elif instance.content_type in ContentType.objects.filter(app_label='demandas'):
        if not instance.texto.startswith('Etapa da demanda alterada para'):
            Notificar.novo_comentario(instance)


class SugestaoMelhoria(models.Model):
    SITUACAO_PENDENTE = '1'
    SITUACAO_EM_ANALISE = '2'
    SITUACAO_SUSPENSA = '3'
    SITUACAO_DEFERIDA = '4'
    SITUACAO_INDEFERIDA = '5'
    SITUACAO_CANCELADA = '6'
    SITUACAO_CHOICES = [
        [SITUACAO_PENDENTE, 'Pendente'],
        [SITUACAO_EM_ANALISE, 'Em análise'],
        [SITUACAO_SUSPENSA, 'Suspensa'],
        [SITUACAO_DEFERIDA, 'Deferida'],
        [SITUACAO_INDEFERIDA, 'Indeferida'],
        [SITUACAO_CANCELADA, 'Cancelada'],
    ]

    area_atuacao = models.ForeignKeyPlus("demandas.AreaAtuacaoDemanda", verbose_name='Área de Atuação')
    tags = models.ManyToManyField("demandas.Tag", verbose_name='Tags relacionadas')
    requisitante = models.CurrentUserField(related_name='sugestaomelhoria_requisitante', verbose_name='Requisitante')
    titulo = models.CharField('Título', max_length=250)
    descricao = models.TextField('Descrição')
    situacao = models.CharFieldPlus('Situação', choices=SITUACAO_CHOICES, default=SITUACAO_PENDENTE)
    interessados = models.ManyToManyField(User, related_name='sugestaomelhoria_interessados_set', verbose_name='Interessados')
    responsavel = models.ForeignKeyPlus(User, related_name='sugestaomelhoria_responsavel', verbose_name='Responsável', null=True)
    demanda_gerada = models.ForeignKeyPlus("demandas.Demanda", verbose_name='Demanda Gerada', null=True,
                                           on_delete=models.SET_NULL)
    votos = models.IntegerFieldPlus(verbose_name='Votos', default=0)
    cadastrado_em = models.DateTimeField('Data de Cadastro', auto_now_add=True, null=True, blank=True)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Sugestão de Melhoria'
        verbose_name_plural = 'Sugestões de Melhorias'

    def __str__(self):
        return f'Sugestão de Melhoria #{self.pk}'

    def get_absolute_url(self):
        return reverse('sugestao_melhoria', kwargs={'sugestao_melhoria_id': self.id})

    @staticmethod
    def sugestoes_por_area(area_atuacao, qs_sugestoes_initial=None):
        sugestoes = qs_sugestoes_initial if qs_sugestoes_initial is not None else SugestaoMelhoria.objects.all()
        return sugestoes.filter(area_atuacao=area_atuacao)

    @staticmethod
    def sugestoes_por_tags(tags, qs_sugestoes_initial=None):
        sugestoes = qs_sugestoes_initial if qs_sugestoes_initial is not None else SugestaoMelhoria.objects.all()
        return sugestoes.filter(tags=tags)

    @staticmethod
    def sugestoes_por_situacao(situacao, qs_sugestoes_initial=None):
        sugestoes = qs_sugestoes_initial if qs_sugestoes_initial is not None else SugestaoMelhoria.objects.all()
        return sugestoes.filter(situacao=situacao)

    @staticmethod
    def sugestoes_por_papel_usuario(user_requisitante=None,
                                    user_interessado=None,
                                    user_demandante=None,
                                    user_responsavel=None,
                                    qs_sugestoes_initial=None):

        sugestoes = qs_sugestoes_initial if qs_sugestoes_initial is not None else SugestaoMelhoria.objects.all()

        algum_papel_informado = False

        if user_requisitante:
            sugestoes = sugestoes.filter(requisitante=user_requisitante)
            algum_papel_informado = True

        if user_interessado:
            sugestoes = sugestoes.filter(interessados=user_interessado)
            algum_papel_informado = True

        if user_demandante:
            sugestoes = sugestoes.filter(area_atuacao__demandantes=user_demandante) | \
                sugestoes.filter(area_atuacao__demandante_responsavel=user_demandante)
            algum_papel_informado = True

        if user_responsavel:
            sugestoes = sugestoes.filter(responsavel=user_responsavel)
            algum_papel_informado = True

        return sugestoes.distinct() if algum_papel_informado else qs_sugestoes_initial

    @staticmethod
    def sugestoes_ativas(qs_sugestoes_initial=None):
        sugestoes = qs_sugestoes_initial if qs_sugestoes_initial is not None else SugestaoMelhoria.objects.all()
        return sugestoes.filter(situacao__in=[
            SugestaoMelhoria.SITUACAO_PENDENTE,
            SugestaoMelhoria.SITUACAO_EM_ANALISE,
            SugestaoMelhoria.SITUACAO_SUSPENSA,
        ])

    @staticmethod
    def eh_usuario_ti(user):
        # TODO: Existe a função 'in_group' de 'djtools.templatetags.filters' que
        # TODO: poderia ter sido usada aqui. Porém, 'templatetags' está no escopo de
        # TODO: "consumidor do domínio", e não deve ser dependência do domínio.
        return user.groups.filter(name__in=[
            'Coordenador de TI sistêmico',
            'Analista',
            'Desenvolvedor',
        ]).exists()

    def is_responsavel_ou_demandante(self, user):
        return (
            self.is_responsavel(user)
            or user in self.area_atuacao.demandantes.all()
            or user == self.area_atuacao.demandante_responsavel
        )

    def is_responsavel(self, user):
        return user == self.responsavel

    def eh_requisitante(self, user):
        return user == self.requisitante

    def tem_responsavel(self):
        return bool(self.responsavel)

    def get_etapas(self):
        result = []
        if self.is_em_analise:
            result.append([SugestaoMelhoria.SITUACAO_DEFERIDA, 'Deferida'])
            result.append([SugestaoMelhoria.SITUACAO_INDEFERIDA, 'Indeferida'])
            result.append([SugestaoMelhoria.SITUACAO_SUSPENSA, 'Suspensa'])
            result.append([SugestaoMelhoria.SITUACAO_CANCELADA, 'Cancelada'])
        elif self.is_suspensa:
            result.append([SugestaoMelhoria.SITUACAO_EM_ANALISE, 'Em análise'])
        return result

    def is_situacao_ativa(self):
        return self.situacao in [SugestaoMelhoria.SITUACAO_EM_ANALISE, SugestaoMelhoria.SITUACAO_SUSPENSA, SugestaoMelhoria.SITUACAO_PENDENTE]

    @staticmethod
    def pode_adicionar_uma_sugestao(user):
        return user.has_perm('demandas.add_sugestaomelhoria')

    def pode_editar_todos_dados(self, user):
        """ todos os atributos """
        return self.demanda_gerada is None and self.is_responsavel_ou_demandante(user)

    def pode_editar_dados_basicos(self, user):
        """ atributos: título, descrição, interessados e tags """
        situacao = self.situacao in [SugestaoMelhoria.SITUACAO_PENDENTE]
        return self.pode_editar_todos_dados(user) or (
            situacao and user == self.requisitante
        )

    @staticmethod
    def pode_salvar_sugestao(user, sugestao):
        return SugestaoMelhoria.pode_adicionar_uma_sugestao(user) and (
            sugestao.pode_editar_dados_basicos(user)
            or sugestao.pode_editar_todos_dados(user)
        )

    def pode_visualizar(self, user):
        return user.has_perm('demandas.view_sugestaomelhoria')

    def pode_gerar_demanda(self, user):
        return (
            self.is_responsavel(user)
            and self.demanda_gerada is None
            and self.is_deferida
        )

    def gerar_demanda(self, user):
        try:
            if self.pode_gerar_demanda(user):
                nova_demanda = Demanda(
                    area=self.area_atuacao,
                    titulo=self.titulo,
                    descricao=self.descricao
                )
                nova_demanda.save()

                # TODO: Os demandantes para a demanda gerada não foram bem definidos na especificação da demanda.
                # TODO: Usando o responsável como demandante.
                demanda_demandantes = [self.responsavel]
                nova_demanda.demandantes.set(demanda_demandantes)

                demanda_interessados = [self.requisitante]
                demanda_interessados = demanda_interessados + [_ for _ in self.interessados.all()]
                nova_demanda.interessados.set(demanda_interessados)

                nova_demanda.tags.set([_ for _ in self.tags.all()])

                novo_historico = HistoricoSituacao()
                novo_historico.demanda = nova_demanda
                novo_historico.usuario = user
                novo_historico.situacao = nova_demanda.situacao
                novo_historico.data_previsao = None  # TODO: ?
                novo_historico.save()

                situacao_alterada = False

                if not self.is_deferida:
                    self.situacao = SugestaoMelhoria.SITUACAO_DEFERIDA
                    situacao_alterada = True

                self.demanda_gerada = nova_demanda
                self.save()

                if situacao_alterada:
                    Notificar.nova_situacao_em_sugestao_melhoria(self, user)

                # coloca a demanda em última prioridade dentro da sua área
                Demanda.colocar_demanda_em_ultima_prioridade(nova_demanda, user)

                # notifica a abertura da nova demanda
                Notificar.demanda_aberta(nova_demanda)
            else:
                raise Exception('O usuário "{}" não pode gerar a demanda para esta sugestão de melhoria.'.format(
                    user.get_vinculo()
                ))
        except Exception:
            raise Exception('Ocorreu um erro ao gerar a demanda para esta sugestão de melhoria.')

    def eh_demanda_gerada_em_andamento(self):
        return self.demanda_gerada is not None and not self.demanda_gerada.eh_situacao_terminal()

    def pode_visualizar_demanda_gerada(self, user):
        # TODO: Sobre os interessados na sugestão de melhoria e o seu amplo escopo de escolha,
        # TODO: é possível que um User selecionado não tenha permissão de visualizar
        # TODO: uma demanda. Por exemplo, um aluno não pode visualizar uma demanda,
        # TODO: mas pode ser selecionado em uma sugestão de melhoria, que por sua vez
        # TODO: pode gerar uma demanda no final.
        # TODO: Para resolver isso aqui neste contexto, a visualização da demanda gerada
        # TODO: ficará condicionada à permissão estática "demandas.view_demanda". Na prática,
        # TODO: o botão "Ver Demanda" não estará disponível para os demais usuários, mesmo que
        # TODO: estejam entre os interessados na sugestão de melhoria (a inconsistência silenciosa vai continuar).
        return user.has_perm('demandas.view_demanda')

    def pode_excluir_demanda_gerada(self, user):
        return (
            self.is_responsavel(user)
            and self.eh_demanda_gerada_em_andamento()
        )

    def pode_votar(self):
        return self.situacao not in [SugestaoMelhoria.SITUACAO_DEFERIDA, SugestaoMelhoria.SITUACAO_INDEFERIDA, SugestaoMelhoria.SITUACAO_CANCELADA]

    def pode_visualizar_comentario(self, user):
        return self.pode_visualizar(user)

    def pode_registrar_comentario(self, user):
        return self.pode_visualizar_comentario(user) and not (self.is_deferida or self.is_indeferida or self.is_cancelada)

    @property
    def is_em_analise(self):
        return self.situacao == SugestaoMelhoria.SITUACAO_EM_ANALISE

    @property
    def is_suspensa(self):
        return self.situacao == SugestaoMelhoria.SITUACAO_SUSPENSA

    @property
    def is_deferida(self):
        return self.situacao == SugestaoMelhoria.SITUACAO_DEFERIDA

    @property
    def is_indeferida(self):
        return self.situacao == SugestaoMelhoria.SITUACAO_INDEFERIDA

    @property
    def is_cancelada(self):
        return self.situacao == SugestaoMelhoria.SITUACAO_CANCELADA

    @property
    def qtd_votos(self):
        voto = SugestaoVoto.objects.filter(sugestao=self)
        return voto.filter(concorda=True).count() - voto.filter(concorda=False).count()

    @property
    def ja_concordou(self):
        usuario = tl.get_user()
        return SugestaoVoto.objects.filter(sugestao=self, usuario=usuario, concorda=True).exists()

    @property
    def ja_discordou(self):
        usuario = tl.get_user()
        return SugestaoVoto.objects.filter(sugestao=self, usuario=usuario, concorda=False).exists()

    def quem_concordou(self):
        return SugestaoVoto.objects.filter(sugestao=self, concorda=True)

    def quem_discordou(self):
        return SugestaoVoto.objects.filter(sugestao=self, concorda=False)


class SugestaoVoto(models.ModelPlus):
    sugestao = models.ForeignKeyPlus(SugestaoMelhoria, verbose_name='Sugestão de Melhoria', on_delete=models.CASCADE)
    usuario = models.CurrentUserField()
    concorda = models.BooleanField(null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        sugestao = self.sugestao
        sugestao.votos = sugestao.qtd_votos
        sugestao.save()


class AmbienteHomologacao(ModelPlus):
    criador = models.ForeignKeyPlus(AnalistaDesenvolvedor, verbose_name='Responsável', on_delete=models.CASCADE)
    branch = models.CharFieldPlus(verbose_name='Branch', default='master')
    banco = models.CharFieldPlus(verbose_name='Banco de Dados', default='suap_mascarado_pequeno')
    data_criacao = models.DateFieldPlus(verbose_name='Data de Criação')
    data_expiracao = models.DateFieldPlus(verbose_name='Data de Expiração')
    senha = models.CharFieldPlus(verbose_name='Senha', null=True, blank=False)
    pipeline = models.PositiveIntegerFieldPlus(verbose_name='Pipeline')
    url_gitlab = models.CharFieldPlus(verbose_name='Pipeline')
    ativo = models.BooleanField(verbose_name='Ativo', default=False)

    class Meta:
        verbose_name = 'Ambiente de Homologação'
        verbose_name_plural = 'Ambientes de Homologação'

    def __str__(self):
        return '{} [{}]'.format(self.branch, self.pipeline)

    def get_absolute_url(self):
        return '/demandas/ambientehomologacao/{}/'.format(self.pk)

    def save(self, *args, **kwargs):
        if self.pipeline is None:
            self.data_criacao = datetime.today()
            pipeline = ''
            try:
                pipeline = self.criar_pipeline()
                self.pipeline = pipeline['id']
                self.url_gitlab = pipeline['web_url']
            except KeyError:
                raise Exception(f'Não foi possível criar pipeline, por favor atualize a branch. Mensagem do pipeline: {pipeline}')
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        if self.senha:
            self.excluir_container()
        super().delete(*args, **kwargs)

    def criar_pipeline(self):
        variables = [
            {'key': 'CI_COMMIT_BRANCH', 'variable_type': 'env_var', 'value': self.branch},
            {'key': 'CI_COMMIT_AUTHOR', 'variable_type': 'env_var', 'value': self.criador.username_gitlab},
            {'key': 'DATABASE_TEMPLATE', 'variable_type': 'env_var', 'value': self.banco},
            {'key': 'NAME', 'variable_type': 'env_var', 'value': self.branch},
            {'key': 'PASSWORD', 'variable_type': 'env_var', 'value': self.senha},
        ]
        return gitlab.create_pipeline(variables, self.branch)

    def criar_atualizar_container(self):
        gitlab.execute_job(self.pipeline, 'deploy')
        self.ativo = True
        self.save()

    def excluir_container(self):
        gitlab.execute_job(self.pipeline, 'undeploy')
        self.ativo = False
        self.save()

    def destruir(self):
        gitlab.execute_job(self.pipeline, 'destroy')
        self.ativo = False
        self.save()

    def executar_comando(self, comando):
        return gitlab.job_log(self.pipeline, 'deploy')

    def get_status_container(self):
        log = gitlab.job_log(self.pipeline, 'deploy')
        status = 0, 'Aguardando criação'
        if 'SENHA:' in log:
            status = 100, 'Processo concluído com sucesso.'
        elif 'python manage.py sync' in log:
            status = 75, 'Executando o comando sync.'
        elif 'git pull origin' in log:
            status = 50, 'Sincronizando repositório.'
        elif 'createdb -U postgres' in log:
            status = 20, 'Criando banco de dados.'
        elif 'docker run' in log:
            status = 5, 'Criando container.'
        elif 'Job succeeded' in log:
            status = -1, 'Processo concluído com falha.'
        elif 'Job failed' in log:
            status = -1, 'Erro na execução do processo'
        return status

    def get_url_homologacao(self):
        return 'https://{}.{}'.format(self.branch, settings.GITLAB_CI_DOMAIN)
