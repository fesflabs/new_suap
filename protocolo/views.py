from datetime import datetime, timedelta
from django.conf import settings
from django.shortcuts import get_object_or_404
from djtools.utils.response import render_to_string
from django.apps import apps
from comum.models import Configuracao, PrestadorServico
from comum.utils import get_setor, get_todos_setores, enviar_para_impressao
from djtools import layout
from djtools.utils import rtr, httprr, render, to_ascii, permission_required, get_session_cache
from protocolo import pdf, pdfa3
from protocolo.etiqueta import imprimir_etiqueta
from protocolo.forms import (
    TramiteFormReceber,
    ProcessoFormFinalizar,
    TramiteFormEncaminharFactory,
    TramiteFormInformarRecebimentoExterno,
    TramiteFormRetornarProcessoParaAmbitoInterno,
    ProtocoloForm,
)
from protocolo.models import Processo, Tramite
from rh.models import Setor, Servidor


@layout.servicos_anonimos()
def servicos_anonimos(request):
    servicos_anonimos = list()

    servicos_anonimos.append(dict(categoria='Consultas', url="/protocolo/consulta_publica", icone="file-alt", titulo='Processos Físicos'))

    return servicos_anonimos


@layout.quadro('Protocolo', icone='file', pode_esconder=True)
def index_quadros(quadro, request):
    def do():

        if request.user.has_perm('protocolo.pode_tramitar_processo'):
            funcionario_logado = request.user.get_relacionamento()
            if type(funcionario_logado) in [Servidor, PrestadorServico]:
                meus_setores = (Setor.objects.filter(pk=funcionario_logado.setor.pk) | funcionario_logado.setores_adicionais.all()).distinct()
                processos_aguardando_recebimento = Tramite.get_caixa_entrada(meus_setores).filter(
                    data_recebimento__isnull=True, data_encaminhamento__gte=datetime.today() - timedelta(90)
                )
                processos_aguardando_encaminhamento = Tramite.get_caixa_entrada(meus_setores).filter(
                    data_recebimento__isnull=False, data_encaminhamento__gte=datetime.today() - timedelta(90)
                )
                if processos_aguardando_recebimento.exists():
                    quadro.add_item(
                        layout.ItemContador(
                            titulo='Processos a receber',
                            subtitulo='Dos últimos 90 dias',
                            qtd=processos_aguardando_recebimento.count(),
                            url='/protocolo/caixa_entrada_saida/?tab=0&setor=todos',
                        )
                    )
                if processos_aguardando_encaminhamento.exists():
                    quadro.add_item(
                        layout.ItemContador(
                            titulo='Processos a encaminhar',
                            subtitulo='Dos últimos 90 dias',
                            qtd=processos_aguardando_encaminhamento.count(),
                            url='/protocolo/caixa_entrada_saida/?tab=1&setor=todos',
                        )
                    )

        if request.user.groups.filter(name='Cadastrador de processos') and request.user.has_perm('protocolo.add_processo'):
            quadro.add_item(layout.ItemAcessoRapido(titulo='Adicionar Processo', icone='plus', url='/admin/protocolo/processo/add/', classe='success'))

        return quadro

    return get_session_cache(request, 'index_quadros_protocolo', do, 24 * 3600)


