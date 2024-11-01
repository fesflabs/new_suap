# Generated by Django 3.2.5 on 2022-06-24 11:19

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0042_alter_solicitacaoreservasala_status'),
    ]

    operations = [
        migrations.CreateModel(
            name='JustificativaUsuarioExterno',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('justificativa', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Perfil')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Perfil para Cadastro de Usuário Externo',
                'verbose_name_plural': 'Perfis para Cadastro de Usuários Externos',
            },
        ),
        migrations.CreateModel(
            name='UsuarioExterno',
            fields=[
            ],
            options={
                'verbose_name': 'Usuário Externo',
                'verbose_name_plural': 'Usuários Externos',
                'proxy': True,
                'indexes': [],
                'constraints': [],
            },
            bases=('comum.prestadorservico',),
        ),
        migrations.AlterModelOptions(
            name='prestadorservico',
            options={'permissions': (('eh_prestador', 'Prestador de Serviço'), ('change_usuarioexterno', 'Pode gerenciar Usuário Externo')), 'verbose_name': 'Prestador de serviço', 'verbose_name_plural': 'Prestadores de serviço'},
        ),
        migrations.AddField(
            model_name='prestadorservico',
            name='usuario_externo',
            field=models.BooleanField(default=False, help_text='Indica se o prestador é um Usuário Externo', verbose_name='Usuário Externo'),
        ),
        migrations.AddField(
            model_name='prestadorservico',
            name='justificativa_cadastro',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.justificativausuarioexterno', verbose_name='Justificativa para Cadastro'),
        ),
    ]
