import os
from django.conf import settings
from comum.models import Configuracao
from djtools.utils import to_ascii
from edu.models import RespostaEducacenso
from edu.models.alunos import Aluno
from edu.models.cadastros_gerais import Estado, Cidade, SituacaoMatricula, SituacaoMatriculaPeriodo
from edu.models.cadastros_gerais import Modalidade
from edu.models.cursos import ComponenteCurricular
from edu.models.diarios import ProfessorDiario
from edu.models.diretorias import Diretoria, CalendarioAcademico
from edu.models.professores import Professor
from edu.models.turmas import Turma
from rh.models import Servidor
from rh.models import UnidadeOrganizacional

MODALIDADES = (Modalidade.INTEGRADO, Modalidade.SUBSEQUENTE, Modalidade.INTEGRADO_EJA, Modalidade.PROEJA_FIC_FUNDAMENTAL, Modalidade.CONCOMITANTE)


def formatar(texto, remover_virgula=False):
    if texto is None:
        texto = ''
    for caractere in ('\'', '"', '-', '.', 'ª', 'º', ':', '&', ')', '(', '*', '=', ';', ':', '+', ']', '[', '}', '{'):
        texto = texto.replace(caractere, '')
    if remover_virgula:
        texto = texto.replace(',', '')
    texto = texto.replace('  ', ' ')
    return to_ascii(texto).upper()


class ExportadorAlunosSemCodigo:
    def __init__(self, ano, task):
        self.ano = ano
        self.registros = []

        pks = (
            Turma.objects.filter(
                curso_campus__modalidade__in=MODALIDADES,
                ano_letivo__ano=self.ano,
                diario__matriculadiario__isnull=False,
                diario__matriculadiario__matricula_periodo__aluno__codigo_educacenso__isnull=True,
            )
            .values_list('diario__matriculadiario__matricula_periodo__aluno', flat=True)
            .order_by('diario__matriculadiario__matricula_periodo__aluno')
            .distinct()
        )
        alunos = Aluno.objects.filter(pk__in=pks)
        alunos = alunos.exclude(naturalidade__isnull=True)

        for aluno in task.iterate(alunos):
            cpf_aluno = str(aluno.pessoa_fisica.cpf).replace('.', '').replace('-', '')
            cpf_aluno = str(int(cpf_aluno))
            cpf_aluno = cpf_aluno.rjust(11, '0')
            self.registros.append(
                '%s|%s||%s|%s|%s|%s|%s|'
                % (
                    aluno.matricula,
                    cpf_aluno,
                    formatar(aluno.pessoa_fisica.nome),
                    aluno.pessoa_fisica.nascimento_data.strftime('%d/%m/%Y'),
                    formatar(aluno.nome_mae or aluno.pessoa_fisica.nome_mae or ''),
                    formatar(aluno.nome_pai or aluno.pessoa_fisica.nome_pai or ''),
                    aluno.naturalidade_id and aluno.naturalidade.codigo or '',
                )
            )
        file_path = os.path.join(settings.TEMP_DIR, 'alunos_sem_codigo.txt')
        f = open(file_path, 'w')
        f.write(str('\r\n'.join(self.registros)))
        f.close()
        task.finalize('Arquivo gerado com sucesso', '/', file_path=file_path)


