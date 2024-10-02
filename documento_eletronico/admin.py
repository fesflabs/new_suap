from django.contrib import admin
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.db import transaction
from django.shortcuts import redirect
from django.urls import reverse_lazy
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from mptt.admin import MPTTModelAdmin
from reversion_compare.admin import CompareVersionAdmin
from sentry_sdk import capture_exception

from comum.utils import get_setor
from djtools.contrib.admin import ModelAdminPlus
from djtools.middleware.threadlocals import get_user
from djtools.templatetags.filters import status, format_profile
from djtools.utils import get_datetime_now, httprr, get_uo_setor_listfilter

from documento_eletronico.forms import (
    TipoDocumentoForm,
    TipoDocumentoTextoForm,
    TipoDocumentoTextoAddForm,
    ModeloDocumentoForm,
    DocumentoTextoForm,
    CompartilhamentoDocumentosSetorPessoaForm,
    CompartilhamentoDocumentosPessoaForm,
    DocumentoTextoPessoalForm,
    DocumentoPessoalDigitalizadoForm
)
from documento_eletronico.models import (
    DocumentoTexto,
    TipoDocumento,
    TipoDocumentoTexto,
    ModeloDocumento,
    CompartilhamentoSetorPessoa,
    CompartilhamentoDocumentoPessoa,
    DocumentoDigitalizado,
    Classificacao,
    TipoConferencia,
    TipoVinculoDocumento,
    NivelPermissao,
    HipoteseLegal,
    DocumentoTextoPessoal,
    DocumentoDigitalizadoPessoal,
    DocumentoDigitalizadoAnexoSimples,
    DocumentoTextoAnexoDocumentoDigitalizado
)
from documento_eletronico.status import DocumentoStatus
from documento_eletronico.utils import eh_auditor, eh_procurador, get_setores_compartilhados

from documento_eletronico.views import get_documento_or_forbidden
from django.conf import settings


class CompareVersionAdminPlus(CompareVersionAdmin):
    # Template file used for the compare view:
    compare_template = "documento_eletronico/reversion-compare/compare.html"

    # change template from django-reversion to add compare selection form:
    object_history_template = "documento_eletronico/reversion-compare/object_history.html"

    def compare(self, obj, version1, version2):
        diff, has_unfollowed_fields = super().compare(obj, version1, version2)
        if hasattr(self, 'list_display_compare'):
            displayed_diff = []
            for diff_field in diff:
                if diff_field['field'].name in self.list_display_compare:
                    displayed_diff.append(diff_field)

            diff = displayed_diff
        return diff, has_unfollowed_fields


class TipoDocumentoFilter(admin.SimpleListFilter):
    title = "Tipo"
    parameter_name = 'tipo'

    def lookups(self, request, model_admin):
        tipos = TipoDocumentoTexto.objects.filter(modelos__isnull=False).distinct()
        return tipos.order_by('nome').values_list('id', 'nome')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(modelo__tipo_documento_texto=self.value())
        return queryset


class TipoDocumentoDigitalizadoFilter(admin.SimpleListFilter):
    title = "Tipo"
    parameter_name = 'tipo'

    def lookups(self, request, model_admin):
        tipos = TipoDocumentoTexto.objects.filter(modelos__isnull=False).distinct()
        return tipos.order_by('nome').values_list('id', 'nome')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(tipo=self.value())
        return queryset


