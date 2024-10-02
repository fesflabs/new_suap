import sys
from datetime import datetime
from decimal import Decimal

from django.db import transaction
from django.db.models.query_utils import Q
from django.db.utils import IntegrityError

from ae.models import DemandaAlunoAtendida, DemandaAluno
from comum.utils import tl
from djtools.utils import get_client_ip
from edu.models import Aluno
from ponto.models import Maquina, MaquinaLog
from rh.models import PessoaFisica

EXCEPTION_MAQUINA_SEM_PERMISSAO_REFEICOES = 'Máquina sem permissão para registro de refeições - {}'


def registrar_refeicoes_offline(registros, operador_id):
    usernames_erro = []
    """
    Registra a refeição de modo offline, o ``horario`` deve ser confiável.
    """
    ip = get_client_ip(tl.get_request())
    try:
        maquina = Maquina.objects.get(ip=ip, ativo=True, cliente_refeitorio=True)
    except Maquina.DoesNotExist:
        return dict(ok=False, msg=EXCEPTION_MAQUINA_SEM_PERMISSAO_REFEICOES.format(ip))

    HORA_LIMITE_CAFE = 10
    HORA_LIMITE_ALMOCO = 16

    FORMATO_HORARIO = '%Y-%m-%d %H:%M:%S'
    cafe = DemandaAluno.objects.get(pk=DemandaAluno.CAFE)
    almoco = DemandaAluno.objects.get(pk=DemandaAluno.ALMOCO)
    jantar = DemandaAluno.objects.get(pk=DemandaAluno.JANTAR)
    refeicoes = list()
    demandas = Q()
    for registro in registros.split('|'):
        username, datahora = registro.split(';')
        try:
            horario = datetime.strptime(datahora, FORMATO_HORARIO)
        except ValueError:
            msg = 'Para o usuário {} Horário "{}" não está no formato "{}"'.format(username, datahora, FORMATO_HORARIO.replace('%', ''))
            MaquinaLog.objects.create(maquina=maquina, operacao='registrar_refeicoes_offline', status=MaquinaLog.ERRO, mensagem=msg)
            return dict(ok=False, msg=msg)

        if horario.hour < HORA_LIMITE_CAFE:
            demanda = cafe.id
        elif horario.hour >= HORA_LIMITE_CAFE and horario.hour < HORA_LIMITE_ALMOCO:
            demanda = almoco.id
        elif horario.hour >= HORA_LIMITE_ALMOCO:
            demanda = jantar.id

        refeicoes.append([username, horario, demanda])
        demandas |= Q(aluno__matricula=username, data=horario, demanda_id=demanda)

    refeicoes_existentes = DemandaAlunoAtendida.objects.filter(demandas).values_list('aluno__matricula', 'data', 'demanda_id')
    operador = PessoaFisica.objects.get(pk=operador_id)
    for refeicao in refeicoes:
        username, horario, demanda = refeicao
        if refeicao not in refeicoes_existentes:
            sid = transaction.savepoint()
            try:
                aluno = Aluno.objects.get(matricula=username)
                atendimento = DemandaAlunoAtendida()
                atendimento.responsavel_vinculo = operador.user.get_vinculo()
                atendimento.demanda_id = demanda
                atendimento.aluno = aluno
                atendimento.data = horario
                atendimento.quantidade = Decimal(1)
                atendimento.valor = Decimal(0)
                atendimento.observacao = 'Registrada pelo sistema'
                atendimento.terminal = maquina
                atendimento.campus = maquina.uo
                atendimento.cadastrado_por = operador.user
                atendimento.save()
                transaction.savepoint_commit(sid)
            except IntegrityError as e:
                if 'ae_demandaalunoatendida_aluno_id_key' not in ''.join(e.args):
                    usernames_erro.append(username)
                transaction.savepoint_rollback(sid)
            except Exception as e:
                usernames_erro.append(username)
                sys.stdout.write("ERRO TERMINAL")
                sys.stdout.write(str(e))
                sys.stdout.flush()
                transaction.savepoint_rollback(sid)
    if usernames_erro:
        MaquinaLog.objects.create(
            maquina=maquina, operacao='registrar_refeicoes_offline', status=MaquinaLog.ERRO, mensagem='Erros nos registros: {}'.format(','.join(usernames_erro))
        )
    else:
        MaquinaLog.objects.create(maquina=maquina, operacao='registrar_refeicoes_offline')
    return dict(ok=True, usernames_erro=';'.join(usernames_erro))


exposed = [[registrar_refeicoes_offline, 'registrar_refeicoes_offline']]