@rtr()
@permission_required('protocolo.pode_ver_processo')
def processo(request, processo_id):
    processo = get_object_or_404(Processo, id=processo_id)

    if processo.tem_vinculo_com_processo_eletronico:
        return httprr(processo.get_absolute_url())

    title = 'Processo %s' % processo
    tramites_processo = processo.tramite_set.order_by('ordem')
    if not request.user.groups.filter(name__in=['Tramitador de processos', 'Cadastrador de processos']).exists():
        if not Processo.objects.filter(id=processo_id, interessado_documento=request.user.get_profile().cpf).exists():
            return httprr('..', 'Você não tem permissão para visualizar este processo.', 'error')

    if tramites_processo:
        ultimo_tramite = processo.get_ultimo_tramite()
        if get_setor():
            caixas = Tramite.get_caixas()
            if ultimo_tramite in caixas['entrada']:
                na_caixa_entrada = True
            if ultimo_tramite in caixas['saida'] or ultimo_tramite in Tramite.get_caixa_tramitacao_externa():
                na_caixa_saida = True

    if request.user.has_perm('protocolo.pode_gerar_capa'):
        link_capa_processo = "/protocolo/capa_processo/%d/" % processo.id
        link_capa_processo_a3 = "/protocolo/capa_processo_a3/%d/" % processo.id

    if 'ponto' in settings.INSTALLED_APPS:
        Maquina = apps.get_model('ponto', 'Maquina')
        maquinas = Maquina.get_maquinas_impressao(request.user)
    link_compovante_processo = "/protocolo/processo_imprimir_comprovante/%d/" % processo.id
    if processo.pode_editar_processo(request.user):
        link_processo_editar = "/admin/protocolo/processo/%d/" % processo.id

    if (processo.status == Processo.STATUS_FINALIZADO) and (ultimo_tramite.orgao_interno_recebimento in get_todos_setores(request.user)):
        link_processo_remover_finalizacao = "/protocolo/processo_remover_finalizacao/%d" % processo.id

    if processo.status in [Processo.STATUS_FINALIZADO, Processo.STATUS_ARQUIVADO]:
        processo_dados_finalizacao = dict()
        processo_dados_finalizacao['ordem'] = len(tramites_processo) + 1
        processo_dados_finalizacao['setor'] = tramites_processo.order_by('-ordem')[0].orgao_interno_recebimento
        processo_dados_finalizacao['data_finalizacao'] = processo.data_finalizacao
        processo_dados_finalizacao['vinculo_finalizacao'] = processo.vinculo_finalizacao
        processo_dados_finalizacao['observacao_finalizacao'] = processo.observacao_finalizacao

    arquivos_processo = processo.arquivo_set.all()

    return locals()


@permission_required('protocolo.pode_gerar_capa, rsc.add_processorsc')
def processo_capa(request, processo_id):
    """Gera a capa PDF do Processo"""
    return pdf.imprimir_capa(Processo.objects.get(pk=processo_id))


@permission_required('protocolo.pode_gerar_capa')
def processo_capa_a3(request, processo_id):
    """Gera a capa PDF do Processo"""
    return pdfa3.imprimir_capa_a3(Processo.objects.get(pk=processo_id))


@rtr()
@permission_required('protocolo.pode_tramitar_processo')
def caixa_entrada_saida(request):
    title = 'Caixa de Entrada / Saída'
    setor = get_setor(request.user)
    if setor is not None:

        if request.GET.get('setor') is not None:
            try:
                setores_ids = int(request.GET.get('setor'))
            except Exception:
                setores_ids = None
            if setores_ids:
                setor_escolhido = Setor.objects.get(pk=setores_ids)
                setores = Setor.objects.filter(pk=setores_ids)  # deve ser queryset
            else:
                setores = Setor.objects.filter(pk=setor.id)  # deve ser queryset
        else:
            setor_escolhido = Setor.objects.get(pk=setor.id)
            setores = Setor.objects.filter(pk=setor.id)

        caixas = Tramite.get_caixas(setores=setores)
        cx_entrada = caixas['entrada'].order_by('data_encaminhamento')
        cx_entrada_nao_recebidos = cx_entrada.filter(data_recebimento__isnull=True).order_by('data_encaminhamento')
        cx_entrada_recebidos = cx_entrada.filter(data_recebimento__isnull=False).order_by('data_encaminhamento')
        cx_saida = caixas['saida'].order_by('data_encaminhamento')
        setores_visiveis = get_todos_setores(request.user)
    return locals()


@rtr('protocolo/templates/caixa_tramitacao_externa.html')
@permission_required('protocolo.pode_tramitar_processo')
def caixa_tramitacao_externa(request):
    tramitacao_externa_list = Tramite.get_caixa_tramitacao_externa()
    return locals()


@rtr()
@permission_required('protocolo.pode_tramitar_processo')
def processo_receber(request, tramite_id):
    tramite = get_object_or_404(Tramite, id=tramite_id)
    title = 'Receber Processo %s' % str(tramite.processo)

    if tramite.data_recebimento:
        return httprr(tramite.processo.get_absolute_url(), 'A operação não pode ser realizada porque o processo já foi recebido.')

    if request.method == "POST":
        form = TramiteFormReceber(request.POST, instance=tramite, request=request)
        if form.is_valid():
            form.save()
            if 'receber_e_encaminhar' in request.POST:
                return httprr('/protocolo/processo_encaminhar/%d/interno/' % tramite.id, 'Processo recebido com sucesso. Agora você já pode encaminhá-lo.')
            elif 'receber_e_finalizar' in request.POST:
                return httprr('/protocolo/processo_finalizar/%d/' % tramite.processo.id, 'Processo recebido com sucesso. Agora você já pode finalizá-lo.')
            else:
                return httprr(tramite.processo.get_absolute_url(), 'Processo recebido com sucesso.')
    else:
        form = TramiteFormReceber(instance=tramite, request=request)

    return locals()


