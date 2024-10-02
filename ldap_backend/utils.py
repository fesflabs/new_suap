import random
import re
from datetime import datetime, timedelta

from django.conf import settings
from django.core.files.storage import default_storage

from comum.models import Configuracao
from rh.models import Setor


def ad_to_datetime(t):
    """Converte datetime do AD para datetime python"""
    # ano base + qtd dias do ``t``
    return datetime(1601, 1, 1) + timedelta(float(t) / 864000000000)


def datetime_to_ad(t):
    """Converte datetime python para datetime AD"""
    delta = t - datetime(1601, 1, 1)
    return delta.days * 864000000000 + (delta.seconds * 10000000)


def senha_randomica(tamanho=10):
    """Gerar senha randomica """
    dic = dict(letras_minusculas='abcdefghjkmnpqrstuvwxyz', letras_maiusculas='ABCDEFGHJKLMNPQRSTUVWXYZ', numeros='23456789', caracteres_especiais='!@#$%&*_+')
    randomSource = dic['letras_minusculas'] + dic['letras_maiusculas'] + dic['numeros'] + dic['caracteres_especiais']
    password = random.choice(dic['letras_minusculas'])
    password += random.choice(dic['letras_maiusculas'])
    password += random.choice(dic['numeros'])
    password += random.choice(dic['caracteres_especiais'])

    for i in range(tamanho - 4):
        password += random.choice(randomSource)

    passwordList = list(password)
    random.SystemRandom().shuffle(passwordList)
    password = ''.join(passwordList)
    return password


def format_name(val):
    """Naming conventions in Active Directory for computers, domains, sites, and OUs:
        https://support.microsoft.com/en-us/kb/909264"""
    disallowed_chars = ['\\', '/', ':', '*', '?', '"', '<', '>', '|']
    for c in disallowed_chars:
        val = val.replace(c, '-')
    return val


def get_setor_dn(setor, domain):
    caminho = setor.get_caminho()[:-1]
    caminho.reverse()
    dn = 'OU=%s' % setor.sigla
    for i in caminho:
        dn += ',OU=%s' % i.sigla
    for i in domain.split('.'):
        dn += ',DC=%s' % i
    return format_name(dn).replace(' ', '')


def get_thumbnail_content(pf):
    if pf.foto:

        fname = pf.foto.name.replace('fotos/', 'fotos/75x100/')
        try:
            f = default_storage.open(fname)
            content = f.read()
            f.close()
            return content
        except OSError:
            return None


def get_obj_attrs(model_obj, ldap_conf):
    """
    Retorna os atributos do ``model_obj`` que são importantes para a sincronia com
    o LDAP. O ``model_obj`` deve ser `rh.Servidor` ou `edu.Aluno`.
    """
    func_by_model_name = dict(
        aluno=get_aluno_attrs,
        servidor=get_servidor_attrs,
        prestadorservico=get_prestadorservico_attrs
    )
    model_name = model_obj.__class__.__name__.lower()
    obj_attrs = func_by_model_name[model_name](model_obj, ldap_conf)
    if not obj_attrs:
        return obj_attrs
    obj_attrs['extensionAttribute6'], obj_attrs['extensionAttribute7'] = get_cafe_attrs(model_obj.pessoa_fisica)
    obj_attrs['extensionAttribute8'] = model_obj.pessoa_fisica.email_secundario or None

    # `extensionAttribute9` é utilizado para o Campus ZL/EAD na integração com o Moodle.
    # Se for aluno ou prestador, será o email pessoal/secundário; se for servidor será o institucional.
    if model_name == 'servidor':
        obj_attrs['extensionAttribute9'] = model_obj.email_institucional or None
    else:
        obj_attrs['extensionAttribute9'] = obj_attrs['extensionAttribute8']

    return obj_attrs


