# Generated by Django 2.2.10 on 2020-05-18 20:14

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('catalogo_provedor_servico', '0019_solicitacao_nome')]

    operations = [
        migrations.RemoveField(model_name='servico', name='entra_campo'),
        migrations.RemoveField(model_name='servico', name='extra_label'),
        migrations.AddField(model_name='servico', name='extra_campo', field=djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Campo extra a apresentar')),
    ]
