# -*- coding: utf-8 -*-

import datetime
from copy import deepcopy
from dateutil.relativedelta import relativedelta
from comum.utils import datas_entre, formata_segundos
from collections import OrderedDict
from ponto.enums import TipoLiberacao
from ponto.models import Frequencia, AbonoChefia, HorarioCompensacao, RecessoOpcaoEscolhida, RecessoOpcao, RecessoPeriodoCompensacao, Afastamento
from django.conf import settings
from comum.models import Configuracao
from djtools.db.models import Q


def get_relatorio_de_ponto(servidor, data_inicial, data_final):
    #
    # relatorio_de_ponto['dias'] ---> [
    #   {'dia': ? (date), 'carga_horaria_do_dia': ? (int q indica horas), ... },
    #   {'dia': ? (date), 'carga_horaria_do_dia': ? (int q indica horas), ... },
    #   {'dia': ? (date), 'carga_horaria_do_dia': ? (int q indica horas), ... },
    #   ...
    # ]
    return Frequencia.relatorio_ponto_pessoa(
        servidor.get_vinculo(),
        data_ini=data_inicial,
        data_fim=data_final,
        sabado=False,
        domingo=False,
        show_grafico=False,
        so_inconsistentes=False,
        trata_compensacoes=False,
        trata_inconsistencias=False,
    )


def get_compensacoes_informadas(servidor, data_inicial, data_final):
    return (
        HorarioCompensacao.objects.filter(funcionario=servidor, data_compensacao__gte=data_inicial, data_compensacao__lte=data_final, situacao=HorarioCompensacao.SITUACAO_VALIDO)
        | HorarioCompensacao.objects.filter(funcionario=servidor, data_aplicacao__gte=data_inicial, data_aplicacao__lte=data_final, situacao=HorarioCompensacao.SITUACAO_VALIDO)
    ).distinct()


def get_acompanhamentos(servidor, data_inicial, data_final):
    return (
        RecessoOpcaoEscolhida.objects.filter(
            funcionario=servidor, validacao=RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO, dias_escolhidos__dia__data__gte=data_inicial, dias_escolhidos__dia__data__lte=data_final
        )
        | RecessoOpcaoEscolhida.objects.filter(
            funcionario=servidor,
            validacao=RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO,
            recesso_opcao__periodos_de_compensacao__data_inicial__lte=data_inicial,
            recesso_opcao__periodos_de_compensacao__data_final__gte=data_inicial,
        )
        | RecessoOpcaoEscolhida.objects.filter(
            funcionario=servidor,
            validacao=RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO,
            recesso_opcao__periodos_de_compensacao__data_inicial__lte=data_final,
            recesso_opcao__periodos_de_compensacao__data_final__gte=data_final,
        )
    ).distinct()


def get_datas_entre(data_inicial, data_final):
    return datas_entre(data_inicial, data_final)


def get_periodos_de_dias_a_atualizar(dias_agendados, dias_atualizados):
    """
        agendados         x   x  x               x    x          x
        atualizados          |----------------------------|

    """
    data_zero = datetime.date(1900, 1, 1)

    dia_atualizado_min = data_zero
    dia_atualizado_max = data_zero
    if dias_atualizados:
        dia_atualizado_min = min(dias_atualizados)
        dia_atualizado_max = max(dias_atualizados)

    dia_agendado_min = data_zero
    dia_agendado_max = data_zero
    if dias_agendados:
        dia_agendado_min = min(dias_agendados)
        dia_agendado_max = max(dias_agendados)

    periodo_um = []
    if dia_agendado_min < dia_atualizado_min:
        periodo_um = [dia_agendado_min, dia_atualizado_min - datetime.timedelta(1)]

    periodo_dois = []
    if dia_agendado_max > dia_atualizado_max:
        periodo_dois = [dia_atualizado_max + datetime.timedelta(1), dia_agendado_max]

    if periodo_um and (periodo_um[0] == data_zero or periodo_um[1] == data_zero):
        periodo_um = []

    if periodo_dois and (periodo_dois[0] == data_zero or periodo_dois[1] == data_zero):
        periodo_dois = []

    return [periodo_um, periodo_dois]


def formatar_segundos(segundos=0, add_sufixos_h_min_seg=False, omite_se_zero=False):
    if add_sufixos_h_min_seg:
        return '{}'.format(formata_segundos(segundos, '{h}h ', '{m}min ', '{s}seg', omite_se_zero))
    return '{}'.format(formata_segundos(segundos, '{h:02.0f}:', '{m:02.0f}:', '{s:02.0f}', omite_se_zero))


def get_periodos(dias, formatar=False):
    dias = sorted(dias)
    periodos = []
    dia_inicial = None
    dia_anterior = None
    for dia in dias:
        if dia_inicial is None:
            dia_inicial = dia
        if dia_anterior:
            if not dia - datetime.timedelta(1) == dia_anterior:
                periodos.append([dia_inicial, dia_anterior])
                dia_inicial = dia
        dia_anterior = dia
    if dia_inicial and dia_anterior:
        periodos.append([dia_inicial, dia_anterior])

    if formatar:
        periodos_formatado = []
        for periodo in periodos:
            if periodo[0] == periodo[1]:
                periodos_formatado.append('{}'.format(periodo[0].strftime('%d/%m/%Y')))
            else:
                periodos_formatado.append('{} a {}'.format(periodo[0].strftime('%d/%m/%Y'), periodo[1].strftime('%d/%m/%Y')))
        return ', '.join(periodos_formatado)
    return periodos


