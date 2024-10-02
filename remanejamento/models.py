# -*- coding: utf-8 -*-
import datetime
import hashlib

from django.db import transaction

from djtools.db import models
from djtools.utils import to_ascii


class Edital(models.ModelPlus):
    titulo = models.CharField('Título', max_length=255)
    descricao = models.TextField('Descrição')
    url = models.URLField(verbose_name='Link para mais informações', null=True, blank=True, )
    campus = models.ManyToManyField('rh.UnidadeOrganizacional', verbose_name='Campus', blank=True, help_text="Informe os campi participantes deste remanejamento.")
    cargos = models.ManyToManyField('rh.cargoemprego', verbose_name='Cargos', help_text='Servidores destes cargos poderão se inscrever neste edital.')
    coordenadores = models.ManyToManyField('comum.User', verbose_name='Coordenadores', blank=True, help_text='Os coordenadores poderão acompanhar as inscrições deste edital.')

    tem_anexo = models.BooleanField(default=False, verbose_name='Permite anexo?', help_text='Indica que deverá ser anexado um arquivo no formulário de inscrição.')
    chave_hash = models.CharField(max_length=128, help_text='Irá compor a chave de autenticidade da inscrição.<br/> Em nenhuma hipótese um candidato pode ver este campo.')

    inicio_recursos_edital = models.DateTimeFieldPlus(verbose_name='Início dos Recursos ao Edital', null=True, blank=True)
    fim_recursos_edital = models.DateTimeFieldPlus(verbose_name='Fim dos Recursos ao Edital', null=True, blank=True)
    resultado_recursos_edital = models.DateTimeFieldPlus(verbose_name='Resultado dos Recursos ao Edital', null=True, blank=True)

    inicio_inscricoes = models.DateTimeFieldPlus(verbose_name='Início das inscrições')
    fim_inscricoes = models.DateTimeFieldPlus(verbose_name='Fim das inscrições')

    inicio_avaliacoes = models.DateTimeFieldPlus(verbose_name='Início das avaliações', null=True, blank=True)
    fim_avaliacoes = models.DateTimeFieldPlus(verbose_name='Fim das avaliações', null=True, blank=True)

    inicio_desistencias = models.DateTimeFieldPlus(verbose_name='Início da Desistência do edital', null=True, blank=True)
    fim_desistencias = models.DateTimeFieldPlus(verbose_name='Fim da desistência do edital', null=True, blank=True)

    inicio_recursos = models.DateTimeFieldPlus(verbose_name='Início dos recursos do resultado', null=True, blank=True)
    fim_recursos = models.DateTimeFieldPlus(verbose_name='Fim dos recursos do resultado', null=True, blank=True)
    resultado_recursos = models.DateTimeFieldPlus(verbose_name='Resultado dos recursos ao resultado', null=True, blank=True)

    inicio_resultados = models.DateTimeFieldPlus(verbose_name='Resultado Final')

    class Meta:
        verbose_name = 'Edital'
        verbose_name_plural = 'Editais'

    def __str__(self):
        return self.titulo

    @classmethod
    def get_em_periodo_de_inscricao(cls):
        agora = datetime.datetime.now()
        return cls.objects.filter(inicio_inscricoes__lte=agora, fim_inscricoes__gte=agora)

    @classmethod
    def get_em_periodo_de_recurso(cls):
        agora = datetime.datetime.now()
        return cls.objects.filter(inicio_recursos__lte=agora, fim_recursos__gte=agora)

    @classmethod
    def get_em_periodo_de_recurso_edital(cls):
        agora = datetime.datetime.now()
        return cls.objects.filter(inicio_recursos_edital__lte=agora, fim_recursos_edital__gte=agora)

    @classmethod
    def get_em_periodo_de_inscricao_servidor(cls, servidor):
        if not servidor.cargo_emprego:
            return cls.objects.none()
        return cls.get_em_periodo_de_inscricao().filter(cargos=servidor.cargo_emprego)

    @classmethod
    def get_em_periodo_recurso_edital_servidor(cls, servidor):
        if not servidor.cargo_emprego:
            cls.objects.none()
        return cls.get_em_periodo_de_recurso_edital().filter(cargos=servidor.cargo_emprego)

    @classmethod
    def get_em_periodo_de_recurso_servidor(cls, servidor):
        if not servidor.cargo_emprego:
            return cls.objects.none()
        return cls.get_em_periodo_de_recurso().filter(cargos=servidor.cargo_emprego)

    def is_em_periodo_de_inscricao(self):
        return self.inicio_inscricoes <= datetime.datetime.now() <= self.fim_inscricoes

    def is_em_periodo_de_avaliacao(self):
        if self.inicio_avaliacoes and self.fim_avaliacoes:
            return self.inicio_avaliacoes <= datetime.datetime.now() <= self.fim_avaliacoes
        return False

    def is_em_periodo_de_recurso_edital(self):
        if self.inicio_recursos_edital and self.fim_recursos_edital:
            return self.inicio_recursos_edital <= datetime.datetime.now() <= self.fim_recursos_edital
        return False

    def is_em_periodo_de_recursos(self):
        if self.inicio_recursos and self.fim_recursos:
            return self.inicio_recursos <= datetime.datetime.now() <= self.fim_recursos
        return False

    def is_em_periodo_de_inscricao_servidor(self, servidor):
        return self.is_em_periodo_de_inscricao() and self.cargos.filter(pk=servidor.cargo_emprego.pk).exists()

    def is_em_periodo_de_recurso_edital_servidor(self, servidor):
        return self.is_em_periodo_de_recurso_edital() and self.cargos.filter(pk=servidor.cargo_emprego.pk).exists()

    def is_em_periodo_de_recurso_servidor(self, servidor):
        return self.is_em_periodo_de_recursos() and self.cargos.filter(pk=servidor.cargo_emprego.pk).exists()

    def is_pode_exibir_resultado(self):
        return self.inicio_resultados <= datetime.datetime.now() if self.inicio_resultados else False

    def is_pode_exibir_resultado_recurso(self):
        return self.resultado_recursos <= datetime.datetime.now() if self.resultado_recursos else False

    def get_url_inscrever(self):
        return f'/remanejamento/inscrever/{self.pk}/'

    def get_url_recurso(self):
        return f'/remanejamento/recurso_edital/{self.pk}/'


