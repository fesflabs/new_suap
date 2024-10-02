# pylint: skip-file
# flake8: noqa
import itertools
import json
import marshal
from decimal import Decimal

from django.utils.translation import gettext_lazy as _
from django.conf import settings
from django.contrib.admin.widgets import FilteredSelectMultiple
from django.db.models import ForeignKey
from django.db.models.query import QuerySet
from django.forms.utils import flatatt
from django.forms.widgets import (
    Input,
    TextInput,
    DateTimeInput,
    DateInput,
    TimeInput,
    MultiWidget,
    Widget,
    Select,
    RadioSelect,
    SelectMultiple,
    CheckboxInput,
    CheckboxSelectMultiple,
    HiddenInput,
)
from django.template.context_processors import csrf
from django.template.defaultfilters import filesizeformat
from djtools.utils.response import render_to_string
from django.utils.datastructures import MultiValueDict
from django.utils.encoding import force_str
from django.utils.html import format_html
from django.utils.safestring import mark_safe
from pipeline.forms import PipelineFormMedia

from djtools.utils import mask_nota, randomic, has_change_permission, has_add_permission, mask_cpf, mask_money, mask_placa, \
    mask_cnpj, timeless_dump_qs
from .patch_templates import *  # NOQA


# TODO: gerar id's para os widgets (funcionar com label for)
# TODO: pegar max_length do models
# TODO: melhorar visualizacao do field required


class Masked:
    class Media:
        js = ('/static/djtools/jquery/jquery.maskedinput.js', '/static/djtools/jquery/widgets-core.js')


class MaskedInput(TextInput, Masked):
    pass


class BrDataWidget(DateTimeInput, Masked):
    """
    Define o ``format`` e aplica a máscara javascript a partir da classe.
    """

    format = '%d/%m/%Y'

    def __init__(self, attrs=None, format=None, show_label=True):
        attrs = attrs or {}
        if show_label:
            attrs.update({'class': 'br-data-widget', 'size': '10', 'maxlength': '10'})
        else:
            attrs.update({'class': 'br-data-widget labeless', 'size': '10', 'maxlength': '10'})
        super(DateTimeInput, self).__init__(attrs)
        if format:
            self.format = format


class RegionalDateWidget(DateInput):
    input_type = 'date'

    def render(self, name, value, attrs=None, renderer=None):
        value = self.format_value(value)

        attrs = attrs or {}
        attrs.update({'autocomplete': 'off'})
        html = super().render(name, value, attrs)
        return mark_safe(html)


class RegionalTimeWidget(TimeInput):
    input_type = 'time'

    def render(self, name, value, attrs=None, renderer=None):
        value = self.format_value(value)
        attrs = attrs or {}
        attrs.update({'step': '1'})
        return super().render(name, value, attrs)


class RegionalDateTimeWidget(DateTimeInput):
    input_type = 'datetime-local'

    def render(self, name, value, attrs=None, renderer=None):
        value = self.format_value(value)
        attrs = attrs or {}
        attrs.update({'step': '1'})
        html = super().render(name, value, attrs)
        return mark_safe(html)


class TextareaCounterWidget(forms.Textarea):
    def __init__(self, max_length, attrs=None):
        self.max_length = max_length
        super().__init__(attrs)

    def render(self, name, value, attrs=None, renderer=None):
        max_length = self.max_length
        id_ = attrs['id']
        script = """
        <script>
            jQuery(document).ready(function() {{
                var textarea = $("#{id}");
                textarea.on('keyup', function() {{
                    textCounter_{id}(textarea, {max_length});
                }});
                count = get_qtd_caracteres(textarea);
                textarea.parent().append('<p class="help"><span id="counter_{id}">'+({max_length}-count)+'</span> caractere(s) restante(s)</p>');
            }});
            function textCounter_{id}(field, maxlimit ) {{
                if ( get_qtd_caracteres(field) > maxlimit ) {{
                    set_max_caracteres(field, maxlimit);
                    $("#counter_{id}").text(0);
                }} else {{
                    $("#counter_{id}").text(maxlimit - get_qtd_caracteres(field));
                }}
            }}
            function get_qtd_caracteres(field){{
                //Recupera ignorando os caracteres que não são "visíveis"
                return field.val().replace(/[\\n\\r]/g, '').length;
            }}
            function set_max_caracteres(field, maxlimit){{
                //Seta o texto máximo para o campo ignorando os caracteres que não são "visíveis"
                var texto = field.val();
                var caracteres_ignorados = texto.match(/(\\r\\n|\\n|\\r)/gm);
                var qtd_ignorados = 0;
                if(caracteres_ignorados){{
                    qtd_ignorados = caracteres_ignorados.length;
                }}
                field.val(field.val().substr(0, maxlimit+qtd_ignorados));
            }}

        </script>
        """.format(
            id=id_,
            max_length=max_length,
        )
        html = super().render(name, value, attrs)
        return mark_safe(f'{html}{script}')


class TextareaCloneWidget(forms.Textarea):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.clones = ''

    def render(self, name, value, attrs=None, renderer=None):
        id_ = attrs['id']
        if not attrs:
            attrs = dict()
        attrs.update(style='width:100%')
        html = super().render(name, value, attrs)
        html = '''
            <div>
                <div style="width:370px;float:left; padding:3px">
                    <div>
                    </div>
                    %(html)s
                </div>
                <div id="clone_%(id)s" style="width:370px;float:left; padding:3px; height:200px; overflow:scroll">
                    <label>Buscar/Filtrar</label>
                    <input type="text" style="width:100%%" name="q" value="" id="search_%(id)s" class="search-query">

                    %(clone)s

                </div>
            </div>
            <p class="help" style="clear:both">Click em algum registro ao lado para copiar seu conteúdo na área de texto.</p>

            <style>
                #clone_%(id)s div{cursor:pointer; padding:3px !important;}
                #clone_%(id)s div:hover{background-color:#DEDEDE;}
            </style>

            <script>
                jQuery(document).ready(function() {
                    $("#clone_%(id)s div").click(function(){$("#%(id)s").val($(this).find("p")[0].innerHTML.split("<br>").join(""));});
                    jQuery.expr[':'].icontains = function(a, i, m) {
                        return jQuery(a).text().toUpperCase().indexOf(m[3].toUpperCase()) >= 0;
                    };

                    $("#search_%(id)s").keyup(
                        function(){
                            var value = $(this).val();
                            var itens = $("#clone_%(id)s").find("div > p");
                            for(var i=0; i<itens.length; i++) $(itens[i]).parent().show();
                            var hidden = itens.filter(":not(:icontains("+value+"))");
                            for(var i=0; i<hidden.length; i++) $(hidden[i]).parent().hide();
                        }
                    );
                });
            </script>

        ''' % {
            'id': id_,
            'html': html,
            'clone': self.clones,
        }
        return mark_safe(html)


