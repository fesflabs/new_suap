# Generated by Django 2.2.16 on 2021-05-18 14:34

import django.db.models.deletion
from django.db import migrations, models

import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0019_auto_20210512_1917'),
        ('licenca_capacitacao', '0009_auto_20210513_1904'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServidorComplementar',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('categoria', models.CharField(choices=[['docente', 'Docente'], ['tecnico_administrativo', 'Técnico-Administrativo']], default='tecnico_administrativo', max_length=30)),
                ('data_cadastro', djtools.db.models.DateTimeFieldPlus(auto_now_add=True, verbose_name='Data de cadastro')),
                ('justificativa', models.TextField(verbose_name='Justificativa')),
                ('edital', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='licenca_capacitacao.EditalLicCapacitacao', verbose_name='Edital')),
                ('servidor', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.Servidor', verbose_name='Servidor')),
            ],
            options={
                'verbose_name': 'Servidor Complementar',
                'verbose_name_plural': 'Servidores Complementares',
            },
        ),
    ]