import datetime
from datetime import date

from django.apps import apps
from django.contrib import admin, messages
from django.contrib.admin import helpers
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils.safestring import mark_safe

from ae.forms import (
    DemandaAlunoAtendidaModelForm,
    OfertaPasseForm,
    OfertaTurmaForm,
    OfertaAlimentacaoForm,
    OfertaValorRefeicaoForm,
    OfertaBolsaForm,
    OfertaValorBolsaForm,
    InscricaoModelForm,
    AtendimentoSetorForm,
    ProgramaForm,
    ValorTotalAuxiliosForm,
    ValorTotalBolsasForm,
    HorarioSolicitacaoForm,
    DatasLiberadasForm,
    AcaoEducativaForm,
    AtividadeDiversaForm,
    EditalForm,
    DatasRecessoFeriasForm,
    PeriodoInscricaoForm,
    TipoProgramaForm,
    OpcaoRespostaPerguntaParticipacaoForm,
    OpcaoRespostaInscricaoProgramaForm,
    AgendamentoRefeicaoForm,
    SolicitacaoAuxilioAlunoForm,
    AuxilioEventualForm,
)
from ae.models import (
    CategoriaAlimentacao,
    TipoAtendimentoSetor,
    AtendimentoSetor,
    Idioma,
    OfertaValorRefeicao,
    OfertaValorBolsa,
    DemandaAluno,
    Inscricao,
    DemandaAlunoAtendida,
    Programa,
    OfertaAlimentacao,
    OfertaTurma,
    OfertaBolsa,
    OfertaPasse,
    CategoriaBolsa,
    ValorTotalAuxilios,
    ValorTotalBolsas,
    Caracterizacao,
    BeneficioGovernoFederal,
    TipoEscola,
    SituacaoTrabalho,
    Participacao,
    AgendamentoRefeicao,
    HorarioSolicitacaoRefeicao,
    HistoricoFaltasAlimentacao,
    DatasLiberadasFaltasAlimentacao,
    HistoricoSuspensoesAlimentacao,
    TipoAtividadeDiversa,
    AtividadeDiversa,
    AcaoEducativa,
    ParticipacaoTrabalho,
    SolicitacaoRefeicaoAluno,
    MotivoSolicitacaoRefeicao,
    HorarioJustificativaFalta,
    DatasRecessoFerias,
    Edital,
    PeriodoInscricao,
    TipoPrograma,
    PerguntaInscricaoPrograma,
    OpcaoRespostaInscricaoPrograma,
    PerguntaParticipacao,
    OpcaoRespostaPerguntaParticipacao,
    SolicitacaoAuxilioAluno,
    TipoAuxilioEventual,
    AuxilioEventual,
)
from comum.models import Ano, Configuracao
from comum.utils import get_uo, get_sigla_reitoria
from djtools.contrib.admin import ModelAdminPlus
from djtools.templatetags.filters import in_group, format_
from djtools.templatetags.filters.utils import format_money
from djtools.templatetags.tags import icon
from djtools.utils import httprr
from edu.models import CursoCampus, Modalidade, Turno, MatriculaPeriodo, SituacaoMatriculaPeriodo
from rh.models import UnidadeOrganizacional
from django.conf import settings


class ProgramaAdmin(ModelAdminPlus):
    list_display = ('tipo_programa', 'instituicao', 'get_publico_alvo', 'participantes', 'impedir_solicitacao_beneficio', 'get_is_configuracao_pendente')
    search_fields = ('titulo',)
    list_filter = ('instituicao', 'tipo_programa')
    ordering = ('instituicao', 'tipo_programa__titulo')

    list_display_icons = True
    form = ProgramaForm

    def get_publico_alvo(self, obj):
        lista = list()
        for publico in obj.publico_alvo.all():
            lista.append(publico.sigla)
        return ', '.join(lista)

    get_publico_alvo.short_description = 'Público-Alvo'

    def participantes(self, obj):
        return mark_safe(obj.get_participacoes_abertas().count())

    participantes.short_description = 'Qtd. Participantes'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.groups.filter(name='Nutricionista').exists():
            qs = qs.filter(tipo_programa__sigla=Programa.TIPO_ALIMENTACAO)
            if not get_uo(request.user).setor.sigla == get_sigla_reitoria():
                qs = qs.filter(instituicao=get_uo(request.user))
        else:
            if not request.user.has_perm('ae.pode_ver_relatorios_todos'):
                qs = qs.filter(instituicao=get_uo(request.user))
        return qs

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)

        if not request.user.has_perm('ae.pode_ver_relatorios_todos'):
            if request.user.groups.filter(name='Nutricionista').exists():
                list_filter = tuple()
            else:
                list_filter = ()
        return list_filter

    def get_is_configuracao_pendente(self, obj):
        return format_(obj.estah_configurado())

    get_is_configuracao_pendente.short_description = 'Configuração Realizada?'

    def save_model(self, request, obj, form, change):
        obj.titulo = '{} ({})'.format(form.cleaned_data['tipo_programa'].titulo, form.cleaned_data['instituicao'])
        obj.save()


admin.site.register(Programa, ProgramaAdmin)


class ProgramaFilter(admin.SimpleListFilter):
    title = "Programa"
    parameter_name = "programa"

    def lookups(self, request, model_admin):
        programas = Programa.objects.all()

        if not request.user.has_perm('ae.pode_ver_relatorios_todos'):
            programas = programas.filter(instituicao=get_uo(request.user))

        return [(d.id, d.titulo) for d in programas]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(programa=get_object_or_404(Programa, pk=self.value()))


class EditalFilter(admin.SimpleListFilter):
    title = "Edital"
    parameter_name = "edital"

    def lookups(self, request, model_admin):
        editais = Edital.objects.all()
        return [(d.id, d.__str__()) for d in editais]

    def queryset(self, request, queryset):
        if self.value():
            busca = queryset.filter(periodo_inscricao__edital=get_object_or_404(Edital, pk=self.value()))
            if not request.user.has_perm('ae.pode_ver_relatorios_todos'):
                busca = busca.filter(periodo_inscricao__campus=get_uo(request.user))
            return busca


class DocumentacaoChoices:
    EM_DIA = '1'
    NAO_ENTEGUE = '2'
    EXPIRADA = '3'

    OPCOES = ((EM_DIA, 'Em Dia'), (NAO_ENTEGUE, 'Não Entregue'), (EXPIRADA, 'Expirada'))


class DocumentacaoFilter(admin.SimpleListFilter):
    title = "Documentação"
    parameter_name = "documentacao"

    def lookups(self, request, model_admin):
        return DocumentacaoChoices.OPCOES

    def queryset(self, request, queryset):
        if self.value():
            from comum.utils import somar_data
            prazo_expiracao = Configuracao.get_valor_por_chave('ae', 'prazo_expiracao_documentacao')
            total_dias = prazo_expiracao and int(prazo_expiracao) or 365
            data = somar_data(datetime.datetime.now(), -total_dias)
            if self.value() == DocumentacaoChoices.EM_DIA:
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__documentada=True, aluno__data_documentacao__gte=data)

                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__documentada=True, aluno__data_documentacao__gte=data)

            elif self.value() == DocumentacaoChoices.NAO_ENTEGUE:
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__documentada=False)

                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__documentada=False)

            elif self.value() == DocumentacaoChoices.EXPIRADA:
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__data_documentacao__lt=data)

                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__data_documentacao__lt=data)


class RendaChoices:
    ATE_UM_QUARTO = '1'
    ENTRE_UM_QUARTO_E_MEIO = '2'
    ENTRE_MEIO_E_UM = '3'
    ENTRE_UM_E_UM_MEIO = '4'
    ENTRE_UM_MEIO_E_DOIS = '5'
    ENTRE_DOIS_E_DOIS_MEIO = '6'
    ENTRE_DOIS_MEIO_E_TRES = '7'
    ENTRE_TRES_E_TRES_MEIO = '8'
    ENTRE_TRES_MEIO_E_QUATRO = '9'
    ENTRE_QUATRO_E_QUATRO_MEIO = '10'
    ENTRE_QUATRO_MEIO_E_CINCO = '11'
    MAIOR_QUE_CINCO = '12'
    NAO_INFORMADO = '13'
    IGUAL_0_SM = '14'

    OPCOES = (
        (IGUAL_0_SM, 'Igual a 0 SM'),
        (ATE_UM_QUARTO, 'Até ¼ SM'),
        (ENTRE_UM_QUARTO_E_MEIO, 'Entre ¼ SM e ½ SM'),
        (ENTRE_MEIO_E_UM, 'Entre ½ SM e 1 SM'),
        (ENTRE_UM_E_UM_MEIO, 'Entre 1 SM e 1 ½ SM'),
        (ENTRE_UM_MEIO_E_DOIS, 'Entre 1 ½ SM e 2 SM'),
        (ENTRE_DOIS_E_DOIS_MEIO, 'Entre 2 SM e 2 ½ SM'),
        (ENTRE_DOIS_MEIO_E_TRES, 'Entre 2 ½ SM e 3 SM'),
        (ENTRE_TRES_E_TRES_MEIO, 'Entre 3 SM e 3 ½ SM'),
        (ENTRE_TRES_MEIO_E_QUATRO, 'Entre 3 ½ SM e 4 SM'),
        (ENTRE_QUATRO_E_QUATRO_MEIO, 'Entre 4 SM e 4 ½ SM'),
        (ENTRE_QUATRO_MEIO_E_CINCO, 'Entre 4 ½ SM e 5 SM'),
        (MAIOR_QUE_CINCO, 'Maior que 5 SM'),
        (NAO_INFORMADO, 'Não Informado'),
    )


