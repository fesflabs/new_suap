from djtools.utils import normalizar_nome_proprio
from ppe.models import TrabalhadorEducando, CursoTurma, TutorTurma
from rh.models import UnidadeOrganizacional


def serialize(obj, add_id=False):
    dados = dict()
    if obj and add_id:
        dados.update(id=obj.id)
    if isinstance(obj, CursoTurma):
        componente = obj.curso_formacao.curso
        dados.update(
            situacao=obj.get_situacao_display() or "",
            descricao=componente.descricao or "",
            descricao_historico=componente.descricao_historico or "",
            nome_breve_curso_moodle=obj.nome_breve_curso_moodle,
        )
    elif isinstance(obj, TrabalhadorEducando):
        dados.update(
            matricula=obj.pessoa_fisica.cpf.replace(".", "").replace("-", "") or "",
            nome=normalizar_nome_proprio(obj.pessoa_fisica.nome) or "",
            email=obj.pessoa_fisica.email or "",
            email_secundario=obj.pessoa_fisica.email_secundario or "",
            situacao=obj.pessoa_fisica.user and obj.pessoa_fisica.user.is_active and "ativo" or "inativo",
        )
    elif isinstance(obj, TutorTurma):
        dados.update(
            nome=normalizar_nome_proprio(obj.tutor.pessoa_fisica.nome) or "",
            email=obj.tutor.pessoa_fisica.email or "",
            email_secundario=obj.tutor.pessoa_fisica.email_secundario or "",
            tipo="Principal",
            login=obj.tutor.pessoa_fisica.user.username,
            status=obj.tutor.pessoa_fisica.user.is_active and "ativo" or "inativo",
        )

    return dados