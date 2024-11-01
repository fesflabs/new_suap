# Generated by Django 3.2.5 on 2022-12-27 10:09

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0032_rename_posse_fim_prova_final_cursoturma_posse_etapa_5'),
    ]

    operations = [
        migrations.CreateModel(
            name='SituacaoMatricula',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo_academico', models.IntegerField(null=True)),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=255, unique=True, verbose_name='Descrição')),
                ('ativo', models.BooleanField(default=False, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Situação de Matrícula',
                'verbose_name_plural': 'Situações de Matrículas',
                'ordering': ('descricao',),
            },
        ),
        migrations.AlterModelOptions(
            name='cursoturma',
            options={'permissions': (('lancar_nota_curso_turma', 'Pode lançar nota em Cursos'), ('reabrir_cursoturma', 'Pode reabri Cursos')), 'verbose_name': 'Diário de Curso', 'verbose_name_plural': 'Diários de Cursos'},
        ),
        migrations.AddField(
            model_name='trabalhadoreducando',
            name='situacao',
            field=djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='ppe.situacaomatricula', verbose_name='Situação'),
        ),
    ]
