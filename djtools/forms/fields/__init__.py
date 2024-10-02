import base64
import os
import re
from decimal import Decimal
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import default_storage
from django.core.validators import EMPTY_VALUES, validate_email
from django.forms.fields import Field
from django.forms.models import ModelChoiceField, ModelMultipleChoiceField
from django.template import Context, Template
from django.template.defaultfilters import filesizeformat
from django.utils.encoding import smart_str
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _
from djtools.choices import STATE_CHOICES
from djtools.forms.widgets import (
    AjaxFileUploadWidget,
    AlphaNumericUpperCaseWidget,
    AlphaNumericWidget,
    AutocompleteWidget,
    BRCpfCnpjWidget,
    BRCpfWidget,
    BRDateRangeWidget,
    BrCepWidget,
    BrCnpjWidget,
    BrDinheiroAlmoxWidget,
    BrDinheiroWidget,
    NotaWidget,
    BrPlacaVeicularWidget,
    BrTelefoneWidget,
    CapitalizeTextWidget,
    ChainedSelectWidget,
    Image,
    IntegerWidget,
    PhotoCaptureInput,
    RegionalDateTimeWidget,
    RegionalDateWidget,
    RegionalTimeWidget,
    SelectMultiplePopup,
    SelectPopup,
    ClearableFileInputPlus,
    JSONEditorWidget,
    NullBooleanSelect, SelectPopupAvaliacao
)
from djtools.utils import mask_cnpj, mask_cpf, mask_placa
import json
import jsonschema


class BooleanRequiredField(forms.BooleanField):
    widget = NullBooleanSelect

    def to_python(self, value):
        """
        Explicitly check for the string 'True' and 'False', which is what a
        hidden field will submit for True and False, for 'true' and 'false',
        which are likely to be returned by JavaScript serializations of forms,
        and for '1' and '0', which is what a RadioField will submit. Unlike
        the Booleanfield, this field must check for True because it doesn't
        use the bool() function.
        """
        if value in (True, 'True', 'true', '1'):
            return True
        elif value in (False, 'False', 'false', '0'):
            return False
        else:
            return None

    def validate(self, value):
        if value is None:
            raise ValidationError(self.error_messages['required'], code='required')


class CharFieldPlus(forms.CharField):
    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 255)
        self._widget_attrs = kwargs.pop('widget_attrs', {})
        if 'width' in kwargs:
            self._widget_attrs['style'] = 'width: %spx;' % kwargs.pop('width')
        super().__init__(*args, **kwargs)

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)
        attrs.update(self._widget_attrs)
        return attrs


class ModelChoiceFieldPlus(forms.ModelChoiceField):
    widget = AutocompleteWidget


class MultipleModelChoiceField(forms.ModelMultipleChoiceField):
    widget = forms.CheckboxSelectMultiple

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.help_text = ''


class MultipleModelChoiceFieldPlus(forms.ModelMultipleChoiceField):

    def __init__(self, *args, **kwargs):
        # Retira o texto `msg` do `help_text`, já que não faz sentido e confunde o usuário, pois o
        # widget é autocomplete e não precisa segurar as teclas control ou command.
        if 'help_text' in kwargs:
            msg = str(_('Hold down "Control", or "Command" on a Mac, to select more than one.'))
            kwargs['help_text'] = str(kwargs['help_text']).replace(msg, '')
        if 'widget' not in kwargs:
            kwargs['widget'] = AutocompleteWidget(multiple=True)
        super().__init__(*args, **kwargs)


class ModelChoiceIteratorPlus:
    """
    Este Iterator foi criado para evitar problemas com cache de choices no
    ``ModelChoiceFieldPlus``.
    """

    def __init__(self, field):
        self.field = field
        self.queryset = field.queryset

    def __iter__(self):
        if self.field.empty_label is not None:
            yield ("", self.field.empty_label)
        if self.field.group_by:
            groups = list(set(self.queryset.values_list(self.field.group_by, flat=True)))
            groups.sort()
            for group in groups:
                group_choices = []
                for obj in self.queryset.filter(**{str(self.field.group_by): group}):
                    group_choices.append([obj.pk, self.field.label_from_instance(obj)])
                yield [str(group), group_choices]
        else:
            for obj in self.queryset.all():
                yield self.choice(obj)

    def choice(self, obj):
        if self.field.to_field_name:
            key = obj.serializable_value(self.field.to_field_name)
        else:
            key = obj.pk
        return (key, self.field.label_from_instance(obj))


