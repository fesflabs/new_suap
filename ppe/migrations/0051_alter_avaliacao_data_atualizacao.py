# Generated by Django 3.2.5 on 2023-03-24 13:26

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0050_avaliacao_data_atualizacao'),
    ]

    operations = [
        migrations.AlterField(
            model_name='avaliacao',
            name='data_atualizacao',
            field=djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data de Atualização'),
        ),
    ]