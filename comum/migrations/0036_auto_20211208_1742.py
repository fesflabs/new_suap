# Generated by Django 3.2.5 on 2021-12-08 17:42

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0035_auto_20211208_1651'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='device',
            unique_together={('user', 'user_agent')},
        ),
        migrations.RemoveField(
            model_name='device',
            name='ip_address',
        ),
    ]
