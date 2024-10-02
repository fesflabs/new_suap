import gzip
import logging
import os
import tempfile
import time
import zipfile
from operator import itemgetter

from django.apps.registry import apps
from django.conf import settings
from django.core.files.storage import default_storage
from django.db import transaction

from djtools.storages import cache_file

log = logging.getLogger(__name__)

Log = apps.get_model('comum', 'log')


def descompactar_arquivos(pasta, destino=None, tipo='.gz'):
    """
    Descompacta todos os arquivos .zip ou .gz da pasta remota passada como parâmetro
    if not os.path.exists(settings.TEMP_DIR):
            os.makedirs(settings.TEMP_DIR)
    """
    if not destino:
        destino = pasta

    if tipo == '.zip':
        nova_pasta_local = pasta
    else:
        nova_pasta_local = settings.TEMP_DIR + '/' + pasta

    arquivos = [i for i in default_storage.listdir(nova_pasta_local)[1] if i.endswith(tipo)]
    for arquivo in arquivos:
        cache_file(pasta + '/' + arquivo)

    pasta_local = settings.TEMP_DIR + '/' + pasta

    if tipo == '.zip':
        for zp in arquivos:
            f = open(pasta_local + '/' + zp, 'rb')
            zipfile.ZipFile(f).extractall(pasta_local)
            f.close()
    else:
        for gz in arquivos:
            f = gzip.open(pasta_local + '/' + gz, 'rb')
            file_content = f.read()
            f.close()
            f = open(destino + '/' + gz[:-3], 'wb')
            f.write(file_content)
            f.close()


def identificar_layout(nome_arquivo_ref, pasta):
    """
    Identifica a qual tipo de arquivo de dados se refere o arquivo de referencia (parametro nome_arquivo_ref)
    Os modelos estarão na pasta passada como parametro com a extensão .ref, o retorno será o nome do arquivo sem a extensão.
    Isso é necessário por que o nome do arquivo não o identifica.
    """
    arquivo = open(nome_arquivo_ref)
    conteudo = arquivo.read()
    arquivo.close()

    pasta = pasta
    for arquivo_nome_ref in [i for i in os.listdir(pasta) if i.endswith('.REF')]:
        arquivo_ref = open(pasta + '/' + arquivo_nome_ref)
        conteudo_ref = arquivo_ref.read()
        arquivo_ref.close()

        # A identificação é feita comparando-se o conteúdo dos arquivo
        # Essa sequencia de replace() é necessário porque alguns arquivos veem com tabs/espaços/etc a mais ou a menos
        if conteudo.strip().replace('\n', '').replace('\t', '').replace('\r', '').replace(' ', '') == conteudo_ref.strip().replace('\n', '').replace('\t', '').replace(
            '\r', ''
        ).replace(' ', ''):
            log.debug(f'identifiquei {arquivo_nome_ref} no arquivo {nome_arquivo_ref}')
            return arquivo_nome_ref.replace('.REF', '')

    log.info(
        'Arquivo {} está fora dos padrões esperados. \n \
              Verifique se o arquivo está correto ou se o layout não foi alterado.'.format(
            nome_arquivo_ref
        )
    )
    return None


def formatar_ref(arquivo_ref):
    """
    Faz a conversão de um arquivo de referencia para uma lista de dicionários.
    As chaves do dicionários serão ser:
        - descricao: nome do campo
        - tipo: tipo do campo
        - tamanho: tamanho tal qual está no arquivo de referencia (ex: 0012 ou 12,2)
        - tamanho_int: tamanho realmente ocupado pelo campo (ex: 12,2 => 14)
        - inicio: posicao inicial do campo
        - fim: posicao final do campo
    >>> print 'Não sei pq estes testes não estão sendo executados...'
    >>> conteudo = ['GR-MATRICULA                            N 0012',
                    'IT-NO-SERVIDOR                          A 0060']
    >>> ref = formatar_ref(conteudo)
    >>> matricula = ref[0]
    >>> matricula['descricao']
    'GR-MATRICULA'
    >>> matricula['tipo']
    'N'
    >>> matricula['tamanho']
    '0012'
    >>> matricula['tamanho_int']
    12
    >>> matricula['inicio']
    0
    >>> matricula['fim']
    12 - isso vai falhar qd for executado
    """
    campos = []
    posicao = 1
    for i in arquivo_ref:
        descricao, tipo, tamanho = i.split()
        tamanho_int = sum(int(n) for n in tamanho.split(','))
        inicio = posicao - 1
        fim = inicio + tamanho_int
        campos.append(dict(descricao=descricao, tipo=tipo, tamanho=tamanho, tamanho_int=tamanho_int, inicio=inicio, fim=fim))  # i[41:], # tamanho puro ## Pq não somente tamanho?
        posicao = posicao + tamanho_int
    return campos


