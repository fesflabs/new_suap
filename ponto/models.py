import datetime
import time
from collections import OrderedDict
from datetime import date, timedelta
from os.path import join

from django.conf import settings
from django.core.exceptions import ValidationError
from django.db.models import Q, Prefetch
from django.db.models.query import QuerySet
from django.db.models.signals import post_delete, post_save

from comum.models import Predio, PrestadorServico
from comum.utils import agrupar_em_pares, datas_entre, existe_conflito_entre_intervalos, formata_segundos, possui_horario_extra_noturno, tl, meses_entre, formata_segundos_h_min_seg
from djtools.db import models
from djtools.db.models import ModelPlus
from djtools.html.graficos import ColumnChart
from djtools.utils import save_session_cache, send_notification, djtools_max, djtools_min
from ponto.enums import TipoLiberacao
from rh.models import Funcao, Funcionario, Servidor, ServidorAfastamento, UnidadeOrganizacional, Viagem, Situacao

PRIVATE_ROOT_DIR = join(settings.MEDIA_PRIVATE, 'ponto')


class Frequencia(models.ModelPlus):
    INCONSISTENCIA_MENOR_JORNADA = 'INCONSISTENCIA_MENOR_JORNADA'
    INCONSISTENCIA_MAIOR_JORNADA = 'INCONSISTENCIA_MAIOR_JORNADA'
    INCONSISTENCIA_FALTA = 'INCONSISTENCIA_FALTA'
    INCONSISTENCIA_TEMPO_MAIOR_DEZ_HORAS = 'INCONSISTENCIA_TEMPO_MAIOR_DEZ_HORAS'
    INCONSISTENCIA_TRABALHO_FDS = 'INCONSISTENCIA_TRABALHO_FDS'
    INCONSISTENCIA_NUMERO_IMPAR_REGISTROS = 'INCONSISTENCIA_NUMERO_IMPAR_REGISTROS'

    DESCRICAO_INCONSISTENCIA = {
        INCONSISTENCIA_MENOR_JORNADA: "Tempo inferior ao expediente",
        INCONSISTENCIA_MAIOR_JORNADA: "Tempo excedente ao expediente",
        INCONSISTENCIA_FALTA: "Sem registro",
        INCONSISTENCIA_TEMPO_MAIOR_DEZ_HORAS: "Tempo de trabalho superior a 10h",
        INCONSISTENCIA_TRABALHO_FDS: "Tempo de trabalho no fim de semana",
        INCONSISTENCIA_NUMERO_IMPAR_REGISTROS: "Número incompleto de registros de frequências",
        "": "",
    }

    ###
    # situação das inconsistências
    # abono
    SITUACAO_INCONSISTENCIA_DESCONSIDERAR_ABONO = 'desconsiderar_abono'
    SITUACAO_INCONSISTENCIA_COM_ABONO = 'com_abono'
    SITUACAO_INCONSISTENCIA_SEM_ABONO = 'sem_abono'
    SITUACAO_INCONSISTENCIA_COM_OU_SEM_ABONO = 'com_ou_sem_abono'
    SITUACAO_INCONSISTENCIA_ABONO_CHOICES = [
        SITUACAO_INCONSISTENCIA_DESCONSIDERAR_ABONO,
        SITUACAO_INCONSISTENCIA_COM_ABONO,
        SITUACAO_INCONSISTENCIA_SEM_ABONO,
        SITUACAO_INCONSISTENCIA_COM_OU_SEM_ABONO,
    ]
    # débito de CH
    SITUACAO_INCONSISTENCIA_DESCONSIDERAR_DEBITO = 'desconsiderar_debito'
    SITUACAO_INCONSISTENCIA_COM_DEBITO_TODO_COMPENSADO = 'com_debito_total_compensado'
    SITUACAO_INCONSISTENCIA_COM_DEBITO_PARTE_COMPENSADO = 'com_debito_parte_compensado'
    SITUACAO_INCONSISTENCIA_COM_DEBITO_NADA_COMPENSADO = 'com_debito_nada_compensado'
    SITUACAO_INCONSISTENCIA_COM_DEBITO_PENDENTE = 'com_debito_nao_compensado'
    SITUACAO_INCONSISTENCIA_COM_DEBITO_COMPENSADO_OU_PENDENTE = 'com_debito_compensado_ou_nao'
    SITUACAO_INCONSISTENCIA_DEBITO_CHOICES = [
        SITUACAO_INCONSISTENCIA_DESCONSIDERAR_DEBITO,
        SITUACAO_INCONSISTENCIA_COM_DEBITO_TODO_COMPENSADO,
        SITUACAO_INCONSISTENCIA_COM_DEBITO_PARTE_COMPENSADO,
        SITUACAO_INCONSISTENCIA_COM_DEBITO_NADA_COMPENSADO,
        SITUACAO_INCONSISTENCIA_COM_DEBITO_PENDENTE,
        SITUACAO_INCONSISTENCIA_COM_DEBITO_COMPENSADO_OU_PENDENTE,
    ]

    vinculo = models.ForeignKeyPlus('comum.Vinculo', null=True, on_delete=models.CASCADE)
    horario = models.DateTimeField(db_index=True)
    maquina = models.ForeignKeyPlus('ponto.Maquina', on_delete=models.CASCADE)
    acao = models.CharField('Ação', max_length=1)
    online = models.BooleanField(default=True)
    ip = models.GenericIPAddressField(verbose_name='IP', null=True, blank=True)

    class History:
        disabled = True

    class Meta:
        db_table = 'frequencia'
        verbose_name = 'Frequência'
        verbose_name_plural = 'Frequências'

        unique_together = ('vinculo', 'horario')
        permissions = (
            ('pode_ver_frequencia_propria', "Pode ver frequência própria"),
            ('pode_ver_frequencias_enquanto_foi_chefe', "Pode ver frequência de quando foi chefe"),
            ('pode_ver_frequencia_campus', "Pode ver frequência de campus"),
            ('pode_ver_frequencia_todos', "Pode ver frequência de todos"),
            ('pode_ver_frequencia_estagiarios', "Pode ver frequências de estagiários"),
            ('pode_ver_frequencia_bolsistas', "Pode ver frequências de bolsistas"),
            ('pode_ver_frequencia_terceirizados_propria', "Pode ver frequência própria como terceirizado"),
            ('pode_ver_frequencia_terceirizados_setor', "Pode ver frequências de terceirizados"),
            ('pode_ver_frequencia_terceirizados_campus', "Pode ver frequências de terceirizados"),
            ('pode_ver_frequencia_terceirizados_todos', "Pode ver frequências de terceirizados"),
            ('pode_ver_frequencia_extra_noturna', "Pode ver frequência extra noturna"),
            ('pode_ver_frequencia_por_cargo', "Pode ver frequência por cargo"),
            ('eh_gerente_sistemico_ponto', "É gerente sistêmico de ponto"),
        )

    @classmethod
    def get_horario_extra_noturno(cls, par):
        extra_segundos = 0
        extra_minutos = 0
        horario_limite = 22
        excede_horario_limite = 23
        entrada = par[0]
        saida = par[1]
        if entrada.hour <= horario_limite and saida.hour >= excede_horario_limite:
            extra_minutos = 60
        elif entrada.hour == horario_limite and saida.hour == horario_limite:
            extra_minutos = saida.minute - entrada.minute
            extra_segundos = saida.second - entrada.second
        elif saida.hour == horario_limite:
            extra_minutos = saida.minute
            extra_segundos = saida.second
        total_segundos = extra_segundos + extra_minutos * 60
        return total_segundos

    @classmethod
    def insere_frequencia(cls, vinculo, maquina, horario=None, online=True, ip=None):
        '''
        Método que insere frequência para o funcionario. Usado pelo terminal.
        :param vinculo:
        :param maquina:
        :param horario:
        :param online:
        :return:
        '''
        if maquina.ativo and maquina.cliente_ponto:
            horario_frequencia = horario or datetime.datetime.now()
            frequencias_dia = cls.get_frequencias_por_data(vinculo, horario_frequencia.date())

            acao_default = (frequencias_dia.count() % 2) and 'S' or 'E'

            Frequencia.objects.get_or_create(vinculo=vinculo, horario=horario_frequencia, defaults={'maquina': maquina, 'acao': acao_default, 'online': online, 'ip': ip})

            # Nota: Organiza as frequências ajustando as ações no caso de vir uma
            # frequencia batida anteriormente a uma já importada
            reorganizar_acoes = frequencias_dia.filter(horario__gt=horario_frequencia).count()
            if reorganizar_acoes:
                for index, f in enumerate(frequencias_dia):
                    ordem = index + 1
                    if ordem % 2:
                        f.acao = 'E'
                    else:
                        f.acao = 'S'
                    f.save()

    @classmethod
    def get_frequencias_por_periodo(cls, vinculo, data_inicio, data_fim):
        '''
        Recupera Frequências por Período
        :param pessoa:
        :param data_inicio:
        :param data_fim:
        :return: Frequencias do Período
        '''
        return cls.objects.filter(
            vinculo=vinculo,
            horario__range=[datetime.datetime(data_inicio.year, data_inicio.month, data_inicio.day), datetime.datetime(data_fim.year, data_fim.month, data_fim.day, 23, 59, 59)],
        ).order_by('horario')

    @classmethod
    def get_frequencias_por_data(cls, vinculo, data):
        return cls.get_frequencias_por_periodo(vinculo, data, data)

    @classmethod
    def get_tempo_entre_frequencias(cls, frequencias):
        '''
        Recebe queryset de frequencias ou lista de horarios e retorna tempo em segundos
        :param frequencias:
        :return: tempo em segundos
        '''

        tempo = 0
        if isinstance(frequencias, QuerySet) and frequencias.exists():
            lista_frequencias = agrupar_em_pares(frequencias.values_list('horario', flat=True))
        elif frequencias:
            lista_frequencias = agrupar_em_pares([freq.horario if type(freq) == Frequencia else freq for freq in frequencias])
        else:
            return tempo

        for par in lista_frequencias:
            if len(par) == 2:
                delta = par[1] - par[0]
                segundos = delta.seconds
            else:
                segundos = 0
            tempo += segundos

        return tempo

    @classmethod
    def relatorio_frequencias_prestador(cls, vinculo, data_ini=None, data_fim=None, sabado=True, domingo=True):

        data_ini = data_ini or date.today()
        data_fim = data_fim or date.today()
        servidores = Servidor.objects.filter(cpf=vinculo.relacionamento.cpf)
        eh_servidor = servidores.exists()
        dados = OrderedDict()
        observacoes_data = []

        for dia in datas_entre(data_ini, data_fim, sabado, domingo):

            existe_conflitos = ""
            frequencias_dia_servidor = {}
            frequencias_prestador = Frequencia.get_frequencias_por_data(vinculo, dia).order_by('horario')
            tempo = 0
            if frequencias_prestador.exists():
                duracao = 0
                # Se a frequencia do prestador existe nós buscamos se existe a frequencia deste como servidor para saber se
                # Existem conflitos entre os horários"
                if eh_servidor:
                    frequencias_servidor = Frequencia.objects.none()

                    for servidor in servidores:
                        frequencias_servidor = Frequencia.get_frequencias_por_data(servidor.get_vinculo(), dia).order_by('horario')
                        frequencias_dia_servidor[servidor.matricula] = dict(frequencias=frequencias_servidor)

                        #                       Verificacao dos conflitos entre as frequencias
                        if frequencias_prestador.count() % 2 == 0:
                            if frequencias_servidor.count() % 2 == 0:
                                if existe_conflito_entre_intervalos(
                                    list(frequencias_prestador.values_list('horario', flat=True)) + list(frequencias_servidor.values_list('horario', flat=True))
                                ):
                                    existe_conflitos = "Há conflitos entre frequências do servidor/prestador de serviço."
                            else:
                                existe_conflitos = "Frequência como servidor em aberto."
                        else:
                            existe_conflitos = "Existe frequência de entrada mas não de saída do prestador."

                for par in agrupar_em_pares(frequencias_prestador.values_list('horario', flat=True)):
                    if len(par) == 2:
                        delta = par[1] - par[0]
                        segundos = delta.seconds
                    else:
                        segundos = 0
                    tempo += segundos

            observacoes = Observacao.objects.filter(vinculo=vinculo, data=dia)
            if observacoes.exists():
                observacoes_data.append(observacoes.distinct('data').get().data)

            liberacoes = Liberacao.filtrar_por_dia(vinculo=vinculo, data=dia)

            duracao = time.strftime('%H:%M:%S', time.gmtime(tempo))
            duracao_segundos = tempo

            dados[dia] = dict(
                dia=dia,
                horarios=frequencias_prestador,
                horarios_servidor=frequencias_dia_servidor,
                liberacoes=liberacoes,
                observacoes=observacoes,
                duracao=duracao,
                duracao_segundos=duracao_segundos,
                existe_conflitos=existe_conflitos,
            )
        datas_observacoes_extra = (
            Observacao.objects.filter(vinculo=vinculo, data__lte=data_fim, data__gte=data_ini).exclude(data__in=observacoes_data).values_list('data', flat=True).distinct()
        )
        if datas_observacoes_extra.exists():
            for data_obs in datas_observacoes_extra:
                observacoes_extra = Observacao.objects.filter(vinculo=vinculo, data=data_obs)
                dados[data_obs] = dict(
                    dia=data_obs,
                    horarios=None,
                    horarios_servidor=None,
                    liberacoes=None,
                    observacoes=observacoes_extra,
                    duracao=time.strftime('%H:%M:%S', time.gmtime(0)),
                    duracao_segundos=0,
                    existe_conflitos=None,
                )
            dados = OrderedDict(sorted(dados.items()))

        lista = list(dados.values())
        return lista

    @classmethod
    def relatorio_frequencias_setor(
        cls,
        setor,
        data_ini=None,
        data_fim=None,
        servidor_logado=None,
        so_inconsistentes=False,
        so_frequencias_em_que_era_chefe=False,
        so_inconsistentes_apenas_esta_inconsistencia=None,
        so_inconsistentes_situacao_abono=SITUACAO_INCONSISTENCIA_COM_OU_SEM_ABONO,
        so_inconsistentes_situacao_debito=SITUACAO_INCONSISTENCIA_COM_DEBITO_COMPENSADO_OU_PENDENTE,
        servidores=None
    ):

        ####################################################################################################
        # funcionarios = setor.get_servidores(recursivo).filter(excluido=False)
        ####################################################################################################

        # apenas os funcionários que, no período selecionado, estavam no setor informado
        # (OU em seus setores descendentes)
        dias_em_que_foi_chefe_setor = []
        if servidor_logado.eh_servidor:
            for funcao_servidor in servidor_logado.historico_funcao(data_ini, data_fim).filter(setor_suap__isnull=False, funcao__codigo__in=Funcao.get_codigos_funcao_chefia()):
                if setor in funcao_servidor.setor_suap.descendentes:
                    if funcao_servidor.data_inicio_funcao < data_ini:
                        funcao_servidor.data_inicio_funcao = data_ini
                    if not funcao_servidor.data_fim_funcao or funcao_servidor.data_fim_funcao > data_fim:
                        funcao_servidor.data_fim_funcao = data_fim
                    dias_em_que_foi_chefe_setor += datas_entre(funcao_servidor.data_inicio_funcao, funcao_servidor.data_fim_funcao)

        lista = []
        for servidor in servidores:
            dias_liberado_frequencia = servidor.get_dias_liberado_frequencia_periodo(data_ini, data_fim)
            relatorio_ponto = cls.relatorio_ponto_pessoa(
                servidor.get_vinculo(),
                data_ini,
                data_fim,
                so_inconsistentes=so_inconsistentes,
                dias_em_que_foi_chefe_setor=dias_em_que_foi_chefe_setor,
                so_frequencias_em_que_era_chefe=so_frequencias_em_que_era_chefe,
                trata_compensacoes=True,
                dias_liberado_frequencia=dias_liberado_frequencia,
                so_inconsistentes_apenas_esta_inconsistencia=so_inconsistentes_apenas_esta_inconsistencia,
                so_inconsistentes_situacao_abono=so_inconsistentes_situacao_abono,
                so_inconsistentes_situacao_debito=so_inconsistentes_situacao_debito,
            )
            lista.append(relatorio_ponto)

        return lista

    @classmethod
    def get_inconsistencias(cls, vinculo, dia, jornada_trabalho_hrs=None, contexto_compensacao=None, frequencias=None, tolerancia_15min=True):
        """
            :return lista com as inconsistências que estão definidas em constantes no model Frequencia
        """
        # não há inconsistência hoje ou no futuro
        if dia >= datetime.date.today():
            return []

        sub_instance = vinculo.relacionamento

        # chamado 89283
        # "frequências inconsistentes" e "compensação de horários"
        if not jornada_trabalho_hrs and not contexto_compensacao:
            from ponto.compensacao import Contexto

            contexto_compensacao = Contexto(servidor=sub_instance, periodo_data_inicial=dia, periodo_data_final=dia)

        data_inicio_exercicio_na_instituicao = None
        if type(sub_instance) == Servidor:
            if sub_instance.data_inicio_exercicio_na_instituicao:
                data_inicio_exercicio_na_instituicao = sub_instance.data_inicio_exercicio_na_instituicao

            if not jornada_trabalho_hrs:
                # carga horária exigida para o dia em questão via compensação
                jornada_trabalho_hrs = contexto_compensacao.get_dia(dia).carga_horaria_qtd / 3600

        # não há inconsistência se anterior a data de início de exercício na instituição
        if data_inicio_exercicio_na_instituicao and dia < data_inicio_exercicio_na_instituicao:
            return []

        if not frequencias:
            frequencias = cls.get_frequencias_por_data(vinculo, dia).order_by('horario')

        incosistencia = []
        is_fim_de_semana = dia.weekday() >= 5

        tolerancia_15min_em_segundos = 0
        if tolerancia_15min:
            tolerancia_15min_em_segundos = 900

        # há registro de ponto?
        if frequencias:
            # no fim de semana?
            if is_fim_de_semana:
                incosistencia = [cls.INCONSISTENCIA_TRABALHO_FDS]

            # seg-sex?
            else:
                tempo = cls.get_tempo_entre_frequencias(frequencias)

                # registros ponto contabilizou ZERO ?
                if tempo == 0:
                    incosistencia = [cls.INCONSISTENCIA_FALTA]

                # registros ponto contabilizou trabalho superior a 10h ?
                elif tempo >= 36000:
                    incosistencia = [cls.INCONSISTENCIA_TEMPO_MAIOR_DEZ_HORAS]

                # CH trabalhada INFERIOR a jornada de trabalho exigida ?
                # tolerância: 15min
                elif tempo < (jornada_trabalho_hrs * 60 * 60 - tolerancia_15min_em_segundos):
                    incosistencia = [cls.INCONSISTENCIA_MENOR_JORNADA]

                # CH trabalhada SUPERIOR a jornada de trabalho exigida ?
                # tolerância: 15min
                elif (tempo > (jornada_trabalho_hrs * 60 * 60 + tolerancia_15min_em_segundos)) and ((jornada_trabalho_hrs * 60 * 60) != 0):
                    incosistencia = [cls.INCONSISTENCIA_MAIOR_JORNADA]

            # chamado 114661
            is_numero_impar_de_registros = len(frequencias) % 2 == 1
            if is_numero_impar_de_registros:
                incosistencia += [cls.INCONSISTENCIA_NUMERO_IMPAR_REGISTROS]

        # não há registro ponto seg-sex?
        elif not is_fim_de_semana:
            incosistencia = [cls.INCONSISTENCIA_FALTA]

        if incosistencia:
            if cls.existe_liberacao_inconsistencia(vinculo, dia):
                incosistencia = []

        return incosistencia

    @classmethod
    def existe_liberacao_inconsistencia(cls, vinculo, dia):
        # férias?
        if 'ferias' in settings.INSTALLED_APPS:
            from ferias.models import Ferias

            if Ferias.pessoa_estava_de_ferias_no_dia(vinculo.relacionamento, dia):
                return True

        # afastamento SIAPE?
        if ServidorAfastamento.get_afastamentos(vinculo.relacionamento, dia, dia).exists():
            return True

        # afastamento RH?
        if Afastamento.buscar_afastamento_periodo(vinculo, dia, dia).exists():
            return True

        # viagens?
        if Viagem.get_viagens(vinculo.relacionamento, dia, dia).exists():
            return True

        # liberações
        sub_instance = vinculo.relacionamento
        if type(sub_instance) == Servidor:
            historico_setor = sub_instance.historico_setor_suap(dia, dia)
            uo = None
            if sub_instance.setor:
                uo = sub_instance.setor.uo
            if historico_setor.exists():
                uo = historico_setor[0].setor.uo

            # liberações, exceto parciais ?
            liberacoes = Liberacao.liberacoes_por_uo(dia, dia, uo)
            liberacoes_parciais = liberacoes.filter(tipo=TipoLiberacao.get_numero(TipoLiberacao.LIBERACAO_PARCIAL))
            if liberacoes.exists() and not liberacoes_parciais.exists():
                return True

            # liberações recorrentes?
            liberacoes_recorrentes_no_mes = Liberacao.liberacoes_recorrentes_por_uo(dia, dia, uo)
            if liberacoes_recorrentes_no_mes.exists():
                for liberacao in liberacoes_recorrentes_no_mes:
                    liberacao.data_inicio = date(dia.year, liberacao.data_inicio.month, liberacao.data_inicio.day)
                    liberacao.data_fim = date(dia.year, liberacao.data_fim.month, liberacao.data_fim.day)
                    if liberacao.data_inicio <= dia <= liberacao.data_fim:
                        return True

        return False

    @classmethod
    def tem_saida_antecipada(cls, vinculo, dia, jornada_trabalho_hrs=None, contexto_compensacao=None, frequencias=None):
        inconsistencia = cls.get_inconsistencias(
            vinculo,
            dia,
            jornada_trabalho_hrs=jornada_trabalho_hrs,
            contexto_compensacao=contexto_compensacao,
            frequencias=frequencias,
            tolerancia_15min=False,  # desconsidera a tolerância de 15 minutos
        )
        tem_saida_antecipada = cls.INCONSISTENCIA_MENOR_JORNADA in inconsistencia
        return tem_saida_antecipada

    @classmethod
    def relatorio_noturno(cls, cargo_emprego, uo, data_ini=None, data_fim=None, sabado=True, domingo=True):
        """
        Listagem de frequência extra noturna.
        """

        # Excluindo professores substitutos de pesquisa de docentes
        if cargo_emprego == 'professor_substituto_temporario':
            servidores = Servidor.objects.substitutos_ou_temporarios().filter(setor__uo=uo)
        elif cargo_emprego == 'docente':
            servidores = Servidor.objects.docentes_permanentes().filter(setor__uo=uo)
        elif cargo_emprego == 'tecnico_administrativo':
            servidores = Servidor.objects.tecnicos_administrativos().filter(setor__uo=uo)

        lista = []
        #       A partir da versao 1.6 do django substituir por objects.filter(horario__hour=23)
        servidores = servidores.filter(
            id__in=Frequencia.objects.filter(horario__range=[data_ini, data_fim + timedelta(1)])
            .extra(where=["EXTRACT('hour' from horario) >= '22' "])
            .values_list('vinculo__pessoa__pk', flat=True)
        )
        for servidor in servidores:
            lista.append(cls.relatorio_ponto_pessoa(servidor.get_vinculo(), data_ini, data_fim, sabado, domingo, so_horario_extra_noturno=True))
        return lista

    @classmethod
    def relatorio_terceirizados(cls, terceirizado=None, setor=None, data_ini=None, data_fim=None, sabado=True, domingo=True, recursivo=True, ocupacao=None):
        """
        Retorna uma lista de dicionários com as frequências de terceirizados da Instituição.

        """
        terceirizados = PrestadorServico.objects.filter(excluido=False, setor__isnull=False, ativo=True)
        if terceirizado:
            terceirizados = PrestadorServico.objects.filter(id=terceirizado.id, ativo=True)

        elif setor:
            if recursivo:
                terceirizados = terceirizados.filter(setor__in=setor.descendentes)
            else:
                terceirizados = terceirizados.filter(setor=setor)

        if ocupacao:
            terceirizados = terceirizados.filter(ocupacaoprestador__ocupacao=ocupacao)
        lista = []
        for terceirizado in terceirizados.distinct('nome'):
            frequencias = cls.relatorio_frequencias_prestador(terceirizado.get_vinculo(), data_ini, data_fim, sabado, domingo)
            if frequencias:
                total_periodo = 0
                for frequencia in frequencias:
                    total_periodo += frequencia['duracao_segundos']
                dic_totalperiodo = formata_segundos(total_periodo)
                total_periodo = '%(h)sh %(m)smin %(s)sseg' % dic_totalperiodo
                dado = dict(funcionario=terceirizado, frequencias=frequencias, total_periodo=total_periodo)
                lista.append(dado)

        return lista

    @classmethod
    def relatorio_cargo_emprego(cls, cargo_emprego, data_ini=None, data_fim=None, sabado=True, domingo=True):
        servidores = Servidor.objects.filter(cargo_emprego=cargo_emprego, excluido=False)
        lista = []
        for servidor in servidores:
            relatorio_ponto = cls.relatorio_ponto_pessoa(servidor.get_vinculo(), data_ini, data_fim, False, False, True)
            if relatorio_ponto['dias']:  # tem relatório de ponto?
                lista.append(relatorio_ponto)

        return lista

    @classmethod
    def relatorio_ponto_pessoa_novo(cls, vinculo, servidor_logado, data_ini=None, data_fim=None, escopo='chefe'):
        servidor = vinculo.relacionamento
        setores_funcionario = servidor.historico_setor_suap(data_ini, data_fim)
        dias_liberado_frequencia = servidor.get_dias_liberado_frequencia_periodo(data_ini, data_fim)
        dias_em_que_foi_chefe_setor = []
        dias_em_que_estava_no_campus = []
        for setor_funcionario in setores_funcionario:
            data_inicio_setor_referencia = djtools_max(setor_funcionario.data_inicio_no_setor, data_ini)
            data_fim_setor_referencia = djtools_min(setor_funcionario.data_fim_no_setor, data_fim)
            if servidor_logado.setor.uo == setor_funcionario.setor.uo:
                if not dias_em_que_estava_no_campus:
                    dias_em_que_estava_no_campus = datas_entre(data_inicio_setor_referencia, data_fim_setor_referencia)
                else:
                    dias_em_que_estava_no_campus += datas_entre(data_inicio_setor_referencia, data_fim_setor_referencia)
            for funcao_servidor in servidor_logado.historico_funcao(data_ini, data_fim).filter(setor_suap__isnull=False, funcao__codigo__in=Funcao.get_codigos_funcao_chefia()):
                if setor_funcionario.setor in funcao_servidor.setor_suap.descendentes:
                    funcao_servidor.data_inicio_funcao = djtools_max(funcao_servidor.data_inicio_funcao, data_inicio_setor_referencia)
                    funcao_servidor.data_fim_funcao = djtools_max(funcao_servidor.data_fim_funcao, data_fim_setor_referencia)
                    dias_em_que_foi_chefe_setor += datas_entre(funcao_servidor.data_inicio_funcao, funcao_servidor.data_fim_funcao)
        kwargs = {}
        if escopo == 'chefe':
            kwargs['so_frequencias_em_que_era_chefe'] = True
        elif escopo == 'campus':
            kwargs['dias_em_que_estava_no_campus'] = dias_em_que_estava_no_campus

        return cls.relatorio_ponto_pessoa(
            vinculo,
            data_ini,
            data_fim,
            trata_compensacoes=True,
            dias_em_que_foi_chefe_setor=dias_em_que_foi_chefe_setor,
            dias_liberado_frequencia=dias_liberado_frequencia,
            **kwargs,
        )

    @classmethod
    def relatorio_ponto_pessoa(
        cls,
        vinculo,
        data_ini=None,
        data_fim=None,
        sabado=True,
        domingo=True,
        so_inconsistentes=False,
        dias_em_que_foi_chefe_setor=[],
        so_horario_extra_noturno=False,
        show_grafico=True,
        so_frequencias_em_que_era_chefe=False,
        dias_em_que_estava_no_campus=[],
        trata_compensacoes=False,
        dias_liberado_frequencia=[],
        trata_inconsistencias=True,
        so_inconsistentes_apenas_esta_inconsistencia=None,
        so_inconsistentes_situacao_abono=SITUACAO_INCONSISTENCIA_COM_OU_SEM_ABONO,
        so_inconsistentes_situacao_debito=SITUACAO_INCONSISTENCIA_COM_DEBITO_COMPENSADO_OU_PENDENTE,
    ):
        relatorio_pessoa = OrderedDict()
        data_ini = data_ini or date.today()
        data_fim = data_fim or date.today()
        funcionario = vinculo.relacionamento
        relatorio_pessoa['funcionario'] = funcionario
        data_fim_instituicao = None
        data_inicio_instituicao = None
        if funcionario.eh_servidor:
            data_inicio_instituicao = funcionario.data_inicio_exercicio_na_instituicao
            data_fim_instituicao = funcionario.data_fim_servico_na_instituicao

        dias_dict = OrderedDict()
        semanas_dict = OrderedDict()
        dias_periodo = datas_entre(data_ini, data_fim)
        for dia in dias_periodo:
            dias_dict[dia] = dict(dia=dia)

        if data_fim_instituicao and data_fim_instituicao < data_fim:
            for dia in datas_entre(data_fim_instituicao, data_fim):
                if dias_dict.get(dia):
                    dias_dict[dia]['excluido'] = f'Excluído desde o dia {data_fim_instituicao.strftime("%d/%m/%Y")}'
        if data_inicio_instituicao and data_inicio_instituicao > data_ini:
            for dia in datas_entre(data_ini, data_inicio_instituicao):
                if dias_dict.get(dia):
                    dias_dict[dia]['excluido'] = f'Início do vinculo a partir do dia {data_inicio_instituicao.strftime("%d/%m/%Y")}'

        if funcionario.eh_servidor:
            afastamentos_siape = ServidorAfastamento.get_afastamentos(funcionario, data_ini, data_fim)
            afastamentos_siape = afastamentos_siape.select_related('afastamento')
            afastamentos_siape = afastamentos_siape.only('afastamento', 'data_inicio', 'data_termino')

            for afastamento_siape in afastamentos_siape:
                for dia in datas_entre(afastamento_siape.data_inicio, afastamento_siape.data_termino):
                    if dia in dias_periodo:
                        dias_dict[dia]['liberado'] = True
                        if not dias_dict[dia].get('afastamentos_siape'):
                            dias_dict[dia]['afastamentos_siape'] = [afastamento_siape.afastamento]
                        else:
                            dias_dict[dia]['afastamentos_siape'].append(afastamento_siape.afastamento)

            afastamentos_siape = Afastamento.buscar_afastamento_periodo(vinculo, data_ini, data_fim).select_related('tipo')

            for afastamento in afastamentos_siape:
                for dia in datas_entre(afastamento.data_ini, afastamento.data_fim):
                    if dia in dias_periodo:
                        dias_dict[dia]['liberado'] = True
                        if not dias_dict[dia].get('afastamentos_rh'):
                            dias_dict[dia]['afastamentos_rh'] = [afastamento]
                        else:
                            dias_dict[dia]['afastamentos_rh'].append(afastamento)

            # Calculando os Viagens do SCDP
            # Verificar quais as situações que tem que ser filtradas aqui.
            for viagem_servidor in Viagem.get_viagens(vinculo.relacionamento, data_ini, data_fim).only('data_inicio_viagem', 'data_fim_viagem', 'servidor', 'objetivo_viagem', 'situacao'):
                for dia in datas_entre(viagem_servidor.data_inicio_viagem, viagem_servidor.data_fim_viagem):
                    if dia in dias_periodo:
                        dias_dict[dia]['liberado'] = True
                        if not dias_dict[dia].get('viagens_scdp'):
                            dias_dict[dia]['viagens_scdp'] = [viagem_servidor]
                        else:
                            dias_dict[dia]['viagens_scdp'].append(viagem_servidor)

            if 'ferias' in settings.INSTALLED_APPS:
                from ferias.models import Ferias, ParcelaFerias

                ferias_dados = Ferias.get_ferias_no_periodo(vinculo.relacionamento, data_ini, data_fim)
                ferias_dados = ferias_dados.only('pk')
                ferias_dados = ferias_dados.prefetch_related(Prefetch('parcelaferias_set', queryset=ParcelaFerias.objects.all().only('data_inicio', 'data_fim')))

                for ferias in ferias_dados:
                    for dia_ferias in list(ferias.get_dias_ferias().keys()):
                        if dia_ferias in dias_periodo:
                            dias_dict[dia_ferias]['liberado'] = True
                            if not dias_dict[dia_ferias].get('ferias'):
                                dias_dict[dia_ferias]['ferias'] = "Férias"

            for liberacao in Liberacao.filtrar_por_periodo(vinculo, data_ini, data_fim).only('tipo', 'data_inicio', 'data_fim', 'descricao'):
                if liberacao.tipo == TipoLiberacao.get_numero(TipoLiberacao.FERIADO_RECORRENTE):
                    for ano in range(data_ini.year, data_fim.year + 1):
                        liberacao.data_inicio = date(ano, liberacao.data_inicio.month, liberacao.data_inicio.day)
                        liberacao.data_fim = date(ano, liberacao.data_fim.month, liberacao.data_fim.day)
                        for dia in datas_entre(liberacao.data_inicio, liberacao.data_fim):
                            if dia in dias_periodo:
                                dias_dict[dia]['liberado'] = True
                                if not dias_dict[dia].get('liberacoes'):
                                    dias_dict[dia]['liberacoes'] = [liberacao]
                                else:
                                    dias_dict[dia]['liberacoes'].append(liberacao)
                else:
                    if not liberacao.data_fim:
                        liberacao.data_fim = liberacao.data_inicio
                    for dia in datas_entre(liberacao.data_inicio, liberacao.data_fim):
                        if dia in dias_periodo:
                            dias_dict[dia]['liberado'] = True
                            if not dias_dict[dia].get('liberacoes'):
                                dias_dict[dia]['liberacoes'] = [liberacao]
                            else:
                                dias_dict[dia]['liberacoes'].append(liberacao)

            for abono in AbonoChefia.objects.filter(vinculo_pessoa=vinculo, data__lte=data_fim, data__gte=data_ini):
                dias_dict[abono.data]['abono_chefia'] = abono

        for observacao in Observacao.objects.filter(vinculo=vinculo, data__lte=data_fim, data__gte=data_ini):
            if dias_dict[observacao.data].get('observacoes'):
                dias_dict[observacao.data]['observacoes'].append(observacao)
            else:
                dias_dict[observacao.data]['observacoes'] = [observacao]

        for anexo in DocumentoAnexo.objects.filter(vinculo=vinculo, data__lte=data_fim, data__gte=data_ini):
            if dias_dict[anexo.data].get('anexos'):
                dias_dict[anexo.data]['anexos'].append(anexo)
            else:
                dias_dict[anexo.data]['anexos'] = [anexo]

        for historico_funcao in funcionario.historico_funcao().filter(funcao__codigo__in=Funcao.get_codigos_funcao_chefia()):
            data_fim_referencia = historico_funcao.data_fim_funcao if historico_funcao.data_fim_funcao else data_fim
            for dia in datas_entre(historico_funcao.data_inicio_funcao, data_fim_referencia):
                if dia in dias_periodo:
                    dias_dict[dia]['tem_funcao_chefia'] = True

        for frequencia in Frequencia.get_frequencias_por_periodo(vinculo, data_ini, data_fim).select_related('maquina'):
            if dias_dict[frequencia.horario.date()].get('horarios'):
                dias_dict[frequencia.horario.date()]['horarios'].append(frequencia)
            else:
                dias_dict[frequencia.horario.date()]['horarios'] = [frequencia]

            if dias_dict[frequencia.horario.date()].get('horarios_dia'):
                dias_dict[frequencia.horario.date()]['horarios_dia'].append(frequencia.horario)
            else:
                dias_dict[frequencia.horario.date()]['horarios_dia'] = [frequencia.horario]
        for dia_foi_chefe in dias_em_que_foi_chefe_setor:
            if dias_dict.get(dia_foi_chefe):
                dias_dict[dia_foi_chefe]['pode_abonar_dia'] = True

        for dia_liberado_frequencia in dias_liberado_frequencia:
            if dias_dict.get(dia_liberado_frequencia):
                dias_dict[dia_liberado_frequencia]['dia_liberado_frequencia'] = True

        tempo_total_horas_trabalhadas = 0
        tempo_total_carga_horaria = 0
        tempo_total_hora_extra_noturna = 0
        tempo_abonado_sem_compensacao = 0
        tempo_trabalho_remoto = 0
        tempo_abonado_para_compensacao = 0
        tempo_nao_abonado = 0
        hora_extra_nao_justificada = 0
        hora_extra_justificada = 0
        hora_extra_para_compensacao_carga_horaria = 0
        trabalho_fds_permitido_como_hora_extra = 0
        trabalho_fds_permitido_para_compensacao_carga_horaria = 0
        trabalho_fds_nao_permitido = 0

        if funcionario.eh_servidor:
            # jornadas de trabalho do servidor
            # são instâncias de rh.JornadaTrabalho + rh.JornadaTrabalhoInternaCargaHorariaReduzida
            jornadas_servidor = funcionario.get_jornadas_periodo_dict(data_ini, data_fim)

        tem_horarios_inferiores = False
        tem_horarios_excedentes = False

        ###
        # contexto de compensação (inconsistências, saldos, débitos, compensações)
        if so_inconsistentes or trata_compensacoes or trata_inconsistencias:
            from ponto.compensacao import Contexto

            contexto_compensacao = Contexto(servidor=funcionario, periodo_data_inicial=data_ini, periodo_data_final=data_fim)
        semana_count = 1
        semanas_dict[semana_count] = OrderedDict()
        semanas_dict[semana_count]['ch_exigida'] = 0
        semanas_dict[semana_count]['ch_valida'] = 0
        semanas_dict[semana_count]['ch_segundos'] = 0
        for dia in datas_entre(data_ini, data_fim):
            if dia != data_ini and dia.weekday() == 0:
                semana_count += 1
                semanas_dict[semana_count] = OrderedDict()
                semanas_dict[semana_count]['ch_exigida'] = 0
                semanas_dict[semana_count]['ch_valida'] = 0
                semanas_dict[semana_count]['ch_segundos'] = 0

            frequencias_dia = []
            if dias_dict[dia].get('horarios'):
                frequencias_dia = dias_dict[dia].get('horarios')

            # Esse horarios_frequencias substitui o values_list da queryset
            horarios_frequencias_dia = dias_dict[dia].get('horarios_dia')
            hora_extra_noturna = 0
            tempo = 0
            if frequencias_dia and horarios_frequencias_dia:
                for par in agrupar_em_pares(horarios_frequencias_dia):
                    if len(par) == 2:
                        if possui_horario_extra_noturno(par):
                            hora_extra_noturna = cls.get_horario_extra_noturno(par)
                tempo = cls.get_tempo_entre_frequencias(horarios_frequencias_dia)

            # máximo 10 horas por dia (36000 segundos)
            tempo_bruto = tempo
            if tempo > 36000:
                tempo = 36000

            ###
            # determina se o dia será ou não exibido
            mostrar_dia = True

            if so_frequencias_em_que_era_chefe or dias_em_que_estava_no_campus:
                if dia not in dias_em_que_foi_chefe_setor and dia not in dias_em_que_estava_no_campus:
                    mostrar_dia = False

            tem_acoes_ponto = any([frequencias_dia, dias_dict[dia].get('observacoes'), dias_dict[dia].get('abono_chefia'), dias_dict[dia].get('anexos')])
            if not tem_acoes_ponto and (dia.weekday() >= 5 or dias_dict[dia].get('excluido')):
                mostrar_dia = False

            if mostrar_dia and so_inconsistentes:
                tem_inconsistencia = False
                if dias_dict.get(dia):
                    inconsistencias_do_dia = Frequencia.get_inconsistencias(vinculo, dia, contexto_compensacao=contexto_compensacao, frequencias=horarios_frequencias_dia)

                    if inconsistencias_do_dia:
                        tem_inconsistencia = True

                        if so_inconsistentes_apenas_esta_inconsistencia:
                            tem_inconsistencia = tem_inconsistencia and so_inconsistentes_apenas_esta_inconsistencia in inconsistencias_do_dia

                        if so_inconsistentes_situacao_abono not in cls.SITUACAO_INCONSISTENCIA_ABONO_CHOICES:
                            so_inconsistentes_situacao_abono = cls.SITUACAO_INCONSISTENCIA_COM_OU_SEM_ABONO

                        if not so_inconsistentes_situacao_abono == cls.SITUACAO_INCONSISTENCIA_DESCONSIDERAR_ABONO:
                            dia_tem_abono = dias_dict.get(dia, {}).get('abono_chefia', False)

                            tem_inconsistencia = tem_inconsistencia and any(
                                [
                                    so_inconsistentes_situacao_abono == cls.SITUACAO_INCONSISTENCIA_COM_OU_SEM_ABONO,
                                    dia_tem_abono and so_inconsistentes_situacao_abono == cls.SITUACAO_INCONSISTENCIA_COM_ABONO,
                                    not dia_tem_abono and so_inconsistentes_situacao_abono == cls.SITUACAO_INCONSISTENCIA_SEM_ABONO,
                                ]
                            )

                        if so_inconsistentes_situacao_debito not in cls.SITUACAO_INCONSISTENCIA_DEBITO_CHOICES:
                            so_inconsistentes_situacao_debito = cls.SITUACAO_INCONSISTENCIA_COM_DEBITO_COMPENSADO_OU_PENDENTE

                        if not so_inconsistentes_situacao_debito == cls.SITUACAO_INCONSISTENCIA_DESCONSIDERAR_DEBITO:
                            dia_debito = contexto_compensacao.get_dia(dia)
                            dia_debito_restante = dia_debito.debito_qtd_restante
                            dia_tem_debito_pendente = dia_debito_restante > 0
                            dia_tem_debito_total = dia_debito_restante == dia_debito.debito_qtd_considerado

                            tem_inconsistencia = tem_inconsistencia and any(
                                [
                                    so_inconsistentes_situacao_debito == cls.SITUACAO_INCONSISTENCIA_COM_DEBITO_COMPENSADO_OU_PENDENTE,
                                    dia_tem_debito_pendente
                                    and not dia_tem_debito_total
                                    and so_inconsistentes_situacao_debito == cls.SITUACAO_INCONSISTENCIA_COM_DEBITO_PARTE_COMPENSADO,
                                    dia_tem_debito_pendente
                                    and dia_tem_debito_total
                                    and so_inconsistentes_situacao_debito == cls.SITUACAO_INCONSISTENCIA_COM_DEBITO_NADA_COMPENSADO,
                                    not dia_tem_debito_pendente and so_inconsistentes_situacao_debito == cls.SITUACAO_INCONSISTENCIA_COM_DEBITO_TODO_COMPENSADO,
                                ]
                            )
                    else:
                        tem_inconsistencia = False

                # remove o dia caso não tenha inconsistência
                if not tem_inconsistencia:
                    mostrar_dia = False

            if mostrar_dia and so_horario_extra_noturno:
                if dias_dict.get(dia):
                    if not dias_dict[dia].get('hora_extra_noturna'):
                        mostrar_dia = False

            if mostrar_dia:
                semanas_dict[semana_count]['min_dia'] = min(dia, semanas_dict[semana_count]['min_dia']) if semanas_dict[semana_count].get('min_dia') else dia
                semanas_dict[semana_count]['max_dia'] = max(dia, semanas_dict[semana_count]['max_dia']) if semanas_dict[semana_count].get('max_dia') else dia
            else:
                dias_dict.pop(dia)
                continue  # processa o próximo dia

            ################################################################################################
            # obtém a carga horária do servidor no dia em questão
            # Para docentes é usada a regra da carga-horária / 2
            ################################################################################################
            if funcionario.eh_servidor:
                try:

                    jornada_trabalho_servidor_diaria = jornadas_servidor[dia].get_jornada_trabalho_diaria()
                    #
                    if dias_dict[dia].get('tem_funcao_chefia'):
                        jornada_trabalho_servidor_diaria = 8
                    elif funcionario.eh_docente:
                        jornada_trabalho_servidor_diaria = jornada_trabalho_servidor_diaria / 2
                except Exception:
                    jornada_trabalho_servidor_diaria = 0
            else:
                jornada_trabalho_servidor_diaria = 0

            dias_dict[dia]['carga_horaria_do_dia'] = jornada_trabalho_servidor_diaria
            dias_dict[dia]['semana'] = semana_count

            carga_horaria_dias_segundos = jornada_trabalho_servidor_diaria * 60 * 60

            dias_dict[dia]['carga_horaria_do_dia_h'] = formata_segundos(carga_horaria_dias_segundos)['h']
            dias_dict[dia]['carga_horaria_do_dia_m'] = formata_segundos(carga_horaria_dias_segundos)['m']

            ################################################################################################

            duracao = time.strftime('%H:%M:%S', time.gmtime(tempo))
            duracao_bruto = time.strftime('%H:%M:%S', time.gmtime(tempo_bruto))
            duracao_segundos = tempo
            duracao_segundos_bruto = tempo_bruto

            dias_dict[dia]['duracao'] = duracao
            dias_dict[dia]['duracao_bruto'] = duracao_bruto
            dias_dict[dia]['duracao_segundos'] = duracao_segundos
            dias_dict[dia]['duracao_segundos_bruto'] = duracao_segundos_bruto
            dias_dict[dia]['acao_abono_inconsistencia'] = None

            ###
            # exibe a descrição das inconsistências
            tem_inconsistencia_inferior = False
            tem_inconsistencia_superior = False
            if trata_inconsistencias:
                tipo_inconsistencia = cls.get_inconsistencias(vinculo, dia, contexto_compensacao=contexto_compensacao, frequencias=horarios_frequencias_dia)

                if tipo_inconsistencia:
                    tipo_inconsistencia = tipo_inconsistencia[0]
                else:
                    tipo_inconsistencia = ''

                informacoes_inconsistencia = cls.DESCRICAO_INCONSISTENCIA[tipo_inconsistencia]
                if tipo_inconsistencia:
                    if tipo_inconsistencia in [
                        Frequencia.INCONSISTENCIA_MENOR_JORNADA,
                        Frequencia.INCONSISTENCIA_FALTA,
                        Frequencia.INCONSISTENCIA_MAIOR_JORNADA,
                        Frequencia.INCONSISTENCIA_TEMPO_MAIOR_DEZ_HORAS,
                        Frequencia.INCONSISTENCIA_NUMERO_IMPAR_REGISTROS,
                    ]:
                        if tipo_inconsistencia in [Frequencia.INCONSISTENCIA_MENOR_JORNADA, Frequencia.INCONSISTENCIA_FALTA]:
                            tem_inconsistencia_inferior = True
                        elif tipo_inconsistencia in [Frequencia.INCONSISTENCIA_MAIOR_JORNADA, Frequencia.INCONSISTENCIA_TEMPO_MAIOR_DEZ_HORAS]:
                            tem_inconsistencia_superior = True
                        dias_dict[dia]['informacoes_registro_info'] = informacoes_inconsistencia
                    else:
                        dias_dict[dia]['informacoes_registro'] = informacoes_inconsistencia

                    if AbonoChefia.CHOICES_POR_INCONSISTENCIAS[tipo_inconsistencia] == AbonoChefia.ACAO_ABONO_FALTA_CHOICES:
                        dias_dict[dia]['acao_abono_inconsistencia'] = 'inferior'
                    elif AbonoChefia.CHOICES_POR_INCONSISTENCIAS[tipo_inconsistencia] == AbonoChefia.ACAO_ABONO_TEMPO_MAIOR_DEZ_HORAS_CHOICES:
                        dias_dict[dia]['acao_abono_inconsistencia'] = 'excedente'

            dias_dict[dia]['hora_extra_noturna'] = hora_extra_noturna

            if dias_dict[dia].get('abono_chefia') and not any(
                [
                    dias_dict[dia].get('liberacoes'),
                    dias_dict[dia].get('afastamentos_rh'),
                    dias_dict[dia].get('afastamentos_siape'),
                    dias_dict[dia].get('ferias'),
                    dias_dict[dia].get('viagens_scdp'),
                    dias_dict[dia].get('dia_liberado_frequencia'),
                ]
            ):
                abono = dias_dict[dia]['abono_chefia']
                if abono:
                    tem_inconsistencia_superior = False
                    tem_inconsistencia_inferior = False
                if abono.acao_abono == AbonoChefia.ABONADO_SEM_COMPENSACAO:
                    tempo_abonado_sem_compensacao += jornada_trabalho_servidor_diaria * 60 * 60 - duracao_segundos
                    dias_dict[dia]['duracao_computada'] = time.strftime('%H:%M:%S', time.gmtime(jornada_trabalho_servidor_diaria * 60 * 60))

                if abono.acao_abono == AbonoChefia.TRABALHO_REMOTO:
                    tempo_trabalho_remoto += jornada_trabalho_servidor_diaria * 60 * 60 - duracao_segundos
                    dias_dict[dia]['duracao_computada'] = time.strftime('%H:%M:%S', time.gmtime(jornada_trabalho_servidor_diaria * 60 * 60))

                elif abono.acao_abono == AbonoChefia.ABONADO_COM_COMPENSACAO:
                    tempo_abonado_para_compensacao += jornada_trabalho_servidor_diaria * 60 * 60 - duracao_segundos
                    dias_dict[dia]['duracao_computada'] = duracao

                elif abono.acao_abono == AbonoChefia.NAO_ABONADO:
                    tempo_nao_abonado += jornada_trabalho_servidor_diaria * 60 * 60 - duracao_segundos
                    dias_dict[dia]['duracao_computada'] = duracao

                elif abono.acao_abono == AbonoChefia.HORA_EXTRA_NAO_JUSTIFICADA:
                    hora_extra_nao_justificada += duracao_segundos - jornada_trabalho_servidor_diaria * 60 * 60
                    dias_dict[dia]['duracao_computada'] = time.strftime('%H:%M:%S', time.gmtime(jornada_trabalho_servidor_diaria * 60 * 60))

                elif abono.acao_abono == AbonoChefia.HORA_EXTRA_JUSTIFICADA:
                    hora_extra_justificada += duracao_segundos - jornada_trabalho_servidor_diaria * 60 * 60
                    dias_dict[dia]['duracao_computada'] = duracao

                elif abono.acao_abono == AbonoChefia.HORA_EXTRA_PARA_COMPENSACAO_CARGA_HORARIA:
                    hora_extra_para_compensacao_carga_horaria += duracao_segundos - jornada_trabalho_servidor_diaria * 60 * 60
                    dias_dict[dia]['duracao_computada'] = duracao

                elif abono.acao_abono == AbonoChefia.TRABALHO_FDS_PERMITIDO_PARA_COMPENSACAO_CARGA_HORARIA:
                    trabalho_fds_permitido_para_compensacao_carga_horaria += duracao_segundos
                    dias_dict[dia]['duracao_computada'] = duracao

                elif abono.acao_abono == AbonoChefia.TRABALHO_FDS_PERMITIDO_COMO_HORA_EXTRA:
                    trabalho_fds_permitido_como_hora_extra += duracao_segundos
                    dias_dict[dia]['duracao_computada'] = duracao

                elif abono.acao_abono == AbonoChefia.TRABALHO_FDS_NAO_PERMITIDO:
                    trabalho_fds_nao_permitido += duracao_segundos
                    dias_dict[dia]['duracao_computada'] = time.strftime('%H:%M:%S', time.gmtime(0))
            if tem_inconsistencia_inferior:
                tem_horarios_inferiores = tem_inconsistencia_inferior
            if tem_inconsistencia_superior:
                tem_horarios_excedentes = tem_inconsistencia_superior

            if not dias_dict[dia].get('dia_liberado_frequencia'):
                tempo_total_hora_extra_noturna += hora_extra_noturna
                tempo_total_horas_trabalhadas += tempo

            tem_liberacao_de_ponto_no_dia = False
            if dias_dict[dia].get('liberacoes'):
                for liberacao in dias_dict[dia].get('liberacoes'):
                    if liberacao.tipo != TipoLiberacao.get_numero(TipoLiberacao.EVENTO):
                        tem_liberacao_de_ponto_no_dia = True

            tem_liberacao_parcial_de_ponto_no_dia = False
            ch_horaria_maxima_exigida = 0  # em horas
            dias_dict[dia]['liberacoes_exceto_parciais'] = []
            for liberacao in dias_dict[dia].get('liberacoes', []):
                if liberacao.tipo == TipoLiberacao.get_numero(TipoLiberacao.LIBERACAO_PARCIAL):
                    tem_liberacao_parcial_de_ponto_no_dia = True
                    ###
                    dias_dict[dia]['liberado'] = False
                    ###
                    ch_horaria_maxima_exigida = liberacao.ch_maxima_exigida  # em horas
                else:
                    dias_dict[dia]['liberacoes_exceto_parciais'].append(liberacao)

            semanas_dict[semana_count]['ch_valida'] += duracao_segundos - tempo_nao_abonado - hora_extra_nao_justificada - trabalho_fds_nao_permitido
            semanas_dict[semana_count]['ch_segundos'] += duracao_segundos_bruto
            dias_dict[dia]['duracao_segundos_bruto'] = duracao_segundos_bruto
            if dia.weekday() < 5 and dia <= date.today():
                if not (
                    tem_liberacao_de_ponto_no_dia
                    or dias_dict[dia].get('ferias')
                    or dias_dict[dia].get('afastamentos_siape')
                    or dias_dict[dia].get('afastamentos_rh')
                    or dias_dict[dia].get('viagens_scdp')
                    or dias_dict[dia].get('dia_liberado_frequencia')
                ):
                    tempo_total_carga_horaria += jornada_trabalho_servidor_diaria * 60 * 60
                    semanas_dict[semana_count]['ch_exigida'] += jornada_trabalho_servidor_diaria * 60 * 60

                elif tem_liberacao_parcial_de_ponto_no_dia:
                    jornada_do_dia = jornada_trabalho_servidor_diaria * 60 * 60
                    ch_horaria_maxima_exigida = ch_horaria_maxima_exigida * 60 * 60
                    if jornada_do_dia > ch_horaria_maxima_exigida:
                        tempo_total_carga_horaria += ch_horaria_maxima_exigida
                        semanas_dict[semana_count]['ch_exigida'] += ch_horaria_maxima_exigida
                    else:
                        tempo_total_carga_horaria += jornada_do_dia
                        semanas_dict[semana_count]['ch_exigida'] += jornada_do_dia
        relatorio_pessoa['dias'] = list(dias_dict.values())
        relatorio_pessoa['semanas'] = semanas_dict

        relatorio_pessoa['total_periodo'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(tempo_total_horas_trabalhadas)
        relatorio_pessoa['total_periodo_carga_horaria'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(tempo_total_carga_horaria)
        if tempo_total_hora_extra_noturna:
            relatorio_pessoa['total_hora_extra_noturna'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(tempo_total_hora_extra_noturna)

        if tempo_abonado_sem_compensacao or tempo_abonado_para_compensacao or tempo_nao_abonado or tempo_trabalho_remoto:
            relatorio_pessoa['total_abonado_sem_compensacao'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(tempo_abonado_sem_compensacao)
            relatorio_pessoa['total_trabalho_remoto'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(tempo_trabalho_remoto)
            relatorio_pessoa['total_abonado_para_compensacao'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(tempo_abonado_para_compensacao)
            relatorio_pessoa['total_nao_abonado'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(tempo_nao_abonado)

        if hora_extra_nao_justificada or hora_extra_justificada or hora_extra_para_compensacao_carga_horaria:
            relatorio_pessoa['total_hora_extra_nao_justificada'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(hora_extra_nao_justificada)
            relatorio_pessoa['total_hora_extra_justificada'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(hora_extra_justificada)
            relatorio_pessoa['total_hora_extra_para_compensacao_carga_horaria'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(hora_extra_para_compensacao_carga_horaria)

        if trabalho_fds_permitido_para_compensacao_carga_horaria or trabalho_fds_permitido_como_hora_extra or trabalho_fds_nao_permitido:
            relatorio_pessoa['total_trabalho_fds_permitido_para_compensacao_carga_horaria'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(
                trabalho_fds_permitido_para_compensacao_carga_horaria
            )
            relatorio_pessoa['total_trabalho_fds_permitido_como_hora_extra'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(trabalho_fds_permitido_como_hora_extra)
            relatorio_pessoa['total_trabalho_fds_nao_permitido'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(trabalho_fds_nao_permitido)

        tempo_total_valido = (
            tempo_total_horas_trabalhadas + tempo_abonado_sem_compensacao + tempo_trabalho_remoto - trabalho_fds_nao_permitido - hora_extra_nao_justificada - tempo_nao_abonado
        )

        relatorio_pessoa['total_tempo_valido'] = '%(h)sh %(m)smin %(s)sseg' % formata_segundos(tempo_total_valido)
        saldo = tempo_total_valido - tempo_total_carga_horaria
        saldo_descricao_grafico = 'Saldo'
        saldo_descricao_totais = 'Saldo de horas para o período informado. Equivale ao tempo total válido ' 'menos o total da carga horária devida.'

        # situações no gráfico
        total_debito_pendente = 0
        total_debito_pendente_grafico_descricao = ''
        total_saldo_restante = 0
        total_saldo_restante_grafico_descricao = ''

        relatorio_pessoa['trata_compensacoes'] = trata_compensacoes

        if trata_compensacoes:
            ##################################################################################
            # SALDOS, DÉBITOS E COMPENSAÇÕES no período informado
            from ponto.compensacao import formatar_segundos

            total_debito = 0
            total_debito_reposto = 0
            total_debito_pendente = 0
            total_saldo = 0
            total_saldo_utilizado = 0
            total_saldo_restante = 0
            total_debito_desconsiderado = 0
            mensagens_debito_desconsiderado = []
            dias_debito_desconsiderado = []
            total_saldo_desconsiderado = 0
            mensagens_saldo_desconsiderado = []
            dias_saldo_desconsiderado = []

            for data in datas_entre(data_ini, data_fim):
                if data in dias_dict:
                    situacao_dia = contexto_compensacao.get_dia(data)

                    log_ch_desconsiderada = situacao_dia.get_log_ch_desconsiderada

                    if situacao_dia.is_debito:
                        debito_restante = situacao_dia.debito_qtd_restante

                        dias_dict[data]['compensacao'] = {
                            'is_debito': True,
                            'ch_paga_percentual': situacao_dia.debito_qtd_percentual_reposicao,
                            'ch_restante_a_pagar': formatar_segundos(debito_restante),
                            'ch_restante_a_pagar_is_maior_que_zero': debito_restante > 0,
                            'ch_restante_a_pagar_is_menor_que_15min': debito_restante < 900,
                            'acompanhamentos_compensacoes_especificas': situacao_dia.acompanhamentos_envolvidos_contendo_o_dia_como_debito,
                        }

                        total_debito += situacao_dia.debito_qtd_considerado
                        total_debito_reposto += situacao_dia.debito_qtd_reposto
                        total_debito_pendente += situacao_dia.debito_qtd_restante

                        if log_ch_desconsiderada:
                            total_debito_desconsiderado += situacao_dia.debito_qtd_desconsiderado
                            mensagens_debito_desconsiderado.append(log_ch_desconsiderada)
                            dias_debito_desconsiderado.append(situacao_dia.dia)

                    elif situacao_dia.is_saldo:
                        dias_dict[data]['compensacao'] = {'is_saldo': True}

                        total_saldo += situacao_dia.saldo_qtd_considerado
                        total_saldo_utilizado += situacao_dia.saldo_qtd_utilizado
                        total_saldo_restante += situacao_dia.saldo_qtd_restante

                        if log_ch_desconsiderada:
                            total_saldo_desconsiderado += situacao_dia.saldo_qtd_desconsiderado
                            mensagens_saldo_desconsiderado.append(log_ch_desconsiderada)
                            dias_saldo_desconsiderado.append(situacao_dia.dia)

            relatorio_pessoa['totais_compensacao'] = dict(
                total_debito=formatar_segundos(total_debito, True),
                total_debito_reposto=formatar_segundos(total_debito_reposto, True),
                total_debito_pendente=formatar_segundos(total_debito_pendente, True),
                total_saldo=formatar_segundos(total_saldo, True),
                total_saldo_utilizado=formatar_segundos(total_saldo_utilizado, True),
                total_saldo_restante=formatar_segundos(total_saldo_restante, True),
                total_debito_reposto_is_zero=total_debito_reposto == 0,
                total_debito_pendente_is_zero=total_debito_pendente == 0,
                total_saldo_restante_is_zero=total_saldo_restante == 0,
                total_debito_desconsiderado=formatar_segundos(total_debito_desconsiderado, True),
                total_debito_desconsiderado_motivos=mensagens_debito_desconsiderado,
                total_debito_desconsiderado_dias=dias_debito_desconsiderado,
                total_debito_desconsiderado_is_zero=total_debito_desconsiderado == 0,
                total_saldo_desconsiderado=formatar_segundos(total_saldo_desconsiderado, True),
                total_saldo_desconsiderado_motivos=mensagens_saldo_desconsiderado,
                total_saldo_desconsiderado_dias=dias_saldo_desconsiderado,
                total_saldo_desconsiderado_is_zero=total_saldo_desconsiderado == 0,
            )

            if total_debito_pendente > 0:
                total_debito_pendente_grafico_descricao = 'Débito pendente'

            if total_saldo_restante > 0:
                total_saldo_restante_grafico_descricao = 'Saldo restante'

        relatorio_pessoa['saldo'] = ("" if saldo >= 0 else "-") + '%(h)sh %(m)smin %(s)sseg' % formata_segundos(saldo)
        relatorio_pessoa['saldo_descricao_grafico'] = saldo_descricao_grafico
        relatorio_pessoa['saldo_descricao_totais'] = saldo_descricao_totais
        relatorio_pessoa['tem_horarios_excedentes'] = tem_horarios_excedentes
        relatorio_pessoa['tem_horarios_inferiores'] = tem_horarios_inferiores

        if show_grafico:
            serie = list()

            serie.append(
                {'name': 'Carga Horária Exigida ', 'y': tempo_total_carga_horaria / 3600.0, 'y_format': formata_segundos_h_min_seg(tempo_total_carga_horaria), 'color': '#77a1e5'}
            )

            serie.append(
                {
                    'name': 'Total de Horas Trabalhadas',
                    'y': tempo_total_horas_trabalhadas / 3600.0,
                    'y_format': formata_segundos_h_min_seg(tempo_total_horas_trabalhadas),
                    'color': '#77a1e5',
                }
            )

            if tempo_abonado_sem_compensacao:
                serie.append(
                    {
                        'name': 'Total abonado sem necessidade de compensação ',
                        'y': tempo_abonado_sem_compensacao / 3600.0,
                        'y_format': formata_segundos_h_min_seg(tempo_abonado_sem_compensacao),
                        'color': '#a6c96a',
                    }
                )
            if tempo_trabalho_remoto:
                serie.append(
                    {'name': 'Total Trabalho Remoto', 'y': tempo_trabalho_remoto / 3600.0, 'y_format': formata_segundos_h_min_seg(tempo_trabalho_remoto), 'color': '#a6c96a'}
                )

            if tempo_nao_abonado:
                serie.append({'name': 'Total não abonado', 'y': tempo_nao_abonado / 3600.0, 'y_format': formata_segundos_h_min_seg(tempo_nao_abonado), 'color': '#c42525'})

            if tempo_abonado_para_compensacao:
                serie.append(
                    {
                        'name': 'Total abonado para compensação',
                        'y': tempo_abonado_para_compensacao / 3600.0,
                        'y_format': formata_segundos_h_min_seg(tempo_abonado_para_compensacao),
                        'color': '#f28f43',
                    }
                )

            if hora_extra_justificada:
                serie.append(
                    {'name': 'Hora extra justificada', 'y': hora_extra_justificada / 3600.0, 'y_format': formata_segundos_h_min_seg(hora_extra_justificada), 'color': '#a6c96a'}
                )

            if hora_extra_nao_justificada:
                serie.append(
                    {
                        'name': 'Hora extra não justificada',
                        'y': hora_extra_nao_justificada / 3600.0,
                        'y_format': formata_segundos_h_min_seg(hora_extra_nao_justificada),
                        'color': '#f28f43',
                    }
                )

            if hora_extra_para_compensacao_carga_horaria:
                serie.append(
                    {
                        'name': 'Hora extra para compensação de carga horária',
                        'y': hora_extra_para_compensacao_carga_horaria / 3600.0,
                        'y_format': formata_segundos_h_min_seg(hora_extra_para_compensacao_carga_horaria),
                        'color': '#a6c96a',
                    }
                )

            if trabalho_fds_permitido_para_compensacao_carga_horaria:
                serie.append(
                    {
                        'name': 'Trabalho no fim de semana permitido para compensação de carga horária',
                        'y': trabalho_fds_permitido_para_compensacao_carga_horaria / 3600.0,
                        'y_format': formata_segundos_h_min_seg(trabalho_fds_permitido_para_compensacao_carga_horaria),
                        'color': '#77a1e5',
                    }
                )

            if trabalho_fds_permitido_como_hora_extra:
                serie.append(
                    {
                        'name': 'Trabalho no fim de semana permitido como hora extra',
                        'y': trabalho_fds_permitido_como_hora_extra / 3600.0,
                        'y_format': formata_segundos_h_min_seg(trabalho_fds_permitido_como_hora_extra),
                        'color': '#77a1e5',
                    }
                )

            if trabalho_fds_nao_permitido:
                serie.append(
                    {
                        'name': 'Trabalho no fim de semana não permitido',
                        'y': trabalho_fds_nao_permitido / 3600.0,
                        'y_format': formata_segundos_h_min_seg(trabalho_fds_nao_permitido),
                        'color': '#c42525',
                    }
                )

            # situações
            cor_barra_red = '#c42525'
            cor_barra_green = '#a6c96a'

            if total_debito_pendente > 0:
                serie.append(
                    {
                        'name': '{}'.format(total_debito_pendente_grafico_descricao),
                        'y': total_debito_pendente * -1 / 3600.0,
                        'y_format': formata_segundos_h_min_seg(total_debito_pendente * -1),
                        'color': cor_barra_red,
                    }
                )

            if total_saldo_restante > 0:
                serie.append(
                    {
                        'name': '{}'.format(total_saldo_restante_grafico_descricao),
                        'y': total_saldo_restante / 3600.0,
                        'y_format': formata_segundos_h_min_seg(total_saldo_restante),
                        'color': cor_barra_green,
                    }
                )

            grafico = ColumnChart(
                'grafico_%s' % vinculo.pessoa.pk,
                title='Frequências %s' % vinculo.pessoa.nome,
                subtitle='Contabilização das horas no período',
                data=serie,
                minPointLength=5,
                showDataLabels=True,
                tooltip=dict(pointFormat='<b>{point.y_format}</b>'),
                format='{point.y_format}',
            )
            grafico.plotOptions['column'] = {'shadow': False}

            relatorio_pessoa['grafico_frequencias'] = grafico

        relatorio_pessoa['eh_chefe_periodo'] = False

        if len(dias_em_que_foi_chefe_setor) > 0:
            relatorio_pessoa['eh_chefe_periodo'] = True

        relatorio_pessoa['qtd_dias_periodo'] = (data_fim - data_ini).days + 1

        return relatorio_pessoa

    @staticmethod
    def segundos_para_time(segundos=0):
        """ segundos para Time """
        if segundos >= 0:
            minutos, segundos = divmod(segundos, 60)
            horas, minutos = divmod(minutos, 60)
            #
            return datetime.time(hour=horas, minute=minutos, second=segundos)
        return datetime.time(second=0)

    @staticmethod
    def time_para_segundos(time=None):
        """ Time para segundos """
        if time:
            return time.hour * 60 * 60 + time.minute * 60 + time.second
        #
        return 0


class VersaoTerminal(models.ModelPlus):
    numero = models.CharField(max_length=5, verbose_name='Número de Versão', unique=True)

    def __str__(self):
        return self.numero


class Maquina(models.ModelPlus):
    descricao = models.CharField(max_length=30, verbose_name='Descrição')
    ip = models.GenericIPAddressField(unique=True, verbose_name='IP')
    porta_servico = models.PositiveIntegerField(
        null=True, blank=True, verbose_name='Porta Serviço', help_text='Porta do serviço disponibilizado pela máquina. ' 'Use caso seja servidor de impressão.'
    )
    ativo = models.BooleanField(default=None, verbose_name='Ativa', null=True, help_text='Caso seja desconhecido, a máquina ainda não foi aceita pelo administrador do SUAP.')
    cliente_cadastro_impressao_digital = models.BooleanField(default=False, verbose_name='Cadastro de Impressões Digitais')
    cliente_chaves = models.BooleanField(default=False, verbose_name='Terminal de Chaves')
    cliente_ponto = models.BooleanField(default=False, verbose_name='Terminal de Ponto Eletrônico')
    cliente_refeitorio = models.BooleanField(default=False, verbose_name='Terminal de Refeitório')
    servidor_impressao = models.BooleanField(default=False, verbose_name='Servidor de Impressão', help_text='A máquina será utilizada para impressão de comprovantes do protocolo.')
    texto_final_impressao = models.TextField(
        null=True,
        blank=True,
        help_text='Preencha esse campo caso tenha marcado a opção anterior e deseja que algum texto seja impresso ao final do comprovante. Ex: Ou ligue para  (XX) XXXX-XXX',
    )
    uo = models.ForeignKeyPlus(UnidadeOrganizacional, null=True, verbose_name='Campus', on_delete=models.CASCADE)
    observacao = models.TextField('Observação', null=True, blank=True)
    usuarios = models.ManyToManyField(
        'comum.User', blank=True, verbose_name='Usuários', help_text='Usuários que poderão usar os serviços da máquina. ' 'Use caso seja servidor de impressão.'
    )
    ultimo_log = models.DateTimeField(null=True, blank=True)
    predios = models.ManyToManyField(Predio, blank=True)
    versao_terminal = models.ForeignKeyPlus(VersaoTerminal, null=True, blank=True, verbose_name='Versão do Terminal', on_delete=models.CASCADE)

    class History:
        ignore_fields = ('ultimo_log',)

    class Meta:
        db_table = 'maquina'
        verbose_name = 'Máquina'
        verbose_name_plural = 'Máquinas'

    def clean(self):
        if (
            (self.cliente_refeitorio and self.cliente_ponto)
            or (self.cliente_refeitorio and self.cliente_chaves)
            or (self.cliente_refeitorio and self.cliente_cadastro_impressao_digital)
        ):
            raise ValidationError('Terminal de refeitório não pode ser configurado com módulo de ' 'cadastro/chaves/ponto.')

    def __str__(self):
        return self.descricao

    def get_atividade(self):
        ultimo_registro = self.ultimo_log
        velho = datetime.datetime.today() - timedelta(1)
        return ultimo_registro < velho

    @classmethod
    def get_maquinas_impressao(cls, user=None):
        user = user or tl.get_user()
        if not user.has_perm('protocolo.pode_imprimir_comprovante'):
            return Maquina.objects.none()
        return user.maquina_set.filter(servidor_impressao=True, ativo=True)


class MaquinaLog(models.ModelPlus):
    """
    A classe serve para guardar as últimas operações das máquinas.
    """

    SUCESSO = 0
    ERRO = 1
    ALERTA = 2

    STATUS_MAQUINA_LOG_CHOICES = [[SUCESSO, 'Sucesso'], [ERRO, 'Erro'], [ALERTA, 'Alerta']]

    maquina = models.ForeignKeyPlus(Maquina, verbose_name='Máquina', on_delete=models.CASCADE)
    status = models.PositiveIntegerFieldPlus('Status', choices=STATUS_MAQUINA_LOG_CHOICES, default=SUCESSO)
    operacao = models.CharField('Operação', max_length=255)
    mensagem = models.TextField('Mensagem', null=True, blank=True)
    horario = models.DateTimeField(auto_now=True, verbose_name='Horário')

    class History:
        disabled = True

    class Meta:
        ordering = ['maquina', 'operacao']
        verbose_name = 'Log de Máquina'
        verbose_name_plural = 'Logs de Máquinas'

    def save(self, *args, **kargs):
        super().save(*args, **kargs)
        self.maquina.ultimo_log = self.horario
        self.maquina.save()


class Liberacao(models.ModelPlus):
    uo = models.ForeignKeyPlus(
        UnidadeOrganizacional, null=True, blank=True, on_delete=models.CASCADE, verbose_name='Unidade Organizacional', help_text='Define onde será aplicada a liberação.'
    )
    data_inicio = models.DateFieldPlus('Data Início', db_index=True)
    data_fim = models.DateFieldPlus('Data Fim', null=True, db_index=True)
    descricao = models.TextField('Descrição', max_length=200)
    tipo = models.PositiveIntegerField('Tipo Liberação', default=0, choices=TipoLiberacao.get_choices())
    ch_maxima_exigida = models.IntegerField(
        'Carga horária máxima exigida pela instituição (em horas) ',
        default=0,
        help_text='Somente para o tipo \'{}\'. É a carga ' 'horária máxima que será exigida no(s) dia(s) ' 'do período informado.'.format(TipoLiberacao.LIBERACAO_PARCIAL),
    )

    class Meta:
        verbose_name = 'Liberação'
        verbose_name_plural = 'Liberações'

    def __str__(self):
        return self.descricao

    @classmethod
    def filtrar_por_dia(cls, vinculo, data):
        return cls.filtrar_por_periodo(vinculo, data, data)

    @classmethod
    def liberacoes_por_uo(cls, data_inicio, data_fim, uo=None):
        liberacoes = cls.objects.filter(data_inicio__lte=data_fim, data_fim__gte=data_inicio, uo__isnull=True) | cls.objects.filter(
            data_inicio__gte=data_inicio, data_inicio__lte=data_fim, uo__isnull=True
        )
        if uo:
            liberacoes = (
                liberacoes
                | cls.objects.filter(data_inicio__lte=data_fim, data_fim__gte=data_inicio, uo=uo)
                | cls.objects.filter(data_inicio__gte=data_inicio, data_inicio__lte=data_fim, uo=uo)
            )
        return liberacoes

    @classmethod
    def liberacoes_recorrentes_por_uo(cls, data_inicio, data_fim, uo=None):
        meses = meses_entre(data_inicio, data_fim)
        qs_liberacao = cls.objects.filter(tipo=TipoLiberacao.get_numero(TipoLiberacao.FERIADO_RECORRENTE))
        qs_liberacao_por_uo = cls.objects.none()
        qs_liberacao_sem_uo = (
            qs_liberacao.filter(uo__isnull=True)
            .filter(Q(data_inicio__month__in=meses) | Q(data_fim__month__in=meses))
            .filter(data_inicio__lte=data_fim)  # o início da liberação deve ser anterior ou igual a data final do período
        )
        if uo:
            qs_liberacao_por_uo = (
                qs_liberacao.filter(uo=uo)
                .filter(Q(data_inicio__month__in=meses) | Q(data_fim__month__in=meses))
                .filter(data_inicio__lte=data_fim)  # o início da liberação deve ser anterior ou igual a data final do período
            )

        qs_liberacao = qs_liberacao_sem_uo | qs_liberacao_por_uo
        if data_inicio == data_fim:
            qs_liberacao = qs_liberacao.filter(data_inicio__day=data_inicio.day)

        return qs_liberacao

    @classmethod
    def filtrar_por_periodo_por_uo(cls, data_inicio, data_fim, uo=None):
        return (cls.liberacoes_por_uo(data_inicio, data_fim, uo) | cls.liberacoes_recorrentes_por_uo(data_inicio, data_fim, uo)).distinct()

    @classmethod
    def filtrar_por_periodo(cls, vinculo, data_inicio, data_fim):
        if data_inicio > data_fim:
            return cls.objects.none()

        if isinstance(vinculo.relacionamento, Servidor):
            servidor = vinculo.relacionamento
            historico_setor = servidor.historico_setor_suap(data_inicio, data_fim)
            if historico_setor.exists():
                liberacoes = cls.objects.none()
                for setor_historico in historico_setor:
                    if setor_historico.data_inicio_no_setor <= data_inicio:
                        data_inicio_referencia = data_inicio
                    else:
                        data_inicio_referencia = setor_historico.data_inicio_no_setor

                    if not setor_historico.data_fim_no_setor or (setor_historico.data_fim_no_setor and setor_historico.data_fim_no_setor >= data_fim):
                        data_fim_referencia = data_fim
                    else:
                        data_fim_referencia = setor_historico.data_fim_no_setor
                    liberacoes = liberacoes | cls.filtrar_por_periodo_por_uo(data_inicio_referencia, data_fim_referencia, setor_historico.setor.uo)

                if not data_fim_referencia or data_fim_referencia and data_fim_referencia < data_fim:
                    if vinculo.relacionamento.setor:
                        liberacoes = liberacoes | cls.filtrar_por_periodo_por_uo(data_fim_referencia, data_fim, vinculo.relacionamento.setor.uo)
                return liberacoes
            else:
                historico_setor = servidor.historico_setor_siape(data_inicio, data_fim)
                if historico_setor.exists():
                    liberacoes = cls.objects.none()
                    for setor_hist in historico_setor:
                        uo_servidor = setor_hist.setor_exercicio.uo and setor_hist.setor_exercicio.uo.equivalente
                        if setor_hist.data_inicio_setor_lotacao and setor_hist.data_inicio_setor_lotacao <= data_inicio:
                            data_inicio_referencia = data_inicio
                        else:
                            data_inicio_referencia = setor_hist.data_inicio_setor_lotacao

                        if not setor_hist.data_fim_setor_lotacao or setor_hist.data_fim_setor_lotacao and setor_hist.data_fim_setor_lotacao >= data_fim:
                            data_fim_referencia = data_fim
                        else:
                            data_fim_referencia = setor_hist.data_fim_setor_lotacao
                        liberacoes = liberacoes | cls.filtrar_por_periodo_por_uo(data_inicio_referencia, data_fim_referencia, uo_servidor)

                    if not data_fim_referencia or data_fim_referencia and data_fim_referencia < data_fim:
                        if vinculo.relacionamento.setor:
                            liberacoes = liberacoes | cls.filtrar_por_periodo_por_uo(data_fim_referencia, data_fim, vinculo.relacionamento.setor.uo)
                    return liberacoes

        if vinculo.relacionamento.setor:
            return cls.filtrar_por_periodo_por_uo(data_inicio, data_fim, vinculo.relacionamento.setor.uo)
        else:
            return cls.filtrar_por_periodo_por_uo(data_inicio, data_fim)

    @classmethod
    def get_liberacoes_calendario(cls, uo, ano, mes=None):
        return cls.get_liberacoes_calendario_nao_recorrentes(uo, ano, mes) + cls.get_liberacoes_calendario_recorrentes(uo, ano, mes)

    @classmethod
    def get_liberacoes_calendario_nao_recorrentes(cls, uo, ano, mes=None):
        qs_liberacoes_campus = Liberacao.objects.filter(uo=uo).exclude(tipo=TipoLiberacao.get_numero(TipoLiberacao.FERIADO_RECORRENTE))
        qs_liberacoes = Liberacao.objects.filter(uo=None).exclude(tipo=TipoLiberacao.get_numero(TipoLiberacao.FERIADO_RECORRENTE))
        if mes:
            liberacoes_campus = qs_liberacoes_campus.filter(data_inicio__year=ano, data_inicio__month=mes) | qs_liberacoes_campus.filter(data_fim__year=ano, data_fim__month=mes)
            liberacoes = qs_liberacoes.filter(data_inicio__year=ano, data_inicio__month=mes) | qs_liberacoes.filter(data_fim__year=ano, data_fim__month=mes)
        else:
            liberacoes_campus = qs_liberacoes_campus.filter(data_inicio__year=ano) | qs_liberacoes_campus.filter(data_fim__year=ano)
            liberacoes = qs_liberacoes.filter(data_inicio__year=ano) | qs_liberacoes.filter(data_fim__year=ano)

        return list((liberacoes | liberacoes_campus).order_by('data_inicio'))

    @classmethod
    def get_liberacoes_calendario_recorrentes(cls, uo, ano, mes=None):
        feriados_recorrentes_campus = Liberacao.objects.filter(uo=uo, tipo=TipoLiberacao.get_numero(TipoLiberacao.FERIADO_RECORRENTE))
        feriados_recorrentes = Liberacao.objects.filter(uo=None, tipo=TipoLiberacao.get_numero(TipoLiberacao.FERIADO_RECORRENTE))
        liberacoes = []
        for liberacao in (feriados_recorrentes | feriados_recorrentes_campus).order_by('data_inicio'):
            data = '{}-{}-{}'.format(str(liberacao.data_inicio.day), str(liberacao.data_inicio.month), str(ano))
            if liberacao.data_inicio == liberacao.data_fim or liberacao.data_fim is None:
                liberacao.data_inicio = datetime.datetime.strptime(data, "%d-%m-%Y").date()
                liberacao.data_fim = datetime.datetime.strptime(data, "%d-%m-%Y").date()
            else:
                liberacao.data_inicio = datetime.datetime.strptime(data, "%d-%m-%Y").date()
                liberacao.data_fim = datetime.datetime.strptime(data, "%d-%m-%Y").date()
            liberacoes.append(liberacao)
        return liberacoes

    def get_ch_maxima_exigida_display(self):
        if self.tipo == TipoLiberacao.get_numero(TipoLiberacao.LIBERACAO_PARCIAL):
            return '{}'.format(self.ch_maxima_exigida)
        return 'Não aplicado.'

    def get_liberacao_css(self):
        css = 'Não aplicado.'
        if self.tipo in [0, 5]:
            css = 'extra'
        elif self.tipo == 1:
            css = 'evento'
        elif self.tipo == 2:
            css = 'recesso'
        elif self.tipo in [3, 4]:
            css = 'feriado'
        return css


class Observacao(models.ModelPlus):
    """
    Representa as observações cadastradas pelo funcionário.
    Estas NÃO sairão no relatório de frequências oficial.
    """

    vinculo = models.ForeignKeyPlus('comum.Vinculo', verbose_name='Vínculo', editable=False, on_delete=models.CASCADE)
    data = models.DateFieldPlus(db_index=True, verbose_name='Data da Frequência')
    descricao = models.TextField(verbose_name='Observação')
    data_cadastro = models.DateTimeField(auto_now_add=True, editable=False, null=True, verbose_name='Data de Cadastro')

    class Meta:
        verbose_name = 'Observação'
        verbose_name_plural = 'Observações'

    def __str__(self):
        return 'Observação do Dia: {}'.format(self.data.strftime('%d/%m/%Y'))


class DocumentoAnexo(models.ModelPlus):
    vinculo = models.ForeignKeyPlus('comum.Vinculo', editable=False, on_delete=models.CASCADE)
    data = models.DateFieldPlus(db_index=True)
    descricao = models.TextField(max_length=200, verbose_name='Descrição')
    anexo = models.PrivateFileField(
        verbose_name='Anexo', upload_to='ponto/anexos', filetypes=['pdf', 'jpeg', 'jpg', 'png'], help_text='O formato do arquivo deve ser ".pdf", ".jpeg", ".jpg" ou ".png"'
    )

    class Meta:
        verbose_name = 'Anexo'
        verbose_name_plural = 'Anexos'

    def __str__(self):
        return self.descricao

    def delete(self, *args, **kwargs):
        self.anexo.delete()
        super().delete(*args, **kwargs)


class AbonoChefia(ModelPlus):
    """
    Representa se a chefia abona ou não uma anomalia no registro de ponto assim como sua justificativa/observacao
    do ponto cadastrada pelo funcionário.
    """

    NAO_ABONADO = 0
    ABONADO_COM_COMPENSACAO = 1
    ABONADO_SEM_COMPENSACAO = 2
    TRABALHO_REMOTO = 9

    HORA_EXTRA_NAO_JUSTIFICADA = 3
    HORA_EXTRA_JUSTIFICADA = 4
    HORA_EXTRA_PARA_COMPENSACAO_CARGA_HORARIA = 7

    TRABALHO_FDS_NAO_PERMITIDO = 5
    TRABALHO_FDS_PERMITIDO_PARA_COMPENSACAO_CARGA_HORARIA = 6
    TRABALHO_FDS_PERMITIDO_COMO_HORA_EXTRA = 8

    NUMERO_IMPAR_REGISTROS_NAO_PERMITIDO = 9

    ACAO_ABONO_FALTA_CHOICES = [
        [ABONADO_COM_COMPENSACAO, 'Abonado com compensação de horário'],
        [ABONADO_SEM_COMPENSACAO, 'Abonado sem compensação de horário'],
        [TRABALHO_REMOTO, 'Trabalho Remoto'],
        [NAO_ABONADO, 'Não abonado'],
    ]
    ACAO_ABONO_TEMPO_MAIOR_DEZ_HORAS_CHOICES = [  # na verdade refere-se ao tempo superior a carga horária do dia
        [
            HORA_EXTRA_PARA_COMPENSACAO_CARGA_HORARIA,  # apenas para efeitos de carga horária excedente
            'Tempo de trabalho excedente para compensação de carga-horária (até o limite de 10h de trabalho por dia)',
        ],
        [HORA_EXTRA_JUSTIFICADA, 'Hora extra justificada (até o limite de 10h de trabalho por dia)'],  # apenas para efeitos de remuneração
        [HORA_EXTRA_NAO_JUSTIFICADA, 'Hora extra não justificada'],
    ]
    ACAO_ABONO_TRABALHO_FDS_CHOICES = [
        [
            TRABALHO_FDS_PERMITIDO_PARA_COMPENSACAO_CARGA_HORARIA,  # apenas para efeitos de carga horária excedente
            'Trabalho no fim de semana autorizado para compensação de carga horária',
        ],
        [TRABALHO_FDS_PERMITIDO_COMO_HORA_EXTRA, 'Trabalho no fim de semana autorizado como hora extra'],  # apenas para efeitos de remuneração
        [TRABALHO_FDS_NAO_PERMITIDO, 'Trabalho no fim de semana não justificado/autorizado'],
    ]
    ACAO_ABONO_SAIDA_ANTECIPADA_CHOICES = [
        [ABONADO_COM_COMPENSACAO, 'Abonado com compensação de horário'],
        [ABONADO_SEM_COMPENSACAO, 'Abonado sem compensação de horário'],
        [TRABALHO_REMOTO, 'Trabalho Remoto'],
        [NAO_ABONADO, 'Não abonado'],
    ]
    ACAO_NUMERO_IMPAR_REGISTROS_CHOICES = [
        [NUMERO_IMPAR_REGISTROS_NAO_PERMITIDO, Frequencia.DESCRICAO_INCONSISTENCIA[Frequencia.INCONSISTENCIA_NUMERO_IMPAR_REGISTROS]]
    ]

    #   Quando for criar as outras regras de ponto lembrar de criar dict para os choices do formulario
    ACAO_ABONO_CHOICES = ACAO_ABONO_FALTA_CHOICES + ACAO_ABONO_TEMPO_MAIOR_DEZ_HORAS_CHOICES + ACAO_ABONO_TRABALHO_FDS_CHOICES

    CHOICES_POR_INCONSISTENCIAS = {
        Frequencia.INCONSISTENCIA_MENOR_JORNADA: ACAO_ABONO_FALTA_CHOICES,
        Frequencia.INCONSISTENCIA_MAIOR_JORNADA: ACAO_ABONO_TEMPO_MAIOR_DEZ_HORAS_CHOICES,
        Frequencia.INCONSISTENCIA_FALTA: ACAO_ABONO_FALTA_CHOICES,
        Frequencia.INCONSISTENCIA_TEMPO_MAIOR_DEZ_HORAS: ACAO_ABONO_TEMPO_MAIOR_DEZ_HORAS_CHOICES,
        Frequencia.INCONSISTENCIA_TRABALHO_FDS: ACAO_ABONO_TRABALHO_FDS_CHOICES,
        Frequencia.INCONSISTENCIA_NUMERO_IMPAR_REGISTROS: ACAO_NUMERO_IMPAR_REGISTROS_CHOICES
    }

    vinculo_pessoa = models.ForeignKeyPlus('comum.Vinculo', editable=False, on_delete=models.CASCADE)
    vinculo_chefe_imediato = models.ForeignKeyPlus('comum.Vinculo', related_name='vinculo_chefe_imediato_set', editable=False, on_delete=models.CASCADE)
    data = models.DateFieldPlus()
    descricao = models.TextField(max_length=200, verbose_name='Descrição', blank=True)
    acao_abono = models.PositiveIntegerField('Ação chefia imediata', default=NAO_ABONADO, choices=ACAO_ABONO_CHOICES)
    data_cadastro = models.DateTimeField(auto_now_add=True, editable=False, null=True)
    ultima_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('vinculo_pessoa', 'data')  # 1 abono por pessoa e dia
        verbose_name = 'Abono Chefia'
        verbose_name_plural = 'Abono Chefia'

    def __str__(self):
        return self.descricao

    def get_acao_abono_display_css(self):
        if self.acao_abono in [self.NAO_ABONADO, self.HORA_EXTRA_NAO_JUSTIFICADA, self.TRABALHO_FDS_NAO_PERMITIDO]:
            return 'error'
        elif self.acao_abono in [
            self.ABONADO_SEM_COMPENSACAO,
            self.TRABALHO_REMOTO,
            self.HORA_EXTRA_JUSTIFICADA,
            self.TRABALHO_FDS_PERMITIDO_COMO_HORA_EXTRA,
            self.TRABALHO_FDS_PERMITIDO_PARA_COMPENSACAO_CARGA_HORARIA,
            self.HORA_EXTRA_PARA_COMPENSACAO_CARGA_HORARIA,
        ]:
            return 'success'
        elif self.acao_abono == self.ABONADO_COM_COMPENSACAO:
            return 'alert'
        else:
            return 'info'

    def save(self, *args, **kwargs):
        acao_foi_editada = not (self.id is None)
        #
        super().save(*args, **kwargs)
        #
        self.notificar(acao_editada=acao_foi_editada)

    def notificar(self, acao_editada=False):
        """
            envia e-mail apos a insercao ou as edicoes da acao do chefe imediato
        """
        pessoa = self.vinculo_pessoa.pessoa
        if pessoa.email:
            observacoes = Observacao.objects.filter(data=self.data, vinculo=self.vinculo_pessoa)
            observacoes_da_pessoa = ''
            for observacao in observacoes:
                if observacoes_da_pessoa:
                    observacoes_da_pessoa += '\n'
                observacoes_da_pessoa += '{}'.format(observacao.descricao)
            if not observacoes_da_pessoa:
                observacoes_da_pessoa = 'Sem observações.'

            frequencias = Frequencia.get_frequencias_por_data(self.vinculo_pessoa, self.data)
            frequencias_da_pessoa = ''
            for frequencia in frequencias:
                if frequencias_da_pessoa:
                    frequencias_da_pessoa += '\n'
                frequencias_da_pessoa += '{}:{} ({})'.format(frequencia.acao, frequencia.horario.strftime('%H:%M:%S'), frequencia.maquina)
            if not frequencias_da_pessoa:
                frequencias_da_pessoa = 'Sem frequências.'

            assunto = '[SUAP] Avaliação da Frequência do Dia {}'.format(self.data.strftime('%d/%m/%Y'))
            mensagem = '''<h1>Avaliação da Frequência do Dia</h1>
                <h2>{data}</h2>
                <p>Prezado(a) {nome},</p>
                <p>Comunicamos que a sua chefia imediata, {chefe}, {acao} com relação à frequência do dia {data}.</p>
                <h3>Avaliação da Chefia Imediata</h3>
                <dl>
                    <dt>{abono}:</dt><dd>{descricao}</dd>
                </dl>
                <h3>Frequência do Servidor</h3>
                <dl>
                    <dt>Data:</dt>
                    <dd>{data}</dd>
                    <dt>Registros:</dt>
                    <dd>{frequencias}</dd>
                    <dt>Observações:</dt>
                    <dd>{observacoes}</dd>
                </dl>'''.format(
                data=self.data.strftime('%d/%m/%Y'),
                nome=pessoa.nome,
                chefe=self.vinculo_chefe_imediato.pessoa.nome,
                acao=(acao_editada and 'manifestou-se novamente') or 'manifestou-se',
                abono=self.get_acao_abono_display(),
                descricao=self.descricao,
                frequencias=frequencias_da_pessoa,
                observacoes=observacoes_da_pessoa,
            )
            send_notification(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [self.vinculo_pessoa], categoria='Avaliação da Frequência do Dia')


class TipoAfastamento(models.ModelPlus):
    class Meta:
        verbose_name = 'Tipo de Afastamento'
        verbose_name_plural = 'Tipos de Afastamento'

    SEARCH_FIELDS = ['descricao', 'codigo']
    descricao = models.TextField(max_length=200, verbose_name='Descrição')
    # Ajustando para importar os afastamentos a partes das extracoes
    codigo = models.CharField(max_length=5, null=True, blank=True)

    def __str__(self):
        return self.descricao


class AfastamentoManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().select_related('tipo')


class Afastamento(models.ModelPlus):
    """
    Representa os afastamentos cadastrados pelo RH.
    Estes sairão no relatório de frequências oficial.
    OBS: É possível que esteja duplicado com suap.ServidorOcorrencia do tipo
    `AFASTAMENTO`. Nesse caso, o RH deverá remover a duplicidade.
    """

    objects = AfastamentoManager()

    vinculo = models.ForeignKeyPlus('comum.Vinculo', on_delete=models.CASCADE)
    tipo = models.ForeignKeyPlus(TipoAfastamento, null=True, blank=True, on_delete=models.CASCADE)
    data_ini = models.DateFieldPlus('Data Inicial', db_index=True)
    data_fim = models.DateFieldPlus('Data Final', null=True, db_index=True)
    descricao = models.TextField('Descrição', max_length=200)

    @classmethod
    def buscar_afastamento_periodo(cls, vinculo, data_ini, data_fim):
        return cls.objects.filter(vinculo=vinculo, data_ini__lte=data_fim, data_fim__gte=data_ini)

    class Meta:
        verbose_name = 'Afastamento'
        verbose_name_plural = 'Afastamentos'

    def __str__(self):
        if self.tipo:
            return '{}: {}'.format(str(self.tipo), self.descricao)
        else:
            return self.descricao

    @classmethod
    def buscar(cls, vinculo, data_ini, data_fim):
        return cls.objects.filter(vinculo=vinculo, data_ini__lte=data_fim, data_fim__gte=data_ini)

    @classmethod
    def buscar_afastamentos_parciais(cls, vinculo, data_ini, data_fim):
        """
            O objetivo é obter as instâncias de afastamentos que estão associadas a processos de afastamentos parciais.
            Infelizmente não há uma ligação (FK) entre Afastamento e Afastamento Parcial. Dessa forma será
            necessário usar o atributo 'tipo' de Afastamento e, baseado na descrição do tipo, determinar se o
            o afastamento é um afastamento parcial. Essa determinação deve ser feita em tempo de desenvolvimento de
            modo a 'descobrir' quais tipos de afastamentos fazem referência a afastamento parcial.

            Afastamento Parcial:
                Parecer/MP/CONJUR/FNF/Nº 1810 – 1.11/2009 e Orientação Normativa Nº 02/2016-DIGPE/IFRN

            Problema:
                O RH pode duplicar o cadastro de tipos de afastamentos que fazem referência a afastamento parcial.

            No momento (04/12/2018), há dois tipos cadastrados:
                Id 317
                Id 316
        """
        ids_tipos_afastamentos_parciais = [316, 317]  # hardcod mesmo !!!!!!!!!!!!
        return cls.objects.filter(vinculo=vinculo, data_ini__lte=data_fim, data_fim__gte=data_ini, tipo_id__in=ids_tipos_afastamentos_parciais)


##########################################################################################
# COMPENSAÇÃO DE HORÁRIO E RECESSOS
##########################################################################################


class HorarioCompensacao(models.Model):
    """ Representa um informe de compensação de horário

        Por padrão, qualquer dia com saldo excedente pode ser usado para compensação de horário, informando o dia da
        compensação (o dia do saldo excedente), o dia compensado e a quantidade de carga horária compensada.

        Os informes de compensação poderão ser invalidados/sem efeito caso a chefia abone negativamente dias com saldos
        excedentes e dias com débitos.

        Um informe de compensação será invalidado, conforme abonos da chefia, nas seguintes situações:

        1) quando o dia da compensação (o dia do saldo excedente) receber os abonos:

            1.1) HORA EXTRA NÃO JUSTIFICADA: não considera o saldo excedente.
            1.2) HORA EXTRA JUSTIFICADA: não considera o saldo excedente, pois, nesse caso, os efeitos são apenas
            remuneratórios.
            1.3) TRABALHO FDS NÃO PERMITIDO: não considera o saldo excedente.
            1.4) TRABALHO FDS PERMITIDO COMO HORA EXTRA: não considera o saldo excedente, pois,	nesse caso, os
            efeitos são apenas remuneratórios.

        2) quando o dia compensado (o dia do débito) receber os abonos:

            2.1) NÃO ABONADO: o dia não poderá ser compensado, desconsiderando o débito.
            2.2) ABONADO SEM COMPENSAÇÃO: o dia não precisará ser compensado, desconsiderando o débito.
    """

    SITUACAO_VALIDO = 1
    SITUACAO_INVALIDO = 2
    SITUACAO_CHOICES = [[SITUACAO_VALIDO, 'Válido'], [SITUACAO_INVALIDO, 'Invalidado/Sem Efeito']]

    SALDO_MINIMO_EM_SEGUNDOS = 1
    DEBITO_MINIMO_EM_SEGUNDOS = 1

    funcionario = models.ForeignKeyPlus('rh.Servidor', editable=False, verbose_name='Funcionário', related_name='funcionario_compensacao_horario', on_delete=models.CASCADE)
    data_compensacao = models.DateFieldPlus('Data da Compensação/Saldo', help_text='Dia no qual há uma carga horária excedente.')
    data_aplicacao = models.DateFieldPlus('Data do Débito', help_text='Dia no qual há um débito de carga horária.')
    ch_compensada = models.TimeFieldPlus('Carga Horária Compensada', help_text='Formato: HH:MM.')
    chefe = models.ForeignKeyPlus(
        'rh.Servidor',
        editable=False,
        verbose_name='Chefe Imediato',
        help_text='Chefe Imediato na Data da Compensação',
        related_name='chefe_compensacao_horario',
        null=True,
        blank=True,
        on_delete=models.CASCADE,
    )
    observacoes = models.TextField('Observações', null=True, blank=True)
    #
    # situação do informe de compensação em relação aos possíveis abonos que podem ocorrer
    abono_na_data_compensacao = models.ForeignKeyPlus(
        'ponto.AbonoChefia', null=True, blank=True, editable=False, related_name='abono_na_data_compensacao', on_delete=models.SET_NULL
    )  # exclui-se o abono, mas não o informe
    abono_na_data_aplicacao = models.ForeignKeyPlus(
        'ponto.AbonoChefia', null=True, blank=True, editable=False, related_name='abono_na_data_aplicacao', on_delete=models.SET_NULL
    )  # exclui-se o abono, mas não o informe
    situacao = models.IntegerField('Situação', choices=SITUACAO_CHOICES, default=SITUACAO_VALIDO, editable=False)

    class Meta:
        ordering = ('funcionario', '-data_aplicacao', '-data_compensacao')
        verbose_name = 'Informe de Compensação de Horário'
        verbose_name_plural = 'Informes de Compensação de Horário'

    def __str__(self):
        return 'Compensação de {} do dia {}. Carga Horária produzida em {}{}. Servidor: {}'.format(
            formata_segundos(Frequencia.time_para_segundos(self.ch_compensada), '{h}h', '{m}min', '', True),
            self.data_aplicacao.strftime('%d/%m/%Y'),
            self.data_compensacao.strftime('%d/%m/%Y'),
            ' (Sábado)' if self.is_compensacao_no_sabado else '',
            self.funcionario,
        )

    @property
    def is_compensacao_no_sabado(self):
        return self.data_compensacao.weekday() == 5

    @property
    def frequencia_duracao(self):
        """ duração da frequência na data da compensação em Time """
        frequencias = Frequencia.get_frequencias_por_data(vinculo=self.funcionario.get_vinculo(), data=self.data_compensacao)
        return Frequencia.segundos_para_time(Frequencia.get_tempo_entre_frequencias(frequencias))

    def save(self, *args, **kwargs):
        #
        # resolve o chefe imediato do funcionário na data da compensação
        try:
            if not self.chefe:
                self.chefe = self.funcionario.sub_instance().chefes_na_data(data=self.data_compensacao)[0]
        except Exception:
            self.chefe = None
        #
        super().save(*args, **kwargs)

    def save_observacao_no_ponto(self, descricao_na_data_compensacao=None, descricao_na_data_aplicacao=None):
        self.observacoes = ''

        observacoes = []

        if descricao_na_data_compensacao:
            observacoes.append(descricao_na_data_compensacao)

        if descricao_na_data_aplicacao:
            observacoes.append(descricao_na_data_aplicacao)

        if observacoes:
            self.observacoes = ' '.join(observacoes)

        self.save()

    def get_auto_obs_descricao_na_data_compensacao(self):
        return 'Carga horária de {} usada na compensação do dia {}'.format(
            formata_segundos(Frequencia.time_para_segundos(self.ch_compensada), '{h}h', '{m}min', '', True), self.data_aplicacao.strftime('%d/%m/%Y')
        )

    def get_auto_obs_descricao_na_data_aplicacao(self):
        return 'Carga horária de {} compensada no dia {}'.format(
            formata_segundos(Frequencia.time_para_segundos(self.ch_compensada), '{h}h', '{m}min', '', True), self.data_compensacao.strftime('%d/%m/%Y')
        )

    def get_absolute_url(self):
        return '/ponto/abrir_compensacao_horario/{}/'.format(self.id)

    @staticmethod
    def is_dia_util(vinculo, data):
        """
            :return [True/False, ['infor extra', 'infor extra', 'infor extra', ...]]
        """
        from ponto.compensacao import SituacaoDia  # evitar import circular

        return SituacaoDia(vinculo.relacionamento, data).is_dia_util

    @staticmethod
    def inspecionar_informes_abono_chefia_salvo(sender, **kwargs):
        """
            Os informes de compensação poderão ser invalidados/sem efeito caso a chefia abone negativamente dias
            com saldos excedentes e dias com débitos.

            Um informe de compensação será invalidado, conforme abonos da chefia, nas seguintes situações:

            1) quando o dia da compensação (o dia do saldo excedente) receber os abonos:

                1.1) HORA EXTRA NÃO JUSTIFICADA: não considera o saldo excedente.
                1.2) HORA EXTRA JUSTIFICADA: não considera o saldo excedente, pois, nesse caso, os efeitos são apenas
                remuneratórios.
                1.3) TRABALHO FDS NÃO PERMITIDO: não considera o saldo excedente.
                1.4) TRABALHO FDS PERMITIDO COMO HORA EXTRA: não considera o saldo excedente, pois,	nesse caso, os
                efeitos são apenas remuneratórios.

            2) quando o dia compensado (o dia do débito) receber os abonos:

                2.1) NÃO ABONADO: o dia não poderá ser compensado, desconsiderando o débito.
                2.2) ABONADO SEM COMPENSAÇÃO: o dia não precisará ser compensado, desconsiderando o débito.

                Em ambos os casos, a carga horária compensada "voltará" como saldo para o dia da compensação.
        """
        abono_chefia = kwargs.get('instance')
        if abono_chefia:
            informes = (
                (HorarioCompensacao.objects.filter(data_compensacao=abono_chefia.data) | HorarioCompensacao.objects.filter(data_aplicacao=abono_chefia.data))
                .filter(funcionario=abono_chefia.vinculo_pessoa.relacionamento)
                .distinct()
            )
            for informe in informes:
                if abono_chefia.acao_abono in [
                    AbonoChefia.HORA_EXTRA_NAO_JUSTIFICADA,
                    AbonoChefia.HORA_EXTRA_JUSTIFICADA,
                    AbonoChefia.TRABALHO_FDS_NAO_PERMITIDO,
                    AbonoChefia.TRABALHO_FDS_PERMITIDO_COMO_HORA_EXTRA,
                    AbonoChefia.NAO_ABONADO,
                    AbonoChefia.ABONADO_SEM_COMPENSACAO,
                    AbonoChefia.TRABALHO_REMOTO,
                ]:
                    # o abono poderá ter impacto negativo ao informe atual
                    if abono_chefia.data == informe.data_compensacao:
                        # o dia do saldo foi abonado
                        informe.abono_na_data_compensacao = abono_chefia
                    if abono_chefia.data == informe.data_aplicacao:
                        # o dia do débito foi abonado
                        informe.abono_na_data_aplicacao = abono_chefia
                    #
                    houve_impacto_negativo = informe.abono_na_data_compensacao is not None or informe.abono_na_data_aplicacao is not None
                    #
                    if houve_impacto_negativo:
                        # atualiza o informe
                        informe.situacao = HorarioCompensacao.SITUACAO_INVALIDO
                        informe.save()
                else:
                    # a ação do abono provavelmente foi alterada e isso poderá ter impacto positivo ao informe atual
                    if informe.abono_na_data_compensacao == abono_chefia:
                        # o abono deixa de afetar o informe na data da compensação
                        informe.abono_na_data_compensacao = None
                    #
                    if informe.abono_na_data_aplicacao == abono_chefia:
                        # o abono deixa de afetar o informe na data da aplicação
                        informe.abono_na_data_aplicacao = None
                    #
                    houve_impacto_positivo_na_data_compensacao = informe.abono_na_data_compensacao is None
                    houve_impacto_positivo_na_data_aplicacao = informe.abono_na_data_aplicacao is None
                    #
                    if houve_impacto_positivo_na_data_compensacao and houve_impacto_positivo_na_data_aplicacao:
                        informe.situacao = HorarioCompensacao.SITUACAO_VALIDO
                        # restaura as observações caso não tenha nenhuma das duas
                        if not informe.observacoes:
                            informe.save_observacao_no_ponto(informe.get_auto_obs_descricao_na_data_compensacao(), informe.get_auto_obs_descricao_na_data_aplicacao())
                    if houve_impacto_positivo_na_data_compensacao or houve_impacto_positivo_na_data_compensacao:
                        # atualiza o informe (pode ser que a situação ainda continue inválida)
                        informe.save()

    @staticmethod
    def inspecionar_informes_abono_chefia_excluido(sender, **kwargs):
        abono_chefia = kwargs.get('instance')
        if abono_chefia:
            for informe in (
                (HorarioCompensacao.objects.filter(abono_na_data_compensacao=abono_chefia) | HorarioCompensacao.objects.filter(abono_na_data_aplicacao=abono_chefia))
                .filter(funcionario=abono_chefia.vinculo_pessoa.relacionamento)
                .distinct()
            ):
                # atualiza o informe
                informe.abono_na_data_compensacao = None
                informe.abono_na_data_aplicacao = None
                informe.situacao = HorarioCompensacao.SITUACAO_VALIDO
                # restaura as observações caso não tenha nenhuma das duas
                if not informe.observacoes:
                    informe.save_observacao_no_ponto(informe.get_auto_obs_descricao_na_data_compensacao(), informe.get_auto_obs_descricao_na_data_aplicacao())
                informe.save()
        #
        # só pra fazer uma limpeza em possíveis inconsistências ...
        for informe in HorarioCompensacao.objects.filter(
            situacao=HorarioCompensacao.SITUACAO_INVALIDO,  # inválidos
            abono_na_data_compensacao__isnull=True,
            abono_na_data_aplicacao__isnull=True,  # e sem abonos!!
            funcionario=abono_chefia.vinculo_pessoa.relacionamento,
        ):
            # atualiza o informe
            informe.situacao = HorarioCompensacao.SITUACAO_VALIDO
            # restaura as observações caso não tenha nenhuma das duas
            if not informe.observacoes:
                informe.save_observacao_no_ponto(informe.get_auto_obs_descricao_na_data_compensacao(), informe.get_auto_obs_descricao_na_data_aplicacao())
            informe.save()

    def get_situacao(self):  # uma outra versão do get_situacao_display
        situacao_display = self.get_situacao_display()  # padrão
        if not self.situacao == HorarioCompensacao.SITUACAO_VALIDO:
            if self.abono_na_data_compensacao:
                situacao_display += '. '
                if self.abono_na_data_compensacao.acao_abono in [AbonoChefia.HORA_EXTRA_NAO_JUSTIFICADA, AbonoChefia.TRABALHO_FDS_NAO_PERMITIDO]:
                    situacao_display += 'Saldo Excedente Desconsiderado. '
                elif self.abono_na_data_compensacao.acao_abono in [AbonoChefia.HORA_EXTRA_JUSTIFICADA, AbonoChefia.TRABALHO_FDS_PERMITIDO_COMO_HORA_EXTRA]:
                    situacao_display += 'Saldo Excedente Desconsiderado (apenas efeitos remuneratórios). '
                situacao_display += 'Abono: {} - {} ({})'.format(
                    self.abono_na_data_compensacao.data.strftime('%d/%m/%Y'), self.abono_na_data_compensacao.get_acao_abono_display(), self.abono_na_data_compensacao.descricao
                )
            #
            if self.abono_na_data_aplicacao:
                situacao_display += '. '
                if self.abono_na_data_aplicacao.acao_abono == AbonoChefia.NAO_ABONADO:
                    situacao_display += 'Débito Não Poderá ser Compensado. '
                elif self.abono_na_data_aplicacao.acao_abono in [AbonoChefia.ABONADO_SEM_COMPENSACAO, AbonoChefia.TRABALHO_REMOTO]:
                    situacao_display += 'Débito Não Necessitará ser Compensado. '
                situacao_display += 'Abono: {} - {} ({})'.format(
                    self.abono_na_data_aplicacao.data.strftime('%d/%m/%Y'), self.abono_na_data_aplicacao.get_acao_abono_display(), self.abono_na_data_aplicacao.descricao
                )
        return situacao_display

    @property
    def opcoes_compensacao_envolvidas(self):
        # return RecessoOpcao.objects.filter(
        #     recessoopcaoescolhida__funcionario=self.funcionario,
        #     recessoopcaoescolhida__validacao=RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO,
        #     recessoopcaoescolhida__dias_escolhidos__dia__data=self.data_aplicacao
        # )
        from ponto.compensacao import SituacaoDia

        situacao = SituacaoDia(servidor=self.funcionario, dia=self.data_aplicacao)
        return RecessoOpcao.objects.filter(recessoopcaoescolhida__in=situacao.acompanhamentos_envolvidos_contendo_o_dia_como_debito).distinct()

    @property
    def ch_compensada_em_segundos(self):
        return Frequencia.time_para_segundos(self.ch_compensada)

    def delete(self, *args, **kwargs):
        delete = super().delete(*args, **kwargs)
        if delete:
            from ponto.utils import get_total_tempo_debito_pendente_semana_anterior, get_total_tempo_debito_pendente_mes_anterior

            save_session_cache(tl.get_request(), 'total_tempo_debito_pendente_semana_anterior', get_total_tempo_debito_pendente_semana_anterior)

            save_session_cache(tl.get_request(), 'total_tempo_debito_pendente_mes_anterior', get_total_tempo_debito_pendente_mes_anterior)
        return delete


#
# "ouvindo" o pós save e o pós delete dos abonos de chefia (AbonoChefia)
abono_post_save = post_save.connect(sender=AbonoChefia, receiver=HorarioCompensacao.inspecionar_informes_abono_chefia_salvo)
abono_post_delete = post_delete.connect(sender=AbonoChefia, receiver=HorarioCompensacao.inspecionar_informes_abono_chefia_excluido)


class RecessoOpcao(models.Model):
    """ Representa uma opção de recesso definida pelo RH """
    SEARCH_FIELDS = ['descricao']

    class Meta:
        verbose_name = 'Opção de Compensação'
        verbose_name_plural = 'Opções de Compensação'

    TIPO_NATAL_ANO_NOVO = 1
    TIPO_OUTRO = 2
    TIPO_CHOICES = [[TIPO_NATAL_ANO_NOVO, 'Recesso Natal/Ano Novo'], [TIPO_OUTRO, 'Outro']]

    SITUACAO_EM_FASE_DE_CADASTRO = 1
    SITUACAO_ABERTO_PARA_ESCOLHA_DE_DATAS = 2
    SITUACAO_FECHADO = 3
    SITUACAO_CHOICES = [
        [SITUACAO_EM_FASE_DE_CADASTRO, 'Em Fase de Cadastro'],
        [SITUACAO_ABERTO_PARA_ESCOLHA_DE_DATAS, 'Aberto para Escolha dos Dias do Recesso'],
        [SITUACAO_FECHADO, 'Concluído Cadastro e Escolha dos Dias do Recesso'],
    ]

    responsavel = models.ForeignKeyPlus('rh.Servidor', editable=False, verbose_name='Responsável pelo Cadastro', on_delete=models.CASCADE)
    #
    tipo = models.IntegerField('Tipo', choices=TIPO_CHOICES, default=TIPO_OUTRO)
    descricao = models.TextField('Descrição')
    #
    periodo_de_escolha_data_inicial = models.DateFieldPlus('Data de Início para o Período de Escolhas', null=True, blank=True)
    periodo_de_escolha_data_final = models.DateFieldPlus('Data de Término para o Período de Escolhas', null=True, blank=True)
    #
    situacao = models.IntegerField('Situação', choices=SITUACAO_CHOICES, default=SITUACAO_EM_FASE_DE_CADASTRO, editable=False)
    #
    qtde_max_dias_escolhidos = models.PositiveIntegerFieldPlus(
        'Quantidade de Dias a Escolher', help_text='Número máximo de Dias que ' 'podem ser escolhidos', min_value=0, default=0, blank=True
    )

    # Os fields 'publico_alvo_campi' e 'publico_alvo_servidores' representam os servidores afetados
    # por esta opção de compensação. O field 'publico_alvo_campi' é mais abrangente e pode envolver
    # servidores indesejados. Há situações em que servidores são automaticamente desconsiderados.
    # Para todos os efeitos, onde houver necessidade de saber os servidores de uma opção de compensação, utilize
    # o método 'get_servidores' desta classe.

    publico_alvo_campi = models.ManyToManyFieldPlus('rh.UnidadeOrganizacional', verbose_name='Público alvo - Campi', blank=True, related_name='publico_alvo_campi')
    publico_alvo_servidores = models.ManyToManyFieldPlus('rh.Servidor', verbose_name='Público alvo - Servidores', blank=True, related_name='publico_alvo_servidores')

    def get_servidores(self):
        """
            público alvo (lista de servidores) desta opção de compensação
        """
        servidores = self.publico_alvo_servidores.all()
        servidores_campi = Servidor.objects.ativos().filter(setor__uo__in=self.publico_alvo_campi.all())

        ##
        # restrições quanto aos servidores selecionados APENAS via campi,
        # onde pode haver servidores indesejados/impedidos
        if self.tipo == RecessoOpcao.TIPO_NATAL_ANO_NOVO:
            '''
                Demanda 595 / NOTA TÉCNICA Nº 317/2013/CGNOR/DENOP/SEGEP/MP:
                    - recesso de fim de ano não se aplica aos estagiários e aos prestadores de serviço
            '''
            servidores_campi = servidores_campi.exclude(situacao__codigo__in=Situacao.situacoes_siape_estagiarios())
        ##

        publico_alvo = servidores | servidores_campi

        return publico_alvo.distinct()

    @property
    def is_permite_escolha_dos_dias_pelos_servidores(self):
        return self.tipo in [RecessoOpcao.TIPO_NATAL_ANO_NOVO]

    def __str__(self):
        return '{}'.format(self.descricao)

    def get_absolute_url(self):
        return '/ponto/abrir_opcao_recesso/{}/'.format(self.id)

    @property
    def is_em_fase_de_cadastro(self):
        return self.situacao == RecessoOpcao.SITUACAO_EM_FASE_DE_CADASTRO

    @property
    def is_aberto_para_escolhas_de_datas(self):
        return self.is_permite_escolha_dos_dias_pelos_servidores and self.situacao == RecessoOpcao.SITUACAO_ABERTO_PARA_ESCOLHA_DE_DATAS

    @property
    def is_concluido_cadastro_e_escolhas_de_datas(self):
        return self.situacao == RecessoOpcao.SITUACAO_FECHADO

    @property
    def is_no_periodo_para_escolhas_de_datas(self):
        return self.is_aberto_para_escolhas_de_datas and self.periodo_de_escolha_data_inicial <= datetime.date.today() <= self.periodo_de_escolha_data_final

    @property
    def is_definido_dias_do_recesso(self):
        return self.dias_do_recesso.all().exists()

    @property
    def is_definido_periodos_de_compensacao(self):
        return self.periodos_de_compensacao.all().exists()

    @property
    def is_definido_periodo_de_escolha(self):
        return self.is_permite_escolha_dos_dias_pelos_servidores and self.periodo_de_escolha_data_inicial is not None and self.periodo_de_escolha_data_final is not None

    def liberar_para_escolha_dos_dias_do_recesso(self):
        if not (self.is_publico_alvo_definido and self.is_definido_dias_do_recesso and self.is_definido_periodo_de_escolha and self.is_definido_periodos_de_compensacao):
            raise Exception('Verifique se o Público Alvo, os Dias do Recesso, os Períodos de Compensação e o Período de Escolha dos Dias do Recesso foram definidos.')
        if not self.is_em_fase_de_cadastro:
            raise Exception('Verifique se a Opção de Recesso está em Fase de Cadastro pelo RH.')
        hoje = datetime.date.today()
        maior_data_periodo_compensacao = self.periodos_de_compensacao.all().order_by('-data_inicial')[0].data_final
        if hoje > maior_data_periodo_compensacao:
            raise Exception('Os Períodos de Compensação estão no passado.')
        #
        if self.dias_do_recesso.all().count() < self.qtde_max_dias_escolhidos:
            raise Exception(
                'O número Máximo de Dias a Escolher ({}) '
                'é maior que o número de '
                'Dias definidos ({}).'.format(self.qtde_max_dias_escolhidos, self.dias_do_recesso.all().count())
            )
        # ufa, agora vai!
        self.situacao = RecessoOpcao.SITUACAO_ABERTO_PARA_ESCOLHA_DE_DATAS
        self.save()

    def retornar_a_fase_de_cadastro(self):
        self.situacao = RecessoOpcao.SITUACAO_EM_FASE_DE_CADASTRO
        self.save()

    def fechar_cadastro_e_escolha(self):
        if not self.is_permite_escolha_dos_dias_pelos_servidores:
            # escolha automática de dias por parte dos servidores (na marra mesmo!!!)
            pode_rodar_escolha_automatica = self.is_publico_alvo_definido and self.is_definido_dias_do_recesso and self.is_definido_periodos_de_compensacao
            if not pode_rodar_escolha_automatica:
                raise Exception('Verifique se o Público Alvo, os Dias e os Períodos de Compensação foram definidos.')

            if pode_rodar_escolha_automatica:
                try:
                    self.escolher_dias_automaticamente()
                except Exception as erro:
                    raise Exception('Não foi possível concluir o cadastramento. {}'.format(str(erro)))

        self.situacao = RecessoOpcao.SITUACAO_FECHADO
        self.save()

    def escolher_dias_automaticamente(self):  # throws Exception
        try:
            for servidor in self.get_servidores():
                if not RecessoOpcaoEscolhida.objects.filter(funcionario=servidor, recesso_opcao=self).exists():
                    acompanhamento = RecessoOpcaoEscolhida()
                    acompanhamento.funcionario = servidor
                    acompanhamento.recesso_opcao = self
                    acompanhamento.validacao = RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO
                    acompanhamento.save()

                    # 1 acompanhamento ----> N dias escolhidos
                    for dia in self.dias_do_recesso.all():
                        dia_escolhido = RecessoDiaEscolhido()
                        dia_escolhido.recesso_opcao_escolhida = acompanhamento
                        dia_escolhido.dia = dia
                        dia_escolhido.save()

        except Exception:
            RecessoOpcaoEscolhida.objects.filter(recesso_opcao=self).delete()  # rollback
            raise Exception()

    @property
    def is_publico_alvo_definido(self):
        return self.get_servidores().exists()

    def get_servidores_display(self):
        servidores = self.get_servidores()
        if servidores.count() > 5:
            lista = '{} ... +{}'.format(', '.join([str(servidor) for servidor in servidores[:5]]), servidores.count() - 5)
        else:
            lista = ', '.join([str(servidor) for servidor in servidores])
        return lista

    @staticmethod
    def get_recessos_opcoes_com_dias_a_escolher_hoje(funcionario):
        """ retorna um dicionário:
            {
                com_dias_a_escolher: queryset [recesso_opcao, recesso_opcao, ...],
                com_dias_a_editar: queryset [recesso_opcao, recesso_opcao, ...],
                com_dias_a_remarcar: queryset [recesso_opcao, recesso_opcao, ...],
                com_dias_que_ainda_pode_editar: queryset [recesso_opcao, recesso_opcao, ...]
            }
        """
        hoje = datetime.date.today()
        #
        # todas as opções de recessos que estão abertas para a escolha de datas e
        # com período de escolha "caindo" hoje
        recessos_opcoes = RecessoOpcao.objects.filter(
            situacao=RecessoOpcao.SITUACAO_ABERTO_PARA_ESCOLHA_DE_DATAS, periodo_de_escolha_data_inicial__lte=hoje, periodo_de_escolha_data_final__gte=hoje
        )
        #
        # omite as opções nas quais o servidor não pertence ao publico alvo
        for recesso_opcao in recessos_opcoes:
            if not recesso_opcao.get_servidores().filter(pk=funcionario.id).exists():
                recessos_opcoes = recessos_opcoes.exclude(id=recesso_opcao.id)
        #
        # recessos a escolher = todos - os já escolhidos pelo funcionário
        recessos_a_escolher = recessos_opcoes.exclude(recessoopcaoescolhida__funcionario=funcionario)
        #
        # recessos a editar = dentre todos, apenas os do funcionário informado e que estão 'aguardando'
        recessos_a_editar = recessos_opcoes.filter(
            recessoopcaoescolhida__funcionario=funcionario, recessoopcaoescolhida__validacao__in=[RecessoOpcaoEscolhida.VALIDACAO_AGUARDANDO]
        )
        #
        # recessos a remarcar = dentre todos, apenas os do funcionário e que estão 'não-autorizados-remarcar'
        recessos_a_remarcar = recessos_opcoes.filter(
            recessoopcaoescolhida__funcionario=funcionario, recessoopcaoescolhida__validacao__in=[RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO_REMARCAR]
        )

        # recessos que ainda pode editar = dentre todos, apenas:
        recessos_ainda_pode_editar = recessos_opcoes.filter(
            # os do funcionário informado
            recessoopcaoescolhida__funcionario=funcionario,
            # diferente de "não autorizado"
            recessoopcaoescolhida__validacao__in=[
                RecessoOpcaoEscolhida.VALIDACAO_AGUARDANDO,
                RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO,
                RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO_REMARCAR,
            ],
        )

        return dict(
            com_dias_a_escolher=recessos_a_escolher,
            com_dias_a_editar=recessos_a_editar,
            com_dias_a_remarcar=recessos_a_remarcar,
            com_dias_que_ainda_pode_editar=recessos_ainda_pode_editar,
        )

    @staticmethod
    def get_recessos_opcoes_periodo_escolha_expirado():
        """ Recessos abertos com período de escolhas expirado
        """
        recessos_ids = []
        for recesso_opcao in RecessoOpcao.objects.filter(situacao=RecessoOpcao.SITUACAO_ABERTO_PARA_ESCOLHA_DE_DATAS):
            # não está no período?
            if not recesso_opcao.is_no_periodo_para_escolhas_de_datas:
                recessos_ids.append(recesso_opcao.id)
        return RecessoOpcao.objects.filter(id__in=recessos_ids)

    @staticmethod
    def set_concluir_recessos_opcoes_pendentes():
        """ Recessos abertos com período de escolhas expirado são concluídos (tentativas)
        """
        for recesso_opcao in RecessoOpcao.get_recessos_opcoes_periodo_escolha_expirado():
            try:
                recesso_opcao.fechar_cadastro_e_escolha()
            except Exception:
                pass

    @staticmethod
    def get_recessos_opcoes_abertos_e_autorizados(funcionario):
        """ Recessos ainda abertos para escolha (em período de escolha) porém já autorizados
        """
        return RecessoOpcao.objects.filter(
            situacao=RecessoOpcao.SITUACAO_ABERTO_PARA_ESCOLHA_DE_DATAS,
            recessoopcaoescolhida__funcionario=funcionario,
            recessoopcaoescolhida__validacao=RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO,
        )

    @staticmethod
    def get_recessos_opcoes_abertos_e_nao_autorizados(funcionario):
        """ Recessos ainda abertos para escolha (em período de escolha) porém já não autorizados (sem possibilidade de
            remarcação)
        """
        return RecessoOpcao.objects.filter(
            situacao=RecessoOpcao.SITUACAO_ABERTO_PARA_ESCOLHA_DE_DATAS,
            recessoopcaoescolhida__funcionario=funcionario,
            recessoopcaoescolhida__validacao=RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO,
        )


class RecessoPeriodoCompensacao(models.Model):
    """ Representa um período definido pelo RH no qual o recesso poderá ser compensado """

    class Meta:
        verbose_name = 'Período de Compensação'
        verbose_name_plural = 'Períodos de Compensação'

    recesso_opcao = models.ForeignKeyPlus('ponto.RecessoOpcao', editable=False, related_name='periodos_de_compensacao', on_delete=models.CASCADE)
    data_inicial = models.DateFieldPlus('Data Inicial')
    data_final = models.DateFieldPlus('Data Final')

    def __str__(self):
        return '{} a {}'.format(self.data_inicial.strftime('%d/%m/%Y'), self.data_final.strftime('%d/%m/%Y'))


class RecessoDia(models.Model):
    """ Representa um dia definido pelo RH no qual haverá recesso """

    class Meta:
        verbose_name = 'Dia a Compensar'
        verbose_name_plural = 'Dias a Compensar'
        ordering = ('data',)
        unique_together = ('data', 'recesso_opcao')

    recesso_opcao = models.ForeignKeyPlus('ponto.RecessoOpcao', editable=False, related_name='dias_do_recesso', on_delete=models.CASCADE)
    data = models.DateFieldPlus('Dia do Recesso')

    def __str__(self):
        return '{}'.format(self.data.strftime('%d/%m/%Y'))


class RecessoOpcaoEscolhida(models.Model):
    """ Representa uma opção de recesso escolhida por um servidor/funcionário pela qual deseja gozar um ou mais
        dias de recesso
    """

    VALIDACAO_AGUARDANDO = 1
    VALIDACAO_AUTORIZADO = 2
    VALIDACAO_NAO_AUTORIZADO = 3
    VALIDACAO_NAO_AUTORIZADO_REMARCAR = 4
    VALIDACAO_CHOICES = [
        [VALIDACAO_AGUARDANDO, 'Aguardando'],
        [VALIDACAO_AUTORIZADO, 'Autorizado'],
        [VALIDACAO_NAO_AUTORIZADO_REMARCAR, 'Não Autorizado - Remarcar Novamente'],
        [VALIDACAO_NAO_AUTORIZADO, 'Não Autorizado'],
    ]

    class Meta:
        verbose_name = 'Acompanhamento de Compensação'
        verbose_name_plural = 'Acompanhamentos de Compensações'

    funcionario = models.ForeignKeyPlus('rh.Servidor', editable=False, verbose_name='Servidor', related_name='funcionario_recesso', on_delete=models.CASCADE)
    recesso_opcao = models.ForeignKeyPlus('ponto.RecessoOpcao', editable=False, verbose_name='Opção de Compensação', on_delete=models.CASCADE)
    data_escolha = models.DateFieldPlus('Data da Escolha', auto_now_add=True)
    validacao = models.IntegerField('Validação', choices=VALIDACAO_CHOICES, default=VALIDACAO_AGUARDANDO)
    validador = models.ForeignKeyPlus('rh.Servidor', verbose_name='Validador', related_name='validador_recesso', blank=True, null=True, on_delete=models.CASCADE)
    motivo_nao_autorizacao = models.TextField('Motivo da Não Autorização (se for o caso)', null=True, blank=True)

    dias_efetivos_a_compensar_cache = models.TextField('', null=True, blank=True, editable=False)
    pode_validar_apos_prazo = models.BooleanField('Liberado para validação após término do prazo', default=False)

    def __str__(self):
        return '{}'.format(self.recesso_opcao)

    @property
    def chefes(self):
        """ chefes na data da escolha + chefes na data de hoje + validador selecionado (se for o caso) """
        try:
            funcionario = self.funcionario.sub_instance()

            chefes = funcionario.chefes_na_data(self.data_escolha, considerar_setor_no_qual_tem_funcao=True) | funcionario.chefes_na_data(
                datetime.date.today(), considerar_setor_no_qual_tem_funcao=True
            )

            if self.validador and self.validador not in chefes:
                chefes = chefes | Funcionario.objects.filter(id=self.validador.id)

            return chefes  # instâncias de rh.Funcionario
        except Exception:
            return []

    def is_chefe(self, relacionamento=None):
        if relacionamento:
            return relacionamento.id in [chefe.id for chefe in self.chefes]
        return False

    @property
    def is_aguardando(self):
        return self.validacao == RecessoOpcaoEscolhida.VALIDACAO_AGUARDANDO

    def get_absolute_url(self):
        return '/ponto/abrir_recesso_escolhido/{}/'.format(self.id)

    def notifica_validacao(self):
        if not self.is_aguardando:
            assunto = '[SUAP] Validação de {}'.format(self.recesso_opcao)
            url = '{}/ponto/abrir_recesso_escolhido/{}/'.format(settings.SITE_URL, self.id)
            mensagem = '''
                <h1>Validação de Recesso</h1>
                <h2>{}</h2>
                <dl>
                    <dt>Validação:</dt><dd>{} {}</dd>
                    <dt>Validador:</dt><dd>{}</dd>
                    <dt>Dias Escolhidos:</dt><dd>{}</dd>
                    <dt>Data da Escolha:</dt><dd>{}</dd>
                </dl>
                <p>--</p>
                <p>Para mais informações, acesse: <a href="{}">{}</a></p>
                '''.format(
                self.recesso_opcao,
                self.get_validacao_display(),
                '(Motivo: {})'.format(self.motivo_nao_autorizacao)
                if self.validacao in [RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO, RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO_REMARCAR]
                else '',
                self.validador,
                ', '.join([str(dia_escolhido) for dia_escolhido in self.dias_escolhidos.all()]),
                self.data_escolha.strftime('%d/%m/%Y'),
                url,
                url,
            )
            send_notification(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [self.funcionario.get_vinculo()])

    def dias_efetivos_a_compensar(self, retornar_tambem_contexto_compensacao=False, contexto_compensacao=None):
        """
            retorna [date, date, date, ...] ou [[date, date, date, ...], instância de Contexto]

            se um contexto não for fornecido, mas for solicitado o seu retorno, será criado um contexto dentro
            do período dos dias efetivos a compensar e sem o cálculo de uma possível distribuíção de débitos e saldos.
        """

        subconjunto_dos_dias = []
        contexto = contexto_compensacao
        erro_no_cache = False

        if self.dias_efetivos_a_compensar_cache:
            try:
                subconjunto_dos_dias = [
                    datetime.datetime.strptime(data_string.strip(), '%d/%m/%Y').date() for data_string in self.dias_efetivos_a_compensar_cache.split(';') if data_string
                ]
            except Exception:
                erro_no_cache = True

        if erro_no_cache or not self.dias_efetivos_a_compensar_cache:
            todos_os_dias = [dia_escolhido.dia.data for dia_escolhido in self.dias_escolhidos.all().select_related('dia')]

            if todos_os_dias:
                if contexto:
                    for dia in todos_os_dias:
                        if contexto.get_dia(dia, add_se_nao_existir=True).is_debito:
                            subconjunto_dos_dias.append(dia)
                else:
                    from ponto.compensacao import Contexto

                    contexto = Contexto(self.funcionario, min(todos_os_dias), max(todos_os_dias))

                    for dia_debito in list(contexto.dias_debitos.keys()):
                        if dia_debito in todos_os_dias:
                            subconjunto_dos_dias.append(dia_debito)

        subconjunto_dos_dias = sorted(subconjunto_dos_dias)

        if not self.dias_efetivos_a_compensar_cache:
            if subconjunto_dos_dias:
                self.dias_efetivos_a_compensar_cache = ';'.join([data.strftime('%d/%m/%Y') for data in subconjunto_dos_dias])
            else:
                self.dias_efetivos_a_compensar_cache = ';'  # cache mínimo não vazio
            self.save()

        if retornar_tambem_contexto_compensacao:
            if not contexto and subconjunto_dos_dias:
                from ponto.compensacao import Contexto

                contexto = Contexto(self.funcionario, min(subconjunto_dos_dias), max(subconjunto_dos_dias))

            return subconjunto_dos_dias, contexto

        return subconjunto_dos_dias

    def compensacoes(self):
        """ retorna uma lista com as compensações (instâncias de HorararioCompensacao) já informadas para
            os dias efetivos a compensar
        """
        compensacoes = HorarioCompensacao.objects.filter(funcionario=self.funcionario, data_aplicacao__in=self.dias_efetivos_a_compensar()).order_by(
            'data_aplicacao', 'data_compensacao'
        )
        return compensacoes

    def totais_ch(self, carga_horaria_total=False, carga_horaria_debito_considerado=False, carga_horaria_compensada=False, carga_horaria_pendente=False):
        total_carga_horaria_total = 0
        total_carga_horaria_debito_considerado = 0
        total_carga_horaria_compensada = 0
        total_carga_horaria_pendente = 0
        dias_a_compensar = []
        contexto_compensacao = None

        if carga_horaria_total or carga_horaria_compensada or carga_horaria_pendente:
            dias_a_compensar, contexto_compensacao = self.dias_efetivos_a_compensar(retornar_tambem_contexto_compensacao=True)

            for dia_a_compensar in dias_a_compensar:
                if carga_horaria_total:
                    total_carga_horaria_total += contexto_compensacao.get_dia(dia_a_compensar).carga_horaria_qtd

                if carga_horaria_debito_considerado:
                    total_carga_horaria_debito_considerado += contexto_compensacao.get_dia(dia_a_compensar).debito_qtd_considerado

                if carga_horaria_compensada:
                    total_carga_horaria_compensada += contexto_compensacao.get_dia(dia_a_compensar).debito_qtd_reposto

                if carga_horaria_pendente:
                    total_carga_horaria_pendente += contexto_compensacao.get_dia(dia_a_compensar).debito_qtd_restante

        return dict(
            total_carga_horaria_total=total_carga_horaria_total,
            total_carga_horaria_debito_considerado=total_carga_horaria_debito_considerado,
            total_carga_horaria_compensada=total_carga_horaria_compensada,
            total_carga_horaria_pendente=total_carga_horaria_pendente,
            dias_a_compensar=dias_a_compensar,
            contexto_compensacao=contexto_compensacao,
        )

    def pode_excluir(self, relacionamento):
        usuario_eh_o_solicitante = relacionamento == self.funcionario
        recesso_opcao_escolhida_estah_aguardando_validacao = self.is_aguardando
        recesso_opcao_escolhida_tem_compensacoes_informadas = self.compensacoes().exists()
        recesso_opcao_escolhida_com_dias_livremente_selecionados = self.recesso_opcao.is_permite_escolha_dos_dias_pelos_servidores
        # recesso_opcao_estah_com_cadastro_concluido = self.recesso_opcao.is_concluido_cadastro_e_escolhas_de_datas
        return (
            usuario_eh_o_solicitante
            and recesso_opcao_escolhida_com_dias_livremente_selecionados
            # and recesso_opcao_estah_com_cadastro_concluido
            and (recesso_opcao_escolhida_estah_aguardando_validacao or not recesso_opcao_escolhida_tem_compensacoes_informadas)
        )

    @staticmethod
    def get_recessos_escolhidos_aguardando_validacao_hoje(validador):
        hoje = datetime.date.today()
        queryset = RecessoOpcaoEscolhida.objects.filter(
            # funcionários que eu vou validar
            validacao=RecessoOpcaoEscolhida.VALIDACAO_AGUARDANDO,
            recesso_opcao__situacao=RecessoOpcao.SITUACAO_ABERTO_PARA_ESCOLHA_DE_DATAS,
            recesso_opcao__periodo_de_escolha_data_inicial__lte=hoje,
            recesso_opcao__periodo_de_escolha_data_final__gte=hoje,
        )
        return queryset.filter(Q(validador=validador) | Q(funcionario__setor_id__in=validador.historico_funcao(hoje, hoje).values_list('setor_suap_id', flat=True)))

    @staticmethod
    def has_recessos_escolhidos(servidor):
        return RecessoOpcaoEscolhida.objects.filter(funcionario=servidor, validacao=RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO).exists()


class RecessoDiaEscolhido(models.Model):
    """ Representa um dia de recesso escolhido por um servidor/funcionário
    """

    class Meta:
        verbose_name = 'Dia Escolhido do Recesso'
        verbose_name_plural = 'Dias Escolhidos do Recesso'
        ordering = ('dia__data',)

    recesso_opcao_escolhida = models.ForeignKeyPlus('ponto.RecessoOpcaoEscolhida', editable=False, related_name='dias_escolhidos', on_delete=models.CASCADE)
    dia = models.ForeignKeyPlus('ponto.RecessoDia', verbose_name='Dia de Recesso', on_delete=models.CASCADE)

    def __str__(self):
        return '{}'.format(self.dia.data.strftime('%d/%m/%Y'))


class RecessoCompensacao(HorarioCompensacao):
    """ Representa um informe de compensação de horário de um dia de recesso escolhido/gozado.
        Ponto de "conexão" com a implementação ref. aos informes de compensação de horário.
    """

    dia_escolhido = models.ForeignKeyPlus('ponto.RecessoDiaEscolhido', editable=False, on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Informe de Compensação de Horário de Recesso'
        verbose_name_plural = 'Informes de Compensação de Horário de Recessos'


##########################################################################################
##########################################################################################
