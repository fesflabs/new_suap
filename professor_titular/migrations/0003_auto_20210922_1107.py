# Generated by Django 3.2.5 on 2021-09-22 11:07

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('professor_titular', '0002_auto_20210922_1000'),
    ]

    operations = [
        migrations.AddField(
            model_name='validacaocppd',
            name='formulario_pontuacao_status',
            field=models.IntegerField(null=True, verbose_name='Situação do Formulário de Pontuação'),
        ),
        migrations.AddField(
            model_name='validacaocppd',
            name='relatorio_descritivo_status',
            field=models.IntegerField(null=True, verbose_name='Situação do Relatório Descritivo'),
        ),
    ]
