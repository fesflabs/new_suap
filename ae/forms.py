import calendar
import datetime
from collections import OrderedDict
from datetime import date, timedelta
from decimal import Decimal
from django.conf import settings
from dateutil.relativedelta import relativedelta
from dateutil.rrule import DAILY, rrule
from django.apps import apps
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import F, Max, Q, FloatField, Sum
from django.db.models.aggregates import Count
from django.db.models.functions import Cast
from django.forms.widgets import HiddenInput
from django.shortcuts import get_object_or_404

from ae import tasks
from ae.models import (
    AcaoEducativa,
    AgendamentoRefeicao,
    AtendimentoSetor,
    AtividadeDiversa,
    AuxilioEventual,
    BeneficioGovernoFederal,
    Caracterizacao,
    CategoriaAlimentacao,
    CategoriaBolsa,
    CompanhiaDomiciliar,
    ContribuinteRendaFamiliar,
    DatasLiberadasFaltasAlimentacao,
    DatasRecessoFerias,
    DemandaAluno,
    DemandaAlunoAtendida,
    DocumentoInscricaoAluno,
    Edital,
    HorarioSolicitacaoRefeicao,
    Idioma,
    Inscricao,
    InscricaoCaracterizacao,
    IntegranteFamiliarCaracterizacao,
    MeioTransporte,
    MotivoSolicitacaoRefeicao,
    NecessidadeEspecial,
    OfertaAlimentacao,
    OfertaBolsa,
    OfertaPasse,
    OfertaTurma,
    OfertaValorBolsa,
    OfertaValorRefeicao,
    OpcaoRespostaInscricaoPrograma,
    OpcaoRespostaPerguntaParticipacao,
    Participacao,
    ParticipacaoAlimentacao,
    ParticipacaoBolsa,
    ParticipacaoIdioma,
    ParticipacaoPasseEstudantil,
    ParticipacaoTrabalho,
    PassesChoices,
    PerguntaInscricaoPrograma,
    PerguntaParticipacao,
    PeriodoInscricao,
    Programa,
    RazaoAfastamentoEducacional,
    RelatorioGestao,
    RespostaInscricaoPrograma,
    RespostaParticipacao,
    SituacaoTrabalho,
    SolicitacaoAlimentacao,
    SolicitacaoAuxilioAluno,
    SolicitacaoRefeicaoAluno,
    TipoAtendimentoSetor,
    TipoEscola,
    TipoPrograma,
    TipoRefeicao,
    TurnoChoices,
    ValorTotalAuxilios,
    ValorTotalBolsas,
    TipoAuxilioEventual,
    DadosBancarios,
)
from comum.models import Ano, Raca, Vinculo, UsuarioGrupo
from comum.utils import existe_conflito_entre_intervalos, get_sigla_reitoria, get_uo
from djtools import forms
from djtools.choices import DiaSemanaChoices
from djtools.forms.fields import MultiFileField
from djtools.forms.widgets import AutocompleteWidget, TreeWidget
from djtools.forms.wizard import FormWizardPlus
from djtools.utils import SpanField, SpanWidget
from edu.models import Aluno, Convenio, CursoCampus as Curso, Diretoria, MatriculaDiario, Modalidade, SituacaoMatricula, \
    Turma
from rh.models import Banco
from rh.models import Servidor, Setor, UnidadeOrganizacional
from saude.models import Anamnese, Atendimento, CondutaMedica, IntervencaoEnfermagem, SituacaoAtendimento, \
    TipoAtendimento


class ConfiguracaoForm(forms.FormPlus):
    edital_webservice = forms.CharField(label='Webservice para editais - SGC', required=False)
    caracterizacao_webservice = forms.CharField(label='Webservice para caracterizacao - SGC', required=False)
    prazo_expiracao_documentacao = forms.IntegerField(label='Prazo, em dias, de validade da documentação dos alunos', required=False, help_text='Este prazo serve para definir se a documentação do aluno está expirada ou não.')


class ProgramaForm(forms.ModelFormPlus):
    demandas = forms.ModelMultipleChoiceField(
        label='Atendimentos incluídos', queryset=DemandaAluno.ativas.all(), widget=FilteredSelectMultiple('Atendimentos', True), required=False
    )

    publico_alvo = forms.ModelMultipleChoiceField(
        label='Público-Alvo', queryset=UnidadeOrganizacional.objects.uo(), widget=FilteredSelectMultiple('Público-Alvo', True), required=False
    )

    class Meta:
        model = Programa
        fields = ['tipo_programa', 'descricao', 'instituicao', 'demandas', 'impedir_solicitacao_beneficio', 'publico_alvo']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['instituicao'].queryset = UnidadeOrganizacional.objects.uo().all()


# -----------------------------------------------------------------------------
# Forms relacionadas a participação em programas ------------------------------
# -----------------------------------------------------------------------------
class GerenciarParticipacaoBuscaForm(forms.FormPlus):
    METHOD = 'GET'
    matricula_nome = forms.CharField(label='Matrícula/Nome', max_length=100, required=False)
    situacao = forms.ChoiceField(required=False, choices=[['Todas', 'Todas'], ['Ativo', 'Ativo'], ['Inativo', 'Inativo']], label='Situação de Matrícula')
    categoria = forms.ModelChoiceField(queryset=CategoriaAlimentacao.objects, required=False, label='Filtrar por Categoria')
    documentacao_expirada = forms.BooleanField(required=False, label='Somente com documentação expirada?')

    def __init__(self, *args, **kwargs):
        self.alimentacao = kwargs.pop('alimentacao', None)
        super().__init__(*args, **kwargs)
        if not self.alimentacao:
            del self.fields['categoria']


class ParticipacaoBaseForm(forms.ModelFormPlus):
    data_entrada = forms.DateFieldPlus(label='Data de Entrada', required=True)
    motivo_entrada = forms.CharField(label='Motivo de Entrada', widget=forms.Textarea, required=True)

    def __init__(self, *args, **kwargs):
        programa = kwargs.pop('programa')
        inscricao = kwargs.pop('inscricao')
        request = kwargs.pop('request')

        super().__init__(*args, **kwargs)

        self.programa = programa
        self.inscricao = inscricao
        self.request = request
        self.participacao = None

        if 'instance' in kwargs and kwargs['instance']:
            self.participacao = kwargs['instance'].participacao
            self.fields['data_entrada'].initial = self.participacao.data_inicio
            self.fields['motivo_entrada'].initial = self.participacao.motivo_entrada

            if self.participacao.data_termino is not None:
                self.fields['data_termino'] = forms.DateFieldPlus(label='Data de Saída', required=True)
                self.fields['motivo_termino'] = forms.CharField(label='Motivo de Saída', widget=forms.Textarea, required=True)
                self.fields['data_termino'].initial = self.participacao.data_termino
                self.fields['motivo_termino'].initial = self.participacao.motivo_termino

    def clean_data_entrada(self):
        if 'data_entrada' in self.cleaned_data:
            participacoes = Participacao.objects.filter(aluno=self.inscricao.aluno, programa=self.programa)
            if self.participacao:
                participacoes = participacoes.exclude(pk=self.participacao.pk)

            for participacao in participacoes:
                if not self.participacao:
                    if participacao.data_termino is None:
                        raise forms.ValidationError('Existe participação aberta para o aluno.')

                    if participacao.data_termino and participacao.data_termino >= self.cleaned_data['data_entrada']:
                        raise forms.ValidationError('A Data de Entrada da participação é menor que a Data de Saída da última participação.')

            return self.cleaned_data['data_entrada']
        return None

    def clean(self):
        data_inicio = self.cleaned_data.get('data_entrada')
        if data_inicio:
            data_termino1 = self.cleaned_data.get('data_termino')
            if data_termino1:
                if data_termino1 <= data_inicio:
                    raise ValidationError('Data de Saída não pode ser menor ou igual à Data de Entrada.')
            else:
                data_termino1 = datetime.date.today()
                if data_inicio > data_termino1:
                    raise ValidationError('Data de Entrada não pode ser maior que hoje.')

            participantes = Participacao.objects.filter(aluno=self.inscricao.aluno, programa=self.programa)
            if data_inicio <= datetime.date.today():
                participacoes = participantes
                if self.participacao:
                    participacoes = participacoes.exclude(id=self.participacao.id)

                for p in participacoes:
                    data_termino2 = p.data_termino
                    if not data_termino2:
                        data_termino2 = datetime.date.today()
                    retorno = existe_conflito_entre_intervalos([data_inicio, data_termino1, p.data_inicio, data_termino2])
                    if retorno:
                        raise ValidationError('Aluno já possui participação neste período, confira em Gerenciar Participações.')

            tem_participacao = participantes.filter(Q(data_termino__isnull=True) | Q(data_termino__gte=datetime.date.today())).exists()

            # uma participação ainda não finalizada não possui o campo 'data_termino'
            if tem_participacao and not self.participacao:
                raise ValidationError('Não é possível adicionar participação. Verifique se o aluno já tem participação aberta.')

        return super().clean()

    @transaction.atomic()
    def save(self, *args, **kwargs):
        if self.participacao:
            self.participacao.data_inicio = self.cleaned_data['data_entrada']
            self.participacao.motivo_entrada = self.cleaned_data['motivo_entrada']
            if self.participacao.data_termino is not None:
                self.participacao.data_termino = self.cleaned_data['data_termino']
                self.participacao.motivo_termino = self.cleaned_data['motivo_termino']
            self.participacao.save()
        else:
            self.participacao = Participacao.objects.create(
                programa=self.programa,
                aluno=self.inscricao.aluno,
                inscricao=self.inscricao,
                data_inicio=self.cleaned_data['data_entrada'],
                motivo_entrada=self.cleaned_data['motivo_entrada'],
                atualizado_por=self.request.user.get_vinculo(),
                atualizado_em=datetime.datetime.now(),
            )


class ParticipacaoAlimentacaoForm(ParticipacaoBaseForm):
    cafe = forms.MultipleChoiceField(label='Café da Manhã', choices=DiaSemanaChoices.DIAS_SEMANA_RESUMIDO_CHOICES, widget=forms.CheckboxSelectMultiple, required=False)
    almoco = forms.MultipleChoiceField(label='Almoço', choices=DiaSemanaChoices.DIAS_SEMANA_RESUMIDO_CHOICES, widget=forms.CheckboxSelectMultiple, required=False)
    jantar = forms.MultipleChoiceField(label='Jantar', choices=DiaSemanaChoices.DIAS_SEMANA_RESUMIDO_CHOICES, widget=forms.CheckboxSelectMultiple, required=False)

    class Meta:
        model = ParticipacaoAlimentacao
        fields = ('data_entrada', 'motivo_entrada', 'cafe', 'almoco', 'jantar', 'categoria')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.pk:
            if (
                (self.instance.solicitacao_atendida_cafe and self.instance.solicitacao_atendida_cafe.valida())
                or (self.instance.solicitacao_atendida_almoco and self.instance.solicitacao_atendida_almoco.valida())
                or (self.instance.solicitacao_atendida_janta and self.instance.solicitacao_atendida_janta.valida())
            ):
                if self.instance.solicitacao_atendida_cafe:
                    self.fields['cafe'].initial = self.instance.solicitacao_atendida_cafe.get_itens_escolhidos()
                    self.fields['cafe'] = SpanField(widget=SpanWidget(), label='Café da Manhã')
                    self.fields['cafe'].widget.label_value = ", ".join(self.instance.solicitacao_atendida_cafe.get_choice_list())
                    self.fields['cafe'].widget.original_value = self.instance.solicitacao_atendida_cafe.get_itens_escolhidos()
                    self.fields['cafe'].required = False
                else:
                    self.fields['cafe'].initial = []
                    self.fields['cafe'] = SpanField(widget=SpanWidget(), label='Café da Manhã')
                    self.fields['cafe'].widget.label_value = " "
                    self.fields['cafe'].widget.original_value = []
                    self.fields['cafe'].required = False

                if self.instance.solicitacao_atendida_almoco:
                    self.fields['almoco'].initial = self.instance.solicitacao_atendida_almoco.get_itens_escolhidos()
                    self.fields['almoco'] = SpanField(widget=SpanWidget(), label='Almoço')
                    self.fields['almoco'].widget.label_value = ", ".join(self.instance.solicitacao_atendida_almoco.get_choice_list())
                    self.fields['almoco'].widget.original_value = self.instance.solicitacao_atendida_almoco.get_itens_escolhidos()
                    self.fields['almoco'].required = False
                else:
                    self.fields['almoco'].initial = []
                    self.fields['almoco'] = SpanField(widget=SpanWidget(), label='Almoço')
                    self.fields['almoco'].widget.label_value = " "
                    self.fields['almoco'].widget.original_value = []
                    self.fields['almoco'].required = False

                if self.instance.solicitacao_atendida_janta:
                    self.fields['jantar'].initial = self.instance.solicitacao_atendida_janta.get_itens_escolhidos()
                    self.fields['jantar'] = SpanField(widget=SpanWidget(), label='Jantar')
                    self.fields['jantar'].widget.label_value = ", ".join(self.instance.solicitacao_atendida_janta.get_choice_list())
                    self.fields['jantar'].widget.original_value = self.instance.solicitacao_atendida_janta.get_itens_escolhidos()
                    self.fields['jantar'].required = False
                else:
                    self.fields['jantar'].initial = []
                    self.fields['jantar'] = SpanField(widget=SpanWidget(), label='Jantar')
                    self.fields['jantar'].widget.label_value = " "
                    self.fields['jantar'].widget.original_value = []
                    self.fields['jantar'].required = False

            if self.instance.categoria:
                self.fields['categoria'] = SpanField(widget=SpanWidget(), label='Categoria')
                self.fields['categoria'].widget.label_value = self.instance.categoria
                self.fields['categoria'].widget.original_value = self.instance.categoria
                self.fields['categoria'].required = False

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.instance.pk:
            self.instance.participacao = self.participacao

        if self.instance.pk and self.instance.solicitacao_atendida_cafe:
            solicitacao_cafe = self.instance.solicitacao_atendida_cafe
        else:
            solicitacao_cafe = SolicitacaoAlimentacao()
        for item in self.cleaned_data['cafe']:
            if int(item) == DiaSemanaChoices.SEGUNDA:
                solicitacao_cafe.seg = True
            elif int(item) == DiaSemanaChoices.TERCA:
                solicitacao_cafe.ter = True
            elif int(item) == DiaSemanaChoices.QUARTA:
                solicitacao_cafe.qua = True
            elif int(item) == DiaSemanaChoices.QUINTA:
                solicitacao_cafe.qui = True
            elif int(item) == DiaSemanaChoices.SEXTA:
                solicitacao_cafe.sex = True
            elif int(item) == DiaSemanaChoices.SABADO:
                solicitacao_cafe.sab = True
            elif int(item) == DiaSemanaChoices.DOMINGO:
                solicitacao_cafe.dom = True
        solicitacao_cafe.save()

        if self.instance.pk and self.instance.solicitacao_atendida_almoco:
            solicitacao_almoco = self.instance.solicitacao_atendida_almoco
        else:
            solicitacao_almoco = SolicitacaoAlimentacao()
        for item in self.cleaned_data['almoco']:
            if int(item) == DiaSemanaChoices.SEGUNDA:
                solicitacao_almoco.seg = True
            elif int(item) == DiaSemanaChoices.TERCA:
                solicitacao_almoco.ter = True
            elif int(item) == DiaSemanaChoices.QUARTA:
                solicitacao_almoco.qua = True
            elif int(item) == DiaSemanaChoices.QUINTA:
                solicitacao_almoco.qui = True
            elif int(item) == DiaSemanaChoices.SEXTA:
                solicitacao_almoco.sex = True
            elif int(item) == DiaSemanaChoices.SABADO:
                solicitacao_almoco.sab = True
            elif int(item) == DiaSemanaChoices.DOMINGO:
                solicitacao_almoco.dom = True
        solicitacao_almoco.save()

        if self.instance.pk and self.instance.solicitacao_atendida_janta:
            solicitacao_jantar = self.instance.solicitacao_atendida_janta
        else:
            solicitacao_jantar = SolicitacaoAlimentacao()
        for item in self.cleaned_data['jantar']:
            if int(item) == DiaSemanaChoices.SEGUNDA:
                solicitacao_jantar.seg = True
            elif int(item) == DiaSemanaChoices.TERCA:
                solicitacao_jantar.ter = True
            elif int(item) == DiaSemanaChoices.QUARTA:
                solicitacao_jantar.qua = True
            elif int(item) == DiaSemanaChoices.QUINTA:
                solicitacao_jantar.qui = True
            elif int(item) == DiaSemanaChoices.SEXTA:
                solicitacao_jantar.sex = True
            elif int(item) == DiaSemanaChoices.SABADO:
                solicitacao_jantar.sab = True
            elif int(item) == DiaSemanaChoices.DOMINGO:
                solicitacao_jantar.dom = True
        solicitacao_jantar.save()

        self.instance.solicitacao_atendida_cafe = solicitacao_cafe
        self.instance.solicitacao_atendida_almoco = solicitacao_almoco
        self.instance.solicitacao_atendida_janta = solicitacao_jantar
        self.instance.save()

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            if len(cleaned_data.get('almoco')) == 0 and len(cleaned_data.get('jantar')) == 0 and len(cleaned_data.get('cafe')) == 0:
                self.errors['__all__'] = self.error_class(['Selecione pelo menos um dia da semana.'])
                del cleaned_data['almoco']
                del cleaned_data['jantar']
                del cleaned_data['cafe']
            if self.cleaned_data['data_entrada'].year < 1900:
                self.errors['data_entrada'] = self.error_class(['O ano do atendimento deve ser superior a 1900.'])
                del cleaned_data['data_entrada']
        return cleaned_data


class ParticipacaoIdiomaForm(ParticipacaoBaseForm):
    class Meta:
        model = ParticipacaoIdioma
        fields = ('data_entrada', 'motivo_entrada', 'idioma')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.pk and self.instance.idioma:
            self.fields['idioma'].widget.attrs['readonly'] = 'readonly'
            self.fields['idioma'] = SpanField(widget=SpanWidget(), label='Idioma')
            self.fields['idioma'].widget.label_value = self.instance.idioma
            self.fields['idioma'].widget.original_value = self.instance.idioma
            self.fields['idioma'].required = False

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.instance.pk:
            self.instance.participacao = self.participacao
        self.instance.save()

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            if self.cleaned_data['data_entrada'].year < 1900:
                self.errors['data_entrada'] = self.error_class(['O ano do atendimento deve ser superior a 1900.'])
                del cleaned_data['data_entrada']
            if not self.cleaned_data.get('idioma'):
                raise forms.ValidationError('Deve-se selecionar um idioma.')
        return super().clean()


class ParticipacaoTrabalhoForm(ParticipacaoBaseForm):
    class Meta:
        model = ParticipacaoTrabalho
        fields = ('data_entrada', 'motivo_entrada', 'bolsa_concedida')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        bolsas = Q(disponivel=True, campus=self.programa.instituicao, ativa=True)

        if self.instance.bolsa_concedida:
            self.fields['bolsa_concedida'] = forms.ModelChoiceField(
                label='Bolsa concedida',
                queryset=OfertaBolsa.objects,
                widget=AutocompleteWidget(search_fields=OfertaBolsa.SEARCH_FIELDS, readonly=True),
                initial=self.instance.bolsa_concedida.pk,
            )
            self.fields['bolsa_concedida'].required = False
            self.fields['bolsa_concedida'].queryset = OfertaBolsa.objects.filter(bolsas | Q(pk=self.instance.bolsa_concedida.pk)).distinct().order_by("setor__sigla")
        else:
            self.fields['bolsa_concedida'].queryset = OfertaBolsa.objects.filter(bolsas).order_by("setor__sigla")

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.instance.pk:
            self.instance.participacao = self.participacao
        self.instance.save()

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            if self.cleaned_data['data_entrada'].year < 1900:
                self.errors['data_entrada'] = self.error_class(['O ano da participação deve ser superior a 1900.'])
            else:
                bolsas = ParticipacaoBolsa.objects.filter(aluno=self.inscricao.aluno, data_termino__gt=cleaned_data['data_entrada'])
                bolsas = bolsas.filter(
                    Q(aluno=self.inscricao.aluno) & (Q(data_termino__gt=cleaned_data['data_entrada']) | Q(data_termino__isnull=True) | Q(data_termino__gte=datetime.date.today()))
                )
                if bolsas.exists():
                    for bolsa in bolsas:
                        if bolsa.data_termino:
                            if bolsa.data_termino >= cleaned_data['data_entrada'] and bolsa.data_inicio <= cleaned_data['data_entrada']:
                                raise forms.ValidationError('O aluno selecionado já possui outra bolsa no período informado.')

                        else:
                            raise forms.ValidationError('O aluno selecionado já possui outra bolsa no período informado.')
        return cleaned_data


class ParticipacaoTransporteForm(ParticipacaoBaseForm):
    class Meta:
        model = ParticipacaoPasseEstudantil
        fields = ('data_entrada', 'motivo_entrada', 'valor_concedido', 'tipo_passe_concedido')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.instance.tipo_passe_concedido:
            self.fields['valor_concedido'].widget.attrs['readonly'] = 'readonly'
            self.fields['valor_concedido'].required = False
            self.fields['tipo_passe_concedido'] = SpanField(widget=SpanWidget(), label='Tipo de Passe Concedido')
            self.fields['tipo_passe_concedido'].widget.label_value = self.instance.get_tipo_passe_concedido_display()
            self.fields['tipo_passe_concedido'].widget.original_value = self.instance.tipo_passe_concedido
            self.fields['tipo_passe_concedido'].required = False

    def clean_tipo_passe_concedido(self):
        tipo_passe = self.cleaned_data.get('tipo_passe_concedido')
        if not tipo_passe:
            raise ValidationError('Este campo possui preenchimento obrigatório.')
        return self.cleaned_data['tipo_passe_concedido']

    def clean_valor_concedido(self):
        if not self.instance.tipo_passe_concedido:
            valor_concedido = self.cleaned_data.get('valor_concedido')
            if not valor_concedido:
                raise ValidationError('Este campo possui preenchimento obrigatório.')
        return self.cleaned_data['valor_concedido']

    @transaction.atomic()
    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.instance.pk:
            self.instance.participacao = self.participacao
        self.instance.save()

    def clean_data_entrada(self):
        data_entrada = self.cleaned_data.get('data_entrada')
        if data_entrada.year < 1900:
            self.errors['data_entrada'] = self.error_class(['O ano do atendimento deve ser superior a 1900.'])
        return self.cleaned_data['data_entrada']


def ParticipacaoFormFactory(data=None, programa=None, inscricao=None, instance=None, request=None):
    if instance:
        if hasattr(instance, 'participacao'):
            programa = instance.participacao.programa
            inscricao = instance.participacao.inscricao
        else:
            programa = instance.programa
            inscricao = instance.inscricao

    if programa.get_tipo() == Programa.TIPO_ALIMENTACAO:
        return ParticipacaoAlimentacaoForm(data, programa=programa, inscricao=inscricao, instance=instance, request=request)
    elif programa.get_tipo() == Programa.TIPO_IDIOMA:
        return ParticipacaoIdiomaForm(data, programa=programa, inscricao=inscricao, instance=instance, request=request)
    elif programa.get_tipo() == Programa.TIPO_TRABALHO:
        return ParticipacaoTrabalhoForm(data, programa=programa, inscricao=inscricao, instance=instance, request=request)
    elif programa.get_tipo() == Programa.TIPO_TRANSPORTE:
        return ParticipacaoTransporteForm(data, programa=programa, inscricao=inscricao, instance=instance, request=request)
    else:
        return PerguntaParticipacaoForm(data, programa=programa, inscricao=inscricao, instance=instance, request=request)