class EditalRecurso(models.ModelPlus):
    """
    Recursos impetrados contra o Edital
    """

    edital = models.ForeignKeyPlus('remanejamento.edital', verbose_name='Edital', on_delete=models.CASCADE)
    servidor = models.ForeignKeyPlus('rh.servidor', verbose_name="Servidor", null=True, on_delete=models.CASCADE)
    recurso_texto = models.TextField('Texto do Recurso', blank=True)
    dh_recurso = models.DateTimeField(auto_now_add=True, verbose_name='Horário de cadastro do recurso')
    recurso_resposta = models.TextField('Resposta ao Recurso', blank=True)
    dh_resposta = models.DateTimeField(verbose_name='Horário de cadastro da resposta ao recurso', null=True, blank=True)
    recurso_respondido = models.BooleanField(verbose_name="O recurso foi respondido?", default=False)

    class Meta:
        verbose_name = 'Recurso ao Edital'
        verbose_name_plural = 'Recursos ao Edital'

    def get_absolute_url(self):
        return f"/remanejamento/visualizar_recurso_edital/{self.pk}/".format()

    def pode_exibir_resposta_recurso_edital(self, user):
        if not self.recurso_resposta or not self.edital.resultado_recursos_edital:
            return False
        return self.edital.resultado_recursos_edital <= datetime.datetime.now() or user in self.edital.coordenadores.all()


