# Generated by Django 3.2.5 on 2022-10-28 10:26

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('ppe', '0007_auto_20221021_0921'),
    ]

    operations = [
        migrations.CreateModel(
            name='RepresentacaoConceitual',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Descrição')),
                ('valor_minimo', djtools.db.models.NotaField(verbose_name='Valor Mínimo')),
                ('valor_maximo', djtools.db.models.NotaField(verbose_name='Valor Máximo')),
                ('estrutura_curso', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='ppe.estruturacurso')),
            ],
            options={
                'verbose_name': 'Representação Conceitual',
                'verbose_name_plural': 'Representações Conceituais',
            },
        ),
    ]
