from xml.dom.minidom import parseString

from django import forms
from django.forms.fields import SplitDateTimeField
from django.forms.utils import flatatt
from django.utils.encoding import force_str, smart_str
from django.utils.html import conditional_escape
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

from djtools.forms.fields import DateTimeFieldPlus
from djtools.forms.widgets import AutocompleteWidget
from djtools.templatetags.filters import format_


def pretty_name(name):
    "Converts 'first_name' to 'First name'"
    name = name[0].upper() + name[1:]
    return name.replace('_', ' ')


class BoundField:
    "A Field plus data"

    def __init__(self, form, field, name):
        self.form = form
        self.field = field
        self.name = name
        self.html_name = form.add_prefix(name)
        self.html_initial_name = form.add_initial_prefix(name)
        if self.field.label is None:
            self.label = pretty_name(name)
        else:
            self.label = self.field.label
        self.help_text = field.help_text or ''

    def __str__(self):
        """Renders this field as an HTML widget."""
        if self.field.show_hidden_initial:
            return self.as_widget() + self.as_hidden(only_initial=True)
        return self.as_widget()

    def _errors(self):
        """
        Returns an ErrorList for this field. Returns an empty ErrorList
        if there are none.
        """
        return self.form.errors.get(self.name, self.form.error_class())

    errors = property(_errors)

    def as_widget(self, widget=None, attrs=None, only_initial=False):
        """
        Renders the field by rendering the passed widget, adding any HTML
        attributes passed as attrs.  If no widget is specified, then the
        field's default widget will be used.
        """
        if not widget:
            widget = self.field.widget
        attrs = attrs or {}
        auto_id = self.auto_id
        if auto_id and 'id' not in attrs and 'id' not in widget.attrs:
            attrs['id'] = auto_id
        if not self.form.is_bound or (hasattr(self.form, 'is_wizard') and self.name not in self.form.data):
            data = self.form.initial.get(self.name, self.field.initial)
            if callable(data):
                data = data()
        else:
            if isinstance(self.field, forms.FileField) and self.data is None:
                data = self.form.initial.get(self.name, self.field.initial)
            else:
                data = self.data
        if not only_initial:
            name = self.html_name
        else:
            name = self.html_initial_name
        return widget.render(name, data, attrs=attrs)

    def as_text(self, attrs=None, **kwargs):
        """
        Returns a string of HTML for representing this as an <input type="text">.
        """
        return self.as_widget(forms.TextInput(), attrs, **kwargs)

    def as_textarea(self, attrs=None, **kwargs):
        "Returns a string of HTML for representing this as a <textarea>."
        return self.as_widget(forms.Textarea(), attrs, **kwargs)

    def as_hidden(self, attrs=None, **kwargs):
        """
        Returns a string of HTML for representing this as an <input type="hidden">.
        """
        return self.as_widget(self.field.hidden_widget(), attrs, **kwargs)

    def _data(self):
        """
        Returns the data for this BoundField, or None if it wasn't given.
        """
        return self.field.widget.value_from_datadict(self.form.data, self.form.files, self.html_name)

    data = property(_data)

    def label_tag(self, contents=None, attrs=None):
        """
        Wraps the given contents in a <label>, if the field has an ID attribute.
        Does not HTML-escape the contents. If contents aren't given, uses the
        field's HTML-escaped label.

        If attrs are given, they're used as HTML attributes on the <label> tag.
        """
        contents = contents or conditional_escape(self.label)
        widget = self.field.widget
        id_ = widget.attrs.get('id') or self.auto_id
        if id_:
            attrs = attrs and flatatt(attrs) or ''
            contents = '<label for="{}"{}>{}</label>'.format(widget.id_for_label(id_), attrs, str(contents))
        return mark_safe(contents)

    def _is_hidden(self):
        "Returns True if this BoundField's widget is hidden."
        return self.field.widget.is_hidden

    is_hidden = property(_is_hidden)

    def _auto_id(self):
        """
        Calculates and returns the ID attribute for this BoundField, if the
        associated Form has specified auto_id. Returns an empty string otherwise.
        """
        auto_id = self.form.auto_id
        if auto_id and '%s' in smart_str(auto_id):
            return smart_str(auto_id) % self.html_name
        elif auto_id:
            return self.html_name
        return ''

    auto_id = property(_auto_id)


