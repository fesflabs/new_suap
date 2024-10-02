from django.contrib import admin
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe

from almoxarifado.forms import EmpenhoPermanenteForm
from comum.utils import get_uo
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from djtools.templatetags.filters import in_group, format_money
from patrimonio.forms import CautelaForm, CautelaInventarioForm, BaixaForm, ConferenciaForm, PlanoContasForm, CategoriaMaterialForm
from patrimonio.models import (
    CategoriaMaterialPermanente,
    ConferenciaItem,
    Inventario,
    Cautela,
    InventarioRotulo,
    Baixa,
    InventarioCategoria,
    EmpenhoPermanente,
    CautelaInventario,
    Requisicao,
    InventarioTipoUsoPessoal,
    RequisicaoInventarioUsoPessoal,
    ConferenciaSala,
    PlanoContas,
)
from rh.models import Servidor
from djtools.templatetags.tags import icon


class InventarioTipoUsoPessoalAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('descricao', 'requisicao_periodo_inicio', 'requisicao_periodo_fim')


admin.site.register(InventarioTipoUsoPessoal, InventarioTipoUsoPessoalAdmin)


class RequisicaoInventarioUsoPessoalAdmin(ModelAdminPlus):
    search_fields = ('vinculo__pessoa__nome', 'vinculo__pessoa__pessoafisica__cpf', 'vinculo__user__username')
    list_display = ('get_nome', 'get_cpf', 'get_email', 'get_email_secundario', 'get_uo', 'tipo_uso_pessoal', 'horario', 'cadastrado', 'indicado', 'atendido')
    list_filter = ('vinculo__setor__uo', 'tipo_uso_pessoal__descricao', 'cadastrado', 'indicado')
    readonly_fields = ('vinculo', 'tipo_uso_pessoal')
    list_display_icons = True
    export_to_xls = True

    def get_nome(self, obj):
        return mark_safe('<a href="/rh/servidor/{}/">{}</a>'.format(obj.vinculo.relacionamento.matricula, obj.vinculo.pessoa.nome))

    get_nome.short_description = 'Nome'
    get_nome.admin_order_field = 'vinculo__pessoa__nome'

    def get_cpf(self, obj):
        return obj.vinculo.pessoa.pessoafisica.cpf.replace('.', '').replace('-', '')

    get_cpf.short_description = 'CPF'

    def get_email(self, obj):
        return obj.vinculo.pessoa.email

    get_email.short_description = 'E-mail'

    def get_email_secundario(self, obj):
        return obj.vinculo.pessoa.email_secundario

    get_email_secundario.short_description = 'E-mail Secundário'

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Nome', 'CPF', 'Matrícula', 'E-mail Institucional', 'E-mail Secundário', 'Tipo Uso Pessoal', 'Data Cadastro', 'Campus']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            row = [
                idx + 1,
                obj.vinculo.pessoa.nome,
                obj.vinculo.pessoa.pessoafisica.cpf,
                obj.vinculo.relacionamento.matricula,
                obj.vinculo.pessoa.email,
                obj.vinculo.pessoa.email_secundario,
                obj.tipo_uso_pessoal.descricao,
                obj.horario,
                obj.vinculo.setor.uo if obj.vinculo.setor else None,
            ]
            rows.append(row)
        return rows


admin.site.register(RequisicaoInventarioUsoPessoal, RequisicaoInventarioUsoPessoalAdmin)


class CategoriaMaterialPermanenteAdmin(ModelAdminPlus):
    form = CategoriaMaterialForm
    search_fields = ('nome', 'codigo')
    list_display = ('codigo', 'nome', 'plano_contas', 'vida_util_em_anos', 'percentual_residual')
    ordering = ('codigo',)
    list_display_icons = True

    def get_fieldsets(self, request, obj=None):
        if in_group(request.user, 'Contador de Patrimônio Sistêmico'):
            return super().get_fieldsets(request, obj)
        return [(None, {'fields': ('codigo', 'nome', 'percentual_residual', 'vida_util_em_anos')})]


admin.site.register(CategoriaMaterialPermanente, CategoriaMaterialPermanenteAdmin)


