from datetime import date, timedelta, datetime
from django.core.exceptions import ValidationError
from django.forms.formsets import formset_factory
from django.forms.utils import ErrorList

from almoxarifado.models import Empenho
from comum.models import PrestadorServico, Configuracao
from comum.utils import data_normal
from contratos.models import (
    Aditivo,
    AnexoContrato,
    Apostilamento,
    Contrato,
    Cronograma,
    Fiscal,
    Garantia,
    MaoDeObra,
    Medicao,
    Ocorrencia,
    Parcela,
    Penalidade,
    PublicacaoAditivo,
    SubtipoContrato,
    TipoContrato,
    TipoLicitacao,
    TipoPublicacao,
    AnexoMaoDeObra,
    ContratoTipoDocumentoComprobatorio,
    ArrecadacaoReceita,
    TipoDocumentoComprobatorio,
    MedicaoTipoDocumentoComprobatorio)
from djtools import forms
from djtools.choices import Anos, Meses
from djtools.forms.widgets import AutocompleteWidget, FilteredSelectMultiplePlus
from djtools.utils.pdf import pdf_valido
from protocolo.models import Processo
from rh.models import Servidor, UnidadeOrganizacional, Pessoa
from documento_eletronico.models import DocumentoTexto, NivelPermissao, TipoDocumento
from suap import settings


