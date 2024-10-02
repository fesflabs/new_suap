from comum.models import UsuarioGrupoSetor, UsuarioGrupo
from djtools.templatetags.filters import in_group


def realizar_procedimentos_academicos(user, curso_campus=None):
    autorizado = False
    if not user.is_anonymous:
        autorizado = user.is_superuser
        if not autorizado:
            autorizado = UsuarioGrupo.objects.filter(user=user, group__name__in=['Administrador Acadêmico', 'Diretor Acadêmico Sistêmico']).exists()
            if not autorizado and curso_campus is not None:
                autorizado = UsuarioGrupoSetor.objects.filter(usuario_grupo__user=user, usuario_grupo__group__name__in=['Secretário Acadêmico', 'Diretor Acadêmico', 'Diretor de Ensino'], setor=curso_campus.diretoria.setor).exists()
                if not autorizado:
                    pessoa_fisica = user.get_profile()
                    autorizado = (
                        (pessoa_fisica and curso_campus.coordenador and pessoa_fisica.pk == curso_campus.coordenador.pk)
                        or (pessoa_fisica and curso_campus.coordenador_2 and pessoa_fisica.pk == curso_campus.coordenador_2.pk)
                        or False
                    )
                    if not autorizado and user.eh_servidor:
                        # é coordenador de modalidade de ensino
                        autorizado = user.get_vinculo().relacionamento.coordenadormodalidade_set.filter(modalidades=curso_campus.modalidade, diretoria=curso_campus.diretoria).exists()
                        if not autorizado:
                            autorizado = UsuarioGrupoSetor.objects.filter(
                                usuario_grupo__user=user, usuario_grupo__group__name='Comissão de Horários', setor__uo=curso_campus.diretoria.setor.uo
                            ).exists()
    return autorizado


def realizar_procedimentos_diarios_especiais(user, diario_especial=None):
    autorizado = user.is_superuser
    if not autorizado:
        autorizado = UsuarioGrupoSetor.objects.filter(usuario_grupo__user=user, usuario_grupo__group__name__in=['Secretário Acadêmico', 'Diretor Acadêmico', 'Coordenador de Curso', 'Coordenador de Desporto'], setor=diario_especial.diretoria.setor).exists()
        if not autorizado:
            autorizado = UsuarioGrupo.objects.filter(user=user, group__name__in=['Administrador Acadêmico', 'Diretor Acadêmico Sistêmico', 'Coordenador Acadêmico Sistêmico']).exists()
    return autorizado


def is_admin(user):
    return user.is_superuser or in_group(user, 'edu Administrador')


def is_responsavel(request, aluno):
    return request.user.is_anonymous and request.session.get('matricula_aluno_como_resposavel') == aluno.matricula


def is_proprio_aluno(request, aluno):
    return aluno.is_user(request)


def is_orientador(request, aluno):
    return aluno.matriculaperiodo_set.filter(projetofinal__orientador__vinculo__user=request.user).exists()


def is_coorientador(request, aluno):
    return (
        aluno.matriculaperiodo_set.filter(projetofinal__coorientadores__user=request.user).exists()
    )


def is_examinador(request, aluno):
    return (
        aluno.matriculaperiodo_set.filter(projetofinal__examinador_interno__user=request.user).exists()
        | aluno.matriculaperiodo_set.filter(projetofinal__examinador_externo__user=request.user).exists()
        | aluno.matriculaperiodo_set.filter(projetofinal__terceiro_examinador__user=request.user).exists()
    )


def is_presidente(request, aluno):
    return aluno.matriculaperiodo_set.filter(projetofinal__presidente__vinculo__user=request.user).exists()


def pode_ver_dados_aluno(request):
    return in_group(
        request.user,
        'Diretor Acadêmico,Diretor Acadêmico Sistêmico,Coordenador de Curso,Coordenador Acadêmico Sistêmico,Coordenador de Modalidade Acadêmica,Administrador Acadêmico,Secretário Acadêmico,Diretor Acadêmico,Estagiário,Professor,Coordenador de Estágio,Coordenador de Estágio Sistêmico,Coordenador de Estágio Docente,Coordenador de Registros Acadêmicos,Estagiário Acadêmico Sistêmico',
    )


def pode_ver_dados_sociais(request, aluno):
    return is_admin(request.user) or is_proprio_aluno(request, aluno) or in_group(request.user, 'Assistente Social, Coordenador de Atividades Estudantis Sistêmico')


def pode_ver_dados_academicos(request, aluno):
    return is_admin(request.user) or is_responsavel(request, aluno) or is_proprio_aluno(request, aluno) or pode_ver_dados_aluno(request)


def tem_permissao_realizar_procedimentos(user, aluno):
    return is_admin(user) or realizar_procedimentos_academicos(user, aluno.curso_campus)


def pode_realizar_procedimentos_enade(user, curso_campus):
    if user.is_anonymous:
        return False
    autorizado = user.is_superuser
    if not autorizado:
        autorizado = UsuarioGrupo.objects.filter(user=user, group__name__in=['Administrador Acadêmico', 'Diretor de Avaliação e Regulação do Ensino', 'Operador ENADE']).exists()
        if not autorizado:
            pessoa_fisica = user.get_profile()
            autorizado = (UsuarioGrupoSetor.objects.filter(usuario_grupo__user=user, usuario_grupo__group__name='Coordenador de Curso', setor=curso_campus.diretoria.setor).exists()
                          and (
                (pessoa_fisica and curso_campus.coordenador and pessoa_fisica.pk == curso_campus.coordenador.pk)
                or (curso_campus.coordenador_2 and pessoa_fisica.pk == curso_campus.coordenador_2)
            )
            )
    return autorizado


def pode_realizar_procedimentos(user, aluno):
    return is_admin(user) or tem_permissao_realizar_procedimentos(user, aluno) and not aluno.is_concluido()


def pode_ver_requisitos_de_conclusao(request, aluno):
    return is_admin(request.user) or pode_ver_dados_academicos(request, aluno) or in_group(request.user, 'Organizador de Formatura, Coordenador de Registros Acadêmicos')


def pode_ver_endereco_professores(user):
    return is_admin(user) or in_group(user, 'Administrador Acadêmico')


def pode_alterar_email(request, aluno):
    if request.user.is_anonymous:
        return False
    if aluno:
        coordenador_ti_sistemico = UsuarioGrupo.objects.filter(user=request.user, group__name='Coordenador de TI sistêmico').exists()
        coordenador_ti_campus = UsuarioGrupo.objects.filter(user=request.user, group__name='Coordenador de TI de campus').exists() and aluno.curso_campus.diretoria.setor.uo == request.user.get_vinculo().setor.uo
        cra = UsuarioGrupo.objects.filter(user=request.user, group__name='Coordenador de Registros Acadêmicos', setores__uo=aluno.curso_campus.diretoria.setor.uo_id).exists()
        if coordenador_ti_sistemico or coordenador_ti_campus or tem_permissao_realizar_procedimentos(request.user, aluno) or cra:
            return True
    return False
