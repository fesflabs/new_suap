import time
from datetime import datetime, date

from django.conf import settings
from django.contrib.auth import authenticate
from oauth2_provider.contrib.rest_framework import OAuth2Authentication, IsAuthenticatedOrTokenHasScope
from oauth2_provider.decorators import protected_resource
from rest_framework import status
from rest_framework import viewsets
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.authtoken import views
from rest_framework.decorators import api_view
from rest_framework.decorators import permission_classes, authentication_classes
from rest_framework.exceptions import NotFound
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.settings import api_settings
from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.settings import api_settings as jwt_settings
from rest_framework_simplejwt.views import token_obtain_pair
from rest_framework.test import APIRequestFactory
from url_filter.integrations.drf import DjangoFilterBackend

from ae.models import Programa, Participacao
from comum.models import Ano, User, PessoaEndereco, PessoaTelefone
from comum.utils import get_setor, datas_entre, agrupar_em_pares, formata_segundos
from contracheques.models import ContraCheque
from contracheques.models import ContraChequeRubrica as ContraChequeRubricaModel
from contratos.models import Contrato
from demandas.models import Atualizacao
from djtools.templatetags.filters import format_
from djtools.utils import primeiro_dia_da_semana
from edu.models import Aluno, MatriculaPeriodo, Diario
from edu.models import CursoCampus
from edu.models.historico import MatriculaDiario
from edu.models.professores import Professor
from edu.models.utils import PeriodoLetivoAtual
from eventos.models import Banner
from patrimonio.models import Inventario
from pesquisa.models import Projeto as ProjetoPesquisa, Participacao as PartPesquisa
from ponto.models import Frequencia, Liberacao
from projetos.models import Projeto as ProjetoExtensao, Participacao as PartExtensao
from protocolo.models import Processo
from rh.admin import ServidorAdmin
from rh.models import Servidor, UnidadeOrganizacional, Setor, Funcionario, PCA, ServidorOcorrencia, ServidorAfastamento
from .models import AplicacaoOAuth2 as Application
from .permissions import TokenFromTrustedApp

# TODO: usar `from . import serializers` para evitar import gigante abaixo
from .serializers import (
    Profile,
    PontoFrequencia,
    TempoIntervalo,
    CalendarioAdministrativo,
    EventoCalendarioAdministrativo,
    ListaServidores,
    ContraChequeDisponivel,
    ContraChequeMesAno,
    ContraChequeDetalhe,
    ContraChequeRubrica,
    EstatisticaServidores,
    MeusProcessos,
    MeuProcesso,
    AlunoSerializer,
    CursoCampusSerializer,
    ServidorSerializer,
    ProgramaSerializer,
    UnidadeOrganizacionalSerializer,
    ParticipacaoSerializer,
    ProjetoPesquisaSerializer,
    ProjetoExtensaoSerializer,
    AtualizacaoSerializer,
    InventarioSerializer,
    ProcessoSerializer,
    ContratoSerializer,
    SetorSerializer,
    ProfileSerializer,
    MatriculaPeriodoSerializer,
    ItemConfiguracaoAvaliacaoSerializer,
    BoletimSerializer,
    ContraChequeAnoMesSerializer,
    ContraChequeSerializer,
    FrequenciasHojeSerializer,
    MatriculaDiarioSerializer,
    DetalheProcessoSerializer,
    FeriasSerializer,
    ServidorOcorrenciaSerializer,
    ServidorAfastamentoSerializer,
    ParticipacaoProjetoPesquisaSerializer,
    ParticipacaoProjetoExtensaoSerializer,
    DiarioSerializer,
    PlanoIndividualTrabalhoSerializer,
    BannerSerializer,
    AlunoCarometro,
    ServidorSerializer2,
    ServidorSerializer3,
    ContraChequeSerializer2,
    ApplicationSerializer,
)
from .services_utils import service_doc, ServiceDocParameter, hora_min_seg_to_str, exigir_captcha, response_captcha


