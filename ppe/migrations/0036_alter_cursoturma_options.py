# Generated by Django 3.2.5 on 2022-12-27 14:49

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0035_alter_cursoturma_options'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='cursoturma',
            options={'permissions': (('lancar_nota_curso_turma', 'Pode lançar nota em Cursos'), ('reabrir_cursoturma', 'Pode reabri Cursos'), ('emitir_boletins', 'Pode emitir boletins dos Cursos'), ('mudar_posse_curso_turma', 'Pode mudar posse de Diário do cursos')), 'verbose_name': 'Diário de Curso', 'verbose_name_plural': 'Diários de Cursos'},
        ),
    ]