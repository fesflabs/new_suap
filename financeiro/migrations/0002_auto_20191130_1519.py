# Generated by Django 2.2.7 on 2019-11-30 15:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('financeiro', '0001_initial')]

    operations = [
        migrations.AlterField(model_name='evento', name='nome', field=models.CharField(max_length=50, verbose_name='Nome')),
        migrations.AlterField(model_name='notadotacao', name='observacao', field=models.TextField(verbose_name='Observação')),
    ]