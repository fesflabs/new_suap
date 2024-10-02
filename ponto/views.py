import csv
import os
import time
import zipfile
from datetime import date, datetime, timedelta
from os import stat
from os.path import exists
from urllib.parse import urlencode
import ipaddress
from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import connection, transaction
from django.db.models.expressions import Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize
from django.views.decorators.csrf import csrf_exempt

from comum.models import Configuracao, PrestadorServico
from comum.utils import agrupar_em_pares, data_normal, datas_entre, extrair_periodo, formata_segundos
from djtools import layout
from djtools.storages import cache_file
from djtools.templatetags.filters import format_
from djtools.utils import (
    djtools_max,
    djtools_min,
    get_client_ip,
    get_real_sql,
    get_session_cache,
    httprr,
    permission_required,
    primeiro_dia_da_semana,
    render,
    rtr,
    str_to_dateBR,
)
from ponto.compensacao import Contexto
from ponto.enums import TipoFormFrequenciaTerceirizados
from ponto.forms import (
    AbonoChefiaFormFactory,
    AbonoChefiaLoteFormFactory,
    DocumentoAnexoChangeForm,
    DocumentoAnexoForm,
    FrequenciaCargoEmpregoFormFactory,
    FrequenciaFuncionarioFormFactory,
    FrequenciaNoturnaFormFactory,
    FrequenciaTerceirizadosFormFactory,
    HorarioCompensacaoEditarObservacoesPontoForm,
    HorarioCompensacaoPeriodoForm,
    LocalizarServidorForm,
    ObservacaoForm,
    RecessoDiaAddForm,
    RecessoOpcaoEscolhidaEditarChefeForm,
    RecessoOpcaoEscolhidaEditarForm,
    RecessoOpcaoEscolhidaValidarForm,
    RecessoPeriodoCompensacaoAddForm,
    RecessoPeriodoEscolhaForm,
    get_type_form_dias_escolhidos,
    get_type_form_multiplas_compensacao_horario,
    setor_raiz_por_permissao_ponto,
    FrequenciaDocenteFormFactory,
    FrequenciasPorSetorFormFactory,
)
from ponto.models import (
    AbonoChefia,
    DocumentoAnexo,
    Frequencia,
    HorarioCompensacao,
    Maquina,
    MaquinaLog,
    Observacao,
    RecessoDia,
    RecessoDiaEscolhido,
    RecessoOpcao,
    RecessoOpcaoEscolhida,
    RecessoPeriodoCompensacao,
)
from ponto.utils import (
    get_data_ultimo_dia_mes_corrente,
    get_relatorios_ponto_adaptados_para_relatorios_pit_rit_ponto_docente,
    get_response_xls_registros_frequencias,
    get_total_tempo_debito_pendente_mes_anterior,
    get_total_tempo_debito_pendente_semana_anterior,
    is_request_xls,
    pode_ver_frequencia,
    get_total_tempo_saldo_restante_mes_corrente,
    get_total_tempo_debito_pendente_mes_corrente,
)
from rh.models import Funcao, Funcionario, Servidor, Setor


@layout.alerta()
def index_alertas(request):
    alertas = list()
    return alertas


@layout.quadro('Frequências', icone='clock')
def index_quadros_frequencias(quadro, request):
    hoje = datetime.now()
    sub_instance = request.user.get_relacionamento()
    if request.user.eh_servidor:
        servidor = sub_instance

        # compensação de horários - acompanhamento de débitos específicos
        recessos_a_analisar = RecessoOpcaoEscolhida.get_recessos_escolhidos_aguardando_validacao_hoje(servidor)
        if recessos_a_analisar.exists():
            qtd = recessos_a_analisar.count()
            quadro.add_item(
                layout.ItemContador(
                    titulo='Compensaç{} de Horário'.format(pluralize(qtd, 'ão,ões')),
                    subtitulo='Aguardando sua validação',
                    qtd=qtd,
                    url='/admin/ponto/recessoopcaoescolhida/?tab=recessos_do_setor&validacao__exact={}'.format(RecessoOpcaoEscolhida.VALIDACAO_AGUARDANDO),
                )
            )

        # somente RH
        if request.user.has_perm('add_recessoopcao'):
            # tenta concluir opções abertas com tempo de escolha expirado
            RecessoOpcao.set_concluir_recessos_opcoes_pendentes()

            recessos_pendentes = RecessoOpcao.get_recessos_opcoes_periodo_escolha_expirado()
            if recessos_pendentes.exists():
                qtd = recessos_pendentes.count()
                quadro.add_item(
                    layout.ItemContador(
                        titulo='Opç{} de Compensação de Horário'.format(pluralize(qtd, 'ão,ões')),
                        subtitulo='Em aberto com período de escolha expirado',
                        qtd=qtd,
                        url='/admin/ponto/recessoopcao/?situacao__exact={}'.format(RecessoOpcao.SITUACAO_ABERTO_PARA_ESCOLHA_DE_DATAS),
                    )
                )

    if request.user.eh_servidor or request.user.eh_prestador and not request.user.get_vinculo().eh_usuario_externo():
        vinculo = request.user.get_vinculo()
        funcionario = vinculo.relacionamento

        if funcionario.eh_prestador or (funcionario.eh_servidor and not funcionario.eh_aposentado):
            total_tempo_hoje = 0
            total_tempo_semana = 0
            frequencias_hoje = Frequencia.objects.none()
            for dia in datas_entre(primeiro_dia_da_semana(hoje), hoje):
                frequencias_dia = Frequencia.get_frequencias_por_data(vinculo, dia)
                if dia == hoje:
                    frequencias_hoje = frequencias_dia
                    if frequencias_hoje.exists():
                        tempo = 0
                        for par in agrupar_em_pares(frequencias_hoje.values_list('horario', flat=True)):
                            if len(par) == 2:
                                delta = par[1] - par[0]
                                segundos = delta.seconds
                            else:
                                segundos = 0
                            tempo += segundos
                        if frequencias_hoje.latest('horario').acao == 'E':
                            momento_da_entrada = frequencias_hoje.latest('horario').horario
                            momento_agora = datetime.now()
                            while momento_agora < momento_da_entrada:
                                momento_agora = datetime.now()
                            delta = momento_agora - momento_da_entrada
                            segundos = delta.seconds
                            tempo += segundos
                        total_tempo_hoje = time.strftime('%H:%M:%S', time.gmtime(tempo))
                        total_tempo_semana += tempo
                else:
                    total_tempo_semana += Frequencia.get_tempo_entre_frequencias(frequencias_dia)
            total_tempo_semana = formata_segundos(total_tempo_semana, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)

            if frequencias_hoje or total_tempo_semana:
                if frequencias_hoje:
                    valor_hoje = ''
                    for i, f in enumerate(frequencias_hoje):
                        if i > 0:
                            valor_hoje += " | "
                        if f.acao == "E":
                            classe = 'true'
                        else:
                            classe = 'false'
                        valor_hoje += '{}: <span class="{}">{}</span>'.format(f.acao, classe, f.horario.strftime('%H:%M'))
                else:
                    valor_hoje = '<span class="false">Não há registro de frequências.</span>'

                quadro.add_item(layout.ItemLista(titulo='Hoje', valor=valor_hoje))
                if total_tempo_hoje:
                    quadro.add_item(layout.ItemLista(titulo='Total de Hoje', valor=total_tempo_hoje))
                if total_tempo_semana:
                    quadro.add_item(layout.ItemLista(titulo='Total da Semana', valor=total_tempo_semana))

            url_freq = '/ponto/frequencia_funcionario/'
            if funcionario.eh_prestador:
                url_freq = '/ponto/frequencia_terceirizados/'
            quadro.add_item(layout.ItemAcessoRapido(titulo='Frequências', url=url_freq, icone='calendar-alt'))

            if not funcionario.eh_prestador and not funcionario.eh_docente:
                eh_docente_tem_recessos_escolhidos = funcionario.eh_docente and RecessoOpcaoEscolhida.has_recessos_escolhidos(funcionario)
                if not funcionario.eh_docente or eh_docente_tem_recessos_escolhidos:
                    quadro.add_item(layout.ItemAcessoRapido(titulo='Informar Compensação', url='/ponto/adicionar_compensacao/', icone='exchange-alt'))
                if Configuracao.get_valor_por_chave('ponto', 'subnets_ponto_online'):
                    quadro.add_item(
                        layout.ItemAcessoRapido(titulo='Registrar Frequência', url='/ponto/registrar_frequencia_online/', icone=None, classe='success')
                    )

        if funcionario.eh_servidor and not funcionario.eh_docente and not funcionario.eh_liberado_controle_frequencia():
            ###
            # débito da semana passada
            total_tempo_debito_pendente_semana_anterior = get_session_cache(
                request, 'total_tempo_debito_pendente_semana_anterior', get_total_tempo_debito_pendente_semana_anterior, 5 * 60
            )

            deb_semana_anterior, _ = total_tempo_debito_pendente_semana_anterior
            if deb_semana_anterior > 0:
                quadro.add_item(
                    layout.ItemLista(
                        grupo='Compensações:',
                        titulo='Débito Pendente da Semana Passada',
                        valor='<span class="{}">{}</span>'.format(
                            'false' if deb_semana_anterior > 0 else 'true', formata_segundos(deb_semana_anterior, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)
                        ),
                    )
                )

            ###
            # débito do mês passado
            total_tempo_debito_pendente_mes_anterior = get_session_cache(request, 'total_tempo_debito_pendente_mes_anterior', get_total_tempo_debito_pendente_mes_anterior, 5 * 60)

            deb_mes_anterior, deb_mes_anterior_ate_mes_atual = total_tempo_debito_pendente_mes_anterior
            if deb_mes_anterior > 0:
                css_span = 'false' if deb_mes_anterior > 0 else 'true'
                deb_span = formata_segundos(deb_mes_anterior, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)
                quadro.add_item(layout.ItemLista(grupo='Compensações:', titulo='Débito Pendente do Mês Passado', valor='<span class="{}">{}</span>'.format(css_span, deb_span)))

            ###
            # débito do mês corrente
            total_tempo_debito_pendente_mes_corrente = get_session_cache(request, 'total_tempo_debito_pendente_mes_corrente', get_total_tempo_debito_pendente_mes_corrente, 5 * 60)

            deb_mes_corrente = total_tempo_debito_pendente_mes_corrente
            if deb_mes_corrente > 0:
                deb_span = formata_segundos(deb_mes_corrente, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)
                quadro.add_item(layout.ItemLista(grupo='Compensações:', titulo='Débito Pendente do Mês Atual', valor='<span class="false">{}</span>'.format(deb_span)))

            ###
            # débito a ser compensado até o final do mês corrente
            css_span = '' if deb_mes_anterior == deb_mes_anterior_ate_mes_atual else 'false' if deb_mes_anterior_ate_mes_atual > 0 else 'true'
            deb_span = (
                ''
                if deb_mes_anterior == deb_mes_anterior_ate_mes_atual
                else '<strong>{}</strong>'.format(formata_segundos(deb_mes_anterior_ate_mes_atual, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True))
            )
            if css_span != '':
                quadro.add_item(
                    layout.ItemLista(
                        grupo='Compensações:',
                        titulo='Débito a ser compensado até {}'.format(get_data_ultimo_dia_mes_corrente().strftime('%d/%m/%Y')),
                        valor='<span class="{}">{}</span>'.format(css_span, deb_span),
                    )
                )

            ###
            # saldo restante do mês corrente
            total_tempo_saldo_restante_mes_corrente = get_session_cache(request, 'total_tempo_saldo_restante_mes_corrente', get_total_tempo_saldo_restante_mes_corrente, 5 * 60)

            saldo_mes_atual = total_tempo_saldo_restante_mes_corrente
            if saldo_mes_atual > 0:
                saldo_span = formata_segundos(saldo_mes_atual, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)
                quadro.add_item(layout.ItemLista(grupo='Compensações:', titulo='Saldo Restante do Mês Atual', valor='<span class="true">{}</span>'.format(saldo_span)))

    return quadro


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()

    if request.user.eh_servidor:
        servidor = request.user.get_relacionamento()
        recessos_opcoes = RecessoOpcao.get_recessos_opcoes_com_dias_a_escolher_hoje(servidor)
        for recesso_opcao in recessos_opcoes.get('com_dias_a_escolher'):
            inscricoes.append(
                dict(
                    titulo='<strong>{}</strong>: ' 'Há dias disponíveis que você pode escolher.'.format(recesso_opcao),
                    url='/ponto/escolher_dia_de_recesso/',
                    prazo='{}'.format(recesso_opcao.periodo_de_escolha_data_final.strftime('%d/%m/%Y')),
                )
            )
        for recesso_opcao in recessos_opcoes.get('com_dias_a_editar'):
            validador_nao_definido = RecessoOpcaoEscolhida.objects.filter(recesso_opcao=recesso_opcao, funcionario=servidor, validador__isnull=True).exists()

            inscricoes.append(
                dict(
                    titulo='<strong>{}</strong>: '
                    'Você ainda pode <strong>editar</strong> os dias escolhidos.{}'.format(
                        recesso_opcao, '<strong> Não é possível validar sua escolha, pois o validador não foi definido.</strong>.' if validador_nao_definido else ''
                    ),
                    url='/ponto/escolher_dia_de_recesso/',
                    prazo='{}'.format(recesso_opcao.periodo_de_escolha_data_final.strftime('%d/%m/%Y')),
                )
            )
        for recesso_opcao in recessos_opcoes.get('com_dias_a_remarcar'):
            opcoes_escolhidas = RecessoOpcaoEscolhida.objects.filter(recesso_opcao=recesso_opcao, funcionario=servidor)
            for opcao_escolhida in opcoes_escolhidas:
                inscricoes.append(
                    dict(
                        titulo='<strong>{}</strong>: '
                        'Os dias que você escolheu <strong>não foram autorizados</strong>.'
                        '<strong>Remarque-os</strong> novamente.'.format(recesso_opcao),
                        url='/ponto/abrir_recesso_escolhido/{}/'.format(opcao_escolhida.id),
                        prazo='{}'.format(recesso_opcao.periodo_de_escolha_data_final.strftime('%d/%m/%Y')),
                    )
                )

    return inscricoes


