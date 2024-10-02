# -*- coding: utf-8 -*-
from comum.models import PrestadorServico
from comum.utils import get_uo
from djtools.management.commands import BaseCommandPlus
from rh.models import Servidor
from edu.models import Aluno
import tqdm

from saude.management.commands import importar_dados_rnmaisvacina


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        erros = 0
        total = 0
        for servidor in tqdm.tqdm(Servidor.objects.ativos()):
            options = {'cpf': servidor.cpf, 'vinculo': servidor.get_vinculo().id, 'campus': get_uo(servidor.get_vinculo().user).id, 'pythonpath': None, 'verbosity': '1', 'traceback': None, 'settings': None}
            importar_dados_command = importar_dados_rnmaisvacina.Command()
            count_exceptions = importar_dados_command.handle(*args, **options)
            if count_exceptions:
                erros += 1
            else:
                total += 1
        mensagem = '\n\t RESUMO - SERVIDORES'

        mensagem += '\n{} \t TOTAL '.format(total)
        mensagem += '\n{} \t Exceções '.format(erros)

        erros = 0
        total = 0
        for aluno in tqdm.tqdm(Aluno.ativos.filter(pessoa_fisica__cpf__isnull=False, pessoa_fisica__user__isnull=False, vinculos__isnull=False)):
            options = {'cpf': aluno.pessoa_fisica.cpf, 'vinculo': aluno.get_vinculo().id, 'campus': aluno.curso_campus.diretoria.setor.uo.id, 'pythonpath': None, 'verbosity': '1', 'traceback': None, 'settings': None}
            importar_dados_command = importar_dados_rnmaisvacina.Command()
            count_exceptions = importar_dados_command.handle(*args, **options)
            if count_exceptions:
                erros += 1
            else:
                total += 1
        mensagem += '\n\t RESUMO - ALUNOS'

        mensagem += '\n{} \t TOTAL '.format(total)
        mensagem += '\n{} \t Exceções '.format(erros)

        erros = 0
        total = 0
        for prestador in tqdm.tqdm(PrestadorServico.objects.filter(vinculos__isnull=False, ativo=True, cpf__isnull=False, ocupacaoprestador__isnull=False).distinct()):
            if prestador.get_vinculo() and prestador.setor and prestador.setor.uo:
                options = {'cpf': prestador.cpf, 'vinculo': prestador.get_vinculo().id, 'campus': prestador.setor.uo.id, 'pythonpath': None, 'verbosity': '1', 'traceback': None, 'settings': None}
                importar_dados_command = importar_dados_rnmaisvacina.Command()
                count_exceptions = importar_dados_command.handle(*args, **options)
                if count_exceptions:
                    erros += 1
                else:
                    total += 1
        mensagem += '\n\t RESUMO - PRESTADORES DE SERVIÇO'

        mensagem += '\n{} \t TOTAL '.format(total)
        mensagem += '\n{} \t Exceções '.format(erros)
        return mensagem
