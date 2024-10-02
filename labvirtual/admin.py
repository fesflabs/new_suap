from django.contrib import admin
from django.utils.safestring import mark_safe
from django.urls import reverse
#
from djtools.contrib.admin import ModelAdminPlus
from djtools.contrib.admin import CustomTabListFilter, DateRangeListFilter
from djtools.utils import get_datetime_now, httprr
#
from agendamento.status import SolicitacaoAgendamentoStatus
from .models import SolicitacaoLabVirtual, AgendamentoLabVirtual, DesktopPool
from .forms import DesktopPoolForm
from .perms import pode_gerenciar_solicitacao_labvirtual


class DesktopPoolAdmin(ModelAdminPlus):
    list_display = ('name', 'description', 'location', 'get_options', )
    change_list_template = 'vdi/change_list.html'
    ordering = ('name', )
    list_display_icons = True
    form = DesktopPoolForm

    def has_add_permission(self, request):
        return False

    def get_options(self, obj):
        texto = '<ul class="action-bar">'
        #
        if self.request.user.has_perm('labvirtual.add_solicitacaolabvirtual'):
            texto = texto + '<li><a class="btn" href="{}">Solicitar Agendamento</a></li>'.format(
                reverse('labvirtual:solicitar_agendamento', kwargs={"pk": obj.pk})
            )
        #
        texto = texto + '</ul>'
        return mark_safe(texto)
    #
    get_options.short_description = 'Ações'

    def get_queryset(self, request, manager=None, *args, **kwargs):
        queryset = super().get_queryset(request, manager, *args, **kwargs)
        return queryset.my_desktop_pools(request.user)


admin.site.register(DesktopPool, DesktopPoolAdmin)


class SolicitacaoLabVirtualAdmin(ModelAdminPlus):
    list_display = (
        'laboratorio', 'solicitante', 'get_periodo',
        'get_recorrencias', 'get_status',
        'get_options'
    )
    list_filter = (
        CustomTabListFilter, 'status',
        ('data_inicio', DateRangeListFilter),
        ('data_fim', DateRangeListFilter),
    )
    exclude = (
        'status',
        'data_avaliacao', 'observacao_avaliador',
        'justificativa_cancelamento', 'data_cancelamento',
        'cancelado_por'
    )
    search_fields = ('laboratorio__nome', 'solicitante__pessoafisica__nome')
    date_hierarchy = 'data_inicio'
    ordering = ('-data_inicio', '-hora_inicio')
    #
    list_display_icons = True
    #
    export_to_xls = True
    show_count_on_tabs = True
    #
    readonly_fields = ['laboratorio', ]

    actions = ["sincronizar_agendamentos"]

    def sincronizar_agendamentos(self, request, queryset):
        #
        for object in queryset.filter(status=SolicitacaoAgendamentoStatus.STATUS_DEFERIDA):
            object.finalizar()
            object.save()
        #

    def add_view(self, request):
        app_label = DesktopPool._meta.app_label
        model_name = DesktopPool._meta.model_name
        url = reverse(f'admin:{app_label}_{model_name}_changelist')
        return httprr(url)

    def has_add_permission(self, request):
        has_permission = super().has_add_permission(request)
        return has_permission

    def has_delete_permission(self, request, obj=None):
        has_permission = super().has_delete_permission(request, obj=obj)
        return has_permission and pode_gerenciar_solicitacao_labvirtual(request.user, obj)

    # TODO: LabVirtual nao tem o metodo pode_editar
    def has_change_permission(self, request, obj=None):
        has_permission = super().has_change_permission(request, obj=obj)
        has_permission = has_permission and obj.pode_editar(user=request.user) if obj else has_permission
        return has_permission

    def get_tabs(self, request):
        tabs = []
        tabs = ['tab_minhas_solicitacoes', 'tab_solicitacoes_a_avaliar']
        tabs.append('tab_minhas_solicitacoes_futuras')
        return tabs

    def tab_minhas_solicitacoes_futuras(self, request, queryset):
        hoje = get_datetime_now()
        agora = hoje.time()
        reservas_derefidas = queryset.filter(solicitante=request.user)
        reservas_derefidas_hoje = reservas_derefidas.filter(data_inicio=hoje.date(), hora_inicio__gt=agora)
        reservas_derefidas_futuras = reservas_derefidas.filter(data_inicio__gt=hoje.date())
        return reservas_derefidas_hoje | reservas_derefidas_futuras

    tab_minhas_solicitacoes_futuras.short_description = 'Minhas Solicitações Futuras'

    def tab_minhas_solicitacoes(self, request, queryset):
        return queryset.filter(solicitante=request.user)

    tab_minhas_solicitacoes.short_description = 'Minhas Solicitações'

    def tab_solicitacoes_a_avaliar(self, request, queryset):
        return queryset.filter(status=SolicitacaoAgendamentoStatus.STATUS_ESPERANDO)

    tab_solicitacoes_a_avaliar.short_description = 'Solicitações a Avaliar'

    def get_periodo(self, obj):
        return obj.get_periodo()

    get_periodo.short_description = 'Período'

    def get_recorrencias(self, obj):
        return obj.get_recorrencias()

    get_recorrencias.short_description = 'Recorrência'

    def get_status(self, obj):
        return obj.get_formated_status()

    get_status.short_description = 'Status'

    def get_options(self, obj):
        texto = '<ul class="action-bar">'
        if obj.pode_editar_membros():
            texto += '<li><a class="btn success" href="{}"> Adicionar Membro</a></li>'.format(
                reverse('labvirtual:procurar_usuario', args=[obj.pk])
            )
        #
        texto = texto + '</ul>'
        return mark_safe(texto)
    #
    get_options.short_description = 'Ações'


