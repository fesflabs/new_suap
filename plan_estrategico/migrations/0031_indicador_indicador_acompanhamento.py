# Generated by Django 2.2.16 on 2021-02-10 15:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plan_estrategico', '0030_variaveltrimestralcampus'),
    ]

    operations = [
        migrations.AddField(
            model_name='indicador',
            name='indicador_acompanhamento',
            field=models.BooleanField(default=False, verbose_name='Indicador de acompanhamento?'),
        ),
    ]