# Generated by Django 2.2.16 on 2021-03-23 18:13

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('contratos', '0015_auto_20210309_1346'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tipofiscal',
            name='pode_gerenciar_todas_medicoes_contrato',
            field=models.BooleanField(default=False, verbose_name='Fiscal pode gerenciar medições de outros fiscais?'),
        ),
    ]