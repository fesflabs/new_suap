# Generated by Django 3.1 on 2021-08-23 10:40

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0017_auto_20210823_0850'),
    ]

    operations = [
        migrations.AddField(
            model_name='subtipoevento',
            name='multiplas_atividades',
            field=models.BooleanField(default=False, verbose_name='Múltiplas Atividades'),
        ),
    ]