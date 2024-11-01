# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-09-10 13:43


from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models
import djtools.middleware.threadlocals


class Migration(migrations.Migration):

    initial = True

    dependencies = [('rh', '0002_auto_20190902_1545'), migrations.swappable_dependency(settings.AUTH_USER_MODEL), ('comum', '0002_auto_20190814_1443')]

    operations = [
        migrations.CreateModel(
            name='ArquivoMeta',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_importacao', djtools.db.models.DateTimeFieldPlus(auto_now_add=True, null=True, verbose_name='Data da Importação')),
                ('arquivo', djtools.db.models.FileFieldPlus(upload_to='', verbose_name='Arquivo')),
                (
                    'usuario',
                    djtools.db.models.CurrentUserField(
                        blank=True,
                        default=djtools.middleware.threadlocals.get_user,
                        editable=False,
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Usuário',
                    ),
                ),
            ],
            options={'verbose_name': 'Arquivo Meta e Real', 'verbose_name_plural': 'Arquivo de Metas e Reais'},
        ),
        migrations.CreateModel(
            name='EtapaProjeto',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=50, verbose_name='Descrição')),
                ('data_inicio', models.DateField(verbose_name='Data Inicial')),
                ('data_fim', models.DateField(verbose_name='Data Final')),
                ('objetivo_etapa', models.CharField(max_length=100, null=True, verbose_name='Objetivo')),
                ('responsaveis_etapa', models.CharField(max_length=100, null=True, verbose_name='Responsáveis')),
                ('meta_etapa', models.CharField(max_length=50, null=True, verbose_name='Meta da Etapa')),
                ('unidade_medida', models.CharField(max_length=50, null=True, verbose_name='Unidade de Medida')),
                ('valor_etapa', models.DecimalField(decimal_places=2, max_digits=9, null=True, verbose_name='Valor da Etapa')),
            ],
            options={'verbose_name': 'Etapa do Projeto', 'verbose_name_plural': 'Etapas dos Projetos'},
        ),
        migrations.CreateModel(
            name='Indicador',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sigla', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Sigla')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Descrição')),
                ('finalidade', models.TextField(blank=True, verbose_name='Finalidade')),
                ('forma_calculo', models.CharField(max_length=100, verbose_name='Forma de Cálculo')),
                ('casas_decimais', models.PositiveIntegerField(choices=[(0, 0), (1, 1), (2, 2), (3, 3), (4, 4)], default=0, verbose_name='Casas decimais')),
                (
                    'tendencia',
                    models.CharField(
                        choices=[('Quanto mais melhor', 'Quanto mais melhor'), ('Quanto menos melhor', 'Quanto menos melhor')],
                        default='Quanto mais melhor',
                        max_length=20,
                        verbose_name='Tendência',
                    ),
                ),
                (
                    'tipo',
                    djtools.db.models.CharFieldPlus(choices=[('Percentual', 'Percentual'), ('Absoluto', 'Absoluto')], default='Absoluto', max_length=255, verbose_name='Tipo'),
                ),
            ],
            options={'verbose_name': 'Indicador', 'verbose_name_plural': 'Indicadores'},
        ),
        migrations.CreateModel(
            name='MetaIndicador',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ano', models.PositiveIntegerField(verbose_name='Ano')),
                ('meta', djtools.db.models.DecimalFieldPlus(decimal_places=4, max_digits=12, null=True, verbose_name='Meta do Ano')),
            ],
            options={'verbose_name': 'Meta', 'verbose_name_plural': 'Metas', 'ordering': ['ano']},
        ),
        migrations.CreateModel(
            name='ObjetivoEstrategico',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sigla', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Sigla')),
                ('descricao', models.TextField(verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Objetivo Estratégico', 'verbose_name_plural': 'Objetivos Estratégicos'},
        ),
        migrations.CreateModel(
            name='ObjetivoIndicador',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('relevancia', models.PositiveIntegerField(default=0, verbose_name='Relevância')),
            ],
            options={'verbose_name': 'Relevância', 'verbose_name_plural': 'Relevâncias'},
        ),
        migrations.CreateModel(
            name='PDI',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('documento', models.FileField(max_length=255, upload_to='plan_estrategico/anexos/', verbose_name='Documento PDI')),
                ('valor_faixa_verde', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Valor Inicial da Faixa Verde')),
                ('valor_faixa_amarela', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Valor Inicial da Faixa Amarela')),
                ('valor_faixa_vermelha', models.DecimalField(decimal_places=2, default=0, max_digits=12, verbose_name='Valor Inicial da Faixa Vermelha ')),
                (
                    'ano_final_pdi',
                    djtools.db.models.ForeignKeyPlus(
                        help_text='Vigência final do PDI',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='ano_final_pdi_plan_estrategico',
                        to='comum.Ano',
                        verbose_name='Ano Final',
                    ),
                ),
                (
                    'ano_inicial_pdi',
                    djtools.db.models.ForeignKeyPlus(
                        help_text='Vigência inicial do PDI',
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name='ano_inicial_pdi_plan_estrategico',
                        to='comum.Ano',
                        verbose_name='Ano Inicial',
                    ),
                ),
            ],
            options={'verbose_name': 'PDI', 'verbose_name_plural': 'PDIs'},
        ),
        migrations.CreateModel(
            name='PDIIndicador',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'tipo',
                    djtools.db.models.CharFieldPlus(
                        choices=[('Percentual', 'Percentual'), ('Inteiro', 'Inteiro'), ('Decimal', 'Decimal')], default='Percentual', max_length=255, verbose_name='Tipo'
                    ),
                ),
                ('valor_referencia', djtools.db.models.DecimalFieldPlus(decimal_places=4, max_digits=12, null=True, verbose_name='Valor Referência')),
                ('indicador', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.Indicador')),
            ],
            options={'verbose_name': 'Indicador no PDI', 'verbose_name_plural': 'Indicadores no PDI'},
        ),
        migrations.CreateModel(
            name='PDIObjetivoEstrategico',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('objetivo', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.ObjetivoEstrategico')),
                ('pdi', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.PDI')),
            ],
            options={'verbose_name': 'Objetivo Estratégico do PDI', 'verbose_name_plural': 'Objetivos Estratégicos do PDI'},
        ),
        migrations.CreateModel(
            name='PDIPerspectiva',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('pdi', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='perspectivas', to='plan_estrategico.PDI', verbose_name='PDI')),
            ],
            options={'verbose_name': 'Perspectiva do PDI', 'verbose_name_plural': 'Perspectivas do PDI'},
        ),
        migrations.CreateModel(
            name='Perspectiva',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sigla', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Sigla')),
                ('nome', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Perspectiva', 'verbose_name_plural': 'Perspectivas'},
        ),
        migrations.CreateModel(
            name='PlanoAtividade',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_geral_inicial', djtools.db.models.DateFieldPlus(verbose_name='Início da Vigência')),
                ('data_geral_final', djtools.db.models.DateFieldPlus(verbose_name='Fim da Vigência')),
                ('data_orcamentario_preloa_inicial', djtools.db.models.DateFieldPlus(verbose_name='Início do Cadastro Orçamentário Pré-LOA')),
                ('data_orcamentario_preloa_final', djtools.db.models.DateFieldPlus(verbose_name='Fim do Cadastro Orçamentário Pré-LOA')),
                ('data_projetos_preloa_inicial', djtools.db.models.DateFieldPlus(verbose_name='Início do Cadastro de Projetos Pré-LOA')),
                ('data_projetos_preloa_final', djtools.db.models.DateFieldPlus(verbose_name='Fim do Cadastro de Projetos Pré-LOA')),
                ('data_atividades_preloa_inicial', djtools.db.models.DateFieldPlus(verbose_name='Início do Cadastro de Atividades Pré-LOA')),
                ('data_atividades_preloa_final', djtools.db.models.DateFieldPlus(verbose_name='Fim do Cadastro de Atividades Pré-LOA')),
                ('data_orcamentario_posloa_inicial', djtools.db.models.DateFieldPlus(verbose_name='Início do Cadastro Orçamentário Pós-LOA')),
                ('data_orcamentario_posloa_final', djtools.db.models.DateFieldPlus(verbose_name='Fim do Cadastro Orçamentário Pós-LOA')),
                ('data_projetos_posloa_inicial', djtools.db.models.DateFieldPlus(verbose_name='Início do Cadastro de Projeto Pós-LOA')),
                ('data_projetos_posloa_final', djtools.db.models.DateFieldPlus(verbose_name='Fim do Cadastro de Projeto Pós-LOA')),
                ('data_atividades_posloa_inicial', djtools.db.models.DateFieldPlus(verbose_name='Início do Cadastro de Atividades Pós-LOA')),
                ('data_atividades_posloa_final', djtools.db.models.DateFieldPlus(verbose_name='Fim do Cadastro de Atividades Pós-LOA')),
                ('ano_base', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='comum.Ano', verbose_name='Ano Base')),
                ('pdi', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.PDI')),
            ],
            options={'verbose_name': 'Plano de Atividade', 'verbose_name_plural': 'Planos de Atividades', 'ordering': ('ano_base',)},
        ),
        migrations.CreateModel(
            name='ProjetoEstrategico',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(max_length=100, verbose_name='Nome do Projeto')),
                ('descricao', models.TextField(verbose_name='Descrição')),
                ('recurso_total', models.DecimalField(decimal_places=2, max_digits=9, verbose_name='Recurso Total')),
                ('meta_projeto', models.CharField(max_length=50, verbose_name='Meta do Projeto')),
                ('unidade_medida', models.CharField(max_length=50, verbose_name='Unidade de Medida')),
                ('data_inicio', models.DateField(verbose_name='Data Inicial')),
                ('data_fim', models.DateField(verbose_name='Data Final')),
                ('anexo', models.FileField(max_length=255, upload_to='plan_estrategico/anexos/', verbose_name='Projeto Estratégico')),
                ('objetivo_estrategico', models.ManyToManyField(to='plan_estrategico.PDIObjetivoEstrategico', verbose_name='Objetivo Estratégico')),
                ('pdi', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.PDI', verbose_name='PDI')),
            ],
            options={'verbose_name': 'Projeto Estratégico', 'verbose_name_plural': 'Projetos Estratégicos'},
        ),
        migrations.CreateModel(
            name='UnidadeGestora',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.CharField(choices=[('Diretoria Sistêmica', 'Diretoria Sistêmica'), ('Pró-Reitoria', 'Pró-Reitoria')], max_length=20, verbose_name='Tipo')),
                ('pdi', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.PDI')),
                (
                    'setor_equivalente',
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='unidadegestora_setor', to='rh.Setor', verbose_name='Setor Equivalente'),
                ),
            ],
            options={'verbose_name': 'Unidade Gestora', 'verbose_name_plural': 'Unidades Gestoras', 'ordering': ('tipo', 'setor_equivalente__nome')},
        ),
        migrations.CreateModel(
            name='Variavel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('sigla', models.CharField(help_text='A sigla é utilizada na fórmula dos indicadores', max_length=50)),
                ('nome', models.CharField(max_length=100)),
                ('descricao', models.TextField(max_length=1000, verbose_name='Descrição')),
                ('fonte', models.CharField(help_text='Origem do dado', max_length=255)),
            ],
            options={'verbose_name': 'Variável', 'verbose_name_plural': 'Variáveis'},
        ),
        migrations.CreateModel(
            name='VariavelCampus',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('valor_ideal', models.DecimalField(decimal_places=4, max_digits=15, null=True, verbose_name='Valor Meta')),
                ('valor_real', models.DecimalField(decimal_places=4, max_digits=15, null=True, verbose_name='Valor Real')),
                ('ano', models.PositiveIntegerField(verbose_name='Ano')),
                ('data_atualizacao', djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Data da Importação')),
                ('uo', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.UnidadeOrganizacional', verbose_name='Unidade Administrativa')),
                ('variavel', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.Variavel', verbose_name='Variavel')),
            ],
            options={'verbose_name': 'Variável Campus/Ano', 'verbose_name_plural': 'Variáveis Campus/Ano'},
        ),
        migrations.AddField(
            model_name='projetoestrategico',
            name='unidade_gestora',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.UnidadeGestora', verbose_name='Unidade Gestora'),
        ),
        migrations.AddField(
            model_name='pdiperspectiva',
            name='perspectiva',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.Perspectiva', verbose_name='Perspectiva'),
        ),
        migrations.AddField(
            model_name='pdiobjetivoestrategico',
            name='pdi_perspectiva',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.PDIPerspectiva', verbose_name='Perspectiva'),
        ),
        migrations.AddField(model_name='pdiindicador', name='objetivos', field=models.ManyToManyField(to='plan_estrategico.PDIObjetivoEstrategico')),
        migrations.AddField(model_name='pdiindicador', name='pdi', field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.PDI')),
        migrations.AddField(
            model_name='objetivoindicador',
            name='indicador',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.PDIIndicador', verbose_name='Indicador'),
        ),
        migrations.AddField(
            model_name='objetivoindicador',
            name='objetivo_estrategico',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.PDIObjetivoEstrategico', verbose_name='Objetivo Estratégico'),
        ),
        migrations.AddField(
            model_name='metaindicador',
            name='indicador',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.PDIIndicador', verbose_name='Indicador'),
        ),
        migrations.AddField(
            model_name='etapaprojeto',
            name='projeto',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='plan_estrategico.ProjetoEstrategico', verbose_name='Projeto Estratégico'),
        ),
        migrations.AlterUniqueTogether(name='unidadegestora', unique_together=set([('pdi', 'setor_equivalente')])),
        migrations.AlterUniqueTogether(name='planoatividade', unique_together=set([('pdi', 'ano_base')])),
        migrations.AlterUniqueTogether(name='pdiperspectiva', unique_together=set([('pdi', 'perspectiva')])),
        migrations.AlterUniqueTogether(name='pdiobjetivoestrategico', unique_together=set([('pdi', 'objetivo')])),
        migrations.AlterUniqueTogether(name='pdiindicador', unique_together=set([('pdi', 'indicador')])),
        migrations.AlterUniqueTogether(name='pdi', unique_together=set([('ano_inicial_pdi', 'ano_final_pdi')])),
    ]
