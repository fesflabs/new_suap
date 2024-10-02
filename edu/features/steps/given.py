from behave import given  # NOQA
from django.contrib.auth.models import Group
from datetime import datetime
from edu.models.cursos import Componente, ComponenteCurricular, Matriz, EstruturaCurso, CursoCampus, MatrizCurso
from edu.models.cadastros_gerais import (
    Estado,
    Pais,
    TipoComponente,
    NivelEnsino,
    Nucleo,
    NaturezaParticipacao,
    AreaCapes,
    Modalidade,
    TipoProfessorDiario,
    HorarioAulaDiario,
    HorarioAula,
    HorarioCampus,
    FormaIngresso,
    Cidade,
    SituacaoMatricula,
    SituacaoMatriculaPeriodo,
    Turno,
)
from edu.models.diretorias import Diretoria, CalendarioAcademico
from edu.models.diarios import Diario, ProfessorDiario, ConfiguracaoAvaliacao, ItemConfiguracaoAvaliacao, Aula, NotaAvaliacao
from edu.models.professores import Professor
from edu.models.turmas import Turma
from edu.models.alunos import Aluno, SequencialMatricula
from edu.models.historico import MatriculaPeriodo, MatriculaDiario
from edu.models.utils import HistoricoSituacaoMatricula, HistoricoSituacaoMatriculaPeriodo
from edu.models.procedimentos import ConfiguracaoPedidoMatricula, PedidoMatriculaDiario, PedidoMatricula


def mudar_data(context, data):
    context.execute_steps(f'Quando a data do sistema for "{data}"')


@given('os cadastros de Pais e Estado')
def step_cadastros_pais_estado(context):
    Pais.objects.get_or_create(nome='Brasil')
    Estado.objects.get_or_create(id=24, nome='Rio Grande do Norte')


