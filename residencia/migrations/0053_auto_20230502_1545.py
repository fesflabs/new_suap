# Generated by Django 3.2.5 on 2023-05-02 15:45

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0052_alter_calendarioacademico_qtd_etapas'),
    ]

    operations = [
        migrations.AlterField(
            model_name='calendarioacademico',
            name='data_fim_etapa_1',
            field=djtools.db.models.DateFieldPlus(blank=True, help_text='Data de encerramento da primeira etapa', null=True, verbose_name='Fim'),
        ),
        migrations.AlterField(
            model_name='calendarioacademico',
            name='data_inicio_etapa_1',
            field=djtools.db.models.DateFieldPlus(blank=True, help_text='Data de início da primeira etapa', null=True, verbose_name='Início'),
        ),
    ]