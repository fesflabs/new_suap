# Generated by Django 2.2.16 on 2021-04-26 17:49

from django.db import migrations


def popular_campus_equipe_servico(apps, schema_editor):
    """
     Popula os dados do campo 'campus' da entidade EquipeServiço com a UO do vinculo""

     :param apps:
     :param schema_editor:
     :return:
     """
    ServicoEquipe = apps.get_model('catalogo_provedor_servico', 'ServicoEquipe')
    for membro_equipe in ServicoEquipe.objects.all():
        uo = membro_equipe.vinculo.setor.uo if membro_equipe.vinculo else None
        membro_equipe.campus = uo
        membro_equipe.save()


def despopular_campus_equipe_servico(apps, schema_editor):
    """
    Apaga os dados do campo 'campus' da entidade EquipeServiço ""

    :param apps:
    :param schema_editor:
    :return:
    """
    ServicoEquipe = apps.get_model('catalogo_provedor_servico', 'ServicoEquipe')
    ServicoEquipe.objects.all().update(campus=None)


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo_provedor_servico', '0048_servicoequipe_campus'),
    ]

    operations = [
        migrations.RunPython(popular_campus_equipe_servico, despopular_campus_equipe_servico),
    ]