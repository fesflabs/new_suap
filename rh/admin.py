import datetime

from django.apps import apps
from django.contrib import admin, messages
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied, ValidationError
from django.db.models import Q, Subquery, OuterRef
from django.http import HttpResponseRedirect
from django.utils.safestring import mark_safe

from comum.forms import SetorTelefoneForm
from comum.models import SetorTelefone, PessoaTelefone, PessoaEndereco, Vinculo
from djtools import forms
from djtools.contrib.admin import ModelAdminPlus, CustomTabListFilter
from djtools.choices import Meses
from djtools.choices import DiaSemanaChoices
from djtools.templatetags.filters import format_user, in_group
from djtools.templatetags.tags import icon
from djtools.forms.widgets import AutocompleteWidget


from djtools.utils import get_uo_setor_listfilter, httprr
from rh.forms import (
    SetorForm,
    PessoaFisicaForm,
    PessoaJuridicaForm,
    ServidorForm,
    ServidorSetorHistoricoForm,
    SetorJornadaHistoricoFormFactory,
    AvaliadorExternoForm,
    AreaVinculacaoForm,
    GetServidorFuncaoHistoricoForm,
    GetServidorFuncaoSiapeHistoricoForm,
    InstituicaoForm,
    SetorAddForm,
    PCAForm,
    CronogramaFolhaForm,
    JornadaTrabalhoPCAForm,
    RegimeJuridicoPCAForm,
    PosicionamentoPCAForm,
    AcaoSaudeForm,
    AgendarAtendimentoForm,
    AgendaAtendimentoHorarioForm,
    DataConsultaBloqueadaForm,
    ProcessoCargaHorariaReduzidaRHForm,
    PessoaExternaForm,
    PessoaEnderecoForm,
    PessoaJurificaContatoForm,
    BancoForm,
    ServidorReativacaoTemporariaForm,
    ExcecaoDadoWSForm,
    SolicitacaoAlteracaoFotoForm,
)

from rh.importador import PosicionamentoPCA
from rh.importador_ws import ImportadorWs
from rh.models import (
    Atividade,
    CampoExcecaoWS,
    CargoClasse,
    DiplomaLegal,
    ExcecaoDadoWS,
    SolicitacaoAlteracaoFoto,
    Titulacao,
    Funcao,
    GrupoCargoEmprego,
    CargoEmprego,
    GrupoOcorrencia,
    JornadaTrabalho,
    NivelEscolaridade,
    Ocorrencia,
    RegimeJuridico,
    Situacao,
    Banco,
    ServidorOcorrencia,
    Setor,
    UnidadeOrganizacional,
    PessoaJuridica,
    PessoaFisica,
    Servidor,
    Pessoa,
    ServidorSetorHistorico,
    SetorJornadaHistorico,
    Avaliador,
    AreaVinculacao,
    Instituicao,
    ServidorFuncaoHistorico,
    Papel,
    AreaConhecimento,
    JornadaTrabalhoPCA,
    PCA,
    CronogramaFolha,
    RegimeJuridicoPCA,
    AcaoSaude,
    HorarioAgendado,
    AgendaAtendimentoHorario,
    DataConsultaBloqueada,
    CargaHorariaReduzida,
    PessoaExterna,
    TipoUnidadeOrganizacional,
    PessoaJuridicaContato,
    PadraoVencimento,
    ServidorAfastamento,
    AfastamentoSiape,
    CargoEmpregoArea,
    ServidorReativacaoTemporaria,
)
from django.conf import settings


def restringir_grupo(self, request):
    self.usuario = request.user
    chefe = Servidor.objects.get(user__id=self.usuario.id)
    self.subordinados = Servidor.objects.filter(setor__superior=chefe.setor)
    if request.REQUEST == {}:
        return admin.ModelAdmin.get_queryset(self, request).filter(servidor=request.REQUEST["servidor"])
    else:
        return admin.ModelAdmin.get_queryset(self, request)


###############
# Atividade
###############


class AtividadeAdmin(ModelAdminPlus):
    list_display = ("nome", "codigo", "excluido")
    ordering = ("excluido", "nome", "codigo")
    list_filter = ["excluido"]
    search_fields = ("nome", "codigo")


admin.site.register(Atividade, AtividadeAdmin)


###############
# Bancos
###############


class BancoAdmin(ModelAdminPlus):
    form = BancoForm
    list_display = ("codigo", "nome", "sigla", "excluido")
    ordering = ("excluido", "nome", "codigo")
    list_filter = ["excluido"]
    search_fields = ("nome", "codigo", "sigla")


admin.site.register(Banco, BancoAdmin)


###############
# Cargo Emprego
###############


class CargoEmpregoUtilizadosFilter(admin.SimpleListFilter):
    title = "Cargo emprego usado no sistema"
    parameter_name = "usado_no_sistema"

    SIM = "SIM"
    NAO = "NAO"

    def lookups(self, request, model_admin):
        return ((self.SIM, "Sim"), (self.NAO, "Não"))

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == self.SIM:
                return queryset.filter(servidor__isnull=False).distinct()
            elif self.value() == self.NAO:
                return queryset.filter(servidor__isnull=True).distinct()


class CargoEmpregoAreaInline(admin.StackedInline):
    model = CargoEmpregoArea
    fields = ("descricao",)
    extra = 1


class CargoEmpregoAdmin(ModelAdminPlus):
    list_display = ("nome", "nome_amigavel", "codigo", "grupo_cargo_emprego", "excluido")
    list_display_icons = True
    readonly_fields = ("codigo", "nome", "sigla_escolaridade", "excluido")
    ordering = ("excluido", "nome", "codigo")
    list_filter = ["excluido", CargoEmpregoUtilizadosFilter]
    search_fields = ("nome", "codigo")
    inlines = [CargoEmpregoAreaInline]


admin.site.register(CargoEmprego, CargoEmpregoAdmin)


###############
# Cargo Classe
###############


class CargoClasseAdmin(ModelAdminPlus):
    list_display = ("nome", "codigo", "excluido")
    ordering = ("excluido", "nome", "codigo")
    list_filter = ["excluido"]
    search_fields = ("nome", "codigo")


admin.site.register(CargoClasse, CargoClasseAdmin)


###############
# Diploma Legal
###############


class DiplomaLegalAdmin(ModelAdminPlus):
    list_display = ("nome", "sigla", "codigo", "excluido")
    ordering = ("excluido", "nome", "sigla", "codigo")
    list_filter = ["excluido"]
    search_fields = ("nome", "codigo", "sigla")


admin.site.register(DiplomaLegal, DiplomaLegalAdmin)


###############
# Titulacao
###############


class TitulacaoAdmin(ModelAdminPlus):
    list_display = ("nome", "codigo", "titulo_masculino", "titulo_feminino")
    ordering = ("nome", "codigo")
    search_fields = ("nome", "codigo")


admin.site.register(Titulacao, TitulacaoAdmin)


###############
# Funcao
###############


class FuncaoAdmin(ModelAdminPlus):

    list_display = ("nome", "codigo", "funcao_suap", "excluido")
    ordering = ("excluido", "nome", "codigo")
    list_filter = ["funcao_siape", "funcao_suap", "excluido"]
    search_fields = ("nome", "codigo")


admin.site.register(Funcao, FuncaoAdmin)


###############
# Servidor Funcao
###############
class DataFimFuncaoFilter(admin.SimpleListFilter):
    title = "Data Fim de Função"
    parameter_name = "com_data_fim"

    def lookups(self, request, model_admin):
        return [[True, "Com data fím"], [False, "Sem data fím"]]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(data_fim_funcao__isnull=self.value() == "False")
        return queryset


class ServidorFuncaoHistoricoAdmin(ModelAdminPlus):
    list_display = (
        "servidor",
        "data_inicio_funcao",
        "data_fim_funcao",
        "funcao",
        "nivel",
        "atividade",
        "setor",
        "setor_suap",
        "atualiza_pelo_extrator",
    )
    ordering = ("-data_inicio_funcao",)
    list_filter = (
        get_uo_setor_listfilter("setor_suap", "Setor SUAP", "Campus SUAP")
        + ("funcao", "atividade")
        + get_uo_setor_listfilter("setor", "Setor SIAPE", "Campus SIAPE", setor_suap=False)
        + (DataFimFuncaoFilter,)
    )
    search_fields = ("servidor__nome", "servidor__matricula", "funcao__codigo", "funcao__nome")
    list_display_icons = True
    date_hierarchy = "data_inicio_funcao"

    def get_queryset(self, request):
        if request.user.is_superuser:
            queryset = super().get_queryset(request)
        elif request.user.has_perm("rh.eh_rh_sistemico") or in_group(request.user, "Auditor"):
            queryset = super().get_queryset(request).exclude(funcao__codigo="ETG")
        else:
            funcionario = request.user.get_profile().funcionario
            if funcionario:
                uo_siape = UnidadeOrganizacional.objects.filter(equivalente=funcionario.setor.uo, setor__excluido=False)
                queryset = super().get_queryset(request).exclude(funcao__codigo="ETG")
                queryset = (queryset.filter(setor_suap__uo=funcionario.setor.uo) | queryset.filter(setor__uo__in=uo_siape)).distinct()
            else:
                queryset = ServidorFuncaoHistorico.objects.none()
        return queryset

    def get_form(self, request, obj=None, **kwargs):
        if obj and not obj.funcao.funcao_suap:
            return GetServidorFuncaoSiapeHistoricoForm(request.user)
        return GetServidorFuncaoHistoricoForm(request.user)


