from django.core.management.base import BaseCommand
from catalogo_provedor_servico.models import Solicitacao
from catalogo_provedor_servico.providers.impl.ifrn.codes import ID_GOVBR_6176_MATRICULA_EAD,\
    ID_GOVBR_6424_MATRICULA_CURSO_NIVEL_SUPERIOR_IFRN, ID_GOVBR_10054_MATRICULA_POS_GRADUACAO_IFRN, \
    ID_GOVBR_6410_MATRICULA_CURSO_NIVEL_TECNICO_IFRN
from django.apps import apps
from django.db import transaction


class Command(BaseCommand):
    '''
    Este command é voltado para o ambiente de desenvolvolvimento, para que se possa realizar "n" vezes a simulação de um
    atendimento digital por completo, ou seja, desde a sua solicitação até a sua execução.

    Exemplos de chamada:
    - - - - - - - - - -
    Simular a remoção da solicitação de id 1234:
     - python manage.py apagar_atendimentos_digitais -id 1234 -s
     - python manage.py apagar_atendimentos_digitais --id 1234 --simulate

    Remover a solicitação de id 1234:
     - python manage.py apagar_atendimentos_digitais -id 1234
     - python manage.py apagar_atendimentos_digitais --id 1234

    Apagar todas as solicitacões:
     - python manage.py apagar_atendimentos_digitais

    Simular a remoção de todas as solicitações:
    - python manage.py apagar_atendimentos_digitais --s
    - python manage.py apagar_atendimentos_digitais --simulate

    '''

    def add_arguments(self, parser):
        parser.add_argument('-id', '--id', type=str, help='Id da Solicitacao (Opcional)', )
        parser.add_argument('-s', '--simulate', action='store_true', help='Define se deve ser apenas uma simulacao.')

    @transaction.atomic()
    def handle(self, *args, **options):
        solicitacao_id = options['id']
        simulate = options['simulate']

        print('<<< Command apagar_atendimentos_digitais (catalogo_provedor_servico) >>>')
        print('Parâmetros informados: ')
        print(f' - id (Solicitacao): {solicitacao_id}', )
        print(f' - simulate: {simulate}\n')

        if simulate:
            print('Iniciando simulacao...\n')

        if not solicitacao_id:
            if not input('Deseja realmente apagar todas as solicitacoes? (S = Sim, N = Nao)').strip().upper() == 'S':
                print('Processamento abortado.')
                return

        if solicitacao_id:
            solicitacoes = Solicitacao.objects.filter(id=solicitacao_id)
        else:
            solicitacoes = Solicitacao.objects.all()

        if not solicitacoes:
            print('Nenhuma solicitacao encontrada.')
            print('FIM')
            return

        for solicitacao in solicitacoes:
            print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -')
            print(f'Solicitacao {solicitacao.id}')
            print(f' - Cpf: {solicitacao.cpf}')
            print(f' - Nome: {solicitacao.nome}')
            print(f' - Serviço: {solicitacao.servico.id_servico_portal_govbr} - {solicitacao.servico.titulo}\n')

            '''
            Exemplo de um dados_registros_execucao_as_json:
            [
                {
                    "app": "processo_eletronico",
                    "model": "Processo",
                    "id": 149920,
                    "operation": "CREATE",
                    "registered_on": "2020-09-21 17:13:23.797969"
                },
                {
                    "app": "documento_eletronico",
                    "model": "DocumentoDigitalizado",
                    "id": 584300,
                    "operation": "CREATE",
                    "registered_on": "2020-09-21 17:13:23.960084"
                },
                {
                    "app": "processo_eletronico",
                    "model": "DocumentoDigitalizadoProcesso",
                    "id": 580785,
                    "operation": "CREATE",
                    "registered_on": "2020-09-21 17:13:23.976396"
                },
                {
                    "app": "processo_eletronico",
                    "model": "Tramite",
                    "id": 550910,
                    "operation": "CREATE",
                    "registered_on": "2020-09-21 17:13:24.128199"
                }
            ]
            '''
            dados_registros_execucao_as_json = solicitacao.get_dados_registros_execucao_as_json()
            if dados_registros_execucao_as_json:
                print(' - Verificando registros criados ou atualizados durante a solicitação...')
                # A execução vai ser de trás pra frente porque os últimos registros criados devem ser os primeiros
                # a serem removidos.
                for dre in dados_registros_execucao_as_json[::-1]:
                    operation = dre['operation']
                    id = dre['id']
                    app_name = dre['app']
                    model_name = dre['model']
                    Model = apps.get_model(app_name, model_name)

                    if operation == 'CREATE':
                        print(f'   - Removendo o {model_name} ({app_name}) de id {id}.')
                        if not simulate:
                            Model.objects.filter(id=id).delete()

                    elif operation == 'UPDATE':
                        if solicitacao.servico.id_servico_portal_govbr in [ID_GOVBR_6176_MATRICULA_EAD, ID_GOVBR_6424_MATRICULA_CURSO_NIVEL_SUPERIOR_IFRN,
                                                                           ID_GOVBR_10054_MATRICULA_POS_GRADUACAO_IFRN, ID_GOVBR_6410_MATRICULA_CURSO_NIVEL_TECNICO_IFRN]:
                            if app_name == 'processo_seletivo' and model_name == 'CandidatoVaga':
                                print(f'   - Atualizando o {model_name} ({app_name}) de id {id}, permitindo assim uma nova matricula para o mesmo cidadao.')
                                if not simulate:
                                    Model.objects.filter(id=id).update(situacao=None)

            print('\n - Por fim, apagando a solicitacao em si e tudo que depende dela. Ex: SoliciacaoEtapa, SolicitacaoEtapaArquivo... .')
            if not simulate:
                Solicitacao.objects.filter(id=solicitacao_id).delete()
                # Solicitacao.objects.filter(id=solicitacao_id).update(status=Solicitacao.STATUS_EM_ANALISE)

            print('- - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - - -\n')

        if simulate:
            print('ATENÇÃO: Esta foi apenas uma simulacao, portando nenhum persitencia foi realizada.\n')

        print('<<< FIM >>>')