class DashboardFilter(admin.SimpleListFilter):
    title = "Agrupamento"
    parameter_name = 'opcao'

    TODOS = ('0',)
    # Opções do Dashboard
    MEUS_DOCUMENTOS = '1'
    FAVORITOS = '2'
    COMPARTILHADOS_COMIGO = '3'
    # ASSINATURA
    DOCUMENTOS_ESPERANDO_ASSINATURA = '4'
    DOCUMENTOS_ASSINADOS_POR_MIM = '5'
    SOLICITACOES_ASSINATURA = '8'
    # Revisão
    DOCUMENTOS_ESPERANDO_REVISAO = '6'
    DOCUMENTOS_REVISADOS = '7'
    SOLICITACOES_REVISAO = '9'
    VINCULADOS_A_MIM = '10'

    OPCOES = (
        (MEUS_DOCUMENTOS, 'Meus Documentos'),
        (FAVORITOS, 'Favoritos'),
        (COMPARTILHADOS_COMIGO, 'Compartilhados comigo'),
        (VINCULADOS_A_MIM, 'Documentos vinculados a mim'),
        # Assinatura
        (DOCUMENTOS_ESPERANDO_ASSINATURA, 'Documentos esperando assinatura'),
        (DOCUMENTOS_ASSINADOS_POR_MIM, 'Minhas assinaturas'),
        (SOLICITACOES_ASSINATURA, 'Minhas solicitações de assinatura'),
        # Revisão
        (DOCUMENTOS_ESPERANDO_REVISAO, 'Documentos esperando revisão'),
        (DOCUMENTOS_REVISADOS, 'Minhas revisões'),
        (SOLICITACOES_REVISAO, 'Minhas solicitações de revisão'),
    )

    def lookups(self, request, model_admin):
        return DashboardFilter.OPCOES

    def queryset(self, request, queryset):
        switcher = {
            DashboardFilter.MEUS_DOCUMENTOS: queryset.proprios(request.user),
            DashboardFilter.FAVORITOS: queryset.filter(usuarios_marcadores_favoritos=request.user),
            DashboardFilter.COMPARTILHADOS_COMIGO: queryset.compartilhados(request.user),
            DashboardFilter.VINCULADOS_A_MIM: queryset.vinculados_a_mim(request.user),
            # Assinatura
            DashboardFilter.DOCUMENTOS_ESPERANDO_ASSINATURA: queryset.esperando_assinatura(request.user),
            DashboardFilter.DOCUMENTOS_ASSINADOS_POR_MIM: queryset.assinados(request.user),
            DashboardFilter.SOLICITACOES_ASSINATURA: queryset.assinatura_requisitada_por(request.user),
            # Revisao
            DashboardFilter.DOCUMENTOS_ESPERANDO_REVISAO: queryset.revisao_pendente(request.user),
            DashboardFilter.DOCUMENTOS_REVISADOS: queryset.revisados_por(request.user),
            DashboardFilter.SOLICITACOES_REVISAO: queryset.requisicao_pendente(request.user),
        }

        if self.value():
            return switcher.get(self.value(), queryset.none())
        return queryset


