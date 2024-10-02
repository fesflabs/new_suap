# -*- coding: utf-8 -*-
import datetime

from django.contrib.auth.decorators import permission_required
from django.core.exceptions import ObjectDoesNotExist
from rest_framework import status
from rest_framework.authentication import TokenAuthentication, SessionAuthentication
from rest_framework.decorators import api_view, authentication_classes
from rest_framework.response import Response

from djtools.utils import normalizar_nome_proprio
from edu.models import Turma, Diario, Aluno, CursoCampus, Polo, Matriz, MatrizCurso, ComponenteCurricular, \
    ProfessorDiario
from rh.models import UnidadeOrganizacional, Servidor

# =========================== INTEGRAÇÃO COM O SIABI - BIBLIOTECA =========================== #

'''
* DADOS DO CAMPI
curl -X GET http://localhost:8000/rh/api/campi/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C'

* DADOS DOS SERVIDORES:
curl -X GET http://localhost:8000/rh/api/servidores/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C'
curl -X GET http://localhost:8000/rh/api/servidores/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C' -d 'sigla_campus=RE'
curl -X GET http://localhost:8000/rh/api/servidores/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C' -d 'matricula=1799479'

* DADOS DOS CURSOS
curl -X GET http://localhost:8000/edu/api/listar_cursos/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C'
curl -X GET http://localhost:8000/edu/api/listar_cursos/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C' -d 'sigla_campus=AP'

* DADOS DAS MATRIZES
curl -X GET http://localhost:8000/edu/api/listar_matrizes/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C'
curl -X GET http://localhost:8000/edu/api/listar_matrizes/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C' -d 'sigla_campus=AP'

* DADOS DO ALUNO
curl -X GET http://localhost:8000/edu/api/dados_aluno/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C' -d 'matricula=20121081080237'

'''


