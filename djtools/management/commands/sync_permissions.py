"""
``APP/permissions.yaml`` template:

suap_operador
   comum:
      sala:
       - can_add_sala
       - can_change_sala
       - can_delete_sala
"""
from fnmatch import fnmatch
from os.path import isfile

from django.apps import apps as loader
from django.conf import settings
from django.contrib.auth.models import Group
from django.utils import termcolors

from comum.models import GerenciamentoGrupo, GroupDetail
from djtools.management.commands import BaseCommandPlus
from djtools.management.permission import GroupPermission
from djtools.utils import sync_groups_and_permissions
from djtools.utils import walk


class Command(BaseCommandPlus):

    grupos_no_permisions_yaml = []

    def add_arguments(self, parser):
        parser.add_argument('apps', nargs='*', type=str)
        parser.add_argument(
            '--check',
            action='store_true',
            help='Realiza uma verificação se os arquivos das permissões estão corretas.',
        )
        parser.add_argument(
            '--raise-exception',
            action='store_true',
            help='Realiza uma verificação se os arquivos das permissões estão corretas.',
        )

    def handle(self, *args, **options):
        apps = options['apps'] if options['apps'] else []
        raise_exception = options.get('raise_exception')
        check = options.get('check')
        failed_msg = ''

        group_permission = GroupPermission()
        grupos = []
        permissoes = []
        module_permissions = []
        apps_has_menu_json = set()
        for path, subdir, files in walk("."):
            for name in files:
                if fnmatch(name, 'menu.yaml'):
                    apps_has_menu_json.add(path.replace('./', ''))

        installed_apps = set(settings.INSTALLED_APPS)
        apps_instaladas_com_menu = installed_apps.intersection(apps_has_menu_json)
        apps_extra = apps_instaladas_com_menu.difference(settings.INSTALLED_APPS_SUAP)
        if apps_extra:
            failed_msg = f'[warning] As apps: {", ".join(apps_extra)}. Não estão definidos no INSTALLED_APPS_SUAP. ' \
                         f'Isso pode fazer com que esse(s) módulo(s) não tenham seus menus ' \
                         f'processados ou que seus grupos não apareçam no gerenciamento de grupos. ' \
                         f'Por favor veja o arquivo "settings_sample.py" para definir apps no SUAP'
            self.stdout.write(termcolors.make_style(fg='yellow')(failed_msg))

        for app in settings.INSTALLED_APPS_SUAP:
            # recupera todas as permissões dos arquivos de permissions do app
            grupo = self.processar_group_permission(app, apps, options, group_permission)
            if grupo:
                grupos.append(grupo)
            # recupera todas as permissões dos modelos do app
            try:
                for model in list(loader.get_app_config(app).get_models()):
                    for permissao in model._meta.permissions:
                        if not permissao in module_permissions:
                            module_permissions.append(f'{app}.{model.__name__.lower()}.{permissao[0]}')
            except Exception:
                pass
        # verfica se tem alguma permissao no yaml mas não no modelo
        permissao_yaml = False
        permissao_modelo = False
        for grupo in grupos:
            for permissao in grupo:
                permissoes.append(permissao)
                perm = permissao.split('.')[1]
                if not self.model_exist(permissao):
                    if not permissao_modelo:
                        failed_msg = '>>> Modelo inexistente no módulo:'
                        self.stderr.write(failed_msg)
                        permissao_yaml = True
                    self.stderr.write(permissao)
                elif '.add_%s' % perm not in permissao and '.view_%s' % perm not in permissao and '.delete_%s' % perm not in permissao and '.change_%s' % perm not in permissao:
                    if permissao not in module_permissions:
                        if not permissao_yaml:
                            failed_msg = '>>> Permissões no yaml inexistentes no modelo:'
                            self.stderr.write(failed_msg)
                            permissao_yaml = True
                        self.stderr.write(permissao)

        # verifica se tem alguma permissao no modelo mas não no yaml
        permissao_modelo = False
        for permissao in module_permissions:
            perm = permissao.split('.')[1]
            if (
                permissao not in permissoes
                and '.add_%s' % perm not in permissao
                and '.view_%s' % perm not in permissao
                and '.delete_%s' % perm not in permissao
                and '.change_%s' % perm not in permissao
            ):
                if not permissao_modelo:
                    failed_msg = '>>> Permissões no modelo inexistentes no yaml:'
                    self.stderr.write(failed_msg)
                    permissao_modelo = True
                self.stderr.write(permissao)
        if not check:
            self.limpar_permissoes_dos_grupos(group_permission)
            sync_groups_and_permissions(*group_permission.obter_dicionario_permissoes_descricoes())
            self.processar_grupo_gerenciador(group_permission)
            if options['verbosity']:
                if Group.objects.exclude(id__in=self.grupos_no_permisions_yaml).exists():
                    self.stdout.write(
                        termcolors.make_style(fg='yellow')(
                            '[warning] grupos não existentes nos permissions.yaml: %s' % list(Group.objects.exclude(id__in=self.grupos_no_permisions_yaml).values_list('id', 'name'))
                        )
                    )
                self.stdout.write(termcolors.make_style(fg='green')('[sync_permissions] finished'))
        if failed_msg and raise_exception:
            raise Exception(failed_msg)

    def processar_group_permission(self, app, apps, options, groupPermission):
        permissoes = []
        if len(apps) == 0 or app in apps:
            permissionFileName = f'{app}/permissions.yaml'

            if settings.LPS:
                permissionFileName_lps = f'{app}/lps/{settings.LPS}/permissions.yaml'
                if isfile(permissionFileName_lps):
                    permissionFileName = permissionFileName_lps

            if isfile(permissionFileName) and (len(apps) == 0 or app in apps):
                permissoes = groupPermission.processar_yaml(permissionFileName, app)
        return permissoes

    def model_exist(self, permission):
        try:
            permission_app = permission.split('.')[0]
            permission_model = permission.split('.')[1]
            loader.get_model(permission_app, permission_model)
            return True
        except Exception:
            return False

    def processar_grupo_gerenciador(self, groupPermission):
        """
        Criar um grupo gerenciador de nome 'APP GerenciamentoGrupo.NOME_GRUPO_GERENCIADOR_FORMAT' e coloca ele como gerenciador de todos os grupos da APP, inclusive ele;
        Se o grupo gerenciador já existir ele apenas refaz o processo, limpando todos os grupos gerenciados e colocando de novo um a um
        """
        for nome_app, app in list(groupPermission.apps.items()):
            grupo_gerenciador = Group.objects.get_or_create(name=GerenciamentoGrupo.NOME_GRUPO_GERENCIADOR_FORMAT.format(nome_app))[0]
            GroupDetail.objects.update_or_create(group=grupo_gerenciador, app=app.nome,
                                                 defaults={'descricao': f'Grupo responsável por gerenciar os outros grupos e usuários do módulo {nome_app}', 'app_manager': app.nome})
            gerenciamento_grupo = GerenciamentoGrupo.objects.get_or_create(grupo_gerenciador=grupo_gerenciador)[0]
            gerenciamento_grupo.grupos_gerenciados.clear()
            for key, value in list(app.grupos.items()):
                grupo = Group.objects.get(name=key)
                if value.can_manager and value.app_manager == nome_app:
                    gerenciamento_grupo.grupos_gerenciados.add(grupo)
                self.grupos_no_permisions_yaml.append(grupo.id)

            gerenciamento_grupo.grupos_gerenciados.add(grupo_gerenciador)
            self.grupos_no_permisions_yaml.append(grupo_gerenciador.id)

    def limpar_permissoes_dos_grupos(self, group_permission):
        """
        Remove todas as permissões dos grupos para que após o processamento eles só tenham as permissões definidas nos permissions.yaml
        """
        for grupo in group_permission.obter_grupos():
            nome_grupo = grupo.nome
            grupo = Group.objects.filter(name=nome_grupo).first()
            if grupo:
                grupo.permissions.clear()
