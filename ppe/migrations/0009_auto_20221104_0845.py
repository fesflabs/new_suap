# Generated by Django 3.2.5 on 2022-11-04 08:45

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0008_representacaoconceitual'),
    ]

    operations = [
        migrations.AddField(
            model_name='formacaoppe',
            name='ch_especifica',
            field=models.PositiveIntegerField(default=0, help_text='Hora-Relógio', verbose_name='Cursos específicos'),
        ),
        migrations.AlterField(
            model_name='cursoformacaoppe',
            name='tipo',
            field=models.PositiveIntegerField(choices=[[1, 'Formação Permanente'], [2, 'Transversais'], [3, 'Específicos']]),
        ),
        migrations.AlterField(
            model_name='formacaoppe',
            name='ch_componentes_obrigatorios',
            field=models.PositiveIntegerField(help_text='Hora-Relógio', verbose_name='Cursos obrigatórios'),
        ),
    ]
