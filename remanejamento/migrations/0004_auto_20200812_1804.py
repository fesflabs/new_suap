# Generated by Django 2.2.10 on 2020-08-12 18:04

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('remanejamento', '0003_auto_20200812_1749'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='editalrecurso',
            name='pessoa',
        ),
        migrations.RemoveField(
            model_name='inscricao',
            name='pessoa',
        ),
    ]