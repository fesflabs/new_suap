# -*- coding: utf-8 -*-

from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.utils.safestring import mark_safe

from comum.models import Ano
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter, DateRangeListFilter
from djtools.templatetags.tags import icon
from djtools.utils import httprr
from professor_titular.forms import ProcessoProfessorTitularForm, ProcessoAvaliadorForm, AvaliacaoForm
from professor_titular.models import Unidade, Grupo, PontuacaoMinima, Indicador, Criterio, ProcessoTitular, CategoriaMemorialDescritivo, ProcessoAvaliador, Avaliacao


class UnidadeAdmin(ModelAdminPlus):
    list_display = ('nome', 'sigla')


admin.site.register(Unidade, UnidadeAdmin)


class GrupoTitularAdmin(ModelAdminPlus):
    list_display = ('nome', 'percentual')


admin.site.register(Grupo, GrupoTitularAdmin)


class PontuacaoMinimaTitularAdmin(ModelAdminPlus):
    list_display = ('ano', 'grupo', 'pontuacao_exigida', 'qtd_minima_grupos')


admin.site.register(PontuacaoMinima, PontuacaoMinimaTitularAdmin)


class IndicadorAdmin(ModelAdminPlus):
    list_display = ('grupo', 'nome', 'descricao')


admin.site.register(Indicador, IndicadorAdmin)


class CriterioAdmin(ModelAdminPlus):
    list_display = ('indicador', 'artigo', 'nome', 'descricao', 'status', 'pontos', 'unidade', 'categoria_memorial_descritivo')


admin.site.register(Criterio, CriterioAdmin)


class CategoriaMemorialDescritivoAdmin(ModelAdminPlus):
    list_display = ('nome',)


admin.site.register(CategoriaMemorialDescritivo, CategoriaMemorialDescritivoAdmin)


class AvaliacaoAdmin(ModelAdminPlus):
    list_display = ('processo', 'avaliador', 'get_status')
    search_fields = ('processo__servidor__matricula', 'processo__servidor__pessoa_fisica__nome', 'avaliador__vinculo__pessoa__nome')
    list_display_icons = True
    form = AvaliacaoForm

    def get_status(self, obj):
        return mark_safe(obj.status_estilizado)

    get_status.short_description = 'Situação da Avaliação'


admin.site.register(Avaliacao, AvaliacaoAdmin)


