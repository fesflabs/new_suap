# pylint: skip-file
# flake8: noqa
"""
Arquivo modelo do settings.py.
Aqui deve conter apenas o que há de diferente em relação ao settings_base.py,
como por exemplo senhas e outros dados sigilosos.
"""

import sys
import os
import json

from .settings_base import *

ALLOWED_HOSTS = os.environ.get('ALLOWED_HOSTS', '*').split(',')
DEBUG = os.environ.get('DEBUG', 'True') == 'True'

SITE_URL = os.environ.get('SITE_URL', 'http://localhost:8000')

SERVER_ALIAS = os.environ.get('SERVER_ALIAS', 'suap')

if not DEBUG:
    SECURE_PROXY_SSL_HEADER = os.environ.get('SECURE_PROXY_SSL_HEADER', 'HTTP_X_FORWARDED_PROTO,https').split(',')
else:
    CSRF_COOKIE_NAME = 'csrftoken'
    CSRF_COOKIE_SECURE = False
    SESSION_COOKIE_NAME = 'sessionid'
    SESSION_COOKIE_SECURE = False
    SUAP_CONTROL_COOKIE_NAME = 'suap-control'

admins = os.environ.get('ADMINS', 'Admin,admin@suap.net').split(':')
ADMINS = []
for admin in admins:
    ADMINS.append(admin.split(','))

EMAIL_HOST = os.environ.get('EMAIL_HOST', '')
EMAIL_PORT = os.environ.get('EMAIL_PORT', '')
EMAIL_HOST_USER = os.environ.get('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD', '')
EMAIL_SUBJECT_PREFIX = '[suap-erros] '
EMAIL_USE_TLS = os.environ.get('EMAIL_USE_TLS', 'False') == 'True'
DEFAULT_FROM_EMAIL = os.environ.get('DEFAULT_FROM_EMAIL', 'suap@naoresponder.ifrn.edu.br')
SERVER_EMAIL = DEFAULT_FROM_EMAIL
if DEBUG and not EMAIL_HOST:
    EMAIL_BACKEND = os.environ.get('EMAIL_BACKEND', 'djtools.email_debug.EmailBackend')

DATABASES = {
    'default': {
        'ENGINE': 'djtools.db.backends.postgresql',
        'NAME': os.environ.get('DATABASE_NAME', 'suap_dev'),
        'USER': os.environ.get('DATABASE_USER', 'postgres'),
        'PASSWORD': os.environ.get('DATABASE_PASSWORD', ''),
        'HOST': os.environ.get('DATABASE_HOST', '127.0.0.1'),
        'PORT': os.environ.get('DATABASE_PORT', '5432')
    },
}

ACADEMICO = {}
ACADEMICO['SISTEMA'] = os.environ.get('ACADEMICO_SISTEMA', 'q_academico')
ACADEMICO['DATABASE_ENGINE'] = os.environ.get('ACADEMICO_DATABASE_ENGINE', '')
ACADEMICO['DATABASE_NAME'] = os.environ.get('ACADEMICO_DATABASE_NAME', '')
ACADEMICO['DATABASE_USER'] = os.environ.get('ACADEMICO_DATABASE_USER', '')
ACADEMICO['DATABASE_PASSWORD'] = os.environ.get('ACADEMICO_DATABASE_PASSWORD', '')
ACADEMICO['DATABASE_HOST'] = os.environ.get('ACADEMICO_DATABASE_HOST', '')

SIABI = {}
SIABI['SISTEMA'] = os.environ.get('SIABI_SISTEMA', 'siabi')
SIABI['DATABASE_ENGINE'] = os.environ.get('SIABI_DATABASE_ENGINE', '')
SIABI['DATABASE_NAME'] = os.environ.get('SIABI_DATABASE_NAME', '')
SIABI['DATABASE_USER'] = os.environ.get('SIABI_DATABASE_USER', '')
SIABI['DATABASE_PASSWORD'] = os.environ.get('SIABI_DATABASE_PASSWORD', '')
SIABI['DATABASE_HOST'] = os.environ.get('SIABI_DATABASE_HOST', '')