def txt_to_dict(ref, txt):
    """
    Faz a conversão de uma linha de dados em um dicionario
    """
    item = dict()
    for campo in ref:
        valor = txt[campo['inicio']: campo['fim']].strip()
        if not valor.replace('0', ''):
            valor = None
        item[campo['descricao']] = valor
    return item


def get_itens(ref_filename, txt_filename, order_by=None):
    """
    Faz a conversão do arquivo txt para um lista de dicionario
    """
    itens = []
    if os.path.isfile(ref_filename) and os.path.isfile(txt_filename):
        with open(ref_filename) as arquivo_ref:
            ref_linhas = arquivo_ref.readlines()

        with open(txt_filename, encoding='utf-8') as arquivo_txt:
            txt_linhas = arquivo_txt.readlines()

        ref = formatar_ref(ref_linhas)

        for linha in txt_linhas:
            item = dict()
            linha = linha.strip()
            for campo in ref:
                valor = linha[campo['inicio']: campo['fim']].strip()
                item[campo['descricao']] = valor
            itens.append(item)

        if order_by:
            itens = sorted(itens, key=itemgetter(order_by))

    return itens


class Importador:
    """
    Importador genérico de dados oriundos de arquivos com colunas de tamanho fixo
    """

    class Meta:
        abstract = True

    def __init__(self, ordem=[], local_arquivos=None, local_refs=None, destino_arquivos=None, log_level='INFO'):
        self.ordem = ordem
        self.pasta = local_arquivos
        self.pasta_txt = destino_arquivos
        self.local_refs = local_refs
        self.layout_arquivo = dict()
        log.setLevel(level=logging.getLevelName(log_level))

    def descompactar_arquivos_manuais(self):
        self._temp_dir = tempfile.mkdtemp(dir=settings.TEMP_DIR)
        descompactar_arquivos(self.pasta, self._temp_dir, '.zip')

    def _verificar_arquivos(self):
        arquivos = self.get_arquivos()
        if arquivos:
            return True
        return False

    def get_arquivos(self):
        pasta_local = settings.TEMP_DIR + '/' + self.pasta
        if default_storage.exists(pasta_local):
            return [i for i in default_storage.listdir(pasta_local)[1] if i.endswith('.gz')]
        return []

    def _prepare(self):
        """
        Prepara as coisas, por exemplo, define os layout de arquivos.

        Importadores concretos deverão definir os parâmetros de execução
            Os parâmetros necessários são:
            - ordem de execução (nome dos arquivos de referência sem a extensão .ref);
            - pasta onde estão os arquivos
        """
        if not os.path.exists(settings.TEMP_DIR):
            os.makedirs(settings.TEMP_DIR)
        self._temp_dir = tempfile.mkdtemp(dir=settings.TEMP_DIR)
        local_refs = self.local_refs

        # FIXME (?): Acho que isso não está no lugar certo. :-/
        descompactar_arquivos(self.pasta, self._temp_dir)
        for arquivo_nome in [i for i in os.listdir(self._temp_dir) if i.endswith('.REF')]:
            nome_arquivo_ref = self._temp_dir + '/' + arquivo_nome
            nome_arquivo_txt = self._temp_dir + '/' + arquivo_nome.replace('.REF', '.TXT')
            if self.layout_arquivo.get(identificar_layout(nome_arquivo_ref, local_refs)):
                self.layout_arquivo[identificar_layout(nome_arquivo_ref, local_refs)].append([nome_arquivo_ref, nome_arquivo_txt])
            else:
                self.layout_arquivo[identificar_layout(nome_arquivo_ref, local_refs)] = [[nome_arquivo_ref, nome_arquivo_txt]]

    def _process(self):
        for layout in self.ordem:
            if self.layout_arquivo.get(layout):
                self.processar_arquivo(layout, self.layout_arquivo[layout])

    def _get_map_layout_functions(self):
        """
        Returna um dicionario que mapeia os layout e suas funcoes de processamento

        As subsclasses deverão implementar esse métodos.
        Será algo do tipo:
            layouts = dict(
                       municipio         = importar_municipios,
                       credor            = importar_credores,
            )
            return layouts
        """
        raise NotImplementedError()

    def processar_arquivo(self, layout, arquivos):
        if layout is None:
            return
        for arquivo in arquivos:
            layouts = self._get_map_layout_functions()

            funcao = layouts.get(layout, None)

            log.info('>>> Processando <{}> ... {}'.format(funcao.__name__, arquivo[1].split('/')[-1]))
            itens = get_itens(arquivo[0], arquivo[1])
            inicio = time.time()
            try:
                funcao(itens)
            except Exception as e:
                mensagem_log = [f'{arquivo[0]}: {str(e)}']
                mlog = Log(titulo='Importação de arquivos', texto='ERRO no arquivo' + ''.join(mensagem_log))
                with transaction.atomic():
                    mlog.save()
                e.message = mensagem_log
                raise e
            fim = time.time()
            log.info(f'>>> Finalizado <{funcao.__name__}> em {fim - inicio}...')

    def _clear(self):
        """
        Faz a remoção de arquivos que tenham sido criados durante o processo,
        ou qualquer outra coisa que precise ser liberada
        """
        import shutil

        shutil.rmtree(self._temp_dir)
        log.debug('apagando diretorio temporário')

        # apagando arquivos na pasta de upload padrão
        path_upload = self.pasta + '/'
        arquivos = [i for i in default_storage.listdir(path_upload)[1] if i.endswith('.gz') or i.endswith('.zip')]
        for f in arquivos:
            default_storage.delete(path_upload + f)

        # apagando pasta de extração (tmp)
        path_tmp_extracao = settings.TEMP_DIR + '/' + path_upload
        if default_storage.exists(path_tmp_extracao):
            arquivos_extracao = [i for i in default_storage.listdir(path_tmp_extracao)[1]]
            for f in arquivos_extracao:
                default_storage.delete(path_tmp_extracao + f)
            default_storage.delete(path_tmp_extracao)

        # apagando tmp
        path_tmp = self._temp_dir
        if default_storage.exists(path_tmp):
            arquivos_tmp = [i for i in default_storage.listdir(path_tmp)[1]]
            for f in arquivos_tmp:
                default_storage.delete(path_tmp + f)
            default_storage.delete(path_tmp)

        log.debug(f'apagando todos os arquivos com extensão .gz e .zip do diretório {self.pasta}')

    def run(self):
        """
        Faz a execução da importação.
        Antes deste metodo ser executado é necessário que a pasta e a ordem dos arquivos tenham sidos especificados,
        também é necessário que os arquivos de dados tenham a extensão .TXT e os de referência .REF
        """

        if not self.pasta:
            raise PastaArquivosException('Você precisa definir a pasta onde estão os arquivos')

        if not self.local_refs:
            raise PastaArquivosRefException('Você precisa definir a pasta onde estão os arquivos de referência')

        if not self.ordem:
            raise OrdemArquivosException('Você precisa definir a ordem de importação dos arquivos')

        self._prepare()

        self._process()

        self._clear()


class PastaArquivosException(Exception):
    pass


class PastaArquivosRefException(Exception):
    pass


class OrdemArquivosException(Exception):
    pass
