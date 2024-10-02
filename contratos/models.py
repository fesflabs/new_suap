from datetime import date, datetime, timedelta
from decimal import Decimal

from django.contrib.auth.models import Group
from django.db.models import Sum, Q

from almoxarifado.models import Empenho
from comum.models import Arquivo, Configuracao, PrestadorServico
from comum.utils import formata_nome_arquivo, somar_data
from djtools.choices import Meses
from djtools.db import models
from djtools.templatetags.filters import in_group
from documento_eletronico.models import TipoDocumento
from protocolo.models import Processo
from rh.models import PessoaJuridica, Servidor, UnidadeOrganizacional, Pessoa

""" Seguro Garantia, Fiança, Caução """
TIPO_GARANTIA_SEGURO = 'SEGURO'
TIPO_GARANTIA_FIANCA = 'FIANCA'
TIPO_GARANTIA_CAUCAO = 'CAUCAO'
TIPO_GARANTIA_SIAFI = 'SIAFI'

TIPO_GARANTIA_CHOICES = [[TIPO_GARANTIA_SEGURO, 'Seguro Garantia'], [TIPO_GARANTIA_FIANCA, 'Fiança'],
                         [TIPO_GARANTIA_CAUCAO, 'Caução'], [TIPO_GARANTIA_SIAFI, 'Registro Garantia no SIAFI']]

TIPO_TERMO_ADITIVO_MAJORACAO = 'MAJ'
TIPO_TERMO_ADITIVO_SUPRESSAO = 'SUP'

TIPO_TERMO_ADITIVO_CHOICES = [[TIPO_TERMO_ADITIVO_MAJORACAO, 'Majoração'], [TIPO_TERMO_ADITIVO_SUPRESSAO, 'Supressão']]


class SituacaoOcorrencia:
    SITUACAO_PENDENTE = 'PEN'
    SITUACAO_RESOLVIDA = 'RES'

    SITUACAO_CHOICES = [[SITUACAO_PENDENTE, 'Pendente'], [SITUACAO_RESOLVIDA, 'Resolvida']]


