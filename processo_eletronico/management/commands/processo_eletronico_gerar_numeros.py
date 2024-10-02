# -*- coding: utf-8 -*-
import tqdm
from django.apps import apps
from django.db import transaction
from django.db.models import Avg, F

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    @transaction.atomic()
    def handle(self, *args, **options):
        verbosity = options.get('verbosity', 3)

        Processo = apps.get_model("processo_eletronico", "Processo")
        Tramite = apps.get_model("processo_eletronico", "Tramite")
        TipoProcesso = apps.get_model("processo_eletronico", "TipoProcesso")
        UnidadeOrganizacional = apps.get_model("rh", "UnidadeOrganizacional")
        Setor = apps.get_model("rh", "Setor")
        DocumentoDigitalizado = apps.get_model("documento_eletronico", "DocumentoDigitalizado")
        DocumentoTexto = apps.get_model("documento_eletronico", "DocumentoTexto")

        NumerosProcessoEletronicoPorSetor = apps.get_model("processo_eletronico", "NumerosProcessoEletronicoPorSetor")
        NumerosProcessoEletronicoPorTipo = apps.get_model("processo_eletronico", "NumerosProcessoEletronicoPorTipo")
        NumerosProcessoEletronicoGeral = apps.get_model("processo_eletronico", "NumerosProcessoEletronicoGeral")
        NumerosProcessoEletronicoTempoPorTipo = apps.get_model("processo_eletronico", "NumerosProcessoEletronicoTempoPorTipo")

        from processo_eletronico.status import ProcessoStatus
        from documento_eletronico.status import DocumentoStatus

        processos = Processo.objects.all().order_by('id')
        setores = Setor.objects.all()

        # Carregando setores
        # --------------------------------------
        processos_iniciados_no_setor = {}
        processos_tramitados_no_setor = {}
        NumerosProcessoEletronicoPorSetor.objects.all().delete()
        if setores.exists():
            tqdm_setores = setores
            if verbosity:
                tqdm_setores = tqdm.tqdm(setores)
            for setor in tqdm_setores:
                processos_iniciados_no_setor[setor.id] = 0
                processos_tramitados_no_setor[setor.id] = 0

                num = NumerosProcessoEletronicoPorSetor()
                num.setor = setor
                num.save()

        # Analisando aberturas e tramites
        # --------------------------------------
        if processos.exists():
            tqdm_processos = processos
            if verbosity:
                tqdm_processos = tqdm.tqdm(processos)
            for processo in tqdm_processos:
                # -------------------------------
                # Qual setor abriu o processo
                # -------------------------------
                try:
                    processos_iniciados_no_setor[processo.setor_criacao.id] += 1
                except Exception:
                    pass

                # -------------------------------
                # Por quais setores ele tramitou
                # -------------------------------
                setores_tramites_processo = (
                    Tramite.objects.filter(processo=processo).order_by('destinatario_setor_id').distinct('destinatario_setor_id').values_list('destinatario_setor_id', flat=True)
                )
                for setor_tramite in setores_tramites_processo:
                    if processos_tramitados_no_setor.get(setor_tramite):
                        processos_tramitados_no_setor[setor_tramite] += 1
                    else:
                        processos_tramitados_no_setor[setor_tramite] = 1

        # Gravando dados de aberturas e tramites
        # --------------------------------------
        tqdm_setores = setores
        if verbosity:
            tqdm_setores = tqdm.tqdm(setores)
        for setor in tqdm_setores:
            num = NumerosProcessoEletronicoPorSetor.objects.get(setor_id=setor.id)
            num.criou = processos_iniciados_no_setor[setor.id]
            num.tramitou = processos_tramitados_no_setor[setor.id]
            num.save()

        # Analisando e gravando os dados por tipo
        # --------------------------------------
        NumerosProcessoEletronicoPorTipo.objects.all().delete()
        tipos = TipoProcesso.objects.all()
        tqdm_tipos = tipos
        if verbosity:
            tqdm_tipos = tqdm.tqdm(tipos)
        for tipo in tqdm_tipos:
            num = NumerosProcessoEletronicoPorTipo()
            num.tipo = tipo
            num.qtd = Processo.objects.filter(tipo_processo=tipo).count()
            num.save()

        # Analisando e gravando os dados gerais
        # --------------------------------------
        NumerosProcessoEletronicoGeral.objects.all().delete()
        num = NumerosProcessoEletronicoGeral()

        num.STATUS_ATIVO = Processo.objects.filter(status=ProcessoStatus.STATUS_ATIVO).count()

        num.STATUS_ARQUIVADO = Processo.objects.filter(status=ProcessoStatus.STATUS_ARQUIVADO).count()
        num.STATUS_SOBRESTADO = Processo.objects.filter(status=ProcessoStatus.STATUS_SOBRESTADO).count()
        num.STATUS_FINALIZADO = Processo.objects.filter(status=ProcessoStatus.STATUS_FINALIZADO).count()
        num.STATUS_ANEXADO = Processo.objects.filter(status=ProcessoStatus.STATUS_ANEXADO).count()
        num.STATUS_REABERTO = Processo.objects.filter(status=ProcessoStatus.STATUS_REABERTO).count()
        num.STATUS_AGUARDANDO_CIENCIA = Processo.objects.filter(status=ProcessoStatus.STATUS_AGUARDANDO_CIENCIA).count()
        num.STATUS_AGUARDANDO_JUNTADA = Processo.objects.filter(status=ProcessoStatus.STATUS_AGUARDANDO_JUNTADA).count()
        num.STATUS_EM_HOMOLOGACAO = Processo.objects.filter(status=ProcessoStatus.STATUS_EM_HOMOLOGACAO).count()

        num.qtd_processos = (
            num.STATUS_ATIVO
            + num.STATUS_ARQUIVADO
            + num.STATUS_SOBRESTADO
            + num.STATUS_FINALIZADO
            + num.STATUS_ANEXADO
            + num.STATUS_REABERTO
            + num.STATUS_AGUARDANDO_CIENCIA
            + num.STATUS_AGUARDANDO_JUNTADA
            + num.STATUS_EM_HOMOLOGACAO
        )

        num.qtd_documentos_texto = DocumentoTexto.objects.exclude(status=DocumentoStatus.STATUS_CANCELADO).count()
        num.qtd_documentos_digitalizado = DocumentoDigitalizado.objects.all().count()

        num.save()

        # Analisando e gravando dados de tempo médio dos tipos de proceso por cada UO de criacao
        # --------------------------------------
        NumerosProcessoEletronicoTempoPorTipo.objects.all().delete()
        uos = UnidadeOrganizacional.objects.suap().all()
        tqdm_uos = uos
        if verbosity:
            tqdm_uos = tqdm.tqdm(uos)
        tipos = TipoProcesso.objects.all()
        for uo in tqdm_uos:
            for tipo in tipos:
                pm = (
                    Processo.objects.filter(setor_criacao__uo=uo, status=4, tipo_processo=tipo)
                    .annotate(x=(F('data_finalizacao') - F('data_hora_criacao')), y=(F('tipo_processo')))
                    .aggregate(Avg('x'))
                )
                pc = Processo.objects.filter(setor_criacao__uo=uo, status=4, tipo_processo=tipo).count()
                num = NumerosProcessoEletronicoTempoPorTipo()
                num.uo_origem_interessado = uo
                num.tipo = tipo
                num.tempo_medio = pm['x__avg'].days if (pm['x__avg']) else None
                num.qtd = pc
                num.save()
