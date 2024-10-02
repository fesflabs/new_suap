from django.contrib import admin, messages
from django.urls import reverse_lazy
from django.utils.safestring import mark_safe
from django.http import HttpResponseRedirect

from comum.utils import get_uo
from djtools.contrib.admin import ModelAdminPlus
from djtools.contrib.admin.filters import CustomTabListFilter
from djtools.templatetags.filters import in_group
from plan_estrategico.forms import PDIForm, PerspectivaForm, ArquivoMetaForm, PlanoAtividadePDIForm, PreenchimentoVariavelForm
from plan_estrategico.models import (
    PDI,
    Perspectiva,
    ObjetivoEstrategico,
    Indicador,
    Variavel,
    VariavelCampus,
    ArquivoMeta,
    PlanoAtividade,
    ProjetoPlanoAtividade,
    PeriodoPreenchimentoVariavel,
    ProjetoEstrategico,
    TematicaVariavel)


class PDIAdmin(ModelAdminPlus):
    list_display = ('ano_inicial_pdi', 'ano_final_pdi', 'qtd_anos', 'get_documento_url', 'get_mapa_url', 'get_manual_url', 'get_acoes')
    list_display_icons = True

    form = PDIForm

    fieldsets = (
        ('Período PDI', {'fields': ('qtd_anos', 'ano_inicial_pdi', 'ano_final_pdi', 'documento', 'mapa_estrategico', 'manual')}),
        ('Faixa do Farol de Desempenho', {'fields': (('valor_faixa_vermelha'), ('valor_faixa_amarela'), ('valor_faixa_verde'))}),
    )

    def get_documento_url(self, obj):
        if obj.documento:
            return mark_safe('<a href="{}">{}</a>'.format(obj.documento.url, 'Documento PDI'))
        return '-'

    get_documento_url.short_description = 'Documento PDI'

    def get_mapa_url(self, obj):
        if obj.mapa_estrategico:
            return mark_safe(f'<a href="{obj.mapa_estrategico.url}">Mapa Estratégico</a>')
        return '-'

    get_mapa_url.short_description = 'Mapa Estratégico'

    def get_manual_url(self, obj):
        if obj.manual:
            return mark_safe(f'<a href="{obj.manual.url}">Manual</a>')
        return '-'

    get_manual_url.short_description = 'Manual Indicadores'

    def get_acoes(self, obj):
        return mark_safe('<a class="btn" href="{}">Detalhar</a>'.format(reverse_lazy('pdi_ver', kwargs={'pdi_pk': obj.pk})))

    get_acoes.short_description = 'Ações'


admin.site.register(PDI, PDIAdmin)


class PerspectivaAdmin(ModelAdminPlus):
    list_display = ('sigla', 'nome', 'descricao')
    list_display_icons = True
    list_filter = ('id',)
    search_fields = ('nome',)

    form = PerspectivaForm

    fieldsets = ((None, {'fields': ('sigla', 'nome', 'descricao')}),)


admin.site.register(Perspectiva, PerspectivaAdmin)


class ProjetoEstrategicoAdmin(ModelAdminPlus):
    list_display = ('codigo', 'nome')
    list_display_icons = True
    search_fields = ('nome',)


admin.site.register(ProjetoEstrategico, ProjetoEstrategicoAdmin)


class ObjetivoEstrategicoAdmin(ModelAdminPlus):
    list_display = ('sigla', 'descricao')
    list_display_icons = True
    search_fields = ('descricao',)


admin.site.register(ObjetivoEstrategico, ObjetivoEstrategicoAdmin)


class IndicadorAdmin(ModelAdminPlus):
    list_display = ('sigla', 'descricao', 'tipo', 'calcular_media', 'get_tendencia')
    list_display_icons = True
    search_fields = ('sigla', 'descricao', 'tendencia')
    avoid_short_search = False

    def get_tendencia(self, obj):
        if obj.tendencia == Indicador.DIRECAO_ALTA:
            retorno = '<i style="color: green" class="fas fa-long-arrow-alt-up"></i>'
        else:
            retorno = '<i style="color: green" class="fas fa-long-arrow-alt-down"></i>'

        return mark_safe(retorno)

    get_tendencia.short_description = 'Tendência'


admin.site.register(Indicador, IndicadorAdmin)


class TematicaVariavelAdmin(ModelAdminPlus):
    list_display = ('nome',)
    ordering = ('nome',)
    search_fields = ('nome',)
    list_display_icons = True
    avoid_short_search = False


admin.site.register(TematicaVariavel, TematicaVariavelAdmin)


