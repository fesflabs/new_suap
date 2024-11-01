# Generated by Django 3.2.5 on 2022-07-31 19:58

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='DocumentoProcessoBarramento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('conteudo_arquivo', models.BinaryField(blank=True, null=True)),
                ('ordem', models.PositiveIntegerField(verbose_name='Ordem Documento')),
                ('hash_para_barramento', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Hash do Documento para Barramento')),
                ('enviado', models.BooleanField(default=False, verbose_name='Enviado')),
                ('recebido', models.BooleanField(default=False, verbose_name='Recebido')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='HipoteseLegalPEN',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('id_hipotese_legal_pen', models.PositiveIntegerField(unique=True, verbose_name='ID Hipotese Legal - PEN')),
                ('nome', djtools.db.models.CharFieldPlus(blank=True, max_length=200, null=True, verbose_name='Nome')),
                ('descricao', models.TextField(null=True, verbose_name='Descrição')),
                ('base_legal', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Base Legal')),
                ('status', models.BooleanField(default=True, verbose_name='Status')),
                ('hipotese_padrao', models.BooleanField(default=False, verbose_name='Hipotese Padrão')),
            ],
            options={
                'verbose_name': 'Hipótese Legal - PEN',
                'verbose_name_plural': 'Hipóteses Legais - PEN',
                'ordering': ('descricao',),
            },
        ),
        migrations.CreateModel(
            name='MapeamentoTiposDocumento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('tipo_para_recebimento_suap', models.BooleanField(default=False, verbose_name='Tipo para recebimento no SUAP?')),
            ],
            options={
                'verbose_name': 'Mapeamento de Tipo de Documento para o Barramento - PEN',
                'verbose_name_plural': 'Mapeamentos de Tipos de Documentos para o Barramento - PEN',
                'ordering': ('tipo_doc_barramento_pen__nome',),
            },
        ),
        migrations.CreateModel(
            name='ProcessoBarramento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nre_barramento_pen', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Número de Registro do Processo no Barramento PEN')),
                ('criado_no_suap', models.BooleanField(default=True, verbose_name='Criado no SUAP')),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TipoDocumentoPEN',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('id_tipo_doc_pen', models.PositiveIntegerField(unique=True, verbose_name='ID Tipo Documento PEN')),
                ('nome', djtools.db.models.CharFieldPlus(max_length=200, verbose_name='Descrição')),
                ('observacao', djtools.db.models.CharFieldPlus(max_length=300, verbose_name='Observação')),
            ],
            options={
                'verbose_name': 'Tipo de Documento do Barramento PEN',
                'verbose_name_plural': 'Tipos de Documentos do Barramento PEN',
                'ordering': ('nome',),
            },
        ),
        migrations.CreateModel(
            name='TramiteBarramento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_hora_encaminhamento', models.DateTimeField(auto_now_add=True, verbose_name='Data de Encaminhamento')),
                ('documentos', models.JSONField(null=True)),
                ('qtd_documentos', models.PositiveIntegerField(null=True, verbose_name='Quantidade Documentos')),
                ('metadados_processo', models.JSONField(null=True)),
                ('status', models.PositiveIntegerField(choices=[[1, 'Pendente de Envio'], [2, 'Pendente de Recebimento'], [3, 'Enviado'], [4, 'Recebido'], [5, 'Recusado'], [6, 'Cancelado']], verbose_name='Status')),
                ('retorno_situacao', djtools.db.models.CharFieldPlus(max_length=500, null=True, verbose_name='Retorno da situação')),
                ('id_tramite_barramento', djtools.db.models.PositiveIntegerFieldPlus(null=True, verbose_name='Id Tramite Barramento')),
                ('destinatario_externo_repositorio_id', djtools.db.models.PositiveIntegerFieldPlus(null=True, verbose_name='Id Repositório Destinatário')),
                ('destinatario_externo_repositorio_descricao', djtools.db.models.CharFieldPlus(max_length=500, null=True, verbose_name='Descrição Repositório Destinatário')),
                ('destinatario_externo_estrutura_id', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Id Estrutura Destinatário')),
                ('destinatario_externo_estrutura_descricao', djtools.db.models.CharFieldPlus(max_length=500, null=True, verbose_name='Descrição Estrutura Destinatário')),
                ('remetente_externo_repositorio_id', djtools.db.models.PositiveIntegerFieldPlus(null=True, verbose_name='Id Repositório Remetente')),
                ('remetente_externo_repositorio_descricao', djtools.db.models.CharFieldPlus(max_length=500, null=True, verbose_name='Descrição Repositório Remetente')),
                ('remetente_externo_estrutura_id', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Id Estrutura Remetente')),
                ('remetente_externo_estrutura_descricao', djtools.db.models.CharFieldPlus(max_length=500, null=True, verbose_name='Descrição Estrutura Remetente')),
                ('tramite_externo_recibo_envio_json', models.JSONField(null=True)),
                ('tramite_externo_recibo_conclusao_json', models.JSONField(null=True)),
                ('componentes_digitais_a_receber', models.JSONField(null=True)),
                ('processo_barramento', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='processos_suap_barramento', to='conectagov_pen.processobarramento', verbose_name='Processo Barramento')),
            ],
            options={
                'verbose_name': 'Trâmite Externo de Processo Eletrônico',
                'verbose_name_plural': 'Trâmites Externos de Processos Eletrônicos',
                'ordering': ('data_hora_encaminhamento',),
                'permissions': (('pode_tramitar_pelo_barramento', 'Pode Tramitar Processos Eletrônicos pelo Barramento'),),
            },
        ),
    ]
