# coding=utf-8

from djtools.apps import SuapAppConfig as AppConfig


class GerenciadorProjetosConfig(AppConfig):
    default = True
    name = 'gerenciador_projetos'
    verbose_name = 'Gerenciador de Projetos'
    description = 'Permite a criação de projetos de trabalho, gerenciando seus membros e o planejamento e andamento de tarefas.'
    icon = 'thumbtack'
    area = 'Comum'
