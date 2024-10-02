# -*- coding: utf-8 -*-

"""
Criando o banco de dados suap_dev baseado nos dados iniciais dos testes do Suap.
"""

from django.core.management import call_command

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        call_command('test_suap', 'comum.tests.TestCase', '--nopylint', '--failfast', '--update-dev-db')