class ProcessoTitularAdmin(ModelAdminPlus):
    list_display = ('opcoes', 'servidor', 'get_numero', 'get_pontuacao_media_final', 'get_data_processo', 'status_estilizado', 'botao_imprimir', 'get_acoes')
    list_filter = (CustomTabListFilter,)
    list_display_icons = False
    search_fields = ('servidor__matricula', 'servidor__nome')
    form = ProcessoProfessorTitularForm
    show_count_on_tabs = True
    export_to_xls = True

    def get_queryset(self, request):

        queryset = super(ProcessoTitularAdmin, self).get_queryset(request)
        if request.user.is_superuser:
            return queryset
        '''
        se a pessoa não tiver a permissão "pode_validar_processotitular" filtra apenas os próprios processos
        pois não é um membro da CPPD
        '''
        if not request.user.has_perm('professor_titular.pode_validar_processotitular'):
            queryset = queryset.filter(servidor_id=request.user.get_relacionamento().id)

        '''
        se for um membro da CPPD (tiver a permissão pode_validar_processotitular) irá filtrar apenas os processos que não estejam
        com o avaliado e também trará os próprios processos
        '''
        if request.user.has_perm('professor_titular.pode_validar_processotitular'):
            queryset = queryset.exclude(status__in=[ProcessoTitular.STATUS_AGUARDANDO_AJUSTES_USUARIO, ProcessoTitular.STATUS_AGUARDANDO_ENVIO_CPPD]) | queryset.filter(
                servidor_id=request.user.get_relacionamento().id
            )

        if not request.user.has_perm('professor_titular.pode_avaliar_processotitular') and not request.user.has_perm('professor_titular.pode_validar_processotitular'):
            queryset = queryset.filter(servidor_id=request.user.get_relacionamento().id)

        return queryset

    def get_list_display(self, request):
        default_list_display = super(ProcessoTitularAdmin, self).get_list_display(request)
        if request.GET.get('tab') == 'tab_processos_finalizados':
            coluna_pagamento = ('get_situacao_pagamento',)
            nova_list_display = default_list_display + coluna_pagamento
            return nova_list_display
        return default_list_display

    def get_situacao_pagamento(self, obj):
        avaliacoes = obj.avaliacao_set.filter(status__in=[Avaliacao.FINALIZADA])
        qtd_pagas = avaliacoes.filter(avaliacao_paga=True).count()
        qtd_nao_pagas = avaliacoes.filter(avaliacao_paga=False).count()
        if qtd_nao_pagas == 0:
            situacao = 'Todas as Avaliações foram pagas.'
            class_css = 'status-success'
        else:
            situacao = 'Avaliações Pagas: {} <br /> Avaliações Não Pagas: {}'.format(qtd_pagas, qtd_nao_pagas)
            class_css = 'status-info'
        return mark_safe('<span class="status {} text-nowrap-normal">{}</span>'.format(class_css, situacao))

    get_situacao_pagamento.short_description = 'Situação dos Pagamentos'

    def get_data_processo(self, obj):
        retorno = ''
        if obj.processo_eletronico:
            retorno = obj.processo_eletronico.data_hora_criacao
        elif obj.protocolo:
            retorno = obj.protocolo.data_cadastro
        return retorno

    get_data_processo.short_description = 'Data Processo'

    def get_numero(self, obj):
        if obj.protocolo:
            return mark_safe('<a href="/protocolo/processo/{}/" class="popup">{}</a>'.format(obj.protocolo.id, obj.protocolo.numero_processo))
        elif obj.processo_eletronico:
            return mark_safe('<a href="/processo_eletronico/processo/{}/" class="popup">{}</a>'.format(obj.processo_eletronico.id, obj.processo_eletronico))
        return None

    get_numero.admin_order_field = 'protocolo__numero_processo'
    get_numero.short_description = 'Número do Processo'

    def get_pontuacao_media_final(self, obj):
        return mark_safe("{:.2f}".format(obj.pontuacao_media_final()))

    get_pontuacao_media_final.short_description = 'Pontuação Validada'

    def get_tabs(self, request):
        result = ['tab_meus_processos']
        if request.user.has_perm('professor_titular.pode_validar_processotitular'):
            result.append('tab_processos_rejeitados')
            result.append('tab_processos_pendentes')
            result.append('tab_processos_validados')
            result.append('tab_processos_em_avaliacao')
            result.append('tab_aguardando_ciencia')
            result.append('tab_processos_ciente_resultado')
            result.append('tab_processos_finalizados')
        return result

    def tab_meus_processos(self, request, queryset):
        return queryset.filter(servidor__vinculo__user=request.user)

    tab_meus_processos.short_description = 'Meus Processos'

    def tab_processos_rejeitados(self, request, queryset):
        if not request.user.has_perm('professor_titular.pode_validar_processotitular'):
            queryset = queryset.filter(servidor__vinculo__user=request.user)
        return queryset.filter(status=ProcessoTitular.STATUS_REJEITADO)

    tab_processos_rejeitados.short_description = 'Processos Rejeitados'

    def tab_processos_pendentes(self, request, queryset):
        if not request.user.has_perm('professor_titular.pode_validar_processotitular'):
            queryset = queryset.filter(servidor__vinculo__user=request.user)
        return queryset.filter(status=ProcessoTitular.STATUS_AGUARDANDO_VALIDACAO_CPPD)

    tab_processos_pendentes.short_description = 'Processos Pendentes'

    '''
    Aba que mostra os processos já validados pela CPPD e que estão esperando a atribuição de avaliadores
    '''

    def tab_processos_validados(self, request, queryset):
        return queryset.filter(status=ProcessoTitular.STATUS_AGUARDANDO_AVALIADORES)

    tab_processos_validados.short_description = 'Processos Validados'

    '''
    Aba que mostra os processos que já tem avaliadores selecionados ou que já estão em avaliação
    Aba está renomeada para "Processos em análise" para melhor entendimento
    '''

    def tab_processos_em_avaliacao(self, request, queryset):
        return queryset.filter(status__in=[ProcessoTitular.STATUS_EM_AVALIACAO, ProcessoTitular.STATUS_AGUARDANDO_ACEITE_AVALIADOR])

    tab_processos_em_avaliacao.short_description = 'Processos em Análise'

    '''
    Aba que mostra os processos que estão aguardando a ciência do avaliado
    '''

    def tab_aguardando_ciencia(self, request, queryset):
        return queryset.filter(status=ProcessoTitular.STATUS_AGUARDANDO_CIENCIA)

    tab_aguardando_ciencia.short_description = 'Aguardando Ciência'

    '''
    Aba que mostra os processos que os avaliados deram ciência do resultado (avaliação finalizada)
    '''

    def tab_processos_ciente_resultado(self, request, queryset):
        return queryset.filter(status=ProcessoTitular.STATUS_CIENTE_DO_RESULTADO)

    tab_processos_ciente_resultado.short_description = 'Processos Cientes de Resultado'

    '''
    Aba que mostra os processos finalizados
    '''

    def tab_processos_finalizados(self, request, queryset):
        return queryset.filter(status__in=[ProcessoTitular.STATUS_APROVADO, ProcessoTitular.STATUS_REPROVADO])

    tab_processos_finalizados.short_description = 'Processos Finalizados'

    def status_estilizado(self, obj):
        return mark_safe(obj.status_estilizado)

    status_estilizado.admin_order_field = 'status'
    status_estilizado.short_description = 'Situação'

    def get_acoes(self, obj):
        html = '<ul class="action-bar">'
        if obj.pode_ser_validado() and self.request.user.has_perm('professor_titular.pode_validar_processotitular'):
            html += '<li><a href="/professor_titular/validar_processo_titular/{}" class="btn success">Validar</a></li>'.format(obj.id)
        elif obj.status in [ProcessoTitular.STATUS_REJEITADO, ProcessoTitular.STATUS_REPROVADO] and self.request.user.get_relacionamento().id == obj.servidor.id:
            html += '<li><a href="/professor_titular/clonar_processo_titular/{:d}/" class="btn primary">Clonar</a></li>'.format(obj.pk)
        elif obj.status in [ProcessoTitular.STATUS_AGUARDANDO_ACEITE_AVALIADOR, ProcessoTitular.STATUS_EM_AVALIACAO]:
            html += '<li><a href="/professor_titular/acompanhar_avaliacao/{:d}/" class="btn popup success">Acompanhar Avaliação</a></li>'.format(obj.pk)
        elif obj.status in [
            ProcessoTitular.STATUS_APROVADO,
            ProcessoTitular.STATUS_REPROVADO,
            ProcessoTitular.STATUS_AGUARDANDO_CIENCIA,
            ProcessoTitular.STATUS_CIENTE_DO_RESULTADO,
        ]:
            html += '<li><a href="/professor_titular/acompanhar_avaliacao/{:d}/" class="btn default">Visualizar Avaliação</a></li>'.format(obj.pk)
        if obj.pode_selecionar_avaliadores() and self.request.user.has_perm('professor_titular.change_indicador'):  # testando uma permissão específica de membro CPPD
            html += '<li><a href="/professor_titular/selecionar_avaliadores/{:d}/" class="btn popup">Selecionar Avaliadores</a></li>'.format(obj.pk)
        if obj.concorda_deferimento and obj.status == ProcessoTitular.STATUS_CIENTE_DO_RESULTADO and self.request.user.has_perm('professor_titular.pode_validar_processotitular'):
            html += '<li><a href="/professor_titular/finalizar_processo/{:d}/" class="btn warning confirm">Finalizar Processo</a></li>'.format(obj.pk)
        if obj.status != ProcessoTitular.STATUS_REJEITADO and self.request.user.has_perm('professor_titular.pode_validar_processotitular'):
            html += '<li><a href="/professor_titular/rejeitar_processo_cppd/{:d}/" class="btn danger no-confirm popup">Rejeitar</a></li>'.format(obj.pk)
        html += '</ul>'
        return mark_safe(html)

    get_acoes.short_description = 'Opções'

    def botao_imprimir(self, obj):
        if obj.status != ProcessoTitular.STATUS_AGUARDANDO_ENVIO_CPPD:
            result = ''' <ul class="action-bar">
                            <li class="has-child">
                                <a href="#" class="btn default">Documentos</a>
                                <ul>'''
            if obj.protocolo:
                result += ''' <li><a href="/professor_titular/processo_capa/{id}/" target="_blank"> Capa do Processo </a></li>'''.format(id=obj.id)

            result += '''          <li><a href="/professor_titular/requerimento_pdf/{id}/" target="_blank"> Requerimento </a></li>
                                    <li><a href="/professor_titular/relatorio_descritivo_pdf/{id}" target="_blank"> Memorial Descritivo </a></li>
                                    <li><a href="/professor_titular/formulario_pontuacao_pdf/{id}/" target="_blank"> Formulário de Pontuação </a></li>
                                    <li><a href="/professor_titular/documentos_anexados_pdf/{id}/" target="_blank">Listagem dos Documentos Anexados </a></li>
                                    <li><a href="/professor_titular/download_arquivos/{id}/"> Downloads dos Arquivos </a></li>
                                    <li><a href="/professor_titular/gerar_processo_completo/{id}/"> Gerar Processo Completo </a></li>
                        '''.format(
                id=obj.id
            )

            if obj.status in [ProcessoTitular.STATUS_APROVADO, ProcessoTitular.STATUS_CIENTE_DO_RESULTADO]:
                result += '''<li><a href="/professor_titular/imprimir_documentos_pdf/{id}/" target="_blank"> Documentos para Impressão </a></li>'''.format(id=obj.id)
                result += '''<li><a href="/professor_titular/encaminhamento_banca_pdf/{id}/" target="_blank"> Documento de Encaminhamento da Banca </a></li>'''.format(id=obj.id)

            result += '''</ul>
                        </li>
                    </ul>'''

            return mark_safe(result)

        else:
            return mark_safe('<span class="status status-error">Não enviado</span>')

    botao_imprimir.short_description = 'Documentos'

    def has_add_permission(self, request):
        tem_permissao = super(ProcessoTitularAdmin, self).has_add_permission(request)
        return tem_permissao and request.user.eh_docente

    def add_view(self, request):
        if self.has_add_permission(request):
            return httprr('/professor_titular/criar_processo_titular/')
        else:
            raise PermissionDenied('Você não tem permissão para acessar esta página!')

    def opcoes(self, obj):
        html = ''
        if (obj.avaliado_pode_editar() or obj.avaliado_pode_ajustar()) and self.request.user.get_relacionamento().id == obj.servidor.id:
            html += icon('edit', '/professor_titular/abrir_processo_titular/{}/'.format(obj.id))
        else:
            html += icon('view', '/professor_titular/abrir_processo_titular/{}/'.format(obj.id))

        if obj.avaliado_pode_editar() and self.request.user.get_relacionamento().id == obj.servidor.id:
            html += icon('delete', '/professor_titular/excluir_processo_titular/{}/'.format(obj.id))

        return mark_safe(html)

    opcoes.short_description = 'Ações'

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Servidor', 'Número do Processo', 'Data do Processo', 'Pontuação Média Final', 'Situação']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            numero_processo = ''
            if obj.processo_eletronico:
                numero_processo = obj.processo_eletronico.data_hora_criacao
            elif obj.protocolo:
                numero_processo = obj.protocolo.data_cadastro
            row = [idx + 1, obj.servidor, numero_processo, self.get_data_processo(obj), self.get_pontuacao_media_final(obj), obj.get_status_display()]
            rows.append(row)
        return rows


