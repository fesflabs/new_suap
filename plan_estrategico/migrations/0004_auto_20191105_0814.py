# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-11-05 08:14
from __future__ import unicode_literals

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [('plan_estrategico', '0003_auto_20191031_1056')]

    operations = [
        migrations.AlterModelOptions(name='variavel', options={'ordering': ('sigla',), 'verbose_name': 'Variável', 'verbose_name_plural': 'Variáveis'}),
        migrations.AlterModelOptions(
            name='variavelcampus', options={'ordering': ('variavel__sigla',), 'verbose_name': 'Variável Campus/Ano', 'verbose_name_plural': 'Variáveis Campus/Ano'}
        ),
    ]