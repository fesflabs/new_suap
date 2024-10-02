# -*- coding: utf-8 -*-

from comum.models import Arquivo, Vinculo
from djtools.db import models
from rh.models import UnidadeOrganizacional, PessoaJuridica
from djtools.utils.calendario import somarDias
import datetime
from comum import utils


class TipoConvenio(models.ModelPlus):
    descricao = models.CharField(max_length=30)

    class Meta:
        verbose_name_plural = 'Tipos de Convênios'
        verbose_name = 'Tipo de Convênio'

    def __str__(self):
        return self.descricao


class TipoAnexo(models.ModelPlus):
    descricao = models.CharField(max_length=30)

    class Meta:
        verbose_name = 'Tipo de Anexo'
        verbose_name_plural = 'Tipos de Anexos'

    def __str__(self):
        return self.descricao


class SituacaoConvenio(models.ModelPlus):
    VIGENTE = 1
    RESCINDIDO = 2
    VINCENDO = 3
    VENCIDO = 4
    descricao = models.CharField(max_length=30)

    class Meta:
        verbose_name_plural = 'Situações de Convênio'
        verbose_name = 'Situação de Convênio'

    def __str__(self):
        return self.descricao


class Convenio(models.ModelPlus):
    SEARCH_FIELDS = ['numero', 'vinculos_conveniadas__pessoa__nome', 'vinculos_conveniadas__pessoa__pessoajuridica__nome_fantasia', 'vinculos_conveniadas__pessoa__pessoajuridica__cnpj', 'vinculos_conveniadas__pessoa__pessoafisica__cpf', 'objeto']

    numero = models.CharField(max_length=10, help_text='No formato: 99999/9999', verbose_name='Número', unique=False)
    tipo = models.ForeignKeyPlus(TipoConvenio, related_name='convenios_set', verbose_name='Tipo', on_delete=models.CASCADE)
    situacao = models.ForeignKeyPlus(SituacaoConvenio, related_name='situacoes_set', verbose_name='Situação', on_delete=models.CASCADE)
    vinculos_conveniadas = models.ManyToManyField(Vinculo, verbose_name='Conveniadas')
    uo = models.ForeignKeyPlus(UnidadeOrganizacional, null=False, verbose_name='Campus', on_delete=models.CASCADE)
    interveniente = models.ForeignKeyPlus(PessoaJuridica, null=True, verbose_name='Interveniente', on_delete=models.CASCADE)
    data_inicio = models.DateField(db_column='data_inicio', verbose_name='Data de Início')
    data_fim = models.DateField(db_column='data_fim', verbose_name='Data de Vencimento')
    objeto = models.TextField(max_length=500)
    continuado = models.BooleanField(verbose_name='Continuado', default=False)
    financeiro = models.BooleanField(verbose_name='Usa Recurso Financeiro', default=False)

    class Meta:
        verbose_name = 'Convênio'
        verbose_name_plural = 'Convênios'

    def __str__(self):
        return 'Convênio nº {}'.format(self.numero)

    def adicionar_termo_aditivo(self, termo):
        ultimo_termo = self.get_ultimo_termo_aditivo()
        if ultimo_termo:
            termo.ordem = ultimo_termo.ordem + 1
        else:
            termo.ordem = 1
        termo.convenio = self
        termo.save()
        return termo

    def adicionar_anexo(self, anexo):
        anexo.convenio = self
        anexo.save()
        return anexo

    def get_conveniadas_as_string(self):
        return ', '.join([str(pj.pessoa) for pj in self.vinculos_conveniadas.all()])

    def delete(self, *args, **kwargs):
        for obj in AnexoConvenio.objects.filter(convenio__id=self.id):
            obj.delete()
        super(Convenio, self).delete(*args, **kwargs)

    def get_aditivos(self):
        return self.aditivos_set.all().order_by('ordem')

    def get_data_vencimento(self):
        data_vencimento = self.data_fim
        aditivos = self.aditivos_set.all()
        for aditivo in aditivos:
            if aditivo.data_fim and (aditivo.data_fim > data_vencimento):
                data_vencimento = aditivo.data_fim
        return data_vencimento

    def get_situacao(self):
        if self.get_data_vencimento() < datetime.datetime.today().date() and self.situacao.pk != SituacaoConvenio.RESCINDIDO:
            if self.situacao.pk != SituacaoConvenio.VENCIDO:
                self.situacao = SituacaoConvenio.objects.get(pk=SituacaoConvenio.VENCIDO)
                self.save()
            return self.situacao
        if (somarDias(self.get_data_vencimento(), -60) < datetime.datetime.today().date()) and self.situacao.pk != SituacaoConvenio.RESCINDIDO:
            if self.situacao.pk != SituacaoConvenio.VINCENDO:
                self.situacao = SituacaoConvenio.objects.get(pk=SituacaoConvenio.VINCENDO)
                self.save()
            return self.situacao
        if self.situacao.pk != SituacaoConvenio.RESCINDIDO:
            if self.situacao.pk != SituacaoConvenio.VIGENTE:
                self.situacao = SituacaoConvenio.objects.get(pk=SituacaoConvenio.VIGENTE)
                self.save()
            return self.situacao
        return self.situacao

    def get_termos_aditivos(self):
        return self.aditivos_set.order_by('ordem')

    def get_ultimo_termo_aditivo(self):
        termos = self.aditivos_set.order_by('-ordem')
        if not termos:
            return None
        return termos[0]

    @staticmethod
    def get_empresas_conveniadas(cls, uo=None, apenas_ativo=False):
        qs = Convenio.objects.all()
        if apenas_ativo:
            qs = qs.filter(data_fim__gte=datetime.datetime.now())
        if uo:
            qs = qs.filter(uo__sigla=utils.get_sigla_reitoria()) | qs.filter(uo=uo)
        return PessoaJuridica.objects.filter(id__in=qs.values_list('vinculos_conveniadas__pessoa__pessoajuridica__id', flat=True)).order_by('nome').distinct()


