# -*- coding: utf-8 -*-

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils.safestring import mark_safe

from comum.models import Ano
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter, DateRangeListFilter
from djtools.templatetags.tags import icon
from djtools.utils import httprr
from rsc.forms import ProcessoAvaliadorForm
from rsc.models import Unidade, Diretriz, TipoRsc, Criterio, ProcessoRSC, ProcessoAvaliador, ValidacaoCPPD, ParametroPagamento, Avaliacao


class AvaliacaoAdmin(ModelAdminPlus):
    pass


admin.site.register(Avaliacao, AvaliacaoAdmin)


class UnidadeAdmin(ModelAdminPlus):
    list_display = ('nome', 'sigla')


admin.site.register(Unidade, UnidadeAdmin)


class DiretrizAdmin(ModelAdminPlus):
    list_filter = ('tipo_rsc',)
    list_display = ('tipo_rsc', 'nome', 'descricao', 'peso', 'teto')


admin.site.register(Diretriz, DiretrizAdmin)


class TipoRscAdmin(ModelAdminPlus):
    list_display = ('nome', 'categoria')


admin.site.register(TipoRsc, TipoRscAdmin)


class CriterioAdmin(ModelAdminPlus):
    list_filter = ('diretriz', 'unidade', 'status')
    list_display = ('diretriz', 'numero', 'nome', 'fator', 'teto', 'unidade', 'status')


admin.site.register(Criterio, CriterioAdmin)


