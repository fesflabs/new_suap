# -*- coding: utf-8 -*-
from datetime import datetime

from djtools.utils import send_notification
from django.db import transaction
from django.forms import Textarea
from django.utils.safestring import mark_safe
from comum.models import PrestadorServico
from comum.utils import tl
from djtools import forms
from djtools.forms.widgets import AutocompleteWidget
from professor_titular.models import ProcessoTitular, ValidacaoCPPD, ProcessoAvaliador, Avaliacao
from progressoes.assinatura import SuapAssinaturaForm
from protocolo.models import Processo
from rh.models import Servidor, Avaliador
from django.conf import settings


class ProcessoRSCDocumentoExigidosForm(forms.ModelFormPlus):
    class Meta:
        model = ProcessoTitular
        exclude = ()
        # fields = ('data_concessao_ultima_rt', 'data_exercio_carreira', 'data_conclusao_titulacao_rsc_pretendido' )


class ProcessoTitularForm(forms.FormPlus):

    # fields que representam todos os arquivos do processo
    qtd_itens = forms.IntegerFieldPlus()
    data_referencia = forms.DateFieldPlus()
    nota_pretendida = forms.DecimalField()
    descricao = forms.CharField(label='Motivo de Saída', widget=forms.Textarea(), required=True)

    # relatório descritivo do processo
    introducao_relatorio_descritivo = forms.CharFieldPlus(widget=Textarea, max_length=100000)
    conclusao_relatorio_descritivo = forms.CharFieldPlus(widget=Textarea, max_length=100000)

    # datas documentos preliminares
    data_concessao_titulacao_doutor = forms.DateFieldPlus()
    data_progressaoD404 = forms.DateFieldPlus()
    data_avaliacao_desempenho = forms.DateFieldPlus()
    data_graduacao_EBTT = forms.DateFieldPlus()

    def __init__(self, *args, **kwargs):
        self.processo = kwargs.pop('processo', None)
        super(ProcessoTitularForm, self).__init__(*args, **kwargs)
        if self.processo:
            if not self.processo.avaliado_pode_editar():
                self.fields['data_concessao_titulacao_doutor'].widget.attrs['disabled'] = 'disabled'
                self.fields['data_progressaoD404'].widget.attrs['disabled'] = 'disabled'
                self.fields['data_graduacao_EBTT'].widget.attrs['disabled'] = 'disabled'
                self.fields['data_avaliacao_desempenho'].widget.attrs['disabled'] = 'disabled'
                self.fields['introducao_relatorio_descritivo'].widget.attrs['disabled'] = "disabled"
                self.fields['conclusao_relatorio_descritivo'].widget.attrs['disabled'] = "disabled"

    @staticmethod
    def factory_field_render_arquivo(processo, criterio, request):
        field_arquivo = forms.AjaxFileUploadField('/professor_titular/professor_titular_upload/', 'onCompleteUploadCriterio%d' % criterio.id)
        field_arquivo.widget.request = request
        field_arquivo.widget.params['criterio'] = criterio.id
        field_arquivo.widget.params['processo'] = processo.id
        return field_arquivo.widget.render('', '')

    @staticmethod
    def factory_field_render_qtd_itens(arquivo_instance):
        form_arquivo = ProcessoTitularForm()
        field_qtd_itens_name = "Arquivo_%s_qtd" % arquivo_instance.id

        teto_grupo = arquivo_instance.criterio.indicador.grupo.get_teto(arquivo_instance.processo.ano)
        field_qtd_itens_onkeyup = "calcula_nota_pretendida(this, %s, %s, %s, %s, %s, %s);" % (
            arquivo_instance.id,
            arquivo_instance.criterio.indicador.id,
            arquivo_instance.criterio.indicador.grupo.id,
            arquivo_instance.criterio.id,
            arquivo_instance.criterio.pontos,
            teto_grupo,
        )

        pontuacoes = arquivo_instance.criterio.indicador.grupo.pontuacaominima_set.filter(ano=arquivo_instance.processo.ano)
        if pontuacoes.exists():
            pontuacao_minima_exigida = pontuacoes[0].pontuacao_exigida
            qtd_minima_grupos = pontuacoes[0].qtd_minima_grupos
        field_qtd_itens_onblur = "Processa_Salvamento('%s', %s, '%s', '%s', '%s', '%s');" % (
            'Autosalvar',
            arquivo_instance.processo_id,
            'tipo_rsc',
            arquivo_instance.processo.get_status_display(),
            pontuacao_minima_exigida,
            qtd_minima_grupos,
        )

        if (arquivo_instance.processo.avaliado_pode_editar()) and (tl.get_user().get_relacionamento().id == arquivo_instance.processo.servidor.id):
            field_qtd_itens = form_arquivo.fields['qtd_itens'].widget.render(
                field_qtd_itens_name,
                arquivo_instance.qtd_itens,
                {'id': 'qtd_%s' % arquivo_instance.id, 'OnKeyUp': field_qtd_itens_onkeyup, 'onchange': field_qtd_itens_onkeyup + field_qtd_itens_onblur},
            )
        else:
            field_qtd_itens = form_arquivo.fields['qtd_itens'].widget.render(
                field_qtd_itens_name,
                arquivo_instance.qtd_itens,
                {'id': 'qtd_%s' % arquivo_instance.id, 'OnKeyUp': field_qtd_itens_onkeyup, 'onchange': field_qtd_itens_onkeyup + field_qtd_itens_onblur, 'disabled': "disabled"},
            )

        return mark_safe("%s" % field_qtd_itens)

    @staticmethod
    def factory_field_render_data_referencia(arquivo_instance):
        form_arquivo = ProcessoTitularForm()
        field_data_referencia_name = "Arquivo_%s_data" % arquivo_instance.id
        pontuacoes = arquivo_instance.criterio.indicador.grupo.pontuacaominima_set.filter(ano=arquivo_instance.processo.ano)
        if pontuacoes.exists():
            pontuacao_minima_exigida = pontuacoes[0].pontuacao_exigida
            qtd_minima_grupos = pontuacoes[0].qtd_minima_grupos
        field_data_referencia_onblur = "Processa_Salvamento('%s', %s, '%s', '%s', '%s', '%s');" % (
            'Autosalvar',
            arquivo_instance.processo_id,
            'tipo_rsc',
            arquivo_instance.processo.get_status_display(),
            pontuacao_minima_exigida,
            qtd_minima_grupos,
        )
        attrs = {'id': 'data_%s' % arquivo_instance.id, 'onchange': field_data_referencia_onblur}

        if not (arquivo_instance.processo.avaliado_pode_editar()) or not (tl.get_user().get_relacionamento().id == arquivo_instance.processo.servidor.id):
            attrs['disabled'] = 'disabled'

        field_data_referencia = form_arquivo.fields['data_referencia'].widget.render(field_data_referencia_name, arquivo_instance.data_referencia, attrs)
        return field_data_referencia

    @staticmethod
    def factory_field_render_nota_pretendida(arquivo_instance):
        form_arquivo = ProcessoTitularForm()
        field_nota_pretendida_name = "Arquivo_%s_nota" % arquivo_instance.id
        # field_nota_pretendida =  form_arquivo.fields['nota_pretendida'].widget.render(field_nota_pretendida_name,
        #                                                                               arquivo_instance.nota_pretendida, {'id': 'nota_%s' % arquivo_instance.id,
        #                                                                                                                  'type': 'hidden'})
        # return field_nota_pretendida
        form_arquivo.fields['nota_pretendida'].widget = forms.HiddenInput(attrs={'id': 'nota_%s' % arquivo_instance.id})
        return form_arquivo.fields['nota_pretendida'].widget.render(field_nota_pretendida_name, arquivo_instance.nota_pretendida)

    @staticmethod
    def factory_field_render_descricao(arquivo_instance):
        form_arquivo = ProcessoTitularForm()
        field_name = "Arquivo_%s_descricao" % arquivo_instance.id
        pontuacoes = arquivo_instance.criterio.indicador.grupo.pontuacaominima_set.filter(ano=arquivo_instance.processo.ano)
        if pontuacoes.exists():
            pontuacao_minima_exigida = pontuacoes[0].pontuacao_exigida
            qtd_minima_grupos = pontuacoes[0].qtd_minima_grupos
        field_onblur = "Processa_Salvamento('%s', %s, '%s', '%s', '%s', '%s');" % (
            'Autosalvar',
            arquivo_instance.processo_id,
            'tipo_rsc',
            arquivo_instance.processo.get_status_display(),
            pontuacao_minima_exigida,
            qtd_minima_grupos,
        )

        if (arquivo_instance.processo.avaliado_pode_editar() or arquivo_instance.processo.avaliado_pode_ajustar()) and (
            tl.get_user().get_relacionamento().id == arquivo_instance.processo.servidor.id
        ):
            field_descricao = form_arquivo.fields['descricao'].widget.render(
                field_name,
                arquivo_instance.descricao,
                {'id': 'descricao_%s' % arquivo_instance.id, 'onchange': field_onblur, 'class': 'textarea_descricao', 'style': 'width: 100%'},
            )
        else:
            field_descricao = form_arquivo.fields['descricao'].widget.render(
                field_name,
                arquivo_instance.descricao,
                {'id': 'descricao_%s' % arquivo_instance.id, 'onchange': field_onblur, 'class': 'textarea_descricao', 'style': 'width: 100%', 'disabled': "disabled"},
            )

        return field_descricao


