# Generated by Django 3.2.5 on 2021-12-07 18:36

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0027_merge_20211028_1549'),
        ('licenca_capacitacao', '0019_editalliccapacitacao_codigos_licenca_capacitacao'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='editalliccapacitacao',
            name='codigos_licenca_capacitacao',
        ),
        migrations.CreateModel(
            name='CodigoLicencaCapacitacao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo_licenca_capacitacao', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.afastamentosiape', verbose_name='Código de Licença Capacitação')),
            ],
            options={
                'verbose_name': 'Código de Licença Capacitação',
                'verbose_name_plural': 'Códigos de Licença Capacitação',
            },
        ),
    ]