def render_field(form, field_name):
    normal_row = '''%(errors)s%(label)s%(field)s%(help_text)s'''
    error_row = '<div>%s</div>'
    row_ender = '</td></tr>'
    help_text_html = '<p class="help">%s</p>'
    errors_on_separate_row = False

    "Helper function for outputting HTML. Used by as_table(), as_ul(), as_p()."
    top_errors = form.non_field_errors()  # Errors that should be displayed above all fields.
    output, hidden_fields = [], []
    field = form.fields[field_name]
    bf = BoundField(form, field, field_name)
    bf_errors = form.error_class([conditional_escape(error) for error in bf.errors])  # Escape and cache in local variable.
    if bf.is_hidden:
        if bf_errors:
            top_errors.extend(['(Hidden field {}) {}'.format(field_name, force_str(e)) for e in bf_errors])
        hidden_fields.append(str(bf))
    else:
        if errors_on_separate_row and bf_errors:
            output.append(error_row % force_str(bf_errors))
        if bf.label:
            label = conditional_escape(force_str(bf.label))
            # Only add the suffix if the label does not end in
            # punctuation.
            if form.label_suffix:
                if label[-1] not in ':?.!':
                    label += form.label_suffix
            label = bf.label_tag(label) or ''
        else:
            label = ''
        if field.help_text:
            help_text = help_text_html % force_str(field.help_text)
        else:
            help_text = ''
        output.append(normal_row % {'errors': force_str(bf_errors), 'label': force_str(label), 'field': str(bf), 'help_text': help_text})
    # if top_errors:
    #    output.insert(0, error_row % force_str(top_errors))
    if hidden_fields:  # Insert any hidden fields in the last row.
        str_hidden = ''.join(hidden_fields)
        if output:
            last_row = output[-1]
            # Chop off the trailing row_ender (e.g. '</td></tr>') and
            # insert the hidden fields.
            if not last_row.endswith(row_ender):
                # This can happen in the as_p() case (and possibly others
                # that users write): if there are only top errors, we may
                # not be able to conscript the last row for our purposes,
                # so insert a new, empty row.
                last_row = normal_row % {'errors': '', 'label': '', 'field': '', 'help_text': ''}
                output.append(last_row)
            output[-1] = last_row[: -len(row_ender)] + str_hidden + row_ender
        else:
            # If there aren't any rows in the output, just append the
            # hidden fields.
            output.append(str_hidden)
    return mark_safe(''.join(output))


def indent_xml(xml, indent=' ' * 4):
    """Indent and return XML."""
    return parseString(xml).toprettyxml(indent)


