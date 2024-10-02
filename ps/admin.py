# -*- coding: utf-8 -*-

from django.contrib import admin

from djtools.contrib.admin import ModelAdminPlus
from ps.models import OfertaVaga, Inscricao


class OfertaVagaAdmin(ModelAdminPlus):
    list_display = ['unidade', 'concurso', 'curso', 'turno', 'qtd', 'ano', 'semestre']
    search_fields = ['unidade', 'concurso']
    list_filter = ('uo', 'concurso', 'turno', 'ano', 'semestre')


admin.site.register(OfertaVaga, OfertaVagaAdmin)


class InscricaoAdmin(ModelAdminPlus):
    list_display = ['cpf', 'candidato', 'numero', 'unidade', 'concurso', 'curso', 'ano', 'semestre']
    search_fields = ['nome_candidato']
    list_filter = ('uo', 'concurso', 'ano', 'semestre')


admin.site.register(Inscricao, InscricaoAdmin)
