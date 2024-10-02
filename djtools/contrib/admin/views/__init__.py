from datetime import datetime, timedelta
import operator
from django.conf import settings

from django.contrib.admin.filters import FieldListFilter
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib.admin.utils import get_fields_from_path, lookup_needs_distinct, prepare_lookup_value
from django.contrib.admin.views.main import ChangeList
from django.contrib.admin.exceptions import DisallowedModelAdminLookup
from django.core.exceptions import FieldDoesNotExist
from django.db import models
from django.utils.timezone import make_aware

from comum.utils import normalizar_termos_busca
from djtools.utils import get_search_field, to_ascii
from functools import reduce


class ChangeListPlus(ChangeList):
    ALL_VAR = 'all'
    ORDER_VAR = 'o'
    ORDER_TYPE_VAR = 'ot'
    PAGE_VAR = 'p'
    SEARCH_VAR = 'q'
    TO_FIELD_VAR = 't'
    IS_POPUP_VAR = 'pop'
    ERROR_FLAG = 'e'

    IGNORED_PARAMS = (ALL_VAR, ORDER_VAR, ORDER_TYPE_VAR, SEARCH_VAR, IS_POPUP_VAR, TO_FIELD_VAR)

    def get_queryset(self, request):
        """
        Método redefinido para tratar campos SearchField. Converte cada valor
        para ASCII maiúsculo e usa cláusula `contains` (default seria `icontains`).
        """
        qs = super().get_queryset(request)
        if get_search_field(self.model):
            # Remove os filtros usados por causa do parâmetro GET `q`
            termos = normalizar_termos_busca(self.query, self.model_admin.avoid_short_search)[0]
            for i in termos.split():
                qs.query.where.children.pop()
            orm_lookups = ['%s__contains' % (str(search_field)) for search_field in self.search_fields]
            # Adicionando os filtros no `qs`
            for bit in termos.split():
                bit = str(to_ascii(bit.upper()))
                or_queries = [models.Q(**{orm_lookup: bit}) for orm_lookup in orm_lookups]
                qs = qs.filter(reduce(operator.or_, or_queries))
        return qs

    def get_filters(self, request):
        lookup_params = self.get_filters_params()  # a dictionary of the query string
        may_have_duplicates = False
        has_active_filters = False

        for key, value in lookup_params.items():
            if not self.model_admin.lookup_allowed(key, value):
                raise DisallowedModelAdminLookup("Filtering by %s not allowed" % key)

        filter_specs = []
        if self.list_filter:
            for list_filter in self.list_filter:
                lookup_params_count = len(lookup_params)
                if callable(list_filter):
                    spec = list_filter(request, lookup_params, self.model, self.model_admin)
                else:
                    spec = None
                    custom = False
                    field_path = None
                    if isinstance(list_filter, (tuple, list)):
                        field, field_list_filter_class = list_filter
                        if hasattr(field_list_filter_class, 'queryset_default'):
                            list_filter = list_filter[0]
                        else:
                            custom = True
                    else:
                        field, field_list_filter_class = list_filter, FieldListFilter.create
                    if not isinstance(field, models.Field):
                        field_path = field
                        field = get_fields_from_path(self.model, field_path)[-1]
                    if not custom and hasattr(field, 'remote_field') and field.remote_field:
                        try:
                            filtros = list_filter.split('__')
                            related_class = self.model
                            title = ''
                            for filtro in filtros:
                                try:
                                    related_field = related_class._meta.get_field(filtro)
                                    related_class = related_field.remote_field.model
                                    if hasattr(related_field, 'verbose_name'):
                                        title = related_field.verbose_name
                                    elif hasattr(related_field, 'related_model'):
                                        title = related_field.related_model._meta.verbose_name
                                    else:
                                        title = filtro.title()
                                except Exception:
                                    related_class = related_class._meta.get_field(filtro).model
                            module_name = related_class._meta.app_label
                            app_name = related_class._meta.model_name
                            url = f'/json/{module_name}/{app_name}/'
                            from djtools.contrib.admin.filters import QuerysetACListFilter
                            qs_related = self.model_admin.get_queryset(request).values(list_filter)
                            AutoCompleteListFilter = QuerysetACListFilter(related_class.objects.filter(pk__in=qs_related))
                            spec = AutoCompleteListFilter(related_field, request, lookup_params, self.model, self.model_admin, field_path=list_filter, url=url, title=title)
                            field = related_field
                        except Exception:
                            pass
                    if not isinstance(field, models.Field):
                        field = get_fields_from_path(self.model, field_path)[-1]
                    if spec is None:
                        spec = field_list_filter_class(field, request, lookup_params, self.model, self.model_admin, field_path=field_path)

                    if lookup_params_count > len(lookup_params):
                        may_have_duplicates |= lookup_needs_distinct(self.lookup_opts, field_path)
                if spec and spec.has_output():
                    filter_specs.append(spec)
                    if lookup_params_count > len(lookup_params):
                        has_active_filters = True

        if self.date_hierarchy:
            # Create bounded lookup parameters so that the query is more
            # efficient.
            year = lookup_params.pop('%s__year' % self.date_hierarchy, None)
            if year is not None:
                month = lookup_params.pop('%s__month' % self.date_hierarchy, None)
                day = lookup_params.pop('%s__day' % self.date_hierarchy, None)
                try:
                    from_date = datetime(
                        int(year),
                        int(month if month is not None else 1),
                        int(day if day is not None else 1),
                    )
                except ValueError as e:
                    raise IncorrectLookupParameters(e) from e
                if day:
                    to_date = from_date + timedelta(days=1)
                elif month:
                    # In this branch, from_date will always be the first of a
                    # month, so advancing 32 days gives the next month.
                    to_date = (from_date + timedelta(days=32)).replace(day=1)
                else:
                    to_date = from_date.replace(year=from_date.year + 1)
                if settings.USE_TZ:
                    from_date = make_aware(from_date)
                    to_date = make_aware(to_date)
                lookup_params.update({
                    '%s__gte' % self.date_hierarchy: from_date,
                    '%s__lt' % self.date_hierarchy: to_date,
                })
        # At this point, all the parameters used by the various ListFilters
        # have been removed from lookup_params, which now only contains other
        # parameters passed via the query string. We now loop through the
        # remaining parameters both to ensure that all the parameters are valid
        # fields and to determine if at least one of them needs distinct(). If
        # the lookup parameters aren't real fields, then bail out.
        try:
            for key, value in list(lookup_params.items()):
                lookup_params[key] = prepare_lookup_value(key, value)
                may_have_duplicates = may_have_duplicates or lookup_needs_distinct(self.lookup_opts, key)
            return (
                filter_specs, bool(filter_specs), lookup_params, may_have_duplicates,
                has_active_filters,
            )
        except FieldDoesNotExist as e:
            raise IncorrectLookupParameters(e)

    def get_ordering(self, request, queryset):
        ordering = super().get_ordering(request, queryset)
        if len(ordering) > 1 and ordering[-1] == '-pk':
            ordering.pop(-1)
        return ordering
