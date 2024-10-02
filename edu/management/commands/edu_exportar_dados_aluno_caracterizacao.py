# -*- coding: utf-8 -*-

"""

"""
import os
from django.conf import settings

from ae.models import Caracterizacao
from djtools.management.commands import BaseCommandPlus
from edu.models import Aluno, MatriculaPeriodo
from djtools.templatetags.filters import format_


import csv

DIR_PATH = os.path.join(settings.BASE_DIR, 'edu/dados')
if not os.path.exists(DIR_PATH):
    os.mkdir(DIR_PATH)


def export(data, name, mode='w'):
    file_path = os.path.join(DIR_PATH, f'{name}.csv')

    with open(file_path, mode) as f:
        wr = csv.writer(f, delimiter=';', quotechar='"', quoting=csv.QUOTE_MINIMAL)
        for d in data:
            wr.writerow(d)


def get_alunos(periodo, qtd_campos_caracterizacao):
    result = []
    ano, p = periodo[1].split('.')
    qs_alunos = Aluno.objects.filter(
        curso_campus__diretoria__setor__uo__sigla='CNAT',
        ano_letivo__ano=ano,
        periodo_letivo=p).select_related('caracterizacao', 'curso_campus', 'situacao', 'curso_campus__diretoria__setor')[0:5]

    for aluno in qs_alunos:
        print(aluno)
        dados_aluno = []
        dados_aluno.append(aluno.matricula)
        dados_aluno.append(aluno.forma_ingresso and aluno.forma_ingresso.descricao or '-')
        dados_aluno.append(f'{aluno.curso_campus.codigo} - {aluno.curso_campus.descricao}')
        dados_aluno.append(aluno.curso_campus.diretoria.setor.sigla)
        dados_aluno.append(aluno.situacao.descricao)

        caracterizacao = Caracterizacao.objects.filter(aluno_id=aluno.id).first()
        if caracterizacao:
            for field in caracterizacao._meta.get_fields():
                if hasattr(field, 'attname'):
                    if field.attname != 'id' and field.attname != 'aluno_id':
                        value = getattr(caracterizacao, field.attname)
                        dados_aluno.append(format_(value, False))
        else:
            for i in range(0, qtd_campos_caracterizacao):
                dados_aluno.append('-')

        for i in range(0, periodo[0]):
            dados_aluno.append('-')
            dados_aluno.append('-')

        qs_mp = MatriculaPeriodo.objects.filter(aluno_id=aluno.id, ano_letivo__ano__lte=2021).order_by('ano_letivo__ano', 'periodo_letivo')
        if p == 1:
            qs_mp = qs_mp.filter(ano_letivo__ano__gte=ano)
        else:
            qs_mp = qs_mp.filter(ano_letivo__ano__gt=ano) | qs_mp.filter(ano_letivo__ano=ano, periodo_letivo=2)
        for mp in qs_mp:
            if mp.ano_letivo.ano == ano and mp.periodo_letivo == 1 and p == 2:
                continue
            dados_aluno.append(format_(mp.get_ira()))
            dados_aluno.append(f'{format_(mp.get_percentual_carga_horaria_frequentada())}%')

        result.append(dados_aluno)
    return result


class Command(BaseCommandPlus):

    def handle(self, *args, **options):
        PERIODOS = [
            [0, '2015.1'],
            [1, '2015.2'],
            [2, '2016.1'],
            [3, '2016.2'],
            [4, '2017.1'],
            [5, '2017.2'],
            [6, '2018.1'],
            [7, '2018.2'],
            [8, '2019.1'],
            [9, '2019.2'],
            [10, '2020.1'],
            [11, '2020.2'],
            [12, '2021.1'],
            [13, '2021.2']
        ]

        dados = []

        cabecalho = ['Matrícula', 'Forma de Ingresso', 'Curso', 'Diretoria', 'Situação']
        caracterizacao = Caracterizacao.objects.first()
        qtd_campos_caracterizacao = 0
        for field in caracterizacao._meta.get_fields():
            if hasattr(field, 'verbose_name'):
                if field.attname != 'id' and field.attname != 'aluno_id':
                    qtd_campos_caracterizacao += 1
                    cabecalho.append(field.verbose_name)
        for periodo in PERIODOS:
            cabecalho.append(f'IRA {periodo[1]}')
            cabecalho.append(f'Frequência {periodo[1]}')
        dados.append(cabecalho)

        for periodo in PERIODOS:
            print(periodo)
            dados.extend(get_alunos(periodo, qtd_campos_caracterizacao))

        export(dados, 'alunos')

        print(f'File saved at {DIR_PATH}/!')
