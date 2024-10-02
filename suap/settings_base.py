# pylint: skip-file
# flake8: noqa

import logging

from os.path import abspath, dirname, join, exists
from os import makedirs
import os
import datetime
import tempfile

TIPO_ARVORE_SETORES = os.environ.get('TIPO_ARVORE_SETORES', 'SUAP')  # 'SUAP|SIAPE'

USE_REDIS = os.environ.get('USE_REDIS', 'False') == 'True'
USE_SENTRY = os.environ.get('USE_SENTRY', 'False') == 'True'
USE_CELERY = os.environ.get('USE_CELERY', 'False') == 'True'
USE_ELASTICSEARCH = os.environ.get('USE_ELASTICSEARCH', 'False') == 'True'
USE_HISTORY = os.environ.get('USE_HISTORY', 'False') == 'True'
USE_EDU_LOG = os.environ.get('USE_EDU_LOG', 'True') == 'True'

SITE_URL = 'http://localhost:8000'
BASE_DIR = dirname(dirname(abspath(__file__)))
PROJECT_NAME = BASE_DIR.split('/')[-1]

EMAIL_HOST = ''
EMAIL_PORT = ''
EMAIL_HOST_USER = ''
EMAIL_HOST_PASSWORD = ''
EMAIL_SUBJECT_PREFIX = '[suap-erros] '
EMAIL_USE_TLS = ''

DEFAULT_FROM_EMAIL = 'suap@naoresponder.ifrn.edu.br'

MONTH_DAY_FORMAT = r'd \d\e F'
YEAR_MONTH_FORMAT = r'F \d\e Y'

DATABASES = {'default': {'ENGINE': 'django.db.backends.postgresql', 'NAME': 'suap', 'USER': 'postgres', 'PASSWORD': '', 'HOST': '127.0.0.1', 'PORT': '5432'}}

ACADEMICO = {}
ACADEMICO['SISTEMA'] = 'q_academico'
ACADEMICO['DATABASE_NAME'] = ''
ACADEMICO['DATABASE_USER'] = ''
ACADEMICO['DATABASE_PASSWORD'] = ''
ACADEMICO['DATABASE_HOST'] = ''

SIABI = {}
SIABI['SISTEMA'] = 'siabi'
SIABI['DATABASE_ENGINE'] = ''
SIABI['DATABASE_NAME'] = ''
SIABI['DATABASE_USER'] = ''
SIABI['DATABASE_PASSWORD'] = ''
SIABI['DATABASE_HOST'] = ''
DATABASE_ROUTERS = ['ldap_backend.router.SuapRouter']

SUAP_TESTS = {}
SUAP_TESTS['SALVAR_CENARIO'] = False
SUAP_TESTS['MANTER_JSON'] = False

TIME_ZONE = 'America/Recife'
LANGUAGE_CODE = 'pt-br'
DATE_FORMAT = 'd/m/Y'
DATE_INPUT_FORMATS = ('%Y-%m-%d', '%d/%m/%Y')
DATETIME_FORMAT = 'd/m/Y H:i'
DATETIME_INPUT_FORMATS = ('%Y-%m-%dT%H:%M:%S', '%d/%m/%Y %H:%M:%S', '%d/%m/%Y %H:%M')

STATICFILES_FINDERS = ('django.contrib.staticfiles.finders.FileSystemFinder', 'django.contrib.staticfiles.finders.AppDirectoriesFinder', 'pipeline.finders.PipelineFinder')

STATICFILES_STORAGE = 'djtools.storages.pipeline.CacheControlPipelineStorage'

DEFAULT_STORAGE = 'djtools.storages.storage.FileSystemStoragePlus'

STATIC_ROOT = join(BASE_DIR, 'static')
STATIC_URL = '/static/'
ADMIN_MEDIA_PREFIX = '/static/admin/'

MEDIA_ROOT = join(BASE_DIR, 'deploy/media')
TEMP_DIR = join(MEDIA_ROOT, 'tmp')
tempfile.tempdir = TEMP_DIR
FILE_UPLOAD_TEMP_DIR = TEMP_DIR

if not exists(TEMP_DIR):
    makedirs(TEMP_DIR)
MEDIA_URL = '/media/'
TEMP_URL = '/media/tmp/'
NOCAPTCHA = True

# Arquivos de midia (futuramente as midias serão movidas para uma particao específica)
MEDIA_PUBLIC = join(BASE_DIR, 'deploy/media/public-media')
MEDIA_PRIVATE = join(BASE_DIR, 'deploy/media/private-media')
MEDIA_PRIVATE_URL = '/djtools/private_media/?media='

SECRET_KEY = 'xru6&52s_b&vv5%!f@hyd)m&059z^x54q(s-=2-x9b1up(xiwn'

