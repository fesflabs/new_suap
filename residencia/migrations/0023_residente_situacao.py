# Generated by Django 3.2.5 on 2022-12-11 18:35

from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0022_log_ref_diario'),
    ]

    operations = [
        migrations.AddField(
            model_name='residente',
            name='situacao',
            field=djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='residencia.situacaomatricula', verbose_name='Situação'),
        ),
    ]