class RejeitarProcessoCPPDForm(forms.FormPlus):
    processo = forms.ModelChoiceFieldPlus(ProcessoTitular.objects, label='Processo RSC', widget=forms.HiddenInput())
    tipo = forms.ChoiceField(label='Tipo', choices=ProcessoAvaliador.TIPO_RECUSA_CHOICES)
    motivo_recusa = forms.CharFieldPlus(label='Motivo da Recusa', max_length=10000, widget=forms.Textarea())
    SUBMIT_LABEL = 'Rejeitar'

    def __init__(self, *args, **kwargs):
        if 'processo' in kwargs:
            self.processo = kwargs.pop('processo')
        super(RejeitarProcessoCPPDForm, self).__init__(*args, **kwargs)
        if self.processo:
            self.fields['processo'].initial = self.processo.id

    @transaction.atomic
    def processar(self):
        if self.cleaned_data.get('processo'):
            processo_id = self.cleaned_data.get('processo').id
        else:
            raise forms.ValidationError('Processo não encontrado.')

        processo = ProcessoTitular.objects.get(id=processo_id)
        motivo_recusa = self.cleaned_data.get('motivo_recusa')
        if not motivo_recusa or motivo_recusa == '':
            raise Exception('O motivo da rejeição deve ser preenchido.')
        else:
            validacaoCPPD = ValidacaoCPPD()
            validacaoCPPD.acao = validacaoCPPD.ACAO_REJEITAR
            validacaoCPPD.processo = processo
            validacaoCPPD.validador = self.request.user.get_relacionamento()
            validacaoCPPD.motivo_rejeicao = motivo_recusa
            validacaoCPPD.save()
            processo.status = ProcessoTitular.STATUS_REJEITADO
            processo.save()


