# flake8: noqa
from datetime import datetime

from django.contrib import admin
from django.contrib.admin.options import IncorrectLookupParameters
from django.utils.encoding import force_str
from django.utils.safestring import mark_safe

from djtools.contrib.admin.views import ChangeListPlus
from djtools.utils import timeless_dump_qs


class RelatedOnlyFieldListFilterPlus(admin.RelatedOnlyFieldListFilter):

    def __init__(self, field, request, params, model, model_admin, field_path):
        super().__init__(field, request, params, model, model_admin, field_path)
        self.allow_multiple_choices = field.name in model_admin.list_filter_multiple_choices
        self.lookup_vals = self.allow_multiple_choices and request.GET.getlist(self.lookup_kwarg) or []

    def field_choices(self, field, request, model_admin):
        pk_qs = model_admin.get_queryset(request).distinct().values_list('%s__pk' % self.field_path, flat=True)
        try:
            return field.get_choices(include_blank=False, limit_choices_to={'pk__in': pk_qs})
        except Exception:
            return [x for x in field.get_choices(include_blank=False) if x[0] in pk_qs and True or False]

    def queryset(self, request, queryset):
        if self.allow_multiple_choices and self.lookup_vals:
            self.used_parameters.pop(self.lookup_kwarg, None)
            self.used_parameters[self.lookup_kwarg.replace('exact', 'in')] = self.lookup_vals
        return super().queryset(request, queryset)

    def choices(self, changelist):
        if not self.allow_multiple_choices:
            yield {
                'selected': self.lookup_val is None and not self.lookup_val_isnull,
                'query_string': changelist.get_query_string(remove=[self.lookup_kwarg, self.lookup_kwarg_isnull]),
                'display': 'Todos',
            }
        for pk_val, val in self.lookup_choices:
            yield {
                'selected': self.lookup_val == str(pk_val) or (self.allow_multiple_choices and str(pk_val) in self.lookup_vals),
                'query_string': changelist.get_query_string({self.lookup_kwarg: pk_val}, [self.lookup_kwarg_isnull]),
                'display': val,
            }
        if not self.allow_multiple_choices:
            if self.include_empty_choice:
                yield {
                    'selected': bool(self.lookup_val_isnull),
                    'query_string': changelist.get_query_string({self.lookup_kwarg_isnull: 'True'}, [self.lookup_kwarg]),
                    'display': self.empty_value_display,
                }


class TabListFilter(admin.SimpleListFilter):
    title = "tab"
    parameter_name = "tab"
    template = 'admin/tablistfilter.html'

    def __init__(self, *args, **kwargs):
        self.model_admin = args[3]
        super().__init__(*args, **kwargs)

    def choices(self, cl):
        queryset = self.model_admin.model.objects.none()
        contador_nas_abas = True if hasattr(self.model_admin, 'show_count_on_tabs') and self.model_admin.show_count_on_tabs else False

        hide_empty_tabs = True if hasattr(self.model_admin, 'hide_empty_tabs') and self.model_admin.hide_empty_tabs else False
        if contador_nas_abas:
            # dicionario que guarda os parametros passados no request
            filtros = dict()
            IGNORAR = ChangeListPlus.IGNORED_PARAMS + ('tab', 'p')
            search_term = ''
            if self.request.GET.urlencode():
                for key, value in list(self.request.GET.items()):
                    if not key in IGNORAR:
                        if '__in' in key and key[-4:] == '__in':
                            filtros[key] = value.split(',')
                        else:
                            filtros[key] = value == 'True' if value in ['True', 'False'] else value
                    elif key == 'q':
                        search_term = value

            queryset = self.model_admin.get_queryset(self.request)
            filter_simple = []
            filter_listfilter = dict()
            filter_fieldlistfilter = dict()

            for filter in self.model_admin.get_list_filter(self.request):
                if type(filter) in [str, str]:
                    filter_simple.append(filter)
                elif type(filter) == tuple:
                    filter_fieldlistfilter[filter[0]] = filter[1]
                else:
                    filter_listfilter[filter.parameter_name] = filter

            for key, value in list(filtros.items()):
                filtro = key.replace('__exact', '').replace('__id', '').replace('__isnull', '').replace('drf__', '').replace('__lte', '').replace('__gte', '')
                if filtro in filter_simple or filtro in list(filter_fieldlistfilter.keys()):
                    # DateRangeFilter
                    if key.startswith('drf__'):
                        if value:
                            tokens = value.split('/')
                            queryset = queryset.filter(**{key.replace('drf__', ''): '{}-{}-{}'.format(tokens[2], tokens[1], tokens[0])})
                    else:
                        queryset = queryset.filter(**{key: value})
                elif filtro in list(filter_listfilter.keys()):
                    filtrar = filter_listfilter[key]
                    queryset = filtrar(self.request, {key: value}, self.model_admin.model, self.model_admin).queryset(self.request, queryset)
            if search_term:
                queryset = self.model_admin.get_search_results(self.request, queryset, search_term)[0]
        tabs_to_show = self.lookup_choices

        first = self.value() is None
        for lookup, title in tabs_to_show:
            yield {
                'selected': self.value() == force_str(lookup) or first,
                'query_string': cl.get_query_string({self.parameter_name: lookup}, []),
                'display': title,
                'pode_mostrar_contador': contador_nas_abas and title != 'Todos',
                'hide_empty_tabs': hide_empty_tabs,
                'contador': self.queryset_from_tab(self.request, queryset, lookup).distinct().count() if contador_nas_abas and title != 'Todos' else 0,
            }
            first = False