@layout.info()
def index_infos(request):
    infos = list()

    if request.user.eh_servidor:
        funcionario = request.user.get_relacionamento()
        recessos_opcoes = RecessoOpcao.get_recessos_opcoes_abertos_e_autorizados(funcionario)
        for recesso_opcao in recessos_opcoes:
            opcoes_escolhidas = RecessoOpcaoEscolhida.objects.filter(recesso_opcao=recesso_opcao, funcionario=funcionario)
            for opcao_escolhida in opcoes_escolhidas:
                infos.append(
                    dict(
                        titulo=f'<strong>{recesso_opcao}</strong>: O período que você escolheu <strong>foi autorizado</strong>.',
                        url='/ponto/abrir_recesso_escolhido/{}/'.format(opcao_escolhida.id),
                    )
                )

        recessos_opcoes = RecessoOpcao.get_recessos_opcoes_abertos_e_nao_autorizados(funcionario)
        for recesso_opcao in recessos_opcoes:
            opcoes_escolhidas = RecessoOpcaoEscolhida.objects.filter(recesso_opcao=recesso_opcao, funcionario=funcionario)
            for opcao_escolhida in opcoes_escolhidas:
                infos.append(
                    dict(
                        titulo='<strong>{}</strong>: ' 'O período que você escolheu <strong>não foi autorizado</strong>.'.format(recesso_opcao),
                        url='/ponto/abrir_recesso_escolhido/{}/'.format(opcao_escolhida.id),
                    )
                )
    return infos


def frequencia_funcionario_get_escopo_relatorio_ponto_pessoa(request, funcionario_logado, form):
    servidor = form.cleaned_data['funcionario']
    servidor_is_docente = servidor.eh_docente

    data_inicio = form.cleaned_data['faixa_0']
    data_fim = form.cleaned_data['faixa_1']
    so_inconsistentes = form.cleaned_data.get('so_inconsistentes', False)
    if so_inconsistentes:
        title = 'Frequências Inconsistentes do Funcionário: {}'.format(servidor)
    else:
        title = 'Frequências do Funcionário: {}'.format(servidor)

    pode_ver_frequencias = False
    if servidor.cpf == funcionario_logado.cpf or request.user.has_perm('ponto.pode_ver_frequencia_todos'):
        pode_ver_frequencias = True

    dias_em_que_foi_chefe_setor = []
    dias_em_que_estava_no_campus = []
    if funcionario_logado.eh_servidor:
        setores_funcionario = servidor.historico_setor_suap(data_inicio, data_fim)
        funcoes_servidor_logado = funcionario_logado.historico_funcao(data_inicio, data_fim).filter(setor_suap__isnull=False, funcao__codigo__in=Funcao.get_codigos_funcao_chefia())
        tem_funcao_no_periodo = funcoes_servidor_logado.exists()
        for setor_funcionario in setores_funcionario:
            if not pode_ver_frequencias and request.user.has_perm('ponto.pode_ver_frequencia_campus') and funcionario_logado.setor.uo == setor_funcionario.setor.uo:
                data_inicio_setor_referencia = djtools_max(setor_funcionario.data_inicio_no_setor, data_inicio)
                data_fim_setor_referencia = djtools_min(setor_funcionario.data_fim_no_setor, data_fim)
                if not dias_em_que_estava_no_campus:
                    dias_em_que_estava_no_campus = datas_entre(data_inicio_setor_referencia, data_fim_setor_referencia)
                else:
                    dias_em_que_estava_no_campus += datas_entre(data_inicio_setor_referencia, data_fim_setor_referencia)
                pode_ver_frequencias = True

            if tem_funcao_no_periodo:
                for funcao_servidor in funcoes_servidor_logado:
                    if setor_funcionario.setor in funcao_servidor.setor_suap.descendentes:
                        data_referencia_inicio_chefia = djtools_max(setor_funcionario.data_inicio_no_setor, data_inicio, funcao_servidor.data_inicio_funcao)
                        data_referencia_fim_chefia = djtools_min(setor_funcionario.data_fim_no_setor, data_fim, funcao_servidor.data_fim_funcao)
                        dias_em_que_foi_chefe_setor += datas_entre(data_referencia_inicio_chefia, data_referencia_fim_chefia)

    so_frequencias_em_que_era_chefe = False
    if not pode_ver_frequencias and dias_em_que_foi_chefe_setor:
        pode_ver_frequencias = True
        so_frequencias_em_que_era_chefe = True

    so_inconsistentes_apenas_esta_inconsistencia = None
    so_inconsistentes_situacao_abono = Frequencia.SITUACAO_INCONSISTENCIA_COM_OU_SEM_ABONO
    so_inconsistentes_situacao_debito = Frequencia.SITUACAO_INCONSISTENCIA_COM_DEBITO_COMPENSADO_OU_PENDENTE
    if so_inconsistentes:
        so_inconsistentes_apenas_esta_inconsistencia = form.cleaned_data.get('so_inconsistentes_apenas_esta_inconsistencia', None)
        so_inconsistentes_situacao_abono = form.cleaned_data.get('so_inconsistentes_situacao_abono', Frequencia.SITUACAO_INCONSISTENCIA_COM_OU_SEM_ABONO)
        so_inconsistentes_situacao_debito = form.cleaned_data.get('so_inconsistentes_situacao_debito', Frequencia.SITUACAO_INCONSISTENCIA_COM_DEBITO_COMPENSADO_OU_PENDENTE)

    return {
        'title': title,
        'servidor': servidor,
        'servidor_is_docente': servidor_is_docente,
        'data_inicio': data_inicio,
        'data_fim': data_fim,
        'dias_em_que_foi_chefe_setor': dias_em_que_foi_chefe_setor,
        'so_frequencias_em_que_era_chefe': so_frequencias_em_que_era_chefe,
        'dias_em_que_estava_no_campus': dias_em_que_estava_no_campus,
        'so_inconsistentes': so_inconsistentes,
        'pode_ver_frequencias': pode_ver_frequencias,
        'so_inconsistentes_apenas_esta_inconsistencia': so_inconsistentes_apenas_esta_inconsistencia,
        'so_inconsistentes_situacao_abono': so_inconsistentes_situacao_abono,
        'so_inconsistentes_situacao_debito': so_inconsistentes_situacao_debito,
    }


def frequencia_funcionario_get_relatorio_ponto_pessoa_info(request, servidor, data_inicio, data_fim):
    relacionamento_logado = request.user.get_relacionamento()

    escopo = ''

    if request.user.has_perm('ponto.pode_ver_frequencia_todos'):
        escopo = 'todos'
    elif request.user.has_perm('ponto.pode_ver_frequencia_campus') and servidor.setor.uo == relacionamento_logado.setor.uo:
        escopo = 'campus'
    elif request.user.has_perm('ponto.pode_ver_frequencias_enquanto_foi_chefe'):
        for setor in servidor.setor_suap_servidor_por_periodo(data_inicio, data_fim):
            if relacionamento_logado.eh_chefe_do_setor_periodo(setor, data_inicio, data_fim):
                escopo = 'chefe'

    if not escopo:
        return HttpResponseForbidden('Você não pode visualizar frequências desse servidor.')

    relatorio = Frequencia.relatorio_ponto_pessoa_novo(
        vinculo=servidor.get_vinculo(), servidor_logado=relacionamento_logado, data_ini=data_inicio, data_fim=data_fim, escopo=escopo
    )

    return locals()