class ModelChoiceFieldPlus2(forms.ModelChoiceField):
    """
    Uma versão do forms.ModelChoiceField com 2 novas funcionalidades:

    1) Definição do label_template, que é útil quando se quer mostrar algo diferente
       do tradicional ``unicode``.
       USO: campo = ModelChoiceFieldPlus2(queryset=User.objects.all(), label_template='{{obj.first_name}}')
    2) Definição do group_by, que é útil para montar optgroups baseado num atributo
       dos objetos do queryset
    """

    def __init__(self, queryset, empty_label="---------", required=True, widget=None, label=None, initial=None, help_text=None, to_field_name=None, *args, **kwargs):
        self.label_template = kwargs.pop('label_template', None)
        self.group_by = kwargs.pop('group_by', None)
        super().__init__(
            queryset=queryset,
            empty_label=empty_label,
            required=required,
            widget=widget,
            label=label,
            initial=initial,
            help_text=help_text,
            to_field_name=to_field_name,
            *args,
            **kwargs
        )

    def _get_choices(self):
        if self.group_by:
            return ModelChoiceIteratorPlus(self)
        else:
            return super()._get_choices()

    choices = property(_get_choices, forms.ChoiceField._set_choices)

    def label_from_instance(self, obj):
        if not self.label_template:
            return super().label_from_instance(obj)
        t = Template(self.label_template)
        return mark_safe(t.render(Context({'obj': obj})).replace(' ', '&nbsp;'))


class DateFieldPlus(forms.DateField):
    widget = RegionalDateWidget

    def clean(self, value):
        if value:
            for format in ('%Y-%m-%d', '%d/%m/%Y'):
                try:
                    data = self.strptime(value, format)
                    break
                except (ValueError, TypeError):
                    data = None
                    continue
            if data and data.year < 1900:
                raise forms.ValidationError('O ano precisa ser maior do que 1900.')

        return super().clean(value)


class TimeFieldPlus(forms.TimeField):
    widget = RegionalTimeWidget


class DateTimeFieldPlus(forms.DateTimeField):
    widget = RegionalDateTimeWidget


class FileFieldPlus(forms.FileField):
    """
    Same as FileField, but you can specify:
        * filetypes - list containing allowed content_types. Example: ['pdf', 'png', 'jpg']
        * max_file_size - a number indicating the maximum file size allowed for upload.
            2.5 MB - 2621440
            5   MB - 5242880
            10  MB - 10485760
            20  MB - 20971520
            50  MB - 52428800
            100 MB - 104857600
            250 MB - 262144000
            500 MB - 524288000
    """

    widget = ClearableFileInputPlus

    def __init__(self, *args, **kwargs):
        self.label = kwargs.get('label')
        self.filetypes = kwargs.pop('filetypes', None)
        self.check_mimetype = kwargs.pop('check_mimetype', True)
        self.max_file_size = kwargs.pop('max_file_size', None)
        self.widget_custom_cls = kwargs.pop('widget_custom_cls', ClearableFileInputPlus)
        if not self.max_file_size:
            self.max_file_size = settings.DEFAULT_FILE_UPLOAD_MAX_SIZE
        super().__init__(*args, **kwargs)
        self.widget = self.widget_custom_cls()
        self.widget.max_file_size = self.max_file_size
        self.widget.extensions = self.get_extensions()
        self.widget.mimetypes = self.get_mimetypes()

    def get_extensions(self):
        if self.filetypes:
            ext_whitelist = []
            if 'pdf' in self.filetypes:
                ext_whitelist += ['.pdf', ]
            if 'jpg' in self.filetypes:
                ext_whitelist += ['.jpeg', '.jpg']
            if 'png' in self.filetypes:
                ext_whitelist += ['.png', ]
            if 'xls' in self.filetypes:
                ext_whitelist += ['.xls', ]
            if 'xlsx' in self.filetypes:
                ext_whitelist += ['.xlsx']
            if 'doc' in self.filetypes:
                ext_whitelist += ['.doc', ]
            if 'docx' in self.filetypes:
                ext_whitelist += ['.docx', ]
            if 'csv' in self.filetypes:
                ext_whitelist += ['.csv', ]
            return ext_whitelist

    def get_mimetypes(self):
        if self.filetypes:
            mime_whitelist = []
            if 'pdf' in self.filetypes:
                mime_whitelist += ['application/pdf', ]
            if 'jpg' in self.filetypes:
                mime_whitelist += ['image/jpeg', 'image/pjpeg']
            if 'png' in self.filetypes:
                mime_whitelist += ['image/png', ]
            if 'xls' in self.filetypes:
                mime_whitelist += [
                    'application/vnd.ms-excel',
                    'application/msexcel',
                    'application/x-msexcel',
                    'application/x-ms-excel',
                    'application/x-excel',
                    'application/xls',
                    'application/x-dos_ms_excel',
                    'application/x-xls',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'application/ms-excel',
                ]
            if 'xlsx' in self.filetypes:
                mime_whitelist += [
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                ]
            if 'doc' in self.filetypes or 'docx' in self.filetypes:
                mime_whitelist += [
                    'application/msword',
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                    'application/zip',
                    'multipart/x-zip',
                ]
            if 'csv' in self.filetypes:
                mime_whitelist += ['text/csv', 'text/plain', 'application/vnd.ms-excel']
            return mime_whitelist

    def __setattr__(self, key, value):
        super().__setattr__(key, value)
        if key == 'required':
            self.widget.is_required = value
        if key == 'max_file_size':
            self.widget.max_file_size = value
        if key == 'filetypes':
            self.widget.extensions = self.get_extensions()
            self.widget.mimetypes = self.get_mimetypes()

    def clean(self, *args, **kwargs):
        value = super().clean(*args, **kwargs)
        if value:
            if self.filetypes:
                mime_whitelist = self.get_mimetypes()
                ext_whitelist = self.get_extensions()
                filename = value.name
                try:
                    import magic
                    try:
                        value.seek(0)
                        mime_type = magic.from_buffer(value.read(), mime=True)
                    except magic.MagicException:
                        raise forms.ValidationError('Problemas ao obter o formato do arquivo')
                except ModuleNotFoundError:
                    mime_type = value.content_type
                ext = os.path.splitext(filename)[1].lower()
                if ext not in ext_whitelist or (self.check_mimetype and mime_type not in mime_whitelist):
                    raise forms.ValidationError('O formato do arquivo não é válido. Por favor, envie um arquivo nos formatos: {}.'.format(', '.join(ext_whitelist)))
                value.seek(0)
            if self.max_file_size:
                try:
                    if hasattr(value, 'size') and value.size > int(self.max_file_size):
                        raise forms.ValidationError(
                            f'Por favor mantenha o arquivo com tamanho até {filesizeformat(self.max_file_size)}. Tamanho atual: {filesizeformat(value.size)}.'
                        )
                except Exception:
                    raise ValidationError('Arquivo inválido por favor substitua-o e tente novamente.')
        return value