def render_form(form):
    #    fieldsets = (
    #        (None, {
    #            'fields': ('url', 'title', 'content', 'sites')
    #        }),
    #        ('Advanced options', {
    #            'fields': (('enable_comments', 'registration_required'), ('template_name',))
    #        }),
    #    )

    include_fields = form._meta.fields if hasattr(form, '_meta') and form._meta and form._meta.fields else None
    exclude_fields = form._meta.exclude if hasattr(form, '_meta') and form._meta and form._meta.exclude else None
    model_fields = (
        [model_field.name for model_field in form._meta.model._meta.fields]
        if hasattr(form, '_meta') and hasattr(form._meta, 'model') and hasattr(form._meta.model, '_meta')
        else None
    )
    if hasattr(form, 'fieldsets'):
        fieldsets = form.fieldsets
    else:
        fields = []
        for nome_campo in list(form.fields.keys()):
            if model_fields and nome_campo in model_fields:
                if include_fields and not nome_campo in include_fields:
                    continue
                elif exclude_fields and nome_campo in exclude_fields:
                    continue
            fields.append(nome_campo)
        fieldsets = [(None, {'fields': fields})]

    # fieldsets = hasattr(form, 'fieldsets') and form.fieldsets or [(None, {'fields': form.fields.keys()})]

    out = []
    if hasattr(form, 'INFO'):
        out.append('<p class="msg info"><strong>Atenção: </strong>{}</p>'.format(form.INFO))
    if hasattr(form, 'ALERT'):
        out.append('<p class="msg alert"><strong>Atenção: </strong>{}</p>'.format(form.ALERT))
    # non_field_errors
    if form.non_field_errors():
        out.append('<ul class="errorlist">')
        for error in form.non_field_errors():
            out.append('<li>%s</li>' % error)
        out.append('</ul>')

    for fieldset_name, options in fieldsets:

        lines = options['fields']
        classes = ' '.join(options.get('classes', ()))
        fieldset_description = options.get('description', None)

        # Fieldset
        out.append('<fieldset class="module aligned %(classes)s">' % dict(classes=classes))
        if fieldset_name:
            out.append('<h2>%(fieldset_name)s</h2>' % dict(fieldset_name=fieldset_name))
        if fieldset_description:
            out.append('<div class="description">%(fieldset_description)s</div>' % dict(fieldset_description=fieldset_description))

        for line in lines:
            if isinstance(line, str):
                try:
                    field = form.fields[line]
                except KeyError:
                    continue
                if isinstance(field.widget, forms.HiddenInput):
                    # Hidden field has no div.form-row
                    out.append(render_field(form, line))
                    continue
                else:
                    line = [line]

            out.append('<div class="form-row %(line_classes)s ">' % dict(line_classes=' '.join(line)))

            for field_name in line:

                try:
                    form.fields[field_name]
                except KeyError:
                    raise KeyError('Field "%s" not in form.' % field_name)

                field_classes = []
                if len(line) > 1:
                    field_classes.append('field-box')
                if field_name is line[0]:
                    field_classes.append('field-box-first')
                else:
                    field_classes.append('field-box-later')
                if form.fields[field_name].required:
                    field_classes.append('required')
                out.append('<div class="%(field_classes)s">' % dict(field_classes=' '.join(field_classes)))

                out.append(render_field(form, field_name))

                out.append('</div>')

            out.append('</div>')

        out.append('</fieldset>')

    out = ''.join(out)
    return mark_safe(out)
    # return indent_xml(out)[22:] # retirar o ``<?xml version="1.0" ?>``


def show_form_data(form, data=None):
    data = data or form.data
    fieldsets = hasattr(form, 'fieldsets') and form.fieldsets or [(None, {'fields': list(form.fields.keys())})]

    out = []
    for fieldset_name, options in fieldsets:

        lines = options['fields']
        classes = ' '.join(options.get('classes', ()))
        fieldset_description = options.get('description', None)

        # Fieldset
        out.append('<fieldset class="module aligned %(classes)s">' % dict(classes=classes))
        if fieldset_name:
            out.append('<h2>%(fieldset_name)s</h2>' % dict(fieldset_name=fieldset_name))
        if fieldset_description:
            out.append('<div class="description">%(fieldset_description)s</div>' % dict(fieldset_description=fieldset_description))

        for line in lines:
            if isinstance(line, str):
                if isinstance(form.fields[line].widget, forms.HiddenInput):
                    continue
                else:
                    line = [line]

            out.append('<div class="form-row %(line_classes)s ">' % dict(line_classes=' '.join(line)))

            for field_name in line:
                field_classes = []
                if len(line) > 1:
                    field_classes.append('field-box')
                if field_name is line[0]:
                    field_classes.append('field-box-first')
                else:
                    field_classes.append('field-box-later')
                if form.fields[field_name].required:
                    field_classes.append('required')
                out.append('<div class="%(field_classes)s">' % dict(field_classes=' '.join(field_classes)))

                template = '<label style="padding-top: 0">%(label)s</label><span>%(value)s</span>'

                field = form.fields[field_name]

                if field.label:
                    label = field.label
                else:
                    label = ' '.join(field_name.split('_')).capitalize()

                if isinstance(field, forms.BooleanField):
                    value = form.cleaned_data.get(field_name) and _('Yes') or _('No')
                else:
                    value = format_(form.cleaned_data[field_name]) or '<em class="scarletred1">Não Informado</em>'
                if hasattr(field, 'choices'):
                    for c_id, c_val in field.choices:
                        if c_id == form.data[field_name]:
                            value = c_val
                out.append(template % dict(label=label, value=value))

                out.append('</div>')

            out.append('</div>')

        out.append('</fieldset>')

    out = ''.join(out)
    return mark_safe(out)


