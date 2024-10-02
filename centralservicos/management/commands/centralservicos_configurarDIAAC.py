# -*- coding: utf-8 -*-

import os
import sys

import xlrd
from django.conf import settings
from django.contrib.auth.models import Group
from django.db import transaction

from centralservicos.models import GrupoAtendimento, CentroAtendimento, CategoriaServico
from comum.models import User, AreaAtuacao
from djtools.management.commands import BaseCommandPlus
from rh.models import UnidadeOrganizacional, Setor

"""
python manage.py centralservicos_configurarDIAAC
"""


class Command(BaseCommandPlus):

    # def add_arguments(self, parser):
    # parser.add_argument('file_path', nargs='+', type=str)

    @transaction.atomic
    def configura_cadastros(self):
        if not AreaAtuacao.objects.filter(nome='Ensino').exists():
            area_ensino = AreaAtuacao()
            area_ensino.nome = 'Ensino'
            area_ensino.save()

            novo_centro_atendimento = CentroAtendimento()
            novo_centro_atendimento.nome = 'Campus'
            novo_centro_atendimento.area = area_ensino
            novo_centro_atendimento.eh_local = True
            novo_centro_atendimento.save()

            try:
                centro_atendimento = CentroAtendimento.objects.get(pk=5)
                centro_atendimento.nome = 'DIAAC'
                centro_atendimento.area = area_ensino
                centro_atendimento.save()
            except Exception:
                print(("Unexpected error:", sys.exc_info()[0]))

            categoria = CategoriaServico()
            categoria.nome = 'Secretaria Acadêmica'
            categoria.area = area_ensino
            categoria.save()

            """
            #Alterando o grupo de Servico SUAP-EDU para a categoria Secretaria Academica
            gruposervico = GrupoServico.objects.get(pk=30)
            gruposervico.categorias.clear()
            gruposervico.categorias.add(categoria)

            servicos = Servico.objects.filter(grupo_servico = gruposervico)
            for servico in servicos:
                bases = BaseConhecimento.objects.filter(servicos__in=[servico,]).distinct()
                for base in bases:
                    base_nova = base
                    base_nova.pk = None
                    base_nova.area = area_ensino
                    base_nova.grupos_atendimento.clear()

            Para cada servico do gruposervico SUAP-EDU (pk=30)
                Copie as Bases de Conhecimento utilizada
                    Clone esta base de conhecimento
                    Remova todos os Grupos de Atendimento
                    Remova todos os serviços (adicione apenas o serviço atual)
                    Atribua ao Serviço
                    Remova a BC antiga do Serviço
                    Pegue a Base antiga e remova Grupos de Servicos e Grupo de Atendimento que não seja da área de TI
            """

    def handle(self, *args, **options):
        self.configura_cadastros()
        file_path = 'centralservicos/fixtures/ConfiguracaoDIAAC.xlsx'
        file_path = os.path.join(settings.BASE_DIR, file_path)
        print(file_path)

        with open(file_path, 'r') as f:
            content = f.read()
        workbook = xlrd.open_workbook(file_contents=content)
        sheet = workbook.sheet_by_index(1)

        try:
            for i in range(2, sheet.nrows):  # Iniciando na 3a Linha
                nome = sheet.cell_value(i, 0)
                campus = sheet.cell_value(i, 1)
                uo = UnidadeOrganizacional.objects.suap().get(sigla=campus)
                centro_id = int(sheet.cell_value(i, 2))
                centro_atendimento = CentroAtendimento.objects.get(pk=centro_id)
                grupo_superior = sheet.cell_value(i, 4)
                print(('Processando {} - {}'.format(nome, centro_atendimento)))

                if GrupoAtendimento.objects.filter(nome=nome, centro_atendimento=centro_atendimento).exists():
                    print('Grupo de Atendimento já existe. Não será processado.')
                else:
                    if grupo_superior:
                        grupo_superior = GrupoAtendimento.objects.get(nome=grupo_superior)
                    else:
                        grupo_superior = None

                    matricula_responsaveis = sheet.cell_value(i, 5)
                    if matricula_responsaveis:
                        responsaveis = User.objects.filter(username__in=matricula_responsaveis.split(';'))
                    else:
                        setor = Setor.objects.get(sigla=nome)
                        responsaveis = setor.chefes.values_list('pessoafisica_ptr__user__pk', flat=True)

                    if responsaveis:
                        print(('Responsaveis {}'.format(responsaveis)))
                        obj = GrupoAtendimento.objects.create(nome=nome, campus=uo, centro_atendimento=centro_atendimento, grupo_atendimento_superior=grupo_superior)
                        obj.responsaveis.set(responsaveis)
                        # obj.atendentes.set(responsaveis)

                        group = Group.objects.get(name='Atendente da Central de Serviços')
                        """ Para todos os atendentes vinculados ao GrupoAtendimento, que não possuam a permissão """
                        atendentes_sem_permissao = User.objects.filter(atendentes_set__isnull=False).exclude(groups=group)
                        for user in atendentes_sem_permissao:
                            user.groups.add(group)
                    else:
                        print('Grupo de Atendimento não importado. Responsáveis não localizados.')

        except Exception:
            print(("Unexpected error:", sys.exc_info()[0]))
            raise
