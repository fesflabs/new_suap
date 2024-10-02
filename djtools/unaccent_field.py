# -*- coding: utf-8 -*-

from django.db import models
from django.db.models.lookups import IContains, IExact, IStartsWith, IEndsWith, In, IsNull


class UnaccentLookupUpper(object):
    def process_lhs(self, compiler, connection, lhs=None):
        lhs, lhs_params = super().process_lhs(compiler, connection)
        concat = 'f_unaccent(%s)'
        # lhs = UPPER("pessoa"."nome"::text)
        if 'UPPER' in lhs:
            lhs = lhs[6:-1]
        return concat % lhs, lhs_params

    def as_sql(self, compiler, connection):
        from djtools.utils import to_ascii
        sql, params = super().as_sql(compiler, connection)
        cleaned_params = []
        for param in params:
            cleaned_params.append(to_ascii(param))
        return sql, cleaned_params


class UnaccentIContains(UnaccentLookupUpper, IContains):
    pass


class UnaccentIExact(UnaccentLookupUpper, IExact):
    pass


class UnaccentIStartWith(UnaccentLookupUpper, IStartsWith):
    pass


class UnaccentIEndWith(UnaccentLookupUpper, IEndsWith):
    pass


class UnaccentIn(UnaccentLookupUpper, In):
    def process_rhs(self, compiler, connection):
        if self.rhs_is_direct_value():
            # rhs should be an iterable, we use batch_process_rhs
            # to prepare/transform those values
            rhs = list(self.rhs)
            if not rhs:
                from django.db.models.sql.datastructures import EmptyResultSet

                raise EmptyResultSet
            sqls, sqls_params = self.batch_process_rhs(compiler, connection, rhs)
            placeholder = '(' + ', '.join('UPPER({0})'.format(sql) for sql in sqls) + ')'
            return (placeholder, sqls_params)
        else:
            return super().process_rhs(compiler, connection)


class UnaccentIsNull(UnaccentLookupUpper, IsNull):
    pass

# TODO: ideal usar CharFieldPlus, mas ocorre erro de importação. O pacote djtools.db.models.__init__.py carrega antes do engine do database.


class UnaccentField(models.CharField):
    description = 'Unaccent Field'

    def __init__(self, *args, **kwargs):
        # duplicando trecho de código do CharFieldPlus
        kwargs.setdefault('max_length', 255)
        self.extra_attrs = kwargs.pop('extra_attrs', {})
        self.widget_attrs = kwargs.pop('widget_attrs', {})
        if 'width' in kwargs:
            self.widget_attrs['style'] = 'width: {}px;'.format(kwargs.pop('width'))

        if 'db_index' not in kwargs:
            kwargs['db_index'] = True
        super().__init__(*args, **kwargs)
        self.lookup = None

    # duplicando método do CharFieldPlus
    def formfield(self, *args, **kwargs):
        field = super().formfield(*args, **kwargs)
        field.widget.attrs.update(self.widget_attrs)
        return field

    def deconstruct(self):
        name, path, args, kwargs = super().deconstruct()
        if self.db_index is False:
            kwargs['db_index'] = False
        else:
            del kwargs['db_index']

        return name, path, args, kwargs

    def get_lookup(self, lookup_name):
        if lookup_name in ['icontains', 'contains']:
            return UnaccentIContains
        elif lookup_name in ('exact', 'iexact'):
            return UnaccentIExact
        elif lookup_name == 'istartswith':
            return UnaccentIStartWith
        elif lookup_name == 'iendswith':
            return UnaccentIEndWith
        elif lookup_name == 'in':
            return UnaccentIn
        elif lookup_name == 'isnull':
            return UnaccentIsNull
        else:
            raise TypeError('Unaccent Field got invalid lookup: %s' % lookup_name)


UnaccentField.register_lookup(UnaccentIContains)
UnaccentField.register_lookup(UnaccentIExact)
UnaccentField.register_lookup(UnaccentIStartWith)
UnaccentField.register_lookup(UnaccentIEndWith)
UnaccentField.register_lookup(UnaccentIn)
UnaccentField.register_lookup(UnaccentIsNull)
