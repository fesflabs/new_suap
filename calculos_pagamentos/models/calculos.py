# -*- coding: utf-8 -*-

import calendar
from datetime import datetime
from decimal import Decimal
from comum.utils import tl

from ckeditor.fields import RichTextField
from django.core.exceptions import ValidationError
from django.db.models.aggregates import Sum, Min, Max
from django.template.loader import get_template

from comum.models import FuncaoCodigo
from comum.utils import get_setor
from djtools.db import models
from djtools.db.models import ModelPlus, Q
from documento_eletronico.models import Documento, DocumentoTexto, ModeloDocumento
from rh.models import UnidadeOrganizacional, Servidor, JornadaTrabalho, Titulacao

TIPO_CALCULO_CHOICES = [
    [1, 'Cálculo de Substituição'],
    [2, 'Cálculo de Progressão'],
    [3, 'Cálculo de Periculosidade'],
    [4, 'Cálculo de Insalubridade'],
    [5, 'Cálculo de RT'],
    [6, 'Cálculo de RSC'],
    [7, 'Cálculo de IQ'],
    [8, 'Cálculo de Mudança de Regime'],
    [9, 'Cálculo de Auxílio Transporte'],
    [10, 'Cálculo de Abono de Permanência'],
    [11, 'Cálculo de Nomeação de CD'],
    [12, 'Cálculo de Exoneração de CD'],
    [13, 'Cálculo de Designação de FG/FUC'],
    [14, 'Cálculo de Dispensa de FG/FUC'],
    [15, 'Cálculo de Acerto de Término de Contrato Temporário - Professor Substituto'],
    [16, 'Cálculo de Acerto de Término de Contrato Temporário - Intérprete de Libras'],
]


def getClasseCalculo(x):
    return {
        1: CalculoSubstituicao,
        2: CalculoProgressao,
        3: CalculoPericulosidade,
        4: CalculoInsalubridade,
        5: CalculoRT,
        6: CalculoRSC,
        7: CalculoIQ,
        8: CalculoMudancaRegime,
        9: CalculoTransporte,
        10: CalculoPermanencia,
        11: CalculoNomeacaoCD,
        12: CalculoExoneracaoCD,
        13: CalculoDesignacaoFG,
        14: CalculoDispensaFG,
        15: CalculoTerminoContratoProfSubs,
        16: CalculoTerminoContratoInterpLibras,
    }[x]


# # # CÁLCULO DE SUBSTITUIÇÃO # # #

# IFMA/Tássio - Valor de pagamento por período para cada código de função usado pelo IFMA.
class ValorPorFuncao(ModelPlus):
    funcao = models.ForeignKeyPlus(FuncaoCodigo, null=False, related_name='funcaocodigo4valorporfuncao', verbose_name='Cargo/Função')
    valor = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    data_inicio = models.DateFieldPlus(verbose_name='Data de início do valor', null=True, blank=True)
    data_fim = models.DateFieldPlus(verbose_name='Data de fim do valor', null=True, blank=True)

    def __unicode__(self):
        return '{} ({} - {}) - R${}'.format(
            self.funcao,
            self.data_inicio and self.data_inicio.strftime('%d/%m/%Y') or 'Anteriormente',
            self.data_fim and self.data_fim.strftime('%d/%m/%Y') or 'Atualmente',
            self.valor,
        )

    def __str__(self):
        return '{} ({} - {}) - R${}'.format(
            self.funcao,
            self.data_inicio and self.data_inicio.strftime('%d/%m/%Y') or 'Anteriormente',
            self.data_fim and self.data_fim.strftime('%d/%m/%Y') or 'Atualmente',
            self.valor,
        )

    class Meta:
        ordering = ['funcao', '-data_fim']
        verbose_name = 'Valor Por Função'
        verbose_name_plural = 'Valores Por Função'

    def clean(self):
        if not self.data_inicio and not self.data_fim:
            raise ValidationError('Informe pelo menos uma das duas datas solicitadas para o valor desta função.')

        if self.data_inicio:
            qs = ValorPorFuncao.objects.filter(funcao=self.funcao, data_inicio__lte=self.data_inicio, data_fim__gte=self.data_inicio)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError('A data de início informada está dentro, ou no limite, de outro período já registrado' ' para esta função.')
            qs = ValorPorFuncao.objects.filter(funcao=self.funcao, data_inicio__lte=self.data_inicio, data_fim__isnull=True)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError(
                    'A data de início informada está após, ou no limite, a data de início de outro período já '
                    'registrado para esta função que não tem data de término. Inclua a data de término '
                    'do outro período antes de criar um novo.'
                )

        if self.data_fim:
            qs = ValorPorFuncao.objects.filter(funcao=self.funcao, data_inicio__lte=self.data_fim, data_fim__gte=self.data_fim)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError('A data de fim informada está dentro, ou no limite, de outro período já registrado' ' para esta função.')

            qs = ValorPorFuncao.objects.filter(funcao=self.funcao, data_inicio__isnull=True, data_fim__gte=self.data_fim)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError(
                    'A data de fim informada está antes, ou no limite, da data de fim de outro período já '
                    'registrado para esta função que não tem data de início. Inclua a data de início '
                    'do outro período antes de criar um novo.'
                )

        if self.data_inicio and self.data_fim:
            qs = ValorPorFuncao.objects.filter(funcao=self.funcao, data_inicio__gte=self.data_inicio, data_fim__lte=self.data_fim)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError('O período informado engloba outros períodos já cadastrados. Não é possível ' 'cadastrar um período nesta condição.')


# # # CLASSES E MÉTODOS GERAIS DE CÁLCULOS # # #

# IFMA/Tássio
class NivelVencimento(ModelPlus):

    codigo = models.CharField(verbose_name='Código do nível', max_length=16, null=False, unique=True)
    categoria = models.CharField(max_length=30, null=True, choices=[['docente', 'Docente'], ['tecnico_administrativo', 'Técnico-Administrativo']], default='tecnico_administrativo')

    def __unicode__(self):
        return '{} - {}'.format(self.get_categoria(), self.codigo)

    def __str__(self):
        return '{} - {}'.format(self.get_categoria(), self.codigo)

    class Meta:
        verbose_name = 'Nível de Vencimento'
        verbose_name_plural = 'Níveis de Vencimento'
        ordering = ['id']

    def get_categoria(self):
        if self.categoria == 'docente':
            return 'Docente'
        if self.categoria == 'tecnico_administrativo':
            return 'Técnico-Administrativo'
        return None


# IFMA/Tássio - Nível de Vencimento TAE correspondente a cada combinação de Classe e Padrão de Vencimento
class NivelVencimentoTAEPorClasseEPadrao(ModelPlus):
    cargo_classe = models.ForeignKeyPlus(
        'rh.CargoClasse', null=False, on_delete=models.CASCADE, verbose_name='Classe TAE', related_name='cargoclasse4nivelvencimentoTAEporclasseepadrao'
    )
    nivel_padrao = models.CharField(max_length=3, null=False, blank=False, verbose_name='Padrão de Vencimento')
    nivel = models.ForeignKeyPlus(NivelVencimento, null=False, verbose_name='Nível de Vencimento de TAE', limit_choices_to={'categoria': 'tecnico_administrativo'})

    def __unicode__(self):
        return '{} + {} = {}'.format(self.cargo_classe, self.nivel_padrao, self.nivel)

    def __str__(self):
        return '{} + {} = {}'.format(self.cargo_classe, self.nivel_padrao, self.nivel)

    class Meta:
        ordering = ['cargo_classe', 'nivel_padrao', 'nivel']
        verbose_name = 'Nível de Vencimento de TAE por Classe e Padrão de Vencimento'
        verbose_name_plural = 'Níveis de Vencimento de TAE por Classe e Padrão de Vencimento'


# IFMA/Tássio - Valor do Nível de Vencimento em um período.
class ValorPorNivelVencimento(ModelPlus):
    nivel = models.ForeignKeyPlus(NivelVencimento, null=False, related_name='valores_do_nivel', verbose_name='Nível de Vencimento')
    valor = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    data_inicio = models.DateFieldPlus(verbose_name='Data de início do valor', null=True, blank=True)
    data_fim = models.DateFieldPlus(verbose_name='Data de fim do valor', null=True, blank=True)

    def __unicode__(self):
        return '{} ({} - {})'.format(
            self.nivel, self.data_inicio and self.data_inicio.strftime('%d/%m/%Y') or 'Anteriormente', self.data_fim and self.data_fim.strftime('%d/%m/%Y') or 'Atualmente'
        )

    def __str__(self):
        return '{} ({} - {})'.format(
            self.nivel, self.data_inicio and self.data_inicio.strftime('%d/%m/%Y') or 'Anteriormente', self.data_fim and self.data_fim.strftime('%d/%m/%Y') or 'Atualmente'
        )

    class Meta:
        ordering = ['nivel', '-data_fim']
        verbose_name = 'Valor Por Nível de Vencimento de TAE'  # Incluído TAE para título nas telas admin
        verbose_name_plural = 'Valores Por Nível de Vencimento de TAE'  # Incluído TAE para título nas telas admin

    def clean(self):
        if not self.data_inicio and not self.data_fim:
            raise ValidationError('Informe pelo menos uma das duas datas solicitadas para o valor deste nível.')

        if self.data_inicio:
            qs = ValorPorNivelVencimento.objects.filter(nivel=self.nivel, data_inicio__lte=self.data_inicio, data_fim__gte=self.data_inicio)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError('A data de início informada está dentro, ou no limite, de outro período já registrado' ' para este nível.')
            qs = ValorPorNivelVencimento.objects.filter(nivel=self.nivel, data_inicio__lte=self.data_inicio, data_fim__isnull=True)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError(
                    'A data de início informada está após, ou no limite, a data de início de outro período já '
                    'registrado para este nível que não tem data de término. Inclua a data de término '
                    'do outro período antes de criar um novo.'
                )

        if self.data_fim:
            qs = ValorPorNivelVencimento.objects.filter(nivel=self.nivel, data_inicio__lte=self.data_fim, data_fim__gte=self.data_fim)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError('A data de fim informada está dentro, ou no limite, de outro período já registrado' ' para este nível.')

            qs = ValorPorNivelVencimento.objects.filter(nivel=self.nivel, data_inicio__isnull=True, data_fim__gte=self.data_fim)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError(
                    'A data de fim informada está antes, ou no limite, da data de fim de outro período já '
                    'registrado para este nível que não tem data de início. Inclua a data de início '
                    'do outro período antes de criar um novo.'
                )

        if self.data_inicio and self.data_fim:
            qs = ValorPorNivelVencimento.objects.filter(nivel=self.nivel, data_inicio__gte=self.data_inicio, data_fim__lte=self.data_fim)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError('O período informado engloba outros períodos já cadastrados. Não é possível ' 'cadastrar um período nesta condição.')


