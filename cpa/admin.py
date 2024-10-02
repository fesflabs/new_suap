# -*- coding: utf-8 -*-
from django.contrib import admin
from django.http.response import HttpResponseRedirect
from django.utils.safestring import mark_safe

from cpa.forms import QuestionarioForm
from cpa.models import Pergunta, Categoria, Resposta, Questionario, QuestionarioCategoria, QuestionarioOpcao, Opcao
from djtools.contrib.admin import ModelAdminPlus, StackedInlinePlus


class OpcaoAdmin(ModelAdminPlus):
    pass


admin.site.register(Opcao, OpcaoAdmin)


class CategoriaAdmin(ModelAdminPlus):
    # TODO: criar uma forma de fazer isso já no ModelAdminPlus
    def changelist_view(self, request, extra_context=None):
        retorno = super(CategoriaAdmin, self).changelist_view(request, extra_context)
        retorno.template_name = 'cpa/templates/admin/change_list.html'
        return retorno


admin.site.register(Categoria, CategoriaAdmin)


class QuestionarioCategoriaInline(StackedInlinePlus):
    model = QuestionarioCategoria


class QuestionarioOpcaoInline(StackedInlinePlus):
    model = QuestionarioOpcao


class QuestionarioAdmin(ModelAdminPlus):
    list_display = ['descricao', 'publico', 'ano', 'get_campus', 'get_opcoes']
    ordering = ('id',)
    search_fields = ('descricao',)
    list_filter = ('ano', 'publico')
    inlines = [QuestionarioCategoriaInline, QuestionarioOpcaoInline]
    list_display_icons = True
    form = QuestionarioForm

    def get_campus(self, obj):
        return mark_safe(obj.get_campus() or " - ")

    get_campus.short_description = 'Campus'

    def get_opcoes(self, obj):
        return mark_safe('<a href="/cpa/clonar_questionario/{:d}/" class="btn primary">Clonar</a>'.format(obj.pk))

    get_opcoes.short_description = 'Opções'

    def response_add(self, request, obj):
        self.message_user(request, 'Questionário cadastrado com sucesso.')
        return HttpResponseRedirect('/cpa/questionario/{:d}/'.format(obj.pk))


admin.site.register(Questionario, QuestionarioAdmin)


class PerguntaAdmin(ModelAdminPlus):
    list_display = ['id', 'texto', 'categoria', 'objetiva']
    ordering = ('id',)
    search_fields = ('texto',)
    list_filter = ['questionario', 'categoria', 'objetiva']


admin.site.register(Pergunta, PerguntaAdmin)


class RespostaAdmin(ModelAdminPlus):
    search_fields = ['pergunta__texto']
    list_display = ['id', 'get_pergunta', 'resposta']
    ordering = ('id',)
    list_filter = ['pergunta__questionario', 'pergunta__categoria', 'pergunta__objetiva']

    def get_pergunta(self, obj):
        return '{}...'.format(obj.pergunta.texto[:100])

    get_pergunta.short_description = 'Pergunta'

    def export_to_csv(self, request, queryset, processo):
        header = ['#', 'Servidor', 'Dimensão', 'Pergunta', 'Resposta']
        rows = [header]
        for obj in processo.iterate(queryset.select_related('pergunta', 'servidor')):
            row = [obj.pk, str(obj.servidor), obj.pergunta.categoria, obj.pergunta.texto, obj.resposta]
            rows.append(row)
        return rows


admin.site.register(Resposta, RespostaAdmin)