class DocumentoTextoAdmin(ModelAdminPlus):
    list_display = (
        'setor_dono',
        'get_tipo_documento',
        'identificador',
        'get_assunto',
        'get_status',
        'get_nivel_acesso',
        'get_autor',
        'data_criacao',
        'get_assinaturas',
        'get_data_primeira_assinatura',
        'get_data_finalizacao',
        'get_favorito',
    )
    ordering = ['-data_criacao', '-identificador_numero']

    list_filter = (
        (DashboardFilter,)
        + get_uo_setor_listfilter(parametro_setor='setor_dono', title_setor='Setor Dono', title_uo='Campus Dono')
        + (TipoDocumentoFilter, 'nivel_acesso', 'status', 'usuario_criacao', 'interessados')
    )

    search_fields = DocumentoTexto.SEARCH_FIELDS + ['assunto', 'id']

    list_display_icons = True
    list_per_page = 32
    date_hierarchy = 'data_criacao'
    form = DocumentoTextoForm
    actions = ['excluir_documentos_rascunho']

    fieldsets = (
        ('Dados do Documento', {'fields': ('tipo', 'modelo',
                                           'assunto', 'setor_dono',
                                           'classificacao')},),
        ('Nível de Acesso', {'fields': ('instrucoes_gerais', 'ciencia_instrucoes_gerais', 'nivel_acesso', 'hipotese_legal')}),
    )

    def get_actions(self, request):
        actions = super().get_actions(request)
        # Só vai exibir a ação para quem pode editar pelo meno 1 documento ou se já criou algum documento
        if DocumentoTexto.objects.compartilhados(request.user, NivelPermissao.EDITAR).exists() or DocumentoTexto.objects.proprios(request.user).exists():
            return actions
        else:
            for key in list(actions.keys()):
                del actions[key]
            return actions

    def excluir_documentos_rascunho(self, request, queryset):
        # if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
        #     messages.error(request, 'Você não tem permissão para realizar este procedimento.')
        #     return
        qtd_documentos_removidos = 0
        for documento in queryset:
            if not documento.pode_ser_excluido():
                continue

            if not documento.eh_documento_pessoal:
                if 'estagios' in settings.INSTALLED_APPS:
                    if DocumentoTexto.objects.filter(pk=documento.pk, praticaprofissional__isnull=False).exists():
                        continue
                if 'contratos' in settings.INSTALLED_APPS:
                    if not documento.estah_em_rascunho and (
                            documento.medicoes_despacho_set.exists() or documento.medicoes_termo_definitivo_set.exists()):
                        continue

            try:
                # Garante que os anexos serao excluidos
                anexos_simples = documento.get_apenas_anexos_digitalizados_simples()
                for anexo_simples in anexos_simples:
                    anexo_simples.delete()

                documento.delete()
                qtd_documentos_removidos += 1
            except Exception as e:
                capture_exception(e)

        self.message_user(request, f'{qtd_documentos_removidos} documentos na situação rascunho foram removidos.')

    excluir_documentos_rascunho.short_description = 'Remover documentos/rascunhos selecionados'

    def get_assunto(self, obj):
        user = get_user()
        if obj.nivel_acesso != DocumentoTexto.NIVEL_ACESSO_PUBLICO and not obj.pode_ler(user):
            return "Assunto Restrito"
        return obj.assunto

    get_assunto.short_description = 'Assunto'

    def get_tipo_documento(self, obj):
        return obj.modelo.tipo_documento_texto.nome

    get_tipo_documento.short_description = 'Tipo de Documento'
    get_tipo_documento.admin_order_field = 'modelo__tipo_documento_texto'

    def get_status(self, obj):
        return format_html(status(obj.get_status()))

    get_status.short_description = 'Situação do Documento'
    get_status.admin_order_field = 'status'

    def get_nivel_acesso(self, obj):
        return format_html(status(obj.get_nivel_acesso_display()))

    get_nivel_acesso.short_description = 'Nível de Acesso'
    get_nivel_acesso.admin_order_field = 'nivel_acesso'

    def get_assinaturas(self, obj):
        out = '-'
        user = get_user()
        if obj.nivel_acesso != DocumentoTexto.NIVEL_ACESSO_PUBLICO and not obj.pode_ler(user):
            return out
        if obj.status == DocumentoStatus.STATUS_FINALIZADO:
            out = f'''
                <ul>
                    {''.join(['<li>' + format_profile(o.assinatura.pessoa, o.assinatura.pessoa.nome) + '</li>' for o in obj.assinaturadocumentotexto_set.all()])}
                </ul>
                '''
        elif obj.status in [DocumentoStatus.STATUS_AGUARDANDO_ASSINATURA, DocumentoStatus.STATUS_ASSINADO]:
            out = f'''
                <ul>
                    {''.join(['<li>' + format_profile(o.solicitado, o.solicitado.nome) + f'{status(o.get_status_display())}</li>' for o in  obj.solicitacaoassinatura_set.all()])}
                </ul>
                '''
        return mark_safe(out)

    get_assinaturas.short_description = 'Assinaturas'

    def get_autor(self, obj):
        return format_profile(obj.usuario_criacao.pessoafisica, obj.usuario_criacao.pessoafisica.nome_usual)

    get_autor.short_description = 'Autor'

    def get_data_primeira_assinatura(self, obj):
        if obj.get_data_primeira_assinatura():
            return obj.get_data_primeira_assinatura()
        else:
            return "-"

    get_data_primeira_assinatura.short_description = "Data da Primeira Assinatura"

    def get_data_finalizacao(self, obj):
        if obj.get_data_finalizacao():
            return obj.get_data_finalizacao()
        else:
            return "-"

    get_data_finalizacao.short_description = "Data de Finalização"

    def get_favorito(self, obj):
        action = 'add'
        css = 'disabled cinza'
        if obj.usuarios_marcadores_favoritos.filter(id=self.request.user.id).exists():
            action = 'remove'
            css = 'warning'
        return format_html(f'''
                <a href="/documento_eletronico/gerenciar_favoritos/{obj.pk}/{action}/" title="Adicionar aos Favoritos" class="star">
                    <span class="fas fa-star {css}" aria-hidden="true"></span><span class="sr-only">Adicionar aos Favoritos</span>
                </a>
            ''')

    get_favorito.short_description = 'Favorito'

    def response_change(self, request, obj):
        if "_continue" in request.POST or "_addanother" in request.POST or "fancybox" in request.GET or "_popup" in request.POST:
            return super().response_change(request, obj)
        else:
            url = reverse_lazy('visualizar_documento', kwargs={'documento_id': obj.id}, current_app='documento_eletronico')
            return httprr(url)

    def get_object(self, request, object_id, from_field=None):
        obj = super().get_object(request, object_id, from_field)
        # Caso exista o parâmatro "clonado", alguns atributos são zerados para forçar o usuário a informá-los.
        obj_clonado = request.GET.get('clonado', False)
        if obj_clonado and obj:
            obj.setor_dono = None
            obj.assunto = None
        return obj

    def get_queryset(self, request, manager=None, *args, **kwargs):
        qs = super().get_queryset(request, manager=None, *args, **kwargs)  # .by_user(usuario)

        # dependendo da opcao de agrupamento exclui ou nao documentos pessoais da listagem
        if request.GET.get('opcao') not in (DashboardFilter.DOCUMENTOS_ESPERANDO_ASSINATURA, DashboardFilter.DOCUMENTOS_ASSINADOS_POR_MIM, DashboardFilter.SOLICITACOES_ASSINATURA):
            qs = qs.impessoais()

        qs = qs.select_related('modelo__tipo_documento_texto')
        qs = qs.select_related('usuario_criacao__pessoafisica')

        # Se usuário externo restringe somente aos documentos vinculados ou com solicitações de assinatura
        if request.user.get_vinculo().eh_usuario_externo():
            qs1 = list(qs.compartilhados(request.user).values_list('pk', flat=True))
            qs2 = list(qs.assinados(request.user).values_list('pk', flat=True))
            qs3 = list(qs.esperando_assinatura(request.user).values_list('pk', flat=True))
            qs4 = list(qs.vinculados_a_mim(request.user).values_list('pk', flat=True))
            qs = qs.filter(pk__in=qs1 + qs2 + qs3 + qs4)

        return qs.only('setor_dono', 'modelo__tipo_documento_texto', 'assunto', 'status', 'nivel_acesso', 'usuario_criacao__pessoafisica')

    def response_add(self, request, obj, post_url_continue=None):
        super().response_add(request, obj, post_url_continue)
        return httprr(f'/documento_eletronico/visualizar_documento/{obj.id}/')

    def add_view(self, request, form_url='', extra_context=None):
        if not get_setores_compartilhados(request.user, NivelPermissao.EDITAR).exists():
            return httprr(
                '/admin/documento_eletronico/documentotexto',
                message='Você não tem permissão em nenhum Setor para adição de Documentos Eletrônicos. '
                'Entre em contato com o Chefe do setor pretendido, e solicite que o mesmo Gerencie o Compartilhamento de Documentos Eletrônicos do setor.',
                tag='error',
            )
        return super().add_view(request, form_url, extra_context)

    # Comentado para atender a nova funcionalidade de permissões do processo e documento eletrônico
    """
    def get_action_bar(self, request, remove_add_button=False):
        items = super(DocumentoTextoAdmin, self).get_action_bar(request, remove_add_button)
        usuario_logado = request.user.get_relacionamento()
        if request.user.pessoafisica.eh_servidor and usuario_logado.eh_chefe_do_setor_hoje(usuario_logado.setor):
            for setor in Setor.objects.filter(
                pk__in=usuario_logado.servidorfuncaohistorico_set.atuais()
                .filter(funcao__codigo__in=Funcao.get_codigos_funcao_chefia())
                .values_list('setor_suap_id', flat=True)
                .distinct()
            ):
                items.append(
                    dict(
                        url='/documento_eletronico/gerenciar_compartilhamento_setor/{0}/'.format(setor.id),
                        label='Gerenciar Compartilhamento: {0}'.format(setor),
                        css_class='popup primary',
                    )
                )
        return items
    """
    # Controle de permissões -------------------------------------------------------------------------------------------

    def has_view_permission(self, request, obj=None):
        if obj and not obj.pode_ler(request.user):
            return False
        return True

    def has_change_permission(self, request, obj=None):
        if obj and not obj.pode_editar(request.user):
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return obj and obj.pode_ser_excluido(request.user)


