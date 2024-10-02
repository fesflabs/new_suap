# -*- coding: utf-8 -*-
from djtools import forms
from djtools.forms.widgets import CheckboxSelectMultiplePlus
from rh.models import UnidadeOrganizacional
from temp_rh2.models import CompeticaoDesportiva, ModalidadeDesportiva, InscricaoCompeticaoDesportiva, Prova, Categoria
from django.contrib import auth


class CompeticoesDesportivasForm(forms.ModelFormPlus):
    modalidades = forms.ModelMultipleChoiceField(label='Modalidades', queryset=ModalidadeDesportiva.objects.all(), widget=CheckboxSelectMultiplePlus())
    categorias = forms.ModelMultipleChoiceField(label='Categorias', queryset=Categoria.objects.filter(excluido=False), widget=CheckboxSelectMultiplePlus())
    provas_natacao = forms.ModelMultipleChoiceField(
        label='Provas da Natação', queryset=Prova.objects.filter(modalidade__pk=ModalidadeDesportiva.CODIGO_NATACAO), widget=CheckboxSelectMultiplePlus()
    )
    provas_atletismo = forms.ModelMultipleChoiceField(
        label='Provas do Atletismo', queryset=Prova.objects.filter(modalidade__pk=ModalidadeDesportiva.CODIGO_ATLETISMO), widget=CheckboxSelectMultiplePlus()
    )
    provas_jogos_eletronicos = forms.ModelMultipleChoiceField(
        label='Provas dos Jogos Eletônicos', queryset=Prova.objects.filter(modalidade__pk=ModalidadeDesportiva.CODIGO_JOGOS_ELETRONICOS), widget=CheckboxSelectMultiplePlus()
    )
    uo = forms.ModelChoiceField(label='UO', required=False, queryset=UnidadeOrganizacional.objects.suap().all(), empty_label='Todos')

    def __init__(self, *args, **kwargs):
        super(CompeticoesDesportivasForm, self).__init__(*args, **kwargs)
        self.fields['data_inicio_periodo1_jogos'].required = True
        self.fields['data_fim_periodo1_jogos'].required = True
        if 'instance' in kwargs:
            competicao_desportiva = kwargs['instance']
            if competicao_desportiva:
                self.fields['categorias'].queryset = (competicao_desportiva.categorias.all() | Categoria.objects.filter(excluido=False)).distinct()

    class Meta:
        model = CompeticaoDesportiva
        exclude = ()


