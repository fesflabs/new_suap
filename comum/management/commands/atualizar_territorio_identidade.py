# -*- coding: utf-8 -*-
from django.core.files.storage import default_storage

from djtools.management.commands import BaseCommandPlus
from comum.models import RegistroEmissaoDocumento, TerritorioIdentidade, Municipio
import datetime

from djtools.utils import to_ascii


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        Municipio.objects.filter(pk=1).update(nome='Salvador-')
        qs_m = Municipio.objects.all()
        for m in qs_m:
            m.save()


        qs = TerritorioIdentidade.objects.all()
        for territorioidentidade in qs:
            for cidade in territorioidentidade.lista_cidades.replace('.','').replace('-','').split(','):
                nome_cidade = (f'{to_ascii(cidade)}-BA').replace(' ', '').upper()
                municipio = Municipio.objects.filter(identificacao=nome_cidade)
                if municipio.exists():
                    if len(municipio)>1:
                        print(f'{municipio} - achou 2')
                    else:
                        print(f'{municipio} - {territorioidentidade.nome}')
                        municipio[0].territorio_identidade = territorioidentidade
                        municipio[0].save()
                else:
                    print(f'{nome_cidade} - não achou')





