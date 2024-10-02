from djtools import forms
from .models import BoletimProgramado
from documento_eletronico.models import TipoDocumento
from django.contrib.admin.widgets import FilteredSelectMultiple
from datetime import datetime


class BoletimProgramadoForm(forms.ModelFormPlus):
    tipo_documento = forms.ModelMultipleChoiceField(
        label='Tipos de documentos', queryset=TipoDocumento.ativos, widget=FilteredSelectMultiple('Tipos de Documentos', True), required=True
    )

    class Meta:
        model = BoletimProgramado
        fields = ['titulo', 'tipo_documento', 'nivel_acesso', 'programado', 'programado_semanal', 'programado_mensal']


class GerarBoletimMesForm(forms.FormPlus):
    METHOD = 'GET'
    SUBMIT_LABEL = 'Gerar Boletim'

    ano = forms.IntegerField(label='Selecione o Ano:', required=False, widget=forms.Select())
    mes = forms.MesField(label='Selecione o Mês:', required=False, choices=[])

    def __init__(self, *args, **kwargs):
        super(GerarBoletimMesForm, self).__init__(*args, **kwargs)
        maior_ano = datetime.now().year
        _anos = list(range(maior_ano, 2017, -1))
        ANO_CHOICES = [[a, '{}'.format(a)] for a in _anos]
        self.fields['ano'].widget.choices = ANO_CHOICES
