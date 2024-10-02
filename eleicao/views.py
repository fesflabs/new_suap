# -*- coding: utf-8 -*-
import io
import datetime
import hashlib

import qrcode
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db.models.functions import Lower
from django.http.response import HttpResponse
from django.shortcuts import get_object_or_404
from django.template.defaultfilters import pluralize

from comum.models import PrestadorServico
from comum.utils import get_sigla_reitoria
from djtools import layout
from djtools.templatetags.filters import format_datetime
from djtools.utils import rtr, httprr, to_ascii, render, permission_required, XlsResponse, get_client_ip, get_session_cache, documento
from edu.models import Aluno
from eleicao.forms import ChapaInscricaoForm, CandidatoInscricaoForm, CandidatoValidarForm, ValidarVotoForm, ValidarVotoBuscarForm, ChapaValidarForm, BuscarPublicoForm
from eleicao.models import Eleicao, Candidato, Voto, Edital, Chapa
from rh.models import Servidor, UnidadeOrganizacional


@layout.inscricao()
def index_inscricoes(request):
    inscricoes = list()
    # Eleições com inscrição aberta
    eleicoes_abertas = Eleicao.get_inscricao_aberta(request.user)
    for eleicao in eleicoes_abertas:
        inscricoes.append(
            dict(
                url='/eleicao/inscricao/{:d}/'.format(eleicao.id),
                titulo='Inscreva-se para: <strong>{}</strong>.'.format(eleicao.descricao),
                prazo=eleicao.edital.data_inscricao_fim,
            )
        )

    # Eleições em votação
    for eleicao in Eleicao.get_em_votacao(request.user):
        if not Voto.objects.filter(eleitor=request.user, candidato__eleicao=eleicao).exists():
            inscricoes.append(
                dict(
                    url='/eleicao/votacao/{:d}/'.format(eleicao.id),
                    titulo='Votação aberta para: <strong>{}</strong>.'.format(eleicao.descricao),
                    prazo=eleicao.edital.data_votacao_fim,
                )
            )

    return inscricoes


@layout.info()
def index_infos(request):
    infos = list()
    # Eleições em campanha
    if Eleicao.get_em_campanha(request.user):
        qtd = len(Eleicao.get_em_campanha(request.user))
        infos.append(dict(url='/eleicao/campanha/', titulo='<strong>Eleições:</strong> Veja a{plural} campanha{plural}.'.format(plural=pluralize(qtd))))

    return infos


@layout.quadro('Eleições', icone='thumbs-up')
def index_quadros(quadro, request):
    def do():
        eleicoes_abertas = Eleicao.get_abertas(request.user)
        if eleicoes_abertas:
            # Eleições que gerencio
            if (
                request.user.eh_servidor
                and Edital.objects.filter(vinculos_coordenadores=request.user.get_vinculo(), data_resultado_final__year__gte=datetime.date.today().year).exists()
            ):
                quadro.add_item(layout.ItemAcessoRapido(titulo='Minhas Eleições', icone='bars', url='/admin/eleicao/edital/?tab=tab_minhas_eleicoes'))

            # Eleições que concorri
            tem_eleicoes_participacao = Candidato.objects.filter(candidato_vinculo=request.user.get_vinculo())
            if tem_eleicoes_participacao:
                quadro.add_item(layout.ItemAcessoRapido(titulo='Minhas Candidaturas', icone='bars', url='/eleicao/minhas_candidaturas/'))

            # Eleições em votação
            for eleicao in Eleicao.get_em_votacao(request.user):
                if Voto.objects.filter(eleitor=request.user, candidato__eleicao=eleicao).exists():
                    quadro.add_item(
                        layout.ItemLista(titulo='Comprovante de Votação'.format(), valor=eleicao, url=f'/eleicao/votacao/{eleicao.id}/')
                    )

            # Resultado Preliminar
            for eleicao in eleicoes_abertas:
                if eleicao.pode_ver_resultado_preliminar(request.user.get_vinculo()):
                    quadro.add_item(
                        layout.ItemLista(titulo='Resultado Preliminar', valor=eleicao, url=f'/eleicao/resultado/{eleicao.id}/')
                    )

        return quadro

    return get_session_cache(request, 'index_quadros_eleicao', do, 24 * 3600)


