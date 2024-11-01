# Generated by Django 3.2.5 on 2022-09-29 21:18

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import djtools.db.models
import djtools.storages.storage
import djtools.thumbs


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0051_merge_20220929_0741'),
        ('rh', '0043_servidor_numero_registro'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('ppe', '0002_unidadelotacao'),
    ]

    operations = [
        migrations.CreateModel(
            name='SequencialMatriculaTrabalhadorEducando',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('prefixo', djtools.db.models.CharFieldPlus(max_length=255)),
                ('contador', models.PositiveIntegerField()),
            ],
            options={
                'abstract': False,
            },
        ),
        migrations.CreateModel(
            name='TrabalhadorEducando',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('matricula', djtools.db.models.CharFieldPlus(db_index=True, max_length=255, verbose_name='Matrícula')),
                ('foto', djtools.thumbs.ImageWithThumbsField(blank=True, null=True, storage=djtools.storages.storage.FileSystemStoragePlus(), upload_to='trabalhadoreseducandos')),
                ('estado_civil', djtools.db.models.CharFieldPlus(choices=[['Solteiro', 'Solteiro'], ['Casado', 'Casado'], ['União Estável', 'União Estável'], ['Divorciado', 'Divorciado'], ['Viúvo', 'Viúvo']], max_length=255, null=True)),
                ('numero_dependentes', djtools.db.models.PositiveIntegerFieldPlus(null=True, verbose_name='Número de Dependentes')),
                ('logradouro', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Logradouro')),
                ('numero', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Número')),
                ('complemento', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Complemento')),
                ('bairro', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Bairro')),
                ('cep', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='CEP')),
                ('tipo_zona_residencial', djtools.db.models.CharFieldPlus(choices=[['1', 'Urbana'], ['2', 'Rural']], max_length=255, null=True, verbose_name='Zona Residencial')),
                ('logradouro_profissional', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Logradouro Profissional')),
                ('numero_profissional', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Número Profissional')),
                ('complemento_profissional', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Complemento Profissional')),
                ('bairro_profissional', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Bairro Profissional')),
                ('cep_profissional', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='CEP Profissional')),
                ('tipo_zona_residencial_profissional', djtools.db.models.CharFieldPlus(blank=True, choices=[['1', 'Urbana'], ['2', 'Rural']], max_length=255, null=True, verbose_name='Zona Residencial Profissional')),
                ('telefone_profissional', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Telefone Profissional')),
                ('nome_pai', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Nome do Pai')),
                ('estado_civil_pai', djtools.db.models.CharFieldPlus(blank=True, choices=[['Solteiro', 'Solteiro'], ['Casado', 'Casado'], ['União Estável', 'União Estável'], ['Divorciado', 'Divorciado'], ['Viúvo', 'Viúvo']], max_length=255, null=True)),
                ('pai_falecido', models.BooleanField(default=False, verbose_name='Pai é falecido?')),
                ('nome_mae', djtools.db.models.CharFieldPlus(max_length=255, null=True, verbose_name='Nome da Mãe')),
                ('estado_civil_mae', djtools.db.models.CharFieldPlus(blank=True, choices=[['Solteiro', 'Solteiro'], ['Casado', 'Casado'], ['União Estável', 'União Estável'], ['Divorciado', 'Divorciado'], ['Viúvo', 'Viúvo']], max_length=255, null=True)),
                ('mae_falecida', models.BooleanField(default=False, verbose_name='Mãe é falecida?')),
                ('responsavel', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Nome do Responsável')),
                ('email_responsavel', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Email do Responsável')),
                ('parentesco_responsavel', djtools.db.models.CharFieldPlus(blank=True, choices=[['Pai/Mãe', 'Pai/Mãe'], ['Avô/Avó', 'Avô/Avó'], ['Tio/Tia', 'Tio/Tia'], ['Sobrinho/Sobrinha', 'Sobrinho/Sobrinha'], ['Outro', 'Outro']], max_length=255, null=True, verbose_name='Parentesco do Responsável')),
                ('cpf_responsavel', djtools.db.models.BrCpfField(blank=True, max_length=14, null=True, verbose_name='CPF do Responsável')),
                ('autorizacao_carteira_estudantil', models.BooleanField(default=False, help_text='O aluno autoriza o envio de seus dados pessoais para o Sistema Brasileiro de Educação (SEB) para fins de emissão da carteira de estudante digital de acordo com a Medida Provisória Nº 895, de 6 de setembro de 2019', verbose_name='Autorização para Emissão da Carteira Estudantil')),
                ('telefone_principal', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Telefone Principal')),
                ('telefone_secundario', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Telefone Secundário')),
                ('telefone_adicional_1', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Telefone do Responsável')),
                ('telefone_adicional_2', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Telefone do Responsável')),
                ('facebook', models.URLField(blank=True, null=True, verbose_name='Facebook')),
                ('instagram', models.URLField(blank=True, null=True, verbose_name='Instagram')),
                ('twitter', models.URLField(blank=True, null=True, verbose_name='Twitter')),
                ('linkedin', models.URLField(blank=True, null=True, verbose_name='Linkedin')),
                ('skype', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Skype')),
                ('tipo_sanguineo', djtools.db.models.CharFieldPlus(blank=True, choices=[['O-', 'O-'], ['O+', 'O+'], ['A-', 'A-'], ['A+', 'A+'], ['B-', 'B-'], ['B+', 'B+'], ['AB-', 'AB-'], ['AB+', 'AB+']], max_length=255, null=True, verbose_name='Tipo Sanguíneo')),
                ('nacionalidade', djtools.db.models.CharFieldPlus(choices=[['Brasileira', 'Brasileira'], ['Brasileira - Nascido no exterior ou naturalizado', 'Brasileira - Nascido no exterior ou naturalizado'], ['Estrangeira', 'Estrangeira']], max_length=255, null=True, verbose_name='Nacionalidade')),
                ('passaporte', djtools.db.models.CharFieldPlus(default='', max_length=50, verbose_name='Nº do Passaporte')),
                ('tipo_necessidade_especial', djtools.db.models.CharFieldPlus(blank=True, choices=[['1', 'Baixa Visão'], ['11', 'Cegueira'], ['2', 'Deficiência Auditiva'], ['3', 'Deficiência Física'], ['4', 'Deficiência Intelectual'], ['5', 'Deficiência Múltipla'], ['22', 'Surdez'], ['222', 'Surdocegueira']], max_length=255, null=True, verbose_name='Tipo de Necessidade Especial')),
                ('tipo_transtorno', djtools.db.models.CharFieldPlus(blank=True, choices=[['1', 'Autismo'], ['2', 'Síndrome de Asperger'], ['3', 'Síndrome de Rett'], ['4', 'Transtorno Desintegrativo da Infância']], max_length=255, null=True, verbose_name='Tipo de Transtorno')),
                ('superdotacao', djtools.db.models.CharFieldPlus(blank=True, choices=[['1', 'Altas habilidades/Superdotação']], max_length=255, null=True, verbose_name='Superdotação')),
                ('tipo_instituicao_origem', djtools.db.models.CharFieldPlus(blank=True, choices=[['Pública', 'Pública'], ['Privada', 'Privada']], max_length=255, null=True, verbose_name='Tipo de Instituição')),
                ('nome_instituicao_anterior', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Nome da Instituição')),
                ('habilitacao_pedagogica', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Habilitação para Curso de Formação Pedagógica')),
                ('numero_rg', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Número do RG')),
                ('data_emissao_rg', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data de Emissão')),
                ('numero_titulo_eleitor', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Título de Eleitor')),
                ('zona_titulo_eleitor', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Zona')),
                ('secao', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Seção')),
                ('data_emissao_titulo_eleitor', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data de Emissão')),
                ('numero_carteira_reservista', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Número da Carteira de Reservista')),
                ('regiao_carteira_reservista', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Região')),
                ('serie_carteira_reservista', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Série')),
                ('ano_carteira_reservista', models.PositiveIntegerField(blank=True, null=True, verbose_name='Ano')),
                ('tipo_certidao', djtools.db.models.CharFieldPlus(blank=True, choices=[['1', 'Nascimento'], ['2', 'Casamento']], max_length=255, null=True, verbose_name='Tipo de Certidão')),
                ('cartorio', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Cartório')),
                ('numero_certidao', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Número de Termo')),
                ('folha_certidao', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Folha')),
                ('livro_certidao', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Livro')),
                ('data_emissao_certidao', djtools.db.models.DateFieldPlus(blank=True, null=True, verbose_name='Data de Emissão')),
                ('matricula_certidao', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Matrícula')),
                ('data_matricula', djtools.db.models.DateTimeFieldPlus(auto_now_add=True, verbose_name='Data da Matrícula')),
                ('cota_sistec', djtools.db.models.CharFieldPlus(blank=True, choices=[['1', 'Escola Pública'], ['2', 'Cor/Raça'], ['3', 'Olimpíada'], ['4', 'Indígena'], ['5', 'Necessidades Especiais'], ['6', 'Zona Rural'], ['7', 'Quilombola'], ['8', 'Assentamento'], ['9', 'Não se aplica']], max_length=255, null=True, verbose_name='Cota SISTEC')),
                ('cota_mec', djtools.db.models.CharFieldPlus(blank=True, choices=[['1', 'Seleção Geral'], ['2', 'Oriundo de escola pública, com renda superior a 1,5 S.M. e declarado preto, pardo ou indígena (PPI)'], ['3', 'Oriundo de escola pública, com renda superior a 1,5 S.M., não declarado PPI'], ['4', 'Oriundo de escola pública, com renda inferior a 1,5 S.M., declarado PPI'], ['5', 'Oriundo de escola pública, com renda inferior a 1,5 S.M., não declarado PPI'], ['0', 'Não se aplica']], max_length=255, null=True, verbose_name='Cota MEC')),
                ('renda_per_capita', models.DecimalField(decimal_places=2, help_text='Número de salários mínimos ganhos pelos integrantes da família dividido pelo número de integrantes', max_digits=15, null=True, verbose_name='Renda Per Capita')),
                ('observacao_historico', models.TextField(blank=True, null=True, verbose_name='Observação para o Histórico')),
                ('observacao_matricula', models.TextField(blank=True, null=True, verbose_name='Observação da Matrícula')),
                ('alterado_em', djtools.db.models.DateTimeFieldPlus(auto_now=True, null=True, verbose_name='Data de Alteração')),
                ('email_academico', models.EmailField(blank=True, max_length=254, verbose_name='Email Acadêmico')),
                ('email_qacademico', models.EmailField(blank=True, max_length=254, verbose_name='Email Q-Acadêmico')),
                ('email_google_classroom', models.EmailField(blank=True, max_length=254, verbose_name='Email do Google Classroom')),
                ('csf', models.BooleanField(default=False, verbose_name='Ciência sem Fronteiras')),
                ('documentada', models.BooleanField(default=False, verbose_name='Doc. Entregue')),
                ('data_documentacao', models.DateTimeField(null=True, verbose_name='Data de Entrega da Documentação')),
                ('cartao_sus', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Cartão SUS')),
                ('codigo_educacenso', djtools.db.models.CharFieldPlus(blank=True, max_length=255, null=True, verbose_name='Código EDUCACENSO')),
                ('nis', djtools.db.models.CharFieldPlus(blank=True, help_text='Número de Identificação Social', max_length=255, null=True, verbose_name='NIS')),
                ('poder_publico_responsavel_transporte', djtools.db.models.CharFieldPlus(blank=True, choices=[['1', 'Municipal'], ['2', 'Estadual']], max_length=255, null=True, verbose_name='Poder Público Responsável pelo Transporte Escolar')),
                ('tipo_veiculo', djtools.db.models.CharFieldPlus(blank=True, choices=[['Rodoviário', [['1', 'Vans/WV'], ['2', 'Kombi Micro-Ônibus'], ['3', 'Ônibus'], ['4', 'Bicicleta'], ['5', 'Tração Animal'], ['6', 'Outro tipo de veículo rodoviário']]], ['Aquaviário', [['7', 'Capacidade de até 5 pessoas'], ['8', 'Capacidade entre 5 a 15 pessoas'], ['9', 'Capacidade entre 15 e 35 pessoas'], ['10', 'Capacidade acima de 35 pessoas']]], ['Ferroviário', [['11', 'Trem/Metrô']]]], max_length=255, null=True, verbose_name='Tipo de Veículo Utilizado no Transporte Escolar')),
                ('ano_conclusao_estudo_anterior', djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trabalhadoreducando_ano_conclusao_anterior_set', to='comum.ano', verbose_name='Ano de Conclusão de Estudo Anterior')),
                ('cidade', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.municipio', verbose_name='Cidade')),
                ('cidade_profissional', djtools.db.models.ForeignKeyPlus(null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trabalhadoreducando_cidade_profissional_set', to='comum.municipio', verbose_name='Cidade Profissional')),
                ('estado_emissao_carteira_reservista', djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trabalhadoreducando_estado_emissor_carteira_reservista_set', to='comum.unidadefederativa', verbose_name='Estado Emissor')),
                ('naturalidade', djtools.db.models.ForeignKeyPlus(blank=True, help_text='Cidade em que o(a) trabalhadoreducando nasceu. Obrigatório para brasileiros', null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trabalhadoreducando_naturalidade_set', to='comum.municipio', verbose_name='Naturalidade')),
                ('nivel_ensino_anterior', djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.nivelensino')),
                ('orgao_emissao_rg', djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.orgaoemissorrg', verbose_name='Orgão Emissor')),
                ('pais_origem', djtools.db.models.ForeignKeyPlus(blank=True, help_text='Obrigatório para estrangeiros', null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.pais', verbose_name='País de Origem')),
                ('pessoa_fisica', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='trabalhadoreducando_set', to='rh.pessoafisica', verbose_name='Pessoa Física')),
                ('uf_emissao_rg', djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trabalhadoreducando_emissor_rg_set', to='comum.unidadefederativa', verbose_name='Estado Emissor')),
                ('uf_emissao_titulo_eleitor', djtools.db.models.ForeignKeyPlus(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='trabalhadoreducando_emissor_titulo_eleitor_set', to='comum.unidadefederativa', verbose_name='Estado Emissor')),
            ],
            options={
                'verbose_name': 'Trabalhador Educando',
                'verbose_name_plural': 'Trabalhadores Educandos',
                'ordering': ('pessoa_fisica__nome',),
                'permissions': (('emitir_diploma', 'Pode emitir diploma de Trabalhador Educando'), ('emitir_boletim', 'Pode emitir boletim de Trabalhador Educando'), ('emitir_historico', 'Pode emitir histórico de Trabalhador Educando'), ('efetuar_matricula', 'Pode efetuar matricula de Trabalhador Educando'), ('pode_sincronizar_dados', 'Pode sincronizar dados de Trabalhador Educando'), ('gerar_relatorio', 'Pode gerar relatórios de Trabalhador Educando'), ('pode_ver_chave_acesso_pais', 'Pode ver chave de acesso dos pais'), ('change_foto', 'Pode editar foto de Trabalhador Educando'), ('view_dados_academicos', 'Pode visualizar dados acadêmicos de Trabalhador Educando'), ('view_dados_pessoais', 'Pode visualizar dados pessoais de Trabalhador Educando')),
            },
        ),
        migrations.CreateModel(
            name='Observacao',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('observacao', models.TextField(verbose_name='Observação da Matrícula')),
                ('data', djtools.db.models.DateFieldPlus(verbose_name='Data')),
                ('trabalhadoreducando', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, to='ppe.trabalhadoreducando', verbose_name='Trabalhador Educando')),
                ('usuario', djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE, related_name='trabalhadoreducando_observacao_set', to=settings.AUTH_USER_MODEL, verbose_name='Usuário')),
            ],
            options={
                'permissions': (('adm_delete_observacao', 'Pode deletar observações de outros usuários'),),
            },
        ),
    ]
