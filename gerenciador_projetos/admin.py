# -*- coding: utf-8 -*-


from django.contrib import admin
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe

from djtools.contrib.admin import ModelAdminPlus, PermissionDenied
from djtools.templatetags.filters import status
from djtools.templatetags.tags import icon
from gerenciador_projetos.forms import ProjetoForm, ListaForm, TagForm, TipoAtividadeForm
from gerenciador_projetos.models import TipoAtividade, Projeto, Tag, Lista
from django.db.models import Q


class ProjetoAdmin(ModelAdminPlus):
    form = ProjetoForm
    list_display = ('get_acoes', 'titulo', 'get_areas', 'get_gerentes', 'get_membros', 'get_situacao_display', 'get_qtd_tarefas', 'get_opcoes')
    list_display_icons = False
    search_fields = ('titulo', 'descricao')
    list_filter = ('areas', 'gerentes', 'situacao')

    def get_acoes(self, obj):
        texto = icon('view', '/gerenciador_projetos/projeto/{:d}/'.format(obj.id))
        if obj.pode_editar_projeto():
            texto = texto + icon('edit', '/admin/gerenciador_projetos/projeto/{:d}/change'.format(obj.id))
        texto = texto + '</ul>'
        return mark_safe(texto)

    get_acoes.short_description = 'Ações'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.criado_por = request.user
        super(ProjetoAdmin, self).save_model(request, obj, form, change)

    def get_areas(self, obj):
        lista = ["<ul>"]
        for area in obj.areas.all():
            lista.append("<li>{}</li>".format(area))
        lista.append("</ul>")
        return mark_safe("\n".join(lista))

    get_areas.short_description = 'Áreas'

    def get_membros(self, obj):
        lista = ["<ul>"]
        for user in obj.membros.all():
            lista.append("<li>{} ({})</li>".format(user, user.pessoafisica.funcionario.setor))
        lista.append("</ul>")
        return mark_safe("\n".join(lista))

    get_membros.short_description = 'Membros'

    def get_qtd_tarefas(self, obj):
        return obj.tarefa_set.count()

    get_qtd_tarefas.short_description = 'Tarefas'

    def get_situacao_display(self, obj):
        return status(obj.get_situacao_display())

    get_situacao_display.short_description = 'Situação'

    def get_opcoes(self, obj):
        return mark_safe(
            '<ul class="action-bar">'
            '<li><a href="/gerenciador_projetos/projeto/{}/dashboard/" class="btn default"><span class="fas fa-columns" aria-hidden="true"></span> Dashboard</a></li>'
            '</ul>'.format(obj.id)
        )

    get_opcoes.short_description = 'Opções'

    def get_queryset(self, request):
        qs = super(ProjetoAdmin, self).get_queryset(request)
        qs = qs.filter(Q(gerentes__in=[request.user]) | Q(membros=request.user) | Q(interessados=request.user)).distinct()
        return qs

    def change_view(self, request, object_id, form_url='', extra_context=None):
        projeto = get_object_or_404(Projeto, pk=object_id)
        if not projeto.pode_editar_projeto(request.user):
            raise PermissionDenied()
        return super(ProjetoAdmin, self).change_view(request, object_id, form_url, extra_context)

    def get_gerentes(self, obj):
        lista = ["<ul>"]
        for user in obj.gerentes.all():
            lista.append("<li>{} ({})</li>".format(user, user.pessoafisica.funcionario.setor))
        lista.append("</ul>")
        return mark_safe("\n".join(lista))
    get_gerentes.short_description = 'Gerentes'


admin.site.register(Projeto, ProjetoAdmin)


class ListaAdmin(ModelAdminPlus):
    form = ListaForm
    search_fields = ('nome',)
    list_display = ('nome', 'ativa', 'criada_por')
    list_display_icons = True
    list_per_page = 25

    def get_queryset(self, request):
        qs = super(ListaAdmin, self).get_queryset(request)
        if not request.user.is_superuser:
            return qs.filter(criada_por=request.user)
        return qs

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.criada_por = request.user
        super(ListaAdmin, self).save_model(request, obj, form, change)


admin.site.register(Lista, ListaAdmin)


class TagAdmin(ModelAdminPlus):
    form = TagForm
    search_fields = ('nome',)
    list_filter = ('projeto',)
    list_display = ('projeto', 'nome', 'cor')
    list_display_icons = True
    list_per_page = 25

    def get_queryset(self, request):
        qs = super(TagAdmin, self).get_queryset(request)
        if not (request.user.is_superuser or request.user.groups.filter(name='centralservicos Administrador').exists()):
            return qs  # .filter(projeto__id=request.user.id)
        return qs


admin.site.register(Tag, TagAdmin)


class TipoAtividadeAdmin(ModelAdminPlus):
    form = TipoAtividadeForm
    search_fields = ('nome',)
    list_display = ('nome',)
    list_display_icons = True
    list_per_page = 25

    def get_queryset(self, request):
        qs = super(TipoAtividadeAdmin, self).get_queryset(request)
        if not (request.user.is_superuser or request.user.groups.filter(name='centralservicos Administrador').exists()):
            return qs  # .filter(projeto__id=request.user.id)
        return qs


admin.site.register(TipoAtividade, TipoAtividadeAdmin)
