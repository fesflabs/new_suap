from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db.models import Q
from django.db.models.aggregates import Sum

from comum.models import Ano
from django.db import transaction

from comum.utils import tl
from djtools import forms
from djtools.forms import ModelFormPlus
from djtools.forms.widgets import RenderableSelectMultiple, AutocompleteWidget, FilteredSelectMultiplePlus
from djtools.templatetags.filters import format_money
from financeiro.models import AcaoAno

from plan_estrategico.models import (
    PDI,
    Perspectiva,
    PDIPerspectiva,
    UnidadeGestora,
    ObjetivoEstrategico,
    ProjetoEstrategico,
    EtapaProjeto,
    Indicador,
    MetaIndicador,
    PDIObjetivoEstrategico,
    PDIIndicador,
    ObjetivoIndicador,
    VariavelCampus,
    ArquivoMeta,
    PlanoAtividade,
    OrigemRecurso,
    ProjetoPlanoAtividade,
    EtapaProjetoPlanoAtividade,
    OrigemRecursoProjeto,
    OrigemRecursoProjetoEtapa,
    UnidadeGestoraEtapa,
    AtividadeEtapa,
    NaturezaDespesaPlanoAtividade,
    UnidadeOrigemEtapa,
    PeriodoPreenchimentoVariavel,
    TematicaVariavel)


from plan_estrategico.utils import get_setor_unidade_gestora
from rh.models import Setor, UnidadeOrganizacional, PessoaFisica, Servidor


class PDIForm(forms.ModelFormPlus):
    ano_inicial_pdi = forms.ModelChoiceField(label='Ano Inicial', help_text='Vigência inicial do PDI', queryset=Ano.objects)
    ano_final_pdi = forms.ModelChoiceField(label='Ano Final', help_text='Vigência final do PDI', queryset=Ano.objects)
    qtd_anos = forms.IntegerField(label='Duração do PDI em anos')

    class Meta:
        model = PDI
        fields = ('qtd_anos', 'ano_inicial_pdi', 'ano_final_pdi', 'documento', 'mapa_estrategico', 'manual')

    def clean(self):
        super().clean()
        if 'ano_inicial_pdi' in self.cleaned_data and 'ano_final_pdi' in self.cleaned_data:
            if self.cleaned_data['ano_inicial_pdi'].ano > self.cleaned_data['ano_final_pdi'].ano:
                self.add_error('ano_final_pdi', 'O ano final deve ser maior que o inicial.')

            elif 'qtd_anos' in self.cleaned_data and self.cleaned_data['qtd_anos'] and self.cleaned_data['ano_final_pdi'].ano - self.cleaned_data['ano_inicial_pdi'].ano != (self.cleaned_data['qtd_anos'] - 1):
                self.add_error('ano_final_pdi', 'O período não corresponde a duração do PDI.')

        return self.cleaned_data


class PerspectivaForm(forms.ModelFormPlus):
    class Meta:
        model = Perspectiva
        fields = ('sigla', 'nome', 'descricao')


class AssociarPerspectivaPDIForm(forms.FormPlus):
    SUBMIT_LABEL = 'Adicionar apenas selecionados'

    perspectivas = forms.MultipleModelChoiceField(Perspectiva.objects, label='', required=False, widget=RenderableSelectMultiple('widgets/perspectivas_widget.html'))

    def __init__(self, *args, **kwargs):
        self.pdi = kwargs.pop('pdi')
        super().__init__(*args, **kwargs)

        m_initial = PDIPerspectiva.objects.filter(pdi=self.pdi).values_list('perspectiva__pk', flat=True)

        qs = Perspectiva.objects.all()

        self.fields['perspectivas'].queryset = qs
        self.fields['perspectivas'].initial = m_initial

    @transaction.atomic()
    def save(self):
        # Adiciona as perspectivas novas
        m_ids = list()
        for perspectiva in self.cleaned_data['perspectivas']:
            pass
            m_ids.append(perspectiva.pk)
            if not PDIPerspectiva.objects.filter(pdi=self.pdi, perspectiva=perspectiva).exists():
                PDIPerspectiva.objects.create(pdi=self.pdi, perspectiva=perspectiva)

        for pdi_perspectiva in PDIPerspectiva.objects.filter(pdi=self.pdi).exclude(perspectiva__pk__in=m_ids):
            pdi_perspectiva.delete()


class AssociarObjetivoPDIForm(forms.FormPlus):
    SUBMIT_LABEL = 'Adicionar apenas selecionados'

    objetivos = forms.MultipleModelChoiceField(queryset=ObjetivoEstrategico.objects, label='', required=False, widget=RenderableSelectMultiple('widgets/objetivos_widget.html'))

    def __init__(self, *args, **kwargs):
        self.pdi = kwargs.pop('pdi')
        self.pdi_perspectiva = kwargs.pop('perspectiva')

        super().__init__(*args, **kwargs)

        selecionados = PDIObjetivoEstrategico.objects.filter(pdi_perspectiva=self.pdi_perspectiva).values_list('objetivo__pk', flat=True)
        qs = ObjetivoEstrategico.objects.filter(Q(pdiobjetivoestrategico__isnull=True) | Q(pdiobjetivoestrategico__pdi_perspectiva=self.pdi_perspectiva))
        self.fields['objetivos'].queryset = qs

        if selecionados:
            self.fields['objetivos'].initial = selecionados

    @transaction.atomic()
    def save(self):
        m_ids = list()
        for objetivo in self.cleaned_data['objetivos']:
            m_ids.append(objetivo.pk)
            if not PDIObjetivoEstrategico.objects.filter(pdi_perspectiva=self.pdi_perspectiva, objetivo=objetivo).exists():
                PDIObjetivoEstrategico.objects.create(pdi_perspectiva=self.pdi_perspectiva, objetivo=objetivo)

        for pdi_objetivo in PDIObjetivoEstrategico.objects.filter(pdi_perspectiva=self.pdi_perspectiva).exclude(objetivo__pk__in=m_ids):
            pdi_objetivo.delete()


class AssociarIndicadorPDIForm(forms.FormPlus):
    SUBMIT_LABEL = 'Adicionar apenas selecionados'

    indicadores = forms.MultipleModelChoiceField(Indicador.objects, label='', required=False, widget=RenderableSelectMultiple('widgets/indicadores_widget.html'))

    def __init__(self, *args, **kwargs):
        self.pdi = kwargs.pop('pdi')
        self.pdi_objetivo = kwargs.pop('objetivo')
        super().__init__(*args, **kwargs)

        selecionados = PDIIndicador.objects.filter(objetivos=self.pdi_objetivo).values_list('indicador__pk', flat=True)

        self.fields['indicadores'].querset = Indicador.objects.all()
        self.fields['indicadores'].initial = selecionados

    @transaction.atomic()
    def save(self):
        m_ids = list()

        for indicador in self.cleaned_data['indicadores']:
            m_ids.append(indicador.pk)
            if not PDIIndicador.objects.filter(pdi=self.pdi, indicador=indicador).exists():
                pdi_indicador = PDIIndicador.objects.create(pdi=self.pdi, indicador=indicador)
                pdi_indicador.objetivos.add(self.pdi_objetivo)

                ObjetivoIndicador.objects.create(indicador=pdi_indicador, objetivo_estrategico=self.pdi_objetivo, relevancia=0)
            else:
                pdi_indicador = PDIIndicador.objects.get(pdi=self.pdi, indicador=indicador)
                if not pdi_indicador.objetivos.filter(id=self.pdi_objetivo.pk).exists():
                    pdi_indicador.objetivos.add(self.pdi_objetivo)
                    objetivo_indicador = ObjetivoIndicador.objects.filter(indicador=pdi_indicador, objetivo_estrategico=self.pdi_objetivo)
                    if objetivo_indicador.exists():
                        objetivo_indicador[0].relevancia = 0
                    else:
                        ObjetivoIndicador.objects.create(indicador=pdi_indicador, objetivo_estrategico=self.pdi_objetivo, relevancia=0)

        for pdi_indicador in PDIIndicador.objects.filter(pdi=self.pdi, objetivos=self.pdi_objetivo).exclude(indicador__pk__in=m_ids):
            pdi_indicador.objetivos.remove(self.pdi_objetivo)
            ObjetivoIndicador.objects.filter(indicador=pdi_indicador, objetivo_estrategico=self.pdi_objetivo).delete()


