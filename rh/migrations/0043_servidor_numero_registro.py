# Generated by Django 3.2.5 on 2022-09-29 16:17

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0042_merge_20220929_0741'),
    ]

    operations = [
        migrations.AddField(
            model_name='servidor',
            name='numero_registro',
            field=djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Número de Registro no Conselho Profissional'),
        ),
    ]