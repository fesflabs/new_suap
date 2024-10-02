from comum.models import Municipio, User
from djtools import forms
from djtools.forms import AutocompleteWidget
from djtools.forms.widgets import TreeWidget
from rh.forms import ServidorInformacoesPessoaisForm
from rh.models import CargoEmprego, Setor, Servidor
from rh.enums import Nacionalidade
import re


'''
O formulário "CargoEmpregoForm" herda direto de ModelForm por que esse formulário não existia originalmente no forms.py
e para a LPS foi redefinido no CargoEmpregoAdmin 
'''


class CargoEmpregoForm(forms.ModelFormPlus):

    class Meta:
        model = CargoEmprego
        exclude = ['excluido']
