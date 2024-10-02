# -*- coding: utf-8 -*-


from django.contrib import admin

from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from egressos.forms import PesquisaForm
from egressos.models import Pesquisa


class PesquisaAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ['titulo', 'descricao', 'modalidade', 'inicio', 'fim']
    search_fields = ('titulo', 'descricao')
    list_filter = [CustomTabListFilter, 'modalidade', 'conclusao', 'uo', 'curso_campus']
    form = PesquisaForm

    fieldsets = (('Dados da Pesquisa', {'fields': (('titulo',), ('descricao',))}), ('Público Alvo', {'fields': ('modalidade', 'conclusao', 'uo', 'curso_campus')}))


admin.site.register(Pesquisa, PesquisaAdmin)