class ContratoForm(forms.ModelFormPlus):
    tipo = forms.ModelChoiceField(TipoContrato.objects, required=True)
    subtipo = forms.ChainedModelChoiceField(
        SubtipoContrato.objects, label='Subtipo', empty_label='Selecione um Tipo', obj_label='descricao', form_filters=[('tipo', 'tipo')], required=True
    )

    data_inicio = forms.DateFieldPlus(label='Data de Início')
    data_fim = forms.DateFieldPlus(label='Data de Término', required=False)
    tempo_indeterminado = forms.BooleanField(label='Tempo Indeterminado', required=False)

    valor = forms.DecimalFieldPlus('Valor', required=True)

    processo = forms.ModelChoiceField(queryset=Processo.objects, widget=AutocompleteWidget(), label='Processo', required=True)

    empenho = forms.ModelChoiceField(queryset=Empenho.objects, widget=AutocompleteWidget(search_fields=Empenho.SEARCH_FIELDS), label='Empenho', required=False)
    campi = forms.ModelMultipleChoiceField(queryset=UnidadeOrganizacional.objects.suap(), widget=FilteredSelectMultiplePlus('', True), label='Campi')
    pessoa_contratada = forms.ModelChoiceField(
        queryset=Pessoa.objects, widget=AutocompleteWidget(search_fields=Pessoa.SEARCH_FIELDS), label='Contratada', required=True, help_text="Busque por Nome, CPF ou CNPJ."
    )

    tipo_licitacao = forms.ModelChoiceField(label='Tipo de Licitação', queryset=TipoLicitacao.objects, widget=forms.Select, required=False)
    pregao = forms.CharField(required=False, label='Número da Licitação')

    data_conclusao = forms.DateFieldPlus(label='Data de Conclusão', required=False)

    arquivo_contrato = forms.FileFieldPlus(required=False, label="Arquivo do Contrato")

    documento_digital_contrato = forms.ModelChoiceField(label='Documento Digital do Contrato', queryset=DocumentoTexto.objects.none(), widget=AutocompleteWidget(search_fields=DocumentoTexto.SEARCH_FIELDS), required=False)

    class Meta:
        model = Contrato
        exclude = ('ordem', 'arquivo', 'cancelado', 'motivo_cancelamento', 'dh_cancelamento', 'usuario_cancelamento', 'numero_processo', 'tempo_indeterminado', 'documento_digital_contrato')

    class Media:
        js = ('/static/contratos/js/ContratoForm.js',)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if self.instance.arrecadacaoreceita_set.exists():
            self.fields['arrecadacao_receita'].widget.attrs['disabled'] = True

        if 'documento_eletronico' in settings.INSTALLED_APPS:
            user = self.request.user
            tipo_documento_contrato = Configuracao.get_valor_por_chave('contratos', 'tipo_documento_contrato')
            if tipo_documento_contrato and user:
                # TODO: Os documentos aqui exibidos não deveriam ser todos aqueles FINALIZADOS, PUBLICOS e do TIPO esperado pelo módulo de contratos?
                qs_documentostexto_contratos = (DocumentoTexto.objects.compartilhados(user, NivelPermissao.LER) | DocumentoTexto.objects.proprios(user)).filter(modelo__tipo_documento_texto__pk=int(tipo_documento_contrato))
                self.fields['documento_digital_contrato'].queryset = qs_documentostexto_contratos

            # TODO: Conversar com Inácio para ver se isso é necessário uma vez que existe a configuração que aponta para
            # o tipo de contrato "Contrato".
            if self.instance.documentos_texto_tipo_contato_relacionados().exists():
                self.fields['documento_digital_contrato'].initial = self.instance.documentos_texto_tipo_contato_relacionados().first()

    def clean_numero(self):
        try:
            c = Contrato.objects.get(numero=self.cleaned_data['numero'])  # Se nao achar um contrato será lançada a exceçao Contrato.DoesNotExist
            if c.id == self.instance.id:  # se o contrato retornado for o que está sendo atualizando, lança a mesma excecao para aproveitar o tratamento já feito
                raise Contrato.DoesNotExist()
        except Contrato.DoesNotExist:
            return self.cleaned_data['numero']

        raise forms.ValidationError('Este número já existe. Por favor escolha outro.')

    def clean_data_conclusao(self):
        cleaned_data = self.cleaned_data
        data_inicio = cleaned_data.get('data_inicio')
        data_conclusao = cleaned_data.get('data_conclusao')
        concluido = cleaned_data.get('concluido')

        # Se está marcado como concluído deve ser informado data_conclusao
        if concluido:
            if not data_conclusao:
                self.fields['data_conclusao'].initial = datetime.today()
                raise forms.ValidationError('A data de conclusão é obrigatória, pois o contrato foi marcado como concluído.')

            # Verifica se data conclusão é válida
            if data_inicio and data_conclusao < data_inicio:
                raise forms.ValidationError(f'A data de conclusão não pode ser menor que data de início do contrato ({data_inicio.strftime("%d/%m/%Y")}).')

        return data_conclusao

    def clean_data_fim(self):
        cleaned_data = self.cleaned_data
        data_fim = cleaned_data.get('data_fim')
        data_inicio = cleaned_data.get('data_inicio')

        # verifica se data final é válida
        if data_fim and data_inicio and data_fim < data_inicio:
            raise forms.ValidationError('Data final não pode ser menor que data inicial.')

        # A data não pode passar de 5 anos da data de inicio
        if data_fim and data_inicio and data_fim - data_inicio > timedelta(5 * 365):
            raise forms.ValidationError('A data final não pode ser')

        if data_fim and data_inicio and data_fim - data_inicio > timedelta(5 * 365):
            raise forms.ValidationError('A data final não pode ser maior do que {} (5 anos a mais que a data inicial).'.format(data_normal(data_inicio + timedelta(5 * 365))))

        return data_fim

    def clean(self):
        cleaned_data = self.cleaned_data
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')

        if not self.errors:
            if data_fim and data_inicio > data_fim:
                self._errors["data_fim"] = ['Data final anterior a data inicial']

        if cleaned_data.get('tipo') == 'Despesa':  # TODO
            if not cleaned_data.get('empenho'):
                self.add_error('empenho', 'Se o tipo de contrato for despesa, o empenho é obrigatório.')
        if cleaned_data.get('tipo') == 'Receita':  # TODO
            if not cleaned_data.get('processo'):
                self.add_error('processo', 'Se o tipo de contrato for receita, o processo é obrigatório.')
        if not cleaned_data.get('concluido') and cleaned_data.get('motivo_conclusao'):
            self.add_error('concluido', 'Você deve marcar o campo Concluído pois informou um Motivo para Conclusão.')
        if cleaned_data.get('concluido') and not cleaned_data.get('motivo_conclusao'):
            self.add_error('motivo_conclusao', 'Você deve informar um Motivo para Conclusão pois marcou o campo Concluído.')

        # TODO: Testar isso com um contrato novo, feito do zero.
        tem_arquivo_upload = cleaned_data.get('arquivo_contrato') is not None
        tem_documento_digitalizado = cleaned_data.get('documento_digital_contrato') is not None
        if not tem_arquivo_upload and not tem_documento_digitalizado:
            self.add_error('documento_digital_contrato', 'Você deve selecionar o Documento Digital do Contrato ou adicionar o Arquivo do Contrato (upload).')

        return cleaned_data