class PrivateFileField(FileFieldPlus):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        from djtools.storages import get_private_storage

        self.storage = get_private_storage()


class MultiFileField(forms.FileField):
    widget = ClearableFileInputPlus

    default_error_messages = {
        'min_num': "O número mínimo de arquivos deve ser de: %(min_num)s \
            (%(num_files)s arquivos foram submetidos).",
        'max_num': "O SUAP aceita o upload de no máximo  %(max_num)s arquivos\
            por vez (%(num_files)s arquivos foram submetidos).",
        'file_size': "O arquivo: %(uploaded_file_name)s,\
            excede o tamanho máxima de submissão.",
    }

    def __init__(self, *args, **kwargs):
        self.filetypes = kwargs.pop('filetypes', None)
        self.check_mimetype = kwargs.pop('check_mimetype', True)
        self.min_num = kwargs.pop('min_num', 0)
        self.max_num = kwargs.pop('max_num', None)
        self.max_file_size = kwargs.pop('max_file_size', None)
        if not self.max_file_size:
            self.max_file_size = settings.DEFAULT_FILE_UPLOAD_MAX_SIZE
        super().__init__(*args, **kwargs)
        self.widget.max_file_size = self.max_file_size
        self.widget.multiple = True
        self.widget.extensions = self.get_extensions()

    def get_extensions(self):
        if self.filetypes:
            ext_whitelist = []
            if 'pdf' in self.filetypes:
                ext_whitelist += ['.pdf', ]
            if 'jpg' in self.filetypes:
                ext_whitelist += ['.jpeg', '.jpg']
            if 'png' in self.filetypes:
                ext_whitelist += ['.png', ]
            if 'xls' in self.filetypes:
                ext_whitelist += ['.xls', '.xlsx']
            if 'doc' in self.filetypes:
                ext_whitelist += ['.doc', '.docx']
            if 'csv' in self.filetypes:
                ext_whitelist += ['.csv', ]
            return ext_whitelist

    def get_mimetypes(self):
        if self.filetypes:
            mime_whitelist = []
            if 'pdf' in self.filetypes:
                mime_whitelist += ['application/pdf', ]
            if 'jpg' in self.filetypes:
                mime_whitelist += ['image/jpeg', 'image/pjpeg']
            if 'png' in self.filetypes:
                mime_whitelist += ['image/png', ]
            if 'xls' in self.filetypes:
                mime_whitelist += [
                    'application/vnd.ms-excel',
                    'application/msexcel',
                    'application/x-msexcel',
                    'application/x-ms-excel',
                    'application/x-excel',
                    'application/xls',
                    'application/x-dos_ms_excel',
                    'application/x-xls',
                    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                    'application/ms-excel',
                ]
            if 'doc' in self.filetypes:
                mime_whitelist += [
                    'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'application/zip',
                    'multipart/x-zip'
                ]
            if 'csv' in self.filetypes:
                mime_whitelist += ['text/csv', 'text/plain', 'application/vnd.ms-excel']
            return mime_whitelist

    def to_python(self, data):
        ret = []
        for item in data:
            ret.append(super().to_python(item))
        return ret

    def validate(self, data):
        super().validate(data)
        num_files = len(data)

        if len(data) and not data[0]:
            num_files = 0
        if num_files < self.min_num:
            raise ValidationError(self.error_messages['min_num'] % {'min_num': self.min_num, 'num_files': num_files})

        elif self.max_num and num_files > self.max_num:
            raise ValidationError(self.error_messages['max_num'] % {'max_num': self.max_num, 'num_files': num_files})
        if num_files:
            for uploaded_file in data:
                if uploaded_file.size > self.max_file_size:
                    raise ValidationError(self.error_messages['file_size'] % {'uploaded_file_name': uploaded_file.name})

    def compress(self, value):
        if value:
            return value
        return None

    def clean(self, *args, **kwargs):
        values = super().clean(*args, **kwargs)
        if values:
            for value in values:
                if self.filetypes:
                    mime_whitelist = self.get_mimetypes()
                    ext_whitelist = self.get_extensions()
                    filename = value.name
                    try:
                        import magic
                        try:
                            mime_type = magic.from_buffer(value.read(1024), mime=True)
                        except magic.MagicException:
                            raise forms.ValidationError('Problemas ao obter o formato do arquivo')
                    except ModuleNotFoundError:
                        mime_type = value.content_type
                    ext = os.path.splitext(filename)[1].lower()
                    if ext not in ext_whitelist or (self.check_mimetype and mime_type not in mime_whitelist):
                        raise forms.ValidationError('O formato do arquivo não é válido. Por favor, envie um arquivo nos formatos: {}.'.format(', '.join(ext_whitelist)))
                    value.seek(0)
                if self.max_file_size:
                    try:
                        if hasattr(value, 'size') and value.size > int(self.max_file_size):
                            raise forms.ValidationError(
                                f'Por favor mantenha o arquivo com tamanho até {filesizeformat(self.max_file_size)}. Tamanho atual: {filesizeformat(value.size)}.'
                            )
                    except Exception:
                        raise ValidationError('Arquivo inválido por favor substitua-o e tente novamente.')
        return values


