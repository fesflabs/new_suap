import os.path
from datetime import timedelta, datetime
from typing import Iterable

from django.conf import settings
from django.contrib.auth.models import Group
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db import transaction
from django.db.models import Avg, Sum, Q
from django.apps import apps
from django.db.models.signals import m2m_changed, post_save, post_delete
from django.dispatch import receiver
from django_fsm import FSMIntegerField, transition
from model_utils import Choices

from centralservicos.utils import Notificar
from comum.models import User, Comentario
from djtools.db import models
from rh.models import UnidadeOrganizacional

STATUS_ATIVO = "ativo"
AVALIACAO_RUIM = 1
AVALIACAO_REGULAR = 2
AVALIACAO_BOM = 3
AVALIACAO_OTIMO = 4
AVALIACAO_EXCELENTE = 5

AVALIACAO_CHOICES = [[AVALIACAO_RUIM, '1'], [AVALIACAO_REGULAR, '2'], [AVALIACAO_BOM, '3'], [AVALIACAO_OTIMO, '4'], [AVALIACAO_EXCELENTE, '5']]


class Tag(models.ModelPlus):
    nome = models.CharFieldPlus('Nome', max_length=60, unique=True, help_text='Informe um nome para tag')
    area = models.ForeignKeyPlus('comum.AreaAtuacao', verbose_name='Área do Serviço')

    class Meta:
        ordering = ['nome']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.nome


class GestorAreaServico(models.ModelPlus):
    gestor = models.ForeignKeyPlus(
        User, related_name='gestorareaservico_set', verbose_name='Gestor', null=False, blank=False, help_text='Informe o nome do gestor desta área de serviço.'
    )
    area = models.ForeignKeyPlus('comum.AreaAtuacao', verbose_name='Área do Serviço')

    class Meta:
        unique_together = ('gestor', 'area')
        ordering = ['area']
        verbose_name = 'Gestor da Área do Serviço'
        verbose_name_plural = 'Gestores das Áreas dos Serviços'

    def __str__(self):
        return f'{self.gestor} - {self.area.nome}'

    @classmethod
    def minhas_areas(cls, user):
        """ Retorna uma lista de Areas que o usuário é gestor.
            Se o usuário for superuser, retorna todas as areas
        """
        from comum.models import AreaAtuacao

        if user.groups.filter(name='centralservicos Administrador').exists():
            return AreaAtuacao.objects.all()
        else:
            return AreaAtuacao.objects.filter(id__in=cls.objects.filter(gestor=user).values('area').distinct())


@receiver(post_save, sender=GestorAreaServico, dispatch_uid="adiciona_grupo_gestor_area_servico")
def adiciona_grupo_gestor_area_servico(sender, instance, **kwargs):
    group = Group.objects.get(name='Gestor da Central de Serviços')
    instance.gestor.groups.add(group)


@receiver(post_delete, sender=GestorAreaServico, dispatch_uid="remove_grupo_gestor_area_servico")
def remove_grupo_gestor_area_servico(sender, instance, **kwargs):
    group = Group.objects.get(name='Gestor da Central de Serviços')
    if not GestorAreaServico.objects.filter(gestor=instance.gestor).exists():
        instance.gestor.groups.remove(group)


class CentroAtendimento(models.ModelPlus):
    nome = models.CharFieldPlus('Nome', max_length=80, help_text='Informe um nome para o Centro de Atendimento')
    eh_local = models.BooleanField('Centro de Atendimento Local?', default=False)
    area = models.ForeignKeyPlus('comum.AreaAtuacao', verbose_name='Área do Serviço')

    class Meta:
        unique_together = ('nome', 'area')
        ordering = ['nome']
        verbose_name = 'Centro de Atendimento'
        verbose_name_plural = 'Centros de Atendimento'

    def __str__(self):
        return self.nome


class CategoriaServico(models.ModelPlus):
    nome = models.CharFieldPlus('Nome', max_length=80, unique=True, help_text='Informe um nome para a categoria de serviço')
    area = models.ForeignKeyPlus('comum.AreaAtuacao', verbose_name='Área do Serviço')

    class Meta:
        ordering = ['nome']
        verbose_name = 'Categoria de Serviço'
        verbose_name_plural = 'Categorias de Serviço'

    def __str__(self):
        return self.nome

    def get_grupos_servicos_com_base_conhecimento(self):
        """ Retorna os grupos de servicos ativos que possuem base de conhecimento vinculada """
        return self.gruposervico_set.filter(
            pk__in=BaseConhecimento.objects.filter(ativo=True, servicos__grupo_servico__categorias=self).values('servicos__grupo_servico')
        ).distinct()

    def get_grupos_servicos_com_base_conhecimento_faq(self):
        """ Retorna os grupos de servicos ativos que possuem base de conhecimento vinculada do tipo FAQ """
        return self.gruposervico_set.filter(
            pk__in=BaseConhecimento.objects.filter(visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA, servicos__grupo_servico__categorias=self, servicos__interno=False)
            .exclude(servicos__interno=True)
            .values('servicos__grupo_servico')
        ).distinct()


class GrupoServico(models.ModelPlus):
    nome = models.CharFieldPlus('Nome', max_length=80, unique=True, help_text='Informe um nome para o grupo de serviço')
    detalhamento = models.CharFieldPlus('Descrição', max_length=600, help_text='Informe detalhes do grupo de serviço')
    categorias = models.ManyToManyFieldPlus(CategoriaServico)
    icone = models.CharFieldPlus(
        'Ícone', max_length=80, blank=True, default='list', help_text='Informe um ícone para representar este grupo de Serviços. Fonte: https://fontawesome.com/v4.7.0/icons/'
    )

    class Meta:
        ordering = ['nome']
        verbose_name = 'Grupo de Serviço'
        verbose_name_plural = 'Grupos de Serviço'

    def __str__(self):
        return self.nome

    def get_servicos_ativos_com_base_conhecimento_faq(self):
        """ Retorna os servicos ativos que possuem base de conhecimento vinculada do tipo FAQ """
        return Servico.objects.filter(
            ativo=True,
            id__in=BaseConhecimento.objects.filter(visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA, servicos__grupo_servico=self, servicos__interno=False).values('servicos'),
        ).distinct()

    def get_bases_conhecimento_faq(self):
        """ Retorna as bases de conhecimento do tipo FAQ """
        return (
            BaseConhecimento.objects.filter(ativo=True).filter(visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA, servicos__grupo_servico=self, servicos__interno=False).distinct()
        )

    def get_bases_conhecimento(self):
        """ Retorna as bases de conhecimento ativas """
        return BaseConhecimento.objects.filter(ativo=True).filter(servicos__grupo_servico=self).distinct()


class Servico(models.ModelPlus):
    SEARCH_FIELDS = ['nome', 'texto_ajuda']

    TIPO_REQUISICAO = 'REQ'
    TIPO_INCIDENTE = 'INC'

    TIPO_CHOICES = [[TIPO_REQUISICAO, 'Requisição'], [TIPO_INCIDENTE, 'Incidente']]

    nome = models.CharFieldPlus('Nome', width=450, max_length=120, unique=True)
    tipo = models.CharFieldPlus('Tipo', max_length=3, choices=TIPO_CHOICES, null=False)
    area = models.ForeignKey('comum.AreaAtuacao', verbose_name='Área do Serviço', on_delete=models.CASCADE)
    centros_atendimento = models.ManyToManyFieldPlus(
        CentroAtendimento,
        verbose_name='Centros de Atendimento',
        related_name='servicos_centros_atendimento_set',
        help_text='Informe pelo menos um centro de atendimento responsável pelo atendimento do chamado.',
    )
    grupo_servico = models.ForeignKeyPlus(GrupoServico, verbose_name='Grupo de Serviço', null=False, on_delete=models.CASCADE)
    texto_ajuda = models.TextField('Informações Adicionais', null=True, blank=True)
    texto_modelo = models.TextField('Informações para preenchimento do chamado', null=True, blank=True)
    permite_anexos = models.BooleanField('Permite anexos?', default=False)
    requer_numero_patrimonio = models.BooleanField('Requer número do patrimônio?', default=False)
    permite_abertura_terceiros = models.BooleanField('Permite abertura de chamado por terceiros?', default=False)
    permite_telefone_adicional = models.BooleanField('Permite interessado informar Telefone Adicional?', default=False)
    sla_em_horas = models.PositiveIntegerField('SLA (em horas)', default=1)
    ativo = models.BooleanField('Ativo?', default=True)
    publico_direcionado = models.ManyToManyFieldPlus(
        'comum.Publico',
        verbose_name='Público',
        blank=True,
        related_name='servicos_publico_direcionado_set',
        help_text='Caso deseje restringir este serviço a apenas alguns tipos de usuário, selecione um ou mais.',
    )
    interno = models.BooleanField('Interno?', default=False, help_text='Serviços internos estarão disponíveis apenas para Atendentes da Central de Serviço.')

    class Meta:
        ordering = ['grupo_servico', 'tipo', 'nome']
        verbose_name = 'Serviço'
        verbose_name_plural = 'Serviços'

    def __str__(self):
        return f'{self.grupo_servico.nome} | {self.nome}'

    def pode_acessar_servico(self, usuario):
        """ Verifica se o usuario logado tem acesso ao servico """
        if not self.publico_direcionado.exists():
            return True
        else:
            tipo_usuario = usuario.get_relacionamento()
            modelo_usuario = type(usuario.get_relacionamento()).__name__
            for publico in self.publico_direcionado.all():
                if publico.modelo_base == modelo_usuario and publico.get_queryset().filter(pk=tipo_usuario.pk).exists():
                    return True
        return False

    @classmethod
    def get_content_types_disponiveis(cls):
        """ Retorna os seguintes tipos: Servidor, Aluno e PrestadorServico """
        return ContentType.objects.filter(app_label__in=['comum', 'edu', 'rh']).filter(model__in=['servidor', 'prestadorservico', 'aluno'])

    def get_quantidade_chamados(self):
        return Chamado.objects.filter(servico=self).count()

    def get_quantidade_chamados_abertos(self):
        return Chamado.objects.filter(servico=self).exclude(status__in=[StatusChamado.RESOLVIDO, StatusChamado.FECHADO, StatusChamado.CANCELADO]).count()

    def get_centros_atendimento(self, campus_id):
        return self.centros_atendimento.filter(models.Q(eh_local=False) | models.Q(eh_local=True, grupoatendimento__campus_id=campus_id)).order_by('-eh_local', 'nome').distinct()

    def get_campus_disponiveis_para_atendimento(self):
        """ Retorna uma lista de Campus (UO) que estejam disponíveis (possuam Grupos de Atendimento) para o servico """
        ids = GrupoAtendimento.objects.filter(centro_atendimento__in=self.centros_atendimento.all()).values_list('campus', flat=True)
        return UnidadeOrganizacional.objects.suap().filter(id__in=ids).order_by('sigla')

    def get_bases_de_conhecimento_disponiveis(self, grupo_atendimento):
        return (
            BaseConhecimento.objects.filter(area=self.area, ativo=True)
            .filter(models.Q(grupos_atendimento__isnull=True) | models.Q(grupos_atendimento__in=[grupo_atendimento]))
            .filter(models.Q(servicos__isnull=True) | models.Q(servicos__in=[self]))
        )

    def get_bases_de_conhecimento_disponiveis_para_resolucao(self, grupo_atendimento):
        return (
            BaseConhecimento.objects.filter(area=self.area, ativo=True, necessita_correcao=False, supervisao_pendente=False)
            .filter(models.Q(grupos_atendimento__isnull=True) | models.Q(grupos_atendimento__in=[grupo_atendimento]))
            .filter(models.Q(servicos__isnull=True) | models.Q(servicos__in=[self]))
        )

    def get_bases_conhecimento_faq(self):
        return (
            BaseConhecimento.objects.filter(ativo=True)
            .filter(
                models.Q(servicos__isnull=True, area=self.area, visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA)
                | models.Q(servicos__in=[self], visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA)
            )
            .distinct()
        )

    def tem_bases_conhecimento_publicas(self):
        return (
            BaseConhecimento.objects.filter(ativo=True)
            .filter(
                models.Q(servicos__isnull=True, area=self.area, visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA)
                | models.Q(servicos__in=[self], visibilidade=BaseConhecimento.VISIBILIDADE_PUBLICA)
            )
            .exists()
        )

    def get_unico_centro_atendimento(self):
        if self.centros_atendimento.count() == 1:
            return self.centros_atendimento.first()

    def get_ext_combo_template(self):
        if self.texto_ajuda:
            ajuda = f'<p class="disabled">{str(self.texto_ajuda)}</p>'
        else:
            ajuda = ''
        template = '''
                <h3>{}</h3>
                <p>Grupo: {}</p>
                {}
                    '''.format(
            self.nome, self.grupo_servico.nome, ajuda
        )
        return template


