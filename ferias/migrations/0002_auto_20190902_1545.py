# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-09-02 15:45


from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('ferias', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='ParcelaFerias',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero_parcela', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Número da Parcela')),
                ('data_inicio', djtools.db.models.DateFieldPlus(db_index=True, verbose_name='Data de Início Parcela')),
                ('data_fim', djtools.db.models.DateFieldPlus(db_index=True, verbose_name='Data de Fim Parcela')),
                (
                    'setenta_porcento',
                    models.BooleanField(
                        default=False,
                        help_text='Adiantamento de 70% do salário, proporcional à parcela de férias (desconto integral após 02 meses do recebimento): Caso deseje esta opção, fazer a solicitação no campo acima, especificando em qual ou quais parcelas deseja o adiantamento.',
                        verbose_name='Adiantamento de Setenta Porcento?',
                    ),
                ),
                ('adiantamento_gratificacao_natalina', models.BooleanField(default=False, verbose_name='Adiantamento de Gratificação Natalina?')),
                ('continuacao_interrupcao', models.BooleanField(default=False, verbose_name='É a continuação de uma interrupção de férias?')),
                ('parcela_interrompida', models.BooleanField(default=False, verbose_name='A parcela foi interrompida?')),
                ('ferias', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='ferias.Ferias')),
            ],
            options={'verbose_name': 'Parcela de Férias', 'verbose_name_plural': 'Parcelas de Férias', 'ordering': ('ferias', 'numero_parcela')},
        ),
        migrations.AlterUniqueTogether(name='periodocadastroferias', unique_together=set([])),
        migrations.RemoveField(model_name='periodocadastroferias', name='ano_referencia'),
        migrations.RemoveField(model_name='periodocadastroferias', name='uo'),
        migrations.DeleteModel(name='PeriodoCadastroFerias'),
        migrations.AlterUniqueTogether(name='parcelaferias', unique_together=set([('ferias', 'numero_parcela')])),
    ]