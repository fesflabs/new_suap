# -*- coding: utf-8 -*-
import subprocess
from django.utils import termcolors

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    help = 'Incluindo Unicode Literals em todas as classes'

    def incluir_unicode_literals(self):
        stdout, stderr = subprocess.Popen("find . -name '*.py' -not -path '*/migrations/*'", shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).communicate()

        for nome_arquivo in stdout.split('\n'):
            if '.py' in nome_arquivo and '2_to_3_unicode_literals.py' not in nome_arquivo:
                arquivo = open(nome_arquivo, 'r')
                texto = arquivo.read()
                arquivo.close()
                if not 'unicode_literals' in texto.decode('utf-8'):
                    utf8 = "# -*- coding: utf-8 -*-\nfrom __future__ import unicode_literals\n"
                    if not 'utf-8' in texto:
                        texto = utf8 + texto
                    else:
                        if "# -*- coding: utf-8 -*-" in texto:
                            texto = texto.replace("# -*- coding: utf-8 -*-", utf8)
                        elif "# -*- coding: utf-8 -*" in texto:
                            texto = texto.replace("# -*- coding: utf-8 -*", utf8)
                        elif "# coding=utf-8" in texto:
                            texto = texto.replace("# coding=utf-8", utf8)
                    arquivo = open(nome_arquivo, 'w')
                    arquivo.write(texto)
                    arquivo.close()

    def handle(self, *args, **options):
        try:
            self.retirar_unicode()
        except Exception as e:
            self.stderr.write(termcolors.make_style(fg='red', opts=('bold',))(str(e)))
            raise