@given('os cadastros da funcionalidade 001')
def step_cadastros_feature_001(context):
    from rh.models import Setor

    if not Diretoria.objects.filter(setor=Setor.objects.get(sigla='DIAC/CEN')).exists():
        from rh.models import JornadaTrabalho, CargoEmprego, Situacao, Servidor
        from comum.models import UsuarioGrupoSetor, UsuarioGrupo

        mudar_data(context, '10/03/2019')

        # Cenário: Cadastrar Diretoria Acadêmica
        diretoria = Diretoria.objects.get_or_create(setor=Setor.objects.get(sigla='DIAC/CEN'))[0]

        situacao = Situacao.objects.get(codigo=Situacao.ATIVO_PERMANENTE)
        cargo_emprego = CargoEmprego.objects.get(codigo='01')
        setor_suap = Setor.todos.get(sigla='DIAC/CEN', codigo__isnull=True)
        setor_siape = Setor.todos.get(sigla='DIAC/CEN', codigo__isnull=False)
        jornada_trabalho = JornadaTrabalho.objects.get(codigo='01')

        if not Servidor.objects.filter(matricula='100001').exists():
            servidor = Servidor.objects.get_or_create(
                nome='Administrador Acadêmico',
                matricula='100001',
                excluido=False,
                situacao=situacao,
                cargo_emprego=cargo_emprego,
                setor=setor_suap,
                setor_lotacao=setor_siape,
                setor_exercicio=setor_siape,
                email='administrador_academico@ifrn.edu.br',
                cpf='730.378.660-04',
                jornada_trabalho=jornada_trabalho,
            )[0]
            user = servidor.user
            user.set_password('abcd')
            user.is_staff = True
            user.groups.add(Group.objects.get(name='Servidor'))
            user.groups.add(Group.objects.get(name='Administrador Acadêmico'))
            user.save()
            servidor.eh_servidor = True
            servidor.save()

        # Cenário: Vincular Secretário Acadêmico
        if not Servidor.objects.filter(matricula='100002').exists():
            servidor = Servidor.objects.get_or_create(
                nome='Servidor SA',
                matricula='100002',
                excluido=False,
                situacao=situacao,
                cargo_emprego=cargo_emprego,
                setor=setor_suap,
                setor_lotacao=setor_siape,
                setor_exercicio=setor_siape,
                email='secretario_academico@ifrn.edu.br',
                cpf='601.382.290-58',
                jornada_trabalho=jornada_trabalho,
            )[0]
            user = servidor.user
            user.set_password('abcd')
            user.is_staff = True
            user.groups.add(Group.objects.get(name='Servidor'))
            user.save()
            grupo = Group.objects.get(name='Secretário Acadêmico')
            usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupo, user=user)[0]
            UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=diretoria.setor)
            servidor.eh_servidor = True
            servidor.save()

        # Cenário: Vincular Diretor Geral
        if not Servidor.objects.filter(matricula='100003').exists():
            servidor = Servidor.objects.get_or_create(
                nome='Servidor DG',
                matricula='100003',
                excluido=False,
                situacao=situacao,
                cargo_emprego=cargo_emprego,
                setor=setor_suap,
                setor_lotacao=setor_siape,
                setor_exercicio=setor_siape,
                email='diretor_geral@ifrn.edu.br',
                cpf='940.209.400-88',
                jornada_trabalho=jornada_trabalho,
            )[0]
            user = servidor.user
            user.set_password('abcd')
            user.is_staff = True
            user.groups.add(Group.objects.get(name='Servidor'))
            user.save()
            servidor.eh_servidor = True
            servidor.save()

            grupo = Group.objects.get(name='Diretor Geral')
            usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupo, user=user)[0]
            UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=diretoria.setor)

            diretoria.diretor_geral = servidor
            diretoria.diretor_geral_exercicio = servidor
            diretoria.save()

        # Cenário: Vincular Diretor Acadêmico
        if not Servidor.objects.filter(matricula='100004').exists():
            servidor = Servidor.objects.get_or_create(
                nome='Servidor DA',
                matricula='100004',
                excluido=False,
                situacao=situacao,
                cargo_emprego=cargo_emprego,
                setor=setor_suap,
                setor_lotacao=setor_siape,
                setor_exercicio=setor_siape,
                email='diretor_academico@ifrn.edu.br',
                cpf='923.941.200-02',
                jornada_trabalho=jornada_trabalho,
            )[0]
            user = servidor.user
            user.set_password('abcd')
            user.is_staff = True
            user.groups.add(Group.objects.get(name='Servidor'))
            user.save()
            servidor.eh_servidor = True
            servidor.save()

            grupo = Group.objects.get(name='Diretor Acadêmico')
            usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupo, user=user)[0]
            UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=diretoria.setor)

            diretoria.diretor_academico = servidor
            diretoria.diretor_academico_exercicio = servidor
            diretoria.save()

        # Cenário: Vincular Coordenador de Curso
        if not Servidor.objects.filter(matricula='100005').exists():
            servidor = Servidor.objects.get_or_create(
                nome='Servidor CC',
                matricula='100005',
                excluido=False,
                situacao=situacao,
                cargo_emprego=cargo_emprego,
                setor=setor_suap,
                setor_lotacao=setor_siape,
                setor_exercicio=setor_siape,
                email='coordenador_curso@ifrn.edu.br',
                cpf='156.763.530-07',
                jornada_trabalho=jornada_trabalho,
            )[0]
            user = servidor.user
            user.set_password('abcd')
            user.is_staff = True
            user.groups.add(Group.objects.get(name='Servidor'))
            user.save()
            servidor.eh_servidor = True
            servidor.save()

            grupo = Group.objects.get(name='Coordenador de Curso')
            usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupo, user=user)[0]
            UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=diretoria.setor)

        # Cenário: Vincular Coordenador de Registros Acadêmicos
        if not Servidor.objects.filter(matricula='100006').exists():
            servidor = Servidor.objects.get_or_create(
                nome='Servidor CRA',
                matricula='100006',
                excluido=False,
                situacao=situacao,
                cargo_emprego=cargo_emprego,
                setor=setor_suap,
                setor_lotacao=setor_siape,
                setor_exercicio=setor_siape,
                email='cra@ifrn.edu.br',
                cpf='153.888.030-07',
                jornada_trabalho=jornada_trabalho,
            )[0]
            user = servidor.user
            user.set_password('abcd')
            user.is_staff = True
            user.groups.add(Group.objects.get(name='Servidor'))
            user.save()
            servidor.eh_servidor = True
            servidor.save()

            grupo = Group.objects.get(name='Coordenador de Registros Acadêmicos')
            usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupo, user=user)[0]
            UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=diretoria.setor)

        if not Servidor.objects.filter(matricula='100007').exists():
            servidor = Servidor.objects.get_or_create(
                nome='Servidor P',
                matricula='100007',
                excluido=False,
                situacao=situacao,
                cargo_emprego=cargo_emprego,
                setor=setor_suap,
                setor_lotacao=setor_siape,
                setor_exercicio=setor_siape,
                email='professor@ifrn.edu.br',
                cpf='475.849.400-21',
                jornada_trabalho=jornada_trabalho,
            )[0]
            user = servidor.user
            user.set_password('abcd')
            user.is_staff = True
            user.groups.add(Group.objects.get(name='Servidor'))
            user.save()
            servidor.eh_servidor = True
            servidor.save()

    if not Diretoria.objects.filter(setor=Setor.objects.get(sigla='RAIZ')).exists():
        # Cenário: Cadastrar Diretoria Acadêmica do tipo RE
        reitoria = Diretoria.objects.get_or_create(setor=Setor.objects.get(sigla='RAIZ'), tipo=Diretoria.TIPO_SISTEMICA)[0]

        re_suap = Setor.todos.get(sigla='RAIZ', codigo__isnull=True)
        re_siape = Setor.todos.get(sigla='RAIZ', codigo__isnull=False)

        # Cenário: Vincular Diretor de Avaliação e Regulação do Ensino
        if not Servidor.objects.filter(matricula='100009').exists():
            servidor = Servidor.objects.get_or_create(
                nome='Servidor DARE',
                matricula='100009',
                excluido=False,
                situacao=situacao,
                cargo_emprego=cargo_emprego,
                setor=re_suap,
                setor_lotacao=re_siape,
                setor_exercicio=re_siape,
                email='dare@ifrn.edu.br',
                cpf='921.158.970-30',
                jornada_trabalho=jornada_trabalho,
            )[0]
            user = servidor.user
            user.set_password('abcd')
            user.is_staff = True
            user.groups.add(Group.objects.get(name='Servidor'))
            user.save()
            grupo = Group.objects.get(name='Diretor de Avaliação e Regulação do Ensino')
            usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupo, user=user)[0]
            UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=reitoria.setor)
            servidor.eh_servidor = True
            servidor.save()

        # Cenário: Vincular Operador ENADE
        if not Servidor.objects.filter(matricula='100008').exists():
            servidor = Servidor.objects.get_or_create(
                nome='Servidor Op Enade',
                matricula='100008',
                excluido=False,
                situacao=situacao,
                cargo_emprego=cargo_emprego,
                setor=setor_suap,
                setor_lotacao=setor_siape,
                setor_exercicio=setor_siape,
                email='op.enade@ifrn.edu.br',
                cpf='330.384.680-45',
                jornada_trabalho=jornada_trabalho,
            )[0]
            user = servidor.user
            user.set_password('abcd')
            user.is_staff = True
            user.groups.add(Group.objects.get(name='Servidor'))
            user.save()
            grupo = Group.objects.get(name='Operador ENADE')
            usuario_grupo = UsuarioGrupo.objects.get_or_create(group=grupo, user=user)[0]
            UsuarioGrupoSetor.objects.get_or_create(usuario_grupo=usuario_grupo, setor=diretoria.setor)
            servidor.eh_servidor = True
            servidor.save()


