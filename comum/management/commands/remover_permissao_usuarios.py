# -*- coding: utf-8 -*-
from django.contrib.auth.models import Group

from djtools.management.commands import BaseCommandPlus
from edu.models import Aluno
from rh.models import PessoaFisica, Servidor


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        self.remover_chaves_usuario_inativos()
        self.remover_servidores_inativos()

    def remover_chaves_usuario_inativos(self):
        pessoas_fisicas = PessoaFisica.objects.filter(chave__isnull=False).distinct()
        alunos = Aluno.objects.filter(id__in=pessoas_fisicas.filter(aluno_edu_set__isnull=False).values_list('aluno_edu_set__id', flat=True))
        servidores = Servidor.objects.filter(id__in=pessoas_fisicas.filter(servidores__isnull=False).values_list('servidores__id', flat=True))

        # Remoção de permissão de chaves para servidores removidos/redistribuídos
        servidores = servidores.filter(situacao__nome_siape='REDISTRIBUIDO')
        for servidor in servidores:
            for chave in servidor.chave_set.all():
                chave.pessoas.remove(servidor)

        # alunos/bolsistas egressos ou transferidos (sem matrícula ativa)
        alunos = alunos.filter(situacao__ativo=False)
        for aluno in alunos:
            for chave in aluno.pessoa_fisica.chave_set.all():
                chave.pessoas.remove(aluno.pessoa_fisica)

    def remover_servidores_inativos(self):
        grupo_avaliador_sala = Group.objects.get(name='Avaliador de Sala')
        servidores_inativos = Servidor.objects.inativos().filter(user__groups=grupo_avaliador_sala)
        for servidor in servidores_inativos:
            servidor.user.groups.remove(grupo_avaliador_sala)
