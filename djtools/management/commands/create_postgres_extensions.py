# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from django.db import connection


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        print('Criando extensões do postgres')
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")
            cursor.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")
            cursor.execute("""CREATE OR REPLACE FUNCTION f_unaccent(text) RETURNS text AS
                    $func$
                    SELECT unaccent('unaccent', upper($1))
                    $func$  LANGUAGE sql IMMUTABLE SET search_path = public, pg_temp;
            """)
