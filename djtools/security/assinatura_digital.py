# -*- coding: utf-8 -*-
import base64
import os
import tempfile
from PyPDF2 import PdfFileWriter, PdfFileReader
from io import StringIO
from reportlab.pdfgen import canvas
from os import path
from subprocess import Popen, PIPE, STDOUT
from os.path import abspath, dirname

CAMINHO_SELO = abspath(dirname(__file__)) + '/selo-opaco.png'

"""
    Classe responsável por inserir um selo de autenticidade nos arquivos PDF.
    Além do selo, é possível também adicionar uma string que pode ser utilizada para identificar
    o arquivo em uma base de dados ou sistema de arquivos.
"""


class Carimbo:
    def __init__(self, caminho_selo=CAMINHO_SELO):
        self.caminho_selo = caminho_selo

    """
        Adicionar o selo cujo caminho está definido na constante CAMINHO_ARQUIVO_SELO no arquivo PDF.
        caminho_arquivo: string contendo a localização do arquivo no sistema de arquivos
        identificador: string opcional contendo um identificador para o aquivo que está sendo carimbado
    """

    def carimbar(self, caminho_arquivo, identificador):
        caminho_arquivo_temporario = caminho_arquivo + '.pdf'
        os.rename(caminho_arquivo, caminho_arquivo_temporario)
        arquivo = PdfFileReader(open(caminho_arquivo_temporario, "rb"))
        output = PdfFileWriter()
        pagina0 = arquivo.getPage(0)
        output.addPage(pagina0)

        buffer = StringIO()
        p = canvas.Canvas(buffer)
        p.drawString(10, 10, identificador)
        p.drawImage(self.caminho_selo, 520, 750, 50, 50, mask='auto')
        p.showPage()
        p.save()
        pdf = buffer.getvalue()
        buffer.close()
        # f = tempfile.NamedTemporaryFile(delete=False)
        f = open(tempfile.mktemp(), 'wb')
        f.write(pdf)
        f.close()

        selo = PdfFileReader(open(f.name, "rb"))
        pagina0.mergePage(selo.getPage(0))
        for i in range(1, arquivo.getNumPages()):
            output.addPage(arquivo.getPage(i))
        outputStream = open(caminho_arquivo, "wb")
        output.write(outputStream)
        outputStream.close()
        os.remove(f.name)


"""
    Classe responsável por encriptar/decriptar arquivos
"""


class Cifrador:
    """
        Criptografa o arquivo passado como parâmetro com uma determinada senha
            caminho_arquivo: string contendo a localização do arquivo no sistema de arquivos
            senha: string contendo uma senha que será requerida no processo de decriptografia
    """

    def encriptar(self, caminho_arquivo, senha):
        if not path.isfile(caminho_arquivo):
            raise Exception('O arquivo a ser encriptado é inválido ou não existe')
        cmd = 'openssl enc -aes-256-cbc -salt -in "%s" -out "%s" -pass pass:%s' % (caminho_arquivo, caminho_arquivo + '.tmp', senha)
        out = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True).stdout
        out.read()
        os.rename(caminho_arquivo + '.tmp', caminho_arquivo)

    """
        Decriptografa o arquivo passado como parâmetro com uma determinada senha (deve ser a mesma usada no processo de criptografia)
            caminho_arquivo: string contendo a localização do arquivo no sistema de arquivos
            senha: string contendo a mesma senha utilizada no processo de criptografia
    """

    def decriptar(self, caminho_arquivo, senha):
        if not path.isfile(caminho_arquivo):
            raise Exception('O arquivo a ser decriptado é inválido ou não existe')
        cmd = 'openssl enc -d -aes-256-cbc -in "%s" -out "%s" -pass pass:%s' % (caminho_arquivo, caminho_arquivo + '.tmp', senha)
        out = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True).stdout
        out.read()
        os.rename(caminho_arquivo + '.tmp', caminho_arquivo)


"""
    Classe responsável por calcular a assinatura/hash dos arquivos enviados para o servidor e verificar sua autenticidade.
    Diferente dos arquivos armazenados através do padrão XMLSec, os arquivos assinados/verificados por esta classes podem
    ser armazenados em uma base de dados ou qualquer outro mecanismo que possa armazenar tanto o arquivo binário quanto sua
    assinatura.
"""


