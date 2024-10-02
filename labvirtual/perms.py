from comum.models import UsuarioGrupoSetor, UsuarioGrupo
from djtools.templatetags.filters import in_group


def is_admin(user):
    return user.is_superuser


def pode_gerenciar_solicitacao_labvirtual(user, laboratorio=None):
    autorizado = is_admin(user) or in_group(user, 'edu Administrador')
    if not autorizado:
        grupos_sistemicos = ['Administrador Acadêmico', 'Diretor Acadêmico Sistêmico', 'Coordenador Acadêmico Sistêmico']
        autorizado = UsuarioGrupo.objects.filter(user=user, group__name__in=grupos_sistemicos).exists()
        if not autorizado and laboratorio:
            eh_do_campus = laboratorio.location == user.get_vinculo().setor.uo
            grupos_campus = ['Secretário Acadêmico', 'Diretor Acadêmico', 'Coordenador de Curso']
            autorizado = eh_do_campus and UsuarioGrupoSetor.objects.filter(usuario_grupo__user=user, usuario_grupo__group__name__in=grupos_campus).exists()
        #
    return autorizado


def pode_gerenciar_vdi(user, laboratorio=None):
    autorizado = is_admin(user)
    if not autorizado:
        autorizado = UsuarioGrupo.objects.filter(user=user, group__name='Coordenador de TI sistêmico').exists()
        if not autorizado and laboratorio:
            eh_do_campus = laboratorio.campus == user.get_vinculo().setor.uo
            autorizado = eh_do_campus and UsuarioGrupo.objects.filter(user=user, group__name='Coordenador de TI de campus').exists()
    #
    return autorizado
