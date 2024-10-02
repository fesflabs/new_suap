# coding=utf-8
from django.db.models import Q

from djtools.management.commands import BaseCommandPlus
from rh.models import PessoaFisica
from comum.models import User


class Command(BaseCommandPlus):
    help = 'Verifica se a pessoa fisica tem aluno, servidor ou prestador'

    def handle(self, *args, **options):
        print('Atualizando Users')
        User.objects.filter(pessoafisica__funcionario__servidor__isnull=False, eh_servidor=False).update(eh_servidor=True)
        User.objects.filter(pessoafisica__funcionario__servidor__isnull=True, eh_servidor=True).update(eh_servidor=False)

        User.objects.filter(pessoafisica__funcionario__servidor__eh_docente=True, eh_docente=False).update(eh_docente=True)
        User.objects.filter(pessoafisica__funcionario__servidor__eh_docente=False, eh_docente=True).update(eh_docente=False)

        User.objects.filter(pessoafisica__funcionario__servidor__eh_tecnico_administrativo=True, eh_tecnico_administrativo=False).update(eh_tecnico_administrativo=True)
        User.objects.filter(pessoafisica__funcionario__servidor__eh_tecnico_administrativo=False, eh_tecnico_administrativo=True).update(eh_tecnico_administrativo=False)

        User.objects.filter(pessoafisica__funcionario__prestadorservico__isnull=False, eh_prestador=False).update(eh_prestador=True)
        User.objects.filter(pessoafisica__funcionario__prestadorservico__isnull=True, eh_prestador=True).update(eh_prestador=False)

        User.objects.filter(pessoafisica__aluno_edu_set__isnull=False, eh_aluno=False).update(eh_aluno=True)
        User.objects.filter(pessoafisica__aluno_edu_set__isnull=True, eh_aluno=True).update(eh_aluno=False)

        print('Atualizando Pessoas')
        for pessoa in PessoaFisica.objects.filter(
            Q(eh_aluno=False, aluno_edu_set__isnull=False)
            | Q(eh_aluno=True, aluno_edu_set__isnull=True)
            | Q(eh_servidor=False, funcionario__servidor__isnull=False)
            | Q(eh_servidor=True, funcionario__servidor__isnull=True)
            | Q(eh_prestador=False, funcionario__prestadorservico__isnull=False)
            | Q(eh_prestador=True, funcionario__prestadorservico__isnull=True)
        ):
            pessoa.save()
