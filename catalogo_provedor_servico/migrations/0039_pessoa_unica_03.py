# Generated by Django 2.2.16 on 2020-09-24 10:37

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('catalogo_provedor_servico', '0038_pessoa_unica_02'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='servicoequipe',
            name='pessoa_fisica',
        ),
        migrations.RemoveField(
            model_name='solicitacao',
            name='atribuinte',
        ),
        migrations.RemoveField(
            model_name='solicitacao',
            name='responsavel',
        ),
        migrations.RemoveField(
            model_name='solicitacaohistoricosituacao',
            name='responsavel',
        ),
        migrations.RemoveField(
            model_name='solicitacaoresponsavelhistorico',
            name='atribuinte',
        ),
        migrations.RemoveField(
            model_name='solicitacaoresponsavelhistorico',
            name='responsavel',
        ),
    ]