class RendaFilter(admin.SimpleListFilter):
    title = "Renda per capita"
    parameter_name = "renda"

    def lookups(self, request, model_admin):
        return RendaChoices.OPCOES

    def queryset(self, request, queryset):
        if self.value():
            from comum.models import Configuracao
            from decimal import Decimal

            sm = Decimal(Configuracao.get_valor_por_chave('comum', 'salario_minimo'))
            if self.value() == RendaChoices.IGUAL_0_SM:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).filter(renda_bruta_familiar=0)
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.ATE_UM_QUARTO:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(where=['renda_bruta_familiar/qtd_pessoas_domicilio <= {}/4'.format(sm)])
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.ENTRE_UM_QUARTO_E_MEIO:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
                    where=['renda_bruta_familiar/qtd_pessoas_domicilio > {}/4 AND renda_bruta_familiar/qtd_pessoas_domicilio <= {}/2'.format(sm, sm)]
                )
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.ENTRE_MEIO_E_UM:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
                    where=['renda_bruta_familiar/qtd_pessoas_domicilio > {}/2 AND renda_bruta_familiar/qtd_pessoas_domicilio <= {}'.format(sm, sm)]
                )
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.ENTRE_UM_E_UM_MEIO:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
                    where=['renda_bruta_familiar/qtd_pessoas_domicilio > {} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 1.5*{}'.format(sm, sm)]
                )
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.ENTRE_UM_MEIO_E_DOIS:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
                    where=['renda_bruta_familiar/qtd_pessoas_domicilio > 1.5*{} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 2*{}'.format(sm, sm)]
                )
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.ENTRE_DOIS_E_DOIS_MEIO:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
                    where=['renda_bruta_familiar/qtd_pessoas_domicilio > 2*{} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 2.5*{}'.format(sm, sm)]
                )
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.ENTRE_DOIS_MEIO_E_TRES:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
                    where=['renda_bruta_familiar/qtd_pessoas_domicilio > 2.5*{} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 3*{}'.format(sm, sm)]
                )
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.ENTRE_TRES_E_TRES_MEIO:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
                    where=['renda_bruta_familiar/qtd_pessoas_domicilio > 3*{} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 3.5*{}'.format(sm, sm)]
                )
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.ENTRE_TRES_MEIO_E_QUATRO:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
                    where=['renda_bruta_familiar/qtd_pessoas_domicilio > 3.5*{} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 4*{}'.format(sm, sm)]
                )
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.ENTRE_QUATRO_E_QUATRO_MEIO:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
                    where=['renda_bruta_familiar/qtd_pessoas_domicilio > 4*{} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 4.5*{}'.format(sm, sm)]
                )
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.ENTRE_QUATRO_MEIO_E_CINCO:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
                    where=['renda_bruta_familiar/qtd_pessoas_domicilio > 4.5*{} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 5*{}'.format(sm, sm)]
                )
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.MAIOR_QUE_CINCO:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(where=['renda_bruta_familiar/qtd_pessoas_domicilio > ({} * 5)'.format(sm)])
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))

            elif self.value() == RendaChoices.NAO_INFORMADO:
                caracterizacao = Caracterizacao.objects.filter(qtd_pessoas_domicilio=0)
                if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
                    return queryset.filter(aluno__in=caracterizacao.values_list('aluno', flat=True))
                elif in_group(request.user, 'Assistente Social'):
                    return queryset.filter(programa__instituicao=get_uo(request.user), aluno__in=caracterizacao.values_list('aluno', flat=True))


class CursoFilter(admin.SimpleListFilter):
    title = "Curso"
    parameter_name = "curso"

    def lookups(self, request, model_admin):
        cursos = CursoCampus.objects.filter(ativo=True).order_by('descricao')

        if not request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
            cursos = cursos.filter(diretoria__setor__uo=get_uo(request.user))

        return [(d.id, d.descricao) for d in cursos]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(aluno__curso_campus=CursoCampus.objects.get(pk=self.value()))


class PrimeiraOpcaoFilter(admin.SimpleListFilter):
    title = "Primeira Turma"
    parameter_name = "primeira"

    def lookups(self, request, model_admin):
        opcoes = OfertaTurma.objects.filter(ativa=True)

        return [(d.id, d) for d in opcoes]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(inscricaoidioma__primeira_opcao=self.value())


class SegundaOpcaoFilter(admin.SimpleListFilter):
    title = "Segunda Turma"
    parameter_name = "segunda"

    def lookups(self, request, model_admin):
        opcoes = OfertaTurma.objects.filter(ativa=True)

        return [(d.id, d) for d in opcoes]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(inscricaoidioma__segunda_opcao=self.value())


class ProgramaSocialFilter(admin.SimpleListFilter):
    title = "Programa Social"
    parameter_name = "programasocial"

    def lookups(self, request, model_admin):
        opcoes = BeneficioGovernoFederal.objects.all()

        return [(d.id, d) for d in opcoes]

    def queryset(self, request, queryset):
        if self.value():
            caracterizacoes = Caracterizacao.objects.filter(beneficiario_programa_social=self.value())
            return queryset.filter(aluno__id__in=caracterizacoes.values_list('aluno', flat=True))


class EscolaPublicaFilter(admin.SimpleListFilter):
    title = "Escola de Origem"
    parameter_name = "tipoescola"

    def lookups(self, request, model_admin):
        opcoes = TipoEscola.objects.all()

        return [(d.id, d) for d in opcoes]

    def queryset(self, request, queryset):
        if self.value():
            caracterizacoes = Caracterizacao.objects.filter(Q(escola_ensino_medio=self.value()) | Q(escola_ensino_fundamental=self.value()))
            return queryset.filter(aluno__id__in=caracterizacoes.values_list('aluno', flat=True))


class ResponsavelFinanceiroFilter(admin.SimpleListFilter):
    title = "Situação Financeira do Responsável"
    parameter_name = "situacaoresponsavel"

    def lookups(self, request, model_admin):
        opcoes = SituacaoTrabalho.objects.all()

        return [(d.id, d) for d in opcoes]

    def queryset(self, request, queryset):
        if self.value():
            caracterizacoes = Caracterizacao.objects.filter(responsavel_financeir_trabalho_situacao=self.value())
            return queryset.filter(aluno__id__in=caracterizacoes.values_list('aluno', flat=True))


class ModalidadeFilter(admin.SimpleListFilter):
    title = "Modalidade"
    parameter_name = "modalidade"

    def lookups(self, request, model_admin):
        opcoes = Modalidade.objects.all()

        return [(d.id, d) for d in opcoes]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(aluno__curso_campus__modalidade=self.value())


class OutrosProgramasFilter(admin.SimpleListFilter):
    title = "Participa de algum programa do Serviço Social"
    parameter_name = "progrinstituicao"

    def lookups(self, request, model_admin):
        opcoes = (('1', 'Sim'), ('2', 'Não'))
        return opcoes

    def queryset(self, request, queryset):
        hoje = datetime.date.today()
        participacoes_abertas = Participacao.objects.filter(Q(data_termino__gte=hoje) | Q(data_termino__isnull=True))
        if self.value() == '1':
            return queryset.filter(aluno__in=participacoes_abertas.values_list('aluno', flat=True))
        elif self.value() == '2':
            return queryset.exclude(aluno__in=participacoes_abertas.values_list('aluno', flat=True))


class AnoLetivoFilter(admin.SimpleListFilter):
    title = "Ano Letivo"
    parameter_name = "anoletivo"

    def lookups(self, request, model_admin):
        opcoes = Ano.objects.all()

        return [(d.id, d) for d in opcoes]

    def queryset(self, request, queryset):
        return queryset


class PeriodoLetivoFilter(admin.SimpleListFilter):
    title = "Período Letivo"
    parameter_name = "periodoletivo"

    def lookups(self, request, model_admin):
        opcoes = (('1', '1'), ('2', '2'))
        return opcoes

    def queryset(self, request, queryset):
        return queryset


class TurnoFilter(admin.SimpleListFilter):
    title = "Turno"
    parameter_name = "turno"

    def lookups(self, request, model_admin):
        opcoes = Turno.objects.all()

        return [(d.id, d) for d in opcoes]

    def queryset(self, request, queryset):
        ano = request.GET.get('anoletivo')
        periodo = request.GET.get('periodoletivo')
        if ano and periodo and self.value():
            alunos = MatriculaPeriodo.objects.filter(ano_letivo=ano, periodo_letivo=periodo, turma__turno=self.value())
            return queryset.filter(aluno__in=alunos.values_list('aluno', flat=True))


class SituacaoMatriculaPeriodoFilter(admin.SimpleListFilter):
    title = "Situação da Matrícula no Período"
    parameter_name = "situacaomatricula"

    def lookups(self, request, model_admin):
        opcoes = SituacaoMatriculaPeriodo.objects.all()

        return [(d.id, d) for d in opcoes]

    def queryset(self, request, queryset):
        ano = request.GET.get('anoletivo')
        periodo = request.GET.get('periodoletivo')
        if ano and periodo and self.value():
            alunos = MatriculaPeriodo.objects.filter(ano_letivo=ano, periodo_letivo=periodo, situacao=self.value())
            return queryset.filter(aluno__in=alunos.values_list('aluno', flat=True))


class ParticipanteProgramaFilter(admin.SimpleListFilter):
    title = "Participante do Programa"
    parameter_name = "participanteprograma"

    def lookups(self, request, model_admin):
        opcoes = Programa.objects.all()

        return [(d.id, d) for d in opcoes]

    def queryset(self, request, queryset):
        if self.value():
            programa = Programa.objects.get(id=self.value())
            participacoes_abertas = programa.get_participacoes_abertas()
            return queryset.filter(aluno__in=participacoes_abertas.values_list('aluno', flat=True))


