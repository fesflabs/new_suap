# -*- coding: utf-8 -*-

import xlwt
from xlwt.Style import colour_map

from datetime import datetime, timedelta

from dateutil.relativedelta import relativedelta
from django.http import HttpResponse

from comum.utils import tl
from djtools.utils import user_has_one_of_perms
from ponto.compensacao import debito_pendente, saldo_restante
from rh.models import Servidor


def pode_ver_frequencia(funcionario, request=None):
    """Testa se o ``current_user`` pode ver as frequências do ``funcionario``"""

    if not request:
        return False
    current_user = request.user
    if not request.user.get_profile().funcionario:
        return False

    funcionario_logado = request.user.get_profile().funcionario

    # superusuário pode tudo
    if current_user.is_superuser:
        return True

    # em qualquer caso a permissão ``pode_ver_frequencia_todos`` pode ver
    if current_user.has_perm('ponto.pode_ver_frequencia_todos'):
        return True

    # verificação própria
    if current_user.get_profile().cpf == funcionario.cpf:
        return user_has_one_of_perms(current_user, ['ponto.pode_ver_frequencia_propria', 'ponto.pode_ver_frequencias_enquanto_foi_chefe', 'ponto.pode_ver_frequencia_campus'])

    # funcionario do campus de funcionario_logado
    if funcionario_logado.eh_do_meu_campus(funcionario):
        return current_user.has_perm('ponto.pode_ver_frequencia_campus')

    else:
        return user_has_one_of_perms(current_user, ['ponto.pode_ver_frequencias_enquanto_foi_chefe'])


def get_datas_segunda_feira_e_sexta_feira_semana_passada():
    hoje = datetime.now() - timedelta(1)

    if hoje.weekday() == 6:  # Considerando que domingo é o primeiro dia da semana
        hoje = hoje - timedelta(days=-1)  # Corrigi a data de hoje para o cálculo ficar correto.

    segunda_feira_semana_passada = hoje - timedelta(7)
    segunda_feira_semana_passada = segunda_feira_semana_passada - timedelta(segunda_feira_semana_passada.weekday())

    sexta_feira_semana_passada = segunda_feira_semana_passada + timedelta(4)

    return segunda_feira_semana_passada, sexta_feira_semana_passada


def get_datas_dia_um_e_ultimo_dia_mes_passado():
    hoje = datetime.now()

    ultimo_dia_mes_passado = datetime(year=hoje.year, month=hoje.month, day=1) - timedelta(1)
    dia_um_mes_passado = datetime(year=ultimo_dia_mes_passado.year, month=ultimo_dia_mes_passado.month, day=1)

    return dia_um_mes_passado, ultimo_dia_mes_passado


def get_data_ultimo_dia_mes_corrente():
    hoje = datetime.now()

    proximo_mes = hoje + relativedelta(months=1)
    ultimo_dia_mes_corrente = datetime(year=proximo_mes.year, month=proximo_mes.month, day=1) - timedelta(1)

    return ultimo_dia_mes_corrente


def get_total_tempo_debito_pendente_semana_anterior():
    """ retorna uma lista com dois valores:
        - o débito restante/pendente em segundos da semana passada
        - o débito restante/pendente em segundos da semana passada que pode ser compensado até o final do mês corrente
    """
    segunda_feira_semana_passada, sexta_feira_semana_passada = get_datas_segunda_feira_e_sexta_feira_semana_passada()
    return debito_pendente(
        servidor=Servidor.objects.get(pk=tl.get_profile().id),
        data_inicial=segunda_feira_semana_passada.date(),
        data_final=sexta_feira_semana_passada.date(),
        data_limite_compensacao=get_data_ultimo_dia_mes_corrente().date(),
    )


def get_total_tempo_debito_pendente_mes_anterior():
    """ retorna uma lista com dois valores:
        - o débito restante/pendente em segundos do mês anterior
        - o débito restante/pendente em segundos do mês anterior que pode ser compensado até o final do mês corrente
    """
    dia_um_mes_passado, ultimo_dia_mes_passado = get_datas_dia_um_e_ultimo_dia_mes_passado()
    return debito_pendente(
        servidor=Servidor.objects.get(pk=tl.get_profile().id),
        data_inicial=dia_um_mes_passado.date(),
        data_final=ultimo_dia_mes_passado.date(),
        data_limite_compensacao=get_data_ultimo_dia_mes_corrente().date(),
    )


def get_total_tempo_debito_pendente_mes_corrente():
    """ retorna o débito restante/pendente em segundos do mês corrente """
    hoje = datetime.now()
    dia_um_mes_atual = datetime(hoje.year, hoje.month, 1)
    ultimo_dia_mes_atual = get_data_ultimo_dia_mes_corrente()
    return debito_pendente(servidor=Servidor.objects.get(pk=tl.get_profile().id), data_inicial=dia_um_mes_atual.date(), data_final=ultimo_dia_mes_atual.date())[0]


