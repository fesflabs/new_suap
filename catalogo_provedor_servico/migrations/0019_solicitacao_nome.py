# Generated by Django 2.2.10 on 2020-05-18 17:14

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('catalogo_provedor_servico', '0018_auto_20200518_1649')]

    operations = [
        migrations.AddField(
            model_name='solicitacao', name='nome', field=djtools.db.models.CharFieldPlus(default='', max_length=255, verbose_name='Solicitante'), preserve_default=False
        )
    ]
