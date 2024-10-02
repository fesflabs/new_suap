# -*- coding: utf-8 -*-
from djtools.apps import SuapAppConfig as AppConfig


class CatalogoProvedorServicoConfig(AppConfig):
    default = True
    name = 'catalogo_provedor_servico'
    verbose_name = 'Catálogo Digital'
    description = 'Gerencia os serviços do Catálogo Digital.'
    icon = 'check-circle'
    area = 'Comum'