class RevogarParticipacaoForm(forms.ModelFormPlus):
    data_termino = forms.DateFieldPlus(label='Data da Saída', required=True)
    motivo_termino = forms.CharField(label='Motivo da Saída', widget=forms.Textarea, required=True)

    class Meta:
        model = Participacao
        fields = ('data_termino', 'motivo_termino')

    def clean_data_termino(self):
        if self.cleaned_data['data_termino'] <= self.instance.data_inicio:
            raise forms.ValidationError('Data de Saída não pode ser menor ou igual à Data de Entrada.')

        for p in Participacao.objects.filter(aluno=self.instance.aluno, programa=self.instance.programa).exclude(id=self.instance.id):
            data_termino = p.data_termino
            if not data_termino:
                data_termino = datetime.date.today()
            if existe_conflito_entre_intervalos([self.instance.data_inicio, self.cleaned_data['data_termino'], p.data_inicio, data_termino]):
                raise forms.ValidationError('Aluno já possui participação neste período. Acesse Gerenciar Participações e procure por participações com datas conflitantes.')

        return self.cleaned_data['data_termino']


class CaracterizacaoForm(forms.ModelFormPlus):
    form_id = forms.IntegerField(required=False, initial=1, widget=forms.HiddenInput())
    necessidade_especial = forms.ModelMultipleChoiceField(
        queryset=NecessidadeEspecial.objects.all(), widget=forms.CheckboxSelectMultiple(), required=False, label='Pessoa com deficiência/Necessidades Educacionais Especiais'
    )
    possui_conhecimento_idiomas = forms.BooleanField(
        label='Possui conhecimento em idiomas', initial=False, required=False, help_text='Marque caso possua conhecimento em outros idiomas.'
    )
    idiomas_conhecidos = forms.ModelMultipleChoiceField(queryset=Idioma.objects.all(), widget=forms.CheckboxSelectMultiple(), required=False)
    beneficiario_programa_social = forms.MultipleModelChoiceField(
        queryset=BeneficioGovernoFederal.objects.all().exclude(descricao='Programa de Erradicação do Trabalho Infantil'),
        required=False,
        label='Informe os programas do governo federal dos quais você ou algum membro de sua família seja beneficiário.',
    )
    ficou_tempo_sem_estudar = forms.BooleanField(label='Ausência Escolar', initial=False, required=False)
    razao_ausencia_educacional = forms.ModelChoiceField(
        queryset=RazaoAfastamentoEducacional.objects.all(), widget=forms.Select(), required=False, label='Razão da ausência escolar'
    )
    tempo_sem_estudar = forms.IntegerField(required=False, label='Tempo sem estudar (em meses)')
    contribuintes_renda_familiar = forms.ModelMultipleChoiceField(
        queryset=ContribuinteRendaFamiliar.objects.all(), widget=forms.CheckboxSelectMultiple(), required=True, label='Contribuintes da Renda Familiar'
    )
    renda_bruta_familiar = forms.DecimalFieldPlus(initial='0,00', label='Renda Bruta Familiar R$', required=True)
    companhia_domiciliar = forms.ModelChoiceField(required=True, queryset=CompanhiaDomiciliar.objects.all(), widget=forms.RadioSelect(), empty_label=None)
    responsavel_financeiro = forms.ModelChoiceField(
        required=True, widget=forms.RadioSelect(), empty_label=None, queryset=ContribuinteRendaFamiliar.objects.all(), label='Principal Responsável Financeiro'
    )
    responsavel_financeir_trabalho_situacao = forms.ModelChoiceField(
        required=True,
        label='Situação de Trabalho do Principal Responsável Financeiro',
        queryset=SituacaoTrabalho.objects.all().exclude(descricao='Trabalha com vínculo empregatício'),
    )
    meio_transporte_utilizado = forms.MultipleModelChoiceField(
        queryset=MeioTransporte.objects.all(), required=True, label='Meio de transporte que você utiliza/utilizará para se deslocar'
    )

    fieldsets = (
        ('Dados Pessoais', {'fields': (('raca', 'form_id'), ('possui_necessidade_especial', 'necessidade_especial'), ('estado_civil'), ('qtd_filhos'), ('tipo_servico_saude'))}),
        (
            'Dados Educacionais',
            {
                'fields': (
                    ('ensino_fundamental_conclusao', 'ensino_medio_conclusao'),
                    ('escola_ensino_fundamental', 'nome_escola_ensino_fundamental'),
                    ('escola_ensino_medio', 'nome_escola_ensino_medio'),
                    ('ficou_tempo_sem_estudar', 'tempo_sem_estudar', 'razao_ausencia_educacional'),
                    ('possui_conhecimento_idiomas', 'idiomas_conhecidos'),
                    ('possui_conhecimento_informatica'),
                )
            },
        ),
        (
            'Situação Familiar e Socioeconômica',
            {
                'fields': (
                    ('trabalho_situacao'),
                    ('meio_transporte_utilizado'),
                    ('contribuintes_renda_familiar', 'responsavel_financeiro'),
                    ('responsavel_financeir_trabalho_situacao', 'responsavel_financeiro_nivel_escolaridade'),
                    ('pai_nivel_escolaridade', 'mae_nivel_escolaridade'),
                    ('renda_bruta_familiar'),
                    ('companhia_domiciliar', 'qtd_pessoas_domicilio'),
                    ('tipo_imovel_residencial', 'tipo_area_residencial'),
                    ('beneficiario_programa_social'),
                )
            },
        ),
        (
            'Acesso às Tecnologias da Informação e Comunicação',
            {
                'fields': (
                    ('frequencia_acesso_internet', 'local_acesso_internet'),
                    ('quantidade_computadores', 'quantidade_notebooks', 'quantidade_netbooks', 'quantidade_smartphones'),
                )
            },
        ),
    )

    class Meta:
        model = Caracterizacao
        exclude = ('aluno', 'historico_caracterizacao', 'renda_per_capita', 'data_cadastro', 'data_ultima_atualizacao')

    def __init__(self, aluno, *args, **kwargs):
        if 'inscricao_caracterizacao' in kwargs:
            kwargs.pop('inscricao_caracterizacao')
            self.SUBMIT_LABEL = 'Continuar'

        super().__init__(*args, **kwargs)
        self.aluno = aluno
        self.fields['nome_escola_ensino_medio'].required = False
        self.fields['escola_ensino_medio'].required = False
        self.fields['nome_escola_ensino_fundamental'].required = False
        self.fields['frequencia_acesso_internet'].required = True
        self.fields['local_acesso_internet'].required = False
        self.fields['quantidade_computadores'].required = True
        self.fields['quantidade_notebooks'].required = True
        self.fields['quantidade_netbooks'].required = True
        self.fields['quantidade_smartphones'].required = True

        self.PROEJA = Modalidade.objects.get(pk=Caracterizacao.MODALIDADE_EJA)
        self.SUBSEQUENTE = Modalidade.objects.get(pk=Caracterizacao.MODALIDADE_SUBSEQUENTE)
        self.GRADUACAO = Modalidade.objects.get(pk=Caracterizacao.MODALIDADE_GRADUACAO)
        self.ENGENHARIA = Modalidade.objects.get(pk=Caracterizacao.MODALIDADE_ENGENHARIA)
        self.LICENCIATURA = Modalidade.objects.get(pk=Caracterizacao.MODALIDADE_LICENCIATURA)
        self.ESPECIALIZACAO = Modalidade.objects.get(pk=Caracterizacao.MODALIDADE_ESPECIALIZACAO)
        self.MESTRADO = Modalidade.objects.get(pk=Caracterizacao.MODALIDADE_MESTRADO)
        self.DOUTOURADO = Modalidade.objects.get(pk=Caracterizacao.MODALIDADE_DOUTORADO)

        if not aluno.curso_campus.modalidade in [
            self.PROEJA,
            self.SUBSEQUENTE,
            self.GRADUACAO,
            self.ENGENHARIA,
            self.LICENCIATURA,
            self.ESPECIALIZACAO,
            self.MESTRADO,
            self.DOUTOURADO,
        ]:
            self.fields['ficou_tempo_sem_estudar'].widget = HiddenInput()
            self.fields['tempo_sem_estudar'].widget = HiddenInput()
            self.fields['razao_ausencia_educacional'].widget = HiddenInput()

        if self.instance.pk:
            self.initial['meio_transporte_utilizado'] = list(self.instance.meio_transporte_utilizado.values_list('id', flat=True))
            self.initial['contribuintes_renda_familiar'] = list(self.instance.contribuintes_renda_familiar.values_list('id', flat=True))
            self.initial['idiomas_conhecidos'] = list(self.instance.idiomas_conhecidos.values_list('id', flat=True))

    def clean_qtd_pessoas_domicilio(self):
        qtd_pessoas_domicilio = self.cleaned_data['qtd_pessoas_domicilio']
        if int(qtd_pessoas_domicilio) <= 0:
            raise ValidationError("Informe o número de pessoas que moram no domicílio, incluíndo você. Caso more sozinho, informe o valor 1.")
        if int(qtd_pessoas_domicilio) > 20:
            raise ValidationError("O valor máximo deste campo é 20.")

        return qtd_pessoas_domicilio

    def clean(self):
        cleaned_data = super().clean()

        if self.errors:
            return cleaned_data

        if 'possui_necessidade_especial' in cleaned_data and cleaned_data['possui_necessidade_especial']:
            if not ('necessidade_especial' in cleaned_data and cleaned_data['necessidade_especial']):
                self._errors['necessidade_especial'] = self.error_class(['Selecione a(s) necessidade(s) especial(ais) que você possui.'])
                del cleaned_data['necessidade_especial']
        else:
            cleaned_data['necessidade_especial'] = NecessidadeEspecial.objects.none()

        if (
            'ficou_tempo_sem_estudar' in cleaned_data
            and cleaned_data['ficou_tempo_sem_estudar']
            and self.aluno.curso_campus.modalidade
            in [self.PROEJA, self.SUBSEQUENTE, self.GRADUACAO, self.ENGENHARIA, self.LICENCIATURA, self.ESPECIALIZACAO, self.MESTRADO, self.DOUTOURADO]
        ):
            if not ('tempo_sem_estudar' in cleaned_data and self.cleaned_data['tempo_sem_estudar']):
                self._errors['tempo_sem_estudar'] = self.error_class(['Informe o tempo que você deixou de estudar.'])
                del cleaned_data['tempo_sem_estudar']
            if not ('razao_ausencia_educacional' in cleaned_data and self.cleaned_data['razao_ausencia_educacional']):
                self._errors['razao_ausencia_educacional'] = self.error_class(['Informe a razão pela qual você deixou de estudar.'])
                del cleaned_data['razao_ausencia_educacional']
        else:
            cleaned_data['tempo_sem_estudar'] = None
            cleaned_data['razao_ausencia_educacional'] = None

        if 'possui_conhecimento_idiomas' in cleaned_data and cleaned_data['possui_conhecimento_idiomas']:
            if not ('idiomas_conhecidos' in cleaned_data and cleaned_data['idiomas_conhecidos']):
                self._errors['idiomas_conhecidos'] = self.error_class(['Selecione o(s) idioma(s) que você conhece.'])
                del cleaned_data['idiomas_conhecidos']
        else:
            cleaned_data['idiomas_conhecidos'] = Idioma.objects.none()

        # if 'responsavel_financeiro' in self.cleaned_data and 'contribuintes_renda_familiar' in self.cleaned_data:
        #            if self.cleaned_data['responsavel_financeiro'] not in self.cleaned_data['contribuintes_renda_familiar']:
        #                raise forms.ValidationError(u'A pessoa responsável pela renda familiar deve ser um dos contribuintes da renda familiar')
        #
        #        if 'responsavel_financeiro' in self.cleaned_data and 'responsavel_financeiro_nivel_escolaridade' in self.cleaned_data and 'pai_nivel_escolaridade' in self.cleaned_data:
        #            if self.cleaned_data['responsavel_financeiro'].descricao==u'Pai':
        #                if self.cleaned_data['responsavel_financeiro_nivel_escolaridade'] != self.cleaned_data['pai_nivel_escolaridade']:
        #                    raise forms.ValidationError(u'Há uma divergência entre o nível de escolaridade do pai e da pessoa responsável pela renda familiar')
        #
        #        if 'responsavel_financeiro' in self.cleaned_data and 'responsavel_financeiro_nivel_escolaridade' in self.cleaned_data and 'mae_nivel_escolaridade' in self.cleaned_data:
        #            if self.cleaned_data['responsavel_financeiro'].descricao==u'Mãe':
        #                if self.cleaned_data['responsavel_financeiro_nivel_escolaridade'] != self.cleaned_data['mae_nivel_escolaridade']:
        #                    raise forms.ValidationError(u'Há uma divergência entre o nível de escolaridade da mãe e da pessoa responsável pela renda familiar')
        #
        #        if 'renda_bruta_familiar' in self.cleaned_data:
        #            if self.cleaned_data['renda_bruta_familiar'] == 0:
        #                raise forms.ValidationError(u'Informe a Renda Bruta Familiar em Reais')

        return self.cleaned_data


# ------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------------------------------------------------------------


class InscricaoModelForm(forms.ModelFormPlus):
    aluno = forms.ModelChoiceField(queryset=Aluno.objects, widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS), label='Aluno', required=True)

    class Meta:
        model = Inscricao
        exclude = ('parecer', 'parecer_data', 'parecer_autor_vinculo', 'atualizado_por', 'atualizado_em')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
            self.fields['aluno'] = forms.ModelChoiceField(queryset=Aluno.objects, widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS), label='Aluno', required=True)