admin.site.register(DocumentoTexto, DocumentoTextoAdmin)


class DocumentoDigitalizadoAdmin(CompareVersionAdminPlus):

    def get_queryset(self, request, manager=None, *args, **kwargs):
        qs = super().get_queryset(request, manager=None, *args, **kwargs)  # .by_user(usuario)
        qs = qs.impessoais()  # excluíndo os documentos pessoais da listagem geral.
        return qs


admin.site.register(DocumentoDigitalizado, DocumentoDigitalizadoAdmin)

# Trata-se do "Tipo de Documento Externo".


class TipoDocumentoAdmin(ModelAdminPlus, CompareVersionAdmin):
    list_display = ('nome', 'sigla', 'ativo', 'permite_documentos_pessoais')
    search_fields = ('nome', 'sigla')
    list_display_icons = True
    list_filter = ('permite_documentos_pessoais',)
    form = TipoDocumentoForm
    change_form_template = 'documento_eletronico/templates/adminutils/change_form.html'


admin.site.register(TipoDocumento, TipoDocumentoAdmin)


# Trata-se do "Tipo de Documento Interno", que possui cabeçalho e rodapé.
class TipoDocumentoTextoAdmin(ModelAdminPlus, CompareVersionAdmin):
    list_display = ('nome', 'sigla', 'ativo', 'vincular_pessoa', 'permite_documentos_pessoais', 'permite_documentos_anexos', 'get_opcoes')
    search_fields = ('nome', 'sigla')
    list_display_icons = True
    list_filter = ('vincular_pessoa', 'permite_documentos_pessoais', 'permite_documentos_anexos')
    safe_view = True
    form = TipoDocumentoTextoForm
    add_form = TipoDocumentoTextoAddForm

    change_form_template = 'documento_eletronico/templates/adminutils/change_form.html'

    def get_opcoes(self, obj):
        opcoes = f'<li><a href="/documento_eletronico/clonar_tipo_documento/{obj.pk:d}/" class="btn primary">Clonar</a></li>'
        opcoes += f'<li><a href="/admin/documento_eletronico/modelodocumento/?tipo_documento__id__exact={obj.pk:d}" class="btn default">Lista de Modelos</a></li>'
        return mark_safe(f'<ul class="action-bar">{opcoes}</ul>')

    #
    get_opcoes.short_description = 'Opções'
    get_opcoes.attrs = {'class': 'no-print'}