class FormPlus:
    def render_fieldsets(self):
        return render_form(self)

    def pre_fields(self, fields):
        """
        Validates a value for each field in ``fields`` at ``self.cleaned_data``.
        """
        blank_fields = []
        for field_name in fields:
            if field_name not in self.cleaned_data:
                blank_fields.append('"%s"' % self.fields[field_name].label)
        if blank_fields:
            raise forms.ValidationError('O(s) campo(s) %s deve(m) ser preenchido(s).' % ', '.join(blank_fields))


class DtModelForm(forms.ModelForm):
    """
    ``forms.ModelForm`` com mais poderes

    * Atributo ``required_fields``
    * Atributo ``readonly_fields``
    * Atributo ``hidden_fields_``

    * Definição automática de widgets
       - ModelChoiceField com mais de 50 opções será um AutocompleteWidget
    """

    def _get_widget_for_modelchoicefield(self, fname):
        field = self.fields[fname]
        if isinstance(field, forms.ModelMultipleChoiceField):
            return forms.CheckboxSelectMultiple
        elif isinstance(field, forms.ModelChoiceField):
            if fname in self.declared_fields and self.declared_fields[fname].widget:
                return field.widget
            if isinstance(field, forms.ModelChoiceField):
                if field.queryset.count() <= 50:
                    return field.widget
                return AutocompleteWidget

    def get_field_attrs_for_modelchoicefield(self, fname):
        field = self.fields[fname]
        return dict(
            widget=self._get_widget_for_modelchoicefield(fname),
            required=field.required,
            queryset=field.queryset,
            empty_label=field.empty_label,
            label=field.label,
            initial=field.initial,
            help_text=field.help_text,
            to_field_name=field.to_field_name,
        )

    def get_field_attrs_for_datefield(self, fname):
        field = self.fields[fname]
        return dict(required=field.required, label=field.label, initial=field.initial, help_text=field.help_text)

    def __init__(self, *args, **kwargs):

        setattr(self.Meta, 'exclude', ['cadastrado_em', 'cadastrado_por'])
        super().__init__(*args, **kwargs)

        self.required_fields = getattr(self, 'required_fields', [])
        self.readonly_fields = getattr(self, 'readonly_fields', [])
        self.hidden_fields_ = getattr(self, 'hidden_fields_', [])
        self.exclude = [f.name for f in self._meta.model._meta.fields if not f.editable]

        for fname, field in list(self.fields.items()):

            if isinstance(field, forms.ModelChoiceField):
                new_f = forms.ModelChoiceField(**self.get_field_attrs_for_modelchoicefield(fname))
                self.fields[fname] = new_f

            if isinstance(field, forms.ModelMultipleChoiceField):
                attrs = self.get_field_attrs_for_modelchoicefield(fname)
                attrs.pop('empty_label')
                attrs.pop('to_field_name')
                new_f = forms.ModelMultipleChoiceField(**attrs)
                self.fields[fname] = new_f

            if isinstance(field, (forms.DateTimeField, SplitDateTimeField)):
                new_f = DateTimeFieldPlus(**self.get_field_attrs_for_datefield(fname))
                self.fields[fname] = new_f

            if fname in self.required_fields:
                self.fields[fname].required = True

            if fname in self.readonly_fields:
                self.fields[fname].widget.attrs.update({'readonly': 'readonly'})

            if fname in self.hidden_fields_:
                self.fields[fname].widget = forms.HiddenInput()