@given('os cadastros da funcionalidade 002')
def step_cadastros_feature_002(context):
    if not TipoComponente.objects.filter(descricao='POS').exists():
        from comum.models import Ano

        # Cenário: Cadastrar Tipo de Componente
        step_cadastro_tipo_componente(None)
        tipo = TipoComponente.objects.get_or_create(descricao='POS')[0]

        # Cenário: Cadastrar Componente
        step_cadastro_componente(None)
        diretoria = Diretoria.objects.get(setor__sigla='DIAC/CEN')
        nivel = NivelEnsino.objects.get(descricao='Pós-graduação')
        componente = dict(
            descricao='Leitura e Produção de Textos Acadêmicos',
            descricao_historico='Leitura e Produção de Textos Acadêmicos',
            abreviatura='LPTA',
            tipo=tipo,
            diretoria=diretoria,
            nivel_ensino=nivel,
            ativo=True,
            ch_hora_relogio=45,
            ch_hora_aula=60,
            ch_qtd_creditos=3,
        )
        Componente.objects.get_or_create(**componente)

        # Cenário: Cadastrar Estrutura de Curso
        estrutura = dict(
            descricao='Especialização e Aperfeiçoamento',
            ativo=True,
            tipo_avaliacao=EstruturaCurso.TIPO_AVALIACAO_SERIADO,
            limite_reprovacao=10,
            criterio_avaliacao=EstruturaCurso.CRITERIO_AVALIACAO_NOTA,
            media_aprovacao_sem_prova_final=60,
            media_evitar_reprovacao_direta=20,
            media_aprovacao_avaliacao_final=60,
            percentual_frequencia=75,
            ira=EstruturaCurso.IRA_PONDERADA_POR_CH,
            qtd_periodos_conclusao=4,
            qtd_max_reprovacoes_periodo=0,
            qtd_max_reprovacoes_disciplina=0,
            qtd_trancamento_voluntario=2,
            numero_max_certificacoes=4,
            media_certificacao_conhecimento=60,
        )
        estrutura = EstruturaCurso.objects.get_or_create(**estrutura)[0]

        # Cenário: Cadastrar Matriz Curricular
        ano = Ano.objects.get(ano=2019)
        matriz = dict(
            descricao='Especialização em Educação Profissional',
            ano_criacao=ano,
            periodo_criacao=1,
            nivel_ensino=nivel,
            ativo=True,
            data_inicio=datetime.strptime('15/03/2019', '%d/%m/%Y'),
            qtd_periodos_letivos=2,
            estrutura=estrutura,
            ch_componentes_obrigatorios=90,
            ch_componentes_optativos=0,
            ch_componentes_eletivos=0,
            ch_seminarios=0,
            ch_pratica_profissional=0,
            ch_componentes_tcc=30,
            exige_tcc=True,
            ch_atividades_complementares=0,
            ch_atividades_aprofundamento=0,
            ch_atividades_extensao=0,
            ch_pratica_como_componente=0,
            ch_visita_tecnica=0
        )
        matriz = Matriz.objects.get_or_create(**matriz)[0]

        # Cenário: Cadastrar Núcleo
        nucleo = Nucleo.objects.get_or_create(descricao='Formação')[0]

        # Cenário: Vincular Componente à Matriz Curricular
        step_cadastro_componente_curricular(None)
        componente_curricular = dict(
            matriz=matriz,
            componente=Componente.objects.get(abreviatura='LPTA'),
            periodo_letivo=1,
            tipo=ComponenteCurricular.TIPO_REGULAR,
            qtd_avaliacoes=1,
            nucleo=nucleo,
            ch_presencial=45,
            ch_pratica=0,
        )
        ComponenteCurricular.objects.get_or_create(**componente_curricular)

        # Cenário: Cadastrar Natureza de Participação
        natureza = NaturezaParticipacao.objects.get_or_create(descricao='Presencial')[0]

        # Cenário: Cadastrar Área Capes
        areacapes = AreaCapes.objects.get_or_create(descricao='Educação')[0]

        # Cenário: Cadastrar Curso
        diretoria = Diretoria.objects.get(setor__sigla='DIAC/CEN')
        curso = dict(
            descricao='Especialização em Educação Profissional',
            descricao_historico='Especialização em Educação Profissional',
            ano_letivo=ano,
            periodo_letivo=1,
            data_inicio=datetime.strptime('15/03/2019', '%d/%m/%Y'),
            ativo=True,
            codigo='10101',
            natureza_participacao=natureza,
            modalidade=Modalidade.objects.get(descricao='Especialização'),
            area_capes=areacapes,
            periodicidade=CursoCampus.PERIODICIDADE_SEMESTRAL,
            diretoria=diretoria,
            emite_diploma=True,
            plano_ensino=True,
            fator_esforco_curso=1,
            titulo_certificado_masculino='Especialista em Educação Profissional',
            titulo_certificado_feminino='Especialista em Educação Profissional',
        )
        curso = CursoCampus.objects.get_or_create(**curso)[0]

        # Cenário: Vincular Matriz ao Curso
        matrizcurso = dict(
            matriz=matriz,
            curso_campus=curso,
        )
        MatrizCurso.objects.get_or_create(**matrizcurso)