admin.site.register(TipoDocumentoTexto, TipoDocumentoTextoAdmin)


class ModeloDocumentoAdmin(ModelAdminPlus, CompareVersionAdminPlus):
    list_display = (
        'get_tipo_documento',
        'nome',
        'ativo',
        'permite_nivel_acesso_sigiloso',
        'permite_nivel_acesso_restrito',
        'permite_nivel_acesso_publico',
        'get_nivel_acesso_padrao',
        'get_opcoes',
    )
    search_fields = ('nome',)
    list_filter = ('tipo_documento_texto', 'permite_nivel_acesso_sigiloso', 'permite_nivel_acesso_restrito', 'permite_nivel_acesso_publico')
    list_display_icons = True
    safe_view = True
    form = ModeloDocumentoForm
    fieldsets = ModeloDocumentoForm.fieldsets

    def get_nivel_acesso_padrao(self, obj):
        return obj.get_nivel_acesso_padrao_display()

    get_nivel_acesso_padrao.admin_order_field = 'nivel_acesso_padrao'
    get_nivel_acesso_padrao.short_description = 'Nível de Acesso Padrão'

    def get_tipo_documento(self, obj):
        return obj.tipo_documento_texto.nome

    get_tipo_documento.admin_order_field = 'tipo_documento__nome'
    get_tipo_documento.short_description = 'Tipo de Documento'

    def get_opcoes(self, obj):
        opcoes = f'<li><a href="/documento_eletronico/clonar_modelo_documento/{obj.pk:d}/" class="btn primary">Clonar</a></li>'
        opcoes += f'<li><a href="/admin/documento_eletronico/modelodocumento/{obj.pk:d}/delete/" class="btn danger">Apagar</a></li>'
        return mark_safe(f'<ul class="action-bar">{opcoes}</ul>')

    #
    get_opcoes.short_description = 'Opções'
    get_opcoes.attrs = {'class': 'no-print'}

    def save_model(self, request, obj, form, change):
        obj.setor_dono = get_setor(request.user)
        super().save_model(request, obj, form, change)

    def response_add(self, request, obj, post_url_continue=None):
        super().response_add(request, obj, post_url_continue)
        return httprr(f'/documento_eletronico/editar_modelo_documento/{obj.id:d}/')

    def change_view(self, request, object_id, form_url='', extra_context=None):
        return httprr(f'/documento_eletronico/editar_modelo_documento/{object_id}/')


admin.site.register(ModeloDocumento, ModeloDocumentoAdmin)


class HipoteseLegalAdmin(ModelAdminPlus):
    list_display = ('descricao', 'base_legal', 'nivel_acesso')
    search_fields = ('descricao',)


admin.site.register(HipoteseLegal, HipoteseLegalAdmin)


class ClassificacaoAdmin(ModelAdminPlus, MPTTModelAdmin):
    list_display = ('get_descricao', 'suficiente_para_classificar_processo', 'ativo', 'mec', 'migrado')
    search_fields = ('codigo', 'descricao')
    list_filter = ('ativo', 'mec', 'migrado')
    list_display_icons = True

    def get_descricao(self, obj):
        return mark_safe('<span class="sublevel">{}|---</span> {}'.format(obj.get_level() * '&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;', obj))

    #
    get_descricao.short_description = 'Descrição'


admin.site.register(Classificacao, ClassificacaoAdmin)


class TipoConferenciaAdmin(ModelAdminPlus):
    search_fields = ('descricao',)


admin.site.register(TipoConferencia, TipoConferenciaAdmin)


class TipoVinculoDocumentoAdmin(ModelAdminPlus):
    search_fields = ('descricao',)
    list_display = ('descricao', 'descricao_voz_ativa', 'descricao_voz_passiva')


admin.site.register(TipoVinculoDocumento, TipoVinculoDocumentoAdmin)


class CompartilhamentoDocumentoPessoaAdmin(ModelAdminPlus):
    list_filter = ('documento',)
    search_fields = ('documento__identificador', 'pessoa_permitida__nome')
    list_display = ('documento', 'pessoa_permitida', 'nivel_permissao', 'data_criacao', 'usuario_criacao')
    list_display_icons = True

    form = CompartilhamentoDocumentosPessoaForm


