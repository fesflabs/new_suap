# -*- coding: utf-8 -*-

from datetime import datetime
from decimal import Decimal

from django.apps.registry import apps
from django.core.exceptions import ValidationError
from django.db.models.aggregates import Sum
from django.db.transaction import atomic
from django.utils.safestring import mark_safe

from cursos.enums import SituacaoCurso, SituacaoParticipante, TipoCurso
from djtools.choices import Meses
from djtools.db import models
from djtools.templatetags.filters import format_money
from protocolo.models import Processo
from rh.models import UnidadeOrganizacional


class HorasPermitidas(models.ModelPlus):
    """
    São quantidades possíveis de serem escolhidos na ``CotaAnualServidor``. As quantidades padrão são 120 e 240 horas.
    """

    qtd_horas = models.FloatField(unique=True)
    default = models.BooleanField('Default?', default=False)

    class Meta:
        verbose_name = 'Horas Permitidas'
        verbose_name_plural = 'Horas Permitidas'

    def __str__(self):
        return str(self.qtd_horas)

    def save(self, *args, **kwargs):
        if self.default == True:
            HorasPermitidas.objects.all().update(default=False)
        super(HorasPermitidas, self).save(*args, **kwargs)


class Atividade(models.ModelPlus):
    SEARCH_FIELDS = ['descricao']
    """
    São as atividades a serem desempenhadas por um servidor em ``HorasTrabalhadas``.
    """
    descricao = models.TextField('Descrição', unique=True)
    valor_hora = models.DecimalFieldPlus('Valor da Hora')
    ativa = models.BooleanField('Ativa?', default=True)

    class Meta:
        verbose_name = 'Atividade'
        verbose_name_plural = 'Atividades'
        ordering = ['descricao']

    def __str__(self):
        return '{} ({})'.format(self.descricao, format_money(self.valor_hora))