def get_total_tempo_saldo_restante_mes_corrente():
    """ retorna o saldo restante em segundos do mês corrente """
    hoje = datetime.now()
    dia_um_mes_atual = datetime(hoje.year, hoje.month, 1)
    ultimo_dia_mes_atual = get_data_ultimo_dia_mes_corrente()
    return saldo_restante(servidor=Servidor.objects.get(pk=tl.get_profile().id), data_inicial=dia_um_mes_atual.date(), data_final=ultimo_dia_mes_atual.date())


def get_relatorios_ponto_adaptados_para_relatorios_pit_rit_ponto_docente(relatorios_app_ponto, data_ini, data_fim, so_semanas_inconsistentes=False):
    from pit_rit.utils import PontoDocente

    lista_relatorios_adaptados = []
    for relatorio in relatorios_app_ponto:
        if relatorio['funcionario'].servidor.eh_docente:
            # adapta o relatório de ponto corrente para o relatório de ponto docente
            lista_relatorios_adaptados.append(
                PontoDocente(
                    servidor=relatorio['funcionario'].servidor,
                    data_inicial=data_ini,
                    data_final=data_fim,
                    relatorio_de_ponto=relatorio,
                    so_semanas_inconsistentes=so_semanas_inconsistentes,
                ).get_relatorio_de_ponto_adaptado()
            )
        else:
            # não adapta o relatório
            lista_relatorios_adaptados.append(relatorio)
    return lista_relatorios_adaptados


################################
# valores baseados no retorno da chamda date.weekday
DIA_DA_SEMANA_SEG = 0
DIA_DA_SEMANA_TER = 1
DIA_DA_SEMANA_QUA = 2
DIA_DA_SEMANA_QUI = 3
DIA_DA_SEMANA_SEX = 4
DIA_DA_SEMANA_SAB = 5
DIA_DA_SEMANA_DOM = 6


def is_dia_da_semana(data, dia_da_semana):
    return data.weekday() == dia_da_semana


################################
def is_request_xls(request):
    return request.GET.get('xls') or request.POST.get('xls')


def get_response_xls_registros_frequencias(relatorios, filename=None):
    """
        request: HTTPRequest
        relatorios: List<relatorio_pessoa>
        relatorio_pessoa: saída do método Frequencia.relatorio_ponto_pessoa
    """

    xls_response = None

    filename = filename or f'Relatório de Frequências{f" - {get_nome_funcionario(relatorios[0])}" if len(relatorios) == 1 else ""}'

    xls_response = HttpResponse(content_type='application/ms-excel')
    xls_response['Content-Disposition'] = f'attachment; filename={filename}.xls'

    planilha = xlwt.Workbook(encoding='utf-8')

    style_negrito = XlwtStyleHelper().font_bold().get_style()
    cell_width_min = 3600

    for relatorio in relatorios:
        periodo = get_periodo(relatorio)

        pagina_name = get_nome_funcionario(relatorio)[:30]  # até 31 caracteres (limitação do xlwt)
        pagina = planilha.add_sheet(pagina_name)

        pagina.row(0).write(0, 'Funcionário:', style_negrito)
        pagina.row(0).write(1, get_nome_funcionario(relatorio))
        pagina.row(1).write(0, 'Matrícula:', style_negrito)
        pagina.row(1).write(1, get_matricula_funcionario(relatorio))
        pagina.row(2).write(0, 'Data Início:', style_negrito)
        pagina.row(2).write(1, periodo[0].strftime('%d/%m/%Y') if periodo[0] else '')
        pagina.row(3).write(0, 'Data Fim:', style_negrito)
        pagina.row(3).write(1, periodo[1].strftime('%d/%m/%Y') if periodo[1] else '')

        pagina.row(5).write(0, 'Data', style_negrito)
        pagina.row(5).write(1, 'CH', style_negrito)
        pagina.row(5).write(2, 'Registros', style_negrito)
        pagina.row(5).write(3, 'Duração Bruta', style_negrito)
        pagina.row(5).write(4, 'Duração Válida', style_negrito)
        pagina.row(5).write(5, 'Duração Final', style_negrito)

        pagina.col(0).width = cell_width_min
        pagina.col(1).width = cell_width_min
        pagina.col(2).width = cell_width_min * 2
        pagina.col(3).width = cell_width_min
        pagina.col(4).width = cell_width_min
        pagina.col(5).width = cell_width_min

        row = 6

        for frequencia_dia in relatorio['dias']:
            dia_info = get_detalhes_frequencia_dia(frequencia_dia)

            registro_1 = dia_info.registros[0] if len(dia_info.registros) >= 1 else None

            # data
            pagina.row(row).write(0, dia_info.dia.strftime('%d/%m/%Y'))

            # ch
            pagina.row(row).write(1, f'{dia_info.ch}h')

            # registro 1
            if registro_1:
                pagina.row(row).write(2, f'{registro_1.acao}: {registro_1.horario.strftime("%H:%M:%S")} ({registro_1.maquina} {f": {registro_1.ip}" if registro_1.ip else ""})')
            else:
                pagina.row(row).write(2, '')

            # duração
            duracao_bruta = dia_info.duracao_bruto
            duracao_valida = dia_info.duracao
            duracao_final = dia_info.duracao_computada if dia_info.duracao_computada else duracao_valida
            pagina.row(row).write(3, f'{duracao_bruta}')
            pagina.row(row).write(4, f'{duracao_valida}')
            pagina.row(row).write(5, f'{duracao_final}')

            # registros 2 em diante
            for registro in dia_info.registros[1:]:
                row += 1
                pagina.row(row).write(0, '')
                pagina.row(row).write(1, '')

                pagina.row(row).write(2, f'{registro.acao}: {registro.horario.strftime("%H:%M:%S")} ({registro.maquina} {f": {registro.ip}" if registro.ip else ""})')

                pagina.row(row).write(3, '')
                pagina.row(row).write(4, '')
                pagina.row(row).write(5, '')

            row += 1

    planilha.save(xls_response)

    return xls_response


