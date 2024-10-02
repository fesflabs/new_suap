# -*- coding: utf-8 -*-
import zipfile
from datetime import datetime
from os import stat
from os.path import exists

from django.contrib import messages
from django.core.exceptions import PermissionDenied
from django.db import connection
from django.http import HttpResponse
from django.shortcuts import get_object_or_404

from chaves.forms import MovimentacaoChaveForm, BuscarUsuarioChaveForm, AdicionarChaveForm, CopiarUsuariosChaveForm, ListarUsuariosChaveForm, SetorChaveForm, PeriodoForm
from chaves.models import Chave
from comum.utils import get_uo
from djtools.utils import httprr, rtr, permission_required, get_client_ip
from ponto.models import Maquina, MaquinaLog
from rh.models import Pessoa, Servidor, PessoaFisica


def get_tabela_chaves(request):
    try:
        maquina = Maquina.objects.get(ip=get_client_ip(request), cliente_chaves=True, ativo=True)
    except Maquina.DoesNotExist:
        raise PermissionDenied('Máquina sem permissões')

    ARQUIVO_DUMP = '/tmp/tabela_chaves.zip'
    if exists(ARQUIVO_DUMP) and datetime.fromtimestamp(stat(ARQUIVO_DUMP)[-1]).date() == datetime.today():
        # Se existe um arquivo gerado no dia, este não precisa ser criado
        pass

    else:
        # Não existe arquivo gerado no dia, então precisa ser criado
        cursor = connection.cursor()
        query = """\
        CREATE TEMP TABLE tabela_terminal_ponto AS 
        SELECT c.id as id, identificacao, s.nome as sala, p.nome as predio, setor.sigla as campus
        FROM chaves_chave c
        inner join comum_sala s on c.sala_id = s.id
        inner join comum_predio p on s.predio_id = p.id
        inner join unidadeorganizacional uo on p.uo_id = uo.id
        inner join setor on uo.setor_id = setor.id
        """

        # lista somente os prédios selecionados
        if maquina.predios.exists():
            query += " where p.id IN ({})".format(",".join([str(id) for id in maquina.predios.values_list('id', flat=True)]))

        cursor.execute(query)

        # Gerando o dump
        dump_file = open('/tmp/tabela_terminal.copy', 'w')
        cursor.copy_to(dump_file, 'tabela_terminal_ponto')
        dump_file.close()

        # Removendo tabela temporária
        cursor.execute('DROP TABLE tabela_terminal_ponto')

        # Compactando o dump
        zip_file = zipfile.ZipFile(ARQUIVO_DUMP, 'w', zipfile.ZIP_DEFLATED)
        zip_file.write('/tmp/tabela_terminal.copy', 'tabela_terminal.copy')
        zip_file.close()

    # Abrindo o arquivo zipado
    dump_zip_file = open(ARQUIVO_DUMP, 'rb')
    conteudo_dump = dump_zip_file.read()
    dump_zip_file.close()

    MaquinaLog.objects.create(maquina=maquina, operacao='chaves_get_tabela_chaves')

    response = HttpResponse(conteudo_dump, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=dump_terminal.zip'
    return response


def get_tabela_permissoes(request):
    try:
        maquina = Maquina.objects.get(ip=get_client_ip(request), cliente_chaves=True, ativo=True)
    except Maquina.DoesNotExist:
        raise PermissionDenied('Máquina sem permissões')

    ARQUIVO_DUMP = '/tmp/tabela_permissoes.zip'
    if exists(ARQUIVO_DUMP) and datetime.fromtimestamp(stat(ARQUIVO_DUMP)[-1]).date() == datetime.today():
        # Se existe um arquivo gerado no dia, este não precisa ser criado
        pass

    else:
        # Não existe arquivo gerado no dia, então precisa ser criado
        cursor = connection.cursor()
        query = """\
        CREATE TEMP TABLE tabela_terminal_ponto AS 
        SELECT id, chave_id, pessoa_id from chaves_chave_pessoas
        """

        cursor.execute(query)

        # Gerando o dump
        dump_file = open('/tmp/tabela_terminal.copy', 'w')
        cursor.copy_to(dump_file, 'tabela_terminal_ponto')
        dump_file.close()

        # Removendo tabela temporária
        cursor.execute('DROP TABLE tabela_terminal_ponto')

        # Compactando o dump
        zip_file = zipfile.ZipFile(ARQUIVO_DUMP, 'w', zipfile.ZIP_DEFLATED)
        zip_file.write('/tmp/tabela_terminal.copy', 'tabela_terminal.copy')
        zip_file.close()

    # Abrindo o arquivo zipado
    dump_zip_file = open(ARQUIVO_DUMP, 'rb')
    conteudo_dump = dump_zip_file.read()
    dump_zip_file.close()

    MaquinaLog.objects.create(maquina=maquina, operacao='chaves_get_tabela_permissoes')

    response = HttpResponse(conteudo_dump, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename=dump_terminal.zip'
    return response


@rtr()
@permission_required('chaves.change_chave')
def movimentacao_chave(request):
    if request.method == 'GET' and 'chave' in request.GET:
        form = MovimentacaoChaveForm(request.GET)
        if form.is_valid():
            chave = get_object_or_404(Chave, pk=request.GET['chave'])
            title = 'Movimentação da Chave: {}'.format(chave)
            data_inicio = form.cleaned_data['data_inicio']
            data_termino = form.cleaned_data['data_termino']

            data_inicio = data_inicio.strftime("%d/%m/%Y 00:00:00")
            data_termino = data_termino.strftime("%d/%m/%Y 23:59:59")

            chave.movimentacoes = chave.movimentacao_set.filter(
                data_emprestimo__gt=datetime.strptime(data_inicio, "%d/%m/%Y %H:%M:%S"), data_emprestimo__lt=datetime.strptime(data_termino, "%d/%m/%Y %H:%M:%S")
            ).order_by('-data_emprestimo')
    else:
        return httprr('/admin/chaves/chave/')
    return locals()


@rtr()
@permission_required('chaves.poder_ver_todas, chaves.poder_ver_do_campus')
def gerenciamento_pessoas(request):
    title = 'Gerenciar Pessoas'
    form = BuscarUsuarioChaveForm(request.GET or None)
    if form.is_valid():
        usuarios = form.processar()

    return locals()


@rtr()
@permission_required('chaves.poder_ver_todas, chaves.poder_ver_do_campus')
def chaves_pessoa(request, pessoa_id):
    title = 'Chaves Associadas'
    pessoa = get_object_or_404(Pessoa, id=pessoa_id)
    todas_chaves = Chave.objects.filter(pessoas=pessoa_id)
    uo = get_uo(request.user)
    chaves_campus = todas_chaves.filter(sala__predio__uo=uo)
    if request.user.has_perm('chaves.poder_ver_todas'):
        chaves_campus = todas_chaves
    outras_chaves = todas_chaves.exclude(id__in=chaves_campus.values_list('id', flat=True))
    if request.POST:
        chaves_ids = request.POST.getlist('chaves[]')
        if chaves_ids:
            chaves_a_remover = chaves_campus.filter(id__in=chaves_ids)
            for chave_a_remover in chaves_a_remover:
                chave_a_remover.pessoas.remove(pessoa)

            messages.success(request, 'Chave(s) desassociada(s) com sucesso.')
        else:
            messages.error(request, 'Selecione alguma chave para desassociar.')

    return locals()


@rtr()
@permission_required('chaves.poder_ver_todas, chaves.poder_ver_do_campus')
def adicionar_chave(request, pessoa_id):
    title = 'Adicionar Chave'
    pessoa_fisica = get_object_or_404(PessoaFisica, id=pessoa_id)
    form = AdicionarChaveForm(request.POST or None, request=request, pessoa_fisica=pessoa_fisica)
    if form.is_valid():
        form.processar(pessoa_fisica)
        return httprr('/chaves/gerenciamento_pessoas/?nome={}'.format(pessoa_fisica.user.username), 'Chave associada com sucesso.')

    return locals()


@rtr()
@permission_required('chaves.change_chave')
def copiar_usuarios(request):
    title = 'Passo 1: Informe as Chaves de Origem e Destino'
    form = CopiarUsuariosChaveForm(request.POST or None, request=request)
    if form.is_valid():
        return httprr('/chaves/copiar_usuarios_chave/{}/{}/'.format(form.cleaned_data['chave_origem'].id, form.cleaned_data['chave_destino'].id))
    return locals()


@rtr()
@permission_required('chaves.change_chave')
def copiar_usuarios_chave(request, chave_origem_id, chave_destino_id):
    chave_origem = get_object_or_404(Chave, pk=chave_origem_id)
    chave_destino = get_object_or_404(Chave, pk=chave_destino_id)
    title = 'Passo 2: Selecione as Pessoas que terão acesso à chave {}'.format(chave_destino)
    form = ListarUsuariosChaveForm(request.POST or None, chave_origem=chave_origem, chave_destino=chave_destino)
    if form.is_valid():
        for pessoa in form.cleaned_data['pessoas']:
            chave_destino.pessoas.add(pessoa)

        return httprr('/admin/chaves/chave/', 'Pessoas cadastradas na sala de destino com sucesso.')

    return locals()


@rtr()
@permission_required('chaves.change_chave')
def associar_setor_a_chave(request):
    title = 'Liberar Chaves aos Servidores do Setor'
    form = SetorChaveForm(request.POST or None, request=request)
    if form.is_valid():
        chaves = form.cleaned_data.get('chaves')
        setor = form.cleaned_data.get('setor')
        servidores = Servidor.objects.ativos().filter(setor=setor)
        for chave in chaves:
            for servidor in servidores:
                chave.pessoas.add(servidor)

        return httprr('/admin/chaves/chave/', 'Pessoas cadastradas na sala de destino com sucesso.')

    return locals()


@rtr()
@permission_required('chaves.change_chave')
def chaves_emprestadas(request):
    title = 'Chaves Emprestadas e Não Devolvidas'
    chaves = Chave.objects.all()
    if not (request.user.is_superuser or request.user.has_perm('chaves.poder_ver_todas')):
        chaves = chaves.filter(sala__predio__uo=get_uo(request.user))

    form = PeriodoForm(request.POST or None)
    if form.is_valid():
        data_inicio = form.cleaned_data['data_inicio']
        data_termino = form.cleaned_data['data_termino']
        chaves_emprestadas = list()
        for chave in chaves:
            if chave.movimentacao_set.filter(data_emprestimo__gt=data_inicio, data_emprestimo__lt=data_termino).exists():
                mais_recente = chave.movimentacao_set.filter(data_emprestimo__gt=data_inicio, data_emprestimo__lt=data_termino).order_by('-data_emprestimo')[0]
                if not mais_recente.pessoa_devolucao:
                    chaves_emprestadas.append(mais_recente)

    return locals()
