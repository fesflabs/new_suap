# Generated by Django 3.2.5 on 2021-12-15 12:18

from django.db import migrations, models
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0037_merge_20211211_0909'),
    ]

    operations = [
        migrations.AlterField(
            model_name='device',
            name='friendly_name',
            field=models.TextField(db_index=True, verbose_name='Dispositivo'),
        ),
        migrations.AlterField(
            model_name='device',
            name='nickname',
            field=djtools.db.models.CharFieldPlus(blank=True, db_index=True, max_length=255, null=True, verbose_name='Apelido'),
        ),
        migrations.AlterField(
            model_name='device',
            name='user_agent',
            field=models.TextField(db_index=True, verbose_name='Agente do Dispositivo'),
        ),
        migrations.AlterField(
            model_name='sessioninfo',
            name='ip_address',
            field=models.TextField(db_index=True, verbose_name='Endereço IP'),
        ),
    ]