class RendimentoCaracterizacaoForm(forms.ModelFormPlus):
    SUBMIT_LABEL = 'Continuar'
    informacoes_complementares = forms.CharField(
        widget=forms.Textarea,
        label='Informações complementares:',
        help_text='Se achar necessário, relate alguma situação familiar especial, não contemplada no questionário, \
    a qual você julga importante para fundamentar a análise de sua situação econômica.',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['familiar_doente_cronico_nome'].required = False
        self.fields['informacoes_complementares'].required = False
        self.fields['moradia_especificacao'].required = False
        self.fields['rendimento_mesada'].required = False
        self.fields['rendimento_aux_parentes'].required = False
        self.fields['rendimento_aluguel'].required = False
        self.fields['rendimento_outro'].required = False
        self.fields['valor_transporte'].label = 'Valor gasto com transporte por dia'
        self.fields['remuneracao_trabalho'].label = 'Renda do Estudante'
        self.fields['remuneracao_trabalho'].help_text = 'Renda do estudante com trabalho, benefício, bolsa, estágio, aposentadoria, pensão, etc...'

    class Meta:
        model = InscricaoCaracterizacao
        exclude = ('aluno', 'data')


class AtendimentoSetorForm(forms.ModelFormPlus):
    alunos = forms.MultipleModelChoiceFieldPlus(queryset=Aluno.objects.all(), required=True, help_text='Procure pelo nome ou matrícula do(s) aluno(s)')
    campus = forms.ModelChoiceField(
        queryset=UnidadeOrganizacional.objects.uo().all(),
        widget=AutocompleteWidget(search_fields=UnidadeOrganizacional.SEARCH_FIELDS), label='Campus', required=True
    )

    class Meta:
        model = AtendimentoSetor
        fields = ('campus', 'tipoatendimentosetor', 'data', 'data_termino', 'valor', 'setor', 'observacao', 'alunos', 'numero_processo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        if not user.groups.filter(name='Coordenador de Atividades Estudantis Sistêmico').exists() and not user.groups.filter(name='Diretor Geral').exists():
            self.fields['campus'].queryset = self.fields['campus'].queryset.filter(id=get_uo(user).id)

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            if self.cleaned_data['data'].year < 1900:
                self.errors['data'] = self.error_class(['O ano de início do auxílio deve ser superior a 1900.'])
            if self.cleaned_data['data'].year > datetime.datetime.now().year + 100:
                self.errors['data'] = self.error_class(['O ano de início do auxílio deve ser inferior a {:d}.'.format(datetime.datetime.now().year + 100)])

            if self.cleaned_data['data_termino']:
                if self.cleaned_data['data_termino'] < self.cleaned_data['data']:
                    self.errors['data_termino'] = self.error_class(['A data de término do auxílio deve ser superior à data de início.'])
                if self.cleaned_data['data_termino'].year > datetime.datetime.now().year + 100:
                    self.errors['data_termino'] = self.error_class(['O ano de término do auxílio deve ser inferior a {:d}.'.format(datetime.datetime.now().year + 100)])

        return cleaned_data


class DemandaAlunoAtendidaModelForm(forms.ModelFormPlus):
    responsavel_vinculo = forms.ModelChoiceField(
        queryset=Vinculo.objects, widget=AutocompleteWidget(search_fields=Vinculo.SEARCH_FIELDS, readonly=True), label='Responsável', required=False
    )

    data = forms.DateTimeFieldPlus()
    quantidade = forms.IntegerField(min_value=0)
    campus = forms.ModelChoiceField(
        queryset=UnidadeOrganizacional.objects.uo().all(), widget=AutocompleteWidget(search_fields=UnidadeOrganizacional.SEARCH_FIELDS), label='Campus', required=True
    )

    class Meta:
        model = DemandaAlunoAtendida
        fields = ('demanda', 'campus', 'programa', 'aluno', 'data', 'quantidade', 'valor', 'observacao', 'responsavel_vinculo', 'arquivo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        self.fields['data'].initial = datetime.datetime.today()
        self.fields['responsavel_vinculo'].initial = user.get_vinculo()
        self.fields['quantidade'].initial = 1
        uo = get_uo(user)
        if not uo.setor.sigla == get_sigla_reitoria():
            self.fields['programa'].queryset = Programa.objects.filter(instituicao=uo)
        if user.groups.filter(name='Nutricionista').exists():
            self.fields['demanda'].queryset = DemandaAluno.ativas.filter(id__in=[DemandaAluno.ALMOCO, DemandaAluno.JANTAR, DemandaAluno.CAFE]) | DemandaAluno.ativas.filter(eh_kit_alimentacao=True)
        elif user.groups.filter(name='Coordenador de Atividades Estudantis').exists() and not user.groups.filter(name__in=['Coordenador de Atividades Estudantis Sistêmico', 'Bolsista do Serviço Social', 'Assistente Social']).exists():
            self.fields['demanda'].queryset = DemandaAluno.ativas.filter(eh_kit_alimentacao=True)
        else:
            self.fields['demanda'].queryset = DemandaAluno.ativas.all()
        if not user.groups.filter(name='Coordenador de Atividades Estudantis Sistêmico').exists():
            campus_id = self.instance.campus_id
            if not campus_id:
                campus_id = get_uo(self.request.user).id

            self.fields['campus'].initial = campus_id
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo().filter(id=campus_id)
            self.fields['campus'].widget.attrs['readonly'] = True
        self.fields['aluno'] = forms.ModelChoiceField(queryset=Aluno.nao_fic,
                                                      widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS),
                                                      label='Aluno', required=True)
        if self.instance.pk:
            self.fields['aluno'].widget.attrs['readonly'] = True
            self.fields['aluno'] = SpanField(widget=SpanWidget(), label='Aluno')
            self.fields['aluno'].widget.original_value = self.instance.aluno

        if user.groups.filter(name='Bolsista do Serviço Social').exists():
            self.fields['responsavel_vinculo'] = forms.ModelChoiceFieldPlus(
                queryset=Vinculo.objects, widget=AutocompleteWidget(search_fields=Vinculo.SEARCH_FIELDS), label='Responsável', required=True
            )

            self.fields['responsavel_vinculo'].queryset = Vinculo.objects.filter(setor__uo=get_uo(user), user__in=UsuarioGrupo.objects.filter(group__name__in=['Assistente Social', 'Coordenador de Atividades Estudatis', 'Nutricionista']).values_list('user', flat=True))

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('data'):
            if cleaned_data.get('data').year < 1900:
                self.errors['data'] = self.error_class(['O ano do atendimento deve ser superior a 1900.'])
            if cleaned_data.get('data').year > datetime.datetime.now().year + 100:
                self.errors['data'] = self.error_class(['O ano do atendimento deve ser inferior a {:d}.'.format(datetime.datetime.now().year + 100)])
            if cleaned_data.get('data') > datetime.datetime.now():
                self.errors['data'] = self.error_class(['Não é possível registrar atendimento futuro.'])

        if self.cleaned_data.get('aluno') and self.cleaned_data.get('demanda') and not self.cleaned_data.get(
                'aluno').situacao.ativo and not self.cleaned_data.get('demanda').eh_kit_alimentacao:
            self.errors['aluno'] = self.error_class(
                ['Só é permitido adicionar atendimento do tipo "kit de alimentação" para alunos inativos.'])
        registro_existente = False
        if self.instance.pk:
            if (
                DemandaAlunoAtendida.objects.filter(demanda=self.cleaned_data.get('demanda'), aluno=self.cleaned_data.get('aluno'), data=cleaned_data.get('data'))
                .exclude(id=self.instance.pk)
                .exists()
            ):
                registro_existente = True
        else:

            if DemandaAlunoAtendida.objects.filter(demanda=self.cleaned_data.get('demanda'), aluno=self.cleaned_data.get('aluno'), data=cleaned_data.get('data')).exists():
                registro_existente = True
        if registro_existente:
            self.errors['aluno'] = self.error_class(['Já existe um atendimento desta demanda para o mesmo aluno na mesma data.'])
        return super().clean()


def InscricaoFormFactory(request, programas):
    fields = dict()

    fields['aluno'] = forms.ModelChoiceField(
        queryset=Aluno.nao_fic.filter(situacao__ativo=True, caracterizacao__isnull=False),
        widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS),
        label='Aluno',
        required=True,
        help_text='Somente alunos não-FIC, ativos e com Caracterização Socioeconômica preenchida',
    )

    fields['data_cadastro'] = forms.DateTimeFieldPlus(initial=datetime.datetime.today())
    fields['edital'] = forms.ModelChoiceFieldPlus(label='Edital', queryset=Edital.objects.filter(ativo=True))
    if request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
        fields['programa'] = forms.ModelChoiceFieldPlus(label='Programa', queryset=Programa.objects.filter(id__in=programas.values_list('id', flat=True)))
    else:
        fields['programa'] = forms.ModelChoiceFieldPlus(
            label='Programa', queryset=Programa.objects.filter(instituicao=get_uo(request.user), id__in=programas.values_list('id', flat=True))
        )
        fields['aluno'].queryset = fields['aluno'].queryset.filter(curso_campus__diretoria__setor__uo=get_uo(request.user))

    fieldsets = ((None, {'fields': ('aluno', 'data_cadastro', 'edital', 'programa')}),)
    return type('InscricaoForm', (forms.BaseForm,), {'base_fields': fields, 'METHOD': 'POST', 'fieldsets': fieldsets, 'SUBMIT_LABEL': 'Continuar'})


class InscricaoAlunoForm(forms.FormPlus):
    programa = forms.ModelChoiceFieldPlus(label='Programa', queryset=Programa.objects)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['programa'].queryset = Programa.objects.all()

    fieldsets = ((None, {'fields': ('aluno', 'programa')}),)

    class Meta:
        exclude = 'aluno'


class InscricaoDetalhamentoAlimentacaoForm(forms.FormPlus):
    justificativa = forms.CharField(label='Motivo da Solicitação', widget=forms.Textarea, required=True)
    # TODO: com ae.SolicitacaoAlimentacao.load_choice_list não é mais preciso
    # colocar um campo para cada dia da semana. Basta um com CHOICES[Seg, Ter, Qua, Qui, Sex]
    seg_almoco = forms.BooleanField(label='Segunda', required=False)
    ter_almoco = forms.BooleanField(label='Terça', required=False)
    qua_almoco = seg = forms.BooleanField(label='Quarta', required=False)
    qui_almoco = seg = forms.BooleanField(label='Quinta', required=False)
    sex_almoco = seg = forms.BooleanField(label='Sexta', required=False)
    seg_janta = forms.BooleanField(label='Segunda', required=False)
    ter_janta = forms.BooleanField(label='Terça', required=False)
    qua_janta = seg = forms.BooleanField(label='Quarta', required=False)
    qui_janta = seg = forms.BooleanField(label='Quinta', required=False)
    sex_janta = seg = forms.BooleanField(label='Sexta', required=False)
    seg_cafe = forms.BooleanField(label='Segunda', required=False)
    ter_cafe = forms.BooleanField(label='Terça', required=False)
    qua_cafe = seg = forms.BooleanField(label='Quarta', required=False)
    qui_cafe = seg = forms.BooleanField(label='Quinta', required=False)
    sex_cafe = seg = forms.BooleanField(label='Sexta', required=False)

    fieldsets = (
        (None, {'fields': (('justificativa'),)}),
        ('Café da Manhã', {'fields': (('seg_cafe', 'ter_cafe', 'qua_cafe', 'qui_cafe', 'sex_cafe'),)}),
        ('Almoço', {'fields': (('seg_almoco', 'ter_almoco', 'qua_almoco', 'qui_almoco', 'sex_almoco'),)}),
        ('Jantar', {'fields': (('seg_janta', 'ter_janta', 'qua_janta', 'qui_janta', 'sex_janta'),)}),
    )

    def clean(self):
        dados = self.cleaned_data
        opcoes_alimentacao = [
            dados.get('seg_almoco'),
            dados.get('ter_almoco'),
            dados.get('qua_almoco'),
            dados.get('qui_almoco'),
            dados.get('sex_almoco'),
            dados.get('seg_janta'),
            dados.get('ter_janta'),
            dados.get('qua_janta'),
            dados.get('qui_janta'),
            dados.get('sex_janta'),
            dados.get('seg_cafe'),
            dados.get('ter_cafe'),
            dados.get('qua_cafe'),
            dados.get('qui_cafe'),
            dados.get('sex_cafe'),
        ]

        if not True in opcoes_alimentacao:
            raise forms.ValidationError('Selecione pelo menos uma opção de alimentação')
        return super().clean()


class InscricaoDetalhamentoIdiomaForm(forms.FormPlus):
    primeira_opcao = forms.ModelChoiceFieldPlus(queryset=OfertaTurma.objects.filter(ativa=True).order_by('idioma', 'turma'), label='Primeira Opção', required=True)
    segunda_opcao = forms.ModelChoiceFieldPlus(
        queryset=OfertaTurma.objects.filter(ativa=True).order_by('idioma', 'turma'),
        label='Segunda Opção',
        required=True,
        help_text='Informe a primeira opção igual a segunda caso só possua uma preferência',
    )

    justificativa = forms.CharField(label='Motivo da solicitação', widget=forms.Textarea, required=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        if Aluno.objects.filter(pessoa_fisica=user.get_profile()).exists():
            aluno = Aluno.objects.get(pessoa_fisica=user.get_profile())
            self.fields['primeira_opcao'].queryset = self.fields['primeira_opcao'].queryset.filter(campus=aluno.curso_campus.diretoria.setor.uo)
            self.fields['segunda_opcao'].queryset = self.fields['segunda_opcao'].queryset.filter(campus=aluno.curso_campus.diretoria.setor.uo)
        else:
            if not user.groups.filter(name='Coordenador de Atividades Estudantis Sistêmico').exists():
                self.fields['primeira_opcao'].queryset = self.fields['primeira_opcao'].queryset.filter(campus=get_uo(user))
                self.fields['segunda_opcao'].queryset = self.fields['segunda_opcao'].queryset.filter(campus=get_uo(user))


def InscricaoDetalhamentoTrabalhoFormFactory(usuario):
    fields = dict()
    fields['setor_preferencia'] = forms.ModelChoiceField(label='Setor Preferencial', queryset=Setor.objects.all(), widget=TreeWidget(), required=True)
    fields['turno'] = forms.ChoiceField(label='Turno', widget=forms.Select, required=True, choices=TurnoChoices.TURNO_CHOICES)
    fields['habilidades'] = forms.CharField(label='Habilidades', widget=forms.Textarea, required=True)

    fields['habilidades'].widget.attrs['cols'] = '75'
    fields['habilidades'].widget.attrs['rows'] = '4'
    fields['setor_preferencia'].widget.label_from_instance = lambda obj: "{}".format(obj.nome)

    fields['justificativa'] = forms.CharField(label='Motivo da solicitação', widget=forms.Textarea, required=True)

    fieldsets = ((None, {'fields': ('setor_preferencia', 'turno', 'habilidades', 'justificativa')}),)

    return type('InscricaoDetalhamentoTrabalhoForm', (forms.BaseForm,), {'base_fields': fields, 'METHOD': 'POST', 'fieldsets': fieldsets})


def InscricaoDetalhamentoPasseEstudantilFormFactory(usuario):
    fields = dict()
    fields['tipo_passe'] = forms.ChoiceField(label='Tipo de Passe', widget=forms.Select, required=True, choices=PassesChoices.PASSES_CHOICES)

    fields['justificativa'] = forms.CharField(label='Motivo da solicitação', widget=forms.Textarea, required=True)

    fieldsets = ((None, {'fields': ('tipo_passe', 'justificativa')}),)

    return type('InscricaoDetalhamentoPasseEstudantilForm', (forms.BaseForm,), {'base_fields': fields, 'METHOD': 'POST', 'fieldsets': fieldsets})


class DemandaAlunoAtendidaForm(forms.ModelFormPlus):
    demanda = forms.ModelChoiceField(queryset=DemandaAluno.ativas.all().order_by('nome'), empty_label=None)
    data = forms.DateTimeFieldPlus()
    valor = forms.DecimalFieldPlus(initial='0,00')

    def __init__(self, *args, **kwargs):
        demandas = kwargs.pop('demandas', None)
        super().__init__(*args, **kwargs)
        self.fields['demanda'].queryset = demandas

    class Meta:
        model = DemandaAlunoAtendida
        fields = ('demanda', 'data', 'quantidade', 'valor', 'observacao')


class AgendamentoRefeicaoForm(forms.ModelFormPlus):
    aluno = forms.ModelChoiceField(queryset=Aluno.objects, widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS), label='Aluno', required=True)
    data = forms.DateFieldPlus()

    class Meta:
        model = AgendamentoRefeicao
        fields = ('programa', 'aluno', 'data', 'tipo_refeicao')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if self.request.user.has_perm('ae.add_programa'):
            self.fields['programa'].queryset = self.fields['programa'].queryset.filter(tipo=Programa.TIPO_ALIMENTACAO)
        else:
            programa = get_object_or_404(Programa, instituicao=get_uo(self.request.user), tipo=Programa.TIPO_ALIMENTACAO)
            self.fields['programa'].queryset = self.fields['programa'].queryset.filter(id=programa.id)
        self.fields['data'].initial = datetime.datetime.today()

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data

        aluno = cleaned_data.get('aluno')
        tipo_refeicao = cleaned_data.get('tipo_refeicao')
        data = cleaned_data.get('data')
        programa = cleaned_data.get('programa')

        if aluno:
            if not aluno.situacao.ativo:
                raise forms.ValidationError('O aluno selecionado está inativo.')
            if not aluno.pessoa_fisica.template:
                raise forms.ValidationError('O aluno selecionado não possui digital cadastrada.')

        if AgendamentoRefeicao.objects.filter(cancelado=False, programa=programa, aluno=aluno, tipo_refeicao=tipo_refeicao, data=data).exists():
            raise forms.ValidationError('Este agendamento já foi cadastrado.')

        if not OfertaAlimentacao.objects.filter(campus=programa.instituicao, dia_inicio__lte=data, dia_termino__gte=data).exists():
            raise forms.ValidationError('Não existe Oferta de Refeição cadastrada na semana escolhida para o seu campus.')

        lista_de_participacoes = Participacao.objects.filter(programa=programa, aluno=aluno)
        lista_de_participacoes = lista_de_participacoes.filter(id__in=ParticipacaoAlimentacao.objects.values_list('participacao_id'))
        lista_de_participacoes = lista_de_participacoes.filter(Q(data_termino__isnull=True) | Q(data_termino__gte=data))
        if lista_de_participacoes:
            participacao_ativa = lista_de_participacoes[0]
            participacao_alimentacao = ParticipacaoAlimentacao.objects.get(participacao=participacao_ativa)
            if participacao_alimentacao.suspensa:
                raise forms.ValidationError('O aluno está com a participação suspensa.')

            if tipo_refeicao == AgendamentoRefeicao.TIPO_CAFE:
                cafe = SolicitacaoAlimentacao.objects.get(pk=participacao_alimentacao.solicitacao_atendida_cafe_id)

                if (
                    data.weekday() == 0
                    and cafe.seg
                    or data.weekday() == 1
                    and cafe.ter
                    or data.weekday() == 2
                    and cafe.qua
                    or data.weekday() == 3
                    and cafe.qui
                    or data.weekday() == 4
                    and cafe.sex
                    or data.weekday() == 5
                    and cafe.sab
                    or data.weekday() == 6
                    and cafe.dom
                ):
                    raise forms.ValidationError('O aluno já possui Café da Manhã para este dia.')

            elif tipo_refeicao == AgendamentoRefeicao.TIPO_ALMOCO:
                almoco = SolicitacaoAlimentacao.objects.get(pk=participacao_alimentacao.solicitacao_atendida_almoco.id)

                if (
                    data.weekday() == 0
                    and almoco.seg
                    or data.weekday() == 1
                    and almoco.ter
                    or data.weekday() == 2
                    and almoco.qua
                    or data.weekday() == 3
                    and almoco.qui
                    or data.weekday() == 4
                    and almoco.sex
                    or data.weekday() == 5
                    and almoco.sab
                    or data.weekday() == 6
                    and almoco.dom
                ):
                    raise forms.ValidationError('O aluno já possui Almoço para este dia.')

            elif tipo_refeicao == AgendamentoRefeicao.TIPO_JANTAR:
                jantar = SolicitacaoAlimentacao.objects.get(pk=participacao_alimentacao.solicitacao_atendida_janta_id)

                if (
                    data.weekday() == 0
                    and jantar.seg
                    or data.weekday() == 1
                    and jantar.ter
                    or data.weekday() == 2
                    and jantar.qua
                    or data.weekday() == 3
                    and jantar.qui
                    or data.weekday() == 4
                    and jantar.sex
                    or data.weekday() == 5
                    and jantar.sab
                    or data.weekday() == 6
                    and jantar.dom
                ):
                    raise forms.ValidationError('O aluno já possui Jantar para este dia.')

        return cleaned_data


class EstatisticasCaracterizacaoForm(forms.FormPlus):
    SUBMIT_LABEL = 'Buscar'
    METHOD = 'GET'

    choices = [['Ativo', 'Ativo'], ['Inativo', 'Inativo'], ['Todos', 'Todos']]
    inscricao_choices = [[3, 'Todos'], [1, 'Somente inscritos'], [2, 'Somente não inscritos']]
    participacao_choices = [[3, 'Todos'], [1, 'Somente participantes'], [4, 'Somente participantes atuais'], [2, 'Somente não participantes']]

    situacao_matricula = forms.ChoiceField(required=False, choices=choices, label='Filtrar por Situação:')

    modalidade = forms.ModelChoiceField(label='Filtrar por Modalidade:', required=False, queryset=Modalidade.objects, empty_label='Todos')

    campus = forms.ModelChoiceField(label='Filtrar por Campus:', required=False, queryset=UnidadeOrganizacional.objects.uo(), empty_label='Todos')

    inscricao_situacao = forms.ChoiceField(required=False, choices=inscricao_choices, label='Filtrar por Situação da Inscrição:')

    programa = forms.ChainedModelChoiceField(
        Programa.objects,
        label='Filtrar por Inscritos no Programa:',
        empty_label='Selecione o Campus',
        required=False,
        obj_label='titulo',
        form_filters=[('campus', 'instituicao_id')],
    )

    participacao_situacao = forms.ChoiceField(required=False, choices=participacao_choices, label='Filtrar por Situação da Participação:')

    participantes = forms.ChainedModelChoiceField(
        Programa.objects,
        label='Filtrar por Participantes do Programa:',
        empty_label='Selecione o Campus',
        required=False,
        obj_label='titulo',
        form_filters=[('campus', 'instituicao_id')],
    )

    diretoria = forms.ChainedModelChoiceField(
        Diretoria.objects,
        label='Filtrar por Diretoria:',
        empty_label='Selecione o Campus',
        required=False,
        obj_label='setor__sigla',
        form_filters=[('campus', 'setor__uo_id')],
        qs_filter='aluno__caracterizacao__isnull=False',
    )

    curso = forms.ChainedModelChoiceField(
        Curso.objects.order_by('descricao'),
        label='Filtrar por Curso:',
        empty_label='Selecione o Campus',
        required=False,
        obj_label='descricao',
        form_filters=[('campus', 'diretoria__setor__uo_id')],
        qs_filter='aluno__caracterizacao__isnull=False',
    )

    turma = forms.ModelChoiceFieldPlus(Turma.objects, label='Filtrar por Turma', required=False, widget=AutocompleteWidget(search_fields=Turma.SEARCH_FIELDS))

    ano = forms.ChoiceField(required=False, choices=[], label='Filtrar por Ano de Ingresso:')
    ano_letivo = forms.ChoiceField(required=False, choices=[], label='Filtrar por Ano Letivo:')

    incluir_fic = forms.BooleanField(widget=forms.CheckboxInput, required=False, label='Incluir FIC')

    class Media:
        js = ['/static/ae/js/estatisticasform.js']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        campi = UnidadeOrganizacional.objects.uo().all()
        user = self.request.user
        if not user.has_perm('ae.pode_ver_relatorio_caracterizacao_todos'):
            campi = campi.filter(id=get_uo().id)

        self.fields['campus'].queryset = campi

        ANO_CHOICES = []
        _anos = (
            Caracterizacao.objects.extra({'year': "CAST(EXTRACT(YEAR FROM data_matricula) AS TEXT)"})
            .values_list('year')
            .annotate(total_item=Count('aluno__data_matricula'))
            .values_list('year', flat=True)
            .order_by('-year')
        )
        for a in _anos:
            ANO_CHOICES.append(['{}'.format(a), '{}'.format(a)])
        ANO_CHOICES.append(['Todos', 'Todos'])
        self.fields['ano'].choices = ANO_CHOICES
        self.fields['ano_letivo'].choices = ANO_CHOICES


class RelatorioBolsasForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Buscar'

    categoria = forms.ModelChoiceField(label='Filtrar por Categoria:', required=False, queryset=CategoriaBolsa.objects.filter(ativa=True), empty_label='Todos')
    campus = forms.ModelChoiceField(label='Filtrar por Campus:', required=False, queryset=UnidadeOrganizacional.objects.uo(), empty_label='Todos')
    modalidade = forms.ModelChoiceField(label='Filtrar por Modalidade:', required=False, queryset=Modalidade.objects.all(), empty_label='Todos')
    curso = forms.ChainedModelChoiceField(
        Curso.objects.all().order_by('descricao'),
        label='Filtrar por Curso:',
        empty_label='Selecione um Campus e/ou uma Modalidade',
        required=False,
        obj_label='descricao',
        form_filters=[('campus', 'diretoria__setor__uo_id'), ('modalidade', 'modalidade_id')],
    )
    ano = forms.IntegerField(label='Filtrar por Ano:', required=False, widget=forms.Select())
    mes = forms.MesField(label='Filtrar por Mês:', required=False, choices=[], empty_label="Todos")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        campi = UnidadeOrganizacional.objects.uo().all()

        if not self.request.user.has_perm('ae.pode_ver_lista_bolsas_todos'):
            campi = campi.filter(id=get_uo().id)
            self.fields['campus'].queryset = campi

        maior_ano = ParticipacaoBolsa.objects.all().aggregate(Max('data_termino'))['data_termino__max'].year
        _anos = list(range(maior_ano, 1999, -1))
        ANO_CHOICES = [[a, '{}'.format(a)] for a in _anos]
        ANO_CHOICES.append(['0', 'Todos'])
        self.fields['ano'].widget.choices = ANO_CHOICES


class AlunosProgramaForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Buscar'
    ATIVOS = 'Ativos'
    INATIVOS = 'Inativos'

    PARTICIPANTES_CHOICES = (('', 'Todos'), (ATIVOS, ATIVOS), (INATIVOS, INATIVOS))

    campus = forms.ModelChoiceField(label='Filtrar por Campus:', required=False, queryset=UnidadeOrganizacional.objects.uo(), empty_label='Todos')
    tipo_programa = forms.ModelChoiceField(label='Tipo de Programa:', required=False, queryset=TipoPrograma.objects, empty_label='Todos')
    programa = forms.ChainedModelChoiceField(
        Programa.objects, label='Filtrar por Programa:', empty_label='Selecione o Campus', required=False, obj_label='titulo', form_filters=[('campus', 'instituicao_id')]
    )

    participantes = forms.ChoiceField(choices=PARTICIPANTES_CHOICES, label='Participantes', required=False)

    setores_do_campus = forms.BooleanField(label='Filtrar por Atuação em Setores do Campus', required=False)

    diretoria = forms.ChainedModelChoiceField(
        Diretoria.objects, label='Filtrar por Diretoria', empty_label='Selecione o Campus', required=False, obj_label='setor__sigla', form_filters=[('campus', 'setor__uo_id')]
    )

    modalidade = forms.ModelChoiceField(label='Filtrar por Modalidade', required=False, queryset=Modalidade.objects.all(), empty_label='Todos')

    curso = forms.ChainedModelChoiceField(
        Curso.objects.order_by('descricao'),
        label='Filtrar por Curso',
        empty_label='Selecione um Campus e/ou uma Modalidade',
        required=False,
        obj_label='descricao',
        form_filters=[('campus', 'diretoria__setor__uo_id'), ('modalidade', 'modalidade_id')],
        qs_filter='aluno__caracterizacao__isnull=False',
    )

    data_inicio = forms.DateFieldPlus(label='Início do Período', required=False)
    data_fim = forms.DateFieldPlus(label='Término do Período', required=False)

    class Media:
        js = ['/static/ae/js/lista_participantes_programas.js']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        campi = UnidadeOrganizacional.objects.uo().all()
        user = self.request.user
        if not user.has_perm('ae.pode_ver_relatorio_participacao_todos'):
            campi = campi.filter(id=get_uo().id)
        self.fields['campus'].queryset = campi
        ano = datetime.datetime.now().date().year
        self.fields['data_inicio'].initial = date(ano, 1, 1)
        self.fields['data_fim'].initial = date(ano, 12, 13)

    def clean(self):
        ano = datetime.datetime.now().date().year
        data_inicio = self.cleaned_data.get('data_inicio', date(ano, 1, 1))
        data_fim = self.cleaned_data.get('data_fim', date(ano, 12, 13))
        if data_fim - data_inicio > timedelta(days=365):
            raise ValidationError('Diferença entre as datas não podem ser maiores que 1 ano.')
        return self.cleaned_data


class OfertaPasseForm(forms.ModelFormPlus):
    class Meta:
        model = OfertaPasse
        exclude = ('atualizado_por', 'atualizado_em')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        eh_diretor_geral = user.groups.filter(name='Diretor Geral').exists()
        if not user.groups.filter(name='Coordenador de Atividades Estudantis Sistêmico').exists() and not eh_diretor_geral:
            self.fields['campus'].queryset = self.fields['campus'].queryset.filter(id=get_uo(user).id)

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data
        if cleaned_data.get('valor_passe') <= 0:
            raise forms.ValidationError('O valor deve ser maior que zero.')
        if cleaned_data.get('data_inicio').year != cleaned_data.get('data_termino').year:
            raise forms.ValidationError('As datas de início e término não podem ser em anos diferentes.')
        if cleaned_data.get('data_inicio') >= cleaned_data.get('data_termino'):
            raise ValidationError('A data de início não pode ser maior ou igual a data de término.')
        if cleaned_data.get('campus') and self.instance.pk:
            for oferta in OfertaPasse.objects.filter(campus=cleaned_data.get('campus')).exclude(pk=self.instance.pk):
                if existe_conflito_entre_intervalos([oferta.data_inicio, oferta.data_termino, cleaned_data.get('data_inicio'), cleaned_data.get('data_termino')]):
                    raise ValidationError('O período informado está em conflito com períodos anteriores.')
        return cleaned_data


class ValorTotalAuxiliosForm(forms.ModelFormPlus):
    campus = forms.ModelChoiceFieldPlus(label='Campus', required=True,
                                        queryset=UnidadeOrganizacional.objects.uo())

    class Meta:
        model = ValorTotalAuxilios
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        eh_diretor_geral = user.groups.filter(name='Diretor Geral').exists()
        if not user.groups.filter(name='Coordenador de Atividades Estudantis Sistêmico').exists() and not eh_diretor_geral:
            self.fields['campus'].queryset = self.fields['campus'].queryset.filter(id=get_uo(user).id)

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data
        if cleaned_data.get('valor') <= 0:
            raise forms.ValidationError('O valor deve ser maior que zero.')
        if cleaned_data.get('data_inicio').year != cleaned_data.get('data_termino').year:
            raise forms.ValidationError('As datas de início e término não podem ser em anos diferentes.')
        if cleaned_data.get('data_inicio') >= cleaned_data.get('data_termino'):
            raise ValidationError('A data de início não pode ser maior ou igual a data de saída.')
        if cleaned_data.get('campus'):
            for oferta in ValorTotalAuxilios.objects.filter(campus=cleaned_data.get('campus'), tipoatendimentosetor=cleaned_data.get('tipoatendimentosetor')).exclude(
                pk=self.instance.pk
            ):
                if existe_conflito_entre_intervalos([oferta.data_inicio, oferta.data_termino, cleaned_data.get('data_inicio'), cleaned_data.get('data_termino')]):
                    raise ValidationError('O período informado está em conflito com períodos anteriores.')
        return cleaned_data


class ValorTotalBolsasForm(forms.ModelFormPlus):
    campus = forms.ModelChoiceFieldPlus(label='Campus', required=True,
                                        queryset=UnidadeOrganizacional.objects.uo())

    class Meta:
        model = ValorTotalBolsas
        exclude = ()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        eh_diretor_geral = user.groups.filter(name='Diretor Geral').exists()
        if not user.groups.filter(name='Coordenador de Atividades Estudantis Sistêmico').exists() and not eh_diretor_geral:
            self.fields['campus'].queryset = self.fields['campus'].queryset.filter(id=get_uo(user).id)

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data
        if cleaned_data.get('valor') <= 0:
            raise forms.ValidationError('O valor deve ser maior que zero.')
        if cleaned_data.get('data_inicio').year != cleaned_data.get('data_termino').year:
            raise forms.ValidationError('As datas de início e término não podem ser em anos diferentes.')
        if cleaned_data.get('data_inicio') >= cleaned_data.get('data_termino'):
            raise ValidationError('A data de início não pode ser maior ou igual a data de saída.')
        if cleaned_data.get('campus'):
            for oferta in ValorTotalBolsas.objects.filter(campus=cleaned_data.get('campus'), categoriabolsa=cleaned_data.get('categoriabolsa')).exclude(pk=self.instance.pk):
                if existe_conflito_entre_intervalos([oferta.data_inicio, oferta.data_termino, cleaned_data.get('data_inicio'), cleaned_data.get('data_termino')]):
                    raise ValidationError('O período informado está em conflito com períodos anteriores.')
        return cleaned_data


class OfertaTurmaForm(forms.ModelFormPlus):
    campus = forms.ModelChoiceField(label='Campus', required=True,
                                    queryset=UnidadeOrganizacional.objects.uo())

    class Meta:
        model = OfertaTurma
        exclude = ('atualizado_por', 'atualizado_em')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        if not user.groups.filter(name='Coordenador de Atividades Estudantis Sistêmico').exists():
            self.fields['campus'].queryset = self.fields['campus'].queryset.filter(id=get_uo(user).id)


class OfertaAlimentacaoForm(forms.ModelFormPlus):
    class Meta:
        model = OfertaAlimentacao
        exclude = ('atualizado_por', 'atualizado_em')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        if user.has_perm('ae.pode_gerenciar_ofertaalimentacao_todos') and self.instance.id:
            self.fields['campus'].queryset = self.fields['campus'].queryset.filter(id=self.instance.campus_id)

        elif user.has_perm('ae.pode_gerenciar_ofertaalimentacao_do_campus') and not user.has_perm('ae.pode_gerenciar_ofertaalimentacao_todos'):
            self.fields['campus'].queryset = self.fields['campus'].queryset.filter(id=get_uo(user).id)
            self.fields['campus'].initial = get_uo(user).id

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()

        if (
            not self.instance.id
            and cleaned_data.get('dia_inicio')
            and cleaned_data.get('campus')
            and OfertaAlimentacao.objects.filter(campus=cleaned_data.get('campus'), dia_inicio=cleaned_data.get('dia_inicio')).exists()
        ):
            self.add_error('dia_inicio', 'Já existe uma oferta de alimentação com início na segunda-feira informada.')

        if (
            self.instance.id
            and cleaned_data.get('dia_inicio')
            and cleaned_data.get('campus')
            and OfertaAlimentacao.objects.filter(campus=cleaned_data.get('campus'), dia_inicio=cleaned_data.get('dia_inicio')).exclude(id=self.instance.id).exists()
        ):
            self.add_error('dia_inicio', 'Já existe uma oferta de alimentação com início na segunda-feira informada.')
        if cleaned_data.get('dia_inicio') and not (cleaned_data.get('dia_inicio').weekday() == 0):
            self.add_error('dia_inicio', 'O dia inicial deve ser uma segunda-feira.')

        if cleaned_data.get('dia_termino') and not (cleaned_data.get('dia_termino').weekday() == 4):
            self.add_error('dia_termino', 'O dia final deve ser uma sexta-feira.')

        if cleaned_data.get('dia_inicio') and cleaned_data.get('dia_termino'):
            if cleaned_data.get('dia_termino') <= cleaned_data.get('dia_inicio'):
                self.add_error('dia_termino', 'O dia final deve ser maior que o dia inicial.')
            elif (cleaned_data.get('dia_termino') - cleaned_data.get('dia_inicio')).days > 5:
                self.add_error('dia_termino', 'O dia final deve ser na mesma semana que o dia inicial.')


class OfertaValorRefeicaoForm(forms.ModelFormPlus):
    campus = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().all(), required=True)

    class Meta:
        model = OfertaValorRefeicao
        exclude = ('atualizado_por', 'atualizado_em')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        eh_diretor_geral = user.groups.filter(name='Diretor Geral').exists()
        if not user.groups.filter(name='Coordenador de Atividades Estudantis Sistêmico').exists() and not eh_diretor_geral:
            self.fields['campus'].queryset = self.fields['campus'].queryset.filter(id=get_uo(user).id)

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data
        if cleaned_data.get('valor') <= 0:
            raise forms.ValidationError('O valor deve ser maior que zero.')
        if cleaned_data.get('data_inicio').year != cleaned_data.get('data_termino').year:
            raise forms.ValidationError('As datas de início e término não podem ser de anos diferentes.')
        if cleaned_data.get('data_inicio') >= cleaned_data.get('data_termino'):
            raise ValidationError('A data de início não pode ser maior ou igual a data de saída.')
        if cleaned_data.get('campus'):
            for oferta in OfertaValorRefeicao.objects.filter(campus=cleaned_data.get('campus')).exclude(pk=self.instance.pk):
                if existe_conflito_entre_intervalos([oferta.data_inicio, oferta.data_termino, cleaned_data.get('data_inicio'), cleaned_data.get('data_termino')]):
                    raise ValidationError('O período informado está em conflito com períodos anteriores.')
        return cleaned_data


