# coding=utf-8

from djtools.apps import SuapAppConfig as AppConfig


class ProgressoesConfig(AppConfig):
    default = True
    name = 'progressoes'
    verbose_name = 'Progressões'
    description = 'Gerencia os dados e fluxos ao avaliação e concessão de progressão funcional de Docentes e Técnicos-Administrativos.'
    icon = 'chart-line'
    area = 'Gestão de Pessoas'
