# Generated by Django 3.2.5 on 2023-03-24 12:39

from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0049_auto_20230324_1239'),
        ('rh', '0046_auto_20221120_1533'),
    ]

    operations = [
        migrations.AlterField(
            model_name='Servidor',
            name='pessoa_fisica',
            field=djtools.db.models.ForeignKeyPlus(default=1, on_delete=django.db.models.deletion.CASCADE, related_name='servidores', to='rh.pessoafisica'),
        ),
        migrations.AlterField(
            model_name='Viagem',
            name='pessoa_fisica',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='viagemscdppessoafisica_set', to='rh.pessoafisica'),
        ),
        migrations.AlterField(
            model_name='Papel',
            name='pessoa',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.pessoafisica', verbose_name='Pessoa Física'),
        ),
        migrations.AlterField(
            model_name='PessoaExterna',
            name='pessoa_fisica',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.pessoafisica'),
        ),
        migrations.AlterField(
            model_name='DadosBancariosPF',
            name='pessoa_fisica',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='dadosbancariospessoafisica_set', to='rh.pessoafisica'),
        ),
        migrations.AlterField(
            model_name='HorarioAgendado',
            name='solicitante',
            field=djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='solicitante', to='rh.funcionario'),
        ),
    ]