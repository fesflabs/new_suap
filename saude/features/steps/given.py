# -*- coding: utf-8 -*-`


import datetime

from behave import given

from rh.models import TipoUnidadeOrganizacional, Setor, UnidadeOrganizacional, PessoaFisica
from saude.models import (
    TipoAtividadeGrupo,
    PerguntaMarcadorNutricao,
    AnoReferenciaAcaoEducativa,
    ObjetivoAcaoEducativa,
    CategoriaExameLaboratorial,
    OrientacaoNutricional,
    ReceitaNutricional,
    AvaliacaoGastroIntestinal,
    RestricaoAlimentar,
    MotivoAtendimentoNutricao,
    DiagnosticoNutricional,
    ProcedimentoOdontologia,
    MotivoChegadaPsicologia,
    QueixaPsicologica,
    BloqueioAtendimentoSaude,
    ProcedimentoEnfermagem,
)


@given('os usuarios do SAUDE')
def step_usuarios_saude(context):
    context.execute_steps(
        """
       Dado os seguintes usuários
            | Nome                       | Matrícula   | Setor | Lotação | Email                                   | CPF             | Senha | Grupo                                |
            | CoordSaudeSistemico        | 111001      | CZN    | CZN      | CoordenadorSaudeSistemico@ifrn.edu.br   | 668.588.220-46  | abcd  | Coordenador de Saúde Sistêmico       |
            | Medico                     | 111002      | CZN    | CZN      | Medico@ifrn.edu.br                      | 854.354.257-87  | abcd  | Médico                               |
            | Odontologo                 | 111003      | DIAC/CZN    | DIAC/CZN      | Odontologo@ifrn.edu.br                  | 765.845.710-12  | abcd  | Odontólogo                           |
            | Enfermeiro                 | 111004      | CEN    | CEN      | Enfermeiro@ifrn.edu.br                  | 546.943.756-23  | abcd  | Enfermeiro                           |
            | TecnicoEnfermagem          | 111005      | DIAC/CEN    | DIAC/CEN      | TecnicoEnfermagem@ifrn.edu.br           | 324.543.344-12  | abcd  | Técnico em Enfermagem                |
            | AuxiliarEnfermagem         | 111006      | CZN    | CZN      | AuxiliarEnfermagem@ifrn.edu.br          | 756.257.546-12  | abcd  | Auxiliar de Enfermagem               |
            | Fisioterapeuta             | 111007      | CZN    | CZN      | Fisioterapeuta@ifrn.edu.br              | 543.743.423-67  | abcd  | Fisioterapeuta                       |
            | Psicologo                  | 111008      | DIAC/CZN    | DIAC/CZN      | Psicologo@ifrn.edu.br                   | 257.743.710-67  | abcd  | Psicólogo                            |
            | Nutricionista              | 111009      | DIAC/CZN    | DIAC/CZN      | Nutricionista@ifrn.edu.br               | 943.543.257-67  | abcd  | Nutricionista                        |
            | TecnicoSaudeBucal          | 111010      | DIAC/CZN    | DIAC/CZN      | TecnicoSaudeBucal@ifrn.edu.br           | 645.433.195-20  | abcd  | Técnico em Saúde Bucal               |
    """
    )


@given('os seguintes campi')
def step_os_seguintes_campi(context):
    tipo_unid = TipoUnidadeOrganizacional.objects.last()
    setor_id, _ = Setor.objects.get_or_create(nome='A007')

    unidade, _ = UnidadeOrganizacional.objects.suap().get_or_create(nome='CCampus1', sigla='CC', tipo=tipo_unid, setor=setor_id)


@given('os seguintes tipos de atividades em grupo')
def step_tipos_atividades_grupos(context):
    atividade, _ = TipoAtividadeGrupo.get_or_create(descricao='Reunião')


@given('os seguintes anos de referencia')
def step_anos_referencia(context):
    ano, _ = AnoReferenciaAcaoEducativa.objects.get_or_create(ano='2019')


@given('os seguintes objetivos')
def step_objetivos(context):
    objetivo, _ = ObjetivoAcaoEducativa.objects.get_or_create(descricao='Novo Objetivo de Ação Educativa')


@given('as seguintes perguntas')
def step_perguntas(context):
    pergunta, _ = PerguntaMarcadorNutricao.objects.get_or_create(pergunta='Nova Pergunta')


@given('as seguintes categorias de exames')
def step_categorias_exames(context):
    categoria, _ = CategoriaExameLaboratorial.objects.get_or_create(nome='Perfil Glicêmico')