class ProcessoRSCAdmin(ModelAdminPlus):
    list_display = (
        'opcoes',
        'servidor',
        'tipo_rsc',
        'get_numero',
        'get_cpf',
        'get_data_protocolo',
        'pontuacao_validada_com_corte',
        'pontuacao_pretendida',
        'get_validador',
        'status_estilizado',
        'botao_imprimir',
        'get_acoes',
    )
    list_display_icons = False
    list_filter = (CustomTabListFilter,)
    show_count_on_tabs = True
    search_fields = ('servidor__matricula', 'servidor__nome')
    export_to_xls = True

    def get_list_display(self, request):
        default_list_display = super(ProcessoRSCAdmin, self).get_list_display(request)
        if request.GET.get('tab') == 'tab_processos_finalizados':
            coluna_pagamento = ('get_situacao_pagamento',)
            nova_list_display = default_list_display + coluna_pagamento
            return nova_list_display
        return default_list_display

    def get_situacao_pagamento(self, obj):
        avaliacoes = obj.avaliacao_set.filter(status__in=[Avaliacao.DEFERIDA, Avaliacao.INDEFERIDA])
        qtd_nao_pagas = avaliacoes.filter(avaliacao_paga=False).count()
        if qtd_nao_pagas == 0:
            situacao = 'Todas as Avaliações foram pagas.'
            class_css = 'status-success'
        else:
            qtd_pagas = avaliacoes.filter(avaliacao_paga=True).count()
            situacao = f'''<dl>
            <dt>Avaliações Pagas:</dt><dd> {qtd_pagas}</dd>
            <dt>Avaliações Não Pagas:</dt><dd>{qtd_nao_pagas}</dd>
            </dl>'''
            class_css = 'status-info'
        return mark_safe(f'<span class="status {class_css} text-nowrap-normal">{situacao}</span>')

    get_situacao_pagamento.short_description = 'Situação dos Pagamentos'

    def get_numero(self, obj):
        processo = obj.processo_eletronico or obj.protocolo
        return mark_safe(f'<a href="{processo.get_absolute_url()}" class="popup">{processo}</a>') if processo else ''

    get_numero.admin_order_field = 'protocolo__numero_processo'
    get_numero.short_description = 'Número do Processo'

    def get_cpf(self, obj):
        return obj.servidor.cpf if obj.servidor else ''

    get_cpf.short_description = 'CPF'

    def get_data_protocolo(self, obj):
        return mark_safe(obj.protocolo.data_cadastro) if obj.protocolo else ''

    get_data_protocolo.admin_order_field = 'protocolo__data_cadastro'
    get_data_protocolo.short_description = 'Data Protocolo'

    def get_validador(self, obj):
        validacao = ValidacaoCPPD.objects.filter(processo=obj).first()
        return getattr(validacao, 'validador', '(Nenhum)')

    get_validador.admin_order_field = 'validacaocppd__validador'
    get_validador.short_description = 'Validador Responsável'

    def get_tabs(self, request):
        result = ['tab_meus_processos']
        if request.user.has_perm('rsc.pode_validar_processorsc'):
            result.append('tab_processos_rejeitados')
            result.append('tab_processos_pendentes')
            result.append('tab_processos_validados')
            result.append('tab_processos_em_avaliacao')
            result.append('tab_aguardando_ciencia')
            result.append('tab_processos_ciente_resultado')
            result.append('tab_processos_finalizados')
            result.append('tab_processos_finalizados_aposentados')
            result.append('tab_processos_analisados_aposentados')
        return result

    '''
    Aba que mostra apenas os processos criados por mim
    '''

    def tab_meus_processos(self, request, queryset):
        return queryset.filter(servidor__vinculo__user=request.user)

    tab_meus_processos.short_description = 'Meus Processos'

    '''
    Aba que mostra os processos rejeitados 
    '''

    def tab_processos_rejeitados(self, request, queryset):
        if not request.user.has_perm('rsc.pode_validar_processorsc'):
            queryset = queryset.filter(servidor__vinculo__user=request.user)
        return queryset.filter(status__in=[ProcessoRSC.STATUS_REJEITADO]).order_by('-id')

    tab_processos_rejeitados.short_description = 'Processos Rejeitados'

    '''
    Aba que mostra os processos que necessitam de atenção da CPPD (processos para validação, por exemplo)
    '''

    def tab_processos_pendentes(self, request, queryset):
        if not request.user.has_perm('rsc.pode_validar_processorsc'):
            queryset = queryset.filter(servidor__vinculo__user=request.user)
        return queryset.filter(status__in=[ProcessoRSC.STATUS_AGUARDANDO_VALIDACAO_CPPD, ProcessoRSC.STATUS_AGUARDANDO_NOVA_VALIDACAO]).order_by('-id')

    tab_processos_pendentes.short_description = 'Processos Pendentes'

    '''
    Aba que mostra os processos que os avaliados deram ciência do resultado (avaliação finalizada)
    '''

    def tab_processos_ciente_resultado(self, request, queryset):
        return queryset.filter(status=ProcessoRSC.STATUS_CIENTE_DO_RESULTADO)

    tab_processos_ciente_resultado.short_description = 'Processos Cientes de Resultado'

    '''
    Aba que mostra os processos que estão aguardando a ciência do avaliado
    '''

    def tab_aguardando_ciencia(self, request, queryset):
        return queryset.filter(status=ProcessoRSC.STATUS_AGUARDANDO_CIENCIA)

    tab_aguardando_ciencia.short_description = 'Aguardando Ciência'

    '''
    Aba que mostra os processos finalizados
    '''

    def tab_processos_finalizados(self, request, queryset):
        return queryset.filter(status__in=[ProcessoRSC.STATUS_APROVADO, ProcessoRSC.STATUS_REPROVADO], tipo_processo__in=[ProcessoRSC.TIPO_PROCESSO_GERAL])

    tab_processos_finalizados.short_description = 'Processos Finalizados (geral)'

    '''
    Aba que mostra os processos já validados pela CPPD e que estão esperando a atribuição de avaliadores
    '''

    def tab_processos_validados(self, request, queryset):
        return queryset.filter(status=ProcessoRSC.STATUS_AGUARDANDO_AVALIADORES)

    tab_processos_validados.short_description = 'Processos Validados'

    '''
    Aba que mostra os processos que já tem avaliadores selecionados ou que já estão em avaliação
    Aba está renomeada para "Processos em análise" para melhor entendimento
    '''

    def tab_processos_em_avaliacao(self, request, queryset):
        return queryset.filter(status__in=[ProcessoRSC.STATUS_EM_AVALIACAO, ProcessoRSC.STATUS_AGUARDANDO_ACEITE_AVALIADOR])

    tab_processos_em_avaliacao.short_description = 'Processos em Análise'

    '''
    Aba que mostra os processos analisados dos aposentados
    '''

    def tab_processos_analisados_aposentados(self, request, queryset):
        return queryset.filter(status=ProcessoRSC.STATUS_ANALISADO)

    tab_processos_analisados_aposentados.short_description = 'Processos Analisados (aposentados)'

    '''
     Aba que mostra os processos analisados dos aposentados
    '''

    def tab_processos_finalizados_aposentados(self, request, queryset):
        return queryset.filter(status__in=[ProcessoRSC.STATUS_APROVADO, ProcessoRSC.STATUS_REPROVADO], tipo_processo__in=[ProcessoRSC.TIPO_PROCESSO_APOSENTADO])

    tab_processos_finalizados_aposentados.short_description = 'Processos Finalizados (aposentados)'

    def status_estilizado(self, obj):
        return mark_safe(obj.status_estilizado)

    status_estilizado.admin_order_field = 'status'
    status_estilizado.short_description = 'Situação'

    def get_queryset(self, request):
        queryset = super(ProcessoRSCAdmin, self).get_queryset(request)

        if request.user.is_superuser:
            return queryset

        '''
        se a pessoa não tiver a permissão "pode_validar_processorsc" filtra apenas os próprios processos
        pois não é um membro da CPPD
        '''
        if not request.user.has_perm('rsc.pode_validar_processorsc') and not request.user.has_perm('rsc.pode_ver_relatorio_rsc'):
            queryset = queryset.filter(servidor_id=request.user.get_profile().id)

        '''
        se for um membro da CPPD (tiver a permissão pode_validar_processorsc) irá filtrar apenas os processos que não estejam
        com o avaliado e também trará os próprios processos
        '''
        if request.user.has_perm('rsc.pode_validar_processorsc') or request.user.has_perm('rsc.pode_ver_relatorio_rsc'):
            queryset = queryset.exclude(status__in=[ProcessoRSC.STATUS_AGUARDANDO_AJUSTES_USUARIO, ProcessoRSC.STATUS_AGUARDANDO_ENVIO_CPPD]) | queryset.filter(
                servidor_id=request.user.get_relacionamento().id
            )

        if (
            not request.user.has_perm('rsc.pode_avaliar_processorsc')
            and not request.user.has_perm('rsc.pode_validar_processorsc')
            and not request.user.has_perm('rsc.pode_ver_relatorio_rsc')
        ):
            queryset = queryset.filter(servidor_id=request.user.get_relacionamento().id)

        return queryset

    def botao_imprimir(self, obj):
        if obj.status != ProcessoRSC.STATUS_AGUARDANDO_ENVIO_CPPD:
            result = '''<ul class="action-bar">
                            <li class="has-child">
                                <a href="#" class="btn default">Documentos</a>
                                <ul>'''
            if obj.protocolo:
                result += ''' <li><a href="/rsc/processo_capa/{id}/" target="_blank"> Capa do Processo </a></li>'''.format(id=obj.id)

            result += '''          <li><a href="/rsc/requerimento_pdf/{id}/" target="_blank"> Requerimento </a></li>
                                    <li><a href="/rsc/relatorio_descritivo_pdf/{id}" target="_blank"> Relatório Descritivo </a></li>
                                    <li><a href="/rsc/formulario_pontuacao_pdf/{id}/" target="_blank"> Formulário de Pontuação </a></li>
                                    <li><a href="/rsc/documentos_anexados_pdf/{id}/" target="_blank"> Documentos Anexados </a></li>
                                    <li><a href="/rsc/download_arquivos/{id}/"> Downloads dos Arquivos </a></li>
                                    <li><a href="/rsc/gerar_processo_completo/{id}/"> Gerar Processo Completo </a></li>
                                    '''.format(
                id=obj.id
            )

            if obj.status in [ProcessoRSC.STATUS_APROVADO, ProcessoRSC.STATUS_CIENTE_DO_RESULTADO, ProcessoRSC.STATUS_REPROVADO]:
                result += '''<li><a href="/rsc/imprimir_documentos_pdf/{id}/" target="_blank"> Documentos para Impressão </a></li>'''.format(id=obj.id)

            result += '''      </ul>
                            </li>
                        </ul>'''

            return mark_safe(result)
        else:
            return mark_safe('<span class="status status-error">Não enviado</span>')

    botao_imprimir.short_description = 'Documentos'

    def has_add_permission(self, request):
        return request.user.eh_docente

    def add_view(self, request):
        if self.has_add_permission(request):
            return httprr('/rsc/criar_processo_rsc/')
        else:
            raise PermissionDenied('Você não tem permissão para acessar esta página.')

    def opcoes(self, obj):
        html = ''
        if (obj.avaliado_pode_editar() or obj.avaliado_pode_ajustar()) and self.request.user.get_relacionamento().id == obj.servidor_id:
            html += icon('edit', '/rsc/abrir_processo_rsc/{}/'.format(obj.id))
        else:
            html += icon('view', '/rsc/abrir_processo_rsc/{}/'.format(obj.id))

        if obj.avaliado_pode_editar() and self.request.user.get_relacionamento().id == obj.servidor_id:
            html += icon('delete', '/rsc/excluir_processo_rsc/{}/'.format(obj.id))

        return mark_safe(html)

    opcoes.short_description = 'Opções'

    def get_acoes(self, obj):

        html = '<ul class="action-bar">'
        if obj.pode_ser_validado() and self.request.user.has_perm('rsc.pode_validar_processorsc'):
            html += '<li><a class="btn success" href="/rsc/validar_processorsc/{}">Validar</a></li>'.format(obj.id)
        elif obj.status in [ProcessoRSC.STATUS_REJEITADO, ProcessoRSC.STATUS_REPROVADO] and (self.request.user.get_profile().id == obj.servidor.id or obj.interessado_falecido()):
            html += '<li><a href="/rsc/clonar_processo_rsc/{:d}/" class="btn primary">Clonar</a></li>'.format(obj.id)
        elif obj.status in [ProcessoRSC.STATUS_AGUARDANDO_ACEITE_AVALIADOR, ProcessoRSC.STATUS_EM_AVALIACAO]:
            html += '<li><a href="/rsc/acompanhar_avaliacao/{:d}/" class="btn popup">Acompanhar Avaliação</a></li>'.format(obj.id)
        elif obj.status in [ProcessoRSC.STATUS_APROVADO, ProcessoRSC.STATUS_REPROVADO, ProcessoRSC.STATUS_AGUARDANDO_CIENCIA, ProcessoRSC.STATUS_CIENTE_DO_RESULTADO]:
            html += '<li><a href="/rsc/acompanhar_avaliacao/{:d}/" class="btn default popup">Visualizar Avaliação</a></li>'.format(obj.id)
        if obj.pode_selecionar_avaliadores() and self.request.user.has_perm('rsc.change_diretriz'):  # testando uma permissão específica de membro CPPD
            html += '<li><a href="/rsc/selecionar_avaliadores/{:d}/" class="btn warning popup">Selecionar Avaliadores</a></li>'.format(obj.id)
        if (
            obj.concorda_deferimento
            and obj.concorda_data_retroatividade
            and obj.status == ProcessoRSC.STATUS_CIENTE_DO_RESULTADO
            and self.request.user.has_perm('rsc.pode_validar_processorsc')
        ):
            html += '<li><a href="/rsc/finalizar_processo/{:d}/" class="btn warning confirm">Finalizar Processo</a></li>'.format(obj.id)
        if obj.status != ProcessoRSC.STATUS_REJEITADO and self.request.user.has_perm('rsc.pode_validar_processorsc'):
            html += '<li><a href="/rsc/rejeitar_processo_cppd/{:d}/" class="btn danger no-confirm popup">Rejeitar</a></li>'.format(obj.id)
        if obj.status == ProcessoRSC.STATUS_ANALISADO and self.request.user.has_perm('rsc.pode_validar_processorsc'):
            html += '<li><a href="/rsc/deferir_processo_aposentado/{:d}/" class="btn warning confirm">Deferir</a></li>'.format(obj.id)
        if obj.status in [ProcessoRSC.STATUS_REJEITADO, ProcessoRSC.STATUS_REPROVADO] and self.request.user.is_superuser:
            html += '<li><a href="/rsc/clonar_processo_rsc_mantendo_mesmo_processo_eletronico/{:d}/" class="btn primary">Clonar mantendo processo eletrônico</a></li>'.format(obj.id)

        # TODO Adiciona uma opcao para corrigir solicitacoes de RSC ja enviadas a CPPD que eventualmente nao tenha numero
        # de processo eletronico gerado. Essa opcao sera temporaria
        # ----------------------------------------------------------
        pode_gerar_pe = True
        docente_enviou_processo = not obj.status == ProcessoRSC.STATUS_AGUARDANDO_ENVIO_CPPD
        processo_eletronico_gerado = obj.processo_eletronico

        if not docente_enviou_processo:
            pode_gerar_pe = False

        if processo_eletronico_gerado:
            pode_gerar_pe = False

        if pode_gerar_pe and self.request.user.has_perm('rsc.delete_processoavaliador') or self.request.user.is_superuser:
            html += '<li><a href="/rsc/gerar_processo_eletronico/{:d}/" class="btn warning confirm">Gerar Processo Eletrônico</a></li>'.format(obj.id)
        # ----------------------------------------------------------

        html += '</ul>'
        return mark_safe(html)

    get_acoes.short_description = 'Ações'

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Servidor', 'Número do Processo', 'Data do Processo', 'Situação']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            numero_processo = ''
            data_protocolo = ''
            if obj.processo_eletronico:
                numero_processo = obj.processo_eletronico.numero_protocolo_fisico
                data_protocolo = obj.processo_eletronico.data_hora_criacao
            elif obj.protocolo:
                numero_processo = obj.protocolo.numero_protocolo
                data_protocolo = obj.protocolo.data_cadastro
            row = [idx + 1, obj.servidor, numero_processo, data_protocolo, obj.get_status_display()]
            rows.append(row)
        return rows