admin.site.register(SolicitacaoLabVirtual, SolicitacaoLabVirtualAdmin)


class AgendamentoLabVirtualAdmin(ModelAdminPlus):
    list_display = ('laboratorio', 'get_ocorrencias', 'solicitante', 'get_status', 'get_options')
    search_fields = ('laboratorio__nome', 'solicitante__pessoafisica__nome')

    readonly_fields = [
        'status',
        'solicitacao', 'laboratorio'
    ]

    list_filter = (
        'status',
        ('data_hora_inicio', DateRangeListFilter),
    )
    list_display_icons = True
    ordering = ('-data_hora_inicio',)

    #
    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        # has_change_permission = super().has_change_permission(request, obj=obj)
        # return has_change_permission and obj.inativo if obj else has_change_permission
        return False

    def has_delete_permission(self, request, obj=None):
        has_delete_permission = super().has_delete_permission(request, obj=obj)
        return has_delete_permission and obj.inativo if obj else has_delete_permission

    def get_options(self, obj):
        texto = '<ul class="action-bar">'
        if not obj.finalizado:
            # if obj.pode_ativar():
            texto += '<li><a class="btn success popup" href="{}">Ativar</a></li>'.format(
                reverse('labvirtual:liberar_agendamento', kwargs={"pk": obj.pk})
            )
            #
            # if obj.pode_inativar():
            texto += '<li><a class="btn danger popup" href="{}">Encerrar</a></li>'.format(
                reverse('labvirtual:encerrar_agendamento', kwargs={"pk": obj.pk})
            )
            #
        #
        texto = texto + '</ul>'
        return mark_safe(texto)
    #
    get_options.short_description = 'Ações'

    #
    def get_status(self, obj):
        if obj.ativo:
            retorno = '<span class="status status-success">{}</span>'.format(obj.get_status_display())
        elif obj.inativo:
            retorno = '<span class="status status-alert">{}</span>'.format(obj.get_status_display())
        else:
            retorno = '<span class="status status-error">{}</span>'.format(obj.get_status_display())

        return mark_safe(retorno)

    get_status.short_description = 'Status'

    def get_ocorrencias(self, obj):
        return obj.get_ocorrencias()

    get_ocorrencias.short_description = 'Ocorrência(s)'


admin.site.register(AgendamentoLabVirtual, AgendamentoLabVirtualAdmin)
