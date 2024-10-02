# -*- coding: utf-8 -*-
import os.path
from datetime import timedelta, date, datetime

from django.conf import settings
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F
from django.db.models.signals import m2m_changed
from django.forms.models import model_to_dict

from comum.models import AreaAtuacao, User
from comum.utils import formata_nome_arquivo
from comum.utils import tl
from djtools.db import models
from djtools.utils import send_notification
from gerenciador_projetos.enums import SituacaoProjeto, VisibilidadeProjeto, PrioridadeTarefa, TipoRecorrencia, \
    DiaDaSemana, MesDoAno


class Projeto(models.ModelPlus):
    """ areas e listas de tarefas """

    areas = models.ManyToManyFieldPlus(AreaAtuacao, verbose_name='Áreas de Atuação')
    titulo = models.CharFieldPlus('Título')
    descricao = models.TextField('Descrição')
    projeto_pai = models.ForeignKeyPlus('gerenciador_projetos.Projeto', verbose_name='Projeto Pai', null=True,
                                        blank=True, on_delete=models.CASCADE)
    uo = models.ForeignKeyPlus('rh.UnidadeOrganizacional', verbose_name='Campus',
                               related_name='gerenciador_projeto_campus')
    criado_em = models.DateTimeField(auto_now_add=True)
    criado_por = models.ForeignKeyPlus('comum.User', verbose_name='Criado Por',
                                       related_name='gerenciador_projeto_criado_por_set', blank=True)
    gerentes = models.ManyToManyField(
        'comum.User',
        verbose_name='Gerentes',
        related_name='gerenciador_projeto_gerentes_set'
    )
    interessados = models.ManyToManyField(
        'comum.User',
        verbose_name='Interessados',
        related_name='gerenciador_projeto_interessados_set',
        help_text='Interessados são usuários que possuem acesso de leitura a todas as informações do projeto.',
    )
    membros = models.ManyToManyField(
        'comum.User',
        verbose_name='Membros',
        related_name='gerenciador_projeto_membros_set',
        help_text='Membros são usuários que podem contribuir com o projeto no desenvolvimento de suas tarefas.',
    )
    visibilidade = models.CharFieldPlus('Visibilidade', default=VisibilidadeProjeto.PRIVADO,
                                        choices=VisibilidadeProjeto.choices)
    situacao = models.IntegerField('Situação', default=SituacaoProjeto.ABERTO, choices=SituacaoProjeto.choices)
    data_conclusao_estimada = models.DateFieldPlus('Data Estimada de Conclusão', null=True, blank=True)
    data_conclusao = models.DateFieldPlus('Data de Conclusão', null=True, blank=True)

    # origem = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['titulo']
        verbose_name = 'Projeto'
        verbose_name_plural = 'Projetos'

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return '/gerenciador_projetos/projeto/{}/'.format(self.id)

    def save(self, *args, **kwargs):
        insert = not self.pk
        super(Projeto, self).save(*args, **kwargs)
        if not insert and self.situacao == SituacaoProjeto.CONCLUIDO:
            for tarefa in self.tarefa_set.filter(data_conclusao__isnull=True):
                tarefa.fechar_tarefa()

    def clonar(self, user=None):
        if not user:
            user = tl.get_user()
        projeto = self

        tarefas = projeto.tarefas_raiz()
        tags = projeto.tag_set.all()
        projeto_listas = projeto.listaprojeto_set.all()
        areas = projeto.areas.all()

        projeto.id = None
        projeto.titulo = 'Cópia de {}'.format(projeto.titulo)
        projeto.criado_em = datetime.now()
        projeto.criado_por = user
        projeto.situacao = SituacaoProjeto.ABERTO
        projeto.save()

        projeto.gerentes.add(user)

        for area in areas:
            projeto.areas.add(area)

        # Clona todas as tags do projeto e armazena-as em um dicionário, onde
        # a chave é o pk da tag original e o valor é a tag correspondente clonada.
        dtags = {}
        for tag in tags:
            tagpk_ref = tag.pk
            tag.pk = None
            tag.save()
            dtags[tagpk_ref] = tag

        for projeto_lista in projeto_listas:
            projeto_lista.pk = None
            projeto_lista.projeto = projeto
            projeto_lista.save()

        for tarefa in tarefas:
            tarefa.projeto = projeto
            tarefa.clonar(user, dtags)

        return projeto

    def tarefas(self, tarefa=None):
        if tarefa:
            return self.tarefa_set.exclude(pk=tarefa.id)
        else:
            return self.tarefa_set.all()

    def tarefas_raiz(self):
        return self.tarefa_set.filter(tarefa_pai__isnull=True)

    def tarefas_sem_lista(self, filtros=None):
        tarefas = self.tarefa_set.filter(lista__isnull=True)
        if filtros:
            tarefas = tarefas.filter(**filtros)
        return tarefas

    def tarefas_por_lista(self, lista, filtros=None):
        tarefas = self.tarefa_set.filter(lista=lista)
        if filtros:
            tarefas = tarefas.filter(**filtros)
        return tarefas

    def listas_do_projeto(self):
        return self.listaprojeto_set.order_by('posicao')

    def total_progresso(self):
        # A contabilização do progresso do projeto irá considerar o seguinte
        # - Para a tarefa que tiver filhos a sua contabilização do % de progresso
        #   irá considerar apenas as suas tarefas filhas.
        # - Para a tarefa que não tem filhos a sua contabilização do % de progresso
        #   irá considerar apenas ela mesma
        # O calculo explicado ja esta na contabilizacao do progresso das tarefas
        # Assim, basta contabilizar as tarefas pai
        quantidade_tarefas = self.tarefas_raiz().count()
        if quantidade_tarefas > 0:
            soma_progressao_tarefas = 0
            for t in self.tarefas_raiz():
                soma_progressao_tarefas += t.total_progresso_numero()
            return '{:.0f}'.format((soma_progressao_tarefas / (quantidade_tarefas * 100)) * 100)
        return '{:.0f}'.format(0)

    def tarefas_ativas(self):
        return self.tarefa_set.filter(data_conclusao__isnull=True)

    def previsao_conclusao(self):
        d = {'titulo': '', 'valor': ''}
        if self.data_conclusao:
            d = {'titulo': 'Projeto concluído em', 'valor': self.data_conclusao}
        elif self.data_conclusao_estimada:
            if date.today() > self.data_conclusao_estimada:
                retorno = date.today() - self.data_conclusao_estimada
                d = {'titulo': 'Tempo ultrapassado', 'valor': timedelta(seconds=retorno.total_seconds())}
            else:
                retorno = self.data_conclusao_estimada - date.today()
                d = {'titulo': 'Conclusão prevista em', 'valor': timedelta(seconds=retorno.total_seconds())}
        return d

    def eh_gerente_projeto(self, user=None):
        if not user:
            user = tl.get_user()
        if user in self.gerentes.all():
            return True
        return False

    def eh_membro_projeto(self, user=None):
        if not user:
            user = tl.get_user()
        if user in self.membros.all():
            return True
        return False

    def eh_interessado_projeto(self, user=None):
        if not user:
            user = tl.get_user()
        if user in self.interessados.all():
            return True
        return False

    def pode_ver_projeto(self, user=None):
        if not user:
            user = tl.get_user()
        return self.eh_gerente_projeto(user) or self.eh_membro_projeto() or self.eh_interessado_projeto()

    def pode_editar_projeto(self, user=None):
        if not user:
            user = tl.get_user()
        return self.eh_gerente_projeto(user) or user.is_superuser

    def pode_adicionar_comentarios(self, user=None):
        if not user:
            user = tl.get_user()
        return self.eh_gerente_projeto(user) or self.eh_membro_projeto(user) or user.is_superuser

    def pode_adicionar_tarefas(self, user=None):
        if not user:
            user = tl.get_user()
        return self.eh_gerente_projeto(user) or self.eh_membro_projeto(user) or user.is_superuser

    def pode_editar_tarefas(self, user=None):
        if not user:
            user = tl.get_user()
        return self.eh_gerente_projeto(user) or self.eh_membro_projeto(user) or user.is_superuser

    def pode_adicionar_listas(self, user=None):
        if not user:
            user = tl.get_user()
        return self.eh_gerente_projeto(user) or user.is_superuser

    def pode_editar_listas(self, user=None):
        if not user:
            user = tl.get_user()
        return self.eh_gerente_projeto(user) or user.is_superuser

    def pode_editar_tags(self, user=None):
        if not user:
            user = tl.get_user()
        return self.eh_gerente_projeto(user) or user.is_superuser

    @property
    def concluido(self):
        return self.situacao == SituacaoProjeto.CONCLUIDO


