# -*- coding: utf-8 -*-
from django.db.models.deletion import Collector
from django.core import serializers
from djtools.management.commands import BaseCommandPlus
import pdb


def dump(qs):
    lista = []
    c = []
    collector = Collector('default')
    collector.collect(qs)
    for instances in collector.data.values():
        for instance in instances:
            if instance.__class__.__name__ not in ['Log', 'RegistroDiferenca'] and instance not in lista:
                lista.append(instance)
                if instance.__class__.__name__ not in c:
                    c.append(instance.__class__.__name__)
    for qs in collector.fast_deletes:
        for instance in qs:
            if instance.__class__.__name__ not in ['Log', 'RegistroDiferenca'] and instance not in lista:
                lista.append(instance)
                if instance.__class__.__name__ not in c:
                    c.append(instance.__class__.__name__)
    return c, lista


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        queryset = None
        print(
            '\nPor favor, instancie o queryset que você deseja salvar e em seguida digite a tecla "c".\nÉ necessário importar os modelos necessários.\n\tEx: from edu.models import Aluno\n\tqueryset = Aluno.objects.filter(ano_letivo__ano=2015)\n\n'
        )
        pdb.set_trace()
        c, lista = dump(queryset)
        print(
            (
                'Um arquivo "backup.json" foi salvo no diretório corrente contendo %s objetos. Para restaurá-los, digite o seguinte comando:\n\n\tpython manage.py restore %s < backup.json\n\nÉ necessário ordenar as classes corretamente de acordo com as dependências entre elas.\n\n'
                % (len(lista), ' '.join(c))
            )
        )
        f = open('backup.json', 'w')
        f.write(serializers.serialize("json", lista))
        f.close()
