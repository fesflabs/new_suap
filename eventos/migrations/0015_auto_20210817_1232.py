# Generated by Django 3.1 on 2021-08-17 12:32

import django.db.models.deletion
from django.db import migrations, models

import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0014_auto_20210817_0941'),
    ]

    operations = [
        migrations.AddField(
            model_name='classificacaoevento',
            name='detalhamento',
            field=models.TextField(blank=True, null=True, verbose_name='Detalhamento'),
        ),
        migrations.RemoveField(
            model_name='evento',
            name='tipo',
        ),
        migrations.AddField(
            model_name='evento',
            name='tipo',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='eventos.tipoevento', verbose_name='Tipo'),
        ),
        migrations.AlterField(
            model_name='subtipoevento',
            name='detalhamento',
            field=models.TextField(verbose_name='Descrição'),
        )
    ]