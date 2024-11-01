# Generated by Django 3.2.5 on 2022-06-08 11:51

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('professor_titular', '0003_auto_20210922_1107'),
    ]

    operations = [
        migrations.AddField(
            model_name='processotitular',
            name='clonado',
            field=models.BooleanField(default=False, verbose_name='Clonado'),
        ),
        migrations.CreateModel(
            name='CloneArquivoErro',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_arquivo', djtools.db.models.IntegerFieldPlus(choices=[[1, 'Arquivo Exigido'], [2, 'Arquivo']], verbose_name='Tipo de Arquivo')),
                ('nome_arquivo', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Arquivo')),
                ('tipo_documento_exigido', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Tipo de Documento Exigido')),
                ('indicador', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Indicador')),
                ('criterio', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Critério')),
                ('processo_titular', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='professor_titular.processotitular')),
            ],
            options={
                'verbose_name': 'Arquivo com problema na clonagem',
                'verbose_name_plural': 'Arquivos com problema na clonagem',
            },
        ),
    ]