@given('os seguintes pacientes bloqueados')
def step_pacientes_bloqueados(context):
    pessoa_fisica = PessoaFisica.objects.filter(cpf='559.454.350-31').first()
    profissional = PessoaFisica.objects.filter(cpf='668.588.220-46').first()

    bloqueio_atendimento, _ = BloqueioAtendimentoSaude.objects.get_or_create(
        vinculo_paciente=pessoa_fisica.sub_instance().get_vinculo(),
        vinculo_profissional=profissional.sub_instance().get_vinculo(),
        data=datetime.datetime.strptime('01/29/2050', "%m/%d/%Y"),
    )


@given('as seguintes orientacoes nutricionais')
def step_orientacoes_nutricionais(context):
    if context.table is not None:
        for row in context.table:
            orientacao_nutricional, _ = OrientacaoNutricional.objects.get_or_create(titulo=row['Titulo'], descricao=row['Descrição'])
    else:
        orientacao_nutricional, _ = OrientacaoNutricional.objects.get_or_create(titulo='Nova orientação nutricional', descricao='Descrição da orientação nutricional.')


@given('as seguintes receitas nutricionais')
def step_receitas_nutricionais(context):
    if context.table is not None:
        for row in context.table:
            receita_nutricional, _ = ReceitaNutricional.objects.get_or_create(titulo=row['Titulo'], descricao=row['Descrição'])
    else:
        receita_nutricional, _ = ReceitaNutricional.objects.get_or_create(titulo='Nova receita nutricional', descricao='Descrição da receita nutricional.')


@given('as seguintes avaliações gastrointestinais')
def step_avaliacoes_gastrointestinais(context):
    if context.table is not None:
        for row in context.table:
            avaliacao_gastrointestinal, _ = AvaliacaoGastroIntestinal.objects.get_or_create(descricao=row['Descrição'])
    else:
        avaliacao_gastrointestinal, _ = AvaliacaoGastroIntestinal.objects.get_or_create(descricao='Outros')


@given('as seguintes restrições alimentares')
def step_restricoes_alimentares(context):
    if context.table is not None:
        for row in context.table:
            restricao_alimentar, _ = RestricaoAlimentar.objects.get_or_create(descricao=row['Descrição'])
    else:
        restricao_alimentar, _ = RestricaoAlimentar.objects.get_or_create(descricao='Outros')


@given('os seguintes motivos do atendimento nutricional')
def step_motivos_atendimento_nutricional(context):
    if context.table is not None:
        for row in context.table:
            motivo_atendimento, _ = MotivoAtendimentoNutricao.objects.get_or_create(descricao=row['Descrição'])
    else:
        motivo_atendimento, _ = MotivoAtendimentoNutricao.objects.get_or_create(descricao='Outros')


@given('os seguintes diagnósticos nutricionais')
def step_diagnosticos_nutricionais(context):
    if context.table is not None:
        for row in context.table:
            diagnostico_nutricional, _ = DiagnosticoNutricional.objects.get_or_create(descricao=row['Descrição'])
    else:
        diagnostico_nutricional, _ = DiagnosticoNutricional.objects.get_or_create(descricao='Outros')


@given('os seguintes procedimentos odontológicos')
def step_procedimentos_odontologicos(context):
    if context.table is not None:
        for row in context.table:
            procedimento_odontologico, _ = ProcedimentoOdontologia.objects.get_or_create(denominacao=row['Denominação'])
    else:
        procedimento_odontologico, _ = ProcedimentoOdontologia.objects.get_or_create(denominacao='Outros')


@given('os seguintes motivos de chegada psicológo')
def step_chegada_psicologo(context):
    if context.table is not None:
        for row in context.table:
            motivo_chegada, _ = MotivoChegadaPsicologia.objects.get_or_create(descricao=row['Descrição'])
    else:
        MotivoChegadaPsicologia.objects.get_or_create(descricao='Outros')


@given('as seguintes queixas psicológicas')
def step_queixas_psicologicas(context):
    if context.table is not None:
        for row in context.table:
            queixa_psicologica, _ = QueixaPsicologica.objects.get_or_create(descricao=row['Descrição'])
    else:
        QueixaPsicologica.objects.get_or_create(descricao='Outros')


@given('os seguintes procedimentos de enfermagem')
def step_procedimentos_enfermagem(context):
    if context.table is not None:
        for row in context.table:
            procedimento_enfermagem, _ = ProcedimentoEnfermagem.objects.get_or_create(denominacao=row['Denominação'])
    else:
        procedimento_enfermagem, _ = ProcedimentoEnfermagem.objects.get_or_create(denominacao='Outros')
