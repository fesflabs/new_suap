# Generated by Django 2.2.7 on 2020-02-05 15:00

import requests
from django.db import migrations
from django.conf import settings
from django.apps import apps
import os


def migrate(apps, editor):
    RegistroEmissaoDocumento = apps.get_model('comum.RegistroEmissaoDocumento')
    ContentType = apps.get_model('contenttypes.ContentType')
    lista = [
        ('Comprovante de Dados Acadêmicos', 'edu.aluno'),
        ('Histórico', 'edu.aluno'),
        ('Declaração de Orientação', 'edu.professor'),
        ('Declaração de Matrícula', 'edu.aluno'),
        ('Declaração de Carga Horária Cumprida', 'edu.aluno'),
        ('Diploma/Certificado', 'edu.registroemissaodiploma'),
        ('Declaração de Participação em Projeto Final', 'edu.projetofinal'),
        ('Certificado ENEM', 'edu.registroemissaocertificadoenem'),
        ('Certificado ENEM', 'edu.registroemissaocertificadoenem'),
        ('Histórico SICA', 'sica.Historico'),
        ('Declaração SICA', 'sica.Historico'),
        ('Pesquisa', 'pesquisa.participacao'),
        ('Extensão', 'projetos.participacao'),
        ('Carteira Funcional Digital', 'rh.servidor'),
        ('Certificado de Participação em Evento [CORROMPIDO]', 'edu.participanteevento'),
        ('Comprovante de Matrícula', 'edu.aluno'),
        ('Declaração', 'edu.aluno'),
        ('ENCCEJA', 'encceja.solicitacao'),
    ]
    for tipo_documento, modelo in lista:
        app_label, model_name = modelo.split('.')
        if app_label in settings.INSTALLED_APPS:
            tipo_objeto = ContentType.objects.get_for_model(apps.get_model(modelo))
            RegistroEmissaoDocumento.objects.filter(tipo=tipo_documento).update(tipo_objeto=tipo_objeto)

    if 'edu' not in settings.INSTALLED_APPS:
        return
    tipo_objeto = ContentType.objects.get_for_model(apps.get_model('edu.participanteevento'))
    RegistroEmissaoDocumento.objects.filter(tipo='Certificado de Participação em Evento').update(tipo_objeto=tipo_objeto)

    tipo_objeto_participanteevento = ContentType.objects.get_for_model(apps.get_model('edu.participanteevento'))
    for registro in RegistroEmissaoDocumento.objects.filter(tipo='Diploma/Certificado de Participação em Evento'):
        registro.tipo = 'Diploma/Certificado'
        registro.documento = 'comum/registroemissaodocumento/documento/xxxx/participanteevento-{}.pdf'.format(registro.modelo_pk)
        registro.tipo_objeto = tipo_objeto_participanteevento
        registro.save()

    tipo_objeto_registroemissaodiploma = ContentType.objects.get_for_model(apps.get_model('edu.registroemissaodiploma'))
    for registro in RegistroEmissaoDocumento.objects.filter(tipo='Diploma/Certificado', tipo_objeto=tipo_objeto_participanteevento):
        registro.pk = None
        registro.tipo = 'Diploma/Certificado'
        registro.documento = 'comum/registroemissaodocumento/documento/xxxx/registroemissaodiploma-{}.pdf'.format(registro.modelo_pk)
        registro.tipo_objeto = tipo_objeto_registroemissaodiploma
        registro.save()

    tipo_objeto = ContentType.objects.get_for_model(apps.get_model('edu.professor'))
    RegistroEmissaoDocumento.objects.filter(tipo_objeto__isnull=True, tipo='Declaração de Vínculo', modelo_pk__lt=10000).update(tipo_objeto=tipo_objeto)

    tipo_objeto = ContentType.objects.get_for_model(apps.get_model('edu.aluno'))
    RegistroEmissaoDocumento.objects.filter(tipo_objeto__isnull=True, tipo='Declaração de Vínculo', modelo_pk__gt=10000).update(tipo_objeto=tipo_objeto)


