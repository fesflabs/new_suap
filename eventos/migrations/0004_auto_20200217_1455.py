# Generated by Django 2.2.7 on 2020-02-17 14:55
import os
from django.conf import settings
from django.db import migrations
import shutil


def migrate(apps, editor):
    Group = apps.get_model('auth.Group')
    EventoEnsino = apps.get_model('edu.Evento')
    Evento = apps.get_model('eventos.Evento')
    Dimensao = apps.get_model('eventos.Dimensao')
    TipoParticipacao = apps.get_model('eventos.TipoParticipacao')
    TipoParticipante = apps.get_model('eventos.TipoParticipante')
    Participante = apps.get_model('eventos.Participante')
    ParticipanteEvento = apps.get_model('edu.ParticipanteEvento')
    RegistroEmissaoDocumento = apps.get_model('comum.RegistroEmissaoDocumento')
    ContentType = apps.get_model('contenttypes.ContentType')
    content_type_ensino = ContentType.objects.get_for_model(apps.get_model('edu.participanteevento'))

    # cadastrando as dimensoes
    ensino = Dimensao.objects.get_or_create(descricao='Ensino')[0]
    Dimensao.objects.get_or_create(descricao='Pesquisa')
    Dimensao.objects.get_or_create(descricao='Extensão')
    Dimensao.objects.get_or_create(descricao='Recursos Humanos')
    Dimensao.objects.get_or_create(descricao='Gestão')

    # adicionando os grupos da dimensão do ensino
    grupos_ensino_locais = 'Coordenador de Registros Acadêmicos', 'Diretor Acadêmico', 'Organizador de Palestras', 'Secretário Acadêmico'
    grupos_ensino_sistemicos = 'Administrador Acadêmico'
    for group in Group.objects.filter(name__in=grupos_ensino_locais):
        ensino.grupos_avaliadores_locais.add(group)
    for group in Group.objects.filter(name=grupos_ensino_sistemicos):
        ensino.grupos_avaliadores_sistemicos.add(group)

    # cadastrando os tipos de participação padrões
    modelo_certificado_template_path = os.path.join(settings.BASE_DIR, 'eventos/template/base_para_certificados.docx')
    modelo_certificado_dir_path = os.path.join(settings.MEDIA_ROOT, 'eventos/modelo_certificado/')
    modelo_certificado_file_path = os.path.join(modelo_certificado_dir_path, 'base_para_certificados_padrao.docx')
    if not os.path.exists(modelo_certificado_dir_path):
        os.makedirs(modelo_certificado_dir_path)
    if not os.path.exists(modelo_certificado_file_path):
        shutil.copy(modelo_certificado_template_path, modelo_certificado_file_path)
    tipo_participacao_participante = TipoParticipacao.objects.get_or_create(
        descricao='Participante', modelo_certificado_padrao='eventos/modelo_certificado/base_para_certificados_padrao.docx'
    )[0]
    tipo_participacao_palestrante = TipoParticipacao.objects.get_or_create(descricao='Palestrante')[0]
    tipo_participacao_convidado = TipoParticipacao.objects.get_or_create(descricao='Convidado')[0]
    TipoParticipacao.objects.get_or_create(descricao='Organizador')[0]

    # processando os eventos do módulo de eventos
    for evento in Evento.objects.all().order_by('id'):
        tipo_participante = TipoParticipante.objects.create(evento=evento, tipo_participacao=tipo_participacao_participante)
        evento.participantes.update(tipo=tipo_participante, inscricao_validada=True)

    # processando os eventos do módulo de ensino
    for evento_ensino in EventoEnsino.objects.all().order_by('-id'):
        evento = Evento.objects.create(
            nome=evento_ensino.titulo,
            apresentacao=evento_ensino.descricao,
            local='',
            data_inicio=evento_ensino.data,
            hora_inicio='00:00',
            campus=evento_ensino.uo,
            gera_certificado=True,
            deferido=True,
            qtd_participantes=evento_ensino.participantes.count(),
        )
        evento.dimensoes.add(ensino)

        def adicionar_paticipante(participante_evento, tipo):
            registro_emissao_documento = RegistroEmissaoDocumento.objects.filter(tipo_objeto=content_type_ensino, modelo_pk=participante_evento.pk).first()
            codigo_geracao_certificado = None
            if registro_emissao_documento:
                codigo_geracao_certificado = '{}{}'.format(registro_emissao_documento.data_emissao.strftime('%d%m%Y'), registro_emissao_documento.codigo_verificador[0:7])
                registro_emissao_documento.delete()
            Participante.objects.create(
                evento=evento,
                nome=participante_evento.participante.nome,
                cpf=participante_evento.participante.cpf and participante_evento.participante.cpf[0:14] or None,
                email=participante_evento.participante.email_secundario or participante_evento.participante.email,
                tipo=tipo,
                data_cadastro=participante_evento.evento.data,
                inscricao_validada=True,
                certificado_enviado=registro_emissao_documento is not None,
                codigo_geracao_certificado=codigo_geracao_certificado,
            )

        participantes = ParticipanteEvento.objects.filter(evento=evento_ensino, tipo_participacao='Participante').order_by('id')
        if participantes:
            tipo_participante = TipoParticipante.objects.create(
                evento=evento, tipo_participacao=tipo_participacao_participante, modelo_certificado=evento_ensino.modelo_certificado_participacao
            )
            for participante_evento in participantes:
                adicionar_paticipante(participante_evento, tipo_participante)
        palestrantes = ParticipanteEvento.objects.filter(evento=evento_ensino, tipo_participacao='Palestrante').order_by('id')
        if palestrantes:
            tipo_palestrante = TipoParticipante.objects.create(
                evento=evento, tipo_participacao=tipo_participacao_palestrante, modelo_certificado=evento_ensino.modelo_certificado_palestrante
            )
            for participante_evento in palestrantes:
                adicionar_paticipante(participante_evento, tipo_palestrante)
        convidados = ParticipanteEvento.objects.filter(evento=evento_ensino, tipo_participacao='Convidado').order_by('id')
        if convidados:
            tipo_convidado = TipoParticipante.objects.create(
                evento=evento, tipo_participacao=tipo_participacao_convidado, modelo_certificado=evento_ensino.modelo_certificado_convidado
            )
            for participante_evento in convidados:
                adicionar_paticipante(participante_evento, tipo_convidado)


def unmigrate(apps, editor):
    pass


class Migration(migrations.Migration):

    dependencies = [('eventos', '0003_auto_20200217_1444')]

    operations = [migrations.RunPython(migrate, unmigrate)]