class TipoContrato(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição', max_length=30)

    class Meta:
        verbose_name = 'Tipo de Contrato'
        verbose_name_plural = 'Tipos de Contratos'

    def __str__(self):
        return self.descricao


class SubtipoContrato(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')
    tipo = models.ForeignKeyPlus(TipoContrato, verbose_name='Tipo de Contrato')

    class Meta:
        verbose_name = 'Subtipo de Contrato'
        verbose_name_plural = 'Subtipos de Contratos'

    def __str__(self):
        return self.descricao


class MotivoConclusaoContrato(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Motivo de Conclusão de Contrato'
        verbose_name_plural = 'Motivos de Conclusão de Contratos'

    def __str__(self):
        return self.descricao


class TipoLicitacao(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Tipo de Licitação'
        verbose_name_plural = 'Tipos de Licitação'

    def __str__(self):
        return self.descricao


class ContratoQueryset(models.QuerySet):
    def ativos(self):
        return self.filter(concluido=False, cancelado=False)

    def concluidos(self):
        return self.filter(concluido=True, cancelado=False)

    def proximos_a_vencer(self):
        hoje = datetime.now().date()
        dias_inicio_licitacao = Configuracao.get_valor_por_chave('contratos', 'dias_nova_licitacao') or 90
        return self.ativos().filter(data_vencimento__gte=hoje, data_vencimento__lte=hoje + timedelta(days=int(dias_inicio_licitacao)))

    def proximos_a_vencer_com_garantias(self):
        return self.proximos_a_vencer().filter(garantias_set__isnull=False)

    def com_vigencia_expirada(self):
        hoje = datetime.now().date()
        return self.ativos().filter(data_vencimento__lt=hoje)

    def com_ocorrencias_expiradas(self):
        hoje = datetime.now()
        return self.ativos().filter(ocorrencia__prazo_resolucao__lt=hoje, ocorrencia__situacao=SituacaoOcorrencia.SITUACAO_PENDENTE)

    def a_serem_aditivados(self):
        daqui_a_30_dias = datetime.now() + timedelta(days=30)
        return self.ativos().filter(continuado=True, data_vencimento__lt=daqui_a_30_dias).order_by('data_vencimento')

    def a_serem_licitados(self):
        data_5_anos_atras = date.today() - timedelta(5 * 365)
        data_5_anos_mais_prazo_licitacao = date.today() - timedelta(5 * 365)
        return self.filter(data_inicio__range=[data_5_anos_atras, data_5_anos_mais_prazo_licitacao]).order_by('data_fim')


class ContratoManager(models.Manager):
    def get_queryset(self):
        return ContratoQueryset(self.model, using=self._db)

    def ativos(self):
        return self.get_queryset().ativos()

    def concluidos(self):
        return self.get_queryset().concluidos()

    def proximos_a_vencer(self):
        return self.get_queryset().proximos_a_vencer()

    def proximos_a_vencer_com_garantias(self):
        return self.get_queryset().proximos_a_vencer_com_garantias()

    def com_vigencia_expirada(self):
        return self.get_queryset().com_vigencia_expirada()

    def com_ocorrencias_expiradas(self):
        return self.get_queryset().com_ocorrencias_expiradas()

    def a_serem_aditivados(self):
        return self.get_queryset().a_serem_aditivados()

    def a_serem_licitados(self):
        return self.get_queryset().a_serem_licitados()


class Contrato(models.ModelPlus):
    SEARCH_FIELDS = ('numero', 'objeto') + tuple('contratada__{}'.format(search) for search in Pessoa.SEARCH_FIELDS)
    tipo = models.ForeignKeyPlus(TipoContrato, verbose_name='Tipo de Contrato', related_name='contratos_set', on_delete=models.CASCADE)
    subtipo = models.ForeignKeyPlus(SubtipoContrato, verbose_name='SubTipo de Contrato', on_delete=models.CASCADE, null=True, blank=True)
    numero = models.CharFieldPlus('Número', help_text='No formato: 99999/9999', unique=False)
    valor = models.DecimalFieldPlus('Valor do Contrato')
    valor_executado = models.DecimalFieldPlus('Valor Executado', null=True, blank=True)
    valor_total = models.DecimalFieldPlus('Valor Total', null=True, blank=True)
    valor_previsto_parcela = models.DecimalFieldPlus(null=True, blank=True)

    data_inicio = models.DateFieldPlus('Data de Início', db_column='data_inicio')
    data_fim = models.DateField(
        'Data de Término', db_column='data_fim', null=True, blank=True, help_text='Caso você não informe uma Data de Término, o Contrato vai ser considerado como Indeterminado'
    )
    data_vencimento = models.DateField('Data de Vencimento do Contrato', null=True, blank=True)
    objeto = models.TextField('Objeto de Contrato', max_length=500)
    continuado = models.BooleanField('É Continuado?', default=False)
    arrecadacao_receita = models.BooleanField('Possui arrecadação de receita?', default=False, help_text='Caso esta opção seja marcada, será possível registrar Valores de Concessão para o contrato')
    processo = models.ForeignKeyPlus(Processo, related_name='contrato_processo_set', null=True, blank=False, verbose_name='Processo', on_delete=models.CASCADE)
    empenho = models.ForeignKeyPlus(Empenho, related_name='contrato_empenho_set', null=True, verbose_name='Empenho', on_delete=models.CASCADE)
    campi = models.ManyToManyField(UnidadeOrganizacional, db_column='campus_id', related_name='contrato_uo_set', verbose_name='Campi')
    pessoa_contratada = models.ForeignKeyPlus(Pessoa, null=False, verbose_name='Pessoa Contratada', related_name='pessoacontratada_set', on_delete=models.CASCADE)
    contratada = models.ForeignKeyPlus(PessoaJuridica, null=True, verbose_name='Contratada', on_delete=models.CASCADE)
    qtd_parcelas = models.SmallIntegerField(db_column='qtd_parcelas', verbose_name='Quantidade de Parcelas', default=1)

    arquivo = models.OneToOneField(Arquivo, null=True, on_delete=models.CASCADE)
    arquivo_contrato = models.PrivateFileField(
        verbose_name='Arquivo do Contrato', upload_to='contratos/arquivos/', filetypes=['pdf'], help_text='O formato do arquivo deve ser ".pdf"', null=True, max_length=500
    )

    # Licitação
    tipo_licitacao = models.ForeignKeyPlus(TipoLicitacao, related_name='contratos_set', verbose_name='Tipo de Licitação', null=True, blank=True, on_delete=models.CASCADE)
    pregao = models.CharField('Pregão', max_length=100, null=True, blank=True)
    pregao = models.CharField('Pregão', max_length=100, null=True, blank=True)
    estimativa_licitacao = models.DateField('Estimativa para início dos procedimentos para nova Licitação', null=True, blank=True)

    # Conclusao
    data_conclusao = models.DateField('Data de Conclusão', null=True, blank=True)
    concluido = models.BooleanField('Concluído?', default=False)
    motivo_conclusao = models.ForeignKeyPlus(MotivoConclusaoContrato, verbose_name='Motivo de Conclusão', null=True, blank=True)

    # Cancelamento
    cancelado = models.BooleanField('Cancelado?', default=False)
    motivo_cancelamento = models.TextField('Motivo de Cancelamento', blank=True)
    dh_cancelamento = models.DateTimeField('Data/Hora Cancelamento', blank=True, null=True)
    usuario_cancelamento = models.ForeignKeyPlus(
        'comum.User', verbose_name='Usuário Cancelamento', related_name="usuario_cancelamento", null=True, blank=True, editable=False, on_delete=models.CASCADE
    )

    numero_processo = models.CharField('Número Processo', max_length=20, null=True, blank=True)
    numero_empenho = models.CharField(verbose_name='Números de Empenhos', help_text='Números de Empenhos separados por vírgula', max_length=100, null=True, blank=True)

    # Garantia
    exige_garantia_contratual = models.BooleanField(' Possui exigência de garantia contratual?', default=False)

    objects = ContratoManager()

    class Meta:
        verbose_name = 'Contrato'
        verbose_name_plural = 'Contratos'
        permissions = (
            ("pode_visualizar_contrato", "Pode visualizar contrato"),
            ("pode_submeter_arquivo", "Pode submeter arquivo"),
            ("pode_visualizar_arquivo", "Pode visualizar aquivo"),
            ("pode_efetuar_medicao", "Pode efetuar medição"),
            ("pode_gerar_cronograma", "Pode gerar cronograma"),
            ("pode_visualizar_cronograma", "Pode visualizar cronograma"),
            ("pode_adicionar_publicacao", "Pode adicionar publicação"),
            ("pode_excluir_publicacao", "Pode excluir publicação"),
            ("pode_submeter_publicacao", "Pode submeter publicação"),
            ("pode_adicionar_anexo", "Pode adicionar anexo"),
            ("pode_visualizar_anexo", "Pode visualizar anexo"),
            ("pode_visualizar_publicacao", "Pode visualizar publicação"),
            ("pode_adicionar_fiscal", "Pode adicionar fiscal"),
            ("pode_excluir_fiscal", "Pode exlcuir fiscal"),
            ("pode_aditivar_contrato", "Pode aditivar contrato"),
            ("pode_cancelar_contrato", "Pode cancelar contrato"),
            ("pode_submeter_medicao", "Pode submeter medição"),
        )

    def __str__(self):
        return '{}'.format(self.numero)

    def get_absolute_url(self):
        return "/contratos/contrato/{}/".format(self.id)

    def delete(self, *args, **kwargs):
        for obj in PublicacaoContrato.objects.filter(contrato__id=self.id):
            obj.delete()
        for obj in AnexoContrato.objects.filter(contrato__id=self.id):
            obj.delete()
        for obj in Aditivo.objects.filter(contrato__id=self.id):
            obj.delete()

        arquivo = self.arquivo
        super().delete(*args, **kwargs)
        if arquivo:
            arquivo.delete()

    def save(self, *args, **kwargs):
        self.data_vencimento = self.get_data_vencimento()
        self.valor_executado = self.get_valor_executado()
        self.valor_total = self.get_valor_total()
        self.valor_previsto_parcela = self.get_valor_previsto_parcela()
        super().save(*args, **kwargs)

    def get_qtd_dias_total(self):
        return (self.get_data_fim() - self.data_inicio).days if self.get_data_fim() else (datetime.now().date() - self.data_inicio).days

    def get_qtd_dias_executado(self):
        return (date.today() - self.data_inicio).days

    def get_percentual_dias_executado(self):
        qtd_dias_total = self.get_qtd_dias_total()
        if qtd_dias_total == 0:
            return 0

        percentual = int(self.get_qtd_dias_executado() * 100 / qtd_dias_total)
        if percentual > 100:
            return 100
        if percentual < 0:
            return 0
        return percentual

    def get_percentual_executado(self):
        percentual = 0
        if self.valor_total > 0:  # evita divisao por zero
            percentual = Decimal('100') * self.valor_executado / self.valor_total
        return int(percentual)

    def get_valor_total(self):
        return self.valor + self.get_valor_aditivado() + self.get_valor_apostilado()

    def get_valor_executado(self):
        total = Decimal('0')
        cronograma = self.get_cronograma()
        if cronograma:
            for parcela in cronograma.parcelas_set.all():
                for medicao in parcela.medicoes_set.all():
                    total += medicao.valor_executado
        return total

    def get_valor_previsto_parcela(self):
        total = Decimal('0')
        cronograma = self.get_cronograma()
        if cronograma:
            for parcela in Parcela.objects.filter(cronograma=cronograma, medicoes_set__isnull=True):
                total += parcela.valor_previsto
        return total

    def get_saldo_contrato(self):
        return self.valor_total - (self.valor_previsto_parcela + self.valor_executado)

    def get_saldo_atual(self):
        return self.valor_total - (self.valor_executado)

    def get_total_arrecadacao(self):
        return ArrecadacaoReceita.objects.filter(contrato=self).aggregate(total=Sum('valor'))['total'] or 0

    def adicionar_termo_aditivo(self, termo):
        ultimo_termo = self.get_ultimo_termo_aditivo()
        if ultimo_termo:
            termo.ordem = ultimo_termo.ordem + 1
        else:
            termo.ordem = 1
        termo.contrato = self
        termo.save()
        return termo

    def adicionar_fiscal(self, fiscal):
        if not in_group(fiscal.servidor.user, 'Fiscal de Contrato'):
            fiscal.servidor.user.groups.add(Group.objects.get(name='Fiscal de Contrato'))
        fiscal.contrato = self
        fiscal.save()
        return fiscal

    def adicionar_anexo(self, anexo):
        anexo.contrato = self
        anexo.save()
        return anexo

    def get_publicacoes(self):
        return PublicacaoAditivo.objects.filter(aditivo__contrato=self).order_by('aditivo', 'data')

    def adicionar_publicacao(self, publicacao):
        publicacao.contrato = self
        publicacao.save()
        return publicacao

    def get_publicacoes_contrato(self):
        return PublicacaoContrato.objects.filter(contrato=self).order_by('id')

    def get_fiscais_atuais(self):
        return self.fiscais_set.filter(data_exclusao__isnull=True, inativo=False)

    def get_fiscal(self, servidor):
        return self.get_fiscais_atuais().filter(servidor=servidor).first()

    def eh_fiscal(self, servidor):
        return self.get_fiscais_atuais().filter(servidor=servidor).exists()

    def eh_gestor_contrato(self, servidor):
        return self.get_fiscais_atuais().filter(servidor=servidor, tipo__eh_gestor_contrato=True).exists()

    def get_uos_as_string(self):
        return ', '.join(self.campi.all().values_list('sigla', flat=True))

    def set_cronograma(self, cronograma):
        cronograma.contrato = self
        cronograma.save()

    def get_cronograma(self):
        cronogramas = self.cronograma_set.all()
        if cronogramas.exists():
            return cronogramas.latest('id')
        else:
            return None

    def get_valor_aditivado(self):
        total = Decimal('0')
        for aditivo in self.aditivos_set.all():
            if aditivo.de_valor and aditivo.valor:  # evita NoneType em aditivo.valor
                if aditivo.tipo_termo_aditivo == TIPO_TERMO_ADITIVO_SUPRESSAO:
                    total = total - aditivo.valor
                else:
                    total += aditivo.valor
        return total

    def get_valor_apostilado(self):
        total = Decimal('0')
        for apostilamento in self.apostilamentos_set.all():
            if apostilamento.valor:  # evita NoneType em aditivo.valor
                total += apostilamento.valor
        return total

    def get_data_fim(self):
        data = self.data_fim
        for aditivo in self.aditivos_set.all().order_by('data_fim'):
            if aditivo.de_prazo and aditivo.data_fim:
                data = aditivo.data_fim
        return data

    def get_apostilamentos(self):
        return self.apostilamentos_set.all()

    def get_data_vencimento(self):
        data_vencimento = self.data_fim
        ultimo_aditivo = None
        if data_vencimento:
            ultimo_aditivo = self.aditivos_set.filter(de_prazo=True, data_fim__gt=data_vencimento).order_by('data_fim').last()
        return ultimo_aditivo.data_fim if ultimo_aditivo else data_vencimento

    def get_data_prorrogacao(self):
        if self.continuado is True:
            data_inicio = self.data_inicio
            ultimo_aditivo = self.aditivos_set.filter(de_prazo=True, data_inicio__gt=self.data_inicio).order_by('-data_inicio').last()
            data_inicial = ultimo_aditivo.data_inicio if ultimo_aditivo else data_inicio
            return data_inicial + timedelta(5 * 365)

    def get_aditivos(self):
        return self.aditivos_set.all().order_by('ordem')

    def get_ultimo_termo_aditivo(self):
        return self.aditivos_set.order_by('-ordem').first()

    @classmethod
    def get_pendencias(cls, uo):
        contratos_pendentes = {}

        # lista todos os contratos
        contratos = cls.objects.ativos()

        # informou campus?
        if uo:
            contratos = contratos.filter(campi=uo.pk)

        # itera contratos para verificar pendências
        for contrato in contratos:
            pendencias = []

            # anexou arquivo digitalizado (Informações Gerais do Contrato)?
            if not contrato.arquivo:
                pendencias.append("Arquivo digitalizado não anexado")

            # anexou arquivo da Publicação?
            if not contrato.publicacoes_set.exists():
                pendencias.append("Publicações do contrato não informadas")

            # verificando se alguma publicação está sem anexo
            for publicacao in contrato.publicacoes_set.all():
                if not publicacao.arquivo:
                    pendencias.append("Há publicações sem anexo")
                    break

            # verificando se algum termo aditivo está sem anexo
            for aditivo in contrato.aditivos_set.all():
                if not aditivo.arquivo:
                    pendencias.append("Há termo aditivo sem anexo")
                    break

            # verificando se contrato tem fiscal
            if not contrato.fiscais_set.exists():
                pendencias.append("Contrato sem fiscal definido")

            # verificando se contrato tem cronograma
            if not contrato.cronograma_set.exists():
                pendencias.append("Contrato sem cronograma")

            # verificando se parcelas no cronograma
            for cronograma in contrato.cronograma_set.all():
                if not cronograma.parcelas_set.exists():
                    pendencias.append("Cronograma sem parcelas")

            # se tem pendência, associa mensagens (removendo pendências duplicadas)
            if pendencias:
                contratos_pendentes[contrato] = {'mensagens': set(pendencias)}

        return contratos_pendentes

    def get_qtd_documentos_relacionados(self):
        return self.anexos_set.all().count() + self.documentotexto_contrato_set.all().count()

    def documentos_texto_tipo_contato_relacionados(self):
        tipo_documento_contrato = TipoDocumento.objects.filter(nome="Contrato", ativo=True).first()
        return self.documentotexto_contrato_set.filter(documento__modelo__tipo_documento_texto=tipo_documento_contrato)


class TipoPublicacao(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Tipo de Publicação'
        verbose_name_plural = 'Tipos de Publicações'

    def __str__(self):
        return self.descricao


class PublicacaoContrato(models.ModelPlus):
    contrato = models.ForeignKeyPlus(Contrato, verbose_name='Contrato', related_name='publicacoes_set', on_delete=models.CASCADE)
    tipo = models.ForeignKeyPlus(TipoPublicacao, verbose_name='Tipo de Publicação', on_delete=models.CASCADE)
    numero = models.CharFieldPlus('Número')
    data = models.DateField()
    descricao = models.CharFieldPlus('Descrição', help_text='Breve descrição sobre o conteúdo da publicação')
    arquivo = models.OneToOneField(Arquivo, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Publicação'
        verbose_name_plural = 'Publicações'

    def __str__(self):
        return '{} {}'.format(self.tipo, self.descricao)

    def delete(self, *args, **kwargs):
        arquivo = self.arquivo
        super().delete(*args, **kwargs)
        if arquivo:
            arquivo.delete()


class TipoAnexo(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')

    class Meta:
        verbose_name = 'Tipo de Anexo'
        verbose_name_plural = 'Tipos de Anexos'

    def __str__(self):
        return self.descricao


class TipoFiscal(models.ModelPlus):
    descricao = models.CharFieldPlus(verbose_name='Descrição')
    pode_gerenciar_todas_medicoes_contrato = models.BooleanField(verbose_name='Fiscal pode gerenciar medições de outros fiscais?', default=False)
    eh_gestor_contrato = models.BooleanField(verbose_name='É gestor do contrato?', default=False, help_text='Um Fiscal Gestor do Contrato poderá gerar o Termo de Recebimento Definitivo.')

    class Meta:
        verbose_name = 'Tipo de Fiscal'
        verbose_name_plural = 'Tipos de Fiscais'
        ordering = ('descricao',)

    def __str__(self):
        return self.descricao


def anexo_apostilamento_path(instance, filename):
    filename = formata_nome_arquivo(filename)
    return 'contratos/contrato/{}/apostilamento/anexo_{}{}'.format(instance.contrato.id, instance.id, filename)


class Apostilamento(models.ModelPlus):
    contrato = models.ForeignKeyPlus(Contrato, related_name='apostilamentos_set', on_delete=models.CASCADE)
    especificacao = models.TextField('Especificação', null=True, blank=True)
    numero = models.CharFieldPlus('Número', help_text='No formato: 99999/9999')
    valor = models.DecimalFieldPlus('Valor', null=True, blank=True)
    data_inicio = models.DateFieldPlus('Data de Início', null=True, blank=True)
    data_fim = models.DateFieldPlus('Data de Vencimento', null=True, blank=True)
    arquivo = models.FileFieldPlus(upload_to=anexo_apostilamento_path)
    numero_processo = models.CharFieldPlus('Número Processo', max_length=20, null=True, blank=True)
    numero_empenho = models.CharFieldPlus('Números de Empenhos', null=True, blank=True, help_text='Números de Empenhos separados por vírgula')

    class Meta:
        verbose_name = 'Apostilamento'
        verbose_name_plural = 'Apostilamentos'

    def __str__(self):
        return '{} - {}'.format(self.contrato, self.numero)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.contrato.save()

    def delete(self, *args, **kwargs):
        contrato = self.contrato
        super().delete(*args, **kwargs)
        contrato.save()


class Aditivo(models.ModelPlus):
    contrato = models.ForeignKeyPlus(Contrato, related_name='aditivos_set', on_delete=models.CASCADE)
    ordem = models.PositiveSmallIntegerField('Ordem', default=0)
    numero = models.CharFieldPlus('Número', help_text='No formato: 99999/9999', unique=False)
    valor = models.DecimalFieldPlus('Valor', null=True, blank=True)
    data_inicio = models.DateFieldPlus('Data de Início', db_column='data_inicio', null=True, blank=True)
    data_fim = models.DateFieldPlus('Data de Vencimento', db_column='data_fim', null=True, blank=True)
    processo = models.ForeignKeyPlus(Processo, related_name='aditivo_processo_set', null=True, verbose_name='Processo', on_delete=models.CASCADE)
    empenho = models.ForeignKeyPlus(Empenho, related_name='aditivo_empenho_set', null=True, verbose_name='Empenho', on_delete=models.CASCADE)
    arquivo = models.OneToOneField(Arquivo, null=True, on_delete=models.CASCADE)
    de_prazo = models.BooleanField('Aditivo de Prazo', default=False)
    de_valor = models.BooleanField('Aditivo de Valor', default=False)
    de_fiscal = models.BooleanField('Aditivo de Fiscal', default=False)
    de_outro = models.BooleanField('Outros', default=False)
    especificacao = models.TextField('Especificação', null=True, blank=True)
    tipo_termo_aditivo = models.CharFieldPlus('Tipo de Termo de Aditivo', max_length=5, choices=TIPO_TERMO_ADITIVO_CHOICES, null=True, blank=True)
    numero_parcelas = models.PositiveSmallIntegerField('Número de Parcelas', null=True, blank=True)
    numero_processo = models.CharFieldPlus('Número Processo', max_length=20, null=True, blank=True)
    numero_empenho = models.CharFieldPlus('Números de Empenhos', null=True, blank=True, help_text='Números de Empenhos separados por vírgula')

    class Meta:
        verbose_name = 'Termo Aditivo'
        verbose_name_plural = 'Termos Aditivos'
        unique_together = ('contrato', 'ordem')  # Saber se o número é unico ou pode ser repetido no termoo aditivo

    def __str__(self):
        return '{}º Termo ({})'.format(self.ordem, self.get_tipo())

    def save(self, *args, **kwargs):
        if not (self.ordem):
            self.ordem = self.contrato.get_proxima_ordem()
        super().save(*args, **kwargs)
        self.contrato.save()

    def delete(self, *args, **kwargs):
        contrato = self.contrato
        for obj in PublicacaoAditivo.objects.filter(aditivo__id=self.id):
            obj.delete()
        arquivo = self.arquivo
        super().delete(*args, **kwargs)
        if arquivo:
            arquivo.delete()
        contrato.save()

    def adicionar_publicacao(self, publicacao):
        publicacao.aditivo = self
        publicacao.save()
        return publicacao

    def get_tipo(self):
        tipo = []
        if self.de_prazo:
            tipo.append('de Prazo')
        if self.de_valor:
            tipo.append('de Valor')
        if self.de_fiscal:
            tipo.append('de Fiscal')
        if self.de_outro:
            tipo.append('de Outro')
        if len(tipo) == 0:
            tipo = ['Indefinido']

        return ', '.join(tipo)

    def get_fiscais(self):
        return self.contrato.fiscais_set.filter(termo_aditivo=self)

    def get_qtd_dias_total(self):
        return (self.data_fim - self.data_inicio).days if self.data_fim and self.data_inicio else 0

    def get_qtd_dias_executado(self):
        return (date.today() - self.data_inicio).days if self.data_fim and self.data_inicio and date.today() < self.data_fim else self.get_qtd_dias_total()

    def get_percentual_dias_executado(self):
        qtd_dias_total = self.get_qtd_dias_total()
        if qtd_dias_total == 0:
            return 0

        percentual = int(self.get_qtd_dias_executado() * 100 / qtd_dias_total)
        if percentual > 100:
            return 100
        if percentual < 0:
            return 0
        return percentual


class MaoDeObra(models.ModelPlus):
    contrato = models.ForeignKeyPlus(Contrato, related_name='maodeobra_set', on_delete=models.CASCADE)
    prestador_servico = models.ForeignKeyPlus(PrestadorServico, related_name='prestadorservico_set', on_delete=models.PROTECT)
    data_nascimento = models.DateFieldPlus('Data de Nascimento')
    categoria = models.CharFieldPlus('Categoria')
    funcao = models.CharFieldPlus('Função')
    escolaridade = models.CharFieldPlus('Escolaridade', max_length=100)
    jornada_trabalho = models.CharFieldPlus('Jornada de Trabalho', max_length=40)
    salario_bruto = models.DecimalFieldPlus('Salário Bruto')
    custo_mensal = models.DecimalFieldPlus('Custo Mensal')
    desligamento = models.DateFieldPlus('Data de Desligamento', null=True)
    numero_cct = models.CharFieldPlus('Número da CCT', max_length=50, blank=True)
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus', null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Mão-de-Obra'
        verbose_name_plural = 'Mãos-de-Obra'

    def __str__(self):
        return '{} - {}'.format(self.contrato, self.prestador_servico)

    def adicionar_anexo(self, anexo):
        anexo.maodeobra = self
        anexo.save()
        return anexo


class AnexoMaoDeObra(models.ModelPlus):
    maodeobra = models.ForeignKeyPlus(MaoDeObra, related_name='anexos_set', on_delete=models.CASCADE)
    descricao = models.CharFieldPlus(verbose_name='Descrição')
    arquivo = models.FileFieldPlus(verbose_name="Arquivo", upload_to='contratos/maodeobra/')
    data = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'

    def __str__(self):
        return self.descricao


def consulta_susep_path(instance, filename):
    filename = formata_nome_arquivo(filename)
    return 'contratos/contrato/{}/consulta_susep/anexo_{}{}'.format(instance.contrato.id, instance.id, filename)


class Garantia(models.ModelPlus):
    contrato = models.ForeignKeyPlus(Contrato, related_name='garantias_set', on_delete=models.CASCADE)
    tipo = models.CharFieldPlus('Tipo de Garantia', max_length=20, choices=TIPO_GARANTIA_CHOICES)
    data_inicio = models.DateFieldPlus('Data de Início', null=True, blank=True)
    vigencia = models.DateFieldPlus('Data de Vigência')
    pa_siafi = models.CharFieldPlus('PA do SIAFI', help_text='Lançamento patrimonial (PA) SIAFI')
    valor = models.DecimalFieldPlus()
    consulta_susep = models.FileFieldPlus('Anexo', help_text='Susep, anexos, etc', upload_to=consulta_susep_path, null=True)

    class Meta:
        verbose_name = 'Garantia'
        verbose_name = 'Garantias'

    def __str__(self):
        return '{} - {}: {}'.format(self.contrato, self.tipo, self.vigencia)


def penalidade_path(instance, filename):
    filename = formata_nome_arquivo(filename)
    return 'contratos/contrato/{:d}/penalidade_{}'.format(instance.contrato.id, filename)


class Penalidade(models.ModelPlus):
    TIPO_PENALIDADE_ADVERTENCIA = 'Advertência'
    TIPO_PENALIDADE_MULTA = 'Multa'
    TIPO_PENALIDADE_SUSPENSAO = 'Suspensão'

    TIPO_PENALIDADE_CHOICES = [[TIPO_PENALIDADE_ADVERTENCIA, 'Advertência'], [TIPO_PENALIDADE_MULTA, 'Multa'], [TIPO_PENALIDADE_SUSPENSAO, 'Suspensão']]

    contrato = models.ForeignKeyPlus(Contrato, related_name='penalidades_set', on_delete=models.CASCADE)
    tipo = models.CharFieldPlus('Tipo', max_length=20, choices=TIPO_PENALIDADE_CHOICES)
    arquivo = models.FileFieldPlus(upload_to=penalidade_path, verbose_name='Arquivo')

    atualizado_por = models.ForeignKeyPlus('comum.Vinculo', null=True, related_name='atualizado_por_vinculo', verbose_name='Atualizado Por', on_delete=models.CASCADE)
    atualizado_em = models.DateTimeField('Atualizado em', auto_now=True, null=True, blank=True)

    class Meta:
        verbose_name = 'Penalidade'
        verbose_name = 'Penalidades'
        ordering = ('-atualizado_em',)

    def __str__(self):
        return '{} - {}'.format(self.contrato, self.tipo)

    def delete(self, *args, **kwargs):
        arquivo = self.arquivo
        if arquivo:
            arquivo.delete()
        super().delete(*args, **kwargs)


class AnexoContrato(models.ModelPlus):
    contrato = models.ForeignKeyPlus(Contrato, related_name='anexos_set', on_delete=models.CASCADE)
    tipo = models.ForeignKeyPlus(TipoAnexo, on_delete=models.CASCADE)
    descricao = models.CharFieldPlus('Descrição', help_text='Breve descrição sobre o conteúdo do anexo')
    arquivo = models.OneToOneField(Arquivo, null=True, on_delete=models.CASCADE)
    data = models.DateTimeField(null=True)
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus',
                                   on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'

    def __str__(self):
        return '{} {}'.format(self.tipo, self.descricao)

    def delete(self, *args, **kwargs):
        arquivo = self.arquivo
        super().delete(*args, **kwargs)
        if arquivo:
            arquivo.delete()


class DocumentoTextoContrato(models.ModelPlus):
    contrato = models.ForeignKeyPlus(Contrato, related_name='documentotexto_contrato_set', on_delete=models.CASCADE)
    documento = models.ForeignKeyPlus('documento_eletronico.DocumentoTexto', verbose_name='Documento')

    # CRIAÇÃO DO VÍNCULO ENTRE DOCUMENTO E CONTRATO
    data_hora_inclusao = models.DateTimeFieldPlus('Data de Inclusão', auto_now_add=True, editable=False)
    usuario_inclusao = models.CurrentUserField(verbose_name='Usuário de Inclusão', related_name='%(app_label)s_%(class)s_documentos_processos_criados', null=False, editable=False)

    # REMOCÃO LÓGICA DO VÍNCULO ENTRE DOCUMENTO E CONTRATO
    data_hora_remocao = models.DateTimeFieldPlus('Data de Remoção', blank=True, null=True, editable=False)
    usuario_remocao = models.ForeignKeyPlus(
        'comum.User',
        verbose_name='Usuário de Remoção',
        related_name='%(app_label)s_%(class)s_documentos_processos_alterados',
        editable=False,
        blank=True,
        null=True,
        on_delete=models.CASCADE,
    )

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return 'Doc. {} - Contrato {}'.format(self.documento, self.contrato)


class Fiscal(models.ModelPlus):
    contrato = models.ForeignKeyPlus(Contrato, related_name='fiscais_set', on_delete=models.CASCADE)
    tipo = models.ForeignKeyPlus(TipoFiscal, on_delete=models.CASCADE)
    servidor = models.ForeignKeyPlus(Servidor, on_delete=models.CASCADE)
    numero_portaria = models.CharFieldPlus('Portaria', max_length=20)
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, db_column='campus_id', verbose_name='Campi', on_delete=models.CASCADE)
    data_nomeacao = models.DateFieldPlus('Data da Nomeação', null=True, blank=True, help_text='Data em que o servidor foi nomeado fiscal do contrato (consultar portaria)')
    data_vigencia = models.DateFieldPlus('Data da Vigência', null=True, blank=True, help_text='Data limite prevista para atuação como fiscal do contrato (consultar portaria)')
    data_exclusao = models.DateFieldPlus('Data da Exclusão', null=True)
    termo_aditivo = models.ForeignKeyPlus(Aditivo, null=True, blank=True, on_delete=models.CASCADE)
    inativo = models.BooleanField('Inativo?', default=False)

    class Meta:
        verbose_name = 'Fiscal'
        verbose_name_plural = 'Fiscais'
        ordering = ('inativo',)

    def __str__(self):
        return '{} ({})'.format(self.servidor.nome, str(self.campus))


class PublicacaoAditivo(models.ModelPlus):
    aditivo = models.ForeignKeyPlus(Aditivo, related_name='publicacoes_set', on_delete=models.CASCADE)
    tipo = models.ForeignKeyPlus(TipoPublicacao, on_delete=models.CASCADE)
    numero = models.CharFieldPlus('Número', max_length=50)
    data = models.DateFieldPlus('Data da Publicação')
    descricao = models.CharFieldPlus('Descrição', max_length=255, help_text='Breve descrição sobre o conteúdo da publicação')
    arquivo = models.OneToOneField(Arquivo, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Publicação'
        verbose_name_plural = 'Publicações'

    def __str__(self):
        return '{} {}'.format(self.tipo, self.descricao)

    def delete(self, *args, **kwargs):
        arquivo = self.arquivo
        super().delete(*args, **kwargs)
        if arquivo:
            arquivo.delete()


class Cronograma(models.ModelPlus):
    numero = models.CharFieldPlus('Número do Cronograma', max_length=50, null=False)
    nl = models.CharFieldPlus('NL', help_text='Nota de Lançamento', max_length=25, null=True)
    rc = models.CharFieldPlus('RC', max_length=25, help_text='Registro de Contrato', null=True)
    contrato = models.ForeignKeyPlus(Contrato, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Cronograma'
        verbose_name_plural = 'Cronogramas'

    def __str__(self):
        return '{}'.format(self.numero)

    def get_parcelas(self):
        return self.parcelas_set.order_by('data_prevista_inicio')

    def adicionar_parcela(self, parcela):
        parcela.cronograma = self
        # if self.contrato.get_saldo_contrato() < parcela.valor_previsto:
        parcela.save()
        return parcela

    def delete(self, *args, **kwargs):
        contrato = self.contrato
        super().delete(*args, **kwargs)
        contrato.save()


class Parcela(models.ModelPlus):
    cronograma = models.ForeignKeyPlus(Cronograma, related_name='parcelas_set', on_delete=models.CASCADE)
    data_prevista_inicio = models.DateField(verbose_name='Data Prevista Início')
    data_prevista_fim = models.DateField(verbose_name='Data Prevista Conclusão')
    valor_previsto = models.DecimalField(decimal_places=2, max_digits=9)
    sem_medicao = models.BooleanField(verbose_name='Parcela Sem Medição', null=True)

    class Meta:
        verbose_name = 'Parcela de Contrato'
        verbose_name_plural = 'Parcelas de Contrato'

    def __str__(self):
        return str(self.valor_previsto)

    def registrar_medicao(self, medicao):
        medicao.data_medicao = datetime.today()
        medicao.parcela = self
        medicao.save()

    def pode_ser_excluida(self):
        return not self.is_medida()

    def valor_executado_parcela(self):
        return self.medicoes_set.aggregate(valor_executado_parcela=Sum('valor_executado'))['valor_executado_parcela']

    def is_medida(self):
        return self.medicoes_set.exists()

    def is_not_medida(self):
        return not self.is_medida()

    def get_medicoes(self, uo=None):
        if uo:
            return self.medicoes_set.filter(campus=uo)
        else:
            return self.medicoes_set.all()

    @classmethod
    def get_parcelas_nao_medidas(cls, uo=None):
        # por questão de peformance, apenas as parcelas dos três ultimos meses serão levados em consideracao
        parcelas = (
            Parcela.objects.filter(data_prevista_fim__lt=datetime.today())
            .filter(data_prevista_fim__gt=somar_data(datetime.today(), -90))
            .filter(cronograma__contrato__concluido=False)
            .filter(cronograma__contrato__cancelado=False)
            .filter(medicoes_set__isnull=True)
            .order_by('data_prevista_inicio')
        )

        if uo:
            parcelas = parcelas.filter(cronograma__contrato__campi=uo)
        return parcelas

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.cronograma.contrato.save()

    def delete(self, *args, **kwargs):
        contrato = self.cronograma.contrato
        super().delete(*args, **kwargs)
        contrato.save()


class Medicao(models.ModelPlus):
    parcela = models.ForeignKeyPlus(Parcela, related_name='medicoes_set', on_delete=models.CASCADE)
    data_inicio = models.DateField(null=False)
    data_fim = models.DateField(null=False)
    data_medicao = models.DateField(null=False)
    numero_documento = models.CharField(max_length=50, verbose_name='Número do Documento', null=False)
    valor_executado = models.DecimalField(decimal_places=2, max_digits=9, null=False)
    fiscal = models.ForeignKeyPlus(Fiscal, null=False, on_delete=models.CASCADE)
    ocorrencia = models.TextField(max_length=500, verbose_name='Ocorrência', null=False)
    providencia = models.TextField(max_length=500, verbose_name='Providência Adotada', null=True)
    arquivo = models.OneToOneField(Arquivo, null=True, on_delete=models.CASCADE)
    processo = models.ForeignKeyPlus(Processo, related_name='medicao_processo_set', null=True, verbose_name='Processo', on_delete=models.PROTECT)
    numero_processo = models.CharField('Número Processo', max_length=30, null=True, blank=True)
    despacho_documentotexto = models.ForeignKeyPlus(
        'documento_eletronico.DocumentoTexto', null=True, on_delete=models.PROTECT, related_name='medicoes_despacho_set', verbose_name="Despacho - Documento Eletrônico"
    )
    termo_definitivo_documentotexto = models.ForeignKeyPlus(
        'documento_eletronico.DocumentoTexto', null=True, on_delete=models.PROTECT, related_name='medicoes_termo_definitivo_set', verbose_name="Termo de Recebimento Definitivo - Documento Eletrônico"
    )
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus', null=True, blank=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Medição'
        verbose_name_plural = 'Medições'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.parcela.cronograma.contrato.save()

    def delete(self, *args, **kwargs):
        contrato = self.parcela.cronograma.contrato
        super().delete(*args, **kwargs)
        contrato.save()

    def pode_ser_recebida_definitivamente(self):
        if self.medicaotipodocumentocomprobatorio_set.filter(~Q(confirmacao_fiscal=MedicaoTipoDocumentoComprobatorio.NAO_SE_APLICA)).exists() and not self.termo_definitivo_documentotexto:
            return True
        return False

    def foi_recebida_definitivamente(self):
        if not self.medicaotipodocumentocomprobatorio_set.filter(confirmacao_fiscal=MedicaoTipoDocumentoComprobatorio.CONFIRMADO).filter(~Q(recebido_gerente="Recebido")).exists():
            return True
        return False

    def get_update_url(self):
        return "/contratos/atualizar_medicao/{}/{}".format(self.id, self.parcela.cronograma.contrato.id)


class MedicaoEletrica(models.ModelPlus):
    medicao = models.OneToOneFieldPlus(Medicao, null=False, unique=True)
    mes_referencia = models.PositiveIntegerFieldPlus('Mês de Referência', choices=Meses.get_choices(), null=False)
    ano_referencia = models.PositiveIntegerFieldPlus('Ano de Referência', null=False)
    consumo_ponta = models.DecimalFieldPlus('Consumo Ponta(kWh)', null=True, max_digits=12, decimal_places=0)
    consumo_fora_ponta = models.DecimalFieldPlus('Consumo Fora de Ponta(kWh)', null=True, max_digits=12, decimal_places=0)

    class Meta:
        verbose_name = 'Medição Elétrica'
        verbose_name_plural = 'Medições Elétricas'

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.medicao.save()

    def delete(self, *args, **kwargs):
        medicao = self.medicao
        super().delete(*args, **kwargs)
        medicao.save()


def anexo_resposta_ocorrencia_path(instance, filename):
    filename = formata_nome_arquivo(filename)
    return 'contratos/contrato/{:d}/ocorrencia/resposta_{:d}{}'.format(instance.contrato.id, instance.id, filename)


class Ocorrencia(models.ModelPlus):
    data = models.DateTimeField(null=False, auto_now=True)
    contrato = models.ForeignKeyPlus(Contrato, null=False, on_delete=models.CASCADE)
    fiscal = models.ForeignKeyPlus(Fiscal, null=False, on_delete=models.CASCADE)
    descricao = models.TextField(max_length=1024, verbose_name='Descrição', null=False, blank=False)
    campus = models.ForeignKeyPlus(UnidadeOrganizacional, verbose_name='Campus', null=True, blank=True, on_delete=models.CASCADE)
    arquivo = models.OneToOneField(Arquivo, null=True, on_delete=models.CASCADE)
    prazo_resolucao = models.DateField('Prazo para Resolução', null=True)
    situacao = models.CharField('Situação', max_length=3, choices=SituacaoOcorrencia.SITUACAO_CHOICES, null=True, blank=True)
    anexo_resposta = models.FileFieldPlus(upload_to=anexo_resposta_ocorrencia_path, null=True)
    notificacao_enviada = models.BooleanField(verbose_name='Notificação Enviada?', default=False)

    class Meta:
        verbose_name = 'Ocorrência'
        verbose_name_plural = 'Ocorrências'


class TipoDocumentoComprobatorio(models.ModelPlus):
    descricao = models.CharFieldPlus('Descrição')
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Tipo de Documento Comprobatório para Medição'
        verbose_name_plural = 'Tipos de Documentos Comprobatórios para Medição'

    def __str__(self):
        return self.descricao


class ContratoTipoDocumentoComprobatorio(models.ModelPlus):
    contrato = models.ForeignKeyPlus(Contrato, null=False, blank=False, on_delete=models.CASCADE)
    tipo_documento_comprobatorio = models.ForeignKeyPlus(TipoDocumentoComprobatorio, null=False, blank=False, on_delete=models.PROTECT)

    class Meta:
        verbose_name = 'Tipo de Documento Comprobatório do Contrato'
        verbose_name_plural = 'Tipos de Documentos Comprobatórios do Contrato'

    def __str__(self):
        return self.contrato.numero + " - " + self.tipo_documento_comprobatorio.descricao


class MedicaoTipoDocumentoComprobatorio(models.ModelPlus):
    CONFIRMADO = 1
    NAO_SE_APLICA = 2
    CONFIMACAO_FISCAL_CHOICES = [
        [CONFIRMADO, 'Sim'],
        [NAO_SE_APLICA, 'Não se aplica'],
    ]

    medicao = models.ForeignKeyPlus(Medicao, null=False, blank=False, on_delete=models.CASCADE)
    tipo_documento_comprobatorio = models.ForeignKeyPlus(TipoDocumentoComprobatorio, null=False, blank=False, on_delete=models.CASCADE)
    confirmado = models.BooleanField(default=False, verbose_name="Confirmado")
    confirmacao_fiscal = models.PositiveIntegerFieldPlus(null=True, blank=True, choices=CONFIMACAO_FISCAL_CHOICES, verbose_name="Incluído no Processo:")
    recebido_gerente = models.CharField(null=True, blank=True, max_length=8, choices=[('Recebido', 'Recebido'), ('Pendente', 'Pendente')], verbose_name="Recebimento")
    parecer_gerente = models.CharField(null=True, blank=True, max_length=300, verbose_name="Descrição da Pendência")
    data_avaliacao = models.DateTimeField(null=True, blank=True, verbose_name="Data da Avaliação")
    avaliador_gerente = models.ForeignKeyPlus('comum.User', null=True, blank=True, verbose_name="Avaliador", on_delete=models.CASCADE)

    @property
    def confirmacao_fiscal_display(self):
        return self.CONFIMACAO_FISCAL_CHOICES[int(self.confirmacao_fiscal or 0) - 1][1]

    class Meta:
        verbose_name = 'Documento Comprobatório da Medição'
        verbose_name_plural = 'Documentos Comprobatórios da Medição'

    def __str__(self):
        return self.tipo_documento_comprobatorio.descricao


class ArrecadacaoReceita(models.ModelPlus):
    contrato = models.ForeignKeyPlus(Contrato, related_name='arrecadacaoreceita_set', on_delete=models.CASCADE)
    valor = models.DecimalFieldPlus()
    data = models.DateFieldPlus('Data da Concessão', db_column='data_inicio')

    class Meta:
        verbose_name = 'Arrecadação de Receita'
        verbose_name_plural = 'Arrecadação das Receitas'

    def __str__(self):
        return '{} : {}'.format(self.contrato, self.valor)
