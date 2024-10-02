from djtools.apps import SuapAppConfig as AppConfig


class PpeConfig(AppConfig):
    default = True
    name = 'ppe'
    verbose_name = 'PPE'
    area = 'PPE'
    description = 'Realiza o controle acadêmico PPE.'
    icon = 'chalkboard-teacher'

