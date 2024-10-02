# -*- coding: utf-8 -*-

from django.db import transaction

from djtools.management.commands import BaseCommandPlus
from documento_eletronico.models import Assinatura
from documento_eletronico.utils import processar_template_ckeditor, get_variaveis, EstagioProcessamentoVariavel
from processo_eletronico.models import Tramite, ModeloDespacho, AssinaturaTramite, AssinaturaParecerSimples, \
    ParecerDocumentoTexto
from processo_eletronico.models import gerar_assinatura_tramite_senha


class Command(BaseCommandPlus):
    """
        Command criado para reassinar os depachos devido a um erro ao processamento
        das variáveis
    """

    def handle(self, *args, **options):
        self.reassinar_despachos()

    def reassinar_despachos(self):
        for tramite in Tramite.objects.all():
            sid = transaction.savepoint()
            try:
                # Removendo assinatura
                modelo = ModeloDespacho.get_modelo()
                assinatura_tramite_antiga = AssinaturaTramite.objects.filter(tramite=tramite).first()

                hash_antigo = tramite.hash_conteudo

                variaveis = get_variaveis(
                    documento_identificador='', estagio_processamento_variavel=EstagioProcessamentoVariavel.ASSINATURA_DOCUMENTO, usuario=tramite.remetente_pessoa.pessoafisica.user
                )
                tramite.cabecalho_observacao_encaminhamento = processar_template_ckeditor(texto=modelo.cabecalho, variaveis=variaveis)
                tramite.rodape_observacao_encaminhamento = processar_template_ckeditor(texto=modelo.rodape, variaveis=variaveis)

                if hash_antigo == tramite.hash_conteudo:
                    print(("Tramite %s já processado " % tramite))
                    continue

                # Assinando encaminhamento
                assinatura = Assinatura()
                assinatura.pessoa = assinatura_tramite_antiga.assinatura.pessoa
                assinatura.papel = assinatura_tramite_antiga.assinatura.papel
                assinatura.nome_papel = assinatura_tramite_antiga.assinatura.nome_papel
                assinatura.hmac = gerar_assinatura_tramite_senha(tramite, tramite.remetente_pessoa)

                #
                print(("Removendo assinatura %s" % assinatura_tramite_antiga))
                assinatura_tramite_antiga.delete()

                tramite.save()
                assinatura.save()
                #
                assinatura_tramite = AssinaturaTramite()
                assinatura_tramite.tramite = tramite
                assinatura_tramite.assinatura = assinatura
                assinatura_tramite.save()
                print(("Criando %s" % assinatura_tramite))
                transaction.savepoint_commit(sid)
            except Exception as e:
                transaction.savepoint_rollback(sid)
                import sys
                import traceback

                exc_type, exc_value, exc_traceback = sys.exc_info()
                print("*** print_tb:")
                traceback.print_tb(exc_traceback, limit=1, file=sys.stdout)
                print("*** print_exception:")
                traceback.print_exception(exc_type, exc_value, exc_traceback, limit=2, file=sys.stdout)
                print("*** print_exc:")
                traceback.print_exc()
                print("*** format_exc, first and last line:")
                formatted_lines = traceback.format_exc().splitlines()
                print((formatted_lines[0]))
                print((formatted_lines[-1]))
                print("*** format_exception:")
                print((repr(traceback.format_exception(exc_type, exc_value, exc_traceback))))
                print("*** extract_tb:")
                print((repr(traceback.extract_tb(exc_traceback))))
                print("*** format_tb:")
                print((repr(traceback.format_tb(exc_traceback))))
                print(("*** tb_lineno:", exc_traceback.tb_lineno))
                raise e

    def reassinar_parecer(self):

        for parecer in ParecerDocumentoTexto.objects.all():
            # Removendo assinatura
            assinatura_antiga = AssinaturaParecerSimples.objects.filter(parecer=parecer)
            usuario = assinatura_antiga.pessoa.user
            papel = assinatura_antiga.papel
            assinatura_antiga.delete()
            parecer.assinar_via_senha(usuario, papel)
            parecer.save()