class CertificadorBD:
    """
        Calcula o hash de um determinando arquivo presente do disco rígido. Utiliza o algorítmo sha256
            caminho_arquivo: string contendo o caminho do arquivo cujo hash será calculado
    """

    def calcular_hash(self, caminho_arquivo):
        if not path.isfile(caminho_arquivo):
            raise Exception('O arquivo cujo hash deseja-se calcular é inválido ou não existe')
        cmd1 = 'openssl dgst -sha256 < "%s"' % (caminho_arquivo)
        out1 = Popen(cmd1, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True).stdout
        hash = out1.read()
        if hash.startswith('(stdin)= '):
            return hash[9:]  # compatibilidade com MAC OS
        else:
            return hash

    """
        Calcula e retorna a assinatura de um arquivo presente no disco rígido baseado na chave privada.
        A senha deve ser fornecida caso a chave privada seja projetida.
            caminho_arquivo_chave_priv: string contendo o caminho do arquivo da chave privada
            senha: senha utilizada no processo de criação da chave. Caso nenhuma senha tenha sido utilizada, o valor desse parâmetro é ignorado
            caminho_arquivo: string contendo o caminho do arquivo cuja assinatura será extraída
    """

    def calcular_assinatura(self, caminho_arquivo_chave_priv, senha, caminho_arquivo):
        if not path.isfile(caminho_arquivo_chave_priv):
            raise Exception('O arquivo contendo a chave privada é inválido ou não existe')
        if not path.isfile(caminho_arquivo):
            raise Exception('O arquivo a ser assinado é inválido ou não existe')
        hash = self.calcular_hash(caminho_arquivo)
        # arq_hash = tempfile.NamedTemporaryFile(delete=False)
        arq_hash = open(tempfile.mktemp(), 'wb')
        arq_hash.write(hash)
        arq_hash.close()
        cmd2 = 'openssl rsautl -sign -inkey "%s" -keyform PEM -in "%s" -passin pass:%s' % (caminho_arquivo_chave_priv, arq_hash.name, senha)
        out2 = Popen(cmd2, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True).stdout
        retorno = out2.read()
        if retorno.find('unable') != -1:
            os.remove(arq_hash.name)
            raise Exception(retorno)
        os.remove(arq_hash.name)
        return base64.b64encode(retorno)

    """
        Verifica a autenticidade e integridade de um arquivo presente no disco rígido baseado na assinatura previamente calculada
        e na chave pública associada à chave privada utilizada no processo de assinatura
            caminho_arquivo_chave_pub: string contendo o caminho do arquivo da chave publica
            assinatura_64: string contendo a assinatura do arquivo codificado no formato base64
            caminho_arquivo: string contendo o caminho do arquivo cuja verificação será realizada
            return: True se o arquivo for autêntico, False caso contrário
    """

    def verificar(self, caminho_arquivo_chave_pub, assinatura_64, caminho_arquivo):
        if not path.isfile(caminho_arquivo_chave_pub):
            raise Exception('O arquivo contendo a chave pública é inválido ou não existe')
        if not path.isfile(caminho_arquivo):
            raise Exception('O arquivo a ser verificado é inválido ou não existe')
        # arq_assinatura = tempfile.NamedTemporaryFile(delete=False)
        arq_assinatura = open(tempfile.mktemp(), 'wb')
        try:
            arq_assinatura.write(base64.b64decode(assinatura_64))
        except Exception:
            arq_assinatura.close()
            os.remove(arq_assinatura.name)
            return False
        arq_assinatura.close()
        cmd2 = 'openssl rsautl -verify -inkey "%s" -keyform PEM -pubin -in "%s"' % (caminho_arquivo_chave_pub, arq_assinatura.name)
        out2 = Popen(cmd2, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True).stdout
        verificacao = out2.read()
        os.remove(arq_assinatura.name)
        hash = self.calcular_hash(caminho_arquivo)
        return verificacao == hash

    """
        Verifica a autenticidade e integridade de um arquivo presente no disco rígido baseado na assinatura previamente calculada
        e no certificado (formato PEM) associado à chave privada utilizada no processo de assinatura
            caminho_arquivo_certificado: string contendo o caminho do arquivo do certificado (formato PEM)
            assinatura_64: string contendo a assinatura do arquivo codificado no formato base64
            caminho_arquivo: string contendo o caminho do arquivo cuja verificação será realizada
            return: True se o arquivo for autêntico, False caso contrário
    """

    def verificar_com_certificado(self, caminho_certificado, assinatura_64, caminho_arquivo):
        if not path.isfile(caminho_certificado):
            raise Exception('O arquivo de certificado é inválido ou não existe')
        if not path.isfile(caminho_arquivo):
            raise Exception('O arquivo a ser verificado é inválido ou não existe')
        cmd1 = 'openssl x509 -inform pem -in "%s" -pubkey -noout' % caminho_certificado
        out1 = Popen(cmd1, shell=True, stdin=PIPE, stdout=PIPE, stderr=STDOUT, close_fds=True).stdout
        conteudo = out1.read()
        # arq_chave_pub = tempfile.NamedTemporaryFile(delete=False)
        arq_chave_pub = open(tempfile.mktemp(), 'wb')
        arq_chave_pub.write(conteudo)
        arq_chave_pub.close()
        autentico = self.verificar(arq_chave_pub.name, assinatura_64, caminho_arquivo)
        os.remove(arq_chave_pub.name)
        return autentico
