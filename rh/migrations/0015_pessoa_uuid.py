# Generated by Django 2.2.16 on 2021-01-26 17:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0014_auto_20200516_0227'),
    ]

    operations = [
        migrations.AddField(
            model_name='pessoa',
            name='uuid',
            field=models.UUIDField(null=True, unique=True),
        ),
    ]
