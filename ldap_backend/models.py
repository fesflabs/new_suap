import itertools

import ldap
import ldap.modlist as modlist
import ldapdb
import ldapdb.models.fields as ldapFields
from datetime import datetime, timedelta
#
from django.conf import settings
from djtools.db import models
from djtools.utils import send_mail
#
from comum.utils import get_uo, get_todos_setores
from rh.models import Setor, PessoaFisica
#
from .adpasswd import ADInterface
from .utils import get_obj_attrs, datetime_to_ad, get_senha_inicial, get_setor_dn, format_name
from .manager import LdapUserManager

USER_ACCOUNT_CONTROL_ACTIVE = '512'
USER_ACCOUNT_CONTROL_INACTIVE = '514'


def props(obj):
    return {key: value for key, value in obj.__dict__.items()
            if not callable(value) and not key.startswith('_')}


class LdapConf(models.ModelPlus):
    SOLUCAO_ACTIVE_DIRECTORY = 'active_directory'
    SOLUCAO_OPEN_LDAP = 'open_ldap'
    SOLUCAO_CHOICES = ((SOLUCAO_ACTIVE_DIRECTORY, 'Active Directory'), (SOLUCAO_OPEN_LDAP, 'OpenLDAP'))

    solucao = models.CharField('Solução de autenticação', max_length=20, choices=SOLUCAO_CHOICES)
    uri = models.CharFieldPlus('URI', help_text='Ex.: "ldap://ldap.ifrn.local:389".', unique=True)
    who = models.CharFieldPlus('Usuário (DN)', help_text='Ex.: "cn=admin,dc=ifrn,dc=edu,dc=br".', width=600)
    cred = models.CharFieldPlus('Senha', null=True, blank=True)
    base = models.CharFieldPlus('Base DN', help_text='Ex.: "OU=IFRN,DC=ifrn,DC=local".', width=600)
    filterstr_prefix = models.CharFieldPlus('Filtro de autenticação', default='sAMAccountName=', help_text='Ex.: "sAMAccountName=", "uid=".')
    domain = models.CharFieldPlus('Domínio', help_text='Ex.: "ifrn.local".')
    email_admin = models.EmailField(default='digti@ifrn.edu.br', help_text='Email da coordenação de TI')
    priority = models.IntegerField('Prioridade', default=1000)
    active = models.BooleanField('Serviço ativo', default=True)
    resolve_referral = models.BooleanField('LDAP should resolve referrals', default=True)

    class Meta:
        permissions = (
            ('change_ldap_user_password_subtree', 'Pode modificar a senha de usuários da sub-árvore'),
            ('change_ldap_user_password_all', 'Pode modificar a senha de todos os usuários'),
            ('change_ldap_user_password_aluno', 'Pode modificar a senha de alunos'),
            ('sync_ldap_user', 'Pode sincronizar usuários'),
            ('view_ldap_user', 'Pode ver usuários'),
            ('pode_acessar_google_classroom', 'Pode acessar o Google Classrooom'),
        )
        verbose_name = 'Configuração do Serviço de Diretório'
        verbose_name_plural = 'Configurações dos Serviços de Diretório'

    def __str__(self):
        return self.uri

    @property
    def filterstr(self):
        return [x.replace("=", "") for x in self.filterstr_prefix.split(',')]

    @classmethod
    def peek(cls):
        try:
            return cls.objects.filter(active=True).order_by('priority').first()
        except cls.DoesNotExist:
            return None

    @classmethod
    def get_active_settings(cls):
        obj = cls.peek()
        return props(obj if obj else LdapConf())

    @classmethod
    def get_active(cls):
        try:
            for obj in cls.objects.filter(active=True).order_by('priority'):
                if obj.has_connectivity():
                    return obj
        except cls.DoesNotExist:
            return None

    def has_connectivity(self):
        try:
            self.bind()
            return True
        except ldap.SERVER_DOWN:
            return False

    def can_change_user_password(self, user, ldap_username):
        return False
        if (
            not user.has_perm('ldap_backend.change_ldap_user_password_subtree')
            and not user.has_perm('ldap_backend.change_ldap_user_password_all')
            and not user.has_perm('ldap_backend.change_ldap_user_password_aluno')
        ):
            return False

        try:
            pessoa_fisica = PessoaFisica.objects.get(username=ldap_username)
        except PessoaFisica.DoesNotExist:
            return False

        if not pessoa_fisica.get_usuario_ldap(attrs=['dn']):
            return False

        """
            Pode alterar a senha caso:
                - Tenha permissao de alterar senha de todos(inclui superusuário);
                - Tenha permissao de alterar senha subtree, o usuário seja do mesmo campus;
                - Tenha permissao de alterar senha de aluno, e o usuário seja aluno do mesmo campus;

            Superusuário e quem tem permissão user_password_all podem fazer tudo
        """
        if user.has_perm('ldap_backend.change_ldap_user_password_all'):
            return True

        sub_instance = pessoa_fisica.sub_instance()
        if pessoa_fisica.eh_servidor:
            if sub_instance.eh_aposentado and user.has_perm('ldap_backend.change_ldap_user_password_subtree'):
                return True
            if sub_instance.campus == get_uo(user) and user.has_perm('ldap_backend.change_ldap_user_password_subtree'):
                return True

        elif pessoa_fisica.eh_aluno:
            if user.has_perm('ldap_backend.change_ldap_user_password_subtree'):
                return True
            elif (
                user.has_perm('ldap_backend.change_ldap_user_password_aluno')
                and pessoa_fisica.eh_aluno
                and pessoa_fisica.sub_instance().curso_campus.diretoria.setor in get_todos_setores(user)
            ):
                return True
        elif pessoa_fisica.eh_prestador and user.has_perm('ldap_backend.change_ldap_user_password_subtree'):
            return True

        return False

    def bind(self, who=None, password=None, unbind=False):
        if who is None and password is None:
            who, password = self.who, self.cred
        try:
            ldap_obj = ldap.initialize(self.uri, bytes_mode=False)
            if not self.resolve_referral:
                ldap_obj.set_option(ldap.OPT_REFERRALS, 0)
        except ldap.LDAPError:
            raise ValueError('A URI %s esta inválida' % self.uri)
        try:
            ldap_obj.simple_bind_s(who, password)
        except ldap.INVALID_CREDENTIALS:
            raise ValueError('Credenciais invalidas para %s' % who)
        if unbind:
            ldap_obj.unbind_s()
        return ldap_obj

    def check_password(self, username, password):
        try:
            if self.solucao == self.SOLUCAO_ACTIVE_DIRECTORY:
                who = username + '@' + self.domain
            else:
                who = self.filterstr_prefix + username + ',' + self.base
            self.bind(who, password, unbind=True)
            return True
        except Exception:
            return False

    @property
    def default_search_fields(self):
        default_search_fields = ['!uid', 'sAMAccountName', 'givenName', 'sn', 'mail']
        for filter in self.filterstr:
            if filter not in default_search_fields:
                default_search_fields.append(filter)
        return default_search_fields

    def mount_filter_by_query(self, q, search_fields=None):
        search_fields = search_fields or self.default_search_fields
        filterstr = '(|'
        for f in search_fields:
            filterstr += '({}=*{}*)'.format(f, q)
        filterstr += ')'

        return filterstr

    def mount_filterstr(self, username):
        default_search_fields = ['sAMAccountName'] + self.filterstr
        filterstr = '(|'
        for f in default_search_fields:
            filterstr += '({}={})'.format(f, username)
        filterstr += ')'
        return filterstr

    def get_usernames_from_principalname(self, principal_name):
        return list(itertools.chain(*[[cn.decode() for cn in row['cn']] for row in self.search_objects(filterstr=f'(userPrincipalName={principal_name})')]))

    def get_usernames_from_mail(self, principal_name):
        return list(itertools.chain(*[[cn.decode() for cn in row['cn']] for row in self.search_objects(filterstr=f'(mail={principal_name})')]))

    def get_user(self, username, attrs=None, base=None):
        """recupera dados do usuário ``username``"""
        base = base or self.base
        ldap_obj = self.bind()
        filterstr = self.mount_filterstr(username)
        try:
            result = ldap_obj.search_ext_s(
                base=base, scope=ldap.SCOPE_SUBTREE, filterstr=filterstr, attrlist=attrs, attrsonly=0, serverctrls=None, clientctrls=None, timeout=-1, sizelimit=0
            )
        except ldap.OPERATIONS_ERROR:
            return dict()
        if result:
            dn, attrs = result[0]
            if type(attrs) == list:
                return dict()
            attrs['dn'] = dn
            return attrs
        else:
            return dict()

    def search_objects(self, q=None, filterstr=None, attrlist=None, base=None, search_fields=None, use_paged_results=True):
        """
        Busca objetos genéricos. Usado para buscar usuários e OUs
        """
        base = base or self.base
        filterstr = filterstr or self.mount_filter_by_query(q, search_fields)

        ldap_obj = self.bind()
        if not use_paged_results:
            result = ldap_obj.search_ext_s(
                base=base, filterstr=filterstr, attrlist=attrlist, scope=ldap.SCOPE_SUBTREE, attrsonly=0, serverctrls=None, clientctrls=None, timeout=-1, sizelimit=0
            )
        else:
            msgid = ldap_obj.search_ext(base=base, filterstr=filterstr, attrlist=attrlist, scope=ldap.SCOPE_SUBTREE)
            rtype, result, rmsgid, serverctrls = ldap_obj.result3(msgid)
        results = []
        for r in result:
            dn, attrs = r
            if dn:
                attrs['dn'] = dn
                results.append(attrs)
        return results

    def modify(self, dn_or_username, attrs, mod_list=None):
        """
        Faz a operação modify.

        attrs: {'field1': 'value1', 'field2': 'value2'}
        mod_list: {'field1', 'add', 'field2': 'delete'}, o default é o 'replace'.
        """
        MODS = dict(add=ldap.MOD_ADD, replace=ldap.MOD_REPLACE, delete=ldap.MOD_DELETE)
        # Se dn_or_username tiver os caracteres ',' e '=', assume-se que é o dn
        if ',' in dn_or_username and '=' in dn_or_username:
            dn = dn_or_username
        else:  # assume-se que foi passado um username
            dn = self.get_user(dn_or_username, attrs=['dn']).get('dn')
            if not dn:
                return 0

        mod_list = mod_list or dict()
        mod_attrs = []
        for key, value in list(attrs.items()):
            if value == '':
                raise ValueError('Error on modify "{}": "{}" is empty string (should be None?)'.format(dn, key))
            if isinstance(value, list):
                value = [val.encode('utf-8') for val in value]
            if isinstance(value, str):
                value = [value.encode('utf-8')]
            mod = MODS[mod_list.get(key, 'replace')]
            mod_attrs.append((mod, key, value))
        self.bind().modify_s(dn, mod_attrs)
        return 1

    def move_object(self, dn, newdn, newrdn=None):
        newrdn = newrdn or newdn.split(',')[0]
        newsuperior = ','.join(newdn.split(',')[1:])
        ldap_obj = self.bind()
        ldap_obj.rename_s(dn=dn, newsuperior=newsuperior, newrdn=newrdn)

    def sync_all_ous(self, test_mode=True):
        """Sincroniza todos os setores do SUAP no LDAP.
        Nota: como a criação é recursiva, ao criar os setores folhas, a árvore
              inteira será criada.
        """
        for s in Setor.get_folhas():
            self.sync_ou(s, test_mode=test_mode)

    def sync_ou(self, setor, test_mode=True):
        """
        Mapeamento SUAP X LDAP:
            Setor.id -> OU.adminDescription
            Setor.nome -> OU.description
        """

        def print_(msg, test_mode):
            prefix = test_mode and '[TEST] ' or '> '
            print(prefix + msg)

        if setor.superior:
            ou_superior = self.get_ou_by_admin_description(setor.superior.pk)
            if not ou_superior or ou_superior[0]['ou'][0].decode() != format_name(setor.superior.sigla).replace(' ', ''):
                self.sync_ou(setor.superior, test_mode=test_mode)

        newdn = get_setor_dn(setor, self.domain)
        attrs = {'objectclass': [b'top', b'organizationalUnit'], 'adminDescription': [str(setor.id).encode()], 'description': [setor.nome.encode()]}

        ldap_ou = self.get_ou_by_admin_description(setor.pk)
        if ldap_ou:  # Atualizar OU existente no LDAP
            dn = ldap_ou[0]['dn']
            if ldap_ou[0]['description'][0].decode() != setor.nome:
                if not test_mode:
                    self.modify(dn, dict(description=setor.nome))
            if dn != newdn:
                print_('Movendo OU de "{}" para "{}"'.format(dn, newdn), test_mode)
                if not test_mode:
                    try:
                        self.move_object(dn=dn, newdn=newdn)
                    except ldap.OTHER as e:
                        if setor.superior:
                            self.sync_ou(setor.superior, test_mode=test_mode)
                        else:
                            raise e

        else:  # Criar OU no LDAP
            ldif = modlist.addModlist(attrs)
            print_('Criando OU "{}"'.format(newdn), test_mode)
            if not test_mode:
                try:
                    self.bind().add_ext_s(newdn, ldif)
                except ldap.ALREADY_EXISTS:
                    print_('OU "{}" já existe então atualize.'.format(newdn), test_mode)
                    self.modify(newdn, dict(description=setor.nome, adminDescription=setor.id))

    def sync_user(self, obj):
        """
        Cria ou atualiza o `obj` no LDAP.

        obj: instância de Servidor, Aluno ou Prestador; também pode ser uma
            string representando o username (evitar essa opção, que é mais lenta)
        """
        ATTRS_TO_GET = ['dn', 'sAMAccountName', 'userAccountControl', 'memberOf', 'mail', 'accountExpires', 'pwdLastSet', 'lastLogon']

        if isinstance(obj, str):
            try:
                obj = PessoaFisica.objects.get(username=obj).sub_instance()
            except PessoaFisica.DoesNotExist:
                raise Exception('Nenhuma pessoa física com username {}'.format(obj))

        ATTRS_TO_GET.extend(self.filterstr)
        ATTRS_TO_GET = list(set(ATTRS_TO_GET))
        ldap_user = self.get_user(obj.username, attrs=ATTRS_TO_GET)
        #####################################################################################
        # Se no LDAP o user tem `mail`, deixar o valor do `mail` em Servidor.email_institucional`
        # e `Aluno.email_academico`.
        # if ldap_user and ldap_user['sAMAccountName'][0]:
        # Testando se todas as chaves listadas no filtro de autenticação estão presentes.
        #####################################################################################

        if obj.__class__.__name__.lower() == 'servidor' and ldap_user and all(k in ldap_user for k in self.filterstr):
            ldap_mail = ldap_user.get('mail', [b''])[0].decode()
            if ldap_mail:
                obj.__class__.objects.filter(id=obj.id).update(email_institucional=ldap_mail)
                obj.email_institucional = ldap_mail

        obj_attrs = get_obj_attrs(model_obj=obj, ldap_conf=self)
        if not obj_attrs:
            print('>>> Impossível gerar DN para objeto:{}'.format(obj))
            return

        new_dn = obj_attrs.pop('dn')
        member_of = obj_attrs.pop('memberOf', [])
        thumbnail_photo = obj_attrs.pop('thumbnailPhoto')
        senha = get_senha_inicial(obj)

        if obj_attrs.pop('active'):  # o usuário deve ser ativo no LDAP?

            if ldap_user:  # Usuário existe, vamos atualizá-lo

                # Caso futuramente se queira sincronizar o `objectClass` nas
                # edições, cada item deve ser tratado individualmente para apenas
                # adicionar o que é necessário, pois o ldap.MOD_REPLACE pode causar
                # inconsistências com outros sistemas (ex: Microsoft Lync)
                obj_attrs.pop('cn', None)  # `cn` não é atualizável

                # `userPrincipalName` aka UPN não é atualizável (erro CONSTRAINT_ATT_TYPE)
                obj_attrs.pop('userPrincipalName', None)

                if ldap_user['dn'] != new_dn:  # Usuário deve ser movido?
                    self.move_object(ldap_user['dn'], new_dn)

                if ldap_user['userAccountControl'][0].decode() != USER_ACCOUNT_CONTROL_ACTIVE:  # Usuário deve ser ativado?
                    self.change_password(new_dn, senha, force=True)
                    self.activate_user(obj.username)

                # Usuário nunca logou nem definiu a senha?
                if ldap_user.get('pwdLastSet', [b'0'])[0].decode() == '0' and ldap_user.get('lastLogon', [b'0'])[0].decode() == '0':
                    self.change_password(new_dn, senha, force=True)

                # sincroniza os atributos e já ativa também
                self.modify(obj.username, obj_attrs)

            else:  # Usuário não existe, vamos criá-lo
                obj_attrs.pop('mail', None)  # `mail` de um novo usuário é sempre None (e dá erro no addModlist)
                # Não se pode criar objeto com algum atributo sendo `None`
                for k, v in list(obj_attrs.items()):
                    if not v:
                        del obj_attrs[k]
                obj_attrs['userAccountControl'] = USER_ACCOUNT_CONTROL_INACTIVE
                try:
                    dict_bin = {}
                    for key, value in list(obj_attrs.items()):
                        if isinstance(value, str):
                            dict_bin[key] = value.encode('utf8')
                        if isinstance(value, list):
                            list_bin = []
                            for item in value:
                                list_bin.append(item.encode('utf8'))
                            dict_bin[key] = list_bin

                    modattrs = modlist.addModlist(dict_bin)
                    self.bind().add_s(new_dn, modattrs)
                except ldap.NO_SUCH_OBJECT:
                    raise ValueError('OU inexistente no LDAP: {}'.format(new_dn.split(',', 1)[1]))
                self.change_password(new_dn, senha, force=True)
                self.activate_user(obj.username)

            # tratando o ``memberOf`` do usuário
            groups_to_add = list(set(member_of) - set(ldap_user.get('memberOf', [])))
            for group_dn in groups_to_add:
                try:
                    self.modify(group_dn, {'member': new_dn}, mod_list={'member': 'add'})
                except ldap.ALREADY_EXISTS:
                    pass
                except ldap.NO_SUCH_OBJECT:
                    raise ValueError('Grupo inexistente no LDAP: {}'.format(group_dn))

            # tratando o ``thumbnailPhoto`` do usuário; estranhamente a escrita
            # do atributo só funciona ser atualizado isoladamente.
            if thumbnail_photo:
                self.modify(obj.username, dict(thumbnailPhoto=thumbnail_photo))

        else:  # o usuário deve ser inativo no LDAP
            if not ldap_user:
                return
            obj_attrs.pop('objectClass')
            obj_attrs.pop('cn', None)
            obj_attrs.pop('accountExpires')
            daqui_a_15_dias = datetime_to_ad(datetime.now() + timedelta(15))
            if ldap_user['userAccountControl'][0].decode() != USER_ACCOUNT_CONTROL_INACTIVE and int(ldap_user['accountExpires'][0].decode()) > daqui_a_15_dias:
                print('>>> Usuario será inativado em 15 dias:{}'.format(obj))
                obj_attrs['accountExpires'] = str(daqui_a_15_dias)
                if obj.pessoa_fisica.email and not settings.DEBUG:
                    titulo = '[SUAP] Sua conta será expirada em 15 dias'
                    mensagem = '''
                    <h1>Expiração de Conta</h1>
                    <p>Prezado(a) {},</p>
                    <p>A sua conta de {} com login {}, de acesso aos computadores, sistemas e webmail
                    do IFRN, irá expirar em 15 (quinze) dias, pois nosso sistema detectou o desligamento desse vínculo junto à Instituição.</p>
                    <p>Caso você ainda possua ESTE VÍNCULO ATIVO, por favor entrar em contato com a
                    TI de seu campus.</p>'''.format(
                        obj.pessoa_fisica.nome, obj._meta.verbose_name, obj.pessoa_fisica.username
                    )
                    send_mail(titulo, mensagem, self.email_admin, [obj.pessoa_fisica.email])
            self.modify(obj.username, obj_attrs)

    def limpar_emails_academico_e_google(self, obj):
        """
        Inativa o `obj` no LDAP.

        obj: instância de Aluno; também pode ser uma
            string representando o username (evitar essa opção, que é mais lenta)
        """
        ATTRS_TO_GET = ['dn', 'sAMAccountName', 'userAccountControl', 'memberOf', 'mail', 'accountExpires', 'pwdLastSet', 'lastLogon']

        if isinstance(obj, str):
            try:
                obj = PessoaFisica.objects.get(username=obj).sub_instance()
            except PessoaFisica.DoesNotExist:
                raise Exception('Nenhuma pessoa física com username {}'.format(obj))

        ATTRS_TO_GET.extend(self.filterstr)
        ATTRS_TO_GET = list(set(ATTRS_TO_GET))
        ldap_user = self.get_user(obj.username, attrs=ATTRS_TO_GET)
        obj_attrs = {}
        # Retirei a inativação do AD
        # obj_attrs['userAccountControl'] = '514'
        # Email Academico
        obj_attrs['extensionAttribute4'] = None
        # Email Classroom
        obj_attrs['extensionAttribute5'] = None
        if not ldap_user:
            raise ldap.LDAPError()
        self.modify(obj.username, obj_attrs)
        return True

    def change_password(self, dn_or_username, password, force=False):
        """
        Se `force` for True, caso o `password` seja inválido, será gerada uma
        senha aleatória.
        Se `async` for False, não vai esperar a resposta do servidor LDAP.
        """
        if ',' in dn_or_username:
            dn = dn_or_username
        else:
            dn = self.get_user(dn_or_username, attrs=['dn'])['dn']
        port = '636'
        host = str(self.uri.split('//')[1].split(':')[0])  # ldap://name:389 -> name
        try:
            conf = ADInterface(host=host, port=port, binddn=str(self.who), bindpw=str(self.cred), searchdn=str(self.base))
            conf.changepass_by_dn(dn, password)
            return True
        except Exception:
            return False

    def activate_user(self, username):
        self.modify(username, {'userAccountControl': USER_ACCOUNT_CONTROL_ACTIVE})

    def get_ou_by_admin_description(self, description, base=None):
        """``description`` é `setor.pk`"""
        try:
            query = '(&(objectClass=organizationalUnit)(adminDescription={0}))'
            filterstr = query.format(str(description))
            attrlist = ['dn', 'ou', 'name', 'description', 'adminDescription']
            return self.search_objects(base=base, filterstr=filterstr, attrlist=attrlist)
        except ldap.NO_SUCH_OBJECT:
            return None


