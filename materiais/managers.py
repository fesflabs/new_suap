# -*- coding: utf-8 -*-

from django.db import models


class MateriaisAtivosManager(models.Manager):
    def get_queryset(self):
        return super(MateriaisAtivosManager, self).get_queryset().filter(ativo=True)