@rtr()
@login_required
def votacao(request, eleicao_id):
    eleicao = get_object_or_404(Eleicao, id=eleicao_id)
    title = 'Votação para {}'.format(eleicao.descricao)
    vinculo = request.user.get_vinculo()
    candidatos = eleicao.get_candidatos_validos(vinculo)
    voto = Voto.get_por_eleicao_eleitor(eleicao, vinculo)
    if voto:
        title = 'Comprovante de Votação'
        return render('votar.html', locals())

    if not eleicao.pode_votar(vinculo):
        raise PermissionDenied

    return locals()


@rtr()
@login_required
def votar(request, candidato_id):
    title = 'Comprovante de Votação'
    candidato = get_object_or_404(Candidato, pk=candidato_id)
    vinculo = request.user.get_vinculo()
    if not candidato.eleicao.pode_votar_em(vinculo, candidato):
        raise PermissionDenied

    sub_instance = vinculo.relacionamento
    if isinstance(sub_instance, Aluno):
        campus = sub_instance.curso_campus.diretoria.setor.uo
    elif isinstance(sub_instance, PrestadorServico):
        campus = sub_instance.setor.uo
    elif isinstance(sub_instance, Servidor):
        if sub_instance.campus_lotacao_siape:
            campus = sub_instance.campus_lotacao_siape.equivalente
        elif sub_instance.campus_exercicio_siape:
            campus = sub_instance.campus_exercicio_siape.equivalente
        elif sub_instance.campus:
            campus = sub_instance.campus.equivalente

    voto = Voto.objects.create(eleicao=candidato.eleicao, candidato=candidato, data_voto=datetime.datetime.today(), ip=get_client_ip(request), campus=campus)
    voto.string_hash = '{}|{}|{}|{}|{}'.format(
        voto.id, to_ascii(voto.candidato.candidato_vinculo.pessoa.nome), to_ascii(voto.eleitor.get_profile().nome), format_datetime(voto.data_voto), voto.ip
    ).encode()
    voto.hash = hashlib.sha1(voto.string_hash).hexdigest()
    voto.save()
    return locals()


@login_required
def voto_qrcode(request, voto_id):
    voto = get_object_or_404(Voto, pk=voto_id)
    # gerando qrcode
    img = qrcode.make(voto.string_hash)
    fp = io.BytesIO()
    img.save(fp, 'png')
    return HttpResponse(fp.getvalue(), content_type="image/png")


@rtr()
@permission_required('eleicao.validar_candidato')
def validar_candidato(request, candidato_id):
    title = 'Avaliar Candidatura'
    candidato = get_object_or_404(Candidato, pk=candidato_id)
    if not candidato.eleicao.pode_validar(request.user.get_vinculo()) or not candidato.pode_ser_validado():
        raise PermissionDenied

    form = CandidatoValidarForm(request.POST or None, candidato=candidato)
    if form.is_valid():
        form.validar()
        return httprr('..', 'O candidato foi avaliado.')

    return locals()


@rtr()
@permission_required('eleicao.validar_chapa')
def validar_chapa(request, chapa_id):
    title = 'Avaliar Candidatura'
    chapa = get_object_or_404(Chapa, pk=chapa_id)
    if not chapa.eleicao.pode_validar(request.user.get_vinculo()) or not chapa.pode_ser_validado():
        raise PermissionDenied

    form = ChapaValidarForm(request.POST or None, chapa=chapa)
    if form.is_valid():
        form.validar()
        return httprr('..', 'A chapa foi avaliada.')

    return locals()