class ImageFieldPlus(forms.ImageField):
    widget = ClearableFileInputPlus

    def __init__(self, upload_to='', storage=None, *args, **kwargs):
        self.init = kwargs.pop('initial', None)
        self.max_file_size = kwargs.pop('max_file_size', None)
        if not self.max_file_size:
            self.max_file_size = settings.DEFAULT_FILE_UPLOAD_MAX_SIZE
        self.upload_to = upload_to
        self.storage = storage or default_storage
        super().__init__(*args, **kwargs)
        self.widget = ClearableFileInputPlus()
        self.widget.max_file_size = self.max_file_size
        self.widget.extensions = self.get_extensions()
        self.widget.mimetypes = self.get_mimetypes()
        self.widget.max_file_size = self.max_file_size

    def get_extensions(self):
        return ['.jpeg', '.jpg', '.png', ]

    def get_mimetypes(self):
        return ['image/jpeg', 'image/pjpeg', 'image/png', ]

    def clean(self, data, initial=None):
        data = super().clean(data, initial)
        if self.max_file_size and data:
            try:
                if data.size > int(self.max_file_size):
                    raise forms.ValidationError(
                        'Por favor mantenha o arquivo com tamanho até {}. Tamanho atual: {}.'.format(
                            filesizeformat(self.max_file_size), filesizeformat(data.size))
                    )
            except AttributeError:
                raise ValidationError('Arquivo inválido por favor tente novamente.')
        return data


class BrTelefoneField(forms.Field):
    widget = BrTelefoneWidget

    def __init__(self, *args, **kwargs):
        if 'max_length' in kwargs:
            kwargs.pop('max_length')
        kwargs.pop('empty_value', None)
        super(self.__class__, self).__init__(*args, **kwargs)
        self.help_text = kwargs.get('help_text', 'Formato: "(99) 99999-9999"')

    default_error_messages = {'invalid': 'O número deve estar no formato (99) 99999-9999.'}

    def clean(self, value):
        super().clean(value)
        if value in EMPTY_VALUES:
            return ''
        value = re.sub(r'(\(|\)|\s+)', '', smart_str(value))
        phone_digits_re = re.compile(r'^(\d{2})[-\.]?(\d{4,5})[-\.]?(\d{4})$')
        m = phone_digits_re.search(value)
        if m:
            return f'({m.group(1)}) {m.group(2)}-{m.group(3)}'
        raise forms.ValidationError(self.error_messages['invalid'])


class BrCepField(forms.RegexField):
    widget = BrCepWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('help_text', 'Formato: "99999-999"')
        kwargs['max_length'] = 9
        super().__init__(r'^\d{5}-\d{3}$', *args, **kwargs)

    def clean(self, value):
        value = super().clean(value)
        if value in EMPTY_VALUES:
            return ''
        if not re.match(r'\d\d\d\d\d-\d\d\d', value):
            raise forms.ValidationError(self.error_messages['invalid'])
        return value


def DV_maker(v):
    if v >= 2:
        return 11 - v
    return 0


