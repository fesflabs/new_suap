# Generated by Django 3.2.5 on 2022-02-04 16:54

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('ponto', '0006_alter_maquina_ativo'),
    ]

    operations = [
        migrations.AlterField(
            model_name='abonochefia',
            name='data',
            field=djtools.db.models.DateFieldPlus(),
        ),
        migrations.AlterField(
            model_name='afastamento',
            name='data_fim',
            field=djtools.db.models.DateFieldPlus(db_index=True, null=True, verbose_name='Data Final'),
        ),
        migrations.AlterField(
            model_name='afastamento',
            name='data_ini',
            field=djtools.db.models.DateFieldPlus(db_index=True, verbose_name='Data Inicial'),
        ),
        migrations.AlterField(
            model_name='documentoanexo',
            name='data',
            field=djtools.db.models.DateFieldPlus(db_index=True),
        ),
        migrations.AlterField(
            model_name='liberacao',
            name='data_fim',
            field=djtools.db.models.DateFieldPlus(db_index=True, null=True, verbose_name='Data Fim'),
        ),
        migrations.AlterField(
            model_name='liberacao',
            name='data_inicio',
            field=djtools.db.models.DateFieldPlus(db_index=True, verbose_name='Data Início'),
        ),
        migrations.AlterField(
            model_name='observacao',
            name='data',
            field=djtools.db.models.DateFieldPlus(db_index=True, verbose_name='Data da Frequência'),
        ),
        migrations.AlterField(
            model_name='recessoopcaoescolhida',
            name='data_escolha',
            field=djtools.db.models.DateFieldPlus(auto_now_add=True, verbose_name='Data da Escolha'),
        ),
    ]