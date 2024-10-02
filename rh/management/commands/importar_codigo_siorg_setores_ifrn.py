# -*- coding: utf-8 -*-
from djtools.management.commands import BaseCommandPlus
from rh.models import Setor
from suds.client import Client
import datetime
from collections import Counter


class Command(BaseCommandPlus):
    def print_list(self, list):
        for lista in list:
            print(lista)

    def handle(self, *args, **options):

        title = 'RH - Importação do Código SIORG dos Setores do IFRN'
        print('')
        print(('- ' * len(title)))
        print(title)
        print(('- ' * len(title)))

        print(
            'ATENÇÃO: Por conta de diferenças cadastrais entre os setores retornados pelo SIORG e os setores '
            'cadastrados no SUAP do IFRN, este command tem que ser avaliado antes de ser executado. Em tese ele irá '
            'atender vários outros órgãos, contudo caberá ao responsável pelo órgão fazer essa avaliação e implementar '
            'possíveis ajustes, atentendo assim as suas necessidades. Caso deseje, você pode executar apenas "SIMULAR" '
            'o processamento, sem que qualquer dado seja alterado no banco de dados.'
        )

        print()
        executar_command = input('Informe o que deseja fazer? (SIMULAR/EXECUTAR/ABORTAR) ').strip().upper()

        executar_simulacao = executar_command == 'SIMULAR'
        executar_pra_valer = executar_command == 'EXECUTAR'
        if not executar_simulacao and not executar_pra_valer:
            print()
            print('Processamento abortado.')
            return

        print()
        print(('Início do processamento: {0}'.format(datetime.datetime.now().strftime('%d/%m/%Y - %H:%M:%S'))))
        print()

        # Documentação do Novo Web Service SIORG Versão 1.1
        # http://www.dainf.ct.utfpr.edu.br/~caio/ws/
        # https://siorg.planejamento.gov.br/siorg-cidadao-webapp/pages/listar_orgaos_estruturas/listar_orgaos_estruturas.jsf#bxResultado
        url_service = 'http://estruturaorganizacional.dados.gov.br/ConsultarEstruturaWSImpl?wsdl'
        metodo = 'consultarEstruturaOrganizacionalCompleta'

        # https://softwarepublico.gov.br/archives/thread/sei-negocio/duvida-codigo-siorg-na-composicao-do-nup
        cliente_ws = None
        try:
            print()
            print(('Tentando consumir o webservice "{0}" oferecido pelo Governo Federal...'.format(url_service)))

            cliente_ws = Client(url_service)
            cliente_ws.options.location = url_service.split('?')[0]
            # list_of_methods = [method for method in client.wsdl.services[0].ports[0].methods]
            # for m in list_of_methods:
            #     print m

            print('Webservice carregado com sucesso.')
        except Exception as e:
            print(('Erro ao consumir o webservices. Detalhes: {0}'.format(e)))
            return

        print()

        # O parâmetro "codigoUnidade" é o código siorg. No caso do IFRN o código é o 439.
        # http://estruturaorganizacional.dados.gov.br/doc/orgao-entidade.xml
        # http://estruturaorganizacional.dados.gov.br/doc/unidade-organizacional/439
        # https://www.governoeletronico.gov.br/eixos-de-atuacao/governo/novo-siorg/documentos-e-arquivos/SIORG-NovoSiorg-v1.1-WebServices.pdf
        codigo_unidade_ifrn = 439

        print(('Consumindo o método {0}...'.format(metodo)))
        print(('Carregando a estrutura organizacional do IFRN (código {0}) segundo o Governo Federal...'.format(codigo_unidade_ifrn)))
        print(
            'Atenção: Cada órgão tem um código identificador junto ao Governo Federal. Para saber qual é o código '
            'da sua entidade, faça o seguinte: \n'
            '1 - Acesse http://estruturaorganizacional.dados.gov.br/doc/orgao-entidade.xml; \n'
            '2 - Faça uma busca textual pela sigla da sua entidade. Ex: IFRN, IFPB, IFPE; \n'
            '3 - Procure o atributo <codigoOrgaoEntidade>. Nele existirá uma URL com um número ao final. Esse número '
            'é o código da sua entidade.'
        )

        retorno_ws = cliente_ws.service.consultarEstruturaOrganizacionalCompleta(codigoUnidade=codigo_unidade_ifrn)
        log_sucesso_setores_codigo_siorg_mantido = list()
        log_sucesso_setores_codigo_siorg_atualizado = list()
        log_erro = list()

        siglas_setores_governo_federal = list()
        for u in retorno_ws.unidades:
            codigo_siorg = u.codigoUnidade
            sigla = u.sigla.replace('-', '/').lstrip()
            nome = u.nome.lstrip()

            siglas_setores_governo_federal.append(sigla)

            # Tentativa 1 - Pela sigla...
            # Somente os setores que tem funcionarios serão atualizados. Isso evita o problema dos setores duplicados,
            # que apresentam o mesma sigla, contudo um tem funcionários e o outro não. O que tem funcionários é o correto,
            # o que não tem será, em tese, excluído futuramente.
            suap_setor = Setor.todos.filter(sigla=sigla).exclude(funcionarios__isnull=True)

            # Tentativa 2 - Pela sigla do campus e pelo nome do setor...
            # Alguns setores do SUAP estão com a sigla diferente da sigla retornada pelo webservices, mas tem o mesmo nome.
            #
            # Exemplo:
            # WebServices >>> Coordenação de Pesquisa e Inovação (CPI/ZN - Código Siorg: 106960)
            # Suap >>> Coordenação de Pesquisa e Inovação (COPEIN/ZN)
            if not suap_setor.exists() and len(sigla.split('/')) > 1:
                sigla_campus = sigla.split('/')[-1]
                # print sigla_campus, nome
                suap_setor = Setor.todos.filter(uo__sigla=sigla_campus, nome=nome).exclude(funcionarios__isnull=True)

            if suap_setor.exists():
                if suap_setor.count() > 1:
                    log_erro.append(
                        '{0} ({1} - Código Siorg: {2}); Importação não realizada. Existem {3} usando a mesma sigla.'.format(nome, sigla, codigo_siorg, suap_setor.count())
                    )
                else:
                    suap_setor = suap_setor[0]

                    if suap_setor.codigo_siorg:
                        if sigla == suap_setor.sigla:
                            log_sucesso_setores_codigo_siorg_mantido.append('{0} ({1} - Código Siorg: {2})'.format(nome, sigla, codigo_siorg))
                        else:
                            log_sucesso_setores_codigo_siorg_mantido.append(
                                '{0} ({1} - Código Siorg: {2}); Sigla do Setor no SUAP: {3}'.format(nome, sigla, codigo_siorg, suap_setor.sigla)
                            )
                    else:
                        suap_setor.codigo_siorg = codigo_siorg
                        if executar_pra_valer:
                            suap_setor.save()

                        if sigla == suap_setor.sigla:
                            log_sucesso_setores_codigo_siorg_atualizado.append('{0} ({1} - Código Siorg: {2})'.format(nome, sigla, codigo_siorg))
                        else:
                            log_sucesso_setores_codigo_siorg_atualizado.append(
                                '{0} ({1} - Código Siorg: {2}); Sigla do Setor no SUAP: {3}'.format(nome, sigla, codigo_siorg, suap_setor.sigla)
                            )

            else:
                log_erro.append('{0} ({1} - Código Siorg: {2}); Setor não localizado no SUAP.'.format(nome, sigla, codigo_siorg))

        counter_siglas_setores_governo_federal = Counter(siglas_setores_governo_federal)
        log_alerta_setores_com_mesma_sigla_segundo_governo_federal = list()
        for k, v in list(counter_siglas_setores_governo_federal.items()):
            if v > 1:
                log_alerta_setores_com_mesma_sigla_segundo_governo_federal.append('O setor de sigla "{0}" possui {1} registro(s) na base de dados do Governo Federal.'.format(k, v))

        if len(log_alerta_setores_com_mesma_sigla_segundo_governo_federal) > 0:
            print()
            print(
                (
                    'ATENÇÃO: As unidades listadas abaixo, num total de {0} registro(s), apresentam a mesma sigla na '
                    'base de dados do Governo Federal. Possivelmente são de campis diferentes, por isso se faz necessário '
                    'averiguar caso a caso para definir o código SIORG correto no SUAP!'.format(len(log_alerta_setores_com_mesma_sigla_segundo_governo_federal))
                )
            )
            self.print_list(log_alerta_setores_com_mesma_sigla_segundo_governo_federal)

        titulo_log_sucesso_setores_codigo_siorg_mantido = 'Unidades Que Já Possuíam Código Siorg Definidos no SUAP: {0} registro(s)'.format(
            len(log_sucesso_setores_codigo_siorg_mantido)
        )
        print()
        print(('- ' * len(titulo_log_sucesso_setores_codigo_siorg_mantido)))
        print(titulo_log_sucesso_setores_codigo_siorg_mantido)
        print(('- ' * len(titulo_log_sucesso_setores_codigo_siorg_mantido)))
        self.print_list(log_sucesso_setores_codigo_siorg_mantido)

        titulo_log_sucesso_setores_codigo_siorg_atualizado = 'Unidades Que Tiveram o Código Siorg Atualizado com Sucesso no SUAP: {0} registro(s)'.format(
            len(log_sucesso_setores_codigo_siorg_atualizado)
        )
        print()
        print(('- ' * len(titulo_log_sucesso_setores_codigo_siorg_atualizado)))
        print(titulo_log_sucesso_setores_codigo_siorg_atualizado)
        print(('- ' * len(titulo_log_sucesso_setores_codigo_siorg_atualizado)))
        self.print_list(log_sucesso_setores_codigo_siorg_atualizado)

        titulo_log_erro = 'Unidades Não Atualizadas Pois Não Existem Registros Equivalente no SUAP: {0} registro(s)'.format(len(log_erro))
        print()
        print(('- ' * len(titulo_log_erro)))
        print(titulo_log_erro)
        print(('- ' * len(titulo_log_erro)))
        self.print_list(log_erro)

        print()
        print('Processamento concluído com sucesso.')
        if not executar_pra_valer:
            print(
                'OBS: Este processamento foi apenas uma SIMULAÇÃO. Nada foi gravado no banco de dados. Para executar '
                'algo em definitivo, realize novamente o processamento e escolha a opção "EXECUTAR".'
            )

        print()
        print(('Fim do processamento: {0}'.format(datetime.datetime.now().strftime('%d/%m/%Y - %H:%M:%S'))))
