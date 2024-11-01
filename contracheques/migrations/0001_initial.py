# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-14 14:54


from django.db import migrations, models
import django.db.models.deletion
import django.db.models.manager
import djtools.db.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [('comum', '0002_auto_20190814_1443'), ('rh', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='AgrupamentoRubricas',
            fields=[('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')), ('descricao', models.CharField(max_length=150))],
            options={'verbose_name': 'Agrupamento de Rubrica', 'verbose_name_plural': 'Agrupamento de Rubricas'},
        ),
        migrations.CreateModel(
            name='Beneficiario',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=40)),
                ('agencia', models.CharField(max_length=6, null=True)),
                ('ccor', models.CharField(max_length=13, null=True)),
                ('banco', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.Banco')),
            ],
            options={'verbose_name': 'Beneficiário', 'verbose_name_plural': 'Beneficiários'},
        ),
        migrations.CreateModel(
            name='ContraCheque',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'mes',
                    models.SmallIntegerField(
                        choices=[
                            [1, 'Janeiro'],
                            [2, 'Fevereiro'],
                            [3, 'Março'],
                            [4, 'Abril'],
                            [5, 'Maio'],
                            [6, 'Junho'],
                            [7, 'Julho'],
                            [8, 'Agosto'],
                            [9, 'Setembro'],
                            [10, 'Outubro'],
                            [11, 'Novembro'],
                            [12, 'Dezembro'],
                        ]
                    ),
                ),
                ('servidor_nivel_padrao', models.CharField(blank=True, max_length=4, null=True, verbose_name='Nível Padrão')),
                ('bruto', djtools.db.models.DecimalFieldPlus(decimal_places=2, max_digits=12, null=True)),
                ('desconto', djtools.db.models.DecimalFieldPlus(decimal_places=2, max_digits=12, null=True)),
                ('liquido', djtools.db.models.DecimalFieldPlus(decimal_places=2, max_digits=12, null=True)),
                ('ano', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='comum.Ano')),
                ('pensionista', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.Pensionista')),
                ('servidor', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.Servidor')),
                (
                    'servidor_cargo_classe',
                    djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.CargoClasse', verbose_name='Cargo Classe'),
                ),
                (
                    'servidor_cargo_emprego',
                    djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.CargoEmprego', verbose_name='Cargo Emprego'),
                ),
                (
                    'servidor_jornada_trabalho',
                    djtools.db.models.ForeignKeyPlus(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.JornadaTrabalho', verbose_name='Jornada de Trabalho'
                    ),
                ),
                (
                    'servidor_setor_localizacao',
                    djtools.db.models.ForeignKeyPlus(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='setor_exercicio', to='rh.Setor', verbose_name='Setor de Localização'
                    ),
                ),
                (
                    'servidor_setor_lotacao',
                    djtools.db.models.ForeignKeyPlus(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='setor_lotacao', to='rh.Setor', verbose_name='Setor de Lotação'
                    ),
                ),
                (
                    'servidor_situacao',
                    djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.Situacao', verbose_name='Situação'),
                ),
                (
                    'servidor_titulacao',
                    djtools.db.models.ForeignKeyPlus(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.Titulacao', verbose_name='Titulação baseada no contracheque'
                    ),
                ),
            ],
            options={
                'verbose_name': 'Contracheque',
                'verbose_name_plural': 'Contracheques',
                'permissions': (
                    ('pode_ver_contracheques_detalhados', 'Ver qualquer Contracheque detalhado'),
                    ('pode_ver_contracheques_agrupados', 'Ver o total de Contracheque ou grupo'),
                    ('pode_ver_contracheques_historicos', 'Buscar dados no histórico'),
                ),
            },
        ),
        migrations.CreateModel(
            name='ContraChequeRubrica',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor', djtools.db.models.DecimalFieldPlus(decimal_places=2, max_digits=12, null=True)),
                ('sequencia', models.IntegerField(null=True)),
                ('prazo', models.CharField(max_length=3, null=True)),
                ('beneficiario', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='contracheques.Beneficiario')),
                ('contra_cheque', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='contracheques.ContraCheque')),
            ],
            options={'verbose_name': 'Rubrica de Contracheque', 'verbose_name_plural': 'Rubricas de Contracheques'},
        ),
        migrations.CreateModel(
            name='Rubrica',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('codigo', models.CharField(max_length=5, unique=True)),
                ('excluido', models.BooleanField(default=False)),
                ('nome', models.CharField(max_length=40)),
            ],
            options={'abstract': False},
            managers=[('todos', django.db.models.manager.Manager())],
        ),
        migrations.CreateModel(
            name='TipoRubrica',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=20)),
                ('codigo', models.CharField(max_length=2)),
            ],
            options={'verbose_name': 'Tipo de Rubrica', 'verbose_name_plural': 'Tipos de Rubricas'},
        ),
        migrations.AddField(
            model_name='contrachequerubrica',
            name='rubrica',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='contracheques.Rubrica'),
        ),
        migrations.AddField(
            model_name='contrachequerubrica',
            name='tipo',
            field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='contracheques.TipoRubrica'),
        ),
        migrations.AddField(model_name='agrupamentorubricas', name='rubricas', field=djtools.db.models.ManyToManyFieldPlus(to='contracheques.Rubrica')),
    ]