class InventarioAdmin(ModelAdminPlus):
    search_fields = ('numero',)
    list_display = ('get_acoes', 'numero', 'status', 'get_carga_atual', 'get_descricao')
    list_display_links = None

    list_per_page = 50
    ordering = ('-numero',)

    def get_acoes(self, obj):
        texto = icon('view', '/patrimonio/inventario/{:d}/'.format(obj.id))
        texto = texto + icon('edit', '/patrimonio/inventario_editar/{:d}/'.format(obj.id))
        if self.request.user.is_superuser:
            texto = texto + icon('delete', '/admin/patrimonio/inventario/{:d}/delete/'.format(obj.id))
        texto = texto + '</ul>'

        return mark_safe(texto)

    get_acoes.short_description = 'Ações'


admin.site.register(Inventario, InventarioAdmin)


class InventarioRotuloAdmin(ModelAdminPlus):
    list_display = ['id', 'nome', 'descricao', 'unidade_organizacional']
    search_fields = ['nome', 'descricao']


admin.site.register(InventarioRotulo, InventarioRotuloAdmin)


class InventarioCategoriaAdmin(ModelAdminPlus):
    pass


admin.site.register(InventarioCategoria, InventarioCategoriaAdmin)


class EmpenhoPermanenteAdmin(ModelAdminPlus):
    form = EmpenhoPermanenteForm

    def response_change(self, request, obj):
        self.message_user(request, 'Item alterado com sucesso')
        return HttpResponseRedirect(obj.empenho.get_absolute_url())


admin.site.register(EmpenhoPermanente, EmpenhoPermanenteAdmin)


class BaixaAdmin(ModelAdminPlus):
    form = BaixaForm
    search_fields = ('numero', 'observacao', 'processo__numero_processo', 'movimentopatrim__inventario__numero')
    list_filter = ('tipo', 'uo')
    list_display = ('id', 'numero', 'tipo', 'data', 'processo', 'uo', 'observacao', 'get_valor')
    list_display_icons = True
    date_hierarchy = 'data'

    def has_change_permission(self, request, obj=None):
        # Liberar acesso apenas à listagem, não à edição.
        if obj:
            return False
        return super().has_change_permission(request, obj)

    def get_valor(self, obj):
        return format_money(obj.get_valor())

    get_valor.short_description = 'Valor'

    def response_change(self, request, obj):
        self.message_user(request, 'Baixa editada com sucesso.')
        return HttpResponseRedirect(obj.get_absolute_url())

    def response_add(self, request, obj):
        self.message_user(request, 'Baixa adicionada com sucesso.')
        return HttpResponseRedirect(obj.get_absolute_url())


admin.site.register(Baixa, BaixaAdmin)


class CautelaAdmin(ModelAdminPlus):
    form = CautelaForm
    list_display = ('get_link', 'responsavel', 'descricao', 'get_data_inicio', 'get_data_fim', 'detalhar')
    search_fields = ('responsavel', 'descricao')

    def get_link(self, obj):
        return mark_safe('<a href="{}">{}</a>'.format(obj.get_absolute_url(), obj.id))

    get_link.short_description = 'Cautela'

    def response_change(self, request, obj):
        self.message_user(request, 'Cautela editada com sucesso')
        return HttpResponseRedirect(obj.get_absolute_url())

    def response_add(self, request, obj):
        self.message_user(request, 'Cautela adicionada com sucesso')
        return HttpResponseRedirect(obj.get_absolute_url())

    def detalhar(self, obj):
        return mark_safe('<ul class="action-bar"><li><a class="btn" href="/patrimonio/tela_cautela_detalhe/%s">Detalhar Cautela</a></li></ul>' % (obj.pk))

    detalhar.short_description = 'Opções'

    def get_data_inicio(self, obj):
        return obj.get_data_inicio()

    get_data_inicio.short_description = 'Data Inicial'
    get_data_inicio.admin_order_field = 'data_inicio'

    def get_data_fim(self, obj):
        return obj.get_data_fim()

    get_data_fim.short_description = 'Data Final'


admin.site.register(Cautela, CautelaAdmin)


