# -*- coding: utf-8 -*-

from datetime import datetime
from django.conf import settings
from djtools.management.commands import BaseCommandPlus
import os


class Command(BaseCommandPlus):
    def handle(self, *args, **options):

        pg_dump = ['pg_dump']
        if getattr(settings, 'DATABASE_USER'):
            pg_dump.append('--username=%s' % settings.DATABASE_USER)
        if getattr(settings, 'DATABASE_HOST'):
            pg_dump.append('--host=%s' % settings.DATABASE_HOST)
        if getattr(settings, 'DATABASE_PORT'):
            pg_dump.append('--port=%s' % settings.DATABASE_PORT)
        pg_dump.append(settings.DATABASE_NAME)
        pg_dump = ' '.join(pg_dump)

        now = datetime.now()
        backup_name = '%s_%s.sql' % (settings.DATABASE_NAME, now.strftime('%Y%m%d_%H%M%S'))
        backup_name = os.path.join(settings.PROJECT_ROOT, backup_name)

        print(('%s > %s' % (pg_dump, backup_name)))
        os.system('%s > %s' % (pg_dump, backup_name))
