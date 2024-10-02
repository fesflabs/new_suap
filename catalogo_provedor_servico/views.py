import datetime
import json
import logging
from functools import reduce
from operator import or_

from django.conf import settings
from django.contrib import messages
from django.contrib.admin.models import LogEntry, DELETION, ADDITION
from django.contrib.auth.decorators import permission_required, login_required
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.db import models
from django.db.models import Count, F
from django.db.models.functions import Cast
from django.http import JsonResponse, HttpResponse, Http404, HttpResponseRedirect
from django.shortcuts import redirect, get_object_or_404
from django.template.defaultfilters import pluralize, filesizeformat
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.html import strip_tags
from django.utils.safestring import mark_safe
from django.views.decorators.csrf import csrf_exempt
from rest_framework.decorators import api_view, permission_classes
from sentry_sdk import capture_exception

from api.permissions import TokenFromTrustedApp
from catalogo_provedor_servico.forms import IndeferirSolicitacaoForm, DashboradFiltroForm, \
    RetornarParaAnaliseSolicitacaoForm, AtribuirAtendimentoForm, ApagarAtendimentoForm, TestarDisponibilidadeForm, \
    AdicionarUsuarioEquipeFormFactory
from catalogo_provedor_servico.models import RegistroAcompanhamentoGovBR, Servico, ServicoEquipe, \
    RegistroNotificacaoGovBR
from catalogo_provedor_servico.providers.factory import get_service_provider_factory
from catalogo_provedor_servico.serializers import ServicoSerializer, AvaliacaoDisponibilidadeServicoSerializer, \
    RegistroAcompanhamentoGovBRSerializer
from catalogo_provedor_servico.services import registrar_acompanhamento_servico, registrar_conclusao_servico, \
    registrar_reabertura_servico, notificar_cidadao_via_notifica_govbr
from comum.models import Vinculo
from comum.utils import get_uo
from djtools import layout
from djtools.html.graficos import LineChart, PieChart
from djtools.utils import httprr, rtr, get_session_cache
from catalogo_provedor_servico.utils import Notificar
from rh.models import UnidadeOrganizacional
from .models import ServicoGerenteEquipeLocal, Solicitacao, SolicitacaoEtapa, SolicitacaoEtapaArquivo
from .providers.base import Resposta
from .utils import get_cpf_formatado, obter_choices_por_funcao

logger = logging.getLogger(__name__)

# NÃO APAGAR
# Carrega os arquivos do pacote impl de cada instituição definidas pela variavel do settings SERVICE_PROVIDER_FACTORY
# durante a inicialização do django
get_service_provider_factory()


@layout.quadro('Solicitações do Catálogo Digital', icone='check-circle', pode_esconder=True)
def index_quadros(quadro, request):
    def do():
        vinculo = request.user.get_vinculo()
        eh_sistemico = request.user.has_perm('catalogo_provedor_servico.eh_gerente_sistemico_catalogo')
        queryset = Solicitacao.objects.all()

        if not eh_sistemico:
            queryset = Solicitacao.objects.filter(servico__servicoequipe__vinculo_id=vinculo.pk, uo=F('servico__servicoequipe__campus'))

        url_base = '/admin/catalogo_provedor_servico/solicitacao/'
        em_analise = queryset.filter(status=Solicitacao.STATUS_EM_ANALISE)
        if em_analise.exists():
            url_em_analise = f'{url_base}?status__exact={Solicitacao.STATUS_EM_ANALISE}'
            if eh_sistemico:
                qtd_em_analise = em_analise.count()
                quadro.add_item(
                    layout.ItemContador(
                        titulo='Solicitaç{} do Catálogo'.format(pluralize(qtd_em_analise, 'ão,ões')),
                        subtitulo='Em análise',
                        qtd=qtd_em_analise,
                        url=url_em_analise,
                    )
                )
            else:
                qtd_atribuidos_para_mim = em_analise.filter(vinculo_responsavel=vinculo).count()
                qtd_nao_atribuidos = em_analise.filter(vinculo_responsavel__isnull=True).count()
                url_em_analise_por_mim = f'{url_em_analise}&vinculo_responsavel={vinculo.pk}'
                url_em_analise_por_ninguem = f'{url_em_analise}&vinculo_responsavel=nenhum'
                if qtd_atribuidos_para_mim:
                    quadro.add_item(
                        layout.ItemContador(
                            titulo='Solicitaç{} do Catálogo'.format(pluralize(qtd_atribuidos_para_mim, 'ão,ões')),
                            subtitulo='Em análise por mim',
                            qtd=qtd_atribuidos_para_mim,
                            url=url_em_analise_por_mim,
                        )
                    )
                if qtd_nao_atribuidos:
                    quadro.add_item(
                        layout.ItemContador(
                            titulo='Solicitaç{} do Catálogo'.format(pluralize(qtd_nao_atribuidos, 'ão,ões')),
                            subtitulo='Em análise não atríbuidos',
                            qtd=qtd_nao_atribuidos,
                            url=url_em_analise_por_ninguem,
                        )
                    )

        dados_aguardando_correcao = queryset.filter(status=Solicitacao.STATUS_AGUARDANDO_CORRECAO_DE_DADOS)
        url_dados_aguardando_correcao = f'{url_base}?status__exact={Solicitacao.STATUS_AGUARDANDO_CORRECAO_DE_DADOS}'
        if not eh_sistemico:
            dados_aguardando_correcao = dados_aguardando_correcao.filter(vinculo_responsavel=vinculo.pk)
            url_dados_aguardando_correcao = f'{url_dados_aguardando_correcao}&vinculo_responsavel={vinculo.pk}'
        qtd_dados_aguardando_correcao = dados_aguardando_correcao.count()
        if qtd_dados_aguardando_correcao:
            plural = pluralize(qtd_dados_aguardando_correcao)
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Solicitaç{pluralize(qtd_dados_aguardando_correcao, "ão,ões")} do Catálogo',
                    subtitulo=f'Aguardando Correç{pluralize(qtd_dados_aguardando_correcao, "ão,ões")} de Dado{plural}',
                    qtd=qtd_dados_aguardando_correcao,
                    url=url_dados_aguardando_correcao,
                )
            )

        dados_corrigidos = queryset.filter(status=Solicitacao.STATUS_DADOS_CORRIGIDOS)
        url_dados_corrigidos = f'{url_base}?status__exact={Solicitacao.STATUS_DADOS_CORRIGIDOS}'
        if not eh_sistemico:
            dados_corrigidos = dados_corrigidos.filter(vinculo_responsavel=vinculo.pk)
            url_dados_corrigidos = f'{url_dados_corrigidos}&vinculo_responsavel={vinculo.pk}'
        qtd_dados_corrigidos = dados_corrigidos.count()
        if qtd_dados_corrigidos:
            plural = pluralize(qtd_dados_corrigidos)
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Solicitaç{pluralize(qtd_dados_corrigidos, "ão,ões")} do Catálogo',
                    subtitulo=f'Com o{plural} Dado{plural} Corrigido{plural}',
                    qtd=qtd_dados_corrigidos,
                    url=url_dados_corrigidos,
                )
            )

        prontas_para_execucao = queryset.filter(status=Solicitacao.STATUS_PRONTO_PARA_EXECUCAO)
        url_pronta_para_execucao = f'{url_base}?status__exact={Solicitacao.STATUS_PRONTO_PARA_EXECUCAO}'
        if not eh_sistemico:
            prontas_para_execucao = prontas_para_execucao.filter(vinculo_responsavel=vinculo.pk)
            url_pronta_para_execucao = url_pronta_para_execucao + f'&vinculo_responsavel={vinculo.pk}'
        qtd_prontas_para_execucao = prontas_para_execucao.count()
        if qtd_prontas_para_execucao:
            quadro.add_item(
                layout.ItemContador(
                    titulo=f'Solicitaç{pluralize(qtd_prontas_para_execucao, "ão,ões")} do Catálogo',
                    subtitulo=f'Pronta{pluralize(qtd_prontas_para_execucao)} para Execução',
                    qtd=qtd_prontas_para_execucao,
                    url=url_pronta_para_execucao,
                )
            )

        return quadro

    return get_session_cache(request, 'index_catalogo_servico', do, 60)