SECRET_KEY = os.environ.get('SECRET_KEY', 'xru6&52s_b&vv5%!f@hyd)m&059z^x54q(s-=2-x9b1up(xiwn')
RECAPTCHA_PUBLIC_KEY = os.environ.get('RECAPTCHA_PUBLIC_KEY', '')
RECAPTCHA_PRIVATE_KEY = os.environ.get('RECAPTCHA_PRIVATE_KEY', '')

PRE_INSTALLED_APPS_SUAP += os.environ.get('PRE_INSTALLED_APPS_SUAP', '') and tuple(os.environ.get('PRE_INSTALLED_APPS_SUAP', '').split(',')) or ()

# Defina os módulos nessa propriedade caso queira que ela tenha seu menu e
INSTALLED_APPS_SUAP += os.environ.get('INSTALLED_APPS_SUAP', '') and tuple(os.environ.get('INSTALLED_APPS_SUAP', '').split(',')) or ()

POS_INSTALLED_APPS_SUAP += os.environ.get('POS_INSTALLED_APPS_SUAP', '') and tuple(os.environ.get('POS_INSTALLED_APPS_SUAP', '').split(',')) or ()

if DEBUG:
    PASSWORD_HASHERS = [
        'django.contrib.auth.hashers.UnsaltedMD5PasswordHasher',
        'django.contrib.auth.hashers.Argon2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2PasswordHasher',
        'django.contrib.auth.hashers.PBKDF2SHA1PasswordHasher',
        'django.contrib.auth.hashers.BCryptSHA256PasswordHasher',
        'django.contrib.auth.hashers.BCryptPasswordHasher',
    ]
    INTERNAL_IPS = ['127.0.0.1']
    MIDDLEWARE += (
        #    'debug_toolbar.middleware.DebugToolbarMiddleware',
    )
    POS_INSTALLED_APPS_SUAP += (
        #    'debug_toolbar',
    )

if USE_SENTRY:
    import sentry_sdk
    import subprocess
    from sentry_sdk.integrations.django import DjangoIntegration
    from sentry_sdk.integrations.redis import RedisIntegration
    from sentry_sdk.integrations.celery import CeleryIntegration

    sentry_sdk.init(
        dsn=os.environ.get('SENTRY_URL', 'http://token@sentry.ifrn.local/3'),
        integrations=[DjangoIntegration(), RedisIntegration(), CeleryIntegration()],
        #release=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=BASE_DIR)[:-1].decode(),
        environment='production',
        # If you wish to associate users to errors (assuming you are using
        # django.contrib.auth) you may enable sending PII data.
        traces_sample_rate=0.0,
        send_default_pii=True,
    )
    sentry_sdk.set_tag("suap.server.name", SERVER_ALIAS)

MOODLE_URL_API = os.environ.get('MOODLE_URL_API', 'http://localhost/moodle/local/suap/api/')
MOODLE_SYNC_TOKEN = ''

if USE_REDIS:
    SESSION_ENGINE = 'django.contrib.sessions.backends.cache'
    SESSION_CACHE_ALIAS = 'session'
    CACHES = {
        'default': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ.get('REDIS_LOCATION', 'redis://127.0.0.1:6379/1'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'PASSWORD': os.environ.get('REDIS_PASSWORD', '')
            }
        },
        'session': {
            'BACKEND': 'django_redis.cache.RedisCache',
            'LOCATION': os.environ.get('SESSION_LOCATION', 'redis://127.0.0.1:6379/2'),
            'OPTIONS': {
                'CLIENT_CLASS': 'django_redis.client.DefaultClient',
                'PASSWORD': os.environ.get('SESSION_PASSWORD', '')
            }
        }
    }

TEMPLATES[0]['OPTIONS']['debug'] = DEBUG
PIPELINE['PIPELINE_ENABLED'] = not DEBUG