class OfertaBolsaForm(forms.ModelFormPlus):
    campus = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().all(), required=True)
    setor = forms.ModelChoiceField(label='Setor', queryset=Setor.objects.all(), widget=TreeWidget(), required=True)

    class Meta:
        model = OfertaBolsa
        exclude = ('atualizado_por', 'atualizado_em')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['setor'].widget.label_from_instance = lambda obj: "{} ({})".format(obj.nome, obj.sigla)
        user = self.request.user
        if not user.groups.filter(name='Coordenador de Atividades Estudantis Sistêmico').exists():
            self.fields['campus'].queryset = self.fields['campus'].queryset.filter(id=get_uo(user).id)
        instance = getattr(self, 'instance', None)
        if instance and instance.pk:
            self.fields['disponivel'].widget.attrs['disabled'] = False

    def clean(self):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data
        if self.instance and self.instance.pk:
            hoje = date.today()
            participacao = ParticipacaoTrabalho.objects.filter(
                Q(bolsa_concedida=self.instance), Q(participacao__data_termino__isnull=True) | Q(participacao__data_termino__gte=hoje)
            ).exists()
            if participacao and not self.cleaned_data['ativa']:
                raise forms.ValidationError('Não é possível inativar uma oferta vinculada a uma participação.')

            if participacao and self.cleaned_data['disponivel']:
                raise forms.ValidationError('Não é possível tornar disponível uma oferta vinculada a uma participação.')

        return cleaned_data


class OfertaValorBolsaForm(forms.ModelFormPlus):
    campus = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().all(), required=True)

    class Meta:
        model = OfertaValorBolsa
        exclude = ('atualizado_por', 'atualizado_em')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        eh_diretor_geral = user.groups.filter(name='Diretor Geral').exists()
        if not user.groups.filter(name='Coordenador de Atividades Estudantis Sistêmico').exists() and not eh_diretor_geral:
            self.fields['campus'].queryset = self.fields['campus'].queryset.filter(id=get_uo(user).id)

    def clean(self, *args, **kwargs):
        cleaned_data = super().clean()
        if self.errors:
            return cleaned_data
        if cleaned_data.get('valor') <= 0:
            raise forms.ValidationError('O valor deve ser maior que zero.')
        if cleaned_data.get('data_inicio').year != cleaned_data.get('data_termino').year:
            raise forms.ValidationError('As datas de início e término não podem ser em anos diferentes.')
        if cleaned_data.get('data_inicio') >= cleaned_data.get('data_termino'):
            raise ValidationError('A data de início não pode ser maior ou igual a data de término.')
        if cleaned_data.get('campus'):
            for oferta in OfertaValorBolsa.objects.filter(campus=cleaned_data.get('campus')).exclude(pk=self.instance.pk):
                if existe_conflito_entre_intervalos([oferta.data_inicio, oferta.data_termino, cleaned_data.get('data_inicio'), cleaned_data.get('data_termino')]):
                    raise ValidationError('O período informado está em conflito com períodos anteriores.')
        return cleaned_data


class RelatorioSemanalRefeitorioForm(forms.FormPlus):
    data = forms.DateFieldPlus(label='Informar uma Segunda-feira')
    tipo_refeicao = forms.ChoiceField(
        choices=[(DemandaAluno.CAFE, 'Café da manhã'), (DemandaAluno.ALMOCO, 'Almoço'), (DemandaAluno.JANTAR, 'Jantar')],
        initial=DemandaAluno.ALMOCO,
        widget=forms.Select(),
        label='Filtrar por Tipo de Refeição',
    )
    categoria = forms.ModelChoiceField(queryset=CategoriaAlimentacao.objects.all(), label='Filtrar por Categoria', empty_label='Todas as categorias', required=False)
    agendados = forms.BooleanField(widget=forms.CheckboxInput, required=False, label='Somente Refeições Agendadas')
    avulsos = forms.BooleanField(widget=forms.CheckboxInput, required=False, label='Somente Atendimentos Avulsos')

    def clean_data(self):
        dias = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']
        if self.cleaned_data['data'].weekday() != 0:
            raise forms.ValidationError('O dia informado é um(a) {}. Por favor, informe uma segunda-feira.'.format(dias[self.cleaned_data['data'].weekday()]))
        return self.cleaned_data['data']

    def clean_tipo_refeicao(self):
        return int(self.cleaned_data['tipo_refeicao'])

    def clean(self):
        if self.cleaned_data.get('categoria') and self.cleaned_data.get('agendados'):
            raise forms.ValidationError('Não é possível filtrar os atendimentos agendados por categoria.')
        if self.cleaned_data.get('categoria') and self.cleaned_data.get('avulsos'):
            raise forms.ValidationError('Não é possível filtrar os atendimentos avulsos por categoria.')
        if self.cleaned_data.get('agendados') and self.cleaned_data.get('avulsos'):
            raise forms.ValidationError('Não é possível filtrar os atendimentos agendados e avulsos.')


SEGUNDA = 'Seg'
TERCA = 'Ter'
QUARTA = 'Qua'
QUINTA = 'Qui'
SEXTA = 'Sex'


class AdicionarParticipacaoAlimentacao(forms.FormPlus):
    CHOICE_DIAS = [[SEGUNDA, SEGUNDA], [TERCA, TERCA], [QUARTA, QUARTA], [QUINTA, QUINTA], [SEXTA, SEXTA]]
    cafe = forms.MultipleChoiceField(choices=CHOICE_DIAS, widget=forms.CheckboxSelectMultiple, required=False, label='Café da Manhã')
    almoco = forms.MultipleChoiceField(choices=CHOICE_DIAS, widget=forms.CheckboxSelectMultiple, required=False, label='Almoço')
    jantar = forms.MultipleChoiceField(choices=CHOICE_DIAS, widget=forms.CheckboxSelectMultiple, required=False)
    data_entrada = forms.DateFieldPlus(required=True, label='Data da Entrada')
    categoria = forms.ModelChoiceField(queryset=CategoriaAlimentacao.objects.all(), required=True)
    motivo_entrada = forms.CharField(widget=forms.Textarea, required=True, label='Motivo de Entrada')

    def clean(self):
        dados = self.cleaned_data
        if len(dados.get('almoco')) == 0 and len(dados.get('jantar')) == 0 and len(dados.get('cafe')) == 0:  # não selecionou nada
            raise forms.ValidationError('Selecione pelo menos um dia da semana.')
        return super().clean()


class ParticipacaoForm(forms.FormPlus):
    data_termino = forms.DateFieldPlus(required=False, label='Data de Saída')
    motivo_termino = forms.CharField(widget=forms.Textarea, required=False, label='Motivo de Saída')

    def __init__(self, *args, **kargs):
        self.__participacao = kargs.pop('participacao', None)
        super().__init__(*args, **kargs)
        self.fields['data_termino'].initial = self.__participacao.data_termino
        self.fields['motivo_termino'].initial = self.__participacao.motivo_termino

    def clean_motivo_termino(self):
        cleaned_data = self.cleaned_data
        motivo_termino = cleaned_data.get('motivo_termino')
        data_termino = cleaned_data.get('data_termino')
        if motivo_termino and not data_termino:
            raise forms.ValidationError('Não é possível ter um Motivo de Saída se não há uma Data de Saída.')
        if not motivo_termino and data_termino:
            raise forms.ValidationError('Informe o Motivo de Saída.')
        participacao = Participacao.objects.filter(aluno=self.__participacao.aluno, programa=self.__participacao.programa)
        participacao = participacao.filter(Q(data_termino__isnull=True) | Q(data_termino__gte=datetime.date.today()))
        if not data_termino and self.__participacao.data_termino and participacao.exists():
            raise forms.ValidationError('Não é possível tornar essa participação ativa. Note que já existe uma participação aberta neste programa.')
        return cleaned_data['motivo_termino']


class ParticipacaoBolsaModelForm(forms.ModelFormPlus):
    aluno = forms.ModelChoiceField(queryset=Aluno.caracterizados.all(), widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS), label='Aluno', required=True)
    categoria = forms.ModelChoiceField(label='Categoria da Bolsa', queryset=CategoriaBolsa.objects.filter(vinculo_programa=False, ativa=True), required=True)
    setor = forms.ModelChoiceField(label='Setor', queryset=Setor.objects.all(), widget=TreeWidget(), required=False)
    data_inicio = forms.DateFieldPlus(label='Data de Entrada')
    data_termino = forms.DateFieldPlus(label='Data de Saída', required=False)

    class Meta:
        model = ParticipacaoBolsa
        exclude = ['aluno_participante_projeto']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        if not user.groups.filter(name='Coordenador de Atividades Estudantis Sistêmico').exists():
            uo = get_uo(user).id
            self.fields['aluno'] = forms.ModelChoiceField(
                queryset=Aluno.caracterizados.filter(curso_campus__diretoria__setor__uo=uo),
                widget=AutocompleteWidget(search_fields=Aluno.SEARCH_FIELDS),
                label='Aluno',
                required=True,
            )

    def clean_data_termino(self):
        if 'data_termino' in self.cleaned_data and self.cleaned_data['data_termino'] and 'data_inicio' in self.cleaned_data and self.cleaned_data['data_inicio']:
            if self.cleaned_data['data_termino'] < self.cleaned_data['data_inicio']:
                raise forms.ValidationError('A data de término deve ser maior que a data de início.')
            return self.cleaned_data['data_termino']

    def clean(self):
        if self.cleaned_data.get('data_inicio') and self.cleaned_data.get('aluno'):
            aluno = self.cleaned_data.get('aluno')
            data_inicio = self.cleaned_data.get('data_inicio')
            data_termino = self.cleaned_data.get('data_termino')
            if not self.instance.pk:
                qs_participacao_bolsa = ParticipacaoBolsa.objects.filter(aluno=aluno)
                qs_participacao_bolsa_data_termino_preenchido = qs_participacao_bolsa.filter(data_termino__isnull=False)  # tem data termino no banco
                if 'data_termino' in self.cleaned_data and self.cleaned_data['data_termino']:
                    qs_participacao_bolsa_data_termino_preenchido = qs_participacao_bolsa_data_termino_preenchido.filter(
                        Q(data_inicio__range=(data_inicio, data_termino)) | Q(data_termino__range=(data_inicio, data_termino))
                    )
                else:
                    qs_participacao_bolsa_data_termino_preenchido = qs_participacao_bolsa_data_termino_preenchido.filter(
                        data_termino__gt=data_inicio
                    )  # data_final do banco tem q menor do que a data_inicio do formulario pra deixar passar
                if qs_participacao_bolsa_data_termino_preenchido:
                    raise forms.ValidationError('Já existe uma bolsa cadastrada para o período informado.')
                qs_participacao_bolsa_data_termino_nao_preenchido = qs_participacao_bolsa.filter(data_termino__isnull=True)
                if qs_participacao_bolsa_data_termino_nao_preenchido:
                    raise forms.ValidationError('Já existe uma bolsa cadastrada sem data de término informada.')
        return self.cleaned_data


SIM = 'Sim'
NAO = 'Não'


