# coding=utf-8

from djtools.apps import SuapAppConfig as AppConfig


class RemanejamentoConfig(AppConfig):
    default = True
    name = 'remanejamento'
    verbose_name = 'Remanejamento'
    description = 'Gerencia os dados e fluxos do processo de concorrência aos editais de remanejamento interno de servidores.'
    icon = 'exchange-alt'
    area = 'Gestão de Pessoas'