@rtr()
@login_required
def minhas_candidaturas(request):
    title = 'Minhas Candidaturas'
    vinculo = request.user.get_vinculo()
    candidaturas = Candidato.objects.filter(candidato_vinculo=vinculo)
    sub_instance = vinculo.relacionamento
    if isinstance(sub_instance, Aluno):
        campus = sub_instance.curso_campus.diretoria.setor.uo
    elif isinstance(sub_instance, PrestadorServico):
        campus = sub_instance.setor.uo
    elif isinstance(sub_instance, Servidor):
        if sub_instance.campus_lotacao_siape:
            campus = sub_instance.campus_lotacao_siape.equivalente
        elif sub_instance.campus_exercicio_siape:
            campus = sub_instance.campus_exercicio_siape.equivalente
        elif sub_instance.campus:
            campus = sub_instance.campus.equivalente

    return locals()


@rtr()
@login_required
def inscricao(request, eleicao_id):
    eleicao = get_object_or_404(Eleicao, pk=eleicao_id)
    vinculo = request.user.get_vinculo()
    if not eleicao.pode_inscrever(vinculo):
        raise PermissionDenied

    sub_instance = vinculo.relacionamento
    if isinstance(sub_instance, Aluno):
        campus = sub_instance.curso_campus.diretoria.setor.uo
    elif isinstance(sub_instance, PrestadorServico):
        campus = sub_instance.setor.uo
    elif isinstance(sub_instance, Servidor):
        if sub_instance.campus_lotacao_siape:
            campus = sub_instance.campus_lotacao_siape.equivalente
        elif sub_instance.campus_exercicio_siape:
            campus = sub_instance.campus_exercicio_siape.equivalente
        elif sub_instance.campus:
            campus = sub_instance.campus.equivalente

    title = 'Inscrição para {}'.format(eleicao.descricao)
    form = None
    if eleicao.tipo == Eleicao.TIPO_CHAPA:
        form = ChapaInscricaoForm(request.POST or None, eleicao=eleicao)
    else:
        candidato = Candidato()
        candidato.candidato_vinculo = vinculo
        candidato.campus = campus
        candidato.eleicao = eleicao
        form = CandidatoInscricaoForm(request.POST or None, instance=candidato, eleicao=eleicao)

    if form.is_valid():
        form.save()
        return httprr('/', 'Sua inscrição foi realizada.')

    return locals()


@rtr()
@login_required
def campanha(request):
    title = 'Campanha(s)'
    eleicoes = Eleicao.get_em_campanha(request.user)
    if not eleicoes:
        raise PermissionDenied

    for eleicao in eleicoes:
        eleicao.candidatos = eleicao.get_candidatos_validos(request.user.get_vinculo())

    return locals()


@rtr()
@permission_required('eleicao.add_eleicao')
def validar_votacao(request, eleicao_id):
    eleicao = get_object_or_404(Eleicao, pk=eleicao_id)
    title = 'Validar Votos: {}'.format(eleicao.descricao)
    if not eleicao.pode_homologar(request.user.get_vinculo()):
        raise PermissionDenied

    form = ValidarVotoBuscarForm(request.GET or None)
    votos = eleicao.voto_set.order_by('eleitor__pessoafisica__nome')
    if form.is_valid():
        votos = form.processar(votos)

    return locals()


@rtr()
@permission_required('eleicao.validar_voto')
def invalidar_voto(request, voto_id):
    title = 'Avaliar voto'
    voto = get_object_or_404(Voto, pk=voto_id)
    if not voto.eleicao.pode_homologar(request.user.get_vinculo()):
        raise PermissionDenied

    voto.valido = False
    form = ValidarVotoForm(request.POST or None, instance=voto)
    if form.is_valid():
        form.save()
        return httprr('..', 'Voto avaliado com sucesso.')

    return locals()


@rtr()
@login_required()
def resultado(request, eleicao_id):
    eleicao = get_object_or_404(Eleicao, pk=eleicao_id)
    title = 'Resultado: {}'.format(eleicao.descricao)
    if not eleicao.pode_ver_resultado_final(request.user.get_vinculo()) and not eleicao.pode_ver_resultado_preliminar(request.user.get_vinculo()):
        raise PermissionDenied

    if eleicao.resultado_global:
        candidatos = eleicao.obter_resultados()
    else:
        campi = eleicao.obter_resultados_por_campus()

    return locals()


