# Generated by Django 3.2.5 on 2021-09-17 17:04

from django.db import migrations, models


def atualizar_dados(apps, schema):
    CategoriaNotificacao = apps.get_model('comum.CategoriaNotificacao')
    PreferenciaNotificacao = apps.get_model('comum.PreferenciaNotificacao')

    c1, _ = CategoriaNotificacao.objects.get_or_create(assunto='Alerta de dispositivo desativado', ativa=True)
    c2, _ = CategoriaNotificacao.objects.get_or_create(assunto='Alerta de login após diversas tentativas', ativa=True)
    c3, _ = CategoriaNotificacao.objects.get_or_create(assunto='Alerta de dispositivo desconhecido', ativa=True)
    c4, _ = CategoriaNotificacao.objects.get_or_create(assunto='Alerta de tentativas excessivas de login sem sucesso', ativa=True)

    c1.forcar_habilitacao = True
    c1.save()

    c2.forcar_habilitacao = True
    c2.save()

    c3.forcar_habilitacao = True
    c3.save()

    c4.forcar_habilitacao = True
    c4.save()

    PreferenciaNotificacao.objects.filter(categoria__in=[c1, c2, c3, c4]).update(via_suap=True, via_email=True)


class Migration(migrations.Migration):

    dependencies = [
        ('comum', '0030_auto_20210921_1914'),
    ]

    operations = [
        migrations.AddField(
            model_name='categorianotificacao',
            name='forcar_habilitacao',
            field=models.BooleanField(default=False, help_text='Se marcar o usuário não poderá desabilitar as preferências de notificação associadas a esta categoria.', verbose_name='Forçar Habilitação'),
        ),
        migrations.RunPython(atualizar_dados),
    ]
