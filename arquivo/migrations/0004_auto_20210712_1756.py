# Generated by Django 2.2.24 on 2021-07-12 17:56

import arquivo.models
from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('arquivo', '0003_auto_20210309_2004'),
    ]

    operations = [
        migrations.AlterField(
            model_name='arquivo',
            name='file',
            field=djtools.db.models.FileFieldPlus(upload_to=arquivo.models.file_upload_to),
        ),
    ]
