# Generated by Django 2.2.16 on 2021-03-01 17:09

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('materiais', '0002_auto_20200414_1330'),
    ]

    operations = [
        migrations.AlterField(
            model_name='materialcotacao',
            name='arquivo',
            field=djtools.db.models.FileFieldPlus(blank=True, null=True, upload_to='materiais/cotacao/'),
        ),
    ]
