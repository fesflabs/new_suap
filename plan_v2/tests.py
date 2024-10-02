# -*- coding: utf-8 -*-
from django.apps import apps
from comum.tests import SuapTestCase

"""
Perfis da APP:
    - Administrador de Planejamento Institucional
    - Coordenador de Planejamento Institucional Sistêmico
    - Coordenador de Planejamento Institucional

Cadastro do PDI:
    - Cadastro das unidades administrativas
    - Associação dos macroprocessos
    - Adição dos objetivos estratégicos
    - Associação das ações

Cadastro do Plano de Ação:
    * Sistêmico
        - Adicionar origem de recurso
        - Rateamento das origens de recurso
        - Vincular natureza de despesa
        - Importar Objetivo Estratégicos
        - Validação
    * Unidade Administrativas
        - Adicionar ação
        - Definir responsável
        - Cadastrar atividades

Etapas do Plano de Ação:
    - Cadastro Sistêmico
    - Cadastro do Campus
    - Validação do Plano

------------------------------------------------------------------------------------------------------------------------

Usuários:
    * Administrador de Planejamento Institucional
        - servidor_a
    * Coordenador de Planejamento Institucional Sistêmico
        - servidor_c
    * Coordenador de Planejamento Institucional
        - servidor_d

Unidade Administrativas:
    * Campus A - campus_a_suap
        - servidor_a
        - servidor_c
    * Campus B - campus_b_suap
        - servidor_b
        - servidor_d
"""

# Importa os modelos usados no teste
Eixo = apps.get_model('plan_v2', 'Eixo')


# Grupos de acesso ao módulo
GRUPO_ADMINISTRADOR = 'Administrador de Planejamento Institucional'
GRUPO_COORDENADOR_SISTEMICO = 'Coordenador de Planejamento Institucional Sistêmico'
GRUPO_COORDENADOR_CAMPUS = 'Coordenador de Planejamento Institucional'


class PlanV2TestCase(SuapTestCase):

    first_time = True

    def _pre_setup(self):
        if PlanV2TestCase.first_time:
            self.carga_inicial()
        super(PlanV2TestCase, self)._pre_setup()

    def carga_inicial(self):
        self.definir_variaveis_de_instancia()

        eixo_1 = Eixo(nome='Eixo 1')
        eixo_1.save()
        eixo_2 = Eixo(nome='Eixo 2')
        eixo_2.save()

        PlanV2TestCase.first_time = False
