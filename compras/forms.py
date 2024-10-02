# -*- coding: utf-8 -*-

from compras.models import ProcessoCompraCampusMaterial, ProcessoCompra, Calendario, Evento, TipoEvento, Fase, Processo
from comum.models import Ano
from djtools import forms
from djtools.forms.utils import DtModelForm
from djtools.forms.widgets import AutocompleteWidget, FilteredSelectMultiplePlus
from materiais.models import Material, MaterialTag
from rh.models import UnidadeOrganizacional


def ProcessoCompraCampusMaterialFormFactory(processo_compra_campus):
    tags = processo_compra_campus.processo_compra.tags.all()

    class FormClass(DtModelForm):
        campus = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.uo().all(), label='Campus', required=True)

        class Meta:
            model = ProcessoCompraCampusMaterial
            exclude = ['material_tag']

        hidden_fields_ = ['processo_compra_campus']
        material = forms.ModelChoiceField(
            queryset=Material.objects.filter(tags__in=tags),
            widget=AutocompleteWidget(qs_filter='tags__in={}'.format(','.join([str(i) for i in tags.all().values_list('id', flat=1)])), search_fields=Material.SEARCH_FIELDS),
        )

    return FormClass


def ProcessoCompraFormFactory(instance=None):
    class ProcessoCompraForm(forms.FormPlus):
        descricao = forms.CharField(label='Descrição', required=True, max_length=25, initial=(instance and instance.descricao) or None)
        observacao = forms.CharField(label='Observação', required=False, widget=forms.Textarea, initial=(instance and instance.observacao) or None)
        data_inicio = forms.DateTimeField(initial=(instance and instance.data_inicio) or None, label='Data início')
        data_fim = forms.DateTimeField(initial=(instance and instance.data_fim) or None, label='Data fim')
        update_data = forms.BooleanField(label='Atualizar todos os processos de compra dos campi com esta data', required=False, initial=False)

    return ProcessoCompraForm


class ProcessoCompraForm(forms.ModelFormPlus):
    aplicar_todos = forms.BooleanField(label="Aplicar a todos os campi", help_text="Caso marcado, inclui todos os campos não informados.", required=False)
    tags = forms.MultipleModelChoiceFieldPlus(label='Tags', queryset=MaterialTag.objects, widget=FilteredSelectMultiplePlus('', True), required=False)

    class Meta:
        model = ProcessoCompra
        exclude = ()


class EventoForm(forms.ModelFormPlus):
    calendario = forms.ModelChoiceField(label='Calendário', queryset=Calendario.objects.filter(ativo=True))
    tipo_evento = forms.ChainedModelChoiceField(
        queryset=TipoEvento.objects.filter(ativo=True),
        label='Tipo de Evento',
        obj_label='descricao',
        empty_label='Selecione o Calendário',
        form_filters=[('calendario', 'calendario_id')],
    )

    class Meta:
        model = Evento
        fields = ('calendario', 'tipo_evento', 'data_inicio', 'data_fim', 'ativo', )

    def __init__(self, *args, **kwargs):
        super(EventoForm, self).__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['calendario'].initial = self.instance.tipo_evento.calendario.id

    def cleaned_data(self):
        cleaned_data = super(EventoForm, self).clean()
        if cleaned_data.get('data_inicio') and cleaned_data.get('data_fim') and cleaned_data.get('data_inicio') >= cleaned_data.get('data_fim'):
            self.add_error('data_fim', 'A data de início não pode ser maior ou igual a data de fim.')
        return cleaned_data


class CalendarioForm(forms.FormPlus):
    ano = forms.ModelChoiceField(label='Ano', queryset=Ano.objects, required=False)
    calendario = forms.ModelChoiceField(Calendario.objects.filter(ativo=True), label='Calendário', empty_label='Todos', required=False)


class CalendarioCompraForm(forms.FormPlus):
    ano = forms.ModelChoiceField(label='Ano', queryset=Ano.objects, required=False)
    calendario = forms.ModelChoiceField(Calendario.objects.filter(ativo=True), label='Calendário', required=False)
    processo = forms.ChainedModelChoiceField(
        Processo.objects.all(),
        label='Processo',
        empty_label='Selecione um calendário',
        required=False,
        obj_label='tipo_processo__descricao',
        form_filters=[('calendario', 'tipo_processo__tipo_calendario_id')],
    )
    fase = forms.ChainedModelChoiceField(
        Fase.objects.all(),
        label='Fase',
        empty_label='Selecione um processo',
        required=False,
        obj_label='descricao',
        form_filters=[('processo', 'processo_id')],
    )


class FaseForm(forms.ModelFormPlus):
    class Meta:
        model = Fase
        fields = ('descricao', 'data_inicio', 'data_fim', 'fase_inicial', 'cor', 'ativo')
