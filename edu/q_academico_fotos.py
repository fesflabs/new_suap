# -*- coding: utf-8 -*-

from sys import stdout

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage

from edu.models import Aluno


class DAO:
    def __init__(self):
        self.connection = None

    def get_connection(self):
        """Conexão com SQL Server"""
        import pymssql

        if self.connection is None:
            self.connection = pymssql.connect(
                host=settings.ACADEMICO['DATABASE_HOST'],
                user=settings.ACADEMICO['DATABASE_USER'],
                password=settings.ACADEMICO['DATABASE_PASSWORD'],
                database='SISTEMA_ACADEMICO_BINARIOS',
                as_dict=True,
            )
        return self.connection

    def get_fotos_qtd(self):
        sql = "SELECT count(*) as c FROM FW_CONTEUDOS_BINARIOS WHERE tipo_conteudo_binario = 0"
        cursor = self.get_connection().cursor()
        cursor.execute(sql)
        qtd = cursor.fetchone()['c']
        cursor.close()
        return qtd

    def atualizar_fotos(self, codigo_academico_pf=None, verbose=0):
        sql = """
        SELECT cod_conteudo_binario, conteudo_binario 
        FROM FW_CONTEUDOS_BINARIOS 
        WHERE tipo_conteudo_binario = 0
        """
        if codigo_academico_pf:
            sql += ' AND cod_conteudo_binario = {}'.format(codigo_academico_pf)
        fotos_qtd = self.get_fotos_qtd()
        percentual = 0
        contador = 1
        importados = 0

        cursor = self.get_connection().cursor()
        cursor.execute(sql)

        row = cursor.fetchone()
        while row:
            foto = {'codigo': row['cod_conteudo_binario'], 'conteudo': row['conteudo_binario']}

            for aluno in Aluno.objects.filter(codigo_academico_pf=foto['codigo']):
                if not aluno.foto.name:
                    try:
                        aluno.foto.save('{}.jpg'.format(aluno.pk), ContentFile(foto['conteudo']))
                        importados += 1
                    except Exception:
                        print(('[FAIL] {}'.format(aluno.matricula)))
                        default_storage.delete(aluno.foto.name)
                        aluno.foto = ''
                        aluno.save()

            if verbose:
                percentual_atual = '{:.0f}'.format(contador / float(fotos_qtd) * 100)
                if percentual_atual != percentual:
                    percentual = percentual_atual
                    stdout.write("Importando fotos: {}%%\r".format(percentual))
                    stdout.flush()

            contador += 1

            row = cursor.fetchone()

        cursor.close()

        return importados
