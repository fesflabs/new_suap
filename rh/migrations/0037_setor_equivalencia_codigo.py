# Generated by Django 3.2.5 on 2022-06-01 09:37

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0036_auto_20220405_2129'),
    ]

    operations = [
        migrations.AddField(
            model_name='setor',
            name='equivalencia_codigo',
            field=models.CharField(blank=True, help_text='Código do setor SIAPE que é equivalente a este setor SUAP.', max_length=9, null=True, unique=True, verbose_name='Código de Equivalência'),
        ),
    ]
