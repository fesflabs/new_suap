# Generated by Django 2.2.16 on 2021-04-23 16:45

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0017_auto_20210126_1840'),
    ]

    operations = [
        migrations.CreateModel(
            name='ServidorReativacaoTemporaria',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_inicio', models.DateField(null=False, verbose_name='Data de Início')),
                ('data_fim', models.DateField(null=False, verbose_name='Data de Fim')),
                ('servidor', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.Servidor', verbose_name='Servidor')),
            ],
            options={
                'verbose_name': 'Reativação Temporária de Servidor',
                'verbose_name_plural': 'Reativações Temporárias dos Servidores',
            },
        ),
    ]