@api_view(("POST",))
@service_doc(
    "Confere a autenticidade de um usuário (login e senha exigidos).",
    token_authorization=False,
    parameters=[
        ServiceDocParameter(name="login", description="Login do usuário", paramType=ServiceDocParameter.PARAM_TYPE_FORM),
        ServiceDocParameter(name="senha", description="Senha do usuário", paramType=ServiceDocParameter.PARAM_TYPE_FORM),
    ],
)
def confere_login_senha(request):
    if not exigir_captcha(request.data.get("username")):
        login = request.POST.get("login", None)
        senha = request.POST.get("senha", None)

        if login and senha:
            if authenticate(username=login, password=senha):
                return Response({"detail": "Credenciais válidas"}, status=status.HTTP_200_OK)
            else:
                return Response({"detail": "Credenciais inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({"detail": "É necessário informar o login e a senha do usuário."}, status=status.HTTP_400_BAD_REQUEST)
    else:
        return response_captcha()


@api_view(["POST"])
@permission_classes((AllowAny,))
@service_doc(
    "Obtém o token de um usuário (username e password exigidos).",
    token_authorization=False,
    parameters=[
        ServiceDocParameter(name="username", description="Username do usuário", paramType=ServiceDocParameter.PARAM_TYPE_FORM),
        ServiceDocParameter(name="password", description="Password do usuário", paramType=ServiceDocParameter.PARAM_TYPE_FORM),
    ],
)
def obtem_token(request):
    if not exigir_captcha(request.data.get("username")):
        login = request.data.get("username", None)
        senha = request.data.get("password", None)

        if login and senha:
            if authenticate(username=login, password=senha):
                return views.ObtainAuthToken().post(request)  # usa a implementação nativa do rest_framework
            else:
                return Response({"detail": "Credenciais inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({"detail": "É necessário informar o login e a senha do usuário."}, status=status.HTTP_400_BAD_REQUEST)

    else:
        return response_captcha()


@api_view(["POST"])
@permission_classes((AllowAny,))
@service_doc(
    "Obtém o token jwt de um usuário (username e password exigidos).",
    token_authorization=False,
    parameters=[
        ServiceDocParameter(name="username", description="Username do usuário", paramType=ServiceDocParameter.PARAM_TYPE_FORM),
        ServiceDocParameter(name="password", description="Password do usuário", paramType=ServiceDocParameter.PARAM_TYPE_FORM),
    ],
)
def obtem_token_jwt(request):
    if not exigir_captcha(request.data.get("username")):
        login = request.data.get("username", None)
        senha = request.data.get("password", None)

        if login and senha:
            if authenticate(username=str(login), password=str(senha)):
                factory = APIRequestFactory()
                request_drf = factory.post('/api-token-auth/', request.data, format='json')
                return token_obtain_pair(request_drf)  # usa a implementação nativa do rest_framework_jwt
            else:
                return Response({"detail": "Credenciais inválidas"}, status=status.HTTP_401_UNAUTHORIZED)
        else:
            return Response({"detail": "É necessário informar o login e a senha do usuário."}, status=status.HTTP_400_BAD_REQUEST)

    else:
        return response_captcha()


@api_view(["GET"])
@authentication_classes((JWTAuthentication, TokenAuthentication))
@service_doc("Obtém os dados do usuário logado (exige o seu token).", response_serializer="api.serializers.ProfileSerializer")
def obtem_meus_dados(request):
    obj = ProfileSerializer(request.user)
    return Response(obj.data)


@api_view(["GET"])
@authentication_classes((JWTAuthentication, TokenAuthentication))
@service_doc(
    "Obtém dados de um usuário qualquer " "(exige o token do usuário requisitante).", response_serializer="api.serializers.Profile"
)
def obtem_profile(request, matricula):
    response = Profile()
    pessoa_fisica = Servidor.objects.filter(matricula=matricula)
    if pessoa_fisica.exists():
        response.set_profile_from_pessoa_fisica(pessoa_fisica[0])
        return Response(response.data)
    else:
        return Response({"detail": "Matrícula não encontrada."}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@authentication_classes((JWTAuthentication, TokenAuthentication))
@service_doc(
    "Obtém a frequência ocorrida em uma certa data e de um usuário qualquer " "(exige o token do usuário requisitante).",
    response_serializer="api.serializers.PontoFrequencia",
    parameters=[
        ServiceDocParameter(
            name="data", description="Data de referência (formato dd/mm/aaaa)", paramType=ServiceDocParameter.PARAM_TYPE_QUERY
        )
    ],
)
def obtem_frequencia(request, matricula):

    if not request.user.eh_servidor:
        return Response({"detail": "Usuário não tem permissão de acesso a esse serviço."}, status=status.HTTP_403_FORBIDDEN)
    #
    servidor = request.user.get_relacionamento()
    if servidor and servidor.matricula == matricula:
        try:
            data = request.GET.get("data", "")
            #
            data_dia = int(data.split("/")[0])
            data_mes = int(data.split("/")[1])
            data_ano = int(data.split("/")[2])
            #
            data = datetime(data_ano, data_mes, data_dia)
        except Exception:
            return Response({"detail": "Data inválida."}, status=status.HTTP_400_BAD_REQUEST)
        #
        pessoa_fisica = Servidor.objects.filter(matricula=matricula)
        if not pessoa_fisica.exists():
            return Response({"detail": "Matrícula não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        #
        response = PontoFrequencia()
        #
        response.data_referencia = data.strftime("%d/%m/%Y")
        #
        frequencias = Frequencia.objects.filter(
            vinculo=pessoa_fisica[0].get_vinculo(), horario__year=data.year, horario__month=data.month, horario__day=data.day
        ).order_by("horario")
        #
        # jornada de trabalho do dia
        try:
            jornadas = pessoa_fisica[0].get_jornadas_servidor_dict(data_inicio=data.date(), data_fim=data.date())
            response.jornada_trabalho = jornadas[data.date()].get_jornada_trabalho_diaria()
        except Exception:
            response.jornada_trabalho = 0
        #
        # registros de frequencias
        segundos = 0
        frequencia_anterior = None
        registros = ""
        for frequencia in frequencias:
            if frequencia_anterior:
                qtd_hora = frequencia.horario.hour - frequencia_anterior.horario.hour
                qtd_min = frequencia.horario.minute - frequencia_anterior.horario.minute
                qtd_seg = frequencia.horario.second - frequencia_anterior.horario.second
                segundos += qtd_hora * 60 * 60
                segundos += qtd_min * 60
                segundos += qtd_seg
                frequencia_anterior = None
            else:
                frequencia_anterior = frequencia
            registro_horas, registro_minutos, registro_segundos = hora_min_seg_to_str(
                frequencia.horario.hour, frequencia.horario.minute, frequencia.horario.second
            )
            if len(registros):
                registros += "|"
            registros += f"{registro_horas}:{registro_minutos}"
        response.registros = registros
        #
        # carga horária
        houve_frequencias_e_ha_uma_entrada_sem_saida_correspondente = len(frequencias) and frequencia_anterior
        if houve_frequencias_e_ha_uma_entrada_sem_saida_correspondente:
            agora_referencia = datetime.now()
            if not data.date() == agora_referencia.date():
                agora_referencia = datetime(data.year, data.month, data.day, 23, 59, 59)
            qtd_hora = agora_referencia.hour - frequencia_anterior.horario.hour
            qtd_min = agora_referencia.minute - frequencia_anterior.horario.minute
            qtd_seg = agora_referencia.second - frequencia_anterior.horario.second
            segundos += qtd_hora * 60 * 60
            segundos += qtd_min * 60
            segundos += qtd_seg
        horas = segundos // (60 * 60)
        minutos = (segundos % 3600) // 60
        segundos = (segundos % 3600) % 60
        horas, minutos, segundos = hora_min_seg_to_str(horas, minutos, segundos)
        response.carga_horaria = f"{horas}:{minutos}:{segundos}"
        #
        return Response(response.data)
    else:
        return Response({"detail": "Usuário não tem permissão de acesso a esse serviço."}, status=status.HTTP_403_FORBIDDEN)


@api_view(["GET"])
@authentication_classes((JWTAuthentication, TokenAuthentication))
@service_doc(
    "Obtém o tempo de intervalo ocorrido em uma certa data e de um usuário qualquer " "(exige o token do usuário requisitante).",
    response_serializer="api.serializers.TempoIntervalo",
    parameters=[
        ServiceDocParameter(
            name="data", description="Data de referência (formato dd/mm/aaaa)", paramType=ServiceDocParameter.PARAM_TYPE_QUERY
        )
    ],
)
def obtem_tempo_intervalo(request, matricula):
    if not request.user.eh_servidor:
        return Response({"detail": "Usuário não tem permissão de acesso a esse serviço."}, status=status.HTTP_403_FORBIDDEN)

    servidor = request.user.get_relacionamento()
    if servidor and servidor.matricula == matricula:
        try:
            data = request.GET.get("data", "")
            #
            data_dia = int(data.split("/")[0])
            data_mes = int(data.split("/")[1])
            data_ano = int(data.split("/")[2])
            #
            data = datetime(data_ano, data_mes, data_dia)
        except Exception:
            return Response({"detail": "Data inválida."}, status=status.HTTP_400_BAD_REQUEST)
        #
        pessoa_fisica = Servidor.objects.filter(matricula=matricula)
        if not pessoa_fisica.exists():
            return Response({"detail": "Matrícula não encontrada."}, status=status.HTTP_404_NOT_FOUND)
        #
        response = TempoIntervalo()
        #
        response.data_referencia = data.strftime("%d/%m/%Y")
        #
        frequencias = Frequencia.objects.filter(
            vinculo=pessoa_fisica[0].get_vinculo(), horario__year=data.year, horario__month=data.month, horario__day=data.day
        ).order_by("horario")
        segundos = 0
        frequencia_inicio_intervalo = None
        frequencia_fim_intervalo = None
        if len(frequencias) > 2:  # 0, 1, 2, 3, ..., N
            frequencia_inicio_intervalo = frequencias[1]
            frequencia_fim_intervalo = frequencias[2]
        elif len(frequencias) == 2:  # 0, 1
            frequencia_inicio_intervalo = frequencias[1]
        #
        if frequencia_inicio_intervalo:
            horario_inicio_intervalo = frequencia_inicio_intervalo.horario
            #
            if frequencia_fim_intervalo:
                horario_fim_intervalo = frequencia_fim_intervalo.horario
            else:
                agora = datetime.now()
                if not data.date() == agora.date():
                    #
                    # data limite para se calcular o intervalo do dia
                    agora = datetime(data.year, data.month, data.day, 23, 59, 59)
                #
                horario_fim_intervalo = datetime(data.year, data.month, data.day, agora.hour, agora.minute, agora.second)
            #
            segundos = (horario_fim_intervalo - horario_inicio_intervalo).seconds
        #
        response.horas = segundos // (60 * 60)
        response.minutos = segundos // 60 % 60
        response.segundos = segundos // 60 % 60 % 60
        response.minutos_inteiros = segundos // 60
        response.segundos_inteiros = segundos
        #
        response.terceiro_registro_ocorrido = len(frequencias) > 2
        #
        return Response(response.data)
    else:
        return Response({"detail": "Usuário não tem permissão de acesso a esse serviço."}, status=status.HTTP_403_FORBIDDEN)
        #


@api_view(["GET"])
@authentication_classes((JWTAuthentication, TokenAuthentication))
@service_doc(
    "Obtém o meu calendário administrativo do ano corrente " "(exige o token do usuário requisitante).",
    response_serializer="api.serializers.CalendarioAdministrativo",
)
def obtem_meu_calendario_administrativo(request):
    response = CalendarioAdministrativo()

    get_object_or_404(Funcionario, username=request.user.username)
    ano = datetime.now().year
    usuario_logado = request.user.get_profile()

    campus = usuario_logado.funcionario.setor.uo
    liberacoes = Liberacao.get_liberacoes_calendario(campus, ano)

    try:
        ano = Ano.objects.get(ano=ano)
    except Exception:
        return Response({"detail": f"Problema na obtenção dos dados do ano {ano}."}, status=status.HTTP_400_BAD_REQUEST)
    #
    documentos_legais = []
    eventos = []
    recessos = []
    feriados = []
    for liberacao in liberacoes:
        evento = EventoCalendarioAdministrativo(
            data_inicio=liberacao.data_inicio, data_fim=liberacao.data_fim, descricao=liberacao.descricao
        )
        if liberacao.tipo == 0 and evento not in documentos_legais:
            documentos_legais.append(evento)
        elif liberacao.tipo == 1 and evento not in eventos:
            eventos.append(evento)
        elif liberacao.tipo == 2 and evento not in recessos:
            recessos.append(evento)
        elif (liberacao.tipo == 3 or liberacao.tipo == 4) and evento not in feriados:
            feriados.append(evento)
    #
    ferias = []
    if "ferias" in settings.INSTALLED_APPS and request.user.eh_servidor:
        from ferias.models import Ferias

        data_ini = date(ano.ano, 1, 1)
        data_fim = date(ano.ano, 12, 31)
        periodos = Ferias.get_periodos_pessoa_estava_de_ferias(request.user.get_relacionamento(), data_ini, data_fim)
        for periodo_ini, periodo_fim, label in periodos:
            evento = EventoCalendarioAdministrativo(data_inicio=periodo_ini, data_fim=periodo_fim, descricao=label)
            if evento not in ferias:
                ferias.append(evento)
    #
    response.ano = str(ano)
    response.campus = str(campus)
    response.documentos_legais = [documento.data for documento in documentos_legais]
    response.eventos = [dia_evento.data for dia_evento in eventos]
    response.recessos = [recesso.data for recesso in recessos]
    response.feriados = [feriado.data for feriado in feriados]
    response.ferias = [dia_ferias.data for dia_ferias in ferias]
    #
    return Response(response.data)


@api_view(["GET"])
@authentication_classes((JWTAuthentication, TokenAuthentication))
@service_doc(
    "Obtém uma lista paginada de servidores de acordo com alguns critérios " "(exige o token do usuário requisitante).",
    response_serializer="api.serializers.ListaServidores",
    parameters=[
        ServiceDocParameter(name="pesquisa", description="Termo a pesquisar"),
        ServiceDocParameter(name="pagina", description="Número da página a exibir (padrão 1)", required=False),
        ServiceDocParameter(name="registros_na_pagina", description="Quantidade de registros na página (padrão 10)", required=False),
    ],
)
def obtem_lista_servidores_paginada(request):
    response = ListaServidores()
    #
    pesquisa = request.GET.get("pesquisa", None)
    pagina = int(request.GET.get("pagina", "1"))
    registros_na_pagina = int(request.GET.get("registros_na_pagina", "10"))
    #
    num_ultima_posicao = pagina * registros_na_pagina - registros_na_pagina
    lista_servidores = _obtem_lista_servidores(pesquisa, num_ultima_posicao, registros_na_pagina)
    #
    lista_servidores_final = []
    for servidor in lista_servidores:
        pessoa = Profile()
        pessoa.set_profile_from_pessoa_fisica(servidor)
        #
        lista_servidores_final.append(pessoa)
    #
    response.quantidade = len(lista_servidores_final)
    response.servidores = [servidor.data for servidor in lista_servidores_final]
    #
    return Response(response.data)
    #


def _obtem_lista_servidores(pesquisa, num_ultima_posicao, num_registros_a_retornar):
    servidores_manager = Servidor.objects.ativos()
    #
    if pesquisa:
        """
        um "and" entre as partes do termo pesquisado sobre um campo pesquisado
        e depois um "or" entre os campos pesquisados

        pesquisa: "fulano de tal"

        filtro:
            filter(campo1="fulano") & filter(campo1="de") & filter(campo1="tal")
                |
            filter(campo2="fulano") & filter(campo2="de") & filter(campo2="tal")
                |
            filter(campo3="fulano") & filter(campo3="de") & filter(campo3="tal")
                |
            ...

        por que isso?
            no banco -> campo1 = "fulano da silva de tal"
            pesquisa -> "fulano de tal"
            filtro -> campo1__icontains="fulano de tal"
                NÃO RETORNA NENHUM RESULTADO, EMBORA "fulano de tal" ESTEJA CONTIDO EM "fulano da silva de tal"

        Essa implementação retorna resultados mesmo invertendo a ordem dos termos da pesquisa.
            pesquisa -> "de tal fulano"

        TODO: pesquisar lookup "__search"
        """
        lista_servidores = None
        for field in ServidorAdmin.search_fields:
            field_queryset = None
            for pesquisa_parte in pesquisa.split(" "):
                pesquisa_parte_filtro = {}
                pesquisa_parte_filtro.setdefault(f"{field}__icontains", f"{pesquisa_parte}")
                #
                if field_queryset:
                    #
                    # aplica AND
                    field_queryset = field_queryset & field_queryset.filter(**pesquisa_parte_filtro)
                else:
                    #
                    # AND nos próximos filtros
                    field_queryset = servidores_manager.filter(**pesquisa_parte_filtro)
            #
            if lista_servidores:
                #
                # aplica OR
                lista_servidores = lista_servidores | field_queryset
            else:
                #
                # OR nos próximos filtros
                lista_servidores = field_queryset
        #
        lista_servidores = lista_servidores.distinct()
    else:
        lista_servidores = servidores_manager.all()
    #
    return lista_servidores[num_ultima_posicao: (num_ultima_posicao + num_registros_a_retornar)]


@api_view(["GET"])
@authentication_classes((JWTAuthentication, TokenAuthentication))
@service_doc(
    "Obtém uma lista dinâmica de servidores de acordo com alguns critérios " "(exige o token do usuário requisitante).",
    response_serializer="api.serializers.ListaServidores",
    parameters=[
        ServiceDocParameter(name="pesquisa", description="Termo a pesquisar"),
        ServiceDocParameter(name="num_ultima_posicao", description="Posição do último registro carregado (padrão 0)", required=False),
        ServiceDocParameter(name="num_proximos_registros", description="Quantidade de próximos registros (padrão 10)", required=False),
    ],
)
def obtem_lista_servidores_dinamica(request):
    response = ListaServidores()
    #
    pesquisa = request.GET.get("pesquisa", None)
    num_ultima_posicao = int(request.GET.get("num_ultima_posicao", "0"))
    num_proximos_registros = int(request.GET.get("num_proximos_registros", "10"))
    #
    lista_servidores = _obtem_lista_servidores(pesquisa, num_ultima_posicao, num_proximos_registros)
    #
    lista_servidores_final = []
    for servidor in lista_servidores:
        pessoa = Profile()
        pessoa.set_profile_from_pessoa_fisica(servidor)
        #
        lista_servidores_final.append(pessoa)
    #
    response.quantidade = len(lista_servidores_final)
    response.servidores = [servidor.data for servidor in lista_servidores_final]
    #
    return Response(response.data)
    #


@api_view(["GET"])
@authentication_classes((JWTAuthentication, TokenAuthentication))
@service_doc(
    "Obtém estatísticas de servidores (exige o token do usuário requisitante).", response_serializer="api.serializers.EstatisticaServidores"
)
def obtem_estatisticas_servidores(request):
    response = EstatisticaServidores()
    response.quantidade_ativos = Servidor.objects.ativos().count()
    return Response(response.data)


@api_view(["GET"])
@authentication_classes((JWTAuthentication, TokenAuthentication))
@service_doc(
    "Obtém os contracheques disponíveis (apenas os meses) de um usuário qualquer " "(exige o token do usuário requisitante).",
    response_serializer="api.serializers.ContraChequeDisponivel",
)
def obtem_contracheques_disponiveis(request, matricula):
    if not request.user.eh_servidor:
        return Response({"detail": "Usuário não tem permissão de acesso a esse serviço."}, status=status.HTTP_403_FORBIDDEN)

    servidor = request.user.get_relacionamento()
    if not servidor.matricula == matricula:
        return Response({"detail": "Usuário não tem permissão de acesso a esse serviço."}, status=status.HTTP_403_FORBIDDEN)
    servidor_solicitado = Servidor.objects.filter(matricula=matricula)
    if not servidor_solicitado.exists():
        return Response({"detail": "Matrícula não encontrada."}, status=status.HTTP_404_NOT_FOUND)
    #
    response = ContraChequeDisponivel()
    contra_cheques = ContraCheque.objects.ativos().fita_espelho().filter(servidor=servidor_solicitado[0])
    meses_disponiveis = []
    for contra_cheque in contra_cheques:
        mesano = ContraChequeMesAno()
        mesano.mes = contra_cheque.mes
        mesano.ano = contra_cheque.ano.ano
        meses_disponiveis.append(mesano)
    #
    response.meses = [mes.data for mes in meses_disponiveis]
    #
    return Response(response.data)


@api_view(["GET"])
@authentication_classes((JWTAuthentication, TokenAuthentication))
@service_doc(
    "Obtém os detalhes de um contracheque de um usuário qualquer " "(exige o token do usuário requisitante).",
    response_serializer="api.serializers.ContraChequeDetalhe",
)
def obtem_contracheque(request, matricula, ano, mes):

    if not request.user.eh_servidor:
        return Response({"detail": "Usuário não tem permissão de acesso a esse serviço."}, status=status.HTTP_403_FORBIDDEN)

    servidor = request.user.get_relacionamento()
    servidor_solicitado = Servidor.objects.filter(matricula=matricula)
    #
    if not matricula == servidor.matricula:
        return Response({"detail": "Usuário não tem permissão de acesso a esse serviço."}, status=status.HTTP_403_FORBIDDEN)

    if not servidor_solicitado.exists():
        return Response({"detail": "Matrícula não encontrada"}, status=status.HTTP_404_NOT_FOUND)
    try:
        mes = int(mes)
        ano = int(ano)
    except Exception:
        return Response({"detail": "Mês/Ano inválido."}, status=status.HTTP_400_BAD_REQUEST)
    #
    contra_cheque = ContraCheque.objects.ativos().fita_espelho().filter(servidor=servidor_solicitado[0], mes=mes, ano__ano=ano)
    if contra_cheque.exists():
        contra_cheque = contra_cheque[0]
        response = ContraChequeDetalhe()
        #
        response.mes = mes
        response.ano = ano
        #
        # vantagens
        rendimentos = ContraChequeRubricaModel.objects.filter(contra_cheque=contra_cheque, tipo__nome="Rendimento")
        rubricas_vantagens = []
        total_vantagens = 0
        for rendimento in rendimentos:
            rubrica = ContraChequeRubrica()
            rubrica.descricao = rendimento.rubrica.nome
            rubrica.valor = f"{rendimento.valor}"
            total_vantagens += rendimento.valor
            #
            rubricas_vantagens.append(rubrica)
        #
        # desvantagens
        descontos = ContraChequeRubricaModel.objects.filter(contra_cheque=contra_cheque, tipo__nome="Desconto")
        rubricas_descontos = []
        total_descontos = 0
        for desconto in descontos:
            rubrica = ContraChequeRubrica()
            rubrica.descricao = desconto.rubrica.nome
            rubrica.valor = f"{desconto.valor}"
            total_descontos += desconto.valor
            #
            rubricas_descontos.append(rubrica)
        #
        response.vantagens = [vantagem.data for vantagem in rubricas_vantagens]
        response.descontos = [desconto.data for desconto in rubricas_descontos]
        #
        # totais
        response.total_vantagens = f"{total_vantagens}"
        response.total_descontos = f"{total_descontos}"
        response.total_liquido = f"{total_vantagens - total_descontos}"
        #
        return Response(response.data)
    else:
        return Response({"detail": "Contracheque não encontrado."}, status=status.HTTP_404_NOT_FOUND)


@api_view(["GET"])
@authentication_classes((JWTAuthentication, TokenAuthentication))
@service_doc("Obtém informações sobre os meus processos (exige o seu token).", response_serializer="api.serializers.MeusProcessos")
def meus_processos(request):
    try:
        response = MeusProcessos()
        #
        processos = []
        for processo in Processo.objects.filter(interessado_documento=request.user.get_profile().cpf):
            meu_processo = MeuProcesso()
            meu_processo.data_cadastro = processo.data_cadastro.strftime("%d/%m/%Y")
            meu_processo.assunto = processo.assunto
            meu_processo.numero_processo = processo.numero_processo
            meu_processo.setor_atual = processo.get_orgao_responsavel_atual() and str(processo.get_orgao_responsavel_atual()) or ""
            meu_processo.responsavel_atual = (
                processo.get_vinculo_responsavel_atual() and str(processo.get_vinculo_responsavel_atual()) or ""
            )
            meu_processo.status = processo.status
            processos.append(meu_processo)
        #
        response.meus_processos = [processo.data for processo in processos]
        #
        return Response(response.data)
    except Exception:
        return Response({"detail": "Processos não disponíveis."}, status=status.HTTP_404_NOT_FOUND)


# =========================== APIs REST =========================== #


class AlunosViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = AlunoSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["ano_letivo", "periodo_letivo", "situacao", "curso_campus", "polo"]
    lookup_field = "matricula"

    def get_queryset(self):
        return Aluno.ativos.all()


class CursoCampusViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = CursoCampusSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["ativo", "ano_letivo", "modalidade", "diretoria"]
    lookup_field = "codigo"

    def get_queryset(self):
        return CursoCampus.objects.all()


class AtualizacaoViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = ()
    permission_classes = [AllowAny]
    required_scopes = ["dados_publicos"]
    serializer_class = AtualizacaoSerializer

    def get_queryset(self):
        return Atualizacao.objects.all()


class SetorViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticated]
    serializer_class = SetorSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["nome", "sigla", "uo", "excluido", "uo", "areas_vinculacao"]
    queryset = Setor.objects.all()


class ServidoresViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticated]
    serializer_class = ServidorSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["matricula", "nome", "setor", "cargo_emprego"]
    lookup_field = "matricula"

    def get_queryset(self):
        return Servidor.objects.ativos()


class ProjetoPesquisaViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = ProjetoPesquisaSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["titulo", "resumo"]

    def get_queryset(self):
        return ProjetoPesquisa.objects.all()


class ProjetoPesquisaAreaConhecimentoViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = ProjetoPesquisaSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["titulo", "resumo"]

    def get_queryset(self):
        return ProjetoPesquisa.objects.filter(
            area_conhecimento__superior__codigo=self.kwargs["codigo_area"], area_conhecimento__codigo=self.kwargs["codigo_sub_area"]
        )


class ProjetoExtensaoViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = ProjetoExtensaoSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["titulo", "resumo"]

    def get_queryset(self):
        return ProjetoExtensao.objects.all()


class ProgramasViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = ProgramaSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["instituicao", "tipo"]

    def get_queryset(self):
        return Programa.objects.all()


class ParticipacaoViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = ParticipacaoSerializer

    def get_queryset(self):
        return Participacao.objects.all()


class InventarioViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = InventarioSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["numero"]

    def get_queryset(self):
        return Inventario.objects.all()


class ProcessoViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = ProcessoSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["interessado_nome", "assunto", "status", "uo", "data_cadastro"]

    def get_queryset(self):
        return Processo.objects.all().order_by("-data_cadastro")


class MeusProcessosViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    serializer_class = ProcessoSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["assunto", "status", "uo", "data_cadastro"]

    def get_queryset(self):
        return Processo.objects.filter(interessado_documento=self.request.user.get_profile().cpf).order_by("-data_cadastro")


class DetalheProcessoViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = DetalheProcessoSerializer

    def retrieve(self, request, pk=None):
        obj = get_object_or_404(Processo, pk=pk)
        serializer = DetalheProcessoSerializer(obj)
        return Response(serializer.data)


class ContratoViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = ContratoSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["numero", "contratada", "campi", "data_inicio"]

    def get_queryset(self):
        return Contrato.objects.all().order_by("-data_inicio")


class PlanoIndividualTrabalhoViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = PlanoIndividualTrabalhoSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["ano_letivo", "periodo_letivo"]

    def get_queryset(self):
        if "pit_rit" in settings.INSTALLED_APPS:
            from pit_rit.models import PlanoIndividualTrabalho

            return PlanoIndividualTrabalho.objects.filter(deferida=True)
        return []

    def retrieve(self, request, matricula=None):
        if "pit_rit" in settings.INSTALLED_APPS:
            from pit_rit.models import PlanoIndividualTrabalho

            qs = PlanoIndividualTrabalho.objects.filter(professor__vinculo__user__username=matricula).order_by(
                "ano_letivo", "periodo_letivo"
            )
            serializer = PlanoIndividualTrabalhoSerializer(qs, many=True)
            return Response(serializer.data)
        return None


class BannerViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, JWTAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticatedOrTokenHasScope]
    required_scopes = ["dados_publicos"]
    serializer_class = BannerSerializer
    filter_backends = [DjangoFilterBackend]
    filter_fields = ["tipo", "data_inicio", "data_termino"]

    def get_queryset(self):
        return Banner.objects.order_by("-data_inicio")


# Serviços criados para o SUAP Mobile


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def obtem_meus_dados_v2(request):
    """
    Obtém os dados do usuário logado.
    """
    obj = ProfileSerializer(request.user)
    return Response(obj.data)


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def obtem_meus_periodos_letivos_v2(request):
    """
    Obtém os períodos letivos do aluno logado.
    """
    get_object_or_404(Aluno, matricula=request.user.username)
    obj = PeriodoLetivoAtual.get_instance(request)

    data = []
    for ano_letivo, periodo_letivo in obj.get_periodos():
        data.append({"ano_letivo": ano_letivo, "periodo_letivo": periodo_letivo})

    return Response(data)


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def turmas_virtuais_v2(request, ano_letivo, periodo_letivo):
    """
    Obtém as turmas virtuais do aluno logado em um determinado período e ano letivo.
    """
    obj = get_object_or_404(Aluno, matricula=request.user.username)
    qs = obj.matriculaperiodo_set.filter(ano_letivo__ano=ano_letivo, periodo_letivo=periodo_letivo)
    if not qs.exists():
        raise NotFound()
    matricula_periodo = qs[0]
    matriculas_diario = matricula_periodo.matriculadiario_set.all()

    serializer = MatriculaPeriodoSerializer(matriculas_diario, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def turma_virtual_v2(request, pk):
    """
    Obtém os dados de um diário da turma virtual do aluno logado.
    """
    aluno = get_object_or_404(Aluno, matricula=request.user.username)
    qs = MatriculaDiario.objects.filter(diario__pk=pk, matricula_periodo__aluno=aluno).exclude(
        situacao__in=[MatriculaDiario.SITUACAO_TRANCADO, MatriculaDiario.SITUACAO_TRANSFERIDO, MatriculaDiario.SITUACAO_CANCELADO]
    )
    if qs.exists():
        obj = qs.first()
    else:
        raise NotFound()

    serializer = MatriculaDiarioSerializer(obj)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def minhas_avaliacoes_v2(request):
    """
    Obtém a lista das próximas avaliações do aluno logado.
    """
    aluno = get_object_or_404(Aluno, matricula=request.user.username)
    avaliacoes = aluno.get_avaliacoes()

    serializer = ItemConfiguracaoAvaliacaoSerializer(avaliacoes, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def meu_boletim_v2(request, ano_letivo, periodo_letivo):
    """
    Obtém as notas do aluno logado  em um determinado período e ano letivo.
    """
    aluno = get_object_or_404(Aluno, matricula=request.user.username)
    matricula_periodo = get_object_or_404(MatriculaPeriodo, aluno=aluno, ano_letivo__ano=ano_letivo, periodo_letivo=periodo_letivo)
    matriculas_diario = matricula_periodo.matriculadiario_set.all().order_by("diario__componente_curricular__componente__descricao")

    serializer = BoletimSerializer(matriculas_diario, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def obtem_meus_contracheques_v2(request):
    """
    Obtém a lista dos meses com contracheques disponíveis para o usuário logado.
    """
    obj = get_object_or_404(Servidor, matricula=request.user.username)
    qs = ContraCheque.objects.ativos().fita_espelho().filter(servidor=obj).order_by("-ano__ano", "-mes")
    serializer = ContraChequeAnoMesSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def obtem_detalhes_contracheque_v2(request, ano, mes):
    """
    Obtém o detalhamento de um determinado contracheque do usuário logado.
    """
    obj = get_object_or_404(Servidor, matricula=request.user.username)
    contracheque = get_object_or_404(ContraCheque, servidor=obj, ano__ano=ano, mes=mes, excluido=False, tipo_importacao=ContraCheque.IMPORTACAO_FITA_ESPELHO)
    serializer = ContraChequeSerializer(contracheque)

    if contracheque.pode_ver(request):
        return Response(serializer.data)
    else:
        return Response({})


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def obtem_frequencias_v2(request):
    """
    Obtém a lista das frequências no dia de hoje do usuário logado.
    """
    get_object_or_404(Servidor, matricula=request.user.username)
    vinculo = request.user.get_vinculo()
    setor = get_setor(request.user)

    if (vinculo.eh_servidor() or vinculo.eh_prestador()) and setor:
        hoje = datetime.now()
        total_tempo_semana = 0
        total_tempo_hoje = 0
        frequencias_hoje = Frequencia.objects.none()
        dict_response = dict()

        for dia in datas_entre(primeiro_dia_da_semana(hoje), hoje):
            frequencias_dia = Frequencia.get_frequencias_por_data(vinculo, dia)
            if dia == hoje:
                frequencias_hoje = frequencias_dia
                if frequencias_hoje.exists():
                    tempo = 0
                    for par in agrupar_em_pares(frequencias_hoje.values_list("horario", flat=True)):
                        if len(par) == 2:
                            delta = par[1] - par[0]
                            segundos = delta.seconds
                        else:
                            segundos = 0
                        tempo += segundos
                    if frequencias_hoje.latest("horario").acao == "E":
                        momento_da_entrada = frequencias_hoje.latest("horario").horario
                        momento_agora = datetime.now()
                        while momento_agora < momento_da_entrada:
                            momento_agora = datetime.now()
                        delta = momento_agora - momento_da_entrada
                        segundos = delta.seconds
                        tempo += segundos
                    total_tempo_hoje = time.strftime("%H:%M:%S", time.gmtime(tempo))
                    total_tempo_semana += tempo
            else:
                total_tempo_semana += Frequencia.get_tempo_entre_frequencias(frequencias_dia)

        dict_response["frequencias_hoje"] = FrequenciasHojeSerializer(frequencias_hoje, many=True).data
        dict_response["total_tempo_hoje"] = total_tempo_hoje
        dict_response["total_tempo_semana"] = "%(h)sh %(m)smin %(s)sseg" % formata_segundos(total_tempo_semana)
        return Response(dict_response)
    else:
        return Response({})


@api_view(["POST"])
@permission_classes([AllowAny])
def obtem_token_acesso_responsaveis(request):
    """
    Retorna o token de um determinado aluno a partir da sua matrícula e a sua chave de acesso do resposável.
    """
    jwt_payload_handler = jwt_settings.JWT_PAYLOAD_HANDLER
    jwt_encode_handler = jwt_settings.JWT_ENCODE_HANDLER
    try:
        matricula = request.data.get("matricula")
    except Exception:
        return Response({"detail": "Erro ao tentar recuperar número da matrícula."}, status=status.HTTP_400_BAD_REQUEST)
    if not exigir_captcha(matricula):
        aluno = get_object_or_404(Aluno, matricula=matricula)

        if aluno.get_chave_responsavel() != request.data.get("chave"):
            user = User.objects.filter(username=matricula).first()
            if user:
                user.login_attempts += 1
                user.save()
            return Response({"detail": "Credenciais inválidas"}, status=status.HTTP_401_UNAUTHORIZED)

        payload = jwt_payload_handler(aluno.pessoa_fisica.user)
        token = jwt_encode_handler(payload)

        return Response({"token": token})
    else:
        return response_captcha()


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def obtem_historico_funcional_v2(request):
    """
    Obtém a timeline do Histórico Funcional do Servidor logado.
    """
    obj = get_object_or_404(Servidor, matricula=request.user.username)
    timeline = PCA.montar_timeline(obj.pca_set.all().order_by("data_entrada_pca"))
    servidor_tempo_servico_na_instituicao_via_pca = obj.tempo_servico_na_instituicao_via_pca()
    servidor_tempo_servico_na_instituicao_via_pca_ficto = obj.tempo_servico_na_instituicao_via_pca(ficto=True)
    lista = []

    # Tratamento necessário para converter o retorno da timeline de dict para lista.
    for k, v in list(timeline.items()):
        v.update({"data": k})
        lista.append(v)

    lista.append(
        {
            "css": "default",
            "data": obj.data_fim_servico_na_instituicao if obj.data_fim_servico_na_instituicao else "Hoje",
            "eventos": [
                {
                    "descricao": """<h4>Tempo de Serviço</h4>
                <dl>
                    <dt>Tempo Real:</dt>
                    <dd>{}</dd>
                    <dt>Tempo Ficto:</dt>
                    <dd>{}</dd>
                </dl>
            """.format(
                        format_(servidor_tempo_servico_na_instituicao_via_pca), format_(servidor_tempo_servico_na_instituicao_via_pca_ficto)
                    ),
                    "css": "default",
                }
            ],
        }
    )

    return Response(lista)


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def obtem_ferias_v2(request):
    """
    Obtém a lista de férias do Servidor logado.
    """
    obj = get_object_or_404(Servidor, matricula=request.user.username)
    if "ferias" in settings.INSTALLED_APPS:
        from ferias.models import Ferias

        ferias = Ferias.objects.filter(servidor=obj).order_by("ano")
        serializer = FeriasSerializer(ferias, many=True)
        return Response(serializer.data)
    else:
        return Response({})


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def obtem_ocorrencias_afastamentos_servidor_v2(request):
    """
    Obtém a lista de ocorrências e afastamentos do Servidor logado.
    """
    obj = get_object_or_404(Servidor, matricula=request.user.username)

    servidor_ocorrencias = (
        ServidorOcorrencia.objects.filter(servidor=obj).exclude(ocorrencia__grupo_ocorrencia__nome="AFASTAMENTO").order_by("data")
    )
    servidor_afastamentos = ServidorAfastamento.objects.filter(servidor=obj, cancelado=False).order_by("data_inicio")
    serializer_ocorrencias = ServidorOcorrenciaSerializer(servidor_ocorrencias, many=True)
    serializer_afastamentos = ServidorAfastamentoSerializer(servidor_afastamentos, many=True)

    dict_response = {"ocorrencias": serializer_ocorrencias.data, "afastamentos": serializer_afastamentos.data}
    return Response(dict_response)


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def obtem_participacoes_projeto_v2(request):
    """
    Obtém a lista de participações em projeto do Servidor logado.
    """
    obj = get_object_or_404(Servidor, matricula=request.user.username)

    participacoes_extensao = PartExtensao.objects.filter(vinculo_pessoa=obj.get_vinculo(), ativo=True, projeto__aprovado=True)
    participacoes_pesquisa = PartPesquisa.objects.filter(vinculo_pessoa=obj.get_vinculo(), ativo=True, projeto__aprovado=True)

    serializer_extensao = ParticipacaoProjetoExtensaoSerializer(participacoes_extensao, many=True)
    serializer_pesquisa = ParticipacaoProjetoPesquisaSerializer(participacoes_pesquisa, many=True)

    dict_response = {"participacoes_extensao": serializer_extensao.data, "participacoes_pesquisa": serializer_pesquisa.data}
    return Response(dict_response)


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def meus_diarios_v2(request, ano_letivo, periodo_letivo):
    """
    Obtém os diários ministrados em um determinado período e ano letivo pelo professor logado.
    """
    obj = get_object_or_404(Professor, vinculo__user__username=request.user.username)
    ids_diarios = obj.professordiario_set.filter(diario__ano_letivo__ano=ano_letivo, diario__periodo_letivo=periodo_letivo).values_list(
        "diario__pk", flat=True
    )
    diarios = Diario.objects.filter(pk__in=ids_diarios)

    serializer = DiarioSerializer(diarios, many=True)
    return Response(serializer.data)
    return Response([])


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def meu_diario_v2(request, pk):
    """
    Obtém um diário ministrado pelo professor logado de acordo com o id informado.
    """
    obj = get_object_or_404(Professor, vinculo__user__username=request.user.username)
    id_diario = obj.professordiario_set.filter(diario__pk=pk).values_list("diario__pk", flat=True)
    if id_diario:
        diario = Diario.objects.get(pk=id_diario)
        serializer = DiarioSerializer(diario, many=False)
        return Response(serializer.data)
    else:
        raise NotFound()


@api_view(["GET"])
@authentication_classes((OAuth2Authentication, JWTAuthentication, SessionAuthentication))
def obtem_banners_ativos_v2(request):
    """
    Obtém a lista de banners ativos.
    """
    hoje = datetime.now()
    qs = Banner.objects.filter(data_inicio__lte=hoje, data_termino__gte=hoje)
    serializer = BannerSerializer(qs, many=True)
    return Response(serializer.data)


@api_view(["GET"])
@authentication_classes((JWTAuthentication, SessionAuthentication))
def alunos_carometro_v2(request, sigla_campus, ano_letivo):
    """
    Obtém a lista de alunos ativos do campus e ano letivo indicado.
    """
    ano = get_object_or_404(Ano, ano=ano_letivo)
    campus = get_object_or_404(UnidadeOrganizacional, sigla__iexact=sigla_campus)

    qs = Aluno.ativos.filter(ano_letivo=ano, curso_campus__diretoria__setor__uo=campus)
    serializer = AlunoCarometro(qs, many=True)
    return Response(serializer.data)


@api_view(["GET"])
def eu(request):
    if request.auth and not request.auth.allow_scopes(["identificacao", "email"]):
        return Response(status=status.HTTP_401_UNAUTHORIZED)
    user = request.user
    relacionamento = user.get_relacionamento()
    campus = relacionamento.campus
    data = {
        "identificacao": user.username,
        "nome": user.get_full_name(),
        "email": user.email,
        "email_secundario": relacionamento.pessoa_fisica.email_secundario,
        "email_google_classroom": getattr(relacionamento, "email_google_classroom", None),
        "email_academico": getattr(relacionamento, "email_academico", None),
        "campus": campus and str(campus) or None,
    }
    if request.auth and request.auth.allow_scopes(["documentos_pessoais"]):
        data["cpf"] = relacionamento.pessoa_fisica.cpf
        data["data_de_nascimento"] = relacionamento.pessoa_fisica.nascimento_data
        data["sexo"] = relacionamento.pessoa_fisica.sexo
    return Response(data)


@api_view(["GET"])
def meus_grupos(request):
    return Response(list(request.user.groups.values_list("name", flat=True)))


class ApplicationViewSet(viewsets.ModelViewSet):

    authentication_classes = (OAuth2Authentication, TokenAuthentication, SessionAuthentication)
    permission_classes = [IsAuthenticated]
    serializer_class = ApplicationSerializer

    def get_queryset(self):
        # Restringe queryset às aplicações criadas por request.user
        return Application.objects.filter(user=self.request.user)


################################################################################


class CampiViewSet(viewsets.ReadOnlyModelViewSet):
    authentication_classes = (OAuth2Authentication, TokenAuthentication)
    permission_classes = [IsAuthenticated]
    serializer_class = UnidadeOrganizacionalSerializer

    def get_queryset(self):
        return UnidadeOrganizacional.objects.suap().all()


@api_view(["GET"])
@permission_classes([TokenFromTrustedApp])
def list_servidores(request):
    queryset = (
        Servidor.objects.all()
        .order_by("nome")
        .values_list(
            "id",
            "cpf",
            "matricula",
            "nome",
            "nascimento_data",
            "foto",
            "setor__sigla",
            "setor__uo__sigla",
            "cargo_emprego__nome",
            "cargo_emprego__grupo_cargo_emprego__categoria",
            "excluido",
            "situacao__nome_siape",
            "email",
            "email_secundario",
            "pagto_banco__codigo",
            "pagto_banco__nome",
            "pagto_agencia",
            "pagto_ccor",
            "pagto_ccor_tipo",
        )
    )
    if "campus" in request.GET:
        queryset = queryset.filter(setor__uo__sigla=request.GET["campus"])
    if "matricula" in request.GET:
        queryset = queryset.filter(matricula=request.GET["matricula"])
    serializer_fields = [
        "id",
        "cpf",
        "matricula",
        "nome",
        "data_de_nascimento",
        "foto",
        "setor",
        "campus",
        "cargo",
        "categoria_do_cargo",
        "excluido",
        "situacao",
        "email",
        "email_secundario",
        "banco_codigo",
        "banco_nome",
        "banco_conta_agencia",
        "banco_conta_numero",
        "banco_conta_operacao",
    ]

    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    paginator = pagination_class()
    page = paginator.paginate_queryset(queryset, request)
    ids = [i[0] for i in page]

    cache_enderecos = dict()
    for pe in PessoaEndereco.objects.filter(pessoa__id__in=ids).values_list(
        "pessoa", "logradouro", "numero", "complemento", "bairro", "cep", "municipio__nome"
    ):
        pessoa_id = pe[0]
        endereco = ", ".join([i for i in pe[1:] if i])
        cache_enderecos[pessoa_id] = endereco

    cache_telefones = dict()
    for pessoa_id, telefone in PessoaTelefone.objects.filter(id__in=ids).values_list("pessoa", "numero"):
        cache_telefones[pessoa_id] = telefone

    def _build_obj(obj):
        obj_as_dict = dict(zip(serializer_fields, obj))
        obj_as_dict["ativo"] = not obj_as_dict["excluido"]
        obj_as_dict["endereco"] = cache_enderecos.get(obj_as_dict["id"]) or ""
        obj_as_dict["telefone"] = cache_telefones.get(obj_as_dict["id"]) or ""
        return obj_as_dict

    obj_list = [_build_obj(obj) for obj in page]
    serializer = ServidorSerializer2(obj_list, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
@permission_classes([TokenFromTrustedApp])
@protected_resource(scopes=["contracheques"])
def list_contracheques(request):

    ano = int(request.GET.get("ano", 0))
    mes = int(request.GET.get("mes", 0))

    queryset = (
        ContraCheque.objects.ativos()
        .fita_espelho()
        .filter(ano__ano=ano, mes=mes, pensionista__isnull=True)
        .values("id", "ano__ano", "mes", "servidor__matricula", "bruto")
        .order_by("servidor__nome")
    )
    pagination_class = api_settings.DEFAULT_PAGINATION_CLASS
    paginator = pagination_class()
    page = paginator.paginate_queryset(queryset, request)
    cc_ids = [i["id"] for i in page]
    cache_ccr = dict()
    for ccr in (
        ContraChequeRubricaModel.objects.filter(contra_cheque__id__in=cc_ids)
        .select_related("rubrica", "tipo")
        .values("contra_cheque", "valor", "prazo", "rubrica__codigo", "rubrica__nome", "tipo__codigo", "tipo__nome")
    ):
        cache_ccr.setdefault(ccr["contra_cheque"], []).append(ccr)

    def _build_obj(obj):
        return dict(
            matricula=obj["servidor__matricula"],
            ano=obj["ano__ano"],
            mes=obj["mes"],
            valor_bruto=obj["bruto"] or 0,
            ccr_list=cache_ccr.get(obj["id"], []),
        )  # evitar None

    obj_list = [_build_obj(obj) for obj in page]
    serializer = ContraChequeSerializer2(obj_list, many=True)
    return paginator.get_paginated_response(serializer.data)


@api_view(["GET"])
@permission_classes([TokenFromTrustedApp])
@protected_resource(scopes=["integra"])
def list_servidores_integra(request):
    fields = [
        "cpf", "nome", "sexo", "excluido", "email_institucional", "setor__uo__id",
        "matricula", "situacao__nome", "cargo_emprego__grupo_cargo_emprego__categoria",
        "setor__uo__nome",
    ]
    queryset = Servidor.objects.ativos_permanentes().only(*fields).values(*fields)

    def _build_obj(obj):
        return dict(
            cpf=obj["cpf"],
            nome=obj["nome"],
            siape=obj["matricula"],
            campusId=obj["setor__uo__id"],
            campusNome=obj["setor__uo__nome"],
            email=obj["email_institucional"],
            tipoUsuario=obj["cargo_emprego__grupo_cargo_emprego__categoria"],
            sexo=obj["sexo"],
            situacao=obj["situacao__nome"],
            excluido=obj["excluido"],
        )
    obj_list = [_build_obj(obj) for obj in queryset]
    serializer = ServidorSerializer3(obj_list, many=True)
    from rest_framework.response import Response
    return Response(serializer.data)