class ContratoCancelarForm(forms.FormPlus):
    motivo_cancelamento = forms.CharField(widget=forms.Textarea, required=True, label='Motivo do Cancelamento')


class MaoDeObraForm(forms.ModelFormPlus):
    data_nascimento = forms.DateFieldPlus(label='Data de Nascimento')
    desligamento = forms.DateFieldPlus(label='Data de Desligamento', required=False)
    prestador_servico = forms.ModelChoiceFieldPlus(
        queryset=PrestadorServico.objects.filter(ativo=True), widget=AutocompleteWidget(search_fields=PrestadorServico.SEARCH_FIELDS), label='Prestador de Serviços'
    )

    class Meta:
        model = MaoDeObra
        exclude = ['contrato']

    def __init__(self, *args, **kwargs):
        self.contrato = kwargs.pop('contrato', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            pks_uos_contrato = Contrato.objects.filter(pk=self.instance.contrato.id).values_list('campi', flat=True)
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.suap().filter(pk__in=pks_uos_contrato)
        else:
            pks_uos_contrato = Contrato.objects.filter(pk=self.contrato.id).values_list('campi', flat=True)
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.suap().filter(pk__in=pks_uos_contrato)


class PenalidadeForm(forms.ModelFormPlus):

    class Meta:
        model = Penalidade
        exclude = ['contrato', 'atualizado_por', 'atualizado_em']


class GarantiaForm(forms.ModelFormPlus):
    data_inicio = forms.DateFieldPlus(label='Data Início')
    vigencia = forms.DateFieldPlus(label='Vigência')
    consulta_susep = forms.FileFieldPlus(label='Anexo', required=True)

    class Meta:
        model = Garantia
        exclude = ['contrato']


class ApostilamentoForm(forms.ModelFormPlus):
    data_inicio = forms.DateFieldPlus(label='Data inicial', required=False)
    data_fim = forms.DateFieldPlus(label='Data final', required=False)

    class Meta:
        model = Apostilamento
        exclude = ['contrato', 'numero_processo', 'numero_empenho']

    def __init__(self, *args, **kwargs):
        try:
            self.data_inicio_contrato = kwargs.pop('data_inicio_contrato')
        except KeyError:
            self.data_inicio_contrato = kwargs['instance'].contrato.data_inicio
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')

        if not self.errors and (data_inicio and data_fim):
            if data_inicio and data_fim and data_inicio > data_fim:
                self._errors['data_fim'] = ErrorList(['Data final anterior a data inicial.'])
            if data_inicio and self.data_inicio_contrato > data_inicio:
                self._errors['data_inicio'] = ErrorList(['Data inicial informada é anterior a data inicial do contrato.'])
        return cleaned_data


class TermoAditivoForm(forms.ModelFormPlus):
    de_prazo = forms.BooleanField(required=False)
    de_valor = forms.BooleanField(required=False)
    de_fiscal = forms.BooleanField(required=False)
    de_outro = forms.BooleanField(required=False)
    valor = forms.DecimalFieldPlus('Valor', required=False)
    data_inicio = forms.DateFieldPlus(label='Data inicial', required=False)
    data_fim = forms.DateFieldPlus(label='Data final', required=False)

    processo = forms.ModelChoiceField(queryset=Processo.objects, widget=AutocompleteWidget(), label='Processo', required=False)

    empenho = forms.ModelChoiceField(queryset=Empenho.objects, widget=AutocompleteWidget(search_fields=Empenho.SEARCH_FIELDS), label='Empenho', required=False)

    arquivo_aditivo = forms.FileFieldPlus(label='Anexo')

    class Meta:
        model = Aditivo
        exclude = ['contrato', 'ordem', 'arquivo', 'numero_processo', 'numero_empenho']

    class Media:
        js = ('/static/contratos/js/TermoAditivoForm.js',)

    def __init__(self, *args, **kwargs):
        try:
            self.data_inicio_contrato = kwargs.pop('data_inicio_contrato')
        except KeyError:
            self.data_inicio_contrato = kwargs['instance'].contrato.data_inicio
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            self.fields['arquivo_aditivo'].widget = forms.HiddenInput()
            self.fields['arquivo_aditivo'].required = False

    def clean(self):
        cleaned_data = self.cleaned_data
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')

        if not self.errors:
            if data_inicio and data_fim and data_inicio > data_fim:
                self._errors['data_fim'] = ErrorList(['Data final anterior a data inicial.'])
            if data_inicio and self.data_inicio_contrato > data_inicio:
                self._errors['data_inicio'] = ErrorList(['Data inicial informada é anterior a data inicial do contrato.'])
        return cleaned_data


class PublicacaoContratoForm(forms.FormPlus):
    data = forms.DateFieldPlus(label='Data')
    tipo = forms.ModelChoiceField(label='Tipo', queryset=TipoPublicacao.objects, required=True)
    numero = forms.CharField(label='Número')
    descricao = forms.CharField(label='Descrição', max_length=255)
    arquivo = forms.FileFieldPlus(label='Arquivo')

    def clean(self):
        arquivo = self.cleaned_data.get('arquivo')
        if arquivo and not pdf_valido(arquivo):
            self.add_error('arquivo', 'Formato de arquivo não aceito (utilize somente arquivos PDF).')
        return self.cleaned_data


class EditarPublicacaoContratoForm(forms.FormPlus):
    data = forms.DateFieldPlus(label='Data', help_text='Data no formato dd/mm/aaaa')
    tipo = forms.ModelChoiceField(label='Tipo', queryset=TipoPublicacao.objects, required=True)
    numero = forms.CharField(label='Número')
    descricao = forms.CharField(label='Descrição', max_length=255)


class PublicacaoAditivoForm(forms.ModelFormPlus):
    data = forms.DateFieldPlus(label='Data', help_text='Data no formato dd/mm/aaaa')

    class Meta:
        model = PublicacaoAditivo
        exclude = ('arquivo', 'aditivo')


class AnexoContratoForm(forms.ModelFormPlus):
    data = forms.DateFieldPlus(label='Data', initial=date.today(), help_text='Data no formato dd/mm/aaaa')
    anexo = forms.FileFieldPlus(label='Anexo', required=True)

    class Meta:
        model = AnexoContrato
        exclude = ('arquivo', 'contrato')

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.contrato = kwargs.pop('contrato', None)
        super().__init__(*args, **kwargs)
        if self.instance and self.instance.arquivo:
            self.fields['anexo'].initial = self.instance.arquivo.get_field_file(self.user)
        if self.instance.pk:
            pks_uos_contrato = Contrato.objects.filter(pk=self.instance.contrato.id).values_list('campi', flat=True)
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.suap().filter(pk__in=pks_uos_contrato)
        else:
            pks_uos_contrato = Contrato.objects.filter(pk=self.contrato.id).values_list('campi', flat=True)
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.suap().filter(pk__in=pks_uos_contrato)


class AnexoMaoDeObraForm(forms.ModelFormPlus):
    class Meta:
        model = AnexoMaoDeObra
        exclude = ('maodeobra',)

    def __init__(self, *args, **kwargs):
        maodeobra = kwargs.pop("maodeobra")
        super().__init__(*args, **kwargs)
        self.instance.maodeobra = maodeobra


class ParcelaForm(forms.ModelFormPlus):
    data_prevista_inicio = forms.DateFieldPlus(label='Data Prevista de Início', help_text='Data no formato dd/mm/aaaa do início de execução')
    data_prevista_fim = forms.DateFieldPlus(label='Data Prevista de Término', help_text='Data no formato dd/mm/aaaa do término de execução')
    valor_previsto = forms.DecimalFieldPlus(label='Valor Previsto (R$)', required=True, help_text='Valor Previsto da Parcela')
    sem_medicao = forms.BooleanField(label='Parcela Sem Medição', initial=False, required=False)

    fieldsets = (('', {'fields': (('data_prevista_inicio', 'data_prevista_fim'), 'valor_previsto', 'campus', 'sem_medicao',)}),)

    class Meta:
        model = Parcela
        fields = ('data_prevista_inicio', 'data_prevista_fim', 'valor_previsto', 'sem_medicao')

    def set_contrato(self, contrato):
        self.contrato = contrato

    def __init__(self, *args, **kwargs):
        self.contrato = kwargs.pop('contrato', None)
        super().__init__(*args, **kwargs)
        if self.instance.medicoes_set.exists():
            del self.fields['valor_previsto']

    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data.get('valor_previsto') is not None:
            if (self.contrato.get_saldo_contrato() + (self.instance.valor_previsto or 0)) < cleaned_data['valor_previsto']:
                raise forms.ValidationError("Valor Previsto é maior que o Saldo (Parcelas + Medição) deste contrato.")


ParcelaContratoFormSet = formset_factory(ParcelaForm, extra=0)


class OcorrenciaMedicaoForm(forms.ModelFormPlus):
    ocorrencia = forms.CharField(widget=forms.Textarea, required=False, label='Ocorrência(s)', help_text='Descreva aqui as ocorrências registradas nessa medição')
    providencia = forms.CharField(widget=forms.Textarea, required=False, label='Providência(s)', help_text='Descreva aqui as providências tomadas para cada ocorrência')

    class Meta:
        model = Medicao
        fields = ('ocorrencia', 'providencia')


class MedicaoForm(forms.ModelFormPlus):
    data_inicio = forms.DateFieldPlus(label='Data Efetiva de Início', help_text='Data no formato dd/mm/aaaa do início efetivo de execução')
    data_fim = forms.DateFieldPlus(label='Data Efetiva de Término', help_text='Data no formato dd/mm/aaaa do término efetivo de execução')
    valor_executado = forms.DecimalFieldPlus(label='Valor Executado (R$)', help_text='Valor efetivamente executado', required=True)
    numero_documento = forms.CharField(required=True, label='Nº do Documento', help_text='Número da nota/documento fiscal')

    processo = forms.ModelChoiceField(queryset=Processo.objects, widget=AutocompleteWidget(), label='Processo', required=True)

    arquivo_medicao = forms.FileFieldPlus(label='Arquivo')

    ocorrencia = forms.CharField(widget=forms.Textarea, required=False, label='Ocorrência(s)', help_text='Descreva aqui as ocorrências registradas nessa medição')
    providencia = forms.CharField(widget=forms.Textarea, required=False, label='Providência(s)', help_text='Descreva aqui as providências tomadas para cada ocorrência')

    fieldsets = (('Medição', {'fields': (
        ('data_inicio', 'data_fim'), 'valor_executado', 'numero_documento', 'arquivo_medicao', 'processo', 'campus')}), ('Ocorrências', {'fields': ('ocorrencia', 'providencia')}),)

    class Meta:
        model = Medicao
        fields = ('data_inicio', 'data_fim', 'numero_documento', 'valor_executado', 'processo', 'campus', 'arquivo_medicao', 'ocorrencia', 'providencia')

    def __init__(self, *args, **kwargs):
        self.parcela = kwargs.pop('parcela', None)
        super().__init__(*args, **kwargs)
        self.fields['data_inicio'].initial = self.parcela.data_prevista_inicio
        self.fields['data_fim'].initial = self.parcela.data_prevista_fim
        self.fields['valor_executado'].initial = self.parcela.valor_previsto
        if self.instance and self.instance.arquivo:
            self.fields['arquivo_medicao'].initial = self.instance.arquivo.get_field_file(self.request.user)
        self.fields['arquivo_medicao'].label = 'Arquivo da Medição'

        pks_uos_contrato = Contrato.objects.filter(pk=self.parcela.cronograma.contrato.id).values_list('campi', flat=True)
        self.fields['campus'].queryset = UnidadeOrganizacional.objects.suap().filter(pk__in=pks_uos_contrato)

        fields_conf = list()
        if ContratoTipoDocumentoComprobatorio.objects.filter(contrato__pk=self.parcela.cronograma.contrato.id).exists():
            for field_conf in ContratoTipoDocumentoComprobatorio.objects.filter(contrato__pk=self.parcela.cronograma.contrato.id):
                field_name = "field_name_{}".format(field_conf.tipo_documento_comprobatorio.pk)
                initial_value = "2"
                readonly = False
                medicao_doc_comprobatorio = self.instance.medicaotipodocumentocomprobatorio_set.filter(medicao__id=self.instance.id, tipo_documento_comprobatorio__id=field_conf.tipo_documento_comprobatorio.pk)
                if medicao_doc_comprobatorio.exists():
                    initial_value = medicao_doc_comprobatorio.first().confirmacao_fiscal
                    readonly = True if medicao_doc_comprobatorio.first().recebido_gerente == "Recebido" else False

                if not field_name in self.fields.keys():
                    self.fields[field_name] = forms.ChoiceField(required=False, choices=MedicaoTipoDocumentoComprobatorio.CONFIMACAO_FISCAL_CHOICES, label=field_conf.tipo_documento_comprobatorio.descricao)
                    fields_conf.append("field_name_{}".format(field_conf.tipo_documento_comprobatorio.pk))
                    self.fields[field_name].initial = initial_value
                    self.fields[field_name].widget.attrs['readonly'] = readonly

        if fields_conf:
            try:
                if MedicaoForm.fieldsets[2]:
                    pass
            except IndexError:
                MedicaoForm.fieldsets += (('Conferência de Documentos', {'fields': tuple(fields_conf)}), )

    def clean(self):
        cleaned_data = self.cleaned_data
        if cleaned_data.get('valor_executado') is not None:
            saldo_contrato = self.parcela.cronograma.contrato.get_saldo_atual()
            if self.instance.valor_executado:
                saldo_contrato = self.parcela.cronograma.contrato.get_saldo_atual() + self.instance.valor_executado
            if saldo_contrato < cleaned_data['valor_executado']:
                raise forms.ValidationError("Valor da medição maior que o saldo do contrato.")
        return cleaned_data


class MedicaoEletricaForm(MedicaoForm):
    fieldsets = None
    mes_referencia = forms.ChoiceField(label='Mês de Referência', required=True, choices=Meses.get_choices())
    ano_referencia = forms.ChoiceField(label='Ano de Referência', required=True, choices=Anos.get_choices())
    consumo_ponta = forms.DecimalFieldPlus(label='Consumo de Ponta(kWh)', required=False, max_digits=0)
    consumo_fora_ponta = forms.DecimalFieldPlus(label='Consumo Fora Ponta(kWh)', required=False, max_digits=0)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        default_mes_referencia = self.parcela.data_prevista_inicio.month
        default_ano_referencia = self.parcela.data_prevista_inicio.year
        self.fields['mes_referencia'].initial = default_mes_referencia
        self.fields['ano_referencia'].initial = default_ano_referencia
        if self.instance and hasattr(self.instance, 'medicaoeletrica'):
            self.fields['mes_referencia'].initial = self.instance.medicaoeletrica.mes_referencia or default_mes_referencia
            self.fields['ano_referencia'].initial = self.instance.medicaoeletrica.ano_referencia or default_ano_referencia
            self.fields['consumo_ponta'].initial = self.instance.medicaoeletrica.consumo_ponta
            self.fields['consumo_fora_ponta'].initial = self.instance.medicaoeletrica.consumo_fora_ponta

        self.fieldsets = MedicaoForm.fieldsets + (('Medição Elétrica', {
            'fields': (('consumo_ponta', 'consumo_fora_ponta'), ('ano_referencia', 'mes_referencia'))}),)


class CronogramaForm(forms.ModelFormPlus):
    nl = forms.CharField(required=False, label='NL')
    rc = forms.CharField(required=False, label='RC')

    class Meta:
        model = Cronograma
        exclude = ('contrato',)


class FiscalForm(forms.ModelFormPlus):
    data_nomeacao = forms.DateFieldPlus(label='Data da Nomeação', required=False)
    data_vigencia = forms.DateFieldPlus(label='Data Final da Vigência', required=False)
    servidor = forms.ModelChoiceField(label='Servidor', queryset=Servidor.objects.ativos(), widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS))

    class Meta:
        model = Fiscal
        exclude = ('contrato', 'data_exclusao', 'termo_aditivo')

    def __init__(self, *args, **kwargs):
        self.contrato = kwargs.pop('contrato', None)
        super().__init__(*args, **kwargs)
        self.fields['campus'].queryset = UnidadeOrganizacional.objects.uo()

        if self.instance and self.instance.servidor_id:
            self.fields['servidor'] = forms.ModelChoiceField(
                label='Servidor', queryset=Servidor.objects, widget=AutocompleteWidget(readonly=True, search_fields=Servidor.SEARCH_FIELDS), initial=self.instance.servidor_id
            )

    def clean(self):
        cleaned_data = self.cleaned_data
        if self.contrato and cleaned_data.get('servidor') and Fiscal.objects.filter(contrato=self.contrato, servidor=cleaned_data['servidor'], inativo=False).exists():
            self.add_error('servidor', 'Este fiscal já foi adicionado ao contrato.')
        return cleaned_data


