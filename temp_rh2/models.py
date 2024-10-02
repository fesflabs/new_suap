# -*- coding: utf-8 -*-

import datetime

from djtools.db import models
from djtools.db.models import ModelPlus
from djtools.utils import get_age

from comum.models import User
from django.db.models import Q

from ckeditor.fields import RichTextField


class Categoria(ModelPlus):
    nome = models.CharField(max_length=20, blank=False, null=False, verbose_name='Nome')
    idade_inferior = models.PositiveIntegerField('Limite de idade inferior')
    idade_superior = models.PositiveIntegerField('Limite de idade superior')
    excluido = models.BooleanField(default=False)

    def __str__(self):
        return "Categoria {} de {} à {} anos".format(self.nome, self.idade_inferior, self.idade_superior)

    class Meta:
        verbose_name = 'Categoria'
        verbose_name_plural = 'Categorias'


class ModalidadeDesportiva(ModelPlus):
    CODIGO_NATACAO = 9
    CODIGO_ATLETISMO = 8
    CODIGO_JOGOS_ELETRONICOS = 25

    MASCULINO = 1
    FEMININO = 2
    MISTO = 3
    NAO_APLICA = 4
    choices_sexo = ((MASCULINO, 'Masculino'), (FEMININO, 'Feminino'), (MISTO, 'Misto'), (NAO_APLICA, 'Não se aplica'))

    COLETIVO = 1
    INDIVIDUAL = 2
    choices_tipo_modalidade = ((COLETIVO, 'Coletivo'), (INDIVIDUAL, 'Individual'))
    nome = models.CharField(max_length=20, blank=False, null=False, verbose_name='Nome')
    sexo = models.PositiveIntegerField('Sexo', default=1, choices=choices_sexo, help_text='Quando o esporte for individual escolher "Não se aplica"')
    tipo = models.PositiveIntegerField('Tipo', default=1, choices=choices_tipo_modalidade)
    exige_atestado = models.BooleanField('Modalidade exige atestado médico?', default=True)

    def __str__(self):
        if self.sexo == self.NAO_APLICA:
            return '{} - {}'.format(self.nome, self.get_tipo_display())
        return '{} - {} - {}'.format(self.nome, self.get_sexo_display(), self.get_tipo_display())

    class Meta:
        verbose_name = 'Modalidade Desportiva'
        verbose_name_plural = 'Modalidades Desportivas'
        permissions = ()


class Prova(ModelPlus):
    nome = models.CharField(max_length=20, blank=False, null=False, verbose_name='Nome')
    modalidade = models.ForeignKeyPlus(ModalidadeDesportiva, verbose_name='Modalidade')

    def __str__(self):
        return "{} - {}".format(self.nome, self.modalidade)

    class Meta:
        verbose_name = 'Prova'
        verbose_name_plural = 'Provas'