class UnidadeGestoraForm(forms.ModelFormPlus):
    setor_equivalente = forms.ModelChoiceFieldPlus2(
        label_template='{{obj.sigla|rjust:"15"}} - {{obj.nome}}',
        label='Setor',
        help_text='Setor que responde pela unidade gestora',
        queryset=Setor.objects.all().order_by('sigla', 'nome'),
        widget=AutocompleteWidget(search_fields=Setor.SEARCH_FIELDS),
    )

    class Meta:
        model = UnidadeGestora
        fields = ('tipo', 'setor_equivalente', 'codigo_projeto', 'recurso_total')

    def __init__(self, *args, **kwargs):
        pdi = kwargs.pop('pdi')
        super().__init__(*args, **kwargs)
        self.instance.pdi = pdi

    def clean(self):
        if not self.errors:
            if self.cleaned_data['setor_equivalente']:
                if not self.instance.pk and UnidadeGestora.objects.filter(setor_equivalente=self.cleaned_data['setor_equivalente'], pdi=self.instance.pdi).exists():
                    self.add_error('setor_equivalente', 'Unidade Gestora com este Setor Equivalente já existe para este PDI.')
            if (self.cleaned_data['tipo'] == UnidadeGestora.TIPO_DIRETORIA or self.cleaned_data['tipo'] == UnidadeGestora.TIPO_PRO_REITORIA) and not self.cleaned_data[
                'codigo_projeto'
            ]:
                self.add_error('codigo_projeto', 'Este campo é obrigatório para o tipo de unidade gestora selecionado.')
        return self.cleaned_data


class AtividadeEtapaForm(forms.ModelFormPlus):
    origem_recurso_etapa = forms.ModelChoiceFieldPlus2(
        label='Origem de recurso', help_text='Origem de recurso da etapa', queryset=OrigemRecursoProjetoEtapa.objects.all(), required=False
    )

    naturezadespesa = forms.ModelChoiceFieldPlus2(
        label='Natureza de despesa',
        queryset=NaturezaDespesaPlanoAtividade.objects.all(),
        required=False,
        widget=AutocompleteWidget(search_fields=NaturezaDespesaPlanoAtividade.SEARCH_FIELDS),
    )

    unidade_gestora = forms.ModelChoiceFieldPlus2(
        label='Unidade gestora', queryset=UnidadeGestora.objects.all(), required=False, widget=AutocompleteWidget(search_fields=UnidadeGestora.SEARCH_FIELDS, readonly=True)
    )

    valor = forms.DecimalFieldPlus(label='Valor Proposto R$', required=False)

    class Meta:
        model = AtividadeEtapa
        fields = ('nome', 'descricao', 'valor', 'origem_recurso_etapa', 'naturezadespesa', 'unidade_gestora')

    def __init__(self, *args, **kwargs):
        etapa = kwargs.pop('etapa')
        super().__init__(*args, **kwargs)
        self.instance.etapa_projeto_plano_atividade = etapa

        naturezas_planoatividade = NaturezaDespesaPlanoAtividade.objects.filter(plano_atividade=self.instance.etapa_projeto_plano_atividade.projeto_plano_atividade.plano_atividade)
        self.fields['naturezadespesa'].queryset = naturezas_planoatividade
        # sobrescrevendo o querySet de origem_recurso_etapa
        qs = OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade=self.instance.etapa_projeto_plano_atividade)

        self.fields['origem_recurso_etapa'].queryset = qs

        qs = UnidadeGestora.objects.filter(setor_equivalente=get_setor_unidade_gestora(user=self.request.user))[0]

        self.fields['unidade_gestora'].initial = qs
        self.fields['valor'].initial = Decimal(0)

    def clean(self):
        super().clean()
        if self.cleaned_data.get('valor') is None:
            self.add_error('valor', 'Informe um valor')
        if not self.cleaned_data['origem_recurso_etapa']:
            self.add_error('origem_recurso_etapa', 'Selecione uma origem de recurso')
        if not self.cleaned_data['naturezadespesa']:
            self.add_error('naturezadespesa', 'Selecione uma natureza de despesa')
        return self.cleaned_data


class ProjetoEstrategicoPDIForm(forms.ModelFormPlus):
    objetivo_estrategico = forms.ModelMultipleChoiceField(
        label='Objetivo Estratégico', required=True, widget=FilteredSelectMultiplePlus('', True), queryset=PDIObjetivoEstrategico.objects.all()
    )
    data_inicio = forms.DateFieldPlus(label="Data Inicial")
    data_fim = forms.DateFieldPlus(label='Data Final')

    fieldsets = (
        (None, {'fields': (('nome',),)}),
        (None, {'fields': (('descricao',),)}),
        ('', {'fields': (('meta_projeto', 'unidade_medida'),)}),
        ('', {'fields': (('objetivo_estrategico',),)}),
        ('', {'fields': (('data_inicio', 'data_fim', 'tipo'),)}),
        ('', {'fields': (('unidade_gestora', 'recurso_total', 'anexo'),)}),
    )

    class Meta:
        model = ProjetoEstrategico
        fields = ('nome', 'descricao', 'objetivo_estrategico', 'unidade_gestora', 'recurso_total', 'meta_projeto', 'unidade_medida', 'anexo', 'data_inicio', 'data_fim', 'tipo')

    def __init__(self, *args, **kwargs):
        pdi = kwargs.pop('pdi')
        super().__init__(*args, **kwargs)
        self.instance.pdi = pdi
        if self.instance.pk:
            self.initial['objetivo_estrategico'] = [o.pk for o in self.instance.objetivo_estrategico.all()]

        # Exibe apenas as unidades gestores do tipo Pró-Reitoria e Diretoria Sistêmica
        qs = UnidadeGestora.objects.filter(setor_equivalente=get_setor_unidade_gestora(user=self.request.user))
        self.fields['unidade_gestora'].queryset = qs

    def clean(self):
        super().clean()

        if 'data_inicio' in self.cleaned_data and 'data_fim' in self.cleaned_data:
            if self.cleaned_data['data_inicio'] > self.cleaned_data['data_fim']:
                self.add_error('data_fim', 'A data final deve ser maior que a data inicial.')

        return self.cleaned_data


class EtapaProjetoForm(forms.ModelFormPlus):
    data_inicio = forms.DateFieldPlus(label="Data Inicial da Etapa")
    data_fim = forms.DateFieldPlus(label='Data Final da Etapa')

    class Meta:
        model = EtapaProjeto
        fields = ('codigo', 'descricao', 'data_inicio', 'data_fim', 'objetivo_etapa', 'responsaveis_etapa', 'meta_etapa', 'unidade_medida', 'valor_etapa')

    def __init__(self, *args, **kwargs):
        projeto = kwargs.pop('projeto')
        super().__init__(*args, **kwargs)
        self.instance.projeto = projeto

        q_etapas = EtapaProjeto.objects.filter(projeto=self.instance.projeto).count()
        if self.instance.pk:
            self.fields['codigo'].initial = self.instance.codigo
        else:
            self.fields['codigo'].initial = q_etapas + 1

    def clean(self):
        super().clean()
        if 'codigo' in self.cleaned_data:
            if not self.instance.pk or (self.instance.pk and not self.instance.codigo == self.cleaned_data['codigo']):
                if EtapaProjeto.objects.filter(projeto=self.instance.projeto, codigo=self.cleaned_data['codigo']).exists():
                    self.add_error('codigo', 'Este código já está sendo usado por outra etapa deste projeto.')
        if 'data_inicio' in self.cleaned_data and 'data_fim' in self.cleaned_data:
            if self.cleaned_data['data_inicio'] > self.cleaned_data['data_fim']:
                self.add_error('data_fim', 'A data final deve ser maior que a data inicial.')
        if 'valor_etapa' in self.cleaned_data:
            if (self.instance.projeto.get_saldo_projeto() + (self.instance.valor_etapa or 0)) < self.cleaned_data['valor_etapa']:
                self.add_error('valor_etapa', 'Valor da etapa maior que o saldo do projeto.')
        return self.cleaned_data