class Exportador:
    DOCENTE = 1
    ALUNOS = 2

    def __init__(self, ano, uo, ignorar_erros, task):
        self.ano = ano
        self.uo = uo
        self.ignorar_erros = ignorar_erros
        self.registros = []
        self.cpf_operador = task.user and task.user.get_vinculo().pessoa.pessoafisica.cpf or None
        self.modalidades = MODALIDADES

        self.erros = []

        uos = self.uo and [self.uo] or UnidadeOrganizacional.objects.suap().all()
        dados = []
        for uo in uos:
            alunos = (
                Aluno.objects.filter(
                    curso_campus__modalidade__in=self.modalidades,
                    matriculaperiodo__ano_letivo__ano=self.ano,
                    matriculaperiodo__periodo_letivo=1,
                    curso_campus__diretoria__setor__uo=uo)
                .exclude(situacao=SituacaoMatricula.TRANSFERIDO_INTERNO)
                .order_by('pessoa_fisica__cpf')
                .order_by('-matriculaperiodo')
                .distinct()
            )  # [0:10]

            turmas = Turma.objects.filter(
                curso_campus__modalidade__in=self.modalidades, ano_letivo__ano=ano, periodo_letivo=1, diario__matriculadiario__isnull=False, curso_campus__diretoria__setor__uo=uo
            ).distinct()

            professores = Servidor.objects.filter(
                eh_docente=True,
                pk__in=ProfessorDiario.objects.filter(
                    diario__matriculadiario__isnull=False,
                    diario__turma__curso_campus__modalidade__in=self.modalidades,
                    diario__ano_letivo__ano=self.ano,
                    diario__turma__curso_campus__diretoria__setor__uo=uo,
                )
                .values_list('professor__vinculo__pessoa__pessoafisica', flat=True)
                .distinct(),
            )
            dados.append((uo, alunos, turmas, professores))

        for uo, alunos, turmas, professores in dados:
            task.count(alunos, turmas, professores)

        for uo, alunos, turmas, professores in dados:
            self.exportar_registros_00(uo)
            self.exportar_registros_10(uo)
            self.exportar_registros_20(turmas, task)
            self.exportar_registros_30(professores, turmas, None, task)
            self.exportar_registros_30_alunos(alunos, turmas, task)
            self.exportar_registros_40(professores, uo, task)
            self.exportar_registros_50(professores, turmas, task)
            self.exportar_registros_60(alunos, task)
            self.registros.append('99|')

            file_path = os.path.join(settings.TEMP_DIR, 'educacenso.txt')
            if self.ignorar_erros:
                s = '\r\n'.join(self.registros)
            else:
                s = '\r\n'.join(self.erros)
            with open(file_path, 'w') as f:
                f.write(s)
            task.finalize('Arquivo gerado com sucesso', '/edu/relatorio_educacenso/', file_path=file_path)

    def adicionar(self, registro):
        for i, item in enumerate(registro):
            registro[i] = str(item)
        self.registros.append('|'.join(registro))

    def exportar_registros_00(self, uo):
        siglas = uo.sigla == 'EAD' and (uo.sigla, 'CNAT') or (uo.sigla,)
        diretoria = Diretoria.objects.filter(setor__uo__sigla__in=siglas).first()
        if diretoria:
            calendario_academico = CalendarioAcademico.objects.exclude(descricao__unaccent__icontains='depend').filter(
                diario__turma__curso_campus__diretoria__setor__uo=uo,
                diario__turma__curso_campus__modalidade=Modalidade.INTEGRADO,
                diario__ano_letivo__ano=self.ano,
                diario__componente_curricular__qtd_avaliacoes=4,
            ).first()
            if calendario_academico is None:
                modalidades = (Modalidade.INTEGRADO, Modalidade.SUBSEQUENTE, Modalidade.INTEGRADO_EJA, Modalidade.PROEJA_FIC_FUNDAMENTAL, Modalidade.CONCOMITANTE)
                qs_calendario_academico = CalendarioAcademico.objects.exclude(descricao__unaccent__icontains='depend').filter(diario__turma__curso_campus__diretoria__setor__uo=uo, diario__turma__curso_campus__modalidade__in=modalidades, diario__ano_letivo__ano=self.ano)
                if qs_calendario_academico.exists():
                    from django.db.models import Max, Min
                    inicio = qs_calendario_academico.aggregate(Min('data_inicio'))
                    data_inicio = inicio and inicio['data_inicio__min'] and inicio['data_inicio__min'].strftime('%d/%m/%Y')
                    fim = qs_calendario_academico.aggregate(Max('data_fim'))
                    data_fim = fim and fim['data_fim__max'] and fim['data_fim__max'].strftime('%d/%m/%Y')
            else:
                data_inicio = calendario_academico.data_inicio.strftime('%d/%m/%Y')
                data_fim = calendario_academico.data_fim.strftime('%d/%m/%Y')

            if data_inicio and data_fim:
                if diretoria.diretor_geral_id:
                    registro = list()
                    # 1 Tipo de registro
                    registro.append('00')
                    # 2 Código de escola - Inep
                    registro.append(uo.codigo_inep)
                    # 3 Situação de funcionamento
                    registro.append(1)
                    # 4 Data de início do ano letivo
                    registro.append(data_inicio)
                    # 5 Data de término do ano letivo
                    registro.append(data_fim)
                    # 6 Nome da escola
                    instituicao = Configuracao.get_valor_por_chave('comum', 'instituicao_sigla')
                    registro.append('{} - {}'.format(instituicao, to_ascii(diretoria.setor.uo.nome).upper()))
                    # 7 CEP
                    registro.append(formatar(diretoria.setor.uo.cep and diretoria.setor.uo.cep))
                    # 8 Município
                    estado = Estado.objects.get(pk=Estado.ESTADOS[diretoria.setor.uo.municipio.uf])
                    qs_cidade = Cidade.objects.filter(nome=diretoria.setor.uo.municipio.nome.upper(), estado=estado)
                    registro.append(qs_cidade.exists() and qs_cidade[0].codigo or diretoria.setor.uo.municipio.codigo)
                    # 9 Distrito
                    # registro.append(diretoria.setor.uo.distrito)
                    registro.append('05')
                    # 10 Endereço
                    registro.append(formatar(diretoria.setor.uo.endereco))
                    # 11 Endereço número
                    registro.append('')
                    # 12 Complemento
                    registro.append('')
                    # 13 Bairro
                    registro.append('')
                    # 14 DDD
                    registro.append('')
                    # 15 Telefone
                    registro.append('')
                    # 16 Outro telefone de contato
                    registro.append('')
                    # 17 Endereço eletrônico (e-mail) da escola
                    registro.append('')
                    # 18 Código do órgão regional de ensino
                    registro.append('')
                    # 19 Localização/Zona da escola
                    registro.append(diretoria.setor.uo.zona_rual and 2 or 1)
                    # 20 Localização diferenciada da escola
                    # 1 – Área de assentamento
                    # 2 – Terra indígena
                    # 3 – Área onde se localiza comunidade remanescente de quilombos
                    # 7 – Não está em área de localização diferenciada
                    registro.append(7)
                    # 21 Dependência administrativa
                    registro.append(1)
                    # 22 Secretaria de Educação/Ministério da Educação
                    registro.append(1)
                    # 23 Secretaria de Segurança Pública/Forças Armadas/Militar
                    registro.append(0)
                    # 24 Secretaria da Saúde/Ministério da Saúde
                    registro.append(0)
                    # 25 Outro órgão da administração pública
                    registro.append(0)
                    # 26 Mantenedora da escola privada – Empresa, grupos empresariais do setor privado ou pessoa física.
                    registro.append('')
                    # 27 Mantenedora da escola privada – Sindicatos de trabalhadores ou patronais, associações, cooperativas.
                    registro.append('')
                    # 28 Mantenedora da escola privada – Organização não governamental (ONG) - nacional ou internacional.
                    registro.append('')
                    # 29 Mantenedora da escola privada – Instituições sem fins lucrativos.
                    registro.append('')
                    # 30 Mantenedora da escola privada – Sistema S (Sesi, Senai, Sesc, outros)
                    registro.append('')
                    # 31 Mantenedora da escola privada – Organização da Sociedade Civil de Interesse Público (Oscip)
                    registro.append('')
                    # 32 Categoria da escola privada
                    registro.append('')
                    # 33 Poder público responsável pela parceria ou convênio entre a Administração Pública e outras instituições - Secretaria estadual
                    registro.append(0)
                    # 34 Poder público responsável pela parceria ou convênio entre a Administração Pública e outras instituições - Secretaria Municipal
                    registro.append(0)
                    # 35 Poder público responsável pela parceria ou convênio entre a Administração Pública e outras instituições - Não possui parceria ou convênio
                    registro.append(1)
                    # 36 Formas de contratação entre a Administração Pública e outras instituições - Termo de colaboração (Lei nº 13.019/2014)
                    registro.append('')
                    # 37 Formas de contratação entre a Administração Pública e outras instituições - Termo de fomento (Lei nº 13.019/2014)
                    registro.append('')
                    # 38 Formas de contratação entre a Administração Pública e outras instituições - Acordo de cooperação (Lei nº 13.019/2014)
                    registro.append('')
                    # 39 Formas de contratação entre a Administração Pública e outras instituições - Contrato de prestação de serviço
                    registro.append('')
                    # 40 Formas de contratação entre a Administração Pública e outras instituições - Termo de cooperação técnica e financeira
                    registro.append('')
                    # 41 Formas de contratação entre a Administração Pública e outras instituições - Contrato de consórcio público/Convênio de cooperação
                    registro.append('')
                    # 42 Número de matrículas atendidas por meio da parceria ou convênio - Atividade complementar
                    registro.append('')
                    # 43 Número de matrículas atendidas por meio da parceria ou convênio - Atendimento educacional especializado
                    registro.append('')
                    # 44 Número de matrículas atendidas por meio da parceria ou convênio - Ensino Regular - Creche - Parcial
                    registro.append('')
                    # 45 Número de matrículas atendidas por meio da parceria ou convênio - Ensino Regular - Creche - Integral
                    registro.append('')
                    # 46 Número de matrículas atendidas por meio da parceria ou convênio - Ensino Regular - Pré-escola - Parcial
                    registro.append('')
                    # 47 Número de matrículas atendidas por meio da parceria ou convênio - Ensino Regular - Pré-escola - Integral
                    registro.append('')
                    # 48 Número de matrículas atendidas por meio da parceria ou convênio - Ensino Regular - Ensino Fundamental - Anos Iniciais - Parcial
                    registro.append('')
                    # 49 Número de matrículas atendidas por meio da parceria ou convênio - Ensino Regular - Ensino Fundamental - Anos Iniciais - Integral
                    registro.append('')
                    # 50 Número de matrículas atendidas por meio da parceria ou convênio - Ensino Regular - Ensino Fundamental - Anos Finais - Parcial
                    registro.append('')
                    # 51 Número de matrículas atendidas por meio da parceria ou convênio - Ensino Regular - Ensino Fundamental - Anos Finais - Integral
                    registro.append('')
                    # 52 Número de matrículas atendidas por meio da parceria ou convênio - Ensino Regular - Ensino Médio - Parcial
                    registro.append('')
                    # 53 Número de matrículas atendidas por meio da parceria ou convênio - Ensino Regular - Ensino Médio - Integral
                    registro.append('')
                    # 54 Número de matrículas atendidas por meio da parceria ou convênio - Educação Especial - Classe especial - Parcial
                    registro.append('')
                    # 55 Número de matrículas atendidas por meio da parceria ou convênio - Educação Especial - Classe especial - Integral
                    registro.append('')
                    # 56 Número de matrículas atendidas por meio da parceria ou convênio - Educação de Jovens e Adultos (EJA) - Ensino fundamental
                    registro.append('')
                    # 57 Número de matrículas atendidas por meio da parceria ou convênio - Educação de Jovens e Adultos (EJA) - Ensino médio
                    registro.append('')
                    # 58 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional - Integrada à educação de jovens e adultos no ensino fundamental - Parcial
                    registro.append('')
                    # 59 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional - Integrada à educação de jovens e adultos no ensino fundamental - Integral
                    registro.append('')
                    # 60 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional técnica - Integrada à educação de jovens e adultos de nível médio - Parcial
                    registro.append('')
                    # 61 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional técnica - Integrada à educação de jovens e adultos de nível médio - Integral
                    registro.append('')
                    # 62 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional técnica - Concomitante à educação de jovens e adultos de nível médio - Parcial
                    registro.append('')
                    # 63 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional técnica - Concomitante à educação de jovens e adultos de nível médio - Integral
                    registro.append('')
                    # 64 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional técnica - Concomitante intercomplementar à educação de jovens e adultos de nível médio - Parcial
                    registro.append('')
                    # 65 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional técnica - Concomitante intercomplementar à educação de jovens e adultos de nível médio - Integral
                    registro.append('')
                    # 66 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional técnica - Integrada ao ensino médio - Parcial
                    registro.append('')
                    # 67 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional técnica - Integrada ao ensino médio - Integral
                    registro.append('')
                    # 68 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional técnica - Concomitante ao ensino médio - Parcial
                    registro.append('')
                    # 69 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional técnica - Concomitante ao ensino médio - Integral
                    registro.append('')
                    # 70 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional técnica - Concomitante intercomplementar ao ensino médio - Parcial
                    registro.append('')
                    # 71 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Qualificação profissional técnica - Concomitante intercomplementar ao ensino médio - Integral
                    registro.append('')
                    # 72 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Integrada ao ensino médio - Parcial
                    registro.append('')
                    # 73 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Integrada ao ensino médio - Integral
                    registro.append('')
                    # 74 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Concomitante ao ensino médio - Parcial
                    registro.append('')
                    # 75 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Concomitante ao ensino médio - Integral
                    registro.append('')
                    # 76 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Concomitante intercomplementar ao ensino médio - Parcial
                    registro.append('')
                    # 77 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Concomitante intercomplementar ao ensino médio - Integral
                    registro.append('')
                    # 78 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Subsequente ao ensino médio
                    registro.append('')
                    # 79 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Integrada à educação de jovens e adultos de nível médio - Parcial
                    registro.append('')
                    # 80 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Integrada à educação de jovens e adultos de nível médio - Integral
                    registro.append('')
                    # 81 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Concomitante à educação de jovens e adultos de nível médio - Parcial
                    registro.append('')
                    # 82 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Concomitante à educação de jovens e adultos de nível médio - Integral
                    registro.append('')
                    # 83 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Concomitante intercomplementar à educação de jovens e adultos de nível médio - Parcial
                    registro.append('')
                    # 84 Número de matrículas atendidas por meio da parceria ou convênio - Educação Profissional - Educação profissional técnica de nível médio - Concomitante intercomplementar à educação de jovens e adultos de nível médio - Integral
                    registro.append('')
                    # 85 CNPJ da mantenedora principal da escola privada
                    registro.append('')
                    # 86 CNPJ da escola privada
                    registro.append('')
                    # 87 Regulamentação/Autorização no conselho ou órgão municipal, estadual ou federal de educação.
                    registro.append(1)
                    # 88 Esfera administrativa do conselho ou órgão responsável pela regulamentação/autorização - Federal
                    registro.append(1)
                    # 89 Esfera administrativa do conselho ou órgão responsável pela regulamentação/autorização - Estadual
                    registro.append(0)
                    # 90 Esfera administrativa do conselho ou órgão responsável pela regulamentação/autorização - Municipal
                    registro.append(0)
                    # 91 Unidade vinculada a Escola de Educação Básica ou Unidade ofertante de Ensino Superior
                    registro.append(uo.codigo_censup and 2 or 0)
                    # 92 Código da Escola Sede
                    registro.append('')
                    # 93 Código da IES
                    registro.append(uo.codigo_censup and '1082' or '')
                    self.adicionar(registro)

    def exportar_registros_10(self, uo):
        registro = []
        qs = RespostaEducacenso.objects.filter(
            questao__registro__ano_censo__ano=self.ano, campus=uo
        ).order_by('questao__numero_campo')
        for r in qs:
            if r.resposta == 'True':
                v = '1'
            elif r.resposta == 'False':
                v = '0'
            else:
                v = r.resposta or ''
            if v == '0':
                if r.questao.numero_campo in (86, 87, 88, 89):
                    v = ''
                elif 96 < r.questao.numero_campo < 98:
                    v = ''
                elif 115 < r.questao.numero_campo < 131:
                    v = ''
            registro.append(v)
        self.adicionar(registro)

    def exportar_registros_20(self, turmas, task):
        for turma in task.iterate(turmas):
            if not turma.get_alunos_matriculados().exists():
                continue
            diarios_turma = self.get_diarios_turma(turma)
            if diarios_turma.exists():
                registro = list()
                # 1 Tipo de registro
                registro.append(20)
                # 2 Código de escola - Inep
                registro.append(turma.curso_campus.diretoria.setor.uo.codigo_inep)
                # 3 Código da Turma na Entidade/Escola
                registro.append(turma.codigo)
                # 4 Código da Turma - INEP
                registro.append('')
                # 5 Nome da Turma
                registro.append('{} {}'.format(formatar(turma.curso_campus.descricao_historico[0:65], True), turma.codigo.replace('.', '')))
                # 6 Tipo de mediação didático-pedagógica
                # 3->Educaçaão a distancia
                # 1->presencial
                is_presencial = not turma.curso_campus.diretoria.ead
                registro.append(is_presencial and 1 or 3)
                # 7 Horário da Turma - Horário Inicial - Hora
                inicio, termino = ':', ':'
                if is_presencial:
                    horario_aula = turma.diario_set.all()[0].horario_campus.horarioaula_set.filter(turno=turma.turno).order_by('numero')
                    inicio = horario_aula.exists() and horario_aula[0].inicio or ':'
                    termino = horario_aula.exists() and horario_aula[horario_aula.count() - 1].termino or ':'
                registro.append(inicio.split(':')[0])
                # 8 Horário da Turma - Horário Inicial - Minuto
                registro.append(inicio.split(':')[1])
                # 9 Horário da Turma - Horário Final - Hora
                registro.append(termino.split(':')[0])
                # 10 Horário da Turma - Horário Final - Minuto
                registro.append(termino.split(':')[1])
                # 11 Dias da Semana - Domingo
                registro.append(is_presencial and '0' or '')
                # 12 Dias da Semana - Segunda-feira
                registro.append(is_presencial and 1 or '')
                # 13 Dias da Semana - Terça-feira
                registro.append(is_presencial and 1 or '')
                # 14 Dias da Semana - Quarta-feira
                registro.append(is_presencial and 1 or '')
                # 15 Dias da Semana - Quinta-feira
                registro.append(is_presencial and 1 or '')
                # 16 Dias da Semana - Sexta-feira
                registro.append(is_presencial and 1 or '')
                # 17 Dias da Semana - Sábado
                registro.append(is_presencial and '0' or '')
                # 18 Tipo de Atendimento - Escolarização
                registro.append(1)
                # 19 Tipo de Atendimento - Atividade complementar
                registro.append(0)
                # 20 Tipo de Atendimento - Atendimento educacional especializado - AEE
                registro.append(0)
                etapa, tecnico_integrado = self.get_etapa(turma)
                # 21 Estrutura curricular - Formação geral básica
                registro.append(tecnico_integrado)
                # 22 Estrutura curricular - Itinerário formativo
                registro.append(0)
                # 23 Estrutura curricular - Não se aplica
                registro.append(tecnico_integrado == 1 and '0' or '1')
                # 24 Código do Tipo de Atividade 1
                registro.append('')
                # 25 Código do Tipo de Atividade 2
                registro.append('')
                # 26 Código do Tipo de Atividade 3
                registro.append('')
                # 27 Código do Tipo de Atividade 4
                registro.append('')
                # 28 Código do Tipo de Atividade 5
                registro.append('')
                # 29 Código do Tipo de Atividade 6
                registro.append('')
                # 30 Local de funcionamento diferenciado da turma
                registro.append(is_presencial and '0' or '')
                # 31 Modalidade
                registro.append(4)
                # 32 Etapa de Ensino
                registro.append(etapa)
                # 33 Código Curso
                registro.append(etapa and turma.curso_campus.codigo_educacenso or '')
                # 34 Formas de organização da turma - Série/ano (séries anuais)
                registro.append(etapa != 68 and '1' or '0')
                # 35 Formas de organização da turma - Períodos semestrais
                registro.append(etapa == 68 and '1' or '0')
                # 36 Formas de organização da turma - Ciclo(s)
                registro.append('0')
                # 37 Formas de organização da turma - Grupos não seriados com base na idade ou competência
                registro.append('0')
                # 38 Formas de organização da turma - Módulos
                registro.append('0')
                # 39 Formas de organização da turma - Alternância regular de períodos de estudos (proposta pedagógica de formação por alternância: tempo-escola e tempo-comunidade)
                registro.append('0')
                # 40 Unidade curricular - Eletivas
                registro.append('')
                # 41 Unidade curricular - Libras
                registro.append('')
                # 42 Unidade curricular - Língua indígena
                registro.append('')
                # 43 Unidade curricular - Língua/Literatura estrangeira - Espanhol
                registro.append('')
                # 44 Unidade curricular - Língua/Literatura estrangeira - Francês
                registro.append('')
                # 45 Unidade curricular - Língua/Literatura estrangeira - outra
                registro.append('')
                # 46 Unidade curricular - Projeto de vida
                registro.append('')
                # 47 Unidade curricular - Trilhas de aprofundamento/aprendizagens
                registro.append('')
                # 48 Áreas do conhecimento/componentes curriculares - 1 - Química
                registro.append(tecnico_integrado and diarios_turma.filter(componente_curricular__componente__descricao__unaccent__icontains='Química', componente_curricular__nucleo__descricao='Estruturante').exists() and 1 or 0)
                # 49 Áreas do conhecimento/componentes curriculares - 2 - Física
                registro.append(
                    tecnico_integrado
                    and diarios_turma.filter(componente_curricular__componente__descricao__unaccent__icontains='Física')
                    .exclude(componente_curricular__componente__descricao__unaccent__icontains='Educação física')
                    .exists()
                    and 1
                    or 0
                )
                # 50 Áreas do conhecimento/componentes curriculares - 3 - Matemática
                registro.append(tecnico_integrado and diarios_turma.filter(componente_curricular__componente__descricao__unaccent__icontains='Matemática').exists() and 1 or 0)
                # 51 Áreas do conhecimento/componentes curriculares - 4 - Biologia
                registro.append(tecnico_integrado and diarios_turma.filter(componente_curricular__componente__descricao__unaccent__icontains='Biologi').exists() and 1 or 0)
                # 52 Áreas do conhecimento/componentes curriculares - 5 - Ciências
                registro.append(0)
                # 53 Áreas do conhecimento/componentes curriculares - 6 - Língua / Literatura portuguesa
                registro.append(tecnico_integrado and diarios_turma.filter(componente_curricular__componente__descricao__unaccent__icontains='Portugu').exists() and 1 or 0)
                # 54 Áreas do conhecimento/componentes curriculares - 7 - Língua / Literatura estrangeira – Inglês
                registro.append(tecnico_integrado and diarios_turma.filter(componente_curricular__componente__descricao__unaccent__icontains='Ingl').exists() and 1 or 0)
                # 55 Áreas do conhecimento/componentes curriculares - 8 - Língua / Literatura estrangeira – Espanhol
                registro.append(tecnico_integrado and diarios_turma.filter(componente_curricular__componente__descricao__unaccent__icontains='Espanhol').exists() and 1 or 0)
                # 56 Áreas do conhecimento/componentes curriculares - 9 - Língua / Literatura estrangeira – Outra
                registro.append(0)
                # 57 Áreas do conhecimento/componentes curriculares - 10 - Artes (educação artística, teatro, dança, música, artes plásticas e outras)
                registro.append(tecnico_integrado and diarios_turma.filter(componente_curricular__componente__descricao__unaccent__icontains='Arte I').exists() and 1 or 0)
                # 58 Áreas do conhecimento/componentes curriculares - 11 - Educação física
                registro.append(tecnico_integrado and diarios_turma.filter(componente_curricular__componente__descricao__unaccent__icontains='Educação física').exists() and 1 or 0)
                # 59 Áreas do conhecimento/componentes curriculares - 12 - História
                registro.append(tecnico_integrado and diarios_turma.filter(componente_curricular__componente__descricao__unaccent__icontains='História').exists() and 1 or 0)
                # 60 Áreas do conhecimento/componentes curriculares - 13 - Geografia
                registro.append(tecnico_integrado and diarios_turma.filter(componente_curricular__componente__descricao__unaccent__icontains='Geografia').exists() and 1 or 0)
                # 61 Áreas do conhecimento/componentes curriculares - 14 - Filosofia
                registro.append(
                    tecnico_integrado
                    and diarios_turma.filter(componente_curricular__nucleo__descricao='Estruturante')
                    .filter(componente_curricular__componente__descricao__unaccent__icontains='Filosofia')
                    .exclude(componente_curricular__componente__descricao__unaccent__icontains='Filosofia,')
                    .exists()
                    and 1
                    or 0
                )
                # 62 Áreas do conhecimento/componentes curriculares - 16 - Informática/Computação
                registro.append(tecnico_integrado and diarios_turma.exclude(componente_curricular__nucleo__descricao='Tecnológico').filter(componente_curricular__componente__descricao__unaccent__icontains='Informática').exists() and 1 or 0)
                # 63 Áreas do conhecimento/componentes curriculares - 17 - Áreas do conhecimento/componentes curriculares
                if not tecnico_integrado or (tecnico_integrado and diarios_turma.filter(componente_curricular__nucleo__descricao='Tecnológico').exists()):
                    registro.append(1)
                else:
                    registro.append(0)
                # 64 Áreas do conhecimento/componentes curriculares - 23 - Libras
                registro.append(0)
                # 65 Áreas do conhecimento/componentes curriculares - 25 - Áreas do conhecimento/componentes curriculares
                registro.append(0)
                # 66 Áreas do conhecimento/componentes curriculares - 26 - Ensino religioso
                registro.append(0)
                # 67 Áreas do conhecimento/componentes curriculares - 27 - Língua indígena
                registro.append(0)
                # 68 Áreas do conhecimento/componentes curriculares - 28 - Estudos sociais
                registro.append(0)
                # 69 Áreas do conhecimento/componentes curriculares - 29 - Sociologia
                registro.append(
                    tecnico_integrado
                    and diarios_turma.filter(componente_curricular__nucleo__descricao='Estruturante')
                    .filter(componente_curricular__componente__descricao__unaccent__icontains='Sociologia')
                    .exclude(componente_curricular__componente__descricao__unaccent__icontains='Sociologia d')
                    .exists()
                    and 1
                    or 0
                )
                # 70 Áreas do conhecimento/componentes curriculares - 30 - Língua / Literatura estrangeira – Francês
                registro.append(tecnico_integrado and diarios_turma.filter(componente_curricular__componente__descricao__unaccent__icontains='Franc').exists() and 1 or 0)
                # 71 Áreas do conhecimento/componentes curriculares - 31. Língua Portuguesa como Segunda Língua
                registro.append(0)
                # 72 Áreas do conhecimento/componentes curriculares - 32. Estágio curricular supervisionado
                registro.append(0)
                # 73 Áreas do conhecimento/componentes curriculares - 33. Projeto de vida
                registro.append(0)
                # 74 Áreas do conhecimento/componentes curriculares - 99. Outras áreas do conhecimento
                registro.append(tecnico_integrado and self.get_diarios_outros_componentes(diarios_turma).exists() and '1' or '0')
                self.adicionar(registro)

    def exportar_registros_30(self, professores, turmas, uo, task):
        for servidor in task.iterate(professores):
            check_servidor = self.check_servidor(servidor)
            if check_servidor[0]:
                continue
            naturalidade = check_servidor[1]
            nacionalidade = check_servidor[2]
            professor = Professor.objects.filter(vinculo__pessoa__id=servidor.pessoa_fisica.id).first()
            if turmas and professor:
                lista = []
                for turma in turmas.filter(diario__professordiario__professor=professor):
                    if turma.get_alunos_matriculados().exists() and self.get_diarios_turma(turma, professor).exists():
                        lista.append(turma)
                if not lista:
                    continue
            if uo is None:
                uo = turma.curso_campus.diretoria.setor.uo
            registro = list()
            # 1	Tipo do registro
            registro.append(30)
            # 2 Código de escola - Inep
            registro.append(uo.codigo_inep)
            # 3	Código da pessoa física no sistema próprio
            registro.append(servidor.matricula)
            # 4	Identificação única (Inep)
            registro.append('')
            # 5 Número do CPF
            registro.append(formatar(servidor.cpf))
            # 6 Nome completo
            registro.append(to_ascii(formatar(servidor.nome_registro)))
            # 7 Data de Nascimento
            registro.append(servidor.nascimento_data.strftime('%d/%m/%Y'))
            # 8 Filiação
            nome_mae = formatar(servidor.nome_mae or '')
            nome_pai = formatar(servidor.nome_pai or '')
            registro.append((nome_mae or nome_pai) and 1 or 0)
            # 9 Filiação 1 (preferencialmente o nome da mãe)
            registro.append(nome_mae)
            # 10 Filiação 2 (preferencialmente o nome do pai)
            registro.append(nome_pai)
            # 11    Sexo        1    Fixo    Numérico    Obrigatório
            registro.append(servidor.sexo == 'M' and 1 or 2)
            # 12    Cor/Raça        1    Fixo    Numérico    Obrigatório
            registro.append(servidor.raca_id and servidor.raca.codigo_censup or 1)
            # 13    Nacionalidade        1    Fixo    Numérico    Obrigatório
            # 1 - Brasileiro
            # 2 - Brasileira - Nascido no exterior ou naturalizado
            # 3 - Estrangeiro
            if servidor.nacionalidade == 1:
                registro.append(1)
            elif servidor.nacionalidade in (2, 3):
                registro.append(2)
            else:
                registro.append(3)
            # 14 País de nacionalidade
            registro.append(nacionalidade)
            # 15    Município de Nascimento        7    Fixo    Númerico    Condicional
            registro.append(servidor.nacionalidade == 1 and naturalidade and naturalidade.codigo or '')
            # 16 Pessoa física com deficiência, transtorno do espectro autista ou altas habilidades/ superdotação
            registro.append(0)
            # 17 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Cegueira
            registro.append('')
            # 18 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Baixa visão
            registro.append('')
            # 19 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Surdez
            registro.append('')
            # 20 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Deficiência auditiva
            registro.append('')
            # 21 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Surdocegueira
            registro.append('')
            # 22 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Deficiência física
            registro.append('')
            # 23 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Deficiência intelectual
            registro.append('')
            # 24 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Deficiência múltipla
            registro.append('')
            # 25 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Transtorno do espectro autista
            registro.append('')
            # 26 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Altas habilidades/ superdotação
            registro.append('')
            # 27 Auxílio ledor
            registro.append('')
            # 28 Auxílio transcrição
            registro.append('')
            # 29 Guia-Intérprete
            registro.append('')
            # 30 Tradutor-Intérprete de Libras
            registro.append('')
            # 31 Leitura Labial
            registro.append('')
            # 32 Prova Ampliada (Fonte 18)
            registro.append('')
            # 33 Prova superampliada (Fonte 24)
            registro.append('')
            # 34 CD com áudio para deficiente visual
            registro.append('')
            # 35 Prova de Língua Portuguesa como Segunda Língua para surdos e deficientes auditivos
            registro.append('')
            # 36 Prova em Vídeo em Libras
            registro.append('')
            # 37 Material didático e prova em Braille
            registro.append('')
            # 38 Nenhum
            registro.append('')
            # 39 Número da matrícula da certidão de nascimento (certidão nova)
            registro.append('')
            # 40 País da residência
            registro.append('')
            # 41 CEP
            registro.append('')
            # 42 Município de residência
            registro.append('')
            # 43 Localização/ Zona de residência
            registro.append('')
            # 44 Localização diferenciada de residência
            registro.append('')
            # 45 Maior nível de escolaridade concluído
            registro.append(6)
            # 46 Tipo de ensino médio cursado
            registro.append('')
            # 47 Código do Curso 1
            registro.append(professor and professor.curso_superior_id and professor.curso_superior.codigo or '999990')
            # 48 Ano de Conclusão 1
            registro.append(professor and professor.ano_conclusao_curso_superior or '2010')
            # 49 Instituição de educação superior 1
            registro.append(professor and professor.instituicao_ensino_superior_id and professor.instituicao_ensino_superior.codigo or '9999999')
            # 50 Código do Curso 2
            registro.append('')
            # 51 Ano de Conclusão 2
            registro.append('')
            # 52 Instituição de educação superior 2
            registro.append('')
            # 53 Código do Curso 3
            registro.append('')
            # 54 Ano de Conclusão 3
            registro.append('')
            # 55 Instituição de educação superior 3
            registro.append('')
            # 56 Formação/Complementação pedagógica - Área do conhecimento/ componentes curriculares 1
            registro.append('')
            # 57 Formação/Complementação pedagógica - Área do conhecimento/ componentes curriculares 2
            registro.append('')
            # 58 Formação/Complementação pedagógica - Área do conhecimento/ componentes curriculares 3
            registro.append('')
            titulacao = professor and professor.titulacao or ''
            titulacao_pos = 'speciali' in titulacao and 1 or 'estr' in titulacao and 2 or 'outor' in titulacao and 3 or ''
            # 59 Pós-Graduações concluídas - Tipo de pós-graduação 1
            registro.append(titulacao_pos)
            # 60 Pós-Graduações concluídas - Área da pós-graduação 1
            registro.append(titulacao_pos and int(professor.area_ultima_titulacao or 0) or '')
            # 61 Pós-Graduações concluídas - Ano de conclusão da pós-graduação 1
            registro.append(titulacao_pos and professor.ano_ultima_titulacao and professor.ano_ultima_titulacao.ano or '')
            # 62 Pós-Graduações concluídas - Tipo de pós-graduação 2
            registro.append('')
            # 63 Pós-Graduações concluídas - Área da pós-graduação 2
            registro.append('')
            # 64 Pós-Graduações concluídas - Ano de conclusão da pós-graduação 2
            registro.append('')
            # 65 Pós-Graduações concluídas - Tipo de pós-graduação 3
            registro.append('')
            # 66 Pós-Graduações concluídas - Área da pós-graduação 3
            registro.append('')
            # 67 Pós-Graduações concluídas - Ano de conclusão da pós-graduação 3
            registro.append('')
            # 68 Pós-Graduações concluídas - Tipo de pós-graduação 4
            registro.append('')
            # 69 Pós-Graduações concluídas - Área da pós-graduação 4
            registro.append('')
            # 70 Pós-Graduações concluídas - Ano de conclusão da pós-graduação 4
            registro.append('')
            # 71 Pós-Graduações concluídas - Tipo de pós-graduação 5
            registro.append('')
            # 72 Pós-Graduações concluídas - Área da pós-graduação 5
            registro.append('')
            # 73 Pós-Graduações concluídas - Ano de conclusão da pós-graduação 5
            registro.append('')
            # 74 Pós-Graduações concluídas - Tipo de pós-graduação 6
            registro.append('')
            # 75 Pós-Graduações concluídas - Área da pós-graduação 6
            registro.append('')
            # 76 Pós-Graduações concluídas - Ano de conclusão da pós-graduação 6
            registro.append('')
            # 77 Pós-Graduações concluídas - Não tem pós-graduação concluída
            registro.append((not titulacao or 'radua' in titulacao) and 1 or '')
            # 78 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Creche (0 a 3 anos)
            registro.append(0)
            # 79 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Pré-escola (4 e 5 anos)
            registro.append(0)
            # 80 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Anos iniciais do ensino fundamental
            registro.append(0)
            # 81 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Anos finais do ensino fundamental
            registro.append(0)
            # 82 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Ensino médio
            registro.append(0)
            # 83 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação de jovens e adultos
            registro.append(0)
            # 84 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação especial
            registro.append(0)
            # 85 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação Indígena
            registro.append(0)
            # 86 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação do campo
            registro.append(0)
            # 87 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação ambiental
            registro.append(0)
            # 88 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação em direitos humanos
            registro.append(0)
            # 89 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Gênero e diversidade sexual
            registro.append(0)
            # 90 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Direitos de criança e adolescente
            registro.append(0)
            # 91 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação para as relações étnico-raciais e História e cultura afro-brasileira e africana
            registro.append(0)
            # 92 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Gestão Escolar
            registro.append(0)
            # 93 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Outros
            registro.append(0)
            # 94 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Nenhum
            registro.append(1)
            # 95 Endereço Eletrônico (e-mail)
            qs_diretoria = Diretoria.objects.filter(setor__uo=uo, tipo=Diretoria.TIPO_DIRETORIA_ENSINO)
            if qs_diretoria.exists():
                diretoria = qs_diretoria.first()
            else:
                diretoria = Diretoria.objects.filter(setor__uo=uo).first()
            registro.append((servidor.get_vinculo().user == diretoria.diretor_geral.user or servidor.get_vinculo().user == diretoria.diretor_academico.user) and servidor.email and servidor.email.upper() or '')
            self.adicionar(registro)

    def exportar_registros_30_alunos(self, alunos, turmas, task):
        for aluno in task.iterate(alunos):
            matricula_periodo = aluno.matriculaperiodo_set.filter(ano_letivo__ano=self.ano, periodo_letivo=1).order_by('-periodo_letivo')[0]
            turma = matricula_periodo.turma_id and matricula_periodo.turma or None
            if not turma:
                ultimo_prodecimento = matricula_periodo.procedimentomatricula_set.order_by('-data').first()
                self.erros.append(
                    '{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(
                        aluno.matricula,
                        'SEM TURMA',
                        aluno.curso_campus.diretoria.setor.uo.sigla,
                        aluno.curso_campus.diretoria,
                        aluno.situacao,
                        ultimo_prodecimento and ultimo_prodecimento.tipo or '',
                        ultimo_prodecimento and ultimo_prodecimento.data.strftime('%d/%m/%Y'),
                    )
                )
                continue
            if 0 and not aluno.codigo_educacenso:
                self.erros.append(
                    '{}\t{}\t{}\t{}\t{}'.format(aluno.matricula, 'CODIGO EDUCACENSO', aluno.curso_campus.diretoria.setor.uo.sigla, aluno.curso_campus.diretoria, aluno.situacao)
                )
                continue
            if not self.get_diarios_turma(turma).exists():
                self.erros.append(
                    '{}\t{}\t{}\t{}\t{}'.format(aluno.matricula, 'CODIGO TURMA', aluno.curso_campus.diretoria.setor.uo.sigla, aluno.curso_campus.diretoria, aluno.situacao)
                )
                continue
            if (
                not matricula_periodo.matriculadiario_set.exclude(
                    diario__componente_curricular__tipo=ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL, diario__componente_curricular__pode_fechar_pendencia=True
                )
                .exclude(diario__professordiario__isnull=True)
                .exclude(diario__professordiario__professor__vinculo__pessoa__pessoafisica__nascimento_municipio__isnull=True)
                .exists()
            ):
                continue
            if aluno.nacionalidade == 'Brasileira - Nascido no exterior ou naturalizado' or aluno.nacionalidade == 'Brasileira':
                nacionalidade = 76
            else:
                from comum.models import Pais
                pais = aluno.pais_origem and Pais.objects.filter(nome=formatar(aluno.pais_origem.nome.upper())).first() or None
                if pais and pais.codigo_educacenso:
                    nacionalidade = pais.codigo_educacenso
                else:
                    self.erros.append(
                        '{}\t{}\t{}\t{}\t{}'.format(aluno.matricula, 'SEM CODIGO PAIS', aluno.curso_campus.diretoria.setor.uo.sigla, aluno.curso_campus.diretoria, aluno.situacao)
                    )
                    continue
            if aluno.nacionalidade == 'Brasileira' and not aluno.naturalidade_id:
                self.erros.append('{}\t{}\t{}'.format(aluno.matricula, 'SEM NATURALIDADE', turma.curso_campus.diretoria.setor.uo.sigla))
                continue

            dados_rf = aluno.get_dados_receita_federal(self.cpf_operador)
            registro = list()
            # 1	Tipo do registro
            registro.append(30)
            # 2 Código de escola - Inep
            registro.append(turma.curso_campus.diretoria.setor.uo.codigo_inep)
            # 3	Código da pessoa física no sistema próprio
            registro.append(aluno.matricula)
            # 4	Identificação única (Inep)
            registro.append(aluno.codigo_educacenso or '')
            # 5 Número do CPF
            registro.append(formatar(aluno.pessoa_fisica.cpf))
            # 6 Nome completo
            if dados_rf.get('Nome'):
                registro.append(to_ascii(dados_rf.get('Nome').upper()))
            else:
                registro.append(to_ascii(formatar(aluno.pessoa_fisica.nome_registro)))
            # 7 Data de Nascimento
            if dados_rf.get('DataNascimento'):
                registro.append(f"{dados_rf['DataNascimento'][6:8]}/{dados_rf['DataNascimento'][4:6]}/{dados_rf['DataNascimento'][0:4]}")
            else:
                registro.append(aluno.pessoa_fisica.nascimento_data.strftime('%d/%m/%Y'))
            # 8 Filiação
            # nome_mae = formatar(aluno.nome_mae or '')
            nome_mae = formatar(dados_rf.get('NomeMae', ''))
            nome_pai = formatar(aluno.nome_pai or '')
            registro.append((nome_mae or nome_pai) and 1 or 0)
            # 9 Filiação 1 (preferencialmente o nome da mãe)
            registro.append(nome_mae)
            # 10 Filiação 2 (preferencialmente o nome do pai)
            registro.append(nome_pai)
            # 11    Sexo        1    Fixo    Numérico    Obrigatório
            registro.append(aluno.pessoa_fisica.sexo == 'M' and 1 or 2)
            # 12    Cor/Raça        1    Fixo    Numérico    Obrigatório
            registro.append(aluno.pessoa_fisica.raca_id and aluno.pessoa_fisica.raca.codigo_censup or 1)
            # 13    Nacionalidade        1    Fixo    Numérico    Obrigatório
            # 1 - Brasileiro
            # 2 - Brasileira - Nascido no exterior ou naturalizado
            # 3 - Estrangeiro
            if aluno.nacionalidade == 'Brasileira':
                registro.append(1)
            elif aluno.nacionalidade == 'Brasileira - Nascido no exterior ou naturalizado':
                registro.append(2)
            else:
                registro.append(3)
            # 14 País de nacionalidade
            registro.append(nacionalidade)
            # 15    Município de Nascimento        7    Fixo    Númerico    Condicional
            registro.append(aluno.nacionalidade == 'Brasileira' and aluno.naturalidade.codigo or '')
            # 16 Pessoa física com deficiência, transtorno do espectro autista ou altas habilidades/ superdotação
            registro.append(0)
            # 17 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Cegueira
            registro.append('')
            # 18 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Baixa visão
            registro.append('')
            # 19 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Surdez
            registro.append('')
            # 20 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Deficiência auditiva
            registro.append('')
            # 21 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Surdocegueira
            registro.append('')
            # 22 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Deficiência física
            registro.append('')
            # 23 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Deficiência intelectual
            registro.append('')
            # 24 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Deficiência múltipla
            registro.append('')
            # 25 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Transtorno do espectro autista
            registro.append('')
            # 26 Tipo de deficiência, transtorno do espectro autista e altas habilidades/superdotação – Altas habilidades/ superdotação
            registro.append('')
            # 27 Auxílio ledor
            registro.append('')
            # 28 Auxílio transcrição
            registro.append('')
            # 29 Guia-Intérprete
            registro.append('')
            # 30 Tradutor-Intérprete de Libras
            registro.append('')
            # 31 Leitura Labial
            registro.append('')
            # 32 Prova Ampliada (Fonte 18)
            registro.append('')
            # 33 Prova superampliada (Fonte 24)
            registro.append('')
            # 34 CD com áudio para deficiente visual
            registro.append('')
            # 35 Prova de Língua Portuguesa como Segunda Língua para surdos e deficientes auditivos
            registro.append('')
            # 36 Prova em Vídeo em Libras
            registro.append('')
            # 37 Material didático e prova em Braille
            registro.append('')
            # 38 Nenhum
            registro.append('')
            # 39 Número da matrícula da certidão de nascimento (certidão nova)
            registro.append('')
            # 40 País da residência
            registro.append(76)
            # 41 CEP
            registro.append('')
            # 42 Município de residência
            registro.append('')
            # 43 Localização/ Zona de residência
            registro.append(aluno.tipo_zona_residencial)
            # 44 Localização diferenciada de residência
            registro.append('')
            # 45 Maior nível de escolaridade concluído
            registro.append('')
            # 46 Tipo de ensino médio cursado
            registro.append('')
            # 47 Código do Curso 1
            registro.append('')
            # 48 Ano de Conclusão 1
            registro.append('')
            # 49 Instituição de educação superior 1
            registro.append('')
            # 50 Código do Curso 2
            registro.append('')
            # 51 Ano de Conclusão 2
            registro.append('')
            # 52 Instituição de educação superior 2
            registro.append('')
            # 53 Código do Curso 3
            registro.append('')
            # 54 Ano de Conclusão 3
            registro.append('')
            # 55 Instituição de educação superior 3
            registro.append('')
            # 56 Formação/Complementação pedagógica - Área do conhecimento/ componentes curriculares 1
            registro.append('')
            # 57 Formação/Complementação pedagógica - Área do conhecimento/ componentes curriculares 2
            registro.append('')
            # 58 Formação/Complementação pedagógica - Área do conhecimento/ componentes curriculares 3
            registro.append('')
            # 59 Pós-Graduações concluídas - Tipo de pós-graduação 1
            registro.append('')
            # 60 Pós-Graduações concluídas - Área da pós-graduação 1
            registro.append('')
            # 61 Pós-Graduações concluídas - Ano de conclusão da pós-graduação 1
            registro.append('')
            # 62 Pós-Graduações concluídas - Tipo de pós-graduação 2
            registro.append('')
            # 63 Pós-Graduações concluídas - Área da pós-graduação 2
            registro.append('')
            # 64 Pós-Graduações concluídas - Ano de conclusão da pós-graduação 2
            registro.append('')
            # 65 Pós-Graduações concluídas - Tipo de pós-graduação 3
            registro.append('')
            # 66 Pós-Graduações concluídas - Área da pós-graduação 3
            registro.append('')
            # 67 Pós-Graduações concluídas - Ano de conclusão da pós-graduação 3
            registro.append('')
            # 68 Pós-Graduações concluídas - Tipo de pós-graduação 4
            registro.append('')
            # 69 Pós-Graduações concluídas - Área da pós-graduação 4
            registro.append('')
            # 70 Pós-Graduações concluídas - Ano de conclusão da pós-graduação 4
            registro.append('')
            # 71 Pós-Graduações concluídas - Tipo de pós-graduação 5
            registro.append('')
            # 72 Pós-Graduações concluídas - Área da pós-graduação 5
            registro.append('')
            # 73 Pós-Graduações concluídas - Ano de conclusão da pós-graduação 5
            registro.append('')
            # 74 Pós-Graduações concluídas - Tipo de pós-graduação 6
            registro.append('')
            # 75 Pós-Graduações concluídas - Área da pós-graduação 6
            registro.append('')
            # 76 Pós-Graduações concluídas - Ano de conclusão da pós-graduação 6
            registro.append('')
            # 77 Pós-Graduações concluídas - Não tem pós-graduação concluída
            registro.append('')
            # 78 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Creche (0 a 3 anos)
            registro.append('')
            # 79 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Pré-escola (4 e 5 anos)
            registro.append('')
            # 80 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Anos iniciais do ensino fundamental
            registro.append('')
            # 81 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Anos finais do ensino fundamental
            registro.append('')
            # 82 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Ensino médio
            registro.append('')
            # 83 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação de jovens e adultos
            registro.append('')
            # 84 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação especial
            registro.append('')
            # 85 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação Indígena
            registro.append('')
            # 86 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação do campo
            registro.append('')
            # 87 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação ambiental
            registro.append('')
            # 88 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação em direitos humanos
            registro.append('')
            # 89 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Gênero e diversidade sexual
            registro.append('')
            # 90 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Direitos de criança e adolescente
            registro.append('')
            # 91 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Educação para as relações étnico-raciais e História e cultura afro-brasileira e africana
            registro.append('')
            # 92 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Gestão Escolar
            registro.append('')
            # 93 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Outros
            registro.append('')
            # 94 Outros cursos específicos (Formação continuada com mínimo de 80 horas) - Nenhum
            registro.append('')
            # 95 Endereço Eletrônico (e-mail)
            registro.append('')
            self.adicionar(registro)

    def exportar_registros_40(self, professores, uo, task):
        qs_diretoria = Diretoria.objects.filter(setor__uo=uo, tipo=Diretoria.TIPO_DIRETORIA_ENSINO)
        if qs_diretoria.exists():
            diretoria = qs_diretoria.first()
        else:
            diretoria = Diretoria.objects.filter(setor__uo=uo).first()
        matriculas = [diretoria.diretor_geral.user.username, diretoria.diretor_academico.user.username]
        gestores = Servidor.objects.filter(matricula__in=matriculas)
        gestores_sem_diario = gestores.exclude(pk__in=professores.values_list('pk', flat=True))
        if gestores_sem_diario.exists():
            self.exportar_registros_30(gestores_sem_diario, None, uo, task)
        for servidor in gestores:
            registro = list()
            # 1 Tipo de registro
            registro.append(40)
            # 2 Código de escola - Inep
            registro.append(uo.codigo_inep)
            # 3 Código da pessoa física no sistema próprio
            registro.append(servidor.matricula)
            # 4 Identificação única (Inep)
            registro.append('')
            # 5 Cargo
            #     1: Diretor(a)
            #     2: Outro Cargo
            registro.append(2)
            # 6 Critério de acesso ao cargo/função
            registro.append('')
            # 7 Situação Funcional/ Regime de contratação/Tipo de vínculo
            registro.append('')
            self.adicionar(registro)

    def exportar_registros_50(self, professores, turmas, task):
        for servidor in task.iterate(professores):
            if self.check_servidor(servidor)[0]:
                continue
            professor = Professor.objects.get(vinculo__pessoa__id=servidor.pessoa_fisica.id)
            lista = []
            for turma in turmas.filter(diario__professordiario__professor=professor):
                if turma.get_alunos_matriculados().exists() and self.get_diarios_turma(turma, professor).exists():
                    lista.append(turma)

            for turma in lista:
                diarios_professor = self.get_diarios_turma(turma, professor)
                if diarios_professor.exists():
                    registro = list()
                    # 1 Tipo de registro
                    registro.append(50)
                    # 2 Código de escola - Inep
                    registro.append(turma.curso_campus.diretoria.setor.uo.codigo_inep)
                    # 3 Código da pessoa física no sistema próprio
                    registro.append(servidor.matricula)
                    # 4 Identificação única (Inep)
                    registro.append('')
                    # 5 Código da Turma na Entidade/Escola
                    registro.append(turma.codigo)
                    # 6 Código da turma no INEP
                    registro.append('')
                    # 7 Função que exerce na escola/Turma
                    is_presencial = not turma.curso_campus.diretoria.ead
                    registro.append(is_presencial and 1 or 5)
                    # 8 Situação Funcional/ Regime de contratação/Tipo de Vínculo
                    registro.append(servidor.situacao.nome in ('CONT.PROF.SUBSTITUTO', 'CONT.PROF.TEMPORARIO') and 2 or 1)
                    disciplinas = []
                    tecnico_integrado = self.get_etapa(turma)[1]
                    if tecnico_integrado and diarios_professor.filter(componente_curricular__componente__descricao__unaccent__icontains='Química', componente_curricular__nucleo__descricao='Estruturante').exists():
                        disciplinas.append('1')
                    if (
                        tecnico_integrado
                        and diarios_professor.filter(componente_curricular__componente__descricao__unaccent__icontains='Física')
                        .exclude(componente_curricular__componente__descricao__unaccent__icontains='Educação física')
                        .exists()
                    ):
                        disciplinas.append('2')
                    if tecnico_integrado and diarios_professor.filter(componente_curricular__componente__descricao__unaccent__icontains='Matemática').exists():
                        disciplinas.append('3')
                    if tecnico_integrado and diarios_professor.filter(componente_curricular__componente__descricao__unaccent__icontains='Biologi').exists():
                        disciplinas.append('4')
                    if tecnico_integrado and diarios_professor.filter(componente_curricular__componente__descricao__unaccent__icontains='Portugu').exists():
                        disciplinas.append('6')
                    if tecnico_integrado and diarios_professor.filter(componente_curricular__componente__descricao__unaccent__icontains='Ingl').exists():
                        disciplinas.append('7')
                    if tecnico_integrado and diarios_professor.filter(componente_curricular__componente__descricao__unaccent__icontains='Espanhol').exists():
                        disciplinas.append('8')
                    if tecnico_integrado and diarios_professor.filter(componente_curricular__componente__descricao__unaccent__icontains='Franc').exists():
                        disciplinas.append('30')
                    if tecnico_integrado and diarios_professor.filter(componente_curricular__componente__descricao__unaccent__icontains='Arte I').exists():
                        disciplinas.append('10')
                    if tecnico_integrado and diarios_professor.filter(componente_curricular__componente__descricao__unaccent__icontains='Educação física').exists():
                        disciplinas.append('11')
                    if tecnico_integrado and diarios_professor.filter(componente_curricular__componente__descricao__unaccent__icontains='História').exists():
                        disciplinas.append('12')
                    if tecnico_integrado and diarios_professor.filter(componente_curricular__componente__descricao__unaccent__icontains='Geografia').exists():
                        disciplinas.append('13')
                    if (
                        tecnico_integrado
                        and diarios_professor.filter(componente_curricular__nucleo__descricao='Estruturante')
                        .filter(componente_curricular__componente__descricao__unaccent__icontains='Filosofia')
                        .exclude(componente_curricular__componente__descricao__unaccent__icontains='Filosofia,')
                        .exists()
                    ):
                        disciplinas.append('14')
                    if (
                        tecnico_integrado
                        and diarios_professor.filter(componente_curricular__nucleo__descricao='Estruturante')
                        .filter(componente_curricular__componente__descricao__unaccent__icontains='Sociologia')
                        .exclude(componente_curricular__componente__descricao__unaccent__icontains='Sociologia d,')
                        .exists()
                    ):
                        disciplinas.append('29')
                    if (
                        tecnico_integrado
                        and diarios_professor.exclude(componente_curricular__nucleo__descricao='Tecnológico')
                        .filter(componente_curricular__componente__descricao__unaccent__icontains='Informática')
                        .exists()
                    ):
                        disciplinas.append('16')
                    if tecnico_integrado and diarios_professor.filter(componente_curricular__nucleo__descricao='Tecnológico').exists():
                        disciplinas.append('17')
                    if tecnico_integrado and self.get_diarios_outros_componentes(diarios_professor).exists():
                        disciplinas.append('99')
                    if not tecnico_integrado:
                        disciplinas.append('17')
                    disciplinas = list(set(disciplinas))
                    for i in range(len(disciplinas), 15):
                        disciplinas.append('')
                    # 9 a 23 Áreas do conhecimento/componentes curriculares - Código 1 a 15)
                    for codigo in disciplinas:
                        registro.append(codigo)
                    # 24 Unidade(s) curricular(es) que leciona - Eletivas
                    registro.append('')
                    # 25 Unidade(s) curricular(es) que leciona - Libras
                    registro.append('')
                    # 26 Unidade(s) curricular(es) que leciona - Língua indígena
                    registro.append('')
                    # 27 Unidade(s) curricular(es) que leciona - Língua/Literatura estrangeira - Espanhol
                    registro.append('')
                    # 28 Unidade(s) curricular(es) que leciona - Língua/Literatura estrangeira - Francês
                    registro.append('')
                    # 29 Unidade(s) curricular(es) que leciona - Língua/Literatura estrangeira - outra
                    registro.append('')
                    # 30 Unidade(s) curricular(es) que leciona - Projeto de vida
                    registro.append('')
                    # 31 Unidade(s) curricular(es) que leciona - Trilhas de aprofundamento/aprendizagens
                    registro.append('')
                    self.adicionar(registro)

    def exportar_registros_60(self, alunos, task):
        for aluno in task.iterate(alunos):
            matricula_periodo = aluno.matriculaperiodo_set.filter(ano_letivo__ano=self.ano, periodo_letivo=1).order_by('-periodo_letivo')[0]
            turma = matricula_periodo.turma_id and matricula_periodo.turma or None
            if not turma:
                ultimo_prodecimento = matricula_periodo.procedimentomatricula_set.order_by('-data').first()
                self.erros.append(
                    '{}\t{}\t{}\t{}\t{}\t{}\t{}'.format(
                        aluno.matricula,
                        'SEM TURMA',
                        aluno.curso_campus.diretoria.setor.uo.sigla,
                        aluno.curso_campus.diretoria,
                        aluno.situacao,
                        ultimo_prodecimento and ultimo_prodecimento.tipo or '',
                        ultimo_prodecimento and ultimo_prodecimento.data.strftime('%d/%m/%Y'),
                    )
                )
                continue
            if aluno.nacionalidade == 'Brasileira' and not aluno.naturalidade_id:
                self.erros.append(
                    '{}\t{}\t{}\t{}\t{}'.format(aluno.matricula, 'SEM NATURALIDADE', aluno.curso_campus.diretoria.setor.uo.sigla, aluno.curso_campus.diretoria, aluno.situacao)
                )
                continue
            if 0 and not aluno.codigo_educacenso:
                self.erros.append(
                    '{}\t{}\t{}\t{}\t{}'.format(aluno.matricula, 'CODIGO EDUCACENSO', aluno.curso_campus.diretoria.setor.uo.sigla, aluno.curso_campus.diretoria, aluno.situacao)
                )
                continue
            if not self.get_diarios_turma(turma).exists():
                self.erros.append(
                    '{}\t{}\t{}\t{}\t{}'.format(aluno.matricula, 'CODIGO TURMA', aluno.curso_campus.diretoria.setor.uo.sigla, aluno.curso_campus.diretoria, aluno.situacao)
                )
                continue
            if (
                not matricula_periodo.matriculadiario_set.exclude(
                    diario__componente_curricular__tipo=ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL, diario__componente_curricular__pode_fechar_pendencia=True
                )
                .exclude(diario__professordiario__isnull=True)
                .exclude(diario__professordiario__professor__vinculo__pessoa__pessoafisica__nascimento_municipio__isnull=True)
                .exists()
            ):
                continue

            is_presencial = not turma.curso_campus.diretoria.ead

            registro = list()
            # 1	Tipo de registro
            registro.append(60)
            # 2 Código de escola - Inep
            registro.append(aluno.curso_campus.diretoria.setor.uo.codigo_inep)
            # 3 Código da pessoa física no sistema próprio
            registro.append(aluno.matricula)
            # 4	Identificação única (Inep)
            registro.append(aluno.codigo_educacenso or '')
            # 5 Código da Turma na Entidade/Escola
            registro.append(turma.codigo)
            # 6 Código da turma no INEP
            registro.append('')
            # 7 Código da Matrícula do Aluno
            registro.append('')
            # 8 Turma multi
            registro.append('')
            # 9 Tipo do itinerário formativo - Linguagens e suas tecnologias
            registro.append('')
            # 10 Tipo do itinerário formativo - Matemática e suas tecnologias
            registro.append('')
            # 11 Tipo do itinerário formativo - Ciências da natureza e suas tecnologias
            registro.append('')
            # 12 Tipo do itinerário formativo - Ciências humanas e sociais aplicadas
            registro.append('')
            # 13 Tipo do itinerário formativo - Formação técnica e profissional
            registro.append('')
            # 14 Tipo do itinerário formativo - Itinerário formativo integrado
            registro.append('')
            # 15 Composição do itinerário formativo integrado - Linguagens e suas tecnologias
            registro.append('')
            # 16 Composição do itinerário formativo integrado - Matemática e suas tecnologias
            registro.append('')
            # 17 Composição do itinerário formativo integrado - Ciências da natureza e suas tecnologias
            registro.append('')
            # 18 Composição do itinerário formativo integrado - Ciências humanas e sociais aplicadas
            registro.append('')
            # 19 Composição do itinerário formativo integrado - Formação técnica e profissionalS
            registro.append('')
            # 20 Tipo do curso do itinerário de formação técnica e profissional
            registro.append('')
            # 21 Itinerário concomitante intercomplementar à matrícula de formação geral básica
            registro.append('')
            # 22 Tipo de atendimento educacional especializado - Desenvolvimento de funções cognitivas
            registro.append('')
            # 23 Tipo de atendimento educacional especializado - Desenvolvimento de vida autônoma
            registro.append('')
            # 24 Tipo de atendimento educacional especializado - Enriquecimento curricular
            registro.append('')
            # 25 Tipo de atendimento educacional especializado - Ensino da informática acessível
            registro.append('')
            # 26 Tipo de atendimento educacional especializado - Ensino da Língua Brasileira de Sinais (Libras)
            registro.append('')
            # 27 Tipo de atendimento educacional especializado - Ensino da Língua Portuguesa como Segunda Língua
            registro.append('')
            # 28 Tipo de atendimento educacional especializado - Ensino das técnicas do cálculo no Soroban
            registro.append('')
            # 29 Tipo de atendimento educacional especializado - Ensino de Sistema Braille
            registro.append('')
            # 30 Tipo de atendimento educacional especializado - Ensino de técnicas para orientação e mobilidade
            registro.append('')
            # 31 Tipo de atendimento educacional especializado - Ensino de uso da Comunicação Alternativa e Aumentativa (CAA)
            registro.append('')
            # 32 Tipo de atendimento educacional especializado - Ensino de uso de recursos ópticos e não ópticos
            registro.append('')
            # 33 Recebe escolarização em outro espaço (diferente da escola)
            registro.append(is_presencial and 1 or '')
            # 34 Transporte escolar público
            usa_transporte_publico = is_presencial and (aluno.poder_publico_responsavel_transporte and '1' or '0') or ''
            registro.append(usa_transporte_publico)
            # 35 Poder Público responsável pelo transporte escolar
            if usa_transporte_publico == '1':
                if aluno.poder_publico_responsavel_transporte == '1':
                    registro.append('2')
                else:
                    registro.append('1')
            else:
                registro.append('')
            valor_vazio = is_presencial and aluno.poder_publico_responsavel_transporte and '0' or ''
            # 36 Tipo de veículo utilizado no transporte escolar público - Rodoviário - Bicicleta
            registro.append(is_presencial and aluno.tipo_veiculo == Aluno.BICICLETA and '1' or valor_vazio)
            # 37 Tipo de veículo utilizado no transporte escolar público - Rodoviário - Microônibus
            registro.append(is_presencial and aluno.tipo_veiculo == Aluno.KOMBI_MICRO_ONIBUS and '1' or valor_vazio)
            # 38 Tipo de veículo utilizado no transporte escolar público - Rodoviário - Ônibus
            registro.append(is_presencial and aluno.tipo_veiculo == Aluno.ONIBUS and '1' or valor_vazio)
            # 39 Tipo de veículo utilizado no transporte escolar público - Rodoviário – Tração Animal
            registro.append(is_presencial and aluno.tipo_veiculo == Aluno.TRACAO_ANIMAL and '1' or valor_vazio)
            # 40 Tipo de veículo utilizado no transporte escolar público - Rodoviário - Vans/Kombis
            registro.append(is_presencial and aluno.tipo_veiculo == Aluno.VANS_WV and '1' or valor_vazio)
            # 41 Tipo de veículo utilizado no transporte escolar público - Rodoviário - Outro
            registro.append(is_presencial and aluno.tipo_veiculo == Aluno.OUTRO_VEICULO_RODOVIARIO and '1' or valor_vazio)
            # 42 Tipo de veículo utilizado no transporte escolar público - Aquaviário - Capacidade de até 5 aluno(a)s
            registro.append(is_presencial and aluno.tipo_veiculo == Aluno.AQUAVIARIO_ATE_5 and '1' or valor_vazio)
            # 43 Tipo de veículo utilizado no transporte escolar público - Aquaviário - Capacidade entre 5 a 15 aluno(a)s
            registro.append(is_presencial and aluno.tipo_veiculo == Aluno.AQUAVIARIO_ENTRE_5_A_15 and '1' or valor_vazio)
            # 44 Tipo de veículo utilizado no transporte escolar público - Aquaviário - Capacidade entre 15 a 35 aluno(a)s
            registro.append(is_presencial and aluno.tipo_veiculo == Aluno.AQUALVIARIO_ENTRE_15_E_35 and '1' or valor_vazio)
            # 45 Tipo de veículo utilizado no transporte escolar público - Aquaviário - Capacidade acima de 35 aluno(a)s
            registro.append(is_presencial and aluno.tipo_veiculo == Aluno.AQUAVIARIO_ACIMA_DE_35 and '1' or valor_vazio)
            self.adicionar(registro)

    def get_diarios_turma(self, turma, professor=None):
        qs = turma.diario_set.\
            exclude(componente_curricular__tipo=ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL, componente_curricular__pode_fechar_pendencia=True).\
            exclude(professordiario__isnull=True).\
            exclude(professordiario__professor__vinculo__pessoa__pessoafisica__nacionalidade=1, professordiario__professor__vinculo__pessoa__pessoafisica__nascimento_municipio__isnull=True)
        if professor:
            qs = qs.filter(professordiario__professor=professor)
        return qs

    def get_diarios_outros_componentes(self, qs_diario):
        qs_diario = qs_diario.\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Química', componente_curricular__nucleo__descricao='Estruturante').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Física').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Matemática').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Biologi').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Portugu').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Ingl').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Espanhol').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Franc').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Arte I').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Educação física').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='História').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Geografia').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Filosofia', componente_curricular__nucleo__descricao='Estruturante').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Sociologia', componente_curricular__nucleo__descricao='Estruturante').\
            exclude(componente_curricular__componente__descricao__unaccent__icontains='Informática').\
            exclude(componente_curricular__nucleo__descricao='Tecnológico')
        return qs_diario

    def get_etapa(self, turma):
        if turma.curso_campus.modalidade.pk == Modalidade.INTEGRADO_EJA:
            etapa = 74
        elif turma.curso_campus.modalidade.pk == Modalidade.PROEJA_FIC_FUNDAMENTAL:
            etapa = 68
        elif turma.curso_campus.modalidade.pk == Modalidade.SUBSEQUENTE:
            etapa = 40
        elif turma.curso_campus.modalidade.pk == Modalidade.CONCOMITANTE:
            etapa = 39
        else:
            etapa = turma.periodo_matriz == 1 and 30 or turma.periodo_matriz == 2 and 31 or turma.periodo_matriz == 3 and 32 or turma.periodo_matriz == 4 and 33 or ''
        tecnico_integrado = etapa in (30, 31, 32, 33, 74) and 1 or 0
        return etapa, tecnico_integrado

    def check_servidor(self, servidor):
        tem_erro = False
        qs_naturalidade = Cidade.objects.none()
        if servidor.nacionalidade == 1:
            if not servidor.nascimento_municipio:
                self.erros.append('{}\t{}'.format(servidor.matricula, 'BRASILEIRO SEM NATURALIDADE'))
                tem_erro = True
            elif not servidor.nascimento_municipio.uf:
                self.erros.append('{}\t{}'.format(servidor.matricula, 'BRASILEIRO SEM UF'))
                tem_erro = True
            else:
                qs_naturalidade = Cidade.objects.filter(
                    nome__in=(to_ascii(servidor.nascimento_municipio.nome).upper(), servidor.nascimento_municipio.nome.upper()),
                    estado_id=Estado.ESTADOS[servidor.nascimento_municipio.uf]
                )
                qs_naturalidade = qs_naturalidade | Cidade.objects.filter(nome__iexact=servidor.nascimento_municipio.nome)
                if not qs_naturalidade.exists():
                    tem_erro = True
                    self.erros.append(
                        '{}\t{} ({}, {})'.format(
                            servidor.matricula,
                            'CODIGO DA NATURALIDADE ERRADO',
                            to_ascii(servidor.nascimento_municipio.nome).upper(),
                            servidor.nascimento_municipio.nome.upper(),
                        )
                    )
        if servidor.nacionalidade in (1, 2, 3):
            nacionalidade = 76
        elif servidor.pais_origem and servidor.pais_origem.codigo_educacenso:
            nacionalidade = servidor.pais_origem.codigo_educacenso
        else:
            self.erros.append('{}\t{}'.format(servidor.matricula, 'SEM CODIGO PAIS'))
            tem_erro = True
            nacionalidade = None
        return tem_erro, not tem_erro and qs_naturalidade.first(), not tem_erro and nacionalidade


