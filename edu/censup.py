import datetime
import os
import tempfile
from django.conf import settings
from djtools.utils import to_ascii, mask_cpf
from edu.models.alunos import Aluno
from edu.models.cadastros_gerais import NivelEnsino, Modalidade, SituacaoMatricula, SituacaoMatriculaPeriodo, FormaIngresso
from edu.models.diarios import Diario, ProfessorDiario
from rh.models import Servidor, ServidorFuncaoHistorico


class Exportador:
    DOCENTE = 1
    ALUNOS = 2

    def __init__(self, tipo, ano, uos=None, amostra=True, cpfs=[], ignorar_cpfs=[], task=None):
        self.tipo = tipo
        self.ano = ano
        self.uos = uos
        self.registros = []
        self.amostra = amostra
        self.cpfs = []
        self.ignorar_cpfs = []
        self.task = task
        self.cpf_operador = self.task.user and self.task.user.get_vinculo().pessoa.pessoafisica.cpf or None

        for cpf in cpfs:
            self.cpfs.append(mask_cpf(cpf, clean=False))
        for cpf in ignorar_cpfs:
            self.ignorar_cpfs.append(mask_cpf(cpf, clean=False))

        if tipo == Exportador.DOCENTE:
            self.exportar_docentes()
        elif tipo == Exportador.ALUNOS:
            self.exportar_alunos()

    def __str__(self):
        return '\r\n'.join(self.registros)

    def adicionar(self, registro):
        for i, item in enumerate(registro):
            registro[i] = str(item)
        self.registros.append('|'.join(registro))

    def exportar_docentes(self, matriculas=[]):
        from pesquisa.models import Projeto as ProjetoPesquisa, TipoVinculo
        from projetos.models import Projeto as ProjetoExtensao
        registro = list()

        # 1 Tipo do registro
        registro.append(30)

        # 2 ID da IES no INEP
        registro.append(1082)

        self.adicionar(registro)

        # Diários de gradução e pós-graduação scrict sensu
        diarios = Diario.objects.filter(ano_letivo__ano=self.ano)
        if self.uos:
            diarios = diarios.filter(turma__curso_campus__diretoria__setor__uo__in=self.uos)
        diarios_graducao = diarios.filter(turma__curso_campus__modalidade__nivel_ensino=NivelEnsino.GRADUACAO)
        diarios_graducao_ead = diarios_graducao.filter(turma__curso_campus__diretoria__ead=True)
        diarios_graducao_presenciais = diarios_graducao.filter(turma__curso_campus__diretoria__ead=False)
        diarios_stricto_sensu = diarios.filter(turma__curso_campus__modalidade__in=(Modalidade.MESTRADO, Modalidade.DOUTORADO))
        diarios_stricto_sensu_ead = diarios_stricto_sensu.filter(turma__curso_campus__diretoria__ead=True)
        diarios_stricto_sensu_presenciais = diarios_stricto_sensu.filter(turma__curso_campus__diretoria__ead=False)

        # Docentes que ministraram aula em diários de cursos de gradução no ano de referencia
        professores_diarios = ProfessorDiario.objects.filter(diario__ano_letivo__ano=self.ano, diario__turma__curso_campus__modalidade__nivel_ensino=NivelEnsino.GRADUACAO)
        if self.uos:
            professores_diarios = professores_diarios.filter(diario__turma__curso_campus__diretoria__setor__uo__in=self.uos)
        if matriculas:
            professores_diarios = professores_diarios.filter(
                professor__vinculo__pessoa__id__in=Servidor.objects.filter(matricula__in=matriculas).values_list('pessoa_fisica__id', flat=True)
            )
        professores = Servidor.objects.filter(
            pessoa_fisica__id__in=professores_diarios.values_list('professor__vinculo__pessoa__id', flat=True).order_by('professor__vinculo__pessoa').distinct()
        )
        professores_substitutos = professores.filter(situacao__nome__in=('CONT.PROF.SUBSTITUTO', 'CONT.PROF.TEMPORARIO')).values_list('pk', flat=True).distinct()
        professores_visitantes = professores.filter(situacao__nome='CONTR.PROF.VISITANTE').values_list('pk', flat=True).distinct()
        professores_bolsistas = professores.exclude(contracheque__ano=self.ano).values_list('pk', flat=True).distinct()

        # Docentes que participaram de projetos de pesquisa no ano de referência
        projetos_pesquisa = ProjetoPesquisa.objects.filter(aprovado=True)
        projetos_pesquisa = (
            projetos_pesquisa.filter(inicio_execucao__year=self.ano)
            | projetos_pesquisa.filter(fim_execucao__year=self.ano)
            | projetos_pesquisa.filter(inicio_execucao__year__lt=self.ano, fim_execucao__year__gt=self.ano)
        )
        professores_pesquisa = projetos_pesquisa.values_list('participacao__pessoa', flat=True).order_by('participacao__pessoa').distinct()
        professores_pesquisa_bolsitas = (
            projetos_pesquisa.filter(participacao__vinculo=TipoVinculo.BOLSISTA).values_list('participacao__pessoa', flat=True).order_by('participacao__pessoa').distinct()
        )

        # Docentes que participaram de projetos de extensão no ano de referência
        projetos_extensao = ProjetoExtensao.objects.filter(aprovado=True)
        projetos_extensao = (
            projetos_extensao.filter(inicio_execucao__year=self.ano)
            | projetos_extensao.filter(fim_execucao__year=self.ano)
            | projetos_extensao.filter(inicio_execucao__year__lt=self.ano, fim_execucao__year__gt=self.ano)
        )
        professores_extensao = projetos_extensao.values_list('participacao__pessoa', flat=True).order_by('participacao__pessoa').distinct()

        # Docentes que participaram da gestão ano de referência
        professores_gestores = ServidorFuncaoHistorico.objects.filter()
        professores_gestores = (
            professores_gestores.filter(data_inicio_funcao__year=self.ano)
            | professores_gestores.filter(data_fim_funcao__year=self.ano)
            | professores_gestores.filter(data_inicio_funcao__year__lt=self.ano, data_inicio_funcao__year__gt=self.ano)
        )

        if self.cpfs:
            professores = professores.filter(cpf__in=self.cpfs)

        if self.amostra:
            professores = professores[0:10]

        if self.tipo == Exportador.DOCENTE:
            for servidor in self.task.iterate(professores):
                registro = list()
                cpf = servidor.cpf.replace('.', '').replace('-', '')
                if servidor.cpf in self.ignorar_cpfs:
                    continue

                # 1	Tipo do registro		2	Fixo	Numérico	Obrigatório
                registro.append(31)

                # 2	ID do docente na IES		20	Variável	Alfanumérico	Opcional
                registro.append(servidor.matricula)

                # 3	Nome		120	Variável	Alfanumérico	Obrigatório
                registro.append(to_ascii(servidor.nome.upper()))

                # 4	CPF		11	Fixo	Alfanumérico	Obrigatório
                registro.append(cpf)

                # 5	Documento estrangeiro		20	Variável	Alfanumérico	Opcional
                registro.append('')

                # 6	Data de Nascimento		8	Fixo	Data	Obrigatório
                registro.append(servidor.nascimento_data.strftime('%d%m%Y'))

                # 7	Cor/Raça		1	Fixo	Numérico	Obrigatório TODO
                registro.append(servidor.raca_id and servidor.raca.codigo_censup or 1)

                # 8	Nacionalidade		1	Fixo	Numérico	Obrigatório
                # 1 - Brasileiro 2 - Brasileira - Nascido no exterior ou naturalizado 3 - Estrangeiro
                if servidor.nacionalidade == 1:
                    registro.append(1)
                elif servidor.nacionalidade in (2, 3):
                    registro.append(2)
                else:
                    registro.append(3)

                # 9	País de origem		3	Fixo	Alfanumérico	Obrigatório
                registro.append(servidor.pais_origem and servidor.pais_origem.codigo_censup or 'BRA')

                # 10	UF de nascimento		2	Fixo	Numérico	Opcional
                registro.append('')

                # 11	Município de Nascimento		7	Fixo	Númerico	Condicional
                registro.append('')

                # 12	Docente com deficiência, transtorno global do desenvolvimento (TGD)/transtorno do espectro autista (TEA) ou altas habilidades/superdotação		1	Fixo	Numérico	Obrigatório
                # 0 - Não 1 - Sim 2 - Não dispõe da informação
                registro.append(2)

                # 13	Tipo de deficiência cegueira		1	Fixo	Numérico	Condicional
                registro.append('')

                # 14	Tipo de deficiência baixa visão		1	Fixo	Numérico	Condicional
                registro.append('')

                # 15	Tipo de deficiência surdez		1	Fixo	Numérico	Condicional
                registro.append('')

                # 16	Tipo de deficiência auditiva		1	Fixo	Numérico	Condicional
                registro.append('')

                # 17	Tipo de deficiência física		1	Fixo	Numérico	Condicional
                registro.append('')

                # 18	Tipo de deficiência surdocegueira		1	Fixo	Numérico	Condicional
                registro.append('')

                # 19	Tipo de deficiência intelectual		1	Fixo	Numérico	Condicional
                registro.append('')

                # 20 Tipo de deficiência - Transtorno global do desenvolvimento (TGD)/Transtorno do Espectro Autista (TEA)    1    Fixo    Numérico    Condicional
                registro.append('')

                # 21 Tipo de deficiência - Altas habilidades/ superdotação    1    Fixo    Numérico    Condicional
                registro.append('')

                # 22	Escolaridade		1	Fixo	Numérico	Obrigatório
                # 1 - Sem formação de nível superior
                # 3 - Nível superior sem pós graduação
                # 4 - Especialização
                # 5 - Mestrado
                # 6 - Doutorado

                if servidor.professor.titulacao:
                    if servidor.professor.titulacao in ['Graduado', 'Graduada']:
                        registro.append(3)
                    elif servidor.professor.titulacao == 'Especialista':
                        registro.append(4)
                    elif servidor.professor.titulacao in ['Mestre', 'Mestra']:
                        registro.append(5)
                    elif servidor.professor.titulacao in ['Doutor', 'Doutora', 'Pós-Doutor', 'Pós-Doutora']:
                        registro.append(6)
                else:
                    registro.append(1)

                # 23	Situação do Docente na IES		1	Fixo	Numérico	Obrigatório
                # 1 - Esteve em exercício 2 - Afastado para qualificação 3 - Afastado para exercício em outros órgãos/entidades 4 - Afastado por outros motivos 5 - Afastado para tratamento de saúde
                lecionou_diario_graducao_presencial = (
                    diarios_graducao_presenciais.filter(professordiario__professor__vinculo__pessoa__id=servidor.pessoa_fisica.id).exists() and 1 or 0
                )
                lecionou_diario_graducao_ead = diarios_graducao_ead.filter(professordiario__professor__vinculo__pessoa__id=servidor.pessoa_fisica.id).exists() and 1 or 0
                lecionou_diario_pos_graducao_presencial = (
                    diarios_stricto_sensu_presenciais.filter(professordiario__professor__vinculo__pessoa__id=servidor.pessoa_fisica.id).exists() and 1 or 0
                )
                lecionou_diario_pos_graducao_ead = diarios_stricto_sensu_ead.filter(professordiario__professor__vinculo__pessoa__id=servidor.pessoa_fisica.id).exists() and 1 or 0

                esteve_em_exercicio = lecionou_diario_graducao_presencial or lecionou_diario_graducao_ead

                if esteve_em_exercicio:
                    registro.append(1)
                else:
                    registro.append(4)

                # 24	Docente em exercício em 31/12		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio:
                    dia_31_dez = datetime.date(self.ano, 12, 31)
                    registro.append((servidor.data_fim_servico_na_instituicao is None or servidor.data_fim_servico_na_instituicao > dia_31_dez) and 1 or 0)
                else:
                    registro.append('')

                # 25	Regime de trabalho		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio:
                    if servidor.jornada_trabalho.nome == 'DEDICACAO EXCLUSIVA':
                        registro.append(1)
                    elif servidor.jornada_trabalho.nome == '40 HORAS SEMANAIS':
                        registro.append(2)
                    else:
                        registro.append(3)
                else:
                    registro.append('')

                # 26	Docente substituto		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio:
                    registro.append(servidor.pk in professores_substitutos and 1 or 0)
                else:
                    registro.append('')

                # 27	Docente Visitante		1	 Fixo	Numerico	Condicional
                professor_visitante = servidor.pk in professores_visitantes
                if esteve_em_exercicio:
                    registro.append(professor_visitante and 1 or 0)
                else:
                    registro.append('')

                # 28	Tipo de vínculo de docente visitante à IES		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio and professor_visitante:
                    registro.append(servidor.pk in professores_bolsistas and 2 or 1)
                else:
                    registro.append('')

                # 29	"Atuação do Docente - Ensino em curso sequencial de formação específica"		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio:
                    registro.append(0)
                else:
                    registro.append('')

                # 30	"Atuação do Docente - Ensino em curso de graduação presencial"		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio:
                    registro.append(lecionou_diario_graducao_presencial)
                else:
                    registro.append('')

                # 31	"Atuação do Docente - Ensino em curso de graduação a distância"		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio:
                    registro.append(lecionou_diario_graducao_ead)
                else:
                    registro.append('')

                # 32	"Atuação do Docente - Ensino de pós-graduação stricto sensu presencial"		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio:
                    registro.append(lecionou_diario_pos_graducao_presencial)
                else:
                    registro.append('')

                # 33	"Atuação do Docente - Ensino de pós-graduação stricto sensu a distância"		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio:
                    registro.append(lecionou_diario_pos_graducao_ead)
                else:
                    registro.append('')

                # 34	"Atuação do Docente - Pesquisa"		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio:
                    registro.append(servidor.pk in professores_pesquisa and 1 or 0)
                else:
                    registro.append('')

                # 35	"Atuação do Docente - Extensão"		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio:
                    registro.append(servidor.pk in professores_extensao and 1 or 0)
                else:
                    registro.append('')

                # 36	"Atuação do Docente - Gestão, planejamento e avaliação"		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio:
                    registro.append(servidor.pk in professores_gestores and 1 or 0)
                else:
                    registro.append('')

                # 37	Bolsa Pesquisa		1	Fixo	Numérico	Condicional
                if esteve_em_exercicio and servidor.pk in professores_pesquisa:
                    registro.append(servidor.pk in professores_pesquisa_bolsitas and 1 or 0)
                else:
                    registro.append('')
                self.adicionar(registro)
                if esteve_em_exercicio:
                    for codigo_censup in (
                        diarios_graducao_presenciais.filter(professordiario__professor__vinculo__pessoa__id=servidor.pessoa_fisica.id)
                        .values_list('turma__curso_campus__codigo_censup', flat=True)
                        .order_by('turma__curso_campus__codigo_censup')
                        .distinct()
                    ):

                        registro32 = list()
                        # 1 Tipo do registro
                        registro32.append(32)

                        # 2 Código do curso no INEP
                        registro32.append(codigo_censup)

                        self.adicionar(registro32)
                    if lecionou_diario_graducao_ead:
                        for codigo_censup in (
                            diarios_graducao_ead.filter(professordiario__professor__vinculo__pessoa__id=servidor.pessoa_fisica.id).values_list('turma__curso_campus__codigo_censup', flat=True).order_by('turma__curso_campus__codigo_censup').distinct()
                        ):
                            registro32 = list()

                            # 1 Tipo do registro
                            registro32.append(32)

                            # 2 Código do curso no INEP
                            registro32.append(codigo_censup)

                            self.adicionar(registro32)

            output = tempfile.NamedTemporaryFile(mode='w', dir=os.path.join(settings.TEMP_DIR), delete=False, suffix='.txt')
            output.write(str(self))
            output.close()
            self.task.finalize('Arquivo gerado com sucesso', '/edu/relatorio_censup/', file_path=output.name)

    def exportar_alunos(self):
        from estagios.models import PraticaProfissional
        from pesquisa.models import Projeto as ProjetoPesquisa, TipoVinculo
        from projetos.models import Projeto as ProjetoExtensao
        from ae.models import ParticipacaoAlimentacao, ParticipacaoTrabalho, ParticipacaoPasseEstudantil, Caracterizacao
        registro = list()

        # 1    Tipo de registro
        registro.append(40)

        # 2    ID da IES no INEP
        registro.append(1082)

        self.adicionar(registro)

        # Alunos que participaram de projetos de extensão no ano de referência
        projetos_extensao = ProjetoExtensao.objects.filter(aprovado=True)
        projetos_extensao = (
            projetos_extensao.filter(inicio_execucao__year=self.ano)
            | projetos_extensao.filter(fim_execucao__year=self.ano)
            | projetos_extensao.filter(inicio_execucao__year__lt=self.ano, fim_execucao__year__gt=self.ano)
        )
        alunos_extensao = projetos_extensao.values_list('participacao__vinculo_pessoa', flat=True).order_by('participacao__vinculo_pessoa').distinct()
        alunos_extensao_bolsitas = (
            alunos_extensao.filter(participacao__vinculo=TipoVinculo.BOLSISTA).values_list('participacao__vinculo_pessoa', flat=True).order_by('participacao__vinculo_pessoa').distinct()
        )

        # Aluno que participaram de projetos de pesquisa no ano de referência
        projetos_pesquisa = ProjetoPesquisa.objects.filter(aprovado=True)
        projetos_pesquisa = (
            projetos_pesquisa.filter(inicio_execucao__year=self.ano)
            | projetos_pesquisa.filter(fim_execucao__year=self.ano)
            | projetos_pesquisa.filter(inicio_execucao__year__lt=self.ano, fim_execucao__year__gt=self.ano)
        )
        alunos_pesquisa = projetos_pesquisa.values_list('participacao__vinculo_pessoa', flat=True).order_by('participacao__vinculo_pessoa').distinct()
        alunos_pesquisa_bolsitas = (
            projetos_pesquisa.filter(participacao__vinculo=TipoVinculo.BOLSISTA).values_list('participacao__vinculo_pessoa', flat=True).order_by('participacao__vinculo_pessoa').distinct()
        )

        # Alunos estagiários
        qs_pratica_profissional = PraticaProfissional.objects.filter(obrigatorio=False, tipo=PraticaProfissional.TIPO_ESTAGIO)
        qs_pratica_profissional = (
            qs_pratica_profissional.filter(data_inicio__year=self.ano)
            | qs_pratica_profissional.filter(data_fim__year=self.ano)
            | qs_pratica_profissional.filter(data_inicio__year__lt=self.ano, data_fim__year__gt=self.ano)
        )
        alunos_estagiarios = qs_pratica_profissional.values_list('aluno', flat=True).order_by('aluno').distinct()
        alunos_estagiarios_remunerados = qs_pratica_profissional.filter(remunerada=True).values_list('aluno', flat=True).order_by('aluno').distinct()

        alunos = Aluno.objects.filter(matriz__isnull=False, curso_campus__modalidade__nivel_ensino=NivelEnsino.GRADUACAO, matriculaperiodo__ano_letivo__ano=self.ano, ano_letivo__ano__lte=self.ano,).distinct()

        if self.uos:
            alunos = alunos.filter(curso_campus__diretoria__setor__uo__in=self.uos)

        if self.cpfs:
            alunos = alunos.filter(pessoa_fisica__cpf__in=self.cpfs)

        if self.amostra:
            alunos = alunos.order_by('pessoa_fisica__cpf', '-pk')[0:10]
        else:
            alunos = alunos.order_by('pessoa_fisica__cpf', '-pk')

        if self.tipo == Exportador.ALUNOS:
            ultimo_cpf = None
            for aluno in self.task.iterate(alunos):
                if aluno.pessoa_fisica.cpf in self.ignorar_cpfs:
                    continue
                if aluno.dt_conclusao_curso and aluno.dt_conclusao_curso.year != self.ano:
                    continue
                cpf = aluno.pessoa_fisica.cpf.replace('.', '').replace('-', '')
                if cpf != ultimo_cpf:
                    ultimo_cpf = cpf
                    registro = list()

                    dados_rf = aluno.get_dados_receita_federal(self.cpf_operador)

                    # 1	Tipo de registro	2	Fixo	Numérico	Obrigatório
                    registro.append(41)

                    # 2	ID do aluno no INEP	12	Fixo	Numérico	Opcional
                    registro.append('')

                    # 3	Nome	120	Variável	Alfanumérico	Obrigatório
                    # registro.append(to_ascii(aluno.pessoa_fisica.nome_registro.upper()))
                    registro.append(to_ascii(dados_rf['Nome'].upper()))

                    # 4	CPF	11	Fixo	Alfanumérico	Obrigatório
                    registro.append(cpf)

                    # 5	Documento de estrangeiro ou passaporte	20	Variável	Alfanumérico	Condicional
                    if aluno.nacionalidade == 'Estrangeira':
                        registro.append(aluno.passaporte)
                    else:
                        registro.append('')

                    # 6 Data de Nascimento	8	Fixo	Data	Obrigatório
                    # registro.append(aluno.pessoa_fisica.nascimento_data.strftime('%d%m%Y'))
                    registro.append(f"{dados_rf['DataNascimento'][6:8]}/{dados_rf['DataNascimento'][4:6]}/{dados_rf['DataNascimento'][0:4]}")

                    # 7	Cor/Raça	1	Fixo	Numérico	Obrigatório
                    raca = ''
                    if aluno.pessoa_fisica.raca_id:
                        raca = aluno.pessoa_fisica.raca.codigo_censup or ''
                    if not raca:
                        try:
                            raca = aluno.caracterizacao.raca_id and aluno.caracterizacao.raca.codigo_censup or ''
                        except Caracterizacao.DoesNotExist:
                            pass
                    registro.append(raca or '6')

                    # 8	Nacionalidade	1	Fixo	Numérico	Obrigatório
                    if aluno.nacionalidade == 'Estrangeira':
                        registro.append(3)
                    elif aluno.nacionalidade == 'Brasileira - Nascido no exterior ou naturalizado':
                        registro.append(2)
                    else:
                        registro.append(1)

                    # 9	UF de nascimento	2	Fixo	Numérico	Condicional
                    registro.append('')

                    # 10	Município de nascimento	7	Fixo	Numérico	Condicional
                    registro.append('')

                    # 11	País de origem	3	Fixo	Alfanumérico	Obrigatório
                    if aluno.nacionalidade == 'Brasileira' or not aluno.pais_origem_id:
                        registro.append('BRA')
                    else:
                        registro.append(aluno.pais_origem.sigla)

                    # 12	Aluno com deficiência, transtorno global do desenvolvimento ou altas habilidades/superdotação	1	Fixo	Numérico	Obrigatório
                    possui_necessidade_especial = aluno.tipo_necessidade_especial or aluno.tipo_transtorno or aluno.superdotacao
                    if possui_necessidade_especial:
                        registro.append(1)
                    else:
                        registro.append(2)

                    # 13	Tipo de deficiência - Cegueira	1	Fixo	Numérico	Condicional
                    if Aluno.DEFICIENCIA_VISUAL_TOTAL == aluno.tipo_necessidade_especial:
                        registro.append(1)
                    else:
                        registro.append(possui_necessidade_especial and '0' or '')

                    # 14	Tipo de deficiência - Baixa visão	1	Fixo	Numérico	Condicional
                    if Aluno.DEFICIENCIA_VISUAL == aluno.tipo_necessidade_especial:
                        registro.append(1)
                    else:
                        registro.append(possui_necessidade_especial and '0' or '')

                    # 15	Tipo de deficiência - Surdez	1	Fixo	Numérico	Condicional
                    if Aluno.DEFICIENCIA_AUDITIVA_TOTAL == aluno.tipo_necessidade_especial:
                        registro.append(1)
                    else:
                        registro.append(possui_necessidade_especial and '0' or '')

                    # 16	Tipo de deficiência - auditiva	1	Fixo	Numérico	Condicional
                    if Aluno.DEFICIENCIA_AUDITIVA == aluno.tipo_necessidade_especial:
                        registro.append(1)
                    else:
                        registro.append(possui_necessidade_especial and '0' or '')

                    # 17	Tipo de deficiência - física	1	Fixo	Numérico	Condicional
                    if Aluno.DEFICIENCIA_FISICA == aluno.tipo_necessidade_especial:
                        registro.append(1)
                    else:
                        registro.append(possui_necessidade_especial and '0' or '')

                    # 18	Tipo de deficiência - Surdocegueira	1	Fixo	Numérico	Condicional
                    if Aluno.DEFICIENCIA_AUDITIVA_VISUAL_TOTAL == aluno.tipo_necessidade_especial:
                        registro.append(1)
                    else:
                        registro.append(possui_necessidade_especial and '0' or '')

                    # 19	Tipo de deficiência - Intelectual	1	Fixo	Numérico	Condicional
                    if Aluno.DEFICIENCIA_MENTAL == aluno.tipo_necessidade_especial:
                        registro.append(1)
                    else:
                        registro.append(possui_necessidade_especial and '0' or '')

                    # 20    Tipo de deficiência - Transtorno global do desenvolvimento (TGD)/Transtorno do Espectro Autista (TEA)    1    Fixo    Numérico    Condicional
                    if aluno.tipo_transtorno in [Aluno.AUTISMO_INFANTIL, Aluno.SINDROME_ASPERGER, Aluno.SINDROME_DE_RETT, Aluno.TRANSTORNO_DESINTEGRATIVO_DA_INFANCIA]:
                        registro.append(1)
                    else:
                        registro.append(possui_necessidade_especial and '0' or '')

                    # 21	Tipo de deficiência - Altas habilidades/ superdotação	1	Fixo	Numérico	Condicional
                    if aluno.superdotacao:
                        registro.append(1)
                    else:
                        registro.append(possui_necessidade_especial and '0' or '')

                    # 22    Tipo de escola que concluiu o Ensino Médio    1    Fixo    Numérico    Obrigatório
                    if aluno.tipo_instituicao_origem == 'Privada':
                        registro.append(0)
                    elif aluno.tipo_instituicao_origem == 'Pública':
                        registro.append(1)
                    else:
                        registro.append(2)

                    self.adicionar(registro)
                qs_matricula_periodo = aluno.matriculaperiodo_set.filter(ano_letivo__ano=self.ano)

                if self.uos:
                    qs_matricula_periodo = qs_matricula_periodo.filter(aluno__curso_campus__diretoria__setor__uo__in=self.uos)

                lista = []
                for mp in qs_matricula_periodo.order_by('-periodo_letivo'):
                    if mp.aluno.curso_campus.codigo_censup in lista:
                        continue
                    lista.append(mp.aluno.curso_campus.codigo_censup)
                    registro = list()

                    # 1	Tipo de registro	2	Fixo	Numérico	Obrigatório
                    registro.append(42)

                    # 2    ID na IES - Identificação única do aluno na IES    20    Variável    Alfanumérico    Opcional
                    registro.append('')

                    # 3	Período de referência	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 4	Código do Curso	12	Variável	Numérico	Obrigatório
                    registro.append(mp.aluno.curso_campus.codigo_censup)

                    # 5	Código do pólo do curso a distância 	12	Variável	Numérico (tabela)	Condicional
                    if mp.aluno.curso_campus.diretoria.ead and mp.aluno.polo_id:
                        registro.append(mp.aluno.polo.codigo_censup)
                    else:
                        registro.append('')

                    # 6	Turno do aluno	1	Fixo	Numérico	Condicional
                    if not mp.aluno.curso_campus.diretoria.ead:
                        if mp.aluno.turno_id == 3:  # Matutino
                            registro.append(1)
                        elif mp.aluno.turno_id == 2:  # Vespertino
                            registro.append(2)
                        elif mp.aluno.turno_id == 1:  # Noturno
                            registro.append(3)
                        else:
                            registro.append(4)
                    else:
                        registro.append('')

                    # 7	Situação de vínculo do aluno ao curso	1	Fixo	Numérico 	Obrigatório
                    ch_prevista = mp.aluno.matriz.get_carga_horaria_total_prevista()
                    ch_cumprida = mp.aluno.get_ch_componentes_cumpridos(True, ano=self.ano) + mp.aluno.get_ch_atividades_complementares_cumprida(ano=self.ano)
                    is_formado = mp.aluno.dt_conclusao_curso and mp.aluno.dt_conclusao_curso.year == self.ano
                    id_situacao_censup = ''
                    if (
                        ch_prevista <= ch_cumprida
                        and not mp.aluno.pendencia_tcc
                        and not mp.aluno.pendencia_pratica_profissional
                        and not mp.aluno.pendencia_ch_atividade_complementar
                        and not mp.aluno.pendencia_ch_tcc
                        and not mp.aluno.pendencia_ch_pratica_profissional
                        and not mp.aluno.pendencia_ch_seminario
                        and not mp.aluno.pendencia_ch_eletiva
                        and not mp.aluno.pendencia_ch_optativa
                        and not mp.aluno.pendencia_ch_obrigatoria
                    ):
                        is_formado = True
                        id_situacao_censup = 6
                    elif mp.aluno.situacao.pk == SituacaoMatricula.FALECIDO:
                        id_situacao_censup = 7
                    else:
                        situacao_censup = mp.get_situacao_censup()
                        if situacao_censup == 'Formado':
                            id_situacao_censup = 6
                        elif situacao_censup == 'Cursando':
                            id_situacao_censup = 2
                        elif situacao_censup == 'Matrícula Trancada':
                            id_situacao_censup = 3
                        elif situacao_censup == 'Transferido para outro curso da mesma IES':
                            id_situacao_censup = 5
                        elif situacao_censup == 'Desvinculado do Curso':
                            id_situacao_censup = 4

                    if not is_formado and id_situacao_censup == 6:
                        # se aluno não está formado no ano do censup então não será adicionado
                        continue

                    registro.append(id_situacao_censup)

                    if ch_cumprida > ch_prevista:
                        ch_cumprida = ch_prevista
                        if not is_formado:
                            ch_cumprida = ch_cumprida - 30

                    # 8	Curso origem	12	Variável	Numérico	Condicional
                    semestre_ingresso = '0{}{}'.format(mp.aluno.periodo_letivo, mp.aluno.ano_letivo.ano)
                    qs_curso_origem = (
                        Aluno.objects.exclude(pk=mp.aluno.pk)
                        .exclude(curso_campus__codigo_censup=mp.aluno.curso_campus.codigo_censup)
                        .filter(
                            pessoa_fisica__cpf=mp.aluno.pessoa_fisica.cpf, curso_campus__modalidade=mp.aluno.curso_campus.modalidade, situacao=SituacaoMatricula.TRANSFERIDO_INTERNO
                        )
                        .filter(matriculaperiodo__ano_letivo__ano=self.ano)
                        .order_by('-ano_letivo__ano')
                    )
                    qs_matriz_origem = (
                        Aluno.objects.exclude(pk=mp.aluno.pk)
                        .filter(curso_campus__codigo_censup=mp.aluno.curso_campus.codigo_censup)
                        .filter(
                            pessoa_fisica__cpf=mp.aluno.pessoa_fisica.cpf, curso_campus__modalidade=mp.aluno.curso_campus.modalidade, situacao=SituacaoMatricula.TRANSFERIDO_INTERNO
                        )
                        .filter(matriculaperiodo__ano_letivo__ano=self.ano)
                        .order_by('-ano_letivo__ano')
                    )
                    if qs_curso_origem.exists() and (mp.aluno.forma_ingresso_id and 'transf' in mp.aluno.forma_ingresso.descricao.lower()):
                        registro.append(qs_curso_origem[0].curso_campus.codigo_censup)
                    else:
                        registro.append('')

                    if qs_matriz_origem.exists():
                        semestre_ingresso = '0{}{}'.format(qs_matriz_origem[0].periodo_letivo, qs_matriz_origem[0].ano_letivo.ano)

                    # 9	Semestre de conclusão do curso	1	Fixo	Numérico	Condicional
                    if is_formado:
                        registro.append(mp.periodo_letivo)
                    else:
                        registro.append('')

                    # 10	Aluno PARFOR	1	Fixo	Numérico	Condicional
                    if mp.aluno.curso_campus.modalidade.pk == Modalidade.LICENCIATURA:
                        if mp.aluno.convenio_id and mp.aluno.convenio.descricao == 'PARFOR':
                            registro.append(1)
                        else:
                            registro.append(0)
                    else:
                        registro.append('')

                    # 11 Segunda Licenciatura / Formação pedagógica    1 Fixo Numérico Condicional
                    registro.append(mp.aluno.curso_campus.modalidade.pk == Modalidade.LICENCIATURA and '0' or '')

                    # 12 Tipo - Segunda Licenciatura / Formação pedagógica    1 Fixo Numérico Condicional
                    registro.append('')

                    # 13	Semestre de ingresso no curso	6	Fixo	Numérico	Obrigatório
                    registro.append(semestre_ingresso)

                    # 14	"Forma de ingresso/seleção  - Vestibular"	1	Fixo	Numérico	Obrigatório
                    registro.append(mp.aluno.forma_ingresso.classificacao_censup == FormaIngresso.VESTIBULAR and 1 or 0)

                    # 15	"Forma de ingresso/seleção  - Enem"	1	Fixo	Numérico	Obrigatório
                    registro.append(mp.aluno.forma_ingresso.classificacao_censup == FormaIngresso.ENEM and 1 or 0)

                    # 16	"Forma de ingresso/seleção  - Avaliação Seriada"	1	Fixo	Numérico	Obrigatório
                    registro.append(mp.aluno.forma_ingresso.classificacao_censup == FormaIngresso.AVALIACAO_SERIADA and 1 or 0)

                    # 17	"Forma de ingresso/seleção  - Seleção Simplificada"	1	Fixo	Numérico	Obrigatório
                    registro.append(mp.aluno.forma_ingresso.classificacao_censup == FormaIngresso.SELECAO_SIMPLIFICADA and 1 or 0)

                    # 18	"Forma de ingresso/seleção  - Egresso BI/LI"	1	Fixo	Numérico	Obrigatório
                    registro.append(0)

                    # 19	"Forma de ingresso/seleção  - PEC-G"	1	Fixo	Numérico	Condicional
                    registro.append(mp.aluno.forma_ingresso.classificacao_censup == FormaIngresso.PEC_G and 1 or 0)

                    # 20	"Forma de ingresso/seleção  - Transferência Ex Officio"	1	Fixo	Numérico	Obrigatório
                    registro.append(mp.aluno.forma_ingresso.classificacao_censup == FormaIngresso.TRANSFERENCIA_EX_OFICIO and 1 or 0)

                    # 21	"Forma de ingresso/seleção  - Decisão judicial"	1	Fixo	Numérico	Obrigatório
                    registro.append(mp.aluno.forma_ingresso.classificacao_censup == FormaIngresso.DECISAO_JUDICIAL and 1 or 0)

                    # 22	"Forma de ingresso  - Seleção para Vagas Remanescentes"	1	Fixo	Numérico	Obrigatório
                    registro.append(mp.aluno.forma_ingresso.classificacao_censup == FormaIngresso.VAGAS_REMANESCENTES and 1 or 0)

                    # 23	"Forma de ingresso  - Seleção para Vagas de Programas Especiais"	1	Fixo	Numérico	Obrigatório
                    registro.append(mp.aluno.forma_ingresso.classificacao_censup == FormaIngresso.PROGRAMAS_ESPECIAIS and 1 or 0)

                    # 24	Mobilidade acadêmica	1	Fixo	Numérico	Condicional
                    is_aluno_intercambista = mp.situacao == SituacaoMatriculaPeriodo.INTERCAMBIO and 1 or 0
                    registro.append(is_aluno_intercambista)

                    # 25	Tipo de mobilidade acadêmica	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 26	Mobilidade acadêmica Nacional - IES destino	12	Variável	Numérico	Condicional
                    registro.append('')

                    # 27	Mobilidade acadêmica Internacional - País destino	3	Fixo	Alfanumérico	Condicional
                    registro.append('')

                    # 28	Programa de reserva de vagas	1	Fixo	Numérico	Obrigatório
                    is_aluno_reserva_vaga = (
                        mp.aluno.forma_ingresso.programa_vaga_etinico
                        | mp.aluno.forma_ingresso.programa_vaga_pessoa_deficiencia
                        | mp.aluno.forma_ingresso.programa_vaga_escola_publica
                        | mp.aluno.forma_ingresso.programa_vaga_social
                        | mp.aluno.forma_ingresso.programa_vaga_outros
                    )
                    registro.append(is_aluno_reserva_vaga and 1 or 0)

                    # 29	"Programa de reserva de vagas/açoes afirmativas - Etnico"	1	Fixo	Numérico	Condicional
                    if is_aluno_reserva_vaga:
                        registro.append(mp.aluno.forma_ingresso.programa_vaga_etinico and 1 or 0)
                    else:
                        registro.append('')

                    # 30	"Programa de reserva de vagas/ações afirmativas - Pessoa com deficiência"	1	Fixo	Numérico	Condicional
                    if is_aluno_reserva_vaga:
                        registro.append(mp.aluno.forma_ingresso.programa_vaga_pessoa_deficiencia and 1 or 0)
                    else:
                        registro.append('')

                    # 31	"Programa de reserva de vagas - Estudante procedente de escola pública"	1	Fixo	Numérico	Condicional
                    if is_aluno_reserva_vaga:
                        registro.append(mp.aluno.forma_ingresso.programa_vaga_escola_publica and 1 or 0)
                    else:
                        registro.append('')

                    # 32	"Programa de reserva de vagas/ações afirmativas - Social/renda familiar"	1	Fixo	Numérico	Condicional
                    if is_aluno_reserva_vaga:
                        registro.append(mp.aluno.forma_ingresso.programa_vaga_social and 1 or 0)
                    else:
                        registro.append('')

                    # 33	"Programa de reserva de vagas/ações afirmativas - Outros"	1	Fixo	Numérico	Condicional
                    if is_aluno_reserva_vaga:
                        registro.append(mp.aluno.forma_ingresso.programa_vaga_outros and 1 or 0)
                    else:
                        registro.append('')

                    # 34	Financiamento estudantil	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 35	"Financiamento Estudantil Reembolsável - FIES"	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 36	"Financiamento Estudantil Reembolsável - Governo Estadual"	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 37	"Financiamento Estudantil Reembolsável -Governo Municipal"	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 38	"Financiamento Estudantil Reembolsável  - IES"	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 39	"Financiamento Estudantil Reembolsável - Entidades externas"	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 40	"Tipo de financiamento não reembolsável - ProUni integral"	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 41	"Tipo de financiamento não reembolsável - ProUni parcial"	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 42	"Tipo de financiamento não reembolsável - Entidades externas"	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 43	"Tipo de financiamento não reembolsável - Governo estadual"	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 44	"Tipo de financiamento não reembolsável - IES"	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 45	"Tipo de financiamento não reembolsável - Governo municipal"	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 46	Apoio Social	1	Fixo	Numérico	Obrigatório
                    qs_alimentacao = ParticipacaoAlimentacao.objects.filter(participacao__aluno=mp.aluno)
                    qs_bolsa = ParticipacaoTrabalho.objects.filter(participacao__aluno=mp.aluno)
                    qs_transporte = ParticipacaoPasseEstudantil.objects.filter(participacao__aluno=mp.aluno)
                    possui_apoio_social = qs_alimentacao.exists() or qs_bolsa.exists() or qs_transporte.exists()
                    registro.append(possui_apoio_social and 1 or 0)

                    # 47	"Tipo de apoio social - Alimentação"	1	Fixo	Numérico	Condicional
                    if possui_apoio_social:
                        registro.append(qs_alimentacao.exists() and 1 or 0)
                    else:
                        registro.append('')

                    # 48	"Tipo de apoio social - Moradia"	1	Fixo	Numérico	Condicional
                    if possui_apoio_social:
                        registro.append(0)
                    else:
                        registro.append('')

                    # 49	"Tipo de apoio social - Transporte"	1	Fixo	Numérico	Condicional
                    if possui_apoio_social:
                        registro.append(qs_transporte.exists() and 1 or 0)
                    else:
                        registro.append('')

                    # 50	"Tipo de apoio social - Material didático"	1	Fixo	Numérico	Condicional
                    if possui_apoio_social:
                        registro.append(0)
                    else:
                        registro.append('')

                    # 51	"Tipo de apoio social - Bolsa trabalho"	1	Fixo	Numérico	Condicional
                    if possui_apoio_social:
                        registro.append(qs_bolsa.exists() and 1 or 0)
                    else:
                        registro.append('')

                    # 52	"Tipo de apoio social - Bolsa permanência"	1	Fixo	Numérico	Condicional
                    if possui_apoio_social:
                        registro.append(0)
                    else:
                        registro.append('')

                    # 53	Atividade extracurricular	1	Fixo	Numérico	Obrigatório
                    is_aluno_pesquisa = mp.aluno.pessoa_fisica.pk in alunos_pesquisa
                    is_bolsista_pesquisa = mp.aluno.pessoa_fisica.pk in alunos_pesquisa_bolsitas
                    is_aluno_extensao = mp.aluno.pessoa_fisica.pk in alunos_extensao
                    is_bolsista_extensao = mp.aluno.pessoa_fisica.pk in alunos_extensao_bolsitas
                    is_aluno_estagiario = mp.aluno.pk in alunos_estagiarios
                    if is_aluno_pesquisa or is_aluno_extensao or is_aluno_estagiario:
                        registro.append(1)
                    else:
                        registro.append(0)

                    # 54	"Atividade extracurricular - Pesquisa"	1	Fixo	Numérico	Condicional
                    if is_aluno_pesquisa or is_aluno_extensao or is_aluno_estagiario:
                        registro.append(is_aluno_pesquisa and 1 or 0)
                    else:
                        registro.append('')

                    # 55	"Bolsa/remuneração referente à atividade extracurricular - Pesquisa"	1	Fixo	Numérico	Condicional
                    if is_aluno_pesquisa:
                        registro.append(is_bolsista_pesquisa and 1 or 0)
                    else:
                        registro.append('')

                    # 56	"Atividade extracurricular - Extensão"	1	Fixo	Numérico	Condicional
                    if is_aluno_pesquisa or is_aluno_extensao or is_aluno_estagiario:
                        registro.append(is_aluno_extensao and 1 or 0)
                    else:
                        registro.append('')

                    # 57	"Bolsa/remuneração referente à atividade extracurricular - Extensão"	1	Fixo	Numérico	Condicional
                    if is_aluno_extensao:
                        registro.append(is_bolsista_extensao and 1 or 0)
                    else:
                        registro.append('')

                    # 58	"Atividade extracurricular - Monitoria"	1	Fixo	Numérico	Condicional
                    if is_aluno_pesquisa or is_aluno_extensao or is_aluno_estagiario:
                        registro.append(0)
                    else:
                        registro.append('')

                    # 59	"Bolsa/remuneração referente à atividade extracurricular - Monitoria"	1	Fixo	Numérico	Condicional
                    registro.append('')

                    # 60	"Atividade extracurricular - Estágio não obrigatório"	1	Fixo	Numérico	Condicional
                    if is_aluno_pesquisa or is_aluno_extensao or is_aluno_estagiario:
                        if is_aluno_estagiario:
                            registro.append(1)
                        else:
                            registro.append(0)
                    else:
                        registro.append('')

                    # 61	"Bolsa/remuneração referente à atividade extracurricular - Estágio não obrigatório"	1	Fixo	Numérico	Condicional
                    if is_aluno_pesquisa or is_aluno_extensao or is_aluno_estagiario:
                        if is_aluno_estagiario:
                            registro.append(mp.aluno.pk in alunos_estagiarios_remunerados and 1 or 0)
                        else:
                            registro.append('')
                    else:
                        registro.append('')

                    # 62	Carga horária total do curso por aluno	5	Variável	Numérico	Obrigatório
                    registro.append(ch_prevista)

                    # 63	Carga horária integralizada pelo aluno	5	Variável	Numérico	Obrigatório
                    registro.append(ch_cumprida)

                    # 64    Justificativa    2    Fixo    Numérico    Condicional
                    registro.append('')

                    self.adicionar(registro)

            output = tempfile.NamedTemporaryFile(mode='w', dir=settings.TEMP_DIR, delete=False, suffix='.txt')
            output.write(str(self))
            output.close()
            self.task.finalize('Arquivo gerado com sucesso', '/edu/relatorio_censup/', file_path=output.name)