def get_senha_inicial(obj):
    """
    Retorna a senha inicial no formato:

        instituicao_sigla.cpf_somente_numeros

    caso objeto tenha CPF. Caso contrário retorna uma string randômica.
    """
    sigla = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
    utilizar_senha_randomica = Configuracao.get_valor_por_chave('ldap_backend', 'utilizar_senha_randomica')
    if utilizar_senha_randomica:
        return senha_randomica(10)
    try:
        if hasattr(obj, "nascimento_data"):
            senha = f'@{sigla.upper()}{obj.nascimento_data.strftime("%d%m%Y")}'
        else:
            senha = f'@{sigla.upper()}{obj.pessoa_fisica.nascimento_data.strftime("%d%m%Y")}'
    except Exception:
        senha = senha_randomica(10)
    return senha


def get_tipos_email_disponiveis(user):
    instance = user.get_relacionamento()

    dominio_institucional = Configuracao.get_valor_por_chave('ldap_backend', 'dominio_institucional')
    dominio_academico = Configuracao.get_valor_por_chave('ldap_backend', 'dominio_academico')
    dominio_google_classroom = Configuracao.get_valor_por_chave('ldap_backend', 'dominio_google_classroom')

    tipos = dict()

    # Servidor
    if user.eh_servidor and not instance.excluido:
        if dominio_institucional and not instance.email_institucional:
            tipos['institucional'] = 'Institucional'
        if not instance.eh_estagiario and dominio_google_classroom and not instance.email_google_classroom:
            tipos['google_classroom'] = 'Google Sala de Aula'
        if dominio_academico and not instance.email_academico and not instance.eh_aposentado:
            tipos['academico'] = 'Acadêmico'

    # Grupo Professor e Prestador de Serviço
    elif user.has_perm('edu.eh_professor') and user.eh_prestador:
        if dominio_google_classroom and not instance.email_google_classroom:
            tipos['google_classroom'] = 'Google Sala de Aula'
    # Aluno
    elif user.eh_aluno and instance.situacao.ativo:
        if dominio_academico and not instance.email_academico:
            tipos['academico'] = 'Acadêmico'
        if dominio_google_classroom and not instance.email_google_classroom:
            tipos['google_classroom'] = 'Google Sala de Aula'

    return tipos


############
# Servidor #
############


def get_funcionario_dn(funcionario, ldap_conf):
    """
    Retorna o DN para o ``funcionario`` com base no seu setor (Pode ser servidor
    e prestador).
    """
    setor = funcionario.setor
    if not setor:
        try:
            setor = funcionario.setor_exercicio.uo.equivalente.setor
        except AttributeError:
            try:
                setor = funcionario.setor_lotacao.uo.equivalente.setor
            except AttributeError:
                setor = Setor.raiz()
    if not funcionario.username:
        return None
    return 'CN={},{}'.format(funcionario.username.strip(), get_setor_dn(setor, ldap_conf.domain))


def get_servidor_grupos(servidor, ldap_conf):
    grupos = []
    if not servidor.eh_estagiario:
        grupos.append(settings.LDAP_GROUP_SERVIDOR)
    if servidor.email_google_classroom:
        grupos.append(settings.LDAP_GROUP_GOOGLE_CLASSROOM)
    return grupos


def get_cafe_attrs(pessoa_fisica):
    cpf = pessoa_fisica.cpf and re.sub(r'\D', '', pessoa_fisica.cpf) or None
    try:
        data_nascimento = pessoa_fisica.nascimento_data.strftime("%Y%m%d")
    except (AttributeError, ValueError):
        data_nascimento = None
    return cpf, data_nascimento