@rtr()
@login_required
def frequencia_funcionario(request):
    title = 'Frequências por Servidor'

    if not request.user.has_perm('ponto.pode_ver_frequencia_propria') and not request.user.has_perm('ponto.pode_ver_frequencia_todos'):
        raise PermissionDenied("Usuário não pode ver frequencia própria.")

    if request.user.eh_docente and 'pit_rit' in settings.INSTALLED_APPS and Configuracao.get_valor_por_chave('pit_rit', 'ponto_docente_ativado'):
        form_class = FrequenciaDocenteFormFactory(request)
    else:
        form_class = FrequenciaFuncionarioFormFactory(request)

    form = form_class(request.GET or None)

    funcionario_logado = request.user.get_relacionamento()

    if not funcionario_logado.setor:
        raise PermissionDenied('Servidor não está associado a nenhum setor.')

    if form.is_valid():
        escopo_relatorio_ponto_pessoa = frequencia_funcionario_get_escopo_relatorio_ponto_pessoa(request, funcionario_logado, form)

        pode_ver_frequencias = escopo_relatorio_ponto_pessoa['pode_ver_frequencias']
        if not pode_ver_frequencias:
            raise PermissionDenied('Você não tem permissão para visualizar a frequência deste servidor para o período informado.')

        servidor_is_docente = escopo_relatorio_ponto_pessoa['servidor_is_docente']
        if servidor_is_docente and 'pit_rit' in settings.INSTALLED_APPS and Configuracao.get_valor_por_chave('pit_rit', 'ponto_docente_ativado'):
            from pit_rit.views import frequencia_docente

            return frequencia_docente(request)

        title = escopo_relatorio_ponto_pessoa['title']
        servidor = escopo_relatorio_ponto_pessoa['servidor']
        data_inicio = escopo_relatorio_ponto_pessoa['data_inicio']
        data_fim = escopo_relatorio_ponto_pessoa['data_fim']
        dias_em_que_foi_chefe_setor = escopo_relatorio_ponto_pessoa['dias_em_que_foi_chefe_setor']
        so_frequencias_em_que_era_chefe = escopo_relatorio_ponto_pessoa['so_frequencias_em_que_era_chefe']
        dias_em_que_estava_no_campus = escopo_relatorio_ponto_pessoa['dias_em_que_estava_no_campus']
        so_inconsistentes = escopo_relatorio_ponto_pessoa['so_inconsistentes']
        so_inconsistentes_apenas_esta_inconsistencia = escopo_relatorio_ponto_pessoa['so_inconsistentes_apenas_esta_inconsistencia']
        so_inconsistentes_situacao_abono = escopo_relatorio_ponto_pessoa['so_inconsistentes_situacao_abono']
        so_inconsistentes_situacao_debito = escopo_relatorio_ponto_pessoa['so_inconsistentes_situacao_debito']

        relatorios = []
        relatorio_pessoa = Frequencia.relatorio_ponto_pessoa(
            vinculo=servidor.get_vinculo(),
            data_ini=data_inicio,
            data_fim=data_fim,
            dias_em_que_foi_chefe_setor=dias_em_que_foi_chefe_setor,
            so_frequencias_em_que_era_chefe=so_frequencias_em_que_era_chefe,
            dias_em_que_estava_no_campus=dias_em_que_estava_no_campus,
            so_inconsistentes=so_inconsistentes,
            trata_compensacoes=True,
            so_inconsistentes_apenas_esta_inconsistencia=so_inconsistentes_apenas_esta_inconsistencia,
            so_inconsistentes_situacao_abono=so_inconsistentes_situacao_abono,
            so_inconsistentes_situacao_debito=so_inconsistentes_situacao_debito,
        )

        # verifica se o período possui saldos produzidos de carga horária que podem ser utilizados
        if 'totais_compensacao' in relatorio_pessoa:
            ha_dias_com_saldo = not relatorio_pessoa['totais_compensacao']['total_saldo_restante_is_zero']

        relatorios.append(relatorio_pessoa)

        hoje = datetime.date(datetime.today())

        if is_request_xls(request):
            xls = get_response_xls_registros_frequencias(relatorios)

            if xls:
                return xls

        return render('ponto/templates/relatorio_frequencia.html', locals())

    return locals()


@login_required()
def registrar_frequencia_online(request):
    subredes = Configuracao.get_valor_por_chave('ponto', 'subnets_ponto_online')
    if subredes:
        ip_valido = False
        ip = get_client_ip(request)
        for subrede in subredes.split(';'):
            ip_valido = ip_valido or ipaddress.ip_address(ip) in ipaddress.ip_network(subrede)
        if ip_valido:
            maquina = Maquina.objects.get_or_create(descricao='Ponto Online', ip='127.0.0.1', ativo=True, cliente_ponto=True)[0]
            Frequencia.insere_frequencia(request.user.get_vinculo(), maquina=maquina, ip=ip)
            return httprr('/', 'Frequência registrada com sucesso')
    return HttpResponseForbidden()


@rtr()
@login_required()
@permission_required('ponto.pode_ver_frequencia_todos, ponto.pode_ver_frequencia_campus, ponto.pode_ver_frequencias_enquanto_foi_chefe')
def ajax_frequencia_funcionario(request):
    servidor = get_object_or_404(Servidor.objects, matricula=request.GET.get('matricula', 0))
    data_inicio = datetime.strptime(request.GET.get('data_inicio', datetime.today().strftime('%d/%m/%Y')), '%d/%m/%Y').date()
    data_fim = datetime.strptime(request.GET.get('data_fim', datetime.today().strftime('%d/%m/%Y')), '%d/%m/%Y').date()
    relatorio_info = frequencia_funcionario_get_relatorio_ponto_pessoa_info(request, servidor, data_inicio, data_fim)
    if isinstance(relatorio_info, HttpResponseForbidden):
        return relatorio_info
    relatorio_info.update(locals())

    if is_request_xls(request):
        try:
            xls = get_response_xls_registros_frequencias([relatorio_info['relatorio']])

            if xls:
                return xls
        except Exception:
            pass

    return relatorio_info


@rtr()
@login_required
@permission_required('ponto.pode_ver_frequencia_todos, ponto.pode_ver_frequencia_campus, ponto.pode_ver_frequencias_enquanto_foi_chefe')
def relatorio_frequencias_setor(request):
    permissoes = ['ponto.pode_ver_frequencia_todos', 'ponto.pode_ver_frequencia_campus', 'ponto.pode_ver_frequencias_enquanto_foi_chefe']
    title = "Relatório de Frequências por Setor"
    FormClass = FrequenciasPorSetorFormFactory(request)
    form = FormClass(request.GET or None)
    funcionario_logado = request.user.get_relacionamento()

    if form.is_valid():
        setor = form.cleaned_data['setor']
        recursivo = form.cleaned_data['recursivo']
        faixa_0 = form.cleaned_data['faixa_0']
        faixa_1 = form.cleaned_data['faixa_1']

        title = f"Relatório de Frequências por Setor - {setor.sigla} {'e Setores descendentes' if form.cleaned_data['recursivo'] else ''}"

        servidores = setor.get_servidores_por_periodo(data_inicial=faixa_0, data_final=faixa_1, recursivo=recursivo)
        caminho_setor = setor.get_caminho_setor(setor_raiz_por_permissao_ponto(request))
        url_frequencias = "relatorio_frequencias_setor"
        filhos = Setor.objects.filter(pk__in=setor.filhos.values_list('pk', flat=True))

        if is_request_xls(request):
            relatorios = []

            for servidor in servidores:
                try:
                    relatorio_info = frequencia_funcionario_get_relatorio_ponto_pessoa_info(request, servidor, faixa_0, faixa_1)
                    relatorios.append(relatorio_info['relatorio'])
                except Exception:
                    pass

            if relatorios:
                xls_todos = get_response_xls_registros_frequencias(relatorios, filename=title)

                if xls_todos:
                    return xls_todos

    return locals()


@rtr()
@login_required
@permission_required('ponto.pode_ver_frequencia_terceirizados_todos, ponto.pode_ver_frequencia_terceirizados_campus, ponto.pode_ver_frequencia_terceirizados_setor')
def frequencia_terceirizados_setor(request):
    title = "Frequências por Prestador de Serviço"

    FormClass = FrequenciaTerceirizadosFormFactory(request, TipoFormFrequenciaTerceirizados.POR_SETOR)
    form = FormClass(request.GET or None)
    if form.is_valid():
        ocupacao = form.cleaned_data['ocupacao']
        setor = form.cleaned_data['setor']
        funcionarios = Frequencia.relatorio_terceirizados(
            terceirizado=None,
            setor=form.cleaned_data['setor'],
            recursivo=form.cleaned_data['recursivo'],
            ocupacao=ocupacao,
            data_ini=form.cleaned_data['faixa_0'],
            data_fim=form.cleaned_data['faixa_1'],
        )
        data_ini = data_normal(form.cleaned_data['faixa_0'])
        data_fim = data_normal(form.cleaned_data['faixa_1'])

        situacao = 'Terceirizado'
        periodo = '{} a {}'.format(data_ini, data_fim)
        return render('ponto/templates/relatorio_frequencia_terceirizados.html', locals())
    else:
        return locals()


@rtr()
@login_required
@permission_required('ponto.pode_ver_frequencia_terceirizados_todos, ponto.pode_ver_frequencia_terceirizados_campus, ponto.pode_ver_frequencia_terceirizados_setor, ponto.pode_ver_frequencia_terceirizados_propria')
def frequencia_terceirizados(request):
    title = "Frequências por Prestador de Serviço"
    FormClass = FrequenciaTerceirizadosFormFactory(request, TipoFormFrequenciaTerceirizados.POR_TERCEIRIZADO)
    form = FormClass(request.GET or None)
    if form.is_valid():
        terceirizado = form.cleaned_data['terceirizado']
        funcionarios = Frequencia.relatorio_terceirizados(
            terceirizado=terceirizado, setor=None, recursivo=form.cleaned_data.get('recursivo'), data_ini=form.cleaned_data['faixa_0'], data_fim=form.cleaned_data['faixa_1']
        )
        data_ini = data_normal(form.cleaned_data['faixa_0'])
        data_fim = data_normal(form.cleaned_data['faixa_1'])

        situacao = 'Terceirizado'
        periodo = '{} a {}'.format(data_ini, data_fim)
        return render('ponto/templates/relatorio_frequencia_terceirizados.html', locals())
    else:
        return locals()


@rtr()
@login_required
@permission_required('ponto.pode_ver_frequencia_todos, ponto.pode_ver_frequencia_campus, ponto.pode_ver_frequencias_enquanto_foi_chefe')
def frequencia_cargo_emprego(request):
    title = 'Frequência de Cargo/Emprego'
    FormClass = FrequenciaCargoEmpregoFormFactory()
    form = FormClass(request.GET or None)
    relatorios_visiveis = []
    if form.is_valid():
        relatorios = Frequencia.relatorio_cargo_emprego(
            cargo_emprego=form.cleaned_data['cargo_emprego'], data_ini=form.cleaned_data['faixa_0'], data_fim=form.cleaned_data['faixa_1']
        )
        for relatorio in relatorios:
            if pode_ver_frequencia(relatorio['funcionario'], request):
                relatorios_visiveis.append(relatorio)
        relatorios = relatorios_visiveis

        ponto_docente_via_app_pit_rit_is_ativado = 'pit_rit' in settings.INSTALLED_APPS and Configuracao.get_valor_por_chave('pit_rit', 'ponto_docente_ativado')
        if ponto_docente_via_app_pit_rit_is_ativado:
            faixa_0 = form.cleaned_data['faixa_0']
            faixa_1 = form.cleaned_data['faixa_1']
            relatorios = get_relatorios_ponto_adaptados_para_relatorios_pit_rit_ponto_docente(relatorios, faixa_0, faixa_1)

        return render('ponto/templates/relatorio_frequencia.html', locals())
    return locals()


@rtr()
@permission_required('ponto.pode_ver_frequencia_extra_noturna')
def frequencia_noturna(request):
    """
    Retorna as frequências noturnas extras (22h às 23h).
    """
    FormClass = FrequenciaNoturnaFormFactory(request.user)
    title = "Frequências Noturnas"
    form = FormClass(request.GET or None)
    if form.is_valid():
        relatorios = Frequencia.relatorio_noturno(
            cargo_emprego=form.cleaned_data['cargo_emprego'], uo=form.cleaned_data['uo'], data_ini=form.cleaned_data['faixa_0'], data_fim=form.cleaned_data['faixa_1']
        )
        data_ini = data_normal(form.cleaned_data['faixa_0'])
        data_fim = data_normal(form.cleaned_data['faixa_1'])
        situacao = 'Horário extra noturno'
        csv_link = '/ponto/frequencia_noturna_csv/?' + urlencode(request.GET)
        periodo = f'{data_ini} a {data_fim}'

        ponto_docente_via_app_pit_rit_is_ativado = 'pit_rit' in settings.INSTALLED_APPS and Configuracao.get_valor_por_chave('pit_rit', 'ponto_docente_ativado')
        if ponto_docente_via_app_pit_rit_is_ativado:
            faixa_0 = form.cleaned_data['faixa_0']
            faixa_1 = form.cleaned_data['faixa_1']
            relatorios = get_relatorios_ponto_adaptados_para_relatorios_pit_rit_ponto_docente(relatorios, faixa_0, faixa_1)

        return render('ponto/templates/relatorio_frequencia.html', locals())
    return locals()