class GrupoAtendimento(models.ModelPlus):
    grupo_atendimento_superior = models.ForeignKeyPlus(
        'centralservicos.GrupoAtendimento', verbose_name='Grupo de Atendimento Superior', null=True, blank=True, on_delete=models.CASCADE
    )
    campus = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Campus')
    centro_atendimento = models.ForeignKeyPlus(CentroAtendimento, verbose_name='Centro de Atendimento', null=False, blank=False)
    nome = models.CharFieldPlus('Nome', max_length=120)
    responsaveis = models.ManyToManyFieldPlus(
        User, verbose_name='Responsáveis', related_name='responsaveis_set', help_text='O responsável pelo grupo de atendimento deve ser um dos atendentes.'
    )
    atendentes = models.ManyToManyFieldPlus(User, related_name='atendentes_set', blank=True, verbose_name='Atendentes Vinculados ao Grupo')

    class Meta:
        ordering = ['nome']
        verbose_name = 'Grupo de Atendimento'
        verbose_name_plural = 'Grupos de Atendimento'

    def __str__(self):
        return f'{self.nome} ({self.centro_atendimento})'

    def clean(self):
        # Não pode existir mais de um grupo de atendimento, no mesmo nível, na mesma UO,
        # no mesmo centro de atendimento
        if not hasattr(self, 'centro_atendimento'):
            raise ValidationError('Nenhum centro de atendimento encontrado.')
        if not hasattr(self, 'campus'):
            raise ValidationError('Nenhum campus encontrado.')
        if (
            GrupoAtendimento.objects.filter(grupo_atendimento_superior=self.grupo_atendimento_superior, campus=self.campus, centro_atendimento=self.centro_atendimento)
            .exclude(pk=self.id)
            .exists()
        ):
            raise ValidationError('Não pode existir mais de um grupo de atendimento, no mesmo nível, ' 'na mesma UO, no mesmo centro de atendimento.')

    @classmethod
    def get_grupo_primeiro_nivel(cls, uo, centro):
        """ Retorna o grupo de primeiro nível
            Para isto, verifica se o centro de atendimento eh_local = True
            Em caso positivo, retorna o grupo de primeiro nivel do campus informado,
            em caso negativo, retorna o grupo de primeiro nivel sem considerar o campus
                (considerando apenas o centro de atendimento)
        """
        if centro.eh_local:
            lista = GrupoAtendimento.objects.filter(grupoatendimento__isnull=True, campus=uo, centro_atendimento=centro)
        else:
            grupos = GrupoAtendimento.objects.filter(centro_atendimento=centro, grupo_atendimento_superior__isnull=False)
            gs_keys = grupos.values_list('grupo_atendimento_superior__id', flat=True)
            lista = GrupoAtendimento.objects.filter(centro_atendimento=centro).exclude(pk__in=gs_keys)

        if lista:
            return lista[0]
        else:
            return None

    def email_responsaveis(self):
        """ Retorna a lista de emails separada por virgula dos responsáveis """
        return self.responsaveis.exclude(email='').values_list('email', flat=True)

    def pode_editar(self, user):
        if user.has_perm('comum.is_gestor_da_central_de_servicos') or user in self.responsaveis.all():
            return True
        return False

    def get_vinculos_responsaveis(self):
        responsaveis = []
        if self.responsaveis.exists():
            for responsavel in self.responsaveis.all():
                responsaveis.append(responsavel.get_vinculo())
        return responsaveis

    def pertence_ao_grupo(self, user):
        return GrupoAtendimento.meus_grupos(user).filter(id=self.id).exists()

    def eh_primeiro_nivel(self):
        """ Informa se o grupo é de primeiro nível """
        grupo = GrupoAtendimento.get_grupo_primeiro_nivel(self.campus, self.centro_atendimento)
        if grupo and grupo.id == self.pk:
            return True
        else:
            return False

    def get_grupo_antendimento_inferior(self, chamado):
        """ Retorna o grupo de atendimento inferior. Se tiver mais de um,
            irá verificar com base no chamado (quem escalou).
        """
        grupo = None
        nivel_anterior = GrupoAtendimento.objects.filter(grupo_atendimento_superior=self)
        if nivel_anterior.count() == 1:  # Se só existe um grupo de atendimento no nivel inferior, atribui ele
            grupo = nivel_anterior[0]
        elif nivel_anterior.count() > 1:  # Se existe mais de um, obtem o ultimo (inferior) que foi atribuido
            atendimento_atribuicoes = chamado.atendimentoatribuicao_set.filter(grupo_atendimento__in=nivel_anterior).order_by('-atribuido_em')
            if atendimento_atribuicoes.count() >= 1:
                grupo = atendimento_atribuicoes[0].grupo_atendimento
        return grupo

    @classmethod
    def meus_grupos(cls, user, area=None):
        """ Retorna uma lista de Grupos que o Usuário é Atendente ou Responsável
            Se informar a área, executa o filtro por area
        """
        qs = cls.objects.filter(models.Q(atendentes=user) | models.Q(responsaveis=user)).distinct()

        if area:
            filter_area = Q(centro_atendimento__area__in=area) if isinstance(area, Iterable) else Q(centro_atendimento__area=area)
            qs = qs.filter(filter_area)

        return qs

    @classmethod
    def meus_grupos_com_servicos_ou_chamados_ativos(cls, user, area=None):
        """ Retorna uma lista de Grupos que o Usuário é Atendente ou Responsável
            Se informar a área, executa o filtro por area
        """
        qs = cls.meus_grupos(user, area).filter(models.Q(centro_atendimento__servicos_centros_atendimento_set__ativo=True) | models.Q(id__in=AtendimentoAtribuicao.objects.filter(chamado_id__in=Chamado.ativos.all().values_list('id', flat=True)).values_list('grupo_atendimento_id', flat=True)))

        return qs

    @classmethod
    def areas_vinculadas_ao_meu_centro_atendimento(cls, user):
        from comum.models import AreaAtuacao

        if user.is_superuser or user.groups.filter(name='centralservicos Administrador').exists():
            return AreaAtuacao.objects.all()
        else:
            return AreaAtuacao.objects.filter(id__in=cls.meus_grupos(user).values('centro_atendimento__area'))

    @classmethod
    def get_grupos_por_responsavel(cls, user):
        """ Retorna uma lista de Grupos que o Usuário é Responsável
            Se o usuário for superuser, retorna todos os grupos
        """
        if user.is_superuser:
            return cls.objects.all()
        else:
            return cls.objects.filter(models.Q(responsaveis=user))

    @classmethod
    def raiz(cls):
        try:
            return cls.objects.get(grupo_atendimento_superior__isnull=True)
        except cls.MultipleObjectsReturned:
            raise Exception('Existe mais de um Grupo de Atendimento raiz.')
        except cls.DoesNotExist:
            return None


def altera_permissao_apos_salvar_atendentes(sender, **kwargs):
    group = Group.objects.get(name='Atendente da Central de Serviços')
    """ Para todos os atendentes vinculados ao GrupoAtendimento, que não possuam a permissão """
    atendentes_sem_permissao = User.objects.filter(atendentes_set__isnull=False).exclude(groups=group)
    for user in atendentes_sem_permissao:
        user.groups.add(group)
    """ Para todos os usuários que tem permissão, mas não são atendentes """
    nao_atendentes_com_permissao = User.objects.filter(atendentes_set__isnull=True, groups=group)
    for user in nao_atendentes_com_permissao:
        user.groups.remove(group)


m2m_changed.connect(altera_permissao_apos_salvar_atendentes, sender=GrupoAtendimento.atendentes.through)