class DataConcessaoTitulacaoDoutorForm(forms.FormPlus):
    arquivo = forms.AjaxFileUploadField('/professor_titular/professor_titular_upload_documentos_exigidos/', 'onCompleteUploadDataTitulacaoDoutor', multiple=False)

    def __init__(self, *args, **kwargs):
        processo = kwargs.pop('processo')
        super(DataConcessaoTitulacaoDoutorForm, self).__init__(*args, **kwargs)
        self.fields['arquivo'].widget.request = self.request
        self.fields['arquivo'].widget.params['processo'] = processo.id
        self.fields['arquivo'].widget.params['tipo'] = 'TITULO_DOUTOR'


class DataGraduacaoIngressoEBTTForm(forms.FormPlus):
    arquivo = forms.AjaxFileUploadField('/professor_titular/professor_titular_upload_documentos_exigidos/', 'onCompleteUploadDataGraduacaoIngressoEBTT', multiple=False)

    def __init__(self, *args, **kwargs):
        processo = kwargs.pop('processo')
        super(DataGraduacaoIngressoEBTTForm, self).__init__(*args, **kwargs)
        self.fields['arquivo'].widget.request = self.request
        self.fields['arquivo'].widget.params['processo'] = processo.id
        self.fields['arquivo'].widget.params['tipo'] = 'DIPLOMA_GRADUACAO_EBTT'


class TermoAvaliacaoDesempenhoForm(forms.FormPlus):
    arquivo = forms.AjaxFileUploadField('/professor_titular/professor_titular_upload_documentos_exigidos/', 'onCompleteUploadTermoAvaliacaoDesempenho', multiple=False)

    def __init__(self, *args, **kwargs):
        processo = kwargs.pop('processo')
        super(TermoAvaliacaoDesempenhoForm, self).__init__(*args, **kwargs)
        self.fields['arquivo'].widget.request = self.request
        self.fields['arquivo'].widget.params['processo'] = processo.id
        self.fields['arquivo'].widget.params['tipo'] = 'TERMO_AVALIACAO_DESEMPENHO'


