import datetime
import os

import numpy as np
from django.db import transaction
from django.db.models.aggregates import Max, Count
from django.template.defaultfilters import linebreaksbr
from django.utils.safestring import mark_safe

from comum.models import Publico, Vinculo
from djtools.db import models
from djtools.html.graficos import PieChart
from rh.models import UnidadeOrganizacional


class Enquete(models.ModelPlus):
    tag = models.CharFieldPlus('Tag', default='Responda à Enquete', help_text='Tag que será usada na tela inicial do questionário/enquete.')
    titulo = models.CharFieldPlus('Título')
    descricao = models.TextField('Descrição')
    data_inicio = models.DateTimeFieldPlus('Data de Início')
    data_fim = models.DateTimeFieldPlus('Data de Término')
    vinculos_relacionados_enquete = models.ManyToManyFieldPlus('comum.Vinculo', verbose_name='Vínculos Relacionados', related_name='vinculos_relacionados_enquete', blank=True)
    vinculos_responsaveis = models.ManyToManyFieldPlus('comum.Vinculo', related_name='vinculos_responsaveis_enquetes', verbose_name='Responsável(is)', blank=True)
    publicada = models.BooleanField(default=False)
    manter_enquete_inicio = models.BooleanField('Manter Enquete na Tela Inicial', default=False, help_text='Se esta opção ficar desmarcada, quando um usuário responder a enquete, ela não vai mais aparecer na tela inicial para ele.')
    resultado_publico = models.BooleanField(
        'Resultado Público', default=False, help_text='No resultado dessa enquete irá aparecer quem respondeu (somente para Responsáveis pela Enquete).'
    )
    instrucoes = models.FileFieldPlus(verbose_name='Anexo', upload_to='enquete/instrucoes/', null=True, blank=True)
    descricao_anexo = models.CharFieldPlus(verbose_name='Descrição do Anexo', default='Instruções da Enquete', blank=True)
    texto_orientacao = models.TextField('Texto de Orientação', blank=True)
    vinculos_publico = models.ManyToManyFieldPlus('comum.Vinculo', related_name='vinculos_publico', verbose_name='Vínculos Público', blank=True)

    class Meta:
        verbose_name = 'Enquete'
        verbose_name_plural = 'Enquetes'

    def __str__(self):
        return self.titulo

    def get_absolute_url(self):
        return "/enquete/enquete/{}/".format(self.id)

    def save(self, *args, **kargs):
        if self.pk:
            if not self.pode_publicar() and self.publicada:
                self.publicada = False
            self.vinculos_publico.set(self.get_publicos())

        super().save(*args, **kargs)

    def get_instrucoes(self):
        return os.path.basename(self.instrucoes.name)

    def get_perguntas_agrupadas_por_categoria(self):
        categorias = self.get_categorias()
        for categoria in categorias:
            categoria.perguntas = self.pergunta_set.filter(categoria=categoria).order_by('ordem')
            categoria.cabecalho = [pergunta for pergunta in categoria.perguntas]
        return categorias

    def get_categorias(self):
        return self.categoria_set.order_by('ordem')

    def get_vinculos_relacionados_enquete(self):
        vinculos_relacionados_enquete = []
        for vinculo_publico in self.vinculos_relacionados_enquete.all():
            vinculos_relacionados_enquete.append(str(vinculo_publico))

        return ', '.join(vinculos_relacionados_enquete)

    def get_opcoes(self):
        return self.opcao_set.filter(opcaopergunta__isnull=True)

    def get_publicos(self):
        publicos = self.vinculos_relacionados_enquete.all().distinct()
        for publico_campi in self.publicocampi_set.all():
            publicos |= publico_campi.publico.get_queryset_vinculo(publico_campi.campi, publico_campi.tipo_setor)

        return publicos.distinct()

    def get_publico_str(self):
        retorno = list()
        for publico_campi in self.publicocampi_set.all():
            retorno.append('{}'.format(publico_campi))

        if self.vinculos_relacionados_enquete.exists():
            retorno.append('Vínculos Específicos')

        return ', '.join(retorno)

    def eh_parte_publico(self, vinculo):
        return self.vinculos_publico.filter(id=vinculo.id).exists()

    def respondeu(self, vinculo):
        return vinculo.enquete_resposta_vinculo.filter(pergunta__enquete=self).exists()

    def respondeu_todas_as_perguntas(self, vinculo):
        qtd_perguntas = self.pergunta_set.all().count()
        qtd_perguntas_respondidas = self.pergunta_set.filter(resposta__vinculo=vinculo).distinct().count()
        return qtd_perguntas_respondidas == qtd_perguntas

    def pode_responder(self, vinculo):
        return self.publicada and self.data_inicio <= datetime.datetime.today() <= self.data_fim and self.eh_parte_publico(vinculo)

    @classmethod
    def get_abertas(cls, vinculo):
        enquetes_abertas = set()
        enquetes = Enquete.objects.filter(data_inicio__lte=datetime.datetime.today(), data_fim__gte=datetime.datetime.today(), publicada=True)
        for enquete in enquetes:
            if enquete.eh_parte_publico(vinculo):
                enquetes_abertas.add(enquete)

        return enquetes_abertas

    def get_respostas_objetivas(self, vinculo):
        qs = Resposta.objects.filter(pergunta__enquete=self, pergunta__objetiva=True)
        qs = qs.filter(vinculo=vinculo)
        return qs

    def eh_responsavel(self, user):
        return user.is_superuser or self.vinculos_responsaveis.filter(id=user.get_vinculo().id).exists()

    def tem_pergunta_sem_opcao(self):
        return self.pergunta_set.filter(objetiva=True, opcoes__isnull=True).exists() and not self.opcao_set.filter(opcaopergunta__isnull=True).exists()

    def get_descricao(self):
        return mark_safe(linebreaksbr(self.descricao))

    def pode_publicar(self):
        retorno = False
        if self.pergunta_set.exists():
            if self.pergunta_set.filter(objetiva=True).exists():
                retorno = not self.tem_pergunta_sem_opcao()
            else:
                retorno = True
        if not self.vinculos_relacionados_enquete.exists() and not self.publicocampi_set.exists():
            retorno = False
        return retorno

    def get_participantes(self):
        return Vinculo.objects.filter(enquete_resposta_vinculo__pergunta__enquete=self).annotate(data_cadastro=Max('enquete_resposta_vinculo__data_cadastro')).distinct()

    def get_status(self):
        if self.publicada:
            hoje = datetime.datetime.now()
            if self.data_inicio > hoje:
                return mark_safe('<span class="status status-alert">Aguardando publicação</span>')
            elif self.data_fim >= hoje:
                return mark_safe('<span class="status status-success">Publicada</span>')
            else:
                return mark_safe('<span class="status status-error">Expirada</span>')
        else:
            return mark_safe('<span class="status status-error">Privada</span>')

    def get_graficos_resultado(self, participantes, task):
        graficos = list()

        self.categorias = self.get_perguntas_agrupadas_por_categoria()
        task.count(self.categorias)
        i = 0
        for categoria in self.categorias:
            categoria.cabecalho = []
            respostas = []
            for pergunta in categoria.perguntas:
                pergunta.respostas = pergunta.resposta_set.filter(vinculo__in=participantes).order_by(
                    'data_cadastro', 'vinculo__pessoa__nome'
                )
                if pergunta.objetiva:
                    opcoes = pergunta.get_opcoes()
                    pergunta.resultado_opcoes = opcoes
                    dados_grafico = list()
                    dados = pergunta.respostas.order_by('opcao__id').values('opcao__id').annotate(count=Count('opcao__id'))
                    # Removendo o order_by porque estava entrando no group_by e gerando agregações incorretas
                    for opcao in opcoes:
                        dados_opcao = dados.filter(opcao__id=opcao.id).first()
                        opcao.qtd = dados_opcao and dados_opcao['count'] or 0
                        dados_grafico.append([opcao.texto, opcao.qtd])

                    grafico = PieChart('grafico_pergunta_{:d}'.format(pergunta.id), title=pergunta.get_html(), data=dados_grafico)
                    grafico.id = 'grafico_pergunta_{:d}'.format(pergunta.id)
                    pergunta.grafico_id = grafico.id
                    graficos.append(grafico)

                categoria.cabecalho.append(pergunta)
                pergunta.respostas_dict = pergunta.get_respostas_dict()

                for participante in participantes:
                    if participante.id in pergunta.respostas_dict:
                        respostas.append(pergunta.respostas_dict[participante.id])
                    else:
                        respostas.append('-')

            x = len(categoria.cabecalho)
            if x > 0:
                y = len(respostas) / x
                array_respostas = np.array(respostas)
                categoria.tabela = array_respostas.reshape(x, int(y)).transpose().tolist()
            i += 1
            task.update_progress(i)
        return graficos

    def can_change(self, user):
        return self.eh_responsavel(user)


