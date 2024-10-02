"""
Baseado no django_behave.
"""
import fnmatch
import json
import os
import sys
import unittest
from collections import OrderedDict
from optparse import make_option
from os.path import dirname, abspath, join, basename, isdir, isfile
from django.test.testcases import LiveServerTestCase
from behave.configuration import Configuration, options
from behave.formatter._registry import make_formatters
from behave.formatter.ansi_escapes import escapes
from behave.runner import Runner as BehaveRunner, Context
from behave.runner_util import parse_features
from django.apps import apps
from django.conf import settings
from django.test.runner import DiscoverRunner


def get_app(label):
    appconfig = apps.get_app_config(label)
    return appconfig.models_module or appconfig.module


def get_app_dir(app_module):
    app_dir = dirname(app_module.__file__)
    if basename(app_dir) == 'models':
        app_dir = abspath(join(app_dir, '../'))
    return app_dir


def get_features(app_module):
    app_dir = get_app_dir(app_module)

    # if isdir(join(app_dir, 'lps/{}/features'.format(settings.LPS))):
    #     features_dir = abspath(join(app_dir, 'lps/{}/features'.format(settings.LPS)))
    #     return features_dir
    if isdir(join(app_dir, 'features')):
        features_dir = abspath(join(app_dir, 'features'))
        return features_dir
    else:
        return None


def parse_argv(argv, option_info):
    behave_options = list(option_info.keys())

    new_argv = ["behave"]
    our_opts = {"browser": None}

    for index in range(len(argv)):
        if argv[index] in behave_options and argv[index].startswith("--"):
            # Convert to Behave option
            new_argv.append("--" + argv[index][9:])

            # Add option argument if there is one
            if option_info[argv[index]] == True:
                new_argv.append(argv[index + 1])
                index += 1  # Skip past option arg

    if '--behave_capture' not in argv:
        new_argv.extend(['--no-capture', '--no-capture-stderr', '--no-logcapture'])

    return (new_argv, our_opts)


def get_options():
    option_list = ()

    option_info = {}

    for fixed, keywords in options:
        # Look for the long version of this option
        long_option = None
        for option in fixed:
            if option.startswith("--"):
                long_option = option
                break

        # Only deal with those options that have a long version
        if long_option:
            # remove function types, as they are not compatible with optparse
            if hasattr(keywords.get('type'), '__call__'):
                del keywords['type']

            # Remove 'config_help' as that's not a valid optparse keyword
            if "config_help" in keywords:
                keywords.pop("config_help")

            name = "--behave_" + long_option[2:]

            option_list = option_list + (make_option(name, **keywords),)

            # Need to store a little info about the Behave option so that we
            # can deal with it later.  'has_arg' refers to if the option has
            # an argument.  A boolean option, for example, would NOT have an
            # argument.
            action = keywords.get("action", "store")
            if action == "store" or action == "append":
                has_arg = True
            else:
                has_arg = False

            option_info.update({name: has_arg})

    return (option_list, option_info)


class MyBehaveRunner(BehaveRunner):
    def run_with_paths(self):
        extra_steps = [path + '/steps/' for path in self.config.paths]

        self.context = Context(self)
        self.context.debug = self.config.debug
        self.load_hooks()
        self.load_step_definitions(extra_step_paths=settings.TEST_COMMON_STEPS + extra_steps)

        # -- ENSURE: context.execute_steps() works in weird cases (hooks, ...)
        # self.setup_capture()
        # self.run_hook('before_all', self.context)

        # -- STEP: Parse all feature files (by using their file location).
        try:
            lps_path = self.config.paths[0].replace('features', f'lps/{settings.LPS}/features/')
        except IndexError:
            lps_path = ''

        feature_locations = []

        for obj_file in self.feature_locations():
            if self.config.include_re is None or self.config.include_re.search(obj_file.filename):
                if isfile(lps_path + obj_file.filename.split('/')[-1]):
                    obj_file.filename = lps_path + obj_file.filename.split('/')[-1]
                feature_locations.append(obj_file)

        features = parse_features(feature_locations, language=self.config.lang)

        self.features.extend(features)

        # -- STEP: Run all features.
        stream_openers = self.config.outputs
        self.formatters = make_formatters(self.config, stream_openers)
        return self.run_model()