# IFMA/Tássio - Valor do Nível de Vencimento Docente para uma Joranada de Trabalho.
class ValorPorNivelVencimentoDocente(ValorPorNivelVencimento):
    jornada_trabalho = models.ForeignKeyPlus(JornadaTrabalho, null=False, verbose_name='Jornada de Trabalho', related_name='jornada4valorpornivelvencimentodocente')

    class Meta:
        verbose_name = 'Valor Por Nível de Vencimento Docente e Carga Horária'
        verbose_name_plural = 'Valores Por Nível de Vencimento Docente e Carga Horária'

    def __unicode__(self):
        return '{} - {} ({} - {})'.format(
            self.nivel,
            self.jornada_trabalho,
            self.data_inicio and self.data_inicio.strftime('%d/%m/%Y') or 'Anteriormente',
            self.data_fim and self.data_fim.strftime('%d/%m/%Y') or 'Atualmente',
        )

    def __str__(self):
        return '{} - {} ({} - {})'.format(
            self.nivel,
            self.jornada_trabalho,
            self.data_inicio and self.data_inicio.strftime('%d/%m/%Y') or 'Anteriormente',
            self.data_fim and self.data_fim.strftime('%d/%m/%Y') or 'Atualmente',
        )

    def clean(self):
        return


# IFMA/Tássio - Valor da Retribuição por Titulação.
class ValorRetribuicaoTitulacao(ModelPlus):
    nivel = models.ForeignKeyPlus(NivelVencimento, null=False, verbose_name='Nível de Vencimento', limit_choices_to={'categoria': 'docente'})
    jornada_trabalho = models.ForeignKeyPlus(JornadaTrabalho, null=False, verbose_name='Jornada de Trabalho', related_name='jornada4valorretribuicaotitulacao')
    titulacoes = models.ManyToManyField(
        Titulacao,
        blank=False,
        verbose_name='Titulações',
        limit_choices_to=Q(codigo__gte='23') & Q(codigo__lte='27') | Q(codigo__gte='48') & Q(codigo__lte='50'),
        related_name='titulacao4valorretribuicaotitulacao',
    )
    valor = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    data_inicio = models.DateFieldPlus(verbose_name='Data de início do valor', null=True, blank=True)
    data_fim = models.DateFieldPlus(verbose_name='Data de fim do valor', null=True, blank=True)

    def __unicode__(self):
        return '{} - {} - {} ({} - {})'.format(
            self.nivel,
            self.jornada_trabalho,
            self.get_titulacoes_as_string(),
            self.data_inicio and self.data_inicio.strftime('%d/%m/%Y') or 'Anteriormente',
            self.data_fim and self.data_fim.strftime('%d/%m/%Y') or 'Atualmente',
        )

    def __str__(self):
        return '{} - {} - {} ({} - {})'.format(
            self.nivel,
            self.jornada_trabalho,
            self.get_titulacoes_as_string(),
            self.data_inicio and self.data_inicio.strftime('%d/%m/%Y') or 'Anteriormente',
            self.data_fim and self.data_fim.strftime('%d/%m/%Y') or 'Atualmente',
        )

    class Meta:
        ordering = ['nivel', '-data_fim']
        verbose_name = 'Valor de Retribuição Por Titulação'
        verbose_name_plural = 'Valores de Retribuição Por Titulação'

    def get_titulacoes_as_string(self):
        string = ''
        for titulacao in self.titulacoes.all():
            if string == '':
                string = str(titulacao)
            else:
                string += ', ' + str(titulacao)
        return string


# IFMA/Tássio - Classe geral para cálculos.
class Calculo(ModelPlus):
    servidor = models.ForeignKeyPlus(Servidor, verbose_name='Servidor Interessado')
    justificativa = RichTextField(verbose_name="Justificativa", blank=True)
    observacoes = RichTextField(verbose_name="Observações.", blank=True)

    atesto = models.BooleanField('Atesto', default=False)
    atestador = models.ForeignKeyPlus('comum.User', verbose_name="Usuário atestador")
    data_criacao = models.DateTimeFieldPlus('Data de Criação', null=False, auto_now_add=True)

    total = models.DecimalFieldPlus(null=False, default=0.0)
    tipo = models.PositiveIntegerField('Tipo do Cálculo', choices=TIPO_CALCULO_CHOICES, null=False, default=0)
    excluido = models.BooleanField(default=False, verbose_name='Excluído')

    class Meta:
        verbose_name = 'Cálculo'
        verbose_name_plural = 'Cálculos'

    def get_calculo_espeficico(self):
        return getClasseCalculo(self.tipo).objects.get(pk=self.pk)

    def __unicode__(self):
        return self.get_calculo_espeficico().__unicode__()

    def __str__(self):
        return self.get_calculo_espeficico().__unicode__()

    def get_absolute_url(self):
        calculo = self.get_calculo_espeficico()
        return '/{}/{}/'.format(calculo._meta.label_lower.replace(".", "/"), calculo.id)

    def clean(self):
        if not self.atesto:
            raise ValidationError({'atesto': 'Você não pode salvar o cálculo sem atestar que todas as informações ' 'acima estão corretamente preenchidas.'})

    def get_valor_detalhamento(self, atributo, gratificacao, data_inicio, data_fim):
        '''
        :param atributo: string com o nome do atribito
        :param gratificacao: booleano se é um valor de gratificação ou não
        :param data_inicio: data de início dos detalhamentos a considerar
        :param data_fim: data de fim dos detalhamentos a considerar
        :return: somatório dos valores dos objetos da classe get_detalhamento_model associadas a este cálculo e com os
                    parâmetros passados.
        '''
        valor = 0
        detalhamentos = self.get_detalhamento_model().objects.filter(periodo__calculo=self, gratificacao=gratificacao, data_inicio__gte=data_inicio, data_fim__lte=data_fim)
        for detalhamento in detalhamentos:
            valor += getattr(detalhamento, atributo) or 0
        return valor

    def get_data_inicio(self):
        return self.get_detalhamento_model().objects.filter(periodo__calculo=self).aggregate(Min('data_inicio'))['data_inicio__min']

    def get_data_fim(self):
        return self.get_detalhamento_model().objects.filter(periodo__calculo=self).aggregate(Max('data_fim'))['data_fim__max']

    def tem_gratificacao(self):
        return self.get_detalhamento_model().objects.filter(periodo__calculo=self, gratificacao=True).exists()

    @property
    def pode_editar(self):
        return not self.pagamentos.filter(situacao__in=[1, 2, 3, 4, 5, 6]).exists() and not self.excluido

    @property
    def pode_excluir(self):
        return not self.pagamentos.filter(situacao__in=[1, 2, 3, 4, 5, 6]).exists() and not self.excluido


# IFMA/Tássio - Classe que guarda dados de uma portaria física
class PortariaFisica(ModelPlus):
    calculo = models.ForeignKeyPlus(Calculo, verbose_name='Cálculo')
    numero = models.PositiveIntegerField('Número da Portaria', null=False)
    data_portaria = models.DateFieldPlus('Data da Portaria', null=False)
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name="Campus da Portaria", null=False, related_name='campus4portariafisica')
    processo = models.ForeignKeyPlus(
        'protocolo.Processo',
        verbose_name='Processo Físico',
        null=True,
        blank=True,
        help_text="Informe um processo físico ou um processo eletrônico.",
        related_name='processo4portariafisica',
    )
    processo_eletronico = models.ForeignKeyPlus(
        'processo_eletronico.Processo', verbose_name='Processo Eletrônico', null=True, blank=True, related_name='processo_eletronico4portariafisica'
    )

    class Meta:
        verbose_name = 'Portaria Física'
        verbose_name_plural = 'Portarias Físicas'

    def __unicode__(self):
        return 'Portaria {}/{}'.format(self.numero, self.data_portaria.year)

    def __str__(self):
        return 'Portaria {}/{}'.format(self.numero, self.data_portaria.year)


# IFMA/Tássio - Classe geral para períodos de cálculos.
class Periodo(ModelPlus):
    data_inicio = models.DateFieldPlus('Data Inicial', null=False)
    data_fim = models.DateFieldPlus('Data Final', null=False)
    nivel = models.ForeignKeyPlus(NivelVencimento, null=False, blank=True, verbose_name='Nível de Vencimento', related_name="nivel4%(app_label)s_%(class)s")
    jornada = models.ForeignKeyPlus(JornadaTrabalho, null=False, verbose_name='Jornada de Trabalho', related_name="jornada4%(app_label)s_%(class)s")

    class Meta:
        abstract = True
        ordering = ['data_inicio']

    def __unicode__(self):
        return 'Período ({} - {})'.format(self.data_inicio.strftime('%d/%m/%Y'), self.data_fim.strftime('%d/%m/%Y'))


# IFMA/Tássio - Classe geral para detalhamentos.
class Detalhamento(ModelPlus):
    data_inicio = models.DateFieldPlus('Data Inicial', null=False)  # Início do mês
    data_fim = models.DateFieldPlus('Data Final', null=False)  # Fim do mês
    quant_dias = models.IntegerField(null=False)
    total = models.DecimalFieldPlus(null=False)
    gratificacao = models.BooleanField(default=False)

    class Meta:
        abstract = True
        ordering = ['data_inicio', 'gratificacao']


# IFMA/Tássio - Classe para férias.
class Ferias(ModelPlus):
    data_inicio = models.DateFieldPlus('Data Inicial do Primeiro Período de Férias', null=False)
    ano_referencia = models.PositiveIntegerField('Ano de Exercício/Referência', null=False, blank=False)
    total = models.DecimalFieldPlus(null=False)

    class Meta:
        abstract = True
        ordering = ['ano_referencia']

    def __unicode__(self):
        return 'Férias cadastradas'

    def clean(self):
        if self.ano_referencia:
            if not (datetime.now().date().year - 6 <= self.ano_referencia <= datetime.now().date().year):
                raise ValidationError({'ano_referencia': 'O ano de referência não é igual ao ano corrente ou até 6 anos anteriores a ele.'})


# Método de definição dos padrões usados pelo sistema
def padrao_choices():
    choices = []
    try:
        padroes = NivelVencimentoTAEPorClasseEPadrao.objects.all().order_by("nivel_padrao").distinct("nivel_padrao").values_list("nivel_padrao", flat=True)
        if padroes.exists():
            for p in padroes:
                choices.append([p, p])
    except Exception:
        pass
    return choices


# Métodos para filtrar as titulações referentes determinados cálculos
def titulacoes_choices():
    return Q(codigo__gte='23') & Q(codigo__lte='27')


def rsc_choices():
    return Q(codigo__gte='48') & Q(codigo__lte='50')


def all_titulacoes_choices():
    return titulacoes_choices() | rsc_choices()


# Opções para campos de adicionais de insalubridade
INSALUBRIDADE_CHOICES = [[0, 'Inexiste'], [10, '10%'], [20, '20%']]


# Opções para campos de IQ
IQ_CHOICES = [[0, 'Inexiste'], [10, '10%'], [15, '15%'], [20, '20%'], [25, '25%'], [30, '30%'], [35, '35%'], [52, '52%'], [75, '75%']]


# Opções para campos de quantidade de meses
MESES_CHOICES = [[0, 0], [1, 1], [2, 2], [3, 3], [4, 4], [5, 5], [6, 6], [7, 7], [8, 8], [9, 9], [10, 10], [11, 11], [12, 12]]


