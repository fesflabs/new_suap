# -*- coding: utf-8 -*-

from django.contrib.admin.decorators import register
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from pit_rit.models import ConfiguracaoAtividadeDocente, TipoAtividadeDocente, PlanoIndividualTrabalho, AtividadeDocente
from django.contrib import messages
from django.utils.safestring import mark_safe
from rh.models import Servidor


@register(ConfiguracaoAtividadeDocente)
class ConfiguracaoAtividadeDocenteAdmin(ModelAdminPlus):
    list_filter = ('ano_letivo_inicio', 'periodo_letivo_inicio')
    list_display = ('ano_letivo_inicio', 'periodo_letivo_inicio', 'ha_semanal', 'ha_minima_semanal')
    list_display_icons = True


@register(TipoAtividadeDocente)
class TipoAtividadeDocenteAdmin(ModelAdminPlus):
    list_filter = ('categoria', 'ativo')
    list_display = ('descricao', 'ch_minima_semanal', 'ch_maxima_semanal', 'categoria', 'ativo')
    list_display_icons = True
    ordering = ('ativo',)
    fieldsets = (
        ('Dados Gerais', {'fields': ('descricao', 'categoria')}),
        ('Carga Horária', {'fields': (('ch_minima_semanal', 'ch_maxima_semanal'),)}),
        ('Outras Informações', {'fields': (('exige_documentacao', 'exige_horario', 'ativo'),)}),
    )


@register(PlanoIndividualTrabalho)
class PlanoIndividualTrabalhoAdmin(ModelAdminPlus):
    search_fields = ('professor__vinculo__pessoa__nome', 'professor__vinculo__user__username')
    list_display = ('professor', 'ano_letivo', 'periodo_letivo', 'get_qtd_atividades_nao_avaliadas', 'get_percentual_preenchimento_relatorio', 'deferida')
    list_filter = (CustomTabListFilter, 'ano_letivo', 'periodo_letivo', 'deferida')

    list_display_icons = True
    list_per_page = 15
    export_to_xls = True
    actions = 'publicar', 'revogar_publicacao'
    exclude = 'professor', 'ano_letivo', 'periodo_letivo', 'deferida'
    ordering = 'ano_letivo__ano', 'periodo_letivo', 'professor__vinculo__pessoa__nome'
    show_count_on_tabs = True

    def get_queryset(self, request):
        qs = super(PlanoIndividualTrabalhoAdmin, self).get_queryset(request, PlanoIndividualTrabalho.objects)
        qs = qs.filter(ano_letivo__ano__gt=2017) or qs.filter(ano_letivo__ano=2017, periodo_letivo=2)
        return qs

    def publicar(self, request, queryset):
        queryset.update(deferida=True)
        messages.success(request, 'Os planos selecionados foram publicados com sucesso.')

    publicar.short_description = 'Publicar'

    def revogar_publicacao(self, request, queryset):
        queryset.update(deferida=False)
        messages.success(request, 'A publicação dos planos selecionados foi revogada com sucesso.')

    revogar_publicacao.short_description = 'Revogar Publicação'

    def get_actions(self, request):
        actions = super(PlanoIndividualTrabalhoAdmin, self).get_actions(request)
        if not request.GET.get('tab') == 'tab_aguardando_publicacao':
            del actions['publicar']
        if not request.GET.get('tab') == 'tab_publicados':
            del actions['revogar_publicacao']
        return actions

    def get_tabs(self, request):
        return ['tab_sem_atividades', 'tab_pendentes', 'tab_aguardando_publicacao', 'tab_publicados']

    def tab_sem_atividades(self, request, queryset):
        return queryset.filter(atividadedocente__isnull=True)

    tab_sem_atividades.short_description = 'Sem Atividades Cadastradas'

    def tab_pendentes(self, request, queryset):
        diretor_academico = request.user.get_relacionamento()
        qs = AtividadeDocente.objects.filter(pit__professor__vinculo__pessoa__excluido=False, deferida__isnull=True)
        qs = qs.filter(pit__ano_letivo__ano__gt=2017) or qs.filter(pit__ano_letivo__ano=2017, pit__periodo_letivo=2)
        qs_atividades_docente = qs.filter(
            pit__professor__vinculo__pessoa__id__in=Servidor.objects.filter(setor_exercicio=diretor_academico.setor_exercicio).values_list('pessoa_fisica__id', flat=True)
        ) | qs.filter(pit__professor__vinculo__pessoa__id__in=Servidor.objects.filter(setor_lotacao=diretor_academico.setor_lotacao).values_list('pessoa_fisica__id', flat=True))
        ids = qs_atividades_docente.order_by('pit').values_list('pit', flat=True).distinct()
        return queryset.filter(id__in=ids)

    tab_pendentes.short_description = 'Com Atividades Não-Avaliadas'

    def tab_aguardando_publicacao(self, request, queryset):
        queryset = queryset.filter(ano_letivo__ano__gt=2017) or queryset.filter(ano_letivo__ano=2017, periodo_letivo=2)
        return queryset.exclude(deferida=True).exclude(atividadedocente__deferida__isnull=True).exclude(atividadedocente__isnull=True).distinct()

    tab_aguardando_publicacao.short_description = 'Aguardando Publicação'

    def tab_publicados(self, request, queryset):
        return queryset.filter(deferida=True)

    tab_publicados.short_description = 'Publicados'

    def has_add_permission(self, request):
        return False

    def get_qtd_atividades_nao_avaliadas(self, obj):
        total = obj.atividadedocente_set.count()
        if total:
            deferidas = obj.atividadedocente_set.filter(deferida=True).count()
            percentual = total and int(100.1 * deferidas / total) or 0
            return mark_safe('<div class="progress"><p>{}%</p></div>'.format(percentual))
        return '-'

    get_qtd_atividades_nao_avaliadas.short_description = 'Percentual de Deferimento das Atividades'

    def get_percentual_preenchimento_relatorio(self, obj):
        percentual = obj.get_percentual_preenchimento_relatorio()
        return mark_safe('<div class="progress"><p>{}%</p></div>'.format(percentual))

    get_percentual_preenchimento_relatorio.short_description = 'Percentual do Preenchimento do Relatório'
