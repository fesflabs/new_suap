# Generated by Django 3.2.5 on 2021-12-03 16:27

from django.db import migrations


def ajuste_setor_sala(apps, schema_editor):
    SetorSiads = apps.get_model('siads', 'SetorSiads')

    for setor in SetorSiads.objects.all():
        if setor.sala is not None:
            setor.tipo = 'SALA'
            setor.save()


class Migration(migrations.Migration):

    dependencies = [
        ('siads', '0024_setorsiads_tipo'),
    ]

    operations = [
        migrations.RunPython(ajuste_setor_sala)
    ]