MIDDLEWARE = (
    # Middlewares do django
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    # 'djtools.middleware.session_middleware.SessionMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.contrib.admindocs.middleware.XViewMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'django.middleware.gzip.GZipMiddleware',
    # Middlewares do suap
    'djtools.middleware.userinfo.UserInfoMiddleware',
    'djtools.middleware.threadlocals.ThreadLocals',
    'djtools.middleware.servidor_sem_setor.ServidorSemSetorMiddleware',
    'djtools.middleware.change_process_name.ChangeProcessNameMiddleware',
    'djtools.middleware.seleciona_vinculo.SelecionaVinculoMiddleware',
    # 'djtools.middleware.online_now_middleware.OnlineNowMiddleware',
    'reversion.middleware.RevisionMiddleware',
    # 'djtools.middleware.previnir_multiplos_logins.UserRestrict',
    'djtools.middleware.minify_html.MinifyHTMLMiddleware',
    # deve ser removido assim que o problema no pacote django-pipeline for resolvido
    # 'edu.middleware.titulacao.InformarTitulacaoMiddleware',
)

X_FRAME_OPTIONS = 'SAMEORIGIN'

DEFAULT_AUTO_FIELD = 'django.db.models.AutoField'

ROOT_URLCONF = 'suap.urls'

LOGIN_URL = '/accounts/login/'
LOGOUT_URL = '/accounts/logout/'
LOGIN_REDIRECT_URL = '/'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': ['%s/templates' % (BASE_DIR), '%s/comum/templates' % (BASE_DIR), '%s/djtools/templates/adminutils' % (BASE_DIR), BASE_DIR],
        'APP_DIRS': True,
        'OPTIONS': {
            'builtins': [
                'djtools.templatetags.filters.utils',
                'djtools.templatetags.filters.ajax',
                'djtools.templatetags.filters.sanitize',
                'djtools.templatetags.tags.pagination',
                'djtools.templatetags.tags.renders',
                'djtools.templatetags.tags.utils',
            ],
            'context_processors': [
                'django.contrib.auth.context_processors.auth',
                'django.template.context_processors.debug',
                'django.template.context_processors.i18n',
                'django.template.context_processors.media',
                'django.template.context_processors.request',
                'django.template.context_processors.tz',
                'django.contrib.messages.context_processors.messages',
                'comum.utils.suap_context_processor',
            ],
            'debug': True,
        },
    }
]


class DisableMigrations:
    def __contains__(self, item):
        return True

    def __getitem__(self, item):
        return None


PRE_INSTALLED_APPS_SUAP = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'djtools',  # O djtools deve vir antes de django.contrib.admin
    'django.contrib.admin',
    'captcha',
    'django.contrib.postgres',
)

# Todas as apps inclusas na lista abaixo serão testadas ao executar o comando test_suap
INSTALLED_APPS_SUAP = (
    'comum',
    'rh',
    'almoxarifado',
    'edu',
    'catalogo_provedor_servico',
    'gestao',
    'patrimonio',
    'ponto',
    'centralservicos',
    'contracheques',
    'protocolo',
    'frota',
    'financeiro',
    'ldap_backend',
    'chaves',
    'estacionamento',
    'cursos',
    'remanejamento',
    'contratos',
    'planejamento',
    'convenios',
    'orcamento',
    'materiais',
    'projetos',
    'compras',
    'pedagogia',
    'ae',
    'cnpq',
    'pdi',
    'cpa',
    'processo_seletivo',
    'saude',
    'arquivo',
    'microsoft',
    'ferias',
    'eleicao',
    'enquete',
    'rsc',
    'progressoes',
    'estagios',
    'portaria',
    'pesquisa',
    'avaliacao_integrada',
    'clipping',
    'temp_rh2',
    'acumulocargo',
    'plan_v2',
    'demandas',
    'api',
    'professor_titular',
    'ps',
    'etep',
    'documento_eletronico',
    'processo_eletronico',
    'avaliacao_cursos',
    'eventos',
    'encceja',
    'egressos',
    'gerenciador_projetos',
    'pit_rit',
    'pit_rit_v2',
    'plan_estrategico',
    'integracao_wifi',
    'acompanhamentofuncional',
    'conectagov_pen',
    'sica',
    'calculos_pagamentos',
    'demandas_externas',
    'tesouro_gerencial',
    'boletim_servico',
    'auxilioemergencial',
    'licenca_capacitacao',
    'erros',
    'pdp_ifrn',
    'processmining',
    'siads',
    'labfisico',
)

POS_INSTALLED_APPS_SUAP = (
    'django_extensions',
    'django_tables2',
    'ckeditor',
    'reversion',  # https://github.com/etianen/django-reversion
    'reversion_compare',  # https://github.com/jedie/django-reversion-compare
    'rest_framework_swagger',
    'rest_framework.authtoken',
    'corsheaders',
    'sass_processor',
    'pipeline',
    # Documento e Processo Eletrônico
    'django_fsm',
    'crispy_forms',
    # 'wkhtmltopdf',
    'mptt',
    'formtools',
    'rest_framework',
    'oauth2_provider',
    'django_celery_beat',
    # 'social_django',
)