class VariavelAdmin(ModelAdminPlus):
    list_display = ('nome', 'sigla', 'descricao', 'tematica', 'fonte')
    list_filter = ('tematica',)
    exclude = ['valor']
    ordering = ('sigla',)
    search_fields = ('nome', 'sigla', 'fonte', 'descricao')
    list_display_icons = True
    avoid_short_search = False
    show_count_on_tabs = True


admin.site.register(Variavel, VariavelAdmin)


class VariavelCampusAdmin(ModelAdminPlus):
    list_display = ('get_variavel', 'get_situacao', 'uo', 'ano', 'get_fonte', 'get_valor_ideal', 'get_valor_real', 'get_valor_trimestral', 'data_atualizacao', 'get_opcoes')
    ordering = ('variavel__sigla', 'ano')
    list_filter = (CustomTabListFilter, 'uo', 'ano', 'variavel__fonte', 'variavel__tematica', 'situacao', )
    search_fields = ('variavel__nome', 'variavel__sigla')
    show_list_display_icons = True
    export_to_xls = True
    export_to_csv = True
    avoid_short_search = False
    actions = 'ativar_variavel', 'desativar_variavel'
    show_count_on_tabs = True
    list_display_links = None

    def get_opcoes(self, obj):
        opcoes = list()
        opcoes.append('<ul class="action-bar">')
        if PeriodoPreenchimentoVariavel.get_em_periodo_de_preenchimento() and PeriodoPreenchimentoVariavel.get_em_periodo_de_preenchimento()[0].ano.ano == obj.ano\
                and (in_group(self.request.user, 'Administrador de Planejamento Estratégico') or (in_group(self.request.user, 'Gestor Estratégico Local, Gestor Estratégico Sistêmico') and obj.variavel.fonte == 'Manual')):
            opcoes.append(f'<li><a href=/plan_estrategico/variavel/{obj.pk}/atualizar/ class="btn popup primary">Informar Valor </a></li>')
        if self.request.user.groups.filter(name='Administrador de Planejamento Estratégico'):
            opcoes.append(f'<li><a href=/plan_estrategico/variavel_ideal/{obj.pk}/atualizar/ class="btn popup primary">Atualizar Valor da Meta </a></li>')
        opcoes.append(f'<li><a href=/plan_estrategico/ver_valores_trimestrais/{obj.pk}/ class="btn popup default">Ver Valores Trimestrais </a></li>')
        opcoes.append(
            '<li><a href=/plan_estrategico/variavel/{}/visualizar/ class="btn popup default">Detalhar </a></li>'.format(
                obj.variavel.pk))
        opcoes.append('</ul>')
        return mark_safe(' '.join(opcoes))

    get_opcoes.short_description = 'Opções'

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if request.user.groups.filter(name__in=['Gestor Estratégico Local', 'Gestor Estratégico Sistêmico']):
            list_display = ('get_variavel', 'uo', 'ano', 'get_fonte', 'get_valor_real', 'get_valor_trimestral', 'data_atualizacao', 'get_opcoes')
        return list_display

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if request.user.groups.filter(name='Gestor Estratégico Local, Gestor Estratégico Sistêmico'):
            list_filter = (CustomTabListFilter, 'uo', 'ano', 'variavel__tematica')
        return list_filter

    def get_valor_ideal(self, obj):
        if obj.valor_ideal is None:
            return mark_safe('<span class="status status-alert">Aguardando valor</span>')
        else:
            return str(obj.valor_ideal).replace('.', ',')

    get_valor_ideal.short_description = 'Valor Meta'

    def get_fonte(self, obj):
        if obj.variavel.fonte:
            return obj.variavel.fonte

    get_fonte.short_description = 'Fonte'

    def get_variavel(self, obj):
        return obj.variavel.sigla

    get_variavel.short_description = 'Variável'

    def get_valor_real(self, obj):
        if obj.valor_real is None:
            return mark_safe('<span class="status status-alert">Aguardando valor</span>')
        else:
            return str(obj.valor_real).replace('.', ',')

    get_valor_real.short_description = 'Último valor informado'

    def get_valor_trimestral(self, obj):
        if obj.variavel.fonte != 'Manual':
            return mark_safe('<span class="status status-info">Preenchimento Automático</span>')
        elif obj.valor_trimestral is None:
            return mark_safe('<span class="status status-alert">Aguardando valor</span>')
        else:
            return str(obj.valor_trimestral).replace('.', ',')

    get_valor_trimestral.short_description = 'Valor Acumulado'

    def get_situacao(self, obj):
        if obj.situacao == VariavelCampus.ATIVA:
            return mark_safe('<span class="status status-success">Ativa</span>')
        else:
            return mark_safe('<span class="status status-danger">Não se aplica</span>')

    get_situacao.short_description = 'Situação'

    def get_tabs(self, request):
        return ['tab_manual', 'tab_automaticas']

    def get_queryset(self, request):
        queryset = super().get_queryset(request)
        if request.user.groups.filter(name='Gestor Estratégico Sistêmico'):
            queryset = queryset.filter(situacao=VariavelCampus.ATIVA)
            return queryset
        if request.user.groups.filter(name='Gestor Estratégico Local'):
            queryset = queryset.filter(uo=get_uo(request.user), situacao=VariavelCampus.ATIVA)
        return queryset

    def tab_manual(self, request, queryset):
        return queryset.filter(variavel__fonte='Manual')

    tab_manual.short_description = 'Variáveis Manuais'

    def tab_automaticas(self, request, queryset):
        return queryset.exclude(variavel__fonte='Manual')

    tab_automaticas.short_description = 'Variáveis Automáticas'

    def get_action_bar(self, request):
        pdi = PDI.objects.all().first()
        items = super().get_action_bar(request)
        if pdi.manual:
            url_base = pdi.manual.url
            items.append(dict(url=url_base, label='Manual de Indicadores'))
        return items

    def desativar_variavel(self, request, queryset):
        for variavel in queryset:
            if variavel.valor_real is None:
                variavel.valor_real = 0
            variavel.situacao = VariavelCampus.NAO_SE_APLICA
            variavel.save()
        messages.success(request, 'As variáveis selecionadas foram desativadas com sucesso.')

    desativar_variavel.short_description = 'Desativar variáveis selecionadas'

    def ativar_variavel(self, request, queryset):
        queryset.update(situacao=VariavelCampus.ATIVA)
        messages.success(request, 'As variáveis selecionadas foram ativadas com sucesso.')

    ativar_variavel.short_description = 'Ativar variáveis selecionadas'

    def get_actions(self, request):
        if in_group(request.user, 'Administrador de Planejamento Estratégico'):
            return super().get_actions(request)
        return []