@documento()
@rtr()
@login_required()
def resultado_pdf(request, eleicao_id):
    eleicao = get_object_or_404(Eleicao, pk=eleicao_id)
    title = 'Resultado: {}'.format(eleicao.descricao)
    if not eleicao.pode_ver_resultado_final(request.user.get_vinculo()) and not eleicao.pode_ver_resultado_preliminar(request.user.get_vinculo()):
        raise PermissionDenied

    uo = UnidadeOrganizacional.objects.suap().get(sigla=get_sigla_reitoria())
    if eleicao.resultado_global:
        candidatos = eleicao.obter_resultados()
    else:
        campi = eleicao.obter_resultados_por_campus()

    return locals()


@login_required()
def exportar_resultado(request, edital_id):
    edital = get_object_or_404(Edital, pk=edital_id)
    if not edital.pode_ver_resultado(request.user.get_vinculo()):
        raise PermissionDenied

    rows = [['Campus', 'Público', 'Candidato', 'Tempo na Instituição (Em anos)', 'Idade (Em anos)', 'Quantidade de votos']]
    for eleicao in edital.eleicao_set.order_by('publico'):
        campi = eleicao.obter_resultados_por_campus()
        for campus in campi:
            if hasattr(campus, 'candidatos'):
                for candidato in campus.candidatos:
                    row = []
                    nome_publico = '-'
                    if eleicao.publico:
                        nome_publico = eleicao.publico.nome
                    row.append(campus.nome)
                    row.append(nome_publico)
                    row.append(candidato.candidato_vinculo.pessoa.nome)
                    row.append(candidato.get_tempo_na_instituicao().days / 365.25)
                    data_nascimento = '-'
                    if candidato.candidato_vinculo.relacionamento.pessoa_fisica.nascimento_data:
                        data_nascimento = (datetime.date.today() - candidato.candidato_vinculo.relacionamento.pessoa_fisica.nascimento_data).days / 365.25
                    row.append(data_nascimento)
                    votos = '{}'.format(candidato.qtd_votos)
                    row.append(votos)
                    rows.append(row)

    return XlsResponse(rows)


@rtr()
@login_required()
def ver_publico(request, eleicao_id):
    eleicao = get_object_or_404(Eleicao, pk=eleicao_id)
    title = 'Público da Eleição: {}'.format(eleicao)
    vinculo = request.user.get_vinculo()
    eh_coordenador_eleicao = eleicao.edital.eh_coordenador(vinculo) or request.user.is_superuser
    vinculos = eleicao.vinculo_publico_eleicao.all().order_by(Lower('pessoa__nome'))
    votos = Voto.objects.filter(candidato__eleicao=eleicao)
    publico = []
    for vinculo in vinculos:
        votou = votos.filter(eleitor=vinculo.user, valido=True).exists()
        publico.append({'vinculo': vinculo, 'votou': votou})

    pode_ver_resultados = False
    if (eleicao.pode_ver_resultado_final(vinculo) or eleicao.pode_ver_resultado_preliminar(vinculo)) and votos.exists():
        pode_ver_resultados = True
    form = BuscarPublicoForm(request.GET or None, eleicao=eleicao)
    if form.is_valid():
        vinculos = form.processar()

    return locals()


@rtr()
@login_required()
def atualizar_publico(request, eleicao_id):
    eleicao = get_object_or_404(Eleicao, pk=eleicao_id)
    vinculo = request.user.get_vinculo()
    if not eleicao.edital.eh_coordenador(vinculo) and not request.user.is_superuser:
        raise PermissionDenied('Você não tem permissão para acessar essa tela.')

    eleicao.save()
    return httprr('/eleicao/ver_publico/{}/'.format(eleicao_id), 'Público da eleição {} foi atualizado com sucesso.'.format(eleicao))
