# Generated by Django 3.2.5 on 2023-04-25 10:12

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0050_rename_unidade_arendizagem_componentecurricular_unidade_aprendizagem'),
    ]

    operations = [
        migrations.AlterField(
            model_name='residente',
            name='tipo_zona_residencial',
            field=djtools.db.models.CharFieldPlus(blank=True, choices=[['1', 'Urbana'], ['2', 'Rural']], max_length=255, null=True, verbose_name='Zona Residencial'),
        ),
        migrations.AlterField(
            model_name='solicitacaoresidente',
            name='tipo_zona_residencial',
            field=djtools.db.models.CharFieldPlus(blank=True, choices=[['1', 'Urbana'], ['2', 'Rural']], max_length=255, null=True, verbose_name='Zona Residencial'),
        ),
    ]