@given('os cadastros da funcionalidade 003')
def step_cadastros_feature_003(context):
    if not Turno.objects.filter(id='1', descricao='Noturno').exists():
        from rh.models import UnidadeOrganizacional
        from comum.models import Vinculo, Sala, Ano

        # Cenário: Cadastrar Turno
        step_cadastro_turno(None)
        Turno.objects.get_or_create(id='1', descricao='Noturno')

        # Cenário: Cadastrar Horário do Campus
        uo = UnidadeOrganizacional.objects.suap().get(sigla='CEN')
        horariocampus = HorarioCampus.objects.get_or_create(descricao='Horário Padrão [Aula 45min]', uo=uo, ativo=True, eh_padrao=True)[0]
        turno = Turno.objects.get(descricao='Matutino')
        HorarioAula.objects.get_or_create(horario_campus=horariocampus, numero=1, turno=turno, inicio='7:00', termino='7:45')
        HorarioAula.objects.get_or_create(horario_campus=horariocampus, numero=2, turno=turno, inicio='7:50', termino='8:35')
        HorarioAula.objects.get_or_create(horario_campus=horariocampus, numero=3, turno=turno, inicio='8:40', termino='9:25')

        # Cenário: Cadastrar Tipo de Professor em Diário
        TipoProfessorDiario.objects.get_or_create(descricao='Principal')[0]

        # Cenário: Cadastrar Calendário Acadêmico
        step_cadastro_calendario_academico(None)
        ano_letivo = Ano.objects.get(ano=2019)
        diretoria = Diretoria.objects.get(setor__sigla='DIAC/CEN')
        calendario = CalendarioAcademico.objects.get_or_create(
            descricao='Calendário Acadêmico Especialização 2019.1',
            uo=uo,
            diretoria=diretoria,
            tipo=CalendarioAcademico.TIPO_SEMESTRAL,
            ano_letivo=ano_letivo,
            periodo_letivo=1,
            data_inicio=datetime.strptime('20/03/2019', '%d/%m/%Y'),
            data_fim=datetime.strptime('18/07/2019', '%d/%m/%Y'),
            data_fechamento_periodo=datetime.strptime('19/07/2019', '%d/%m/%Y'),
            qtd_etapas=CalendarioAcademico.QTD_ETAPA_1,
            data_inicio_etapa_1=datetime.strptime('20/03/2019', '%d/%m/%Y'),
            data_fim_etapa_1=datetime.strptime('18/07/2019', '%d/%m/%Y'),
        )[0]

        # Cenário: Gerar Turmas e Diário
        curso = CursoCampus.objects.get(descricao='Especialização em Educação Profissional')
        matriz = Matriz.objects.get(descricao='Especialização em Educação Profissional')
        componentes = ComponenteCurricular.objects.filter(componente__sigla__in=['POS.0003', 'POS.0001'])
        if not Turma.objects.filter(ano_letivo=ano_letivo, periodo_letivo=1, curso_campus=curso, matriz=matriz).exists():
            Turma.gerar_turmas(ano_letivo, 1, {1: turno}, {1: 10}, {1: 1}, curso, matriz, horariocampus, calendario, componentes, False, True)

        # Cenário: Configurar Diário
        step_cadastro_predio(None)
        step_cadastro_sala(None)
        step_configuracao_diario(None)
        diario = Diario.objects.get(pk=1)
        diario.local_aula = Sala.objects.get(nome='Sala 101')
        diario.save()
        vinculo = Vinculo.objects.get(pessoa__nome='Servidor P')
        professor = Professor.objects.get_or_create(vinculo=vinculo)[0]
        Professor.objects.update(titulacao='Graduado', ultima_instituicao_de_titulacao='UFRN',
                                 area_ultima_titulacao='01', ano_ultima_titulacao=Ano.objects.first())
        professor.vinculo.user.groups.add(Group.objects.get(name='Professor'))
        professordiario = dict(
            diario=diario,
            professor=professor,
            tipo=TipoProfessorDiario.objects.get(descricao='Principal'),
            percentual_ch=100,
            data_inicio_etapa_1=datetime.strptime('20/03/2019', '%d/%m/%Y'),
            data_fim_etapa_1=datetime.strptime('25/07/2019', '%d/%m/%Y'),
            data_inicio_etapa_final=datetime.strptime('19/07/2019', '%d/%m/%Y'),
            data_fim_etapa_final=datetime.strptime('26/07/2019', '%d/%m/%Y'),
        )
        ProfessorDiario.objects.get_or_create(**professordiario)
        step_definicao_horario_aula_diario(None, '1M1,1M2', diario.pk)


@given('os cadastros da funcionalidade 004')
def step_cadastros_feature_004(context):
    if not FormaIngresso.objects.filter(descricao='Ampla Concorrência').exists():
        from rh.models import PessoaFisica
        from comum.models import Raca, Ano

        step_cadastros_pais_estado(context)

        # Cenário: Cadastrar Forma de Ingresso
        ingresso = FormaIngresso.objects.get_or_create(descricao='Ampla Concorrência', ativo=True, classificacao_censup=FormaIngresso.ENEM, classificacao_educacenso=4)[0]

        # Cenário: Cadastrar Cidade
        cidade = Cidade.objects.get_or_create(nome='Natal')[0]

        # Cenário: Efetuar Matrícula Institucional
        step_cadastro_raca(None)
        pessoa_fisica = PessoaFisica()
        pessoa_fisica.cpf = '770.625.744-49'
        pessoa_fisica.nome_registro = 'João da Silva'
        pessoa_fisica.sexo = 'M'
        pessoa_fisica.nascimento_data = datetime.strptime('10/10/1990', '%d/%m/%Y')
        pessoa_fisica.raca = Raca.objects.get(descricao='Parda')
        pessoa_fisica.email_secundario = 'joao.silva@email.com'
        pessoa_fisica.save()

        ano = Ano.objects.get(ano=2019)
        curso = CursoCampus.objects.get(descricao='Especialização em Educação Profissional')
        matriz = Matriz.objects.get(descricao='Especialização em Educação Profissional')

        aluno = cadastrar_aluno(pessoa_fisica, cidade, ano, ingresso, curso, matriz)
        matricular_aluno(aluno, ano, curso, matriz)

        pessoa_fisica2 = PessoaFisica()
        pessoa_fisica2.cpf = '901.348.860-97'
        pessoa_fisica2.nome_registro = 'Pedro da Silva'
        pessoa_fisica2.sexo = 'M'
        pessoa_fisica2.nascimento_data = datetime.strptime('10/10/1990', '%d/%m/%Y')
        pessoa_fisica2.raca = Raca.objects.get(descricao='Parda')
        pessoa_fisica2.email_secundario = 'pedro.silva@email.com'
        pessoa_fisica2.save()
        aluno2 = cadastrar_aluno(pessoa_fisica2, cidade, ano, ingresso, curso, matriz)
        matricular_aluno(aluno2, ano, curso, matriz)

        # Cenário: Matricular em Turma
        turma = Turma.objects.get(ano_letivo=ano, periodo_letivo=1, periodo_matriz=1, curso_campus=curso, matriz=matriz)
        mp = MatriculaPeriodo.objects.filter(aluno__curso_campus=curso, ano_letivo=ano, periodo_letivo=1, periodo_matriz=1)

        turma.matricular_alunos(mp)


