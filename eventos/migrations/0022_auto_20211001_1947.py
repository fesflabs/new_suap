# Generated by Django 3.2.5 on 2021-10-01 19:47

import json

from django.db import migrations


def migrate(apps, editor):
    Evento = apps.get_model('eventos.Evento')
    lista = json.loads(open('/tmp/eventos.json').read())
    for pk, tipo_id in lista:
        Evento.objects.filter(pk=pk).update(tipo_id=tipo_id)
    Evento.objects.filter(tipo_id=3).update(tipo_id=4)
    Evento.objects.filter(tipo_id=3).delete()


def unmigrate(apps, editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0021_auto_20210914_0646'),
    ]

    operations = [
        migrations.RunPython(migrate, unmigrate)
    ]