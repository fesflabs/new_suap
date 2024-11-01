# Generated by Django 2.2.7 on 2019-11-25 10:36

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('comum', '0004_auto_20191009_1509')]

    operations = [
        migrations.AlterField(
            model_name='areaatuacao',
            name='icone',
            field=djtools.db.models.CharFieldPlus(
                blank=True, default='list', help_text='Informe um ícone para representar esta Área de Atuação. Fonte: https://fontawesome.com/', max_length=80, verbose_name='Ícone'
            ),
        )
    ]
