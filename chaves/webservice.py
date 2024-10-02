# -*- coding: utf-8 -*-

import xmlrpc.client

from django.db import transaction

from chaves.models import Chave, Movimentacao
from comum.utils import get_uo, tl
from comum.models import User
from djtools.utils import get_client_ip
from ponto.models import Maquina, MaquinaLog
from rh.models import PessoaFisica, Pessoa

DB_ENCODING = 'utf-8'
CLIENT_ENCODING = 'latin-1'
EXCEPTION_MAQUINA_SEM_PERMISSAO_CHAVES = 'A Máquina com ip {} não tem permissão para o módulo de chaves'
EXCEPTION_CHAVE_NAO_ENCONTRADA = 'A chave {} não foi encontrada'
MSG_USUARIO_SEM_CAMPUS = 'O usuário não está relacionado a nenhum Campus!'


def get_dados_chave(session_pk, chave_identificacao):
    """
    Retorna dados relevantes sobre a chave.

    Variáveis de retorno:
    1) ok : bool
    2) disponivel : bool
    3) pessoas_permitidas: dict
        {pessoa_id:str = [pessoa_nome:str, 
                          template:xmlrpcbin, pode_registrar_sem_digital:bool]}
    4) pessoa_emprestimo : str (pessoa que está com a chave caso ela esteja emprestada)
    """
    try:
        ip = get_client_ip(tl.get_request())
        maquina = Maquina.objects.get(ip=ip, cliente_chaves=True, ativo=True)
    except Maquina.DoesNotExist:
        return dict(ok=False, msg=EXCEPTION_MAQUINA_SEM_PERMISSAO_CHAVES.format(ip))

    # Testando se o usuário está num Campus
    user = User.objects.get(username=session_pk)
    pessoa_emprestimo = ''
    user_uo = get_uo(user)
    if not user_uo:
        return dict(ok=False, msg=MSG_USUARIO_SEM_CAMPUS)

    # Testando se existe chave no campus do usuário com a identificação passada
    try:
        chave = Chave.objects.get(identificacao=chave_identificacao, ativa=True, sala__predio__uo=user_uo)
        if not chave.disponivel:
            m = chave.movimentacao_set.get(data_devolucao=None)
            pessoa_emprestimo = str(m.pessoa_emprestimo)
    except Chave.DoesNotExist:
        return dict(ok=False, msg=EXCEPTION_CHAVE_NAO_ENCONTRADA.format(chave_identificacao))

    # Pegando dados das pessoas permitidas para a chave
    pessoas_permitidas = {}
    lista = []
    for id in chave.pessoas.values_list('id', flat=True):
        lista.append(id)
    lista.append(user.get_profile().pk)
    for pf in PessoaFisica.objects.filter(id__in=lista):
        pessoas_permitidas[str(pf.pk)] = [pf.nome, xmlrpc.client.Binary(pf.get_template(CLIENT_ENCODING)), pf.tem_digital_fraca]
    MaquinaLog.objects.create(maquina=maquina, operacao='chaves_get_dados_chave')
    return dict(ok=True, disponivel=chave.disponivel, pessoas_permitidas=pessoas_permitidas, pessoa_emprestimo=pessoa_emprestimo)


def efetuar_emprestimo_ou_devolucao(session_pk, chave_identificacao, pessoa_emprestimo, observacao):
    ip = get_client_ip(tl.get_request())
    try:
        maquina = Maquina.objects.get(ip=ip, cliente_chaves=True, ativo=True)
    except Maquina.DoesNotExist:
        return dict(ok=False, msg=EXCEPTION_MAQUINA_SEM_PERMISSAO_CHAVES.format(ip))

    # Testando se o usuário está num Campus
    user = User.objects.get(username=session_pk)
    user_uo = get_uo(user)
    if not user_uo:
        return dict(ok=False, msg=MSG_USUARIO_SEM_CAMPUS)

    # Testando se existe chave no campus do usuário com a identificação passada
    try:
        chave = Chave.objects.get(identificacao=chave_identificacao, ativa=True, sala__predio__uo=user_uo)
    except Chave.DoesNotExist:
        return dict(ok=False, msg=EXCEPTION_CHAVE_NAO_ENCONTRADA.format(chave_identificacao))

    pessoa_emprestimo = Pessoa.objects.get(pk=pessoa_emprestimo)

    if chave.disponivel and not chave.pessoa_permitida(pessoa_emprestimo):
        msg = 'Pessoa não permitida'
        MaquinaLog.objects.create(maquina=maquina, operacao='chaves_efetuar_emprestimo_ou_devolucao', status=MaquinaLog.ERRO, mensagem=msg)
        return dict(ok=False, msg=msg)

    try:
        if chave.disponivel:
            msg = 'Empréstimo realizado com sucesso'
            MaquinaLog.objects.create(maquina=maquina, operacao='chaves_efetuar_emprestimo_ou_devolucao', mensagem=msg)
            chave._efetuar_emprestimo(pessoa_emprestimo, user.get_profile(), observacao)
            return dict(ok=True, msg=msg)
        else:
            msg = 'Devolução realizada com sucesso'
            MaquinaLog.objects.create(maquina=maquina, operacao='chaves_efetuar_emprestimo_ou_devolucao', mensagem=msg)
            chave._efetuar_devolucao(pessoa_emprestimo, user.get_profile(), observacao)
            return dict(ok=True, msg=msg)
    except Exception as e:
        msg = str(e)
        MaquinaLog.objects.create(maquina=maquina, operacao='chaves_efetuar_emprestimo_ou_devolucao', status=MaquinaLog.ERRO, mensagem=msg)
        return dict(ok=False, msg=msg)