admin.site.register(ServidorFuncaoHistorico, ServidorFuncaoHistoricoAdmin)


###############
# Grupo de Cargo Emprego
###############


class GrupoCargoEmpregoAdmin(ModelAdminPlus):
    list_display = ("nome", "sigla", "codigo", "categoria", "excluido")
    ordering = ("excluido", "nome", "sigla", "codigo")
    list_filter = ["categoria"]
    search_fields = ("nome", "codigo", "sigla")


admin.site.register(GrupoCargoEmprego, GrupoCargoEmpregoAdmin)


###############
# Grupo de Ocorrencia
###############


class GrupoOcorrenciaAdmin(ModelAdminPlus):
    list_display = ("nome", "codigo", "excluido")
    ordering = ("excluido", "nome", "codigo")
    list_filter = ["excluido"]
    search_fields = ("nome", "codigo")


admin.site.register(GrupoOcorrencia, GrupoOcorrenciaAdmin)


###############
# Jornada de Trabalho
###############


class JornadaTrabalhoAdmin(ModelAdminPlus):
    list_display = ("nome", "codigo", "excluido")
    ordering = ("excluido", "nome", "codigo")
    list_filter = ["excluido"]
    search_fields = ("nome", "codigo")


admin.site.register(JornadaTrabalho, JornadaTrabalhoAdmin)


class SetorJornadaHistoricoAdmin(ModelAdminPlus):
    list_display = ("setor_link_historico_jornadas", "jornada_trabalho", "data_inicio_da_jornada", "data_fim_da_jornada_formatada")
    search_fields = (
        "setor__nome",
        "setor__sigla",
        "jornada_trabalho__codigo",
        "jornada_trabalho__nome",
        "data_inicio_da_jornada",
        "data_fim_da_jornada",
    )
    list_filter = ("jornada_trabalho",)
    list_display_icons = True

    def setor_link_historico_jornadas(self, obj):
        return mark_safe(
            '<a href="/rh/setor_jornada_historico/%s/" title="%s">%s</a>'
            % (obj.setor.id, "Detalhar Jornada de Trabalho de %s" % obj.setor, obj.setor)
        )

    setor_link_historico_jornadas.short_description = "Setor"
    setor_link_historico_jornadas.admin_order_field = "setor"

    def data_fim_da_jornada_formatada(self, obj):
        if obj.data_fim_da_jornada:
            return obj.data_fim_da_jornada
        else:
            return "-"

    data_fim_da_jornada_formatada.short_description = "Data Final da Jornada"
    data_fim_da_jornada_formatada.admin_order_field = "data_fim_da_jornada"

    def get_action_bar(self, request):
        items = super().get_action_bar(request)
        url_base = "/rh/setor_jornada_historico_pendencias/"
        items.append(dict(url=url_base, label="Setores com pendências"))
        return items

    def get_queryset(self, request):
        if request.user.has_perm("rh.eh_rh_sistemico"):
            return SetorJornadaHistorico.objects.all()
        else:
            #
            # exibe apenas os históricos dos setores pertencentes ao mesmo campus do usuário logado
            #
            funcionario = request.user.get_profile().funcionario
            if funcionario:
                return SetorJornadaHistorico.objects.filter(setor__uo__sigla=funcionario.setor.uo.sigla)
            else:
                return []  # usuário logado tem permissão para gerenciar jornadas de trabalho de setores mas não é funcionário!!!!!

    def get_form(self, request, obj=None, **kwargs):
        return SetorJornadaHistoricoFormFactory(request)


admin.site.register(SetorJornadaHistorico, SetorJornadaHistoricoAdmin)


###############
# Nivel Escolaridade
###############


class NivelEscolaridadeAdmin(ModelAdminPlus):
    list_display = ("nome", "codigo", "excluido")
    ordering = ("excluido", "nome", "codigo")
    list_filter = ["excluido"]
    search_fields = ("nome", "codigo")


admin.site.register(NivelEscolaridade, NivelEscolaridadeAdmin)


###############
# Ocorrencia
###############


class OcorrenciaAdmin(ModelAdminPlus):
    list_display = ("nome", "codigo", "grupo_ocorrencia", "excluido")
    ordering = ("excluido", "nome", "codigo")
    list_filter = ["excluido"]
    search_fields = ("nome", "codigo")


admin.site.register(Ocorrencia, OcorrenciaAdmin)


class PessoaAdmin(ModelAdminPlus):
    list_display_icons = True
    exclude = ("setores_adicionais",)

    def has_add_permission(self, request):
        if request.user == request.user.is_superuser:
            return True
        return False

    def cpf_ou_cnpj(self, obj):
        try:
            return obj.pessoafisica.cpf
        except Exception:
            return obj.pessoajuridica.cnpj

    cpf_ou_cnpj.short_description = "CPF ou CNPJ"

    list_display = ["nome", "cpf_ou_cnpj"]
    search_fields = ["nome"]


admin.site.register(Pessoa, PessoaAdmin)


class TelefoneInline(admin.StackedInline):
    model = PessoaTelefone
    fields = ("numero",)
    extra = 1


class ContatoInline(admin.StackedInline):
    form = PessoaJurificaContatoForm
    model = PessoaJuridicaContato
    fields = ("descricao", "telefone", "email", "via_form_suap")
    extra = 1


class PessoaEnderecoInline(admin.StackedInline):
    form = PessoaEnderecoForm
    model = PessoaEndereco
    fields = ("municipio", "logradouro", "numero", "complemento", "bairro", "cep", "via_form_suap")
    extra = 1


class PessoaFisicaAdmin(ModelAdminPlus):
    form = PessoaFisicaForm
    search_fields = ("nome", "username", "cpf")
    list_display = ("nome", "cpf", "telefones", "username")
    list_display_icons = True
    inlines = [TelefoneInline]

    def has_add_permission(self, request):
        if request.user == request.user.is_superuser:
            return True
        return False

    def has_change_permission(self, request, obj=None):
        if obj and request.user == obj.user:
            # Se a pessoa a ser editada for a logada, pode editar
            return True
        return super(self.__class__, self).has_change_permission(request, obj)

    def get_form(self, request, obj=None, **kwargs):
        if request.user.is_superuser:
            kwargs["fields"] = ("nome", "sexo", "cpf", "passaporte", "nascimento_data", "tem_digital_fraca", "username")
        else:
            kwargs["fields"] = ("nome", "sexo", "cpf", "passaporte", "nascimento_data")
        return super().get_form(request, obj=obj, **kwargs)


admin.site.register(PessoaFisica, PessoaFisicaAdmin)


class PessoaJuridicaAdmin(ModelAdminPlus):
    fields = ("nome", "nome_fantasia", "cnpj", "ramo_atividade", "nome_representante_legal", "email", "inscricao_estadual", "website")
    form = PessoaJuridicaForm
    inlines = [ContatoInline, PessoaEnderecoInline]
    list_display_icons = True
    list_display = ("cnpj", "get_nome", "nome_fantasia", "telefones", "natureza_juridica", "ramo_atividade", "sistema_origem")
    list_filter = ("sistema_origem",)
    search_fields = ("nome", "nome_fantasia", "cnpj")

    def get_nome(self, obj):
        return obj.nome

    get_nome.short_description = "Razão Social"
    get_nome.admin_order_field = "nome"

    def get_view_inlines(self, request):
        return ["get_telefones", "get_enderecos"]

    def get_telefones(self, obj):
        return obj.pessoajuridicacontato_set.all()

    get_telefones.short_description = "Telefones"
    get_telefones.columns = ["descricao", "telefone", "email"]

    def get_enderecos(self, obj):
        return obj.pessoaendereco_set.all()

    get_enderecos.short_description = "Endereços"


admin.site.register(PessoaJuridica, PessoaJuridicaAdmin)


###############
# Regime Juridico
###############


class RegimeJuridicoAdmin(ModelAdminPlus):
    list_display = ("nome", "sigla", "codigo_regime", "excluido")
    ordering = ("excluido", "nome", "sigla", "codigo_regime")
    list_filter = ["excluido"]
    search_fields = ("nome", "sigla", "codigo")


admin.site.register(RegimeJuridico, RegimeJuridicoAdmin)


###############
# Representante Legal
###############

# class RepresentanteLegalAdmin(admin.ModelAdmin):
# pass
# admin.site.register(RepresentanteLegal, RepresentanteLegalAdmin)

############
# Servidor #
############


class CategoriaListFilter(admin.SimpleListFilter):
    title = "Categoria"
    parameter_name = "categoria"
    DOCENTE = "docente"
    TECNICO = "tecnico_administrativo"
    ESTAGIARIO = "estagiario"

    def lookups(self, request, model_admin):
        return [[self.DOCENTE, "Docente"], [self.TECNICO, "Técnico Administrativo"], [self.ESTAGIARIO, "Estagiário"]]

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == self.DOCENTE:
                return queryset.filter(eh_docente=True)
            elif self.value() == self.TECNICO:
                return queryset.filter(eh_tecnico_administrativo=True)
            elif self.value() == self.ESTAGIARIO:
                return queryset.filter(situacao__codigo__in=Situacao.situacoes_siape_estagiarios())
        return queryset