@api_view(['GET'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def listar_cursos(request):
    """
        Exemplo de como executar a função através da linha de comando:
        curl -X GET http://localhost:8000/edu/api/listar_cursos/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C' -d 'sigla_campus=AP'
    """
    retorno = []
    try:
        sigla_campus = request.data.get('sigla_campus')
        periodo_letivo = request.data.get('periodo_letivo')
        ano_letivo = request.data.get('ano_letivo')
        codigo = request.GET.get('codigo')
        qs = CursoCampus.objects.all()
        if sigla_campus:
            qs = qs.filter(diretoria__setor__uo__sigla=sigla_campus)
        if periodo_letivo:
            qs = qs.filter(turma__periodo_letivo=periodo_letivo)
        if ano_letivo:
            qs = qs.filter(turma__ano_letivo__ano=ano_letivo)
        if codigo:
            qs = qs.filter(codigo=codigo)

        for curso_campus in qs:
            dict_curso = dict(
                id=curso_campus.pk,
                codigo=curso_campus.codigo or '',
                descricao=curso_campus.descricao_historico or '',
                sigla_campus=curso_campus.diretoria.setor.uo.sigla,
                modalidade=curso_campus.modalidade_id and curso_campus.modalidade.descricao or None,
                natureza_participacao=curso_campus.natureza_participacao and curso_campus.natureza_participacao.descricao or None
            )
            retorno.append(dict_curso)
    except BaseException as e:
        retorno.append(dict(erro=str(e)))
        return Response({"erro": str(e)})
    return Response(retorno)


@api_view(['GET'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def listar_matrizes(request):
    """
        Exemplo de como executar a função através da linha de comando:
        curl -X GET http://localhost:8000/edu/api/listar_matrizes/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C' -d 'sigla_campus=AP'
    """
    retorno = []
    try:
        qs = Matriz.objects.all()
        sigla_campus = request.data.get('sigla_campus')
        if sigla_campus:
            qs = qs.filter(matrizcurso__curso_campus__diretoria__setor__uo__sigla=sigla_campus)
        for matriz in qs:
            componentes_curriculares = []
            for cc in matriz.componentecurricular_set.all():
                componente_curricular = dict()
                componente_curricular['id'] = cc.pk
                componente_curricular['descricao'] = cc.componente.descricao
                componente_curricular['descricao_historico'] = cc.componente.descricao_historico
                componente_curricular['sigla'] = cc.componente.sigla
                componente_curricular['periodo'] = cc.periodo_letivo
                componente_curricular['tipo'] = cc.tipo
                componente_curricular['optativo'] = cc.optativo
                componente_curricular['qtd_avaliacoes'] = cc.qtd_avaliacoes
                componentes_curriculares.append(componente_curricular)
            dict_curso = dict(id=matriz.pk, descricao=matriz.descricao, componentes_curriculares=componentes_curriculares)
            retorno.append(dict_curso)
    except BaseException as e:
        return Response({"erro": str(e)})
    return Response(retorno)


@api_view(['GET'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def listar_vinculos_matrizes_cursos(request):
    """
        Exemplo de como executar a função através da linha de comando:
        curl -X GET http://localhost:8000/edu/api/listar_vinculos_matrizes_cursos/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C'
    """
    retorno = []
    try:
        qs = MatrizCurso.objects.all()
        for matriz_curso in qs:
            vinculo = dict(matriz=matriz_curso.matriz.pk, curso=matriz_curso.curso_campus.id)
            retorno.append(vinculo)
    except BaseException as e:
        return Response({"erro": str(e)})
    return Response(retorno)


@api_view(['GET', 'POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def dados_servidor(request):
    matricula = request.GET.get('matricula') or request.POST.get('matricula')
    servidor = Servidor.objects.filter(matricula=matricula).values(
        'matricula', 'nome', 'email', 'foto', 'setor__uo__sigla'
    ).first()
    if not servidor:
        return Response({"erro": "Servidor não encontrado com a matrícula {}".format(matricula)}, status=status.HTTP_404_NOT_FOUND)
    return Response(
        dict(matricula=servidor['matricula'], nome=servidor['nome'], campus=servidor['setor__uo__sigla'], email=servidor['email'], foto=servidor['foto'])
    )


@api_view(['GET', 'POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def dados_aluno(request):
    """
    Retorna os dados de um aluno com a matrícula específica e é utilizado pelo SIABI.

        curl -X GET http://localhost:8000/edu/api/dados_aluno/?matricula=20121081080237 -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C'
    """
    matricula = request.GET.get('matricula') or request.POST.get('matricula')
    ano_conclusao = request.GET.get('ano_conclusao') or request.POST.get('ano_conclusao')
    codigo_curso = request.GET.get('codigo_curso') or request.POST.get('codigo_curso')
    if matricula:
        try:
            aluno = Aluno.objects.get(matricula=matricula)
            return Response(aluno.get_dados_siabi())
        except ObjectDoesNotExist:
            return Response({"erro": "Aluno não encontrado com a matrícula {}".format(matricula)}, status=status.HTTP_404_NOT_FOUND)
    else:
        alunos = []
        for aluno in Aluno.objects.filter(ano_conclusao=ano_conclusao, curso_campus__codigo=codigo_curso):
            alunos.append(aluno.get_dados_siabi())
        return Response(alunos)
    return Response({"erro": "Matrícula não informada."}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def listar_alunos_atualizados(request):
    '''
        Retorna uma lista de alunos que tiveram atualizações nos dados.
        Exemplo de como executar a função através da linha de comando:
        curl -X POST http://localhost:8000/edu/api/listar_alunos_atualizados/ -H 'Authorization: Token 8facb29faca05b28ab783350d94bf35C' -d 'data=01/01/2015'
    '''
    try:
        msg = "Nao existe alunos adicionados/atualizados apos esta data. Formato da data deve ser 'dd/mm/yyy'"

        data_array = request.data.get('data').split("/")
        data = datetime.date(int(data_array[2]), int(data_array[1]), int(data_array[0]))
        alunos_qs = Aluno.objects.filter(alterado_em__gte=data)
        if alunos_qs.exists():
            alunos = []
            for aluno in alunos_qs[0:1000]:
                alunos.append(aluno.get_dados_siabi())
            return Response(alunos)
        else:
            return Response({"erro": msg})
    except BaseException as e:
        return Response({"erro": str(e)})


# =========================== INTEGRAÇÃO COM O MOODLE - EAD =========================== #


@api_view(['POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def listar_cursos_ead(request):
    """
        Retorna os dados de um curso ou de todos os cursos de um ano e período letivo específicos.
        Exemplo de como executar a função através da linha de comando:
        curl -X POST http://localhost:8000/edu/api/listar_cursos_ead/ -H 'Authorization: Token <token>' -d 'id_campus=1&ano_letivo=2015&periodo_letivo=1'
    """
    retorno = dict()
    try:
        id_campus = request.data.get('id_campus')
        periodo_letivo = request.data.get('periodo_letivo')
        ano_letivo = request.data.get('ano_letivo')

        if ano_letivo and periodo_letivo and id_campus:
            qs_curso = CursoCampus.objects.filter(turma__ano_letivo__ano=ano_letivo, turma__periodo_letivo=periodo_letivo, diretoria__setor__uo__id=id_campus)
        else:
            retorno.update(erro='Parametros inválidos.')
            return Response(retorno)
        if qs_curso.exists():
            for curso in qs_curso:
                retorno.update({str(curso.id): serialize(curso)})
    except BaseException as e:
        retorno.update(erro=str(e))
    return Response(retorno)


@api_view(['POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def listar_turmas_ead(request):
    """
        Retorna os dados de uma turma ou de todas as turmas de um curso/polo de um ano e período letivo específicos.
        Exemplo de como executar a função através da linha de comando:
        curl -X POST http://localhost:8000/edu/api/listar_turmas_ead/ -H 'Authorization: Token <token>' -d 'id_curso=638&ano_letivo=2015&periodo_letivo=1'
    """
    retorno = dict()
    try:
        id_curso = request.data.get('id_curso')
        ano_letivo = request.data.get('ano_letivo')
        periodo_letivo = request.data.get('periodo_letivo')

        if id_curso and ano_letivo and periodo_letivo:
            qs_turma = Turma.objects.filter(ano_letivo__ano=ano_letivo, periodo_letivo=periodo_letivo, curso_campus__id=id_curso)
        else:
            retorno.update(erro='Parametros inválidos.')
            return Response(retorno)

        if qs_turma.exists():
            for turma in qs_turma:
                retorno.update({str(turma.id): serialize(turma)})
    except BaseException as e:
        retorno.update(erro=str(e))
    return Response(retorno)


@api_view(['POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def listar_diarios_ead(request):
    """
        Retorna os dados de um diário ou de todos os diários de uma turma/componente_curricular de um ano e período letivo específicos.
        Exemplo de como executar a função através da linha de comando:
        curl -X POST http://localhost:8000/edu/api/listar_diarios_ead/ -H 'Authorization: Token <token>' -d 'id_turma=1119'
    """
    retorno = dict()
    try:
        id_turma = request.data.get('id_turma')

        if id_turma:
            qs_diario = Diario.objects.filter(turma__id=id_turma)
        else:
            retorno.update(erro='Parametros inválidos.')
            return Response(retorno)

        if qs_diario.exists():
            for diario in qs_diario:
                retorno.update({str(diario.pk): serialize(diario)})
    except BaseException as e:
        retorno.update(erro=str(e))
    return Response(retorno)


@api_view(['POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def listar_professores_ead(request):
    """
        Retorna os dados dos professores de um diário ou de todos os diários de uma turma/componente_curricular/idprofessor de um ano e período letivo específicos
        Exemplo de como executar a função através da linha de comando:
        curl -X POST http://localhost:8000/edu/api/listar_professores_ead/ -H 'Authorization: Token <token>' -d 'id_diario=45'
    """
    retorno = dict()
    try:
        id_diario = request.data.get('id_diario')

        if id_diario:
            diario = Diario.objects.get(pk=id_diario)
        else:
            retorno.update(erro='Parametros inválidos.')
            return Response(retorno)

        dict_professores = dict()
        for professor_diario in diario.professordiario_set.all():
            dict_professores.update(
                {
                    str(professor_diario.professor.id): serialize(professor_diario)
                }
            )
        retorno.update(dict_professores)
    except BaseException as e:
        retorno.update(erro=str(e))
    return Response(retorno)


@api_view(['POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def listar_alunos_ead(request):
    """
        Retorna os dados dos alunos de um diário ou de todos os diários de uma turma/componente_curricular/matricula de um ano e período letivo específicos.
        Exemplo de como executar a função através da linha de comando:
        curl -X POST http://localhost:8000/edu/api/listar_alunos_ead/ -H 'Authorization: Token <token>' -d 'id_diario=45'
    """
    retorno = dict()
    try:
        id_diario = request.data.get('id_diario') or 0
        diario = Diario.objects.filter(pk=id_diario)
        if id_diario and diario.exists():
            diario = diario[0]
        else:
            retorno.update(erro='Parametros inválidos.')
            return Response(retorno)

        dict_alunos = dict()
        for matricula_diario in diario.matriculadiario_set.all():
            aluno = matricula_diario.matricula_periodo.aluno
            dict_alunos.update(
                {
                    str(aluno.id): serialize(aluno)
                }
            )
        retorno.update(dict_alunos)
    except BaseException as e:
        retorno.update(erro=str(e))
    return Response(retorno)


@api_view(['POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def listar_polos_ead(request):
    """
        Retorna todos os polos disponíveis.
        Exemplo de como executar a função através da linha de comando:
        curl -X POST http://localhost:8000/edu/api/listar_polos_ead/ -H 'Authorization: Token <token>'
    """
    retorno = dict()
    try:
        qs_polos = Polo.objects.all()
        if qs_polos.exists():
            for polo in qs_polos:
                retorno.update({str(polo.id): serialize(polo)})
    except BaseException as e:
        retorno.update(erro=str(e))
    return Response(retorno)


@api_view(['POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def listar_campus_ead(request):
    """
        Retorna todos os polos disponíveis.
        Exemplo de como executar a função através da linha de comando:
        curl -X POST http://localhost:8000/edu/api/listar_campus_ead/ -H 'Authorization: Token <token>'
    """
    retorno = dict()
    try:
        qs_campus = UnidadeOrganizacional.objects.suap().all()
        if qs_campus.exists():
            for campus in qs_campus:
                retorno.update({str(campus.id): serialize(campus)})
    except BaseException as e:
        retorno.update(erro=str(e))
    return Response(retorno)


@api_view(['POST'])
@authentication_classes((TokenAuthentication, SessionAuthentication))
@permission_required('edu.pode_sincronizar_dados')
def listar_componentes_curriculares_ead(request):
    """
        Retorna todos os componentes curriculares disponíveis para um curso específico.
        Exemplo de como executar a função através da linha de comando:
        curl -X POST http://localhost:8000/edu/api/listar_componentes_curriculares_ead/ -H 'Authorization: Token <token>' -d 'id_curso=873'
    """
    retorno = dict()
    try:
        id_curso = request.data.get('id_curso')
        qs_curso = CursoCampus.objects.filter(pk=id_curso)

        if qs_curso.exists():
            for curso in qs_curso:
                for matriz_curso in curso.matrizcurso_set.all():
                    componentes_curriculares = matriz_curso.matriz.componentecurricular_set.all()
                    for componente_curricular in componentes_curriculares:
                        retorno.update({str(componente_curricular.id): serialize(componente_curricular)})
    except BaseException as e:
        retorno.update(erro=str(e))
    return Response(retorno)


def serialize(obj, add_id=False):
    dados = dict()
    if obj and add_id:
        dados.update(id=obj.id)
    if isinstance(obj, UnidadeOrganizacional):
        dados['descricao'] = obj.nome
        dados['sigla'] = obj.sigla
    elif isinstance(obj, ComponenteCurricular):
        dados['descricao'] = obj.componente.descricao
        dados['descricao_historico'] = obj.componente.descricao_historico
        dados['sigla'] = obj.componente.sigla
        dados['periodo'] = obj.periodo_letivo
        dados['tipo'] = obj.tipo
        dados['optativo'] = obj.optativo
        dados['qtd_avaliacoes'] = obj.qtd_avaliacoes
    elif isinstance(obj, Polo):
        dados['descricao'] = obj.descricao
    elif isinstance(obj, Aluno):
        dados.update(
            matricula=obj.matricula or "",
            nome=normalizar_nome_proprio(obj.pessoa_fisica.nome) or "",
            email=obj.pessoa_fisica.email or "",
            email_secundario=obj.pessoa_fisica.email_secundario or "",
            situacao=obj.pessoa_fisica.user and obj.pessoa_fisica.user.is_active and "ativo" or "inativo",
            polo=obj.polo_id,
        )
    elif isinstance(obj, ProfessorDiario):
        dados.update(
            nome=normalizar_nome_proprio(obj.professor.vinculo.pessoa.nome) or "",
            email=obj.professor.vinculo.pessoa.email or "",
            email_secundario=obj.professor.vinculo.pessoa.email_secundario or "",
            tipo=obj.tipo.descricao or "",
            login=obj.professor.vinculo.user.username,
            status=obj.professor.vinculo.user.is_active and "ativo" or "inativo",
        )
    elif isinstance(obj, Diario):
        componente = obj.componente_curricular.componente
        dados.update(
            situacao=obj.get_situacao_display() or "",
            descricao=componente.descricao or "",
            descricao_historico=componente.descricao_historico or "",
            sigla=componente.sigla or "",
        )
    elif isinstance(obj, Turma):
        dados.update(codigo=obj.codigo or "")
    elif isinstance(obj, CursoCampus):
        dados.update(codigo=obj.codigo or "", nome=obj.descricao_historico or "", descricao=obj.descricao or "")
    return dados
