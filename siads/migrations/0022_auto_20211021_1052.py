# Generated by Django 3.2.5 on 2021-10-21 10:52

from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0025_auto_20210920_0912'),
        ('comum', '0031_forcar_habilitacao'),
        ('siads', '0021_alter_setorsiads_uo'),
    ]

    operations = [
        migrations.AddField(
            model_name='setorsiads',
            name='sala',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.sala'),
        ),
        migrations.AlterField(
            model_name='setorsiads',
            name='setor_suap',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.setor'),
        ),
    ]