def get_servidor_attrs(servidor, ldap_conf):
    """
    Retorna os atributos para sincronização do usuário no LDAP.
    """
    dn = get_funcionario_dn(servidor, ldap_conf)
    if not dn:
        return dict()

    # Tratando department (sigla do setor de exercício) e extensionAttribute1 (câmpus de exercício)
    department = None
    extensionAttribute1 = None
    if servidor.setor:
        department = servidor.setor.sigla
        if servidor.setor.uo:
            extensionAttribute1 = servidor.setor.uo.setor.sigla

    # Tratando extensionAttribute11 (câmpus de lotação_campus_exercicio)
    extensionAttribute11 = None
    if servidor.setor_lotacao and servidor.setor_lotacao.uo:
        if servidor.setor_lotacao.uo.equivalente:
            extensionAttribute11 = f'{servidor.setor_lotacao.uo.equivalente.sigla}'
        else:
            extensionAttribute11 = f'{servidor.setor_lotacao.uo.sigla}'

    if (servidor.setor and servidor.setor.uo):
        extensionAttribute11 = f'{extensionAttribute11}_{servidor.setor.uo.sigla}' if extensionAttribute11 else servidor.setor.uo.sigla
    elif (servidor.setor_exercicio and servidor.setor_exercicio.uo):
        if servidor.setor_exercicio.uo.equivalente:
            extensionAttribute11 = f'{extensionAttribute11}_{servidor.setor_exercicio.uo.equivalente.sigla}' if extensionAttribute11 else servidor.setor_exercicio.uo.equivalente.sigla
        else:
            extensionAttribute11 = f'{extensionAttribute11}_{servidor.setor_exercicio.uo.sigla}' if extensionAttribute11 else servidor.setor_exercicio.uo.sigla

    funcao = None
    if not servidor.eh_estagiario:
        funcao = servidor.funcao_display or None

    attrs = dict(
        dn=dn,
        userPrincipalName='{}@{}'.format(servidor.username, ldap_conf.domain),
        active=not servidor.excluido,
        objectClass=['top', 'person', 'organizationalPerson', 'user'],
        cn=servidor.username,
        givenName=servidor.nome.split()[0],
        sn=' '.join(servidor.nome.split()[1:])[:64] or None,
        DisplayName=servidor.nome,
        memberOf=get_servidor_grupos(servidor, ldap_conf),
        userAccountControl=(not servidor.excluido) and '512' or '514',
        accountExpires='0',  # Nunca expira
        department=department,
        description=servidor.nome,
        title=servidor.cargo_emprego and servidor.cargo_emprego.nome or None,
        thumbnailPhoto=get_thumbnail_content(servidor),
        mail=servidor.email_institucional or None,
        extensionAttribute1=extensionAttribute1,  # campus
        extensionAttribute2=servidor.categoria_display or None,  # docente, tec-adm, estagiario
        extensionAttribute3=funcao,
        extensionAttribute4=servidor.email_academico or None,
        extensionAttribute5=servidor.email_google_classroom or None,
        extensionAttribute10=(not servidor.excluido) and 'Ativo' or 'Inativo',
        extensionAttribute11=extensionAttribute11,
    )
    # Filtro de autenticação
    for filtro in ldap_conf.filterstr:
        attrs[filtro] = servidor.matricula
    for key, value in list(attrs.items()):
        if key == 'thumbnailPhoto':
            continue
        if isinstance(value, str):
            value = value.strip()
        elif isinstance(value, list):
            value = [i.strip() for i in value]
        attrs[key] = value

    return attrs


#########
# Aluno #
#########


def get_aluno_dn(aluno, ldap_conf):
    """
    Retorna o DN para o ``aluno``.
    """
    try:
        setor = aluno.campus.setor
        username = aluno.username.strip()
    except AttributeError:
        return None
    return 'CN={},OU=Alunos,{}'.format(username, get_setor_dn(setor, ldap_conf.domain))


def get_aluno_grupos(aluno, ldap_conf):
    dn = get_aluno_dn(aluno, ldap_conf)
    dn_sem_cn = ','.join(dn.split(',')[1:])
    campus_identificacao = aluno.campus.setor.sigla.split('/')[-1]
    grupo_dn = 'CN=G_{}_ALUNOS,{}'.format(campus_identificacao, dn_sem_cn)
    return [grupo_dn]