class CompeticaoDesportiva(ModelPlus):
    nome = models.CharField(max_length=20, blank=False, null=False, verbose_name="Nome")
    descricao = models.TextField(blank=False, null=False, verbose_name='Descrição')
    ano = models.ForeignKeyPlus('comum.Ano', null=False, blank=False, on_delete=models.CASCADE)

    uo = models.ForeignKeyPlus(
        'rh.unidadeorganizacional', null=True, blank=True, on_delete=models.CASCADE, verbose_name='Unidade Organizacional', help_text='Define escopo da competição'
    )

    modalidades = models.ManyToManyField(ModalidadeDesportiva, verbose_name='Modalidades desportivas')
    categorias = models.ManyToManyField(Categoria, verbose_name='Categorias')

    max_modalidades_coletivas_por_inscricao = models.PositiveIntegerField('Quantidade Máxima de modalidades coletivas', default=2)
    max_modalidades_individuais_por_inscricao = models.PositiveIntegerField('Quantidade Máxima modalidades individuais', default=2)

    max_modalidades_por_inscricao = models.PositiveIntegerField('Quantidade Máxima modalidades Independente se individual ou coletiva', default=4)

    max_provas_natacao = models.PositiveIntegerField('Máximo de provas de Natação', default=3)
    max_provas_atletismo = models.PositiveIntegerField('Máximo de provas de Atletismo', default=3)
    max_provas_jogos_eletronicos = models.PositiveIntegerField('Máximo de provas dos jogos eletrônicos', default=3)

    provas_natacao = models.ManyToManyField(Prova, verbose_name='Provas da Natação', related_name="provas_natacao_competicao", blank=True)
    provas_atletismo = models.ManyToManyField(Prova, verbose_name='Provas da Atletismo', related_name="provas_atletismo_competicao", blank=True)

    provas_jogos_eletronicos = models.ManyToManyField(Prova, verbose_name='Provas dos Jogos Eletrônicos', related_name="provas_jogos_eletronicos_competicao", blank=True)

    data_inicio_periodo_inscricoes = models.DateFieldPlus('Data inicial do período de inscrições', null=False)
    data_fim_periodo_inscricoes = models.DateFieldPlus('Data final do período de inscrições', null=False)

    data_inicio_periodo_validacao = models.DateFieldPlus('Data inicial do período de validação', null=False)
    data_fim_periodo_validacao = models.DateFieldPlus('Data final do período de validação', null=False)

    data_inicio_confirmacao_inscritos = models.DateFieldPlus('Data inicial do período de confirmação dos inscritos', null=False)
    data_fim_confirmacao_inscritos = models.DateFieldPlus('Data final do período de confirmação dos inscritos', null=False)

    data_inicio_reajustes = models.DateFieldPlus('Data inicial do período de reajustes (pelo representante do campus)', null=False)
    data_fim_reajustes = models.DateFieldPlus('Data final do período de reajustes (pelo representante do campus)', null=False)

    data_homologacao_inscricoes = models.DateFieldPlus('Data de homologação e consolidação das inscrições', null=False)

    data_inicio_periodo1_jogos = models.DateFieldPlus('Data inicial do período 1 de jogos', null=False)
    data_fim_periodo1_jogos = models.DateFieldPlus('Data final do período 1 de jogos', null=False)

    data_inicio_periodo2_jogos = models.DateFieldPlus('Data inicial do período 2 de jogos', null=True, blank=True)
    data_fim_periodo2_jogos = models.DateFieldPlus('Data final do período 2 de jogos', null=True, blank=True)

    class Meta:
        unique_together = ('nome', 'ano')
        verbose_name = 'Competição Desportiva'
        verbose_name_plural = 'Competições Desportivas'

        ordering = ('ano', 'nome')

    def __str__(self):
        return ' {} {}'.format(self.nome, self.ano.ano)


