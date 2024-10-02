# -*- coding: utf-8 -*-
from comum.models import Municipio, Vinculo
from comum.utils import get_uo, get_sigla_reitoria
from convenios.models import TipoConvenio, SituacaoConvenio, Aditivo, AnexoConvenio, ProfissionalLiberal, ConselhoProfissional
from djtools import forms
from djtools.forms.widgets import AutocompleteWidget
from djtools.templatetags.filters import in_group
from rh.models import UnidadeOrganizacional, PessoaJuridica


class ConvenioForm(forms.ModelFormPlus):
    vinculos_conveniadas = forms.MultipleModelChoiceFieldPlus(label='Conveniadas', required=False, queryset=Vinculo.objects)
    interveniente = forms.ModelChoiceField(
        queryset=PessoaJuridica.objects, widget=AutocompleteWidget(search_fields=PessoaJuridica.SEARCH_FIELDS), label='Interveniente', required=False
    )
    situacao = forms.ModelChoiceField(queryset=SituacaoConvenio.objects, widget=forms.Select, required=True, empty_label=None, label='Situação')
    tipo = forms.ModelChoiceField(queryset=TipoConvenio.objects, widget=forms.Select, required=True, empty_label=None)
    uo = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.suap(), widget=forms.Select, required=True, empty_label=None, label='Campus')
    data_inicio = forms.DateFieldPlus(label='Data de Início')
    data_fim = forms.DateFieldPlus(label='Data de Término')

    def __init__(self, *args, **kwargs):
        super(ConvenioForm, self).__init__(*args, **kwargs)
        self.fields['vinculos_conveniadas'].queryset = Vinculo.objects.filter(pessoa__pessoajuridica__isnull=False) | Vinculo.objects.filter(
            id__in=ProfissionalLiberal.objects.values_list('vinculo_pessoa', flat=True)
        )


class AditivoForm(forms.ModelFormPlus):
    data = forms.DateFieldPlus(label='Data de Realização', required=True, help_text='Data em que o aditivo foi publicado')
    data_inicio = forms.DateFieldPlus(label='Data Inicial', required=False, help_text='Data inicial da nova vigência caso se trate de um aditivo de prazo')
    data_fim = forms.DateFieldPlus(label='Data Final', required=False, help_text='Data final da nova vigência caso se trate de um aditivo de prazo')
    objeto = forms.CharField(label="Objeto", widget=forms.Textarea)

    class Meta:
        model = Aditivo
        exclude = ['convenio', 'ordem']


class AnexoForm(forms.ModelFormPlus):
    class Meta:
        model = AnexoConvenio
        exclude = ('arquivo', 'convenio')


class UploadArquivoForm(forms.FormPlus):
    arquivo = forms.FileFieldPlus()


class BuscaConvenioForm(forms.FormPlus):
    numero = forms.CharField(required=False, label='Número')
    conveniada = forms.ModelChoiceField(queryset=Vinculo.objects, widget=AutocompleteWidget(search_fields=Vinculo.SEARCH_FIELDS), label='Conveniada', required=False)
    interveniente = forms.ModelChoiceField(
        queryset=PessoaJuridica.objects, widget=AutocompleteWidget(search_fields=PessoaJuridica.SEARCH_FIELDS), label='Interveniente', required=False
    )
    situacao = forms.ModelChoiceField(queryset=SituacaoConvenio.objects, widget=forms.Select, required=False, label='Situação')
    tipo = forms.ModelChoiceField(queryset=TipoConvenio.objects, widget=forms.Select, required=False)
    uo = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.suap(), widget=forms.Select, required=False, label='Campus')
    data_inicio = forms.DateFieldPlus(label='Data de Início', required=False)
    data_fim = forms.DateFieldPlus(label='Data de Término', required=False)

    def __init__(self, *args, **kwargs):
        super(BuscaConvenioForm, self).__init__(*args, **kwargs)
        if in_group(self.request.user, ['Operador de Convênios']):
            sigla_reitoria = get_sigla_reitoria()
            if UnidadeOrganizacional.objects.suap().filter(sigla=sigla_reitoria).exists():
                reitoria = UnidadeOrganizacional.objects.suap().get(sigla=sigla_reitoria)
                self.fields['uo'].queryset = UnidadeOrganizacional.objects.suap().filter(id__in=[get_uo(self.request.user).id, reitoria.id])
            else:
                self.fields['uo'].queryset = UnidadeOrganizacional.objects.suap().filter(id=get_uo(self.request.user).id)
        self.fields['conveniada'].queryset = Vinculo.objects.filter(pessoa__pessoajuridica__isnull=False) | Vinculo.objects.filter(
            id__in=ProfissionalLiberal.objects.values_list('vinculo_pessoa', flat=True)
        )


class CampusForm(forms.Form):
    uo = forms.ModelChoiceField(label='Campus', queryset=UnidadeOrganizacional.objects.suap(), empty_label='Todos', required=False)

    def __init__(self, *args, **kwargs):
        self.uos = kwargs.pop('uos', None)
        super(CampusForm, self).__init__(*args, **kwargs)
        self.fields['uo'].queryset = UnidadeOrganizacional.objects.suap().filter(id__in=self.uos.values_list('id', flat=True))


class ProfissionalLiberalForm(forms.ModelFormPlus):
    nome = forms.CharFieldPlus(label='Nome')
    cpf = forms.BrCpfField(label='CPF')
    municipio = forms.ModelChoiceFieldPlus(queryset=Municipio.objects, label='Município')
    sexo = forms.ChoiceField(label='Sexo', choices=[['M', 'Masculino'], ['F', 'Feminino']])
    nascimento_data = forms.DateFieldPlus(label='Data de Nascimento', required=False)
    cep = forms.BrCepField(label='CEP')
    telefone = forms.BrTelefoneField(label='Telefone')

    class Meta:
        model = ProfissionalLiberal
        fields = ('nome', 'cpf', 'sexo', 'nascimento_data', 'numero_registro', 'conselho', 'telefone', 'email', 'cep', 'logradouro', 'numero', 'complemento', 'bairro')

    class Media:
        js = ('/static/convenios/js/profissionaliberalform.js',)

    def __init__(self, *args, **kwargs):
        super(ProfissionalLiberalForm, self).__init__(*args, **kwargs)
        self.fields['conselho'].queryset = ConselhoProfissional.objects.filter(ativo=True)
        self.fields['complemento'].required = False
        if self.instance.pk:
            self.fields['nome'].initial = self.instance.vinculo_pessoa.pessoa.nome
            self.fields['cpf'].initial = self.instance.vinculo_pessoa.pessoa.pessoafisica.cpf
            self.fields['sexo'].initial = self.instance.vinculo_pessoa.pessoa.pessoafisica.sexo
            self.fields['nascimento_data'].initial = self.instance.vinculo_pessoa.pessoa.pessoafisica.nascimento_data

    def clean(self):
        cleaned_data = super(ProfissionalLiberalForm, self).clean()
        erro = False
        if self.cleaned_data.get('cpf'):
            if self.instance.pk and ProfissionalLiberal.objects.exclude(id=self.instance.pk).filter(vinculo_pessoa__pessoa__pessoafisica__cpf=self.cleaned_data.get('cpf')).exists():
                erro = True
            elif not self.instance.pk and ProfissionalLiberal.objects.filter(vinculo_pessoa__pessoa__pessoafisica__cpf=self.cleaned_data.get('cpf')).exists():
                erro = True
        if erro:
            self.add_error('cpf', 'Já existe um profissional liberal cadastrado com este CPF.')

        return cleaned_data
