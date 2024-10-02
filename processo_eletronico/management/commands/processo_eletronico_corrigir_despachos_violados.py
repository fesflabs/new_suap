# -*- coding: utf-8 -*-
from django.apps import apps
from django.db import transaction
from django.db.models.query_utils import Q

from djtools.management.commands import BaseCommandPlus
from processo_eletronico.models import gerar_assinatura_tramite_senha


class Command(BaseCommandPlus):
    @transaction.atomic()
    def handle(self, *args, **options):
        title = 'Processo Eletrônico - Command que corrige os despachos dos trâmites que apresentam a mensagem "Esse despacho foi violado"'
        print('')
        print(('- ' * len(title)))
        print(title)
        print(('- ' * len(title)))

        print(
            'Cenário exemplo: Suponhamos que temos dois processos, A e B, sendo que B está apensado a A. Ao tentar tramitar '
            'A com um despacho simples, o sistema primeiramente fazia o trâmite de B (Despacho #100), não realizava a assinatura do '
            'despacho desse trâmite, daí em seguida realizava o trâmite de A (Despacho #101) e assinava o despacho do trâmite de A. '
            'Como resultado disso, o despacho do trâmite de B ficava sem assinatura e assim gerava o erro "Esse despacho foi '
            'violado" quando o usuário clicava em "Visualizar Processo". '
        )

        print()
        print(
            'O objetivo deste command é varrer todos os trâmites com despacho violado, ou seja, sem a respecitivas assinaturas '
            'e criar as assinaturas, com base na assinatura do trâmite "irmão" do processo apensado. Obs: Este command funciona '
            'independentemente da quantidade de processos unidos por apensamento.'
        )

        executar_command = options.get('executar_command') or input('Deseja continuar? (S/n)').strip().upper() == 'S'
        if not executar_command:
            print()
            print('Processamento abortado.')
            return

        Tramite = apps.get_model("processo_eletronico", "Tramite")
        ApensamentoProcesso = apps.get_model("processo_eletronico", "ApensamentoProcesso")
        Assinatura = apps.get_model("documento_eletronico", "Assinatura")
        AssinaturaTramite = apps.get_model("processo_eletronico", "AssinaturaTramite")

        tramites_com_despachos_violados = Tramite.objects.filter(Q(despacho_corpo__isnull=False) & ~Q(despacho_corpo='')).filter(assinaturatramite__isnull=True)

        if tramites_com_despachos_violados.count() > 0:
            print(('Foram encontrados {} trâmites com despachos violados'.format(tramites_com_despachos_violados.count())))
        else:
            print('Nenhum trâmite com despacho violado encontrado.')

        tramites_irmaos = list()
        msg_erro = list()
        for t in tramites_com_despachos_violados:
            # for t in tramites_com_despachos_violados[1:2]:
            # processos_apensados_pks = t.processo.get_processos_apensados().values_list('id', flat=True)
            apensamentos = t.processo.apensamentoprocesso_set.values_list('apensamento', flat=True)
            processos_irmaos_apensados = ApensamentoProcesso.objects.filter(apensamento__in=apensamentos).exclude(processo=t.processo).values_list('processo', flat=True)

            # Tentando localizar o trâmite irmão, ou seja, aquele que tem as mesmas características do trâmite em questão
            # e que tem a assinatura criada.
            tramite_irmao_assinado = Tramite.objects.filter(
                # data_hora_encaminhamento = t.data_hora_encaminhamento,
                # data_hora_recebimento = t.data_hora_recebimento,
                # despacho_cabecalho = t.despacho_cabecalho,
                despacho_corpo=t.despacho_corpo,
                # despacho_rodape = t.despacho_rodape,
                # pessoa_recebimento = t.pessoa_recebimento,
                remetente_setor=t.remetente_setor,
                remetente_pessoa=t.remetente_pessoa,
                destinatario_setor=t.destinatario_setor,
                destinatario_pessoa=t.destinatario_pessoa,
                # Fazendo a busca somente nos trâmites dos processos irmãos envolvidos nos apensamentos.
                processo__in=processos_irmaos_apensados,
                # Buscando o trâmite que tem a assinatura. Isso porque o bug em questão pode envolver "n" processos.
                # Ex: Num caso de um apensamento envolvendo 4 processos, 3 deles tiveram o despachos não assinados.
                assinaturatramite__isnull=False,
            )
            # print t.processo
            # print t
            # print tramite_irmao_assinado
            # print

            qtd_tramite_irmao = tramite_irmao_assinado.count()
            if qtd_tramite_irmao == 1:
                tramites_irmaos.append({'tramite_nao_assinado': t, 'tramite_irmao_assinado': tramite_irmao_assinado.first()})
            else:
                msg_erro.append('Total de trâmites irmãos para o trâmite {}: {}.'.format(t, qtd_tramite_irmao))

        if msg_erro:
            raise Exception('Há trâmites para os quais não foi possível obter o trâmite irmão. Detalhes:\n' + '\n'.join(msg_erro))

        if tramites_irmaos:
            print('Iniciando a geração das assinaturas para os trâmites com "despachos violados" (sem assinatura)...')

            i = 0
            for ti in tramites_irmaos:
                i += 1

                tramite_nao_assinado = ti['tramite_nao_assinado']
                tramite_irmao_assinado = ti['tramite_irmao_assinado']

                print()
                print(('=' * 100))
                print(
                    ('{}º - Trâmite não assinado: #{} (Processo {} - id: {})'.format(i, tramite_nao_assinado.id, tramite_nao_assinado.processo, tramite_nao_assinado.processo.id))
                )
                print(('=' * 100))
                print(
                    ('Trâmite irmão assinado: #{} (Processo {} - id: {}), '.format(tramite_irmao_assinado.id, tramite_irmao_assinado.processo, tramite_irmao_assinado.processo.id))
                )
                print(('- Hash do conteúdo: {}'.format(tramite_irmao_assinado.hash_conteudo)))
                print(('- Hmac da assinatura: {}'.format(tramite_irmao_assinado.assinaturatramite.assinatura.hmac)))

                assinatura_base_para_copia = tramite_irmao_assinado.assinaturatramite.assinatura

                # Criando a assinatura para o trâmite não assinado.
                assinatura = Assinatura()
                assinatura.pessoa = assinatura_base_para_copia.pessoa
                assinatura.papel = assinatura_base_para_copia.papel
                assinatura.nome_papel = assinatura_base_para_copia.nome_papel
                assinatura.hmac = gerar_assinatura_tramite_senha(tramite_nao_assinado, assinatura_base_para_copia.pessoa)
                assinatura.save()
                # Forçando que a assinatura fique com o mesmo valor da assinatura base, uma vez que o atributo  "data_assinatura"
                # está com o "auto_now_add", ou seja, data automática apenas no ato da inserção.
                assinatura.data_assinatura = assinatura_base_para_copia.data_assinatura
                assinatura.save()

                assinatura_tramite = AssinaturaTramite()
                assinatura_tramite.tramite = tramite_nao_assinado
                assinatura_tramite.assinatura = assinatura
                assinatura_tramite.save()

                print()
                print(('Assinatura do trâmite #{} gerada com sucesso!'.format(tramite_nao_assinado.id)))
                print(('- Hash do conteúdo: {}'.format(tramite_nao_assinado.hash_conteudo)))
                print(('- Hmac da assinatura: {}'.format(tramite_nao_assinado.assinaturatramite.assinatura.hmac)))
        print()
        print('FIM')