def MetaIndicadorFormFactory(indicador):
    class MetaIndicadorForm(forms.FormPlus):
        valor_referencia = forms.DecimalField(label='Referência', initial=indicador.get_valor_referencia, decimal_places=indicador.casas_decimais)

        SUBMIT_LABEL = 'Atualizar Metas'

        fieldsets = [(None, {'fields': ('valor_referencia', 'valor_referencia0', 'valor_referencia1', 'valor_referencia2', 'valor_referencia3', 'valor_referencia4')})]

        def save(self):
            self.indicador.valor_referencia = self.cleaned_data['valor_referencia']
            self.indicador.save()

            for nome, campo in list(self.cleaned_data.items()):
                if not nome.startswith('meta_ano'):
                    continue
                meta = MetaIndicador.objects.get(indicador=self.indicador, ano=nome.split('_')[-1])
                meta.meta = self.cleaned_data[nome]
                meta.save()

    MetaIndicadorForm.indicador = indicador

    fs_fields = list()

    for meta in indicador.metaindicador_set.all():
        field_name = 'meta_ano_{}'.format(meta.ano)
        fs_fields.append(field_name)
        MetaIndicadorForm.base_fields[field_name] = forms.DecimalField(label='{}'.format(meta.ano), initial=meta.get_valor_meta, decimal_places=indicador.casas_decimais)

    MetaIndicadorForm.fieldsets.append(('Anuais', {'fields': fs_fields}))

    return MetaIndicadorForm


def ObjetivoIndicadorFormFactory(objetivo):
    class ObjetivoIndicadorForm(forms.FormPlus):
        SUBMIT_LABEL = 'Atualizar Relevâncias'

        fieldsets = [(None, {'fields': ('valor_relevancia', 'valor_relevancia0', 'valor_relevancia1', 'valor_relevancia2', 'valor_relevancia3', 'valor_relevancia4')})]

        def clean(self):
            super().clean()
            total = 0
            for nome, campo in list(self.cleaned_data.items()):
                total += self.cleaned_data[nome]
            if total > 100:
                self.add_error('', ' Percentuais maior que 100%')
            elif total < 100:
                self.add_error('', ' Percentuais menor que 100%')
            return self.cleaned_data

        def save(self):
            for nome, campo in list(self.cleaned_data.items()):
                if not nome.startswith('objetivoindicador'):
                    continue
                objetivo_indicador = ObjetivoIndicador.objects.get(indicador=nome.split('_')[-1], objetivo_estrategico=self.objetivo)
                objetivo_indicador.relevancia = self.cleaned_data[nome]
                objetivo_indicador.save()

    ObjetivoIndicadorForm.objetivo = objetivo

    fs_fields = list()
    for objetivo in objetivo.objetivoindicador_set.all().order_by('id'):

        field_name = 'objetivoindicador_{}'.format(objetivo.indicador.id)
        fs_fields.append(field_name)
        ObjetivoIndicadorForm.base_fields[field_name] = forms.DecimalField(
            label='{}'.format(objetivo.indicador), initial=objetivo.relevancia, decimal_places=objetivo.indicador.casas_decimais
        )

    ObjetivoIndicadorForm.fieldsets.append(('indicadores', {'fields': fs_fields}))

    return ObjetivoIndicadorForm


def farol_filtro_formfactory(pdi, sigla_instituicao):
    ano_choices = [[ano, ano] for ano in range(pdi.ano_inicial_pdi.ano, pdi.ano_final_pdi.ano + 1)]

    class FarolFiltro1Form(forms.FormPlus):
        ano = forms.ChoiceField(label='Ano', choices=ano_choices, required=False)
        perspectiva = forms.ModelChoiceField(label='Perspectiva', queryset=Perspectiva.objects, required=False)
        campus = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False, empty_label=sigla_instituicao)

        def __init__(self, *args, **kwargs):
            pdi = kwargs.pop('pdi')
            ano_base = kwargs.pop('ano_base')

            uo = kwargs.pop('uo')
            self.base_fields['ano'].initial = ano_base
            if uo:
                self.base_fields['campus'].initial = uo.id
            super().__init__(*args, **kwargs)

            choices = list()
            for ano in range(pdi.ano_inicial_pdi.ano, pdi.ano_final_pdi.ano):
                choices.append((ano, ano))

            self.base_fields['ano'].choices = choices

    return FarolFiltro1Form


def farol_indicadores_filtro_formfactory(pdi, sigla_instituicao, objetivo):
    ano_choices = [[ano, ano] for ano in range(pdi.ano_inicial_pdi.ano, pdi.ano_final_pdi.ano + 1)]

    class FarolFiltro2Form(forms.FormPlus):
        ano = forms.ChoiceField(label='Ano', choices=ano_choices, required=False)
        campus = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False, empty_label=sigla_instituicao)
        indicador = forms.ModelChoiceField(label='Indicador', queryset=PDIIndicador.objects.filter(pdi=pdi), required=False)

        def __init__(self, *args, **kwargs):
            pdi = kwargs.pop('pdi')
            ano_base = kwargs.pop('ano_base')
            uo = kwargs.pop('uo')

            self.base_fields['ano'].initial = ano_base
            if uo:
                self.base_fields['campus'].initial = uo.id
            self.base_fields['indicador'].queryset = PDIIndicador.objects.filter(objetivoindicador__objetivo_estrategico=objetivo, pdi=pdi)
            super().__init__(*args, **kwargs)

            choices = list()
            for ano in range(pdi.ano_inicial_pdi.ano, pdi.ano_final_pdi.ano):
                choices.append((ano, ano))

            self.base_fields['ano'].choices = choices
            self.base_fields['ano'].initial = ano_base

    return FarolFiltro2Form