def GetInscricaoCompeticaoDesportivaForm(inscricao_desportiva=None, servidor=None, request=None):
    indice = 5
    if servidor.sexo == 'M':
        indice = 1
    elif servidor.sexo == 'F':
        indice = 2
    queryset_modalidades = ModalidadeDesportiva.objects.filter(sexo__in=[indice, 3, 4])
    queryset_provas_atletismo = Prova.objects.none()
    queryset_provas_natacao = Prova.objects.none()
    queryset_provas_jogos_eletronicos = Prova.objects.none()
    if inscricao_desportiva and inscricao_desportiva.competicao_desportiva:
        queryset_modalidades = inscricao_desportiva.competicao_desportiva.modalidades.filter(sexo__in=[indice, 3, 4])
        if inscricao_desportiva.competicao_desportiva.modalidades.filter(pk=ModalidadeDesportiva.CODIGO_ATLETISMO).exists():
            queryset_provas_atletismo = inscricao_desportiva.competicao_desportiva.provas_atletismo.all()
        if inscricao_desportiva.competicao_desportiva.modalidades.filter(pk=ModalidadeDesportiva.CODIGO_NATACAO).exists():
            queryset_provas_natacao = inscricao_desportiva.competicao_desportiva.provas_natacao.all()
        if inscricao_desportiva.competicao_desportiva.modalidades.filter(pk=ModalidadeDesportiva.CODIGO_JOGOS_ELETRONICOS).exists():
            queryset_provas_jogos_eletronicos = inscricao_desportiva.competicao_desportiva.provas_jogos_eletronicos.all()

    class InscricaoCompeticaoDesportivaForm(forms.ModelFormPlus):
        uo = forms.ModelChoiceField(
            label='Confirme seu Campus:',
            queryset=UnidadeOrganizacional.objects.suap(),
            help_text='Em caso de remanejamento do servidor após efetuada a inscrição,\
                        enquanto estivermos no prazo de inscrição dos jogos, o servidor poderá optar pelo novo campus de lotação.',
        )
        modalidades = forms.ModelMultipleChoiceField(
            label='Escolha as modalidades que deseja participar:', queryset=queryset_modalidades.order_by('-tipo', 'nome'), widget=CheckboxSelectMultiplePlus()
        )

        provas_natacao = forms.ModelMultipleChoiceField(
            label='Escolha as provas de natação:', queryset=queryset_provas_natacao, widget=CheckboxSelectMultiplePlus(), required=False
        )
        provas_atletismo = forms.ModelMultipleChoiceField(
            label='Escolha as provas de atletismo:', queryset=queryset_provas_atletismo, widget=CheckboxSelectMultiplePlus(), required=False
        )
        provas_jogos_eletronicos = forms.ModelMultipleChoiceField(
            label='Escolha as provas dos jogos eletrônicos:', queryset=queryset_provas_jogos_eletronicos, widget=CheckboxSelectMultiplePlus(), required=False
        )

        fieldsets = (
            (
                '',
                {
                    'fields': (
                        'uo',
                        'termo_recebimento_hospedagem',
                        'modalidades',
                        'provas_natacao',
                        'provas_atletismo',
                        'provas_jogos_eletronicos',
                        'preferencia_camisa',
                        'preferencia_short',
                        'termo_aceitacao_exame',
                        'atestado_medico',
                    )
                },
            ),
        )

        class Media:
            js = ('/static/temp_rh2/js/ShowHideProvas.js',)

        class Meta:
            model = InscricaoCompeticaoDesportiva
            exclude = (
                'servidor',
                'categoria',
                'competicao_desportiva',
                'situacao',
                'validado_por',
                'homologado_por',
                'rejeitado_por',
                'validado_em',
                'homologado_em',
                'rejeitado_em',
                'observacao_rejeicao',
            )

        def __init__(self, *args, **kwargs):
            if kwargs.get('instance') and kwargs.get('instance').pk:
                initial = kwargs.setdefault('initial', {})
                initial['modalidades'] = [modalidade.pk for modalidade in kwargs['instance'].modalidades.all()]
                initial['provas_natacao'] = [prova_natacao.pk for prova_natacao in kwargs['instance'].provas_natacao.all()]
                initial['provas_atletismo'] = [prova_atletismo.pk for prova_atletismo in kwargs['instance'].provas_atletismo.all()]
                initial['provas_jogos_eletronicos'] = [prova_jogos_eletronicos.pk for prova_jogos_eletronicos in kwargs['instance'].provas_jogos_eletronicos.all()]

            super(InscricaoCompeticaoDesportivaForm, self).__init__(*args, **kwargs)

        def clean_termo_aceitacao_exame(self):
            if 'termo_aceitacao_exame' in self.cleaned_data and self.cleaned_data['termo_aceitacao_exame']:
                return self.cleaned_data['termo_aceitacao_exame']
            raise forms.ValidationError('Inscrição só pode ser realizada após a marcação do termo de aceitação.')

        def clean_modalidades(self):
            if 'modalidades' in self.cleaned_data and self.cleaned_data['modalidades']:
                maximo_coletivas = self.instance.competicao_desportiva.max_modalidades_coletivas_por_inscricao
                maximo_individual = self.instance.competicao_desportiva.max_modalidades_individuais_por_inscricao
                maximo_modalidades = self.instance.competicao_desportiva.max_modalidades_por_inscricao
                if self.cleaned_data['modalidades'].all().count() > maximo_modalidades:
                    raise forms.ValidationError('Você não pode escolher mais que {} modalidades'.format(maximo_modalidades))
                if self.cleaned_data['modalidades'].filter(tipo=ModalidadeDesportiva.COLETIVO).count() > maximo_coletivas:
                    raise forms.ValidationError('Você não pode escolher mais que {} modalidades coletivas'.format(maximo_coletivas))
                if self.cleaned_data['modalidades'].filter(tipo=ModalidadeDesportiva.INDIVIDUAL).count() > maximo_individual:
                    raise forms.ValidationError('Você não pode escolher mais que {} modalidades individuais'.format(maximo_individual))

                return self.cleaned_data['modalidades']
            raise forms.ValidationError('Escolha, no minimo, uma modalidade.')

        def clean_termo_recebimento_hospedagem(self):
            if 'termo_recebimento_hospedagem' in self.cleaned_data and self.cleaned_data['termo_recebimento_hospedagem']:
                if hasattr(servidor.endereco_municipio, 'pk') and servidor.endereco_municipio.pk in [9, 44, 8, 25, 17, 11, 2, 89, 1, 21, 318, 77]:
                    raise forms.ValidationError('Servidores da grande Natal não tem direito de receber hospedagem.')
            return self.cleaned_data['termo_recebimento_hospedagem']

        def clean_provas_natacao(self):
            if 'provas_natacao' in self.cleaned_data and self.cleaned_data['provas_natacao']:
                maximo_provas_natacao = self.instance.competicao_desportiva.max_provas_natacao
                if self.cleaned_data['provas_natacao'].count() > maximo_provas_natacao:
                    raise forms.ValidationError('Servidor só poderá escolher até {} provas de natação conforme regulamento.'.format(maximo_provas_natacao))
            return self.cleaned_data['provas_natacao']

        def clean_provas_atletismo(self):
            if 'provas_natacao' in self.cleaned_data and self.cleaned_data['provas_atletismo']:
                maximo_provas_atletismo = self.instance.competicao_desportiva.max_provas_atletismo
                if self.cleaned_data['provas_atletismo'].count() > maximo_provas_atletismo:
                    raise forms.ValidationError('Servidor só poderá escolher até {} provas de atletismo conforme regulamento.'.format(maximo_provas_atletismo))
            return self.cleaned_data['provas_atletismo']

        def clean_provas_jogos_eletronicos(self):
            if 'provas_jogos_eletronicos' in self.cleaned_data and self.cleaned_data['provas_jogos_eletronicos']:
                maximo_provas_jogos_eletronicos = self.instance.competicao_desportiva.max_provas_jogos_eletronicos
                if self.cleaned_data['provas_jogos_eletronicos'].count() > maximo_provas_jogos_eletronicos:
                    raise forms.ValidationError('Servidor só poderá escolher até {} provas de jogos eletronicos conforme regulamento.'.format(maximo_provas_jogos_eletronicos))
            return self.cleaned_data['provas_jogos_eletronicos']

        def clean(self):
            if not self.cleaned_data.get('atestado_medico') and self.cleaned_data.get('modalidades'):
                modalidades = self.cleaned_data.get('modalidades')
                if modalidades.exclude(exige_atestado=False).exists():
                    raise forms.ValidationError('Servidor só poderá realizar a inscrição se anexar um atestado médico.')
            return self.cleaned_data

    return InscricaoCompeticaoDesportivaForm