class BaseConhecimento(models.ModelPlus):
    SEARCH_FIELDS = ['titulo', 'resumo', 'solucao', 'servicos__nome']

    NAO = False
    SIM = True
    SIM_NAO_CHOICES = ((NAO, 'Não'), (SIM, 'Sim'))

    VISIBILIDADE_PUBLICA = 'publica'
    VISIBILIDADE_PRIVADA = 'privada'
    VISIBILIDADE_SIGILOSA = 'sigilosa'

    VISIBILIDADE_CHOICES_TODAS = ((VISIBILIDADE_PUBLICA, 'Pública'), (VISIBILIDADE_PRIVADA, 'Privada'), (VISIBILIDADE_SIGILOSA, 'Sigilosa'))

    VISIBILIDADE_CHOICES_PRIVADA_OU_SIGILOSA = ((VISIBILIDADE_PRIVADA, 'Privada'), (VISIBILIDADE_SIGILOSA, 'Sigilosa'))

    titulo = models.CharFieldPlus('Título', max_length=120, null=False, blank=False)
    resumo = models.TextField('Resumo', null=False, blank=False)
    solucao = models.TextField('Solução', null=True, blank=True)
    tags = models.CharFieldPlus(
        'Tags', max_length=80, help_text='Separe cada tag com uma vírgula e espaço. Ex.: Ensino, Tecnologia da Informação, Extensão, Internet', null=True, blank=True
    )
    atualizado_em = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    grupos_atendimento = models.ManyToManyFieldPlus(
        GrupoAtendimento,
        blank=True,
        verbose_name='Restringir aos Grupos de Atendimento',
        help_text='Não selecione nenhuma opção para exibir esta base de conhecimento em todos os ' 'grupos de atendimento.',
    )
    servicos = models.ManyToManyFieldPlus(
        Servico,
        blank=True,
        verbose_name='Restringir aos Serviços',
        help_text='Não selecione nenhuma opção para exibir esta base de conhecimento em todos os serviços.',
        related_name='base_conhecimento_servicos_set',
    )
    area = models.ForeignKeyPlus('comum.AreaAtuacao', verbose_name='Área do Serviço')
    necessita_correcao = models.BooleanField(
        'Necessita correção?',
        null=True,
        blank=True,
        default=NAO,
        choices=SIM_NAO_CHOICES,
        help_text='Marque esta opção caso esta base de conhecimento necessite de alguma correção.',
    )
    supervisao_pendente = models.BooleanField(
        'Supervisão pendente?',
        null=True,
        blank=True,
        default=False,
        choices=SIM_NAO_CHOICES,
        help_text='Marque esta opção caso esta base de conhecimento necessite de aprovação por algum supervisor.',
    )
    atualizado_por = models.ForeignKeyPlus(User, related_name='atualizado_por_set', verbose_name='Atualizado Por', null=True)
    visibilidade = models.CharFieldPlus(
        max_length=10,
        default=VISIBILIDADE_PRIVADA,
        choices=VISIBILIDADE_CHOICES_TODAS,
        null=True,
        help_text='<strong>Sigilosa:</strong> restringe os artigos apenas a determinados Grupos de Atendimento;<br /><strong>Privada:</strong> artigos visíveis a todos os atendentes da Central de Serviços;<br /> <strong>Pública:</strong> artigos visíveis a todos os atendentes da Central de Serviços e na área de Perguntas Frequentes.',
    )
    ativo = models.BooleanField('Ativo?', default=True)

    class Meta:
        ordering = ['titulo']
        verbose_name = 'Base de Conhecimento'
        verbose_name_plural = 'Bases de Conhecimento'
        permissions = (
            ('add_active_baseconhecimento', 'Pode adicionar uma base de conhecimento sem necessitar supervisão'),
            ('add_public_baseconhecimento', 'Pode adicionar uma base de conhecimento pública'),
            ('review_baseconhecimento', 'Pode revisar bases de conhecimento'),
            ('pode_unificar_baseconhecimento', 'Pode unificar bases de conhecimento'),
        )

    def __str__(self):
        return self.titulo

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_absolute_url(self):
        return f'/centralservicos/baseconhecimento/{self.id}/'

    def get_tags(self):
        tags = list()
        if self.tags:
            tags = self.tags.split(", ")
        return tags

    def get_visualizar_base_conhecimento_url(self):
        return f'{settings.SITE_URL}{self.get_absolute_url()}'

    def get_ext_combo_template(self):
        resumo = ''
        tags = ''
        if self.tags:
            tags = f'<p>Tags: {str(self.tags)}</p>'
        if self.resumo:
            resumo = f'<p class="disabled">{str(self.resumo)}</p>'

        return f'''<h3>{self.titulo}</h3> {tags} {resumo}'''

    def save(self, *args, **kwargs):
        """
        Ao incluir/alterar base de conhecimento, atualiza o campo 'atualizado_em' e 'atualizado_por', caso tenha alterado os camos resumo ou solução.
        """

        if self.atualizado_por and not self.atualizado_por.has_perm('centralservicos.add_active_baseconhecimento'):
            self.supervisao_pendente = True
        retorno = super().save(*args, **kwargs)
        self.__original_resumo = self.resumo
        self.__original_solucao = self.solucao
        if self.supervisao_pendente:
            """ Enviar email apenas a atendentes/responsaveis da area que sejam do grupo Supervisor """
            group = Group.objects.get(name='Supervisor da Base de Conhecimento')
            usuarios = list()
            supervisores = group.user_set.all()
            for supervisor in supervisores:
                usuarios.append(supervisor)

            atendentes = User.objects.filter(atendentes_set__grupoatendimento__centro_atendimento__area=self.area)
            for atendente in atendentes:
                usuarios.append(atendente)

            Notificar.supervisao_pendente_em_base_conhecimento(self, usuarios)
        return retorno

    def estah_disponivel_para_uso(self):
        return not self.necessita_correcao and not self.supervisao_pendente

    def get_media_avaliacoes(self):
        return (
            AvaliaBaseConhecimento.objects.filter(base_conhecimento=self, pergunta__ativo=True, pergunta__area=self.area, data__gte=self.atualizado_em).aggregate(Avg('nota'))[
                'nota__avg'
            ]
            or 0.0
        )

    @property
    def get_quantidade_utilizacoes(self):
        return HistoricoStatus.objects.filter(status=StatusChamado.get_status_resolvido(), bases_conhecimento__in=[self]).distinct().count()

    @property
    def get_quantidade_avaliacoes(self):
        return AvaliaBaseConhecimento.objects.filter(base_conhecimento=self, pergunta__ativo=True, pergunta__area=self.area, data__gte=self.atualizado_em).count()

    @transaction.atomic()
    def marcar_para_correcao(self, texto, user):
        baseconhecimento_content = ContentType.objects.get(app_label='centralservicos', model='baseconhecimento')
        comentario = Comentario()
        comentario.cadastrado_por = user
        comentario.texto = texto
        comentario.content_type = baseconhecimento_content
        comentario.content_object = self
        comentario.object_id = self.pk
        comentario.save()

        BaseConhecimento.objects.filter(id=self.pk).update(necessita_correcao=True)
        if self.atualizado_por:
            Notificar.base_conhecimento_marcada_para_revisao(self, comentario, user)


class BaseConhecimentoAnexo(models.ModelPlus):
    base_conhecimento = models.ForeignKeyPlus(BaseConhecimento, verbose_name='Base de Conhecimento', null=False, blank=False)
    anexo = models.FileFieldPlus(
        upload_to='upload/baseconhecimento/anexos/',
        validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'xls', 'csv', 'docx', 'doc', 'pdf', 'jpg', 'jpeg', 'png', 'zip', 'txt'])],
        null=False,
        blank=False,
        max_file_size=10485760,
    )

    def nome_arquivo(self):
        return os.path.basename(self.anexo.name)

    def __str__(self):
        return self.base_conhecimento.titulo

    class Meta:
        ordering = ['anexo']
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'


class PerguntaAvaliacaoBaseConhecimento(models.ModelPlus):
    area = models.ForeignKeyPlus('comum.AreaAtuacao', verbose_name='Área do Serviço')
    titulo = models.CharFieldPlus('Título', max_length=120, help_text='A resposta à pergunta será uma escala de 1 a 5.')
    ativo = models.BooleanField('Ativo?', default=False)

    class Meta:
        ordering = ['area', 'titulo']
        verbose_name = 'Pergunta da Avaliação da Base de Conhecimento'
        verbose_name_plural = 'Perguntas da Avaliação da Base de Conhecimento'

    def __str__(self):
        return f'{self.titulo} ({self.area.nome})'


class AvaliaBaseConhecimento(models.ModelPlus):
    base_conhecimento = models.ForeignKeyPlus(BaseConhecimento, verbose_name='Base de Conhecimento')
    pergunta = models.ForeignKeyPlus(PerguntaAvaliacaoBaseConhecimento, verbose_name='Pergunta', null=True)
    nota = models.PositiveSmallIntegerField('Nota da Avaliação', choices=AVALIACAO_CHOICES)
    data = models.DateTimeField(verbose_name='Data da Avaliação', auto_now=True)
    avaliado_por = models.ForeignKeyPlus(User, related_name='avaliado_por_set', verbose_name='Avaliado Por')

    class Meta:
        unique_together = ('base_conhecimento', 'pergunta', 'avaliado_por')
        ordering = ['base_conhecimento']
        verbose_name = 'Avaliação da Base de Conhecimento'
        verbose_name_plural = 'Avaliações das Bases de Conhecimento'

    def __str__(self):
        return self.base_conhecimento.titulo

    @classmethod
    def get_media_avaliacao(cls, base_conhecimento, pergunta):
        return cls.objects.filter(base_conhecimento=base_conhecimento, pergunta=pergunta).aggregate(Avg('nota'))['nota__avg']


class StatusChamado:
    ABERTO = 1
    EM_ATENDIMENTO = 2
    RESOLVIDO = 3
    FECHADO = 4
    REABERTO = 5
    SUSPENSO = 6
    CANCELADO = 7

    STATUS = Choices(
        (ABERTO, 'aberto', 'Aberto'),
        (EM_ATENDIMENTO, 'atendimento', 'Em atendimento'),
        (RESOLVIDO, 'resolvido', 'Resolvido'),
        (FECHADO, 'fechado', 'Fechado'),
        (REABERTO, 'reaberto', 'Reaberto'),
        (SUSPENSO, 'suspenso', 'Suspenso'),
        (CANCELADO, 'cancelado', 'Cancelado'),
    )

    @classmethod
    def get_action_from_status(cls, argument):
        status_name = StatusChamado.STATUS[argument]
        switcher = {"Aberto": "abrir", "Resolvido": "resolver", "Fechado": "fechar", "Suspenso": "suspender", "Cancelado": "cancelar", "Reaberto": "Reaberto"}
        # Get the correct state from switcher dictionary
        return switcher.get(status_name, status_name)

    @classmethod
    def get_status_aberto(cls):
        return StatusChamado.ABERTO

    @classmethod
    def get_status_em_atendimento(cls):
        return StatusChamado.EM_ATENDIMENTO

    @classmethod
    def get_status_resolvido(cls):
        return StatusChamado.RESOLVIDO

    @classmethod
    def get_status_fechado(cls):
        return StatusChamado.FECHADO

    @classmethod
    def get_status_reaberto(cls):
        return StatusChamado.REABERTO

    @classmethod
    def get_status_suspenso(cls):
        return StatusChamado.SUSPENSO

    @classmethod
    def get_status_cancelado(cls):
        return StatusChamado.CANCELADO


class ChamadosAtivosManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .exclude(status__in=(StatusChamado.get_status_fechado(), StatusChamado.get_status_resolvido(), StatusChamado.get_status_cancelado()))
        )


class ChamadosSLAEstouradoManager(models.Manager):
    def get_queryset(self):
        return (
            super()
            .get_queryset()
            .filter(data_limite_atendimento__lt=datetime.now())
            .exclude(status__in=(StatusChamado.get_status_fechado(), StatusChamado.get_status_resolvido(), StatusChamado.get_status_cancelado()))
        )