admin.site.register(CompartilhamentoDocumentoPessoa, CompartilhamentoDocumentoPessoaAdmin)


class CompartilhamentoSetorPessoaAdmin(ModelAdminPlus):
    list_filter = ('setor_dono',)
    search_fields = ('setor_dono__sigla', 'pessoa_permitida__nome')
    list_display = ('setor_dono', 'pessoa_permitida', 'nivel_permissao', 'data_criacao', 'usuario_criacao')
    list_display_icons = True

    form = CompartilhamentoDocumentosSetorPessoaForm


admin.site.register(CompartilhamentoSetorPessoa, CompartilhamentoSetorPessoaAdmin)


class DocumentoTextualPessoalAuditorFilter(admin.SimpleListFilter):
    title = "Agrupamento"
    parameter_name = 'opcao'

    TODOS = ('0',)
    # Opções do Dashboard
    MEUS_DOCUMENTOS = '1'

    OPCOES = (
        (MEUS_DOCUMENTOS, 'Meus Documentos'),
    )

    def lookups(self, request, model_admin):
        return DocumentoTextualPessoalAuditorFilter.OPCOES

    def queryset(self, request, queryset):
        switcher = {
            DocumentoTextualPessoalAuditorFilter.MEUS_DOCUMENTOS: queryset.proprios(request.user),
        }

        if self.value():
            return switcher.get(self.value(), queryset.none())
        return queryset


class DocumentoTextoPessoalAdmin(ModelAdminPlus):

    list_display_icons = True
    list_display = (
        'get_tipo_documento',
        'identificador',
        'get_assunto',
        'get_status',
        'get_nivel_acesso',
        'get_dono',
        'data_criacao',
        'get_data_primeira_assinatura',
        'get_data_finalizacao',
    )
    ordering = ['-data_criacao', '-identificador_numero']
    list_per_page = 32
    date_hierarchy = 'data_criacao'
    search_fields = DocumentoTexto.SEARCH_FIELDS + ['assunto', 'id']

    form = DocumentoTextoPessoalForm

    fieldsets = (
        ('Dados do Documento', {'fields': ('tipo', 'modelo',
                                           'assunto',
                                           'classificacao')},),
        ('Nível de Acesso', {'fields': ('instrucoes_gerais', 'ciencia_instrucoes_gerais', 'nivel_acesso', 'hipotese_legal')}),
    )

    # ------------------------
    # LIST DISPLAY
    # ------------------------

    def changelist_view(self, request, extra_context=None):
        referrer = request.META.get('HTTP_REFERER', '')
        if len(request.GET) == 0 and '?' not in referrer:
            if self._possui_acesso_pelo_cargo(request.user):
                get_param = "opcao=1"
                return redirect(f"{request.path}?{get_param}")
        return super().changelist_view(request, extra_context=extra_context)

    def get_assunto(self, obj):
        user = get_user()
        if obj.nivel_acesso != DocumentoTexto.NIVEL_ACESSO_PUBLICO and not obj.pode_ler(user):
            return "Assunto Restrito"
        return obj.assunto

    get_assunto.short_description = 'Assunto'

    def get_tipo_documento(self, obj):
        return obj.modelo.tipo_documento_texto.nome

    get_tipo_documento.short_description = 'Tipo de Documento'
    get_tipo_documento.admin_order_field = 'modelo__tipo_documento_texto'

    def get_status(self, obj):
        return format_html(status(obj.get_status()))

    get_status.short_description = 'Situação do Documento'
    get_status.admin_order_field = 'status'

    def get_nivel_acesso(self, obj):
        return format_html(status(obj.get_nivel_acesso_display()))

    get_nivel_acesso.short_description = 'Nível de Acesso'
    get_nivel_acesso.admin_order_field = 'nivel_acesso'

    def get_assinado_por(self, obj):
        return ', '.join([format_profile(o.assinatura.pessoa, o.assinatura.pessoa.nome) for o in obj.assinaturadocumentotexto_set.all()])

    get_assinado_por.short_description = 'Assinado por'

    def get_dono(self, obj):
        return format_profile(obj.usuario_criacao.pessoafisica, obj.usuario_criacao.pessoafisica.nome_usual)

    get_dono.short_description = 'Dono'

    def get_data_primeira_assinatura(self, obj):
        if obj.get_data_primeira_assinatura():
            return obj.get_data_primeira_assinatura()
        else:
            return "-"

    get_data_primeira_assinatura.short_description = "Data da Primeira Assinatura"

    def get_data_finalizacao(self, obj):
        if obj.get_data_finalizacao():
            return obj.get_data_finalizacao()
        else:
            return "-"

    get_data_finalizacao.short_description = "Data de Finalização"

    # ------------------------
    # METODOS
    # ------------------------

    def _possui_acesso_pelo_cargo(self, user):
        return eh_auditor(user) or eh_procurador(user)

    def get_list_filter(self, request):
        list_filter = ('nivel_acesso', 'status', TipoDocumentoFilter)
        if self._possui_acesso_pelo_cargo(request.user):
            list_filter += (DocumentoTextualPessoalAuditorFilter,)
        return list_filter

    def response_change(self, request, obj):
        if "_continue" in request.POST or "_addanother" in request.POST or "fancybox" in request.GET or "_popup" in request.POST:
            return super().response_change(request, obj)
        else:
            url = reverse_lazy('visualizar_documento', kwargs={'documento_id': obj.id}, current_app='documento_eletronico')
            return httprr(url)

    def get_object(self, request, object_id, from_field=None):
        obj = super().get_object(request, object_id, from_field)
        # Caso exista o parâmatro "clonado", alguns atributos são zerados para forçar o usuário a informá-los.
        obj_clonado = request.GET.get('clonado', False)
        if obj_clonado and obj:
            obj.assunto = None
        return obj

    def get_queryset(self, request, manager=None, *args, **kwargs):
        qs = super().get_queryset(request, manager=None, *args, **kwargs)  # .by_user(usuario)
        if not self._possui_acesso_pelo_cargo(request.user):
            qs = qs.filter(usuario_criacao=request.user)
        #
        qs = qs.select_related('modelo__tipo_documento_texto')
        qs = qs.select_related('usuario_criacao__pessoafisica')

        return qs.only('modelo__tipo_documento_texto', 'assunto', 'status', 'nivel_acesso', 'usuario_criacao__pessoafisica')

    def response_add(self, request, obj, post_url_continue=None):
        return httprr(f'/documento_eletronico/visualizar_documento/{obj.id}/')

    def has_view_permission(self, request, obj=None):
        has_view_permission = super().has_view_permission(request, obj)
        if has_view_permission and obj:
            return obj.pode_ler(request.user)
        return has_view_permission

    def has_change_permission(self, request, obj=None):
        has_change_permission = super().has_change_permission(request, obj)
        if has_change_permission and obj:
            return obj.pode_editar(request.user)
        return has_change_permission

    def has_delete_permission(self, request, obj=None):
        has_delete_permission = super().has_delete_permission(request, obj)
        return has_delete_permission and obj and obj.pode_ser_excluido(request.user)


