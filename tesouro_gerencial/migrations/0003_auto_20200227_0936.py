# Generated by Django 2.2.7 on 2020-02-27 09:36

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('tesouro_gerencial', '0002_auto_20200131_1325')]

    operations = [
        migrations.CreateModel(
            name='DocumentoEmpenho',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', djtools.db.models.CharFieldPlus(max_length=23, unique=True, verbose_name='Número')),
                (
                    'tipo',
                    djtools.db.models.CharFieldPlus(
                        choices=[
                            ('NE', 'Nota de Empenho'),
                            ('NS', 'Nota de Sistema'),
                            ('OB', 'Ordem Bancária'),
                            ('DF', 'Documento de Arrecadação da Receita Federal'),
                            ('DR', 'Documento de Arrecadação Municipal/Estadual'),
                            ('GP', 'Guia de Recolhimento da Previdência Social'),
                            ('GR', 'Guia de recolhimento da União'),
                        ],
                        max_length=2,
                        verbose_name='Tipo',
                    ),
                ),
                ('data_emissao', djtools.db.models.DateFieldPlus(verbose_name='Data de Emissão')),
                ('observacao', models.TextField(verbose_name='Observação')),
                ('favorecido_codigo', djtools.db.models.CharFieldPlus(max_length=14)),
                ('favorecido_nome', djtools.db.models.CharFieldPlus(max_length=255)),
                ('acao_governo_original', djtools.db.models.CharFieldPlus(max_length=4)),
                ('fonte_recurso_original', djtools.db.models.CharFieldPlus(max_length=10)),
                ('naturesa_despesa_original', djtools.db.models.CharFieldPlus(max_length=6)),
                ('grupo_despesa_original', djtools.db.models.CharFieldPlus(max_length=1)),
                ('acao_governo', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.AcaoGoverno')),
                (
                    'documento_empenho_inicial',
                    djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.DocumentoEmpenho'),
                ),
                (
                    'emitente_ug',
                    djtools.db.models.ForeignKeyPlus(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='tesouro_gerencial_documentoempenho_emitente_ug',
                        to='tesouro_gerencial.UnidadeGestora',
                        verbose_name='UG Emitente',
                    ),
                ),
                (
                    'esfera_orcamentaria',
                    djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.EsferaOrcamentaria', verbose_name='Esfera orçamentária'),
                ),
                (
                    'fonte_recurso',
                    djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.FonteRecurso', verbose_name='Fonte de recurso'),
                ),
                ('plano_interno', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.PlanoInterno')),
                ('ptres', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.ProgramaTrabalhoResumido', verbose_name='PTRES')),
                (
                    'responsavel_ug',
                    djtools.db.models.ForeignKeyPlus(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='tesouro_gerencial_documentoempenho_responsavel_ug',
                        to='tesouro_gerencial.UnidadeGestora',
                        verbose_name='UG Responsável',
                    ),
                ),
                (
                    'unidade_orcamentaria',
                    djtools.db.models.ForeignKeyPlus(
                        on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.ClassificacaoInstitucional', verbose_name='Unidade Orçamentaria'
                    ),
                ),
            ],
            options={'verbose_name': 'Documento de Empenho', 'verbose_name_plural': 'Documentos de Empenho'},
        ),
        migrations.CreateModel(
            name='DocumentoEmpenhoEspecifico',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'tipo',
                    djtools.db.models.CharFieldPlus(
                        blank=True, choices=[('Estagiários', 'Estagiários'), ('GECC', 'GECC'), ('Capacitação', 'Capacitação')], max_length=255, verbose_name='Tipo'
                    ),
                ),
                ('observacao', models.TextField(blank=True, verbose_name='Observação')),
                ('documento_empenho', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.DocumentoEmpenho')),
            ],
            options={'verbose_name': 'Documento de Empenho Específico', 'verbose_name_plural': 'Documentos de Empenho Específicos'},
        ),
        migrations.CreateModel(
            name='DocumentoEmpenhoItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor', djtools.db.models.DecimalFieldPlus(decimal_places=2, default=0, max_digits=12)),
                ('subitem_original', djtools.db.models.CharFieldPlus(max_length=2)),
                ('documento_empenho', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='tesouro_gerencial.DocumentoEmpenho')),
                ('subitem', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.SubElementoNaturezaDespesa')),
            ],
            options={'verbose_name': 'Item do Documento de Empenho', 'verbose_name_plural': 'Itens do Documento de Empenho', 'unique_together': {('documento_empenho', 'subitem')}},
        ),
        migrations.CreateModel(
            name='DocumentoLiquidacao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', djtools.db.models.CharFieldPlus(max_length=23, unique=True, verbose_name='Número')),
                (
                    'tipo',
                    djtools.db.models.CharFieldPlus(
                        choices=[
                            ('NE', 'Nota de Empenho'),
                            ('NS', 'Nota de Sistema'),
                            ('OB', 'Ordem Bancária'),
                            ('DF', 'Documento de Arrecadação da Receita Federal'),
                            ('DR', 'Documento de Arrecadação Municipal/Estadual'),
                            ('GP', 'Guia de Recolhimento da Previdência Social'),
                            ('GR', 'Guia de recolhimento da União'),
                        ],
                        max_length=2,
                        verbose_name='Tipo',
                    ),
                ),
                ('data_emissao', djtools.db.models.DateFieldPlus(verbose_name='Data de Emissão')),
                ('observacao', models.TextField(verbose_name='Observação')),
                ('favorecido_codigo', djtools.db.models.CharFieldPlus(max_length=14)),
                ('favorecido_nome', djtools.db.models.CharFieldPlus(max_length=255)),
                ('acao_governo_original', djtools.db.models.CharFieldPlus(max_length=4)),
                ('fonte_recurso_original', djtools.db.models.CharFieldPlus(max_length=10)),
                ('naturesa_despesa_original', djtools.db.models.CharFieldPlus(max_length=6)),
                ('grupo_despesa_original', djtools.db.models.CharFieldPlus(max_length=1)),
                ('acao_governo', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.AcaoGoverno')),
                (
                    'emitente_ug',
                    djtools.db.models.ForeignKeyPlus(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='tesouro_gerencial_documentoliquidacao_emitente_ug',
                        to='tesouro_gerencial.UnidadeGestora',
                        verbose_name='UG Emitente',
                    ),
                ),
                (
                    'esfera_orcamentaria',
                    djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.EsferaOrcamentaria', verbose_name='Esfera orçamentária'),
                ),
                (
                    'fonte_recurso',
                    djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.FonteRecurso', verbose_name='Fonte de recurso'),
                ),
                ('plano_interno', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.PlanoInterno')),
                ('ptres', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.ProgramaTrabalhoResumido', verbose_name='PTRES')),
                (
                    'responsavel_ug',
                    djtools.db.models.ForeignKeyPlus(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='tesouro_gerencial_documentoliquidacao_responsavel_ug',
                        to='tesouro_gerencial.UnidadeGestora',
                        verbose_name='UG Responsável',
                    ),
                ),
                (
                    'unidade_orcamentaria',
                    djtools.db.models.ForeignKeyPlus(
                        on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.ClassificacaoInstitucional', verbose_name='Unidade Orçamentaria'
                    ),
                ),
            ],
            options={'verbose_name': 'Documento de Liquidação', 'verbose_name_plural': 'Documentos de Liquidação'},
        ),
        migrations.CreateModel(
            name='DocumentoLiquidacaoItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor', djtools.db.models.DecimalFieldPlus(decimal_places=2, default=0, max_digits=12)),
                ('subitem_original', djtools.db.models.CharFieldPlus(max_length=2)),
                ('documento_empenho_inicial', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.DocumentoEmpenho')),
                (
                    'documento_liquidacao',
                    djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='tesouro_gerencial.DocumentoLiquidacao'),
                ),
                ('subitem', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.SubElementoNaturezaDespesa')),
            ],
            options={
                'verbose_name': 'Item do Documento de Liquidação',
                'verbose_name_plural': 'Itens do Documento de Liquidação',
                'unique_together': {('documento_liquidacao', 'subitem', 'documento_empenho_inicial')},
            },
        ),
        migrations.CreateModel(
            name='DocumentoPagamento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', djtools.db.models.CharFieldPlus(max_length=23, unique=True, verbose_name='Número')),
                (
                    'tipo',
                    djtools.db.models.CharFieldPlus(
                        choices=[
                            ('NE', 'Nota de Empenho'),
                            ('NS', 'Nota de Sistema'),
                            ('OB', 'Ordem Bancária'),
                            ('DF', 'Documento de Arrecadação da Receita Federal'),
                            ('DR', 'Documento de Arrecadação Municipal/Estadual'),
                            ('GP', 'Guia de Recolhimento da Previdência Social'),
                            ('GR', 'Guia de recolhimento da União'),
                        ],
                        max_length=2,
                        verbose_name='Tipo',
                    ),
                ),
                ('data_emissao', djtools.db.models.DateFieldPlus(verbose_name='Data de Emissão')),
                ('observacao', models.TextField(verbose_name='Observação')),
                ('favorecido_codigo', djtools.db.models.CharFieldPlus(max_length=14)),
                ('favorecido_nome', djtools.db.models.CharFieldPlus(max_length=255)),
                ('acao_governo_original', djtools.db.models.CharFieldPlus(max_length=4)),
                ('fonte_recurso_original', djtools.db.models.CharFieldPlus(max_length=10)),
                ('naturesa_despesa_original', djtools.db.models.CharFieldPlus(max_length=6)),
                ('grupo_despesa_original', djtools.db.models.CharFieldPlus(max_length=1)),
                ('acao_governo', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.AcaoGoverno')),
                (
                    'emitente_ug',
                    djtools.db.models.ForeignKeyPlus(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='tesouro_gerencial_documentopagamento_emitente_ug',
                        to='tesouro_gerencial.UnidadeGestora',
                        verbose_name='UG Emitente',
                    ),
                ),
                (
                    'esfera_orcamentaria',
                    djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.EsferaOrcamentaria', verbose_name='Esfera orçamentária'),
                ),
                (
                    'fonte_recurso',
                    djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.FonteRecurso', verbose_name='Fonte de recurso'),
                ),
                ('plano_interno', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.PlanoInterno')),
                ('ptres', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.ProgramaTrabalhoResumido', verbose_name='PTRES')),
                (
                    'responsavel_ug',
                    djtools.db.models.ForeignKeyPlus(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='tesouro_gerencial_documentopagamento_responsavel_ug',
                        to='tesouro_gerencial.UnidadeGestora',
                        verbose_name='UG Responsável',
                    ),
                ),
                (
                    'unidade_orcamentaria',
                    djtools.db.models.ForeignKeyPlus(
                        on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.ClassificacaoInstitucional', verbose_name='Unidade Orçamentaria'
                    ),
                ),
            ],
            options={'verbose_name': 'Documento de Pagamento', 'verbose_name_plural': 'Documentos de Pagamento'},
        ),
        migrations.CreateModel(
            name='DocumentoPagamentoItem',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor', djtools.db.models.DecimalFieldPlus(decimal_places=2, default=0, max_digits=12)),
                ('subitem_original', djtools.db.models.CharFieldPlus(max_length=2)),
                ('documento_empenho_inicial', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.DocumentoEmpenho')),
                (
                    'documento_pagamento',
                    djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='itens', to='tesouro_gerencial.DocumentoPagamento'),
                ),
                ('subitem', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='tesouro_gerencial.SubElementoNaturezaDespesa')),
            ],
            options={
                'verbose_name': 'Item do Documento de Pagamento',
                'verbose_name_plural': 'Itens do Documento de Pagamento',
                'unique_together': {('documento_pagamento', 'subitem', 'documento_empenho_inicial')},
            },
        ),
        migrations.RemoveField(model_name='documentoitem', name='documento'),
        migrations.RemoveField(model_name='documentoitem', name='subitem'),
        migrations.DeleteModel(name='Documento'),
        migrations.DeleteModel(name='DocumentoItem'),
    ]
