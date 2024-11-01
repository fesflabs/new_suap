# Generated by Django 2.2.10 on 2020-04-30 14:40

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0006_auto_20200402_1132'),
    ]

    operations = [
        migrations.AddField(
            model_name='evento',
            name='hora_fim_inscricoes',
            field=djtools.db.models.TimeFieldPlus(blank=True, null=True, verbose_name='Hora de Fim das Inscrições'),
        ),
        migrations.AddField(
            model_name='evento',
            name='hora_inicio_inscricoes',
            field=djtools.db.models.TimeFieldPlus(null=True, verbose_name='Hora de Início das Inscrições'),
        ),
    ]
