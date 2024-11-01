# Generated by Django 3.2.5 on 2021-07-19 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('projetos', '0011_edital_exige_frequencia_aluno'),
    ]

    operations = [
        migrations.AlterField(
            model_name='projeto',
            name='possui_acoes_empreendedorismo',
            field=models.BooleanField(null=True, verbose_name='Contempla Ações de Empreendedorismo, Cooperativismo ou Economia Solidária Criativa'),
        ),
        migrations.AlterField(
            model_name='registrofrequencia',
            name='atendida',
            field=models.BooleanField(null=True, verbose_name='Atendida'),
        ),
    ]
