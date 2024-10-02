# -*- coding: utf-8 -*-
import subprocess
from django.utils import termcolors

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    help = 'Retirando unicode todas as classes'

    def retirar_unicode(self):
        stdout, stderr = subprocess.Popen("find . -name '*.py' -not -path '*/migrations/*'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()

        cmd = "2to3 -wnf unicode {}"
        for nome_arquivo in stdout.split('\n'):
            if '.py' in nome_arquivo and '2_to_3_unicode_suap.py' not in nome_arquivo:
                comando = cmd.format(nome_arquivo)
                self.stdout.write(termcolors.make_style(fg='green', opts=('bold',))('>>> Usando comando "{}" ...'.format(comando)))
                subprocess.Popen(comando, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()

    def handle(self, *args, **options):
        try:
            self.retirar_unicode()
        except Exception as e:
            self.stderr.write(termcolors.make_style(fg='red', opts=('bold',))(str(e)))
            raise
