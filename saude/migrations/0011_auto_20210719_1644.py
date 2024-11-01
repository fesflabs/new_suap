# Generated by Django 3.2.5 on 2021-07-19 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('saude', '0010_auto_20210629_1308'),
    ]

    operations = [
        migrations.AlterField(
            model_name='anamnese',
            name='gravida',
            field=models.BooleanField(null=True, verbose_name='Grávida?'),
        ),
        migrations.AlterField(
            model_name='cartaovacinal',
            name='sem_data',
            field=models.BooleanField(default=None, null=True, verbose_name='Desconhece data de vacinação'),
        ),
    ]
