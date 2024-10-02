import multiprocessing as mp
import os
import subprocess
import sys
import shlex
import traceback
from django.core.management import color_style
from django.apps import apps
from django.template.defaultfilters import slugify
from djtools.management.commands import BaseCommandPlus


areas = {}
for app_config in apps.get_app_configs():
    area = getattr(app_config, 'area', None)
    if area:
        area = slugify(area)
        if area not in areas:
            areas[area] = set()
        areas[area].add(app_config.name)


class Process(mp.Process):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._pconn, self._cconn = mp.Pipe()
        self._exception = None

    def run(self):
        try:
            super().run()
            self._cconn.send(None)
        except Exception as e:
            tb = traceback.format_exc()
            self._cconn.send((e, tb))
            # raise e  # You can still rise this exception if you need to

    @property
    def exception(self):
        if self._pconn.poll():
            self._exception = self._pconn.recv()
        return self._exception


class Command(BaseCommandPlus):
    help = 'Verificações automáticas do código do SUAP'
    apps = ''
    target_branch = ''
    source_branch = ''
    modules = []

    def get_apps(self, apps, n):
        import math
        tamanho = math.ceil(len(apps) / n)
        splitted_apps = []
        for i in range(0, n):
            splitted_apps.append(apps[i * tamanho:i * tamanho + tamanho])
        return splitted_apps

    def print_warning(self, val):
        self.stderr.write(val, style_func=self.style.WARNING)
        self.stderr.flush()
        sys.stderr.flush()

    def print_error(self, val):
        self.stderr.write(val, style_func=self.style.ERROR)
        self.stderr.flush()
        sys.stderr.flush()

    def print_success(self, val):
        self.stdout.write(val, style_func=self.style.SUCCESS)
        self.stdout.flush()
        sys.stdout.flush()

    def run_command(self, command):
        os.environ["PYTHONUNBUFFERED"] = "1"
        result = os.system(command)

        # testes falharam?
        if result:
            raise Exception(f'Falha no comando "{command}"')

    def get_modules(self):
        process = subprocess.Popen(shlex.split('git diff --name-only origin/master..'), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=False)
        self.print_success('Arquivos afetados: ')
        for line in iter(process.stdout.readline, b''):
            output = line.rstrip().decode()
            self.print_success(output)

    def check_django(self):
        cmd = 'python manage.py check --fail-level DEBUG -v 3'
        self.print_success(f'>>> Checando por warnings do django com "{cmd}" ...')

        self.run_command(cmd)

    def check_permissions(self):
        cmd = 'python manage.py sync_permissions --check --raise-exception'
        self.print_success(f'>>> Checando permissões com "{cmd}" ...')

        self.run_command(cmd)

    def check_missing_migrations(self):
        cmd = 'python manage.py makemigrations --dry-run --noinput --check'
        self.print_success(f'>>> Checando migrações com "{cmd}" ...')

        self.run_command(cmd)

    def check_imports_migrations(self):
        cmd = '! find . -name "*.py" -type f | grep "migrations" | xargs grep -r "from .*models" | grep -v django'
        self.print_success('>>> Checando imports de migrações...')

        self.run_command(cmd)

    def check_collectstatic(self):
        cmd = 'python manage.py collectstatic --no-input -c -v 0'
        self.print_success(f'>>> Checando arquivos estáticos com "{cmd}"...')

        self.run_command(cmd)

    def check_black(self):
        cmd = 'python bin/black.py -v 3'
        self.print_success(f'>>> Reformatando arquivos com "{cmd}"...')

        self.run_command(cmd)

    def check_pylint(self):
        cmd = 'python bin/pylint.py -v 3'
        self.print_success(f'>>> Python Linting com "{cmd}"...')

        self.run_command(cmd)

    def test_django(self, apps=''):
        cmd = 'python'
        # if os.environ.get('JOB_ID'):
        #     cmd = 'coverage run'
        cmd += f' manage.py test_suap --nocoverage --noinput --failfast --parallel 2 {apps}'
        self.print_success(f'>>> Testes do django com "{cmd}"...')
        self.run_command(cmd)

    def test_behave(self, apps=''):
        cmd = 'python'
        # if os.environ.get('SUAP_CHECK') == 'behave' and os.environ.get('JOB_ID'):
        #     cmd = 'coverage run'
        cmd += f' manage.py test_behave --behave_format progress --behave_stop --noinput {apps}'
        self.print_success(f'>>> Testes do behave com "{cmd}"...')
        self.run_command(cmd)

    def coverage_report(self):
        if os.environ.get('JOB_ID'):
            self.print_success('>>> Gerando Coverage Report...')
            # self.run_command('coverage report')
            # job_id = os.environ.get('JOB_ID')
            # self.run_command(f'coverage xml -o {job_id}/artifacts/coverage.xml')
            # self.run_command(f'cp "{job_id}/artifacts/coverage.xml" "/tmp/{job_id}/coverage.xml"')

    def handle(self, *args, **options):
        self.style = color_style(True)
        try:
            if os.environ.get('SUAP_CHECK') == 'code':
                self.get_modules()
                self.check_django()
                self.check_permissions()
                self.check_missing_migrations()
                self.check_imports_migrations()
                self.check_collectstatic()
                self.check_pylint()
                self.check_black()
            elif os.environ.get('SUAP_CHECK') == 'django':
                if os.environ['SUAP_APPS'] == 'edu':
                    self.test_django('edu')
                else:
                    test_apps = set()
                    for app_list in areas.values():
                        for app_label in app_list:
                            if app_label != 'edu':
                                test_apps.add(app_label)
                    self.test_django(' '.join(test_apps))
                self.coverage_report()
            elif os.environ.get('SUAP_CHECK') == 'behave':
                self.test_behave(' '.join(areas[os.environ['SUAP_APPS']]))
                self.coverage_report()
            elif os.environ.get('SUAP_CHECK') == 'generate_doc':
                self.test_behave()
            else:
                self.get_modules()
                self.check_django()
                self.check_permissions()
                self.check_missing_migrations()
                self.check_imports_migrations()
                self.check_collectstatic()
                self.check_pylint()
                self.check_black()
                self.test_django()
                self.test_behave()
            print('Testes finalizados com sucesso.')
        except Exception as e:
            self.print_error(str(e))
            sys.exit(1)