# Opções para campos de PSS
PSS_CHOICES = [[0, 'Sem desconto'], [8, '8%'], [9, '9%'], [11, '11%']]


class MotivoSubstituicao(ModelPlus):

    descricao = models.CharField(verbose_name='Descrição', max_length=400)

    def __unicode__(self):
        return '{}'.format(self.descricao)

    def __str__(self):
        return '{}'.format(self.descricao)

    class Meta:
        verbose_name = 'Motivo do Afastamento'
        verbose_name_plural = 'Motivos do Afastamento'


# # # CÁLCULO DE SUBSTITUIÇÃO # # #
class CalculoSubstituicao(Calculo):

    MOTIVO_FERIAS = 'ferias'
    MOTIVO_LICENCA_CAPACITACAO = 'licenca_capacitacao'
    MOTIVO_LICENCA_MEDICA = 'licenca_medica'
    MOTIVO_RECESSO_NATALINO = 'recesso_natalino'
    MOTIVO_VIAGEM = 'viagem'
    MOTIVO_OUTROS = 'outros'
    TIPOS_SUBSTITUICAO_CHOICE = (
        (MOTIVO_FERIAS, 'Férias'),
        (MOTIVO_LICENCA_CAPACITACAO, 'Licença Capacitação'),
        (MOTIVO_LICENCA_MEDICA, 'Licença Médica'),
        (MOTIVO_RECESSO_NATALINO, 'Recesso Natalino'),
        (MOTIVO_VIAGEM, 'Viagem'),
        (MOTIVO_OUTROS, 'Outros'),
    )

    total_grat = models.DecimalFieldPlus(null=False, default=0.0)

    # SUBSTITUIÇÃO
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name="Campus", null=False)

    # motivo_substituicao = models.CharFieldPlus('Motivo do Afastamento', choices=([('', '---------')] + list(TIPOS_SUBSTITUICAO_CHOICE)))
    motivo_substituicao = models.ForeignKeyPlus(MotivoSubstituicao, verbose_name="Motivo do Afastamento")

    # SUBSTITUTO
    funcao_servidor_substituto = models.ForeignKeyPlus(
        FuncaoCodigo,
        verbose_name='Função do Substituto',
        null=True,
        help_text='Selecione a função original do servidor substituto, se houver.',
        related_name='funcao_substituto4calculosubstituicao',
        blank=True,
    )
    data_inicio_funcao_servidor_substituto = models.DateFieldPlus(
        'Data Inicial da Função do Substituto', help_text='Preencha caso a função original tenha sido finalizada durante a substituição.', null=True, blank=True
    )
    data_fim_funcao_servidor_substituto = models.DateFieldPlus(
        'Data Final da Função do Substituto', help_text='Preencha caso a função original tenha sido finalizada durante a substituição.', null=True, blank=True
    )

    # TITULAR
    titular = models.ForeignKeyPlus(
        Servidor, verbose_name='Servidor Titular', null=True, blank=True, related_name='servidor_titular4calculosubstituicao', help_text='Este campo não é obrigatório.'
    )
    funcao_servidor_titular = models.ForeignKeyPlus(
        FuncaoCodigo, verbose_name='Função do Titular', help_text='Selecione a função do servidor titular.', null=False, related_name='funcao_titular4calculosubstituicao'
    )

    # RESULTADO
    resultado = models.TextField('Resultado')

    # IFMA Leonardo
    documento = models.ForeignKeyPlus('documento_eletronico.documentotexto', null=True, on_delete=models.PROTECT, verbose_name="Documento Eletrônico")

    class Meta:
        verbose_name = 'Cálculo de Substituição'
        verbose_name_plural = 'Cálculos de Substituição'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    # IFMA/Tássio: Método-Propriedade para retornar a primeira portaria
    @property
    def portaria(self):
        return self.portariafisica_set.first()

    def get_detalhamento_model(self):
        return DetalhamentoSubstituicao

    def save(self):
        self.total_grat = 0
        for periodo in self.periodosubstituicao_set.all():
            p = PeriodoSubstituicao.objects.filter(id=periodo.id).annotate(Sum('detalhamentosubstituicao__valor_grat'))[0]
            self.total_grat += p.detalhamentosubstituicao__valor_grat__sum or 0

        self.total = self.total_grat
        self.tipo = 1
        super(CalculoSubstituicao, self).save()
        # IFMA LEONARDO 04/12/2017
        # Comentado no IFRN
        # if self.portaria and self.portaria.processo_eletronico and self.resultado:
        #    self.gerar_documento_eletronico()
        # IFMA FIM LEONARDO 04/12/2017

    # IFMA Leonardo Rosa 04/12/2017
    def gerar_documento_eletronico(self):
        title = self.__unicode__()

        detalhamentos = DetalhamentoSubstituicao.objects.filter(periodo__calculo=self, gratificacao=False)
        gratificacoes = DetalhamentoSubstituicao.objects.filter(periodo__calculo=self, gratificacao=True)

        total = self.total
        template = get_template('calculos_pagamentos/templates/documentoeletronico_calculosubstituicao.html')
        html = template.render({'title': title, 'calculo': self, 'detalhamentos': detalhamentos, 'gratificacoes': gratificacoes, 'total': total})

        modelo = None
        try:
            modelo = ModeloDocumento.objects.get(nome='Cálculo Substituição')
        except Exception:
            raise Exception('Não existe o modelo de documento texto com nome de "Cálculo Substituição".')

        user = tl.get_user()

        assunto = title + ' - Portaria - ' + str(self.portaria.numero) + ' de  ' + str(self.portaria.data_portaria.strftime("%d/%m/%Y"))

        setordono = get_setor(user)

        if self.documento:
            documento_novo = DocumentoTexto.adicionar_documento_texto(
                usuario=user, setor_dono=setordono, assunto=assunto, modelo=modelo, nivel_acesso=Documento.NIVEL_ACESSO_PUBLICO, corpo=html, documento=self.documento.id
            )
        else:
            documento_novo = DocumentoTexto.adicionar_documento_texto(
                usuario=user, setor_dono=setordono, assunto=assunto, modelo=modelo, nivel_acesso=Documento.NIVEL_ACESSO_PUBLICO, corpo=html
            )
            self.documento = documento_novo
            self.save()
        return documento_novo

    # IFMA LEONARDO FIM

    def get_valor_substituicao(self, data_inicio, data_fim):
        return self.get_valor_detalhamento('valor_grat', False, data_inicio, data_fim)

    def get_valor_gratificacao(self, data_inicio, data_fim):
        return self.get_valor_detalhamento('total', True, data_inicio, data_fim)


# IFMA/Tássio - Classe para salvar os períodos de uma substituição específica.
class PeriodoSubstituicao(ModelPlus):
    calculo = models.ForeignKeyPlus(CalculoSubstituicao, verbose_name='Cálculo de Substituição')
    data_inicio = models.DateFieldPlus('Data Inicial', null=False)
    data_fim = models.DateFieldPlus('Data Final', null=False)

    class Meta:
        verbose_name = 'Período de Substituição'
        verbose_name_plural = 'Períodos de Substituição'
        ordering = ['data_inicio']

    def __unicode__(self):
        return 'Período ({} - {})'.format(self.data_inicio.strftime('%d/%m/%Y'), self.data_fim.strftime('%d/%m/%Y'))

    def __str__(self):
        return 'Período ({} - {})'.format(self.data_inicio.strftime('%d/%m/%Y'), self.data_fim.strftime('%d/%m/%Y'))


# IFMA/Tássio - Classe para salvar o detalhamento mensal de um determinado período de um pagamento por substituição.
class DetalhamentoSubstituicao(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoSubstituicao, verbose_name='Período de Substituição')
    valor_grat = models.DecimalFieldPlus(null=False)

    class Meta:
        ordering = ['data_inicio', 'id']

    def save(self):
        # Abaixo dava erro pois valores vinham como floats.
        self.total = Decimal(self.valor_grat)
        super(DetalhamentoSubstituicao, self).save()


# # # CÁLCULO DE PROGRESSÃO # # #

# IFMA/Tássio - Classe para calcular pagamento devido pela progressão de um servidor.
class CalculoProgressao(Calculo):
    total_venc = models.DecimalFieldPlus(null=False, default=0.0)
    total_rt = models.DecimalFieldPlus(null=False, default=0.0)
    total_anuenio = models.DecimalFieldPlus(null=False, default=0.0)
    total_per = models.DecimalFieldPlus(null=False, default=0.0)
    total_ins = models.DecimalFieldPlus(null=False, default=0.0)
    total_iq = models.DecimalFieldPlus(null=False, default=0.0)

    class Meta:
        verbose_name = 'Cálculo de Progressão'
        verbose_name_plural = 'Cálculos de Progressão'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.total_venc, self.total_rt, self.total_anuenio = 0, 0, 0
        self.total_per, self.total_ins, self.total_iq = 0, 0, 0
        for periodo in self.periodocalculoprogressao_set.all():
            p = PeriodoCalculoProgressao.objects.filter(id=periodo.id).annotate(
                Sum('detalhamentoprogressao__valor_venc'),
                Sum('detalhamentoprogressao__valor_rt'),
                Sum('detalhamentoprogressao__valor_anuenio'),
                Sum('detalhamentoprogressao__valor_per'),
                Sum('detalhamentoprogressao__valor_ins'),
                Sum('detalhamentoprogressao__valor_iq'),
            )[0]
            self.total_venc += p.detalhamentoprogressao__valor_venc__sum or 0
            self.total_rt += p.detalhamentoprogressao__valor_rt__sum or 0
            self.total_anuenio += p.detalhamentoprogressao__valor_anuenio__sum or 0
            self.total_per += p.detalhamentoprogressao__valor_per__sum or 0
            self.total_ins += p.detalhamentoprogressao__valor_ins__sum or 0
            self.total_iq += p.detalhamentoprogressao__valor_iq__sum or 0

            p = PeriodoCalculoProgressao.objects.filter(id=periodo.id).annotate(
                Sum('feriascalculoprogressao__valor_venc'),
                Sum('feriascalculoprogressao__valor_rt'),
                Sum('feriascalculoprogressao__valor_anuenio'),
                Sum('feriascalculoprogressao__valor_per'),
                Sum('feriascalculoprogressao__valor_ins'),
                Sum('feriascalculoprogressao__valor_iq'),
            )[0]
            self.total_venc += p.feriascalculoprogressao__valor_venc__sum or 0
            self.total_rt += p.feriascalculoprogressao__valor_rt__sum or 0
            self.total_anuenio += p.feriascalculoprogressao__valor_anuenio__sum or 0
            self.total_per += p.feriascalculoprogressao__valor_per__sum or 0
            self.total_ins += p.feriascalculoprogressao__valor_ins__sum or 0
            self.total_iq += p.feriascalculoprogressao__valor_iq__sum or 0

        self.total = self.total_venc + self.total_rt + self.total_anuenio + self.total_per + self.total_ins + self.total_iq
        self.tipo = 2
        super(CalculoProgressao, self).save()