class InscricaoCompeticaoDesportiva(ModelPlus):
    PP = 1
    P = 2
    M = 3
    G = 4
    GG = 5
    XG = 6
    choices_tamanhos = ((PP, 'PP'), (P, 'P'), (M, 'M'), (G, 'G'), (GG, 'GG'), (XG, 'XG'))

    choices_situacoes = ((1, 'Inscrição em Análise'), (2, 'Validada'), (3, 'Homologada'), (4, 'Rejeitada'))

    servidor = models.ForeignKeyPlus('rh.Servidor', null=False, blank=False, on_delete=models.CASCADE)
    uo = models.ForeignKeyPlus('rh.UnidadeOrganizacional', null=False, blank=True, verbose_name='Campus Inscrito', on_delete=models.CASCADE)
    termo_recebimento_hospedagem = models.BooleanField(
        "Desejo receber hospedagem",
        blank=False,
        default=False,
        null=False,
        help_text="Estou ciente de que a desistência de participação poderá acarretar à devolução dos valores referentes a hospedagem, salvo por motivo devidamente justificado ao respectivo representante do campus/polo até a data limite de homologação das inscrições.",
    )
    competicao_desportiva = models.ForeignKeyPlus('temp_rh2.CompeticaoDesportiva', verbose_name='Competição', null=False, on_delete=models.CASCADE, blank=False)
    modalidades = models.ManyToManyField(ModalidadeDesportiva, verbose_name='Modalidades')
    provas_natacao = models.ManyToManyField(Prova, verbose_name='Provas da Natação', related_name="provas_natacao", blank=True)
    provas_atletismo = models.ManyToManyField(Prova, verbose_name='Provas da Atletismo', related_name="provas_atletismo", blank=True)
    provas_jogos_eletronicos = models.ManyToManyField(Prova, verbose_name='Provas Jogos Eletrônicos', related_name="provas_jogos_eletronicos", blank=True)

    preferencia_camisa = models.PositiveIntegerField('Tamanho da camisa', default=3, choices=choices_tamanhos, help_text='Tamanho da camisa/uniforme')
    preferencia_short = models.PositiveIntegerField('Tamanho do short', default=3, choices=choices_tamanhos, help_text='Tamanho da short/uniforme')
    situacao = models.PositiveIntegerField('Situação', default=1, choices=choices_situacoes, help_text='Situação')
    termo_aceitacao_exame = models.BooleanField(
        "Termo de aceitação para entrega do atestado médico",
        blank=False,
        default=False,
        null=False,
        help_text="Estou ciente de que a participação nos jogos está condicionada a entrega de Atestado Médico comprovando a capacidade física competitiva para salvaguardar minha integridade física. A entrega do atestado é obrigatória para todas as modalidades, exceto para o xadrez.",
    )

    categoria = models.ForeignKeyPlus('temp_rh2.Categoria', verbose_name='Categoria', null=True, blank=False)

    validado_em = models.DateTimeFieldPlus(null=True, blank=True)
    validado_por = models.ForeignKeyPlus('comum.User', related_name='inscricao_desportiva_validada_por', null=True, on_delete=models.CASCADE, blank=True, editable=False)

    homologado_em = models.DateTimeFieldPlus(null=True, blank=True)
    homologado_por = models.ForeignKeyPlus('comum.User', related_name='inscricao_desportiva_homologada_por', null=True, on_delete=models.CASCADE, blank=True, editable=False)

    rejeitado_em = models.DateTimeFieldPlus(null=True, blank=True)
    rejeitado_por = models.ForeignKeyPlus('comum.User', related_name='inscricao_desportiva_rejeitada_por', null=True, on_delete=models.CASCADE, blank=True, editable=False)
    observacao_rejeicao = models.TextField(blank=True, verbose_name='Observação da Rejeição')

    atestado_medico = models.FileFieldPlus(
        'Atestado Médico',
        upload_to='temp_rh2/atividade_complementar/',
        null=True,
        blank=True,
        check_mimetype=False,
        help_text='Neste campo você deve anexar o atestado médico para a participação nos jogos. O atestado é obrigatório para todos os participantes, exceto os inscritos somente em tênis de mesa e/ou xadrez. Tipos de arquivos aceitos: PDF, PNG ou JPG. Tamanho Máximo: 5Mb',
        filetypes=['pdf', 'png', 'jpg'],
        max_file_size=5242880,
    )

    class Meta:
        unique_together = ('servidor', 'competicao_desportiva')
        verbose_name = 'Inscrição na Competição Desportiva'
        verbose_name_plural = 'Inscrições na Competições Desportivas'

        permissions = (('pode_validar_inscricaocompeticaodesportiva', 'Pode validar inscrição competição desportiva'),)

    def __str__(self):
        return 'Inscrição {} - {}'.format(self.servidor.nome, self.competicao_desportiva.nome)

    def get_absolute_url(self):
        return "/temp_rh2/competicao_desportiva/inscricao/{}/{}/".format(self.competicao_desportiva.pk, self.pk)

    @property
    def calcular_categoria(self):
        data_nascimento = self.servidor.nascimento_data
        if data_nascimento:
            idade_fim_do_ano = get_age(self.servidor.nascimento_data, datetime.date(self.competicao_desportiva.ano.ano, 12, 31))
            return self.competicao_desportiva.categorias.filter(idade_inferior__lte=idade_fim_do_ano, idade_superior__gte=idade_fim_do_ano).first()
        return None

    def save(self, *args, **kargs):
        if not self.categoria:
            self.categoria = self.calcular_categoria
        super(InscricaoCompeticaoDesportiva, self).save(*args, **kargs)


