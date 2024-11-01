# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-14 14:54


from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [('rh', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('nome', models.CharField(max_length=255))],
            options={'verbose_name': 'Categoria', 'verbose_name_plural': 'Categorias'},
        ),
        migrations.CreateModel(
            name='Opcao',
            fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('nome', models.CharField(max_length=255))],
            options={'verbose_name': 'Opções', 'verbose_name_plural': 'Opção', 'ordering': ('nome',)},
        ),
        migrations.CreateModel(
            name='Pergunta',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('texto', models.TextField(help_text="Palavras relacionadas ao dicionário de dados devem estar entre aspas simples. Ex: 'IFRN'")),
                ('objetiva', models.BooleanField(default=False)),
                ('ordem', models.IntegerField()),
                ('identificador', models.CharField(max_length=255)),
                ('categoria', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='cpa.Categoria')),
            ],
            options={'verbose_name': 'Pergunta', 'verbose_name_plural': 'Perguntas', 'ordering': ('ordem',)},
        ),
        migrations.CreateModel(
            name='Questionario',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=255, verbose_name='Descrição')),
                ('publico', models.IntegerField(choices=[[0, 'Geral'], [1, 'Alunos'], [2, 'Técnicos'], [3, 'Docentes']])),
                ('ano', models.IntegerField()),
                ('data_inicio', models.DateField(verbose_name='Data de Início')),
                ('data_fim', models.DateField(verbose_name='Data de Término')),
                ('dicionario', models.TextField(blank=True, help_text='Ex: IFRN: Instituto Federal do...', null=True, verbose_name='Dicionário')),
                ('campus', djtools.db.models.ManyToManyFieldPlus(blank=True, to='rh.UnidadeOrganizacional', verbose_name='Campus')),
            ],
            options={'verbose_name': 'Questionário', 'verbose_name_plural': 'Questionários'},
        ),
        migrations.CreateModel(
            name='QuestionarioCategoria',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ordem', models.IntegerField()),
                ('categoria', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='cpa.Categoria')),
                ('questionario', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='cpa.Questionario')),
            ],
            options={'verbose_name': 'Categorias do questionário', 'verbose_name_plural': 'Categoria do questionário', 'ordering': ('ordem',)},
        ),
        migrations.CreateModel(
            name='QuestionarioOpcao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ordem', models.IntegerField()),
                (
                    'agrupamento',
                    models.CharField(
                        blank=True, help_text='Os gráficos dos resultados agrupados irão levar esse campo em consideração', max_length=255, verbose_name='Nome do Agrupamento'
                    ),
                ),
                ('opcao', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='cpa.Opcao')),
                ('questionario', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='cpa.Questionario')),
            ],
            options={'verbose_name': 'Opções de resposta', 'verbose_name_plural': 'Opção de resposta', 'ordering': ('ordem',)},
        ),
        migrations.CreateModel(
            name='Resposta',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('identificador', models.CharField(max_length=255)),
                ('referencia', models.CharField(blank=True, max_length=255, null=True)),
                ('resposta', models.TextField(help_text='Resposta')),
                ('opcao', djtools.db.models.ForeignKeyPlus(help_text='Resposta objetiva', null=True, on_delete=django.db.models.deletion.CASCADE, to='cpa.Opcao')),
                ('pergunta', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='cpa.Pergunta')),
                (
                    'uo',
                    djtools.db.models.ForeignKeyPlus(
                        null=True, on_delete=django.db.models.deletion.CASCADE, related_name='respostaautoavaliacao_uo_set', to='rh.UnidadeOrganizacional'
                    ),
                ),
            ],
            options={'verbose_name': 'Resposta', 'verbose_name_plural': 'Respostas'},
        ),
        migrations.AddField(model_name='pergunta', name='questionario', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='cpa.Questionario')),
    ]
