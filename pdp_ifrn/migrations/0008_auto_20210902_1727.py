# Generated by Django 3.2.5 on 2021-09-02 17:27

from django.db import migrations, models
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('rh', '0023_servidorfuncaohistorico_atualiza_pelo_extrator'),
        ('pdp_ifrn', '0007_auto_20210730_0915'),
    ]

    operations = [
        migrations.AddField(
            model_name='resposta',
            name='titulo_necessidade',
            field=djtools.db.models.CharFieldPlus(blank=True, help_text='Em caso de já possuir uma opção em consideração qual seria o título previsto da ação de desenvolvimento para essa necessidade?', max_length=400, null=True, verbose_name='Título previsto da ação de desenvolvimento'),
        ),
        migrations.AlterField(
            model_name='historicostatusresposta',
            name='status',
            field=djtools.db.models.CharFieldPlus(default=(('pendente', 'Pendente'), ('deferida', 'Deferida pela Comissão Local'), ('indeferida', 'Indeferida pela Comissão Local'), ('aprovada', 'Aprovada pelo Dirigente Máximo do Campus/Reitoria'), ('reprovada', 'Reprovada pelo Dirigente Máximo do Campus/Reitoria'), ('homologada', 'Homologada pelo Reitor'), ('rejeitada', 'Rejeitada pelo Reitor')), max_length=10, verbose_name='Situação'),
        ),
        migrations.AlterField(
            model_name='resposta',
            name='acao_transversal',
            field=djtools.db.models.CharFieldPlus(choices=[('sim', 'Sim'), ('nao', 'Não')], help_text='Essa necessidade de desenvolvimento é transversal, ou seja, comum a múltiplas unidades do IFRN?', max_length=3, verbose_name='Ação Transversal'),
        ),
        migrations.AlterField(
            model_name='resposta',
            name='justificativa_necessidade',
            field=models.TextField(help_text='Descreva do que serão capazes se for atendida sua necessidade e o resultado que trará para o IFRN. Ex: Para gerir contratos de papéis para uma utilização racional dos materiais que resultará na redução do consumo do papel (máximo de 200 caracteres).', max_length=200, verbose_name='Que resultado essa ação de desenvolvimento trará?'),
        ),
        migrations.AlterField(
            model_name='resposta',
            name='onus_inscricao',
            field=djtools.db.models.CharFieldPlus(choices=[('sim', 'Sim'), ('nao', 'Não')], max_length=3, verbose_name='A ação de desenvolvimento pode ser ofertada de modo gratuito? Sim ou não'),
        ),
        migrations.RemoveField(
            model_name='resposta',
            name='setor_beneficiado',
        ),
        migrations.AddField(
            model_name='resposta',
            name='setor_beneficiado',
            field=models.ManyToManyField(help_text='Qual unidade funcional do IFRN será beneficiada pela ação de desenvolvimento para essa necessidade?', related_name='setor_beneficiado', to='rh.Setor', verbose_name='Setor Beneficiado'),
        ),
        migrations.AlterField(
            model_name='resposta',
            name='valor_onus_inscricao',
            field=djtools.db.models.DecimalFieldPlus(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Se não gratuita, qual o custo total previsto da ação de desenvolvimento para essa necessidade?'),
        ),
    ]