admin.site.register(ProcessoRSC, ProcessoRSCAdmin)


class ProtocoloYearFilter(admin.SimpleListFilter):
    title = "Ano do Protocolo"
    parameter_name = "protocolo_year"

    def lookups(self, request, model_admin):
        return [[ano, ano] for ano in Ano.objects.all().values_list('ano', flat=True)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(processo__protocolo__data_cadastro__year=self.value()).distinct()


class ProcessoAvaliacaoAdmin(ModelAdminPlus):
    list_display = ('processo', 'get_numero', 'get_situacao_processo', 'get_avaliador', 'responsavel_cadastro', 'get_situacao_avaliador_processo', 'data_aceite', 'data_convite')
    list_display_icons = True
    list_filter = ('status', 'processo__status', ProtocoloYearFilter, ('data_aceite', DateRangeListFilter))
    search_fields = ProcessoRSC.SEARCH_FIELDS
    export_to_xls = True

    form = ProcessoAvaliadorForm

    def get_list_display(self, request):
        list_display = super(ProcessoAvaliacaoAdmin, self).get_list_display(request)
        if request.user.has_perm('rsc.delete_processoavaliador'):
            list_display = list_display + ('get_acao',)
        return list_display

    def export_to_xls(self, request, queryset, processo):
        header = ['#', 'Interessado', 'Matrícula SIAPE', 'Processo', 'Data de entrada do processo',
                  'Situação do Processo', 'Responsável Cadastro do Avaliador', 'Avaliador', 'Matrícula SIAPE/CPF',
                  'Data de Convite', 'Data de Aceite',
                  'Situação Avaliação']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            row = [
                idx + 1,
                obj.processo.servidor.pessoafisica_ptr.nome,
                obj.processo.servidor.matricula,
                obj.processo.protocolo.numero_processo if obj.processo.protocolo else '',
                obj.processo.protocolo.data_cadastro if obj.processo.protocolo else '',
                obj.processo.get_status_display(),
                obj.responsavel_cadastro,
                obj.avaliador.vinculo.user.get_profile().nome,
                obj.avaliador.matricula_siape or obj.avaliador.vinculo.user.get_profile().cpf,
                obj.data_convite,
                obj.data_aceite,
                obj.get_status_display()
            ]
            rows.append(row)
        return rows

    def has_add_permission(self, request):
        return False

    def get_avaliador(self, obj):
        if obj.avaliador:
            return mark_safe('<a href="/rh/avaliador/{}/" class="popup">{}</a>'.format(obj.avaliador.id, obj.avaliador))
        return None

    get_avaliador.admin_order_field = 'avaliador'
    get_avaliador.short_description = 'Avaliador'

    def get_numero(self, obj):
        if obj.processo.protocolo:
            return mark_safe('<a href="/protocolo/processo/{}/" class="popup">{}</a>'.format(obj.processo.protocolo.id, obj.processo.protocolo.numero_processo))
        return None

    get_numero.admin_order_field = 'processo__protocolo__numero_processo'
    get_numero.short_description = 'Número do Protocolo'

    def get_situacao_avaliador_processo(self, obj):
        return mark_safe(obj.situacao_avaliador())

    get_situacao_avaliador_processo.admin_order_field = 'status'
    get_situacao_avaliador_processo.short_description = 'Situação'

    def get_situacao_processo(self, obj):
        return mark_safe(obj.processo.status_estilizado)

    get_situacao_processo.admin_order_field = 'processo__status'
    get_situacao_processo.short_description = 'Situação do Processo'

    def get_acao(self, obj):
        return mark_safe('<ul class="action-bar"><li><a class="btn danger no-confirm"  href="/admin/rsc/processoavaliador/{}/delete/"> Apagar? </a></li></ul>'.format(obj.pk))

    get_acao.short_description = 'Ação'

    def get_queryset(self, request):
        queryset = super(ProcessoAvaliacaoAdmin, self).get_queryset(request)
        return queryset


admin.site.register(ProcessoAvaliador, ProcessoAvaliacaoAdmin)


class ParametroPagamentoAdmin(ModelAdminPlus):
    list_display = ('valor_por_avaliacao', 'hora_por_avaliacao')

    def get_action_bar(self, request):
        if not ParametroPagamento.objects.all().exists():
            return super(ParametroPagamentoAdmin, self).get_action_bar(request)


admin.site.register(ParametroPagamento, ParametroPagamentoAdmin)


class ValidacaoCPPDAdmin(ModelAdminPlus):
    list_display = (
        'processo',
        'data_conclusao_titulacao_rsc_pretendido_validada',
        'data_exercio_carreira_validada',
        'data_concessao_ultima_rt_validada',
        'validador',
        'acao',
        'motivo_rejeicao',
        'data',
        'ajustado',
    )


admin.site.register(ValidacaoCPPD, ValidacaoCPPDAdmin)
