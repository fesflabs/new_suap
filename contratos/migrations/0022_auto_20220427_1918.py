# Generated by Django 3.2.5 on 2022-04-27 19:18

from django.db import migrations, models
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('contratos', '0021_auto_20220426_1529'),
    ]

    operations = [
        migrations.AddField(
            model_name='contrato',
            name='exige_garantia_contratual',
            field=models.BooleanField(default=False, verbose_name=' Possui exigência de garantia contratual?'),
        ),
        migrations.AddField(
            model_name='garantia',
            name='data_inicio',
            field=djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data de Início'),
        ),
        migrations.AlterField(
            model_name='garantia',
            name='tipo',
            field=djtools.db.models.CharFieldPlus(choices=[['SEGURO', 'Seguro Garantia'], ['FIANCA', 'Fiança'], ['CAUCAO', 'Caução'], ['SIAFI', 'Registro Garantia no SIAFI']], max_length=20, verbose_name='Tipo de Garantia'),
        ),
    ]