class ParticipanteProgramaDaInscricaoFilter(admin.SimpleListFilter):
    title = " Tem participação ativa no mesmo Programa"
    parameter_name = "participanteprogramadainscricao"

    def lookups(self, request, model_admin):
        return [('Sim', 'Sim'), ('Não', 'Não')]

    def queryset(self, request, queryset):
        if self.value():
            participacoes_abertas = Participacao.abertas.filter(programa__in=queryset.values_list('programa', flat=True))
            ids_inscricoes = list()
            for participacao in participacoes_abertas:
                if queryset.filter(aluno=participacao.aluno, programa=participacao.programa).exists():
                    ids_inscricoes.append(queryset.filter(aluno=participacao.aluno, programa=participacao.programa)[0].id)
            if self.value() == 'Sim':
                return queryset.filter(id__in=ids_inscricoes)
            elif self.value() == 'Não':
                return queryset.exclude(id__in=ids_inscricoes)


class InscricaoAdmin(ModelAdminPlus):
    list_display = ('get_aluno', 'get_programa', 'data_cadastro', 'get_situacao', 'get_documentada', 'get_prioritaria', 'get_selecionada', 'get_participacao', 'get_opcoes')
    list_filter = (
        'programa__instituicao',
        ProgramaFilter,
        'programa__tipo_programa',
        EditalFilter,
        'ativa',
        DocumentacaoFilter,
        RendaFilter,
        'prioritaria',
        CursoFilter,
        ProgramaSocialFilter,
        EscolaPublicaFilter,
        ResponsavelFinanceiroFilter,
        ModalidadeFilter,
        OutrosProgramasFilter,
        ParticipanteProgramaDaInscricaoFilter,
        AnoLetivoFilter,
        PeriodoLetivoFilter,
        TurnoFilter,
        'selecionada',
    )
    search_fields = ('aluno__pessoa_fisica__nome', 'aluno__matricula')
    date_hierarchy = 'data_cadastro'
    exclude = ('ativa', 'documentada', 'prioritaria', 'data_documentacao')

    ordering = ('-data_cadastro',)

    form = InscricaoModelForm

    actions = [
        'registrar_entrega_documentacao',
        'registrar_ausencia_documentacao',
        'adicionar_lista_prioridade',
        'remover_lista_prioridade',
        'adicionar_lista_selecionados',
        'remover_lista_selecionados',
        'ativar_inscricao',
        'inativar_inscricao',
    ]
    actions_on_top = True
    actions_on_bottom = True

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.list_display_links = None

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()

    def change_view(self, request, object_id, form_url='', extra_context=None):
        raise PermissionDenied()

    def changelist_view(self, request, extra_context=None):
        list_filter = self.list_filter
        if request.GET.get('progrinstituicao') and request.GET.get('progrinstituicao') == '1':
            if not ParticipanteProgramaFilter in list_filter:
                list_filter = (
                    'programa__instituicao',
                    ProgramaFilter,
                    'programa__tipo_programa',
                    EditalFilter,
                    'ativa',
                    DocumentacaoFilter,
                    RendaFilter,
                    'prioritaria',
                    CursoFilter,
                    ProgramaSocialFilter,
                    EscolaPublicaFilter,
                    ResponsavelFinanceiroFilter,
                    ModalidadeFilter,
                    OutrosProgramasFilter,
                    ParticipanteProgramaDaInscricaoFilter,
                    ParticipanteProgramaFilter,
                    AnoLetivoFilter,
                    PeriodoLetivoFilter,
                    TurnoFilter,
                    'selecionada',
                )
        else:
            list_filter = (
                'programa__instituicao',
                ProgramaFilter,
                'programa__tipo_programa',
                EditalFilter,
                'ativa',
                DocumentacaoFilter,
                RendaFilter,
                'prioritaria',
                CursoFilter,
                ProgramaSocialFilter,
                EscolaPublicaFilter,
                ResponsavelFinanceiroFilter,
                ModalidadeFilter,
                OutrosProgramasFilter,
                ParticipanteProgramaDaInscricaoFilter,
                AnoLetivoFilter,
                PeriodoLetivoFilter,
                TurnoFilter,
                'selecionada',
            )
        if request.GET.get('programa') and Programa.objects.filter(id=request.GET.get('programa'), tipo_programa__sigla=Programa.TIPO_IDIOMA).exists():
            if not PrimeiraOpcaoFilter in list_filter:
                list_filter += (PrimeiraOpcaoFilter, SegundaOpcaoFilter)
        if request.GET.get('anoletivo') and request.GET.get('periodoletivo'):
            if not TurnoFilter in list_filter:
                list_filter += (TurnoFilter, SituacaoMatriculaPeriodoFilter)
        self.list_filter = list_filter
        if not request.user.has_perm('ae.pode_ver_comprovante_inscricao'):
            if 'get_opcoes' in self.list_display:
                self.list_display = list(self.list_display)
                self.list_display.remove('get_opcoes')
        elif 'get_opcoes' not in self.list_display:
            self.list_display = self.list_display + ['get_opcoes']
        return super().changelist_view(request, extra_context=extra_context)

    def get_aluno(self, obj):
        return mark_safe('{} <a href="{}">({})</a>'.format(obj.aluno.pessoa_fisica.nome, obj.aluno.get_absolute_url(), obj.aluno.matricula))

    get_aluno.admin_order_field = "aluno__pessoa_fisica__nome"
    get_aluno.short_description = 'Aluno'

    def get_programa(self, obj):
        return mark_safe('<a href="{}">{}</a>'.format(obj.programa.get_absolute_url(), obj.programa))

    get_programa.short_description = 'Programa'

    def get_action_bar(self, request):
        items = []
        if self.has_add_permission(request):
            items.append(dict(url='/ae/inscricao_identificacao/', label='Efetuar Inscrição', css_class='success'))
        return items

    def get_actions(self, request):
        if in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            return super().get_actions(request)
        return []

    def add_view(self, request):
        return httprr('/ae/inscricao_identificacao/')

    def delete_view(self, request, object_id):
        result = super().delete_view(request, object_id)
        result['Location'] = "/admin/ae/inscricao/"
        return result

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        Aluno = apps.get_model("edu", "aluno")
        if not request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
            if in_group(request.user, 'Assistente Social'):
                qs = qs.filter(programa__instituicao=get_uo(request.user))
            else:
                qs = qs.filter(aluno=Aluno.objects.get(matricula=request.user.get_relacionamento().matricula))
        return qs

    def get_situacao(self, obj):
        return mark_safe(obj.ativa and '<span class="status status-ativa">Ativa</span>' or '<span class="status status-inativa">Inativa</span>')

    get_situacao.short_description = 'Situação'
    get_situacao.admin_order_field = 'ativa'

    def get_documentada(self, obj):
        return obj.aluno.get_situacao_documentacao()

    get_documentada.short_description = 'Documentação'
    get_documentada.admin_order_field = 'documentada'

    def get_participacao(self, obj):
        return mark_safe(
            obj.get_participacao_aberta() and '<span class="status status-participante">Participante</span>' or '<span class="status status-error">Não participante</span>'
        )

    get_participacao.short_description = 'Participação'

    def get_prioritaria(self, obj):
        return mark_safe(obj.prioritaria and '<span class="status status-alert">Prioritária</span>' or '<span class="status status-info">Normal</span>')

    get_prioritaria.short_description = 'Prioridade'
    get_prioritaria.admin_order_field = 'prioritaria'

    def get_selecionada(self, obj):
        return mark_safe(obj.selecionada and '<span class="status status-success">Sim</span>' or '<span class="status status-error">Não</span>')

    get_selecionada.short_description = 'Seleção'
    get_selecionada.admin_order_field = 'selecionada'

    def get_opcoes(self, obj):
        if self.request.user.groups.filter(name__in=['Assistente Social', 'Coordenador de Atividades Estudantis Sistêmico']):
            texto = '<ul class="action-bar">'
            if obj.parecer:
                texto += '<li><a href="/ae/parecer_inscricao/{:d}/" class="btn primary"><span class="fas fa-edit" aria-hidden="true"></span> Editar Parecer</a></li>'.format(obj.pk)
            else:
                texto += '<li><a href="/ae/parecer_inscricao/{:d}/" class="btn success"><span class="fas fa-plus" aria-hidden="true"></span> Adicionar Parecer</a></li>'.format(obj.pk)

            texto += (
                '<li><a href="/edu/aluno/{}/?tab=atividades_estudantis" class="btn"><span class="fas fa-tasks" aria-hidden="true"></span> Documentação do Aluno</a></li>'
                '<li><a href="/ae/comprovante_inscricao/{:d}/" class="btn default"><span class="fas fa-search" aria-hidden="true"></span> Comprovante de Inscrição</a></li>'
                '</ul>'.format(
                    obj.aluno.matricula, obj.pk
                )
            )
        else:
            texto = '-'
        return mark_safe(texto)

    get_opcoes.short_description = 'Opções'

    # Actions -----------------------------------------------------------------
    def adicionar_lista_selecionados(self, request, queryset):
        if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            messages.error(request, 'Você não tem permissão para realizar este procedimento.')
            return

        total = queryset.count()
        count = queryset.filter(selecionada=False).update(selecionada=True)

        if total == count:
            mensagem = 'Inclusão na lista de selecionadas realizada com sucesso.'
            tag = messages.SUCCESS
        elif total == 1:  # count == 0
            mensagem = 'A inscrição não pôde ser incluída na lista de selecionadas.'
            tag = messages.ERROR
        else:
            mensagem = '{} de {} inscrições incluídas na lista de selecionadas com sucesso.'.format(count, total)
            tag = messages.SUCCESS

        self.message_user(request, mensagem, level=tag)

    adicionar_lista_selecionados.short_description = 'Adicionar à lista de selecionadas'

    def remover_lista_selecionados(self, request, queryset):
        if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            messages.error(request, 'Você não tem permissão para realizar este procedimento.')
            return

        total = queryset.filter(selecionada=True).update(selecionada=False)

        if total == 0:
            mensagem = 'Nenhuma inscrição foi removida da lista de selecionadas.'
        elif total == 1:
            mensagem = '1 inscrição foi removida da lista de selecionadas com sucesso.'
        else:
            mensagem = '{:d} inscrições removidas da lista de selecionadas com sucesso.'.format(total)

        self.message_user(request, mensagem)

    remover_lista_selecionados.short_description = 'Remover da lista de selecionadas'

    def adicionar_lista_prioridade(self, request, queryset):
        if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            messages.error(request, 'Você não tem permissão para realizar este procedimento.')
            return

        total = queryset.count()
        count = queryset.filter(aluno__documentada=True, prioritaria=False).update(prioritaria=True)

        if total == count:
            mensagem = 'Inclusão na lista de prioridades realizada com sucesso.'
            tag = messages.SUCCESS
        elif total == 1:  # count == 0
            mensagem = 'A inscrição não pôde ser incluída na lista de prioridades, pois para isso é necessário que a documentação tenha sido previamente entregue.'
            tag = messages.ERROR
        else:
            mensagem = '{} de {} inscrições incluídas na lista de prioridades com sucesso. Para essa operação é necessário que a documentação tenha sido entregue.'.format(
                count, total
            )
            tag = messages.SUCCESS

        self.message_user(request, mensagem, level=tag)

    adicionar_lista_prioridade.short_description = 'Adicionar à lista de prioridades'

    def remover_lista_prioridade(self, request, queryset):
        if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            messages.error(request, 'Você não tem permissão para realizar este procedimento.')
            return

        total = queryset.filter(prioritaria=True).update(prioritaria=False)

        if total == 0:
            mensagem = 'Nenhuma inscrição foi removida da lista de prioridades.'
        elif total == 1:
            mensagem = '1 inscrição foi removida da lista de prioridades com sucesso.'
        else:
            mensagem = '{:d} inscrições removidas da lista de prioridades com sucesso.'.format(total)

        self.message_user(request, mensagem)

    remover_lista_prioridade.short_description = 'Remover da lista de prioridades'

    def registrar_entrega_documentacao(self, request, queryset):
        if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            messages.error(request, 'Você não tem permissão para realizar este procedimento.')
            return

        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
        return HttpResponseRedirect("/ae/informar_data_entrega_documentacao/?ids={}".format(",".join(selected)))

    registrar_entrega_documentacao.short_description = 'Registrar entrega de documentação'

    def registrar_ausencia_documentacao(self, request, queryset):
        if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            messages.error(request, 'Você não tem permissão para realizar este procedimento.')
            return

        selected = request.POST.getlist(helpers.ACTION_CHECKBOX_NAME)
        return HttpResponseRedirect("/ae/informar_ausencia_documentacao/?ids={}".format(",".join(selected)))

    registrar_ausencia_documentacao.short_description = 'Registrar ausência de documentação'

    def ativar_inscricao(self, request, queryset):
        if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            messages.error(request, 'Você não tem permissão para realizar este procedimento.')
            return

        for inscricao in queryset:
            inscricao.ativa = True
            inscricao.save()
        self.message_user(request, 'Ativação registrada com sucesso.')

    ativar_inscricao.short_description = 'Ativar inscrição'

    def inativar_inscricao(self, request, queryset):
        if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            messages.error(request, 'Você não tem permissão para realizar este procedimento.')
            return

        atendidas = 0
        impedidas = 0
        for inscricao in queryset:
            if inscricao.get_participacao_aberta():
                impedidas += 1
            else:
                atendidas += 1
                inscricao.ativa = False
                inscricao.save()

        mensagem = ''
        if atendidas > 1:
            mensagem = '{} inscrições inativadas.'.format(atendidas)
            tag = messages.SUCCESS
        elif atendidas == 1:
            mensagem = '{} inscrição inativada.'.format(atendidas)
            tag = messages.SUCCESS

        if impedidas == 1:
            mensagem = '{} {} inscrição não foi inativada porque o aluno é participante do programa.'.format(mensagem, impedidas)
            tag = messages.ERROR
        if impedidas > 1:
            mensagem = '{} {} inscricões não foram inativadas porque os alunos são participantes dos programas.'.format(mensagem, impedidas)
            tag = messages.ERROR
        if mensagem:
            self.message_user(request, mensagem, level=tag)

    inativar_inscricao.short_description = 'Inativar inscrição'