@login_required
@permission_required('ponto.pode_ver_frequencia_extra_noturna')
def frequencia_noturna_csv(request):
    cargo_emprego = request.GET['cargo_emprego']
    uo = request.GET['uo']
    data_ini = str_to_dateBR(request.GET['faixa_0'])
    data_fim = str_to_dateBR(request.GET['faixa_1'])
    extrair_periodo(data_ini, data_fim)
    relatorio_extra_noturno = Frequencia.relatorio_noturno(cargo_emprego=cargo_emprego, uo=uo, data_ini=data_ini, data_fim=data_fim)
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="relatorio.csv"'
    writer = csv.writer(response)
    for index, f in enumerate(relatorio_extra_noturno):
        funcionario = f['funcionario']
        frequencias = f['frequencias']
        num_frequencias = len(frequencias)
        total_periodo = f['total_periodo'].replace('s', '')
        servidor = [funcionario.matricula, funcionario.nome, num_frequencias, total_periodo]
        writer.writerow(servidor)
    return response


#################################################################
# Métodos para adicionar e remover Observação e Abono de Chefia #
#################################################################
@login_required
@rtr()
@csrf_exempt
def observacao_adicionar(request, data_observacao):
    title = 'Adicionar Observação de Ponto'
    observacao = Observacao(data=datetime.strptime(data_observacao, "%d%m%Y"), vinculo=request.user.get_vinculo())
    tem_abono = AbonoChefia.objects.filter(data=observacao.data, vinculo_pessoa=observacao.vinculo).exists()
    form = ObservacaoForm(request.POST or None, instance=observacao)
    if form.is_valid():
        form.save()
        return httprr('..', 'Observação salva com sucesso.')
    return locals()


@login_required
@rtr()
@csrf_exempt
def observacao_editar(request, observacao_id):
    title = 'Editar Observação de Ponto'
    observacao = get_object_or_404(Observacao, id=observacao_id, vinculo=request.user.get_vinculo())
    tem_abono = AbonoChefia.objects.filter(data=observacao.data, vinculo_pessoa=observacao.vinculo).exists()
    if not tem_abono:
        form = ObservacaoForm(request.POST or None, instance=observacao)
        if form.is_valid():
            form.save()
            return httprr('..', 'Observação editada com sucesso.')
        else:
            return locals()
    else:
        raise PermissionDenied('Acesso negado.')


@login_required
@rtr()
@csrf_exempt
def observacao_remover(request, observacao_id):
    # Nota: existe o filtro por pessoa para evitar que um usuário mal intencionado
    #       remova observações de outras pessoas
    observacao = get_object_or_404(Observacao, id=observacao_id, vinculo=request.user.get_vinculo())
    tem_abono = AbonoChefia.objects.filter(data=observacao.data, vinculo_pessoa=observacao.vinculo).exists()
    if not tem_abono:
        observacao.delete()
        return httprr(request.META.get('HTTP_REFERER', '..'), 'Observação excluída com sucesso.')
    else:
        return httprr(
            request.META.get('HTTP_REFERER', '..'), 'Não foi possível excluir a observação. Existe uma ação da chefia imediata com relação à frequência inconsistente.', tag='failure'
        )


@rtr()
@login_required
def adicionar_abono_inconsistencia_frequencia(request, servidor_matricula, data_falta):
    servidor_faltoso = get_object_or_404(Servidor, matricula=servidor_matricula)
    servidor = request.user.get_relacionamento()
    data_inconsistencia = datetime.strptime(data_falta, "%d%m%Y").date()
    setor = servidor_faltoso.setor_suap_servidor_no_dia(data_inconsistencia)
    setor_chefe = servidor.setor

    if not setor:
        raise PermissionDenied('Servidor não está associado a nenhum setor.')

    # - verifica se foi/é chefe no setor e no período indicado
    is_chefe_de_setor = servidor.eh_chefe_do_setor_periodo(setor, data_inconsistencia, data_inconsistencia)
    if not is_chefe_de_setor:
        raise PermissionDenied('Tela acessada apenas por FGs ou CDs.')
    if servidor_faltoso == servidor:
        raise PermissionDenied('Servidor não pode abonar suas próprias inconsistências.')

    if servidor_faltoso.eh_liberado_controle_frequencia():
        raise PermissionDenied('São dispensados do controle de frequência os ocupantes de cargos de Direção - CD, hierarquicamente iguais ou superiores a DAS 4 ou CD - 3')

    contexto_compensacao = Contexto(servidor=servidor_faltoso.get_vinculo().relacionamento, periodo_data_inicial=data_inconsistencia, periodo_data_final=data_inconsistencia)

    frequencias_servidor = Frequencia.get_frequencias_por_data(servidor_faltoso.get_vinculo(), data_inconsistencia)

    inconsistencia = Frequencia.get_inconsistencias(
        servidor_faltoso.get_vinculo(), data_inconsistencia, contexto_compensacao=contexto_compensacao, frequencias=frequencias_servidor
    )

    tem_saida_antecipada = Frequencia.tem_saida_antecipada(
        servidor_faltoso.get_vinculo(), data_inconsistencia, contexto_compensacao=contexto_compensacao, frequencias=frequencias_servidor
    )

    if not inconsistencia and not tem_saida_antecipada:
        raise PermissionDenied('Servidor não tem inconsistências para a data passada.')

    title = "Abonar Inconsistência do Servidor {} do dia {}".format(servidor_faltoso, format_(data_inconsistencia))

    observacoes = Observacao.objects.filter(vinculo=servidor_faltoso.get_vinculo(), data=data_inconsistencia)

    jornada_trabalho = servidor_faltoso.get_jornadas_periodo_dict(data_inconsistencia, data_inconsistencia).get(data_inconsistencia).get_jornada_trabalho_diaria()

    if inconsistencia:
        tipo_inconsistencia = inconsistencia[0]
    else:
        tipo_inconsistencia = ''

    informacao_registro = Frequencia.DESCRICAO_INCONSISTENCIA[tipo_inconsistencia]

    try:
        abono = AbonoChefia.objects.get(vinculo_pessoa=servidor_faltoso.get_vinculo(), data=data_inconsistencia)
    except AbonoChefia.DoesNotExist:
        abono = AbonoChefia(vinculo_pessoa=servidor_faltoso.get_vinculo(), data=data_inconsistencia)

    FormClass = AbonoChefiaFormFactory(tipo_inconsistencia)
    form = FormClass(request.POST or None, instance=abono)
    if form.is_valid():
        abono.vinculo_chefe_imediato = servidor.get_vinculo()
        form.save()
        ancora = servidor_faltoso.matricula + data_inconsistencia.strftime('%d/%m/%Y') or ''
        return httprr('..', 'Abono de inconsistência salvo com sucesso.', anchor=ancora, close_popup=True)

    return locals()


####################################
# Funções para o terminal de ponto #
####################################