admin.site.register(ProcessoTitular, ProcessoTitularAdmin)


class ProtocoloYearFilter(admin.SimpleListFilter):
    title = "Ano do Protocolo"
    parameter_name = "protocolo_year"

    def lookups(self, request, model_admin):
        return [[ano, ano] for ano in Ano.objects.all().values_list('ano', flat=True)]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(processo__protocolo__data_cadastro__year=self.value()).distinct()


class ProcessoAvaliacaoAdmin(ModelAdminPlus):
    list_display = ('processo', 'get_numero', 'get_situacao_processo', 'vinculo_responsavel_cadastro', 'get_avaliador', 'get_situacao_avaliador_processo', 'get_situacao_avaliacao', 'data_convite', 'data_aceite')
    list_display_icons = True
    list_filter = ('status', 'processo__status', ProtocoloYearFilter, ('data_aceite', DateRangeListFilter))
    search_fields = ('processo__servidor__matricula', 'processo__servidor__pessoa_fisica__nome', 'avaliador__vinculo__pessoa__nome')
    export_to_xls = True
    form = ProcessoAvaliadorForm

    def get_list_display(self, request):
        list_display = super(ProcessoAvaliacaoAdmin, self).get_list_display(request)
        if request.user.has_perm('professor_titular.delete_processoavaliador'):
            list_display = list_display + ('get_acao',)
        return list_display

    def to_xls(self, request, queryset, processo):
        header = ['#', 'Interessado', 'Matrícula SIAPE', 'Processo', 'Data de entrada do processo',
                  'Situação do Processo', 'Responsável Cadastro do Avaliador', 'Avaliador', 'Matrícula SIAPE/CPF',
                  'Data de Convite', 'Data de Aceite', 'Situação Avaliação']
        rows = [header]
        for idx, obj in enumerate(processo.iterate(queryset)):
            row = [
                idx + 1,
                obj.processo.servidor.pessoa_fisica.nome,
                obj.processo.servidor.matricula,
                obj.processo.protocolo.numero_processo if obj.processo.protocolo else '',
                obj.processo.protocolo.data_cadastro if obj.processo.protocolo else '',
                obj.processo.get_status_display(),
                obj.vinculo_responsavel_cadastro,
                obj.avaliador.vinculo.pessoa.nome,
                obj.avaliador.matricula_siape or obj.avaliador.vinculo.pessoa.pessoafisica.cpf,
                obj.data_convite,
                obj.data_aceite,
                obj.get_status_display()
            ]
            rows.append(row)
        return rows

    def get_avaliador(self, obj):
        if obj.avaliador:
            return mark_safe('<a href="/rh/avaliador/{}/" class="popup">{}</a>'.format(obj.avaliador.id, obj.avaliador))
        return ''

    get_avaliador.admin_order_field = 'avaliador'
    get_avaliador.short_description = 'Avaliador'

    def get_numero(self, obj):
        if obj.processo.protocolo:
            return mark_safe('<a href="/protocolo/processo/{}/" class="popup">{}</a>'.format(obj.processo.protocolo.id, obj.processo.protocolo.numero_processo))
        return ''

    get_numero.admin_order_field = 'processo__protocolo__numero_processo'
    get_numero.short_description = 'Número do Processo'

    def get_situacao_avaliador_processo(self, obj):
        return mark_safe(obj.situacao_avaliador())

    get_situacao_avaliador_processo.admin_order_field = 'status'
    get_situacao_avaliador_processo.short_description = 'Situação'

    def get_situacao_processo(self, obj):
        return mark_safe(obj.processo.status_estilizado)

    get_situacao_processo.admin_order_field = 'processo__status'
    get_situacao_processo.short_description = 'Situação do Processo'

    def get_situacao_avaliacao(self, obj):
        if obj.avaliacao_correspondente:
            return mark_safe(obj.avaliacao_correspondente.status_estilizado)
        return ''

    get_situacao_avaliacao.short_description = 'Situação da Avaliação'

    def get_acao(self, obj):
        return mark_safe(
            f'<ul class="action-bar"><li><a class="btn danger no-confirm" href="/admin/professor_titular/processoavaliador/{obj.pk}/delete/">Apagar?</a></li></ul>'
        )

    get_acao.short_description = 'Ação'


admin.site.register(ProcessoAvaliador, ProcessoAvaliacaoAdmin)
