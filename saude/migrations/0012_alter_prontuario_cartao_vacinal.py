# Generated by Django 3.2.5 on 2021-12-23 15:17

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('saude', '0011_auto_20210719_1644'),
    ]

    operations = [
        migrations.AlterField(
            model_name='prontuario',
            name='cartao_vacinal',
            field=djtools.db.models.FileFieldPlus(max_length=255, null=True, upload_to='saude/prontuario', verbose_name='Cartão Vacinal'),
        ),
    ]