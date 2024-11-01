# Generated by Django 2.2.10 on 2020-05-26 19:59

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo_provedor_servico', '0024_auto_20200525_2241'),
    ]

    operations = [
        migrations.AlterField(
            model_name='solicitacao',
            name='status',
            field=djtools.db.models.CharFieldPlus(choices=[('INCOMPLETO', 'Incompleto'), ('EM_ANALISE', 'Em Análise'), ('AGUARDANDO_CORRECAO_DE_DADOS', 'Aguardando Correção de Dados'), ('DADOS_CORRIGIDOS', 'Dados Corrigidos'), ('PRONTO_PARA_EXECUCAO', 'Pronto Para Execução'), ('ATENDIDO', 'Atendido'), ('NAO_ATENDIDO', 'Não Atendido'), ('EXPIRADO', 'Expirado')], default='EM_ANALISE', max_length=50, verbose_name='Status'),
        ),
    ]
