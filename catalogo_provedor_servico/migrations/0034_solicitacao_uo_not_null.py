# Generated by Django 2.2.10 on 2020-07-12 18:01

import django.db.models.deletion
from django.db import migrations

import djtools.db.models
# from catalogo_provedor_servico.providers.impl.ifrn.matricula_ead import CAMPUS_ZL, ID_GOVBR_6176_MATRICULA_EAD


def atribuir_uo_solicitacoes_matricula_ead(apps, schema_editor):
    '''
    Este comando atribui ao campos ZL, responsável pelo EAD, todos as solicitações criadas
    para o serviço de "Participar de processo seletivo para curso de Educação à Distância - IFRN",
    antes que o atributo "uo" seja ajustado para NOT NULL.

    :param apps:
    :param schema_editor:
    :return: None
    '''
    # Solicitacao = apps.get_model('catalogo_provedor_servico', 'Solicitacao')
    # solicitacoes = Solicitacao.objects.filter(servico__id_servico_portal_govbr=ID_GOVBR_6176_MATRICULA_EAD,
    #                                           uo__isnull=True)
    # solicitacoes.update(uo=CAMPUS_ZL)


class Migration(migrations.Migration):
    dependencies = [
        ('catalogo_provedor_servico', '0033_auto_20200710_1417'),
    ]

    operations = [
        migrations.RunPython(atribuir_uo_solicitacoes_matricula_ead),

        migrations.AlterField(
            model_name='solicitacao',
            name='uo',
            field=djtools.db.models.ForeignKeyPlus(on_delete=django.db.models.deletion.CASCADE,
                                                   related_name='solicitacoes', to='rh.UnidadeOrganizacional',
                                                   verbose_name='Campus'),
        ),
    ]
