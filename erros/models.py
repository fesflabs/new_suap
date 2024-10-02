import datetime
from django.conf import settings

from comum.models import Preferencia, Vinculo
from django.db.models.aggregates import Count
from djtools.db import models
from djtools.templatetags.filters import in_group
from erros.utils import get_custom_view_name_from_url, comentar_erro_issue_gitlab, sincronizar_ferramentas
from erros.notificacoes import Notificar
from erros.utils import ferramentas_configuradas, get_modulo


class Erro(models.ModelPlus):
    SITUACAO_ABERTO = 1
    SITUACAO_EM_ANDAMENTO = 2
    SITUACAO_RESOLVIDO = 3
    SITUACAO_SUSPENSO = 4
    SITUACAO_CANCELADO = 5
    SITUACAO_REABERTO = 6
    SITUACAO_EM_CORRECAO = 7
    SITUACAO_UNIFICADO = 8
    SITUACAO_CHOICES = [
        [SITUACAO_ABERTO, 'Reportado'],
        [SITUACAO_EM_ANDAMENTO, 'Em análise'],
        [SITUACAO_EM_CORRECAO, 'Em correção'],
        [SITUACAO_RESOLVIDO, 'Resolvido'],
        [SITUACAO_SUSPENSO, 'Aguardando feedback'],
        [SITUACAO_CANCELADO, 'Cancelado'],
        [SITUACAO_REABERTO, 'Reaberto'],
        [SITUACAO_UNIFICADO, 'Unificado']
    ]
    SITUACOES_FINAIS = [SITUACAO_RESOLVIDO, SITUACAO_CANCELADO, SITUACAO_UNIFICADO]

    FUNCIONALIDADE = 'Funcionalidade'
    MANUTENCAO = 'Manutenção'
    BUG = 'Bug'
    TIPO_CHOICES = ((BUG, 'Bug'), (FUNCIONALIDADE, 'Funcionalidade'), (MANUTENCAO, 'Manutenção'), )

    SEARCH_FIELDS = ('id', 'url',)
    descricao = models.TextField(verbose_name='Descrição')
    url = models.TextField(verbose_name='URL com Erro')
    url_sentry = models.TextField(verbose_name='URL do Sentry', null=True, blank=True)
    sentry_issue_id = models.CharFieldPlus('Id da Issue do Sentry', null=True, blank=True)
    gitlab_issue_url = models.TextField(verbose_name='URL do Gitlab', null=True, blank=True)
    view = models.CharFieldPlus(verbose_name='View')
    maquina = models.TextField(verbose_name='Máquina', null=False, blank=True)
    informante = models.ForeignKeyPlus('comum.Vinculo', null=True, related_name='informantes_erros', verbose_name='Reportado por')
    situacao = models.IntegerField(choices=SITUACAO_CHOICES, verbose_name='Situação', default=SITUACAO_ABERTO)
    data_criacao = models.DateTimeFieldPlus(auto_now_add=True, verbose_name='Data de Criação')
    data_ultima_alteracao = models.DateTimeFieldPlus(auto_now=True, verbose_name='Data da Última Alteração')
    atendente_atual = models.ForeignKeyPlus('comum.Vinculo', null=True, blank=True, related_name='atendentes_erros', verbose_name='Atendente Atual')
    qtd_vinculos_afetados = models.IntegerField('Quantidade de Usuários Afetados', null=False, blank=False, default=1)
    titulo_atualizacao = models.CharFieldPlus(verbose_name='Título', null=True)
    tipo_atualizacao = models.CharFieldPlus(choices=TIPO_CHOICES, null=True, default=BUG, verbose_name='Tipo')
    grupos_atualizacao = models.ManyToManyFieldPlus('auth.Group', verbose_name='Grupos Envolvidos')
    ip_address = models.TextField(null=False, blank=True, verbose_name='Endereço IP')
    agent = models.TextField(null=False, blank=True, verbose_name='Navegador')
    atualizacao = models.OneToOneFieldPlus('demandas.Atualizacao', null=True, blank=True, verbose_name='Atualização')

    class Meta:
        verbose_name = 'Erro'
        verbose_name_plural = 'Erros'

    def __str__(self):
        return f'Erro {self.pk}: {self.modulo_afetado}'

    def get_absolute_url(self):
        return f'/erros/erro/{self.pk}/'

    def get_visualizar_erro_url(self):
        return f'{settings.SITE_URL}{self.get_absolute_url()}'

    @property
    def modulo_afetado(self):
        try:
            names = self.view.split('.')
            if names[0] == 'admin':
                return names[1] or 'admin'
            else:
                return names[0]
        except Exception:
            return 'djtools'

    @property
    def modulo_afetado_display(self):
        try:
            return get_modulo(self.modulo_afetado).verbose_name
        except Exception:
            return 'Erros'

    def criar(self):
        self.save()
        interessado = InteressadoErro()
        interessado.vinculo = self.informante
        interessado.erro = self
        preferencia = Preferencia.objects.filter(usuario=self.informante.user).first()
        interessado.tema = preferencia.tema if preferencia else Preferencia.PADRAO
        interessado.save()
        Notificar.criar_erro(self)

    def get_vinculos_interessados(self):
        if not hasattr(self, 'vinculos_interessados'):
            self.vinculos_interessados = Vinculo.objects.filter(pk__in=self.interessadoerro_set.filter(ativo=True).values_list('vinculo', flat=True))
        return self.vinculos_interessados

    def get_vinculos_atendentes(self):
        atendentes = [atendente.vinculo for atendente in self.get_outros_atendentes()]
        if self.atendente_atual:
            atendentes.append(self.atendente_atual)
        return atendentes

    def get_vinculos_gerentes(self):
        return list(Vinculo.objects.filter(user__usuariogrupo__group__name='Recebedor de Demandas'))

    def get_notificados(self, ignorado=None, so_atendentes=False):
        notificados = self.get_vinculos_atendentes() or self.get_vinculos_gerentes()
        if not so_atendentes:
            notificados += self.get_vinculos_interessados()
        return [x for x in set(notificados) if x is not None and x != ignorado]

    def vinculo_eh_atendente_atual(self, vinculo):
        return self.atendente_atual == vinculo

    def vinculo_pode_ser_atendente(self, vinculo):
        return in_group(vinculo.user, 'Desenvolvedor', ignore_if_superuser=False)

    def vinculo_eh_interessado(self, vinculo):
        return vinculo in self.get_vinculos_interessados()

    def pode_assumir(self, vinculo):
        return self.situacao not in self.SITUACOES_FINAIS and self.vinculo_pode_ser_atendente(vinculo) and not self.vinculo_eh_atendente_atual(vinculo)

    def pode_sincronizar_gitlab(self, vinculo):
        return self.situacao not in self.SITUACOES_FINAIS and ferramentas_configuradas() and self.vinculo_pode_ser_atendente(vinculo) and not self.gitlab_issue_url and self.sentry_issue_id

    def pode_criar_issue_gitlab(self, vinculo):
        return self.situacao not in self.SITUACOES_FINAIS and ferramentas_configuradas() and self.vinculo_pode_ser_atendente(vinculo) and not self.gitlab_issue_url and not self.gitlab_issue_url

    def pode_devolver(self, vinculo):
        return self.situacao not in self.SITUACOES_FINAIS and self.vinculo_eh_atendente_atual(vinculo) and self.situacao not in self.SITUACOES_FINAIS

    def pode_atribuir(self, vinculo):
        return self.situacao not in self.SITUACOES_FINAIS and in_group(vinculo.user, 'Recebedor de Demandas', ignore_if_superuser=False)

    def pode_unificar(self, vinculo):
        return self.situacao not in self.SITUACOES_FINAIS and in_group(vinculo.user, 'Recebedor de Demandas', ignore_if_superuser=False)

    def pode_comentar(self, vinculo):
        return self.situacao not in self.SITUACOES_FINAIS and (self.vinculo_eh_interessado(vinculo) or self.vinculo_pode_ser_atendente(vinculo))

    def pode_comentar_nota_interna(self, vinculo):
        return self.situacao not in self.SITUACOES_FINAIS and self.vinculo_pode_ser_atendente(vinculo)

    def pode_se_interessar(self, vinculo):
        return vinculo not in self.get_vinculos_interessados() and not vinculo.eh_aluno() and self.situacao not in self.SITUACOES_FINAIS

    def pode_se_desinteressar(self, vinculo):
        return vinculo in self.get_vinculos_interessados() and vinculo != self.informante and self.situacao not in self.SITUACOES_FINAIS

    def pode_ver_comentarios(self, vinculo):
        return self.vinculo_eh_interessado(vinculo) or self.vinculo_pode_ser_atendente(vinculo)

    def pode_ver_nota_interna(self, vinculo):
        return self.vinculo_pode_ser_atendente(vinculo)

    def pode_alterar_url(self, vinculo):
        return self.vinculo_eh_atendente_atual(vinculo) and self.situacao not in self.SITUACOES_FINAIS

    def pode_editar_atualizacao(self, vinculo):
        return self.vinculo_pode_ser_atendente(vinculo) and self.situacao not in self.SITUACOES_FINAIS and 'demandas' in settings.INSTALLED_APPS

    def pode_alterar_situacao(self, vinculo):
        return self.get_situacoes_disponiveis(vinculo) and self.vinculo_eh_atendente_atual(vinculo)

    def get_situacoes_disponiveis(self, vinculo):
        eh_atendente = self.vinculo_eh_atendente_atual(vinculo)
        eh_informante = self.informante == vinculo
        if not eh_atendente and not eh_informante:
            return []
        if self.situacao in [self.SITUACAO_ABERTO, self.SITUACAO_REABERTO]:
            if eh_atendente:
                return [self.SITUACAO_EM_ANDAMENTO, self.SITUACAO_EM_CORRECAO, self.SITUACAO_CANCELADO]
            else:
                return []
        elif self.situacao == self.SITUACAO_EM_ANDAMENTO:
            if eh_atendente:
                return [self.SITUACAO_EM_CORRECAO, self.SITUACAO_RESOLVIDO, self.SITUACAO_SUSPENSO, self.SITUACAO_CANCELADO]
            else:
                return []
        elif self.situacao == self.SITUACAO_EM_CORRECAO:
            if eh_atendente:
                return [self.SITUACAO_EM_ANDAMENTO, self.SITUACAO_RESOLVIDO, self.SITUACAO_SUSPENSO, self.SITUACAO_CANCELADO]
            else:
                return []
        elif self.situacao == self.SITUACAO_SUSPENSO:
            if eh_atendente:
                return [self.SITUACAO_EM_ANDAMENTO, self.SITUACAO_EM_CORRECAO, self.SITUACAO_RESOLVIDO, self.SITUACAO_CANCELADO]
            else:
                return []
        elif self.situacao in [self.SITUACAO_CANCELADO, self.SITUACAO_RESOLVIDO]:
            return [self.SITUACAO_REABERTO]

    def get_outros_atendentes(self):
        return self.atendenteerro_set.exclude(vinculo=self.atendente_atual)

    def get_outros_interessados(self):
        if not hasattr(self, 'outros_interessados'):
            self.outros_interessados = self.interessadoerro_set.exclude(vinculo=self.informante).exclude(ativo=False)
        return self.outros_interessados

    def devolver(self, vinculo):
        if self.pode_devolver(vinculo):
            self.atendente_atual = None
            self.save()
            HistoricoComentarioErro.objects.create(erro=self, descricao='devolveu o atendimento.', vinculo=vinculo, automatico=True)

    def atribuir(self, atribuinte, atribuido):
        if self.pode_atribuir(atribuinte):
            self.atendente_atual = atribuido
            self.save()
            HistoricoComentarioErro.objects.create(erro=self, descricao=f'habilitou {atribuido} como atendente principal.', vinculo=atribuinte, automatico=True)
            self.gerenciar_atendente(atribuido, mensagem_customizada='', forcar_assumir=True)
            Notificar.atribuir_erro(self, atribuinte)

    def unificar(self, vinculo, erros):
        if self.pode_unificar(vinculo):
            urls = []
            url_principal = f'<a href={self.get_absolute_url()}>#{self.pk}</a>'
            for erro in erros:
                for interessado in erro.interessadoerro_set.filter(ativo=True):
                    self.gerenciar_interessado(interessado.vinculo, mensagem_customizada=f'foi adicionado como interessado por {vinculo}.', tema=interessado.tema)
                HistoricoComentarioErro.objects.create(erro=self, descricao=erro.descricao, vinculo=erro.informante)
                erro.situacao = erro.SITUACAO_UNIFICADO
                erro.save()

                descricao = f'unificou este erro com o erro {url_principal}.'
                HistoricoComentarioErro.objects.create(erro=erro, descricao=descricao, vinculo=vinculo, automatico=True)
                url = f'<a href={erro.get_absolute_url()}>#{erro.pk}</a>'
                urls.append(url)

            descricao = f'unificou este erro com os erros: {" ".join(urls)}.'
            HistoricoComentarioErro.objects.create(erro=self, descricao=descricao, vinculo=vinculo, automatico=True)

    def comentar(self, vinculo, descricao, tipo, automatico=False):
        self.gerenciar_atendente(vinculo)
        comentario = HistoricoComentarioErro.objects.create(erro=self, descricao=descricao, vinculo=vinculo, tipo=tipo, automatico=automatico)
        Notificar.comentar_erro(comentario)
        if self.situacao == self.SITUACAO_SUSPENSO and vinculo in self.get_vinculos_interessados():
            HistoricoComentarioErro.objects.create(erro=self, descricao='Situação alterada automaticamente pelo sistema para Em análise.', automatico=True)
            self.situacao = self.SITUACAO_EM_ANDAMENTO
            self.save()

    def anexar(self, anexado_por, descricao, arquivo):
        self.gerenciar_atendente(anexado_por)
        anexo = AnexoErro.objects.create(erro=self, descricao=descricao, anexado_por=anexado_por, arquivo=arquivo)
        descricao_comentario = f'adicionou o anexo <a href="{anexo.arquivo.url}">{descricao}</a>'
        HistoricoComentarioErro.objects.create(erro=self, descricao=descricao_comentario, vinculo=anexado_por, tipo=HistoricoComentarioErro.TIPO_COMENTARIO, automatico=True)
        Notificar.adicionar_anexo(anexo)

    def editar_atualizacao(self, desenvolvedor=None):
        from demandas.models import Atualizacao, Tag
        atualizacao = self.atualizacao or Atualizacao()
        if atualizacao and self.titulo_atualizacao and self.tipo_atualizacao and self.grupos_atualizacao.exists():
            atualizacao.descricao = self.titulo_atualizacao
            atualizacao.tipo = self.tipo_atualizacao
            atualizacao.data = datetime.datetime.now().today()
            atualizacao.save()
            self.atualizacao = atualizacao
            self.save()
            tag, _ = Tag.objects.get_or_create(nome=self.modulo_afetado_display, defaults=dict(sigla=self.modulo_afetado))
            atualizacao.tags.add(tag)
            atualizacao.responsaveis.clear()
            if desenvolvedor is None:
                atualizacao.responsaveis.add(self.atendente_atual.user)
            else:
                atualizacao.responsaveis.add(desenvolvedor)
            atualizacao.grupos.clear()
            for grupo in self.grupos_atualizacao.all():
                atualizacao.grupos.add(grupo)

    def gerenciar_situacao(self, vinculo, situacao, motivo=None, mensagem_customizada=None):
        descricao_situacao = Erro(situacao=situacao).get_situacao_display()
        descricao = mensagem_customizada
        if not mensagem_customizada:
            descricao = f'alterou a situação para: {descricao_situacao}.'
        HistoricoComentarioErro.objects.create(erro=self, descricao=descricao, vinculo=vinculo, automatico=True)
        self.situacao = situacao
        self.save()
        if motivo:
            HistoricoComentarioErro.objects.create(erro=self, descricao=motivo, vinculo=vinculo)
        if situacao == self.SITUACAO_RESOLVIDO:
            conf = ferramentas_configuradas()
            if conf:
                sincronizar_ferramentas(self, conf, force_close=True)
            else:
                self.editar_atualizacao()
        Notificar.alterar_situacao_erro(self, vinculo, motivo)

    def gerenciar_atendente(self, vinculo, mensagem_customizada=None, forcar_assumir=False):
        if self.vinculo_pode_ser_atendente(vinculo):
            atendente, criado = AtendenteErro.objects.get_or_create(vinculo=vinculo, erro=self)
            descricao = mensagem_customizada
            if not self.atendente_atual or forcar_assumir:
                self.atendente_atual = vinculo
                self.save()
                if mensagem_customizada is None:
                    descricao = 'se habilitou como atendente principal.'
            elif criado:
                if mensagem_customizada is None:
                    descricao = 'se habilitou como atendente auxiliar.'
            if descricao:
                HistoricoComentarioErro.objects.create(erro=self, descricao=descricao, vinculo=vinculo, automatico=True)
            if self.situacao in [self.SITUACAO_REABERTO, self.SITUACAO_ABERTO]:
                self.gerenciar_situacao(vinculo, situacao=self.SITUACAO_EM_ANDAMENTO)

    def alterar_url(self, vinculo, url, tipo, issue_id):
        url_antiga = ''
        visibilidade = HistoricoComentarioErro.VISIBILIDADE_INTERESSADOS
        if tipo == 'erro':
            url_antiga = self.url
            self.url = url
            self.view = get_custom_view_name_from_url(url)
        elif tipo == 'sentry':
            url_antiga = self.url_sentry
            self.url_sentry = url
            self.sentry_issue_id = issue_id
            visibilidade = HistoricoComentarioErro.VISIBILIDADE_ATENDENTES
        elif tipo == 'gitlab':
            url_antiga = self.gitlab_issue_url
            self.gitlab_issue_url = url
            visibilidade = HistoricoComentarioErro.VISIBILIDADE_ATENDENTES
        if not url_antiga:
            url_antiga = ''
        if url_antiga != url:
            url_antiga = url_antiga or 'vazio'
            url = url or 'vazio'
            self.save()
            descricao = f'alterou a URL do {tipo} de {url_antiga} para {url}.'
            if tipo == 'gitlab':
                conf = ferramentas_configuradas()
                comentar_erro_issue_gitlab(self, conf)
            HistoricoComentarioErro.objects.create(erro=self, descricao=descricao, vinculo=vinculo, automatico=True, visibilidade=visibilidade)

    def gerenciar_interessado(self, vinculo, habilitar=True, mensagem_customizada=None, tema=''):
        interessado, criado = InteressadoErro.objects.get_or_create(vinculo=vinculo, erro=self, defaults={'tema': tema})
        descricao = mensagem_customizada
        if criado:
            if not mensagem_customizada:
                descricao = 'se habilitou como interessado.'
        else:
            if habilitar and not interessado.ativo:
                if not mensagem_customizada:
                    descricao = 'se habilitou novamente como interessado.'
                interessado.ativo = True
                interessado.save()
            elif not habilitar and interessado.ativo:
                if not mensagem_customizada:
                    descricao = 'se desabilitou como interessado.'
                interessado.ativo = False
                interessado.save()
            else:
                descricao = None

        self.qtd_vinculos_afetados = InteressadoErro.objects.filter(erro=self, ativo=True).count()
        self.save()
        if descricao:
            HistoricoComentarioErro.objects.create(erro=self, descricao=descricao, vinculo=vinculo, automatico=True)
        return interessado

    def cancelar_automatico(self):
        HistoricoComentarioErro.objects.create(erro=self, descricao='Erro cancelado automaticamente por falta de feedback.', automatico=True)
        self.situacao = self.SITUACAO_CANCELADO
        self.save()

    def get_temas_e_contadores_erro(self):
        return self.interessadoerro_set.filter(ativo=True).exclude(tema='').values('tema').annotate(total=Count('tema')).values_list('tema', 'total')


