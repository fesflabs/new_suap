# -*- coding: utf-8 -*-
import datetime

import ldap
from django.apps import apps

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def print_list(self, list):
        for lista in list:
            print(lista)

    def exibir_dados_setor_unificado(self, su_setores):
        print(' - Setores INATIVOS no Suap...')
        if not su_setores['inativos']:
            print('   - Nenhum')
        else:
            for s in su_setores['inativos']:
                print(('   - Sigla: {}   Campus: {}   Id: {}'.format(s.sigla, s.uo, s.id)))

        print(' - Setores ATIVOS no Suap...')
        if not su_setores['ativos']:
            print('   - Nenhum')
        else:
            for s in su_setores['ativos']:
                print(('   - Sigla: {}   Campus: {}   Id: {}'.format(s.sigla, s.uo, s.id)))

    def handle(self, *args, **options):
        title = 'RH - Observar Setores no AD (Active Directory)'
        print()
        print(('- ' * len(title)))
        print(title)
        print(('- ' * len(title)))

        print(
            'O objetivo deste command eh simplesmente varrer os setores "suap", verificar se ha o cadastro do respectivo\n'
            'setor no AD e se esse cadastro esta consistente ou se ha alguma problema. Obs: Toda a operacao eh somente\n'
            'leitura. Nada ha escrita no AD ou no SUAP!'
        )

        print()
        print()
        print(('Inicio do processamento: {0}'.format(datetime.datetime.now().strftime('%d/%m/%Y - %H:%M:%S'))))
        print()

        LdapConf = apps.get_model('ldap_backend', 'LdapConf')
        ldapconf = LdapConf.get_active()
        if not ldapconf:
            raise Exception('Nao foi encontrada nenhuma configuracao de AD no banco de dados do SUAP.')

        ad_url = ldapconf.uri
        ad_user = ldapconf.who
        ad_pass = ldapconf.cred
        base_address = ldapconf.base
        atts_to_read = ['*']

        print(('Dados do AD: \n - {}\n - {}\n - {}\n - {}'.format(ad_url, ad_user, ad_pass, base_address)))
        print('Tentando conexao com o AD...')
        connect = ldap.initialize(ad_url)
        connect.set_option(ldap.OPT_REFERRALS, 0)
        connect.simple_bind_s(who=ad_user, cred=ad_pass)
        print('Conexao realizada com sucesso!')
        print('')

        Setor = apps.get_model('rh', 'Setor')
        # setores = Setor.suap.filter(sigla='COCTADM/JC')
        # setores = Setor.todos.all().order_by('uo__sigla', 'sigla')
        setores = Setor.suap.all().order_by('uo__sigla', 'sigla')
        # setores = Setor.suap.filter(uo__isnull=False).order_by('uo__sigla', 'sigla')
        # setores = Setor.suap.filter(sigla='COFIMPAT/ZL').order_by('uo__sigla', 'sigla')

        # "setores_unificados" eh um dicionario de dicionarios, que tem como chave a sigla do setor. Seu objetivo eh
        # agrupar todas as Uos do SUAP que possuam a mesma sigla, visando facilitar posteriormente a busca no AD e a
        # analise que busca alguma inconsistencia no AD.
        setores_unificados = dict()
        for setor in setores:
            setor_unificado = setores_unificados.get(setor.sigla, None)
            if not setor_unificado:
                setor_unificado = dict()
                setor_unificado['inativos'] = list()
                setor_unificado['inativos_id'] = list()
                setor_unificado['ativos'] = list()
                setor_unificado['ativos_id'] = list()

            if setor.excluido:
                setor_unificado['inativos'].append(setor)
                setor_unificado['inativos_id'].append(setor.id)
            else:
                setor_unificado['ativos'].append(setor)
                setor_unificado['ativos_id'].append(setor.id)

            setores_unificados[setor.sigla] = setor_unificado

        # Uma vez que os setores do SUAP com a mesma sigla foram unificados...
        for su_sigla, su_setores in list(setores_unificados.items()):
            print(('Carregando dados do setor de sigla "{}" no AD...'.format(su_sigla)))
            # O ajuste abaixo na sigla do setor eh necessario porque no SUAP o cadastro geralmente inclue uma '/' para
            # separar a sigla do setor da sigla do campus, so que no AD ao inves da '/' usas-se '-'.
            search_param = 'OU={}'.format(su_sigla.replace('/', '-'))
            ad_rows = connect.search_s(base_address, ldap.SCOPE_SUBTREE, search_param, atts_to_read)

            msg_erro = ''
            # Se não há registro no AD...
            if not ad_rows:
                if su_setores['ativos_id']:
                    msg_erro += 'PROBLEMA: O setor nao existe no AD mas esta como ativo no SUAP.\n'
            # Caso contrário...
            else:
                for ad_row in ad_rows:
                    # dn eh a chave primaria do objeto no AD.
                    # dn = ad_row[0]
                    data = ad_row[1]
                    setor_id_ad = int(data.get('adminDescription', [-1])[0])

                    if setor_id_ad in su_setores['inativos_id']:
                        msg_erro += 'PROBLEMA: O setor do AD estah como INATIVO no SUAP.\n'
                    elif setor_id_ad not in su_setores['ativos_id']:
                        msg_erro += 'PROBLEMA: O setor do AD nao estah como ATIVO no SUAP.\n'

                    if len(su_setores['ativos_id']) > 1:
                        msg_erro = 'PROBLEMA: O setor do AD tem mais de uma UO ATIVA no SUAP.\n'

            # Se ha algum erro, ele será exibido.
            if msg_erro:
                print(msg_erro)
                self.exibir_dados_setor_unificado(su_setores)

                # Se o setor existe no AD, seus atributos tambem serao exibidos.
                if ad_rows:
                    print(' - Setor no AD...')
                    for key, value in list(data.items()):
                        print(('   - ', key, value))
            else:
                print('OK - O cadastro do setor no AD esta correto.')

            print()

        print()
        print('Processamento concluido com sucesso.')
        print(('Fim do processamento: {0}'.format(datetime.datetime.now().strftime('%d/%m/%Y - %H:%M:%S'))))