# app externa 'rest_framework_swagger' deve vir depois da app suap 'api' e fora do escopo do 'test_suap'
INSTALLED_APPS = PRE_INSTALLED_APPS_SUAP + INSTALLED_APPS_SUAP + POS_INSTALLED_APPS_SUAP

# CSRF
CSRF_COOKIE_HTTPONLY = True
CSRF_COOKIE_SECURE = True
# CSRF_COOKIE_SAMESITE = 'Strict'
CSRF_COOKIE_NAME = '__Host-csrftoken'
CSRF_COOKIE_AGE = (30 * 24 * 60 * 60) - (3 * 60 * 60)  # 1 mês de acordo com a demanda #1133 -3 horas do horário de verão


CKEDITOR_UPLOAD_PATH = {'/dev/null/'}

CKEDITOR_CONFIGS = {
    'default': {
        'skin': 'moono-lisa',
        'toolbar_Basic': [['Source', '-', 'Bold', 'Italic']],
        'toolbar_YourCustomToolbarConfig': [
            {'name': 'document', 'items': ['Source', 'Preview', '-', 'Maximize', 'ShowBlocks']},
            {'name': 'clipboard', 'items': ['Save', 'Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'editing', 'items': ['Find', 'Replace', '-', 'SelectAll']},
            '/',
            {'name': 'basicstyles', 'items': ['Bold', 'Italic', 'Underline', 'CopyFormatting', '-', 'Strike', 'Subscript', 'Superscript', 'RemoveFormat']},
            {
                'name': 'paragraph',
                'items': [
                    'NumberedList',
                    'BulletedList',
                    '-',
                    'Outdent',
                    'Indent',
                    'textindent',
                    '-',
                    'Blockquote',
                    'CreateDiv',
                    '-',
                    'JustifyLeft',
                    'JustifyCenter',
                    'JustifyRight',
                    'JustifyBlock',
                    '-',
                    'BidiLtr',
                    'BidiRtl',
                ],
            },
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'insert', 'items': ['base64image', 'Table', 'HorizontalRule', 'SpecialChar', 'PageBreak']},
            '/',
            {'name': 'styles', 'items': ['lineheight', 'Styles', 'Format', 'Font', 'FontSize', 'Size']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
        ],
        'toolbar_DocumentoEletronicoConfig': [
            {'name': 'document', 'items': ['Source', 'Preview', '-', 'Maximize', 'ShowBlocks']},
            {'name': 'clipboard', 'items': ['Save', 'Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'editing', 'items': ['SelectAll']},
            '/',
            {'name': 'basicstyles', 'items': ['Bold', 'Italic', 'Underline', 'CopyFormatting', '-', 'Strike', 'RemoveFormat']},
            {
                'name': 'paragraph',
                'items': [
                    'NumberedList',
                    'BulletedList',
                    '-',
                    'Outdent',
                    'Indent',
                    '-',
                    'Blockquote',
                    'CreateDiv',
                    '-',
                    'JustifyLeft',
                    'JustifyCenter',
                    'JustifyRight',
                    'JustifyBlock',
                    '-',
                ],
            },
            {'name': 'texttransform', 'items': ['TransformTextToUppercase', 'TransformTextToLowercase', 'TransformTextCapitalize', 'TransformTextSwitcher']},
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'insert', 'items': ['base64image', 'Table', 'HorizontalRule', 'SpecialChar', 'PageBreak']},
            '/',
            {'name': 'styles', 'items': ['lineheight', 'Format', 'Font', 'FontSize', 'Size']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'indent', 'items': ['textindent']},
        ],
        'toolbar': 'DocumentoEletronicoConfig',  # put selected toolbar config here
        'width': '100%',
        'filebrowserWindowHeight': 725,
        'filebrowserWindowWidth': 940,
        'toolbarCanCollapse': True,
        'extraPlugins': ','.join(
            [
                'base64image',
                'copyformatting',
                'tableresize',
                'tabletools',
                'lineheight',
                'richcombo',
                'floatpanel',
                'panel',
                'listblock',
                'autosave',
                'simple-ruler',
                'button',
                'textindent',
                'texttransform'
            ]
        ),
        'removePlugins': 'resize,elementspath,stylesheetparser',
        'removeDialogTabs': 'image:advanced;link:advanced',
        'line_height': '1em;1.15em;1.5em;2em;3em;3.5em',
        'indentation': '94.5',  # 2.5cm em px
        'disableNativeSpellChecker': False,
        'allowedContent': True,
        'extraAllowedContent': 'iframe[*]',
    },
    'full': {'toolbar': 'full'},
    'basic_suap': {
        'skin': 'moono-lisa',
        'toolbar_YourCustomToolbarConfig': [
            {'name': 'document', 'items': ['Preview', '-', 'Maximize', 'ShowBlocks']},
            {'name': 'clipboard', 'items': ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'editing', 'items': ['Find', 'Replace', '-', 'SelectAll']},
            '/',
            {'name': 'basicstyles', 'items': ['Bold', 'Italic', 'Underline', 'CopyFormatting', '-', 'Strike', 'Subscript', 'Superscript', 'RemoveFormat']},
            {
                'name': 'paragraph',
                'items': [
                    'NumberedList',
                    'BulletedList',
                    '-',
                    'Outdent',
                    'Indent',
                    'textindent',
                    '-',
                    'Blockquote',
                    'CreateDiv',
                    '-',
                    'JustifyLeft',
                    'JustifyCenter',
                    'JustifyRight',
                    'JustifyBlock',
                    '-',
                    'BidiLtr',
                    'BidiRtl',
                ],
            },
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'insert', 'items': ['base64image', 'Table', 'HorizontalRule', 'SpecialChar', 'PageBreak']},
            '/',
            {'name': 'styles', 'items': ['lineheight', 'Styles', 'Format', 'Font', 'FontSize', 'Size']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'indent', 'items': ['textindent']},
        ],
        'toolbar': 'YourCustomToolbarConfig',  # put selected toolbar config here
        'width': '100%',
        'filebrowserWindowHeight': 725,
        'filebrowserWindowWidth': 940,
        'toolbarCanCollapse': True,
        'tabSpaces': 4,
        'extraPlugins': ','.join(
            ['base64image', 'copyformatting', 'tableresize', 'tabletools', 'lineheight', 'richcombo', 'floatpanel', 'panel', 'listblock', 'button', 'textindent']
        ),
        'removePlugins': 'resize,elementspath,stylesheetparser',
        'removeDialogTabs': 'image:advanced;link:advanced',
        'line_height': '1em;1.15em;1.5em;2em;3em;3.5em',
        'disableNativeSpellChecker': False,
        'allowedContent': True,
        'extraAllowedContent': 'iframe[*]',
    },
    'basico_sem_imagem': {
        'skin': 'moono-lisa',
        'toolbar_YourCustomToolbarConfig': [
            {'name': 'document', 'items': ['Preview', '-', 'Maximize', 'ShowBlocks']},
            {'name': 'clipboard', 'items': ['Cut', 'Copy', 'Paste', 'PasteText', 'PasteFromWord', '-', 'Undo', 'Redo']},
            {'name': 'editing', 'items': ['Find', 'Replace', '-', 'SelectAll']},
            '/',
            {'name': 'basicstyles', 'items': ['Bold', 'Italic', 'Underline', 'CopyFormatting', '-', 'Strike', 'Subscript', 'Superscript', 'RemoveFormat']},
            {
                'name': 'paragraph',
                'items': [
                    'NumberedList',
                    'BulletedList',
                    '-',
                    'Outdent',
                    'Indent',
                    'textindent',
                    '-',
                    'Blockquote',
                    'CreateDiv',
                    '-',
                    'JustifyLeft',
                    'JustifyCenter',
                    'JustifyRight',
                    'JustifyBlock',
                    '-',
                    'BidiLtr',
                    'BidiRtl',
                ],
            },
            {'name': 'links', 'items': ['Link', 'Unlink', 'Anchor']},
            {'name': 'insert', 'items': ['Table', 'HorizontalRule', 'SpecialChar', 'PageBreak']},
            '/',
            {'name': 'styles', 'items': ['lineheight', 'Styles', 'Format', 'Font', 'FontSize', 'Size']},
            {'name': 'colors', 'items': ['TextColor', 'BGColor']},
            {'name': 'indent', 'items': ['textindent']},
        ],
        'toolbar': 'YourCustomToolbarConfig',  # put selected toolbar config here
        'width': '100%',
        'filebrowserWindowHeight': 725,
        'filebrowserWindowWidth': 940,
        'toolbarCanCollapse': True,
        'tabSpaces': 4,
        'extraPlugins': ','.join(
            ['copyformatting', 'tableresize', 'tabletools', 'lineheight', 'richcombo', 'floatpanel', 'panel', 'listblock', 'button', 'textindent', 'blockimagepaste']
        ),
        'removePlugins': 'resize,elementspath,stylesheetparser,base64image',
        'removeDialogTabs': 'image:advanced;link:advanced',
        'line_height': '1em;1.15em;1.5em;2em;3em;3.5em',
        'disableNativeSpellChecker': False,
        'allowedContent': True,
        'extraAllowedContent': 'iframe[*]',
    },
}

if 'ldap_backend' in INSTALLED_APPS:
    AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend', 'ldap_backend.ldap_backend.LdapBackend')
else:
    AUTHENTICATION_BACKENDS = ('django.contrib.auth.backends.ModelBackend',)

LDAP_GROUP_SERVIDOR = 'CN=G_SERVIDORES,OU=IFRN,DC=ifrn,DC=local'
LDAP_GROUP_GOOGLE_CLASSROOM = 'CN=Professores que usam o Google Sala de Aula,OU=COINRE,OU=DIGTI,OU=RE,OU=IFRN,DC=ifrn,DC=local'

AUTH_USER_MODEL = 'comum.User'

SESSION_ENGINE = 'django.contrib.sessions.backends.file'
SESSION_FILE_PATH = join(BASE_DIR, 'deploy/sessions')

SESSION_SERIALIZER = 'django.contrib.sessions.serializers.PickleSerializer'
SESSION_COOKIE_AGE = 1 * 24 * 60 * 60  # tempo em segundos
# SESSION_COOKIE_SAMESITE = 'Strict'
SESSION_COOKIE_NAME = '__Host-sessionid'
SESSION_COOKIE_SECURE = True

SUAP_CONTROL_COOKIE_NAME = '__Host-suap-control'

SECURE_BROWSER_XSS_FILTER = True

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse'
        }
    },
    'handlers': {
        'file': {
            'level': 'DEBUG', 'class': 'logging.FileHandler', 'filename': join(BASE_DIR, 'deploy/logs/debug.log')
        },
        'history': {
            'level': 'DEBUG', 'class': 'logging.FileHandler', 'filename': join(BASE_DIR, 'deploy/logs/history/history.log')
        },
    },
    'loggers': {
        'behave': {
            'handlers': ['file'], 'level': 'DEBUG', 'propagate': False
        },
        'history': {
            'handlers': ['history'], 'level': 'DEBUG', 'propagate': False
        }
    },
}

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
WSGI_APPLICATION = 'suap.wsgi.application'