# ESSE TRECHO É PARA GARANTIR QUE TODOS OS MODULOS ESPECIFICADOS AQUI NO PRE_INSTALLED_APPS_SUAP OU INSTALLED_APPS_SUAP OU
#  POS_INSTALLED_APPS_SUAP ESTEJAM REPLICADOS EM INSTALLED_APPS
INSTALLED_APPS = PRE_INSTALLED_APPS_SUAP + INSTALLED_APPS_SUAP + POS_INSTALLED_APPS_SUAP

GHOSTSCRIPT_CMD = os.environ.get('GHOSTSCRIPT_CMD', '/usr/bin/gs')

BEHAVE_CHROME_HEADLESS = os.environ.get('BEHAVE_CHROME_HEADLESS', 'True') != 'False'
BEHAVE_CHROME_WEBDRIVER = os.environ.get('BEHAVE_CHROME_WEBDRIVER', '/usr/local/bin/chromedriver')

BEHAVE_AUTO_DOC = os.environ.get('BEHAVE_AUTO_DOC', 'False') == 'True'
BEHAVE_AUTO_DOC_PATH = os.environ.get('BEHAVE_AUTO_DOC_PATH', os.path.join(BASE_DIR, 'deploy/media/documentacao'))
BEHAVE_AUTO_MOCK = os.environ.get('BEHAVE_AUTO_MOCK', 'False') == 'True'
BEHAVE_AUTO_MOCK_PATH = os.environ.get('BEHAVE_AUTO_MOCK_PATH', os.path.join(BASE_DIR, 'deploy/media/sql'))

TRUSTED_CERTS_DIRECTORY = os.path.join(BASE_DIR, 'certs')

if USE_CELERY:
    CELERY_BROKER_URL = os.environ.get('CELERY_BROKER_URL', 'redis://localhost:6379/3')
    CELERY_RESULT_BACKEND = os.environ.get('CELERY_RESULT_BACKEND', 'redis://localhost:6379/4')
    CELERY_ACCEPT_CONTENT = ['application/json']
    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-task_serializer
    CELERY_TASK_SERIALIZER = 'json'
    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#std:setting-result_serializer
    CELERY_RESULT_SERIALIZER = 'json'
    # http://docs.celeryproject.org/en/latest/userguide/configuration.html#beat-scheduler
    CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"
    TASK_QUEUES_CELERY = {}
    tasks = os.environ.get('CELERY_TASK_QUEUES', '') and os.environ.get('CELERY_TASK_QUEUES', '').split(':') or ()
    for task in tasks:
        key, value = task.split(',')
        TASK_QUEUES_CELERY[key] = value

MOODLE_SYNC_TOKEN = os.environ.get('MOODLE_SYNC_TOKEN', '')

for key, value in list(os.environ.items()):
    if key.startswith('SUAP_'):
        key = key.replace('SUAP_', '')
        try:
            globals()[key] = json.loads(value.replace("'", '"'))
        except ValueError:
            globals()[key] = value


# Modulos FESFS-SUS
del(OAUTH2_PROVIDER_APPLICATION_MODEL, OAUTH2_PROVIDER)
INSTALLED_APPS_SUAP = ('comum', 'ldap_backend', 'rh', 'processo_eletronico', 'conectagov_pen', 'documento_eletronico','processo_seletivo', 'estagios', 'convenios', 'edu', 'ppe', 'residencia')
INSTALLED_APPS = PRE_INSTALLED_APPS_SUAP + INSTALLED_APPS_SUAP + POS_INSTALLED_APPS_SUAP


# # - - - - - - - - - - - - - - -
# # Catálogo Provedor de Serviço
# # - - - - - - - - - - - - - - -
# # Descomente estre trecho caso esteja usando o módulo Catálogo Provedor de Serviço em ambiente de desenvolvimento.
# # {id_servico_portal_govbr de producao: id_servico_portal_govbr do ambiente de treinamento}
#
# Gov Br Produção:
# https://www.servicos.gov.br/api/v1/servicos/orgao/439
#

