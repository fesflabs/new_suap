# Generated by Django 3.2.5 on 2021-07-19 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('cnpq', '0003_auto_20210518_1127'),
    ]

    operations = [
        migrations.AlterField(
            model_name='formacaoacademicatitulacao',
            name='flag_bolsa',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='integranteprojeto',
            name='flag_responsavel',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='organizacaoeventos',
            name='flag_evento_itinerante',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='orientacaoandamento',
            name='flag_bolsa',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='orientacaoconcluida',
            name='flag_bolsa',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='outraproducao',
            name='flag_relevancia',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='producaobibliografica',
            name='flag_relevancia',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='producaotecnica',
            name='flag_relevancia',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='vinculo',
            name='flag_dedicacao_exclusiva',
            field=models.BooleanField(null=True),
        ),
        migrations.AlterField(
            model_name='vinculo',
            name='flag_vinculo_empregaticio',
            field=models.BooleanField(null=True),
        ),
    ]
