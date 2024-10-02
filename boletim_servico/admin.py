# -*- coding: utf-8 -*-

from django.contrib import admin
from django.urls import reverse
from django.utils.safestring import mark_safe

from djtools.contrib.admin import ModelAdminPlus
from documento_eletronico.models import Documento
from boletim_servico import models
from .forms import BoletimProgramadoForm


class ConfiguracaoSetorInline(admin.TabularInline):
    model = models.ConfiguracaoSetorBoletim
    min_num = 1
    extra = 0


@admin.register(models.BoletimProgramado)
class BoletimProgramadoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('titulo', 'link', 'acoes')
    list_filter = ['tipo_documento']
    inlines = [ConfiguracaoSetorInline]
    form = BoletimProgramadoForm

    def get_changeform_initial_data(self, request):
        return {'criado_por': request.user, 'nivel_acesso': Documento.NIVEL_ACESSO_PUBLICO}

    @mark_safe
    def link(self, obj):
        if obj.programado:
            url = reverse('admin:boletim_servico_boletimdiario_changelist') + '?boletim_programado={}'.format(obj.pk)
        else:
            url = reverse('admin:boletim_servico_boletimperiodo_changelist') + '?boletim_programado={}'.format(obj.pk)

        return '<a href="{}" class="btn default">Visualizar Boletins</a>'.format(url)

    def acoes(self, obj):
        return mark_safe('<a href="/boletim_servico/gerar_boletim_servico/{}/" class="btn">Gerar Boletim</a>'.format(obj.pk))
    acoes.short_description = 'Ações'

    def save_model(self, request, obj, form, change):
        if not obj.pk:
            obj.criado_por = request.user
        obj.save()


@admin.register(models.BoletimDiario)
class BoletimDiarioAdmin(ModelAdminPlus):
    list_display = ('titulo', 'situacao', 'data_criacao')
    list_filter = ('boletim_programado', 'situacao')
    date_hierarchy = 'data'
    ordering = ['-data']
    list_display_links = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return True

    def get_list_filter(self, request):
        if not request.user.has_perm('boletim_servico.add_boletimprogramado'):
            return []
        return super(BoletimDiarioAdmin, self).get_list_filter(request)

    def get_list_display(self, request):
        if not request.user.has_perm('boletim_servico.add_boletimprogramado'):
            return ('titulo', 'data_criacao')
        return super(BoletimDiarioAdmin, self).get_list_display(request)

    @mark_safe
    def titulo(self, obj):
        if obj.possui_link:
            return '<a href="{}">{}</a>'.format(obj.arquivo.url, obj)
        return f'{obj}'

    titulo.short_description = 'Título'

    def get_queryset(self, request, manager=None, *args, **kwargs):
        qs = super(BoletimDiarioAdmin, self).get_queryset(request, manager, *args, **kwargs)
        if not request.user.has_perm('boletim_servico.add_boletimprogramado'):
            qs = qs.filter(situacao=models.BoletimDiario.Situacao.FINALIZADO)
        return qs


@admin.register(models.BoletimPeriodo)
class BoletimPeriodoAdmin(ModelAdminPlus):
    list_display = ('titulo', 'situacao', 'data_criacao', 'acoes')
    list_filter = ('boletim_programado', 'situacao')
    date_hierarchy = 'data_inicio'
    ordering = ['-data_inicio']
    list_display_links = None

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        if obj:
            return False
        return True

    def get_list_filter(self, request):
        if not request.user.has_perm('boletim_servico.add_boletimprogramado'):
            return []
        return super(BoletimPeriodoAdmin, self).get_list_filter(request)

    def get_list_display(self, request):
        if not request.user.has_perm('boletim_servico.add_boletimprogramado'):
            return ('titulo', 'data_criacao')
        return super(BoletimPeriodoAdmin, self).get_list_display(request)

    @mark_safe
    def titulo(self, obj):
        if obj.possui_link:
            return '<a href="{}">{}</a>'.format(obj.arquivo.url, obj)
        return f'{obj}'

    titulo.short_description = 'Título'

    def get_queryset(self, request, manager=None, *args, **kwargs):
        qs = super(BoletimPeriodoAdmin, self).get_queryset(request, manager, *args, **kwargs)
        if not request.user.has_perm('boletim_servico.add_boletimprogramado'):
            qs = qs.filter(situacao=models.BoletimPeriodo.Situacao.FINALIZADO)
        return qs

    def acoes(self, obj):
        opcoes = '<ul class="action-bar">'

        usuario = self.request.user

        if obj.situacao not in [3, 4]:
            opcoes += '<li><a href="/boletim_servico/reprocessar_boletim/{}/" class="btn primary">Reprocessar Boletim</a></li>'.format(obj.id)

        if usuario.has_perm('boletim_servico.delete_boletimperiodo'):
            opcoes += '<li><a href="/boletim_servico/remover_boletim_periodo/{}/" class="btn danger">Excluir</a></li>'.format(
                obj.id)

        opcoes += '</ul>'
        return mark_safe(opcoes)

    acoes.short_description = 'Ações'
