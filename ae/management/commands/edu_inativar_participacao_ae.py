from datetime import datetime
from djtools.management.commands import BaseCommandPlus
from ae.models import Participacao
from django.contrib.auth.models import Group
from comum.models import UsuarioGrupo
from djtools.utils import send_notification
from django.conf import settings


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        titulo = '[SUAP] Encerramento de Participação do Aluno em Programa'
        grupo = Group.objects.get(name='Assistente Social')

        for participacao in Participacao.abertas.filter(aluno__situacao__ativo=False):
            participacao.data_termino = datetime.today()
            participacao.motivo_termino = "O aluno possui situação de matrícula inativa na instituição."
            participacao.save()
            texto = (
                '<h1>Encerramento de Participação do Aluno em Programa</h1>'
                '<p>A participação do aluno \'{}\' foi encerrada pois o mesmo possui situação de matrícula inativa na instituição.</p>'.format(participacao.aluno)
            )

            for usuario in UsuarioGrupo.objects.filter(group=grupo, user__vinculo__setor__uo=participacao.aluno.curso_campus.diretoria.setor.uo):
                send_notification(titulo, texto, settings.DEFAULT_FROM_EMAIL, [usuario.user.get_vinculo()])