@api_view(['GET'])
@permission_classes([TokenFromTrustedApp])
def servicos_ativos(request, id_servico_portal_govbr=None):
    try:
        servicos_ativos = get_service_provider_factory().get_servicos_ativos(
            id_servico_portal_govbr=id_servico_portal_govbr)
        if not servicos_ativos:
            return JsonResponse(data=Resposta(mensagem='Nenhum serviço ativo.').json(), safe=False)

        serializer = ServicoSerializer(servicos_ativos, many=True)
        resposta = Resposta(resposta=serializer.data)
        return JsonResponse(resposta.json(), safe=False)
    except Exception as e:
        if settings.DEBUG:
            raise e
        capture_exception(e)
        resposta = Resposta.create_from_exception(mensagem='Erro ao listar os serviços ativos.', exception=e)
        return JsonResponse(data=resposta.json(), safe=False, status=404)


@api_view(['GET'])
@permission_classes([TokenFromTrustedApp])
def servicos_disponiveis(request, cpf):
    try:
        cpf = get_cpf_formatado(cpf)
        servicos = get_service_provider_factory().get_servicos_disponiveis(cpf)
        if not servicos:
            return JsonResponse(data=Resposta(mensagem='Nenhum serviço disponível.').json(), safe=False)

        serializer = ServicoSerializer(servicos, many=True)
        resposta = Resposta(resposta=serializer.data)
        return JsonResponse(resposta.json(), safe=False)
    except Exception as e:
        if settings.DEBUG:
            raise e
        capture_exception(e)
        resposta = Resposta.create_from_exception(mensagem='Erro ao listar os serviços disponíveis.', exception=e)
        return JsonResponse(data=resposta.json(), safe=False, status=404)


@api_view(['GET'])
@permission_classes([TokenFromTrustedApp])
def servicos_avaliacao_disponibilidade(request, cpf):
    try:
        cpf = get_cpf_formatado(cpf)
        avaliacoes_disponibilidade_servicos = get_service_provider_factory().get_avaliacoes_disponibilidade_servicos(
            cpf)
        if not avaliacoes_disponibilidade_servicos:
            return JsonResponse(data=Resposta(
                mensagem='Nenhuma avaliação de disponibilidade de serviço encontra-se disponível.').json(), safe=False)

        serializer = AvaliacaoDisponibilidadeServicoSerializer(avaliacoes_disponibilidade_servicos, many=True)
        resposta = Resposta(resposta=serializer.data)
        return JsonResponse(resposta.json(), safe=False)
    except Exception as e:
        if settings.DEBUG:
            raise e
        capture_exception(e)
        resposta = Resposta.create_from_exception(
            mensagem='Erro ao realizar a avaliação de disponibilidade dos serviços para o cpf {}.'.format(cpf),
            exception=e)
        return JsonResponse(data=resposta.json(), safe=False, status=404)


@api_view(['POST'])
@permission_classes([TokenFromTrustedApp])
def servicos_autocompletar(request):
    try:
        choices_resource_id = request.POST.get('choices_resource_id')
        if choices_resource_id:
            filters = request.POST.get('filters')
            qs = obter_choices_por_funcao(choices_resource_id, filters)
            search_fields = qs.model.SEARCH_FIELDS
            results = []
            page = int(request.POST.get('page', 1))
            term = request.POST.get('term')
            if term:
                words = term.split()
                for word in words:
                    or_queries = [models.Q(**{f'{field_name}__icontains': word}) for field_name in search_fields]
                    qs = qs.filter(reduce(or_, or_queries))

            for obj in qs[20 * page - 20: 20 * page]:
                results.append({'id': obj.pk, 'text': str(obj)})

            results = {'results': results, 'pagination': {'more': (page * 20) < qs.count()}}
            return JsonResponse(results, safe=False)
        else:
            resposta = Resposta.create_from_exception(
                mensagem='Erro ao realizar a avaliação de disponibilidade dos serviços',
                exception=Exception('choices_resouce_id vazio'))
            return JsonResponse(data=resposta.json(), safe=False, status=404)
    except Exception as e:
        if settings.DEBUG:
            raise e
        capture_exception(e)
        resposta = Resposta.create_from_exception(
            mensagem='Erro ao realizar a avaliação de disponibilidade dos serviços', exception=e)
        return JsonResponse(data=resposta.json(), safe=False, status=404)


@csrf_exempt
@api_view(['GET', 'POST'])
@permission_classes([TokenFromTrustedApp])
def receber_solicitacao(request, id_servico_portal_govbr, cpf):
    try:
        # Verifica novamente se este servico está disponivel para o CPF informado.
        cpf = get_cpf_formatado(cpf)

        service_provider = get_service_provider_factory().get_service_provider(
            id_servico_portal_govbr=id_servico_portal_govbr)
        if not service_provider or not service_provider.get_avaliacao_disponibilidade(cpf=cpf).is_ok:
            resposta = Resposta(mensagem='Serviço indisponível para o cpf {}.'.format(cpf))
            return JsonResponse(data=resposta.json(), safe=False)

        # O método receber solicitação já devolve o JSonResponse.
        return service_provider.receber_solicitacao(request=request, cpf=cpf)
    except Exception as e:
        if settings.DEBUG:
            raise e
        capture_exception(e)
        print(e)
        resposta = Resposta.create_from_exception(mensagem='Erro ao receber solicitação.', exception=e)
        return JsonResponse(data=resposta.json(), safe=False, status=404)


