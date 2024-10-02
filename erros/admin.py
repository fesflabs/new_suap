from datetime import datetime

from dateutil.relativedelta import relativedelta
from django.apps import apps
from django.contrib import admin
from django.contrib.admin import SimpleListFilter
from django.utils.safestring import mark_safe

from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from djtools.templatetags.filters import in_group, format_
from erros.forms import ErroForm
from erros.models import Erro
from erros.utils import get_apps_disponiveis


class ModuloAfetadoListFilter(SimpleListFilter):
    title = 'Módulo Afetado'
    parameter_name = 'modulo_afetado'

    def lookups(self, request, model_admin):
        return [(c.label, c.verbose_name) for c in get_apps_disponiveis()]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(view__icontains=self.value())
        else:
            return queryset


class SouInteressadoErroFilter(SimpleListFilter):
    title = 'Sou Interessado'
    parameter_name = 'sou_interessado'

    def lookups(self, request, model_admin):
        return [('sim', 'Sim'), ('nao', 'Não')]

    def queryset(self, request, queryset):
        if self.value() == 'sim':
            return queryset.filter(interessadoerro__vinculo=request.user.get_vinculo())
        else:
            return queryset


class AtribuidoAMimErroListFilter(SimpleListFilter):
    title = 'Atribuído a Mim'
    parameter_name = 'atribuido_a_mim'

    def lookups(self, request, model_admin):
        return [('sim', 'Sim'), ('nao', 'Não')]

    def queryset(self, request, queryset):
        if self.value() == 'sim':
            return queryset.filter(atendente_atual=request.user.get_vinculo())
        else:
            return queryset


class PendenteAtribuicaoErroListFilter(SimpleListFilter):
    title = 'Pendente de Atribuição'
    parameter_name = 'pendente_atribuicao'

    def lookups(self, request, model_admin):
        return [('sim', 'Sim'), ('nao', 'Não')]

    def queryset(self, request, queryset):
        if self.value() == 'sim':
            return queryset.filter(atendente_atual__isnull=True)
        else:
            return queryset


class ErroAdmin(ModelAdminPlus):
    list_display = ()
    list_filter = (CustomTabListFilter, ModuloAfetadoListFilter, SouInteressadoErroFilter, 'atendente_atual')
    search_fields = ('url', 'view')
    list_display_icons = True
    show_count_on_tabs = True
    ordering = ('-qtd_vinculos_afetados', 'data_criacao')
    form = ErroForm

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if in_group(request.user, 'Desenvolvedor'):
            list_display += ('id', 'get_modulo_afetado', 'view', 'get_url_erro', 'get_tem_url_sentry', 'get_tem_url_gitlab', 'get_data_criacao', 'informante', 'qtd_vinculos_afetados', 'atendente_atual')
        else:
            list_display += ('id', 'get_modulo_afetado', 'get_url_erro', 'get_data_criacao', 'informante')
        return list_display

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if in_group(request.user, 'Desenvolvedor'):
            list_filter += (AtribuidoAMimErroListFilter, )
        if in_group(request.user, 'Recebedor de Demandas'):
            list_filter += (PendenteAtribuicaoErroListFilter, )
        return list_filter

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        if in_group(request.user, 'Desenvolvedor'):
            return qs
        else:
            return (qs.exclude(situacao=Erro.SITUACAO_CANCELADO) | qs.filter(situacao=Erro.SITUACAO_CANCELADO, interessadoerro__vinculo=request.user.get_vinculo())).distinct()

    def get_url_erro(self, obj):
        url = obj.url
        url_trimmed = (url[:100] + '...') if len(url) > 103 else url
        return url_trimmed

    get_url_erro.short_description = 'URL'
    get_url_erro.admin_order_field = 'url'

    def get_tabs(self, request):
        return ['tab_abertos', 'tab_em_andamento', 'tab_aguardando_feedback', 'tab_resolvidos', 'tab_cancelados', 'tab_any_data']

    def tab_abertos(self, request, queryset):
        return queryset.filter(situacao__in=[Erro.SITUACAO_ABERTO, Erro.SITUACAO_REABERTO])

    tab_abertos.short_description = 'Reportados'

    def tab_em_andamento(self, request, queryset):
        return queryset.filter(situacao=Erro.SITUACAO_EM_ANDAMENTO)

    tab_em_andamento.short_description = 'Em análise'

    def tab_resolvidos(self, request, queryset):
        return queryset.filter(situacao=Erro.SITUACAO_RESOLVIDO)

    tab_resolvidos.short_description = 'Resolvidos'

    def tab_aguardando_feedback(self, request, queryset):
        return queryset.filter(situacao=Erro.SITUACAO_SUSPENSO)

    tab_aguardando_feedback.short_description = 'Aguardando feedback'

    def tab_cancelados(self, request, queryset):
        return queryset.filter(situacao=Erro.SITUACAO_CANCELADO)

    tab_cancelados.short_description = 'Cancelados'

    def get_tem_url_sentry(self, obj):
        return mark_safe(format_(bool(obj.url_sentry)))

    get_tem_url_sentry.short_description = 'Tem URL do Sentry?'

    def get_tem_url_gitlab(self, obj):
        return mark_safe(format_(bool(obj.gitlab_issue_url)))

    get_tem_url_gitlab.short_description = 'Tem URL do Gitlab?'

    def get_modulo_afetado(self, obj):
        try:
            return apps.get_app_config(obj.modulo_afetado).verbose_name
        except Exception:
            return '-'

    get_modulo_afetado.short_description = 'Módulo Afetado'

    def get_data_criacao(self, obj):
        quinze_dias = datetime.now() + relativedelta(days=-15)
        data_criacao = obj.data_criacao
        if data_criacao < quinze_dias:
            return mark_safe('<span class="false">{}</span>'.format(data_criacao.strftime("%d/%m/%Y")))
        else:
            return data_criacao

    get_data_criacao.short_description = 'Reportado em'

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


admin.site.register(Erro, ErroAdmin)
