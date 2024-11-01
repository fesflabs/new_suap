# Generated by Django 2.2.7 on 2019-12-09 15:05

from django.db import migrations
import django.db.models.deletion
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [('plan_estrategico', '0008_origemrecursoprojetoetapa_valor')]

    operations = [
        migrations.AddField(
            model_name='unidadegestoraetapa', name='valor', field=djtools.db.models.DecimalFieldPlus(blank=True, decimal_places=2, max_digits=12, null=True, verbose_name='Valor')
        ),
        migrations.AlterField(
            model_name='origemrecursoprojetoetapa',
            name='etapa_projeto_plano_atividade',
            field=djtools.db.models.ForeignKeyPlus(
                on_delete=django.db.models.deletion.CASCADE,
                related_name='origens_recurso_etapa',
                to='plan_estrategico.EtapaProjetoPlanoAtividade',
                verbose_name='Etapa do projeto do plano de atividade',
            ),
        ),
    ]