def get_aluno_attrs(aluno, ldap_conf):
    """
    Retorna os atributos para sincronização do usuário no LDAP.
    """
    dn = get_aluno_dn(aluno, ldap_conf)
    if not dn:
        return dict()

    if aluno.email_academico:
        userPrincipalName = aluno.email_academico
    else:
        userPrincipalName = '{}@{}'.format(aluno.username, ldap_conf.domain)

    attrs = dict(
        dn=dn,
        userPrincipalName=userPrincipalName,
        # sAMAccountName       = aluno.username,
        active=aluno.situacao.ativo,
        objectClass=['top', 'person', 'organizationalPerson', 'user'],
        memberOf=get_aluno_grupos(aluno, ldap_conf),
        cn=aluno.username,
        givenName=aluno.pessoa_fisica.nome.split()[0],
        sn=' '.join(aluno.pessoa_fisica.nome.split()[1:])[:64] or None,
        DisplayName=aluno.pessoa_fisica.nome,
        userAccountControl='512',  # 512 ativo, 514 inativo
        accountExpires='0',  # Nunca expira
        description=aluno.pessoa_fisica.nome,
        thumbnailPhoto=None,
        mail=aluno.email_academico or None,
        extensionAttribute1=None,
        extensionAttribute2='Aluno',
        extensionAttribute3=None,
        extensionAttribute4=aluno.email_academico or None,
        extensionAttribute5=aluno.email_google_classroom or None,
        extensionAttribute10=None,
    )
    # Filtro de autenticação
    for filtro in ldap_conf.filterstr:
        attrs[filtro] = aluno.matricula
    for key, value in list(attrs.items()):
        if key == 'thumbnailPhoto':
            continue
        if isinstance(value, str):
            value = value.strip()
        elif isinstance(value, list):
            value = [i.strip() for i in value]
        attrs[key] = value

    return attrs


####################
# PrestadorServico #
####################


def get_prestadorservico_attrs(prestador, ldap_conf):
    """
    Retorna os atributos para sincronização do usuário no LDAP.
    """
    dn = get_funcionario_dn(prestador, ldap_conf)
    if not dn:
        return dict()

    department = None
    extensionAttribute1 = None

    if prestador.setor:
        department = prestador.setor.sigla
        if prestador.setor.uo:
            extensionAttribute1 = prestador.setor.uo.setor.sigla
    vinculo = prestador.get_vinculo()
    extenssionAttribute2 = 'Prestador'
    if vinculo and hasattr(vinculo, 'professor_set') and vinculo.professor_set.exists():
        extenssionAttribute2 = 'Prestador-Docente'

    attrs = dict(
        dn=dn,
        userPrincipalName='{}@{}'.format(prestador.username, ldap_conf.domain),
        # sAMAccountName       = prestador.username,
        active=prestador.ativo,
        objectClass=['top', 'person', 'organizationalPerson', 'user'],
        cn=prestador.username,
        givenName=prestador.nome.split()[0],
        sn=' '.join(prestador.nome.split()[1:])[:64] or None,
        DisplayName=prestador.nome,
        userAccountControl=prestador.ativo and '512' or '514',  # 512 ativo, 514 inativo
        accountExpires='0',  # Nunca expira
        department=department,
        description=prestador.nome,
        extensionAttribute1=extensionAttribute1,  # campus
        extensionAttribute2=extenssionAttribute2,
        extensionAttribute3=None,
        extensionAttribute4=None,
        extensionAttribute5=prestador.email_google_classroom or None,
        extensionAttribute10=prestador.ativo and 'Ativo' or 'Inativo',
        title='Prestador',
        thumbnailPhoto=None,
    )
    # Filtro de autenticação
    for filtro in ldap_conf.filterstr:
        attrs[filtro] = prestador.username

    for key, value in list(attrs.items()):
        if isinstance(value, str):
            value = value.strip()
        elif isinstance(value, list):
            value = [i.strip() for i in value]
        attrs[key] = value

    return attrs


def extract_cn_from_ldap_user(member):
    import ldap
    exploded_dn = ldap.dn.explode_dn(member, flags=ldap.DN_FORMAT_LDAPV2)
    # member_dn = {parts[0]: parts[1] for item in exploded_dn if (parts := item.split('='))}
    member_dn = dict()
    for item in exploded_dn:
        parts = item.split('=')
        if parts:
            member_dn[parts[0]] = parts[1]
    return member_dn["CN"]
