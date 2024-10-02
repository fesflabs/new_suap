from comum.models import UsuarioGrupoSetor, UsuarioGrupo
from djtools.templatetags.filters import in_group


def is_admin(user):
    return user.is_superuser or in_group(user, ['Coordenador(a) PPE', 'Supervisor(a) Pedagógico(a)'])


def is_responsavel(request, trabalhadoreducando):
    return request.user.is_anonymous and request.session.get('matricula_trabalhadoreducando_como_resposavel') == trabalhadoreducando.matricula


def is_proprio_trabalhadoreducando(request, trabalhadoreducando):
    return trabalhadoreducando.is_user(request)


def pode_ver_dados_trabalhadoreducando(request):
    return in_group(
        request.user,
        ['Coordenador(a) PPE', 'Supervisor(a) Pedagógico(a)'],
    )


def pode_ver_dados_sociais(request, trabalhadoreducando):
    return is_admin(request.user) or is_proprio_trabalhadoreducando(request, trabalhadoreducando)


def tem_permissao_realizar_procedimentos(user, trabalhadoreducando):
    return is_admin(user) or trabalhadoreducando and realizar_procedimentos_academicos(user)


def realizar_procedimentos_academicos(user):
    autorizado = False
    if not user.is_anonymous:
        autorizado = user.is_superuser
        if not autorizado:
            autorizado = is_admin(user)
            if not autorizado:
                autorizado = UsuarioGrupo.objects.filter(user=user, group__name__in=['Coordenador(a) PPE',]).exists()
    return autorizado


def pode_ver_dados_academicos(request, trabalhadoreducando):
    return is_admin(request.user) or is_responsavel(request, trabalhadoreducando) or is_proprio_trabalhadoreducando(request, trabalhadoreducando) or pode_ver_dados_trabalhadoreducando(request)


def pode_alterar_email_trabalhadoreducando(request, trabalhadoreducando):
    if request.user.is_anonymous:
        return False
    if trabalhadoreducando:
        coordenador_ti_sistemico = UsuarioGrupo.objects.filter(user=request.user, group__name='Coordenador de TI sistêmico').exists()
        if coordenador_ti_sistemico or is_admin(request.user):
            return True
    return False

def pode_ver_requisitos_de_conclusao(request, trabalhadoreducando):
    return is_admin(request.user) or pode_ver_dados_academicos(request, trabalhadoreducando) or in_group(request.user, 'Coordenador(a) PPE, Gestor(a) PPE')