class ModalidadeDesportivaForm(forms.ModelFormPlus):
    class Meta:
        model = ModalidadeDesportiva
        exclude = ()


def GetValidacaoInscricaoCompeticaoDesportivaForm(inscricao_desportiva=None, etapa="validacao"):
    SITUACAO_CHOICES_FORMULARIO = ((2, 'Validar Inscrição'), (4, 'Rejeitar Inscrição'))
    if etapa == "homologacao":
        SITUACAO_CHOICES_FORMULARIO = ((3, 'Homologar Inscrição'), (4, 'Rejeitar Inscrição'))

    class ValidarInscricaoCompeticaoDesportivaForm(forms.ModelFormPlus):

        situacao = forms.ChoiceField(label='Ação:', choices=SITUACAO_CHOICES_FORMULARIO, required=True, widget=forms.RadioSelect)

        def __init__(self, *args, **kwargs):
            super(ValidarInscricaoCompeticaoDesportivaForm, self).__init__(*args, **kwargs)

        class Meta:
            model = InscricaoCompeticaoDesportiva
            exclude = (
                'servidor',
                'atestado_medico',
                'uo',
                'provas_atletismo',
                'provas_natacao',
                'provas_jogos_eletronicos',
                'termo_recebimento_diaria',
                'preferencia_camisa',
                'categoria',
                'preferencia_short',
                'termo_aceitacao_exame',
                'termo_recebimento_hospedagem',
                'competicao_desportiva',
                'modalidades',
                'validado_por',
                'homologado_por',
                'rejeitado_por',
                'validado_em',
                'homologado_em',
                'rejeitado_em',
            )

        class Media:
            js = ('/static/temp_rh2/js/RejeitarInscricaoCompeticao.js',)

        def clean(self):
            if not self.cleaned_data.get('situacao'):
                raise forms.ValidationError('Corrija os erros abaixo.')
            if self.cleaned_data['situacao'] == "4" and self.cleaned_data['observacao_rejeicao'] == "":
                raise forms.ValidationError('Descreva o motivo para a rejeição da inscrição.')
            return self.cleaned_data

    return ValidarInscricaoCompeticaoDesportivaForm


class FormConfirmaInscricaoCursoSuap(forms.Form):
    senha = forms.CharField(label='Senha para confirmar', widget=forms.PasswordInput)
    confirmar = forms.BooleanField(label='Confirmar')

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request')
        super(FormConfirmaInscricaoCursoSuap, self).__init__(*args, **kwargs)

    def clean(self):
        cleaned_data = super(FormConfirmaInscricaoCursoSuap, self).clean()

        if 'confirmar' in cleaned_data and cleaned_data['confirmar']:
            if not auth.authenticate(username=self.request.user.username, password=cleaned_data['senha']):
                raise forms.ValidationError('A senha não confere com a do usuário logado.')

        return cleaned_data
