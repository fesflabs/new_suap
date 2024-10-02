# -*- coding: utf-8 -*-

from djtools.management.commands import BaseCommandPlus
from django.core.files.base import ContentFile
from conectagov_pen.processa_pendencias import receber_processo, atualizar_tramite_barramento_recebido
from conectagov_pen.models import TramiteBarramento, DocumentoProcessoBarramento


class Command(BaseCommandPlus):
    def handle(self, *args, **options):
        title = 'Conectagov / barramento - Comando para receber/criar no SUAP processos pendentes de recebimento ' 'que estão com tramite concluido no barramento'
        print('')
        print(('- ' * len(title)))
        print(title)
        print(('- ' * len(title)))

        executar_command = input('Informe o que deseja fazer? (SIMULAR/EXECUTAR) ').strip().upper()

        if executar_command == 'EXECUTAR':
            executar = True
        elif executar_command == 'SIMULAR':
            executar = False

        processar_tramites_recebidos_no_barramento_nao_gerados_no_suap(executar=executar)
        print("FIM DO PROCESSAMENTO")


def processar_tramites_recebidos_no_barramento_nao_gerados_no_suap(executar=False):
    # Tramites barramento com status pendente de recebimento e que nao possui processo gerado no suap
    tramites_barramento_pendentes_recebimento = TramiteBarramento.objects.filter(status=TramiteBarramento.STATUS_PENDENTE_RECEBIMENTO, processo_barramento__processo__isnull=True)
    if tramites_barramento_pendentes_recebimento.exists():
        print(("Existem {} trâmites do barramento pendentes de recebimento".format(tramites_barramento_pendentes_recebimento.count())))
        for tramite_barramento in tramites_barramento_pendentes_recebimento:
            # Verifica se o tramite está com situação 6 (recibo de conclusao) no barramento, caso positivo realiza
            # a rotina para criar o processo no SUAP
            # if tramite_barramento.foi_recebido_no_destino:
            print(
                (
                    "O tramite do barramendo de id nº {} - processo nº {} já foi está na situação 6 "
                    "(recibo de conclusao recebido) mas devido a erro nao foi criado no SUAP".format(
                        tramite_barramento.id_tramite_barramento, tramite_barramento.metadados_processo['processo']['protocolo']
                    )
                )
            )
            documentos_recebidos = list()
            for doc in tramite_barramento.metadados_processo['processo']['documentos']:
                for comp in doc['componentesDigitais']:
                    hash_componente = comp['hash']['conteudo']
                    documento_armazenado = DocumentoProcessoBarramento.objects.get(hash_para_barramento=hash_componente)
                    conteudo_documento = ContentFile(documento_armazenado.conteudo_arquivo).read()
                    conteudo_documento = conteudo_documento.decode("utf-8")
                    documentos_recebidos.append(
                        {
                            'idt': tramite_barramento.id_tramite_barramento,
                            'protocolo': tramite_barramento.metadados_processo['processo']['protocolo'],
                            'ordem': doc['ordem'],
                            'assunto': doc['descricao'],
                            'id_tipo_doc_pen': doc['especie']['codigo'],
                            'nome_tipo_doc_pen': doc['especie']['nomeNoProdutor'],
                            'conteudo': conteudo_documento,
                            'hash': hash_componente,
                            'nome_arquivo': comp['nome'],
                            'tipo_conteudo': comp['tipoDeConteudo'],  # txt = html,etc - #out
                            'tipo_arquivo': comp['mimeType'],
                            'complemento_tipo_arquivo': comp['dadosComplementaresDoTipoDeArquivo'],
                            'nivel_acesso': doc['nivelDeSigilo'],
                        }
                    )
            print(("O processo nº {} será criado no suap com os seguintes documentos:".format(tramite_barramento.metadados_processo['processo']['protocolo'])))
            for documento in documentos_recebidos:
                print(('Documento {}: {} com assunto: {} - HASH: {}'.format(documento['ordem'], documento['nome_arquivo'], documento['assunto'], documento['hash'])))
            if executar:
                # try:
                processo_suap = receber_processo(tramite_barramento.metadados_processo, documentos_recebidos, tramite_barramento.processo_barramento, tramite_barramento)
                atualizar_tramite_barramento_recebido(
                    tramite_barramento, tramite_barramento.metadados_processo, tramite_barramento.tramite_externo_recibo_conclusao_json, tramite_barramento.documentos
                )
                print(("Executado com sucesso, processo {} criado/recebido".format(processo_suap)))
            else:
                print("SIMULAÇÃO - Use a opção EXECUTAR para criar/receber o processo")