class PublicoCampi(models.ModelPlus):
    enquete = models.ForeignKeyPlus(Enquete, on_delete=models.CASCADE)
    publico = models.ForeignKeyPlus(Publico, verbose_name='Público', on_delete=models.CASCADE)
    campi = models.ManyToManyFieldPlus('rh.UnidadeOrganizacional', verbose_name='Campi')
    tipo_setor = models.CharFieldPlus(
        'Tipo de Setor do Funcionario/Servidor',
        choices=Publico.TIPO_SETOR_CHOICES,
        default=Publico.TIPO_SETOR_SUAP,
        help_text='Este setor será levado em consideração com relação aos campi escolhidos',
    )

    class Meta:
        verbose_name = 'Público Campi'
        verbose_name_plural = 'Públicos Campi'

    def __str__(self):
        if self.id:  # if/else para evitar BUG de recursividade ao remover `self` pelo admin
            siglas = self.campi.all().values_list('sigla', flat=True)
        else:
            siglas = []
        return ' {} ({})'.format(self.publico, ', '.join(siglas))


class Categoria(models.ModelPlus):
    enquete = models.ForeignKeyPlus(Enquete, on_delete=models.CASCADE)
    texto = models.TextField()
    orientacao = models.TextField('Orientação da Categoria', blank=True, help_text='Texto de orientação da Categoria da Enquete')
    ordem = models.IntegerField()

    class Meta:
        verbose_name = 'Categoria de Enquete'
        verbose_name_plural = 'Categorias de Enquete'

    def __str__(self):
        return self.texto

    def get_html(self):
        return mark_safe(linebreaksbr(self.texto))

    @transaction.atomic
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.enquete.save()  # para despublicar se for o caso