class VariavelCampusForm(forms.ModelFormPlus):
    class Meta:
        model = VariavelCampus
        fields = ('valor_trimestral',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class VariavelCampusIdealForm(forms.ModelFormPlus):
    class Meta:
        model = VariavelCampus
        fields = ('valor_ideal',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


class ArquivoMetaForm(forms.ModelFormPlus):
    class Meta:
        model = ArquivoMeta
        fields = ('arquivo',)


# retorna um choice contendo os anos que ainda não foram cadastrados
def anos_disponiveis_as_choices(id_pdi):
    pdi = PDI.objects.get(pk=id_pdi)
    anos_cadastrados = list(PlanoAtividade.objects.filter(pdi=id_pdi).values_list('ano_base__ano', flat=True))

    total_anos = []
    for ano in range(pdi.ano_inicial_pdi.ano, pdi.ano_final_pdi.ano + 1):

        total_anos.append(ano)
    for ano in anos_cadastrados:

        if ano == total_anos:
            continue
        if ano in total_anos:
            total_anos.remove(ano)
    anos = Ano.objects.filter(ano__in=total_anos)
    return anos


class PlanoAtividadePDIForm(forms.ModelFormPlus):
    ano_base = forms.ModelChoiceField(label='Ano Base', help_text='Ano de realização das atividades', queryset=Ano.objects.all())
    data_geral_inicial = forms.DateFieldPlus(label="Início")
    data_geral_final = forms.DateFieldPlus(label='Fim')
    data_orcamentario_preloa_inicial = forms.DateFieldPlus(label="Início Orçamentário")
    data_orcamentario_preloa_final = forms.DateFieldPlus(label='Fim Orçamentário')
    data_projetos_preloa_inicial = forms.DateFieldPlus(label="Início Projetos")
    data_projetos_preloa_final = forms.DateFieldPlus(label='Fim Projetos')
    data_atividades_preloa_inicial = forms.DateFieldPlus(label="Início Atividades")
    data_atividades_preloa_final = forms.DateFieldPlus(label='Fim Atividades')
    data_orcamentario_posloa_inicial = forms.DateFieldPlus(label="Início Orçamentário")
    data_orcamentario_posloa_final = forms.DateFieldPlus(label='Fim Orçamentário')
    data_projetos_posloa_inicial = forms.DateFieldPlus(label="Início Projetos")
    data_projetos_posloa_final = forms.DateFieldPlus(label='Fim Projetos')
    data_atividades_posloa_inicial = forms.DateFieldPlus(label="Início Atividades")
    data_atividades_posloa_final = forms.DateFieldPlus(label='Fim atividades')
    percentual_reserva_tecnica = forms.IntegerField(label='Percentual Reserva Técnica')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # se o pdi foi passado via url (get method) ou se trata de uma edição
        if 'pdi' in self.request.GET:
            self.fields['ano_base'].queryset = anos_disponiveis_as_choices(self.request.GET['pdi'])

        if self.instance.pk:
            self.fields['ano_base'].initial = self.instance.ano_base
            queryset = anos_disponiveis_as_choices(self.instance.pdi.id)
            self.fields['ano_base'].queryset = queryset | Ano.objects.filter(id=self.instance.ano_base.id)

    def clean(self):
        errors = dict()
        if not self.errors:
            if self.cleaned_data['percentual_reserva_tecnica']:
                if self.cleaned_data['percentual_reserva_tecnica'] > 100 or 0 > self.cleaned_data['percentual_reserva_tecnica']:
                    self.add_error('percentual_reserva_tecnica', 'O Percentual da reserva técnica deve estar compreendido entre 0 e 100.')

            if self.cleaned_data['data_geral_final'] <= self.cleaned_data['data_geral_inicial']:
                self.add_error('data_geral_final', 'A data final não pode ser menor ou igual à data inicial.')

            if not self.cleaned_data.get('data_orcamentario_preloa_inicial') < self.cleaned_data.get('data_orcamentario_preloa_final'):
                errors['data_orcamentario_preloa_inicial'] = ['Esta data deve ser menor que a data final da fase Pré-LOA Orçamentária.']

            if not self.cleaned_data.get('data_orcamentario_preloa_inicial') < self.cleaned_data.get('data_orcamentario_preloa_final') < self.cleaned_data.get('data_projetos_preloa_inicial'):
                errors['data_orcamentario_preloa_final'] = ['Esta data deve ser maior que a data inicial da fase Pré-LOA Orçamentária e menor que a data inicial da fase Pré-LOA de projetos.']

            if not self.cleaned_data.get('data_orcamentario_preloa_final') < self.cleaned_data.get('data_projetos_preloa_inicial') < self.cleaned_data.get('data_projetos_preloa_final'):
                errors['data_projetos_preloa_inicial'] = ['Esta data deve ser maior que a data final da fase Pré-LOA Orçamentária e menor que a data final da fase Pré-LOA de projetos.']

            if not self.cleaned_data.get('data_projetos_preloa_inicial') < self.cleaned_data.get(
                    'data_projetos_preloa_final') < self.cleaned_data.get('data_atividades_preloa_inicial'):
                errors['data_projetos_preloa_final'] = ['Esta data deve ser maior que a data inicial da fase Pré-LOA de projetos e menor que a data inicial da fase Pré-LOA de atividades.']

            if not self.cleaned_data.get('data_projetos_preloa_final') < self.cleaned_data.get('data_atividades_preloa_inicial') < self.cleaned_data.get('data_atividades_preloa_final'):
                errors['data_atividades_preloa_inicial'] = ['Esta data deve ser maior que a data final da fase Pré-LOA de projetos e menor que a data final da fase Pré-LOA de atividades.']

            if not self.cleaned_data.get('data_atividades_preloa_inicial') < self.cleaned_data.get('data_atividades_preloa_final') < self.cleaned_data.get('data_orcamentario_posloa_inicial'):
                errors['data_atividades_preloa_final'] = ['Esta data deve ser maior que a data inicial da fase Pré-LOA de atividades e menor que a data inicial da fase Pós-LOA de Orçamentária.']

            if not self.cleaned_data.get('data_atividades_preloa_final') < self.cleaned_data.get('data_orcamentario_posloa_inicial') < self.cleaned_data.get('data_orcamentario_posloa_final'):
                errors['data_orcamentario_posloa_inicial'] = ['Esta data deve ser maior que a data final da fase Pré-LOA de atividades e menor que a data final da fase Pós-LOA de Orçamentária.']

            if not self.cleaned_data.get('data_orcamentario_posloa_inicial') < self.cleaned_data.get('data_orcamentario_posloa_final') < self.cleaned_data.get('data_projetos_posloa_inicial'):
                errors['data_orcamentario_posloa_final'] = ['Esta data deve ser maior que a data inicial da fase Pós-LOA Orçamentária e menor que a data final da fase Pós-LOA de projetos.']

            if not self.cleaned_data.get('data_orcamentario_posloa_final') < self.cleaned_data.get('data_projetos_posloa_inicial') < self.cleaned_data.get('data_projetos_posloa_final'):
                errors['data_projetos_posloa_inicial'] = ['Esta data deve ser maior que a data final da fase Pós-LOA Orçamentária e menor que a data inicial da fase Pós-LOA de projetos.']

            if not self.cleaned_data.get('data_projetos_posloa_inicial') < self.cleaned_data.get('data_projetos_posloa_final') < self.cleaned_data.get('data_atividades_posloa_inicial'):
                errors['data_projetos_posloa_final'] = ['Esta data deve ser maior que a data inicial da fase Pós-LOA projetos e menor que a data inicial da fase Pós-LOA de atividades.']

            if not self.cleaned_data.get('data_projetos_posloa_final') < self.cleaned_data.get('data_atividades_posloa_inicial') < self.cleaned_data.get('data_atividades_posloa_final'):
                errors['data_atividades_posloa_inicial'] = ['Esta data deve ser maior que a data final da fase Pós-LOA projetos e menor que a data final da fase Pós-LOA de atividades.']

            if not self.cleaned_data.get('data_atividades_posloa_inicial') < self.cleaned_data.get('data_atividades_posloa_final') < self.cleaned_data.get('data_geral_final'):
                errors['data_atividades_posloa_final'] = ['Esta data deve ser maior que a data inicial da fase Pós-LOA atividades e menor que a data final do plano de atividades.']

        if errors:
            raise ValidationError(errors)
        return self.cleaned_data


class OrigemRecursoForm(forms.ModelFormPlus):
    acao_financeira = forms.ModelChoiceFieldPlus(
        label='Ação Orçamentária', help_text='', queryset=AcaoAno.objects, widget=AutocompleteWidget(label_value='codigo_e_ptres', search_fields=AcaoAno.SEARCH_FIELDS)
    )

    class Meta:
        model = OrigemRecurso
        fields = ('acao_financeira', 'gnd')

    def __init__(self, *args, **kwargs):
        self.plano_atividade = kwargs.pop('plano_atividade')
        super().__init__(*args, **kwargs)
        self.instance.plano_atividade = self.plano_atividade

        self.fields['acao_financeira'].queryset = AcaoAno.objects.filter(ano_base=self.plano_atividade.ano_base)


class NaturezaDespesaForm(forms.ModelFormPlus):
    class Meta:
        model = NaturezaDespesaPlanoAtividade
        fields = ('natureza_despesa',)

    def __init__(self, *args, **kwargs):
        self.plano_atividade = kwargs.pop('plano_atividade')
        super().__init__(*args, **kwargs)
        self.instance.plano_atividade = self.plano_atividade

    def clean(self):
        if not self.errors:
            if self.cleaned_data['natureza_despesa']:
                if (
                    not self.instance.pk
                    and NaturezaDespesaPlanoAtividade.objects.filter(natureza_despesa=self.cleaned_data['natureza_despesa'], plano_atividade=self.instance.plano_atividade).exists()
                ):
                    self.add_error('natureza_despesa', 'Esta Natureza de Despesa já está vinculada para este Plano de Atividades.')
        return self.cleaned_data


class AssociarProjetosPlanoAtividadeForm(forms.FormPlus):
    SUBMIT_LABEL = 'Adicionar apenas selecionados'

    # projetos selecionados
    projetos = forms.MultipleModelChoiceField(queryset=ProjetoEstrategico.objects, label='', required=False, widget=RenderableSelectMultiple('widgets/projetos_widget.html'))

    def __init__(self, *args, **kwargs):
        self.plano = kwargs.pop('plano')
        self.servidor = kwargs.pop('servidor')

        super().__init__(*args, **kwargs)
        # recupera todos os projetos do plano de atividade
        m_initial = ProjetoPlanoAtividade.objects.filter(
            plano_atividade=self.plano, projeto__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=self.servidor)
        ).values_list('projeto__pk', flat=True)

        qs = ProjetoEstrategico.objects.filter(unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=self.servidor))

        # Carrega todos os projetos
        self.fields['projetos'].queryset = qs.exclude(id__in=m_initial)

        # Seleciona os projetos que já foram salvos
        self.fields['projetos'].initial = m_initial

    def clean(self):
        selecionados_ids = list()
        for projeto in self.cleaned_data['projetos']:
            pass
            selecionados_ids.append(projeto.pk)
        if len(selecionados_ids) == 0:
            raise forms.ValidationError('Selecione pelo menos um projeto estratégico.')
        return self.cleaned_data

    @transaction.atomic()
    def save(self):
        # lista de novos projetos
        selecionados_ids = list()
        # itera sobre os projetos selecionados
        for projeto in self.cleaned_data['projetos']:
            pass
            selecionados_ids.append(projeto.pk)
            # se o projeto corrente selecionado ainda não foi salvo, salva.
            if not ProjetoPlanoAtividade.objects.filter(plano_atividade=self.plano, projeto=projeto).exists():
                ProjetoPlanoAtividade.objects.create(plano_atividade=self.plano, projeto=projeto)