class CautelaInventarioAdmin(ModelAdminPlus):
    form = CautelaInventarioForm

    def response_change(self, request, obj):
        self.message_user(request, 'Item alterado com sucesso')
        return HttpResponseRedirect(obj.cautela.get_absolute_url())


admin.site.register(CautelaInventario, CautelaInventarioAdmin)


def restringir_requisicoes(self, request):
    qs = Requisicao.objects.filter(Q(vinculo_origem__setor__uo=get_uo(request.user)) | Q(vinculo_destino__setor__uo=get_uo(request.user)) | Q(usuario_requisicao=request.user))
    return qs


class ConferenciaAdmin(ModelAdminPlus):
    form = ConferenciaForm
    list_display = ('sala', 'responsavel', 'dh_criacao', 'get_opcoes')
    list_filter = ('sala__predio__uo',)
    list_display_icons = True
    date_hierarchy = 'dh_criacao'

    def get_opcoes(self, obj):
        return mark_safe(
            '<ul class="action-bar">'
            '<li><a class="btn success popup" data-height="500" href="/patrimonio/autorizar_coletor/%s/">Autorizar Coletor</a></li>'
            '<li><a class="btn default" href="/patrimonio/imprimir_conferencia/%s/">Detalhes da Conferência</a></li>'
            '</ul>' % (obj.pk, obj.pk)
        )

    get_opcoes.short_description = 'Opções'


admin.site.register(ConferenciaSala, ConferenciaAdmin)


class ConferenciaItemAdmin(ModelAdminPlus):
    list_display = ('get_inventario', 'get_descricao_inventario', 'get_estado_conservacao_inventario', 'get_sala_conferencia', 'dh_coleta')
    list_filter = ('conferencia__sala__predio__uo',)
    list_display_icons = True
    date_hierarchy = 'dh_coleta'
    export_to_xls = True

    def has_add_permission(self, request, obj=None):
        return False

    def has_view_permission(self, request, obj=None):
        return True

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_inventario(self, obj):
        return mark_safe(f'<a href="{obj.inventario.get_absolute_url()}">{obj.inventario.numero}</a>')

    get_inventario.short_description = 'Inventário'
    get_inventario.admin_order_field = 'inventario__numero'

    def get_descricao_inventario(self, obj):
        return obj.inventario.get_descricao()

    get_descricao_inventario.short_description = 'Descrição'
    get_descricao_inventario.admin_order_field = 'inventario__descricao'

    def get_estado_conservacao_inventario(self, obj):
        return obj.inventario.estado_conservacao

    get_estado_conservacao_inventario.short_description = 'Estado de Conservação'
    get_estado_conservacao_inventario.admin_order_field = 'inventario__estado_conservacao'

    def get_sala_conferencia(self, obj):
        return obj.conferencia.sala

    get_sala_conferencia.short_description = 'Sala Conferência'
    get_sala_conferencia.admin_order_field = 'conferencia__sala'


admin.site.register(ConferenciaItem, ConferenciaItemAdmin)


