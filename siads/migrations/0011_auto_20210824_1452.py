# Generated by Django 3.2.5 on 2021-08-24 14:52

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0023_servidorfuncaohistorico_atualiza_pelo_extrator'),
        ('siads', '0010_auto_20210824_1132'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='materialconsumo',
            name='uo',
        ),
        migrations.AddField(
            model_name='grupomaterialpermanente',
            name='uo',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.unidadeorganizacional'),
        ),
        migrations.AlterField(
            model_name='materialconsumo',
            name='nome_processado',
            field=models.CharField(max_length=1024, null=True, verbose_name='Nome Processado'),
        ),
    ]