class MyBehaveTestCase(LiveServerTestCase):

    first_time = True

    def __initial_data(self):
        """
        Método executado uma vez no início dos testes. Nesse ponto pode-se realizar a carga inicial para os testes.
        """

        # Laço passando por todos os 'caminhos'(path) dos modulos a serem testados
        for path in self.get_features_dir():
            # Acrescenta o nome do arquivo ao caminho
            test_file = path + "/test_initial_data.py"
            # Verifica se o arquivo "teste_dados_iniciais" existe naquele modulo
            if isfile(test_file):
                # Pega o caminho a partir de 'suap/' ([modulo]/features)
                str_module = path[len(settings.BASE_DIR) + 1:]
                # Substitui a '/' pelo '.'
                str_module = str_module.replace('/', '.')
                # Acrescenta o nome do arquivo e a função a ser chamada
                str_module += ".test_initial_data.initial_data"
                # Acrescenta a string à lista de caminhos de carga inicial
                settings.TEST_INITIAL_DATA.append(str_module)

        if self.first_time:
            for carga in settings.TEST_INITIAL_DATA:
                modulo = __import__(carga[: carga.rindex('.')], fromlist=carga[: carga.rindex('.')])
                str_funcao = carga[carga.rindex('.') + 1:]

                if hasattr(modulo, str_funcao):
                    funcao = getattr(modulo, str_funcao)
                    funcao()
            self.first_time = False

    def __init__(self, **kwargs):
        self.features_dir = kwargs.pop('features_dir')
        self.option_info = kwargs.pop('option_info')
        super().__init__(**kwargs)
        if settings.BEHAVE_AUTO_DOC_PATH:
            os.makedirs(settings.BEHAVE_AUTO_DOC_PATH, exist_ok=True)
        if settings.BEHAVE_AUTO_MOCK_PATH:
            os.makedirs(settings.BEHAVE_AUTO_MOCK_PATH, exist_ok=True)

    def setUp(self):
        self.__initial_data()
        self.setupBehave()

    def setupBehave(self):
        old_argv = sys.argv
        (sys.argv, _) = parse_argv(old_argv, self.option_info)

        self.behave_config = Configuration()
        sys.argv = old_argv

        self.behave_config.server_url = self.live_server_url  # property of LiveServerTestCase
        self.behave_config.paths = self.get_features_dir()
        self.behave_config.format = self.behave_config.format if self.behave_config.format else ['pretty']
        self.behave_config.debug = '--noinput' not in sys.argv

        # disable these in case you want to add set_trace in the tests you're developing
        if self.behave_config.stdout_capture:
            self.behave_config.stdout_capture = self.behave_config.stdout_capture
        else:
            self.behave_config.stdout_capture = False

        if self.behave_config.stderr_capture:
            self.behave_config.stderr_capture = self.behave_config.stderr_capture
        else:
            self.behave_config.stderr_capture = False

    def get_features_dir(self):
        if isinstance(self.features_dir, str):
            return [self.features_dir]
        return self.features_dir

    def runTest(self, result=None):
        runner = MyBehaveRunner(self.behave_config)
        failed = runner.run()

        try:
            undefined_steps = runner.undefined_steps
        except AttributeError:
            undefined_steps = runner.undefined

        if self.behave_config.show_snippets and undefined_steps:
            msg = "\nYou can implement step definitions for undefined steps with "
            msg += "these snippets:\n\n"
            printed = set()

            if sys.version_info[0] == 3:
                string_prefix = "('"
            else:
                string_prefix = "(u'"

            for step in set(undefined_steps):
                if step in printed:
                    continue
                printed.add(step)

                msg += "@" + step.step_type + string_prefix + step.name + "')\n"
                msg += "def impl(context):\n"
                msg += "    assert False\n\n"

            sys.stderr.write(escapes['undefined'] + msg + escapes['reset'])
            sys.stderr.flush()

        if failed:
            raise AssertionError('Existe(m) erro(s) nos testes!!!')


class MyBehaveTestRunner(DiscoverRunner):
    def __init__(self, *args, **kwargs):
        self.option_list, self.option_info = get_options()
        super().__init__(*args, **kwargs)

    @classmethod
    def add_arguments(cls, parser):
        # Set up to accept all of Behave's command line options and our own.  In
        # order to NOT conflict with Django's test command, we'll start all options
        # with the prefix "--behave_" (we'll only do the long version of an option).
        super().add_arguments(parser)
        option_list, cls.option_info = get_options()

        for option in option_list:
            parser.add_argument(*option._long_opts, action=option.action, dest=option.dest, help=option.help)

    def make_bdd_test_suite(self, features_dir):
        return MyBehaveTestCase(features_dir=features_dir, option_info=self.option_info)

    def build_suite(self, test_labels, extra_tests=None, **kwargs):
        suites = []
        features_dirs = []
        features = []
        if not test_labels:
            test_labels = sorted(settings.INSTALLED_APPS_SUAP)

        for label in test_labels:
            if '.' in label:
                continue
            app = get_app(label)
            features_dir = get_features(app)
            if features_dir is not None:
                features_dirs.append(features_dir)
                features.append(label)
                if self.parallel > 1:
                    suite = unittest.TestSuite()
                    suite.addTest(self.make_bdd_test_suite(features_dir))
                    suites.append(suite)

        # Forçando parallel
        if self.parallel > 1:
            parallel_suite = self.parallel_test_suite(suites, self.parallel, failfast=True)
            self.parallel = min(self.parallel, len(features))

            # If there's only one TestCase, parallelization isn't needed.
            if self.parallel > 1:
                suite = parallel_suite

        else:
            suite = unittest.TestSuite()
            suite.addTest(self.make_bdd_test_suite(features_dirs))

        print(f'test_behave {"parallel "+str(self.parallel) if self.parallel > 1 else ""} - {" ".join(features)}')
        return suite

    def teardown_test_environment(self, **kwargs):
        if settings.BEHAVE_AUTO_DOC:
            pattern = "documentacao_test_*.json"
            files = []
            for entry in os.listdir(settings.BEHAVE_AUTO_DOC_PATH):
                if fnmatch.fnmatch(entry, pattern):
                    files.append(f'{settings.BEHAVE_AUTO_DOC_PATH}/{entry}')
            json_file = f'{settings.BEHAVE_AUTO_DOC_PATH}/documentacao.json'

            aplicacoes = OrderedDict()
            for arquivo in files:
                with open(arquivo) as json_file_test:
                    json_apps = json.loads(json_file_test.read())
                    for key, value in json_apps["aplicacoes"].items():
                        aplicacoes[key] = value

            dicionario = {"aplicacoes": aplicacoes}
            with open(json_file, mode='w') as f:
                f.write(json.dumps(dicionario))

            for arquivo in files:
                os.remove(arquivo)
        super().teardown_test_environment(**kwargs)

    def setup_databases(self, **kwargs):
        database = super().setup_databases(**kwargs)
        return database