class RequisicaoAdmin(ModelAdminPlus):
    list_display = ('get_numero', 'vinculo_origem', 'vinculo_destino', 'requisitante', 'get_tipo', 'get_data_requisicao', 'get_data_aceite', 'get_status')
    list_display_icons = True
    list_per_page = 20
    list_filter = (CustomTabListFilter, 'campus_origem', 'campus_destino', 'tipo', 'status')
    search_fields = ('id', 'vinculo_origem__pessoa__nome', 'vinculo_destino__pessoa__nome')
    show_count_on_tabs = True

    def get_action_bar(self, request):
        items = super().get_action_bar(request)
        if Servidor.objects.filter(pk=request.user.get_profile().pk).exists():
            items.append(dict(url='/patrimonio/requisitar_transferencia/', label='Adicionar Nova Requisição', css_class='success'))
        return items

    def get_numero(self, obj):
        return obj.id

    get_numero.short_description = 'Número'

    def get_tabs(self, request):
        return ['tab_enviadas', 'tab_recebidas', 'tab_aguardando_aprovacao_servidor', 'tab_aguardando_informacao_pa_origem', 'tab_aguardando_informacao_pa_destino']

    def get_queryset(self, request, *args, **kwargs):
        if in_group(self.request.user, 'Coordenador de Patrimônio Sistêmico'):
            return Requisicao.objects.all()
        return Requisicao.restringir_queryset(super().get_queryset(request, *args, **kwargs), request.user)

    def tab_enviadas(self, request, queryset):
        return queryset.filter(vinculo_origem__user=request.user)

    tab_enviadas.short_description = 'Enviadas'

    def tab_recebidas(self, request, queryset):
        return queryset.filter(vinculo_destino__user=request.user)

    tab_recebidas.short_description = 'Recebidas'

    def tab_aguardando_aprovacao_servidor(self, request, queryset):
        return queryset.filter(status=Requisicao.STATUS_AGUARDANDO_APROVACAO_SERVIDOR_DESTINO, vinculo_destino__user=request.user)

    tab_aguardando_aprovacao_servidor.short_description = 'Aguardando Aprovação do Servidor'

    def tab_aguardando_informacao_pa_origem(self, request, queryset):
        if in_group(self.request.user, 'Coordenador de Patrimônio Sistêmico, Contador de Patrimônio Sistêmico'):
            return queryset.filter(status=Requisicao.STATUS_DEFERIDA_AGUARDANDO_INFORMACAO_PA_ORIGEM)
        return queryset.filter(status=Requisicao.STATUS_DEFERIDA_AGUARDANDO_INFORMACAO_PA_ORIGEM, campus_origem=get_uo(request.user))

    tab_aguardando_informacao_pa_origem.short_description = 'Aguardando PA Campus Origem'

    def tab_aguardando_informacao_pa_destino(self, request, queryset):
        if in_group(self.request.user, 'Coordenador de Patrimônio Sistêmico, Contador de Patrimônio Sistêmico'):
            return queryset.filter(status=Requisicao.STATUS_DEFERIDA_AGUARDANDO_INFORMACAO_PA_DESTINO)
        return queryset.filter(status=Requisicao.STATUS_DEFERIDA_AGUARDANDO_INFORMACAO_PA_DESTINO, campus_destino=get_uo(request.user))

    tab_aguardando_informacao_pa_destino.short_description = 'Aguardando PA Campus Destino'

    def has_add_permission(self, request):
        # Evitar uso para super usuários, já que nenhum grupo tem a permissão add_requisicao.
        return False

    def has_change_permission(self, request, obj=None):
        # Liberar acesso apenas à listagem, não à edição.
        if obj:
            return False
        return super().has_change_permission(request, obj)

    def get_status(self, obj):
        return mark_safe(obj.get_status())

    get_status.admin_order_field = 'status'
    get_status.short_description = 'Situação'

    def get_tipo(self, obj):
        return mark_safe(obj.get_tipo_display())

    get_tipo.admin_order_field = 'tipo'
    get_tipo.short_description = 'Tipo'

    def get_data_requisicao(self, obj):
        try:
            retorno = obj.requisicaohistorico_set.get(status=Requisicao.STATUS_AGUARDANDO_APROVACAO_SERVIDOR_DESTINO).alterado_em
        except Exception:
            retorno = obj.requisicaohistorico_set.get(status=Requisicao.STATUS_DEFERIDA).alterado_em
        return mark_safe(retorno)

    get_data_requisicao.short_description = 'Data da Requisição'

    def get_data_aceite(self, obj):
        retorno = obj.requisicaohistorico_set.get(status=Requisicao.STATUS_DEFERIDA_AGUARDANDO_INFORMACAO_PA_ORIGEM).alterado_em
        if obj.tipo == Requisicao.TIPO_MESMO_CAMPI:
            retorno = obj.requisicaohistorico_set.get(status=Requisicao.STATUS_DEFERIDA).alterado_em
        return mark_safe(retorno)

    get_data_aceite.short_description = 'Data do Aceite'


admin.site.register(Requisicao, RequisicaoAdmin)


class PlanoContasAdmin(ModelAdminPlus):
    form = PlanoContasForm
    search_fields = ('codigo', 'descricao')
    list_display = ('codigo', 'descricao', 'ativo', 'data_desativacao')
    ordering = ('codigo',)
    list_display_icons = True


admin.site.register(PlanoContas, PlanoContasAdmin)
