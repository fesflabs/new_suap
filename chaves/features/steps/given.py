# -*- coding: utf-8 -*-

from behave import given

from comum.models import Predio, Sala
from rh.models import UnidadeOrganizacional, Servidor


@given('Salas e Servidores já existentes')
def step_cadastros_feature_001(context):
    campus_a_suap = UnidadeOrganizacional.objects.get(sigla='A0')
    predio = Predio.objects.get_or_create(nome='Prédio A1', uo=campus_a_suap, ativo=True)[0]
    Sala.objects.get_or_create(nome='Sala A1', ativa=True, predio=predio, agendavel=False, )[0]
    Servidor.objects.filter(matricula='1111111').update(tem_digital_fraca=True)