def get_nome_funcionario(relatorio):
    return relatorio['funcionario'].nome


def get_matricula_funcionario(relatorio):
    try:
        return relatorio['funcionario'].matricula
    except Exception:
        return ''


def get_periodo(relatorio):
    try:
        data_inicio = get_detalhes_frequencia_dia(relatorio['dias'][0])
        data_fim = get_detalhes_frequencia_dia(relatorio['dias'][len(relatorio['dias']) - 1])
        return [data_inicio.dia, data_fim.dia]
    except Exception:
        return [None, None]


def get_detalhes_frequencia_dia(frequencia_dia):
    """
        frequencia_dia: uma "linha" de relatorio.dias
    """

    class DictAsClass:
        def __init__(self, **args):
            for attr in args:
                setattr(self, attr, args[attr])

    return DictAsClass(**{
        'dia': frequencia_dia.get('dia'),
        'ch': frequencia_dia.get('carga_horaria_do_dia_h'),
        'registros': [
            DictAsClass(**{
                'acao': registro.acao,
                'horario': registro.horario,
                'maquina': registro.maquina,
                'ip': registro.ip
            }) for registro in frequencia_dia.get('horarios', [])
        ],
        'duracao_bruto': frequencia_dia.get('duracao_bruto', ''),
        'duracao': frequencia_dia.get('duracao', ''),
        'duracao_computada': frequencia_dia.get('duracao_computada', '')
    })


class XlwtStyleHelper:
    FONT_BOLD = 'font: bold True;'
    COLOR_STR_RED = 'red'
    COLOR_STR_GREEN = 'green'
    COLOR_STR_BLUE = 'blue'

    def __init__(self):
        self.new_rgb_colors_replace_original_colours = ['plum', 'tan', 'gray80', 'coral', 'white']
        self.new_rgb_colors = {}
        self.str_to_parse_collection = []

    def custom(self, str_to_parse):
        self.str_to_parse_collection.append(str_to_parse)
        return self

    def font_bold(self):
        self.str_to_parse_collection.append(self.FONT_BOLD)
        return self

    def cell_background_color_str(self, color_str):
        self.str_to_parse_collection.append(f'pattern: pattern solid, fore_colour {color_str};')
        return self

    def cell_background_color_RGB(self, xlwt_instance, r, g, b):
        # é possível criar (substituir) até 5 cores personalizadas (há uma limitação na paleta de cores no xlwt)
        colour_new = f'{r},{g},{b}'
        if len(self.new_rgb_colors_replace_original_colours):
            if colour_new in self.new_rgb_colors:
                colour_replaced = self.new_rgb_colors[colour_new]
            else:
                colour_replaced = self.new_rgb_colors_replace_original_colours.pop()
                colour_replaced_index = colour_map[colour_replaced]
                xlwt_instance.set_colour_RGB(colour_replaced_index, r, g, b)
                self.new_rgb_colors[colour_new] = colour_replaced
            self.str_to_parse_collection.append(f'pattern: pattern solid, fore_colour {colour_replaced};')
        else:
            raise Exception(f'RGB Color ({colour_new}) não pode ser adicionada. O limite da paleta de cores foi alcançado.')
        return self

    def get_style(self):
        return xlwt.easyxf("".join(self.str_to_parse_collection))
