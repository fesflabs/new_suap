# -*- coding: utf-8 -*-

# Servidor de impressão que deverá rodar no cliente para que o comprovante seja impresso
# Para finalizar o processo, digite CTRL + C
#
# Se for necessario mudar o IP do servidor SUAP crie um arquivo chamado suap.cfg com o seguinte conteúdo
# [config]
# suap=10.22.0.241
# porta=COM1
#
# Para gerar o EXE instale o py2exe, crie um arquivo chamado setup.py com o seguinte conteúdo:
# from distutils.core import setup
# import py2exe
# setup(console=['impressora.py'])
#
# Gerando o exe:
# python setup.py py2exe
#
# O py2exe só pode ser gerado no Windows
#
# Para configurar a velocidade da porta da impressora:
# mode COM1 9600,n,8,1

import socket
import configparser
import datetime
import os

try:
    config = configparser.RawConfigParser()
    config.read('suap.cfg')
    ip_suap = config.get('config', 'suap')
    porta = config.get('config', 'porta')
except Exception:
    ip_suap = '10.22.0.241'
    porta = 'COM1'


print("Servidor de Impressao do SUAP")
print("-----------------------------")
print(("Servidor SUAP autorizado: ", ip_suap))
print("\n")

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.bind(('0.0.0.0', 9999))

print("Servidor de impressao iniciado. Aguardando conexoes...")

while True:
    try:
        s.listen(1)
        conn, addr = s.accept()

        while True:
            # IP que está conectando é o IP do SUAP?
            if addr[0] != ip_suap:
                print(("ALERTA: Conexao negada para o IP ", addr[0]))
                break

            data = conn.recv(1024)

            if not data:
                break

            print(("[%s] Imprimindo na porta %s... " % (datetime.datetime.now(), porta)))
            f = open('imp.txt', 'w')
            f.write('%s\n' % data)  # python will convert \n to os.linesep
            f.close()  # you can omit in most cases as the destructor will call if

            os.system('type imp.txt > %s' % porta)

        conn.close()

    except Exception:
        s.close()
