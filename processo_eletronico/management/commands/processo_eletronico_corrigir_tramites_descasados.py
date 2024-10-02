# -*- coding: utf-8 -*-
from django.apps import apps
from django.db import transaction
from django.db.models import F, Max, Q

from djtools.management.commands import BaseCommandPlus


class Command(BaseCommandPlus):
    def print_title(self, title):
        print()
        print(('=' * len(title)))
        print(title)
        print(('=' * len(title)))

    @transaction.atomic()
    def handle(self, *args, **options):
        title = 'Processo Eletrônico - Command que corrige os trâmites "descasados"'
        print('')
        print(('- ' * len(title)))
        print(title)
        print(('- ' * len(title)))

        print(
            'Cenário exemplo: Alguns processos não estavam podendo ser recebidos. Ao tentar recebê-los estava ocorrendo\n'
            'o erro \"turned more than one Tramite -- it returned 2\".  No caso identificamos que o problema é porque\n'
            'alguns processos estão com mais de um trâmite "em aberto". Possivelmente isso ocorreu na época em que\n'
            'havia um bug que permitia a remoção do último trâmite de um processo mas o mesmo não ocorria com os \n'
            'processos apensados.'
        )

        print()
        print(
            'O objetivo deste command é identificar esses trâmites "descasados" e removê-los. Aproveitamos a ocorrência\n'
            'para verificar também se todos os processos estão com a referência correta no atributo "último trâmite".'
        )

        print()
        executar_command = options.get('executar_command') or input('Deseja continuar? (S/n)').strip().upper() == 'S'
        if not executar_command:
            print()
            print('Processamento abortado.')
            return

        Processo = apps.get_model('processo_eletronico', 'Processo')
        Tramite = apps.get_model('processo_eletronico', 'Tramite')

        self.print_title('Verificando se todos os processos estão com o último trâmite correto...')
        processos_com_ultimo_tramite_errado = Processo.objects.annotate(max_ultimo_tramite_id=Max('tramites__id')).filter(~Q(max_ultimo_tramite_id=F('ultimo_tramite__id')))
        if processos_com_ultimo_tramite_errado:
            print(('Existem {} processos com o último trâmite errado.'.format(processos_com_ultimo_tramite_errado.count())))
            print('Iniciando a correção...')
            for p in processos_com_ultimo_tramite_errado:
                print()
                print(('<<< Processo {} (id: {}) >>> '.format(p, p.id)))
                print((' - Corrigindo o último trâmite de id #{} para id #{}'.format(p.ultimo_tramite.id, p.max_ultimo_tramite_id)))
                p.ultimo_tramite = Tramite.objects.get(pk=p.max_ultimo_tramite_id)
                p.save()
            print()
            print('Correção finalizada com sucesso.')
        else:
            print('Todos os processos estão com o último trâmite correto. Nenhum ajuste é necessário.')

        self.print_title('Verificando se há trâmites descasados...')
        # Procurando todos os trâmites em aberto anteriores ao último trâmite do processo.
        tramites_descasados = Tramite.objects.filter(data_hora_recebimento__isnull=True, id__lt=F('processo__ultimo_tramite__id')).order_by('processo__id')
        if tramites_descasados:
            print(('Existem {} trâmites descasados.'.format(tramites_descasados.count())))
            print('Iniciando a correção...')
            for t in tramites_descasados:
                if t.processo.apensamentoprocesso_set.exists():
                    processo_tem_registro_apensamento = 'Sim'
                else:
                    processo_tem_registro_apensamento = 'Não'

                print()
                print(('<<< Processo {} (id: {}, tem/teve apensamentos: {}) >>>'.format(t.processo, t.processo.id, processo_tem_registro_apensamento)))
                print(('Trâmite descasado: #{}'.format(t.id)))
                print((' - Data Hora Encaminhamento: {}'.format(t.data_hora_encaminhamento.strftime('%d/%m/%Y %H:%M:%S'))))
                print(' - Remetente:')
                print(('    - Setor: {}'.format(t.remetente_setor)))
                print(('    - Pessoa: {}'.format(t.remetente_pessoa)))
                print(('    - Despacho: {}'.format(t.despacho_corpo or '')))
                print(' - Destinatário:')
                print(('     - Setor: {}'.format(t.destinatario_setor or '')))
                print(('     - Pessoa: {}'.format(t.destinatario_pessoa or '')))
                t.delete()

            print()
            print('Todos os trâmites descasados foram removidos com sucesso.')
        else:
            print('Não há trâmites descasados. Nenhum ajuste é necessário.')

        print()
        print('FIM')