class InteressadoErro(models.ModelPlus):
    vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Interessado')
    erro = models.ForeignKeyPlus('erros.Erro')
    tema = models.CharFieldPlus(verbose_name='Tema ao ser vinculado ao erro', null=False, blank=True, default='')
    ativo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('vinculo', 'erro')

    def save(self, *args, **kwargs):
        if not self.tema:
            preferencia = Preferencia.objects.filter(usuario=self.vinculo.user).first()
            self.tema = preferencia.tema if preferencia else Preferencia.PADRAO

        super().save(*args, **kwargs)


class AtendenteErro(models.ModelPlus):
    vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Interessado')
    erro = models.ForeignKeyPlus('erros.Erro')
    ativo = models.BooleanField(default=True)

    class Meta:
        unique_together = ('vinculo', 'erro')


class HistoricoComentarioErro(models.ModelPlus):
    TIPO_COMENTARIO = 'comentario'
    TIPO_NOTA_INTERNA = 'nota_interna'

    VISIBILIDADE_INTERESSADOS = 'interessados'
    VISIBILIDADE_ATENDENTES = 'atendentes'

    TIPO_CHOICES = ((TIPO_COMENTARIO, 'Comentário'), (TIPO_NOTA_INTERNA, 'Nota Interna'))
    VISIBILIDADE_CHOICES = ((VISIBILIDADE_INTERESSADOS, 'Interessados e Atendentes'), (VISIBILIDADE_ATENDENTES, 'Atendentes'))

    erro = models.ForeignKeyPlus('erros.Erro')
    descricao = models.TextField(verbose_name='Tipo')
    vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Atendente', null=True)
    automatico = models.BooleanField(default=False)
    ativo = models.BooleanField(default=True)
    tipo = models.CharFieldPlus(choices=TIPO_CHOICES, default=TIPO_COMENTARIO)
    data_alteracao = models.DateTimeFieldPlus(auto_now_add=True)
    visibilidade = models.CharFieldPlus(choices=VISIBILIDADE_CHOICES, default=VISIBILIDADE_INTERESSADOS)

    class Meta:
        ordering = ('-data_alteracao',)

    def pode_desconsiderar_comentario(self, vinculo):
        return self.ativo and self.erro.pode_comentar(vinculo) and vinculo == self.vinculo

    def pode_ver(self, vinculo):
        return self.visibilidade == self.VISIBILIDADE_ATENDENTES and self.erro.vinculo_pode_ser_atendente(vinculo) or self.visibilidade == self.VISIBILIDADE_INTERESSADOS

    def desconsiderar_comentario(self):
        self.ativo = False
        self.save()


class AnexoErro(models.ModelPlus):
    erro = models.ForeignKeyPlus('erros.Erro')
    descricao = models.CharFieldPlus('Descrição', max_length=80, null=False, blank=False, help_text='Informe uma descrição resumida sobre o arquivo anexado')
    arquivo = models.FileFieldPlus(
        max_length=255,
        upload_to='erros/anexos/',
        filetypes=['xls', 'csv', 'doc', 'pdf', 'jpg', 'png'],
        create_date_subdirectories=True
    )
    ativo = models.BooleanField(default=True)

    anexado_por = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Anexado por', null=False, blank=False)
    anexado_em = models.DateTimeFieldPlus(verbose_name='Anexado em', auto_now_add=True, null=False, blank=False)