@given('os cadastros da funcionalidade 005')
def step_cadastros_feature_005(context):
    if not Aula.objects.all().exists():

        # Cenário: Acessar diário
        diario = Diario.objects.get(componente_curricular__componente__sigla='POS.0001')

        # Cenário: Configurar Forma de Avaliação
        configuracao = ConfiguracaoAvaliacao.objects.get(diario=diario, etapa=1)
        item_configuracao_avaliacao = ItemConfiguracaoAvaliacao.objects.get(configuracao_avaliacao=configuracao)
        item_configuracao_avaliacao.tipo = ItemConfiguracaoAvaliacao.TIPO_SEMINARIO
        item_configuracao_avaliacao.sigla = 'S1'
        item_configuracao_avaliacao.descricao = 'Avaliação final'
        item_configuracao_avaliacao.data = datetime.strptime('20/07/2019', '%d/%m/%Y')
        item_configuracao_avaliacao.save()

        # Cenário: Registrar Aula
        mudar_data(context, '21/03/2019')
        professor = Professor.objects.get(vinculo__pessoa__nome='Servidor P')
        professordiario = ProfessorDiario.objects.get(diario=diario, professor=professor)
        Aula.objects.get_or_create(
            etapa=1, quantidade=60, data=datetime.strptime('20/03/2019', '%d/%m/%Y'), conteudo='Apresentação da disciplina', professor_diario=professordiario
        )

        # Cenário: Lançar Notas
        matricula_periodo = MatriculaPeriodo.objects.get(aluno__matricula='20191101010001', ano_letivo__ano=2019, periodo_letivo=1)
        matricula_diario = MatriculaDiario.objects.get(diario=diario, matricula_periodo=matricula_periodo)
        nota_avaliacao = NotaAvaliacao.objects.get(matricula_diario=matricula_diario, item_configuracao_avaliacao=item_configuracao_avaliacao)
        nota_avaliacao.nota = 70
        nota_avaliacao.save()
        matricula_diario.registrar_nota_etapa(1)

        # Cenário: Entregar Etapa
        mudar_data(context, '20/07/2019')
        diario.entregar_etapa(1)


@given('os cadastros da funcionalidade 006')
def step_cadastros_feature_006(context):
    matricula_periodo = MatriculaPeriodo.objects.get(aluno__matricula='20191101010001', ano_letivo__ano=2019, periodo_letivo=1)
    if matricula_periodo.situacao.pk == SituacaoMatriculaPeriodo.MATRICULADO:

        # Registrar Aula (em posse do registro)
        diario = Diario.objects.get(componente_curricular__componente__sigla='POS.0003')
        professor = Professor.objects.get(vinculo__pessoa__nome='Servidor P')
        professordiario = ProfessorDiario.objects.get(diario=diario, professor=professor)
        Aula.objects.get_or_create(
            etapa=1, quantidade=60, data=datetime.strptime('20/03/2019', '%d/%m/%Y'), conteudo='Apresentação da disciplina', professor_diario=professordiario
        )

        # Lançar Nota (em posse do registro)
        matricula_diario = MatriculaDiario.objects.get(diario=diario, matricula_periodo=matricula_periodo)
        configuracao = ConfiguracaoAvaliacao.objects.get(diario=diario, etapa=1)
        item_configuracao_avaliacao = ItemConfiguracaoAvaliacao.objects.get(configuracao_avaliacao=configuracao)
        nota_avaliacao = NotaAvaliacao.objects.get(matricula_diario=matricula_diario, item_configuracao_avaliacao=item_configuracao_avaliacao)
        nota_avaliacao.nota = 80
        nota_avaliacao.save()
        matricula_diario.registrar_nota_etapa(1)

        # Cenário: Fechar Período
        diarios = Diario.objects.filter(turma=matricula_periodo.turma)
        for diario in diarios:
            diario.entregar_etapa(1)
            diario.entregar_etapa(5)
        matricula_periodo.fechar_periodo_letivo(False)
        for diario in diarios:
            diario.fechar()


@given('os cadastros da funcionalidade 007')
def step_cadastros_feature_007(context):
    if not ConfiguracaoPedidoMatricula.objects.filter(descricao='Renovação 2019.2').exists():
        from comum.models import Ano

        # Cenário: Gerar Turmas e Diários
        ano = Ano.objects.get(ano=2019)
        turno = Turno.objects.get(descricao='Matutino')
        curso = CursoCampus.objects.get(descricao='Especialização em Educação Profissional')
        matriz = Matriz.objects.get(descricao='Especialização em Educação Profissional')
        horariocampus = HorarioCampus.objects.get(descricao='Horário Padrão [Aula 45min]')
        calendario_academico = CalendarioAcademico.objects.get(descricao='Calendário Acadêmico Especialização 2019.2')
        componentes = ComponenteCurricular.objects.filter(componente__sigla__in=['POS.0003', 'POS.0002'])

        Turma.gerar_turmas(ano, 2, {1: turno, 2: turno}, {1: 10, 2: 10}, {1: 1, 2: 1}, curso, matriz, horariocampus, calendario_academico, componentes, False, True)

        # Cenário: Configurar Renovação de Matrícula
        configuracao_pedido_matricula, _ = ConfiguracaoPedidoMatricula.get_or_create(
            descricao='Renovação 2019.2',
            ano_letivo=ano,
            periodo_letivo=2,
            data_inicio=datetime.strptime('21/07/2019', '%d/%m/%Y'),
            data_fim=datetime.strptime('21/07/2019', '%d/%m/%Y'),
        )
        diretoria = Diretoria.objects.get(setor__sigla='DIAC/CEN')
        configuracao_pedido_matricula.diretorias.add(diretoria)
        configuracao_pedido_matricula.cursos.add(curso)

        # Cenário: Realizar Pedido de Matrícula
        mudar_data(context, "21/07/2019")
        turma = Turma.objects.get(ano_letivo=ano, periodo_letivo=2, periodo_matriz=2, curso_campus=curso, matriz=matriz)
        mp = MatriculaPeriodo.objects.get(aluno__matricula='20191101010001', ano_letivo=ano, periodo_letivo=2, periodo_matriz=2)
        pm = PedidoMatricula.get_or_create(matricula_periodo=mp, configuracao_pedido_matricula=configuracao_pedido_matricula, turma=turma)[0]

        for diario in turma.diario_set.all():
            pedido_matricula_diario = PedidoMatriculaDiario()
            pedido_matricula_diario.diario = diario
            pedido_matricula_diario.pedido_matricula = pm
            pedido_matricula_diario.save()

        # Cenário: Processar Pedidos de Matrícula
        mudar_data(context, "22/07/2019")
        pm.matricular_na_turma()
        qs_pedido_matricula_diario = pm.pedidomatriculadiario_set.filter(diario__turma=turma)
        for pedido_matricula_diario in qs_pedido_matricula_diario:
            pedido_matricula_diario.matricular_no_diario(PedidoMatriculaDiario.MOTIVO_PERIODIZADO)


