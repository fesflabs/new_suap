# Generated by Django 3.2.5 on 2022-12-19 09:13

from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0053_merge_20220929_2218'),
        ('ppe', '0029_auto_20221211_1025'),
    ]

    operations = [
        migrations.AddField(
            model_name='trabalhadoreducando',
            name='categoria',
            field=djtools.db.models.CharFieldPlus(blank=True, choices=[['Biomedicina', 'Biomedicina'], ['Enfermagem', 'Enfermagem'], ['Farmácia', 'Farmácia'], ['Fisioterapia', 'Fisioterapia'], ['Fonoaudiologia', 'Fonoaudiologia'], ['Medicina', 'Medicina'], ['Medicina Veterinária', 'Medicina Veterinária'], ['Nutrição', 'Nutrição'], ['Odontologia', 'Odontologia'], ['Psicologia', 'Psicologia'], ['Terapia Ocupacional', 'Terapia Ocupacional'], ['Saúde Ocupacional', 'Saúde Ocupacional']], max_length=100, null=True, verbose_name='Categoria'),
        ),
        migrations.AddField(
            model_name='trabalhadoreducando',
            name='conselho',
            field=djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.conselhoprofissional', verbose_name='Conselho de Fiscalização Profissional'),
        ),
        migrations.AddField(
            model_name='trabalhadoreducando',
            name='numero_registro',
            field=djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Número de Registro no Conselho de Fiscalização Profissional'),
        ),
    ]
