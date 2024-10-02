# -*- coding: utf-8 -*-
from django.utils.safestring import mark_safe

from django.contrib import admin
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from encceja.models import Avaliacao, AreaConhecimento, Configuracao, Pontuacao, Solicitacao
from rh.models import UnidadeOrganizacional


class AvaliacaoAdmin(ModelAdminPlus):
    list_display = ('ano', 'tipo', 'descricao_edital', 'pontuacao_min_area_conhecimento', 'pontuacao_min_redacao')
    list_filter = ('ano', 'tipo')
    search_fields = ('descricao_edital',)
    ordering = ('ano', 'tipo')
    export_to_xls = True
    list_per_page = 15
    list_display_icons = True
    fieldsets = (
        ('Dados Gerais', {'fields': ('ano', 'tipo', 'descricao_edital')}),
        ('Pontuações Mínimas', {'fields': ('pontuacao_min_area_conhecimento', 'pontuacao_min_redacao')}),
    )


admin.site.register(Avaliacao, AvaliacaoAdmin)


class AreaConhecimentoAdmin(ModelAdminPlus):
    list_display = ('nome', 'descricao')
    search_fields = ('nome', 'descricao')
    export_to_xls = True
    list_per_page = 15
    list_display_icons = True


admin.site.register(AreaConhecimento, AreaConhecimentoAdmin)


class ConfiguracaoAdmin(ModelAdminPlus):
    list_display = ('descricao', 'ativa')
    list_filter = ('ativa',)
    search_fields = ('descricao',)
    export_to_xls = True
    list_per_page = 15
    list_display_icons = True


admin.site.register(Configuracao, ConfiguracaoAdmin)


class PontuacaoInline(admin.StackedInline):
    model = Pontuacao
    extra = 1


class SolicitacaoAdmin(ModelAdminPlus):
    list_display = ('nome', 'cpf', 'get_edicao_encceja', 'aproveitamento_de_notas_outras_edicoes', 'get_tipo_certificacao', 'get_situacao')
    list_xls_display = 'nome', 'cpf', 'configuracao', 'data_emissao', 'tipo_certificado_display', 'atendida'
    list_filter = (CustomTabListFilter, 'configuracao__ano', 'emissor', 'tipo_certificado', 'uo', 'cancelada', 'aproveitamento_de_notas_outras_edicoes')
    search_fields = ('nome', 'cpf', 'inscricao')
    date_hierarchy = 'data_emissao'
    ordering = ('nome', 'configuracao')
    export_to_xls = True
    list_per_page = 15
    list_display_icons = True
    inlines = [PontuacaoInline]

    fieldsets = (
        ('Dados Gerais', {'fields': (('configuracao', 'uo'), 'processo')}),
        ('Dados do Solicitante', {'fields': (('nome', 'inscricao'), ('cpf', 'data_nascimento'), 'ppl')}),
        ('Pontuação da Redação', {'fields': (('avaliacao_redacao', 'pontuacao_redacao'),)}),
    )

    def get_form(self, request, *args, **kwargs):
        form = super(SolicitacaoAdmin, self).get_form(request, *args, **kwargs)
        form.base_fields['uo'].queryset = UnidadeOrganizacional.objects.campi()
        return form

    def get_action_bar(self, request):
        items = super(SolicitacaoAdmin, self).get_action_bar(request)
        if request.user.is_superuser or request.user.groups.filter(name='Administrador ENCCEJA').exists():
            items.append(dict(url='/encceja/importar_resultado/', label='Importar Resultado'))
        return items

    def get_tipo_certificacao(self, obj):
        return mark_safe(obj.get_tipo_certificacao(formatar=True))

    get_tipo_certificacao.short_description = 'Tipo de Certificação'

    def get_edicao_encceja(self, obj):
        return obj.configuracao.ano

    get_edicao_encceja.short_description = 'Edição'

    def get_situacao(self, obj):
        if obj.cancelada:
            return mark_safe('<span class="status status-error">Cancelada por {} em {}</span>'.format(obj.responsavel_cancelamento, obj.data_cancelamento.strftime("%d/%m/%y")))
        elif obj.atendida:
            texto = f'por {obj.emissor}'if obj.emissor else 'automaticamente'
            return mark_safe('<span class="status status-success">Atendida por {} em {}</span>'.format(texto, obj.data_emissao.strftime("%d/%m/%y")))
        return ''

    get_situacao.short_description = 'Situação'

    def get_tabs(self, request):
        return ['tab_avaliadas']

    def tab_avaliadas(self, request, queryset):
        return queryset.filter(data_emissao__isnull=False)

    tab_avaliadas.short_description = 'Avaliadas'


admin.site.register(Solicitacao, SolicitacaoAdmin)
