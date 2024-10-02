# -*- coding: utf-8 -*-
"""
Created on 25/02/2015

@author: misael
"""

from comum.management.commands.media_padronizacao_00_comum import MediaCommand, FileUtils
from django.conf import settings
from rh.models import PessoaFisica
from sets import Set


class Command(MediaCommand):
    SIMULACAO = False

    def __init__(self):
        modulo = 'RH'
        entidade = 'PessoaFisica'
        atributo = 'foto'

        # Exemplo do valor do campo foto no banco de dados:
        # rh/pessoafisica/foto/196917.jpg
        diretorio_antigo = settings.MEDIA_ROOT + '/fotos/'

        # Tenho que usar 'self aqui porque esse atributo não foi previso na classe pai, pois a ideia do MediaCommand
        # era padronizar a estrutura de conteúdos digitais sempre desprezando o diretório antigo e criando um novo diretório.
        self.diretorio_fotos_descartadas = settings.MEDIA_ROOT + '/fotos_descartadas/'

        # A rotina abaixo foi comentada pois a parte de padronização do local das imagens (private media vs public media)
        # vai ficar pra um segundo momento.
        # diretorio_novo = settings.MEDIA_ROOT + '/rh/pessoafisica/foto/'
        diretorio_novo = settings.MEDIA_ROOT + '/fotos_new/'
        MediaCommand.__init__(self, modulo, entidade, atributo, diretorio_antigo, diretorio_novo, fazer_perguntas=False)

    def executar_procedimento(self):
        if self.SIMULACAO:
            self.terminal.add_separator()
            self.terminal.log('Iniciando SIMULAÇÃO...')
            self.terminal.add_separator()

        qs_registros_banco = PessoaFisica.objects.all()
        # qs_registros_banco = PessoaFisica.objects.filter(pk=2)
        qs_registros_banco_alvo_migracao = PessoaFisica.objects.filter(foto__isnull=False).exclude(foto="")
        # qs_registros_banco_alvo_migracao = PessoaFisica.objects.filter(pk=2)

        self.terminal.log('Registros no banco de dados do SUAP')
        self.terminal.add_separator()
        self.terminal.log('Total de registros do banco: {}'.format(
            self.get_numero_formatado_para_exibicao(qs_registros_banco.count())))
        self.terminal.log('Total de registros do banco que tem informação sobre foto: {}'.format(
            self.get_numero_formatado_para_exibicao(qs_registros_banco_alvo_migracao.count())))
        self.terminal.log(
            'Total de registros que não tem informação de foto: {}'.format(
                self.get_numero_formatado_para_exibicao(
                    (qs_registros_banco.count() - qs_registros_banco_alvo_migracao.count()))
            )
        )
        self.terminal.add_empty_line()

        registros_banco_dict_list = qs_registros_banco_alvo_migracao.values('id', 'nome', 'foto').order_by('id')
        registros_banco_set = Set()
        registros_banco_nao_existentes_em_disco_dict_list = []

        self.terminal.log('Carregando as fotos do disco...')
        # registros_disco_set = Set(FileUtils.get_file_names('/Users/misaelbarreto/Desenvolvimento/pycharm/ifrn/fontes/suap/deploy/media/rh/pessoafisica/foto'))
        registros_disco_set = Set(FileUtils.get_file_names(self.diretorio_antigo))
        registros_disco_existentes_em_banco_list = []
        registros_disco_nao_existentes_em_banco_list = []
        # self.terminal.log(registros_disco_set)
        self.terminal.log('Total de arquivos em disco (incluindo thumbs): {}'.format(
            self.get_numero_formatado_para_exibicao(len(registros_disco_set))))
        # self.terminal.log(registros_disco_set)

        # Adicionando o caminho completo da foto, para facilitar a busca em disco mais a frente.
        # self.terminal.log(registros_banco_dict_list)
        for rd in registros_banco_dict_list:
            rd['foto_caminho_completo'] = settings.MEDIA_ROOT + '/' + rd['foto']
            # self.terminal.log(rd['foto_caminho_completo'])
            registros_banco_set.add(rd['foto_caminho_completo'])
        # self.terminal.log(registros_banco_dict_list)

        # Vendos quais registros do banco não possuem o respectivo arquivo em disco.
        for rb in registros_banco_dict_list:
            if rb['foto_caminho_completo'] not in registros_disco_set:
                registros_banco_nao_existentes_em_disco_dict_list.append(rb)

        self.terminal.log(
            'Registros do banco que não possuem arquivo referente em disco: {}'.format(
                self.get_numero_formatado_para_exibicao(len(registros_banco_nao_existentes_em_disco_dict_list))
            )
        )
        self.terminal.add_separator()
        self.terminal.log(registros_banco_nao_existentes_em_disco_dict_list, show=False)
        self.terminal.add_empty_line()

        # Agora se faz o contrário, ou seja, se observa quais arquivos não são apontados no banco de dados. Isso é
        # necessário porque leva em conta os thumbs e também será uma informação de log importante.
        # self.terminal.log(registros_banco_set)
        for rd in registros_disco_set:
            # Se for um registro das mini-imagens (thumbs) geradas pelo SUAP, a busca será feita em cima da imagem
            # principal, ou seja, a que de fato é referenciada em banco.
            rd_para_pesquisa = rd.replace('/75x100/', '/').replace('/150x200/', '/')
            # self.terminal.log(rd_para_pesquisa)
            # self.terminal.log(rd)
            if rd_para_pesquisa not in registros_banco_set:
                registros_disco_nao_existentes_em_banco_list.append('{} ({})'.format(rd, FileUtils.filesize(rd)))
            else:
                registros_disco_existentes_em_banco_list.append(rd)

        self.terminal.log(
            'Registros no disco que não possuem referência em banco (incluindo thumbs): {}'.format(
                self.get_numero_formatado_para_exibicao(len(registros_disco_nao_existentes_em_banco_list))
            )
        )
        self.terminal.add_separator()
        self.terminal.log(registros_disco_nao_existentes_em_banco_list, show=False)
        self.terminal.add_empty_line()

        if (not self.fazer_perguntas) or (self.terminal.ask_yes_or_no('Deseja realmente executar a migração (daqui não tem volta)')):
            self.terminal.add_separator()
            self.terminal.add_empty_line()

            self.terminal.log('Criando coluna temporária "foto_antes_ajuste" na tabela de "pessoa_fisica" com o valor atual de foto...')
            self.terminal.log('Obs: Essa rotina só é executada uma única vez')
            if not self.SIMULACAO:
                sql_criacao_coluna_foto_antes_ajuste = """
                                                            DO
                                                            $$
                                                            BEGIN
                                                            IF not EXISTS (
                                                                            SELECT 	column_name
                                                                            FROM 	information_schema.columns
                                                                            WHERE 	table_schema='public'
                                                                                and table_name='pessoa_fisica'
                                                                                and column_name='foto_antes_ajuste'
                                                                           ) THEN
                                                                ALTER TABLE pessoa_fisica ADD COLUMN foto_antes_ajuste CHARACTER VARYING(100) DEFAULT NULL;
                                                                UPDATE pessoa_fisica SET foto_antes_ajuste = foto WHERE TRIM(COALESCE(foto, '')) <> '';
                                                            END IF;
                                                            END
                                                            $$
                                                        """
                self.execute_sql(sql_criacao_coluna_foto_antes_ajuste)

            self.terminal.log('Criando o novo diretório...')
            if not self.SIMULACAO:
                self.execute_cmd('mkdir -p ' + self.diretorio_novo)
                self.terminal.add_empty_line()
                self.terminal.log('Criando os sub-diretório dos thumbs... ')
                self.execute_cmd('mkdir -p ' + self.diretorio_novo + '75x100')
                self.execute_cmd('mkdir -p ' + self.diretorio_novo + '150x200')
            self.terminal.add_empty_line()

            self.terminal.log('Movendo os arquivos...')
            self.terminal.add_separator()
            i = 0
            for rd in registros_disco_existentes_em_banco_list:
                file_origem = rd
                file_destino = file_origem.replace(self.diretorio_antigo, self.diretorio_novo)

                if not self.SIMULACAO:
                    FileUtils.move(file_origem, file_destino)
                    # A cópia sai muito cara, muito demorada, por isso adotamos a rotina de mover os arquivos.
                    # FileUtils.copy_file(origem, destino)
                i = i + 1
                # self.terminal.log('Origem: ' +  origem)
                # self.terminal.log(self.diretorio_antigo)
                # self.terminal.log(self.diretorio_novo)
                # self.terminal.log('Destino: ' + destino)

            self.terminal.log(
                'Total dos arquivos movidos (há referência em banco): ' + self.get_numero_formatado_para_exibicao(
                    len(registros_disco_existentes_em_banco_list)))
            self.terminal.add_empty_line()

            # self.terminal.log("Ajustando a tabela 'PessoaFisica' o novo endereço das fotos...")
            # self.terminal.add_separator()
            # if not self.SIMULACAO:
            #    sql1 =  """
            #                UPDATE  pessoa_fisica
            #                SET     foto = REPLACE(foto, 'fotos/', 'rh/pessoafisica/foto/')
            #                WHERE   TRIM(COALESCE(foto, '')) <> ''
            #            """
            #    self.terminal.log('Executando o SQL: ' + sql1)
            #    self.execute_sql(sql1)
            # self.terminal.add_empty_line()

            self.terminal.log("Ajustando tabela 'PessoaFisica' com os registros que não tem fotos...")
            self.terminal.add_separator()
            if registros_banco_nao_existentes_em_disco_dict_list:
                for r in registros_banco_nao_existentes_em_disco_dict_list:
                    sql2 = "UPDATE pessoa_fisica SET foto = '' WHERE pessoa_ptr_id = {:d}".format(r['id'])
                    if not self.SIMULACAO:
                        self.execute_sql(sql2)
                    self.terminal.log('Executando o comando SQL: ' + sql2)
            else:
                self.terminal.log("Não foi necessário")

            self.terminal.add_empty_line()

            # Cucuruto = Fotos incompletas, normalmente com apenas o top da cabeça das pessoas, com tamanho médio de 4K.
            # Segundo Breno possivelmente isso foi fruto de problemas ao tentar trazer fotos do Q-Academico.
            self.terminal.log('Movendo o antigo diretório que contém os arquivos lixo (cucurutos) para ...')
            self.terminal.log(self.diretorio_fotos_descartadas)
            if not self.SIMULACAO:
                # FileUtils.delete_dir(self.diretorio_antigo)
                FileUtils.move(self.diretorio_antigo, self.diretorio_fotos_descartadas)
            self.terminal.add_empty_line()

            self.terminal.log(
                'Movendo o novo diretório para o mesmo endereço do antigo. ' 'A padronização irá ficar pra depois.')
            if not self.SIMULACAO:
                FileUtils.move(self.diretorio_novo, self.diretorio_antigo)
            self.terminal.add_empty_line()

            self.terminal.log('PROCEDIMENTO COMPLETADO COM SUCESSO!', color='green', opts=('bold',))

        arquivo_log = settings.MEDIA_ROOT + '/ajuste_midia_rh_pessoafisica_foto.log'
        self.terminal.add_empty_line()
        self.terminal.log('Salvando log da operação... ', color='yellow', opts=('bold',))
        self.terminal.save_log(arquivo_log)
        self.terminal.log('Log da operação salvo com sucesso', color='green', opts=('bold',))

    def get_numero_formatado_para_exibicao(self, numero):
        return '{:,}'.format(numero).replace(',', '.')