def GetTabFromFieldValue(from_field_values):
    class TabFromFieldValueListFilter(TabListFilter):
        def __init__(self, *args, **kwargs):
            self.field = from_field_values
            super().__init__(*args, **kwargs)

        def lookups(self, request, model_admin):
            self.request = request
            return [(value, value) for value in model_admin.get_queryset(request).order_by(self.field).values_list(self.field, flat=True).distinct()]

        def queryset(self, request, queryset):
            if self.value():
                return queryset.filter(**{self.field: self.value()})

        def queryset_from_tab(self, request, queryset, tab):
            return queryset.filter(**{self.field: tab})

    return TabFromFieldValueListFilter


class CustomTabListFilter(TabListFilter):
    def lookups(self, request, model_admin):
        self.model_admin = model_admin
        self.request = request
        return [
            [aba, getattr(getattr(model_admin, aba), 'short_description')] if hasattr(getattr(model_admin, aba), 'short_description') else [aba, aba]
            for aba in model_admin.get_all_tabs(request)
        ]

    def queryset(self, request, queryset):
        if self.value() is None:
            tab_name = self.model_admin.get_all_tabs(request)[0]
            tab_func = getattr(self.model_admin, tab_name)
            return tab_func(request, queryset)

        if self.value():
            try:
                return getattr(self.model_admin, self.value())(request, queryset)
            except AttributeError:
                return None

    def queryset_from_tab(self, request, queryset, tab):
        return getattr(self.model_admin, tab)(request, queryset)