class FuncaoListFilter(admin.SimpleListFilter):
    title = "Função"
    parameter_name = "funcao"

    def lookups(self, request, model_admin):
        return [[funcao.pk, str(funcao)] for funcao in Funcao.objects.usadas()]

    def queryset(self, request, queryset):
        hoje = datetime.date.today()
        if self.value():
            funcoes_hoje = ServidorFuncaoHistorico.objects.filter(servidor=OuterRef('pk'), funcao_id=self.value(), data_inicio_funcao__lte=hoje).filter(Q(data_fim_funcao__gte=hoje) | Q(data_fim_funcao__isnull=True))
            queryset = queryset.filter(pk__in=Subquery(funcoes_hoje.values('servidor__pk')))
        return queryset.distinct()


class ServidorAdmin(ModelAdminPlus):
    form = ServidorForm
    list_display_icons = True
    list_per_page = 20
    list_filter = ('setor__uo', 'setor',
                   "excluido",
                   CategoriaListFilter,
                   "cargo_emprego_area",
                   FuncaoListFilter,
                   "situacao",
                   )
    if "edu" in settings.INSTALLED_APPS:
        list_filter += ("professor__disciplina",)
    list_display = ("get_foto", "get_info_principal", "get_info_cargo", "get_info_funcional")
    search_fields = tuple(Servidor.SEARCH_FIELDS) + ("setor__sigla",)
    export_to_xls = True

    dados_funcionais = (("Dados Funcionais", {"fields": ("cargo_emprego", "setor", "setores_adicionais")}),)
    dados_sistemicos = (("Para Terminal de Ponto", {"fields": ("tem_digital_fraca", "senha_ponto")}),)
    fieldsets = (
        ("Dados Pessoais", {"fields": ("nome_usual", "nome_pai", "nascimento_municipio", ("grupo_sanguineo", "fator_rh"), "foto")}),
    ) + dados_funcionais

    extra_fieldsets = (
        (
            "Dados Pessoais",
            {
                "fields": (
                    "nome_usual",
                    "nome_social",
                    "nome_registro",
                    "nome_pai",
                    "nascimento_municipio",
                    ("grupo_sanguineo", "fator_rh"),
                    "foto",
                )
            },
        ),
    ) + dados_funcionais

    super_extra_fieldsets = (("SÓ SUPERUSUÁRIO", {"fields": ("setor_exercicio", "excluido")}),)

    def get_fieldsets(self, request, obj=None):
        meus_fieldsets = self.fieldsets
        if request.user.has_perm("rh.add_servidor"):
            meus_fieldsets = (
                self.extra_fieldsets + self.dados_sistemicos + (("Para Gestão de Pessoas", {"fields": ("cpf", "matricula", "situacao")}),)
            )
        elif request.user.has_perm("rh.eh_rh_sistemico"):
            meus_fieldsets = self.extra_fieldsets + self.dados_sistemicos
        if request.user.is_superuser:
            meus_fieldsets += self.super_extra_fieldsets

        return meus_fieldsets

    def get_info_principal(self, obj):
        show_telefones, show_email = "", ""
        if obj.telefones_institucionais:
            show_telefones = "<dt>Telefones institucionais:</dt>"
            for telefone in obj.telefones_institucionais.split(","):
                show_telefones += "<dd>%s</dd>" % telefone

        if obj.email:
            show_email = f'<a href="mailto:{obj.email}">{obj.email}</a>'
        out = """
        <dl>
            <dt class="hidden">Nome:</dt><dd class="negrito">%(nome)s</dd>
            <dt class="hidden">E-mail:</dt><dd>%(show_email)s </dd>
            %(show_telefones)s
        </dl>
        """ % dict(
            nome=obj.__str__(), pk=obj.pk, show_telefones=show_telefones, show_email=show_email
        )
        return mark_safe(out)

    get_info_principal.short_description = "Dados Principais"

    def get_info_cargo(self, obj):
        hoje = datetime.datetime.now()
        out = ["<dl>"]
        if obj.cargo_emprego:
            out.append(f"<dt>Cargo:</dt><dd>{str(obj.cargo_emprego.nome)}</dd>")
        if obj.historico_funcao(hoje, hoje):
            for historico in obj.historico_funcao(hoje, hoje):
                out.append(f"<dt>{historico.funcao_display}:</dt>")
                out.append("<dd>{}</dd>".format(historico.atividade.nome if historico.atividade_id else "Sem Atividade"))
        if obj.situacao:
            if obj.excluido:
                if obj.data_fim_servico_na_instituicao:
                    out.append(
                        '<dt>Situação:</dt><dd>{} <span class="false">(Excluído em {})</span></dd>'.format(
                            obj.situacao, obj.data_fim_servico_na_instituicao.strftime("%d/%m/%Y")
                        )
                    )
                else:
                    out.append(f'<dt>Situação:</dt><dd>{obj.situacao} <span class="false">(Excluído)</span></dd>')
            else:
                out.append(f"<dt>Situação:</dt><dd>{obj.situacao}</dd>")

        out.append("</dl>")
        return mark_safe("".join(out))

    get_info_cargo.short_description = "Cargo/Função/Situação"

    def get_info_funcional(self, obj):
        out = ["<dl>"]

        if obj.setor_lotacao:
            out.append("<dt>SIAPE Lotação:</dt><dd>%s</dd>" % (obj.setor_lotacao.sigla))
        if obj.setor_exercicio:
            out.append("<dt>SIAPE Exercício:</dt><dd>%s</dd>" % (obj.setor_exercicio.sigla))
        if obj.setor:
            out.append("<dt>SUAP:</dt><dd>%s</dd>" % obj.setor.sigla)
        out.append("</dl>")
        return mark_safe("".join(out))

    get_info_funcional.short_description = "Setor"

    def get_foto(self, obj):
        img_src = obj.pessoa_fisica.get_foto_75x100_url()
        return mark_safe(f'<div class="photo-circle"><img src="{img_src}" alt="{obj.__str__()}" /></div>')

    get_foto.short_description = "Foto"

    def to_xls(self, request, queryset, processo):
        header = [
            "#",
            "Matrícula",
            "Nome",
            "E-mail para Contato",
            "Cargo",
            "Funções",
            "Situação",
            "Campus de Lotação",
            "Setor de Lotação",
            "Campus Exercício",
            "Setor Exercício",
            "Campus SUAP",
            "Setor SUAP",
            "Disciplina de Ingresso",
            "Excluído",
        ]
        hoje = datetime.datetime.now()
        rows = [header]
        for idx, servidor in enumerate(processo.iterate(queryset), 1):
            historico_funcao_hoje = ""
            if servidor.historico_funcao(hoje, hoje):
                for historico in servidor.historico_funcao(hoje, hoje):
                    historico_funcao_hoje += (
                        f'{historico.funcao_display}:{historico.atividade.nome if historico.atividade_id else "Sem Atividade"} \n'
                    )
            row = [
                idx,
                servidor.matricula,
                servidor.nome,
                servidor.email,
                servidor.cargo_emprego,
                historico_funcao_hoje,
                servidor.situacao,
                servidor.setor_lotacao.uo if servidor.setor_lotacao else "",
                servidor.setor_lotacao,
                servidor.setor_exercicio.uo if servidor.setor_exercicio else "",
                servidor.setor_exercicio,
                servidor.setor.uo if servidor.setor else "",
                servidor.setor,
                servidor.professor.disciplina if servidor.professor else "",
                "Sim" if servidor.excluido else "Não",
            ]
            rows.append(row)
        return rows


admin.site.register(Servidor, ServidorAdmin)


###############
# Servidor Ocorrencia
###############


class ServidorOcorrenciaAdmin(ModelAdminPlus):
    list_display = ("servidor", "ocorrencia", "data", "data_termino")
    ordering = ("servidor__nome", "data")
    search_fields = ("servidor__matricula", "servidor__nome", "ocorrencia__nome", "ocorrencia__grupo_ocorrencia__nome")


admin.site.register(ServidorOcorrencia, ServidorOcorrenciaAdmin)


class ServidorReativacaoTemporariaAdmin(ModelAdminPlus):
    list_display = ("servidor", "data_inicio", "data_fim")
    ordering = ("servidor__nome", "data_inicio")
    search_fields = ("servidor__matricula", "servidor__nome")
    form = ServidorReativacaoTemporariaForm

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)

        try:
            # Se tiver webservice ele vai tentar reativar pelo webservice
            importador = ImportadorWs()
            cpf = obj.servidor.pessoa_fisica.cpf
            importador.importacao_servidor(cpf, False, False)
            importador.atualizar_ferias_afastamentos(cpf=cpf, ano_inicio=1990)
            servidor = Servidor.objects.get(pk=obj.servidor_id)
            if not servidor.excluido:
                ultimo_historico_setor = servidor.historico_setor_suap().order_by("-pk").first()
                ultimo_historico_setor.data_fim_no_setor = None
                ultimo_historico_setor.save()
                servidor.setor = ultimo_historico_setor.setor
                uo = ultimo_historico_setor.setor.uo
                uo_siape = UnidadeOrganizacional.objects.filter(equivalente=uo).first()
                servidor.setor_exercicio = uo_siape.setor
                servidor.save()
        except ValidationError:
            # Não tem webservice configurado
            servidor = Servidor.objects.get(pk=obj.servidor_id)
            servidor.excluido = False
            servidor.save()

        # Se existir LDAP tem que sincronizar para replicar o status de nao excluido
        try:
            LdapConf = apps.get_model("ldap_backend", "LdapConf")
            conf = LdapConf.get_active()
            conf.sync_user(servidor.get_user())
        except Exception:
            pass