@csrf_exempt
@api_view(['GET'])
@permission_classes([TokenFromTrustedApp])
def obter_arquivo(request, cpf, hash_sha512_link_id):
    try:
        cpf = get_cpf_formatado(cpf)

        try:
            solicitacao_etapa_arquivo = SolicitacaoEtapaArquivo.objects.get(hash_sha512_link_id=hash_sha512_link_id,
                                                                            solicitacao_etapa__solicitacao__cpf=cpf)

            resposta = Resposta(resposta={'arquivo': solicitacao_etapa_arquivo.get_arquivo_unico_as_strb64()})
            return JsonResponse(data=resposta.json(), safe=False)
        except SolicitacaoEtapaArquivo.DoesNotExist:
            resposta = Resposta(mensagem='O arquivo solicitado não existe para o cpf {}.'.format(cpf))
            return JsonResponse(data=resposta.json(), safe=False)

    except Exception as e:
        capture_exception(e)
        resposta = Resposta.create_from_exception(mensagem='Erro ao tentar obter o arquivo.', exception=e)
        return JsonResponse(data=resposta.json(), safe=False, status=404)


@login_required()
def enviar_registros_pendentes_govbr(request):
    try:
        registros_nao_enviados = RegistroAcompanhamentoGovBR.objects.filter(
            status__in=[RegistroAcompanhamentoGovBR.PENDENTE, RegistroAcompanhamentoGovBR.ERRO])

        for registro_acompanhamento in registros_nao_enviados:
            if registro_acompanhamento.tipo == RegistroAcompanhamentoGovBR.TIPO_ACOMPANHAMENTO:
                registrar_acompanhamento_servico(registro=registro_acompanhamento)
            elif registro_acompanhamento.tipo == RegistroAcompanhamentoGovBR.TIPO_CONCLUSAO:
                registrar_conclusao_servico(registro=registro_acompanhamento)
            elif registro_acompanhamento.tipo == RegistroAcompanhamentoGovBR.TIPO_CONCLUSAO:
                registrar_reabertura_servico(registro=registro_acompanhamento)

        return httprr('/admin/catalogo_provedor_servico/registroacompanhamentogovbr/',
                      "Registros processados com sucesso", tag="success")

    except Exception:
        return httprr('/admin/catalogo_provedor_servico/registroacompanhamentogovbr/', "Erro ao enviar registros",
                      tag="error")


@login_required()
def visualizar_arquivo(request, hash_sha512_link_id):
    try:
        try:
            solicitacao_etapa_arquivo = SolicitacaoEtapaArquivo.objects.get(hash_sha512_link_id=hash_sha512_link_id)
            response = HttpResponse(content=solicitacao_etapa_arquivo.arquivo_unico.get_conteudo_as_bytes(),
                                    content_type=solicitacao_etapa_arquivo.arquivo_unico.tipo_conteudo)
            response['Content-Disposition'] = 'inline; filename={}'.format(solicitacao_etapa_arquivo.nome_original)
            return response
        except SolicitacaoEtapaArquivo.DoesNotExist:
            return Http404('O arquivo solicitado não existe.')
    except Exception as e:
        msg_error = 'Erro ao tentar obter o arquivo.'
        if settings.DEBUG:
            msg_error += ' Detalhes: {}'.format(e)
        capture_exception(e)
        return Http404(msg_error)


@rtr()
@login_required()
@permission_required('catalogo_provedor_servico.pode_avaliar_solicitacoes')
def indeferir_solicitacao(request, id):
    solicitacao = get_object_or_404(Solicitacao.objects, id=id)
    title = f'Indeferir Solicitação {solicitacao}'

    if not solicitacao.has_status_permite_indeferimento():
        return httprr(solicitacao.get_absolute_url(), 'Status inválido.', 'error')

    form = IndeferirSolicitacaoForm(request.POST or None, instance=solicitacao)
    if form.is_valid():
        form.save()
        return httprr(solicitacao.get_absolute_url(), 'Solicitação indeferida com sucesso.')

    return locals()


@rtr()
@login_required()
@permission_required('catalogo_provedor_servico.pode_avaliar_solicitacoes')
def reenviar_notificacao_govbr(request, id):

    registro_notificacao = RegistroNotificacaoGovBR.objects.filter(pk=id).first()

    if registro_notificacao.enviada:
        return httprr(reverse('avaliar_solicitacao', args=(registro_notificacao.solicitacao.id,)), 'Notificação já enviada.', 'warning')

    if registro_notificacao.tipo == RegistroNotificacaoGovBR.SMS:
        notificar_cidadao_via_notifica_govbr(registro_notificacao.solicitacao,
                                             mensagem_sms=registro_notificacao.mensagem,
                                             registro_notificacao=registro_notificacao)
    elif registro_notificacao.tipo == RegistroNotificacaoGovBR.EMAIL:
        notificar_cidadao_via_notifica_govbr(registro_notificacao.solicitacao,
                                             mensagem_email=strip_tags(registro_notificacao.mensagem),
                                             registro_notificacao=registro_notificacao)
    elif registro_notificacao.tipo == RegistroNotificacaoGovBR.APP:
        notificar_cidadao_via_notifica_govbr(registro_notificacao.solicitacao,
                                             mensagem_email=registro_notificacao.mensagem,
                                             registro_notificacao=registro_notificacao)

    if registro_notificacao.enviada:
        return httprr(reverse('avaliar_solicitacao', args=(registro_notificacao.solicitacao.id,)), 'Notificação enviada com sucesso.', 'success')
    else:
        return httprr(reverse('avaliar_solicitacao', args=(registro_notificacao.solicitacao.id,)), 'Erro ao enviar a notificação.', 'error')

    return locals()


@rtr()
@login_required()
@permission_required('catalogo_provedor_servico.pode_avaliar_solicitacoes')
def enviar_notificacao_correcao_dados_govbr(request, id):
    '''
    Envia notificação para solicitar correção de dados
    '''
    solicitacao = Solicitacao.objects.filter(pk=id).first()

    if not solicitacao.status == Solicitacao.STATUS_AGUARDANDO_CORRECAO_DE_DADOS:
        return httprr(reverse('avaliar_solicitacao', args=(solicitacao.id,)),
                      'A notificação não pode ser enviada pois a Solicitação não está  Aguardando Correção de Dados.', 'warning')

    service_provider = get_service_provider_factory().get_service_provider(
        id_servico_portal_govbr=solicitacao.servico.id_servico_portal_govbr)
    dados_email = service_provider.get_dados_email(solicitacao=solicitacao)

    if solicitacao.status == Solicitacao.STATUS_AGUARDANDO_CORRECAO_DE_DADOS:
        service_provider.registrar_acompanhamento(solicitacao)
        Notificar.solicitacao_correcao_de_dados(solicitacao, dados_email)

    registro_notificacao = RegistroNotificacaoGovBR.objects.filter(solicitacao__pk=solicitacao.id).last()

    if registro_notificacao.enviada:
        return httprr(reverse('avaliar_solicitacao', args=(registro_notificacao.solicitacao.id,)), 'Notificação enviada com sucesso.', 'success')
    else:
        return httprr(reverse('avaliar_solicitacao', args=(registro_notificacao.solicitacao.id,)), 'Erro ao enviar a notificação.', 'error')

    return locals()


