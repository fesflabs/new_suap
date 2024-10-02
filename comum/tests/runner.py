import logging
import logging.config
import os

from django.conf import settings
from django.db import transaction
from django.test.runner import DiscoverRunner

# settings.LOGGING['handlers']['console'] = {
#             'level': 'DEBUG',
#             'class': 'logging.StreamHandler',
#             'stream': sys.stdout,
#             'formatter': 'simple'
#         }
# settings.LOGGING['loggers']['django_test'] = {
#             'handlers': ['console'],
#             'level': 'INFO',
#         }

LOGGING_VERBOSITY_PARSE = {0: logging.WARNING, 1: logging.ERROR, 2: logging.INFO, 3: logging.DEBUG}


class DiscoverageRunner(DiscoverRunner):
    @classmethod
    def add_arguments(cls, parser):
        super().add_arguments(parser)
        parser.add_argument('--nocoverage', action='store_true', dest='no_coverage', default=False, help='Desativa a execução do teste de cobertura.')
        parser.add_argument('--createdb', action='store_true', dest='createdb', default=False, help='Cria um novo banco de dados. Usar em conjunto com keepdb')

    def __init__(self, no_coverage=False, createdb=False, **kwargs):
        super().__init__(**kwargs)

        settings.TEST_REUSEDB = kwargs.get('keepdb', False)
        self.no_coverage = no_coverage
        self.createdb = createdb

        root = logging.getLogger()
        root.handlers[-1].setFormatter(logging.Formatter('%(levelname)s - %(message)s'))
        root.setLevel(LOGGING_VERBOSITY_PARSE[self.verbosity])

        # logger = logging.getLogger('django_test')
        # logger.setLevel(LOGGING_VERBOSITY_PARSE[self.verbosity])

        # logging.config.dictConfig(settings.LOGGING)

    def run_tests(self, test_labels, extra_tests=None, **kwargs):
        if self.no_coverage:
            return super().run_tests(test_labels, extra_tests=extra_tests, **kwargs)

        if not self.no_coverage:
            apps = []
            for app in test_labels:
                apps.append(app.split('.')[0])
            import coverage
            cov = coverage.coverage(source=apps, omit=['*/src/*', '*/lib/*', '*/django-pagination/*', '*/management/*', '*/migrations/*', '*tests*', '*/tests/*'])
            cov.start()

        result = super().run_tests(test_labels, extra_tests, **kwargs)

        if not self.no_coverage:
            cov.stop()

        self.build_suite(test_labels, extra_tests)

        # Se incluir a linha import abaixo no início deste módulo, ocorrerá o erro
        # DatabaseError: relation "auth_user_groups" already exists
        from comum.tests import SuapTestCase

        SuapTestCase.print_test_resume()

        if not self.no_coverage:
            print()
            # cov.save()
            cov.report()
            cov.html_report()

            print()
            htmlcov = os.path.join(settings.BASE_DIR, 'htmlcov', 'index.html')
            print('Para maiores detalhes do teste de cobertura, abra {}'.format(htmlcov))

        return result

    def setup_databases(self, **kwargs):
        _keepdb = self.keepdb
        if self.keepdb and self.createdb:
            transaction.get_connection().close()
            self.keepdb = False
        old_names = super().setup_databases(**kwargs)
        self.keepdb = _keepdb
        return old_names

    def teardown_databases(self, *args, **kwargs):
        if not self.keepdb:
            return super().teardown_databases(*args, **kwargs)
