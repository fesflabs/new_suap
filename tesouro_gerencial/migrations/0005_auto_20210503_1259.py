# Generated by Django 2.2.16 on 2021-05-03 12:59

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('tesouro_gerencial', '0004_auto_20200326_1403'),
    ]

    operations = [
        migrations.AlterField(
            model_name='gru',
            name='codigo',
            field=djtools.db.models.CharFieldPlus(max_length=10, verbose_name='Código'),
        ),
    ]