class BuscarAlunoForm(forms.FormPlus):
    METHOD = 'GET'

    # DADOS PESSOAIS
    matricula = forms.CharField(max_length=50, required=False, label='Matrícula', help_text='Filtrar por matrícula ou parte')
    nome = forms.CharField(max_length=80, required=False, help_text='Filtrar por parte do nome')
    CHOICES_FAIXA_ETARIA = [[0, 'Todos'], [1, 'Até 14 anos'], [2, 'Entre 15 e 17 anos'], [3, 'Entre 18 e 29 anos'], [4, 'Entre 30 e 49 anos'], [5, 'Acima de 50 anos']]
    faixa_etaria = forms.ChoiceField(required=False, choices=CHOICES_FAIXA_ETARIA, label='Faixa Etária')

    # DADOS ACADEMICOS
    campus = forms.ModelChoiceField(
        label='Campus', required=False, queryset=UnidadeOrganizacional.objects.uo().all(), empty_label='Todos', widget=forms.Select(attrs={'onchange': "$('#filtro').submit();"})
    )
    curso = forms.ModelChoiceField(
        label='Curso',
        queryset=Curso.objects.all(),
        required=False,
        widget=AutocompleteWidget(search_fields=Curso.SEARCH_FIELDS),
        help_text='Permite buscar todos os cursos, inclusive os de modalidade FIC',
    )
    CHOICES_SITUACAO_MATRICULA = [['Ativo', 'Ativo'], ['Inativo', 'Inativo']]
    situacao = forms.ChoiceField(
        required=False, choices=CHOICES_SITUACAO_MATRICULA, label='Situação de Matrícula', widget=forms.Select(attrs={'onchange': "$('#filtro').submit();"})
    )

    tipo_matricula = forms.ModelChoiceField(SituacaoMatricula.objects, required=False, label='Tipo de Matrícula', widget=forms.Select(attrs={'onchange': "$('#filtro').submit();"}))
    modalidade = forms.ModelMultiplePopupChoiceField(Modalidade.objects, label='Modalidade', required=False)

    # DADOS DA CARACTERIZACAO
    CHOICES_CARACTERIZACAO = [[SIM, SIM], [NAO, NAO]]
    caracterizacao = forms.ChoiceField(label='Com caracterização', choices=CHOICES_CARACTERIZACAO, required=False)
    CHOICES_SALARIO_MINIMO = [
        [0, 'Todas'],
        [1, 'Até 1 salário mínimo'],
        [2, 'Entre 1 e 2 salários mínimos'],
        [3, 'Entre 2 e 5 salários mínimos'],
        [4, 'Entre 5 e 10 salários mínimos'],
        [5, 'Acima de 10 salários mínimos'],
    ]
    renda_bruta_familiar = forms.ChoiceField(label='Renda Bruta Familiar', choices=CHOICES_SALARIO_MINIMO, required=False)
    raca = forms.ModelChoiceField(label='Etnia/Raça/Cor', required=False, queryset=Raca.objects.all(), empty_label='Todos')
    necessidades_especiais = forms.ChoiceField(label='Necessidade Especial', choices=(), required=False)
    procedencia_ensino_medio = forms.ModelChoiceField(label='Procedência Escolar do Ensino Médio', required=False, queryset=TipoEscola.objects.all(), empty_label='Todos')
    procedencia_ensino_fundamental = forms.ModelChoiceField(
        label='Procedência Escolar do Ensino Fundamental', required=False, queryset=TipoEscola.objects.all(), empty_label='Todos'
    )

    # DADOS DO SERVICO SOCIAL
    atendimentos = forms.ModelChoiceField(label='Atendimentos Recebidos', required=False, queryset=DemandaAluno.ativas.all(), empty_label='Todos')
    ano_limite = datetime.date.today().year
    ANO_CHOICES = [['Todos', 'Todos']]
    ANO_CHOICES += [['{}'.format(ano), '{}'.format(ano)] for ano in range(ano_limite, 2006, -1)]
    atendimentos_em = forms.ChoiceField(label='Atendimentos Recebidos em', required=False, choices=ANO_CHOICES)
    programa_inscricoes_sim_nao = forms.BooleanField(label='Tem inscrição em algum Programa', required=False)
    programa_inscricoes_inicial = forms.DateFieldPlus(label='Inscrito em Programa a partir de', required=False)
    programa_inscricoes_final = forms.DateFieldPlus(label='Inscrito em Programa até', required=False)
    programa_inscricoes = forms.ModelChoiceField(label='Inscrito em Programa', queryset=Programa.objects.all(), required=False)
    programa_participacoes_sim_nao = forms.BooleanField(label='Tem participação em algum Programa', required=False)
    programa_participacoes = forms.ModelChoiceField(label='Participante em Programa', queryset=Programa.objects.all(), required=False)
    tipo_programa_inscricao = forms.ModelChoiceField(label='Tipo de Programa de Inscrição:', required=False, queryset=TipoPrograma.objects, empty_label='Todos')
    tipo_programa_participacao = forms.ModelChoiceField(label='Tipo de Programa de Participação:', required=False, queryset=TipoPrograma.objects, empty_label='Todos')

    # OPÇÕES DE EXIBICAO
    ver_nome = forms.BooleanField(label='Nome', initial=True, required=False)
    ver_matricula = forms.BooleanField(label='Matrícula', initial=True, required=False)
    ver_curso = forms.BooleanField(label='Curso', initial=False, required=False)
    ver_polo_ead = forms.BooleanField(label='Polo EAD', initial=False, required=False)
    ver_informacoes_contato = forms.BooleanField(label='Dados de Contato', initial=False, required=False)
    ver_rg_cpf = forms.BooleanField(label='RG e CPF', initial=False, required=False)
    ver_dados_pessoais = forms.BooleanField(label='Dados Pessoais', initial=False, required=False)
    ver_dados_educacionais = forms.BooleanField(label='Dados Educacionais', initial=False, required=False)
    ver_dados_familiares = forms.BooleanField(label='Dados Familiares', initial=False, required=False)
    ver_acesso_tecnologias = forms.BooleanField(label='Acesso às Tecnologias da Informação e Comunicação', initial=False, required=False)
    ver_inscricoes_em_programas = forms.BooleanField(label='Inscrições em Programas', initial=False, required=False)
    ver_documentacao = forms.BooleanField(label='Documentação', initial=False, required=False)

    fieldsets = (
        ('Filtros de Dados Pessoais', {'fields': (('matricula', 'nome'), ('faixa_etaria'))}),
        ('Filtros de Dados Acadêmicos', {'fields': (('campus', 'curso'), ('situacao', 'tipo_matricula'), 'modalidade')}),
        (
            'Filtros de Dados da Caracterização',
            {'fields': (('caracterizacao'), ('raca', 'renda_bruta_familiar', 'necessidades_especiais'), ('procedencia_ensino_medio', 'procedencia_ensino_fundamental'))},
        ),
        (
            'Filtros de Dados do Serviço Social',
            {
                'fields': (
                    ('atendimentos', 'atendimentos_em'),
                    ('programa_inscricoes_sim_nao', 'programa_inscricoes', 'tipo_programa_inscricao'),
                    ('programa_inscricoes_inicial', 'programa_inscricoes_final'),
                    ('programa_participacoes_sim_nao', 'programa_participacoes', 'tipo_programa_participacao'),
                )
            },
        ),
        (
            'Opções de Exibição (Gerais)',
            {'fields': (('ver_curso', 'ver_rg_cpf', 'ver_polo_ead'), ('ver_informacoes_contato'), ('ver_inscricoes_em_programas', 'ver_documentacao'))},
        ),
        ('Opções de Exibição (Caracterização Socioeconômica)', {'fields': (('ver_dados_pessoais', 'ver_dados_educacionais', 'ver_dados_familiares'), ('ver_acesso_tecnologias'))}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        if user.has_perm('ae.pode_ver_lista_dos_alunos_campus') and not user.has_perm('ae.pode_ver_lista_dos_alunos'):
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo().filter(pk=get_uo(user).id)
            self.fields['campus'].empty_label = None
            self.fields['programa_inscricoes'].queryset = Programa.objects.filter(instituicao=get_uo(user))
            self.fields['programa_participacoes'].queryset = Programa.objects.filter(instituicao=get_uo(user))
            self.fields['curso'].queryset = Curso.objects.filter(diretoria__setor__uo=get_uo(user))

        if self.data.get('campus'):
            campus = UnidadeOrganizacional.objects.uo().get(pk=self.data.get('campus'))
            self.fields['programa_inscricoes'].queryset = Programa.objects.filter(instituicao=campus)
            self.fields['programa_participacoes'].queryset = Programa.objects.filter(instituicao=campus)
            self.fields['curso'].queryset = Curso.objects.filter(diretoria__setor__uo=campus)

        if self.data.get('caracterizacao') == SIM or self.data.get('caracterizacao') is None:
            NECESSIDADES_ESPECIAIS_CHOICES = [['', ''], ['Nenhuma', 'Nenhuma'], ['Qualquer', 'Qualquer']]
            NECESSIDADES_ESPECIAIS_CHOICES += [
                ['{}'.format(necessidade_especial.pk), '{}'.format(necessidade_especial)] for necessidade_especial in NecessidadeEspecial.objects.all()
            ]
            self.fields['necessidades_especiais'].choices = NECESSIDADES_ESPECIAIS_CHOICES
            self.fields['programa_inscricoes'].empty_label = 'Selecione'
            self.fields['programa_participacoes'].empty_label = 'Selecione'
        else:
            self.fields['necessidades_especiais'].initial = []
            self.fields['necessidades_especiais'] = SpanField(widget=SpanWidget(), label='Necessidade Especial')
            self.fields['necessidades_especiais'].widget.label_value = 'Filtro "Sem caracterização" ativo.'
            self.fields['necessidades_especiais'].widget.original_value = []
            self.fields['necessidades_especiais'].required = False
            self.fields['raca'].queryset = Raca.objects.none()
            self.fields['raca'].initial = []
            self.fields['raca'] = SpanField(widget=SpanWidget(), label='Etnia/Raça/Cor')
            self.fields['raca'].widget.label_value = 'Filtro "Sem caracterização" ativo.'
            self.fields['raca'].widget.original_value = []
            self.fields['raca'].required = False
            self.fields['programa_inscricoes'].queryset = Programa.objects.none()
            self.fields['programa_inscricoes'].initial = []
            self.fields['programa_inscricoes'] = SpanField(widget=SpanWidget(), label='Inscrito em Programa')
            self.fields['programa_inscricoes'].widget.label_value = 'Filtro "Sem caracterização" ativo.'
            self.fields['programa_inscricoes'].widget.original_value = []
            self.fields['programa_inscricoes'].required = False
            self.fields['programa_participacoes'].queryset = Programa.objects.none()
            self.fields['programa_participacoes'].initial = []
            self.fields['programa_participacoes'] = SpanField(widget=SpanWidget(), label='Participante em Programa')
            self.fields['programa_participacoes'].widget.label_value = 'Filtro "Sem caracterização" ativo.'
            self.fields['programa_participacoes'].widget.original_value = []
            self.fields['programa_participacoes'].required = False
            self.fields['procedencia_ensino_medio'].initial = []
            self.fields['procedencia_ensino_medio'] = SpanField(widget=SpanWidget(), label='Procedência Escolar do Ensino Médio')
            self.fields['procedencia_ensino_medio'].widget.label_value = 'Filtro "Sem caracterização" ativo.'
            self.fields['procedencia_ensino_medio'].widget.original_value = []
            self.fields['procedencia_ensino_medio'].required = False
            self.fields['procedencia_ensino_fundamental'].initial = []
            self.fields['procedencia_ensino_fundamental'] = SpanField(widget=SpanWidget(), label='Procedência Escolar do Ensino Fundamental')
            self.fields['procedencia_ensino_fundamental'].widget.label_value = 'Filtro "Sem caracterização" ativo.'
            self.fields['procedencia_ensino_fundamental'].widget.original_value = []
            self.fields['procedencia_ensino_fundamental'].required = False


class ListaAtendidosAuxiliosForm(forms.FormPlus):
    METHOD = 'GET'

    categoria = forms.ModelChoiceField(label='Filtrar por Categoria:', required=False, queryset=TipoAtendimentoSetor.objects.all(), empty_label='Todos')
    campus = forms.ModelChoiceField(label='Filtrar por Campus', queryset=UnidadeOrganizacional.objects.uo().all(), required=False, empty_label='Todos')
    modalidade = forms.ModelChoiceField(label='Filtrar por Modalidade', required=False, queryset=Modalidade.objects.all(), empty_label='Todos')
    curso = forms.ChainedModelChoiceField(
        Curso.objects.all().order_by('descricao'),
        label='Filtrar por Curso',
        empty_label='Selecione um Campus e/ou uma Modalidade',
        required=False,
        obj_label='descricao',
        form_filters=[('campus', 'diretoria__setor__uo_id'), ('modalidade', 'modalidade_id')],
    )
    ano = forms.IntegerField(label='Filtrar por Ano', widget=forms.Select())
    mes = forms.MesField(label='Filtrar por Mês:', required=False, choices=[], empty_label="Todos")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ano_limite = datetime.date.today().year
        ANO_CHOICES = [(ano, '{}'.format(ano)) for ano in range(ano_limite, 2009, -1)]
        self.fields['ano'].widget.choices = ANO_CHOICES

        if not self.request.user.has_perm('ae.pode_visualizar_auxilios'):
            self.fields.pop('campus')

    def processar(self):
        categoria = self.cleaned_data.get('categoria', None)
        ano = self.cleaned_data.get('ano', None)
        campus = self.cleaned_data.get('campus', None)
        modalidade = self.cleaned_data.get('modalidade', None)
        user = self.request.user

        auxilios = AtendimentoSetor.objects.all()

        if categoria:
            auxilios = auxilios.filter(tipoatendimentosetor=categoria)

        if ano:
            auxilios = auxilios.filter(data__year=ano)

            mes = self.cleaned_data.get('mes', None)
            if mes and mes != 0:
                auxilios = auxilios.filter(data__month=mes).order_by('data')

        if campus or not user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
            if not campus:
                campus = get_uo(user)
            auxilios = auxilios.filter(campus=campus)

        alunos_ids = auxilios.values_list('alunos', flat=True)
        alunos = Aluno.objects.filter(id__in=alunos_ids).distinct()

        if modalidade:
            alunos = alunos.filter(curso_campus__modalidade=modalidade)

        return alunos


class RelatorioAtendimentoForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Buscar'

    ano = forms.IntegerField(label='Filtrar por Ano', widget=forms.Select())
    campus = forms.ModelChoiceField(label='Filtrar por Campus', queryset=UnidadeOrganizacional.objects.uo().all(), required=False, empty_label='Todos')
    renda = forms.ChoiceField(label='Filtrar por Renda', choices=RelatorioGestao.OPCOES)
    somente_ead = forms.BooleanField(label='Exibir somente Alunos EAD', required=False, initial=False)
    reprocessar_dados = forms.BooleanField(label='Reprocessar Dados', required=False, initial=False)

    def __init__(self, *args, **kwargs):
        if 'relatorio' in kwargs:
            self.relatorio = kwargs.pop('relatorio')
        super().__init__(*args, **kwargs)

        ano_limite = datetime.date.today().year
        ANO_CHOICES = [(ano, '{}'.format(ano)) for ano in range(ano_limite, 2009, -1)]
        self.fields['ano'].widget.choices = ANO_CHOICES

        if not self.request.user.has_perm('ae.pode_ver_relatorios_todos'):
            self.fields.pop('campus')

        if not hasattr(self, 'relatorio'):
            self.fields['reprocessar_dados'].widget = forms.HiddenInput()

    def clean_reprocessar_dados(self):
        reprocessar_dados = self.cleaned_data.get('reprocessar_dados')
        # remove 'reprocessar_dados' do GET para não ficar reprocessando após toda requisição
        if hasattr(self.request.GET, '_mutable'):
            self.request.GET._mutable = True
        self.request.GET['reprocessar_dados'] = False
        return reprocessar_dados and not 'finalize' in self.request.GET

    def _get_dados(self):
        self.is_valid()
        ano = self.cleaned_data.get('ano')
        somente_ead = self.cleaned_data.get('somente_ead')
        campus = self.cleaned_data.get('campus')
        renda = self.cleaned_data.get('renda')
        user = self.request.user
        if not campus and not user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
            campus = get_uo(user)
        return ano, campus, somente_ead, renda

    def obter_relatorio(self):
        try:
            ano, campus, somente_ead, renda = self._get_dados()
            return RelatorioGestao.objects.filter(campus=campus, ano=ano, somente_alunos_ead=somente_ead, renda_per_capita=renda).latest('id')
        except RelatorioGestao.DoesNotExist:
            return None

    def criar_relatorio(self):
        ano, campus, somente_ead, renda = self._get_dados()
        return RelatorioGestao.objects.create(campus=campus, ano=ano, somente_alunos_ead=somente_ead, renda_per_capita=renda)

    def processar_queries(self):
        ano, campus, somente_ead, renda = self._get_dados()
        user = self.request.user

        demandas_atendidas = DemandaAlunoAtendida.objects.filter(quantidade__gt=0, demanda__ativa=True)
        auxilios_atendidos = AtendimentoSetor.objects.all()
        bolsas_atendidas = ParticipacaoBolsa.objects.all()
        participacoes_atendidas = Participacao.objects.all()
        atendimentos_saude = Atendimento.objects.filter(aluno__isnull=False, data_cancelado__isnull=True).exclude(situacao=SituacaoAtendimento.CANCELADO).distinct()

        if ano:
            demandas_atendidas = demandas_atendidas.filter(data__year=ano)
            auxilios_atendidos = auxilios_atendidos.filter(data__year=ano)
            bolsas_atendidas = bolsas_atendidas.filter(
                Q(data_inicio__lte=date(ano, 12, 31), data_termino__isnull=True) | Q(data_inicio__lte=date(ano, 12, 31), data_termino__gte=date(ano, 0o1, 0o1))
            )
            participacoes_atendidas = participacoes_atendidas.filter(
                Q(data_inicio__lte=date(ano, 12, 31), data_termino__isnull=True) | Q(data_inicio__lte=date(ano, 12, 31), data_termino__gte=date(ano, 0o1, 0o1))
            )

            atendimentos_saude = atendimentos_saude.exclude(tipo=TipoAtendimento.PSICOLOGICO).filter(
                data_aberto__lte=date(ano, 12, 31), data_aberto__gte=date(ano, 0o1, 0o1)
            ) | atendimentos_saude.filter(tipo=TipoAtendimento.PSICOLOGICO).filter(
                atendimentopsicologia__data_atendimento__lte=date(ano, 12, 31), atendimentopsicologia__data_atendimento__gte=date(ano, 0o1, 0o1)
            )

        if campus or not user.has_perm('ae.pode_ver_relatorio_atendimento_todos'):
            if not campus:
                campus = get_uo(user)
            demandas_atendidas = demandas_atendidas.filter(campus=campus)
            auxilios_atendidos = auxilios_atendidos.filter(campus=campus)
            bolsas_atendidas = bolsas_atendidas.filter(aluno__curso_campus__diretoria__setor__uo=campus)
            participacoes_atendidas = participacoes_atendidas.filter(programa__instituicao=campus)
            atendimentos_saude = atendimentos_saude.filter(usuario_aberto__pessoafisica__funcionario__setor__uo=campus)

        if somente_ead:
            demandas_atendidas = demandas_atendidas.filter(aluno__curso_campus__diretoria__ead=True)
            auxilios_atendidos = auxilios_atendidos.filter(alunos__curso_campus__diretoria__ead=True)
            bolsas_atendidas = bolsas_atendidas.filter(aluno__curso_campus__diretoria__ead=True)
            participacoes_atendidas = participacoes_atendidas.filter(aluno__curso_campus__diretoria__ead=True)
            atendimentos_saude = atendimentos_saude.filter(aluno__curso_campus__diretoria__ead=True)

        if renda and renda != RelatorioGestao.TODAS:
            from comum.models import Configuracao
            from decimal import Decimal

            sm = Decimal(Configuracao.get_valor_por_chave('comum', 'salario_minimo'))
            if renda == RelatorioGestao.ATE_MEIO:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(where=['renda_bruta_familiar/qtd_pessoas_domicilio <= {}/2'.format(sm)])

            elif renda == RelatorioGestao.ENTRE_MEIO_E_UM:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
                    where=['renda_bruta_familiar/qtd_pessoas_domicilio > {}/2 AND renda_bruta_familiar/qtd_pessoas_domicilio <= {}'.format(sm, sm)]
                )

            elif renda == RelatorioGestao.ENTRE_UM_E_UM_MEIO:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(
                    where=['renda_bruta_familiar/qtd_pessoas_domicilio > {} AND renda_bruta_familiar/qtd_pessoas_domicilio <= 1.5*{}'.format(sm, sm)]
                )

            elif renda == RelatorioGestao.MAIOR_QUE_UM_E_MEIO:
                caracterizacao = Caracterizacao.objects.filter(~Q(qtd_pessoas_domicilio=0)).extra(where=['renda_bruta_familiar/qtd_pessoas_domicilio > ({} * 1.5)'.format(sm)])

            ids_por_renda = caracterizacao.values_list('aluno', flat=True)
            demandas_atendidas = demandas_atendidas.filter(aluno__in=ids_por_renda)
            auxilios_atendidos = auxilios_atendidos.filter(alunos__in=ids_por_renda)
            bolsas_atendidas = bolsas_atendidas.filter(aluno__in=ids_por_renda)
            participacoes_atendidas = participacoes_atendidas.filter(aluno__in=ids_por_renda)
            atendimentos_saude = atendimentos_saude.filter(aluno__in=ids_por_renda)

        return [demandas_atendidas, auxilios_atendidos, bolsas_atendidas, participacoes_atendidas, atendimentos_saude]

    def _obter_dict_dados(self, meses, custeio):
        return dict(
            meses=meses,
            valor_total=0,
            valor_total_1_sem=0,
            valor_total_2_sem=0,
            total=0,
            total_1_sem=0,
            total_2_sem=0,
            total_alunos=set(),
            total_alunos_1_sem=set(),
            total_alunos_2_sem=set(),
            agrupamento_aluno=list(),
            custeio=custeio,
        )

    def _obter_dict_meses(self):
        meses = dict()
        for mes in range(1, 13):
            meses[mes] = dict(valor=0, qtd=0, qtd_aluno=set(), agrupamento_aluno=list())

        return meses

    def obter_dados_para_exibicao(self, items, nome, aluno_id, custeio=None, agrupamento_aluno=None, nome_agrupamento=None, nome_agrupador=None, valores_agrupados=[]):
        """
        Retorna dois dicionários para exibição dos dados.
        Keyword arguments:
           *items:               Uma lista contendo os dados a serem trabalhados no relatório agrupados, pelo menos, pelo id do aluno
           *nome:                Uma string com o nome do atributo a ser exibido
           *aluno_id             Uma string que representa o atributo que contém o id do aluno para se calcuar os alunos atendidos
            custeio:             Uma string com o nome do atributo a ser exibido
            agrupamento_aluno:   Uma string com o nome do atributo que será utilizado para se agrupar os alunos [Auxílio]
            nome_agrupamento:    Uma string com o nome a ser exibido no caso de dados de items agrupados [Atendimento]
            nome_agrupador:      Uma string com o nome do atributo a se agrupar os items [Atendimento]
            valores_agrupados:   Uma lista com valores do atributo 'nome_agrupado' que devem se agrupar para formar o novo 'nome' 'nome_agrupamento' [Atendimento]

        * parametros obrigatórios
        [] usado em
        """
        dados = OrderedDict()
        dados_alunos = OrderedDict()

        for mes in range(1, 13):
            dados_alunos[mes] = set()

        for item in items:
            item_nome = item[nome]
            if item_nome not in dados:
                meses = self._obter_dict_meses()
                dados[item_nome] = self._obter_dict_dados(meses, item.get(custeio) or '-')

            item_mes = item['mes']
            # se true devem-se agrupar os alunos para totalizar
            if not agrupamento_aluno or item[agrupamento_aluno] not in dados[item_nome]['meses'][item_mes]['agrupamento_aluno']:
                if agrupamento_aluno:
                    dados[item_nome]['meses'][item_mes]['agrupamento_aluno'].append(item[agrupamento_aluno])

                dados[item_nome]['total'] += item['qtd'] or 0
                dados[item_nome]['valor_total'] += item['valor_total'] or 0
                dados[item_nome]['meses'][item_mes]['qtd'] += item['qtd'] or 0
                dados[item_nome]['meses'][item_mes]['valor'] += item['valor_total'] or 0
                if item_mes <= 6:
                    dados[item_nome]['total_1_sem'] += item['qtd'] or 0
                    dados[item_nome]['valor_total_1_sem'] += item['valor_total'] or 0
                else:
                    dados[item_nome]['total_2_sem'] += item['qtd'] or 0
                    dados[item_nome]['valor_total_2_sem'] += item['valor_total'] or 0

            dados[item_nome]['meses'][item_mes]['qtd_aluno'].add(item[aluno_id])
            dados[item_nome]['total_alunos'].add(item[aluno_id])
            dados_alunos[item_mes].add(item[aluno_id])
            if item_mes <= 6:
                dados[item_nome]['total_alunos_1_sem'].add(item[aluno_id])
            else:
                dados[item_nome]['total_alunos_2_sem'].add(item[aluno_id])

            # se true indica que deve-se adicionar um nome 'nome_agrupador' que irá agrupar itens
            if nome_agrupador and item[nome_agrupador] in valores_agrupados:
                if nome_agrupamento not in dados:
                    meses = self._obter_dict_meses()
                    dados[nome_agrupamento] = self._obter_dict_dados(meses, '')

                dados[nome_agrupamento]['total'] += item['qtd'] or 0
                dados[nome_agrupamento]['valor_total'] += item['valor_total'] or 0
                dados[nome_agrupamento]['meses'][item_mes]['qtd'] += item['qtd'] or 0
                dados[nome_agrupamento]['meses'][item_mes]['valor'] += item['valor_total'] or 0
                dados[nome_agrupamento]['total_alunos'].add(item[aluno_id])
                dados[nome_agrupamento]['meses'][item_mes]['qtd_aluno'].add(item[aluno_id])
                if item_mes <= 6:
                    dados[nome_agrupamento]['total_1_sem'] += item['qtd'] or 0
                    dados[nome_agrupamento]['total_alunos_1_sem'].add(item[aluno_id])
                    dados[nome_agrupamento]['valor_total_1_sem'] += item['valor_total'] or 0
                else:
                    dados[nome_agrupamento]['total_2_sem'] += item['qtd'] or 0
                    dados[nome_agrupamento]['total_alunos_2_sem'].add(item[aluno_id])
                    dados[nome_agrupamento]['valor_total_2_sem'] += item['valor_total'] or 0

        return [dados, dados_alunos]

    def obter_dados_para_exibicao_ano(self, items, nome, aluno_id, ano, agrupamento_aluno, programa=False):
        """
        Retorna dois dicionários para exibição dos dados.
        Keyword arguments:
           *items:               Uma lista contendo os dados a serem trabalhados no relatório agrupados, pelo menos, pelo id do aluno
           *nome:                Uma string com o nome do atributo a ser exibido
           *aluno_id             Uma string que representa o atributo que contém o id do aluno para se calcuar os alunos atendidos
           *ano:                 Um inteiro que representa o ano que se está trabalhando no relatório (quando o relatório deve trabalhar com períodos de datas)
           *agrupamento_aluno:   Uma string com o nome do atributo que será utilizado para se agrupar os alunos

        * parametros obrigatórios
        [] usado em
        """
        dados = OrderedDict()
        dados_alunos = OrderedDict()
        if programa:
            valores_refeicao = dict()
            valores_bolsa = dict()
            ids_participacoes = [item['id'] for item in items]
            participacoes = {p.pk: p for p in Participacao.objects.filter(id__in=ids_participacoes)}

            ids_programas = [item['programa__id'] for item in items]
            programas = {p.pk: p for p in Programa.objects.filter(id__in=ids_programas)}
        else:
            ids_alunos = [item[aluno_id] for item in items]
            uo_alunos = dict(Aluno.objects.filter(id__in=ids_alunos).values_list('id', 'curso_campus__diretoria__setor__uo__id'))
            dict_ofertas = dict()

        for mes in range(1, 13):
            dados_alunos[mes] = set()

        for item in items:
            item_nome = item[nome]
            if item_nome not in dados:
                meses = self._obter_dict_meses()
                for mes in range(1, 13):
                    meses[mes]['valor'] = None
                dados[item_nome] = self._obter_dict_dados(meses, item.get(None) or '-')

            data_inicio = item['data_inicio']
            data_termino = item['data_termino'] or date(ano, 12, 31)
            for mes in range(1, 13):
                inicio_mes = date(ano, mes, 1)
                fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
                if int(mes) == 12:
                    data_termino_auxilio = datetime.datetime(ano + 1, 1, 1).date()
                else:
                    data_termino_auxilio = datetime.datetime(ano, int(mes) + 1, 1).date()

                if existe_conflito_entre_intervalos([data_inicio, data_termino, inicio_mes, fim_mes]):
                    # se true devem-se agrupar os alunos para totalizar
                    if not agrupamento_aluno or item[agrupamento_aluno] not in dados[item_nome]['agrupamento_aluno']:
                        if agrupamento_aluno:
                            dados[item_nome]['agrupamento_aluno'].append(item[agrupamento_aluno])
                        dados[item_nome]['total'] += 1
                        if mes <= 6:
                            dados[item_nome]['total_1_sem'] += 1
                            dados[item_nome]['total_alunos_1_sem'].add(item[aluno_id])
                        else:
                            dados[item_nome]['total_2_sem'] += 1
                            dados[item_nome]['total_alunos_2_sem'].add(item[aluno_id])

                    dados[item_nome]['meses'][mes]['qtd'] += 1
                    dados[item_nome]['total_alunos'].add(item[aluno_id])
                    dados[item_nome]['meses'][mes]['qtd_aluno'].add(item[aluno_id])
                    if programa:
                        programa_do_aluno = programas.get(item['programa__id'])
                        uo_id = programa_do_aluno.instituicao_id
                        if programa_do_aluno.tipo == Programa.TIPO_ALIMENTACAO:
                            if dados[item_nome]['meses'][mes]['valor'] is None:
                                if uo_id not in valores_refeicao:
                                    valores_refeicao[uo_id] = dict()

                                if inicio_mes not in valores_refeicao[uo_id]:
                                    valores_refeicao[uo_id][inicio_mes] = dict()

                                if fim_mes not in valores_refeicao[uo_id][inicio_mes]:
                                    ofertas = OfertaValorRefeicao.objects.filter(campus_id=uo_id, data_inicio__lte=fim_mes, data_termino__gte=inicio_mes)
                                    valores_refeicao[uo_id][inicio_mes][fim_mes] = ofertas.values_list('valor', flat=True)

                                valor_refeicao = valores_refeicao[uo_id][inicio_mes][fim_mes]
                                if valor_refeicao:
                                    preco = valor_refeicao[0]
                                    if preco:
                                        quantidade = DemandaAlunoAtendida.objects.filter(campus_id=uo_id, data__year=ano, demanda__in=[1, 2, 19], data__month=mes).count()
                                        valor_no_mes_gasto_com_o_aluno = preco * quantidade
                                        dados[item_nome]['meses'][mes]['valor'] = valor_no_mes_gasto_com_o_aluno
                                        dados[item_nome]['valor_total'] += valor_no_mes_gasto_com_o_aluno
                                        if mes <= 6:
                                            dados[item_nome]['valor_total_1_sem'] += valor_no_mes_gasto_com_o_aluno
                                        else:
                                            dados[item_nome]['valor_total_2_sem'] += valor_no_mes_gasto_com_o_aluno

                        elif programa_do_aluno.tipo == Programa.TIPO_TRANSPORTE:
                            if dados[item_nome]['meses'][mes]['valor'] is None:
                                dados[item_nome]['meses'][mes]['valor'] = 0
                            diferenca = None
                            participacao_do_aluno = participacoes.get(item['id'])
                            dias_do_mes = 22
                            dias_abonados_geral = DatasRecessoFerias.objects.filter(data__gte=inicio_mes, data__lt=data_termino_auxilio, campus=uo_id).exclude(
                                data__week_day__in=[1, 7]
                            )
                            dias_abonados = dias_abonados_geral.filter(data__gte=participacao_do_aluno.data_inicio)
                            if participacao_do_aluno.data_termino:
                                dias_abonados = dias_abonados.filter(data__lt=participacao_do_aluno.data_termino)
                            qtd_dias_abonados = dias_abonados.count()
                            valor = participacao_do_aluno.sub_instance().valor_concedido and Decimal(participacao_do_aluno.sub_instance().valor_concedido).quantize(Decimal(10) ** -2) or 0
                            if valor:
                                if participacao_do_aluno.data_inicio > inicio_mes and participacao_do_aluno.data_inicio.month == int(mes):

                                    fromdate = participacao_do_aluno.data_inicio
                                    todate = data_termino_auxilio
                                    daygenerator = (fromdate + timedelta(x + 1) for x in range((todate - fromdate).days))
                                    diferenca = sum(1 for day in daygenerator if day.weekday() < 5)

                                    if diferenca > dias_do_mes:
                                        diferenca_em_dias = dias_do_mes - qtd_dias_abonados
                                    else:
                                        diferenca_em_dias = diferenca - qtd_dias_abonados
                                    if diferenca_em_dias < 0:
                                        diferenca_em_dias = 0
                                    valor = Decimal((valor / dias_do_mes) * diferenca_em_dias).quantize(Decimal(10) ** -2)
                                if (
                                    participacao_do_aluno.data_termino
                                    and participacao_do_aluno.data_termino < data_termino_auxilio
                                    and participacao_do_aluno.data_termino.month == int(mes)
                                ):
                                    fromdate = inicio_mes
                                    todate = participacao_do_aluno.data_termino
                                    daygenerator = (fromdate + timedelta(x + 1) for x in range((todate - fromdate).days))
                                    diferenca = sum(1 for day in daygenerator if day.weekday() < 5)
                                    if diferenca > dias_do_mes:
                                        diferenca_em_dias = dias_do_mes - qtd_dias_abonados
                                    else:
                                        diferenca_em_dias = diferenca - qtd_dias_abonados
                                    if diferenca_em_dias < 0:
                                        diferenca_em_dias = 0
                                    valor = Decimal((valor / dias_do_mes) * diferenca_em_dias).quantize(Decimal(10) ** -2)
                                if not diferenca:
                                    if qtd_dias_abonados > dias_do_mes:
                                        qtd_dias_abonados = dias_do_mes
                                    valor = ((dias_do_mes - qtd_dias_abonados) * valor) / dias_do_mes
                                dados[item_nome]['meses'][mes]['valor'] += valor
                                dados[item_nome]['valor_total'] += valor
                                if mes <= 6:
                                    dados[item_nome]['valor_total_1_sem'] += valor
                                else:
                                    dados[item_nome]['valor_total_2_sem'] += valor

                        elif programa_do_aluno.tipo == Programa.TIPO_TRABALHO:
                            dias_do_mes = 30
                            if dados[item_nome]['meses'][mes]['valor'] is None:
                                dados[item_nome]['meses'][mes]['valor'] = 0
                            participacao_do_aluno = participacoes.get(item['id'])

                            if uo_id not in valores_bolsa:
                                valores_bolsa[uo_id] = dict()

                            if inicio_mes not in valores_bolsa[uo_id]:
                                valores_bolsa[uo_id][inicio_mes] = dict()

                            if fim_mes not in valores_bolsa[uo_id][inicio_mes]:
                                ofertas = OfertaValorBolsa.objects.filter(data_inicio__lte=data_termino_auxilio, data_termino__gte=inicio_mes, campus_id=uo_id)
                                valores_bolsa[uo_id][inicio_mes][fim_mes] = ofertas.values_list('valor', flat=True)

                            valor_bolsa = valores_bolsa[uo_id][inicio_mes][fim_mes]
                            if valor_bolsa:
                                valor = valor_bolsa[0]
                                if valor:
                                    if participacao_do_aluno.data_inicio > inicio_mes and participacao_do_aluno.data_inicio.month == mes:
                                        diferenca = data_termino_auxilio - participacao_do_aluno.data_inicio
                                        valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)

                                    if (
                                        participacao_do_aluno.data_termino
                                        and participacao_do_aluno.data_termino < data_termino_auxilio
                                        and participacao_do_aluno.data_termino.month == mes
                                    ):
                                        diferenca = participacao_do_aluno.data_termino - inicio_mes
                                        valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)

                                    if valor:
                                        dados[item_nome]['meses'][mes]['valor'] += valor
                                        dados[item_nome]['valor_total'] += valor
                                        if mes <= 6:
                                            dados[item_nome]['valor_total_1_sem'] += valor
                                        else:
                                            dados[item_nome]['valor_total_2_sem'] += valor
                        else:
                            dias_do_mes = 30
                            participacao_do_aluno = participacoes.get(item['id'])
                            if dados[item_nome]['meses'][mes]['valor'] is None:
                                dados[item_nome]['meses'][mes]['valor'] = 0
                            if RespostaParticipacao.objects.filter(
                                pergunta__eh_info_financeira=True, pergunta__ativo=True, pergunta__tipo_resposta=PerguntaParticipacao.NUMERO, participacao=participacao_do_aluno
                            ).exists():
                                valor = (
                                    RespostaParticipacao.objects.filter(
                                        pergunta__eh_info_financeira=True,
                                        pergunta__ativo=True,
                                        pergunta__tipo_resposta=PerguntaParticipacao.NUMERO,
                                        participacao=participacao_do_aluno,
                                    )
                                    .annotate(soma=Cast('valor_informado', FloatField()))
                                    .aggregate(Sum('soma'))['soma__sum']
                                )
                                if participacao_do_aluno.data_inicio > inicio_mes and participacao_do_aluno.data_inicio.month == int(mes):
                                    diferenca = data_termino_auxilio - participacao_do_aluno.data_inicio
                                    valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)
                                if (
                                    participacao_do_aluno.data_termino
                                    and participacao_do_aluno.data_termino < data_termino_auxilio
                                    and participacao_do_aluno.data_termino.month == int(mes)
                                ):
                                    diferenca = participacao_do_aluno.data_termino - inicio_mes
                                    valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)
                                if valor:
                                    dados[item_nome]['meses'][mes]['valor'] += Decimal(valor)
                                    dados[item_nome]['valor_total'] += Decimal(valor)
                                    if mes <= 6:
                                        dados[item_nome]['valor_total_1_sem'] += Decimal(valor)
                                    else:
                                        dados[item_nome]['valor_total_2_sem'] += Decimal(valor)

                    else:
                        if dados[item_nome]['meses'][mes]['valor'] is None:
                            dados[item_nome]['meses'][mes]['valor'] = 0
                        uo_id = uo_alunos.get(item[aluno_id])
                        dias_do_mes = 30
                        if uo_id not in dict_ofertas:
                            dict_ofertas[uo_id] = dict()

                        if inicio_mes not in dict_ofertas[uo_id]:
                            dict_ofertas[uo_id][inicio_mes] = dict()

                        if fim_mes not in dict_ofertas[uo_id][inicio_mes]:
                            ofertas = OfertaValorBolsa.objects.filter(data_inicio__lte=fim_mes, data_termino__gte=inicio_mes, campus=uo_id)
                            dict_ofertas[uo_id][inicio_mes][fim_mes] = ofertas.values_list('valor', flat=True)

                        valor_ofertas = dict_ofertas[uo_id][inicio_mes][fim_mes]
                        if valor_ofertas:
                            participantes = ParticipacaoBolsa.objects.filter(aluno_id=item[aluno_id])
                            participantes = participantes.filter(Q(data_termino__gt=inicio_mes, data_inicio__lt=fim_mes) | Q(data_termino__isnull=True, data_inicio__lt=fim_mes))
                            for participacao_bolsa in participantes.values('data_inicio', 'data_termino'):
                                valor = valor_ofertas[0]
                                if participacao_bolsa.get('data_inicio') > inicio_mes and participacao_bolsa.get('data_inicio').month == mes:
                                    diferenca = fim_mes - participacao_bolsa.get('data_inicio')
                                    valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)

                                if (
                                    participacao_bolsa.get('data_termino')
                                    and participacao_bolsa.get('data_termino') < fim_mes
                                    and participacao_bolsa.get('data_termino').month == mes
                                ):
                                    diferenca = participacao_bolsa.get('data_termino') - inicio_mes
                                    valor = Decimal((valor / dias_do_mes) * diferenca.days).quantize(Decimal(10) ** -2)

                                dados[item_nome]['meses'][mes]['valor'] += valor
                                dados[item_nome]['valor_total'] += valor
                                if mes <= 6:
                                    dados[item_nome]['valor_total_1_sem'] += valor
                                else:
                                    dados[item_nome]['valor_total_2_sem'] += valor

                    dados_alunos[mes].add(item[aluno_id])

        for nome, dado in list(dados.items()):
            for mes, dado_mes in list(dado['meses'].items()):
                if dado_mes['valor'] is None:
                    dado_mes['valor'] = 0

        return [dados, dados_alunos]

    def obter_dados_para_exibicao_ano_saude(self, items, nome, aluno_id, ano, agrupamento_aluno):
        """
        Retorna dois dicionários para exibição dos dados.
        Keyword arguments:
           *items:               Uma lista contendo os dados a serem trabalhados no relatório agrupados, pelo menos, pelo id do aluno
           *nome:                Uma string com o nome do atributo a ser exibido
           *aluno_id             Uma string que representa o atributo que contém o id do aluno para se calcuar os alunos atendidos
           *ano:                 Um inteiro que representa o ano que se está trabalhando no relatório (quando o relatório deve trabalhar com períodos de datas)
           *agrupamento_aluno:   Uma string com o nome do atributo que será utilizado para se agrupar os alunos
        """

        def obter_nomes_saude():
            item_medico = 'medico'
            item_enfermagem = 'enfermagem'
            item_aval_bio_fechada = 'aval_bio_fechada'
            item_aval_bio_aberta = 'aval_bio_aberta'
            return item_medico, item_enfermagem, item_aval_bio_fechada, item_aval_bio_aberta

        def preencher_dados_saude(dados):
            item_medico, item_enfermagem, item_aval_bio_fechada, item_aval_bio_aberta = obter_nomes_saude()
            if item_medico not in dados:
                dados[item_medico] = self._obter_dict_dados(meses_medico, '-')

            if item_enfermagem not in dados:
                dados[item_enfermagem] = self._obter_dict_dados(meses_enfermagem, '-')

            if item_aval_bio_fechada not in dados:
                dados[item_aval_bio_fechada] = self._obter_dict_dados(meses_aval_bio_fechada, '-')

            if item_aval_bio_aberta not in dados:
                dados[item_aval_bio_aberta] = self._obter_dict_dados(meses_aval_bio_aberta, '-')

            return dados

        def preencher_dict_dados(dados, nome, item, mes, aluno_id, agrupamento_aluno):
            dados[nome]['agrupamento_aluno'].append(item[agrupamento_aluno])
            dados[nome]['total'] += 1
            dados[nome]['meses'][mes]['qtd'] += 1
            dados[nome]['total_alunos'].add(item[aluno_id])
            dados[nome]['meses'][mes]['qtd_aluno'].add(item[aluno_id])
            if mes <= 6:
                dados[nome]['total_1_sem'] += 1
                dados[nome]['total_alunos_1_sem'].add(item[aluno_id])
            else:
                dados[nome]['total_2_sem'] += 1
                dados[nome]['total_alunos_2_sem'].add(item[aluno_id])

        dados = OrderedDict()
        dados_alunos = OrderedDict()

        for mes in range(1, 13):
            dados_alunos[mes] = set()

        for item in items:
            item_nome = item[nome]

            if item_nome not in dados:
                meses = self._obter_dict_meses()
                meses_medico = self._obter_dict_meses()
                meses_enfermagem = self._obter_dict_meses()
                meses_aval_bio_aberta = self._obter_dict_meses()
                meses_aval_bio_fechada = self._obter_dict_meses()
                dados[item_nome] = self._obter_dict_dados(meses, item.get(None) or '-')
                dados = preencher_dados_saude(dados)

            if item_nome == TipoAtendimento.PSICOLOGICO and item['atendimentopsicologia__data_atendimento']:
                data_termino = data_inicio = item['atendimentopsicologia__data_atendimento'].date()
            else:
                data_termino = data_inicio = item['data_aberto'].date()

            for mes in range(1, 13):
                inicio_mes = date(ano, mes, 1)
                fim_mes = date(ano, mes, calendar.monthrange(ano, mes)[1])
                if existe_conflito_entre_intervalos([data_inicio, data_termino, inicio_mes, fim_mes]):
                    # se true devem-se agrupar os alunos para totalizar
                    if not agrupamento_aluno or item[agrupamento_aluno] not in dados[item_nome]['agrupamento_aluno']:
                        if agrupamento_aluno:
                            dados[item_nome]['agrupamento_aluno'].append(item[agrupamento_aluno])

                        dados[item_nome]['total'] += 1
                        if mes <= 6:
                            dados[item_nome]['total_1_sem'] += 1
                            dados[item_nome]['total_alunos_1_sem'].add(item[aluno_id])
                        else:
                            dados[item_nome]['total_2_sem'] += 1
                            dados[item_nome]['total_alunos_2_sem'].add(item[aluno_id])

                    dados[item_nome]['meses'][mes]['qtd'] += 1
                    dados[item_nome]['total_alunos'].add(item[aluno_id])
                    dados[item_nome]['meses'][mes]['qtd_aluno'].add(item[aluno_id])
                    item_medico, item_enfermagem, item_aval_bio_fechada, item_aval_bio_aberta = obter_nomes_saude()
                    if item_nome == TipoAtendimento.AVALIACAO_BIOMEDICA:
                        if item['data_fechado']:
                            preencher_dict_dados(dados, item_aval_bio_fechada, item, mes, aluno_id, agrupamento_aluno)
                        else:
                            preencher_dict_dados(dados, item_aval_bio_aberta, item, mes, aluno_id, agrupamento_aluno)

                    if item_nome == TipoAtendimento.ENFERMAGEM_MEDICO:
                        if (
                            CondutaMedica.objects.filter(atendimento__id=item[agrupamento_aluno]).exists()
                            and Anamnese.objects.filter(atendimento__id=item[agrupamento_aluno]).exists()
                        ):
                            preencher_dict_dados(dados, item_medico, item, mes, aluno_id, agrupamento_aluno)

                        if (
                            IntervencaoEnfermagem.objects.filter(atendimento__id=item[agrupamento_aluno]).exists()
                            and IntervencaoEnfermagem.objects.filter(atendimento__id=item[agrupamento_aluno]).exists()
                        ):
                            preencher_dict_dados(dados, item_enfermagem, item, mes, aluno_id, agrupamento_aluno)

                    dados_alunos[mes].add(item[aluno_id])

        return [dados, dados_alunos]

    def processar(self, title, request):
        return tasks.relatorio_atendimento(request.GET, request.META.get('QUERY_STRING', ''), request.user.username)


