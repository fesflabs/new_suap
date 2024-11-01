# Generated by Django 3.2.5 on 2022-11-28 07:16

from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0013_alter_residente_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='residente',
            name='curso_campus',
            field=djtools.db.models.ForeignKeyPlus(default=None, on_delete=django.db.models.deletion.CASCADE, to='residencia.cursoresidencia', verbose_name='Curso', null=True, blank=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='residente',
            name='matriz',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='residencia.matriz', verbose_name='Matriz'),
        ),
    ]
