# Generated by Django 2.2.16 on 2021-02-19 08:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('enquete', '0004_auto_20200214_1051'),
    ]

    operations = [
        migrations.AlterField(
            model_name='resposta',
            name='data_cadastro',
            field=models.DateTimeField(verbose_name='Data'),
        ),
    ]
