# Generated by Django 3.2.5 on 2023-03-24 12:39

from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0049_auto_20230324_1239'),
        ('comum', '0053_merge_20220929_2218'),
    ]

    operations = [
        migrations.AlterField(
            model_name='Vinculo',
            name='pessoa',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.pessoa', verbose_name='Pessoa'),
        ),
        migrations.AlterField(
            model_name='PessoaEndereco',
            name='pessoa',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.pessoa'),
        ),
        migrations.AlterField(
            model_name='PessoaTelefone',
            name='pessoa',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.pessoa'),
        ),
        migrations.AlterField(
            model_name='ContatoEmergencia',
            name='pessoa_fisica',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.pessoafisica', verbose_name='Servidor'),
        ),
        migrations.AlterField(
            model_name='PrestadorServico',
            name='pessoa_fisica',
            field=djtools.db.models.ForeignKeyPlus(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='prestadores', to='rh.pessoafisica'),
        ),
        migrations.AlterField(
            model_name='OcupacaoPrestador',
            name='prestador',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='comum.prestadorservico'),
        ),
    ]