class AssociarEtapasProjetoPlanoAtividadeForm(forms.FormPlus):
    SUBMIT_LABEL = 'Adicionar apenas selecionados'

    # etapas selecionados
    etapas = forms.MultipleModelChoiceField(queryset=EtapaProjeto.objects, label='', required=False, widget=RenderableSelectMultiple('widgets/etapas_widget.html'))

    def __init__(self, *args, **kwargs):
        self.projeto_plano_atividade = kwargs.pop('projeto_plano_atividade')
        super().__init__(*args, **kwargs)

        # recupera todas as etapas do projeto do plano de atividade
        m_initial = EtapaProjetoPlanoAtividade.objects.filter(projeto_plano_atividade=self.projeto_plano_atividade).values_list('etapa__pk', flat=True)
        qs = EtapaProjeto.objects.filter(projeto=self.projeto_plano_atividade.projeto).order_by('id')

        # Carrega todas as etapas
        self.fields['etapas'].queryset = qs.exclude(id__in=m_initial)

        # Seleciona os projetos que já foram salvos
        self.fields['etapas'].initial = m_initial

    @transaction.atomic()
    def save(self):
        # lista de novas etapas
        selecionadas_ids = list()
        # itera sobre as etapas selecionadas
        for etapa in self.cleaned_data['etapas']:
            pass
            selecionadas_ids.append(etapa.pk)
            # se a etapa corrente selecionada ainda não foi salva, salva.
            if not EtapaProjetoPlanoAtividade.objects.filter(projeto_plano_atividade=self.projeto_plano_atividade, etapa=etapa).exists():
                EtapaProjetoPlanoAtividade.objects.create(projeto_plano_atividade=self.projeto_plano_atividade, etapa=etapa)


class AssociarOrigemRecursoProjetoPlanoAtividadeForm(forms.FormPlus):
    SUBMIT_LABEL = 'Adicionar apenas selecionados'

    # Origens de recursos selecionados
    origens_recursos = forms.MultipleModelChoiceField(
        queryset=OrigemRecurso.objects, label='', required=False, widget=RenderableSelectMultiple('widgets/origens_recursos_widget.html')
    )

    def __init__(self, *args, **kwargs):
        self.projeto_plano_atividade = kwargs.pop('projeto_plano_atividade')
        super().__init__(*args, **kwargs)

        # recupera todas as origens de recurso do projeto do plano de atividade
        m_initial = OrigemRecursoProjeto.objects.filter(projeto_plano_atividade=self.projeto_plano_atividade).values_list('origem_recurso__pk', flat=True)

        qs = OrigemRecurso.objects.filter(plano_atividade=self.projeto_plano_atividade.plano_atividade)

        # Carrega todas as origens de recursos
        self.fields['origens_recursos'].queryset = qs

        # Seleciona as origens que já foram salvas
        self.fields['origens_recursos'].initial = m_initial

    @transaction.atomic()
    def save(self):
        # lista de novas origens
        selecionadas_ids = list()
        # itera sobre as origens selecionadas
        for origem_recurso in self.cleaned_data['origens_recursos']:
            pass
            selecionadas_ids.append(origem_recurso.pk)
            # se a origem de recurso corrente selecionada ainda não foi salva, salva.
            if not OrigemRecursoProjeto.objects.filter(projeto_plano_atividade=self.projeto_plano_atividade, origem_recurso=origem_recurso).exists():
                OrigemRecursoProjeto.objects.create(projeto_plano_atividade=self.projeto_plano_atividade, origem_recurso=origem_recurso)

        # Exclui todas as etapas que não estão selecionadas
        for origem_recurso_projeto in OrigemRecursoProjeto.objects.filter(projeto_plano_atividade=self.projeto_plano_atividade).exclude(origem_recurso__pk__in=selecionadas_ids):
            origem_recurso_projeto.delete()


class OrigemRecursoEspecialForm(forms.Form):
    origens_recurso = forms.ModelChoiceField(queryset=OrigemRecursoProjetoEtapa.objects, label='Origem da etapa', required=True)

    def __init__(self, *args, **kwargs):
        self.etapa_projeto_plano_atividade = kwargs.pop('etapa_projeto_plano_atividade')
        super().__init__(*args, **kwargs)

        qs = OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade=self.etapa_projeto_plano_atividade)
        self.fields['origens_recurso'].queryset = qs

    def save(self):
        origem_recurso_etapa = self.cleaned_data['origens_recurso']
        origem_recurso_etapa = OrigemRecursoProjetoEtapa.objects.filter(
            origem_recurso_projeto=origem_recurso_etapa.origem_recurso_projeto, etapa_projeto_plano_atividade=origem_recurso_etapa.etapa_projeto_plano_atividade
        )[0]
        origem_recurso_etapa.tipo_especial = True
        origem_recurso_etapa.save()
        origem_recurso_etapa.etapa_projeto_plano_atividade.tipo_especial = True
        origem_recurso_etapa.etapa_projeto_plano_atividade.save()


