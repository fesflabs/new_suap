# Generated by Django 3.2.5 on 2022-07-19 17:30

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0038_auto_20220610_0752'),
        ('comum', '0043_notificacaosistema_objeto_relacionado'),
    ]

    operations = [
        migrations.CreateModel(
            name='ContatoEmergencia',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome_contato', djtools.db.models.CharFieldPlus(max_length=200, verbose_name='Nome do Contato')),
                ('telefone', djtools.db.models.BrTelefoneField(max_length=15, verbose_name='Telefone')),
                ('pessoa_fisica', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.pessoafisica', verbose_name='Servidor')),
            ],
            options={
                'verbose_name': 'Contato de Emergência',
                'verbose_name_plural': 'Contatos de Emergência',
            },
        ),
    ]