class UploadArquivoContratoForm(forms.ModelFormPlus):
    class Meta:
        model = Contrato
        fields = ('arquivo_contrato',)


class SolicitacaoFiscalForm(forms.FormPlus):
    numero_memorando = forms.CharField(label='Ofício Nº')


class SolicitacaoPublicacaoPortariaFiscalForm(forms.FormPlus):
    servidor = forms.ModelChoiceField(queryset=Servidor.objects, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS, minChars=5), label='Servidor', required=True)


class DespachoTermoAditivoForm(forms.FormPlus):
    numero_memorando = forms.CharField(label='Memorando Nº')
    numero_despacho = forms.CharField(label='Despacho Nº')


class DespachoFiscalForm(forms.FormPlus):
    servidor = forms.ModelChoiceField(label='Servidor', queryset=Servidor.objects.ativos(), widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS))


class OcorrenciaForm(forms.ModelFormPlus):
    prazo_resolucao = forms.DateFieldPlus(label='Prazo para Resolução', required=True)

    class Meta:
        model = Ocorrencia
        fields = ['descricao', 'prazo_resolucao', 'situacao', 'campus']

    def __init__(self, *args, **kwargs):
        self.contrato = kwargs.pop('contrato', None)
        super().__init__(*args, **kwargs)
        if self.instance.pk:
            pks_uos_contrato = Contrato.objects.filter(pk=self.instance.contrato.id).values_list('campi', flat=True)
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.suap().filter(pk__in=pks_uos_contrato)
        else:
            pks_uos_contrato = Contrato.objects.filter(pk=self.contrato.id).values_list('campi', flat=True)
            self.fields['campus'].queryset = UnidadeOrganizacional.objects.suap().filter(pk__in=pks_uos_contrato)