@rtr()
@login_required()
@permission_required('catalogo_provedor_servico.pode_avaliar_solicitacoes')
def retornar_para_analise_solicitacao(request, id):
    solicitacao = get_object_or_404(Solicitacao.objects, id=id)
    title = f'Retornar para Análise - {solicitacao} '

    if not solicitacao.has_status_permite_retornar_para_analise():
        return httprr(solicitacao.get_absolute_url(), 'Status inválido.', 'error')

    form = RetornarParaAnaliseSolicitacaoForm(request.POST or None, instance=solicitacao)
    if form.is_valid():
        form.save()
        return httprr(solicitacao.get_absolute_url(), 'Solicitação alterada para Análise com sucesso.',
                      close_popup=True)

    return locals()


@rtr()
@login_required()
@permission_required('catalogo_provedor_servico.pode_avaliar_solicitacoes')
def avaliar_solicitacao(request, id):
    title = 'Avaliação de Solicitação'

    # TODO: Revisar e se possível otimizar!
    solicitacao = get_object_or_404(Solicitacao, id=id)

    solicitacao_atendida_por_qualquer_uo = bool(not solicitacao.uo)

    campus_usuario_atende = UnidadeOrganizacional.objects.filter(
        pk__in=solicitacao.servico.servicoequipe_set.filter(
            vinculo=request.user.get_vinculo()).values_list('campus_id', flat=True)
    )
    campus_usuario_gerencia = UnidadeOrganizacional.objects.filter(
        pk__in=solicitacao.servico.servicogerenteequipelocal_set.filter(
            vinculo=request.user.get_vinculo()).values_list('campus_id', flat=True)
    )

    solicitacoes_responsaveis_historico = solicitacao.solicitacaoresponsavelhistorico_set.all().order_by('-id')
    solicitacoes_situacoes_historico = solicitacao.solicitacaohistoricosituacao_set.all().order_by('-id')
    notificacoes_govbr = solicitacao.registronotificacaogovbr_set.all().order_by('-id')
    solicitacoes_etapas = SolicitacaoEtapa.objects.filter(solicitacao=solicitacao)
    service_provider = get_service_provider_factory().get_service_provider(
        id_servico_portal_govbr=solicitacao.servico.id_servico_portal_govbr)

    pf_atende_uo_da_solicitacao = (solicitacao.uo in campus_usuario_atende)
    pf_eh_gerente_avaliacao_da_uo = (solicitacao.uo in campus_usuario_gerencia)
    pf_eh_responsavel_atual_pela_solicitacao = (solicitacao.vinculo_responsavel == request.user.get_vinculo())

    em_periodo_avaliacao = False

    # Uma vez o form submetido, os dados do jsons do formulário e da avaliação serão atualizados e depois persistidos.
    existe_campo_aguardando_avaliacao = False
    existe_campo_com_error = False

    # Montando os dados necessários para a criação dinâmica do formuário de avaliação, com base nos jsons do formulário
    # em si e da avaliação.
    etapas = list()
    candidato_vaga = None

    em_periodo_avaliacao = service_provider.is_em_periodo_avaliacao(solicitacao=solicitacao, campus=solicitacao.uo)
    for se in solicitacoes_etapas:
        dados_as_json = se.get_dados_as_json()
        numero_etapa = se.numero_etapa
        formulario = dados_as_json['formulario'].copy()
        correcoes_necessarias = 0

        for campo in formulario:
            name = campo['name']
            type = campo['type']
            value = campo['value']
            read_only = campo.get('read_only', False)

            if type == 'date' and value:
                campo['value'] = datetime.datetime.strptime(campo['value'], '%Y-%m-%d').strftime('%d/%m/%Y')

            if type == 'choices' and value:
                if campo.get('display_value'):
                    campo['value'] = campo.get('display_value')

            if campo['type'] == 'file':
                value_hash_sha512_link_id = campo['value_hash_sha512_link_id']
                if value_hash_sha512_link_id:
                    link_base = '<a href="/rh/arquivo_unico/{arquivo_hash_sha512_link_id}/?filename={arquivo_nome}" target="_blank">{arquivo_nome} ({arquivo_tamanho})</a>'

                    arquivo_tamanho = filesizeformat(campo['value_size_in_bytes'])
                    arquivo_extensao = '.{}'.format(campo['value_original_name'].split('.')[-1])
                    arquivo_nome = '{}{}'.format(campo['label_to_file'], arquivo_extensao)

                    campo['value_as_link'] = mark_safe(
                        link_base.format(
                            arquivo_hash_sha512_link_id=campo['value_hash_sha512_link_id'],
                            arquivo_nome=arquivo_nome,
                            arquivo_tipo=campo['value_content_type'],
                            arquivo_tamanho=arquivo_tamanho,
                        )
                    )

            # Adicionando em cada campo as informações da avaliação.
            if read_only:
                campo['avaliacao_status'] = 'OK'
                campo['avaliacao_status_msg'] = None
            else:
                status = campo.get('avaliacao_status')
                status_msg = campo.get('avaliacao_status_msg')

                if not status and not existe_campo_aguardando_avaliacao:
                    existe_campo_aguardando_avaliacao = True

                if status and status == 'ERROR' and not existe_campo_com_error:
                    existe_campo_com_error = True

            if campo.get('avaliacao_status') != 'OK':
                correcoes_necessarias += 1

        etapas.append(
            {'numero_etapa': numero_etapa, 'formulario': formulario, 'correcoes_necessarias': correcoes_necessarias})

    exibir_btn_solicitar_correcao = all([existe_campo_com_error, not existe_campo_aguardando_avaliacao,
                                         solicitacao.status == Solicitacao.STATUS_EM_ANALISE, em_periodo_avaliacao])

    exibir_btn_salvar = all([solicitacao.has_status_permite_avaliacao_dados(), pf_eh_responsavel_atual_pela_solicitacao,
                             em_periodo_avaliacao])

    exibir_btn_indeferimento = all(
        [solicitacao.has_status_permite_indeferimento(), pf_eh_responsavel_atual_pela_solicitacao,
         em_periodo_avaliacao])

    exibir_btn_retornar_para_analise = all(
        [solicitacao.has_status_permite_retornar_para_analise(), em_periodo_avaliacao,
         (pf_atende_uo_da_solicitacao or pf_eh_gerente_avaliacao_da_uo)])

    exibir_btn_assumir_atendimento = solicitacao.has_status_permite_avaliacao_dados() \
        and not pf_eh_responsavel_atual_pela_solicitacao \
        and (
        (
            solicitacao.vinculo_responsavel is None and pf_atende_uo_da_solicitacao)
        or pf_eh_gerente_avaliacao_da_uo
    ) or solicitacao_atendida_por_qualquer_uo
    exibir_btn_atribuir_atendimento = solicitacao.has_status_permite_avaliacao_dados() and (
        pf_eh_responsavel_atual_pela_solicitacao or pf_eh_gerente_avaliacao_da_uo)
    exibir_btn_execucao = solicitacao.status == Solicitacao.STATUS_PRONTO_PARA_EXECUCAO and pf_eh_responsavel_atual_pela_solicitacao

    exibir_btn_reenviar_notificacao_correcao_dados = solicitacao.status == Solicitacao.STATUS_AGUARDANDO_CORRECAO_DE_DADOS

    if request.POST:
        if not pf_eh_responsavel_atual_pela_solicitacao:
            raise PermissionDenied

        # Uma vez o form submetido, os dados do jsons do formulário e da avaliação serão atualizados e depois persistidos.
        existe_campo_aguardando_avaliacao = False
        existe_campo_com_error = False

        try:
            for etapa in etapas:
                numero_etapa = etapa['numero_etapa']
                solicitacao_etapa = SolicitacaoEtapa.objects.get(solicitacao=solicitacao, numero_etapa=numero_etapa)
                dados_as_json = solicitacao_etapa.get_dados_as_json()
                for campo in dados_as_json['formulario']:
                    name = campo['name']
                    read_only = campo.get('read_only', False)

                    avaliacao_status_name = 'etapa_{}____{}____status'.format(etapa['numero_etapa'], name)
                    avaliacao_status = request.POST[avaliacao_status_name]
                    avaliacao_status = avaliacao_status if avaliacao_status else None

                    avaliacao_status_msg_name = '{}_msg'.format(avaliacao_status_name)
                    avaliacao_status_msg = request.POST[avaliacao_status_msg_name]
                    avaliacao_status_msg = avaliacao_status_msg if avaliacao_status == 'ERROR' and avaliacao_status_msg else None

                    novo_valor_name = f'etapa_{numero_etapa}____{name}____novo_valor'
                    novo_valor = request.POST.get(novo_valor_name)

                    limpar_valor_name = f'etapa_{numero_etapa}____{name}____limpar_valor'
                    limpar_valor = request.POST.get(limpar_valor_name)

                    existe_campo_aguardando_avaliacao = bool(existe_campo_aguardando_avaliacao or not avaliacao_status)

                    existe_campo_com_error = bool(existe_campo_com_error or avaliacao_status == 'ERROR')

                    if read_only:
                        campo['avaliacao_status'] = 'OK'
                        campo['avaliacao_status_msg'] = None
                    else:
                        campo['avaliacao_status'] = avaliacao_status
                        campo['avaliacao_status_msg'] = avaliacao_status_msg

                    if novo_valor:
                        if campo['type'] == 'date':
                            try:
                                novo_valor = datetime.datetime.strptime(novo_valor, '%d/%m/%Y').strftime('%Y-%m-%d')
                            except Exception:
                                return httprr('.',
                                              f'Data "{novo_valor}" do campo {name} da etapa {numero_etapa} inválida.',
                                              'error')
                        campo['value'] = novo_valor
                    elif limpar_valor == 'true':
                        campo['value'] = ''

                solicitacao_etapa.dados = json.dumps(dados_as_json, indent=4)
                solicitacao_etapa.save()

            if not existe_campo_com_error and not existe_campo_aguardando_avaliacao:
                messages.add_message(request, messages.INFO,
                                     'Todos os campos foram avaliados como "OK". A solicitação está pronta ser executada.')
                solicitacao.status = Solicitacao.STATUS_PRONTO_PARA_EXECUCAO
                solicitacao.status_detalhamento = 'Os dados foram avaliados e aprovados. A solicitação está pronta para execução.'
            else:
                solicitacao.status = Solicitacao.STATUS_EM_ANALISE
                solicitacao.status_detalhamento = 'Aguardando análise dos dados.'

                if existe_campo_aguardando_avaliacao:
                    messages.add_message(request, messages.WARNING, 'Existem campos aguardando avaliação.')

                if existe_campo_com_error:
                    if 'btn_salvar_e_solicitar_correcao' in request.POST:
                        solicitacao.status = Solicitacao.STATUS_AGUARDANDO_CORRECAO_DE_DADOS
                        solicitacao.status_detalhamento = 'Aguardando correção de dados.'
                        messages.add_message(request, messages.INFO, 'A correção de dados foi solicitada.')
                    else:
                        messages.add_message(request, messages.WARNING, 'Existem campos avaliados como "Com Problema".')

            if solicitacao.vinculo_responsavel != request.user.get_vinculo():
                solicitacao.vinculo_responsavel = request.user.get_vinculo()

            solicitacao.save(enviar_email=True)
            messages.add_message(request, messages.INFO, 'Avaliação salva com sucesso.')
        except Exception as e:
            if settings.DEBUG:
                raise e
            capture_exception(e)
            messages.add_message(request, messages.ERROR,
                                 'Erros ao tentar salvar a avaliação. Detalhes: {}'.format(str(e)))

        return redirect('avaliar_solicitacao', id=solicitacao.id)

    return locals()


