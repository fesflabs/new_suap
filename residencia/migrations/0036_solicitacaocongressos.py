# Generated by Django 3.2.5 on 2023-02-01 20:56

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('residencia', '0035_auto_20230201_2024'),
    ]

    operations = [
        migrations.CreateModel(
            name='SolicitacaoCongressos',
            fields=[
                ('solicitacaousuario_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='residencia.solicitacaousuario')),
                ('descricao_evento', models.TextField(verbose_name='Descrição do evento')),
                ('condicao_participacao', models.TextField(verbose_name='Condição da participação')),
                ('modalidade', djtools.db.models.CharFieldPlus(choices=[('Presencial', 'Presencial'), ('Online', 'Online')], default='Presencial', max_length=255, null=True, verbose_name='Modalidade do evento')),
                ('hora_inicio', djtools.db.models.TimeFieldPlus(help_text='Utilize o formato hh:mm:ss', verbose_name='Horário do evento')),
                ('estagio', models.TextField(blank=True, help_text='Se for R2 informe o estágio que está no momento', null=True, verbose_name='Estágio')),
                ('data_inicio', djtools.db.models.DateFieldPlus(verbose_name='Início')),
                ('data_fim', djtools.db.models.DateFieldPlus(verbose_name='Fim')),
                ('email', models.CharField(blank=True, max_length=50, verbose_name='E-mail para contato')),
            ],
            options={
                'verbose_name': 'Solicitação de Congressos',
                'verbose_name_plural': 'Solicitações de Congressos',
            },
            bases=('residencia.solicitacaousuario',),
        ),
    ]