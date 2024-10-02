# -*- coding: utf-8 -*-
import six
from django.utils.encoding import force_str

__all__ = ('ReadOnlyFieldsMixin', 'new_readonly_form_class')


class ReadOnlyFieldsMixin(object):
    """Usage:

    class MyFormAllFieldsReadOnly(ReadOnlyFieldsMixin, forms.Form):
        ...


    class MyFormSelectedFieldsReadOnly(ReadOnlyFieldsMixin, forms.Form):
        readonly_fields = ('field1', 'field2')
        ...
    """

    readonly_fields = ()

    def __init__(self, *args, **kwargs):
        super(ReadOnlyFieldsMixin, self).__init__(*args, **kwargs)
        self.define_readonly_fields(self.fields)

    def clean(self):
        cleaned_data = super(ReadOnlyFieldsMixin, self).clean()

        for field_name, field in six.iteritems(self.fields):
            if self._must_be_readonly(field_name):
                cleaned_data[field_name] = getattr(self.instance, field_name)

        return cleaned_data

    def define_readonly_fields(self, field_list):

        fields = [field for field_name, field in six.iteritems(field_list) if self._must_be_readonly(field_name)]

        list([self._set_readonly(field) for field in fields])

    def _all_fields(self):
        return not bool(self.readonly_fields)

    def _set_readonly(self, field):
        field.widget.attrs['disabled'] = 'true'
        field.required = False

    def _must_be_readonly(self, field_name):
        return field_name in self.readonly_fields or self._all_fields()


def new_readonly_form_class(form_class, readonly_fields=()):
    name = force_str("ReadOnly{}".format(form_class.__name__))
    class_fields = {'readonly_fields': readonly_fields}
    return type(name, (ReadOnlyFieldsMixin, form_class), class_fields)