class SituacaoContratosForm(forms.FormPlus):
    campus = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.suap().all(), required=False)
    data_inicio = forms.DateFieldPlus(label='Data inicial', required=True)
    data_fim = forms.DateFieldPlus(label='Data final', required=True)
    eh_continuado = forms.BooleanField(label='Somente continuados', initial=False, required=False)
    eh_concluido = forms.BooleanField(label='Somente concluídos', initial=False, required=False)

    def clean(self):
        cleaned_data = self.cleaned_data
        data_inicio = cleaned_data.get('data_inicio')
        data_fim = cleaned_data.get('data_fim')

        if not self.errors:
            if data_inicio > data_fim:
                self._errors['data_fim'] = ['Data final anterior a data inicial']
        return cleaned_data


class RelatorioPendenciasForm(forms.FormPlus):
    campus = forms.ModelChoiceField(queryset=UnidadeOrganizacional.objects.suap(), label='Filtrar por Campus', required=False, empty_label='Todos')


class FiltroContratoForm(forms.FormPlus):
    CHOICES = ((None, "---"), (True, "Sim"), (False, "Não"))
    busca = forms.CharFieldPlus(label='Busca', required=False)
    tipo_licitacao = forms.ModelChoiceField(label='Tipo de Licitação', queryset=TipoLicitacao.objects, widget=forms.Select, required=False)
    periodo_data_inicio = forms.BRDateRangeField(label='Início', required=False, help_text='Data do Início do contrato')
    periodo_data_vencimento = forms.BRDateRangeField(label='Vencimento', help_text='Considera a maior entre a data final do contrato ou do(s) seus aditivo(s).', required=False)
    concluido = forms.ChoiceField(label='Concluído', choices=CHOICES, required=False)
    cancelado = forms.ChoiceField(label='Cancelado', choices=CHOICES, required=False)


