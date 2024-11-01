# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-14 15:05


from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models
import djtools.storages


class Migration(migrations.Migration):

    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ('rh', '0001_initial'), ('comum', '0002_auto_20190814_1443')]

    operations = [
        migrations.CreateModel(
            name='AbonoChefia',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField()),
                ('descricao', models.TextField(blank=True, max_length=200, verbose_name='Descrição')),
                (
                    'acao_abono',
                    models.PositiveIntegerField(
                        choices=[
                            [1, 'Abonado com compensação de horário'],
                            [2, 'Abonado sem compensação de horário'],
                            [0, 'Não abonado'],
                            [7, 'Tempo de trabalho excedente para compensação de carga-horária (até o limite de 10h de trabalho por dia)'],
                            [4, 'Hora extra justificada (até o limite de 10h de trabalho por dia)'],
                            [3, 'Hora extra não justificada'],
                            [6, 'Trabalho no fim de semana autorizado para compensação de carga horária'],
                            [8, 'Trabalho no fim de semana autorizado como hora extra'],
                            [5, 'Trabalho no fim de semana não justificado/autorizado'],
                        ],
                        default=0,
                        verbose_name='Ação chefia imediata',
                    ),
                ),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, null=True)),
                ('ultima_atualizacao', models.DateTimeField(auto_now=True)),
                (
                    'vinculo_chefe_imediato',
                    djtools.db.models.ForeignKeyPlus(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='vinculo_chefe_imediato_set', to='comum.Vinculo'),
                ),
                ('vinculo_pessoa', djtools.db.models.ForeignKeyPlus(editable=False, on_delete=django.db.models.deletion.CASCADE, to='comum.Vinculo')),
            ],
            options={'verbose_name': 'Abono Chefia', 'verbose_name_plural': 'Abono Chefia'},
        ),
        migrations.CreateModel(
            name='Afastamento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_ini', models.DateField(db_index=True, verbose_name='Data Inicial')),
                ('data_fim', models.DateField(db_index=True, null=True, verbose_name='Data Final')),
                ('descricao', models.TextField(max_length=200, verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Afastamento', 'verbose_name_plural': 'Afastamentos'},
        ),
        migrations.CreateModel(
            name='DocumentoAnexo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField(db_index=True)),
                ('descricao', models.TextField(max_length=200, verbose_name='Descrição')),
                (
                    'anexo',
                    djtools.db.models.PrivateFileField(
                        help_text='O formato do arquivo deve ser ".pdf", ".jpeg", ".jpg" ou ".png"',
                        storage=djtools.storages.get_private_storage(),
                        upload_to='ponto/anexos',
                        verbose_name='Anexo',
                    ),
                ),
                ('pessoa', djtools.db.models.ForeignKeyPlus(editable=False, on_delete=django.db.models.deletion.CASCADE, to='rh.Pessoa')),
            ],
            options={'verbose_name': 'Anexo', 'verbose_name_plural': 'Anexos'},
        ),
        migrations.CreateModel(
            name='Frequencia',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('horario', models.DateTimeField(db_index=True)),
                ('acao', models.CharField(max_length=1, verbose_name='Ação')),
                ('online', models.BooleanField(default=True)),
            ],
            options={
                'verbose_name': 'Frequência',
                'verbose_name_plural': 'Frequências',
                'db_table': 'frequencia',
                'permissions': (
                    ('pode_ver_frequencia_propria', 'Pode ver frequência própria'),
                    ('pode_ver_frequencias_enquanto_foi_chefe', 'Pode ver frequência de quando foi chefe'),
                    ('pode_ver_frequencia_campus', 'Pode ver frequência de campus'),
                    ('pode_ver_frequencia_todos', 'Pode ver frequência de todos'),
                    ('pode_ver_frequencia_estagiarios', 'Pode ver frequências de estagiários'),
                    ('pode_ver_frequencia_bolsistas', 'Pode ver frequências de bolsistas'),
                    ('pode_ver_frequencia_terceirizados_propria', 'Pode ver frequência própria como terceirizado'),
                    ('pode_ver_frequencia_terceirizados_setor', 'Pode ver frequências de terceirizados'),
                    ('pode_ver_frequencia_terceirizados_campus', 'Pode ver frequências de terceirizados'),
                    ('pode_ver_frequencia_terceirizados_todos', 'Pode ver frequências de terceirizados'),
                    ('pode_ver_frequencia_extra_noturna', 'Pode ver frequência extra noturna'),
                    ('pode_ver_frequencia_por_cargo', 'Pode ver frequência por cargo'),
                    ('eh_gerente_sistemico_ponto', 'É gerente sistêmico de ponto'),
                ),
            },
        ),
        migrations.CreateModel(
            name='HorarioCompensacao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_compensacao', djtools.db.models.DateFieldPlus(help_text='Dia no qual há uma carga horária excedente.', verbose_name='Data da Compensação/Saldo')),
                ('data_aplicacao', djtools.db.models.DateFieldPlus(help_text='Dia no qual há um débito de carga horária.', verbose_name='Data do Débito')),
                ('ch_compensada', djtools.db.models.TimeFieldPlus(help_text='Formato: HH:MM.', verbose_name='Carga Horária Compensada')),
                ('observacoes', models.TextField(blank=True, null=True, verbose_name='Observações')),
                ('situacao', models.IntegerField(choices=[[1, 'Válido'], [2, 'Invalidado/Sem Efeito']], default=1, editable=False, verbose_name='Situação')),
            ],
            options={
                'verbose_name': 'Informe de Compensação de Horário',
                'verbose_name_plural': 'Informes de Compensação de Horário',
                'ordering': ('funcionario', '-data_aplicacao', '-data_compensacao'),
            },
        ),
        migrations.CreateModel(
            name='Liberacao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_inicio', models.DateField(db_index=True, verbose_name='Data Início')),
                ('data_fim', models.DateField(db_index=True, null=True, verbose_name='Data Fim')),
                ('descricao', models.TextField(max_length=200, verbose_name='Descrição')),
                (
                    'tipo',
                    models.PositiveIntegerField(
                        choices=[[0, 'Por Documento Legal'], [1, 'Evento/Data Comemorativa'], [2, 'Recesso'], [3, 'Feriado'], [4, 'Feriado Recorrente'], [5, 'Liberação Parcial']],
                        default=0,
                        verbose_name='Tipo Liberação',
                    ),
                ),
                (
                    'ch_maxima_exigida',
                    models.IntegerField(
                        default=0,
                        help_text="Somente para o tipo 'Liberação Parcial'. É a carga horária máxima que será exigida no(s) dia(s) do período informado.",
                        verbose_name='Carga horária máxima exigida pela instituição (em horas) ',
                    ),
                ),
                (
                    'uo',
                    djtools.db.models.ForeignKeyPlus(
                        blank=True,
                        help_text='Define onde será aplicada a liberação.',
                        null=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        to='rh.UnidadeOrganizacional',
                        verbose_name='Unidade Organizacional',
                    ),
                ),
            ],
            options={'verbose_name': 'Liberação', 'verbose_name_plural': 'Liberações'},
        ),
        migrations.CreateModel(
            name='Maquina',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=30, verbose_name='Descrição')),
                ('ip', models.GenericIPAddressField(unique=True, verbose_name='IP')),
                (
                    'porta_servico',
                    models.PositiveIntegerField(
                        blank=True, help_text='Porta do serviço disponibilizado pela máquina. Use caso seja servidor de impressão.', null=True, verbose_name='Porta Serviço'
                    ),
                ),
                (
                    'ativo',
                    models.NullBooleanField(default=None, help_text='Caso seja desconhecido, a máquina ainda não foi aceita pelo administrador do SUAP.', verbose_name='Ativa'),
                ),
                ('cliente_cadastro_impressao_digital', models.BooleanField(default=False, verbose_name='Cadastro de Impressões Digitais')),
                ('cliente_chaves', models.BooleanField(default=False, verbose_name='Terminal de Chaves')),
                ('cliente_ponto', models.BooleanField(default=False, verbose_name='Terminal de Ponto Eletrônico')),
                ('cliente_refeitorio', models.BooleanField(default=False, verbose_name='Terminal de Refeitório')),
                (
                    'servidor_impressao',
                    models.BooleanField(default=False, help_text='A máquina será utilizada para impressão de comprovantes do protocolo.', verbose_name='Servidor de Impressão'),
                ),
                (
                    'texto_final_impressao',
                    models.TextField(
                        blank=True,
                        help_text='Preencha esse campo caso tenha marcado a opção anterior e deseja que algum texto seja impresso ao final do comprovante. Ex: Ou ligue para  (XX) XXXX-XXX',
                        null=True,
                    ),
                ),
                ('observacao', models.TextField(blank=True, null=True, verbose_name='Observação')),
                ('ultimo_log', models.DateTimeField(blank=True, null=True)),
                ('predios', models.ManyToManyField(blank=True, to='comum.Predio')),
                ('uo', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.UnidadeOrganizacional', verbose_name='Campus')),
                (
                    'usuarios',
                    models.ManyToManyField(
                        blank=True,
                        help_text='Usuários que poderão usar os serviços da máquina. Use caso seja servidor de impressão.',
                        to=settings.AUTH_USER_MODEL,
                        verbose_name='Usuários',
                    ),
                ),
            ],
            options={'verbose_name': 'Máquina', 'verbose_name_plural': 'Máquinas', 'db_table': 'maquina'},
        ),
        migrations.CreateModel(
            name='MaquinaLog',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('status', djtools.db.models.PositiveIntegerFieldPlus(choices=[[0, 'Sucesso'], [1, 'Erro'], [2, 'Alerta']], default=0, verbose_name='Status')),
                ('operacao', models.CharField(max_length=255, verbose_name='Operação')),
                ('mensagem', models.TextField(blank=True, null=True, verbose_name='Mensagem')),
                ('horario', models.DateTimeField(auto_now=True, verbose_name='Horário')),
                ('maquina', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='ponto.Maquina', verbose_name='Máquina')),
            ],
            options={'verbose_name': 'Log de Máquina', 'verbose_name_plural': 'Logs de Máquinas', 'ordering': ['maquina', 'operacao']},
        ),
        migrations.CreateModel(
            name='Observacao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', models.DateField(db_index=True)),
                ('descricao', models.TextField(verbose_name='Descrição')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, null=True)),
                ('vinculo', djtools.db.models.ForeignKeyPlus(editable=False, on_delete=django.db.models.deletion.CASCADE, to='comum.Vinculo')),
            ],
            options={'verbose_name': 'Observação', 'verbose_name_plural': 'Observações'},
        ),
        migrations.CreateModel(
            name='RecessoDia',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data', djtools.db.models.DateFieldPlus(verbose_name='Dia do Recesso')),
            ],
            options={'verbose_name': 'Dia a Compensar', 'verbose_name_plural': 'Dias a Compensar', 'ordering': ('data',)},
        ),
        migrations.CreateModel(
            name='RecessoDiaEscolhido',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('dia', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='ponto.RecessoDia', verbose_name='Dia de Recesso')),
            ],
            options={'verbose_name': 'Dia Escolhido do Recesso', 'verbose_name_plural': 'Dias Escolhidos do Recesso', 'ordering': ('dia__data',)},
        ),
        migrations.CreateModel(
            name='RecessoOpcao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo', models.IntegerField(choices=[[1, 'Recesso Natal/Ano Novo'], [2, 'Outro']], default=2, verbose_name='Tipo')),
                ('descricao', models.TextField(verbose_name='Descrição')),
                ('periodo_de_escolha_data_inicial', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data de Início para o Período de Escolhas')),
                ('periodo_de_escolha_data_final', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data de Término para o Período de Escolhas')),
                (
                    'situacao',
                    models.IntegerField(
                        choices=[[1, 'Em Fase de Cadastro'], [2, 'Aberto para Escolha dos Dias do Recesso'], [3, 'Concluído Cadastramento']],
                        default=1,
                        editable=False,
                        verbose_name='Situação',
                    ),
                ),
                (
                    'qtde_max_dias_escolhidos',
                    djtools.db.models.PositiveIntegerFieldPlus(
                        blank=True, default=0, help_text='Número máximo de Dias que podem ser escolhidos', verbose_name='Quantidade de Dias a Escolher'
                    ),
                ),
                (
                    'publico_alvo_campi',
                    djtools.db.models.ManyToManyFieldPlus(blank=True, related_name='publico_alvo_campi', to='rh.UnidadeOrganizacional', verbose_name='Público alvo - Campi'),
                ),
                (
                    'publico_alvo_servidores',
                    djtools.db.models.ManyToManyFieldPlus(blank=True, related_name='publico_alvo_servidores', to='rh.Servidor', verbose_name='Público alvo - Servidores'),
                ),
                (
                    'responsavel',
                    djtools.db.models.ForeignKeyPlus(editable=False, on_delete=django.db.models.deletion.CASCADE, to='rh.Servidor', verbose_name='Responsável pelo Cadastro'),
                ),
            ],
            options={'verbose_name': 'Opção de Compensação', 'verbose_name_plural': 'Opções de Compensação'},
        ),
        migrations.CreateModel(
            name='RecessoOpcaoEscolhida',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_escolha', models.DateField(auto_now_add=True, verbose_name='Data da Escolha')),
                (
                    'validacao',
                    models.IntegerField(
                        choices=[[1, 'Aguardando'], [2, 'Autorizado'], [4, 'Não Autorizado - Remarcar Novamente'], [3, 'Não Autorizado']], default=1, verbose_name='Validação'
                    ),
                ),
                ('motivo_nao_autorizacao', models.TextField(blank=True, null=True, verbose_name='Motivo da Não Autorização (se for o caso)')),
                ('dias_efetivos_a_compensar_cache', models.TextField(blank=True, editable=False, null=True, verbose_name='')),
                ('pode_validar_apos_prazo', models.BooleanField(default=False, verbose_name='Liberado para validação após término do prazo')),
                (
                    'funcionario',
                    djtools.db.models.ForeignKeyPlus(
                        editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='funcionario_recesso', to='rh.Servidor', verbose_name='Servidor'
                    ),
                ),
                (
                    'recesso_opcao',
                    djtools.db.models.ForeignKeyPlus(editable=False, on_delete=django.db.models.deletion.CASCADE, to='ponto.RecessoOpcao', verbose_name='Compensação'),
                ),
                (
                    'validador',
                    djtools.db.models.ForeignKeyPlus(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='validador_recesso', to='rh.Servidor', verbose_name='Validador'
                    ),
                ),
            ],
            options={'verbose_name': 'Acompanhamento de Compensação', 'verbose_name_plural': 'Acompanhamentos de Compensações'},
        ),
        migrations.CreateModel(
            name='RecessoPeriodoCompensacao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_inicial', djtools.db.models.DateFieldPlus(verbose_name='Data Inicial')),
                ('data_final', djtools.db.models.DateFieldPlus(verbose_name='Data Final')),
                (
                    'recesso_opcao',
                    djtools.db.models.ForeignKeyPlus(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='periodos_de_compensacao', to='ponto.RecessoOpcao'),
                ),
            ],
            options={'verbose_name': 'Período de Compensação', 'verbose_name_plural': 'Períodos de Compensação'},
        ),
        migrations.CreateModel(
            name='TipoAfastamento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.TextField(max_length=200, verbose_name='Descrição')),
                ('codigo', models.CharField(blank=True, max_length=5, null=True)),
            ],
            options={'verbose_name': 'Tipo de Afastamento', 'verbose_name_plural': 'Tipos de Afastamento'},
        ),
        migrations.CreateModel(
            name='VersaoTerminal',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('numero', models.CharField(max_length=5, unique=True, verbose_name='Número de Versão')),
            ],
            options={'abstract': False},
        ),
        migrations.CreateModel(
            name='RecessoCompensacao',
            fields=[
                (
                    'horariocompensacao_ptr',
                    models.OneToOneField(
                        auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='ponto.HorarioCompensacao'
                    ),
                )
            ],
            options={'verbose_name': 'Informe de Compensação de Horário de Recesso', 'verbose_name_plural': 'Informes de Compensação de Horário de Recessos'},
            bases=('ponto.horariocompensacao',),
        ),
        migrations.AddField(
            model_name='recessodiaescolhido',
            name='recesso_opcao_escolhida',
            field=djtools.db.models.ForeignKeyPlus(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='dias_escolhidos', to='ponto.RecessoOpcaoEscolhida'),
        ),
        migrations.AddField(
            model_name='recessodia',
            name='recesso_opcao',
            field=djtools.db.models.ForeignKeyPlus(editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='dias_do_recesso', to='ponto.RecessoOpcao'),
        ),
        migrations.AddField(
            model_name='maquina',
            name='versao_terminal',
            field=djtools.db.models.ForeignKeyPlus(
                blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='ponto.VersaoTerminal', verbose_name='Versão do Terminal'
            ),
        ),
        migrations.AddField(
            model_name='horariocompensacao',
            name='abono_na_data_aplicacao',
            field=djtools.db.models.ForeignKeyPlus(
                blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='abono_na_data_aplicacao', to='ponto.AbonoChefia'
            ),
        ),
        migrations.AddField(
            model_name='horariocompensacao',
            name='abono_na_data_compensacao',
            field=djtools.db.models.ForeignKeyPlus(
                blank=True, editable=False, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='abono_na_data_compensacao', to='ponto.AbonoChefia'
            ),
        ),
        migrations.AddField(
            model_name='horariocompensacao',
            name='chefe',
            field=djtools.db.models.ForeignKeyPlus(
                blank=True,
                editable=False,
                help_text='Chefe Imediato na Data da Compensação',
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name='chefe_compensacao_horario',
                to='rh.Servidor',
                verbose_name='Chefe Imediato',
            ),
        ),
        migrations.AddField(
            model_name='horariocompensacao',
            name='funcionario',
            field=djtools.db.models.ForeignKeyPlus(
                editable=False, on_delete=django.db.models.deletion.CASCADE, related_name='funcionario_compensacao_horario', to='rh.Servidor', verbose_name='Funcionário'
            ),
        ),
        migrations.AddField(model_name='frequencia', name='maquina', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='ponto.Maquina')),
        migrations.AddField(
            model_name='frequencia', name='vinculo', field=djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.Vinculo')
        ),
        migrations.AddField(
            model_name='afastamento',
            name='tipo',
            field=djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='ponto.TipoAfastamento'),
        ),
        migrations.AddField(model_name='afastamento', name='vinculo', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='comum.Vinculo')),
        migrations.AlterUniqueTogether(name='recessodia', unique_together=set([('data', 'recesso_opcao')])),
        migrations.AddField(
            model_name='recessocompensacao',
            name='dia_escolhido',
            field=djtools.db.models.ForeignKeyPlus(editable=False, on_delete=django.db.models.deletion.CASCADE, to='ponto.RecessoDiaEscolhido'),
        ),
        migrations.AlterUniqueTogether(name='frequencia', unique_together=set([('vinculo', 'horario')])),
        migrations.AlterUniqueTogether(name='abonochefia', unique_together=set([('vinculo_pessoa', 'data')])),
    ]
