# Generated by Django 3.2.5 on 2022-04-01 14:30

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('sica', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='historico',
            name='ultima_via_emitida',
            field=models.IntegerField(blank=True, default=1, null=True, verbose_name='Última Via Emitida'),
        ),
    ]