@rtr()
@permission_required('protocolo.pode_tramitar_processo')
def processo_encaminhar_primeiro_tramite(request, processo_id, tipo_encaminhamento_descricao):
    processo = get_object_or_404(Processo, id=processo_id)
    title = 'Encaminhar Processo %s (primeiro trâmite)' % str(processo)

    if Tramite.objects.filter(processo=processo, ordem=1):
        return httprr(processo.get_absolute_url(), 'A operação não pode ser realizada porque o processo já teve o seu primeiro trâmite realizado.')

    if processo.tem_vinculo_com_processo_eletronico:
        return httprr(processo.get_absolute_url(), 'A operação não pode ser realizada porque o processo possui vínculo com processo ' 'eletrônico.')

    tramite_novo = Tramite()
    tramite_novo.processo = processo
    tramite_novo.ordem = 1
    if tipo_encaminhamento_descricao == 'interno':
        tramite_novo.tipo_encaminhamento = Tramite.TIPO_ENCAMINHAMENTO_INTERNO
        tramite_novo.orgao_interno_encaminhamento = get_setor()
    elif tipo_encaminhamento_descricao == 'externo':
        tramite_novo.tipo_encaminhamento = Tramite.TIPO_ENCAMINHAMENTO_EXTERNO
        tramite_novo.orgao_interno_encaminhamento = get_setor()

    if request.method == "POST":
        form = TramiteFormEncaminharFactory(tramite=tramite_novo, request_method=request.POST, request=request)
        if form.is_valid():
            form.save()
            return httprr(processo.get_absolute_url(), 'Processo encaminhado com sucesso.')
    else:
        form = TramiteFormEncaminharFactory(tramite=tramite_novo, request_method=None, request=request)
    return locals()


@rtr()
@permission_required('protocolo.pode_tramitar_processo')
def processo_encaminhar(request, tramite_id, tipo_encaminhamento_descricao):
    # Último trâmite realizado por completo.
    tramite = get_object_or_404(Tramite, id=tramite_id)
    title = 'Encaminhar Processo %s' % str(tramite.processo)
    nova_ordem = tramite.ordem + 1

    if Tramite.objects.filter(processo=tramite.processo, ordem=nova_ordem):
        return httprr(tramite.processo.get_absolute_url(), 'A operação não pode ser realizada porque o processo já foi encaminhado.')

    if tramite.processo.tem_vinculo_com_processo_eletronico:
        return httprr(tramite.processo.get_absolute_url(), 'A operação não pode ser realizada porque o processo possui vínculo com processo ' 'eletrônico.')

    # Novo trâmite que se inicia, com base nos dados do último tramite
    # realizado por completo.
    tramite_novo = Tramite()
    tramite_novo.processo = tramite.processo
    tramite_novo.ordem = nova_ordem

    if tipo_encaminhamento_descricao == 'interno':
        tramite_novo.tipo_encaminhamento = Tramite.TIPO_ENCAMINHAMENTO_INTERNO
    elif tipo_encaminhamento_descricao == 'externo':
        tramite_novo.tipo_encaminhamento = Tramite.TIPO_ENCAMINHAMENTO_EXTERNO
    tramite_novo.orgao_interno_encaminhamento = tramite.orgao_interno_recebimento
    form = TramiteFormEncaminharFactory(tramite=tramite_novo, request_method=request.POST or None, request=request)
    if form.is_valid():
        form.save()
        return httprr(tramite.processo.get_absolute_url(), 'Processo encaminhado com sucesso.')

    return locals()


