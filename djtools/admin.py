from django.utils.safestring import mark_safe

from djtools.models import Task
from django.contrib import admin
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from djtools.templatetags.filters import in_group


class TaskAdmin(ModelAdminPlus):
    list_display = ('id', 'type', 'user', 'start', 'get_progress', 'end', 'get_message', 'total', 'partial')
    ordering = ('-start',)
    list_filter = [CustomTabListFilter, 'type']
    search_fields = ('user__username', 'uuid')
    show_count_on_tabs = True
    list_display_icons = True

    def get_queryset(self, request, *args, **kwargs):
        qs = super().get_queryset(request, *args, **kwargs)
        if in_group(request.user, 'Desenvolvedor'):
            return qs
        return qs.filter(user=request.user)

    def get_message(self, obj):
        if in_group(self.request.user, 'Desenvolvedor'):
            return obj.message
        if obj.error:
            return 'Erro ao processar esta tarefa.'
        else:
            return obj.message
    get_message.short_description = 'Situação'

    def get_tabs(self, request):
        return ['tab_em_execucao']

    def tab_em_execucao(self, request, queryset):
        return queryset.filter(end__isnull=True)

    tab_em_execucao.short_description = 'Em Execução'

    def has_view_permission(self, request, obj=None):
        if obj:
            return in_group(request.user, 'Desenvolvedor') or obj.user == request.user
        else:
            return True

    def get_action_bar(self, request):
        super().get_action_bar(request, remove_add_button=True)

    def get_progress(self, obj):
        return mark_safe(f'''<div class="progress"><p>{obj.get_progress()}%</p></div>''')
    get_progress.short_description = 'Progresso'


admin.site.register(Task, TaskAdmin)