@given('a matrícula do aluno regime de crédito')
def step_matricula_aluno_credito(context):
    from rh.models import PessoaFisica
    from comum.models import Raca, Ano

    ingresso = FormaIngresso.objects.get_or_create(descricao='Ampla Concorrência', ativo=True, classificacao_censup=FormaIngresso.ENEM, classificacao_educacenso=4)[0]
    cidade = Cidade.objects.get_or_create(nome='Natal')[0]

    pessoa_fisica = PessoaFisica()
    pessoa_fisica.cpf = '194.733.810-26'
    pessoa_fisica.nome_registro = 'Maria Pereira'
    pessoa_fisica.sexo = 'F'
    pessoa_fisica.nascimento_data = datetime.strptime('11/11/1991', '%d/%m/%Y')
    pessoa_fisica.raca = Raca.objects.get(descricao='Parda')
    pessoa_fisica.save()

    ano = Ano.objects.get(ano=2019)
    curso = CursoCampus.objects.get(descricao='Licenciatura em Geografia')
    matriz = Matriz.objects.get(descricao='Licenciatura em Geografia')

    aluno = cadastrar_aluno(pessoa_fisica, cidade, ano, ingresso, curso, matriz)
    matricular_aluno(aluno, ano, curso, matriz)


@given('os cadastros iniciais de banco')
def step_cadastro_banco(context):
    from rh.models import Banco

    Banco.objects.get_or_create(codigo='001', sigla='BB', nome='Banco do Brasil')


@given('os cadastros iniciais de tipo de componente')
def step_cadastro_tipo_componente(context):
    componente = dict(
        descricao='LIC',
    )
    TipoComponente.objects.get_or_create(**componente)


@given('os cadastros iniciais de componente')
def step_cadastro_componente(context):
    tipo = TipoComponente.objects.filter(descricao='POS').first()
    diretoria = Diretoria.objects.filter(setor__sigla='DIAC/CEN').first()
    nivel = NivelEnsino.objects.filter(descricao='Pós-graduação').first()

    componente = dict(
        descricao='Didática da Educação Profissional',
        descricao_historico='Didática da Educação Profissional',
        abreviatura='DEP',
        tipo=tipo,
        diretoria=diretoria,
        nivel_ensino=nivel,
        ativo=True,
        ch_hora_relogio=45,
        ch_hora_aula=60,
        ch_qtd_creditos=3,
    )
    Componente.objects.get_or_create(**componente)

    componente = dict(
        descricao='Elaboração do Trabalho de Conclusão de Curso',
        descricao_historico='Elaboração do Trabalho de Conclusão de Curso',
        abreviatura='ETCC',
        tipo=tipo,
        diretoria=diretoria,
        nivel_ensino=nivel,
        ativo=True,
        ch_hora_relogio=30,
        ch_hora_aula=45,
        ch_qtd_creditos=0,
    )
    Componente.objects.get_or_create(**componente)

    tipo = TipoComponente.objects.filter(descricao='LIC').first()
    nivel = NivelEnsino.objects.filter(descricao='Graduação').first()

    componente = dict(
        descricao='Matemática Aplicada à Geografia',
        descricao_historico='Matemática Aplicada à Geografia',
        abreviatura='MAG',
        tipo=tipo,
        diretoria=diretoria,
        nivel_ensino=nivel,
        ativo=True,
        ch_hora_relogio=30,
        ch_hora_aula=40,
        ch_qtd_creditos=2,
    )
    Componente.objects.get_or_create(**componente)

    componente = dict(
        descricao='Estatística Básica',
        descricao_historico='Estatística Básica',
        abreviatura='EB',
        tipo=tipo,
        diretoria=diretoria,
        nivel_ensino=nivel,
        ativo=True,
        ch_hora_relogio=30,
        ch_hora_aula=40,
        ch_qtd_creditos=2,
    )
    Componente.objects.get_or_create(**componente)

    componente = dict(
        descricao='Fundamentos da Educação',
        descricao_historico='Fundamentos da Educação',
        abreviatura='FE',
        tipo=tipo,
        diretoria=diretoria,
        nivel_ensino=nivel,
        ativo=True,
        ch_hora_relogio=60,
        ch_hora_aula=80,
        ch_qtd_creditos=4,
    )
    Componente.objects.get_or_create(**componente)

    componente = dict(
        descricao='Elaboração de Material Didático em Geografia',
        descricao_historico='Elaboração de Material Didático em Geografia',
        abreviatura='EMDG',
        tipo=tipo,
        diretoria=diretoria,
        nivel_ensino=nivel,
        ativo=True,
        ch_hora_relogio=60,
        ch_hora_aula=80,
        ch_qtd_creditos=4,
    )
    Componente.objects.get_or_create(**componente)