class Pergunta(models.ModelPlus):
    TABELA = 'tabela'
    LISTA = 'lista'
    GALERIA = 'galeria'
    TIPO_LAYOUT = ((TABELA, 'Tabela'), (LISTA, 'Lista'), (GALERIA, 'Galeria'))

    enquete = models.ForeignKeyPlus(Enquete, on_delete=models.CASCADE)
    categoria = models.ForeignKeyPlus(Categoria, on_delete=models.CASCADE)
    layout = models.CharFieldPlus(verbose_name='Layout das Respostas', blank=True, choices=TIPO_LAYOUT, default=LISTA, help_text='Válido somente para perguntas objetivas')
    texto = models.TextField(verbose_name='Título da Pergunta')
    numerico = models.BooleanField(
        'Campo Numérico', blank=True, default=False, help_text='Marque este campo caso a resposta deva ser apenas numérica, em caso de pergunta subjetiva.'
    )
    objetiva = models.BooleanField(default=True)
    multipla_escolha = models.BooleanField(verbose_name='Múltipla Escolha', default=False)
    ordem = models.IntegerField()
    obrigatoria = models.BooleanField(verbose_name='Obrigatória', default=False)

    class Meta:
        verbose_name = 'Pergunta'
        verbose_name_plural = 'Perguntas'
        ordering = ('ordem', 'id')

    def __str__(self):
        return self.texto

    def get_resposta(self, vinculo):
        respostas = self.resposta_set.filter(vinculo=vinculo)
        if not respostas.exists():
            return None

        if self.objetiva:
            if self.multipla_escolha:
                return list(respostas.values_list('opcao_id', flat=True))
            else:
                return respostas[0].opcao_id
        else:
            return respostas[0].resposta

    def salvar_resposta(self, vinculo, resposta_atual):
        uo = vinculo.setor.uo

        respostas = self.resposta_set.filter(vinculo=vinculo)
        if respostas.exists():
            if self.multipla_escolha:
                respostas_atuais = respostas.filter(opcao__in=resposta_atual)
                respostas_excluidas = respostas.exclude(opcao__in=resposta_atual)
                respostas_excluidas.delete()
                novas_respostas = resposta_atual.exclude(id__in=respostas_atuais.values_list('opcao', flat=True))
                for opcao in novas_respostas:
                    resposta = Resposta()
                    resposta.pergunta = self
                    resposta.resposta = ''
                    resposta.vinculo = vinculo
                    resposta.uo = uo
                    resposta.opcao = opcao
                    resposta.data_ultima_resposta = datetime.datetime.now()
                    resposta.save()
            else:
                if self.objetiva:
                    resposta = respostas[0]
                    resposta.opcao = resposta_atual
                else:
                    resposta = respostas[0]
                    resposta.resposta = resposta_atual

                resposta.data_ultima_resposta = datetime.datetime.now()
                resposta.uo = uo
                resposta.save()
        else:
            if self.multipla_escolha:
                for opcao in resposta_atual:
                    resposta = Resposta()
                    resposta.pergunta = self
                    resposta.resposta = ''
                    resposta.vinculo = vinculo
                    resposta.uo = uo
                    resposta.opcao = opcao
                    resposta.data_ultima_resposta = datetime.datetime.now()
                    resposta.save()
            else:
                resposta = Resposta()
                resposta.pergunta = self
                resposta.resposta = ''
                resposta.vinculo = vinculo
                resposta.uo = uo
                if self.objetiva:
                    resposta.opcao = resposta_atual
                else:
                    resposta.resposta = resposta_atual
                resposta.data_ultima_resposta = datetime.datetime.now()
                resposta.save()

    def get_html(self):
        return mark_safe(linebreaksbr(self.texto))

    def get_opcoes(self):
        opcoes = OpcaoPergunta.objects.filter(pergunta=self)
        if opcoes.exists():
            opcoes = opcoes.order_by('ordem')
        elif self.enquete.opcao_set.exists():
            opcoes = self.enquete.opcao_set.filter(opcaopergunta__isnull=True)
        return opcoes

    def get_respostas_dict(self):
        ret_dict = dict()

        for resposta in self.resposta_set.all().order_by('data_cadastro'):
            ret_dict[resposta.vinculo_id] = resposta

        return ret_dict

    @transaction.atomic
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.enquete.save()  # para despublicar se for o caso