class AssociarOrigemRecursoEtapaProjetoPlanoAtividadeForm(forms.FormPlus):
    SUBMIT_LABEL = 'Adicionar apenas selecionados'

    # Origens de recursos  selecionados
    origens_recursos_projetos = forms.MultipleModelChoiceField(
        queryset=OrigemRecursoProjeto.objects, label='', required=False, widget=RenderableSelectMultiple('widgets/origens_recursos_projetos_widget.html')
    )

    def __init__(self, *args, **kwargs):
        self.etapa_projeto_plano_atividade = kwargs.pop('etapa_projeto_plano_atividade')
        super().__init__(*args, **kwargs)

        # recupera todas as origens de recurso da etapa do projeto do plano de atividade
        m_initial = OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade=self.etapa_projeto_plano_atividade).values_list('origem_recurso_projeto__pk', flat=True)

        # Mostra somente as origens de recursos do projeto que podem ser selecionadas na etapa
        qs = OrigemRecursoProjeto.objects.filter(projeto_plano_atividade_id=self.etapa_projeto_plano_atividade.projeto_plano_atividade)
        self.fields['origens_recursos_projetos'].queryset = qs

        # Seleciona as origens que já foram salvas
        self.fields['origens_recursos_projetos'].initial = m_initial

    @transaction.atomic()
    def save(self):
        # lista de novas origens
        selecionadas_ids = list()
        # itera sobre as origens selecionadas
        for origem_recurso in self.cleaned_data['origens_recursos_projetos']:
            pass
            selecionadas_ids.append(origem_recurso.pk)
            # se a origem de recurso corrente selecionada ainda não foi salva, salva.
            if not OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade=self.etapa_projeto_plano_atividade, origem_recurso_projeto=origem_recurso).exists():
                OrigemRecursoProjetoEtapa.objects.create(etapa_projeto_plano_atividade=self.etapa_projeto_plano_atividade, origem_recurso_projeto=origem_recurso)

        # Exclui todas as etapas que não estão selecionadas
        for origem_recurso_projeto in OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade=self.etapa_projeto_plano_atividade).exclude(
            origem_recurso_projeto__pk__in=selecionadas_ids
        ):
            origem_recurso_projeto.delete()


class AssociarUnidadeGestoraEtapaProjetoPlanoAtividadeForm(forms.FormPlus):
    SUBMIT_LABEL = 'Adicionar apenas selecionados'

    # Unidades gestoras  selecionados
    unidades_gestoras_campi = forms.MultipleModelChoiceField(
        queryset=UnidadeGestora.objects, label='', required=False, widget=RenderableSelectMultiple('widgets/unidades_gestoras_etapa_widget.html')
    )
    unidades_gestoras_sistemicas = forms.MultipleModelChoiceField(
        queryset=UnidadeGestora.objects, label='', required=False, widget=RenderableSelectMultiple('widgets/unidades_gestoras_sistemicas_etapa_widget.html')
    )

    def __init__(self, *args, **kwargs):
        self.etapa_projeto_plano_atividade = kwargs.pop('etapa_projeto_plano_atividade')
        super().__init__(*args, **kwargs)

        # recupera todas as Unidades gestoras da etapa do projeto do plano de atividade
        m_initial = UnidadeGestoraEtapa.objects.filter(etapa_projeto_plano_atividade=self.etapa_projeto_plano_atividade).values_list('unidade_gestora__pk', flat=True)

        # Mostra as Unidades disponíveis a serem selecionadas
        qs = UnidadeGestora.objects.filter(pdi=self.etapa_projeto_plano_atividade.projeto_plano_atividade.plano_atividade.pdi)
        self.fields['unidades_gestoras_campi'].queryset = qs.filter(tipo=UnidadeGestora.TIPO_CAMPUS)

        self.fields['unidades_gestoras_sistemicas'].queryset = qs.filter(tipo__in=(UnidadeGestora.TIPO_PRO_REITORIA, UnidadeGestora.TIPO_DIRETORIA))
        # Seleciona as Unidades gestoras que já foram salvas
        self.fields['unidades_gestoras_campi'].initial = m_initial.filter(unidade_gestora__tipo=UnidadeGestora.TIPO_CAMPUS)
        self.fields['unidades_gestoras_sistemicas'].initial = m_initial.filter(unidade_gestora__tipo__in=(UnidadeGestora.TIPO_PRO_REITORIA, UnidadeGestora.TIPO_DIRETORIA))

    @transaction.atomic()
    def save(self):
        # lista de novas UG
        selecionadas_ids = list()
        # itera sobre as UG
        unidades_gestoras_form = self.cleaned_data['unidades_gestoras_campi'] | self.cleaned_data['unidades_gestoras_sistemicas']
        for unidade_gestora in unidades_gestoras_form:
            pass
            selecionadas_ids.append(unidade_gestora.pk)
            # se a UG corrente selecionada ainda não foi salva, salva.
            if not UnidadeGestoraEtapa.objects.filter(etapa_projeto_plano_atividade=self.etapa_projeto_plano_atividade, unidade_gestora=unidade_gestora).exists():
                UnidadeGestoraEtapa.objects.create(etapa_projeto_plano_atividade=self.etapa_projeto_plano_atividade, unidade_gestora=unidade_gestora)

        # Exclui todas as etapas que não estão selecionadas
        for unidade_gestora_etapa in UnidadeGestoraEtapa.objects.filter(etapa_projeto_plano_atividade=self.etapa_projeto_plano_atividade).exclude(
            unidade_gestora__pk__in=selecionadas_ids
        ):
            unidade_gestora_etapa.delete()


class OrigemRecursoProjetoForm(forms.ModelFormPlus):
    valor = forms.DecimalFieldPlus("Valor")

    class Meta:
        model = OrigemRecursoProjeto
        fields = ('valor',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean(self):
        valor = self.cleaned_data.get('valor')
        if valor is None:
            raise ValidationError('Campo obrigatório.')
        valor_executado = OrigemRecursoProjeto.objects.filter(
            projeto_plano_atividade__plano_atividade=self.instance.projeto_plano_atividade.plano_atividade, origem_recurso=self.instance.origem_recurso
        )
        valor_executado_atual = (valor_executado.aggregate(total=Sum('valor'))['total'] or 0) - (self.instance.valor or 0)

        saldo_disponivel = self.instance.origem_recurso.valor_total() - valor_executado_atual
        saldo = self.instance.origem_recurso.valor_total() - (valor_executado_atual + self.cleaned_data['valor'])

        if saldo < 0:
            raise forms.ValidationError('Este valor ultrapassou o valor disponível para esta Origem de Recurso. Saldo Disponível: %s' % format_money(saldo_disponivel))

        return self.cleaned_data


class GerenciarCompartilhamentoGEstorUAForm(forms.FormPlus):
    qs_servidores = PessoaFisica.objects.filter(eh_servidor=True)
    pessoas_com_poder_de_chefe = forms.MultipleModelChoiceFieldPlus(label='Servidores com poder de Gestor', queryset=qs_servidores, required=False)

    fieldsets = (('Servidores com poder de Gestor Planejamento Estratégico', {'fields': ('pessoas_com_poder_de_chefe',)}),)

    def __init__(self, *args, **kwargs):
        self.setor_escolhido = kwargs.pop('setor_escolhido', None)
        super().__init__(*args, **kwargs)
        self.fields['pessoas_com_poder_de_chefe'].label = 'Servidores com poder de gestor no(a) {}'.format(self.setor_escolhido)
        self.fields['pessoas_com_poder_de_chefe'].queryset = PessoaFisica.objects.filter(
            id__in=Servidor.objects.filter(setor__in=self.setor_escolhido.descendentes).values_list('id', flat=True)
        )


class ValoresOrigemRecursoEtapaForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.origemrecurso = kwargs.pop('origemrecurso', None)
        super().__init__(*args, **kwargs)
        nome_campos = ''
        for i in OrigemRecursoProjetoEtapa.objects.filter(origem_recurso_projeto=self.origemrecurso).order_by('etapa_projeto_plano_atividade'):
            label = '{} - {}'.format(i.etapa_projeto_plano_atividade.etapa.codigo, i.etapa_projeto_plano_atividade.etapa)
            inicial = i.valor
            self.fields["{}".format(i.id)] = forms.DecimalFieldPlus(label=label, required=True, initial=inicial)
            nome_campos = nome_campos + '{}, '.format(i.id)

    def clean(self):
        valor_origem_projeto = self.origemrecurso.valor or 0
        total = Decimal(0)
        for i, valor in self.cleaned_data.items():
            total += valor

        saldo = valor_origem_projeto - total
        if saldo < 0:
            self.add_error('', 'Valor distribuído maior que o valor disponível desta Origem de Recurso.  Valor ultrapassado:  R$  %s' % format_money(saldo))

        if saldo > 0:
            self.add_error('', 'Você ainda precisa distribuir nas etapas para esta Origem de Recurso R$ %s' % format_money(saldo))


class ValoresEtapaUnidadesForm(forms.Form):
    def __init__(self, *args, **kwargs):
        self.origemrecurso = kwargs.pop('origemrecurso', None)
        self.etapa = kwargs.pop('etapa', None)
        super().__init__(*args, **kwargs)
        nome_campos = ''
        for i in UnidadeGestoraEtapa.objects.filter(etapa_projeto_plano_atividade=self.etapa):
            label = '{}'.format(i.unidade_gestora.setor_equivalente.sigla)
            inicial = Decimal(0)
            if UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa=self.origemrecurso, unidade_gestora=i).exists():
                inicial = UnidadeOrigemEtapa.objects.filter(origem_recurso_etapa=self.origemrecurso, unidade_gestora=i)[0].valor
            self.fields["{}".format(i.id)] = forms.DecimalFieldPlus(label=label, required=True, initial=inicial)
            nome_campos = nome_campos + '{}, '.format(i.id)

    def clean(self):
        valor_origem_etapa = (
            OrigemRecursoProjetoEtapa.objects.filter(origem_recurso_projeto=self.origemrecurso.origem_recurso_projeto.id, etapa_projeto_plano_atividade=self.etapa)[0].valor or 0
        )

        total = Decimal(0)
        for i, valor in self.cleaned_data.items():
            total += valor

        saldo = valor_origem_etapa - total
        if saldo < 0:
            self.add_error('', 'Valor distribuído maior que o valor disponível desta Origem de Recurso.  Valor ultrapassado:  R$ %s' % format_money(saldo))

        if saldo > 0:
            self.add_error('', 'Você ainda precisa distribuir nas Unidades administrativas para esta Origem de Recurso R$ %s' % format_money(saldo))