# IFMA/Tássio - Classe para salvar os períodos com respectivos dados de um cálculo de progressão.
class PeriodoCalculoProgressao(Periodo):
    calculo = models.ForeignKeyPlus(CalculoProgressao, verbose_name='Cálculo de Progressão')
    nivel_passado = models.ForeignKeyPlus(
        NivelVencimento, null=False, blank=True, verbose_name='Nível de Vencimento Anterior', related_name="nivel_passado4%(app_label)s_%(class)s"
    )
    jornada_passada = models.ForeignKeyPlus(JornadaTrabalho, null=False, verbose_name='Jornada de Trabalho Anterior', related_name="jornada_passada4%(app_label)s_%(class)s")
    # Campos criados para facilitar o preenchimento de formulários pelos usuários
    padrao_vencimento_novo = models.CharField(max_length=3, null=True, blank=True, verbose_name='Padrão de Vencimento Novo')
    padrao_vencimento_passado = models.CharField(max_length=3, null=True, blank=True, verbose_name='Padrão de Vencimento Anterior')
    titulacao_passada = models.ForeignKeyPlus(
        Titulacao, null=True, blank=True, related_name='titulacao_passada4periodocalculoprogressao', verbose_name='Titulação Anterior', limit_choices_to=all_titulacoes_choices
    )

    titulacao_nova = models.ForeignKeyPlus(
        Titulacao, null=True, blank=True, related_name='titulacao_nova4periodocalculoprogressao', verbose_name='Titulação Nova', limit_choices_to=all_titulacoes_choices
    )
    anuenio = models.DecimalFieldPlus('Anuênio a Receber (%)', default=Decimal("0.0"), null=True, blank=True)
    periculosidade = models.BooleanField('Adicional de Periculosidade (10%)', default=False)
    insalubridade = models.PositiveIntegerField('Adicional de Insalubridade', choices=INSALUBRIDADE_CHOICES, null=True, blank=True, default=0)
    iq = models.PositiveIntegerField('Incentivo à Qualificação', choices=IQ_CHOICES, null=True, blank=True, default=0)

    class Meta(Periodo.Meta):
        verbose_name = 'Período do Cálculo de Progressão'
        verbose_name_plural = 'Períodos do Cálculo de Progressão'

    def get_ferias(self):
        return self.feriascalculoprogressao_set


# IFMA/Tássio - Classe para salvar o detalhamento mensal de um determinado período de um pagamento por progressao.
class DetalhamentoProgressao(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoCalculoProgressao, verbose_name='Período de Progressão', on_delete=models.CASCADE)
    valor_venc = models.DecimalFieldPlus(null=False)
    valor_rt = models.DecimalFieldPlus(null=True)
    valor_anuenio = models.DecimalFieldPlus(null=True)
    valor_per = models.DecimalFieldPlus(null=True)
    valor_ins = models.DecimalFieldPlus(null=True)
    valor_iq = models.DecimalFieldPlus(null=True)

    class Meta(Detalhamento.Meta):
        verbose_name = 'Detalhamento Mensal de Progressão'
        verbose_name_plural = 'Detalhamentos Mensais de Progressão'

    def save(self):
        # Abaixo dava erro pois valores vinham como floats.
        self.total = (
            Decimal(self.valor_venc)
            + Decimal(self.valor_rt or 0)
            + Decimal(self.valor_anuenio or 0)
            + Decimal(self.valor_per or 0)
            + Decimal(self.valor_ins or 0)
            + Decimal(self.valor_iq or 0)
        )
        super(DetalhamentoProgressao, self).save()


# IFMA/Tássio - Classe para salvar os dados de férias de um cálculo de progressão.
class FeriasCalculoProgressao(Ferias):
    periodo = models.ForeignKeyPlus(PeriodoCalculoProgressao, verbose_name='Período do Cálculo de Progressão')

    valor_venc = models.DecimalFieldPlus(null=False)
    valor_rt = models.DecimalFieldPlus(null=True)
    valor_anuenio = models.DecimalFieldPlus(null=True)
    valor_per = models.DecimalFieldPlus(null=True)
    valor_ins = models.DecimalFieldPlus(null=True)
    valor_iq = models.DecimalFieldPlus(null=True)

    class Meta(Ferias.Meta):
        verbose_name = 'Férias do Cálculo de Progressão'
        verbose_name_plural = 'Férias do Cálculo de Progressão'

    def save(self):
        # Abaixo dava erro pois valores vinham como floats.
        self.total = (
            Decimal(self.valor_venc)
            + Decimal(self.valor_rt or 0)
            + Decimal(self.valor_anuenio or 0)
            + Decimal(self.valor_per or 0)
            + Decimal(self.valor_ins or 0)
            + Decimal(self.valor_iq or 0)
        )
        super(FeriasCalculoProgressao, self).save()


# # # CÁLCULO DE PERICULOSIDADE # # #

# Classe para calcular pagamento de adicional de periculosidade.
class CalculoPericulosidade(Calculo):
    total_per = models.DecimalFieldPlus(null=False, default=0.0)

    class Meta:
        verbose_name = 'Cálculo de Periculosidade'
        verbose_name_plural = 'Cálculos de Periculosidade'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.total_per = 0
        for periodo in self.periodopericulosidade_set.all():
            p = PeriodoPericulosidade.objects.filter(id=periodo.id).annotate(Sum('detalhamentopericulosidade__valor_per'))[0]
            self.total_per += p.detalhamentopericulosidade__valor_per__sum or 0

            p = PeriodoPericulosidade.objects.filter(id=periodo.id).annotate(Sum('feriaspericulosidade__valor_per'))[0]
            self.total_per += p.feriaspericulosidade__valor_per__sum or 0

        self.total = self.total_per
        self.tipo = 3
        super(CalculoPericulosidade, self).save()


# Classe para salvar os períodos com respectivos dados de um cálculo de periculosidade.
class PeriodoPericulosidade(Periodo):
    calculo = models.ForeignKeyPlus(CalculoPericulosidade, verbose_name='Cálculo de Periculosidade')
    # Campos criados para facilitar o preenchimento de formulários pelos usuários. NÃO MUDAR NOME POR CAUSA DE SCRIPT.
    padrao_vencimento_novo = models.CharField(max_length=3, null=True, blank=True, verbose_name='Padrão de Vencimento')

    class Meta(Periodo.Meta):
        verbose_name = 'Período do Cálculo de Periculosidade'
        verbose_name_plural = 'Períodos do Cálculo de Periculosidade'

    def get_ferias(self):
        return self.feriaspericulosidade_set


# Classe para salvar o detalhamento mensal de um determinado período de um pagamento por periculosidade.
class DetalhamentoPericulosidade(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoPericulosidade, verbose_name='Período de Periculosidade', on_delete=models.CASCADE)
    valor_venc = models.DecimalFieldPlus(null=False, verbose_name='Vencimento Recebido')
    valor_per = models.DecimalFieldPlus(null=False, verbose_name='Ad. de Periculosidade a Receber')

    class Meta(Detalhamento.Meta):
        verbose_name = 'Detalhamento Mensal de Periculosidade'
        verbose_name_plural = 'Detalhamentos Mensais de Periculosidade'

    def save(self):
        self.total = self.valor_per
        super(DetalhamentoPericulosidade, self).save()


# Classe para salvar os dados de férias de um cálculo de periculosidade.
class FeriasPericulosidade(Ferias):
    periodo = models.ForeignKeyPlus(PeriodoPericulosidade, verbose_name='Período do Cálculo de Periculosidade')
    valor_venc = models.DecimalFieldPlus(null=False, verbose_name='Vencimento Recebido')
    valor_per = models.DecimalFieldPlus(null=False, verbose_name='Ad. de Periculosidade a Receber')

    class Meta(Ferias.Meta):
        verbose_name = 'Férias do Cálculo de Periculosidade'
        verbose_name_plural = 'Férias do Cálculo de Periculosidade'

    def save(self):
        self.total = self.valor_per
        super(FeriasPericulosidade, self).save()


# # # CÁLCULO DE INSALUBRIDADE # # #

# Classe para calcular pagamento de adicional de insalubridade.
class CalculoInsalubridade(Calculo):
    total_ins = models.DecimalFieldPlus(null=False, default=0.0)

    class Meta:
        verbose_name = 'Cálculo de Insalubridade'
        verbose_name_plural = 'Cálculos de Insalubridade'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.total_ins = 0
        for periodo in self.periodoinsalubridade_set.all():
            p = PeriodoInsalubridade.objects.filter(id=periodo.id).annotate(Sum('detalhamentoinsalubridade__valor_ins'))[0]
            self.total_ins += p.detalhamentoinsalubridade__valor_ins__sum or 0

            p = PeriodoInsalubridade.objects.filter(id=periodo.id).annotate(Sum('feriasinsalubridade__valor_ins'))[0]
            self.total_ins += p.feriasinsalubridade__valor_ins__sum or 0

        self.total = self.total_ins
        self.tipo = 4
        super(CalculoInsalubridade, self).save()

    def get_detalhamento_model(self):
        return DetalhamentoInsalubridade


# Classe para salvar os períodos com respectivos dados de um cálculo de insalubridade.
class PeriodoInsalubridade(Periodo):
    calculo = models.ForeignKeyPlus(CalculoInsalubridade, verbose_name='Cálculo de Insalubridade')
    # Campos criados para facilitar o preenchimento de formulários pelos usuários. NÃO MUDAR NOME POR CAUSA DE SCRIPT.
    padrao_vencimento_novo = models.CharField(max_length=3, null=True, blank=True, verbose_name='Padrão de Vencimento')
    insalubridade = models.PositiveIntegerField('Adicional de Insalubridade', choices=INSALUBRIDADE_CHOICES[1:], null=False)

    class Meta(Periodo.Meta):
        verbose_name = 'Período do Cálculo de Insalubridade'
        verbose_name_plural = 'Períodos do Cálculo de Insalubridade'

    def get_ferias(self):
        return self.feriasinsalubridade_set


# Classe para salvar o detalhamento mensal de um determinado período de um pagamento por insalubridade.
class DetalhamentoInsalubridade(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoInsalubridade, verbose_name='Período de Insalubridade', on_delete=models.CASCADE)
    valor_venc = models.DecimalFieldPlus(null=False, verbose_name='Vencimento Recebido')
    valor_ins = models.DecimalFieldPlus(null=False, verbose_name='Ad. de Insalubridade a Receber')

    class Meta(Detalhamento.Meta):
        verbose_name = 'Detalhamento Mensal de Insalubridade'
        verbose_name_plural = 'Detalhamentos Mensais de Insalubridade'

    def save(self):
        self.total = self.valor_ins
        super(DetalhamentoInsalubridade, self).save()


# Classe para salvar os dados de férias de um cálculo de insalubridade.
class FeriasInsalubridade(Ferias):
    periodo = models.ForeignKeyPlus(PeriodoInsalubridade, verbose_name='Período do Cálculo de Insalubridade')
    valor_venc = models.DecimalFieldPlus(null=False, verbose_name='Vencimento Recebido')
    valor_ins = models.DecimalFieldPlus(null=False, verbose_name='Ad. de Insalubridade a Receber')

    class Meta(Ferias.Meta):
        verbose_name = 'Férias do Cálculo de Insalubridade'
        verbose_name_plural = 'Férias do Cálculo de Insalubridade'

    def save(self):
        self.total = self.valor_ins
        super(FeriasInsalubridade, self).save()