class Curso(models.ModelPlus):
    """
    Representa tanto um curso quanto um concurso com participação do servidor.
    """

    SEARCH_FIELDS = ['descricao']

    descricao = models.TextField('Descrição')
    ano_pagamento = models.ForeignKeyPlus(
        'comum.Ano', on_delete=models.CASCADE, verbose_name='Ano de Pagamento', help_text='Ano referente ao pagamento das horas trabalhadas neste Curso/Concurso.'
    )
    edital = models.FileFieldPlus('Edital', upload_to='cursos/editais', blank=True)
    processos = models.ManyToManyFieldPlus(Processo, blank=True, verbose_name='Processos relacionados')
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus', on_delete=models.CASCADE)
    tipo = models.PositiveIntegerField('Tipo', blank=False, choices=TipoCurso.get_choices())
    situacao = models.PositiveIntegerField('Situação', null=False, blank=False, default=SituacaoCurso.NAO_INICIADO, choices=SituacaoCurso.get_choices())

    data_cadastro = models.DateTimeFieldPlus('Data de Cadastro', null=True, blank=True, auto_now_add=datetime.now())
    data_inicio = models.DateTimeFieldPlus('Data de Início do Curso', null=True, blank=True)
    data_cadastrado_folha = models.DateTimeFieldPlus('Data de Finalização do Curso', null=True, blank=True)

    responsaveis = models.ManyToManyFieldPlus('rh.Servidor', blank=True, verbose_name='Responsáveis')

    class Meta:
        verbose_name = 'Curso ou Concurso'
        verbose_name_plural = 'Cursos ou Concursos'
        unique_together = ('descricao', 'ano_pagamento')
        permissions = (
            ('pode_informar_cadastro_em_folha', 'Pode Informar Cadastro em Folha'),
            ('pode_gerenciar_participantes', 'Pode Gerenciar Participantes'),
            ('pode_ver_relatorio_pagamento_gecc', 'Pode Ver Relatório de Pagamento GECC'),
            ('pode_gerenciar_curso_concurso', 'Pode Gerenciar Curso/Concurso'),
        )

    @property
    def participantes(self):
        return self.participante_set.all().order_by('servidor__nome')

    ##################################################################
    # Verifica se o evento tem participante com pendência de pagamento
    ##################################################################
    def tem_participante_pendente(self):
        return self.participantes.filter(situacao=SituacaoParticipante.PENDENTE).exists()

    ############################################################
    # Lista participantes sem problema de pendência de pagamento
    ############################################################
    @property
    def participantes_sem_pendecia(self):
        return self.participantes.exclude(situacao=SituacaoParticipante.PENDENTE)

    ################################################
    # Lista participantes com pendência de pagamento
    ################################################
    @property
    def participantes_com_pendencia(self):
        return self.participantes.filter(situacao=SituacaoParticipante.PENDENTE)

    ####################################################################################################################
    # Lista os participantes de acordo com a situação do evento:
    # 1. se a situação do evento for "Cadastrado em Folha", mostra apenas os participantes sem pendência de pagamento
    # 2. se a situação do evento for diferente de "Cadastrado em Folha", mostra todos os participantes independente da situação
    ####################################################################################################################
    @property
    def get_participantes(self):
        retorno = self.participantes
        if self.situacao == SituacaoCurso.CADASTRADO_EM_FOLHA:
            retorno = self.participantes_sem_pendecia
        return retorno

    @property
    def tem_participante_sem_hora_trabalhada(self):
        return self.participantes.filter(situacao=SituacaoParticipante.LIBERADO, horas_trabalhada__isnull=True).exists()

    @property
    def tem_participante_aguardando_liberacao(self):
        return self.participantes.filter(situacao=SituacaoParticipante.AGUARDANDO_LIBERACAO).exists()

    def eh_responsavel(self, servidor):
        if servidor.eh_servidor:
            return self.responsaveis.filter(matricula=servidor.matricula).exists()
        return False

    def valor_total(self, situacoes=[SituacaoParticipante.LIBERADO, SituacaoParticipante.AGUARDANDO_LIBERACAO]):
        valor_total = 0
        for hora_trabalhada in self.participantes.filter(horas_trabalhada__isnull=False, situacao__in=situacoes):
            valor_total += hora_trabalhada.atividade.valor_hora * Decimal(str(hora_trabalhada.horas_trabalhada))
        return round(valor_total, 2)

    def horas_previstas_total(self, situacoes=[SituacaoParticipante.LIBERADO, SituacaoParticipante.AGUARDANDO_LIBERACAO]):
        horas = self.participantes.filter(situacao__in=situacoes).aggregate(horas_total=Sum('horas_prevista'))
        return horas.get('horas_total')

    def horas_trabalhadas_total(self, situacoes=[SituacaoParticipante.LIBERADO, SituacaoParticipante.AGUARDANDO_LIBERACAO]):
        horas = self.participantes.filter(situacao__in=situacoes).aggregate(horas_total=Sum('horas_trabalhada'))
        return horas.get('horas_total')

    def tem_participante_problema_horas(self):
        for participante in self.participantes.all().exclude(situacao__in=[SituacaoParticipante.NAO_LIBERADO, SituacaoParticipante.LIBERADO]):
            if participante.problema_com_horas:
                return True
        return False

    def pode_excluir_curso(self):
        if not self.horas_trabalhadas_total > 0:
            return False
        return True

    def pode_iniciar_curso(self):
        if (
            not self.tem_participante_problema_horas()
            and self.situacao == SituacaoCurso.NAO_INICIADO
            and not self.tem_participante_aguardando_liberacao
            and not self.participantes.filter(situacao=SituacaoParticipante.NAO_LIBERADO).exists()
            and self.participantes.exists()
        ):
            return True
        return False

    def pode_voltar_nao_iniciado(self):
        if self.horas_trabalhadas_total <= 0 and self.situacao == SituacaoCurso.INICIADO:
            return True
        return False

    '''
    Para finalizar um curso é preciso
    1 - A situação do curso está como INICIADO
    2 - Todos os participantes do curso estarem com suas horas trabalhadas cadastradas
    '''

    def pode_finalizar_curso(self):
        # verificando a situação do curso
        if self.situacao is not SituacaoCurso.INICIADO:
            return False
        # verificando horas trabalhadas
        for p in self.participantes.all():
            if p.horas_trabalhada is None:
                return False
        return True

    def pode_autorizar_pagamento(self):
        # verificando a situação do curso
        if self.situacao is not SituacaoCurso.FINALIZADO:
            return False
        # verificando horas trabalhadas
        for p in self.participantes.all():
            if p.horas_trabalhada is None:
                return False
        return True

    def pode_gerenciar_participante(self, usuario_logado):
        servidor = usuario_logado.get_relacionamento()
        if self.situacao == SituacaoCurso.NAO_INICIADO and (
            usuario_logado.has_perm('cursos.pode_gerenciar_participantes') or usuario_logado.is_superuser or self.eh_responsavel(servidor)
        ):
            return True
        return False

    def pode_remover_participante(self):
        if self.situacao == SituacaoCurso.NAO_INICIADO:
            return True
        return False

    def pode_adicionar_horas_participante(self):
        if self.situacao == SituacaoCurso.INICIADO:
            return True
        return False

    def pode_imprimir_listagem(self):
        return self.situacao in [SituacaoCurso.AGUARDANDO_CADASTRO_EM_FOLHA, SituacaoCurso.CADASTRADO_EM_FOLHA]

    def iniciar(self):
        if self.pode_iniciar_curso():
            self.situacao = SituacaoCurso.INICIADO
            self.data_inicio = datetime.now()
            self.save()
        else:
            raise ValidationError('Não foi possível iniciar o curso.')

    #
    # o metodo finalizar na verdade seta a situação da atividade para aguardando cadastro em folha
    @atomic
    def finalizar(self):
        if self.pode_finalizar_curso():
            self.situacao = SituacaoCurso.AGUARDANDO_CADASTRO_EM_FOLHA
            self.save()
        else:
            raise ValidationError('Este curso não pode ser finalizado.')

    @atomic
    def informar_cadastro_folha(self, request):
        CronogramaFolha = apps.get_model('rh', 'CronogramaFolha')
        cronograma = CronogramaFolha.get_cronograma_hoje()

        if cronograma:
            Participante.gerencia_participantes_no_cadastro_em_folha(self, request.POST.getlist('add_participante'), cronograma)
            self.situacao = SituacaoCurso.CADASTRADO_EM_FOLHA
            self.data_cadastrado_folha = datetime.now()
            self.save()
        else:
            raise ValidationError('Não existe cadastrado um cronograma para fechamento de folha que seja válido para os cálculos de pagamento.')

    def __str__(self):
        return self.descricao

    def get_absolute_url(self):
        return "/cursos/curso/{:d}/".format(self.id)

    get_absolute_url.short_description = 'Descrição'

    def save(self):
        if self.situacao == SituacaoCurso.INICIADO and self.tem_participante_problema_horas():
            raise ValidationError('O curso não pode ser iniciado pois existe participantes com problemas de carga horária.')
        super(Curso, self).save()

    def get_situacao_html(self):
        tipo = 'alert'
        if self.situacao == SituacaoCurso.NAO_INICIADO:
            tipo = 'error'
        if self.situacao == SituacaoCurso.CADASTRADO_EM_FOLHA:
            tipo = 'success'
        return mark_safe(f'<span class="status status-{tipo}">{self.get_situacao_display()}</span>')