class AnexoConvenio(models.ModelPlus):
    convenio = models.ForeignKeyPlus(Convenio, related_name='anexos_set', on_delete=models.CASCADE)
    tipo = models.ForeignKeyPlus(TipoAnexo, on_delete=models.CASCADE)
    descricao = models.CharField(max_length=255, verbose_name='Descrição', help_text='Breve descrição sobre o conteúdo do anexo')
    arquivo = models.OneToOneField(Arquivo, null=True, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'

    def __str__(self):
        return '{} - {}'.format(self.tipo, self.descricao)

    def delete(self, *args, **kwargs):
        arquivo = self.arquivo
        super(AnexoConvenio, self).delete(*args, **kwargs)
        if arquivo:
            arquivo.delete()


class Aditivo(models.ModelPlus):
    convenio = models.ForeignKeyPlus(Convenio, related_name='aditivos_set', on_delete=models.CASCADE)
    ordem = models.PositiveSmallIntegerField(default=0)
    numero = models.CharField(max_length=10, verbose_name='Número', unique=False)
    objeto = models.TextField(max_length=500)
    data = models.DateField(db_column='data', verbose_name='Data de Realização', null=False, blank=False)
    data_inicio = models.DateField(db_column='data_inicio', verbose_name='Data de Início', null=True, blank=True)
    data_fim = models.DateField(db_column='data_fim', verbose_name='Data de Vencimento', null=True, blank=True)

    class Meta:
        unique_together = ('convenio', 'ordem')  # Saber se o número é unico ou pode ser repetido no termoo aditivo

    def __str__(self):
        tipo = ''
        if self.data_inicio:
            tipo += ' de Prazo'
        return '{}º Termo ({})'.format(self.ordem, tipo)

    def save(self, *args, **kwargs):
        if not (self.ordem):
            self.ordem = self.convenio.get_proxima_ordem()
        super(Aditivo, self).save(*args, **kwargs)
        return self


class ConselhoProfissional(models.ModelPlus):
    nome = models.CharFieldPlus('Nome do Conselho', max_length=100)
    sigla = models.CharFieldPlus('Sigla do Conselho', max_length=10)
    ativo = models.BooleanField('Ativo', default=True)

    class Meta:
        verbose_name = 'Conselho Profissional'
        verbose_name_plural = 'Conselhos Profissionais'

    def __str__(self):
        return '{} ({})'.format(self.nome, self.sigla)


class ProfissionalLiberal(models.ModelPlus):
    vinculo_pessoa = models.ForeignKeyPlus(Vinculo, null=True, verbose_name='Pessoa')
    numero_registro = models.CharFieldPlus('Número de Registro no Conselho de Fiscalização Profissional')
    conselho = models.ForeignKeyPlus(ConselhoProfissional)
    telefone = models.CharField('Telefone', null=True, max_length=45)
    email = models.EmailField('E-mail', null=True)
    municipio = models.ForeignKeyPlus('comum.Municipio', verbose_name='Município', null=True, on_delete=models.CASCADE)
    logradouro = models.CharFieldPlus(null=True)
    numero = models.CharField('Nº', max_length=50, null=True)
    complemento = models.CharFieldPlus(null=True)
    bairro = models.CharFieldPlus(null=True)
    cep = models.CharField('CEP', max_length=9, null=True)

    class Meta:
        verbose_name = 'Profissional Liberal'
        verbose_name_plural = 'Profissionais Liberais'

    def __str__(self):
        return self.vinculo_pessoa.pessoa.nome