class Contexto(object):
    """
        situação do ponto de um servidor em um período
    """

    def __init__(self, servidor, periodo_data_inicial, periodo_data_final, relatorio_de_ponto=None):

        self.servidor = servidor
        assert self.servidor is not None

        assert periodo_data_inicial is not None
        assert periodo_data_final is not None

        # tabela contendo os dias e suas respectivas situações (instâncias de SituacaoDia)
        self.situacao = OrderedDict()

        # se adianta visando menos consultas simples (de uma data) no futuro
        # engloba "um mês atrás e um mês na frente" conforme regra do mês seguinte
        periodo_data_inicial_plus = datetime.date(year=(periodo_data_inicial - relativedelta(months=1)).year, month=(periodo_data_inicial - relativedelta(months=1)).month, day=1)
        periodo_data_final_plus = datetime.date(
            year=(periodo_data_final + relativedelta(months=2)).year, month=(periodo_data_final + relativedelta(months=2)).month, day=1
        ) - datetime.timedelta(1)

        # dados "anexos" ao contexto (são os dados necessários para fazer TODOS os cálculos)
        # após instanciação, esses dados são atualizados conforme os dias vão sendo adicionados

        #########
        if relatorio_de_ponto:
            self.relatorio_de_ponto = {'dias': deepcopy(relatorio_de_ponto['dias'])}

            dias_ponto = [ponto['dia'] for ponto in self.relatorio_de_ponto['dias']]

            self.relatorio_de_ponto_dias_atualizados = []
            self.relatorio_de_ponto_dias_agendados_para_atualizacao = []

            if dias_ponto:
                self.relatorio_de_ponto_dias_atualizados = get_datas_entre(min(dias_ponto), max(dias_ponto))
                # o relatório de ponto está dentro do período informado?
                self.relatorio_de_ponto_dias_agendados_para_atualizacao = get_datas_entre(periodo_data_inicial_plus, periodo_data_final_plus)
        else:
            self.relatorio_de_ponto = get_relatorio_de_ponto(servidor, periodo_data_inicial_plus, periodo_data_final_plus)

            self.relatorio_de_ponto_dias_atualizados = get_datas_entre(periodo_data_inicial_plus, periodo_data_final_plus)
            self.relatorio_de_ponto_dias_agendados_para_atualizacao = []

        #########
        self.compensacoes_informadas = get_compensacoes_informadas(servidor, periodo_data_inicial_plus, periodo_data_final_plus)

        self.compensacoes_informadas_dias_atualizados = get_datas_entre(periodo_data_inicial_plus, periodo_data_final_plus)
        self.compensacoes_informadas_dias_agendados_para_atualizacao = []

        #########
        self.acompanhamentos_envolvidos = get_acompanhamentos(servidor, periodo_data_inicial_plus, periodo_data_final_plus)
        self.acompanhamentos_envolvidos_dias_atualizados = get_datas_entre(periodo_data_inicial_plus, periodo_data_final_plus)
        self.acompanhamentos_envolvidos_dias_agendados_para_atualizacao = []
        self.acompanhamentos_envolvidos_dias_efetivos_a_compensar = {}  # {id_acompanhamento: dias_efetivos}

        # adiciona os dias no contexto atual
        for dia in get_datas_entre(periodo_data_inicial_plus, periodo_data_final_plus):
            self.add_dia(dia)

        # guarda o período INICIALMENTE informado (escopo dos totais e outras informações)
        self.periodo_inicial = [periodo_data_inicial, periodo_data_final]

        # ponto docente ativado?
        self.ponto_docente_ativado = 'pit_rit' in settings.INSTALLED_APPS and Configuracao.get_valor_por_chave('pit_rit', 'ponto_docente_ativado') == 'True'

        # histórico de função do servidor no período
        self.historico_funcao = self.servidor.historico_funcao(periodo_data_inicial, periodo_data_final)

        # datas início e fim de exercício na instituição
        self.data_inicio_exercicio_na_instituicao = self.servidor.data_inicio_exercicio_na_instituicao
        self.data_fim_servico_na_instituicao = self.servidor.data_fim_servico_na_instituicao

        # datas início e fim para fins de compensação
        self.data_inicio_a_cobrar_compensacao = self.data_inicio_exercicio_na_instituicao  # padrão
        self.data_fim_a_cobrar_compensacao = self.data_fim_servico_na_instituicao

        # chamado 75933: cobrar compensação a partir da data em que havia cadastro em algum setor
        # procura a data mais antiga em que o servidor estava cadastrado em um setor (data inicial no primeiro setor)
        # código baseado em "ponto.views.frequencia_funcionario_get_escopo_relatorio_ponto_pessoa"
        # no contexto desse método de referência, essa informação é calculada conforme variável
        # "dias_em_que_estava_no_campus"
        dias_iniciais_em_setores = []
        for setor in self.servidor.historico_setor_suap(self.data_inicio_exercicio_na_instituicao, None):
            dias_iniciais_em_setores.append(setor.data_inicio_no_setor)
        if dias_iniciais_em_setores:
            self.data_inicio_a_cobrar_compensacao = min(dias_iniciais_em_setores)

        # confirmando os dados "anexos"
        # deixar essas 3 chamadas no final do __init__
        self.update_relatorio_de_ponto()
        self.update_compensacoes_informadas()
        self.update_acompanhamentos_envolvidos()

    # -------------------------------------------------------------------------------------------------------

    def update_relatorio_de_ponto(self):
        for periodo in get_periodos_de_dias_a_atualizar(self.relatorio_de_ponto_dias_agendados_para_atualizacao, self.relatorio_de_ponto_dias_atualizados):
            if periodo and periodo[0] and periodo[1]:
                relatorio_de_ponto_dias_agendados_para_atualizacao_final = get_datas_entre(periodo[0], periodo[1])

                if relatorio_de_ponto_dias_agendados_para_atualizacao_final:
                    relatorio_ponto_atualizacao = get_relatorio_de_ponto(
                        self.servidor, min(set(relatorio_de_ponto_dias_agendados_para_atualizacao_final)), max(set(relatorio_de_ponto_dias_agendados_para_atualizacao_final))
                    )

                    if self.relatorio_de_ponto:
                        self.relatorio_de_ponto['dias'] += relatorio_ponto_atualizacao['dias']
                    else:
                        self.relatorio_de_ponto = relatorio_ponto_atualizacao

                    self.relatorio_de_ponto_dias_atualizados += relatorio_de_ponto_dias_agendados_para_atualizacao_final

        self.relatorio_de_ponto_dias_agendados_para_atualizacao = []

    def update_compensacoes_informadas(self):
        for periodo in get_periodos_de_dias_a_atualizar(self.compensacoes_informadas_dias_agendados_para_atualizacao, self.compensacoes_informadas_dias_atualizados):
            if periodo and periodo[0] and periodo[1]:
                compensacoes_informadas_dias_agendados_para_atualizacao_final = get_datas_entre(periodo[0], periodo[1])

                if compensacoes_informadas_dias_agendados_para_atualizacao_final:
                    self.compensacoes_informadas = self.compensacoes_informadas | get_compensacoes_informadas(
                        self.servidor,
                        min(set(compensacoes_informadas_dias_agendados_para_atualizacao_final)),
                        max(set(compensacoes_informadas_dias_agendados_para_atualizacao_final)),
                    )

                    self.compensacoes_informadas_dias_atualizados += compensacoes_informadas_dias_agendados_para_atualizacao_final

        self.compensacoes_informadas_dias_agendados_para_atualizacao = []

    def update_acompanhamentos_envolvidos(self):
        for periodo in get_periodos_de_dias_a_atualizar(self.acompanhamentos_envolvidos_dias_agendados_para_atualizacao, self.acompanhamentos_envolvidos_dias_atualizados):
            if periodo and periodo[0] and periodo[1]:
                acompanhamentos_envolvidos_dias_agendados_para_atualizacao_final = get_datas_entre(periodo[0], periodo[1])

                if acompanhamentos_envolvidos_dias_agendados_para_atualizacao_final:
                    self.acompanhamentos_envolvidos = self.acompanhamentos_envolvidos | get_acompanhamentos(
                        self.servidor,
                        min(set(acompanhamentos_envolvidos_dias_agendados_para_atualizacao_final)),
                        max(set(acompanhamentos_envolvidos_dias_agendados_para_atualizacao_final)),
                    )

                    self.acompanhamentos_envolvidos_dias_atualizados += acompanhamentos_envolvidos_dias_agendados_para_atualizacao_final

        for acompanhamento in self.acompanhamentos_envolvidos:
            if acompanhamento.id not in self.acompanhamentos_envolvidos_dias_efetivos_a_compensar:
                self.acompanhamentos_envolvidos_dias_efetivos_a_compensar[acompanhamento.id] = acompanhamento.dias_efetivos_a_compensar(contexto_compensacao=self)

        self.acompanhamentos_envolvidos_dias_agendados_para_atualizacao = []

    # -------------------------------------------------------------------------------------------------------

    @property
    def dias(self):
        """ todos os dias dentro do período informado """
        dias = datas_entre(self.periodo_inicial[0], self.periodo_inicial[1])
        return self._get_dias(dias)

    @property
    def dias_saldos(self):
        """ todos os saldos dentro do período informado """
        dias = datas_entre(self.periodo_inicial[0], self.periodo_inicial[1])
        return self._get_dias(dias, 'is_saldo')

    @property
    def dias_debitos(self):
        """ todos os débitos dentro do período informado """
        dias = datas_entre(self.periodo_inicial[0], self.periodo_inicial[1])
        return self._get_dias(dias, 'is_debito')

    @property
    def todos_dias_debitos(self):
        """ todos os débitos envolvidos """
        dias = self._get_dias_debitos_efetivos()
        return self._get_dias(dias, 'is_debito')

    @property
    def dias_debitos_especificos(self):
        """ todos os débitos específicos dentro do período informado """
        dias = datas_entre(self.periodo_inicial[0], self.periodo_inicial[1])
        return self._get_dias(dias, 'is_debito_especifico')

    @property
    def todos_dias_debitos_especificos(self):
        """ todos os débitos específicos envolvidos """
        dias = self._get_dias_debitos_efetivos()
        return self._get_dias(dias, 'is_debito_especifico')

    @property
    def dias_debitos_pendentes(self):
        """ todos os débitos pendentes dentro do período informado """
        dias = datas_entre(self.periodo_inicial[0], self.periodo_inicial[1])
        return self._get_dias(dias, 'is_debito_pendente')

    @property
    def todos_dias_debitos_pendentes(self):
        """ todos os débitos pendentes envolvidos """
        dias = self._get_dias_debitos_efetivos()
        return self._get_dias(dias, 'is_debito_pendente')

    # -------------------------------------------------------------------------------------------------------

    def __str__(self):
        contexto = ''
        for dia in list(self.situacao.keys()):
            contexto += '{}\n'.format(dia.strftime('%d/%m/%Y'))
        return contexto

    def add_dia(self, dia, situacao_dia=None):
        # dia = datetime.date
        if not situacao_dia:
            if dia in self.situacao:
                situacao_dia = self.situacao[dia]
            else:
                situacao_dia = SituacaoDia(servidor=self.servidor, dia=dia, contexto=self)
        self.situacao[dia] = situacao_dia

        # apenas agenda o dia para atualização (caso necessário) dos dados "anexos" ao contexto
        self.relatorio_de_ponto_dias_agendados_para_atualizacao.append(dia)
        self.compensacoes_informadas_dias_agendados_para_atualizacao.append(dia)
        self.acompanhamentos_envolvidos_dias_agendados_para_atualizacao.append(dia)

        return self.get_dia(dia)

    def add_periodo(self, data_inicial, data_final):
        for dia in get_datas_entre(data_inicial, data_final):
            self.add_dia(dia)

    def add_dias(self, dias):
        for dia in dias:
            self.add_dia(dia)

    def get_dia(self, dia, add_se_nao_existir=False):
        # dia = datetime.date
        if dia in self.situacao:
            return self.situacao[dia]  # instância de SituacaoDia
        elif add_se_nao_existir:
            return self.add_dia(dia)
        return None

    @property
    def get_periodo(self):
        return self.periodo_inicial

    @property
    def get_todo_periodo_envolvido(self):
        """
            baseado nos dias dos debitos efetivos
        """
        debito_data_minima = None
        debito_data_maxima = None

        dias_debitos_efetivos = self._get_dias_debitos_efetivos()
        if dias_debitos_efetivos:
            debito_data_minima = min(dias_debitos_efetivos)
            debito_data_maxima = max(dias_debitos_efetivos)

        return [debito_data_minima, debito_data_maxima]

    @property
    def get_relatorio_de_ponto(self):
        return self.relatorio_de_ponto

    @property
    def get_compensacoes_informadas(self):
        return self.compensacoes_informadas

    @property
    def get_acompanhamentos_envolvidos(self):
        return self.acompanhamentos_envolvidos

    @property
    def get_frequencias_as_queryset(self):
        frequencias = Frequencia.objects.none()
        if 'dias' in self.relatorio_de_ponto['dias']:
            for dia_ponto in self.relatorio_de_ponto['dias']:
                frequencias = frequencias | Frequencia.objects.filter(id__in=[frequencia.id for frequencia in dia_ponto['horarios']])
        return frequencias

    # -------------------------------------------------------------------------------------------------------

    @property
    def total_carga_horaria_qtd(self):
        """ dentro do período informado """
        return self._total_qtd(self.periodo_inicial[0], self.periodo_inicial[1], 'carga_horaria_qtd')

    @property
    def total_carga_horaria_trabalhada_qtd(self):
        """ dentro do período informado """
        return self._total_qtd(self.periodo_inicial[0], self.periodo_inicial[1], 'carga_horaria_trabalhada_qtd')

    @property
    def total_debito_qtd_considerado(self):
        """ dentro do período informado """
        return self._total_qtd(self.periodo_inicial[0], self.periodo_inicial[1], 'debito_qtd_considerado')

    @property
    def total_debito_qtd_desconsiderado(self):
        """ dentro do período informado """
        return self._total_qtd(self.periodo_inicial[0], self.periodo_inicial[1], 'debito_qtd_desconsiderado')

    @property
    def total_debito_qtd_reposto(self):
        """ dentro do período informado """
        return self._total_qtd(self.periodo_inicial[0], self.periodo_inicial[1], 'debito_qtd_reposto')

    @property
    def total_debito_qtd_restante(self):
        """ dentro do período informado """
        return self._total_qtd(self.periodo_inicial[0], self.periodo_inicial[1], 'debito_qtd_restante')

    @property
    def total_saldo_qtd_considerado(self):
        """ dentro do período informado """
        return self._total_qtd(self.periodo_inicial[0], self.periodo_inicial[1], 'saldo_qtd_considerado')

    @property
    def total_saldo_qtd_desconsiderado(self):
        """ dentro do período informado """
        return self._total_qtd(self.periodo_inicial[0], self.periodo_inicial[1], 'saldo_qtd_desconsiderado')

    @property
    def total_saldo_qtd_utilizado(self):
        """ dentro do período informado """
        return self._total_qtd(self.periodo_inicial[0], self.periodo_inicial[1], 'saldo_qtd_utilizado')

    @property
    def total_saldo_qtd_restante(self):
        """ dentro do período informado """
        return self._total_qtd(self.periodo_inicial[0], self.periodo_inicial[1], 'saldo_qtd_restante')

    # -------------------------------------------------------------------------------------------------------

    @property
    def mensagens_debito_desconsiderado(self):
        """ dentro do período informado """
        return self._get_log(self.periodo_inicial[0], self.periodo_inicial[1], SituacaoDia.LOG_OPERACAO_DEBITO_DESCONSIDERADO)

    @property
    def mensagens_saldo_desconsiderado(self):
        """ dentro do período informado """
        return self._get_log(self.periodo_inicial[0], self.periodo_inicial[1], SituacaoDia.LOG_OPERACAO_SALDO_DESCONSIDERADO)

    @property
    def dias_debito_desconsiderado(self):
        """ dentro do período informado """
        return self._get_dias_com_log(self.periodo_inicial[0], self.periodo_inicial[1], SituacaoDia.LOG_OPERACAO_DEBITO_DESCONSIDERADO)

    @property
    def dias_saldo_desconsiderado(self):
        """ dentro do período informado """
        return self._get_dias_com_log(self.periodo_inicial[0], self.periodo_inicial[1], SituacaoDia.LOG_OPERACAO_SALDO_DESCONSIDERADO)

    # -------------------------------------------------------------------------------------------------------

    def _get_dias_debitos_efetivos(self):
        """
            são todos os débitos do período informado + os débitos cobertos por cada um dos saldos do período informado
        """
        dias_debitos_efetivos = list(self.dias_debitos.keys())

        if self.dias_saldos:
            for saldo_situacao in list(self.dias_saldos.values()):
                for dia_possivel_debito in saldo_situacao.saldo_dias_dos_debitos:
                    if self.get_dia(dia_possivel_debito, add_se_nao_existir=True).is_debito:
                        dias_debitos_efetivos.append(dia_possivel_debito)

        return set(dias_debitos_efetivos)

    def _get_dias(self, dias, property_condicao=None):
        dias_situacao = OrderedDict()  # {dia: SituacaoDia, ...}
        for dia in dias:
            if property_condicao:
                if getattr(self.get_dia(dia, add_se_nao_existir=True), property_condicao):
                    dias_situacao[dia] = self.get_dia(dia)
            else:
                dias_situacao[dia] = self.get_dia(dia)
        return dias_situacao

    def _total_qtd(self, data_inicial, data_final, attr):
        total = 0
        for dia in datas_entre(data_inicial, data_final):
            total += getattr(self.get_dia(dia, add_se_nao_existir=True), attr)
        return total

    def _get_log(self, data_inicial, data_final, operacao):
        mensagens = []
        for dia in datas_entre(data_inicial, data_final):
            log = self.get_dia(dia).get_log(operacao)
            if log:
                mensagens.append('<strong>{}</strong>: {} '.format(dia.strftime('%d/%m/%Y'), log))
        return mensagens

    def _get_dias_com_log(self, data_inicial, data_final, operacao):
        dias = []
        for dia in datas_entre(data_inicial, data_final):
            log = self.get_dia(dia).get_log(operacao)
            if log:
                dias.append(dia)
        return dias