# # # CÁLCULO DE RETRIBUIÇÃO POR TITULAÇÃO # # #

# Classe para calcular pagamento de retribuição por titulação.
class CalculoRT(Calculo):
    total_rt = models.DecimalFieldPlus(null=False, default=0.0)

    class Meta:
        verbose_name = 'Cálculo de RT'
        verbose_name_plural = 'Cálculos de RT'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.total_rt = 0
        for periodo in self.periodort_set.all():
            p = PeriodoRT.objects.filter(id=periodo.id).annotate(Sum('detalhamentort__valor_rt'))[0]
            self.total_rt += p.detalhamentort__valor_rt__sum or 0

            p = PeriodoRT.objects.filter(id=periodo.id).annotate(Sum('feriasrt__valor_rt'))[0]
            self.total_rt += p.feriasrt__valor_rt__sum or 0

        self.total = self.total_rt
        self.tipo = 5
        super(CalculoRT, self).save()

    def get_detalhamento_model(self):
        return DetalhamentoRT


# Classe para salvar os períodos com respectivos dados de um cálculo de retribuição por titulação.
class PeriodoRT(Periodo):
    calculo = models.ForeignKeyPlus(CalculoRT, verbose_name='Cálculo de RT')
    titulacao_passada = models.ForeignKeyPlus(
        Titulacao, null=True, blank=True, related_name='titulacao_passada4%(app_label)s_%(class)s', verbose_name='Titulação Anterior', limit_choices_to=titulacoes_choices
    )
    titulacao_nova = models.ForeignKeyPlus(
        Titulacao, null=False, blank=False, related_name='titulacao_nova4%(app_label)s_%(class)s', verbose_name='Titulação Nova', limit_choices_to=titulacoes_choices
    )

    class Meta(Periodo.Meta):
        verbose_name = 'Período do Cálculo de RT'
        verbose_name_plural = 'Períodos do Cálculo de RT'

    def get_ferias(self):
        return self.feriasrt_set

    def get_detalhamento_model(self):
        return DetalhamentoRT


# Classe para salvar o detalhamento mensal de um determinado período de um pagamento de retribuição por titulação.
class DetalhamentoRT(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoRT, verbose_name='Período do Cálculo de RT', on_delete=models.CASCADE)
    valor_rt = models.DecimalFieldPlus(null=False, verbose_name='RT a Receber')

    class Meta(Detalhamento.Meta):
        verbose_name = 'Detalhamento Mensal de RT'
        verbose_name_plural = 'Detalhamentos Mensais de RT'

    def save(self):
        self.total = self.valor_rt
        super(DetalhamentoRT, self).save()


# Classe para salvar os dados de férias de um cálculo de retribuição por titulação.
class FeriasRT(Ferias):
    periodo = models.ForeignKeyPlus(PeriodoRT, verbose_name='Período do Cálculo de RT')
    valor_rt = models.DecimalFieldPlus(null=False, verbose_name='RT a Receber')

    class Meta(Ferias.Meta):
        verbose_name = 'Férias do Cálculo de RT'
        verbose_name_plural = 'Férias do Cálculo de RT'

    def save(self):
        self.total = self.valor_rt
        super(FeriasRT, self).save()


# # # CÁLCULO DE RSC # # #

# Classe para calcular pagamento de RSC.
class CalculoRSC(Calculo):
    total_rt = models.DecimalFieldPlus(null=False, default=0.0)

    class Meta:
        verbose_name = 'Cálculo de RSC'
        verbose_name_plural = 'Cálculos de RSC'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.total_rt = 0
        for periodo in self.periodorsc_set.all():
            p = PeriodoRSC.objects.filter(id=periodo.id).annotate(Sum('detalhamentorsc__valor_rt'))[0]
            self.total_rt += p.detalhamentorsc__valor_rt__sum or 0

            p = PeriodoRSC.objects.filter(id=periodo.id).annotate(Sum('feriasrsc__valor_rt'))[0]
            self.total_rt += p.feriasrsc__valor_rt__sum or 0

        self.total = self.total_rt
        self.tipo = 6
        super(CalculoRSC, self).save()

    def get_detalhamento_model(self):
        return DetalhamentoRSC


# Classe para salvar os períodos com respectivos dados de um cálculo de RSC.
class PeriodoRSC(Periodo):
    calculo = models.ForeignKeyPlus(CalculoRSC, verbose_name='Cálculo de RSC')
    titulacao_passada = models.ForeignKeyPlus(
        Titulacao, null=True, blank=True, related_name='titulacao_passada4%(app_label)s_%(class)s', verbose_name='Titulação Anterior', limit_choices_to=titulacoes_choices
    )
    titulacao_nova = models.ForeignKeyPlus(
        Titulacao, null=False, blank=False, related_name='titulacao_nova4%(app_label)s_%(class)s', verbose_name='Titulação Nova', limit_choices_to=rsc_choices
    )

    class Meta(Periodo.Meta):
        verbose_name = 'Período do Cálculo de RSC'
        verbose_name_plural = 'Períodos do Cálculo de RSC'

    def get_ferias(self):
        return self.feriasrsc_set

    def get_detalhamento_model(self):
        return DetalhamentoRSC


# Classe para salvar o detalhamento mensal de um determinado período de um pagamento de RSC.
class DetalhamentoRSC(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoRSC, verbose_name='Período do Cálculo de RSC', on_delete=models.CASCADE)
    valor_rt = models.DecimalFieldPlus(null=False, verbose_name='RT a Receber')

    class Meta(Detalhamento.Meta):
        verbose_name = 'Detalhamento Mensal de RSC'
        verbose_name_plural = 'Detalhamentos Mensais de RSC'

    def save(self):
        self.total = self.valor_rt
        super(DetalhamentoRSC, self).save()


# Classe para salvar os dados de férias de um cálculo de RSC.
class FeriasRSC(Ferias):
    periodo = models.ForeignKeyPlus(PeriodoRSC, verbose_name='Período do Cálculo de RSC')
    valor_rt = models.DecimalFieldPlus(null=False, verbose_name='RT a Receber')

    class Meta(Ferias.Meta):
        verbose_name = 'Férias do Cálculo de RSC'
        verbose_name_plural = 'Férias do Cálculo de RSC'

    def save(self):
        self.total = self.valor_rt
        super(FeriasRSC, self).save()


# # # CÁLCULO DE INCENTIVO À QUALIFICAÇÃO # # #

# Classe para calcular pagamento de incentivo à qualificacao.
class CalculoIQ(Calculo):
    total_iq = models.DecimalFieldPlus(null=False, default=0.0)

    class Meta:
        verbose_name = 'Cálculo de IQ'
        verbose_name_plural = 'Cálculos de IQ'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.total_iq = 0
        for periodo in self.periodoiq_set.all():
            p = PeriodoIQ.objects.filter(id=periodo.id).annotate(Sum('detalhamentoiq__valor_iq'))[0]
            self.total_iq += p.detalhamentoiq__valor_iq__sum or 0

            p = PeriodoIQ.objects.filter(id=periodo.id).annotate(Sum('feriasiq__valor_iq'))[0]
            self.total_iq += p.feriasiq__valor_iq__sum or 0

        self.total = self.total_iq
        self.tipo = 7
        super(CalculoIQ, self).save()

    def get_detalhamento_model(self):
        return DetalhamentoIQ


# Classe para salvar os períodos com respectivos dados de um cálculo de incentivo à qualificacao.
class PeriodoIQ(Periodo):
    calculo = models.ForeignKeyPlus(CalculoIQ, verbose_name='Cálculo de IQ')
    padrao_vencimento_novo = models.CharField(max_length=3, null=False, verbose_name='Padrão de Vencimento')
    iq_passado = models.PositiveIntegerField('Incentivo à Qualificação Passado', choices=IQ_CHOICES, null=True, blank=True, default=0)
    iq_novo = models.PositiveIntegerField('Incentivo à Qualificação Novo', choices=IQ_CHOICES, null=False, default=0)

    class Meta(Periodo.Meta):
        verbose_name = 'Período do Cálculo de IQ'
        verbose_name_plural = 'Períodos do Cálculo de IQ'

    def get_ferias(self):
        return self.feriasiq_set


# Classe para salvar o detalhamento mensal de um determinado período de um pagamento de incentivo à qualificacao.
class DetalhamentoIQ(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoIQ, verbose_name='Período do Cálculo de IQ', on_delete=models.CASCADE)
    valor_iq = models.DecimalFieldPlus(null=False, verbose_name='IQ a Receber')

    class Meta(Detalhamento.Meta):
        verbose_name = 'Detalhamento Mensal de IQ'
        verbose_name_plural = 'Detalhamentos Mensais de IQ'

    def save(self):
        self.total = self.valor_iq
        super(DetalhamentoIQ, self).save()


# Classe para salvar os dados de férias de um cálculo de incentivo à qualificacao.
class FeriasIQ(Ferias):
    periodo = models.ForeignKeyPlus(PeriodoIQ, verbose_name='Período do Cálculo de IQ')
    valor_iq = models.DecimalFieldPlus(null=False, verbose_name='IQ a Receber')

    class Meta(Ferias.Meta):
        verbose_name = 'Férias do Cálculo de IQ'
        verbose_name_plural = 'Férias do Cálculo de IQ'

    def save(self):
        self.total = self.valor_iq
        super(FeriasIQ, self).save()


# # # CÁLCULO DE MUDANÇA DE REGIME # # #

# IFMA/Tássio - Classe para calcular pagamento devido a mudança de regime de um servidor.
class CalculoMudancaRegime(Calculo):
    total_venc = models.DecimalFieldPlus(null=False, default=0.0)
    total_rt = models.DecimalFieldPlus(null=False, default=0.0)
    total_anuenio = models.DecimalFieldPlus(null=False, default=0.0)
    total_per = models.DecimalFieldPlus(null=False, default=0.0)
    total_ins = models.DecimalFieldPlus(null=False, default=0.0)
    total_iq = models.DecimalFieldPlus(null=False, default=0.0)

    class Meta:
        verbose_name = 'Cálculo de Mudança de Regime'
        verbose_name_plural = 'Cálculos de Mudança de Regime'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.total_venc, self.total_rt, self.total_anuenio = 0, 0, 0
        self.total_per, self.total_ins, self.total_iq = 0, 0, 0
        for periodo in self.periodomudancaregime_set.all():
            p = PeriodoMudancaRegime.objects.filter(id=periodo.id).annotate(
                Sum('detalhamentomudancaregime__valor_venc'),
                Sum('detalhamentomudancaregime__valor_rt'),
                Sum('detalhamentomudancaregime__valor_anuenio'),
                Sum('detalhamentomudancaregime__valor_per'),
                Sum('detalhamentomudancaregime__valor_ins'),
                Sum('detalhamentomudancaregime__valor_iq'),
            )[0]
            self.total_venc += p.detalhamentomudancaregime__valor_venc__sum or 0
            self.total_rt += p.detalhamentomudancaregime__valor_rt__sum or 0
            self.total_anuenio += p.detalhamentomudancaregime__valor_anuenio__sum or 0
            self.total_per += p.detalhamentomudancaregime__valor_per__sum or 0
            self.total_ins += p.detalhamentomudancaregime__valor_ins__sum or 0
            self.total_iq += p.detalhamentomudancaregime__valor_iq__sum or 0

            p = PeriodoMudancaRegime.objects.filter(id=periodo.id).annotate(
                Sum('feriasmudancaregime__valor_venc'),
                Sum('feriasmudancaregime__valor_rt'),
                Sum('feriasmudancaregime__valor_anuenio'),
                Sum('feriasmudancaregime__valor_per'),
                Sum('feriasmudancaregime__valor_ins'),
                Sum('feriasmudancaregime__valor_iq'),
            )[0]
            self.total_venc += p.feriasmudancaregime__valor_venc__sum or 0
            self.total_rt += p.feriasmudancaregime__valor_rt__sum or 0
            self.total_anuenio += p.feriasmudancaregime__valor_anuenio__sum or 0
            self.total_per += p.feriasmudancaregime__valor_per__sum or 0
            self.total_ins += p.feriasmudancaregime__valor_ins__sum or 0
            self.total_iq += p.feriasmudancaregime__valor_iq__sum or 0

        self.total = self.total_venc + self.total_rt + self.total_anuenio + self.total_per + self.total_ins + self.total_iq
        self.tipo = 8
        super(CalculoMudancaRegime, self).save()

    def get_detalhamento_model(self):
        return DetalhamentoMudancaRegime