@rtr()
@permission_required('catalogo_provedor_servico.pode_avaliar_solicitacoes')
def executar_solicitacao(request, id):
    solicitacao = get_object_or_404(Solicitacao, id=id)
    service_provider = get_service_provider_factory().get_service_provider(
        id_servico_portal_govbr=solicitacao.servico.id_servico_portal_govbr)
    try:
        return service_provider.executar_solicitacao(request=request, solicitacao=solicitacao)
    except Exception as e:
        if settings.DEBUG:
            raise e
        if not isinstance(e, ValidationError):
            capture_exception(e)
        return httprr(solicitacao.get_absolute_url(), f'Erro ao executar solicitação. Detalhes: {str(e)}', 'error')


@csrf_exempt
@api_view(['GET'])
@permission_classes([TokenFromTrustedApp])
def acompanhamentos_por_cidadao(request, cpf):
    try:
        cpf = get_cpf_formatado(cpf)
        acompanhamentos = RegistroAcompanhamentoGovBR.objects.filter(solicitacao__cpf=cpf,
                                                                     tipo=RegistroAcompanhamentoGovBR.TIPO_ACOMPANHAMENTO)
        if not acompanhamentos:
            return JsonResponse(data=Resposta(mensagem='Nenhum acompanhamento encontrado.').json(), safe=False)

        serializer = RegistroAcompanhamentoGovBRSerializer(acompanhamentos, many=True)
        resposta = Resposta(resposta=serializer.data)
        return JsonResponse(resposta.json(), safe=False)
    except ConnectionError as e:
        resposta = Resposta.create_from_exception(mensagem='Erro ao listar os acompanhamentos.', exception=e)
        return JsonResponse(data=resposta.json(), safe=False, status=404)
    except Exception as e:
        if settings.DEBUG:
            raise e
        capture_exception(e)
        resposta = Resposta.create_from_exception(mensagem='Erro ao listar os acompanhamentos.', exception=e)
        return JsonResponse(data=resposta.json(), safe=False, status=404)