class FiltroContratoEletricoForm(forms.FormPlus):
    ano = forms.ChoiceField(label='Ano:', widget=forms.Select())
    mes = forms.MesField(label='Mês', empty_label="Todos")

    fieldsets = ((None, {'fields': (('ano', 'mes'),)}),)

    def __init__(self, *args, **kwargs):
        contrato = kwargs.pop('contrato')
        super().__init__(*args, **kwargs)
        self.fields['ano'].choices = Anos.get_choices(ano_minimo=contrato.data_inicio.year, empty_label='Todos', empty_value='todos')
        self.fields['ano'].initial = date.today().year


class ConfiguracaoForm(forms.FormPlus):
    dias_nova_licitacao = forms.IntegerFieldPlus(label='Quantidade de dias para iniciar nova licitação', required=False, initial=90)
    tipo_contrato_energia_eletrica = forms.ModelChoiceField(
        label='SubTipo de Contrato Energia Elétrica',
        help_text='Escolha aqui o subtipo de contrato que será usado como referência para contratos de fornecimento de energia elétrica.',
        queryset=SubtipoContrato.objects,
        widget=forms.Select,
        required=False,
    )
    if 'documento_eletronico' in settings.INSTALLED_APPS:
        tipo_documento_contrato = forms.ModelChoiceField(
            label='Selecione o tipo de documento utilizado para Contratos Administrativos',
            help_text='Escolha aqui o tipo de documento utilizado para Contratos Administrativos.',
            queryset=TipoDocumento.objects.filter(ativo=True),
            widget=AutocompleteWidget(search_fields=TipoDocumento.SEARCH_FIELDS),
            required=False,
        )