admin.site.register(DocumentoTextoPessoal, DocumentoTextoPessoalAdmin)


class DocumentoDigitalizadoPessoalAuditorFilter(admin.SimpleListFilter):
    title = "Agrupamento"
    parameter_name = 'opcao'

    TODOS = ('0',)
    # Opções do Dashboard
    MEUS_DOCUMENTOS = '1'

    OPCOES = (
        (MEUS_DOCUMENTOS, 'Meus Documentos'),
    )

    def lookups(self, request, model_admin):
        return DocumentoDigitalizadoPessoalAuditorFilter.OPCOES

    def queryset(self, request, queryset):
        switcher = {
            DocumentoDigitalizadoPessoalAuditorFilter.MEUS_DOCUMENTOS: queryset.filter(usuario_criacao=request.user),
        }

        if self.value():
            return switcher.get(self.value(), queryset.none())
        return queryset


class DocumentoDigitalizadoPessoalAdmin(ModelAdminPlus):

    list_display_icons = True
    form = DocumentoPessoalDigitalizadoForm

    list_per_page = 25
    date_hierarchy = 'data_criacao'
    ordering = ('-data_criacao', )
    search_fields = ('assunto', )

    fieldsets = (
        ('Dados do documento', {'fields': ('tipo', 'assunto')}),
        ('Nível de Acesso', {'fields': ('instrucoes_gerais', 'ciencia_instrucoes_gerais', 'nivel_acesso', 'hipotese_legal')}),
    )

    fieldsets_add = (
        ('Dados do documento', {'fields': ('tipo', 'arquivo', 'tipo_conferencia', 'assunto')}),
        ('Nível de Acesso', {'fields': ('instrucoes_gerais', 'ciencia_instrucoes_gerais', 'nivel_acesso', 'hipotese_legal')}),
        ('Dados Adicionais', {'fields': (('identificador_numero', 'identificador_ano'), 'identificador_setor_sigla',
                                         'identificador_tipo_documento_sigla')}),
        ('Assinatura', {'fields': ('papel', 'senha',)}),
    )

    def _possui_acesso_pelo_cargo(self, user):
        return user.groups.filter(name__in=['Auditor']).exists()

    def get_list_display(self, request):
        list_display = super().get_list_display(request) + ('assunto', 'tipo')
        if self._possui_acesso_pelo_cargo(request.user):
            list_display += ('dono_documento', )
        return list_display + ('nivel_acesso', 'data_criacao',)

    def get_list_filter(self, request):
        list_filter = ('nivel_acesso', TipoDocumentoDigitalizadoFilter)
        if self._possui_acesso_pelo_cargo(request.user):
            list_filter += ('dono_documento', DocumentoDigitalizadoPessoalAuditorFilter, )
        return list_filter

    def save_model(self, request, obj, form, change):
        sid = transaction.savepoint()
        try:
            is_insert = not obj.id

            if is_insert:
                obj.data_criacao = get_datetime_now()
                obj.usuario_criacao = request.user
                obj.dono_documento = request.user.get_profile()
            obj.data_ultima_modificacao = get_datetime_now()
            obj.usuario_ultima_modificacao = request.user

            obj.save()

            if is_insert:
                papel = form.cleaned_data.get('papel')
                obj.assinar_via_senha(request.user, papel)

            transaction.savepoint_commit(sid)
        except Exception as e:
            transaction.savepoint_rollback(sid)
            raise ValidationError(f'{e}')

    def get_fieldsets(self, request, obj=None):
        if obj:
            return self.fieldsets
        else:
            return self.fieldsets_add

    def get_queryset(self, request, manager=None, *args, **kwargs):
        qs = super().get_queryset(request, manager=None, *args, **kwargs)
        if not self._possui_acesso_pelo_cargo(request.user):
            qs = qs.filter(usuario_criacao=request.user)
        return qs

    def has_view_permission(self, request, obj=None):
        has_view_permission = super().has_view_permission(request, obj)
        if has_view_permission and obj:
            return obj.pode_ler(request.user)
        return has_view_permission

    def has_change_permission(self, request, obj=None):
        has_change_permission = super().has_change_permission(request, obj)
        if has_change_permission and obj:
            return obj.pode_editar(request.user)
        return False

    def add_view(self, request, form_url='', extra_context=None):
        # Cria papel (quando ele ainda não existe)
        # - para que alunos possam criar documentos pessoais
        # - para que alunos possam executar as outras operações relacionadas ao documento pessoal
        if request.user.get_vinculo().eh_aluno():
            request.user.get_vinculo().relacionamento.criar_papel_discente()
        return super().add_view(request, form_url, extra_context)

    def changelist_view(self, request, extra_context=None):
        referrer = request.META.get('HTTP_REFERER', '')
        if len(request.GET) == 0 and '?' not in referrer:
            if self._possui_acesso_pelo_cargo(request.user):
                get_param = "opcao=1"
                return redirect(f"{request.path}?{get_param}")
        return super().changelist_view(request, extra_context=extra_context)