@transaction.atomic
def get_dump_terminal_ponto(request):
    """
    Retorna ``dump_terminal.zip``, que é um dump que corresponde à tabela
    ``pessoa`` dos terminais de ponto eletrônico.
    """
    try:
        m = Maquina.objects.get(ip=get_client_ip(request), cliente_ponto=True, ativo=True)
    except Maquina.DoesNotExist:
        raise PermissionDenied('Máquina sem permissões')

    ARQUIVO_DUMP = '/tmp/tabela_terminal.zip'
    if exists(ARQUIVO_DUMP) and datetime.fromtimestamp(stat(ARQUIVO_DUMP)[-1]).date() == date.today():
        # Se existe um arquivo gerado no dia, este não precisa ser criado
        pass

    else:
        # Não existe arquivo gerado no dia, então precisa ser criado
        cursor = connection.cursor()

        qs = (
            Funcionario.objects.annotate(setor_sigla=Coalesce('setor__sigla', Value('     ')))
            .filter(excluido=False, username__isnull=False)
            .exclude(username='')
            .values('username', 'nome', 'template', 'tem_digital_fraca', 'setor_sigla')
        )
        query = get_real_sql(qs, remove_order_by=True)

        query = 'CREATE TEMP TABLE tabela_terminal_ponto AS ' + query
        cursor.execute(query)
        # Gerando o dump
        dump_file = open('/tmp/tabela_terminal.copy', 'w')
        cursor.copy_to(dump_file, 'tabela_terminal_ponto')
        dump_file.close()

        # Removendo tabela temporária
        cursor.execute('DROP TABLE tabela_terminal_ponto')

        # Compactando o dump
        zip_file = zipfile.ZipFile(ARQUIVO_DUMP, 'w', zipfile.ZIP_DEFLATED)
        zip_file.write('/tmp/tabela_terminal.copy', 'tabela_terminal.copy')
        zip_file.close()

    # Abrindo o arquivo zipado
    dump_zip_file = open(ARQUIVO_DUMP)
    conteudo_dump = dump_zip_file.read()
    dump_zip_file.close()

    MaquinaLog.objects.create(maquina=m, operacao='ponto_get_dump_terminal_ponto')

    response = HttpResponse(conteudo_dump, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=dump_terminal.zip'
    return response


@transaction.atomic
def get_fotos_terminal_ponto(request):
    """
    Retorna ``fotos.zip``, que é um dump que vai servir para definir as fotos
    das pessoas nos terminais de ponto eletrônico.
    """
    try:
        m = Maquina.objects.get(ip=get_client_ip(request), cliente_ponto=True, ativo=True)
    except Maquina.DoesNotExist:
        raise PermissionDenied('Máquina sem permissões')

    ARQUIVO_DUMP = '/tmp/fotos.zip'

    if exists(ARQUIVO_DUMP) and datetime.fromtimestamp(stat(ARQUIVO_DUMP)[-1]).date() == date.today():
        # Se existe um arquivo gerado no dia, este não precisa ser criado
        pass

    else:
        zip_file = zipfile.ZipFile(ARQUIVO_DUMP, 'w', zipfile.ZIP_DEFLATED)
        for s in Servidor.objects.ativos().exclude(foto__isnull=True, foto=''):
            if not s.foto:
                continue
            # foto_path_sem_extensao = '.'.join(s.foto.path.split('.')[:-1])
            # miniatura_path = foto_path_sem_extensao + '.150x150.jpg'
            remote_filename = s.foto.name.replace('fotos/', 'fotos/150x200/')
            local_filename = cache_file(remote_filename)
            if not os.path.exists(local_filename):
                continue
            zip_file.write(local_filename, '%s.jpg' % s.matricula)
            os.unlink(local_filename)
        for s in PrestadorServico.objects.filter(excluido=False).exclude(foto__isnull=True, foto=''):
            if not s.foto:
                continue
            # foto_path_sem_extensao = '.'.join(s.foto.path.split('.')[:-1])
            # miniatura_path = foto_path_sem_extensao + '.150x150.jpg'
            remote_filename = s.foto.name.replace('fotos/', 'fotos/150x200/')
            local_filename = cache_file(remote_filename)
            if not os.path.exists(local_filename):
                continue
            zip_file.write(local_filename, '%s.jpg' % s.matricula)
            os.unlink(local_filename)
        zip_file.close()

    dump_zip_file = open(ARQUIVO_DUMP, 'rb')
    conteudo_dump = dump_zip_file.read()
    dump_zip_file.close()

    MaquinaLog.objects.create(maquina=m, operacao='ponto_get_fotos_terminal_ponto')

    response = HttpResponse(conteudo_dump, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=fotos.zip'
    return response


##########################################################################################
# COMPENSAÇÃO DE HORÁRIO
##########################################################################################


@rtr()
@permission_required('ponto.change_horariocompensacao')
def abrir_compensacao_horario(request, compensacao_horario_id):
    title = 'Informe de Compensação de Horário'
    #
    compensacao = get_object_or_404(HorarioCompensacao, pk=compensacao_horario_id)
    #
    usuario_logado = request.user.get_relacionamento()
    usuario_logado_is_informante = usuario_logado == compensacao.funcionario
    usuario_logado_is_chefe = compensacao.chefe == usuario_logado
    #
    if not (usuario_logado_is_informante or usuario_logado_is_chefe):
        raise PermissionDenied
    #
    return locals()


@rtr()
@permission_required('ponto.change_horariocompensacao')
def editar_obs_compensacao_horario(request, compensacao_horario_id):
    compensacao = get_object_or_404(HorarioCompensacao, pk=compensacao_horario_id)
    title = 'Editar Observações de {}'.format(compensacao)
    usuario_logado = request.user.get_relacionamento()
    usuario_logado_is_informante = usuario_logado == compensacao.funcionario
    if not usuario_logado_is_informante or compensacao.situacao == HorarioCompensacao.SITUACAO_INVALIDO:
        raise PermissionDenied
    #
    form = HorarioCompensacaoEditarObservacoesPontoForm(request.POST or None, instance=compensacao)
    #
    if form.is_valid() and form.save():
        return httprr('/ponto/abrir_compensacao_horario/{}/'.format(compensacao_horario_id), 'Observações editadas com sucesso.')
    return locals()


@rtr()
@permission_required('ponto.add_recessoopcao')
def abrir_opcao_recesso(request, recesso_opcao_id):
    title = 'Opção de Compensação'
    recesso_opcao = get_object_or_404(RecessoOpcao, pk=recesso_opcao_id)
    recesso_opcao_periodo_escolhas_aberto_e_expirado = recesso_opcao.is_aberto_para_escolhas_de_datas and not recesso_opcao.is_no_periodo_para_escolhas_de_datas
    recesso_opcao_com_pendencias_de_validacao_remarcacao = (
        recesso_opcao_periodo_escolhas_aberto_e_expirado
        and recesso_opcao.recessoopcaoescolhida_set.filter(
            validacao__in=[RecessoOpcaoEscolhida.VALIDACAO_AGUARDANDO, RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO_REMARCAR]
        ).exists()
    )
    return locals()


@rtr()
@permission_required('ponto.add_recessoopcao')
def excluir_opcao_recesso(request, recesso_opcao_id):
    recesso_opcao = get_object_or_404(RecessoOpcao, pk=recesso_opcao_id)
    #
    if RecessoDiaEscolhido.objects.filter(
        recesso_opcao_escolhida__recesso_opcao=recesso_opcao,
        recesso_opcao_escolhida__validacao__in=[
            RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO,
            RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO,
            RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO_REMARCAR,
        ],
    ).exists():
        return httprr(
            '/ponto/abrir_opcao_recesso/{}/'.format(recesso_opcao.id),
            'Exclusão não permitida. Há dias escolhidos por um ou mais servidores, ' 'com validação dos chefes imediatos.',
            tag='error',
        )
    #
    # admin, vai que é tua!!!
    return httprr('/admin/ponto/recessoopcao/{}/delete/'.format(recesso_opcao.id))


@rtr('adicionar_dia_de_recesso_ou_periodo_de_compensacao.html')
@permission_required('ponto.add_recessoopcao')
def adicionar_dia_de_recesso(request, recesso_opcao_id):
    title = 'Adicionar Dias a Compensar'
    recesso_opcao = get_object_or_404(RecessoOpcao, pk=recesso_opcao_id)

    data_unica = request.POST.get('numero_de_datas') == '1' or request.GET.get('numero_de_datas') == '1'
    data_periodo = request.POST.get('numero_de_datas') == '2' or request.GET.get('numero_de_datas') == '2'
    if not data_unica and not data_periodo:
        data_periodo = True

    form = RecessoDiaAddForm(request.POST or None, recesso_opcao=recesso_opcao, is_data_unica=data_unica)
    form.SUBMIT_LABEL = 'Salvar e Continuar'
    form.EXTRA_BUTTONS = [{'type': 'button', 'value': 'Salvar e Concluir', 'onclick': 'salvar_e_concluir();'}]  # função javascript definida no template

    salvar_e_concluir = request.POST.get('salvar_e_concluir') == '1'

    if form.is_valid() and form.save():
        if salvar_e_concluir:
            return httprr('..')
        else:
            return httprr(
                '.',
                'Salvo com sucesso. Já adicionados: {}'.format(', '.join([str(dia_recesso) for dia_recesso in recesso_opcao.dias_do_recesso.all()])),
                get_params='numero_de_datas={}'.format('1' if data_unica else '2'),
            )
    return locals()


@rtr()
@permission_required('ponto.add_recessoopcao')
def excluir_data_de_recesso(request, recesso_data_id):
    recesso_dia = get_object_or_404(RecessoDia, pk=recesso_data_id)
    dia_excluido = str(recesso_dia)
    recesso_opcao_id = recesso_dia.recesso_opcao.id
    #
    if RecessoDiaEscolhido.objects.filter(
        dia=recesso_dia,
        recesso_opcao_escolhida__validacao__in=[
            RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO,
            RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO,
            RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO_REMARCAR,
        ],
    ).exists():
        return httprr(
            '/ponto/abrir_opcao_recesso/{}/'.format(recesso_opcao_id),
            'Exclusão não permitida. O dia {} foi escolhido por um ou mais servidores, com validação dos chefes imediatos.'.format(dia_excluido),
            tag='error',
        )
    #
    recesso_dia.delete()
    return httprr('/ponto/abrir_opcao_recesso/{}/'.format(recesso_opcao_id), 'Dia {} removido com sucesso.'.format(dia_excluido))


@rtr('adicionar_dia_de_recesso_ou_periodo_de_compensacao.html')
@permission_required('ponto.add_recessoopcao')
def adicionar_periodo_de_compensacao(request, recesso_opcao_id):
    title = 'Adicionar Períodos de Compensação'
    recesso_opcao = get_object_or_404(RecessoOpcao, pk=recesso_opcao_id)

    data_unica = request.POST.get('numero_de_datas') == '1' or request.GET.get('numero_de_datas') == '1'
    data_periodo = request.POST.get('numero_de_datas') == '2' or request.GET.get('numero_de_datas') == '2'
    if not data_unica and not data_periodo:
        data_periodo = True

    form = RecessoPeriodoCompensacaoAddForm(request.POST or None, recesso_opcao=recesso_opcao, is_data_unica=data_unica)
    form.SUBMIT_LABEL = 'Salvar e Continuar'
    form.EXTRA_BUTTONS = [{'type': 'button', 'value': 'Salvar e Concluir', 'onclick': 'salvar_e_concluir();'}]  # função javascript definida no template

    salvar_e_concluir = request.POST.get('salvar_e_concluir') == '1'

    if form.is_valid() and form.save():
        if salvar_e_concluir:
            return httprr('..')
        else:
            return httprr(
                '.',
                'Salvo com sucesso. Já adicionados: {}'.format(', '.join([str(periodo) for periodo in recesso_opcao.periodos_de_compensacao.all()])),
                get_params='numero_de_datas={}'.format('1' if data_unica else '2'),
            )
    return locals()


@rtr()
@permission_required('ponto.add_recessoopcao')
def excluir_periodo_de_compensacao(request, periodo_de_compensacao_id):
    periodo_de_compensacao = get_object_or_404(RecessoPeriodoCompensacao, pk=periodo_de_compensacao_id)
    periodo_excluido = str(periodo_de_compensacao)
    recesso_opcao_id = periodo_de_compensacao.recesso_opcao.id
    periodo_de_compensacao.delete()
    return httprr('/ponto/abrir_opcao_recesso/{}/'.format(recesso_opcao_id), 'Período de Compensação {} removido com sucesso.'.format(periodo_excluido))


@rtr()
@permission_required('ponto.add_recessoopcao')
def definir_periodo_escolha_recesso(request, recesso_opcao_id):
    title = 'Definir o Período de Escolha dos Dias a Compensar'
    recesso_opcao = get_object_or_404(RecessoOpcao, pk=recesso_opcao_id)
    form = RecessoPeriodoEscolhaForm(request.POST or None, instance=recesso_opcao)
    if form.is_valid() and form.save():
        if form.instance.is_definido_periodo_de_escolha:
            return httprr('..', 'Período de Escolha definido com sucesso.')
        return httprr('..')
    return locals()


@rtr()
@permission_required('ponto.add_recessoopcao')
def liberar_escolha_recesso(request, recesso_opcao_id):
    recesso_opcao = get_object_or_404(RecessoOpcao, pk=recesso_opcao_id)
    try:
        recesso_opcao.liberar_para_escolha_dos_dias_do_recesso()
        return httprr('/ponto/abrir_opcao_recesso/{}/'.format(recesso_opcao_id), 'Período de Escolha dos Dias a Compensar liberado com sucesso.')
    except Exception as Erro:
        return httprr('/ponto/abrir_opcao_recesso/{}/'.format(recesso_opcao_id), str(Erro), tag='error')


@rtr()
@permission_required('ponto.add_recessoopcao')
def retornar_a_fase_de_cadastro(request, recesso_opcao_id):
    recesso_opcao = get_object_or_404(RecessoOpcao, pk=recesso_opcao_id)
    recesso_opcao.retornar_a_fase_de_cadastro()
    return httprr('/ponto/abrir_opcao_recesso/{}/'.format(recesso_opcao_id), 'Opção de Compensação Em Fase de Cadastro novamente.')


@rtr()
@permission_required('ponto.add_recessoopcao')
def fechar_cadastro_e_escolha(request, recesso_opcao_id):
    recesso_opcao = get_object_or_404(RecessoOpcao, pk=recesso_opcao_id)
    try:
        recesso_opcao.fechar_cadastro_e_escolha()
        return httprr('/ponto/abrir_opcao_recesso/{}/'.format(recesso_opcao_id), 'Cadastramento concluído.')
    except Exception as erro:
        return httprr('/ponto/abrir_opcao_recesso/{}/'.format(recesso_opcao_id), str(erro), tag='error')


@rtr()
@permission_required('ponto.add_recessoopcaoescolhida')
def escolher_dia_de_recesso(request):
    title = 'Escolher Dias'
    try:
        form = get_type_form_dias_escolhidos(request)(request.POST or None)
        if form.is_valid():
            form.save()
            return httprr('/admin/ponto/recessoopcaoescolhida/?tab=meus_recessos', 'Dias salvos com sucesso.')
    except Exception as erro:
        return httprr('/admin/ponto/recessoopcaoescolhida/?tab=meus_recessos', str(erro), tag='error')
    return locals()


@rtr()
@permission_required('ponto.add_recessoopcaoescolhida')
def abrir_recesso_escolhido(request, recesso_opcao_escolhida_id):
    title = 'Acompanhamento de Compensação'

    recesso_opcao_escolhida = get_object_or_404(RecessoOpcaoEscolhida, pk=recesso_opcao_escolhida_id)

    relacionamento = request.user.get_relacionamento()
    usuario_logado_is_solicitante = relacionamento.pk == recesso_opcao_escolhida.funcionario.pk
    usuario_logado_is_chefe = recesso_opcao_escolhida.is_chefe(relacionamento)

    if not (usuario_logado_is_solicitante or usuario_logado_is_chefe):
        raise PermissionDenied

    periodos_compensacao = [periodo for periodo in recesso_opcao_escolhida.recesso_opcao.periodos_de_compensacao.all()]
    periodo_compensacao_inicio = min(periodo.data_inicial for periodo in periodos_compensacao)
    periodo_compensacao_fim = max(periodo.data_final for periodo in periodos_compensacao)

    usuario_logado_pode_validar = (
        recesso_opcao_escolhida.is_aguardando
        and usuario_logado_is_chefe
        and (recesso_opcao_escolhida.recesso_opcao.is_no_periodo_para_escolhas_de_datas or recesso_opcao_escolhida.pode_validar_apos_prazo)
    )

    usuario_logado_pode_excluir = recesso_opcao_escolhida.pode_excluir(relacionamento)

    usuario_logado_pode_cancelar_validacao = (
        usuario_logado_is_chefe
        and not recesso_opcao_escolhida.is_aguardando
        and (recesso_opcao_escolhida.recesso_opcao.is_no_periodo_para_escolhas_de_datas or recesso_opcao_escolhida.pode_validar_apos_prazo)
    )

    usuario_logado_pode_editar_dias_escolhidos = (
        usuario_logado_is_solicitante
        and recesso_opcao_escolhida.validacao
        in [recesso_opcao_escolhida.VALIDACAO_AGUARDANDO, recesso_opcao_escolhida.VALIDACAO_AUTORIZADO, recesso_opcao_escolhida.VALIDACAO_NAO_AUTORIZADO_REMARCAR]
        and recesso_opcao_escolhida.recesso_opcao.is_no_periodo_para_escolhas_de_datas
        and not recesso_opcao_escolhida.compensacoes().exists()
    )

    ch_totais = recesso_opcao_escolhida.totais_ch(carga_horaria_total=True, carga_horaria_debito_considerado=True, carga_horaria_compensada=True, carga_horaria_pendente=True)

    ch_total = ch_totais['total_carga_horaria_total']
    ch_total_is_zero = ch_total == 0
    ch_total = formata_segundos(ch_total, '{h:2d}h ', '{m:2d}min ', '{s:2d}seg ', True)

    ch_debito_considerado = ch_totais['total_carga_horaria_debito_considerado']
    ch_debito_considerado_is_zero = ch_debito_considerado == 0
    ch_debito_considerado = formata_segundos(ch_debito_considerado, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)

    ch_compensada = ch_totais['total_carga_horaria_compensada']
    ch_compensada_is_zero = ch_compensada == 0
    ch_compensada = formata_segundos(ch_compensada, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)

    ch_pendente = ch_totais['total_carga_horaria_pendente']
    ch_pendente_is_maior_zero = ch_pendente > 0
    ch_pendente_is_negativa = ch_pendente < 0  # possível problema de duplicidade em informes de compensação
    ch_pendente = formata_segundos(ch_pendente, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)

    dias_definidos = [dia_definido.data for dia_definido in recesso_opcao_escolhida.recesso_opcao.dias_do_recesso.all()]
    dias_definidos_format = [dia_definido.strftime('%d/%m/%Y') for dia_definido in dias_definidos]
    dias_definidos_format_dmy = [dia_definido.strftime('%d%m%Y') for dia_definido in dias_definidos]

    dias_efetivos_a_compensar = ch_totais['dias_a_compensar']
    dias_efetivos_a_compensar_format = [dia_efetivo.strftime('%d/%m/%Y') for dia_efetivo in dias_efetivos_a_compensar]
    dias_efetivos_a_compensar_format_dmy = [dia_efetivo.strftime('%d%m%Y') for dia_efetivo in dias_efetivos_a_compensar]
    dias_efetivos_a_compensar_situacoes = (
        [dia_situacao for dia_situacao in list(ch_totais['contexto_compensacao'].dias_debitos.values()) if dia_situacao.dia in dias_efetivos_a_compensar]
        if ch_totais['contexto_compensacao']
        else []
    )

    meu_acompanhamento_descricao = 'Resumo do {} Acompanhamento'.format('Meu' if usuario_logado_is_solicitante else '')

    return locals()


@permission_required('ponto.add_recessoopcaoescolhida')
def excluir_recesso_escolhido(request, recesso_opcao_escolhida_id):
    recesso_opcao_escolhida = get_object_or_404(RecessoOpcaoEscolhida, pk=recesso_opcao_escolhida_id)
    #
    usuario_logado = request.user.get_relacionamento()
    pode_excluir = recesso_opcao_escolhida.pode_excluir(usuario_logado)
    #
    if not pode_excluir:
        raise PermissionDenied
    #
    recesso_opcao_escolhida.delete()
    #
    return httprr('/admin/ponto/recessoopcaoescolhida/', 'Informações excluídas com sucesso.')


@rtr()
@permission_required('ponto.add_recessoopcaoescolhida')
def editar_dias_de_recesso_escolhidos(request, recesso_opcao_escolhida_id):
    title = 'Editar Dias'
    recesso_opcao_escolhida = get_object_or_404(RecessoOpcaoEscolhida, pk=recesso_opcao_escolhida_id)
    try:
        form = get_type_form_dias_escolhidos(request, recesso_opcao_escolhida.recesso_opcao)(request.POST or None)
        if form.is_valid():
            form.save()
            return httprr('/ponto/abrir_recesso_escolhido/{}/'.format(recesso_opcao_escolhida_id), 'Dias salvos com sucesso.')
    except Exception as erro:
        return httprr('/ponto/abrir_recesso_escolhido/{}/'.format(recesso_opcao_escolhida_id), str(erro), tag='error')
    return locals()


@rtr()
@permission_required('ponto.add_recessoopcaoescolhida')
def validar_recesso_escolhido(request, recesso_opcao_escolhida_id):
    title = 'Validação do Chefe Imediato'
    recesso_opcao_escolhida = get_object_or_404(RecessoOpcaoEscolhida, pk=recesso_opcao_escolhida_id)
    #
    usuario_logado = request.user.get_relacionamento()
    usuario_logado_is_chefe = recesso_opcao_escolhida.is_chefe(usuario_logado)
    #
    pode_validar = (
        recesso_opcao_escolhida.is_aguardando
        and usuario_logado_is_chefe
        and (recesso_opcao_escolhida.recesso_opcao.is_no_periodo_para_escolhas_de_datas or recesso_opcao_escolhida.pode_validar_apos_prazo)
    )

    if not pode_validar:
        raise PermissionDenied
    #
    form = RecessoOpcaoEscolhidaValidarForm(data=request.POST or None, instance=recesso_opcao_escolhida, request=request)
    #
    if form.is_valid():
        form.save()
        return httprr('..', 'Validação salva com sucesso.')
    #
    return locals()


@login_required
def cancelar_validacao_recesso_escolhido(request, recesso_opcao_escolhida_id):
    recesso_opcao_escolhida = get_object_or_404(RecessoOpcaoEscolhida, pk=recesso_opcao_escolhida_id)

    usuario_logado = request.user.get_relacionamento()
    usuario_logado_is_chefe = recesso_opcao_escolhida.is_chefe(usuario_logado)
    recesso_opcao_escolhida_estah_validada = not recesso_opcao_escolhida.is_aguardando

    recesso_opcao_estah_aberta_para_escolhas_hoje = recesso_opcao_escolhida.recesso_opcao.is_no_periodo_para_escolhas_de_datas

    pode_cancelar = (
        usuario_logado_is_chefe and recesso_opcao_escolhida_estah_validada and (recesso_opcao_estah_aberta_para_escolhas_hoje or recesso_opcao_escolhida.pode_validar_apos_prazo)
    )

    if not pode_cancelar:
        raise PermissionDenied

    #
    try:
        recesso_opcao_escolhida.validacao = RecessoOpcaoEscolhida.VALIDACAO_AGUARDANDO
        recesso_opcao_escolhida.motivo_nao_autorizacao = ''
        recesso_opcao_escolhida.save()
        #
        return httprr('/ponto/abrir_recesso_escolhido/{}/'.format(recesso_opcao_escolhida.id), 'Validação cancelada com sucesso.')
    except Exception:
        pass
    return httprr('/ponto/abrir_recesso_escolhido/{}/'.format(recesso_opcao_escolhida.id), 'Validação não foi cancelada.', tag='error')


@rtr()
@permission_required('ponto.add_horariocompensacao')
def informar_compensacao(request, periodo_inicio, periodo_fim):
    title = 'Informar Compensação de Horário'
    periodo_data_inicial = datetime.strptime(periodo_inicio, '%d%m%Y').date()
    periodo_data_final = datetime.strptime(periodo_fim, '%d%m%Y').date()

    apenas_debitos_do_periodo_consultado = request.GET.get('apenas_debitos_do_periodo_consultado', False) == '1'

    omite_debitos_de_acompanhamentos_especificos = request.GET.get('omite_debitos_de_acompanhamentos_especificos', False) == '1'

    url_omite_debitos_de_acompanhamentos_especificos = f'{request.get_full_path()}'
    if not omite_debitos_de_acompanhamentos_especificos:
        if '?' not in url_omite_debitos_de_acompanhamentos_especificos:
            url_omite_debitos_de_acompanhamentos_especificos += '?'
        else:
            url_omite_debitos_de_acompanhamentos_especificos += '&'
        url_omite_debitos_de_acompanhamentos_especificos += 'omite_debitos_de_acompanhamentos_especificos=1'

    form = get_type_form_multiplas_compensacao_horario(
        request,
        periodo_data_inicial,
        periodo_data_final,
        apenas_debitos_do_periodo_consultado=apenas_debitos_do_periodo_consultado,
        omite_debitos_de_acompanhamentos_especificos=omite_debitos_de_acompanhamentos_especificos,
    )(request.POST or None)

    if form.is_valid():
        compensacoes = form.save()
        datas_debitos = ','.join({compensacao.data_aplicacao.strftime('%d%m%Y') for compensacao in compensacoes})
        return httprr(
            '/ponto/ver_frequencia/{}/?datas={}'.format(request.user.get_relacionamento().matricula, datas_debitos), 'Informes de Compensação de Horário salvos com sucesso.'
        )
    return locals()


@rtr("informar_compensacao.html")
@permission_required('ponto.add_horariocompensacao')
def informar_compensacao_recesso(request, periodo_inicio, periodo_fim):
    title = 'Informar Compensação de Horário'

    periodo_data_inicial = datetime.strptime(periodo_inicio, '%d%m%Y').date()
    periodo_data_final = datetime.strptime(periodo_fim, '%d%m%Y').date()

    apenas_debitos_de_recessos = True
    apenas_esses_recessos_escolhidos = []
    if request.GET and request.GET.get('recesso_escolhido', None):
        try:
            recesso_opcao_escolhida = get_object_or_404(RecessoOpcaoEscolhida, pk=request.GET.get('recesso_escolhido'))
            apenas_esses_recessos_escolhidos = [recesso_opcao_escolhida]
        except Exception:
            pass

    form = get_type_form_multiplas_compensacao_horario(
        request, periodo_data_inicial, periodo_data_final, apenas_recessos=True, apenas_os_recessos_escolhidos=apenas_esses_recessos_escolhidos
    )(request.POST or None)

    if form.is_valid():
        compensacoes = form.save()
        datas_debitos = ','.join({compensacao.data_aplicacao.strftime('%d%m%Y') for compensacao in compensacoes})
        return httprr(
            '/ponto/ver_frequencia/{}/?datas={}'.format(request.user.get_relacionamento().matricula, datas_debitos), 'Informes de Compensação de Horário salvos com sucesso.'
        )
    return locals()


@rtr()
@permission_required('ponto.add_horariocompensacao')
def adicionar_compensacao(request):
    title = 'Informar Compensação de Horário - Período dos Saldos'

    hoje = datetime.today()

    try:
        data_inicio_initial = datetime.strptime(request.GET.get('data_inicio'), '%d%m%Y').date()
    except Exception:
        data_inicio_initial = date(hoje.year, hoje.month, 1)

    try:
        data_fim_initial = datetime.strptime(request.GET.get('data_fim'), '%d%m%Y').date()
    except Exception:
        data_fim_initial = hoje

    form = HorarioCompensacaoPeriodoForm(request.POST or None, initial={'data_inicio': data_inicio_initial, 'data_fim': data_fim_initial})
    if '_popup' in request.GET:
        popup = '?_popup=1'
    else:
        popup = ''

    if form.is_valid():
        return httprr('/ponto/informar_compensacao/{}/{}/{}'.format(form.cleaned_data['data_inicio'].strftime('%d%m%Y'), form.cleaned_data['data_fim'].strftime('%d%m%Y'), popup))

    return locals()


@rtr()
@permission_required('ponto.add_horariocompensacao')
def detalhar_compensacao(request, matricula, data):
    title = 'Detalhes da Compensação de Horário'

    servidor = get_object_or_404(Servidor, matricula=matricula)
    data = datetime.strptime(data, '%d%m%Y').date()

    contexto_compensacao = Contexto(servidor, data, data)

    compensacoes = contexto_compensacao.get_compensacoes_informadas

    debitos = contexto_compensacao.dias_debitos
    is_debito = data in debitos
    debito = timedelta(seconds=debitos[data].debito_qtd_considerado if is_debito else 0)
    debito_acompanhamentos_especificos = debitos[data].acompanhamentos_envolvidos_contendo_o_dia_como_debito if is_debito else []
    debito_view = formata_segundos(debito.seconds, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)

    saldos = contexto_compensacao.dias_saldos
    is_saldo = data in saldos
    saldo = timedelta(seconds=saldos[data].saldo_qtd_considerado if is_saldo else 0)
    saldo_view = formata_segundos(saldo.seconds, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)

    compensacoes_paga = []
    compensacoes_utilizada = []
    total_paga = timedelta(seconds=0)
    total_utilizada = timedelta(seconds=0)

    for compensacao in compensacoes:
        if data == compensacao.data_compensacao:
            compensacoes_utilizada.append(compensacao)
            total_utilizada += timedelta(seconds=Frequencia.time_para_segundos(compensacao.ch_compensada))
        if data == compensacao.data_aplicacao:
            compensacoes_paga.append(compensacao)
            total_paga += timedelta(seconds=Frequencia.time_para_segundos(compensacao.ch_compensada))

    total_paga_view = formata_segundos(total_paga.seconds, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)
    total_utilizada_view = formata_segundos(total_utilizada.seconds, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)

    debito_restante = debito - total_paga if total_paga <= debito else timedelta(0)
    debito_restante_view = formata_segundos(debito_restante.seconds, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)

    saldo_restante = saldo - total_utilizada if total_utilizada <= saldo else timedelta(0)
    saldo_restante_view = formata_segundos(saldo_restante.seconds, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)

    dia_anterior = data - timedelta(1)
    dia_seguinte = data + timedelta(1)

    return locals()


@rtr()
@permission_required('ponto.add_horariocompensacao')
def ver_frequencia(request, matricula):
    """
        suporte para múltiplas datas
        mostra apenas as frequências
        /ver_frequencia/matricula/?datas=dmY,dmY,dmY,dmY ou datas=yyyy-mm-dd,yyyy-mm-dd,yyyy-mm-dd,
    """

    title = 'Consulta Simples de Frequências'
    servidor = get_object_or_404(Servidor, matricula=matricula)
    datas_str = request.GET and request.GET.get('datas', '').split(',')
    datas = []
    for data_str in datas_str:
        if data_str:
            try:
                datas.append(datetime.strptime(data_str, '%d%m%Y').date())
            except Exception:
                try:
                    datas.append(datetime.strptime(data_str, '%Y-%m-%d').date())
                except Exception:
                    return httprr('..', 'Data inválida.', 'error')

    try:
        relatorio = Frequencia.relatorio_ponto_pessoa(vinculo=servidor.get_vinculo(), data_ini=min(datas), data_fim=max(datas), show_grafico=False, trata_compensacoes=True)
        frequencias_dias = []
        for frequencia_dia in relatorio['dias']:
            if frequencia_dia['dia'] in datas:
                frequencias_dias.append(frequencia_dia)

        relatorio['dias'] = frequencias_dias

        if is_request_xls(request):
            try:
                xls = get_response_xls_registros_frequencias([relatorio], filename=title)

                if xls:
                    return xls
            except Exception:
                pass

    except Exception:
        relatorio = []

    return locals()


@rtr()
@permission_required('ponto.add_horariocompensacao')
def remover_compensacoes(request, matricula):
    """
        suporta remoção de múltiplos informes de compensação
    """

    servidor = get_object_or_404(Servidor, matricula=matricula)

    if not request.user.get_relacionamento().matricula == matricula:
        raise PermissionDenied

    compensacoes_por_data_debito = request.GET.get('localizar_opcao') == '1'
    compensacoes_por_data_saldo = request.GET.get('localizar_opcao') == '2'
    compensacoes_em_duplicidade = request.GET.get('localizar_opcao') == '3'

    confirmando_remocao = request.POST.get('remover') == 'sim'
    senha_remocao_confere = False

    data_inicio = None
    data_fim = None

    compensacoes = HorarioCompensacao.objects.none()

    if compensacoes_por_data_debito or compensacoes_por_data_saldo:
        title = 'Remover Compensações - Localizar por Data'

        if compensacoes_por_data_debito:
            title = '{} do Débito'.format(title)
        else:
            title = '{} da Compensação/Saldo'.format(title)

        if confirmando_remocao:
            data_inicio = datetime.strptime(request.POST.get('data_inicio'), '%d%m%Y')
            data_fim = datetime.strptime(request.POST.get('data_fim'), '%d%m%Y')

            form = HorarioCompensacaoPeriodoForm(dict(data_inicio=data_inicio, data_fim=data_fim))
        else:
            form = HorarioCompensacaoPeriodoForm(request.POST or None)

            if form.is_valid():
                data_inicio = form.cleaned_data['data_inicio']
                data_fim = form.cleaned_data['data_fim']

        if data_inicio and data_fim:
            compensacoes = HorarioCompensacao.objects.filter(funcionario=servidor)

            if compensacoes_por_data_debito:
                compensacoes = compensacoes.filter(data_aplicacao__gte=data_inicio, data_aplicacao__lte=data_fim)
            else:
                compensacoes = compensacoes.filter(data_compensacao__gte=data_inicio, data_compensacao__lte=data_fim)

    elif compensacoes_em_duplicidade:
        title = 'Remover Compensações em Duplicidade'

        # compensações em duplicidade:
        # mesma data do débito
        # mesma data da compensação
        # mesma carga horária compensada

        compensacoes_ids = []

        compensacoes_todas = []
        for compensacao in HorarioCompensacao.objects.filter(funcionario=servidor):
            compensacoes_todas.append(
                '{},{}{}{}'.format(
                    compensacao.id,
                    compensacao.data_aplicacao.strftime('%d/%m/%Y'),
                    compensacao.data_compensacao.strftime('%d/%m/%Y'),
                    compensacao.ch_compensada.strftime('%H:%M:%S'),
                )
            )

        while compensacoes_todas:
            compensacao_teste = compensacoes_todas[0]

            compensacoes_duplicadas_ids = []
            for compensacao in compensacoes_todas[1:]:
                if compensacao.split(',')[1] == compensacao_teste.split(',')[1]:  # compara os ids das compensações
                    compensacoes_duplicadas_ids.append(compensacao.split(',')[0])

            compensacoes_processadas_ids = [compensacao_teste.split(',')[0]] + compensacoes_duplicadas_ids

            compensacoes_todas_tmp = []
            for compensacao in compensacoes_todas:
                if compensacao.split(',')[0] not in compensacoes_processadas_ids:
                    compensacoes_todas_tmp.append(compensacao)
            compensacoes_todas = compensacoes_todas_tmp

            compensacoes_ids += compensacoes_duplicadas_ids

        compensacoes = compensacoes | HorarioCompensacao.objects.filter(id__in=compensacoes_ids)
    else:
        return httprr('/admin/ponto/horariocompensacao/', tag='error', message='Remover Compensações: Opção Inválida.')

    compensacoes_selecionadas_ids = []

    if confirmando_remocao:
        senha = request.POST.get('password')
        senha_remocao_confere = authenticate(username=servidor.matricula, password=senha) is not None

        for field in request.POST:
            try:
                selecao = field.split('selecao_')[1]  # selecao_?
                if selecao:
                    compensacoes_selecionadas_ids.append(selecao)
            except Exception:
                pass

        if senha_remocao_confere and compensacoes_selecionadas_ids:
            compensacoes.filter(id__in=compensacoes_selecionadas_ids).delete()

            return httprr('/admin/ponto/horariocompensacao/?tab=meus_informes', 'Informes de Compensação removidos com sucesso.')

    if compensacoes:
        if compensacoes_por_data_saldo:
            compensacoes = compensacoes.order_by('data_compensacao')
        else:
            compensacoes = compensacoes.order_by('data_aplicacao')

    return locals()


@rtr()
@permission_required('ponto.add_recessoopcaoescolhida')
def editar_chefe_recesso_escolhido(request, recesso_opcao_escolhida_id):
    recesso_opcao_escolhida = get_object_or_404(RecessoOpcaoEscolhida, pk=recesso_opcao_escolhida_id)

    title = 'Editar o Chefe Imediato de {}'.format(recesso_opcao_escolhida)

    usuario_logado = request.user.get_relacionamento()
    usuario_logado_is_solicitante = usuario_logado == recesso_opcao_escolhida.funcionario
    usuario_logado_is_chefe = recesso_opcao_escolhida.is_chefe(usuario_logado)
    chefes = recesso_opcao_escolhida.chefes

    eh_possivel_editar_o_chefe = (usuario_logado_is_solicitante or usuario_logado_is_chefe) and recesso_opcao_escolhida.is_aguardando and len(chefes) >= 1

    if not eh_possivel_editar_o_chefe:
        return httprr('/ponto/abrir_recesso_escolhido/{}/'.format(recesso_opcao_escolhida_id), 'Não é possível modificar o Chefe Imediato.', 'error')

    form = RecessoOpcaoEscolhidaEditarChefeForm(request.POST or None, instance=recesso_opcao_escolhida)

    if form.is_valid():
        form.save()
        return httprr('/ponto/abrir_recesso_escolhido/{}/'.format(recesso_opcao_escolhida_id), 'Chefe Imediato modificado com sucesso.')

    return locals()


@rtr()
@login_required()
def localizar_acompanhamentos(request):
    if not (request.user.is_superuser or request.user.has_perm('rh.eh_rh_sistemico') or request.user.has_perm('rh.eh_rh_campus')):
        raise PermissionDenied

    title = 'Localizar Acompanhamentos'

    form = LocalizarServidorForm(request.POST or None)
    acompanhamentos = RecessoOpcaoEscolhida.objects.none()
    if form.is_valid():
        acompanhamentos = RecessoOpcaoEscolhida.objects.filter(funcionario__id=form.cleaned_data['servidor'].id)

    return locals()


@rtr()
@login_required()
def editar_acompanhamento(request, recesso_opcao_escolhida_id):
    if not (request.user.is_superuser or request.user.has_perm('rh.eh_rh_sistemico') or request.user.has_perm('rh.eh_rh_campus')):
        raise PermissionDenied

    acompanhamento = get_object_or_404(RecessoOpcaoEscolhida, pk=recesso_opcao_escolhida_id)
    dias_efetivos_a_compensar = acompanhamento.dias_efetivos_a_compensar()
    dias_efetivos_a_compensar_format = [dia_efetivo.strftime('%d/%m/%Y') for dia_efetivo in dias_efetivos_a_compensar]

    title = 'Editar Acompanhamento'

    form = RecessoOpcaoEscolhidaEditarForm(request.POST or None, instance=acompanhamento)
    if form.is_valid():
        form.save()
        return httprr('/ponto/localizar_acompanhamentos/', '{}: Acompanhamento \'{}\' salvo com sucesso.'.format(acompanhamento.funcionario, acompanhamento.recesso_opcao))

    return locals()


@rtr()
@permission_required('ponto.add_horariocompensacao')
def ver_compensacao_detalhada(request):
    title = 'Relatório Detalhado da Compensação de Horários'

    servidor = request.user.get_relacionamento()

    form = HorarioCompensacaoPeriodoForm(request.POST or None)

    if form.is_valid():
        contexto = Contexto(servidor=servidor, periodo_data_inicial=form.cleaned_data.get('data_inicio'), periodo_data_final=form.cleaned_data.get('data_fim'))

        total_exigido = 0
        total_trabalhado = 0
        total_situacao_inicial_debito = 0
        total_situacao_inicial_saldo = 0
        total_desconsiderado_debito = 0
        total_desconsiderado_saldo = 0
        total_considerado_debito = 0
        total_considerado_saldo = 0
        total_reposto_do_debito = 0
        total_utilizado_do_saldo = 0
        total_restante_debito = 0
        total_restante_saldo = 0

        for dia in list(contexto.dias.values()):
            total_exigido += dia.carga_horaria_qtd
            total_trabalhado += dia.carga_horaria_trabalhada_qtd
            total_situacao_inicial_debito += dia.debito_qtd_inicial
            total_situacao_inicial_saldo += dia.saldo_qtd_inicial
            total_desconsiderado_debito += dia.debito_qtd_desconsiderado
            total_desconsiderado_saldo += dia.saldo_qtd_desconsiderado
            total_considerado_debito += dia.debito_qtd_considerado
            total_considerado_saldo += dia.saldo_qtd_considerado
            total_reposto_do_debito += dia.debito_qtd_reposto
            total_utilizado_do_saldo += dia.saldo_qtd_utilizado
            total_restante_debito += dia.debito_qtd_restante
            total_restante_saldo += dia.saldo_qtd_restante

    return locals()


@rtr()
@permission_required('ponto.add_recessoopcaoescolhida')
def atualizar_lista_dias_efetivos_a_compensar(request, recesso_opcao_escolhida_id):
    recesso_opcao_escolhida = get_object_or_404(RecessoOpcaoEscolhida, pk=recesso_opcao_escolhida_id)
    recesso_opcao_escolhida.dias_efetivos_a_compensar_cache = ''
    recesso_opcao_escolhida.dias_efetivos_a_compensar()
    return httprr('/ponto/abrir_recesso_escolhido/{}/'.format(recesso_opcao_escolhida_id))


##########################################################################################
##########################################################################################


@rtr()
@login_required
@transaction.atomic
def documento_anexar_add(request, dia_ponto):
    title = 'Anexar Documento'

    dia_data = date(year=int(dia_ponto[-4:]), month=int(dia_ponto[2:-4]), day=int(dia_ponto[:2]))

    hoje = datetime.date(datetime.today())

    if dia_data > hoje:
        return HttpResponseForbidden('Não é possível anexar documentos em datas futuras.')

    pessoa = request.user.get_profile()

    rel_ponto = Frequencia.relatorio_ponto_pessoa(vinculo=request.user.get_vinculo(), data_ini=dia_data, data_fim=dia_data)
    freq = rel_ponto['dias'][0]
    freq_keys = list(freq.keys())

    form = DocumentoAnexoForm(request.POST or None, request.FILES or None, vinculo=request.user.get_vinculo(), data=dia_data)

    if form.is_valid():
        form.save()
        return httprr('..', 'Documento anexado.')

    return locals()


@rtr()
@login_required
@transaction.atomic
def documento_anexar_change(request, pk):
    title = 'Anexar Documento'

    documento_anexo = get_object_or_404(DocumentoAnexo, pk=pk)
    pessoa = request.user.get_profile()

    if documento_anexo.vinculo != request.user.get_vinculo():
        return HttpResponseForbidden()

    form = DocumentoAnexoChangeForm(request.POST or None, instance=documento_anexo)

    if form.is_valid():
        form.save()
        return httprr('..', 'Operação realizada.')

    return locals()


@login_required
@transaction.atomic
def documento_anexar_delete(request, pk):
    documento_anexo = get_object_or_404(DocumentoAnexo, pk=pk)

    if documento_anexo.vinculo != request.user.get_vinculo():
        return HttpResponseForbidden()

    documento_anexo.delete()

    return httprr(request.META.get('HTTP_REFERER', '..'), 'Observação excluída com sucesso.')


@rtr()
@login_required
@csrf_exempt
def adicionar_abono_inconsistencia_frequencia_lote(request):
    if not ('frequencias_dias' in request.GET):
        return httprr(
            '..',
            'Nenhum dia escolhido para avaliação.',
            tag='error',
            close_popup=True)

    title = 'Homologação de frequências em Lote'

    frequencias_dias = request.GET.getlist('frequencias_dias')

    ancora = None
    servidor_matricula = None
    tipo_inconsistencia = None
    dias = list()
    for index, value in enumerate(frequencias_dias):
        if len(value.split("_")) < 2:
            return httprr(
                '..',
                'Entrada incorreta de dados!',
                tag='error',
                close_popup=True)
        else:
            if index == 0:
                servidor_matricula = value.split("_")[0]
                servidor_faltoso = get_object_or_404(Servidor, matricula=servidor_matricula)
                servidor = request.user.get_relacionamento()
                ancora = servidor_faltoso.matricula or ''
                if servidor_faltoso == servidor:
                    return httprr(
                        '..',
                        'Servidor não pode abonar suas próprias inconsistências.',
                        tag='error',
                        anchor=ancora,
                        close_popup=True)
                if servidor_faltoso.eh_liberado_controle_frequencia():
                    return httprr(
                        '..',
                        'São dispensados do controle de frequência os ocupantes de cargos de Direção - CD, hierarquicamente iguais ou superiores a DAS 4 ou CD - 3',
                        tag='error',
                        anchor=ancora,
                        close_popup=True)
            elif servidor_matricula != value.split("_")[0]:
                return httprr(
                    '..',
                    'Erro: Há mais de um servidor na validação!',
                    tag='error',
                    anchor=ancora,
                    close_popup=True)
            data_falta = value.split("_")[1]
            data_inconsistencia = datetime.strptime(data_falta, "%d%m%Y").date()
            ancora = servidor_faltoso.matricula + data_inconsistencia.strftime('%d/%m/%Y') or ''

            contexto_compensacao = Contexto(
                servidor=servidor_faltoso.get_vinculo().relacionamento, periodo_data_inicial=data_inconsistencia, periodo_data_final=data_inconsistencia
            )

            frequencias_servidor = Frequencia.get_frequencias_por_data(servidor_faltoso.get_vinculo(), data_inconsistencia)

            inconsistencia = Frequencia.get_inconsistencias(
                servidor_faltoso.get_vinculo(), data_inconsistencia, contexto_compensacao=contexto_compensacao, frequencias=frequencias_servidor
            )

            tem_saida_antecipada = Frequencia.tem_saida_antecipada(
                servidor_faltoso.get_vinculo(), data_inconsistencia, contexto_compensacao=contexto_compensacao, frequencias=frequencias_servidor
            )

            if not inconsistencia and not tem_saida_antecipada:
                return httprr(
                    '..',
                    'Servidor não tem inconsistências para algumas das datas marcadas. ' 'Refaça a marcação.',
                    tag='error',
                    anchor=ancora,
                    close_popup=True)

            observacoes_servidor = Observacao.objects.filter(vinculo=servidor_faltoso.get_vinculo(), data=data_inconsistencia)
            anexos = DocumentoAnexo.objects.filter(vinculo=servidor_faltoso.get_vinculo(), data=data_inconsistencia)
            jornada_trabalho_obj = servidor_faltoso.get_jornadas_periodo_dict(data_inconsistencia, data_inconsistencia).get(data_inconsistencia)
            jornada_trabalho = jornada_trabalho_obj.get_jornada_trabalho_diaria()
            dias.append({'data': data_inconsistencia, 'jornada_trabalho_obj': jornada_trabalho_obj, 'observacoes_servidor': observacoes_servidor, 'anexos': anexos})

            if inconsistencia:
                tipo_inconsistencia_dia = inconsistencia[0]
            else:
                tipo_inconsistencia_dia = ''

            tipo_inconsistencia_form = tipo_inconsistencia_dia
            tipo_inconsistencia_dia = AbonoChefia.CHOICES_POR_INCONSISTENCIAS[tipo_inconsistencia_dia]

            if index == 0:
                tipo_inconsistencia = tipo_inconsistencia_dia
            elif tipo_inconsistencia != tipo_inconsistencia_dia:
                return httprr(
                    '..',
                    'Devem ser selecionados somente dias com a mesma inconsistência: TEMPO EXCEDENTE ou ' 'TEMPO INFERIOR.',
                    tag='error',
                    anchor=ancora,
                    close_popup=True)

            setor = servidor_faltoso.setor_suap_servidor_no_dia(data_inconsistencia)
            setor_chefe = servidor.setor
            if not setor:
                return httprr(
                    '..',
                    'Servidor não está associado a nenhum setor.',
                    tag='error',
                    anchor=ancora,
                    close_popup=True)

            # - verifica se foi/é chefe no setor e no período indicado
            is_chefe_de_setor = servidor.eh_chefe_do_setor_periodo(setor, data_inconsistencia, data_inconsistencia)
            if not is_chefe_de_setor:
                return httprr(
                    '..',
                    'Funcionalidade acessada apenas por FGs ou CDs.',
                    tag='error',
                    anchor=ancora,
                    close_popup=True)
            abono = None
            try:
                abono = AbonoChefia.objects.get(vinculo_pessoa=servidor_faltoso.get_vinculo(), data=data_inconsistencia)
            except AbonoChefia.DoesNotExist:
                pass
            if abono:
                return httprr(
                    '..',
                    'Já existe abono de inconsistência para alguns destes dias.',
                    tag='error',
                    anchor=ancora,
                    close_popup=True)

    FormClass = AbonoChefiaLoteFormFactory(tipo_inconsistencia_form, frequencias_dias)
    form = FormClass(request.POST or None)

    if form.is_valid():
        data_anchor = datetime.today()
        for dia in dias:
            data_anchor = dia['data']
            abono = AbonoChefia.objects.create(
                vinculo_pessoa=servidor_faltoso.get_vinculo(),
                vinculo_chefe_imediato=servidor.get_vinculo(),
                data=dia['data'],
                descricao=request.POST['descricao'],
                acao_abono=request.POST['acao_abono'],
            )
        ancora = servidor_faltoso.matricula + data_anchor.strftime('%d/%m/%Y') or ''

        return httprr(
            '..',
            'Abonos de inconsistência salvos com sucesso.',
            anchor=ancora,
            close_popup=True)

    return locals()
