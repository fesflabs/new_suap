# -*- coding: utf-8 -*-
import datetime

from django.apps import apps
from django.db.models import Q

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    """
        O tipo de documento Memorando ficou inativo no SUAP a partir de 01/01/2020. A medida atende às orientações do
        Manual de Redação da Presidência da República (2018) e do Manual de Redação Oficial do IFRN (2019).
         Este comando  cancelaa todas as solicitações pendentes existentes em documentos do tipo memorando.
    """

    def handle(self, *args, **options):
        Papel = apps.get_model("rh", "Papel")
        Aluno = apps.get_model("edu", "Aluno")

        executar_command = input('Informe o que deseja fazer? (SIMULAR/EXECUTAR/ABORTAR) ').strip().upper()

        executar_simulacao = executar_command == 'SIMULAR'
        executar_pra_valer = executar_command == 'EXECUTAR'
        if not executar_simulacao and not executar_pra_valer:
            print()
            print('Processamento abortado.')
            return

        title = 'Doc. Eletrônico - Command para inativar o papel para alunos sem matricula ativa que possuem papel'
        print('')
        print(('- ' * len(title)))
        print(title)
        print(('- ' * len(title)))

        hoje = datetime.date.today()
        alunos_com_papel_ativo = Aluno.objects.filter(pessoa_fisica__papel__data_inicio__lte=hoje, pessoa_fisica__papel__tipo_papel=Papel.TIPO_PAPEL_DISCENTE).exclude(
            Q(pessoa_fisica__papel__data_fim__isnull=False) | Q(pessoa_fisica__papel__data_fim__lte=hoje)
        )
        total_alunos = alunos_com_papel_ativo.count()
        counter = 0
        count_erros = 0
        qtd_inativados = 0
        exceptions = dict()
        if alunos_com_papel_ativo:
            print()
            print(('Foram encontrados {} alunos inativos com Papel do Tipo Discente ativo.'.format(alunos_com_papel_ativo.count())))
            for aluno in alunos_com_papel_ativo:
                try:
                    print("Analisando se o Aluno {} - matricula: {} esta com situação ativa no SUAP".format(aluno.pessoa_fisica.nome, aluno.matricula))
                    if not aluno.situacao.ativo:
                        if executar_pra_valer:
                            Papel.objects.filter(pessoa=aluno.pessoa_fisica, tipo_papel=Papel.TIPO_PAPEL_DISCENTE).update(data_fim=datetime.datetime.now())
                            qtd_inativados += 1
                            print("Inativou papeis do aluno {}".format(aluno.pessoa_fisica.nome))
                    else:
                        print("Aluno {} esta ativo".format(aluno.pessoa_fisica.nome))

                    print()
                    counter += 1
                    percentual = counter / float(total_alunos) * 100
                    print("{}% executado - {} de {} alunos".format(percentual, counter, total_alunos))
                except Exception as e:
                    count_erros += 1
                    exceptions[e] = aluno.matricula
                    continue

        else:
            print()
            print('Nenhum aluno inativo com papel de Discente ativo foi encontrado .')
        if exceptions:
            print('HOUVE ERRO NA EXECUÇÃO DOS SEGUINTES ITENS')
            for exception in exceptions:
                print(exception)
        print('Fim do processamento.')
        if not executar_pra_valer:
            print(
                'OBS: Este processamento foi apenas uma SIMULAÇÃO. Nada foi gravado no banco de dados. Para executar '
                'algo em definitivo, realize novamente o processamento e escolha a opção "EXECUTAR".'
            )