class Disciplina(models.ModelPlus):
    """
    Disciplinas disponíveis para um determinado Edital.
    É usado em remanejamento para docentes.
    """

    edital = models.ForeignKeyPlus('remanejamento.edital', on_delete=models.CASCADE)
    descricao = models.CharField('Descrição', max_length=255)
    avaliadores = models.ManyToManyField('comum.User')

    class Meta:
        ordering = ['-edital', 'descricao']
        unique_together = ('edital', 'descricao')

    def __str__(self):
        return '%s' % (self.descricao)

    @classmethod
    def get_avaliadores_ids(cls):
        avaliadores_ids = []
        for disciplina in cls.objects.all():
            avaliadores_ids += disciplina.avaliadores.values_list('id', flat=True)
        return list(set(avaliadores_ids))


class DisciplinaItem(models.ModelPlus):
    disciplina = models.ForeignKeyPlus('remanejamento.disciplina', on_delete=models.CASCADE)
    descricao = models.TextField('Descrição')
    sequencia = models.PositiveIntegerField('Sequência')
    nao_avaliar = models.BooleanField('Não avaliar', default=False, help_text="será exibido na tela de avaliação, mas não será solicitado a porcentagem.")

    class Meta:
        ordering = ['disciplina', 'sequencia']
        verbose_name = 'Critério de avaliação de disciplina'
        verbose_name_plural = 'Critérios de avaliação de disciplinas'
        unique_together = (('disciplina', 'descricao'), ('disciplina', 'sequencia'))

    def __str__(self):
        return '%s - %s' % (self.disciplina, self.descricao)