# Gov Br Treinamento:
# https://servicos.treina.nuvem.gov.br/api/v1/servicos/orgao/439  <<< Usar este para fazer o DE PARA.
# https://servicos.nuvem.gov.br/api/v1/servicos/orgao  <<< Endereço antigo.
#
# SERVICO_ID_AMBIENTE_TREINAMENTO = {6024: 4202,
#                                    6424: 4602,
#                                    6410: 4588,
#                                    6176: 4354,
#                                    10056: 3315,
#                                    10054: 3315}
# # Obs: Para o código de produção "10054 - Matricular-se em Curso de Pós-Graduação - IFRN" não achei equivalente
# # no ambiente de Gov Br de Treinamento, por isso estou apontando temporariamente para o servico 3315.
#
# def get_id_servico_portal_govbr(id_servico_portal_govbr):
#     '''
#     Este método foi criado para fazer o "DE PARA" entre os IDs dos serviços da base GOV BR de Produção e a base GOV BR
#     de treinamento. André já solicitou junto ao pessoal do GOV BR a correção disso. Até lá usaremos desse recurso para
#     continuar trabalhando.
#
#     :param id_servico_portal_govbr Id do GOV BR de produção
#     :return: id_servico_portal_govbr Id do GOV BR de treinamento
#     '''
#     result = SERVICO_ID_AMBIENTE_TREINAMENTO.get(id_servico_portal_govbr)
#     if not result:
#         raise Exception('Não foi possível traduzir o código {} para o código usado em ambiente de treinamento do ' 'Governo Federal'.format(id_servico_portal_govbr))
#     return result
SERVICE_PROVIDER_FACTORY = os.environ.get('SERVICE_PROVIDER_FACTORY', 'catalogo_provedor_servico.providers.impl.ifrn.factory.IfrnServiceProviderFactory')

DEFAULT_FILE_STORAGE = os.environ.get('DEFAULT_FILE_STORAGE', 'djtools.storages.storage.FileSystemStoragePlus')
if DEFAULT_FILE_STORAGE == 'djtools.storages.s3.MediaS3Storage':
    AWS_S3_SIGNATURE_VERSION = os.environ.get('AWS_S3_SIGNATURE_VERSION', 's3v4')
    AWS_S3_REGION_NAME = os.environ.get('AWS_S3_REGION_NAME', 'us-east-2')
    AWS_S3_CUSTOM_DOMAIN = os.environ.get('AWS_S3_CUSTOM_DOMAIN', None)
    AWS_S3_ENDPOINT_URL = os.environ.get('AWS_S3_ENDPOINT_URL', None)  # 'http://minio.suap.ifrn.edu.br:9000'

    AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'teste')
    AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'testeteste')
    STATICFILES_STORAGE = os.environ.get('STATICFILES_STORAGE', 'pipeline.storage.PipelineStorage')  # djtools.storages.s3.S3PipelineStorage

    AWS_MEDIA_BUCKET_NAME = os.environ.get('AWS_MEDIA_BUCKET_NAME', 'media')
    AWS_STATIC_BUCKET_NAME = os.environ.get('AWS_STATIC_BUCKET_NAME', 'static')
    AWS_TEMP_BUCKET_NAME = os.environ.get('AWS_TEMP_BUCKET_NAME', 'temp')
    AWS_STORAGE_BUCKET_NAME = os.environ.get('AWS_STORAGE_BUCKET_NAME', 'suap')


# As configurações de testes devem vir no final do arquivo para sobrescrver todas as outras configurações
if 'test_suap' in sys.argv or 'test' in sys.argv or 'test_behave' in sys.argv:
    DEBUG = False
    DEFAULT_DATABASE_TEST = 'test_suap_dev'
    DATABASES['default']['TEST'] = {'NAME': DEFAULT_DATABASE_TEST, 'CONN_MAX_AGE': 0}
    PASSWORD_HASHERS = ('django.contrib.auth.hashers.MD5PasswordHasher',)
    DEFAULT_FILE_STORAGE = 'djtools.storages.storage.FileSystemStoragePlus'
    MIGRATION_MODULES = DisableMigrations()
    CSRF_COOKIE_NAME = 'csrftoken'
    SESSION_COOKIE_NAME = 'sessionid'
    USE_REDIS = False
    USE_SENTRY = False
    USE_CELERY = False