admin.site.register(ServidorReativacaoTemporaria, ServidorReativacaoTemporariaAdmin)


class ServidorSetorHistoricoAdmin(ModelAdminPlus):
    form = ServidorSetorHistoricoForm
    list_display = ("servidor", "setor", "data_inicio_no_setor", "data_fim_no_setor")
    list_filter = ["setor"]
    search_fields = ["servidor__nome", "servidor__matricula", "setor__nome"]
    list_per_page = 20
    list_display_icons = True

    ordering = ("-data_inicio_no_setor", "data_fim_no_setor")


admin.site.register(ServidorSetorHistorico, ServidorSetorHistoricoAdmin)


#########
# Setor #
#########


class SetorTelefoneInline(admin.TabularInline):
    model = SetorTelefone
    extra = 2
    form = SetorTelefoneForm


class SetorSuapSiapeFilter(admin.SimpleListFilter):
    title = "Árvore de Setor"
    parameter_name = "arvore_setor"

    def lookups(self, request, model_admin):
        return [[0, 'Todos'], [1, 'SUAP'], [2, 'SIAPE']]

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == '1':
                return queryset.suap().distinct()
            elif self.value() == '0':
                return queryset.siape().distinct()
        return queryset


class SetorAdmin(ModelAdminPlus):
    form = SetorForm
    add_form = SetorAddForm
    list_display = ("show_info_principal", "get_telefones", "get_chefes", "get_qtd_servidores", "get_jornada", "configuracoes")
    list_filter = ("uo", "excluido", "areas_vinculacao")
    list_display_icons = True
    list_per_page = 20
    export_to_xls = True
    ordering = ("sigla", "nome")
    search_fields = ("sigla", "nome", "codigo")
    inlines = [SetorTelefoneInline]

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        self.list_filter = list_filter + (SetorSuapSiapeFilter,) if request.user.is_superuser else list_filter
        return self.list_filter

    def restringir_queryset(self, request):
        """
        Superusuários podem ver todos os setores, os outros apenas os SUAP.
        """
        return request.user.is_superuser and Setor.todos or Setor.objects

    get_queryset = restringir_queryset

    def configuracoes(self, obj):
        out = ['<ul class="action-bar">']

        # Permissoes do processo e documento eletronico
        # ------------------------------------------------
        chefe_setor_ou_poder_de_chefe = False
        if self.request.user.eh_servidor and "documento_eletronico" in settings.INSTALLED_APPS:
            from processo_eletronico.utils import chefe_ou_com_poder_de_chefe_no_setor

            chefe_setor_ou_poder_de_chefe = chefe_ou_com_poder_de_chefe_no_setor(self.request.user, obj)
            if chefe_setor_ou_poder_de_chefe:
                out.append(
                    "<li>"
                    '<a class="btn primary" href="/processo_eletronico/permissoes/?setor={:d}">Permissões para Documentos e Processos Eletrônicos</a>'
                    "</li>".format(obj.pk)
                )

        # Jornadas de Trabalho
        # ------------------------------------------------
        if self.request.user.has_perm("rh.pode_gerenciar_setor_jornada_historico"):
            out.append(
                '<li><a class="btn primary" href="/rh/setor_jornada_historico/{:d}/">Gerenciamento de Jornadas de Trabalho</a></li>'.format(
                    obj.pk
                )
            )
        out.append("</ul>")

        return mark_safe("".join(out))

    configuracoes.short_description = "Configurações"

    def show_info_principal(self, obj):
        # Principal
        out = [
            """
        <p><strong>%(sigla)s</strong> (%(nome)s)</p>
        <p>%(caminho)s</p>"""
            % dict(sigla=obj.sigla, caminho=obj.get_caminho_as_html(), nome=obj.nome)
        ]

        return mark_safe("".join(out))

    show_info_principal.short_description = "Informações Principais"
    show_info_principal.admin_order_field = "sigla"

    def get_jornada(self, obj):
        return obj.tipo_jornada_trabalho_por_data()

    get_jornada.short_description = "Jornada de Trabalho"

    def get_qtd_servidores(self, obj):

        # Servidores
        qtd_servidores = Servidor.objects.filter(excluido=False, setor=obj).count()
        if qtd_servidores == 0:
            info_servidores = '<span class="status status-error">Nenhum servidor</span>'
        else:
            info_servidores = """
            <a href="/admin/rh/servidor/?excluido__exact=0&setor__id__exact=%d"
               title="Listar servidores">
                %d servidor%s
            </a>""" % (
                obj.pk,
                qtd_servidores,
                qtd_servidores > 1 and "es" or "",
            )
        return mark_safe("%(info_servidores)s" % dict(info_servidores=info_servidores))

    get_qtd_servidores.short_description = "Qtd. de Servidores"

    def get_telefones(self, obj):
        saida = ""
        if obj.setortelefone_set.all().exists():
            telefones = [f"<li>{telefone}</li>" for telefone in obj.setortelefone_set.all()]
            saida = """<ul>{telefones}</ul>""".format(telefones="".join(telefones))

        return mark_safe(saida)

    get_telefones.short_description = "Telefones"

    def get_chefes(self, obj):
        out = []
        for servidor in Servidor.objects.filter(pk__in=obj.historico_funcao().values_list("servidor", flat=True).distinct()):
            out.append(f"<li>{format_user(servidor.get_user())}</li>")
        return mark_safe("<ul>{}</ul>".format("".join(out)))

    get_chefes.short_description = "Chefes"

    def get_form(self, request, obj=None, **kwargs):
        if request.user.is_superuser:
            kwargs["exclude"] = []
        else:
            kwargs["exclude"] = ["codigo"]
        return super().get_form(request, obj=obj, **kwargs)

    def to_xls(self, request, queryset, task):
        header = ["#", "Setor", "Campus", "Telefones", "Chefes do Setor", "Tipo de Jornada Trabalho", "Quantidade de Servidores"]
        rows = [header]
        for idx, obj in enumerate(task.iterate(queryset)):
            uo = obj.uo
            row = [
                idx + 1,
                f"{obj.nome} ({obj.sigla})",
                f"{obj.uo.nome} ({obj.uo.sigla})" if uo else "",
                ",".join([f"{st.numero}(ramal:{st.ramal})" for st in obj.setortelefone_set.all()]),
                ",".join([str(chefe) for chefe in obj.chefes.all()]),
                obj.tipo_jornada_trabalho_por_data(),
                Servidor.objects.filter(excluido=False, setor=obj).count(),
            ]
            rows.append(row)
        return rows


admin.site.register(Setor, SetorAdmin)


###############
# Situacao
###############


class SituacaoAdmin(ModelAdminPlus):
    list_display = ("nome", "nome_siape", "codigo", "excluido")
    ordering = ("excluido", "nome", "nome_siape", "codigo")
    list_filter = ["excluido"]
    search_fields = ("nome", "nome_siape", "codigo")


admin.site.register(Situacao, SituacaoAdmin)


##########
# Campus #
##########
class TipoUnidadeOrganizacionalAdmin(ModelAdminPlus):
    pass


admin.site.register(TipoUnidadeOrganizacional, TipoUnidadeOrganizacionalAdmin)