class Inscricao(models.ModelPlus):
    horario = models.DateTimeField(auto_now_add=True, verbose_name='Horário')
    edital = models.ForeignKeyPlus('remanejamento.edital', on_delete=models.CASCADE)
    disciplina = models.ForeignKeyPlus(Disciplina, null=True, blank=True, on_delete=models.CASCADE)
    servidor = models.ForeignKeyPlus('rh.servidor', null=True, verbose_name="Servidor", on_delete=models.CASCADE)
    inicio_exercicio = models.DateFieldPlus(verbose_name='Início de exercício')
    anexo = models.FileFieldPlus(upload_to='remanejamento/anexos/', max_length=255, blank=True)
    dou_numero = models.CharField('Número', max_length=255)
    dou_data = models.DateFieldPlus(verbose_name='Data')
    dou_pagina = models.CharField('Página', max_length=255)
    dou_sessao = models.CharField('Seção', max_length=255)
    classificacao_concurso = models.PositiveIntegerField('Classificação no concurso para ingresso no IFRN')
    jornada_trabalho = models.ForeignKeyPlus('rh.jornadatrabalho', on_delete=models.CASCADE)
    frase_pura = models.TextField(help_text='Este campo é o que o candidato pode ver')
    frase_pura_com_chave = models.TextField(help_text='Em nenhuma hipótese um candidato pode ver este campo')
    frase_hash = models.CharField(
        max_length=128, help_text='Este campo é o que o candidato pode ver. Juntamente com ' '"frase_pura", é a garantia de que os dados inseridos pelo usuário ' 'estão intactos.'
    )
    recurso_texto = models.TextField('Texto do Recurso', blank=True)
    confirmada = models.BooleanField(default=True)
    observacao = models.TextField('Observações', blank=True)
    data_desistencia = models.DateTimeFieldPlus(null=True, blank=True, verbose_name='Data/hora da desistência')

    # Avaliação
    avaliacao_avaliador = models.ForeignKeyPlus('comum.User', null=True, blank=True, on_delete=models.CASCADE, verbose_name='Avaliador da inscrição')
    avaliacao_status = models.CharField(
        max_length=255,
        default='Pendente',
        blank=True,
        verbose_name='Status avaliação',
        choices=[
            ['Pendente', 'Pendente'],
            ['Aguardando habilitação da banca', 'Aguardando habilitação da banca'],
            ['Habilitado', 'Habilitado'],
            ['Não habilitado', 'Não habilitado'],
            ['Avaliado', 'Avaliado'],
            ['Apto', 'Apto'],
            ['Não apto', 'Não apto'],
        ],
    )
    avaliacao_score = models.FloatField(null=True, blank=True, verbose_name='Score')
    avaliacao_recurso = models.TextField('Resposta ao recurso', blank=True)

    class Meta:
        verbose_name = 'Inscrição'
        verbose_name_plural = 'Inscrições'

    @transaction.atomic()
    def save(self, *args, **kwargs):
        """
        O método foi sobrescrito para preencher automaticamente o campo ``confirmada``.
        """
        # Vamos desconfirmar as inscrições anteriores para o mesmo edital e disciplina
        # caso esteja cadastrando uma nova inscrição
        if not self.pk:
            self.confirmada = True
            Inscricao.objects.filter(servidor=self.servidor, edital=self.edital, disciplina=self.disciplina).update(confirmada=False)

        super(Inscricao, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return '/remanejamento/inscricao/%d/' % self.pk

    def atualizar_frases(self):
        self.frase_pura, self.frase_pura_com_chave = self.get_frase_pura_e_com_chave()
        self.frase_hash = self.get_frase_hash()
        self.save()

    def efetivar_desistencia(self):
        self.confirmada = False
        self.data_desistencia = datetime.datetime.now()
        self.save()

    def get_frase_pura_e_com_chave(self):

        # Itens padrão
        itens = [
            'id',
            str(self.pk),
            'horario',
            str(self.horario),
            'edital',
            str(self.edital.titulo),
            'servidor',
            str(self.servidor),
            'inicio_exercicio',
            str(self.inicio_exercicio),
            'dou_numero',
            str(self.dou_numero),
            'dou_data',
            str(self.dou_data),
            'dou_pagina',
            str(self.dou_pagina),
            'dou_sessao',
            str(self.dou_sessao),
            'classificacao_concurso',
            str(self.classificacao_concurso),
            'jornada_trabalho',
            str(self.jornada_trabalho),
        ]

        # Adicionando ``self.inscricaoitem_set.all()``
        for item in self.inscricaoitem_set.all():
            itens.append(str(item.campus))
            itens.append(str(item.preferencia))

        if self.disciplina:
            itens.append('Disciplina')
            itens.append(str(self.disciplina))

        frase_pura = []
        for idx, i in enumerate(itens):
            frase_pura.append(i)
            if idx % 2 == 0:  # label
                frase_pura.append(': ')
            elif idx != (len(itens) - 1):  # valor e não é o último
                frase_pura.append(' | ')
        frase_pura = ''.join(frase_pura)
        frase_pura_com_chave = frase_pura + ' | ' + self.edital.chave_hash
        return to_ascii(frase_pura).upper(), to_ascii(frase_pura_com_chave).upper()

    def get_frase_hash(self):
        return hashlib.sha512(self.frase_pura_com_chave.encode('utf-8')).hexdigest()

    def pode_ver(self, user):
        """Testa se o usuário pode ver a inscrição"""
        return any(
            [user.is_superuser, self.servidor.get_vinculo().user == user, user in self.edital.coordenadores.all(), self.disciplina and user in self.disciplina.avaliadores.all()]
        )

    def pode_mudar_status(self, user):
        """Testa se o usuário pode mudar o status da inscrição"""
        return self.disciplina and any([user.is_superuser, user in self.edital.coordenadores.all()])

    def avaliador_pode_habilitar(self, user):
        """
        Testa se o usuário pode mudar o status da inscrição para 
        `Não Habilitado`.
        """
        return self.pode_avaliar(user) and self.avaliacao_status == 'Aguardando habilitação da banca'

    def pode_ver_parecer(self, user):
        return self.pode_ver(user) and self.avaliacao_status in ('Apto', 'Não apto', 'Não habilitado') and self.disciplina.edital.is_pode_exibir_resultado()

    def pode_ver_resultado_recurso(self, user):
        return self.edital.is_pode_exibir_resultado_recurso() or user in self.edital.coordenadores.all()

    def pode_avaliar(self, user):
        """Testa se o usuário pode avaliar a inscrição"""
        if not self.disciplina:
            return False
        if not self.disciplina.edital.is_em_periodo_de_avaliacao():
            return False
        if self.avaliacao_status not in ['Aguardando habilitação da banca', 'Habilitado', 'Avaliado']:
            return False
        return any([user.is_superuser, user == self.avaliacao_avaliador, user in self.edital.coordenadores.all()])

    def pode_cadastrar_recurso(self, user):
        return all(
            [
                self.servidor.get_vinculo().user == user,
                self.confirmada,
                self.edital.is_em_periodo_de_recurso_servidor(self.servidor),
                not self.recurso_texto,
            ]
        )

    def pode_excluir_recurso(self, user):
        return all(
            [
                self.servidor.get_vinculo().user == user,
                self.confirmada,
                self.edital.is_em_periodo_de_recurso_servidor(self.servidor),
                self.recurso_texto,
            ]
        )

    def atualizar_score(self):
        valores = self.inscricaodisciplinaitem_set.values_list('apto_percentual', flat=True)
        if len(valores) > 0:
            self.avaliacao_score = float(sum(valores)) / len(valores)
            self.save()

    def is_habilitado(self):
        return self.avaliacao_status in ('Habilitado', 'Avaliado', 'Apto', 'Não apto')

    def is_apto(self):
        return self.avaliacao_status == 'Apto'

    def get_itens(self):
        return self.inscricaodisciplinaitem_set.all()

    def is_pode_desistir(self, user):
        if not self.edital.inicio_desistencias or not self.edital.fim_desistencias:
            return False
        if not (self.edital.inicio_desistencias <= datetime.datetime.now() and self.edital.fim_desistencias >= datetime.datetime.now()):
            return False
        return self.servidor.get_vinculo().user == user

    @classmethod
    def get_em_periodo_cancelamento_servidor(cls, servidor):
        agora = datetime.datetime.now()
        # se não é servidor retorna none
        if not servidor:
            return cls.objects.none()

        return cls.objects.filter(edital__inicio_desistencias__lte=agora, edital__fim_desistencias__gte=agora, data_desistencia__isnull=True, servidor=servidor)

    @classmethod
    def get_em_periodo_recurso_servidor(cls, servidor):
        agora = datetime.datetime.now()
        # se não é servidor retorna none
        if not servidor:
            return cls.objects.none()

        return cls.objects.filter(edital__inicio_recursos__lte=agora, edital__fim_recursos__gte=agora,
                                  servidor=servidor, recurso_texto='')


class InscricaoItem(models.ModelPlus):
    inscricao = models.ForeignKeyPlus('remanejamento.inscricao', on_delete=models.CASCADE)
    campus = models.ForeignKeyPlus('rh.UnidadeOrganizacional', on_delete=models.CASCADE)
    preferencia = models.PositiveIntegerField()

    class Meta:
        ordering = ['inscricao', 'preferencia']
        unique_together = (('inscricao', 'campus'), ('inscricao', 'preferencia'))


class InscricaoDisciplinaItem(models.ModelPlus):
    inscricao = models.ForeignKeyPlus('remanejamento.inscricao', on_delete=models.CASCADE)
    disciplina_item = models.ForeignKeyPlus('remanejamento.disciplinaitem', on_delete=models.CASCADE)
    apto = models.BooleanField(default=False)  # DEPRECATE
    apto_percentual = models.IntegerField()
    observacao = models.TextField('Observações', blank=True)

    class Meta:
        ordering = ['inscricao', 'disciplina_item']
        unique_together = ('inscricao', 'disciplina_item')
