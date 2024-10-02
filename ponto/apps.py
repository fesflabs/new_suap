# coding=utf-8

from djtools.apps import SuapAppConfig as AppConfig


class PontoConfig(AppConfig):
    default = True
    name = 'ponto'
    verbose_name = 'Ponto'
    description = 'Gerencia os dados e fluxos referentes a batida de ponto, compensação de horas e justificativas do ponto de frequência dos servidores.'
    icon = 'hourglass-start'
    area = 'Gestão de Pessoas'
