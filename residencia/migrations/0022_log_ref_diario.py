# Generated by Django 3.2.5 on 2022-12-11 18:28

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0021_auto_20221211_1819'),
    ]

    operations = [
        migrations.AddField(
            model_name='log',
            name='ref_diario',
            field=models.IntegerField(db_index=True, null=True),
        ),
    ]