class BrTelefoneWidget(MaskedInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'br-phone-number-widget', 'size': '18', 'maxlength': '18'})
        super().__init__(attrs=attrs)


class BRCpfCnpjWidget(MaskedInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'br-cpf-cnpj-widget', 'size': '18', 'maxlength': '18'})
        super(self.__class__, self).__init__(attrs=attrs)

    def render(self, name, value, attrs=None, renderer=None):
        return super(self.__class__, self).render(name, value, attrs=attrs)


class BRCpfWidget(MaskedInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'br-cpf-widget', 'size': '14', 'maxlength': '14'})
        super(self.__class__, self).__init__(attrs=attrs)

    def render(self, name, value, attrs=None, renderer=None):
        if value and value.isdigit() and len(value) == 11:
            value = mask_cpf(value)
        return super(self.__class__, self).render(name, value, attrs=attrs)


class BrCnpjWidget(MaskedInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'br-cnpj-widget', 'size': '18', 'maxlength': '18'})
        super(self.__class__, self).__init__(attrs=attrs)

    def render(self, name, value, attrs=None, renderer=None):
        if value and value.isdigit() and len(value) == 14:
            value = mask_cnpj(value)
        return super(self.__class__, self).render(name, value, attrs=attrs)


class BrDinheiroWidget(MaskedInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'br-dinheiro-widget', 'size': '15', 'maxlength': '15'})
        super().__init__(attrs=attrs)

    def format_value(self, value):
        if value is None:
            value = ''
        expected_types = (str, Decimal, int)
        if not isinstance(value, expected_types):
            raise ValueError('Value type must be in %s %s' % expected_types)

        if isinstance(value, str) and (value == '' or ',' in value):
            # value is blank or already formatted
            return value
        else:
            try:
                return mask_money(value)
            except Exception:  # adicionado para o caso de inserir um valor diferente do padrão, por exemplo a letra acentuada "ã"
                return value

    def render(self, name, value, attrs=None, renderer=None):
        value = self.format_value(value)
        return super().render(name, value, attrs=attrs)


class NotaWidget(MaskedInput):
    def __init__(self, attrs={}):
        length = 3
        if settings.NOTA_DECIMAL:
            attrs.update({'onkeyup': f'mask_nota(this, {settings.CASA_DECIMAL} )'})
            if settings.CASA_DECIMAL == 2:
                length = 4
        attrs.update({'class': 'nota-widget', 'maxlength': length})
        super().__init__(attrs=attrs)

    def render(self, name, value, attrs=None, renderer=None):
        value = mask_nota(value)
        return super().render(name, value, attrs=attrs, renderer=renderer)


class BrDinheiroAlmoxWidget(MaskedInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'br-dinheiro-almox-widget', 'size': '15', 'maxlength': '15'})
        super().__init__(attrs=attrs)

    def format_value(self, value):
        if value is None:
            value = ''
        expected_types = (str, Decimal)
        if not isinstance(value, expected_types):
            raise ValueError('Value type must be in %s %s' % expected_types)

        if isinstance(value, str) and (value == '' or ',' in value):
            # value is blank or already formatted
            return value
        else:
            return value

    def render(self, name, value, attrs=None, renderer=None):
        value = self.format_value(value)
        return super().render(name, value, attrs=attrs)


class BRDateRangeWidget(MultiWidget):
    def __init__(self, widgets=(RegionalDateWidget, RegionalDateWidget), attrs={}):
        super(self.__class__, self).__init__(widgets, attrs)

    def decompress(self, value):
        if not value:
            return ['', '']
        return value

    def render(self, name, value, attrs=None, renderer=None):
        # value is a list of values, each corresponding to a widget
        # in self.widgets.
        if not isinstance(value, list):
            value = self.decompress(value)
        output = []
        final_attrs = self.build_attrs(attrs)
        id_ = final_attrs.get('id', None)
        for i, widget in enumerate(self.widgets):
            try:
                widget_value = value[i]
            except IndexError:
                widget_value = None
            if id_:
                final_attrs = dict(final_attrs, id=f'{id_}_{i}')
            output.append(widget.render(name + '_%s' % i, widget_value, final_attrs))
            if i == 0:
                output.append('<span style="padding: 0px 10px 0px 4px">até</span>')
        return mark_safe(''.join(output))


class BrPlacaVeicularWidget(MaskedInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'placa-widget', 'size': '10', 'maxlength': '8'})
        super(self.__class__, self).__init__(attrs=attrs)

    def render(self, name, value, attrs=None, renderer=None):
        if value and len(value) == 7:
            value = mask_placa(value)
        return super(self.__class__, self).render(name, value, attrs=attrs)


class BrCepWidget(MaskedInput):
    class Media:
        js = ("/static/djtools/consulta_cep/js/consulta_cep.js",)

    def __init__(self, attrs={}):
        attrs.update({'class': 'br-cep-widget', 'size': '9', 'maxlength': '9'})
        super(self.__class__, self).__init__(attrs=attrs)


class IntegerWidget(MaskedInput):
    input_type = 'number'

    def __init__(self, attrs={}):
        attrs.update({'class': 'integer-widget'})
        super(self.__class__, self).__init__(attrs=attrs)


class AlphaNumericWidget(MaskedInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'alpha-widget'})
        super(self.__class__, self).__init__(attrs=attrs)


class AlphaNumericUpperCaseWidget(MaskedInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'upper-text-widget'})
        super(self.__class__, self).__init__(attrs=attrs)


class CapitalizeTextWidget(MaskedInput):
    def __init__(self, attrs={}):
        attrs.update({'class': 'capitalize-text-widget'})
        super(self.__class__, self).__init__(attrs=attrs)


###############
# Autocomplete Configuration
###############

BASE_SEARCH_URL = 'autocompletar'


def get_search_url(cls):
    data = dict(base_search_url=BASE_SEARCH_URL, app_label=cls._meta.app_label, model_label=cls.__name__.lower())
    return '/%(base_search_url)s/%(app_label)s/%(model_label)s/' % data


def get_change_list_url(cls):
    data = dict(app_label=cls._meta.app_label, model_name=cls.__name__.lower())
    return '/admin/%(app_label)s/%(model_name)s/' % data


def get_add_another_url(cls):
    data = dict(app_label=cls._meta.app_label, model_name=cls.__name__.lower())
    return '/admin/%(app_label)s/%(model_name)s/add/' % data


ALL_AUTOCOMPLETE_OPTIONS = (
    'matchCase',
    'matchContains',
    'mustMatch',
    'minChars',
    'selectFirst',
    'extraParams',
    'formatItem',
    'formatMatch',
    'formatResult',
    'multiple',
    'multipleSeparator',
    'width',
    'autoFill',
    'max',
    'highlight',
    'scroll',
    'scrollHeight',
)