class DeclaracaoDIGPEForm(forms.FormPlus):
    arquivo = forms.AjaxFileUploadField('/professor_titular/professor_titular_upload_documentos_exigidos/', 'onCompleteUploadDeclaraçãoDIGPE', multiple=False)

    def __init__(self, *args, **kwargs):
        processo = kwargs.pop('processo')
        super(DeclaracaoDIGPEForm, self).__init__(*args, **kwargs)
        self.fields['arquivo'].widget.request = self.request
        self.fields['arquivo'].widget.params['processo'] = processo.id
        self.fields['arquivo'].widget.params['tipo'] = 'DECLARACAO_DIGPE'


class ValidacaoCPPDForm(forms.ModelFormPlus):
    processo = forms.ModelChoiceFieldPlus(ProcessoTitular.objects, label='Processo', widget=forms.HiddenInput())
    motivo_rejeicao = forms.CharField(widget=forms.Textarea)

    def __init__(self, *args, **kwargs):
        if 'processo' in kwargs:
            self.processo = kwargs.pop('processo')
        super(ValidacaoCPPDForm, self).__init__(*args, **kwargs)
        if self.processo:
            self.fields['processo'].initial = self.processo

        self.fields['data_conclusao_titulacao_validada'].widget.attrs['disabled'] = 'disabled'
        self.fields['data_graduacao_ebtt_validada'].widget.attrs['disabled'] = 'disabled'
        self.fields['data_progressao_validada'].widget.attrs['disabled'] = 'disabled'
        self.fields['data_avaliacao_desempenho_validada'].widget.attrs['disabled'] = 'disabled'

    class Meta:
        model = ValidacaoCPPD
        exclude = ()