def gerar_registros_diploma(sessionid, limit=1):
    RegistroEmissaoDocumento = apps.get_model('comum.RegistroEmissaoDocumento')
    cookies = {'sessionid': sessionid}
    diretorio = os.path.join(settings.MEDIA_ROOT, 'comum/registroemissaodocumento/documento/0000')
    if not os.path.exists(diretorio):
        os.makedirs(diretorio)
    qs = RegistroEmissaoDocumento.objects.filter(documento__startswith='comum/registroemissaodocumento/documento/xxxx/registroemissaodiploma-')
    qs = limit and qs[0:limit] or qs
    for registro in qs:
        print(registro.pk, registro.tipo, registro.data_emissao, registro.codigo_verificador, registro.objeto.pk)
        url = 'https://suap.ifrn.edu.br/edu/registroemissaodiploma_pdf/{}/'.format(registro.modelo_pk)
        response = requests.get(url, allow_redirects=True, cookies=cookies)
        if response.status_code == 200 and response.url == url:
            relative_path = registro.documento.name.replace('/xxxx/', '/0000/{}-'.format(registro.codigo_verificador[0:7]))
            file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            print(file_path)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            registro.documento = relative_path
            registro.save()
        else:
            print('Error: Registro {}'.format(registro.pk))
            break


def gerar_certificados_eventos(sessionid, limit=1):
    RegistroEmissaoDocumento = apps.get_model('comum.RegistroEmissaoDocumento')
    cookies = {'sessionid': sessionid}
    diretorio = os.path.join(settings.MEDIA_ROOT, 'comum/registroemissaodocumento/documento/0000')
    if not os.path.exists(diretorio):
        os.makedirs(diretorio)
    qs = RegistroEmissaoDocumento.objects.filter(documento__startswith='comum/registroemissaodocumento/documento/xxxx/participanteevento-')
    qs = limit and qs[0:limit] or qs
    for registro in qs:
        print(registro.pk, registro.tipo, registro.data_emissao, registro.codigo_verificador, registro.objeto.pk)
        url = 'https://suap.ifrn.edu.br/edu/imprimir_certificado_participacao_evento/{}/'.format(registro.modelo_pk)
        response = requests.get(url, allow_redirects=True, cookies=cookies)
        if response.status_code == 200 and response.url == url:
            relative_path = registro.documento.name.replace('/xxxx/', '/0000/{}-'.format(registro.codigo_verificador[0:7]))
            file_path = os.path.join(settings.MEDIA_ROOT, relative_path)
            print(file_path)
            with open(file_path, 'wb') as f:
                f.write(response.content)
            registro.documento = relative_path
            registro.save()
        else:
            print('Error: Registro {}'.format(registro.pk))
            break


def unmigrate(apps, editor):
    pass


class Migration(migrations.Migration):

    if 'edu' in settings.INSTALLED_APPS:
        dependencies = [
            ('comum', '0007_registroemissaodocumento_tipo_objeto'),
            # ('edu', '0016_auto_20200123_1435'),
        ]

        # As migrations abaixo foram referenciadas manualmente, pois ao tentar criar um banco do zero, executando o comando
        # "python manage.py migrate", ocorria o erro: "LookupError: No installed app with label 'edu'" . Para saber quais
        # migrations referenciar, tomei como parâmetro a data da última modificação realizada nesta migrations(07/02/2020 - ffff5b78746f064f0701451cf25e92492c412e20)
        # e fui atrás das migrations dos módulos abaixo que existiam nesta mesma data ou na primeira data anterior a ela.
        # Obs: Um exceção foi o edu, pois na data imediatamente anterior ocorreu um alteracão na migration initial, daí peguei
        # a migration da data anterior a essa ajuste na migration initial.

        if 'sica' in settings.INSTALLED_APPS:
            dependencies.append(('sica', '0001_initial'))
        if 'pesquisa' in settings.INSTALLED_APPS:
            dependencies.append(('pesquisa', '0002_auto_20191205_1929'))
        if 'encceja' in settings.INSTALLED_APPS:
            dependencies.append(('encceja', '0003_auto_20191209_1656'))
    else:
        dependencies = [
            ('comum', '0007_registroemissaodocumento_tipo_objeto'),
        ]

    operations = [migrations.RunPython(migrate, unmigrate)]