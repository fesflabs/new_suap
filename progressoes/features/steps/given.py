# -*- coding: utf-8 -*-


from behave import given

from rh.models import ServidorSetorHistorico, Servidor, Setor, PadraoVencimento
import datetime


@given('os cadastros básicos de progressões')
def step_impl(context):
    context.execute_steps(
        """
        Dado os seguintes usuários
        | Nome                              | Matrícula            | Setor | Lotação | Email                                | CPF             | Senha   | Grupo                                               |
        | Coordenador de Gestão de Pessoas  | CoordGesPessoas      | A0    | A0      | coordgespessoas@ifrn.edu.br          | 077.255.187-34      | abcd    | Coordenador de Gestão de Pessoas                    |
    """
    )
    servidor = Servidor.objects.get(matricula='1111111')
    data = datetime.datetime(2019, 2, 8).date()
    setor = Setor.objects.get(sigla='A1')
    ServidorSetorHistorico.objects.create(servidor=servidor, setor=setor, data_inicio_no_setor=data)
    PadraoVencimento.objects.get_or_create(categoria=PadraoVencimento.CATEGORIA_TECNICO_ADMINISTRATIVO, classe='E',
                                           posicao_vertical='01')
    PadraoVencimento.objects.get_or_create(categoria=PadraoVencimento.CATEGORIA_TECNICO_ADMINISTRATIVO, classe='E',
                                           posicao_vertical='02')