admin.site.register(Inscricao, InscricaoAdmin)


class TipoAtendimentoSetorAdmin(ModelAdminPlus):
    list_display = ('nome', 'descricao')
    ordering = ('nome',)
    search_fields = ('nome', 'descricao')
    list_display_icons = True


admin.site.register(TipoAtendimentoSetor, TipoAtendimentoSetorAdmin)


class AtendimentoSetorAdmin(ModelAdminPlus):
    form = AtendimentoSetorForm
    list_display = ('campus', 'tipoatendimentosetor', 'data', 'data_termino', 'valor', 'numero_processo', 'atualizado_por', 'atualizado_em')
    ordering = ('campus', '-data', 'tipoatendimentosetor')
    list_filter = ('tipoatendimentosetor',)
    list_display_icons = True
    date_hierarchy = 'data'
    search_fields = ('tipoatendimentosetor__nome', 'tipoatendimentosetor__descricao', 'observacao', 'numero_processo')

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if request.user.has_perm('ae.pode_detalhar_programa_todos'):
            list_filter = ('campus', 'tipoatendimentosetor')
        return list_filter

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_detalhar_programa_todos'):
            qs = qs.filter(campus=get_uo(request.user))
        return qs

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()


admin.site.register(AtendimentoSetor, AtendimentoSetorAdmin)


class DemandaAlunoAdmin(ModelAdminPlus):
    list_display = ('nome', 'descricao', 'custeio', 'atualizado_por', 'atualizado_em', 'ativa')
    list_filter = ('eh_kit_alimentacao', 'ativa',)
    search_fields = ('nome', 'descricao', 'custeio', 'ativa')
    list_display_icons = True
    add_exclude = ('atualizado_em', 'atualizado_por')

    def add_view(self, *args, **kwargs):
        self.exclude = getattr(self, 'add_exclude', ())
        return super().add_view(*args, **kwargs)

    def change_view(self, *args, **kwargs):
        self.exclude = getattr(self, 'add_exclude', ())
        return super().change_view(*args, **kwargs)

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()


admin.site.register(DemandaAluno, DemandaAlunoAdmin)


class CategoriaAlimentacaoAdmin(ModelAdminPlus):
    list_display = ('nome', 'descricao')
    search_fields = ('nome', 'descricao')
    list_display_icons = True


admin.site.register(CategoriaAlimentacao, CategoriaAlimentacaoAdmin)


class CategoriaBolsaAdmin(ModelAdminPlus):
    list_display = ('nome', 'descricao', 'tipo_bolsa', 'ativa')
    search_fields = ('nome', 'descricao')
    list_filter = ('tipo_bolsa', 'ativa')
    list_display_icons = True


admin.site.register(CategoriaBolsa, CategoriaBolsaAdmin)


class IdiomaAdmin(ModelAdminPlus):
    list_display = ('descricao',)
    search_fields = ('descricao',)


admin.site.register(Idioma, IdiomaAdmin)


class DemandaAlunoFilter(admin.SimpleListFilter):
    title = "Tipo de Atendimento"
    parameter_name = 'demanda'

    def lookups(self, request, model_admin):
        return DemandaAluno.ativas.values_list('id', 'nome')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(demanda=self.value())


