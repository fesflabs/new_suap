# Generated by Django 2.2.16 on 2021-04-21 09:01

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('encceja', '0004_auto_20200709_1356'),
    ]

    operations = [
        migrations.AddField(
            model_name='configuracao',
            name='modelo_certificacao_completa_com_timbre',
            field=djtools.db.models.FileFieldPlus(blank=True, help_text='O arquivo de modelo deve ser uma arquivo .docx. Marcações disponíveis #NOME#, #CPF#, #ANO#, #AREAS#, #AVALIACOES#, #PONTUACAO#,\n                                                       #EDITAIS#, #LEGENDA_EDITAIS#, #CODIGOVERIFICADOR#, #LOCAL#, #DATA#, #AVA_REDACAO#, #EDIT_REDACAO#, #PONT_REDACAO#', null=True, upload_to='encceja/modelos_documento/', verbose_name='Modelo de Certificação Completa com Timbre'),
        ),
        migrations.AddField(
            model_name='configuracao',
            name='modelo_certificacao_parcial_com_timbre',
            field=djtools.db.models.FileFieldPlus(blank=True, help_text='O arquivo de modelo deve ser uma arquivo .docx. Marcações disponíveis #NOME#, #CPF#, #ANO#, #AREAS#, #AVALIACOES#, #PONTUACAO#,\n                                                       #EDITAIS#, #LEGENDA_EDITAIS#, #CODIGOVERIFICADOR#, #LOCAL#, #DATA#, #AVA_REDACAO#, #EDIT_REDACAO#, #PONT_REDACAO#', null=True, upload_to='encceja/modelos_documento/', verbose_name='Modelo de Certificação Parcial Com Timbre'),
        ),
    ]
