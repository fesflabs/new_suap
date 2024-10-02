from comum.models import UsuarioGrupoSetor, UsuarioGrupo
from djtools.templatetags.filters import in_group


def is_admin(user):
    return user.is_superuser or in_group(user, 'Secretário(a) Residência')


def is_responsavel(request, residente):
    return request.user.is_anonymous and request.session.get('matricula_residente_como_resposavel') == residente.matricula


def is_proprio_residente(request, residente):
    return residente.is_user(request)


def pode_ver_dados_residente(request):
    return in_group(
        request.user,
        'Secretário(a) Residência',
    )


def pode_ver_dados_bancarios(request):
    return request.user.has_perm('residencia.view_dados_bancarios')


def pode_ver_dados_sociais(request, residente):
    return is_admin(request.user) or is_proprio_residente(request, residente)


def tem_permissao_realizar_procedimentos(user, residente):
    curso_campus = None
    if residente and hasattr(residente, 'curso_campus'):
        curso_campus = residente.curso_campus
    return is_admin(user) or residente and realizar_procedimentos_academicos(user, curso_campus)


def realizar_procedimentos_academicos(user, curso_campus=None):
    autorizado = False
    if not user.is_anonymous:
        autorizado = user.is_superuser
        if not autorizado:
            autorizado = is_admin(user)
            # autorizado = UsuarioGrupo.objects.filter(user=user, group__name__in=['Administrador Acadêmico', 'Diretor Acadêmico Sistêmico']).exists()
            # if not autorizado and curso_campus is not None:
            #     autorizado = UsuarioGrupoSetor.objects.filter(usuario_grupo__user=user, usuario_grupo__group__name__in=['Secretário Acadêmico', 'Diretor Acadêmico', 'Diretor de Ensino'], setor=curso_campus.diretoria.setor).exists()
            #     if not autorizado:
            #         pessoa_fisica = user.get_profile()
            #         autorizado = (
            #             (pessoa_fisica and curso_campus.coordenador and pessoa_fisica.pk == curso_campus.coordenador.pk)
            #             or (pessoa_fisica and curso_campus.coordenador_2 and pessoa_fisica.pk == curso_campus.coordenador_2.pk)
            #             or False
            #         )
            #         if not autorizado and user.eh_servidor:
            #             # é coordenador de modalidade de ensino
            #             autorizado = user.get_vinculo().relacionamento.coordenadormodalidade_set.filter(modalidades=curso_campus.modalidade, diretoria=curso_campus.diretoria).exists()
            #             if not autorizado:
            #                 autorizado = UsuarioGrupoSetor.objects.filter(
            #                     usuario_grupo__user=user, usuario_grupo__group__name='Comissão de Horários', setor__uo=curso_campus.diretoria.setor.uo
            #                 ).exists()
    return autorizado


def pode_ver_dados_academicos(request, residente):
    return is_admin(request.user) or is_responsavel(request, residente) or is_proprio_residente(request, residente) or pode_ver_dados_residente(request)


def pode_alterar_email_residente(request, residente):
    if request.user.is_anonymous:
        return False
    if residente:
        coordenador_ti_sistemico = UsuarioGrupo.objects.filter(user=request.user, group__name='Coordenador de TI sistêmico').exists()
        if coordenador_ti_sistemico or is_admin(request.user):
            return True
    return False