class DemandaAlunoAtendidaAdmin(ModelAdminPlus):
    list_display = ('get_acoes', 'demanda', 'get_aluno', 'data', 'get_quantidade', 'valor', 'responsavel_vinculo', 'data_registro', 'terminal', 'get_arquivo')
    date_hierarchy = 'data'
    ordering = ('-data',)
    list_filter = (DemandaAlunoFilter, 'demanda__eh_kit_alimentacao', 'terminal')
    search_fields = ('aluno__pessoa_fisica__nome', 'aluno__matricula')
    form = DemandaAlunoAtendidaModelForm
    list_display_icons = False
    list_per_page = 40

    def get_acoes(self, obj):
        texto = icon('view', '/ae/atendimento/{:d}/'.format(obj.id))
        if self.request.user.has_perm('ae.change_demandaalunoatendida') and (
            not self.request.user.groups.filter(name='Bolsista do Serviço Social') or self.request.user.get_vinculo() == obj.responsavel_vinculo
        ):
            texto = texto + icon('edit', '/admin/ae/demandaalunoatendida/{:d}/change/'.format(obj.id))
        texto = texto + '</ul>'

        return mark_safe(texto)

    get_acoes.short_description = 'Ações'

    def get_aluno(self, obj):
        if self.request.user.groups.filter(name='Nutricionista').exists():
            texto = '{} ({})'.format(obj.aluno.pessoa_fisica.nome, obj.aluno.matricula)
        else:
            texto = '{} <a href="{}">({})</a>'.format(obj.aluno.pessoa_fisica.nome, obj.aluno.get_absolute_url(), obj.aluno.matricula)
        if obj.demanda_id in [DemandaAluno.CAFE, DemandaAluno.ALMOCO, DemandaAluno.JANTAR] and not obj.aluno.pessoa_fisica.template:
            texto += '<span class="status status-error">Sem digital cadastrada</span>'
        return mark_safe(texto)
    get_aluno.short_description = 'Aluno'

    def get_quantidade(self, obj):
        return '{}'.format(obj.quantidade).replace('.0', '')

    get_quantidade.short_description = 'Quantidade'
    get_quantidade.admin_order_field = 'quantidade'

    def get_arquivo(self, obj):
        if obj.arquivo:
            return mark_safe("<a href='{}{}' class='btn default'>Visualizar Arquivo</a>".format(settings.MEDIA_PRIVATE_URL, obj.arquivo))
        return '-'

    get_arquivo.short_description = 'Arquivo'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
            qs = qs.filter(campus=get_uo(request.user))
            if request.user.groups.filter(name='Nutricionista').exists():
                qs = qs.filter(demanda__in=[DemandaAluno.CAFE, DemandaAluno.ALMOCO, DemandaAluno.JANTAR]) | qs.filter(demanda__eh_kit_alimentacao=True)
            if request.user.groups.filter(name='Coordenador de Atividades Estudantis').exists() and not request.user.groups.filter(name__in=['Coordenador de Atividades Estudantis Sistêmico', 'Bolsista do Serviço Social', 'Assistente Social']).exists():
                qs = qs.filter(demanda__eh_kit_alimentacao=True)
        return qs.filter(demanda__ativa=True)

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if request.user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
            list_display = list_display + ('campus',)
        return list_display

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if request.user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
            list_filter = ('demanda', 'campus', 'demanda__eh_kit_alimentacao', 'terminal')
        return list_filter

    def changelist_view(self, request, extra_context=None):
        if get_uo(request.user):
            return super().changelist_view(request, extra_context)
        raise PermissionDenied('Usuário não tem Setor SUAP.')

    def has_change_permission(self, request, obj=None):
        retorno = super().has_change_permission(request, obj)
        if retorno and obj is not None:
            if not request.user.has_perm('ae.change_demandaalunoatendida') or (
                request.user.groups.filter(name='Bolsista do Serviço Social') and not (request.user.get_vinculo() == obj.responsavel_vinculo)
            ):
                retorno = False
        return retorno

    def has_delete_permission(self, request, obj=None):
        retorno = super().has_delete_permission(request)
        if retorno and obj is not None:
            if request.user.has_perm('ae.add_programa') or obj.campus == get_uo(request.user):
                return True
        return False

    def delete_view(self, request, object_id):
        result = super().delete_view(request, object_id)
        result['Location'] = "/ae/lista_alunodemandaatendida/"
        return result


admin.site.register(DemandaAlunoAtendida, DemandaAlunoAtendidaAdmin)


class OfertaAlimentacaoAdmin(ModelAdminPlus):
    form = OfertaAlimentacaoForm
    list_display = (
        'get_campus',
        'dia_inicio',
        'dia_termino',
        'cafe_seg',
        'cafe_ter',
        'cafe_qua',
        'cafe_qui',
        'cafe_sex',
        'almoco_seg',
        'almoco_ter',
        'almoco_qua',
        'almoco_qui',
        'almoco_sex',
        'janta_seg',
        'janta_ter',
        'janta_qua',
        'janta_qui',
        'janta_sex',
    )
    list_display_icons = True
    date_hierarchy = 'dia_inicio'
    fieldsets = (
        ('Localização', {'fields': (('campus',),)}),
        ('Período da Oferta', {'fields': (('dia_inicio', 'dia_termino'),)}),
        ('Café da manhã', {'fields': (('cafe_seg', 'cafe_ter', 'cafe_qua', 'cafe_qui', 'cafe_sex'),)}),
        ('Almoço', {'fields': (('almoco_seg', 'almoco_ter', 'almoco_qua', 'almoco_qui', 'almoco_sex'),)}),
        ('Jantar', {'fields': (('janta_seg', 'janta_ter', 'janta_qua', 'janta_qui', 'janta_sex'),)}),
    )

    def get_campus(self, obj):
        return obj.campus.setor.nome

    get_campus.short_description = 'Campus'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.groups.filter(name='Nutricionista').exists():
            if not get_uo(request.user).setor.sigla == get_sigla_reitoria():
                qs = qs.filter(campus=get_uo(request.user))
        else:
            if not request.user.has_perm('ae.pode_detalhar_programa_todos'):
                qs = qs.filter(campus=get_uo(request.user))
        return qs

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if request.user.has_perm('ae.pode_detalhar_programa_todos'):
            list_filter = ('campus',)

        return list_filter

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        form.base_fields['campus'].queryset = UnidadeOrganizacional.objects.uo()
        return form


admin.site.register(OfertaAlimentacao, OfertaAlimentacaoAdmin)


class OfertaValorRefeicaoAdmin(ModelAdminPlus):
    form = OfertaValorRefeicaoForm
    list_display = ('campus', 'get_valor', 'data_inicio', 'data_termino')
    ordering = ('campus', 'data_inicio')
    list_filter = ('campus',)
    list_display_icons = True
    date_hierarchy = 'data_inicio'

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            list_filter = tuple()
        return list_filter

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            qs = qs.filter(campus=get_uo(request.user))
        return qs

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()

    def get_valor(self, obj):
        return format_money(obj.valor)

    get_valor.short_description = 'Valor Unitário (R$)'


admin.site.register(OfertaValorRefeicao, OfertaValorRefeicaoAdmin)


class OfertaTurmaAdmin(ModelAdminPlus):
    form = OfertaTurmaForm
    list_display = ('campus', 'idioma', 'turma', 'dia1', 'dia2', 'horario1', 'horario2', 'professor', 'ativa', 'numero_vagas')
    ordering = ('ano', 'semestre')
    list_filter = ('campus', 'idioma', 'ano', 'semestre', 'ativa')
    search_fields = ('horario1', 'horario2', 'professor', 'turma')
    list_display_icons = True

    actions = ['ativar_oferta', 'inativar_oferta']
    actions_on_top = True
    actions_on_bottom = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_detalhar_programa_todos'):
            qs = qs.filter(campus=get_uo(request.user))
        return qs

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if not request.user.has_perm('ae.pode_detalhar_programa_todos'):
            list_filter = ('idioma', 'ano', 'semestre', 'ativa')
        return list_filter

    def get_actions(self, request):
        if in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            return super().get_actions(request)
        return []

    def ativar_oferta(self, request, queryset):
        if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            messages.error(request, 'Você não tem permissão para realizar este procedimento.')
            return

        queryset.update(ativa=True)

        self.message_user(request, 'Ativação registrada com sucesso.')

    ativar_oferta.short_description = 'Ativar oferta(s)'

    def inativar_oferta(self, request, queryset):
        if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            messages.error(request, 'Você não tem permissão para realizar este procedimento.')
            return

        queryset.update(ativa=False)

        self.message_user(request, 'Inativação registrada com sucesso.')

    inativar_oferta.short_description = 'Inativar oferta(s)'

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()


admin.site.register(OfertaTurma, OfertaTurmaAdmin)


class OfertaBolsaAdmin(ModelAdminPlus):
    form = OfertaBolsaForm
    list_display = ('get_setor', 'descricao_funcao', 'get_participante', 'campus', 'turno', 'disponivel', 'ativa')
    ordering = ('-disponivel',)
    list_filter = ('setor', 'campus', 'disponivel', 'ativa')
    search_fields = ('descricao_funcao',)
    list_display_icons = True

    actions = ['ativar_oferta', 'inativar_oferta']
    actions_on_top = True
    actions_on_bottom = True

    def get_setor(self, obj):
        return obj.setor.nome

    get_setor.short_description = 'Setor'

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if not request.user.has_perm('ae.pode_detalhar_programa_todos'):
            list_filter = ('disponivel', 'ativa')
        return list_filter

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_detalhar_programa_todos'):
            qs = qs.filter(setor__uo=get_uo(request.user))
        return qs

    def get_actions(self, request):
        if in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            return super().get_actions(request)
        return []

    def ativar_oferta(self, request, queryset):
        if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            messages.error(request, 'Você não tem permissão para realizar este procedimento.')
            return

        queryset.update(ativa=True)

        self.message_user(request, 'Ativação registrada com sucesso.')

    ativar_oferta.short_description = 'Ativar oferta(s)'

    def inativar_oferta(self, request, queryset):
        if not in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico'):
            messages.error(request, 'Você não tem permissão para realizar este procedimento.')
            return

        queryset.update(ativa=False)

        self.message_user(request, 'Inativação registrada com sucesso.')

    inativar_oferta.short_description = 'Inativar oferta(s)'

    def get_participante(self, obj):
        texto = ''
        hoje = date.today()
        participacao = ParticipacaoTrabalho.objects.filter(Q(bolsa_concedida=obj), Q(participacao__data_termino__isnull=True) | Q(participacao__data_termino__gte=hoje))
        if participacao.exists():
            registro = participacao[0]
            texto = texto + '{}, desde {}'.format(registro.participacao.aluno.pessoa_fisica.nome, format_(registro.participacao.data_inicio))
        return mark_safe(texto)

    get_participante.short_description = 'Participante'

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()


admin.site.register(OfertaBolsa, OfertaBolsaAdmin)


class OfertaValorBolsaAdmin(ModelAdminPlus):
    form = OfertaValorBolsaForm
    list_display = ('campus', 'get_valor', 'data_inicio', 'data_termino')
    ordering = ('campus', '-data_inicio')
    list_filter = ('campus',)
    list_display_icons = True
    date_hierarchy = 'data_inicio'

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            list_filter = tuple()
        return list_filter

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            qs = qs.filter(campus=get_uo(request.user))
        return qs

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()

    def get_valor(self, obj):
        return format_money(obj.valor)

    get_valor.short_description = 'Valor Mensal da Bolsa (R$)'


admin.site.register(OfertaValorBolsa, OfertaValorBolsaAdmin)