class Opcao(models.ModelPlus):
    texto = models.TextField()
    enquete = models.ForeignKeyPlus(Enquete, on_delete=models.CASCADE)
    ordem = models.IntegerField()
    imagem = models.ImageFieldPlus(upload_to='enquete/opcao/imagem', blank=True)
    documento = models.FileFieldPlus(upload_to='enquete/opcao/documento', filetypes=['pdf'], blank=True)

    class Meta:
        verbose_name_plural = 'Opção de Enquete'
        verbose_name = 'Opções de Enquete'
        ordering = ('ordem',)

    def __str__(self):
        return self.texto

    def get_html(self):
        return mark_safe(linebreaksbr(self.texto))

    @transaction.atomic
    def delete(self, *args, **kwargs):
        super().delete(*args, **kwargs)
        self.enquete.save()  # para despublicar se for o caso


class OpcaoPergunta(Opcao):
    pergunta = models.ForeignKeyPlus(Pergunta, related_name='opcoes', on_delete=models.CASCADE)

    class Meta:
        verbose_name_plural = 'Opção de Resposta'
        verbose_name = 'Opções de Resposta'
        ordering = ('ordem',)

    def get_html(self):
        return mark_safe(linebreaksbr(self.texto))


class Resposta(models.ModelPlus):
    referencia = models.CharField(max_length=255, null=True, blank=True)
    pergunta = models.ForeignKeyPlus(Pergunta, on_delete=models.CASCADE)
    uo = models.ForeignKeyPlus(UnidadeOrganizacional, related_name='enquete_resposta_uo_set', null=True, on_delete=models.CASCADE)
    resposta = models.TextField(help_text='Resposta')
    opcao = models.ForeignKeyPlus(Opcao, null=True, help_text='Resposta Objetiva', on_delete=models.CASCADE)
    vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Vínculo', related_name='enquete_resposta_vinculo', null=True)
    data_cadastro = models.DateTimeField('Data', auto_now_add=True)
    data_ultima_resposta = models.DateTimeField('Data da última resposta', null=True)

    class Meta:
        verbose_name = 'Resposta'
        verbose_name_plural = 'Respostas'

    def __str__(self):
        return str(self.opcao) if self.opcao else self.resposta

    def get_resposta(self):
        return mark_safe(linebreaksbr(self.resposta))