@csrf_exempt
@api_view(['GET'])
@permission_classes([TokenFromTrustedApp])
def solicitacoes_pendentes_de_avaliacao(request, cpf):
    try:
        cpf = get_cpf_formatado(cpf)
        solicitacoes_pendentes_de_avaliacao = RegistroAcompanhamentoGovBR.objects.filter(solicitacao__cpf=cpf,
                                                                                         tipo=RegistroAcompanhamentoGovBR.TIPO_CONCLUSAO,
                                                                                         avaliado=False)
        if not solicitacoes_pendentes_de_avaliacao:
            return JsonResponse(data=Resposta(mensagem='Nenhuma solicitação pendente de avaliação.').json(), safe=False)

        dados = []
        for registro in solicitacoes_pendentes_de_avaliacao:
            dados.append(
                {
                    'nome_servico': registro.solicitacao.servico.titulo,
                    "etapa": registro.solicitacao.status,
                    "cpfCidadao": registro.payload['cpfCidadao'],
                    "orgao": registro.payload['orgao'],
                    "protocolo": registro.payload['protocolo'],
                    "servico": registro.payload['servico'],
                }
            )
        resposta = Resposta(resposta=dados)
        return JsonResponse(resposta.json(), safe=False)
    except Exception as e:
        if settings.DEBUG:
            raise e
        capture_exception(e)
        resposta = Resposta.create_from_exception(mensagem='Erro ao listar os acompanhamentos.', exception=e)
        return JsonResponse(data=resposta.json(), safe=False, status=404)


@permission_required('catalogo_provedor_servico.pode_avaliar_solicitacoes')
def assumir_atendimento(request, id):
    solicitacao = get_object_or_404(Solicitacao, pk=id)
    vinculo = request.user.get_vinculo()
    try:
        solicitacao.atribuir_responsavel(vinculo_atribuinte=vinculo,
                                         vinculo_responsavel=vinculo,
                                         data_associacao_responsavel=datetime.datetime.now(),
                                         instrucao='Assumiu o atendimento.')
        solicitacao.save()
        messages.success(request, f'O responsável foi associado a {vinculo}')
    except Exception as e:
        if settings.DEBUG:
            raise e
        if not isinstance(e, ValidationError):
            capture_exception(e)
        messages.error(request, str(e))

    return HttpResponseRedirect(reverse('avaliar_solicitacao', args=(id,)))


@rtr()
@login_required()
@permission_required('catalogo_provedor_servico.pode_avaliar_solicitacoes')
def atribuir_atendimento(request, id):
    solicitacao = get_object_or_404(Solicitacao.objects, id=id)
    title = f'Atribuir Solicitação {solicitacao}'

    if not solicitacao.has_status_permite_avaliacao_dados():
        return httprr(solicitacao.get_absolute_url(),
                      'O status da solicitação não permite realizar ações inerentes a avaliação.', 'error')

    form = AtribuirAtendimentoForm(request.POST or None, instance=solicitacao, request=request)
    if form.is_valid():
        form.save()
        return httprr(solicitacao.get_absolute_url(), 'Atribuição realizada com sucesso.')

    return locals()


@rtr()
@permission_required('catalogo_provedor_servico.pode_visualizar_relatorio')
def dashboard(request):
    title = 'Dashboard'
    grafico_evolucao = None
    grafico_status = None
    grafico_responsavel = None
    grafico_responsavel_detalhado = None

    responsavel_atendimento = None

    status_dict = dict(Solicitacao.STATUS_CHOICES)

    form = DashboradFiltroForm(request.GET or None)

    if form.is_valid():
        servico = form.cleaned_data['servico']
        data_inicio = form.cleaned_data['data_inicio']
        data_fim = form.cleaned_data['data_fim']
        uo = form.cleaned_data.get('uo')

        solicitacoes = Solicitacao.objects.filter(
            servico=servico,
            data_criacao__range=(data_inicio, data_fim)
        ).order_by()
        if uo:
            solicitacoes = solicitacoes.filter(uo=uo)
        # Evolução diária das solicitações --------------
        evolucao_diaria = list()
        solicitacoes_evolucao = solicitacoes.annotate(
            dt_criacao=Cast('data_criacao', output_field=models.DateField())
        ).values('dt_criacao').annotate(
            qtd_solicitacoes=Count('dt_criacao')
        )

        for solicitacao in solicitacoes_evolucao.order_by('dt_criacao'):
            evolucao_diaria.append([solicitacao['dt_criacao'].strftime("%d/%m/%Y"), solicitacao['qtd_solicitacoes']])

        grafico_evolucao = PieChart('grafico_evolucao', title='Evolução Diária',
                                    subtitle='Quantidade de solicitações realizadas por dia', data=evolucao_diaria)
        setattr(grafico_evolucao, 'id', 'grafico_evolucao')

        # Solicitações por status ------------
        solicitacao_status = list()
        solicitacoes_status = solicitacoes.values('status').annotate(qtd_status=Count('status'))

        for solicitacao in solicitacoes_status:
            solicitacao_status.append([solicitacao['status'], solicitacao['qtd_status']])

        grafico_status = PieChart('grafico_status', title='Quantidade por Status', subtitle='', data=solicitacao_status)
        setattr(grafico_status, 'id', 'grafico_status')

        # Solicitações por responsável ------------
        responsavel_atendimento = list()
        responsaveis_atendimento = solicitacoes.values('vinculo_responsavel__pessoa__nome').annotate(
            qtd_por_responsavel=Count('vinculo_responsavel'))

        for solicitacao in responsaveis_atendimento:
            responsavel_atendimento.append(
                [solicitacao['vinculo_responsavel__pessoa__nome'], solicitacao['qtd_por_responsavel']])

        grafico_responsavel = PieChart('grafico_responsavel', title='Quantidade por Responsável', subtitle='',
                                       data=responsavel_atendimento)
        setattr(grafico_responsavel, 'id', 'grafico_responsavel')

        # Solicitações por responsável ------------
        responsavel_atendimento_dict = dict()
        responsaveis_atendimento = solicitacoes.values('vinculo_responsavel__pessoa__nome', 'status').annotate(
            total=Count('status'))

        for atendimento in responsaveis_atendimento:
            nome = atendimento['vinculo_responsavel__pessoa__nome'] or '-'
            status = status_dict[atendimento['status']]
            total = atendimento['total']

            if nome == 'None':
                nome = 'Sem Avaliador'

            if nome not in responsavel_atendimento_dict:
                responsavel_atendimento_dict[nome] = dict()
                for key, value in status_dict.items():
                    responsavel_atendimento_dict[nome][value] = 0

            responsavel_atendimento_dict[nome][status] += total

        responsavel_atendimento = list()
        for responsavel, dados in responsavel_atendimento_dict.items():
            responsavel_atendimento.append([responsavel] + list(dados.values()))

        grafico_responsavel_detalhado = LineChart(
            'grafico_responsavel_detalhado', title='Quantidade por Responsável - Detalhamento', subtitle='',
            data=responsavel_atendimento, groups=list(status_dict.values())
        )
        setattr(grafico_responsavel_detalhado, 'id', 'grafico_responsavel_detalhado')

    return locals()