class UnidadeOrganizacionalAdmin(ModelAdminPlus):
    list_display = ("id", "nome", "sigla", "codigo_ug", "codigo_ugr", "setor", "municipio", "codigo_protocolo", "show_tipo")
    search_fields = ("setor__sigla", "setor__nome")
    list_display_icons = True

    def get_queryset(self, request, manager=None, *args, **kwargs):
        if request.user.is_superuser:
            queryset = UnidadeOrganizacional.objects
        else:
            queryset = UnidadeOrganizacional.objects.suap()
        return queryset

    def show_tipo(self, obj):
        return mark_safe(obj.setor.codigo and '<span class="false">SIAPE</span>' or '<span class="true">SUAP</span>')

    show_tipo.admin_order_field = "setor__codigo"
    show_tipo.short_description = "Tipo"

    def get_form(self, request, obj=None, **kwargs):
        eh_siape = False
        if not obj:
            setor_qs = Setor.todos.all()
            help_text = "Exibindo todos os setores."
        elif obj and obj.setor.codigo:
            setor_qs = Setor.siape.all()
            eh_siape = True
            help_text = "Exibindo apenas setores SIAPE."
        else:
            setor_qs = Setor.objects.all()
            help_text = "Exibindo apenas setores SUAP."
        if eh_siape:
            self.fieldsets = (
                ("Tipo do Campus", {"fields": ("tipo",)}),
                ("Dados Gerais", {"fields": (("nome", "sigla"), ("setor", "cnpj"), ("codigo_ug", "codigo_ugr"), "equivalente")}),
                ("Endereço", {"fields": ("endereco", ("municipio", "zona_rual"), ("cep", "bairro"))}),
                ("Contato", {"fields": (("telefone", "fax"),)}),
                ("Protocolo", {"fields": ("codigo_protocolo",)}),
                ("Acadêmico", {"fields": (("codigo_inep", "codigo_censup", "codigo_emec"), "portaria_criacao")}),
                ("ConectaGOV - Barramento PEN", {"fields": ("id_repositorio_pen", "id_estrutura_pen")}),
            )

        else:
            self.fieldsets = (
                ("Tipo do Campus", {"fields": ("tipo",)}),
                ("Dados Gerais", {"fields": (("nome", "sigla"), ("setor", "cnpj"), ("codigo_ug", "codigo_ugr"))}),
                ("Endereço", {"fields": (("endereco", "numero"), ("municipio", "zona_rual"), ("cep", "bairro"))}),
                ("Contato", {"fields": (("telefone", "fax"),)}),
                ("Protocolo", {"fields": ("codigo_protocolo",)}),
                ("Acadêmico", {"fields": (("codigo_inep", "codigo_censup"), ("codigo_emec", "codigo_sistec"), "portaria_criacao")}),
                ("ConectaGOV - Barramento PEN", {"fields": ("setor_recebimento_pen", "id_repositorio_pen", "id_estrutura_pen")}),
            )

        class UnidadeOrganizacionalForm(forms.ModelFormPlus):
            class Meta:
                model = UnidadeOrganizacional
                exclude = ()
                if not eh_siape:
                    exclude = ("equivalente",)

            setor = forms.ModelChoiceFieldPlus2(
                queryset=setor_qs, help_text=help_text, label_template="{{ obj }} ({% if obj.codigo %}SIAPE{% else %}SUAP{% endif %})"
            )

            setor_recebimento_pen = forms.ModelChoiceField(
                label="Setor de Recebimento de Processos Externos",
                queryset=Setor.objects.all(),
                required=False,
                widget=AutocompleteWidget(),
            )

        return UnidadeOrganizacionalForm


admin.site.register(UnidadeOrganizacional, UnidadeOrganizacionalAdmin)


#############
# Avaliador #
#############
class AvaliadorInternoExternoFilter(admin.SimpleListFilter):
    title = "Tipo de Avaliador"
    parameter_name = "tipo_avaliador"

    def lookups(self, request, model_admin):
        tipo_avaliador = [[0, "Avaliador Interno"], [1, "Avaliador Externo"]]
        return tipo_avaliador

    def queryset(self, request, queryset):
        if self.value():
            if self.value() == "1":
                return queryset.filter(vinculo__tipo_relacionamento=ContentType.objects.get(Vinculo.SERVIDOR))
            elif self.value() == "0":
                return queryset.filter(vinculo__tipo_relacionamento=ContentType.objects.get(Vinculo.PRESTADOR))
        return queryset


class AvaliadorAdmin(ModelAdminPlus):
    list_display = (
        "get_cpf",
        "get_nome",
        "get_instituicao_origem",
        "get_dados_bancarios",
        "get_foto",
        "avaliacoes_realizadas_no_ano",
        "qtd_perda_prazo_aceite",
        "qtd_perda_prazo_avaliacao",
        "qtd_rejeicao_avaliacao",
        "ativo",
    )
    list_filter = ("ativo", AvaliadorInternoExternoFilter, "instituicao_origem", "banco")
    search_fields = ("vinculo__user__pessoafisica__nome", "vinculo__user__pessoafisica__cpf", "vinculo__user__username")
    form = AvaliadorExternoForm
    list_display_icons = True
    list_per_page = 40
    ordering = ("vinculo__user__pessoafisica__nome",)
    export_to_xls = True

    fieldsets = (
        (
            None,
            {
                "fields": (
                    "matricula_siape",
                    "nome",
                    "cpf",
                    "email",
                    "instituicao_origem",
                    "ativo",
                    "numero_telefone",
                    "titulacao",
                    "padrao_vencimento",
                )
            },
        ),
    )

    def export_to_xls(self, request, queryset, processo):
        header = [
            "#",
            "Matrícula",
            "Nome",
            "Data de Nascimento",
            "CPF",
            "Telefone",
            "E-mail para Contato",
            "Instituição de Origem",
            "Número do Documento de Identificação",
            "Emissor do Documento de Identificação",
            "PIS/PASEP",
            "Logradouro",
            "Número",
            "Município",
            "Complemento",
            "Bairro",
            "CEP",
            "Banco",
            "Número de Agência",
            "Tipo Conta",
            "Número da Conta",
            "Operação",
        ]

        rows = [header]
        queryset = queryset.order_by("vinculo__user__pessoafisica__nome")
        for idx, obj in enumerate(processo.iterate(queryset), 1):
            row = [
                idx,
                obj.get_matricula(),
                obj.vinculo.user.get_profile().nome,
                obj.vinculo.user.get_profile().nascimento_data,
                obj.vinculo.user.get_profile().cpf,
                obj.vinculo.user.get_profile().telefones,
                obj.vinculo.user.get_profile().email,
                obj.instituicao_origem,
                obj.numero_documento_identificacao,
                obj.emissor_documento_identificacao,
                obj.pis_pasep,
                obj.endereco_logradouro,
                obj.endereco_numero,
                obj.endereco_municipio,
                obj.endereco_complemento,
                obj.endereco_bairro,
                obj.endereco_cep,
                obj.banco,
                obj.numero_agencia,
                obj.tipo_conta,
                obj.numero_conta,
                obj.operacao,
            ]
            rows.append(row)
        return rows

    def avaliacoes_realizadas_no_ano(self, obj):
        return obj.avaliacoes_realizadas_no_ano()

    avaliacoes_realizadas_no_ano.short_description = "Avaliações realizadas no ano"

    def get_instituicao_origem(self, obj):
        uasg = obj.instituicao_origem.uasg if obj.instituicao_origem else "-"
        ug = obj.instituicao_origem.unidade_gestora if obj.instituicao_origem else "-"
        out = """
        <dl>
            <dt>Instituição de Origem:</dt><dd>%(instituicao)s</dd>
            <dt>UG:</dt><dd>%(ug)s </dd>
            <dt>UASG:</dt><dd>%(uasg)s </dd>
        </dl>
        """ % dict(
            instituicao=obj.instituicao_origem or "-", ug=ug, uasg=uasg
        )
        return mark_safe(out)

    get_instituicao_origem.short_description = "Instituição Origem"

    def get_dados_bancarios(self, obj):
        banco = obj.banco or "-"
        numero_agencia = obj.numero_agencia or "-"
        numero_conta = obj.numero_conta or "-"
        operacao = obj.operacao or "-"
        out = """
        <dl>
            <dt>Banco:</dt><dd>%(banco)s</dd>
            <dt>Agência:</dt><dd>%(numero_agencia)s </dd>
            <dt>Conta:</dt><dd>%(numero_conta)s </dd>
            <dt>Operação:</dt><dd>%(operacao)s </dd>
        </dl>
        """ % dict(
            banco=banco, numero_agencia=numero_agencia, numero_conta=numero_conta, operacao=operacao
        )
        return mark_safe(out)

    get_dados_bancarios.short_description = "Dados Bancários"

    def qtd_perda_prazo_aceite(self, obj):
        return obj.qtd_perda_prazo_aceite()

    qtd_perda_prazo_aceite.short_description = "Excedeu prazo de aceite"

    def qtd_perda_prazo_avaliacao(self, obj):
        return obj.qtd_perda_prazo_avaliacao()

    qtd_perda_prazo_avaliacao.short_description = "Excedeu prazo de avaliação"

    def qtd_rejeicao_avaliacao(self, obj):
        return obj.qtd_rejeicao_avaliacao()

    qtd_rejeicao_avaliacao.short_description = "Rejeições de avaliação"

    def get_cpf(self, obj):
        return obj.vinculo.user.get_profile().cpf

    get_cpf.short_description = "CPF"

    def get_nome(self, obj):
        return obj.vinculo.user.get_profile().nome

    get_nome.short_description = "Nome"

    def get_foto(self, obj):
        return mark_safe('<img class="foto-miniatura" src="%s"/>' % obj.vinculo.user.get_profile().get_foto_75x100_url())

    get_foto.short_description = "Foto"


admin.site.register(Avaliador, AvaliadorAdmin)


#############
# AreaVinculacao #
#############


class AreaVinculacaoAdmin(ModelAdminPlus):
    list_display = ("id", "ordem", "descricao")
    fields = ("descricao", "ordem")
    form = AreaVinculacaoForm


admin.site.register(AreaVinculacao, AreaVinculacaoAdmin)


class InstituicaoAdmin(ModelAdminPlus):
    list_display = ("nome", "unidade_gestora", "uasg", "ativo")
    ordering = ("ativo", "nome")
    list_filter = ("ativo",)
    search_fields = ("nome",)
    form = InstituicaoForm


admin.site.register(Instituicao, InstituicaoAdmin)


