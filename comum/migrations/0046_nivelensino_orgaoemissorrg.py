# Generated by Django 3.2.5 on 2022-09-26 21:08

from django.db import migrations, models
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0045_merge_0044_contatoemergencia_0044_merge_20220705_1111'),
    ]

    operations = [
        migrations.CreateModel(
            name='NivelEnsino',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=255, unique=True, verbose_name='Descrição')),
            ],
            options={
                'verbose_name': 'Nível de Ensino',
                'verbose_name_plural': 'Níveis de Ensino',
                'ordering': ('descricao',),
            },
        ),
        migrations.CreateModel(
            name='OrgaoEmissorRg',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Nome')),
            ],
            options={
                'verbose_name': 'Orgão Emissor de Identidade',
                'verbose_name_plural': 'Orgãos Emissores de Identidade',
            },
        ),
    ]