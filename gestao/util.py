# -*- coding: utf-8 -*-

import datetime
from decimal import Decimal

from rh.models import UnidadeOrganizacional

'''
def get_periodo_referencia_sistema_simulacao():
    from gestao.models import PeriodoReferencia
    periodo_referencia = PeriodoReferencia()
    periodo_referencia.ano = 2016
    periodo_referencia.data_base = datetime.date(periodo_referencia.ano, 1, 1)
    periodo_referencia.data_limite = datetime.date(periodo_referencia.ano, 12, 31)
    return periodo_referencia
'''


def get_proxima_data(data, dia_da_semana=6):
    '''
    @data: datetime
    @weekday: dia da seman, sendo de 0 (Segunda) até 6 (Domingo)
    '''
    t = datetime.timedelta((7 + dia_da_semana - data.weekday()) % 7)
    return data + t


def get_cache_expira():
    '''
    Cache expira sempre no domingo as 00:00
    :return: retorna em segundos o tempo para o cache expirar
    '''
    dtinicio = datetime.datetime.now()
    dtfim = get_proxima_data(dtinicio)
    dtfim = datetime.datetime(dtfim.year, dtfim.month, dtfim.day)
    return (dtfim - dtinicio).total_seconds()


class TabelaBidimensional:

    "Tabela utilizada pela view detalhar_variavel para exibir os dados de alunos em função do campus e do nível de ensino"

    def __init__(self, qs_matriculas1=None, qs_alunos=None, uo=None):
        from edu.models import Modalidade, Diretoria

        colunas = []
        colunas.append('CAMPUS')
        for modalidade in Modalidade.objects.all():
            colunas.append(modalidade.descricao)
        colunas.append('TOTAL')
        uos_campus_ids = Diretoria.objects.values('setor__uo').distinct()
        uos_campus = UnidadeOrganizacional.objects.suap().filter(pk__in=uos_campus_ids)

        registros = []
        registro_final = dict()
        registro_final[0] = 'TOTAL'
        n = Modalidade.objects.count()
        total_final = 0
        for i in range(1, n + 1):
            registro_final[i] = 0
        for uo_campus in uos_campus:
            registro = dict()
            total = 0
            registro[0] = uo_campus.sigla
            i = 1
            for modalidade in Modalidade.objects.all():
                subtotal = 0
                if qs_matriculas1 is not None:
                    subtotal += qs_matriculas1.filter(aluno__curso_campus__diretoria__setor__uo__id=uo_campus.id, aluno__curso_campus__modalidade__id=modalidade.id).count()
                if qs_alunos is not None:
                    subtotal += qs_alunos.filter(curso_campus__diretoria__setor__uo__id=uo_campus.id, curso_campus__modalidade__id=modalidade.id).count()

                registro[i] = subtotal
                registro_final[i] += subtotal
                total += subtotal
                i += 1
            total_final += total
            registro[i] = total

            if not uo:
                registros.append(registro)
        registro_final[int(n + 1)] = total_final
        registros.append(registro_final)

        self.colunas = colunas
        self.registros = registros


class VariavelDiff:
    @staticmethod
    def calcular(arquivo_siafi, dados_suap, only_diff=True):
        import csv

        arquivo_siafi = csv.reader(arquivo_siafi, delimiter=';')
        siafi = dict()
        for row in arquivo_siafi:
            if row[1].strip():
                ug_executora = row[0]
            if ug_executora not in siafi:
                siafi[ug_executora] = dict()
                if row[1].strip():
                    nome = row[1]
                siafi[ug_executora]['nome'] = nome
                siafi[ug_executora]['valores'] = dict()
            natureza = row[2]
            valor = Decimal(row[3].replace('.', '').replace(',', '.'))
            if natureza in siafi[ug_executora]['valores']:
                siafi[ug_executora]['valores'][natureza] += valor
            else:
                siafi[ug_executora]['valores'][natureza] = valor

        suap = dict()
        for row in dados_suap:
            ug_executora = row[0]
            if ug_executora not in suap:
                suap[ug_executora] = dict()
                if row[1].strip():
                    nome = row[1]
                suap[ug_executora]['nome'] = nome
                suap[ug_executora]['valores'] = dict()
            natureza = row[2]
            valor = row[3]
            if not isinstance(row[3], Decimal):
                valor = Decimal(valor.replace('.', '').replace(',', '.'))
            if natureza in suap[ug_executora]['valores']:
                suap[ug_executora]['valores'][natureza] += valor
            else:
                suap[ug_executora]['valores'][natureza] = valor

        rows = []
        rows.append(['UG Executora', 'Nome', 'Natureza', 'SUAP', 'SIAFI', 'DIFF'])
        keys = list(suap.keys()) + list(siafi.keys())
        keys.sort()
        keys = sorted(set(keys))
        for ug_executora in keys:
            try:
                keys = list()
                if ug_executora in siafi:
                    keys += list(siafi[ug_executora]['valores'].keys())
                    if siafi[ug_executora]['nome'].strip():
                        nome = siafi[ug_executora]['nome']
                if ug_executora in suap:
                    keys += list(suap[ug_executora]['valores'].keys())
                    if suap[ug_executora]['nome'].strip():
                        nome = suap[ug_executora]['nome']

                keys.sort()
                keys = sorted(set(keys))

                for natureza in keys:
                    try:
                        valor_siafi = Decimal(0)
                        if ug_executora in siafi and natureza in siafi[ug_executora]['valores']:
                            valor_siafi = siafi[ug_executora]['valores'].pop(natureza)

                        valor_suap = Decimal(0)
                        if ug_executora in suap and natureza in suap[ug_executora]['valores']:
                            valor_suap = suap[ug_executora]['valores'].pop(natureza)

                        if only_diff:
                            if valor_suap != valor_siafi:
                                rows.append([ug_executora, nome, natureza, valor_suap, valor_siafi, valor_siafi - valor_suap])
                        else:
                            rows.append([ug_executora, nome, natureza, valor_suap, valor_siafi, valor_siafi - valor_suap])

                    except Exception:
                        pass

            except Exception:
                pass
        return rows