@rtr()
@login_required()
def apagar_atendimento(request):
    if not settings.DEBUG:
        raise PermissionDenied('Esta página só está disponível para ambiente de desenvolvimento.')

    title = 'Apagar Atendimento (Ambiente de Desenvolvimento)'
    form = ApagarAtendimentoForm(data=request.POST or None)
    if form.is_valid():
        solicitacao = form.cleaned_data.get('solicitacao')
        call_command('apagar_atendimentos_digitais', id=solicitacao.id)

        return httprr('..',
                      'O command "apagar_atendimentos_digitais" foi invocado com sucesso. Verifique se o registro foi excluido.')
    return locals()


@rtr()
@login_required()
@permission_required('catalogo_provedor_servico.eh_gerente_local_catalogo',
                     'catalogo_provedor_servico.eh_gerente_sistemico_catalogo')
def gerenciar_equipe(request, servico_id):
    servico = get_object_or_404(Servico, pk=servico_id)
    title = f'Gerenciar Equipe de Atendimento do serviço: {servico}'
    vinculo = request.user.get_vinculo()
    relacionamento = vinculo.relacionamento
    uo_usuario_logado = get_uo(relacionamento)
    eh_gerente_local = request.user.has_perm('catalogo_provedor_servico.eh_gerente_local_catalogo')
    eh_gerente_sistemico = request.user.has_perm('catalogo_provedor_servico.eh_gerente_sistemico_catalogo')

    contador_dict = dict()
    uo_escolhida = None
    if request.GET.get('uo'):
        uo_escolhida = UnidadeOrganizacional.objects.get(pk=request.GET.get('uo'))

    uos = UnidadeOrganizacional.objects.uo()

    if not eh_gerente_sistemico and eh_gerente_local:
        uos = uos.filter(
            pk__in=servico.servicogerenteequipelocal_set.filter(
                vinculo=request.user.get_vinculo()).values_list('campus_id', flat=True)
        )
    if not uo_escolhida:
        uo_escolhida = uos.filter(pk=uo_usuario_logado.pk).first() if uos.filter(
            pk=uo_usuario_logado.pk).exists() else uos.first()

    if not eh_gerente_sistemico and eh_gerente_local and not servico.servicogerenteequipelocal_set.filter(
            vinculo=request.user.get_vinculo(), campus=uo_escolhida).exists():
        return httprr('..', f'Você não gerenciar a equipe deste serviço em {uo_escolhida}.', tag='alert')
    vinculos = Vinculo.objects.filter(servicoequipe__servico=servico,
                                      servicoequipe__campus=uo_escolhida).order_by('pessoa__nome')
    for uo in uos:
        contador_dict[uo.pk] = Vinculo.objects.filter(servicoequipe__servico=servico, servicoequipe__campus=uo).count()

    return locals()


@rtr()
@login_required()
@permission_required('catalogo_provedor_servico.eh_gerente_sistemico_catalogo')
def gerenciar_gerente_equipe_local_servico_catalogo(request, servico_id):
    servico = get_object_or_404(Servico, pk=servico_id)
    title = f'Gerenciar Gerentes Locais do Serviço: {servico}'
    vinculo = request.user.get_vinculo()
    relacionamento = vinculo.relacionamento
    uo_usuario_logado = get_uo(relacionamento)

    contador_dict = dict()
    uo_escolhida = None
    if request.GET.get('uo'):
        uo_escolhida = UnidadeOrganizacional.objects.get(pk=request.GET.get('uo'))

    uos = UnidadeOrganizacional.objects.uo()

    if not uo_escolhida:
        uo_escolhida = uos.filter(pk=uo_usuario_logado.pk).first() if uos.filter(
            pk=uo_usuario_logado.pk).exists() else uos.first()

    vinculos = Vinculo.objects.filter(servicogerenteequipelocal__servico=servico,
                                      servicogerenteequipelocal__campus=uo_escolhida).order_by('pessoa__nome')
    for uo in uos:
        contador_dict[uo.pk] = Vinculo.objects.filter(servicogerenteequipelocal__servico=servico, servicogerenteequipelocal__campus=uo).count()

    return locals()


@rtr()
@login_required()
@permission_required('catalogo_provedor_servico.eh_gerente_local_catalogo',
                     'catalogo_provedor_servico.eh_gerente_sistemico_catalogo')
def adicionar_usuario_equipe(request, servico_id, uo_id):
    servico = get_object_or_404(Servico, pk=servico_id)
    uo = get_object_or_404(UnidadeOrganizacional, pk=uo_id)
    title = f'Adicionar Usuário Equipe de Atendimento do serviço: {servico}'

    relacionamento = request.user.get_vinculo().relacionamento
    eh_gerente_sistemico = request.user.has_perm('catalogo_provedor_servico.eh_gerente_sistemico_catalogo')
    eh_gerente_local = request.user.has_perm(
        'catalogo_provedor_servico.eh_gerente_local_catalogo') and not eh_gerente_sistemico

    if not eh_gerente_sistemico and eh_gerente_local and (not servico.servicogerenteequipelocal_set.filter(
            vinculo=request.user.get_vinculo(), campus=uo).exists()):
        return httprr('..', 'Você não tem permissão para adicionar usuário na equipe desta Unidade.', tag='alert')

    FormClass = AdicionarUsuarioEquipeFormFactory(request.user, uo)
    form = FormClass(request.POST or None)
    if form.is_valid():
        msg_success = 'O(s) seguinte(s) usuário(s) foram adicionado(s):'
        msg_alert = 'O(s) seguintes usuário(s) já estavam incluídos na equipe:'
        tem_sucesso = False
        tem_alerta = False
        for vinculo in form.cleaned_data['vinculo']:
            servicoequipe, created = ServicoEquipe.objects.get_or_create(servico=servico, vinculo=vinculo, campus=uo)
            if created:
                LogEntry.objects.log_action(
                    user_id=request.user.pk,
                    content_type_id=ContentType.objects.get_for_model(servicoequipe).pk,
                    object_id=servicoequipe.pk,
                    object_repr=force_str(servicoequipe),
                    action_flag=ADDITION
                )
                msg_success += f'<a href="{vinculo.relacionamento.get_absolute_url()}">{vinculo.relacionamento}</a>; '
                tem_sucesso = True
            else:
                msg_alert += f'<a href="{vinculo.relacionamento.get_absolute_url()}">{vinculo.relacionamento}</a>; '
                tem_alerta = True

        if tem_sucesso:
            messages.add_message(request, messages.SUCCESS, mark_safe(msg_success))
        if tem_alerta:
            messages.add_message(request, messages.WARNING, mark_safe(msg_alert))

        return httprr('..')
    return locals()


