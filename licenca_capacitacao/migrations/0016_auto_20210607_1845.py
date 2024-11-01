# Generated by Django 2.2.16 on 2021-06-07 18:45

from django.db import migrations


def setar_solcitacao_alteracao_inicio_exercicio(apps, schema):
    SolicitacaoAlteracaoDataInicioExercicio = apps.get_model('licenca_capacitacao', 'SolicitacaoAlteracaoDataInicioExercicio')
    ServidorDataInicioExercicioAjustada = apps.get_model('licenca_capacitacao', 'ServidorDataInicioExercicioAjustada')

    sols = SolicitacaoAlteracaoDataInicioExercicio.objects.filter(situacao__isnull=False)
    for sol in sols:
        ajus = ServidorDataInicioExercicioAjustada.objects.filter(servidor=sol.servidor)
        if ajus:
            ajus[0].solicitacao_alteracao = sol
            ajus[0].save()


class Migration(migrations.Migration):

    dependencies = [
        ('licenca_capacitacao', '0015_auto_20210528_1140'),
    ]

    operations = [migrations.RunPython(setar_solcitacao_alteracao_inicio_exercicio)]
