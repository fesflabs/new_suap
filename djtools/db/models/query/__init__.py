# -*- coding: utf-8 -*-
# pylint: skip-file
# from django.db.models.fields import IntegerField
# from django.db.models.query import QuerySet  # NOQA


# class QuerySetPlus(QuerySet):
#
#     def order_by_relevance(self):
#         if hasattr(self.model, 'RELEVANCE_ORDERING'):
#             ordering = ['order_relevance',]
#             if hasattr(self.model._meta, 'ordering'):
#                 [ordering.append(order) for order in self.model._meta.ordering]
#
#             return self.filter().annotate(order_relevance=self.model._case_ordering_relevance(self.model.RELEVANCE_ORDERING)).order_by(*ordering)
#         return self.filter()