DEFAULT_AUTOCOMPLETE_OPTIONS = dict(autoFill=True, minChars=2, scroll=False, extraParams=dict())


def set_autocomplete_options(obj, options):
    options = options or dict()
    for option in list(options.keys()):
        if option not in ALL_AUTOCOMPLETE_OPTIONS:
            raise ValueError(f'Autocomplete option error: "{option}" not in {ALL_AUTOCOMPLETE_OPTIONS}')
    new_options = DEFAULT_AUTOCOMPLETE_OPTIONS.copy()
    new_options.update(options)
    obj.options = json.dumps(new_options)


###############
# AutocompleteWidget
# http://jannisleidel.com/2008/11/autocomplete-form-widget-foreignkey-model-fields/)
###############


class AutocompleteWidgetOld(TextInput):
    """
    Widget desenvolvido para ser utilizado com field ``forms.ModelChoiceField``.
    View Ajax default: djtools.utils.autocomplete_view
    """

    # TODO: mover scripts do template ``autocomplete_widget.html`` para arquivo js.
    class Media:
        js = ("/static/djtools/jquery/jquery.autocomplete.js", "/static/djtools/jquery/jquery.bgiframe.min.js", "/static/admin/js/admin/RelatedObjectLookups.js")

    def __init__(
        self,
        url=None,
        id_=None,
        attrs=None,
        show=True,
        help_text=None,
        readonly=False,
        side_html=None,
        label_value=None,
        form_filters=None,
        search_fields=None,
        manager_name=None,
        qs_filter=None,
        can_add_related=True,
        submit_on_select=False,
        **options
    ):
        self.can_add_related = can_add_related
        self.help_text = help_text
        self.show = show
        self.attrs = attrs and attrs.copy() or {}
        self.id_ = id_ or randomic()
        self.url = url
        self.readonly = readonly
        self.side_html = side_html
        self.form_filters = form_filters
        self.submit_on_select = submit_on_select

        options['extraParams'] = options.get('extraParams', {})

        if readonly:
            options['extraParams']['readonly'] = 1

        if label_value:
            options['extraParams']['label_value'] = label_value
        if form_filters:
            if not isinstance(form_filters, (tuple, list)):
                raise ValueError('`form_filters` deve ser lista ou tupla')
            options['extraParams']['form_parameter_names'] = ','.join([i[0] for i in form_filters])
            options['extraParams']['django_filter_names'] = ','.join([i[1] for i in form_filters])

        if search_fields:
            if not isinstance(search_fields, (tuple, list)):
                raise ValueError('`search_fields` deve ser lista ou tupla')
            options['extraParams']['search_fields'] = ','.join(search_fields)
        if manager_name:
            if not isinstance(manager_name, str):
                raise ValueError('`manager_name` deve ser basestring')
            options['extraParams']['manager_name'] = manager_name
        if qs_filter:
            if not isinstance(qs_filter, str):
                raise ValueError('`qs_filter` deve ser basestring')
            options['extraParams']['qs_filter'] = qs_filter
        if 'ext_combo_template' in options['extraParams']:
            # http://stackoverflow.com/questions/1253528/is-there-an-easy-way-to-pickle-a-python-function-or-otherwise-serialize-its-cod#answers-header
            # serializa a função
            code_string = marshal.dumps(options['extraParams'].pop('ext_combo_template').__code__)
            code_string = timeless_dump_qs(code_string)
            options['extraParams']['ext_combo_template'] = code_string

        set_autocomplete_options(self, options)
        super().__init__(self.attrs)

    def render(self, name, value=None, attrs=None, renderer=None):
        model_cls = self.choices.queryset.model
        value = value or ''
        if not isinstance(value, (str, int, model_cls)):
            raise ValueError('value must be basestring, int or a models.Model instance. Got %s.' % value)
        if isinstance(value, model_cls):
            value = value.pk
        self.url = self.url or get_search_url(model_cls)
        context = dict(
            id=self.id_,
            value=value,
            options=self.options,
            form_filters=self.form_filters,
            name=name,
            url=self.url,
            change_list_url=get_change_list_url(model_cls),
            add_another_url=get_add_another_url(model_cls),
            has_change_permission=has_change_permission(model_cls),
            has_add_permission=has_add_permission(model_cls),
            side_html=self.side_html,
            readonly=self.readonly,
            attrs=self.attrs,
            show=self.show,
            control=timeless_dump_qs(self.choices.queryset.all().query),
            help_text=self.help_text,
            submit_on_select=self.submit_on_select,
            can_add_related=self.can_add_related,
        )

        output = render_to_string('djtools/templates/autocomplete_widget.html', context)
        return mark_safe(output)


