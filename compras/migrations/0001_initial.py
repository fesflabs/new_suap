# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-14 14:54


from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models
import djtools.middleware.threadlocals


class Migration(migrations.Migration):

    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ('materiais', '__first__'), ('rh', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='ProcessoCompra',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cadastrado_em', models.DateTimeField(auto_now_add=True)),
                ('descricao', models.CharField(max_length=255, verbose_name='Descrição')),
                ('observacao', models.TextField(blank=True)),
                ('status', models.IntegerField(choices=[[1, 'Aguardando validação'], [2, 'Validado']], default=1)),
                ('data_inicio', models.DateTimeField()),
                ('data_fim', models.DateTimeField()),
                ('validado_em', models.DateTimeField(blank=True, editable=False, null=True)),
                (
                    'cadastrado_por',
                    djtools.db.models.CurrentUserField(
                        blank=True,
                        default=djtools.middleware.threadlocals.get_user,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ('tags', models.ManyToManyField(blank=True, to='materiais.MaterialTag')),
                (
                    'validado_por',
                    djtools.db.models.ForeignKeyPlus(
                        blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='abc', to=settings.AUTH_USER_MODEL
                    ),
                ),
            ],
            options={
                'verbose_name': 'Processo de compra',
                'verbose_name_plural': 'Processos de compra',
                'permissions': (('pode_gerenciar_processocompra', 'Pode gerenciar processos de compra'),),
            },
        ),
        migrations.CreateModel(
            name='ProcessoCompraCampus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_inicio', models.DateTimeField()),
                ('data_fim', models.DateTimeField()),
                ('status', models.IntegerField(choices=[[1, 'Aguardando validação'], [2, 'Validado']], default=1, editable=False)),
                ('validado_em', models.DateTimeField(blank=True, editable=False, null=True)),
                ('valor_total', djtools.db.models.DecimalFieldPlus(decimal_places=2, default=0, editable=False, max_digits=12)),
                ('campus', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.UnidadeOrganizacional')),
                ('processo_compra', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='compras.ProcessoCompra')),
                ('validado_por', djtools.db.models.ForeignKeyPlus(blank=True, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
            options={
                'verbose_name': 'Processo Compra Campus',
                'verbose_name_plural': 'Processo Compra Campus',
                'ordering': ('processo_compra', 'campus__setor__sigla'),
                'permissions': (('pode_validar_do_seu_campus', 'Pode validar processos de compra do seu campus'),),
            },
        ),
        migrations.CreateModel(
            name='ProcessoCompraCampusMaterial',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cadastrado_em', models.DateTimeField(auto_now_add=True)),
                ('qtd', models.FloatField()),
                ('valor_unitario', djtools.db.models.DecimalFieldPlus(decimal_places=2, default=0, editable=False, max_digits=12)),
                (
                    'valor_total',
                    djtools.db.models.DecimalFieldPlus(
                        decimal_places=2, default=0, editable=False, help_text='Esse valor vai ser atualizado após o processo de compra ser validado.', max_digits=12
                    ),
                ),
                (
                    'cadastrado_por',
                    djtools.db.models.CurrentUserField(
                        blank=True,
                        default=djtools.middleware.threadlocals.get_user,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ('material', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='materiais.Material')),
                ('material_tag', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='materiais.MaterialTag')),
                ('processo_compra_campus', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='compras.ProcessoCompraCampus')),
            ],
            options={'verbose_name': 'Material em processo de compra', 'verbose_name_plural': 'Materiais em processo de compra'},
        ),
        migrations.CreateModel(
            name='ProcessoCompraMaterial',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor_unitario', djtools.db.models.DecimalFieldPlus(decimal_places=2, default=0, editable=False, max_digits=12)),
                ('valor_referencia', models.TextField()),
                ('material', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='materiais.Material')),
                ('material_tag', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='materiais.MaterialTag')),
                ('processo_compra', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='compras.ProcessoCompra')),
            ],
            options={'ordering': ['material_tag', 'material__id']},
        ),
        migrations.CreateModel(
            name='ProcessoMaterialCotacao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cotacao', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='materiais.MaterialCotacao')),
                ('material', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='materiais.Material')),
                ('processo_compra', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='compras.ProcessoCompra')),
            ],
            options={'verbose_name': 'Processo de Compra Cotação', 'verbose_name_plural': 'Processos de Compra Cotações'},
        ),
        migrations.AlterUniqueTogether(name='processocompracampusmaterial', unique_together=set([('processo_compra_campus', 'material')])),
        migrations.AlterUniqueTogether(name='processocompracampus', unique_together=set([('processo_compra', 'campus')])),
    ]