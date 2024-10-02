from decimal import Decimal
from comum.models import Ano, User
from djtools.db import models
from django.contrib.auth.models import Group
from edu.models import Professor
from edu.models.logs import LogModel
from django.conf import settings
from edu.models.cadastros_gerais import PERIODO_LETIVO_CHOICES
from rh.models import Servidor
import datetime


class AtividadeEnsino(models.ModelPlus):

    SUBGRUPOS = [
        (1, 'Aulas'),
        (2, 'Atividade de Preparação, Manutenção e Apoio ao Ensino'),
        (3, 'Programas ou Projetos de Ensino'),
        (4, 'Atendimento, Acompanhamento, Avaliação e Orientação de Alunos'),
        (5, 'Reuniões Pedagógicas, de Grupo e Afins'),
    ]

    descricao = models.CharFieldPlus(verbose_name='Descrição')
    subgrupo = models.IntegerField(verbose_name='Subgrupo', choices=SUBGRUPOS)

    class Meta:
        verbose_name = 'Atividade de Ensino'
        verbose_name_plural = 'Atividades de Ensino'

    def __str__(self):
        return self.descricao


class AtividadePesquisa(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Atividade de Pesquisa e Inovação'
        verbose_name_plural = 'Atividades de Pesquisa e Inovação'

    def __str__(self):
        return self.descricao


class AtividadeExtensao(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Atividade de Extensão'
        verbose_name_plural = 'Atividades de Extensão'

    def __str__(self):
        return self.descricao


class AtividadeGestao(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name='Descrição')

    class Meta:
        verbose_name = 'Atividade de Gestão'
        verbose_name_plural = 'Atividades de Gestão'

    def __str__(self):
        return self.descricao


class PlanoIndividualTrabalhoV2(LogModel):
    # DADOS GERAIS
    ano_letivo = models.ForeignKeyPlus(Ano, verbose_name='Ano Letivo', on_delete=models.CASCADE)
    periodo_letivo = models.IntegerField(verbose_name='Período Letivo', choices=PERIODO_LETIVO_CHOICES)

    professor = models.ForeignKeyPlus(Professor, verbose_name='Professor', on_delete=models.CASCADE)

    # ENSINO
    # Aulas
    obs_aulas = models.TextField(verbose_name='Observações', null=True, blank=False)
    arquivo_aulas = models.FileFieldPlus(verbose_name='Arquivo', null=True, blank=True, upload_to='pit_rit_v2')

    # Preparação e Manutenção ao Ensino
    ch_preparacao_manutencao_ensino = models.PositiveIntegerField(verbose_name='Carga-Horária', default=0)
    obs_preparacao_manutencao_ensino = models.TextField(verbose_name='Observações', null=True, blank=False)
    arquivo_preparacao_manutencao_ensino = models.FileFieldPlus(verbose_name='Arquivo', null=True, blank=True, upload_to='pit_rit_v2')
    # Apoio ao Ensino
    ch_apoio_ensino = models.PositiveIntegerField(verbose_name='Carga-Horária', default=0)
    atividades_apoio_ensino = models.ManyToManyFieldPlus(AtividadeEnsino, verbose_name='Atividades', related_name='a1')
    outras_atividades_apoio_ensino = models.TextField(verbose_name='Outras Atividades', null=True, blank=True)
    obs_apoio_ensino = models.TextField(verbose_name='Observações', null=True, blank=False)
    arquivo_apoio_ensino = models.FileFieldPlus(verbose_name='Arquivo', null=True, blank=True, upload_to='pit_rit_v2')

    # Programas ou Projetos de Ensino
    ch_programas_projetos_ensino = models.PositiveIntegerField(verbose_name='Carga-Horária', default=0)
    obs_programas_projetos_ensino = models.TextField(verbose_name='Observações', null=True, blank=False)
    arquivo_programas_projetos_ensino = models.FileFieldPlus(verbose_name='Arquivo', null=True, blank=True, upload_to='pit_rit_v2')

    # Atendimento, Acompanhamento, Avaliação e Orientação de Alunos
    ch_orientacao_alunos = models.PositiveIntegerField(verbose_name='Carga-Horária', default=0)
    atividades_orientacao_alunos = models.ManyToManyFieldPlus(AtividadeEnsino, verbose_name='Atividades', related_name='a2')
    outras_atividades_orientacao_alunos = models.TextField(verbose_name='Outras Atividades', null=True, blank=True)
    obs_orientacao_alunos = models.TextField(verbose_name='Observações', null=True, blank=False)
    arquivo_orientacao_alunos = models.FileFieldPlus(verbose_name='Arquivo', null=True, blank=True, upload_to='pit_rit_v2')

    # Reuniões Pedagógicas, de Grupo e Afins
    ch_reunioes = models.PositiveIntegerField(verbose_name='Carga-Horária', default=0)
    atividades_reunioes = models.ManyToManyFieldPlus(AtividadeEnsino, verbose_name='Atividades', related_name='a3')
    outras_atividades_reunioes = models.TextField(verbose_name='Outras Atividades', null=True, blank=True)
    obs_reunioes = models.TextField(verbose_name='Observações', null=True, blank=False)
    arquivo_reunioes = models.FileFieldPlus(verbose_name='Arquivo', null=True, blank=True, upload_to='pit_rit_v2')

    # PESQUISA E INOVAÇÃO
    ch_pesquisa = models.PositiveIntegerField(verbose_name='Carga-Horária', default=0)
    atividades_pesquisa = models.ManyToManyFieldPlus(AtividadePesquisa, verbose_name='Atividades')
    outras_atividades_pesquisa = models.TextField(verbose_name='Outras Atividades', null=True, blank=True)
    obs_pesquisa = models.TextField(verbose_name='Observações', null=True, blank=False)
    arquivo_pesquisa = models.FileFieldPlus(verbose_name='Arquivo', null=True, blank=True, upload_to='pit_rit_v2')

    # EXTENSÃO
    ch_extensao = models.PositiveIntegerField(verbose_name='Carga-Horária', default=0)
    atividades_extensao = models.ManyToManyFieldPlus(AtividadeExtensao, verbose_name='Atividades')
    outras_atividades_extensao = models.TextField(verbose_name='Outras Atividades', null=True, blank=True)
    obs_extensao = models.TextField(verbose_name='Observações', null=True, blank=False)
    arquivo_extensao = models.FileFieldPlus(verbose_name='Arquivo', null=True, blank=True, upload_to='pit_rit_v2')

    # GESTÃO E REPRESENTAÇÃO INSTITUCIONAL
    ch_gestao = models.PositiveIntegerField(verbose_name='Carga-Horária', default=0)
    atividades_gestao = models.ManyToManyFieldPlus(AtividadeGestao, verbose_name='Atividades')
    outras_atividades_gestao = models.TextField(verbose_name='Outras Atividades', null=True, blank=True)
    obs_gestao = models.TextField(verbose_name='Observações', null=True, blank=False)
    arquivo_gestao = models.FileFieldPlus(verbose_name='Arquivo', null=True, blank=True, upload_to='pit_rit_v2')

    # DADOS DA AVALIAÇÃO DO PLANO
    data_envio = models.DateTimeFieldPlus(verbose_name='Data do Envio do Plano', null=True)
    avaliador = models.ForeignKeyPlus(Servidor, verbose_name='Avaliador do Plano', null=True, on_delete=models.CASCADE)
    aprovado = models.BooleanField(verbose_name='Plano Aprovado', null=True)
    data_aprovacao = models.DateTimeFieldPlus(verbose_name='Data da Aprovação do Plano', null=True)

    # DADOS DA AVALIAÇÃO DO RELATORIO
    data_envio_relatorio = models.DateTimeFieldPlus(verbose_name='Data do Envio do Relatório', null=True)
    avaliador_relatorio = models.ForeignKeyPlus(Servidor, verbose_name='Avaliador do Relatório', null=True, on_delete=models.CASCADE, related_name='avaliador_relatorio_set')
    relatorio_aprovado = models.BooleanField(verbose_name='Relatório Aprovado', null=True)
    data_aprovacao_relatorio = models.DateTimeFieldPlus(verbose_name='Data da Aprovação do Relatório', null=True)

    # DADOS DA PUBLICAÇÃO
    publicado = models.BooleanField(verbose_name='Publicado', null=True)
    responsavel_publicacao = models.ForeignKeyPlus(
        Servidor, verbose_name='Responsável pela Publicação', null=True, related_name='responsavel_publiacao_set', on_delete=models.CASCADE
    )
    data_publicacao = models.DateTimeFieldPlus(verbose_name='Data da Publicação', null=True)

    class Meta:
        verbose_name = 'Plano Individual de Trabalho'
        verbose_name_plural = 'Planos Individuais de Trabalho'

    def save(self, *args, **kwargs):
        super().save()
        if self.avaliador:
            user = User.objects.get(username=self.avaliador.matricula)
            group = Group.objects.get(name='Avaliador de Plano Individual de Trabalho')
            user.groups.add(group)
        if self.avaliador_relatorio:
            user = User.objects.get(username=self.avaliador_relatorio.matricula)
            group = Group.objects.get(name='Avaliador de Plano Individual de Trabalho')
            user.groups.add(group)
        if self.responsavel_publicacao:
            user = User.objects.get(username=self.responsavel_publicacao.matricula)
            group = Group.objects.get(name='Publicador de Plano Individual de Trabalho')
            user.groups.add(group)

    def can_change(self, user=None):
        return user == self.professor.vinculo.user

    def get_absolute_url(self):
        return '/edu/professor/{}/?tab=planoatividades&ano-periodo={}.{}'.format(self.professor.pk, self.ano_letivo, self.periodo_letivo)

    def __str__(self):
        return 'Plano Individual de Trabalho - {} - {}/{}'.format(self.professor, self.ano_letivo, self.periodo_letivo)

    def is_relatorio_preenchido(self):
        for attr in (
            'obs_aulas',
            'obs_preparacao_manutencao_ensino',
            'obs_apoio_ensino',
            'obs_programas_projetos_ensino',
            'obs_orientacao_alunos',
            'obs_reunioes',
            'obs_pesquisa',
            'obs_extensao',
            'obs_gestao',
        ):
            if getattr(self, attr) is None:
                return False
        return True

    def get_atividades(self, tipo):
        lista = []
        for atividade in getattr(self, tipo).all():
            lista.append(atividade.descricao)
        for atividade in (getattr(self, 'outras_{}'.format(tipo)) or '').split('\n'):
            if atividade.strip():
                lista.append(atividade)
        return lista

    def get_atividades_apoio_ensino(self):
        return self.get_atividades('atividades_apoio_ensino')

    def get_atividades_orientacao_alunos(self):
        return self.get_atividades('atividades_orientacao_alunos')

    def get_atividades_reunioes(self):
        return self.get_atividades('atividades_reunioes')

    def get_atividades_pesquisa(self):
        return self.get_atividades('atividades_pesquisa')

    def get_atividades_extensao(self):
        return self.get_atividades('atividades_extensao')

    def get_atividades_gestao(self):
        return self.get_atividades('atividades_gestao')

    # Diários
    def get_vinculo_diarios(self, fic=None):
        return self.professor.get_vinculo_diarios(self.ano_letivo.ano, self.periodo_letivo, fic, None, False)

    def get_ch_diarios(self, fic=False):
        ch_semanal_credito = 0
        ch_semanal_efetiva = 0
        for professor_diario in self.get_vinculo_diarios(fic):
            ch_diario = professor_diario.get_qtd_creditos_efetiva(self.periodo_letivo)
            ch_semanal_credito += ch_diario

            componente = professor_diario.diario.componente_curricular.componente
            ch_semanal_efetiva += ch_diario * componente.ch_hora_relogio / componente.ch_hora_aula if componente.ch_hora_aula else 0
        return ch_semanal_credito, ch_semanal_efetiva

    # Minicursos
    def get_vinculos_minicurso(self):
        return self.professor.get_vinculos_minicurso(self.ano_letivo.ano, self.periodo_letivo)

    def get_ch_minicursos(self):
        soma = 0
        for vinculo in self.get_vinculos_minicurso():
            soma += vinculo.get_carga_horaria_semanal_ha()
        return soma

    # Diários Especiais
    def get_vinculos_diarios_especiais(self, is_cap=None):
        return self.professor.get_vinculos_diarios_especiais(self.ano_letivo.ano, self.periodo_letivo, is_cap)

    def get_ch_semanal_diarios_especiais(self):
        ch_semanal_diarios_especiais = 0
        for diario_especial in self.get_vinculos_diarios_especiais(True):
            ch_semanal_diarios_especiais += diario_especial.get_carga_horaria_semanal_ha()
        if ch_semanal_diarios_especiais > 6:
            ch_semanal_diarios_especiais = 6
        for diario_especial in self.get_vinculos_diarios_especiais(False):
            ch_semanal_diarios_especiais += diario_especial.get_carga_horaria_semanal_ha()
        return ch_semanal_diarios_especiais

    # Cargas-Horárias
    def get_cargas_horarias(self):
        ch_semanal_diarios, ch_semanal_efetiva = self.get_ch_diarios()
        ch_semanal_diarios_fic, ch_semanal_efetiva_fic = self.get_ch_diarios(True)
        ch_semanal_minicursos = self.get_ch_minicursos()
        ch_semanal_diarios_especiais = self.get_ch_semanal_diarios_especiais()
        ch_preparacao_manutencao_ensino = self.ch_preparacao_manutencao_ensino
        ch_apoio_ensino = self.ch_apoio_ensino
        ch_programas_projetos_ensino = self.ch_programas_projetos_ensino
        ch_orientacao_alunos = self.ch_orientacao_alunos
        ch_reunioes = self.ch_reunioes

        ch_pesquisa = self.ch_pesquisa
        ch_extensao = self.ch_extensao
        ch_gestao = self.ch_gestao

        ch_semanal_aulas = ch_semanal_diarios + ch_semanal_diarios_fic + ch_semanal_minicursos + ch_semanal_diarios_especiais
        ch_aulas = int(round(Decimal(settings.PERCENTUAL_CH_PREPARACAO_AULAS_PIT) / Decimal(100) * (Decimal(ch_semanal_efetiva + ch_semanal_efetiva_fic) + Decimal(ch_semanal_minicursos + ch_semanal_diarios_especiais) * Decimal(3) / 4)))

        ch_total = (
            ch_aulas + ch_preparacao_manutencao_ensino + ch_apoio_ensino + ch_programas_projetos_ensino + ch_orientacao_alunos + ch_reunioes + ch_pesquisa + ch_extensao + ch_gestao
        )
        return (
            ch_semanal_aulas,
            ch_aulas,
            ch_semanal_diarios,
            ch_semanal_diarios_fic,
            ch_semanal_minicursos,
            ch_semanal_diarios_especiais,
            ch_preparacao_manutencao_ensino,
            ch_apoio_ensino,
            ch_programas_projetos_ensino,
            ch_orientacao_alunos,
            ch_reunioes,
            ch_pesquisa,
            ch_extensao,
            ch_gestao,
            ch_total,
        )

    def pode_enviar_plano(self, user):
        return self.aprovado is None and self.data_envio is None and self.professor.vinculo.user == user

    def pode_alterar_avaliador_plano(self, user):
        return self.aprovado is None and self.data_envio and self.professor.vinculo.user == user

    def pode_avaliar_plano(self, user):
        return self.aprovado is None and self.data_envio and self.avaliador.get_vinculo().user == user

    def pode_desfazer_aprovacao_plano(self, user):
        return self.aprovado and self.avaliador.get_vinculo().user == user and not self.publicado and self.data_envio_relatorio is None

    def pode_preencher_relatorio(self, user):
        return self.aprovado and self.data_envio_relatorio is None and self.professor.vinculo.user == user

    def pode_enviar_relatorio(self, user):
        return self.aprovado and self.is_relatorio_preenchido() and self.relatorio_aprovado is None and self.data_envio_relatorio is None and self.professor.vinculo.user == user

    def pode_alterar_avaliador_relatorio(self, user):
        return self.aprovado and self.is_relatorio_preenchido() and self.relatorio_aprovado is None and self.data_envio_relatorio and self.professor.vinculo.user == user

    def pode_avaliar_relatorio(self, user):
        return self.aprovado and self.data_envio_relatorio and self.relatorio_aprovado is None and self.avaliador_relatorio.get_vinculo().user == user

    def pode_desfazer_aprovacao_relatorio(self, user):
        return self.relatorio_aprovado and self.avaliador_relatorio.get_vinculo().user == user and not self.publicado

    def aprovar_plano(self, user, parecer):
        if self.pode_avaliar_plano(user):
            self.aprovado = True
            self.data_aprovacao = datetime.datetime.now()
            self.save()

            parecer.pit = self
            parecer.data = self.data_aprovacao
            parecer.tipo = 'PIT'
            parecer.servidor = self.avaliador
            parecer.save()

    def devolver_plano(self, user, parecer):
        if self.pode_avaliar_plano(user) or self.pode_desfazer_aprovacao_plano(user):
            parecer.pit = self
            parecer.data = datetime.datetime.now()
            parecer.tipo = 'PIT'
            parecer.servidor = self.avaliador
            parecer.save()

            self.aprovado = None
            self.data_aprovacao = None
            self.data_envio = None
            self.avaliador = None
            self.save()

    def aprovar_relatorio(self, user, parecer, responsavel_publicacao):
        if self.pode_avaliar_relatorio(user):
            self.relatorio_aprovado = True
            self.data_aprovacao_relatorio = datetime.datetime.now()
            self.responsavel_publicacao = responsavel_publicacao
            self.save()

            parecer.pit = self
            parecer.data = self.data_aprovacao_relatorio
            parecer.tipo = 'RIT'
            parecer.servidor = self.avaliador_relatorio
            parecer.save()

    def devolver_relatorio(self, user, parecer):
        if self.pode_avaliar_relatorio(user) or self.pode_desfazer_aprovacao_relatorio(user):
            parecer.pit = self
            parecer.data = datetime.datetime.now()
            parecer.tipo = 'RIT'
            parecer.servidor = self.avaliador_relatorio
            parecer.save()

            self.relatorio_aprovado = None
            self.data_aprovacao_relatorio = None
            self.data_envio_relatorio = None
            self.avaliador_relatorio = None
            self.responsavel_publicacao = None
            self.save()


class Parecer(models.ModelPlus):

    pit = models.ForeignKeyPlus(PlanoIndividualTrabalhoV2, verbose_name='Plano Individual de Trabalho')
    tipo = models.CharFieldPlus(verbose_name='Tipo', null=True, choices=[['PIT', 'PIT'], ['RIT', 'RIT']], default='PIT')
    data = models.DateTimeFieldPlus(verbose_name='Data')
    obs = models.TextField(verbose_name='Observação')
    servidor = models.ForeignKeyPlus(Servidor, verbose_name='Servidor', null=True, on_delete=models.CASCADE, help_text='Servidor que emitiu o parecer')

    class Meta:
        verbose_name = 'Parecer'
        verbose_name_plural = 'Pareceres'
        ordering = ('-data',)

    def __str__(self):
        return self.obs