# IFMA/Tássio - Classe para salvar os períodos com respectivos dados de um cálculo de mudança de regime.
class PeriodoMudancaRegime(Periodo):
    calculo = models.ForeignKeyPlus(CalculoMudancaRegime, verbose_name='Cálculo de Mudança de Regime')
    jornada_passada = models.ForeignKeyPlus(JornadaTrabalho, null=False, verbose_name='Jornada de Trabalho Anterior', related_name="jornada_passada4%(app_label)s_%(class)s")
    # Campo criado para facilitar o preenchimento de formulários pelos usuários. NÃO MUDAR NOME POR CAUSA DE SCRIPT.
    padrao_vencimento_novo = models.CharField(max_length=3, null=True, blank=True, verbose_name='Padrão de Vencimento')
    titulacao_nova = models.ForeignKeyPlus(
        Titulacao, null=True, blank=True, related_name='titulacao_nova4%(app_label)s_%(class)s', verbose_name='Titulação', limit_choices_to=all_titulacoes_choices
    )
    anuenio = models.DecimalFieldPlus('Anuênio a Receber (%)', default=Decimal("0.0"), null=True, blank=True)
    periculosidade = models.BooleanField('Adicional de Periculosidade (10%)', default=False)
    insalubridade = models.PositiveIntegerField('Adicional de Insalubridade', choices=INSALUBRIDADE_CHOICES, null=True, blank=True, default=0)
    iq = models.PositiveIntegerField('Incentivo à Qualificação', choices=IQ_CHOICES, null=True, blank=True, default=0)

    class Meta(Periodo.Meta):
        verbose_name = 'Período do Cálculo de Mudança de Regime'
        verbose_name_plural = 'Períodos do Cálculo de Mudança de Regime'

    def get_ferias(self):
        return self.feriasmudancaregime_set


# IFMA/Tássio - Classe para salvar o detalhamento mensal de um determinado período de um pagamento por mudança d regime.
class DetalhamentoMudancaRegime(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoMudancaRegime, verbose_name='Período do Cálculo de Mudança de Regime')
    valor_venc = models.DecimalFieldPlus(null=False)
    valor_rt = models.DecimalFieldPlus(null=True)
    valor_anuenio = models.DecimalFieldPlus(null=True)
    valor_per = models.DecimalFieldPlus(null=True)
    valor_ins = models.DecimalFieldPlus(null=True)
    valor_iq = models.DecimalFieldPlus(null=True)

    class Meta(Detalhamento.Meta):
        verbose_name = 'Detalhamento Mensal de Mudança de Regime'
        verbose_name_plural = 'Detalhamentos Mensais de Mudança de Regime'

    def save(self):
        # Abaixo dava erro pois valores vinham como floats.
        self.total = (
            Decimal(self.valor_venc)
            + Decimal(self.valor_rt or 0)
            + Decimal(self.valor_anuenio or 0)
            + Decimal(self.valor_per or 0)
            + Decimal(self.valor_ins or 0)
            + Decimal(self.valor_iq or 0)
        )
        super(DetalhamentoMudancaRegime, self).save()


# IFMA/Tássio - Classe para salvar os dados de férias de um cálculo de mudança de regime.
class FeriasMudancaRegime(Ferias):
    periodo = models.ForeignKeyPlus(PeriodoMudancaRegime, verbose_name='Período do Cálculo de Mudança de Regime')
    valor_venc = models.DecimalFieldPlus(null=False)
    valor_rt = models.DecimalFieldPlus(null=True)
    valor_anuenio = models.DecimalFieldPlus(null=True)
    valor_per = models.DecimalFieldPlus(null=True)
    valor_ins = models.DecimalFieldPlus(null=True)
    valor_iq = models.DecimalFieldPlus(null=True)

    class Meta(Ferias.Meta):
        verbose_name = 'Férias do Cálculo de Mudança de Regime'
        verbose_name_plural = 'Férias do Cálculo de Mudança de Regime'

    def save(self):
        # Abaixo dava erro pois valores vinham como floats.
        self.total = (
            Decimal(self.valor_venc)
            + Decimal(self.valor_rt or 0)
            + Decimal(self.valor_anuenio or 0)
            + Decimal(self.valor_per or 0)
            + Decimal(self.valor_ins or 0)
            + Decimal(self.valor_iq or 0)
        )
        super(FeriasMudancaRegime, self).save()


# # # CÁLCULO DE AUXÍLIO TRANSPORTE # # #

# Classe para calcular pagamento de auxílio transporte.
class CalculoTransporte(Calculo):
    total_aux = models.DecimalFieldPlus(null=False, default=0.0)

    class Meta:
        verbose_name = 'Cálculo de Auxílio Transporte'
        verbose_name_plural = 'Cálculos de Auxílio Transporte'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.total_aux = 0
        for periodo in self.periodotransporte_set.all():
            p = PeriodoTransporte.objects.filter(id=periodo.id).annotate(Sum('detalhamentotransporte__valor_aux'))[0]
            self.total_aux += p.detalhamentotransporte__valor_aux__sum or 0

        self.total = self.total_aux
        self.tipo = 9
        super(CalculoTransporte, self).save()

    def get_detalhamento_model(self):
        return DetalhamentoTransporte


# Classe para salvar os períodos com respectivos dados de um cálculo de auxílio transporte.
class PeriodoTransporte(Periodo):
    calculo = models.ForeignKeyPlus(CalculoTransporte, verbose_name='Cálculo de Auxílio Transporte')
    # Campos criados para facilitar o preenchimento de formulários pelos usuários. NÃO MUDAR NOME POR CAUSA DE SCRIPT.
    padrao_vencimento_novo = models.CharField(max_length=3, null=True, blank=True, verbose_name='Padrão de Vencimento')
    quant_passagens = models.PositiveIntegerField('Quantidade Diária de Passagens', null=False, blank=False)
    valor_passagem = models.DecimalFieldPlus('Valor Unitário da Passagem (R$)', default=Decimal("0.0"), null=False, blank=False)
    dias_uteis_mes_incompleto = models.PositiveIntegerField(
        'Dias Úteis de Mês Incompleto',
        default=0,
        null=False,
        blank=False,
        help_text="Quantidade de dias úteis a ser considerada no " "cálculo do valor do auxílio para um mês " "incompleto dentro do período informado.",
    )

    class Meta(Periodo.Meta):
        verbose_name = 'Período do Cálculo de Auxílio Transporte'
        verbose_name_plural = 'Períodos do Cálculo de Auxílio Transporte'

    def get_detalhamento_model(self):
        return DetalhamentoTransporte


# Classe para salvar o detalhamento mensal de um determinado período de um pagamento de auxílio transporte.
class DetalhamentoTransporte(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoTransporte, verbose_name='Período de Auxílio Transporte')
    valor_aux = models.DecimalFieldPlus(null=False, verbose_name='Auxílio Transporte a Receber')

    class Meta(Detalhamento.Meta):
        verbose_name = 'Detalhamento Mensal de Auxílio Transporte'
        verbose_name_plural = 'Detalhamentos Mensais de Auxílio Transporte'

    def save(self):
        self.total = self.valor_aux
        super(DetalhamentoTransporte, self).save()


# # # CÁLCULO DE ABONO DE PERMANÊNCIA # # #

# Classe para calcular pagamento de abono de permanência.
class CalculoPermanencia(Calculo):
    total_abono = models.DecimalFieldPlus(null=False, default=0.0)

    class Meta:
        verbose_name = 'Cálculo de Abono de Permanência'
        verbose_name_plural = 'Cálculos de Abono de Permanência'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.total_abono = 0
        for periodo in self.periodopermanencia_set.all():
            p = PeriodoPermanencia.objects.filter(id=periodo.id).annotate(Sum('detalhamentopermanencia__valor_abono'))[0]
            self.total_abono += p.detalhamentopermanencia__valor_abono__sum or 0

        self.total = self.total_abono
        self.tipo = 10
        super(CalculoPermanencia, self).save()

    def get_detalhamento_model(self):
        return DetalhamentoPermanencia


# Classe para salvar os períodos com respectivos dados de um cálculo de abono de permanência.
class PeriodoPermanencia(ModelPlus):
    calculo = models.ForeignKeyPlus(CalculoPermanencia, verbose_name='Cálculo de Abono de Permanência')
    data_inicio = models.DateFieldPlus('Data Inicial', null=False)
    data_fim = models.DateFieldPlus('Data Final', null=False)
    valor_mensal_abono = models.DecimalFieldPlus('Valor Mensal do Abono de Permanência (R$)', default=Decimal("0.0"), null=False, blank=False)

    class Meta:
        verbose_name = 'Período do Cálculo de Abono de Permanência'
        verbose_name_plural = 'Períodos do Cálculo de Abono de Permanência'
        ordering = ['data_inicio']

    def __unicode__(self):
        return 'Período ({} - {})'.format(self.data_inicio.strftime('%d/%m/%Y'), self.data_fim.strftime('%d/%m/%Y'))

    def __str__(self):
        return 'Período ({} - {})'.format(self.data_inicio.strftime('%d/%m/%Y'), self.data_fim.strftime('%d/%m/%Y'))

    def get_detalhamento_model(self):
        return DetalhamentoPermanencia


# Classe para salvar o detalhamento mensal de um determinado período de um pagamento de abono de permanência.
class DetalhamentoPermanencia(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoPermanencia, verbose_name='Período de Abono de Permanência')
    valor_abono = models.DecimalFieldPlus(null=False, verbose_name='Abono de Permanência a Receber')

    class Meta(Detalhamento.Meta):
        verbose_name = 'Detalhamento Mensal de Abono de Permanência'
        verbose_name_plural = 'Detalhamentos Mensais de Abono de Permanência'

    def save(self):
        self.total = self.valor_abono
        super(DetalhamentoPermanencia, self).save()


