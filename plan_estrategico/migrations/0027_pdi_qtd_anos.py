# Generated by Django 2.2.10 on 2020-09-16 09:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('plan_estrategico', '0026_auto_20200825_1348'),
    ]

    operations = [
        migrations.AddField(
            model_name='pdi',
            name='qtd_anos',
            field=models.IntegerField(null=True, verbose_name='Duração em anos'),
        ),
    ]