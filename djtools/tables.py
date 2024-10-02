# -*- coding: utf-8 -*-
from django_tables2 import SingleTableView, RequestConfig


class PagedFilteredTableView(SingleTableView):
    filter_class = None
    formhelper_class = None
    context_filter_name = 'filter'

    def get_queryset(self, **kwargs):
        qs = super(PagedFilteredTableView, self).get_queryset()
        self.filter = self.filter_class(self.request.GET, queryset=qs.filter(**kwargs))
        self.filter.form.helper = self.formhelper_class()
        self.filter.form.helper.form_method = 'post'
        self.filter.form.helper.form_tag = False
        return self.filter.qs

    def get_table(self, **kwargs):
        table = super(PagedFilteredTableView, self).get_table(**kwargs)
        page = self.kwargs.get('page') or self.request.GET.get('page') or 1
        RequestConfig(self.request, paginate={'page': page, "per_page": self.paginate_by}).configure(table)
        return table

    def get_context_data(self, **kwargs):
        context = super(PagedFilteredTableView, self).get_context_data()
        context[self.context_filter_name] = self.filter
        return context
