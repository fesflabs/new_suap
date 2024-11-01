# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-14 14:54


from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [('rh', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='CargoPublicoAcumulavel',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('orgao_lotacao', models.CharField(blank=True, max_length=255, verbose_name='Orgão de Lotação')),
                ('uf', models.CharField(blank=True, max_length=5, verbose_name='UF')),
                ('cargo_que_ocupa', models.CharField(blank=True, max_length=255, verbose_name='Cargo/Emprego/Função que ocupa')),
                ('jornada_trabalho', models.CharField(blank=True, max_length=255, verbose_name='Jornada de trabalho do cargo/emprego/função')),
                ('nivel_escolaridade', djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Nível de escolaridade do cargo/emprego/função')),
                ('data_ingresso_orgao', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data de ingresso no orgão')),
                (
                    'situacao',
                    djtools.db.models.CharFieldPlus(blank=True, help_text='Quadro ou Tabela: Permanente, Temporário, Comissionado, etc.', max_length=255, verbose_name='Situação'),
                ),
                ('remuneracao', djtools.db.models.CharFieldPlus(blank=True, help_text='Vencimentos, Salários, Proventos, etc.', max_length=255, verbose_name='Da Remuneração')),
                (
                    'natureza_orgao',
                    djtools.db.models.CharFieldPlus(
                        blank=True, help_text='Administração Direta, Autarquia, Empresa Pública ou Sociedade de Economia Mista', max_length=255, verbose_name='Natureza do Órgão'
                    ),
                ),
                ('subordinacao', djtools.db.models.CharFieldPlus(blank=True, help_text='Ministério, Secretaria de Estado/Município', max_length=255, verbose_name='Subordinação')),
                ('esfera_governo', djtools.db.models.CharFieldPlus(blank=True, help_text='Federal, Estadual ou Municipal', max_length=255, verbose_name='Esfera do Governo')),
                (
                    'area_atuacao_cargo',
                    djtools.db.models.CharFieldPlus(blank=True, help_text='Técnica/Científica, Saúde ou Magistério', max_length=255, verbose_name='Área de atuação do cargo'),
                ),
            ],
            options={
                'verbose_name': 'Anexo I - Informações de Cargo/Emprego/Função ocupado em outro órgão',
                'verbose_name_plural': 'Anexo I - Informações de Cargo/Emprego/Função ocupado em outro órgão',
            },
        ),
        migrations.CreateModel(
            name='DeclaracaoAcumulacaoCargo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                (
                    'nao_possui_outro_vinculo',
                    models.BooleanField(
                        default=False,
                        verbose_name='Não possuo qualquer outro vínculo ativo com a administração pública direta ou indireta nas esferas federal, estadual, distrital ou municipal, nem percebo proventos de aposentadoria, reforma ou pensão de nenhum órgão ou entidade da administração pública.',
                    ),
                ),
                (
                    'tem_outro_cargo_acumulavel',
                    models.BooleanField(
                        default=False,
                        verbose_name='Ocupo cargo público acumulável com compatibilidade de horários com o vínculo assumido com o IFRN, conforme disposto no Anexo I.',
                    ),
                ),
                (
                    'tem_aposentadoria',
                    models.BooleanField(default=False, verbose_name='Percebo proventos de aposentadoria devidamente acumuláveis com o cargo assumido no IFRN, conforme Anexo II.'),
                ),
                ('tem_pensao', models.BooleanField(default=False, verbose_name='Sou beneficiário de pensão, conforme informações prestadas em Anexo III.')),
                (
                    'tem_atuacao_gerencial',
                    models.BooleanField(default=False, verbose_name='Tenho atuação gerencial em atividade mercantil, conforme informações prestadas em Anexo IV.'),
                ),
                (
                    'exerco_atividade_remunerada_privada',
                    models.BooleanField(default=False, verbose_name='Exerço atividade remunerada privada, conforme informações prestadas em Anexo V.'),
                ),
                ('data_cadastro', djtools.db.models.DateTimeFieldPlus(auto_now_add=True, null=True)),
            ],
            options={
                'verbose_name': 'Declaração de Acumulação de Cargos',
                'verbose_name_plural': 'Declaração de Acumulação de Cargos',
                'ordering': ['servidor__nome'],
                'permissions': (('pode_ver_declaracao', 'Pode ver Declaração'),),
            },
        ),
        migrations.CreateModel(
            name='ExerceAtividadeRemuneradaPrivada',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome_empresa_trabalha', djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Nome da empresa onde trabalha/Empregador')),
                ('funcao_emprego_ocupado', djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Função ou emprego ocupado(tipo de atividade desempenhada)')),
                ('jornada_trabalho', djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Jornada de trabalho semanal a que está submetido')),
                ('nivel_escolaridade_funcao', djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Nível de escolaridade da função/emprego')),
                ('data_inicio_atividade', djtools.db.models.DateFieldPlus(blank=True, max_length=255, null=True, verbose_name='Data de início da atividade remunerada privada')),
                ('nao_exerco_atividade_remunerada', models.BooleanField(default=False, blank=True, verbose_name='NÃO exerço qualquer atividade remunerada privada')),
                ('declaracao', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='acumulocargo.DeclaracaoAcumulacaoCargo')),
            ],
            options={'verbose_name': 'Anexo V - Informações sobre atividade remunerada privada', 'verbose_name_plural': 'Anexo V - Informações sobre atividade remunerada privada'},
        ),
        migrations.CreateModel(
            name='PeriodoDeclaracaoAcumuloCargos',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=255, verbose_name='Descrição')),
                ('publico', models.IntegerField(choices=[[0, 'Geral'], [1, 'Técnicos'], [2, 'Docentes']], verbose_name='Público')),
                ('ano', models.IntegerField()),
                ('data_inicio', models.DateField(verbose_name='Data de Início')),
                ('data_fim', models.DateField(verbose_name='Data de Término')),
                ('campus', djtools.db.models.ManyToManyFieldPlus(blank=True, to='rh.UnidadeOrganizacional', verbose_name='Campus')),
            ],
            options={'verbose_name': 'Questionário de Acúmulo de Cargos', 'verbose_name_plural': 'Questionários de Acúmulo de Cargos'},
        ),
        migrations.CreateModel(
            name='TemAposentadoria',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('cargo_origem_aposentadoria', models.CharField(blank=True, max_length=255, verbose_name='Cargo que deu origem à aposentadoria')),
                ('uf', models.CharField(blank=True, max_length=5, verbose_name='UF')),
                ('fundamento_legal', models.CharField(blank=True, max_length=255, verbose_name='Fundamento legal da aposentadoria')),
                ('ato_legal', models.CharField(blank=True, max_length=255, verbose_name='Ato legal da aposentadoria')),
                ('jornada_trabalho', djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Jornada de trabalho do cargo que exerceu')),
                ('nivel_escolaridade', djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Nível de escolaridade do cargo/emprego/função')),
                ('data_vigencia', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data de vigência da aposentadoria')),
                (
                    'area_atuacao_cargo',
                    djtools.db.models.CharFieldPlus(blank=True, help_text='Técnica/Científica, Saúde ou Magistério', max_length=255, verbose_name='Área de atuação do cargo'),
                ),
                (
                    'natureza_orgao',
                    djtools.db.models.CharFieldPlus(
                        blank=True, help_text='Administração Direta, Autarquia, Empresa Pública ou Sociedade de Economia Mista', max_length=255, verbose_name='Natureza do Órgão'
                    ),
                ),
                ('subordinacao', djtools.db.models.CharFieldPlus(blank=True, help_text='Ministério, Secretaria de Estado/Município', max_length=255, verbose_name='Subordinação')),
                ('esfera_governo', djtools.db.models.CharFieldPlus(blank=True, help_text='Federal, Estadual ou Municipal', max_length=255, verbose_name='Esfera do Governo')),
                ('declaracao', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='acumulocargo.DeclaracaoAcumulacaoCargo')),
            ],
            options={'verbose_name': 'Anexo II - Informações de Aposentadoria em outro órgão', 'verbose_name_plural': 'Anexo II - Informações de Aposentadoria em outro órgão'},
        ),
        migrations.CreateModel(
            name='TemAtuacaoGerencial',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('empresa_que_atua', djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Empresa em que atua')),
                ('tipo_atuacao_gerencial', djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Tipo de atuação gerencial')),
                ('tipo_sociedade_mercantil', djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Tipo de sociedade mercantil')),
                ('descricao_atividade_exercida', djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Descrição da atividade comercial exercida')),
                ('qual_participacao_societaria', djtools.db.models.CharFieldPlus(blank=True, max_length=255, verbose_name='Qual a participação societária')),
                ('data_inicio_atuacao', djtools.db.models.DateFieldPlus(blank=True, max_length=255, null=True, verbose_name='Data de início da atuação')),
                ('nao_exerco_atuacao_gerencial', models.BooleanField(default=False, blank=True, verbose_name='NÃO exerço qualquer atuação gerencial em atividade mercantil')),
                ('nao_exerco_comercio', models.BooleanField(default=False, blank=True, verbose_name='NÃO exerço comércio')),
                ('declaracao', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='acumulocargo.DeclaracaoAcumulacaoCargo')),
            ],
            options={
                'verbose_name': 'Anexo IV - Informações sobre atuação gerencial em atividades mercantil',
                'verbose_name_plural': 'Anexo IV - Informações sobre atuação gerencial em atividades mercantil',
            },
        ),
        migrations.CreateModel(
            name='TemPensao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_pensao', models.CharField(blank=True, max_length=255, verbose_name='Tipo de pensão')),
                ('fundamento_legal', models.CharField(blank=True, max_length=255, verbose_name='Fundamento legal da pensão')),
                ('grau_parentesco', models.CharField(blank=True, max_length=255, verbose_name='Grau de parentesco com o instituidor de pensão')),
                ('data_inicio_concessao', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data de início de concessão do benefício')),
                (
                    'dependencia_economica',
                    djtools.db.models.CharFieldPlus(
                        blank=True, help_text='Certidão de casamento, nascimento, declaração de IR, etc', max_length=255, verbose_name='Dependência econômica'
                    ),
                ),
                ('declaracao', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='acumulocargo.DeclaracaoAcumulacaoCargo')),
            ],
            options={
                'verbose_name': 'Anexo III - Informações sobre Pensão Civil em outro órgão',
                'verbose_name_plural': 'Anexo III - Informações sobre Pensão Civil em outro órgão',
            },
        ),
        migrations.AddField(
            model_name='declaracaoacumulacaocargo',
            name='periodo_declaracao_acumulo_cargo',
            field=djtools.db.models.ForeignKeyPlus(
                on_delete=django.db.models.deletion.CASCADE, to='acumulocargo.PeriodoDeclaracaoAcumuloCargos', verbose_name='Período de Declaração de Acumulação de Cargo'
            ),
        ),
        migrations.AddField(
            model_name='declaracaoacumulacaocargo',
            name='servidor',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.Servidor', verbose_name='Servidor'),
        ),
        migrations.AddField(
            model_name='cargopublicoacumulavel',
            name='declaracao',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='acumulocargo.DeclaracaoAcumulacaoCargo'),
        ),
        migrations.AlterUniqueTogether(name='declaracaoacumulacaocargo', unique_together=set([('servidor', 'periodo_declaracao_acumulo_cargo')])),
    ]