admin.site.register(VariavelCampus, VariavelCampusAdmin)


class PeriodoPreenchimentoVariavelAdmin(ModelAdminPlus):
    list_display = ('ano', 'trimestre', 'data_inicio', 'data_termino')
    list_filter = ('ano',)
    list_display_icons = True

    form = PreenchimentoVariavelForm


admin.site.register(PeriodoPreenchimentoVariavel, PeriodoPreenchimentoVariavelAdmin)


class ArquivoMetaAdmin(ModelAdminPlus):
    list_display = ('arquivo', 'data_importacao', 'usuario')
    list_display_icons = True

    form = ArquivoMetaForm


admin.site.register(ArquivoMeta, ArquivoMetaAdmin)


class PlanoAtividadeAdmin(ModelAdminPlus):
    list_display = ('pdi', 'ano_base', 'data_geral_inicial', 'data_geral_final')
    list_display_icons = True

    form = PlanoAtividadePDIForm

    fieldsets = (
        (None, {'fields': ('pdi', 'ano_base', 'percentual_reserva_tecnica')}),
        ('Período de Vigência', {'fields': (('data_geral_inicial', 'data_geral_final'),)}),
        (
            'Período Pré-LOA',
            {
                'fields': (
                    ('data_orcamentario_preloa_inicial', 'data_orcamentario_preloa_final'),
                    ('data_projetos_preloa_inicial', 'data_projetos_preloa_final'),
                    ('data_atividades_preloa_inicial', 'data_atividades_preloa_final'),
                )
            },
        ),
        (
            'Período Pós-LOA',
            {
                'fields': (
                    ('data_orcamentario_posloa_inicial', 'data_orcamentario_posloa_final'),
                    ('data_projetos_posloa_inicial', 'data_projetos_posloa_final'),
                    ('data_atividades_posloa_inicial', 'data_atividades_posloa_final'),
                )
            },
        ),
    )


admin.site.register(PlanoAtividade, PlanoAtividadeAdmin)


class ProjetoPlanoAtividadeAdmin(ModelAdminPlus):
    list_display = ('projeto', 'plano_atividade')

    def delete_view(self, request, object_id, extra_context=None):
        obj = ProjetoPlanoAtividade.objects.get(id=int(object_id)).plano_atividade_id
        response = super().delete_view(request, object_id, extra_context)

        if isinstance(response, HttpResponseRedirect):
            return HttpResponseRedirect(f'/plan_estrategico/ver_plano_atividade/{obj}/?tab=projeto_estrategico')

        return response


admin.site.register(ProjetoPlanoAtividade, ProjetoPlanoAtividadeAdmin)
