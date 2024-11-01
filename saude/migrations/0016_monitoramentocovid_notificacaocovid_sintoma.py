# Generated by Django 3.2.5 on 2022-03-17 15:52

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0038_auto_20211215_1218'),
        ('rh', '0031_auto_20220201_1748'),
        ('saude', '0015_alter_passaportevacinalcovid_options'),
    ]

    operations = [
        migrations.CreateModel(
            name='Sintoma',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=500, verbose_name='Descrição')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Sintoma',
                'verbose_name_plural': 'Sintomas',
            },
        ),
        migrations.CreateModel(
            name='NotificacaoCovid',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('situacao', djtools.db.models.CharFieldPlus(choices=[('Suspeito sintomático', 'Suspeito sintomático'), ('Suspeito contactante', 'Suspeito contactante'), ('Confirmado', 'Confirmado')], max_length=100, verbose_name='Situação')),
                ('data_inicio_sintomas', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data de Início dos Sintomas')),
                ('data_ultimo_teste', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data do Último Teste Realizado')),
                ('resultado_ultimo_teste', djtools.db.models.CharFieldPlus(blank=True, choices=[('Positivo', 'Positivo'), ('Negativo', 'Negativo')], max_length=15, null=True, verbose_name='Resultado do Último Teste Realizado')),
                ('arquivo_ultimo_teste', djtools.db.models.FileFieldPlus(blank=True, max_length=255, null=True, upload_to='upload/saude/covid', verbose_name='Arquivo do Último Teste Realizado')),
                ('data_contato_suspeito', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data do Contato Suspeito')),
                ('mora_com_suspeito', djtools.db.models.CharFieldPlus(blank=True, choices=[('Sim', 'Sim'), ('Não', 'Não')], max_length=15, null=True, verbose_name='A pessoa com quem você teve contato mora na mesma casa que você?')),
                ('esteve_sem_mascara', djtools.db.models.CharFieldPlus(blank=True, choices=[('Sim', 'Sim'), ('Não', 'Não')], max_length=15, null=True, verbose_name='Durante esse contato você esteve sem máscara?')),
                ('tempo_exposicao', djtools.db.models.CharFieldPlus(blank=True, max_length=200, null=True, verbose_name='Qual foi o tempo de exposição que você teve com essa pessoa?')),
                ('suspeito_fez_teste', djtools.db.models.CharFieldPlus(blank=True, choices=[('Sim', 'Sim'), ('Não', 'Não'), ('Não sei', 'Não sei')], max_length=15, null=True, verbose_name='A pessoa com que você teve contato realizou teste COVID?')),
                ('arquivo_teste', djtools.db.models.FileFieldPlus(blank=True, max_length=255, null=True, upload_to='upload/saude/covid', verbose_name='Resultado do Teste')),
                ('cadastrado_em', djtools.db.models.DateTimeFieldPlus(auto_now_add=True, verbose_name='Cadastrado em')),
                ('monitoramento', djtools.db.models.CharFieldPlus(choices=[('Sem monitoramento', 'Sem monitoramento'), ('Suspeito em monitoramento', 'Suspeito em monitoramento'), ('Confirmado em monitoramento', 'Confirmado em monitoramento'), ('Descartado', 'Descartado'), ('Recuperado', 'Recuperado'), ('Óbito', 'Óbito')], default='Sem monitoramento', max_length=100, verbose_name='Monitoramento')),
                ('sintomas', djtools.db.models.ManyToManyFieldPlus(blank=True, to='saude.Sintoma')),
                ('uo', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.unidadeorganizacional', verbose_name='Campus')),
                ('vinculo', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='comum.vinculo', verbose_name='Vínculo')),
            ],
            options={
                'verbose_name': 'Notificação de COVID-19',
                'verbose_name_plural': 'Notificações de COVID-19',
            },
        ),
        migrations.CreateModel(
            name='MonitoramentoCovid',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('monitoramento', models.TextField(verbose_name='Monitoramento')),
                ('situacao', djtools.db.models.CharFieldPlus(choices=[('Sem monitoramento', 'Sem monitoramento'), ('Suspeito em monitoramento', 'Suspeito em monitoramento'), ('Confirmado em monitoramento', 'Confirmado em monitoramento'), ('Descartado', 'Descartado'), ('Recuperado', 'Recuperado'), ('Óbito', 'Óbito')], max_length=50, verbose_name='Situação')),
                ('cadastrado_em', djtools.db.models.DateTimeFieldPlus(auto_now_add=True, verbose_name='Cadastrado em')),
                ('cadastrado_por', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='comum.vinculo', verbose_name='Cadastrado por')),
                ('notificacao', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='saude.notificacaocovid', verbose_name='Notificação Covid-19')),
            ],
            options={
                'verbose_name': 'Monitoramento de COVID-19',
                'verbose_name_plural': 'Monitoramentos de COVID-19',
            },
        ),
    ]
