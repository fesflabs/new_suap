# Generated by Django 2.2.10 on 2020-04-06 11:10

import almoxarifado.estoque
from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('almoxarifado', '0002_auto_20190814_1454')]

    operations = [
        migrations.CreateModel(
            name='Catmat',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', djtools.db.models.CharFieldPlus(max_length=6, unique=True, verbose_name='Código')),
                ('descricao', models.TextField(max_length=1000, verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Código CATMAT', 'verbose_name_plural': 'Códigos CATMAT', 'ordering': ['codigo']},
            bases=(models.Model, almoxarifado.estoque.Estocavel),
        ),
        migrations.AddField(
            model_name='materialconsumo',
            name='catmat',
            field=djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to='almoxarifado.Catmat', verbose_name='CATMAT'),
        ),
    ]
