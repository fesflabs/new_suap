# -*- coding: utf-8 -*-

from djtools.db import models
from edu.models.logs import LogModel


class Credenciamento(LogModel):

    SEARCH_FIELDS = ['nome']
    CREDECIAMENTO = 1
    RECREDECIAMENTO = 2
    RENOVACAO_RECREDECIAMENTO = 3

    TIPO_CHOICES = [
        [CREDECIAMENTO, 'Credenciamento'],
        [RECREDECIAMENTO, 'Recredenciamento'],
        [RENOVACAO_RECREDECIAMENTO, 'Renovação de Recredenciamento'],
    ]

    tipo = models.PositiveIntegerFieldPlus(verbose_name='Tipo', choices=TIPO_CHOICES)
    tipo_ato = models.CharFieldPlus(verbose_name='Tipo', choices=[['Parecer', 'Parecer'], ['Resolução', 'Resolução'], ['Decreto', 'Decreto'], ['Portaria', 'Portaria'], ['Lei Federal', 'Lei Federal'], ['Lei Estadual', 'Lei Estadual'], ['Lei Municipal', 'Lei Municipal'], ['Ato Próprio', 'Ato Próprio']])
    numero_ato = models.CharFieldPlus(verbose_name='Número')
    data_ato = models.DateFieldPlus(verbose_name='Data')

    numero_publicacao = models.CharFieldPlus(verbose_name='Número da Publicação')
    data_publicacao = models.DateFieldPlus(verbose_name='Data da Publicação')
    veiculo_publicacao = models.CharFieldPlus(verbose_name='Veículo da Publicação', choices=[['DOU', 'DOU']])
    secao_publicacao = models.CharFieldPlus(verbose_name='Seção da Publicação')
    pagina_publicacao = models.CharFieldPlus(verbose_name='Página da Publicação')

    class Meta:
        verbose_name = 'Credenciamento'
        verbose_name_plural = 'Credenciamentos'

    def __str__(self):
        return '{} - {}'.format(self.tipo_ato, self.numero_ato)