REST_FRAMEWORK = {
    'DEFAULT_RENDERER_CLASSES': ('rest_framework.renderers.JSONRenderer', 'rest_framework.renderers.BrowsableAPIRenderer'),
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'oauth2_provider.contrib.rest_framework.OAuth2Authentication',
        'rest_framework.authentication.TokenAuthentication',
        'rest_framework.authentication.SessionAuthentication',
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 100,
    'DEFAULT_SCHEMA_CLASS': 'rest_framework.schemas.coreapi.AutoSchema',
}

OAUTH2_PROVIDER_APPLICATION_MODEL = 'api.AplicacaoOAuth2'
OAUTH2_PROVIDER = {
    'REQUEST_APPROVAL_PROMPT': 'auto',
    'SCOPES': {
        'identificacao': 'Seu nome, campus e identificação/matrícula',
        'email': 'Seus endereços de e-mail (institucional, acadêmico e secundário/pessoal)',
        'contracheques': 'Seus contracheques',
        'documentos_pessoais': 'CPF, data de nascimento e sexo.',
        'integra': 'CPF e alguns outros dados dos servidores ativos para integração com o portal Integra.',
    },
    'SCOPES_BACKEND_CLASS': 'api.backends.SuapScopes',
    'DEFAULT_SCOPES': ['identificacao', 'email'],
    'APPLICATION_ADMIN_CLASS': 'api.admin.AplicacaoOAuth2Admin'
}

