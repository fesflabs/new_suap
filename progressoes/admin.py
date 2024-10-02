# -*- coding: utf-8 -*-
from django.contrib import admin
from django.utils.safestring import mark_safe

from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from djtools.templatetags.tags import icon
from djtools.utils import httprr
from progressoes.forms import ProcessoProgressaoAddForm, AvaliacaoModeloForm, ProcessoProgressaoEditForm, EstagioProbatorioAddForm, EstagioProbatorioEditForm
from progressoes.models import ProcessoProgressao, AvaliacaoModelo, AvaliacaoModeloCriterio


class AvaliacaoModeloAdmin(ModelAdminPlus):
    list_display = ('nome', 'tipo')
    search_fields = ('nome', 'itens_avaliados__descricao_questao')
    form = AvaliacaoModeloForm
    list_display_icons = True


admin.site.register(AvaliacaoModelo, AvaliacaoModeloAdmin)


class AvaliacaoModeloCriterioAdmin(ModelAdminPlus):
    list_display = ('descricao_questao', 'nota_minima', 'nota_maxima', 'passo_nota')
    list_display_icons = True


admin.site.register(AvaliacaoModeloCriterio, AvaliacaoModeloCriterioAdmin)


class ProcessoProgressaoAdmin(ModelAdminPlus):
    list_display = (
        'acoes',
        'avaliado',
        'tipo_processo',
        'data_inicio_contagem_progressao',
        'data_fim_contagem_progressao',
        'status_display',
        'avaliacoes_respondidas',
        'assinaturas_requeridas',
        'opcoes',
    )
    search_fields = (
        'avaliado__nome',
        'avaliado__matricula',
        'processoprogressaoperiodo__processoprogressaoavaliacao__avaliador__nome',
        'processoprogressaoperiodo__processoprogressaoavaliacao__avaliador__matricula',
    )
    list_display_icons = False
    list_filter = (CustomTabListFilter, 'tipo')
    show_count_on_tabs = True
    # FIELDSETS
    fieldset_progressao = (('', {'fields': ('avaliado', 'data_inicio_contagem_progressao', 'data_fim_contagem_progressao', 'padrao_anterior', 'padrao_novo')}),)
    fieldset_progressao_add = (('', {'fields': ('avaliado', 'data_inicio_contagem_progressao', 'padrao_anterior', 'padrao_novo')}),)
    fieldset_estagio_probatorio = (('', {'fields': ('avaliado', 'data_inicio_contagem_progressao', 'data_fim_contagem_progressao',)}),)
    fieldset_estagio_probatorio_add = (('', {'fields': ('avaliado', 'data_inicio_contagem_progressao',)}),)
    super_extra_fieldsets = (('SÓ SUPERUSUÁRIO', {'fields': ('processo_eletronico',)}),)

    def get_action_bar(self, request, remove_add_button=True):
        subitems = [
            dict(label='Progressão', url='/admin/progressoes/processoprogressao/add/?tipo=1'),
            dict(label='Estágio Probatório', url='/admin/progressoes/processoprogressao/add/?tipo=2'),
        ]
        item = dict(label='Adicionar Processo', css_class='success', subitems=subitems)
        return [item]

    def tipo_processo(self, obj):
        return obj.get_tipo_display()

    tipo_processo.short_description = 'Tipo de Processo'
    tipo_processo.admin_order_field = 'tipo'

    def get_list_filter(self, request):
        if request.user.has_perm('progressoes.pode_ver_todos_os_processos'):
            if 'avaliado__setor__uo' not in self.list_filter:
                self.list_filter += ('avaliado__setor__uo',)
        return super(ProcessoProgressaoAdmin, self).get_list_filter(request)

    def get_form(self, request, obj=None, **kwargs):
        if not obj:
            tipo = request.GET.get('tipo', None)
            if tipo:
                tipo = int(tipo)
            if tipo == ProcessoProgressao.TIPO_ESTAGIO_PROBATORIO:
                self.form = EstagioProbatorioAddForm
            else:
                self.form = ProcessoProgressaoAddForm
        else:
            if obj.is_tipo_estagio_probatorio:
                self.form = EstagioProbatorioEditForm
            else:
                self.form = ProcessoProgressaoEditForm
        return super(ProcessoProgressaoAdmin, self).get_form(request, obj, **kwargs)

    def get_fieldsets(self, request, obj=None):
        meus_fieldsets = ()
        if not obj:
            tipo = request.GET.get('tipo', None)
            if tipo:
                tipo = int(tipo)
            if tipo == ProcessoProgressao.TIPO_ESTAGIO_PROBATORIO:
                meus_fieldsets = self.fieldset_estagio_probatorio_add
            else:
                meus_fieldsets = self.fieldset_progressao_add
        else:
            if obj.is_tipo_estagio_probatorio:
                meus_fieldsets = self.fieldset_estagio_probatorio
            else:
                meus_fieldsets = self.fieldset_progressao
            # somente no opção de editar podemos ver este campo
            if request.user.is_superuser:
                meus_fieldsets += self.super_extra_fieldsets
        return meus_fieldsets

    def response_add(self, request, obj, post_url_continue=None):
        return httprr('/progressoes/editar_processo/{}/'.format(obj.id), message='Processo de progressão cadastrado com sucesso.')

    def response_change(self, request, obj):
        return httprr('/progressoes/editar_processo/{}/'.format(obj.id), message='Processo de progressão alterado com sucesso.')

    def acoes(self, obj):
        acoes = icon('view', '/progressoes/editar_processo/{}/'.format(obj.id))
        if obj.status != ProcessoProgressao.STATUS_FINALIZADO:
            acoes += icon('delete', '/admin/progressoes/processoprogressao/{}/delete'.format(obj.id), 'Excluir Processo', 'no-confirm')
        return mark_safe('{}'.format(acoes))

    acoes.short_description = 'Ações'

    def opcoes(self, obj):
        opcoes = ""
        if obj.status == ProcessoProgressao.STATUS_FINALIZADO:
            opcoes += "<a class='btn' href='/progressoes/imprimir_processo/{}/' " "title='Imprimir Processo'>Imprimir Processo</a>".format(obj.id)
        return mark_safe('{}'.format(opcoes))

    opcoes.short_description = 'Opções'

    def avaliacoes_respondidas(self, obj):
        avaliacoes = obj.obter_avaliacoes()
        if avaliacoes:
            avaliacoes_total = len(avaliacoes)
        else:
            avaliacoes_total = 0

        avaliacoes_respondidas = 0
        for avaliacao in avaliacoes:
            if avaliacao.is_avaliada:
                avaliacoes_respondidas += 1

        class_css = "status-error"
        if avaliacoes:
            class_css = "status-em-tramite"
        if avaliacoes_respondidas > 0 and avaliacoes_respondidas == avaliacoes_total:
            class_css = "status-finalizado"

        return mark_safe("<span class='status {} text-nowrap-normal'>{}/{}</span>".format(class_css, avaliacoes_respondidas, avaliacoes_total))

    avaliacoes_respondidas.short_description = 'Avaliações Respondidas'

    def assinaturas_requeridas(self, obj):
        avaliacoes = obj.obter_avaliacoes()
        avaliacoes_pendentes = 0
        assinaturas_realizadas = 0
        assinaturas_requeridas = 0
        class_css = "status-error"
        if avaliacoes:
            class_css = "status-em-tramite"
            for avaliacao in avaliacoes:
                assinaturas_situacao = avaliacao.assinaturas_realizadas_requeridas()
                assinaturas_realizadas += assinaturas_situacao[0]
                assinaturas_requeridas += assinaturas_situacao[1]
                if avaliacao.is_pendente:
                    avaliacoes_pendentes += 1

        if assinaturas_realizadas > 0 and assinaturas_realizadas == assinaturas_requeridas and avaliacoes_pendentes == 0:
            class_css = "status-finalizado"

        return mark_safe("<span class='status {} text-nowrap-normal'>{}/{}</span>".format(class_css, assinaturas_realizadas, assinaturas_requeridas))

    assinaturas_requeridas.short_description = 'Assinaturas'

    def get_queryset(self, request, manager=None, *args, **kwargs):
        qs = ModelAdminPlus.get_queryset(self, request, manager=manager, *args, **kwargs)
        if request.user.has_perm('progressoes.pode_ver_todos_os_processos'):
            pass
        elif request.user.has_perm('progressoes.pode_ver_apenas_processos_do_seu_campus'):
            campus_usuario_logado = request.user.get_profile().funcionario.setor.uo
            qs = qs.filter(avaliado__setor__uo__sigla=campus_usuario_logado.sigla)
        else:
            qs = qs.none()
        return qs

    def get_tabs(self, request):
        return ['tab_a_iniciar', 'tab_em_tramite', 'tab_finalizados', 'tab_any_data']

    def tab_a_iniciar(self, request, queryset):
        return queryset.filter(status=ProcessoProgressao.STATUS_A_INICIAR)

    tab_a_iniciar.short_description = 'A Iniciar'

    def tab_em_tramite(self, request, queryset):
        return queryset.filter(status=ProcessoProgressao.STATUS_EM_TRAMITE)

    tab_em_tramite.short_description = 'Em Trâmite'

    def tab_finalizados(self, request, queryset):
        return queryset.filter(status=ProcessoProgressao.STATUS_FINALIZADO)

    tab_finalizados.short_description = 'Finalizados'

    def status_display(self, obj):
        class_css = "status-error"  # padrao: status a iniciar
        if obj.status == ProcessoProgressao.STATUS_EM_TRAMITE:
            class_css = "status-em-tramite"
        if obj.status == ProcessoProgressao.STATUS_FINALIZADO:
            situacao_processo = obj.obter_situacao_final_processo()
            if situacao_processo == ProcessoProgressao.SITUACAO_FINAL_APROVADO:
                class_css = "status-finalizado"
            elif situacao_processo == ProcessoProgressao.SITUACAO_FINAL_APROVADO:
                class_css = "status-rejeitado"

        return mark_safe("<span class='status {} text-nowrap-normal'>{}</span>".format(class_css, obj.get_status_display()))

    status_display.admin_order_field = 'status'
    status_display.short_description = 'Situação'


admin.site.register(ProcessoProgressao, ProcessoProgressaoAdmin)
