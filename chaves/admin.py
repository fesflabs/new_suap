# -*- coding: utf-8 -*-
from datetime import datetime

from django.contrib import admin
from django.utils.safestring import mark_safe

from chaves.forms import ChaveForm, MovimentacaoAdminForm
from chaves.models import Chave, Movimentacao
from comum.utils import get_uo, somar_data
from djtools.contrib.admin import ModelAdminPlus


class ChaveAdmin(ModelAdminPlus):
    form = ChaveForm
    list_display = ('identificacao', 'get_campus', 'get_predio', 'get_sala', 'get_pessoas_permitidas', 'ativa', 'disponivel', 'get_movimentacao')
    list_display_icons = True
    list_filter = ('ativa', 'disponivel', 'sala__predio__uo', 'sala__predio')
    list_per_page = 25
    search_fields = ('identificacao', 'sala__nome', 'sala__predio__nome')

    fieldsets = ((None, {'fields': ('identificacao', 'sala', 'ativa', 'pessoas')}),)
    avoid_short_search = False

    def get_movimentacao(self, obj):
        data_termino = datetime.now()
        data_inicio = somar_data(data_termino, -7)
        return mark_safe(
            '''
        <ul class="action-bar">
            <li><a href="/chaves/movimentacao_chave/?data_inicio={}&data_termino={}&chave={:d}" class="btn default">Ver Movimentação</a></li>
        </ul>
            '''.format(
                datetime.strftime(data_inicio, '%d/%m/%Y'), datetime.strftime(data_termino, '%d/%m/%Y'), obj.id
            )
        )

    get_movimentacao.short_description = 'Opções'

    def get_campus(self, obj):
        return '{}'.format(obj.sala.predio.uo)

    get_campus.short_description = 'Campus'
    get_campus.admin_order_field = 'sala__predio__uo'

    def get_queryset(self, request):
        qs = super(ChaveAdmin, self).get_queryset(request)
        if request.user.is_superuser or request.user.has_perm('chaves.poder_ver_todas'):
            return qs

        return qs.filter(sala__predio__uo=get_uo(request.user))

    def get_predio(self, obj):
        return mark_safe('<strong><a href="/admin/comum/predio/{:d}/">{}</a></strong>'.format(obj.sala.predio.pk, obj.sala.predio))

    get_predio.short_description = 'Prédio'
    get_predio.admin_order_field = 'sala__predio'

    def get_sala(self, obj):
        return mark_safe(
            '''
        <strong><a href="/admin/comum/sala/{:d}/">{}</a></strong><br/>
        <span class="cinza">{}</span>
        '''.format(
                obj.sala.pk, obj.sala, '{uo} &rarr; {predio} &rarr; {sala}'.format(uo=obj.sala.predio.uo, predio=obj.sala.predio, sala=obj.sala)
            )
        )

    get_sala.short_description = 'Sala'
    get_sala.admin_order_field = 'sala'

    def get_pessoas_permitidas(self, obj):
        out = ['<ol>']
        for i in obj.pessoas.all():
            out.append('<li>{}</li>'.format(i.nome))
        out.append('</ol>')
        return mark_safe(''.join(out))

    get_pessoas_permitidas.short_description = 'Pessoas Permitidas'

    def get_action_bar(self, request):
        items = super(ChaveAdmin, self).get_action_bar(request)
        url_setor = '/chaves/associar_setor_a_chave/'
        items.append(dict(url=url_setor, label='Associar Setor', css_class='primary'))
        url_copiar_usuarios = '/chaves/copiar_usuarios/'
        items.append(dict(url=url_copiar_usuarios, label='Copiar Pessoas entre Chaves', css_class='primary'))
        return items


admin.site.register(Chave, ChaveAdmin)


class MovimentacaoAdmin(ModelAdminPlus):
    list_display = ('chave', 'data_emprestimo', 'pessoa_emprestimo', 'data_devolucao', 'pessoa_devolucao')
    list_filter = ('chave', 'data_emprestimo', 'data_devolucao')

    form = MovimentacaoAdminForm

    def get_queryset(self, request):
        qs = super(MovimentacaoAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return qs
        return qs.filter(chave__sala__predio__uo=get_uo(request.user))


admin.site.register(Movimentacao, MovimentacaoAdmin)
