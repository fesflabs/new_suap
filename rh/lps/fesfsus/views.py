
# -*- coding: utf-8 -*-

from collections import OrderedDict
from datetime import date, datetime

from django.contrib.auth.decorators import permission_required
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize

from comum.models import Configuracao
from comum.utils import get_qtd_dias_por_ano, get_uo
from djtools import layout
from djtools.utils import rtr
from rh.models import (
    PCA,
    Servidor,
    ServidorAfastamento,
    ServidorFuncaoHistorico,
    ServidorOcorrencia,
    ServidorSetorHistorico,
    ServidorSetorLotacaoHistorico,
    Situacao,
    Viagem, CargaHorariaReduzida, Funcao, UnidadeOrganizacional,
)
from rh.views import rh_servidor_view_tab, index
from suap import settings

'''
Substituição da view servidor em views.py
'''

@layout.quadro("Gestão de Pessoas", icone="users", pode_esconder=True)
def index_quadros(quadro, request):
    eh_rh_sistemico = request.user.has_perm("rh.eh_rh_sistemico")
    eh_rh_campus = request.user.has_perm("rh.eh_rh_campus")
    if eh_rh_sistemico or eh_rh_campus:
        qtd_servidores_sem_setor_suap = Servidor.get_sem_setor_suap().count()
        if qtd_servidores_sem_setor_suap:
            quadro.add_item(
                layout.ItemContador(
                    titulo="Servidor{}".format(pluralize(qtd_servidores_sem_setor_suap, "es")),
                    subtitulo="Sem setor SUAP",
                    qtd=qtd_servidores_sem_setor_suap,
                    url="/rh/servidores_sem_setor_suap/",
                )
            )

        qtd_processos_afastamento_parcial_a_validar_rh = CargaHorariaReduzida.get_processos_rh_a_validar().count()
        if qtd_processos_afastamento_parcial_a_validar_rh:
            quadro.add_item(
                layout.ItemContador(
                    titulo="Processo{} de afastamento parcial".format(pluralize(qtd_processos_afastamento_parcial_a_validar_rh, "s")),
                    subtitulo="A validar",
                    qtd=qtd_processos_afastamento_parcial_a_validar_rh,
                    url="/admin/rh/cargahorariareduzida/",
                )
            )

        qtd_servidores_sem_cargo = Servidor.get_sem_cargo().count()
        if qtd_servidores_sem_cargo:
            quadro.add_item(
                layout.ItemContador(
                    titulo="Servidor{}".format(pluralize(qtd_servidores_sem_cargo, "es")),
                    subtitulo="Sem cargo",
                    qtd=qtd_servidores_sem_cargo,
                    url="/rh/servidores_sem_cargo/",
                )
            )

        hoje = datetime.now()
        uo = get_uo(request.user)
        if eh_rh_sistemico and uo and "edu" in settings.INSTALLED_APPS:
            qtd_docentes_sem_disciplina_ingresso = (
                Servidor.objects.docentes()
                .filter(situacao__codigo=Situacao.ATIVO_PERMANENTE, professor__disciplina__isnull=True, setor__uo=uo)
                .count()
            )
            if qtd_docentes_sem_disciplina_ingresso:
                quadro.add_item(
                    layout.ItemContador(
                        titulo="Docente{} sem disciplina de ingresso".format(pluralize(qtd_docentes_sem_disciplina_ingresso)),
                        subtitulo="Campus {}".format(uo),
                        qtd=qtd_docentes_sem_disciplina_ingresso,
                        url="/edu/disciplina_ingresso_docentes/?campus={}&disciplinas={}".format(uo.pk, 1),
                    )
                )

        if eh_rh_sistemico and uo:
            qtd_servidores_sem_area = (
                Servidor.objects.ativos()
                .filter(cargo_emprego__cargoempregoarea__isnull=False, cargo_emprego_area__isnull=True)
                .distinct()
                .count()
            )
            if qtd_servidores_sem_area:
                quadro.add_item(
                    layout.ItemContador(
                        titulo="Servidor{}".format(pluralize(qtd_servidores_sem_area, "es")),
                        subtitulo="Sem área",
                        qtd=qtd_servidores_sem_area,
                        url="/rh/servidores_por_area/?com_area_cadastrada=2",
                    )
                )

        if uo:
            servidor_funcao_historico = ServidorFuncaoHistorico.objects.filter(
                setor__uo__equivalente=uo, data_fim_funcao__gte=hoje, setor_suap__isnull=True
            ).exclude(funcao__codigo=Funcao.CODIGO_ESTAGIARIO) | ServidorFuncaoHistorico.objects.filter(
                setor__uo__equivalente=uo, data_fim_funcao__isnull=True, setor_suap__isnull=True
            ).exclude(
                funcao__codigo=Funcao.CODIGO_ESTAGIARIO
            )
            qtd_servidor_funcao_historico = servidor_funcao_historico.count()
            if qtd_servidor_funcao_historico:
                uo_siape = UnidadeOrganizacional.objects.siape().filter(equivalente=uo, setor__excluido=False).latest("pk")
                quadro.add_item(
                    layout.ItemContador(
                        titulo="Funções de Servidores sem Setor SUAP",
                        subtitulo="Campus {}".format(uo_siape),
                        qtd=qtd_servidor_funcao_historico,
                        url="/admin/rh/servidorfuncaohistorico/?setoruo={}&com_data_fim=False".format(uo_siape.pk),
                    )
                )

    if request.user.has_perm("rh.view_servidor"):
        quadro.add_item(layout.ItemAcessoRapido(titulo="Servidores", icone="users", url="/admin/rh/servidor/?excluido__exact=0"))
        quadro.add_item(layout.BuscaRapida(titulo="Servidor", url="/admin/rh/servidor/"))
    return quadro

