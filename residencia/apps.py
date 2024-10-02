from djtools.apps import SuapAppConfig as AppConfig


class ResidenciaConfig(AppConfig):
    default = True
    name = 'residencia'
    verbose_name = 'Residência'
    area = 'Residência'
    description = 'Realiza o controle acadêmico.'
    icon = 'chalkboard-teacher'
