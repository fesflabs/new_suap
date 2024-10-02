# -*- coding: utf-8 -*-
import argparse
import email
import os
import zipfile
from datetime import date, timedelta, datetime
from imaplib import IMAP4_SSL

from comum.models import Configuracao
from djtools.management.commands import BaseCommandPlus
from tesouro_gerencial.importador import ImportadorNotaCredito, ImportadorExecNE, ImportadorRAP, ImportadorGRU


class Command(BaseCommandPlus):
    def add_arguments(self, parser):
        def validar_data(s):
            try:
                return datetime.strptime(s, "%d/%m/%Y")
            except ValueError:
                msg = "Data inválida: '{0}'.".format(s)
                raise argparse.ArgumentTypeError(msg)

        parser.add_argument('--data', '-d', dest='data', action='store', type=validar_data, help='Data da mensagem de email que deve ser importada - formato DD/MM/AAAA')

    def handle(self, *args, **options):
        verbosity = int(options.get('verbosity', 1)) >= 1 and 1 or 0
        download_folder = "/tmp"

        data_email = options.get('data')

        def decode_header(header_string):
            try:
                decoded_seq = email.header.decode_header(header_string)
                return str(email.header.make_header(decoded_seq))
            except Exception:  # fallback: return as is
                return header_string

        # connect to the imap server
        servidor_email = Configuracao.get_valor_por_chave(app='tesouro_gerencial', chave='servidor_email')
        login_email = Configuracao.get_valor_por_chave(app='tesouro_gerencial', chave='email')
        senha_email = Configuracao.get_valor_por_chave(app='tesouro_gerencial', chave='senha_email')

        mail = IMAP4_SSL(servidor_email)
        mail.login(login_email, senha_email)
        try:
            mail.select('INBOX', readonly=True)
            if data_email:
                data_de = data_email.strftime("%d-%b-%Y")
                data_ate = (data_email + timedelta(1)).strftime("%d-%b-%Y")
                typ, [msg_ids] = mail.search(None, '(SENTSINCE {0} SENTBEFORE {1})'.format(data_de, data_ate), '(FROM lista-cdsdw@serpro.gov.br)')
            else:
                data = (date.today() - timedelta(1)).strftime("%d-%b-%Y")  # se rodar no final do dia
                typ, [msg_ids] = mail.search(None, '(SENTSINCE {0})'.format(data), '(FROM lista-cdsdw@serpro.gov.br)')

            # get complete email messages in RFC822 format
            for num in msg_ids.split():
                typ, msg_data = mail.fetch(num, '(RFC822)')
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        att_path = "No attachment found."
                        for part in msg.walk():
                            if part.get_content_maintype() == 'multipart':
                                continue
                            if part.get('Content-Disposition') is None:
                                continue

                            filename = decode_header(part.get_filename())
                            att_path = os.path.join(download_folder, filename)
                            if not os.path.isfile(att_path):
                                fp = open(att_path, 'wb')
                                fp.write(part.get_payload(decode=True))
                                fp.close()

                        zip_file = open(att_path, 'rb')
                        zipfile.ZipFile(zip_file).extractall(download_folder)
                        zip_file.close()
                        os.remove(zip_file.name)
                        print()
                        for header in ['subject', 'to', 'from', 'date']:
                            print('{:8}: {}'.format(header.upper(), decode_header(msg[header])))

                        print('{:8}: {}'.format('ANEXO', att_path))

        finally:
            try:
                mail.close()
            finally:
                mail.logout()

        def get_arquivos_por_nome(arquivos, parte_nome):
            return [arquivo for arquivo in arquivos if parte_nome in arquivo.name]

        arquivos_csv = []
        for arquivo in os.scandir(download_folder):
            if os.path.splitext(arquivo)[1] == '.csv':
                arquivos_csv.append(arquivo)

        prefixos_arquivo_importador = {
            'Movimentações de crédito': ImportadorNotaCredito,
            'Exec NE Emitido, Liquidado e Pago': ImportadorExecNE,
            'RAP PROC N PROC INSCRITOS': ImportadorRAP,
            'ARRECADAÇÃO POR GRU': ImportadorGRU,
        }

        for prefixo_arquivo in prefixos_arquivo_importador.keys():
            arquivos = get_arquivos_por_nome(arquivos_csv, prefixo_arquivo)
            ClasseImportador = prefixos_arquivo_importador[prefixo_arquivo]
            importador = ClasseImportador(arquivos=arquivos, tipo_log=verbosity, encoding='utf-16')
            importador.run()
            for arquivo in arquivos:
                os.remove(arquivo)
