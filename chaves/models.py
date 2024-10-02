# -*- coding: utf-8 -*-
from datetime import datetime

from comum.models import Sala
from djtools.db import models
from rh.models import Pessoa


class Chave(models.ModelPlus):
    """
    A restrição de unicidade "identificacao" X "sala__predio__uo" é assegurada
    pelo form de adição de chaves, visto que o Django não dá suporte a definir
    colunas de outras tabelas no "unique_together"
    """

    SEARCH_FIELDS = ['identificacao', 'sala__nome', 'sala__predio__nome', 'sala__predio__uo__nome', 'sala__predio__uo__sigla']
    identificacao = models.CharField('Identificação', max_length=50)
    sala = models.ForeignKeyPlus(Sala, verbose_name='Sala', null=False, on_delete=models.CASCADE)
    ativa = models.BooleanField(default=True)
    pessoas = models.ManyToManyField(Pessoa, blank=True, verbose_name='Pessoas Permitidas')
    disponivel = models.BooleanField(default=True, editable=False, verbose_name='Disponível')

    class Meta:
        verbose_name = 'Chave'
        verbose_name_plural = 'Chaves'
        ordering = ['sala__predio__uo', 'sala__nome', 'identificacao']
        permissions = (("poder_ver_todas", "Pode ver todas as chaves"), ("poder_ver_do_campus", "Pode ver as chaves do campus"))

    def __str__(self):
        return "{} ({})".format(self.identificacao, self.sala)

    def pessoa_permitida(self, pessoa):
        return self.pessoas.filter(pk=pessoa.pk).exists()

    def _efetuar_emprestimo(self, pessoa, operador, observacao):
        Movimentacao.objects.create(chave=self, pessoa_emprestimo=pessoa, operador_emprestimo=operador, observacao_emprestimo=observacao)
        self.disponivel = False
        self.save()

    def _efetuar_devolucao(self, pessoa, operador, observacao):
        movimentacao_pendente = Movimentacao.objects.get(chave=self, data_devolucao=None)
        movimentacao_pendente.data_devolucao = datetime.now()
        movimentacao_pendente.pessoa_devolucao = pessoa
        movimentacao_pendente.operador_devolucao = operador
        movimentacao_pendente.observacao_devolucao = observacao
        movimentacao_pendente.save()
        self.disponivel = True
        self.save()


class Movimentacao(models.ModelPlus):
    chave = models.ForeignKeyPlus(Chave, on_delete=models.CASCADE)
    # Dados do empréstimo
    data_emprestimo = models.DateTimeField(verbose_name='Data do Empréstimo')
    operador_emprestimo = models.ForeignKeyPlus(
        Pessoa, verbose_name='Operador Empréstimo', on_delete=models.CASCADE, related_name='chaves_movimentadas_emprestimo_como_operador_set', null=True, blank=True
    )
    pessoa_emprestimo = models.ForeignKeyPlus(Pessoa, verbose_name='Pessoa Empréstimo', on_delete=models.CASCADE, related_name='chaves_movimentadas_emprestimo_set')
    observacao_emprestimo = models.TextField(null=True, verbose_name='Observação Empréstimo', blank=True)
    # Dados da devolução
    data_devolucao = models.DateTimeField(null=True, verbose_name='Data da Devolução', blank=True)
    operador_devolucao = models.ForeignKeyPlus(
        Pessoa, verbose_name='Operador Devolução', on_delete=models.CASCADE, related_name='chaves_movimentadas_devolucao_como_operador_set', blank=True, null=True
    )
    pessoa_devolucao = models.ForeignKeyPlus(
        Pessoa, verbose_name='Pessoa Devolução', on_delete=models.CASCADE, related_name='chaves_movimentadas_devolucao_set', null=True, blank=True
    )
    observacao_devolucao = models.TextField(null=True, blank=True, verbose_name='Observação Devolução')

    class Meta:
        verbose_name = 'Movimentação'
        verbose_name_plural = 'Movimentações'
        unique_together = (('chave', 'data_emprestimo'), ('chave', 'data_devolucao'))
