# -*- coding: utf-8 -*-


from behave import given  # NOQA
from comum.models import Ano
from edu.models import (
    Turno,
    Aluno,
    SituacaoMatricula,
    Matriz,
    CursoCampus,
    Diretoria,
    Professor,
    Modalidade,
    EstruturaCurso,
    MatriculaPeriodo,
    SituacaoMatriculaPeriodo,
    Estado,
    Cidade,
)
from estagios.models import TipoRemuneracao
from rh.models import Setor, PessoaJuridica, Servidor
from datetime import datetime, date


@given('os dados básicos para os estágios')
def step_dados_basicos_estagios(context):
    Turno.objects.get_or_create(id='6', descricao='Diurno')
    Turno.objects.get_or_create(id='1', descricao='Noturno')
    ano = Ano.objects.get_or_create(ano=str(datetime.now().year))[0]
    situacao = SituacaoMatricula.objects.get_or_create(descricao='Matriculado', ativo=True)[0]

    diretoria = Diretoria.objects.get_or_create(setor=Setor.objects.get(sigla='DIAC/CEN'))[0]

    modalidade = Modalidade.objects.get_or_create(descricao='Engenharia', id=Modalidade.ENGENHARIA)[0]
    estrutura = EstruturaCurso.objects.get_or_create(
        descricao='Estrutura', ativo=True, tipo_avaliacao=EstruturaCurso.TIPO_AVALIACAO_SERIADO, criterio_avaliacao=EstruturaCurso.CRITERIO_AVALIACAO_NOTA
    )[0]

    curso = CursoCampus.objects.get_or_create(
        descricao='Curso',
        descricao_historico='Curso',
        ano_letivo=ano,
        periodo_letivo=1,
        data_inicio=date.today(),
        ativo=True,
        codigo='0981',
        modalidade=modalidade,
        # turno=turno,
        # area=area.pk,
        # eixo=eixo.pk,
        # area_capes=area_capes.pk,
        # periodicidade=CursoCampus.PERIODICIDADE_LIVRE,
        diretoria=diretoria,
        emite_diploma=True,
    )[0]

    matriz = Matriz.objects.get_or_create(
        descricao='Matriz',
        ano_criacao=ano,
        periodo_criacao=1,
        data_inicio=datetime.now(),
        data_fim=None,
        ativo=True,
        estrutura=estrutura,
        qtd_periodos_letivos=3,
        ch_componentes_obrigatorios=20,
        ch_componentes_optativos=0,
        ch_componentes_eletivos=0,
        ch_seminarios=0,
        ch_componentes_tcc=10,
        ch_atividades_complementares=0,
        ch_pratica_profissional=0,
        ch_atividades_aprofundamento=0,
        ch_atividades_extensao=0,
        ch_pratica_como_componente=0,
        ch_visita_tecnica=0,
    )[0]

    aluno = Aluno.objects.filter(matricula='20191101011021')
    if aluno.exists():
        aluno = aluno[0]
        aluno.ano_letivo = ano
        aluno.periodo_letivo = 1
        aluno.situacao = situacao
        aluno.ano_let_prev_conclusao = datetime.now().year
        aluno.matriz = matriz
        aluno.curso_campus = curso
        aluno.save()

    MatriculaPeriodo.objects.get_or_create(
        aluno=aluno,
        ano_letivo=Ano.objects.get_or_create(ano=2018)[0],
        periodo_letivo=1,
        situacao=SituacaoMatriculaPeriodo.objects.get_or_create(id=SituacaoMatriculaPeriodo.MATRICULADO, descricao='Matriculado')[0],
    )

    PessoaJuridica.objects.get_or_create(nome='BANCO DO BRASIL SA', nome_fantasia='Banco do Brasil', cnpj='00.000.000/0001-91')

    servidor = Servidor.objects.filter(matricula='102003')[0]
    if servidor:
        servidor.eh_docente = True
        servidor.save()
        Professor.objects.get_or_create(vinculo=servidor.get_vinculo())

    servidor2 = Servidor.objects.filter(matricula='102004')[0]
    if servidor2:
        servidor2.eh_docente = True
        servidor2.save()
        Professor.objects.get_or_create(vinculo=servidor2.get_vinculo())

    TipoRemuneracao.objects.get_or_create(descricao='Bolsa')

    estado = Estado.objects.get_or_create(nome='Estado')[0]
    Cidade.objects.get_or_create(nome='Cidade', estado=estado)
