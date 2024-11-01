# Generated by Django 2.2.7 on 2020-01-20 16:29

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('rh', '0004_auto_20191127_1640'), ('plan_estrategico', '0014_auto_20200109_1559')]

    operations = [
        migrations.CreateModel(
            name='IndicadorTrimestralCampus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ano', models.PositiveIntegerField(verbose_name='Ano')),
                ('valor', models.DecimalField(decimal_places=4, max_digits=15, null=True, verbose_name='Valor Real')),
                ('trimestre', models.PositiveIntegerField(choices=[(1, '1º Trimestre'), (2, '2º Trimestre'), (3, '3º Trimestre'), (4, '4º Trimestre')], verbose_name='Trimestre')),
                ('indicador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.PDIIndicador', verbose_name='Indicador')),
                (
                    'uo',
                    djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.UnidadeOrganizacional', verbose_name='Unidade Administrativa'),
                ),
            ],
            options={
                'verbose_name': 'Valor Trimestral do Indicador',
                'verbose_name_plural': 'Valores Trimestrais do Indicador',
                'unique_together': {('indicador', 'ano', 'uo', 'trimestre')},
            },
        )
    ]
