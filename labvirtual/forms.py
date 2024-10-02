#
from django.db import transaction
from django.core.exceptions import ValidationError
from django.utils.formats import localize
#
from djtools.utils import SpanField
from djtools.utils import get_datetime_now
from djtools import forms
from djtools.forms.widgets import AutocompleteWidget
from comum.models import UnidadeOrganizacional
from edu.models import Diario
from agendamento.forms import SolicitacaoAgendamentoModelForm
from agendamento.status import SolicitacaoAgendamentoStatus
#
from .models import SolicitacaoLabVirtual, DesktopPool


class DesktopPoolForm(forms.ModelForm):
    readonly_fields = ('desktop_pool_id', )
    location = forms.ModelChoiceFieldPlus(label='Campus', queryset=UnidadeOrganizacional.locals, required=False)
    desktop_pool_id = forms.CharFieldPlus(label='Horizon ID', widget=forms.TextInput(attrs={'readonly': 'readonly'}))

    class Meta:
        model = DesktopPool
        fields = ('name', 'description', 'location', 'desktop_pool_id')


class SolicitacaoLabVirtualForm(SolicitacaoAgendamentoModelForm):
    readonly_fields = ('laboratorio', 'capacidade')
    #
    laboratorio = forms.ModelChoiceFieldPlus(label='Laboratorio', queryset=DesktopPool.objects, required=True)
    capacidade = forms.IntegerFieldPlus(label='Capacidade', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    #
    diario = forms.ModelChoiceFieldPlus(label='Diario', queryset=Diario.objects, required=False, widget=AutocompleteWidget())
    #

    fieldsets = (
        (
            'Dados Gerais',
            {
                'fields': (
                    ('laboratorio', 'capacidade'),
                    ('diario'),
                    ('data_inicio', 'data_fim'),
                    ('hora_inicio', 'hora_fim'),
                )
            },
        ),
        (
            'Dias da Semana',
            {
                'fields': (
                    (
                        'recorrencia_segunda', 'recorrencia_terca', 'recorrencia_quarta',
                        'recorrencia_quinta', 'recorrencia_sexta', 'recorrencia_sabado',
                        'recorrencia_domingo'
                    ),
                )
            },
        ),
    )

    class Meta:
        model = SolicitacaoLabVirtual
        fields = (
            'laboratorio', 'diario',
            'data_inicio', 'data_fim', 'hora_inicio', 'hora_fim',
            'recorrencia_segunda', 'recorrencia_terca', 'recorrencia_quarta',
            'recorrencia_quinta', 'recorrencia_sexta', 'recorrencia_sabado',
            'recorrencia_domingo'
        )

    def __init__(self, *args, **kwargs):
        laboratorio_pk = kwargs.pop('laboratorio_pk', None)
        super().__init__(*args, **kwargs)

        #
        laboratorio_qs = DesktopPool.objects.filter(pk=laboratorio_pk)
        laboratorio = laboratorio_qs.first()
        self.fields['laboratorio'].queryset = laboratorio_qs
        self.fields['laboratorio'].initial = laboratorio.pk
        self.fields['laboratorio'].widget.attrs['readonly'] = True
        #
        self.fields['capacidade'].initial = laboratorio.max_number_of_machines()
        self.fields['capacidade'].widget.attrs['readonly'] = True

    def verificar_duplicadas(self, cleaned_data):
        duplicadas = SolicitacaoLabVirtual.objects.filter(
            laboratorio=cleaned_data['laboratorio'],
            diario=cleaned_data['diario'],
            status=SolicitacaoAgendamentoStatus.STATUS_ESPERANDO,
            data_inicio=cleaned_data['data_inicio'],
            hora_inicio=cleaned_data['hora_inicio'],
            data_fim=cleaned_data['data_fim'],
            hora_fim=cleaned_data['hora_fim'],
            recorrencia_segunda=cleaned_data['recorrencia_segunda'],
            recorrencia_terca=cleaned_data['recorrencia_terca'],
            recorrencia_quarta=cleaned_data['recorrencia_quarta'],
            recorrencia_quinta=cleaned_data['recorrencia_quinta'],
            recorrencia_sexta=cleaned_data['recorrencia_sexta'],
            recorrencia_sabado=cleaned_data['recorrencia_sabado'],
            recorrencia_domingo=cleaned_data['recorrencia_domingo'],
        ).exists()
        if duplicadas:
            raise ValidationError("Uma solicitação idêntica já existe.\n")

    def _validar_solicitacao(self, cleaned_data):
        solicitacao = SolicitacaoLabVirtual(
            laboratorio=cleaned_data['laboratorio'],
            diario=cleaned_data['diario'],
            status=SolicitacaoAgendamentoStatus.STATUS_ESPERANDO,
            data_inicio=cleaned_data['data_inicio'],
            hora_inicio=cleaned_data['hora_inicio'],
            data_fim=cleaned_data['data_fim'],
            hora_fim=cleaned_data['hora_fim'],
            recorrencia_segunda=cleaned_data['recorrencia_segunda'],
            recorrencia_terca=cleaned_data['recorrencia_terca'],
            recorrencia_quarta=cleaned_data['recorrencia_quarta'],
            recorrencia_quinta=cleaned_data['recorrencia_quinta'],
            recorrencia_sexta=cleaned_data['recorrencia_sexta'],
            recorrencia_sabado=cleaned_data['recorrencia_sabado'],
            recorrencia_domingo=cleaned_data['recorrencia_domingo'],
        )
        #
        if solicitacao.tem_conflito_reservas():
            raise ValidationError(f"O laboratório {cleaned_data['laboratorio']} já possui uma reserva no intervalo específico.\n")
        #
        if solicitacao.diario:
            qtde_alunos = solicitacao.diario.get_quantidade_alunos_ativos()
            if cleaned_data['capacidade'] < qtde_alunos:
                raise ValidationError(f"O laboratório suporta {cleaned_data['capacidade']} máquinas, sendo insuficientes para {qtde_alunos} alunos.\n")

    def clean(self):
        cleaned_data = super().clean()
        if self.is_valid():
            self.verificar_duplicadas(cleaned_data)
            self._validar_solicitacao(cleaned_data)
        return cleaned_data


class IndeferirSolicitacaoLabVirtualForm(forms.ModelFormPlus):
    readonly_fields = ('avaliador', 'data_avaliacao')
    avaliador = forms.CharField(label='Avaliador', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    data_avaliacao = forms.CharField(label='Data da Avaliação', widget=forms.TextInput(attrs={'readonly': 'readonly'}))
    observacao_avaliador = forms.CharField(label='Justificativa', widget=forms.Textarea(), required=True)

    fieldsets = (
        (None, {
            'fields': (('avaliador'), ('data_avaliacao'), ('observacao_avaliador'))
        }),
    )

    class Meta:
        model = SolicitacaoLabVirtual
        fields = ('observacao_avaliador', )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['avaliador'].initial = self.user
        self.fields['avaliador'].widget.attrs['readonly'] = True
        #
        data_avaliacao = get_datetime_now()
        self.fields['data_avaliacao'].initial = localize(data_avaliacao)
        self.fields['data_avaliacao'].widget.attrs['readonly'] = True
        #

    def clean_observacao_avaliador(self):
        observacao_avaliador = self.cleaned_data.get('observacao_avaliador', None)
        if observacao_avaliador is None:
            self.add_error('observacao_avaliador', 'Informe a justificativa do indeferimento')
        return observacao_avaliador

    @transaction.atomic()
    def save(self, *args, **kwargs):
        self.instance.data_avaliacao = get_datetime_now()
        self.instance.avaliador = self.user
        self.instance.indeferir()
        return super().save(*args, **kwargs)


class CancelarSolicitacaoLabVirtualForm(forms.ModelFormPlus):
    cancelado_por = SpanField('Avaliador')
    status = SpanField('Status')
    data_cancelamento = SpanField('Data do Cancelamento')
    justificativa_cancelamento = forms.CharField(label='Justificativa', widget=forms.Textarea(), required=True)

    fieldsets = (
        (None, {
            'fields': (('cancelado_por'), ('data_cancelamento'), ('status'), ('justificativa_cancelamento'))
        }),
    )

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        self.fields['cancelado_por'].widget.original_value = self.user
        #
        data_cancelamento = get_datetime_now()
        self.fields['data_cancelamento'].widget.original_value = data_cancelamento
        self.fields['data_cancelamento'].widget.label_value = localize(data_cancelamento)
        #
        self.fields['status'].widget.original_value = 'Cancelada'

    class Meta:
        model = SolicitacaoLabVirtual
        fields = ('justificativa_cancelamento', )

    def clean_justificatiava_cancelamento(self):
        justificatica = self.cleaned_data.get('justificatiava_cancelamento', None)
        if justificatica is None:
            self.add_error('justificativa_cancelamento', 'Informe a justificativa do indeferimento')
        return justificatica

    @transaction.atomic()
    def save(self, *args, **kwargs):
        self.instance.data_avaliacao = get_datetime_now()
        self.instance.cancelar()
        return super().save(*args, **kwargs)