class OfertaPasseAdmin(ModelAdminPlus):
    form = OfertaPasseForm
    list_display = ('campus', 'get_valor_passe', 'data_inicio', 'data_termino')
    list_display_icons = True
    list_filter = ('campus',)
    date_hierarchy = 'data_inicio'
    ordering = ('campus', '-data_inicio')

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            list_filter = tuple()
        return list_filter

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            qs = qs.filter(campus=get_uo(request.user))
        return qs

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()

    def get_valor_passe(self, obj):
        return format_money(obj.valor_passe)

    get_valor_passe.short_description = 'Recurso Planejado (R$)'


admin.site.register(OfertaPasse, OfertaPasseAdmin)


class ValorTotalAuxiliosAdmin(ModelAdminPlus):
    form = ValorTotalAuxiliosForm
    list_display = ('campus', 'tipoatendimentosetor', 'get_valor', 'data_inicio', 'data_termino')
    ordering = ('campus', '-data_inicio')
    list_filter = ('campus', 'tipoatendimentosetor')
    list_display_icons = True
    date_hierarchy = 'data_inicio'

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            list_filter = tuple()
        return list_filter

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            qs = qs.filter(campus=get_uo(request.user))
        return qs

    def get_valor(self, obj):
        return format_money(obj.valor)

    get_valor.short_description = 'Recurso Planejado (R$)'


admin.site.register(ValorTotalAuxilios, ValorTotalAuxiliosAdmin)


class ValorTotalBolsasAdmin(ModelAdminPlus):
    form = ValorTotalBolsasForm
    list_display = ('campus', 'categoriabolsa', 'get_valor', 'data_inicio', 'data_termino')
    ordering = ('campus', '-data_inicio')
    list_filter = ('campus', 'categoriabolsa')
    list_display_icons = True
    date_hierarchy = 'data_inicio'

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            list_filter = tuple()
        return list_filter

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            qs = qs.filter(campus=get_uo(request.user))
        return qs

    def get_valor(self, obj):
        return format_money(obj.valor)

    get_valor.short_description = 'Recurso Planejado (R$)'


admin.site.register(ValorTotalBolsas, ValorTotalBolsasAdmin)


class AgendamentoRefeicaoAdmin(ModelAdminPlus):
    date_hierarchy = 'data'
    ordering = ('-data', 'aluno', 'tipo_refeicao')
    list_display = ('get_aluno', 'data', 'tipo_refeicao', 'atualizado_por', 'atualizado_em', 'cancelado', 'cancelado_por', 'cancelado_em', 'get_opcoes')
    list_display_icons = False
    list_display_links = None
    list_filter = ('programa__instituicao', 'tipo_refeicao', 'cancelado')
    list_per_page = 50
    search_fields = ('aluno__pessoa_fisica__nome', 'aluno__matricula')
    form = AgendamentoRefeicaoForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.has_perm('ae.pode_ver_listas_todos'):
            return qs
        else:
            return qs.filter(programa__instituicao=get_uo(request.user))

    def get_aluno(self, obj):
        if self.request.user.groups.filter(name='Nutricionista').exists():
            return mark_safe('{} ({})'.format(obj.aluno.pessoa_fisica.nome, obj.aluno.matricula))
        return mark_safe('{} <a href="/edu/aluno/{}/">({})</a>'.format(obj.aluno.pessoa_fisica.nome, obj.aluno.matricula, obj.aluno.matricula))

    get_aluno.short_description = 'Aluno'

    def get_opcoes(self, obj):
        super().get_queryset(self.request)
        hoje = datetime.datetime.today()
        if not obj.cancelado and obj.data >= datetime.datetime(hoje.year, hoje.month, hoje.day, 0, 0, 0) and self.request.user.has_perm('ae.add_solicitacaoalimentacao'):
            return mark_safe('<a href="/ae/remover_agendamento_refeicao/?id={}" class="btn danger">Cancelar</a>'.format(obj.pk))
        return mark_safe('-')

    get_opcoes.short_description = 'Opções'

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()


admin.site.register(AgendamentoRefeicao, AgendamentoRefeicaoAdmin)


class HorarioSolicitacaoRefeicaoAdmin(ModelAdminPlus):
    form = HorarioSolicitacaoForm
    list_display = ('uo', 'tipo_refeicao', 'hora_inicio', 'dia_inicio', 'hora_fim', 'dia_fim')
    list_filter = ('uo',)
    list_display_icons = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.has_perm('ae.pode_ver_listas_todos'):
            return qs
        else:
            return qs.filter(uo=get_uo(request.user))

    def has_add_permission(self, request):
        return request.user.has_perm('ae.pode_ver_listas_campus')

    def has_change_permission(self, request, obj=None):
        retorno = super().has_change_permission(request, obj)
        if retorno and obj is not None:
            if not request.user.has_perm('ae.pode_ver_listas_campus'):
                retorno = False
        return retorno

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()


admin.site.register(HorarioSolicitacaoRefeicao, HorarioSolicitacaoRefeicaoAdmin)


class HorarioJustificativaFaltaAdmin(ModelAdminPlus):
    form = HorarioSolicitacaoForm
    list_display = ('uo', 'tipo_refeicao', 'hora_inicio', 'dia_inicio', 'hora_fim', 'dia_fim')
    list_filter = ('uo',)
    list_display_icons = True

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.has_perm('ae.pode_ver_listas_todos'):
            return qs
        else:
            uo = request.user.get_vinculo().setor.uo
            return qs.filter(uo=uo)

    def has_add_permission(self, request):
        return request.user.has_perm('ae.pode_ver_listas_campus')

    def has_change_permission(self, request, obj=None):
        retorno = super().has_change_permission(request, obj)
        if retorno and obj is not None:
            if not request.user.has_perm('ae.pode_ver_listas_campus'):
                retorno = False
        return retorno

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()


admin.site.register(HorarioJustificativaFalta, HorarioJustificativaFaltaAdmin)


class CampusFilter(admin.SimpleListFilter):
    title = "Campus"
    parameter_name = 'descricao'

    def lookups(self, request, model_admin):

        if request.user.has_perm('ae.pode_ver_listas_todos'):
            campus = UnidadeOrganizacional.objects.uo().all()
        else:
            campus_usuario = get_uo(request.user)
            if campus_usuario:
                campus = UnidadeOrganizacional.objects.uo().filter(id=campus_usuario.id)
            else:
                campus = UnidadeOrganizacional.objects.none()
        return campus.values_list('id', 'sigla')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(aluno__curso_campus__diretoria__setor__uo=self.value())


class JustificadaFilter(admin.SimpleListFilter):
    title = "Justificada"
    parameter_name = 'justificada'

    def lookups(self, request, model_admin):
        opcoes = (('1', 'Sim'), ('2', 'Não'))

        return opcoes

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(justificativa__isnull=False)
        elif self.value() == '2':
            return queryset.filter(justificativa__isnull=True)


class CategoriaFilter(admin.SimpleListFilter):
    title = "Categoria"
    parameter_name = 'categoria'

    def lookups(self, request, model_admin):
        opcoes = (('1', 'Participantes'), ('2', 'Agendados'))

        return opcoes

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(participacao__isnull=False)
        elif self.value() == '2':
            return queryset.filter(participacao__isnull=True)


class HistoricoFaltasAlimentacaoAdmin(ModelAdminPlus):
    list_display = ('aluno', 'tipo_refeicao', 'data', 'justificativa', 'justificada_em')
    date_hierarchy = 'data'
    ordering = ('-data',)
    list_filter = (CampusFilter, 'tipo_refeicao', JustificadaFilter, CategoriaFilter)
    list_display_icons = False
    list_display_links = None
    search_fields = ('aluno__pessoa_fisica__nome', 'aluno__matricula')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.has_perm('ae.pode_ver_listas_todos'):
            return qs
        else:
            return qs.filter(aluno__curso_campus__diretoria__setor__uo=get_uo(request.user))

    def has_add_permission(self, request):
        return False


admin.site.register(HistoricoFaltasAlimentacao, HistoricoFaltasAlimentacaoAdmin)


class DatasLiberadasFaltasAlimentacaoAdmin(ModelAdminPlus):
    form = DatasLiberadasForm
    list_display = ('campus', 'data', 'recorrente', 'atualizado_por_vinculo', 'atualizado_em')
    ordering = ('campus', '-data')
    list_filter = ('campus', 'recorrente')
    list_display_icons = True
    list_display_links = None
    date_hierarchy = 'data'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.has_perm('ae.pode_ver_listas_todos'):
            return qs
        else:
            return qs.filter(campus=get_uo(request.user))

    def has_add_permission(self, request):
        return request.user.has_perm('ae.pode_ver_listas_campus')

    def has_change_permission(self, request, obj=None):
        retorno = super().has_change_permission(request, obj)
        if retorno and obj is not None:
            if not request.user.has_perm('ae.pode_ver_listas_campus') and not request.user.has_perm('ae.add_programa'):
                retorno = False
        return retorno

    def save_model(self, request, obj, form, change):
        obj.atualizado_por_vinculo = request.user.get_vinculo()
        obj.atualizado_em = datetime.datetime.now()
        obj.save()


admin.site.register(DatasLiberadasFaltasAlimentacao, DatasLiberadasFaltasAlimentacaoAdmin)


class HistoricoSuspensoesCampusFilter(admin.SimpleListFilter):
    title = "Campus"
    parameter_name = 'descricao'

    def lookups(self, request, model_admin):
        if request.user.has_perm('ae.pode_ver_listas_todos'):
            campus = UnidadeOrganizacional.objects.uo().all()
        else:
            campus = UnidadeOrganizacional.objects.uo().filter(id=get_uo(request.user).id)
        return campus.values_list('id', 'sigla')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(participacao__aluno__curso_campus__diretoria__setor__uo=self.value())


