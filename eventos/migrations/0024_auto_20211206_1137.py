# Generated by Django 3.2.5 on 2021-12-06 11:37

from django.db import migrations
from tqdm import tqdm


def atualizar_ch_atividade(apps, schema_editor):
    AtividadeEvento = apps.get_model('eventos', 'AtividadeEvento')

    for atividade in tqdm(AtividadeEvento.objects.all()):
        atividade.ch = atividade.ch * 60 * 60
        atividade.save()


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0023_alter_participante_telefone'),
    ]

    operations = [
        migrations.RunPython(atualizar_ch_atividade),
    ]