# Generated by Django 2.2.16 on 2021-01-26 17:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0011_merge_20201221_1533'),
    ]

    operations = [
        migrations.AddField(
            model_name='user',
            name='uuid',
            field=models.UUIDField(null=True, unique=True),
        ),
    ]