class HistoricoSuspensoesAlimentacaoAdmin(ModelAdminPlus):
    list_display = ('get_aluno', 'data_inicio', 'data_termino', 'get_liberado_por_vinculo')
    date_hierarchy = 'data_inicio'
    ordering = ('-data_inicio',)
    list_filter = (HistoricoSuspensoesCampusFilter,)
    list_display_icons = False
    list_display_links = None
    search_fields = ('participacao__aluno__pessoa_fisica__nome', 'participacao__aluno__matricula')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.has_perm('ae.pode_ver_listas_todos'):
            return qs
        else:
            return qs.filter(participacao__aluno__curso_campus__diretoria__setor__uo=get_uo(request.user))

    def has_add_permission(self, request):
        return False

    def get_aluno(self, obj):
        return mark_safe(obj.participacao.aluno)

    get_aluno.short_description = 'Aluno'

    def get_liberado_por_vinculo(self, obj):
        return '{} - {}'.format(obj.liberado_por_vinculo.pessoa.nome, obj.liberado_por_vinculo.relacionamento.matricula)

    get_liberado_por_vinculo.short_description = 'Responsável pela Liberação'


admin.site.register(HistoricoSuspensoesAlimentacao, HistoricoSuspensoesAlimentacaoAdmin)


class TipoAtividadeDiversaAdmin(ModelAdminPlus):
    list_display = ('nome',)
    search_fields = ('nome',)
    list_display_icons = True


admin.site.register(TipoAtividadeDiversa, TipoAtividadeDiversaAdmin)


class AtividadeDiversaAdmin(ModelAdminPlus):
    list_display = ('tipo', 'data_inicio', 'data_termino', 'cancelada', 'atualizado_por_vinculo', 'atualizado_em', 'get_opcoes')
    list_filter = ('tipo', 'data_inicio', 'data_termino', 'cadastrado_por', 'cancelada')
    search_fields = ('observacao',)
    list_display_icons = True
    ordering = ('-data_inicio',)

    form = AtividadeDiversaForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
            qs = qs.filter(campus=get_uo(request.user))
        return qs

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if request.user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
            list_display = ('tipo', 'data_inicio', 'data_termino', 'campus', 'cancelada', 'get_opcoes')
        return list_display

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if request.user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
            list_filter = ('campus', 'tipo', 'data_inicio', 'data_termino', 'cadastrado_por')
        return list_filter

    def get_opcoes(self, obj):
        if not obj.cancelada:
            texto = '<ul class="action-bar"><li><a href="/ae/cancelar_atividade_diversa/{}/" class="btn danger">Inativar</a></li></ul>'.format(obj.pk)
        else:
            texto = '<ul class="action-bar"><li><a href="/ae/cancelar_atividade_diversa/{}/" class="btn success">Ativar</a></li></ul>'.format(obj.pk)
        return mark_safe(texto)

    get_opcoes.short_description = 'Opções'

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por_vinculo = request.user.get_vinculo()
        obj.save()


admin.site.register(AtividadeDiversa, AtividadeDiversaAdmin)


class AcaoEducativaAdmin(ModelAdminPlus):
    list_display = ('titulo', 'data_inicio', 'data_termino', 'cancelada', 'atualizado_por_vinculo', 'atualizado_em', 'get_opcoes')
    list_filter = ('data_inicio', 'data_termino', 'cadastrado_por', 'cancelada')
    search_fields = ('titulo', 'descricao')
    list_display_icons = True
    ordering = ('-data_inicio',)

    form = AcaoEducativaForm

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
            qs = qs.filter(campus=get_uo(request.user))
        return qs

    def get_list_display(self, request):
        list_display = super().get_list_display(request)
        if request.user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
            list_display = ('titulo', 'data_inicio', 'data_termino', 'campus', 'cancelada', 'get_opcoes')
        return list_display

    def get_list_filter(self, request):
        list_filter = super().get_list_filter(request)
        if request.user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
            list_filter = ('campus', 'data_inicio', 'data_termino', 'cadastrado_por')
        return list_filter

    def get_opcoes(self, obj):
        if not obj.cancelada:
            texto = '<ul class="action-bar"><li><a href="/ae/cancelar_acao_educativa/{}/" class="btn danger">Inativar</a></li></ul>'.format(obj.pk)
        else:
            texto = '<ul class="action-bar"><li><a href="/ae/cancelar_acao_educativa/{}/" class="btn success">Ativar</a></li></ul>'.format(obj.pk)
        return mark_safe(texto)

    get_opcoes.short_description = 'Opções'

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por_vinculo = request.user.get_vinculo()
        obj.save()


admin.site.register(AcaoEducativa, AcaoEducativaAdmin)


class CampusSolicitacaoRefeicaoFilter(admin.SimpleListFilter):
    title = "Campus"
    parameter_name = 'uo'

    def lookups(self, request, model_admin):

        if request.user.has_perm('ae.pode_ver_solicitacao_refeicao'):
            campus = UnidadeOrganizacional.objects.uo().all()
        else:
            campus = UnidadeOrganizacional.objects.uo().filter(id=get_uo(request.user).id)
        return campus.values_list('id', 'sigla')

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(programa__instituicao=self.value())


class SolicitacaoRefeicaoDeferidaFilter(admin.SimpleListFilter):
    title = "Situação"
    parameter_name = 'situacao'

    def lookups(self, request, model_admin):
        OPCOES = (('1', 'Deferidas'), ('2', 'Indeferidas'), ('3', 'Aguardando Avaliação'))
        return OPCOES

    def queryset(self, request, queryset):
        if self.value() == '1':
            return queryset.filter(deferida=True)
        elif self.value() == '2':
            return queryset.filter(deferida=False)
        if self.value() == '3':
            return queryset.filter(deferida__isnull=True)


class SolicitacaoRefeicaoAlunoAdmin(ModelAdminPlus):
    list_display = ('get_campus_aluno', 'programa', 'aluno', 'data_auxilio', 'data_solicitacao', 'tipo_refeicao', 'motivo_solicitacao', 'get_deferida', 'get_avaliador')
    date_hierarchy = 'data_auxilio'
    ordering = ('-data_auxilio', '-data_solicitacao', 'programa', 'aluno')
    list_filter = (CampusSolicitacaoRefeicaoFilter, 'programa', 'tipo_refeicao', SolicitacaoRefeicaoDeferidaFilter)
    list_per_page = 50
    list_display_icons = False
    list_display_links = None

    def get_queryset(self, request):
        qs = super().get_queryset(request)

        if request.user.has_perm('ae.pode_ver_solicitacao_refeicao'):
            return qs
        else:
            return qs.filter(programa__instituicao=get_uo(request.user))

    def get_campus_aluno(self, obj):
        return obj.programa.instituicao

    get_campus_aluno.short_description = 'Campus'

    def get_avaliador(self, obj):
        if obj.avaliador_vinculo:
            return '{} - {}'.format(obj.avaliador_vinculo.pessoa.nome, obj.avaliador_vinculo.relacionamento.matricula)
        else:
            return '-'

    get_avaliador.short_description = 'Avaliador'

    def get_deferida(self, obj):
        if obj.deferida:
            return mark_safe('<span class="status status-success">Deferida</span>')
        elif obj.deferida == False:
            return mark_safe('<span class="status status-error">Indeferida</span>')
        elif obj.deferida is None:
            return mark_safe('<span class="status status-alert">Aguardando avaliação</span>')

    get_deferida.short_description = 'Situação'


admin.site.register(SolicitacaoRefeicaoAluno, SolicitacaoRefeicaoAlunoAdmin)


class EditalAdmin(ModelAdminPlus):
    list_display = ('descricao', 'get_tipos_programas', 'link_edital', 'ativo', 'get_opcoes')
    list_filter = ('ativo',)
    search_fields = ('descricao',)
    list_display_icons = True
    form = EditalForm

    def get_tipos_programas(self, obj):
        programas = list()
        for programa in obj.tipo_programa.all():
            programas.append(programa.titulo)
        return ', '.join(programas)

    get_tipos_programas.short_description = 'Tipos de Programas'

    def get_opcoes(self, obj):
        texto = '<ul class="action-bar">'
        if obj.ativo:
            texto = texto + '<li><a href="/ae/alterar_situacao_edital/{:d}/" class="btn danger">Inativar</a></li>'.format(obj.pk)
        else:
            texto = texto + '<li><a href="/ae/alterar_situacao_edital/{:d}/" class="btn success">Ativar</a></li>'.format(obj.pk)

        return mark_safe(texto)

    get_opcoes.short_description = 'Opções'


admin.site.register(Edital, EditalAdmin)


class PeriodoAtivoFilter(admin.SimpleListFilter):
    title = "Ativo"
    parameter_name = 'ativo'

    def lookups(self, request, model_admin):
        OPCOES = (('1', 'Sim'), ('2', 'Não'))
        return OPCOES

    def queryset(self, request, queryset):
        hoje = datetime.datetime.now().date()
        if self.value() == '1':
            return queryset.filter(data_inicio__lte=hoje, data_termino__gte=hoje)
        elif self.value() == '2':
            return queryset.filter(Q(data_inicio__gt=hoje) | Q(data_termino__lt=hoje))


class PeriodoInscricaoAdmin(ModelAdminPlus):
    list_display = ('campus', 'edital', 'get_programa', 'data_inicio', 'data_termino', 'apenas_participantes')
    list_filter = ('campus', 'edital', PeriodoAtivoFilter)
    search_fields = ('edital__descricao',)
    list_display_icons = True
    ordering = ('-data_inicio',)
    form = PeriodoInscricaoForm

    def get_programa(self, obj):
        programas = list()
        for programa in obj.programa.all():
            programas.append(programa.titulo)
        return ', '.join(programas)

    get_programa.short_description = 'Programas'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
            qs = qs.filter(campus=get_uo(request.user))
        return qs

    def save_model(self, request, obj, form, change):
        if form.cleaned_data.get('inativar_inscricoes'):
            for programa in form.cleaned_data.get('programa'):
                Inscricao.objects.filter(programa=programa).update(ativa=False)
        obj.save()


