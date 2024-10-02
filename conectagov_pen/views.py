# -*- coding: utf-8 -*-
from django.contrib import messages

from comum.models import Configuracao
from djtools.services import consulta_quitacao_eleitoral_cidadao
from djtools.utils import JsonResponse, get_client_ip
from djtools.views import httprr, rtr
from django.contrib.auth.decorators import login_required

from suap import settings
from .connect_pen import API_PEN_Exception
from .forms import HipoteseLegalPadraoPENForm, APIExternaForm
from .processa_pendencias import processo_pen
from .api_pen_services import barramento_disponivel, get_tramite, get_recibo_envio, enviar_processo, \
    enviar_componente_digital, get_estrutura_por_id, cancelar_tramite, get_hipoteses
from conectagov_pen.models import TramiteBarramento, DocumentoProcessoBarramento, HipoteseLegalPEN
from conectagov_pen.utils import processo_possui_tipos_de_documentos_nao_mapeados_no_envio, strdecode
from processo_eletronico.models import Processo, Tramite, DocumentoDigitalizado, DocumentoTexto
from django.shortcuts import get_object_or_404
from comum.utils import get_uo
from django.db import transaction
import time
import json


@rtr()
@login_required()
@transaction.atomic()
def envia_processo(request, processo_id, id_repositorio, id_estrutura):
    """
     Rotina que envia um processo pelo barramento, em caso de falha o processo irá para a lista de pendentes de envio
    :param request:
    :param processo_id:
    :param id_repositorio:
    :param id_estrutura:
    :return:
    """
    if barramento_disponivel():
        msg = None
        tipo_msg = "warning"
        processo = get_object_or_404(Processo, pk=processo_id)
        serializador_processo = processo_pen(processo)
        if not get_uo(request.user).id_estrutura_pen:
            msg = "Unidade {} não está configurada para enviar processos pelo barramento.".format(get_uo(request.user).sigla)
        elif not processo.esta_ativo():
            msg = "Processo {} não está na situação 'Em trâmite'.".format(processo.numero_protocolo_fisico)
        elif processo.eh_privado():
            msg = "Processo {} é privado e não pode ser encaminhado via barramento.".format(processo.numero_protocolo_fisico)
        elif processo.tem_documento_sigiloso():
            msg = "Processo {} possui documento(s) sigiloso(s) e não pode ser encaminhado via barramento.".format(processo.numero_protocolo_fisico)
        elif not processo.interessados.all().exists():
            msg = "Processo {} não possui interessados cadastrados.".format(processo.numero_protocolo_fisico)
        elif not processo.get_todos_documentos_processo():
            msg = "Processo {} não possui documentos.".format(processo.numero_protocolo_fisico)
        elif processo_possui_tipos_de_documentos_nao_mapeados_no_envio(processo.get_todos_documentos_processo()):
            msg = "Processo {} possui tipos de documentos não mapeados para o barramento do PEN.".format(processo.numero_protocolo_fisico)
        elif not serializador_processo:
            msg = "Processo {} não possui novos documentos para enviar pelo barramento.".format(processo.numero_protocolo_fisico)
        else:
            processo_ = serializador_processo[0]  # metadados_para_barramento
            documentos_com_conteudo = serializador_processo[1]
            processo_barramento = serializador_processo[2]
            tramite_barramento = serializador_processo[3]
            processo_['cabecalho']['destinatario']['identificacaoDoRepositorioDeEstruturas'] = id_repositorio
            processo_['cabecalho']['destinatario']['numeroDeIdentificacaoDaEstrutura'] = id_estrutura
            envia_metadados = enviar_processo(processo_)

        if not msg:
            if envia_metadados['status_code'] == 200:
                metadados = json.loads(envia_metadados['content'])
                idt = metadados['IDT']
                nre = metadados['NRE']
                tramite = get_tramite(idt)
                tramite_barramento.metadados_processo = metadados
                tramite_barramento.id_tramite_barramento = idt
                tramite_barramento.save()
                hashDosComponentesPendentesDeEnvio = tramite['hashDosComponentesPendentesDeEnvio']
                msg_docs = ""
                for doc in documentos_com_conteudo:
                    conteudo_arquivo = doc['conteudo']
                    hash_documento = doc['documento']['hash_documento']
                    objeto_documento = None
                    if 'id_documento' in doc['documento']:
                        if doc['documento']['tipo_parte_processo'] == 'DOCUMENTO_TEXTO':
                            objeto_documento = DocumentoTexto.objects.get(id=doc['documento']['id_documento'])
                        elif doc['documento']['tipo_parte_processo'] == 'DOCUMENTO_DIGITALIZADO':
                            objeto_documento = DocumentoDigitalizado.objects.get(id=doc['documento']['id_documento'])

                    if strdecode(hash_documento) in hashDosComponentesPendentesDeEnvio:
                        componente = {"conteudo": conteudo_arquivo, "hashDoComponenteDigital": hash_documento}
                        envia_comp = enviar_componente_digital(metadados['ticketParaEnvioDeComponentesDigitais'], tramite['protocolo'], componente)
                        t = 0
                        while envia_comp['status_code'] != 200:
                            t += 1
                            time.sleep(5)

                            """
                            Após 3 tentativas sem sucesso de enviar o componente digital o TramiteBarramento é cancelado
                            """
                            if t == 3:
                                cancelar_tramite(int(tramite['IDT']))
                                tramite_barramento.status = tramite_barramento.STATUS_CANCELADO
                                retorno = json.loads(envia_comp['content'])
                                tramite_barramento.retorno_situacao = retorno['mensagem']
                                tramite_barramento.save()
                                return httprr(processo.get_absolute_url(), retorno['mensagem'])

                        if envia_comp['status_code'] == 200:
                            DocumentoProcessoBarramento.objects.filter(
                                processo_barramento=processo_barramento.id, ordem=doc['documento']['ordem'], enviado=False, recebido=False
                            ).update(enviado=True)
                            if objeto_documento:
                                msg_docs += objeto_documento.assunto
                            else:
                                msg_docs += "Capa/Despacho/Parecer"
                    else:
                        msg = "Conflito na checagem de hash do documento {} - id: {}".format(objeto_documento.assunto, objeto_documento.id)
                recibo_envio = get_recibo_envio(idt)
                t = 0
                while recibo_envio['status_code'] != 200:
                    t += 1
                    time.sleep(5)
                    if t == 3:
                        cancelar_tramite(int(tramite['IDT']))
                        tramite_barramento.status = tramite_barramento.STATUS_CANCELADO
                        retorno = json.loads(recibo_envio['content'])
                        tramite_barramento.retorno_situacao = retorno['mensagem']
                        tramite_barramento.save()
                        return httprr(processo.get_absolute_url(), recibo_envio['content']['mensagem'])
                if recibo_envio['status_code'] == 200:
                    dados_tramite_barramento = {
                        'processo_barramento': processo_barramento,
                        'idt': idt,
                        'recibo_envio': recibo_envio,
                        'remetente_repositorio_id': processo_['cabecalho']['remetente']['identificacaoDoRepositorioDeEstruturas'],
                        'remetente_estrutura_id': processo_['cabecalho']['remetente']['numeroDeIdentificacaoDaEstrutura'],
                        'destinatario_repositorio_id': processo_['cabecalho']['destinatario']['identificacaoDoRepositorioDeEstruturas'],
                        'destinatario_estrutura_id': processo_['cabecalho']['destinatario']['numeroDeIdentificacaoDaEstrutura'],
                    }
                    dados_tramite = {
                        'processo': processo_barramento.processo,
                        'tramite_barramento': atualiza_tramite_barramento(tramite_barramento, dados_tramite_barramento),
                        'remetente_setor': processo_barramento.processo.get_setor_atual(),
                        'remetente_pessoa': request.user.pessoafisica,
                    }
                    tramite = criar_tramite_envio(dados_tramite)
                    if tramite:
                        if not processo_barramento.nre_barramento_pen:
                            processo_barramento.nre_barramento_pen = nre
                            processo_barramento.save()
                        processo.colocar_em_tramite_externo()
                        processo.save()
                        msg = 'Processo tramitado externamente com sucesso por {}. Documentos enviados:'.format(tramite.remetente_pessoa.nome) + msg_docs
                        tipo_msg = "success"
            else:
                msg = 'O SUAP não está conseguindo enviar este processo, por gentileza, tente novamente mais tarde {}.'.format(envia_metadados)
                tipo_msg = "error"
        else:
            tipo_msg = "error"
            return httprr(processo.get_absolute_url(), msg, tag=tipo_msg)
    else:
        msg = 'Barramento ConectaGOV indisponível no momento, por gentileza, tente novamente mais tarde.'
        raise API_PEN_Exception(msg)
    return httprr(processo.get_absolute_url(), msg, tag=tipo_msg)