class ExportacaoForm(forms.FormPlus):
    STATUS_ANDAMENTO = 'Em andamento'
    STATUS_CONCLUIDO = 'Concluídos'
    STATUS_CANCELADOS = 'Cancelados'
    STATUS_TODOS = 'Todos'
    STATUS_CHOICES = ((STATUS_TODOS, STATUS_TODOS), (STATUS_ANDAMENTO, STATUS_ANDAMENTO), (STATUS_CONCLUIDO, STATUS_CONCLUIDO), (STATUS_CANCELADOS, STATUS_CANCELADOS))

    QUADRO_PUBLICACAO = 'Publicações'
    QUADRO_CRONOGRAMA = 'Cronograma'
    QUADRO_CHOICES = ((QUADRO_PUBLICACAO, QUADRO_PUBLICACAO), (QUADRO_CRONOGRAMA, QUADRO_CRONOGRAMA))

    tipo = forms.ModelChoiceFieldPlus(queryset=TipoContrato.objects, label='Tipo do Contrato', required=False)
    data_inicio_periodo = forms.BRDateRangeField(label='Período para Início do Contrato', required=False)
    campi = forms.ModelMultipleChoiceField(queryset=UnidadeOrganizacional.objects, widget=FilteredSelectMultiplePlus('', True), label='Campi')
    status = forms.ChoiceField(label='Estado do contrato', choices=STATUS_CHOICES, initial=STATUS_TODOS, required=False)
    quadros = forms.MultipleChoiceField(label='Quadros', choices=QUADRO_CHOICES, widget=forms.CheckboxSelectMultiple, required=False)