@rtr()
@login_required()
@permission_required('catalogo_provedor_servico.eh_gerente_local_catalogo',
                     'catalogo_provedor_servico.eh_gerente_sistemico_catalogo')
def remover_usuario_equipe(request, servico_id, vinculo_id, uo_id):
    servico = get_object_or_404(Servico, pk=servico_id)
    vinculo = get_object_or_404(Vinculo, pk=vinculo_id)
    uo = get_object_or_404(UnidadeOrganizacional, pk=uo_id)
    eh_gerente_local = request.user.has_perm('catalogo_provedor_servico.eh_gerente_local_catalogo')
    eh_gerente_sistemico = request.user.has_perm('catalogo_provedor_servico.eh_gerente_sistemico_catalogo')

    if not eh_gerente_sistemico and eh_gerente_local and not servico.servicogerenteequipelocal_set.filter(
            vinculo=request.user.get_vinculo()).exists():
        return httprr('.', 'Você não tem permissão para remover usuário na equipe desta Unidade.', tag='alert')
    servicoequipe = ServicoEquipe.objects.filter(vinculo=vinculo, servico=servico, campus=uo).first()
    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(servicoequipe).pk,
        object_id=servicoequipe.pk,
        object_repr=force_str(servicoequipe),
        action_flag=DELETION
    )
    servicoequipe.delete()
    return httprr(
        reverse('gerenciar_equipe_servico_catalogo', args=[servico_id]) + f'?uo={vinculo.setor.uo_id}',
        f'Usuário {vinculo} removido da equipe do serviço com sucesso.', tag='success')


@rtr()
@login_required()
@permission_required('catalogo_provedor_servico.eh_gerente_sistemico_catalogo')
def adicionar_usuario_gerente_equipe_local(request, servico_id, uo_id):
    servico = get_object_or_404(Servico, pk=servico_id)
    uo = get_object_or_404(UnidadeOrganizacional, pk=uo_id)
    title = f'Adicionar Usuário Gerente Equipe Local do Serviço: {servico}'
    relacionamento = request.user.get_vinculo().relacionamento
    FormClass = AdicionarUsuarioEquipeFormFactory(request.user, uo)
    form = FormClass(request.POST or None)
    if form.is_valid():
        msg_success = 'O(s) seguinte(s) usuário(s) foram adicionado(s):'
        msg_alert = 'O(s) seguintes usuário(s) já estavam incluídos na equipe:'
        tem_sucesso = False
        tem_alerta = False
        for vinculo in form.cleaned_data['vinculo']:
            servicogerenteequipe, created = ServicoGerenteEquipeLocal.objects.get_or_create(servico=servico, vinculo=vinculo, campus=uo)
            if created:
                LogEntry.objects.log_action(
                    user_id=request.user.pk,
                    content_type_id=ContentType.objects.get_for_model(servicogerenteequipe).pk,
                    object_id=servicogerenteequipe.pk,
                    object_repr=force_str(servicogerenteequipe),
                    action_flag=ADDITION
                )
                msg_success += f'<a href="{vinculo.relacionamento.get_absolute_url()}">{vinculo.relacionamento}</a>; '
                tem_sucesso = True
            else:
                msg_alert += f'<a href="{vinculo.relacionamento.get_absolute_url()}">{vinculo.relacionamento}</a>; '
                tem_alerta = True

        if tem_sucesso:
            messages.add_message(request, messages.SUCCESS, mark_safe(msg_success))
        if tem_alerta:
            messages.add_message(request, messages.WARNING, mark_safe(msg_alert))

        return httprr('..')
    return locals()


@rtr()
@login_required()
@permission_required('catalogo_provedor_servico.eh_gerente_sistemico_catalogo')
def remover_usuario_gerente_equipe_local(request, servico_id, vinculo_id, uo_id):
    servico = get_object_or_404(Servico, pk=servico_id)
    vinculo = get_object_or_404(Vinculo, pk=vinculo_id)
    uo = get_object_or_404(UnidadeOrganizacional, pk=uo_id)
    servicoegerenteequipe = ServicoGerenteEquipeLocal.objects.filter(vinculo=vinculo, servico=servico, campus=uo).first()
    LogEntry.objects.log_action(
        user_id=request.user.pk,
        content_type_id=ContentType.objects.get_for_model(servicoegerenteequipe).pk,
        object_id=servicoegerenteequipe.pk,
        object_repr=force_str(servicoegerenteequipe),
        action_flag=DELETION
    )
    servicoegerenteequipe.delete()
    return httprr(
        reverse('gerenciar_gerente_equipe_servico_catalogo', args=[servico_id]) + f'?uo={vinculo.setor.uo_id}',
        f'Usuário {vinculo} removido da equipe do serviço com sucesso.', tag='success')


@rtr()
@login_required()
def testar_disponibilidade(request):
    title = 'Testar Disponibilidades'
    form = TestarDisponibilidadeForm(data=request.GET, request=request)
    try:
        if form.is_valid():
            cpf = form.cleaned_data['cpf']
            if cpf:
                cpf = get_cpf_formatado(cpf)
                servicos = get_service_provider_factory().get_avaliacoes_disponibilidade_servicos(cpf,
                                                                                                  avaliar_somente_servicos_ativos=True)
                servicos_disponiveis = []
                servicos_indisponiveis = []
                for servico in servicos:
                    if not servico.criterios_erro:
                        servicos_disponiveis.append(servico)
                    else:
                        servicos_indisponiveis.append(servico)
    except Exception as e:
        if settings.DEBUG:
            raise e
        capture_exception(e)
        erro = f'Serviço indisponível ou mal-configurado. Detalhe: {e}'
        return httprr('/', erro, 'error')

    return locals()