class ParticipantesPendentesPagamentoManager(models.Manager):
    #
    # manager que retorna apenas os participantes pendentes de pagamento
    def get_queryset(self):
        qs = super(ParticipantesPendentesPagamentoManager, self).get_queryset().filter(situacao=SituacaoParticipante.PENDENTE)
        return qs


class Participante(models.ModelPlus):
    SEARCH_FIELDS = ['servidor__nome', 'servidor__matricula']
    VALOR_PADRAO_HORAS_TRABALHADAS = 120

    curso = models.ForeignKeyPlus(Curso, null=False, blank=False, verbose_name='Curso ou Concurso', on_delete=models.CASCADE)
    servidor = models.ForeignKeyPlus('rh.Servidor', null=False, blank=False, verbose_name='Servidor', on_delete=models.CASCADE)
    mes_pagamento = models.PositiveIntegerField('Mês de Pagamento', null=True, blank=True)
    atividade = models.ForeignKeyPlus(Atividade, null=False, blank=False, verbose_name='Atividade', on_delete=models.CASCADE)
    atividade_mes = models.PositiveIntegerField('Mês da Atividade', null=True, blank=True)
    horas_prevista = models.FloatField('Horas Previstas de Trabalho', null=False, blank=False)
    horas_trabalhada = models.FloatField('Horas Trabalhadas', null=True, blank=True)
    responsavel_liberacao = models.ForeignKeyPlus(
        'rh.Servidor', null=True, blank=True, verbose_name='Responsável pela Liberação', on_delete=models.CASCADE, related_name='responsavel_liberacao_set'
    )
    data_liberacao = models.DateTimeFieldPlus('Data da Liberação', null=True, blank=True)
    situacao = models.PositiveIntegerField('Situação', null=False, blank=False, default=SituacaoParticipante.AGUARDANDO_LIBERACAO, choices=SituacaoParticipante.get_choices())
    motivo_nao_liberacao = models.CharFieldPlus('Motivo do Indeferimento', max_length=500, null=True, blank=True)
    data_cadastro = models.DateTimeFieldPlus('Data de Cadastro', null=False, blank=False, auto_now_add=datetime.now())
    ano_desconto_carga_horaria = models.PositiveIntegerFieldPlus('Ano de Desconto da Carga Horária', null=True, blank=True)

    objects = models.Manager()
    pendentes = ParticipantesPendentesPagamentoManager()

    class Meta:
        verbose_name = 'Participante'
        verbose_name_plural = 'Participantes'
        permissions = (('pode_ver_seu_relatorio', 'Pode Ver o Próprio Relatório'),)

    def atividade_mes_display(self):
        return Meses.get_mes(self.atividade_mes)

    def mes_pagamento_display(self):
        if self.mes_pagamento:
            return Meses.get_mes(self.mes_pagamento)
        return None

    def get_ext_combo_template(self):
        return self.servidor.get_ext_combo_template()

    def __str__(self):
        return '{} ({})'.format(self.servidor.nome, self.servidor.matricula)

    '''
    quantidade de horas trabalhadas vezes o valor da hora da atividade
    '''

    @property
    def valor_total(self):
        return self.horas_trabalhada and self.atividade.valor_hora * Decimal(str(self.horas_trabalhada)) or None

    '''
    horas disponíveis no ano corrente
    '''

    @property
    def horas_disponiveis_ano(self):
        ano = self.curso.ano_pagamento
        horas_total = 0

        # verificando horas trabalhadas pelo servidor
        horas_total += self.servidor.qtd_horas_trabalhadas_gecc(ano)

        # verificando horas previstas de trabalhos em cursos/concursos que o servidor está inscrito.
        qtd_horas_previstas = self.servidor.participante_set.filter(
            curso__ano_pagamento=ano,
            horas_trabalhada__isnull=True,
            curso__situacao__in=[SituacaoCurso.NAO_INICIADO, SituacaoCurso.INICIADO],
            situacao=SituacaoParticipante.LIBERADO,
        ).aggregate(horas=Sum('horas_prevista'))
        horas_total += qtd_horas_previstas.get('horas') or 0

        # verificando se o servidor tem hora extra cadastrada para o ano corrente
        horas_extra = CotaExtra.cota_extra_servidor_no_ano(self.servidor, ano)

        return (self.VALOR_PADRAO_HORAS_TRABALHADAS + horas_extra) - horas_total

    @property
    def horas_trabalhadas_no_ano(self):
        return self.servidor.qtd_horas_trabalhadas_gecc(ano=self.curso.ano_pagamento)

    @property
    def horas_permitidas_no_ano(self):
        ano = self.curso.ano_pagamento
        servidor = self.servidor

        cota_extra = 0
        for cota in CotaExtra.objects.filter(ano=ano, servidor=servidor):
            cota_extra += cota.horas_permitida

        return self.VALOR_PADRAO_HORAS_TRABALHADAS + cota_extra

    @property
    def problema_com_horas(self):
        if self.horas_prevista > self.horas_disponiveis_ano:
            return True
        return False

    def get_situacao_html(self):
        if self.situacao == SituacaoParticipante.LIBERADO:
            return mark_safe('<span class="status status-aceito">Deferido</span>')
        if self.situacao == SituacaoParticipante.NAO_LIBERADO:
            return mark_safe('<span class="status status-impedido">Indeferido: {}</span>'.format(self.motivo_nao_liberacao))
        if self.problema_com_horas:
            return mark_safe('<span class="status status-impedido">Carga Horária Insuficiente</span>')
        if self.situacao == SituacaoParticipante.PENDENTE:
            return mark_safe('<span class="status status-pendente">Pendente de Pagamento</span>')
        if self.situacao == SituacaoParticipante.AGUARDANDO_LIBERACAO:
            return mark_safe('<span class="status status-pendente">Aguardando Liberação</span>')

    def deferir_participacao(self, responsavel):
        if not self.problema_com_horas:
            self.data_liberacao = datetime.now()
            self.responsavel_liberacao = responsavel
            self.situacao = SituacaoParticipante.LIBERADO
            self.save()
        else:
            raise ValidationError('Carga horária insuficiente para a participação no evento/atividade.')

    def indeferir_participacao(self, motivo):
        self.data_liberacao = datetime.now()
        self.situacao = SituacaoParticipante.NAO_LIBERADO
        self.motivo_nao_liberacao = motivo
        self.save()

    @classmethod
    def gerencia_participantes_no_cadastro_em_folha(cls, curso, ids_participantes, cronograma, apenas_pendentes=False):
        #
        # atualizando o mes de pagamento dos participantes para geração de relatórios
        curso.participantes.filter(id__in=ids_participantes).update(mes_pagamento=cronograma.mes, situacao=SituacaoParticipante.LIBERADO)

        #
        # se a checagem não for apenas de pendentes...
        if not apenas_pendentes:
            #
            # verifica se existe participante que ficou pendente de pagamento e atualiza a situação
            curso.participantes.exclude(id__in=ids_participantes).update(situacao=SituacaoParticipante.PENDENTE)