class UploadArquivoForm(forms.FormPlus):
    arquivo = forms.FileFieldPlus(filetypes=['pdf'])

    def clean_arquivo(self):
        arquivo = self.cleaned_data.get('arquivo', None)
        if not pdf_valido(arquivo):
            raise ValidationError('Formato de arquivo não aceito (utilize somente arquivos PDF).')
        return self.clean


class ContratoTiposDocumentosComprobatorioForm(forms.FormPlus):
    tipo_documento_comprobatorio = forms.ModelChoiceField(label='Tipo de Documento Comprobatório', queryset=TipoDocumentoComprobatorio.objects.filter(ativo=True), required=True)

    def __init__(self, *args, **kwargs):
        self.contrato = kwargs.pop('contrato', None)
        super().__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = self.cleaned_data
        tipo_documento_comprobatorio = cleaned_data.get('tipo_documento_comprobatorio')

        if not self.errors:
            if ContratoTipoDocumentoComprobatorio.objects.filter(contrato=self.contrato, tipo_documento_comprobatorio=tipo_documento_comprobatorio).exists():
                self._errors['tipo_documento_comprobatorio'] = ['Tipo de documento já está vinculado ao Contrato']
        return cleaned_data

    def save(self):
        tipo_doc_contrato = ContratoTipoDocumentoComprobatorio()
        tipo_doc_contrato.contrato = self.contrato
        tipo_doc_contrato.tipo_documento_comprobatorio = self.cleaned_data['tipo_documento_comprobatorio']
        tipo_doc_contrato.save()
        return tipo_doc_contrato


class ArrecadacaoReceitaForm(forms.ModelFormPlus):

    class Meta:
        model = ArrecadacaoReceita
        exclude = ['contrato']


class MedicaoTipoDocumentoComprobatorioForm(forms.ModelFormPlus):
    class Meta:
        model = MedicaoTipoDocumentoComprobatorio
        exclude = ['medicao', 'confirmado', 'data_avaliacao', 'avaliador_gerente']

    def clean_parecer_gerente(self):
        cleaned_data = self.cleaned_data
        parecer_gerente = cleaned_data.get('parecer_gerente')

        if cleaned_data['recebido_gerente'] == "Pendente" and parecer_gerente is None:
            raise forms.ValidationError('É necessário informar uma descrição da pendência.')
        return parecer_gerente