# # # CLASSES DE CÁLCULOS DE DESIGNAÇÃO/DISPENSA DE FG/FUC E NOMEAÇÃO/EXONERAÇÃO DE CD # # #


class ValoresFuncaoDetalhados(ModelPlus):
    valorporfuncao = models.OneToOneFieldPlus(ValorPorFuncao, verbose_name="Função Gratificada")
    valor_venc = models.DecimalFieldPlus(null=False, verbose_name='Vencimento (R$)')
    valor_gadf = models.DecimalFieldPlus(null=False, verbose_name='Gratificação de Atividade pelo Desempenho de Função (R$)')
    valor_age = models.DecimalFieldPlus(null=False, verbose_name='Adicional de Gestão Educacional (R$)')

    class Meta:
        verbose_name = 'Valores de Função Por Rubrica'
        verbose_name_plural = 'Valores de Funções Por Rubrica'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, str(self.valorporfuncao))

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, str(self.valorporfuncao))

    def clean(self):
        if self.valorporfuncao.valor != self.valor_venc + self.valor_gadf + self.valor_age:
            raise ValidationError('O somátória das rubricas difere do valor total da função de R${}.'.format(self.valorporfuncao.valor))


# IFMA/Tássio - Classe base para calcular valor a receber ou a devolver por designação/dispensa de FG/FUC ou
# nomeação/exoneração de CD.
class CalculoFGsCDs(Calculo):
    total_grat = models.DecimalFieldPlus(null=False, default=0.0)

    def get_detalhamento_model(self):
        return DetalhamentoFGsCDs


class CalculoCD(CalculoFGsCDs):
    def save(self):
        self.total_grat = 0
        for periodo in self.periodofgscds_set.all():
            p = PeriodoFGsCDs.objects.filter(id=periodo.id).annotate(Sum('detalhamentofgscds__valor_grat'))[0]
            self.total_grat += p.detalhamentofgscds__valor_grat__sum or 0

            p = PeriodoFGsCDs.objects.filter(id=periodo.id).annotate(Sum('feriasfgscds__valor_grat'))[0]
            self.total_grat += p.feriasfgscds__valor_grat__sum or 0

        self.total = self.total_grat
        super(CalculoCD, self).save()


class CalculoNomeacaoCD(CalculoCD):
    class Meta:
        verbose_name = 'Cálculo de Nomeação de CD'
        verbose_name_plural = 'Cálculos de Nomeação de CD'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.tipo = 11
        super(CalculoNomeacaoCD, self).save()


class CalculoExoneracaoCD(CalculoCD):
    class Meta:
        verbose_name = 'Cálculo de Exoneração de CD'
        verbose_name_plural = 'Cálculos de Exoneração de CD'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.tipo = 12
        super(CalculoExoneracaoCD, self).save()


class CalculoFG(CalculoFGsCDs):
    total_venc = models.DecimalFieldPlus(null=False, default=0.0)
    total_gadf = models.DecimalFieldPlus(null=False, default=0.0)
    total_age = models.DecimalFieldPlus(null=False, default=0.0)

    def save(self):
        self.total_grat, self.total_venc, self.total_gadf, self.total_age = 0, 0, 0, 0

        for periodo in self.periodofgscds_set.all():
            p = PeriodoFGsCDs.objects.filter(id=periodo.id).annotate(
                Sum('detalhamentofgscds__valor_grat'), Sum('detalhamentofgscds__valor_venc'), Sum('detalhamentofgscds__valor_gadf'), Sum('detalhamentofgscds__valor_age')
            )[0]
            self.total_grat += p.detalhamentofgscds__valor_grat__sum or 0
            self.total_venc += p.detalhamentofgscds__valor_venc__sum or 0
            self.total_gadf += p.detalhamentofgscds__valor_gadf__sum or 0
            self.total_age += p.detalhamentofgscds__valor_age__sum or 0

            p = PeriodoFGsCDs.objects.filter(id=periodo.id).annotate(
                Sum('feriasfgscds__valor_grat'), Sum('feriasfgscds__valor_venc'), Sum('feriasfgscds__valor_gadf'), Sum('feriasfgscds__valor_age')
            )[0]
            self.total_grat += p.feriasfgscds__valor_grat__sum or 0
            self.total_venc += p.feriasfgscds__valor_venc__sum or 0
            self.total_gadf += p.feriasfgscds__valor_gadf__sum or 0
            self.total_age += p.feriasfgscds__valor_age__sum or 0

        self.total = self.total_grat + self.total_venc + self.total_gadf + self.total_age
        super(CalculoFG, self).save()


class CalculoDesignacaoFG(CalculoFG):
    class Meta:
        verbose_name = 'Cálculo de Designação de FG/FUC'
        verbose_name_plural = 'Cálculos de Designação de FG/FUC'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.tipo = 13
        super(CalculoDesignacaoFG, self).save()


class CalculoDispensaFG(CalculoFG):
    class Meta:
        verbose_name = 'Cálculo de Dispensa de FG/FUC'
        verbose_name_plural = 'Cálculos de Dispensa de FG/FUC'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def save(self):
        self.tipo = 14
        super(CalculoDispensaFG, self).save()


# IFMA/Tássio - Classe para salvar os períodos com respectivos dados de cálculos de FG/CD.
class PeriodoFGsCDs(ModelPlus):
    calculo = models.ForeignKeyPlus(CalculoFGsCDs, verbose_name='Cálculo')
    data_inicio = models.DateFieldPlus('Data Inicial', null=False)
    data_fim = models.DateFieldPlus('Data Final', null=False)
    funcao = models.ForeignKeyPlus(FuncaoCodigo, verbose_name='Função', null=False)
    meses_devidos_grat_nat = models.PositiveIntegerField('Meses a Receber de Gratificação Natalina', choices=MESES_CHOICES, null=True, blank=False, default=0)
    meses_indevidos_grat_nat = models.PositiveIntegerField('Meses a Devolver de Gratificação Natalina', choices=MESES_CHOICES, null=True, blank=False, default=0)
    recebeu_grat_nat = models.BooleanField('Já recebeu a gratificação natalina?', default=False)  # Apagar esse campo após o estabelecimento do campo meses_indevidos_grat_nat

    class Meta:
        verbose_name = 'Período do Cálculo'
        verbose_name_plural = 'Períodos do Cálculo'

    def __unicode__(self):
        return 'Período ({} - {})'.format(self.data_inicio.strftime('%d/%m/%Y'), self.data_fim.strftime('%d/%m/%Y'))

    def __str__(self):
        return 'Período ({} - {})'.format(self.data_inicio.strftime('%d/%m/%Y'), self.data_fim.strftime('%d/%m/%Y'))

    def get_detalhamento_model(self):
        return self.calculo.get_detalhamento_model()

    def get_ferias(self):
        return self.feriasfgscds_set


# IFMA/Tássio - Classe para salvar o detalhamento mensal de um determinado período de um cálculo de FG/CD.
class DetalhamentoFGsCDs(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoFGsCDs, verbose_name='Período do Cálculo')
    valor_grat = models.DecimalFieldPlus(null=True)
    valor_venc = models.DecimalFieldPlus(null=True)
    valor_gadf = models.DecimalFieldPlus(null=True)
    valor_age = models.DecimalFieldPlus(null=True)

    def save(self):
        # Abaixo dava erro pois valores vinham como floats.
        self.total = Decimal(self.valor_grat) + Decimal(self.valor_venc or 0) + Decimal(self.valor_gadf or 0) + Decimal(self.valor_age or 0)
        super(DetalhamentoFGsCDs, self).save()


# IFMA/Tássio - Classe para salvar os dados de férias de um cálculo de FG/CD.
class FeriasFGsCDs(Ferias):
    periodo = models.ForeignKeyPlus(PeriodoFGsCDs, verbose_name='Período do Cálculo')
    valor_grat = models.DecimalFieldPlus(null=True)
    valor_venc = models.DecimalFieldPlus(null=True)
    valor_gadf = models.DecimalFieldPlus(null=True)
    valor_age = models.DecimalFieldPlus(null=True)

    class Meta(Ferias.Meta):
        verbose_name = 'Férias do Cálculo'
        verbose_name_plural = 'Férias do Cálculo'

    def save(self):
        # Abaixo dava erro pois valores vinham como floats.
        self.total = Decimal(self.valor_grat) + Decimal(self.valor_venc or 0) + Decimal(self.valor_gadf or 0) + Decimal(self.valor_age or 0)
        super(FeriasFGsCDs, self).save()


# # # CÁLCULO DE ACERTO DE TÉRMINO DE CONTRATO TEMPORÁRIO # # #

# IFMA/Tássio - Valor de auxílio-alimentação por período.
class ValorAlimentacao(ModelPlus):
    valor = models.DecimalField(max_digits=12, decimal_places=2, null=False)
    data_inicio = models.DateFieldPlus(verbose_name='Data de início do valor', null=True, blank=True)
    data_fim = models.DateFieldPlus(verbose_name='Data de fim do valor', null=True, blank=True)

    def __unicode__(self):
        return 'Auxílio-Alimentação ({} - {}) - R${}'.format(
            self.data_inicio and self.data_inicio.strftime('%d/%m/%Y') or 'Anteriormente', self.data_fim and self.data_fim.strftime('%d/%m/%Y') or 'Atualmente', self.valor
        )

    def __str__(self):
        return 'Auxílio-Alimentação ({} - {}) - R${}'.format(
            self.data_inicio and self.data_inicio.strftime('%d/%m/%Y') or 'Anteriormente', self.data_fim and self.data_fim.strftime('%d/%m/%Y') or 'Atualmente', self.valor
        )

    class Meta:
        ordering = ['-data_fim']
        verbose_name = 'Valor de Auxílio-Alimentação'
        verbose_name_plural = 'Valores de Auxílio-Alimentação'

    def clean(self):
        if not self.data_inicio and not self.data_fim:
            raise ValidationError('Informe pelo menos uma das duas datas solicitadas para o valor.')

        if self.data_inicio:
            qs = ValorAlimentacao.objects.filter(data_inicio__lte=self.data_inicio, data_fim__gte=self.data_inicio)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError('A data de início informada está dentro de outro período já registrado, ou no ' 'limite.')
            qs = ValorAlimentacao.objects.filter(data_inicio__lte=self.data_inicio, data_fim__isnull=True)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError(
                    'A data de início informada está igual ou após a data de início de outro período'
                    ' já registrado que não tem data de término. Inclua a data de término do outro '
                    'período antes de criar um novo.'
                )

        if self.data_fim:
            qs = ValorAlimentacao.objects.filter(data_inicio__lte=self.data_fim, data_fim__gte=self.data_fim)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError('A data de fim informada está dentro de outro período já registrado, ou no ' 'limite,')

            qs = ValorAlimentacao.objects.filter(data_inicio__isnull=True, data_fim__gte=self.data_fim)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError(
                    'A data de fim informada está igual ou antes da data de fim de outro período já '
                    'registrado que não tem data de início. Inclua a data de início '
                    'do outro período antes de criar um novo.'
                )

        if self.data_inicio and self.data_fim:
            qs = ValorAlimentacao.objects.filter(data_inicio__gte=self.data_inicio, data_fim__lte=self.data_fim)
            if self.id:
                qs = qs.exclude(id=self.id)
            if qs.exists():
                raise ValidationError('O período informado engloba outros períodos já cadastrados. Não é possível ' 'cadastrar um período nesta condição.')