@rtr()
@permission_required('protocolo.pode_tramitar_processo')
def processo_editar_encaminhamento(request, tramite_id):
    tramite = get_object_or_404(Tramite, id=tramite_id)
    title = 'Editar Encaminhamento do Processo %s' % str(tramite.processo)

    if tramite.data_recebimento:
        return httprr(tramite.processo.get_absolute_url(), 'A operação não pode ser realizada porque o ' 'processo já foi recebido.')

    if tramite.processo.tem_vinculo_com_processo_eletronico:
        return httprr(tramite.processo.get_absolute_url(), 'A operação não pode ser realizada porque o processo possui vínculo com ' 'processo eletrônico.')

    if request.method == "POST":
        form = TramiteFormEncaminharFactory(tramite=tramite, request_method=request.POST, request=request)
        if form.is_valid():
            form.save()
            return httprr(tramite.processo.get_absolute_url(), 'Processo encaminhado com sucesso.')
    else:
        form = TramiteFormEncaminharFactory(tramite=tramite, request_method=None, request=request)

    return locals()


@rtr()
@permission_required('protocolo.pode_tramitar_processo')
def processo_informar_recebimento_externo(request, tramite_id):
    tramite = get_object_or_404(Tramite, id=tramite_id)
    title = 'Informar Recebimento de Processo {} no Órgão Externo {}'.format(tramite.processo, tramite.orgao_vinculo_externo_recebimento)

    if request.method == "POST":
        form = TramiteFormInformarRecebimentoExterno(data=request.POST, instance=tramite)
        if form.is_valid():
            form.save()
            return httprr(tramite.processo.get_absolute_url(), 'Processo encaminhado com sucesso')
    else:
        form = TramiteFormInformarRecebimentoExterno(instance=tramite)

    return locals()


@rtr()
@permission_required('protocolo.pode_tramitar_processo')
def processo_retornar_para_ambito_interno(request, tramite_id):
    tramite = get_object_or_404(Tramite, id=tramite_id)

    title = 'Retornar Processo %s para Âmbito Interno' % str(tramite.processo)
    nova_ordem = tramite.ordem + 1

    if Tramite.objects.filter(processo=tramite.processo, ordem=nova_ordem):
        return httprr(tramite.processo.get_absolute_url(), 'A operação não pode ser realizada porque o processo já foi encaminhado.')

    # Novo trâmite que se inicia, com base nos dados do último tramite realizado.
    tramite_novo = Tramite()
    tramite_novo.processo = tramite.processo
    tramite_novo.ordem = nova_ordem
    tramite_novo.tipo_encaminhamento = Tramite.TIPO_ENCAMINHAMENTO_INTERNO

    # fields = ['orgao_vinculo_externo_encaminhamento', 'vinculo_encaminhamento', 'data_encaminhamento', 'observacao_encaminhamento', 'observacao_recebimento']
    tramite_novo.orgao_vinculo_externo_encaminhamento = tramite.orgao_vinculo_externo_encaminhamento
    if tramite.vinculo_recebimento:
        tramite_novo.vinculo_encaminhamento = tramite.vinculo_recebimento
    else:
        tramite_novo.vinculo_encaminhamento = tramite.orgao_interno_recebimento
    tramite_novo.data_encaminhamento = datetime.today()

    if request.method == "POST":
        form = TramiteFormRetornarProcessoParaAmbitoInterno(data=request.POST, instance=tramite_novo, request=request)
        if form.is_valid():
            form.save()
            return httprr(tramite.processo.get_absolute_url(), 'O retorno do processo foi cadastrado com sucesso.')
    else:
        form = TramiteFormRetornarProcessoParaAmbitoInterno(instance=tramite_novo, request=request)

    return locals()


@permission_required('protocolo.pode_tramitar_processo')
def processo_remover_encaminhamento(request, tramite_id):
    tramite = get_object_or_404(Tramite, id=tramite_id)
    if tramite.data_recebimento:
        return httprr(tramite.processo.get_absolute_url(), 'A operação não pode ser realizada porque o processo já foi recebido.')
    tramite.delete()
    return httprr(tramite.processo.get_absolute_url(), 'Encaminhamento removido com sucesso.')


@rtr()
@permission_required('protocolo.pode_tramitar_processo')
def processo_finalizar(request, processo_id):
    processo = get_object_or_404(Processo, id=processo_id)
    title = 'Finalizar Processo %s' % str(processo)
    if processo.status != Processo.STATUS_EM_TRAMITE:
        return httprr(processo.get_absolute_url(), 'O processo não pode ser finalizado porque não está mais "em trâmite".')

    if request.method == "POST":
        form = ProcessoFormFinalizar(request.POST, instance=processo, request=request)
        if form.is_valid():
            form.save()
            return httprr(processo.get_absolute_url(), 'Processo finalizado com sucesso.')
    else:
        form = ProcessoFormFinalizar(instance=processo, request=request)

    return locals()