class ValoresEtapaAtividadesForm(forms.Form):
    fieldsets = ()

    def __init__(self, *args, **kwargs):
        self.origemrecurso = kwargs.pop('origemrecurso', None)
        self.etapa = kwargs.pop('etapa', None)
        super().__init__(*args, **kwargs)
        nome_campos = ''
        user = tl.get_user()
        for i in AtividadeEtapa.objects.filter(
            etapa_projeto_plano_atividade=self.etapa, origem_recurso_etapa=self.origemrecurso, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=user)
        ):
            label = 'Valor a compatibilizar'
            inicial = Decimal(0)
            inicial_reserva_tecnica = Decimal(0)
            origem_especial = None
            if OrigemRecursoProjetoEtapa.objects.filter(
                etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=self.etapa.projeto_plano_atividade.plano_atividade, tipo_especial=True
            ).exists():
                origem_especial = OrigemRecursoProjetoEtapa.objects.filter(
                    etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=self.etapa.projeto_plano_atividade.plano_atividade, tipo_especial=True
                )[0]
            if AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade=self.etapa, origem_recurso_etapa=self.origemrecurso, pk=i.pk).exists():
                inicial = AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade=self.etapa, origem_recurso_etapa=self.origemrecurso, pk=i.pk)[0].valor_rateio or Decimal(0)
                inicial_reserva_tecnica = AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade=self.etapa, origem_recurso_etapa=self.origemrecurso, pk=i.pk)[
                    0
                ].valor_reserva_tecnica or Decimal(0)
            if i.valor is None:
                i.valor = Decimal(0)
            self.fields["valor_proposto_{}".format(i.id)] = forms.DecimalFieldPlus(label='Valor proposto', required=True, initial=i.valor)
            self.fields["valor_proposto_{}".format(i.id)].widget.attrs['readonly'] = 'readonly'

            self.fields["{}".format(i.id)] = forms.DecimalFieldPlus(label=label, required=True, initial=inicial)

            self.fields["reserva_tecnica_{}".format(i.id)] = forms.DecimalFieldPlus(label='Valor a complementar', required=True, initial=inicial_reserva_tecnica)
            if not origem_especial:
                self.fields["reserva_tecnica_{}".format(i.id)].widget.attrs['readonly'] = 'readonly'
            elif origem_especial.origem_recurso_projeto.origem_recurso.gnd != self.origemrecurso.origem_recurso_projeto.origem_recurso.gnd:
                self.fields["reserva_tecnica_{}".format(i.id)].widget.attrs['readonly'] = 'readonly'
            elif not UnidadeOrigemEtapa.objects.filter(
                origem_recurso_etapa=origem_especial, unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=tl.get_user())
            ).exists():
                self.fields["reserva_tecnica_{}".format(i.id)].widget.attrs['readonly'] = 'readonly'
            else:
                if self.etapa.eh_especial() and self.origemrecurso.tipo_especial:
                    self.fields["reserva_tecnica_{}".format(i.id)].widget.attrs['readonly'] = 'readonly'
            nome_campos = nome_campos + '{},'.format(i.descricao)
            self.fieldsets = self.fieldsets + ((i.nome, {'fields': (('valor_proposto_{}'.format(i.id), '{}'.format(i.id), 'reserva_tecnica_{}'.format(i.id)),)}),)

    def clean(self):
        valor_origem_unidade = (
            UnidadeOrigemEtapa.objects.filter(
                origem_recurso_etapa=self.origemrecurso, unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=tl.get_user())
            )[0].valor
            or 0
        )

        valor_especial_unidade = 0
        if OrigemRecursoProjetoEtapa.objects.filter(
            etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=self.etapa.projeto_plano_atividade.plano_atividade, tipo_especial=True
        ).exists():
            or_especial = OrigemRecursoProjetoEtapa.objects.filter(
                etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=self.etapa.projeto_plano_atividade.plano_atividade, tipo_especial=True
            )[0]
            if UnidadeOrigemEtapa.objects.filter(
                origem_recurso_etapa=or_especial, unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=tl.get_user())
            ).exists():
                valor_especial_unidade = (
                    UnidadeOrigemEtapa.objects.filter(
                        origem_recurso_etapa=or_especial, unidade_gestora__unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=tl.get_user())
                    )[0].valor
                    or 0
                )
        user = tl.get_user()
        total_valor = 0
        total_reserva_tecnica = 0
        valor_rateado_ativ = 0
        total_atividades_reserva = 0
        if OrigemRecursoProjetoEtapa.objects.filter(
            etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=self.etapa.projeto_plano_atividade.plano_atividade, tipo_especial=True
        ).exists():
            atividades = AtividadeEtapa.objects.filter(origem_recurso_etapa=or_especial, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=user))
            valor_rateado_ativ = atividades.aggregate(total=Sum('valor_rateio'))['total'] or 0
            atividades_reserva = AtividadeEtapa.objects.filter(etapa_projeto_plano_atividade__projeto_plano_atividade__plano_atividade=self.etapa.projeto_plano_atividade.plano_atividade,
                                                               valor_reserva_tecnica__isnull=False, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=user)
                                                               ).exclude(origem_recurso_etapa=self.origemrecurso)
            total_atividades_reserva = atividades_reserva.aggregate(total=Sum('valor_reserva_tecnica'))['total'] or 0
        for i in AtividadeEtapa.objects.filter(
            etapa_projeto_plano_atividade=self.etapa, origem_recurso_etapa=self.origemrecurso, unidade_gestora__setor_equivalente=get_setor_unidade_gestora(user=user)
        ):
            try:
                total_valor += self.cleaned_data["{}".format(i.id)]
                total_reserva_tecnica += self.cleaned_data["reserva_tecnica_{}".format(i.id)]
            except KeyError:
                pass

        saldo = valor_origem_unidade - total_valor

        if self.origemrecurso.tipo_especial:
            unidade = UnidadeGestora.objects.filter(setor_equivalente=get_setor_unidade_gestora(user=user))[0]
            if unidade.recurso_total:
                valor_percentual_unidade = valor_origem_unidade
            else:
                valor_percentual_unidade = (valor_origem_unidade * self.etapa.projeto_plano_atividade.plano_atividade.percentual_reserva_tecnica) / 100
            saldo = valor_especial_unidade - (total_reserva_tecnica + total_atividades_reserva)
            if saldo > valor_percentual_unidade:
                saldo = valor_percentual_unidade - total_valor
            else:
                saldo = saldo - total_valor

        if saldo < 0:
            self.add_error('', 'O somatório dos valores a compatibilizar ultrapassa o valor disponível nesta OR em R$ %s' % format_money(saldo))

        if not self.etapa.eh_especial() and saldo > 0:
            self.add_error('', 'Você ainda precisa distribuir nas atividades para esta Origem de Recurso R$ %s' % format_money(saldo))
        if not self.etapa.eh_especial():
            valor_especial_unidade = valor_especial_unidade - valor_rateado_ativ
            saldo_especial = valor_especial_unidade - (total_reserva_tecnica + total_atividades_reserva)
            if saldo_especial < 0:
                self.add_error('', 'O somatório dos valores a complementar ultrapassa o valor disponível em R$ %s' % format_money(saldo_especial))


