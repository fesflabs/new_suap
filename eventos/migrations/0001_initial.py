# -*- coding: utf-8 -*-
# Generated by Django 1.11.23 on 2019-08-14 14:57


from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models
import djtools.middleware.threadlocals


class Migration(migrations.Migration):

    initial = True

    dependencies = [migrations.swappable_dependency(settings.AUTH_USER_MODEL), ('rh', '0001_initial')]

    operations = [
        migrations.CreateModel(
            name='AssuntoAtendimento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Assunto de Atendimento', 'verbose_name_plural': 'Assuntos de Atendimentos'},
        ),
        migrations.CreateModel(
            name='AtendimentoPublico',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data/Hora do Cadastro')),
                ('assunto', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='eventos.AssuntoAtendimento')),
                ('campus', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.UnidadeOrganizacional', verbose_name='Campus')),
            ],
            options={'verbose_name': 'Atendimento ao Público', 'verbose_name_plural': 'Atendimentos ao Público'},
        ),
        migrations.CreateModel(
            name='Banner',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', djtools.db.models.CharFieldPlus(max_length=1000, verbose_name='Título')),
                ('imagem', djtools.db.models.FileFieldPlus(upload_to='', verbose_name='Imagem')),
                ('tipo', djtools.db.models.CharFieldPlus(choices=[('Início', 'Início')], default='Início', max_length=100, verbose_name='Tipo')),
                ('link', djtools.db.models.CharFieldPlus(blank=True, max_length=1000, null=True, verbose_name='Link')),
                ('data_inicio', models.DateTimeField(verbose_name='Início da Publicação')),
                ('data_termino', models.DateTimeField(verbose_name='Término da Publicação')),
            ],
            options={'verbose_name': 'Banner', 'verbose_name_plural': 'Banners'},
        ),
        migrations.CreateModel(
            name='ClassificacaoEvento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=50, verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Classificação de Eventos', 'verbose_name_plural': 'Classificações de Eventos'},
        ),
        migrations.CreateModel(
            name='Evento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', models.CharField(db_index=True, max_length=255)),
                ('apresentacao', models.TextField(help_text='Espaço para que sejam falados os objetivos principais etc.', verbose_name='Apresentação')),
                ('imagem', models.ImageField(blank=True, help_text='Logotipo ou algo que ilustre o evento', null=True, upload_to='', verbose_name='Imagem')),
                ('local', djtools.db.models.CharFieldPlus(max_length=255)),
                ('data_inicio', djtools.db.models.DateFieldPlus(verbose_name='Data de Início')),
                ('hora_inicio', djtools.db.models.TimeFieldPlus(verbose_name='Hora de Início')),
                ('data_fim', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data de Fim')),
                ('hora_fim', djtools.db.models.TimeFieldPlus(blank=True, null=True, verbose_name='Hora de Fim')),
                ('carga_horaria', models.CharField(blank=True, max_length=255, null=True, verbose_name='Carga Horária')),
                ('servidores_envolvidos', models.PositiveIntegerField(blank=True, null=True, verbose_name='Quantidade de Servidores Envolvidos na Organização')),
                ('qtd_participantes', models.PositiveIntegerField(blank=True, null=True, verbose_name='Quantidade de Participantes')),
                ('recursos', djtools.db.models.DecimalFieldPlus(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Recursos Envolvidos')),
                ('site', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True)),
                (
                    'gera_certificado',
                    models.BooleanField(
                        verbose_name='Gera Certificado?',
                        blank=True,
                        help_text='Marque essa opção caso deseje que certificados sejam emitidos e enviados por e-mail para os participantes após a realização do evento.',
                    ),
                ),
                ('deferido', models.NullBooleanField(verbose_name='Deferido?')),
                ('motivo_indeferimento', models.TextField(blank=True, verbose_name='Motivo do Indeferimento')),
                ('data_emissao_certificado', models.DateTimeField(blank=True, null=True)),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo?')),
                ('ultima_atualizacao_em', djtools.db.models.DateTimeFieldPlus(auto_now=True)),
                (
                    'campus',
                    djtools.db.models.ForeignKeyPlus(
                        on_delete=django.db.models.deletion.CASCADE, related_name='campus_responsavel', to='rh.UnidadeOrganizacional', verbose_name='Campus Responsável'
                    ),
                ),
                (
                    'classificacao',
                    djtools.db.models.ForeignKeyPlus(
                        blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='eventos.ClassificacaoEvento', verbose_name='Classificação'
                    ),
                ),
                ('coordenador', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='rh.Servidor')),
            ],
            options={
                'verbose_name': 'Evento',
                'verbose_name_plural': 'Eventos',
                'permissions': (('pode_avaliar_evento', 'Pode avaliar evento'), ('pode_gerenciar_evento', 'Pode gerenciar evento')),
            },
        ),
        migrations.CreateModel(
            name='MotivoAtendimento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Motivo de Atendimento', 'verbose_name_plural': 'Motivos de Atendimentos'},
        ),
        migrations.CreateModel(
            name='Natureza',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=50, verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Natureza de Eventos', 'verbose_name_plural': 'Naturezas de Eventos'},
        ),
        migrations.CreateModel(
            name='Participante',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', djtools.db.models.CharFieldPlus(max_length=255)),
                ('email', models.EmailField(max_length=254)),
                ('data_cadastro', models.DateTimeField(auto_now_add=True)),
                ('certificado_enviado', models.BooleanField(default=False, verbose_name='Certificado Enviado')),
                ('codigo_geracao_certificado', djtools.db.models.CharFieldPlus(max_length=16, null=True)),
                ('evento', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='participantes', to='eventos.Evento')),
            ],
            options={'verbose_name': 'Participante', 'verbose_name_plural': 'Participantes'},
        ),
        migrations.CreateModel(
            name='PublicoAlvoEvento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=50, verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Público Alvo de Eventos', 'verbose_name_plural': 'Públicos Alvo de Eventos'},
        ),
        migrations.CreateModel(
            name='PublicoAtendimento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Público de Atendimento', 'verbose_name_plural': 'Públicos de Atendimentos'},
        ),
        migrations.CreateModel(
            name='SituacaoAtendimento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Situação de Atendimento', 'verbose_name_plural': 'Situações de Atendimentos'},
        ),
        migrations.CreateModel(
            name='TipoAtendimento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Tipo de Atendimento', 'verbose_name_plural': 'Tipos de Atendimentos'},
        ),
        migrations.CreateModel(
            name='TipoEvento',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', models.CharField(max_length=50, verbose_name='Descrição')),
            ],
            options={'verbose_name': 'Tipo de Eventos', 'verbose_name_plural': 'Tipos de Eventos'},
        ),
        migrations.AddField(model_name='evento', name='natureza', field=models.ManyToManyField(to='eventos.Natureza')),
        migrations.AddField(model_name='evento', name='publico_alvo', field=models.ManyToManyField(blank=True, to='eventos.PublicoAlvoEvento', verbose_name='Público Alvo')),
        migrations.AddField(
            model_name='evento',
            name='setor',
            field=djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='rh.Setor', verbose_name='Setor Responsável'),
        ),
        migrations.AddField(model_name='evento', name='tipo', field=models.ManyToManyField(to='eventos.TipoEvento')),
        migrations.AddField(
            model_name='evento',
            name='ultima_atualizacao_por',
            field=djtools.db.models.CurrentUserField(
                blank=True, default=djtools.middleware.threadlocals.get_user, editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL
            ),
        ),
        migrations.AddField(
            model_name='atendimentopublico', name='motivo', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='eventos.MotivoAtendimento')
        ),
        migrations.AddField(
            model_name='atendimentopublico',
            name='publico',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='eventos.PublicoAtendimento', verbose_name='Público'),
        ),
        migrations.AddField(
            model_name='atendimentopublico',
            name='situacao',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='eventos.SituacaoAtendimento', verbose_name='Situação'),
        ),
        migrations.AddField(
            model_name='atendimentopublico', name='tipo', field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='eventos.TipoAtendimento')
        ),
        # migrations.AlterUniqueTogether(name='participante', unique_together=set([('evento', 'email')])),
    ]
