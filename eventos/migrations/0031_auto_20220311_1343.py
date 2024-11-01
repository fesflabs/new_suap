# Generated by Django 3.2.5 on 2022-03-11 13:43

from django.db import migrations
import djtools.db.models


class Migration(migrations.Migration):

    dependencies = [
        ('eventos', '0030_evento_finalizado'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tipoparticipacao',
            name='modelo_certificado_padrao',
            field=djtools.db.models.FileFieldPlus(blank=True, help_text='O arquivo de modelo deve ser um arquivo .docx contendo as marcações #INSTITUICAO#, #NOMEDOPARTICIPANTE#, #TIPODOPARTICIPANTE#, #TIPOPARTICIPACAO#, #PARTICIPANTE#, #CPF#, #NOMEDOEVENTO#, #EVENTO#, #ATIVIDADES#, #LOCAL#, #CAMPUS#, #CARGAHORARIA#, #DATAINICIALADATAFINAL#, #PERIODOREALIZACAO#, #SETORRESPONSAVEL#, #CIDADE#, #UF#, #DATAEMISSAO#, #DATA#, #CODIGOVERIFICADOR#.', null=True, upload_to='eventos/modelo_certificado/', verbose_name='Modelo de Certificado Padrão'),
        ),
        migrations.AlterField(
            model_name='tipoparticipante',
            name='modelo_certificado',
            field=djtools.db.models.FileFieldPlus(blank=True, help_text='O arquivo de modelo deve ser um arquivo .docx contendo as marcações #INSTITUICAO#, #NOMEDOPARTICIPANTE#, #TIPODOPARTICIPANTE#, #TIPOPARTICIPACAO#, #PARTICIPANTE#, #CPF#, #NOMEDOEVENTO#, #EVENTO#, #ATIVIDADES#, #LOCAL#, #CAMPUS#, #CARGAHORARIA#, #DATAINICIALADATAFINAL#, #PERIODOREALIZACAO#, #SETORRESPONSAVEL#, #CIDADE#, #UF#, #DATAEMISSAO#, #DATA#, #CODIGOVERIFICADOR#. Não preencher caso deseje utilizar o modelo padrão.', null=True, upload_to='eventos/modelo_certificado/', verbose_name='Modelo de Certificado'),
        ),
    ]