class SituacaoDia(object):
    """
        situação do ponto de um dia específico
    """

    LOG_OPERACAO_DEBITO_DESCONSIDERADO = 'debito_desconsiderado'
    LOG_OPERACAO_SALDO_DESCONSIDERADO = 'saldo_desconsiderado'

    def __init__(self, servidor, dia, contexto=None):
        self.servidor = servidor
        self.dia = dia  # datetime.date

        assert self.servidor is not None
        assert self.dia is not None

        # uma instância de Contexto (o contexto no qual o dia está incluído)
        self._contexto = contexto

        self._relatorio_ponto_do_dia = None  # {'dia': dia, ... } --> uma linha do relatório de ponto
        self._compensacoes_informadas_para_o_dia = None  # [compensação, compensação, compensação]
        self._acompanhamentos_envolvidos_contendo_o_dia = None
        self._acompanhamentos_envolvidos_contendo_o_dia_como_debito = None
        self._acompanhamentos_envolvidos_contendo_o_dia_inicialmente_como_debito = None
        self._acompanhamentos_envolvidos_contendo_o_dia_como_saldo = None
        self._abono_do_dia = None
        self._liberacao_tipo_parcial_do_dia = None
        self._liberacao_tipo_evento_do_dia = None

        # qtd = TODAS AS QUANTIDADES em segundos

        self._carga_horaria_inicial_qtd = None
        self._carga_horaria_qtd = None
        self._carga_horaria_trabalhada_qtd = None

        self._distribuicao_possivel_calculada = None

        self._debito_eh_especifico = None
        self._debito_qtd_inicial = None
        self._debito_precisa_repor = None
        self._debito_nao_pode_repor = None
        self._debito_qtd_desconsiderado = None
        self._debito_qtd_considerado = None
        self._debito_dias_dos_saldos = None
        self._debito_qtd_reposto = None
        self._debito_qtd_percentual_reposicao = None
        self._debito_qtd_restante = None
        self._debito_reposicao_distribuicao = None

        self._saldo_qtd_inicial = None
        self._saldo_qtd_maxima_permitida = None
        self._saldo_permitida_utilizacao = None
        self._saldo_qtd_desconsiderado = None
        self._saldo_qtd_considerado = None
        self._saldo_dias_dos_debitos = None
        self._saldo_qtd_utilizado = None
        self._saldo_qtd_restante = None
        self._saldo_utilizacao_distribuicao = None

        self.logs = {}  # {'operação': ['msg1', 'msg2', ...]}

    @property
    def contexto(self):
        if self._contexto is None:
            self._contexto = Contexto(self.servidor, self.dia, self.dia)
            # adiciona o dia (e sua situação) atual ao contexto
            self._contexto.add_dia(dia=self.dia, situacao_dia=self)
        return self._contexto

    def _add_log(self, operacao, mensagem):
        if operacao not in self.logs:
            self.logs[operacao] = []
        self.logs[operacao].append(mensagem)

    @property
    def hoje(self):
        return datetime.date.today()

    def get_log(self, operacao):
        log = ''
        if operacao in self.logs:
            log = '. '.join(self.logs[operacao])
        if log:
            log += '. '
        return log

    @property
    def get_log_ch_desconsiderada(self):
        if self.is_debito:
            return self.get_log(self.LOG_OPERACAO_DEBITO_DESCONSIDERADO)
        if self.is_saldo:
            return self.get_log(self.LOG_OPERACAO_SALDO_DESCONSIDERADO)
        return ''

    # -------------------------------------------------------------------------------------------------------

    @property
    def relatorio_ponto_do_dia(self):
        """
            relatorio_ponto_do_dia = {'dia': ? (date), 'carga_horaria_do_dia': ? (int q indica horas), ... }
        """
        if self._relatorio_ponto_do_dia is None:
            if self.contexto.relatorio_de_ponto is None:
                self.contexto.relatorio_de_ponto = get_relatorio_de_ponto(self.servidor, self.dia, self.dia)

            def buscar_ponto_do_dia(situacao_dia):
                relatorio_ponto_do_dia = {}
                for dia in situacao_dia.contexto.relatorio_de_ponto['dias']:
                    if dia['dia'] == situacao_dia.dia:
                        relatorio_ponto_do_dia = dia
                        break
                return relatorio_ponto_do_dia

            self._relatorio_ponto_do_dia = buscar_ponto_do_dia(self)

            if not self._relatorio_ponto_do_dia:
                #########################
                # o contexto precisa ser atualizado
                # adianta: 5 dias antes e 5 dias depois
                cinco_dias = datetime.timedelta(5)
                self.contexto.add_periodo(self.dia - cinco_dias, self.dia + cinco_dias)
                self.contexto.update_relatorio_de_ponto()
                self._relatorio_ponto_do_dia = buscar_ponto_do_dia(self)

        return self._relatorio_ponto_do_dia

    @property
    def ha_frequencia_no_dia(self):
        ponto_do_dia = self.relatorio_ponto_do_dia
        return ponto_do_dia and ponto_do_dia['duracao_segundos'] > 0

    @property
    def relatorio_ponto_do_dia_as_relatorio_frequencias(self):
        if self.relatorio_ponto_do_dia:
            frequencia_do_dia = self.relatorio_ponto_do_dia
            if self.is_debito:
                frequencia_do_dia.update(
                    {
                        'compensacao': {
                            'is_debito': True,
                            'ch_paga_percentual': self.debito_qtd_percentual_reposicao,
                            'ch_restante_a_pagar': formatar_segundos(self.debito_qtd_restante),
                            'ch_restante_a_pagar_is_maior_que_zero': self.debito_qtd_restante > 0,
                            'ch_restante_a_pagar_is_menor_que_15min': self.debito_qtd_restante < 900,
                            'acompanhamentos_compensacoes_especificas': self.acompanhamentos_envolvidos_contendo_o_dia_como_debito,
                        }
                    }
                )
            return {'funcionario': self.contexto.servidor, 'dias': [frequencia_do_dia]}
        return {}

    @property
    def compensacoes_informadas_para_o_dia(self):
        if self._compensacoes_informadas_para_o_dia is None:
            if self.contexto.compensacoes_informadas is None:
                self.contexto.compensacoes_informadas = get_compensacoes_informadas(self.servidor, self.dia, self.dia)

            def buscar_compensacoes_informadas_para_o_dia(situacao_dia):
                return (
                    situacao_dia.contexto.compensacoes_informadas.filter(data_compensacao=situacao_dia.dia)
                    | situacao_dia.contexto.compensacoes_informadas.filter(data_aplicacao=situacao_dia.dia)
                ).distinct()

            cinco_dias = datetime.timedelta(5)
            self.contexto.add_periodo(self.dia - cinco_dias, self.dia + cinco_dias)
            self.contexto.update_compensacoes_informadas()
            self._compensacoes_informadas_para_o_dia = buscar_compensacoes_informadas_para_o_dia(self)

        return self._compensacoes_informadas_para_o_dia

    @property
    def acompanhamentos_envolvidos_contendo_o_dia(self):
        if self._acompanhamentos_envolvidos_contendo_o_dia is None:
            if self.contexto.acompanhamentos_envolvidos is None:
                self.contexto.acompanhamentos_envolvidos = get_acompanhamentos(self.servidor, self.dia, self.dia)

            self._acompanhamentos_envolvidos_contendo_o_dia = RecessoOpcaoEscolhida.objects.none()

            def buscar_acompanhamentos_envolvidos_contendo_o_dia(situacao_dia):
                return (
                    situacao_dia.contexto.acompanhamentos_envolvidos.filter(dias_escolhidos__dia__data=situacao_dia.dia)
                    | situacao_dia.contexto.acompanhamentos_envolvidos.filter(
                        recesso_opcao__periodos_de_compensacao__data_inicial__lte=situacao_dia.dia, recesso_opcao__periodos_de_compensacao__data_final__gte=situacao_dia.dia
                    )
                ).distinct()

            cinco_dias = datetime.timedelta(5)
            self.contexto.add_periodo(self.dia - cinco_dias, self.dia + cinco_dias)
            self.contexto.update_acompanhamentos_envolvidos()
            self._acompanhamentos_envolvidos_contendo_o_dia = buscar_acompanhamentos_envolvidos_contendo_o_dia(self)
        return self._acompanhamentos_envolvidos_contendo_o_dia

    @property
    def acompanhamentos_envolvidos_contendo_o_dia_como_debito(self):
        if self._acompanhamentos_envolvidos_contendo_o_dia_como_debito is None:
            self._acompanhamentos_envolvidos_contendo_o_dia_como_debito = self.acompanhamentos_envolvidos_contendo_o_dia.filter(dias_escolhidos__dia__data=self.dia)

            # chamado 63394: É possível que um servidor venha trabalhar normalmente mesmo em um dia que ele
            # mesmo escolheu para débito. Nesse caso, o dia passa a ser normal (podendo gerar saldo ou débito)
            acompanhamentos_ids_exclude = []
            for acompanhamento in self._acompanhamentos_envolvidos_contendo_o_dia_como_debito:
                # se a opção de compensação permite que o público alvo escolha livremente os dias
                # e o dia em questão tem frequências, então esse dia deixa de ser um débito com um acompanhamento
                # específico
                if acompanhamento.recesso_opcao.is_permite_escolha_dos_dias_pelos_servidores:
                    if self.ha_frequencia_no_dia:
                        acompanhamentos_ids_exclude.append(acompanhamento.id)

            if acompanhamentos_ids_exclude:
                self._acompanhamentos_envolvidos_contendo_o_dia_como_debito = self._acompanhamentos_envolvidos_contendo_o_dia_como_debito.exclude(
                    id__in=acompanhamentos_ids_exclude
                )

        return self._acompanhamentos_envolvidos_contendo_o_dia_como_debito

    @property
    def acompanhamentos_envolvidos_contendo_o_dia_como_saldo(self):
        if self._acompanhamentos_envolvidos_contendo_o_dia_como_saldo is None:
            self._acompanhamentos_envolvidos_contendo_o_dia_como_saldo = self.acompanhamentos_envolvidos_contendo_o_dia.filter(
                recesso_opcao__periodos_de_compensacao__data_inicial__lte=self.dia, recesso_opcao__periodos_de_compensacao__data_final__gte=self.dia
            )
        return self._acompanhamentos_envolvidos_contendo_o_dia_como_saldo

    @property
    def has_funcao_no_dia(self):
        return self.contexto.historico_funcao.filter(Q(data_inicio_funcao__lte=self.dia), Q(data_fim_funcao__gte=self.dia) | Q(data_fim_funcao__isnull=True)).exists()

    # -------------------------------------------------------------------------------------------------------
    @property
    def carga_horaria_maxima_permitida_para_o_dia(self):
        # 10 horas
        ch_qtd_maxima_diaria = 10 * 60 * 60  # em segundos

        # trata liberação parcial (pode ser que a máxima exigida seja menor que as 10h)
        liberacao_parcial = self.liberacao_tipo_parcial_do_dia
        if liberacao_parcial:
            ch_qtd_maxima_diaria = liberacao_parcial.ch_maxima_exigida * 60 * 60  # em segundos

        return ch_qtd_maxima_diaria

    @property
    def abono_do_dia(self):
        if self._abono_do_dia is None:
            ponto_do_dia = self.relatorio_ponto_do_dia
            if 'abono_chefia' in ponto_do_dia:
                self._abono_do_dia = ponto_do_dia['abono_chefia']
        return self._abono_do_dia

    @property
    def liberacao_tipo_parcial_do_dia(self):
        if self._liberacao_tipo_parcial_do_dia is None:
            ponto_do_dia = self.relatorio_ponto_do_dia
            if ponto_do_dia:
                for liberacao in ponto_do_dia.get('liberacoes', []):
                    if liberacao.tipo == TipoLiberacao.get_numero(TipoLiberacao.LIBERACAO_PARCIAL):
                        self._liberacao_tipo_parcial_do_dia = liberacao
        return self._liberacao_tipo_parcial_do_dia

    @property
    def liberacao_tipo_evento_do_dia(self):
        if self._liberacao_tipo_evento_do_dia is None:
            ponto_do_dia = self.relatorio_ponto_do_dia
            if ponto_do_dia:
                for liberacao in ponto_do_dia.get('liberacoes', []):
                    if liberacao.tipo == TipoLiberacao.get_numero(TipoLiberacao.EVENTO):
                        self._liberacao_tipo_evento_do_dia = liberacao
        return self._liberacao_tipo_evento_do_dia

    @property
    def carga_horaria_inicial_qtd(self):
        """ ch exigida INICIALMENTE para o dia """
        if self._carga_horaria_inicial_qtd is None:
            # {'dia': ? (date), 'carga_horaria_do_dia': ? (int q indica horas), ... }
            ponto_do_dia = self.relatorio_ponto_do_dia

            if self.is_dia_util_para_debito or self.is_dia_util_para_saldo:
                if 'carga_horaria_do_dia' in ponto_do_dia:
                    self._carga_horaria_inicial_qtd = ponto_do_dia['carga_horaria_do_dia'] * 60 * 60  # em segundos

                if self.is_sabado or self.is_domingo:
                    self._carga_horaria_inicial_qtd = 0  # nada é exigido

            if self._carga_horaria_inicial_qtd is None:
                self._carga_horaria_inicial_qtd = 0
        return self._carga_horaria_inicial_qtd

    @property
    def carga_horaria_qtd(self):
        """ ch exigida FINAL para o dia """
        if self._carga_horaria_qtd is None:
            self._carga_horaria_qtd = self.carga_horaria_inicial_qtd

            # trata liberação parcial
            liberacao_parcial = self.liberacao_tipo_parcial_do_dia
            if liberacao_parcial:
                ch_maxima_exigida_pela_instituicao = liberacao_parcial.ch_maxima_exigida * 60 * 60  # segundos
                if self._carga_horaria_qtd > ch_maxima_exigida_pela_instituicao:
                    self._carga_horaria_qtd = ch_maxima_exigida_pela_instituicao

            if self._carga_horaria_qtd is None:
                self._carga_horaria_qtd = 0
        return self._carga_horaria_qtd

    @property
    def carga_horaria_trabalhada_qtd(self):
        """ carga horária trabalhada no dia """
        if self._carga_horaria_trabalhada_qtd is None:
            ponto_do_dia = self.relatorio_ponto_do_dia
            if 'duracao_segundos_bruto' in ponto_do_dia:
                self._carga_horaria_trabalhada_qtd = ponto_do_dia['duracao_segundos_bruto']
            if self._carga_horaria_trabalhada_qtd is None:
                self._carga_horaria_trabalhada_qtd = 0
        return self._carga_horaria_trabalhada_qtd

    @property
    def is_sabado_ou_domingo(self):
        return self.is_sabado or self.is_domingo

    @property
    def is_sabado(self):
        return self.dia.weekday() == 5

    @property
    def is_domingo(self):
        return self.dia.weekday() == 6

    @property
    def is_dia_possivel(self):
        escopo_data_minima = self.contexto.data_inicio_a_cobrar_compensacao
        escopo_data_maxima = self.contexto.data_fim_a_cobrar_compensacao or self.dia
        return escopo_data_minima <= self.dia <= escopo_data_maxima

    @property
    def is_dia_util(self):
        """ é um dia útil para o servidor?
            com informações extras

            :return [True/False, ['infor extra', 'infor extra', 'infor extra', ...]]
        """
        if not self.is_dia_possivel:
            return False, []

        informacoes_extras = []
        ponto_do_dia = self.relatorio_ponto_do_dia or {}

        # condição 1 (não pode ser sáb ou dom)
        condicao_1 = not self.is_sabado_ou_domingo
        if not condicao_1:
            if self.is_sabado:
                informacoes_extras.append('Sábado')
            elif self.is_domingo:
                informacoes_extras.append('Domingo')

        # condição 2 (não pode haver qualquer afastamento, liberação, viagens ou férias)
        afastamentos = [ponto_do_dia.get('afastamentos_siape'), ponto_do_dia.get('afastamentos_rh')]

        liberacoes = [ponto_do_dia.get('liberacoes')]

        viagens_ferias = [ponto_do_dia.get('viagens_scdp'), ponto_do_dia.get('ferias')]

        ocorrencias = afastamentos + liberacoes + viagens_ferias

        condicao_2 = not any(ocorrencias)
        if not condicao_2:
            for tipo_ocorrencias in ocorrencias:
                if tipo_ocorrencias:
                    for ocorrencia in tipo_ocorrencias:
                        try:
                            informacoes_extras.append(str(ocorrencia))
                        except Exception:
                            pass

        # dia útil ?
        is_dia_util = condicao_1 and condicao_2

        # ordem de precedência
        # viagens_ferias > afastamentos > liberações

        if not is_dia_util:
            if not any(viagens_ferias):
                # trata exceções em afastamento/liberações que ainda podem tornar o dia como útil
                if any(afastamentos):
                    # trata afastamento parcial
                    afastamentos_parciais = Afastamento.buscar_afastamentos_parciais(self.servidor.get_vinculo(), self.dia, self.dia)
                    for afastamento in afastamentos:
                        if afastamento in afastamentos_parciais:
                            ch_do_dia = ponto_do_dia['carga_horaria_do_dia'] * 60 * 60
                            if ch_do_dia > 0:
                                # o dia é útil conforme contexto:
                                #   - não há férias ou viagens
                                #   - há afastamento parcial
                                #   - CH do dia é maior que zero (CH que deve ser cumprida!!!)
                                is_dia_util = True
                                break
                elif any(liberacoes):
                    # trata liberacao parcial
                    if self.liberacao_tipo_parcial_do_dia:
                        # o dia é útil conforme contexto:
                        #   - não há férias ou viagens
                        #   - não há afastamentos
                        #   - há liberação parcial
                        #   - CH que deve ser cumprida até o limite definido no cadastro da liberação parcial
                        is_dia_util = True

        return is_dia_util, informacoes_extras

    @property
    def is_dia_que_pode_gerar_debito(self):
        if not self.is_dia_possivel:
            return False

        # o dia é útil para o servidor?
        condicao_1 = self.is_dia_util[0]

        if not self.servidor.eh_docente:
            return condicao_1
        else:
            ###
            # trata servidor docente
            # o ponto docente está ativado E
            # o servidor não tem função no dia E
            # o dia não é um débito de um acompanhamento específico
            # então, o cálculo de débitos está fora do escopo deste módulo
            condicao_2 = self.contexto.ponto_docente_ativado and not self.has_funcao_no_dia and not self.is_debito_especifico

            if condicao_2:
                return False
            ###

            return condicao_1

    @property
    def is_dia_que_pode_gerar_saldo(self):
        if not self.is_dia_possivel:
            return False

        # regra geral
        condicao_1 = self.is_sabado_ou_domingo or self.is_dia_que_pode_gerar_debito

        # trata o tipo de liberação EVENTO
        # o dia em questão possui uma liberação e isso, por padrão, impossibilita a geração de saldo,
        # exceto se a liberação é do tipo EVENTO
        condicao_2 = self.liberacao_tipo_evento_do_dia

        # trata servidor docente
        # a app pit_rit está instalada
        # o ponto docente está ativado
        # o servidor não tem função no dia
        # então, o cálculo de saldos está fora do escopo deste módulo
        condicao_3 = self.servidor.eh_docente and self.contexto.ponto_docente_ativado and not self.has_funcao_no_dia

        pode_gerar_saldo = condicao_1 or condicao_2 or condicao_3

        return pode_gerar_saldo

    @property
    def is_dia_util_para_debito(self):
        return self.is_dia_que_pode_gerar_debito

    @property
    def is_dia_util_para_saldo(self):
        return self.is_dia_que_pode_gerar_saldo

    # -------------------------------------------------------------------------------------------------------

    @property
    def is_debito_inicialmente(self):
        """ é um possível débito ? """
        if self.dia >= self.hoje and not self.is_debito_especifico:
            return False  # o dia está no futuro e não é um débito específico
        return self.is_dia_util_para_debito and (self.carga_horaria_trabalhada_qtd - self.carga_horaria_qtd < 0)  # trabalhou menos que a exigida?

    @property
    def is_debito_especifico(self):
        """ é um débito específico em acompanhamento? """
        if self._debito_eh_especifico is None:
            self._debito_eh_especifico = self.acompanhamentos_envolvidos_contendo_o_dia_como_debito.exists()

            if self._debito_eh_especifico is None:
                self._debito_eh_especifico = False
        return self._debito_eh_especifico

    @property
    def debito_qtd_inicial(self):
        if self._debito_qtd_inicial is None:
            if self.is_debito_inicialmente:
                self._debito_qtd_inicial = (self.carga_horaria_trabalhada_qtd - self.carga_horaria_qtd) * -1

            if self._debito_qtd_inicial is None:
                self._debito_qtd_inicial = 0
        return self._debito_qtd_inicial

    @property
    def debito_precisa_repor(self):
        """ precisa ou não repor? """
        if self._debito_precisa_repor is None:
            if self.debito_qtd_inicial:
                abono_do_dia = self.abono_do_dia
                abono_com_compensacao = abono_do_dia and abono_do_dia.acao_abono == AbonoChefia.ABONADO_COM_COMPENSACAO
                self._debito_precisa_repor = not abono_do_dia or abono_com_compensacao

                if not self._debito_precisa_repor:
                    abono_sem_compensacao = abono_do_dia and abono_do_dia.acao_abono == AbonoChefia.ABONADO_SEM_COMPENSACAO
                    if abono_sem_compensacao:
                        self._add_log(self.LOG_OPERACAO_DEBITO_DESCONSIDERADO, 'Abonado Sem Compensação pela Chefia Imediata')
                    trabalho_remoto = abono_do_dia and abono_do_dia.acao_abono == AbonoChefia.TRABALHO_REMOTO
                    if trabalho_remoto:
                        self._add_log(self.LOG_OPERACAO_DEBITO_DESCONSIDERADO, 'Trabalho remoto validado pela Chefia Imediata')

            if self._debito_precisa_repor is None:
                self._debito_precisa_repor = False
        return self._debito_precisa_repor

    @property
    def debito_nao_pode_repor(self):
        """ pode ou não repor? """
        if self._debito_nao_pode_repor is None:
            if self.debito_qtd_inicial:
                abono_do_dia = self.abono_do_dia
                self._debito_nao_pode_repor = abono_do_dia and abono_do_dia.acao_abono == AbonoChefia.NAO_ABONADO

                if self._debito_nao_pode_repor:
                    self._add_log(self.LOG_OPERACAO_DEBITO_DESCONSIDERADO, 'Não Abonado pela Chefia Imediata')

            if self._debito_nao_pode_repor is None:
                self._debito_nao_pode_repor = False
        return self._debito_nao_pode_repor

    @property
    def debito_qtd_desconsiderado(self):
        """ com os motivos """
        if self._debito_qtd_desconsiderado is None:
            if self.debito_qtd_inicial:
                self._debito_qtd_desconsiderado = 0

                if self.debito_nao_pode_repor:
                    self._debito_qtd_desconsiderado = self.debito_qtd_inicial  # TOTALMENTE desconsiderado

                    self._add_log(self.LOG_OPERACAO_DEBITO_DESCONSIDERADO, 'Não poderá pagar o débito')

                if not self.debito_precisa_repor:
                    self._debito_qtd_desconsiderado = self.debito_qtd_inicial  # TOTALMENTE desconsiderado

                    self._add_log(self.LOG_OPERACAO_DEBITO_DESCONSIDERADO, 'Não precisará pagar o débito')

                # trata liberação parcial
                liberacao_parcial = self.liberacao_tipo_parcial_do_dia
                if liberacao_parcial:
                    ch_maxima_exigida_pela_instituicao = liberacao_parcial.ch_maxima_exigida * 60 * 60  # em segundos
                    ch_exigida_inicial_servidor = self.carga_horaria_inicial_qtd
                    ch_trabalhada_servidor = self.carga_horaria_trabalhada_qtd

                    if ch_trabalhada_servidor:
                        if ch_trabalhada_servidor < ch_exigida_inicial_servidor:
                            if ch_trabalhada_servidor >= ch_maxima_exigida_pela_instituicao:
                                self._debito_qtd_desconsiderado = self.debito_qtd_inicial  # TOTALMENTE desconsiderado
                                self._add_log(
                                    self.LOG_OPERACAO_DEBITO_DESCONSIDERADO,
                                    'Não precisará pagar o débito pois a carga horária trabalhada é maior '
                                    'que a carga horária máxima exigida pela instituição devido à liberação '
                                    'parcial ocorrida no dia em questão',
                                )

            if self._debito_qtd_desconsiderado is None:
                self._debito_qtd_desconsiderado = 0
        return self._debito_qtd_desconsiderado

    @property
    def debito_qtd_considerado(self):
        if self._debito_qtd_considerado is None:
            if self.debito_qtd_inicial:
                self._debito_qtd_considerado = self.debito_qtd_inicial - self.debito_qtd_desconsiderado

            if self._debito_qtd_considerado is None:
                self._debito_qtd_considerado = self.debito_qtd_inicial
        return self._debito_qtd_considerado

    @property
    def is_debito(self):
        return self.debito_qtd_considerado > 0

    @property
    def debito_dias_dos_saldos(self):
        """ universo de dias de saldo para quitar o débito """
        if self._debito_dias_dos_saldos is None:
            if self.debito_qtd_considerado:
                self._debito_dias_dos_saldos = []

                # regra: mês seguinte
                dia_inicial_saldo = self.dia + datetime.timedelta(1)
                dia_final_saldo = datetime.date((self.dia + relativedelta(months=2)).year, (self.dia + relativedelta(months=2)).month, 1) - datetime.timedelta(1)
                self._debito_dias_dos_saldos += get_datas_entre(dia_inicial_saldo, dia_final_saldo)

                # regra: débitos em acompanhamento
                opcoes_compensacoes = RecessoOpcao.objects.filter(recessoopcaoescolhida__in=self.acompanhamentos_envolvidos_contendo_o_dia_como_debito)
                for periodo_compensacao in RecessoPeriodoCompensacao.objects.filter(recesso_opcao__in=opcoes_compensacoes):
                    self._debito_dias_dos_saldos += get_datas_entre(periodo_compensacao.data_inicial, periodo_compensacao.data_final)

                self._debito_dias_dos_saldos = sorted(set(self._debito_dias_dos_saldos))

            if self._debito_dias_dos_saldos is None:
                self._debito_dias_dos_saldos = []

        return self._debito_dias_dos_saldos

    @property
    def debito_qtd_reposto(self):
        """ débito com reposição informada """
        if self._debito_qtd_reposto is None:
            if self.debito_qtd_considerado:
                self._debito_qtd_reposto = 0
                for compensacao in self.compensacoes_informadas_para_o_dia:
                    if compensacao.data_aplicacao == self.dia:
                        self._debito_qtd_reposto += Frequencia.time_para_segundos(compensacao.ch_compensada)

            if self._debito_qtd_reposto is None:
                self._debito_qtd_reposto = 0
        return self._debito_qtd_reposto

    @property
    def debito_qtd_percentual_reposicao(self):
        """ percentual de reposição do débito """
        if self._debito_qtd_percentual_reposicao is None:
            self._debito_qtd_percentual_reposicao = 0
            if self.debito_qtd_considerado:
                self._debito_qtd_percentual_reposicao = int(self.debito_qtd_reposto * 100 / self.debito_qtd_considerado)
                if self._debito_qtd_percentual_reposicao > 100:  # possível situação de duplicidade de compensações
                    self._debito_qtd_percentual_reposicao = 100
        return self._debito_qtd_percentual_reposicao

    @property
    def debito_qtd_restante(self):
        """ o que resta de débito """
        if self._debito_qtd_restante is None:
            if self.debito_qtd_considerado:
                self._debito_qtd_restante = self.debito_qtd_considerado - self.debito_qtd_reposto
            else:
                self._debito_qtd_restante = 0

            if self._debito_qtd_restante is None:
                self._debito_qtd_restante = 0

            if self._debito_qtd_restante < 0:  # possível situação de duplicidade de compensações
                self._debito_qtd_restante = 0
        return self._debito_qtd_restante

    @property
    def debito_reposicao_distribuicao(self):
        if self._debito_reposicao_distribuicao is None:
            debito_distribuicoes = OrderedDict()

            for dia_saldo in self.debito_dias_dos_saldos:
                debito_distribuicao = [dia_saldo, 0, []]

                for compensacao in self.compensacoes_informadas_para_o_dia:
                    if compensacao.data_compensacao == dia_saldo:
                        debito_distribuicao[1] += Frequencia.time_para_segundos(compensacao.ch_compensada)
                        debito_distribuicao[2].append(compensacao)

                debito_distribuicoes[dia_saldo] = (debito_distribuicao[0], debito_distribuicao[1], debito_distribuicao[2])
            self._debito_reposicao_distribuicao = list(debito_distribuicoes.values())
        return self._debito_reposicao_distribuicao

    @property
    def is_debito_pendente(self):
        return self.debito_qtd_restante > 0

    # -------------------------------------------------------------------------------------------------------

    @property
    def is_saldo_inicialmente(self):
        """ é um possível saldo ? """
        if self.dia >= self.hoje:
            return False  # o dia está no futuro
        return self.is_dia_util_para_saldo and (self.carga_horaria_trabalhada_qtd - self.carga_horaria_qtd > 0)  # trabalhou mais que a exigida?

    @property
    def saldo_qtd_inicial(self):
        if self._saldo_qtd_inicial is None:
            if self.is_saldo_inicialmente:
                self._saldo_qtd_inicial = self.carga_horaria_trabalhada_qtd - self.carga_horaria_qtd

            if self._saldo_qtd_inicial is None:
                self._saldo_qtd_inicial = 0
        return self._saldo_qtd_inicial

    @property
    def saldo_qtd_maxima_permitida(self):
        if self._saldo_qtd_maxima_permitida is None:
            # qtd máxima diária - CH do dia
            self._saldo_qtd_maxima_permitida = self.carga_horaria_maxima_permitida_para_o_dia - self.carga_horaria_qtd

            if self._saldo_qtd_maxima_permitida <= 0:
                # isso ocorrerá em algum momento ???
                # sim. no caso de liberação parcial do dia.
                # nessa caso, é possível que não haja margem para
                # geração de saldo (ex: minha carga horária é 8h mas a instituição exigiu apenas 6h)
                self._saldo_qtd_maxima_permitida = 0
        return self._saldo_qtd_maxima_permitida

    @property
    def saldo_permitida_utilizacao(self):
        """ pode utilizar? """
        if self._saldo_permitida_utilizacao is None:
            if self.saldo_qtd_inicial:
                abono_do_dia = self.abono_do_dia

                abono_negativo_1 = abono_do_dia and abono_do_dia.acao_abono == AbonoChefia.HORA_EXTRA_NAO_JUSTIFICADA

                abono_negativo_2 = abono_do_dia and abono_do_dia.acao_abono == AbonoChefia.HORA_EXTRA_JUSTIFICADA

                abono_negativo_3 = abono_do_dia and abono_do_dia.acao_abono == AbonoChefia.TRABALHO_FDS_NAO_PERMITIDO

                abono_negativo_4 = abono_do_dia and abono_do_dia.acao_abono == AbonoChefia.TRABALHO_FDS_PERMITIDO_COMO_HORA_EXTRA

                saldo_is_desconsiderado = abono_do_dia and (abono_negativo_1 or abono_negativo_2 or abono_negativo_3 or abono_negativo_4)

                self._saldo_permitida_utilizacao = not abono_do_dia or (abono_do_dia and not saldo_is_desconsiderado)

                if not self._saldo_permitida_utilizacao:
                    if abono_negativo_1:
                        self._add_log(self.LOG_OPERACAO_SALDO_DESCONSIDERADO, 'Hora Extra Não Justificada')

                    if abono_negativo_2:
                        self._add_log(self.LOG_OPERACAO_SALDO_DESCONSIDERADO, 'Hora Extra Justificada')

                    if abono_negativo_3:
                        self._add_log(self.LOG_OPERACAO_SALDO_DESCONSIDERADO, 'Trabalho no Fim de Semana Não Justificado')

                    if abono_negativo_4:
                        self._add_log(self.LOG_OPERACAO_SALDO_DESCONSIDERADO, 'Trabalho no Fim de Semana como Hora Extra')

            if self._saldo_permitida_utilizacao is None:
                self._saldo_permitida_utilizacao = False
        return self._saldo_permitida_utilizacao

    @property
    def saldo_qtd_desconsiderado(self):
        """ com os motivos """
        if self._saldo_qtd_desconsiderado is None:
            if self.saldo_qtd_inicial:
                self._saldo_qtd_desconsiderado = 0

                if not self.saldo_permitida_utilizacao:
                    self._saldo_qtd_desconsiderado = self.saldo_qtd_inicial  # TOTALMENTE desconsiderado

                # trata o saldo máximo permitido
                if self.saldo_qtd_inicial and self.saldo_qtd_inicial > self.saldo_qtd_maxima_permitida:
                    # desconsidera o excedente
                    self._saldo_qtd_desconsiderado = self.saldo_qtd_inicial - self.saldo_qtd_maxima_permitida

                    if self.saldo_qtd_maxima_permitida > 0:
                        self._add_log(
                            self.LOG_OPERACAO_SALDO_DESCONSIDERADO,
                            '{} foram desconsiderados como saldo pois o limite de '
                            'carga horária máxima diária de {} foi ultrapassado'.format(
                                formatar_segundos(self._saldo_qtd_desconsiderado, True, True), formatar_segundos(self.carga_horaria_maxima_permitida_para_o_dia, True, True)
                            ),
                        )
                    else:
                        # desconsidera tudo que foi gerado
                        self._add_log(
                            self.LOG_OPERACAO_SALDO_DESCONSIDERADO,
                            '{} foram desconsiderados como saldo pois no dia em questão '
                            'não há possibilidade de geração de saldo'.format(formatar_segundos(self._saldo_qtd_desconsiderado, True, True)),
                        )

            if self._saldo_qtd_desconsiderado is None:
                self._saldo_qtd_desconsiderado = 0
        return self._saldo_qtd_desconsiderado

    @property
    def saldo_qtd_considerado(self):
        if self._saldo_qtd_considerado is None:
            if self.saldo_qtd_inicial:
                self._saldo_qtd_considerado = self.saldo_qtd_inicial - self.saldo_qtd_desconsiderado

            if self._saldo_qtd_considerado is None:
                self._saldo_qtd_considerado = self.saldo_qtd_inicial

        return self._saldo_qtd_considerado

    @property
    def is_saldo(self):
        return self.saldo_qtd_considerado > 0

    @property
    def saldo_dias_dos_debitos(self):
        """ abrangência dos débitos """
        if self._saldo_dias_dos_debitos is None:
            if self.saldo_qtd_considerado:
                self._saldo_dias_dos_debitos = []

                # regra: mês seguinte (anterior nesse caso)
                dia_inicial_debito = datetime.date((self.dia - relativedelta(months=1)).year, (self.dia - relativedelta(months=1)).month, 1)
                dia_final_debito = self.dia - datetime.timedelta(1)

                self._saldo_dias_dos_debitos += get_datas_entre(dia_inicial_debito, dia_final_debito)

                # regra: débitos em acompanhamento
                for acompanhamento in self.acompanhamentos_envolvidos_contendo_o_dia_como_saldo:
                    if acompanhamento.id in self.contexto.acompanhamentos_envolvidos_dias_efetivos_a_compensar:
                        self._saldo_dias_dos_debitos += self.contexto.acompanhamentos_envolvidos_dias_efetivos_a_compensar[acompanhamento.id]
                    else:
                        self._saldo_dias_dos_debitos += acompanhamento.dias_efetivos_a_compensar(contexto_compensacao=self.contexto)

                self._saldo_dias_dos_debitos = sorted(set(self._saldo_dias_dos_debitos))

            if self._saldo_dias_dos_debitos is None:
                self._saldo_dias_dos_debitos = []

        return self._saldo_dias_dos_debitos

    @property
    def saldo_qtd_utilizado(self):
        """ saldo utilizado em reposições """
        if self._saldo_qtd_utilizado is None:
            if self.saldo_qtd_considerado:
                self._saldo_qtd_utilizado = 0
                for compensacao in self.compensacoes_informadas_para_o_dia:
                    if compensacao.data_compensacao == self.dia:
                        self._saldo_qtd_utilizado += Frequencia.time_para_segundos(compensacao.ch_compensada)

            if self._saldo_qtd_utilizado is None:
                self._saldo_qtd_utilizado = 0
        return self._saldo_qtd_utilizado

    @property
    def saldo_qtd_restante(self):
        """ o que resta de saldo """
        if self._saldo_qtd_restante is None:
            if self.saldo_qtd_considerado:
                self._saldo_qtd_restante = self.saldo_qtd_considerado - self.saldo_qtd_utilizado
            else:
                self._saldo_qtd_restante = 0

            if self._saldo_qtd_restante < 0:  # possível situação de duplicidade de compensações
                self._saldo_qtd_restante = 0
        return self._saldo_qtd_restante

    @property
    def saldo_utilizacao_distribuicao(self):
        if self._saldo_utilizacao_distribuicao is None:
            saldo_distribuicoes = OrderedDict()

            for dia_debito in self.saldo_dias_dos_debitos:
                # data do débito,
                # ch utilizada,
                # compensações que geraram a ch utilizada,
                # débito específico? / acompanhamentos

                debito_especifico_acompanhamentos = None
                dia_debito_situacao = self.contexto.get_dia(dia_debito, add_se_nao_existir=True)
                if dia_debito_situacao.is_debito_especifico:
                    debito_especifico_acompanhamentos = dia_debito_situacao.acompanhamentos_envolvidos_contendo_o_dia_como_debito

                saldo_distribuicao = [dia_debito, 0, [], debito_especifico_acompanhamentos]

                for compensacao in self.compensacoes_informadas_para_o_dia:
                    if compensacao.data_aplicacao == dia_debito:
                        saldo_distribuicao[1] += Frequencia.time_para_segundos(compensacao.ch_compensada)
                        saldo_distribuicao[2].append(compensacao)

                saldo_distribuicoes[dia_debito] = (saldo_distribuicao[0], saldo_distribuicao[1], saldo_distribuicao[2], saldo_distribuicao[3])
            self._saldo_utilizacao_distribuicao = list(saldo_distribuicoes.values())
        return self._saldo_utilizacao_distribuicao

    # -------------------------------------------------------------------------------------------------------


