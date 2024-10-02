import subprocess
import sys

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    help = 'Reformatação automática dos códigos do SUAP'

    def add_arguments(self, parser):
        parser.add_argument('apps', nargs='*', type=str)

        parser.add_argument(
            '--all',
            action='store_true',
            help='Realiza uma verificação em todos os arquivos e não somente os alterados em relação a branch master.',
        )

    def handle(self, *args, **options):
        if options['apps']:
            apps = ' '.join(options['apps'])
        else:
            apps = '.'
        command = ''
        if options['all']:
            command = '--all'

        result = subprocess.run(f'python ./bin/black.py {command} {apps}'.split(' '))
        sys.exit(result.returncode)
