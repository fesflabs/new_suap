# Generated by Django 3.2.5 on 2021-07-19 16:44

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('patrimonio', '0003_auto_20210309_2004'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inventariotipousopessoal',
            name='enviar_email_inscrito',
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AlterField(
            model_name='requisicao',
            name='inv_inconsistentes',
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AlterField(
            model_name='requisicaoinventariousopessoal',
            name='cadastrado',
            field=models.BooleanField(default=False, null=True),
        ),
        migrations.AlterField(
            model_name='requisicaoinventariousopessoal',
            name='indicado',
            field=models.BooleanField(default=False, null=True),
        ),
    ]