class AutocompleteWidget(Select):
    class Media(PipelineFormMedia):
        js_packages = ('select2',)
        css_packages = {'all': ('select2',)}

    def __init__(
        self,
        url=None,
        id_=None,
        attrs=None,
        show=True,
        help_text=None,
        readonly=False,
        side_html=None,
        label_value=None,
        form_filters=None,
        search_fields=None,
        manager_name=None,
        qs_filter=None,
        can_add_related=True,
        submit_on_select=False,
        multiple=False,
        ext_combo_template=None,
        **options
    ):
        self.can_add_related = can_add_related
        self.help_text = help_text
        self.show = show
        self.attrs = attrs and attrs.copy() or {}
        self.id_ = id_ or randomic()
        self.url = url
        self.readonly = readonly
        self.side_html = side_html
        self.form_filters = form_filters
        self.submit_on_select = submit_on_select
        self.allow_multiple_selected = multiple
        self.ext_combo_template = ext_combo_template or str

        options['extraParams'] = options.get('extraParams', {})

        if readonly:
            options['extraParams']['readonly'] = 1

        if label_value:
            options['extraParams']['label_value'] = label_value
        if form_filters:
            if not isinstance(form_filters, (tuple, list)):
                raise ValueError('`form_filters` deve ser lista ou tupla')
            options['extraParams']['form_parameter_names'] = json.dumps(form_filters)

        if search_fields:
            if not isinstance(search_fields, (tuple, list)):
                raise ValueError('`search_fields` deve ser lista ou tupla')
            options['extraParams']['search_fields'] = ','.join(search_fields)
        if manager_name:
            if not isinstance(manager_name, str):
                raise ValueError('`manager_name` deve ser basestring')
            options['extraParams']['manager_name'] = manager_name
        if qs_filter:
            if not isinstance(qs_filter, str):
                raise ValueError('`qs_filter` deve ser basestring')
            options['extraParams']['qs_filter'] = qs_filter
        if 'ext_combo_template' in options['extraParams']:
            # http://stackoverflow.com/questions/1253528/is-there-an-easy-way-to-pickle-a-python-function-or-otherwise-serialize-its-cod#answers-header
            # serializa a função
            code_string = marshal.dumps(options['extraParams'].pop('ext_combo_template').__code__)
            code_string = timeless_dump_qs(code_string)
            options['extraParams']['ext_combo_template'] = code_string

        self.options = options
        super().__init__(self.attrs)

    def render(self, name, value=None, attrs=None, renderer=None):
        if not hasattr(self.choices, 'queryset'):
            if isinstance(value, str):
                value = [value]
            context = dict(
                id=self.id_,
                values=value,
                options=self.options,
                form_filters=self.form_filters,
                name=name,
                side_html=self.side_html,
                readonly=self.readonly,
                attrs=self.attrs,
                show=self.show,
                help_text=self.help_text,
                submit_on_select=self.submit_on_select,
                can_add_related=self.can_add_related,
                allow_multiple_selected=self.allow_multiple_selected,
                static=True,
                choices=self.choices
            )
            output = render_to_string('djtools/templates/widgets/select2.html', context)
            return mark_safe(output)

        model_cls = self.choices.queryset.model
        if self.readonly and hasattr(self.readonly, 'pk'):
            return mark_safe(
                f'{self.readonly} <input type="hidden" name="{name}" value="{self.readonly.pk}">'
            )
        values = value or []
        if not isinstance(values, (str, int, model_cls, list, QuerySet)):
            raise ValueError('value must be basestring, int or a models.Model instance. Got %s.' % value)
        if isinstance(values, model_cls):
            values = [[value.pk, self.ext_combo_template(value)]]
        elif isinstance(values, int) or (isinstance(values, str) and values.isdigit()):
            values = [[values, self.ext_combo_template(model_cls.objects.filter(pk=values).first())]]
        elif isinstance(values, QuerySet):
            values = []
            for obj in value:
                if type(obj) == int:
                    values.append([obj, self.ext_combo_template(model_cls.objects.filter(pk=obj).first())])
                else:
                    values.append([obj.pk, self.ext_combo_template(obj)])
        elif values:
            qs = model_cls.objects.none()
            try:
                qs = model_cls.objects.filter(pk__in=values)
            except TypeError:
                pks = [i.pk for i in values]
                qs = model_cls.objects.filter(pk__in=pks)
            except ValueError:
                # values is not int
                pass
            values = []
            for obj in qs:
                values.append([obj.pk, self.ext_combo_template(obj)])

        self.url = self.url or f'/json/{model_cls._meta.app_label}/{model_cls.__name__.lower()}/'
        context = dict(
            id=self.id_,
            values=values,
            options=self.options,
            form_filters=self.form_filters,
            name=name,
            url=self.url,
            change_list_url=get_change_list_url(model_cls),
            add_another_url=get_add_another_url(model_cls),
            has_change_permission=has_change_permission(model_cls),
            has_add_permission=has_add_permission(model_cls),
            side_html=self.side_html,
            readonly=self.readonly,
            attrs=self.attrs,
            show=self.show,
            control=timeless_dump_qs(self.choices.queryset.all().query),
            help_text=self.help_text,
            submit_on_select=self.submit_on_select,
            can_add_related=self.can_add_related,
            allow_multiple_selected=self.allow_multiple_selected,
        )
        output = render_to_string('djtools/templates/widgets/select2.html', context)
        return mark_safe(output)


class QrCodeScanner(TextInput):

    def render(self, name, value, attrs=None, **kwargs):
        attrs.update(style='margin-left:160px;width:300px')
        widget = super().render(name, value, attrs=attrs, **kwargs)
        output = render_to_string('djtools/templates/widgets/qr_code_scanner.html', dict(widget=widget, name=name))
        return mark_safe(output)


class AjaxMultiSelect(Widget):
    class Media:
        js = ("/static/djtools/jquery/jquery.autocomplete.js", "/static/djtools/jquery/jquery.bgiframe.min.js")

    def __init__(self, auto_url=None, app_name=None, class_name=None, attrs=None, form_filters=None, placeholder="", search_fields=None, **options):
        self.auto_url = auto_url
        self.form_filters = form_filters
        self.placeholder = placeholder

        options['extraParams'] = options.get('extraParams', {})

        if form_filters:
            if not isinstance(form_filters, (tuple, list)):
                raise ValueError('`form_filters` deve ser lista ou tupla')
            options['extraParams']['form_parameter_names'] = ','.join([i[0] for i in form_filters])
            options['extraParams']['django_filter_names'] = ','.join([i[1] for i in form_filters])

        if search_fields:
            if not isinstance(search_fields, (tuple, list)):
                raise ValueError('`search_fields` deve ser lista ou tupla')
            options['extraParams']['search_fields'] = ','.join(search_fields)

        options['scroll'] = True
        set_autocomplete_options(self, options)
        super(self.__class__, self).__init__(attrs)

    def render(self, name, value, attrs=None, choices=(), renderer=None):
        self.auto_url = self.auto_url or get_search_url(self.choices.queryset.model)

        # style extra item in self.attrs
        extra_style_item = self.attrs.pop("extra_style_item", None)

        # style extra remove icon link in self.attrs
        extra_style_remove_icon = self.attrs.pop("extra_style_remove_icon", None)

        final_attrs = self.build_attrs(attrs)
        final_attrs.setdefault('id', 'id_' + name)
        if value and value != ['']:
            if isinstance(value, (tuple, list, QuerySet)):
                value = [getattr(item, 'pk') if hasattr(item, 'pk') else item for item in value]
            else:
                if isinstance(value, str) and len(list(value.split(","))) > 1:
                    value = list(value.split(","))
                else:
                    value = [getattr(value, 'pk')] if hasattr(value, 'pk') else [value]
            try:
                items = self.choices.queryset.filter(id__in=value)
            except Exception:
                items = []
        else:
            items = []

        context = dict(
            name=name,
            attrs=flatatt(final_attrs),
            url=self.auto_url,
            placeholder=self.placeholder,
            options=self.options,
            control=timeless_dump_qs(self.choices.queryset.all().query),
            items=items,
            form_filters=self.form_filters,
            extra_style_item=extra_style_item,
            extra_style_remove_icon=extra_style_remove_icon,
        )

        output = render_to_string('djtools/templates/multipleautocomplete_widget.html', context)

        return mark_safe(output)

    def value_from_datadict(self, data, files, name):
        if isinstance(data, MultiValueDict):
            return data.getlist(name)
        return data.get(name, None)


###############
# TreeWidget
###############


class ExtTreeWidget(TextInput):
    pass


