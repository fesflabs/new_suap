# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-14 14:54


from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [('comum', '0002_auto_20190814_1443'), ('rh', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='Aditivo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ordem', models.PositiveSmallIntegerField(default=0)),
                ('numero', models.CharField(max_length=10, verbose_name='Número')),
                ('objeto', models.TextField(max_length=500)),
                ('data', models.DateField(db_column='data', verbose_name='Data de Realização')),
                ('data_inicio', models.DateField(blank=True, db_column='data_inicio', null=True, verbose_name='Data de Início')),
                ('data_fim', models.DateField(blank=True, db_column='data_fim', null=True, verbose_name='Data de Vencimento')),
            ],
        ),
        migrations.CreateModel(
            name='AnexoConvenio',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(help_text='Breve descrição sobre o conteúdo do anexo', max_length=255, verbose_name='Descrição')),
                ('arquivo', models.OneToOneField(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.Arquivo')),
            ],
            options={'verbose_name': 'Anexo', 'verbose_name_plural': 'Anexos'},
        ),
        migrations.CreateModel(
            name='ConselhoProfissional',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', djtools.db.models.CharFieldPlus(max_length=100, verbose_name='Nome do Conselho')),
                ('sigla', djtools.db.models.CharFieldPlus(max_length=10, verbose_name='Sigla do Conselho')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={'verbose_name': 'Conselho Profissional', 'verbose_name_plural': 'Conselhos Profissionais'},
        ),
        migrations.CreateModel(
            name='Convenio',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.CharField(help_text='No formato: 99999/9999', max_length=10, verbose_name='Número')),
                ('data_inicio', models.DateField(db_column='data_inicio', verbose_name='Data de Início')),
                ('data_fim', models.DateField(db_column='data_fim', verbose_name='Data de Vencimento')),
                ('objeto', models.TextField(max_length=500)),
                ('continuado', models.BooleanField(default=False, verbose_name='Continuado')),
                ('financeiro', models.BooleanField(default=False, verbose_name='Usa Recurso Financeiro')),
                ('conveniadas', models.ManyToManyField(db_column='pessoajuridica_id', related_name='conveniadas_set', to='rh.Pessoa', verbose_name='Conveniadas')),
                ('interveniente', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.PessoaJuridica', verbose_name='Interveniente')),
            ],
            options={'verbose_name': 'Convênio', 'verbose_name_plural': 'Convênios'},
        ),
        migrations.CreateModel(
            name='ProfissionalLiberal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_registro', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Número de Registro no Conselho de Fiscalização Profissional')),
                ('telefone', models.CharField(max_length=45, null=True, verbose_name='Telefone')),
                ('email', models.EmailField(max_length=254, null=True, verbose_name='E-mail')),
                ('logradouro', djtools.db.models.CharFieldPlus(max_length=255, null=True)),
                ('numero', models.CharField(max_length=50, null=True, verbose_name='Nº')),
                ('complemento', djtools.db.models.CharFieldPlus(max_length=255, null=True)),
                ('bairro', djtools.db.models.CharFieldPlus(max_length=255, null=True)),
                ('cep', models.CharField(max_length=9, null=True, verbose_name='CEP')),
                ('conselho', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='convenios.ConselhoProfissional')),
                ('municipio', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.Municipio', verbose_name='Município')),
                ('pessoa', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.Pessoa')),
            ],
            options={'verbose_name': 'Profissional Liberal', 'verbose_name_plural': 'Profissionais Liberais'},
        ),
        migrations.CreateModel(
            name='SituacaoConvenio',
            fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('descricao', models.CharField(max_length=30))],
            options={'verbose_name': 'Situação de Convênio', 'verbose_name_plural': 'Situações de Convênio'},
        ),
        migrations.CreateModel(
            name='TipoAnexo',
            fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('descricao', models.CharField(max_length=30))],
            options={'verbose_name': 'Tipo de Anexo', 'verbose_name_plural': 'Tipos de Anexos'},
        ),
        migrations.CreateModel(
            name='TipoConvenio',
            fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('descricao', models.CharField(max_length=30))],
            options={'verbose_name': 'Tipo de Convênio', 'verbose_name_plural': 'Tipos de Convênios'},
        ),
        migrations.AddField(
            model_name='convenio',
            name='situacao',
            field=djtools.db.models.ForeignKeyPlus(
                on_delete=django.db.models.deletion.CASCADE, related_name='situacoes_set', to='convenios.SituacaoConvenio', verbose_name='Situação'
            ),
        ),
        migrations.AddField(
            model_name='convenio',
            name='tipo',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='convenios_set', to='convenios.TipoConvenio', verbose_name='Tipo'),
        ),
        migrations.AddField(
            model_name='convenio',
            name='uo',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.UnidadeOrganizacional', verbose_name='Campus'),
        ),
        migrations.AddField(
            model_name='anexoconvenio',
            name='convenio',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='anexos_set', to='convenios.Convenio'),
        ),
        migrations.AddField(model_name='anexoconvenio', name='tipo', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='convenios.TipoAnexo')),
        migrations.AddField(
            model_name='aditivo',
            name='convenio',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='aditivos_set', to='convenios.Convenio'),
        ),
        migrations.AlterUniqueTogether(name='aditivo', unique_together=set([('convenio', 'ordem')])),
    ]