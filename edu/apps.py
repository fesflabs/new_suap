# -*- coding: utf-8 -*-


from djtools.apps import SuapAppConfig as AppConfig


class EduConfig(AppConfig):
    default = True
    name = 'edu'
    verbose_name = 'Ensino'
    area = 'Ensino'
    description = 'Realiza o controle acadêmico.'
    icon = 'chalkboard-teacher'
