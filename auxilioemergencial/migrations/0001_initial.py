# Generated by Django 2.2.10 on 2020-09-14 19:21

from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models
import djtools.storages


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('ae', '0006_auto_20200402_1114'),
        ('rh', '0014_auto_20200516_0227'),
        ('comum', '0008_auto_20200205_1500'),
        ('edu', '0028_auto_20200601_0703'),
    ]

    operations = [
        migrations.CreateModel(
            name='Edital',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=5000, verbose_name='Descrição')),
                ('data_inicio', djtools.db.models.DateTimeFieldPlus(verbose_name='Data de Início das Inscrições')),
                ('data_termino', djtools.db.models.DateTimeFieldPlus(verbose_name='Data de Término das Inscrições')),
                ('link_edital', djtools.db.models.CharFieldPlus(blank=True, max_length=1000, null=True, verbose_name='Link para o Edital')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
                ('campus', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='campus_periodoinscricao', to='rh.UnidadeOrganizacional', verbose_name='Campus')),
            ],
            options={
                'verbose_name': 'Edital Emergencial',
                'verbose_name_plural': 'Editais Emergenciais',
            },
        ),
        migrations.CreateModel(
            name='InscricaoAluno',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data')),
                ('telefones_contato', djtools.db.models.CharFieldPlus(max_length=500, verbose_name='Telefones de Contato')),
                ('emails_contato', djtools.db.models.CharFieldPlus(max_length=500, verbose_name='Emails de Contato')),
                ('tem_matricula_outro_instituto', models.BooleanField(default=False, verbose_name='Possui matrícula em outra Instituição de Ensino?')),
                ('foi_atendido_outro_instituto', models.BooleanField(default=False, verbose_name='Foi atendido por algum auxílio emergencial de inclusão digital ou auxílio semelhante em outra Instituição de Ensino?')),
                ('mora_com_pessoas_instituto', models.BooleanField(default=False, verbose_name='Você mora com outras pessoas que também estão matriculadas no IFRN?')),
                ('pessoas_do_domicilio', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Informe o(s) nome(s) completo(s) do(s) estudante(s) que moram com você:')),
                ('banco', models.CharField(max_length=50, null=True, verbose_name='Banco')),
                ('numero_agencia', models.CharField(help_text='Ex: 3293-X', max_length=50, null=True, verbose_name='Número da Agência')),
                ('tipo_conta', models.CharField(choices=[('Conta Corrente', 'Conta Corrente'), ('Conta Poupança', 'Conta Poupança')], max_length=50, null=True, verbose_name='Tipo da Conta')),
                ('numero_conta', models.CharField(help_text='Ex: 23384-6', max_length=50, null=True, verbose_name='Número da Conta')),
                ('operacao', models.CharField(blank=True, max_length=50, null=True, verbose_name='Operação')),
                ('cpf', models.CharField(max_length=20, null=True, verbose_name='CPF')),
                ('renda_bruta_familiar', djtools.db.models.DecimalFieldPlus(decimal_places=2, help_text='Considerar a soma de todos os rendimentos mensais da família sem os descontos.', max_digits=12, null=True, verbose_name='Renda Bruta Familiar R$')),
                ('renda_per_capita', djtools.db.models.DecimalFieldPlus(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Renda per Capita')),
                ('aluno', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='edu.Aluno', verbose_name='Aluno')),
            ],
            options={
                'verbose_name': 'Inscrição do Aluno',
                'verbose_name_plural': 'Inscrições do Aluno',
            },
        ),
        migrations.CreateModel(
            name='TipoAuxilio',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('titulo', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='Título')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=2000, null=True, verbose_name='Descrição')),
                ('ativo', models.BooleanField(default=True, verbose_name='Ativo')),
            ],
            options={
                'verbose_name': 'Tipo de Auxílio',
                'verbose_name_plural': 'Tipos de Auxílios',
            },
        ),
        migrations.CreateModel(
            name='IntegranteFamiliar',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nome', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='1. Nome')),
                ('data_nascimento', djtools.db.models.DateFieldPlus(null=True, verbose_name='2. Data de Nascimento')),
                ('idade', models.IntegerField(null=True, verbose_name='Idade')),
                ('parentesco', djtools.db.models.CharFieldPlus(max_length=255, verbose_name='3. Relação com o Aluno')),
                ('remuneracao', djtools.db.models.DecimalFieldPlus(decimal_places=2, max_digits=12, null=True, verbose_name='6. Renda Bruta* Mensal Média')),
                ('ultima_remuneracao', djtools.db.models.DecimalFieldPlus(decimal_places=2, max_digits=12, null=True, verbose_name='Última Remuneração')),
                ('data', models.DateTimeField(auto_now=True, null=True, verbose_name='Data')),
                ('id_inscricao', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Id da Inscrição')),
                ('aluno', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='edu.Aluno', verbose_name='Aluno')),
                ('estado_civil', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='ae.EstadoCivil', verbose_name='4. Estado Civil')),
                ('inscricao', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='auxilioemergencial.InscricaoAluno', verbose_name='Inscrição')),
                ('situacao_trabalho', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='ae.SituacaoTrabalho', verbose_name='5. Ocupação')),
            ],
            options={
                'verbose_name': 'Integrante Familiar',
                'verbose_name_plural': 'Integrantes Familiares',
            },
        ),
        migrations.CreateModel(
            name='InscricaoMaterialPedagogico',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data da Inscrição')),
                ('ultima_atualizacao', models.DateTimeField(null=True, verbose_name='Última Atualização')),
                ('descricao_material', djtools.db.models.CharFieldPlus(max_length=2000, verbose_name='Material didático pedagógico que deseja solicitar')),
                ('especificacao_material', djtools.db.models.CharFieldPlus(max_length=2000, verbose_name='Especificações do material didático pedagógico solicitado')),
                ('valor_solicitacao', djtools.db.models.DecimalFieldPlus(decimal_places=2, max_digits=6, verbose_name='Valor da Solicitação de Auxílio (Valor Máximo: R$ 400,00)')),
                ('justificativa_solicitacao', djtools.db.models.CharFieldPlus(max_length=5000, verbose_name='Justificativa para Solicitação')),
                ('situacao', djtools.db.models.CharFieldPlus(choices=[('Concluída', 'Concluída'), ('Pendente de assinatura do responsável', 'Pendente de assinatura do responsável')], default='Pendente de assinatura do responsável', max_length=100, verbose_name='Situação')),
                ('assinado_pelo_responsavel', models.BooleanField(default=False, verbose_name='Assinado pelo Responsável')),
                ('assinado_pelo_responsavel_em', djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Assinado pelo Responsável em')),
                ('parecer', djtools.db.models.CharFieldPlus(choices=[('Sem parecer', 'Sem parecer'), ('Deferido', 'Deferido'), ('Deferido, mas sem recurso disponível para atendimento no momento', 'Deferido, mas sem recurso disponível para atendimento no momento'), ('Pendente de documentação complementar', 'Pendente de documentação complementar'), ('Indeferido', 'Indeferido')], default='Sem parecer', max_length=100, verbose_name='Parecer')),
                ('data_parecer', models.DateTimeField(null=True, verbose_name='Data do Parecer')),
                ('documentacao_pendente', djtools.db.models.CharFieldPlus(max_length=2000, null=True, verbose_name='Indique qual documentação esse estudante deve anexar')),
                ('data_limite_envio_documentacao', djtools.db.models.DateFieldPlus(null=True, verbose_name='Indique a data limite para que o estudante anexe essa documentação')),
                ('valor_concedido', djtools.db.models.DecimalFieldPlus(decimal_places=2, max_digits=6, null=True, verbose_name='Valor Concedido')),
                ('termo_compromisso_assinado', models.BooleanField(default=False, verbose_name='Termo de Compromisso Assinado')),
                ('termo_compromisso_assinado_em', djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Termo de Compromisso Assinado em')),
                ('fim_auxilio', djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Fim do Auxílio')),
                ('aluno', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='edu.Aluno', verbose_name='Aluno')),
                ('autor_parecer', djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='autor_parecer_auxiliodidatico', to='comum.Vinculo', verbose_name='Autor do Parecer')),
                ('edital', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='auxilioemergencial.Edital', verbose_name='Edital')),
            ],
            options={
                'verbose_name': 'Inscrição de Auxílio para Material Didático Pedagógico',
                'verbose_name_plural': 'Inscrições de Auxílio para Material Didático Pedagógico',
            },
        ),
        migrations.CreateModel(
            name='InscricaoInternet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data da Inscrição')),
                ('ultima_atualizacao', models.DateTimeField(null=True, verbose_name='Última Atualização')),
                ('situacao_acesso_internet', djtools.db.models.CharFieldPlus(choices=[('NÃO possuo conexão própria à internet, dependo de redes de terceiros para me conectar.', 'NÃO possuo conexão própria à internet, dependo de redes de terceiros para me conectar.'), ('Possuo conexão própria com a internet, mas meu acesso é limitado, instável, ou de baixa capacidade, preciso de outra rede melhor para acesso rápido.', 'Possuo conexão própria com a internet, mas meu acesso é limitado, instável, ou de baixa capacidade, preciso de outra rede melhor para acesso rápido.'), ('Possuo conexão própria com a internet e adequada para o acompanhamento das aulas e atividades remotas.', 'Possuo conexão própria com a internet e adequada para o acompanhamento das aulas e atividades remotas.')], max_length=1000, verbose_name='Quanto a minha situação de acesso à internet necessário as aulas remotas, declaro que')),
                ('justificativa_solicitacao', djtools.db.models.CharFieldPlus(max_length=5000, verbose_name='Justificativa para Solicitação')),
                ('valor_solicitacao', djtools.db.models.DecimalFieldPlus(decimal_places=2, max_digits=6, verbose_name='Valor da Solicitação de Auxílio (Valor Máximo: R$ 100,00)')),
                ('situacao', djtools.db.models.CharFieldPlus(choices=[('Concluída', 'Concluída'), ('Pendente de assinatura do responsável', 'Pendente de assinatura do responsável')], default='Pendente de assinatura do responsável', max_length=100, verbose_name='Situação')),
                ('assinado_pelo_responsavel', models.BooleanField(default=False, verbose_name='Assinado pelo Responsável')),
                ('assinado_pelo_responsavel_em', djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Assinado pelo Responsável em')),
                ('parecer', djtools.db.models.CharFieldPlus(choices=[('Sem parecer', 'Sem parecer'), ('Deferido', 'Deferido'), ('Deferido, mas sem recurso disponível para atendimento no momento', 'Deferido, mas sem recurso disponível para atendimento no momento'), ('Pendente de documentação complementar', 'Pendente de documentação complementar'), ('Indeferido', 'Indeferido')], default='Sem parecer', max_length=100, verbose_name='Parecer')),
                ('data_parecer', models.DateTimeField(null=True, verbose_name='Data do Parecer')),
                ('valor_concedido', djtools.db.models.DecimalFieldPlus(decimal_places=2, max_digits=6, null=True, verbose_name='Valor Concedido')),
                ('documentacao_pendente', djtools.db.models.CharFieldPlus(max_length=2000, null=True, verbose_name='Indique qual documentação esse estudante deve anexar')),
                ('data_limite_envio_documentacao', djtools.db.models.DateFieldPlus(null=True, verbose_name='Indique a data limite para que o estudante anexe essa documentação')),
                ('termo_compromisso_assinado', models.BooleanField(default=False, verbose_name='Termo de Compromisso Assinado')),
                ('termo_compromisso_assinado_em', djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Termo de Compromisso Assinado em')),
                ('fim_auxilio', djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Fim do Auxílio')),
                ('aluno', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='edu.Aluno', verbose_name='Aluno')),
                ('autor_parecer', djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='autor_parecer_auxiliointernet', to='comum.Vinculo', verbose_name='Autor do Parecer')),
                ('edital', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='auxilioemergencial.Edital', verbose_name='Edital')),
            ],
            options={
                'verbose_name': 'Inscrição para Auxílio de Serviço de Internet',
                'verbose_name_plural': 'Inscrições para Auxílio de Serviço de Internet',
            },
        ),
        migrations.CreateModel(
            name='InscricaoDispositivo',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, verbose_name='Data da Inscrição')),
                ('ultima_atualizacao', models.DateTimeField(null=True, verbose_name='Última Atualização')),
                ('situacao_equipamento', djtools.db.models.CharFieldPlus(choices=[('NÃO possuo equipamentos (tablet ou computador).', 'NÃO possuo equipamentos (tablet ou computador).'), ('Possuo equipamento (tablet ou computador), mas com configuração inferior às descritas como básicas neste Edital.', 'Possuo equipamento (tablet ou computador), mas com configuração inferior às descritas como básicas neste Edital.'), ('Na minha residência existe um equipamento (tablet ou computador) com as configurações básicas descritas neste Edital, mas é compartilhado ou pertence a outro membro da família.', 'Na minha residência existe um equipamento (tablet ou computador) com as configurações básicas descritas neste Edital, mas é compartilhado ou pertence a outro membro da família.'), ('Possuo equipamento (tablet ou computador) com configurações básicas adequadas conforme descritas neste Edital ou de capacidade superior.', 'Possuo equipamento (tablet ou computador) com configurações básicas adequadas conforme descritas neste Edital ou de capacidade superior.')], max_length=1000, verbose_name='Declaro quanto ao equipamento que')),
                ('justificativa_solicitacao', djtools.db.models.CharFieldPlus(max_length=5000, verbose_name='Justificativa para Solicitação')),
                ('valor_solicitacao', djtools.db.models.DecimalFieldPlus(decimal_places=2, max_digits=6, verbose_name='Valor da Solicitação de Auxílio (Valor Máximo: R$ 1.500,00)')),
                ('situacao', djtools.db.models.CharFieldPlus(choices=[('Concluída', 'Concluída'), ('Pendente de assinatura do responsável', 'Pendente de assinatura do responsável')], default='Pendente de assinatura do responsável', max_length=100, verbose_name='Situação')),
                ('assinado_pelo_responsavel', models.BooleanField(default=False, verbose_name='Assinado pelo Responsável')),
                ('assinado_pelo_responsavel_em', djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Assinado pelo Responsável em')),
                ('parecer', djtools.db.models.CharFieldPlus(choices=[('Sem parecer', 'Sem parecer'), ('Deferido', 'Deferido'), ('Deferido, mas sem recurso disponível para atendimento no momento', 'Deferido, mas sem recurso disponível para atendimento no momento'), ('Pendente de documentação complementar', 'Pendente de documentação complementar'), ('Indeferido', 'Indeferido')], default='Sem parecer', max_length=100, verbose_name='Parecer')),
                ('data_parecer', models.DateTimeField(null=True, verbose_name='Data do Parecer')),
                ('valor_concedido', djtools.db.models.DecimalFieldPlus(decimal_places=2, max_digits=6, null=True, verbose_name='Valor Concedido')),
                ('documentacao_pendente', djtools.db.models.CharFieldPlus(max_length=2000, null=True, verbose_name='Indique qual documentação esse estudante deve anexar')),
                ('data_limite_envio_documentacao', djtools.db.models.DateFieldPlus(null=True, verbose_name='Indique a data limite para que o estudante anexe essa documentação')),
                ('termo_compromisso_assinado', models.BooleanField(default=False, verbose_name='Termo de Compromisso Assinado')),
                ('termo_compromisso_assinado_em', djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Termo de Compromisso Assinado em')),
                ('fim_auxilio', djtools.db.models.DateTimeFieldPlus(null=True, verbose_name='Fim do Auxílio')),
                ('aluno', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='edu.Aluno', verbose_name='Aluno')),
                ('autor_parecer', djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='autor_parecer_auxiliodispositivo', to='comum.Vinculo', verbose_name='Autor do Parecer')),
                ('edital', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='auxilioemergencial.Edital', verbose_name='Edital')),
            ],
            options={
                'verbose_name': 'Inscrição de Auxílio para Aquisição de Dispositivo Eletrônico',
                'verbose_name_plural': 'Inscrições de Auxílio para Aquisição de Dispositivo Eletrônico',
            },
        ),
        migrations.AddField(
            model_name='edital',
            name='tipo_auxilio',
            field=djtools.db.models.ManyToManyFieldPlus(to='auxilioemergencial.TipoAuxilio', verbose_name='Tipos de Auxílio'),
        ),
        migrations.CreateModel(
            name='DocumentoAluno',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('descricao', djtools.db.models.CharFieldPlus(max_length=1000, verbose_name='Descrição')),
                ('arquivo', djtools.db.models.PrivateFileField(max_length=255, storage=djtools.storages.get_private_storage(), upload_to='auxilioemergencial/inscricao/documentos', verbose_name='Arquivo')),
                ('data_cadastro', models.DateTimeField(auto_now_add=True, null=True, verbose_name='Data')),
                ('aluno', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='edu.Aluno', verbose_name='Aluno')),
                ('cadastrado_por', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.Vinculo', verbose_name='Responsável pela Cadastro')),
            ],
            options={
                'verbose_name': 'Documentos da Inscrição do Aluno',
                'verbose_name_plural': 'Documentos das Inscrições dos Alunos',
            },
        ),
    ]