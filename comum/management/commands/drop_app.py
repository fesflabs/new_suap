# -*- coding: utf-8 -*-

"""
Comando que remove todas as tables, views, sequences e index de uma aplicacao.
"""

from djtools.management.commands import BaseCommandPlus
from django.utils import termcolors
from django.db import connection


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        if args:
            cursor = connection.cursor()
            try:
                app = args[0] + '_%%'
                sql = """SELECT c.relname as name
                                FROM pg_catalog.pg_class c
                                LEFT JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                                WHERE n.nspname NOT IN ('pg_catalog', 'pg_toast')
                                AND c.relkind = 'r'
                                AND pg_catalog.pg_table_is_visible(c.oid)
                                AND c.relname like '{}';""".format(
                    app
                )
                cursor.execute(sql)

                for row in cursor.fetchall():
                    cursor.execute("drop table {} cascade".format(row))
                    connection._commit()
                    print((termcolors.make_style(fg='cyan', opts=('bold',))('{} removed'.format(row))))

                print((termcolors.make_style(fg='yellow', opts=('bold',))('{} removed'.format(args[0]))))
            except Exception as e:
                connection._rollback()
                print((termcolors.make_style(fg='cyan', opts=('bold',))('Error: {}'.format(e))))
        else:
            print((termcolors.make_style(fg='cyan', opts=('bold',))('Error: app not informed')))
