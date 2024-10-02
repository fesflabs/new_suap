# pylint: skip-file
from djtools.lps import MetaFormPlus, MetaModelFormPlus
from djtools.forms.widgets import AutocompleteWidget
import datetime
from django.contrib.auth.models import Group, Permission
from django.contrib import auth
from django.forms import modelformset_factory
from django.forms.models import BaseModelFormSet
from django.conf import settings
from django import forms

assert forms
from django.forms import *  # NOQA
from djtools.forms.fields import *  # NOQA
from djtools.forms.widgets import *  # NOQA
from djtools.forms.utils import *  # NOQA
from djtools.forms.fields import JSONSchemaField  # NOQA


class NonrelatedInlineFormSet(BaseModelFormSet):
    """
    A basic implementation of an inline formset that doesn't make assumptions
    about any relationship between the form model and its parent instance.
    """

    def __init__(self, instance=None, save_as_new=None, **kwargs):
        self.instance = instance
        super().__init__(**kwargs)
        self.queryset = self.real_queryset

    @classmethod
    def get_default_prefix(cls):
        opts = cls.model._meta
        return (opts.app_label + '-' + opts.model_name)

    def save_new(self, form, commit=True):
        obj = super().save_new(form, commit=False)
        self.save_new_instance(self.instance, obj)
        if commit:
            obj.save()
        return obj


def nonrelated_inlineformset_factory(model, obj=None, queryset=None, formset=NonrelatedInlineFormSet, save_new_instance=None, **kwargs):
    """
    FormSet factory that sets an explicit queryset on new classes.
    """
    FormSet = modelformset_factory(model, formset=formset, **kwargs)
    FormSet.real_queryset = queryset
    FormSet.save_new_instance = save_new_instance
    return FormSet


class FormPlus(forms.Form, metaclass=MetaFormPlus):
    """
    Torna o ``request`` disponível no ``FormPlus`` através de ``self.request`` quando passado como parêmetro no inicialização.
    """

    def __init__(self, *args, **kwargs):
        if 'request' in kwargs:
            self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)


class ModelFormPlus(forms.ModelForm, metaclass=MetaModelFormPlus):
    # class ModelFormPlus(forms.ModelForm):
    """
    Torna o ``request`` disponível no ``ModelFormPlus`` através de ``self.request`` quando passado como parêmetro no inicialização.
    """

    def __init__(self, *args, **kwargs):
        if 'request' in kwargs:
            self.request = kwargs.pop('request')
        super().__init__(*args, **kwargs)


"""
    Form de confirmação de ação base para ser usado como herança nos forms que exijam confirmacão.
"""


class ConfirmacaoAcaoForm(FormPlus):
    confirmar = forms.BooleanField(required=True)

    def __init__(self, *args, **kwargs):
        label = 'Confirma a operação?'
        if 'label' in kwargs:
            label = kwargs.pop('label')
        super().__init__(*args, **kwargs)
        self.fields['confirmar'].label = label


"""
    Form de confirmação de ação com senha base para ser usado como herança nos forms que exijam confirmacão.
"""


class ConfirmacaoAcaoComSenhaForm(ConfirmacaoAcaoForm):
    senha = forms.CharField(label='Senha para confirmar', widget=forms.PasswordInput)

    def clean(self):
        cleaned_data = super().clean()

        if 'confirmar' in cleaned_data and cleaned_data['confirmar']:
            if not auth.authenticate(username=self.request.user.username, password=cleaned_data['senha']):
                raise forms.ValidationError('A senha não confere com a do usuário logado.')

        return cleaned_data


# Forms específicos


class AtribuirPermissaoForm(FormPlus):
    usuarios = forms.CharField(label='Usuários', required=True, widget=forms.Textarea(), help_text='Lista de username separada por ; ou , ou quebra de linha')
    grupos = forms.ModelMultipleChoiceField(Group.objects.all(), widget=AutocompleteWidget(multiple=True), required=False)
    permissoes = forms.ModelMultipleChoiceField(Permission.objects.all(), widget=AutocompleteWidget(multiple=True), label='Permissões', required=False)