SWAGGER_SETTINGS = {
    'info': {
        'contact': 'digti@ifrn.edu.br',
        # 'description': 'Documentação da cópia da base do CNES do LAIS',
        # 'license': 'Apache 2.0',
        # 'licenseUrl': 'http://www.apache.org/licenses/LICENSE-2.0.html',
        # 'termsOfServiceUrl': 'http://helloreverb.com/terms/',
        'title': 'SUAP API Rest',
    },
    'api_version': '1.0',
    'is_authenticated': True,
    # 'doc_expansion': 'list',
    'doc_expansion': 'none',
    'SECURITY_DEFINITIONS': None,
    # 'exclude_namespaces': ['suapurls'],
    # 'exclude_url_names': [],
    # 'api_path': '/',
    # 'base_path': '',
    # 'enabled_methods': ['get', 'post', 'put', 'patch', 'delete'],
    # 'api_key': '123',
    # 'is_superuser': False,
    # 'unauthenticated_user': 'django.contrib.auth.models.AnonymousUser',
    'permission_denied_handler': 'api.services_utils.permission_denied_handler',
    # 'resource_access_handler': 'Token',
    # 'token_type': 'comum.views.resource_access_handler',
    # 'base_path': 'integra.telessaude.ufrn.br/api-docs',
    'exclude_app_names': ['edu', 'rh', 'contracheques'],  # chave exclusiva utilizada pelo SUAP.
}