class Chamado(models.ModelPlus):
    MEIO_ABERTURA_TELEFONE = 'telefone'
    MEIO_ABERTURA_EMAIL = 'email'
    MEIO_ABERTURA_PESSOALMENTE = 'pessoalmente'
    MEIO_ABERTURA_WEB = 'web'

    MEIO_ABERTURA_CHOICES = (
        (MEIO_ABERTURA_WEB, 'Interface Web'),
        (MEIO_ABERTURA_TELEFONE, 'Telefone'),
        (MEIO_ABERTURA_EMAIL, 'Email'),
        (MEIO_ABERTURA_PESSOALMENTE, 'Pessoalmente'),
    )

    status = FSMIntegerField(default=StatusChamado.STATUS.aberto, choices=StatusChamado.STATUS, protected=True)
    servico = models.ForeignKeyPlus(Servico, verbose_name='Serviço', null=False, blank=False)
    descricao = models.TextField('Descrição', null=False, blank=False, help_text='Descreva a sua solicitação')
    aberto_em = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    aberto_por = models.ForeignKeyPlus(User, related_name='aberto_por_set', verbose_name='Aberto Por', null=False, blank=False)
    requisitante = models.ForeignKeyPlus(
        User, related_name='requisitante_set', verbose_name='Requisitante', null=False, blank=False, help_text='Informe o nome de quem está requisitando a abertura do chamado.'
    )
    telefone_adicional = models.BrTelefoneField(
        'Telefone Adicional para Contato', blank=True, max_length=15, help_text='Para agilizar o atendimento, informe um número adicional para contato.'
    )
    interessado = models.ForeignKeyPlus(
        User,
        related_name='interessado_set',
        verbose_name='Interessado',
        null=False,
        blank=False,
        help_text='Caso esteja abrindo o chamado para outra pessoa, informe o nome do interessado.',
    )
    uo_interessado = models.ForeignKeyPlus(UnidadeOrganizacional, related_name='uo_interessado_set', verbose_name='Unidade Organizacional do Interessado', null=True)
    meio_abertura = models.CharFieldPlus('Meio de Abertura', max_length=20, choices=MEIO_ABERTURA_CHOICES, null=False, blank=False)
    numero_patrimonio = models.CharFieldPlus('Número do Patrimônio', max_length=20, null=True, blank=True)
    autorizado = models.BooleanField('Autorizado?', null=True, blank=True)
    data_limite_atendimento = models.DateTimeField('Data Limite para atendimento do chamado', null=False, blank=False)
    notificacao_enviada = models.BooleanField('Notificação Enviada?', default=False)
    nota_avaliacao = models.PositiveSmallIntegerField('Nota da Avaliação', choices=AVALIACAO_CHOICES, null=True, blank=True)
    comentario_avaliacao = models.TextField('Comentário da Avaliação', null=False, blank=True)
    data_avaliacao = models.DateTimeField(verbose_name='Data da Avaliação', null=True)
    reclassificado = models.PositiveSmallIntegerField('Chamado Reclassificado', null=True, help_text='Número de vezes que o chamado foi reclassificado.')
    outros_interessados = models.ManyToManyFieldPlus(
        User,
        related_name='outros_interessados_set',
        verbose_name='Outros Interessados',
        help_text='Vincule neste chamado outros usuários que desejem acompanhar alterações e' ' comentários deste chamado.',
    )
    fechado_automaticamente = models.BooleanField('Fechado Automaticamente?', null=True, blank=True)
    tags = models.ManyToManyFieldPlus(Tag, related_name='tags_set', verbose_name='Tags', help_text='Vincule tags neste chamados para facilitar a identificação do mesmo.')
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus', null=True)

    objects = models.Manager()
    ativos = ChamadosAtivosManager()
    com_sla_estourado = ChamadosSLAEstouradoManager()

    def __str__(self):
        return f'{self.pk}: {self.servico.nome}'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.centro_atendimento = None

    class Meta:
        ordering = ['-aberto_em']
        verbose_name = 'Chamado'
        verbose_name_plural = 'Chamados'
        permissions = (
            # Permissões relativas a atribuição de chamado
            ('add_atendimentoatribuicao', 'Pode atribuir um chamado'),
            ('add_auto_atribuicao', 'Pode assumir um chamado'),
            ('change_atendimentoatribuicao', 'Pode alterar atribuição de um chamado'),
            ('reclassify_chamado', 'Pode reclassificar um chamado'),
            # Permissões que alterar o status do chamado
            ('solve_chamado', 'Pode resolver um chamado'),
            ('close_chamado', 'Pode fechar um chamado'),
            ('reopen_chamado', 'Pode reabrir um chamado'),
            ('suspend_chamado', 'Pode suspender um chamado'),
            ('cancel_chamado', 'Pode cancelar um chamado'),
            # Permissões para anexos
            ('add_attachement', 'Pode adicionar anexo'),
            ('add_comment', 'Pode adicionar comentário'),
            ('add_internal_note', 'Pode adicionar nota interna'),
            ('add_interested', 'Pode adicionar interessado'),
            ('remove_interested', 'Pode remover interessado'),
            ('list_chamados_usuario', 'Pode listar chamados do usuário'),
            ('list_chamados_suporte', 'Pode listar chamados do suporte'),
            ('pode_ver_indicadores', 'Pode ver indicadores'),
        )

    def get_absolute_url(self):
        return f'/centralservicos/chamado/{self.id}/'

    def save(self, *args, **kwargs):
        """
        Ao criar um Chamado, cria automaticamente um Chamado Atendimento e um HistoricoStatus
        O detalhe é que o save só é chamado quando está sendo criado um chamado
        """
        insert = not self.pk
        # self.data_limite_atendimento = self.aberto_em + timedelta(hours=self.servico.sla_em_horas)
        self.data_limite_atendimento = self.calcula_data_limite_sem_feriados_fds()
        retorno = super().save(*args, **kwargs)
        if insert:
            atribuicao = AtendimentoAtribuicao()
            atribuicao.chamado = self
            if not self.centro_atendimento:
                raise ValidationError('É necessário informar um centro de atendimento ao abrir o chamado.')

            grupo = GrupoAtendimento.get_grupo_primeiro_nivel(self.campus, self.centro_atendimento)
            if not grupo:
                raise ValidationError(
                    'Nenhum grupo de atendimento foi cadastrado para a UO ({}) '
                    'do servidor Interessado, no centro de atendimento ({}).'.format(self.campus, self.centro_atendimento)
                )

            atribuicao.grupo_atendimento = grupo
            atribuicao.atribuido_em = datetime.today()
            atribuicao.save()

            historico_status = HistoricoStatus()
            historico_status.chamado = self
            historico_status.usuario = self.aberto_por
            historico_status.data_hora = self.aberto_em
            historico_status.status = self.status
            historico_status.save()
        return retorno

    def tem_tags_disponiveis(self, areas):
        return Tag.objects.exclude(id__in=self.tags.all()).filter(area__in=areas).exists()

    def criar_comunicacao(self, usuario, data_hora, observacao):
        if observacao:
            mensagem_automatica = self.fechado_automaticamente or False
            comunicacao = Comunicacao()
            comunicacao.chamado = self
            comunicacao.data_hora = data_hora
            comunicacao.remetente = usuario
            comunicacao.tipo = comunicacao.TIPO_COMENTARIO
            comunicacao.texto = observacao
            comunicacao.mensagem_automatica = mensagem_automatica
            comunicacao.save(suspender_notificacao=True)
            return comunicacao
        return None

    @transaction.atomic()
    def gravar_historico_status(self, usuario, status, data_hora, tempo_atendimento=None, tempo_suspensao=None, tempo_resposta=None, observacao=None):
        historico_status = HistoricoStatus()
        historico_status.chamado = self
        historico_status.usuario = usuario
        historico_status.status = status
        historico_status.data_hora = data_hora
        historico_status.tempo_atendimento = tempo_atendimento
        historico_status.tempo_suspensao = tempo_suspensao
        historico_status.tempo_resposta = tempo_resposta
        historico_status.comunicacao = self.criar_comunicacao(usuario, data_hora, observacao)
        historico_status.save()
        return historico_status

    def get_source_state(self,):
        transitions = self.get_available_status_transitions()
        actual = {t.source for t in transitions}
        return actual.pop()

    @transition(field=status, source=StatusChamado.EM_ATENDIMENTO, target=StatusChamado.RESOLVIDO, permission=lambda instance, user: instance.eh_atendente(user))
    def resolver_chamado_transition(self, usuario):
        pass

    def resolver_chamado(self, usuario, bases_conhecimento, observacao=None):
        """
        Se  target é Resolvido / Suspenso e o anterior em atendimento,
        conta tempo de Atendimento
        """
        self.resolver_chamado_transition(usuario)
        with transaction.atomic():
            self.save()
            agora = datetime.today()
            tempo = agora - self.get_ultimo_historico_status().data_hora
            historico_status = self.gravar_historico_status(usuario, StatusChamado.RESOLVIDO, agora, tempo_atendimento=tempo.total_seconds(), observacao=observacao)
            historico_status.atualizar_bases_conhecimento(bases_conhecimento)
        #
        Notificar.status_atualizado(self)

    @transition(field=status, source=StatusChamado.EM_ATENDIMENTO, target=StatusChamado.SUSPENSO)
    def suspender_chamado_transition(self,):
        pass

    def suspender_chamado(self, usuario, observacao=None):
        self.suspender_chamado_transition()
        with transaction.atomic():
            self.save()
            self.gravar_historico_status(usuario, StatusChamado.SUSPENSO, datetime.today(), observacao=observacao)

        Notificar.status_atualizado(self)

    @transition(field=status, source=[StatusChamado.RESOLVIDO, StatusChamado.FECHADO], target=StatusChamado.REABERTO)
    def reabrir_chamado_transition(self,):
        pass

    @transition(field=status, source=[StatusChamado.EM_ATENDIMENTO], target=StatusChamado.ABERTO)
    def escalar_chamado_transition(self,):
        pass

    def escalar_chamado(self, usuario):
        self.escalar_chamado_transition()
        with transaction.atomic():
            self.save()
            self.gravar_historico_status(usuario, StatusChamado.ABERTO, datetime.today())
        Notificar.status_atualizado(self)

    @transition(field=status, source=[StatusChamado.ABERTO, StatusChamado.EM_ATENDIMENTO, StatusChamado.SUSPENSO], target=StatusChamado.CANCELADO)
    def cancelar_chamado_transition(self,):
        pass

    def cancelar_chamado(self, usuario, observacao):
        self.cancelar_chamado_transition()
        with transaction.atomic():
            self.save()
            self.gravar_historico_status(usuario, StatusChamado.CANCELADO, datetime.today(), observacao=observacao)

        Notificar.status_atualizado(self)

    def get_available_status_index(self,):
        return [s.target for s in self.get_available_status_transitions()]

    def get_available_status_name(self,):
        return [(StatusChamado.get_action_from_status(s.target), StatusChamado.STATUS[s.target].replace(" ", "_").lower()) for s in self.get_available_status_transitions()]

    def get_available_status_display_name(self,):
        return [StatusChamado.STATUS[s.target] for s in self.get_available_status_transitions()]

    def get_proximos_status(self):
        try:
            # return next(self.get_available_status_transitions()).target
            return sorted(t.target for t in self.get_available_status_transitions())[0]
        except StopIteration:
            return None

    @transition(
        field=status,
        source=[StatusChamado.ABERTO, StatusChamado.REABERTO, StatusChamado.SUSPENSO],
        target=StatusChamado.EM_ATENDIMENTO,
        permission=lambda instance, user: instance.eh_atendente(user),
    )
    def colocar_em_atendimento_transition(self, usuario):
        pass

    def colocar_em_atendimento(self, usuario):
        self.colocar_em_atendimento_transition(usuario)
        agora = datetime.today()
        tempo = agora - self.get_ultimo_historico_status().data_hora
        tempo_resposta = tempo.total_seconds()
        with transaction.atomic():
            self.save()
            self.gravar_historico_status(usuario, StatusChamado.get_status_em_atendimento(), agora, tempo_resposta=tempo_resposta)
        Notificar.status_atualizado(self)

    @transition(field=status, source=[StatusChamado.RESOLVIDO], target=StatusChamado.FECHADO)
    def fechar_chamado_transition(self,):
        pass

    def fechar_chamado(self, usuario, nota_avaliacao=None, comentario_avaliacao=None, fechado_automaticamente=None, observacao=None):
        self.fechar_chamado_transition()
        with transaction.atomic():
            if nota_avaliacao:
                self.nota_avaliacao = nota_avaliacao
                self.data_avaliacao = datetime.now()
            if comentario_avaliacao:
                self.comentario_avaliacao = comentario_avaliacao
            self.fechado_automaticamente = fechado_automaticamente
            self.save()
            self.gravar_historico_status(usuario, StatusChamado.FECHADO, datetime.today(), observacao=observacao)
        #
        Notificar.status_atualizado(self)

    """
        Chamada a este método ocorre quando um chamado é reclassificado e muda de Centro/Grupo de Atentimento.
        Neste caso, o chamado estava Em Atendimento e deve ficar Em Aberto no novo Centro/Grupo de Atentimento.

    """

    @transition(field=status, source=[StatusChamado.EM_ATENDIMENTO], target=StatusChamado.ABERTO)
    def colocar_em_aberto_transition(self,):
        pass

    def colocar_em_aberto(self, usuario, observacao=None):
        self.colocar_em_aberto_transition()
        with transaction.atomic():
            self.save()
            self.gravar_historico_status(usuario, StatusChamado.ABERTO, datetime.today(), observacao=observacao)
        Notificar.status_atualizado(self)

    def reabrir_chamado(self, usuario, observacao):
        self.reabrir_chamado_transition()
        with transaction.atomic():
            self.save()
            self.gravar_historico_status(usuario, StatusChamado.REABERTO, datetime.today(), observacao=observacao)
        Notificar.status_atualizado(self)

    def escalar_ou_retornar_atendimento(self, operacao, atribuido_por, atribuido_para=None):
        """
            Escala (sobe o nível do atendimento) ou
            Retorna (desce o nível do atendimento)
            Informe escalar=True para subir e escalar=False para descer
        """
        # Obtem a atribuicao mais recente
        atribuicao = self.get_atendimento_atribuicao_atual()
        if operacao == 'escalar':
            grupo = atribuicao.grupo_atendimento.grupo_atendimento_superior
            tipo_justificativa = AtendimentoAtribuicao.TIPO_CHAMADO_ESCALADO
            justificativa_cancelamento = 'Chamado escalado para Nível de Atendimento Superior'
        else:
            grupo = atribuicao.grupo_atendimento.get_grupo_antendimento_inferior(self)
            tipo_justificativa = AtendimentoAtribuicao.TIPO_CHAMADO_RETORNADO
            justificativa_cancelamento = 'Chamado retornado ao Nível de Atendimento Anterior'

        # Atualiza a atribuicao anterior e cria uma nova
        atribuicao.cancelado_em = datetime.today()
        atribuicao.cancelado_por = atribuido_por
        atribuicao.justificativa_cancelamento = justificativa_cancelamento
        atribuicao.tipo_justificativa = tipo_justificativa
        atribuicao.save()

        atribuicao = AtendimentoAtribuicao()
        atribuicao.chamado = self
        atribuicao.grupo_atendimento = grupo
        atribuicao.atribuido_em = datetime.today()
        atribuicao.atribuido_por = atribuido_por
        atribuicao.atribuido_para = atribuido_para
        atribuicao.save()

        if self.status != StatusChamado.get_status_aberto() and self.status != StatusChamado.get_status_reaberto():
            # Altera o status para reaberto.
            self.escalar_chamado(atribuido_por)

    def escalar_atendimento(self, atribuido_por):
        self.escalar_ou_retornar_atendimento('escalar', atribuido_por)
        self.save()

    def retornar_atendimento(self, atribuido_por):
        self.escalar_ou_retornar_atendimento('retornar', atribuido_por)
        self.save()

    def atribuir_atendente(self, grupo, atribuido_por, atribuido_para, justificativa_cancelamento='Nova atribuição de chamado', tipo_justificativa=None):
        """
            Verifica se está atribuído a alguem.
            Se estiver: cancela e se auto atribui
            Se não estiver: se auto atribui
        """
        # Obtem a atribuicao mais recente
        atribuicao = self.get_atendimento_atribuicao_atual()
        if atribuicao.atribuido_para:
            # Sim, está atribuido para alguem diferente da nova atribuicao
            if atribuicao.atribuido_para != atribuido_para:
                # Atualiza a atribuicao anterior e cria uma nova
                atribuicao.cancelado_em = datetime.today()
                atribuicao.cancelado_por = atribuido_por
                atribuicao.justificativa_cancelamento = justificativa_cancelamento
                atribuicao.tipo_justificativa = tipo_justificativa or AtendimentoAtribuicao.TIPO_NOVA_ATRIBUICAO
                atribuicao.save()

                atribuicao = AtendimentoAtribuicao()
                atribuicao.chamado = self
                atribuicao.grupo_atendimento = grupo
                atribuicao.atribuido_em = datetime.today()
                atribuicao.atribuido_por = atribuido_por
                atribuicao.atribuido_para = atribuido_para
                atribuicao.save()

        else:
            # Ainda não está atribuido para ninguem
            atribuicao.atribuido_por = atribuido_por
            atribuicao.atribuido_para = atribuido_para
            atribuicao.atribuido_em = datetime.today()
            atribuicao.save()

        if atribuido_por != atribuido_para:
            Notificar.chamado_atribuido(self)

    @transaction.atomic
    def reclassificar(self, servico_novo, campus_novo, centro_atendimento_novo, justificativa, usuario):
        if self.status not in (StatusChamado.get_status_aberto(), StatusChamado.get_status_reaberto(), StatusChamado.get_status_em_atendimento()):
            raise ValidationError('Um chamado só pode ser reclassificado se estiver Aberto ou Em Atendimento.')

        grupo = GrupoAtendimento.get_grupo_primeiro_nivel(campus_novo, centro_atendimento_novo)
        if not grupo:
            raise ValidationError('Não existe Grupo de Atendimento vinculado a este Serviço ' 'nesta Unidade Organizacional.')
        # Campus novo sendo atribuído aqui, pois pode mudar se o centro de atendimento não for local
        campus_novo = grupo.campus

        servico_anterior = self.servico
        campus_anterior = self.campus
        centro_atendimento_anterior = self.get_atendimento_atribuicao_atual().grupo_atendimento.centro_atendimento

        self.servico = servico_novo
        self.reclassificado = 1 if not self.reclassificado else self.reclassificado + 1
        self.campus = campus_novo
        self.save()

        comunicacao = Comunicacao()
        comunicacao.chamado = self
        comunicacao.remetente = usuario
        comunicacao.tipo = Comunicacao.TIPO_COMENTARIO
        texto = []
        texto.append(f'<strong>Chamado Reclassificado</strong> (Código Interno: #{servico_anterior.id}-{servico_novo.id})')
        if servico_anterior.id != servico_novo.id:
            texto.append(f'\n Serviço alterado de "{servico_anterior.nome}" para "{servico_novo.nome}".')
        if centro_atendimento_anterior.id != centro_atendimento_novo.id:
            texto.append(f'\n Centro de Atendimento alterado de "{centro_atendimento_anterior.nome}" para "{centro_atendimento_novo.nome}".')
        if campus_anterior.id != campus_novo.id:
            texto.append(f'\n Campus alterado de "{campus_anterior.nome}" para "{campus_novo.nome}".')
        comunicacao.texto = ''.join(texto)
        comunicacao.mensagem_automatica = True
        comunicacao.save()

        comunicacao.pk = None
        comunicacao.texto = justificativa
        comunicacao.mensagem_automatica = False
        comunicacao.save()

        """
        Ao reclassificar um chamado, caso mude o Centro de Atendimento,
        o chamado deverá mudar de status (caso já esteja em atendimento)
        e ser redirecionado para o primeiro nivel do novo centro de atendimento.
        """
        if centro_atendimento_anterior != centro_atendimento_novo or campus_anterior != campus_novo:
            # Atualiza a atribuicao anterior e cria uma nova
            atribuicao = self.get_atendimento_atribuicao_atual()
            atribuicao.cancelado_em = datetime.today()
            atribuicao.cancelado_por = usuario
            atribuicao.justificativa_cancelamento = 'Alteração realizada em decorrência da mudança de Serviço/Centro de Atendimento.'
            atribuicao.save()

            atribuicao = AtendimentoAtribuicao()
            atribuicao.chamado = self
            atribuicao.grupo_atendimento = grupo
            atribuicao.atribuido_em = datetime.today()
            atribuicao.atribuido_por = usuario
            atribuicao.save()

            if self.status != StatusChamado.get_status_aberto() and self.status != StatusChamado.get_status_reaberto():
                self.colocar_em_aberto(usuario)

    @transaction.atomic
    def alterar_status(self, usuario, status_id=None, bases_conhecimento=None, observacao=None, nota_avaliacao=None, comentario_avaliacao=None, fechado_automaticamente=None):

        novo_status = status_id if status_id else self.get_proximo_status()
        agora = datetime.today()
        tempo_atendimento = None
        tempo_resposta = None
        tempo_suspensao = None
        tempo = agora - self.get_ultimo_historico_status().data_hora

        """ Se o status novo for Resolvido/Suspenso e o anterior em atendimento, conta tempo de Atendimento """
        """ Se o status novo Em Atendimento for e o anterior Suspenso, conta tempo de Suspensão """
        """ Se o status novo for Em Atendimento e o anterior Aberto/Reaberto, conta tempo de resposta """
        if novo_status in (StatusChamado.get_status_resolvido(), StatusChamado.get_status_suspenso()) and self.status == StatusChamado.get_status_em_atendimento():
            tempo_atendimento = tempo.total_seconds()
        elif novo_status == StatusChamado.get_status_em_atendimento() and self.status == StatusChamado.get_status_suspenso():
            tempo_suspensao = tempo.total_seconds()
        elif novo_status == StatusChamado.get_status_em_atendimento() and self.status in (StatusChamado.get_status_aberto(), StatusChamado.get_status_reaberto()):
            tempo_resposta = tempo.total_seconds()

        bases_conhecimento = bases_conhecimento or BaseConhecimento.objects.none()
        self.status = novo_status

        if nota_avaliacao:
            self.nota_avaliacao = nota_avaliacao
            self.data_avaliacao = datetime.now()
        if comentario_avaliacao:
            self.comentario_avaliacao = comentario_avaliacao
        self.fechado_automaticamente = fechado_automaticamente
        self.save()

        historico_status = HistoricoStatus()
        historico_status.chamado = self
        historico_status.usuario = usuario
        historico_status.data_hora = agora
        historico_status.status_id = self.status

        if tempo_atendimento:
            historico_status.tempo_atendimento = tempo_atendimento
        if tempo_resposta:
            historico_status.tempo_resposta = tempo_resposta
        if tempo_suspensao:
            historico_status.tempo_suspensao = tempo_suspensao

        if observacao:
            comunicacao = Comunicacao()
            comunicacao.chamado = self
            comunicacao.data_hora = historico_status.data_hora
            comunicacao.remetente = usuario
            comunicacao.tipo = comunicacao.TIPO_COMENTARIO
            comunicacao.texto = observacao
            comunicacao.save(suspender_notificacao=True)
            historico_status.comunicacao = comunicacao
        historico_status.save()
        for base in bases_conhecimento:
            historico_status.bases_conhecimento.add(base)

        Notificar.status_atualizado(self)

    @transaction.atomic
    def adicionar_outros_interessados(self, outros_interessados):
        self.outros_interessados.add(*outros_interessados)
        Notificar.adicao_outros_interessados(self, outros_interessados)

    @transaction.atomic
    def adicionar_grupos_interessados(self, grupos_interessados):
        qs = User.objects.none()
        for grupo in grupos_interessados:
            qs = qs | grupo.interessados.all().exclude(id__in=self.outros_interessados.all()).exclude(id=self.interessado.id)
        self.adicionar_outros_interessados(qs.all().distinct())

    def adicionar_tags(self, tags):
        self.tags.add(*tags)

    def estah_com_sla_estourado(self):
        if not self.get_tempo_gasto():
            return None
        valor = (self.get_tempo_gasto().total_seconds() // 3600) - self.get_sla_em_horas()
        return valor > 0

    def get_tempo_atendimento(self):
        tempo = self.historicostatus_set.filter(tempo_atendimento__isnull=False).aggregate(tempo=Sum('tempo_atendimento'))['tempo']
        if tempo:
            return timedelta(seconds=tempo)
        else:
            return None

    def get_tempo_resposta(self):
        tempo = self.historicostatus_set.filter(tempo_resposta__isnull=False).aggregate(tempo=Sum('tempo_resposta'))['tempo']
        if tempo:
            return timedelta(seconds=tempo)
        else:
            return None

    def get_sla_em_horas(self):
        """ Retorna o tempo do SLA do servico deste chamado
            Calculando a diferença (em horas) entre a data_limite_atendimento e a data de abertura do chamado
        """
        tempo = self.data_limite_atendimento - self.aberto_em
        return int(tempo.total_seconds() // 3600)

    def get_tempo_gasto_detalhes(self):
        """ Retorna uma lista com tempo efetivamente gasto com o atendimento
            É a somatória do período de tempo entre os chamados abertos/reabertos e resolvidos (ou ainda não resolvidos)
            A lista contem os atributos: status, data_inicio, data_fim, tempo_total
            O último registro da lista, contém apenas o tempo total
        """
        tempo = timedelta(seconds=0)
        lista = []
        data_inicio = None
        data_fim = None
        status_inicio = None
        try:
            for historico_status in self.historicostatus_set.order_by('data_hora'):
                if historico_status.status in (StatusChamado.get_status_aberto(), StatusChamado.get_status_reaberto()):
                    data_inicio = historico_status.data_hora
                    status_inicio = historico_status.status

                elif historico_status.status == StatusChamado.get_status_resolvido():
                    data_fim = historico_status.data_hora
                    status_fim = historico_status.status
                    ultimo_registro = data_fim - data_inicio
                    tempo += ultimo_registro
                    d = dict(status_inicio=status_inicio, data_inicio=data_inicio, status_fim=status_fim, data_fim=data_fim, tempo_total=ultimo_registro)
                    lista.append(d)
                    data_inicio = None
                    data_fim = None
                    status_inicio = None

            if data_inicio and not data_fim:
                agora = datetime.now()
                ultimo_registro = agora - data_inicio
                tempo += ultimo_registro
                d = dict(status_inicio=status_inicio, data_inicio=data_inicio, tempo_total=ultimo_registro)
                lista.append(d)

            d = dict(tempo_total=timedelta(seconds=tempo.total_seconds()))
            lista.append(d)
        except Exception:
            return None

        return lista

    def get_tempo_ultrapassado(self):
        """ Opções:
            Chamado resolvido sem ter o tempo ultrapassado
            Chamado resolvido com tempo ultrapassado
            Chamado aberto sem tempo ultrapassado
            Chamado aberto com tempo ultrapassado
        """
        retorno = None
        historicostatus = self.historicostatus_set.filter(status=StatusChamado.get_status_resolvido()).order_by('data_hora')
        if historicostatus.exists():
            if historicostatus[0].data_hora > self.data_limite_atendimento:
                retorno = historicostatus[0].data_hora - self.data_limite_atendimento
                return timedelta(seconds=retorno.total_seconds())
        else:
            if datetime.now() > self.data_limite_atendimento:
                retorno = datetime.now() - self.data_limite_atendimento
                return timedelta(seconds=retorno.total_seconds())
        return retorno

    def calcula_data_limite_sem_feriados_fds(self):
        """ Retorna a data limite de atendimento do chamado considerando o
                SLA do serviço, finais de semana e feriados.
        """
        data_inicio = self.aberto_em
        sla = self.servico.sla_em_horas
        liberacoes = self.busca_liberacoes(data_inicio)

        # se a data de abertura for fds ou feriado, não contabilizar as horas para os calculos
        if data_inicio.weekday() in (5, 6) or data_inicio.date in liberacoes:
            data_inicio = datetime(data_inicio.year, data_inicio.month, data_inicio.day, 23, 59, 0)

        dias_chamado = sla / 24  # descobrir nro de dias (24h)
        horas_chamado = sla % 24  # pegar o restante

        data_limite = datetime(data_inicio.year, data_inicio.month, data_inicio.day, data_inicio.hour, data_inicio.minute)

        while dias_chamado > 0:
            data_limite += timedelta(days=1)
            if data_limite.weekday() not in (5, 6) and data_limite.date() not in liberacoes:
                dias_chamado -= 1

        data_limite += timedelta(hours=horas_chamado)
        return data_limite

    def busca_liberacoes(self, data_inicio):
        """ retorna a lista de dias que não tem expediente """
        liberacoes = []
        Liberacao = apps.get_model('ponto', 'Liberacao')
        if Liberacao:
            data_fim = data_inicio + timedelta(days=150)

            lista_liberacoes = list(Liberacao.get_liberacoes_calendario_recorrentes(UnidadeOrganizacional.TIPO_REITORIA, data_inicio.year)) + list(
                Liberacao.objects.filter(uo=None, data_inicio__gte=data_inicio, ch_maxima_exigida=0)
            )

            if data_inicio.year != data_fim.year:
                lista_liberacoes = lista_liberacoes + list(Liberacao.get_liberacoes_calendario(UnidadeOrganizacional.TIPO_REITORIA, data_fim.year))

            for liberacao in lista_liberacoes:
                liberacoes.extend(self.transforma_periodo_em_lista_dias(liberacao.data_inicio, liberacao.data_fim))
        return liberacoes

    def transforma_periodo_em_lista_dias(self, data_inicio, data_fim):
        """ Retorna a lista de dias entre a data_inicio até data_fim """
        dias = []
        while data_inicio <= data_fim:
            dias.append(data_inicio)
            data_inicio += timedelta(days=1)
        return dias

    def get_tempo_gasto(self):
        """ Retorna o tempo total efetivamente gasto com o atendimento """
        tempo = self.get_tempo_gasto_detalhes()
        if tempo:
            return tempo.pop()['tempo_total']

    def get_tempo_ate_data_limite(self):
        """ Retorna o tempo restante ate atingir a data limite """
        tempo = self.data_limite_atendimento - datetime.now()
        return timedelta(seconds=tempo.total_seconds())

    def get_tempo_apos_data_limite(self):
        """ Retorna o tempo ultrapassado após atingir a data limite """
        tempo = datetime.now() - self.data_limite_atendimento
        return timedelta(seconds=tempo.total_seconds())

    def get_bases_de_conhecimento_aplicadas(self):
        qs = self.historicostatus_set.filter(status=StatusChamado.get_status_resolvido())
        if qs.exists():
            return qs.order_by('-data_hora')[0].bases_conhecimento.all()

    def get_ultimo_historico_status(self):
        return self.historicostatus_set.order_by('-data_hora')[0]

    def get_atendimento_atribuicao_atual(self):
        return self.atendimentoatribuicao_set.order_by('-atribuido_em').first()

    def get_atendimento_atribuicao_anterior(self):
        atendimentos = self.atendimentoatribuicao_set.order_by('-atribuido_em')
        if atendimentos.count() > 1:
            return atendimentos[1]

    def get_historicostatus(self):
        return self.historicostatus_set.all().order_by('-data_hora')

    def get_comentarios(self):
        return self.comunicacao_set.filter(tipo=Comunicacao.TIPO_COMENTARIO)

    def get_notas_internas(self):
        return self.comunicacao_set.filter(tipo=Comunicacao.TIPO_NOTA_INTERNA).order_by('-data_hora')

    def email_interessados(self):
        emails = []
        if self.interessado.email:
            emails += [self.interessado.email]
        emails += self.outros_interessados.exclude(email='').values_list('email', flat=True)
        return emails

    def get_vinculos_interessados(self):
        interessados = []
        if self.outros_interessados.exists():
            for outro in self.outros_interessados.all():
                interessados.append(outro.get_vinculo())
        interessados.append(self.interessado.get_vinculo())
        return interessados

    def eh_outro_interessado(self, user):
        return self.outros_interessados.filter(username=user.username).exists()

    def pessoa_envolvida(self, user):
        return user in (self.requisitante, self.interessado, self.aberto_por) or self.eh_outro_interessado(user)

    def permite_visualizar(self, user):
        """
            Apenas Super usuário, Auditores, responsáveis pelo atendimento ou pessoas envolvidas na abertura
            do chamado podem visualizar o chamado
        """
        return (
            self.pessoa_envolvida(user)
            or (user.has_perm('centralservicos.change_chamado') and self.atendimentoatribuicao_set.filter(grupo_atendimento__in=user.atendentes_set.all()))
            or user.is_superuser
            or user.groups.filter(models.Q(name='centralservicos Administrador') | models.Q(name='Auditor')).exists()
        )

    def get_atendente_do_chamado(self):
        return self.get_atendimento_atribuicao_atual().atribuido_para

    def get_responsaveis_equipe_atendimento(self):
        """ Retorna os chefes do Grupo de Atendimento do respectivo Chamado """
        atendimento = self.get_atendimento_atribuicao_atual()
        if atendimento:
            return atendimento.grupo_atendimento.responsaveis.all()

    def get_atendentes_equipe_atendimento(self):
        """ Retorna os atendentes do Grupo de Atendimento do respectivo Chamado """
        atendimento = self.get_atendimento_atribuicao_atual()
        if atendimento:
            return atendimento.grupo_atendimento.atendentes.all()

    def eh_atendente(self, user):
        atendimento = self.get_atendimento_atribuicao_atual()
        return user.has_perm('centralservicos.change_chamado') and atendimento and atendimento.atribuido_para == user and not atendimento.cancelado_em

    def estah_resolvido(self):
        return self.status == StatusChamado.get_status_resolvido()

    def estah_suspenso(self):
        return self.status == StatusChamado.get_status_suspenso()

    def estah_em_atendimento(self):
        return self.status == StatusChamado.get_status_em_atendimento()

    def estah_fechado(self):
        return self.status == StatusChamado.get_status_fechado()

    def estah_cancelado(self):
        return self.status == StatusChamado.get_status_cancelado()

    def eh_proximo_status_em_atendimento(self):
        return StatusChamado.get_status_em_atendimento() in self.get_available_status_index()

    def pode_escalar(self):
        """ Para poder escalar o chamado, o mesmo não pode estar resolvido, nao pode estar fechado
            deve estar atribuído a algum atendente e deve possuit um grupo de atendimento superior
        """
        if (
            self.status not in (StatusChamado.get_status_resolvido(), StatusChamado.get_status_fechado(), StatusChamado.get_status_cancelado(), StatusChamado.get_status_suspenso())
            and self.get_atendimento_atribuicao_atual()
            and self.get_atendimento_atribuicao_atual().atribuido_para
            and self.get_atendimento_atribuicao_atual().grupo_atendimento.grupo_atendimento_superior
        ):
            return True
        else:
            return False

    def pode_atribuir(self):
        if self.status not in (StatusChamado.get_status_resolvido(), StatusChamado.get_status_fechado(), StatusChamado.get_status_cancelado()):
            return True
        return False

    def pode_assumir(self, user):
        atendimento_atribuicao = self.get_atendimento_atribuicao_atual()
        if (
            atendimento_atribuicao
            and self.pode_atribuir()
            and not atendimento_atribuicao.atribuido_para == user
            and atendimento_atribuicao.grupo_atendimento.pertence_ao_grupo(user)
            and user.has_perm('centralservicos.change_chamado')
        ):
            return True
        else:
            return False

    def pode_retornar(self):
        if (
            self.status not in (StatusChamado.get_status_resolvido(), StatusChamado.get_status_fechado(), StatusChamado.get_status_cancelado(), StatusChamado.get_status_suspenso())
            and self.get_atendimento_atribuicao_atual()
            and self.get_atendimento_atribuicao_atual().grupo_atendimento.get_grupo_antendimento_inferior(self)
        ):
            return True
        else:
            return False

    def pode_fechar(self, user):
        """ Para poder fechar o chamado, o chamado deverá estar resolvido """
        """ E o usuário ser super user, chefe do atendimento ou o proprio usuario (pessoa_envolvida) """
        if self.estah_resolvido():
            if (
                user.is_superuser
                or user in (self.requisitante, self.interessado)
                or self.get_atendimento_atribuicao_atual().grupo_atendimento.responsaveis.filter(pk=user.pk).exists()
            ):
                return True
            else:
                return False

    def pode_reabrir(self, user):
        """
            Para poder reabrir o chamado, o chamado deverá estar resolvido ou fechado.

            E o usuário ser super user, chefe do atendimento ou o proprio
            usuario (pessoa_envolvida)
        """
        if self.estah_resolvido() and not self.estah_fechado():
            if (
                user.is_superuser
                or user in (self.requisitante, self.interessado)
                or self.get_atendimento_atribuicao_atual().grupo_atendimento.responsaveis.filter(pk=user.pk).exists()
            ):
                return True
            else:
                return False
        return False

    def pode_reclassificar(self, user):
        if self.status in (StatusChamado.get_status_aberto(), StatusChamado.get_status_reaberto(), StatusChamado.get_status_em_atendimento()):
            if user.is_superuser or self.get_responsaveis_equipe_atendimento().filter(pk=user.pk).exists() or self.eh_atendente(user):
                return True
        return False

    def pode_suspender(self, user):
        return self.status == StatusChamado.get_status_em_atendimento() and self.eh_atendente(user)

    def pode_cancelar(self, user):
        if self.status in (StatusChamado.get_status_aberto(), StatusChamado.get_status_em_atendimento(), StatusChamado.get_status_suspenso()):
            if user in (self.requisitante, self.interessado) or self.eh_atendente(user) or user.is_superuser:
                return True
        return False

    TIPO_USUARIO_REQUISITANTE = 'R'
    TIPO_USUARIO_INTERESSADO = 'I'
    TIPO_USUARIO_OUTROS_INTERESSADOS = 'O'
    TIPO_USUARIO_CHOICES = [
        [TIPO_USUARIO_REQUISITANTE, 'Requisitante'],
        [TIPO_USUARIO_INTERESSADO, 'Interessado'],
        [TIPO_USUARIO_OUTROS_INTERESSADOS, 'Outros Interessados'],
        ['', 'Qualquer'],
    ]

    @classmethod
    def get_chamados_do_usuario(cls, user, chamado_id=None, area=None, data_inicial=None, data_final=None, status=None, tipo_usuario=None):
        if not tipo_usuario:
            qs = Chamado.objects.filter(models.Q(requisitante=user) | models.Q(interessado=user) | models.Q(outros_interessados__pk=user.pk))
        elif tipo_usuario == Chamado.TIPO_USUARIO_REQUISITANTE:
            qs = Chamado.objects.filter(requisitante=user)
        elif tipo_usuario == Chamado.TIPO_USUARIO_INTERESSADO:
            qs = Chamado.objects.filter(interessado=user)
        else:
            qs = Chamado.objects.filter(outros_interessados__pk=user.pk)

        if chamado_id:
            qs = qs.filter(pk=chamado_id)
        else:
            if area:
                qs = qs.filter(servico__area=area)
            if data_inicial:
                qs = qs.filter(aberto_em__gte=datetime(data_inicial.year, data_inicial.month, data_inicial.day, 0, 0, 0))
            if data_final:
                qs = qs.filter(aberto_em__lte=datetime(data_final.year, data_final.month, data_final.day, 23, 59, 59))

            if status:
                if status == STATUS_ATIVO:
                    qs = qs.exclude(status__in=(StatusChamado.get_status_fechado(), StatusChamado.get_status_resolvido(), StatusChamado.get_status_cancelado()))
                else:
                    qs = qs.filter(status=status)

        return qs.distinct()

    ATRIBUIDOS_A_MIM = '1'
    ATRIBUIDOS_A_OUTROS = '2'
    SEM_ATRIBUICAO = '3'
    ATRIBUIDOS_A_MIM_OU_SEM_ATRIBUICAO = '4'
    ATRIBUIDOS = '5'
    ATRIBUICOES_CHOICES = [
        [ATRIBUIDOS_A_MIM, 'Atribuídos a mim'],
        [ATRIBUIDOS_A_OUTROS, 'Atribuídos a outros'],
        [SEM_ATRIBUICAO, 'Sem atribuição'],
        [ATRIBUIDOS_A_MIM_OU_SEM_ATRIBUICAO, 'Atribuídos a mim ou sem atribuição'],
        [ATRIBUIDOS, 'Atribuídos'],
    ]

    @classmethod
    def get_chamados_do_suporte(cls, user, **kwargs):
        chamado_id = kwargs.get('chamado_id')
        data_inicial = kwargs.get('data_inicial')
        data_final = kwargs.get('data_final')
        tipo = kwargs.get('tipo')
        status = kwargs.get('status')
        nota_avaliacao = kwargs.get('nota_avaliacao')
        uo = kwargs.get('uo')
        area = kwargs.get('area')
        grupo_atendimento = kwargs.get('grupo_atendimento')
        tags = kwargs.get('tags')
        atribuicoes = kwargs.get('atribuicoes')
        todos_status = kwargs.get('todos_status')
        texto_livre = kwargs.get('texto_livre')
        considerar_escalados = kwargs.get('considerar_escalados')
        servico = kwargs.get('servico')
        grupo_servico = kwargs.get('grupo_servico')
        interessado = kwargs.get('interessado')
        aberto_por = kwargs.get('aberto_por')
        atendente = kwargs.get('atendente')
        ordenar_por = kwargs.get('ordenar_por') or 'data_limite_atendimento'
        tipo_ordenacao = kwargs.get('tipo_ordenacao') or ''
        sla_estourado = kwargs.get('sla_estourado')
        ordenar_por = f'{tipo_ordenacao}{ordenar_por}'

        qs = Chamado.objects.all()
        if chamado_id:
            qs = qs.filter(pk=chamado_id)
        else:
            if grupo_atendimento:
                filter_grupo_atendimento = Q(grupo_atendimento__in=grupo_atendimento) if isinstance(grupo_atendimento, Iterable) else Q(grupo_atendimento=grupo_atendimento)
                atendimentos = AtendimentoAtribuicao.objects.filter(filter_grupo_atendimento, cancelado_em__isnull=True)
            else:
                """ Obtem os chamados que ja passaram pelo grupo de atendimento.
                Independente se está atualmente no grupo. """
                if considerar_escalados or chamado_id:
                    atendimentos = AtendimentoAtribuicao.objects.filter(grupo_atendimento__in=GrupoAtendimento.meus_grupos(user, area))
                else:
                    atendimentos = AtendimentoAtribuicao.objects.filter(grupo_atendimento__in=GrupoAtendimento.meus_grupos(user, area), cancelado_em__isnull=True)

            if atribuicoes:
                if atribuicoes == Chamado.ATRIBUIDOS_A_MIM:
                    atendimentos = atendimentos.filter(atribuido_para=user, cancelado_em__isnull=True)
                elif atribuicoes == Chamado.ATRIBUIDOS_A_OUTROS:
                    if atendente:
                        atendimentos = atendimentos.filter(atribuido_para__isnull=False, cancelado_em__isnull=True, atribuido_para=atendente)
                    else:
                        atendimentos = atendimentos.filter(atribuido_para__isnull=False, cancelado_em__isnull=True).exclude(atribuido_para=user)
                elif atribuicoes == Chamado.SEM_ATRIBUICAO:
                    atendimentos = atendimentos.filter(atribuido_para__isnull=True, cancelado_em__isnull=True)
                elif atribuicoes == Chamado.ATRIBUIDOS_A_MIM_OU_SEM_ATRIBUICAO:
                    atendimentos = atendimentos.filter(cancelado_em__isnull=True).filter(models.Q(atribuido_para=user) | models.Q(atribuido_para__isnull=True))
                elif atribuicoes == Chamado.ATRIBUIDOS:
                    atendimentos = atendimentos.filter(atribuido_para__isnull=False, cancelado_em__isnull=True)

            if uo:
                filter_uo = Q(grupo_atendimento__campus_id__in=uo) if isinstance(uo, Iterable) else Q(grupo_atendimento__campus=uo)
                atendimentos = atendimentos.filter(filter_uo)

            qs = qs.filter(pk__in=atendimentos.values('chamado'))

            if data_inicial:
                qs = qs.filter(aberto_em__gte=datetime(data_inicial.year, data_inicial.month, data_inicial.day, 0, 0, 0))
            if data_final:
                qs = qs.filter(aberto_em__lte=datetime(data_final.year, data_final.month, data_final.day, 23, 59, 59))
            if tipo:
                qs = qs.filter(servico__tipo=tipo)
            if tags:
                qs = qs.filter(tags__in=tags)
            if nota_avaliacao:
                qs = qs.filter(nota_avaliacao=nota_avaliacao)
            if not todos_status:
                if status:
                    qs = qs.filter(status__in=[int(s) for s in status])
                else:
                    qs = qs.exclude(status__in=(StatusChamado.get_status_fechado(), StatusChamado.get_status_resolvido(), StatusChamado.get_status_cancelado()))
            if servico:
                qs = qs.filter(servico__id=servico.id)
            if grupo_servico:
                qs = qs.filter(servico__grupo_servico__id=grupo_servico.id)
            if interessado:
                qs = qs.filter(models.Q(interessado=interessado) | models.Q(requisitante=interessado) | models.Q(outros_interessados__id=interessado.id))
            if aberto_por:
                qs = qs.filter(aberto_por=aberto_por)
            if texto_livre:
                comunicacoes = Comunicacao.objects.filter(texto__icontains=texto_livre)
                qs = qs.filter(models.Q(pk__in=comunicacoes.values('chamado')) | models.Q(descricao__unaccent__icontains=texto_livre) | models.Q(numero_patrimonio__icontains=texto_livre))
            if sla_estourado:
                qs = qs.filter(data_limite_atendimento__lt=datetime.now())

        return qs.distinct().order_by(ordenar_por)

    def get_linha_do_tempo(self):
        lista = list()
        for comentario in self.get_comentarios():
            lista.append(dict(tipo='comentario', ordem='2', data_hora=comentario.data_hora, objeto=comentario))
        for historicostatus in self.get_historicostatus():
            lista.append(dict(tipo='historicostatus', ordem='1', data_hora=historicostatus.data_hora, objeto=historicostatus))
        for atendimentoatribuicao in self.atendimentoatribuicao_set.order_by('-atribuido_em'):
            lista.append(dict(tipo='atendimentoatribuicao', ordem='3', data_hora=atendimentoatribuicao.atribuido_em, objeto=atendimentoatribuicao))
        for anexo in self.chamadoanexo_set.order_by('-anexado_em'):
            lista.append(dict(tipo='anexo', ordem='4', data_hora=anexo.anexado_em, objeto=anexo))
        if self.data_avaliacao:
            lista.append(dict(tipo='avaliacao', ordem='1', data_hora=self.data_avaliacao))

        lista.sort(key=lambda x: (x['data_hora'], x['ordem']), reverse=True)
        return lista

    @classmethod
    def get_chamados_com_sla_estourado(cls):
        return Chamado.objects.filter(
            data_limite_atendimento__lt=datetime.now(),
            status__in=(StatusChamado.get_status_aberto(), StatusChamado.get_status_em_atendimento(), StatusChamado.get_status_reaberto()),
        ).order_by('data_limite_atendimento')

    def get_visualizar_chamado_url(self):
        return f'{settings.SITE_URL}{self.get_absolute_url()}'


class HistoricoStatus(models.ModelPlus):
    chamado = models.ForeignKeyPlus(Chamado, verbose_name='Chamado')
    data_hora = models.DateTimeField(auto_now_add=True)
    usuario = models.ForeignKeyPlus(User, verbose_name='Usuário')
    status = models.IntegerField(choices=StatusChamado.STATUS)
    bases_conhecimento = models.ManyToManyFieldPlus(BaseConhecimento, related_name='basesconhecimento_set', blank=True, verbose_name='Bases de Conhecimento utilizadas')
    comunicacao = models.OneToOneField('centralservicos.Comunicacao', verbose_name='Comunicação', null=True, on_delete=models.CASCADE)
    tempo_atendimento = models.FloatField('Tempo de Atendimento', null=True, help_text='Tempo de Atendimento entre as situações Em Atendimento e Resolvido.')
    tempo_resposta = models.FloatField('Tempo de Resposta', null=True, help_text='Tempo de Resposta entre as situações Aberto e Em Atendimento.')
    tempo_suspensao = models.FloatField('Tempo de Suspensão', null=True, help_text='Tempo de Suspensão entre as situações Suspenso e Em Atendimento.')

    def aberto(self,):
        return self.status == StatusChamado.get_status_aberto() or self.status == StatusChamado.get_status_reaberto()

    def get_tempo_atendimento(self):
        return timedelta(seconds=self.tempo_atendimento)

    def get_tempo_resposta(self):
        return timedelta(seconds=self.tempo_resposta)

    def get_tempo_suspensao(self):
        return timedelta(seconds=self.tempo_suspensao)

    def __str__(self):
        return f'{self.pk}: {self.chamado} - {StatusChamado.STATUS[self.status]}'

    class Meta:
        ordering = ['data_hora']
        verbose_name = 'Histórico do Situações'
        verbose_name_plural = 'Históricos do Situações'

    def get_bases_conhecimento(self):
        lista = ["<ul>"]
        for base_conhecimento in self.bases_conhecimento.all():
            lista.append(f"<li>{base_conhecimento.titulo}</li>")
        lista.append("</ul>")
        return "\n".join(lista)

    def atualizar_bases_conhecimento(self, bases_conhecimento=None):
        for base in bases_conhecimento:
            self.bases_conhecimento.add(base)


class ChamadoAnexo(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição', max_length=80, null=False, blank=False, help_text='Informe uma descrição resumida sobre o arquivo anexado')
    chamado = models.ForeignKeyPlus(Chamado, verbose_name='Chamado')
    anexo = models.FileFieldPlus(
        max_length=255,
        upload_to='upload/chamado/anexos/',
        validators=[FileExtensionValidator(allowed_extensions=['xlsx', 'xls', 'csv', 'docx', 'doc', 'pdf', 'jpg', 'jpeg', 'png'])],
    )
    anexado_em = models.DateTimeField(auto_now_add=True, null=False, blank=False)
    anexado_por = models.ForeignKeyPlus(User, verbose_name='Anexado Por', null=False, blank=False)

    def __str__(self):
        return f'Chamado {self.chamado.id} - Anexo ({self.id}): {self.descricao}'

    class Meta:
        ordering = ['anexado_em']
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'


class Comunicacao(models.ModelPlus):
    TIPO_COMENTARIO = 'comentario'
    TIPO_NOTA_INTERNA = 'nota_interna'

    TIPO_CHOICES = ((TIPO_COMENTARIO, 'Comentário'), (TIPO_NOTA_INTERNA, 'Nota Interna'))

    chamado = models.ForeignKeyPlus(Chamado, verbose_name='Chamado')
    texto = models.TextField('Texto', null=False, blank=False)
    tipo = models.CharFieldPlus('Tipo', max_length=15, choices=TIPO_CHOICES, null=False, blank=False)
    data_hora = models.DateTimeField(default=datetime.now, null=False, blank=False)
    remetente = models.ForeignKeyPlus(User, verbose_name='Remetente', null=False, blank=False)
    usuarios_citados = models.ManyToManyFieldPlus(User, related_name='usuarios_citados_set', verbose_name='Usuários Citados')
    mensagem_automatica = models.BooleanField('Mensagem Automática?', default=False)
    bases_conhecimento = models.ManyToManyFieldPlus(
        BaseConhecimento,
        related_name='comunicacao_basesconhecimento_set',
        blank=True,
        verbose_name='Bases de Conhecimento',
        help_text='Sugestão de bases de conhecimento para este chamado',
    )
    desconsiderada_em = models.DateTimeField('Desconsiderada Em', null=True, blank=True, help_text='Informe a partir de quando esta comunicação foi desconsiderada.')

    def save(self, *args, **kwargs):
        if not self.pk:
            suspender_notificacao = kwargs.pop('suspender_notificacao', False)
            if suspender_notificacao is False:
                if self.tipo == Comunicacao.TIPO_COMENTARIO:
                    Notificar.comentario(self)
                else:
                    Notificar.nota_interna_ao_atendente(self)
        return super().save(*args, **kwargs)

    def __str__(self):
        return f'Chamado {self.chamado.id} - Comunicação {self.texto}'

    class Meta:
        ordering = ['data_hora']
        verbose_name = 'Comunicação'
        verbose_name_plural = 'Comunicações'


def envia_emails_usuarios_citados(sender, **kwargs):
    instance = kwargs.pop('instance', None)
    action = kwargs.pop('action', None)
    if action == "post_add":
        Notificar.nota_interna_ao_atendente(instance, citar_outros_usuarios=True)


m2m_changed.connect(envia_emails_usuarios_citados, sender=Comunicacao.usuarios_citados.through)


class Autorizacao(models.ModelPlus):
    chamado = models.ForeignKeyPlus(Chamado, verbose_name='Chamado')
    texto = models.TextField('Texto', null=False, blank=False)
    enviado_em = models.DateTimeField('Enviado em', auto_now_add=True, null=False, blank=False)
    enviado_por = models.ForeignKeyPlus(User, related_name='enviado_por_set', verbose_name='Enviado por', null=True, blank=True)
    enviado_para = models.ForeignKeyPlus(User, related_name='enviado_para_set', verbose_name='Enviado para', null=False, blank=False)
    autorizado_em = models.DateTimeField('Autorizado em', null=True, blank=True)
    autorizado_por = models.ForeignKeyPlus(User, related_name='autorizado_por_set', verbose_name='Autorizado por', null=True, blank=True)

    def __str__(self):
        return f'Chamado {self.chamado.id} - Autorização {self.id}'

    class Meta:
        ordering = ['enviado_em']
        verbose_name = 'Autorização'
        verbose_name_plural = 'Autorizações'


class AtendimentoAtribuicao(models.ModelPlus):
    TIPO_CHAMADO_ESCALADO = 'CHAMADO_ESCALADO'
    TIPO_CHAMADO_RETORNADO = 'CHAMADO_RETORNADO'
    TIPO_NOVA_ATRIBUICAO = 'NOVA_ATRIBUICAO'

    TIPO_CHOICES = ((TIPO_CHAMADO_ESCALADO, 'Chamado Escalado'), (TIPO_CHAMADO_RETORNADO, 'Chamado Retornado'), (TIPO_NOVA_ATRIBUICAO, 'Chamado com Nova Atribuição'))
    chamado = models.ForeignKeyPlus(Chamado, verbose_name='Chamado')
    grupo_atendimento = models.ForeignKeyPlus(GrupoAtendimento, verbose_name='Grupo de Atendimento')
    atribuido_em = models.DateTimeField('Atribuído em', null=True, blank=True)
    atribuido_por = models.ForeignKeyPlus(User, related_name='atribuido_por_set', verbose_name='Atribuído por', null=True, blank=True)
    atribuido_para = models.ForeignKeyPlus(User, related_name='atribuido_para_set', verbose_name='Atribuído para', null=True, blank=True)
    cancelado_em = models.DateTimeField('Cancelado em', null=True, blank=True)
    cancelado_por = models.ForeignKeyPlus(User, related_name='cancelado_por_set', verbose_name='Cancelado por', null=True, blank=True)
    justificativa_cancelamento = models.TextField(verbose_name='Justificativa', null=True, blank=True)
    tipo_justificativa = models.CharFieldPlus('Tipo', max_length=25, choices=TIPO_CHOICES, null=True)

    def __str__(self):
        return f'Chamado {self.chamado.id} - Atendimento {self.id}'

    class Meta:
        ordering = ['-atribuido_em']
        verbose_name = 'Atribuição'
        verbose_name_plural = 'Atribuições'


class Monitoramento(models.ModelPlus):
    titulo = models.CharFieldPlus('Título', max_length=100, help_text='Informe um título para este monitoramento.')
    grupos = models.ManyToManyFieldPlus(GrupoAtendimento, verbose_name='Grupo de Atendimento')
    token = models.CharFieldPlus('Token', max_length=32, unique=True, help_text='Token gerado automaticamente pelo sistema.')
    cadastrado_por = models.ForeignKeyPlus(User, related_name='cadastrado_por_set', verbose_name='Cadastrado Por')
    cadastrado_em = models.DateTimeField(auto_now_add=True)
    organizar_por_tipo = models.BooleanField('Organizar por Tipo', default=True)

    def get_absolute_url(self):
        return f'/centralservicos/monitoramento/{self.token}/'

    def __str__(self):
        return f'{self.titulo} - {self.token}'

    class Meta:
        ordering = ['titulo']
        verbose_name = 'Monitoramento'
        verbose_name_plural = 'Monitoramentos'


class RespostaPadrao(models.ModelPlus):
    atendente = models.ForeignKeyPlus(User, related_name='resposta_atendente_set', verbose_name='Atendente')
    status = models.IntegerField(choices=StatusChamado.STATUS, default=StatusChamado.EM_ATENDIMENTO, null=True, blank=True)
    texto = models.TextField('Texto Padrão')

    def __str__(self):
        return f'{self.texto}'

    class Meta:
        ordering = ['texto']
        verbose_name = 'Resposta Padrão'
        verbose_name_plural = 'Respostas Padrão'


class GrupoInteressado(models.ModelPlus):
    titulo = models.CharFieldPlus('Título', max_length=100, help_text='Informe um título para este grupo de interessados.')
    grupo_atendimento = models.ForeignKeyPlus(GrupoAtendimento, verbose_name='Grupo de Atendimento')
    interessados = models.ManyToManyFieldPlus(User, verbose_name='Interessados', related_name='grupointeressados_set')

    def __str__(self):
        return f'{self.titulo}'

    class Meta:
        ordering = ['titulo']
        verbose_name = 'Grupo de Interessados'
        verbose_name_plural = 'Grupos de Interessados'
