# Generated by Django 2.2.7 on 2020-01-23 11:13

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('rh', '0004_auto_20191127_1640')]

    operations = [
        migrations.AlterModelOptions(
            name='cargahorariareduzida', options={'verbose_name': 'Processo de Alteração de Carga Horária', 'verbose_name_plural': 'Processos de Alteração de Carga Horária'}
        ),
        migrations.AlterField(model_name='cargahorariareduzida', name='data_inicio', field=djtools.db.models.DateFieldPlus(null=True, verbose_name='Início da Alteração')),
        migrations.AlterField(model_name='cargahorariareduzida', name='data_termino', field=djtools.db.models.DateFieldPlus(null=True, verbose_name='Término da Alteração')),
    ]