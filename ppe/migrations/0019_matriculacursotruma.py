# Generated by Django 3.2.5 on 2022-12-02 09:08

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0018_trabalhadoreducando_turma'),
    ]

    operations = [
        migrations.CreateModel(
            name='MatriculaCursoTruma',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nota_1', djtools.db.models.NotaField(null=True, verbose_name='N1')),
                ('nota_final', djtools.db.models.NotaField(null=True, verbose_name='NAF')),
                ('situacao', models.PositiveIntegerField(choices=[[1, 'Cursando'], [2, 'Aprovado'], [3, 'Reprovado'], [4, 'Prova Final'], [5, 'Reprovado por falta'], [6, 'Trancado'], [7, 'Cancelado'], [8, 'Dispensado'], [9, 'Pendente']], default=1, verbose_name='Situação')),
                ('curso_turma', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='ppe.cursoturma')),
                ('trabalhador_educando', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='ppe.trabalhadoreducando')),
            ],
            options={
                'verbose_name': 'Matrícula em Turma',
                'verbose_name_plural': 'Matrículas em Turma',
                'ordering': ('trabalhador_educando__pessoa_fisica__nome',),
            },
        ),
    ]