ACCESS_LOG = True
AUTHN_LOG = False
AUTHZ_LOG = True
ACCESS_LOG_MODULES = ['centralservicos']

# Documento Eletrônico
DOC_SECRET_KEY = 'xru6&52s_b&vv5%!f@hyd)m&059z^x54q(s-=2-x9b1up(xiwn'
# Add to your settings file
CONTENT_TYPES = ['pdf']


DEFAULT_UPLOAD_ALLOWED_IMAGE_EXTENSIONS = ['jpg', 'jpeg', 'png']
DEFAULT_UPLOAD_ALLOWED_DATA_EXTENSIONS = ['xlsx', 'xls', 'csv', 'txt']
DEFAULT_UPLOAD_ALLOWED_DOCUMENT_EXTENSIONS = ['docx', 'doc', 'pdf']
DEFAULT_UPLOAD_ALLOWED_EXTENSIONS = DEFAULT_UPLOAD_ALLOWED_IMAGE_EXTENSIONS + DEFAULT_UPLOAD_ALLOWED_DATA_EXTENSIONS + DEFAULT_UPLOAD_ALLOWED_DOCUMENT_EXTENSIONS + ['zip']

# 1.00    MB  1024    KB  1048576     Bytes
# 2.50    MB  2560    KB  2621440     Bytes
# 5.00    MB  5120    KB  5242880     Bytes
# 10.00   MB  10240   KB  10485760    Bytes
# 20.00   MB  20480   KB  20971520    Bytes
# 50.00   MB  51200   KB  52428800    Bytes
# 100.00  MB  102400  KB  104857600   Bytes
# 250.00  MB  256000  KB  262144000   Bytes
# 500.00  MB  512000  KB  524288000   Bytes
BYTES_SIZE_1MB = 1048576
PROCESSO_ELETRONICO_DOCUMENTO_EXTERNO_MAX_UPLOAD_SIZE = 10 * BYTES_SIZE_1MB  # 10 MB

# Tamanho máximo aceitável para ser tratado diretamente na memória antes de ser enviado para o sistema de arquivos
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * BYTES_SIZE_1MB  # 5 MB

# Tamanho máximo padrão para upload de arquivos
DEFAULT_FILE_UPLOAD_MAX_SIZE = 10 * BYTES_SIZE_1MB

# Tamanho máximo de informação presente num request (excluindo uploads de arquivo). Por padrão, o valor é 2.5 MB
# (2621440 bytes). Caso o tamanho exceda esse valor, será lançada uma exceção Bad Request 500 - RequestDataTooBig.
# Isso pode ocorrer nos documentos de texto criados dentro do módulo de Documento Eletrônico, uma vez que as imagens
# presentes acabam sendo texto (string base 64).
# /django/conf/global_settings.py
DATA_UPLOAD_MAX_MEMORY_SIZE = 100 * BYTES_SIZE_1MB  # 10 MB

#
SIGNER_MAX_AGE = 60000
# Esse é o caminho da ferramenta usada para gerar os PDFs dos documentos criados.
# Lembrese de instalar no S.O:
# Mac OS X: brew install Caskroom/cask/wkhtmltopdf
WKHTMLTOPDF_CMD = '/usr/bin/wkhtmltopdf'
# Absolute path to Ghostscript executable here or command name if Ghostscript is
# in your PATH.
GHOSTSCRIPT_CMD = "/usr/local/bin/gs"

PDFUNITE_CMD = "/usr/bin/pdfunite"

TEST_RUNNER = 'comum.tests.runner.DiscoverageRunner'

# Configurações do CORS
CORS_ALLOW_ALL_ORIGINS = False

# Configurações do JWT
JWT_AUTH = {
    'JWT_VERIFY': True,
    'JWT_VERIFY_EXPIRATION': True,
    'JWT_ALLOW_REFRESH': True,
    'JWT_EXPIRATION_DELTA': datetime.timedelta(hours=24),
    'JWT_REFRESH_EXPIRATION_DELTA': datetime.timedelta(days=7),
    'JWT_AUTH_HEADER_PREFIX': 'JWT',
}

LPS = 'fesfsus'
DATA_UPLOAD_MAX_NUMBER_FIELDS = None

# TEST_RUNNER = 'djtools.new_tests.runner.MyBehaveTestRunner'
TEST_INITIAL_DATA = ['djtools.new_tests.test_initial_data.start_database', 'djtools.new_tests.test_initial_data.initial_data']
TEST_COMMON_STEPS = [join(BASE_DIR, 'djtools/new_tests/common_steps')]

BEHAVE_BROWSER = 'chrome'
BEHAVE_CHROME_HEADLESS = True
BEHAVE_CHROME_WEBDRIVER = ''
BEHAVE_WINDOW_SIZE = '1980,2160'
# BEHAVE_WINDOW_SIZE = '1980,1080'
BEHAVE_WINDOW_POSITION = ''

