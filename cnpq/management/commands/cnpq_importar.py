"""
Comando que extrai os curriculos lattes
"""
import datetime
import io
import os
import re
import sys
import time
import zipfile
import os.path
from urllib.error import URLError

from django.core.mail import mail_admins
from django.core.management import CommandError

from django.db import transaction
from django.utils import termcolors
from sentry_sdk import capture_exception
from suds.client import Client


from cnpq.xml_parsers import CurriculoVittaeLattesParser
from djtools.management.commands import BaseCommandPlus
from djtools.utils import b64decode, b64encode
from rh.models import Servidor
from django.conf import settings
from comum.models import Configuracao


class EmptyResponse(Exception):
    pass


class Command(BaseCommandPlus):
    help = 'Executa os testes do SUAP'

    def add_arguments(self, parser):
        parser.add_argument('--file', '-f', dest='file', action='store', default=[], help='Arquivo zip contendo o currículo lattes em formato xml baixado da plataforma lattes.')

        parser.add_argument('--matricula', '-m', dest='matricula', action='store', default=[], help='Matricula.')

        parser.add_argument('--forcar', action='store_true', dest='forcar', default=False, help='Forçar a importação de todos.')

        parser.add_argument('--xml', dest='xml', action='store_true', default=False, help='Importa e salva os XML.')

    def handle(self, *args, **options):
        # Servidor: Ricardo Alexsandro de Medeiros Valentim (1488270)
        # usar ./manage.py cnpq_importar --forcar -m=1488270 -f=/Users/jailtonpaiva/Downloads/3181772060208133.zip
        servidores = None
        forcar = options.get('forcar', False)
        nome_arquivo = options.get('file', None)
        matricula = options.get('matricula', None)
        origem_chamada = options.get('origem_view', None)
        xml = options.get('xml', None)
        verbosity = options.get('verbosity', 3)

        if matricula:
            servidores = Servidor.objects.filter(matricula=matricula)
        if nome_arquivo:
            if os.path.isfile(nome_arquivo):
                file_name, file_extension = os.path.splitext(nome_arquivo)
                identificador_cnpq = file_name.split('/')[-1]
                curriculo_str = self.get_arquivo_xml(nome_arquivo, 'curriculo')
                data_atualizacao = None
                curriculo_lattes = CurriculoVittaeLattesParser(curriculo_str, data_atualizacao, identificador_cnpq, forcar)
                if servidores:
                    curriculo_lattes.parse(servidores[0])
                    if hasattr(servidores[0].get_vinculo(), 'vinculo_curriculo_lattes'):
                        from cnpq.views import atualizar_grupos_pesquisa
                        atualizar_grupos_pesquisa(servidores[0].get_vinculo().vinculo_curriculo_lattes)
                    self.stdout.write(self.style.SUCCESS('Currículo de {} importado com sucesso.'.format(servidores[0].nome)))
                    return
            else:
                raise CommandError('Arquivo {} não encontrado.'.format(nome_arquivo))

        if not servidores and not nome_arquivo:
            servidores = Servidor.objects.filter(excluido=False)

        total = servidores.count()

        count_extraidos = 0
        count_novos = 0
        count_atualizados = 0
        count_erros = 0
        count = 0
        count1_exceptions = 0
        count2_exceptions = 0
        exceptions = dict()
        for servidor in servidores:
            time.sleep(1)
            count += 1
            porcentagem = int(float(count) / total * 100)

            if verbosity:
                sys.stdout.write(termcolors.make_style(fg='cyan', opts=('bold',))('\r[{}] {}% - Extraindo {} de {}'.format('#' * int(porcentagem / 10), porcentagem, count, total)))
                sys.stdout.flush()

            identificador_cnpq = ''

            try:
                identificador_cnpq = self.get_identificador(servidor.cpf)
            except Exception as e:
                count_erros += 1
                exceptions[servidor] = e
                continue

            if identificador_cnpq is None:
                count_erros += 1
                continue

            novo = False

            data_atualizacao = None

            sid = transaction.savepoint()

            tipo_acao = 0

            try:
                data_atualizacao_str = self.get_data_atualizacao(identificador_cnpq)

                if data_atualizacao_str != 'None':
                    data_atualizacao = datetime.datetime.strptime(data_atualizacao_str, "%d/%m/%Y %H:%M:%S")
                curriculo_str = None
                if hasattr(servidor.get_vinculo(), 'vinculo_curriculo_lattes'):
                    if xml:
                        curriculo_str = self.get_curriculo(identificador_cnpq)
                    data_ultima_extracao = servidor.get_vinculo().vinculo_curriculo_lattes.data_extracao

                    if data_ultima_extracao:
                        if data_atualizacao >= data_ultima_extracao or forcar:
                            tipo_acao = 1
                else:
                    novo = True
                    tipo_acao = 2

                if tipo_acao == 0:
                    continue

                count_extraidos += 1

                if tipo_acao == 1 and hasattr(servidor.get_vinculo(), 'vinculo_curriculo_lattes'):
                    servidor.get_vinculo().vinculo_curriculo_lattes.delete()
                if not curriculo_str:
                    curriculo_str = self.get_curriculo(identificador_cnpq)
                curriculo_str = b64decode(curriculo_str)

                curriculo_lattes = CurriculoVittaeLattesParser(curriculo_str, data_atualizacao, identificador_cnpq, forcar)

                executou_parse = curriculo_lattes.parse(servidor)

                if executou_parse:
                    curriculo_atualizado = servidor.get_vinculo().vinculo_curriculo_lattes
                    curriculo_atualizado.data_extracao = datetime.datetime.now()
                    curriculo_atualizado.save()
                    from cnpq.views import atualizar_grupos_pesquisa
                    atualizar_grupos_pesquisa(curriculo_atualizado)

                    if novo:
                        count_novos += 1
                    else:
                        count_atualizados += 1
                    transaction.savepoint_commit(sid)
                    transaction.commit()
                else:
                    transaction.savepoint_rollback(sid)
            except (URLError, EmptyResponse) as e:
                transaction.savepoint_rollback(sid)
                exceptions[servidor] = e
                count1_exceptions += 1
            except Exception as e:
                transaction.savepoint_rollback(sid)
                exceptions[servidor] = e
                count2_exceptions += 1
                capture_exception(e)

        mensagem = '\n\t ERROS '

        for servidor in exceptions:
            mensagem += '\n{} => {}'.format(servidor, exceptions.get(servidor))

        mensagem += '\n\n'
        mensagem += '\n{} \t TOTAL '.format(total)
        mensagem += '\n{} \t Extraidos '.format(count_extraidos)
        mensagem += '\n{} \t Novos '.format(count_novos)
        mensagem += '\n{} \t Atualizados '.format(count_atualizados)
        mensagem += '\n{} \t Servidores sem curriculo/ligação com o {} '.format(count_erros, Configuracao.get_valor_por_chave('comum', 'instituicao_sigla'))

        mensagem += '\n{} \t Exceções t1 '.format(count1_exceptions)
        mensagem += '\n{} \t Exceções t2 '.format(count2_exceptions)

        # se tiver alguma exeção
        if count1_exceptions or count2_exceptions:
            mail_admins('[SUAP] Importação do CNPQ', mensagem)

        if origem_chamada:
            return count1_exceptions + count2_exceptions + count_erros
        return mensagem

    def getClient(self):
        URL = 'http://servicosweb.cnpq.br/srvcurriculo/WSCurriculo?wsdl'
        client = Client(URL)
        client.set_options(location='http://servicosweb.cnpq.br/srvcurriculo/WSCurriculo')
        return client

    def get_identificador(self, cpf):
        cpf = re.sub(r'\D', '', cpf)  # retira tudo que nao eh digito
        resposta = self.getClient().service.getIdentificadorCNPq(cpf, '', '')
        if not resposta:
            raise EmptyResponse()
        if '<MENSAGEM><ERRO>' in str(resposta):
            raise CommandError('Erro {}'.format(resposta))
        return '{}'.format(resposta)

    def get_data_atualizacao(self, identificador):
        resposta = self.getClient().service.getDataAtualizacaoCV(identificador)
        if not resposta:
            raise EmptyResponse()
        if '<MENSAGEM><ERRO>' in str(resposta):
            raise CommandError('Erro {}'.format(resposta))
        return str(resposta)

    def get_curriculo(self, identificador):
        # salvando arquivo zip em memoria
        resposta = self.getClient().service.getCurriculoCompactado(identificador)
        if not resposta:
            raise EmptyResponse()
        arquivo_zip = io.BytesIO()
        arquivo_zip.write(b64decode(resposta.encode('utf8')))
        arquivo_zip.getvalue()
        if '_ERRO.xml' in str(arquivo_zip.getvalue()):
            raise CommandError('Erro {}'.format(arquivo_zip.getvalue()))
        curriculo = self.get_arquivo_xml(arquivo_zip, identificador)
        arquivo_zip.close()
        return b64encode(curriculo)

    def get_arquivo_xml(self, filepath, identificador):
        # extraindo o conteudo do arquivo dentro do zip
        nome_xml = '{}.xml'.format(identificador)
        arquivo_zip = zipfile.ZipFile(filepath, 'r')
        curriculo = arquivo_zip.read(nome_xml)
        arquivo_zip.close()
        pasta = os.path.join(settings.TEMP_DIR, 'curriculos/')
        if not os.path.exists(pasta):
            os.makedirs(pasta)
        with open('{}{}'.format(pasta, nome_xml), "wb") as f:  # use `wb` mode
            f.write(curriculo)
        return curriculo
