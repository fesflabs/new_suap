# Generated by Django 3.2.5 on 2022-07-27 10:45

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0044_merge_20220705_1111'),
        ('convenios', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='convenio',
            name='vinculos_conveniadas',
            field=models.ManyToManyField(to='comum.Vinculo', verbose_name='Conveniadas'),
        ),
        migrations.AddField(
            model_name='profissionalliberal',
            name='vinculo_pessoa',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, verbose_name='Pessoa', to='comum.vinculo'),
        ),
        migrations.AlterField(
            model_name='profissionalliberal',
            name='pessoa',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE,
                                                   to='rh.pessoa'),
        ),
    ]