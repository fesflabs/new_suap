# Generated by Django 3.2.5 on 2022-02-19 17:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('labfisico', '0002_auto_20220217_0847'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='guacamoleconnection',
            unique_together={('hostname', 'domain'), ('connection_name', 'connection_group')},
        ),
    ]
