# Generated by Django 3.2.5 on 2021-09-15 09:43

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('progressoes', '0002_avaliacaomodelo_tipo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='avaliacaocriterionota',
            name='nota',
            field=models.FloatField(),
        ),
    ]