class GraficoAtendimentoForm(forms.FormPlus):
    ano_limite = datetime.date.today().year
    ANO_CHOICES = [['Todos', 'Todos']]
    ANO_CHOICES += [['{}'.format(ano), '{}'.format(ano)] for ano in range(ano_limite, 2006, -1)]

    ano = forms.ChoiceField(required=False, choices=ANO_CHOICES, label='Filtrar por Ano:')


class RelatorioFinanceiroForm(forms.FormPlus):
    ano_limite = datetime.date.today().year
    ANO_CHOICES = []
    ANO_CHOICES.append(['Selecione um ano', 'Selecione um ano'])
    for ano in range(ano_limite, 2009, -1):
        ANO_CHOICES.append(['{}'.format(ano), '{}'.format(ano)])

    ano = forms.ChoiceField(required=False, choices=ANO_CHOICES, label='Filtrar por Ano:')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        if user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            self.fields['campus'] = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.uo().all(), empty_label='Todos', label='Filtrar por Campus:', required=False)


class RelatorioFinanceiroAuxiliosForm(forms.FormPlus):
    ano_limite = datetime.date.today().year
    ANO_CHOICES = []
    ANO_CHOICES.append(['Selecione um ano', 'Selecione um ano'])
    for ano in range(ano_limite, 2009, -1):
        ANO_CHOICES.append(['{}'.format(ano), '{}'.format(ano)])

    ano = forms.ChoiceField(required=False, choices=ANO_CHOICES, label='Filtrar por Ano:')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        if user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            self.fields['campus'] = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.uo().all(), empty_label='Todos', label='Filtrar por Campus:', required=False)
        self.fields['tipo_auxilio'] = forms.ModelChoiceField(
            queryset=TipoAtendimentoSetor.objects.all().order_by('descricao'), empty_label='Todos', label='Filtrar por Tipo de Auxílio:', required=False
        )


class RelatorioFinanceiroBolsasForm(forms.FormPlus):
    ano_limite = datetime.date.today().year
    ANO_CHOICES = []
    ANO_CHOICES.append(['Selecione um ano', 'Selecione um ano'])
    for ano in range(ano_limite, 2009, -1):
        ANO_CHOICES.append(['{}'.format(ano), '{}'.format(ano)])

    ano = forms.ChoiceField(required=False, choices=ANO_CHOICES, label='Filtrar por Ano:')

    categoria = forms.ModelChoiceField(queryset=CategoriaBolsa.objects.all(), empty_label='Selecione uma categoria', label='Filtrar por Categoria:', required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user = self.request.user
        if user.has_perm('ae.pode_ver_relatorio_financeiro_todos'):
            self.fields['campus'] = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.uo().all(), empty_label='Todos', label='Filtrar por Campus:', required=False)


class AnoForm(forms.FormPlus):
    SUBMIT_LABEL = 'Continuar >>'

    ano = forms.ChoiceField(choices=[], required=False, label='Filtrar por Ano:')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ano_limite = datetime.date.today().year
        ANO_CHOICES = []
        ANO_CHOICES.append(['Todos', 'Todos'])
        ANO_CHOICES += [(ano, '{}'.format(ano)) for ano in range(ano_limite, 2000, -1)]
        self.fields['ano'].choices = ANO_CHOICES


class ParecerInscricaoForm(forms.ModelFormPlus):
    parecer = forms.CharField(widget=forms.Textarea(), label='Parecer da Inscrição')

    class Meta:
        model = Inscricao
        fields = ['parecer']


class SolicitacaoRefeicaoAlunoForm(forms.ModelForm):
    dia_solicitacao = forms.ChoiceField(label="Solicitação para:", required=False, choices=TipoRefeicao.DIAS)
    escolha_motivo_solicitacao = forms.ModelChoiceField(MotivoSolicitacaoRefeicao.objects, label='Motivo da Solicitação')

    fieldsets = ((None, {'fields': ('tipo_refeicao_escolhido', 'escolha_motivo_solicitacao', 'dia_solicitacao')}),)

    class Meta:
        model = SolicitacaoRefeicaoAluno
        fields = ('dia_solicitacao',)

    class Media:
        js = ['/static/ae/js/solicitacao_refeicao.js']

    def __init__(self, *args, **kwargs):
        aluno = kwargs.pop('aluno')
        programa = kwargs.pop('programa')
        self.uo = kwargs.pop('uo')
        super().__init__(*args, **kwargs)
        self.instance.aluno = aluno
        self.instance.programa = programa
        self.instance.data_solicitacao = datetime.datetime.today()
        agora = datetime.datetime.now()
        self.fields['escolha_motivo_solicitacao'].queryset = MotivoSolicitacaoRefeicao.objects.filter(ativo=True)
        refeicoes = HorarioSolicitacaoRefeicao.objects.filter(
            uo=self.uo, hora_inicio__lte=agora, hora_fim__gte=agora, dia_fim=F('dia_inicio')
        ) | HorarioSolicitacaoRefeicao.objects.filter(Q(uo=self.uo), Q(hora_inicio__lte=agora) | Q(hora_fim__gte=agora), ~Q(dia_fim=F('dia_inicio')))
        self.fields['tipo_refeicao_escolhido'] = forms.ChoiceField(
            label="Tipo de Refeição:",
            choices=[[0, 'Selecione o Tipo']] + [[r.id, r.get_tipo_refeicao_display()] for r in refeicoes],
            widget=forms.Select(attrs={'onchange': 'recarrega()'}),
        )

    def clean(self, *args, **kwargs):
        if self.cleaned_data.get('tipo_refeicao_escolhido'):
            if self.cleaned_data['tipo_refeicao_escolhido'] == '0':
                raise forms.ValidationError('Escolha um tipo de refeição.')

        return super().clean()


class HorarioSolicitacaoForm(forms.ModelForm):
    uo = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=True)

    class Meta:
        model = HorarioSolicitacaoRefeicao
        fields = ('uo', 'tipo_refeicao', 'hora_inicio', 'dia_inicio', 'hora_fim', 'dia_fim')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.request.user.has_perm('ae.pode_ver_listas_todos'):
            self.fields['uo'] = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().filter(id=get_uo(self.request.user).id), initial=0)

    def clean(self, *args, **kwargs):
        if (
            self.cleaned_data.get('dia_inicio')
            and self.cleaned_data['dia_inicio'] == TipoRefeicao.AMANHA
            and self.cleaned_data.get('dia_fim')
            and self.cleaned_data['dia_fim'] == TipoRefeicao.HOJE
        ):
            raise forms.ValidationError('O dia de término não pode ser "Dia anterior" quando o dia de início for "Mesmo dia".')
        if (
            self.cleaned_data.get('tipo_refeicao')
            and self.cleaned_data.get('tipo_refeicao') == TipoRefeicao.TIPO_ALMOCO
            and self.cleaned_data.get('dia_fim')
            and self.cleaned_data['dia_fim'] == HorarioSolicitacaoRefeicao.MESMO_DIA
            and self.cleaned_data.get('hora_fim')
            and self.cleaned_data.get('hora_fim') > datetime.time(11, 00, 00, 00)
        ):
            raise forms.ValidationError('O limite de horário para o almoço é até 11 horas.')
        if (
            self.cleaned_data.get('tipo_refeicao')
            and self.cleaned_data.get('tipo_refeicao') == TipoRefeicao.TIPO_JANTAR
            and self.cleaned_data.get('dia_fim')
            and self.cleaned_data['dia_fim'] == HorarioSolicitacaoRefeicao.MESMO_DIA
            and self.cleaned_data.get('hora_fim')
            and self.cleaned_data.get('hora_fim') > datetime.time(17, 00, 00, 00)
        ):
            raise forms.ValidationError('O limite de horário para o jantar é até 17 horas.')
        return super().clean()


class JustificaFaltaRefeicaoForm(forms.FormPlus):
    data = forms.DateFieldPlus(label='Dia da Refeição')
    tipo_refeicao = forms.ChoiceField(label="Tipo de Refeição:", required=False, choices=TipoRefeicao.TIPOS)
    justificativa = forms.CharField(label='Justificativa', max_length=500, widget=forms.Textarea)

    def clean(self, *args, **kwargs):
        hoje = date.today()
        if self.cleaned_data.get('data'):
            if self.cleaned_data['data'] < hoje:
                raise forms.ValidationError('Não é possível informar faltas que já ocorreram.')

        return super().clean()


