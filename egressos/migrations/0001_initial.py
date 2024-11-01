# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-14 14:54


from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [('comum', '0002_auto_20190814_1443'), ('edu', '0001_initial'), ('rh', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='Categoria',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Título')),
                ('ordem', models.PositiveSmallIntegerField(null=True, verbose_name='Ordem')),
            ],
            options={'verbose_name': 'Categoria', 'verbose_name_plural': 'Categorias', 'ordering': ('pk',)},
        ),
        migrations.CreateModel(
            name='EmailEnviado',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('destinatarios', models.TextField(verbose_name='Destinatários')),
                ('mensagem', models.TextField(verbose_name='Mensagem')),
            ],
            options={'verbose_name': 'E-mail Enviado', 'verbose_name_plural': 'E-mails Enviados'},
        ),
        migrations.CreateModel(
            name='Opcao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('conteudo', models.TextField(verbose_name='Opção de Resposta')),
                ('complementacao_subjetiva', models.BooleanField(default=False, verbose_name='Complementação Subjetiva')),
                (
                    'direcionamento_categoria',
                    djtools.db.models.ForeignKeyPlus(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='egressos.Categoria', verbose_name='Direcionar à Categoria'
                    ),
                ),
            ],
            options={'verbose_name': 'Opção de Resposta', 'verbose_name_plural': 'Opção de Resposta', 'ordering': ('pk',)},
        ),
        migrations.CreateModel(
            name='Pergunta',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('conteudo', models.TextField(verbose_name='Conteúdo')),
                (
                    'tipo',
                    djtools.db.models.PositiveIntegerFieldPlus(
                        choices=[
                            [1, 'Objetiva de resposta única'],
                            [2, 'Objetiva de respostas múltiplas'],
                            [3, 'Subjetiva'],
                            [4, 'Objetiva de resposta única com complementação subjetiva'],
                        ]
                    ),
                ),
                ('preenchimento_obrigatorio', models.BooleanField(verbose_name='Preenchimento Obrigatório')),
                ('categoria', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='egressos.Categoria', verbose_name='Categoria')),
            ],
            options={'verbose_name': 'Pergunta', 'verbose_name_plural': 'Pergunta', 'ordering': ('categoria__pk', 'pk')},
        ),
        migrations.CreateModel(
            name='Pesquisa',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Título')),
                ('descricao', models.TextField(verbose_name='Descrição')),
                ('inicio', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Início')),
                ('fim', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Fim')),
                ('publicada', models.NullBooleanField(verbose_name='Publicada')),
                ('conclusao', djtools.db.models.ManyToManyFieldPlus(to='comum.Ano', verbose_name='Ano de Conclusão')),
                ('curso_campus', djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='edu.CursoCampus', verbose_name='Curso')),
                (
                    'modalidade',
                    djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='edu.Modalidade', verbose_name='Público Alvo'),
                ),
                ('uo', djtools.db.models.ManyToManyFieldPlus(blank=True, to='rh.UnidadeOrganizacional', verbose_name='Campus')),
            ],
            options={'verbose_name': 'Pesquisa de Acompanhamento de Egressos', 'verbose_name_plural': 'Pesquisas de Acompanhamento de Egressos'},
        ),
        migrations.CreateModel(
            name='Resposta',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('resposta_subjetiva', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Resposta Subjetiva')),
                ('aluno', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='edu.Aluno')),
                ('opcoes', djtools.db.models.ManyToManyFieldPlus(to='egressos.Opcao', verbose_name='Opções Selecionadas')),
                ('pergunta', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='egressos.Pergunta')),
            ],
            options={
                'verbose_name': 'Resposta',
                'verbose_name_plural': 'Respostas',
                'permissions': (('view_pesquisas_respondidas', 'Pode ver suas próprias respostas a pesquisas de egressos'),),
            },
        ),
        migrations.AddField(model_name='pergunta', name='pesquisa', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='egressos.Pesquisa')),
        migrations.AddField(model_name='opcao', name='pergunta', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='egressos.Pergunta')),
        migrations.AddField(
            model_name='emailenviado', name='pesquisa', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='egressos.Pesquisa')
        ),
        migrations.AddField(model_name='categoria', name='pesquisa', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='egressos.Pesquisa')),
        migrations.AlterUniqueTogether(name='resposta', unique_together=set([('aluno', 'pergunta')])),
    ]
