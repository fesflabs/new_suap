# Generated by Django 2.2.16 on 2021-02-24 17:21

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('compras', '0002_auto_20200312_1321'),
    ]

    operations = [
        migrations.CreateModel(
            name='Calendario',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=1000, verbose_name='Descrição')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Calendário',
                'verbose_name_plural': 'Calendários',
            },
        ),
        migrations.CreateModel(
            name='TipoEvento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=1000, verbose_name='Descrição')),
                ('cor', djtools.db.models.CharFieldPlus(choices=[('alert', 'Amarelo'), ('info', 'Azul'), ('extra', 'Laranja'), ('extra2', 'Roxo'), ('success', 'Verde'), ('error', 'Vermelho'), ('nenhum', 'Nenhum')], help_text='Informe uma cor para o tipo de evento', max_length=255, verbose_name='Cor')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('calendario', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='compras.Calendario', verbose_name='Calendário')),
            ],
            options={
                'verbose_name': 'Tipo de Evento',
                'verbose_name_plural': 'Tipos de Evento',
            },
        ),
        migrations.CreateModel(
            name='Evento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_inicio', djtools.db.models.DateFieldPlus(verbose_name='Data de Início')),
                ('data_fim', djtools.db.models.DateFieldPlus(verbose_name='Data de Fim')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('tipo_evento', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='compras.TipoEvento', verbose_name='Tipo de Evento')),
            ],
            options={
                'verbose_name': 'Evento',
                'verbose_name_plural': 'Eventos',
            },
        ),
    ]
