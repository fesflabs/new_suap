# Generated by Django 2.2.7 on 2020-01-21 08:58

from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('rh', '0004_auto_20191127_1640'), ('contratos', '0004_popular_arquivo_contrato_20191203_1721')]

    operations = [
        migrations.AddField(
            model_name='contrato',
            name='pessoa_contratada',
            field=djtools.db.models.ForeignKeyPlus(
                null=True, on_delete=django.db.models.deletion.CASCADE, related_name='pessoacontratada_set', to='rh.Pessoa', verbose_name='Pessoa Contratada'
            ),
        )
    ]