class AcaoSaudeAtivoFilter(admin.SimpleListFilter):
    title = "Ação de Saúde Ativas"
    parameter_name = "acao_saude_ativa"

    def lookups(self, request, model_admin):
        options = [[1, "Sim"], [0, "Não"]]
        return options

    def queryset(self, request, queryset):
        value = 1
        if self.value() and self.value() == "0":
            value = 0

        if value == 1:
            hoje = datetime.datetime.now()
            queryset = queryset.filter(periodo_inscricao_inicio__lte=hoje, periodo_inscricao_fim__gte=hoje)

        return queryset


class AcaoSaudeAdmin(ModelAdminPlus):
    search_fields = ("descricao",)
    list_filter = (AcaoSaudeAtivoFilter,)
    form = AcaoSaudeForm
    list_display_icons = True
    list_display_links = None
    list_display = ("descricao", "data_inicio", "data_fim", "periodo_inscricao_inicio", "periodo_inscricao_fim", "get_dias_semanas")

    fieldsets = (
        ("", {"fields": ("descricao", ("data_inicio", "data_fim"), ("periodo_inscricao_inicio", "periodo_inscricao_fim"), "dias_semanas")}),
    )

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if AcaoSaude.pode_ver_toda_agenda(request.user):
            list_display = list_display + ("get_acoes",)
        else:
            list_display = list_display + ("get_coluna_inscricao_horarios",)
        return list_display

    def get_dias_semanas(self, obj):
        if obj.dias_semanas:
            lista = []
            dias_semanas = eval(obj.dias_semanas)
            for i in range(0, len(dias_semanas)):
                dia_semana = int(dias_semanas[i])
                lista.append(DiaSemanaChoices.DIAS_RESUMIDO_CHOICES[dia_semana - 1][1])
            return ",".join(lista)
        return None

    get_dias_semanas.short_description = "Dias de Semana"

    def get_acoes(self, obj):
        html = '<ul class="action-bar">'
        if (self.request.user.is_superuser or self.request.user.has_perm("rh.add_agendaatendimentohorario")) and obj.em_periodo_inscricao():
            html += f'<li><a href="/rh/adicionar_horario/{obj.id}/" class="btn success">Adicionar Horários</a></li>'

            if obj.agendaatendimentohorario_set.exists():
                html += '<li class="has-child"><a href="#" class="btn success">Agendar</a><ul style="display: none;">'
                for horario in obj.agendaatendimentohorario_set.all().order_by("hora_inicio"):
                    html += '<li><a class="btn" href="/rh/agendar_horario/{}/"> {} ({}) </a></li>'.format(
                        horario.id, horario.horario_atendimento(), horario.profissional
                    )
                html += "</ul></li>"

        html += "</ul>"
        return mark_safe(html)

    get_acoes.short_description = "Opções"

    def get_coluna_inscricao_horarios(self, obj):
        html = "<ul>"
        for horario in obj.agendaatendimentohorario_set.all().order_by("hora_inicio"):
            html += f'<li><a href="/rh/agendar_horario/{horario.id}/"> {horario.horario_atendimento()} </a></li>'
        html += "</ul>"
        return mark_safe(html)

    get_coluna_inscricao_horarios.short_description = "Inscrição"


admin.site.register(AcaoSaude, AcaoSaudeAdmin)


class HorarioAgendadoAdmin(ModelAdminPlus):
    list_display = ("get_icons_actions", "solicitante", "get_acao_saude", "get_horarios", "data_consulta", "cancelado")
    list_display_icons = False
    list_display_links = None
    search_fields = ("solicitante__nome",)
    list_filter = ("horario__acao_saude", "horario__profissional", "cancelado")
    form = AgendarAtendimentoForm

    def get_acao_saude(self, obj):
        return mark_safe(obj.horario.acao_saude)

    get_acao_saude.short_description = "Ação de Saúde"

    def get_horarios(self, obj):
        html = "<ul>"
        html += f"<li>{obj.horario.hora_inicio} às {obj.horario.hora_fim}</li>"
        html += "</ul>"
        return mark_safe(html)

    get_horarios.short_description = "Horários"

    def get_icons_actions(self, obj):
        html = """
                <a href="/rh/cancelar_agendamento/{id}/" class="btn warning confirm">Cancelar</a>
                <a href="/admin/rh/horarioagendado/{id}/delete/" class="btn danger">Deletar</a>
                """.format(
            id=obj.id
        )
        return mark_safe(html)

    get_icons_actions.short_description = "#"


admin.site.register(HorarioAgendado, HorarioAgendadoAdmin)


class AgendaAtendimentoHorarioAdmin(ModelAdminPlus):
    list_display = ("acao_saude", "profissional", "get_periodo", "quantidade_vaga", "get_quantidade_inscritos", "get_acoes")
    search_fields = ("acao_saude__descricao", "profissional__nome")
    list_filter = ("acao_saude",)
    list_display_icons = True
    form = AgendaAtendimentoHorarioForm

    def get_periodo(self, obj):
        return mark_safe("De {} até {}".format(obj.hora_inicio.strftime("%H:%M"), obj.hora_fim.strftime("%H:%M")))

    get_periodo.short_description = "Período"

    def get_quantidade_inscritos(self, obj):
        hoje = datetime.datetime.now()
        return obj.horarioagendado_set.filter(cancelado=False, data_consulta__gte=hoje).count()

    get_quantidade_inscritos.short_description = "Quantidade de Inscritos"

    def get_acoes(self, obj):
        return mark_safe(f'<a href="/rh/agendar_horario/{obj.id}/" class="btn success">Inscrição</a>')

    get_acoes.short_description = "Opções"


admin.site.register(AgendaAtendimentoHorario, AgendaAtendimentoHorarioAdmin)


class DataConsultaBloqueadaAdmin(ModelAdminPlus):
    list_display = ("acao_saude", "data_consulta_bloqueada", "motivo_bloqueio", "houve_remarcacao")
    list_display_icons = True
    fields = ("acao_saude", "data_consulta_bloqueada", "motivo_bloqueio")
    list_filter = ("acao_saude",)
    form = DataConsultaBloqueadaForm


admin.site.register(DataConsultaBloqueada, DataConsultaBloqueadaAdmin)


class PapelAdmin(ModelAdminPlus):
    search_fields = ("pessoa__username", "pessoa__nome", "descricao", "detalhamento")
    list_filter = get_uo_setor_listfilter("setor_suap")
    list_display = ("pessoa", "descricao", "detalhamento", "data_inicio", "data_fim")
    fields = ("pessoa", "descricao", "detalhamento", "data_inicio", "data_fim")
    date_hierarchy = "data_inicio"


admin.site.register(Papel, PapelAdmin)