class DatasLiberadasForm(forms.ModelForm):
    data = forms.DateFieldPlus(label='Data ou Início do Período', required=True)
    data_fim = forms.DateFieldPlus(label='Data de término', required=False, help_text='Deixar em branco quando não for liberação para um período')

    class Meta:
        model = DatasLiberadasFaltasAlimentacao
        fields = ('campus', 'data', 'data_fim', 'recorrente')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['campus'] = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo().filter(id=get_uo(self.request.user).id), initial=0)
        if self.instance.id:
            self.fields['data_fim'].widget = forms.HiddenInput()

    def clean(self):
        if (
            'data_fim' in self.cleaned_data
            and self.cleaned_data.get('data_fim')
            and self.cleaned_data.get('data')
            and self.cleaned_data.get('data') > self.cleaned_data.get('data_fim')
        ):
            raise forms.ValidationError('A data final não pode ser menor do que a data inicial.')
        if DatasLiberadasFaltasAlimentacao.objects.filter(campus=self.cleaned_data.get('campus'), data=self.cleaned_data.get('data')).exists():
            raise forms.ValidationError('Esta data já foi cadastrada.')
        if DatasRecessoFerias.objects.filter(campus=self.cleaned_data.get('campus'), data=self.cleaned_data.get('data')).exists():
            raise forms.ValidationError('Esta data já foi cadastrada como recesso/férias.')
        return self.cleaned_data

    @transaction.atomic()
    def save(self, force_insert=False, force_update=False, commit=True):
        m = super().save(commit=False)
        if 'data_fim' in self.cleaned_data and self.cleaned_data.get('data_fim'):
            data_inicial = self.cleaned_data.get('data') + datetime.timedelta(days=1)
            campus = self.cleaned_data.get('campus')
            for dt in rrule(DAILY, dtstart=data_inicial, until=self.cleaned_data.get('data_fim')):
                # Se nao existe uma liberacao para o dia
                if not DatasLiberadasFaltasAlimentacao.objects.filter(campus=campus, data=dt).first():
                    nova_liberacao = DatasLiberadasFaltasAlimentacao()
                    nova_liberacao.campus = campus
                    nova_liberacao.data = dt
                    nova_liberacao.recorrente = self.cleaned_data.get('recorrente')
                    nova_liberacao.save()
        return m


class LiberaParticipacaoAlimentacaoForm(forms.FormPlus):
    matricula_nome = forms.CharField(label='Matrícula/Nome', max_length=100, required=False)


class FolhaPagamentoForm(forms.FormPlus):
    METHOD = 'GET'
    ver_nome = forms.BooleanField(label='Nome', initial=False, required=False)
    ver_matricula = forms.BooleanField(label='Matrícula', initial=False, required=False)
    ver_cpf = forms.BooleanField(label='CPF', initial=False, required=False)
    ver_banco = forms.BooleanField(label='Banco', initial=False, required=False)
    ver_agencia = forms.BooleanField(label='Agência', initial=False, required=False)
    ver_operacao = forms.BooleanField(label='Operação', initial=False, required=False)
    ver_conta = forms.BooleanField(label='Número da Conta', initial=False, required=False)
    ver_tipo_passe = forms.BooleanField(label='Tipo de Passe', initial=False, required=False)
    ver_valor_padrao = forms.BooleanField(label='Valor Padrão', initial=False, required=False)
    ver_valor_pagar = forms.BooleanField(label='Valor a Pagar', initial=False, required=False)
    ano = forms.ModelChoiceField(queryset=Ano.objects, label='Ano', required=False)

    mes = forms.ChoiceField(
        choices=[
            [1, 'Janeiro'],
            [2, 'Fevereiro'],
            [3, 'Março'],
            [4, 'Abril'],
            [5, 'Maio'],
            [6, 'Junho'],
            [7, 'Julho'],
            [8, 'Agosto'],
            [9, 'Setembro'],
            [10, 'Outubro'],
            [11, 'Novembro'],
            [12, 'Dezembro'],
        ],
        label='Mês',
        required=False,
    )
    fieldsets = (
        ('Filtros', {'fields': (('ano', 'mes'),)}),
        (
            'Opções de Exibição',
            {
                'fields': (
                    ('ver_nome', 'ver_matricula', 'ver_cpf'),
                    ('ver_banco', 'ver_agencia'),
                    ('ver_operacao', 'ver_conta'),
                    ('ver_tipo_passe', 'ver_valor_padrao', 'ver_valor_pagar'),
                )
            },
        ),
    )

    def __init__(self, *args, **kwargs):
        self.programa = kwargs.pop('programa', None)
        super().__init__(*args, **kwargs)
        if self.programa.get_tipo() == Programa.TIPO_TRABALHO:
            self.fieldsets = (
                ('Filtros', {'fields': (('ano', 'mes'),)}),
                ('Opções de Exibição', {'fields': (('ver_nome', 'ver_matricula', 'ver_cpf'), ('ver_banco', 'ver_agencia'), ('ver_operacao', 'ver_conta'), ('ver_valor_pagar'))}),
            )

        else:
            self.fieldsets = (
                ('Filtros', {'fields': (('ano', 'mes'),)}),
                (
                    'Opções de Exibição',
                    {
                        'fields': (
                            ('ver_nome', 'ver_matricula', 'ver_cpf'),
                            ('ver_banco', 'ver_agencia'),
                            ('ver_operacao', 'ver_conta'),
                            ('ver_tipo_passe', 'ver_valor_padrao', 'ver_valor_pagar'),
                        )
                    },
                ),
            )

    def clean(self):
        if not self.cleaned_data.get('ano'):
            raise forms.ValidationError('Selecione o ano.')
        return self.cleaned_data


PERIODO_LETIVO_CHOICES = [['', '']] + settings.PERIODO_LETIVO_CHOICES


class RelatorioAlunosAptosForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Pesquisar'

    CRITERIOS_CHOICES = [
        [1, 'Alunos sem matrículas em disciplina'],
        [2, 'Alunos matriculados em só uma disciplina'],
        [3, 'Alunos matriculados em duas disciplinas'],
        [4, 'Alunos de cursos FIC'],
        [5, 'Alunos de cursos de Aperfeiçoamento, Especialização e Mestrado'],
    ]

    ano_letivo = forms.ModelChoiceField(Ano.objects.filter(ano=datetime.date.today().year), label='Ano Letivo')
    periodo_letivo = forms.ChoiceField(choices=PERIODO_LETIVO_CHOICES, label='Período Letivo', required=False)
    uo = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo().all(), label='Campus', required=False)
    excluir_criterios = forms.MultipleChoiceField(label='Critérios', choices=CRITERIOS_CHOICES, widget=forms.CheckboxSelectMultiple, required=False)
    excluir_proitec = forms.BooleanField(label='Convênio PROITEC', required=False)
    exportar_excel = forms.BooleanField(label='Exibir dados em planilha Excel', required=False)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)

        self.convenios_field_name = ['excluir_proitec']
        for convenio in Convenio.objects.all():
            convenio_field_name = '{}'.format(convenio.pk)
            self.convenios_field_name.append(convenio_field_name)
            self.fields[convenio_field_name] = forms.BooleanField(label='Convênio {}'.format(convenio), required=False)

        self.fieldsets = (
            ('Dados Gerais', {'fields': (('ano_letivo', 'periodo_letivo', 'uo'),)}),
            ('Esconder Alunos com seguintes Critérios', {'fields': ('excluir_criterios', self.convenios_field_name)}),
            ('Opções de Exibição', {'fields': ('exportar_excel',)}),
        )

    def processar(self):
        from edu.forms import EstatisticaForm

        situacoes_alunos_matriculados = EstatisticaForm.MAPA_SITUACAO['SITUACAO_MATRICULADO']
        ano_letivo = self.cleaned_data['ano_letivo'].ano
        periodo_letivo = self.cleaned_data['periodo_letivo']
        exportar_excel = self.cleaned_data['exportar_excel']
        uo = self.cleaned_data['uo']
        qs_matriculados = Aluno.objects.exclude(turmaminicurso__gerar_matricula=False).filter(
            matriculaperiodo__ano_letivo__ano=ano_letivo, matriculaperiodo__situacao__in=situacoes_alunos_matriculados
        )

        if periodo_letivo:
            qs_matriculados = qs_matriculados.filter(matriculaperiodo__periodo_letivo=periodo_letivo)

        if uo:
            qs_matriculados = qs_matriculados.filter(curso_campus__diretoria__setor__uo=uo)

        qs_final = qs_matriculados.exclude(pk=0)
        qs_4_ano = qs_matriculados.exclude(pk=0)
        qs_eja = qs_matriculados.filter(curso_campus__modalidade=Modalidade.INTEGRADO_EJA)

        excluir_criterios = self.cleaned_data['excluir_criterios']
        excluir_proitec = self.cleaned_data['excluir_proitec']

        # 1. Alunos matriculados em só uma disciplina
        if '1' in excluir_criterios:
            if periodo_letivo:
                qs_final = qs_final.exclude(
                    pk__in=MatriculaDiario.objects.filter(matricula_periodo__ano_letivo__ano=ano_letivo, matricula_periodo__periodo_letivo=periodo_letivo)
                    .values_list('matricula_periodo')
                    .order_by('matricula_periodo')
                    .annotate(n=Count('matricula_periodo'))
                    .filter(n=0)
                    .values_list('matricula_periodo__aluno', flat=True)
                )
            else:
                qs_final = qs_final.exclude(
                    pk__in=MatriculaDiario.objects.filter(matricula_periodo__ano_letivo__ano=ano_letivo)
                    .values_list('matricula_periodo')
                    .order_by('matricula_periodo')
                    .annotate(n=Count('matricula_periodo'))
                    .filter(n=0)
                    .values_list('matricula_periodo__aluno', flat=True)
                )

        # 2. Alunos matriculados em só uma disciplina
        if '2' in excluir_criterios:
            if periodo_letivo:
                qs_final = qs_final.exclude(
                    pk__in=MatriculaDiario.objects.filter(matricula_periodo__ano_letivo__ano=ano_letivo, matricula_periodo__periodo_letivo=periodo_letivo)
                    .values_list('matricula_periodo')
                    .order_by('matricula_periodo')
                    .annotate(n=Count('matricula_periodo'))
                    .filter(n=1)
                    .values_list('matricula_periodo__aluno', flat=True)
                )
            else:
                qs_final = qs_final.exclude(
                    pk__in=MatriculaDiario.objects.filter(matricula_periodo__ano_letivo__ano=ano_letivo)
                    .values_list('matricula_periodo')
                    .order_by('matricula_periodo')
                    .annotate(n=Count('matricula_periodo'))
                    .filter(n=1)
                    .values_list('matricula_periodo__aluno', flat=True)
                )

        # 3. Alunos matriculados em duas disciplinas
        if '3' in excluir_criterios:
            if periodo_letivo:
                qs_final = qs_final.exclude(
                    pk__in=MatriculaDiario.objects.filter(matricula_periodo__ano_letivo__ano=ano_letivo, matricula_periodo__periodo_letivo=periodo_letivo)
                    .values_list('matricula_periodo')
                    .order_by('matricula_periodo')
                    .annotate(n=Count('matricula_periodo'))
                    .filter(n=2)
                    .values_list('matricula_periodo__aluno', flat=True)
                )
            else:
                qs_final = qs_final.exclude(
                    pk__in=MatriculaDiario.objects.filter(matricula_periodo__ano_letivo__ano=ano_letivo)
                    .values_list('matricula_periodo')
                    .order_by('matricula_periodo')
                    .annotate(n=Count('matricula_periodo'))
                    .filter(n=2)
                    .values_list('matricula_periodo__aluno', flat=True)
                )

        # 4. Alunos de cursoS FIC
        if '4' in excluir_criterios:
            qs_final = qs_final.exclude(curso_campus__modalidade=Modalidade.FIC)

        # 5. Alunos de cursos de Aperfeiçoamento, Especialização e Mestrado
        if '5' in excluir_criterios:
            qs_final = qs_final.exclude(curso_campus__modalidade__in=[Modalidade.APERFEICOAMENTO, Modalidade.ESPECIALIZACAO, Modalidade.MESTRADO])

        qs_4_ano = (
            qs_4_ano.filter(curso_campus__modalidade__in=[Modalidade.INTEGRADO, Modalidade.INTEGRADO_EJA])
            .filter(matriz__qtd_periodos_letivos__gt=0)
            .values('id')
            .extra(where=['periodo_atual=qtd_periodos_letivos'])
        )

        if excluir_proitec:
            qs_final = qs_final.exclude(matriz__estrutura__proitec=True) | qs_final.filter(matriz__estrutura_id=None)

        excluir_convenios = []
        for convenio_field_name in self.convenios_field_name:
            if convenio_field_name != 'excluir_proitec':
                if self.cleaned_data[convenio_field_name]:
                    excluir_convenios.append(int(convenio_field_name))

        qs_final = qs_final.exclude(convenio__id__in=excluir_convenios)

        qs_caracterizados = qs_matriculados.filter(caracterizacao__isnull=False)

        return qs_matriculados, qs_caracterizados, qs_final, qs_4_ano, qs_eja, exportar_excel


class AtividadeDiversaForm(forms.ModelFormPlus):
    servidores_envolvidos = forms.MultipleModelChoiceFieldPlus(label='Servidores Envolvidos', queryset=Servidor.objects.all(), required=True)
    campus = forms.ModelChoiceFieldPlus(label='Campus', queryset=UnidadeOrganizacional.objects.uo().all())

    class Meta:
        model = AtividadeDiversa
        fields = ('tipo', 'campus', 'data_inicio', 'data_termino', 'observacao', 'servidores_envolvidos')


class AcaoEducativaForm(forms.ModelFormPlus):
    servidores_envolvidos = forms.MultipleModelChoiceFieldPlus(label='Servidores Envolvidos', queryset=Servidor.objects.all(), required=True)
    campus = forms.ModelChoiceFieldPlus(label='Campus', queryset=UnidadeOrganizacional.objects.uo().all())

    class Meta:
        model = AcaoEducativa
        fields = ('titulo', 'campus', 'data_inicio', 'data_termino', 'descricao', 'servidores_envolvidos')


class DataEntregaDocumentacaoForm(forms.FormPlus):
    data = forms.DateFieldPlus(label='Data', required=True)
    url = forms.CharField(required=False, label='Url', widget=forms.HiddenInput())

    def __init__(self, *args, **kwargs):
        self.url = kwargs.pop('url', None)
        super().__init__(*args, **kwargs)
        self.fields['url'].initial = self.url