# ==================================================================================
# Inscricao do curso SUAP
# ==================================================================================
class CursoSuap(ModelPlus):

    sigla = models.CharField(max_length=10, blank=False, null=False, verbose_name='Sigla')

    denominacao = models.CharField(max_length=255, blank=False, null=False, verbose_name='Denominação')

    sobre = models.TextField('Sobre')

    data_inicio_periodo_inscricoes = models.DateFieldPlus('Data inicial do período de inscrições', null=False)
    data_fim_periodo_inscricoes = models.DateFieldPlus('Data final do período de inscrições', null=False)

    ativo = models.BooleanField(default=False)

    def __str__(self):
        return self.denominacao

    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'

    @staticmethod
    def cursos_com_inscricao_aberta():

        hoje = datetime.datetime.now().date()

        cursos = CursoSuap.objects.filter(Q(data_inicio_periodo_inscricoes__lte=hoje) & Q(data_fim_periodo_inscricoes__gte=hoje))
        # cursos = cursos.filter(ativo=True)

        return cursos

    @staticmethod
    def curso_suap_com_inscricao_aberta():

        hoje = datetime.datetime.now().date()

        cursos = CursoSuap.objects.filter(Q(data_inicio_periodo_inscricoes__lte=hoje) & Q(data_fim_periodo_inscricoes__gte=hoje))
        # cursos = cursos.filter(ativo=True)
        cursos = cursos.filter(sigla='CS')

        return cursos.exists()

    @staticmethod
    def curso_procdoc_com_inscricao_aberta():

        hoje = datetime.datetime.now().date()

        cursos = CursoSuap.objects.filter(Q(data_inicio_periodo_inscricoes__lte=hoje) & Q(data_fim_periodo_inscricoes__gte=hoje))
        # cursos = cursos.filter(ativo=True)
        cursos = cursos.filter(sigla='PD')

        return cursos.exists()

    @staticmethod
    def cursos_ativos():

        cursos = CursoSuap.objects.filter(ativo=True)

        return cursos

    @staticmethod
    def curso_suap_ativo():

        cursos = CursoSuap.objects.filter(ativo=True)
        cursos = cursos.filter(sigla='CS')

        return cursos.exists()

    @staticmethod
    def curso_procdoc_ativo():
        cursos = CursoSuap.objects.filter(ativo=True)
        cursos = cursos.filter(sigla='PD')

        return cursos.exists()


class InscricaoCursoSuap(ModelPlus):

    curso = models.ForeignKeyPlus(CursoSuap, on_delete=models.PROTECT)

    usuario = models.ForeignKeyPlus(User, verbose_name='Usuário', on_delete=models.CASCADE)

    data = models.DateTimeFieldPlus('Data', null=True, blank=True)

    enviou_email_solinsc = models.BooleanField(default=False, verbose_name='Coordenação Enviou email para o inscrito')

    data_confirmacao_inscricao = models.DateField('Data de Confirmação da Inscrição', null=True, blank=True)

    solicitou_diaria = models.BooleanField(default=False, verbose_name='Solicitou diária')

    def __str__(self):
        return '{} em {}'.format(self.curso, self.usuario)

    @staticmethod
    def get_usuario_inscricao(curso, usuario):
        return InscricaoCursoSuap.objects.get(curso=curso, usuario=usuario)

    @staticmethod
    def existe_usuario_inscricao(curso, usuario):
        return InscricaoCursoSuap.objects.filter(curso=curso, usuario=usuario).exists()


class LogInscricaoCursoSuap(ModelPlus):

    log = models.CharField(max_length=255, blank=False, null=False, verbose_name='Log')

    data = models.DateTimeField('Data/Hora', auto_now_add=True, null=True, blank=True)

    def __str__(self):
        return '{} em {}'.format(self.log, self.data)


class ConteudoEmail(ModelPlus):
    assunto = models.CharField(max_length=255, verbose_name='Assunto')
    corpo = RichTextField('Corpo')

    def __str__(self):
        return self.assunto
