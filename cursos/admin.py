# -*- coding: utf-8 -*-
from datetime import date

from django.contrib import admin
from django.utils.safestring import mark_safe

from cursos.enums import SituacaoParticipante
from cursos.forms import CursoForm, AtividadeForm, CotaExtraForm
from cursos.models import Curso, Atividade, Participante, CotaExtra
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from djtools.templatetags.filters import format_money, in_group
from rh.models import Funcao


class CursoAdmin(ModelAdminPlus):
    list_display = ('descricao', 'campus', 'ano_pagamento', 'qtd_participantes', 'horas_total', 'valor_total', 'get_situacao')
    list_filter = ('ano_pagamento', 'campus', 'tipo', 'situacao')
    search_fields = ['descricao']
    ordering = ['ano_pagamento']
    list_display_icons = True
    form = CursoForm

    def get_fieldsets(self, request, obj=None):
        fieldsets = (('', {'fields': ('descricao', 'ano_pagamento', 'campus', 'tipo', 'edital', 'processos', 'responsaveis')}),)
        if request.user.is_superuser:
            fieldsets = fieldsets + (('Só Superusuarios', {'fields': ('situacao',)}),)
        return fieldsets

    def valor_total(self, obj):
        return format_money(obj.valor_total())

    valor_total.short_description = 'Valor Total'

    def horas_total(self, obj):
        return obj.horas_trabalhadas_total() or '-'

    horas_total.short_description = 'Qtd. Horas Trabalhadas'

    def qtd_participantes(self, obj):
        return obj.participante_set.count()

    qtd_participantes.short_description = 'Qtd. de Participantes'

    def get_situacao(self, obj):
        return obj.get_situacao_html()

    get_situacao.short_description = 'Situação'
    get_situacao.admin_order_field = 'situacao'

    '''
    Sobrescrevendo o queryset de acordo com o acesso permitido de cada usuário
    '''

    def get_queryset(self, request):
        queryset = super(CursoAdmin, self).get_queryset(request)

        usuario = request.user

        if usuario.is_superuser or in_group(
            usuario, 'Coordenador de Gestão de Pessoas Sistêmico, Coordenador de Gestão de Pessoas, Operador de Gestão de Pessoas, Operador de Cursos e Concursos'
        ):
            return queryset
        else:
            servidor_logado = usuario.get_relacionamento()
            if servidor_logado.eh_servidor:
                qs1 = queryset.filter(responsaveis=servidor_logado)
                qs2 = queryset.filter(participante__servidor=servidor_logado)
                queryset = (qs1 | qs2).distinct()
            else:
                queryset = queryset.none()
        return queryset


admin.site.register(Curso, CursoAdmin)


class AtividadeAdmin(ModelAdminPlus):
    list_display = ['descricao', 'valor']
    search_fields = ('descricao',)
    list_filter = ["ativa"]

    list_display_icons = True
    form = AtividadeForm

    def valor(self, obj):
        return "{}".format(obj.valor_hora)

    valor.short_description = 'Valor'
    valor.admin_order_field = 'valor_hora'


admin.site.register(Atividade, AtividadeAdmin)


class CotaExtraAdmin(ModelAdminPlus):
    list_display = ['servidor', 'get_processos', 'ano', 'horas_permitida']
    search_fields = ['servidor__nome', 'servidor__matricula']
    list_filter = ['ano']
    form = CotaExtraForm
    list_display_icons = True

    def get_processos(self, obj):
        html = '<ul>'
        for o in obj.processos.all():
            html += '<li>{}</li>'.format(o)
        html += '</ul>'
        return mark_safe(html)

    get_processos.short_description = 'Processos'


admin.site.register(CotaExtra, CotaExtraAdmin)


