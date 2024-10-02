from djtools.apps import SuapAppConfig as AppConfig


class LabvirtualConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'labvirtual'
    verbose_name = 'Laboratório Virtual'
    area = 'Ensino'
    description = 'Realiza o controle de laboratórios virtuais.'
    icon = 'chalkboard-teacher'
