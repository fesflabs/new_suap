# Generated by Django 3.2.5 on 2021-12-20 17:10
import os
import shutil
import tqdm
from django.db import migrations
import djtools.db.models
from django.conf import settings


def atualizar(qs, field_str, path):
    marcar_para_deletar = []
    folder = os.path.join(settings.MEDIA_ROOT, path)
    os.makedirs(folder, exist_ok=True)
    for obj in tqdm.tqdm(qs):
        field = getattr(obj, field_str)
        file_name = field.name
        file_name = file_name and file_name.startswith('./') and file_name[2:] or file_name
        if file_name:
            original = os.path.join(settings.MEDIA_ROOT, file_name)
            marcar_para_deletar.append(original)
            target = os.path.join(folder, file_name)
            setattr(obj, field_str, os.path.join(path, file_name))
            obj.save()
            if not settings.DEBUG:
                shutil.copyfile(original, target)
    if not settings.DEBUG:
        for arquivo in marcar_para_deletar:
            os.remove(arquivo)
    with open(os.path.join(settings.MEDIA_ROOT, 'arquivos_excluidos.txt'), 'a') as f:
        for arquivo in marcar_para_deletar:
            f.write(arquivo + '\n')
    return marcar_para_deletar


def atualizar_dados(apps, schema):
    ServidorCessaoFrequencia = apps.get_model('acompanhamentofuncional.ServidorCessaoFrequencia')
    atualizar(ServidorCessaoFrequencia.objects.all(), 'arquivo', 'acompanhamentofuncional/servidorcessaofrequencia/')


class Migration(migrations.Migration):

    dependencies = [
        ('acompanhamentofuncional', '0003_auto_20210301_1709'),
    ]

    operations = [
        migrations.AlterField(
            model_name='servidorcessaofrequencia',
            name='arquivo',
            field=djtools.db.models.FileFieldPlus(max_length=250, upload_to='acompanhamentofuncional/servidorcessaofrequencia/'),
        ),
        migrations.RunPython(atualizar_dados),
    ]