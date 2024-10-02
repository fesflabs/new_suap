# -*- coding: utf-8 -*-

from django.core.management import call_command

from comum.models import Configuracao
from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        commands = list()
        commands.append('sync_ldap_alunos')
        commands.append('sync_ldap_servidores')
        commands.append('sync_ldap_prestadores')
        commands.append('sync_ldap_ous')
        # Agora via configuração no ldap_backend o usuário escolhe se quer ou não logar com LDAP ou só Django mesmo
        if Configuracao.get_valor_por_chave('ldap_backend', 'utilizar_autenticacao_via_ldap'):
            commands.append('prevent_login_with_modelbackend')

        for command in commands:
            call_command(command, interactive=False, raise_exception=False)