BEHAVE_AUTO_DOC = False
BEHAVE_AUTO_DOC_PATH = join(MEDIA_ROOT, 'documentacao')
BEHAVE_AUTO_MOCK = False
BEHAVE_AUTO_MOCK_PATH = ''

USA_LEITOR_BIOMETRICO_GRIAULE = True

PIPELINE = {
    'JS_COMPRESSOR': 'pipeline.compressors.jsmin.JSMinCompressor',
    'COMPILERS': ('libsasscompiler.LibSassCompiler',),
    'CSS_COMPRESSOR': 'pipeline.compressors.NoopCompressor',
    'JAVASCRIPT': {
        'jquery': {'source_filenames': ('comum/js/jquery.min.js',), 'output_filename': 'js/jquery.min.js'},
        'jquery.ui.custom': {'source_filenames': ('comum/js/jquery.ui.custom.min.js',), 'output_filename': 'js/jquery.ui.custom.min.js'},
        'nouislider': {'source_filenames': ('comum/js/nouislider.min.js',), 'output_filename': 'js/nouislider.min.js'},
        'main': {'source_filenames': ('comum/js/main.js',), 'output_filename': 'js/main.js'},
        'highlight': {'source_filenames': ('comum/js/highlight.js',), 'output_filename': 'js/highlight.js'},
        'login': {'source_filenames': ('comum/js/login.js',), 'output_filename': 'js/login.js'},
        'index': {'source_filenames': ('djtools/graficos/highcharts.js', 'djtools/graficos/exporting.js', 'comum/js/index.js'), 'output_filename': 'js/index.js'},
        'jstree': {'source_filenames': ('djtools/jstree/jstree.min.js',), 'output_filename': 'js/jstree.min.js'},
        'highcharts': {'source_filenames': ('djtools/graficos/highcharts.js',), 'output_filename': 'js/highcharts.js'},
        'exporting': {'source_filenames': ('djtools/graficos/exporting.js',), 'output_filename': 'js/exporting.js'},
        'actions': {'source_filenames': ('djtools/js/actions.js', ), 'output_filename': 'js/actions.js'},
        'select2': {
            'source_filenames': ('djtools/select2/js/select2.min.js', 'djtools/select2/js/i18n/pt-BR.js', 'djtools/select2/js/select2.custom.js'),
            'output_filename': 'js/select2.js',
        },
        'fancybox': {'source_filenames': ('djtools/fancybox/fancybox-core.js', 'djtools/fancybox/custom.js'), 'output_filename': 'js/fancybox.js'},
        'tabs': {'source_filenames': ('djtools/js/tabs.js',), 'output_filename': 'js/tabs.js'},
        'widgets': {'source_filenames': ('djtools/jquery/jquery.maskedinput.js', 'djtools/jquery/widgets-core.js'), 'output_filename': 'js/widgets.js'}
    },
    'STYLESHEETS': {
        'select2': {'source_filenames': ('djtools/select2/css/select2.min.css',), 'output_filename': 'css/select2.min.css'},
        'default': {'source_filenames': ('djtools/themes/default/main.scss',), 'output_filename': 'css/main_default.css'},
        'dunas': {'source_filenames': ('djtools/themes/dunas/main.scss',), 'output_filename': 'css/main_dunas.css'},
        'aurora': {'source_filenames': ('djtools/themes/aurora/main.scss',), 'output_filename': 'css/main_aurora.css'},
        'luna': {'source_filenames': ('djtools/themes/luna/main.scss',), 'output_filename': 'css/main_luna.css'},
        'govbr': {'source_filenames': ('djtools/themes/govbr/main.scss',), 'output_filename': 'css/main_govbr.css'},
        'alto_contraste': {'source_filenames': ('djtools/themes/alto_contraste/main.scss',), 'output_filename': 'css/main_alto_contraste.css'},
        'ifs': {'source_filenames': ('djtools/themes/ifs/main.scss',), 'output_filename': 'css/main_ifs.css'},
        'anonima': {'source_filenames': ('djtools/css/anonima.css',), 'output_filename': 'css/anonima.css'},
        'magnific-popup': {'source_filenames': ('djtools/magnific-popup/magnific-popup.css',), 'output_filename': 'css/magnific-popup.css'},
    },
}


# - - - - - - - - - - - - - - -
# Catálogo Provedor de Serviço
# - - - - - - - - - - - - - - -
# Esse método é necessário enquanto o ambiente GOV BR de treinamento possuir códigos de serviços diferentes dos serviços
# de produção para uma mesma instituição. No caso, em ambiente de desenvolvimento, lembrar de sobreescrever este método
# e fazer o devido "de para" dos IDs.
def get_id_servico_portal_govbr(id_servico_portal_govbr):
    '''
    Este método foi criado para manter compatibilidade de código e simular o que faz o método
    params_govbr_treinamento.get_id_servico_portal_govbr. Para mais detalhes, consultar o referido método.

    :param id_servico_portal_govbr Id do GOV BR de produção
    :return: id_servico_portal_govbr Id do GOV BR de produção
    '''
    return id_servico_portal_govbr


