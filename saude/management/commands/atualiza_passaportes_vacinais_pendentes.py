# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from saude.management.commands import importar_dados_rnmaisvacina
from saude.models import PassaporteVacinalCovid


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        erros = 0
        total = 0
        for passaporte in PassaporteVacinalCovid.objects.filter(situacao_passaporte=PassaporteVacinalCovid.PENDENTE):
            options = {'cpf': passaporte.cpf, 'vinculo': passaporte.vinculo.id,
                       'campus': passaporte.uo.id, 'pythonpath': None, 'verbosity': '1',
                       'traceback': None, 'settings': None}
            importar_dados_command = importar_dados_rnmaisvacina.Command()
            count_exceptions = importar_dados_command.handle(*args, **options)
            if count_exceptions:
                erros += 1
            else:
                total += 1
        mensagem = '\n\t RESUMO - Passaportes Pendentes atualizados'

        mensagem += '\n{} \t TOTAL '.format(total)
        mensagem += '\n{} \t Exceções '.format(erros)
        return mensagem
