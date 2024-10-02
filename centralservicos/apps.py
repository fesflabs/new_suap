# coding=utf-8

from djtools.apps import SuapAppConfig as AppConfig


class CentralServicosConfig(AppConfig):
    default = True
    name = 'centralservicos'
    verbose_name = 'Central de Serviços'
    description = 'Gerencia a Central de Serviços para abertura de chamados para as diferentes áreas de atuação da instituição.'
    icon = 'concierge-bell'
    area = 'Comum'