class NotificacaoGrupoForm(FormPlus):
    titulo = forms.CharField(label="Título", required=True, initial='Mensagem para Grupo')
    remetente = forms.CharField(label="E-mail", required=True, help_text='E-mail do remetente', initial=settings.DEFAULT_FROM_EMAIL)
    texto = forms.CharField(
        widget=forms.Textarea({'rows': 10, 'cols': 80}), required=True, label='Mensagem', help_text='Pode conter quebras de linha, porém não deve conter tags HTML.'
    )

    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if not self.request.user.is_superuser:
            self.fields['remetente'].initial = self.request.user.get_profile().email
            self.fields['remetente'].widget.attrs['readonly'] = True
            self.fields['remetente'].widget.attrs['disabled'] = True


class MultiFileForm(FormPlus):
    files = MultiFileField(max_num=10, min_num=2, max_file_size=1024 * 1024 * 5)  # NOQA

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def clean_files(self):
        print('clean_files ')
        content = self.cleaned_data['files']
        print('clean_files cleaned_data: %s' % content)


class ConfiguracaoForm(FormPlus):
    url_token_conecta_gov_br = forms.CharField(
        label='Url para obter Token - Conecta Gov.BR', required=False,
        help_text='Em homologação: https://h-apigateway.conectagov.estaleiro.serpro.gov.br/oauth2/jwt-token'
    )
    url_api_conecta_gov_br = forms.CharField(
        label='Url Base da API Gateway - Conecta Gov.BR', required=False,
        help_text='Em homologação: https://h-apigateway.conectagov.estaleiro.serpro.gov.br/ |'
                  'Em produção: https://apigateway.conectagov.estaleiro.serpro.gov.br/'
    )
    client_id_api_cep_gov_br = forms.CharField(
        label='Client ID da API de CEP - Gov.BR', required=False
    )
    client_secret_api_cep_gov_br = forms.CharField(
        label='Client Secret da API de CEP - Gov.BR', required=False
    )
    cpf_operador_api_cep_gov_br = forms.CharField(
        label='CPF do Operador da API de CEP - Gov.BR', required=False
    )

    client_id_api_cpf_gov_br = forms.CharField(
        label='Client ID da API de CPF - Gov.BR', required=False
    )
    client_secret_api_cpf_gov_br = forms.CharField(
        label='Client Secret da API de CPF - Gov.BR', required=False
    )

    client_id_api_cnpj_gov_br = forms.CharField(
        label='Client ID da API de CNPJ - Gov.BR', required=False
    )
    client_secret_api_cnpj_gov_br = forms.CharField(
        label='Client Secret da API de CNPJ - Gov.BR', required=False
    )
    client_id_api_quitacaoeleitoral_gov_br = forms.CharField(
        label='Client ID da API de Quitação Eleitoral - Gov.BR', required=False
    )
    client_secret_quitacaoeleitoral_gov_br = forms.CharField(
        label='Client Secret da API de Quitação Eleitoral - Gov.BR', required=False
    )
    nome_sistema_quitacaoeleitoral_gov_br = forms.CharField(
        label='Nome do Sistema cadastrado - API de Quitação Eleitoral - Gov.BR', required=False
    )


class TwoFactorAuthenticationForm(forms.Form):

    code = forms.IntegerField(required=True, label='Código')

    SUBMIT_LABEL = 'Autenticar'

    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)
        # mascarando o e-mail secundário (x******y@email.com)
        email = list(request.user.get_vinculo().pessoa.email_secundario or '')
        if '@' in email:
            for i in range(1, email.index('@') - 1):
                email[i] = '*'
            email = ''.join(email)
        self.fields['code'].help_text = (
            f'Informe o código de autenticação com 6 dígitos enviado para "{email}" com validade de 5 minutos.'
        )

    def clean_code(self):
        from djtools.models import TwoFactorAuthenticationCode
        from djtools.forms.fields.captcha import ReCaptchaField
        qs = TwoFactorAuthenticationCode.objects.filter(
            user=self.request.user, expires__gte=datetime.datetime.now(),
            code=self.cleaned_data['code']
        )
        if qs.exists():
            return self.cleaned_data['code']
        else:
            # sinalizando na seção que o código foi informado errado para que o recaptcha seja exibido
            self.request.session['2fa'] = 0
            self.request.session.save()
            self.fields['recaptcha'] = ReCaptchaField(label='')
            raise forms.ValidationError('Código de autenticação inválido')


class JSONSchemaForm(forms.Form):

    def __init__(self, schema, options, ajax=True, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['json'] = JSONSchemaField(schema=schema, options=options, ajax=ajax)