class ExportadorEtapa2:
    def __init__(self, ano, uo, ignorar_erros, task):
        self.ano = ano
        self.uo = uo
        self.ignorar_erros = ignorar_erros
        self.registros = []
        self.erros = []

        self.modalidades = (Modalidade.INTEGRADO, Modalidade.SUBSEQUENTE, Modalidade.INTEGRADO_EJA, Modalidade.PROEJA_FIC_FUNDAMENTAL, Modalidade.CONCOMITANTE)

        dados = []
        uos = self.uo and [self.uo] or UnidadeOrganizacional.objects.suap().all()

        for uo in uos:
            alunos = (
                Aluno.objects.filter(
                    curso_campus__modalidade__in=self.modalidades,
                    matriculaperiodo__ano_letivo__ano=self.ano,
                    matriculaperiodo__periodo_letivo=1,
                    curso_campus__diretoria__setor__uo=uo,
                )
                .order_by('pessoa_fisica__cpf')
                .order_by('-matriculaperiodo')
                .distinct()
            )  # [0:10]
            dados.append((uo, alunos))

        for uo, alunos in dados:
            task.count(alunos)

        for uo, alunos in dados:
            self.exportar_registros_89(uo)
            self.exportar_registros_90_91(alunos, task)
            file_path = os.path.join(settings.TEMP_DIR, 'educacenso.txt')
            if self.ignorar_erros:
                s = '\r\n'.join(self.registros)
            else:
                s = '\r\n'.join(self.erros)
            with open(file_path, 'w') as f:
                f.write(s)
            task.finalize('Arquivo gerado com sucesso', '/edu/relatorio_educacenso_etapa_2/', file_path=file_path)

    def adicionar(self, registro):
        for i, item in enumerate(registro):
            registro[i] = str(item)
        self.registros.append('|'.join(registro))

    def exportar_registros_89(self, uo):
        siglas = uo.sigla == 'EAD' and (uo.sigla, 'CNAT') or (uo.sigla,)
        qs_diretoria = Diretoria.objects.filter(setor__uo__sigla__in=siglas)
        qs_calendario_academico = CalendarioAcademico.objects.exclude(descricao__unaccent__icontains='depend').filter(
            diario__turma__curso_campus__diretoria__setor__uo=uo,
            diario__turma__curso_campus__modalidade=Modalidade.INTEGRADO,
            diario__ano_letivo__ano=self.ano,
            diario__componente_curricular__qtd_avaliacoes=4,
        )[0:1]
        if qs_diretoria.exists() and (qs_calendario_academico.exists() or uo.sigla == 'ZL'):
            diretoria = qs_diretoria[0]
            if diretoria.diretor_geral_id:
                servidor = Servidor.objects.get(pk=diretoria.diretor_geral)
                registro = list()
                # 1 Tipo de registro
                registro.append(89)
                # 2 Código de escola - Inep
                registro.append(uo.codigo_inep)
                # 3 Número do CPF do Gestor Escolar
                registro.append(formatar(servidor.cpf))
                # 4 Nome do Gestor Escolar
                registro.append(formatar(servidor.nome_registro))
                # 5 Cargo do Gestor Escolar
                registro.append(1)
                # 6 Endereço eletrônico (e-mail) do Gestor Escolar
                registro.append(servidor.email and servidor.email.upper() or '')
                self.adicionar(registro)

    def exportar_registros_90_91(self, alunos, task):
        l90 = []
        l91 = []
        for aluno in task.iterate(alunos):

            matricula_periodo = aluno.matriculaperiodo_set.filter(ano_letivo__ano=self.ano, periodo_letivo=1).order_by('-periodo_letivo')[0]

            turma = matricula_periodo.turma_id and matricula_periodo.turma or None
            if not turma:
                self.erros.append(
                    '{}\t{}\t{}\t{}\t{}'.format(aluno.matricula, 'SEM TURMA', aluno.curso_campus.diretoria.setor.uo.sigla, aluno.curso_campus.diretoria, aluno.situacao)
                )
                continue

            if not turma.codigo_educacenso:
                self.erros.append(
                    '{}\t{}\t{}\t{}\t{}'.format(turma.codigo, 'CODIGO EDUCACENSO', turma.curso_campus.diretoria.setor.uo.sigla, turma.curso_campus.diretoria, aluno.situacao)
                )
                continue

            if not aluno.codigo_educacenso:
                self.erros.append(
                    '{}\t{}\t{}\t{}\t{}'.format(aluno.matricula, 'CODIGO EDUCACENSO', aluno.curso_campus.diretoria.setor.uo.sigla, aluno.curso_campus.diretoria, aluno.situacao)
                )
                continue

            if not matricula_periodo.codigo_educacenso:
                self.erros.append(
                    '{} {}/{}\t{}\t{}\t{}\t{}'.format(
                        aluno.matricula,
                        matricula_periodo.ano_letivo,
                        matricula_periodo.periodo_letivo,
                        'CODIGO MATRICULA EDUCACENSO',
                        aluno.curso_campus.diretoria.setor.uo.sigla,
                        aluno.curso_campus.diretoria,
                        aluno.situacao,
                    )
                )
                continue

            if matricula_periodo.situacao_id == SituacaoMatriculaPeriodo.TRANSF_CURSO:
                self.erros.append(
                    '{}\t{}\t{}\t{}\t{}'.format(aluno.matricula, 'TRANSFERIDO DE CURSO', aluno.curso_campus.diretoria.setor.uo.sigla, aluno.curso_campus.diretoria, aluno.situacao)
                )

            if (
                not matricula_periodo.matriculadiario_set.exclude(
                    diario__componente_curricular__tipo=ComponenteCurricular.TIPO_PRATICA_PROFISSIONAL, diario__componente_curricular__pode_fechar_pendencia=True
                )
                .exclude(diario__professordiario__isnull=True)
                .exclude(diario__professordiario__professor__vinculo__pessoa__pessoafisica__nascimento_municipio__isnull=True)
                .exists()
            ):
                continue

            situacao = None
            if aluno.situacao.pk in [SituacaoMatricula.TRANSFERIDO_INTERNO, SituacaoMatricula.TRANSFERIDO_EXTERNO, SituacaoMatricula.TRANSFERIDO_SUAP]:
                situacao = 1
            elif aluno.situacao.pk in [
                SituacaoMatricula.EVASAO,
                SituacaoMatricula.JUBILADO,
                SituacaoMatricula.CANCELADO,
                SituacaoMatricula.CANCELAMENTO_COMPULSORIO,
                SituacaoMatricula.CANCELAMENTO_POR_DUPLICIDADE,
                SituacaoMatricula.CANCELAMENTO_POR_DESLIGAMENTO,
            ]:
                situacao = 2
            elif aluno.situacao.pk in [SituacaoMatricula.FALECIDO]:
                situacao = 3
            elif aluno.situacao.pk == SituacaoMatricula.CONCLUIDO:
                situacao = 6
            if aluno.curso_campus.modalidade_id == Modalidade.INTEGRADO:
                if matricula_periodo.situacao_id in [SituacaoMatriculaPeriodo.REPROVADO, SituacaoMatriculaPeriodo.REPROVADO_POR_FALTA]:
                    situacao = 4

                elif matricula_periodo.situacao_id == SituacaoMatriculaPeriodo.APROVADO and aluno.situacao.pk == SituacaoMatricula.CONCLUIDO:
                    situacao = 6

                elif matricula_periodo.situacao_id in [
                    SituacaoMatriculaPeriodo.APROVADO,
                    SituacaoMatriculaPeriodo.MATRICULADO,
                    SituacaoMatriculaPeriodo.DEPENDENCIA,
                    SituacaoMatriculaPeriodo.TRANCADA,
                    SituacaoMatriculaPeriodo.TRANCADA_VOLUNTARIAMENTE,
                    SituacaoMatriculaPeriodo.MATRICULA_VINCULO_INSTITUCIONAL,
                ]:
                    situacao = 5

            if situacao is None and aluno.curso_campus.modalidade_id != Modalidade.INTEGRADO:
                situacao = 7

            registro = list()
            # 1    Tipo de registro
            registro.append(90)
            # 2 Código de escola - Inep
            registro.append(aluno.curso_campus.diretoria.setor.uo.codigo_inep)
            # 3 Código da turma na entidade/escola
            registro.append('')
            # 4 Código da turma no INEP
            registro.append(turma.codigo_educacenso)
            # 5 ID do aluno no INEP
            registro.append(aluno.codigo_educacenso)
            # 6 Código do aluno na Entidade/Escola
            registro.append('')
            # 7 Código da matricula
            registro.append(matricula_periodo.codigo_educacenso)
            # 8 Situação do aluno
            registro.append(situacao)
            l90.append(registro)

            registro = list()
            # 1    Tipo de registro
            registro.append(91)
            # 2 Código de escola - Inep
            registro.append(aluno.curso_campus.diretoria.setor.uo.codigo_inep)
            # 3 Código da turma na entidade/escola
            registro.append('')
            # 4 ID da turma - INEP
            registro.append(turma.codigo_educacenso)
            # 5 Código de identificação única do aluno – INEP
            registro.append(aluno.codigo_educacenso)
            # 6 Código de identificação única do aluno na entidade/escola
            registro.append('')
            # 7 Código da matricula
            registro.append('')
            # 8 Tipo de mediação didático pedagógico
            registro.append('')
            # 9 Código da modalidade
            registro.append('')
            # 10 Código da etapa
            registro.append('')
            # 11 Situação do aluno
            registro.append(situacao)
            l91.append(registro)

        for registro in l90:
            self.adicionar(registro)
        for registro in l91:
            pass
            # self.adicionar(registro) uso adiado