class TreeWidget(TextInput):
    class Media(PipelineFormMedia):
        js_packages = ('jstree',)

    def __init__(self, id_=None, root_nodes=None, attrs={}):
        self.id_ = id_ or randomic()
        super().__init__(attrs)
        self.root_nodes = root_nodes

    def get_parent_field(self):
        cls = self.choices.queryset.model
        for field in cls._meta.fields:
            if isinstance(field, ForeignKey) and field.remote_field.model == cls:
                return field
        raise Exception('Class %s has no self relation' % (cls.__name__))

    def get_root_nodes(self):
        """ Returns a root nodes list
        But for while, this list has a only element.
        This need to be fix. (ticket #1044)
        """
        args = {self.get_parent_field().name: None}
        return self.choices.queryset.filter(**args).order_by('id')

    def get_children(self, node):
        args = {self.get_parent_field().name: node}
        return self.choices.queryset.filter(**args)

    def get_tree_as_ul(self, node):
        nodes = []
        nodes.append('<ul>')
        self.__get_descendents_helper(node, nodes)
        nodes.append('</ul>')
        return nodes

    def label_from_instance(self, obj):
        return str(obj)

    def __get_descendents_helper(self, node, nodes):
        nodes.append('<li id="%(pk)s"><a href="#" title="%(title)s">%(label)s</a>' % dict(pk=node.pk, title=node.nome, label=self.label_from_instance(node)))
        node_children = self.get_children(node)
        if node_children:
            nodes.append('<ul>')
        for c in node_children:
            self.__get_descendents_helper(c, nodes)
        if node_children:
            nodes.append('</ul>')
        nodes.append('</li>')
        return nodes

    # TODO: caso seja necessário deixar a configuração do multiple no init
    def render(self, name, value=None, attrs=None, renderer=None):
        value = value or ''
        self.root_nodes = self.root_nodes or self.get_root_nodes()
        tree_as_ul = []
        for root_node in self.root_nodes:
            tree_as_ul += self.get_tree_as_ul(root_node)

        selected_value = value and 'data.inst.select_node("#%s", true);' % value or ''

        tree_as_ul = ''.join(tree_as_ul)
        output = """
        <div class="tree-container" id="tree-%(name)s">
            %(tree_as_ul)s
        </div>
        <input type="hidden" name="%(name)s" value="%(value)s"/>
        <script class="source below">
        $(document).ready(function () {
            let tree = $("#tree-%(name)s");
            tree.bind("select_node.jstree", function (event, data) {
                value = data.selected;
                $("input[name=%(name)s]").val(value)
            });
            tree.bind('loaded.jstree', function(e, data) {
                $(this).jstree("select_node", "%(value)s");
            });
            tree.jstree({
                'core': {
                    'multiple': false,
                }
            });

        });
        $(".tree-container a").dblclick(function(event){
            $(this).removeClass('jstree-clicked');
            $("input[name=%(name)s]").val('')
        });

        </script>""" % dict(
            name=name, value=value, tree_as_ul=tree_as_ul, selected_value=selected_value, root_id=self.root_nodes and self.root_nodes[0].pk or ''
        )
        return mark_safe(output)


class ChainedSelectWidget(Select):
    def render(self, name, value, attrs=None, choices=(), renderer=None):
        id_ = attrs['id']
        if not value:
            value = self.initial

        data = ""
        if self.qs_filter:
            data += ", qs_filter: '%s'" % self.qs_filter

        options = {}
        attrs['name'] = name
        if self.form_filters:
            if not isinstance(self.form_filters, (tuple, list)):
                raise ValueError('`form_filters` deve ser lista ou tupla')
            options['form_parameter_names'] = ','.join([i[0] for i in self.form_filters])
            options['django_filter_names'] = ','.join([i[1] for i in self.form_filters])

        options['is_required'] = 'true' if self.is_required else 'false'
        context = dict(
            id=id_,
            url=self.url,
            initial=value,
            obj_value='id',
            obj_label=self.obj_label,
            empty_label=self.empty_label,
            data=data,
            options=options,
            qs_filter_params_map=self.qs_filter_params_map,
        )
        if self.queryset:
            context['control'] = timeless_dump_qs(self.queryset.all().query)

        final_attrs = self.build_attrs(attrs)
        output = [format_html('<select{0}>', flatatt(final_attrs))]
        output.append('</select>')
        output.append(render_to_string('djtools/templates/chainedselect_widget.html', context))
        return mark_safe('\n'.join(output))


class RadioSelectPlus(RadioSelect):
    template_name = 'widgets/radio_select_plus.html'


class CheckboxSelectMultiplePlus(SelectMultiple):
    class Media:
        extend = False
        js = ("/static/djtools/widgets/js/marcar_todos_checkbox.js",)

    def render(self, name, value, attrs=None, choices=(), renderer=None):
        mark_all = ''
        if value is None:
            value = []
            mark_all = "markall"
        has_id = attrs and 'id' in attrs
        attrs['name'] = name
        final_attrs = self.build_attrs(attrs)
        output = ['<ul class="checkboxes">']
        # Normalize to strings
        str_values = {force_str(v) for v in value}
        for i, (option_value, option_label) in enumerate(itertools.chain(self.choices, choices)):
            # If an ID attribute was given, add a numeric index as a suffix,
            # so that the checkboxes don't all have the same ID attribute.
            if has_id:
                final_attrs = dict(final_attrs, id='{}_{}'.format(attrs['id'], i))
                label_for = format_html(' for="{0}"', final_attrs['id'])
            else:
                label_for = ''

            cb = CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_str(option_value)
            rendered_cb = cb.render(name, option_value)
            option_label = force_str(option_label)
            output.append(format_html('<li><label{0}>{1} {2}</label></li>', label_for, rendered_cb, option_label))
        output.append('</ul>')
        if str_values:
            label = 'Desmarcar Todos'
        else:
            label = 'Marcar Todos'
            mark_all = "markall"
        output.append(format_html('<a href="#" data-elemento="{0}" class="checkbutton btn {1}">{2}</a>', name, mark_all, label))
        return mark_safe('\n'.join(output))

    def id_for_label(self, id_):
        # See the comment for RadioSelect.id_for_label()
        if id_:
            id_ += '_0'
        return id_


class AjaxFileUploadWidget(Widget):
    class Media:
        js = ("/static/arquivo/js/fileuploader.js", "/static/arquivo/js/compatibility.js", "/static/arquivo/js/pdf.js")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.params = {'csrf_name': 'csrfmiddlewaretoken', 'csrf_xname': 'X-CSRFToken'}
        self.options = {}

    def render(self, name, value=None, attrs=None, renderer=None):
        csrf_token = csrf(self.request).get('csrf_token')
        if csrf_token:
            csrf_token = csrf_token.encode().decode('utf-8')
        self.params['csrf_token'] = csrf_token

        context = dict(
            id=randomic(),
            url=self.url,
            sizeLimit=self.sizeLimit,
            allowedExtensions=self.allowedExtensions,
            multiple=self.multiple,
            params=self.params,
            onCompleteUploadFunction=self.onCompleteUploadFunction,
        )
        context.update(self.options)
        if attrs:
            context.update(attrs)
        context["id"] = randomic()
        output = render_to_string('djtools/templates/ajaxfileupload_widget.html', context)
        return mark_safe(output)