class AvaliadorForm(forms.FormPlus):
    processo = forms.ModelChoiceFieldPlus(ProcessoTitular.objects, label='Processo', widget=forms.HiddenInput())
    avaliador_interno = forms.MultipleModelChoiceFieldPlus(Servidor.objects.docentes_permanentes(), required=False)
    avaliador_externo = forms.MultipleModelChoiceFieldPlus(PrestadorServico.objects.all(), required=False)

    def __init__(self, *args, **kwargs):
        if 'processo' in kwargs:
            self.processo = kwargs.pop('processo')
        super(AvaliadorForm, self).__init__(*args, **kwargs)
        self.fields['avaliador_externo'].queryset = PrestadorServico.objects.filter(vinculo__avaliador__isnull=False, vinculo__avaliador__ativo=True)
        self.fields['avaliador_interno'].queryset = Servidor.objects.docentes_permanentes().exclude(vinculo__avaliador__in=Avaliador.objects.filter(ativo=False))
        if self.processo:
            self.fields['processo'].initial = self.processo.id

    @transaction.atomic
    def processar(self, vinculo):
        if self.cleaned_data.get('processo'):
            processo_id = self.cleaned_data.get('processo').id
        else:
            raise forms.ValidationError('Processo não encontrado.')

        processo = ProcessoTitular.objects.get(id=processo_id)

        '''
        verifica se o avaliador interno já está cadastrado
        '''
        for avaliador_interno in self.cleaned_data.get('avaliador_interno'):
            check_avaliador_interno = Avaliador.objects.filter(vinculo__pessoa=avaliador_interno.pessoa_fisica.pessoa_ptr)
            if not check_avaliador_interno.exists():
                avaliador = Avaliador()
                avaliador.vinculo = avaliador_interno.vinculos.first()
                avaliador.email_contato = avaliador_interno.email
                avaliador.save()
        avaliadores_internos = Avaliador.objects.filter(vinculo__id__in=self.cleaned_data.get('avaliador_interno').values_list('vinculos__id', flat=True))

        count_avaliador_interno = ProcessoAvaliador.objects.filter(processo=processo, status__in=[1, 2, 3], tipo_avaliador=ProcessoAvaliador.AVALIADOR_INTERNO).count()
        for avaliador_interno in avaliadores_internos:
            enviar_email = False
            processoAvaliador = ProcessoAvaliador()
            if count_avaliador_interno == 0:
                processoAvaliador.status = ProcessoAvaliador.AGUARDANDO_ACEITE
                processoAvaliador.data_convite = datetime.today()
                enviar_email = True
            else:
                processoAvaliador.status = ProcessoAvaliador.EM_ESPERA
            processoAvaliador.processo = processo
            processoAvaliador.avaliador = avaliador_interno
            processoAvaliador.tipo_avaliador = ProcessoAvaliador.AVALIADOR_INTERNO
            processoAvaliador.vinculo_responsavel_cadastro = vinculo
            processoAvaliador.save()
            count_avaliador_interno = count_avaliador_interno + 1

            if enviar_email:
                '''
                enviando e-mail para o avaliador selecionado
                '''
                assunto = '[SUAP] Avaliação de Processo Professor Titular'
                mensagem = ProcessoTitular.EMAIL_PROFESSOR_SORTEADO.format(
                    str(avaliador_interno.vinculo.pessoa.nome), str(processo.servidor.pessoa_fisica.nome), str(processoAvaliador.data_limite())
                )

                send_notification(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [avaliador_interno.vinculo])

        '''
        verifica se o avaliador externo já está cadastrado
        '''
        for avaliador_externo in self.cleaned_data.get('avaliador_externo'):
            check_avaliador_externo = Avaliador.objects.filter(vinculo__pessoa=avaliador_externo.pessoa_fisica.pessoa_ptr)
            if not check_avaliador_externo.exists():
                avaliador = Avaliador()
                avaliador.vinculo = avaliador_externo.vinculos.first()
                avaliador.save()

        avaliadores_externos = []
        for id_ae in self.data.getlist('avaliador_externo'):
            ava = Avaliador.objects.get(vinculo__pessoa=id_ae)
            avaliadores_externos.append(ava)

        count_avaliador_externo = ProcessoAvaliador.objects.filter(processo=processo, status__in=[1, 2, 3], tipo_avaliador=ProcessoAvaliador.AVALIADOR_EXTERNO).count()
        for avaliador_externo in avaliadores_externos:
            enviar_email = False
            processoAvaliador = ProcessoAvaliador()
            if count_avaliador_externo < 3:
                processoAvaliador.status = ProcessoAvaliador.AGUARDANDO_ACEITE
                processoAvaliador.data_convite = datetime.today()
                enviar_email = True
            else:
                processoAvaliador.status = ProcessoAvaliador.EM_ESPERA
            processoAvaliador.processo = processo
            processoAvaliador.avaliador = avaliador_externo
            processoAvaliador.tipo_avaliador = ProcessoAvaliador.AVALIADOR_EXTERNO
            processoAvaliador.vinculo_responsavel_cadastro = vinculo
            processoAvaliador.save()
            count_avaliador_externo = count_avaliador_externo + 1

            if enviar_email:
                '''
                enviando e-mail para o avaliador selecionado
                '''
                assunto = '[SUAP] Avaliação de Processo Professor Titular'
                mensagem = ProcessoTitular.EMAIL_PROFESSOR_SORTEADO.format(
                    str(avaliador_externo.vinculo.pessoa.nome), str(processo.servidor.nome), str(processoAvaliador.data_limite())
                )
                send_notification(assunto, mensagem, settings.DEFAULT_FROM_EMAIL, [avaliador_externo.vinculo])

        '''
        mudando status do processo
        '''
        if processo.status != ProcessoTitular.STATUS_EM_AVALIACAO:
            processo.status = ProcessoTitular.STATUS_AGUARDANDO_ACEITE_AVALIADOR
        processo.save()

    def clean_avaliador_interno(self):
        '''
        validando avaliadores internos
        '''
        avaliadores_internos = self.cleaned_data.get('avaliador_interno')
        if self.processo.servidor in avaliadores_internos:
            raise forms.ValidationError('Você não pode escolhe o próprio avaliado (%s) com sendo um avaliador.' % self.processo.servidor)

        return avaliadores_internos


class RecusaAvaliacaoForm(forms.FormPlus):
    processo_avaliador = forms.ModelChoiceFieldPlus(ProcessoAvaliador.objects, label='Processo Avaliador', widget=forms.HiddenInput())
    tipo = forms.ChoiceField(label='Tipo', choices=ProcessoAvaliador.TIPO_RECUSA_CHOICES)
    motivo_recusa = forms.CharFieldPlus(label='Motivo da Recusa', max_length=10000, widget=forms.Textarea())

    def __init__(self, *args, **kwargs):
        if 'processo_avaliador' in kwargs:
            self.processo_avaliador = kwargs.pop('processo_avaliador')
        super(RecusaAvaliacaoForm, self).__init__(*args, **kwargs)
        if self.processo_avaliador:
            self.fields['processo_avaliador'].initial = self.processo_avaliador.id

    @transaction.atomic
    def processar(self):
        if self.cleaned_data.get('processo_avaliador'):
            processo_id = self.cleaned_data.get('processo_avaliador').id
        else:
            raise forms.ValidationError('Processo Avaliador não setado!')
        processo_avaliador = ProcessoAvaliador.objects.get(id=processo_id)
        processo_avaliador.rejeitar(self.cleaned_data)