def atualiza_tramite_barramento(tramite_barramento, dados_tramite_barramento):
    tramite_barramento.processo_barramento = dados_tramite_barramento['processo_barramento']
    # dados_tramite_externo
    tramite_barramento.id_tramite_barramento = dados_tramite_barramento['idt']
    tramite_barramento.remetente_externo_repositorio_id = dados_tramite_barramento['remetente_repositorio_id']
    tramite_barramento.remetente_externo_estrutura_id = dados_tramite_barramento['remetente_estrutura_id']
    tramite_barramento.remetente_externo_estrutura_descricao = get_estrutura_por_id(
        dados_tramite_barramento['remetente_repositorio_id'], dados_tramite_barramento['remetente_estrutura_id']
    )['nome']
    tramite_barramento.destinatario_externo_repositorio_id = dados_tramite_barramento['destinatario_repositorio_id']
    tramite_barramento.destinatario_externo_estrutura_id = dados_tramite_barramento['destinatario_estrutura_id']
    tramite_barramento.destinatario_externo_estrutura_descricao = get_estrutura_por_id(
        dados_tramite_barramento['destinatario_repositorio_id'], dados_tramite_barramento['destinatario_estrutura_id']
    )['nome']
    # recibos_json
    tramite_barramento.tramite_externo_recibo_envio_json = dados_tramite_barramento['recibo_envio']['data']
    tramite_barramento.status = TramiteBarramento.STATUS_ENVIADO
    tramite_barramento.save()
    return tramite_barramento


