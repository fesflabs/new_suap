# Generated by Django 3.2.5 on 2023-01-13 15:59

from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0025_auto_20230113_1258'),
    ]

    operations = [
        migrations.AlterField(
            model_name='frequenciaresidente',
            name='diario',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='matriculadiario_frequencia_residente_set', to='residencia.matriculadiario', verbose_name='Diário'),
        ),
    ]