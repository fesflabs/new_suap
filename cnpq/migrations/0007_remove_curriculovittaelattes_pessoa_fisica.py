# Generated by Django 3.2.5 on 2022-05-30 14:03

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('cnpq', '0006_alter_curriculovittaelattes_data_extracao'),
    ]

    state_operations = [
        migrations.RemoveField(
            model_name='curriculovittaelattes',
            name='pessoa_fisica',
        ),
    ]

    operations = [
        migrations.SeparateDatabaseAndState(
            state_operations=state_operations
        )
    ]