def criar_tramite_envio(dados_tramite):
    tramite_novo = Tramite()
    tramite_novo.processo = dados_tramite['processo']
    tramite_novo.tramite_barramento = dados_tramite['tramite_barramento']
    tramite_novo.remetente_setor = dados_tramite['remetente_setor']
    tramite_novo.remetente_pessoa = dados_tramite['remetente_pessoa']
    tramite_novo.save()
    return tramite_novo


@login_required
def consulta_estrutura(request, repositorio_id):
    from conectagov_pen.api_pen_services import get_estrutura
    from conectagov_pen.utils import monta_retorno_autocomplete

    nome_busca = request.GET.get("q")
    retorno = monta_retorno_autocomplete(get_estrutura(int(repositorio_id), nome_busca))
    return JsonResponse(retorno)


@login_required
def processar_pendencias(request):
    from conectagov_pen.processa_pendencias import processar_pendencias

    if processar_pendencias():
        return httprr('/admin/conectagov_pen/tramitebarramento/', "Trâmites Externos Atualizados Com Sucesso")
    else:
        return httprr('/admin/conectagov_pen/tramitebarramento/', "Não Existem Trâmites Externos Pendentes", 'alert')


@login_required
def importar_hipoteses_legais_pen(request):
    try:
        hipoteses_pen = get_hipoteses()
        for hipotese_pen in hipoteses_pen:
            if not HipoteseLegalPEN.objects.filter(id_hipotese_legal_pen__exact=hipotese_pen.get("identificacao")).exists():
                HipoteseLegalPEN.objects.update_or_create(
                    id_hipotese_legal_pen=hipotese_pen.get("identificacao"),
                    nome=hipotese_pen.get("nome"),
                    descricao=hipotese_pen.get("descricao"),
                    base_legal=hipotese_pen.get("baseLegal"),
                    status=hipotese_pen.get("status")
                )
        return httprr('/admin/conectagov_pen/hipoteselegalpen/', 'Hipóteses Legais do PEN importadas com sucesso.', 'success')
    except Exception as e:
        msg = 'Erro ao importar Hipóteses Legais do PEN.'
        if settings.DEBUG:
            msg = f'{msg} - Detalhes: {str(e)}'
        return httprr('/admin/conectagov_pen/hipoteselegalpen/', msg, 'error')


@rtr()
def definir_hipotese_padrao_pen(request):
    title = 'Hipótese Legal Padrão para Trâmites via Barramento do PEN'
    hipoteses_padrao_exists = HipoteseLegalPEN.objects.filter(hipotese_padrao=True).exists()
    form = HipoteseLegalPadraoPENForm(request.POST or None)
    if form.is_valid():
        hipotese = form.cleaned_data['hipotese']
        try:
            if hipoteses_padrao_exists:
                HipoteseLegalPEN.objects.filter(hipotese_padrao=True).update(hipotese_padrao=False)
            HipoteseLegalPEN.objects.filter(pk=hipotese.id).update(hipotese_padrao=True)
            messages.add_message(request, messages.SUCCESS, f"Hipótese Padrão do PEN alterada para: {hipotese.nome}")
        except Exception:
            messages.add_message(request, messages.ERROR, "Erro ao alterar Hipótese Padrão do PEN")
    hipotese_padrao = HipoteseLegalPEN.objects.filter(
        hipotese_padrao=True).first().nome if hipoteses_padrao_exists else "Nenhuma"

    return locals()


@rtr()
@login_required()
def teste_conexao_apis_externas(request):
    if not request.user.is_superuser:
        return httprr('..', 'Você não tem permissão para acessar esta funcionalidade.', 'error')

    title = 'Teste de Conexão com APIs Externas'

    form = APIExternaForm(request.POST or None)
    if form.is_valid():
        api = form.cleaned_data.get('api')
        payload = form.cleaned_data.get('payload')
        if payload:
            payload = json.loads(payload)
        try:
            if api == "quitacaoeleitoral_consulta_situacao":
                CPF_OPERADOR_API = Configuracao.get_valor_por_chave('djtools', 'cpf_operador_api_cep_gov_br')
                sucesso, response = consulta_quitacao_eleitoral_cidadao(payload, get_client_ip(request), CPF_OPERADOR_API, return_full=True)
                response_headers = response.headers
                response_content = response.json()
                status_code = response.status_code

            if api == "quitacaoeleitoral_emissao_doc":
                CPF_OPERADOR_API = Configuracao.get_valor_por_chave('djtools', 'cpf_operador_api_cep_gov_br')
                sucesso, response = consulta_quitacao_eleitoral_cidadao(payload, get_client_ip(request), True, CPF_OPERADOR_API, return_full=True)
                response_headers = response.headers
                response_content = response.json()
                status_code = response.status_code

        except Exception:
            messages.add_message(request, messages.ERROR, "Erro ao testar conexão com a API")

    return locals()
