# -*- coding: utf-8 -*-
from django.core.files.storage import default_storage

from djtools.management.commands import BaseCommandPlus
from comum.models import RegistroEmissaoDocumento
import datetime


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        qs = RegistroEmissaoDocumento.objects.filter(data_validade__lt=datetime.datetime.today()).exclude(documento='')
        for registro in qs:
            if default_storage.exists(registro.documento.name):
                default_storage.delete(registro.documento.name)
                print(('Arquivo {} apagado'.format(registro.documento.name)))
            else:
                print(('Arquivo {} inexistente'.format(registro.documento.name)))
        qs.update(documento='')