class PreenchimentoVariavelForm(ModelFormPlus):
    class Meta:
        model = PeriodoPreenchimentoVariavel
        fields = ('pdi', 'ano', 'trimestre', 'data_inicio', 'data_termino')

    def clean(self):
        cleaned_data = super().clean()
        if not self.errors:
            data_inicio = cleaned_data.get("data_inicio")
            data_termino = cleaned_data.get("data_termino")
            if data_termino < data_inicio:
                self.add_error('data_termino', 'Data de término deve ser maior ou igual à Data de início.')
            periodos = PeriodoPreenchimentoVariavel.objects.filter(pdi=self.cleaned_data['pdi'])
            if self.instance.pk:
                periodos = periodos.exclude(pk=self.instance.pk)
            if periodos.exists():
                for periodo in periodos:
                    if (
                        periodo.data_inicio <= data_inicio <= periodo.data_termino
                        or periodo.data_inicio <= data_termino <= periodo.data_termino
                    ):
                        raise forms.ValidationError('O Periodo selecionado engloba parte de outro período já cadastrado. Escolha outras datas.')
        return self.cleaned_data


def filtro_indicadores_formfactory(pdi, sigla_instituicao):

    ano_choices = [[ano, ano] for ano in range(pdi.ano_inicial_pdi.ano, pdi.ano_final_pdi.ano + 1)]
    ano_choices.append(['Selecione um ano', 'Selecione um ano'])

    class IndicadoresFiltroForm(forms.FormPlus):
        METHOD = 'GET'
        ano = forms.ChoiceField(label='Ano', choices=ano_choices, required=False, initial='Selecione um ano')
        campus = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False, empty_label=sigla_instituicao)
        indicador = forms.ModelChoiceField(label='Indicador', queryset=PDIIndicador.objects.filter(pdi=pdi).order_by('indicador__sigla'), required=False)

        def __init__(self, *args, **kwargs):
            pdi = kwargs.pop('pdi')
            super().__init__(*args, **kwargs)

            choices = list()
            for ano in range(pdi.ano_inicial_pdi.ano, pdi.ano_final_pdi.ano):
                choices.append((ano, ano))

            self.base_fields['ano'].choices = choices

    return IndicadoresFiltroForm


class RelatorioDemonstrativoForm(forms.FormPlus):
    unidade_gestora = forms.ModelChoiceField(label='Unid. Administrativa', queryset=UnidadeGestora.objects.all(), widget=forms.Select(attrs={'onchange': 'submeter_form(this)'}))


class RelatorioProjetoForm(forms.FormPlus):
    unidade_gestora = forms.ModelChoiceField(label='Unid. Administrativa', queryset=UnidadeGestora.objects.all().order_by('tipo', 'setor_equivalente__sigla'), required=False)
    origem_recurso_etapa = forms.ModelChoiceFieldPlus2(label='Origem de recurso', help_text='Origem de recurso da etapa', queryset=OrigemRecursoProjetoEtapa.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        projeto = kwargs.pop('projeto')
        super().__init__(*args, **kwargs)
        qs = OrigemRecursoProjetoEtapa.objects.filter(etapa_projeto_plano_atividade__projeto_plano_atividade=projeto).distinct('origem_recurso_projeto')
        self.fields['origem_recurso_etapa'].queryset = qs


class RelatorioPlanoatividadeForm(forms.FormPlus):
    unidade_gestora = forms.ModelChoiceField(label='Unid. Administrativa', queryset=UnidadeGestora.objects.all().order_by('tipo', 'setor_equivalente__sigla'), required=False)
    projeto = forms.ModelChoiceField(label='Projeto Estratégico', queryset=ProjetoPlanoAtividade.objects.all().order_by('projeto__codigo'), required=False)
    etapa = forms.ModelChoiceField(label='Etapa', queryset=EtapaProjetoPlanoAtividade.objects.all().order_by('projeto_plano_atividade__projeto__codigo'), required=False)
    origem_recurso = forms.ModelChoiceField(label='Origem de recurso', queryset=OrigemRecurso.objects.all().order_by('acao_financeira__acao__codigo_acao'), required=False)

    def __init__(self, *args, **kwargs):
        plano_atividade = kwargs.pop('plano_atividade')
        super().__init__(*args, **kwargs)
        qs = ProjetoPlanoAtividade.objects.filter(plano_atividade=plano_atividade).order_by('projeto__codigo')
        etapa_qs = EtapaProjetoPlanoAtividade.objects.filter(projeto_plano_atividade__plano_atividade=plano_atividade).order_by('projeto_plano_atividade__projeto__codigo')
        or_qs = OrigemRecurso.objects.filter(plano_atividade=plano_atividade).order_by('acao_financeira__acao__codigo_acao')
        self.fields['projeto'].queryset = qs
        self.fields['etapa'].queryset = etapa_qs
        self.fields['origem_recurso'].queryset = or_qs

        unidade_gestora = UnidadeGestora.objects.filter(setor_equivalente=get_setor_unidade_gestora(user=self.request.user)).first()
        if unidade_gestora:
            self.fields['unidade_gestora'].initial = unidade_gestora.id


def filtro_linhadotempo_formfactory(pdi, sigla_instituicao):
    class LinhaTempoFiltroForm(forms.FormPlus):
        METHOD = 'GET'
        campus = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.uo(), required=False, empty_label=sigla_instituicao)
        indicador = forms.ModelChoiceField(label='Indicador', queryset=PDIIndicador.objects.all().order_by('indicador__sigla'), required=False)

        def __init__(self, *args, **kwargs):
            pdi = kwargs.pop('pdi')
            super().__init__(*args, **kwargs)
            self.fields['indicador'].queryset = PDIIndicador.objects.filter(pdi=pdi).order_by('indicador__sigla')
    return LinhaTempoFiltroForm


class RelatorioRankingForm(forms.FormPlus):
    campus = forms.ModelChoiceField(label='Unid. Administrativa', required=False, queryset=UnidadeOrganizacional.objects.uo().all(), widget=forms.Select(attrs={'onchange': 'submeter_form(this)'}))
    tematica = forms.ModelChoiceField(label='Temática', required=False, queryset=TematicaVariavel.objects.all(), widget=forms.Select(attrs={'onchange': 'submeter_form(this)'}))
