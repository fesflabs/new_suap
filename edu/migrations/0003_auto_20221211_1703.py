# Generated by Django 3.2.5 on 2022-12-11 17:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('edu', '0002_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='aluno',
            name='periodo_letivo',
            field=models.PositiveIntegerField(choices=[[1, '1']], verbose_name='Período de Ingresso'),
        ),
        migrations.AlterField(
            model_name='aluno',
            name='periodo_letivo_integralizacao',
            field=models.PositiveIntegerField(blank=True, choices=[[1, '1']], null=True, verbose_name='Periodo Letivo da Integralização'),
        ),
        migrations.AlterField(
            model_name='atividadeaprofundamento',
            name='periodo_letivo',
            field=models.PositiveIntegerField(choices=[[1, '1']], verbose_name='Período Letivo'),
        ),
        migrations.AlterField(
            model_name='atividadecomplementar',
            name='periodo_letivo',
            field=models.PositiveIntegerField(choices=[[1, '1']], verbose_name='Período Letivo'),
        ),
        migrations.AlterField(
            model_name='calendarioacademico',
            name='periodo_letivo',
            field=models.PositiveIntegerField(choices=[[1, '1']], verbose_name='Período letivo'),
        ),
        migrations.AlterField(
            model_name='colacaograu',
            name='periodo_letivo',
            field=models.PositiveIntegerField(choices=[[1, '1']], verbose_name='Período Letivo'),
        ),
        migrations.AlterField(
            model_name='configuracaopedidomatricula',
            name='periodo_letivo',
            field=models.PositiveIntegerField(choices=[[1, '1']], verbose_name='Período Letivo'),
        ),
        migrations.AlterField(
            model_name='cursocampus',
            name='periodo_letivo',
            field=models.PositiveIntegerField(choices=[[1, '1']], null=True, verbose_name='Período letivo'),
        ),
        migrations.AlterField(
            model_name='diario',
            name='periodo_letivo',
            field=models.PositiveIntegerField(choices=[[1, '1']], verbose_name='Período Letivo'),
        ),
        migrations.AlterField(
            model_name='diarioespecial',
            name='periodo_letivo',
            field=models.PositiveIntegerField(choices=[[1, '1']], verbose_name='Período Letivo'),
        ),
        migrations.AlterField(
            model_name='itemplanoestudo',
            name='periodo_letivo',
            field=models.IntegerField(choices=[[1, '1']], verbose_name='Período Letivo'),
        ),
        migrations.AlterField(
            model_name='matriz',
            name='periodo_criacao',
            field=models.PositiveIntegerField(choices=[[1, '1']], default=1, verbose_name='Período Criação'),
        ),
        migrations.AlterField(
            model_name='professordiario',
            name='periodo_letivo_ch',
            field=models.IntegerField(blank=True, choices=[[1, '1']], help_text='Informar caso o percentual da carga horária ministrada se refira a apenas um período letivo.', null=True, verbose_name='Período Letivo da Carga-Horária'),
        ),
        migrations.AlterField(
            model_name='turma',
            name='periodo_letivo',
            field=models.PositiveIntegerField(choices=[[1, '1']], verbose_name='Período Letivo'),
        ),
        migrations.AlterField(
            model_name='turmaminicurso',
            name='periodo_letivo',
            field=models.PositiveIntegerField(choices=[[1, '1']], verbose_name='Período Letivo'),
        ),
    ]