# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.safestring import mark_safe

from avaliacao_integrada.forms import IndicadorForm, AvaliacaoForm, EixoForm
from avaliacao_integrada.models import Dimensao, TipoAvaliacao, Segmento, Indicador, Variavel, OpcaoResposta, Avaliacao, Eixo, Macroprocesso, Iterador, Resposta
from djtools.contrib.admin import ModelAdminPlus
from djtools.utils import httprr


class EixoAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('ordem', 'descricao')
    list_display_icons = True
    export_to_xls = True
    form = EixoForm


admin.site.register(Eixo, EixoAdmin)


class DimensaoAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_filter = ('eixo',)
    list_display = ('ordem', 'descricao', 'eixo')
    list_display_icons = True
    export_to_xls = True


admin.site.register(Dimensao, DimensaoAdmin)


class MacroprocessoAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_filter = ('dimensao', 'dimensao__eixo')
    list_display = ('ordem', 'descricao', 'dimensao', 'eixo')
    fields = ('dimensao', 'descricao')
    list_display_icons = True
    export_to_xls = True

    def eixo(self, obj):
        return obj.dimensao.eixo


admin.site.register(Macroprocesso, MacroprocessoAdmin)


class TipoAvaliacaoAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('descricao',)
    list_display_icons = True
    export_to_xls = True


admin.site.register(TipoAvaliacao, TipoAvaliacaoAdmin)


class SegmentoAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('id', 'descricao')
    export_to_xls = True


admin.site.register(Segmento, SegmentoAdmin)


class VariavelInline(admin.TabularInline):
    model = Variavel
    extra = 1


class OpcaoRespostaInline(admin.TabularInline):
    model = OpcaoResposta
    extra = 1


class IteradorInline(admin.TabularInline):
    model = Iterador
    extra = 0


class IndicadorAdmin(ModelAdminPlus):
    list_display = ('ordem', 'macroprocesso', 'nome', 'aspecto', 'tipo_resposta', 'get_anos_referencia', 'get_acoes')
    list_filter = ('anos_referencia', 'macroprocesso', 'macroprocesso__dimensao__eixo', 'tipo_resposta', 'em_uso', 'segmentos', 'areas_vinculacao', 'modalidades')
    search_fields = ('nome', 'aspecto')
    list_display_icons = True
    export_to_xls = True
    form = IndicadorForm
    fieldsets = IndicadorForm.fieldsets
    inlines = [VariavelInline, OpcaoRespostaInline, IteradorInline]

    def get_anos_referencia(self, obj):
        lista = ['<ul>']
        for ano in obj.anos_referencia.all():
            lista.append('<li> ')
            lista.append(str(ano))
            lista.append('</li>')
        lista.append('</ul>')
        return mark_safe(''.join(lista))

    get_anos_referencia.short_description = 'Anos de Referência'

    def get_acoes(self, obj):
        return mark_safe('<a href="/avaliacao_integrada/replicar_indicador/{}/" class="btn">Replicar Indicador</a>'.format(obj.pk))

    get_acoes.short_description = 'Opções'

    def response_change(self, request, obj):
        return httprr('..', 'Indicador editado com sucesso.')


admin.site.register(Indicador, IndicadorAdmin)


class AvaliacaoAdmin(ModelAdminPlus):
    list_display = ('nome', 'descricao', 'ano', 'data_inicio', 'data_termino')
    list_filter = ('tipos', 'areas_vinculacao', 'segmentos', 'modalidades', 'ano__ano')
    search_fields = ('nome', 'descricao')
    form = AvaliacaoForm
    fieldsets = AvaliacaoForm.fieldsets
    list_display_icons = True
    export_to_xls = True

    def response_change(self, request, obj):
        return httprr('..', 'Avaliação editada com sucesso.')


admin.site.register(Avaliacao, AvaliacaoAdmin)


class RespostaAdmin(ModelAdminPlus):
    list_filter = ('indicador__macroprocesso__dimensao__eixo', 'indicador__macroprocesso__dimensao', 'indicador__macroprocesso', 'respondente__segmento', 'respondente__avaliacao', 'indicador')
    list_display = ('indicador', 'valor')
    list_display_icons = True


admin.site.register(Resposta, RespostaAdmin)
