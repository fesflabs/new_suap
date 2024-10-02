# -*- coding: utf-8 -*-
from django.utils.safestring import mark_safe

from compras.forms import ProcessoCompraForm, EventoForm, FaseForm
from compras.models import ProcessoCompra, ProcessoCompraCampus, Calendario, TipoEvento, Evento, Nucleo, TipoProcesso, \
    Processo, Fase, SolicitacaoParticipacao
from django.contrib import admin
from django.utils.formats import localize
from djtools.contrib.admin import ModelAdminPlus


class ProcessoCompraCampusInline(admin.StackedInline):
    model = ProcessoCompraCampus


class ProcessoCompraAdmin(ModelAdminPlus):
    form = ProcessoCompraForm
    exclude = ['status']
    inlines = [ProcessoCompraCampusInline]
    list_display = ['show_link', 'show_periodo_inclusao', 'show_tags']

    def save_formset(self, request, form, formset, change):
        super(ProcessoCompraAdmin, self).save_formset(request, form, formset, change)
        if form.cleaned_data['aplicar_todos']:
            form.instance.aplicar_todos_campus()

    def show_link(self, obj):
        return mark_safe('<a href="{}">{}</a>'.format(obj.get_absolute_url(), str(obj)))

    show_link.short_description = 'Processo de compra'

    def show_periodo_inclusao(self, obj):
        return mark_safe('<span class="{}">{} a {}</span>'.format(obj.is_em_periodo_de_inclusao(), localize(obj.data_inicio), localize(obj.data_fim)))

    show_periodo_inclusao.admin_order_field = 'data_inicio'
    show_periodo_inclusao.short_description = 'Período para Inclusão/Validação'

    def show_tags(self, obj):
        return ', '.join([str(item) for item in obj.tags.all()])

    show_tags.short_description = 'Tags'


admin.site.register(ProcessoCompra, ProcessoCompraAdmin)


class CalendarioAdmin(ModelAdminPlus):
    list_display = ('descricao', 'ativo')
    list_filter = ('ativo', )
    ordering = ('descricao',)


admin.site.register(Calendario, CalendarioAdmin)


class TipoEventoAdmin(ModelAdminPlus):
    list_display = ('descricao', 'calendario', 'ativo')
    ordering = ('descricao',)
    list_filter = ('ativo', )


admin.site.register(TipoEvento, TipoEventoAdmin)


class EventoAdmin(ModelAdminPlus):
    form = EventoForm
    list_display = ('tipo_evento', 'get_calendario', 'data_inicio', 'data_fim', 'ativo')
    ordering = ('tipo_evento', 'data_inicio', )
    list_filter = ('tipo_evento__calendario', 'ativo', )
    list_display_icons = True

    def get_calendario(self, obj):
        return obj.tipo_evento.calendario.descricao
    get_calendario.short_description = 'Calendário'


admin.site.register(Evento, EventoAdmin)


class NucleoAdmin(ModelAdminPlus):
    list_display = ('descricao', 'get_componentes', 'get_tipos_processo', 'ativo')
    ordering = ('descricao', 'ativo', )
    list_filter = ('ativo', )
    list_display_icons = True

    def get_componentes(self, obj):
        return ', '.join([pessoa.nome for pessoa in obj.componentes.all()])
    get_componentes.short_description = 'Servidores Relacionados'

    def get_tipos_processo(self, obj):
        return ', '.join([tipo.descricao for tipo in obj.tipoprocesso_set.all()])
    get_tipos_processo.short_description = 'Tipos de Processo'


admin.site.register(Nucleo, NucleoAdmin)


class TipoProcessoAdmin(ModelAdminPlus):
    list_display = ('descricao', 'nucleo_responsavel', 'tipo_calendario', 'ativo')
    ordering = ('descricao', 'ativo', )
    list_filter = ('nucleo_responsavel', 'ativo', )
    list_display_icons = True


admin.site.register(TipoProcesso, TipoProcessoAdmin)


class ProcessoAdmin(ModelAdminPlus):
    list_display = ('tipo_processo', 'situacao', 'get_campi_solicitantes', 'get_opcoes')
    ordering = ('tipo_processo', 'situacao', )
    list_filter = ('tipo_processo', 'situacao', )
    list_display_icons = True

    def get_campi_solicitantes(self, obj):
        return obj.get_campi_solicitantes()
    get_campi_solicitantes.short_description = 'Campi que solicitaram participação'

    def get_opcoes(self, obj):
        texto = '<ul class="action-bar">'
        texto += '<li><a href="/compras/adicionar_fase/{}/" class="btn success">Adicionar Fase</a></li>'.format(obj.pk)
        texto += '<li><a href="/admin/compras/fase/?processo__id__exact={}" class="btn default">Ver Fases</a></li>'.format(obj.pk)
        texto += '</ul>'
        return mark_safe(texto)

    get_opcoes.short_description = 'Opções'

    def has_add_permission(self, request):
        return request.user.has_perm('compras.add_processo') and (request.user.has_perm('compras.add_calendario') or Nucleo.objects.filter(componentes=request.user.get_relacionamento()).exists())

    def get_queryset(self, request):
        qs = super(ProcessoAdmin, self).get_queryset(request)
        if request.user.has_perm('compras.add_calendario'):
            return qs
        else:
            return qs.filter(tipo_processo__nucleo_responsavel__componentes=request.user.get_relacionamento())


admin.site.register(Processo, ProcessoAdmin)


class FaseAdmin(ModelAdminPlus):
    form = FaseForm
    list_display = ('processo', 'data_inicio', 'data_fim', 'fase_inicial', 'ativo', 'get_opcoes')
    ordering = ('data_inicio', 'ativo', )
    list_filter = ('processo', 'ativo', )
    list_display_icons = True

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        qs = super(FaseAdmin, self).get_queryset(request)
        if request.user.has_perm('compras.add_calendario'):
            return qs
        else:
            return qs.filter(processo__tipo_processo__nucleo_responsavel__componentes=request.user.get_relacionamento())

    def get_opcoes(self, obj):
        if obj.fase_inicial:
            texto = '<ul class="action-bar">'
            texto += '<li><a href="/admin/compras/solicitacaoparticipacao/?fase__id__exact={}" class="btn default">Ver Solicitações de Participação</a></li>'.format(obj.pk)
            texto += '</ul>'
            return mark_safe(texto)
    get_opcoes.short_description = 'Opções'


admin.site.register(Fase, FaseAdmin)


class SolicitacaoParticipacaoAdmin(ModelAdminPlus):
    form = FaseForm
    list_display = ('fase', 'campus_solicitante', 'solicitada_em', 'solicitada_por', )
    ordering = ('campus_solicitante', 'solicitada_em', )
    list_filter = ('fase', 'campus_solicitante',)
    list_display_icons = True

    def has_add_permission(self, request):
        return False

    def get_queryset(self, request):
        qs = super(SolicitacaoParticipacaoAdmin, self).get_queryset(request)
        if request.user.has_perm('compras.add_calendario'):
            return qs
        else:
            return qs.filter(fase__processo__tipo_processo__nucleo_responsavel__componentes=request.user.get_relacionamento())


admin.site.register(SolicitacaoParticipacao, SolicitacaoParticipacaoAdmin)