def importar_emprestimos(dados):
    try:
        ip = get_client_ip(tl.get_request())
        maquina = Maquina.objects.get(ip=ip, cliente_chaves=True, ativo=True)
    except Maquina.DoesNotExist:
        return dict(ok=False, msg=EXCEPTION_MAQUINA_SEM_PERMISSAO_CHAVES.format(ip))

    erros = []
    for registro in dados.split('\n'):
        movimentacao_id = None
        try:
            sid = transaction.savepoint()
            movimentacao_id = inserir_movimentacao(registro)
            transaction.savepoint_commit(sid)
        except Exception:
            erros.append(movimentacao_id)
            transaction.savepoint_rollback(sid)
    if erros:
        msg = 'Erros: {}'.format(','.join(erros))
        MaquinaLog.objects.create(maquina=maquina, operacao='importar_emprestimos', status=MaquinaLog.ERRO, mensagem=msg)
    else:
        MaquinaLog.objects.create(maquina=maquina, operacao='importar_emprestimos')
    return dict(ok=True, erros=';'.join(erros))


def inserir_movimentacao(registro):
    if registro:
        registros = registro.replace('\tnull', '\t').split('\t')
        terminal_antigo = len(registros) == 9
        if terminal_antigo:
            chave_id, operador_emprestimo_id, pessoa_emprestimo_id, data_emprestimo, observacao_emprestimo, operador_devolucao_id, pessoa_devolucao_id, data_devolucao, observacao_devolucao = (
                registros
            )
        else:
            movimentacao_id, chave_id, operador_emprestimo_id, pessoa_emprestimo_id, data_emprestimo, observacao_emprestimo, operador_devolucao_id, pessoa_devolucao_id, data_devolucao, observacao_devolucao = (
                registros
            )

        data_emprestimo = data_emprestimo if data_emprestimo else None
        operador_emprestimo_id = operador_emprestimo_id if operador_emprestimo_id else None
        pessoa_emprestimo_id = pessoa_emprestimo_id if pessoa_emprestimo_id else None

        data_devolucao = data_devolucao if data_devolucao else None
        operador_devolucao_id = operador_devolucao_id if operador_devolucao_id else None
        pessoa_devolucao_id = pessoa_devolucao_id if pessoa_devolucao_id else None

        if Movimentacao.objects.filter(chave_id=chave_id, data_devolucao=data_devolucao).exists():
            movimentacao_errada = Movimentacao.objects.filter(chave_id=chave_id, data_devolucao=data_devolucao)[0]
            movimentacao_errada.data_devolucao = None
            movimentacao_errada.save()

        # empréstimo e devolução
        movimentacao, novo = Movimentacao.objects.update_or_create(
            chave_id=chave_id,
            data_emprestimo=data_emprestimo if data_emprestimo else None,
            defaults={
                'data_devolucao': data_devolucao if data_devolucao else None,
                'operador_emprestimo_id': operador_emprestimo_id if operador_emprestimo_id else None,
                'pessoa_emprestimo_id': pessoa_emprestimo_id if pessoa_emprestimo_id else None,
                'observacao_emprestimo': observacao_emprestimo,
                'operador_devolucao_id': operador_devolucao_id if operador_devolucao_id else None,
                'pessoa_devolucao_id': pessoa_devolucao_id if pessoa_devolucao_id else None,
                'observacao_devolucao': observacao_devolucao,
            },
        )

        if terminal_antigo:
            return ''
        else:
            return movimentacao_id


exposed = [[get_dados_chave, 'chaves/get_dados_chave'], [efetuar_emprestimo_ou_devolucao, 'chaves/efetuar_emprestimo_ou_devolucao'], [importar_emprestimos, 'importar_emprestimos']]