@given('os cadastros iniciais de componente curricular')
def step_cadastro_componente_curricular(context):
    matriz = Matriz.objects.get(descricao='Especialização em Educação Profissional')
    nucleo = Nucleo.objects.get(descricao='Formação')

    componente_curricular = dict(
        matriz=matriz,
        componente=Componente.objects.get(abreviatura='DEP'),
        periodo_letivo=1,
        tipo=ComponenteCurricular.TIPO_REGULAR,
        qtd_avaliacoes=1,
        nucleo=nucleo,
        ch_presencial=45,
        ch_pratica=0,
        tipo_modulo=1
    )
    ComponenteCurricular.objects.get_or_create(**componente_curricular)

    componente_curricular = dict(
        matriz=matriz,
        componente=Componente.objects.get(abreviatura='ETCC'),
        periodo_letivo=2,
        tipo=ComponenteCurricular.TIPO_TRABALHO_CONCLUSAO_CURSO,
        qtd_avaliacoes=1,
        nucleo=nucleo,
        ch_presencial=30,
        ch_pratica=0,
        tipo_modulo=2
    )
    ComponenteCurricular.objects.get_or_create(**componente_curricular)

    matriz = Matriz.objects.filter(descricao='Licenciatura em Geografia')
    if matriz.exists():
        matriz = matriz[0]

        componente_curricular = dict(
            matriz=matriz,
            componente=Componente.objects.get(abreviatura='EB'),
            periodo_letivo=2,
            tipo=ComponenteCurricular.TIPO_REGULAR,
            qtd_avaliacoes=2,
            nucleo=nucleo,
            ch_presencial=30,
            ch_pratica=0,
        )
        ComponenteCurricular.objects.get_or_create(**componente_curricular)

        componente_curricular = dict(
            matriz=matriz,
            componente=Componente.objects.get(abreviatura='FE'),
            periodo_letivo=2,
            tipo=ComponenteCurricular.TIPO_REGULAR,
            qtd_avaliacoes=2,
            nucleo=nucleo,
            ch_presencial=60,
            ch_pratica=0,
        )
        ComponenteCurricular.objects.get_or_create(**componente_curricular)

        componente_curricular = dict(
            matriz=matriz,
            componente=Componente.objects.get(abreviatura='EMDG'),
            optativo=True,
            tipo=ComponenteCurricular.TIPO_REGULAR,
            qtd_avaliacoes=2,
            nucleo=nucleo,
            ch_presencial=60,
            ch_pratica=0,
        )
        ComponenteCurricular.objects.get_or_create(**componente_curricular)


@given('os cadastros iniciais de turno')
def step_cadastro_turno(context):
    Turno.objects.get_or_create(id='2', descricao='Vespertino')
    Turno.objects.get_or_create(id='3', descricao='Matutino')
    Turno.objects.get_or_create(id='5', descricao='EAD')
    Turno.objects.get_or_create(id='6', descricao='Diurno')


@given('os cadastros iniciais de calendário acadêmico')
def step_cadastro_calendario_academico(context):
    from rh.models import UnidadeOrganizacional
    from comum.models import Ano

    uo = UnidadeOrganizacional.objects.suap().get(sigla='CEN')
    diretoria = Diretoria.objects.get(setor__sigla='DIAC/CEN')
    ano_letivo = Ano.objects.get(ano=2019)
    calendario_academico = dict(
        descricao='Calendário Acadêmico Especialização 2019.2',
        uo=uo,
        diretoria=diretoria,
        tipo=CalendarioAcademico.TIPO_SEMESTRAL,
        ano_letivo=ano_letivo,
        periodo_letivo=2,
        data_inicio=datetime.strptime('22/07/2019', '%d/%m/%Y'),
        data_fim=datetime.strptime('29/12/2019', '%d/%m/%Y'),
        data_fechamento_periodo=datetime.strptime('30/12/2019', '%d/%m/%Y'),
        qtd_etapas=CalendarioAcademico.QTD_ETAPA_1,
        data_inicio_etapa_1=datetime.strptime('22/07/2019', '%d/%m/%Y'),
        data_fim_etapa_1=datetime.strptime('29/12/2019', '%d/%m/%Y'),
    )
    CalendarioAcademico.objects.get_or_create(**calendario_academico)

    calendario_academico = dict(
        descricao='Calendário Acadêmico Licenciatura 2019.2',
        uo=uo,
        diretoria=diretoria,
        tipo=CalendarioAcademico.TIPO_SEMESTRAL,
        ano_letivo=ano_letivo,
        periodo_letivo=2,
        data_inicio_espaco_pedagogico=datetime.strptime('22/07/2019', '%d/%m/%Y'),
        data_fim_espaco_pedagogico=datetime.strptime('26/07/2019', '%d/%m/%Y'),
        data_inicio=datetime.strptime('29/07/2019', '%d/%m/%Y'),
        data_fim=datetime.strptime('13/12/2019', '%d/%m/%Y'),
        data_inicio_trancamento=datetime.strptime('29/07/2019', '%d/%m/%Y'),
        data_fim_trancamento=datetime.strptime('02/10/2019', '%d/%m/%Y'),
        data_inicio_certificacao=datetime.strptime('11/07/2019', '%d/%m/%Y'),
        data_fim_certificacao=datetime.strptime('15/07/2019', '%d/%m/%Y'),
        data_inicio_prova_final=datetime.strptime('16/12/2019', '%d/%m/%Y'),
        data_fim_prova_final=datetime.strptime('20/12/2019', '%d/%m/%Y'),
        data_fechamento_periodo=datetime.strptime('31/12/2019', '%d/%m/%Y'),
        qtd_etapas=CalendarioAcademico.QTD_ETAPA_2,
        data_inicio_etapa_1=datetime.strptime('29/07/2019', '%d/%m/%Y'),
        data_fim_etapa_1=datetime.strptime('29/09/2019', '%d/%m/%Y'),
        data_inicio_etapa_2=datetime.strptime('30/09/2019', '%d/%m/%Y'),
        data_fim_etapa_2=datetime.strptime('13/12/2019', '%d/%m/%Y'),
    )
    CalendarioAcademico.objects.get_or_create(**calendario_academico)