class CargaHorariaReduzidaAdmin(ModelAdminPlus):
    list_display = ("opcoes", "servidor", "numero", "data_inicio", "data_termino", "status_estilizado")
    search_fields = ("servidor__nome", "servidor__matricula")
    show_count_on_tabs = True
    list_filter = (CustomTabListFilter,)
    change_form_template = "rh/templates/admin/rh/cargahorariareduzida/change_form.html"
    form = ProcessoCargaHorariaReduzidaRHForm

    def opcoes(self, obj):
        html = icon("view", f"/rh/abrir_processo_afastamento_parcial/{obj.id}/")
        if self.has_change_permission(self.request, obj.id):
            html += icon("edit", f"/admin/rh/cargahorariareduzida/{obj.id}/change/")

        if obj.servidor_pode_editar() and self.request.user.get_profile().id == obj.servidor.id:
            html += icon("delete", f"/rh/excluir_processo_afastamento_parcial/{obj.id}/")

        return html

    opcoes.allow_tags = True
    opcoes.short_description = "Ações"

    def status_estilizado(self, obj):
        return mark_safe(obj.status_estilizado)

    status_estilizado.allow_tags = True
    status_estilizado.admin_order_field = "status"
    status_estilizado.short_description = "Situação do Processo"

    def get_tabs(self, request):
        #
        # padrão
        tabs = []
        self.list_display = ("opcoes", "servidor", "tipo", "get_numero", "data_inicio", "data_termino", "status_estilizado")
        """Situaçoes:
        - eh chefe e pertence ao RH
        - eh chefe e nao pertence ao RH
        - nao eh chefe e pertence ao RH
        - nao eh chefe nem pertence ao RH
        """
        if self.existe_minhas_validacoes_como_chefe(request):
            if self._pertence_grupo_coordenador_rh(request):
                # 'eh chefe e RH'
                tabs = [
                    "tab_meus_processos",
                    "tab_processos_validados",
                    "tab_meus_processos_pendentes_de_validacao",
                    "tab_processos_validados_rh",
                    "tab_processos_pendentes_de_validacao_rh",
                ]
            else:
                # 'eh chefe e nao RH'
                tabs = ["tab_meus_processos", "tab_processos_validados", "tab_meus_processos_pendentes_de_validacao"]
        else:
            if self._pertence_grupo_coordenador_rh(request):
                # 'nao eh chefe e pertence ao RH'
                tabs = ["tab_meus_processos", "tab_processos_validados_rh", "tab_processos_pendentes_de_validacao_rh"]
            else:
                # 'nao eh chefe nem pertence ao RH'
                tabs = []
        return tabs

    def response_add(self, request, obj, post_url_continue=None):
        if obj.id:
            return httprr(f"/rh/abrir_processo_afastamento_parcial/{obj.id}/")
        return super().response_add(request, obj, post_url_continue)

    def get_numero(self, obj):
        if obj.protocolo_content_object:
            if obj.protocolo_content_type.app_label == "processo_eletronico":
                return mark_safe(
                    '<a href="/processo_eletronico/processo/{}/" class="popup">{}</a>'.format(
                        obj.protocolo_content_object.id, obj.protocolo_content_object
                    )
                )
            elif obj.protocolo_content_type.app_label == "protocolo":
                return mark_safe(
                    '<a href="/protocolo/processo/{}/" class="popup">{}</a>'.format(
                        obj.protocolo_content_object.id, obj.protocolo_content_object
                    )
                )
        return None

    get_numero.allow_tags = True
    get_numero.short_description = "Número do Processo"

    def has_add_permission(self, request):
        usuario_logado_eh_rh_sistemico = request.user.has_perm("rh.eh_rh_sistemico")
        grupo_coordenador_rh_campus = request.user.has_perm("rh.eh_rh_campus")
        return (
            usuario_logado_eh_rh_sistemico
            or request.user.is_superuser
            or grupo_coordenador_rh_campus
            and ("processo_eletronico" in settings.INSTALLED_APPS or "protocolo" in settings.INSTALLED_APPS)
        )

    def has_change_permission(self, request, obj=None):
        return self.has_add_permission(request)

    def render_view_object(self, request, obj_pk):
        return HttpResponseRedirect(f"/rh/abrir_processo_afastamento_parcial/{obj_pk}/")

    def get_queryset(self, request, manager=None, *args, **kwargs):
        # print 'nao eh chefe nem pertence ao RH'
        qs = super().get_queryset(request, manager, *args, **kwargs)
        return self.regras_filtro_queryset(request, qs)

    def regras_filtro_queryset(self, request, qs):

        usuario_logado_eh_rh_sistemico = in_group(request.user, "Coordenador de Gestão de Pessoas Sistêmico")
        grupo_coordenador_rh_campus = in_group(request.user, "Coordenador de Gestão de Pessoas")
        usuario_logado_campus_sigla = request.user.get_relacionamento().setor.uo.sigla

        """Se for do grupo de RH sistemico ou superuser, pode ver tudo"""
        if usuario_logado_eh_rh_sistemico or request.user.is_superuser:
            return qs.filter(
                Q(status=CargaHorariaReduzida.STATUS_AGUARDANDO_VALIDACAO_RH)
                | Q(status=CargaHorariaReduzida.STATUS_DEFERIDO_PELO_RH)
                | Q(status=CargaHorariaReduzida.STATUS_INDEFERIDO_PELO_RH)
                | Q(status=CargaHorariaReduzida.STATUS_AGUARDANDO_CADASTRAR_HORARIO)
                | Q(status=CargaHorariaReduzida.STATUS_ALTERANDO_HORARIO)
            )
        elif grupo_coordenador_rh_campus:
            return qs.filter(
                Q(status=CargaHorariaReduzida.STATUS_AGUARDANDO_VALIDACAO_RH)
                | Q(status=CargaHorariaReduzida.STATUS_DEFERIDO_PELO_RH)
                | Q(status=CargaHorariaReduzida.STATUS_INDEFERIDO_PELO_RH)
                | Q(status=CargaHorariaReduzida.STATUS_AGUARDANDO_CADASTRAR_HORARIO)
                | Q(status=CargaHorariaReduzida.STATUS_ALTERANDO_HORARIO)
            ).filter(servidor__setor__uo__sigla=usuario_logado_campus_sigla)
        else:
            """se não for do grupo de RH"""
            raise PermissionDenied

    def existe_minhas_validacoes_como_chefe(self, request):
        eu = request.user.get_profile()
        minhas_validacoes = CargaHorariaReduzida.objects.filter(chefe_imediato_validador=eu)
        minhas_validacoes_pendentes = CargaHorariaReduzida.objects.filter(
            id__in=[hc.id for hc in CargaHorariaReduzida.get_processos_afastamento_aguardando_validacao(chefe_imediato_validador=eu)]
        )
        return minhas_validacoes.exists() or minhas_validacoes_pendentes.exists()

    """tabs de usuário que é chefe"""

    def tab_meus_processos(self, request, queryset):
        eu = request.user.get_profile().sub_instance()
        return queryset.filter(servidor=eu)

    tab_meus_processos.short_description = "Meus processos"

    def tab_processos_validados(self, request, queryset):
        eu = request.user.get_profile()
        return queryset.filter(chefe_imediato_validador=eu)

    tab_processos_validados.short_description = "Processos validados como chefe"

    def tab_meus_processos_pendentes_de_validacao(self, request, queryset):
        eu = request.user.get_profile()
        return queryset.filter(
            id__in=[hc.id for hc in CargaHorariaReduzida.get_processos_afastamento_aguardando_validacao(chefe_imediato_validador=eu)]
        )

    tab_meus_processos_pendentes_de_validacao.short_description = "Processos pendentes de validação do chefe"

    """tabs do usuário que pertence ao grupo de RH"""

    def tab_processos_pendentes_de_validacao_rh(self, request, queryset):
        return queryset.filter(status=CargaHorariaReduzida.STATUS_AGUARDANDO_VALIDACAO_RH).exclude(
            id__in=[hc.id for hc in self.tab_meus_processos(request, queryset)]
        )

    tab_processos_pendentes_de_validacao_rh.short_description = "Processos pendentes de validação do RH"

    def tab_processos_validados_rh(self, request, queryset):
        return queryset.filter(servidor_rh_validador__isnull=False)

    tab_processos_validados_rh.short_description = "Processos validados pelo RH"

    def _pertence_grupo_coordenador_rh(self, request):
        # Grupo de pessoas responsáveis por gerenciar a validação do RH
        grupo_coordenador_sistemico = "Coordenador de Gestão de Pessoas Sistêmico"
        grupo_coordenador_rh_campus = "Coordenador de Gestão de Pessoas"
        user_groups = request.user.groups.values_list("name", flat=1)
        return grupo_coordenador_sistemico in user_groups or grupo_coordenador_rh_campus in user_groups


admin.site.register(CargaHorariaReduzida, CargaHorariaReduzidaAdmin)

######################
# Posicionamento PCA #
######################


class PosicionamentoPCAAdmin(ModelAdminPlus):
    list_display = ("get_servidor", "forma_entrada", "data_inicio_posicionamento_pca", "data_fim_posicionamento_pca")
    list_filter = ("forma_entrada",)
    search_fields = ("pca__servidor__nome", "pca__servidor__matricula")
    list_display_icons = True
    form = PosicionamentoPCAForm

    def get_servidor(self, obj):
        return obj.pca.servidor

    get_servidor.short_description = "Servidor"
    get_servidor.admin_order_field = "pca__servidor__nome"


admin.site.register(PosicionamentoPCA, PosicionamentoPCAAdmin)


class JornadaTrabalhoPCAInline(admin.StackedInline):
    form = JornadaTrabalhoPCAForm
    model = JornadaTrabalhoPCA
    extra = 1


class PCAAdmin(ModelAdminPlus):
    list_display = ("servidor", "data_entrada_pca", "get_jornada_trabalho", "get_regime_juridico", "get_posicionamento_pca")
    list_filter = ("servidor",)
    inlines = [JornadaTrabalhoPCAInline]
    list_display_icons = True
    form = PCAForm

    def get_jornada_trabalho(self, obj):
        html = "<ul>"
        for j in obj.jornadatrabalhopca_set.all():
            html += '<li><a href="/admin/rh/jornadatrabalhopca/{}/">Data Início: {} </a></li>'.format(
                j.id, j.data_inicio_jornada_trabalho_pca
            )
        html += "</ul>"
        return mark_safe(html)

    get_jornada_trabalho.short_description = "Jornada de Trabalho PCA"

    def get_regime_juridico(self, obj):
        html = "<ul>"
        for r in obj.regimejuridicopca_set.all():
            html += '<li><a href="/admin/rh/regimejuridicopca/{}/">Data Início: {} </a></li>'.format(
                r.id, r.data_inicio_regime_juridico_pca
            )
        html += "</ul>"
        return mark_safe(html)

    get_regime_juridico.short_description = "Regime Jurídico PCA"

    def get_posicionamento_pca(self, obj):
        html = "<ul>"
        for p in obj.posicionamentopca_set.all():
            html += '<li><a href="/admin/rh/posicionamentopca/{}/">{} - Data Início: {}</a></li>'.format(
                p.id, p.forma_entrada.descricao, p.data_inicio_posicionamento_pca
            )
        html += "</ul>"
        return mark_safe(html)

    get_posicionamento_pca.short_description = "Posicionamento PCA"


admin.site.register(PCA, PCAAdmin)


class JornadaTrabalhoPCAAdmin(ModelAdminPlus):
    list_display = ("pca", "data_inicio_jornada_trabalho_pca", "data_fim_jornada_trabalho_pca", "qtde_jornada_trabalho_pca")
    list_filter = ("pca__servidor",)
    list_display_icons = True
    search_fields = [f"pca__servidor__{term}" for term in Servidor.SEARCH_FIELDS]
    form = JornadaTrabalhoPCAForm