class SelectPopup(Select):
    allow_multiple_selected = False
    template = 'djtools/templates/popup_choice_field_widget.html'

    def __init__(self, *args, **kwargs):
        self.list_template = kwargs.pop('list_template', 'popup_choices.html')
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, choices=(), renderer=None):
        options = dict()
        if self.form_filters:
            if not isinstance(self.form_filters, (tuple, list)):
                raise ValueError('`form_filters` deve ser lista ou tupla')
            options['form_parameter_names'] = ','.join([i[0] for i in self.form_filters])
            options['django_filter_names'] = ','.join([i[1] for i in self.form_filters])

        s = ''
        ss = ''
        if value:
            if isinstance(value, (tuple, list, QuerySet)):
                value = [getattr(item, 'pk') if hasattr(item, 'pk') else item for item in value]
            else:
                value = [getattr(value, 'pk')] if hasattr(value, 'pk') else [value]
            try:
                for obj in self.choices.queryset.filter(id__in=value):
                    if not s:
                        s = obj.pk
                        ss = str(obj)
                    else:
                        s = f'{s};{obj.pk}'
                        ss = f'{ss}, {str(obj)}'
            except Exception:
                pass

        qs = self.choices.queryset.all() if hasattr(self.choices.queryset, 'all') else self.choices.queryset
        qs = timeless_dump_qs(list(qs))
        disabled = False
        if attrs and type(attrs) is dict:
            disabled = attrs.get('disabled', False)

        context = dict(name=name, qs=qs, s=s, ss=ss, options=options, disabled=disabled, list_template=self.list_template)
        output = render_to_string(self.template, context)
        return mark_safe(output)

class SelectPopupAvaliacao(Select):
    allow_multiple_selected = False
    template = 'djtools/templates/popup_choice_avaliacao_field_widget.html'

    def __init__(self, *args, **kwargs):
        self.list_template = kwargs.pop('list_template', 'popup_choices.html')
        super().__init__(*args, **kwargs)

    def render(self, name, value, attrs=None, choices=(), renderer=None):
        options = dict()
        if self.form_filters:
            if not isinstance(self.form_filters, (tuple, list)):
                raise ValueError('`form_filters` deve ser lista ou tupla')
            options['form_parameter_names'] = ','.join([i[0] for i in self.form_filters])
            options['django_filter_names'] = ','.join([i[1] for i in self.form_filters])

        s = ''
        ss = ''
        if value:
            if isinstance(value, (tuple, list, QuerySet)):
                value = [getattr(item, 'pk') if hasattr(item, 'pk') else item for item in value]
            else:
                value = [getattr(value, 'pk')] if hasattr(value, 'pk') else [value]
            try:
                for obj in self.choices.queryset.filter(id__in=value):
                    if not s:
                        s = obj.pk
                        ss = str(obj)
                    else:
                        s = f'{s};{obj.pk}'
                        ss = f'{ss}, {str(obj)}'
            except Exception:
                pass

        qs = self.choices.queryset.all() if hasattr(self.choices.queryset, 'all') else self.choices.queryset
        qs = timeless_dump_qs(list(qs))
        disabled = False
        if attrs and type(attrs) is dict:
            disabled = attrs.get('disabled', False)

        context = dict(name=name, qs=qs, s=s, ss=ss, options=options, disabled=disabled, list_template=self.list_template)
        output = render_to_string(self.template, context)
        return mark_safe(output)


class SelectMultiplePopup(SelectPopup):
    allow_multiple_selected = True
    template = 'djtools/templates/popup_multiple_choice_field_widget.html'

    def __init__(self, *args, **kwargs):
        self.list_template = kwargs.pop('list_template', 'popup_choices.html')
        super().__init__(*args, **kwargs)

    def value_from_datadict(self, data, files, name):
        return name in data and data[name] and data[name].split(';') or []