def QuerysetACListFilter(queryset_limit):

    class AutoCompleteListFilter(admin.FieldListFilter):
        template = 'admin/autocomplete.html'
        module_name = queryset_limit.model._meta.app_label
        app_name = queryset_limit.model._meta.model_name
        url_autocomplete = f'/json/{module_name}/{app_name}/'
        filtered_lookups = []

        def __init__(self, field, request, params, model, model_admin, **kwargs):
            self.queryset_default = queryset_limit
            self.url = kwargs.pop('url', self.url_autocomplete)
            self.parameter_name = kwargs.get('field_path')
            self.title = kwargs.pop('title', field)
            lookups = {}
            for lookup, value in params.items():
                lookups[lookup.replace('__id__exact', '')] = value
            super().__init__(field, request, params, model, model_admin, **kwargs)
            self.filtered_lookups = lookups

            if model_admin.list_filter_autocomplete_form_filters and self.parameter_name in model_admin.list_filter_autocomplete_form_filters:
                self.form_filters = model_admin.list_filter_autocomplete_form_filters[self.parameter_name]
            else:
                self.form_filters = {}

            lookup_choices = self.lookups(request, model_admin)
            if lookup_choices is None:
                lookup_choices = ()
            self.lookup_choices = list(lookup_choices)

        def value(self):
            return self.filtered_lookups.get(self.parameter_name)

        def lookups(self, request, model_admin):
            return [('chave', 'valor')]

        def queryset(self, request, queryset):
            if self.value() and type(self.value()) != str:
                args = {self.parameter_name: self.value()}
                queryset = queryset.filter(**args)
                if hasattr(queryset, 'autocomplete'):
                    queryset = queryset.autocomplete()
                return queryset

        def choices(self, changelist):
            related_model = changelist.model
            if '__' in self.parameter_name:
                for field_name in self.parameter_name.split('__'):
                    field_descriptor = related_model._meta.get_field(field_name)
                    related_model = field_descriptor.related_model
            else:
                field_descriptor = related_model._meta.get_field(self.parameter_name)
                related_model = field_descriptor.related_model
            base_queryset = self.queryset_default.all()
            if hasattr(field_descriptor, 'get_queryset'):
                field_descriptor.get_queryset().all()

            texto = ''
            if self.value() and self.value().isdigit():
                texto = base_queryset.filter(id=self.value()).first()
            if hasattr(base_queryset, 'autocomplete'):
                base_queryset = base_queryset.autocomplete()
            control = timeless_dump_qs(base_queryset.query)
            yield {
                'unicode': texto,
                'value': self.value(),
                'selected': self.value() is None,
                'query_string': changelist.get_query_string({}, [self.parameter_name]),
                'display': 'All',
                'url': self.url,
                'parameter_name': self.parameter_name,
                'control': control,
                'form_filters': self.form_filters,
                'options_dafault': {"autoFill": "true", "minChars": "2", "scroll": "true", "extraParams": {"control": mark_safe(control)}},
            }
            for lookup, title in self.lookup_choices:
                yield {
                    'unicode': texto,
                    'value': self.value(),
                    'selected': self.value() == force_str(lookup),
                    'query_string': changelist.get_query_string({self.parameter_name: lookup}, []),
                    'display': title,
                    'url': self.url,
                    'parameter_name': self.parameter_name,
                    'form_filters': self.form_filters,
                    'control': control,
                    'options_dafault': {"autoFill": "true", "minChars": "2", "scroll": "true", "extraParams": {"control": mark_safe(control)}},
                }

        def expected_parameters(self):
            return self.filtered_lookups

    return AutoCompleteListFilter


# Django doesn't deal well with filter params that look like queryset lookups.
FILTER_PREFIX = 'drf__'


class DateRangeListFilter(admin.FieldListFilter):
    template = 'admin/daterangefilter.html'

    def __init__(self, field, request, params, model, model_admin, field_path):
        self.lookup_kwarg_since = '{}{}__gte'.format(FILTER_PREFIX, field_path)
        self.lookup_kwarg_until = '{}{}__lte'.format(FILTER_PREFIX, field_path)
        super().__init__(field, request, params, model, model_admin, field_path)

    def expected_parameters(self):
        return [self.lookup_kwarg_since, self.lookup_kwarg_until]

    def choices(self, changelist):
        return (
            {'field_path': self.field_path, 'value': changelist.params.get(self.lookup_kwarg_since, '')},
            {'field_path': self.field_path, 'value': changelist.params.get(self.lookup_kwarg_until, '')},
        )

    def _clean_input_prefix(self, input_):
        return {key.split(FILTER_PREFIX)[1] if key.startswith(FILTER_PREFIX) else key: val for (key, val) in list(input_.items())}

    def _get_value(self, name, request):
        value = request.GET.get(name)
        if value:
            try:
                value = datetime.strptime(value, '%d/%m/%Y').date()
            except ValueError as erro:
                raise IncorrectLookupParameters(erro)
        return value

    def queryset(self, request, queryset):
        lookup_kwarg_since_value = self._get_value(self.lookup_kwarg_since, request)
        lookup_kwarg_until_value = self._get_value(self.lookup_kwarg_until, request)
        filter_params = dict()
        if lookup_kwarg_since_value or lookup_kwarg_until_value:
            if lookup_kwarg_since_value:
                filter_params[self.lookup_kwarg_since] = lookup_kwarg_since_value
            if lookup_kwarg_until_value:
                filter_params[self.lookup_kwarg_until] = lookup_kwarg_until_value

            filter_params = self._clean_input_prefix(filter_params)
            return queryset.filter(**filter_params)
        else:
            return queryset


class PassThroughFilter(admin.SimpleListFilter):
    title = ''
    parameter_name = 'pt'
    template = 'admin/hidden_filter.html'

    def lookups(self, request, model_admin):
        return (request.GET.get(self.parameter_name), ''),

    def queryset(self, request, queryset):
        return queryset