@permission_required('protocolo.pode_tramitar_processo')
def processo_remover_finalizacao(request, processo_id):
    processo = get_object_or_404(Processo, id=processo_id)

    if processo.status != Processo.STATUS_FINALIZADO:
        return httprr(processo.get_absolute_url(), 'A operação não pode ser realizada porque o processo não está finalizado.')

    processo.remover_finalizacao()
    return httprr(processo.get_absolute_url(), 'Finalização removida com sucesso.')


@rtr()
@permission_required('protocolo.pode_imprimir_comprovante')
def processo_imprimir_comprovante(request, processo_id, maquina_id):
    processo = get_object_or_404(Processo, id=processo_id)
    if 'ponto' in settings.INSTALLED_APPS:
        Maquina = apps.get_model('ponto', 'Maquina')
    maquina = get_object_or_404(Maquina, id=maquina_id)
    # cliente = xmlrpclib.ServerProxy("http://%s:%s" % (maquina.ip, maquina.porta_servico))

    linhas = []
    linhas.append(Configuracao.get_valor_por_chave('comum', 'instituicao_sigla') + ' - ' + Configuracao.get_valor_por_chave('comum', 'instituicao'))
    linhas.append('                        .')
    linhas.append('PROCESSO: {}'.format(processo.numero_processo))
    linhas.append('                        .')
    linhas.append('ASSUNTO: {}'.format(processo.assunto))
    linhas.append('ORIGEM: {}'.format(str(str(processo.setor_origem))))
    if processo.get_ultimo_tramite():
        linhas.append('DESTINO: {}'.format(str(str(processo.get_ultimo_tramite().orgao_interno_recebimento))))
    linhas.append('DATA DE CADASTRO: {}'.format(processo.data_cadastro.strftime("%d/%m/%Y %H:%M")))
    linhas.append('INTERESSADO: {}'.format(processo.interessado_nome))
    linhas.append('CPF/CNPJ: {}'.format(processo.interessado_documento))
    linhas.append('                        .')
    linhas.append('                        .')
    linhas.append('Para acompanhar este processo, acesse ')
    linhas.append('{}'.format(Configuracao.get_valor_por_chave('protocolo', 'url_consulta_publica')))
    linhas.append(maquina.texto_final_impressao or '')
    texto = '\n'.join(linhas)
    enviar_para_impressao(maquina.ip, 9999, to_ascii(texto))

    return httprr(processo.get_absolute_url(), 'Impressão realizada.')


@permission_required('protocolo.pode_gerar_capa')
def processo_imprimir_etiqueta(request, processo_id):
    processo = get_object_or_404(Processo, id=processo_id)
    return imprimir_etiqueta(processo)


# utilizado pelo webservice no site SuapExterno (https://suap.ifrn.edu.br/)
# Essa função será depreciada já que o SUAP deixará de funcionar somente na intranet
def processo_consulta_publica(numero_processo, documento):
    processos = Processo.objects.filter(interessado_documento=documento, numero_processo=numero_processo)

    if processos:
        processo = processos[0]
        processo.get_orgao_responsavel_atual()
        ultima_ordem = len(processo.tramite_set.all()) + 1
        conteudo_html = str(render_to_string('protocolo/templates/processo_detalhe_externo.html', {'processo': processo, 'ultima_ordem': ultima_ordem}))
        return dict(ok=True, conteudo_html=conteudo_html)
    else:
        return dict(ok=False, msg='Processo não encontrado.')


@rtr()
def consulta_publica(request):
    title = 'Consulta de Processos Físicos'
    category = 'Consultas'
    icon = 'file-alt'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    form = ProtocoloForm(request.POST or None)
    if form.is_valid():
        # quando o método "processo_consulta_publica" for depreciado (webservice deixar de existir),
        # seu conteúdo será transferido para esse local
        try:
            conteudo = processo_consulta_publica(form.cleaned_data["numero_processo"], form.cleaned_data["documento"])['conteudo_html']
            return render('protocolo/templates/processo_detalhe.html', locals())

        except KeyError:
            return httprr('.', 'Processo não encontrado.', 'error')

    return locals()


@rtr()
def visualizar_processo_consulta_publica(request, processo_id):
    title = 'Processo Físico'
    servicos_anonimos = layout.gerar_servicos_anonimos(request)
    processo = Processo.objects.get(id=processo_id)
    return locals()
