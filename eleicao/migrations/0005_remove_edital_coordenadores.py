# Generated by Django 2.2.16 on 2021-02-22 10:50

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('eleicao', '0004_auto_20210222_1025'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='edital',
            name='coordenadores',
        ),
    ]