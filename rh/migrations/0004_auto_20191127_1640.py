# Generated by Django 2.2.7 on 2019-11-27 16:40

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('rh', '0003_auto_20191009_1509')]

    operations = [
        migrations.CreateModel(
            name='CargoEmpregoArea',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=255)),
                ('cargo_emprego', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.CargoEmprego')),
            ],
            options={'verbose_name': 'Área do Cargo Emprego', 'verbose_name_plural': 'Áreas dos Cargos de Emprego'},
        ),
        migrations.AddField(
            model_name='servidor',
            name='cargo_emprego_area',
            field=djtools.db.models.ForeignKeyPlus(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.CargoEmpregoArea', verbose_name='Área do Cargo Emprego'
            ),
        ),
    ]