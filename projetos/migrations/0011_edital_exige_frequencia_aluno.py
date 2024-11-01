# Generated by Django 2.2.16 on 2021-05-26 11:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projetos', '0010_auto_20210506_1521'),
    ]

    operations = [
        migrations.AddField(
            model_name='edital',
            name='exige_frequencia_aluno',
            field=models.BooleanField(default=False, help_text='Marque esta opção caso seja necessário que todos os alunos bolsistas tenham pelo menos um registro de frequência por mês.', verbose_name='Exige Registro de Frequência dos Alunos Bolsistas'),
        ),
    ]