class EditarParticipacaoForm(forms.ModelFormPlus):
    data_termino = forms.DateFieldPlus(label='Data de Saída', required=True)

    class Meta:
        model = Participacao
        fields = ('data_termino',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.programa.get_tipo() == Programa.TIPO_ALIMENTACAO:
            self.fields['categoria'] = forms.ModelChoiceField(queryset=CategoriaAlimentacao.objects, required=False, label='Categoria')
            self.fields['cafe'] = forms.MultipleChoiceField(
                label='Café da Manhã', choices=DiaSemanaChoices.DIAS_SEMANA_RESUMIDO_CHOICES, widget=forms.CheckboxSelectMultiple, required=False
            )
            self.fields['almoco'] = forms.MultipleChoiceField(
                label='Almoço', choices=DiaSemanaChoices.DIAS_SEMANA_RESUMIDO_CHOICES, widget=forms.CheckboxSelectMultiple, required=False
            )
            self.fields['jantar'] = forms.MultipleChoiceField(
                label='Jantar', choices=DiaSemanaChoices.DIAS_SEMANA_RESUMIDO_CHOICES, widget=forms.CheckboxSelectMultiple, required=False
            )
        elif self.instance.programa.get_tipo() == Programa.TIPO_TRANSPORTE:
            self.fields['valor_concedido'] = forms.DecimalFieldPlus(label='Valor concedido (R$)', required=True)
            self.fields['tipo_passe_concedido'] = forms.ChoiceField(choices=PassesChoices.PASSES_CHOICES, label='Tipo de Passe Concedido')

        elif self.instance.programa.get_tipo() == Programa.TIPO_TRABALHO:
            bolsas = Q(disponivel=True, campus=self.instance.programa.instituicao, ativa=True)
            self.fields['bolsa'] = forms.ModelChoiceField(queryset=OfertaBolsa.objects.filter(bolsas), label='Bolsa')

        elif self.instance.programa.get_tipo() == Programa.TIPO_IDIOMA:
            self.fields['idioma'] = forms.ModelChoiceField(queryset=Idioma.objects.all().order_by("descricao"), label='Idioma')

    def clean(self):
        if 'data_termino' in self.cleaned_data and self.cleaned_data.get('data_termino') <= self.instance.data_inicio:
            raise forms.ValidationError('A data final não pode ser menor ou igual a data inicial.')
        return self.cleaned_data


class DashboardForm(forms.FormPlus):
    campus = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Campus', required=False)
    ano = forms.ModelChoiceField(Ano.objects, label='Filtrar por Ano:', required=False)

    def clean(self):
        if not self.cleaned_data.get('ano'):
            raise forms.ValidationError('Selecione um Ano para exibir o Dashboard.')
        return self.cleaned_data


class RelatorioPlanejamentoForm(forms.FormPlus):
    campus = forms.ModelChoiceField(UnidadeOrganizacional.objects.uo(), label='Campus', required=False)
    ano = forms.IntegerField(label='Filtrar por Ano', widget=forms.Select())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ano_limite = datetime.date.today().year
        ANO_CHOICES = [(ano, '{}'.format(ano)) for ano in range(ano_limite, 2009, -1)]
        self.fields['ano'].widget.choices = ANO_CHOICES


class RelatorioPNAESForm(forms.FormPlus):
    METHOD = 'GET'
    campus = forms.ModelChoiceField(UnidadeOrganizacional.objects.suap(), label='Campus', required=False)
    ano = forms.IntegerField(label='Filtrar por Ano', widget=forms.Select())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        ano_limite = datetime.date.today().year
        ANO_CHOICES = [(ano, '{}'.format(ano)) for ano in range(ano_limite, 2009, -1)]
        self.fields['ano'].widget.choices = ANO_CHOICES


class TipoRefeicaoForm(forms.FormPlus):
    aluno = forms.CharFieldPlus(label='Nome ou Matrícula do Aluno', required=False)
    data = forms.DateFieldPlus(label='Data da Refeição', required=True)
    tipo_refeicao = forms.ChoiceField(label='Tipo de Refeição', choices=TipoRefeicao.TIPOS, required=True)
    METHOD = 'GET'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['data'].initial = datetime.date.today()


class AgendamentoDesbloqueioParticipacaoForm(forms.ModelFormPlus):
    liberar_em = forms.DateFieldPlus(label='Data da Liberação:', required=True)

    class Meta:
        model = ParticipacaoAlimentacao
        fields = ('liberar_em',)


class RelatorioDiarioRefeitorioForm(forms.FormPlus):
    data = forms.DateFieldPlus(label='Data')
    tipo_refeicao = forms.ChoiceField(
        choices=[(DemandaAluno.CAFE, 'Café da manhã'), (DemandaAluno.ALMOCO, 'Almoço'), (DemandaAluno.JANTAR, 'Jantar')],
        initial=DemandaAluno.ALMOCO,
        widget=forms.Select(),
        label='Filtrar por Tipo de Refeição',
    )
    categoria = forms.ModelChoiceField(queryset=CategoriaAlimentacao.objects.all(), label='Filtrar por Categoria', empty_label='Todas as categorias', required=False)
    agendados = forms.BooleanField(widget=forms.CheckboxInput, required=False, label='Somente Refeições Agendadas')

    def clean_tipo_refeicao(self):
        return int(self.cleaned_data['tipo_refeicao'])

    def clean(self):
        if self.cleaned_data.get('categoria') and self.cleaned_data.get('agendados'):
            raise forms.ValidationError('Não é possível filtrar os atendimentos agendados por categoria.')


class DatasRecessoFeriasForm(forms.ModelFormPlus):
    campus = forms.ModelChoiceFieldPlus(label='Campus', queryset=UnidadeOrganizacional.objects.uo())
    data = forms.DateFieldPlus(label='Data ou Início do Período', required=True)
    data_fim = forms.DateFieldPlus(label='Data de Término', required=False, help_text='Deixar em branco quando não for liberação para um período')

    class Meta:
        model = DatasRecessoFerias
        fields = ('campus', 'data', 'data_fim')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.request.user.has_perm('ae.pode_ver_relatorio_inscricao_todos'):
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo().filter(id=get_uo(self.request.user).id)
        if self.instance.id:
            self.fields['data_fim'].widget = forms.HiddenInput()

    def clean(self):
        if (
            'data_fim' in self.cleaned_data
            and self.cleaned_data.get('data_fim')
            and self.cleaned_data.get('data')
            and self.cleaned_data.get('data') > self.cleaned_data.get('data_fim')
        ):
            raise forms.ValidationError('A data final não pode ser menor do que a data inicial.')
        if DatasRecessoFerias.objects.filter(campus=self.cleaned_data.get('campus'), data=self.cleaned_data.get('data')).exists():
            raise forms.ValidationError('Esta data já foi cadastrada.')
        return self.cleaned_data

    @transaction.atomic()
    def save(self, force_insert=False, force_update=False, commit=True):
        if 'data_fim' in self.cleaned_data and self.cleaned_data.get('data_fim'):
            data_inicial = self.cleaned_data.get('data') + datetime.timedelta(days=1)
            campus = self.cleaned_data.get('campus')
            for dt in rrule(DAILY, dtstart=data_inicial, until=self.cleaned_data.get('data_fim')):
                # Se nao existe uma liberacao para o dia
                if not DatasRecessoFerias.objects.filter(campus=campus, data=dt).first():
                    nova_liberacao = DatasRecessoFerias()
                    nova_liberacao.campus = campus
                    nova_liberacao.data = dt
                    nova_liberacao.save()
        return super().save(commit=False)


class EditalForm(forms.ModelFormPlus):
    descricao = forms.CharFieldPlus(label='Descrição', widget=forms.Textarea())

    class Meta:
        models = Edital
        fields = ('descricao', 'tipo_programa', 'link_edital')

    def clean(self):
        cleaned_data = super().clean()
        tem_edital_cadastrado = False
        for programa in self.cleaned_data.get('tipo_programa'):
            if self.instance.pk:
                if Edital.objects.filter(tipo_programa=programa, ativo=True).exclude(id=self.instance.pk).exists():
                    tem_edital_cadastrado = True
            elif Edital.objects.filter(tipo_programa=programa, ativo=True).exists():
                tem_edital_cadastrado = True
            if tem_edital_cadastrado:
                raise forms.ValidationError('Já existe um edital ativo para o tipo de programa {}.'.format(programa))
        return cleaned_data


class PeriodoInscricaoForm(forms.ModelFormPlus):
    edital = forms.ModelChoiceFieldPlus(Edital.objects.filter(ativo=True), label='Edital')
    inativar_inscricoes = forms.BooleanField(label='Deseja inativar as inscrições destes programas para este campus?', required=False)

    class Meta:
        models = PeriodoInscricao
        fields = ('edital', 'campus', 'programa', 'data_inicio', 'data_termino', 'apenas_participantes', 'inativar_inscricoes')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.request.user.has_perm('ae.pode_ver_listas_todos'):
            campus = get_uo(self.request.user)
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo().filter(id=campus.id)
            self.fields['programa'].queryset = Programa.objects.filter(instituicao=campus)
        else:
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo().all()

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            periodos = PeriodoInscricao.objects.filter(data_inicio__lte=self.cleaned_data.get('data_termino'), data_termino__gte=self.cleaned_data.get('data_inicio'))
            if self.instance.pk:
                periodos = periodos.exclude(id=self.instance.pk)
            for programa in self.cleaned_data.get('programa'):
                if self.cleaned_data.get('edital') and programa.tipo_programa_id not in self.cleaned_data.get('edital').tipo_programa.values_list('id', flat=True):
                    raise forms.ValidationError('O Edital selecionado não é destinado ao Tipo de Programa: {}.'.format(programa.tipo_programa))
                if self.cleaned_data.get('campus') and programa.instituicao != self.cleaned_data.get('campus'):
                    raise forms.ValidationError('Apenas Programas vinculados ao Campus escolhido podem ser selecionados.')
                if periodos.exists():
                    if periodos.filter(programa=programa).exists():
                        raise forms.ValidationError('O Programa "{}" já está vinculado a outro Período de Inscrição.'.format(programa.titulo))

        return cleaned_data


class RelatorioAlunoRendimentoFrequenciaForm(forms.FormPlus):
    METHOD = 'GET'
    campus = forms.ModelChoiceField(label='Filtrar por Campus:', required=False, queryset=UnidadeOrganizacional.objects.suap())
    ano = forms.ChoiceField(choices=[], label='Filtrar por Ano:')
    periodo = forms.ChoiceField(label='Período', choices=[('', '------'), ('1', '1'), ('2', '2')], required=False)
    programa = forms.ModelChoiceField(label='Programa', queryset=Programa.objects, widget=forms.Select, required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.request.user.has_perm('ae.pode_ver_listas_todos'):
            campus = get_uo(self.request.user)
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo().filter(id=campus.id)
            self.fields['campus'].initial = campus.id
            self.fields['programa'].queryset = Programa.objects.filter(instituicao=campus)
        ano_limite = datetime.date.today().year
        ANO_CHOICES = [(ano, '{}'.format(ano)) for ano in range(ano_limite, 2009, -1)]
        self.fields['ano'].choices = ANO_CHOICES


class TipoProgramaForm(forms.ModelFormPlus):
    descricao = forms.CharFieldPlus(label='Descrição', widget=forms.Textarea())

    class Meta:
        models = TipoPrograma
        fields = ('titulo', 'descricao', 'ativo')


class PerguntaInscricaoProgramaForm(forms.FormPlus):
    justificativa = forms.CharField(label='Motivo da Solicitação', widget=forms.Textarea, required=True)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.tipo_programa = kwargs.pop('tipo_programa', None)
        self.inscricao = kwargs.pop('inscricao', None)
        super().__init__(*args, **kwargs)
        if self.inscricao:
            self.fields['justificativa'].initial = self.inscricao.motivo
        for i in PerguntaInscricaoPrograma.objects.filter(ativo=True, tipo_programa=self.tipo_programa):
            label = '{}'.format(i.pergunta)
            if i.tipo_resposta == PerguntaInscricaoPrograma.TEXTO:
                self.fields["texto_{}".format(i.id)] = forms.CharFieldPlus(label=label, widget=forms.Textarea, required=i.obrigatoria)

            if i.tipo_resposta == PerguntaInscricaoPrograma.PARAGRAFO:
                self.fields["texto_{}".format(i.id)] = forms.CharFieldPlus(label=label, required=i.obrigatoria)

            if i.tipo_resposta == PerguntaInscricaoPrograma.NUMERO:
                self.fields["texto_{}".format(i.id)] = forms.DecimalFieldPlus(label=label, required=i.obrigatoria)

            if i.tipo_resposta == PerguntaInscricaoPrograma.SIM_NAO:
                self.fields["texto_{}".format(i.id)] = forms.ChoiceField(label=label, required=i.obrigatoria, choices=[('Sim', 'Sim'), ('Não', 'Não')])

            if i.tipo_resposta == PerguntaInscricaoPrograma.UNICA_ESCOLHA:
                self.fields["pergunta_{}".format(i.id)] = forms.ModelChoiceField(queryset=i.pergunta_inscricao, label=label, required=i.obrigatoria)

            elif i.tipo_resposta == PerguntaInscricaoPrograma.MULTIPLA_ESCOLHA:
                self.fields["pergunta_{}".format(i.id)] = forms.MultipleModelChoiceField(queryset=i.pergunta_inscricao, label=label, required=i.obrigatoria)

            if self.inscricao:
                if RespostaInscricaoPrograma.objects.filter(pergunta=i, inscricao=self.inscricao).exists():
                    resposta_anterior = RespostaInscricaoPrograma.objects.filter(pergunta=i, inscricao=self.inscricao)
                    if resposta_anterior.exists():
                        resposta_atual = resposta_anterior[0]
                        if resposta_atual.resposta and not resposta_atual.eh_multipla_escolha():
                            self.initial["pergunta_{}".format(i.id)] = resposta_atual.resposta.id
                        elif resposta_atual.resposta:
                            ids_multipla_escolha = list()
                            for resposta in resposta_anterior:
                                ids_multipla_escolha.append(resposta.resposta.id)
                            self.initial["pergunta_{}".format(i.id)] = ids_multipla_escolha
                        else:
                            self.initial["texto_{}".format(i.id)] = resposta_atual.valor_informado


class PerguntaParticipacaoForm(forms.FormPlus):
    data_inicio = forms.DateFieldPlus(label='Data de Entrada', required=True)
    motivo_entrada = forms.CharField(label='Motivo de Entrada', widget=forms.Textarea, required=True)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.programa = kwargs.pop('programa', None)
        self.instance = kwargs.pop('instance', None)
        if hasattr(self.instance, 'participacao'):
            self.participacao = self.instance.participacao
        else:
            self.participacao = self.instance
        super().__init__(*args, **kwargs)
        if self.instance:
            self.fields['data_inicio'].initial = self.instance.data_inicio
            self.fields['motivo_entrada'].initial = self.instance.motivo_entrada

        for i in PerguntaParticipacao.objects.filter(ativo=True, tipo_programa=self.programa.tipo_programa):
            label = '{}'.format(i.pergunta)
            if i.tipo_resposta == PerguntaParticipacao.TEXTO:
                self.fields["texto_{}".format(i.id)] = forms.CharFieldPlus(label=label, widget=forms.Textarea, required=i.obrigatoria)

            if i.tipo_resposta == PerguntaParticipacao.PARAGRAFO:
                self.fields["texto_{}".format(i.id)] = forms.CharFieldPlus(label=label, required=i.obrigatoria)

            if i.tipo_resposta == PerguntaParticipacao.NUMERO:
                self.fields["texto_{}".format(i.id)] = forms.DecimalFieldPlus(label=label, required=i.obrigatoria)

            if i.tipo_resposta == PerguntaParticipacao.SIM_NAO:
                self.fields["texto_{}".format(i.id)] = forms.ChoiceField(label=label, required=i.obrigatoria, choices=[('Sim', 'Sim'), ('Não', 'Não')])

            if i.tipo_resposta == PerguntaParticipacao.UNICA_ESCOLHA:
                self.fields["pergunta_{}".format(i.id)] = forms.ModelChoiceField(queryset=i.pergunta_participacao, label=label, required=i.obrigatoria)

            elif i.tipo_resposta == PerguntaParticipacao.MULTIPLA_ESCOLHA:
                self.fields["pergunta_{}".format(i.id)] = forms.MultipleModelChoiceField(queryset=i.pergunta_participacao, label=label, required=i.obrigatoria)

            if self.instance:
                if RespostaParticipacao.objects.filter(pergunta=i, participacao=self.participacao).exists():
                    resposta_anterior = RespostaParticipacao.objects.filter(pergunta=i, participacao=self.participacao)
                    if resposta_anterior.exists():
                        resposta_atual = resposta_anterior[0]
                        if resposta_atual.resposta and not resposta_atual.eh_multipla_escolha():
                            self.initial["pergunta_{}".format(i.id)] = resposta_atual.resposta.id
                        elif resposta_atual.resposta:
                            ids_multipla_escolha = list()
                            for resposta in resposta_anterior:
                                ids_multipla_escolha.append(resposta.resposta.id)
                            self.initial["pergunta_{}".format(i.id)] = ids_multipla_escolha
                        else:
                            self.initial["texto_{}".format(i.id)] = resposta_atual.valor_informado


class EditarPerguntaParticipacaoForm(forms.FormPlus):
    data_termino = forms.DateFieldPlus(label='Data de Término', required=True)

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        self.programa = kwargs.pop('programa', None)
        self.instance = kwargs.pop('instance', None)
        if hasattr(self.instance, 'participacao'):
            self.participacao = self.instance.participacao
        else:
            self.participacao = self.instance
        super().__init__(*args, **kwargs)
        for i in PerguntaParticipacao.objects.filter(ativo=True, tipo_programa=self.programa.tipo_programa):
            label = '{}'.format(i.pergunta)
            if i.tipo_resposta == PerguntaParticipacao.TEXTO:
                self.fields["texto_{}".format(i.id)] = forms.CharFieldPlus(label=label, widget=forms.Textarea, required=i.obrigatoria)

            if i.tipo_resposta == PerguntaParticipacao.PARAGRAFO:
                self.fields["texto_{}".format(i.id)] = forms.CharFieldPlus(label=label, required=i.obrigatoria)

            if i.tipo_resposta == PerguntaParticipacao.NUMERO:
                self.fields["texto_{}".format(i.id)] = forms.DecimalFieldPlus(label=label, required=i.obrigatoria)

            if i.tipo_resposta == PerguntaParticipacao.SIM_NAO:
                self.fields["texto_{}".format(i.id)] = forms.ChoiceField(label=label, required=i.obrigatoria, choices=[('Sim', 'Sim'), ('Não', 'Não')])

            if i.tipo_resposta == PerguntaParticipacao.UNICA_ESCOLHA:
                self.fields["pergunta_{}".format(i.id)] = forms.ModelChoiceField(queryset=i.pergunta_participacao, label=label, required=i.obrigatoria)

            elif i.tipo_resposta == PerguntaParticipacao.MULTIPLA_ESCOLHA:
                self.fields["pergunta_{}".format(i.id)] = forms.MultipleModelChoiceField(queryset=i.pergunta_participacao, label=label, required=i.obrigatoria)

            if self.instance:
                if RespostaParticipacao.objects.filter(pergunta=i, participacao=self.participacao).exists():
                    resposta_anterior = RespostaParticipacao.objects.filter(pergunta=i, participacao=self.participacao)
                    if resposta_anterior.exists():
                        resposta_atual = resposta_anterior[0]
                        if resposta_atual.resposta and not resposta_atual.eh_multipla_escolha():
                            self.initial["pergunta_{}".format(i.id)] = resposta_atual.resposta.id
                        elif resposta_atual.resposta:
                            ids_multipla_escolha = list()
                            for resposta in resposta_anterior:
                                ids_multipla_escolha.append(resposta.resposta.id)
                            self.initial["pergunta_{}".format(i.id)] = ids_multipla_escolha
                        else:
                            self.initial["texto_{}".format(i.id)] = resposta_atual.valor_informado


class OpcaoRespostaInscricaoProgramaForm(forms.ModelFormPlus):
    pergunta = forms.ModelChoiceField(
        queryset=PerguntaInscricaoPrograma.objects.filter(ativo=True, tipo_resposta__in=[PerguntaInscricaoPrograma.UNICA_ESCOLHA, PerguntaInscricaoPrograma.MULTIPLA_ESCOLHA]),
        label='Pergunta',
    )

    class Meta:
        model = OpcaoRespostaInscricaoPrograma
        fields = ('pergunta', 'valor', 'ativo')


class OpcaoRespostaPerguntaParticipacaoForm(forms.ModelFormPlus):
    pergunta = forms.ModelChoiceField(
        queryset=PerguntaParticipacao.objects.filter(ativo=True, tipo_resposta__in=[PerguntaParticipacao.UNICA_ESCOLHA, PerguntaParticipacao.MULTIPLA_ESCOLHA]), label='Pergunta'
    )

    class Meta:
        model = OpcaoRespostaPerguntaParticipacao
        fields = ('pergunta', 'valor', 'ativo')


class CampusForm(forms.FormPlus):
    campus = forms.ModelChoiceField(label='Filtrar por Campus:', required=False, queryset=UnidadeOrganizacional.objects.uo())


class DocumentacaoInscricaoForm(forms.FormPlus):
    comprovante_residencia = forms.FileFieldPlus(label='Comprovante de Residência', required=True)
    comprovante_renda_aluno = forms.FileFieldPlus(label='Comprovante de Renda do Aluno', required=True)
    arquivos = MultiFileField(min_num=0, max_num=10, max_file_size=1024 * 1024 * 5, label='Documentos Complementares', required=False)

    def __init__(self, *args, **kwargs):
        comprov_resid_valido = kwargs.pop('comprov_resid_valido', None)
        comprovante_renda_aluno = kwargs.pop('comprovante_renda_aluno', None)
        precisa_comprovante_renda_aluno = kwargs.pop('precisa_comprovante_renda_aluno', None)
        super().__init__(*args, **kwargs)
        if comprov_resid_valido.exists():
            self.fields['comprovante_residencia'].initial = comprov_resid_valido.last().arquivo
        if not precisa_comprovante_renda_aluno:
            del self.fields['comprovante_renda_aluno']
        elif comprovante_renda_aluno.exists():
            self.fields['comprovante_renda_aluno'].initial = comprovante_renda_aluno.last().arquivo


class DocumentacaoComprovRendaInscricaoForm(forms.FormPlus):
    def __init__(self, *args, **kwargs):
        self.integrantes = kwargs.pop('integrantes', None)
        super().__init__(*args, **kwargs)
        for integrante in self.integrantes:
            label = 'Comprovante de Renda - {} '.format(integrante.nome)
            self.fields["{}".format(integrante.id)] = forms.FileFieldPlus(label=label, required=True)
            if not integrante.remuneracao:
                self.fields["{}".format(integrante.id)].help_text = 'Como não há renda declarada, anexar declaração informando que não possui renda.'

            documentacao = DocumentoInscricaoAluno.objects.filter(tipo_arquivo=DocumentoInscricaoAluno.COMPROVANTE_RENDA, integrante_familiar=integrante)
            if documentacao.exists():
                self.fields["{}".format(integrante.id)].initial = documentacao.last().arquivo


class AtualizaDocumentoAlunoForm(forms.ModelFormPlus):
    integrante_familiar = forms.ModelChoiceField(queryset=IntegranteFamiliarCaracterizacao.objects, label='Integrante Familiar', required=False)

    class Meta:
        model = DocumentoInscricaoAluno
        fields = ('integrante_familiar', 'arquivo')

    def __init__(self, *args, **kwargs):
        self.aluno = kwargs.pop('aluno', None)
        super().__init__(*args, **kwargs)
        maior_dezoito_anos = date.today() + relativedelta(years=-18)
        if IntegranteFamiliarCaracterizacao.objects.filter(inscricao_caracterizacao__aluno=self.aluno, data_nascimento__lte=maior_dezoito_anos).exists():
            self.fields['integrante_familiar'].queryset = IntegranteFamiliarCaracterizacao.objects.filter(
                inscricao_caracterizacao__aluno=self.aluno, data_nascimento__lte=maior_dezoito_anos
            )
        else:
            del self.fields['integrante_familiar']
        self.fields['arquivo'].required = True


class AdicionarDocumentoAlunoForm(forms.FormPlus):
    tipo_arquivo = forms.ChoiceField(label='Tipo do Arquivo', choices=DocumentoInscricaoAluno.TIPO_ARQUIVO_CHOICES)
    arquivo = forms.FileFieldPlus(label='Arquivo', required=True)
    integrante_familiar = forms.ModelChoiceField(queryset=IntegranteFamiliarCaracterizacao.objects, label='Integrante Familiar', required=False)

    def __init__(self, *args, **kwargs):
        self.aluno = kwargs.pop('aluno', None)
        super().__init__(*args, **kwargs)
        maior_dezoito_anos = date.today() + relativedelta(years=-18)
        if IntegranteFamiliarCaracterizacao.objects.filter(inscricao_caracterizacao__aluno=self.aluno, data_nascimento__lte=maior_dezoito_anos).exists():
            self.fields['integrante_familiar'].queryset = IntegranteFamiliarCaracterizacao.objects.filter(
                inscricao_caracterizacao__aluno=self.aluno, data_nascimento__lte=maior_dezoito_anos
            )
        else:
            del self.fields['integrante_familiar']
        self.fields['arquivo'].required = True


class GerarFolhaPagamentoForm(forms.FormPlus):
    campus = forms.ModelChoiceField(label='Filtrar por Campus:', required=False, queryset=UnidadeOrganizacional.objects.suap())

    tipo_programa = forms.ChoiceField(label='Tipo do Programa', choices=[(Programa.TIPO_TRABALHO, 'Apoio à Formação Estudantil'), (Programa.TIPO_TRANSPORTE, 'Auxílio Transporte')])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.request.user.has_perm('ae.pode_detalhar_programa_todos'):
            campus = get_uo(self.request.user)
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo().filter(id=campus.id)
            self.fields['campus'].initial = campus.id


class ListaAtendimentoRefeicoesForm(forms.FormPlus):
    METHOD = 'GET'
    campus = forms.ModelChoiceField(label='Filtrar por Campus:', required=False, queryset=UnidadeOrganizacional.objects.suap(), empty_label='Todos')
    tipo = forms.ChoiceField(label='Tipo de Atendimento', choices=DemandaAluno.TODAS_REFEICOES_CHOICES, required=False)
    data_inicio = forms.DateFieldPlus(label='Início do Período')
    data_termino = forms.DateFieldPlus(label='Término do Período')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.request.user.has_perm('ae.pode_detalhar_programa_todos'):
            campus = get_uo(self.request.user)
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo().filter(id=campus.id)
            self.fields['campus'].initial = campus.id


class IntegranteFamiliarCaracterizacaoBaseFormSet(forms.models.BaseInlineFormSet):

    def __init__(self, *args, **kwargs):
        self.aluno = kwargs.pop('aluno', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super().clean()
        forms_ids = [f.instance.id for f in self.forms]
        queryset = self.queryset.exclude(id__in=forms_ids)
        registros_composicao = self.aluno.caracterizacao.qtd_pessoas_domicilio - 1
        if registros_composicao != len(forms_ids):
            if registros_composicao == 1:
                raise ValidationError('Por favor, preencha as informações da pessoa que mora com você.')
            else:
                raise ValidationError('Por favor, preencha as informações das {} pessoas que moram com você.'.format(registros_composicao))

        if queryset.exists():
            raise ValidationError('A quantidade de integrantes familiares deve ser igual à quantidade informada na pergunta "Número de pessoas no domicílio", respondida na Caracterização Socioeconômica, menos 1 (não é necessário incluir seus dados aqui).')

        return cleaned_data


class IntegranteFamiliarCaracterizacaoForm(forms.ModelFormPlus):
    class Meta:
        model = IntegranteFamiliarCaracterizacao
        fields = '__all__'
        labels = {
            "remuneracao": "Renda Bruta"
        }


class SolicitacaoAuxilioAlunoForm(forms.ModelFormPlus):
    class Meta:
        model = SolicitacaoAuxilioAluno
        fields = ('tipo_auxilio', 'motivo_solicitacao', 'comprovante')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['comprovante'].required = False
        if not DocumentoInscricaoAluno.objects.filter(aluno=self.request.user.get_relacionamento(), tipo_arquivo=DocumentoInscricaoAluno.COMPROVANTE_RENDA).exists():
            self.fields[
                'comprovante'
            ].help_text = 'Adicione um arquivo ZIP com os comprovantes de renda dos integrantes familiares. Auxílios para exames, medicamentos e óculos exigem o anexo do comprovante da necessidade.'
        else:
            self.fields['comprovante'].help_text = 'Auxílios para exames, medicamentos e óculos exigem o anexo do comprovante da necessidade.'
        self.fields['motivo_solicitacao'].widget = forms.Textarea()
        self.fields['tipo_auxilio'].queryset = TipoAuxilioEventual.objects.filter(ativo=True)

    def clean(self):
        cleaned_data = super().clean()
        if cleaned_data.get('tipo_auxilio') and cleaned_data.get('tipo_auxilio').exige_comprovante and not cleaned_data.get('comprovante'):
            self.add_error('comprovante', 'Este(s) tipo(s) de auxílio(s) exige(m) o anexo do comprovante da necessidade.')

        return cleaned_data


class AvaliarSolicitacaoAuxilioForm(forms.ModelFormPlus):
    deferida = forms.BooleanField(label='Deferida', required=False)

    class Meta:
        model = SolicitacaoAuxilioAluno
        fields = ('deferida', 'parecer_avaliacao')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['parecer_avaliacao'].widget = forms.Textarea()


class AuxilioEventualForm(forms.ModelFormPlus):
    class Meta:
        model = AuxilioEventual
        fields = ('campus', 'aluno', 'tipo_auxilio', 'data', 'quantidade', 'valor', 'observacao', 'arquivo')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.request.user.has_perm('ae.pode_detalhar_programa_todos'):
            campus = get_uo(self.request.user)
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo().filter(id=campus.id)
            self.fields['campus'].initial = campus.id
        self.fields['tipo_auxilio'].queryset = TipoAuxilioEventual.objects.filter(ativo=True)


class EstatisticaInscricoesForm(forms.FormPlus):
    EM_DIA = '1'
    NAO_ENTEGUE = '2'
    EXPIRADA = '3'

    OPCOES = (('', 'Todos'), (EM_DIA, 'Em Dia'), (NAO_ENTEGUE, 'Não Entregue'), (EXPIRADA, 'Expirada'))
    campus = forms.ModelChoiceField(
        queryset=UnidadeOrganizacional.objects.uo().all(), widget=AutocompleteWidget(search_fields=UnidadeOrganizacional.SEARCH_FIELDS), label='Campus', required=False
    )
    documentacao = forms.ChoiceField(label='Situação da Documentação', choices=OPCOES, required=False)


class ImportarCaracterizacaoForm(FormWizardPlus):
    ano = forms.ModelChoiceField(Ano.objects.all(), label='Ano', required=True)
    semestre = periodo_letivo = forms.ChoiceField(choices=[[0, '----']] + PERIODO_LETIVO_CHOICES, label='Semestre', required=True)
    edital = forms.ChoiceField(choices=[], label='Edital', widget=forms.Select(attrs=dict(style='width:600px')))

    steps = ([('Período Letivo', {'fields': ('ano', 'semestre')})], [('Seleção do Edital', {'fields': ('edital',)})])

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def next_step(self):
        if 'edital' in self.fields:
            Edital = apps.get_model('processo_seletivo', 'Edital')
            if Edital:
                queryset = Edital.objects.filter(sisu=False, ano=self.get_entered_data('ano'), semestre=self.get_entered_data('semestre'))
                self.fields['edital'] = forms.ModelChoiceFieldPlus(queryset, label='Edital')

    def processar(self):
        edital = self.cleaned_data['edital']
        return edital.importar_caracterizacoes()


class RelatorioDemandaReprimidaForm(forms.FormPlus):
    ano = forms.ModelChoiceField(Ano.objects.all(), label='Ano', required=True)
    campus = forms.ModelChoiceField(
        queryset=UnidadeOrganizacional.objects.uo().all(), label='Campus', required=False
    )
    programa = forms.ChainedModelChoiceField(
        Programa.objects, label='Filtrar por Programa:', empty_label='Selecione o Campus', required=False, obj_label='titulo', form_filters=[('campus', 'instituicao_id')]
    )


class AdicionarDadoBancarioForm(forms.ModelFormPlus):
    numero_conta = forms.CharField(label='Número da Conta', required=True, widget=forms.TextInput(attrs={'pattern': '[0-9a-zA-Z]+'}), help_text='Utilize apenas números e letras')

    class Meta:
        model = DadosBancarios
        fields = ('instituicao', 'numero_agencia', 'tipo_conta', 'numero_conta', 'operacao', 'prioritario_servico_social')

    def __init__(self, aluno, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        self.instance.aluno = aluno
        if aluno.is_user(self.request):
            del self.fields['prioritario_servico_social']
        self.fields['instituicao'].queryset = Banco.objects.filter(excluido=False).exclude(sigla='').order_by('nome')

    def clean(self):
        prioritario_servico_social = self.cleaned_data.get('prioritario_servico_social')
        dados = DadosBancarios.objects.filter(aluno=self.instance.aluno, prioritario_servico_social=True)
        if prioritario_servico_social and dados.exists():
            if (self.instance.pk and dados.exclude(id=self.instance.pk).exists()) or not self.instance.pk:
                raise forms.ValidationError('Já existe outro Dado Bancário marcado como prioritário para este aluno.')
        return self.cleaned_data

    def clean_instituicao(self):
        banco = self.cleaned_data.get('instituicao')
        if not self.instance.instituicao == banco and self.instance.aluno.get_dados_bancarios().filter(instituicao=banco).exists():
            raise forms.ValidationError("Não é possível adicionar mais de uma conta bancária para o mesmo banco.")
        return self.cleaned_data.get('instituicao')
