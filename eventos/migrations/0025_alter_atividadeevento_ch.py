# Generated by Django 3.2.5 on 2021-12-21 16:08

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0024_auto_20211206_1137'),
    ]

    operations = [
        migrations.AlterField(
            model_name='atividadeevento',
            name='ch',
            field=models.IntegerField(verbose_name='Carga-Horária em segundos'),
        ),
    ]