def debito_pendente(servidor, data_inicial, data_final, data_limite_compensacao=None):
    """ retorna o débito restante/pendente em segundos no período informado

        Se for informado uma data limite para compensação, retornará uma lista com:
            - o débito restante/pendente em segundos no período informado
            - o débito restante/pendente em segundos no período informado que pode ser compensado até a data limite
    """
    contexto = Contexto(servidor=servidor, periodo_data_inicial=data_inicial, periodo_data_final=data_final)

    ch_pendente_no_periodo = 0  # em segundos
    ch_pendente_no_periodo_ate_data_limite_compensacao = 0  # em segundos

    for dia_debito_situacao in list(contexto.dias_debitos_pendentes.values()):
        ch_pendente_no_periodo += dia_debito_situacao.debito_qtd_restante

        if data_limite_compensacao:
            pode_quitar_apos_data_limite_compensacao = False
            for dia_saldo in dia_debito_situacao.debito_dias_dos_saldos:
                if dia_saldo > data_limite_compensacao:
                    pode_quitar_apos_data_limite_compensacao = True
                    break
            if not pode_quitar_apos_data_limite_compensacao:
                ch_pendente_no_periodo_ate_data_limite_compensacao += dia_debito_situacao.debito_qtd_restante

    return ch_pendente_no_periodo, ch_pendente_no_periodo_ate_data_limite_compensacao


def saldo_restante(servidor, data_inicial, data_final):
    """ retorna o saldo restante em segundos no período informado """
    contexto = Contexto(servidor=servidor, periodo_data_inicial=data_inicial, periodo_data_final=data_final)

    ch_restante_no_periodo = 0  # em segundos

    for dia_saldo_situacao in list(contexto.dias_saldos.values()):
        ch_restante_no_periodo += dia_saldo_situacao.saldo_qtd_restante

    return ch_restante_no_periodo


##################################################################################################################