class RenderableSelectMultiple(SelectMultiple):
    def __init__(self, template_name=None, max_result=200, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.template_name = template_name
        self.max_result = max_result

    def render(self, name, value, attrs=None, choices=(), renderer=None):

        pks = []
        if value is None:
            value = []
        if hasattr(value, '__iter__') and value and hasattr(value[0], 'pk'):
            pks = [obj.pk for obj in value]

        has_id = attrs and 'id' in attrs
        attrs['name'] = name
        str_values = {force_str(v) for v in value}
        i = 0
        objects = []

        qs = hasattr(self.choices.queryset, 'all') and self.choices.queryset.all() or self.choices.queryset
        for obj in qs[0: self.max_result]:  # querysets maiores que 200 não deveriam ser utilizados nesse tipo de widget
            option_value = obj.pk
            final_attrs = self.build_attrs(attrs)
            if has_id:
                final_attrs = dict(final_attrs, id='{}_{}'.format(attrs['id'], i))
            if option_value in pks:
                final_attrs.update(checked='checked')
            cb = CheckboxInput(final_attrs, check_test=lambda value: value in str_values)
            option_value = force_str(option_value)
            rendered_cb = cb.render(name, option_value)
            obj.widget = rendered_cb
            i += 1
            objects.append(obj)

        return mark_safe(render_to_string(self.template_name, dict(objects=objects)))


class RadioInput(Input):
    input_type = 'radio'
    template_name = 'django/forms/widgets/input.html'


class RenderableRadioSelect(RadioSelect):
    def __init__(self, template_name=None, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.template_name = template_name

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        objects = []
        for object in self.choices.queryset.all():
            widget = RadioInput(attrs.copy())
            if str(value) == str(object.id):
                object.checked_ = True
                widget.attrs.update(checked='checked')
            object.widget = widget.render(name, object.id, attrs.copy())
            objects.append(object)
        context['objects'] = objects
        for option in context['widget']['optgroups']:
            if option[1][0]['value'] != '':
                option[1][0]['object'] = self.choices.queryset.filter(pk=option[1][0]['value'].value)[0]
        return context


class RenderableCheckboxSelect(CheckboxSelectMultiple):
    def __init__(self, template_name=None, *args, **kwargs):
        super(self.__class__, self).__init__(*args, **kwargs)
        self.template_name = template_name

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        objects = []
        for object in self.choices.queryset.all():
            object.widget = CheckboxInput(attrs.copy()).render(name, object.id, attrs.copy())
            objects.append(object)
        context['objects'] = objects
        return context


class CheckboxTooltipSelectPlus(CheckboxSelectMultiple):
    template_name = 'widgets/checkbox_tooltip_select.html'

    def __init__(self, tooltip_field, attrs=None, choices=()):
        self.tooltip_field = tooltip_field
        super().__init__(attrs)

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        objects = []
        str_values = value and {force_str(v) for v in value} or set()
        for object in self.choices.queryset.all():

            object.widget = CheckboxInput(check_test=lambda v: force_str(v) in str_values).render(name, object.id, attrs.copy())
            object.title = getattr(object, self.tooltip_field)
            objects.append(object)
        context['objects'] = objects
        return context


class PhotoCaptureInput(HiddenInput):
    def render(self, name, value, attrs=None, renderer=None):
        s = (
            """

        <div align="center">
            <video autoplay style="display:none;"></video>
            <canvas id="canvas" width="300" height="400"></canvas>
            <br>
            <input type="button" id="cancel" value="Cancelar" class="btn default">
            &nbsp;&nbsp;
            <input type="button" id="snapshot" value="Fotografar" class="btn primary">
        </div>

        <script language='javascript'>
        var video = document.querySelector("video");
        var canvas = document.querySelector("canvas");
        var canvas_visible = canvas.offsetParent != null;
        var ctx = canvas.getContext('2d');
        var t;
        var c = 0;

        if (canvas_visible){
            navigator.getUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia || navigator.msGetUserMedia || navigator.oGetUserMedia;

            if (navigator.getUserMedia) {
                navigator.getUserMedia({video: true}, handleVideo, videoError);
            }
        }

        function handleVideo(stream) {
            video.srcObject = stream;
        }

        function videoError(e) {
            ctx.font="20px Georgia";
            ctx.fillText("Nenhuma camera encontrada!",10,50);
        }
        function crop(){
            var sourceX = 200;
            var sourceY = 0;
            var sourceWidth = 300;
            var sourceHeight = 400;
            var destWidth = sourceWidth;
            var destHeight = sourceHeight;
            var destX = canvas.width / 2 - destWidth / 2;
            var destY = canvas.height / 2 - destHeight / 2;

            ctx.drawImage(video, sourceX, sourceY, sourceWidth, sourceHeight, destX, destY, destWidth, destHeight);
        }
        function snapshot() {
            if(c == 0){
                crop();
                t = setTimeout("snapshot()", 100);
            }
        }

        if (canvas_visible){
            document.querySelector('#snapshot').onclick = function() {
                if(c == 0){
                    c = 1;
                    crop();
                    clearTimeout(t);
                    var dataURL = canvas.toDataURL();
                    hidden = document.querySelector("#id_%s");
                    hidden.value=dataURL;
                }
            }
            document.querySelector('#cancel').onclick = function() {
                if(c == 1){
                    c = 0;
                    snapshot();
                }
            }
            snapshot();
        }
        </script>
        """
            % name
        )
        return mark_safe(s) + super().render(name, value, attrs)


class PhotoCapturePortraitInput(HiddenInput):
    def render(self, name, value, attrs=None, renderer=None):
        s = (
            """
            <div align="center">
                <video autoplay style="display:none;"></video>
                <canvas id="canvas" width="300" height="400"></canvas>
                <br>
                <input type="button" id="cancel" value="Cancelar" class="btn default">
                &nbsp;&nbsp;
                <input type="button" id="snapshot" value="Fotografar" class="btn primary">
            </div>
            <br>
            <script language='javascript'>
                var video = document.querySelector("video");
                var canvas = document.querySelector("canvas");
                var canvas_visible = canvas.offsetParent != null;
                var ctx = canvas.getContext('2d');
                var t;
                var c = 0;

                if (canvas_visible){
                    navigator.getUserMedia = navigator.getUserMedia || navigator.webkitGetUserMedia || navigator.mozGetUserMedia || navigator.msGetUserMedia || navigator.oGetUserMedia;

                    if (navigator.getUserMedia) {
                        navigator.getUserMedia({video: true}, handleVideo, videoError);
                    }
                }

                function handleVideo(stream) {
                    video.srcObject = stream;
                }

                function videoError(e) {
                    ctx.font="20px Georgia";
                    ctx.fillText("Nenhuma camera encontrada!",10,50);
                }
                function crop(){
                    var sourceX = 200;
                    var sourceY = 0;
                    var sourceWidth = 300;
                    var sourceHeight = 400;
                    var destWidth = sourceWidth;
                    var destHeight = sourceHeight;
                    var destX = canvas.width / 2 - destWidth / 2;
                    var destY = canvas.height / 2 - destHeight / 2;

                    ctx.drawImage(video, sourceX, sourceY, sourceWidth, sourceHeight, destX, destY, destWidth, destHeight);
                }
                function snapshot() {
                    if(c == 0){
                        crop();
                        t = setTimeout("snapshot()", 100);
                    }
                }

                if (canvas_visible){
                    document.querySelector('#snapshot').onclick = function() {
                        if(c == 0){
                            c = 1;
                            crop();
                            clearTimeout(t);
                            var dataURL = canvas.toDataURL();
                            hidden = document.querySelector("#id_%s");
                            hidden.value=dataURL;
                        }
                    }
                    document.querySelector('#cancel').onclick = function() {
                        if(c == 1){
                            c = 0;
                            snapshot();
                        }
                    }
                    snapshot();
                }
            </script>
        """
            % name
        )
        return mark_safe(s) + super().render(name, value, attrs)


class FilteredSelectMultiplePlus(FilteredSelectMultiple):
    @property
    def media(self):
        js = ["/admin/jsi18n/", "/static/admin/js/core.js", "/static/admin/js/SelectBox.js", "/static/admin/js/SelectFilter2.js"]

        return forms.Media(js=js)


class Image(HiddenInput):
    def render(self, name, value, attrs=None, renderer=None):
        s = """
                <div class="form-row">
                    <div class="field-box-first">
                        <label>{}:</label>
                        <img src="{}"/>
                    </div>
                </div>
        """.format(
            self.label,
            self.url_image,
        )

        return mark_safe(s) + super().render(name, value, attrs)


class SubmitButton(forms.Widget):
    """
    A widget that handles a submit button.
    """

    def __init__(self, name, value, label, attrs):
        self.name, self.value, self.label = name, value, label
        self.attrs = attrs

    def __str__(self):
        final_attrs = self.build_attrs(self.attrs, type="submit", name=self.name, value=self.value)
        return mark_safe(f'<button{forms.widgets.flatatt(final_attrs)}>{self.label}</button>')


class AjaxSelectMultiplePopup(Widget):
    def __init__(self, auto_url=None, attrs=None, form_filters=None, required_form_filters=False, placeholder="", **options):
        self.auto_url = auto_url
        self.form_filters = form_filters
        self.required_form_filters = required_form_filters
        self.placeholder = placeholder

        options['extraParams'] = options.get('extraParams', {})

        if form_filters:
            if not isinstance(form_filters, (tuple, list)):
                raise ValueError('`form_filters` deve ser lista ou tupla')
            options['extraParams']['form_parameter_names'] = ','.join([i[0] for i in form_filters])
            options['extraParams']['django_filter_names'] = ','.join([i[1] for i in form_filters])
            options['extraParams']['required_form_filters'] = required_form_filters

        self.options = json.dumps(options)
        super(self.__class__, self).__init__(attrs)

    def render(self, name, value, attrs=None, choices=(), renderer=None):
        self.auto_url = self.auto_url or get_search_url(self.choices.queryset.model)

        final_attrs = self.build_attrs(attrs)
        final_attrs.setdefault('id', 'id_' + name)
        s = ''
        ss = ''
        items = []

        if value and value != ['']:
            if isinstance(value, (tuple, list, QuerySet)):
                value = [getattr(item, 'pk') if hasattr(item, 'pk') else item for item in value]
            else:
                value = [getattr(value, 'pk')] if hasattr(value, 'pk') else [value]
            items = self.choices.queryset.filter(id__in=value)

            for obj in items:
                if not s:
                    s = obj.pk
                    ss = str(obj)
                else:
                    s = f'{s};{obj.pk}'
                    ss = f'{ss}, {str(obj)}'

        context = dict(
            name=name,
            s=s,
            ss=ss,
            attrs=flatatt(final_attrs),
            url=self.auto_url,
            placeholder=self.placeholder,
            options=self.options,
            control=timeless_dump_qs(self.choices.queryset.all().query),
            items=items,
            form_filters=self.form_filters,
        )

        output = render_to_string('djtools/templates/ajax_selectmultiple_popup_widget.html', context)

        return mark_safe(output)

    def value_from_datadict(self, data, files, name):
        if isinstance(data, MultiValueDict):
            return name in data and data[name] and data[name].split(';') or []
        return data.get(name, None)


class MultipleSubmitButton(forms.Select):
    """
    A widget that handles a list of submit buttons.
    """

    def __init__(self, attrs={"class": "btn default"}, choices=()):
        self.attrs = attrs
        self.choices = choices

    def __iter__(self):
        for value, label in self.choices:
            yield SubmitButton(self.name, value, label, self.attrs.copy())

    def __str__(self):
        return '<button type="submit" />'

    def render(self, name, value, attrs=None, choices=(), renderer=None):
        """Outputs a <ul> for this set of submit buttons."""
        self.name = name
        return mark_safe('<ul>\n%s\n</ul>' % '\n'.join(['<li>%s</li>' % force_str(w) for w in self]))

    def value_from_datadict(self, data, files, name):
        """
        returns the value of the widget: IE posts inner HTML of the button
        instead of the value.
        """
        value = data.get(name, None)
        if value in dict(self.choices):
            return value
        else:
            inside_out_choices = {v: k for (k, v) in self.choices}
            if value in inside_out_choices:
                return inside_out_choices[value]
        return None


class ClearableFileInputPlus(forms.ClearableFileInput):
    template_name = 'widgets/clearable_file_input.html'
    max_file_size = settings.DEFAULT_FILE_UPLOAD_MAX_SIZE
    multiple = False
    extensions = None
    mimetypes = None

    def value_from_datadict(self, data, files, name):
        if self.multiple:
            if hasattr(files, 'getlist'):
                upload = files.getlist(name)
            else:
                upload = [files.get(name)]
        else:
            upload = files.get(name)
        if not self.is_required and CheckboxInput().value_from_datadict(
                data, files, self.clear_checkbox_name(name)):

            if upload:
                # If the user contradicts themselves (uploads a new file AND
                # checks the "clear" checkbox), we return a unique marker
                # object that FileField will turn into a ValidationError.
                return object()
            # False signals to clear any existing value, as opposed to just None
            return False

        return upload

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        checkbox_name = self.clear_checkbox_name(name)
        checkbox_id = self.clear_checkbox_id(checkbox_name)
        if self.multiple:
            attrs['multiple'] = 'multiple'
            attrs['class'] = 'multifileuploader'

        context['widget'].update({
            'checkbox_name': checkbox_name,
            'checkbox_id': checkbox_id,
            'is_initial': self.is_initial(value),
            'input_text': self.input_text,
            'initial_text': self.initial_text,
            'clear_checkbox_label': self.clear_checkbox_label,
            'name': name,
            'value': value,
            'attrs': attrs,
            'max_file_size': self.max_file_size,
            'friendly_max_file_size': filesizeformat(self.max_file_size),
            'extensions': self.extensions,
            'extensions_display': self.extensions and ', '.join(self.extensions) or '',
            'mimetypes': self.mimetypes,
        })
        return context


class PositionedPdfInput(ClearableFileInputPlus):
    def render(self, *args, **kwargs):
        widget = super().render(*args, **kwargs)
        html = render_to_string(
            'djtools/templates/widgets/positioned_pdf_input.html',
            dict(widget=widget, id=kwargs.get('attrs').get('id'))
        )
        return html


class JSONEditorWidget(Widget):

    template_name = 'widgets/jsoneditor.html'

    class Media:
        js = (
            '/static/djtools/jsoneditor.js',
            '/static/djtools/jsoneditor_init.js'
        )

    def __init__(self, schema, options, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.schema = schema
        self.options = options

    def get_json_url(self, value, name):
        if isinstance(value, dict):
            return {name: json.dumps(value)}
        else:
            urlname = name + '_url'
            return {urlname: value}

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)

        update = self.get_json_url(self.schema, 'schema')
        context.update(update)
        update = self.get_json_url(self.options, 'options')
        context.update(update)

        context['widget']['type'] = 'hidden'
        return context


class NullBooleanSelect(Select):
    """
    A Select Widget intended to be used with NullBooleanField.
    """

    def __init__(self, attrs=None):
        choices = (
            ('unknown', _('---------')),
            ('true', _('Yes')),
            ('false', _('No')),
        )
        super().__init__(attrs, choices)

    def format_value(self, value):
        try:
            return {
                True: 'true', False: 'false',
                'true': 'true', 'false': 'false',
                # For backwards compatibility with Django < 2.2.
                '2': 'true', '3': 'false',
            }[value]
        except KeyError:
            return 'unknown'

    def value_from_datadict(self, data, files, name):
        value = data.get(name)
        return {
            True: True,
            'True': True,
            'False': False,
            False: False,
            'true': True,
            'false': False,
            # For backwards compatibility with Django < 2.2.
            '2': True,
            '3': False,
        }.get(value)