class LdapUser(ldapdb.models.Model):
    default_search_fields = ['uid', 'sAMAccountName', 'givenName', 'sn', 'mail']
    base_dn = "OU=IFRN,DC=ifrn,DC=local"
    object_classes = ['person', 'organizationalPerson', 'user']
    rdn_fields = ['uid']
    #
    cn = ldapFields.CharField(db_column='cn', verbose_name="Common Name", help_text='Common Name', blank=False)
    uid = ldapFields.CharField(db_column='uSNCreated', verbose_name="User ID", help_text="uid")
    sAMAccountName = ldapFields.CharField(db_column="sAMAccountName", verbose_name="Account Name", unique=True)
    givenName = ldapFields.CharField(db_column="givenName", verbose_name="First Name", blank=True, null=True)
    sn = ldapFields.CharField(db_column='sn', verbose_name="Surname", help_text='Surname', blank=False)
    mail = ldapFields.CharField(db_column='mail', help_text="E-mail", verbose_name="E-mail", blank=True, null=True)

    cn = ldapFields.CharField(db_column='cn', verbose_name="Common Name", help_text='Common Name', blank=False)
    name = ldapFields.CharField(db_column='displayName', help_text="Display Name", verbose_name="Display Name", blank=True, null=True)
    distinguishedName = ldapFields.CharField(db_column="distinguishedName", verbose_name="Distinguished Name", unique=True)
    #
    member_of = ldapFields.ListField(db_column='memberOf', editable=False, null=True)
    objects = LdapUserManager()

    class Meta:
        verbose_name = 'LDAP User'
        verbose_name_plural = 'LDAP Users'

    def distinguished_name(self):
        return self.distinguishedName

    def membership(self):
        # memberOf fill fields in people entries only if a change/write happens in its definitions
        try:
            membership = LdapGroup.objects.filter(member__contains=self.dn)
            if membership:
                # return os.linesep.join([m.dn for m in membership])
                return [i.cn for i in membership]
        except ldap.FILTER_ERROR:
            return []

    def __str__(self):
        return self.sAMAccountName


