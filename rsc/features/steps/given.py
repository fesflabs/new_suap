# -*- coding: utf-8 -*-

from rsc.models import Diretriz, TipoRsc, Unidade, CategoriaMemorialDescritivo
from behave import given  # noqa


@given('os dados básicos para RSC')
def step_cadastros(context):
    TipoRsc.objects.get_or_create(nome='RSC', categoria='docente')
    rsc_tipo = TipoRsc.objects.get(nome='RSC')

    Diretriz.objects.get_or_create(tipo_rsc=rsc_tipo, nome='direcao', descricao='prova', peso=2, teto=10)

    Unidade.objects.get_or_create(nome='prova', sigla='lv')

    CategoriaMemorialDescritivo.get_or_create(nome="pesquisa e atividades")