admin.site.register(DocumentoDigitalizadoPessoal, DocumentoDigitalizadoPessoalAdmin)


class DocumentoDigitalizadoAnexoSimplesAdmin(ModelAdminPlus):

    fieldsets = (
        (None, {'fields': ('tipo', 'tipo_conferencia', 'assunto', 'arquivo')}),
    )

    def save_model(self, request, obj, form, change):
        sid = transaction.savepoint()
        try:
            documento_id = request.GET.get('documento_id')
            documento = get_documento_or_forbidden(request.user, documento_id)

            # Salva o anexo
            obj.usuario_criacao = request.user
            obj.data_ultima_modificacao = get_datetime_now()
            obj.usuario_ultima_modificacao = request.user
            obj.anexo_simples = True
            obj.nivel_acesso = documento.nivel_acesso
            obj.hipotese_legal = documento.hipotese_legal
            obj.save()

            # Vincula como anexo
            d = DocumentoTextoAnexoDocumentoDigitalizado()
            d.documento = documento
            d.documento_anexado = obj
            d.save()

            transaction.savepoint_commit(sid)
        except Exception as e:
            transaction.savepoint_rollback(sid)
            raise ValidationError(f'{e}')

    def response_add(self, request, obj, post_url_continue=None):
        documento_id = request.GET.get('documento_id')
        return httprr(f'/documento_eletronico/visualizar_documento/{documento_id}/')

    def add_view(self, request, form_url='', extra_context=None):
        documento_id = request.GET.get('documento_id')

        # documento = get_object_or_404(DocumentoTexto, pk=documento_id)
        documento = get_documento_or_forbidden(request.user, documento_id)

        if not documento.pode_receber_anexos():
            raise PermissionDenied()
        extra_context = extra_context or {}
        extra_context['title'] = f'Adicionar anexo para o documento {documento}'
        return super(ModelAdminPlus, self).add_view(request, form_url, extra_context)


admin.site.register(DocumentoDigitalizadoAnexoSimples, DocumentoDigitalizadoAnexoSimplesAdmin)