class CotaExtra(models.ModelPlus):
    SEARCH_FIELDS = ['servidor__nome', 'servidor__matricula']
    LIMITE_MAXIMO_POR_SERVIDOR = Participante.VALOR_PADRAO_HORAS_TRABALHADAS * 2  # o dobro do valor padrão

    servidor = models.ForeignKeyPlus('rh.Servidor', null=False, blank=False, verbose_name='Servidor', on_delete=models.CASCADE)
    ano = models.ForeignKeyPlus('comum.Ano', null=False, blank=False, verbose_name='Ano', on_delete=models.CASCADE)
    horas_permitida = models.FloatField('Horas Permitidas', null=False, blank=False)
    processos = models.ManyToManyFieldPlus(Processo, blank=True, verbose_name='Processos relacionados')
    data_cadastro = models.DateTimeFieldPlus('Data de Cadastro', null=False, blank=False, auto_now_add=datetime.now())

    class Meta:
        verbose_name = 'Cota Extra'
        verbose_name_plural = 'Cotas Extras'

    @classmethod
    def cota_extra_servidor_no_ano(cls, servidor, ano):
        qs_cotas = CotaExtra.objects.filter(ano=ano, servidor=servidor)
        saldo_cadastrado = 0
        for c in qs_cotas:
            saldo_cadastrado += c.horas_permitida
        return saldo_cadastrado