class JustificativaDesistenciaForm(forms.FormPlus):
    avaliacao = forms.ModelChoiceFieldPlus(Avaliacao.objects, label='Avaliação', widget=forms.HiddenInput())
    tipo = forms.ChoiceField(label='Tipo', choices=Avaliacao.TIPO_DESISTENCIA_CHOICES)
    justificativa = forms.CharFieldPlus(max_length=10000, widget=forms.Textarea())

    def __init__(self, *args, **kwargs):
        if 'avaliacao' in kwargs:
            self.avaliacao = kwargs.pop('avaliacao')
        super(JustificativaDesistenciaForm, self).__init__(*args, **kwargs)
        if self.avaliacao:
            self.fields['avaliacao'].initial = self.avaliacao.id


class ProcessoPagamentoForm(forms.FormPlus):
    SUBMIT_LABEL = 'Filtrar'
    METHOD = 'GET'

    TODAS = '0'
    AVALIACOES_PAGAS = '1'
    AVALIACOES_NAO_PAGAS = '2'
    TIPO_AVALIACAO_CHOICES = [[TODAS, 'Todas as Avaliações'], [AVALIACOES_PAGAS, 'Com Avaliações Pagas'], [AVALIACOES_NAO_PAGAS, 'Com Avaliações Não Pagas']]

    avaliadores_pagamento_avaliacao = forms.ChoiceField(label='Avaliadores com:', required=False, choices=TIPO_AVALIACAO_CHOICES)
    avaliador = forms.CharFieldPlus(label='Avaliador', max_length=1000, required=False)
    interessado = forms.CharFieldPlus(label='Interessado', max_length=1000, required=False)

    fieldsets = (('Filtros de Pesquisa', {'fields': ('avaliador', 'interessado', 'avaliadores_pagamento_avaliacao')}),)


class RelatorioPagamentoForm(forms.FormPlus):
    avaliacao_paga = forms.BooleanField(label='Apenas Avaliações Pagas', required=False)
    data_inicio = forms.DateFieldPlus(label='Data de Incício', required=False)
    data_final = forms.DateFieldPlus(label='Data Final', required=False)

    SUBMIT_LABEL = 'Filtrar'
    METHOD = 'GET'

    fieldsets = (('Filtros de Pesquisa', {'fields': (('avaliacao_paga'), ('data_inicio', 'data_final'))}),)

    def clean_data_inicio(self):
        data = self.cleaned_data.get('data_inicio')
        if not data:
            raise forms.ValidationError("Por favor, defina um período para a consulta.")
        return data

    def clean_data_final(self):
        data = self.cleaned_data.get('data_final')
        if not data:
            raise forms.ValidationError("Por favor, defina um período para a consulta.")
        return data


class ProcessoProfessorTitularForm(forms.ModelFormPlus):
    servidor = forms.ModelChoiceField(required=False, queryset=Servidor.objects, widget=AutocompleteWidget(search_fields=Servidor.SEARCH_FIELDS))
    protocolo = forms.ModelChoiceField(required=False, queryset=Processo.objects, widget=AutocompleteWidget())

    class Meta:
        model = ProcessoTitular
        exclude = ()


class ProcessoAvaliadorForm(forms.ModelFormPlus):
    processo = forms.ModelChoiceField(required=False, queryset=ProcessoTitular.objects, widget=AutocompleteWidget(search_fields=ProcessoTitular.SEARCH_FIELDS))
    avaliador = forms.ModelChoiceField(required=False, queryset=Avaliador.objects, widget=AutocompleteWidget(search_fields=Avaliador.SEARCH_FIELDS))

    class Meta:
        model = ProcessoAvaliador
        exclude = ()


class AvaliacaoForm(forms.ModelFormPlus):
    processo = forms.ModelChoiceField(required=False, queryset=ProcessoTitular.objects, widget=AutocompleteWidget(search_fields=ProcessoTitular.SEARCH_FIELDS))
    avaliador = forms.ModelChoiceField(required=False, queryset=Avaliador.objects, widget=AutocompleteWidget(search_fields=Avaliador.SEARCH_FIELDS))

    class Meta:
        model = Avaliacao
        exclude = ('motivo_indeferimento',)


class AssinaturaRequerimentoForm(SuapAssinaturaForm):
    assinatura_field_exibir = False