class BrCpfCnpjField(forms.CharField):
    default_error_messages = {
        'invalid': 'CPF/CNPJ inválido.',
        'max_digits': _("This field requires at most 11 digits or 14 characters."),
        'digits_only': _("This field requires only numbers."),
    }

    widget = BRCpfCnpjWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label', 'CPF/CNPJ')
        super(self.__class__, self).__init__(*args, **kwargs)
        self.help_text = kwargs.get('help_text', '(Informe o número do CPF/CNPJ corretamente e sem ponto ou barra)')

    def clean(self, value):
        value = super().clean(value)
        if value in EMPTY_VALUES:
            return ''
        if len(value) == 11:  # formato "99999999999" - cpf
            value = mask_cpf(value)
            if not re.match(r'\d\d\d.\d\d\d.\d\d\d-\d\d', value):
                raise forms.ValidationError(self.error_messages['invalid'])
            orig_value = value[:]
            if not value.isdigit():
                value = re.sub(r'[-\.]', '', value)
            try:
                int(value)
            except ValueError:
                raise forms.ValidationError(self.error_messages['digits_only'])
            if len(value) != 11:
                raise forms.ValidationError(self.error_messages['max_digits'])
            orig_dv = value[-2:]

            new_1dv = sum(i * int(value[idx]) for idx, i in enumerate(range(10, 1, -1)))
            new_1dv = DV_maker(new_1dv % 11)
            value = value[:-2] + str(new_1dv) + value[-1]
            new_2dv = sum(i * int(value[idx]) for idx, i in enumerate(range(11, 1, -1)))
            new_2dv = DV_maker(new_2dv % 11)
            value = value[:-1] + str(new_2dv)
            if value[-2:] != orig_dv:
                raise forms.ValidationError(self.error_messages['invalid'])

            return orig_value
        elif len(value) == 14:  # formato "XX.XXX.XXX/XXXX-XX"
            value = mask_cnpj(value)
            if not re.match(r'\d\d.\d\d\d.\d\d\d/\d\d\d\d-\d\d', value):
                raise forms.ValidationError(self.error_messages['invalid'])
            orig_value = value[:]
            if not value.isdigit():
                value = re.sub(r'[-\./]', '', value)
            try:
                int(value)
            except ValueError:
                raise forms.ValidationError(self.error_messages['digits_only'])
            if len(value) != 14:
                raise forms.ValidationError(self.error_messages['max_digits'])
            orig_dv = value[-2:]

            new_1dv = sum(i * int(value[idx]) for idx, i in enumerate(list(range(5, 1, -1)) + list(range(9, 1, -1))))
            new_1dv = DV_maker(new_1dv % 11)
            value = value[:-2] + str(new_1dv) + value[-1]
            new_2dv = sum(i * int(value[idx]) for idx, i in enumerate(list(range(6, 1, -1)) + list(range(9, 1, -1))))
            new_2dv = DV_maker(new_2dv % 11)
            value = value[:-1] + str(new_2dv)
            if value[-2:] != orig_dv:
                raise forms.ValidationError(self.error_messages['invalid'])
        else:
            raise forms.ValidationError(self.error_messages['invalid'])
        return orig_value


class BrCpfField(forms.CharField):
    default_error_messages = {
        'invalid': _("Favor, informar um CPF válido."),
        'max_digits': _("Este campo requer um valor entre 11 e 14 dígitos."),
        'digits_only': _("Favor, preencher somente com números."),
    }

    widget = BRCpfWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label', 'CPF')
        super(self.__class__, self).__init__(*args, **kwargs)
        self.help_text = kwargs.get('help_text', 'Formato: "XXX.XXX.XXX-XX"')

    def clean(self, value):
        value = super().clean(value)
        if value in EMPTY_VALUES:
            return ''
        if len(value) == 11 and value.isdigit():  # formato "99999999999"
            value = mask_cpf(value)
        if len(value) != 14:  # formato "999.999.999-99"
            raise forms.ValidationError(self.error_messages['invalid'])
        if not re.match(r'\d\d\d.\d\d\d.\d\d\d-\d\d', value):
            raise forms.ValidationError(self.error_messages['invalid'])
        orig_value = value[:]
        if not value.isdigit():
            value = re.sub(r'[-\.]', '', value)
        try:
            int(value)
        except ValueError:
            raise forms.ValidationError(self.error_messages['digits_only'])
        if len(value) != 11:
            raise forms.ValidationError(self.error_messages['max_digits'])
        orig_dv = value[-2:]

        new_1dv = sum(i * int(value[idx]) for idx, i in enumerate(range(10, 1, -1)))
        new_1dv = DV_maker(new_1dv % 11)
        value = value[:-2] + str(new_1dv) + value[-1]
        new_2dv = sum(i * int(value[idx]) for idx, i in enumerate(range(11, 1, -1)))
        new_2dv = DV_maker(new_2dv % 11)
        value = value[:-1] + str(new_2dv)
        if value[-2:] != orig_dv:
            raise forms.ValidationError(self.error_messages['invalid'])

        return orig_value