class Tag(models.ModelPlus):
    COR_CHOICE = (
        ('#f1c40f', 'Amarelo'), ('#3498db', 'Azul'), ('#e67e22', 'Laranja'), ('#8e44ad', 'Roxo'), ('#2ecc71', 'Verde'),
        ('#e74c3c', 'Vermelho'), ('nenhum', 'Nenhum'))

    nome = models.CharFieldPlus('Nome', help_text='Informe um nome para tag')
    cor = models.CharFieldPlus('Cor', help_text='Informe uma cor para tag', choices=COR_CHOICE, default="info")
    projeto = models.ForeignKeyPlus(Projeto, verbose_name='Projeto')

    class Meta:
        ordering = ['nome']
        verbose_name = 'Tag'
        verbose_name_plural = 'Tags'

    def __str__(self):
        return self.nome


class Lista(models.ModelPlus):
    nome = models.CharFieldPlus('Nome', help_text='Informe um nome para a lista')
    ativa = models.BooleanField('Ativa', default=True, null=False)
    criada_por = models.ForeignKeyPlus('comum.User', verbose_name='Criada Por',
                                       related_name='gerenciador_projeto_criada_por_set', null=True, blank=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'Lista'
        verbose_name_plural = 'Listas'

    def __str__(self):
        return self.nome

    @classmethod
    def get_disponiveis(cls, usuario, projeto):
        return Lista.objects.filter(criada_por=usuario)

    def get_tarefas(self, projeto, filtros=None):
        """ Retorna uma Lista de Tarefas da Lista Corrente ordenada pela posição """
        tarefas = Tarefa.objects.filter(projeto=projeto, listatarefa__lista=self,
                                        listatarefa__data_hora_saida__isnull=True).annotate(posicao=F('listatarefa__posicao'))
        if filtros:
            tarefas = tarefas.filter(**filtros)
        return tarefas.order_by('posicao')


class TipoAtividade(models.ModelPlus):
    nome = models.CharFieldPlus('Nome')

    class Meta:
        ordering = ['nome']
        verbose_name = 'Tipo de Atividade'
        verbose_name_plural = 'Tipos de Atividade'

    def __str__(self):
        return self.nome


class Tarefa(models.ModelPlus):
    titulo = models.CharFieldPlus('Título')
    descricao = models.TextField('Descrição', null=True, blank=True)
    projeto = models.ForeignKeyPlus(Projeto, verbose_name='Projeto')
    tipo_atividade = models.ForeignKeyPlus(TipoAtividade, null=True, verbose_name='Tipo de Atividade')
    criado_por = models.ForeignKeyPlus('comum.User')
    atribuido_a = models.ManyToManyFieldPlus('comum.User', verbose_name='Atribuído a',
                                             related_name='gerenciador_tarefa_atribuido_a_set')
    atribuido_por = models.ForeignKeyPlus('comum.User', verbose_name='Atribuído por', null=True,
                                          related_name='gerenciador_tarefa_atribuido_por_set')
    prioridade = models.CharFieldPlus('Prioridade', max_length=10, default=PrioridadeTarefa.MEDIA,
                                      choices=PrioridadeTarefa.choices)
    aberto_em = models.DateTimeField('Aberto Em', auto_now_add=True)
    data_inicio = models.DateFieldPlus('Data de Início', null=True, blank=True)
    data_conclusao_estimada = models.DateFieldPlus('Data Estimada de Conclusão', null=True, blank=True)
    data_conclusao = models.DateFieldPlus('Data de Conclusão', null=True, blank=True)
    observadores = models.ManyToManyField(
        'comum.User',
        related_name='gerenciador_tarefa_observadores_set',
        verbose_name='Observadores',
        help_text='Vincule a esta tarefa usuários que podem ter interesse em acompanhar o andamento da mesma.',
    )
    tarefa_pai = models.ForeignKey(
        'gerenciador_projetos.Tarefa', verbose_name='Tarefa Pai', related_name='gerenciador_tarefa_pai_set', null=True,
        blank=True, on_delete=models.CASCADE
    )
    lista = models.ForeignKeyPlus(Lista, verbose_name='Lista', null=True, blank=True, on_delete=models.SET_NULL)
    tags = models.ManyToManyFieldPlus(
        Tag, related_name='gerenciador_projetos_tags_set', verbose_name='Tags', blank=True,
        help_text='Vincule tags nesta tarefa para facilitar a identificação da mesma.'
    )

    # origem = GenericForeignKey('content_type', 'object_id')

    class Meta:
        ordering = ['data_inicio', 'data_conclusao', 'pk']
        verbose_name = 'Tarefa'
        verbose_name_plural = 'Tarefas'

    def __str__(self):
        return self.titulo

    def __init__(self, *args, **kwargs):
        super(Tarefa, self).__init__(*args, **kwargs)
        self.__initial = self._dict

    def get_absolute_url(self):
        return '/gerenciador_projetos/tarefa/{}/'.format(self.id)

    def get_prioridade_css(self):
        retorno = 'alert'
        if self.prioridade == 'Alta':
            retorno = 'error'
        elif self.prioridade == 'Baixa':
            retorno = 'info'
        return retorno

    def get_situacao(self):
        hoje = date.today()
        retorno = 'Aberta'
        if self.data_conclusao and self.data_conclusao <= hoje:
            retorno = 'Concluída'
        elif self.possui_movimentacao():
            retorno = 'Em andamento'
        return retorno

    def get_historicoevolucao(self):
        return self.historicoevolucao_set.exclude(comentario__exact='').order_by('-data_hora')

    def get_anexos(self):
        return self.historicoevolucao_set.exclude(anexo__exact='')

    def get_subtarefas(self):
        return self.gerenciador_tarefa_pai_set.all()

    def get_subtarefas_nao_concluidas(self):
        return self.gerenciador_tarefa_pai_set.exclude(data_conclusao__isnull=False)

    def get_subtarefas_concluidas(self):
        return self.gerenciador_tarefa_pai_set.exclude(data_conclusao__isnull=True)

    def total_progresso_numero(self):
        quantidade_tarefas = self.get_subtarefas().count()
        percentual = 0
        if quantidade_tarefas:
            # Possui subtarefas
            # - Contabiliza considerando apenas as subtarefas
            percentual = 100 - (self.get_subtarefas_nao_concluidas().count() * 100) / (quantidade_tarefas)
        else:
            # Nao possui subtarefas
            # - Contabiliza considerando apenas ela mesma
            if self.get_situacao() == 'Concluída':
                percentual = 100
        return percentual

    def total_progresso(self):
        return '{:.0f}'.format(self.total_progresso_numero())

    def get_comentarios(self):
        return self.historicoevolucao_set.filter(mensagem_automatica=False).exclude(comentario__exact='')

    def get_listaatual(self):
        return self.listatarefa_set.get(data_hora_saida__isnull=True)

    def possui_movimentacao(self):
        if (
                self.get_subtarefas_nao_concluidas().exists()
                or self.get_comentarios().exists()
                or self.get_anexos().exists()
                or tl.get_user() in self.observadores.all()
                or self.data_conclusao
                or self.data_conclusao_estimada
                or self.atribuido_a.exists()
        ):
            return True
        else:
            return False

    def atribuir_para(self, users=None):
        tarefa = self
        tarefa.atribuido_a.add(users)
        tarefa.save()
        if users is not None:
            if not isinstance(users, list):
                users = [users]
            send_notification(
                assunto='[SUAP] Tarefa atribuída a você',
                mensagem=f'A terefa "{tarefa.titulo}" do projeto "{tarefa.projeto.titulo}" foi atribuída a você',
                de=settings.DEFAULT_FROM_EMAIL,
                vinculos=[u.get_vinculo() for u in users]
            )
        # Adiciona notificação de atribuição
        return tarefa

    @transaction.atomic()
    def reabrir(self, usuario):
        if self.projeto.concluido:
            raise ValidationError('Não é possível reabrir tarefa em um projeto concluído.')
        elif not self.concluida:
            raise ValidationError('A tarefa não está concluída para ser reaberta.')
        else:
            # Cria o histórico da Reabertura

            historico = HistoricoEvolucao()
            historico.tarefa = self
            historico.comentario = f"Tarefa reaberta por {usuario.get_vinculo().pessoa.nome}. " \
                                   f"Data da conclusão anterior era {self.data_conclusao.strftime('%d/%m/%Y')}."
            historico.registrado_por = usuario
            historico.mensagem_automatica = True
            historico.save()

            self.data_conclusao = None
            self.save()

            HistoricoEvolucao.objects.create(tarefa=self, registrado_por=tl.get_user(), mensagem_automatica=True,
                                             comentario='Tarefa reaberta')

    def clonar(self, user=None, dtags=None):
        '''
        :param user: usuário logado
        :param dtags: dicionário onde a chave é o pk da TAG anterior e o valor é o pk da nova TAG
        :return:
        '''
        tarefa = self
        subtarefas = self.get_subtarefas()
        tags = tarefa.tags.all()

        tarefa.data_inicio = datetime.now()
        tarefa.aberto_em = datetime.now()
        tarefa.data_conclusao = None
        tarefa.data_conclusao_estimada = None
        tarefa.id = None
        # Este método pode ser executado a partir do comando gp_tarefas_recorrentes ou a partir da funcionalidade clonar Projeto.
        # Quando o usário for informado, significa que o método foi executado a partir da funcionalidade clonar Projeto
        if user:
            tarefa.criado_por = user
            tarefa.data_inicio = None
            tarefa.lista = None
        tarefa.save()

        # Nova tarefa (tarefa clonada) referencia a nova tag correspondente.
        if dtags:
            for tag in tags:
                tarefa.tags.add(dtags[tag.pk])

        for subtarefa in subtarefas:
            print('tarefa:', tarefa, ', subtarefa:', subtarefa)
            subtarefa.projeto = tarefa.projeto
            subtarefa.tarefa_pai = tarefa
            subtarefa.clonar(user, dtags)
        return tarefa

    @property
    def _dict(self):
        return model_to_dict(self, fields=[field.name for field in self._meta.fields])

    @property
    def diff(self):
        d1 = self.__initial
        d2 = self._dict
        diffs = [(k, (v, d2[k])) for k, v in list(d1.items()) if v != d2[k]]
        return dict(diffs)

    @property
    def diff_verbose(self):
        retorno = ['<ul>']
        for str_field in self.changed_fields:
            field = Tarefa._meta.get_field(str_field)
            field_diff = self.get_field_diff(str_field)
            if field.is_relation:
                model = Tarefa._meta.get_field(str_field).related_model
                obj_antigo = 'vazio' if not field_diff[0] else model.objects.get(pk=field_diff[0])
                obj_novo = 'vazio' if not field_diff[1] else model.objects.get(pk=field_diff[1])
                retorno.append(
                    '<li>Campo <b>{}</b> alterado de <i>{}</i> para <i>{}</i>. </li>'.format(field.verbose_name,
                                                                                             obj_antigo, obj_novo))
            elif isinstance(field, models.DateField):
                data0 = 'vazio' if not field_diff[0] else field_diff[0].strftime('%d/%m/%Y')
                data1 = 'vazio' if not field_diff[1] else field_diff[1].strftime('%d/%m/%Y')
                retorno.append(
                    '<li>Campo <b>{}</b> alterado de <i>{}</i> para <i>{}</i>. </li>'.format(field.verbose_name, data0,
                                                                                             data1))
            else:
                retorno.append(
                    '<li>Campo <b>{}</b> alterado de <i>{}</i> para <i>{}</i>. </li>'.format(field.verbose_name,
                                                                                             field_diff[0],
                                                                                             field_diff[1]))
        retorno.append('</ul>')
        return ''.join(retorno)

    @property
    def has_changed(self):
        return bool(self.diff)

    @property
    def changed_fields(self):
        return list(self.diff.keys())

    @property
    def concluida(self):
        hoje = date.today()
        return self.data_conclusao and self.data_conclusao <= hoje

    def get_field_diff(self, field_name):
        """
        Returns a diff for field if it's changed and None otherwise.
        """
        return self.diff.get(field_name, 'vazio')

    def fechar_tarefa(self, data=None):
        if not data:
            data = date.today()
        self.data_conclusao = data

        HistoricoEvolucao.objects.create(tarefa=self, registrado_por=tl.get_user(), mensagem_automatica=True,
                                         comentario='Tarefa concluída')

        self.save()

    def save(self, *args, **kwargs):
        insert = not self.pk
        if not insert and self.get_field_diff('data_conclusao') != 'vazio':
            for tarefa in self.get_subtarefas_nao_concluidas():
                tarefa.fechar_tarefa()

        super(Tarefa, self).save(*args, **kwargs)

        if insert:
            HistoricoEvolucao.objects.create(tarefa=self, registrado_por=tl.get_user(), mensagem_automatica=True,
                                             comentario='Tarefa criada')

        if not insert and self.has_changed:
            HistoricoEvolucao.objects.create(tarefa=self, registrado_por=tl.get_user(), mensagem_automatica=True,
                                             comentario=self.diff_verbose)
        self.__initial = self._dict


def anexos_da_tarefa_path(instance, filename):
    filename = formata_nome_arquivo(filename)
    return 'gerenciador_projeto/projeto/{0}/tarefa_{1}/{2}'.format(instance.tarefa.projeto.id, instance.tarefa.id,
                                                                   filename)


class HistoricoEvolucao(models.ModelPlus):
    tarefa = models.ForeignKeyPlus(Tarefa, verbose_name='Tarefa')
    comentario = models.TextField('Comentário', null=True, blank=True)
    data_hora = models.DateTimeField(auto_now_add=True)
    registrado_por = models.ForeignKeyPlus('comum.User', verbose_name='Registrado Por',
                                           related_name='gerenciador_historico_evolucao_registrado_por_set')
    anexo = models.PrivateFileField(
        verbose_name='Anexo',
        upload_to=anexos_da_tarefa_path,
        filetypes=['pdf', 'jpeg', 'jpg', 'png'],
        help_text='O formato do arquivo deve ser ".pdf", ".jpeg", ".jpg" ou ".png"',
        null=True,
        blank=True,
    )
    historicoevolucao_pai = models.ForeignKey(
        'gerenciador_projetos.HistoricoEvolucao',
        verbose_name='Histórico de Evolução Pai',
        related_name='gerenciador_historicoevolucao_pai_set',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    data_conclusao = models.DateFieldPlus('Data de Conclusão', null=True, blank=True, help_text="Ao concluir esta tarefa, todas as suas subtarefas também serão concluídas")
    mensagem_automatica = models.BooleanField('Mensagem Automática?', default=False)

    def __str__(self):
        return 'Histórico de Evolução (Tarefa #{0}) - {1}'.format(self.tarefa.id, self.comentario)

    class Meta:
        ordering = ['tarefa', 'data_hora']
        verbose_name = 'Histórico de Evolução'
        verbose_name_plural = 'Histórico de Evolução'

    def nomeanexo(self):
        return os.path.basename(self.anexo.name)

    def clean(self):
        if not self.comentario and not self.anexo and not self.data_conclusao:
            raise ValidationError('É necessário informar pelo menos um dos campos para registrar a evolução.')

        if self.tarefa.concluida:
            raise ValidationError('Não é possível registrar histórico de evolução para tarefas concluídas.')

    def save(self, *args, **kwargs):
        if not self.comentario and self.anexo:
            self.comentario = 'Arquivo anexado.'
        super(HistoricoEvolucao, self).save(*args, **kwargs)
        if self.mensagem_automatica == False:
            if self.data_conclusao:
                self.tarefa.data_conclusao = self.data_conclusao
                self.tarefa.save()


class ListaTarefa(models.ModelPlus):
    lista = models.ForeignKeyPlus(Lista, verbose_name='Lista')
    tarefa = models.ForeignKeyPlus(Tarefa, verbose_name='Tarefa')
    posicao = models.PositiveSmallIntegerField('Posição')
    registrado_por = models.ForeignKeyPlus('comum.User', verbose_name='Registrado Por',
                                           related_name='gerenciador_lista_tarefa_registrado_por_set')
    data_hora_entrada = models.DateTimeField(auto_now_add=True)
    data_hora_saida = models.DateTimeField('Data/Hora Saída', null=True,
                                           help_text='Informa a data/hora que a tarefa foi removida desta lista.')

    class Meta:
        ordering = ['lista', 'posicao']
        verbose_name = 'Lista de Tarefas'
        verbose_name_plural = 'Listas de Tarefas'

    def __str__(self):
        return '{} - ({}) {}'.format(self.lista.nome, self.posicao, self.tarefa.titulo)


class ListaProjeto(models.ModelPlus):
    lista = models.ForeignKeyPlus(Lista, verbose_name='Lista')
    projeto = models.ForeignKeyPlus(Projeto, verbose_name='Projeto')
    posicao = models.PositiveSmallIntegerField('Posição')

    class Meta:
        ordering = ['lista', 'posicao']
        verbose_name = 'Lista de Tarefas Por Projeto'
        verbose_name_plural = 'Listas de Tarefas Por Projeto'

    def __str__(self):
        return '{} - ({}) {}'.format(self.lista.nome, self.posicao, self.projeto.titulo)


class RecorrenciaTarefa(models.ModelPlus):
    tarefa = models.ForeignKeyPlus(Tarefa, verbose_name='Tarefa')
    tipo_recorrencia = models.IntegerField('Tipo de Recorrência', choices=TipoRecorrencia.choices)
    dia_da_semana = models.PositiveSmallIntegerField('Dia da Semana', null=True, blank=True,
                                                     choices=DiaDaSemana.choices)
    dia_do_mes = models.PositiveSmallIntegerField('Dia do Mês', null=True, blank=True)
    mes_do_ano = models.PositiveSmallIntegerField('Mês do Ano', null=True, blank=True, choices=MesDoAno.choices)
    data_fim = models.DateFieldPlus('Data Final', null=True, blank=True)

    class Meta:
        ordering = ['tarefa', 'tipo_recorrencia']
        verbose_name = 'Recorrência da Tarefa'
        verbose_name_plural = 'Recorrências da Tarefa'

    def __str__(self):
        inicio = '{}'.format(self.get_tipo_recorrencia_display())
        fim = ''
        if self.tipo_recorrencia == TipoRecorrencia.SEMANALMENTE:
            fim = ', todas as {}'.format(self.get_dia_da_semana_display())
        elif self.tipo_recorrencia == TipoRecorrencia.MENSALMENTE:
            fim = ', dia {} de cada mês'.format(self.dia_do_mes)
        elif self.tipo_recorrencia == TipoRecorrencia.ANUALMENTE:
            fim = ', na data {}/{}'.format(self.dia_do_mes, self.mes_do_ano)

        return inicio + fim


""" signals """


def adiciona_permissao_apos_salvar_gerentes(sender, **kwargs):
    group = Group.objects.get(name='Gerente de Projeto')
    usuarios_sem_permissao = User.objects.filter(gerenciador_projeto_gerentes_set__isnull=False).exclude(groups=group)
    for user in usuarios_sem_permissao:
        user.groups.add(group)


m2m_changed.connect(adiciona_permissao_apos_salvar_gerentes, sender=Projeto.gerentes.through)


def adiciona_permissao_apos_salvar_membros(sender, **kwargs):
    group = Group.objects.get(name='Membro de Projeto')
    usuarios_sem_permissao = User.objects.filter(gerenciador_projeto_membros_set__isnull=False).exclude(groups=group)
    for user in usuarios_sem_permissao:
        user.groups.add(group)


m2m_changed.connect(adiciona_permissao_apos_salvar_membros, sender=Projeto.membros.through)


def adiciona_permissao_apos_salvar_interessados(sender, **kwargs):
    group = Group.objects.get(name='Interessado do Projeto')
    usuarios_sem_permissao = User.objects.filter(gerenciador_projeto_interessados_set__isnull=False).exclude(
        groups=group)
    for user in usuarios_sem_permissao:
        user.groups.add(group)


m2m_changed.connect(adiciona_permissao_apos_salvar_interessados, sender=Projeto.interessados.through)
