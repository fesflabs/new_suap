# Generated by Django 2.2.10 on 2020-04-27 12:09

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [('cpa', '0001_initial')]

    operations = [
        migrations.AlterField(
            model_name='questionario', name='publico', field=models.IntegerField(choices=[[0, 'Geral'], [1, 'Alunos'], [2, 'Técnicos'], [3, 'Docentes']], verbose_name='Público')
        )
    ]