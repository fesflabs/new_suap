from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

ACTION_CHECKBOX_NAME = '_selected_action'


class ActionForm(forms.Form):
    action = forms.ChoiceField(label=_('Action:'), required=False)
    select_across = forms.BooleanField(
        label='',
        required=False,
        initial=0,
        widget=forms.HiddenInput({'class': 'select-across'}),
    )

    def clean_action(self):
        action = self.data['action']
        if not action:
            raise ValidationError('Por favor escolha alguma ação.')
        return self.data['action']
