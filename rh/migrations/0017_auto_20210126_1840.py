# Generated by Django 2.2.16 on 2021-01-26 18:40

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0016_auto_20210126_1742'),
    ]

    operations = [
        migrations.AlterField(
            model_name='pessoa',
            name='uuid',
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]
