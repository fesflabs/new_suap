# -*- coding: utf-8 -*-
import datetime

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils.safestring import mark_safe

from comum.utils import get_uo, formata_segundos
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter, DateRangeListFilter
from djtools.templatetags.tags import icon
from djtools.utils import httprr
from ponto.forms import (
    MaquinaForm,
    LiberacaoForm,
    AfastamentoForm,
    ObservacaoAdminForm,
    RecessoOpcaoForm,
    RecessoPeriodoCompensacaoAdminForm,
    RecessoDiaAdminForm,
    RecessoOpcaoOutroForm,
)
from ponto.models import (
    Maquina,
    Liberacao,
    Observacao,
    Afastamento,
    TipoAfastamento,
    Frequencia,
    AbonoChefia,
    HorarioCompensacao,
    RecessoOpcao,
    RecessoOpcaoEscolhida,
    RecessoPeriodoCompensacao,
    RecessoDia,
    MaquinaLog,
)


class MaquinaAdmin(ModelAdminPlus):
    form = MaquinaForm
    ordering = ['-id']
    search_fields = ['descricao', 'ip']
    list_display = ['ip', 'descricao', 'ativo', 'get_terminais', 'versao_terminal', 'observacao', 'ultimo_log']
    list_filter = ['ativo', 'cliente_ponto', 'cliente_chaves', 'cliente_cadastro_impressao_digital', 'cliente_refeitorio', 'uo']
    filter_horizontal = ('predios',)

    def get_terminais(self, obj):
        out = '<ul>'
        if obj.cliente_cadastro_impressao_digital:
            out += '<li>Cadastro</li>'
        if obj.cliente_chaves:
            out += '<li>Chaves</li>'
        if obj.cliente_ponto:
            out += '<li>Ponto</li>'
        if obj.cliente_refeitorio:
            out += '<li>Refeitório</li>'
        out += '</ul>'
        return mark_safe(out)

    get_terminais.short_description = 'Terminais'

    def get_queryset(self, request):
        qs = super(MaquinaAdmin, self).get_queryset(request)
        if request.user.is_superuser or request.user.groups.filter(name='Coordenador de TI sistêmico').exists():
            return qs

        qs = qs.filter(uo=get_uo(request.user))
        return qs


admin.site.register(Maquina, MaquinaAdmin)


class LiberacaoAdmin(ModelAdminPlus):
    form = LiberacaoForm
    date_hierarchy = 'data_inicio'
    list_filter = ['uo']
    search_fields = ['descricao']
    list_display = ['data_inicio', 'data_fim', 'uo', 'descricao', 'tipo']
    list_display_icons = True

    def get_queryset(self, request):
        queryset = super(LiberacaoAdmin, self).get_queryset(request)
        if request.user.is_superuser or request.user.has_perm('rh.eh_rh_sistemico'):
            return queryset
        else:
            user_logado = request.user.get_profile()
            if user_logado:
                uo_logado = get_uo(user_logado)
                queryset = queryset.filter(uo=uo_logado)
            else:
                queryset = Liberacao.objects.none()
        return queryset


admin.site.register(Liberacao, LiberacaoAdmin)


def restringir_observacoes(self, request):
    return admin.ModelAdmin.get_queryset(self, request).filter(vinculo=request.user.get_vinculo())


class ObservacaoAdmin(ModelAdminPlus):
    date_hierarchy = 'data'
    search_fields = ['descricao']
    list_display = ['vinculo', 'data', 'descricao']
    get_queryset = restringir_observacoes
    form = ObservacaoAdminForm
    list_display_icons = True

    def has_delete_permission(self, request, obj=None):
        is_superuser = request.user.is_superuser
        if obj:
            tem_abono = AbonoChefia.objects.filter(data=obj.data, vinculo_pessoa=obj.vinculo).exists()
            if tem_abono:
                return is_superuser  # se tem abono, permissao para excluir apenas super usuarios
        return super(ObservacaoAdmin, self).has_delete_permission(request, obj)  # se nao tem abono, retorno padrao


admin.site.register(Observacao, ObservacaoAdmin)


class AfastamentoAdmin(ModelAdminPlus):
    form = AfastamentoForm
    list_display = ['vinculo', 'tipo', 'descricao', 'data_ini', 'data_fim']
    list_filter = ['tipo']
    search_fields = ['descricao', 'vinculo__pessoa__nome']
    list_display_icons = True
    date_hierarchy = 'data_ini'


admin.site.register(Afastamento, AfastamentoAdmin)


class TipoAfastamentoAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display_icons = True


admin.site.register(TipoAfastamento, TipoAfastamentoAdmin)


class FrequenciaAdmin(ModelAdminPlus):
    list_display = ['id', 'maquina', 'vinculo', 'acao', 'horario', 'online']
    list_filter = ['horario', 'acao', 'online', 'maquina']
    search_fields = ['vinculo__pessoa__nome']
    ordering = ['-horario']
    date_hierarchy = 'horario'


admin.site.register(Frequencia, FrequenciaAdmin)


##########################################################################################
# COMPENSAÇÃO DE HORÁRIO
##########################################################################################
class HorarioCompensacaoAdmin(ModelAdminPlus):
    change_form_template = 'ponto/templates/admin/ponto/horariocompensacao/change_form.html'
    list_display = ['_opcoes', 'data_aplicacao', 'data_compensacao', '_ch_compensada', '_situacao']
    list_filter = (('data_aplicacao', DateRangeListFilter), ('data_compensacao', DateRangeListFilter), 'situacao')

    def _opcoes(self, obj):
        return icon('view', obj.get_absolute_url())

    _opcoes.short_description = 'Ações'

    def _ch_compensada(self, obj):
        return obj.ch_compensada.strftime('%H:%M:%S')

    _ch_compensada.short_description = 'Carga Horária Compensada'
    _ch_compensada.admin_order_field = 'ch_compensada'

    def _situacao(self, obj):
        status_css = "status-finalizado"
        if obj.situacao == HorarioCompensacao.SITUACAO_INVALIDO:
            status_css = "status-rejeitado"
        return mark_safe("<span class='status {} text-nowrap-normal'>{}</span>".format(status_css, obj.get_situacao_display()))

    _situacao.short_description = 'Situação'
    _situacao.admin_order_field = 'situacao'

    def get_queryset(self, request, manager=None, *args, **kwargs):
        qs = super(HorarioCompensacaoAdmin, self).get_queryset(request, manager, *args, **kwargs).order_by('data_aplicacao', '-data_compensacao')
        eu = request.user.get_profile().sub_instance()
        meus_informes = qs.filter(funcionario=eu)
        return meus_informes

    def get_form(self, request, obj=None, **kwargs):
        raise PermissionDenied

    def get_action_bar(self, request, remove_add_button=False):
        eu = request.user.get_profile().sub_instance()
        itens = [
            dict(url='/ponto/adicionar_compensacao/', label='Informar Compensação de Horário', css_class='success'),  # redefine o add
            dict(
                label='Remover Compensações',
                css_class='danger no-confirm',
                subitems=[
                    dict(label='Localizar Por Data do Débito', url='/ponto/remover_compensacoes/{}/' '?localizar_opcao=1'.format(eu.matricula)),
                    dict(label='Localizar Por Data da Compensação/Saldo', url='/ponto/remover_compensacoes/{}/' '?localizar_opcao=2'.format(eu.matricula)),
                    dict(label='Localizar Compensações em Duplicidade', url='/ponto/remover_compensacoes/{}/' '?localizar_opcao=3'.format(eu.matricula)),
                ],
            ),
        ]
        return itens + super(HorarioCompensacaoAdmin, self).get_action_bar(request, remove_add_button=True)


admin.site.register(HorarioCompensacao, HorarioCompensacaoAdmin)


class RecessoPeriodoCompensacaoInlines(admin.TabularInline):
    model = RecessoPeriodoCompensacao
    extra = 2
    form = RecessoPeriodoCompensacaoAdminForm


class RecessoDiaInlines(admin.TabularInline):
    model = RecessoDia
    extra = 10
    form = RecessoDiaAdminForm


class RecessoOpcaoAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ('tipo', 'descricao', '_situacao')
    list_filter = ('tipo', 'situacao')

    def _situacao(self, obj):
        if obj.situacao == RecessoOpcao.SITUACAO_FECHADO:
            situacao = '<span class="status status-finalizado">{}</span>'.format(obj.get_situacao_display())
        else:
            situacao = '<span class="status status-em-tramite">{}</span>'.format(obj.get_situacao_display())
            #
            if obj.is_aberto_para_escolhas_de_datas and not obj.is_no_periodo_para_escolhas_de_datas:
                situacao = '<span class="status status-error">' '{} ' '(o período de escolhas expirou)' '</span>'.format(obj.get_situacao_display())
        return mark_safe(situacao)

    _situacao.short_description = 'Situação'
    _situacao.admin_order_field = 'situacao'

    def response_add(self, request, obj, post_url_continue=None):
        return httprr('/ponto/abrir_opcao_recesso/{}/'.format(obj.id), 'Cadastrado com sucesso.')

    def response_change(self, request, obj):
        return httprr('/ponto/abrir_opcao_recesso/{}/'.format(obj.id), 'Alterado com sucesso.')

    def response_post_save_change(self, request, obj):
        return super(RecessoOpcaoAdmin, self).response_post_save_change(request, obj)

    def get_action_bar(self, request, remove_add_button=False):
        subitems = [dict(label='{}'.format(tipo[1]), url='/admin/ponto/recessoopcao/add/?tipo={}'.format(tipo[0])) for tipo in RecessoOpcao.TIPO_CHOICES]
        item = [dict(label='Adicionar', css_class='success', subitems=subitems)]
        return item + super(RecessoOpcaoAdmin, self).get_action_bar(request, remove_add_button=True)

    def get_form(self, request, obj=None, **kwargs):
        if obj:
            tipo = obj.tipo
        else:
            tipo = self._get_tipo(request)

        self.inlines = ()
        if tipo == RecessoOpcao.TIPO_NATAL_ANO_NOVO and obj is None:
            self.inlines = (RecessoDiaInlines, RecessoPeriodoCompensacaoInlines)

        self.form = RecessoOpcaoOutroForm
        if tipo == RecessoOpcao.TIPO_NATAL_ANO_NOVO:
            self.form = RecessoOpcaoForm

        return super(RecessoOpcaoAdmin, self).get_form(request, obj, **kwargs)

    def _get_tipo(self, request):
        try:
            tipo = int(request.GET.get('tipo'))
        except Exception:
            tipo = None

        if tipo not in [_tipo[0] for _tipo in RecessoOpcao.TIPO_CHOICES]:
            raise PermissionDenied

        return tipo

    def render_change_form(self, request, context, add=False, change=False, form_url='', obj=None):
        if obj and not obj.is_em_fase_de_cadastro:
            return httprr(
                '/ponto/abrir_opcao_recesso/{}/'.format(obj.id),
                message='A opção de compensação não está em fase de cadastro. Por favor, faça as edições desejadas por esta página.',
                tag='warning',
            )
        return super(RecessoOpcaoAdmin, self).render_change_form(request, context, add, change, form_url, obj)


admin.site.register(RecessoOpcao, RecessoOpcaoAdmin)


