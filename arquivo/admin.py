# -*- coding: utf-8 -*-
from django.contrib import admin

from arquivo.forms import TipoArquivoForm
from arquivo.models import TipoArquivo, Arquivo, Processo, Funcao
from djtools.contrib.admin import ModelAdminPlus


class TipoArquivoAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao', 'processo')
    search_fields = ('descricao',)
    form = TipoArquivoForm

    def save_model(self, request, obj, form, change):
        processo_id = request.POST.get('processo')
        processo = Processo.objects.get(id=processo_id)
        obj.save()
        processo.tipos_arquivos.add(obj)


admin.site.register(TipoArquivo, TipoArquivoAdmin)


class ProcessoAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao')
    search_fields = ('descricao',)


admin.site.register(Processo, ProcessoAdmin)


class FuncaoAdmin(ModelAdminPlus):
    list_display = ('id', 'descricao')
    search_fields = ('descricao',)


admin.site.register(Funcao, FuncaoAdmin)


class ArquivoAdmin(ModelAdminPlus):
    list_display = ('id', 'nome', 'tipo_arquivo', 'processo_protocolo', 'status')
    list_filter = ('tipo_arquivo',)
    search_fields = ('nome',)


admin.site.register(Arquivo, ArquivoAdmin)
