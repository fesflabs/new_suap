# -*- coding: utf-8 -*-

from comum.utils import get_uo
from django.db import models
from django.db.models import Q

####################
# Inventário
####################


class InventariosAtivosManager(models.Manager):
    def get_queryset(self):
        return super(InventariosAtivosManager, self).get_queryset().filter(status__nome='ativo')


class InventariosPendentesManager(models.Manager):
    def get_queryset(self):
        return super(InventariosPendentesManager, self).get_queryset().filter(status__nome='pendente')


class InventariosBaixadosManager(models.Manager):
    def get_queryset(self):
        return super(InventariosBaixadosManager, self).get_queryset().filter(status__nome='baixado')


class InventariosDepreciaveisManager(models.Manager):
    def get_queryset(self):
        return super(InventariosDepreciaveisManager, self).get_queryset().filter(Q(status__nome='ativo') | Q(status__nome='pendente'))


class InventariosAtivosGerenciaveisManager(models.Manager):
    """
    Inventários ativos com carga no mesmo campus do usuário autenticado e também os inventários que os responsáveis não tem campus (ou setor)
    """

    def get_queryset(self):
        meu_campus = get_uo()
        return (
            super(InventariosAtivosGerenciaveisManager, self)
            .get_queryset()
            .filter(Q(status__nome='ativo'), Q(responsavel_vinculo__setor__uo=meu_campus) | Q(responsavel_vinculo__setor__uo=None))
        )
