# -*- coding: utf-8 -*-
import ldap
from djtools import forms
from djtools.forms.fields.captcha import ReCaptchaField
from djtools.utils import to_ascii
from .models import LdapConf, LdapGroup, LdapUser


class SearchForm(forms.FormPlus):
    tipo = forms.ChoiceField(choices=[['busca_rapida', 'Busca Rápida'], ['busca_detalhada', 'Busca Detalhada']], label='')
    filtro = forms.CharField(required=False, label='', widget=forms.TextInput(attrs=dict(size=100)))

    def mount_user_attrlist(self, ldap_conf):
        args = dict()
        if type(ldap_conf.filterstr) == str:
            args = dict(attrlist=[ldap_conf.filterstr, 'givenName', 'sn', 'mail', 'cn'])
        elif type(ldap_conf.filterstr) == list:
            args = dict(attrlist=ldap_conf.filterstr + ['givenName', 'sn', 'mail', 'cn'])
        return args

    def extract_filterstr(self):
        if self.cleaned_data['tipo'] == 'busca_rapida':
            return {'q': self.cleaned_data['filtro']}
        elif self.cleaned_data['tipo'] == 'busca_detalhada':
            return {'filterstr': self.cleaned_data['filtro']}

    def raw_search(self, ldap_conf):
        try:
            search_fields = self.mount_user_attrlist(ldap_conf)
            search_fields.update(self.extract_filterstr())
            return ldap_conf.search_objects(**search_fields)
        except ldap.LDAPError:
            raise forms.ValidationError(f"O filtro {self.cleaned_data['filtro']} é inválido")
        except Exception:
            raise forms.ValidationError("Aconteceu um erro no processamento")

    def search(self):
        try:
            if self.cleaned_data['tipo'] == 'busca_rapida':
                return LdapUser.objects.filter_by_query(self.cleaned_data['filtro'])
            elif self.cleaned_data['tipo'] == 'busca_detalhada':
                return LdapUser.objects.filter_by_filtestr(self.cleaned_data['filtro'])
            else:
                raise forms.ValidationError(f"O tipo de busca: {self.cleaned_data['tipo']} é inválido.")
        except Exception as e:
            raise forms.ValidationError(f"Aconteceu um erro no processamento da requisição {e}.")

    def clean(self):
        cleaned_data = super().clean()
        tipo = cleaned_data.get('tipo')
        filtro = cleaned_data.get('filtro')
        if (tipo == "busca_detalhada") and ("=" not in filtro):
            msg = f"O filtro {self.cleaned_data['filtro']} é inválido para a busca detalhada."
            self.add_error('filtro', msg)
        return cleaned_data


class ChangePasswordForm(forms.FormPlus):
    password = forms.CharField(max_length=100, widget=forms.PasswordInput, label='Senha')
    password_confirm = forms.CharField(max_length=100, widget=forms.PasswordInput, label='Confirmação de senha')

    def __init__(self, *args, **kwargs):
        self.username = kwargs.pop('username')
        super(ChangePasswordForm, self).__init__(*args, **kwargs)

    def clean_password_confirm(self):
        if self.cleaned_data.get('password') != self.cleaned_data.get('password_confirm'):
            raise forms.ValidationError('A confirmação de senha não é igual à senha.')
        if self.cleaned_data.get('password') != to_ascii(self.cleaned_data.get('password')):
            raise forms.ValidationError('A senha não pode ter caracteres com acentuação.')
        if len(self.cleaned_data.get('password')) < 7:
            raise forms.ValidationError('A senha deve ter pelo menos 7 caracteres.')

        ldap_conf = LdapConf.get_active()
        passwd_result = ldap_conf.change_password(self.username, self.cleaned_data['password'])
        if not passwd_result:
            raise forms.ValidationError('Problema ao definir senha. Certifique-se ' 'que a senha atenda aos requisitos necessários.')
        return self.cleaned_data['password']


class TrocarSenhaForm(ChangePasswordForm):
    recaptcha = ReCaptchaField(label='')


class ConfiguracaoForm(forms.FormPlus):
    dominio_institucional = forms.CharFieldPlus(label='Domínio do email Institucional', help_text='Ex: ifrn.edu.br', required=False)
    dominio_academico = forms.CharFieldPlus(label='Domínio do email Acadêmico', help_text='Ex: academico.ifrn.edu.br', required=False)
    dominio_google_classroom = forms.CharFieldPlus(label='Domínio do email Google Classroom', help_text='Ex: escolar.ifrn.edu.br', required=False)
    url_saml2idp = forms.CharFieldPlus(label='URL do SAML2IDP', help_text='Ex: http://saml2idp.ifrn.local', required=False)
    utilizar_saml2idp_outra_maquina = forms.BooleanField(label='Utilizar SAML2IDP em outra máquina?', required=False)
    utilizar_senha_randomica = forms.BooleanField(label='Utilizar senha randômica para novos usuários?', required=False)

    utilizar_autenticacao_via_ldap = forms.BooleanField(
        label='Utilizar Autenticação via LDAP/AD?', initial=True, required=False,
        help_text='Deixe marcado caso queira logar no usando o seu LDAP/AD.'
    )


class SelecaoEmailForm(forms.FormPlus):
    email = forms.ChoiceField(label='E-mail', choices=())

    def __init__(self, usuario, tipo_dominio, *args, **kwargs):
        self.usuario = usuario
        self.tipo_dominio = tipo_dominio
        emails_disponiveis = usuario.get_emails_disponiveis(tipo=tipo_dominio)
        self.base_fields['email'].choices = list(zip(emails_disponiveis, emails_disponiveis))
        super(SelecaoEmailForm, self).__init__(*args, **kwargs)

    def clean_email(self):
        # Pode ser que um outro usuário escolheu o mesmo email antes que esse usuário submeteu o form
        if self.cleaned_data['email'] not in self.usuario.get_emails_disponiveis(tipo=self.tipo_dominio):
            raise forms.ValidationError('O email %s não está disponível' % self.cleaned_data['email'])
        return self.cleaned_data['email']


class LdapUserForm(forms.ModelFormPlus):
    class Meta:
        model = LdapUser
        fields = ('uid', 'sAMAccountName', 'givenName', 'sn', 'mail')


class LdapGroupForm(forms.ModelFormPlus):
    class Meta:
        model = LdapGroup
        fields = ('name', 'sAMAccountName', 'cn', 'dn')