class RecessoOpcaoEscolhidaAdmin(ModelAdminPlus):
    list_filter = (CustomTabListFilter, 'validacao', 'recesso_opcao')

    def get_list_display(self, request):
        queryset_padrao = super(RecessoOpcaoEscolhidaAdmin, self).get_queryset(request)
        ha_recessos_do_setor = self.recessos_do_setor(request, queryset_padrao).exists()
        list_display = ['_opcoes', 'recesso_opcao', '_dias_efetivos_a_compensar', '_periodo_compensacao', '_total_carga_horaria_pendente', '_validacao', 'opcoes']
        if ha_recessos_do_setor:
            if not request.GET.get('tab') == 'meus_recessos':
                list_display.insert(1, 'funcionario')
        return list_display

    def _dias_efetivos_a_compensar(self, obj):
        if obj.is_aguardando:
            dias_efetivos_selecionados = [dia_escolhido.dia.data for dia_escolhido in obj.dias_escolhidos.all()]
        else:
            dias_efetivos_selecionados = obj.dias_efetivos_a_compensar()

        datas_html = ''

        if dias_efetivos_selecionados:
            datas_html += '<span class="text-nowrap-normal">'
            datas_html += ', '.join([data.strftime('%d/%m/%Y') for data in dias_efetivos_selecionados])
            datas_html += '</span>'
        else:
            datas_html = '-'

        return mark_safe(datas_html)

    _dias_efetivos_a_compensar.short_description = 'Dias Efetivos/Selecionados a Compensar'

    def _opcoes(self, obj):
        return icon('view', obj.get_absolute_url())

    _opcoes.short_description = 'Ações'

    def _periodo_compensacao(self, obj):
        return ', '.join([str(periodo) for periodo in obj.recesso_opcao.periodos_de_compensacao.all()])

    _periodo_compensacao.short_description = 'Período de Compensação'

    def _validacao(self, obj):
        status_css = "status-alert"  # aguardando
        if obj.validacao == RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO:
            status_css = "status-success"
        elif obj.validacao in [RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO, RecessoOpcaoEscolhida.VALIDACAO_NAO_AUTORIZADO_REMARCAR]:
            status_css = "status-error"
        return mark_safe("<span class='status {} text-nowrap-normal'>{}</span>".format(status_css, obj.get_validacao_display()))

    _validacao.short_description = 'Validação'
    _validacao.admin_order_field = 'validacao'

    def _total_carga_horaria_pendente(self, obj):
        eu = self.request.user.get_profile().sub_instance()
        if obj.funcionario == eu and obj.validacao == RecessoOpcaoEscolhida.VALIDACAO_AUTORIZADO:
            total = obj.totais_ch(carga_horaria_pendente=True)['total_carga_horaria_pendente']

            status_css = "true"
            if total > 0:
                status_css = "false"

            total = formata_segundos(total, '{h:02.0f}h ', '{m:02.0f}min ', '{s:02.0f}seg ', True)
            return mark_safe("<span class='{} text-nowrap-normal'>{}</span>".format(status_css, total))
        return "-"

    _total_carga_horaria_pendente.short_description = 'CH Pendente'

    def get_action_bar(self, request, remove_add_button=False):
        itens = [dict(url='/ponto/escolher_dia_de_recesso/', label='Escolher Dias', css_class='success')]  # redefine o add

        eu_sou_super_usuario_ou_rh = request.user.is_superuser or request.user.has_perm('rh.eh_rh_sistemico')
        if eu_sou_super_usuario_ou_rh:
            itens += [dict(url='/ponto/localizar_acompanhamentos/', label='Editar Acompanhamentos')]

        return itens + super(RecessoOpcaoEscolhidaAdmin, self).get_action_bar(request, remove_add_button=True)

    def get_form(self, request, obj=None, **kwargs):
        # não é permitido adicionar/alterar pelo admin
        # há um "add" específico '/ponto/escolher_dia_de_recesso/'
        raise PermissionDenied

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        # não é permitido excluir pelo admin
        return False

    def get_queryset(self, request, manager=None, *args, **kwargs):
        qs = super(RecessoOpcaoEscolhidaAdmin, self).get_queryset(request, manager, *args, **kwargs)
        eu = request.user.get_profile().sub_instance()
        hoje = datetime.date.today()
        return qs.filter(funcionario=eu) | qs.filter(validador=eu) | qs.filter(funcionario__setor__in=eu.historico_funcao(hoje, hoje).values_list('setor_suap', flat=True))

    def get_tabs(self, request):
        queryset_padrao = super(RecessoOpcaoEscolhidaAdmin, self).get_queryset(request)
        ha_recessos_do_setor = self.recessos_do_setor(request, queryset_padrao).exists()
        if ha_recessos_do_setor:
            return ['meus_recessos', 'recessos_do_setor']
        return []

    def meus_recessos(self, request, queryset):
        eu = request.user.get_profile().sub_instance()
        return queryset.filter(funcionario=eu)

    meus_recessos.short_description = 'Minhas Compensações'

    def recessos_do_setor(self, request, queryset):
        eu = request.user.get_profile().sub_instance()
        hoje = datetime.date.today()

        queryset = queryset.filter(
            # funcionários que eu já validei / vou validar
            validador=eu
        ) | queryset.filter(
            # meus subordinados hoje
            funcionario__setor__in=eu.historico_funcao(hoje, hoje).values_list('setor_suap', flat=True)
        )

        return queryset

    recessos_do_setor.short_description = 'Compensações do Setor'

    def opcoes(self, obj):
        relacionamento = self.request.user.get_relacionamento()
        usuario_logado_is_chefe = obj.is_chefe(relacionamento)

        if obj.is_aguardando and usuario_logado_is_chefe and (obj.recesso_opcao.is_no_periodo_para_escolhas_de_datas or obj.pode_validar_apos_prazo):
            return mark_safe('<a href="/ponto/validar_recesso_escolhido/{}/" class="btn success popup">Validar</a>'.format(obj.id))
        return "-"

    opcoes.short_description = 'Opções'
    opcoes.allow_tags = True


admin.site.register(RecessoOpcaoEscolhida, RecessoOpcaoEscolhidaAdmin)


class MaquinaLogAdmin(ModelAdminPlus):
    list_filter = ('maquina__uo', 'horario', 'status')
    ordering = ['-horario']
    list_display_icons = True
    list_display = ('maquina', 'operacao', 'horario', 'status')


admin.site.register(MaquinaLog, MaquinaLogAdmin)
