# Generated by Django 3.2.5 on 2023-05-05 11:00

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0061_merge_20230503_1615'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='unidadeaprendizagemturma',
            options={'ordering': ('turma', 'unidade_aprendizagem'), 'permissions': (('reabrir_unidadeaprendizagemturma', 'Pode reabrir Unidade aprendizagem'), ('lancar_nota_unidadeaprendizagemturma', 'Pode lançar nota em Unidade aprendizagem'), ('mudar_posse_unidadeaprendizagemturma', 'Pode mudar posse de Unidade aprendizagem')), 'verbose_name': 'Unidade Aprendizagem Turma', 'verbose_name_plural': 'Matrículas em Período'},
        ),
    ]