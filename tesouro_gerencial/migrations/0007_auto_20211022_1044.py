# Generated by Django 3.2.5 on 2021-10-22 10:44

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('tesouro_gerencial', '0006_merge_20210512_0953'),
    ]

    operations = [
        migrations.AlterField(
            model_name='documentoempenho',
            name='tipo',
            field=djtools.db.models.CharFieldPlus(choices=[('NE', 'Nota de Empenho'), ('RO', 'Registro Orçamentário'), ('NS', 'Nota de Sistema'), ('OB', 'Ordem Bancária'), ('DF', 'Documento de Arrecadação da Receita Federal'), ('DR', 'Documento de Arrecadação Municipal/Estadual'), ('GP', 'Guia de Recolhimento da Previdência Social'), ('GR', 'Guia de recolhimento da União')], max_length=2, verbose_name='Tipo'),
        ),
        migrations.AlterField(
            model_name='documentoliquidacao',
            name='tipo',
            field=djtools.db.models.CharFieldPlus(choices=[('NE', 'Nota de Empenho'), ('RO', 'Registro Orçamentário'), ('NS', 'Nota de Sistema'), ('OB', 'Ordem Bancária'), ('DF', 'Documento de Arrecadação da Receita Federal'), ('DR', 'Documento de Arrecadação Municipal/Estadual'), ('GP', 'Guia de Recolhimento da Previdência Social'), ('GR', 'Guia de recolhimento da União')], max_length=2, verbose_name='Tipo'),
        ),
        migrations.AlterField(
            model_name='documentopagamento',
            name='tipo',
            field=djtools.db.models.CharFieldPlus(choices=[('NE', 'Nota de Empenho'), ('RO', 'Registro Orçamentário'), ('NS', 'Nota de Sistema'), ('OB', 'Ordem Bancária'), ('DF', 'Documento de Arrecadação da Receita Federal'), ('DR', 'Documento de Arrecadação Municipal/Estadual'), ('GP', 'Guia de Recolhimento da Previdência Social'), ('GR', 'Guia de recolhimento da União')], max_length=2, verbose_name='Tipo'),
        ),
    ]