ADMIN_QUICK_ACCESS = [
    'documents', 'webmail', 'groups', 'microsoft_azure', 'google_classroom', 'phones', 'scdp_siape', 'mobile'
]

SERVICE_PROVIDER_FACTORY = 'catalogo_provedor_servico.providers.impl.ifrn.factory.IfrnServiceProviderFactory'

MOODLE_URL_API = os.environ.get('MOODLE_URL_API', '')
MOODLE_SYNC_TOKEN = ''

TRUSTED_CERTS_DIRECTORY = join(BASE_DIR, 'certs')

# https://docs.djangoproject.com/en/dev/ref/settings/#use-tz
USE_TZ = False

# http://docs.celeryproject.org/en/latest/userguide/configuration.html#beat-scheduler
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

GITLAB_URL = 'https://gitlab.ifrn.edu.br'
GITLAB_API_TOKEN = ''
GITLAB_PROJECT_ID = 8
GITLAB_API_VERSION = 4
GITLAB_CI_DOMAIN = 'suapdevs.ifrn.edu.br'
GITLAB_CI_DB_TEMPLATES = 'suap', 'behave'

NOTA_DECIMAL = False
CASA_DECIMAL = 0  # valores aceitos: 1 ou 2
PERIODO_LETIVO_CHOICES = [[1, '1'], [2, '2']]
IMPEDIR_CHOQUE_HORARIOS_PROFESSOR = False
PERCENTUAL_CH_PREPARACAO_AULAS_PIT = 100
PERMITE_ALTERACAO_CH_PREPARACAO_AULAS_PIT = True

# GOV BR OAUTH2 PROVIDER
SOCIAL_AUTH_GOVBR_KEY = os.environ.get('SOCIAL_AUTH_GOVBR_KEY', 'client_id')
SOCIAL_AUTH_GOVBR_SECRET = os.environ.get('SOCIAL_AUTH_GOVBR_SECRET', 'client_secret_govbr')
SOCIAL_AUTH_GOVBR_SCOPE = ['openid', 'profile', 'phone', 'email', 'govbr_confiabilidades']
SOCIAL_AUTH_GOVBR_EXTRA_DATA = ['name', 'phone_number', 'username', 'email']
SOCIAL_AUTH_REDIRECT_IS_HTTPS = os.environ.get('SOCIAL_AUTH_REDIRECT_IS_HTTPS')
SOCIAL_AUTH_LOGIN_ERROR_URL = '/accounts/login/'
SOCIAL_AUTH_PIPELINE = (
    'social_core.pipeline.social_auth.social_details',
    'social_core.pipeline.social_auth.social_uid',
    'social_core.pipeline.social_auth.auth_allowed',
    'social_core.pipeline.social_auth.social_user',
    'auth_backends.govbr_backend.pipeline.get_username',
    'auth_backends.govbr_backend.pipeline.get_confiabilidades',
    'auth_backends.govbr_backend.pipeline.get_vinculos_ativos_ids',
    'auth_backends.govbr_backend.pipeline.atualiza_dados_cidadao',
    'auth_backends.govbr_backend.pipeline.create_user',
    # 'social_core.pipeline.user.create_user',
    'social_core.pipeline.social_auth.associate_user',
    'social_core.pipeline.social_auth.load_extra_data',
    'social_core.pipeline.user.user_details',
)


# cliente_govbr settings
AUTHORIZATION_URL = os.environ.get('AUTHORIZATION_URL', 'https://sso.acesso.gov.br/authorize')
ACCESS_TOKEN_URL = os.environ.get('ACCESS_TOKEN_URL', 'https://sso.acesso.gov.br/token')
USER_DATA_URL = os.environ.get('USER_DATA_URL', 'https://sso.acesso.gov.br/userinfo')

# urls govbr
LOGOUT_URL_GOV_BR = os.environ.get('LOGOUT_URL_GOV_BR')
ALTERAR_PERFIL_URL_GOV_BR = os.environ.get('ALTERAR_PERFIL_URL_GOV_BR')
ALTERAR_SENHA_URL_GOV_BR = os.environ.get('ALTERAR_SENHA_URL_GOV_BR')


MIDDLEWARE += (
    'auth_backends.govbr_backend.middleware.CustomSocialAuthExceptionMiddleware',
)


AUTHENTICATION_BACKENDS += (
    'auth_backends.govbr_backend.backends.GovbrOAuth2',
)
