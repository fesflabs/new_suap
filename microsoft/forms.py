# -*- coding: utf-8 -*-

from djtools import forms
from edu.models import CursoCampus
from microsoft.models import ConfiguracaoAcessoDreamspark


class ConfiguracaoForm(forms.FormPlus):
    dreamspark_account = forms.CharField(label='Registro Dreamspark', help_text='Número da conta do instituto para acessar o site da Microsoft', required=False)
    dreamspark_key = forms.CharField(label='Chave Dreamspark', help_text='Número da chave do instituto para se conectar ao site da Microsoft', required=False)
    dreamspark_url = forms.CharField(label='URL Dreamspark', help_text='Endereço para autenticação do usuário', required=False)


class ConfiguracaoAcessoDreamsparkForm(forms.ModelFormPlus):
    class Meta:
        model = ConfiguracaoAcessoDreamspark
        exclude = ()

    cursos = forms.MultipleModelChoiceFieldPlus(required=False, queryset=CursoCampus.objects)