@given('os cadastros iniciais de prédio')
def step_cadastro_predio(context):
    from rh.models import UnidadeOrganizacional
    from comum.models import Predio

    uo = UnidadeOrganizacional.objects.suap().get(sigla='CEN')
    Predio.objects.get_or_create(nome='Bloco A', uo=uo, ativo=True)


@given('os cadastros iniciais de sala')
def step_cadastro_sala(context):
    from comum.models import Sala, Predio

    predio = Predio.objects.get(nome='Bloco A')
    Sala.objects.get_or_create(nome='Sala 101', predio=predio, ativa=True)


@given('as configurações iniciais de diário')
def step_configuracao_diario(context):
    from comum.models import Vinculo, Sala

    diario = Diario.objects.get(pk=2)
    diario.local_aula = Sala.objects.get(nome='Sala 101')
    diario.save()
    vinculo = Vinculo.objects.get(pessoa__nome='Servidor P')
    professor = Professor.objects.get_or_create(vinculo=vinculo)[0]
    professor.vinculo.user.groups.add(Group.objects.get(name='Professor'))
    professordiario = dict(
        diario=diario,
        professor=professor,
        tipo=TipoProfessorDiario.objects.get(descricao='Principal'),
        percentual_ch=100,
        data_inicio_etapa_1=datetime.strptime('20/03/2019', '%d/%m/%Y'),
        data_fim_etapa_1=datetime.strptime('25/07/2019', '%d/%m/%Y'),
        data_inicio_etapa_final=datetime.strptime('19/07/2019', '%d/%m/%Y'),
        data_fim_etapa_final=datetime.strptime('26/07/2019', '%d/%m/%Y'),
    )
    ProfessorDiario.objects.get_or_create(**professordiario)
    step_definicao_horario_aula_diario(None, '2M1,2M2', diario.pk)


@given('os horários de aula "{horarios}" do diário "{diario}"')
def step_definicao_horario_aula_diario(context, horarios, diario):
    diario = Diario.objects.get(pk=diario)

    horarios = horarios.split(',')
    for horario in horarios:
        turno = horario[1] == 'N' and 1 or horario[1] == 'V' and 2 or horario[1] == 'M' and 3 or horario[1] == 'E' and 5 or horario[1] == 'D' and 6
        horario_aula = HorarioAula.objects.get(turno=Turno.objects.get(pk=turno), numero=horario[2], horario_campus=diario.horario_campus)
        HorarioAulaDiario.objects.get_or_create(diario=diario, dia_semana=horario[0], horario_aula=horario_aula)


@given('os cadastros iniciais de raça')
def step_cadastro_raca(context):
    from comum.models import Raca

    Raca.objects.get_or_create(descricao='Parda', codigo_siape=4)
    Raca.objects.get_or_create(descricao='Preta', codigo_siape=6)
    Raca.objects.get_or_create(descricao='Branca', codigo_siape=1)
    Raca.objects.get_or_create(descricao='Indígena', codigo_siape=5)
    Raca.objects.get_or_create(descricao='Amarela', codigo_siape=3)
    Raca.objects.get_or_create(descricao='Não declarado', codigo_siape=9)


def cadastrar_aluno(pessoa_fisica, cidade, ano, ingresso, curso, matriz):
    from comum.models import User

    aluno = Aluno()
    aluno.periodo_atual = 1
    aluno.pessoa_fisica = pessoa_fisica
    aluno.estado_civil = 'Solteiro'
    aluno.nome_mae = 'Maria da Silva'
    aluno.logradouro = 'Rua abcd'
    aluno.numero = '123'
    aluno.bairro = 'qwer'
    aluno.cidade = cidade
    aluno.tipo_zona_residencial = '1'
    aluno.nacionalidade = 'Brasileira'
    aluno.naturalidade = cidade
    aluno.ano_letivo = ano
    aluno.periodo_letivo = 1
    aluno.turno = Turno.objects.get(descricao='Matutino')
    aluno.forma_ingresso = ingresso
    aluno.curso_campus = curso
    aluno.matriz = matriz
    aluno.situacao = SituacaoMatricula.objects.get(pk=SituacaoMatricula.MATRICULADO)
    aluno.ano_let_prev_conclusao = 2020
    prefixo = f'{aluno.ano_letivo}{aluno.periodo_letivo}{aluno.curso_campus.codigo}'
    aluno.matricula = SequencialMatricula.proximo_numero(prefixo)
    user = User.objects.get_or_create(username=aluno.matricula, eh_aluno=True)[0]
    user.set_password('123')
    user.is_staff = True
    user.groups.add(Group.objects.get(name='Aluno'))
    user.save()
    pessoa_fisica.user = user
    pessoa_fisica.username = aluno.matricula
    pessoa_fisica.save()
    aluno.email_scholar = ''
    aluno.save()

    return aluno


def matricular_aluno(aluno, ano, curso, matriz):
    hsm = HistoricoSituacaoMatricula()
    hsm.aluno = aluno
    hsm.situacao = aluno.situacao
    hsm.data = datetime.now()
    hsm.save()

    matricula_periodo = MatriculaPeriodo()
    matricula_periodo.aluno = aluno
    matricula_periodo.ano_letivo = aluno.ano_letivo
    matricula_periodo.periodo_letivo = aluno.periodo_letivo
    matricula_periodo.periodo_matriz = 1
    matricula_periodo.situacao = SituacaoMatriculaPeriodo.objects.get(pk=SituacaoMatriculaPeriodo.MATRICULADO)
    matricula_periodo.save()

    hsmp = HistoricoSituacaoMatriculaPeriodo()
    hsmp.matricula_periodo = matricula_periodo
    hsmp.situacao = matricula_periodo.situacao
    hsmp.data = aluno.data_matricula
    hsmp.save()
