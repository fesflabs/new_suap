# Generated by Django 3.2.5 on 2021-09-23 12:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('siads', '0013_alter_setorsiads_chefe'),
    ]

    operations = [
        migrations.AddField(
            model_name='setorsiads',
            name='exportavel',
            field=models.BooleanField(default=True, verbose_name='Exportávek'),
        ),
    ]