class ParticipanteAdmin(ModelAdminPlus):
    list_display = ['servidor', 'curso', 'atividade', 'horas_prevista']
    search_fields = ['servidor__nome', 'servidor__matricula']
    list_display_icons = True
    show_count_on_tabs = True
    list_filter = [CustomTabListFilter, 'curso', ]

    def get_list_display(self, request):
        default_list_display = super(ParticipanteAdmin, self).get_list_display(request)

        if request.GET.get('tab') is None:
            coluna = ('_get_situacao',)
            nova_list_display = default_list_display + coluna
            return nova_list_display

        if request.GET.get('tab') == 'tab_aguardando_chefia':
            coluna = ('get_horas_disponiveis',)

            # verificando se é chefe para mostrar as opções de deferimento/indeferimento
            servidor = request.user.get_relacionamento()
            if (servidor.funcao and servidor.funcao.codigo in Funcao.get_codigos_funcao_chefia()) or (servidor.servidorfuncaohistorico_set.atuais().exists()):
                coluna = ('get_horas_disponiveis', '_get_acoes')

            nova_list_display = default_list_display + coluna
            return nova_list_display

        if request.GET.get('tab') == 'tab_indeferido_chefia':
            coluna = ('motivo_nao_liberacao',)
            nova_list_display = default_list_display + coluna
            return nova_list_display

        return default_list_display

    def _get_situacao(self, obj):
        return obj.get_situacao_html()

    _get_situacao.short_description = 'Situação'

    def _get_acoes(self, obj):
        servidor = self.request.user.get_relacionamento()
        html = '<ul class="action-bar">'
        if servidor == obj.servidor:
            html += '<li><span class="status status-aguardando-validacao">Esperando ação do chefe imediato.</span></li>'
        elif obj.problema_com_horas:
            html += '<li><span class="status status-error">Servidor não tem horas disponíveis para liberação.</span></li>'
            html += '<li><a class="btn danger no-confirm popup" href="/cursos/indeferir_participacao/{}/">Indeferir</a></li>'.format(obj.id)
        else:
            html += '<li><a class="btn success confirm" href="/cursos/deferir_participacao/{}/">Deferir</a></li>'.format(obj.id)
            html += '<li><a class="btn danger no-confirm popup" href="/cursos/indeferir_participacao/{}/">Indeferir</a></li>'.format(obj.id)
        html += '</ul>'
        return mark_safe(html)

    _get_acoes.short_description = 'Ações'

    def has_add_permission(self, request):
        return False

    def get_horas_disponiveis(self, obj):
        return obj.horas_disponiveis_ano

    get_horas_disponiveis.short_description = 'Horas Disponíveis'

    '''
    TABS
    '''

    def get_tabs(self, request):
        return ['tab_aguardando_chefia', 'tab_deferido_chefia', 'tab_indeferido_chefia']

    def tab_aguardando_chefia(self, request, queryset):
        return queryset.filter(situacao=SituacaoParticipante.AGUARDANDO_LIBERACAO)

    tab_aguardando_chefia.short_description = 'Aguardando Aprovação da Chefia'

    def tab_deferido_chefia(self, request, queryset):
        return queryset.filter(situacao=SituacaoParticipante.LIBERADO)

    tab_deferido_chefia.short_description = 'Deferidos pela Chefia'

    def tab_indeferido_chefia(self, request, queryset):
        return queryset.filter(situacao=SituacaoParticipante.NAO_LIBERADO)

    tab_indeferido_chefia.short_description = 'Indeferidos pela Chefia'

    '''
    Sobrescrevendo o queryset de acordo com o tipo de usuário
    '''

    def get_queryset(self, request):
        queryset = super(ParticipanteAdmin, self).get_queryset(request)
        usuario = request.user
        servidor_logado = usuario.get_relacionamento()
        hoje = date.today()
        if usuario.is_superuser:
            return queryset
        if servidor_logado.eh_servidor:
            # se chefe do setor
            setores_sou_chefe_pks = []
            for historico_funcao in servidor_logado.historico_funcao(hoje, hoje).filter(
                    funcao__codigo__in=Funcao.get_codigos_funcao_chefia()):
                if historico_funcao.setor_suap:
                    setores_sou_chefe_pks += historico_funcao.setor_suap.ids_descendentes
            setores_sou_chefe_pks = set(setores_sou_chefe_pks)
            if setores_sou_chefe_pks:
                queryset = queryset.filter(servidor__setor__id__in=setores_sou_chefe_pks)
            else:
                # ver apenas a própria participação
                queryset = queryset.filter(servidor=servidor_logado)
        else:
            queryset = queryset.none()
        return queryset


admin.site.register(Participante, ParticipanteAdmin)