# TODO REMOVER A CLASSE COTAANUALSERVIDOR
class CotaAnualServidor(models.ModelPlus):
    """
    Representa a quantidade máxima de horas a serem trabalhadas por um servidor num ano.
    """

    vinculo = models.ForeignKeyPlus('comum.Vinculo')
    ano_pagamento = models.ForeignKeyPlus('comum.Ano', on_delete=models.CASCADE)
    horas_permitidas = models.ForeignKeyPlus(HorasPermitidas, on_delete=models.CASCADE)
    observacao = models.TextField('Observação', blank=True)

    class Meta:
        verbose_name = 'Cota anual do servidor'
        verbose_name_plural = 'Cotas anuais de servidores'
        unique_together = ('vinculo', 'ano_pagamento')

    def __str__(self):
        return '{} / {}'.format(self.vinculo.pessoa.nome, str(self.ano_pagamento))

    def matricula(self):
        return self.vinculo.relacionamento.matricula

    matricula.short_description = 'Matrícula'


# TODO REMOVER A CLASSE HORASTRABALHADAS
class HorasTrabalhadas(models.ModelPlus):
    """
    Representa a discriminação das horas trabalhadas num curso ou concurso por um servidor.
    """

    curso = models.ForeignKeyPlus(Curso, on_delete=models.CASCADE)
    cota_anual_servidor = models.ForeignKeyPlus(CotaAnualServidor, editable=False, on_delete=models.CASCADE)
    mes_pagamento = models.PositiveIntegerField('Mês de Pagamento', choices=Meses.get_choices())
    atividade = models.ForeignKeyPlus(Atividade, on_delete=models.CASCADE)
    atividade_valor_hora = models.DecimalFieldPlus(editable=False, help_text='Replicado devido a possibilidade de mudança no valor da hora da atividade relacionada.')
    qtd_horas = models.FloatField()

    class Meta:
        ordering = ('mes_pagamento', 'cota_anual_servidor__vinculo__pessoa__nome')
        verbose_name = 'Horas Trabalhadas'
        verbose_name_plural = 'Horas Trabalhadas'
        unique_together = ('curso', 'cota_anual_servidor', 'mes_pagamento', 'atividade', 'atividade_valor_hora')