class BrCnpjField(forms.CharField):
    default_error_messages = {
        'invalid': _("Informe um CNPJ válido."),
        'digits_only': _("Preencha somente com números."),
        'max_digits': _("Este campo requer 14 dígitos."),
    }

    widget = BrCnpjWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label', 'CNPJ')
        super(self.__class__, self).__init__(*args, **kwargs)
        self.help_text = kwargs.get('help_text', 'Formato: "XX.XXX.XXX/XXXX-XX"')

    def clean(self, value):
        """
        Value can be either a string in the format XX.XXX.XXX/XXXX-XX or a
        group of 14 characters.
        """
        value = super().clean(value)
        if value in EMPTY_VALUES:
            return ''
        if len(value) == 14:  # formato "XXXXXXXXXXXXXX"
            value = mask_cnpj(value)
        if len(value) != 18:  # formato "XX.XXX.XXX/XXXX-XX"
            raise forms.ValidationError(self.error_messages['invalid'])
        if not re.match(r'\d\d.\d\d\d.\d\d\d/\d\d\d\d-\d\d', value):
            raise forms.ValidationError(self.error_messages['invalid'])
        orig_value = value[:]
        if not value.isdigit():
            value = re.sub(r'[-\./]', '', value)
        try:
            int(value)
        except ValueError:
            raise forms.ValidationError(self.error_messages['digits_only'])
        if len(value) != 14:
            raise forms.ValidationError(self.error_messages['max_digits'])
        orig_dv = value[-2:]

        new_1dv = sum(i * int(value[idx]) for idx, i in enumerate(list(range(5, 1, -1)) + list(range(9, 1, -1))))
        new_1dv = DV_maker(new_1dv % 11)
        value = value[:-2] + str(new_1dv) + value[-1]
        new_2dv = sum(i * int(value[idx]) for idx, i in enumerate(list(range(6, 1, -1)) + list(range(9, 1, -1))))
        new_2dv = DV_maker(new_2dv % 11)
        value = value[:-1] + str(new_2dv)
        if value[-2:] != orig_dv:
            raise forms.ValidationError(self.error_messages['invalid'])

        return orig_value


