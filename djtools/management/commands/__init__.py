"""
A classe `BaseCommandPlus` deve ser usada no lugar da
`django.core.management.base.BaseCommand` para que um email seja enviado em
caso de erro na execução do comando.

Nota: Foi feito o uso do handler `django.request` por se tratar de um handler
padrão e não ser necessário criar uma nova entrada em `settings.LOGGING.loggers`.
"""

import sys
from datetime import datetime
from logging import getLogger

from django.core.management.base import BaseCommand
from sentry_sdk import capture_exception

logger = getLogger('django.request')


def format_time(dt):
    """
    Retira a parte não significativa de objetos datetime ou timedelta.
    formato padrão para datetime: 2014-05-13 16:03:26.087286
    formato padrão para timedelta: 0:01:22.473183
    """
    return str(dt).split('.')[0]


class BaseCommandPlus(BaseCommand):
    stealth_options = ('interactive', 'raise_exception')

    def execute(self, *args, **options):
        x0 = datetime.now()
        command_name = self.__class__.__module__.split('.')[-1]
        try:
            print(f'[{format_time(datetime.now())}] Command {command_name} INICIANDO')
            super().execute(*args, **options)
        except Exception as e:
            logger.error(msg=str(command_name), exc_info=sys.exc_info())
            capture_exception(e)
            print(f'[{format_time(datetime.now())}] Command {command_name} FAILED')
            if options.get('raise_exception', True):
                raise e
        print(f'[{format_time(datetime.now())}] Command {command_name} OK in {format_time(datetime.now() - x0)}')
