# Generated by Django 2.2.16 on 2020-12-16 19:34

import tqdm
from djtools.templatetags.filters import in_group
from django.db import migrations
from django.contrib.auth.models import Group


def migrar_grupo_gerente_avaliacao_para_gerente_local(apps, schema_editor):
    """
    Realiza a migração dos usuários pertencentes ao grupo ""

    :param apps:
    :param schema_editor:
    :return:
    """
    group_gerente_local_exists = Group.objects.filter(name="Gerente Local do Catalogo Digital").exists()
    for group in tqdm.tqdm(Group.objects.all()):
        if group_gerente_local_exists and group.name == "Gerente de Avaliação do Catálogo Digital":
            grupo_gerente_local_catalogo = Group.objects.get(name="Gerente Local do Catalogo Digital")
            for usuario_grupo in tqdm.tqdm(group.usuariogrupo_set.all()):
                if not in_group(usuario_grupo.user, "Gerente Local do Catalogo Digital"):
                    usuario_grupo.group = grupo_gerente_local_catalogo
                    usuario_grupo.save()
                    print("{} migrou do {} para {}".format(usuario_grupo.user, group.name, grupo_gerente_local_catalogo.name))
                else:
                    usuario_grupo.delete()
                    print("{} removido do {} já pertence a {}".format(usuario_grupo.user, group.name, grupo_gerente_local_catalogo.name))
            if group.usuariogrupo_set.all().count() == 0 and group.name == "Gerente de Avaliação do Catálogo Digital":
                print("Delete group {}".format(group.name))
                group.delete()


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo_provedor_servico', '0043_registronotificacaogovbr'),
    ]

    operations = [
        migrations.RunPython(migrar_grupo_gerente_avaliacao_para_gerente_local),
    ]