admin.site.register(JornadaTrabalhoPCA, JornadaTrabalhoPCAAdmin)


class RegimeJuridicoPCAAdmin(ModelAdminPlus):
    form = RegimeJuridicoPCAForm
    list_display = ("pca", "regime_juridico", "data_inicio_regime_juridico_pca", "data_fim_regime_juridico_pca")
    list_display_icons = True
    list_filter = ("pca__servidor",)


admin.site.register(RegimeJuridicoPCA, RegimeJuridicoPCAAdmin)


class AreaConhecimentoAdmin(ModelAdminPlus):
    list_display = ("descricao", "superior")
    ordering = ("superior__descricao", "descricao")

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.filter(superior__isnull=False)


admin.site.register(AreaConhecimento, AreaConhecimentoAdmin)


class AfastamentoSiapeAdmin(ModelAdminPlus):
    list_display = (
        "codigo",
        "sigla",
        "nome",
        "tipo",
        "interrompe_pagamento",
        "interrompe_tempo_servico",
        "suspende_estagio_probatorio",
        "excluido",
    )
    search_fields = ("codigo", "sigla", "nome")
    list_display_icons = True
    list_filter = ("tipo", "interrompe_pagamento", "interrompe_tempo_servico", "suspende_estagio_probatorio", "excluido")


admin.site.register(AfastamentoSiape, AfastamentoSiapeAdmin)


class ServidorAfastamentoSiapeAdmin(ModelAdminPlus):
    list_display = (
        "servidor",
        "afastamento",
        "data_inicio",
        "data_termino",
        "quantidade_dias_afastamento",
        "tem_efeito_financeiro",
        "cancelado",
    )
    search_fields = (
        "servidor__nome",
        "servidor__matricula",
    )
    list_display_icons = True
    list_filter = ("cancelado", "afastamento__interrompe_pagamento", "tem_efeito_financeiro", "servidor__excluido", "afastamento",)


admin.site.register(ServidorAfastamento, ServidorAfastamentoSiapeAdmin)

########################
# Cronograma da Folha
########################


class CronogramaFolhaAdmin(ModelAdminPlus):
    list_display = (
        "get_mes_ano",
        "data_abertura_atualizacao_folha",
        "data_fechamento_processamento_folha",
        "data_consulta_previa_folha",
        "data_abertura_proxima_folha",
    )
    list_display_icons = True
    form = CronogramaFolhaForm

    def get_mes_ano(self, obj):
        return f"{Meses.get_mes(obj.mes)}/{obj.ano.ano}"

    get_mes_ano.short_description = "Mês/Ano"


admin.site.register(CronogramaFolha, CronogramaFolhaAdmin)


class PessoaExternaAdmin(ModelAdminPlus):
    form = PessoaExternaForm
    search_fields = ("nome", "cpf")
    list_display = ("nome", "cpf", "sexo", "email")
    list_filter = ("sexo",)
    list_display_icons = True


admin.site.register(PessoaExterna, PessoaExternaAdmin)


#####################################
# Modelo usado em Progressões
#####################################


class PadraoVencimentoAdmin(ModelAdminPlus):
    list_display = ("categoria", "classe", "posicao_vertical")
    list_filter = ("categoria", "classe")
    list_display_icons = True


admin.site.register(PadraoVencimento, PadraoVencimentoAdmin)


class ExcecaoDadosWSAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ("servidor", "get_campos")
    search_fields = ("servidor__nome",)
    form = ExcecaoDadoWSForm

    def get_campos(self, obj):
        return [i for i in obj.campos.all()]

    get_campos.short_description = "Campos que serão ignorados na atualização via webservice"


admin.site.register(ExcecaoDadoWS, ExcecaoDadosWSAdmin)


class CampoExcecaoDadosWSAdmin(ModelAdminPlus):
    list_display_icons = True
    list_display = ("campo",)


admin.site.register(CampoExcecaoWS, CampoExcecaoDadosWSAdmin)


###############################################
# Solicitação de Alteração de Foto Servidor
###############################################
class SolicitacaoAlteracaoFotoAdmin(ModelAdminPlus):
    list_display = ("get_foto", "get_dados_solicitante", "data_interacao", "responsavel_interacao", "get_situacao", "motivo_rejeicao")
    search_fields = ("solicitante", "responsavel_interacao")
    list_display_icons = True
    form = SolicitacaoAlteracaoFotoForm
    actions = ('validar_em_lote',)
    list_filter = (CustomTabListFilter,)

    def get_dados_solicitante(self, obj):
        out = "<dl>"
        out += f"<dt>Solicitante:</dt><dd>{str(obj.solicitante)}</dd>"
        if obj.solicitante.email:
            out += f"<dt>E-mail:</dt><dd>{str(obj.solicitante.email)}</dd>"
        if obj.solicitante.situacao:
            out += f"<dt>Situação:</dt><dd>{obj.solicitante.situacao}</dd>"
        if obj.solicitante.setor:
            out += f"<dt>Setor:</dt><dd>{str(obj.solicitante.setor)}</dd>"
        out += "</dl>"
        return mark_safe(out)
    get_dados_solicitante.short_description = "Solicitante"
    get_dados_solicitante.admin_order_field = "solicitante"

    def get_situacao(self, obj):
        return obj.get_situacao_html()
    get_situacao.short_description = "Situação"
    get_situacao.admin_order_field = "situacao"

    #
    # só é permitido solicitar alterações de imagem:
    # - se superuser -> sempre
    # - se usuário comum -> se não hover outra solicitação para o mesmo usuário com a situacao "aguardando validação"
    def has_add_permission(self, request):
        has_permission = super().has_add_permission(request)
        if has_permission:
            has_permission = SolicitacaoAlteracaoFoto.pode_solicitar_alteracao_foto(request.user)
        return has_permission

    def tab_aguardando_validacao(self, request, queryset):
        return queryset.filter(situacao=SolicitacaoAlteracaoFoto.AGUARDADO_VALIDACAO)
    tab_aguardando_validacao.short_description = 'Aguardando Validação'

    def tab_validado(self, request, queryset):
        return queryset.filter(situacao=SolicitacaoAlteracaoFoto.VALIDADA)
    tab_validado.short_description = 'Validado'

    def tab_rejeitado(self, request, queryset):
        return queryset.filter(situacao=SolicitacaoAlteracaoFoto.REJEITADA)
    tab_rejeitado.short_description = 'Rejeitado'

    def get_tabs(self, request):
        return ["tab_aguardando_validacao", "tab_validado", "tab_rejeitado"]

    def show_list_display_icons(self, obj):
        out = []
        out.append(icon("view", obj.get_absolute_url()))
        if obj.situacao == SolicitacaoAlteracaoFoto.AGUARDADO_VALIDACAO:
            out.append(icon("edit", f"/admin/rh/solicitacaoalteracaofoto/{obj.id}/"))
        return mark_safe(''.join(out))
    show_list_display_icons.short_description = '#'

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if request.user.has_perm("rh.eh_rh_sistemico"):
            list_display = list_display + ("get_acoes",)
        return list_display

    def get_actions(self, request):
        actions = super().get_actions(request)
        if not request.user.has_perm("rh.eh_rh_sistemico"):
            del actions["validar_em_lote"]
        return actions

    def get_acoes(self, obj):
        if obj.situacao == SolicitacaoAlteracaoFoto.AGUARDADO_VALIDACAO:
            html = '''
            <ul class="action-bar">
                <li><a class="btn success confirm" href="/rh/validaralteracaofoto/%(id)s/"> Validar </a></li>
                <li><a class="btn danger popup no-confirm" href="/rh/rejeitaralteracaofoto/%(id)s/"> Rejeitar </a></li>
            </ul>
            ''' % {'id': obj.id}
            return mark_safe(html)
        return ''
    get_acoes.short_description = 'Ações'

    def validar_em_lote(self, request, queryset):
        try:
            if request.user.has_perm("rh.eh_rh_sistemico"):
                ids = request.POST.getlist('_selected_action')
                if ids:
                    ids = list(map(int, ids))
                qs_solicitacoes = queryset.filter(id__in=ids, situacao=SolicitacaoAlteracaoFoto.AGUARDADO_VALIDACAO)
                if qs_solicitacoes.exists():
                    for solicitacao in qs_solicitacoes:
                        solicitacao.validar(request.user)
                    messages.success(request, 'Solicitações validadas com sucesso.')
        except Exception as ex:
            messages.error(request, ex)
    validar_em_lote.short_description = "Validar em lote"

    def get_queryset(self, request):
        if request.user.has_perm("rh.eh_rh_sistemico"):
            queryset = super().get_queryset(request)
        else:
            solicitante = request.user.get_relacionamento()
            if solicitante:
                queryset = SolicitacaoAlteracaoFoto.objects.filter(solicitante=solicitante)
            else:
                queryset = SolicitacaoAlteracaoFoto.objects.none()
        return queryset

    def get_foto(self, obj):
        img_src = obj.foto.url
        return mark_safe(f'<div class="photo-circle"><img src="{img_src}" alt="{obj.__str__()}" /></div>')
    get_foto.short_description = "Foto"


admin.site.register(SolicitacaoAlteracaoFoto, SolicitacaoAlteracaoFotoAdmin)