admin.site.register(PeriodoInscricao, PeriodoInscricaoAdmin)


class MotivoSolicitacaoRefeicaoAdmin(ModelAdminPlus):
    list_display = ('descricao', 'ativo')
    list_filter = ('ativo',)
    ordering = ('-descricao',)
    list_display_icons = True
    search_fields = ('descricao',)


admin.site.register(MotivoSolicitacaoRefeicao, MotivoSolicitacaoRefeicaoAdmin)


class DatasRecessoFeriasAdmin(ModelAdminPlus):
    form = DatasRecessoFeriasForm
    list_display = ('campus', 'data', 'atualizado_por', 'atualizado_em')
    list_filter = ('campus',)
    ordering = ('campus', '-data')
    list_display_icons = True
    list_display_links = None
    date_hierarchy = 'data'

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if not request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
            qs = qs.filter(campus=get_uo(request.user))
        return qs

    def save_model(self, request, obj, form, change):
        obj.atualizado_em = datetime.datetime.now()
        obj.atualizado_por = request.user.get_vinculo()
        obj.save()


admin.site.register(DatasRecessoFerias, DatasRecessoFeriasAdmin)


class TipoProgramaAdmin(ModelAdminPlus):
    list_display = ('titulo', 'descricao', 'ativo')
    ordering = ('titulo',)
    search_fields = ('titulo', 'descricao')
    list_display_icons = True
    form = TipoProgramaForm


admin.site.register(TipoPrograma, TipoProgramaAdmin)


class PerguntaInscricaoProgramaAdmin(ModelAdminPlus):
    list_display = ('ordem', 'tipo_programa', 'pergunta', 'tipo_resposta', 'obrigatoria', 'ativo')
    ordering = ('tipo_programa', 'pergunta')
    search_fields = ('pergunta__pergunta', 'descricao')
    list_filter = ('tipo_programa', 'tipo_resposta', 'obrigatoria', 'ativo')
    list_display_icons = True


admin.site.register(PerguntaInscricaoPrograma, PerguntaInscricaoProgramaAdmin)


class OpcaoRespostaInscricaoProgramaAdmin(ModelAdminPlus):
    list_display = ('get_programa', 'pergunta', 'valor', 'ativo')
    ordering = ('pergunta',)
    search_fields = ('pergunta__pergunta', 'valor', )
    list_filter = ('pergunta', 'ativo')
    list_display_icons = True
    form = OpcaoRespostaInscricaoProgramaForm

    def get_programa(self, obj):
        return obj.pergunta.tipo_programa.titulo

    get_programa.short_description = 'Programa'


admin.site.register(OpcaoRespostaInscricaoPrograma, OpcaoRespostaInscricaoProgramaAdmin)


class PerguntaParticipacaoAdmin(ModelAdminPlus):
    list_display = ('tipo_programa', 'pergunta', 'tipo_resposta', 'obrigatoria', 'eh_info_financeira', 'ativo')
    ordering = ('tipo_programa', 'pergunta')
    search_fields = ('pergunta', )
    list_filter = ('tipo_programa', 'tipo_resposta', 'obrigatoria', 'ativo')
    list_display_icons = True


admin.site.register(PerguntaParticipacao, PerguntaParticipacaoAdmin)


class OpcaoRespostaPerguntaParticipacaoAdmin(ModelAdminPlus):
    list_display = ('get_programa', 'pergunta', 'valor', 'ativo')
    ordering = ('pergunta',)
    search_fields = ('pergunta__pergunta', 'valor')
    list_filter = ('pergunta', 'ativo')
    list_display_icons = True
    form = OpcaoRespostaPerguntaParticipacaoForm

    def get_programa(self, obj):
        return obj.pergunta.tipo_programa.titulo

    get_programa.short_description = 'Programa'


admin.site.register(OpcaoRespostaPerguntaParticipacao, OpcaoRespostaPerguntaParticipacaoAdmin)


class TipoAuxilioEventualAdmin(ModelAdminPlus):
    list_display = ('nome', 'descricao', 'ativo')
    list_filter = ('ativo',)
    search_fields = ('nome', 'descricao', 'ativo')
    list_display_icons = True


admin.site.register(TipoAuxilioEventual, TipoAuxilioEventualAdmin)


class SolicitacaoAuxilioAlunoAdmin(ModelAdminPlus):
    list_display = ('get_campus', 'aluno', 'tipo_auxilio', 'data_solicitacao', 'get_comprovante', 'get_situacao', 'get_parecer_avaliacao', 'get_opcoes')
    ordering = ('aluno',)
    list_filter = (CampusFilter, 'deferida')
    list_display_icons = True
    search_fields = ('aluno__pessoa_fisica__nome', 'aluno__matricula')
    form = SolicitacaoAuxilioAlunoForm
    date_hierarchy = 'data_solicitacao'

    def get_situacao(self, obj):
        if obj.deferida:
            return mark_safe('<span class="status status-success">Deferida</span>')
        elif obj.deferida == False:
            return mark_safe('<span class="status status-error">Indeferida</span>')
        elif obj.deferida is None:
            return mark_safe('<span class="status status-alert">Aguardando avaliação</span>')

    get_situacao.short_description = 'Situação'

    def get_campus(self, obj):
        return obj.aluno.curso_campus.diretoria.setor.uo

    get_campus.short_description = 'Campus'

    def get_comprovante(self, obj):
        if obj.comprovante:
            return mark_safe("<a href='{}{}' class='btn default'>Visualizar Arquivo</a>".format(settings.MEDIA_PRIVATE_URL, obj.comprovante))
        return '-'

    get_comprovante.short_description = 'Comprovantes'

    def get_parecer_avaliacao(self, obj):
        if obj.parecer_avaliacao:
            return mark_safe('{} <small>{} em {}</small>'.format(obj.parecer_avaliacao, obj.avaliador_vinculo.pessoa.nome, obj.data_avaliacao.strftime("%d/%m/%Y")))
        return '-'

    get_parecer_avaliacao.short_description = 'Parecer'

    def get_opcoes(self, obj):
        if self.request.user.has_perm('ae.pode_abrir_inscricao_do_campus'):
            texto = '<ul class="action-bar">'
            if obj.deferida is None:
                texto = texto + '<li><a href="/ae/avaliar_solicitacao_auxilio/{:d}/" class="btn success">Avaliar</a></li></ul>'.format(obj.pk)
            else:
                texto = texto + '<li><a href="/ae/avaliar_solicitacao_auxilio/{:d}/" class="btn primary">Editar Avaliação</a></li></ul>'.format(obj.pk)

            return mark_safe(texto)
        return '-'

    get_opcoes.short_description = 'Opções'

    def has_add_permission(self, request, obj=None):
        return request.user.eh_aluno and request.user.has_perm('ae.add_solicitacaoauxilioaluno')

    def has_change_permission(self, request, obj=None):
        retorno = super().has_change_permission(request, obj)
        if obj and not request.user.has_perm('ae.add_solicitacaoauxilioaluno'):
            retorno = False
        if obj and obj.aluno == request.user.get_relacionamento() and obj.deferida is not None:
            retorno = False
        return retorno

    def has_view_permission(self, request, obj=None):
        super().has_view_permission(request, obj)
        return (not request.user.has_perm('ae.add_solicitacaoauxilioaluno')) or (obj and obj.aluno == request.user.get_relacionamento())

    def add_view(self, request):
        if request.user.eh_aluno and request.user.has_perm('ae.add_solicitacaoauxilioaluno'):
            aluno = request.user.get_relacionamento()
            if not Caracterizacao.objects.filter(aluno=aluno).exists():
                return httprr(f'/ae/caracterizacao/{aluno.pk}/', 'Por favor, efetue sua caracterização social antes de solicitar o auxílio.', tag='error')
            else:
                return super().add_view(request)
        else:
            return httprr('/admin/ae/solicitacaoauxilioaluno/', 'Permissão negada.', tag='error')

    def save_model(self, request, obj, form, change):
        obj.aluno = request.user.get_relacionamento()
        obj.save()

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        if request.user.has_perm('ae.add_solicitacaoauxilioaluno') and request.user.eh_aluno:
            qs = qs.filter(aluno=request.user.get_relacionamento())
        elif not request.user.has_perm('ae.add_programa'):
            qs = qs.filter(aluno__curso_campus__diretoria__setor__uo=get_uo(request.user))
        return qs


admin.site.register(SolicitacaoAuxilioAluno, SolicitacaoAuxilioAlunoAdmin)


class AuxilioEventualAdmin(ModelAdminPlus):
    form = AuxilioEventualForm
    list_display = ('campus', 'aluno', 'data', 'tipo_auxilio', 'quantidade', 'valor', 'responsavel', 'atualizado_em', 'observacao')
    date_hierarchy = 'data'
    ordering = ('-data',)
    list_filter = ('campus', 'tipo_auxilio')
    search_fields = ('aluno__pessoa_fisica__nome', 'aluno__matricula')
    list_display_icons = True
    list_per_page = 40

    def save_model(self, request, obj, form, change):
        obj.responsavel = request.user.get_vinculo()
        obj.atualizado_em = datetime.datetime.now()
        obj.save()


admin.site.register(AuxilioEventual, AuxilioEventualAdmin)


class SituacaoTrabalhoAdmin(ModelAdminPlus):
    list_display = ('descricao', )
    list_display_links = None


admin.site.register(SituacaoTrabalho, SituacaoTrabalhoAdmin)