# Classe para calcular pagamento de acerto de término de contrato temporário.
class CalculoTerminoContrato(Calculo):
    contrato = models.CharField(verbose_name='Contrato', max_length=11, null=False, blank=False)
    # Rendimentos
    total_contr = models.DecimalFieldPlus('Contrato', null=False, default=0.0)
    total_transp = models.DecimalFieldPlus('Auxílio Transporte', null=False, default=0.0)
    total_ins = models.DecimalFieldPlus('Adicional de Insalubridade', null=False, default=0.0)
    total_per = models.DecimalFieldPlus('Adicional de Periculosidade', null=False, default=0.0)
    total_iden = models.DecimalFieldPlus('Idenização de Férias', null=False, default=0.0)
    total_ferias = models.DecimalFieldPlus('Férias', null=False, default=0.0)
    total_grat_nat = models.DecimalFieldPlus('Gratif. Natalina Proporcional', null=False, default=0.0)
    # Descontos
    total_alim = models.DecimalFieldPlus('Auxílio Alimentação', null=False, default=0.0)
    total_pss_grat_nat = models.DecimalFieldPlus('PSS da Gratif. Natalina', null=False, default=0.0)
    total_adiantamento_grat_nat = models.DecimalFieldPlus(
        'Adiantamento da Gratificação Natalina', null=False, default=Decimal('0'), help_text='Se recebeu esse adiantamento, informe o valor.'
    )
    total_irpf_grat_nat = models.DecimalFieldPlus(
        'IRPF da Gratificação Natalina',
        null=False,
        default=Decimal('0'),
        help_text="<a href='http://www26.receita.fazenda.gov.br/irpfsimulaliq"
        "/private/pages/simuladoraliquota.jsf'>"
        "Link para calculadora de Simulação de Alíquota Efetiva"
        "</a>",
    )
    # Parâmetros
    meses_devidos_ferias = models.PositiveIntegerField('Quantidade de meses a considerar no cálculo de Idenização de ' 'Férias', choices=MESES_CHOICES, default=0)
    meses_devidos_grat_nat = models.PositiveIntegerField('Quantidade de meses a considerar no cálculo de Gratificação ' 'Natalina', choices=MESES_CHOICES, default=0)
    pss_grat_nat = models.PositiveIntegerField('PSS a Descontar (%)', choices=PSS_CHOICES, default=0, help_text='Percentual do PSS a descontar sobre a Gratificação Natalina.')

    class Meta:
        verbose_name = 'Cálculo de Acerto de Término de Contrato Temporário'
        verbose_name_plural = 'Cálculos de Acerto de Término de Contrato Temporário'

    def __unicode__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    def __str__(self):
        return '{} de {}'.format(self._meta.verbose_name, self.servidor)

    """
    @staticmethod
    def get_periodo_model():
        return PeriodoTerminoContrato

    @staticmethod
    def get_detalhamento_model():
        return DetalhamentoTerminoContrato

    @staticmethod
    def get_detalhamento_alim_model():
        return DetalhamentoAlimentacaoTerminoContrato
    """

    def save(self):
        self.total_contr, self.total_per, self.total_ins, self.total_transp = 0, 0, 0, 0
        self.total_alim = 0
        # Mensais
        for periodo in self.get_periodo_model().objects.filter(calculo=self):
            p = (
                self.get_periodo_model()
                .objects.filter(id=periodo.id)
                .annotate(
                    Sum('detalhamentoterminocontrato__valor_contr'),
                    Sum('detalhamentoterminocontrato__valor_per'),
                    Sum('detalhamentoterminocontrato__valor_ins'),
                    Sum('detalhamentoterminocontrato__valor_transp'),
                )[0]
            )
            self.total_contr += p.detalhamentoterminocontrato__valor_contr__sum or 0
            self.total_per += p.detalhamentoterminocontrato__valor_per__sum or 0
            self.total_ins += p.detalhamentoterminocontrato__valor_ins__sum or 0
            self.total_transp += p.detalhamentoterminocontrato__valor_transp__sum or 0

            p = self.get_periodo_model().objects.filter(id=periodo.id).annotate(Sum('detalhamentoalimentacaoterminocontrato__valor_alim'))[0]
            self.total_alim += p.detalhamentoalimentacaoterminocontrato__valor_alim__sum or 0

        # Rendimentos
        valor_contr_mensal = 0
        ultimo_det = self.get_detalhamento_model().objects.filter(periodo__calculo=self).order_by("-data_fim").first()
        if ultimo_det:
            if (1, calendar.monthrange(ultimo_det.data_fim.year, ultimo_det.data_fim.month)[1]) == (ultimo_det.data_inicio.day, ultimo_det.data_fim.day):
                valor_contr_mensal = ultimo_det.valor_contr
            else:
                valor_contr_mensal = ultimo_det.valor_contr / ultimo_det.quant_dias * 30

        self.total_iden = valor_contr_mensal * self.meses_devidos_ferias / 12
        self.total_iden = Decimal(round(self.total_iden, 2))
        self.total_ferias = self.total_iden / 3
        self.total_ferias = Decimal(round(self.total_ferias, 2))
        self.total_grat_nat = valor_contr_mensal * self.meses_devidos_grat_nat / 12
        self.total_grat_nat = Decimal(round(self.total_grat_nat, 2))

        # Descontos
        self.total_pss_grat_nat = self.total_grat_nat * self.pss_grat_nat / 100
        self.total_pss_grat_nat = Decimal(round(self.total_pss_grat_nat, 2))

        # Totalização
        self.total = self.total_contr + self.total_per + self.total_ins + self.total_transp + self.total_iden + self.total_ferias + self.total_grat_nat
        self.total = self.total - self.total_alim - self.total_pss_grat_nat - self.total_adiantamento_grat_nat - self.total_irpf_grat_nat

        super(CalculoTerminoContrato, self).save()

    def get_periodo_model(self):
        return PeriodoTerminoContrato

    def get_detalhamento_model(self):
        return DetalhamentoTerminoContrato

    def get_detalhamento_alim_model(self):
        return DetalhamentoAlimentacaoTerminoContrato


class CalculoTerminoContratoProfSubs(CalculoTerminoContrato):
    class Meta:
        verbose_name = 'Cálculo de Acerto de Término de Contrato Temporário - Professor Substituto'
        verbose_name_plural = 'Cálculos de Acerto de Término de Contrato Temporário - Professor Substituto'

    def save(self):
        self.tipo = 15
        super(CalculoTerminoContratoProfSubs, self).save()


class CalculoTerminoContratoInterpLibras(CalculoTerminoContrato):
    class Meta:
        verbose_name = 'Cálculo de Acerto de Término de Contrato Temporário - Intérprete de Libras'
        verbose_name_plural = 'Cálculos de Acerto de Término de Contrato Temporário - Intérprete de Libras'

    def save(self):
        self.tipo = 16
        super(CalculoTerminoContratoInterpLibras, self).save()


# Classe para salvar os períodos com respectivos dados de um cálculo de acerto de término de contrato temporário.
class PeriodoTerminoContrato(Periodo):
    calculo = models.ForeignKeyPlus(CalculoTerminoContrato, verbose_name='Cálculo de Término de Contrato Temporário')
    titulacao = models.ForeignKeyPlus(
        Titulacao, verbose_name='Titulação', null=True, blank=True, related_name='titulacao4periodocalculoterminocontrato', limit_choices_to=all_titulacoes_choices
    )
    iq = models.PositiveIntegerField('Incentivo à Qualificação', choices=IQ_CHOICES, null=True, blank=True, default=0)
    periculosidade = models.BooleanField('Adicional de Periculosidade (10%)', default=False)
    insalubridade = models.PositiveIntegerField('Adicional de Insalubridade', choices=INSALUBRIDADE_CHOICES, null=True, blank=True, default=0)
    dias_uteis = models.PositiveIntegerField(
        'Dias Úteis de Mês Incompleto',
        default=0,
        help_text='Quantidade de dias úteis a ser considerada no cálculo dos ' 'valores de Auxílio Alimentação e Auxílio Transporte, no ' 'caso de mês incompleto.',
    )
    transporte = models.DecimalFieldPlus('Auxílio Transporte (R$)', default=Decimal("0.0"), help_text='Valor mensal do Auxílio Transporte recebido pelo servidor.')
    data_inicio_desc_alim = models.DateFieldPlus('Data Inicial do Desconto de Auxílio Alimentação', blank=True, null=True)
    data_fim_desc_alim = models.DateFieldPlus('Data Final do Desconto de Auxílio Alimentação', blank=True, null=True)

    class Meta(Periodo.Meta):
        verbose_name = 'Período do Cálculo'
        verbose_name_plural = 'Períodos do Cálculo'

    def get_detalhamento_model(self):
        return self.calculo.get_detalhamento_model()

    def get_detalhamento_alimentacao_model(self):
        return DetalhamentoAlimentacaoTerminoContrato

    def clean(self):
        if self.data_inicio_desc_alim and not self.data_fim_desc_alim or not self.data_inicio_desc_alim and self.data_fim_desc_alim:
            raise ValidationError({"data_inicio_desc_alim": 'Informe ambas as data para o Desconto de Auxílio ' 'Alimentação ou nenhuma delas.'})


# IFMA/Tássio - Classe para salvar o detalhamento mensal de um determinado período de um cálculo de a. de t. de c.
class DetalhamentoTerminoContrato(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoTerminoContrato, verbose_name='Período do Cálculo')
    valor_contr = models.DecimalFieldPlus(default=0.0)
    valor_per = models.DecimalFieldPlus(null=True, default=0.0)
    valor_ins = models.DecimalFieldPlus(null=True, default=0.0)
    quant_dias_uteis = models.IntegerField()
    valor_transp = models.DecimalFieldPlus(null=True, default=0.0)

    def save(self):
        # Abaixo dava erro pois valores vinham como floats.
        self.total = Decimal(self.valor_contr or 0) + Decimal(self.valor_per or 0) + Decimal(self.valor_ins or 0) + Decimal(self.valor_transp or 0)
        super(DetalhamentoTerminoContrato, self).save()


# IFMA/Tássio - Classe para salvar o detalhamento mensal de um determinado período de um cálculo de a. de t. de c.
class DetalhamentoAlimentacaoTerminoContrato(Detalhamento):
    periodo = models.ForeignKeyPlus(PeriodoTerminoContrato, verbose_name='Período do Cálculo')
    valor_alim = models.DecimalFieldPlus(default=0.0)

    def save(self):
        # Abaixo dava erro pois valores vinham como floats.
        self.total = Decimal(self.valor_alim or 0)
        super(DetalhamentoAlimentacaoTerminoContrato, self).save()
