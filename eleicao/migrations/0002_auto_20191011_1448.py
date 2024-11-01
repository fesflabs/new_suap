# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-10-11 14:48
from __future__ import unicode_literals

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('edu', '0004_auto_20190920_1339'), ('eleicao', '0001_initial')]

    operations = [
        migrations.AddField(
            model_name='eleicao',
            name='alunos_relacionados_eleicao',
            field=djtools.db.models.ManyToManyFieldPlus(blank=True, related_name='alunos_relacionados_eleicao', to='edu.Aluno', verbose_name='Alunos Relacionadas à Eleição'),
        ),
        migrations.AlterField(
            model_name='eleicao',
            name='pessoas_relacionadas_eleicao',
            field=djtools.db.models.ManyToManyFieldPlus(
                blank=True, related_name='pessoas_relacionadas_eleicao', to='rh.Servidor', verbose_name='Servidores Relacionados à Eleição'
            ),
        ),
    ]
