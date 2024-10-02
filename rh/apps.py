# coding=utf-8

from djtools.apps import SuapAppConfig as AppConfig


class RhConfig(AppConfig):
    default = True
    name = 'rh'
    verbose_name = 'Gestão de Pessoas'
    description = 'Gerencia os cadastros e principais funcionalidades relacionadas a Gestão de Pessoais.'
    icon = 'users'
    area = 'Gestão de Pessoas'
