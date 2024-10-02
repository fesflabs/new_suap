# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from django.conf import settings
import os
from arquivo.models import Processo, Funcao


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        print('Importando Função e Processo ...')
        arquivo = os.path.join(settings.BASE_DIR, 'arquivo/static/arquivo/funcoes_processos.txt')
        txt_file = open(arquivo, 'r')
        txt_linhas = txt_file.readlines()
        funcoes_criadas = 0
        processos_criados = 0
        print('-----')

        for linha in txt_linhas:
            # funcao : processo
            funcao_descricao = linha.split(":")[1].strip()
            processo_descricao = linha.split(":")[0].strip()
            print(('Função: {}'.format(funcao_descricao)))
            print(('Processo: {}'.format(processo_descricao)))
            funcao, funcao_foi_criada = Funcao.objects.get_or_create(descricao=funcao_descricao)
            processo, processo_foi_criado = Processo.objects.get_or_create(descricao=processo_descricao)
            processo.funcao = funcao
            processo.save()
            if funcao_foi_criada:
                funcoes_criadas += 1
                if not processo.funcao:
                    processo.funcao = funcao
                    processo.save()
            if processo_foi_criado:
                processos_criados += 1
            print('-----')
        txt_file.close()
        print(('{} Funções criadas. {} Processos criados.'.format(funcoes_criadas, processos_criados)))
