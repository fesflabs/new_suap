# Generated by Django 3.2.5 on 2023-05-02 18:48

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0055_auto_20230502_1622'),
    ]

    operations = [
        migrations.AlterField(
            model_name='unidadeaprendizagem',
            name='ciclo',
            field=models.PositiveIntegerField(choices=[[1, 1], [2, 2], [3, 3], [4, 4]], default=1, verbose_name='Ciclo de avaliação'),
        ),
        migrations.CreateModel(
            name='UnidadeAprendizagemTurma',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('posse_etapa_1', models.PositiveIntegerField(choices=[[1, 'Preceptor'], [0, 'Registro']], default=1)),
                ('calendario_academico', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='residencia.calendarioacademico', verbose_name='Calendário Acadêmico')),
                ('turma', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.SET_NULL, to='residencia.turma')),
                ('unidade_aprendizagem', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.SET_NULL, to='residencia.unidadeaprendizagem')),
            ],
            options={
                'verbose_name': 'Unidade Aprendizagem Turma',
                'verbose_name_plural': 'Matrículas em Período',
                'ordering': ('turma', 'unidade_aprendizagem'),
                'unique_together': {('turma', 'unidade_aprendizagem')},
            },
        ),
    ]