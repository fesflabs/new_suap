# Generated by Django 3.2.5 on 2022-05-25 15:04

from django.db import migrations
import django.db.models.deletion
import djtools.db.models
import tqdm


def migrar_fk_pessoa_para_fk_vinculo(apps, schema_editor):
    Vinculo = apps.get_model('comum.Vinculo')
    DocumentoAnexo = apps.get_model('ponto.DocumentoAnexo')

    vinculos_por_pessoa = {}
    for vinculo in Vinculo.objects.all():
        vinculos_por_pessoa[vinculo.pessoa_id] = vinculo.pk

    for anexo in tqdm.tqdm(DocumentoAnexo.objects.all()):
        anexo.vinculo_id = vinculos_por_pessoa[anexo.pessoa_id]
        anexo.save()


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0040_auto_20220510_1439'),
        ('ponto', '0008_frequencia_ip'),
    ]

    operations = [
        migrations.AddField(
            model_name='documentoanexo',
            name='vinculo',
            field=djtools.db.models.ForeignKeyPlus(editable=False, null=True, on_delete=django.db.models.deletion.CASCADE, to='comum.vinculo'),
        ),

        migrations.RunPython(migrar_fk_pessoa_para_fk_vinculo),
    ]
