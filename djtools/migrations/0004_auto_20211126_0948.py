# Generated by Django 3.2.5 on 2021-11-26 09:48

from django.db import migrations
from django.contrib.auth.models import Permission


def migrate(apps, schema):
    Permission.objects.filter(codename__startswith='view_').delete()


def unmigrate(apps, schema):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ('djtools', '0003_twofactorauthenticationcode'),
    ]

    operations = [
        migrations.RunPython(migrate, unmigrate)
    ]