class DecimalFieldPlus(forms.DecimalField):
    widget = BrDinheiroWidget

    def __init__(self, label='', *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = label
        self.help_text = kwargs.get('help_text', 'Formato: "9.999,99"')

    def clean(self, value):
        if not self.required and not value:
            return None
        if value:
            value = value.replace('.', '').replace(',', '.')
        try:
            return Decimal(value)
        except Exception:
            raise forms.ValidationError(self.error_messages['invalid'])

    def widget_attrs(self, widget):
        attrs = super().widget_attrs(widget)

        if self.decimal_places:
            attrs.setdefault('data-decimal-places', self.decimal_places)

        return attrs


class NotaField(DecimalFieldPlus):
    widget = NotaWidget


class DecimalFieldAlmoxPlus(forms.DecimalField):
    widget = BrDinheiroAlmoxWidget

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.help_text = kwargs.get('help_text', 'Formato: "9.999,999"')

    def clean(self, value):
        if not self.required and not value:
            return None
        if value:
            value = value.replace('.', '').replace(',', '.')
        try:
            return Decimal(value)
        except Exception:
            raise forms.ValidationError(self.error_messages['invalid'])


class NumericField(forms.CharField):
    widget = IntegerWidget

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

    default_error_messages = {'invalid': 'O campo deve ser preenchido apenas com números'}


class IntegerFieldPlus(forms.CharField):
    widget = IntegerWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('max_length', 255)
        self._widget_attrs = kwargs.pop('widget_attrs', {})
        if 'width' in kwargs:
            self._widget_attrs['style'] = 'width: %spx;' % kwargs.pop('width')
        super(self.__class__, self).__init__(*args, **kwargs)

    default_error_messages = {'invalid': 'O campo deve ser preenchido apenas com números'}

    def clean(self, value):
        if not self.required and not value:
            return None
        try:
            return int(value)
        except Exception:
            raise forms.ValidationError(self.error_messages['invalid'])


class AlphaNumericField(forms.CharField):
    widget = AlphaNumericWidget

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

    default_error_messages = {'invalid': 'O campo pode ser preenchido apenas com números ou letras'}


class AlphaNumericUpperCaseField(forms.CharField):
    widget = AlphaNumericUpperCaseWidget

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

    default_error_messages = {'invalid': 'O campo pode ser preenchido apenas com números ou letras maiúsculas'}


class CapitalizeTextField(forms.CharField):
    widget = CapitalizeTextWidget

    def __init__(self, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)

    default_error_messages = {'invalid': 'O campo pode ser preenchido apenas com números ou letras'}


class BrPlacaVeicularField(forms.CharField):
    widget = BrPlacaVeicularWidget

    def __init__(self, *args, **kwargs):
        kwargs.setdefault('label', 'Placa')
        super(self.__class__, self).__init__(*args, **kwargs)
        self.help_text = kwargs.get('help_text', 'Formato: "AAA-1111 (Padrão Antigo)" ou "AAA-1A11 (Padrão Mercosul)"')

    default_error_messages = {'invalid': 'A placa deve estar no formato AAA-1111 ou AAA-1A11'}

    def clean(self, value):
        value = super().clean(value)
        if value in EMPTY_VALUES:
            return ''
        if len(value) == 7:  # formato "AAA1A11"
            value = mask_placa(value)
        if len(value) != 8:  # formato "AAA-1111"
            raise forms.ValidationError(self.error_messages['invalid'])
        grupos = value.split('-')
        if not grupos[0].isalnum():
            raise forms.ValidationError(self.error_messages['invalid'])
        else:
            letras = grupos[0].upper()
        if not grupos[1].isalnum():
            raise forms.ValidationError(self.error_messages['invalid'])
        return letras + '-' + grupos[1]


class BRDateRangeField(forms.MultiValueField):
    widget = BRDateRangeWidget

    def __init__(self, fields=(DateFieldPlus(), DateFieldPlus()), sum_end_date=False, *args, **kwargs):
        super(forms.MultiValueField, self).__init__(*args, **kwargs)
        # Set 'required' to False on the individual fields, because the
        # required validation will be handled by MultiValueField, not by those
        # individual fields.
        for f in fields:
            f.required = False
        self.fields = fields

    def clean(self, value):
        """
        Retorna [(data), (data+1 dia)], pois o formato facilita as pesquisas
        em banco de dados: .filter(date__gt=start_date, date__lt=end_date)
        """
        datefield = DateFieldPlus()
        start_date = value[0]
        end_date = value[1]
        if not self.required and not start_date and not end_date:
            return [start_date, end_date]
        else:
            try:
                start_date = datefield.clean(start_date)
                end_date = datefield.clean(end_date)
            except Exception:
                raise forms.ValidationError('A faixa de datas está inválida.')

        if start_date > end_date:
            raise forms.ValidationError('A data final é menor que a inicial.')
        return [start_date, end_date]


class BrEstadoBrasileiroField(forms.ChoiceField):
    def __init__(self, choices=STATE_CHOICES, required=True, widget=None, label=None, initial=None, help_text=None, *args, **kwargs):
        super().__init__(choices=choices, required=required, widget=widget, label=label, initial=initial, help_text=help_text, *args, **kwargs)


class MesField(forms.ChoiceField):
    meses = [
        [1, "Janeiro"],
        [2, "Fevereiro"],
        [3, "Março"],
        [4, "Abril"],
        [5, "Maio"],
        [6, "Junho"],
        [7, "Julho"],
        [8, "Agosto"],
        [9, "Setembro"],
        [10, "Outubro"],
        [11, "Novembro"],
        [12, "Dezembro"],
    ]

    def __init__(self, label=None, empty_label=None, *args, **kwargs):
        super().__init__(label=label, *args, **kwargs)
        # verifica se foi utilizado algum atributo para o rótulo principal (empty_label para os ModelChoiceField)
        if empty_label:
            self.choices = [[0, empty_label]] + self.meses
        else:
            self.choices = self.meses

    def to_python(self, value):
        value = super().to_python(value)
        if value:
            value = int(str(value))
        return value

    def valid_value(self, value):
        for k, v in self.choices:
            if value == k:
                return True
        return False


class ChainedModelChoiceField(forms.ModelChoiceField):
    """
    Uma versão do forms.ModelChoiceField que trabalha de forma aninhada, onde ele é preenchido de acordo com uma escolha de outro "select".
    Keyword arguments:
       *obj_label:             Uma string com o label que deve ser colocado no option do select
        empty_label            Uma string a ser apresentada quando não tiver dados
        url:                   Uma string com a url de pesquisa. Ela deve retornar um Json e recebe os seguintes parametros: `request.POST` expected args: 'chained_attr', 'id', 'obj_label'
        qs_filter:             Uma query no formato string
                                 Exemplo: aluno__caracterizacao__isnull=False
        qs_filter_params_map   Um dict com parâmetros para o qs_fitler
                                 Exemplo: qs_filter='avaliadores_de_agendamentos=current_user'
                                          qs_filter_params_map    = {'current_user': tl.get_user().id},
      * form_filters           Uma lista de lista que tem 'Uma string com o nome do campo relacionado' e 'Uma string representado com o valor que deve colocar no filter'

    * parametros obrigatórios

    Exemplo:
        estado = forms.ModelChoiceField(Estado.object.all(), label=u'Estado')
        cidade = forms.ChainedModelChoiceFieldPlus(Cidade.objects.all(),
                                              label                = u'Cidade',
                                              empty_label          = u'Selecione o Estado',
                                              obj_label            = 'nome',
                                              form_filters         = [('estado', 'estado_id')]
                                              qs_filter            = 'estado__pais=pais'
                                              qs_filter_params_map = {'pais':1})
    """

    widget = ChainedSelectWidget

    def __init__(self, queryset, empty_label="---------", required=True, widget=None, label=None, initial=None, help_text=None, to_field_name=None, *args, **kwargs):
        try:
            obj_label = kwargs.pop('obj_label')
        except KeyError:
            raise KeyError('Parameter obj_label is required.')

        try:
            form_filters = kwargs.pop('form_filters')
        except KeyError:
            raise KeyError('Parameter form_filters is required.')

        qs_filter = kwargs.pop('qs_filter', None)
        qs_filter_params_map = kwargs.pop('qs_filter_params_map', {})
        url = kwargs.pop('url', None)
        if not url:
            class_name = queryset.model.__name__
            class_module = queryset.model._meta.app_label
            url = f'/chained_select/{class_module}/{class_name}/'

        super().__init__(
            queryset, empty_label=empty_label, required=required, widget=widget, label=label, initial=initial, help_text=help_text, to_field_name=to_field_name, *args, **kwargs
        )

        self.widget.initial = initial
        self.widget.empty_label = empty_label
        self.widget.url = url
        self.widget.form_filters = form_filters
        self.widget.obj_label = obj_label
        self.widget.qs_filter = qs_filter
        self.widget.qs_filter_params_map = qs_filter_params_map
        self.widget.queryset = queryset


class AjaxFileUploadField(Field):
    widget = AjaxFileUploadWidget

    def __init__(self, url, onCompleteUploadFunction, multiple=True, sizeLimit=1024 * 1024 * 50, allowedExtensions=['pdf'], *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.label = ''
        self.widget.url = url
        self.widget.onCompleteUploadFunction = onCompleteUploadFunction
        self.widget.multiple = multiple
        self.widget.sizeLimit = sizeLimit
        self.widget.allowedExtensions = allowedExtensions


class ModelMultiplePopupChoiceField(ModelMultipleChoiceField):
    widget = SelectMultiplePopup

    def __init__(self, queryset, required=True, widget=None, label=None, initial=None, help_text=None, *args, **kwargs):
        form_filters = kwargs.pop('form_filters', None)
        list_template = kwargs.pop('list_template', 'popup_multiple_choices.html')
        super().__init__(queryset=queryset, required=required, widget=widget, label=label, initial=initial, help_text=help_text, *args, **kwargs)
        self.help_text = help_text
        self.widget.form_filters = form_filters
        self.widget.list_template = list_template


class ModelPopupChoiceField(ModelChoiceField):
    widget = SelectPopup

    def __init__(self, queryset, empty_label="---------", required=True, widget=None, label=None, initial=None, help_text=None, *args, **kwargs):
        form_filters = kwargs.pop('form_filters', None)
        list_template = kwargs.pop('list_template', 'popup_choices.html')
        super().__init__(
            queryset=queryset, empty_label=empty_label, required=required, widget=widget, label=label, initial=initial, help_text=help_text, *args, **kwargs
        )
        self.help_text = help_text
        self.widget.form_filters = form_filters
        self.widget.list_template = list_template

class ModelPopupAvaliacaoChoiceField(ModelChoiceField):
    widget = SelectPopupAvaliacao

    def __init__(self, queryset, empty_label="---------", required=True, widget=None, label=None, initial=None, help_text=None, *args, **kwargs):
        form_filters = kwargs.pop('form_filters', None)
        list_template = kwargs.pop('list_template', 'popup_choices.html')
        super().__init__(
            queryset=queryset, empty_label=empty_label, required=required, widget=widget, label=label, initial=initial, help_text=help_text, *args, **kwargs
        )
        self.help_text = help_text
        self.widget.form_filters = form_filters
        self.widget.list_template = list_template

class PhotoCaptureField(Field):
    widget = PhotoCaptureInput

    def to_python(self, value):
        if value:
            return base64.b64decode(value.split(',')[1])
        else:
            return None


class ImageViewField(Field):
    widget = Image

    def __init__(self, url_image, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.widget.url_image = url_image
        self.widget.label = kwargs.get('label')
        self.required = False


class MultiEmailField(forms.CharField):
    widget = forms.Textarea

    def to_python(self, value):
        return value.replace(" ", "")

    def validate(self, value):
        value = value.replace(" ", "")
        super().validate(value)
        if value:
            for email in value.split(','):
                validate_email(email)


class JSONSchemaField(CharFieldPlus):

    def __init__(self, schema, options, ajax=True, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.schemadir = getattr(settings, 'JSONFORMS_SCHEMA_DIR', settings.STATIC_ROOT)
        self.backvalidate = getattr(settings, 'JSONFORMS_SCHEMA_VALIDATE', True)

        self.schema = self.load(schema)

        if (ajax):
            self.widget = JSONEditorWidget(schema=schema, options=options)
        else:
            self.options = self.load(options)
            self.widget = JSONEditorWidget(schema=self.schema, options=self.options)

    def load(self, value):
        if isinstance(value, dict):
            return value
        elif isinstance(value, str):
            file_path = os.path.join(self.schemadir, value)
            if os.path.isfile(file_path):
                static_file = open(file_path)
                json_value = json.loads(static_file.read())
                static_file.close()
                return json_value

            return None

    def to_python(self, value):
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError:
                raise ValidationError('Invalid JSON')
        return value

    def clean(self, value):

        value = super().clean(value)

        if self.backvalidate:
            try:
                jsonschema.validate(value, self.schema)
            except jsonschema.exceptions.ValidationError as e:
                raise ValidationError(message=e.message)

        return value

    def prepare_value(self, value):
        if isinstance(value, (dict, list)):
            return json.dumps(value)
        return value