class LdapGroup(ldapdb.models.Model):
    """
    Class for representing an LDAP group entry.
    """
    # LDAP meta-data
    base_dn = "OU=IFRN,DC=ifrn,DC=local"
    object_classes = ['top', 'group']
    rdn_fields = ['cn']

    cn = ldapFields.CharField(db_column='cn', max_length=200, unique=True, verbose_name="Common Name")
    name = ldapFields.CharField(db_column='name', help_text="Name", verbose_name="Name", blank=True, null=True)
    sAMAccountName = ldapFields.CharField(db_column="sAMAccountName", verbose_name="Account Name", unique=True)
    member = ldapFields.ListField(db_column='member', verbose_name='Group Members', default=[], editable=True, null=True)

    class Meta:
        verbose_name = 'LDAP Grupo'
        verbose_name_plural = 'LDAP Grupos'

    def __str__(self):
        return self.cn

    def add_member(self, member_obj):
        member_obj_dn = member_obj.dn
        if not member_obj_dn in self.member:
            self.member.append(member_obj.dn)
            self.save()
            return True
        return False

    def remove_member(self, member_obj):
        member_obj_dn = member_obj.dn
        if member_obj_dn in self.member:
            self.member.remove(member_obj_dn)
            self.save()
            return True
        return False

    def is_member(self, member_obj):
        member_obj_dn = member_obj.dn
        return member_obj_dn in self.member

    def remove_all(self):
        self.member = []
        self.save()
