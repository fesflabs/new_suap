# Generated by Django 3.2.5 on 2021-12-07 07:49

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0032_alter_ocupacaoprestador_empresa'),
    ]

    operations = [
        migrations.AddField(
            model_name='groupdetail',
            name='app_manager',
            field=djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='App Manager'),
        ),
    ]
