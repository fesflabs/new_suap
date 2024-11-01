# Generated by Django 2.2.16 on 2020-12-07 15:19

import django.contrib.postgres.fields.jsonb
from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo_provedor_servico', '0042_servicogerenteequipelocal'),
    ]

    operations = [
        migrations.CreateModel(
            name='RegistroNotificacaoGovBR',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('response_content', django.contrib.postgres.fields.jsonb.JSONField(null=True)),
                ('data_criacao', djtools.db.models.DateTimeFieldPlus(auto_now_add=True, verbose_name='Data de Criação')),
                ('solicitacao', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='catalogo_provedor_servico.Solicitacao')),
            ],
            options={
                'verbose_name': 'Registro de Notificação Enviada pela Plataforma Notifica',
                'verbose_name_plural': 'Registros de Notificações Enviadas pela Plataforma Notifica',
            },
        ),
    ]
